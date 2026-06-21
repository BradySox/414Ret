from collections.abc import Iterator
from dataclasses import dataclass

from game.commander.tasks.primitive.oca import PlanOcaStrike
from game.commander.tasks.targetorder import shuffled_by_priority
from game.commander.theaterstate import TheaterState
from game.htn import CompoundTask, Method


@dataclass(frozen=True)
class AttackAirInfrastructure(CompoundTask[TheaterState]):
    aircraft_cold_start: bool

    def each_valid_method(self, state: TheaterState) -> Iterator[Method[TheaterState]]:
        for battle_position in shuffled_by_priority(state.oca_targets, state):
            yield [PlanOcaStrike(battle_position, self.aircraft_cold_start)]
