"""SCAR CSAR pending-rescue lifecycle (Phase 2c-3, slice C1).

A SOF team stranded by a botched SCAR capture becomes a ``PendingSofRescue`` on
its coalition. The turn-cap loss condition ages each rescue down one turn per
``Coalition.end_turn`` and writes it off when it reaches zero. These tests pin
that countdown in isolation (the per-turn hook + the pure aging helper).
"""

from __future__ import annotations

from game.scar_rescue import (
    DEFAULT_SOF_RESCUE_TURNS,
    PendingSofRescue,
    age_pending_rescues,
)


def test_aging_decrements_turns_remaining() -> None:
    survivors = age_pending_rescues([PendingSofRescue(1.0, 2.0, turns_remaining=3)])
    assert survivors == [PendingSofRescue(1.0, 2.0, turns_remaining=2)]


def test_rescue_dropped_when_countdown_reaches_zero() -> None:
    # A team with one turn left ages out and is written off this turn.
    assert age_pending_rescues([PendingSofRescue(1.0, 2.0, turns_remaining=1)]) == []


def test_aging_is_independent_per_rescue() -> None:
    survivors = age_pending_rescues(
        [
            PendingSofRescue(1.0, 1.0, turns_remaining=1),  # ages out
            PendingSofRescue(2.0, 2.0, turns_remaining=3),  # survives
        ]
    )
    assert survivors == [PendingSofRescue(2.0, 2.0, turns_remaining=2)]


def test_full_lifespan_from_default_is_finite() -> None:
    # A team stranded at the default cap survives a fixed number of turns then
    # is written off -- the countdown never runs forever.
    rescues = [PendingSofRescue(0.0, 0.0)]
    assert rescues[0].turns_remaining == DEFAULT_SOF_RESCUE_TURNS
    turns_survived = 0
    while rescues:
        rescues = age_pending_rescues(rescues)
        turns_survived += 1
    assert turns_survived == DEFAULT_SOF_RESCUE_TURNS


def test_empty_list_is_a_noop() -> None:
    assert age_pending_rescues([]) == []
