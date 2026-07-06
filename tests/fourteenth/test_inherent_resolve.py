"""CI lock on the Iraq COIN campaign ("Operation Inherent Resolve") authored blocks.

A typo in the will profile or the phase arc degrades silently at runtime (by design),
so the shipped YAML is asserted here -- the sibling of
tests/fourteenth/test_coin.py::test_enduring_resolve_campaign_definition.
"""

from pathlib import Path

import yaml

from game.fourteenth.phases import parse_phases
from game.fourteenth.political_will import parse_will_profile

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
        "campaign_phases",
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
    assert profile.weights.blue_roe_violation == 1.0  # CDE pressure, not taboo
    assert profile.weights.red_ground_unit_lost == 0.05  # body count buys nothing
    assert profile.weights.blue_passive_regen == 0.0  # time drains a mandate

    arc = parse_phases(data["phases"])
    assert [phase.key for phase in arc] == ["isolation", "east_mosul", "west_mosul"]
    # The Mosul positive-control box is permanent; the West Mosul phase adds the tight
    # Old City box on top. Never lock a target class -- the caches stay legal targets.
    zone_counts = [len(phase.restricted_zones) for phase in arc]
    assert zone_counts == [1, 1, 2]
    for phase in arc:
        assert phase.locked_target_classes == ()
        assert phase.free_fire_zones == ()  # no inverted ROE
        for z in phase.restricted_zones:
            assert z.kind == "box"
            assert z.x is not None and z.y is not None
            assert z.width_nm > 0.0 and z.height_nm > 0.0
    # Mosul is always positive-control; the Old City appears only in West Mosul.
    assert any(z.name.startswith("Mosul") for z in arc[0].restricted_zones)
    assert any("Old City" in z.name for z in arc[2].restricted_zones)
