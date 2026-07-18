"""Headless runtime check for the red-net plugin (rednet-config.lua) — §70 C1.

Pins the safety invariants and the "script errors and the feature silently
never starts" class: nothing transmits during the startup grace; per-node first
windows are staggered across one gap so nets never key up together (§49); a
window loops the CW clip (the l10n/DEFAULT path — the §58 silent-fail lesson)
at the node's frequency/position and is stopped after windowSec; windows recur;
a positively-dead node (dead_events ledger or an existed-and-destroyed static)
never transmits — and one killed mid-mission goes off the air; a mission with
no redNet node is a clean no-op.
"""

from __future__ import annotations

from typing import Any

from tests.lua.harness import DcsPluginHarness

PLUGIN = "resources/plugins/rednet/rednet-config.lua"

_OPTIONS = {
    "rednet": {
        "startGraceS": 10,
        "windowSec": 5,
        "gapSec": 20,
        "powerW": 9000,
    }
}


def _config(nodes: list[dict[str, Any]]) -> dict[str, Any]:
    return {"plugins": _OPTIONS, "redNet": {"nodes": nodes}}


def _node(
    name: str = "C2 net",
    units: list[str] | None = None,
    mhz: str = "271.5",
    x: str = "1000.0",
    y: str = "2000.0",
) -> dict[str, Any]:
    return {
        "name": name,
        "units": units or ["0012 | Comms Tower"],
        "x": x,
        "y": y,
        "mhz": mhz,
    }


def _tx(h: DcsPluginHarness) -> list[dict[str, Any]]:
    return h.records("radioTransmissions")


def test_first_window_after_grace_loops_the_cw_clip_then_stops() -> None:
    h = DcsPluginHarness()
    h.lua.globals().dcsRetribution = h.to_lua(_config([_node()]))
    h.load_plugin_script(PLUGIN)

    # Silence during the grace.
    h.advance_to(9)
    assert _tx(h) == []

    # First window: the looped CW clip at the net freq from the node position.
    h.advance_to(10)
    tx = _tx(h)
    assert len(tx) == 1
    assert tx[0]["hz"] == 271.5e6
    assert tx[0]["file"] == "l10n/DEFAULT/rednet-cw.wav"
    assert tx[0]["loop"] is True
    assert tx[0]["mod"] == 0  # the UHF net is AM
    assert tx[0]["power"] == 9000
    assert tx[0]["x"] == 1000.0 and tx[0]["z"] == 2000.0

    # The window is stopped after windowSec.
    h.advance_to(15)
    assert h.records("stoppedTransmissions") == [tx[0]["name"]]

    # Windows recur (jittered gap: 0.6x-1.4x of 20 s after the 5 s window).
    h.advance_to(120)
    assert len(_tx(h)) >= 2
    h.assert_no_lua_errors()


def test_two_nodes_are_staggered_across_one_gap() -> None:
    h = DcsPluginHarness()
    h.lua.globals().dcsRetribution = h.to_lua(
        _config(
            [
                _node("net A", units=["0001 | Mast A"], mhz="251.5"),
                _node("net B", units=["0002 | Mast B"], mhz="305.5"),
            ]
        )
    )
    h.load_plugin_script(PLUGIN)

    # Node 1 keys up at the grace; node 2 half a gap later (10 + 20/2 = 20).
    h.advance_to(10)
    assert [t["hz"] for t in _tx(h)] == [251.5e6]
    h.advance_to(19)
    assert len(_tx(h)) == 1
    h.advance_to(20)
    assert [t["hz"] for t in _tx(h)] == [251.5e6, 305.5e6]
    h.assert_no_lua_errors()


def test_dead_node_never_transmits() -> None:
    h = DcsPluginHarness()
    h.lua.globals().dcsRetribution = h.to_lua(_config([_node()]))
    # Killed before the first window: recorded in the dead_events ledger with
    # the "id | " prefix stripped, like Retribution's BDA path records scenery.
    h.lua.globals().dead_events = h.to_lua(["Comms Tower"])
    h.load_plugin_script(PLUGIN)

    h.advance_to(600)
    assert _tx(h) == []
    h.assert_no_lua_errors()


def test_destroyed_static_counts_as_dead() -> None:
    h = DcsPluginHarness()
    h.lua.globals().dcsRetribution = h.to_lua(_config([_node()]))
    # The placed static exists in the miz but no longer :isExist().
    h.add_static({"name": "0012 | Comms Tower object", "exists": False})
    h.load_plugin_script(PLUGIN)

    h.advance_to(600)
    assert _tx(h) == []
    h.assert_no_lua_errors()


def test_killing_the_node_takes_the_net_off_the_air() -> None:
    h = DcsPluginHarness()
    h.lua.globals().dcsRetribution = h.to_lua(_config([_node()]))
    h.load_plugin_script(PLUGIN)

    h.advance_to(10)
    assert len(_tx(h)) == 1

    # Killed after the first window: no further windows, no lingering schedule.
    h.lua.globals().dead_events = h.to_lua(["0012 | Comms Tower"])
    h.advance_to(600)
    assert len(_tx(h)) == 1
    assert h.pending_scheduled() == 0
    h.assert_no_lua_errors()


def test_no_node_is_a_clean_noop() -> None:
    h = DcsPluginHarness()
    h.lua.globals().dcsRetribution = h.to_lua({"plugins": {}})
    h.load_plugin_script(PLUGIN)
    h.advance_to(600)
    assert _tx(h) == []
    assert h.pending_scheduled() == 0
    h.assert_no_lua_errors()
