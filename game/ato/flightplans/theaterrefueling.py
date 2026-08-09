from __future__ import annotations

from typing import Type

from game.utils import Heading, meters, nautical_miles
from .ibuilder import IBuilder
from .patrolling import PatrollingLayout
from .refuelingflightplan import RefuelingFlightPlan
from .waypointbuilder import WaypointBuilder


class TheaterRefuelingFlightPlan(RefuelingFlightPlan):
    @staticmethod
    def builder_type() -> Type[Builder]:
        return Builder


class Builder(IBuilder[TheaterRefuelingFlightPlan, PatrollingLayout]):
    def layout(self) -> PatrollingLayout:
        racetrack_half_distance = nautical_miles(20).meters

        location = self.package.target

        closest_boundary = self.threat_zones.closest_boundary(location.position)
        heading_to_threat_boundary = Heading.from_degrees(
            location.position.heading_between_point(closest_boundary)
        )
        distance_to_threat = meters(
            location.position.distance_to_point(closest_boundary)
        )
        orbit_heading = heading_to_threat_boundary

        # Station 70nm outside the threat zone.
        threat_buffer = nautical_miles(
            self.coalition.game.settings.tanker_threat_buffer_min_distance
        )
        if self.threat_zones.threatened(location.position):
            orbit_distance = distance_to_threat + threat_buffer
        else:
            orbit_distance = distance_to_threat - threat_buffer

        racetrack_center = location.position.point_from_heading(
            orbit_heading.degrees, orbit_distance.meters
        )

        # 414th demand-based placement: the post-planning reposition pass
        # (game/commander/tankerdemand.py) may set a service point on the flight at
        # the strongest compatible receiver-demand cluster. When present it overrides
        # the anchor above, nudged back out of an enemy threat zone if it landed
        # inside one (head for the nearest boundary -- the way out -- then add the
        # buffer). getattr with a default keeps old saves / un-repositioned tankers
        # on the target anchor with no migration.
        service_point = getattr(self.flight, "refueling_service_point", None)
        if service_point is not None:
            racetrack_center = service_point
            if self.threat_zones.threatened(racetrack_center):
                boundary = self.threat_zones.closest_boundary(racetrack_center)
                away = Heading.from_degrees(
                    racetrack_center.heading_between_point(boundary)
                )
                clearance = (
                    self.threat_zones.distance_to_threat(racetrack_center)
                    + threat_buffer
                )
                racetrack_center = racetrack_center.point_from_heading(
                    away.degrees, clearance.meters
                )

        racetrack_start = racetrack_center.point_from_heading(
            orbit_heading.right.degrees, racetrack_half_distance
        )

        racetrack_end = racetrack_center.point_from_heading(
            orbit_heading.left.degrees, racetrack_half_distance
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

    def build(self, dump_debug_info: bool = False) -> TheaterRefuelingFlightPlan:
        return TheaterRefuelingFlightPlan(self.flight, self.layout())
