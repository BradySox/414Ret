from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from dcs import Point
from dcs.terrain import Caucasus

from game.ato.flightplans.patrolling import PatrollingFlightPlan, PatrollingLayout
from game.ato.flightwaypoint import FlightWaypoint
from game.ato.flightwaypointtype import FlightWaypointType
from game.dcs.aircrafttype import FuelConsumption
from game.utils import Distance, Speed, knots, kph, nautical_miles

T0 = datetime(2020, 1, 1, 12, 0, 0)


def _wp(
    name: str,
    kind: FlightWaypointType = FlightWaypointType.NAV,
    position: Point | None = None,
) -> FlightWaypoint:
    return FlightWaypoint(name, kind, position or Point(0, 0, Caucasus()))


class _FixedPatrolPlan(PatrollingFlightPlan[PatrollingLayout]):
    """Patrol plan with constant 2-minute travel legs for deterministic tests."""

    @property
    def patrol_duration(self) -> timedelta:
        return timedelta(minutes=30)

    @property
    def patrol_speed(self) -> Speed:
        return kph(400)

    @property
    def engagement_distance(self) -> Distance:
        return nautical_miles(10)

    def travel_time_between_waypoints(
        self, a: FlightWaypoint, b: FlightWaypoint
    ) -> timedelta:
        return timedelta(minutes=2)


def _make_patrol_plan(
    plan_type: type[_FixedPatrolPlan] = _FixedPatrolPlan,
    patrol_end: FlightWaypoint | None = None,
) -> _FixedPatrolPlan:
    layout = PatrollingLayout(
        departure=_wp("dep", FlightWaypointType.TAKEOFF),
        custom_waypoints=[],
        arrival=_wp("arr", FlightWaypointType.LANDING_POINT),
        divert=None,
        bullseye=_wp("bull", FlightWaypointType.BULLSEYE),
        nav_to=[],
        nav_from=[],
        patrol_start=_wp("ps", FlightWaypointType.PATROL_TRACK),
        patrol_end=patrol_end or _wp("pe", FlightWaypointType.PATROL),
    )
    flight = SimpleNamespace(package=SimpleNamespace(time_over_target=T0))
    return plan_type(flight, layout)  # type: ignore[arg-type]


def test_patrol_leg_carries_on_station_time() -> None:
    plan = _make_patrol_plan()
    ps = plan.layout.patrol_start
    pe = plan.layout.patrol_end
    # The on-station leg is patrol_duration (30 min), not the 2-minute travel stub. This
    # is what makes patrol_end_time = patrol_start_time + patrol_duration hold when the
    # schedule is chained leg-by-leg (manual ToT cascade, kneeboard ETAs).
    assert plan.total_time_between_waypoints(ps, pe) == timedelta(minutes=30)


def test_non_patrol_legs_are_travel_only() -> None:
    plan = _make_patrol_plan()
    ps = plan.layout.patrol_start
    pe = plan.layout.patrol_end
    # Only the patrol_start -> patrol_end orbit carries the loiter; every other leg
    # (including the reverse direction) stays at travel time.
    assert plan.total_time_between_waypoints(plan.layout.departure, ps) == timedelta(
        minutes=2
    )
    assert plan.total_time_between_waypoints(pe, plan.layout.arrival) == timedelta(
        minutes=2
    )
    assert plan.total_time_between_waypoints(pe, ps) == timedelta(minutes=2)


class _FastPatrolPlan(_FixedPatrolPlan):
    """Round-number patrol: 480 kt for 30 minutes = 240 nm of laps."""

    @property
    def patrol_speed(self) -> Speed:
        return knots(480)


class _ZeroDwellPatrolPlan(_FixedPatrolPlan):
    @property
    def patrol_duration(self) -> timedelta:
        return timedelta()


_FUEL = FuelConsumption(taxi=100, climb=50.0, cruise=20.0, combat=30.0, min_safe=1000)


def test_patrol_leg_fuel_charges_the_laps_flown_on_station() -> None:
    # The on-station leg is flown as laps for the whole patrol duration; the fuel
    # model charges that distance (patrol speed x dwell), not the one straight
    # crossing of the track. 480 kt for 30 min = 240 nm at the cruise rate.
    plan = _make_patrol_plan(_FastPatrolPlan)
    ps = plan.layout.patrol_start
    pe = plan.layout.patrol_end
    assert plan.fuel_burn_distance_between_points(ps, pe).nautical_miles == (
        pytest.approx(240.0)
    )
    burn = plan.fuel_consumption_between_points(ps, pe, _FUEL)
    assert burn == pytest.approx(240.0 * _FUEL.cruise)


def test_patrol_leg_fuel_never_charges_less_than_the_track_itself() -> None:
    # Degenerate dwell: the laps distance floors at the straight track length, so
    # the leg is never cheaper than simply crossing it.
    far_end = _wp("pe", FlightWaypointType.PATROL, Point(100 * 1852.0, 0, Caucasus()))
    plan = _make_patrol_plan(_ZeroDwellPatrolPlan, patrol_end=far_end)
    ps = plan.layout.patrol_start
    pe = plan.layout.patrol_end
    assert plan.fuel_burn_distance_between_points(ps, pe).nautical_miles == (
        pytest.approx(100.0)
    )


def test_non_patrol_legs_burn_the_straight_leg_only() -> None:
    # Transit legs are unchanged: distance is the straight leg, in either
    # direction, and the reverse of the patrol pair is a transit too.
    far_arrival = _wp(
        "arr", FlightWaypointType.LANDING_POINT, Point(0, 50 * 1852.0, Caucasus())
    )
    plan = _make_patrol_plan(_FastPatrolPlan)
    pe = plan.layout.patrol_end
    assert plan.fuel_burn_distance_between_points(
        pe, far_arrival
    ).nautical_miles == pytest.approx(50.0)
    assert plan.fuel_burn_distance_between_points(
        pe, plan.layout.patrol_start
    ).nautical_miles == pytest.approx(0.0)
