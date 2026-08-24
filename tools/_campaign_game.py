"""Build a FRESH game from a shipped campaign, headless.

Why this exists, and it is the important part: the doctrine-mining instruments
were first run against `.retribution` saves out of the DM's Saved Games folder,
and **those saves are hand-edited**. `initialize_turn` re-plans the ATO, so the
packages measured were machine-generated -- but every input to that planning was
not. Air-wing composition, squadron basing, aircraft counts, control-point
ownership, front lines, settings and the SAM laydown all came from a curated
state, so any measurement whose answer depends on *how much of what is where*
was measuring the DM, not the planner.

A fresh game from the shipped campaign yaml is the planner's own laydown, which
is what a doctrine claim about planner behaviour has to be tested against.

Prefer campaigns the fork did not author. Ours are tuned to fork features and
are not representative; the campaign list carries `authors:` and the ones marked
414th are the ones to avoid.

Copied in shape from `tools/system_probe.py`, which already did this.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

CAMPAIGN_DIR = _REPO_ROOT / "resources" / "campaigns"


def campaign_path(name: str) -> Path:
    """Accept a bare campaign name, a stem, or a path."""
    candidate = Path(name)
    if candidate.is_file():
        return candidate
    stem = candidate.stem if candidate.suffix else name
    return CAMPAIGN_DIR / f"{stem}.yaml"


def build_game(name: str, saved_games: Optional[str] = None) -> Any:
    """A fresh Game at turn 0 from a shipped campaign yaml."""
    os.chdir(_REPO_ROOT)

    from game import persistency
    from game.campaignloader.campaign import Campaign
    from game.factions import FACTIONS
    from game.settings import Settings
    from game.theater.start_generator import (
        GameGenerator,
        GeneratorSettings,
        ModSettings,
    )

    if saved_games is None:
        saved_games = str(Path.home() / "Saved Games" / "DCS")
    persistency.setup(saved_games, False, 0)

    campaign = Campaign.from_file(campaign_path(name))
    theater = campaign.load_theater(campaign.advanced_iads)
    air_wing_config = campaign.load_air_wing_config(theater)

    settings = Settings()
    if campaign.settings:
        settings.__dict__.update(Settings.deserialize_state_dict(campaign.settings))

    generator_settings = GeneratorSettings(
        start_date=campaign.recommended_start_date or datetime(2000, 1, 1),
        start_time=campaign.recommended_start_time,
        player_budget=campaign.recommended_player_money,
        enemy_budget=campaign.recommended_enemy_money,
        inverted=False,
        advanced_iads=campaign.advanced_iads,
        no_carrier=False,
        no_lha=False,
        no_player_navy=False,
        no_enemy_navy=False,
        tgo_config=campaign.load_ground_forces_config(),
        carrier_config=campaign.load_carrier_config(),
        squadrons_start_full=True,
    )
    game = GameGenerator(
        player=FACTIONS[campaign.recommended_player_faction],
        enemy=FACTIONS[campaign.recommended_enemy_faction],
        theater=theater,
        air_wing_config=air_wing_config,
        settings=settings,
        generator_settings=generator_settings,
        mod_settings=ModSettings(),
        campaign_name=campaign.name,
    ).generate()
    game.begin_turn_0(squadrons_start_full=True)

    # begin_turn_0 runs its own initialize_turn before the squadrons are stocked,
    # so the ATO is empty on return. One explicit pass is what the app's first
    # turn actually shows -- without it every measurement reads zero packages.
    from game.sim import GameUpdateEvents

    game.initialize_turn(GameUpdateEvents(), for_red=True, for_blue=True)
    return game
