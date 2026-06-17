"""Tests for the SCAR scenario/results bridge (Python side).

The bridge is the spec-§8a integration seam: Retribution composes a ScarTasking,
the generator emits it as a dcsRetribution.Scar Lua table, the SCAR plugin runs
a pass/fail loop in-mission, and the outcome flows back through state.json into
the debrief. The Lua half needs an in-game pass; here we lock in the Python half
that CI can verify: tasking collection, Lua emission, and result parsing.
"""

from typing import Any
from unittest.mock import MagicMock

from dcs.mapping import Point

from game.ato.flighttype import FlightType
from game.debriefing import StateData
from game.missiongenerator.luagenerator import LuaData
from game.missiongenerator.scarluadata import (
    SCAR_HVT_DEST_OFFSET_M,
    SCAR_HVT_SPAWN_OFFSET_M,
    build_scar_taskings,
    populate_scar_lua,
)


def _coalition_with_flights(*flight_types: FlightType, player: bool = True) -> Any:
    package = MagicMock()
    package.target.position = Point(1000, 2000, None)  # type: ignore[arg-type]
    package.flights = [MagicMock(flight_type=ft) for ft in flight_types]
    coalition = MagicMock()
    coalition.player = player
    coalition.opponent.faction.country.id = 7
    coalition.ato.packages = [package]
    return coalition


def test_build_scar_taskings_one_per_scar_flight() -> None:
    game = MagicMock()
    game.coalitions = [
        _coalition_with_flights(FlightType.SCAR, FlightType.CAS, player=True)
    ]

    taskings = build_scar_taskings(game)

    assert len(taskings) == 1  # the CAS flight is ignored
    tasking = taskings[0]
    assert tasking.coalition == "blue"
    assert tasking.hvt_country_id == 7  # the enemy (opponent) country
    assert tasking.area_x == 1000
    assert tasking.area_y == 2000
    assert tasking.hvt_spawn_x == 1000 + SCAR_HVT_SPAWN_OFFSET_M
    assert tasking.hvt_dest_x == 1000 - SCAR_HVT_DEST_OFFSET_M


def test_build_scar_taskings_empty_without_scar_flights() -> None:
    game = MagicMock()
    game.coalitions = [_coalition_with_flights(FlightType.CAS, FlightType.BARCAP)]
    assert build_scar_taskings(game) == []


def test_populate_scar_lua_emits_tasking_table() -> None:
    game = MagicMock()
    game.coalitions = [_coalition_with_flights(FlightType.SCAR)]
    taskings = build_scar_taskings(game)

    root = LuaData("dcsRetribution")
    populate_scar_lua(root, taskings)
    serialized = root.serialize()

    assert "Scar" in serialized
    assert "taskings" in serialized
    assert "taskingId" in serialized
    assert "scar-1" in serialized
    assert "hvtCountryId" in serialized


def test_state_data_parses_scar_results() -> None:
    unit_map = MagicMock()
    data = {
        "scar_results": {
            "scar-1": {"status": "success"},
            "scar-2": {"status": "failed"},
            "scar-3": "active",  # tolerate a bare status string
        }
    }
    state = StateData.from_json(data, unit_map)
    assert state.scar_results == {
        "scar-1": "success",
        "scar-2": "failed",
        "scar-3": "active",
    }


def test_state_data_scar_results_default_empty() -> None:
    unit_map = MagicMock()
    # Lua serializes an empty table as [], which must parse to {} not crash.
    state = StateData.from_json({"scar_results": []}, unit_map)
    assert state.scar_results == {}
    state = StateData.from_json({}, unit_map)
    assert state.scar_results == {}
