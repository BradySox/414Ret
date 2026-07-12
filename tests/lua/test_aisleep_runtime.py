"""Headless runtime check for the ground AI sleep plugin (aisleep-config.lua).

Pins the safety invariants the feature promises: a managed garrison sleeps only when
the sky above it is clear and wakes the moment an aircraft closes inside the wake
radius (or the moment it is hit, whatever the range); a parked aircraft never wakes
anything; the hysteresis band never flaps the controller; and a mission with no
aiSleep node is a clean no-op. The harness models no DCS AI -- what "sleep" actually
buys is the in-game pass (checklist B11).
"""

from __future__ import annotations

from typing import Any

from tests.lua.harness import DcsPluginHarness

PLUGIN = "resources/plugins/aisleep/aisleep-config.lua"

# 15 NM wake radius in meters (the plugin default), and the 1.25x sleep boundary.
WAKE_M = 15 * 1852
SLEEP_M = WAKE_M * 1.25


def _garrison(name: str, x: float = 0.0, z: float = 0.0) -> dict[str, Any]:
    return {
        "name": name,
        "side": 1,  # RED
        "category": 2,  # GROUND
        "units": [{"name": name + "-u1", "type": "T-72B", "x": x, "z": z}],
    }


def _jet(name: str, x: float, z: float, airborne: bool = True) -> dict[str, Any]:
    return {
        "name": name,
        "side": 2,  # BLUE
        "category": 0,  # AIRPLANE
        "units": [
            {
                "name": name + "-u1",
                "type": "F-16C",
                "x": x,
                "z": z,
                "airborne": airborne,
            }
        ],
    }


def _harness(groups: list[str], grace: int = 5, poll: int = 10) -> DcsPluginHarness:
    h = DcsPluginHarness()
    h.lua.globals().dcsRetribution = h.to_lua(
        {
            "plugins": {"aisleep": {"startGraceS": grace, "pollIntervalS": poll}},
            "aiSleep": {"groups": groups},
        }
    )
    return h


def _ai_calls(h: DcsPluginHarness) -> list[dict[str, Any]]:
    return h.records("aiOnOff")


def test_sleeps_after_grace_and_wakes_when_an_aircraft_closes() -> None:
    h = _harness(["Garrison-A"])
    h.add_group(_garrison("Garrison-A"))
    h.load_plugin_script(PLUGIN)

    # Nothing happens during the grace.
    h.advance_to(4)
    assert _ai_calls(h) == []

    # First pass, empty sky: the garrison sleeps.
    h.advance_to(6)
    calls = _ai_calls(h)
    assert [(c["group"], c["on"]) for c in calls] == [("Garrison-A", False)]

    # A jet closes inside the wake radius -> the next poll wakes the group.
    h.add_group(_jet("Viper", x=WAKE_M * 0.5, z=0.0))
    h.advance_to(16)
    calls = _ai_calls(h)
    assert [(c["group"], c["on"]) for c in calls] == [
        ("Garrison-A", False),
        ("Garrison-A", True),
    ]
    h.assert_no_lua_errors()


def test_a_parked_aircraft_never_wakes_a_group() -> None:
    h = _harness(["Garrison-B"])
    h.add_group(_garrison("Garrison-B"))
    # On the ramp right next door, but not airborne.
    h.add_group(_jet("ColdStart", x=1000.0, z=0.0, airborne=False))
    h.load_plugin_script(PLUGIN)

    h.advance_to(30)
    calls = _ai_calls(h)
    # The garrison sleeps (empty *sky*) and stays asleep.
    assert [(c["group"], c["on"]) for c in calls] == [("Garrison-B", False)]
    h.assert_no_lua_errors()


def test_hysteresis_band_never_flaps_the_controller() -> None:
    h = _harness(["Garrison-C"])
    h.add_group(_garrison("Garrison-C"))
    # Between the wake radius and the 1.25x sleep boundary: too far to wake,
    # too close to (re-)sleep.
    h.add_group(_jet("Boundary", x=WAKE_M * 1.1, z=0.0))
    h.load_plugin_script(PLUGIN)

    # Awake at start and inside the sleep boundary -> stays awake, no calls at all.
    h.advance_to(60)
    assert _ai_calls(h) == []
    h.assert_no_lua_errors()


def test_a_hit_wakes_a_sleeping_group_immediately() -> None:
    h = _harness(["Garrison-D"])
    h.add_group(_garrison("Garrison-D"))
    h.load_plugin_script(PLUGIN)

    # Asleep after the first pass.
    h.advance_to(6)
    assert [(c["group"], c["on"]) for c in _ai_calls(h)] == [("Garrison-D", False)]

    # A standoff hit from far beyond the wake radius: wake NOW, not at the next poll.
    h.fire_hit("Garrison-D")
    calls = _ai_calls(h)
    assert [(c["group"], c["on"]) for c in calls] == [
        ("Garrison-D", False),
        ("Garrison-D", True),
    ]
    h.assert_no_lua_errors()


def test_dead_group_is_dropped_and_polling_stops() -> None:
    h = _harness(["Ghost-Garrison"])
    # Never added to the world -> Group.getByName returns nil.
    h.load_plugin_script(PLUGIN)
    h.advance_to(600)
    assert _ai_calls(h) == []
    # The poll loop returned nil once everything managed was gone.
    assert h.pending_scheduled() == 0
    h.assert_no_lua_errors()


def test_no_node_is_a_clean_noop() -> None:
    h = DcsPluginHarness()
    h.lua.globals().dcsRetribution = h.to_lua({"plugins": {}})
    h.add_group(_garrison("Garrison-E"))
    h.load_plugin_script(PLUGIN)
    h.advance_to(600)
    assert _ai_calls(h) == []
    h.assert_no_lua_errors()
