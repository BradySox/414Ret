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

    python tools/supply_route_geo.py [coin|red_flag_81_2|<batch-1 campaign stem>]
    # default: coin. The §50 batch-1 blue rear corridors (BATCH1_BLUE_REAR) are all
    # addressable by campaign stem with spaces as underscores, e.g. task_force_thunder.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field

from dcs.mapping import LatLng, Point
from dcs.terrain.afghanistan import Afghanistan
from dcs.terrain.caucasus import Caucasus
from dcs.terrain.iraq import Iraq
from dcs.terrain.kola import Kola
from dcs.terrain.marianaislands import MarianaIslands
from dcs.terrain.nevada import Nevada
from dcs.terrain.normandy import Normandy
from dcs.terrain.persiangulf import PersianGulf
from dcs.terrain.sinai import Sinai
from dcs.terrain.syria import Syria


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


# =====================================================================================
# --- The §50 standardization BATCH 1 (2026-07-06): blue rear corridors for the
# --- road-less campaigns, so the ambient supply convoys + convoy ambushes reach them.
# --- One mode per campaign stem below (campaigns sharing a laydown share the routes).
# --- Endpoints are the exact blue CP XY from a headless theater load; corridors are
# --- the real road network by lat/lon per the driveable-corridor standard.
# =====================================================================================

# --- Caucasus: Tbilisi bowl (TblisiGap + operation_vectrons_claw share the pair).
CC_TBILISI = (-315671.0, 896630.0)  # Tbilisi-Lochini (BLUE)
CC_VAZIANI = (-319065.0, 903149.0)  # Vaziani (BLUE)

TBILISI_VAZIANI_ROUTES = [
    Route(
        "Tbilisi-Lochini -> Vaziani  (the Kakheti Highway / S5 east past the "
        "airport interchange -- the short BLUE rear hop; feeds the #50 convoys)",
        CC_TBILISI,
        [(41.658, 44.980), (41.645, 45.003)],
        CC_VAZIANI,
    ),
]

# --- Caucasus: west Georgia (WRL_Battle4Georgia + WRL_Kutaisi2Vaziani share the trio).
CC_KUTAISI = (-284887.0, 683859.0)  # Kutaisi (BLUE)
CC_SENAKI = (-281782.0, 647279.0)  # Senaki-Kolkhi (BLUE)
CC_KOBULETI = (-317962.0, 635633.0)  # Kobuleti (BLUE)

WEST_GEORGIA_ROUTES = [
    Route(
        "Kutaisi -> Senaki-Kolkhi  (E60/S1 west through Samtredia and Abasha)",
        CC_KUTAISI,
        [(42.163, 42.335), (42.208, 42.195)],
        CC_SENAKI,
    ),
    Route(
        "Senaki-Kolkhi -> Kobuleti  (S1 to the Khobi junction, then the S2 coastal "
        "road south through Grigoleti/Ureki)",
        CC_SENAKI,
        [(42.190, 41.920), (42.020, 41.750), (41.985, 41.780)],
        CC_KOBULETI,
    ),
]

# --- Caucasus as the Black-Sea coast (slava_ukraini): the A290 Anapa-Novorossiysk road.
CC_ANAPA = (-5412.0, 243129.0)  # Anapa-Vityazevo (BLUE)
CC_NOVOROSSIYSK = (-40918.0, 279256.0)  # Novorossiysk (BLUE)

SLAVA_UKRAINI_ROUTES = [
    Route(
        "Anapa-Vityazevo -> Novorossiysk  (the A290 through Raevskaya and the "
        "Verkhnebakansky pass)",
        CC_ANAPA,
        [(44.837, 37.555), (44.770, 37.690)],
        CC_NOVOROSSIYSK,
    ),
]

# --- Syria map: the Turkish rear highways + the western-Iraq pipeline road.
SY_GAZIANTEP = (210334.0, 147314.0)  # Gaziantep (BLUE)
SY_INCIRLIK = (221208.0, -35240.0)  # Incirlik (BLUE)
SY_HATAY = (147687.0, 39419.0)  # Hatay (BLUE)
SY_COASTDEF = (200062.0, -1069.0)  # COAST DEFENSES FOB (BLUE, Karatas coast)
SY_H4 = (-279367.0, 207219.0)  # H4 (BLUE, Jordan pipeline station)
SY_H3 = (-235406.0, 352523.0)  # H3 (BLUE, west-Iraq pipeline station)

SYRIA_GAZIANTEP_INCIRLIK = Route(
    "Gaziantep -> Incirlik  (the O-52/E90 motorway: Nurdagi -> Bahce -> "
    "Toprakkale -> Ceyhan -- the Turkish BLUE rear spine)",
    SY_GAZIANTEP,
    [(37.190, 36.600), (37.060, 36.150), (37.030, 35.820)],
    SY_INCIRLIK,
)
SYRIA_INCIRLIK_HATAY = Route(
    "Incirlik -> Hatay  (E91/O-53 south: Toprakkale -> Dortyol -> Iskenderun -> "
    "the Belen pass -> Antakya)",
    SY_INCIRLIK,
    [(37.055, 36.150), (36.840, 36.210), (36.520, 36.200)],
    SY_HATAY,
)
SYRIA_INCIRLIK_COAST = Route(
    "Incirlik -> COAST DEFENSES  (D400 east out of Adana, then the Yumurtalik "
    "coast road south)",
    SY_INCIRLIK,
    [(36.950, 35.600), (36.870, 35.740)],
    SY_COASTDEF,
)
SYRIA_H4_H3 = Route(
    "H4 -> H3  (the old Haifa-pipeline highway across the western desert -- the "
    "road the pumping stations exist to guard)",
    SY_H4,
    [(32.660, 38.650), (32.830, 39.300)],
    SY_H3,
)

# --- Nevada (WRL_Battle4area51): the same US-95 leg Red Flag 81-2 uses.
AREA51_ROUTES = [
    Route(
        "Nellis -> Indian Springs (Creech): US-95 north-west out of Las Vegas",
        NELLIS,
        [(36.300, -115.260), (36.420, -115.440), (36.520, -115.610)],
        CREECH,
    ),
]

# --- Persian Gulf: the UAE E11 corridor (operation_noisy_cricket + the WRL redux +
# --- scenic_merge all field the same Al Dhafra / Al Minhad pair).
PG_ALDHAFRA = (-211028.0, -173240.0)  # Al Dhafra AFB (BLUE)
PG_ALMINHAD = (-126014.0, -89133.0)  # Al Minhad AFB (BLUE)

UAE_REAR_ROUTES = [
    Route(
        "Al Dhafra AFB -> Al Minhad AFB  (E11 north along the coast past Ghantoot, "
        "then inland at Jebel Ali to the E611 -- the UAE BLUE rear spine)",
        PG_ALDHAFRA,
        [(24.430, 54.620), (24.860, 54.870), (25.010, 55.100)],
        PG_ALMINHAD,
    ),
]

# --- Sinai map: the Israeli route-40 rear (operation_gazelle) + the Egyptian Delta
# --- corridor (red_sea_rising, which also shares the Tel Nof leg).
SN_HATZOR = (189869.0, 332622.0)  # Hatzor (BLUE)
SN_TELNOF = (198387.0, 341243.0)  # Tel Nof (BLUE)
SN_BENGURION = (217468.0, 348036.0)  # Ben-Gurion (BLUE)
SN_SALIHIYAH = (81974.0, 77621.0)  # As Salihiyah (BLUE, east Delta)
SN_BORGELARAB = (99767.0, -146756.0)  # Borg El Arab Intl (BLUE, Alexandria)

SINAI_HATZOR_TELNOF = Route(
    "Hatzor -> Tel Nof  (route 40/411 through the Gedera junction)",
    SN_HATZOR,
    [(31.810, 34.780)],
    SN_TELNOF,
)
SINAI_TELNOF_BENGURION = Route(
    "Tel Nof -> Ben-Gurion  (route 40 north through Ramla)",
    SN_TELNOF,
    [(31.920, 34.860)],
    SN_BENGURION,
)
SINAI_EGYPT_DELTA = Route(
    "As Salihiyah -> Borg El Arab  (the Delta highways: Zagazig -> Tanta -> "
    "Damanhur -- the Egyptian BLUE rear corridor)",
    SN_SALIHIYAH,
    [(30.590, 31.510), (30.790, 31.000), (31.040, 30.470)],
    SN_BORGELARAB,
)

# --- Iraq (operation_desert_aladeen): the Baghdad ring between the two BLUE fields.
IQ_BAGHDAD = (-142.0, 160.0)  # Baghdad International (BLUE)
IQ_ALSALAM = (2263.0, 25199.0)  # Al-Salam Airbase (BLUE, east Baghdad)

DESERT_ALADEEN_ROUTES = [
    Route(
        "Baghdad International -> Al-Salam Airbase  (the Airport Road east, then "
        "the Army Canal expressway across the city)",
        IQ_BAGHDAD,
        [(33.260, 44.310), (33.285, 44.420)],
        IQ_ALSALAM,
    ),
]

# --- Afghanistan (operation_shattered_dagger, the COIN base laydown): the same
# --- Highway-1 Kandahar<->Bastion ambush alley Enduring Resolve runs (constants above).
SHATTERED_DAGGER_ROUTES = [
    Route(
        "Kandahar Airfield -> Camp Bastion  (Highway 1 west through Zhari/Howz-e "
        "Madad -> Maiwand -> Gereshk, then the Bastion access road)",
        KANDAHAR,
        [(31.596, 65.406), (31.664, 65.045), (31.823, 64.567), (31.875, 64.360)],
        BASTION,
    ),
]

# --- Marianas (operation_velvet_thunder): Guam's Route 1, Marine Corps Drive --
# --- the two BLUE fields sit on the SAME island (the red bases have no roads, so
# --- the §35 red-interdiction no-op there is unchanged).
MI_WONPAT = (-24.0, -78.0)  # Antonio B. Won Pat Intl (BLUE)
MI_ANDERSEN = (10575.0, 14549.0)  # Andersen AFB (BLUE)

GUAM_ROUTES = [
    Route(
        "Won Pat Intl -> Andersen AFB  (Route 16 to Route 1 / Marine Corps Drive "
        "north through Dededo and Yigo)",
        MI_WONPAT,
        [(13.512, 144.839), (13.537, 144.890)],
        MI_ANDERSEN,
    ),
]

# --- Normandy 2 map, the England side (final_countdown_2): the New Forest A-roads
# --- + the London road down to the A31. Utah is across the Channel -- no road.
NM_NEEDSOAR = (140789.0, -85142.0)  # Needs Oar Point (BLUE)
NM_LYMINGTON = (139651.0, -90746.0)  # Lymington (BLUE)
NM_STONEYCROSS = (156400.0, -100851.0)  # Stoney Cross (BLUE)
NM_NORTHOLT = (229644.0, -16612.0)  # Northolt (BLUE)

ENGLAND_REAR_ROUTES = [
    Route(
        "Lymington -> Needs Oar Point  (the B3054 through East End)",
        NM_LYMINGTON,
        [(50.760, -1.480)],
        NM_NEEDSOAR,
    ),
    Route(
        "Stoney Cross -> Lymington  (A337 south through Lyndhurst and Brockenhurst)",
        NM_STONEYCROSS,
        [(50.871, -1.577), (50.818, -1.573)],
        NM_LYMINGTON,
    ),
    Route(
        "Northolt -> Stoney Cross  (A30/M3 via Staines -> Basingstoke -> "
        "Winchester, then the A31 into the New Forest)",
        NM_NORTHOLT,
        [(51.430, -0.510), (51.260, -1.090), (51.060, -1.320), (50.950, -1.550)],
        NM_STONEYCROSS,
    ),
]

# --- Kola (the_anvil_of_war): the Swedish E10/E45/94 rear chain + the E6/E10
# --- Bardufoss->Kiruna corridor over the Norwegian border. Bodo/Andoya are
# --- fjord-and-ferry separated -- left roadless on purpose.
KO_KIRUNA = (-20456.0, -90639.0)  # Kiruna (BLUE)
KO_KALIXFORS = (-26773.0, -94330.0)  # Kalixfors (BLUE)
KO_JOKKMOKK = (-168130.0, -100661.0)  # Jokkmokk (BLUE)
KO_VIDSEL = (-237356.0, -101474.0)  # Vidsel (BLUE)
KO_KALLAX = (-274102.0, -10879.0)  # Kallax / Lulea (BLUE)
KO_BARDUFOSS = (118871.0, -160678.0)  # Bardufoss (BLUE, Norway)

KOLA_REAR_ROUTES = [
    Route(
        "Kiruna -> Kalixfors  (the E10/870 south -- the short garrison hop)",
        KO_KIRUNA,
        [(67.790, 20.280)],
        KO_KALIXFORS,
    ),
    Route(
        "Kalixfors -> Jokkmokk  (E10 south to Gallivare, then the E45 through Porjus)",
        KO_KALIXFORS,
        [(67.130, 20.660), (66.960, 19.830)],
        KO_JOKKMOKK,
    ),
    Route(
        "Jokkmokk -> Vidsel  (road 97 down the Lule valley via Vuollerim, then 356 "
        "at Harads west to the Vidsel range road)",
        KO_JOKKMOKK,
        [(66.430, 20.600), (66.070, 20.950), (65.990, 20.500)],
        KO_VIDSEL,
    ),
    Route(
        "Vidsel -> Kallax  (road 94 to Alvsbyn, E4 at Pitea, north to Lulea)",
        KO_VIDSEL,
        [(65.670, 21.000), (65.330, 21.490), (65.500, 21.920)],
        KO_KALLAX,
    ),
    Route(
        "Bardufoss -> Kiruna  (E6 south through Setermoen to Bjerkvik, then the "
        "E10 east over Bjornfjell/Riksgransen and past Abisko)",
        KO_BARDUFOSS,
        [(68.860, 18.350), (68.550, 17.550), (68.430, 18.100), (68.350, 18.820)],
        KO_KIRUNA,
    ),
]


#: §50 batch 1 -- campaign stem -> (terrain, routes to splice into its yaml).
#: Campaigns sharing a laydown share the route list.
BATCH1_BLUE_REAR: dict[str, tuple[type, list[Route]]] = {
    "TblisiGap": (Caucasus, TBILISI_VAZIANI_ROUTES),
    "operation_vectrons_claw": (Caucasus, TBILISI_VAZIANI_ROUTES),
    "WRL_Battle4Georgia": (Caucasus, WEST_GEORGIA_ROUTES),
    "WRL_Kutaisi2Vaziani": (Caucasus, WEST_GEORGIA_ROUTES),
    "slava_ukraini": (Caucasus, SLAVA_UKRAINI_ROUTES),
    "syria_TheLongRoadToH3": (Syria, [SYRIA_GAZIANTEP_INCIRLIK]),
    "syria_full_map": (Syria, [SYRIA_GAZIANTEP_INCIRLIK]),
    "WRL_AleppoInsurgency": (Syria, [SYRIA_GAZIANTEP_INCIRLIK, SYRIA_INCIRLIK_HATAY]),
    "WRL_Battle4SyriaNorth": (Syria, [SYRIA_INCIRLIK_COAST]),
    "Task Force Thunder": (Syria, [SYRIA_H4_H3]),
    "WRL_Battle4area51": (Nevada, AREA51_ROUTES),
    "operation_noisy_cricket": (PersianGulf, UAE_REAR_ROUTES),
    "WRL_Operation_Noisy_Cricket_Redux": (PersianGulf, UAE_REAR_ROUTES),
    "scenic_merge": (PersianGulf, UAE_REAR_ROUTES),
    "operation_gazelle": (Sinai, [SINAI_HATZOR_TELNOF, SINAI_TELNOF_BENGURION]),
    "red_sea_rising": (Sinai, [SINAI_TELNOF_BENGURION, SINAI_EGYPT_DELTA]),
    "operation_desert_aladeen": (Iraq, DESERT_ALADEEN_ROUTES),
    "operation_shattered_dagger": (Afghanistan, SHATTERED_DAGGER_ROUTES),
    "operation_velvet_thunder": (MarianaIslands, GUAM_ROUTES),
    "final_countdown_2": (Normandy, ENGLAND_REAR_ROUTES),
    "the_anvil_of_war": (Kola, KOLA_REAR_ROUTES),
}


CAMPAIGNS = {
    "coin": (Afghanistan, COIN_ROUTES),
    "red_flag_81_2": (Nevada, RED_FLAG_ROUTES),
    "caucasus_trail_fixes": (Caucasus, CAUCASUS_TRAIL_FIXES),
    "iraq_inherent_resolve": (Iraq, IRAQ_IR_ROUTES),
}
# Every batch-1 campaign is directly addressable too (spaces -> underscores).
CAMPAIGNS.update(
    {
        stem.replace(" ", "_"): (terrain, routes)
        for stem, (terrain, routes) in BATCH1_BLUE_REAR.items()
    }
)


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "coin"
    terrain_cls, routes = CAMPAIGNS[name]
    print(render(terrain_cls(), routes))
