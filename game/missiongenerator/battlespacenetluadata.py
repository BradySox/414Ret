"""Blue voice net -> Lua config bridge (``dcsRetribution.battlespaceNet``, §89 P4).

The living battlespace's audible half: with the master pre-roll gate AND
``living_battlespace_voice_net`` on, the planned ATO's own timeline is turned
into a schedule of short radio calls -- check-ins as follow-on waves launch,
pushes before strike TOTs, on-station and RTB calls -- each synthesized to a
small 8 kHz mono wav at GENERATION time (Windows SAPI via PowerShell; no
player-side install, no runtime dependency) and embedded in the miz. The
``battlespacenet`` plugin transmits each call positionally from the real
transmitting group on the mission's own AWACS frequency
(``trigger.action.radioTransmission`` -- the §70 red-net delivery contract),
so tuning the briefed AWACS channel is enough to hear the war.

Transport decision (design-note open call 5): generation-time pre-render was
chosen over the SRS-runtime TTS ecosystem for the SP-first footprint -- zero
installs, native playback for every client in MP too. The cost is a static
schedule (planned events only; nothing voices dynamic in-mission events) and
SAPI voice quality. The SRS/MSRS path stays recorded in the design note as the
dynamic upgrade if MP nights ever want it.

Every call's truth is the plan: the transmitting group is the real flight's
group (dead or despawned at call time = silence, handled by the plugin), the
times are the flights' own, and the words say only what the ATO says. Audio
only -- no force-model change, no kills, nothing owned by Lua. Emits nothing
when either gate is off, when no blue AWACS exists (nothing to key on), or
when synthesis is unavailable (non-Windows generation) -- all logged, never
silent-skipped.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Optional

from game.ato.flighttype import FlightType

if TYPE_CHECKING:
    from dcs.mission import Mission

    from game import Game

    from .luagenerator import LuaData
    from .missiondata import MissionData

#: Push calls come from the strike families whose TOT is a real push moment;
#: on-station calls from the racetrack families. Everything gets an RTB call.
_PUSH_TASKS = frozenset(
    {
        FlightType.STRIKE,
        FlightType.BAI,
        FlightType.SEAD,
        FlightType.DEAD,
        FlightType.OCA_RUNWAY,
        FlightType.OCA_AIRCRAFT,
        FlightType.ANTISHIP,
        FlightType.CAS,
    }
)
_STATION_TASKS = frozenset(
    {
        FlightType.BARCAP,
        FlightType.TARCAP,
        FlightType.AEWC,
        FlightType.REFUELING,
    }
)

#: Net discipline: minimum gap between calls and a hard cap per mission --
#: chatter that matches the war, not a wall of sound.
MIN_CALL_GAP_S = 20.0
MAX_CALLS = 48

#: The first schedulable moment. Calls whose event lands earlier are dropped
#: rather than piled onto mission start.
EARLIEST_CALL_S = 60.0


@dataclass
class NetCall:
    """One scheduled transmission: mission-relative seconds, the transmitting
    DCS group, the AWACS-net frequency, the spoken text, and (after synthesis)
    the packed miz path of its audio clip."""

    t: float
    group_name: str
    freq_mhz: float
    text: str
    filename: str = ""


@dataclass
class BattlespaceNetInfo:
    """The mission's voice-net plan, stored on ``MissionData.battlespace_net``."""

    calls: list[NetCall] = field(default_factory=list)


def phoneticize(callsign: str) -> str:
    """ "Dodge41" -> "Dodge 4 1": digits read as single numerals on the radio."""
    out: list[str] = []
    for ch in str(callsign):
        if ch.isdigit():
            out.append(" ")
            out.append(ch)
        elif ch in "-_":
            out.append(" ")
        else:
            out.append(ch)
    return " ".join("".join(out).split())


def build_net_schedule(
    game: Game, mission_data: MissionData, now: datetime
) -> list[NetCall]:
    """The chatter schedule implied by the generated ATO. Pure -- no synthesis.

    One voice per package (its first generated flight). Sources of truth:
    ``FlightData.departure_delay`` for the launch check-in, the package TOT for
    push/on-station, ``mission_departure_time`` for RTB. Everything transmits
    on the first blue AWACS frequency -- the one channel the kneeboard already
    briefs -- so the net is audible without hunting the dial.
    """
    settings = game.settings
    if not getattr(settings, "living_battlespace_preroll", False):
        return []
    if not getattr(settings, "living_battlespace_voice_net", False):
        return []
    awacs_freq, awacs_name = _blue_awacs(mission_data)
    if awacs_freq is None:
        logging.info("BSNET: no blue AWACS in the mission; voice net stays silent")
        return []

    calls: list[NetCall] = []
    for flights in mission_data.packages.values():
        blue = [
            f for f in flights if getattr(f, "friendly", None) and f.friendly.is_blue
        ]
        if not blue:
            continue
        lead = blue[0]
        if getattr(lead, "client_units", None):
            # The player's own package: they fly that net live; scripting their
            # lead's calls over them reads wrong.
            continue
        package = lead.package
        callsign = phoneticize(getattr(lead, "callsign", "") or lead.group_name)
        group = lead.group_name

        delay = getattr(lead, "departure_delay", None)
        if delay is not None and delay.total_seconds() > 120:
            calls.append(
                NetCall(
                    delay.total_seconds() + 60,
                    group,
                    awacs_freq,
                    f"{awacs_name}, {callsign}, airborne as fragged.",
                )
            )

        tot = getattr(package, "time_over_target", None)
        if isinstance(tot, datetime):
            tot_s = (tot - now).total_seconds()
            if lead.flight_type in _PUSH_TASKS and tot_s - 300 > EARLIEST_CALL_S:
                calls.append(
                    NetCall(tot_s - 300, group, awacs_freq, f"{callsign}, pushing.")
                )
            if lead.flight_type in _STATION_TASKS and tot_s + 30 > EARLIEST_CALL_S:
                calls.append(
                    NetCall(tot_s + 30, group, awacs_freq, f"{callsign}, on station.")
                )

        departure = getattr(package, "mission_departure_time", None)
        if isinstance(departure, datetime):
            rtb_s = (departure - now).total_seconds() + 60
            if rtb_s > EARLIEST_CALL_S:
                calls.append(
                    NetCall(rtb_s, group, awacs_freq, f"{callsign}, off station, RTB.")
                )

    return _rate_limited(calls)


def _rate_limited(calls: list[NetCall]) -> list[NetCall]:
    """Time order, then net discipline: drop anything inside the minimum gap
    of the previous call, and cap the mission's total."""
    out: list[NetCall] = []
    last = -1e9
    for call in sorted(calls, key=lambda c: c.t):
        if call.t - last < MIN_CALL_GAP_S:
            continue
        out.append(call)
        last = call.t
        if len(out) >= MAX_CALLS:
            break
    return out


def _blue_awacs(mission_data: MissionData) -> tuple[Optional[float], str]:
    """The first blue AWACS's frequency (MHz) and its spoken hail name.

    ``AwacsInfo.blue`` is a Player enum -- always truthy -- so the side check
    must go through ``.is_blue`` (the bare-truthiness audit class).
    """
    for awacs in getattr(mission_data, "awacs", []):
        side = getattr(awacs, "blue", None)
        if side is None or not getattr(side, "is_blue", False):
            continue
        freq = getattr(awacs, "freq", None)
        if freq is None:
            continue
        callsign = str(getattr(awacs, "callsign", "") or "Magic")
        hail = "".join(ch for ch in callsign if ch.isalpha()) or "Magic"
        return freq.hertz / 1_000_000, hail
    return None, "Magic"


def plan_battlespace_net(
    game: Game,
    mission: Mission,
    mission_data: MissionData,
    now: datetime,
    synthesize: Optional[Callable[[list[NetCall], Path], bool]] = None,
) -> Optional[BattlespaceNetInfo]:
    """Schedule, synthesize, and embed the voice net; None when it has nothing.

    ``synthesize`` is injectable for tests; the default is the Windows SAPI
    pipeline. On any synthesis failure the whole net is dropped with a warning
    (never a half-voiced mission) -- the miz without a net is the pre-P4 miz.
    """
    calls = build_net_schedule(game, mission_data, now)
    if not calls:
        return None
    synth = synthesize if synthesize is not None else _synthesize_sapi
    out_dir = Path(tempfile.gettempdir()) / "retribution_battlespace_net"
    shutil.rmtree(out_dir, ignore_errors=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    if not synth(calls, out_dir):
        logging.warning("BSNET: synthesis unavailable/failed; voice net dropped")
        return None
    for index, call in enumerate(calls):
        wav = out_dir / f"bsnet_{index:03d}.wav"
        if not wav.exists() or wav.stat().st_size == 0:
            logging.warning("BSNET: missing clip %s; voice net dropped", wav.name)
            return None
        mission.map_resource.add_resource_file(wav.resolve())
        call.filename = f"l10n/DEFAULT/{wav.name}"
    logging.info("BSNET: %d calls voiced and embedded", len(calls))
    return BattlespaceNetInfo(calls)


def _synthesize_sapi(calls: list[NetCall], out_dir: Path) -> bool:
    """Render every call to 8 kHz mono wav via Windows SAPI. False = no audio.

    8 kHz/8-bit mono is deliberate: ~35 KB per call, and the band limit reads
    as a radio without any effects chain. One PowerShell process voices the
    whole manifest (measured ~150 ms per line).
    """
    if sys.platform != "win32":
        logging.info("BSNET: non-Windows generation; SAPI synthesis unavailable")
        return False
    manifest = [
        {"file": str(out_dir / f"bsnet_{index:03d}.wav"), "text": call.text}
        for index, call in enumerate(calls)
    ]
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    script_path = out_dir / "synth.ps1"
    script_path.write_text(_SAPI_SCRIPT, encoding="utf-8")
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script_path),
                "-Manifest",
                str(manifest_path),
            ],
            capture_output=True,
            timeout=180,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as ex:
        logging.warning("BSNET: SAPI synthesis failed to run: %s", ex)
        return False
    if result.returncode != 0:
        logging.warning(
            "BSNET: SAPI synthesis exited %s: %s",
            result.returncode,
            result.stderr.decode(errors="replace")[:500],
        )
        return False
    return True


_SAPI_SCRIPT = """param([string]$Manifest)
Add-Type -AssemblyName System.Speech
$items = Get-Content -Raw $Manifest | ConvertFrom-Json
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$fmt = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(8000, [System.Speech.AudioFormat.AudioBitsPerSample]::Eight, [System.Speech.AudioFormat.AudioChannel]::Mono)
foreach ($i in $items) {
  $s.SetOutputToWaveFile($i.file, $fmt)
  $s.Rate = 2
  $s.Speak($i.text)
}
$s.SetOutputToNull()
$s.Dispose()
"""


def populate_battlespace_net_lua(root: LuaData, mission_data: MissionData) -> None:
    """Emit the ``dcsRetribution.battlespaceNet`` subtree from the stored plan."""
    info = getattr(mission_data, "battlespace_net", None)
    if info is None or not info.calls:
        return
    node = root.add_item("battlespaceNet")
    call_list = node.add_item("calls")
    for call in info.calls:
        rec = call_list.add_item()
        rec.add_key_value("t", str(call.t))
        rec.add_key_value("group", call.group_name)
        rec.add_key_value("mhz", str(call.freq_mhz))
        rec.add_key_value("file", call.filename)
        rec.add_key_value("text", call.text)
