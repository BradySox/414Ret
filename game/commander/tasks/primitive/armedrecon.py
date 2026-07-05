from __future__ import annotations

from dataclasses import dataclass

from game.ato.flighttype import FlightType
from game.commander.tasks.packageplanningtask import PackagePlanningTask
from game.commander.theaterstate import TheaterState
from game.theater import ControlPoint


@dataclass
class PlanArmedRecon(PackagePlanningTask[ControlPoint]):
    def preconditions_met(self, state: TheaterState) -> bool:
        if self.target not in state.control_point_priority_queue:
            return False
        if not self.target_area_preconditions_met(state):
            return False
        return super().preconditions_met(state)

    def apply_effects(self, state: TheaterState) -> None:
        state.control_point_priority_queue.remove(self.target)
        super().apply_effects(state)

    #: Armed recon flies as a full 4-ship (414th call): a road/area sweep wants the
    #: numbers to cover the corridor, and it pairs with the auto-added recon drone +
    #: the (threat-gated) SEAD escort into a coherent hunter package. Fixed rather
    #: than the 2-4 flight-size roll so the sweep element is consistently substantial.
    ARMED_RECON_FLIGHT_SIZE = 4

    def propose_flights(self) -> None:
        self.propose_flight(FlightType.ARMED_RECON, self.ARMED_RECON_FLIGHT_SIZE)
        self.propose_common_escorts()
