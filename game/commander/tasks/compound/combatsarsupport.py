from collections.abc import Iterator

from game.commander.tasks.primitive.combatsar import PlanCombatSar
from game.commander.theaterstate import TheaterState
from game.htn import CompoundTask, Method


class PlanCombatSarSupport(CompoundTask[TheaterState]):
    def each_valid_method(self, state: TheaterState) -> Iterator[Method[TheaterState]]:
        for target in state.combat_sar_targets:
            yield [PlanCombatSar(target)]
