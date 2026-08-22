"""F-14B(U) DTC cartridge builder (§74).

Schema mined from ``CoreMods/aircraft/F14/DTC`` (``F-14BU_DTC.lua`` + its
``.dlg``). Sections emitted:

* ``NAV`` -- flight plan 1's map lines (the front line) and additional points
  (bullseye, divert, friendly orbits, known threat sites). Its **waypoint list
  is not ours to write**: plan 1 is the ME route, which is already this
  flight's miz route, and the editor greys the waypoint fields out there
  (``updateNAVPlanEditability``). The reference layer is what the route cannot
  carry, so that is what the cartridge adds.
* ``JDAM`` -- the flight's target waypoints as pre-planned points on all four
  stations, with the run-in heading and the cached LAR scalars.
* ``TIS`` -- the package's callsigns in the send-to list.

Constraints mined, not guessed, each easy to undo by accident: ``NAV``
elevations are FEET while ``JDAM`` target elevations are METRES; point names cap
at 8 characters and the trailing ``X`` codes are a real convention the jet reads
(``XB`` bullseye ref, ``XD`` destination -- the NAV tab's own help text); and the
jet is the F-14B(U) alone, since ``F14/Entry/F-14B.lua`` sets the capability flag
only for that rewrite.

``CMDS`` is deliberately omitted: its programs are ED's tuning and nothing in
the campaign improves on them, so the jet keeps its own.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, Optional

from game.ato.flightwaypointtype import FlightWaypointType
from game.missiongenerator.dtc.cartridge import DtcCartridge
from game.missiongenerator.dtc.common import (
    SupportTrack,
    bearing_degrees,
    dedupe_stations,
    flot_segments,
    is_route_waypoint,
    is_target_waypoint,
    known_enemy_threat_sites,
    leg_altitude,
    leg_speed_kmh,
    raw_cap_tracks,
    sanitize_short_name,
    steerpoint_elevation,
    support_tracks,
    waypoint_display_name,
)

if TYPE_CHECKING:
    from dcs import Point

    from game import Game
    from game.ato.flightwaypoint import FlightWaypoint
    from game.missiongenerator.aircraft.flightdata import FlightData
    from game.missiongenerator.missiondata import MissionData

TOMCAT_UNIT_TYPE = "F-14BU"

MAX_PLANS = 12
MAX_WAYPOINTS = 50
MAX_LINES = 4
MAX_LINE_POINTS = 9
#: The descriptor's ``NAV_MAX_TOTAL_REFS``. Its import path allows 50, but the
#: constant is the authored intent, so off-route references stop at 20.
MAX_ADDITIONAL_POINTS = 20
WAYPOINT_NAME_LEN = 8
PLAN_NAME_LEN = 16

JDAM_STATIONS = 4
JDAM_TARGETS_PER_STATION = 8
DEFAULT_DROP_ALT_FT = 20000.0
DEFAULT_DROP_SPD_KTS = 450.0
#: A ground-marked target waypoint plans on the deck, which is no release
#: altitude; below this the ingress leg's altitude is used instead.
MIN_DROP_ALT_FT = 1000.0

TIS_CALLSIGN_LEN = 6

_METRES_TO_FEET = 3.28084
_KMH_TO_KNOTS = 1 / 1.852

#: JDAM launch-acceptability table, ported from the descriptor's
#: ``JDAM_LAR_TABLE``: rows are altitudes (kft), columns Mach, each cell
#: (Rmin nm, Rmax nm, half-angle deg). The jet reads the cached scalars
#: straight out of the cartridge, so they have to be right at write time.
_LAR_ALTS_KFT = (5.0, 10.0, 20.0, 30.0, 40.0, 50.0)
_LAR_MACHS = (0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2)
_LAR_DATA: tuple[tuple[tuple[float, float, float], ...], ...] = (
    (
        (0.87, 1.50, 20.00), (0.93, 1.95, 24.04), (1.07, 2.52, 23.64),
        (1.21, 3.32, 22.24), (1.35, 4.41, 24.72), (1.52, 5.77, 30.62),
        (1.75, 7.52, 32.31), (1.98, 8.95, 34.52), (2.23, 10.09, 37.22),
    ),
    (
        (0.91, 2.29, 32.77), (1.07, 3.04, 35.12), (1.23, 3.74, 37.15),
        (1.42, 4.95, 36.65), (1.62, 6.36, 35.70), (1.81, 8.01, 34.41),
        (2.01, 9.48, 37.02), (2.22, 10.83, 39.82), (2.47, 12.02, 41.79),
    ),
    (
        (1.71, 3.36, 43.14), (2.09, 3.91, 42.72), (1.85, 5.28, 44.44),
        (1.62, 6.75, 45.00), (1.47, 8.29, 44.95), (2.03, 10.02, 44.38),
        (2.21, 11.69, 44.39), (2.03, 13.33, 44.96), (2.25, 14.80, 45.00),
    ),
    (
        (1.42, 4.99, 45.00), (1.89, 5.40, 45.00), (1.99, 6.06, 45.00),
        (2.08, 7.16, 45.00), (2.16, 8.89, 45.00), (2.37, 10.69, 45.00),
        (2.64, 12.53, 45.00), (2.95, 14.51, 45.00), (3.24, 16.34, 45.00),
    ),
    (
        (1.37, 6.84, 45.00), (1.85, 7.35, 45.00), (2.21, 8.12, 45.00),
        (2.48, 8.88, 45.00), (2.48, 9.52, 45.00), (2.65, 10.18, 45.00),
        (2.97, 10.84, 45.00), (3.29, 13.53, 45.00), (3.61, 16.49, 45.00),
    ),
    (
        (1.64, 10.26, 45.00), (2.12, 10.26, 45.00), (2.45, 10.26, 45.00),
        (2.77, 10.82, 45.00), (3.09, 13.37, 45.00), (3.32, 14.58, 45.00),
        (3.48, 14.58, 45.00), (3.64, 14.71, 45.00), (3.87, 15.27, 45.00),
    ),
)  # fmt: skip


def _bracket(values: tuple[float, ...], value: float) -> tuple[int, int, float]:
    if value <= values[0]:
        return 0, 0, 0.0
    if value >= values[-1]:
        return len(values) - 1, len(values) - 1, 0.0
    for index in range(len(values) - 1):
        if values[index] <= value <= values[index + 1]:
            span = values[index + 1] - values[index]
            return index, index + 1, (value - values[index]) / span
    return len(values) - 1, len(values) - 1, 0.0


def _speed_of_sound_kts(altitude_ft: float) -> float:
    """ISA speed of sound: troposphere lapse below the tropopause, then flat."""
    if altitude_ft < 36089:
        temperature = 288.15 - 0.001981 * altitude_ft
    else:
        temperature = 216.65
    return 38.967 * math.sqrt(temperature)


def lookup_jdam_lar(
    ground_speed_kts: float, altitude_kft: float
) -> tuple[float, float, float]:
    """Rmin (nm), Rmax (nm) and half-angle (deg), bilinear over altitude x Mach."""
    mach = ground_speed_kts / _speed_of_sound_kts(altitude_kft * 1000)
    alt_low, alt_high, alt_t = _bracket(_LAR_ALTS_KFT, altitude_kft)
    mach_low, mach_high, mach_t = _bracket(_LAR_MACHS, mach)

    def interpolate(field: int) -> float:
        def across_mach(alt_index: int) -> float:
            low = _LAR_DATA[alt_index][mach_low][field]
            high = _LAR_DATA[alt_index][mach_high][field]
            return low * (1 - mach_t) + high * mach_t

        return across_mach(alt_low) * (1 - alt_t) + across_mach(alt_high) * alt_t

    return interpolate(0), interpolate(1), interpolate(2)


class _Coords:
    """``x``/``y`` plus the ``lat``/``lon`` the editor writes beside them.

    Every point the ME places carries both, and which pair the jet reads is its
    business, so emit both. A reference point off the flight's own route is the
    only way to reach the terrain's projection from a bare ``(x, y)``; without
    one the lat/lon keys are left out rather than written as zeroes.
    """

    def __init__(self, reference: Optional[Point]) -> None:
        self._reference = reference

    def of(self, x: float, y: float, elevation_ft: int = 0) -> dict[str, Any]:
        block: dict[str, Any] = {"x": x, "y": y}
        if self._reference is not None:
            latlng = self._reference.new_in_same_map(x, y).latlng()
            block["lat"] = latlng.lat
            block["lon"] = latlng.lng
        block["elev"] = elevation_ft
        return block


def _feet(metres: float) -> int:
    return int(round(metres * _METRES_TO_FEET))


def _knots(speed_kmh: float) -> float:
    return speed_kmh * _KMH_TO_KNOTS


def _point_name(waypoint: FlightWaypoint) -> str:
    return waypoint_display_name(
        waypoint.display_name or waypoint.name, WAYPOINT_NAME_LEN
    )


def _empty_plan() -> dict[str, Any]:
    return {
        "name": "",
        "waypoints": [],
        "lines": [],
        "additional_points": [],
        "route_as_line": False,
    }


def _suffixed(base: str, suffix: str) -> str:
    """``BULLSXB`` -- the jet's own point-type convention, trimmed to fit.

    The NAV tab documents trailing ``X`` codes that type a point for the crew
    (``XB`` bullseye ref, ``XD`` destination); the base name gives way, not the
    code, because the code is the part the jet reads.
    """
    return base[: WAYPOINT_NAME_LEN - len(suffix)] + suffix


def _reference(coords: _Coords, name: str, x: float, y: float) -> dict[str, Any]:
    entry: dict[str, Any] = {"name": name[:WAYPOINT_NAME_LEN]}
    entry.update(coords.of(x, y))
    return entry


#: Off-route waypoint types and the jet's name code for each.
_REFERENCE_SUFFIXES = {
    FlightWaypointType.BULLSEYE: "XB",
    FlightWaypointType.DIVERT: "XD",
}


def _off_route_name(waypoint: FlightWaypoint) -> str:
    suffix = _REFERENCE_SUFFIXES.get(waypoint.waypoint_type)
    base = _point_name(waypoint)
    return _suffixed(base, suffix) if suffix else base


def _threat_name(label: str) -> str:
    """``SA10`` for a numeric SA-page label, the label itself otherwise."""
    return f"SA{label}" if label.isdigit() else label


def _orbit_tracks(mission_data: MissionData) -> list[SupportTrack]:
    """Tankers and AEW&C first: a fighter wants the basket before the CAP
    stations, and the 20-reference budget runs out."""
    return support_tracks(mission_data) + dedupe_stations(raw_cap_tracks(mission_data))


def _additional_points(
    flight: FlightData,
    mission_data: MissionData,
    game: Game,
    coords: _Coords,
    off_route: list[FlightWaypoint],
) -> list[dict[str, Any]]:
    options = flight.dtc_options
    points = [
        _reference(
            coords,
            _off_route_name(waypoint),
            waypoint.position.x,
            waypoint.position.y,
        )
        for waypoint in off_route
    ]
    if options.friendly_orbits:
        for track in _orbit_tracks(mission_data):
            centre_x, centre_y = track.center
            points.append(_reference(coords, track.callsign, centre_x, centre_y))
    if options.threat_rings:
        for site in known_enemy_threat_sites(game, flight.friendly):
            points.append(_reference(coords, _threat_name(site.label), site.x, site.y))
    return points[:MAX_ADDITIONAL_POINTS]


def _lines(game: Game, coords: _Coords) -> list[dict[str, Any]]:
    lines = []
    for _name, segment in flot_segments(game)[:MAX_LINES]:
        points = [coords.of(x, y) for x, y in segment[:MAX_LINE_POINTS]]
        lines.append({"points": points, "closed": False})
    return lines


def _build_nav(
    flight: FlightData, mission_data: MissionData, game: Game, coords: _Coords
) -> list[dict[str, Any]]:
    """The twelve plans, of which we fill one.

    Plan 1's ``name`` and ``waypoints`` are deliberately left alone: the editor
    labels it "1: ME Route" while the name is empty, and its waypoints ARE the
    miz route DCS already flies (``updateNAVPlanEditability`` greys the fields
    out for exactly that reason). Lines and additional points are what plan 1
    accepts and what a route cannot express.
    """
    options = flight.dtc_options
    plans = [_empty_plan() for _ in range(MAX_PLANS)]
    plan = plans[0]
    off_route = (
        [w for w in flight.waypoints if not is_route_waypoint(w)]
        if options.route
        else []
    )
    if options.flot_and_zones:
        plan["lines"] = _lines(game, coords)
    plan["additional_points"] = _additional_points(
        flight, mission_data, game, coords, off_route
    )
    return plans


def _jdam_target(
    coords: _Coords,
    waypoint: Optional[FlightWaypoint] = None,
    ingress: Optional[FlightWaypoint] = None,
) -> dict[str, Any]:
    """One pre-planned point, or the module's empty slot when there is none."""
    drop_alt = DEFAULT_DROP_ALT_FT
    drop_speed = DEFAULT_DROP_SPD_KTS
    target: dict[str, Any] = {
        "name": "",
        "elev": 0.0,
        "attack_heading": 0.0,
        "has_impact_heading": False,
        "impact_heading": 0,
        "has_impact_angle": False,
        "impact_angle": 65,
        "active": False,
    }
    if waypoint is not None:
        planned_alt_ft = _feet(leg_altitude(waypoint)[0])
        if planned_alt_ft < MIN_DROP_ALT_FT and ingress is not None:
            planned_alt_ft = _feet(leg_altitude(ingress)[0])
        if planned_alt_ft >= MIN_DROP_ALT_FT:
            drop_alt = float(planned_alt_ft)
        if ingress is not None:
            drop_speed = _knots(leg_speed_kmh(ingress, waypoint))
        target.update(coords.of(waypoint.position.x, waypoint.position.y))
        target.update(
            {
                "name": _point_name(waypoint),
                # Metres here, unlike NAV's feet: the descriptor stores the raw
                # getAltitude() and converts only for display.
                "elev": steerpoint_elevation(waypoint),
                "attack_heading": (
                    round(bearing_degrees(ingress.position, waypoint.position), 1)
                    if ingress is not None
                    else 0.0
                ),
                "active": True,
            }
        )
    rmin, rmax, half_angle = lookup_jdam_lar(drop_speed, drop_alt / 1000)
    target["drop_alt"] = drop_alt
    target["drop_spd"] = round(drop_speed)
    target["lar_rmin_nmi"] = rmin
    target["lar_rmax_nmi"] = rmax
    target["lar_half_angle_deg"] = half_angle
    return target


def _build_jdam(flight: FlightData, coords: _Coords) -> dict[str, Any]:
    """Every station gets the same ordered list, so any bomb can take any
    planned point -- the crew picks the index; we do not guess the fit."""
    planned: list[dict[str, Any]] = []
    previous: Optional[FlightWaypoint] = None
    for waypoint in flight.waypoints:
        if is_target_waypoint(waypoint) and len(planned) < JDAM_TARGETS_PER_STATION:
            planned.append(_jdam_target(coords, waypoint, previous))
        if is_route_waypoint(waypoint):
            previous = waypoint
    targets = planned + [
        _jdam_target(coords) for _ in range(JDAM_TARGETS_PER_STATION - len(planned))
    ]
    return {"stations": [{"targets": list(targets)} for _ in range(JDAM_STATIONS)]}


def _tis_callsign(callsign: str) -> str:
    return sanitize_short_name(callsign, TIS_CALLSIGN_LEN).ljust(TIS_CALLSIGN_LEN)


def _build_tis(flight: FlightData, mission_data: MissionData) -> dict[str, Any]:
    """The package's other flights, so the RIO can pass tracks without typing a
    callsign in. Wingmen ride the module's own union, not this list."""
    send_to: list[str] = []
    for other in mission_data.flights:
        if other is flight or other.package is not flight.package:
            continue
        if not other.friendly.is_blue:
            continue
        callsign = _tis_callsign(other.callsign)
        if callsign.strip() and callsign not in send_to:
            send_to.append(callsign)
    return {
        "use_mission_callsign": True,
        "own_callsign": " " * TIS_CALLSIGN_LEN,
        "add_wingmen_to_list": True,
        "send_to_callsigns": send_to,
    }


#: Options that put something in the NAV section. ``nav_aids`` and
#: ``destinations`` have no Tomcat equivalent and are ignored here.
_NAV_OPTIONS = ("route", "flot_and_zones", "friendly_orbits", "threat_rings")


def build_tomcat_cartridge(
    flight: FlightData, mission_data: MissionData, game: Game, name: str
) -> DtcCartridge:
    options = flight.dtc_options
    reference = flight.waypoints[0].position if flight.waypoints else None
    coords = _Coords(reference)
    data: dict[str, Any] = {
        "type": TOMCAT_UNIT_TYPE,
        "name": name,
        # The label the CDNU shows for the loaded cartridge.
        "cartridge_name": sanitize_short_name(flight.callsign, PLAN_NAME_LEN),
    }
    # A section the planner turned off is omitted entirely so the jet's own
    # defaults stand (the §74 Edit Flight DTC tab).
    if any(getattr(options, option) for option in _NAV_OPTIONS):
        data["NAV"] = _build_nav(flight, mission_data, game, coords)
    if options.jdam_targets:
        data["JDAM"] = _build_jdam(flight, coords)
    if options.comms:
        data["TIS"] = _build_tis(flight, mission_data)
    return DtcCartridge(
        name=name,
        unit_type=TOMCAT_UNIT_TYPE,
        terrain=game.theater.terrain.name,
        data=data,
    )
