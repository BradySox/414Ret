"""Tests for threat-weighted BARCAP volume.

`ObjectiveFinder.air_threat_score` scores how contested a defended CP is, and
`threat_weighted_barcap_rounds` turns that into per-CP wave counts so hot
sectors get more BARCAP than quiet flanks.
"""

from __future__ import annotations

import pytest

from game.commander.objectivefinder import ObjectiveFinder
from game.commander.theaterstate import (
    BARCAP_MIN_ROUNDS,
    BARCAP_THREAT_CEILING,
    barcap_coverage_rounds,
    threat_weighted_barcap_rounds,
)
from game.utils import nautical_miles

# --------------------------------------------------------------------------- #
# barcap_coverage_rounds
# --------------------------------------------------------------------------- #


def test_one_wave_covers_a_mission_within_on_station_time() -> None:
    # 60-min on-station spans a 60-min mission -> a single wave suffices.
    assert barcap_coverage_rounds(3600, 3600, 900) == 1


def test_long_mission_needs_more_waves() -> None:
    # 150-min mission, 60-min on-station, 15-min overlap (effective 45 min):
    # ceil((150-60)/45) + 1 = 2 + 1 = 3.
    assert barcap_coverage_rounds(9000, 3600, 900) == 3


def test_coverage_floor_never_below_one() -> None:
    assert barcap_coverage_rounds(1800, 3600, 900) == BARCAP_MIN_ROUNDS


# --------------------------------------------------------------------------- #
# threat_weighted_barcap_rounds
# --------------------------------------------------------------------------- #


def test_no_threat_anywhere_falls_back_to_baseline() -> None:
    # Legacy behavior: with no measurable threat, every CP gets baseline rounds.
    assert threat_weighted_barcap_rounds(2, 0.0, 0.0, False, False) == 2


def test_fleet_keeps_2x_multiplier_on_fallback() -> None:
    assert threat_weighted_barcap_rounds(2, 0.0, 0.0, True, False) == 4


def test_hottest_sector_gets_ceiling() -> None:
    rounds = threat_weighted_barcap_rounds(2, 10.0, 10.0, False, False)
    assert rounds == 2 * BARCAP_THREAT_CEILING


def test_quiet_defended_cp_drops_to_floor() -> None:
    rounds = threat_weighted_barcap_rounds(2, 0.0, 10.0, False, False)
    assert rounds == BARCAP_MIN_ROUNDS


def test_hot_sector_outweighs_quiet_flank() -> None:
    hot = threat_weighted_barcap_rounds(2, 10.0, 10.0, False, False)
    quiet = threat_weighted_barcap_rounds(2, 1.0, 10.0, False, False)
    assert hot > quiet


def test_frontline_cp_floored_above_cold_flank() -> None:
    # A front-line CP with no nearby enemy airfield (score 0) still rates above
    # the cold-flank floor thanks to BARCAP_FRONTLINE_MIN_FACTOR.
    frontline = threat_weighted_barcap_rounds(2, 0.0, 10.0, False, True)
    cold = threat_weighted_barcap_rounds(2, 0.0, 10.0, False, False)
    assert frontline > cold


# --------------------------------------------------------------------------- #
# ObjectiveFinder.air_threat_score
# --------------------------------------------------------------------------- #


class _Player:
    def __init__(self, is_red: bool) -> None:
        self.is_red = is_red


class _Allocations:
    def __init__(self, total_present: int) -> None:
        self.total_present = total_present


class _Airfield:
    def __init__(self, name: str, distance_m: float, present: int, friendly: bool):
        self.name = name
        self._distance_m = distance_m
        self._present = present
        self._friendly = friendly

    def distance_to(self, _other: object) -> float:
        return self._distance_m

    def is_friendly(self, _player: object) -> bool:
        return self._friendly

    def allocated_aircraft(self, _parking_type: object) -> _Allocations:
        return _Allocations(self._present)


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
