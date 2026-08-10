from __future__ import annotations

import math

import pytest

from game.flightplan.carriercruisesolver import (
    CarrierCruiseMode,
    solve_carrier_cruise,
)


def test_zero_deck_angle_is_compatible_with_direct_into_wind() -> None:
    result = solve_carrier_cruise(90.0, 10.0, 0.0)

    assert result.mode is CarrierCruiseMode.EXACT
    assert result.heading == pytest.approx(270.0)
    assert result.carrier_speed == pytest.approx(15.0)
    assert result.wind_over_deck == pytest.approx(25.0)
    assert result.down_deck_component == pytest.approx(25.0)
    assert result.crosswind_component == pytest.approx(0.0)


def test_calm_wind_with_zero_deck_angle_is_exact() -> None:
    result = solve_carrier_cruise(90.0, 0.0, 0.0)

    assert result.mode is CarrierCruiseMode.EXACT
    assert result.carrier_speed == pytest.approx(25.0)
    assert result.wind_over_deck == pytest.approx(25.0)
    assert result.down_deck_component == pytest.approx(25.0)
    assert result.crosswind_component == pytest.approx(0.0)


def test_normal_wind_solves_heading_and_speed_for_aligned_target_wod() -> None:
    result = solve_carrier_cruise(90.0, 15.0, 9.0)

    assert result.mode is CarrierCruiseMode.EXACT
    assert result.heading == pytest.approx(254.887, abs=0.01)
    assert result.carrier_speed > 0
    assert result.wind_over_deck == pytest.approx(25.0)
    assert result.down_deck_component == pytest.approx(25.0)
    assert result.crosswind_component == pytest.approx(0.0, abs=1e-9)


@pytest.mark.parametrize("wind_direction", [0.0, 359.0])
def test_heading_wraparound(wind_direction: float) -> None:
    result = solve_carrier_cruise(wind_direction, 15.0, 9.0)

    assert 0.0 <= result.heading < 360.0


def test_positive_and_negative_wind_offsets_are_mirrored() -> None:
    positive = solve_carrier_cruise(90.0, 15.0, 9.0)
    negative = solve_carrier_cruise(90.0, 15.0, -9.0)

    assert positive.heading == pytest.approx(254.887, abs=0.01)
    assert negative.heading == pytest.approx(285.113, abs=0.01)
    assert positive.carrier_speed == pytest.approx(negative.carrier_speed)


def test_weak_wind_uses_direct_into_wind_approximation() -> None:
    result = solve_carrier_cruise(90.0, 2.0, 9.0)

    assert result.mode is CarrierCruiseMode.WEAK_WIND_APPROXIMATION
    assert result.heading == pytest.approx(270.0)
    assert result.carrier_speed == pytest.approx(23.0)
    assert result.down_deck_component == pytest.approx(25.0 * math.cos(math.radians(9)))
    assert result.crosswind_component == pytest.approx(25.0 * math.sin(math.radians(9)))


def test_high_wind_clamps_speed_and_aligns_deck_with_ambient_wind() -> None:
    result = solve_carrier_cruise(90.0, 30.0, 9.0)

    assert result.mode is CarrierCruiseMode.HIGH_WIND_SPEED_CLAMP
    assert result.heading == pytest.approx(261.0)
    assert result.carrier_speed == 0.0
    assert result.wind_over_deck == pytest.approx(30.0)
    assert result.down_deck_component == pytest.approx(30.0)
    assert result.crosswind_component == pytest.approx(0.0, abs=1e-9)


def test_calm_wind_never_emits_negative_speed() -> None:
    result = solve_carrier_cruise(180.0, 0.0, 9.0)

    assert result.mode is CarrierCruiseMode.WEAK_WIND_APPROXIMATION
    assert result.carrier_speed == 25.0
    assert result.heading == pytest.approx(0.0)
    assert result.wind_over_deck == pytest.approx(25.0)


def test_result_exposes_all_modes() -> None:
    assert solve_carrier_cruise(0.0, 15.0, 9.0).mode is CarrierCruiseMode.EXACT
    assert (
        solve_carrier_cruise(0.0, 2.0, 9.0).mode
        is CarrierCruiseMode.WEAK_WIND_APPROXIMATION
    )
    assert (
        solve_carrier_cruise(0.0, 30.0, 9.0).mode
        is CarrierCruiseMode.HIGH_WIND_SPEED_CLAMP
    )
