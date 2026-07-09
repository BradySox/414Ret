"""Headless runtime check for the mobile-missile plugin (mobilemissiles-config.lua).

Pins the "script errors and the feature silently never starts" invariant: with a missile
site emitted, the plugin waits out the startup grace, then routes each of the site's
alive groups to a scoot point around the site's campaign centre; a destroyed site stops
being routed; and a mission with no mobileMissiles node is a clean no-op.

A tiny ``mist`` stub records the ``goRoute`` calls (the harness models no DCS movement).
"""

from __future__ import annotations

from typing import Any

from tests.lua.harness import DcsPluginHarness

PLUGIN = "resources/plugins/mobilemissiles/mobilemissiles-config.lua"

_MIST_STUB = """
_scootRoutes = {}
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
        -- The route must START at the group's current position and END at the scoot point;
        -- a destination-only (1-waypoint) route leaves a DCS ground group with no leg to
        -- drive (the launchers-never-move bug). Capture the waypoint count + the last (dest).
        local dest = path[#path]
        _scootRoutes[#_scootRoutes + 1] =
            { group = group:getName(), x = dest.x, y = dest.y, points = #path }
        return true
    end,
}
"""


def _ground_group(name: str) -> dict[str, Any]:
    return {
        "name": name,
        "side": 1,  # RED
        "category": 2,  # GROUND
        "units": [{"name": name + "-u1", "type": "Scud_B"}],
    }


def _harness_with_mist() -> DcsPluginHarness:
    h = DcsPluginHarness()
    h.lua.execute(_MIST_STUB)
    return h


def _routes(h: DcsPluginHarness) -> list[dict[str, Any]]:
    return h.to_python(h.lua.globals()._scootRoutes) or []


def test_scoots_each_site_group_after_the_grace() -> None:
    h = _harness_with_mist()
    h.add_group(_ground_group("SCUD-A"))
    h.add_group(_ground_group("SCUD-B"))
    h.lua.globals().dcsRetribution = h.to_lua(
        {
            "plugins": {"mobilemissiles": {"startGraceS": 5, "scootRadiusM": 4000}},
            "mobileMissiles": {
                "sites": [
                    # coords arrive as strings from the emitter; the plugin tonumber()s.
                    {"groups": ["SCUD-A", "SCUD-B"], "x": "1000.0", "y": "2000.0"}
                ]
            },
        }
    )
    h.load_plugin_script(PLUGIN)

    # Nothing moves during the grace period.
    h.advance_to(4)
    assert _routes(h) == []

    # After the grace, every alive group of the site scoots around the site centre
    # (fake getRandPointInCircle = centre.x + radius).
    h.advance_to(6)
    routes = _routes(h)
    assert {r["group"] for r in routes} == {"SCUD-A", "SCUD-B"}
    # Destination = the scoot point (centre.x 1000 + radius 4000).
    assert all(r["x"] == 5000.0 for r in routes)
    # ...reached via a TWO-waypoint route (current position -> destination); a 1-waypoint
    # route is the launchers-never-move bug this fix closes.
    assert all(r["points"] == 2 for r in routes)
    h.assert_no_lua_errors()


def test_destroyed_site_stops_being_routed() -> None:
    h = _harness_with_mist()
    # The site's group is never added -> aliveGroups() finds nothing.
    h.lua.globals().dcsRetribution = h.to_lua(
        {
            "plugins": {"mobilemissiles": {"startGraceS": 5}},
            "mobileMissiles": {
                "sites": [{"groups": ["Ghost-SCUD"], "x": "0.0", "y": "0.0"}]
            },
        }
    )
    h.load_plugin_script(PLUGIN)
    h.advance_to(600)
    assert _routes(h) == []
    h.assert_no_lua_errors()


def test_no_node_is_a_clean_noop() -> None:
    h = _harness_with_mist()
    h.lua.globals().dcsRetribution = h.to_lua({"plugins": {}})
    h.load_plugin_script(PLUGIN)
    h.advance_to(600)
    assert _routes(h) == []
    h.assert_no_lua_errors()
