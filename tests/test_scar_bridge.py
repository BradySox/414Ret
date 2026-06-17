"""Tests for the SCAR scenario/results bridge (Python side).

The bridge is the spec-§8a integration seam: Retribution binds a ScarTasking to
units it already generates (an enemy convoy, or a surface-to-surface missile
site), the generator emits it as a dcsRetribution.Scar Lua table, the SCAR plugin
watches those groups in-mission, and the outcome flows back through state.json
into the debrief. The Lua half needs an in-game pass; here we lock in the Python
half that CI can verify: tasking collection, Lua emission, and result parsing.
"""

from typing import Any
from unittest.mock import MagicMock

from game.ato.flighttype import FlightType
from game.debriefing import StateData
from game.missiongenerator.luagenerator import LuaData
from game.missiongenerator.scarluadata import (
    build_scar_taskings,
    populate_scar_lua,
)
from game.theater.theatergroundobject import MissileSiteGroundObject, SamGroundObject
from game.transfers import Convoy


def _coalition_with_target(
    target: Any, *, extra_types: tuple[FlightType, ...] = ()
) -> Any:
    """A coalition whose single package has a SCAR flight (plus any extra flight
    types) against ``target``."""
    package = MagicMock()
    package.target = target
    package.flights = [MagicMock(flight_type=FlightType.SCAR)] + [
        MagicMock(flight_type=ft) for ft in extra_types
    ]
    coalition = MagicMock()
    coalition.ato.packages = [package]
    return coalition


def _game_with(*coalitions: Any) -> Any:
    game = MagicMock()
    game.coalitions = list(coalitions)
    return game


def test_convoy_target_yields_convoy_tasking() -> None:
    convoy = MagicMock(spec=Convoy)
    convoy.name = "Convoy 001"
    game = _game_with(_coalition_with_target(convoy, extra_types=(FlightType.CAS,)))

    taskings = build_scar_taskings(game)

    assert len(taskings) == 1  # the CAS flight is ignored
    assert taskings[0].variant == "convoy"
    assert taskings[0].target_groups == ("Convoy 001",)


def test_missile_site_target_yields_missile_tasking() -> None:
    site = MagicMock(spec=MissileSiteGroundObject)
    site.groups = [MagicMock(group_name="SCUD-1"), MagicMock(group_name="SCUD-2")]
    game = _game_with(_coalition_with_target(site))

    taskings = build_scar_taskings(game)

    assert len(taskings) == 1
    assert taskings[0].variant == "missile"
    assert taskings[0].target_groups == ("SCUD-1", "SCUD-2")


def test_other_target_yields_no_tasking() -> None:
    # A SCAR flight against e.g. a SAM site emits no scenario tasking (the flight
    # still flies, just without the convoy/missile scenario).
    sam = MagicMock(spec=SamGroundObject)
    game = _game_with(_coalition_with_target(sam))
    assert build_scar_taskings(game) == []


def test_populate_scar_lua_emits_tasking_table() -> None:
    convoy = MagicMock(spec=Convoy)
    convoy.name = "Convoy 001"
    taskings = build_scar_taskings(_game_with(_coalition_with_target(convoy)))

    root = LuaData("dcsRetribution")
    populate_scar_lua(root, taskings)
    serialized = root.serialize()

    assert "Scar" in serialized
    assert "taskings" in serialized
    assert "taskingId" in serialized
    assert "scar-1" in serialized
    assert "convoy" in serialized
    assert "targetGroups" in serialized
    assert "Convoy 001" in serialized


def test_state_data_parses_scar_results() -> None:
    unit_map = MagicMock()
    data = {
        "scar_results": {
            "scar-1": {"status": "success"},
            "scar-2": {"status": "launched"},
            "scar-3": "active",  # tolerate a bare status string
        }
    }
    state = StateData.from_json(data, unit_map)
    assert state.scar_results == {
        "scar-1": "success",
        "scar-2": "launched",
        "scar-3": "active",
    }


def test_state_data_scar_results_default_empty() -> None:
    unit_map = MagicMock()
    # Lua serializes an empty table as [], which must parse to {} not crash.
    state = StateData.from_json({"scar_results": []}, unit_map)
    assert state.scar_results == {}
    state = StateData.from_json({}, unit_map)
    assert state.scar_results == {}
