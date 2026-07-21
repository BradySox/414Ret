"""Headless runtime check for the convoy-ambush plugin (convoyambush-config.lua).

Pins the "script errors and the feature silently never starts" invariant and the spring
logic: an ambush springs (a BLUE cue + an F10 mark) when its convoy closes inside the
trigger radius; a team whose convoy never closes (or that has no convoy at all) stays dug
in and SILENT -- the ambush must remain a surprise, never a telegraphed fight; a team
wiped before it springs never fires; and a mission with no convoyAmbush node is a clean
no-op.

ROE calls are pcall-swallowed by design (the harness stubs no controller/AI), so the
observable spring is the recorded text cue + mark, not the ROE change.
"""

from __future__ import annotations

from typing import Any

from tests.lua.harness import DcsPluginHarness

PLUGIN = "resources/plugins/convoyambush/convoyambush-config.lua"


def _team(name: str) -> dict[str, Any]:
    return {
        "name": name,
        "side": 1,  # RED
        "category": 2,  # GROUND
        "units": [{"name": name + "-u1", "type": "Infantry", "x": 1000.0, "z": 2000.0}],
    }


def _convoy(name: str, x: float, z: float) -> dict[str, Any]:
    return {
        "name": name,
        "side": 2,  # BLUE
        "category": 2,  # GROUND
        "units": [{"name": name + "-u1", "type": "M113", "x": x, "z": z}],
    }


def _config(*, ambushes: list[dict[str, Any]], **options: Any) -> dict[str, Any]:
    return {
        "plugins": {"convoyambush": options},
        "convoyAmbush": {"ambushes": ambushes},
    }


def test_springs_when_the_convoy_closes() -> None:
    h = DcsPluginHarness()
    h.add_group(_team("Ambush-1"))
    # Convoy sits right on the ambush centre -> inside any radius.
    h.add_group(_convoy("Convoy-1", 1000.0, 2000.0))
    h.lua.globals().dcsRetribution = h.to_lua(
        _config(
            ambushes=[
                {
                    "groups": ["Ambush-1"],
                    "x": "1000.0",
                    "y": "2000.0",
                    "convoyGroups": ["Convoy-1"],
                }
            ],
            startGraceS=5,
            pollIntervalS=5,
            triggerRadiusNm=3.24,  # ~6000 m
        )
    )
    h.load_plugin_script(PLUGIN)

    # Nothing springs during the grace.
    h.advance_to(4)
    assert h.records("texts") == []
    assert h.records("marks") == []

    # First poll after the grace: the convoy is in range -> spring (cue + mark).
    h.advance_to(6)
    texts = h.records("texts")
    marks = h.records("marks")
    assert len(texts) == 1
    assert texts[0]["side"] == 2  # BLUE
    assert "ambush" in texts[0]["text"].lower()
    assert len(marks) == 1
    assert marks[0]["x"] == 1000.0 and marks[0]["z"] == 2000.0
    h.assert_no_lua_errors()


def test_does_not_spring_while_the_convoy_is_far() -> None:
    h = DcsPluginHarness()
    h.add_group(_team("Ambush-1"))
    h.add_group(_convoy("Convoy-1", 500000.0, 500000.0))  # far outside the radius
    h.lua.globals().dcsRetribution = h.to_lua(
        _config(
            ambushes=[
                {
                    "groups": ["Ambush-1"],
                    "x": "1000.0",
                    "y": "2000.0",
                    "convoyGroups": ["Convoy-1"],
                }
            ],
            startGraceS=5,
            pollIntervalS=5,
            triggerRadiusNm=3.24,  # ~6000 m
        )
    )
    h.load_plugin_script(PLUGIN)
    h.advance_to(3600)
    # An hour on: the convoy never closed, so the team is still dug in and silent --
    # there is no time-based fallback that would telegraph an ambush nobody drove into.
    assert h.records("texts") == []
    assert h.records("marks") == []
    h.assert_no_lua_errors()


def test_stays_silent_without_a_convoy() -> None:
    h = DcsPluginHarness()
    h.add_group(_team("Ambush-1"))
    # No convoy group exists at all (e.g. it was destroyed before it ever spawned).
    h.lua.globals().dcsRetribution = h.to_lua(
        _config(
            ambushes=[{"groups": ["Ambush-1"], "x": "1000.0", "y": "2000.0"}],
            startGraceS=5,
            pollIntervalS=5,
        )
    )
    h.load_plugin_script(PLUGIN)
    h.advance_to(3600)
    assert h.records("texts") == []
    assert h.records("marks") == []
    h.assert_no_lua_errors()


def test_dead_team_never_springs() -> None:
    h = DcsPluginHarness()
    # The ambush group is never added -> aliveGroups() finds nothing.
    h.add_group(_convoy("Convoy-1", 1000.0, 2000.0))
    h.lua.globals().dcsRetribution = h.to_lua(
        _config(
            ambushes=[
                {
                    "groups": ["Ghost-Ambush"],
                    "x": "1000.0",
                    "y": "2000.0",
                    "convoyGroups": ["Convoy-1"],
                }
            ],
            startGraceS=5,
        )
    )
    h.load_plugin_script(PLUGIN)
    h.advance_to(600)
    assert h.records("texts") == []
    assert h.records("marks") == []
    h.assert_no_lua_errors()


def test_no_node_is_a_clean_noop() -> None:
    h = DcsPluginHarness()
    h.lua.globals().dcsRetribution = h.to_lua({"plugins": {}})
    h.load_plugin_script(PLUGIN)
    h.advance_to(600)
    assert h.records("texts") == []
    h.assert_no_lua_errors()
