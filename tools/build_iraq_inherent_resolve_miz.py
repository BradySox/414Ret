"""Build resources/campaigns/iraq_inherent_resolve.miz by decorating a hand-authored base.

The Battle of Mosul, Oct 2016 -> Jul 2017 -- the 414th's second COIN campaign (sibling of
Operation Enduring Resolve). Like the ER build tool (which decorates Starfire's Shattered
Dagger laydown), this now decorates a **hand-authored base**: `iraq_inherent_resolve_base.miz`
is the miz the user positioned in the DCS Mission Editor to fit the real terrain (the 6
airfields' ownership, the original 5 red FOB strongholds, and every unit's map-fitted
placement). The base is the source of truth for everything already in it -- **edit it in the
ME, not here.** This tool only ADDS the in-between FOB strongholds that fill the long gaps
between the authored towns (the `NEW_FOBS` table below), so the corridor and the belt read as
a continuous contested area rather than isolated clusters.

Workflow: hand-tune the base in the ME -> add gap-filling FOBs here -> re-run. When the user
hand-tunes a machine-added FOB, it graduates into the base (re-export the base) and comes off
`NEW_FOBS`. Everything is deterministic (fixed offsets). Town XY come from real lat/lons
through the Iraq terrain projection (the 414th supply-line standard).

Usage: python tools/build_iraq_inherent_resolve_miz.py
"""

from __future__ import annotations

from pathlib import Path

from dcs.mapping import Point
from dcs.mission import Mission
from dcs.statics import Fortification, Warehouse
from dcs.vehicles import AirDefence, Armor, Unarmed

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "resources/campaigns/iraq_inherent_resolve_base.miz"
DST = REPO / "resources/campaigns/iraq_inherent_resolve.miz"

RED_COUNTRY = "Combined Joint Task Forces Red"

# --- Gap-filling FOB strongholds (name, (x, y)) to add to the base, each getting a light
#     garrison + guns + a strongpoint + one cache. Currently EMPTY: the first batch (Bayji,
#     Qayyarah, Hawija, Makhmur, Gwer -- the Highway-1 corridor + eastern belt gap-fillers)
#     was hand-tuned in the ME and has GRADUATED into `iraq_inherent_resolve_base.miz`. Add
#     the next batch here (from the Iraq projection) when more gaps need filling, then re-run.
NEW_FOBS: list[tuple[str, tuple[float, float]]] = []

# --- Furniture offsets (meters, mission x/y), matching the base's per-stronghold pattern:
#     two garrison groups (armor markers -> filled from the ISIS frontline roster), guns,
#     a SHORAD site, a strongpoint, and one ammo cache.
GARRISON_OFFSETS = [(300.0, 300.0), (-650.0, -450.0)]
AAA_OFFSET = (900.0, -700.0)
SHORAD_OFFSET = (-800.0, 900.0)
STRONGPOINT_OFFSET = (-1300.0, -1000.0)
CACHE_OFFSET = (1400.0, 300.0)


def build() -> None:
    mission = Mission()
    mission.load_file(str(SRC))

    red = mission.country(RED_COUNTRY)
    if red is None:
        raise RuntimeError(f"{SRC} carries no {RED_COUNTRY!r} country")

    def at(base: tuple[float, float], off: tuple[float, float]) -> Point:
        return Point(base[0] + off[0], base[1] + off[1], mission.terrain)

    for name, xy in NEW_FOBS:
        mission.vehicle_group(
            country=red,
            name=name,
            _type=Unarmed.SKP_11,
            position=Point(*xy, mission.terrain),
        )
        for i, off in enumerate(GARRISON_OFFSETS):
            mission.vehicle_group(
                country=red,
                name=f"GARRISON {name} {i + 1}",
                _type=Armor.M_1_Abrams,
                position=at(xy, off),
            )
        mission.vehicle_group(
            country=red,
            name=f"AAA {name}",
            _type=AirDefence.ZSU_23_4_Shilka,
            position=at(xy, AAA_OFFSET),
        )
        mission.vehicle_group(
            country=red,
            name=f"SHORAD {name}",
            _type=AirDefence.Strela_1_9P31,
            position=at(xy, SHORAD_OFFSET),
        )
        mission.static_group(
            country=red,
            name=f"STRONGPOINT {name}",
            _type=Fortification.Tech_combine,
            position=at(xy, STRONGPOINT_OFFSET),
        )
        mission.static_group(
            country=red,
            name=f"CACHE {name} 1",
            _type=Warehouse._Ammunition_depot,
            position=at(xy, CACHE_OFFSET),
        )

    mission.save(str(DST))
    print(
        f"Wrote {DST} (base + {len(NEW_FOBS)} in-between FOBs: {[n for n, _ in NEW_FOBS]})"
    )


if __name__ == "__main__":
    build()
