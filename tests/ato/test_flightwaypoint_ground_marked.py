"""The CAS FLOT boundaries are planned at the flight's combat altitude because for the
AI the waypoint *is* the track to fly. A client's steerpoint there has to sit on the deck
instead, or the diamond floats at the combat altitude (20,000 ft + scatter, RADIO/AGL)
over the target area and there is nothing under it to acquire or slave a pod to.
"""

from dcs import Point
from dcs.terrain import Caucasus

from game.ato.flightwaypoint import FlightWaypoint
from game.ato.flightwaypointtype import FlightWaypointType
from game.utils import feet


def _wp(waypoint_type: FlightWaypointType, flyover: bool = False) -> FlightWaypoint:
    wp = FlightWaypoint(
        "WP",
        waypoint_type,
        Point(0, 0, Caucasus()),
        feet(22000),
        "RADIO",
    )
    wp.flyover = flyover
    return wp


def test_cas_waypoint_marks_ground_for_player() -> None:
    assert _wp(FlightWaypointType.CAS).marks_ground_for_player


def test_target_waypoints_mark_ground_for_player() -> None:
    # The escort's TARGET area is planned at the flight's combat altitude (for the
    # AI it is the track), but the pilot's row/steerpoint there is a place on the
    # ground -- the flown DS91 escort kneeboard read "Target area 22000". Strike
    # and recon targets are already planned at 0 AGL, so for them this is a no-op.
    assert _wp(FlightWaypointType.TARGET_GROUP_LOC).marks_ground_for_player
    assert _wp(FlightWaypointType.TARGET_POINT).marks_ground_for_player
    assert _wp(FlightWaypointType.TARGET_SHIP).marks_ground_for_player


def test_landing_waypoints_mark_ground_for_player() -> None:
    # A landing (or a cargo stopover) is a field on the ground for every flight
    # type. land()/cargo_stop() already plan 0 AGL; the listing makes the cockpit
    # read structural instead of relying on each producer remembering it.
    assert _wp(FlightWaypointType.LANDING_POINT).marks_ground_for_player
    assert _wp(FlightWaypointType.CARGO_STOP).marks_ground_for_player


def test_divert_is_not_ground_marked() -> None:
    # An off-map divert is an exit vector planned at cruise altitude, not a field.
    assert not _wp(FlightWaypointType.DIVERT).marks_ground_for_player


def test_flyover_waypoint_still_marks_ground_for_player() -> None:
    # Armed recon / TARPS already relied on this in the .miz; don't regress it.
    assert _wp(
        FlightWaypointType.TARGET_GROUP_LOC, flyover=True
    ).marks_ground_for_player


def test_ordinary_waypoint_does_not_mark_ground() -> None:
    # A nav waypoint's altitude is a real instruction, not a ground mark.
    assert not _wp(FlightWaypointType.NAV).marks_ground_for_player


def test_cas_ingress_is_not_ground_marked() -> None:
    # The CAS *ingress* carries the AI's EngageTargetsInZone task and is flown at
    # altitude; only the FLOT boundaries themselves are ground marks.
    assert not _wp(FlightWaypointType.INGRESS_CAS).marks_ground_for_player
