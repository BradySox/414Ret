"""Doctrine-mining row 3: does the auto-planner mass, or does it spread?

The doctrine line is "concentrate force on 1-3 objectives". Step 2 established
what the planner can and cannot express (written up in the doctrine-mining note);
this counts what it actually does.

THE KNOWN-BAD METRIC AND HOW THIS AVOIDS IT. "Targets offered vs targets fragged"
cannot separate "chose to spread" from "could not afford more". Two guards:

  * Only turns with ROOM TO CHOOSE are scored -- at least MIN_PACKAGES offensive
    packages to distribute, and at least MIN_POOL_OBJECTIVES distinct candidate
    objectives to distribute them across. A side with four packages and one
    objective did not make a choice.
  * Dispersion is scored against a NULL drawn from the planner's own candidate
    pool, not against an absolute. Picking N targets that are as far apart as N
    random draws would be is the signal; "the targets are far apart" alone is
    just a description of the map.

THREE MEASURES, per scored turn:

  1. OBJECTIVES PER PACKAGE -- distinct owning control points divided by
     offensive packages. 1.0 is one package per objective (maximum spread);
     1/N is everything massed on one.
  2. OBJECTIVE COVERAGE -- for each objective touched, the share of ITS candidate
     targets that were tasked. This is the one that says whether spreading costs
     anything: effort spread so thin that no objective is near finished is effort
     that changes nothing on the map.
  3. DISPERSION PERCENTILE -- observed mean pairwise distance between the chosen
     targets, against the distribution from NULL_DRAWS random same-size draws
     from the candidate pool. 50 means indistinguishable from chance; low means
     the planner clusters.

PRE-REGISTERED THRESHOLDS, written before the first run. Deliberately conjunctive
-- it must both spread AND achieve nothing by it:

  DEFECT      median objectives-per-package >= 0.8
              AND median objective coverage <= 25%
              AND median dispersion percentile >= 25.
  ROW DIES    any one of: median coverage > 50% (objectives do get finished),
              objectives-per-package <= 0.5 (it already masses), or dispersion
              percentile < 10 (it clearly clusters).
  GREY        anything else -- report, build nothing, hand it back.

CORRECTION, and it matters for how much the pre-registration is worth here. The
inclusion gate was first written as "candidate objectives >= 2 x packages" and is
UNSATISFIABLE by construction: objective count is bounded by how many enemy
control points hold candidates (6-9 on the saves used), while package count is
not, so a 15-package turn would have needed 30 objectives. Every turn scored as
"no room" on the first run and the gate was rewritten. The three verdict
thresholds were NOT touched. The finding also came out on the ROW DIES side --
the conservative direction, arguing against building anything -- so a gate
loosened after seeing data cannot have manufactured a defect here. It would
matter if the verdict had gone the other way.

A KNOWN BIAS, stated because it runs one way. The pool is every candidate in the
rebuilt `TheaterState`, but some tasks pick from a narrower slice of it --
`DegradeIads`'s opportunistic tier only considers LORAD and MERAD, for one. So
the pool over-counts objectives that were never really on offer, which inflates
"objectives available" and deflates coverage. Both push the reading toward
"it spreads", i.e. toward declaring a defect. Any ROW DIES verdict survives the
bias; a DEFECT verdict would need the pools narrowed per task first.

Front lines, convoys and downed pilots have no owning control point and are
excluded throughout: CAS is planned off the ground war, not off target choice.

Sibling of `tools/measure_red_planner_headroom.py` and
`tools/measure_tot_past_mission_window.py`; same four-line harness.
Procedure: `docs/dev/design/414th-planner-doctrine-mining-notes.md`.

Run (several saves pool into one verdict, which is how the threshold is read):
    python tools/measure_offensive_concentration.py <save.retribution>... [--turns 3]
"""

from __future__ import annotations

import argparse
import logging
import random
import statistics
import sys
from datetime import datetime
from itertools import combinations
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from game import persistency  # noqa: E402
from game.ato.flighttype import FlightType  # noqa: E402
from game.commander.theaterstate import TheaterState  # noqa: E402
from game.fourteenth.region_priorities import owning_control_point  # noqa: E402
from game.profiling import MultiEventTracer  # noqa: E402
from game.theater.player import Player  # noqa: E402

#: A turn is only scored when the planner had room to mass or spread: enough
#: packages to distribute, and enough distinct objectives to distribute them
#: across. See CORRECTION in the docstring -- the first form of this gate was
#: unsatisfiable, because objective COUNT is bounded by the map while package
#: count is not.
MIN_PACKAGES = 4
MIN_POOL_OBJECTIVES = 4
#: Random same-size draws forming the dispersion null.
NULL_DRAWS = 400
#: Fixed so a re-run of the same save reproduces the same percentile.
NULL_SEED = 20260824


def candidate_targets(state: TheaterState) -> list[Any]:
    """The offensive candidates the planner's compound tasks consume.

    Battle positions and convoys are left out on purpose: they have no owning
    control point, so they are exempt from every measure here.
    """
    pools = (
        state.enemy_air_defenses,
        state.strike_targets,
        state.motorpool_targets,
        state.oca_targets,
        state.enemy_ships,
    )
    targets: list[Any] = []
    for pool in pools:
        targets.extend(pool)
    return targets


def offensive_packages(coalition: Any) -> list[Any]:
    packages = []
    for package in coalition.ato.packages:
        task = package.primary_task
        if task is None or not FlightType(task).is_air_to_ground:
            continue
        if owning_control_point(package.target) is None:
            continue
        packages.append(package)
    return packages


def mean_pairwise_distance(targets: list[Any]) -> Optional[float]:
    if len(targets) < 2:
        return None
    distances = []
    for a, b in combinations(targets, 2):
        try:
            distances.append(a.position.distance_to_point(b.position))
        except Exception:  # a target shape with no position
            continue
    return statistics.mean(distances) if distances else None


def dispersion_percentile(
    chosen: list[Any], pool: list[Any], rng: random.Random
) -> Optional[float]:
    """Where the chosen set's spread sits in the null of same-size draws.

    Below 50 means the planner's picks are closer together than chance; above
    means further apart. None when the pool is too small for a null to mean
    anything.
    """
    observed = mean_pairwise_distance(chosen)
    if observed is None or len(pool) <= len(chosen):
        return None
    null = []
    for _ in range(NULL_DRAWS):
        draw = rng.sample(pool, len(chosen))
        value = mean_pairwise_distance(draw)
        if value is not None:
            null.append(value)
    if not null:
        return None
    below = sum(1 for value in null if value < observed)
    return 100.0 * below / len(null)


def measure_coalition(
    coalition: Any, state: TheaterState, rng: random.Random
) -> Optional[dict[str, Any]]:
    packages = offensive_packages(coalition)
    pool = candidate_targets(state)
    objectives: dict[Any, int] = {}
    for package in packages:
        cp = owning_control_point(package.target)
        objectives[cp] = objectives.get(cp, 0) + 1

    pool_objectives: dict[Any, int] = {}
    for target in pool:
        cp = owning_control_point(target)
        if cp is not None:
            pool_objectives[cp] = pool_objectives.get(cp, 0) + 1

    room = len(packages) >= MIN_PACKAGES and len(pool_objectives) >= MIN_POOL_OBJECTIVES

    # Coverage: of the candidates this objective offered, how many were tasked.
    # The pool is rebuilt from the live game after planning, and tasking a target
    # does not kill it, so the pool still holds everything the planner started
    # with -- no add-back, or the tasked target would be counted twice.
    coverages = []
    for cp, tasked in objectives.items():
        offered = pool_objectives.get(cp, 0)
        if offered:
            coverages.append(min(1.0, tasked / offered))

    return {
        "packages": len(packages),
        "objectives": len(objectives),
        "pool_objectives": len(pool_objectives),
        "room": room,
        "per_package": (len(objectives) / len(packages)) if packages else None,
        "coverage": statistics.median(coverages) if coverages else None,
        "dispersion": dispersion_percentile([p.target for p in packages], pool, rng),
    }


def fmt(value: Optional[float], suffix: str = "") -> str:
    return "n/a" if value is None else f"{value:.2f}{suffix}"


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

    scored: list[dict[str, Any]] = []
    seen = 0
    for save in args.save:
        game = persistency.load_game(save)
        if game is None:
            print(f"could not load {save}")
            continue
        rng = random.Random(NULL_SEED)
        print()
        print(f"save: {save}")
        print(f"campaign turn at load: {game.turn}")

        for step in range(1, args.turns + 1):
            game.initialize_turn(GameUpdateEvents(), for_red=True, for_blue=True)
            now: datetime = game.conditions.start_time
            for label, player in (("red", Player.RED), ("blue", Player.BLUE)):
                coalition = game.coalition_for(player)
                with MultiEventTracer() as tracer:
                    state = TheaterState.from_game(game, player, now, tracer)
                row = measure_coalition(coalition, state, rng)
                if row is None:
                    continue
                seen += 1
                if row["room"]:
                    scored.append(row)
                mark = "scored" if row["room"] else "no room"
                print(
                    f"  turn {step} {label:4s}: {row['packages']:3d} pkgs on "
                    f"{row['objectives']:3d} objectives | pool offers "
                    f"{row['pool_objectives']:3d} | per-pkg "
                    f"{fmt(row['per_package'])} | coverage "
                    f"{fmt(row['coverage'])} | dispersion pct "
                    f"{fmt(row['dispersion'])} | {mark}"
                )
            if step < args.turns:
                try:
                    game.pass_turn(no_action=True)
                except Exception as exc:
                    print(f"  (stopped after turn {step}: {type(exc).__name__}: {exc})")
                    break

    print()
    print("=== pre-registered verdict inputs ===")
    print(f"coalition-turns seen: {seen}, of which scored (had room): {len(scored)}")
    if not scored:
        print("No turn had room to choose. The measure says nothing; widen the saves.")
        return 0
    for key, label in (
        ("per_package", "objectives per package"),
        ("coverage", "objective coverage"),
        ("dispersion", "dispersion percentile"),
    ):
        values = [row[key] for row in scored if row[key] is not None]
        if values:
            print(
                f"median {label:22s}: {statistics.median(values):.2f}  (n={len(values)})"
            )
        else:
            print(f"median {label:22s}: n/a")
    print()
    print("Thresholds are in this file's docstring. Read the verdict off them.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
