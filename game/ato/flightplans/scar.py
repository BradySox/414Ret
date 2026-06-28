from __future__ import annotations

from datetime import timedelta
from typing import Optional, Type

from dcs import Point

from game.ato.flightplans.airspacegeometry import AirspaceGeometry
from game.ato.flightplans.ibuilder import IBuilder
from game.ato.flightplans.patrolling import PatrollingFlightPlan, PatrollingLayout
from game.ato.flightplans.uizonedisplay import UiZone, UiZoneDisplay
from game.ato.flightplans.waypointbuilder import WaypointBuilder
from game.ato.flighttype import FlightType
from game.utils import Distance, Speed, knots, meters, nautical_miles

# SCAR ("Sandy") — the RESCAP escort leg of the Combat SAR rescue package (rescue
# rework: docs/dev/design/414th-scar-rescue-rework-notes.md). Planned like the
# Combat SAR hold: an A-10/Apache launches and **holds** a racetrack near the FLOT
# alongside the King (C-130 on-scene commander) and Jolly Green (rescue helo). When
# a pilot ejects, Sandy protects the survivor, suppresses the threats around them,
# and walks the rescue helo in -- the King talks it on at runtime (voice-first).
#
# The "hold" is a PatrollingFlightPlan racetrack anchored on the front (oriented
# parallel to the FLOT) with a NON-ZERO engagement distance, so the shooter works
# the area near the survivor rather than standing off like AEWC (which zeroes it).
# This replaces the retired armor-hunt plan (a strike against a moving spawned HVT).
SCAR_AREA_RADIUS_NM = 5.0
# Racetrack half-length of the loiter, ~ the box, so the orbit covers the kill box.
SCAR_LOITER_HALF_NM = 6.0
# A modest stand-in for an airframe-scaled on-station loiter (fast-jet vs. A-10);
# kept simple for the rework's Phase 1 and tunable later.
SCAR_LOITER_DURATION = timedelta(minutes=20)


class ScarFlightPlan(PatrollingFlightPlan[PatrollingLayout], UiZoneDisplay):
    @property
    def patrol_duration(self) -> timedelta:
        return SCAR_LOITER_DURATION

    @property
    def patrol_speed(self) -> Speed:
        altitude = self.layout.patrol_start.alt
        if self.flight.unit_type.preferred_patrol_speed(altitude) is not None:
            return self.flight.unit_type.preferred_patrol_speed(altitude)
        return knots(350)

    @property
    def engagement_distance(self) -> Distance:
        # Work the kill box: unlike a pure AEWC orbit (which zeroes this), the SCAR
        # loiter engages ground targets within the box it is holding over.
        return nautical_miles(SCAR_AREA_RADIUS_NM)

    def ui_zone(self) -> UiZone:
        return UiZone(
            [self.layout.patrol_start.position, self.layout.patrol_end.position],
            nautical_miles(SCAR_AREA_RADIUS_NM),
        )

    @staticmethod
    def builder_type() -> Type[Builder]:
        return Builder


class Builder(IBuilder[ScarFlightPlan, PatrollingLayout]):
    def _king_hold_center(self) -> Optional[Point]:
        """Centre of the King's hold racetrack, so Sandy co-orbits the C-130 King.

        The King is the fixed-wing ``COMBAT_SAR`` flight in the same package (the
        helo ``COMBAT_SAR`` flight is the Jolly Green pickup). Accessing its
        ``flight_plan`` lazily builds it; the King's plan depends only on the package
        target and the ``COMBAT_SAR`` flights -- never on SCAR -- so there is no
        recursion. Returns None when the package fields no King (the AI safety net
        without a C-130, or a solo Sandy), so the caller falls back to the FLOT centre.
        """
        for flight in self.package.flights:
            if (
                flight is not self.flight
                and flight.flight_type is FlightType.COMBAT_SAR
                and not flight.is_helo
            ):
                layout = flight.flight_plan.layout
                start = getattr(layout, "patrol_start", None)
                end = getattr(layout, "patrol_end", None)
                if start is not None and end is not None:
                    return start.position.lerp(end.position, 0.5)
        return None

    def layout(self) -> PatrollingLayout:
        half = nautical_miles(SCAR_LOITER_HALF_NM)

        # Orient the racetrack parallel to the FLOT (the standoff-anchor heading the
        # support orbits use) and CENTRE it on the King's hold so Sandy escorts
        # (co-orbits) the C-130 on-scene commander instead of flying an independent
        # racetrack over the front. Falls back to the front centre when there is no
        # King in the package (AI safety net without a C-130, or a solo Sandy). Sandy
        # holds near the fighting where pilots go down -- it does not stand off like
        # AWACS -- and engages threats in its box via the CAS task + weapons-free ROE
        # (configure_scar). Walking Jolly Green in once a pickup starts is voice-first
        # (the King talks the Sandys on) and a combatsar runtime follow-up for the AI.
        _, orbit_heading = AirspaceGeometry(
            self.theater, self.coalition.player, self.threat_zones
        ).standoff_anchor(self.package.target, meters(0))
        center = self._king_hold_center() or self.package.target.position

        racetrack_start = center.point_from_heading(
            orbit_heading.right.degrees, half.meters
        )
        racetrack_end = center.point_from_heading(
            orbit_heading.left.degrees, half.meters
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

    def build(self, dump_debug_info: bool = False) -> ScarFlightPlan:
        return ScarFlightPlan(self.flight, self.layout())
