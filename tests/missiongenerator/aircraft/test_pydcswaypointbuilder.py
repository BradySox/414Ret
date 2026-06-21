from datetime import datetime, timedelta
from types import SimpleNamespace

from dcs import Point
from dcs.terrain import Caucasus

from game.ato.flightwaypoint import FlightWaypoint
from game.ato.flightwaypointtype import FlightWaypointType
from game.missiongenerator.aircraft.waypoints.pydcswaypointbuilder import (
    PydcsWaypointBuilder,
)

T0 = datetime(2020, 1, 1, 12, 0, 0)


class _FakeMovingPoint:
    """Minimal stand-in for a pydcs MovingPoint -- only the ETA fields are exercised."""

    def __init__(self) -> None:
        self.ETA: int = 0
        self.ETA_locked: bool = False
        self.speed_locked: bool = False


def _make_builder(
    client_count: int,
    locked_tot: datetime | None,
    display_tot: datetime | None,
) -> PydcsWaypointBuilder:
    waypoint = FlightWaypoint("wp", FlightWaypointType.NAV, Point(0, 0, Caucasus()))
    flight = SimpleNamespace(
        client_count=client_count,
        unit_type=SimpleNamespace(dcs_unit_type=object()),  # not an AJS37 Viggen
        flight_plan=SimpleNamespace(
            effective_tot_for_waypoint=lambda wp: locked_tot,
            chained_tot_for_waypoint=lambda wp: display_tot,
        ),
    )
    builder = PydcsWaypointBuilder.__new__(PydcsWaypointBuilder)
    builder.waypoint = waypoint
    builder.flight = flight  # type: ignore[assignment]
    builder.now = T0
    return builder


def test_player_auto_waypoint_locks_eta() -> None:
    display = T0 + timedelta(minutes=10)
    builder = _make_builder(client_count=1, locked_tot=None, display_tot=display)
    point = _FakeMovingPoint()
    builder._assign_waypoint_tot(point)  # type: ignore[arg-type]
    # Player flights feed waypoint ETAs into the jet's nav computer, so the chained ToT
    # must be locked into the DCS ETA -- otherwise the cockpit time-on-waypoint is wrong.
    assert point.ETA_locked is True
    assert point.ETA == int(timedelta(minutes=10).total_seconds())
    assert builder.waypoint.tot == display


def test_ai_auto_waypoint_leaves_eta_unlocked() -> None:
    display = T0 + timedelta(minutes=10)
    builder = _make_builder(client_count=0, locked_tot=None, display_tot=display)
    point = _FakeMovingPoint()
    builder._assign_waypoint_tot(point)  # type: ignore[arg-type]
    # AI flights keep the DCS ETA flexible (no over-constraint); only the kneeboard model
    # field is populated.
    assert point.ETA_locked is False
    assert builder.waypoint.tot == display


def test_anchored_waypoint_locks_for_ai_and_player() -> None:
    anchor = T0 + timedelta(minutes=5)
    builder = _make_builder(client_count=0, locked_tot=anchor, display_tot=None)
    point = _FakeMovingPoint()
    builder._assign_waypoint_tot(point)  # type: ignore[arg-type]
    # Structural / manual ToTs are always locked, regardless of player presence.
    assert point.ETA_locked is True
    assert point.ETA == int(timedelta(minutes=5).total_seconds())
