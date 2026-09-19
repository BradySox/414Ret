"""Carrier deck spawn policy + MP slot timing (feature §64).

DCS offers no mission-level control over deck parking beyond spawn timing: the
mission-start spawn wave fills the six-pack (which sits in the taxi lane to the
bow catapults) first, and a group activated even one second later is placed
elsewhere on deck (dcs_liberation#1309). These tests pin the generator's use of
that lever:

* AI carrier ground starts always spawn >= 1s late (never in the six-pack).
* Player carrier flights take the same placement delay under the last-resort
  deck policy, and keep the six-pack under SIXPACK_FIRST.
* A TOT-delayed player carrier flight is no longer late-activated for its full
  delay (which removed its slots from the MP slot list until the push time):
  it spawns uncontrolled like its airfield counterpart, with only the
  one-second placement activation, and the StartCommand holds the AI members
  to the planned push.
* Single player ignores "Spawn player flights immediately": with fewer than
  two player slots in the mission (the same predicate that assigns Player
  rather than Client skill) there is no slot list to keep selectable, so the
  lone player flight is delayed to its planned start time — and a delayed
  cold player flight late-activates (materializing at its planned startup
  time) instead of sitting uncontrolled in the pit from mission start.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any

from game.ato.flightstate import WaitingForStart
from game.ato.starttype import StartType
from game.missiongenerator.aircraft.waypoints.waypointgenerator import (
    WaypointGenerator,
)
from game.settings import CarrierDeckPolicy, Settings


class FakeWaiting(WaitingForStart):
    """WaitingForStart stand-in that skips the real constructor."""

    def __init__(self, remaining: timedelta, spawn: StartType = StartType.COLD) -> None:
        self._remaining = remaining
        self._spawn = spawn

    def time_remaining(self, time: datetime) -> timedelta:
        return self._remaining

    @property
    def spawn_type(self) -> StartType:
        return self._spawn

    @property
    def in_flight(self) -> bool:
        return False


class FakeGroundState:
    """A mission-start pre-flight state (StartUp/Taxi), not WaitingForStart."""

    in_flight = False

    def __init__(self, spawn: StartType = StartType.COLD) -> None:
        self.spawn_type = spawn


class FakeGroup:
    def __init__(self) -> None:
        self.id = 42
        self.tasks: list[Any] = []
        self.late_activation = False
        self.uncontrolled = False

    def add_trigger_action(self, task: Any) -> None:
        self.tasks.append(task)


def make_flight(
    *,
    client_count: int,
    is_fleet: bool,
    state: Any,
    start_type: StartType = StartType.COLD,
) -> Any:
    return SimpleNamespace(
        client_count=client_count,
        state=state,
        start_type=start_type,
        departure=SimpleNamespace(is_fleet=is_fleet, dcs_airport=None),
        flight_plan=SimpleNamespace(takeoff_time=lambda: None),
    )


def run_set_takeoff_time(
    flight: Any, settings: Settings, multiplayer: bool = True
) -> tuple[FakeGroup, Any]:
    group = FakeGroup()
    mission = SimpleNamespace(triggerrules=SimpleNamespace(triggers=[]))
    generator = WaypointGenerator(
        flight,
        group,  # type: ignore[arg-type]
        mission,  # type: ignore[arg-type]
        datetime(2026, 7, 16, 12, 0),
        settings,
        None,  # type: ignore[arg-type]
        multiplayer,
    )
    generator.set_takeoff_time(SimpleNamespace(tot=None))  # type: ignore[arg-type]
    return group, mission


def activation_delays(mission: Any) -> list[int]:
    return [
        trigger.rules[0].seconds
        for trigger in mission.triggerrules.triggers
        if trigger.comment.startswith("FlightLateActivationTrigger")
    ]


def startup_delays(mission: Any) -> list[int]:
    return [
        trigger.rules[0].seconds
        for trigger in mission.triggerrules.triggers
        if trigger.comment.startswith("FlightStartTrigger")
    ]


def settings_with(policy: CarrierDeckPolicy, never_delay: bool = True) -> Settings:
    settings = Settings()
    settings.carrier_deck_policy = policy
    settings.never_delay_player_flights = never_delay
    return settings


def test_ai_carrier_ground_start_spawns_off_the_sixpack() -> None:
    flight = make_flight(client_count=0, is_fleet=True, state=FakeGroundState())
    group, mission = run_set_takeoff_time(
        flight, settings_with(CarrierDeckPolicy.SIXPACK_FIRST)
    )
    assert group.late_activation
    assert activation_delays(mission) == [1]
    assert startup_delays(mission) == []


def test_ai_carrier_flight_with_zero_hold_still_spawns_late() -> None:
    # WaitingForStart(0) previously produced a TimeAfter(0) activation, which
    # joins the mission-start deck fill; the placement delay now floors it.
    flight = make_flight(client_count=0, is_fleet=True, state=FakeWaiting(timedelta()))
    _, mission = run_set_takeoff_time(
        flight, settings_with(CarrierDeckPolicy.LAST_RESORT)
    )
    assert activation_delays(mission) == [1]


def test_ai_carrier_flight_activates_at_its_push_time() -> None:
    flight = make_flight(
        client_count=0, is_fleet=True, state=FakeWaiting(timedelta(minutes=20))
    )
    _, mission = run_set_takeoff_time(
        flight, settings_with(CarrierDeckPolicy.LAST_RESORT)
    )
    assert activation_delays(mission) == [1200]


def test_client_carrier_last_resort_spawns_off_the_sixpack() -> None:
    flight = make_flight(client_count=2, is_fleet=True, state=FakeGroundState())
    group, mission = run_set_takeoff_time(
        flight, settings_with(CarrierDeckPolicy.LAST_RESORT)
    )
    assert group.late_activation
    assert not group.uncontrolled
    assert activation_delays(mission) == [1]


def test_client_carrier_sixpack_first_joins_the_mission_start_fill() -> None:
    flight = make_flight(client_count=2, is_fleet=True, state=FakeGroundState())
    group, mission = run_set_takeoff_time(
        flight, settings_with(CarrierDeckPolicy.SIXPACK_FIRST)
    )
    assert not group.late_activation
    assert mission.triggerrules.triggers == []


def test_delayed_client_carrier_flight_keeps_its_slots() -> None:
    # The MP fix: previously late-activated for the full 45 minutes, so the
    # client slots did not exist until the push time. Now it spawns at ~1s
    # (uncontrolled, off the six-pack) and only the AI members hold for the
    # StartCommand.
    flight = make_flight(
        client_count=2, is_fleet=True, state=FakeWaiting(timedelta(minutes=45))
    )
    group, mission = run_set_takeoff_time(
        flight, settings_with(CarrierDeckPolicy.LAST_RESORT, never_delay=False)
    )
    assert group.uncontrolled
    assert group.late_activation
    assert startup_delays(mission) == [2700]
    assert activation_delays(mission) == [1]


def test_delayed_client_carrier_flight_sixpack_first_spawns_at_start() -> None:
    flight = make_flight(
        client_count=2, is_fleet=True, state=FakeWaiting(timedelta(minutes=45))
    )
    group, mission = run_set_takeoff_time(
        flight, settings_with(CarrierDeckPolicy.SIXPACK_FIRST, never_delay=False)
    )
    assert group.uncontrolled
    assert not group.late_activation
    assert startup_delays(mission) == [2700]
    assert activation_delays(mission) == []


def test_delayed_warm_client_carrier_flight_still_activates_late() -> None:
    # A hot jet cannot wait uncontrolled without burning gas; warm starts keep
    # the full-delay late activation (same as airfields).
    flight = make_flight(
        client_count=2,
        is_fleet=True,
        state=FakeWaiting(timedelta(minutes=45), spawn=StartType.WARM),
        start_type=StartType.WARM,
    )
    group, mission = run_set_takeoff_time(
        flight, settings_with(CarrierDeckPolicy.LAST_RESORT, never_delay=False)
    )
    assert not group.uncontrolled
    assert activation_delays(mission) == [2700]


def test_airfield_flights_are_untouched() -> None:
    # Delayed client airfield flight: uncontrolled at t=0, no activation
    # trigger (there is no six-pack to avoid).
    flight = make_flight(
        client_count=2, is_fleet=False, state=FakeWaiting(timedelta(minutes=45))
    )
    group, mission = run_set_takeoff_time(
        flight, settings_with(CarrierDeckPolicy.LAST_RESORT, never_delay=False)
    )
    assert group.uncontrolled
    assert not group.late_activation
    assert activation_delays(mission) == []

    # Mission-start AI airfield flight: no triggers at all.
    flight = make_flight(client_count=0, is_fleet=False, state=FakeGroundState())
    group, mission = run_set_takeoff_time(
        flight, settings_with(CarrierDeckPolicy.LAST_RESORT)
    )
    assert not group.late_activation
    assert mission.triggerrules.triggers == []


def test_runway_start_never_takes_the_placement_delay() -> None:
    flight = make_flight(
        client_count=2,
        is_fleet=True,
        state=FakeGroundState(spawn=StartType.RUNWAY),
        start_type=StartType.RUNWAY,
    )
    group, mission = run_set_takeoff_time(
        flight, settings_with(CarrierDeckPolicy.LAST_RESORT)
    )
    assert not group.late_activation
    assert mission.triggerrules.triggers == []


def test_multiplayer_client_flight_spawns_immediately_with_the_setting_on() -> None:
    # The MP behavior the setting exists for: two or more player slots in the
    # mission keep every slot selectable from mission start.
    flight = make_flight(
        client_count=2, is_fleet=False, state=FakeWaiting(timedelta(minutes=45))
    )
    group, mission = run_set_takeoff_time(
        flight, settings_with(CarrierDeckPolicy.LAST_RESORT), multiplayer=True
    )
    assert not group.late_activation
    assert not group.uncontrolled
    assert mission.triggerrules.triggers == []


def test_single_player_cold_flight_activates_at_its_planned_startup_time() -> None:
    # Fewer than two player slots: never_delay_player_flights is ignored and
    # the lone cold flight late-activates at its planned startup time rather
    # than idling in the pit from mission start.
    flight = make_flight(
        client_count=1, is_fleet=False, state=FakeWaiting(timedelta(minutes=45))
    )
    group, mission = run_set_takeoff_time(
        flight, settings_with(CarrierDeckPolicy.LAST_RESORT), multiplayer=False
    )
    assert group.late_activation
    assert not group.uncontrolled
    assert activation_delays(mission) == [2700]
    assert startup_delays(mission) == []


def test_single_player_warm_flight_activates_at_its_planned_taxi_time() -> None:
    flight = make_flight(
        client_count=1,
        is_fleet=False,
        state=FakeWaiting(timedelta(minutes=45), spawn=StartType.WARM),
        start_type=StartType.WARM,
    )
    group, mission = run_set_takeoff_time(
        flight, settings_with(CarrierDeckPolicy.LAST_RESORT), multiplayer=False
    )
    assert group.late_activation
    assert not group.uncontrolled
    assert activation_delays(mission) == [2700]


def test_single_player_runway_flight_activates_at_its_takeoff_time() -> None:
    flight = make_flight(
        client_count=1,
        is_fleet=False,
        state=FakeWaiting(timedelta(minutes=20), spawn=StartType.RUNWAY),
        start_type=StartType.RUNWAY,
    )
    group, mission = run_set_takeoff_time(
        flight, settings_with(CarrierDeckPolicy.LAST_RESORT), multiplayer=False
    )
    assert group.late_activation
    assert activation_delays(mission) == [1200]


def test_single_player_short_delay_still_spawns_at_mission_start() -> None:
    # The ten-minute rule survives the single-player bypass: a short hold is
    # not worth a delayed spawn.
    flight = make_flight(
        client_count=1, is_fleet=False, state=FakeWaiting(timedelta(minutes=5))
    )
    group, mission = run_set_takeoff_time(
        flight, settings_with(CarrierDeckPolicy.LAST_RESORT), multiplayer=False
    )
    assert not group.late_activation
    assert not group.uncontrolled
    assert mission.triggerrules.triggers == []


def test_single_player_cold_carrier_flight_activates_late_and_off_sixpack() -> None:
    # Late activation subsumes the one-second placement delay: the flight
    # materializes at its planned startup time, clear of the six-pack.
    flight = make_flight(
        client_count=1, is_fleet=True, state=FakeWaiting(timedelta(minutes=45))
    )
    group, mission = run_set_takeoff_time(
        flight, settings_with(CarrierDeckPolicy.LAST_RESORT), multiplayer=False
    )
    assert group.late_activation
    assert not group.uncontrolled
    assert activation_delays(mission) == [2700]


def test_single_player_ai_flights_keep_the_normal_delay_paths() -> None:
    # AI flights are unaffected by the single-player bypass: a delayed cold
    # AI airfield flight still spawns uncontrolled with a StartCommand hold.
    flight = make_flight(
        client_count=0, is_fleet=False, state=FakeWaiting(timedelta(minutes=45))
    )
    group, mission = run_set_takeoff_time(
        flight, settings_with(CarrierDeckPolicy.LAST_RESORT), multiplayer=False
    )
    assert group.uncontrolled
    assert not group.late_activation
    assert startup_delays(mission) == [2700]
