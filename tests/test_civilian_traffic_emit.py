"""Civilian-traffic preamble emission (Python side).

``_civilian_traffic_preamble`` bakes the combat-airbase exclusion list, the active
front contested points, the keep-out radius, and the regional route caps into the
DO SCRIPT preamble that civilian_traffic.lua reads at runtime. Tested directly with
fakes so no pydcs Mission or plugin-manager state is required. The Lua keep-out /
prune logic itself can only be validated in-game (no Lua runner in CI).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from game.missiongenerator.luagenerator import (
    CIVILIAN_TRAFFIC_KEEPOUT_M,
    CIVILIAN_TRAFFIC_MAXDIST_FW_KM,
    CIVILIAN_TRAFFIC_MAXDIST_HELO_KM,
    CIVILIAN_TRAFFIC_STRAY_CHANCE,
    LuaGenerator,
)


def _cp(name: str, *, airport: bool) -> Any:
    return SimpleNamespace(name=name, dcs_airport=object() if airport else None)


def _front(x: float, y: float) -> Any:
    return SimpleNamespace(position=SimpleNamespace(x=x, y=y))


def _generator(controlpoints: list[Any], fronts: list[Any]) -> LuaGenerator:
    theater = SimpleNamespace(
        controlpoints=controlpoints,
        conflicts=lambda: iter(fronts),
    )
    game = cast(Any, SimpleNamespace(theater=theater))
    return LuaGenerator(game, cast(Any, None), cast(Any, None))


def test_excl_lists_only_airbase_controlpoints_sorted() -> None:
    cps = [
        _cp("Ramat David", airport=True),
        _cp("Carrier Strike Group", airport=False),  # not an airbase
        _cp("Incirlik", airport=True),
    ]
    preamble = _generator(cps, [])._civilian_traffic_preamble()
    # Sorted, airbase-only, and the carrier is absent.
    assert '_CIVILIAN_TRAFFIC_EXCL = {"Incirlik", "Ramat David"}' in preamble
    assert "Carrier Strike Group" not in preamble


def test_emits_front_points_and_routing_constants() -> None:
    fronts = [_front(1000.0, 2000.0), _front(-3000.0, 4000.0)]
    preamble = _generator([], fronts)._civilian_traffic_preamble()

    assert "{x=1000.0, y=2000.0}" in preamble
    assert "{x=-3000.0, y=4000.0}" in preamble
    assert f"_CIVILIAN_TRAFFIC_KEEPOUT = {CIVILIAN_TRAFFIC_KEEPOUT_M}\n" in preamble
    assert (
        f"_CIVILIAN_TRAFFIC_MAXDIST_FW = {CIVILIAN_TRAFFIC_MAXDIST_FW_KM}\n" in preamble
    )
    assert (
        f"_CIVILIAN_TRAFFIC_MAXDIST_HELO = {CIVILIAN_TRAFFIC_MAXDIST_HELO_KM}\n"
        in preamble
    )
    assert (
        f"_CIVILIAN_TRAFFIC_STRAY_CHANCE = {CIVILIAN_TRAFFIC_STRAY_CHANCE}\n"
        in preamble
    )


def test_no_fronts_emits_empty_fronts_table() -> None:
    preamble = _generator(
        [_cp("Incirlik", airport=True)], []
    )._civilian_traffic_preamble()
    assert "_CIVILIAN_TRAFFIC_FRONTS = {}\n" in preamble
