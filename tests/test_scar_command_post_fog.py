"""SCAR campaign engine — command-post intel fog (Phase 1).

Capturing an enemy commander on a SCAR sortie reveals the enemy's command posts.
Until then (with the ``scar_command_post_intel`` setting on) command posts stay
hidden via ``known_for``. This is gated OFF by default and provisional pending
the SME ruling on reveal scope/permanence/depth; these tests pin the wiring.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock

from dcs.mapping import Point

from game.sim.missionresultsprocessor import MissionResultsProcessor
from game.theater import Player
from game.theater.controlpoint import OffMapSpawn
from game.theater.presetlocation import PresetLocation
from game.theater.theatergroundobject import BuildingGroundObject
from game.utils import Heading


class _EnemyCommandPost(BuildingGroundObject):
    def is_friendly(self, to_player: Player) -> bool:
        return False


def _command_post(*, setting_on: bool, captured: bool) -> BuildingGroundObject:
    location = PresetLocation(
        name="cp-target",
        position=Point(0, 0, None),  # type: ignore[arg-type]
        heading=Heading(0),
    )
    control_point = OffMapSpawn(
        name="enemy-cp",
        position=Point(0, 0, None),  # type: ignore[arg-type]
        theater=None,  # type: ignore[arg-type]
        starts_blue=Player.RED,
    )
    tgo = _EnemyCommandPost(
        name="Enemy Command Post",
        category="commandcenter",
        location=location,
        control_point=control_point,
        task=None,
    )
    # known_for() reaches control_point.coalition.game.settings + .opponent.
    tgo.control_point = cast(
        Any,
        SimpleNamespace(
            coalition=SimpleNamespace(
                game=SimpleNamespace(
                    settings=SimpleNamespace(
                        scar_command_post_intel=setting_on,
                        recon_intel_fog=True,
                    )
                ),
                opponent=SimpleNamespace(captured_commander=captured),
            )
        ),
    )
    return tgo


def test_command_post_hidden_until_commander_captured() -> None:
    tgo = _command_post(setting_on=True, captured=False)
    assert tgo.known_for(Player.BLUE) is False  # hidden until capture
    assert tgo.known_for(None) is True  # omniscient (AI/planner) always knows


def test_command_post_revealed_after_capture() -> None:
    tgo = _command_post(setting_on=True, captured=True)
    assert tgo.known_for(Player.BLUE) is True


def test_command_post_not_gated_when_setting_off() -> None:
    # With the feature off, command posts follow the normal recon fog, not the
    # capture gate (so an uncaptured commander does NOT hide them here).
    tgo = _command_post(setting_on=False, captured=False)
    tgo.discovered_by_player = True
    assert tgo.known_for(Player.BLUE) is True


def _processor(*, setting_on: bool) -> tuple[MissionResultsProcessor, Any]:
    game = MagicMock()
    game.settings.scar_command_post_intel = setting_on
    game.blue.captured_commander = False
    return MissionResultsProcessor(game), game


def test_capture_reveals_command_posts() -> None:
    processor, game = _processor(setting_on=True)
    debriefing = SimpleNamespace(
        state_data=SimpleNamespace(scar_results={"scar-1": "captured"})
    )
    processor.commit_scar_results(cast(Any, debriefing))
    assert game.blue.captured_commander is True


def test_non_capture_outcomes_do_not_reveal() -> None:
    processor, game = _processor(setting_on=True)
    debriefing = SimpleNamespace(
        state_data=SimpleNamespace(
            scar_results={"scar-1": "failed", "scar-2": "success"}
        )
    )
    processor.commit_scar_results(cast(Any, debriefing))
    assert game.blue.captured_commander is False


def test_capture_does_nothing_when_setting_off() -> None:
    processor, game = _processor(setting_on=False)
    debriefing = SimpleNamespace(
        state_data=SimpleNamespace(scar_results={"scar-1": "captured"})
    )
    processor.commit_scar_results(cast(Any, debriefing))
    assert game.blue.captured_commander is False
