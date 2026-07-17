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


def test_fire_mission_group_holds_then_scoots_with_a_task_reset() -> None:
    # Fire first, THEN scoot: a group with a forwarded fire-mission hold must not
    # be routed while its launch window (+ margin) is open -- the route push would
    # setTask-replace the pending Hold -> FireAtPoint (the 2026-07-16 flown
    # clobber: 12 of 13 batteries silently lost their fire missions to the first
    # relocation). Once the window passes it scoots, clearing the spent fire task
    # first (a fired launcher otherwise pins on the dead task and never moves).
    h = _harness_with_mist()
    h.add_group(_ground_group("SHAHED-BAT"))
    h.add_group(_ground_group("SCUD-FREE"))
    h.lua.globals().dcsRetribution = h.to_lua(
        {
            "plugins": {
                "mobilemissiles": {
                    "startGraceS": 5,
                    "scootIntervalS": 60,
                    "fireMarginS": 30,
                }
            },
            "mobileMissiles": {
                "sites": [
                    {
                        "groups": ["SHAHED-BAT", "SCUD-FREE"],
                        "x": "1000.0",
                        "y": "2000.0",
                        # Parallel arrays; seconds arrive as strings from the emitter.
                        "fireHoldGroups": ["SHAHED-BAT"],
                        "fireHoldS": ["50"],
                    }
                ]
            },
        }
    )
    h.load_plugin_script(PLUGIN)

    # First tick (t=5): the free group scoots; the fire-mission group sits still.
    h.advance_to(6)
    assert {r["group"] for r in _routes(h)} == {"SCUD-FREE"}

    # Second tick (t=65) is still inside hold(50) + margin(30) = 80: still held.
    h.advance_to(66)
    assert {r["group"] for r in _routes(h)} == {"SCUD-FREE"}

    # Third tick (t=125) is past the window: the battery scoots too, and the
    # spent fire task was cleared before the route push.
    h.advance_to(126)
    assert "SHAHED-BAT" in {r["group"] for r in _routes(h)}
    resets = h.records("controllerResets")
    assert {r["group"] for r in resets} == {"SHAHED-BAT"}
    h.assert_no_lua_errors()


def test_group_without_fire_mission_never_gets_a_task_reset() -> None:
    # A plain scooting group (no fire mission) must be routed WITHOUT resetTask --
    # there is nothing to clear, and a reset would wipe whatever the group is doing.
    h = _harness_with_mist()
    h.add_group(_ground_group("SCUD-A"))
    h.lua.globals().dcsRetribution = h.to_lua(
        {
            "plugins": {"mobilemissiles": {"startGraceS": 5}},
            "mobileMissiles": {
                "sites": [{"groups": ["SCUD-A"], "x": "0.0", "y": "0.0"}]
            },
        }
    )
    h.load_plugin_script(PLUGIN)
    h.advance_to(6)
    assert {r["group"] for r in _routes(h)} == {"SCUD-A"}
    assert h.records("controllerResets") == []
    h.assert_no_lua_errors()


def test_site_loops_are_staggered_across_the_interval() -> None:
    """39 synchronized sites routing in the same frame pegged the sim thread
    (2026-07-17 Scenic Route fly: continuous ANTIFREEZE, single-digit FPS).
    Each site's loop now starts grace + (i-1) * interval/N in, so route pushes
    spread across the interval instead of landing together."""
    h = _harness_with_mist()
    h.add_group(_ground_group("SITE-1"))
    h.add_group(_ground_group("SITE-2"))
    h.lua.globals().dcsRetribution = h.to_lua(
        {
            "plugins": {"mobilemissiles": {"startGraceS": 5, "scootIntervalS": 100}},
            "mobileMissiles": {
                "sites": [
                    {"groups": ["SITE-1"], "x": "0.0", "y": "0.0"},
                    {"groups": ["SITE-2"], "x": "0.0", "y": "0.0"},
                ]
            },
        }
    )
    h.load_plugin_script(PLUGIN)

    # First slice: only site 1 (grace 5); site 2 waits its 50 s stagger slot.
    h.advance_to(6)
    assert {r["group"] for r in _routes(h)} == {"SITE-1"}

    # Site 2's slot (grace + interval/2 = 55).
    h.advance_to(56)
    assert {r["group"] for r in _routes(h)} == {"SITE-1", "SITE-2"}
    h.assert_no_lua_errors()
