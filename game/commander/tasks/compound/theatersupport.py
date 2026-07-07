from collections.abc import Iterator
from dataclasses import dataclass

from game.commander.tasks.compound.aewcsupport import PlanAewcSupport
from game.commander.tasks.compound.refuelingsupport import PlanRefuelingSupport
from game.commander.theaterstate import TheaterState
from game.htn import CompoundTask, Method


@dataclass(frozen=True)
class TheaterSupport(CompoundTask[TheaterState]):
    def each_valid_method(self, state: TheaterState) -> Iterator[Method[TheaterState]]:
        yield [PlanAewcSupport()]
        yield [PlanRefuelingSupport()]
        # Combat SAR is no longer a standing orbit auto-fragged here (2026-07-06
        # rework): the orbiting rescue helo never reliably flew the pickup
        # (commandeer-an-airborne-group, checklist G21). Rescue is now (a) a
        # player-plannable package off the FLOT (FrontLine.mission_types) and
        # (b) an on-demand AI rescue the combatsar runtime spawns when a pilot
        # goes down and no player package is up. See 414th-csar-notes.md.
