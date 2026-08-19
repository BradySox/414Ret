"""Phase 0 measurement for the seam 7 successor framing: is there headroom?

Seam 7 was DROPPED 2026-08-17 after two framings died on the same finding: red's
choices and the player's choices are both functions of the same static map
structure, so red looks responsive with no memory and memory has nothing to add.

A third framing has since appeared from outside -- juanjux's fork replaces the
HTN's *decision-maker* rather than adding a dimension to it. That framing has to
beat the same finding first, and it can be tested before any code exists:

    A better brain is only worth building if the current one is leaving value on
    the table. If red's plan is forced by structure, every brain converges on it.

Three measurements, none of which needs an LLM, a feature, or a flight:

1. CHOICE VOLUME -- how many candidate targets `TheaterState` offered red, versus
   how many distinct targets red actually fragged. Offered ~= used means there was
   no choice to make well or badly, and the seam stays dropped.
2. TASK MIX -- red's offensive effort by primary task. The long-view note flagged
   "what it goes after" as an open dimension after observing red open against
   vehicle groups rather than the SAM belt.
3. BLIND PUSH -- red offensive packages whose target sits inside blue's radar-SAM
   threat, set against how much suppression red planned. Flying strike into a live
   SAM belt you never tried to suppress is a decision that reads wrong in the air,
   which is the kind of evidence the note asks for before reopening the seam.

The card is `docs/dev/design/414th-red-brain-phase0-notes.md`. Read it before
changing anything here: the thresholds are pre-registered and this is only the
instrument. Sibling of `tools/measure_red_axis_persistence.py`, which measures the
axis dimension the first framing died on.

Run:
    python tools/measure_red_planner_headroom.py <save.retribution> [--turns 4]
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from game import persistency  # noqa: E402
from game.ato.flighttype import FlightType  # noqa: E402
from game.commander.theaterstate import TheaterState  # noqa: E402
from game.profiling import MultiEventTracer  # noqa: E402
from game.theater.player import Player  # noqa: E402

#: Tasks that suppress or destroy an air defence. Red planning none of these while
#: pushing ground attack into a live SAM belt is the concrete "reads wrong in the
#: air" candidate; see measurement 3.
SUPPRESSION_TASKS = {FlightType.SEAD, FlightType.DEAD, FlightType.SEAD_ESCORT}


def target_key(target: object) -> str:
    """A stable identity for a package's target, for counting distinct targets."""
    name = getattr(target, "name", None) or getattr(target, "full_name", None)
    return f"{type(target).__name__}:{name or id(target)}"


def red_offensive_packages(game: Any) -> list[Any]:
    packages = []
    for package in game.red.ato.packages:
        task = package.primary_task
        if task is not None and FlightType(task).is_air_to_ground:
            packages.append(package)
    return packages


def candidate_counts(state: TheaterState) -> dict[str, int]:
    """What the planner was offered this turn, by target family.

    Deliberately counts the same lists `PlanNextAction`'s compound tasks consume,
    so "offered" means offered to the planner, not merely present in the theater.
    """
    battle_positions = sum(
        len(positions.front_line_units) if hasattr(positions, "front_line_units") else 0
        for positions in state.enemy_battle_positions.values()
    )
    return {
        "air defenses": len(state.enemy_air_defenses),
        "strike targets": len(state.strike_targets),
        "motorpools": len(state.motorpool_targets),
        "OCA (airfields)": len(state.oca_targets),
        "convoys": len(state.enemy_convoys),
        "shipping": len(state.enemy_shipping),
        "ships": len(state.enemy_ships),
        "battle positions": battle_positions or len(state.enemy_battle_positions),
    }


def measure_turn(game: Any, state: TheaterState) -> dict[str, Any]:
    packages = red_offensive_packages(game)
    distinct = {target_key(p.target) for p in packages}
    tasks: Counter[str] = Counter(FlightType(p.primary_task).value for p in packages)

    threat = state.threat_zones  # blue's zones, from red's point of view
    in_sam_threat = 0
    for package in packages:
        try:
            if threat.threatened_by_radar_sam(package.target):
                in_sam_threat += 1
        except Exception:  # a target shape the zone test cannot take
            continue

    suppression = sum(
        1
        for p in game.red.ato.packages
        if p.primary_task is not None
        and FlightType(p.primary_task) in SUPPRESSION_TASKS
    )

    offered = candidate_counts(state)
    return {
        "packages": len(packages),
        "distinct_targets": len(distinct),
        "offered": offered,
        "offered_total": sum(offered.values()),
        "tasks": tasks,
        "in_sam_threat": in_sam_threat,
        "suppression": suppression,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("save")
    parser.add_argument("--turns", type=int, default=4)
    parser.add_argument(
        "--saved-games",
        default=str(Path.home() / "Saved Games" / "DCS"),
        help="DCS user folder persistency needs before a save will load.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.ERROR)
    persistency.setup(args.saved_games, True, 16880)
    game = persistency.load_game(args.save)
    if game is None:
        print(f"could not load {args.save}")
        return 1

    from game.sim import GameUpdateEvents

    print(f"save: {args.save}")
    print(f"campaign turn at load: {game.turn}")
    print()

    rows: list[dict[str, Any]] = []
    for step in range(1, args.turns + 1):
        game.initialize_turn(GameUpdateEvents(), for_red=True, for_blue=False)
        now: datetime = game.conditions.start_time
        with MultiEventTracer() as tracer:
            state = TheaterState.from_game(game, Player.RED, now, tracer)
        row = measure_turn(game, state)
        rows.append(row)

        used = row["distinct_targets"]
        offered = row["offered_total"]
        pct = f"{used / offered:.0%}" if offered else "n/a"
        print(
            f"turn {step}: {row['packages']:2d} offensive packages on "
            f"{used:2d} distinct targets | offered {offered:3d} ({pct} used)"
        )
        print(f"          offered by family: {row['offered']}")
        print(f"          task mix: {dict(row['tasks'])}")
        print(
            f"          targets inside blue radar-SAM threat: "
            f"{row['in_sam_threat']}/{row['packages']} | "
            f"red suppression packages planned: {row['suppression']}"
        )
        if step < args.turns:
            game.pass_turn(no_action=True)

    print()
    print("=== Phase 0 verdict inputs ===")
    used_total = sum(r["distinct_targets"] for r in rows)
    offered_total = sum(r["offered_total"] for r in rows)
    ratio: Optional[float] = (used_total / offered_total) if offered_total else None
    print(
        f"targets used / offered, all turns: {used_total}/{offered_total}"
        + (f" = {ratio:.1%}" if ratio is not None else "")
    )
    print(f"suppression packages, all turns:   {sum(r['suppression'] for r in rows)}")
    print(
        "packages into radar-SAM threat:    "
        f"{sum(r['in_sam_threat'] for r in rows)}/"
        f"{sum(r['packages'] for r in rows)}"
    )
    print()
    print("Read the verdict off the card, not off this output.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
