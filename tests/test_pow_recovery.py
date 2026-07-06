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
    def __init__(self, player: bool = False) -> None:
        self.alive = True
        self.player = player
        self.repatriated = False

    def kill(self) -> None:
        self.alive = False

    def repatriate(self) -> None:
        self.repatriated = True


def _game(
    holding: dict[Any, Any],
    *,
    will_economy: bool = False,
    invulnerable_player_pilots: bool = False,
) -> Any:
    def find(cp_id: Any) -> Any:
        if cp_id in holding:
            return holding[cp_id]
        raise KeyError(cp_id)

    return SimpleNamespace(
        theater=SimpleNamespace(find_control_point_by_id=find),
        settings=SimpleNamespace(
            vietnam_political_will=will_economy,
            invulnerable_player_pilots=invulnerable_player_pilots,
        ),
    )


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
    assert pilot.alive and pilot.repatriated  # freed and returned to the roster
    assert held.turns_remaining == 2  # freed before the clock advanced


def test_surviving_pows_holds_indefinitely_on_a_will_campaign() -> None:
    pilot = _FakePilot()
    # Clock at 1 would be written off on a normal campaign; a will campaign holds.
    held = PendingPowRecovery("A", 0.0, 0.0, turns_remaining=1, pilot=cast(Any, pilot))
    survivors = surviving_pows(
        cast(Any, _game({}, will_economy=True)), Player.BLUE, [held]
    )
    assert survivors == [held]  # kept -- resolved only by free / war's end
    assert pilot.alive and not pilot.repatriated
    assert held.turns_remaining == 1  # the death clock never advances


def test_surviving_pows_repatriates_an_invulnerable_player_pow_at_writeoff() -> None:
    pilot = _FakePilot(player=True)
    held = PendingPowRecovery("A", 0.0, 0.0, turns_remaining=1, pilot=cast(Any, pilot))
    survivors = surviving_pows(
        cast(Any, _game({}, invulnerable_player_pilots=True)), Player.BLUE, [held]
    )
    assert survivors == []  # dropped from the hold list
    assert pilot.alive and pilot.repatriated  # invulnerable -> returned, not killed


def test_surviving_pows_kills_an_ai_pow_even_with_invulnerable_players() -> None:
    pilot = _FakePilot(player=False)
    held = PendingPowRecovery("A", 0.0, 0.0, turns_remaining=1, pilot=cast(Any, pilot))
    survivors = surviving_pows(
        cast(Any, _game({}, invulnerable_player_pilots=True)), Player.BLUE, [held]
    )
    assert survivors == []
    assert not pilot.alive  # the invulnerable-player setting spares only players


def test_resolve_pows_at_game_end_homecoming_on_win() -> None:
    from game.pow_recovery import resolve_pows_at_game_end

    a, b = _FakePilot(), _FakePilot(player=True)
    coalition = SimpleNamespace(
        pending_pow_recoveries=[
            PendingPowRecovery("A", 0.0, 0.0, pilot=cast(Any, a)),
            PendingPowRecovery("B", 0.0, 0.0, pilot=cast(Any, b)),
        ]
    )
    resolve_pows_at_game_end(cast(Any, _game({})), cast(Any, coalition), won=True)
    assert a.repatriated and b.repatriated  # everyone comes home
    assert a.alive and b.alive
    assert coalition.pending_pow_recoveries == []


def test_resolve_pows_at_game_end_writeoff_on_loss() -> None:
    from game.pow_recovery import resolve_pows_at_game_end

    ai, player = _FakePilot(), _FakePilot(player=True)
    coalition = SimpleNamespace(
        pending_pow_recoveries=[
            PendingPowRecovery("A", 0.0, 0.0, pilot=cast(Any, ai)),
            PendingPowRecovery("B", 0.0, 0.0, pilot=cast(Any, player)),
        ]
    )
    resolve_pows_at_game_end(
        cast(Any, _game({}, invulnerable_player_pilots=True)),
        cast(Any, coalition),
        won=False,
    )
    assert not ai.alive  # AI POW written off
    assert player.alive and player.repatriated  # invulnerable player POW spared
    assert coalition.pending_pow_recoveries == []
