"""CI lock on the graduated ESCORT_JAMMER role (§77, 2026-07-21).

Escort jamming is a *role*, not one airframe. The effect scales to how real the
jet's EW kit is (see :mod:`game.data.escort_jamming`):

- FULL -- dedicated ALQ-99 jammers (EA-18G Growler, EA-6B Prowler): bubble +
  offensive SAM weapons-hold pulses.
- ECM -- built-in ECM fighters (F/A-18C, F-14): moderate defensive bubble.
- SELF_PROTECT -- pod fighters (F-16C, F-4E, AV-8B, A-7E): weak defensive bubble.
- LOOSE -- the opt-in stretch tier: any podded jet, token effect, never
  auto-planned unless ``escort_jamming_loose`` is on.

These tests pin the enum wiring, the tier roster + effect gradient, the loose
gate, the loadout fallback, and the escort-threat plumbing so an upstream merge
can't quietly drop a seam.
"""

from types import SimpleNamespace

import pytest

from game import persistency
from game.ato.flighttype import FlightType
from game.ato.flightplans.escort import EscortFlightPlan
from game.ato.flightplans.flightplanbuildertypes import FlightPlanBuilderTypes
from game.ato.loadouts import Loadout
from game.commander.missionproposals import EscortType
from game.commander.packagefulfiller import PackageFulfiller
from game.data.escort_jamming import EscortJammerTier, effect_for
from game.dcs.aircrafttype import AircraftType
from game.sidc import AirEntity


@pytest.fixture(autouse=True, scope="module")
def _init_persistency(tmp_path_factory: pytest.TempPathFactory) -> None:
    # Resolving an AircraftType reads the DCS saved-game folder (weapon
    # injections), which is only configured once the app boots. Point it at an
    # empty temp dir so it falls back to the bundled resources/ data.
    persistency.setup(str(tmp_path_factory.mktemp("saved_games")), False, 0)


def test_escort_jammer_enum_wiring() -> None:
    task = FlightType.ESCORT_JAMMER
    assert task.value == "Escort Jammer"
    assert task.is_escort_type
    assert task.provides_escort_coverage
    # The jamming effect is scripted; the flight itself is neither an A2A nor
    # an A2G shooter for planner categorization.
    assert not task.is_air_to_air
    assert not task.is_air_to_ground
    assert not task.is_primary_package_task
    assert task.entity_type is AirEntity.ELECTRONIC_COMBAT_JAMMER


def test_escort_jammer_uses_the_escort_flight_plan() -> None:
    # Rides the package join->split like the SEAD escort -- never a standoff
    # racetrack (that is the C-130's JAMMING task, deliberately distinct).
    flight = SimpleNamespace(flight_type=FlightType.ESCORT_JAMMER)
    assert (
        FlightPlanBuilderTypes.for_flight(flight)  # type: ignore[arg-type]
        is EscortFlightPlan.builder_type()
    )


def test_effect_gradient_is_strictly_descending() -> None:
    """Utility falls off: dedicated -> built-in ECM -> pod -> token; only the
    dedicated FULL tier ever suppresses SAMs."""
    full = effect_for(EscortJammerTier.FULL)
    ecm = effect_for(EscortJammerTier.ECM)
    sp = effect_for(EscortJammerTier.SELF_PROTECT)
    loose = effect_for(EscortJammerTier.LOOSE)
    assert (
        full.defensive_power
        > ecm.defensive_power
        > sp.defensive_power
        > loose.defensive_power
        > 0
    )
    assert full.offensive
    assert not ecm.offensive
    assert not sp.offensive
    assert not loose.offensive


# (variant display name -> expected tier). The dedicated jammers are AI-only mods
# (Growler + Prowler); the rest are curated EW-capable fighters.
_TIER_ROSTER = {
    "EA-18G Growler": EscortJammerTier.FULL,
    "EA-6B Prowler": EscortJammerTier.FULL,
    "F/A-18C Hornet (Lot 20)": EscortJammerTier.ECM,
    "F-14B Tomcat": EscortJammerTier.ECM,
    "F-16CM Fighting Falcon (Block 50)": EscortJammerTier.SELF_PROTECT,
    "F-4E-45MC Phantom II": EscortJammerTier.SELF_PROTECT,
    "AV-8B Harrier II Night Attack": EscortJammerTier.SELF_PROTECT,
    "A-7E Corsair II": EscortJammerTier.SELF_PROTECT,
    "A-10C Thunderbolt II (Suite 3)": EscortJammerTier.LOOSE,
}


@pytest.mark.parametrize("variant,tier", _TIER_ROSTER.items())
def test_tier_roster(variant: str, tier: EscortJammerTier) -> None:
    ac = AircraftType.named(variant)
    assert ac.escort_jammer_tier is tier
    # Every tagged airframe is plannable as an escort jammer (the loose ones are
    # gated at plan time, not at the capability level).
    assert ac.capable_of(FlightType.ESCORT_JAMMER)


def test_dedicated_jammers_do_offensive_suppression() -> None:
    for variant in ("EA-18G Growler", "EA-6B Prowler"):
        ac = AircraftType.named(variant)
        assert ac.escort_jammer_tier is not None
        assert effect_for(ac.escort_jammer_tier).offensive


def test_non_ew_fighter_is_not_a_jammer() -> None:
    f15c = AircraftType.named("F-15C Eagle")
    assert f15c.escort_jammer_tier is None
    assert not f15c.capable_of(FlightType.ESCORT_JAMMER)


def test_escort_jammer_loadout_falls_back_to_sead_escort() -> None:
    names = list(Loadout.default_loadout_names_for(FlightType.ESCORT_JAMMER))
    own = names.index("Retribution Escort Jammer")
    fallback = names.index("Retribution SEAD Escort")
    # A dedicated Escort Jammer preset wins when one exists; otherwise the
    # SEAD Escort fit (pods + ARMs) is the right stores.
    assert own < fallback


def _fulfiller_stub(
    *, can_plan: bool, loose: bool, squadron_tiers: list[EscortJammerTier | None]
) -> SimpleNamespace:
    squadrons = [
        SimpleNamespace(aircraft=SimpleNamespace(escort_jammer_tier=t))
        for t in squadron_tiers
    ]
    air_wing = SimpleNamespace(
        auto_assignable_for_task=lambda task: iter(squadrons),
    )
    stub = SimpleNamespace(
        air_wing_can_plan=lambda task: can_plan,
        escort_jamming_loose=loose,
        air_wing=air_wing,
    )
    # Bind the real curated-tier helper so can_plan_escort's self-call resolves.
    stub._has_curated_escort_jammer = lambda: PackageFulfiller._has_curated_escort_jammer(
        stub  # type: ignore[arg-type]
    )
    return stub


def test_curated_jammer_is_planned_with_loose_off() -> None:
    stub = _fulfiller_stub(
        can_plan=True, loose=False, squadron_tiers=[EscortJammerTier.SELF_PROTECT]
    )
    assert PackageFulfiller.can_plan_escort(stub, EscortType.Jammer)  # type: ignore[arg-type]


def test_loose_only_wing_is_gated_off_by_default() -> None:
    # Only a LOOSE-tier squadron in the wing, setting off -> no jammer planned.
    stub = _fulfiller_stub(
        can_plan=True, loose=False, squadron_tiers=[EscortJammerTier.LOOSE]
    )
    assert not PackageFulfiller.can_plan_escort(stub, EscortType.Jammer)  # type: ignore[arg-type]


def test_loose_setting_opens_the_stretch_tier() -> None:
    stub = _fulfiller_stub(
        can_plan=True, loose=True, squadron_tiers=[EscortJammerTier.LOOSE]
    )
    assert PackageFulfiller.can_plan_escort(stub, EscortType.Jammer)  # type: ignore[arg-type]


def test_no_jammer_capable_squadron_cannot_plan() -> None:
    stub = _fulfiller_stub(can_plan=False, loose=True, squadron_tiers=[])
    assert not PackageFulfiller.can_plan_escort(stub, EscortType.Jammer)  # type: ignore[arg-type]


def test_radar_sam_threat_requests_the_jammer_escort() -> None:
    """check_needed_escorts marks Jammer alongside Sead on a radar-SAM route."""
    flight = SimpleNamespace(
        flight_plan=SimpleNamespace(escorted_waypoints=lambda: iter(()))
    )
    builder = SimpleNamespace(
        package=SimpleNamespace(flights=[flight], primary_flight=None)
    )
    threat_zones = SimpleNamespace(
        waypoints_threatened_by_aircraft_engagement=lambda waypoints: False,
        waypoints_threatened_by_radar_sam=lambda waypoints: True,
    )
    stub = SimpleNamespace(
        threat_zones=threat_zones,
        doctrine=SimpleNamespace(always_escort_strikes=False),
    )
    threats = PackageFulfiller.check_needed_escorts(stub, builder)  # type: ignore[arg-type]
    assert threats[EscortType.Sead]
    assert threats[EscortType.Jammer]
    assert not threats[EscortType.AirToAir]
