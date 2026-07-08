"""War economy (§53) P0 -- the supply ledger, observe-only.

Locks the pure accessors (demand, capacity, production, per-CP supply factor, the
coalition aggregate §55 consumes) and the P0 advance behaviour: off is a no-op, on
seeds stockpiles to capacity once, accrues production capped at capacity, and reports
per side. No combat bite is exercised here -- that lands with P2.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.fourteenth.war_economy import (
    _BITE_FLOOR,
    _FUEL_READINESS_FLOOR,
    MIN_DEMAND,
    MUNITIONS_CAPACITY,
    STOCKPILE_TURNS,
    SUPPLY_PER_FRONTLINE_UNIT,
    _flight_scarce_loads,
    advance_munitions,
    advance_war_economy,
    coalition_supply_health,
    frontline_demand,
    fuel_readiness,
    munitions_stock,
    production_rate,
    stockpile_capacity,
    supply_effectiveness,
    supply_factor,
)
from game.theater import Player
from game.theater.base import Base


def _tgo(category: str, *alive: bool) -> Any:
    return SimpleNamespace(
        category=category, statics=[SimpleNamespace(alive=a) for a in alive]
    )


def _cp(
    owner: Player,
    *,
    front: bool = False,
    units: int = 0,
    tgos: list[Any] | None = None,
    supply: float = 0.0,
    connected: list[Any] | None = None,
) -> Any:
    cp = SimpleNamespace(
        captured=owner,
        has_active_frontline=front,
        deployable_front_line_units=units,
        ground_objects=list(tgos or []),
        base=SimpleNamespace(supply=supply, total_frontline_units=units),
    )
    links = list(connected or [])
    cp.transitive_connected_friendly_destinations = lambda: links
    return cp


def _game(cps: list[Any], *, on: bool = True, seeded: bool = False) -> Any:
    messages: list[tuple[str, str]] = []
    return SimpleNamespace(
        theater=SimpleNamespace(
            controlpoints=cps,
            control_points_for=lambda player: [c for c in cps if c.captured == player],
        ),
        settings=SimpleNamespace(war_economy=on),
        blue=SimpleNamespace(player=Player.BLUE),
        red=SimpleNamespace(player=Player.RED),
        war_economy_seeded=seeded,
        messages=messages,
        message=lambda title, body: messages.append((title, body)),
    )


def test_frontline_demand_zero_without_a_front() -> None:
    assert frontline_demand(_cp(Player.RED, front=False, units=9)) == 0.0


def test_frontline_demand_scales_with_deployable_units() -> None:
    assert (
        frontline_demand(_cp(Player.RED, front=True, units=5))
        == SUPPLY_PER_FRONTLINE_UNIT * 5
    )


def test_stockpile_capacity_uses_the_turn_buffer_and_floor() -> None:
    # Active front: buffer of STOCKPILE_TURNS x demand.
    demand = SUPPLY_PER_FRONTLINE_UNIT * 5
    assert (
        stockpile_capacity(_cp(Player.RED, front=True, units=5))
        == STOCKPILE_TURNS * demand
    )
    # No front: falls back to the demand floor so a rear CP still holds a buffer.
    assert stockpile_capacity(_cp(Player.RED)) == STOCKPILE_TURNS * MIN_DEMAND
    # A rear producer's capacity scales with its output so it can hold what it makes.
    producer = _cp(Player.RED, tgos=[_tgo("factory", True, True)])  # 16/turn
    assert stockpile_capacity(producer) == STOCKPILE_TURNS * 16.0


def test_production_rate_counts_alive_sources_and_ignores_storage() -> None:
    cp = _cp(
        Player.RED,
        tgos=[
            _tgo("factory", True, True, False),  # 2 alive x 8 = 16
            _tgo("oil", True),  # 1 alive x 6 = 6
            _tgo("ammo", True),  # storage, not a producer -> ignored
        ],
    )
    assert production_rate(cp) == 16.0 + 6.0
    assert production_rate(_cp(Player.RED, tgos=[_tgo("ammo", True)])) == 0.0


def test_supply_factor_full_partial_starved_and_no_front() -> None:
    demand = SUPPLY_PER_FRONTLINE_UNIT * 5  # 10
    assert supply_factor(_cp(Player.RED, front=True, units=5, supply=demand)) == 1.0
    assert supply_factor(_cp(Player.RED, front=True, units=5, supply=demand / 2)) == 0.5
    assert supply_factor(_cp(Player.RED, front=True, units=5, supply=0.0)) == 0.0
    # Over-stocked reserve clamps to 1.0; no front reads as fully supplied.
    assert supply_factor(_cp(Player.RED, front=True, units=5, supply=demand * 9)) == 1.0
    assert supply_factor(_cp(Player.RED, front=False, supply=0.0)) == 1.0


def test_coalition_supply_health_averages_active_fronts_only() -> None:
    demand = SUPPLY_PER_FRONTLINE_UNIT * 5
    cps = [
        _cp(Player.RED, front=True, units=5, supply=demand / 2),  # 0.5
        _cp(Player.RED, front=True, units=5, supply=demand),  # 1.0
        _cp(Player.RED, front=False, supply=0.0),  # skipped (no front)
        _cp(Player.BLUE, front=True, units=5, supply=0.0),  # other coalition
    ]
    game = _game(cps)
    assert coalition_supply_health(game, game.red) == 0.75
    # A coalition with no active front has nothing to starve.
    assert coalition_supply_health(_game([]), game.red) == 1.0


def test_advance_is_a_noop_when_off() -> None:
    cp = _cp(Player.RED, front=True, units=5, tgos=[_tgo("factory", True)], supply=0.0)
    game = _game([cp], on=False)
    advance_war_economy(game)
    assert cp.base.supply == 0.0
    assert game.war_economy_seeded is False
    assert game.messages == []


def test_advance_seeds_produces_and_consumes() -> None:
    # A self-contained front (produces 8, consumes demand 10, no external sources):
    # seeded to capacity, produce (capped), consume a turn's demand, no refill.
    cp = _cp(Player.RED, front=True, units=5, tgos=[_tgo("factory", True)], supply=0.0)
    game = _game([cp], on=True)
    advance_war_economy(game)
    assert game.war_economy_seeded is True
    # capacity(30) + produce(capped) - consume(demand 10) - no external refill.
    assert cp.base.supply == stockpile_capacity(cp) - frontline_demand(cp)
    # One report per side (BLUE has no CPs but still reports its meter).
    assert len(game.messages) == 2
    assert all(title == "War economy" for title, _ in game.messages)


def test_transport_refills_front_from_connected_producer() -> None:
    producer = _cp(Player.RED, tgos=[_tgo("factory", True, True)])  # 16/turn, no front
    front = _cp(Player.RED, front=True, units=10)  # demand 20, capacity 60
    producer.transitive_connected_friendly_destinations = lambda: [front]
    front.transitive_connected_friendly_destinations = lambda: [producer]
    game = _game([producer, front], on=True)
    advance_war_economy(game)
    # Front: seeded 60, consumed 20 -> 40, refilled 20 from the producer -> 60.
    assert front.base.supply == stockpile_capacity(front)
    # The producer shipped that 20 out of its own stock (48 seeded/capped - 20).
    assert producer.base.supply == stockpile_capacity(producer) - 20.0


def test_isolated_front_cannot_refill_and_drains() -> None:
    # No connected producer -> no resupply; the front draws down its buffer.
    front = _cp(Player.RED, front=True, units=10)  # demand 20, capacity 60
    game = _game([front], on=True)
    advance_war_economy(game)
    assert front.base.supply == stockpile_capacity(front) - frontline_demand(front)


# --- §53 P2: the bite (supply_effectiveness) ---


def _bite_cp(*, on: bool, seeded: bool, front: bool, units: int, supply: float) -> Any:
    game = SimpleNamespace(
        settings=SimpleNamespace(war_economy=on),
        war_economy_seeded=seeded,
    )
    return SimpleNamespace(
        coalition=SimpleNamespace(game=game),
        has_active_frontline=front,
        base=SimpleNamespace(supply=supply, total_frontline_units=units),
    )


def test_effectiveness_is_full_when_off_or_unseeded() -> None:
    # Off -> no bite; on-but-not-yet-seeded -> no bite (protects turn-1 combat).
    assert (
        supply_effectiveness(
            _bite_cp(on=False, seeded=True, front=True, units=5, supply=0.0)
        )
        == 1.0
    )
    assert (
        supply_effectiveness(
            _bite_cp(on=True, seeded=False, front=True, units=5, supply=0.0)
        )
        == 1.0
    )


def test_effectiveness_scales_from_floor_to_one() -> None:
    demand = SUPPLY_PER_FRONTLINE_UNIT * 5  # 10
    full = _bite_cp(on=True, seeded=True, front=True, units=5, supply=demand)
    starved = _bite_cp(on=True, seeded=True, front=True, units=5, supply=0.0)
    half = _bite_cp(on=True, seeded=True, front=True, units=5, supply=demand / 2)
    assert supply_effectiveness(full) == 1.0
    assert supply_effectiveness(starved) == _BITE_FLOOR
    assert supply_effectiveness(half) == _BITE_FLOOR + (1.0 - _BITE_FLOOR) * 0.5


def test_effectiveness_full_without_a_front() -> None:
    # No active front -> nothing to starve -> full effectiveness.
    assert (
        supply_effectiveness(
            _bite_cp(on=True, seeded=True, front=False, units=5, supply=0.0)
        )
        == 1.0
    )


def test_effectiveness_survives_ducktyped_control_point() -> None:
    # A bare fake with no coalition/game link must read as full, never raise.
    bare: Any = SimpleNamespace()
    assert supply_effectiveness(bare) == 1.0


# --- §54 M1: per-base munitions stock + turn-boundary debit ---


def _weapon(family: str | None) -> Any:
    return SimpleNamespace(weapon_group=SimpleNamespace(scarce_family=family))


def _member(*families: str | None) -> Any:
    pylons = {i: (_weapon(f) if f else None) for i, f in enumerate(families)}
    return SimpleNamespace(loadout=SimpleNamespace(pylons=pylons))


def _flight(base: Any, members: list[Any]) -> Any:
    return SimpleNamespace(
        iter_members=lambda: members,
        departure=SimpleNamespace(base=base),
    )


def _muni_game(*, on: bool, seeded: bool, base: Any, flights: list[Any]) -> Any:
    return SimpleNamespace(
        settings=SimpleNamespace(restrict_weapons_by_stock=on, war_economy=False),
        munitions_seeded=seeded,
        theater=SimpleNamespace(controlpoints=[SimpleNamespace(base=base)]),
        blue=SimpleNamespace(
            ato=SimpleNamespace(packages=[SimpleNamespace(flights=flights)])
        ),
        red=SimpleNamespace(ato=SimpleNamespace(packages=[])),
    )


def test_munitions_stock_reads_base() -> None:
    cp: Any = SimpleNamespace(base=SimpleNamespace(munitions={"arm": 5}))
    assert munitions_stock(cp, "arm") == 5
    assert munitions_stock(cp, "pgm_bomb") == 0


def test_flight_scarce_loads_counts_by_family() -> None:
    flight = _flight(
        SimpleNamespace(munitions={}),
        [_member("pgm_bomb", None, "arm"), _member("pgm_bomb")],
    )
    assert _flight_scarce_loads(flight) == {"pgm_bomb": 2, "arm": 1}


def test_advance_munitions_is_a_noop_when_off() -> None:
    base = SimpleNamespace(munitions={})
    game = _muni_game(
        on=False,
        seeded=False,
        base=base,
        flights=[_flight(base, [_member("pgm_bomb")])],
    )
    advance_munitions(game)
    assert base.munitions == {}
    assert game.munitions_seeded is False


def test_advance_munitions_seeds_debits_then_rearms() -> None:
    base = SimpleNamespace(munitions={})
    # One flight loads 12 pgm_bomb stores; nothing else scarce.
    flight = _flight(base, [_member(*(["pgm_bomb"] * 12))])
    game = _muni_game(on=True, seeded=False, base=base, flights=[flight])
    advance_munitions(game)
    assert game.munitions_seeded is True
    # pgm_bomb: seeded 24, -12 loaded = 12, +8 rearm = 20 (net drop is visible).
    assert base.munitions["pgm_bomb"] == 20
    # An unused family: seeded 24, no debit, rearm caps back at capacity.
    assert base.munitions["arm"] == MUNITIONS_CAPACITY


def test_base_supply_defaults_for_pre_feature_saves() -> None:
    # Simulate the unpickle path (no __init__): __setstate__ must default supply.
    base = Base.__new__(Base)
    base.__setstate__({"armor": {}, "strength": 1.0})
    assert base.supply == 0.0
    assert base.strength == 1.0


# --- §53 P3: fuel depots gate air readiness (fuel_readiness) ---


def _fuel_cp(*, on: bool, total: int, active: int) -> Any:
    game = SimpleNamespace(settings=SimpleNamespace(fuel_air_readiness=on))
    return SimpleNamespace(
        coalition=SimpleNamespace(game=game),
        total_fuel_depots_count=total,
        active_fuel_depots_count=active,
    )


def test_fuel_readiness_full_when_off_or_no_depots() -> None:
    assert fuel_readiness(_fuel_cp(on=False, total=4, active=0)) == 1.0
    # A base with no fuel infrastructure is never grounded.
    assert fuel_readiness(_fuel_cp(on=True, total=0, active=0)) == 1.0


def test_fuel_readiness_scales_with_alive_depots() -> None:
    assert fuel_readiness(_fuel_cp(on=True, total=4, active=4)) == 1.0
    assert fuel_readiness(_fuel_cp(on=True, total=4, active=0)) == _FUEL_READINESS_FLOOR
    assert fuel_readiness(_fuel_cp(on=True, total=4, active=2)) == (
        _FUEL_READINESS_FLOOR + (1.0 - _FUEL_READINESS_FLOOR) * 0.5
    )


def test_fuel_readiness_survives_ducktyped_control_point() -> None:
    bare: Any = SimpleNamespace()
    assert fuel_readiness(bare) == 1.0
