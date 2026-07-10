"""Tests for the forward defensive CAP line in ObjectiveFinder.

`vulnerable_control_points()` defends a friendly CP if it anchors an active front
line, in addition to the legacy "enemy airfield within threat range" rule.

A front anchor is defended unconditionally: OPFOR's offensive roll may abandon a
*rear* CP to free its fighters for offense, but never the CP holding the FLOT.
"""

from __future__ import annotations

import pytest

from game.commander.objectivefinder import ObjectiveFinder
from game.utils import Distance


class _FakePlayer:
    def __init__(self, is_red: bool) -> None:
        self.is_red = is_red


class _FakeCP:
    def __init__(self, name: str, has_active_frontline: bool) -> None:
        self.name = name
        self.has_active_frontline = has_active_frontline

    def is_friendly(self, player: object) -> bool:
        return True

    def __repr__(self) -> str:
        return f"_FakeCP({self.name})"


class _FakeTheater:
    def __init__(self, control_points: list[_FakeCP]) -> None:
        self.controlpoints = control_points


class _FakeSettings:
    airbase_threat_range = 30
    opfor_autoplanner_aggressiveness = 50


class _FakeGame:
    def __init__(self, control_points: list[_FakeCP]) -> None:
        self.theater = _FakeTheater(control_points)
        self.settings = _FakeSettings()
        self.turn = 0


class _FakeAirfield:
    """An enemy airfield: `is_friendly(viewer)` is False for the finder's side."""

    def is_friendly(self, _player: object) -> bool:
        return False


class _NoAirfields:
    operational_airfields: list[object] = []

    def operational_airfields_within(self, _distance: object) -> list[object]:
        return []


class _EnemyAirfieldNearby:
    """One enemy airfield in range -- unless the caller zeroed the threat range.

    `vulnerable_control_points` signals "abandon this CP" by passing a zero threat
    range, so honouring the distance is what makes the abandon path observable.
    """

    operational_airfields: list[object] = []

    def operational_airfields_within(self, distance: Distance) -> list[object]:
        return [] if distance.meters <= 0 else [_FakeAirfield()]


@pytest.fixture(autouse=True)
def _no_airfield_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    # The front-line path returns before this is reached; the other paths must
    # not hit the real distance cache with fake control points.
    monkeypatch.setattr(
        ObjectiveFinder,
        "closest_airfields_to",
        staticmethod(lambda _location: _NoAirfields()),
    )


def _finder(control_points: list[_FakeCP], is_red: bool) -> ObjectiveFinder:
    return ObjectiveFinder(_FakeGame(control_points), _FakePlayer(is_red))  # type: ignore[arg-type]


def test_front_line_cp_is_defended() -> None:
    cp = _FakeCP("front", has_active_frontline=True)
    finder = _finder([cp], is_red=False)
    assert cp in list(finder.vulnerable_control_points())


def test_rear_cp_without_nearby_enemy_airfield_is_not_defended() -> None:
    cp = _FakeCP("rear", has_active_frontline=False)
    finder = _finder([cp], is_red=False)
    assert cp not in list(finder.vulnerable_control_points())


def test_opfor_never_abandons_the_front_anchor(monkeypatch: pytest.MonkeyPatch) -> None:
    # aggressiveness is the ratio of threat ignored: plan_offensively when the roll
    # <= aggressiveness. Even on the lowest possible roll, the CP anchoring the FLOT
    # keeps its CAP -- stripping the front to push forward is incoherent, and on a
    # single-front theater it left the front with no red air at all.
    monkeypatch.setattr(ObjectiveFinder, "_offensive_roll", lambda _self, _cp: 1)
    cp = _FakeCP("front", has_active_frontline=True)
    finder = _finder([cp], is_red=True)
    assert cp in list(finder.vulnerable_control_points())


def test_opfor_abandons_a_rear_cp_on_a_low_offensive_roll(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The aggressiveness lever keeps its meaning on rear CPs: a low roll zeroes the
    # threat range, so the nearby enemy airfield no longer makes this CP vulnerable.
    monkeypatch.setattr(
        ObjectiveFinder,
        "closest_airfields_to",
        staticmethod(lambda _location: _EnemyAirfieldNearby()),
    )
    monkeypatch.setattr(ObjectiveFinder, "_offensive_roll", lambda _self, _cp: 1)
    cp = _FakeCP("rear", has_active_frontline=False)
    finder = _finder([cp], is_red=True)
    assert cp not in list(finder.vulnerable_control_points())


def test_opfor_defends_a_rear_cp_on_a_high_offensive_roll(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        ObjectiveFinder,
        "closest_airfields_to",
        staticmethod(lambda _location: _EnemyAirfieldNearby()),
    )
    monkeypatch.setattr(ObjectiveFinder, "_offensive_roll", lambda _self, _cp: 99)
    cp = _FakeCP("rear", has_active_frontline=False)
    finder = _finder([cp], is_red=True)
    assert cp in list(finder.vulnerable_control_points())


def test_ownfor_rear_cp_is_never_abandoned(monkeypatch: pytest.MonkeyPatch) -> None:
    # The roll is OPFOR-only; blue never abandons a threatened base.
    monkeypatch.setattr(
        ObjectiveFinder,
        "closest_airfields_to",
        staticmethod(lambda _location: _EnemyAirfieldNearby()),
    )
    monkeypatch.setattr(ObjectiveFinder, "_offensive_roll", lambda _self, _cp: 1)
    cp = _FakeCP("rear", has_active_frontline=False)
    finder = _finder([cp], is_red=False)
    assert cp in list(finder.vulnerable_control_points())


def test_offensive_roll_is_stable_within_a_turn() -> None:
    # Same (turn, CP) must produce the same roll across repeated planning passes
    # so red's posture doesn't flicker; different CPs may differ.
    finder = _finder([], is_red=True)
    cp = _FakeCP("front", has_active_frontline=True)
    rolls = {finder._offensive_roll(cp) for _ in range(5)}  # type: ignore[arg-type]
    assert len(rolls) == 1
