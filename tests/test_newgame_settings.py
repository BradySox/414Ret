"""Regression tests for new-game settings construction.

Pins the fix for a launch crash: starting a new game built a fresh ``Settings``
whose plugin options were seeded with defaults, then merged the campaign's own
settings on top. The merge replaced the whole ``plugins`` dict instead of layering
the campaign's choices over the seeded defaults, so a campaign carrying an empty
(or older, partial) ``plugins`` blob dropped options it didn't mention -- and the
settings UI then raised ``KeyError`` reading the missing option (e.g.
``ctld.tailorctld``) while opening the New Game wizard.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.plugins import LuaPluginManager
from game.settings import Settings
from qt_ui.windows.newgame.WizardPages.QNewGameSettings import NewGameSettings


def _seeded_settings() -> Settings:
    # Mirror load_default_settings(): a fresh Settings with every current plugin
    # option initialized to its default.
    settings = Settings()
    LuaPluginManager.load_settings(settings)
    assert "ctld.tailorctld" in settings.plugins  # precondition
    return settings


def _campaign(settings_blob: dict[str, Any]) -> Any:
    return SimpleNamespace(settings=settings_blob)


def test_empty_campaign_plugins_keep_seeded_option_defaults() -> None:
    settings = _seeded_settings()

    NewGameSettings._load_campaign_settings(_campaign({"plugins": {}}), settings)

    # The seeded plugin options survive the merge -- no KeyError in the UI.
    assert "ctld.tailorctld" in settings.plugins
    settings.plugin_option("ctld.tailorctld")  # must not raise


def test_campaign_without_plugins_keep_seeded_option_defaults() -> None:
    settings = _seeded_settings()

    NewGameSettings._load_campaign_settings(_campaign({}), settings)

    settings.plugin_option("ctld.tailorctld")  # must not raise


def test_campaign_plugin_choices_override_but_do_not_drop_others() -> None:
    settings = _seeded_settings()
    seeded_default = settings.plugin_option("ctld")

    NewGameSettings._load_campaign_settings(
        _campaign({"plugins": {"ctld": not seeded_default}}), settings
    )

    # The campaign's explicit choice wins...
    assert settings.plugin_option("ctld") == (not seeded_default)
    # ...without dropping options the campaign didn't mention.
    settings.plugin_option("ctld.tailorctld")  # must not raise
