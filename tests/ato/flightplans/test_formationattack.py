from __future__ import annotations

from typing import Any, cast

import pytest
from dcs import Point
from dcs.terrain import Caucasus, Terrain

from game.ato.flight import Flight
from game.ato.flightplans.formationattack import FormationAttackFlightPlan
from game.ato.flighttype import FlightType
from game.ato.flightwaypoint import FlightWaypoint
from game.ato.flightwaypointtype import FlightWaypointType
from game.ato.package import Package
from game.utils import Speed, knots


class _StubPackage:
    def __init__(self, formation_speed: Speed | None) -> None:
        self._formation_speed = formation_speed

    def formation_speed(self, is_helo: bool) -> Speed | None:
        return self._formation_speed


class _StubFlight:
    def __init__(self, package: Package) -> None:
        self.package = package
        self.is_helo = False


class _FormationAttackUnderTest(FormationAttackFlightPlan):
    """Minimal concrete flight plan exercising ``speed_between_waypoints``.

    The real collaborators (package, flight, formation speed) are stubbed so the
    test focuses on how the target-area segment is priced.
    """

    def __init__(self, formation_speed: Speed | None, fallback_speed: Speed) -> None:
        package = cast(Package, _StubPackage(formation_speed))
        self.flight = cast(Flight, _StubFlight(package))
        self._fallback_speed = fallback_speed

    @property
    def best_flight_formation_speed(self) -> Speed:
        return self._fallback_speed


@pytest.fixture(name="target_waypoint")
def target_waypoint_fixture() -> FlightWaypoint:
    terrain: Terrain = Caucasus()
    return FlightWaypoint(
        "TARGET AREA",
        FlightWaypointType.TARGET_GROUP_LOC,
        Point(0, 0, terrain),
    )


def test_uses_package_formation_speed_at_target_when_available(
    target_waypoint: FlightWaypoint,
) -> None:
    formation_speed = knots(400)
    plan = _FormationAttackUnderTest(formation_speed, fallback_speed=knots(500))

    speed = plan.speed_between_waypoints(target_waypoint, target_waypoint)

    assert speed == formation_speed


def test_falls_back_to_flight_speed_when_package_has_no_formation_speed(
    target_waypoint: FlightWaypoint,
) -> None:
    fallback_speed = knots(250)
    plan = _FormationAttackUnderTest(
        formation_speed=None, fallback_speed=fallback_speed
    )

    speed = plan.speed_between_waypoints(target_waypoint, target_waypoint)

    assert speed == fallback_speed


def test_slow_tag_along_is_capped_at_its_own_speed(
    target_waypoint: FlightWaypoint,
) -> None:
    # The TARPS drone excluded from Package.formation_speed faces a package
    # speed faster than it can fly; its own legs stay at its own capability.
    own_speed = knots(169)
    plan = _FormationAttackUnderTest(knots(400), fallback_speed=own_speed)

    speed = plan.speed_between_waypoints(target_waypoint, target_waypoint)

    assert speed == own_speed


class _SpeedOnlyPlan(FormationAttackFlightPlan):
    """FormationFlightPlan stand-in exposing only a formation speed."""

    def __init__(self, speed: Speed) -> None:
        self._speed = speed

    @property
    def best_flight_formation_speed(self) -> Speed:
        return self._speed


def _package_flight(flight_type: FlightType, speed: Speed) -> Flight:
    from types import SimpleNamespace

    return cast(
        Flight,
        SimpleNamespace(
            flight_type=flight_type,
            is_helo=False,
            flight_plan=_SpeedOnlyPlan(speed),
        ),
    )


def _package_with(*flights: Flight) -> Package:
    package = Package(target=cast(Any, None), db=cast(Any, None))
    package.flights = list(flights)
    return package


def test_package_formation_speed_ignores_the_tag_along_tarps_bird() -> None:
    # The auto-added TARPS/BDA drone rides the package on its own ToT offset;
    # it must not drag a Hornet DEAD package's formation legs to MQ-9 pace.
    package = _package_with(
        _package_flight(FlightType.DEAD, knots(519)),
        _package_flight(FlightType.SEAD, knots(422)),
        _package_flight(FlightType.TARPS, knots(169)),
    )
    speed = package.formation_speed(is_helo=False)
    assert speed == knots(422)


def test_recon_package_still_paces_to_its_primary_tarps_bird() -> None:
    # A package whose *primary* is TARPS (a recon package) keeps the recon
    # bird in the formation-speed minimum so its escort stays with it.
    package = _package_with(
        _package_flight(FlightType.TARPS, knots(169)),
        _package_flight(FlightType.ESCORT, knots(517)),
    )
    speed = package.formation_speed(is_helo=False)
    assert speed == knots(169)
