"""Apply a flown mission's state.json to a DIFFERENT campaign save.

The normal Retribution flow binds a mission's ``state.json`` to the UnitMap of
the exact mission the app generated: every kill event is a generated unit NAME
(TGO units are ``<id> | <type>``, aircraft are ``<flight>|<pkg>|<n>|<type>|
Pilot #N``), so a results file can only be submitted against the save that
generated the flown ``.miz``. When the campaign is REGENERATED (new build, new
laydown -- e.g. Red Tide's Friday-night rebuild), every TheaterUnit id and ATO
flight name shifts and the flown results no longer bind: the mission plays out
against one save, but the season needs its outcome applied to another.

This tool re-binds the results. It loads the SOURCE save (the one that
generated the flown mission), the flown ``state.json``, and the TARGET save
(the fresh regeneration), generates a throwaway mission from the target save to
obtain a live UnitMap, and translates every kill event into the target game's
namespace:

- **TGO/theater units** (``NNNN | <name>``, incl. ``... object`` statics):
  resolved in the source save, matched to the nearest same-named unit in the
  target UnitMap (position + name match; each target unit consumed once). A
  unit type the new laydown no longer fields falls back to the nearest
  same-side unit of the same unit CLASS within 30 km, so the attrition still
  lands on the right side. Culling is disabled for the throwaway generation
  (the miz is never flown) so every TGO is spawnable/debriefable regardless of
  how the new ATO's cull zones fall.
- **Aircraft** (``<label>|<country>|<n>|<type>| Pilot #N``): matched by task
  label + airframe against the target ATO's generated flights, AI-crewed units
  first, so squadron attrition lands on the same squadrons flying the same
  jobs. Kills the new ATO fields no flight for are **debited directly** from a
  matching squadron (owned -1, destroyed +1, one non-player pilot killed) --
  the same accounting ``commit_air_losses`` performs -- so a lopsided mission
  (more red jets died than the new ATO flies) still carries its full attrition.
- **Front-line units** (``unit|...| Unit #N``) and **TIC clones**
  (``TIC:unit|...-N#NNN-NN``): matched by unit-type token against the target
  front line, falling back to any unconsumed same-side front-line unit (the
  name embeds the DCS country id). A front thinner than the kill count drops
  the overflow -- you cannot kill more units than exist -- and reports it.
- **QRA intercept survivors**: squadron-UUID keys are remapped by home base +
  airframe, preserving the LOSS count against the target game's own fielded
  QRA (``new_survivors = new_fielded - old_losses``).
- Numeric map-object ids and ``destroyed_objects_positions`` pass through
  unchanged (scenery ids/positions are theater-stable). Any untranslatable
  name that happens to collide with a real target-game unit name is prefixed
  ``UNMAPPED|`` so it cannot kill an unrelated unit by coincidence.

It then runs the real pipeline -- ``Debriefing`` -> ``MissionResultsProcessor
.commit`` -> ``Game.pass_turn`` -- and writes the processed save, exactly as if
the results had been accepted in the app.

Usage (full apply; paths quoted because of spaces)::

    .venv\\Scripts\\python.exe tools/apply_state_json.py ^
        --source-save "C:\\...\\Saves\\414th red tide v5 6pm lock.retribution" ^
        --state "C:\\...\\DCS\\Missions\\state.json" ^
        --target-save "C:\\...\\Saves\\turn 0.retribution" ^
        --out-save "C:\\...\\Saves\\red tide new laydown TURN 2.retribution"

``--translate-only --miz <generated.miz> --out-json <path>`` skips the
processing and only writes a translated state.json bound to a miz the APP
generated (press TAKE OFF first, don't regenerate afterwards), for the
"Manually Submit" flow. In that mode client-seat detection is unavailable, so
an air kill may land on a player-crewed jet (``invulnerable_player_pilots``
still protects the pilot).

Note: ``pass_turn`` autosaves, so ``autosave.retribution`` is rewritten too.
"""

from __future__ import annotations

import argparse
import itertools
import json
import logging
import re
import sys
import tempfile
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Optional, TYPE_CHECKING

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR.parent))

if TYPE_CHECKING:
    from game import Game
    from game.squadrons.squadron import Squadron
    from game.unitmap import UnitMap

#: A TIC (Troops In Contact) respawn clone: "<original group name>-<idx>#<NNN>-<NN>"
#: (kept in sync with game.unitmap.TIC_CLONE_NAME; duplicated so the parse helpers
#: stay importable without the full game package).
TIC_CLONE_NAME = re.compile(r"^(?P<group>.+?)(?:-\d+#\d{3})+-\d{2}$")

#: A generated theater-ground-object unit name: "NNNN | <unit name>".
TGO_UNIT_NAME = re.compile(r"^\d{3,} \| ")

#: Suffix pydcs statics carry on top of the TheaterUnit name.
STATIC_SUFFIX = " object"


# --- pure name parsing (unit-testable, no game objects) ---------------------


def parse_pilot_unit_name(name: str) -> Optional[tuple[str, str]]:
    """(task label, airframe token) for '<label>|<pkg>|<n>|<type>| Pilot #N'."""
    parts = name.split("|")
    if len(parts) < 4 or not parts[-1].startswith(" Pilot #"):
        return None
    if parts[0] in ("unit", "TIC:unit", "Intercept"):
        return None
    return parts[0], parts[-2]


def parse_front_line_unit_name(name: str) -> Optional[str]:
    """Unit-type token for 'unit|...|<type>| Unit #N' (TIC:-prefixed included)."""
    parts = name.split("|")
    if len(parts) < 3 or not parts[-1].startswith(" Unit #"):
        return None
    if parts[0] not in ("unit", "TIC:unit"):
        return None
    return parts[-2]


def parse_tic_clone_name(name: str) -> Optional[str]:
    """Unit-type token for a TIC respawn clone of a front-line (sub)group."""
    match = TIC_CLONE_NAME.match(name)
    if match is None:
        return None
    group = match.group("group")
    if not group.startswith(("unit|", "TIC:unit|")):
        return None
    segments = [s for s in group.split("|") if s]
    if len(segments) < 2:
        return None
    return segments[-1]


# --- target-side pools -------------------------------------------------------


@dataclass
class AircraftEntry:
    name: str
    label: str
    unit_type: str
    client: bool
    used: bool = False


@dataclass
class FrontLineEntry:
    name: str
    token: str  # unit-type token from the generated name
    side: Optional[str]  # "blue"/"red" from the embedded DCS country id
    used: bool = False


@dataclass
class TgoEntry:
    name: str  # the debrief-lookup key (statics carry the " object" suffix)
    human_name: str  # TheaterUnit.name
    position: Any  # Point
    side: Optional[str] = None  # "blue"/"red" ownership
    unit_class: Optional[Any] = None  # UnitClass when known (vehicles/ships)
    used: bool = False


@dataclass
class TargetPools:
    aircraft: list[AircraftEntry] = field(default_factory=list)
    front_line: list[FrontLineEntry] = field(default_factory=list)
    tgos: list[TgoEntry] = field(default_factory=list)
    #: Every name the target debrief could resolve (collision guard); airfield
    #: names are deliberately absent -- they are theater-stable and SHOULD
    #: resolve (a dead "Haina" event is a runway strike carrying over as-is).
    known_names: set[str] = field(default_factory=set)


def front_line_side(name: str, side_of_country: dict[int, str]) -> Optional[str]:
    """Side of a generated front-line name via its embedded DCS country id."""
    parts = name.split("|")
    if len(parts) < 2:
        return None
    try:
        return side_of_country.get(int(parts[1]))
    except ValueError:
        return None


def side_of_country_map(*games: Game) -> dict[int, str]:
    mapping: dict[int, str] = {}
    for game in games:
        mapping.setdefault(game.blue.faction.country.id, "blue")
        mapping.setdefault(game.red.faction.country.id, "red")
    return mapping


def _tgo_unit_side(unit: Any) -> Optional[str]:
    try:
        coalition = unit.ground_object.control_point.coalition
    except AttributeError:
        return None
    return "blue" if coalition.player.is_blue else "red"


def _tgo_unit_class(unit: Any) -> Optional[Any]:
    unit_type = unit.unit_type
    return unit_type.unit_class if unit_type is not None else None


def pools_from_unit_map(
    unit_map: UnitMap, side_of_country: dict[int, str]
) -> TargetPools:
    pools = TargetPools()
    for name, flying in unit_map.aircraft.items():
        parsed = parse_pilot_unit_name(name)
        if parsed is None:
            continue
        label, unit_type = parsed
        client = flying.pilot is not None and flying.pilot.player
        pools.aircraft.append(AircraftEntry(name, label, unit_type, client))
    for name in unit_map.front_line_units:
        token = parse_front_line_unit_name(name)
        if token is not None:
            pools.front_line.append(
                FrontLineEntry(name, token, front_line_side(name, side_of_country))
            )
    for name, mapping in unit_map.theater_objects.items():
        unit = mapping.theater_unit
        pools.tgos.append(
            TgoEntry(
                name,
                unit.name,
                unit.position,
                _tgo_unit_side(unit),
                _tgo_unit_class(unit),
            )
        )
    # Scenery strike targets (authored map buildings, e.g. the Red Tide IADS
    # comms/power buildings) kill via a dead-zone trigger whose event name is
    # the TRIGGER ZONE name, and resolve through unit_map.scenery_objects.
    for zone_name, scenery in unit_map.scenery_objects.items():
        unit = scenery.ground_unit
        pools.tgos.append(
            TgoEntry(zone_name, unit.name, unit.position, _tgo_unit_side(unit), None)
        )
    pools.known_names = (
        set(unit_map.aircraft)
        | set(unit_map.front_line_units)
        | set(unit_map.motorpool_units)
        | set(unit_map.theater_objects)
        | set(unit_map.scenery_objects)
        | set(unit_map.convoys)
        | set(unit_map.cargo_ships)
        | set(unit_map.airlifts)
    )
    return pools


def pools_from_miz(
    miz_path: Path, target_game: Game, side_of_country: dict[int, str]
) -> TargetPools:
    """Best-effort pools for --translate-only: names regexed from the miz.

    Client seats can't be told apart here, and TGO entries come from the save
    (cross-checked against the miz text so a culled site is not offered).
    """
    with zipfile.ZipFile(miz_path) as miz:
        text = miz.read("mission").decode("utf-8", errors="replace")
    names = re.findall(r'\["name"\]="((?:[^"\\]|\\.)*)"', text)
    pools = TargetPools()
    for name in names:
        parsed = parse_pilot_unit_name(name)
        if parsed is not None:
            label, unit_type = parsed
            pools.aircraft.append(AircraftEntry(name, label, unit_type, client=False))
            continue
        token = parse_front_line_unit_name(name)
        if token is not None:
            pools.front_line.append(
                FrontLineEntry(name, token, front_line_side(name, side_of_country))
            )
    in_miz = set(names)
    for unit in _iter_theater_units(target_game):
        if not unit.alive:
            continue
        for candidate in (unit.unit_name, unit.unit_name + STATIC_SUFFIX):
            if candidate in in_miz:
                pools.tgos.append(
                    TgoEntry(
                        candidate,
                        unit.name,
                        unit.position,
                        _tgo_unit_side(unit),
                        _tgo_unit_class(unit),
                    )
                )
    pools.known_names = in_miz
    return pools


def _iter_theater_units(game: Game) -> Iterator[Any]:
    for cp in game.theater.controlpoints:
        for tgo in cp.connected_objectives:
            for group in tgo.groups:
                yield from group.units


# --- translation -------------------------------------------------------------


@dataclass
class TranslationReport:
    tgo_mapped: list[tuple[str, str, float]] = field(default_factory=list)
    tgo_class_fallback: list[tuple[str, str, float]] = field(default_factory=list)
    tgo_unmapped: list[str] = field(default_factory=list)
    air_mapped: list[tuple[str, str]] = field(default_factory=list)
    air_unmapped: list[str] = field(default_factory=list)
    air_debits: list[str] = field(default_factory=list)
    front_mapped: list[tuple[str, str]] = field(default_factory=list)
    front_side_fallback: list[tuple[str, str]] = field(default_factory=list)
    front_unmapped: list[str] = field(default_factory=list)
    qra_lines: list[str] = field(default_factory=list)
    passthrough: list[str] = field(default_factory=list)
    collision_guarded: list[str] = field(default_factory=list)
    numeric_events: int = 0

    def print(self) -> None:
        print(f"\n=== Translation report ===")
        print(
            f"TGO units: {len(self.tgo_mapped)} mapped, "
            f"{len(self.tgo_class_fallback)} class-fallback, "
            f"{len(self.tgo_unmapped)} unmapped"
        )
        for old, new, dist in sorted(self.tgo_mapped):
            print(f"  {old}  ->  {new}  ({dist:.0f} m)")
        for old, new, dist in sorted(self.tgo_class_fallback):
            print(f"  CLASS FALLBACK: {old}  ->  {new}  ({dist:.0f} m)")
        for old in sorted(self.tgo_unmapped):
            print(f"  UNMAPPED: {old}")
        print(
            f"Aircraft: {len(self.air_mapped)} mapped, "
            f"{len(self.air_unmapped)} unmapped (see squadron debits)"
        )
        for old, new in sorted(self.air_mapped):
            print(f"  {old}  ->  {new}")
        for old in sorted(self.air_unmapped):
            print(f"  UNMAPPED: {old}")
        if self.air_debits:
            print("Direct squadron debits for unmapped air kills:")
            for line in self.air_debits:
                print(f"  {line}")
        print(
            f"Front line: {len(self.front_mapped)} mapped, "
            f"{len(self.front_side_fallback)} side-fallback, "
            f"{len(self.front_unmapped)} dropped (front thinner than kill count)"
        )
        front_counts: dict[str, int] = defaultdict(int)
        for old, _new in self.front_mapped:
            token = parse_front_line_unit_name(old) or parse_tic_clone_name(old) or old
            front_counts[token] += 1
        for token, count in sorted(front_counts.items()):
            print(f"  {token} x{count}")
        for old, new in sorted(self.front_side_fallback):
            print(f"  SIDE FALLBACK: {old}  ->  {new}")
        for old in sorted(self.front_unmapped):
            print(f"  DROPPED: {old}")
        print("QRA intercept survivors:")
        for line in self.qra_lines:
            print(f"  {line}")
        print(
            f"Passed through unchanged: {self.numeric_events} numeric map-object "
            f"events + {len(self.passthrough)} unrecognized names"
        )
        for name in sorted(set(self.passthrough)):
            print(f"  passthrough: {name}")
        for name in sorted(set(self.collision_guarded)):
            print(f"  collision-guarded (prefixed UNMAPPED|): {name}")


#: An exact same-type match closer than this is always preferred; beyond it a
#: nearby same-class unit beats a far same-type one.
NEAR_MATCH_M = 30_000

#: How far a class-fallback TGO match may sit from the original kill.
CLASS_FALLBACK_RANGE_M = 100_000


class StateTranslator:
    def __init__(
        self,
        source_units_by_name: dict[str, Any],
        pools: TargetPools,
        side_of_country: dict[int, str],
    ) -> None:
        self.source_units = source_units_by_name
        self.pools = pools
        self.side_of_country = side_of_country
        self.report = TranslationReport()
        self._memo: dict[str, str] = {}

    def translate_events(self, data: dict[str, Any]) -> dict[str, Any]:
        # Pre-resolve every distinct killed-unit name in phases so an exact
        # match is never starved by an earlier kill's fallback (e.g. a dead
        # infantry clone side-falling back onto the only BTR-70 while a real
        # BTR-70 kill is still to come).
        names: list[str] = []
        seen: set[str] = set()
        for key in ("dead_events", "kill_events", "unit_lost_events", "crash_events"):
            for event in data.get(key, []):
                if isinstance(event, str) and event not in seen:
                    seen.add(event)
                    names.append(event)
        self._resolve_names(names)

        out = dict(data)
        for key in ("dead_events", "kill_events", "unit_lost_events", "crash_events"):
            events = data.get(key, [])
            translated: list[Any] = []
            for event in events:
                if isinstance(event, str):
                    translated.append(self._translate_name(event))
                else:
                    self.report.numeric_events += 1
                    translated.append(event)
            out[key] = translated
        out["combat_sar_rescues"] = [
            self._translate_name(n) if isinstance(n, str) else n
            for n in data.get("combat_sar_rescues", [])
        ]
        for key in ("combat_sar_captures", "combat_sar_survivors"):
            entries = []
            for entry in data.get(key, []):
                if isinstance(entry, dict) and isinstance(entry.get("unit"), str):
                    entry = dict(entry)
                    entry["unit"] = self._translate_name(entry["unit"])
                entries.append(entry)
            out[key] = entries
        return out

    def _resolve_names(self, names: list[str]) -> None:
        front_line: list[tuple[str, str]] = []
        aircraft: list[str] = []
        for name in names:
            # QRA clones are accounted through intercept_survivors, never by name.
            if name.startswith("Intercept|"):
                self.report.passthrough.append(name)
                self._memo[name] = self._guard(name)
            elif TGO_UNIT_NAME.match(name):
                self._memo[name] = self._translate_tgo(name)
            elif parse_pilot_unit_name(name) is not None:
                aircraft.append(name)
            else:
                token = parse_front_line_unit_name(name) or parse_tic_clone_name(name)
                if token is not None:
                    front_line.append((name, token))
                else:
                    self.report.passthrough.append(name)
                    self._memo[name] = self._guard(name)
        self._resolve_aircraft(aircraft)
        self._resolve_front_line(front_line)

    def _translate_name(self, name: str) -> str:
        if name in self._memo:
            return self._memo[name]
        # Names outside the killed-unit arrays (combat SAR entries) resolve
        # against the memo built by _resolve_names; anything new passes through.
        self.report.passthrough.append(name)
        result = self._guard(name)
        self._memo[name] = result
        return result

    def _guard(self, name: str) -> str:
        """Prevent an untranslated name from killing an unrelated target unit.

        Old names can coincidentally exist in the new game (id collisions,
        identical group numbering). Airfield names are exempt -- they are
        theater-stable and a dead airfield event IS the runway strike.
        """
        if name in self.pools.known_names:
            self.report.collision_guarded.append(name)
            return f"UNMAPPED|{name}"
        return name

    def _translate_tgo(self, name: str) -> str:
        is_static = name.endswith(STATIC_SUFFIX)
        base = name[: -len(STATIC_SUFFIX)] if is_static else name
        source = self.source_units.get(name) or self.source_units.get(base)
        if source is None:
            self.report.tgo_unmapped.append(f"{name} (not in source save)")
            return self._guard(name)
        # Nearby exact type first; beyond NEAR_MATCH_M a close same-class unit
        # beats a same-type unit on the other side of the map (the attrition
        # should land near where the strike actually happened when possible).
        exact = self._nearest_tgo(lambda e: e.human_name == source.name, source)
        if exact is not None and self._dist(exact, source) <= NEAR_MATCH_M:
            return self._take_tgo(name, exact, source, self.report.tgo_mapped)
        side = _tgo_unit_side(source)
        unit_class = _tgo_unit_class(source)
        fallback = None
        if side is not None and unit_class is not None:
            fallback = self._nearest_tgo(
                lambda e: e.side == side
                and e.unit_class is unit_class
                and self._dist(e, source) <= CLASS_FALLBACK_RANGE_M,
                source,
            )
        if fallback is not None and (
            exact is None or self._dist(fallback, source) < self._dist(exact, source)
        ):
            return self._take_tgo(
                name, fallback, source, self.report.tgo_class_fallback
            )
        if exact is not None:
            return self._take_tgo(name, exact, source, self.report.tgo_mapped)
        self.report.tgo_unmapped.append(f"{name} (no free '{source.name}' in target)")
        return self._guard(name)

    @staticmethod
    def _dist(entry: TgoEntry, source: Any) -> float:
        return entry.position.distance_to_point(source.position)

    def _take_tgo(
        self,
        name: str,
        entry: TgoEntry,
        source: Any,
        report_list: list[tuple[str, str, float]],
    ) -> str:
        entry.used = True
        report_list.append((name, entry.name, self._dist(entry, source)))
        return entry.name

    def _nearest_tgo(self, predicate: Any, source: Any) -> Optional[TgoEntry]:
        best: Optional[TgoEntry] = None
        best_dist = 0.0
        for entry in self.pools.tgos:
            if entry.used or not predicate(entry):
                continue
            dist = self._dist(entry, source)
            if best is None or dist < best_dist:
                best, best_dist = entry, dist
        return best

    def _resolve_aircraft(self, names: list[str]) -> None:
        """Assign air kills tier by tier so a weaker match never starves a
        later kill's exact one."""
        parsed = {n: parse_pilot_unit_name(n) for n in names}
        tiers = [
            lambda e, label, ut: e.label == label
            and e.unit_type == ut
            and not e.client,
            lambda e, label, ut: e.unit_type == ut and not e.client,
            lambda e, label, ut: e.label == label and e.unit_type == ut,
            lambda e, label, ut: e.unit_type == ut,
        ]
        pending = list(names)
        for tier in tiers:
            still: list[str] = []
            for name in pending:
                label, unit_type = parsed[name]  # type: ignore[misc]
                entry = next(
                    (
                        e
                        for e in self.pools.aircraft
                        if not e.used and tier(e, label, unit_type)
                    ),
                    None,
                )
                if entry is None:
                    still.append(name)
                    continue
                entry.used = True
                self.report.air_mapped.append((name, entry.name))
                self._memo[name] = entry.name
            pending = still
        for name in pending:
            self.report.air_unmapped.append(name)
            self._memo[name] = self._guard(name)

    def _resolve_front_line(self, kills: list[tuple[str, str]]) -> None:
        """Exact unit-type matches for every kill first, then side fallbacks."""
        pending: list[tuple[str, str]] = []
        for name, token in kills:
            entry = next(
                (e for e in self.pools.front_line if not e.used and e.token == token),
                None,
            )
            if entry is None:
                pending.append((name, token))
                continue
            entry.used = True
            self.report.front_mapped.append((name, entry.name))
            self._memo[name] = entry.name
        for name, _token in pending:
            side = front_line_side(
                name[len("TIC:") :] if name.startswith("TIC:") else name,
                self.side_of_country,
            )
            entry = None
            if side is not None:
                entry = next(
                    (e for e in self.pools.front_line if not e.used and e.side == side),
                    None,
                )
            if entry is None:
                self.report.front_unmapped.append(name)
                self._memo[name] = self._guard(name)
                continue
            entry.used = True
            self.report.front_side_fallback.append((name, entry.name))
            self._memo[name] = entry.name


def remap_intercept_survivors(
    survivors: dict[str, Any],
    source_game: Game,
    target_game: Game,
    report: TranslationReport,
) -> dict[str, int]:
    """Rewrite squadron-UUID keys, preserving each squadron's LOSS count.

    ``reconcile_intercept_losses`` computes fielded - survivors against the
    TARGET game's own fielded QRA, so the survivor value must be re-derived:
    new_survivors = new_fielded - old_losses.
    """
    from game.missiongenerator.interceptattrition import fielded_qra_by_squadron

    def all_squadrons(game: Game) -> Iterator[Squadron]:
        return itertools.chain(
            game.blue.air_wing.iter_squadrons(), game.red.air_wing.iter_squadrons()
        )

    src_fielded, src_squadrons = fielded_qra_by_squadron(all_squadrons(source_game))
    tgt_fielded, tgt_squadrons = fielded_qra_by_squadron(all_squadrons(target_game))
    all_source = {str(s.id): s for s in all_squadrons(source_game)}

    result: dict[str, int] = {}
    for old_id, raw_survivors in survivors.items():
        squadron = src_squadrons.get(str(old_id))
        if squadron is None:
            known = all_source.get(str(old_id))
            if known is not None:
                report.qra_lines.append(
                    f"SKIPPED {known} @ {known.location.name}: fielded no AI QRA "
                    f"in the source save (player-manned or no reserve); "
                    f"survivors={raw_survivors} carries no loss"
                )
            else:
                report.qra_lines.append(
                    f"DROPPED {old_id}={raw_survivors}: unknown squadron in source save"
                )
            continue
        fielded = src_fielded[str(old_id)]
        losses = fielded - max(0, min(int(raw_survivors), fielded))
        base = squadron.location.name
        airframe = squadron.aircraft.variant_id
        candidates = [
            s
            for s in tgt_squadrons.values()
            if s.location.name == base and s.aircraft.variant_id == airframe
        ] or [s for s in tgt_squadrons.values() if s.location.name == base]
        candidates = [s for s in candidates if str(s.id) not in result]
        if not candidates:
            report.qra_lines.append(
                f"DROPPED {squadron} @ {base}: no matching QRA squadron in target "
                f"(would have carried {losses} losses)"
            )
            continue
        target = candidates[0]
        new_id = str(target.id)
        new_fielded = tgt_fielded[new_id]
        result[new_id] = max(0, new_fielded - losses)
        report.qra_lines.append(
            f"{squadron} @ {base} ({airframe}): {losses} losses -> {target} "
            f"(fielded {new_fielded}, survivors {result[new_id]})"
        )
    return result


def debit_unmapped_air_losses(
    target_game: Game,
    unmapped: list[str],
    report: TranslationReport,
) -> None:
    """Charge air kills the new ATO fields no flight for straight to squadrons.

    Mirrors the accounting ``commit_air_losses`` performs per loss: one owned
    airframe out, one destroyed in, one (never player) pilot killed. Squadron
    choice: same airframe variant, preferring a squadron whose home base
    appears in the old flight's task label, then the one with the most
    airframes left.
    """
    squadrons = list(target_game.blue.air_wing.iter_squadrons()) + list(
        target_game.red.air_wing.iter_squadrons()
    )
    for name in unmapped:
        parsed = parse_pilot_unit_name(name)
        if parsed is None:
            continue
        label, unit_type = parsed
        candidates = [
            s
            for s in squadrons
            if s.aircraft.variant_id == unit_type and s.owned_aircraft > 0
        ]
        if not candidates:
            report.air_debits.append(f"NO SQUADRON with {unit_type} left for: {name}")
            continue
        based = [s for s in candidates if s.location.name in label]
        pick = max(based or candidates, key=lambda s: s.owned_aircraft)
        pick.owned_aircraft -= 1
        pick.destroyed_aircraft += 1
        pilot = next((p for p in pick.active_pilots if not p.player), None)
        if pilot is not None:
            pilot.kill()
        report.air_debits.append(
            f"{name}  =>  {pick} @ {pick.location.name} "
            f"(-1 airframe{'' if pilot is None else ', pilot KIA'})"
        )


# --- driver ------------------------------------------------------------------


def build_source_unit_index(game: Game) -> dict[str, Any]:
    index: dict[str, Any] = {}
    for unit in _iter_theater_units(game):
        index[unit.unit_name] = unit
    return index


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--source-save", required=True, type=Path)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--target-save", required=True, type=Path)
    parser.add_argument(
        "--out-save",
        type=Path,
        help="Processed save to write (required unless --translate-only).",
    )
    parser.add_argument(
        "--out-json",
        type=Path,
        help="Where to write the translated state.json (optional in full mode).",
    )
    parser.add_argument(
        "--saved-games",
        type=Path,
        default=Path.home() / "Saved Games" / "DCS",
        help="DCS saved-games root for persistency.setup.",
    )
    parser.add_argument(
        "--translate-only",
        action="store_true",
        help="Only write the translated JSON (for the app's Manually Submit flow).",
    )
    parser.add_argument(
        "--miz",
        type=Path,
        help="With --translate-only: the miz the APP generated from the target save.",
    )
    parser.add_argument(
        "--keep-miz",
        type=Path,
        help="Full mode: keep the throwaway generated miz at this path.",
    )
    args = parser.parse_args()

    if args.translate_only:
        if args.miz is None or args.out_json is None:
            parser.error("--translate-only requires --miz and --out-json")
    elif args.out_save is None:
        parser.error("--out-save is required (or pass --translate-only)")

    logging.basicConfig(level=logging.WARNING)

    from game import persistency

    persistency.setup(str(args.saved_games), False, 16880)

    source_game = persistency.load_game(str(args.source_save))
    if source_game is None:
        print(f"ERROR: could not load source save {args.source_save}")
        return 1
    target_game = persistency.load_game(str(args.target_save))
    if target_game is None:
        print(f"ERROR: could not load target save {args.target_save}")
        return 1
    with args.state.open(encoding="utf-8") as f:
        data = json.load(f)

    print(
        f"Source: {args.source_save.name} (turn {source_game.turn}) -> "
        f"Target: {args.target_save.name} (turn {target_game.turn})"
    )

    side_of_country = side_of_country_map(source_game, target_game)
    unit_map = None
    if args.translate_only:
        pools = pools_from_miz(args.miz, target_game, side_of_country)
    else:
        from game.sim.missionsimulation import MissionSimulation

        miz_path = args.keep_miz or Path(tempfile.gettempdir()) / "apply_state_json.miz"
        print(f"Generating mission from target save (unit map) -> {miz_path} ...")
        # begin_simulation initializes every flight's sim state, which the
        # spawner reads for start types -- the same order the app's game loop
        # uses (start -> generate). Culling is disabled for the throwaway
        # generation so every TGO the results might reference is spawned and
        # debriefable (the miz is never flown); restored before the save.
        culling = target_game.settings.perf_culling
        target_game.settings.perf_culling = False
        try:
            sim = MissionSimulation(target_game)
            sim.begin_simulation()
            sim.generate_miz(miz_path)
        finally:
            target_game.settings.perf_culling = culling
        unit_map = sim.unit_map
        assert unit_map is not None
        pools = pools_from_unit_map(unit_map, side_of_country)

    translator = StateTranslator(
        build_source_unit_index(source_game), pools, side_of_country
    )
    translated = translator.translate_events(data)
    translated["intercept_survivors"] = remap_intercept_survivors(
        data.get("intercept_survivors", {}) or {},
        source_game,
        target_game,
        translator.report,
    )

    if args.out_json is not None:
        with args.out_json.open("w", encoding="utf-8") as f:
            json.dump(translated, f, indent=1)
        print(f"\nTranslated state written to {args.out_json}")

    if args.translate_only:
        translator.report.print()
        print(
            "\nNext: with the app waiting on this mission (do NOT regenerate), use "
            "'Manually Submit' and pick the translated JSON. Air kills the target "
            "ATO fields no flight for are NOT debited in this mode."
        )
        return 0

    from game.debriefing import Debriefing
    from game.sim import GameUpdateEvents
    from game.sim.missionresultsprocessor import MissionResultsProcessor
    from game.theater import Player

    translated["mission_ended"] = True
    assert unit_map is not None
    debriefing = Debriefing(translated, target_game, unit_map)

    print("\n=== Debrief (as the app would show it) ===")
    for side, player in (("BLUE", Player.BLUE), ("RED", Player.RED)):
        losses = debriefing.loss_counts(player)
        print(
            f"{side}: aircraft={losses.aircraft} front_line={losses.front_line} "
            f"convoy={losses.convoy} ground_objects={losses.ground_objects} "
            f"scenery={losses.scenery} bases_lost={losses.bases_lost} "
            f"runways={losses.runways_destroyed}"
        )
        by_type = debriefing.aircraft_losses_by_type(player)
        for unit_type, count in sorted(
            by_type.items(), key=lambda kv: kv[0].variant_id
        ):
            print(f"    {unit_type.variant_id} x{count}")

    print("\nCommitting results and passing the turn ...")
    MissionResultsProcessor(target_game).commit(debriefing, GameUpdateEvents())
    debit_unmapped_air_losses(
        target_game, translator.report.air_unmapped, translator.report
    )
    translator.report.print()
    target_game.pass_turn()

    if not persistency.save_game(target_game, str(args.out_save)):
        print("ERROR: failed to write the processed save")
        return 1
    print(f"\nDone. Processed save written to {args.out_save}")
    print("(pass_turn also rewrote autosave.retribution, as the app does.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
