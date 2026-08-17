"""The hold point must stay within reach of the departure airfield.

Flown 2026-08-16 (session `c86c58dd`): an F-16CM SEAD Sweep held **205.7 nm**
from its own runway to attack a target **23.6 nm** away -- 596 nm of routing,
and it was still outbound when the mission ended. Every coordinate below is
that flight's, read out of the generated .miz.

Two independent failures produced it, and each is pinned separately here:

1. `JoinZoneGeometry.find_best_join_point()` falls back to `join = self.ip`
   exactly, so the measured IP-to-join separation was 0.81 nm -- the 500 ft
   perturbation. The heading between them aimed the hold wedge.
2. `find_best_hold_point()` answers "nearest point of a zone" with no bound, so
   a wedge aimed anywhere strands the hold anywhere.
"""

from __future__ import annotations

from typing import Any

import pytest
from dcs.mapping import Point
from dcs.terrain.caucasus.caucasus import Caucasus
from shapely.geometry import MultiPolygon, Polygon

from game.flightplan.holdzonegeometry import (
    DEGENERATE_IP_JOIN_SEPARATION,
    HoldZoneGeometry,
    wedge_heading,
)
from game.utils import nautical_miles

TERRAIN = Caucasus()

#: The flown flight's own waypoints (4th test miz, group 442).
HOME = Point(-284824.2, 682976.7, TERRAIN)
JOIN = Point(-277210.2, 691025.7, TERRAIN)
IP = Point(-278676.2, 690711.7, TERRAIN)
TARGET = Point(-290886.3, 726290.4, TERRAIN)


# ------------------------------------------------------------- the wedge axis


def test_the_flown_geometry_is_degenerate() -> None:
    """Anchors the numbers the rest of the file relies on."""
    assert IP.distance_to_point(JOIN) == pytest.approx(1500, abs=200)
    assert IP.distance_to_point(JOIN) < DEGENERATE_IP_JOIN_SEPARATION.meters
    assert HOME.distance_to_point(TARGET) / 1852 == pytest.approx(23.6, abs=0.5)


def test_a_collapsed_join_uses_the_stable_target_axis() -> None:
    """The fix: below the threshold the wedge follows target->join, which does
    not move when the perturbation does."""
    assert wedge_heading(TARGET, IP, JOIN) == pytest.approx(
        TARGET.heading_between_point(JOIN)
    )


def test_the_perturbation_no_longer_chooses_the_wedge() -> None:
    """500 ft of jitter in any direction must not swing the axis.

    Before the fix this same loop spanned nearly the whole compass, and the
    wedge is only 40 degrees wide -- which is how the hold ended up across the
    map.
    """
    headings = []
    for dx, dy in ((150, 0), (-150, 0), (0, 150), (0, -150), (110, -110)):
        jittered = Point(IP.x + dx, IP.y + dy, TERRAIN)
        headings.append(wedge_heading(TARGET, IP, jittered))
    assert max(headings) - min(headings) < 5.0, (
        f"wedge axis swung {max(headings) - min(headings):.0f} degrees on 500 ft "
        "of jitter"
    )


def test_a_normal_separation_still_uses_the_ip_axis() -> None:
    """Unchanged for every flight that is not degenerate."""
    far_join = HOME.point_from_heading(20, nautical_miles(9).meters)
    assert IP.distance_to_point(far_join) > DEGENERATE_IP_JOIN_SEPARATION.meters
    assert wedge_heading(TARGET, IP, far_join) == pytest.approx(
        IP.heading_between_point(far_join)
    )


# ------------------------------------------------------------------ the bound


class FakeDoctrine:
    hold_distance = nautical_miles(25)
    push_distance = nautical_miles(5)


class FakeThreatZone:
    def __init__(self, shape: Any) -> None:
        self.all = shape


class FakeNavMesh:
    def map_bounds(self, theater: Any) -> Polygon:
        big = nautical_miles(600).meters
        return Polygon(
            [
                (HOME.x - big, HOME.y - big),
                (HOME.x - big, HOME.y + big),
                (HOME.x + big, HOME.y + big),
                (HOME.x + big, HOME.y - big),
            ]
        )


class FakeCoalition:
    def __init__(self, threat: Any) -> None:
        self.doctrine = FakeDoctrine()
        self.nav_mesh = FakeNavMesh()
        self.opponent = type("Opp", (), {"threat_zone": FakeThreatZone(threat)})()


def geometry(threat: Any = MultiPolygon([])) -> HoldZoneGeometry:
    return HoldZoneGeometry(
        TARGET, HOME, IP, JOIN, FakeCoalition(threat), None  # type: ignore[arg-type]
    )


def test_the_bound_replaces_a_hold_the_search_strands() -> None:
    """The backstop, exercised directly. This is what a wedge aimed anywhere
    produces, and it must not survive."""
    geo = geometry()

    stranded = Point(56711.2, 514144.4, TERRAIN)  # the flown miz's own WP1
    assert HOME.distance_to_point(stranded) / 1852 == pytest.approx(205.7, abs=1.0)

    bounded = geo._bounded(stranded)

    assert (
        HOME.distance_to_point(bounded) <= FakeDoctrine.hold_distance.meters + 1.0
    ), "a stranded hold survived the bound"


def test_an_in_range_hold_is_returned_untouched() -> None:
    geo = geometry()
    fine = HOME.point_from_heading(45, nautical_miles(10).meters)
    assert geo._bounded(fine) is fine


def test_the_hold_stays_near_home_when_the_home_ring_is_excluded() -> None:
    """End to end on the flown geometry, with the home ring excluded so the
    unbounded fallback branch is the one that runs -- as it did in the flight
    (`preferred_lines` was empty there)."""
    # Covers the 25 nm hold ring but leaves permissible airspace further out,
    # which is the shape that strands the fallback: nothing to hold on near
    # home, plenty of "nearest point" a long way away.
    near = nautical_miles(30).meters
    covers_the_hold_ring = Polygon(
        [
            (HOME.x - near, HOME.y - near),
            (HOME.x - near, HOME.y + near),
            (HOME.x + near, HOME.y + near),
            (HOME.x + near, HOME.y - near),
        ]
    )

    geo = geometry(MultiPolygon([covers_the_hold_ring]))
    assert geo.preferred_lines.is_empty, "the fallback branch is not being exercised"

    hold = geo.find_best_hold_point()

    distance = HOME.distance_to_point(hold) / 1852
    assert (
        distance <= FakeDoctrine.hold_distance.nautical_miles + 0.1
    ), f"hold placed {distance:.1f} nm from home; the flown bug put it 205.7 nm out"
