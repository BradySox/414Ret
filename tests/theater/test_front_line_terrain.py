from typing import Any, cast

from dcs.mapping import Point
from shapely.geometry import MultiPolygon, Polygon

from game.theater.base import Base
from game.theater.frontline import (
    FRONTLINE_MIN_CP_DISTANCE,
    MAX_TERRAIN_DIFFICULTY,
    FrontLine,
    FrontLineSegment,
)


class FakeControlPoint:
    def __init__(self, coalition: Any = None) -> None:
        self.base = Base()
        self.coalition = coalition


class FakeSettings:
    def __init__(self, terrain_weighted: bool) -> None:
        self.scale_aware_front_line = False
        self.terrain_weighted_front_line = terrain_weighted


class FakeLandmap:
    def __init__(self, passable: MultiPolygon) -> None:
        self.inclusion_zone_only = passable


class FakeTheater:
    def __init__(self, landmap: Any) -> None:
        self.landmap = landmap


class FakeGame:
    def __init__(self, terrain_weighted: bool, landmap: Any) -> None:
        self.settings = FakeSettings(terrain_weighted)
        self.theater = FakeTheater(landmap)


class FakeCoalition:
    def __init__(self, terrain_weighted: bool, landmap: Any) -> None:
        self.game = FakeGame(terrain_weighted, landmap)


SEGMENT = 20 * FRONTLINE_MIN_CP_DISTANCE


def _corridor(*spans: tuple[float, float]) -> MultiPolygon:
    """Passable ground: boxes spanning the given y ranges around the route."""
    return MultiPolygon(
        [Polygon([(-1, lo), (1, lo), (1, hi), (-1, hi)]) for lo, hi in spans]
    )


def _front_line(segment_count: int, terrain_weighted: bool, landmap: Any) -> FrontLine:
    front_line = object.__new__(FrontLine)
    front_line.segments = [
        FrontLineSegment(
            Point(0, index * SEGMENT, None),  # type: ignore[arg-type]
            Point(0, (index + 1) * SEGMENT, None),  # type: ignore[arg-type]
        )
        for index in range(segment_count)
    ]
    coalition = FakeCoalition(terrain_weighted, landmap)
    front_line.blue_cp = cast(Any, FakeControlPoint(coalition))
    front_line.red_cp = cast(Any, FakeControlPoint())
    return front_line


def test_open_country_is_difficulty_one() -> None:
    passable = _corridor((0, 2 * SEGMENT))
    front = _front_line(2, terrain_weighted=True, landmap=FakeLandmap(passable))

    assert front._segment_difficulties() == [1.0, 1.0]


def test_impassable_segment_is_the_maximum() -> None:
    # Only the first segment is passable; the second is off the map entirely.
    passable = _corridor((0, SEGMENT))
    front = _front_line(2, terrain_weighted=True, landmap=FakeLandmap(passable))

    difficulties = front._segment_difficulties()
    assert difficulties[0] == 1.0
    assert difficulties[1] == MAX_TERRAIN_DIFFICULTY


def test_setting_off_flattens_every_segment() -> None:
    passable = _corridor((0, SEGMENT))
    front = _front_line(2, terrain_weighted=False, landmap=FakeLandmap(passable))

    assert front._segment_difficulties() == [1.0, 1.0]


def test_missing_landmap_flattens_every_segment() -> None:
    front = _front_line(2, terrain_weighted=True, landmap=None)

    assert front._segment_difficulties() == [1.0, 1.0]


def test_uniform_difficulty_matches_the_plain_proportional_placement() -> None:
    """The compatibility guarantee: flat terrain must not move the front."""
    passable = _corridor((0, 2 * SEGMENT))
    front = _front_line(2, terrain_weighted=True, landmap=FakeLandmap(passable))

    for share in (0.0, 0.25, 0.5, 0.75, 1.0):
        assert front._distance_for_effort_share(share) == share * front.route_length


def test_an_even_fight_sits_at_the_midpoint_whatever_the_terrain() -> None:
    """The neutral point must not move, or every campaign's front start shifts."""
    lopsided = _corridor((0, SEGMENT))
    front = _front_line(2, terrain_weighted=True, landmap=FakeLandmap(lopsided))

    assert front._segment_difficulties() == [1.0, MAX_TERRAIN_DIFFICULTY]
    assert front._distance_for_effort_share(0.5) == front.route_length / 2


def test_pushing_into_hard_ground_needs_a_bigger_advantage() -> None:
    """Four equal segments, the third impassable. Blue advances into it slowly."""
    passable = _corridor((0, 2 * SEGMENT), (3 * SEGMENT, 4 * SEGMENT))
    front = _front_line(4, terrain_weighted=True, landmap=FakeLandmap(passable))

    assert front._segment_difficulties() == [
        1.0,
        1.0,
        MAX_TERRAIN_DIFFICULTY,
        1.0,
    ]

    weighted = front._distance_for_effort_share(0.75)
    flat = 0.75 * front.route_length

    # Same advantage, less ground taken -- the hard segment soaked it up.
    assert weighted < flat
    assert weighted == 2.625 * SEGMENT


def test_open_ground_beyond_the_pass_is_cheap_again() -> None:
    """Ground per unit of advantage: slow through the pass, fast once past it."""
    passable = _corridor((0, 2 * SEGMENT), (3 * SEGMENT, 4 * SEGMENT))
    front = _front_line(4, terrain_weighted=True, landmap=FakeLandmap(passable))

    at_75 = front._distance_for_effort_share(0.75)
    at_90 = front._distance_for_effort_share(0.90)
    at_100 = front._distance_for_effort_share(1.0)

    # 0.15 of advantage spent inside the pass...
    through_the_pass = at_90 - at_75
    # ...against 0.10 spent in the open beyond it.
    past_the_pass = at_100 - at_90

    assert at_90 == 3 * SEGMENT  # exactly clear of the bad going
    assert past_the_pass > 2 * through_the_pass


def test_effort_share_is_monotonic() -> None:
    passable = _corridor((0, SEGMENT), (1.5 * SEGMENT, 3 * SEGMENT))
    front = _front_line(3, terrain_weighted=True, landmap=FakeLandmap(passable))

    shares = [index / 20 for index in range(21)]
    distances = [front._distance_for_effort_share(share) for share in shares]
    assert distances == sorted(distances)
    assert distances[0] == 0.0
    assert distances[-1] == front.route_length


def test_difficulties_are_cached_but_survive_a_pre_feature_save() -> None:
    """Pickled front lines have no cache attribute; it must re-derive."""
    passable = _corridor((0, 2 * SEGMENT))
    front = _front_line(2, terrain_weighted=True, landmap=FakeLandmap(passable))

    first = front._segment_difficulties()
    assert front._segment_difficulties() is first

    del front._difficulties
    assert front._segment_difficulties() == first
