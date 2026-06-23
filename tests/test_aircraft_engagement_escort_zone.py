"""Tests for the fighter *engagement-reach* threat zone used by escort planning.

The air-to-air escort-need decision (``PackageFulfiller.check_needed_escorts``)
used to test a package's escorted waypoints against ``airbases`` -- the enemy
BARCAP *orbit* zone, which ``barcap_threat_range`` deliberately clamps to ~45%
of the way to friendly territory so enemy CAP is not modeled as offensive. A CAS
package orbits on the FLOT (~50% of the way), so its escorted waypoints fell
just outside that clamped zone, the A2A escort was pruned, and -- since CAS is
the only proposer of TARCAP -- TARCAP was never planned. The same gap silently
dropped escorts for other forward packages (DEAD/BAI near the front).

``ThreatZones.air_engagement`` is the *uncapped* fighter reach, used only for the
escort-need decision; the clamped ``airbases`` view still drives the navmesh and
BARCAP placement.
"""

from __future__ import annotations

from dcs.mapping import Point
from shapely.geometry import Point as ShapelyPoint, Polygon

from game.ato.flightwaypoint import FlightWaypoint
from game.ato.flightwaypointtype import FlightWaypointType
from game.data.doctrine import MODERN_DOCTRINE
from game.threatzones import ThreatZones
from game.utils import nautical_miles


def _pt(x: float, y: float) -> Point:
    # Terrain is irrelevant to the planar math exercised here.
    return Point(x, y, None)  # type: ignore[arg-type]


def _segment(distance_m: float) -> list[FlightWaypoint]:
    """A short patrol segment centered ``distance_m`` east of the origin.

    Mirrors a real escorted-waypoints leg (e.g. CAS patrol_start -> patrol_end):
    a single point would build a degenerate one-vertex LineString, which shapely
    rejects, so the production code never passes fewer than two.
    """
    span = nautical_miles(5).meters
    return [
        FlightWaypoint("START", FlightWaypointType.PATROL, _pt(distance_m, -span)),
        FlightWaypoint("END", FlightWaypointType.PATROL, _pt(distance_m, span)),
    ]


def _zone(orbit_radius_m: float, engagement_radius_m: float) -> ThreatZones:
    """A threat zone with concentric orbit/engagement circles about the origin."""
    origin = ShapelyPoint(0, 0)
    return ThreatZones(
        theater=None,  # type: ignore[arg-type]
        airbases=origin.buffer(orbit_radius_m),
        air_defenses=Polygon(),
        radar_sam_threats=Polygon(),
        air_engagement=origin.buffer(engagement_radius_m),
    )


def test_engagement_range_is_the_uncapped_sum() -> None:
    # The engagement reach is the unclamped cap_max_distance + engagement_range,
    # i.e. barcap_threat_range without the 0.45-to-the-enemy-airfield cap.
    expected = (
        MODERN_DOCTRINE.cap_max_distance_from_cp + MODERN_DOCTRINE.cap_engagement_range
    )
    assert ThreatZones.aircraft_engagement_range(MODERN_DOCTRINE) == expected


def test_front_line_waypoint_needs_escort_via_engagement_not_orbit_zone() -> None:
    # Orbit zone clamped at 45 NM, fighters reach 90 NM. A waypoint on the FLOT at
    # 60 NM sits in the gap: the old orbit-zone check misses it, the new
    # engagement-zone check catches it.
    tz = _zone(nautical_miles(45).meters, nautical_miles(90).meters)
    flot = _segment(nautical_miles(60).meters)

    assert tz.waypoints_threatened_by_aircraft(flot) is False
    assert tz.waypoints_threatened_by_aircraft_engagement(flot) is True


def test_engagement_zone_is_a_superset_of_the_orbit_zone() -> None:
    # A waypoint already inside the clamped orbit zone is still flagged, so the
    # broader check never *loses* an escort the old logic would have planned.
    tz = _zone(nautical_miles(45).meters, nautical_miles(90).meters)
    deep = _segment(nautical_miles(30).meters)

    assert tz.waypoints_threatened_by_aircraft(deep) is True
    assert tz.waypoints_threatened_by_aircraft_engagement(deep) is True


def test_waypoint_beyond_fighter_reach_needs_no_escort() -> None:
    tz = _zone(nautical_miles(45).meters, nautical_miles(90).meters)
    far = _segment(nautical_miles(120).meters)

    assert tz.waypoints_threatened_by_aircraft_engagement(far) is False


def test_default_zone_has_no_engagement_threat() -> None:
    # Callers/tests that don't supply air_engagement keep the old (empty) behavior.
    tz = ThreatZones(
        theater=None,  # type: ignore[arg-type]
        airbases=Polygon(),
        air_defenses=Polygon(),
        radar_sam_threats=Polygon(),
    )
    assert tz.waypoints_threatened_by_aircraft_engagement(_segment(0.0)) is False
