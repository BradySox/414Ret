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
from dcs.terrain.thechannel import TheChannel


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


# --- Iraq - Umm al-Ma'arik (Desert Storm 1991): the RED interior road net (Iraq holds
# --- nearly the whole map, so its logistics graph is the interdiction target set).
# --- Corridors follow the real 1991 highway system: Highway 1 (Baghdad-Taji-Balad-
# --- Samarra-Tikrit-Bayji-Qayyarah-Mosul), Highway 10 west (Abu Ghraib-Fallujah-
# --- Habbaniyah), Highway 6 southeast (Salman Pak-Aziziyah-Numaniyah-Kut), the
# --- Tikrit-Kirkuk road over the Jabal Hamrin, the Kirkuk-Altun Kupri-Erbil,
# --- Kirkuk-Chamchamal-Sulaymaniyah and Mosul-Bartella-Erbil roads, and the
# --- Qayyarah-Makhmur-Erbil crossing. Endpoints are exact CP XY from a headless
# --- theater load. The BLUE H-3 -> H-2 -> Al-Asad pipeline-station ladder is NOT
# --- here: those legs are authored as M-113 path groups in the .miz (they carry the
# --- front line as blue climbs the ladder), which double as the convoy routes.
DS_AL_ASAD = (60819.0, -165901.0)  # Al-Asad Airbase (RED -- Qadessiya AB)
DS_BAGHDAD = (-142.0, 160.0)  # Baghdad International (RED)
DS_SALAM = (2263.0, 25199.0)  # Al-Salam Airbase (RED)
DS_TAQADDUM = (9717.0, -58133.0)  # Al-Taquddum (RED)
DS_KUT = (-85732.0, 143282.0)  # Al-Kut (RED)
DS_SAHRA = (157133.0, -61805.0)  # Al-Sahra / Tikrit (RED)
DS_QAYYARAH = (279544.0, -97450.0)  # Qayyarah West (RED)
DS_KIRKUK = (245434.0, 12825.0)  # Kirkuk International (RED)
DS_ERBIL = (330838.0, -22360.0)  # Erbil International (RED)
DS_SULAY = (255226.0, 100814.0)  # Sulaymaniyah International (RED)
DS_BALAD = (75938.0, 13806.0)  # Balad Airbase (RED -- al-Bakr AB)
DS_MOSUL = (339469.0, -94071.0)  # Mosul International (RED -- Firnas AB)

IRAQ_DS91_ROUTES = [
    Route(
        "Baghdad International -> Al-Salam  (RED city hop: the airport expressway "
        "-> the Dora expressway east to the Rasheed side)",
        DS_BAGHDAD,
        [(33.245, 44.31), (33.26, 44.42)],
        DS_SALAM,
    ),
    Route(
        "Baghdad International -> Al-Taquddum  (RED Highway 10 west through Abu "
        "Ghraib -> Fallujah -> Habbaniyah; the western front's supply line)",
        DS_BAGHDAD,
        [(33.30, 44.05), (33.35, 43.79), (33.37, 43.67)],
        DS_TAQADDUM,
    ),
    Route(
        "Baghdad International -> Al-Kut  (RED Highway 6 southeast through Salman "
        "Pak -> Aziziyah -> Numaniyah)",
        DS_BAGHDAD,
        [(33.10, 44.58), (32.91, 44.92), (32.62, 45.29)],
        DS_KUT,
    ),
    Route(
        "Baghdad International -> Balad (al-Bakr)  (RED Highway 1 north through "
        "Taji and the Dujayl junction)",
        DS_BAGHDAD,
        [(33.52, 44.25), (33.72, 44.26), (33.86, 44.28)],
        DS_BALAD,
    ),
    Route(
        "Balad (al-Bakr) -> Al-Sahra (Tikrit)  (RED Highway 1 north through "
        "Samarra -> al-Alam)",
        DS_BALAD,
        [(34.02, 44.20), (34.20, 43.88), (34.60, 43.70)],
        DS_SAHRA,
    ),
    Route(
        "Al-Sahra (Tikrit) -> Qayyarah West  (RED Highway 1 north through Bayji -> "
        "Shirqat; the corridor the Inherent Resolve campaign grinds up, 25 years early)",
        DS_SAHRA,
        [(34.93, 43.49), (35.52, 43.27)],
        DS_QAYYARAH,
    ),
    Route(
        "Al-Sahra (Tikrit) -> Kirkuk  (RED: the Tikrit-Kirkuk road over the Jabal "
        "Hamrin ridge)",
        DS_SAHRA,
        [(34.75, 43.80), (34.95, 44.05), (35.20, 44.20)],
        DS_KIRKUK,
    ),
    Route(
        "Kirkuk -> Erbil  (RED: the Kirkuk-Erbil highway through Altun Kupri)",
        DS_KIRKUK,
        [(35.75, 44.13), (35.95, 44.05), (36.10, 43.99)],
        DS_ERBIL,
    ),
    Route(
        "Kirkuk -> Sulaymaniyah  (RED: the Chamchamal road over the Tasluja pass)",
        DS_KIRKUK,
        [(35.50, 44.60), (35.53, 44.83), (35.58, 45.15)],
        DS_SULAY,
    ),
    Route(
        "Qayyarah West -> Erbil  (RED: the Tigris crossing at Qayyarah -> Makhmur "
        "-> the Erbil plain)",
        DS_QAYYARAH,
        [(35.78, 43.30), (35.77, 43.58), (36.00, 43.75)],
        DS_ERBIL,
    ),
    Route(
        "Qayyarah West -> Mosul (Firnas)  (RED Highway 1 north through Hammam "
        "al-Alil)",
        DS_QAYYARAH,
        [(35.95, 43.20), (36.08, 43.26), (36.20, 43.20)],
        DS_MOSUL,
    ),
    Route(
        "Mosul (Firnas) -> Erbil  (RED: Highway 2 east through Bartella and the "
        "Kalak crossing)",
        DS_MOSUL,
        [(36.35, 43.38), (36.30, 43.65), (36.27, 43.80)],
        DS_ERBIL,
    ),
]


# =====================================================================================
# --- The §50 standardization BATCH 1 (2026-07-06): blue rear corridors for the
# --- road-less campaigns, so the ambient supply convoys + convoy ambushes reach them.
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


# =====================================================================================
# --- The §50 standardization BATCH 2 (2026-07-07): RED rear corridors for the nine
# --- campaigns with no red->red road, so red's ambient supply convoys flow (and the
# --- player has columns to interdict -- the §35 loop). Same standard: exact red CP XY
# --- endpoints, real roads by lat/lon. Blue's ambush layer is untouched by these.
# =====================================================================================

# --- Syria: the Aleppo belt (WRL_AleppoInsurgency; Battle4SyriaNorth shares the
# --- Aleppo legs and adds its Turkish-held FOB line).
SY_ALEPPO = (125577.0, 123125.0)  # Aleppo Intl (RED)
SY_KUWEIRES = (125811.0, 155254.0)  # Kuweires (RED)
SY_JIRAH = (115350.0, 187069.0)  # Jirah (RED)
SY_FOB_XRAY = (108419.0, 110193.0)  # FOB X-RAY (RED, M5 south of Aleppo)
SY_MINAKH = (163698.0, 107431.0)  # Minakh (RED, the Azaz pocket)
SY_TAFTANAZ = (103486.0, 82767.0)  # Taftanaz (RED in Battle4SyriaNorth)
SY_ABU_ALDUHUR = (76049.0, 111345.0)  # Abu al-Duhur (RED in Battle4SyriaNorth)
SY_ERZIN_FOB = (212868.0, 32130.0)  # ERZIN FOB (RED in Battle4SyriaNorth)
SY_OSMANIYE_FOB = (225514.0, 35599.0)  # OSMANIYE FOB (RED in Battle4SyriaNorth)
SY_CEYHAN_FOB = (224062.0, 6871.0)  # CEYHAN FOB (RED in Battle4SyriaNorth)
SY_BB90_FOB = (225900.0, 72474.0)  # BB90 FOB (RED, the Bahce/O-52 corridor)

SYRIA_ALEPPO_KUWEIRES = Route(
    "Aleppo -> Kuweires  (the Dayr Hafir road east out of the city)",
    SY_ALEPPO,
    [(36.210, 37.400)],
    SY_KUWEIRES,
)
SYRIA_KUWEIRES_JIRAH = Route(
    "Kuweires -> Jirah  (the Aleppo-Raqqa road south-east toward Maskanah)",
    SY_KUWEIRES,
    [(36.150, 37.750)],
    SY_JIRAH,
)
SYRIA_ALEPPO_XRAY = Route(
    "Aleppo -> FOB X-RAY  (the M5 south toward Saraqib)",
    SY_ALEPPO,
    [(36.100, 37.150)],
    SY_FOB_XRAY,
)
SYRIA_ALEPPO_MINAKH = Route(
    "Aleppo -> Minakh  (the Azaz road north through Hreitan)",
    SY_ALEPPO,
    [(36.350, 37.100), (36.450, 37.050)],
    SY_MINAKH,
)
SYRIA_TAFTANAZ_ABUALDUHUR = Route(
    "Taftanaz -> Abu al-Duhur  (via Saraqib, then the Abu-Duhur plain road)",
    SY_TAFTANAZ,
    [(35.860, 36.810), (35.790, 37.000)],
    SY_ABU_ALDUHUR,
)
SYRIA_HATAY_ERZIN = Route(
    "Hatay -> ERZIN FOB  (E91 north over the Belen pass through Iskenderun/Dortyol)",
    SY_HATAY,
    [(36.490, 36.210), (36.840, 36.210)],
    SY_ERZIN_FOB,
)
SYRIA_ERZIN_OSMANIYE = Route(
    "ERZIN FOB -> OSMANIYE FOB  (the E91/O-53 short leg north)",
    SY_ERZIN_FOB,
    [(37.000, 36.210)],
    SY_OSMANIYE_FOB,
)
SYRIA_OSMANIYE_CEYHAN = Route(
    "OSMANIYE FOB -> CEYHAN FOB  (O-52/D400 west through Toprakkale)",
    SY_OSMANIYE_FOB,
    [(37.060, 36.130)],
    SY_CEYHAN_FOB,
)
SYRIA_OSMANIYE_BB90 = Route(
    "OSMANIYE FOB -> BB90 FOB  (the O-52 east toward Bahce)",
    SY_OSMANIYE_FOB,
    [(37.080, 36.400)],
    SY_BB90_FOB,
)

# --- Persian Gulf: the Iranian mainland highways (both Noisy Crickets share the
# --- red laydown; the island fields -- Kish/Qeshm/Abu Musa -- stay roadless).
PG_BANDARABBAS = (115766.0, 14258.0)  # Bandar Abbas Intl (RED)
PG_KERMAN = (454117.0, 71096.0)  # Kerman (RED)
PG_SHIRAZ = (381101.0, -351637.0)  # Shiraz Intl (RED)
PG_BUSHEHR = (313020.0, -505678.0)  # Bushehr NPP (RED)

IRAN_MAINLAND_ROUTES = [
    Route(
        "Bandar Abbas -> Kerman  (the truck route north: Hajiabad -> Sirjan -> "
        "the Kerman highway)",
        PG_BANDARABBAS,
        [(28.310, 55.900), (29.450, 55.680), (29.900, 56.300)],
        PG_KERMAN,
    ),
    Route(
        "Bandar Abbas -> Shiraz  (Highway 86/96 west through Lar and Jahrom)",
        PG_BANDARABBAS,
        [(27.680, 54.340), (28.500, 53.560)],
        PG_SHIRAZ,
    ),
    Route(
        "Shiraz -> Bushehr  (Highway 86 down through Kazerun and Borazjan)",
        PG_SHIRAZ,
        [(29.620, 51.650), (29.270, 51.210)],
        PG_BUSHEHR,
    ),
]

# --- Syria map as Cyprus (operation_aegean_aegis): the island's A-road motorways.
CY_AKROTIRI = (-35779.0, -268906.0)  # Akrotiri (RED here)
CY_LARNACA = (-7675.0, -208844.0)  # Larnaca (RED)
CY_ERCAN = (23584.0, -217287.0)  # Ercan (RED)

CYPRUS_ROUTES = [
    Route(
        "Akrotiri -> Larnaca  (the A1/A5 motorway via Limassol and Kofinou)",
        CY_AKROTIRI,
        [(34.680, 33.050), (34.820, 33.390)],
        CY_LARNACA,
    ),
    Route(
        "Larnaca -> Ercan  (the A2 toward Nicosia, then north-east across the "
        "Mesaoria plain)",
        CY_LARNACA,
        [(35.050, 33.400)],
        CY_ERCAN,
    ),
]

# --- The Channel (operation_dynamo): red's 1940 coastal roads.
CH_CALAIS = (6776.0, 22547.0)  # Calais-Marck (RED)
CH_STOMER = (-16952.0, 45168.0)  # Saint Omer Longuenesse (RED)
CH_OSTENDE = (32605.0, 98407.0)  # Ostende (RED)

CHANNEL_ROUTES = [
    Route(
        "Calais -> Saint Omer  (the N43 through Ardres)",
        CH_CALAIS,
        [(50.860, 2.020)],
        CH_STOMER,
    ),
    Route(
        "Calais -> Ostende  (the coastal E40 road through Dunkirk and Veurne)",
        CH_CALAIS,
        [(51.030, 2.350), (51.070, 2.660)],
        CH_OSTENDE,
    ),
]

# --- Marianas (operation_velvet_thunder): red's island-INTERNAL roads -- Saipan's
# --- Middle Road north and Tinian's Broadway. (Island-to-island stays roadless, so
# --- the §35 no-red-trail note only softens: red convoys now exist, per island.)
MI_SAIPAN = (180035.0, 101856.0)  # Saipan Intl (RED)
MI_KITE = (198363.0, 110807.0)  # FOB KITE (RED, north Saipan)
MI_TINIAN = (166860.0, 89957.0)  # Tinian Intl (RED)
MI_BOAT = (172799.0, 91771.0)  # FOB BOAT (RED, north Tinian)

MARIANAS_RED_ROUTES = [
    Route(
        "Saipan Intl -> FOB KITE  (Middle Road / Route 30 north through Garapan "
        "and Tanapag)",
        MI_SAIPAN,
        [(15.190, 145.720), (15.240, 145.760)],
        MI_KITE,
    ),
    Route(
        "Tinian Intl -> FOB BOAT  (Broadway north up the island)",
        MI_TINIAN,
        [(15.030, 145.630)],
        MI_BOAT,
    ),
]

#: §50 batch 2 -- campaign stem -> (terrain, RED routes to splice into its yaml).
#: operation_shattered_dagger reuses the Enduring Resolve ratline verbatim (same
#: laydown -- ER is its fork); pacific_repartee reuses the Guam road (red-owned there).
BATCH2_RED_REAR: dict[str, tuple[type, list[Route]]] = {
    "WRL_AleppoInsurgency": (
        Syria,
        [SYRIA_ALEPPO_KUWEIRES, SYRIA_KUWEIRES_JIRAH, SYRIA_ALEPPO_XRAY],
    ),
    "WRL_Battle4SyriaNorth": (
        Syria,
        [
            SYRIA_ALEPPO_MINAKH,
            SYRIA_ALEPPO_KUWEIRES,
            SYRIA_KUWEIRES_JIRAH,
            SYRIA_TAFTANAZ_ABUALDUHUR,
            SYRIA_HATAY_ERZIN,
            SYRIA_ERZIN_OSMANIYE,
            SYRIA_OSMANIYE_CEYHAN,
            SYRIA_OSMANIYE_BB90,
        ],
    ),
    "operation_noisy_cricket": (PersianGulf, IRAN_MAINLAND_ROUTES),
    "WRL_Operation_Noisy_Cricket_Redux": (PersianGulf, IRAN_MAINLAND_ROUTES),
    "operation_aegean_aegis": (Syria, CYPRUS_ROUTES),
    "operation_dynamo": (TheChannel, CHANNEL_ROUTES),
    # The ER ratline minus its final entry (the Kandahar<->Bastion BLUE corridor,
    # which batch 1 already gave this campaign).
    "operation_shattered_dagger": (Afghanistan, COIN_ROUTES[:-1]),
    "operation_velvet_thunder": (MarianaIslands, MARIANAS_RED_ROUTES),
    "pacific_repartee": (MarianaIslands, GUAM_ROUTES),
}


CAMPAIGNS = {
    "coin": (Afghanistan, COIN_ROUTES),
    "red_flag_81_2": (Nevada, RED_FLAG_ROUTES),
    "caucasus_trail_fixes": (Caucasus, CAUCASUS_TRAIL_FIXES),
    "iraq_inherent_resolve": (Iraq, IRAQ_IR_ROUTES),
    "iraq_desert_storm": (Iraq, IRAQ_DS91_ROUTES),
}
# Every batch-1/batch-2 campaign is directly addressable too (spaces -> underscores;
# a campaign in both batches resolves to its batch-2 red routes -- regenerate batch-1
# blue blocks via the shared route constants if ever needed).
CAMPAIGNS.update(
    {
        stem.replace(" ", "_"): (terrain, routes)
        for stem, (terrain, routes) in BATCH1_BLUE_REAR.items()
    }
)
CAMPAIGNS.update(
    {
        stem.replace(" ", "_") + "_red": (terrain, routes)
        for stem, (terrain, routes) in BATCH2_RED_REAR.items()
    }
)


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "coin"
    terrain_cls, routes = CAMPAIGNS[name]
    print(render(terrain_cls(), routes))
