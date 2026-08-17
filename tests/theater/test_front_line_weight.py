from typing import Any, cast

from dcs.mapping import Point

from game.theater.base import Base
from game.theater.frontline import (
    FRONTLINE_MIN_CP_DISTANCE,
    FrontLine,
    FrontLineSegment,
)


class FakeUnitType:
    def __init__(self, price: int) -> None:
        self.price = price

    def __hash__(self) -> int:
        return id(self)


class FakeControlPoint:
    def __init__(self, coalition: Any = None) -> None:
        self.base = Base()
        self.coalition = coalition


class FakeSettings:
    def __init__(self, scale_aware: bool) -> None:
        self.scale_aware_front_line = scale_aware
        # Rung D off: these tests are about weight, not terrain.
        self.terrain_weighted_front_line = False


class FakeTheater:
    landmap = None


class FakeGame:
    def __init__(self, scale_aware: bool) -> None:
        self.settings = FakeSettings(scale_aware)
        self.theater = FakeTheater()


class FakeCoalition:
    def __init__(self, scale_aware: bool) -> None:
        self.game = FakeGame(scale_aware)


def _front_line(route_length: float, scale_aware: bool) -> FrontLine:
    """A FrontLine with just enough attached to place its position."""
    front_line = object.__new__(FrontLine)
    front_line.segments = [
        FrontLineSegment(
            Point(0, 0, None),  # type: ignore[arg-type]
            Point(0, route_length, None),  # type: ignore[arg-type]
        )
    ]
    # FrontLine.coalition reads blue_cp.coalition.
    front_line.blue_cp = cast(Any, FakeControlPoint(FakeCoalition(scale_aware)))
    front_line.red_cp = cast(Any, FakeControlPoint())
    return front_line


def _stock(base: Base, price: int, count: int) -> None:
    base.armor[cast(Any, FakeUnitType(price))] = count


LONG_ROUTE = 20 * FRONTLINE_MIN_CP_DISTANCE


def test_equal_morale_and_equal_armour_meets_in_the_middle() -> None:
    front = _front_line(LONG_ROUTE, scale_aware=True)
    _stock(front.blue_cp.base, price=100, count=10)
    _stock(front.red_cp.base, price=100, count=10)

    assert front._blue_route_progress == LONG_ROUTE / 2


def test_better_equipped_side_pushes_the_front() -> None:
    """The defect rung C fixes: full strength on both sides, wildly different kit."""
    front = _front_line(LONG_ROUTE, scale_aware=True)
    _stock(front.blue_cp.base, price=100, count=100)
    _stock(front.red_cp.base, price=100, count=10)

    # Blue holds ten times the materiel, so the front sits deep in red's half.
    assert front._blue_route_progress > LONG_ROUTE * 0.9


def test_the_same_matchup_is_a_dead_heat_without_the_setting() -> None:
    """Upstream's behaviour: five vehicles weigh the same as five hundred."""
    front = _front_line(LONG_ROUTE, scale_aware=False)
    _stock(front.blue_cp.base, price=100, count=100)
    _stock(front.red_cp.base, price=100, count=10)

    assert front._blue_route_progress == LONG_ROUTE / 2


def test_morale_still_counts() -> None:
    """Materiel does not override organisation -- the two multiply."""
    front = _front_line(LONG_ROUTE, scale_aware=True)
    _stock(front.blue_cp.base, price=100, count=10)
    _stock(front.red_cp.base, price=100, count=10)
    front.blue_cp.base.strength = 0.25
    front.red_cp.base.strength = 1.0

    assert front._blue_route_progress < LONG_ROUTE / 2


def test_equal_weight_from_different_mixes_is_still_a_dead_heat() -> None:
    """Few good vehicles can balance many cheap ones."""
    front = _front_line(LONG_ROUTE, scale_aware=True)
    _stock(front.blue_cp.base, price=400, count=5)
    _stock(front.red_cp.base, price=100, count=20)

    assert front._blue_route_progress == LONG_ROUTE / 2


def test_no_armour_on_either_side_falls_back_to_morale() -> None:
    """Air-only campaigns must not pin the front to blue's doorstep."""
    front = _front_line(LONG_ROUTE, scale_aware=True)
    front.blue_cp.base.strength = 1.0
    front.red_cp.base.strength = 1.0

    assert front._blue_route_progress == LONG_ROUTE / 2


def test_one_side_with_no_armour_loses_the_ground() -> None:
    front = _front_line(LONG_ROUTE, scale_aware=True)
    _stock(front.blue_cp.base, price=100, count=10)

    assert front._blue_route_progress == LONG_ROUTE - FRONTLINE_MIN_CP_DISTANCE


def test_position_stays_inside_the_clamp() -> None:
    front = _front_line(LONG_ROUTE, scale_aware=True)
    _stock(front.blue_cp.base, price=100, count=10_000)
    _stock(front.red_cp.base, price=1, count=1)

    progress = front._blue_route_progress
    assert (
        FRONTLINE_MIN_CP_DISTANCE
        <= progress
        <= (LONG_ROUTE - FRONTLINE_MIN_CP_DISTANCE)
    )


def test_front_line_weight_is_morale_times_materiel() -> None:
    base = Base()
    _stock(base, price=50, count=4)
    base.strength = 0.5

    assert base.total_armor_value == 200
    assert base.front_line_weight == 100.0


def test_zero_morale_weighs_nothing_however_much_kit() -> None:
    base = Base()
    _stock(base, price=100, count=1000)
    base.strength = 0.0

    assert base.front_line_weight == 0.0
