from collections.abc import Iterator

from game.commander.tasks.primitive.armedrecon import PlanArmedRecon
from game.commander.tasks.primitive.bai import PlanBai
from game.commander.tasks.targetorder import shuffled_by_priority
from game.commander.theaterstate import TheaterState
from game.htn import CompoundTask, Method


class AttackBattlePositions(CompoundTask[TheaterState]):
    def each_valid_method(self, state: TheaterState) -> Iterator[Method[TheaterState]]:
        battle_positions = [
            battle_position
            for group in state.enemy_battle_positions.values()
            for battle_position in group.in_priority_order
        ]
        for battle_position in shuffled_by_priority(battle_positions, state):
            yield [PlanBai(battle_position)]
        # Only plan against the 2 most important CPs
        for cp in state.control_point_priority_queue[:2]:
            if not cp.is_fleet:
                yield [PlanArmedRecon(cp)]
