"""The carrier deck has a ceiling and generation has to respect it (§64).

Test 36 (2026-09-17): the ATO fragged 50 aircraft in 24 groups onto CVN-71.
Seventeen ever existed -- DCS placed 14, then silently dropped every carrier
group that activated afterwards. The Supercarrier Operations Guide (p100) gives
16 parking spots at mission start and says the overflow waits on the hangar
deck "until a suitable parking spot is free", which on a deck where nothing
taxis is never. The overflow air-starts instead, and it is AI that gets moved:
a human has to be able to slot in where the briefing says.
"""

from __future__ import annotations

from types import SimpleNamespace

from game.missiongenerator.aircraft.flightgroupspawner import (
    CARRIER_DECK_SPAWN_SPOTS,
    FlightGroupSpawner,
)


def _spawner(
    deck_use: dict[str, int], *, count: int, clients: int = 0
) -> FlightGroupSpawner:
    spawner = FlightGroupSpawner.__new__(FlightGroupSpawner)
    spawner.flight = SimpleNamespace(count=count, client_count=clients)  # type: ignore[assignment]
    spawner.carrier_deck_use = deck_use
    return spawner


_BOAT = SimpleNamespace(name="CVN-71 Theodore Roosevelt")


def test_the_deck_fills_to_the_guides_sixteen_spots() -> None:
    assert CARRIER_DECK_SPAWN_SPOTS == 16
    deck = {_BOAT.name: CARRIER_DECK_SPAWN_SPOTS - 2}
    assert not _spawner(deck, count=2)._carrier_deck_is_full(_BOAT)  # type: ignore[arg-type]
    assert _spawner(deck, count=3)._carrier_deck_is_full(_BOAT)  # type: ignore[arg-type]


def test_an_empty_deck_takes_anything_that_fits() -> None:
    assert not _spawner({}, count=4)._carrier_deck_is_full(_BOAT)  # type: ignore[arg-type]
    assert _spawner({}, count=CARRIER_DECK_SPAWN_SPOTS + 1)._carrier_deck_is_full(_BOAT)  # type: ignore[arg-type]


def test_a_client_flight_is_never_pushed_off_the_boat() -> None:
    """The briefing tells a human which deck to start on; moving them to an air
    start is worse than the hangar wait. The AI behind them absorbs it."""
    deck = {_BOAT.name: CARRIER_DECK_SPAWN_SPOTS}
    assert not _spawner(deck, count=2, clients=2)._carrier_deck_is_full(_BOAT)  # type: ignore[arg-type]
    assert _spawner(deck, count=2)._carrier_deck_is_full(_BOAT)  # type: ignore[arg-type]


def test_each_boat_counts_its_own_deck() -> None:
    lha = SimpleNamespace(name="LHA-1 Tarawa")
    deck = {_BOAT.name: CARRIER_DECK_SPAWN_SPOTS}
    assert _spawner(deck, count=2)._carrier_deck_is_full(_BOAT)  # type: ignore[arg-type]
    assert not _spawner(deck, count=2)._carrier_deck_is_full(lha)  # type: ignore[arg-type]
