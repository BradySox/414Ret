"""Ground objects sitting on an airfield's runway strip or apron.

DCS holds every AI fixed-wing taxi at a field that has a ground unit on its runway strip
or apron: the §1 backstop-EWR lesson, then Long Road to H3's own Incirlik EWR marker on
2026-09-16 (265 m off the centreline, on the south-west taxiway; the DM had to hand-move
it before anything would taxi) and, most likely, Al Qusayr's garrison armor the same day.
pydcs carries a runway's heading and the parking slots but not the taxiway geometry or the
runway length, so this is a band around the centreline plus a radius around every slot,
not a polygon. It warns and never moves anything: an authored marker is the campaign
author's call, and the warning names the group and the field so the marker can be moved.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Iterator

if TYPE_CHECKING:
    from game.theater import ConflictTheater

#: Half of a 3.2 km runway. Incirlik's 3,048 m runway has a SAM marker 1,766 m out on
#: the approach that never blocked a taxi, so the band stops short of the overruns.
RUNWAY_HALF_LENGTH_M = 1600.0
#: The parallel taxiway sits inside this on every field measured (Incirlik 265 m,
#: Al Qusayr 293 m, Tabqa 265 m).
RUNWAY_STRIP_HALF_WIDTH_M = 300.0
#: A ground unit this close to a stand blocks the aircraft on it.
PARKING_CLEARANCE_M = 80.0
#: Only objects this close to a field are worth measuring against it.
SEARCH_RADIUS_M = 4000.0


@dataclass(frozen=True)
class AirfieldClearanceConflict:
    airfield: str
    ground_object: str
    unit_type: str
    along_m: float
    perp_m: float
    reason: str

    def describe(self) -> str:
        return (
            f"{self.airfield}: {self.ground_object} ({self.unit_type}) sits on the "
            f"{self.reason}, {self.perp_m:.0f} m off the runway centreline and "
            f"{self.along_m:.0f} m along it. A ground unit on the taxiways holds every "
            "AI fixed-wing taxi at the field (§1); the ones that did sat 265-293 m off, "
            "and fields with an object at 264-298 m have also launched, so read the "
            "offset against the field's own layout before moving the marker"
        )


def _iter_ground_units(theater: "ConflictTheater") -> Iterator[tuple[Any, Any]]:
    for cp in theater.controlpoints:
        for tgo in cp.connected_objectives:
            for unit in tgo.units:
                yield tgo, unit


def _runway_offsets(airport: Any, x: float, y: float) -> list[tuple[float, float]]:
    """(along, perp) of a point against each runway centreline through the field."""
    out = []
    for runway in getattr(airport, "runways", []) or []:
        heading = math.radians(float(runway.heading))
        dx, dy = math.cos(heading), math.sin(heading)
        vx, vy = x - airport.position.x, y - airport.position.y
        out.append((vx * dx + vy * dy, vx * dy - vy * dx))
    return out


def airfield_clearance_conflicts(
    theater: "ConflictTheater",
) -> list[AirfieldClearanceConflict]:
    """Every (airfield, ground object) pair where a unit sits on the strip or a stand."""
    conflicts: list[AirfieldClearanceConflict] = []
    for cp in theater.controlpoints:
        airport = getattr(cp, "airport", None)
        if airport is None or not getattr(airport, "runways", None):
            continue
        seen: set[str] = set()
        for tgo, unit in _iter_ground_units(theater):
            if tgo.name in seen:
                continue
            ux, uy = unit.position.x, unit.position.y
            if (
                math.hypot(ux - airport.position.x, uy - airport.position.y)
                > SEARCH_RADIUS_M
            ):
                continue
            reason = None
            along = perp = 0.0
            for along, perp in _runway_offsets(airport, ux, uy):
                if (
                    abs(perp) < RUNWAY_STRIP_HALF_WIDTH_M
                    and abs(along) < RUNWAY_HALF_LENGTH_M
                ):
                    reason = "runway strip"
                    break
            if reason is None:
                for slot in getattr(airport, "parking_slots", []) or []:
                    if (
                        math.hypot(ux - slot.position.x, uy - slot.position.y)
                        < PARKING_CLEARANCE_M
                    ):
                        reason = "apron"
                        offsets = _runway_offsets(airport, ux, uy)
                        along, perp = offsets[0] if offsets else (0.0, 0.0)
                        break
            if reason is None:
                continue
            seen.add(tgo.name)
            unit_type = getattr(getattr(unit, "type", None), "id", None) or str(
                getattr(unit, "type", "?")
            )
            conflicts.append(
                AirfieldClearanceConflict(
                    airfield=cp.name,
                    ground_object=tgo.name,
                    unit_type=str(unit_type),
                    along_m=along,
                    perp_m=perp,
                    reason=reason,
                )
            )
    return conflicts


def log_airfield_clearance_conflicts(theater: "ConflictTheater") -> None:
    for conflict in airfield_clearance_conflicts(theater):
        logging.warning("Airfield clearance: %s", conflict.describe())
