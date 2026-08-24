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
#: barcap_overlap_time used by the carrier-BARCAP fixture below.
OVERLAP = timedelta(minutes=15)


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


def test_strike_is_still_spread_into_the_turn() -> None:
    # A normal strike keeps the spread-out start rather than launching at NOW.
    # The start is a 5 min base offset plus ±5 min uniform jitter, so a single
    # draw can legitimately land exactly on NOW when the jitter fully cancels the
    # base (clamped at 0). Asserting `> NOW` on one draw is therefore flaky;
    # assert on the distribution instead: the overwhelming majority of starts
    # fall strictly after NOW.
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
    settings = _FakeSettings(OVERLAP, max_carrier_simultaneous_barcaps=max_simultaneous)
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
    # same TOT, then queue the next batch behind them. The handover is pulled
    # `barcap_overlap_time` earlier, as on land: chaining raw station-departure left
    # a coverage hole between every naval round.
    tots = _schedule_carrier_barcaps(
        max_simultaneous, max_simultaneous + 1, monkeypatch
    )
    assert tots[:max_simultaneous] == [NOW] * max_simultaneous
    assert tots[max_simultaneous] == NOW + DURATION - OVERLAP


def test_living_battlespace_widens_the_spread_window() -> None:
    # §89 P3: with the gate on, the generic spread's window gains the
    # phase-aware follow-on tail, so some packages' TOTs land past the desired
    # mission length (the waves that launch as/after the player recovers).
    # 12 packages over 120+40 min put the last spread slot at ~147 min; the
    # ±5 min jitter cannot pull it back under 125.
    target = _LandTarget()
    packages = [_FakePackage(target, task=FlightType.STRIKE) for _ in range(12)]
    for package in packages:
        package.has_players = False  # type: ignore[attr-defined]
    settings = _FakeSettings(timedelta())
    settings.living_battlespace_preroll = True  # type: ignore[attr-defined]
    settings.living_battlespace_preroll_cap = 40  # type: ignore[attr-defined]
    coalition = _FakeCoalition(packages, settings)
    coalition.game.turn = 3  # type: ignore[attr-defined]
    ms.MissionScheduler(coalition, timedelta(minutes=120)).schedule_missions(NOW)  # type: ignore[arg-type]
    tots = [p.time_over_target for p in packages]
    assert all(t is not None for t in tots)
    assert max(t for t in tots if t is not None) > NOW + timedelta(minutes=125)


class _TransitTotEstimator:
    """earliest_tot is `now` plus the package's own transit to its target."""

    def __init__(self, package: object) -> None:
        self.package = package

    def earliest_tot(self, now: datetime) -> datetime:
        return now + getattr(self.package, "transit", timedelta())


def _schedule_transits(
    transits: list[timedelta],
    ceiling: timedelta,
    monkeypatch: pytest.MonkeyPatch,
) -> list[datetime]:
    """Spread-schedule one STRIKE per transit; return their TOTs in order."""
    monkeypatch.setattr(ms, "TotEstimator", _TransitTotEstimator)
    packages = []
    for transit in transits:
        package = _FakePackage(_LandTarget(), task=FlightType.STRIKE)
        package.transit = transit  # type: ignore[attr-defined]
        packages.append(package)
    coalition = _FakeCoalition(packages, _FakeSettings(timedelta()))
    ms.MissionScheduler(coalition, ceiling).schedule_missions(NOW)  # type: ignore[arg-type]
    tots = [p.time_over_target for p in packages]
    assert all(t is not None for t in tots)
    return tots  # type: ignore[return-value]


def test_a_long_transit_package_still_arrives_inside_the_cycle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The spread bounded the OFFSET by the cycle and then added transit on top,
    # so the tail of a long-transit ATO was timed past the end of the mission
    # and never serviced its target. 12 packages over 120 min put the last
    # offset near 120; a 40 min transit used to carry it to ~155.
    ceiling = timedelta(minutes=120)
    tots = _schedule_transits([timedelta(minutes=40)] * 12, ceiling, monkeypatch)
    assert max(tots) <= NOW + ceiling


def test_a_package_that_cannot_reach_the_cycle_launches_as_early_as_it_can(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # No offset can put a 150 min transit inside a 120 min cycle, so it takes
    # none at all rather than being delayed further still.
    transit = timedelta(minutes=150)
    tots = _schedule_transits([transit], timedelta(minutes=120), monkeypatch)
    assert tots[0] == NOW + transit


def test_over_long_packages_do_not_collapse_onto_one_arrival(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Pins the choice of scaling over clamping. Clamping to the ceiling would
    # give every package whose transit + offset overran it the SAME TOT, which
    # is the one arrival time the spread exists to stop packages sharing.
    # (Passes on the unpatched tree too -- it guards a later refactor, and is
    # not the evidence for the fix.)
    tots = _schedule_transits(
        [timedelta(minutes=60)] * 8, timedelta(minutes=120), monkeypatch
    )
    assert len(set(tots)) == len(tots)


def test_a_package_with_no_transit_keeps_the_full_spread(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The scaling is room-relative, so a package that is already over its target
    # spends the whole cycle exactly as before -- the fix must not squash the
    # spread for everyone to rescue its tail. (Also passes unpatched.)
    ceiling = timedelta(minutes=120)
    tots = _schedule_transits([timedelta()] * 12, ceiling, monkeypatch)
    assert max(tots) > NOW + timedelta(minutes=100)
    assert min(tots) < NOW + timedelta(minutes=20)
