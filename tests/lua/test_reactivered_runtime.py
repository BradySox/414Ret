"""Headless runtime check for the reactive-red plugin (§89 P5).

Pins the positive-list contract and the silent-failure class: a listed
objective's unit death launches exactly ONE listed alert flight after the
tasking delay; the orbit task is pushed only once the flight is airborne, at
the objective's position; a second death at the same objective never launches
again (one-shot); an unlisted death does nothing; the fragged pool is the hard
cap; a mission with nothing emitted is a clean no-op.
"""

from __future__ import annotations

from typing import Any

from tests.lua.harness import DcsPluginHarness

PLUGIN = "resources/plugins/reactivered/reactivered-config.lua"


def _config(
    objectives: list[dict[str, Any]], groups: list[str], delay: int = 60
) -> dict[str, Any]:
    return {
        "plugins": {"reactivered": {"reactionDelaySec": delay, "orbitAltM": 5000}},
        "reactiveRed": {"objectives": objectives, "groups": groups},
    }


def _objective(
    name: str = "Haina SAM",
    units: list[str] | None = None,
    x: float = 10000.0,
    y: float = 20000.0,
) -> dict[str, Any]:
    return {
        "name": name,
        "units": units or ["0044 | SA-6 LN", "0045 | SA-6 STR"],
        "x": str(x),
        "y": str(y),
    }


def _setup(h: DcsPluginHarness, groups: int = 1) -> None:
    # The struck red site's units (any registered units work for fireDead).
    h.add_group(
        {
            "name": "Haina SAM site",
            "side": 1,
            "category": 2,
            "units": [
                {"name": "0044 | SA-6 LN", "x": 10000.0, "z": 20000.0},
                {"name": "0045 | SA-6 STR", "x": 10010.0, "z": 20010.0},
            ],
        }
    )
    for index in range(groups):
        h.add_group(
            {
                "name": f"REACT {index + 1}",
                "side": 1,
                "category": 0,
                "exists": False,  # parked late-activation until activate()
                "units": [
                    {
                        "name": f"REACT {index + 1}-1",
                        "x": 50000.0,
                        "z": 60000.0,
                        "alt": 100.0,
                        "airborne": False,
                    }
                ],
            }
        )


def test_listed_death_launches_one_alert_and_orbits_when_airborne() -> None:
    h = DcsPluginHarness()
    _setup(h)
    h.lua.globals().dcsRetribution = h.to_lua(_config([_objective()], ["REACT 1"]))
    h.load_plugin_script(PLUGIN)

    h.fire_dead("0044 | SA-6 LN")
    h.advance_to(59)
    assert h.records("activations") == []
    h.advance_to(61)
    assert h.records("activations") == ["REACT 1"]

    # Still on the ground: the first airborne poll pushes nothing.
    h.advance_to(80)
    assert h.records("controllerTasks") == []

    # Airborne: the next poll pushes the orbit at the objective.
    h.update_unit("REACT 1", {"airborne": True})
    h.advance_to(120)
    tasks = h.records("controllerTasks")
    assert len(tasks) == 1
    assert tasks[0]["group"] == "REACT 1"
    assert tasks[0]["taskId"] == "Orbit"
    assert tasks[0]["x"] == 10000.0 and tasks[0]["y"] == 20000.0
    h.assert_no_lua_errors()


def test_one_reaction_per_objective() -> None:
    h = DcsPluginHarness()
    _setup(h, groups=2)
    h.lua.globals().dcsRetribution = h.to_lua(
        _config([_objective()], ["REACT 1", "REACT 2"])
    )
    h.load_plugin_script(PLUGIN)

    h.fire_dead("0044 | SA-6 LN")
    h.fire_dead("0045 | SA-6 STR")
    h.advance_to(120)
    assert h.records("activations") == ["REACT 1"]
    h.assert_no_lua_errors()


def test_pool_is_the_hard_cap() -> None:
    h = DcsPluginHarness()
    _setup(h)
    second = _objective("Depot", ["0090 | Ammo dump"], 30000.0, 40000.0)
    h.add_group(
        {
            "name": "Depot site",
            "side": 1,
            "category": 2,
            "units": [{"name": "0090 | Ammo dump", "x": 30000.0, "z": 40000.0}],
        }
    )
    h.lua.globals().dcsRetribution = h.to_lua(
        _config([_objective(), second], ["REACT 1"])
    )
    h.load_plugin_script(PLUGIN)

    h.fire_dead("0044 | SA-6 LN")
    h.advance_to(70)
    h.fire_dead("0090 | Ammo dump")
    h.advance_to(200)
    # Pool of one: the second objective's launch logs exhaustion, no crash.
    assert h.records("activations") == ["REACT 1"]
    h.assert_no_lua_errors()


def test_unlisted_death_does_nothing() -> None:
    h = DcsPluginHarness()
    _setup(h)
    h.add_group(
        {
            "name": "Bystander",
            "side": 1,
            "category": 2,
            "units": [{"name": "0777 | Truck", "x": 1.0, "z": 2.0}],
        }
    )
    h.lua.globals().dcsRetribution = h.to_lua(_config([_objective()], ["REACT 1"]))
    h.load_plugin_script(PLUGIN)

    h.fire_dead("0777 | Truck")
    h.advance_to(300)
    assert h.records("activations") == []
    h.assert_no_lua_errors()


def test_nothing_emitted_is_a_clean_noop() -> None:
    h = DcsPluginHarness()
    h.lua.globals().dcsRetribution = h.to_lua({"plugins": {"reactivered": {}}})
    h.load_plugin_script(PLUGIN)
    h.advance_to(600)
    assert h.records("activations") == []
    assert h.pending_scheduled() == 0
    h.assert_no_lua_errors()
