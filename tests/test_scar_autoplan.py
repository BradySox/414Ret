"""Tests for SCAR Phase-3 auto-planning (opt-in, blue-only).

`PlanScarHunts` frags up to ``scar_autoplan_per_turn`` player-flyable SCAR
packages per turn against enemy armor concentrations — but only when the
`scar_autoplan` setting is on and the planner is blue. Each `PlanScar` consumes
its battle position, so the hunts spread across *different* targets instead of
stacking on one. With the setting off it is a strict no-op.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from game.ato.flighttype import FlightType
from game.commander.tasks.compound.scarhunts import PlanScarHunts
from game.commander.tasks.primitive.scar import PlanScar


def _state(
    *,
    autoplan: bool,
    is_blue: bool,
    battle_positions: list[Any],
    per_turn: int = 2,
    hunts_planned: int = 0,
    unpredictability: int = 0,
) -> Any:
    # enemy_battle_positions: {cp: group}; group.in_priority_order is iterable.
    group = SimpleNamespace(in_priority_order=list(battle_positions))
    return SimpleNamespace(
        context=SimpleNamespace(
            settings=SimpleNamespace(
                scar_autoplan=autoplan,
                scar_autoplan_per_turn=per_turn,
                ownfor_planner_unpredictability=unpredictability,
                opfor_planner_unpredictability=unpredictability,
            ),
            coalition=SimpleNamespace(player=SimpleNamespace(is_blue=is_blue)),
        ),
        enemy_battle_positions={object(): group} if battle_positions else {},
        scar_hunts_planned=hunts_planned,
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


def test_blue_on_yields_a_scar_per_battle_position() -> None:
    top = object()
    second = object()
    state = _state(autoplan=True, is_blue=True, battle_positions=[top, second])
    methods = _methods(state)
    # One candidate hunt per *distinct* battle position (the planner applies them
    # one at a time, each consuming its target, up to the per-turn cap) — in
    # priority order at unpredictability 0.
    targets = [m[0].target for m in methods]
    assert targets == [top, second]
    assert all(isinstance(m[0], PlanScar) for m in methods)


def test_per_turn_cap_already_met_yields_nothing() -> None:
    # Once scar_autoplan_per_turn hunts are planned this turn, no more are offered.
    state = _state(
        autoplan=True,
        is_blue=True,
        battle_positions=[object(), object()],
        per_turn=2,
        hunts_planned=2,
    )
    assert _methods(state) == []


def test_plan_scar_consumes_its_battle_position() -> None:
    # apply_effects eliminates the target and bumps the per-turn counter, so the
    # planner spreads across targets instead of stacking on one (the bug fix).
    # package defaults to None, so the base apply_effects is a no-op here.
    target = object()
    eliminated: list[Any] = []
    state = cast(
        Any,
        SimpleNamespace(
            eliminate_battle_position=eliminated.append,
            scar_hunts_planned=0,
        ),
    )
    PlanScar(cast(Any, target)).apply_effects(state)
    assert eliminated == [target]
    assert state.scar_hunts_planned == 1


def test_plan_scar_skips_an_already_claimed_position() -> None:
    # preconditions short-circuit to False (before the expensive fulfill check)
    # once the battle position has been eliminated by an earlier hunt.
    state = cast(Any, SimpleNamespace(has_battle_position=lambda _t: False))
    assert PlanScar(cast(Any, object())).preconditions_met(state) is False


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
