from __future__ import annotations

from typing import TYPE_CHECKING

import shapely.ops
from dcs import Point
from shapely.geometry import MultiPolygon, Point as ShapelyPoint, Polygon

from game.utils import nautical_miles

if TYPE_CHECKING:
    from game.coalition import Coalition
    from game.theater import ConflictTheater

#: Below this IP-to-join separation the two points are the same point plus
#: jitter, and the heading between them carries no information. The legitimate
#: separation is at least the doctrine's join distance (tens of miles), so this
#: only catches the collapsed case.
DEGENERATE_IP_JOIN_SEPARATION = nautical_miles(1)


def wedge_heading(target: Point, ip: Point, join: Point) -> float:
    """The axis the hold wedge is aimed down.

    Normally IP->join. That breaks when the two are effectively the same point:
    `JoinZoneGeometry.find_best_join_point()` falls back to `join = self.ip`
    exactly when it finds no usable geometry, and the only thing separating them
    afterwards is the 500 ft perturbation in `FormationAttackFlightPlan`. A
    heading measured across that gap is measuring `random.randint`, and it aims
    the wedge -- and so the hold point -- in an arbitrary direction.

    Flown 2026-08-16: a SEAD Sweep held 205.7 nm from its own runway to attack a
    target 23.6 nm away (596 nm of routing; still outbound when the mission
    ended). Measured ip->join separation on that flight: 0.81 nm.

    Below the threshold, use the target->join axis. It is stable, and it is the
    same form `JoinZoneGeometry` already uses for its own wedge
    (`target.heading_between_point(ip)`), so the two classes agree rather than
    this inventing a rule.
    """
    if ip.distance_to_point(join) < DEGENERATE_IP_JOIN_SEPARATION.meters:
        return target.heading_between_point(join)
    return ip.heading_between_point(join)


class HoldZoneGeometry:
    """Defines the zones used for finding optimal hold point placement.

    The zones themselves are stored in the class rather than just the resulting hold
    point so that the zones can be drawn in the map for debugging purposes.
    """

    def __init__(
        self,
        target: Point,
        home: Point,
        ip: Point,
        join: Point,
        coalition: Coalition,
        theater: ConflictTheater,
    ) -> None:
        self._target = target
        # Hold points are placed one of two ways. Either approach guarantees:
        #
        # * Safe hold point.
        # * Minimum distance to the join point.
        # * Not closer to the target than the join point.
        #
        # 1. As near the join point as possible with a specific distance from the
        #    departure airfield. This prevents loitering directly above the airfield but
        #    also keeps the hold point close to the departure airfield.
        #
        # 2. Alternatively, if the entire home zone is excluded by the above criteria,
        #    as neat the departure airfield as possible within a minimum distance from
        #    the join point, with a restricted turn angle at the join point. This
        #    handles the case where we need to backtrack from the departure airfield and
        #    the join point to place the hold point, but the turn angle limit restricts
        #    the maximum distance of the backtrack while maintaining the direction of
        #    the flight plan.
        self.threat_zone = coalition.opponent.threat_zone.all
        self.home = ShapelyPoint(home.x, home.y)
        self._home_point = home
        self._join_point = join
        self._hold_distance = coalition.doctrine.hold_distance

        self.join = ShapelyPoint(join.x, join.y)

        self.join_bubble = self.join.buffer(coalition.doctrine.push_distance.meters)

        join_to_target_distance = join.distance_to_point(target)
        self.target_bubble = ShapelyPoint(target.x, target.y).buffer(
            join_to_target_distance
        )

        self.home_bubble = self.home.buffer(coalition.doctrine.hold_distance.meters)

        excluded_zones = shapely.ops.unary_union(
            [self.join_bubble, self.target_bubble, self.threat_zone]
        )
        if not isinstance(excluded_zones, MultiPolygon):
            excluded_zones = MultiPolygon([excluded_zones])
        self.excluded_zones = excluded_zones

        join_heading = wedge_heading(target, ip, join)

        # Arbitrarily large since this is later constrained by the map boundary, and
        # we'll be picking a location close to the IP anyway. Just used to avoid real
        # distance calculations to project to the map edge.
        large_distance = nautical_miles(400).meters
        turn_limit = 40
        join_limit_ccw = join.point_from_heading(
            join_heading - turn_limit, large_distance
        )
        join_limit_cw = join.point_from_heading(
            join_heading + turn_limit, large_distance
        )

        join_direction_limit_wedge = Polygon(
            [
                (join.x, join.y),
                (join_limit_ccw.x, join_limit_ccw.y),
                (join_limit_cw.x, join_limit_cw.y),
            ]
        )

        permissible_zones = (
            coalition.nav_mesh.map_bounds(theater)
            .intersection(join_direction_limit_wedge)
            .difference(self.excluded_zones)
            .difference(self.home_bubble)
        )
        if not isinstance(permissible_zones, MultiPolygon):
            permissible_zones = MultiPolygon([permissible_zones])
        self.permissible_zones = permissible_zones
        self.preferred_lines = self.home_bubble.boundary.difference(self.excluded_zones)

    def find_best_hold_point(self) -> Point:
        if self.preferred_lines.is_empty:
            hold, _ = shapely.ops.nearest_points(self.permissible_zones, self.home)
        else:
            hold, _ = shapely.ops.nearest_points(self.preferred_lines, self.join)
        return self._bounded(self._target.new_in_same_map(hold.x, hold.y))

    def _bounded(self, hold: Point) -> Point:
        """Keep the hold within reach of home, whatever the geometry produced.

        Both branches above answer "nearest point of a zone", and neither is
        bounded: an empty or far-flung permissible zone yields a hold point an
        arbitrary distance away. The class contract is the opposite -- the
        docstring's first placement rule is "keeps the hold point close to the
        departure airfield".

        The wedge fix above removes the cause found on 2026-08-16, but a wedge
        aimed anywhere still hits this same unbounded search, so this is the
        backstop for causes not yet found. Falls back to the point the preferred
        branch would have chosen: on the hold ring, toward the join.
        """
        limit = max(
            self._hold_distance.meters,
            self._home_point.distance_to_point(self._join_point),
        )
        if self._home_point.distance_to_point(hold) <= limit:
            return hold
        heading = self._home_point.heading_between_point(self._join_point)
        return self._home_point.point_from_heading(heading, self._hold_distance.meters)
