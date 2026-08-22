"""F-14B(U) DTC cartridge builder (§74).

Schema mined from ``CoreMods/aircraft/F14/DTC`` (``F-14BU_DTC.lua`` + its
``.dlg``). Sections emitted:

* ``NAV`` -- plan 1 takes the reference layer only (the front line as map lines;
  bullseye, divert, friendly orbits and known threat sites as additional points).
  Its **waypoint list is not ours to write**: plan 1 is the ME route, which is
  already this flight's miz route, and the editor greys those fields out
  (``updateNAVPlanEditability``). The flown route goes on **plan 2**, which is
  what an authored cartridge does -- see the design note's diff.
* ``JDAM`` -- the flight's target waypoints as pre-planned points on all four
  stations, with the run-in heading and the cached LAR scalars.
* ``TIS`` -- the package's callsigns in the send-to list.

Constraints mined, not guessed, each easy to undo by accident: ``NAV``
elevations are FEET while ``JDAM`` target elevations are METRES; point names cap
at 8 characters and the trailing ``X`` codes (``XB``, ``XD``, ``XHB``, ``XIP``)
are a convention the jet reads, documented in the NAV tab and used by the
authored cartridge; and the jet is the F-14B(U) alone, since
``F14/Entry/F-14B.lua`` sets the capability flag only for that rewrite.

Every section is always written, ``CMDS`` included, because this descriptor
cannot take a partial cartridge: ``setData`` ends with ``init_CMDS()``, which
indexes ``data.CMDS.CMDSProgramSettings`` unconditionally, and a missing section
crashes the whole post-import refresh (ME-proven 2026-08-22). A section the
planner turned off carries the editor's own reset state instead; ``CMDS`` is
ED's stock table verbatim, which is what the editor saves for an untouched
cartridge.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, Optional

from game.ato.flightwaypointtype import FlightWaypointType
from game.missiongenerator.dtc.cartridge import DtcCartridge
from game.missiongenerator.dtc.common import (
    SupportTrack,
    bearing_degrees,
    flot_segments,
    is_route_waypoint,
    is_target_waypoint,
    known_enemy_threat_sites,
    leg_altitude,
    leg_speed_kmh,
    own_orbit_track,
    sanitize_short_name,
    seconds_of_day,
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
#: Plan 2's label, matching the ED-authored cartridge this was checked against.
ROUTE_PLAN_NAME = "ROUTE 1"

JDAM_STATIONS = 4
JDAM_TARGETS_PER_STATION = 8
DEFAULT_DROP_ALT_FT = 20000.0
DEFAULT_DROP_SPD_KTS = 450.0
#: Below this a planned altitude is no release altitude and the ingress
#: leg's is used instead.
MIN_DROP_ALT_FT = 1000.0

TIS_CALLSIGN_LEN = 6


def _dispenser(
    burst: int, interval: float, salvo: int, salvo_interval: float
) -> dict[str, Any]:
    return {
        "BurstQuantity": burst,
        "BurstInterval": interval,
        "SalvoQuantity": salvo,
        "SalvoInterval": salvo_interval,
    }


_NO_DISPENSE = _dispenser(0, 0, 0, 0)


def _program(
    priority: int, chaff: dict[str, Any], flare: dict[str, Any]
) -> dict[str, Any]:
    return {
        "Priority": priority,
        "Chaff": chaff,
        "Flare": flare,
        "Other1": dict(_NO_DISPENSE),
        "Other2": dict(_NO_DISPENSE),
    }


#: The descriptor's ``CMDS`` table, as the editor serializes it for an untouched
#: cartridge. ED's tuning, carried so ``init_CMDS`` has something to read -- not
#: a place for campaign values.
_CMDS_DEFAULTS: dict[str, Any] = {
    "CMDSBingoSettings": {
        "ChaffNum": 10,
        "FlaresNum": 10,
        "Other1Num": 0,
        "Other2Num": 0,
    },
    "CMDSAutoPrograms": {
        "SAM": {"Program": 5, "Threshold": 3},
        "AAA": {"Program": 2, "Threshold": 2},
        "Aircraft": {"Program": 4, "Threshold": 3},
        "Naval": {"Program": 5, "Threshold": 3},
        "Unknown": {"Program": 4, "Threshold": 3},
    },
    "CMDSAutoOverrides": [],
    "CMDSProgramSettings": {
        "PROG_1": _program(2, _dispenser(2, 0.2, 8, 1), _dispenser(2, 0.5, 8, 1)),
        "PROG_2": _program(0, _dispenser(3, 0.25, 3, 2), _dispenser(1, 1, 1, 1)),
        "PROG_3": _program(0, _dispenser(1, 1, 1, 1), _dispenser(2, 0.5, 4, 3)),
        "PROG_4": _program(0, _dispenser(2, 0.25, 4, 3), _dispenser(1, 1, 4, 3)),
        "PROG_5": _program(1, _dispenser(4, 0.2, 4, 2), _dispenser(1, 1, 2, 2)),
        "PROG_6": _program(1, _dispenser(1, 1, 2, 2), _dispenser(2, 0.5, 6, 2)),
        "PROG_7": _program(0, _dispenser(1, 1, 1, 1), _dispenser(1, 1, 1, 1)),
        "PROG_8": _program(0, _dispenser(1, 1, 1, 1), _dispenser(1, 1, 1, 1)),
    },
}

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


def _whole(value: float) -> Any:
    """Match the editor's own output, which writes 20000 rather than 20000.0."""
    return int(value) if float(value).is_integer() else value


def _knots(speed_kmh: float) -> float:
    return speed_kmh * _KMH_TO_KNOTS


def _zulu_clock(game: Game, waypoint: FlightWaypoint) -> str:
    """The waypoint's TOT as the editor's ``HH:MM:SS`` clock, in Zulu.

    Hours wrap at 24: the field is a clock face, so a sortie crossing Zulu
    midnight loses the day rather than writing an hour the jet cannot show.
    """
    if waypoint.tot is None:
        return ""
    total = seconds_of_day(game, waypoint.tot)
    return f"{(total // 3600) % 24:02d}:{(total % 3600) // 60:02d}:{total % 60:02d}"


def _point_name(waypoint: FlightWaypoint) -> str:
    """``TARGETAR`` -- what the authored cartridge's names look like.

    The descriptor only truncates, but every name in a real cartridge is bare
    uppercase alphanumerics, and the CDNU has no lower case. Retribution's own
    labels arrive as "Target area" and "Join - Point", which would reach the
    cockpit with their spaces and dashes intact.
    """
    folded = waypoint_display_name(waypoint.display_name or waypoint.name)
    return sanitize_short_name(folded, WAYPOINT_NAME_LEN)


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


#: Waypoint types and the jet's name code for each. Only the four codes the NAV
#: tab documents unambiguously are used -- an ED-authored cartridge in hand names
#: its initial point ``IPORCXIP``, so the grammar is real, but ``DP``/``HA``/``ST``
#: have no stated meaning and guessing one would be an unsourced value.
_NAME_SUFFIXES = {
    FlightWaypointType.BULLSEYE: "XB",
    FlightWaypointType.DIVERT: "XD",
    FlightWaypointType.LANDING_POINT: "XHB",
}
_NAME_SUFFIXES.update(
    {
        member: "XIP"
        for member in FlightWaypointType
        if member.name.startswith("INGRESS_")
    }
)


def _coded_name(waypoint: FlightWaypoint) -> str:
    suffix = _NAME_SUFFIXES.get(waypoint.waypoint_type)
    base = _point_name(waypoint)
    return _suffixed(base, suffix) if suffix else base


def _threat_name(label: str) -> str:
    """``SA10`` for a numeric SA-page label, the label itself otherwise."""
    return f"SA{label}" if label.isdigit() else label


def _orbit_tracks(flight: FlightData, mission_data: MissionData) -> list[SupportTrack]:
    """This flight's own orbit (racetrack or hold point), then the tankers and
    AEW&C. Other flights' CAP stations are not this jet's business, and the
    20-reference budget runs out."""
    own = own_orbit_track(flight)
    return ([own] if own is not None else []) + support_tracks(mission_data)


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
            _coded_name(waypoint),
            waypoint.position.x,
            waypoint.position.y,
        )
        for waypoint in off_route
    ]
    if options.friendly_orbits:
        for track in _orbit_tracks(flight, mission_data):
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


def _waypoint_elevation(waypoint: FlightWaypoint, game: Game) -> int:
    """Feet for the waypoint's single altitude field, which is not the Hornet's.

    The Tomcat waypoint has one number where the other jets have two (ground
    under the point, and the height to fly the leg), so it cannot carry both.
    The authored cartridge fills it the way this does: the field's own elevation
    at the ends of the route, the planned altitude in between. A ground-marked
    point keeps 0, which is what it is planned at.
    """
    ground = steerpoint_elevation(waypoint, game)
    if ground:
        return _feet(ground)
    altitude_m, _ = leg_altitude(waypoint, game)
    return _feet(altitude_m)


def _route_waypoint(
    game: Game,
    coords: _Coords,
    waypoint: FlightWaypoint,
    previous: Optional[FlightWaypoint],
) -> dict[str, Any]:
    tot = _zulu_clock(game, waypoint)
    entry: dict[str, Any] = {"name": _coded_name(waypoint)}
    entry.update(
        coords.of(
            waypoint.position.x,
            waypoint.position.y,
            _waypoint_elevation(waypoint, game),
        )
    )
    # Speed and TOT are mutually exclusive in the editor. The planned time wins
    # where there is one, because that is what the package flies to.
    entry["spd"] = 0 if tot else int(round(_knots(leg_speed_kmh(previous, waypoint))))
    entry["tot"] = tot
    return entry


def _build_nav(
    flight: FlightData, mission_data: MissionData, game: Game, coords: _Coords
) -> list[dict[str, Any]]:
    """Twelve plans, of which we fill two.

    **Plan 1 keeps its own waypoints**: the editor labels it "1: ME Route" while
    its name is empty and greys the waypoint fields out
    (``updateNAVPlanEditability``), because those waypoints ARE the miz route DCS
    already flies. It takes the reference layer only -- lines and additional
    points, the two things it accepts and a route cannot express.

    **Plan 2 is the flown route**, which is the shape an ED-authored cartridge in
    hand uses: named waypoints with TOTs, ``route_as_line`` set so the plan draws
    itself, and the reference layer repeated so selecting it loses nothing.
    """
    options = flight.dtc_options
    plans = [_empty_plan() for _ in range(MAX_PLANS)]
    off_route = (
        [w for w in flight.waypoints if not is_route_waypoint(w)]
        if options.route
        else []
    )
    lines = _lines(game, coords) if options.flot_and_zones else []
    references = _additional_points(flight, mission_data, game, coords, off_route)
    plans[0]["lines"] = list(lines)
    plans[0]["additional_points"] = list(references)
    if not options.route:
        return plans

    route = plans[1]
    route["name"] = ROUTE_PLAN_NAME
    route["route_as_line"] = True
    route["lines"] = list(lines)
    route["additional_points"] = list(references)
    # Skip waypoint 0 (the spawn) so plan 2's waypoint n IS the kneeboard's
    # waypoint n -- the same off-by-one the Hornet hit.
    previous: Optional[FlightWaypoint] = None
    for waypoint in flight.waypoints[1:]:
        if not is_route_waypoint(waypoint):
            continue
        if len(route["waypoints"]) == MAX_WAYPOINTS:
            break
        route["waypoints"].append(_route_waypoint(game, coords, waypoint, previous))
        previous = waypoint
    return plans


def _jdam_target(
    coords: _Coords,
    game: Optional[Game] = None,
    waypoint: Optional[FlightWaypoint] = None,
    ingress: Optional[FlightWaypoint] = None,
) -> dict[str, Any]:
    """One pre-planned point, or the module's empty slot when there is none."""
    drop_alt = DEFAULT_DROP_ALT_FT
    drop_speed = DEFAULT_DROP_SPD_KTS
    target: dict[str, Any] = {
        "name": "",
        "elev": 0,
        "attack_heading": 0.0,
        "has_impact_heading": False,
        "impact_heading": 0,
        "has_impact_angle": False,
        "impact_angle": 65,
        "active": False,
    }
    if waypoint is not None:
        assert game is not None
        # A ground-marked target's own altitude is the ground; the release
        # altitude is the ingress leg's.
        release_from = ingress if waypoint.marks_ground_for_player else waypoint
        planned_alt_ft = (
            _feet(leg_altitude(release_from, game)[0]) if release_from else 0
        )
        if planned_alt_ft < MIN_DROP_ALT_FT and ingress is not None:
            planned_alt_ft = _feet(leg_altitude(ingress, game)[0])
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
                "elev": _whole(steerpoint_elevation(waypoint, game)),
                "attack_heading": (
                    round(bearing_degrees(ingress.position, waypoint.position), 1)
                    % 360.0
                    if ingress is not None
                    else 0.0
                ),
                "active": True,
            }
        )
    rmin, rmax, half_angle = lookup_jdam_lar(drop_speed, drop_alt / 1000)
    target["drop_alt"] = _whole(drop_alt)
    target["drop_spd"] = round(drop_speed)
    target["lar_rmin_nmi"] = rmin
    target["lar_rmax_nmi"] = rmax
    target["lar_half_angle_deg"] = half_angle
    return target


def _build_jdam(flight: FlightData, game: Game, coords: _Coords) -> dict[str, Any]:
    """Every station gets the same ordered list, so any bomb can take any
    planned point -- the crew picks the index; we do not guess the fit."""
    planned: list[dict[str, Any]] = []
    previous: Optional[FlightWaypoint] = None
    for waypoint in flight.waypoints:
        is_target = is_target_waypoint(waypoint)
        if is_target and len(planned) < JDAM_TARGETS_PER_STATION:
            planned.append(_jdam_target(coords, game, waypoint, previous))
        if is_route_waypoint(waypoint):
            previous = waypoint
    targets = planned + [
        _jdam_target(coords) for _ in range(JDAM_TARGETS_PER_STATION - len(planned))
    ]
    return {"stations": [{"targets": list(targets)} for _ in range(JDAM_STATIONS)]}


def _tis_callsign(callsign: str) -> str:
    return sanitize_short_name(callsign, TIS_CALLSIGN_LEN).ljust(TIS_CALLSIGN_LEN)


def _tis_defaults(send_to: list[str]) -> dict[str, Any]:
    return {
        "use_mission_callsign": True,
        "own_callsign": " " * TIS_CALLSIGN_LEN,
        "add_wingmen_to_list": True,
        "send_to_callsigns": send_to,
    }


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
    return _tis_defaults(send_to)


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
    # Unlike the Hornet and Viper, a section the planner turned off cannot be
    # omitted -- the descriptor's post-import refresh indexes every section.
    # It carries the editor's reset state instead, which is what the jet would
    # have had anyway (the §74 Edit Flight DTC tab).
    if any(getattr(options, option) for option in _NAV_OPTIONS):
        data["NAV"] = _build_nav(flight, mission_data, game, coords)
    else:
        data["NAV"] = [_empty_plan() for _ in range(MAX_PLANS)]
    if options.jdam_targets:
        data["JDAM"] = _build_jdam(flight, game, coords)
    else:
        empty = [_jdam_target(coords) for _ in range(JDAM_TARGETS_PER_STATION)]
        data["JDAM"] = {
            "stations": [{"targets": list(empty)} for _ in range(JDAM_STATIONS)]
        }
    data["TIS"] = (
        _build_tis(flight, mission_data) if options.comms else _tis_defaults([])
    )
    data["CMDS"] = _CMDS_DEFAULTS
    return DtcCartridge(
        name=name,
        unit_type=TOMCAT_UNIT_TYPE,
        terrain=game.theater.terrain.name,
        data=data,
    )
