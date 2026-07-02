from __future__ import annotations

from datetime import datetime, timedelta
from typing import Type

from dcs import Point

from game.utils import Distance, Heading, meters
from .ibuilder import IBuilder
from .patrolling import PatrollingLayout
from .refuelingflightplan import RefuelingFlightPlan
from .waypointbuilder import WaypointBuilder
from ..flighttype import FlightType
from ..flightwaypoint import FlightWaypoint
from ..flightwaypointtype import FlightWaypointType
from ..refueltasking import refuel_service_time


class PackageRefuelingFlightPlan(RefuelingFlightPlan):
    @staticmethod
    def builder_type() -> Type[Builder]:
        return Builder

    @property
    def patrol_duration(self) -> timedelta:
        service_time = timedelta(minutes=5)
        tanker = self.flight.unit_type
        for flight in self.package.flights:
            if flight.flight_type is FlightType.REFUELING:
                # Don't count tankers (including this one) as receivers.
                continue
            if not flight.unit_type.can_refuel_from(tanker):
                # Skip aircraft whose refueling method this tanker can't service
                # (e.g. a boom tanker and a probe-only receiver).
                continue
            service_time += refuel_service_time(flight.roster.max_size)

        # When the window opened early for a pre-vul receiver, extend the stay by
        # the same amount so the on-station end still covers the post-vul service
        # (patrol_end_time = patrol_start_time + patrol_duration).
        early_open = self._post_vul_on_station_time - self.patrol_start_time
        return service_time + early_open

    def target_area_waypoint(self) -> FlightWaypoint:
        return FlightWaypoint(
            "TARGET AREA",
            FlightWaypointType.TARGET_GROUP_LOC,
            self.package.target.position,
            meters(0),
            "RADIO",
        )

    @property
    def _post_vul_on_station_time(self) -> datetime:
        """When the tanker must be on station for the post-vul (egress) receivers."""
        altitude = self.flight.unit_type.patrol_altitude

        if altitude is None:
            altitude = Distance.from_feet(20000)

        assert self.package.waypoints is not None

        # Cheat in a FlightWaypoint for the split point.
        split: Point = self.package.waypoints.split
        split_waypoint: FlightWaypoint = FlightWaypoint(
            "SPLIT", FlightWaypointType.SPLIT, split, altitude
        )

        # Cheat in a FlightWaypoint for the refuel point.
        refuel: Point = self.package.waypoints.refuel
        refuel_waypoint: FlightWaypoint = FlightWaypoint(
            "REFUEL", FlightWaypointType.REFUEL, refuel, altitude
        )

        delay_target_to_split: timedelta = self.total_time_between_waypoints(
            self.target_area_waypoint(), split_waypoint
        )
        delay_split_to_refuel: timedelta = self.total_time_between_waypoints(
            split_waypoint, refuel_waypoint
        )

        return (
            self.package.time_over_target
            + delay_target_to_split
            + delay_split_to_refuel
            - timedelta(minutes=1.5)
        )

    @property
    def _earliest_pre_vul_receiver_time(self) -> datetime | None:
        """When the first pre-vul (ingress) receiver reaches its refuel point."""
        tanker = self.flight.unit_type
        times: list[datetime] = []
        for flight in self.package.flights:
            if flight.flight_type is FlightType.REFUELING:
                continue
            if not flight.unit_type.can_refuel_from(tanker):
                continue
            refuel_pre = getattr(flight.flight_plan.layout, "refuel_pre", None)
            if refuel_pre is None:
                continue
            arrival = flight.flight_plan.chained_tot_for_waypoint(refuel_pre)
            if arrival is not None:
                times.append(arrival)
        return min(times, default=None)

    @property
    def patrol_start_time(self) -> datetime:
        # On station in time for the post-vul receivers, or earlier when a
        # pre-vul receiver tanks on its way in; patrol_duration stretches by the
        # early opening so the window still covers the post-vul service.
        start = self._post_vul_on_station_time
        earliest_pre_vul = self._earliest_pre_vul_receiver_time
        if earliest_pre_vul is not None:
            start = min(start, earliest_pre_vul - timedelta(minutes=1.5))
        return start


class Builder(IBuilder[PackageRefuelingFlightPlan, PatrollingLayout]):
    def layout(self) -> PatrollingLayout:
        package_waypoints = self.package.waypoints
        assert package_waypoints is not None

        racetrack_half_distance = Distance.from_nautical_miles(20).meters

        racetrack_center = package_waypoints.refuel

        split_heading = Heading.from_degrees(
            racetrack_center.heading_between_point(package_waypoints.split)
        )
        home_heading = split_heading.opposite

        racetrack_start = racetrack_center.point_from_heading(
            split_heading.degrees, racetrack_half_distance
        )

        racetrack_end = racetrack_center.point_from_heading(
            home_heading.degrees, racetrack_half_distance
        )

        builder = WaypointBuilder(self.flight)

        altitude = builder.get_patrol_altitude

        racetrack = builder.race_track(racetrack_start, racetrack_end, altitude)

        return PatrollingLayout(
            departure=builder.takeoff(self.flight.departure),
            nav_to=builder.nav_path(
                self.flight.departure.position, racetrack_start, altitude
            ),
            nav_from=builder.nav_path(
                racetrack_end, self.flight.arrival.position, altitude
            ),
            patrol_start=racetrack[0],
            patrol_end=racetrack[1],
            arrival=builder.land(self.flight.arrival),
            divert=builder.divert(self.flight.divert),
            bullseye=builder.bullseye(),
            custom_waypoints=list(),
        )

    def build(self, dump_debug_info: bool = False) -> PackageRefuelingFlightPlan:
        return PackageRefuelingFlightPlan(self.flight, self.layout())
