from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

from game.ato.flighttype import FlightType
from game.commander.tasks.packageplanningtask import PackagePlanningTask
from game.commander.theaterstate import TheaterState
from game.theater import MissionTarget

if TYPE_CHECKING:
    from game.dcs.aircrafttype import AircraftType
    from game.squadrons.airwing import AirWing


@dataclass
class PlanAewc(PackagePlanningTask[MissionTarget]):
    _air_wing: Optional["AirWing"] = field(default=None, compare=False)

    def preconditions_met(self, state: TheaterState) -> bool:
        if (
            state.context.coalition.player.is_blue
            and not state.context.settings.auto_ato_behavior_awacs
        ):
            return False
        if not super().preconditions_met(state):
            return False
        return self.target in state.aewc_targets

    def apply_effects(self, state: TheaterState) -> None:
        state.aewc_targets.remove(self.target)
        super().apply_effects(state)

    def fulfill_mission(self, state: TheaterState) -> bool:
        # propose_flights() gets no state, so stash the wing for the
        # basing-aware squadron preference below.
        self._air_wing = state.context.coalition.air_wing
        return super().fulfill_mission(state)

    def propose_flights(self) -> None:
        self.propose_flight(
            FlightType.AEWC, 1, preferred_type=self._preferred_aewc_type()
        )
        self.propose_flight(FlightType.ESCORT, 2)

    def _preferred_aewc_type(self) -> Optional["AircraftType"]:
        """Basing-aware AEW&C squadron preference.

        The generic squadron ranking measures base-to-*target* distance, and a
        carrier can easily sit closer to the land AEW&C anchor than the land
        AWACS base does -- the flown Scenic Route Merged plan double-tasked the
        boat's two E-2s (one dragged 160 NM to the land station) while both
        Al Dhafra E-3s sat untasked. The domain rule: a **carrier** station is
        covered by that boat's own squadron; a **land** station by the nearest
        land-based AWACS squadron. Returns None (generic ranking) when no such
        squadron has untasked jets -- an all-carrier wing still covers the land
        station with an E-2, and vice versa.
        """
        wing = self._air_wing
        if wing is None:
            return None
        target_is_carrier = getattr(self.target, "is_carrier", False) or getattr(
            self.target, "is_fleet", False
        )
        best: Optional["AircraftType"] = None
        best_distance = 0.0
        for squadron in wing.iter_squadrons():
            if squadron.untasked_aircraft <= 0:
                continue
            if not squadron.capable_of(FlightType.AEWC):
                continue
            location = squadron.location
            if target_is_carrier:
                if location is self.target:
                    return squadron.aircraft
                continue
            if getattr(location, "is_carrier", False) or getattr(
                location, "is_fleet", False
            ):
                continue
            distance = location.position.distance_to_point(self.target.position)
            if best is None or distance < best_distance:
                best, best_distance = squadron.aircraft, distance
        return best

    @property
    def asap(self) -> bool:
        # Supports all the early CAP flights, so should be in the air ASAP.
        return True
