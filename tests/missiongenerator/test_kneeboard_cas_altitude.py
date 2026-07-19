"""The kneeboard flight plan reads the *planning* model's altitude, while the .miz zeroes
ground-marked waypoints for client flights. Kneeboards are only generated for client
flights, so the page must print what the cockpit will actually show or the two disagree
(the observed case: a CAS deck printing "22000" against a steerpoint on the deck).
"""

import datetime

from dcs import Point
from dcs.terrain import Caucasus

from game.ato.flightwaypoint import FlightWaypoint
from game.ato.flightwaypointtype import FlightWaypointType
from game.missiongenerator.kneeboard import FlightPlanBuilder
from game.utils import NauticalUnits, feet

ALT_COLUMN = 2


def _builder() -> FlightPlanBuilder:
    return FlightPlanBuilder(
        datetime.datetime(2026, 7, 16, 12, 0, 0),
        NauticalUnits(),
    )


def _wp(waypoint_type: FlightWaypointType, flyover: bool = False) -> FlightWaypoint:
    wp = FlightWaypoint(
        "FLOT START",
        waypoint_type,
        Point(0, 0, Caucasus()),
        feet(22000),
        "RADIO",
    )
    wp.pretty_name = "FLOT start"
    wp.flyover = flyover
    return wp


def test_cas_waypoint_alt_column_reads_zero() -> None:
    builder = _builder()
    builder.add_waypoint(1, _wp(FlightWaypointType.CAS))
    assert builder.rows[0][ALT_COLUMN] == "0"


def test_flyover_waypoint_alt_column_reads_zero() -> None:
    builder = _builder()
    builder.add_waypoint(1, _wp(FlightWaypointType.TARGET_GROUP_LOC, flyover=True))
    assert builder.rows[0][ALT_COLUMN] == "0"


def test_escort_target_area_alt_column_reads_zero() -> None:
    # The flown DS91 escort deck read "Target area 22000" beside a Land row of 0:
    # the escort TARGET is planned at the AI's track altitude (not a flyover), but
    # for the pilot it is a place on the ground like every other target row.
    builder = _builder()
    builder.add_waypoint(1, _wp(FlightWaypointType.TARGET_GROUP_LOC))
    assert builder.rows[0][ALT_COLUMN] == "0"


def test_ordinary_waypoint_keeps_its_planned_altitude() -> None:
    builder = _builder()
    builder.add_waypoint(1, _wp(FlightWaypointType.NAV))
    assert builder.rows[0][ALT_COLUMN] == "22000"
