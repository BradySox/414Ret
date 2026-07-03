"""Author campaign ``supply_routes:`` that follow real driveable corridors.

**The standard (2026-07-03, user directive):** a drawn supply line must trace the
corridor you would actually *drive* between the two points -- the road, the river
valley, the mountain pass -- never a straight line across a ridgeline. The endpoints
stay on the control points (Retribution's ``add_yaml_supply_routes`` binds a route to
its CPs by the **first and last** waypoint only, so intermediates never change which
bases the route connects -- they are purely the corridor shape the convoy drives and
the line the player sees).

DCS's own road graph (``terrain.city_graph``) ships empty in the release pydcs, so we
cannot A* the roads programmatically here. But every modern DCS map is
**real-world-coordinate**, so the faithful method is to trace the real road network by
its real latitude/longitude and convert each junction to terrain XY -- the drawn line
then lands on the actual roads/valleys of the satellite base layer. Calibration on
Afghanistan: real town lat/lons convert to within ~1-5 km of the hand-placed FOB
markers, so this is accurate to well inside a route's width.

Usage: define a terrain + a list of :class:`Route` (endpoints as exact CP/marker XY,
intermediate corridor points as real ``(lat, lon)``) and run to emit the YAML block.
The COIN campaign's routes are defined below as the reference application; re-run and
paste the output into ``resources/campaigns/coin_enduring_resolve.yaml``.

    python tools/supply_route_geo.py
"""

from __future__ import annotations

from dataclasses import dataclass, field

from dcs.mapping import LatLng, Point
from dcs.terrain.afghanistan import Afghanistan


@dataclass
class Route:
    """One supply corridor. ``start``/``end`` are exact terrain XY (kept verbatim so
    CP binding is stable); ``corridor`` is the real road path between them as
    ``(lat, lon)`` junctions, in travel order."""

    comment: str
    start: tuple[float, float]
    corridor: list[tuple[float, float]]
    end: tuple[float, float]
    labels: list[str] = field(default_factory=list)


def latlon_to_xy(terrain: object, lat: float, lon: float) -> tuple[float, float]:
    p = Point.from_latlng(LatLng(lat, lon), terrain)  # type: ignore[arg-type]
    return (round(p.x), round(p.y))


def render(terrain: object, routes: list[Route]) -> str:
    lines = ["supply_routes:"]
    for route in routes:
        lines.append(f"  # {route.comment}")
        lines.append("  - waypoints:")
        pts: list[tuple[float, float]] = [route.start]
        pts += [latlon_to_xy(terrain, lat, lon) for lat, lon in route.corridor]
        pts.append(route.end)
        for (x, y), label in zip(pts, route.labels or [""] * len(pts)):
            suffix = f" #{label}" if label else ""
            lines.append(f"      - [{round(x)}, {round(y)}]{suffix}")
    return "\n".join(lines) + "\n"


# --- The COIN campaign (Operation Enduring Resolve): exact FOB marker XY endpoints,
# --- real Helmand/Kandahar/Uruzgan road corridors between them. Roads: Highway 1
# --- (the paved Ring Road, Farah-Delaram-Gereshk-Kandahar), Route 611 (up the
# --- Helmand River valley, Gereshk-Sangin-Kajaki), and the Uruzgan road
# --- (Kandahar-Tarin Kowt through the mountain valleys).
FARAH = (-178644.0, -378451.0)
DELARAM = (-203597.0, -258944.0)
NOWZAD = (-174184.0, -162657.0)  # ANP Hill
SANGIN = (-209298.0, -127205.0)  # FOB Jackson
KAJAKI = (-181518.0, -101421.0)  # FOB Zeebrugge
HADRIAN = (-146856.0, -66510.0)
COBRA = (-111672.0, -60214.0)
FRONTENAC = (-231043.0, -30347.0)
MARTELLO = (-189960.0, -7031.0)
GERONIMO = (-285099.0, -180708.0)
TARINKOT = (-148524.0, -31352.0)

COIN_ROUTES = [
    Route(
        "Farah -> FOB Delaram II  (Highway 1 / the Ring Road, ESE)",
        FARAH,
        [(32.30, 62.55), (32.18, 63.00)],
        DELARAM,
    ),
    Route(
        "FOB Delaram II -> ANP Hill (Now Zad)  (NE track skirting the north edge "
        "of the Dasht-e Margo)",
        DELARAM,
        [(32.30, 63.85), (32.42, 64.20)],
        NOWZAD,
    ),
    Route(
        "ANP Hill (Now Zad) -> FOB Jackson (Sangin)  via Musa Qala -- the 611 wadi",
        NOWZAD,
        [(32.44, 64.75), (32.25, 64.80)],
        SANGIN,
    ),
    Route(
        "FOB Jackson (Sangin) -> FOB Zeebrugge (Kajaki)  (Route 611, up the Helmand)",
        SANGIN,
        [(32.20, 64.98)],
        KAJAKI,
    ),
    Route(
        "Tarinkot -> Kamp Hadrian  (the Tarin Kowt bowl, W toward Deh Rawud)",
        TARINKOT,
        [(32.62, 65.68)],
        HADRIAN,
    ),
    Route(
        "Kamp Hadrian -> Firebase Cobra  (N up the Uruzgan valley)",
        HADRIAN,
        [(32.78, 65.53)],
        COBRA,
    ),
    Route(
        "Tarinkot -> FOB Martello  (SE down the Uruzgan-Kandahar road)",
        TARINKOT,
        [(32.45, 65.96), (32.32, 66.06)],
        MARTELLO,
    ),
    Route(
        "FOB Martello -> FOB Frontenac (the Kandahar gate)  (SW, Uruzgan road descent)",
        MARTELLO,
        [(32.05, 65.99)],
        FRONTENAC,
    ),
    Route(
        "FOB Geronimo -> FOB Zeebrugge (Kajaki)  the Helmand highway the whole way: "
        "Lashkar Gah -> Gereshk -> Sangin -> Kajaki (through the town rings)",
        GERONIMO,
        [(31.59, 64.37), (31.82, 64.55), (32.08, 64.83)],
        KAJAKI,
    ),
]


if __name__ == "__main__":
    print(render(Afghanistan(), COIN_ROUTES))
