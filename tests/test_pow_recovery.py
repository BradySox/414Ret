"""Tests for the captured-pilot POW recovery model (SCAR rescue rework, Phase 3).

A pilot the Combat SAR enemy snatch party seizes before rescue becomes a
``PendingPowRecovery`` held for a few turns. These lock the cheap-to-verify
contract: the dataclass defaults and the turn-cap aging clock. The capture ->
POW commit integration rides ``MissionResultsProcessor`` and the in-game pass.
"""

from __future__ import annotations

from game.pow_recovery import (
    DEFAULT_POW_HOLD_TURNS,
    PendingPowRecovery,
    age_pending_pows,
)


def test_pending_pow_recovery_defaults() -> None:
    captured = PendingPowRecovery(airframe_unit_name="Enfield11", x=1.0, y=2.0)
    assert captured.airframe_unit_name == "Enfield11"
    assert (captured.x, captured.y) == (1.0, 2.0)
    assert captured.turns_remaining == DEFAULT_POW_HOLD_TURNS
    assert captured.holding_cp_id is None


def test_age_pending_pows_decrements_and_keeps_survivors() -> None:
    held = PendingPowRecovery("A", 0.0, 0.0, turns_remaining=2)
    survivors = age_pending_pows([held])
    assert survivors == [held]
    assert held.turns_remaining == 1


def test_age_pending_pows_drops_expired() -> None:
    expiring = PendingPowRecovery("A", 0.0, 0.0, turns_remaining=1)
    survivors = age_pending_pows([expiring])
    assert survivors == []  # decremented to 0 -> the POW is moved deep / written off
    assert expiring.turns_remaining == 0


def test_age_pending_pows_mixed() -> None:
    keep = PendingPowRecovery("keep", 0.0, 0.0, turns_remaining=3)
    drop = PendingPowRecovery("drop", 0.0, 0.0, turns_remaining=1)
    survivors = age_pending_pows([keep, drop])
    assert survivors == [keep]
    assert keep.turns_remaining == 2
