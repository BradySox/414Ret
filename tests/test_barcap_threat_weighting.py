"""Tests for additive threat-weighted BARCAP volume.

`ObjectiveFinder.air_threat_score` scores how contested a defended CP is, and
`threat_weighted_barcap_rounds` adds BARCAP waves to contested sectors *on top
of* the legacy baseline. The weighting is additive: a defended CP never gets
fewer waves than the legacy flat allocation, so it cannot regress coverage.
"""

from __future__ import annotations

import pytest

from game.commander.objectivefinder import FRONT_LINE_AIR_THREAT, ObjectiveFinder
from game.commander.theaterstate import (
    BARCAP_THREAT_CEILING,
    threat_weighted_barcap_rounds,
)
from game.utils import nautical_miles

# --------------------------------------------------------------------------- #
# threat_weighted_barcap_rounds (additive: never below baseline)
# --------------------------------------------------------------------------- #


def test_no_threat_anywhere_falls_back_to_baseline() -> None:
    assert threat_weighted_barcap_rounds(2, 0.0, 0.0, False) == 2


def test_fleet_keeps_2x_multiplier_on_fallback() -> None:
    assert threat_weighted_barcap_rounds(2, 0.0, 0.0, True) == 4


def test_quiet_cp_never_below_baseline() -> None:
    # A quiet flank (score 0) while another sector is hot still gets the full
    # legacy baseline -- the additive scheme cannot reduce coverage.
    assert threat_weighted_barcap_rounds(2, 0.0, 10.0, False) == 2


def test_hottest_sector_gets_ceiling() -> None:
    assert (
        threat_weighted_barcap_rounds(2, 10.0, 10.0, False) == 2 * BARCAP_THREAT_CEILING
    )


def test_hot_sector_outweighs_quiet_flank() -> None:
    hot = threat_weighted_barcap_rounds(2, 10.0, 10.0, False)
    quiet = threat_weighted_barcap_rounds(2, 1.0, 10.0, False)
    assert hot > quiet


def test_fleet_scales_above_quiet_land() -> None:
    hot_fleet = threat_weighted_barcap_rounds(2, 10.0, 10.0, True)
    quiet_land = threat_weighted_barcap_rounds(2, 0.0, 10.0, False)
    assert hot_fleet > quiet_land


# --------------------------------------------------------------------------- #
# ObjectiveFinder.air_threat_score
# --------------------------------------------------------------------------- #


class _Player:
    def __init__(self, is_red: bool) -> None:
        self.is_red = is_red


class _AircraftType:
    """A fake aircraft type; ``fighter`` controls A2A capability."""

    def __init__(self, fighter: bool = True) -> None:
        self._fighter = fighter

    def capable_of(self, _task: object) -> bool:
        return self._fighter


_FIGHTER = _AircraftType(fighter=True)
_BOMBER = _AircraftType(fighter=False)


class _Allocations:
    def __init__(self, present: dict[_AircraftType, int]) -> None:
        self.present = present


class _Airfield:
    def __init__(
        self,
        name: str,
        distance_m: float,
        present: int,
        friendly: bool,
        fighter: bool = True,
    ):
        self.name = name
        self._distance_m = distance_m
        self._present = present
        self._friendly = friendly
        self._type = _FIGHTER if fighter else _BOMBER

    def distance_to(self, _other: object) -> float:
        return self._distance_m

    def is_friendly(self, _player: object) -> bool:
        return self._friendly

    def allocated_aircraft(self, _parking_type: object) -> _Allocations:
        return _Allocations({self._type: self._present})


class _Closest:
    def __init__(self, airfields: list[_Airfield]) -> None:
        self._airfields = airfields

    def operational_airfields_within(self, _distance: object) -> list[_Airfield]:
        return self._airfields


class _Settings:
    airbase_threat_range = 100


class _Theater:
    controlpoints: list[object] = []


class _Game:
    settings = _Settings()
    theater = _Theater()


def _finder(
    airfields: list[_Airfield], monkeypatch: pytest.MonkeyPatch
) -> ObjectiveFinder:
    finder = ObjectiveFinder(_Game(), _Player(is_red=False))  # type: ignore[arg-type]
    monkeypatch.setattr(
        ObjectiveFinder,
        "closest_airfields_to",
        staticmethod(lambda _location: _Closest(airfields)),
    )
    return finder


class _CP:
    name = "cp"
    has_active_frontline = False


class _FrontLineCP:
    name = "front"
    has_active_frontline = True


def test_air_threat_score_zero_with_no_enemy_in_range(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    finder = _finder([], monkeypatch)
    assert finder.air_threat_score(_CP()) == 0.0  # type: ignore[arg-type]


def test_air_threat_score_excludes_friendly_airfields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    friendly = _Airfield("friendly", nautical_miles(10).meters, 20, friendly=True)
    finder = _finder([friendly], monkeypatch)
    assert finder.air_threat_score(_CP()) == 0.0  # type: ignore[arg-type]


def test_air_threat_score_higher_for_closer_and_stronger(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    close_strong = _Airfield("a", nautical_miles(20).meters, 24, friendly=False)
    far_weak = _Airfield("b", nautical_miles(90).meters, 4, friendly=False)

    strong = _finder([close_strong], monkeypatch).air_threat_score(_CP())  # type: ignore[arg-type]
    weak = _finder([far_weak], monkeypatch).air_threat_score(_CP())  # type: ignore[arg-type]
    assert strong > weak > 0.0


def test_air_threat_score_ignores_non_fighters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A base packed with bombers/tankers/transports is not an air threat.
    bombers = _Airfield(
        "b", nautical_miles(20).meters, 24, friendly=False, fighter=False
    )
    finder = _finder([bombers], monkeypatch)
    assert finder.air_threat_score(_CP()) == 0.0  # type: ignore[arg-type]


def test_air_threat_score_front_line_floor_without_airbase(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A contested front with no nearby enemy airbase still scores the floor so it
    # earns extra BARCAP waves instead of collapsing to baseline.
    finder = _finder([], monkeypatch)
    assert finder.air_threat_score(_FrontLineCP()) == FRONT_LINE_AIR_THREAT  # type: ignore[arg-type]


def test_air_threat_score_front_line_floor_is_additive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A front-line CP that *also* has a nearby enemy airbase is the hottest kind
    # of sector: the floor adds on top of the airbase contribution.
    close_strong = _Airfield("a", nautical_miles(20).meters, 24, friendly=False)
    rear = _finder([close_strong], monkeypatch).air_threat_score(_CP())  # type: ignore[arg-type]
    front = _finder([close_strong], monkeypatch).air_threat_score(_FrontLineCP())  # type: ignore[arg-type]
    assert front == rear + FRONT_LINE_AIR_THREAT
