"""Tests for SCAR Phase-3 auto-planning (opt-in, blue-only).

`PlanScarHunts` frags one player-flyable SCAR package per turn against the
highest-priority enemy armor concentration — but only when the `scar_autoplan`
setting is on and the planner is blue. With the setting off it is a strict
no-op, so existing campaigns are unchanged.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from game.ato.flighttype import FlightType
from game.commander.tasks.compound.scarhunts import PlanScarHunts
from game.commander.tasks.primitive.scar import PlanScar


def _state(*, autoplan: bool, is_blue: bool, battle_positions: list[Any]) -> Any:
    # enemy_battle_positions: {cp: group}; group.in_priority_order is iterable.
    group = SimpleNamespace(in_priority_order=list(battle_positions))
    return SimpleNamespace(
        context=SimpleNamespace(
            settings=SimpleNamespace(scar_autoplan=autoplan),
            coalition=SimpleNamespace(player=SimpleNamespace(is_blue=is_blue)),
        ),
        enemy_battle_positions={object(): group} if battle_positions else {},
    )


def _methods(state: Any) -> list[Any]:
    return list(PlanScarHunts().each_valid_method(cast(Any, state)))


def test_off_yields_nothing() -> None:
    state = _state(autoplan=False, is_blue=True, battle_positions=[object()])
    assert _methods(state) == []


def test_red_planner_yields_nothing() -> None:
    state = _state(autoplan=True, is_blue=False, battle_positions=[object()])
    assert _methods(state) == []


def test_no_battle_positions_yields_nothing() -> None:
    state = _state(autoplan=True, is_blue=True, battle_positions=[])
    assert _methods(state) == []


def test_blue_on_yields_one_scar_against_top_target() -> None:
    top = object()
    second = object()
    state = _state(autoplan=True, is_blue=True, battle_positions=[top, second])
    methods = _methods(state)
    # Exactly one auto-fragged hunt, against the highest-priority battle position.
    assert len(methods) == 1
    (task,) = methods[0]
    assert isinstance(task, PlanScar)
    assert task.target is top


def _scar_target() -> Any:
    # get_flight_size() reads the fleet-package weights off the target's coalition;
    # weight only the 2-ship so the size is deterministic.
    settings = SimpleNamespace(
        fpa_2ship_weight=1, fpa_3ship_weight=0, fpa_4ship_weight=0
    )
    return SimpleNamespace(
        coalition=SimpleNamespace(game=SimpleNamespace(settings=settings))
    )


def test_plan_scar_proposes_scar_flight_then_escorts() -> None:
    task = PlanScar(cast(Any, _scar_target()))
    task.propose_flights()
    tasks = [f.task for f in task.flights]
    assert tasks[0] is FlightType.SCAR
    assert FlightType.SEAD_ESCORT in tasks
    assert FlightType.ESCORT in tasks
