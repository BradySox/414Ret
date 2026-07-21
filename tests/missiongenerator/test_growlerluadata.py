"""Growler escort-jamming emitter (dcsRetribution.growler).

Locks the shape the ``growler`` plugin consumes: one record per ESCORT_JAMMER
flight with its group name, side, player flag, graduated tier + derived effect
knobs, and the package member group names it protects. No ESCORT_JAMMER flight
-> no node (the plugin no-ops).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Optional

from game.ato import FlightType
from game.data.escort_jamming import EscortJammerTier
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
    tier: Optional[EscortJammerTier] = None,
) -> Any:
    return SimpleNamespace(
        flight_type=flight_type,
        group_name=group_name,
        package=package,
        friendly=friendly,
        client_units=["human"] if clients else [],
        aircraft_type=SimpleNamespace(escort_jammer_tier=tier),
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
    jammer = _flight(
        FlightType.ESCORT_JAMMER, "Shadow 1", package, tier=EscortJammerTier.FULL
    )
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
    # Full tier -> offensive on, full defensive power.
    assert 'tier = "full"' in output
    assert 'offensive = "1"' in output


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


def test_tier_drives_emitted_effect_knobs() -> None:
    package = object()
    # An ECM-tier jammer: defensive-only (offensive off), reduced power.
    mission_data = SimpleNamespace(
        flights=[
            _flight(
                FlightType.ESCORT_JAMMER,
                "Zapper 1",
                package,
                tier=EscortJammerTier.ECM,
            ),
        ]
    )
    root = LuaData("dcsRetribution")
    populate_growler_lua(root, None, mission_data)  # type: ignore[arg-type]
    output = root.serialize()
    assert 'tier = "ecm"' in output
    # ECM never suppresses SAMs.
    assert 'offensive = "0"' in output


def test_untagged_jammer_defaults_to_self_protect() -> None:
    package = object()
    # A stray ESCORT_JAMMER flight on an untagged airframe still gets a defensive
    # bubble (SELF_PROTECT) but never offensive suppression.
    mission_data = SimpleNamespace(
        flights=[_flight(FlightType.ESCORT_JAMMER, "Ghost 1", package, tier=None)]
    )
    root = LuaData("dcsRetribution")
    populate_growler_lua(root, None, mission_data)  # type: ignore[arg-type]
    output = root.serialize()
    assert 'tier = "self_protect"' in output
    assert 'offensive = "0"' in output
