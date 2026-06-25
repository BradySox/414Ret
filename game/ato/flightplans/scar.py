from __future__ import annotations

from datetime import timedelta
from typing import Type

from game.ato.flightplans.airspacegeometry import AirspaceGeometry
from game.ato.flightplans.ibuilder import IBuilder
from game.ato.flightplans.patrolling import PatrollingFlightPlan, PatrollingLayout
from game.ato.flightplans.uizonedisplay import UiZone, UiZoneDisplay
from game.ato.flightplans.waypointbuilder import WaypointBuilder
from game.utils import Distance, Speed, knots, meters, nautical_miles

# SCAR (Strike Coordination and Reconnaissance) — the loiter-and-task rework
# (docs/dev/design/414th-scar-king-fac-notes.md). The flight is planned like the
# Combat SAR package: it launches and **holds** a racetrack over a kill box, and
# services real, static enemy armor in the box. The C-130 "King" on-scene
# commander designates the target at runtime (Phase 2+); the targets are real
# Retribution TGOs, so their kills attrit the enemy through the normal ground-loss
# path -- no SCAR-specific scoring.
#
# This replaces the old strike-shaped, Armed-Recon-ingress plan against a *moving*
# spawned HVT. The "hold" is a PatrollingFlightPlan racetrack centred on the kill
# box (oriented parallel to the FLOT) with a non-zero engagement distance so the
# AI/player works the box rather than standing off (AEWC zeroes it).
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
        preferred = self.flight.unit_type.preferred_patrol_speed(altitude)
        if preferred is not None:
            return preferred
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
    def layout(self) -> PatrollingLayout:
        half = nautical_miles(SCAR_LOITER_HALF_NM)

        # Orient the racetrack parallel to the FLOT (the standoff-anchor heading the
        # support orbits use) but CENTRE it on the kill box -- the SCAR striker
        # holds over the target area, it does not stand off like AWACS.
        _, orbit_heading = AirspaceGeometry(
            self.theater, self.coalition.player, self.threat_zones
        ).standoff_anchor(self.package.target, meters(0))
        center = self.package.target.position

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
