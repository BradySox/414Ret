from __future__ import annotations

from typing import Type

from game.ato.flightplans.aewc import AewcFlightPlan
from game.ato.flightplans.aewc import Builder as AewcBuilder
from game.ato.flightplans.airspacegeometry import AirspaceGeometry
from game.ato.flightplans.patrolling import PatrollingLayout
from game.ato.flightplans.waypointbuilder import WaypointBuilder
from game.ato.flighttype import FlightType
from game.utils import nautical_miles

# A standing rescue alert is a helicopter (CH-47), not an AWACS. It must hold
# *near* the FLOT so it can actually reach an ejection, not loiter at AWACS depth.
# So Combat SAR gets its own small forward hold instead of the AEW&C racetrack:
#   - a short threat buffer: stage just clear of the immediate FLOT threats
#     (SHORAD/MANPAD reach), not the 70-80 NM support-orbit standoff;
#   - a helo-sized racetrack (a tight hold, not a 60 NM AWACS track).
COMBAT_SAR_THREAT_BUFFER = nautical_miles(15)
COMBAT_SAR_RACETRACK_HALF_DISTANCE = nautical_miles(5)


class CombatSarFlightPlan(AewcFlightPlan):
    """Standing pilot-rescue hold near the FLOT (414th Combat SAR).

    Reuses the AEW&C patrol scaffolding (duration, zero engagement distance, and
    the support-flight integration keyed off ``isinstance(.., AewcFlightPlan)``)
    but holds forward near the front instead of at AWACS standoff. The airframe is
    a CH-47/C-130 rescue craft, so it already patrols at its own (helo-sane)
    ``preferred_patrol_speed`` -- the AEW&C 390 kt branch is never reached. The
    MOOSE CSAR runtime (resources/plugins/combatsar) does the reactive pickup; this
    just keeps a rescue helo on station so coverage exists with no player CSAR up.
    """

    @staticmethod
    def builder_type() -> Type[Builder]:
        return Builder


class Builder(AewcBuilder):
    def layout(self) -> PatrollingLayout:
        racetrack_half_distance = COMBAT_SAR_RACETRACK_HALF_DISTANCE

        # Anchor on the front line, but stand off only a short distance so the
        # rescue helo holds near the fighting (see COMBAT_SAR_THREAT_BUFFER).
        base_center, orbit_heading = AirspaceGeometry(
            self.theater, self.coalition.player, self.threat_zones
        ).standoff_anchor(self.package.target, COMBAT_SAR_THREAT_BUFFER)

        # When more than one Combat SAR is planned, spread their holds laterally
        # along the front so each covers a different section rather than stacking.
        all_csar = sorted(
            [
                f
                for p in self.coalition.ato.packages
                for f in p.flights
                if f.flight_type is FlightType.COMBAT_SAR
            ],
            key=lambda f: str(f.id),
        )
        n = len(all_csar)
        try:
            idx = next(i for i, f in enumerate(all_csar) if f is self.flight)
        except StopIteration:
            idx = 0

        lateral_m = (idx - (n - 1) / 2) * (racetrack_half_distance * 2).meters
        if lateral_m >= 0:
            racetrack_center = base_center.point_from_heading(
                orbit_heading.right.degrees, lateral_m
            )
        else:
            racetrack_center = base_center.point_from_heading(
                orbit_heading.left.degrees, -lateral_m
            )

        racetrack_start = racetrack_center.point_from_heading(
            orbit_heading.right.degrees, racetrack_half_distance.meters
        )
        racetrack_end = racetrack_center.point_from_heading(
            orbit_heading.left.degrees, racetrack_half_distance.meters
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

    def build(self, dump_debug_info: bool = False) -> CombatSarFlightPlan:
        return CombatSarFlightPlan(self.flight, self.layout())
