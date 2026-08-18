from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from game.ato.flighttype import FlightType
from game.commander.tasks.packageplanningtask import PackagePlanningTask
from game.commander.theaterstate import TheaterState
from game.dcs.aircrafttype import AirRefuelType
from game.theater import MissionTarget


@dataclass
class PlanRefueling(PackagePlanningTask[MissionTarget]):
    #: The refuelling methods this coalition's aircraft need, most-needed first.
    #: Filled from the coalition before the flights are proposed.
    needed_refuel_methods: list[AirRefuelType] = field(init=False, default_factory=list)

    def preconditions_met(self, state: TheaterState) -> bool:
        if (
            state.context.coalition.player.is_blue
            and not state.context.settings.auto_ato_behavior_tankers
        ):
            return False
        self.needed_refuel_methods = self._methods_the_wing_needs(state)
        if not super().preconditions_met(state):
            return False
        return self.target in state.refueling_targets

    @staticmethod
    def _methods_the_wing_needs(state: TheaterState) -> list[AirRefuelType]:
        """Boom, probe or both, ordered by how many squadrons take each.

        A theater tanker is only useful to aircraft whose receptacle it fits, and
        the two are physically incompatible, so a wing flying both needs one of
        each. Ordered so the method most of the wing uses gets the tanker that is
        planned first, and therefore the better squadron.
        """
        demand: Counter[AirRefuelType] = Counter()
        for squadron in state.context.coalition.air_wing.iter_squadrons():
            method = squadron.aircraft.air_refuel_type
            if method is not None:
                demand[method] += 1
        return [method for method, _ in demand.most_common()]

    def apply_effects(self, state: TheaterState) -> None:
        state.refueling_targets.remove(self.target)
        super().apply_effects(state)

    def propose_flights(self) -> None:
        # The first tanker is deliberately left unconstrained, so a coalition whose
        # aircraft declare no refuelling method -- or whose only tanker declares
        # none -- plans exactly what it planned before this existed.
        self.propose_flight(FlightType.REFUELING, 1)
        # One more per further method. Optional, because a wing that flies probe
        # receivers without owning a drogue tanker should still get the boom tanker
        # it can field rather than losing the package.
        for method in self.needed_refuel_methods[1:]:
            self.propose_flight(
                FlightType.REFUELING,
                1,
                optional=True,
                refuel_methods=frozenset({method}),
            )
        self.propose_flight(FlightType.ESCORT, 2)
