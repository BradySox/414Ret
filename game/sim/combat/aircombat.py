from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from shapely.ops import unary_union

from game.ato.flightstate import InCombat, InFlight
from game.settings.settings import CombatResolutionMethod
from game.utils import dcs_to_shapely_point
from .capability import (
    air_combat_survivor_loss_chance,
    air_combat_win_probability,
    air_to_air_strength,
)
from .joinablecombat import JoinableCombat
from .. import GameUpdateEvents

if TYPE_CHECKING:
    from game.ato import Flight
    from ..simulationresults import SimulationResults


class AirCombat(JoinableCombat):
    def __init__(self, freeze_duration: timedelta, flights: list[Flight]) -> None:
        super().__init__(freeze_duration, flights)
        footprints = []
        for flight in self.flights:
            if (region := flight.state.a2a_commit_region()) is not None:
                footprints.append(region)
        self.footprint = unary_union(footprints)

    def joinable_by(self, flight: Flight) -> bool:
        if not flight.state.will_join_air_combat:
            return False

        if not isinstance(flight.state, InFlight):
            raise NotImplementedError(
                f"Only InFlight flights are expected to join air combat. {flight} is "
                "not InFlight"
            )

        if self.footprint.intersects(
            dcs_to_shapely_point(flight.state.estimate_position())
        ):
            return True
        return False

    def __str__(self) -> str:
        blue_flights = []
        red_flights = []
        for flight in self.flights:
            if flight.squadron.player.is_blue:
                blue_flights.append(str(flight))
            else:
                red_flights.append(str(flight))

        blue = ", ".join(blue_flights)
        red = ", ".join(red_flights)
        return f"air combat {blue} vs {red}"

    def because(self) -> str:
        return f"of {self}"

    def describe(self) -> str:
        return f"in air-to-air combat"

    def resolve(
        self,
        results: SimulationResults,
        events: GameUpdateEvents,
        time: datetime,
        elapsed_time: timedelta,
        resolution_method: CombatResolutionMethod,
    ) -> None:

        if resolution_method is CombatResolutionMethod.SKIP:
            for flight in self.flights:
                assert isinstance(flight.state, InCombat)
                flight.state.exit_combat(events, time, elapsed_time)
            return

        blue = []
        red = []
        for flight in self.flights:
            if flight.squadron.player.is_blue:
                blue.append(flight)
            else:
                red.append(flight)

        # Capability-weighted odds (not a numbers-only coin flip): each side's strength
        # is capability x count, so a modern jet is no longer doomed by a coin toss but
        # numbers still tell. See game/sim/combat/capability.py.
        blue_strength = sum(air_to_air_strength(f) for f in blue)
        red_strength = sum(air_to_air_strength(f) for f in red)
        if random.random() < air_combat_win_probability(blue_strength, red_strength):
            winner, loser = blue, red
            winner_strength, loser_strength = blue_strength, red_strength
        else:
            winner, loser = red, blue
            winner_strength, loser_strength = red_strength, blue_strength

        if winner == blue:
            logging.debug(f"{self} auto-resolved as blue victory")
        else:
            logging.debug(f"{self} auto-resolved as red victory")

        for flight in loser:
            flight.kill(results, events)

        # A lopsided winner bleeds few survivors; an even fight still costs ~half.
        survivor_loss = air_combat_survivor_loss_chance(winner_strength, loser_strength)
        for flight in winner:
            assert isinstance(flight.state, InCombat)
            if random.random() < survivor_loss:
                flight.kill(results, events)
            else:
                flight.state.exit_combat(events, time, elapsed_time)
