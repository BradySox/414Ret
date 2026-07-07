"""Build ``tanker_war_1988.miz`` from the Noisy Cricket Redux base + oil-platform gun forts.

The Sassan/Sirri oil platforms of the 1988 Gulf were IRGC **gun forts** -- ZU-23 AAA on the
rig decks. This tool takes the Redux campaign miz (the base laydown the Tanker War forks) and
ADDS one **AAA site marker** (``ZSU-23-4 Shilka`` -> the generator fills it from the red
faction's AAA roster; see ``game/campaignloader/mizcampaignloader.py``'s band-marker model) on
each oil platform, then writes the campaign miz. SRC -> DST, so it is idempotent: re-running
always reproduces the same output from the pristine base -- **edit + re-run, never hand-edit
``tanker_war_1988.miz``**.

Placement: DCS renders a ground unit on an oil-platform deck when its coordinates fall on the
platform (verified against the paid campaigns -- e.g. FA-18C Operation Cerberus North mounts a
Silkworm + infantry on a gas platform). A small on-deck offset is used. **The actual on-deck
render is an in-game pass item** (it can't be flown headless); if a battery ends up in the
water, nudge ``DECK_OFFSET`` or place them by eye in the ME.

Only AAA is added: the campaign miz is marker-based, so infantry cannot be placed (no infantry
marker), and a Silkworm on a platform would fight the coastal shoot-and-scoot (it is a
``coastal`` TGO). The 7 shore/island Silkworm sites already carry the anti-ship threat.

Run: ``python tools/build_tanker_war_miz.py``
"""

from __future__ import annotations

from pathlib import Path

from dcs.mapping import Point
from dcs.mission import Mission
from dcs.vehicles import AirDefence

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "resources/campaigns/WRL_Operation_Noisy_Cricket_Redux.miz"
DST = REPO / "resources/campaigns/tanker_war_1988.miz"

RED_COUNTRY = "Combined Joint Task Forces Red"

#: Oil/gas platform static types (the offshore strike targets the AAA defends).
PLATFORM_TYPES = {"Oil platform", "Oil rig", "Gas platform"}

#: On-deck offset (meters, mission x/y). Small enough to keep the battery on the platform
#: footprint (~40-60 m), off the platform static's exact centre so it does not clip.
DECK_OFFSET = (15.0, 12.0)


def build() -> None:
    mission = Mission()
    mission.load_file(str(SRC))
    red = mission.country(RED_COUNTRY)
    if red is None:
        raise RuntimeError(f"{SRC} carries no {RED_COUNTRY!r} country")

    platforms: list[tuple[float, float]] = []
    for sg in red.static_group:
        for unit in sg.units:
            if getattr(unit, "type", "") in PLATFORM_TYPES:
                platforms.append((unit.position.x, unit.position.y))
    if not platforms:
        raise RuntimeError(f"{SRC} has no oil platforms in the {RED_COUNTRY!r} country")

    for i, (x, y) in enumerate(platforms, start=1):
        mission.vehicle_group(
            country=red,
            name=f"GUNFORT AAA {i}",
            _type=AirDefence.ZSU_23_4_Shilka,
            position=Point(x + DECK_OFFSET[0], y + DECK_OFFSET[1], mission.terrain),
        )

    mission.save(str(DST))
    print(f"Wrote {DST.name}: {len(platforms)} oil-platform AAA gun forts added")


if __name__ == "__main__":
    build()
