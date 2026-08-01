from typing import Any, cast

from dcs.mapping import Point

from game.theater.frontline import (
    FRONTLINE_MIN_CP_DISTANCE,
    FrontLine,
    FrontLineSegment,
)


def test_front_line_hash_survives_unpickle_ordering() -> None:
    """FrontLine.__hash__ must NOT depend on blue_cp/red_cp.

    Pickle hashes set/dict keys during load BEFORE __setstate__ restores an
    object's attributes. A state-dependent hash (hash((self.blue_cp,
    self.red_cp))) raises AttributeError on the half-constructed object and
    breaks save loading -- this regressed once in #53 and was the original
    reason upstream made the hash identity-based ("Fix save loading",
    605d8f057). The hash must also stay stable once state is attached, or a key
    inserted while half-constructed lands in the wrong bucket and is lost.
    """
    half_constructed = object.__new__(FrontLine)

    # Pickle inserts the key into the container while it is still empty.
    members = {half_constructed}
    # Hashing the empty object must not raise (blue_cp / red_cp are unset).
    assert hash(half_constructed)

    # __setstate__ then attaches the real attributes...
    half_constructed.blue_cp = cast(Any, object())
    half_constructed.red_cp = cast(Any, object())

    # ...and the key must still be findable, i.e. the hash did not change.
    assert half_constructed in members


def _bare_front_line(route_length: float) -> FrontLine:
    front_line = object.__new__(FrontLine)
    front_line.segments = [
        FrontLineSegment(
            Point(0, 0, None),  # type: ignore[arg-type]
            Point(0, route_length, None),  # type: ignore[arg-type]
        )
    ]
    return front_line


def test_adjust_for_min_dist_clamps_normally_on_a_long_route() -> None:
    """Sanity check: a route comfortably longer than 2x the minimum distance
    clamps toward whichever end the raw distance overshot, same as before."""
    route_length = 10 * FRONTLINE_MIN_CP_DISTANCE
    front_line = _bare_front_line(route_length)

    # Comfortably inside the buffer on both ends: untouched.
    assert front_line._adjust_for_min_dist(route_length / 2) == route_length / 2
    # Overshoots red's end: clamped back to the buffer.
    assert (
        front_line._adjust_for_min_dist(route_length)
        == route_length - FRONTLINE_MIN_CP_DISTANCE
    )
    # Overshoots blue's end: clamped forward to the buffer.
    assert front_line._adjust_for_min_dist(0) == FRONTLINE_MIN_CP_DISTANCE


def test_adjust_for_min_dist_never_inverts_on_a_short_route() -> None:
    """Regression test: on a route shorter than 2x FRONTLINE_MIN_CP_DISTANCE,
    the old clamp logic could push a front that should sit near RED's end
    (blue dominant) all the way back to BLUE's end instead -- a full
    inversion of which side the front favors. It must now settle on the
    midpoint rather than flip sides."""
    route_length = 1.2 * FRONTLINE_MIN_CP_DISTANCE  # short: < 2x MIN_CP_DISTANCE
    front_line = _bare_front_line(route_length)

    # Blue is dominant (90% strength share) -- distance is most of the route,
    # i.e. close to RED's end.
    raw_distance = 0.9 * route_length
    adjusted = front_line._adjust_for_min_dist(raw_distance)

    # Must stay on blue's (the raw distance's) side of the midpoint, not flip
    # to sit closer to blue's own CP than to red's.
    assert adjusted >= route_length / 2
    assert adjusted == route_length / 2  # current fallback: settle at midpoint


def test_adjust_for_min_dist_symmetric_for_short_routes() -> None:
    """The short-route fallback must not itself introduce a directional bias
    -- a red-dominant front (distance near 0) lands on the same midpoint as
    a blue-dominant one (distance near route_length)."""
    route_length = 1.2 * FRONTLINE_MIN_CP_DISTANCE
    front_line = _bare_front_line(route_length)

    near_blue = front_line._adjust_for_min_dist(0.1 * route_length)
    near_red = front_line._adjust_for_min_dist(0.9 * route_length)

    assert near_blue == near_red == route_length / 2
