"""Doctrine-mining row 4: do AI helo routes cross open water?

The doctrine line is "route helos over land, never open water" -- nap-of-earth
masks a helo in ground clutter, and over sea it is engaged like any other
contact.

STEP 2, BOTH HALVES, because skipping the second half is what closed #978.

  Does the planner do it? No. `game/navmesh.py` contains **zero** references to
  land, sea or water: `NavMesh.from_threat_zones` builds its polygons from threat
  zones and `shortest_path` costs them by distance and threat alone. Nothing in
  `WaypointBuilder.nav_path` consults the landmap.

  Is the outcome achieved by something else? No, and this is the part worth
  writing down. Three things in the tree touch land vs water near routing and
  none of them moves a route:
    * `PydcsWaypointBuilder.switch_to_baro_if_in_sea` flips a RADIO (AGL)
      waypoint to BARO over water. That fixes the ALTITUDE REFERENCE, not the
      exposure -- the helo is still over open sea, just measured from the
      surface instead of terrain.
    * `AirAssaultFlightPlan` snaps the drop-off onto land via
      `nearest_land_pos`, bounded so an island map does not teleport the LZ.
      That is the destination, not the route to it.
    * The front-line model masks the FLOT to drivable land
      (`frontlineconflictdescription`). That is ground placement, not flight
      routing.
  So the exposure the doctrine line is about is genuinely unhandled. Whether it
  HAPPENS is what this counts.

POPULATION -- only flights for which a land route plausibly exists:
  * helicopters only;
  * departure and arrival both non-fleet (a helo off an LHA has no land route);
  * the package target not over water (naval targets, and a pilot in the drink);
  * CSAR excluded outright -- a rescue goes where the survivor is.
The first and last NEAR_FIELD_SKIP of each route are ignored so a helo lifting
from a coastal pad is not counted as crossing an ocean.

PRE-REGISTERED THRESHOLDS, written before the first run. The verdict comes from
A and B only; C is context and is deliberately NOT a verdict input, because a
sensible bar for it cannot be set without seeing data and inventing one
afterwards is what cost row 3 its pre-registration.

  A  share of qualifying helo flights with any water on route
  B  median longest continuous over-water run among those flights
  C  (context) over-water distance falling inside enemy radar-SAM threat

  DEFECT    A >= 15% AND B >= 5 NM. Five miles is roughly two minutes in the
            open at helo speed -- long enough to be worth routing around.
  ROW DIES  A < 5%, or B < 2 NM (coastal clipping, not a crossing).
  GREY      anything else -- report, build nothing, hand it back.

  Minimum sample: 15 qualifying flights across all saves. Below that neither
  number is quotable.

A theater with no landmap answers `is_in_sea` False everywhere, so those saves
are skipped rather than counted as all-land.

The harness MIGRATES each save, as the app's load path does and
`persistency.load_game` does not (the row 6 lesson).

Sibling of `tools/measure_tot_past_mission_window.py`.
Procedure: `docs/dev/design/414th-planner-doctrine-mining-notes.md`.

Run (several saves pool into one verdict, which is how the threshold is read):
    python tools/measure_helo_water_routing.py <save.retribution>... [--turns 3]
"""

from __future__ import annotations

import argparse
import logging
import statistics
import sys
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from game import persistency  # noqa: E402
from game.ato.flighttype import FlightType  # noqa: E402
from game.migrator import Migrator  # noqa: E402

METRES_PER_NM = 1852.0
#: Sampling pitch along each route leg.
SAMPLE_NM = 0.5
#: Route distance ignored at each end, so a coastal pad is not a sea crossing.
NEAR_FIELD_SKIP_NM = 1.0
MIN_SAMPLE = 15


def qualifies(flight: Any, theater: Any) -> bool:
    """Only flights for which a land route plausibly exists."""
    if not flight.is_helo:
        return False
    if flight.flight_type is FlightType.CSAR:
        return False
    if getattr(flight.departure, "is_fleet", False):
        return False
    if getattr(flight.arrival, "is_fleet", False):
        return False
    target = getattr(flight.package, "target", None)
    position = getattr(target, "position", None)
    if position is not None and theater.is_in_sea(position):
        return False
    return True


def route_points(flight: Any) -> list[Any]:
    waypoints = getattr(flight.flight_plan, "waypoints", None) or []
    return [w.position for w in waypoints if getattr(w, "position", None) is not None]


def water_runs(points: list[Any], theater: Any) -> tuple[list[float], float, float]:
    """Continuous over-water runs in NM, total route NM, and max NM from land.

    Walks the polyline at a fixed pitch, dropping the near-field at each end.
    "Max from land" is approximated by the half-length of the longest run, which
    is what a straight crossing gives and is never an over-estimate for a run
    that hugs a coast.
    """
    samples: list[tuple[float, bool]] = []
    travelled = 0.0
    for a, b in zip(points, points[1:]):
        leg = a.distance_to_point(b) / METRES_PER_NM
        if leg <= 0:
            continue
        steps = max(1, int(leg / SAMPLE_NM))
        for i in range(steps):
            frac = i / steps
            point = a.lerp(b, frac)
            samples.append((travelled + leg * frac, theater.is_in_sea(point)))
        travelled += leg

    if travelled <= 2 * NEAR_FIELD_SKIP_NM:
        return [], travelled, 0.0

    runs: list[float] = []
    current: Optional[float] = None
    last = 0.0
    for distance, wet in samples:
        if distance < NEAR_FIELD_SKIP_NM or distance > travelled - NEAR_FIELD_SKIP_NM:
            continue
        if wet:
            if current is None:
                current = distance
            last = distance
        elif current is not None:
            runs.append(last - current)
            current = None
    if current is not None:
        runs.append(last - current)
    runs = [r for r in runs if r > 0]
    return runs, travelled, (max(runs) / 2 if runs else 0.0)


def threatened_water_nm(points: list[Any], theater: Any, zones: Any) -> float:
    """Context measure C: over-water NM inside the enemy radar-SAM threat."""
    total = 0.0
    for a, b in zip(points, points[1:]):
        leg = a.distance_to_point(b) / METRES_PER_NM
        steps = max(1, int(leg / SAMPLE_NM))
        for i in range(steps):
            point = a.lerp(b, i / steps)
            if not theater.is_in_sea(point):
                continue
            try:
                if zones.threatened_by_radar_sam(point):
                    total += leg / steps
            except Exception:  # a zone test that will not take a bare point
                return 0.0
    return total


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("save", nargs="+")
    parser.add_argument("--turns", type=int, default=3)
    parser.add_argument(
        "--saved-games",
        default=str(Path.home() / "Saved Games" / "DCS"),
        help="DCS user folder persistency needs before a save will load.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.ERROR)
    persistency.setup(args.saved_games, True, 16880)

    from game.sim import GameUpdateEvents

    rows: list[dict[str, Any]] = []
    for save in args.save:
        game = persistency.load_game(save)
        if game is None:
            print(f"could not load {save}")
            continue
        Migrator(game, False)
        theater = game.theater
        print()
        print(f"save: {save}")
        if theater.landmap is None:
            print("  no landmap -- is_in_sea answers False everywhere. Skipped.")
            continue

        for step in range(1, args.turns + 1):
            game.initialize_turn(GameUpdateEvents(), for_red=True, for_blue=True)
            for label, coalition in (("red", game.red), ("blue", game.blue)):
                zones = game.threat_zone_for(coalition.player.opponent)
                seen = wet = 0
                for package in coalition.ato.packages:
                    for flight in package.flights:
                        if not qualifies(flight, theater):
                            continue
                        points = route_points(flight)
                        if len(points) < 2:
                            continue
                        seen += 1
                        runs, total, from_land = water_runs(points, theater)
                        if not runs:
                            rows.append({"wet": False})
                            continue
                        wet += 1
                        rows.append(
                            {
                                "wet": True,
                                "task": flight.flight_type.value,
                                "longest": max(runs),
                                "total_wet": sum(runs),
                                "route": total,
                                "from_land": from_land,
                                "threatened": threatened_water_nm(
                                    points, theater, zones
                                ),
                            }
                        )
                if seen:
                    print(
                        f"  turn {step} {label:4s}: {seen:3d} qualifying helo flights, "
                        f"{wet:3d} with water on route"
                    )
            if step < args.turns:
                try:
                    game.pass_turn(no_action=True)
                except Exception as exc:
                    print(f"  (stopped after turn {step}: {type(exc).__name__}: {exc})")
                    break

    print()
    print("=== pre-registered verdict inputs ===")
    total = len(rows)
    crossings = [r for r in rows if r["wet"]]
    print(f"qualifying helo flights: {total} (minimum sample {MIN_SAMPLE})")
    if total < MIN_SAMPLE:
        print("Below the minimum sample. Nothing is quotable; widen the saves.")
        return 0

    share = len(crossings) / total
    print(f"A  crossing water:            {len(crossings)}/{total} ({share:.1%})")
    if crossings:
        longest = [r["longest"] for r in crossings]
        print(
            f"B  longest run among those:  median {statistics.median(longest):.1f} NM, "
            f"max {max(longest):.1f} NM"
        )
        print(
            f"   furthest from land:       {max(r['from_land'] for r in crossings):.1f} NM"
        )
        threatened = sum(r["threatened"] for r in crossings)
        print(
            f"C  (context) over-water NM inside enemy radar-SAM threat: {threatened:.1f}"
        )
        tasks: dict[str, int] = {}
        for row in crossings:
            tasks[row["task"]] = tasks.get(row["task"], 0) + 1
        print(f"   by task: {dict(sorted(tasks.items()))}")
    else:
        print("B  no crossings to measure")
    print()
    print("Thresholds are in this file's docstring. Read the verdict off them.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
