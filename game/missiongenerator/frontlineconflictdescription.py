from __future__ import annotations

import math
from dataclasses import dataclass
from functools import cached_property
from typing import Optional, Tuple

from dcs.mapping import Point
from shapely.geometry import LineString, Point as ShapelyPoint
from shapely.ops import nearest_points

from game.settings import Settings
from game.theater.conflicttheater import ConflictTheater, FrontLine
from game.theater.controlpoint import ControlPoint
from game.utils import Heading, dcs_to_shapely_point

#: Rung E: how far a sector may bulge ahead of or behind the front's own line,
#: in metres. Big enough to read as a salient on the F10 map, small enough that
#: the two ends still anchor on the control points they run between.
MAX_SALIENT_DEPTH = 4000.0

#: How far ahead of each sector to look for room to advance into.
_SALIENT_PROBE = 8000.0

#: Lateral samples across the front. Odd, so one lands on the centre.
_SALIENT_SAMPLES = 7


@dataclass(frozen=True)
class FrontLineBounds:
    left_position: Point
    right_position: Point
    #: Rung E: how far each lateral sample sits ahead of (positive) or behind
    #: (negative) the straight chord, left to right. Empty means a straight
    #: front. Both ends are always 0.0, so `left_position`/`right_position` and
    #: every consumer reading only those are unaffected.
    sector_depths: tuple[float, ...] = ()

    @cached_property
    def length(self) -> int:
        return int(self.left_position.distance_to_point(self.right_position))

    @cached_property
    def center(self) -> Point:
        return (self.left_position + self.right_position) / 2

    @cached_property
    def heading_from_left_to_right(self) -> Heading:
        return Heading(
            int(self.left_position.heading_between_point(self.right_position))
        )

    @cached_property
    def advance_heading(self) -> Heading:
        """Blue's forward direction, perpendicular to the front."""
        return self.heading_from_left_to_right.right

    def depth_at(self, offset: float) -> float:
        """Bulge at `offset` metres from the left end, interpolated."""
        if len(self.sector_depths) < 2 or self.length <= 0:
            return 0.0
        fraction = min(max(offset / self.length, 0.0), 1.0)
        scaled = fraction * (len(self.sector_depths) - 1)
        index = int(scaled)
        if index >= len(self.sector_depths) - 1:
            return self.sector_depths[-1]
        low = self.sector_depths[index]
        high = self.sector_depths[index + 1]
        return low + (high - low) * (scaled - index)

    def point_at(self, offset: float) -> Point:
        """The front's actual trace at `offset` metres from the left end.

        With no sector depths this is the straight chord, which is what every
        consumer got before rung E.
        """
        on_chord = self.left_position.point_from_heading(
            self.heading_from_left_to_right.degrees, offset
        )
        depth = self.depth_at(offset)
        if not depth:
            return on_chord
        return on_chord.point_from_heading(self.advance_heading.degrees, depth)

    @cached_property
    def polyline(self) -> tuple[Point, ...]:
        """The front as a bowed line, left to right."""
        if len(self.sector_depths) < 2:
            return (self.left_position, self.right_position)
        steps = len(self.sector_depths) - 1
        points = [
            self.point_at(self.length * index / steps) for index in range(steps + 1)
        ]
        # Pin the ends exactly. `point_at` walks the chord with trig, which
        # drifts a fraction of a micron, and consumers compare these against
        # `left_position` / `right_position`.
        points[0] = self.left_position
        points[-1] = self.right_position
        return tuple(points)


class FrontLineConflictDescription:
    def __init__(
        self,
        theater: ConflictTheater,
        front_line: FrontLine,
        position: Point,
        heading: Optional[Heading] = None,
        size: Optional[int] = None,
        bounds: Optional[FrontLineBounds] = None,
    ):
        self.front_line = front_line
        self.theater = theater
        self.position = position
        self.heading = heading
        self.size = size
        #: Present for ground conflicts only. Carries the rung E sector depths so
        #: the FLOT can be placed along the bowed front instead of the chord.
        self.bounds = bounds

    @property
    def blue_cp(self) -> ControlPoint:
        return self.front_line.blue_cp

    @property
    def red_cp(self) -> ControlPoint:
        return self.front_line.red_cp

    @classmethod
    def frontline_position(
        cls, frontline: FrontLine, theater: ConflictTheater, settings: Settings
    ) -> Tuple[Point, Heading]:
        attack_heading = frontline.blue_forward_heading
        position = cls.find_ground_position(
            frontline.position,
            settings.max_frontline_width * 1000,
            attack_heading.right,
            theater,
        )
        return position, attack_heading.opposite

    @classmethod
    def frontline_bounds(
        cls, front_line: FrontLine, theater: ConflictTheater
    ) -> FrontLineBounds:
        """
        Returns a vector for a valid frontline location avoiding exclusion zones.
        """
        settings = front_line.coalition.game.settings
        center_position, heading = cls.frontline_position(front_line, theater, settings)
        left_heading = heading.left
        right_heading = heading.right
        left_position = cls.extend_ground_position(
            center_position,
            int(settings.max_frontline_width * 1000 / 2),
            left_heading,
            theater,
        )
        right_position = cls.extend_ground_position(
            center_position,
            int(settings.max_frontline_width * 1000 / 2),
            right_heading,
            theater,
        )
        bounds = FrontLineBounds(left_position, right_position)
        if not settings.front_line_salients:
            return bounds
        return FrontLineBounds(
            left_position,
            right_position,
            cls.sector_depths(bounds, theater),
        )

    @classmethod
    def sector_depths(
        cls, bounds: FrontLineBounds, theater: ConflictTheater
    ) -> tuple[float, ...]:
        """How far each sector of the front bulges, from the room ahead of it.

        Sectors facing open ground push forward; sectors facing ground the
        vehicles cannot cross sit back. Depths are centred on their own mean so
        the front as a whole does not move, and tapered to zero at both ends so
        the line still anchors between its two control points.
        """
        if theater.landmap is None or bounds.length <= 0:
            return ()
        rooms = []
        for index in range(_SALIENT_SAMPLES):
            fraction = index / (_SALIENT_SAMPLES - 1)
            on_chord = bounds.left_position.point_from_heading(
                bounds.heading_from_left_to_right.degrees, bounds.length * fraction
            )
            ahead = cls.extend_ground_position(
                on_chord, int(_SALIENT_PROBE), bounds.advance_heading, theater
            )
            rooms.append(on_chord.distance_to_point(ahead))
        mean_room = sum(rooms) / len(rooms)
        depths = []
        for index, room in enumerate(rooms):
            fraction = index / (_SALIENT_SAMPLES - 1)
            taper = math.sin(math.pi * fraction)
            depth = (room - mean_room) * 0.5 * taper
            depths.append(
                max(-MAX_SALIENT_DEPTH, min(MAX_SALIENT_DEPTH, round(depth, 3)))
            )
        return tuple(depths)

    @classmethod
    def frontline_cas_conflict(
        cls, front_line: FrontLine, theater: ConflictTheater
    ) -> FrontLineConflictDescription:
        # TODO: Break apart the front-line and air conflict descriptions.
        # We're wastefully not caching the front-line bounds here because air conflicts
        # can't compute bounds, only a position.
        bounds = cls.frontline_bounds(front_line, theater)
        conflict = cls(
            theater=theater,
            front_line=front_line,
            position=bounds.left_position,
            heading=bounds.heading_from_left_to_right,
            size=bounds.length,
            bounds=bounds,
        )
        return conflict

    @classmethod
    def extend_ground_position(
        cls,
        initial: Point,
        max_distance: int,
        heading: Heading,
        theater: ConflictTheater,
    ) -> Point:
        """Finds the first intersection with an exclusion zone in one heading from an initial point up to max_distance"""
        extended = initial.point_from_heading(heading.degrees, max_distance)
        if theater.landmap is None:
            # TODO: Why is this possible?
            return extended

        p0 = ShapelyPoint(initial.x, initial.y)
        p1 = ShapelyPoint(extended.x, extended.y)
        line = LineString([p0, p1])

        intersection = line.intersection(theater.landmap.inclusion_zone_only.boundary)
        if intersection.is_empty:
            # Max extent does not intersect with the boundary of the inclusion
            # zone, so the full front line is usable. This does assume that the
            # front line was centered on a valid location.
            return extended

        # Otherwise extend the front line only up to the intersection.
        return initial.point_from_heading(heading.degrees, p0.distance(intersection))

    @classmethod
    def find_ground_position(
        cls,
        initial: Point,
        max_distance: int,
        heading: Heading,
        theater: ConflictTheater,
    ) -> Point:
        """Finds a valid ground position for the front line center.

        Checks for positions along the front line first. If none succeed, the nearest
        land position to the initial point is used.
        """
        if theater.landmap is None:
            return initial

        line = LineString(
            [
                dcs_to_shapely_point(
                    initial.point_from_heading(heading.degrees, max_distance)
                ),
                dcs_to_shapely_point(
                    initial.point_from_heading(heading.opposite.degrees, max_distance)
                ),
            ]
        )
        masked_front_line = theater.landmap.inclusion_zone_only.intersection(line)
        if masked_front_line.is_empty:
            return theater.nearest_land_pos(initial)
        nearest_good, _ = nearest_points(
            masked_front_line, dcs_to_shapely_point(initial)
        )
        return initial.new_in_same_map(nearest_good.x, nearest_good.y)
