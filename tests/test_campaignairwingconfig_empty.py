"""Test the authored-empty ``aircraft:`` key handling in CampaignAirWingConfig."""

from __future__ import annotations

from game.campaignloader.campaignairwingconfig import SquadronConfig


def test_authored_empty_aircraft_key_reads_as_any() -> None:
    """An `aircraft:` key left empty in the campaign YAML parses as None.

    It must load as [] ("any aircraft compatible with the primary task" via the
    DefaultSquadronAssigner fallback) instead of crashing New Game — Northern
    Guardian and WRL Noisy Cricket Redux ship such squadrons.
    """
    config = SquadronConfig.from_data({"primary": "Transport", "aircraft": None})
    assert config.aircraft == []
