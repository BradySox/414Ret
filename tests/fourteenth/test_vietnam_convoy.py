"""§35 convoy interdiction -> real, tracked enemy convoy (no phantom units).

Locks the force-planning nudge that replaced the old runtime phantom convoy: when
``vietnam_convoy_interdiction`` is on, the opfor gets a *real* convoy of its own rear units
moved toward the front (debited from the source base), so interdicting it is a real loss.
The guards (setting off / a convoy already flowing / no corridor / a thin source) must all
no-op rather than invent a free column.
"""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from typing import Any

from game.fourteenth.vietnam_convoy import (
    MAX_SOURCE_FRACTION,
    _pick_trail_corridor,
    _skim_units,
    ensure_enemy_trail_convoy,
)


class _Base:
    def __init__(self, armor: dict[Any, int]) -> None:
        self.armor = dict(armor)

    @property
    def total_armor(self) -> int:
        return sum(self.armor.values())

    def commit_losses(self, lost: dict[Any, int]) -> None:
        for unit_type, count in lost.items():
            self.armor[unit_type] -= count


class _CP:
    """Duck-typed ControlPoint. ``dist`` is the distance-to-front the fake fronts read."""

    def __init__(self, name: str, captured: str, dist: float, armor: dict[Any, int]):
        self.name = name
        self.captured = captured
        self.position = SimpleNamespace(dist=dist)
        self.base = _Base(armor)
        self.convoy_routes: dict[Any, Any] = {}


def _front() -> Any:
    # Distance-to-front is just the CP's own ``dist`` marker, so a lower-dist CP is nearer.
    return SimpleNamespace(
        position=SimpleNamespace(distance_to_point=lambda pos: pos.dist)
    )


class _Transfers:
    def __init__(self, convoys: list[Any] | None = None) -> None:
        self.convoys = convoys or []
        self.created: list[Any] = []

    def new_transfer(self, order: Any, now: Any) -> None:
        self.created.append(order)


def _game(
    *,
    on: bool,
    control_points: list[_CP],
    fronts: list[Any],
    convoys: list[Any] | None = None,
    turn: int = 3,
) -> Any:
    transfers = _Transfers(convoys)
    return SimpleNamespace(
        settings=SimpleNamespace(vietnam_convoy_interdiction=on),
        turn=turn,
        red=SimpleNamespace(player="RED", transfers=transfers),
        theater=SimpleNamespace(
            controlpoints=control_points, conflicts=lambda: list(fronts)
        ),
        conditions=SimpleNamespace(start_time=datetime(2000, 1, 1)),
    )


# ---- _skim_units -------------------------------------------------------------------


def test_skim_takes_up_to_cap_from_the_deepest_stock() -> None:
    base_cp = _CP("rear", "RED", 100.0, {"tank": 10, "apc": 4})
    units = _skim_units(base_cp, 4)  # type: ignore[arg-type]
    assert sum(units.values()) == 4
    # Skims the most numerous type first (depth, not a base's only unit of a kind).
    assert units.get("tank", 0) >= units.get("apc", 0)  # type: ignore[call-overload]


def test_skim_never_exceeds_the_source_fraction() -> None:
    base_cp = _CP("rear", "RED", 100.0, {"tank": 6})
    units = _skim_units(base_cp, 4)  # type: ignore[arg-type]
    # Half of 6 = 3, so the cap of 4 is clamped to 3 (never guts the base).
    assert sum(units.values()) == int(6 * MAX_SOURCE_FRACTION) == 3


def test_skim_returns_empty_for_a_thin_source() -> None:
    assert _skim_units(_CP("rear", "RED", 100.0, {"tank": 1}), 4) == {}  # type: ignore[arg-type]
    assert _skim_units(_CP("rear", "RED", 100.0, {}), 4) == {}  # type: ignore[arg-type]


# ---- _pick_trail_corridor ----------------------------------------------------------


def test_corridor_picks_the_road_nearest_the_front_with_a_stocked_source() -> None:
    rear = _CP("rear", "RED", 200.0, {"tank": 8})
    front_cp = _CP("front", "RED", 10.0, {"tank": 2})
    rear.convoy_routes = {front_cp: ()}
    front_cp.convoy_routes = {rear: ()}
    coalition = SimpleNamespace(player="RED")
    corridor = _pick_trail_corridor(
        SimpleNamespace(
            theater=SimpleNamespace(
                controlpoints=[rear, front_cp], conflicts=lambda: [_front()]
            )
        ),  # type: ignore[arg-type]
        coalition,  # type: ignore[arg-type]
    )
    assert corridor is not None
    source, destination = corridor
    # The stocked rear base feeds the front-adjacent base.
    assert source is rear
    assert destination is front_cp


def test_corridor_is_none_without_a_front() -> None:
    rear = _CP("rear", "RED", 200.0, {"tank": 8})
    assert (
        _pick_trail_corridor(
            SimpleNamespace(theater=SimpleNamespace(controlpoints=[rear], conflicts=lambda: [])),  # type: ignore[arg-type]
            SimpleNamespace(player="RED"),  # type: ignore[arg-type]
        )
        is None
    )


def test_corridor_ignores_opfor_to_friendly_roads() -> None:
    # An opfor -> friendly road is the contested front, not a supply corridor.
    red = _CP("red", "RED", 100.0, {"tank": 8})
    blue = _CP("blue", "BLUE", 5.0, {"tank": 2})
    red.convoy_routes = {blue: ()}
    corridor = _pick_trail_corridor(
        SimpleNamespace(
            theater=SimpleNamespace(
                controlpoints=[red, blue], conflicts=lambda: [_front()]
            )
        ),  # type: ignore[arg-type]
        SimpleNamespace(player="RED"),  # type: ignore[arg-type]
    )
    assert corridor is None


# ---- ensure_enemy_trail_convoy -----------------------------------------------------


def test_no_transfer_when_setting_off() -> None:
    rear = _CP("rear", "RED", 200.0, {"tank": 8})
    front_cp = _CP("front", "RED", 10.0, {"tank": 2})
    rear.convoy_routes = {front_cp: ()}
    game = _game(on=False, control_points=[rear, front_cp], fronts=[_front()])
    ensure_enemy_trail_convoy(game)
    assert game.red.transfers.created == []


def test_no_transfer_when_a_convoy_already_flows() -> None:
    rear = _CP("rear", "RED", 200.0, {"tank": 8})
    front_cp = _CP("front", "RED", 10.0, {"tank": 2})
    rear.convoy_routes = {front_cp: ()}
    game = _game(
        on=True,
        control_points=[rear, front_cp],
        fronts=[_front()],
        convoys=["already-rolling"],
    )
    ensure_enemy_trail_convoy(game)
    assert game.red.transfers.created == []


def test_creates_a_real_transfer_of_skimmed_rear_units() -> None:
    rear = _CP("rear", "RED", 200.0, {"tank": 8})
    front_cp = _CP("front", "RED", 10.0, {"tank": 2})
    rear.convoy_routes = {front_cp: ()}
    front_cp.convoy_routes = {rear: ()}
    game = _game(on=True, control_points=[rear, front_cp], fronts=[_front()])
    ensure_enemy_trail_convoy(game)
    assert len(game.red.transfers.created) == 1
    order = game.red.transfers.created[0]
    # A real TransferOrder from the rear source to the front-adjacent destination.
    assert order.origin is rear
    assert order.destination is front_cp
    assert sum(order.units.values()) == 4


def test_no_transfer_on_turn_zero() -> None:
    rear = _CP("rear", "RED", 200.0, {"tank": 8})
    front_cp = _CP("front", "RED", 10.0, {"tank": 2})
    rear.convoy_routes = {front_cp: ()}
    game = _game(on=True, control_points=[rear, front_cp], fronts=[_front()], turn=0)
    ensure_enemy_trail_convoy(game)
    assert game.red.transfers.created == []


# ---- the COIN front-less ratline (C3 follow-up) -------------------------------------


class _CoinUnit:
    """Whitelist-passing GroundUnitType fake for the ratline seed pool."""

    def __init__(self, name: str) -> None:
        from game.data.units import UnitClass

        self.display_name = name
        self.unit_class = UnitClass.IFV
        self.price = 2


def _positioned(cp: _CP, distance_to_others: dict[str, float]) -> _CP:
    """Give a fake CP a position whose distance_to_point reads the other's dist."""
    cp.position = SimpleNamespace(
        dist=cp.position.dist,
        distance_to_point=lambda pos: pos.dist,
    )
    return cp


def test_corridor_falls_back_to_opposing_cps_when_frontless() -> None:
    # No fronts (the COIN air-assault laydown): the corridor orients toward the
    # opposing CPs instead. "dist" doubles as distance-to-blue here.
    rear = _CP("rear", "RED", 100.0, {"truck": 8})
    forward = _CP("forward", "RED", 10.0, {"truck": 1})
    blue = _CP("kandahar", "BLUE", 0.0, {})
    for cp in (rear, forward, blue):
        _positioned(cp, {})
    rear.convoy_routes[forward] = object()
    forward.convoy_routes[rear] = object()
    game = SimpleNamespace(
        theater=SimpleNamespace(
            controlpoints=[rear, forward, blue], conflicts=lambda: []
        )
    )
    corridor = _pick_trail_corridor(game, SimpleNamespace(player="RED"))  # type: ignore[arg-type]
    assert corridor is not None
    source, destination = corridor
    assert source.name == "rear"
    assert destination.name == "forward"


def test_frontless_without_opposing_cps_is_still_none() -> None:
    rear = _CP("rear", "RED", 100.0, {"truck": 8})
    game = SimpleNamespace(
        theater=SimpleNamespace(controlpoints=[rear], conflicts=lambda: [])
    )
    assert (
        _pick_trail_corridor(game, SimpleNamespace(player="RED")) is None  # type: ignore[arg-type]
    )


def test_coin_seeds_an_empty_rear_source_and_ships_a_convoy() -> None:
    # The COIN reality: every stronghold's Base.armor is empty. With
    # coin_insurgency on, the ratline seeds the rear source with whitelisted kit
    # (external support) and ships a real convoy off it.
    rear = _CP("rear", "RED", 100.0, {})
    forward = _CP("forward", "RED", 10.0, {})
    blue = _CP("kandahar", "BLUE", 0.0, {})
    for cp in (rear, forward, blue):
        _positioned(cp, {})
    rear.convoy_routes[forward] = object()
    forward.convoy_routes[rear] = object()

    def commission(units: dict[Any, int]) -> None:
        for unit_type, count in units.items():
            rear.base.armor[unit_type] = rear.base.armor.get(unit_type, 0) + count

    rear.base.commission_units = commission  # type: ignore[attr-defined]
    game = _game(on=True, control_points=[rear, forward, blue], fronts=[])
    game.settings.coin_insurgency = True
    game.red.faction = SimpleNamespace(frontline_units={_CoinUnit("Toyota")})
    ensure_enemy_trail_convoy(game)
    created = game.red.transfers.created
    assert len(created) == 1
    order = created[0]
    assert sum(order.units.values()) == 4  # a full MAX_CONVOY_UNITS load
    # Seeded to exactly 2x the load: the real new_transfer debits the skimmed 4,
    # leaving a 4-unit rear buffer (the fake transfer ledger doesn't debit).
    assert rear.base.total_armor == 8


def test_no_coin_seeding_without_the_toggle() -> None:
    # Vietnam campaigns (or COIN with the insurgency off) never conjure stock:
    # an empty rear stays an empty rear and no convoy ships.
    rear = _CP("rear", "RED", 100.0, {})
    forward = _CP("forward", "RED", 10.0, {})
    blue = _CP("kandahar", "BLUE", 0.0, {})
    for cp in (rear, forward, blue):
        _positioned(cp, {})
    rear.convoy_routes[forward] = object()
    game = _game(on=True, control_points=[rear, forward, blue], fronts=[])
    ensure_enemy_trail_convoy(game)
    assert game.red.transfers.created == []
    assert rear.base.total_armor == 0
