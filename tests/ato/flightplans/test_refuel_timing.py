"""Tests for the tanker-stop time budget.

A flight that visits a tanker spends real time cycling the boom, so the plan
must budget it: the receiver's schedule dwells at the REFUEL waypoint (shifting
takeoff and the hold push earlier), and the package tanker's on-station window
opens early enough to serve a pre-vul receiver while still covering the
post-vul service.
"""

from datetime import datetime, timedelta
from types import SimpleNamespace

from dcs import Point
from dcs.terrain import Caucasus

from game.ato.flighttype import FlightType
from game.ato.flightplans.flightplan import FlightPlan, Layout
from game.ato.flightplans.formation import FormationFlightPlan
from game.ato.flightplans.formationattack import FormationAttackLayout
from game.ato.flightplans.packagerefueling import PackageRefuelingFlightPlan
from game.ato.flightplans.patrolling import PatrollingLayout
from game.ato.flightwaypoint import FlightWaypoint
from game.ato.flightwaypointtype import FlightWaypointType
from game.ato.refueltasking import refuel_service_time
from game.utils import kph

T0 = datetime(2020, 1, 1, 12, 0, 0)

# Every waypoint sits at the same point so travel time is zero and the tests
# measure only the budgeted dwells.
_POINT = Point(0, 0, Caucasus())


def _wp(name: str, kind: FlightWaypointType = FlightWaypointType.NAV) -> FlightWaypoint:
    return FlightWaypoint(name, kind, _POINT)


def _flight(size: int = 2) -> SimpleNamespace:
    return SimpleNamespace(
        roster=SimpleNamespace(max_size=size),
        unit_type=SimpleNamespace(max_speed=kph(900), patrol_altitude=None),
        is_helo=False,
        package=SimpleNamespace(formation_speed=lambda is_helo: None),
    )


class _BarePlan(FlightPlan[Layout]):
    """Concrete stand-in exercising only the base timing math."""

    @property
    def mission_begin_on_station_time(self) -> datetime | None:
        return None


def test_refuel_waypoint_adds_service_time_to_the_leg() -> None:
    plan = _BarePlan(_flight(size=2), SimpleNamespace())  # type: ignore[arg-type]
    refuel = _wp("refuel", FlightWaypointType.REFUEL)
    join = _wp("join", FlightWaypointType.JOIN)
    assert plan.total_time_between_waypoints(refuel, join) == refuel_service_time(2)
    # A plain nav edge gets no dwell.
    assert plan.total_time_between_waypoints(join, refuel) == timedelta()


def test_refuel_duration_scales_with_flight_size() -> None:
    assert refuel_service_time(1) == timedelta(minutes=5)
    assert refuel_service_time(2) == timedelta(minutes=9)
    assert refuel_service_time(4) == timedelta(minutes=17)


class _Formation(FormationFlightPlan):
    @property
    def package_speed_waypoints(self) -> set[FlightWaypoint]:
        return set()

    @property
    def join_time(self) -> datetime:
        return T0

    @property
    def split_time(self) -> datetime:
        return T0


def _formation_layout(refuel_pre: FlightWaypoint | None) -> FormationAttackLayout:
    return FormationAttackLayout(
        departure=_wp("dep", FlightWaypointType.TAKEOFF),
        hold=_wp("hold", FlightWaypointType.LOITER),
        nav_to=[],
        join=_wp("join", FlightWaypointType.JOIN),
        ingress=_wp("ingress", FlightWaypointType.INGRESS_DEAD),
        targets=[_wp("target", FlightWaypointType.TARGET_POINT)],
        split=_wp("split", FlightWaypointType.SPLIT),
        refuel=None,
        refuel_pre=refuel_pre,
        nav_from=[],
        arrival=_wp("arr", FlightWaypointType.LANDING_POINT),
        divert=None,
        bullseye=_wp("bull", FlightWaypointType.BULLSEYE),
        custom_waypoints=[],
    )


def test_push_time_includes_the_pre_vul_tanker_stop() -> None:
    refuel_pre = _wp("refuel", FlightWaypointType.REFUEL)
    plan = _Formation(_flight(size=2), _formation_layout(refuel_pre))  # type: ignore[arg-type]
    # All travel is zero, so pushing early exactly covers the boom time.
    assert plan.push_time == T0 - refuel_service_time(2)


def test_push_time_without_a_tanker_is_unchanged() -> None:
    plan = _Formation(_flight(size=2), _formation_layout(None))  # type: ignore[arg-type]
    assert plan.push_time == T0


def _patrol_layout() -> PatrollingLayout:
    return PatrollingLayout(
        departure=_wp("dep", FlightWaypointType.TAKEOFF),
        nav_to=[],
        patrol_start=_wp("ps", FlightWaypointType.PATROL_TRACK),
        patrol_end=_wp("pe", FlightWaypointType.PATROL),
        nav_from=[],
        arrival=_wp("arr", FlightWaypointType.LANDING_POINT),
        divert=None,
        bullseye=_wp("bull", FlightWaypointType.BULLSEYE),
        custom_waypoints=[],
    )


def _receiver(size: int, refuel_pre_time: datetime | None = None) -> SimpleNamespace:
    refuel_pre = None if refuel_pre_time is None else _wp("refuel")
    return SimpleNamespace(
        flight_type=FlightType.DEAD,
        unit_type=SimpleNamespace(can_refuel_from=lambda tanker: True),
        roster=SimpleNamespace(max_size=size),
        flight_plan=SimpleNamespace(
            layout=SimpleNamespace(refuel_pre=refuel_pre),
            chained_tot_for_waypoint=lambda waypoint: refuel_pre_time,
        ),
    )


def _tanker_plan(receivers: list[SimpleNamespace]) -> PackageRefuelingFlightPlan:
    flight = _flight(size=1)
    flight.package = SimpleNamespace(
        time_over_target=T0,
        target=SimpleNamespace(position=_POINT),
        waypoints=SimpleNamespace(split=_POINT, refuel=_POINT),
        flights=receivers,
        formation_speed=lambda is_helo: None,
    )
    return PackageRefuelingFlightPlan(flight, _patrol_layout())  # type: ignore[arg-type]


def test_tanker_window_is_post_vul_without_pre_vul_receivers() -> None:
    plan = _tanker_plan([_receiver(size=2)])
    post_vul = T0 - timedelta(minutes=1.5)
    assert plan.patrol_start_time == post_vul
    assert plan.patrol_duration == timedelta(minutes=5) + refuel_service_time(2)


def test_tanker_window_opens_early_for_a_pre_vul_receiver() -> None:
    pre_vul_arrival = T0 - timedelta(minutes=60)
    plan = _tanker_plan([_receiver(size=2, refuel_pre_time=pre_vul_arrival)])
    post_vul = T0 - timedelta(minutes=1.5)
    service = timedelta(minutes=5) + refuel_service_time(2)
    assert plan.patrol_start_time == pre_vul_arrival - timedelta(minutes=1.5)
    # The stay stretches by the early opening, so the window still ends after
    # the post-vul service.
    assert plan.patrol_end_time == post_vul + service
