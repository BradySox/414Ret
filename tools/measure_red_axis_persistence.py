"""Phase 0 / Phase 1 measurement for the seam 7 fly card.

Measures where red's offensive effort goes, turn by turn, and how long it stays
there after the player reinforces the axis red is pushing.

The card is `docs/dev/design/414th-retribution-long-view.md`, seam 7. Read it
before changing anything here: the thresholds are pre-registered and this script
is only the instrument.

Run:
    python tools/measure_red_axis_persistence.py <save.retribution> [--turns 6]
                                                 [--intervene-after 3]

Phase 0 runs it on a build with no red-continuity feature and predicts a switch
latency of 1 turn or less. If the baseline already persists, the premise behind
seam 7 is wrong and the test -- not the threshold -- has to be redesigned.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections import Counter
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from game import persistency  # noqa: E402
from game.ato.flighttype import FlightType  # noqa: E402
from game.theater import ControlPoint, FrontLine  # noqa: E402
from game.theater.theatergroundobject import TheaterGroundObject  # noqa: E402


def axis_of(target: object) -> Optional[str]:
    """The BLUE control point a red package's target belongs to.

    There is no single `MissionTarget.control_point`, so this mapping is per
    target type. Written once here rather than improvised per run, as the card
    requires.
    """
    if isinstance(target, FrontLine):
        return target.blue_cp.name
    if isinstance(target, TheaterGroundObject):
        return target.control_point.name
    if isinstance(target, ControlPoint):
        return target.name
    return None


def red_offensive_axes(game: object) -> Counter[str]:
    """Axis -> count of red offensive packages targeting it this turn."""
    counts: Counter[str] = Counter()
    for package in game.red.ato.packages:  # type: ignore[attr-defined]
        task = package.primary_task
        if task is None or not FlightType(task).is_air_to_ground:
            continue
        axis = axis_of(package.target)
        if axis is not None:
            counts[axis] += 1
    return counts


def primary_axis(counts: Counter[str]) -> Optional[str]:
    """The most-targeted axis, or None when there is a tie or nothing at all.

    A tie is never broken arbitrarily -- the card says to record it as a tie.
    """
    if not counts:
        return None
    ranked = counts.most_common()
    if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
        return None
    return ranked[0][0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("save")
    parser.add_argument("--turns", type=int, default=6)
    parser.add_argument("--intervene-after", type=int, default=3)
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

    print(f"save: {args.save}")
    print(f"campaign turn at load: {game.turn}")

    blue_cps = [cp.name for cp in game.theater.player_points()]
    contested = [
        cp.name for cp in game.theater.player_points() if cp.has_active_frontline
    ]
    print(f"blue control points: {len(blue_cps)}")
    print(f"contested axes: {len(contested)} -> {contested}")
    if len(contested) < 3:
        print("WARNING: fewer than 3 contested axes; the card calls this unsuitable.")

    from game.sim import GameUpdateEvents

    history: list[tuple[int, Optional[str], Counter[str]]] = []
    intervened_axis: Optional[str] = None

    for step in range(1, args.turns + 1):
        game.initialize_turn(GameUpdateEvents(), for_red=True, for_blue=False)
        counts = red_offensive_axes(game)
        top = primary_axis(counts)
        history.append((step, top, counts))

        total = sum(counts.values())
        share = f"{counts[top] / total:.0%}" if top and total else "n/a"
        print(
            f"  turn {step}: {total:2d} red offensive packages | "
            f"primary={top or 'TIE/none'} ({share}) | {dict(counts)}"
        )

        if step == args.intervene_after and top is not None:
            intervened_axis = top
            print(f"  -- INTERVENTION: reinforcing {intervened_axis} --")
            print("     (apply by hand; see the card. This run only records.)")

        if step < args.turns:
            game.pass_turn(no_action=True)

    print()
    if intervened_axis is None:
        print("no intervention applied (no clear primary axis at that turn)")
        return 0

    latency = None
    for step, top, _ in history:
        if step <= args.intervene_after:
            continue
        if top != intervened_axis:
            latency = step - args.intervene_after
            break

    print(f"pre-intervention primary axis: {intervened_axis}")
    if latency is None:
        print(f"switch latency L: never switched within {args.turns} turns")
    else:
        print(f"switch latency L: {latency}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
