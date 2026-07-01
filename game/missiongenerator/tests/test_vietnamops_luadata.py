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
    control_points: list[Any] | None = None,
    fronts: list[Any] | None = None,
    harassment: bool = False,
    coalitions: list[Any] | None = None,
    super_gaggle: bool = False,
    fac: bool = False,
    snake_nape: bool = False,
    super_gaggle_commitment: Any | None = None,
) -> str:
    root = LuaData("dcsRetribution")
    game = SimpleNamespace(
        settings=SimpleNamespace(
            vietnam_arc_light=arc_light,
            vietnam_flak_gauntlet=flak,
            vietnam_naval_gunfire=ngfs,
            vietnam_airbase_harassment=harassment,
            vietnam_super_gaggle=super_gaggle,
            vietnam_fac_marking=fac,
            vietnam_snake_and_nape=snake_nape,
        ),
        theater=SimpleNamespace(
            ground_objects=ground_objects or [],
            controlpoints=control_points or [],
            conflicts=lambda: list(fronts or []),
        ),
        coalitions=coalitions or [],
        # §37: the emitter reads the planned gaggle off the game, not geography.
        super_gaggle_commitment=super_gaggle_commitment,
    )
    mission_data = SimpleNamespace(flights=flights)
    populate_vietnam_ops_lua(root, game, mission_data)  # type: ignore[arg-type]
    return root.create_operations_lua()


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


def test_fac_marker_emitted_when_on() -> None:
    lua = _emit([], fac=True)
    assert "VietnamOps" in lua
    assert "fac" in lua
    assert "enabled" in lua


def test_fac_off_no_node() -> None:
    lua = _emit([], fac=False)
    assert "VietnamOps" not in lua


def test_fac_is_independent_of_flak() -> None:
    # FAC on, flak off: a fac node, no flak node (the on-markers don't leak into each other).
    lua = _emit([], fac=True)
    assert "fac" in lua
    assert "flak" not in lua


def test_snake_nape_marker_emitted_when_on() -> None:
    lua = _emit([], snake_nape=True)
    assert "VietnamOps" in lua
    assert "snakeNape" in lua
    assert "enabled" in lua


def test_snake_nape_off_no_node() -> None:
    lua = _emit([], snake_nape=False)
    assert "VietnamOps" not in lua


def test_snake_nape_is_independent_of_fac() -> None:
    # Snake-and-nape on, FAC off: a snakeNape node, no fac node (on-markers don't leak).
    lua = _emit([], snake_nape=True)
    assert "snakeNape" in lua
    assert "fac" not in lua


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


# Convoy interdiction (§35) no longer emits a Lua node -- it creates a real, tracked enemy
# convoy in the force model instead of a phantom runtime column. Its coverage now lives in
# tests/fourteenth/test_vietnam_convoy.py; the emitter must never emit a "convoy" node.
def test_convoy_never_emits_a_lua_node() -> None:
    # Even with the toggle on (via another suite feature present), no convoy sub-node exists.
    lua = _emit([], flak=True)
    assert "convoy" not in lua


class _GeoPoint:
    """A point that can measure distance to another point (for the launch-field pick)."""

    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def distance_to_point(self, other: "_GeoPoint") -> float:
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5


class _Field:
    """A hashable duck-typed airfield/FARP/FOB ControlPoint for the harassment + Super
    Gaggle emitters.

    The harassment emitter reads ``cptype``/``captured``/``position``/``full_name`` and puts
    the CP in an *exclude* set, so (like ``_CP``) it must be hashable -- SimpleNamespace is
    not. The Super Gaggle emitter additionally measures ``position.distance_to_point`` when
    picking the launch field, so the position is a ``_GeoPoint``.
    """

    def __init__(
        self,
        name: str,
        cptype: ControlPointType,
        captured: Any,
        x: float,
        y: float = 0.0,
    ) -> None:
        self.full_name = name
        self.cptype = cptype
        self.captured = captured
        self.position = _GeoPoint(x, y)


def _field(
    name: str, cptype: ControlPointType, captured: Any, x: float, y: float = 0.0
) -> _Field:
    return _Field(name, cptype, captured, x, y)


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


# The Super Gaggle geography + squadron selection now live in game/fourteenth/super_gaggle.py
# (plan_super_gaggle), tested in tests/fourteenth/test_super_gaggle.py. The emitter just
# serializes the planned commitment off the game -- so it emits a node iff one was planned.
def _commitment() -> Any:
    return SimpleNamespace(
        outpost_name="Hill 861",
        outpost_x=1000.0,
        outpost_y=2000.0,
        launch_x=3000.0,
        launch_y=4000.0,
        helo_type="UH-1H",
        helo_unit_names=["SuperGaggle-T3-Helo-1", "SuperGaggle-T3-Helo-2"],
        supp_type="A-4E-C",
        supp_unit_names=["SuperGaggle-T3-Sandy-1"],
    )


def test_super_gaggle_no_node_without_a_commitment() -> None:
    # No planned gaggle (feature off / no plannable run) -> no node, even with the toggle on.
    lua = _emit([], super_gaggle=True, super_gaggle_commitment=None)
    assert "superGaggle" not in lua


def test_super_gaggle_emits_the_committed_run() -> None:
    lua = _emit([], super_gaggle=True, super_gaggle_commitment=_commitment())
    assert "VietnamOps" in lua
    assert "superGaggle" in lua
    assert "Hill 861" in lua  # the besieged outpost
    assert "BLUE" in lua  # the friendly resupply coalition
    # The exact per-airframe unit names are emitted so a killed name maps back to a squadron.
    assert "SuperGaggle-T3-Helo-1" in lua
    assert "SuperGaggle-T3-Helo-2" in lua
    assert "UH-1H" in lua  # the real helo squadron's aircraft type
    assert "SuperGaggle-T3-Sandy-1" in lua  # the committed suppressor airframe
    assert "A-4E-C" in lua


def test_super_gaggle_emits_helos_without_a_suppressor() -> None:
    commit = _commitment()
    commit.supp_type = None
    commit.supp_unit_names = []
    lua = _emit([], super_gaggle=True, super_gaggle_commitment=commit)
    assert "superGaggle" in lua
    assert "SuperGaggle-T3-Helo-1" in lua
    assert "suppressor" not in lua  # no suppressor sub-node when none was committed
