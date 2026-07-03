from dcs import Point
from dcs.drawing import LineStyle, Rgba
from dcs.drawing.drawings import StandardLayer
from dcs.mission import Mission

from game import Game
from game.missiongenerator.frontlineconflictdescription import (
    FrontLineConflictDescription,
)

# Misc config settings for objects drawn in ME mission file (and F10 map)
from game.theater import TRIGGER_RADIUS_CAPTURE

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


class DrawingsGenerator:
    """
    Generate drawn objects for the F10 map and mission editor
    """

    def __init__(self, mission: Mission, game: Game) -> None:
        self.mission = mission
        self.game = game
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

    def generate_restricted_zones(self) -> None:
        """Paint the active phase's ROE zones (circle / box / corridor).

        Reads the same resolved zones the web map layer draws, so the F10 map and
        the client show the identical geometry. No-op outside an authored ROE phase
        (the list is empty) -- non-ROE campaigns see nothing new.
        """
        from game.fourteenth.phases import active_restricted_zones

        for zone in active_restricted_zones(self.game):
            if zone.kind == "circle":
                shape = self.player_layer.add_circle(
                    self.game.point_in_world(*zone.center_xy),
                    zone.radius_m,
                    line_thickness=4,
                    color=ROE_ZONE_LINE,
                    fill=ROE_ZONE_FILL,
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
                    color=ROE_ZONE_LINE,
                    fill=ROE_ZONE_FILL,
                    line_style=LineStyle.Dash,
                )
            shape.name = zone.name

    def generate(self) -> None:
        self.generate_frontlines_drawing()
        self.generate_routes()
        self.generate_cps_markers()
        self.generate_restricted_zones()
