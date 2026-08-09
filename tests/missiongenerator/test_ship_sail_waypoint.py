from types import SimpleNamespace
from typing import Any

import pytest
from dcs.mapping import Point

from game.missiongenerator.tgogenerator import GroundObjectGenerator


def _generator(ground_object: Any) -> GroundObjectGenerator:
    return GroundObjectGenerator(
        ground_object, None, None, None, None  # type: ignore[arg-type]
    )


def test_sail_to_destination_adds_waypoint_and_speed() -> None:
    rotated: list[Any] = []
    ground_object = SimpleNamespace(rotate=lambda h: rotated.append(h))
    gen = _generator(ground_object)

    waypoints: list[tuple[Point, float]] = []
    start = SimpleNamespace(position=Point(0, 0, None), speed=0.0)  # type: ignore[arg-type]
    group = SimpleNamespace(
        points=[start],
        add_waypoint=lambda p, kph: waypoints.append((p, kph)),
    )
    destination = Point(10000, 0, None)  # type: ignore[arg-type]

    heading = gen.sail_to_destination(destination, group)  # type: ignore[arg-type]

    assert len(waypoints) == 1
    wp_point, wp_kph = waypoints[0]
    assert wp_point.x == 10000 and wp_point.y == 0
    assert wp_kph > 0
    assert start.speed > 0
    assert rotated == [heading]


def _carrier_generator(sea: bool = True) -> tuple[Any, Any, list[Any]]:
    rotated: list[Any] = []
    waypoints: list[Any] = []
    ground_object = SimpleNamespace(rotate=lambda heading: rotated.append(heading))
    wind = SimpleNamespace(direction=90.0, speed=15.0)
    game = SimpleNamespace(
        conditions=SimpleNamespace(
            weather=SimpleNamespace(wind=SimpleNamespace(at_0m=wind))
        ),
        theater=SimpleNamespace(is_in_sea=lambda point: sea),
    )
    generator = SimpleNamespace(game=game, ground_object=ground_object)
    start = SimpleNamespace(
        position=Point(0, 0, None),  # type: ignore[arg-type]
        speed=123.0,
    )
    group = SimpleNamespace(
        points=[start],
        add_waypoint=lambda point, speed: waypoints.append((point, speed)),
    )
    return generator, group, [rotated, waypoints]


def test_carrier_cruise_uses_deck_angle_solver_result() -> None:
    from game.flightplan.carriercruisesolver import solve_carrier_cruise
    from game.missiongenerator.tgogenerator import GenericCarrierGenerator

    generator, group, state = _carrier_generator()
    heading = GenericCarrierGenerator.steam_into_wind(generator, group, deck_angle=9.0)
    expected = solve_carrier_cruise(90.0, 15.0 * 1.9438444924, 9.0)

    assert heading is not None
    assert heading.degrees == round(expected.heading)
    assert group.points[0].speed == pytest.approx(expected.carrier_speed * 0.5144444444)
    assert state[1][0][1] == pytest.approx(expected.carrier_speed * 1.852)
    assert state[0] == [heading]


def test_carrier_cruise_exact_mode_applies_positive_solver_speed_to_waypoints() -> None:
    from game.flightplan.carriercruisesolver import solve_carrier_cruise
    from game.missiongenerator.tgogenerator import GenericCarrierGenerator

    generator, group, state = _carrier_generator()
    generator.game.conditions.weather.wind.at_0m.speed = 15.0 / 1.9438444924

    heading = GenericCarrierGenerator.steam_into_wind(generator, group, deck_angle=9.0)
    expected = solve_carrier_cruise(90.0, 15.0, 9.0)

    assert heading is not None
    assert expected.carrier_speed > 0
    assert heading.degrees == round(expected.heading)
    assert group.points[0].speed == pytest.approx(expected.carrier_speed * 0.5144444444)
    assert state[1][0][1] == pytest.approx(expected.carrier_speed * 1.852)
    assert state[0] == [heading]


def test_carrier_cruise_zero_offset_keeps_direct_into_wind_behavior() -> None:
    from game.missiongenerator.tgogenerator import GenericCarrierGenerator

    generator, group, _ = _carrier_generator()
    heading = GenericCarrierGenerator.steam_into_wind(generator, group, deck_angle=0.0)

    assert heading is not None
    assert heading.degrees == 270


def test_carrier_cruise_no_sea_waypoint_does_not_mutate_group() -> None:
    from game.missiongenerator.tgogenerator import GenericCarrierGenerator

    generator, group, state = _carrier_generator(sea=False)
    heading = GenericCarrierGenerator.steam_into_wind(generator, group, deck_angle=9.0)

    assert heading is None
    assert group.points[0].speed == 123.0
    assert state[1] == []
    assert state[0] == []


def test_carrier_cruise_clamps_high_wind_without_negative_speed() -> None:
    from game.missiongenerator.tgogenerator import GenericCarrierGenerator

    generator, group, _ = _carrier_generator()
    generator.game.conditions.weather.wind.at_0m.speed = 30.0 / 1.9438444924
    GenericCarrierGenerator.steam_into_wind(generator, group, deck_angle=9.0)

    assert group.points[0].speed >= 0.0
