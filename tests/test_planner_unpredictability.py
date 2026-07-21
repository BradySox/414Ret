"""Tests for the auto-planner's priority-weighted target ordering.

Covers game/commander/tasks/targetorder.py: with unpredictability 0 the planner
stays strictly deterministic (so existing behavior and tests are preserved), and
with higher values it produces weighted-random orderings that still favor the
highest-priority target.
"""

from __future__ import annotations

import random
from types import SimpleNamespace

from game.commander.tasks.targetorder import shuffled_by_priority


def _state(
    *,
    is_blue: bool,
    ownfor: int = 0,
    opfor: int = 0,
    c2_effects: bool = False,
    ccs: tuple[bool, ...] = (),
) -> object:
    """A fake TheaterState. ``ccs`` is the aliveness of the planning side's own
    command centers (empty = none), ``c2_effects`` toggles §52."""
    settings = SimpleNamespace(
        ownfor_planner_unpredictability=ownfor,
        opfor_planner_unpredictability=opfor,
        c2_decapitation_effects=c2_effects,
    )
    player = SimpleNamespace(is_blue=is_blue)
    tgos = [
        SimpleNamespace(
            category="commandcenter",
            groups=[SimpleNamespace(units=[SimpleNamespace(alive=a)])],
        )
        for a in ccs
    ]
    cp = SimpleNamespace(captured=player, ground_objects=tgos)
    theater = SimpleNamespace(controlpoints=[cp])
    game = SimpleNamespace(settings=settings)
    coalition = SimpleNamespace(player=player, game=game)
    return SimpleNamespace(
        context=SimpleNamespace(settings=settings, coalition=coalition, theater=theater)
    )


def test_zero_strength_is_identity() -> None:
    items = list(range(10))
    for is_blue in (True, False):
        state = _state(is_blue=is_blue)  # both knobs default 0
        assert shuffled_by_priority(items, state, rng=random.Random(1)) == items  # type: ignore[arg-type]


def test_short_lists_are_unchanged() -> None:
    state = _state(is_blue=False, opfor=100)
    assert shuffled_by_priority([], state, rng=random.Random(1)) == []  # type: ignore[arg-type]
    assert shuffled_by_priority([42], state, rng=random.Random(1)) == [42]  # type: ignore[arg-type]


def test_result_is_a_permutation() -> None:
    items = list(range(12))
    state = _state(is_blue=False, opfor=60)
    out = shuffled_by_priority(items, state, rng=random.Random(7))  # type: ignore[arg-type]
    assert sorted(out) == items
    assert len(out) == len(items)


def test_uses_the_correct_side_knob() -> None:
    items = list(range(8))
    # Red planner with only the OWNFOR knob raised must stay deterministic.
    red_state = _state(is_blue=False, ownfor=100, opfor=0)
    assert shuffled_by_priority(items, red_state, rng=random.Random(3)) == items  # type: ignore[arg-type]
    # Blue planner with only the OPFOR knob raised must stay deterministic.
    blue_state = _state(is_blue=True, ownfor=0, opfor=100)
    assert shuffled_by_priority(items, blue_state, rng=random.Random(3)) == items  # type: ignore[arg-type]


def test_high_strength_reorders() -> None:
    items = list(range(20))
    state = _state(is_blue=False, opfor=100)
    out = shuffled_by_priority(items, state, rng=random.Random(0))  # type: ignore[arg-type]
    assert out != items  # near-uniform shuffle should move something
    assert sorted(out) == items


def test_highest_priority_is_favored() -> None:
    """The top-priority target should land first far more often than a low one."""
    items = list(range(6))  # 0 == highest priority
    state = _state(is_blue=False, opfor=40)
    first_counts = {item: 0 for item in items}
    rng = random.Random(123)
    trials = 4000
    for _ in range(trials):
        out = shuffled_by_priority(items, state, rng=rng)  # type: ignore[arg-type]
        first_counts[out[0]] += 1
    # The highest-priority item heads the list more often than any other, and far
    # more often than the lowest-priority one.
    assert first_counts[0] == max(first_counts.values())
    assert first_counts[0] > first_counts[5] * 3


# --- §52: command-center decapitation feeds the shuffler --------------------


def test_decapitated_c2_reorders_even_with_a_zero_base_knob() -> None:
    items = list(range(20))
    # opfor knob 0, but the red planner's command centers are all dead + the
    # feature is on -> the C2 bonus alone drives a reorder.
    state = _state(is_blue=False, opfor=0, c2_effects=True, ccs=(False, False))
    out = shuffled_by_priority(items, state, rng=random.Random(0))  # type: ignore[arg-type]
    assert out != items
    assert sorted(out) == items


def test_intact_c2_stays_deterministic() -> None:
    items = list(range(10))
    state = _state(is_blue=False, opfor=0, c2_effects=True, ccs=(True, True))
    assert shuffled_by_priority(items, state, rng=random.Random(0)) == items  # type: ignore[arg-type]


def test_c2_bonus_is_gated_by_the_setting() -> None:
    items = list(range(10))
    # Dead command centers but the feature is OFF -> still deterministic.
    state = _state(is_blue=False, opfor=0, c2_effects=False, ccs=(False, False))
    assert shuffled_by_priority(items, state, rng=random.Random(0)) == items  # type: ignore[arg-type]
