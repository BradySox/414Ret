from __future__ import annotations

from dataclasses import dataclass

from game.ato.flighttype import FlightType
from game.commander.tasks.packageplanningtask import PackagePlanningTask
from game.commander.theaterstate import TheaterState
from game.theater import MissionTarget


@dataclass
class PlanCombatSar(PackagePlanningTask[MissionTarget]):
    """Auto-plan a Combat SAR (pilot-rescue) standing orbit near a front.

    414th feature. Only fires for the player coalition when Settings.auto_combat_sar
    is on (combat_sar_targets is empty otherwise), so the default-off behaviour is a
    pure no-op. The in-mission MOOSE CSAR engine (resources/plugins/combatsar) does
    the actual rescue; this just keeps a CH-47 orbiting so coverage exists with no
    player CSAR up.
    """

    def preconditions_met(self, state: TheaterState) -> bool:
        if not state.context.settings.auto_combat_sar:
            return False
        if not super().preconditions_met(state):
            return False
        return self.target in state.combat_sar_targets

    def apply_effects(self, state: TheaterState) -> None:
        state.combat_sar_targets.remove(self.target)
        super().apply_effects(state)

    def propose_flights(self) -> None:
        self.propose_flight(FlightType.COMBAT_SAR, 1)

    @property
    def asap(self) -> bool:
        # A standing rescue alert should be airborne early, before the first losses.
        return True
