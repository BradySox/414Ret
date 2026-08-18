from typing import Any, cast

from dcs.mapping import Point

from game.missiongenerator.frontlineconflictdescription import (
    MAX_SALIENT_DEPTH,
    FrontLineBounds,
)


def _point(x: float, y: float) -> Point:
    return Point(x, y, None)  # type: ignore[arg-type]


def _bounds(*depths: float, length: float = 12000.0) -> FrontLineBounds:
    """A front running due east, so the advance direction is due south."""
    return FrontLineBounds(_point(0, 0), _point(0, length), tuple(depths))


def test_a_straight_front_traces_the_chord() -> None:
    bounds = _bounds()

    assert bounds.polyline == (bounds.left_position, bounds.right_position)
    assert bounds.depth_at(6000) == 0.0
    midpoint = bounds.point_at(6000)
    # `point_from_heading` walks with trig, so the chord drifts sub-micron.
    assert round(midpoint.x, 6) == 0
    assert round(midpoint.y) == 6000


def test_endpoints_are_untouched_by_a_bulge() -> None:
    """Every consumer that reads only the two ends must see no change."""
    straight = _bounds()
    bowed = _bounds(0.0, 2000.0, 0.0)

    assert bowed.left_position == straight.left_position
    assert bowed.right_position == straight.right_position
    assert bowed.length == straight.length
    assert bowed.point_at(0) == straight.point_at(0)
    assert bowed.point_at(bowed.length) == straight.point_at(straight.length)


def test_a_bulge_pushes_the_middle_along_the_advance_axis() -> None:
    bounds = _bounds(0.0, 2000.0, 0.0)

    assert bounds.depth_at(6000) == 2000.0
    middle = bounds.point_at(6000)
    # Advance is perpendicular to the front, not along it.
    assert round(middle.y) == 6000
    assert round(abs(middle.x)) == 2000


def test_the_bulge_goes_toward_red_not_away() -> None:
    """A positive depth must be blue's forward direction."""
    bounds = _bounds(0.0, 2000.0, 0.0)

    assert bounds.advance_heading == bounds.heading_from_left_to_right.right
    forward = bounds.point_at(6000)
    backward = FrontLineBounds(
        bounds.left_position, bounds.right_position, (0.0, -2000.0, 0.0)
    ).point_at(6000)
    assert forward != backward


def test_depth_interpolates_between_samples() -> None:
    bounds = _bounds(0.0, 1000.0, 0.0)

    assert bounds.depth_at(0) == 0.0
    assert bounds.depth_at(3000) == 500.0
    assert bounds.depth_at(6000) == 1000.0
    assert bounds.depth_at(9000) == 500.0
    assert bounds.depth_at(12000) == 0.0


def test_depth_is_clamped_to_the_ends_outside_the_front() -> None:
    bounds = _bounds(0.0, 1000.0, 0.0)

    assert bounds.depth_at(-5000) == 0.0
    assert bounds.depth_at(99999) == 0.0


def test_polyline_has_one_vertex_per_sample() -> None:
    bounds = _bounds(0.0, 500.0, 1500.0, 500.0, 0.0)

    assert len(bounds.polyline) == 5
    assert bounds.polyline[0] == bounds.left_position
    assert bounds.polyline[-1] == bounds.right_position


def test_a_zero_length_front_never_divides_by_zero() -> None:
    degenerate = FrontLineBounds(_point(0, 0), _point(0, 0), (0.0, 1000.0, 0.0))

    assert degenerate.length == 0
    assert degenerate.depth_at(0) == 0.0


def test_max_salient_depth_is_smaller_than_a_typical_front() -> None:
    """A bulge is a bend in the line, not a second front."""
    assert 0 < MAX_SALIENT_DEPTH < 10_000


class FakeLandmap:
    def __init__(self, boundary: Any) -> None:
        self.inclusion_zone_only = boundary


class FakeTheater:
    def __init__(self, landmap: Any) -> None:
        self.landmap = landmap


def test_no_landmap_means_no_sector_depths() -> None:
    from game.missiongenerator.frontlineconflictdescription import (
        FrontLineConflictDescription,
    )

    theater = cast(Any, FakeTheater(None))
    assert FrontLineConflictDescription.sector_depths(_bounds(), theater) == ()
