"""The front line is measured against the ground armour can actually hold.

`frontline_bounds` used to cast one ray each way from the centre and stop at the
first inclusion-zone boundary. `find_ground_position` hands it a centre sitting
exactly ON that boundary whenever the route crosses the edge of the drivable
zone, and from there the ray toward the usable ground stops at nought while the
ray into ground no vehicle can enter never meets a boundary and takes the full
half-width. Reproduced on Caucasus - Northern Russia (Kutaisi/Khashuri FOB): a
20 km front with 0% of it on drivable ground, blue and red bunched 15 km apart
on opposite edges of the same ridge.
"""

from __future__ import annotations

from typing import Any, cast

from dcs.mapping import Point
from shapely.geometry import MultiPolygon, Polygon, box

from game.missiongenerator.frontlineconflictdescription import (
    FrontLineConflictDescription,
)
from game.utils import Heading

MAX_WIDTH = 40_000
HALF = MAX_WIDTH / 2

#: Front axis runs east-west: heading 0 means left is west (-y), right is east (+y).
NORTH = Heading.from_degrees(0)


def _point(x: float, y: float) -> Point:
    return Point(x, y, None)  # type: ignore[arg-type]


class _FakeLandmap:
    def __init__(self, *polygons: Polygon) -> None:
        self.inclusion_zone_only = MultiPolygon(list(polygons))


class _FakeTheater:
    def __init__(self, landmap: _FakeLandmap | None) -> None:
        self.landmap = landmap


def _reach(*polygons: Polygon) -> tuple[float, float]:
    theater = cast(Any, _FakeTheater(_FakeLandmap(*polygons)))
    return FrontLineConflictDescription.usable_reach(
        _point(0, 0), NORTH, MAX_WIDTH, theater
    )


def _strip(low_y: float, high_y: float) -> Polygon:
    """Drivable ground spanning the whole axis between two east-west offsets."""
    return box(-50_000, low_y, 50_000, high_y)


def test_open_country_is_unchanged() -> None:
    """The common case must still be the full half-width each way."""
    assert _reach(_strip(-50_000, 50_000)) == (HALF, HALF)


def test_a_centre_on_the_zone_edge_runs_into_the_zone_not_away() -> None:
    """The regression. Drivable ground lies east; nothing may be drawn west."""
    left, right = _reach(_strip(0, 6_000))

    assert left == 0.0
    assert round(right) == 6_000


def test_a_pinned_flank_does_not_widen_the_other() -> None:
    """Slack is not spent across the centre -- upstream's width, minus the bug."""
    left, right = _reach(_strip(-3_000, 50_000))

    assert round(left) == 3_000
    assert right == HALF


def test_the_run_holding_the_centre_wins_over_a_wider_one_further_off() -> None:
    """A 12 km bowl 28 km off the road must not drag the fight away from it."""
    left, right = _reach(_strip(0, 6_000), _strip(28_000, 40_000))

    assert left == 0.0
    assert round(right) == 6_000


def test_a_centre_just_outside_every_run_takes_the_nearest() -> None:
    """`find_ground_position` returns boundary points; rounding can miss by a hair."""
    left, right = _reach(_strip(500, 9_000))

    assert left == 0.0
    assert round(right) == 9_000


def test_ground_on_both_flanks_is_measured_on_both_flanks() -> None:
    left, right = _reach(_strip(-4_000, 7_000))

    assert round(left) == 4_000
    assert round(right) == 7_000


def test_no_landmap_falls_back_to_the_nominal_width() -> None:
    theater = cast(Any, _FakeTheater(None))

    assert FrontLineConflictDescription.usable_reach(
        _point(0, 0), NORTH, MAX_WIDTH, theater
    ) == (HALF, HALF)


def test_an_axis_with_no_drivable_ground_falls_back_to_the_nominal_width() -> None:
    """Air-only campaigns draw an arbitrary front; it must still have extents."""
    assert _reach(box(400_000, 400_000, 410_000, 410_000)) == (HALF, HALF)
