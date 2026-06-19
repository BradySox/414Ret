"""SCAR campaign engine — command-post intel fog (Phase 1).

With the ``scar_command_post_intel`` setting on, an enemy command post is hidden
from the player ENTIRELY — off the map, not strikable — until it is revealed, then
it shows fully with exact coordinates (SME 2026-06-18). Two reveal keys: the
side captured an enemy commander on a SCAR sortie (reveals ALL command posts,
permanently), OR the site was discovered the normal way (attacked / scouted /
TARPS). Gated OFF by default. These tests pin the wiring (the SOF capture mechanic
that produces a "captured" result is Phase 2).
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


def _processor(*, setting_on: bool) -> tuple[MissionResultsProcessor, Any]:
    game = MagicMock()
    game.settings.scar_command_post_intel = setting_on
    game.blue.captured_commander = False
    # The SOF-spend fallback iterates controlpoints; default to none.
    game.theater.controlpoints = []
    return MissionResultsProcessor(game), game


def _sof_insert_flight(origin: Any) -> Any:
    from game.ato.flighttype import FlightType

    return MagicMock(flight_type=FlightType.SOF, departure=origin)


def test_capture_reveals_command_posts() -> None:
    processor, game = _processor(setting_on=True)
    debriefing = SimpleNamespace(
        state_data=SimpleNamespace(scar_results={"scar-1": "captured"})
    )
    processor.commit_scar_results(cast(Any, debriefing))
    assert game.blue.captured_commander is True


def test_capture_does_not_consume_sof_teams() -> None:
    # Phase 2c-2: consumption is debit-on-frag, not on capture. A captured result
    # reveals the command posts but no longer spends inventory here.
    processor, game = _processor(setting_on=True)
    cp = MagicMock()
    game.theater.controlpoints = [cp]
    debriefing = SimpleNamespace(
        state_data=SimpleNamespace(scar_results={"scar-1": "captured"})
    )
    processor.commit_scar_results(cast(Any, debriefing))
    assert game.blue.captured_commander is True
    cp.base.commit_losses.assert_not_called()


def test_flown_sof_insert_debits_a_team_from_its_origin_base() -> None:
    # Phase 2c-2: each fragged SOF insert spends one bought team from its origin
    # base, regardless of the capture outcome.
    from game.dcs.groundunittype import GroundUnitType
    from game.missiongenerator.scarluadata import SCAR_SOF_UNIT_BLUE

    processor, game = _processor(setting_on=True)
    unit = GroundUnitType.named(SCAR_SOF_UNIT_BLUE)
    origin = MagicMock()
    origin.base.armor = {unit: 2}
    game.blue.ato.packages = [MagicMock(flights=[_sof_insert_flight(origin)])]
    game.red.ato.packages = []

    processor.commit_sof_deployments(cast(Any, SimpleNamespace()))

    origin.base.commit_losses.assert_called_once_with({unit: 1})


def test_sof_deployment_is_a_noop_when_setting_off() -> None:
    processor, game = _processor(setting_on=False)
    origin = MagicMock()
    game.blue.ato.packages = [MagicMock(flights=[_sof_insert_flight(origin)])]
    game.red.ato.packages = []

    processor.commit_sof_deployments(cast(Any, SimpleNamespace()))

    origin.base.commit_losses.assert_not_called()


def test_red_capture_does_not_reveal_blue_command_posts() -> None:
    processor, game = _processor(setting_on=True)
    debriefing = SimpleNamespace(
        state_data=SimpleNamespace(scar_results={"red-scar-1": "captured"})
    )

    processor.commit_scar_results(cast(Any, debriefing))

    assert game.blue.captured_commander is False


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
