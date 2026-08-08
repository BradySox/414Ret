"""The Waypoints tab's "Apply to all" altitude setter moves every leg that is flown.

Reported against the flight-altitude control: applying an altitude left the CAS FLOT
start and end waypoints alone. The cause was the filter's last rule, which skipped any
waypoint with an AGL (``RADIO``) reference. ``waypointbuilder.cas()`` hardcodes RADIO
at any altitude, so the FLOT boundaries were always skipped -- and because the planner
marks *everything* at or below ``AGL_TRANSITION_ALT`` RADIO, plus every helicopter leg,
the button did nothing whatsoever on a helo or a low-level plan.

The rule is now the waypoint's own planned altitude: a leg planned on the deck marks a
place on the ground and stays there, a leg planned at an altitude is a height to fly and
moves. Only ground points that carry a *non-zero* planned altitude (the helo landing
zones) still need naming in the skip list.
"""

from dcs import Point
from dcs.terrain import Caucasus

from game.ato.flightwaypoint import AltitudeReference, FlightWaypoint
from game.ato.flightwaypointtype import FlightWaypointType
from game.utils import Distance, feet, meters
from qt_ui.windows.mission.flight.waypoints.QFlightWaypointTab import (
    bulk_alt_type,
    bulk_editable,
)


def _wp(
    waypoint_type: FlightWaypointType,
    altitude: Distance = feet(20000),
    alt_type: AltitudeReference = "BARO",
) -> FlightWaypoint:
    return FlightWaypoint(
        "WP", waypoint_type, Point(0, 0, Caucasus()), altitude, alt_type
    )


def test_cas_flot_boundaries_move() -> None:
    # The reported bug. cas() plans the FLOT boundaries at the combat altitude with a
    # hardcoded RADIO reference, and the old AGL exclusion skipped them every time.
    assert bulk_editable(_wp(FlightWaypointType.CAS, feet(17000), "RADIO"))


def test_low_level_and_helo_legs_move() -> None:
    # Everything at or below AGL_TRANSITION_ALT is planned RADIO, so the old exclusion
    # meant the button was inert on a whole class of plans, not just on CAS.
    assert bulk_editable(_wp(FlightWaypointType.NAV, feet(1500), "RADIO"))
    assert bulk_editable(_wp(FlightWaypointType.INGRESS_CAS, feet(500), "RADIO"))


def test_en_route_legs_move() -> None:
    assert bulk_editable(_wp(FlightWaypointType.NAV))
    assert bulk_editable(_wp(FlightWaypointType.JOIN))
    assert bulk_editable(_wp(FlightWaypointType.PATROL_TRACK))
    assert bulk_editable(_wp(FlightWaypointType.EGRESS))


def test_tanker_legs_move() -> None:
    # Both are planned at an altitude the flight actually flies (the cruise band, and
    # 6,000 ft over the boat), so they follow the route rather than needing an opt-in.
    assert bulk_editable(_wp(FlightWaypointType.REFUEL))
    assert bulk_editable(_wp(FlightWaypointType.RECOVERY_TANKER, feet(6000)))


def test_target_points_stay_on_the_deck() -> None:
    # All three are planner-seeded at 0 ft, so the deck rule covers them without any
    # of them being named in the skip list.
    for waypoint_type in (
        FlightWaypointType.TARGET_POINT,
        FlightWaypointType.TARGET_GROUP_LOC,
        FlightWaypointType.TARGET_SHIP,
    ):
        assert not bulk_editable(_wp(waypoint_type, meters(0), "RADIO"))


def test_field_and_reference_points_stay_on_the_deck() -> None:
    for waypoint_type in (
        FlightWaypointType.TAKEOFF,
        FlightWaypointType.LANDING_POINT,
        FlightWaypointType.CARGO_STOP,
        FlightWaypointType.BULLSEYE,
    ):
        assert not bulk_editable(_wp(waypoint_type, meters(0), "RADIO"))


def test_divert_field_stays_but_off_map_exit_moves() -> None:
    # divert() plans a real field at 0 ft and an off-map divert at cruise altitude.
    # The first is a place to land; the second is an exit vector, and flying it at a
    # different altitude to the rest of the route is exactly what the control is for.
    assert not bulk_editable(_wp(FlightWaypointType.DIVERT, meters(0), "RADIO"))
    assert bulk_editable(_wp(FlightWaypointType.DIVERT))


def test_landing_zones_never_move() -> None:
    # These are planned at the helo's approach altitude, so the deck rule does not
    # catch them: raising them would put the aircraft over its LZ at cruise altitude
    # with nothing to unload onto.
    for waypoint_type in (
        FlightWaypointType.PICKUP_ZONE,
        FlightWaypointType.DROPOFF_ZONE,
        FlightWaypointType.CSAR_PICKUP,
    ):
        assert not bulk_editable(_wp(waypoint_type, feet(2000), "RADIO"))


def test_alt_type_follows_the_planner_rule() -> None:
    # The Alt Type column is read-only, so a bulk set has to leave a coherent
    # reference behind -- one button must not produce a flight at two real altitudes.
    assert bulk_alt_type(feet(20000), is_helo=False) == "BARO"
    assert bulk_alt_type(feet(5000), is_helo=False) == "RADIO"
    assert bulk_alt_type(feet(5001), is_helo=False) == "BARO"


def test_helo_legs_stay_agl() -> None:
    # Helicopters are planned AGL at every altitude; the bulk setter keeps that.
    assert bulk_alt_type(feet(20000), is_helo=True) == "RADIO"
