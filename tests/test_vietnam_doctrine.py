"""P1 of the Vietnam Retribution mode: the VIETNAM_DOCTRINE profile.

Locks the doctrine *model* (display-name rename layer + tasking-whitelist mechanism,
behaviour cloned from COLDWAR) and the faction repoint, so a regression that drops the
renames, re-gates the whitelist, or unpoints a faction fails CI. See
docs/dev/design/414th-vietnam-retribution-notes.md.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from game.ato.flighttype import FlightType
from game.data.doctrine import (
    ALL_DOCTRINES,
    COLDWAR_DOCTRINE,
    MODERN_DOCTRINE,
    VIETNAM_AIR_DEFENSE_DOCTRINE,
    VIETNAM_DOCTRINE,
    WWII_DOCTRINE,
)
from game.data.units import UnitClass
from game.settings import Settings
from game.utils import knots, nautical_miles

_FACTIONS = Path(__file__).resolve().parents[1] / "resources" / "factions"

# The factions repointed from "coldwar" to "vietnam" doctrine in P1. BLUE (and the
# what-if Soviet bomber faction) fly the offensive doctrine; the red air-defense
# split moved Hanoi's factions to "vietnam_air_defense" below.
_VIETNAM_DOCTRINE_FACTIONS = [
    "USA 1970 Vietnam War.json",
    "USA 1971 Vietnam War.json",
    "USSR 1971 Vietnam War.json",
    "usa_1965.json",
    "usa_1970.json",
]

# Hanoi's factions: a pure GCI air-defense force (no Alpha Strike fan, no forced
# strike escorts, no strike-escort reserve trimming the defensive BARCAP).
_VIETNAM_AIR_DEFENSE_FACTIONS = [
    "nva_1970.json",
    "vietcong_1965.json",
    "vietcong_1970.json",
    "vietnam_1965.json",
    "vietnam_1970.json",
]


def test_vietnam_doctrine_registered() -> None:
    assert VIETNAM_DOCTRINE in ALL_DOCTRINES
    assert VIETNAM_DOCTRINE.name == "vietnam"
    assert VIETNAM_AIR_DEFENSE_DOCTRINE in ALL_DOCTRINES
    assert VIETNAM_AIR_DEFENSE_DOCTRINE.name == "vietnam_air_defense"


def test_air_defense_doctrine_differs_only_in_the_offensive_levers() -> None:
    # The red split: Hanoi's air arm keeps the whole Vietnam era identity (renames,
    # knife-fight ranges, gci_ambush, ground OOB) and sheds ONLY BLUE's offensive
    # levers (plus the narrower tasking whitelist below) -- resetting exactly those
    # must recover VIETNAM_DOCTRINE, so no other geometry silently drifts between
    # the two.
    rebadged = replace(
        VIETNAM_AIR_DEFENSE_DOCTRINE,
        name="vietnam",
        strike_flight_count=VIETNAM_DOCTRINE.strike_flight_count,
        always_escort_strikes=True,
        strike_escort_reserve=VIETNAM_DOCTRINE.strike_escort_reserve,
        escort_support_aircraft=False,
        tasking_whitelist=VIETNAM_DOCTRINE.tasking_whitelist,
    )
    assert rebadged == VIETNAM_DOCTRINE
    # The defensive identity survives the split.
    assert VIETNAM_AIR_DEFENSE_DOCTRINE.gci_ambush is True
    assert VIETNAM_AIR_DEFENSE_DOCTRINE.tasking_whitelist is not None
    assert VIETNAM_AIR_DEFENSE_DOCTRINE.display_name_for(FlightType.BARCAP) == "MiGCAP"
    # ...and the offensive levers are genuinely off: no fan, no BARCAP-trimming
    # reserve, no forced strike escorts.
    assert VIETNAM_AIR_DEFENSE_DOCTRINE.strike_flight_count == 1
    assert VIETNAM_AIR_DEFENSE_DOCTRINE.strike_escort_reserve == 0
    assert VIETNAM_AIR_DEFENSE_DOCTRINE.always_escort_strikes is False
    assert VIETNAM_AIR_DEFENSE_DOCTRINE.escort_support_aircraft is True
    # Hanoi never heli-assaulted a foreign air base -- Air Assault is a mass/insertion
    # mission, not an ambush. BLUE keeps it; red doesn't (2026-07-02 playtest finding:
    # red was air-assaulting 1968 Yankee Station's Maykop-Khanskaya, the Ubon/"Thailand"
    # rear base, purely because it had no garrison TGO).
    assert not VIETNAM_AIR_DEFENSE_DOCTRINE.allows(FlightType.AIR_ASSAULT)
    assert VIETNAM_DOCTRINE.allows(FlightType.AIR_ASSAULT)


def test_display_name_overrides_iconic_taskings() -> None:
    assert VIETNAM_DOCTRINE.display_name_for(FlightType.BARCAP) == "MiGCAP"
    assert VIETNAM_DOCTRINE.display_name_for(FlightType.STRIKE) == "Alpha Strike"
    assert VIETNAM_DOCTRINE.display_name_for(FlightType.SEAD) == "Iron Hand"
    assert VIETNAM_DOCTRINE.display_name_for(FlightType.SCAR) == "Sandy"


def test_unmapped_tasking_falls_back_to_enum_value() -> None:
    # CAS is intentionally not renamed -> the canonical persisted label.
    assert VIETNAM_DOCTRINE.display_name_for(FlightType.CAS) == FlightType.CAS.value


def test_existing_doctrines_have_no_renames() -> None:
    for doctrine in (MODERN_DOCTRINE, COLDWAR_DOCTRINE, WWII_DOCTRINE):
        assert dict(doctrine.task_display_names) == {}
        assert doctrine.display_name_for(FlightType.BARCAP) == FlightType.BARCAP.value


def test_non_vietnam_whitelists_stay_open() -> None:
    # Every non-Vietnam doctrine keeps its whitelist open (behaviour == COLDWAR).
    for doctrine in (MODERN_DOCTRINE, COLDWAR_DOCTRINE, WWII_DOCTRINE):
        assert doctrine.tasking_whitelist is None
        assert doctrine.allows(FlightType.DEAD)
        assert doctrine.allows(FlightType.ANTISHIP)


def test_vietnam_whitelist_drops_sead_dead_antiship() -> None:
    # P3: Vietnam has no reliable SEAD and no naval threat, so the auto-planner must not
    # produce SEAD/DEAD/anti-ship -- this is what stops an A-1 being tasked a SEAD sweep.
    for dropped in (
        FlightType.DEAD,
        FlightType.SEAD,
        FlightType.SEAD_ESCORT,
        FlightType.SEAD_SWEEP,
        FlightType.ANTISHIP,
    ):
        assert not VIETNAM_DOCTRINE.allows(dropped), dropped
    # The core taskings the campaign still flies stay allowed.
    for kept in (
        FlightType.STRIKE,
        FlightType.BAI,
        FlightType.CAS,
        FlightType.BARCAP,
        FlightType.ESCORT,
        FlightType.TARCAP,
        FlightType.ARMED_RECON,
        FlightType.AEWC,
    ):
        assert VIETNAM_DOCTRINE.allows(kept), kept


def test_allows_respects_a_whitelist() -> None:
    gated = replace(VIETNAM_DOCTRINE, tasking_whitelist=frozenset({FlightType.STRIKE}))
    assert gated.allows(FlightType.STRIKE)
    assert not gated.allows(FlightType.DEAD)


def test_vietnam_differs_from_coldwar_only_in_the_intended_fields() -> None:
    # Vietnam is a COLDWAR clone EXCEPT for a known, enumerated set of deltas: the display
    # layer (name + renames), the P3 behaviour fields, and the period-authentic planner
    # numbers (A2A engagement ranges, rtb_speed, ground OOB). Resetting exactly those must
    # recover COLDWAR -- so no *other* geometry silently drifted.
    rebadged = replace(
        VIETNAM_DOCTRINE,
        name="coldwar",
        task_display_names={},
        tasking_whitelist=None,
        strike_through_air_defense_threat=False,
        plan_strikes_without_full_escort=False,
        strike_flight_count=1,
        always_escort_strikes=False,
        gci_ambush=False,
        strike_escort_reserve=0,
        escort_support_aircraft=True,
        low_level_attack_altitude=None,
        cap_engagement_range=COLDWAR_DOCTRINE.cap_engagement_range,
        escort_engagement_range=COLDWAR_DOCTRINE.escort_engagement_range,
        rtb_speed=COLDWAR_DOCTRINE.rtb_speed,
        ground_unit_procurement_ratios=COLDWAR_DOCTRINE.ground_unit_procurement_ratios,
    )
    assert rebadged == COLDWAR_DOCTRINE


def test_vietnam_a2a_ranges_are_period_short() -> None:
    # Early Sparrow/short-IR Sidewinder + guns -> engage far closer than the Cold War BVR
    # standoff, turning intercepts into visual merges (period feel at the planner level).
    assert VIETNAM_DOCTRINE.cap_engagement_range < COLDWAR_DOCTRINE.cap_engagement_range
    assert (
        VIETNAM_DOCTRINE.escort_engagement_range
        < COLDWAR_DOCTRINE.escort_engagement_range
    )
    assert VIETNAM_DOCTRINE.cap_engagement_range == nautical_miles(22)
    assert VIETNAM_DOCTRINE.escort_engagement_range == nautical_miles(10)


def test_vietnam_rtb_speed_is_subsonic_period() -> None:
    assert VIETNAM_DOCTRINE.rtb_speed < COLDWAR_DOCTRINE.rtb_speed
    assert VIETNAM_DOCTRINE.rtb_speed == knots(400)


def test_vietnam_ground_oob_is_infantry_heavy_no_atgm() -> None:
    # The Vietnam ground war was infantry/artillery/AAA-heavy with only light armour -- the
    # opposite of Cold War's TANK+ATGM+IFV fist. ATGM/IFV are the Yom Kippur / Central-Front
    # weapons and are never procured under Vietnam doctrine (ratio 0).
    viet = VIETNAM_DOCTRINE.ground_unit_procurement_ratios
    cw = COLDWAR_DOCTRINE.ground_unit_procurement_ratios
    assert viet.for_unit_class(UnitClass.INFANTRY) > viet.for_unit_class(UnitClass.TANK)
    assert viet.for_unit_class(UnitClass.TANK) < cw.for_unit_class(UnitClass.TANK)
    assert viet.for_unit_class(UnitClass.ATGM) == 0
    assert viet.for_unit_class(UnitClass.IFV) == 0
    # ... which Cold War DID field, so the difference is real, not a shared empty.
    assert cw.for_unit_class(UnitClass.ATGM) > 0


def test_vietnam_relaxes_strike_gates_only() -> None:
    # P3: with no reliable SEAD and few fighters, Vietnam strikes into unsuppressed air
    # defenses AND flies unescorted rather than deadlocking the whole offensive fleet.
    assert VIETNAM_DOCTRINE.strike_through_air_defense_threat is True
    assert VIETNAM_DOCTRINE.plan_strikes_without_full_escort is True
    for d in (MODERN_DOCTRINE, COLDWAR_DOCTRINE, WWII_DOCTRINE):
        assert d.strike_through_air_defense_threat is False
        assert d.plan_strikes_without_full_escort is False


def test_vietnam_strike_is_massed_and_force_escorted() -> None:
    # The real Alpha Strike: Vietnam masses up to FOUR coordinated shared-TOT surge
    # sections on one target + the forced fighter escort (always_escort_strikes).
    # Restored from the single-section revert once the fighter economy held
    # (escort_support_aircraft off + strike_escort_reserve + its fence). Stock
    # doctrines keep the single section.
    assert VIETNAM_DOCTRINE.strike_flight_count == 4
    assert VIETNAM_DOCTRINE.always_escort_strikes is True
    for d in (MODERN_DOCTRINE, COLDWAR_DOCTRINE, WWII_DOCTRINE):
        assert d.strike_flight_count == 1
        assert d.always_escort_strikes is False


def test_from_settings_preserves_renames_whitelist_and_flags() -> None:
    # from_settings rebuilds the frozen dataclass field by field -- the additive fields
    # must survive, or a settings-adjusted Vietnam doctrine would silently lose them.
    out = VIETNAM_DOCTRINE.from_settings(Settings())
    assert out.display_name_for(FlightType.STRIKE) == "Alpha Strike"
    assert out.tasking_whitelist is not None
    assert not out.allows(FlightType.DEAD)
    assert out.allows(FlightType.STRIKE)
    assert out.strike_through_air_defense_threat is True
    assert out.plan_strikes_without_full_escort is True
    assert out.strike_flight_count == 4
    assert out.always_escort_strikes is True


def test_vietnam_faction_jsons_declare_vietnam_doctrine() -> None:
    for name in _VIETNAM_DOCTRINE_FACTIONS:
        data = json.loads((_FACTIONS / name).read_text(encoding="utf-8"))
        assert (
            data.get("doctrine") == "vietnam"
        ), f"{name} must declare 'doctrine: vietnam' (P1 repoint)."
    for name in _VIETNAM_AIR_DEFENSE_FACTIONS:
        data = json.loads((_FACTIONS / name).read_text(encoding="utf-8"))
        assert (
            data.get("doctrine") == "vietnam_air_defense"
        ), f"{name} must declare 'doctrine: vietnam_air_defense' (the red split)."


def test_faction_loader_resolves_air_defense_doctrine(tmp_path: Path) -> None:
    # The loader's elif chain silently falls back to MODERN on an unknown doctrine
    # string, so a typo'd branch would un-Vietnam every red faction without failing
    # anywhere else -- load a real red faction JSON through Faction.from_dict.
    from game import persistency
    from game.factions.faction import Faction

    persistency.setup(str(tmp_path), False, 0)
    data = json.loads((_FACTIONS / "nva_1970.json").read_text(encoding="utf-8"))
    faction = Faction.from_dict(data)
    assert faction.doctrine is VIETNAM_AIR_DEFENSE_DOCTRINE


def test_flight_task_display_name_resolves_through_coalition_doctrine() -> None:
    # P1b: the display read-path. Flight.task_display_name navigates
    # coalition -> doctrine -> display_name_for; lock that path + the rename.
    from types import SimpleNamespace

    from game.ato.flight import Flight

    flight = Flight.__new__(Flight)
    flight.coalition = SimpleNamespace(doctrine=VIETNAM_DOCTRINE)  # type: ignore[assignment]
    flight.flight_type = FlightType.SEAD
    assert flight.task_display_name == "Iron Hand"
    # A STRIKE flight only earns "Alpha Strike" when its package masses; a lone
    # section is a plain Strike (a real alpha strike is a deck-load, not a 2-ship).
    flight.flight_type = FlightType.STRIKE
    flight.package = SimpleNamespace(is_massed_strike=False)  # type: ignore[assignment]
    assert flight.task_display_name == "Strike"
    flight.package = SimpleNamespace(is_massed_strike=True)  # type: ignore[assignment]
    assert flight.task_display_name == "Alpha Strike"


def test_flightdata_task_display_name_resolves_through_squadron_doctrine() -> None:
    from types import SimpleNamespace

    from game.missiongenerator.aircraft.flightdata import FlightData

    fd = FlightData.__new__(FlightData)
    fd.squadron = SimpleNamespace(  # type: ignore[assignment]
        coalition=SimpleNamespace(doctrine=VIETNAM_DOCTRINE)
    )
    fd.flight_type = FlightType.STRIKE
    # The massing gate applies here too: lone section = "Strike".
    fd.package = SimpleNamespace(is_massed_strike=False)  # type: ignore[assignment]
    assert fd.task_display_name == "Strike"
    fd.package = SimpleNamespace(is_massed_strike=True)  # type: ignore[assignment]
    assert fd.task_display_name == "Alpha Strike"


def test_package_description_uses_doctrine_rename() -> None:
    # The planning table's package label routes through the doctrine display layer
    # (the deferred P1b site): a Vietnam package reads "Alpha Strike"/"MiGCAP", a stock
    # package keeps the canonical label and the combined "OCA Strike" tag. The
    # "Alpha Strike" label is EARNED: only a real deck-load (>= 2 STRIKE sections
    # totalling >= 4 bombers) reads it; a single section -- or a pair of
    # single-ships on a trivial target -- stays a plain "Strike".
    from types import SimpleNamespace

    from game.ato.package import Package

    def label(doctrine: object, *sections: tuple[FlightType, int]) -> str:
        flights = [
            SimpleNamespace(
                flight_type=flight_type,
                count=count,
                coalition=SimpleNamespace(doctrine=doctrine),
            )
            for flight_type, count in sections
        ]
        pkg = Package.__new__(Package)
        pkg.flights = flights  # type: ignore[assignment]
        return pkg.package_description

    strike2 = (FlightType.STRIKE, 2)
    strike1 = (FlightType.STRIKE, 1)
    # A deck-load = Alpha Strike; anything thinner is just a Strike.
    assert label(VIETNAM_DOCTRINE, strike2, strike2) == "Alpha Strike"
    assert label(VIETNAM_DOCTRINE, strike2) == "Strike"
    assert label(VIETNAM_DOCTRINE, strike1, strike1) == "Strike"
    assert label(VIETNAM_DOCTRINE, (FlightType.BARCAP, 2)) == "MiGCAP"
    assert label(VIETNAM_DOCTRINE, (FlightType.OCA_RUNWAY, 2)) == "Airfield Strike"
    # Non-Vietnam doctrine is unchanged, including the combined OCA label.
    assert label(COLDWAR_DOCTRINE, strike2) == "Strike"
    assert label(COLDWAR_DOCTRINE, (FlightType.OCA_RUNWAY, 2)) == "OCA Strike"


def test_vietnam_authored_low_level_attack_profile() -> None:
    # The deck-level delivery that lets AI attack flights trip the §39 snake-and-nape
    # release gate (and fly inside the §33 flak envelope): Vietnam CAS/BAI/Armed Recon
    # cap their combat legs at 500 ft (the napeCeilingFt default). Both Vietnam
    # doctrines fly it; every stock doctrine keeps None (stock altitudes).
    from game.utils import feet

    assert VIETNAM_DOCTRINE.low_level_attack_altitude == feet(500)
    assert VIETNAM_AIR_DEFENSE_DOCTRINE.low_level_attack_altitude == feet(500)
    for d in (MODERN_DOCTRINE, COLDWAR_DOCTRINE, WWII_DOCTRINE):
        assert d.low_level_attack_altitude is None
    # from_settings rebuilds field by field -- the profile must survive.
    assert VIETNAM_DOCTRINE.from_settings(Settings()).low_level_attack_altitude == feet(
        500
    )


def test_vietnam_gci_ambush_posture() -> None:
    # W5: only Vietnam doctrine flies the GCI hit-and-run ambush; every other
    # doctrine keeps the modern stand-and-fight dispatcher defaults.
    assert VIETNAM_DOCTRINE.gci_ambush is True
    for d in (MODERN_DOCTRINE, COLDWAR_DOCTRINE, WWII_DOCTRINE):
        assert d.gci_ambush is False


def test_dispatcher_tuning_shrinks_radii_for_ambush_doctrine() -> None:
    from game.missiongenerator.interceptluadata import (
        AMBUSH_GCI_RADIUS_NM,
        dispatcher_tuning,
    )

    tuning = dispatcher_tuning(VIETNAM_DOCTRINE, 60, 100)
    assert tuning.ambush is True
    # Engage radius collapses to the P1c close-fight number...
    assert tuning.engage_nm == round(
        VIETNAM_DOCTRINE.cap_engagement_range.nautical_miles
    )
    # ...and the scramble radius caps at the late-launch ambush distance.
    assert tuning.scramble_nm == AMBUSH_GCI_RADIUS_NM
    # The Lua applies its own tight hit-and-run leash for an ambush posture.
    assert tuning.disengage_nm == 0
    # A tighter user setting still wins (min, never max).
    tight = dispatcher_tuning(VIETNAM_DOCTRINE, 15, 30)
    assert tight.engage_nm == 15
    assert tight.scramble_nm == 30


def test_dispatcher_tuning_ambush_ignores_forward_defense() -> None:
    """Forward defense must never widen the era's late, close GCI slash."""
    from game.missiongenerator.interceptluadata import (
        AMBUSH_GCI_RADIUS_NM,
        dispatcher_tuning,
    )

    tuning = dispatcher_tuning(VIETNAM_DOCTRINE, 60, 100, forward_defense=True)
    assert tuning.ambush is True
    assert tuning.scramble_nm == AMBUSH_GCI_RADIUS_NM
    assert tuning.disengage_nm == 0


def test_dispatcher_tuning_passes_settings_through_for_other_doctrines() -> None:
    from game.missiongenerator.interceptluadata import (
        DispatcherTuning,
        dispatcher_tuning,
    )

    for d in (MODERN_DOCTRINE, COLDWAR_DOCTRINE, WWII_DOCTRINE):
        assert dispatcher_tuning(d, 60, 100) == DispatcherTuning(
            engage_nm=60, scramble_nm=100, disengage_nm=0, ambush=False
        )


def test_vietnam_reserves_fighters_for_strike_escort() -> None:
    # The "reserve a fighter ahead of BARCAP" lever: only Vietnam holds fighters
    # back so always_escort_strikes can actually fill (naked-B-52 playtest fix).
    assert VIETNAM_DOCTRINE.strike_escort_reserve == 4
    for d in (MODERN_DOCTRINE, COLDWAR_DOCTRINE, WWII_DOCTRINE):
        assert d.strike_escort_reserve == 0


def test_vietnam_support_orbits_fly_unescorted() -> None:
    # The fighter-economy half of the escort fix: AWACS/tanker escorts consumed
    # the whole fighter force before any strike proposed its own. Vietnam-only.
    assert VIETNAM_DOCTRINE.escort_support_aircraft is False
    for d in (MODERN_DOCTRINE, COLDWAR_DOCTRINE, WWII_DOCTRINE):
        assert d.escort_support_aircraft is True
