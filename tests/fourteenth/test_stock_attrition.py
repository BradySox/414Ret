"""Old-stock loadout attrition (§84).

The behaviour under test is that flights stop being identical, and that a single
jet's magazine comes out MIXED: each station rolls its own depth down the weapon
data's own fallback ladder, deeper and more often as the campaign clock advances,
without ever crossing a weapon family, ending up newer, or touching equipment.
"""

from __future__ import annotations

import random
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import dcs.planes as planes
import pytest

from game import persistency
from game.data.weapons import Weapon, WeaponGroup, WeaponType
from game.ato.loadouts import Loadout
from game.dcs.aircrafttype import AircraftType
from game.fourteenth.stock_attrition import (
    MAX_DEPTH,
    PROTECTED_TYPES,
    _older_group,
    attrition_pressure,
    degrade_loadout_for_stock,
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

    def test_the_double_amraam_rack_degrades_to_the_single_rail(self) -> None:
        """2xAIM-120B (1994) declares AIM-120C (2018) as its fallback.

        The yaml says so outright -- "if we've run out of doubles, start over with
        the singles" -- which is right for date gating and wrong here twice over:
        AIM-120C halves the magazine AND is newer. In a 2027 campaign (Baltic Fury,
        Marianas) both are date-legal, so nothing downstream stops it.

        Hopping over it lands on the rung that comment was actually reaching for:
        AIM-120B, the single rail of the SAME generation -- fewer missiles, not
        newer ones.
        """
        rack = WeaponGroup.named("2xAIM-120B")
        assert rack.fallback is not None
        assert rack.fallback.name == "AIM-120C"
        rack_year = rack.introduction_year
        skipped_year = rack.fallback.introduction_year
        assert rack_year is not None and skipped_year is not None
        assert skipped_year > rack_year, "the trap: the fallback is newer"

        got = _older_group(rack, 1)
        assert got.name == "AIM-120B"
        assert got.introduction_year == rack_year

    def test_the_maverick_ladder_hops_over_its_newer_rungs(self) -> None:
        """AGM-65E (1985) -> AGM-65G (1989) -> AGM-65F (1991).

        All three are legal in Desert Storm (1991), so before the year guard a
        depth-2 roll turned an AGM-65E into an AGM-65F -- strictly newer, in a
        shipped campaign, unclamped. Both newer rungs are now hopped, so the
        Maverick still has real depth to reach into.
        """
        maverick = WeaponGroup.named("AGM-65E")
        start = maverick.introduction_year
        assert start is not None
        for depth in range(MAX_DEPTH + 1):
            got = _older_group(maverick, depth)
            got_year = got.introduction_year
            assert got_year is not None and got_year <= start
        assert _older_group(maverick, 1).name == "AGM-65B"

    def test_a_newer_rung_does_not_end_the_ladder(self) -> None:
        """Stopping dead at a newer rung costs real depth.

        Hopping is worth +15 groups of usable depth across the shipped data, which
        matters because the point of the feature is to USE the magazine's depth
        wherever it exists -- air-to-air, air-to-ground or anti-ship alike.
        """
        with_depth = 0
        for group in WeaponGroup._by_name.values():
            if getattr(group, "category", None) is None:
                continue
            if group.type in PROTECTED_TYPES:
                continue
            if _older_group(group, 1) is not group:
                with_depth += 1
        # Measured 206 against the shipped weapon data. A drop means either the
        # walk was narrowed or weapon groups were removed -- both worth a look.
        assert with_depth >= 206

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


#: A real F/A-18C air-to-air magazine: four AMRAAMs on the LAU-115 rails plus two
#: Sidewinders on the tips. Stations and clsids are the airframe's own pydcs pylon
#: table, so the substitutions below are pylon-legal for real.
#:
#: Built here from explicit clsids rather than resolved by name from a shipped
#: `Retribution BARCAP` payload file, because payload *directories* are registered
#: by `qt_ui.main.inject_custom_payloads` and not by `persistency.setup`. A
#: name-resolved fit therefore passes on a developer box (which has the user's own
#: `Saved Games/.../UnitPayloads`) and raises `StopIteration` in CI, which has no
#: DCS install and no user payloads at all. Explicit clsids are hermetic.
HORNET_A2A_STATIONS = {
    1: "{5CE2FF2A-645A-4197-B48D-8720AC69394F}",  # AIM-9X, left tip
    2: "{LAU-115 - AIM-120C}",  # AIM-120C
    3: "{LAU-115 - AIM-120C}",  # AIM-120C
    7: "{LAU-115 - AIM-120C_R}",  # AIM-120C
    8: "{LAU-115 - AIM-120C_R}",  # AIM-120C
    9: "{5CE2FF2A-645A-4197-B48D-8720AC69394F}",  # AIM-9X, right tip
}


class TestOneJetCarriesAMixedMagazine:
    """The point of the feature, and the reason the roll is PER STATION.

    Rolling once per flight and applying it everywhere only ages the magazine
    uniformly -- 4x AIM-120C becomes 4x AIM-120B, four identical rounds either
    way. These drive a real F/A-18C air-to-air magazine on real pydcs pylon tables.
    """

    @pytest.fixture(autouse=True)
    def _persistency(self, tmp_path: Path) -> None:
        # Weapon.with_clsid and Pylon.for_aircraft need the weapon DB.
        persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16887)

    @staticmethod
    def _hornet_barcap() -> tuple[AircraftType, Loadout]:
        hornet = next(AircraftType.for_dcs_type(planes.FA_18C_hornet))
        fit = Loadout(
            "Retribution BARCAP",
            {n: Weapon.with_clsid(c) for n, c in HORNET_A2A_STATIONS.items()},
            date=None,
        )
        return hornet, fit

    @staticmethod
    def _flight(hornet: AircraftType, turn: int, start: int) -> SimpleNamespace:
        return SimpleNamespace(
            unit_type=hornet,
            coalition=SimpleNamespace(
                game=SimpleNamespace(settings=_settings(start=start), turn=turn)
            ),
        )

    def test_one_loadout_ends_up_carrying_more_than_one_generation(self) -> None:
        hornet, fit = self._hornet_barcap()
        # A high pressure makes the mixture certain rather than likely; the
        # per-turn ramp is covered separately.
        rng = random.Random(20260803)
        for _ in range(40):
            got = degrade_loadout_for_stock(
                fit, self._flight(hornet, turn=12, start=50), rng  # type: ignore[arg-type]
            )
            names = {
                w.weapon_group.name
                for w in got.pylons.values()
                if w is not None and w.weapon_group.name.startswith("AIM-120")
            }
            if len(names) > 1:
                return  # AMRAAMs of two different generations on one jet
        pytest.fail("no mixed-generation AMRAAM magazine in 40 rolls")

    def test_two_flights_of_the_same_type_and_task_differ(self) -> None:
        hornet, fit = self._hornet_barcap()
        rng = random.Random(4242)

        def loads() -> Counter[str]:
            got = degrade_loadout_for_stock(
                fit, self._flight(hornet, turn=12, start=40), rng  # type: ignore[arg-type]
            )
            return Counter(
                w.weapon_group.name for w in got.pylons.values() if w is not None
            )

        seen = {tuple(sorted(loads().items())) for _ in range(12)}
        assert len(seen) > 1, "twelve flights all came out identically loaded"

    def test_the_shipped_fit_is_never_mutated_in_place(self) -> None:
        """Members share the loadout object, so an in-place edit would leak."""
        hornet, fit = self._hornet_barcap()
        before = Counter(
            w.weapon_group.name for w in fit.pylons.values() if w is not None
        )
        rng = random.Random(7)
        for _ in range(20):
            degrade_loadout_for_stock(
                fit, self._flight(hornet, turn=20, start=60), rng  # type: ignore[arg-type]
            )
        after = Counter(
            w.weapon_group.name for w in fit.pylons.values() if w is not None
        )
        assert before == after

    def test_a_substitution_is_never_newer_than_what_it_replaced(self) -> None:
        hornet, fit = self._hornet_barcap()
        rng = random.Random(99)
        original = {n: w.weapon_group for n, w in fit.pylons.items() if w is not None}
        for _ in range(30):
            got = degrade_loadout_for_stock(
                fit, self._flight(hornet, turn=25, start=70), rng  # type: ignore[arg-type]
            )
            for number, weapon in got.pylons.items():
                if weapon is None or number not in original:
                    continue
                was, now = original[number], weapon.weapon_group
                if was is now or was.introduction_year is None:
                    continue
                assert now.introduction_year is not None
                assert now.introduction_year <= was.introduction_year, (
                    f"station {number}: {was.name} ({was.introduction_year}) -> "
                    f"{now.name} ({now.introduction_year}) is an UPGRADE"
                )


class TestItAppliesToEveryFlightType:
    """The hook is task-agnostic, and so is the data: A2A is not a special case.

    The DM's framing: "if the magazine has depth, we should be using it regardless
    of if it's air to air, air to ground, air to ship."
    """

    def test_a_bai_jet_degrades_jdam_to_lgb_to_dumb_bomb(self) -> None:
        """The bomb ladder is already generational, so BAI/Strike get this free."""
        jdam = WeaponGroup.named("GBU-31(V)3/B")
        assert jdam.introduction_year == 2001
        assert _older_group(jdam, 1).name == "GBU-24"  # laser-guided
        assert _older_group(jdam, 2).name == "GBU-10"  # laser-guided
        assert _older_group(jdam, 3).name == "Mk 84"  # unguided

    def test_the_small_jdam_ladder_reaches_unguided(self) -> None:
        assert _older_group(WeaponGroup.named("GBU-38"), 1).name == "GBU-12"
        assert _older_group(WeaponGroup.named("GBU-38"), 2).name == "Mk 82"

    def test_a_cluster_bomb_degrades_a_generation(self) -> None:
        assert _older_group(WeaponGroup.named("CBU-97"), 1).name == "CBU-87"

    @pytest.mark.parametrize("category", ["a2a-missiles", "bombs", "standoff"])
    def test_every_major_family_has_usable_depth(self, category: str) -> None:
        """Anti-ship and air-to-ground live in `standoff`, so it must not be empty."""
        with_depth = [
            g
            for g in WeaponGroup._by_name.values()
            if getattr(g, "category", None) == category
            and g.type not in PROTECTED_TYPES
            and _older_group(g, 1) is not g
        ]
        assert len(with_depth) >= 3


class TestTheWeaponCategoryData:
    def test_groups_are_tagged_with_their_source_directory(self) -> None:
        assert WeaponGroup.named("AIM-9X").category == "a2a-missiles"
        assert WeaponGroup.named("AIM-120C").category == "a2a-missiles"
        # A second directory, so the tag is proven to track the source dir rather
        # than being hardcoded for missiles.
        assert WeaponGroup.named("GBU-12").category == "bombs"

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
