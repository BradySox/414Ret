from __future__ import annotations

from dataclasses import dataclass

from game.ato.flighttype import FlightType
from game.commander.missionproposals import EscortType
from game.commander.tasks.packageplanningtask import PackagePlanningTask
from game.commander.theaterstate import TheaterState
from game.theater.theatergroundobject import IadsGroundObject


@dataclass
class PlanDead(PackagePlanningTask[IadsGroundObject]):
    def preconditions_met(self, state: TheaterState) -> bool:
        # Already found to be shielded behind a belt no DEAD can reach this turn.
        # Don't keep building (and reserving aircraft for) a package that can't
        # accomplish anything -- wait until the belt is actually cleared.
        if self.target in state.unreachable_air_defenses:
            return False
        if (
            self.target not in state.threatening_air_defenses
            and self.target not in state.detecting_air_defenses
        ):
            return False
        if not self.target_area_preconditions_met(state, ignore_iads=True):
            return False
        return super().preconditions_met(state)

    def apply_effects(self, state: TheaterState) -> None:
        # Only treat the SAM as destroyed (clearing the threat gate for strikes
        # that depend on it) if the DEAD can actually reach it. A SAM shielded
        # behind another live radar SAM would turn the DEAD around before it
        # employs, so clearing it here is what tasks strikers into a live belt.
        # Leave it threatening and record it so dependent strikes stay deferred
        # until real BDA confirms the kill on a later turn.
        dead_flights = (
            [f for f in self.package.flights if f.flight_type is FlightType.DEAD]
            if self.package
            else []
        )
        if state.dead_can_reach(self.target, dead_flights):
            state.eliminate_air_defense(self.target)
        else:
            state.unreachable_air_defenses.add(self.target)
        super().apply_effects(state)

    def propose_flights(self) -> None:
        tgt_count = self.target.alive_unit_count()
        self.propose_flight(FlightType.DEAD, min(4, (tgt_count // 2) + 1))

        # DEAD packages felt overstuffed when they requested all three SEAD flavors
        # at once. Keep the air-to-air escort, then choose one SEAD support style:
        # a dedicated SEAD flight for live radar SAMs, otherwise a SEAD escort that
        # can accompany the strikers if the route is threatened.
        self.propose_flight(FlightType.ESCORT, 2, EscortType.AirToAir)
        if self.target.has_live_radar_sam:
            self.propose_flight(FlightType.SEAD, 2, EscortType.Sead)
        else:
            self.propose_flight(FlightType.SEAD_ESCORT, 2, EscortType.Sead)
        if self.target.control_point.coalition.game.settings.autoplan_tankers_for_dead:
            self.propose_flight(FlightType.REFUELING, 1, EscortType.Refuel)
