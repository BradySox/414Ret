"""Adaptive procurement (§68).

Locks the air-defense site repair (gate, per-turn cap, priority order, budget
skip, category exclusions, wreck cleanup) and the price-weighted ground-unit
choice gate.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import patch

from dcs.mapping import Point
from dcs.terrain import Caucasus

from game.fourteenth.adaptive_procurement import (
    MAX_AIR_DEFENSE_REPAIRS_PER_TURN,
    repair_air_defenses,
)
from game.procurement import ProcurementAi

_TERRAIN = Caucasus()


# --- air-defense site repair ---


def _unit(
    price: int, alive: bool = False, name: str = "unit", x: float = 0, y: float = 0
) -> Any:
    return SimpleNamespace(
        alive=alive,
        repairable=True,
        unit_type=SimpleNamespace(price=price),
        unit_name=name,
        position=Point(x, y, _TERRAIN),
        ground_object=SimpleNamespace(name="site", invalidate_threat_poly=lambda: None),
    )


def _site(category: str, *units: Any) -> Any:
    return SimpleNamespace(
        category=category, groups=[SimpleNamespace(units=list(units))]
    )


def _cp(*tgos: Any) -> Any:
    return SimpleNamespace(ground_objects=list(tgos))


def _repair_game(on: bool = True, destroyed: list[dict[str, Any]] | None = None) -> Any:
    wrecks = destroyed if destroyed is not None else []
    return SimpleNamespace(
        settings=SimpleNamespace(auto_repair_air_defenses=on),
        get_destroyed_units=lambda: wrecks,
        theater=SimpleNamespace(terrain=_TERRAIN),
    )


def test_repair_is_a_noop_when_off() -> None:
    dead = _unit(10)
    cp = _cp(_site("aa", dead))
    assert repair_air_defenses(cast(Any, _repair_game(on=False)), [cp], 100.0) == 100.0
    assert not dead.alive


def test_repair_prioritises_degraded_sites_and_radars_within_the_cap() -> None:
    # A degraded site (one unit still alive) with a pricey dead radar and a
    # cheap dead launcher, plus a fully-dead site: the radar and the launcher
    # at the degraded site go first (site priority, then price), the cap stops
    # the fully-dead site's rebuild.
    radar = _unit(20, name="radar")
    launcher = _unit(6, name="launcher")
    alive_launcher = _unit(6, alive=True)
    degraded = _site("aa", radar, launcher, alive_launcher)
    flattened_unit = _unit(30, name="flattened")
    flattened = _site("aa", flattened_unit)
    budget = repair_air_defenses(
        cast(Any, _repair_game()), [_cp(degraded, flattened)], 100.0
    )
    assert radar.alive and launcher.alive
    assert not flattened_unit.alive  # cap of 2 reached first
    assert budget == 100.0 - 20 - 6
    assert MAX_AIR_DEFENSE_REPAIRS_PER_TURN == 2


def test_repair_skips_what_the_budget_cannot_cover() -> None:
    pricey = _unit(50, name="pricey")
    cheap = _unit(5, name="cheap")
    cp = _cp(_site("ewr", pricey, cheap))
    budget = repair_air_defenses(cast(Any, _repair_game()), [cp], 10.0)
    assert not pricey.alive
    assert cheap.alive
    assert budget == 5.0


def test_repair_never_touches_c2_or_alive_or_typeless_units() -> None:
    cc_unit = _unit(10, name="hq")
    comms_unit = _unit(10, name="comms")
    typeless = _unit(10, name="static")
    typeless.unit_type = None
    alive = _unit(10, alive=True)
    cps = [
        _cp(
            _site("commandcenter", cc_unit),
            _site("comms", comms_unit),
            _site("aa", typeless, alive),
        )
    ]
    budget = repair_air_defenses(cast(Any, _repair_game()), cps, 100.0)
    assert budget == 100.0
    assert not cc_unit.alive and not comms_unit.alive and not typeless.alive


def test_repair_clears_the_wreck_marker() -> None:
    dead = _unit(10, x=100, y=200)
    wrecks = [
        {"x": 100.0, "z": 200.0, "type": "SAM"},  # at the repaired unit
        {"x": 5000.0, "z": 5000.0, "type": "Tank"},  # far away, stays
    ]
    game = _repair_game(destroyed=wrecks)
    repair_air_defenses(cast(Any, game), [_cp(_site("aa", dead))], 100.0)
    assert dead.alive
    assert wrecks == [{"x": 5000.0, "z": 5000.0, "type": "Tank"}]


# --- price-weighted unit choice ---


_TANK_CLASS = object()  # identity-compared sentinel for UnitClass


@dataclass(frozen=True)
class _FakeUnit:  # hashable: faction unit pools go through set()
    price: int
    unit_class: Any


def _procurement_ai(adaptive: bool) -> ProcurementAi:
    ai = ProcurementAi.__new__(ProcurementAi)
    ai.game = cast(
        Any, SimpleNamespace(settings=SimpleNamespace(adaptive_procurement=adaptive))
    )
    ai.faction = cast(
        Any,
        SimpleNamespace(
            frontline_units=[
                _FakeUnit(price=30, unit_class=_TANK_CLASS),
                _FakeUnit(price=3, unit_class=_TANK_CLASS),
            ],
            artillery_units=[],
        ),
    )
    return ai


def test_unit_choice_is_price_weighted_when_adaptive() -> None:
    ai = _procurement_ai(adaptive=True)
    with patch("game.procurement.random.choices") as choices:
        choices.side_effect = lambda units, weights, k: [units[0]]
        picked = ai.affordable_ground_unit_of_class(100.0, cast(Any, _TANK_CLASS))
    assert picked is not None
    (units,), kwargs = choices.call_args
    assert sorted(kwargs["weights"]) == [3, 30]
    assert kwargs["k"] == 1


def test_unit_choice_is_uniform_when_off() -> None:
    ai = _procurement_ai(adaptive=False)
    with patch("game.procurement.random.choice") as choice:
        choice.side_effect = lambda units: units[0]
        ai.affordable_ground_unit_of_class(100.0, cast(Any, _TANK_CLASS))
    assert choice.called
