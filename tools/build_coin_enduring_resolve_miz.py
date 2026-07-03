"""Build resources/campaigns/coin_enduring_resolve.miz from operation_shattered_dagger.miz.

The COIN campaign fork (C3 of docs/dev/design/414th-coin-insurgent-replenishment-notes.md,
credit Starfire for the base laydown): Operation Shattered Dagger's miz, unchanged,
plus the **ammo-cache TGO markers** the C1 regen engine throttles on -- a small ring
of `Warehouse.Ammunition_depot` statics around every insurgent stronghold (the 11 red
FOBs + Farah + Tarinkot). Each becomes a real, recon-visible, strikeable ammo TGO
bound to its closest control point (`MizCampaignLoader.AMMUNITION_DEPOT_UNIT_TYPE` ->
`preset_locations.ammunition_depots` -> `generate_ammunition_depots`, one TGO per
marker, deterministic).

The cache laydown table below is the single place to edit when rebalancing cache
density. Deterministic (fixed offsets, no randomness); re-run with any pydcs that
round-trips the miz -- the release package works, the retribution fork is not
required for authoring.

Usage: python tools/build_coin_enduring_resolve_miz.py
"""

from pathlib import Path

from dcs.mapping import Point
from dcs.mission import Mission
from dcs.planes import F_15C
from dcs.ships import Stennis
from dcs.statics import Warehouse
from dcs.vehicles import AirDefence

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "resources/campaigns/operation_shattered_dagger.miz"
DST = REPO / "resources/campaigns/coin_enduring_resolve.miz"

RED_COUNTRY = "Combined Joint Task Forces Red"
BLUE_COUNTRY = "Combined Joint Task Forces Blue"

# --- Off-map blue air (miz-loader sentinel: an F-15C plane group). The 2006 OEF
# --- reality: carrier Hornets from the Arabian Sea and CENTAF heavies/tankers from
# --- the Gulf reached the theater from OFF the map. Positions sit outside the
# --- playbox (south / west of Farah) but on valid terrain.
OFF_MAP_SPAWNS: list[tuple[str, tuple[float, float]]] = [
    ("CENTAF Al Udeid", (-170000.0, -440000.0)),
]

#: A REAL carrier in the Gulf of Oman (user-proven position 2026-07-03 -- a Stennis
#: placed in the DCS editor at this point floats; Retribution's landmap has no sea
#: polys down here, which is why is_in_sea says no, but carrier CPs come straight
#: from this miz sentinel and DCS owns the water). ~800 km to the Helmand box --
#: the real OEF carrier-cycle distance; the CENTAF tanker bridge makes it work.
#: Position updated 2026-07-03 from the user's second proof miz; the carrier sits
#: inside the drawn SAFE TRANSIT CORRIDOR (two editor lines): west wall y ~ -246 km
#: (x -499k..-956k), east wall y ~ +22..+37 km (x -442k..-939k) -- the lane runs
#: from the stronghold belt straight south to the sea, and carrier cycles fly it.
CARRIER = ("CVN-74 John C. Stennis", (-1046758.0, -99755.0))

# --- Red air defenses (era-honest 2006: guns and IR SAMs, NO radar SAMs -- no SEAD
# --- game, the flak/MANPADS envelope is the honesty). Marker types follow
# --- game/campaignloader/mizcampaignloader.py: ZSU-23 = an AAA site the generator
# --- fills from the faction's AAA roster (ZU-23s, ERO technicals); Strela-1 = a
# --- SHORAD site (SA-9). Every stronghold gets guns; the five anchors get SA-9s.
AAA_OFFSET = (900.0, -700.0)
SHORAD_OFFSET = (-800.0, 900.0)
SHORAD_STRONGHOLDS = {
    "Farah",
    "Tarinkot",
    "FOB Jackson",
    "FOB Zeebrugge",
    "FOB Frontenac",
}

# --- The cache laydown. Stronghold centers are the red FOB markers / airfields in
# --- the source miz (verified 2026-07-02); each gets `count` Ammunition-depot
# --- statics on a fixed offset ring so the C1 cache throttle has something real to
# --- lose. Airfield strongholds get 3 (the rear depots), forward FOBs 2.
#   name                     (x, y)                        count
STRONGHOLD_CACHES: list[tuple[str, tuple[float, float], int]] = [
    ("Farah", (-178644.1, -378451.5), 3),
    ("Tarinkot", (-148524.9, -31352.2), 3),
    ("FOB Delaram II", (-203597.5, -258944.7), 2),
    ("ANP Hill", (-174184.4, -162657.2), 2),
    ("Kamp Hadrian", (-146856.9, -66510.4), 2),
    ("Firebase Cobra", (-111672.2, -60214.9), 2),
    ("FOB Anaconda", (-108190.8, 40752.3), 2),
    ("FOB Tobruk", (-136095.2, -337239.4), 2),
    ("FOB Frontenac", (-231043.6, -30347.7), 2),
    ("FOB Jackson", (-209298.7, -127205.1), 2),
    ("FOB Zeebrugge", (-181518.8, -101421.9), 2),
    ("FOB Martello", (-189961.0, -7031.2), 2),
    ("FOB Geronimo", (-285099.2, -180708.9), 2),
]

#: Fixed offset ring (meters, mission x/y) -- caches sit ~1.2-1.6 km off the
#: stronghold center at spread bearings, far from the next CP (strongholds are
#: 30+ km apart) so closest-CP binding is unambiguous.
CACHE_OFFSETS = [
    (1400.0, 300.0),
    (-500.0, -1500.0),
    (-1300.0, 1100.0),
]

#: Explicit cache positions overriding the offset ring. FOB Geronimo's caches hide
#: INSIDE the Lashkar Gah population-center ROE ring (the town sits ~20 km NE of
#: the FOB; both points are ~15-20 km from Geronimo vs ~38 km from Camp Bastion,
#: so closest-CP binding stays Geronimo): starving Geronimo means striking in-town
#: and paying mandate -- the hearts-and-minds dilemma the ring exists to price.
CACHE_POSITION_OVERRIDES: dict[str, list[tuple[float, float]]] = {
    "FOB Geronimo": [
        (-272000.0, -173000.0),  # Lashkar Gah (ring center -267202,-170619)
        (-271000.0, -192500.0),  # Marjah (ring center -271880,-193810)
    ],
}


def build() -> None:
    mission = Mission()
    mission.load_file(str(SRC))

    red = mission.country(RED_COUNTRY)
    if red is None:
        raise RuntimeError(f"{SRC} carries no {RED_COUNTRY!r} country")

    placed = 0
    for stronghold, (x, y), count in STRONGHOLD_CACHES:
        overrides = CACHE_POSITION_OVERRIDES.get(stronghold)
        for index in range(count):
            if overrides is not None:
                cx, cy = overrides[index % len(overrides)]
            else:
                dx, dy = CACHE_OFFSETS[index % len(CACHE_OFFSETS)]
                cx, cy = x + dx, y + dy
            mission.static_group(
                country=red,
                name=f"CACHE {stronghold} {index + 1}",
                _type=Warehouse._Ammunition_depot,
                position=Point(cx, cy, mission.terrain),
            )
            placed += 1

    blue = mission.country(BLUE_COUNTRY)
    if blue is None:
        raise RuntimeError(f"{SRC} carries no {BLUE_COUNTRY!r} country")
    for name, (x, y) in OFF_MAP_SPAWNS:
        mission.flight_group_inflight(
            country=blue,
            name=name,
            aircraft_type=F_15C,
            position=Point(x, y, mission.terrain),
            altitude=6096,
        )
    carrier_name, (cx, cy) = CARRIER
    mission.ship_group(
        country=blue,
        name=carrier_name,
        _type=Stennis,
        position=Point(cx, cy, mission.terrain),
    )

    aaa = 0
    shorad = 0
    for stronghold, (x, y), _count in STRONGHOLD_CACHES:
        mission.vehicle_group(
            country=red,
            name=f"AAA {stronghold}",
            _type=AirDefence.ZSU_23_4_Shilka,
            position=Point(x + AAA_OFFSET[0], y + AAA_OFFSET[1], mission.terrain),
        )
        aaa += 1
        if stronghold in SHORAD_STRONGHOLDS:
            mission.vehicle_group(
                country=red,
                name=f"SHORAD {stronghold}",
                _type=AirDefence.Strela_1_9P31,
                position=Point(
                    x + SHORAD_OFFSET[0], y + SHORAD_OFFSET[1], mission.terrain
                ),
            )
            shorad += 1

    mission.save(str(DST))
    print(
        f"Wrote {DST} ({placed} caches, {aaa} AAA + {shorad} SHORAD sites, "
        f"{len(OFF_MAP_SPAWNS)} off-map spawns, 1 carrier)"
    )


if __name__ == "__main__":
    build()
