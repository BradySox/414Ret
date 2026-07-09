"""Enemy comms jamming -> Lua config bridge (``dcsRetribution.commsJam``).

The IADS comms nodes, given a voice. With ``enemy_comms_jamming`` on, every alive
enemy IADS communications / command-center node becomes a standoff comms jammer:
the ``commsjam`` plugin floods the BLUE side's *briefed* radio channels with
duty-cycled barrage noise transmitted (``trigger.action.radioTransmission``) from
the node's campaign-map position, so the audio arrives in the player's headset
through DCS's own radio path -- SRS users hear it too, because SRS tunes off the
cockpit radios. Power and distance attenuation are DCS-native; no SRS server
dependency exists or is wanted.

Python owns the *plan*: which nodes jam (alive enemy ``comms``/``commandcenter``
TGOs, the same objects MANTIS's C2 graph watches), which frequencies are fair
game (the blue flights' intra-flight channels -- human-crewed flights first --
plus the blue AWACS freqs; GUARD and anything unbriefed are never touched by
construction), and one freshly-allocated **JAM BACKUP** frequency the jammer can
never land on (it comes out of the same ``RadioRegistry`` every briefed channel
came out of, so it is unused by anything). The backup is surfaced on the
kneeboard comms ladder so comms discipline -- push to the backup, kill the node
-- is a play, not a mystery.

**The intel gate** (``comms_jam_requires_capture``, default ON): red can only
jam channels it *knows*, and it learns them from a **captured aircrew's comms
plan** -- the §15/§21 Combat SAR enemy-capture race. In this mode the plugin
stays dormant until either a POW is held whose comms plan is still exploitable
(captured within ``COMMS_COMPROMISE_TURNS``) or a pilot is captured live
mid-mission (``combat_sar_captures``), at which point the jamming starts after a
short exploitation delay. Save the pilot and the net stays clean -- another
reason Combat SAR matters, and a periodic lesson in rotating compromised
channels. The compromise is time-boxed independently of the POW hold, so an
indefinitely-held POW (a will campaign, §48) does not jam the net forever: the
squadron rotates its comms plan after a few turns. Turning the gate off restores
the ambient "jam whenever a C2 node lives" behavior.

Audio pressure ONLY, the §36/§49 discipline: no force-model change, no kills
owned by Lua. Killing the node is an ordinary strike on an ordinary IADS TGO
(recorded natively); the plugin merely stops transmitting when the node dies.
Emits nothing when the setting is off, no enemy comms node is alive, or no blue
frequency exists -- such missions carry no ``commsJam`` node and the plugin
no-ops.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

from game.radio.radios import RadioFrequency, RadioRegistry

if TYPE_CHECKING:
    from game import Game

    from .luagenerator import LuaData
    from .missiondata import MissionData

#: TGO categories that host the jammer. Deliberately the IADS C2 objects only --
#: the same comms masts / command bunkers the MANTIS C2-degradation graph watches
#: -- so the strike that silences the jamming is the strike that degrades the
#: IADS. Never SAMs, never EWRs, never generic buildings.
JAMMER_CATEGORIES = ("comms", "commandcenter")

#: Frequencies that must never be jammed even if they somehow end up briefed as
#: an intra-flight channel: UHF/VHF GUARD (Combat SAR and emergencies live
#: there). The registry reserves both, so this is a defensive double-guard.
GUARD_MHZ = (243.0, 121.5)

#: Hard cap on the emitted jam list. The plugin duty-cycles a small subset per
#: burst anyway; this bounds the Lua config for a huge ATO.
MAX_JAMMED_FREQUENCIES = 10

#: Comm-ladder label for the guaranteed-un-jammed fallback channel. The single
#: source of truth shared by the producer (``missiongenerator.add_comm``) and the
#: kneeboard consumers (the Mission Info BLUF line + the Support Info filter that
#: keeps this channel out of the package table), so the label can't drift between
#: them and silently resurrect the phantom-flight row.
JAM_BACKUP_COMM_NAME = "JAM BACKUP"

#: How many turns a captured comms plan stays exploitable. A POW held past this
#: no longer compromises the net from mission start -- the squadron has rotated
#: its comms plan (the "rotate compromised channels" lesson made literal), even
#: though the POW itself may be held indefinitely on a will campaign. Keeps the
#: §51 comms compromise time-boxed rather than riding the POW hold forever.
COMMS_COMPROMISE_TURNS = 4


@dataclass
class CommsJamJammer:
    """One enemy C2 node that jams: display name, the per-unit DCS names the
    plugin watches for death (the MANTIS ``dcs_name_for_group`` convention --
    unit names; statics resolve in Lua as ``<name> .. " object"``), and the
    campaign-map transmission origin."""

    name: str
    unit_names: list[str]
    x: float
    y: float


@dataclass
class CommsJamInfo:
    """The mission's comms-jam plan, stored on ``MissionData.comms_jam`` so the
    Lua emitter and the kneeboard (JAM BACKUP line) read the same plan."""

    jammers: list[CommsJamJammer]
    frequencies: list[RadioFrequency]
    #: The one frequency guaranteed un-jammed (freshly allocated, so no flight
    #: uses it either). None only if the registry is exhausted.
    backup: Optional[RadioFrequency]
    #: Intel-driven mode (``comms_jam_requires_capture``): red only jams once it
    #: holds a captured aircrew's comms plan. False = jam whenever a node lives.
    capture_only: bool = False
    #: With ``capture_only``, whether the channels are compromised from mission
    #: start: a POW is currently held (``pending_pow_recoveries``), so red took
    #: the comms plan on an earlier turn and it hasn't been rotated out yet.
    #: Otherwise the plugin stays dormant until an in-mission capture.
    active_from_start: bool = True


def plan_comms_jam(
    game: "Game", mission_data: "MissionData", radio_registry: RadioRegistry
) -> Optional[CommsJamInfo]:
    """Build the comms-jam plan, or None when the feature has nothing to do."""
    if not getattr(game.settings, "enemy_comms_jamming", False):
        return None
    jammers = _enemy_jammer_nodes(game)
    if not jammers:
        return None
    frequencies = _blue_briefed_frequencies(mission_data)
    if not frequencies:
        return None
    # alloc_uhf never raises: on an exhausted registry it degrades to *reusing*
    # a channel, which could (freakishly) be one we're about to jam -- retry a
    # few times, then go without a backup rather than publish a jammed one.
    backup: Optional[RadioFrequency] = None
    for _ in range(5):
        candidate = radio_registry.alloc_uhf()
        if candidate not in frequencies:
            backup = candidate
            break
    else:
        logging.warning(
            "Comms jam: could not allocate an un-jammed JAM BACKUP frequency"
        )
    capture_only = bool(getattr(game.settings, "comms_jam_requires_capture", True))
    # A POW captured RECENTLY means red is still exploiting the comms plan it took
    # off them: the channels are compromised from mission start. The compromise is
    # time-boxed to COMMS_COMPROMISE_TURNS -- freeing the POW ends it (they leave
    # pending_pow_recoveries), and so does the squadron rotating its comms plan
    # after a few turns, so an indefinitely-held POW (a will campaign) does not
    # jam the net forever. Old saves' entries carry no captured_turn -> treated as
    # still-fresh (compromised) rather than silently clean.
    pow_compromised = _has_recent_pow(game)
    return CommsJamInfo(
        jammers,
        frequencies,
        backup,
        capture_only=capture_only,
        active_from_start=(not capture_only) or pow_compromised,
    )


def _has_recent_pow(game: "Game") -> bool:
    """True if BLUE holds a POW captured within COMMS_COMPROMISE_TURNS -- the comms
    plan is still exploitable."""
    turn = getattr(game, "turn", 0)
    for entry in getattr(game.blue, "pending_pow_recoveries", []):
        captured_turn = getattr(entry, "captured_turn", None)
        if captured_turn is None:
            return True  # pre-migration entry: assume still compromised
        if turn - captured_turn < COMMS_COMPROMISE_TURNS:
            return True
    return False


def populate_comms_jam_lua(
    root: "LuaData", game: "Game", mission_data: "MissionData"
) -> None:
    """Emit the ``dcsRetribution.commsJam`` subtree from the stored plan."""
    info = getattr(mission_data, "comms_jam", None)
    if info is None:
        return

    node = root.add_item("commsJam")
    jammer_list = node.add_item("jammers")
    for jammer in info.jammers:
        rec = jammer_list.add_item()
        rec.add_key_value("name", jammer.name)
        # Unit names, per the MANTIS C2 convention: the plugin checks
        # StaticObject.getByName(name .. " object") + the dead_events ledger.
        rec.add_data_array("units", jammer.unit_names)
        # pydcs Point: x = north, y = east (the emitter frame the other
        # runtime plugins share).
        rec.add_key_value("x", str(jammer.x))
        rec.add_key_value("y", str(jammer.y))

    freq_list = node.add_item("freqs")
    for freq in info.frequencies:
        rec = freq_list.add_item()
        rec.add_key_value("mhz", str(freq.mhz))
        rec.add_key_value("mod", freq.modulation.name)

    if info.backup is not None:
        # Nested single-value items, not add_key_value: the LuaData serializer
        # drops scalar key-values on an object that also carries nested items.
        node.add_item("backupMhz").set_value(str(info.backup.mhz))
    node.add_item("captureOnly").set_value("true" if info.capture_only else "false")
    node.add_item("activeFromStart").set_value(
        "true" if info.active_from_start else "false"
    )


def _enemy_jammer_nodes(game: "Game") -> list[CommsJamJammer]:
    """Alive enemy (non-player-owned) comms / command-center TGOs.

    Emitted regardless of culling: the transmission is synthetic (a point on
    the map), and an un-spawned node simply can't be killed *this* mission --
    the standing jamming pressure is exactly what motivates fragging a strike
    at it next turn, which un-culls it.
    """
    jammers: list[CommsJamJammer] = []
    for cp in game.theater.controlpoints:
        if cp.captured.is_blue:
            continue
        for tgo in cp.ground_objects:
            if getattr(tgo, "category", None) not in JAMMER_CATEGORIES:
                continue
            unit_names = _alive_unit_names(tgo)
            pos = getattr(tgo, "position", None)
            if not unit_names or pos is None or not hasattr(pos, "x"):
                continue
            name = getattr(tgo, "obj_name", None) or getattr(tgo, "name", "C2 node")
            jammers.append(CommsJamJammer(str(name), unit_names, pos.x, pos.y))
    return jammers


def _alive_unit_names(tgo: Any) -> list[str]:
    names: list[str] = []
    for group in getattr(tgo, "groups", []):
        for unit in getattr(group, "units", []):
            unit_name = getattr(unit, "unit_name", None)
            if unit_name and getattr(unit, "alive", False):
                names.append(unit_name)
    return names


def _blue_briefed_frequencies(mission_data: "MissionData") -> list[RadioFrequency]:
    """The BLUE channels worth stepping on, most human-relevant first.

    Positive list by construction -- intra-flight channels (human-crewed
    flights first, then AI) and blue AWACS/GCI freqs. ATC, ATIS, tankers and
    GUARD are never listed, so ground ops and emergencies stay clean.
    """
    ordered: list[RadioFrequency] = []

    def add(freq: Optional[RadioFrequency]) -> None:
        if freq is None:
            return
        if any(abs(freq.mhz - guard) < 1e-6 for guard in GUARD_MHZ):
            return
        if freq not in ordered:
            ordered.append(freq)

    for flight in mission_data.flights:
        if flight.friendly.is_blue and flight.client_units:
            add(flight.intra_flight_channel)
    for awacs in mission_data.awacs:
        if awacs.blue.is_blue:
            add(awacs.freq)
    for flight in mission_data.flights:
        if flight.friendly.is_blue and not flight.client_units:
            add(flight.intra_flight_channel)
    return ordered[:MAX_JAMMED_FREQUENCIES]
