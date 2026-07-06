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
Each campaign's routes are defined below as its reference application; pick one by name
and paste the output into that campaign's ``resources/campaigns/*.yaml``.

    python tools/supply_route_geo.py [coin|red_flag_81_2]   # default: coin
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field

from dcs.mapping import LatLng, Point
from dcs.terrain.afghanistan import Afghanistan
from dcs.terrain.caucasus import Caucasus
from dcs.terrain.iraq import Iraq
from dcs.terrain.nevada import Nevada


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
KANDAHAR = (-270486.0, -29690.0)  # Kandahar Airfield (BLUE)
BASTION = (-235178.0, -184377.0)  # Camp Bastion (BLUE)

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
    Route(
        "Kandahar Airfield -> Camp Bastion  (the BLUE rear corridor: Highway 1 west "
        "through Zhari/Howz-e Madad -> Maiwand -> Gereshk, then the Bastion access "
        "road -- THE ambush-alley convoy run; feeds the #50 escort convoys)",
        KANDAHAR,
        [(31.596, 65.406), (31.664, 65.045), (31.823, 64.567), (31.875, 64.360)],
        BASTION,
    ),
]


# --- Red Flag 81-2 (Nevada Test & Training Range): exact FOB/airfield marker XY
# --- endpoints, the real NTTR road network between them. Roads: US-95 (the SE->NW
# --- spine: Las Vegas -> Indian Springs -> Mercury -> Beatty -> Goldfield -> Tonopah),
# --- US-6 east out of Tonopah, and the NTS/range interior roads (the Mercury Highway,
# --- the Gold Flat/Kawich valley down to Pahute Mesa). The first route -- THE FRONT
# --- across the NTS -- is the static-front polyline, not a supply road, so it is left
# --- as authored in the yaml and NOT emitted here.
NELLIS = (-398195.0, -17233.0)
CREECH = (-360507.0, -75590.0)  # Indian Springs
MERCURY = (-352000.0, -103000.0)  # Camp Mercury (NTS main gate)
TOLICHA = (-322000.0, -148000.0)  # FOB Tolicha (FEBA anchor)
TONOPAH = (-197282.0, -201302.0)  # Tonopah civil (on US-6)
TTR = (-226505.0, -174698.0)  # Tonopah Test Range
PAHUTE = (-303620.0, -132937.0)  # Pahute Mesa
BEATTY = (-330553.0, -174958.0)
GROOM = (-288604.0, -86870.0)  # Groom Lake

RED_FLAG_ROUTES = [
    Route(
        "Nellis -> Indian Springs (Creech): US-95 north-west out of Las Vegas",
        NELLIS,
        [(36.300, -115.260), (36.420, -115.440), (36.520, -115.610)],
        CREECH,
    ),
    Route(
        "Indian Springs (Creech) -> Camp Mercury: US-95 north-west to the NTS gate",
        CREECH,
        [(36.607, -115.755), (36.640, -115.905)],  # Cactus Springs -> Mercury jct
        MERCURY,
    ),
    Route(
        "Tonopah (civil) -> Tonopah Test Range: US-6 east, then the TTR access road south",
        TONOPAH,
        [(38.045, -116.980), (37.920, -116.860)],
        TTR,
    ),
    Route(
        "Tonopah Test Range -> Pahute Mesa: down the Gold Flat / Kawich Valley corridor",
        TTR,
        [(37.600, -116.600), (37.380, -116.450), (37.200, -116.360)],
        PAHUTE,
    ),
    Route(
        "Pahute Mesa -> FOB Tolicha: the Pahute Mesa road, last leg to the FEBA anchor",
        PAHUTE,
        [(37.030, -116.400)],
        TOLICHA,
    ),
    Route(
        "Beatty -> FOB Tolicha: the western Tolicha Peak corridor into the NTS boundary",
        BEATTY,
        [(36.900, -116.630)],
        TOLICHA,
    ),
    Route(
        "Tonopah Test Range -> Beatty: the real US-95 west corridor -- west to Goldfield, "
        "then south through Scotty's Junction (NOT straight down the Kawich Range)",
        TTR,
        [
            (37.708, -117.235),
            (37.283, -117.021),
            (36.980, -116.820),
        ],  # Goldfield -> Scotty's Jct -> Springdale
        BEATTY,
    ),
    Route(
        "Groom Lake -> Pahute Mesa: the Box feeds the FEBA (NTS interior, Yucca Flat)",
        GROOM,
        [(37.190, -116.000), (37.130, -116.180)],
        PAHUTE,
    ),
]


# --- Caucasus Vietnam trail (1968 Yankee Station + Steel Tiger, shared miz): a
# --- FICTIONAL overlay -- Hanoi is Kutaisi, the Ho Chi Minh Trail FOBs are placed in
# --- the Samegrelo highlands. Per the standard these deep-mountain corridors want an
# --- in-app by-eye pass, NOT headless real-road lat/lon; this entry holds ONLY the
# --- three corridors whose gross defects are unambiguous to fix in place (a bare
# --- straight line, an eastward lowland overshoot) -- the Kolkheti coastal plain and
# --- the western foothill descents are real, driveable, and low-risk. It does NOT
# --- emit the whole block: splice each route individually. Endpoints are verbatim yaml
# --- XY (Senaki / Poti-Kulevi / the Ban Laboy hill FOB), so binding is unchanged.
CT_SENAKI = (-280521.0, 642739.0)  # Haiphong (Senaki), R3 start
CT_THANHHOA_R3 = (-289768.0, 619547.0)  # FOB Thanh Hoa (Poti/Kulevi coast), R3 end
CT_THANHHOA_R4 = (-288780.0, 620946.0)  # FOB Thanh Hoa, R4 end (verbatim, distinct XY)
CT_BANLABOY_R4 = (-266003.0, 623883.0)  # FOB Ban Laboy, R4 start (verbatim)
CT_BANLABOY_R5 = (-267428.0, 625056.0)  # FOB Ban Laboy, R5 start (verbatim)
CT_SENAKI_R5 = (-279960.0, 644266.0)  # Haiphong (Senaki), R5 end (verbatim)

CAUCASUS_TRAIL_FIXES = [
    Route(
        "Haiphong (Senaki) -> FOB Thanh Hoa: SW across the Kolkheti coastal plain "
        "toward the Poti/Kulevi coast (was a bare 2-point straight line)",
        CT_SENAKI,
        [(42.235, 41.870), (42.205, 41.780)],
        CT_THANHHOA_R3,
    ),
    Route(
        "FOB Thanh Hoa <-> FOB Ban Laboy: straight down the western foothill edge "
        "(removed the ~25 km eastward overshoot into the Senaki lowland)",
        CT_BANLABOY_R4,
        [(42.345, 41.770), (42.275, 41.745)],
        CT_THANHHOA_R4,
    ),
    Route(
        "FOB Ban Laboy <-> Haiphong (Senaki): a clean SE descent from the hills to the "
        "Senaki lowland (was a clustered stub + one long straight jump)",
        CT_BANLABOY_R5,
        [(42.350, 41.860), (42.305, 41.930)],
        CT_SENAKI_R5,
    ),
]


# --- Inherent Resolve (Iraq map): the BLUE rear corridor only -- the red 14-route
# --- graph was hand-authored against the base miz and stays as-is. These two routes
# --- link the three blue southern airfields along the real highways so the #50 escort
# --- convoys have roads to run (and ambush alley has an alley): Highway 1 north out
# --- of Baghdad through Taji/Dujayl to Balad, and Highway 10 west through Abu
# --- Ghraib/Fallujah/Habbaniyah to Al-Taquddum. Endpoints are the exact CP XY.
IR_BAGHDAD = (-142.0, 160.0)  # Baghdad International Airport (BLUE)
IR_BALAD = (75938.0, 13806.0)  # Balad Airbase (BLUE, the forward player field)
IR_TAQADDUM = (9717.0, -58133.0)  # Al-Taquddum Airport (BLUE, the strike field)

IRAQ_IR_ROUTES = [
    Route(
        "Baghdad International -> Balad Airbase  (the BLUE rear corridor: Highway 1 "
        "north through Taji and the Dujayl junction; feeds the #50 escort convoys)",
        IR_BAGHDAD,
        [(33.42, 44.22), (33.52, 44.25), (33.72, 44.26), (33.86, 44.28)],
        IR_BALAD,
    ),
    Route(
        "Baghdad International -> Al-Taquddum  (the BLUE western corridor: Highway 10 "
        "through Abu Ghraib -> Fallujah -> Habbaniyah; feeds the #50 escort convoys)",
        IR_BAGHDAD,
        [(33.30, 44.05), (33.35, 43.79), (33.37, 43.67)],
        IR_TAQADDUM,
    ),
]


CAMPAIGNS = {
    "coin": (Afghanistan, COIN_ROUTES),
    "red_flag_81_2": (Nevada, RED_FLAG_ROUTES),
    "caucasus_trail_fixes": (Caucasus, CAUCASUS_TRAIL_FIXES),
    "iraq_inherent_resolve": (Iraq, IRAQ_IR_ROUTES),
}


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "coin"
    terrain_cls, routes = CAMPAIGNS[name]
    print(render(terrain_cls(), routes))
