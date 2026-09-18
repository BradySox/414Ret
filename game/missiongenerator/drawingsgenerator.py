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
# Support-package orbits (tankers + AWACS): a cyan dashed racetrack + a label so a
# pilot can find their tanker / AEW&C on the F10 map in flight (the anti-DTC).
SUPPORT_ORBIT_LINE = Rgba(0, 200, 255, 255)
SUPPORT_ORBIT_FILL = Rgba(0, 200, 255, 55)
SUPPORT_LABEL_TEXT = Rgba(0, 190, 255, 255)
SUPPORT_LABEL_FILL = Rgba(0, 30, 45, 150)
#: Floor for a drawn orbit half-width (~2 NM); below this the capsule is not
#: readable at map zoom. Also the fixed width for a CAP station, which is a
#: station marker -- a CAP chases contacts and no capsule can contain it.
SUPPORT_ORBIT_MIN_RADIUS_M = 3704.0
#: A tanker/AEW&C box is sized off the flight's own orbit speed instead. The AI
#: turns shallow at the end of the leg and overshoots the end waypoint before
#: rolling in, so the fixed 2 NM capsule left the aircraft outside its own box
#: for about half the time on station (test 36: the two KC-135s ran 17.7 and
#: 19.0 km off the leg centreline, the E-3A 13.8, the E-2C 8.9). A 20-degree
#: turn radius plus 3 NM covers all four.
SUPPORT_ORBIT_TURN_BANK_DEG = 20.0
SUPPORT_ORBIT_TURN_PAD_M = 5556.0


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

            # Rung E: draw the bowed trace, so a salient is visible on the F10
            # map rather than hidden behind a straight line. `polyline` is the
            # two endpoints when the front has no sector depths.
            trace = bounds.polyline
            shape = self.player_layer.add_line_segments(
                trace[0],
                [point - trace[0] for point in trace],
                line_thickness=16,
                color=FRONTLINE_COLORS,
                line_style=LineStyle.Triangle,
            )
            shape.name = front_line.name

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
    def _support_orbit_radius(flight: "FlightData") -> float:
        """Half-width of the drawn capsule, from the flight's own orbit speed."""
        from game.ato.flightplans.tacticaloverlay import orbit_radius

        speed = getattr(flight, "patrol_speed", None)
        if speed is None:
            return SUPPORT_ORBIT_MIN_RADIUS_M
        turn = orbit_radius(speed, SUPPORT_ORBIT_TURN_BANK_DEG).meters
        return max(SUPPORT_ORBIT_MIN_RADIUS_M, turn + SUPPORT_ORBIT_TURN_PAD_M)

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
        self._generate_cap_station_orbits()
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
            radius = self._support_orbit_radius(flight)
            if start.distance_to_point(end) < 1.0:
                shape = self.player_layer.add_circle(
                    start,
                    radius,
                    line_thickness=6,
                    color=SUPPORT_ORBIT_LINE,
                    fill=SUPPORT_ORBIT_FILL,
                    line_style=LineStyle.Dash,
                )
            else:
                shape = self.player_layer.add_oblong(
                    start,
                    end,
                    radius,
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

    def _generate_cap_station_orbits(self) -> None:
        """Paint each blue CAP *station* as a thin racetrack on the F10 map.

        The Hornet's SA page displays only the *selected* DTC CAP point (flown
        2026-07-19), so the F10 map is the one display that can show the whole
        friendly orbit picture at once. One racetrack per station (the §6 wave
        relief deduped by the §74 helper), drawn thinner than the tanker/AEW&C
        capsules and labelled with the station's callsign.
        """
        assert self.mission_data is not None
        from game.missiongenerator.dtc.common import dedupe_stations, raw_cap_tracks

        # Two stations can share a callsign, and MIST indexes drawings BY NAME --
        # it logs "already exists in DB" and drops every repeat. Number them.
        used: dict[str, int] = {}
        for station in dedupe_stations(raw_cap_tracks(self.mission_data)):
            if station.start.distance_to_point(station.end) < 1.0:
                shape = self.player_layer.add_circle(
                    station.start,
                    SUPPORT_ORBIT_MIN_RADIUS_M,
                    line_thickness=3,
                    color=SUPPORT_ORBIT_LINE,
                    line_style=LineStyle.Dash,
                )
            else:
                shape = self.player_layer.add_oblong(
                    station.start,
                    station.end,
                    SUPPORT_ORBIT_MIN_RADIUS_M,
                    line_thickness=3,
                    color=SUPPORT_ORBIT_LINE,
                    line_style=LineStyle.Dash,
                )
            seen = used.get(station.callsign, 0) + 1
            used[station.callsign] = seen
            name = station.callsign if seen == 1 else f"{station.callsign} {seen}"
            shape.name = f"CAP {name} orbit"
            label = self.player_layer.add_text_box(
                station.start,
                f"CAP {name}",
                color=SUPPORT_LABEL_TEXT,
                fill=SUPPORT_LABEL_FILL,
                font_size=12,
            )
            label.name = f"CAP {name} label"

    def generate(self) -> None:
        self.generate_frontlines_drawing()
        self.generate_routes()
        self.generate_cps_markers()
        self.generate_support_orbits()
