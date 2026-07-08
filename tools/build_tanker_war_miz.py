"""Refresh the oil-platform AAA gun forts in ``tanker_war_1988.miz`` (in place, idempotent).

The Sassan/Sirri oil platforms of the 1988 Gulf were IRGC **gun forts** -- ZU-23 AAA on the rig
decks. This drops one **AAA site marker** (``ZSU-23-4 Shilka`` -> the generator fills it from the
red faction's AAA roster; see ``game/campaignloader/mizcampaignloader.py``'s band-marker model)
on each oil platform in the campaign miz.

**In place, idempotent, and drawing-safe.** The campaign ``.miz`` is the source of truth -- edit
its laydown *and* the hand-drawn ROE zone (the named polygon "Strait of Hormuz shipping lane",
read via ``from_drawing``) in the DCS Mission Editor. This tool loads that miz, removes any AAA it
added on a prior run, and re-adds a fresh set on the current platforms -- so re-running (e.g. to
retune ``DECK_OFFSET``) never duplicates and **never touches your ME drawings**: pydcs round-trips
the mission's drawings layer, so the shipping-lane polygon (and everything else) survives.

Placement: DCS renders a ground unit on an oil-platform deck when its coordinates fall on the
platform (verified against the paid campaigns -- e.g. FA-18C Operation Cerberus North mounts a
Silkworm + infantry on a gas platform). A small on-deck offset is used. **The on-deck render is an
in-game pass item** (it can't be flown headless); if a battery ends up in the water, nudge
``DECK_OFFSET`` and re-run.

Only AAA is added: the miz is marker-based, so infantry can't be placed (no infantry marker), and
a Silkworm on a platform would fight the coastal shoot-and-scoot (it is a ``coastal`` TGO). The 7
shore/island Silkworm sites already carry the anti-ship threat.

Run: ``python tools/build_tanker_war_miz.py``
"""

from __future__ import annotations

from pathlib import Path

from dcs.mapping import Point
from dcs.mission import Mission
from dcs.vehicles import AirDefence

REPO = Path(__file__).resolve().parent.parent
MIZ = REPO / "resources/campaigns/tanker_war_1988.miz"

RED_COUNTRY = "Combined Joint Task Forces Red"

#: Group-name prefix for the AAA this tool adds -- the key for idempotent removal.
GUNFORT_PREFIX = "GUNFORT AAA"

#: Oil/gas platform static types (the offshore strike targets the AAA defends).
PLATFORM_TYPES = {"Oil platform", "Oil rig", "Gas platform"}

#: On-deck offset (meters, mission x/y). Small enough to keep the battery on the platform
#: footprint (~40-60 m), off the platform static's exact centre so it does not clip.
DECK_OFFSET = (15.0, 12.0)


def build() -> None:
    mission = Mission()
    mission.load_file(str(MIZ))
    red = mission.country(RED_COUNTRY)
    if red is None:
        raise RuntimeError(f"{MIZ} carries no {RED_COUNTRY!r} country")

    # Idempotency: drop any AAA this tool added on a prior run before re-adding, so re-running
    # never doubles the gun forts. Everything else in the miz (drawings, laydown) is untouched.
    red.vehicle_group = [
        group
        for group in red.vehicle_group
        if not group.name.startswith(GUNFORT_PREFIX)
    ]

    platforms: list[tuple[float, float]] = []
    for static_group in red.static_group:
        for unit in static_group.units:
            if getattr(unit, "type", "") in PLATFORM_TYPES:
                platforms.append((unit.position.x, unit.position.y))
    if not platforms:
        raise RuntimeError(f"{MIZ} has no oil platforms in the {RED_COUNTRY!r} country")

    for i, (x, y) in enumerate(platforms, start=1):
        mission.vehicle_group(
            country=red,
            name=f"{GUNFORT_PREFIX} {i}",
            _type=AirDefence.ZSU_23_4_Shilka,
            position=Point(x + DECK_OFFSET[0], y + DECK_OFFSET[1], mission.terrain),
        )

    mission.save(str(MIZ))
    print(f"Refreshed {MIZ.name}: {len(platforms)} oil-platform AAA gun forts")


if __name__ == "__main__":
    build()
