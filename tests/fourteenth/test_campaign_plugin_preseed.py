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

from typing import Any

import yaml

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
