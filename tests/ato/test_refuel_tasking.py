"""Tests for the fuel-driven pre/post-vul tanker tasking decision."""

from game.ato.refueltasking import RefuelTasking, decide_refuel_tasking

RESERVE = 1000.0


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
