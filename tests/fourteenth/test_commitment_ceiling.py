"""Commitment ceiling (CLAUDE.md §48) -- the will-coupled war budget.

As BLUE Political Will falls, Congress trims the war budget (income scaled toward a
floor). Locks the multiplier shape, the BLUE-only + both-toggles gating, and the
message-on-cut, plus the guarantee that the feature is a complete no-op with either
toggle off (so non-Vietnam campaigns and pre-feature saves are untouched).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from game.fourteenth.commitment_ceiling import (
    CEILING_FLOOR_MULT,
    CEILING_FULL_WILL,
    apply_commitment_ceiling,
    will_budget_multiplier,
)


def _game(
    *, ceiling: bool = True, will_on: bool = True, blue_will: float = 100.0
) -> Any:
    messages: list[str] = []
    game = SimpleNamespace(
        settings=SimpleNamespace(
            vietnam_commitment_ceiling=ceiling, vietnam_political_will=will_on
        ),
        blue=SimpleNamespace(political_will=blue_will),
    )
    game.message = lambda title, text="", _m=messages: _m.append(title)
    game.messages = messages
    return game


def _blue() -> Any:
    return SimpleNamespace(is_blue=True)


def _red() -> Any:
    return SimpleNamespace(is_blue=False)


def test_full_funding_while_will_is_high() -> None:
    assert will_budget_multiplier(_game(blue_will=100.0)) == 1.0
    assert will_budget_multiplier(_game(blue_will=CEILING_FULL_WILL)) == 1.0


def test_floor_at_zero_will() -> None:
    assert will_budget_multiplier(_game(blue_will=0.0)) == CEILING_FLOOR_MULT


def test_ramps_linearly_between() -> None:
    # Halfway down the ramp (will = FULL/2) sits halfway between floor and 1.0.
    mid = will_budget_multiplier(_game(blue_will=CEILING_FULL_WILL / 2))
    assert mid == pytest.approx(CEILING_FLOOR_MULT + (1.0 - CEILING_FLOOR_MULT) * 0.5)
    # Monotonic: less will never buys more budget.
    assert will_budget_multiplier(_game(blue_will=20.0)) < will_budget_multiplier(
        _game(blue_will=40.0)
    )


def test_income_cut_below_the_threshold_and_messaged() -> None:
    game = _game(blue_will=30.0)
    out = apply_commitment_ceiling(game, _blue(), 1000.0)
    assert out == pytest.approx(1000.0 * will_budget_multiplier(game))
    assert out < 1000.0
    assert "War budget cut" in game.messages


def test_no_cut_no_message_at_full_funding() -> None:
    game = _game(blue_will=90.0)
    assert apply_commitment_ceiling(game, _blue(), 1000.0) == 1000.0
    assert game.messages == []


def test_red_is_never_coupled() -> None:
    # The ceiling is Washington's war budget only; the enemy income is untouched
    # even at rock-bottom will.
    game = _game(blue_will=0.0)
    assert apply_commitment_ceiling(game, _red(), 1000.0) == 1000.0
    assert game.messages == []


def test_off_switch_returns_income_untouched() -> None:
    # Feature off, or the will economy off: a complete no-op regardless of will.
    game = _game(ceiling=False, blue_will=0.0)
    assert apply_commitment_ceiling(game, _blue(), 1000.0) == 1000.0
    game = _game(will_on=False, blue_will=0.0)
    assert apply_commitment_ceiling(game, _blue(), 1000.0) == 1000.0
