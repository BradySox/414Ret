"""Tests for the captured-pilot held-POW model.

A pilot the enemy snatch party seizes becomes a ``PendingPowRecovery``: held
alive, **freed** by recapturing the holding airfield, or **killed** if the hold
clock runs out (draining political will per turn held). These lock the model
defaults and the ``surviving_pows`` free/age/kill clock. (The dedicated recovery
raid was shelved in the 2026-07-03 CSAR rescope.)
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

from game.pow_recovery import (
    DEFAULT_POW_HOLD_TURNS,
    PendingPowRecovery,
    surviving_pows,
)
from game.theater import Player


class _FakePilot:
    def __init__(self) -> None:
        self.alive = True

    def kill(self) -> None:
        self.alive = False


def _game(holding: dict[Any, Any]) -> Any:
    def find(cp_id: Any) -> Any:
        if cp_id in holding:
            return holding[cp_id]
        raise KeyError(cp_id)

    return SimpleNamespace(theater=SimpleNamespace(find_control_point_by_id=find))


def test_pending_pow_recovery_defaults() -> None:
    captured = PendingPowRecovery(airframe_unit_name="Enfield11", x=1.0, y=2.0)
    assert captured.airframe_unit_name == "Enfield11"
    assert (captured.x, captured.y) == (1.0, 2.0)
    assert captured.turns_remaining == DEFAULT_POW_HOLD_TURNS
    assert captured.holding_cp_id is None
    assert captured.pilot is None


def test_surviving_pows_keeps_unexpired_and_decrements() -> None:
    pilot = _FakePilot()
    held = PendingPowRecovery("A", 0.0, 0.0, turns_remaining=2, pilot=cast(Any, pilot))
    survivors = surviving_pows(cast(Any, _game({})), Player.BLUE, [held])
    assert survivors == [held]
    assert held.turns_remaining == 1
    assert pilot.alive  # still held, not killed


def test_surviving_pows_kills_the_abandoned_pilot() -> None:
    pilot = _FakePilot()
    held = PendingPowRecovery("A", 0.0, 0.0, turns_remaining=1, pilot=cast(Any, pilot))
    survivors = surviving_pows(cast(Any, _game({})), Player.BLUE, [held])
    assert survivors == []  # clock ran out -> dropped
    assert not pilot.alive  # ...and the aviator is killed for good


def test_surviving_pows_frees_when_holding_airfield_recaptured() -> None:
    pilot = _FakePilot()
    cp_id = uuid4()
    friendly_field = SimpleNamespace(captured=Player.BLUE)
    held = PendingPowRecovery(
        "A", 0.0, 0.0, turns_remaining=2, holding_cp_id=cp_id, pilot=cast(Any, pilot)
    )
    survivors = surviving_pows(
        cast(Any, _game({cp_id: friendly_field})), Player.BLUE, [held]
    )
    assert survivors == []  # the field fell -> the POW walks free (dropped)
    assert pilot.alive  # freed, not killed
    assert held.turns_remaining == 2  # freed before the clock advanced
