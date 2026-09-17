"""Red Tide authors a strikeable motorpool depot (§56).

A single ``Fortification.Garage_A`` static near Haina (the forward Soviet base at
the Fulda Gap) is what the §56 loader turns into a ``MotorpoolGroundObject`` bound
to the red CP, so the feature is actually exercised in-game (checklist B8). Lock the
depot here so a future ``red_tide.miz`` re-save can't silently drop it.

Headless-verified end-to-end (2026-07-08): loaded through the real GameGenerator
pipeline, the depot binds to Haina (RED) and materialises one MotorpoolGroundObject;
its parked reserve vehicles populate as red procures armor over turns (``base.armor``
is the purchase stock, empty at turn 0 by design).
"""

from pathlib import Path

from dcs.mission import Mission
from dcs.statics import Fortification

from game.campaignloader.mizcampaignloader import MizCampaignLoader

MIZ = Path("resources/campaigns/red_tide.miz")


def test_red_tide_authors_exactly_one_motorpool_depot() -> None:
    assert MizCampaignLoader.MOTORPOOL_UNIT_TYPE == Fortification.Garage_A.id

    mission = Mission()
    mission.load_file(str(MIZ))

    garages = [
        group
        for coalition in mission.coalition.values()
        for country in coalition.countries.values()
        for group in country.static_group
        if group.units[0].type == MizCampaignLoader.MOTORPOOL_UNIT_TYPE
    ]
    assert len(garages) == 1, f"expected one motorpool depot, found {len(garages)}"
