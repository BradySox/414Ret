from __future__ import annotations

import random
from abc import ABC
from typing import Any, TYPE_CHECKING, TypeVar

from dcs import Point
from shapely.geometry import Point as ShapelyPoint

from game.utils import Heading, meters, nautical_miles
from .flightplan import FlightPlan
from .patrolling import PatrollingLayout
from ..closestairfields import ObjectiveDistanceCache
from ..flightplans.ibuilder import IBuilder
from ..flightplans.planningerror import PlanningError

if TYPE_CHECKING:
    from game.theater import MissionTarget

FlightPlanT = TypeVar("FlightPlanT", bound=FlightPlan[Any])
LayoutT = TypeVar("LayoutT", bound=PatrollingLayout)

# In a contested sector the BARCAP sits further forward (toward
# cap_max_distance_from_cp) so it can commit on inbound raids sooner; a quiet
# flank keeps the legacy back-to-front uniform spread. This is the fraction of
# the min->max distance band the forward bias may consume at peak air threat;
# kept below 1.0 so even the hottest sector retains a little placement jitter
# instead of pinning every wave to the same point. Threat-weighted *volume*
# (how many waves) is handled separately in theaterstate.py; this is the
# placement half of the same feature.
BARCAP_THREAT_FORWARD_BIAS = 0.75


class CapBuilder(IBuilder[FlightPlanT, LayoutT], ABC):
    def cap_racetrack_for_objective(
        self, location: MissionTarget, barcap: bool
    ) -> tuple[Point, Point]:
        closest_cache = ObjectiveDistanceCache.get_closest_airfields(location)
        for airfield in closest_cache.operational_airfields:
            # If the mission is a BARCAP of an enemy airfield, find the *next*
            # closest enemy airfield.
            if airfield == self.package.target:
                continue
            if airfield.captured != self.is_player:
                closest_airfield = airfield
                break
        else:
            for airfield in closest_cache.closest_airfields:
                if airfield.captured != self.is_player:
                    closest_airfield = airfield
                    break
            else:
                raise PlanningError("Could not find any enemy airfields")

        heading = Heading.from_degrees(
            location.position.heading_between_point(closest_airfield.position)
        )

        position = ShapelyPoint(
            self.package.target.position.x, self.package.target.position.y
        )

        if barcap:
            # BARCAPs should remain far enough back from the enemy that their
            # commit range does not enter the enemy's threat zone. Include a 5nm
            # buffer.
            distance_to_no_fly = (
                meters(position.distance(self.threat_zones.all))
                - self.doctrine.cap_engagement_range
                - nautical_miles(5)
            )
            max_track_length = self.doctrine.cap_max_track_length
        else:
            # Other race tracks (TARCAPs, currently) just try to keep some
            # distance from the nearest enemy airbase, but since they are by
            # definition in enemy territory they can't avoid the threat zone
            # without being useless.
            min_distance_from_enemy = nautical_miles(
                self.coalition.game.settings.tarcap_threat_buffer_min_distance
            )
            distance_to_airfield = meters(
                closest_airfield.position.distance_to_point(
                    self.package.target.position
                )
            )
            distance_to_no_fly = distance_to_airfield - min_distance_from_enemy

            # TARCAPs fly short racetracks because they need to react faster.
            max_track_length = self.doctrine.cap_min_track_length + 0.3 * (
                self.doctrine.cap_max_track_length - self.doctrine.cap_min_track_length
            )

        min_cap_distance = min(
            self.doctrine.cap_min_distance_from_cp, distance_to_no_fly
        )
        max_cap_distance = min(
            self.doctrine.cap_max_distance_from_cp, distance_to_no_fly
        )

        # Bias the orbit forward in contested sectors. At threat factor 0 (quiet
        # flank, or any non-CP/TARCAP target) lower_distance == min_cap_distance,
        # so the randint range is identical to the legacy uniform spread.
        lower_distance = min_cap_distance
        if barcap and max_cap_distance > min_cap_distance:
            factor = self._barcap_threat_factor(location)
            if factor > 0.0:
                span = max_cap_distance - min_cap_distance
                lower_distance = (
                    min_cap_distance + (factor * BARCAP_THREAT_FORWARD_BIAS) * span
                )

        end = location.position.point_from_heading(
            heading.degrees,
            random.randint(int(lower_distance.meters), int(max_cap_distance.meters)),
        )

        track_length = random.randint(
            int(self.doctrine.cap_min_track_length.meters),
            int(max_track_length.meters),
        )
        start = end.point_from_heading(heading.opposite.degrees, track_length)
        return start, end

    def _barcap_threat_factor(self, location: MissionTarget) -> float:
        """Normalized air threat (0..1) to the defended control point, used to
        bias the BARCAP orbit forward in contested sectors. Returns 0.0 for
        non-control-point targets so placement is unchanged off the
        threat-weighting path. Imported lazily to avoid a planner/flight-plan
        import cycle.
        """
        from game.commander.objectivefinder import ObjectiveFinder
        from game.theater import ControlPoint

        if not isinstance(location, ControlPoint):
            return 0.0
        finder = ObjectiveFinder(self.coalition.game, self.coalition.player)
        return finder.normalized_air_threat(location)
