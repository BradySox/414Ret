"""Weather-aware auto-planning (§67).

Locks the sky classifiers, the recon-suppression gate, the storm demotion of
low-level visual-attack methods (order-preserving, byte-identical in clear
weather or with the feature off), the name coupling to PlanNextAction's
offensive factories, and the HTN-root integration.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from game.commander.tasks.compound.nextaction import PlanNextAction
from game.fourteenth.weather_planning import (
    VISUAL_ATTACK_METHODS,
    demote_weather_hostile_methods,
    poor_visibility_weather,
    recon_suppressed,
    storm,
)
from game.theater import Player
from game.weather.weather import ClearSkies, Cloudy, Raining, Thunderstorm


def _sky(weather_cls: type[Any] | None, on: bool = True) -> Any:
    weather = object.__new__(weather_cls) if weather_cls is not None else None
    return SimpleNamespace(
        settings=SimpleNamespace(weather_aware_planning=on),
        conditions=SimpleNamespace(weather=weather),
    )


def test_sky_classifiers() -> None:
    assert poor_visibility_weather(cast(Any, _sky(Raining)))
    assert poor_visibility_weather(cast(Any, _sky(Thunderstorm)))
    assert not poor_visibility_weather(cast(Any, _sky(ClearSkies)))
    assert not poor_visibility_weather(cast(Any, _sky(Cloudy)))
    assert storm(cast(Any, _sky(Thunderstorm)))
    assert not storm(cast(Any, _sky(Raining)))


def test_missing_conditions_read_as_clear() -> None:
    # Headless fakes / pre-conditions saves degrade to "clear", never a crash.
    no_conditions = SimpleNamespace(
        settings=SimpleNamespace(weather_aware_planning=True)
    )
    assert not poor_visibility_weather(cast(Any, no_conditions))
    assert not recon_suppressed(cast(Any, no_conditions))


def test_recon_suppressed_only_when_on_and_wet() -> None:
    assert recon_suppressed(cast(Any, _sky(Raining)))
    assert recon_suppressed(cast(Any, _sky(Thunderstorm)))
    assert not recon_suppressed(cast(Any, _sky(ClearSkies)))
    assert not recon_suppressed(cast(Any, _sky(Thunderstorm, on=False)))


STOCK = list(PlanNextAction._OFFENSIVE_FACTORIES)


def test_storm_demotes_visual_attack_to_the_tail() -> None:
    order = demote_weather_hostile_methods(cast(Any, _sky(Thunderstorm)), STOCK)
    # Same set, visual-attack methods at the tail, both partitions keeping
    # their relative order.
    assert sorted(order) == sorted(STOCK)
    tail = order[-len(VISUAL_ATTACK_METHODS) :]
    assert tail == [n for n in STOCK if n in VISUAL_ATTACK_METHODS]
    assert order[: -len(VISUAL_ATTACK_METHODS)] == [
        n for n in STOCK if n not in VISUAL_ATTACK_METHODS
    ]


def test_clear_rain_or_off_leave_the_order_unchanged() -> None:
    assert demote_weather_hostile_methods(cast(Any, _sky(ClearSkies)), STOCK) == STOCK
    # Rain is camera-blind (recon gate) but does NOT ground low-level attack.
    assert demote_weather_hostile_methods(cast(Any, _sky(Raining)), STOCK) == STOCK
    assert (
        demote_weather_hostile_methods(cast(Any, _sky(Thunderstorm, on=False)), STOCK)
        == STOCK
    )


def test_visual_attack_names_match_the_offensive_factories() -> None:
    # The demotion is name-keyed (the §40/§55 indirection); a factory rename
    # must update VISUAL_ATTACK_METHODS with it.
    assert set(VISUAL_ATTACK_METHODS) <= set(PlanNextAction._OFFENSIVE_FACTORIES)


def _planner_state(weather_cls: type | None, on: bool = True) -> Any:
    game = _sky(weather_cls, on)
    game.settings.c2_decapitation_effects = False
    coalition = SimpleNamespace(
        player=Player.RED, game=game, ato=SimpleNamespace(packages=[])
    )
    return SimpleNamespace(
        context=SimpleNamespace(
            settings=game.settings,
            coalition=coalition,
            theater=SimpleNamespace(controlpoints=[]),
        )
    )


def test_htn_offensive_order_reads_the_weather() -> None:
    task = PlanNextAction(aircraft_cold_start=False)
    stormy = task._offensive_order(cast(Any, _planner_state(Thunderstorm)))
    assert stormy[-len(VISUAL_ATTACK_METHODS) :] == [
        n for n in STOCK if n in VISUAL_ATTACK_METHODS
    ]
    clear = task._offensive_order(cast(Any, _planner_state(ClearSkies)))
    assert clear == STOCK
