from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from game.ato.flighttype import FlightType
from game.commander.tasks.packageplanningtask import PackagePlanningTask
from game.commander.theaterstate import TheaterState
from game.theater import MissionTarget

if TYPE_CHECKING:
    from game.dcs.aircrafttype import AircraftType


@dataclass
class PlanCombatSar(PackagePlanningTask[MissionTarget]):
    """Auto-plan a Combat SAR (pilot-rescue) standing orbit near a front.

    414th feature. Only fires for the player coalition when Settings.auto_combat_sar
    is on (combat_sar_targets is empty otherwise), so the default-off behaviour is a
    pure no-op. The in-mission MOOSE CSAR engine (resources/plugins/combatsar) does
    the actual rescue; this keeps the rescue package on station so coverage exists
    with no player CSAR up. Per the rescue rework it fields the standing alert
    (COMBAT_SAR rescue/King) **plus a Sandy (SCAR) escort** so the AI can suppress
    the threats around a downed pilot -- not just orbit.
    """

    #: A C-130 "King" airframe the coalition owns, resolved by PlanCombatSarSupport.
    #: When set, the package fields a dedicated King (C-130 on-scene commander)
    #: alongside the rescue helo. None -> no King flight (e.g. no C-130 owned).
    king_aircraft: Optional[AircraftType] = None

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
        # A dedicated C-130 "King" on-scene commander when the coalition owns one
        # (PlanCombatSarSupport resolves it), pinned to that airframe so it can't
        # collapse into a second rescue helo.
        if self.king_aircraft is not None:
            self.propose_flight(
                FlightType.COMBAT_SAR, 1, preferred_type=self.king_aircraft
            )
        # Rescue-rework safety net: a Sandy (SCAR) escort alongside the standing
        # rescue alert so the AI protects the survivor, not just orbits. Degrades
        # gracefully when no A-10/Apache is free (the fulfiller simply skips it).
        self.propose_flight(FlightType.SCAR, 1)

    @property
    def asap(self) -> bool:
        # A standing rescue alert should be airborne early, before the first losses.
        return True
