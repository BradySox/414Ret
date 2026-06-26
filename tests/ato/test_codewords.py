from __future__ import annotations

from types import SimpleNamespace

from game.ato.codewords import (
    _THEMES,
    MissionCodeWords,
    PushCategory,
    present_categories,
    push_category_for,
)
from game.ato.flighttype import FlightType
from game.coalition import Coalition


def test_generate_assigns_every_push_category_with_distinct_words() -> None:
    cw = MissionCodeWords.generate()
    assert set(cw.push) == set(PushCategory)
    words = list(cw.push.values()) + [cw.success, cw.abort, cw.stop_jam]
    assert len(set(words)) == len(words)  # all distinct
    assert cw.theme in _THEMES


def test_push_for_maps_task_to_its_category_and_none_for_support() -> None:
    cw = MissionCodeWords.generate()
    assert cw.push_for(FlightType.SEAD) == cw.push[PushCategory.SEAD]
    assert cw.push_for(FlightType.STRIKE) == cw.push[PushCategory.STRIKE]
    # A support task that doesn't "push" has no push word.
    assert cw.push_for(FlightType.REFUELING) is None


def test_category_mapping_and_present_categories() -> None:
    assert push_category_for(FlightType.DEAD) is PushCategory.SEAD
    assert push_category_for(FlightType.BARCAP) is PushCategory.CAP
    assert push_category_for(FlightType.AEWC) is None

    present = present_categories(
        [FlightType.SEAD, FlightType.STRIKE, FlightType.REFUELING]
    )
    assert present == {PushCategory.SEAD, PushCategory.STRIKE}


def test_coalition_code_words_stable_within_turn_fresh_next_turn() -> None:
    # __new__ exercises the property without constructing a full Coalition.
    coalition = Coalition.__new__(Coalition)
    coalition.game = SimpleNamespace(turn=1)  # type: ignore[assignment]

    first = coalition.code_words
    assert coalition.code_words is first  # stable while the planner briefs this turn

    coalition.game.turn = 2
    assert coalition.code_words is not first  # a new turn draws a fresh table


def test_coalition_code_words_migrates_saves_without_the_field() -> None:
    coalition = Coalition.__new__(Coalition)
    coalition.game = SimpleNamespace(turn=1)  # type: ignore[assignment]
    assert not hasattr(coalition, "_code_words")  # pre-feature pickle

    assigned = coalition.code_words
    assert coalition.code_words is assigned  # stable after lazy assignment
