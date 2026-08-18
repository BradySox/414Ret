"""The app map draws the same trace as the generated mission.

§90 rung E bows the front line. The .miz drawing and the FLOT placement were
opted in when it landed; the app's own map was missed, so the surface the player
actually plans on kept drawing a straight chord between the two endpoints. It is
a seventh consumer of `frontline_bounds`, not one of the six counted at the time.
"""

from __future__ import annotations

from typing import Any, cast

from dcs.mapping import Point

from game.missiongenerator.frontlineconflictdescription import FrontLineBounds


def _point(x: float, y: float) -> Point:
    return Point(x, y, None)  # type: ignore[arg-type]


def test_a_straight_front_still_sends_exactly_two_points() -> None:
    """No sector depths must be byte-identical to the old two-endpoint payload."""
    bounds = FrontLineBounds(_point(0, 0), _point(0, 12000))

    assert bounds.polyline == (bounds.left_position, bounds.right_position)
    assert len(bounds.polyline) == 2


def test_a_bowed_front_sends_every_vertex() -> None:
    bounds = FrontLineBounds(_point(0, 0), _point(0, 12000), (0.0, 2000.0, 0.0))

    assert len(bounds.polyline) == 3
    # The ends are the exact bounds, so anything reading only the extremes is
    # unaffected by the extra vertex in the middle.
    assert bounds.polyline[0] == bounds.left_position
    assert bounds.polyline[-1] == bounds.right_position


def test_the_middle_vertex_is_off_the_chord() -> None:
    """If it were on the chord the app would render a straight line anyway."""
    bounds = FrontLineBounds(_point(0, 0), _point(0, 12000), (0.0, 2000.0, 0.0))

    middle = bounds.polyline[1]
    on_chord = bounds.left_position.point_from_heading(
        bounds.heading_from_left_to_right.degrees, bounds.length / 2
    )
    assert round(abs(middle.x - on_chord.x)) == 2000


def test_every_vertex_is_convertible_for_the_client() -> None:
    """The server maps each vertex through latlng(); none may be None."""
    bounds = FrontLineBounds(_point(0, 0), _point(0, 12000), (0.0, 1500.0, 0.0))

    assert all(cast(Any, point) is not None for point in bounds.polyline)
