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
        _coinRoutes[#_coinRoutes + 1] = { group = group:getName(), x = wp.x, y = wp.y }
        return true
    end,
}
"""


def _ground_group(name: str) -> dict[str, Any]:
    return {
        "name": name,
        "side": 1,  # RED
        "category": 2,  # GROUND
        "units": [{"name": name + "-u1", "type": "UAZ-469"}],
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
