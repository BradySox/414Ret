"""Old-stock loadout attrition (§84).

The behaviour under test is that flights stop being identical: a roll per flight
walks the loadout down the weapon data's own fallback ladder, deeper and more
often as the campaign clock advances, without ever crossing a weapon family or
touching equipment.
"""

from __future__ import annotations

import random
from types import SimpleNamespace

import pytest

from game.data.weapons import WeaponGroup, WeaponType
from game.fourteenth.stock_attrition import (
    MAX_DEPTH,
    PROTECTED_TYPES,
    _older_group,
    attrition_pressure,
    roll_depth,
)


def _settings(start: int = 0, per_turn: int = 4, ceiling: int = 50) -> SimpleNamespace:
    return SimpleNamespace(
        stock_attrition=True,
        stock_attrition_start=start,
        stock_attrition_per_turn=per_turn,
        stock_attrition_max=ceiling,
    )


class TestPressureScalesWithTheCampaignClock:
    def test_turn_one_is_the_start_value(self) -> None:
        assert attrition_pressure(_settings(start=0), turn=1) == 0
        assert attrition_pressure(_settings(start=10), turn=1) == pytest.approx(0.10)

    def test_it_climbs_every_turn(self) -> None:
        settings = _settings(start=0, per_turn=4)
        early = attrition_pressure(settings, turn=3)
        later = attrition_pressure(settings, turn=10)
        assert early == pytest.approx(0.08)
        assert later > early

    def test_it_stops_at_the_ceiling(self) -> None:
        settings = _settings(start=0, per_turn=4, ceiling=50)
        assert attrition_pressure(settings, turn=100) == pytest.approx(0.50)

    def test_a_zero_ceiling_disables_it_entirely(self) -> None:
        assert attrition_pressure(_settings(start=99, ceiling=0), turn=50) == 0


class TestDepthIsGeometricInPressure:
    def test_zero_pressure_never_reaches_for_old_stock(self) -> None:
        rng = random.Random(0)
        assert all(roll_depth(0.0, rng) == 0 for _ in range(200))

    def test_depth_is_bounded(self) -> None:
        rng = random.Random(1)
        assert all(roll_depth(1.0, rng) == MAX_DEPTH for _ in range(50))

    def test_deeper_rolls_are_rarer_than_shallow_ones(self) -> None:
        rng = random.Random(1234)
        depths = [roll_depth(0.5, rng) for _ in range(4000)]
        counts = [depths.count(d) for d in range(MAX_DEPTH + 1)]
        # Strictly decreasing up to the cap. The TOP bucket is deliberately not
        # part of that run: the loop stops at MAX_DEPTH without needing another
        # roll, so P(MAX_DEPTH) = p**MAX_DEPTH while P(MAX_DEPTH - 1) =
        # p**(MAX_DEPTH - 1) * (1 - p). At exactly p = 0.5 those are EQUAL, and
        # the observed counts differ only by sampling noise -- ordering them
        # would be testing the seed. What matters is that the deep tail stays
        # far rarer than a single rung, which is true for every p <= 0.5 (and
        # stock_attrition_max defaults to 50).
        assert counts[0] > counts[1] > counts[2]
        assert counts[MAX_DEPTH] < counts[1] / 2

    def test_a_worn_down_campaign_reaches_deeper_than_a_fresh_one(self) -> None:
        fresh = [roll_depth(0.1, random.Random(7)) for _ in range(2000)]
        worn = [roll_depth(0.5, random.Random(7)) for _ in range(2000)]
        assert sum(worn) > sum(fresh) * 2


class TestSubstitutionStaysInsideTheWeaponFamily:
    def test_the_amraam_ladder_walks_down_generations(self) -> None:
        amraam_c = WeaponGroup.named("AIM-120C")
        assert _older_group(amraam_c, 1).name == "AIM-120B"
        # Deep enough to break out the Sparrows -- the whole point of the feature.
        assert _older_group(amraam_c, 2).name == "AIM-7MH"

    def test_it_stops_at_the_end_of_the_ladder(self) -> None:
        oldest = WeaponGroup.named("AIM-9B")
        assert _older_group(oldest, MAX_DEPTH) is oldest

    def test_zero_depth_is_a_no_op(self) -> None:
        group = WeaponGroup.named("AIM-120C")
        assert _older_group(group, 0) is group

    def test_a_targeting_pod_never_becomes_a_missile(self) -> None:
        """AN/ASQ-228 ATFLIR declares AIM-120C as its fallback, on purpose.

        That is a sane last resort for date gating and absurd as attrition -- it
        would hang a missile on the targeting-pod station.
        """
        atflir = WeaponGroup.named("AN/ASQ-228 ATFLIR")
        assert atflir.fallback is not None
        assert atflir.fallback.name.startswith("AIM-120")
        assert _older_group(atflir, MAX_DEPTH) is atflir

    def test_equipment_types_are_protected(self) -> None:
        assert WeaponType.TGP in PROTECTED_TYPES
        assert WeaponType.JAMMER in PROTECTED_TYPES
        assert WeaponType.DECOY in PROTECTED_TYPES
        assert WeaponType.OFFENSIVE_JAMMER in PROTECTED_TYPES

    def test_every_a2a_group_stays_in_its_own_directory(self) -> None:
        """The family guard is the resources/weapons subdirectory."""
        amraam = WeaponGroup.named("AIM-120C")
        assert amraam.category == "a2a-missiles"
        for depth in range(MAX_DEPTH + 1):
            assert _older_group(amraam, depth).category == "a2a-missiles"


class TestSubstitutionIsNeverAnUpgrade:
    """`fallback` is a date-gating answer and is NOT monotonic in year.

    18 same-category fallbacks in the shipped data point at a newer weapon, so an
    unguarded walk hands a flight *better* stores the longer the war runs. Date
    gating cannot catch it: where both rungs are legal for the campaign date,
    nothing downstream clamps the upgrade.
    """

    def test_no_group_at_any_depth_ever_gets_newer(self) -> None:
        for group in WeaponGroup._by_name.values():
            start = group.introduction_year
            if start is None:
                continue
            for depth in range(MAX_DEPTH + 1):
                got = _older_group(group, depth)
                if got is group:
                    continue
                assert got.introduction_year is not None, (
                    f"{group.name} -> {got.name} at depth {depth}: "
                    "walked to an undated group"
                )
                assert got.introduction_year <= start, (
                    f"{group.name} ({start}) -> {got.name} "
                    f"({got.introduction_year}) at depth {depth} is an UPGRADE"
                )

    def test_the_double_amraam_rack_does_not_become_a_newer_single(self) -> None:
        """2xAIM-120B (1994) declares AIM-120C (2018) as its fallback.

        The yaml says so outright -- "if we've run out of doubles, start over with
        the singles" -- which is right for date gating and wrong here twice over:
        it halves the magazine AND hands over a newer missile. In a 2027 campaign
        (Baltic Fury, Marianas) both are date-legal, so nothing else stops it.
        """
        rack = WeaponGroup.named("2xAIM-120B")
        assert rack.fallback is not None
        assert rack.fallback.name == "AIM-120C"
        rack_year = rack.introduction_year
        single_year = rack.fallback.introduction_year
        assert rack_year is not None and single_year is not None
        assert single_year > rack_year
        assert _older_group(rack, MAX_DEPTH) is rack

    def test_the_maverick_ladder_does_not_walk_upward(self) -> None:
        """AGM-65E (1985) -> AGM-65G (1989) -> AGM-65F (1991).

        All three are legal in Desert Storm (1991), so before the year guard a
        depth-2 roll turned an AGM-65E into an AGM-65F -- strictly newer, in a
        shipped campaign, unclamped.
        """
        maverick = WeaponGroup.named("AGM-65E")
        start = maverick.introduction_year
        assert start is not None
        for depth in range(MAX_DEPTH + 1):
            got = _older_group(maverick, depth)
            got_year = got.introduction_year
            assert got_year is not None and got_year <= start

    def test_an_undated_rung_stops_the_walk(self) -> None:
        """An unknown year is unprovable, so it is not treated as older."""
        group = WeaponGroup(
            name="undated-probe",
            type=WeaponType.UNKNOWN,
            introduction_year=None,
            fallback_name="AIM-120B",
        )
        object.__setattr__(group, "category", "a2a-missiles")
        assert _older_group(group, MAX_DEPTH) is group


class TestTheWeaponCategoryData:
    def test_groups_are_tagged_with_their_source_directory(self) -> None:
        assert WeaponGroup.named("AIM-9X").category == "a2a-missiles"
        assert WeaponGroup.named("AIM-120D").category == "a2a-missiles"

    def test_a_synthesized_group_has_no_category(self) -> None:
        """Unknown clsids and the clean pylon must read as 'do not cross'."""
        group = WeaponGroup(
            name="synthetic",
            type=WeaponType.UNKNOWN,
            introduction_year=None,
            fallback_name=None,
        )
        assert group.category is None
        assert _older_group(group, MAX_DEPTH) is group

    def test_a_group_restored_without_the_field_does_not_crash(self) -> None:
        """Saves written before `category` existed restore groups without it."""
        group = WeaponGroup.__new__(WeaponGroup)
        group.__setstate__(
            {
                "name": "legacy",
                "type": WeaponType.UNKNOWN,
                "introduction_year": None,
                "fallback_name": None,
            }
        )
        assert _older_group(group, 1) is group


class TestTheLoadoutHook:
    """`degrade_loadout_for_stock` is guarded at every step."""

    def test_a_flight_with_no_game_is_left_alone(self) -> None:
        from game.fourteenth.stock_attrition import degrade_loadout_for_stock

        loadout = object()
        flight = SimpleNamespace()  # no .coalition at all
        assert degrade_loadout_for_stock(loadout, flight) is loadout  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        ("enabled", "is_custom", "turn"),
        [
            (False, False, 20),  # feature off
            (True, True, 20),  # player-customised loadout
            (True, False, 1),  # turn 1 at the default zero start
        ],
    )
    def test_it_returns_the_original_object_untouched(
        self, enabled: bool, is_custom: bool, turn: int
    ) -> None:
        from game.fourteenth.stock_attrition import degrade_loadout_for_stock

        settings = _settings(start=0)
        settings.stock_attrition = enabled
        flight = SimpleNamespace(
            coalition=SimpleNamespace(
                game=SimpleNamespace(settings=settings, turn=turn)
            )
        )
        loadout = SimpleNamespace(is_custom=is_custom)
        assert degrade_loadout_for_stock(loadout, flight) is loadout  # type: ignore[arg-type]
