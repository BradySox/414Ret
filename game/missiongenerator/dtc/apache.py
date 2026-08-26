"""AH-64D BLK.II DTC cartridge builder (§74).

Schema mined from ``CoreMods/aircraft/AH-64D/DTC`` plus an ME-saved cartridge
(2.9.29.27278, the shape audit in the DCS-update design note §3). Sections
emitted, all inside ``NAV.Mission_1``:

* ``Points.WPTHZ`` -- the flight's route as waypoints W01.., named via
  ``note``, ground elevation in ``alt``, map metres in ``x``/``y``.
* ``Routes[1]`` ("ALPHA") -- the route sequence over those waypoints with
  per-leg speed (kts), leg distance and cumulative ETA seconds, the shape the
  editor's own add-point handler writes.
* ``Points.TGT`` -- viewer-fogged enemy SAM sites as target points T01..
  (the TSD has no ring radius; the site name rides ``note``).
* ``Lines`` -- the active front lines (FLOT) as TSD lines.

Partitions the planner computes nothing for (Laser, Radios, Weapon, MISC,
Presets, IDM, ADF, CTRLM, Areas, Zones) are omitted or left empty-but-present
per the sample's skeleton -- the aircraft's own defaults stand, the viper
precedent. ADF stays empty deliberately: the sample's ``Freq`` integers carry
no stated unit, so the CSAR beacon slot (checklist G33) waits on a flown
round-trip before anything writes it.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

from game.missiongenerator.dtc.cartridge import DtcCartridge
from game.missiongenerator.dtc.common import (
    flot_segments,
    is_route_waypoint,
    known_enemy_threat_sites,
    leg_speed_kmh,
    seconds_of_day,
    steerpoint_elevation,
    waypoint_display_name,
)

if TYPE_CHECKING:
    from game import Game
    from game.missiongenerator.aircraft.flightdata import FlightData
    from game.missiongenerator.missiondata import MissionData

APACHE_UNIT_TYPE = "AH-64D_BLK_II"

#: WPTHZ owns waypoints 1-50 (CTRLM takes 51-99).
MAX_WAYPOINTS = 50
#: TGT/THRT points 1-50.
MAX_TARGET_POINTS = 50
#: The TSD line partition ships 15 LINES; keep each to the sample's vertex
#: style rather than guessing a per-line cap.
MAX_LINES = 15
MAX_LINE_VERTICES = 8

#: Symbol ids from the ME-saved sample: 6 = waypoint, 1 = generic target.
_WPTHZ_SYMBOL = 6
_TGT_SYMBOL = 1
#: The sample's line style for a plain TSD line.
_LINE_TYPE = 6

#: The editor's ten route slots, in its own order and spelling (two carry a
#: trailing space in the schema; keep them byte-identical).
_ROUTE_NAMES = [
    "ALPHA",
    "BRAVO",
    "DELTA",
    "ECHO ",
    "HOTEL",
    "INDIA",
    "LIMA ",
    "OSCAR",
    "ROMEO",
    "TANGO",
]


def _nav_point(
    num: int,
    prefix: str,
    symbol: int,
    name: str,
    x: float,
    y: float,
    elevation_m: float,
) -> dict[str, Any]:
    return {
        "num": num,
        "id": symbol,
        "text": f"{prefix}{num:02d}",
        "note": name,
        "x": x,
        "y": y,
        "alt": round(elevation_m),
    }


def _build_waypoints(flight: FlightData, game: Game) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    # Match the kneeboard's numbering: row 0 (takeoff/spawn) is not emitted,
    # so W-number n is kneeboard waypoint n (the Hornet/Viper convention).
    for waypoint in flight.waypoints[1:]:
        if len(points) >= MAX_WAYPOINTS:
            break
        points.append(
            _nav_point(
                len(points) + 1,
                "W",
                _WPTHZ_SYMBOL,
                waypoint_display_name(waypoint.display_name or waypoint.name),
                waypoint.position.x,
                waypoint.position.y,
                steerpoint_elevation(waypoint, game),
            )
        )
    return points


def _build_route(
    flight: FlightData, game: Game, waypoints: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """The ALPHA route over the WPTHZ points, in the editor's own element shape.

    Only waypoints the jet actually flies join the sequence -- an off-route
    point (a briefed reference) stays a WPTHZ entry the crew can direct-to.
    """
    legs: list[dict[str, Any]] = []
    prev_wp = None
    prev_point: dict[str, Any] | None = None
    eta = 0.0
    for waypoint, point in zip(flight.waypoints[1:], waypoints):
        if not is_route_waypoint(waypoint):
            continue
        speed_kts = leg_speed_kmh(prev_wp, waypoint) / 1.852
        if prev_point is None:
            distance = 0.0
            eta = float(seconds_of_day(game, waypoint.tot)) if waypoint.tot else 0.0
        else:
            distance = math.hypot(
                point["x"] - prev_point["x"], point["y"] - prev_point["y"]
            )
            if speed_kts > 0:
                eta += distance / (speed_kts * 0.514)
        legs.append(
            {
                "num": point["num"],
                "alt": point["alt"],
                "speed": round(speed_kts, 1),
                "dist": round(distance, 1),
                "eta": round(eta, 1),
                "fix": False,
            }
        )
        prev_wp = waypoint
        prev_point = point
    return legs


def _build_targets(flight: FlightData, game: Game) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    for site in known_enemy_threat_sites(game, flight.friendly)[:MAX_TARGET_POINTS]:
        points.append(
            _nav_point(
                len(points) + 1,
                "T",
                _TGT_SYMBOL,
                site.name,
                site.x,
                site.y,
                0.0,
            )
        )
    return points


def _build_lines(game: Game) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    for name, points in flot_segments(game)[:MAX_LINES]:
        vertices = [{"x": x, "y": y} for x, y in points[:MAX_LINE_VERTICES]]
        if len(vertices) < 2:
            continue
        lines.append(
            {"note": name, "text": "", "type_num": _LINE_TYPE, "vertices": vertices}
        )
    return lines


def _empty_mission() -> dict[str, Any]:
    return {
        "Points": {
            "WPTHZ": {"isEnabled": True, "POINTS": []},
            "CTRLM": {"isEnabled": True, "POINTS": []},
            "TGT": {"isEnabled": True, "POINTS": []},
        },
        "Routes": [
            {"isEnabled": False, "Name": name, "POINTS": []} for name in _ROUTE_NAMES
        ],
        "Lines": [],
        "Areas": [],
        "Zones": {"NFZ": [], "PFZ": []},
    }


def build_apache_cartridge(
    flight: FlightData, mission_data: MissionData, game: Game, name: str
) -> DtcCartridge:
    terrain = game.theater.terrain.name
    options = flight.dtc_options
    mission = _empty_mission()
    if options.route:
        waypoints = _build_waypoints(flight, game)
        mission["Points"]["WPTHZ"]["POINTS"] = waypoints
        legs = _build_route(flight, game, waypoints)
        if legs:
            mission["Routes"][0]["isEnabled"] = True
            mission["Routes"][0]["POINTS"] = legs
    if options.threat_rings:
        mission["Points"]["TGT"]["POINTS"] = _build_targets(flight, game)
    if options.flot_and_zones:
        mission["Lines"] = _build_lines(game)

    data: dict[str, Any] = {
        "type": APACHE_UNIT_TYPE,
        "name": name,
        "terrain": terrain,
        "NAV": {
            "MissionFile": 1,
            "Mission_1": mission,
            "Mission_2": _empty_mission(),
        },
    }
    return DtcCartridge(
        name=name, unit_type=APACHE_UNIT_TYPE, terrain=terrain, data=data
    )
