"""Which carrier flights park on the deck and which start airborne (§64).

The deck is counted as it empties: a flight holds its spots from the moment it
spawns until DECK_CLEARANCE after its planned takeoff. Counting the whole mission
against the ceiling air-started every flight after the first 16, however long the
deck had been clear. See retlab-features.md §64.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, TYPE_CHECKING

from game.ato.flightstate import Completed
from game.ato.starttype import StartType
from game.missiongenerator.aircraft.waypoints.waypointgenerator import (
    SpawnTiming,
    is_tomcat,
)

if TYPE_CHECKING:
    from game.ato import Flight, Package
    from game.settings import Settings
    from game.theater import ControlPoint

#: The Supercarrier guide's 16 parking starts (p100; its other 4 spawn points are
#: the catapults). Past them DCS hangar-decks a spawn until a spot frees, and on
#: test 36's jammed deck 33 jets never appeared at all.
DECK_SPOTS = 16

#: Tomcats parked at once. Test 36 parked 8 in two seconds and 12 in three minutes,
#: and 3 ever launched; tests 9 and 32 never parked more than 4, and all launched.
DECK_TOMCATS = 4

#: How long past its planned takeoff a flight keeps its spots. Test 32 had six AI
#: Hornets off the deck inside four minutes of spawning.
DECK_CLEARANCE = timedelta(minutes=5)


@dataclass(frozen=True)
class DeckStay:
    """One flight's time on a boat's deck, from spawning to clearing its spots."""

    flight: Flight
    boat: ControlPoint
    parks: datetime
    leaves: datetime
    tomcats: int = 0

    def on_deck_at(self, moment: datetime) -> bool:
        return self.parks <= moment < self.leaves


def deck_stay(
    flight: Flight, now: datetime, settings: Settings, multiplayer: bool
) -> Optional[DeckStay]:
    """When `flight` is parked on its boat's deck, or None if it never is."""
    if not flight.departure.is_fleet:
        return None
    if flight.state.spawn_type is StartType.IN_FLIGHT:
        return None
    parks = now + SpawnTiming(flight, now, settings, multiplayer).spawn_delay()
    leaves = max(parks, flight.flight_plan.takeoff_time()) + DECK_CLEARANCE
    tomcats = flight.count if is_tomcat(flight) else 0
    return DeckStay(flight, flight.departure, parks, leaves, tomcats)


def package_deck_stays(
    packages: Iterable[Package], now: datetime, settings: Settings, multiplayer: bool
) -> list[list[DeckStay]]:
    """Each package's deck stays, one list per boat it launches from."""
    blocks: list[list[DeckStay]] = []
    for package in packages:
        by_boat: dict[ControlPoint, list[DeckStay]] = {}
        for flight in package.flights:
            # The flights AircraftGenerator.generate_flights will actually spawn.
            if not flight.alive or isinstance(flight.state, Completed):
                continue
            if not flight.squadron.location.runway_is_operational():
                continue
            stay = deck_stay(flight, now, settings, multiplayer)
            if stay is not None:
                by_boat.setdefault(stay.boat, []).append(stay)
        blocks.extend(by_boat.values())
    return blocks


def _fits(parked: list[DeckStay], block: list[DeckStay]) -> bool:
    """True when the deck stays within both limits while `block` is on it."""
    together = parked + block
    for moment in {stay.parks for stay in together}:
        if not any(stay.on_deck_at(moment) for stay in block):
            continue
        aboard = [stay for stay in together if stay.on_deck_at(moment)]
        if sum(stay.flight.count for stay in aboard) > DECK_SPOTS:
            return False
        if sum(stay.tomcats for stay in aboard) > DECK_TOMCATS:
            return False
    return True


def overflow(blocks: Iterable[list[DeckStay]]) -> set[Flight]:
    """The flights that start airborne because the deck is full while they would park.

    A package's flights on one boat park together or start airborne together, so no
    package launches half off the deck. Player flights always park; everything else
    is first parked, first served.
    """
    ordered = sorted(
        blocks,
        key=lambda block: (
            not any(stay.flight.client_count for stay in block),
            min(stay.parks for stay in block),
        ),
    )
    parked: dict[ControlPoint, list[DeckStay]] = defaultdict(list)
    airborne: set[Flight] = set()
    for block in ordered:
        deck = parked[block[0].boat]
        players = any(stay.flight.client_count for stay in block)
        if players or _fits(deck, block):
            deck.extend(block)
        else:
            airborne.update(stay.flight for stay in block)
    return airborne


def carrier_overflow(
    packages: Iterable[Package], now: datetime, settings: Settings, multiplayer: bool
) -> set[Flight]:
    return overflow(package_deck_stays(packages, now, settings, multiplayer))
