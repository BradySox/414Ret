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


def _proposed_tasks(task: object) -> list[FlightType]:
    return [f.task for f in task.flights]  # type: ignore[attr-defined]


def test_air_assault_does_not_propose_an_escort_jammer() -> None:
    """An air assault never penetrates a radar-SAM ring (PlanAirAssault's
    preconditions require a cleared objective), so it keeps the SEAD/A2A escorts
    but not the jammer -- which would otherwise burn a scarce Growler and a slot
    of the per-side cap that a DEAD package could use."""
    from game.commander.tasks.primitive.airassault import PlanAirAssault

    # get_flight_size() rolls the package size off the flight-size weights.
    settings = SimpleNamespace(
        fpa_2ship_weight=1, fpa_3ship_weight=0, fpa_4ship_weight=0
    )
    target = SimpleNamespace(
        coalition=SimpleNamespace(game=SimpleNamespace(settings=settings))
    )
    task = PlanAirAssault(target=target)  # type: ignore[arg-type]
    task.propose_flights()

    tasks = _proposed_tasks(task)
    assert FlightType.AIR_ASSAULT == tasks[0]
    assert FlightType.ESCORT_JAMMER not in tasks
    # The rest of the common escort set is untouched.
    for expected in (FlightType.SEAD_ESCORT, FlightType.ESCORT):
        assert expected in tasks


def test_common_escorts_still_propose_the_jammer_by_default() -> None:
    """Only the air assault opts out; every other propose_common_escorts caller
    (strike, BAI, OCA, armed recon, motorpool, CSAR) still asks for one."""
    from game.commander.tasks.primitive.strike import PlanStrike

    task = PlanStrike(target=SimpleNamespace())  # type: ignore[arg-type]
    task.propose_common_escorts()
    assert FlightType.ESCORT_JAMMER in _proposed_tasks(task)


def test_every_proposed_escort_is_prunable() -> None:
    """A doctrine that flies unescorted (COIN/Vietnam) must be able to drop ANY
    escort tasking it proposes. A task the planner proposes as an escort but that
    is absent from PRUNABLE_ESCORTS turns "no escort was free" into "scrub the
    whole package" -- the exact deadlock the doctrine flag exists to prevent.
    §77's ESCORT_JAMMER was that hole: COIN allows the tasking and flies
    unescorted, so an unavailable Growler killed the strike outright."""
    from game.commander.packagefulfiller import PRUNABLE_ESCORTS
    from game.commander.tasks.primitive.cas import PlanCas
    from game.commander.tasks.primitive.strike import PlanStrike

    proposed: set[FlightType] = set()

    strike = PlanStrike(target=SimpleNamespace())  # type: ignore[arg-type]
    strike.propose_common_escorts()
    proposed.update(f.task for f in strike.flights)

    cas = PlanCas(target=SimpleNamespace())  # type: ignore[arg-type]
    cas.propose_flight(FlightType.TARCAP, 2, EscortType.AirToAir)
    cas.propose_flight(FlightType.SEAD_SWEEP, 2)
    proposed.update(f.task for f in cas.flights)

    assert FlightType.ESCORT_JAMMER in proposed
    assert (
        proposed <= PRUNABLE_ESCORTS
    ), f"escort taskings that would scrub their package: {proposed - PRUNABLE_ESCORTS}"


def test_dead_proposes_an_escort_jammer() -> None:
    """DEAD is the tasking §77 was built for -- the jammer's effect rises as it
    closes on a live SAM, and a DEAD package flies straight at one. It rides in on
    the common escorts, so a DEAD package always asks for one."""
    from game.commander.tasks.primitive.dead import PlanDead

    for live_radar in (True, False):
        target = SimpleNamespace(
            alive_unit_count=lambda: 4,
            has_live_radar_sam=live_radar,
            control_point=SimpleNamespace(
                coalition=SimpleNamespace(
                    game=SimpleNamespace(
                        settings=SimpleNamespace(autoplan_tankers_for_dead=False)
                    )
                )
            ),
        )
        task = PlanDead(target=target)  # type: ignore[arg-type]
        task.propose_flights()
        tasks = _proposed_tasks(task)
        assert tasks[0] is FlightType.DEAD
        assert FlightType.ESCORT_JAMMER in tasks
        # Stock DEAD composition: the common escorts always, plus a dedicated SEAD
        # flight only when the target still has a live track radar to suppress.
        assert FlightType.SEAD_ESCORT in tasks
        assert (FlightType.SEAD in tasks) is live_radar


def test_common_escorts_carry_the_jammer_alongside_both_sead_flavours() -> None:
    """The common escorts are upstream's SEAD escort + sweep + A2A, with §77's
    jammer appended on the same radar-SAM trigger. Each is pruned downstream when
    unthreatened or unflyable, so proposing all four costs nothing when they are
    not warranted."""
    from game.commander.tasks.primitive.strike import PlanStrike

    task = PlanStrike(target=SimpleNamespace())  # type: ignore[arg-type]
    task.propose_common_escorts()
    tasks = _proposed_tasks(task)
    assert FlightType.SEAD_ESCORT in tasks
    assert FlightType.SEAD_SWEEP in tasks
    assert FlightType.ESCORT in tasks
    assert FlightType.ESCORT_JAMMER in tasks
    assert tasks.count(FlightType.SEAD_ESCORT) == 1


@pytest.mark.parametrize("variant", _DEDICATED_JAMMERS)
def test_helo_package_takes_no_jet_escort_jammer(variant: str) -> None:
    """The formation-escort guard (Squadron.can_auto_assign_mission) limits a
    helo-led package to helo or LHA-capable escorts, because a plain fast jet
    cannot hold formation on it. ESCORT_JAMMER flies the same EscortFlightPlan
    but was missing from the old hand-written list, so a carrier-but-not-LHA
    Growler could be fragged onto a CH-47 assault from 89 nm away."""
    from game.squadrons.squadron import Squadron

    jammer = AircraftType.named(variant)
    assert jammer.capable_of(FlightType.ESCORT_JAMMER)
    # The premise: both dedicated jammers are carrier-capable but not LHA-capable,
    # so the guard's helo/LHA test is what excludes them.
    assert not jammer.helicopter
    assert not jammer.lha_capable

    squadron = SimpleNamespace(
        location=SimpleNamespace(cptype=SimpleNamespace(name="AIRBASE")),
        aircraft=jammer,
        can_auto_assign=lambda task: True,
    )

    def assign(task: FlightType, heli: bool) -> bool:
        return Squadron.can_auto_assign_mission(
            squadron,  # type: ignore[arg-type]
            SimpleNamespace(),  # type: ignore[arg-type]
            task,
            size=2,
            heli=heli,
            this_turn=False,
            ignore_range=True,
        )

    # A helo-led package takes none of the three formation escorts from a jet...
    for task in (
        FlightType.ESCORT_JAMMER,
        FlightType.ESCORT,
        FlightType.SEAD_ESCORT,
    ):
        assert not assign(task, heli=True), task
        # ...but a jet-led one still does.
        assert assign(task, heli=False), task

    # The independent-path escorts fly their own route and timing, so they stay
    # unguarded on purpose -- a jet may sweep ahead of a helo package.
    for task in (FlightType.SEAD_SWEEP, FlightType.TARCAP):
        assert not task.is_escort_type
        assert assign(task, heli=True), task


def test_coin_doctrine_flies_unescorted_and_allows_the_jammer() -> None:
    """The pairing that made the hole live: COIN both allows ESCORT_JAMMER (no
    tasking whitelist) and flies unescorted, so it reaches the prune branch."""
    from game.data.doctrine import COIN_DOCTRINE

    assert COIN_DOCTRINE.plan_strikes_without_full_escort
    assert COIN_DOCTRINE.allows(FlightType.ESCORT_JAMMER)


def test_radar_sam_threat_requests_the_jammer_escort() -> None:
    """check_needed_escorts marks Jammer alongside Sead on a radar-SAM route."""
    flight = SimpleNamespace(
        flight_plan=SimpleNamespace(escorted_waypoints=lambda: iter(()))
    )
    builder = SimpleNamespace(
        package=SimpleNamespace(flights=[flight], primary_flight=None)
    )
    threat_zones = SimpleNamespace(
        waypoints_threatened_by_aircraft=lambda waypoints: False,
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
