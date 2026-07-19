"""F-16C DTC cartridge builder (§74).

Sections emitted (schema mined from ``CoreMods/aircraft/F-16C/DTC``):

* ``COMM`` -- COM1 (UHF) / COM2 (VHF) preset tables mirroring the radio
  allocator's channel numbers. The Viper's DTC channels carry no name field.
* ``MPD.NAV_PTS`` -- steerpoints with TOS + per-leg speed inline (the Viper
  keeps route timing on the point, unlike the Hornet's separate route table),
  named via the ``note`` field; the flight route first, then tanker / AEW&C /
  CAP anchors as extra steerpoints (the SA-page ask, Viper-style -- the jet
  has no orbit element). The ME's DTC editor caps the list at 25.
* ``MPD.GEO_LINES`` -- up to 4 line sets on the HSD: the FLOT (front lines)
  first, then §40 no-strike zone outlines.
* ``MPD.THREAT_PTS`` -- viewer-fogged enemy SAM rings ("Custom" type, radius
  in meters, <= 15).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from game.missiongenerator.dtc.cartridge import DtcCartridge
from game.missiongenerator.dtc.common import (
    SupportTrack,
    cap_tracks,
    client_altitude,
    flot_segments,
    is_route_waypoint,
    is_target_waypoint,
    known_enemy_threat_sites,
    leg_speed_kmh,
    restricted_zone_outlines,
    seconds_of_day,
    support_tracks,
    waypoint_display_name,
)

if TYPE_CHECKING:
    from game import Game
    from game.missiongenerator.aircraft.flightdata import FlightData
    from game.missiongenerator.missiondata import MissionData

VIPER_UNIT_TYPE = "F-16C_50"

MAX_STEERPOINTS = 25
MAX_GEO_LINE_SETS = 4
MAX_GEO_POINTS_PER_SET = 8
MAX_THREAT_POINTS = 15

#: Stock preset frequencies (MHz), from the module's COMM defaults.
_COM1_DEFAULT_FREQS = [
    305.0, 264.0, 265.0, 256.0, 254.0, 250.0, 270.0, 257.0, 255.0, 262.0,
    259.0, 268.0, 269.0, 260.0, 263.0, 261.0, 267.0, 251.0, 253.0, 266.0,
]  # fmt: skip
_COM2_DEFAULT_FREQS = [
    124.0, 135.0, 136.0, 127.0, 125.0, 121.0, 141.0, 128.0, 126.0, 133.0,
    130.0, 139.0, 140.0, 131.0, 134.0, 132.0, 138.0, 122.0, 124.0, 137.0,
]  # fmt: skip

#: The Custom threat type's stock ceiling (meters; 30,000 ft) from
#: THREAT_PTS_defs.
_CUSTOM_THREAT_ALT = 9144


def _default_comm_table(freqs: list[float]) -> dict[str, Any]:
    return {
        f"Channel_{i}": {"freq": freq, "modulation": 1}
        for i, freq in enumerate(freqs, start=1)
    }


def _build_comm(flight: FlightData) -> dict[str, Any]:
    com1 = _default_comm_table(_COM1_DEFAULT_FREQS)
    com2 = _default_comm_table(_COM2_DEFAULT_FREQS)
    tables = {1: com1, 2: com2}
    for frequency, assignments in flight.frequency_to_channel_map.items():
        for assignment in assignments:
            table = tables.get(assignment.radio_id)
            if table is None or not 1 <= assignment.channel <= 20:
                continue
            table[f"Channel_{assignment.channel}"] = {
                "freq": frequency.mhz,
                "modulation": 1,
            }
    return {
        "COMM1": com1,
        "COMM2": com2,
        "mirror_COMM1": False,
        "mirror_COMM2": False,
    }


def _steerpoint(
    number: int,
    name: str,
    x: float,
    y: float,
    alt_m: float,
    altitude_type: int,
    on_route: bool,
    speed_kmh: float,
    tos: int,
    tos_enabled: bool,
    target: bool,
) -> dict[str, Any]:
    del target  # the Viper marks targets via the route, not a point flag
    return {
        "number": number,
        "id": f"STPT{number}",
        "type": "STPT",
        "note": name,
        "x": x,
        "y": y,
        "alt": alt_m,
        "altitudeType": altitude_type,
        "R1": on_route,
        "R2": False,
        "R3": False,
        "speed": speed_kmh,
        "velocityType": 3,
        "TOS": tos,
        "isTOSEnabled": tos_enabled,
        "FIX_Time": tos_enabled,
        "routeAltitude": alt_m,
        "isOAP_1": False,
        "idOA1": f"OA1{number}",
        "idOA1_Line": f"OA1{number}Line",
        "OAP_1_X": 0,
        "OAP_1_Y": 0,
        "OAP_1_Alt": 0,
        "OAP_1_Bearing": 0,
        "OAP_1_Range": 0,
        "OAP_1_DeltaX": 0,
        "OAP_1_DeltaY": 0,
        "isOAP_2": False,
        "idOA2": f"OA2{number}",
        "idOA2_Line": f"OA2{number}Line",
        "OAP_2_X": 0,
        "OAP_2_Y": 0,
        "OAP_2_Alt": 0,
        "OAP_2_Bearing": 0,
        "OAP_2_Range": 0,
        "OAP_2_DeltaX": 0,
        "OAP_2_DeltaY": 0,
    }


def _anchor_name(track: SupportTrack) -> str:
    return f"{track.kind} {track.callsign}".strip()


def _build_nav_pts(
    flight: FlightData, mission_data: MissionData, game: Game
) -> list[dict[str, Any]]:
    options = flight.dtc_options
    points: list[dict[str, Any]] = []
    prev_route_wp = None
    waypoints = flight.waypoints if options.route else []
    for waypoint in waypoints:
        if len(points) >= MAX_STEERPOINTS:
            return points
        number = len(points) + 1
        on_route = is_route_waypoint(waypoint)
        alt_m, altitude_type = client_altitude(waypoint)
        points.append(
            _steerpoint(
                number,
                waypoint_display_name(waypoint.display_name or waypoint.name),
                waypoint.position.x,
                waypoint.position.y,
                alt_m,
                altitude_type,
                on_route,
                leg_speed_kmh(prev_route_wp if on_route else None, waypoint),
                seconds_of_day(game, waypoint.tot),
                waypoint.tot is not None,
                is_target_waypoint(waypoint),
            )
        )
        if on_route:
            prev_route_wp = waypoint
    # Support anchors after the route: tanker/AEW&C orbits, then CAP stations
    # (the Viper's stand-in for the Hornet's SA racetracks).
    if options.friendly_orbits:
        for track in support_tracks(mission_data) + cap_tracks(mission_data):
            if len(points) >= MAX_STEERPOINTS:
                break
            number = len(points) + 1
            x, y = track.center
            points.append(
                _steerpoint(
                    number,
                    _anchor_name(track),
                    x,
                    y,
                    0.0,
                    1,
                    False,
                    463.0,
                    0,
                    False,
                    False,
                )
            )
    return points


def _build_geo_lines(game: Game) -> list[dict[str, Any]]:
    """FLOT + no-strike outlines across the HSD's four line sets."""
    line_sets: list[tuple[str, list[tuple[float, float]]]] = []
    line_sets.extend(flot_segments(game))
    line_sets.extend(restricted_zone_outlines(game, MAX_GEO_POINTS_PER_SET))
    geo_points: list[dict[str, Any]] = []
    for set_index, (name, points) in enumerate(line_sets[:MAX_GEO_LINE_SETS]):
        flags = {f"L{i}": i == set_index + 1 for i in range(1, 5)}
        for x, y in points[:MAX_GEO_POINTS_PER_SET]:
            number = len(geo_points) + 1
            entry: dict[str, Any] = {
                "number": number,
                "id": f"GEO_LINES{30 + number}",
                "x": x,
                "y": y,
                "alt": 0,
                "note": name,
            }
            entry.update(flags)
            geo_points.append(entry)
    return geo_points


def _build_threat_pts(flight: FlightData, game: Game) -> list[dict[str, Any]]:
    threats: list[dict[str, Any]] = []
    for site in known_enemy_threat_sites(game, flight.friendly)[:MAX_THREAT_POINTS]:
        number = len(threats) + 1
        threats.append(
            {
                "number": number,
                "id": f"THREAT_PTS{55 + number}",
                "x": site.x,
                "y": site.y,
                "threatName": "Custom",
                "radius": site.range_m,
                "alt": _CUSTOM_THREAT_ALT,
                "elev": 0,
                "text": site.label,
                "ring": True,
                "def_num": 1,
            }
        )
    return threats


def build_viper_cartridge(
    flight: FlightData, mission_data: MissionData, game: Game, name: str
) -> DtcCartridge:
    terrain = game.theater.terrain.name
    options = flight.dtc_options
    data: dict[str, Any] = {
        "type": VIPER_UNIT_TYPE,
        "name": name,
        "terrain": terrain,
    }
    # A section the planner turned off is omitted entirely so the jet's own
    # defaults stand (the §74 Edit Flight DTC tab).
    if options.comms:
        data["COMM"] = _build_comm(flight)
    if (
        options.route
        or options.friendly_orbits
        or options.flot_and_zones
        or options.threat_rings
    ):
        data["MPD"] = {
            "terrain": terrain,
            "mirror_NAV_PTS": False,
            "NAV_PTS": _build_nav_pts(flight, mission_data, game),
            "mirror_GEO_LINES": False,
            "GEO_LINES": _build_geo_lines(game) if options.flot_and_zones else [],
            "mirror_THREAT_PTS": False,
            "THREAT_PTS": (
                _build_threat_pts(flight, game) if options.threat_rings else []
            ),
        }
    return DtcCartridge(
        name=name, unit_type=VIPER_UNIT_TYPE, terrain=terrain, data=data
    )
