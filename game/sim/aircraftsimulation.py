from __future__ import annotations

import itertools
import logging
from collections.abc import Iterator
from datetime import datetime, timedelta

from typing_extensions import TYPE_CHECKING

from game.ato.flightstate import Uninitialized, Completed, InCombat
from game.settings.settings import FastForwardStopCondition, CombatResolutionMethod
from .combat import CombatInitiator, FrozenCombat
from .simulationresults import SimulationResults

if TYPE_CHECKING:
    from game import Game
    from game.ato import Flight
    from .gameupdateevents import GameUpdateEvents


class AircraftSimulation:
    def __init__(self, game: Game) -> None:
        self.game = game
        self.combats: list[FrozenCombat] = []
        self.results = SimulationResults()

    def begin_simulation(self) -> None:
        self.reset()
        self.set_initial_flight_states()

    def on_game_tick(
        self,
        events: GameUpdateEvents,
        time: datetime,
        duration: timedelta,
        combat_resolution_method: CombatResolutionMethod,
        force_continue: bool,
    ) -> None:
        if any(
            self._combat_pauses_fast_forward(
                c, combat_resolution_method, force_continue
            )
            for c in self.combats
        ):
            logging.error(
                "Cannot resume simulation because aircraft are in combat and "
                "auto-resolve is disabled"
            )
            events.complete_simulation()
            return

        still_active = []
        for combat in self.combats:
            if combat.on_game_tick(
                time,
                duration,
                self.results,
                events,
                combat_resolution_method,
            ):
                events.end_combat(combat)
            else:
                still_active.append(combat)
        self.combats = still_active

        for flight in self.iter_flights():
            flight.on_game_tick(events, time, duration)

        # Check halts BEFORE creating new combats. Hot-spawn player flights are
        # InFlight here; if we wait until after CombatInitiator they will have
        # transitioned to InCombat and InFlight.should_halt_sim() never fires.
        for flight in self.iter_flights():
            if flight.should_halt_sim() and not force_continue:
                events.complete_simulation()
                return

        # Finish updating all flights before checking for combat so that the new
        # positions are used.
        CombatInitiator(self.game, self.combats, events).update_active_combats()

        # Implement FIRST_CONTACT: stop as soon as any combat exists. Without this,
        # hot-spawn flights with SKIP resolution loop forever — combat resolves with
        # no losses, both sides immediately re-engage, no other halt fires.
        if (
            self.game.settings.fast_forward_stop_condition
            == FastForwardStopCondition.FIRST_CONTACT
            and self.combats
        ):
            events.complete_simulation()
            return

        # Find completed flights, removing them from the ATO and returning aircraft
        # and pilots back to the squadron. Snapshot first: iter_flights() yields
        # lazily from the live package/ATO lists, and removing from those while
        # iterating skips the element after each removal.
        completed = [f for f in self.iter_flights() if isinstance(f.state, Completed)]
        for flight in completed:
            flight.package.remove_flight(flight)
            if len(flight.package.flights) == 0:
                flight.squadron.coalition.ato.remove_package(flight.package)

        if any(
            self._combat_pauses_fast_forward(
                c, combat_resolution_method, force_continue
            )
            for c in self.combats
        ):
            events.complete_simulation()

    def set_initial_flight_states(self) -> None:
        now = self.game.conditions.start_time
        for flight in self.iter_flights():
            flight.state.reinitialize(now)

    def reset(self) -> None:
        for flight in self.iter_flights():
            flight.set_state(Uninitialized(flight, self.game.settings))

    def iter_flights(self) -> Iterator[Flight]:
        packages = itertools.chain(
            self.game.blue.ato.packages, self.game.red.ato.packages
        )
        for package in packages:
            yield from package.flights

    def _auto_resolve_combat(
        self, combat_resolution_method: CombatResolutionMethod, force_continue: bool
    ) -> bool:
        if force_continue:
            return True
        return combat_resolution_method != CombatResolutionMethod.PAUSE

    @staticmethod
    def _combat_involves_player(combat: FrozenCombat) -> bool:
        return any(flight.client_count > 0 for flight in combat.iter_flights())

    def _combat_pauses_fast_forward(
        self,
        combat: FrozenCombat,
        combat_resolution_method: CombatResolutionMethod,
        force_continue: bool,
    ) -> bool:
        """Whether an active combat should stop the fast-forward.

        Normally any combat stops a PAUSE fast-forward so the player can fly it. But the
        PLAYER_AT_IP stop condition means "spawn me at my IP" -- an AI-only skirmish
        elsewhere must not strand the player short of it. So under PLAYER_AT_IP only a
        combat that actually involves a player flight pauses; AI-only combats keep
        ticking and auto-resolve (their freeze elapses and ``resolve`` runs normally).
        When combat already auto-resolves (RESOLVE/SKIP, or ``force_continue``) nothing
        pauses here regardless.
        """
        if self._auto_resolve_combat(combat_resolution_method, force_continue):
            return False
        if (
            self.game.settings.fast_forward_stop_condition
            is FastForwardStopCondition.PLAYER_AT_IP
            and not self._combat_involves_player(combat)
        ):
            return False
        return True
