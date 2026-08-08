from __future__ import annotations

from dataclasses import dataclass

from game.ato.flighttype import FlightType
from game.commander.tasks.packageplanningtask import PackagePlanningTask
from game.commander.theaterstate import TheaterState
from game.theater import ControlPoint


@dataclass
class PlanAirAssault(PackagePlanningTask[ControlPoint]):
    def preconditions_met(self, state: TheaterState) -> bool:
        if self.target not in state.vulnerable_control_points or self.target.is_fleet:
            return False
        if not self.target_area_preconditions_met(state):
            return False
        return super().preconditions_met(state)

    def apply_effects(self, state: TheaterState) -> None:
        state.vulnerable_control_points.remove(self.target)
        super().apply_effects(state)

    def propose_flights(self) -> None:
        self.propose_flight(FlightType.AIR_ASSAULT, self.get_flight_size())
        # No escort jammer (§77). preconditions_met already requires the objective
        # to be clear of radar-SAM threat rings, so the assault never penetrates
        # one -- and §77's model only pays off as the jammer closes on a live SAM.
        # A jammer fragged here also spent a scarce airframe and the per-side cap
        # on a package that could not use it: on Afghanistan turn 1 both of blue's
        # Growler sections went to CH-47 assaults, joining ~15 min behind the
        # helos at 21,000 ft and splitting for home on the same second as the
        # drop, while seven DEAD packages flew into live rings with none.
        self.propose_common_escorts(jammer=False)
