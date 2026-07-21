"""Growler escort-jamming emitter (dcsRetribution.growler).

Locks the shape the ``growler`` plugin consumes: one record per ESCORT_JAMMER
flight with its group name, side, player flag, and the package member group
names it protects. No ESCORT_JAMMER flight -> no node (the plugin no-ops).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.ato import FlightType
from game.missiongenerator.growlerluadata import populate_growler_lua
from game.missiongenerator.luagenerator import LuaData
from game.theater import Player


def _flight(
    flight_type: FlightType,
    group_name: str,
    package: Any,
    *,
    friendly: Player = Player.BLUE,
    clients: bool = False,
) -> Any:
    return SimpleNamespace(
        flight_type=flight_type,
        group_name=group_name,
        package=package,
        friendly=friendly,
        client_units=["human"] if clients else [],
    )


def test_no_escort_jammer_emits_no_node() -> None:
    package = object()
    mission_data = SimpleNamespace(
        flights=[_flight(FlightType.STRIKE, "Strike 1", package)]
    )
    root = LuaData("dcsRetribution")
    populate_growler_lua(root, None, mission_data)  # type: ignore[arg-type]
    assert "growler" not in root.serialize()


def test_jammer_emits_group_side_and_protected_package() -> None:
    package = object()
    other_package = object()
    jammer = _flight(FlightType.ESCORT_JAMMER, "Shadow 1", package)
    mission_data = SimpleNamespace(
        flights=[
            _flight(FlightType.STRIKE, "Hammer 1", package),
            jammer,
            _flight(FlightType.ESCORT, "Guard 1", package),
            # A different package's flight is never in the protected set.
            _flight(FlightType.STRIKE, "Anvil 1", other_package),
        ]
    )
    root = LuaData("dcsRetribution")
    populate_growler_lua(root, None, mission_data)  # type: ignore[arg-type]
    output = root.serialize()
    assert "Shadow 1" in output
    assert "Hammer 1" in output
    assert "Guard 1" in output
    assert "Anvil 1" not in output
    # AI-flown blue jammer: side 2, not a player.
    assert 'side = "2"' in output
    assert 'isPlayer = "0"' in output


def test_player_crewed_jammer_is_flagged() -> None:
    package = object()
    mission_data = SimpleNamespace(
        flights=[
            _flight(FlightType.ESCORT_JAMMER, "Shadow 1", package, clients=True),
        ]
    )
    root = LuaData("dcsRetribution")
    populate_growler_lua(root, None, mission_data)  # type: ignore[arg-type]
    assert 'isPlayer = "1"' in root.serialize()
