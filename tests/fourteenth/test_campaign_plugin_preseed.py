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


def test_red_tide_preseeds_c2_decapitation_effects() -> None:
    settings = _campaign_settings()
    # §52 is default OFF; Red Tide's per-base command-center network is the fit, so
    # the campaign flips it ON (pure turn-model, no plugin dependency).
    assert settings["c2_decapitation_effects"] is True


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
