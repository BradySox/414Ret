"""CI lock on the ESCORT_JAMMER role (§77).

Escort jamming is flown only by dedicated jammers -- the EA-18G Growler and the
EA-6B Prowler, the only airframes that declare the ``Escort Jammer`` task. No
graduated tiers, no podded stand-ins: any other jet (Hornet, Viper, Harrier,
Tomcat, A-10 ...) is not a jammer. These tests pin the roster, the escort
plumbing, the per-side cap, and the loadout fallback so an upstream merge can't
quietly widen the net or drop a seam.
"""

from types import SimpleNamespace

import pytest

from game import persistency
from game.ato.flighttype import FlightType
from game.ato.flightplans.escort import EscortFlightPlan
from game.ato.flightplans.flightplanbuildertypes import FlightPlanBuilderTypes
from game.campaignloader.campaignairwingconfig import SquadronConfig
from game.ato.loadouts import Loadout
from game.commander.missionproposals import EscortType
from game.commander.packagefulfiller import PackageFulfiller
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


# The ONLY airframes that fly escort jamming -- the two dedicated ALQ-99 jammers.
_DEDICATED_JAMMERS = ("EA-18G Growler", "EA-6B Prowler")

# Everything with a jammer/ECM pod that USED to be a graduated-tier jammer, plus a
# plain fighter. None of them may fly escort jamming any more.
_NOT_JAMMERS = (
    "F/A-18C Hornet (Lot 20)",
    "F-14B Tomcat",
    "F-16CM Fighting Falcon (Block 50)",
    "F-4E-45MC Phantom II",
    "AV-8B Harrier II Night Attack",
    "A-7E Corsair II",
    "A-10C Thunderbolt II (Suite 3)",
    "F-15C Eagle",
)


@pytest.mark.parametrize("variant", _DEDICATED_JAMMERS)
def test_dedicated_jammers_are_the_only_capable_airframes(variant: str) -> None:
    ac = AircraftType.named(variant)
    assert ac.capable_of(FlightType.ESCORT_JAMMER)


@pytest.mark.parametrize("variant", _NOT_JAMMERS)
def test_other_airframes_cannot_escort_jam(variant: str) -> None:
    ac = AircraftType.named(variant)
    assert not ac.capable_of(FlightType.ESCORT_JAMMER)


def test_sead_primary_squadron_auto_offers_escort_jammer() -> None:
    """A campaign that authored a dedicated EW jet as a SEAD squadron (#717's
    EA-6B Prowlers: primary SEAD, secondary [SEAD Escort]) still auto-gains the
    Escort Jammer role -- offered to every capable squadron like TARPS, with no
    per-campaign edit. The capability filter drops it for non-jammer airframes."""
    cfg = SquadronConfig.from_data(
        {
            "primary": "SEAD",
            "secondary": ["SEAD Escort"],
            "aircraft": ["EA-6B Prowler"],
        }
    )
    assert FlightType.ESCORT_JAMMER in cfg.auto_assignable
    # And the Prowler airframe is genuinely capable, so the filter keeps it.
    prowler = AircraftType.named("EA-6B Prowler")
    kept = {t for t in cfg.auto_assignable if prowler.capable_of(t)}
    assert FlightType.ESCORT_JAMMER in kept


def test_dedicated_jammers_prefer_jamming_over_sead_escort() -> None:
    """'Prefer them as jammers' (user call 2026-07-21): a dedicated jammer
    out-priorities itself at Escort Jammer over SEAD Escort, AND sits below the
    strike-fighters at SEAD Escort -- so in a package's escort fill (SEAD Escort
    resolves first) a Hornet/Viper takes SEAD Escort and the dedicated jammer is
    freed for the Escort Jammer slot."""
    hornet_se = AircraftType.named("F/A-18C Hornet (Lot 20)").task_priority(
        FlightType.SEAD_ESCORT
    )
    for variant in _DEDICATED_JAMMERS:
        ac = AircraftType.named(variant)
        assert ac.task_priority(FlightType.ESCORT_JAMMER) > ac.task_priority(
            FlightType.SEAD_ESCORT
        )
        assert ac.task_priority(FlightType.SEAD_ESCORT) < hornet_se
        # SEAD as a package lead is untouched -- they're still SEAD shooters.
        assert ac.task_priority(FlightType.SEAD) > hornet_se


def test_escort_jammer_loadout_falls_back_to_sead_escort() -> None:
    names = list(Loadout.default_loadout_names_for(FlightType.ESCORT_JAMMER))
    own = names.index("Retribution Escort Jammer")
    fallback = names.index("Retribution SEAD Escort")
    # A dedicated Escort Jammer preset wins when one exists; otherwise the
    # SEAD Escort fit (pods + ARMs) is the right stores.
    assert own < fallback


def _fulfiller_stub(
    *,
    can_plan: bool,
    planned_jammers: int = 0,
    max_jammers: int = 4,
) -> SimpleNamespace:
    # A stub ATO already holding `planned_jammers` ESCORT_JAMMER flights.
    jammer_flights = [
        SimpleNamespace(flight_type=FlightType.ESCORT_JAMMER)
        for _ in range(planned_jammers)
    ]
    ato = SimpleNamespace(packages=[SimpleNamespace(flights=jammer_flights)])
    stub = SimpleNamespace(
        air_wing_can_plan=lambda task: can_plan,
        max_escort_jammers=max_jammers,
        ato=ato,
    )
    # Bind the real cap helper so can_plan_escort resolves it on the stub.
    stub._escort_jammer_cap_reached = lambda: PackageFulfiller._escort_jammer_cap_reached(
        stub  # type: ignore[arg-type]
    )
    return stub


def test_jammer_is_planned_when_the_wing_fields_one() -> None:
    stub = _fulfiller_stub(can_plan=True)
    assert PackageFulfiller.can_plan_escort(stub, EscortType.Jammer)  # type: ignore[arg-type]


def test_no_jammer_capable_squadron_cannot_plan() -> None:
    stub = _fulfiller_stub(can_plan=False)
    assert not PackageFulfiller.can_plan_escort(stub, EscortType.Jammer)  # type: ignore[arg-type]


def test_escort_jammer_cap_stops_planning_when_reached() -> None:
    # Balance: once the ATO already holds max_escort_jammers, no more are planned.
    at_cap = _fulfiller_stub(can_plan=True, planned_jammers=4, max_jammers=4)
    assert not PackageFulfiller.can_plan_escort(at_cap, EscortType.Jammer)  # type: ignore[arg-type]
    below_cap = _fulfiller_stub(can_plan=True, planned_jammers=3, max_jammers=4)
    assert PackageFulfiller.can_plan_escort(below_cap, EscortType.Jammer)  # type: ignore[arg-type]


def test_escort_jammer_cap_zero_disables_auto_planning() -> None:
    stub = _fulfiller_stub(can_plan=True, planned_jammers=0, max_jammers=0)
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
