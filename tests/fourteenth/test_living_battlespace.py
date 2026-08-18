"""§89 living battlespace: P1 (curve, pinning, launch trigger) and P2
(expended stores, mid-air AI fuel, recovery residue gating + the removal-site
residue ledger)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timedelta

import pytest

from game.ato.flighttype import FlightType
from game.data.weapons import WeaponType
from game.fourteenth.living_battlespace import (
    auto_preroll_stop_needed,
    clear_completed_residue,
    followon_window_minutes,
    idle_spawn_count,
    pin_player_packages,
    preroll_brief_lines,
    preroll_minutes,
    record_completed_residue,
    recovery_residue_enabled,
    residue_flights_for,
    stores_expended,
    use_estimated_fuel_for_ai,
    weapon_survives_expenditure,
)
from game.settings import Settings

NOW = datetime(2027, 7, 17, 14, 0)


def _settings(on: bool = True, cap: int = 40) -> Settings:
    settings = Settings()
    settings.living_battlespace_preroll = on
    settings.living_battlespace_preroll_cap = cap
    return settings


class FakeFlightPlan:
    def __init__(self, startup: datetime) -> None:
        self._startup = startup

    def startup_time(self) -> datetime:
        return self._startup


class FakeFlight:
    def __init__(self, startup: datetime) -> None:
        self.flight_plan = FakeFlightPlan(startup)


class FakePackage:
    def __init__(
        self, startups: list[datetime], has_players: bool, tot: datetime = NOW
    ) -> None:
        self.time_over_target = tot
        self.flights = [FakeFlight(s) for s in startups]
        self.has_players = has_players


class FakeAto:
    def __init__(self, packages: list[FakePackage]) -> None:
        self.packages = packages


class FakeGame:
    def __init__(self, settings: Settings, turn: int, clients: bool = True) -> None:
        self.settings = settings
        self.turn = turn
        self._clients = clients

    def ato_has_clients(self) -> bool:
        return self._clients


class FakeCoalition:
    def __init__(self, game: FakeGame, packages: list[FakePackage]) -> None:
        self.game = game
        self.ato = FakeAto(packages)


def test_gate_off_is_zero_for_all_turns() -> None:
    settings = _settings(on=False)
    assert all(preroll_minutes(settings, turn) == 0 for turn in range(12))


def test_phase_curve_values() -> None:
    settings = _settings()
    assert preroll_minutes(settings, 0) == 0
    assert preroll_minutes(settings, 1) == 15
    assert preroll_minutes(settings, 2) == 15
    assert preroll_minutes(settings, 3) == 40
    assert preroll_minutes(settings, 10) == 40


def test_cap_bounds_the_whole_curve() -> None:
    assert preroll_minutes(_settings(cap=20), 3) == 20
    assert preroll_minutes(_settings(cap=10), 1) == 10
    assert preroll_minutes(_settings(cap=10), 0) == 0


def test_pin_delays_player_package_to_the_offset() -> None:
    package = FakePackage([NOW + timedelta(minutes=5)], has_players=True)
    coalition = FakeCoalition(FakeGame(_settings(), turn=3), [package])
    pin_player_packages(coalition, NOW)  # type: ignore[arg-type]
    assert package.time_over_target == NOW + timedelta(minutes=35)


def test_pin_uses_earliest_flight_startup() -> None:
    package = FakePackage(
        [NOW + timedelta(minutes=20), NOW + timedelta(minutes=5)], has_players=True
    )
    coalition = FakeCoalition(FakeGame(_settings(), turn=3), [package])
    pin_player_packages(coalition, NOW)  # type: ignore[arg-type]
    assert package.time_over_target == NOW + timedelta(minutes=35)


def test_pin_leaves_ai_packages_alone() -> None:
    package = FakePackage([NOW + timedelta(minutes=5)], has_players=False)
    coalition = FakeCoalition(FakeGame(_settings(), turn=3), [package])
    pin_player_packages(coalition, NOW)  # type: ignore[arg-type]
    assert package.time_over_target == NOW


def test_pin_never_pulls_a_later_start_earlier() -> None:
    package = FakePackage([NOW + timedelta(minutes=60)], has_players=True)
    coalition = FakeCoalition(FakeGame(_settings(), turn=3), [package])
    pin_player_packages(coalition, NOW)  # type: ignore[arg-type]
    assert package.time_over_target == NOW


def test_pin_tolerates_a_package_with_no_flights() -> None:
    package = FakePackage([], has_players=True)
    coalition = FakeCoalition(FakeGame(_settings(), turn=3), [package])
    pin_player_packages(coalition, NOW)  # type: ignore[arg-type]
    assert package.time_over_target == NOW


def test_pin_is_a_noop_with_the_gate_off_and_on_turn_zero() -> None:
    for game in (FakeGame(_settings(on=False), turn=3), FakeGame(_settings(), turn=0)):
        package = FakePackage([NOW + timedelta(minutes=5)], has_players=True)
        pin_player_packages(FakeCoalition(game, [package]), NOW)  # type: ignore[arg-type]
        assert package.time_over_target == NOW


def test_auto_preroll_stop_needed() -> None:
    assert not auto_preroll_stop_needed(FakeGame(_settings(on=False), turn=3))  # type: ignore[arg-type]
    assert not auto_preroll_stop_needed(FakeGame(_settings(), turn=0))  # type: ignore[arg-type]
    assert not auto_preroll_stop_needed(FakeGame(_settings(), turn=3, clients=False))  # type: ignore[arg-type]
    assert auto_preroll_stop_needed(FakeGame(_settings(), turn=3))  # type: ignore[arg-type]


# --- P2: expended stores, mid-air AI fuel, recovery residue ---


class FakeCoalitionRef:
    def __init__(self, game: FakeGame) -> None:
        self.game = game


class FakeInFlightState:
    in_flight = True

    def __init__(self, passed: bool) -> None:
        self._passed = passed

    def has_passed_waypoint(self, waypoint: object) -> bool:
        return self._passed


class FakeGroundState:
    in_flight = False


class FakeTotPlan:
    tot_waypoint = "TARGET"


class FakeNoTotPlan:
    @property
    def tot_waypoint(self) -> object:
        raise AttributeError("no target waypoint on this plan")


class FakeStoresFlight:
    def __init__(
        self,
        settings: Settings,
        task: FlightType,
        state: object,
        plan: object | None = None,
    ) -> None:
        self.coalition = FakeCoalitionRef(FakeGame(settings, turn=3))
        self.flight_type = task
        self.state = state
        self.flight_plan = FakeTotPlan() if plan is None else plan


class FakeWeaponGroup:
    def __init__(self, wtype: WeaponType) -> None:
        self.type = wtype


class FakeWeapon:
    def __init__(self, wtype: WeaponType) -> None:
        self.weapon_group = FakeWeaponGroup(wtype)


def test_stores_expended_past_target_strike() -> None:
    flight = FakeStoresFlight(_settings(), FlightType.STRIKE, FakeInFlightState(True))
    assert stores_expended(flight)  # type: ignore[arg-type]


def test_stores_expended_declines() -> None:
    on = _settings()
    cases = [
        FakeStoresFlight(
            _settings(on=False), FlightType.STRIKE, FakeInFlightState(True)
        ),
        FakeStoresFlight(on, FlightType.BARCAP, FakeInFlightState(True)),
        FakeStoresFlight(on, FlightType.CAS, FakeInFlightState(True)),
        FakeStoresFlight(on, FlightType.STRIKE, FakeGroundState()),
        FakeStoresFlight(on, FlightType.STRIKE, FakeInFlightState(False)),
        FakeStoresFlight(
            on, FlightType.STRIKE, FakeInFlightState(True), FakeNoTotPlan()
        ),
    ]
    for flight in cases:
        assert not stores_expended(flight)  # type: ignore[arg-type]


def test_weapon_survives_expenditure_pods_only() -> None:
    for kept in (WeaponType.TGP, WeaponType.JAMMER, WeaponType.DECOY):
        assert weapon_survives_expenditure(FakeWeapon(kept))  # type: ignore[arg-type]
    for dropped in (WeaponType.ARM, WeaponType.LGB, WeaponType.UNKNOWN):
        assert not weapon_survives_expenditure(FakeWeapon(dropped))  # type: ignore[arg-type]


def test_use_estimated_fuel_for_ai() -> None:
    airborne = FakeStoresFlight(_settings(), FlightType.STRIKE, FakeInFlightState(True))
    grounded = FakeStoresFlight(_settings(), FlightType.STRIKE, FakeGroundState())
    gated = FakeStoresFlight(
        _settings(on=False), FlightType.STRIKE, FakeInFlightState(True)
    )
    assert use_estimated_fuel_for_ai(airborne)  # type: ignore[arg-type]
    assert not use_estimated_fuel_for_ai(grounded)  # type: ignore[arg-type]
    assert not use_estimated_fuel_for_ai(gated)  # type: ignore[arg-type]


def test_recovery_residue_enabled_follows_the_gate() -> None:
    assert recovery_residue_enabled(_settings())
    assert not recovery_residue_enabled(_settings(on=False))


# --- P2: the completed-residue ledger (row B57) ---
#
# The earlier fakes never modeled the sim's removal loop, which pulls every
# Completed flight out of its package at the tick boundary -- so the ATO walk
# at generation is structurally blind to them. These fakes model that removal.


class FakeResidueRoster:
    def __init__(self, size: int) -> None:
        self.max_size = size
        self.cleared = False

    def clear(self) -> None:
        self.cleared = True


class FakeResidueAto:
    def __init__(self) -> None:
        self.packages: list[FakeResiduePackage] = []

    def remove_package(self, package: FakeResiduePackage) -> None:
        self.packages.remove(package)


class FakeResidueCoalition:
    def __init__(self, settings: Settings) -> None:
        self.game = FakeGame(settings, turn=3)
        self.ato = FakeResidueAto()


class FakeResidueSquadron:
    """Arrival follows a live relocation order, like the real Squadron."""

    def __init__(self, coalition: FakeResidueCoalition, home: str) -> None:
        self.coalition = coalition
        self.location = home
        self.destination: str | None = None

    @property
    def arrival(self) -> str:
        return self.location if self.destination is None else self.destination


class FakeResiduePackage:
    """Models Package.remove_flight: the walk goes blind, the roster clears."""

    def __init__(self) -> None:
        self.flights: list[FakeResidueFlight] = []

    def remove_flight(self, flight: FakeResidueFlight) -> None:
        self.flights.remove(flight)
        flight.roster.clear()


class FakeResidueFlight:
    def __init__(
        self, squadron: FakeResidueSquadron, package: FakeResiduePackage | None = None
    ) -> None:
        self.squadron = squadron
        self.coalition = squadron.coalition
        self.roster = FakeResidueRoster(2)
        self.alive = True
        if package is None:
            package = FakeResiduePackage()
            squadron.coalition.ato.packages.append(package)
        self.package = package
        package.flights.append(self)

    @property
    def arrival(self) -> str:
        return self.squadron.arrival


def _complete_and_remove(flight: FakeResidueFlight) -> None:
    """The sim's removal-loop shape (aircraftsimulation.on_game_tick): record,
    dismantle, drop the package when it empties."""
    record_completed_residue(flight)  # type: ignore[arg-type]
    flight.package.remove_flight(flight)
    if not flight.package.flights:
        flight.squadron.coalition.ato.remove_package(flight.package)


@pytest.fixture(autouse=True)
def _clean_residue_ledger() -> Iterator[None]:
    clear_completed_residue()
    yield
    clear_completed_residue()


def test_residue_ledger_carries_a_removed_solo_package_flight() -> None:
    settings = _settings()
    coalition = FakeResidueCoalition(settings)
    flight = FakeResidueFlight(FakeResidueSquadron(coalition, "Ramstein"))
    _complete_and_remove(flight)
    # The ATO walk is blind (the package is gone) and the flight is
    # dismantled; only the ledger can still park its jets.
    assert coalition.ato.packages == []
    assert flight.roster.cleared
    assert residue_flights_for(coalition.ato, settings) == [(flight, "Ramstein")]  # type: ignore[arg-type]


def test_residue_ledger_and_the_walk_stay_disjoint_with_a_sibling() -> None:
    settings = _settings()
    coalition = FakeResidueCoalition(settings)
    squadron = FakeResidueSquadron(coalition, "Ramstein")
    first = FakeResidueFlight(squadron)
    sibling = FakeResidueFlight(squadron, package=first.package)
    _complete_and_remove(first)
    # The sibling keeps the package walkable; the completed flight exists only
    # in the ledger -- one render path each, never both.
    assert first.package.flights == [sibling]
    assert coalition.ato.packages == [first.package]
    assert residue_flights_for(coalition.ato, settings) == [(first, "Ramstein")]  # type: ignore[arg-type]


def test_residue_ledger_gate_off_records_nothing() -> None:
    coalition = FakeResidueCoalition(_settings(on=False))
    flight = FakeResidueFlight(FakeResidueSquadron(coalition, "Ramstein"))
    _complete_and_remove(flight)
    assert residue_flights_for(coalition.ato, _settings()) == []  # type: ignore[arg-type]


def test_residue_ledger_gate_off_reads_nothing() -> None:
    settings = _settings()
    coalition = FakeResidueCoalition(settings)
    flight = FakeResidueFlight(FakeResidueSquadron(coalition, "Ramstein"))
    _complete_and_remove(flight)
    assert residue_flights_for(coalition.ato, _settings(on=False)) == []  # type: ignore[arg-type]


def test_residue_ledger_filters_by_coalition_ato() -> None:
    settings = _settings()
    own = FakeResidueCoalition(settings)
    other = FakeResidueCoalition(settings)
    flight = FakeResidueFlight(FakeResidueSquadron(own, "Ramstein"))
    _complete_and_remove(flight)
    assert residue_flights_for(other.ato, settings) == []  # type: ignore[arg-type]


def test_residue_ledger_freezes_arrival_at_completion() -> None:
    settings = _settings()
    coalition = FakeResidueCoalition(settings)
    squadron = FakeResidueSquadron(coalition, "Ramstein")
    flight = FakeResidueFlight(squadron)
    _complete_and_remove(flight)
    # A relocation order placed while the sim is paused moves the live
    # arrival; jets that already landed must not teleport with it.
    squadron.destination = "Spangdahlem"
    assert flight.arrival == "Spangdahlem"
    assert residue_flights_for(coalition.ato, settings) == [(flight, "Ramstein")]  # type: ignore[arg-type]


def test_residue_ledger_skips_a_dead_flight() -> None:
    settings = _settings()
    coalition = FakeResidueCoalition(settings)
    flight = FakeResidueFlight(FakeResidueSquadron(coalition, "Ramstein"))
    _complete_and_remove(flight)
    flight.alive = False
    assert residue_flights_for(coalition.ato, settings) == []  # type: ignore[arg-type]


def test_idle_spawn_count_debits_parked_residue() -> None:
    """The removal returns a completed flight's airframes to the untasked
    pool, so residue and idle filler would otherwise render the SAME jets
    twice (row B57 fail signature 2)."""
    assert idle_spawn_count(4, 2) == 2
    # No residue: the untasked pool spawns in full, as before the ledger.
    assert idle_spawn_count(4, 0) == 4
    # A squadron whose whole pool is residue spawns no filler, and an
    # over-count (parking declines, re-generation) never goes negative.
    assert idle_spawn_count(2, 2) == 0
    assert idle_spawn_count(2, 9) == 0


def test_residue_ledger_clears_for_a_new_sim_cycle() -> None:
    settings = _settings()
    coalition = FakeResidueCoalition(settings)
    flight = FakeResidueFlight(FakeResidueSquadron(coalition, "Ramstein"))
    _complete_and_remove(flight)
    clear_completed_residue()
    assert residue_flights_for(coalition.ato, settings) == []  # type: ignore[arg-type]


# --- P3: follow-on window and the pre-roll briefing block ---


def test_followon_window_matches_the_preroll_curve() -> None:
    assert followon_window_minutes(FakeCoalition(FakeGame(_settings(on=False), 3), [])) == 0  # type: ignore[arg-type]
    assert followon_window_minutes(FakeCoalition(FakeGame(_settings(), 0), [])) == 0  # type: ignore[arg-type]
    assert followon_window_minutes(FakeCoalition(FakeGame(_settings(), 3), [])) == 40  # type: ignore[arg-type]


class FakeBriefFlight:
    def __init__(self, state: object) -> None:
        self.state = state


class FakeBriefPackage:
    def __init__(self, states: list[object]) -> None:
        self.flights = [FakeBriefFlight(s) for s in states]


class FakeSide:
    def __init__(self, packages: list[FakeBriefPackage]) -> None:
        self.ato = FakeAto(packages)  # type: ignore[arg-type]


class Completed:
    """Named to match the real state class -- the brief matches by name."""

    in_flight = False


class Killed:
    """Named to match the real state class -- the brief matches by name."""

    in_flight = False


class FakeBriefGame:
    def __init__(
        self, settings: Settings, blue: list[object], red: list[object]
    ) -> None:
        self.settings = settings
        self.blue = FakeSide([FakeBriefPackage(blue)])
        self.red = FakeSide([FakeBriefPackage(red)])


def test_preroll_brief_lines_gate_off_and_quiet_world() -> None:
    quiet = [FakeGroundState(), FakeGroundState()]
    assert preroll_brief_lines(FakeBriefGame(_settings(on=False), quiet, quiet)) == []  # type: ignore[arg-type]
    assert preroll_brief_lines(FakeBriefGame(_settings(), quiet, quiet)) == []  # type: ignore[arg-type]


def test_preroll_brief_lines_counts_by_state() -> None:
    blue = [
        FakeInFlightState(True),
        FakeInFlightState(False),
        Completed(),
        Killed(),
        FakeGroundState(),
    ]
    red = [FakeInFlightState(True)]
    lines = preroll_brief_lines(FakeBriefGame(_settings(), blue, red))  # type: ignore[arg-type]
    assert lines == [
        "Friendly: airborne 2, recovered 1, lost 1.",
        "Enemy: airborne 1, recovered 0, lost 0 (assessed).",
    ]


def test_preroll_brief_lines_recovered_includes_the_ledger() -> None:
    # A flight the sim already removed is invisible to the ATO walk; the
    # recovered count must still see it through the residue ledger.
    settings = _settings()
    game = FakeBriefGame(settings, [], [])
    coalition = FakeResidueCoalition(settings)
    game.blue = coalition  # type: ignore[assignment]
    flight = FakeResidueFlight(FakeResidueSquadron(coalition, "Ramstein"))
    _complete_and_remove(flight)
    lines = preroll_brief_lines(game)  # type: ignore[arg-type]
    assert lines == ["Friendly: airborne 0, recovered 1, lost 0."]


# --- P5: reactive red ---


# Kept when the P4 voice-net block was removed (2026-08-18): the reactive-red
# tests below use this side double, and it was only ever defined up there.
class FakeSidePlayer:
    def __init__(self, is_blue: bool) -> None:
        self.is_blue = is_blue
        self.is_red = not is_blue


from game.fourteenth.living_battlespace import (  # noqa: E402
    REACTION_PACKAGE_PREFIX,
    plan_red_reactions,
)
from game.missiongenerator.reactiveredluadata import plan_reactive_red  # noqa: E402


def _reactive_settings(master: bool = True, reactive: bool = True) -> Settings:
    settings = _settings(on=master)
    settings.living_battlespace_reactive_red = reactive
    return settings


class FakeAirWing:
    def iter_squadrons(self) -> list[object]:
        return []


class FakeReactionCoalition:
    def __init__(self, settings: Settings, is_red: bool = True) -> None:
        self.game = FakeGame(settings, turn=3)
        self.player = FakeSidePlayer(is_blue=not is_red)
        self.air_wing = FakeAirWing()
        self.ato = FakeAto([])


def test_plan_red_reactions_gates() -> None:
    for coalition in (
        FakeReactionCoalition(_reactive_settings(master=False)),
        FakeReactionCoalition(_reactive_settings(reactive=False)),
        FakeReactionCoalition(_reactive_settings(), is_red=False),
        FakeReactionCoalition(_reactive_settings()),  # red, on, but no squadrons
    ):
        plan_red_reactions(coalition, NOW)  # type: ignore[arg-type]
        assert coalition.ato.packages == []


class FakeCaptured:
    def __init__(self, is_red: bool) -> None:
        self.is_red = is_red


class FakeCp:
    def __init__(self, is_red: bool) -> None:
        self.captured = FakeCaptured(is_red)


class FakeTgoUnit:
    def __init__(self, name: str, alive: bool = True) -> None:
        self.unit_name = name
        self.alive = alive


class FakeTgoGroup:
    def __init__(self, units: list[FakeTgoUnit]) -> None:
        self.units = units


class FakePos:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y


class FakeTgoTarget:
    def __init__(self, name: str, is_red: bool, units: list[FakeTgoUnit]) -> None:
        self.name = name
        self.control_point = FakeCp(is_red)
        self.position = FakePos(100.0, 200.0)
        self.groups = [FakeTgoGroup(units)]


class FakeBluePackage:
    def __init__(self, target: object) -> None:
        self.target = target


class FakeBlueAto:
    def __init__(self, packages: list[FakeBluePackage]) -> None:
        self.packages = packages


class FakeBlueSide:
    def __init__(self, packages: list[FakeBluePackage]) -> None:
        self.ato = FakeBlueAto(packages)


class FakeReactiveGame:
    def __init__(self, settings: Settings, packages: list[FakeBluePackage]) -> None:
        self.settings = settings
        self.blue = FakeBlueSide(packages)


class FakeReactionPackageRef:
    def __init__(self, custom_name: str) -> None:
        self.custom_name = custom_name


class FakeReactionFlightData:
    def __init__(self, is_red: bool, custom_name: str, group_name: str) -> None:
        self.friendly = FakeSidePlayer(is_blue=not is_red)
        # The marker lives on the PACKAGE (FlightData.custom_name is the
        # flight's own and is None for these flights) -- model the real shape.
        self.custom_name = None
        self.package = FakeReactionPackageRef(custom_name)
        self.group_name = group_name


class FakeReactiveMissionData:
    def __init__(self, flights: list[FakeReactionFlightData]) -> None:
        # The flat flights list, matching the real collection the emitter reads.
        self.flights = flights


def test_plan_reactive_red_positive_list() -> None:
    red_tgo = FakeTgoTarget("Haina SAM", True, [FakeTgoUnit("0044 | LN")])
    blue_tgo = FakeTgoTarget("Own depot", False, [FakeTgoUnit("0001 | X")])
    dead_tgo = FakeTgoTarget("Rubble", True, [FakeTgoUnit("0002 | Y", alive=False)])
    game = FakeReactiveGame(
        _reactive_settings(),
        [FakeBluePackage(t) for t in (red_tgo, blue_tgo, dead_tgo, red_tgo)],
    )
    data = FakeReactiveMissionData(
        [
            FakeReactionFlightData(True, f"{REACTION_PACKAGE_PREFIX} (IAP)", "R2"),
            FakeReactionFlightData(True, f"{REACTION_PACKAGE_PREFIX} (GIAP)", "R1"),
            FakeReactionFlightData(True, "Strike package", "S1"),
            FakeReactionFlightData(False, f"{REACTION_PACKAGE_PREFIX} (blue)", "B1"),
        ]
    )
    info = plan_reactive_red(game, data)  # type: ignore[arg-type]
    assert info is not None
    # Only the red TGO with alive units, once (deduped).
    assert [w.name for w in info.watched] == ["Haina SAM"]
    assert info.watched[0].unit_names == ["0044 | LN"]
    # Only red reaction packages, sorted.
    assert info.reaction_groups == ["R1", "R2"]


def test_plan_reactive_red_needs_both_halves() -> None:
    red_tgo = FakeTgoTarget("Haina SAM", True, [FakeTgoUnit("0044 | LN")])
    game = FakeReactiveGame(_reactive_settings(), [FakeBluePackage(red_tgo)])
    no_flights = FakeReactiveMissionData([])
    assert plan_reactive_red(game, no_flights) is None  # type: ignore[arg-type]

    flights = FakeReactiveMissionData(
        [FakeReactionFlightData(True, f"{REACTION_PACKAGE_PREFIX} (IAP)", "R1")]
    )
    no_targets = FakeReactiveGame(_reactive_settings(), [])
    assert plan_reactive_red(no_targets, flights) is None  # type: ignore[arg-type]

    gated = FakeReactiveGame(
        _reactive_settings(reactive=False), [FakeBluePackage(red_tgo)]
    )
    assert plan_reactive_red(gated, flights) is None  # type: ignore[arg-type]
