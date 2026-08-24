"""Doctrine-mining row 2: are packages given a TOT past the mission window?

`MissionScheduler.schedule_missions` bounds the random SPREAD OFFSET by the
desired mission length, then adds it to `TotEstimator(package).earliest_tot`::

    package.time_over_target = next(start_time) + tot

so the window bounds the offset, not the TOT. A package with a long transit can
be placed past the end of the mission and nothing clamps it. That is a reading
of the code, not a defect; this counts it.

TWO POPULATIONS, and only one of them is a scheduling defect:

  AVOIDABLY late -- transit alone would have fitted inside the window, and the
    spread offset is what pushed it out. A clamp fixes these.
  UNAVOIDABLY late -- the package cannot physically reach its target inside the
    window at any offset. Clamping would only lie about it. Counted separately
    because a large number here is a different question (should the package have
    been planned at all?), not this row.

PRE-REGISTERED THRESHOLDS, written before the first run, both coalitions pooled:

  DEFECT      avoidably late >= 10% of spread-scheduled packages
              AND median avoidable overshoot >= 5 minutes.
              Both conditions: the generator's own jitter margin is +/-5 min, so
              a two-minute overshoot is noise, not a wasted sortie.
  ROW DIES    avoidably late < 5%, or median avoidable overshoot < 5 minutes.
  GREY        anything between -- report, build nothing, hand it back.

The window measured against is the scheduler's OWN ceiling
(`desired_player_mission_duration` plus the follow-on minutes it appends), not
the raw setting, because that is the intent the code declares.

Population is the spread branch only: BARCAP/TARCAP waves are planned in rounds
to SPAN the mission (so a late one is correct), AEWC chains, `auto_asap` is
immediate, and RECOVERY is tied to carrier ETAs.

!! Drive this from `tools/_campaign_game.py`, not from a `.retribution` save. The
saves in Saved Games are hand-edited, and the numbers this tool first produced
from them described the save rather than the planner. They are withdrawn.

Sibling of `tools/measure_red_planner_headroom.py`; same four-line harness.
Procedure: `docs/dev/design/414th-planner-doctrine-mining-notes.md`.

Run (several saves pool into one verdict, which is how the threshold is read):
    python tools/measure_tot_past_mission_window.py <save.retribution>... [--turns 3]
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
from game.fourteenth.living_battlespace import followon_window_minutes  # noqa: E402

#: The scheduler's own non-spread branches, each of which times its packages by
#: a rule of its own. Only what falls through to the spread is under test.
DCA_TYPES = {FlightType.BARCAP, FlightType.TARCAP}


def spread_scheduled(package: Any) -> bool:
    """Did this package take `schedule_missions`'s final `else` branch?"""
    task = package.primary_task
    if task is FlightType.RECOVERY or task is FlightType.AEWC:
        return False
    if task in DCA_TYPES:
        return False
    return not package.auto_asap


def window_for(coalition: Any) -> timedelta:
    """The scheduler's own spread ceiling, follow-on extension included."""
    settings = coalition.game.settings
    return settings.desired_player_mission_duration + timedelta(
        minutes=followon_window_minutes(coalition)
    )


def measure_coalition(coalition: Any, now: datetime) -> dict[str, Any]:
    window = window_for(coalition)
    rows: list[dict[str, Any]] = []
    for package in coalition.ato.packages:
        if not spread_scheduled(package):
            continue
        tot = package.time_over_target
        if tot is None:
            continue
        try:
            earliest = TotEstimator(package).earliest_tot(now)
        except Exception:  # a package shape the estimator cannot take
            continue
        transit = earliest - now
        elapsed = tot - now
        rows.append(
            {
                "task": FlightType(package.primary_task).value,
                "transit": transit,
                "elapsed": elapsed,
                # The offset as it ended up AFTER every later pass (SEAD
                # windows, the carrier stagger, player pinning) had its say.
                "offset": elapsed - transit,
                "late": elapsed > window,
                "avoidable": elapsed > window and transit <= window,
                "overshoot": elapsed - window,
            }
        )
    return {"window": window, "rows": rows}


def fmt(delta: timedelta) -> str:
    return f"{delta.total_seconds() / 60:.0f}m"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("save", nargs="+")
    parser.add_argument("--turns", type=int, default=4)
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

        save_rows: list[dict[str, Any]] = []
        print()
        print(f"save: {save}")
        print(f"campaign turn at load: {game.turn}")

        for step in range(1, args.turns + 1):
            game.initialize_turn(GameUpdateEvents(), for_red=True, for_blue=True)
            now: datetime = game.conditions.start_time
            for label, coalition in (("red", game.red), ("blue", game.blue)):
                result = measure_coalition(coalition, now)
                rows = result["rows"]
                save_rows.extend(rows)
                late = [r for r in rows if r["late"]]
                avoidable = [r for r in rows if r["avoidable"]]
                max_offset = max((r["offset"] for r in rows), default=timedelta())
                print(
                    f"  turn {step} {label:4s}: {len(rows):3d} spread-scheduled | "
                    f"window {fmt(result['window'])} | late {len(late):3d} "
                    f"(avoidable {len(avoidable):3d}) | "
                    f"max effective offset {fmt(max_offset)}"
                )
                if avoidable:
                    worst = max(avoidable, key=lambda r: r["overshoot"])
                    med = statistics.median(r["overshoot"] for r in avoidable)
                    print(
                        f"                avoidable overshoot: median {fmt(med)}, "
                        f"worst {fmt(worst['overshoot'])} ({worst['task']}, "
                        f"transit {fmt(worst['transit'])})"
                    )
            if step < args.turns:
                try:
                    game.pass_turn(no_action=True)
                except Exception as exc:
                    # Some saves die in unrelated turn-end code; take the turns
                    # this one did give rather than losing the whole sample.
                    print(f"  (stopped after turn {step}: {type(exc).__name__}: {exc})")
                    break

        avoidable = [r for r in save_rows if r["avoidable"]]
        pct = f"{len(avoidable) / len(save_rows):.1%}" if save_rows else "n/a"
        med = (
            fmt(statistics.median(r["overshoot"] for r in avoidable))
            if avoidable
            else "n/a"
        )
        print(
            f"  SAVE TOTAL: {len(avoidable)}/{len(save_rows)} avoidably late "
            f"({pct}), median overshoot {med}"
        )
        all_rows.extend(save_rows)

    print()
    print("=== pre-registered verdict inputs ===")
    total = len(all_rows)
    late = [r for r in all_rows if r["late"]]
    avoidable = [r for r in all_rows if r["avoidable"]]
    unavoidable = [r for r in late if not r["avoidable"]]
    share: Optional[float] = (len(avoidable) / total) if total else None
    print(f"spread-scheduled packages, all turns: {total}")
    print(
        f"late:                                 {len(late)}"
        + (f" ({len(late) / total:.1%})" if total else "")
    )
    print(
        f"  avoidably late (the defect claim):  {len(avoidable)}"
        + (f" ({share:.1%})" if share is not None else "")
    )
    print(f"  unavoidably late (a different row): {len(unavoidable)}")
    if avoidable:
        overshoots = [r["overshoot"] for r in avoidable]
        print(
            f"avoidable overshoot: median {fmt(statistics.median(overshoots))}, "
            f"max {fmt(max(overshoots))}"
        )
        by_task: dict[str, int] = {}
        for row in avoidable:
            by_task[row["task"]] = by_task.get(row["task"], 0) + 1
        print(f"avoidably late by task: {dict(sorted(by_task.items()))}")
    print()
    print("Thresholds are in this file's docstring. Read the verdict off them.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
