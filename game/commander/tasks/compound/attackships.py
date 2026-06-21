from collections.abc import Iterator

from game.commander.tasks.primitive.antiship import PlanAntiShip
from game.commander.tasks.targetorder import shuffled_by_priority
from game.commander.theaterstate import TheaterState
from game.htn import CompoundTask, Method


class AttackShips(CompoundTask[TheaterState]):
    def each_valid_method(self, state: TheaterState) -> Iterator[Method[TheaterState]]:
        for ship in shuffled_by_priority(state.enemy_ships, state):
            yield [PlanAntiShip(ship)]
