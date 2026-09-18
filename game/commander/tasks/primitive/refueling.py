from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from game.ato.flighttype import FlightType
from game.commander.missionproposals import EscortType
from game.commander.tasks.packageplanningtask import PackagePlanningTask
from game.commander.theaterstate import TheaterState
from typing import Optional, TYPE_CHECKING

from game.dcs.aircrafttype import AirRefuelType
from game.theater import MissionTarget

if TYPE_CHECKING:
    from game.dcs.aircrafttype import AircraftType
    from game.squadrons.airwing import AirWing


@dataclass
class PlanRefueling(PackagePlanningTask[MissionTarget]):
    #: The refuelling methods this coalition's aircraft need, most-needed first.
    #: Filled from the coalition before the flights are proposed.
    needed_refuel_methods: list[AirRefuelType] = field(init=False, default_factory=list)
    #: The wing, stashed before propose_flights() (which gets no state) so the
    #: carrier station can prefer that boat's own tanker.
    _air_wing: Optional["AirWing"] = field(default=None, compare=False)

    def preconditions_met(self, state: TheaterState) -> bool:
        if (
            state.context.coalition.player.is_blue
            and not state.context.settings.auto_ato_behavior_tankers
        ):
            return False
        self.needed_refuel_methods = self._methods_the_wing_needs(state)
        self._air_wing = state.context.coalition.air_wing
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

    @property
    def _is_carrier_station(self) -> bool:
        return bool(
            getattr(self.target, "is_carrier", False)
            or getattr(self.target, "is_fleet", False)
        )

    def _carrier_tanker_type(self) -> Optional["AircraftType"]:
        """That boat's own tanker, or None to leave the generic ranking alone."""
        if self._air_wing is None:
            return None
        for squadron in self._air_wing.iter_squadrons():
            if squadron.untasked_aircraft <= 0:
                continue
            if not squadron.capable_of(FlightType.REFUELING):
                continue
            if squadron.location is self.target:
                return squadron.aircraft
        return None

    def _land_tanker_for(self, method: AirRefuelType) -> Optional["AircraftType"]:
        """The land tanker the planner ranks best for `method` at this station, or None.

        Taken from the planner's own ranking, so a type that exists but cannot reach
        the station does not count as covering its method -- the first tanker is
        mandatory, and one that cannot be filled scrubs the package. Picking the first
        matching type in wing order instead flew a KC-135 160 NM over a KC-10 at 0.
        An untagged tanker passes the planner's method filter but covers nothing here.
        """
        if self._air_wing is None:
            return None
        for squadron in self._air_wing.best_squadrons_for(
            self.target,
            FlightType.REFUELING,
            1,
            heli=False,
            this_turn=True,
            refuel_methods=frozenset({method}),
        ):
            if getattr(squadron.location, "is_carrier", False) or getattr(
                squadron.location, "is_fleet", False
            ):
                continue
            if method in squadron.aircraft.tanker_refuel_types:
                return squadron.aircraft
        return None

    def propose_flights(self) -> None:
        if self._is_carrier_station:
            # A boat's station is covered by that boat's own tanker. The per-method
            # fan-out below is a THEATER concern -- proposing a boom tanker at a
            # probe-only carrier air wing just fails to fill.
            self.propose_flight(
                FlightType.REFUELING, 1, preferred_type=self._carrier_tanker_type()
            )
            self.propose_flight(FlightType.ESCORT, 2, EscortType.AirToAir)
            return
        # One tanker per method a LAND tanker can fly here; a boat-only method is its
        # own station's job (else the probe slot drags the A-6E 314 NM off its boat).
        tankers = {m: self._land_tanker_for(m) for m in self.needed_refuel_methods}
        methods = [m for m in self.needed_refuel_methods if tankers[m] is not None]
        if not methods:
            # Nothing declares a method, or no fitting tanker can come: as before U15.
            self.propose_flight(FlightType.REFUELING, 1)
        # The first is constrained too: left free it took the best squadron overall,
        # and the loop then re-proposed that method -- two boom, no probe (B76). It is
        # mandatory so a short wing still buys a tanker; the rest never scrub.
        for index, method in enumerate(methods):
            self.propose_flight(
                FlightType.REFUELING,
                1,
                optional=index > 0,
                refuel_methods=frozenset({method}),
                preferred_type=tankers[method],
            )
        # See PlanAewc: untagged, this is a primary flight whose shortage scrubs
        # the tanker package outright.
        self.propose_flight(FlightType.ESCORT, 2, EscortType.AirToAir)
