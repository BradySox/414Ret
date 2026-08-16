"""§89 living battlespace: P1 (curve, pinning, launch trigger) and P2
(expended stores, mid-air AI fuel, recovery residue gating)."""

from __future__ import annotations

from datetime import datetime, timedelta

from game.ato.flighttype import FlightType
from game.data.weapons import WeaponType
from game.fourteenth.living_battlespace import (
    auto_preroll_stop_needed,
    followon_window_minutes,
    pin_player_packages,
    preroll_brief_lines,
    preroll_minutes,
    recovery_residue_enabled,
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


# --- P4: the voice-net schedule ---

from game.missiongenerator.battlespacenetluadata import (  # noqa: E402
    BattlespaceNetInfo,
    build_net_schedule,
    phoneticize,
    plan_battlespace_net,
)


def _voice_settings(master: bool = True, voice: bool = True) -> Settings:
    settings = _settings(on=master)
    settings.living_battlespace_voice_net = voice
    return settings


class FakeSidePlayer:
    def __init__(self, is_blue: bool) -> None:
        self.is_blue = is_blue
        self.is_red = not is_blue


class FakeFreq:
    def __init__(self, hertz: int) -> None:
        self.hertz = hertz


class FakeAwacs:
    def __init__(self, is_blue: bool = True, callsign: str = "Magic31-1") -> None:
        self.blue = FakeSidePlayer(is_blue)
        self.freq = FakeFreq(251_000_000)
        self.callsign = callsign


class FakeNetPackage:
    def __init__(self, tot: datetime, departure: datetime) -> None:
        self.time_over_target = tot
        self.mission_departure_time = departure


class FakeNetFlightData:
    def __init__(
        self,
        task: FlightType,
        delay_min: float,
        tot_min: float,
        depart_min: float,
        client: bool = False,
        callsign: str = "Dodge41",
    ) -> None:
        self.friendly = FakeSidePlayer(True)
        self.client_units = ["someone"] if client else []
        self.callsign = callsign
        self.group_name = f"{callsign} grp"
        self.flight_type = task
        self.departure_delay = timedelta(minutes=delay_min)
        self.package = FakeNetPackage(
            NOW + timedelta(minutes=tot_min), NOW + timedelta(minutes=depart_min)
        )


class FakeNetMissionData:
    def __init__(
        self, flights: list[FakeNetFlightData], awacs: list[FakeAwacs]
    ) -> None:
        self.awacs = awacs
        # The emitters read the flat flights list (never .packages, which
        # generate_flights clears per coalition).
        self.flights = flights


def test_phoneticize() -> None:
    assert phoneticize("Dodge41") == "Dodge 4 1"
    assert phoneticize("Colt 1-1") == "Colt 1 1"
    assert phoneticize("Uzi") == "Uzi"


def test_voice_net_gates_and_awacs_requirement() -> None:
    flight = FakeNetFlightData(FlightType.STRIKE, 30, 60, 90)
    data = FakeNetMissionData([flight], [FakeAwacs()])
    assert build_net_schedule(FakeGame(_voice_settings(master=False), 3), data, NOW) == []  # type: ignore[arg-type]
    assert build_net_schedule(FakeGame(_voice_settings(voice=False), 3), data, NOW) == []  # type: ignore[arg-type]
    red_only = FakeNetMissionData([flight], [FakeAwacs(is_blue=False)])
    assert build_net_schedule(FakeGame(_voice_settings(), 3), red_only, NOW) == []  # type: ignore[arg-type]


def test_voice_net_schedule_for_a_strike_package() -> None:
    flight = FakeNetFlightData(FlightType.STRIKE, 30, 60, 90)
    data = FakeNetMissionData([flight], [FakeAwacs()])
    calls = build_net_schedule(FakeGame(_voice_settings(), 3), data, NOW)  # type: ignore[arg-type]
    assert [(c.t, c.text) for c in calls] == [
        (30 * 60 + 60, "Magic, Dodge 4 1, airborne as fragged."),
        (60 * 60 - 300, "Dodge 4 1, pushing."),
        (90 * 60 + 60, "Dodge 4 1, off station, RTB."),
    ]
    assert all(c.freq_mhz == 251.0 for c in calls)
    assert all(c.group_name == "Dodge41 grp" for c in calls)


def test_voice_net_station_task_and_player_skip() -> None:
    cap = FakeNetFlightData(FlightType.BARCAP, 1, 40, 80, callsign="Uzi11")
    player = FakeNetFlightData(FlightType.STRIKE, 30, 60, 90, client=True)
    data = FakeNetMissionData([cap, player], [FakeAwacs()])
    calls = build_net_schedule(FakeGame(_voice_settings(), 3), data, NOW)  # type: ignore[arg-type]
    texts = [c.text for c in calls]
    # Short delay -> no check-in; BARCAP -> on-station, no push; player -> nothing.
    assert texts == ["Uzi 1 1, on station.", "Uzi 1 1, off station, RTB."]


def test_voice_net_rate_limit() -> None:
    flights = [
        FakeNetFlightData(FlightType.BARCAP, 1, 40, 80, callsign=f"Cap{i}")
        for i in range(3)
    ]
    data = FakeNetMissionData(flights, [FakeAwacs()])
    calls = build_net_schedule(FakeGame(_voice_settings(), 3), data, NOW)  # type: ignore[arg-type]
    # Three identical timelines collapse to one call per moment under the gap.
    times = [c.t for c in calls]
    assert times == sorted(times)
    assert all(b - a >= 20 for a, b in zip(times, times[1:]))


class FakeMapResource:
    def __init__(self) -> None:
        self.added: list[str] = []

    def add_resource_file(self, path: object) -> str:
        self.added.append(str(path))
        return "ResKey"


class FakeMission:
    def __init__(self) -> None:
        self.map_resource = FakeMapResource()


def test_plan_embeds_synthesized_clips() -> None:
    flight = FakeNetFlightData(FlightType.STRIKE, 30, 60, 90)
    data = FakeNetMissionData([flight], [FakeAwacs()])
    mission = FakeMission()

    def fake_synth(calls: list[object], out_dir: object) -> bool:
        from pathlib import Path

        for index in range(len(calls)):
            (Path(str(out_dir)) / f"bsnet_{index:03d}.wav").write_bytes(b"RIFFdata")
        return True

    info = plan_battlespace_net(
        FakeGame(_voice_settings(), 3), mission, data, NOW, synthesize=fake_synth  # type: ignore[arg-type]
    )
    assert isinstance(info, BattlespaceNetInfo)
    assert [c.filename for c in info.calls] == [
        "l10n/DEFAULT/bsnet_000.wav",
        "l10n/DEFAULT/bsnet_001.wav",
        "l10n/DEFAULT/bsnet_002.wav",
    ]
    assert len(mission.map_resource.added) == 3


def test_plan_drops_the_net_when_synthesis_fails() -> None:
    flight = FakeNetFlightData(FlightType.STRIKE, 30, 60, 90)
    data = FakeNetMissionData([flight], [FakeAwacs()])
    info = plan_battlespace_net(
        FakeGame(_voice_settings(), 3),  # type: ignore[arg-type]
        FakeMission(),  # type: ignore[arg-type]
        data,  # type: ignore[arg-type]
        NOW,
        synthesize=lambda calls, out_dir: False,
    )
    assert info is None


# --- P5: reactive red ---

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
