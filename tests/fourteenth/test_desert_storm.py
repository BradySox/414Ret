"""CI lock on the Iraq "Umm al-Ma'arik (Desert Storm 1991)" campaign definition.

The will profile / phase arc degrade silently at runtime (by design), the squadron
airframes substitute silently if a faction unit goes missing, the supply routes bind by
closest-CP so a laydown edit can silently re-pair them, and the KARI IADS is authored as
.miz statics -- so the shipped campaign + the faction adds it depends on are asserted
here. Sibling of tests/fourteenth/test_tanker_war.py.
"""

import json
import zipfile
from pathlib import Path
from typing import Any

import yaml

from game.fourteenth.phases import parse_phases
from game.fourteenth.political_will import parse_will_profile

CAMPAIGN = Path("resources/campaigns/iraq_desert_storm.yaml")
FACTIONS = CAMPAIGN.parent.parent / "factions"


def _campaign() -> dict[str, Any]:
    return yaml.safe_load(CAMPAIGN.read_text(encoding="utf-8"))


def test_desert_storm_campaign_definition() -> None:
    data = _campaign()
    assert data["theater"] == "Iraq"
    assert data["recommended_player_faction"] == "NATO Desert Storm"
    assert data["recommended_enemy_faction"] == "Iraq 1991"
    # The air campaign opened 17 January 1991 (datetime form seeds the 0300 clock).
    assert str(data["recommended_start_date"]).startswith("1991-01-17")
    # KARI is a networked IADS -- the whole premise.
    assert data["advanced_iads"] is True
    assert (CAMPAIGN.parent / data["miz"]).exists()

    # The 414th feature preseeds this campaign is built around.
    for key in (
        "restrict_weapons_by_date",
        "restrict_props_by_date",
        "campaign_phases",
        "vietnam_political_will",
        "c2_decapitation_effects",
        "auto_repair_air_defenses",
        "comint_collection",
        "red_comms_net",
        "convoy_ambush",
        "host_red_scramble",
    ):
        assert data["settings"][key] is True, key
    # The s36 lesson: every preseeded feature's plugin is preseeded with it.
    plugins = data["settings"]["plugins"]
    for plugin in ("convoyambush", "mobilemissiles", "rednet", "redscramble"):
        assert plugins[plugin] is True, plugin
    assert plugins["redscramble.hostPlayers"] == "Flash"


def test_desert_storm_blue_flies_the_modern_modules() -> None:
    """The A-10C II + CH-47F squadron authoring depends on the NATO Desert Storm
    faction carrying both (added for this campaign; date-gating era-clamps them)."""
    faction = json.loads(
        (FACTIONS / "NATO_Desert_Storm.json").read_text(encoding="utf-8")
    )
    for airframe in ("A-10C Thunderbolt II (Suite 7)", "CH-47F Block I"):
        assert airframe in faction["aircrafts"], airframe

    squadrons = _campaign()["squadrons"]
    al_asad = squadrons[1]
    authored = {cfg["aircraft"][0] for cfg in al_asad}
    assert "A-10C Thunderbolt II (Suite 7)" in authored
    assert "CH-47F Block I" in authored
    # The escort-starvation fix: blue's fighter squadron stands BARCAP with the
    # air-to-air secondary that feeds every package escort.
    eagles = [cfg for cfg in al_asad if cfg["aircraft"] == ["F-15C Eagle"]]
    assert eagles and eagles[0]["primary"] == "BARCAP"
    assert eagles[0]["secondary"] == "air-to-air"


def test_desert_storm_red_fighters_are_defensively_tasked() -> None:
    """The Red Tide red-posture lesson: interceptors fly BARCAP/TARCAP primaries (the
    GCI alert force the QRA reserve staffs), never offensive fighter taskings."""
    data = _campaign()
    assert data["settings"]["opfor_default_qra_reserve"] == 4
    fighters = {
        "MiG-25PD Foxbat-E",
        "MiG-23ML Flogger-G",
        "MiG-29A Fulcrum-A",
        "MiG-21bis Fishbed-N",
        "Mirage-F1EQ",
    }
    for base_id, configs in data["squadrons"].items():
        for cfg in configs:
            aircraft = cfg.get("aircraft") or []
            if not isinstance(aircraft, list) or not aircraft:
                continue
            if aircraft[0] in fighters and cfg["primary"] != "Escort":
                assert cfg["primary"] in ("BARCAP", "TARCAP"), (base_id, aircraft)


def test_desert_storm_will_profile_is_the_coalition_story() -> None:
    profile = parse_will_profile(_campaign()["will"])
    assert profile.blue.label == "Coalition cohesion"
    assert profile.red.label == "the regime's resolve"
    # One Al-Firdos is survivable, a habit is not.
    assert profile.weights.blue_roe_violation == 3.0


def test_desert_storm_phase_arc() -> None:
    arc = parse_phases(_campaign()["phases"])
    assert [p.key for p in arc] == ["instant_thunder", "scud_hunt", "umm_al_maarik"]
    # Every phase keeps the Baghdad no-strike circle (the CDE bill, never a hard block).
    for phase in arc:
        assert any("Baghdad" in zone.name for zone in phase.restricted_zones), phase.key
    # Instant Thunder advances on IADS attrition -- the rollback coupling.
    assert arc[0].advance_when is not None
    assert arc[0].advance_when.enemy_iads_below == 0.55
    # The Scud hunt surges the red convoys it hunts.
    assert arc[1].trail_surge == 1.5


def test_desert_storm_supply_graph_covers_both_sides() -> None:
    """10 authored routes: 9 red interior corridors + the blue H-3 -> Al-Asad MSR.
    Endpoints are exact CP XY (closest-CP binding reads first/last waypoint only), so
    pin them: a laydown edit that moves a base silently re-pairs the route."""
    routes = _campaign()["supply_routes"]
    assert len(routes) == 10
    endpoints = {(tuple(r["waypoints"][0]), tuple(r["waypoints"][-1])) for r in routes}
    # The blue western MSR (H-3 -> Al-Asad, the pipeline-station road).
    assert ((-23566, -419185), (60819, -165901)) in endpoints
    # Highway 1 north: Baghdad -> Tikrit -> Qayyarah.
    assert ((-142, 160), (157133, -61805)) in endpoints
    assert ((157133, -61805), (279544, -97450)) in endpoints


def test_desert_storm_miz_authors_the_kari_network() -> None:
    """The KARI C2: an ADOC + 3 sector operations centers, comms/power relays at
    every red base, and a 4-station EWR chain -- authored as red-block groups the
    loader binds by proximity."""
    miz = CAMPAIGN.parent / "iraq_desert_storm.miz"
    mission_lua = zipfile.ZipFile(miz).read("mission").decode("utf-8", "replace")
    assert mission_lua.count('".Command Center"') >= 4
    assert mission_lua.count('"Comms tower M"') >= 9
    assert mission_lua.count('"GeneratorF"') >= 9
    assert mission_lua.count('"1L13 EWR"') >= 4
    # The Scud batteries the s49 hunt needs.
    assert mission_lua.count('"Scud_B"') >= 7
    # The Dictator-universe inheritance is gone (zones renamed to the 1991 target set).
    for legacy in ("Wadiya", "Aladeen", "Tamir Mafraad", "Allison Burgers"):
        assert legacy not in mission_lua, legacy
    for renamed in ("Saad 16", "Baba Gurgur", "Daura Oil Refinery"):
        assert renamed in mission_lua, renamed
