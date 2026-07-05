"""Build resources/campaigns/iraq_inherent_resolve.miz from scratch on the Iraq map.

The Battle of Mosul, Oct 2016 -> Jul 2017 -- the 414th's second COIN campaign (sibling
of Operation Enduring Resolve). Unlike the ER build tool (which *decorated* Starfire's
Shattered Dagger laydown), there is no pre-authored Mosul miz, so this generates the whole
laydown headlessly via pydcs.

The caliphate holds the **whole northern belt** (Mosul, Erbil, Kirkuk/K1, Bashur,
Sulaimaniyah, Al-Sahra) plus a cluster of Nineveh town FOBs; blue holds the south (Q-West
the forward airhead, Balad/Baghdad/Taji/Taqaddum the rear) and grinds north on **two
fronts** -- Q-West -> the Mosul ring, and Balad -> Al-Sahra (the Tikrit axis). Every red
stronghold is furnished with a real garrison (armor/technicals filled from the ISIS roster),
guns, a SHORAD site, a strongpoint, and the ammo caches the C1 regen throttle feeds on;
Mosul and Kirkuk anchor the thin SA-6 radar crust. The red-red belt/ratline connectivity is
authored in the campaign yaml's `supply_routes`.

Everything is deterministic (fixed offsets, no randomness). Stronghold XY were derived from
the towns' real lat/lons through the Iraq terrain projection (the 414th supply-line
standard); airfield XY are the terrain airport positions. Edit the tables and re-run.

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

# --- Airfield ownership (terrain airport ids). Kept deliberately SPARSE -- only 6
#     airfields are drawn as control points (every other terrain airport is left unset).
#     The caliphate holds three anchors down the belt; blue holds three southern fields
#     and grinds north up Highway 1. Red *presence* between the anchors is carried by
#     FOBs, not by owning every airstrip.
RED_AIRFIELD_IDS = [
    3,  # Mosul International -- the anchor + SA-6
    4,  # Erbil International -- the NE anchor
    10,  # Kirkuk International -- the central anchor + SA-6
]
BLUE_AIRFIELD_IDS = [
    8,  # Balad -- the forward field + the player's fast air
    13,  # Al-Taquddum -- the strike / coalition-CAS field
    2,  # Baghdad International -- support (tankers / AWACS / CSAR)
]

# --- Red strongholds to FURNISH: (name, (x, y), is_fob, caches, has_sa6). The 3 airfields
#     are already red via ownership above; the FOB towns get an SKP-11 marker to become CPs.
#     Airfield XY are terrain airport positions; town XY are from real lat/lon. FOBs (not
#     more airfields) carry red presence: two Highway-1 steps (Tikrit, Shirqat) up from the
#     Balad front, plus the tight Nineveh ring around Mosul.
#   name              (x, y)                  is_fob caches  SA-6
RED_STRONGHOLDS: list[tuple[str, tuple[float, float], bool, int, bool]] = [
    ("Mosul", (339469.0, -94071.0), False, 3, True),
    ("Erbil", (330838.0, -22360.0), False, 2, False),
    ("Kirkuk", (245434.0, 12825.0), False, 2, True),
    ("Tikrit", (150201.0, -49014.0), True, 2, False),
    ("Shirqat", (264800.0, -85078.0), True, 2, False),
    ("Hammam al-Alil", (322805.0, -81581.0), True, 2, False),
    ("Bartella", (343841.0, -73022.0), True, 2, False),
    ("Tal Afar", (348018.0, -156505.0), True, 2, False),
]

# --- The front (a blue M-113 front-line group; first waypoint at the blue CP, last at the
#     red CP -- only the endpoints bind the front, the middles shape the path). One axis:
#     Balad north up Highway 1 to the Tikrit FOB, the historical Baghdad -> Mosul advance.
FRONTS: list[tuple[str, list[tuple[float, float]]]] = [
    (
        "FRONT Balad-Tikrit",
        [
            (75938.0, 13806.0),
            (100000.0, -12000.0),
            (128000.0, -33000.0),
            (150201.0, -49014.0),
        ],
    ),
]

# --- Blue economy: a Workshop_A factory static at two rear airfields so blue has real
#     production. Placed a short hop off the field so it binds to that CP.
BLUE_FACTORIES: list[tuple[str, tuple[float, float]]] = [
    ("Baghdad Factory", (2200.0, 1800.0)),  # near Baghdad International (-142, 160)
    ("Balad Factory", (78000.0, 15500.0)),  # near Balad (75938, 13806)
]

# --- Per-stronghold furniture offsets (meters, mission x/y). TWO garrison groups now
#     (armor/technicals filled from the ISIS roster), guns, a SHORAD site, and a
#     strongpoint -- so each objective reads as an occupied position, not a lone marker.
GARRISON_OFFSETS = [(300.0, 300.0), (-650.0, -450.0)]
AAA_OFFSET = (900.0, -700.0)
SHORAD_OFFSET = (-800.0, 900.0)
MERAD_OFFSET = (1600.0, 1400.0)
STRONGPOINT_OFFSET = (-1300.0, -1000.0)

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

    caches = 0
    garrisons = 0
    for name, (x, y), is_fob, cache_count, has_sa6 in RED_STRONGHOLDS:
        # Town strongholds need an SKP-11 marker to become FOB control points; airfields
        # are already red via ownership.
        if is_fob:
            mission.vehicle_group(
                country=red,
                name=name,
                _type=Unarmed.SKP_11,
                position=_pt(mission, (x, y)),
            )
        # Two garrison groups (armor markers -> filled from the red frontline roster:
        # technicals, gun trucks, the VBIED).
        for i, (gx, gy) in enumerate(GARRISON_OFFSETS):
            mission.vehicle_group(
                country=red,
                name=f"GARRISON {name} {i + 1}",
                _type=Armor.M_1_Abrams,
                position=Point(x + gx, y + gy, mission.terrain),
            )
            garrisons += 1
        # Guns + a SHORAD site.
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
        # A strongpoint (strike target) -- an objective to hit, not just a marker.
        mission.static_group(
            country=red,
            name=f"STRONGPOINT {name}",
            _type=Fortification.Tech_combine,
            position=Point(
                x + STRONGPOINT_OFFSET[0], y + STRONGPOINT_OFFSET[1], mission.terrain
            ),
        )
        # The thin SA-6 radar crust anchors (Mosul + Kirkuk) -- the SEAD job.
        if has_sa6:
            mission.vehicle_group(
                country=red,
                name=f"MERAD {name}",
                _type=AirDefence.S_75M_Volhov,  # MEDIUM marker -> the faction's SA-6 preset
                position=Point(
                    x + MERAD_OFFSET[0], y + MERAD_OFFSET[1], mission.terrain
                ),
            )
        # Ammo caches.
        for index in range(cache_count):
            dx, dy = CACHE_OFFSETS[index % len(CACHE_OFFSETS)]
            mission.static_group(
                country=red,
                name=f"CACHE {name} {index + 1}",
                _type=Warehouse._Ammunition_depot,
                position=Point(x + dx, y + dy, mission.terrain),
            )
            caches += 1

    # The fronts (blue M-113 front-line groups).
    for front_name, path in FRONTS:
        front = mission.vehicle_group(
            country=blue,
            name=front_name,
            _type=Armor.M_113,
            position=_pt(mission, path[0]),
        )
        for wp in path[1:]:
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
    fobs = sum(1 for s in RED_STRONGHOLDS if s[2])
    print(
        f"Wrote {DST} ("
        f"{len(RED_AIRFIELD_IDS)} red + {len(BLUE_AIRFIELD_IDS)} blue airfields, "
        f"{fobs} red FOBs, {len(RED_STRONGHOLDS)} furnished strongholds, "
        f"{garrisons} garrisons, {caches} caches, "
        f"{len(BLUE_FACTORIES)} factories, {len(FRONTS)} fronts)"
    )


if __name__ == "__main__":
    build()
