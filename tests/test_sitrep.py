from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from typing import Any, Iterable, cast

from game.debriefing import Debriefing
from game.sitrep import SideLosses, Sitrep, sitrep_band_lines
from game.theater.player import Player


def _loss(aircraft: int, front_line: int, ground_objects: int) -> Any:
    return SimpleNamespace(
        aircraft=aircraft, front_line=front_line, ground_objects=ground_objects
    )


def _capture(name: str, by: Player) -> Any:
    return SimpleNamespace(
        control_point=SimpleNamespace(name=name), captured_by_player=by
    )


def _debrief(
    blue: Any,
    red: Any,
    captures: Iterable[Any] = (),
    rescues: Iterable[str] = (),
) -> Debriefing:
    return cast(
        Debriefing,
        SimpleNamespace(
            loss_counts=lambda p: blue if p == Player.BLUE else red,
            base_captures=list(captures),
            state_data=SimpleNamespace(combat_sar_rescues=list(rescues)),
        ),
    )


def test_from_debriefing_splits_sides_captures_and_rescues() -> None:
    debrief = _debrief(
        blue=_loss(2, 5, 1),
        red=_loss(4, 11, 2),
        captures=[
            _capture("Al Dhafra", Player.BLUE),
            _capture("FOB Reaper", Player.RED),
        ],
        rescues=["unit-1", "unit-2"],
    )
    sitrep = Sitrep.from_debriefing(debrief, turn=7, day=date(1988, 6, 6))
    assert sitrep.turn == 7
    assert sitrep.friendly == SideLosses(2, 5, 1)
    assert sitrep.enemy == SideLosses(4, 11, 2)
    assert sitrep.captured == ["Al Dhafra"]  # BLUE took it
    assert sitrep.lost == ["FOB Reaper"]  # RED took it from the player
    assert sitrep.pilots_recovered == 2
    assert not sitrep.is_empty


def test_quiet_turn_is_empty() -> None:
    sitrep = Sitrep.from_debriefing(
        _debrief(_loss(0, 0, 0), _loss(0, 0, 0)), turn=3, day=date(2000, 1, 1)
    )
    assert sitrep.is_empty


def test_kneeboard_lines_formatting_and_plurals() -> None:
    sitrep = Sitrep(
        turn=7,
        day=date(1988, 6, 6),
        friendly=SideLosses(2, 5, 1),
        enemy=SideLosses(4, 11, 0),
        captured=["Al Dhafra"],
        lost=[],
        pilots_recovered=1,
    )
    lines = sitrep.kneeboard_lines()
    assert lines[0] == "Friendly losses: 2 air, 5 armor, 1 site"  # singular site
    assert lines[1] == "Enemy (claimed): 4 air, 11 armor"  # 0 sites omitted
    assert "Captured: Al Dhafra" in lines
    assert "Recovered 1 downed pilot" in lines  # singular
    assert not any(line.startswith("Lost:") for line in lines)


def test_loss_phrase_handles_none_and_site_plural() -> None:
    none_side = Sitrep(
        1, date(2000, 1, 1), SideLosses(0, 0, 0), SideLosses(0, 0, 2), [], [], 0
    )
    lines = none_side.kneeboard_lines()
    assert lines[0] == "Friendly losses: none"
    assert lines[1] == "Enemy (claimed): 2 sites"  # plural


def test_band_lines_gating() -> None:
    sitrep = Sitrep(
        7, date(1988, 6, 6), SideLosses(2, 0, 0), SideLosses(0, 0, 0), [], [], 0
    )
    empty = Sitrep(
        7, date(1988, 6, 6), SideLosses(0, 0, 0), SideLosses(0, 0, 0), [], [], 0
    )
    assert sitrep_band_lines(sitrep, enabled=False) is None  # toggle off
    assert sitrep_band_lines(None, enabled=True) is None  # turn 1 / no prior
    assert sitrep_band_lines(empty, enabled=True) is None  # quiet turn
    lines = sitrep_band_lines(sitrep, enabled=True)
    assert lines is not None
    assert lines[0] == "Turn 7 - 06 Jun 1988"
    assert lines[1] == "Friendly losses: 2 air"
