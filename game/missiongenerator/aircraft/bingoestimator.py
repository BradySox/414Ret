from __future__ import annotations

import math
from typing import TYPE_CHECKING

from dcs import Point

from game.ato.flightwaypointtype import FlightWaypointType
from game.utils import Distance, meters

if TYPE_CHECKING:
    from game.ato.flightwaypoint import FlightWaypoint
    from game.dcs.aircrafttype import FuelConsumption


class BingoEstimator:
    """Estimates bingo/joker fuel values for a flight plan.

    The results returned by this class are bogus for most airframes. Only the few
    airframes which have fuel consumption data available can provide even moderately
    reliable estimates. **Do not use this for flight planning.** This should only be
    used in briefing context where it's okay to be wrong.
    """

    def __init__(
        self,
        fuel_consumption: FuelConsumption | None,
        arrival: Point,
        divert: Point | None,
        waypoints: list[FlightWaypoint],
    ) -> None:
        self.fuel_consumption = fuel_consumption
        self.arrival = arrival
        self.divert = divert
        self.waypoints = waypoints

    def estimate_bingo(self) -> int:
        """Bingo fuel value for the FlightPlan"""
        if (fuel := self.fuel_consumption) is not None:
            return self._fuel_consumption_based_estimate(fuel)
        return self._legacy_bingo_estimate()

    def estimate_joker(self) -> int:
        """Joker fuel value for the FlightPlan"""
        return self.estimate_bingo() + 1000

    def _fuel_consumption_based_estimate(self, fuel: FuelConsumption) -> int:
        # Bingo is the cruise fuel to reach the nearest place the flight can refuel --
        # the recovery field or a tanker on the route -- from the most distant point on
        # the route, plus the landing reserve. With no tanker this is just the cruise
        # fuel to the recovery field from the farthest waypoint (the legacy behavior).
        farthest_nm = self._max_distance_to_a_fuel_source()
        bingo = fuel.cruise * farthest_nm + fuel.min_safe
        return math.ceil(bingo / 100) * 100

    def _fuel_sources(self) -> list[Point]:
        # The recovery field plus any tanker (REFUEL waypoint) the flight crosses; the
        # flight can take on fuel at any of these, so a waypoint's recovery requirement
        # is set by whichever is nearest.
        sources = [self.arrival]
        sources.extend(
            wp.position
            for wp in self.waypoints
            if wp.waypoint_type is FlightWaypointType.REFUEL
        )
        return sources

    def _max_distance_to_a_fuel_source(self) -> float:
        sources = self._fuel_sources()
        return max(
            min(
                meters(wp.position.distance_to_point(src)).nautical_miles
                for src in sources
            )
            for wp in self.waypoints
        )

    def _legacy_bingo_estimate(self) -> int:
        distance_to_arrival = self._max_distance_from(self.arrival)

        bingo = 1000.0  # Minimum Emergency Fuel
        bingo += 500  # Visual Traffic
        bingo += 15 * distance_to_arrival.nautical_miles

        if self.divert is not None:
            max_divert_distance = self._max_distance_from(self.divert)
            bingo += 10 * max_divert_distance.nautical_miles

        return round(bingo / 100) * 100

    def _max_distance_from(self, point: Point) -> Distance:
        return max(meters(point.distance_to_point(w.position)) for w in self.waypoints)
