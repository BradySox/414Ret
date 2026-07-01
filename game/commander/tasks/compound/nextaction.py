from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import ClassVar

from game.commander.tasks.compound.attackairinfrastructure import (
    AttackAirInfrastructure,
)
from game.commander.tasks.compound.attackbattlepositions import AttackBattlePositions
from game.commander.tasks.compound.attackbuildings import AttackBuildings
from game.commander.tasks.compound.attackships import AttackShips
from game.commander.tasks.compound.capturebases import CaptureBases
from game.commander.tasks.compound.defendbases import DefendBases
from game.commander.tasks.compound.degradeiads import DegradeIads
from game.commander.tasks.compound.frontlinecas import PlanFrontLineCas
from game.commander.tasks.compound.interdictreinforcements import (
    InterdictReinforcements,
)
from game.commander.tasks.compound.protectairspace import ProtectAirSpace
from game.commander.tasks.compound.recoverysupport import RecoverySupport
from game.commander.tasks.compound.theatersupport import TheaterSupport
from game.commander.theaterstate import TheaterState
from game.htn import CompoundTask, Method, Task


@dataclass(frozen=True)
class PlanNextAction(CompoundTask[TheaterState]):
    aircraft_cold_start: bool

    def each_valid_method(self, state: TheaterState) -> Iterator[Method[TheaterState]]:
        # Reactive/support methods keep their fixed lead order regardless of any
        # campaign phase (the §17 boundary: reactive defense stays deterministic).
        yield [TheaterSupport()]
        yield [ProtectAirSpace()]
        yield [DefendBases()]
        # The offensive tail is where the campaign phase (W3) applies its soft
        # emphasis: the active phase reorders these methods, which shifts which
        # objectives get first claim on the limited offensive aircraft. No phase
        # (setting off, red coalition, or pre-phase save) yields the stock order.
        for name in self._offensive_order(state):
            yield [self._OFFENSIVE_FACTORIES[name](self)]
        yield [RecoverySupport()]  # for recovery tankers

    # PlanNextAction's offensive methods by class name, in stock priority order.
    # The name-keyed indirection exists for the campaign-phase emphasis
    # (game/fourteenth/phases.py keeps orderings as names so it never imports the
    # commander); a test locks the two modules in sync.
    _OFFENSIVE_FACTORIES: ClassVar[
        dict[str, Callable[["PlanNextAction"], Task[TheaterState]]]
    ] = {
        "InterdictReinforcements": lambda self: InterdictReinforcements(),
        "AttackBattlePositions": lambda self: AttackBattlePositions(),
        "CaptureBases": lambda self: CaptureBases(),
        # CAS decoupled from the capture/ground-stance decision: plan CAS on any
        # front still contested after CaptureBases (incl. fronts where we're
        # winning the ground war and only set an aggressive stance). Runs after
        # CaptureBases so losing fronts keep first claim on the CAS/escort jets.
        "PlanFrontLineCas": lambda self: PlanFrontLineCas(),
        "AttackAirInfrastructure": lambda self: AttackAirInfrastructure(
            self.aircraft_cold_start
        ),
        "AttackBuildings": lambda self: AttackBuildings(),
        "AttackShips": lambda self: AttackShips(),
        "DegradeIads": lambda self: DegradeIads(),
    }

    def _offensive_order(self, state: TheaterState) -> list[str]:
        """The offensive method order for this planning run.

        The phase is the *campaign's* (BLUE-perspective) arc — "roll back the enemy
        IADS" describes blue's intent — so only the blue commander is emphasized;
        red keeps the stock order (a red arc is deferred).
        """
        stock = list(self._OFFENSIVE_FACTORIES)
        coalition = state.context.coalition
        if not coalition.player.is_blue:
            return stock
        from game.fourteenth.phases import active_phase

        phase = active_phase(coalition.game)
        if phase is None or not phase.emphasis:
            return stock
        # Guard against a stale/authored emphasis naming an unknown method, and
        # against one omitting a method: unknown names are dropped, missing ones
        # keep their stock relative order at the tail.
        order = [name for name in phase.emphasis if name in self._OFFENSIVE_FACTORIES]
        order.extend(name for name in stock if name not in order)
        return order
