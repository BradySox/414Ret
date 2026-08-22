"""Build ``resources/campaigns/marianas_forager_1944.miz``.

Operation Forager, 15 June 1944. Blue holds the Charan Kanoa beachhead on Saipan
and a carrier offshore; red holds the other eight fields across Saipan, Tinian,
Rota and Guam.

The miz is a marker mission, not a playable one: ``MizCampaignLoader`` reads
airfield coalitions and a handful of sentinel unit types out of it and builds the
theater from that. Roads and sea lanes live in the campaign yaml instead
(``supply_routes`` and ``shipping_lanes``), which is why none are authored here.

Run from the repo root:

    python tools/build_marianas_forager_miz.py

Never hand-edit the .miz -- re-run this.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

import dcs.countries as countries  # noqa: E402
from dcs.mapping import Point  # noqa: E402
from dcs.mission import Mission  # noqa: E402
from dcs.ships import Stennis  # noqa: E402
from dcs.terrain import MarianaIslandsWWII  # noqa: E402
from dcs.statics import Fortification  # noqa: E402
from dcs.vehicles import AirDefence, Armor  # noqa: E402

DEST = _REPO_ROOT / "resources/campaigns/marianas_forager_1944.miz"

# 15 June 1944: the 2nd and 4th Marine Divisions are ashore on Saipan's west coast
# at Chalan Kanoa and nowhere else. Everything north, south and across the strait
# is still held.
BLUE_AIRFIELDS = ("Charon Kanoa",)
RED_AIRFIELDS = (
    "Isley",  # Aslito, the prize -- taken 18 June
    "Kagman",
    "Marpi",
    "Ushi",  # Tinian's North Field
    "Airfield 3",
    "Gurguan Point",  # Tinian's West Field
    "Rota",  # bypassed in reality, garrisoned to the end
    "Agana",
    "Orote",  # Guam, retaken from 21 July
)

# Pagan is deliberately absent from both lists. The landmap carries no Pagan
# island, so its airstrip sits 313 km inside the sea zone -- see
# docs/dev/design/414th-marianas-wwii-terrain-notes.md. It is left NEUTRAL.

# Task Force 58 stood west of Saipan covering the landings. Far enough offshore to
# be a transit, close enough for the Corsairs to reach the island.
CARRIER_POSITION = Point(183_000, 62_000, MarianaIslandsWWII())

# Japanese AA, anchored on the field it defends and offset so the guns sit clear of
# the runway. The battery itself comes from the faction's Japanese Flak preset
# group; these are only markers saying "an AAA site belongs here". The marker has
# to be one of MizCampaignLoader.AAA_UNIT_TYPES -- flak18 is the only WW2 gun in
# that set, and a Type 96 marker is silently ignored.
AAA_SITES: tuple[tuple[str, str, tuple[int, int]], ...] = (
    ("Isley AAA", "Isley", (1400, -900)),
    ("Kagman AAA", "Kagman", (-1200, 1100)),
    ("Marpi AAA", "Marpi", (-1000, -1200)),
    ("Ushi AAA", "Ushi", (1500, 1000)),
    ("Gurguan Point AAA", "Gurguan Point", (-1300, -1000)),
    ("Rota AAA", "Rota", (1200, 1200)),
    ("Agana AAA", "Agana", (1100, -1300)),
    ("Orote AAA", "Orote", (-1400, 900)),
)

# The garrison itself. Saipan is where the ground war is, so that is where the
# defenders are; Tinian and Guam get one each so a landing there is not walked onto.
# The marker is the loader's sentinel; the units generated are the faction's.
GARRISONS: tuple[tuple[str, str, tuple[int, int]], ...] = (
    ("Aslito Garrison", "Isley", (-1800, 1600)),
    ("Nafutan Garrison", "Isley", (-3400, -1200)),
    ("Tapotchau Garrison", "Kagman", (-2600, -1900)),
    ("Marpi Garrison", "Marpi", (1500, 900)),
    ("Tinian Garrison", "Ushi", (-2200, -1700)),
    ("Orote Garrison", "Orote", (1700, 1400)),
)

# The garrison's fixed installations. Chosen because a 1944 island war is fought
# against supply, not against radar.
STRIKE_TARGETS: tuple[tuple[str, str, tuple[int, int]], ...] = (
    ("Garapan Supply Dump", "Isley", (6200, 3400)),
    ("Tanapag Harbour Stores", "Marpi", (-5600, -3900)),
    ("Tinian Sugar Mill", "Gurguan Point", (3100, 2600)),
    ("Sumay Naval Depot", "Orote", (900, -2100)),
)


def offset_from(mission: Mission, airfield: str, dx: int, dy: int) -> Point:
    base = mission.terrain.airports[airfield].position
    return Point(base.x + dx, base.y + dy, mission.terrain)


def main() -> None:
    mission = Mission(MarianaIslandsWWII())
    # A fresh pydcs mission has neither CJTF country, and the loader reads only
    # those two.
    mission.coalition["blue"].add_country(countries.CombinedJointTaskForcesBlue())
    mission.coalition["red"].add_country(countries.CombinedJointTaskForcesRed())
    blue = mission.country("Combined Joint Task Forces Blue")
    red = mission.country("Combined Joint Task Forces Red")

    for name in BLUE_AIRFIELDS:
        mission.terrain.airports[name].set_blue()
    for name in RED_AIRFIELDS:
        mission.terrain.airports[name].set_red()

    # The Stennis is the loader's sentinel for "a carrier belongs here". The hull
    # actually generated is the faction's, which for USA 1944 (Marianas) is the
    # Essex.
    mission.ship_group(blue, "Carrier Task Force 58", Stennis, CARRIER_POSITION, 1)

    for name, airfield, (dx, dy) in AAA_SITES:
        mission.vehicle_group(
            red, name, AirDefence.flak18, offset_from(mission, airfield, dx, dy)
        )

    for name, airfield, (dx, dy) in GARRISONS:
        mission.vehicle_group(
            red, name, Armor.M_1_Abrams, offset_from(mission, airfield, dx, dy)
        )

    # Strike targets are statics, not vehicles -- the loader reads them off
    # static_group.
    for name, airfield, (dx, dy) in STRIKE_TARGETS:
        mission.static_group(
            red,
            name,
            Fortification.Tech_combine,
            offset_from(mission, airfield, dx, dy),
        )

    DEST.parent.mkdir(parents=True, exist_ok=True)
    mission.save(str(DEST))
    print(f"wrote {DEST}")

    check = Mission()
    check.load_file(str(DEST))
    blue_af = [a.name for a in check.terrain.airport_list() if a.is_blue()]
    red_af = [a.name for a in check.terrain.airport_list() if a.is_red()]
    neutral = [a.name for a in check.terrain.airport_list() if a.is_neutral()]
    print(f"  blue    {blue_af}")
    print(f"  red     {red_af}")
    print(f"  neutral {neutral}")


if __name__ == "__main__":
    main()
