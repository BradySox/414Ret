"""Tests for the fuel-driven pre/post-vul tanker tasking decision."""

from types import SimpleNamespace

from game.ato.flightwaypointtype import FlightWaypointType
from game.ato.refueltasking import (
    RefuelTasking,
    decide_refuel_tasking,
    sortie_fuel_split,
)

RESERVE = 1000.0

_NM = 1852.0  # meters per nautical mile


class _Pos:
    """A point on a line; distance_to_point measures meters along it."""

    def __init__(self, nautical_miles: float) -> None:
        self.x = nautical_miles * _NM

    def distance_to_point(self, other: "_Pos") -> float:
        return abs(self.x - other.x)


def _wp(at_nm: float, *, takeoff: bool = False) -> SimpleNamespace:
    kind = FlightWaypointType.TAKEOFF if takeoff else FlightWaypointType.NAV
    return SimpleNamespace(position=_Pos(at_nm), waypoint_type=kind)


def test_sortie_fuel_split_applies_climb_combat_cruise_rates() -> None:
    fuel = SimpleNamespace(climb=30.0, combat=20.0, cruise=10.0)
    takeoff = _wp(0, takeoff=True)
    join = _wp(10)
    target = _wp(20)
    split = _wp(25)
    landing = _wp(40)
    route = [takeoff, join, target, split, landing]
    combat_speed = {join, target, split}

    to_split, after_split = sortie_fuel_split(route, fuel, combat_speed, split)  # type: ignore[arg-type]

    # takeoff->join is the climb leg (10 nm * 30); join->target and target->split are
    # combat (10 nm * 20 + 5 nm * 20); split->landing is cruise (15 nm * 10).
    assert to_split == 10 * 30 + 10 * 20 + 5 * 20
    assert after_split == 15 * 10


def test_sortie_fuel_split_handles_empty_and_single_point_routes() -> None:
    fuel = SimpleNamespace(climb=30.0, combat=20.0, cruise=10.0)
    only = _wp(0, takeoff=True)
    assert sortie_fuel_split([], fuel, set(), only) == (0.0, 0.0)  # type: ignore[arg-type]
    assert sortie_fuel_split([only], fuel, set(), only) == (0.0, 0.0)  # type: ignore[arg-type]


def _decide(usable: float, to_vul: float, vul_home: float) -> RefuelTasking:
    return decide_refuel_tasking(usable, to_vul, vul_home, RESERVE)


def test_no_tanker_when_internal_fuel_covers_the_sortie() -> None:
    # 6000 needed (3000 + 2000 + 1000 reserve), 7000 available.
    assert _decide(7000, 3000, 2000) is RefuelTasking.NONE


def test_no_tanker_at_the_exact_break_even_point() -> None:
    # Exactly enough: usable == to_vul + vul_home + reserve.
    assert _decide(6000, 3000, 2000) is RefuelTasking.NONE


def test_post_vul_when_short_only_for_the_trip_home() -> None:
    # Can reach end of vul with reserve to spare (5000 >= 3000 + 1000) but can't make
    # it home with reserve (5000 < 6000): tank on egress.
    assert _decide(5000, 3000, 2000) is RefuelTasking.POST_VUL


def test_pre_vul_when_cannot_fight_through_the_vul() -> None:
    # Can't even reach the split holding reserve (3500 < 3000 + 1000): top off on
    # ingress.
    assert _decide(3500, 3000, 2000) is RefuelTasking.PRE_VUL


def test_pre_vul_boundary_just_below_vul_plus_reserve() -> None:
    # usable just under to_vul + reserve -> pre-vul.
    assert _decide(3999, 3000, 1000) is RefuelTasking.PRE_VUL
    # usable exactly at to_vul + reserve -> not pre-vul (post or none).
    assert _decide(4000, 3000, 1000) is not RefuelTasking.PRE_VUL


def test_helper_properties() -> None:
    assert not RefuelTasking.NONE.needs_tanker
    assert RefuelTasking.PRE_VUL.needs_tanker
    assert RefuelTasking.PRE_VUL.refuels_pre_vul
    assert not RefuelTasking.PRE_VUL.refuels_post_vul
    assert RefuelTasking.POST_VUL.refuels_post_vul
    assert not RefuelTasking.POST_VUL.refuels_pre_vul
