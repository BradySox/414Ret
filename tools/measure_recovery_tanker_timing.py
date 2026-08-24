"""Doctrine-mining row 6: is the recovery tanker's schedule reachable?

Step 2 corrected the row as it was written. `RecoveryTankerFlightPlan` overrides
`tot_waypoint` to `layout.departure`, so a recovery tanker's TOT is its TAKEOFF
time, not its arrival on station -- and `_travel_time_to_waypoint(departure)` is
zero, so `takeoff_time()` and the inherited `patrol_start_time` both collapse to
the package TOT. That makes TWO separate questions, measured here together:

  (a) IS THE TAKEOFF TIME REACHABLE? `schedule_missions` ends with

          package.time_over_target = carrier_etas[package.target].pop(0)

      where the ETA is a returning flight's landing time minus ten minutes.
      Every other branch of the scheduler floors on the package's own
      `earliest_tot`; this one does not. A tanker can be told to take off before
      it can start, taxi and get airborne.

  (b) DOES THE TEN-MINUTE LEAD COVER THE TRANSIT? The plan routes the tanker
      from its departure field to a station downwind of the boat, but the
      schedule anchors on takeoff and never charges that leg. Since the assigned
      takeoff is (first landing - 10 min), the tanker reaches its station late
      by exactly `transit - 10 min`. For a tanker on the boat that is small. For
      a land-based one it need not be.

PRE-REGISTERED THRESHOLDS, written before the first run.

  Minimum sample: 8 RECOVERY packages across all saves. Below that neither
  question is answered -- say so rather than quoting a percentage of five.

  (a) DEFECT    >= 10% of packages have assigned TOT < earliest_tot
                AND median shortfall >= 5 min.
      ROW DIES  < 5%, or median shortfall < 5 min.

  (b) DEFECT    >= 25% of packages have departure->station transit > 10 min
                AND median excess >= 5 min. The bar is higher than (a)'s on
                purpose: a tanker that misses the FIRST recovery still services
                the ones behind it, so this is a defect when it is the common
                case, not when it is possible.
      ROW DIES  < 10%, or median excess < 5 min.

  GREY in between for either -- report, build nothing, hand it back.

Measure (a) is applied to every RECOVERY package, not only the ones that took an
ETA from the queue. A package whose carrier had no ETAs keeps the TOT the
fulfiller gave it, and "can this flight reach the time it was given" is the same
question either way.

The harness MIGRATES each save before measuring, which its two siblings do not:
`persistency.load_game` runs no migration, so a save measured without it is a
state the app never loads. That is not cosmetic here -- unmigrated, every save
reports zero recovery tankers.

Sibling of `tools/measure_tot_past_mission_window.py`; same four-line harness.
Procedure: `docs/dev/design/414th-planner-doctrine-mining-notes.md`.

Run (several saves pool into one verdict, which is how the threshold is read):
    python tools/measure_recovery_tanker_timing.py <save.retribution>... [--turns 3]
"""

from __future__ import annotations

import argparse
import logging
import statistics
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from game import persistency  # noqa: E402
from game.ato.flighttype import FlightType  # noqa: E402
from game.ato.traveltime import TotEstimator  # noqa: E402
from game.migrator import Migrator  # noqa: E402

#: The lead `schedule_missions` builds into a recovery ETA: the tanker is told to
#: take off this long before the flight it is meant to service lands.
RECOVERY_LEAD = timedelta(minutes=10)
#: Below this many packages the percentages mean nothing.
MIN_SAMPLE = 8


def station_transit(flight: Any) -> Optional[timedelta]:
    """Time from the tanker's takeoff to its recovery station.

    Reaches into the layout because there is no public accessor: the plan's own
    `patrol_start_time` returns the package TOT unchanged for this plan type,
    which is the thing under test and cannot be used to test it.
    """
    plan = flight.flight_plan
    layout = getattr(plan, "layout", None)
    patrol_start = getattr(layout, "patrol_start", None)
    if patrol_start is None:
        return None
    try:
        return plan._travel_time_to_waypoint(patrol_start)
    except Exception:  # a layout whose waypoints were never populated
        return None


def measure_coalition(coalition: Any, now: datetime) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for package in coalition.ato.packages:
        if package.primary_task is not FlightType.RECOVERY:
            continue
        assigned = package.time_over_target
        if assigned is None:
            continue
        try:
            floor = TotEstimator(package).earliest_tot(now)
        except Exception:
            continue
        transits = [
            transit
            for transit in (station_transit(f) for f in package.flights)
            if transit is not None
        ]
        transit = max(transits) if transits else None
        departure = next(
            (getattr(f.departure, "name", "?") for f in package.flights), "?"
        )
        rows.append(
            {
                "target": getattr(package.target, "name", "?"),
                "departure": departure,
                "assigned": assigned - now,
                "floor": floor - now,
                "shortfall": floor - assigned,
                "transit": transit,
                "excess": (transit - RECOVERY_LEAD) if transit is not None else None,
            }
        )
    return rows


def fmt(delta: Optional[timedelta]) -> str:
    return "n/a" if delta is None else f"{delta.total_seconds() / 60:.0f}m"


def verdict_block(
    label: str, flagged: list[timedelta], total: int, defect_pct: float, dies_pct: float
) -> None:
    share = (len(flagged) / total) if total else 0.0
    median = statistics.median(flagged) if flagged else None
    print(f"{label}")
    print(f"  flagged: {len(flagged)}/{total} ({share:.1%})")
    print(f"  median:  {fmt(median)}")
    print(
        f"  bars:    defect >= {defect_pct:.0%} and >= 5m | dies < {dies_pct:.0%} or median < 5m"
    )


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

    all_rows: list[dict[str, Any]] = []
    for save in args.save:
        game = persistency.load_game(save)
        if game is None:
            print(f"could not load {save}")
            continue
        # `load_game` does not migrate -- only the app's load path does
        # (`QLiberationWindow`). Without this the save is measured in a state no
        # player ever sees, which is how the first run of this tool reported zero
        # recovery tankers on a save that has three.
        Migrator(game, False)
        print()
        print(f"save: {save}")
        print(f"campaign turn at load: {game.turn}")

        for step in range(1, args.turns + 1):
            game.initialize_turn(GameUpdateEvents(), for_red=True, for_blue=True)
            now: datetime = game.conditions.start_time
            for label, coalition in (("red", game.red), ("blue", game.blue)):
                rows = measure_coalition(coalition, now)
                all_rows.extend(rows)
                for row in rows:
                    late = "LATE" if row["shortfall"] > timedelta() else "ok  "
                    print(
                        f"  turn {step} {label:4s}: {row['target'][:22]:22s} "
                        f"from {row['departure'][:18]:18s} | takeoff "
                        f"{fmt(row['assigned'])} vs floor {fmt(row['floor'])} "
                        f"{late} | station transit {fmt(row['transit'])}"
                    )
            if step < args.turns:
                try:
                    game.pass_turn(no_action=True)
                except Exception as exc:
                    print(f"  (stopped after turn {step}: {type(exc).__name__}: {exc})")
                    break

    print()
    print("=== pre-registered verdict inputs ===")
    total = len(all_rows)
    print(f"RECOVERY packages seen: {total} (minimum sample {MIN_SAMPLE})")
    if total < MIN_SAMPLE:
        print(
            "Below the minimum sample. Neither question is answered; widen the saves."
        )
        return 0

    unreachable = [
        row["shortfall"] for row in all_rows if row["shortfall"] > timedelta()
    ]
    verdict_block(
        "(a) takeoff time earlier than the flight can start:",
        unreachable,
        total,
        0.10,
        0.05,
    )
    print()
    excesses = [
        row["excess"]
        for row in all_rows
        if row["excess"] is not None and row["excess"] > timedelta()
    ]
    measured = sum(1 for row in all_rows if row["excess"] is not None)
    verdict_block(
        "(b) station transit longer than the ten-minute lead:",
        excesses,
        measured,
        0.25,
        0.10,
    )
    print()
    print("Thresholds are in this file's docstring. Read the verdict off them.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
