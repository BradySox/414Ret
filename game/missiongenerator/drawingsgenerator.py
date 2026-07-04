from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from dcs import Point
from dcs.drawing import LineStyle, Rgba
from dcs.drawing.drawings import StandardLayer
from dcs.mission import Mission

from game import Game
from game.ato.flighttype import FlightType
from game.ato.flightwaypointtype import FlightWaypointType
from game.missiongenerator.frontlineconflictdescription import (
    FrontLineConflictDescription,
)

# Misc config settings for objects drawn in ME mission file (and F10 map)
from game.theater import TRIGGER_RADIUS_CAPTURE

if TYPE_CHECKING:
    from game.fourteenth.phases import ResolvedZone
    from game.missiongenerator.aircraft.flightdata import FlightData
    from game.missiongenerator.missiondata import MissionData

FRONTLINE_COLORS = Rgba(255, 0, 0, 255)
WHITE = Rgba(255, 255, 255, 255)
CP_RED = Rgba(255, 0, 0, 80)
CP_BLUE = Rgba(0, 0, 255, 80)
CP_NEUTRAL = Rgba(128, 128, 128, 80)
BLUE_PATH_COLOR = Rgba(0, 0, 255, 100)
RED_PATH_COLOR = Rgba(255, 0, 0, 100)
ACTIVE_PATH_COLOR = Rgba(255, 80, 80, 100)
# ROE restricted zones (campaign phases W4): dashed red like the web map layer, so
# they read as *rules* (off-limits airspace), not radar coverage.
ROE_ZONE_LINE = Rgba(212, 58, 58, 220)
ROE_ZONE_FILL = Rgba(212, 58, 58, 40)
# Free-fire (weapons-free) pockets -- inverted ROE (COIN): dashed GREEN, the opposite
# reading of the red restricted zones ("cleared to engage here" vs "off limits").
FREE_FIRE_LINE = Rgba(60, 205, 95, 220)
FREE_FIRE_FILL = Rgba(60, 205, 95, 40)
# Support-package orbits (tankers + AWACS): a cyan dashed racetrack + a label so a
# pilot can find their tanker / AEW&C on the F10 map in flight (the anti-DTC).
SUPPORT_ORBIT_LINE = Rgba(0, 200, 255, 255)
SUPPORT_ORBIT_FILL = Rgba(0, 200, 255, 55)
SUPPORT_LABEL_TEXT = Rgba(0, 190, 255, 255)
SUPPORT_LABEL_FILL = Rgba(0, 30, 45, 150)
#: Racetrack half-width drawn for a support orbit (~2 NM) -- purely a visual cue.
SUPPORT_ORBIT_RADIUS_M = 3704.0


class DrawingsGenerator:
    """
    Generate drawn objects for the F10 map and mission editor
    """

    def __init__(
        self,
        mission: Mission,
        game: Game,
        mission_data: Optional[MissionData] = None,
    ) -> None:
        self.mission = mission
        self.game = game
        #: Populated support/flight data (tankers, AWACS, flights); None when the
        #: caller has none, in which case the support-orbit pass is skipped.
        self.mission_data = mission_data
        self.player_layer = self.mission.drawings.get_layer(StandardLayer.Blue)

    def generate_cps_markers(self) -> None:
        """
        Generate cps as circles
        """
        for cp in self.game.theater.controlpoints:
            if cp.captured.is_blue:
                color = CP_BLUE
            elif cp.captured.is_red:
                color = CP_RED
            else:
                color = CP_NEUTRAL
            shape = self.player_layer.add_circle(
                cp.position,
                TRIGGER_RADIUS_CAPTURE,
                line_thickness=2,
                color=WHITE,
                fill=color,
                line_style=LineStyle.Dot,
            )
            shape.name = cp.name

    def generate_routes(self) -> None:
        """
        Generate routes drawing between cps
        """
        seen = set()
        for cp in self.game.theater.controlpoints:
            seen.add(cp)
            for destination, convoy_route in cp.convoy_routes.items():
                if destination in seen:
                    continue
                else:
                    # Determine path color
                    if cp.captured.is_blue and destination.captured.is_blue:
                        color = BLUE_PATH_COLOR
                    elif cp.captured.is_red and destination.captured.is_red:
                        color = RED_PATH_COLOR
                    else:
                        color = ACTIVE_PATH_COLOR

                    # Add shape to layer
                    shape = self.player_layer.add_line_segments(
                        cp.position,
                        [Point(0, 0, self.game.theater.terrain)]
                        + [p - cp.position for p in convoy_route]
                        + [destination.position - cp.position],
                        line_thickness=6,
                        color=color,
                        line_style=LineStyle.Solid,
                    )
                    shape.name = "path from " + cp.name + " to " + destination.name

    def generate_frontlines_drawing(self) -> None:
        """
        Generate a frontline "line" for each active frontline
        """
        for front_line in self.game.theater.conflicts():
            bounds = FrontLineConflictDescription.frontline_bounds(
                front_line, self.game.theater
            )

            end_point = bounds.left_position.point_from_heading(
                bounds.heading_from_left_to_right.degrees, bounds.length
            )
            shape = self.player_layer.add_line_segment(
                bounds.left_position,
                end_point - bounds.left_position,
                line_thickness=16,
                color=FRONTLINE_COLORS,
                line_style=LineStyle.Triangle,
            )
            shape.name = front_line.name

    def _paint_zones(self, zones: list[ResolvedZone], color: Rgba, fill: Rgba) -> None:
        """Paint resolved ROE zones (circle -> add_circle, else the polygon outline)."""
        for zone in zones:
            if zone.kind == "circle":
                shape = self.player_layer.add_circle(
                    self.game.point_in_world(*zone.center_xy),
                    zone.radius_m,
                    line_thickness=4,
                    color=color,
                    fill=fill,
                    line_style=LineStyle.Dash,
                )
            else:
                points = [self.game.point_in_world(x, y) for x, y in zone.outline_xy]
                if len(points) < 3:
                    continue
                anchor = points[0]
                shape = self.player_layer.add_freeform_polygon(
                    anchor,
                    [p - anchor for p in points],
                    line_thickness=4,
                    color=color,
                    fill=fill,
                    line_style=LineStyle.Dash,
                )
            shape.name = zone.name

    def generate_restricted_zones(self) -> None:
        """Paint the active phase's ROE zones (red no-strike + green free-fire).

        Reads the same resolved zones the web map layer draws, so the F10 map and the
        client show identical geometry. Restricted (no-strike) zones paint red;
        free-fire pockets (inverted ROE, COIN) paint green. No-op outside an authored
        ROE phase (both lists empty) -- non-ROE campaigns see nothing new.
        """
        from game.fourteenth.phases import (
            active_free_fire_zones,
            active_restricted_zones,
        )

        self._paint_zones(
            active_free_fire_zones(self.game), FREE_FIRE_LINE, FREE_FIRE_FILL
        )
        self._paint_zones(
            active_restricted_zones(self.game), ROE_ZONE_LINE, ROE_ZONE_FILL
        )

    @staticmethod
    def _racetrack_ends(
        flight: "FlightData",
    ) -> tuple[Optional[Point], Optional[Point]]:
        """The two ends of a support flight's orbit racetrack, or (None, None).

        ``race_track_start`` is emitted as a ``PATROL_TRACK`` waypoint and
        ``race_track_end`` as a ``PATROL`` waypoint (see the waypoint builder), so
        the pair defines the orbit leg the tanker/AEW&C flies.
        """
        start: Optional[Point] = None
        end: Optional[Point] = None
        for waypoint in flight.waypoints:
            if waypoint.waypoint_type == FlightWaypointType.PATROL_TRACK:
                start = waypoint.position
            elif waypoint.waypoint_type == FlightWaypointType.PATROL:
                end = waypoint.position
        return start, end

    @staticmethod
    def _support_label(flight: "FlightData", info: object) -> str:
        """Callsign · type on line 1; radio freq · TACAN on line 2 (if known)."""
        label = f"{flight.callsign}  {flight.aircraft_type.display_name}"
        comms = []
        freq = getattr(info, "freq", None)
        if freq is not None:
            comms.append(str(freq))
        tacan = getattr(info, "tacan", None)
        if tacan is not None:
            comms.append(f"TCN {tacan}")
        if comms:
            label += "\n" + "  ".join(comms)
        return label

    def generate_support_orbits(self) -> None:
        """Paint each blue tanker / AEW&C orbit as a labelled racetrack on the F10 map.

        Players can't easily find their tanker/AWACS orbit in the cockpit; this draws
        the racetrack the flight flies plus a label (callsign, type, freq, TACAN) so
        the support package is visible in flight -- the reliable, DTC-free way. No-op
        when the caller passed no ``mission_data``.
        """
        if self.mission_data is None:
            return
        info_by_group = {
            info.group_name: info
            for info in [*self.mission_data.tankers, *self.mission_data.awacs]
        }
        for flight in self.mission_data.flights:
            if flight.flight_type not in (FlightType.REFUELING, FlightType.AEWC):
                continue
            if not flight.friendly.is_blue:
                continue
            start, end = self._racetrack_ends(flight)
            if start is None or end is None:
                continue
            if start.distance_to_point(end) < 1.0:
                shape = self.player_layer.add_circle(
                    start,
                    SUPPORT_ORBIT_RADIUS_M,
                    line_thickness=6,
                    color=SUPPORT_ORBIT_LINE,
                    fill=SUPPORT_ORBIT_FILL,
                    line_style=LineStyle.Dash,
                )
            else:
                shape = self.player_layer.add_oblong(
                    start,
                    end,
                    SUPPORT_ORBIT_RADIUS_M,
                    line_thickness=6,
                    color=SUPPORT_ORBIT_LINE,
                    fill=SUPPORT_ORBIT_FILL,
                    line_style=LineStyle.Dash,
                )
            shape.name = f"{flight.callsign} orbit"
            label = self.player_layer.add_text_box(
                start,
                self._support_label(flight, info_by_group.get(flight.group_name)),
                color=SUPPORT_LABEL_TEXT,
                fill=SUPPORT_LABEL_FILL,
                font_size=14,
            )
            label.name = f"{flight.callsign} label"

    def generate(self) -> None:
        self.generate_frontlines_drawing()
        self.generate_routes()
        self.generate_cps_markers()
        self.generate_restricted_zones()
        self.generate_support_orbits()
