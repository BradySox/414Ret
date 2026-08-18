"""Adjudicate the §89 living-battlespace in-game rows without a cockpit.

Two evidence sources, either or both:

* **A control/test miz pair** -- generate the same turn twice, gate off then
  gate on, and diff the structure. This is what makes B56/B57/B58 falsifiable
  from the desk: air starts, uncontrolled ramp residue, pylon counts, fuel
  fractions, late-activation times and the embedded voice clips are all in the
  file. A structural difference the gate is supposed to cause but did not is a
  silent-gate failure, which is the class these rows exist to catch.
* **The two logs** -- ``dcs.log`` carries the plugin runtime (``BSNET|:`` and
  ``REACTRED|:``); Retribution's own ``logs/retribution.log`` carries the
  parking-exhaustion warnings that are the shared fail signature of B56-B58.

Verdicts are deliberately three-valued. NOT OBSERVED is not a pass: it means
the evidence never appeared, which for a feature whose failure mode is silence
is the thing to chase.

Usage::

    python tools/spectator_89_report.py --control off.miz --test on.miz
    python tools/spectator_89_report.py --test on.miz --dcs-log <dcs.log>

Card: docs/dev/flycards/SPECTATOR-89.md. Rows: docs/dev/414th-ingame-pass-checklist.md.
"""

from __future__ import annotations

import argparse
import re
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import dcs.lua

# DCS's ground-start waypoint actions. Anything else on waypoint 1 is an air
# start, which is how a pre-rolled flight enters the mission already en route.
GROUND_STARTS = {
    "From Parking Area",
    "From Parking Area Hot",
    "From Runway",
    "From Ground Area",
    "From Ground Area Hot",
}

PASS = "PASS"
FAIL = "FAIL"
UNSEEN = "NOT OBSERVED"


@dataclass
class MizFacts:
    """The structural facts a spectator pass needs out of one generated miz."""

    path: Path
    air_starts: Counter[str] = field(default_factory=Counter)
    ground_starts: Counter[str] = field(default_factory=Counter)
    uncontrolled: Counter[str] = field(default_factory=Counter)
    late_activated: Counter[str] = field(default_factory=Counter)
    start_times: dict[str, list[float]] = field(default_factory=dict)
    activation_times: list[float] = field(default_factory=list)
    clean_wing: list[str] = field(default_factory=list)
    part_fuel: list[str] = field(default_factory=list)
    client_groups: list[str] = field(default_factory=list)
    ogg_count: int = 0
    ogg_bytes: int = 0

    @property
    def total_flying(self) -> int:
        return sum(self.air_starts.values()) + sum(self.ground_starts.values())


def _load_mission(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path) as miz:
        raw = miz.read("mission").decode("utf-8", errors="replace")
    parsed = dcs.lua.loads(raw)
    mission = parsed.get("mission", parsed)
    if not isinstance(mission, dict):
        raise ValueError(f"{path}: no mission table")
    return mission


def _values(table: Any) -> list[Any]:
    """pydcs' Lua loader yields 1-based dicts for arrays; take the values."""
    if isinstance(table, dict):
        return list(table.values())
    if isinstance(table, list):
        return list(table)
    return []


def read_miz(path: Path) -> MizFacts:
    facts = MizFacts(path=path)
    with zipfile.ZipFile(path) as miz:
        for info in miz.infolist():
            if info.filename.lower().endswith(".ogg"):
                facts.ogg_count += 1
                facts.ogg_bytes += info.file_size
    mission = _load_mission(path)
    for side in ("blue", "red"):
        coalition = mission.get("coalition", {}).get(side, {})
        facts.start_times.setdefault(side, [])
        for country in _values(coalition.get("country", {})):
            for category in ("plane", "helicopter"):
                for group in _values(country.get(category, {}).get("group", {})):
                    _read_group(facts, side, group)
    facts.activation_times = _activation_times(mission)
    return facts


def _activation_times(mission: dict[str, Any]) -> list[float]:
    """When each late-activated flight is released into the mission.

    NOT ``group.start_time`` -- that reads 0 for every waved flight. Retribution
    writes the push as a DCS trigger pair: ``conditions[i]`` carries
    ``c_time_after(N)`` and the matching ``actions[i]`` calls
    ``a_activate_group``. The condition index is the action index, so pairing
    them by key gives the real wave clock.
    """
    trig = mission.get("trig", {})
    conditions = trig.get("conditions", {}) or {}
    actions = trig.get("actions", {}) or {}
    out: list[float] = []
    for key, action in actions.items():
        if "a_activate_group" not in str(action):
            continue
        match = re.search(
            r"c_time_after\((\d+(?:\.\d+)?)\)", str(conditions.get(key, ""))
        )
        if match:
            out.append(float(match.group(1)))
    return out


def _read_group(facts: MizFacts, side: str, group: dict[str, Any]) -> None:
    name = str(group.get("name", "?"))
    points = _values(group.get("route", {}).get("points", {}))
    first = points[0] if points else {}
    action = str(first.get("action", ""))
    if action in GROUND_STARTS:
        facts.ground_starts[side] += 1
    else:
        facts.air_starts[side] += 1
    if group.get("uncontrolled"):
        facts.uncontrolled[side] += 1
    if group.get("lateActivation"):
        facts.late_activated[side] += 1
    facts.start_times[side].append(float(group.get("start_time", 0) or 0))

    for unit in _values(group.get("units", {})):
        if unit.get("skill") == "Client" or unit.get("skill") == "Player":
            facts.client_groups.append(name)
        pylons = _values(unit.get("payload", {}).get("pylons", {}))
        if not pylons:
            facts.clean_wing.append(name)
        fuel = unit.get("fuel")
        if fuel is not None:
            try:
                # Retribution writes AI fuel as an absolute mass; a burned-down
                # tank shows up as a group whose units disagree with the type's
                # full load. We can only flag "not a round full number" here --
                # the control/test diff is what makes it meaningful.
                facts.part_fuel.append(f"{name}={float(fuel):.0f}")
            except (TypeError, ValueError):
                pass


def read_log(path: Path, needles: tuple[str, ...]) -> list[str]:
    if not path.exists():
        return []
    hits: list[str] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if any(needle in line for needle in needles):
                hits.append(line.rstrip())
    return hits


def find_dcs_log() -> Optional[Path]:
    saved = Path.home() / "Saved Games"
    for folder in sorted(saved.glob("DCS*")):
        candidate = folder / "Logs" / "dcs.log"
        if candidate.exists():
            return candidate
    return None


def find_latest_archive() -> Optional[Path]:
    saved = Path.home() / "Saved Games"
    newest: Optional[Path] = None
    for folder in sorted(saved.glob("DCS*")):
        archive = folder / "Missions" / "Retribution Archive"
        for miz in archive.glob("*.miz"):
            if newest is None or miz.stat().st_mtime > newest.stat().st_mtime:
                newest = miz
    return newest


@dataclass
class Row:
    row: str
    title: str
    verdict: str
    evidence: list[str] = field(default_factory=list)


def adjudicate(
    test: Optional[MizFacts],
    control: Optional[MizFacts],
    dcs_lines: list[str],
    app_lines: list[str],
) -> list[Row]:
    rows: list[Row] = []
    rows.append(_b56(test, control, app_lines))
    rows.append(_b57(test, control))
    rows.append(_b58(test, control))
    rows.append(_b59(test, control, dcs_lines))
    rows.append(_b60(dcs_lines))
    return rows


def _b56(
    test: Optional[MizFacts], control: Optional[MizFacts], app_lines: list[str]
) -> Row:
    row = Row("B56", "Pre-roll: the war is already up at spawn", UNSEEN)
    if test is None:
        row.evidence.append("no test miz given")
        return row
    air = sum(test.air_starts.values())
    row.evidence.append(
        f"test: {air} air-start flights of {test.total_flying} "
        f"(blue {test.air_starts['blue']}, red {test.air_starts['red']})"
    )
    if control is not None:
        base = sum(control.air_starts.values())
        row.evidence.append(f"control: {base} air-start of {control.total_flying}")
        row.verdict = PASS if air > base else FAIL
        if air <= base:
            row.evidence.append(
                "the gate added no air starts -- silent gate, or the campaign "
                "already air-starts its AI (check the start-type setting)"
            )
    else:
        # A gate-off miz already air-starts a few flights (measured: 4 of 118 on
        # a pre-§89 generation), so a raw count proves nothing on its own.
        row.evidence.append("no control miz: air starts occur with the gate off too")
    overflow = [
        line for line in app_lines if "No room on runway or parking slots" in line
    ]
    if overflow:
        row.evidence.append(f"{len(overflow)} air-promotions from full parking")
        if len(overflow) > 1:
            row.verdict = FAIL
            row.evidence.append("a pattern, not the known one-off fallback")
    return row


def _b57(test: Optional[MizFacts], control: Optional[MizFacts]) -> Row:
    row = Row("B57", "Ramp residue + clean-wing returners", UNSEEN)
    if test is None:
        row.evidence.append("no test miz given")
        return row
    parked = sum(test.uncontrolled.values())
    row.evidence.append(f"test: {parked} uncontrolled parked groups")
    row.evidence.append(f"test: {len(test.clean_wing)} groups with empty pylons")
    if control is not None:
        base = sum(control.uncontrolled.values())
        row.evidence.append(f"control: {base} uncontrolled parked groups")
        row.verdict = PASS if parked > base else FAIL
        if parked <= base:
            row.evidence.append("no residue appeared -- the Completed branch never ran")
    else:
        # QRA templates and idle aircraft are uncontrolled too (measured: 27 on
        # a pre-§89 generation). Only the delta over control is residue.
        row.evidence.append("no control miz: QRA/idle jets are uncontrolled as well")
    return row


def _b58(test: Optional[MizFacts], control: Optional[MizFacts]) -> Row:
    row = Row("B58", "Follow-on waves launch behind you", UNSEEN)
    if test is None:
        row.evidence.append("no test miz given")
        return row
    latest = max(test.activation_times) if test.activation_times else 0.0
    row.evidence.append(
        f"test: last wave pushes at {latest / 60:.0f} min "
        f"({len(test.activation_times)} timed activations, "
        f"{sum(test.late_activated.values())} late-activated groups)"
    )
    if control is not None:
        base_latest = max(control.activation_times) if control.activation_times else 0.0
        row.evidence.append(f"control: last wave pushes at {base_latest / 60:.0f} min")
        row.verdict = PASS if latest > base_latest else FAIL
        if latest <= base_latest:
            row.evidence.append("the spread window did not widen")
    else:
        row.evidence.append("no control miz: needed to show the window widened")
    return row


def _b59(
    test: Optional[MizFacts], control: Optional[MizFacts], dcs_lines: list[str]
) -> Row:
    row = Row("B59", "Voice net on the AWACS frequency", UNSEEN)
    if test is not None:
        # Retribution embeds ~111 clips of its own before the net adds any, so
        # only the delta over control is the voice net's payload.
        base_count = control.ogg_count if control else 0
        base_bytes = control.ogg_bytes if control else 0
        added_bytes = test.ogg_bytes - base_bytes
        row.evidence.append(
            f"test miz: {test.ogg_count} clips / {test.ogg_bytes / 1_048_576:.1f} MB"
            + (
                f"; +{test.ogg_count - base_count} clips "
                f"/ +{added_bytes / 1_048_576:.1f} MB over control"
                if control
                else " (no control: baseline clips not subtracted)"
            )
        )
        if control and added_bytes > 4 * 1_048_576:
            row.verdict = FAIL
            row.evidence.append("clip payload past the ~1-2 MB expectation")
    armed = [line for line in dcs_lines if "BSNET|: armed" in line]
    idle = [line for line in dcs_lines if "BSNET|: no calls emitted" in line]
    errors = [line for line in dcs_lines if "BSNET|: call error" in line]
    skipped = [line for line in dcs_lines if "off net" in line]
    if armed:
        row.evidence.append(armed[-1].strip())
        match = re.search(r"armed (\d+)", armed[-1])
        if match and int(match.group(1)) > 0 and row.verdict != FAIL:
            row.verdict = PASS
    if idle:
        row.verdict = FAIL
        row.evidence.append("plugin idle: no calls emitted (gate or no blue AWACS)")
    if skipped:
        row.evidence.append(
            f"{len(skipped)} calls skipped for a dead transmitter -- "
            "the liveness guard working, not a fault"
        )
    if errors:
        row.verdict = FAIL
        row.evidence.extend(errors[:3])
    return row


def _b60(dcs_lines: list[str]) -> Row:
    row = Row("B60", "Reactive red over a struck objective", UNSEEN)
    armed = [line for line in dcs_lines if "REACTRED|: armed" in line]
    idle = [line for line in dcs_lines if "REACTRED|: nothing emitted" in line]
    struck = [line for line in dcs_lines if "struck; alert launch in" in line]
    scrambling = [line for line in dcs_lines if "scrambling over" in line]
    station = [line for line in dcs_lines if "on station over" in line]
    exhausted = [line for line in dcs_lines if "reaction pool exhausted" in line]
    lost = [line for line in dcs_lines if "lost before tasking" in line]
    failed = [line for line in dcs_lines if "orbit task push failed" in line]
    if idle:
        row.verdict = FAIL
        row.evidence.append(
            "plugin idle: nothing emitted (gate, or no watched objective)"
        )
        return row
    if armed:
        row.evidence.append(armed[-1].strip())
    else:
        row.evidence.append("never armed -- the emitter produced no plan")
        return row
    row.evidence.append(
        f"{len(struck)} objectives struck, {len(scrambling)} scrambles, "
        f"{len(station)} on station"
    )
    if station:
        row.verdict = PASS
    elif scrambling:
        row.verdict = FAIL
        row.evidence.append("launched but never established the orbit")
    elif struck:
        row.verdict = FAIL
        row.evidence.append("a strike registered but no launch followed")
    if exhausted:
        row.evidence.append("pool exhaustion logged -- the cap holding, not a fault")
    if lost or failed:
        row.evidence.extend(line.strip() for line in (lost + failed)[:3])
    return row


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test", type=Path, help="miz generated with the gates ON")
    parser.add_argument(
        "--control", type=Path, help="same turn generated with them OFF"
    )
    parser.add_argument("--dcs-log", type=Path, help="DCS dcs.log (auto-discovered)")
    parser.add_argument(
        "--app-log",
        type=Path,
        default=Path("logs/retribution.log"),
        help="Retribution's own log, for parking warnings",
    )
    args = parser.parse_args()

    test_path = args.test or find_latest_archive()
    test = read_miz(test_path) if test_path and test_path.exists() else None
    control = read_miz(args.control) if args.control and args.control.exists() else None
    dcs_log = args.dcs_log or find_dcs_log()
    dcs_lines = read_log(dcs_log, ("BSNET|", "REACTRED|")) if dcs_log else []
    app_lines = read_log(args.app_log, ("No room on runway", "No parking for returned"))

    print("§89 spectator pass report")
    print(f"  test miz : {test_path or '(none)'}")
    print(f"  control  : {args.control or '(none)'}")
    print(f"  dcs.log  : {dcs_log or '(not found)'}")
    print()
    for row in adjudicate(test, control, dcs_lines, app_lines):
        print(f"[{row.verdict:>12}] {row.row} - {row.title}")
        for line in row.evidence:
            print(f"               {line}")
    print()
    print("NOT OBSERVED is not a pass. Record results in")
    print("docs/dev/414th-ingame-pass-checklist.md the same session.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
