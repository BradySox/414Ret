"""The carrier deck is counted as it empties, and packages stay whole (§64).

Test 36 (2026-09-17): the ATO fragged 50 aircraft onto CVN-71; DCS placed 14,
then silently dropped every carrier group that activated after them. The first
fix capped the whole mission at the Supercarrier guide's 16 parking spots, which
air-started every flight after the first 16 however long the deck had been clear
(brady turn 3: 15 of 53 off the deck). Counted over time, a package that spawns
after the ones before it have launched parks too.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any

from game.ato.flightstate import Completed, WaitingForStart
from game.ato.starttype import StartType
from game.missiongenerator.aircraft.carrierdeck import (
    DECK_CLEARANCE,
    DECK_SPOTS,
    DECK_TOMCATS,
    DeckStay,
    deck_stay,
    overflow,
    package_deck_stays,
)
from game.settings import CarrierDeckPolicy, Settings

NOW = datetime(2026, 9, 18, 18, 0)
BOAT = "CVN-71 Theodore Roosevelt"


class _Fake:
    """Hashed by identity, as Flight and ControlPoint are."""

    def __init__(self, **fields: Any) -> None:
        self.__dict__.update(fields)


def _minutes(value: float) -> datetime:
    return NOW + timedelta(minutes=value)


def _stay(
    count: int,
    parks: float,
    takeoff: float,
    *,
    clients: int = 0,
    boat: str = BOAT,
    tomcat: bool = False,
) -> DeckStay:
    flight = _Fake(count=count, client_count=clients)
    return DeckStay(
        flight,  # type: ignore[arg-type]
        boat,  # type: ignore[arg-type]
        _minutes(parks),
        _minutes(takeoff) + DECK_CLEARANCE,
        count if tomcat else 0,
    )


def _airborne(*blocks: list[DeckStay]) -> list[Any]:
    """The flights of each block that start airborne, block by block."""
    result = overflow(blocks)
    return [[stay.flight in result for stay in block] for block in blocks]


def test_a_deck_that_has_emptied_takes_the_next_package() -> None:
    """The one-wave bug: 12 jets launched long ago no longer hold the deck."""
    first = [_stay(12, parks=0, takeoff=3)]
    later = [_stay(12, parks=20, takeoff=23)]
    assert _airborne(first, later) == [[False], [False]]


def test_the_deck_never_holds_more_than_sixteen_at_once() -> None:
    assert DECK_SPOTS == 16
    first = [_stay(12, parks=0, takeoff=3)]
    alongside = [_stay(6, parks=2, takeoff=5)]
    assert _airborne(first, alongside) == [[False], [True]]


def test_a_package_parks_whole_or_starts_airborne_whole() -> None:
    """Four more would fit, eight do not: both flights go, not one of them."""
    first = [_stay(10, parks=0, takeoff=3)]
    package = [_stay(4, parks=1, takeoff=4), _stay(4, parks=1, takeoff=4)]
    assert _airborne(first, package) == [[False], [True, True]]


def test_a_flight_keeps_its_spots_until_the_clearance_after_takeoff() -> None:
    clear = 3 + DECK_CLEARANCE.total_seconds() / 60
    full = [_stay(16, parks=0, takeoff=3)]
    assert _airborne(full, [_stay(2, parks=clear - 1, takeoff=clear + 2)]) == [
        [False],
        [True],
    ]
    assert _airborne(full, [_stay(2, parks=clear, takeoff=clear + 3)]) == [
        [False],
        [False],
    ]


def test_first_parked_is_first_served_whatever_the_package_order() -> None:
    early = [_stay(10, parks=0, takeoff=3)]
    late = [_stay(10, parks=2, takeoff=5)]
    assert _airborne(late, early) == [[True], [False]]


def test_a_player_flight_is_never_pushed_off_the_boat() -> None:
    """The briefing tells a human which deck to start on. The AI absorbs it,
    even an AI package that spawned first."""
    ai = [_stay(14, parks=0, takeoff=3)]
    player = [_stay(4, parks=1, takeoff=12, clients=1)]
    assert _airborne(ai, player) == [[True], [False]]


def test_a_players_own_package_parks_with_them() -> None:
    package = [_stay(2, parks=0, takeoff=12, clients=1), _stay(16, parks=0, takeoff=12)]
    assert _airborne(package) == [[False, False]]


def test_test_36s_opening_parks_two_tomcat_pairs_not_four() -> None:
    """Four Tomcat BARCAP pairs at once jammed test 36's deck. Hornets still park."""
    assert DECK_TOMCATS == 4
    pairs = [[_stay(2, parks=0, takeoff=3, tomcat=True)] for _ in range(4)]
    hornets = [_stay(2, parks=0, takeoff=3)]
    assert _airborne(*pairs, hornets) == [[False], [False], [True], [True], [False]]


def test_a_tomcat_pair_parks_once_the_earlier_tomcats_have_gone() -> None:
    first = [_stay(4, parks=0, takeoff=3, tomcat=True)]
    later = [_stay(2, parks=10, takeoff=13, tomcat=True)]
    assert _airborne(first, later) == [[False], [False]]


def test_each_boat_counts_its_own_deck() -> None:
    carrier = [_stay(16, parks=0, takeoff=3)]
    lha = [_stay(16, parks=0, takeoff=3, boat="LHA-1 Tarawa")]
    assert _airborne(carrier, lha) == [[False], [False]]


class _Waiting(WaitingForStart):
    def __init__(self, remaining: timedelta, spawn: StartType) -> None:
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


def _flight(
    *,
    start_in: float,
    takeoff: float,
    start_type: StartType = StartType.WARM,
    is_fleet: bool = True,
    count: int = 2,
    operational: bool = True,
    unit_id: str = "FA-18C_hornet",
) -> Any:
    state = _Waiting(timedelta(minutes=start_in), start_type)
    base = _Fake(
        is_fleet=is_fleet,
        dcs_airport=None,
        runway_is_operational=lambda: operational,
    )
    return _Fake(
        count=count,
        client_count=0,
        alive=True,
        state=state,
        start_type=start_type,
        unit_type=SimpleNamespace(dcs_unit_type=SimpleNamespace(id=unit_id)),
        departure=base,
        squadron=SimpleNamespace(location=base),
        flight_plan=SimpleNamespace(takeoff_time=lambda: _minutes(takeoff)),
    )


def _settings() -> Settings:
    settings = Settings()
    settings.carrier_deck_policy = CarrierDeckPolicy.LAST_RESORT
    return settings


def test_an_ai_carrier_flight_parks_at_its_activation_and_leaves_after_takeoff() -> (
    None
):
    flight = _flight(start_in=20, takeoff=22.5)
    stay = deck_stay(flight, NOW, _settings(), multiplayer=False)
    assert stay is not None
    assert stay.parks == _minutes(20)
    assert stay.leaves == _minutes(22.5) + DECK_CLEARANCE
    assert stay.tomcats == 0


def test_a_tomcat_flight_counts_its_tomcats() -> None:
    flight = _flight(start_in=0, takeoff=3, unit_id="F-14B")
    stay = deck_stay(flight, NOW, _settings(), multiplayer=False)
    assert stay is not None
    assert stay.tomcats == 2


def test_air_starts_and_airfield_flights_never_park_on_a_deck() -> None:
    airborne = _flight(start_in=5, takeoff=5, start_type=StartType.IN_FLIGHT)
    ashore = _flight(start_in=5, takeoff=8, is_fleet=False)
    assert deck_stay(airborne, NOW, _settings(), multiplayer=False) is None
    assert deck_stay(ashore, NOW, _settings(), multiplayer=False) is None


def test_only_flights_that_will_spawn_are_counted() -> None:
    live = _flight(start_in=0, takeoff=3)
    dead = _flight(start_in=0, takeoff=3)
    dead.alive = False
    done = _flight(start_in=0, takeoff=3)
    done.state = Completed.__new__(Completed)
    sunk = _flight(start_in=0, takeoff=3, operational=False)
    package = SimpleNamespace(flights=[live, dead, done, sunk])
    blocks = package_deck_stays([package], NOW, _settings(), multiplayer=False)  # type: ignore[list-item]
    assert [[stay.flight for stay in block] for block in blocks] == [[live]]
