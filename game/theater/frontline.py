from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any, Iterator, List, TYPE_CHECKING, Tuple

from dcs.mapping import Point

from .landmap import poly_contains
from .missiontarget import MissionTarget
from .player import Player
from ..lasercodes.lasercode import LaserCode
from ..utils import Heading, pairwise

if TYPE_CHECKING:
    from game.ato import FlightType
    from .controlpoint import ControlPoint, Coalition


FRONTLINE_MIN_CP_DISTANCE = 5000

#: Rung D: how much dearer the worst going is than open country. Advancing a
#: kilometre through terrain ground forces cannot occupy costs this multiple of
#: the weight advantage that a kilometre of open ground costs, so fronts stall
#: at chokepoints instead of sliding at a uniform rate.
MAX_TERRAIN_DIFFICULTY = 4.0

#: Samples per segment when measuring the going. Segments are a handful per front
#: line and this runs once per front line, so the cost is trivial; more samples
#: buy precision nobody can see on the map.
_TERRAIN_SAMPLES = 8


@dataclass
class FrontLineSegment:
    """
    Describes a line segment of a FrontLine
    """

    point_a: Point
    point_b: Point

    @property
    def blue_forward_heading(self) -> Heading:
        """The heading toward the start of the next red segment or red base."""
        return Heading.from_degrees(self.point_a.heading_between_point(self.point_b))

    @property
    def length(self) -> float:
        """Length of the segment"""
        return self.point_a.distance_to_point(self.point_b)


class FrontLine(MissionTarget):
    """Defines a front line location between two control points.
    Front lines are the area where ground combat happens.
    Overwrites the entirety of MissionTarget __init__ method to allow for
    dynamic position calculation.
    """

    def __init__(
        self,
        blue_point: ControlPoint,
        red_point: ControlPoint,
        laser_code: LaserCode,
    ) -> None:
        self.id = uuid.uuid4()
        self.blue_cp = blue_point
        self.red_cp = red_point
        self.laser_code = laser_code
        try:
            route = list(blue_point.convoy_route_to(red_point))
        except KeyError:
            # Some campaigns are air only and the mission generator currently relies on
            # *some* "front line" being drawn between these two. In this case there will
            # be no supply route to follow. Just create an arbitrary route between the
            # two points.
            route = [blue_point.position, red_point.position]
        # Snap the beginning and end points to the CPs rather than the convoy waypoints,
        # which are on roads.
        route[0] = blue_point.position
        route[-1] = red_point.position
        self.segments: List[FrontLineSegment] = [
            FrontLineSegment(a, b) for a, b in pairwise(route)
        ]
        super().__init__(
            f"Front line {blue_point}/{red_point}", self._compute_position()
        )

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, FrontLine):
            return False
        return (self.blue_cp, self.red_cp) == (other.blue_cp, other.red_cp)

    def __hash__(self) -> int:
        # MUST stay identity-based, NOT hash((self.blue_cp, self.red_cp)).
        # Pickle can call __hash__ before __setstate__ when a FrontLine is a set
        # member / dict key, so a state-dependent hash raises AttributeError and
        # breaks save loading. See upstream "Fix save loading" (605d8f057);
        # #53's audit re-broke this once already. Do not "tidy" it to match __eq__.
        return hash(id(self))

    def _compute_position(self) -> Point:
        return self.point_along_route_from_blue(self._blue_route_progress)

    def update_position(self) -> None:
        self.position = self._compute_position()

    def control_point_friendly_to(self, player: Player) -> ControlPoint:
        if player.is_blue:
            return self.blue_cp
        return self.red_cp

    def control_point_hostile_to(self, player: Player) -> ControlPoint:
        if player.is_blue:
            return self.red_cp
        else:
            return self.blue_cp

    def is_friendly(self, to_player: Player) -> bool:
        """Returns True if the objective is in friendly territory."""
        return False

    def mission_types(self, for_player: Player) -> Iterator[FlightType]:
        from game.ato import FlightType

        yield from [
            FlightType.CAS,
            FlightType.AEWC,
            FlightType.REFUELING,
            # TODO: FlightType.TROOP_TRANSPORT
            # TODO: FlightType.EVAC
        ]
        yield from super().mission_types(for_player)

    @property
    def points(self) -> Iterator[Point]:
        yield self.segments[0].point_a
        for segment in self.segments:
            yield segment.point_b

    @property
    def control_points(self) -> Tuple[ControlPoint, ControlPoint]:
        """Returns a tuple of the two control points."""
        return self.blue_cp, self.red_cp

    @property
    def coalition(self) -> Coalition:
        return self.blue_cp.coalition

    @property
    def route_length(self) -> float:
        """The total distance of all segments"""
        return sum(i.length for i in self.segments)

    @property
    def blue_forward_heading(self) -> Heading:
        """The heading toward the start of the next red segment or red base."""
        return self.active_segment.blue_forward_heading

    @property
    def active_segment(self) -> FrontLineSegment:
        """The FrontLine segment where there can be an active conflict"""
        if self._blue_route_progress <= self.segments[0].length:
            return self.segments[0]

        distance_to_segment = self._blue_route_progress
        for segment in self.segments:
            if distance_to_segment <= segment.length:
                return segment
            else:
                distance_to_segment -= segment.length
        logging.error(
            "Frontline attack distance is greater than the sum of its segments"
        )
        return self.segments[0]

    def point_along_route_from_blue(self, distance: float) -> Point:
        """Returns a point {distance} away from control_point_a along the route."""
        if distance < self.segments[0].length:
            return self.blue_cp.position.point_from_heading(
                self.segments[0].blue_forward_heading.degrees, distance
            )
        remaining_dist = distance
        for segment in self.segments:
            if remaining_dist < segment.length:
                return segment.point_a.point_from_heading(
                    segment.blue_forward_heading.degrees, remaining_dist
                )
            else:
                remaining_dist -= segment.length
        raise RuntimeError(
            f"Could not find front line point {distance} from {self.blue_cp}"
        )

    def _segment_difficulties(self) -> List[float]:
        """Going multiplier per segment, 1.0 for open country.

        Cached on the instance rather than stored on FrontLineSegment: pickled
        saves restore segments without any new field, so a stored attribute
        would raise on every pre-feature save. `getattr` re-derives instead.
        """
        cached = getattr(self, "_difficulties", None)
        if cached is not None and len(cached) == len(self.segments):
            return cached
        difficulties = self._measure_segment_difficulties()
        self._difficulties = difficulties
        return difficulties

    def _measure_segment_difficulties(self) -> List[float]:
        if not self.coalition.game.settings.terrain_weighted_front_line:
            return [1.0] * len(self.segments)
        landmap = self.coalition.game.theater.landmap
        if landmap is None:
            return [1.0] * len(self.segments)
        passable = landmap.inclusion_zone_only
        difficulties = []
        for segment in self.segments:
            blocked = 0
            for step in range(_TERRAIN_SAMPLES):
                # Sample segment interiors: the endpoints are control points and
                # front-line joints, which are passable by construction.
                fraction = (step + 0.5) / _TERRAIN_SAMPLES
                x = (
                    segment.point_a.x
                    + (segment.point_b.x - segment.point_a.x) * fraction
                )
                y = (
                    segment.point_a.y
                    + (segment.point_b.y - segment.point_a.y) * fraction
                )
                if not poly_contains(x, y, passable):
                    blocked += 1
            share = blocked / _TERRAIN_SAMPLES
            difficulties.append(1.0 + (MAX_TERRAIN_DIFFICULTY - 1.0) * share)
        return difficulties

    def _cumulative_effort(self, distance: float) -> float:
        """Effort spent advancing from blue's end to `distance` along the route."""
        difficulties = self._segment_difficulties()
        spent = 0.0
        travelled = 0.0
        for segment, difficulty in zip(self.segments, difficulties):
            if travelled + segment.length >= distance:
                return spent + (distance - travelled) * difficulty
            spent += segment.length * difficulty
            travelled += segment.length
        return spent

    def _distance_for_effort(self, effort: float) -> float:
        """Inverse of `_cumulative_effort`."""
        difficulties = self._segment_difficulties()
        spent = 0.0
        travelled = 0.0
        for segment, difficulty in zip(self.segments, difficulties):
            segment_effort = segment.length * difficulty
            if spent + segment_effort >= effort:
                return travelled + (effort - spent) / difficulty
            spent += segment_effort
            travelled += segment.length
        return self.route_length

    def _distance_for_effort_share(self, share: float) -> float:
        """Map blue's share of the fight to a distance in metres.

        An even fight sits at the midpoint whatever the terrain -- moving the
        neutral point would silently shift where every campaign's front starts.
        The terrain weights the *travel* away from it: ground that vehicles
        cannot cross soaks up advantage, so pushing through a pass costs several
        times what the same distance of open country costs.

        With every segment at difficulty 1.0 this reduces exactly to
        `share * route_length`, which is upstream's placement.
        """
        midpoint = self.route_length / 2
        effort_at_midpoint = self._cumulative_effort(midpoint)
        total_effort = self._cumulative_effort(self.route_length)
        if total_effort <= 0:
            return 0.0
        if share >= 0.5:
            beyond = total_effort - effort_at_midpoint
            target = effort_at_midpoint + (share - 0.5) / 0.5 * beyond
        else:
            target = effort_at_midpoint * (share / 0.5)
        return self._distance_for_effort(target)

    def _weight_of(self, control_point: ControlPoint) -> float:
        """How much this side counts for when the front is placed.

        Rung C: with the setting on, morale is multiplied by the materiel
        actually present, so a full-strength base holding five vehicles no
        longer weighs the same as one holding five hundred. With it off this is
        the bare morale scalar and the placement is upstream's.
        """
        if self.coalition.game.settings.scale_aware_front_line:
            return control_point.base.front_line_weight
        return control_point.base.strength

    @property
    def _blue_route_progress(self) -> float:
        """
        The distance from point "a" where the conflict should occur
        according to the current strength of each control point
        """
        blue_weight = self._weight_of(self.blue_cp)
        red_weight = self._weight_of(self.red_cp)
        if blue_weight <= 0 and red_weight <= 0:
            # Neither side weighs anything -- an air-only campaign, or armour
            # not bought yet. Fall back to morale rather than pinning the front
            # to blue's doorstep, which is what the blue-first branch below
            # would otherwise do.
            blue_weight = self.blue_cp.base.strength
            red_weight = self.red_cp.base.strength
        if blue_weight == 0:
            distance = 0.0
        elif red_weight == 0:
            distance = self.route_length
        else:
            share = blue_weight / (blue_weight + red_weight)
            distance = self._distance_for_effort_share(share)
        return self._adjust_for_min_dist(distance)

    def _adjust_for_min_dist(self, distance: float) -> float:
        """
        Ensures the frontline conflict is never located within the minimum distance
        constant of either end control point.
        """
        if self.route_length < 2 * FRONTLINE_MIN_CP_DISTANCE:
            # The route is too short to keep FRONTLINE_MIN_CP_DISTANCE clear of
            # BOTH ends at once (the two clamp bounds cross). Clamping toward
            # either end in this case can push the front past the midpoint to
            # the OTHER side from where the strength ratio placed it -- e.g. a
            # front that should sit near red's end (blue winning) gets pulled
            # all the way back toward blue's own CP. Neither bound is
            # meaningful for a route this short, so just use the midpoint.
            return self.route_length / 2
        if distance > self.route_length - FRONTLINE_MIN_CP_DISTANCE:
            distance = self.route_length - FRONTLINE_MIN_CP_DISTANCE
        elif distance < FRONTLINE_MIN_CP_DISTANCE:
            distance = FRONTLINE_MIN_CP_DISTANCE
        return distance

    @staticmethod
    def sort_control_points(
        a: ControlPoint, b: ControlPoint
    ) -> tuple[ControlPoint, ControlPoint]:
        if a.is_friendly_to(b):
            raise ValueError(
                "Cannot sort control points that are friendly to each other"
            )
        if a.captured.is_blue:
            return a, b
        return b, a
