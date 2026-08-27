"""The fixed-wing CSAR on-scene commander -- the HC-130 "King".

See docs/dev/design/414th-csar-notes.md.

The King never picks anyone up: the DCS AI ``Land`` task is helicopter-only, so a
fixed-wing rescuer would orbit a survivor forever. ``CsarFlightPlan`` refuses to
build for one, and that refusal is correct -- the King is the *other* half of a
rescue package. It holds on station and works the survivor while the helo does the
recovery, so it gets a racetrack instead of a pickup.

Two rules this file must not break:

* The King stays out of the auto-planner (``FlightType.requires_helicopter`` and
  ``Squadron.can_auto_assign_mission``). This plan is only ever reached by a
  hand-fragged flight.
* The orbit clears the threat rings. A slow unarmed turboprop parked inside a SAM
  ring is a loss, not a rescue.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Type

from game.ato.flightplans.ibuilder import IBuilder
from game.ato.flightplans.patrolling import PatrollingFlightPlan, PatrollingLayout
from game.ato.flightplans.waypointbuilder import WaypointBuilder
from game.utils import Distance, Heading, Speed, meters, nautical_miles

#: How long the King holds on station. Hardcoded rather than exposed: the flight is
#: hand-fragged, so the player who wants a different window moves the waypoints.
ON_STATION_TIME = timedelta(minutes=60)

#: Half the racetrack's length. The legs run tangential to the survivor, so the
#: whole orbit stays at a constant distance from them. Short compared to AEW&C's
#: 30 nm half-track: a King works one survivor, not a whole theater.
RACETRACK_HALF_LENGTH = nautical_miles(10)

#: Where the orbit sits relative to the survivor when nothing is threatening it.
ON_SCENE_DISTANCE = nautical_miles(15)

#: How far outside the nearest threat ring the orbit is pushed, and how much room
#: it keeps from a ring it is already outside of.
THREAT_BUFFER = nautical_miles(10)

#: Never orbit closer than this even when threats crowd the survivor. Overhead is
#: no place for a four-engine turboprop.
MINIMUM_DISTANCE = nautical_miles(5)


class KingFlightPlan(PatrollingFlightPlan[PatrollingLayout]):
    @property
    def patrol_duration(self) -> timedelta:
        return ON_STATION_TIME

    @property
    def patrol_speed(self) -> Speed:
        return self.flight.unit_type.preferred_patrol_speed(
            self.layout.patrol_start.alt
        )

    @property
    def engagement_distance(self) -> Distance:
        # A pure orbit. The King is unarmed and RaceTrackBuilder only reads this
        # for the CAP flight types anyway.
        return meters(0)

    @staticmethod
    def builder_type() -> Type[Builder]:
        return Builder


class Builder(IBuilder[KingFlightPlan, PatrollingLayout]):
    def layout(self) -> PatrollingLayout:
        survivor = self.package.target

        closest_boundary = self.threat_zones.closest_boundary(survivor.position)
        heading_to_threat = Heading.from_degrees(
            survivor.position.heading_between_point(closest_boundary)
        )
        distance_to_threat = meters(
            survivor.position.distance_to_point(closest_boundary)
        )

        if self.threat_zones.threatened(survivor.position):
            # Inside a ring: the nearest edge is the way out, so run for it and put
            # the buffer on top. This can be a long way from the survivor, which is
            # the honest answer -- the alternative is orbiting under a SAM.
            orbit_heading = heading_to_threat
            orbit_distance = distance_to_threat + THREAT_BUFFER
        else:
            # Clear of the rings: hold off on the side away from the nearest threat,
            # closing in when that threat is near enough to crowd the orbit.
            orbit_heading = heading_to_threat.opposite
            orbit_distance = meters(
                min(
                    ON_SCENE_DISTANCE.meters,
                    max(
                        MINIMUM_DISTANCE.meters,
                        distance_to_threat.meters - THREAT_BUFFER.meters,
                    ),
                )
            )

        racetrack_center = survivor.position.point_from_heading(
            orbit_heading.degrees, orbit_distance.meters
        )
        racetrack_start = racetrack_center.point_from_heading(
            orbit_heading.right.degrees, RACETRACK_HALF_LENGTH.meters
        )
        racetrack_end = racetrack_center.point_from_heading(
            orbit_heading.left.degrees, RACETRACK_HALF_LENGTH.meters
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

    def build(self, dump_debug_info: bool = False) -> KingFlightPlan:
        return KingFlightPlan(self.flight, self.layout())
