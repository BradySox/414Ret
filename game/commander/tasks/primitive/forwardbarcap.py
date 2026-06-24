from __future__ import annotations

from dataclasses import dataclass

from game.ato.flighttype import FlightType
from game.commander.tasks.packageplanningtask import PackagePlanningTask
from game.commander.theaterstate import TheaterState
from game.theater import ForwardBarcapZone


@dataclass
class PlanForwardBarcap(PackagePlanningTask[ForwardBarcapZone]):
    """Plans the *added* forward-middle BARCAP screen (414th red forward-BARCAP
    layer). Mirrors ``PlanBarcap`` but targets a ``ForwardBarcapZone`` so the
    racetrack is laid forward-middle on the active front instead of at a rear CP.
    The rear/base BARCAP is unchanged and planned separately by ``PlanBarcap``.
    """

    max_orders: int

    def preconditions_met(self, state: TheaterState) -> bool:
        if not state.forward_barcaps_needed.get(self.target):
            return False
        return super().preconditions_met(state)

    def apply_effects(self, state: TheaterState) -> None:
        state.forward_barcaps_needed[self.target] -= 1
        super().apply_effects(state)

    def propose_flights(self) -> None:
        self.propose_flight(FlightType.BARCAP, self.get_flight_size())

    @property
    def purchase_multiplier(self) -> int:
        return self.max_orders
