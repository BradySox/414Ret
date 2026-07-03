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
from dcs.statics import Warehouse

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "resources/campaigns/operation_shattered_dagger.miz"
DST = REPO / "resources/campaigns/coin_enduring_resolve.miz"

RED_COUNTRY = "Combined Joint Task Forces Red"

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

    mission.save(str(DST))
    print(
        f"Wrote {DST} ({placed} cache markers across {len(STRONGHOLD_CACHES)} strongholds)"
    )


if __name__ == "__main__":
    build()
