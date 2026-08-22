"""Marianas - Operation Forager (1944) keeps its shape.

The campaign's CI lock. It reads the miz and the yaml directly rather than
building a Game, so it stays fast enough for every run; the things a Game would
catch that these cannot are listed in
docs/dev/design/414th-marianas-wwii-terrain-notes.md.

Three of these pin something that actually went wrong while the campaign was
being built:

- Blue asked for 20 aircraft at a 12-stand beach strip, and the second squadron
  came up with zero aircraft and no error. Parking is checked here.
- Pagan Airstrip must stay out. The landmap carries no Pagan island, so the
  airfield sits 313 km inside the sea zone. It is excluded by being left NEUTRAL
  without dynamic spawn, which is quiet enough to undo by accident.
- The AAA markers were authored as Type 96 25mm, which is the right gun and the
  wrong sentinel: MizCampaignLoader only recognises its own AAA_UNIT_TYPES, so
  all eight sites were silently dropped.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from dcs.mission import Mission

from game.campaignloader.mizcampaignloader import MizCampaignLoader

MIZ = Path("resources/campaigns/marianas_forager_1944.miz")
YAML = Path("resources/campaigns/marianas_forager_1944.yaml")

BLUE_AIRFIELDS = {"Charon Kanoa"}
RED_AIRFIELDS = {
    "Isley",
    "Kagman",
    "Marpi",
    "Ushi",
    "Airfield 3",
    "Gurguan Point",
    "Rota",
    "Agana",
    "Orote",
}


def load_mission() -> Mission:
    mission = Mission()
    mission.load_file(str(MIZ))
    return mission


def load_campaign() -> dict[str, Any]:
    return yaml.safe_load(YAML.read_text(encoding="utf-8"))


def test_the_beachhead_is_the_only_blue_field() -> None:
    airports = list(load_mission().terrain.airport_list())
    assert {a.name for a in airports if a.is_blue()} == BLUE_AIRFIELDS
    assert {a.name for a in airports if a.is_red()} == RED_AIRFIELDS


def test_pagan_is_not_a_control_point() -> None:
    """Pagan sits in the sea zone; it is excluded by being NEUTRAL and not a
    dynamic-spawn field, which is what MizCampaignLoader tests."""
    pagan = next(a for a in load_mission().terrain.airport_list() if a.name == "Pagan")
    assert not pagan.is_blue() and not pagan.is_red()
    # This is the exact predicate the loader uses to decide it is a control point.
    assert not pagan.is_neutral()


def test_every_squadron_fits_its_field() -> None:
    """A field with fewer stands than aircraft silently produces an empty
    squadron."""
    mission = load_mission()
    campaign = load_campaign()
    airports = {a.name: a for a in mission.terrain.airport_list()}

    for base, squadrons in campaign["squadrons"].items():
        airport = airports.get(base)
        if airport is None:
            continue  # the carrier; its parking is not an airport's
        wanted = sum(s["size"] for s in squadrons)
        stands = len(airport.parking_slots)
        assert (
            wanted <= stands
        ), f"{base} is asked for {wanted} aircraft but has {stands} stands"


def test_markers_use_the_sentinels_the_loader_recognises() -> None:
    mission = load_mission()
    vehicles = [
        g
        for coalition in mission.coalition.values()
        for country in coalition.countries.values()
        for g in country.vehicle_group
    ]
    statics = [
        g
        for coalition in mission.coalition.values()
        for country in coalition.countries.values()
        for g in country.static_group
    ]

    aaa = [g for g in vehicles if g.units[0].type in MizCampaignLoader.AAA_UNIT_TYPES]
    armor = [
        g
        for g in vehicles
        if g.units[0].type == MizCampaignLoader.ARMOR_GROUP_UNIT_TYPE
    ]
    strike = [
        g
        for g in statics
        if g.units[0].type == MizCampaignLoader.STRIKE_TARGET_UNIT_TYPE
    ]

    assert len(aaa) == 8, f"expected 8 AAA sites, found {len(aaa)}"
    assert len(armor) == 6, f"expected 6 garrisons, found {len(armor)}"
    assert len(strike) == 4, f"expected 4 strike targets, found {len(strike)}"


def test_the_carrier_marker_is_present() -> None:
    mission = load_mission()
    carriers = [
        g
        for coalition in mission.coalition.values()
        for country in coalition.countries.values()
        for g in country.ship_group
        if g.units[0].type == MizCampaignLoader.CV_UNIT_TYPE
    ]
    assert len(carriers) == 1
    assert carriers[0].name in load_campaign()["squadrons"]


def test_the_islands_are_joined() -> None:
    """Saipan, Tinian, Rota and Guam are only reachable from each other by sea."""
    campaign = load_campaign()
    assert len(campaign["supply_routes"]) == 6
    lanes = campaign["shipping_lanes"]
    assert len(lanes) == 3
    for lane in lanes:
        assert len(lane["waypoints"]) >= 2


def test_it_points_at_the_wwii_theater() -> None:
    campaign = load_campaign()
    # The theater key is the directory under resources/theaters, not the pydcs
    # terrain name -- MarianaIslandsWWII here would not resolve.
    assert campaign["theater"] == "MarianasWWII"
    assert Path("resources/theaters/marianaswwii/info.yaml").exists()
