"""Build resources/campaigns/iraq_inherent_resolve.miz from scratch on the Iraq map.

The Battle of Mosul, Oct 2016 -> Jul 2017 -- the 414th's second COIN campaign (sibling
of Operation Enduring Resolve). Unlike the ER build tool (which *decorated* Starfire's
Shattered Dagger laydown), there is no pre-authored Mosul miz, so this generates the whole
laydown headlessly via pydcs: a fresh Iraq mission, the CJTF blue/red countries, airfield
ownership (Mosul red, the ring/rear blue), the red Nineveh town strongholds as FOBs, the
per-stronghold COIN furniture (a garrison cell, guns, the thin SA-6/8/9/13 crust) and the
ammo-cache TGOs the C1 regen throttle feeds on, plus the one southern front (Q-West ->
Hammam al-Alil). The red-red ring/ratline is authored in the campaign yaml's `supply_routes`.

Everything is deterministic (fixed offsets, no randomness). The stronghold XY were derived
from the towns' real lat/lons through the Iraq terrain projection (the 414th supply-line
standard); edit the tables below and re-run to rebalance.

Usage: python tools/build_iraq_inherent_resolve_miz.py
"""

from __future__ import annotations

from pathlib import Path

from dcs.countries import CombinedJointTaskForcesBlue, CombinedJointTaskForcesRed
from dcs.mapping import Point
from dcs.mission import Mission
from dcs.statics import Fortification, Warehouse
from dcs.terrain.iraq.iraq import Iraq
from dcs.vehicles import AirDefence, Armor, Unarmed

REPO = Path(__file__).resolve().parent.parent
DST = REPO / "resources/campaigns/iraq_inherent_resolve.miz"

# --- Airfield ownership (terrain airport ids, from dcs.terrain.iraq.airports).
#     Mosul is the one red airfield (the objective); the ring + rear are blue; the
#     far-SW desert fields (H-2/H-3, id 15-18) and the peripheral Al-Asad/Al-Kut are
#     left unset so they are NOT drawn as control points (keeps the theater on Mosul).
RED_AIRFIELD_IDS = [3]  # Mosul International
BLUE_AIRFIELD_IDS = [
    6,  # Qayyarah West -- the forward airhead, player fields
    4,  # Erbil -- eastern flank / coalition
    5,  # Bashur -- northern Kurdish field
    10,  # Kirkuk
    11,  # K1 Base
    7,  # Sulaimaniyah -- rear
    12,  # Al-Sahra -- mid rear
    8,  # Balad -- heavies
    9,  # Al-Taji -- rear
    2,  # Baghdad International -- support
    14,  # Al-Salam -- support / CSAR
    13,  # Al-Taquddum -- Anbar rear
]

MOSUL = (339469.0, -94071.0)  # Mosul International airfield (the red anchor)

# --- Red Nineveh town strongholds (FOB CPs): name, (x, y), cache count.
#     XY from real lat/lon via the Iraq projection (Point.from_latlng). Tal Afar is the
#     western gateway toward Syria -- the far end of the ratline, a late-arc objective.
#   name              (x, y)                 caches
STRONGHOLDS: list[tuple[str, tuple[float, float], int]] = [
    ("Hammam al-Alil", (322805.0, -81581.0), 2),
    ("Bartella", (343841.0, -73022.0), 2),
    ("Bashiqa", (355988.0, -73419.0), 2),
    ("Hamdaniya", (334903.0, -73325.0), 2),
    ("Tal Afar", (348018.0, -156505.0), 2),
]

# --- The southern front (the historical Federal Police motorway thrust): a M-113
#     front-line group whose first waypoint is at Q-West (blue) and last at Hammam
#     al-Alil (red). Waypoints trace Highway 1 / the Tigris valley NNW; only the
#     endpoints bind the front (closest-CP), the middles shape the path.
QWEST = (279544.0, -97450.0)
FRONT_PATH = [QWEST, (295500.0, -92000.0), (310000.0, -86000.0), (322805.0, -81581.0)]

# --- Blue economy: a Workshop_A factory static at two rear airfields so blue has real
#     production (a from-scratch miz has no inherited economy). Placed a short hop off
#     the field so it binds to that CP.
BLUE_FACTORIES: list[tuple[str, tuple[float, float]]] = [
    ("Baghdad Factory", (2200.0, 1800.0)),  # near Baghdad International (-142, 160)
    ("Balad Factory", (78000.0, 15500.0)),  # near Balad (75938, 13806)
]

# --- Per-stronghold COIN furniture. A garrison armor marker (fills the red frontline
#     roster -> the cell the C1 engine regenerates), an AAA marker (ZU-23 technicals),
#     and a SHORAD marker (SA-8/9/13). Mosul additionally gets a MEDIUM marker (-> SA-6),
#     the one SEAD-relevant radar site. Deterministic offsets, well inside each CP's
#     catchment (strongholds are 15+ km apart).
GARRISON_OFFSET = (300.0, 300.0)
AAA_OFFSET = (900.0, -700.0)
SHORAD_OFFSET = (-800.0, 900.0)
MERAD_OFFSET = (1600.0, 1400.0)

CACHE_OFFSETS = [
    (1400.0, 300.0),
    (-500.0, -1500.0),
    (-1300.0, 1100.0),
]


def _pt(mission: Mission, xy: tuple[float, float]) -> Point:
    return Point(xy[0], xy[1], mission.terrain)


def build() -> None:
    mission = Mission(terrain=Iraq())
    blue = CombinedJointTaskForcesBlue()
    red = CombinedJointTaskForcesRed()
    mission.coalition["blue"].add_country(blue)
    mission.coalition["red"].add_country(red)

    # Airfield ownership.
    airports = {a.id: a for a in mission.terrain.airport_list()}
    for aid in RED_AIRFIELD_IDS:
        airports[aid].set_red()
    for aid in BLUE_AIRFIELD_IDS:
        airports[aid].set_blue()

    # Red town strongholds (FOBs) + their COIN furniture + caches.
    caches = 0
    for name, xy, count in STRONGHOLDS:
        x, y = xy
        mission.vehicle_group(
            country=red, name=name, _type=Unarmed.SKP_11, position=_pt(mission, xy)
        )
        mission.vehicle_group(
            country=red,
            name=f"GARRISON {name}",
            _type=Armor.M_1_Abrams,
            position=Point(
                x + GARRISON_OFFSET[0], y + GARRISON_OFFSET[1], mission.terrain
            ),
        )
        mission.vehicle_group(
            country=red,
            name=f"AAA {name}",
            _type=AirDefence.ZSU_23_4_Shilka,
            position=Point(x + AAA_OFFSET[0], y + AAA_OFFSET[1], mission.terrain),
        )
        mission.vehicle_group(
            country=red,
            name=f"SHORAD {name}",
            _type=AirDefence.Strela_1_9P31,
            position=Point(x + SHORAD_OFFSET[0], y + SHORAD_OFFSET[1], mission.terrain),
        )
        for index in range(count):
            dx, dy = CACHE_OFFSETS[index % len(CACHE_OFFSETS)]
            mission.static_group(
                country=red,
                name=f"CACHE {name} {index + 1}",
                _type=Warehouse._Ammunition_depot,
                position=Point(x + dx, y + dy, mission.terrain),
            )
            caches += 1

    # Mosul (the red airfield anchor): garrison, guns, the SA-6 crust site, and the
    # rear depots (3 caches).
    mx, my = MOSUL
    mission.vehicle_group(
        country=red,
        name="GARRISON Mosul",
        _type=Armor.M_1_Abrams,
        position=Point(
            mx + GARRISON_OFFSET[0], my + GARRISON_OFFSET[1], mission.terrain
        ),
    )
    mission.vehicle_group(
        country=red,
        name="AAA Mosul",
        _type=AirDefence.ZSU_23_4_Shilka,
        position=Point(mx + AAA_OFFSET[0], my + AAA_OFFSET[1], mission.terrain),
    )
    mission.vehicle_group(
        country=red,
        name="SHORAD Mosul",
        _type=AirDefence.Strela_1_9P31,
        position=Point(mx + SHORAD_OFFSET[0], my + SHORAD_OFFSET[1], mission.terrain),
    )
    mission.vehicle_group(
        country=red,
        name="MERAD Mosul",
        _type=AirDefence.S_75M_Volhov,  # MEDIUM marker -> the faction's SA-6 preset
        position=Point(mx + MERAD_OFFSET[0], my + MERAD_OFFSET[1], mission.terrain),
    )
    for index in range(3):
        dx, dy = CACHE_OFFSETS[index % len(CACHE_OFFSETS)]
        mission.static_group(
            country=red,
            name=f"CACHE Mosul {index + 1}",
            _type=Warehouse._Ammunition_depot,
            position=Point(mx + dx, my + dy, mission.terrain),
        )
        caches += 1

    # The southern front (Q-West -> Hammam al-Alil): a blue M-113 front-line group.
    front = mission.vehicle_group(
        country=blue,
        name="FRONT Qayyarah-Mosul",
        _type=Armor.M_113,
        position=_pt(mission, FRONT_PATH[0]),
    )
    for wp in FRONT_PATH[1:]:
        front.add_waypoint(_pt(mission, wp))

    # Blue economy factories.
    for name, xy in BLUE_FACTORIES:
        mission.static_group(
            country=blue,
            name=name,
            _type=Fortification.Workshop_A,
            position=_pt(mission, xy),
        )

    mission.save(str(DST))
    print(
        f"Wrote {DST} ("
        f"{len(RED_AIRFIELD_IDS)} red + {len(BLUE_AIRFIELD_IDS)} blue airfields, "
        f"{len(STRONGHOLDS)} red FOBs, {caches} caches, "
        f"{len(BLUE_FACTORIES)} factories, 1 southern front)"
    )


if __name__ == "__main__":
    build()
