"""§89 living battlespace P1: phase curve, player pinning, launch-flow trigger."""

from __future__ import annotations

from datetime import datetime, timedelta

from game.fourteenth.living_battlespace import (
    auto_preroll_stop_needed,
    pin_player_packages,
    preroll_minutes,
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
