"""The rescue escort -- "Sandy".

See docs/dev/design/414th-csar-notes.md.

Sandy is the armed half of a rescue package: an A-10 or an Apache working the
ground around the survivor while the helo comes in for the pickup. It is the one
role the rescue package had no way to express -- ``CasFlightPlan`` hard-raises
unless the package target is a ``FrontLine``, and a rescue package's target is a
``DownedPilot``.

So it subclasses the CAS plan rather than copying it: the track straddles the
survivor instead of the FLOT, and everything downstream (``CasIngressBuilder``'s
``EngageTargetsInZone``, the map overlay, the escort hand-off points) keeps
working because the plan is still a CAS plan.

Two rules this file must not break:

* The Sandy stays out of the auto-planner. Nothing in the HTN proposes it, and
  every capable airframe carries it under ``secondary_tasks``. An AI Sandy
  circling a pickup it cannot coordinate is noise; this is a role a player flies.
* The track is centred ON the survivor. The engagement zone is what keeps the
  pickup covered, so moving the centre off the pilot silently stops covering them.
"""

from __future__ import annotations

from typing import Type

from game.squadrons.downedpilot import DownedPilot
from game.utils import Distance, nautical_miles
from .cas import Builder as CasBuilder, CasFlightPlan, CasLayout
from .invalidobjectivelocation import InvalidObjectiveLocation
from .waypointbuilder import WaypointBuilder
from ..flightwaypointtype import FlightWaypointType

#: Half the track's length. The legs straddle the survivor, so the flight crosses
#: the pickup twice per circuit instead of driving away from it. Short because a
#: Sandy works one survivor, not a front.
TRACK_HALF_LENGTH = nautical_miles(3)

#: Radius of the engagement zone, centred on the survivor. Wide enough to cover
#: the helo's run-in and departure, tight enough that the flight does not wander
#: off hunting something unrelated while the pickup is happening.
ENGAGEMENT_RANGE = nautical_miles(5)

#: Where the run-in starts, measured from the survivor on the departure side.
#: Matches the rescue helicopter's own ingress distance so the package arrives
#: together.
INGRESS_DISTANCE = nautical_miles(5)


class SandyFlightPlan(CasFlightPlan):
    """A CAS track flown over a downed pilot rather than over the front line."""

    @staticmethod
    def builder_type() -> Type[Builder]:
        return Builder

    @property
    def engagement_distance(self) -> Distance:
        # Not cas_engagement_range_distance: that knob sizes a FLOT sweep. The
        # Sandy's zone is sized to the pickup, and the flight is hand-fragged, so
        # a player who wants a different one moves the waypoints.
        return ENGAGEMENT_RANGE


class Builder(CasBuilder):
    # Subclasses the CAS builder rather than IBuilder so the override stays
    # type-compatible with CasFlightPlan.builder_type(). layout() is replaced
    # wholesale, so the FrontLine requirement never runs.
    def layout(self, dump_debug_info: bool) -> CasLayout:
        survivor = self.package.target
        if not isinstance(survivor, DownedPilot):
            raise InvalidObjectiveLocation(self.flight.flight_type, survivor)

        # Run in from the departure side so the approach does not overfly the
        # pickup, and lay the track across that run-in: the flight arrives, turns
        # onto a leg that crosses the survivor, and wheels back over them.
        home_heading = survivor.position.heading_between_point(
            self.flight.departure.position
        )
        ingress_position = survivor.position.point_from_heading(
            home_heading, INGRESS_DISTANCE.meters
        )
        track_a = survivor.position.point_from_heading(
            (home_heading + 90) % 360, TRACK_HALF_LENGTH.meters
        )
        track_b = survivor.position.point_from_heading(
            (home_heading - 90) % 360, TRACK_HALF_LENGTH.meters
        )
        if track_b.distance_to_point(ingress_position) < track_a.distance_to_point(
            ingress_position
        ):
            track_a, track_b = track_b, track_a

        builder = WaypointBuilder(self.flight)
        altitude = builder.get_combat_altitude
        # The Apache is a Sandy too, and a helicopter navigates AGL.
        use_agl = self.flight.unit_type.dcs_unit_type.helicopter

        patrol_start = builder.cas(track_a, altitude)
        patrol_start.name = "SANDY START"
        patrol_start.pretty_name = "Sandy start"
        patrol_start.description = f"On station over {survivor.name}"

        patrol_end = builder.cas(track_b, altitude)
        patrol_end.name = "SANDY END"
        patrol_end.pretty_name = "Sandy end"
        patrol_end.description = f"On station over {survivor.name}"

        ingress = builder.ingress(
            FlightWaypointType.INGRESS_CAS, ingress_position, survivor
        )
        ingress.description = f"Ingress to cover the rescue of {survivor.name}"

        return CasLayout(
            departure=builder.takeoff(self.flight.departure),
            nav_to=builder.nav_path(
                self.flight.departure.position, ingress_position, altitude, use_agl
            ),
            nav_from=builder.nav_path(
                track_b, self.flight.arrival.position, altitude, use_agl
            ),
            ingress=ingress,
            patrol_start=patrol_start,
            patrol_end=patrol_end,
            arrival=builder.land(self.flight.arrival),
            divert=builder.divert(self.flight.divert),
            bullseye=builder.bullseye(),
            custom_waypoints=list(),
        )

    def build(self, dump_debug_info: bool = False) -> SandyFlightPlan:
        return SandyFlightPlan(self.flight, self.layout(dump_debug_info))
