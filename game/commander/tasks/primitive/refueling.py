from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from game.ato.flighttype import FlightType
from game.commander.tasks.packageplanningtask import PackagePlanningTask
from game.commander.theaterstate import RefuelingTarget, TheaterState
from game.dcs.aircrafttype import AirRefuelType
from game.theater import MissionTarget


@dataclass
class PlanRefueling(PackagePlanningTask[MissionTarget]):
    #: The boom/probe method this tanker must provide (None = unconstrained). Threaded
    #: into the tanker's ProposedFlight so a mixed fleet gets one tanker per method.
    method: Optional[AirRefuelType] = None

    def preconditions_met(self, state: TheaterState) -> bool:
        if (
            state.context.coalition.player.is_blue
            and not state.context.settings.auto_ato_behavior_tankers
        ):
            return False
        if not super().preconditions_met(state):
            return False
        return RefuelingTarget(self.target, self.method) in state.refueling_targets

    def apply_effects(self, state: TheaterState) -> None:
        state.refueling_targets.remove(RefuelingTarget(self.target, self.method))
        super().apply_effects(state)

    def propose_flights(self) -> None:
        self.propose_flight(FlightType.REFUELING, 1, refuel_method=self.method)
        self.propose_flight(FlightType.ESCORT, 2)
