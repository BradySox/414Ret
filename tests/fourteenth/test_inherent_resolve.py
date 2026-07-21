"""CI lock on the Iraq COIN campaign ("Operation Inherent Resolve") authored blocks.

A typo in the will profile or the phase arc degrades silently at runtime (by design),
so the shipped YAML is asserted here -- the sibling of
tests/fourteenth/test_coin.py::test_enduring_resolve_campaign_definition.
"""

from pathlib import Path

import yaml

from game.fourteenth.political_will import parse_will_profile
from game.fourteenth.red_tempo import parse_red_tempo

CAMPAIGN = Path("resources/campaigns/iraq_inherent_resolve.yaml")


def test_inherent_resolve_campaign_definition() -> None:
    data = yaml.safe_load(CAMPAIGN.read_text(encoding="utf-8"))

    assert data["theater"] == "Iraq"

    # The whole COIN stack preseeds on.
    for key in (
        "coin_insurgency",
        "coin_reinfiltration",
        "coin_ied",
        "coin_hvt",
        "coin_dispersed_cells",
        "vietnam_political_will",
        "vietnam_convoy_interdiction",
        "vietnam_airbase_harassment",
        "high_digit_sams",  # the ISIS faction's ERO technicals are HDS content
    ):
        assert data["settings"][key] is True, key

    # Unlike Enduring Resolve, this is a land campaign -- no off-shore carrier.
    assert not data["settings"].get("long_range_carrier_ops", False)

    # The generator decorates a hand-authored base miz; both ship next to the yaml.
    assert (CAMPAIGN.parent / data["miz"]).exists()
    assert (CAMPAIGN.parent / "iraq_inherent_resolve_base.miz").exists()
    # Small real income (the C1 regen engine is the real supply; procurement is a trickle).
    assert data["recommended_enemy_money"] > 0
    # The authored coalition + insurgent factions ship with the campaign.
    assert data["recommended_player_faction"] == "CJTF-OIR 2016"
    assert data["recommended_enemy_faction"] == "Islamic State 2016"
    factions = CAMPAIGN.parent.parent / "factions"
    assert (factions / "cjtf_oir_2016.json").exists()
    assert (factions / "isis_2016.json").exists()

    # The red<->red supply graph, routed through the in-between towns: the Highway-1 corridor
    # (Tikrit -> Bayji -> Shirqat -> Qayyarah -> Hammam al-Alil -> Mosul), the Nineveh ring
    # (Bartella + the Tal Afar ratline), the NE belt (Mosul -> Gwer -> Erbil -> Kirkuk), and
    # the bridges (Makhmur, Hawija) tying the eastern belt into the corridor — plus the two
    # BLUE rear-corridor roads (Baghdad -> Balad up Highway 1, Baghdad -> Al-Taquddum out
    # Highway 10) that the §50 escort convoys run (a blue->blue road is the feature's
    # hard prerequisite; without one it silently no-ops).
    assert len(data["supply_routes"]) == 16
    for route in data["supply_routes"]:
        assert len(route["waypoints"]) >= 2

    # One front, up Highway 1: Balad -> Tikrit.
    assert "Tikrit" in data["control_point_strengths"]

    # Airfields are kept sparse and blue bases only from the south: no squadron is fragged
    # from Qayyarah West (id 6, dropped) or the now-red Erbil (id 4).
    assert 6 not in data["squadrons"]
    assert 4 not in data["squadrons"]

    profile = parse_will_profile(data["will"])
    assert profile.blue.label == "The Coalition's mandate"
    assert profile.red.label == "the caliphate's resolve"
    assert profile.weights.red_cache_lost == 4.0
    assert profile.weights.red_ground_unit_lost == 0.05  # body count buys nothing
    assert profile.weights.blue_passive_regen == 0.0  # time drains a mandate

    # The East Mosul push surges the caliphate's supply down the ratline (§35).
    windows = parse_red_tempo(data["red_tempo"])
    assert [w.from_turn for w in windows] == [6]
    assert windows[0].name == "East Mosul"
    assert windows[0].trail_surge == 2.0
