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
    # Wind from 270; the port-angled deck puts the bow clockwise of it.
    assert result.heading == pytest.approx(285.113, abs=0.01)
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

    assert positive.heading == pytest.approx(285.113, abs=0.01)
    assert negative.heading == pytest.approx(254.887, abs=0.01)
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
    # Stationary ship: the landing area (heading - 9) must face the 270 wind.
    assert result.heading == pytest.approx(279.0)
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


def _apparent_wind_from(
    heading: float, speed: float, wind_direction: float, wind_speed: float
) -> tuple[float, float]:
    """Apparent wind-from bearing and magnitude for a ship on `heading` at
    `speed` in ambient wind blowing toward `wind_direction` at `wind_speed`."""
    h = math.radians(heading)
    f = math.radians(wind_direction + 180.0)
    north = speed * math.cos(h) + wind_speed * math.cos(f)
    east = speed * math.sin(h) + wind_speed * math.sin(f)
    return math.degrees(math.atan2(east, north)) % 360.0, math.hypot(north, east)


@pytest.mark.parametrize("wind_direction", [0.0, 45.0, 110.0, 250.0, 359.0])
@pytest.mark.parametrize("wind_speed", [5.0, 9.19, 15.0, 22.0])
@pytest.mark.parametrize("deck_angle", [7.95, 9.0, 10.5])
def test_apparent_wind_runs_down_the_port_angled_deck(
    wind_direction: float, wind_speed: float, deck_angle: float
) -> None:
    # The invariant behind the B55 sign fix: in EXACT mode the apparent wind
    # must come from the landing-area direction (heading - deck_angle for the
    # port-offset decks every hull ships), not its starboard mirror.
    result = solve_carrier_cruise(wind_direction, wind_speed, deck_angle)
    assert result.mode is CarrierCruiseMode.EXACT

    from_bearing, magnitude = _apparent_wind_from(
        result.heading, result.carrier_speed, wind_direction, wind_speed
    )
    landing_area = (result.heading - deck_angle) % 360.0
    error = (from_bearing - landing_area + 180.0) % 360.0 - 180.0
    assert error == pytest.approx(0.0, abs=1e-6)
    assert magnitude == pytest.approx(25.0, abs=1e-6)


def test_baltic_fury_b55_regression() -> None:
    # The B55 desk finding (Baltic Fury turn 3): wind blowing toward 011 at
    # 9.186 kt, Stennis deck 9.0. The pre-fix solver authored 165.8 (felt wind
    # 18 degrees starboard of the landing area, 7.7 kt crosswind); the correct
    # course is the mirror.
    result = solve_carrier_cruise(11.0, 9.1861, 9.0)

    assert result.mode is CarrierCruiseMode.EXACT
    assert result.heading == pytest.approx(216.19, abs=0.01)
    assert result.carrier_speed == pytest.approx(16.38, abs=0.01)
