"""Tests for same-boat carrier-recovery staggering (the flown midair fix).

DCS flies the whole carrier pattern itself, so arrival TIME is the only
deconfliction lever: two AI packages sent into the same recovery window
converge co-altitude in the DCS overhead (the 2026-07-16 Scenic Route midair).
The scheduler spaces same-boat landings by CARRIER_RECOVERY_INTERVAL, moving
only "spread" AI packages; player/CAP/AEW&C/SCAR/ASAP packages claim their
slots as fixed entries the movable ones space around.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

from game.ato.flighttype import FlightType
from game.commander.missionscheduler import (
    MissionScheduler,
    staggered_recovery_deltas,
)

T0 = datetime(2005, 4, 26, 23, 0)
DCA = {FlightType.BARCAP, FlightType.TARCAP}


class Cp:
    """A hashable stand-in for a control point (SimpleNamespace is not)."""

    def __init__(self, fleet: bool = True) -> None:
        self.is_fleet = fleet


class FakePlan:
    """Landing time derives live from the package TOT, like the real plans."""

    def __init__(self, flight: "FakeFlight", rtb_offset: timedelta) -> None:
        self.flight = flight
        self.rtb_offset = rtb_offset

    @property
    def landing_time(self) -> datetime:
        return self.flight.package.time_over_target + self.rtb_offset

    @landing_time.setter
    def landing_time(self, value: datetime) -> None:
        raise AssertionError("landing_time is derived; never assigned")


class FakeFlight:
    def __init__(
        self,
        package: "FakePackage",
        arrival: Cp,
        rtb_offset: timedelta = timedelta(minutes=30),
        helo: bool = False,
    ) -> None:
        self.package = package
        self.arrival = arrival
        self.is_helo = helo
        self.flight_plan = FakePlan(self, rtb_offset)


class FakePackage:
    def __init__(
        self,
        task: FlightType,
        tot: datetime,
        players: bool = False,
        asap: bool = False,
    ) -> None:
        self.primary_task = task
        self.time_over_target = tot
        self.has_players = players
        self.auto_asap = asap
        self.flights: list[FakeFlight] = []

    def recovering_at(self, cp: Cp, **kwargs: object) -> "FakePackage":
        self.flights.append(FakeFlight(self, cp, **kwargs))  # type: ignore[arg-type]
        return self


def _deconflict(packages: list[FakePackage]) -> None:
    coalition = SimpleNamespace(ato=SimpleNamespace(packages=packages))
    scheduler = MissionScheduler(coalition, timedelta(hours=1))  # type: ignore[arg-type]
    scheduler._deconflict_carrier_recoveries(DCA)


# --- the pure slotting helper ---


def test_slotting_spaces_same_boat_and_ignores_other_boats() -> None:
    boat, other = Cp(), Cp()
    entries = [
        (0, {boat: T0}, True),
        (1, {boat: T0 + timedelta(minutes=1)}, True),
        (2, {other: T0 + timedelta(minutes=2)}, True),
    ]
    deltas = staggered_recovery_deltas(entries, timedelta(minutes=5))  # type: ignore[arg-type]
    # Second same-boat package waits for the slot; the other boat is untouched.
    assert deltas == {1: timedelta(minutes=4)}


def test_fixed_entries_claim_slots_without_moving() -> None:
    boat = Cp()
    entries = [
        (0, {boat: T0}, False),  # a player package: never moved
        (1, {boat: T0 + timedelta(minutes=1)}, True),
    ]
    deltas = staggered_recovery_deltas(entries, timedelta(minutes=5))  # type: ignore[arg-type]
    assert 0 not in deltas
    assert deltas[1] == timedelta(minutes=4)


def test_multi_boat_package_clears_every_boat_it_recovers_at() -> None:
    a, b = Cp(), Cp()
    entries = [
        (0, {a: T0}, True),
        (1, {b: T0 + timedelta(minutes=1)}, True),
        (2, {a: T0 + timedelta(minutes=2), b: T0 + timedelta(minutes=3)}, True),
    ]
    deltas = staggered_recovery_deltas(entries, timedelta(minutes=5))  # type: ignore[arg-type]
    # Clearing boat a needs +3 min (lands a at T0+5); boat b then lands T0+6,
    # exactly one interval after the T0+1 arrival -- no further delay.
    assert deltas == {2: timedelta(minutes=3)}


# --- the scheduler wiring ---


def test_second_ai_package_is_delayed_and_landing_rederives() -> None:
    boat = Cp()
    p1 = FakePackage(FlightType.STRIKE, T0).recovering_at(boat)
    p2 = FakePackage(FlightType.BAI, T0 + timedelta(minutes=2)).recovering_at(boat)
    _deconflict([p1, p2])
    assert p1.time_over_target == T0  # first in keeps its slot
    landings = [
        p1.flights[0].flight_plan.landing_time,
        p2.flights[0].flight_plan.landing_time,
    ]
    assert landings[1] - landings[0] == timedelta(minutes=5)
    # The TOT moved by the same delta (the landing is TOT-derived).
    assert p2.time_over_target == T0 + timedelta(minutes=5)


def test_player_package_is_never_shifted_but_blocks_the_slot() -> None:
    boat = Cp()
    human = FakePackage(FlightType.STRIKE, T0, players=True).recovering_at(boat)
    ai = FakePackage(FlightType.STRIKE, T0 + timedelta(minutes=1)).recovering_at(boat)
    _deconflict([human, ai])
    assert human.time_over_target == T0
    assert ai.time_over_target == T0 + timedelta(minutes=5)


def test_cap_aewc_asap_and_recovery_are_fixed() -> None:
    boat = Cp()
    cap = FakePackage(FlightType.BARCAP, T0).recovering_at(boat)
    aewc = FakePackage(FlightType.AEWC, T0 + timedelta(minutes=1)).recovering_at(boat)
    asap = FakePackage(
        FlightType.STRIKE, T0 + timedelta(minutes=2), asap=True
    ).recovering_at(boat)
    tanker = FakePackage(FlightType.RECOVERY, T0 + timedelta(minutes=3)).recovering_at(
        boat
    )
    ai = FakePackage(FlightType.BAI, T0 + timedelta(minutes=4)).recovering_at(boat)
    _deconflict([cap, aewc, asap, tanker, ai])
    assert cap.time_over_target == T0
    assert aewc.time_over_target == T0 + timedelta(minutes=1)
    assert asap.time_over_target == T0 + timedelta(minutes=2)
    assert tanker.time_over_target == T0 + timedelta(minutes=3)
    # The AI package spaces past the latest CLAIMED slot (the ASAP landing at
    # T0+32; the recovery tanker never claims one -- it is timed off these
    # landings later): T0+2 + 5 = T0+7 TOT.
    assert ai.time_over_target == T0 + timedelta(minutes=7)


def test_helo_and_land_recoveries_are_ignored() -> None:
    boat, land = Cp(), Cp(fleet=False)
    helo = FakePackage(FlightType.STRIKE, T0).recovering_at(boat, helo=True)
    jet = FakePackage(FlightType.STRIKE, T0 + timedelta(minutes=1)).recovering_at(land)
    _deconflict([helo, jet])
    assert helo.time_over_target == T0
    assert jet.time_over_target == T0 + timedelta(minutes=1)
