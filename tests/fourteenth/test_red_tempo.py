"""Red tempo (Vietnam campaign layer W6) -- the turn-windowed "Hanoi answers".

Locks the schedule parse, the last-window-wins selection, the trail-surge
multiplier (incl. the ground-offensive floor), the ground-offensive stance
pulse, and the announce latch. The campaign-YAML lookup is bypassed by patching
``schedule_for`` with parsed windows, so no real campaign definition is needed.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from game.fourteenth import red_tempo
from game.fourteenth.red_tempo import (
    GROUND_OFFENSIVE_MIN_SURGE,
    RedTempoWindow,
    active_window,
    apply_red_tempo,
    ground_offensive_active,
    parse_red_tempo,
    trail_surge_multiplier,
)


def _arc() -> tuple[RedTempoWindow, ...]:
    """The Yankee Station shape: baseline surge -> halt -> Linebacker pulse."""
    return parse_red_tempo(
        [
            {"from_turn": 1, "name": "Rolling Thunder", "trail_surge": 1.5},
            {"from_turn": 8, "name": "The Bombing Halt", "trail_surge": 2.0},
            {"from_turn": 11, "name": "Linebacker", "ground_offensive": 3},
        ]
    )


def _game(turn: int) -> Any:
    game = SimpleNamespace(
        turn=turn,
        campaign_name="Test",
        red=SimpleNamespace(player=SimpleNamespace()),
        theater=SimpleNamespace(conflicts=lambda: []),
        red_tempo_announced_window=None,
        messages=[],
    )
    game.message = lambda title, text: game.messages.append((title, text))
    return game


# --- parsing ------------------------------------------------------------------


def test_parse_none_and_empty() -> None:
    assert parse_red_tempo(None) == ()
    assert parse_red_tempo([]) == ()


def test_parse_reads_fields_and_sorts_by_turn() -> None:
    windows = parse_red_tempo(
        [
            {"from_turn": 11, "name": "Linebacker", "ground_offensive": 3},
            {"from_turn": 1, "trail_surge": 1.5},
        ]
    )
    assert [w.from_turn for w in windows] == [1, 11]  # sorted ascending
    assert windows[0].trail_surge == 1.5
    assert windows[1].ground_offensive_turns == 3
    assert windows[1].name == "Linebacker"


def test_parse_rejects_malformed() -> None:
    with pytest.raises(ValueError):
        parse_red_tempo([{"trail_surge": 2.0}])  # missing from_turn
    with pytest.raises(ValueError):
        parse_red_tempo("nope")


# --- active window: the last one whose from_turn is reached -------------------


def test_active_window_is_the_last_reached(monkeypatch: Any) -> None:
    arc = _arc()
    monkeypatch.setattr(red_tempo, "schedule_for", lambda g: arc)

    def _window(turn: int) -> RedTempoWindow:
        window = active_window(_game(turn))
        assert window is not None
        return window

    assert _window(1).name == "Rolling Thunder"
    assert _window(7).name == "Rolling Thunder"
    assert _window(8).name == "The Bombing Halt"
    assert _window(10).name == "The Bombing Halt"
    assert _window(11).name == "Linebacker"
    assert _window(99).name == "Linebacker"


def test_no_window_before_the_first(monkeypatch: Any) -> None:
    arc = parse_red_tempo([{"from_turn": 5, "trail_surge": 2.0}])
    monkeypatch.setattr(red_tempo, "schedule_for", lambda g: arc)
    assert active_window(_game(1)) is None
    assert trail_surge_multiplier(_game(1)) == 1.0


def test_no_schedule_is_a_noop(monkeypatch: Any) -> None:
    monkeypatch.setattr(red_tempo, "schedule_for", lambda g: ())
    assert active_window(_game(5)) is None
    assert trail_surge_multiplier(_game(5)) == 1.0
    game = _game(5)
    apply_red_tempo(game)  # must not raise / message
    assert game.messages == []


# --- trail surge --------------------------------------------------------------


def test_trail_surge_reads_the_active_window(monkeypatch: Any) -> None:
    arc = _arc()
    monkeypatch.setattr(red_tempo, "schedule_for", lambda g: arc)
    assert trail_surge_multiplier(_game(1)) == 1.5
    assert trail_surge_multiplier(_game(8)) == 2.0


def test_ground_offensive_floors_the_surge(monkeypatch: Any) -> None:
    # Linebacker authors only ground_offensive (trail_surge defaults to 1.0); while
    # the pulse runs the surge is floored at GROUND_OFFENSIVE_MIN_SURGE, then drops.
    arc = _arc()
    monkeypatch.setattr(red_tempo, "schedule_for", lambda g: arc)
    assert ground_offensive_active(_game(11)) is True
    assert ground_offensive_active(_game(13)) is True
    assert trail_surge_multiplier(_game(11)) == GROUND_OFFENSIVE_MIN_SURGE
    assert ground_offensive_active(_game(14)) is False  # 3-turn pulse over
    assert trail_surge_multiplier(_game(14)) == 1.0


# --- ground-offensive stance pulse -------------------------------------------


def _front(red_cp: Any, blue_cp: Any) -> Any:
    return SimpleNamespace(
        control_point_friendly_to=lambda p: red_cp,
        control_point_hostile_to=lambda p: blue_cp,
    )


def test_ground_offensive_raises_passive_stances(monkeypatch: Any) -> None:
    from game.ground_forces.combat_stance import CombatStance

    monkeypatch.setattr(red_tempo, "schedule_for", lambda g: _arc())
    blue_cp = SimpleNamespace(id="b")
    red_cp = SimpleNamespace(stances={"b": CombatStance.DEFENSIVE})
    game = _game(11)
    game.theater = SimpleNamespace(conflicts=lambda: [_front(red_cp, blue_cp)])
    apply_red_tempo(game)
    assert red_cp.stances["b"] == CombatStance.AGGRESSIVE


def test_ground_offensive_never_lowers_a_better_stance(monkeypatch: Any) -> None:
    from game.ground_forces.combat_stance import CombatStance

    monkeypatch.setattr(red_tempo, "schedule_for", lambda g: _arc())
    blue_cp = SimpleNamespace(id="b")
    red_cp = SimpleNamespace(stances={"b": CombatStance.BREAKTHROUGH})
    game = _game(11)
    game.theater = SimpleNamespace(conflicts=lambda: [_front(red_cp, blue_cp)])
    apply_red_tempo(game)
    assert red_cp.stances["b"] == CombatStance.BREAKTHROUGH  # kept its better stance


# --- announce latch -----------------------------------------------------------


def test_announce_fires_once_per_window(monkeypatch: Any) -> None:
    monkeypatch.setattr(red_tempo, "schedule_for", lambda g: _arc())
    game = _game(8)
    apply_red_tempo(game)
    assert any("Hanoi answers" in text for _t, text in game.messages)
    count = len(game.messages)
    apply_red_tempo(game)  # same window -> no repeat
    assert len(game.messages) == count
