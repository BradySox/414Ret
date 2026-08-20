from collections.abc import Iterator

from game.commander.tasks.primitive.antiship import PlanAntiShip
from game.commander.tasks.targetorder import shuffled_by_priority
from game.commander.theaterstate import TheaterState
from game.fourteenth.region_priorities import auto_planning_skips
from game.htn import CompoundTask, Method


class AttackShips(CompoundTask[TheaterState]):
    def each_valid_method(self, state: TheaterState) -> Iterator[Method[TheaterState]]:
        # state.enemy_ships is threat data as well as a target list, so the §93
        # gate belongs here rather than on the list itself.
        ships = [s for s in state.enemy_ships if not auto_planning_skips(s, state)]
        for ship in shuffled_by_priority(ships, state):
            yield [PlanAntiShip(ship)]
