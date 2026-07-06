"""Command-center decapitation -> degraded enemy planning (§52, Feature A).

Locks the coupling: a side's dead command centers scale its planner
unpredictability up (0 when off / intact), the health fraction is exact, the SITREP
status line reads the enemy network, and a C2-less campaign is a no-op.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from game.fourteenth.c2_decapitation import (
    MAX_DECAP_UNPREDICTABILITY,
    c2_health,
    c2_status_line,
    unpredictability_bonus,
)
from game.theater import Player


def _tgo(category: str, *alive: bool) -> Any:
    units = [SimpleNamespace(alive=a) for a in alive]
    return SimpleNamespace(category=category, groups=[SimpleNamespace(units=units)])


def _coalition(player: Player) -> Any:
    return SimpleNamespace(player=player)


def _theater(cps: list[Any]) -> Any:
    return SimpleNamespace(controlpoints=cps)


def _cp(owner: Player, tgos: list[Any]) -> Any:
    return SimpleNamespace(captured=owner, ground_objects=tgos)


def _settings(on: bool = True) -> Any:
    return SimpleNamespace(c2_decapitation_effects=on)


RED = _coalition(Player.RED)


def test_health_is_the_alive_fraction_of_own_command_centers() -> None:
    theater = _theater(
        [
            _cp(
                Player.RED, [_tgo("commandcenter", True), _tgo("commandcenter", False)]
            ),
            _cp(Player.RED, [_tgo("commandcenter", True)]),
            # A blue-owned CC and a non-C2 red TGO are both ignored.
            _cp(Player.BLUE, [_tgo("commandcenter", True)]),
            _cp(Player.RED, [_tgo("aa", True)]),
        ]
    )
    # 2 of 3 red command centers alive.
    assert c2_health(cast(Any, RED), cast(Any, theater)) == 2 / 3


def test_no_command_centers_is_full_health() -> None:
    theater = _theater([_cp(Player.RED, [_tgo("aa", True)])])
    assert c2_health(cast(Any, RED), cast(Any, theater)) == 1.0


def test_bonus_scales_with_the_dead_fraction() -> None:
    intact = _theater([_cp(Player.RED, [_tgo("commandcenter", True)])])
    half = _theater(
        [_cp(Player.RED, [_tgo("commandcenter", True), _tgo("commandcenter", False)])]
    )
    dead = _theater([_cp(Player.RED, [_tgo("commandcenter", False)])])

    assert unpredictability_bonus(cast(Any, RED), cast(Any, intact), _settings()) == 0
    assert unpredictability_bonus(
        cast(Any, RED), cast(Any, half), _settings()
    ) == round(0.5 * MAX_DECAP_UNPREDICTABILITY)
    assert (
        unpredictability_bonus(cast(Any, RED), cast(Any, dead), _settings())
        == MAX_DECAP_UNPREDICTABILITY
    )


def test_bonus_is_zero_when_the_feature_is_off() -> None:
    dead = _theater([_cp(Player.RED, [_tgo("commandcenter", False)])])
    assert (
        unpredictability_bonus(cast(Any, RED), cast(Any, dead), _settings(on=False))
        == 0
    )


def _game(theater: Any, on: bool = True) -> Any:
    return SimpleNamespace(
        theater=theater,
        settings=_settings(on),
        coalition_for=lambda _p: RED,
    )


def test_status_line_reports_a_degraded_enemy_network() -> None:
    theater = _theater(
        [_cp(Player.RED, [_tgo("commandcenter", True), _tgo("commandcenter", False)])]
    )
    line = c2_status_line(cast(Any, _game(theater)), Player.RED)
    assert line == "1/2 command posts operational"


def test_status_line_is_none_when_intact_off_or_c2_less() -> None:
    intact = _theater([_cp(Player.RED, [_tgo("commandcenter", True)])])
    assert c2_status_line(cast(Any, _game(intact)), Player.RED) is None
    degraded = _theater([_cp(Player.RED, [_tgo("commandcenter", False)])])
    assert c2_status_line(cast(Any, _game(degraded, on=False)), Player.RED) is None
    c2_less = _theater([_cp(Player.RED, [_tgo("aa", True)])])
    assert c2_status_line(cast(Any, _game(c2_less)), Player.RED) is None
