"""Test CampaignAirWingConfig.empty() — the blank-canvas air-wing config.

DefaultSquadronAssigner does ``config.by_location[control_point]``; a blank canvas
has no preconfigured squadrons, so the empty config must yield ``[]`` for any base
instead of raising ``KeyError`` (the failure that crashed the first headless run).
"""

from __future__ import annotations

from unittest.mock import MagicMock

from game.campaignloader.campaignairwingconfig import CampaignAirWingConfig


def test_empty_returns_empty_list_for_any_base() -> None:
    config = CampaignAirWingConfig.empty()
    some_base = MagicMock()
    # must not raise KeyError; missing bases read as "no squadrons here"
    assert config.by_location[some_base] == []
