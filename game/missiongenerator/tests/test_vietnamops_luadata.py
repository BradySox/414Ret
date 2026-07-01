from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.ato import FlightType
from game.data.units import UnitClass
from game.missiongenerator.luagenerator import LuaData
from game.missiongenerator.vietnamopsluadata import (
    HARASSMENT_FRONT_REACH_M,
    HEAVY_BOMBER_DCS_IDS,
    populate_vietnam_ops_lua,
)
from game.theater import ControlPointType, Player


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
    convoy: bool = False,
    control_points: list[Any] | None = None,
    fronts: list[Any] | None = None,
    harassment: bool = False,
    coalitions: list[Any] | None = None,
) -> str:
    root = LuaData("dcsRetribution")
    game = SimpleNamespace(
        settings=SimpleNamespace(
            vietnam_arc_light=arc_light,
            vietnam_flak_gauntlet=flak,
            vietnam_naval_gunfire=ngfs,
            vietnam_convoy_interdiction=convoy,
            vietnam_airbase_harassment=harassment,
        ),
        theater=SimpleNamespace(
            ground_objects=ground_objects or [],
            controlpoints=control_points or [],
            conflicts=lambda: list(fronts or []),
        ),
        coalitions=coalitions or [],
    )
    mission_data = SimpleNamespace(flights=flights)
    populate_vietnam_ops_lua(root, game, mission_data)  # type: ignore[arg-type]
    return root.create_operations_lua()


def _pt(x: float, y: float) -> Any:
    return SimpleNamespace(x=x, y=y)


class _CP:
    """A hashable duck-typed ControlPoint -- the convoy emitter keys ``convoy_routes``
    by the connected CP, so the fake must be usable as a dict key (SimpleNamespace is
    not hashable)."""

    def __init__(self, name: str, captured: Any, convoy_routes: dict[Any, Any]) -> None:
        self.id = name
        self.captured = captured
        self.convoy_routes = convoy_routes


def _cp(name: str, captured: Any, convoy_routes: dict[Any, Any]) -> _CP:
    return _CP(name, captured, convoy_routes)


def _front() -> Any:
    # Distance-to-front is faked as the point's |x|, so a smaller-x corridor is "nearer".
    return SimpleNamespace(
        position=SimpleNamespace(distance_to_point=lambda pt: abs(pt.x))
    )


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


def test_convoy_picks_the_enemy_corridor_nearest_the_front() -> None:
    # Two RED->RED supply roads; the corridor whose midpoint is nearer the front (smaller
    # |x|) is the one emitted. A RED->BLUE road is the contested front, never a corridor.
    r1 = _cp("R1", Player.RED, {})
    r2 = _cp("R2", Player.RED, {})
    r3 = _cp("R3", Player.RED, {})
    b1 = _cp("B1", Player.BLUE, {})
    r1.convoy_routes = {
        r2: (_pt(11, 10), _pt(100, 10), _pt(190, 10)),  # midpoint x=100 (near)
        b1: (_pt(1, 1), _pt(2, 2)),  # RED->BLUE: the front, must be ignored
    }
    r2.convoy_routes = {r3: (_pt(511, 20), _pt(555, 20), _pt(599, 20))}  # x=555 (far)
    lua = _emit([], convoy=True, control_points=[r1, r2, r3, b1], fronts=[_front()])
    assert "VietnamOps" in lua
    assert "convoy" in lua
    assert "RED" in lua  # the enemy column's coalition
    assert "190" in lua  # a waypoint unique to the near corridor
    assert "599" not in lua  # the far corridor is not chosen


def test_convoy_off_no_node() -> None:
    r1 = _cp("R1", Player.RED, {})
    r2 = _cp("R2", Player.RED, {})
    r1.convoy_routes = {r2: (_pt(1, 1), _pt(2, 2))}
    lua = _emit([], convoy=False, control_points=[r1, r2], fronts=[_front()])
    assert "convoy" not in lua


def test_convoy_no_node_without_an_enemy_supply_road() -> None:
    # Only a RED->BLUE (front) road exists -> no enemy supply corridor -> no node.
    r1 = _cp("R1", Player.RED, {})
    b1 = _cp("B1", Player.BLUE, {})
    r1.convoy_routes = {b1: (_pt(1, 1), _pt(2, 2))}
    lua = _emit([], convoy=True, control_points=[r1, b1], fronts=[_front()])
    # The VietnamOps node may exist (the toggle is on) but carries no convoy sub-node.
    assert "convoy" not in lua


class _Field:
    """A hashable duck-typed airfield/FARP ControlPoint for the harassment emitter.

    The emitter reads ``cptype``/``captured``/``position``/``full_name`` and puts the CP in
    an *exclude* set, so (like ``_CP``) it must be hashable -- SimpleNamespace is not.
    """

    def __init__(
        self, name: str, cptype: ControlPointType, captured: Any, x: float
    ) -> None:
        self.full_name = name
        self.cptype = cptype
        self.captured = captured
        self.position = SimpleNamespace(x=x, y=0.0)


def _field(name: str, cptype: ControlPointType, captured: Any, x: float) -> _Field:
    return _Field(name, cptype, captured, x)


def _coalition_with_client_at(departure: Any) -> Any:
    """A coalition whose ATO has one client flight departing (and recovering at) ``departure``."""
    flight = SimpleNamespace(
        client_count=1, departure=departure, arrival=departure, divert=None
    )
    package = SimpleNamespace(flights=[flight])
    return SimpleNamespace(ato=SimpleNamespace(packages=[package]))


def test_airbase_harassment_off_no_node() -> None:
    near = _field("Da Nang", ControlPointType.AIRBASE, Player.RED, 10_000)
    lua = _emit([], harassment=False, control_points=[near], fronts=[_front()])
    assert "airbaseHarassment" not in lua


def test_airbase_harassment_emits_forward_occupied_field() -> None:
    near = _field("Da Nang", ControlPointType.AIRBASE, Player.RED, 10_000)
    lua = _emit([], harassment=True, control_points=[near], fronts=[_front()])
    assert "VietnamOps" in lua
    assert "airbaseHarassment" in lua
    assert "Da Nang" in lua


def test_airbase_harassment_no_node_without_a_front() -> None:
    # Forward-only by construction (design rule 4): no front -> nothing eligible -> no node.
    near = _field("Da Nang", ControlPointType.AIRBASE, Player.RED, 10_000)
    lua = _emit([], harassment=True, control_points=[near], fronts=[])
    assert "airbaseHarassment" not in lua


def test_airbase_harassment_skips_rear_neutral_and_non_airfield() -> None:
    rear = _field(
        "Rear Base",
        ControlPointType.AIRBASE,
        Player.RED,
        HARASSMENT_FRONT_REACH_M + 5e4,
    )
    neutral = _field("Neutral Field", ControlPointType.AIRBASE, Player.NEUTRAL, 10_000)
    carrier = _field(
        "Carrier Grp", ControlPointType.AIRCRAFT_CARRIER_GROUP, Player.RED, 10_000
    )
    near = _field("Da Nang", ControlPointType.FARP, Player.RED, 10_000)
    lua = _emit(
        [],
        harassment=True,
        control_points=[rear, neutral, carrier, near],
        fronts=[_front()],
    )
    assert "Da Nang" in lua
    assert "Rear Base" not in lua  # too deep in the rear
    assert "Neutral Field" not in lua  # unoccupied
    assert "Carrier Grp" not in lua  # a ship, not a land ramp


def test_airbase_harassment_never_targets_a_lone_client_spawn_field() -> None:
    # The player's spawn field is the only field; excluding it leaves nothing eligible, so
    # no harassment node is emitted at all -- the hard anti-grief guarantee (design rule 1).
    spawn = _field("Player FARP", ControlPointType.FARP, Player.BLUE, 8_000)
    lua = _emit(
        [],
        harassment=True,
        control_points=[spawn],
        fronts=[_front()],
        coalitions=[_coalition_with_client_at(spawn)],
    )
    assert "airbaseHarassment" not in lua


def test_airbase_harassment_client_spawn_field_is_excluded_not_targeted() -> None:
    spawn = _field("Player FARP", ControlPointType.FARP, Player.BLUE, 5_000)
    enemy = _field("Da Nang", ControlPointType.AIRBASE, Player.RED, 10_000)
    lua = _emit(
        [],
        harassment=True,
        control_points=[spawn, enemy],
        fronts=[_front()],
        coalitions=[_coalition_with_client_at(spawn)],
    )
    assert "Da Nang" in lua  # the enemy field is a target
    assert "excludedFields" in lua
    # The spawn field appears exactly once (in excludedFields) -- never as a target record,
    # which would make it appear a second time as a `name = "Player FARP"` field entry.
    assert lua.count("Player FARP") == 1
