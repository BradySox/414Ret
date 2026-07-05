"""Headless runtime check for the COIN in-mission movement plugin (coin-config.lua).

Pins the "script errors and the feature silently never starts" invariant the luac -p gate
can't catch: with a live HVT + mobile VBIED emitted, the plugin arms movement after the
grace period -- the HVT is routed to a patrol point around its area and the VBIED is routed
at its target base, with no Lua errors -- and it no-ops cleanly when no coin node is present.

A tiny ``mist`` stub records the ``goRoute`` calls (the harness models no DCS movement).
The plugin's alarm-state / ROE ``getController`` block is pcall-guarded, so it needs no
controller stub.
"""

from __future__ import annotations

import math
from typing import Any

from tests.lua.harness import DcsPluginHarness

COIN_PLUGIN = "resources/plugins/coin/coin-config.lua"

# mist stub: enough for the plugin's route math, recording each goRoute into _coinRoutes.
_MIST_STUB = """
_coinRoutes = {}
mist = {
    utils = { kmphToMps = function(k) return (tonumber(k) or 0) * 1000 / 3600 end },
    ground = {
        buildWP = function(pt, action, mps)
            return { x = pt.x, y = pt.y, speed = mps, action = action }
        end,
    },
    getRandPointInCircle = function(p, r)
        return { x = p.x + (tonumber(r) or 0), y = p.y }
    end,
    goRoute = function(group, path)
        local wp = path[1]
        _coinRoutes[#_coinRoutes + 1] =
            { group = group:getName(), x = wp.x, y = wp.y, speed = wp.speed }
        return true
    end,
}
"""


def _ground_group(name: str, x: float = 0.0, z: float = 0.0) -> dict[str, Any]:
    return {
        "name": name,
        "side": 1,  # RED
        "category": 2,  # GROUND
        "units": [{"name": name + "-u1", "type": "UAZ-469", "x": x, "z": z}],
    }


def _harness_with_mist() -> DcsPluginHarness:
    h = DcsPluginHarness()
    h.lua.execute(_MIST_STUB)
    return h


def _routes(h: DcsPluginHarness) -> list[dict[str, Any]]:
    return h.to_python(h.lua.globals()._coinRoutes) or []


def test_arms_hvt_patrol_and_vbied_drive_after_grace() -> None:
    h = _harness_with_mist()
    h.add_group(_ground_group("HVT-Convoy"))
    h.add_group(_ground_group("VBIED-1"))
    h.lua.globals().dcsRetribution = h.to_lua(
        {
            "plugins": {"coin": {"startGraceS": 5}},
            "coin": {
                # coords arrive as strings from the emitter; the plugin tonumber()s them.
                "hvt": {"groups": ["HVT-Convoy"], "x": "1000.0", "y": "2000.0"},
                "vbieds": [
                    {
                        "groups": ["VBIED-1"],
                        "x": "3000.0",
                        "y": "4000.0",
                        "targetX": "0.0",
                        "targetY": "0.0",
                    }
                ],
            },
        }
    )
    h.load_plugin_script(COIN_PLUGIN)

    # Nothing moves during the grace period.
    h.advance_to(4)
    assert _routes(h) == []

    # After grace, both movers are routed exactly once.
    h.advance_to(6)
    routes = _routes(h)
    by_group = {r["group"]: r for r in routes}
    assert set(by_group) == {"HVT-Convoy", "VBIED-1"}
    # HVT wanders around its centre (fake getRandPointInCircle = centre.x + radius=4000).
    assert by_group["HVT-Convoy"]["x"] == 5000.0
    # The VBIED drives straight at its target base (the origin).
    assert by_group["VBIED-1"]["x"] == 0.0 and by_group["VBIED-1"]["y"] == 0.0
    h.assert_no_lua_errors()


def test_no_coin_node_is_a_clean_noop() -> None:
    h = _harness_with_mist()
    h.lua.globals().dcsRetribution = h.to_lua({"plugins": {}})
    h.load_plugin_script(COIN_PLUGIN)
    h.advance_to(120)
    assert _routes(h) == []
    h.assert_no_lua_errors()


def test_cell_wander_and_infiltrator_creep_are_routed_after_grace() -> None:
    h = _harness_with_mist()
    h.add_group(_ground_group("Cell-1"))
    h.add_group(_ground_group("Infil-1"))
    h.lua.globals().dcsRetribution = h.to_lua(
        {
            "plugins": {"coin": {"startGraceS": 5, "cellPatrolRadiusM": 2000}},
            "coin": {
                "cells": [{"groups": ["Cell-1"], "x": "1000.0", "y": "0.0"}],
                "infiltrators": [
                    {
                        "groups": ["Infil-1"],
                        "x": "5000.0",
                        "y": "5000.0",
                        "targetX": "0.0",
                        "targetY": "0.0",
                    }
                ],
            },
        }
    )
    h.load_plugin_script(COIN_PLUGIN)

    h.advance_to(4)
    assert _routes(h) == []

    h.advance_to(6)
    by_group = {r["group"]: r for r in _routes(h)}
    assert set(by_group) == {"Cell-1", "Infil-1"}
    # The cell wanders around its patch (fake getRandPointInCircle = centre.x + radius).
    assert by_group["Cell-1"]["x"] == 3000.0
    # The infiltrator creeps straight at the base it is taking (the origin).
    assert by_group["Infil-1"]["x"] == 0.0 and by_group["Infil-1"]["y"] == 0.0
    h.assert_no_lua_errors()


def test_harassment_grace_then_barrage_with_the_player_field_double_guard() -> None:
    h = _harness_with_mist()
    h.lua.globals().dcsRetribution = h.to_lua(
        {
            "plugins": {"coin": {"harassGraceS": 10, "harassIntervalS": 30}},
            "coin": {
                "harassment": {
                    "bases": [
                        {"name": "FOB Rhino", "x": "0.0", "y": "0.0"},
                        # A player field Python should never have emitted -- the
                        # Lua-side double-guard must keep it safe anyway.
                        {"name": "Player Field", "x": "100000.0", "y": "100000.0"},
                    ],
                    "excludedBases": ["Player Field"],
                }
            },
        }
    )
    h.load_plugin_script(COIN_PLUGIN)

    # Hard no-fire window at mission start.
    h.advance_to(9)
    assert h.records("explosions") == []

    # A generous run of cadences: the watched base draws fire, the excluded never does.
    h.advance_to(600)
    barrage = h.records("explosions")
    assert barrage, "a base in mortar reach must draw fire once the grace expires"
    for impact in barrage:
        assert impact["t"] >= 10
        # Impacts scatter around the base within the dispersion radius (default 250 m).
        assert math.hypot(impact["x"], impact["z"]) <= 250 + 1
        distance_from_player_field = math.hypot(
            impact["x"] - 100000, impact["z"] - 100000
        )
        assert distance_from_player_field > 10000, "the excluded base drew fire"
    assert any("Incoming" in t["text"] for t in h.records("texts"))
    h.assert_no_lua_errors()


def _vbied(name: str, tx: float = 0.0, ty: float = 0.0) -> dict[str, Any]:
    return {
        "groups": [name],
        "x": "0.0",
        "y": "0.0",
        "targetX": str(tx),
        "targetY": str(ty),
    }


def test_one_way_movers_are_paced_to_the_min_journey_window() -> None:
    """The 90-minute rule (user call 2026-07-05): a VBIED/infiltrator drive must still
    be under way at least minJourneyS into the mission, so a cold-starting player can
    always make the intercept. The ordered speed = remaining distance / remaining time,
    capped at the configured speed and floored at a crawl."""
    h = _harness_with_mist()
    # 50 km out: paced well below the 45 km/h max so arrival lands at ~90 min.
    h.add_group(_ground_group("VBIED-Paced", x=30_000.0, z=40_000.0))
    # 500 km out: pacing would need 333 km/h -- capped at the configured speed.
    h.add_group(_ground_group("VBIED-Far", x=300_000.0, z=400_000.0))
    # 1 km out: pacing would be 0.7 km/h -- floored at the 5 km/h crawl.
    h.add_group(_ground_group("VBIED-Near", x=1_000.0, z=0.0))
    h.lua.globals().dcsRetribution = h.to_lua(
        {
            "plugins": {"coin": {"startGraceS": 5}},
            "coin": {
                "vbieds": [
                    _vbied("VBIED-Paced"),
                    _vbied("VBIED-Far"),
                    _vbied("VBIED-Near"),
                ]
            },
        }
    )
    h.load_plugin_script(COIN_PLUGIN)
    h.advance_to(6)
    speeds = {r["group"]: r["speed"] for r in _routes(h)}

    # Paced: ~50,000 m over the ~5,395 s left in the default 5,400 s window.
    assert 9.0 <= speeds["VBIED-Paced"] <= 9.6
    # Capped at the configured 45 km/h (12.5 m/s) -- pacing never speeds a mover UP.
    assert abs(speeds["VBIED-Far"] - 12.5) < 0.01
    # Floored at the 5 km/h crawl (1.39 m/s) -- a close target still creeps in.
    assert abs(speeds["VBIED-Near"] - 5.0 * 1000 / 3600) < 0.01
    h.assert_no_lua_errors()


def test_min_journey_window_passed_restores_full_speed() -> None:
    h = _harness_with_mist()
    h.add_group(_ground_group("VBIED-1", x=30_000.0, z=40_000.0))
    h.lua.globals().dcsRetribution = h.to_lua(
        {
            # A 1 s window is already over when the grace expires -> configured speed.
            "plugins": {"coin": {"startGraceS": 5, "minJourneyS": 1}},
            "coin": {"vbieds": [_vbied("VBIED-1")]},
        }
    )
    h.load_plugin_script(COIN_PLUGIN)
    h.advance_to(6)
    speeds = {r["group"]: r["speed"] for r in _routes(h)}
    assert abs(speeds["VBIED-1"] - 12.5) < 0.01
    h.assert_no_lua_errors()


def test_infiltrator_creep_is_paced_too() -> None:
    h = _harness_with_mist()
    # 20 km out at a 15 km/h configured creep (arrival ~80 min): paced down so the
    # walk is still in progress at the 90-minute mark.
    h.add_group(_ground_group("Infil-1", x=12_000.0, z=16_000.0))
    h.lua.globals().dcsRetribution = h.to_lua(
        {
            "plugins": {"coin": {"startGraceS": 5}},
            "coin": {
                "infiltrators": [
                    {
                        "groups": ["Infil-1"],
                        "x": "0.0",
                        "y": "0.0",
                        "targetX": "0.0",
                        "targetY": "0.0",
                    }
                ]
            },
        }
    )
    h.load_plugin_script(COIN_PLUGIN)
    h.advance_to(6)
    speeds = {r["group"]: r["speed"] for r in _routes(h)}
    # ~20,000 m over ~5,395 s = ~3.7 m/s; below the configured 15 km/h (4.17 m/s).
    assert 3.5 <= speeds["Infil-1"] <= 3.9
    h.assert_no_lua_errors()


def test_dead_hvt_stops_being_routed() -> None:
    # A decapitated HVT (its group gone) must stop scheduling, not error.
    h = _harness_with_mist()
    # VBIED exists, HVT group never added -> firstAlive(hvt) is nil.
    h.add_group(_ground_group("VBIED-1"))
    h.lua.globals().dcsRetribution = h.to_lua(
        {
            "plugins": {"coin": {"startGraceS": 5}},
            "coin": {
                "hvt": {"groups": ["Ghost-HVT"], "x": "1000.0", "y": "2000.0"},
                "vbieds": [
                    {
                        "groups": ["VBIED-1"],
                        "x": "3000.0",
                        "y": "4000.0",
                        "targetX": "0.0",
                        "targetY": "0.0",
                    }
                ],
            },
        }
    )
    h.load_plugin_script(COIN_PLUGIN)
    h.advance_to(6)
    groups = {r["group"] for r in _routes(h)}
    assert groups == {"VBIED-1"}  # the missing HVT is simply never routed
    h.assert_no_lua_errors()
