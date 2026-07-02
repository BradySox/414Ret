"""SCAR campaign engine — command-post intel fog.

With the ``scar_command_post_intel`` setting on, an enemy command post is hidden
from the player ENTIRELY — off the map, not strikable — until it is revealed, then
it shows fully with exact coordinates (SME 2026-06-18). Two reveal keys: the
persisted ``captured_commander`` flag (an old save's commander capture keeps its
permanent all-posts reveal; the capture economy that SET the flag was removed
2026-07-01), OR the site was discovered the normal way (attacked / scouted /
TARPS).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from dcs.mapping import Point

from game.theater import Player
from game.theater.controlpoint import OffMapSpawn
from game.theater.presetlocation import PresetLocation
from game.theater.theatergroundobject import BuildingGroundObject
from game.utils import Heading


class _EnemyCommandPost(BuildingGroundObject):
    def is_friendly(self, to_player: Player) -> bool:
        return False


def _command_post(
    *, setting_on: bool, captured: bool, discovered: bool = False
) -> BuildingGroundObject:
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
    tgo.discovered_by_player = discovered
    # known_for()/hidden_on_player_map() reach control_point.coalition.game.settings
    # + .opponent.captured_commander.
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


def test_command_post_hidden_until_revealed() -> None:
    tgo = _command_post(setting_on=True, captured=False, discovered=False)
    # Composition unknown AND off the map entirely for the human (BLUE)...
    assert tgo.known_for(Player.BLUE) is False
    assert tgo.hidden_on_player_map(Player.BLUE) is True
    # ...but the AI/planner (omniscient, viewer=None) always sees it.
    assert tgo.known_for(None) is True
    assert tgo.hidden_on_player_map(None) is False


def test_command_post_revealed_after_capture() -> None:
    # SME #1/#2: capturing a commander reveals ALL command posts, permanently.
    tgo = _command_post(setting_on=True, captured=True)
    assert tgo.known_for(Player.BLUE) is True
    assert tgo.hidden_on_player_map(Player.BLUE) is False


def test_command_post_revealed_after_discovery() -> None:
    # SME #4: discovering the site the normal way (strike/scout/TARPS) reveals it
    # too — capture is not the only key.
    tgo = _command_post(setting_on=True, captured=False, discovered=True)
    assert tgo.known_for(Player.BLUE) is True
    assert tgo.hidden_on_player_map(Player.BLUE) is False


def test_command_post_not_gated_when_setting_off() -> None:
    # With the feature off, command posts follow the normal recon fog: never hidden
    # from the map (only composition is fogged), and an uncaptured/undiscovered
    # commander does not hide them.
    tgo = _command_post(setting_on=False, captured=False, discovered=False)
    assert tgo.hidden_on_player_map(Player.BLUE) is False
    tgo.discovered_by_player = True
    assert tgo.known_for(Player.BLUE) is True
