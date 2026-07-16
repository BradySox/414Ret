"""Unit tests for BARCAP wave scheduling in MissionScheduler.

These exercise the overlapping-wave logic for land control points without
standing up a full Game/Coalition by faking the minimal surface the scheduler
touches and stubbing TotEstimator.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

import game.commander.missionscheduler as ms
from game.ato.flighttype import FlightType

NOW = datetime(2020, 1, 1, 0, 0, 0)
DURATION = timedelta(minutes=60)


class _FakeFlightPlan:
    def __init__(self, patrol_duration: timedelta) -> None:
        self.patrol_duration = patrol_duration
        self.landing_time = NOW + patrol_duration


class _FakeDeparture:
    is_fleet = False


class _FakeFlight:
    def __init__(self, patrol_duration: timedelta) -> None:
        self.flight_plan = _FakeFlightPlan(patrol_duration)
        self.departure = _FakeDeparture()
        # Land recovery: the carrier-recovery stagger pass skips this flight.
        self.arrival = _FakeDeparture()
        self.is_helo = False


class _LandTarget:
    """A non-naval mission target (BARCAP over a land control point)."""


class _FakePackage:
    def __init__(
        self,
        target: object,
        duration: timedelta = DURATION,
        task: FlightType = FlightType.BARCAP,
    ) -> None:
        self.primary_task = task
        self.auto_asap = False
        self.target = target
        self._duration = duration
        self.flights = [_FakeFlight(duration)]
        self.time_over_target: datetime | None = None

    @property
    def mission_departure_time(self) -> datetime:
        assert self.time_over_target is not None
        return self.time_over_target + self._duration


class _FakeSettings:
    def __init__(
        self,
        overlap: timedelta,
        max_carrier_simultaneous_barcaps: int = 2,
        max_simultaneous_recovery_tankers: int = 2,
    ) -> None:
        self.barcap_overlap_time = overlap
        self.desired_barcap_mission_duration = DURATION
        self.desired_tanker_on_station_time = timedelta(minutes=60)
        self.max_carrier_simultaneous_barcaps = max_carrier_simultaneous_barcaps
        self.max_simultaneous_recovery_tankers = max_simultaneous_recovery_tankers


class _FakeGame:
    def __init__(self, settings: _FakeSettings) -> None:
        self.settings = settings


class _FakeAto:
    def __init__(self, packages: list[_FakePackage]) -> None:
        self.packages = packages


class _FakeCoalition:
    def __init__(self, packages: list[_FakePackage], settings: _FakeSettings) -> None:
        self.ato = _FakeAto(packages)
        self.game = _FakeGame(settings)


class _StubTotEstimator:
    """earliest_tot is always `now` (CAP launches from the defended base)."""

    def __init__(self, package: _FakePackage) -> None:
        self.package = package

    def earliest_tot(self, now: datetime) -> datetime:
        return now


def _schedule(overlap: timedelta, rounds: int) -> list[datetime]:
    target = _LandTarget()
    packages = [_FakePackage(target) for _ in range(rounds)]
    coalition = _FakeCoalition(packages, _FakeSettings(overlap))
    scheduler = ms.MissionScheduler(coalition, timedelta(minutes=120))  # type: ignore[arg-type]
    scheduler.schedule_missions(NOW)
    tots = [p.time_over_target for p in packages]
    assert all(t is not None for t in tots)
    return tots  # type: ignore[return-value]


@pytest.fixture(autouse=True)
def _stub_tot_estimator(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ms, "TotEstimator", _StubTotEstimator)


def test_overlapping_waves_are_spaced_by_duration_minus_overlap() -> None:
    overlap = timedelta(minutes=15)
    tots = _schedule(overlap, rounds=3)

    interval = DURATION - overlap  # 45 minutes of fresh coverage per wave
    assert tots[1] - tots[0] == interval
    assert tots[2] - tots[1] == interval


def test_first_wave_is_jittered_but_bounded() -> None:
    overlap = timedelta(minutes=15)
    # Run several times; the first wave should always land within the jitter
    # ceiling (min(overlap, 5 min)) after the earliest possible TOT (== NOW).
    ceiling = min(overlap, timedelta(minutes=5))
    for _ in range(50):
        first = _schedule(overlap, rounds=1)[0]
        assert NOW <= first <= NOW + ceiling


def test_zero_overlap_reproduces_legacy_back_to_back_schedule() -> None:
    tots = _schedule(timedelta(0), rounds=3)
    # No jitter, and waves chained exactly end-to-end (spacing == duration).
    assert tots[0] == NOW
    assert tots[1] - tots[0] == DURATION
    assert tots[2] - tots[1] == DURATION


def _schedule_one(task: FlightType) -> datetime:
    pkg = _FakePackage(_LandTarget(), task=task)
    coalition = _FakeCoalition([pkg], _FakeSettings(timedelta(minutes=15)))
    ms.MissionScheduler(coalition, timedelta(minutes=120)).schedule_missions(NOW)  # type: ignore[arg-type]
    assert pkg.time_over_target is not None
    return pkg.time_over_target


def test_scar_is_scheduled_asap() -> None:
    # A Sandy rescue escort must be tasked as early as the flight can reach the
    # area (stub earliest_tot == NOW), not spread across the turn like other
    # strike packages.
    assert _schedule_one(FlightType.SCAR) == NOW


def test_strike_is_still_spread_into_the_turn() -> None:
    # Contrast: a normal strike keeps the spread-out start, unlike SCAR which is
    # pinned to NOW. The start is a 5 min base offset plus ±5 min uniform
    # jitter, so a single draw can legitimately land exactly on NOW when the
    # jitter fully cancels the base (clamped at 0). Asserting `> NOW` on one draw
    # is therefore flaky; assert on the distribution instead: the overwhelming
    # majority of starts fall strictly after NOW, which never happens for the
    # always-NOW SCAR case above.
    samples = [_schedule_one(FlightType.STRIKE) for _ in range(200)]
    after_now = [t for t in samples if t > NOW]
    assert len(after_now) >= 0.9 * len(samples)


class _NavalTarget:
    """A naval mission target (BARCAP over a carrier)."""


def _schedule_carrier_barcaps(
    max_simultaneous: int, rounds: int, monkeypatch: pytest.MonkeyPatch
) -> list[datetime]:
    # The carrier branch is gated on isinstance(target, NavalControlPoint); swap in
    # our lightweight stand-in so we don't have to build a real carrier control point.
    monkeypatch.setattr(ms, "NavalControlPoint", _NavalTarget)
    target = _NavalTarget()
    packages = [_FakePackage(target) for _ in range(rounds)]
    settings = _FakeSettings(
        timedelta(minutes=15), max_carrier_simultaneous_barcaps=max_simultaneous
    )
    coalition = _FakeCoalition(packages, settings)
    ms.MissionScheduler(coalition, timedelta(minutes=120)).schedule_missions(NOW)  # type: ignore[arg-type]
    tots = [p.time_over_target for p in packages]
    assert all(t is not None for t in tots)
    return tots  # type: ignore[return-value]


@pytest.mark.parametrize("max_simultaneous", [1, 2, 3])
def test_carrier_barcaps_stack_up_to_the_configured_limit(
    max_simultaneous: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Carriers stack up to `max_carrier_simultaneous_barcaps` waves on-station at the
    # same TOT, then queue the next batch to launch after the prior one recovers (one
    # mission duration later). With the stubbed earliest_tot == NOW, the first batch
    # all share NOW and the wave after the limit is pushed out by DURATION.
    tots = _schedule_carrier_barcaps(
        max_simultaneous, max_simultaneous + 1, monkeypatch
    )
    assert tots[:max_simultaneous] == [NOW] * max_simultaneous
    assert tots[max_simultaneous] == NOW + DURATION
