from collections.abc import Iterator
from typing import Union

from game.commander.tasks.primitive.antiship import PlanAntiShip
from game.commander.tasks.primitive.dead import PlanDead
from game.commander.tasks.targetorder import shuffled_by_priority
from game.commander.theaterstate import TheaterState
from game.data.groups import GroupTask
from game.fourteenth.region_priorities import auto_planning_skips
from game.htn import CompoundTask, Method
from game.theater.theatergroundobject import IadsGroundObject, NavalGroundObject


class DegradeIads(CompoundTask[TheaterState]):
    def each_valid_method(self, state: TheaterState) -> Iterator[Method[TheaterState]]:
        # Reactive tier: SAMs actually threatening a planned target are serviced
        # in strict priority order -- never randomized, so a real threat response
        # is never deferred for the sake of variety.
        for air_defense in state.threatening_air_defenses:
            yield [self.plan_against(air_defense)]

        # §93: this tier PICKS a region to work on, so an IGNORED one is skipped.
        # The reactive tier above is deliberately not gated -- a SAM shooting at a
        # package flying elsewhere is a threat response, not a choice of target.
        prioritized_air_defenses = sorted(
            [
                tgo
                for tgo in state.enemy_air_defenses
                if tgo.task in [GroupTask.LORAD, GroupTask.MERAD]
                and not auto_planning_skips(tgo, state)
            ],
            key=lambda x: (state.priority_cp.distance_to(x) if state.priority_cp else 0)
            - x.max_threat_range().meters,
        )

        # Opportunistic tiers: which non-threatening SAM / detector to chip away
        # at is varied so red's offensive DEAD isn't identical every turn.
        for air_defense in shuffled_by_priority(prioritized_air_defenses, state):
            yield [self.plan_against(air_defense)]
        for detector in shuffled_by_priority(state.detecting_air_defenses, state):
            yield [self.plan_against(detector)]

    @staticmethod
    def plan_against(
        target: Union[IadsGroundObject, NavalGroundObject],
    ) -> Union[PlanDead, PlanAntiShip]:
        if isinstance(target, IadsGroundObject):
            return PlanDead(target)
        return PlanAntiShip(target)
