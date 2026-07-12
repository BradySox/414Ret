"""Campaign plugin preseeds: features that depend on a plugin runtime must ship it.

The generic frontline-artillery harassment (``artillery_base_harassment``) emits its
config into ``dcsRetribution.VietnamOps`` -- the *vietnamops plugin* owns the barrage
runtime. A player whose saved defaults disabled "Vietnam Ops" (perfectly reasonable on
a conventional-campaign squadron) would otherwise silently lose the feature: the
emitter emits, nothing consumes. Red Tide preseeds the plugin ON through its campaign
``settings.plugins`` block, which the New Game wizard layers OVER the player's saved
defaults (see ``QNewGameSettings._load_campaign_settings``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from game.campaignloader.campaign import Campaign
from game.settings import Settings

RED_TIDE = "resources/campaigns/red_tide.yaml"


def _campaign_settings() -> dict[str, Any]:
    with open(RED_TIDE, encoding="utf-8") as f:
        return yaml.safe_load(f)["settings"]


def test_red_tide_preseeds_the_vietnamops_plugin_for_artillery_harassment() -> None:
    settings = _campaign_settings()
    assert settings["artillery_base_harassment"] is True
    # The feature's runtime lives in the vietnamops plugin -- the campaign must
    # carry the plugin ON or a player default of off silently kills the feature.
    assert settings["plugins"]["vietnamops"] is True


def test_red_tide_preseeds_the_commsjam_plugin_for_enemy_comms_jamming() -> None:
    settings = _campaign_settings()
    assert settings["enemy_comms_jamming"] is True
    # §51's runtime lives in the commsjam plugin -- same saved-default-off trap
    # as the vietnamops harassment above.
    assert settings["plugins"]["commsjam"] is True


def test_red_tide_preseeds_the_mobilemissiles_plugin_for_the_scud_hunt() -> None:
    settings = _campaign_settings()
    # §49 relocates the red SS-1C Scud-B batteries in-mission; the runtime lives in
    # the mobilemissiles plugin -- same saved-default-off trap as the others.
    assert settings["mobile_missile_relocation"] is True
    assert settings["plugins"]["mobilemissiles"] is True


def test_red_tide_preseeds_the_redscramble_plugin_for_the_host_menu() -> None:
    settings = _campaign_settings()
    # §61's runtime lives in the redscramble plugin -- same saved-default-off trap
    # as the others. Preseeded ahead of the Friday 2026-07-17 regeneration so the
    # host's "give the boys something to shoot" button is armed for MP events.
    assert settings["host_red_scramble"] is True
    assert settings["plugins"]["redscramble"] is True


def test_red_tide_preseeds_c2_decapitation_effects() -> None:
    settings = _campaign_settings()
    # §52 is default OFF; Red Tide's per-base command-center network is the fit, so
    # the campaign flips it ON (pure turn-model, no plugin dependency).
    assert settings["c2_decapitation_effects"] is True


def test_red_tide_preseeds_red_intent() -> None:
    settings = _campaign_settings()
    # §55 is default OFF; Red Tide is a peer fight where red has real offensive agency,
    # and with war_economy also ON the supply->posture loop closes (a starved red digs
    # in), so the campaign flips it ON (pure turn-model, no plugin dependency).
    assert settings["red_intent"] is True


def test_red_tide_preseeds_the_opfor_qra_reserve() -> None:
    settings = _campaign_settings()
    # The Cold-War Soviet defensive posture depends on red holding a QRA alert reserve.
    # The standard default is 0; preseed it here so it survives a player resetting their
    # saved defaults toward standard (without it, red goes quiet AND passive, and the §1
    # QRA forward-defense layer has nothing to scramble to the front).
    assert settings["opfor_default_qra_reserve"] == 4


def test_red_tide_preseeds_the_era_weapon_gate() -> None:
    settings = _campaign_settings()
    # Red Tide is 1988; the era gate keeps the period jets off post-era weapons. Default
    # off and covered by no other campaign setting, so it must be preseeded to survive a
    # reset to standard defaults.
    assert settings["restrict_weapons_by_date"] is True


def test_red_tide_preseeds_munitions_scarcity() -> None:
    settings = _campaign_settings()
    # §54 is the air axis of the war economy (also preseeded): out-of-stock scarce
    # munitions degrade at load. Default off and covered by no other campaign setting.
    assert settings["restrict_weapons_by_stock"] is True
    assert settings["war_economy"] is True


def test_red_tide_fields_the_two_scud_batteries_for_the_hunt() -> None:
    # §49 only has something to relocate if the .miz actually places missile-category
    # TGOs. Red Tide's laydown carries two SS-1C Scud-B batteries; a future miz edit
    # must not silently drop them (the preseed above would then be a dead toggle).
    campaign = Campaign.from_file(Path(RED_TIDE))
    theater = campaign.load_theater(advanced_iads=True)
    missile_cps = sorted(
        cp.name
        for cp in theater.controlpoints
        for _ in cp.preset_locations.missile_sites
    )
    assert missile_cps == ["Haina", "Wittstock"]


def test_the_plugin_preseed_survives_deserialization_and_wins_the_layering() -> None:
    deserialized = Settings.deserialize_state_dict(dict(_campaign_settings()))
    campaign_plugins = deserialized.get("plugins", {})
    assert campaign_plugins.get("vietnamops") is True
    # The wizard layers the campaign's plugins dict over the player's saved
    # defaults -- a saved "vietnamops: False" must lose to the campaign preseed.
    saved_defaults = {"vietnamops": False, "vietnamops.harassGraceS": 300}
    merged = {**saved_defaults, **campaign_plugins}
    assert merged["vietnamops"] is True
    assert merged["vietnamops.harassGraceS"] == 300  # options untouched


def test_red_tide_preseeds_the_m1_tuning_batch() -> None:
    """The flown M1 (2026-07-11) tuning findings, preseeded so a NEW game gets them.

    - aewc/tanker buffers 30/25 NM: the AI depth push (2.5x) at the 80/70 defaults
      parked the red A-50/IL-78 200/175 NM back over Berlin, leaving the P-14 line
      as red's whole detection net.
    - BARCAP 45 min: a Schonefeld MiG-29 flamed out dry at ~75 min airborne; 60 min
      on-station is a whole Fulcrum+tank fuel load at the AI's patrol speed.
    """
    settings = _campaign_settings()
    assert settings["aewc_threat_buffer_min_distance"] == 30
    assert settings["tanker_threat_buffer_min_distance"] == 25
    assert settings["desired_barcap_mission_duration"] == 45


def test_red_tide_keeps_civilian_air_traffic() -> None:
    # Squadron call 2026-07-12, reversing the first M1 tuning cut: Red Tide KEEPS
    # the civilian layer (the ambient life is worth the occasional Aeroflot
    # incident; BVR discrimination past the FLOT is on the shooter). The campaign
    # must NOT preseed the gate at all -- the generic default (ON) applies.
    settings = _campaign_settings()
    assert "civilian_air_traffic" not in settings


def test_barcap_duration_preseed_deserializes_to_a_timedelta() -> None:
    # Campaign yaml carries minutes as an int; deserialize_state_dict must coerce
    # the timedelta-typed field or every patrol_duration consumer breaks.
    from datetime import timedelta

    deserialized = Settings.deserialize_state_dict(dict(_campaign_settings()))
    assert deserialized["desired_barcap_mission_duration"] == timedelta(minutes=45)


def test_civilian_traffic_gate_defaults_on_and_gates_generate() -> None:
    # The generic gate: default ON (every other campaign byte-identical), and
    # CivilianTrafficGenerator.generate() early-returns when off.
    from types import SimpleNamespace

    from game.missiongenerator.civiliantraffic import CivilianTrafficGenerator

    assert Settings().civilian_air_traffic is True

    gen: CivilianTrafficGenerator = CivilianTrafficGenerator.__new__(
        CivilianTrafficGenerator
    )
    calls: list[str] = []
    gen.game = SimpleNamespace(  # type: ignore[assignment]
        settings=SimpleNamespace(civilian_air_traffic=False)
    )
    gen.mission = SimpleNamespace(  # type: ignore[assignment]
        country=lambda name: calls.append(name)
    )
    gen.generate()
    assert calls == []  # early-returned before touching the mission
