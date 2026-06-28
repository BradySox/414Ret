from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.ato import FlightType
from game.data.units import UnitClass
from game.missiongenerator.luagenerator import LuaData
from game.missiongenerator.vietnamopsluadata import (
    HEAVY_BOMBER_DCS_IDS,
    populate_vietnam_ops_lua,
)


def _flight(dcs_id: str, flight_type: FlightType, group_name: str) -> Any:
    """A duck-typed FlightData with just the fields the Arc Light emitter reads."""
    return SimpleNamespace(
        flight_type=flight_type,
        aircraft_type=SimpleNamespace(dcs_unit_type=SimpleNamespace(id=dcs_id)),
        group_name=group_name,
        package=SimpleNamespace(
            target=SimpleNamespace(position=SimpleNamespace(x=1000.0, y=2000.0))
        ),
    )


def _ship_go(group_name: str, unit_class: UnitClass, color: str) -> Any:
    """A duck-typed naval TheaterGroundObject for the NGFS emitter."""
    unit = SimpleNamespace(unit_type=SimpleNamespace(unit_class=unit_class))
    group = SimpleNamespace(group_name=group_name, units=[unit])
    return SimpleNamespace(groups=[group], faction_color=color)


def _emit(
    flights: list[Any],
    arc_light: bool = False,
    flak: bool = False,
    ngfs: bool = False,
    ground_objects: list[Any] | None = None,
) -> str:
    root = LuaData("dcsRetribution")
    game = SimpleNamespace(
        settings=SimpleNamespace(
            vietnam_arc_light=arc_light,
            vietnam_flak_gauntlet=flak,
            vietnam_naval_gunfire=ngfs,
        ),
        theater=SimpleNamespace(ground_objects=ground_objects or []),
    )
    mission_data = SimpleNamespace(flights=flights)
    populate_vietnam_ops_lua(root, game, mission_data)  # type: ignore[arg-type]
    return root.create_operations_lua()


def test_arc_light_matches_only_heavy_bomber_strike() -> None:
    flights = [
        _flight("B-52H", FlightType.STRIKE, "Arc Light B-52"),
        _flight("F-4E", FlightType.STRIKE, "Tac Strike Phantom"),
        _flight("B-52H", FlightType.BARCAP, "Bomber Not Striking"),
    ]
    lua = _emit(flights, arc_light=True)
    assert "VietnamOps" in lua
    assert "arcLight" in lua
    assert "Arc Light B-52" in lua
    # A tactical striker and a non-Strike bomber are never carpeted.
    assert "Tac Strike Phantom" not in lua
    assert "Bomber Not Striking" not in lua


def test_no_node_when_all_features_off() -> None:
    flights = [_flight("B-52H", FlightType.STRIKE, "Arc Light B-52")]
    lua = _emit(flights, arc_light=False, flak=False)
    assert "VietnamOps" not in lua


def test_flak_marker_emitted_when_on() -> None:
    lua = _emit([], arc_light=False, flak=True)
    assert "VietnamOps" in lua
    assert "flak" in lua
    assert "enabled" in lua


def test_flak_and_arc_light_are_independent() -> None:
    # Flak on, Arc Light off: a flak node, no arcLight node.
    lua = _emit([], arc_light=False, flak=True)
    assert "flak" in lua
    assert "arcLight" not in lua


def test_no_arclight_record_without_eligible_bombers() -> None:
    flights = [_flight("F-4E", FlightType.STRIKE, "Tac Strike Phantom")]
    lua = _emit(flights, arc_light=True)
    assert "arcLight" not in lua


def test_b52h_is_a_recognised_heavy_bomber() -> None:
    assert "B-52H" in HEAVY_BOMBER_DCS_IDS


def test_naval_gunfire_emits_gun_ships_with_coalition() -> None:
    gos = [
        _ship_go("New Jersey", UnitClass.DESTROYER, "BLUE"),
        _ship_go("Oklahoma City", UnitClass.CRUISER, "BLUE"),
        # A carrier is not a gun ship and must not be emitted.
        _ship_go("CV Carrier", UnitClass.AIRCRAFT_CARRIER, "BLUE"),
    ]
    lua = _emit([], ngfs=True, ground_objects=gos)
    assert "navalGunfire" in lua
    assert "New Jersey" in lua
    assert "Oklahoma City" in lua
    assert "CV Carrier" not in lua
    assert "BLUE" in lua


def test_naval_gunfire_off_no_node() -> None:
    gos = [_ship_go("New Jersey", UnitClass.DESTROYER, "BLUE")]
    lua = _emit([], ngfs=False, ground_objects=gos)
    assert "navalGunfire" not in lua


def test_naval_gunfire_no_node_without_gun_ships() -> None:
    gos = [_ship_go("CV Carrier", UnitClass.AIRCRAFT_CARRIER, "BLUE")]
    lua = _emit([], ngfs=True, ground_objects=gos)
    assert "navalGunfire" not in lua
