"""Tests for RefuelingFlightPlan.patrol_speed.

Tankers don't carry an explicit racetrack speed in their data files, so the
fallback path is what every planned tanker actually uses. It should estimate the
speed from the airframe at the same altitude the orbit is planned at, rather than
returning a flat constant.
"""

from datetime import datetime
from types import SimpleNamespace

from dcs import Point
from dcs.terrain import Caucasus

from game.ato.flightplans.patrolling import PatrollingLayout
from game.ato.flightplans.refuelingflightplan import RefuelingFlightPlan
from game.ato.flightwaypoint import FlightWaypoint
from game.ato.flightwaypointtype import FlightWaypointType
from game.utils import feet, knots

T0 = datetime(2020, 1, 1, 12, 0, 0)


class _Refueling(RefuelingFlightPlan):
    """Concrete stand-in; RefuelingFlightPlan already implements every abstract."""


def _wp(name: str, kind: FlightWaypointType = FlightWaypointType.NAV) -> FlightWaypoint:
    return FlightWaypoint(name, kind, Point(0, 0, Caucasus()))


def _layout() -> PatrollingLayout:
    return PatrollingLayout(
        departure=_wp("dep", FlightWaypointType.TAKEOFF),
        custom_waypoints=[],
        arrival=_wp("arr", FlightWaypointType.LANDING_POINT),
        divert=None,
        bullseye=_wp("bull", FlightWaypointType.BULLSEYE),
        nav_to=[],
        nav_from=[],
        patrol_start=_wp("ps", FlightWaypointType.PATROL_TRACK),
        patrol_end=_wp("pe", FlightWaypointType.PATROL),
    )


def _plan(unit_type: object) -> _Refueling:
    flight = SimpleNamespace(
        unit_type=unit_type, package=SimpleNamespace(time_over_target=T0)
    )
    return _Refueling(flight, _layout())  # type: ignore[arg-type]


def test_explicit_patrol_speed_is_used_without_estimating() -> None:
    explicit = knots(390)
    seen: list[object] = []

    def estimate(altitude: object) -> object:
        seen.append(altitude)
        return knots(1)

    unit_type = SimpleNamespace(
        patrol_speed=explicit,
        preferred_patrol_altitude=feet(20000),
        preferred_patrol_speed=estimate,
    )
    assert _plan(unit_type).patrol_speed is explicit
    # An explicit speed short-circuits the estimate entirely.
    assert seen == []


def test_falls_back_to_estimate_at_the_planned_orbit_altitude() -> None:
    altitude = feet(13000)
    estimated = knots(318)
    seen: list[object] = []

    def estimate(alt: object) -> object:
        seen.append(alt)
        return estimated

    unit_type = SimpleNamespace(
        patrol_speed=None,
        preferred_patrol_altitude=altitude,
        preferred_patrol_speed=estimate,
    )
    assert _plan(unit_type).patrol_speed is estimated
    # The estimate is taken at the same altitude the racetrack is planned at.
    assert seen == [altitude]
