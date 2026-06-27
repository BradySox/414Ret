from __future__ import annotations

from dataclasses import dataclass

from game.ato.flighttype import FlightType
from game.commander.tasks.packageplanningtask import PackagePlanningTask
from game.commander.theaterstate import TheaterState
from game.theater.theatergroundobject import VehicleGroupGroundObject


@dataclass
class PlanScar(PackagePlanningTask[VehicleGroupGroundObject]):
    """Frag a player-flyable SCAR hunt against an enemy armor concentration.

    The companion to BAI: where BAI is the AI's anti-armor strike, SCAR turns the
    same kind of target into a moving-HVT discrimination hunt for a human. The
    SCAR ground picture (HVT + decoys + clutter + threat) is composed at mission
    generation from this package's target (``build_scar_taskings``); here we only
    place the package. Gated/selected by ``PlanScarHunts`` so this stays a thin,
    BAI-shaped proposal.

    Like ``PlanBai``, a SCAR hunt **consumes** its battle position: the precondition
    skips an already-claimed group and the effect eliminates it, so the planner
    spreads SCAR across *different* armor concentrations instead of stacking package
    after package on the single top-priority target.
    """

    def preconditions_met(self, state: TheaterState) -> bool:
        if not state.has_battle_position(self.target):
            return False
        return super().preconditions_met(state)

    def apply_effects(self, state: TheaterState) -> None:
        state.eliminate_battle_position(self.target)
        state.scar_hunts_planned += 1
        super().apply_effects(state)

    def propose_flights(self) -> None:
        self.propose_flight(FlightType.SCAR, self.get_flight_size())
        self.propose_common_escorts()
