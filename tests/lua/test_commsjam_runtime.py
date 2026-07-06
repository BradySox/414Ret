"""Headless runtime check for the comms-jamming plugin (commsjam-config.lua).

Pins the safety invariants and the "script errors and the feature silently never
starts" class: nothing transmits during the startup grace; a burst steps on at
most maxFreqsPerBurst channels, loops the noise file at the right Hz from the
jammer's position, and is stopped after burstSec; the channel window rotates so
every briefed freq gets its turn; a positively-dead jammer (dead_events ledger
or an existed-and-destroyed static) never transmits -- with the "jamming has
ceased" cue only if jamming had already been announced; and a mission with no
commsJam node is a clean no-op.
"""

from __future__ import annotations

from typing import Any

from tests.lua.harness import DcsPluginHarness

PLUGIN = "resources/plugins/commsjam/commsjam-config.lua"

_OPTIONS = {
    "commsjam": {
        "startGraceS": 10,
        "burstSec": 5,
        "intervalSec": 20,
        "maxFreqsPerBurst": 2,
        "powerW": 123,
    }
}

_FREQS = [
    {"mhz": "251.0", "mod": "AM"},
    {"mhz": "254.5", "mod": "AM"},
    {"mhz": "30.0", "mod": "FM"},
]


def _config(
    jammers: list[dict[str, Any]], backup: str | None = "271.0"
) -> dict[str, Any]:
    comms_jam: dict[str, Any] = {"jammers": jammers, "freqs": _FREQS}
    if backup is not None:
        comms_jam["backupMhz"] = backup
    return {"plugins": _OPTIONS, "commsJam": comms_jam}


def _jammer(name: str = "C2", units: list[str] | None = None) -> dict[str, Any]:
    return {
        "name": name,
        "units": units or ["0012 | Comms Tower"],
        "x": "1000.0",
        "y": "2000.0",
    }


def _tx(h: DcsPluginHarness) -> list[dict[str, Any]]:
    return h.records("radioTransmissions")


def test_bursts_after_grace_then_stops_and_rotates_channels() -> None:
    h = DcsPluginHarness()
    h.lua.globals().dcsRetribution = h.to_lua(_config([_jammer()]))
    h.load_plugin_script(PLUGIN)

    # Silence during the grace.
    h.advance_to(9)
    assert _tx(h) == []

    # First burst: 2 of the 3 channels, looped noise from the jammer position.
    h.advance_to(10)
    first = _tx(h)
    assert len(first) == 2
    assert [t["hz"] for t in first] == [251.0e6, 254.5e6]
    assert all(t["file"].endswith("commsjam-noise.wav") for t in first)
    assert all(t["loop"] for t in first)
    assert all(t["power"] == 123 for t in first)
    assert all(t["x"] == 1000.0 and t["z"] == 2000.0 for t in first)
    # AM channels carry modulation 0.
    assert all(t["mod"] == 0 for t in first)

    # The burst is stopped after burstSec.
    h.advance_to(15)
    stopped = h.records("stoppedTransmissions")
    assert sorted(stopped) == sorted(t["name"] for t in first)

    # The window rotates: the next cycle leads with the FM channel, then wraps.
    h.advance_to(120)
    tx = _tx(h)
    assert len(tx) >= 4
    assert [t["hz"] for t in tx[:4]] == [251.0e6, 254.5e6, 30.0e6, 251.0e6]
    assert tx[2]["mod"] == 1  # the 30.0 MHz channel is FM

    # The first burst announced the jamming, with the backup channel in the cue.
    texts = [t["text"] for t in h.records("texts")]
    assert any("COMMS JAMMING" in t and "271.000 MHz" in t for t in texts)
    h.assert_no_lua_errors()


def test_dead_jammer_never_transmits() -> None:
    h = DcsPluginHarness()
    h.lua.globals().dcsRetribution = h.to_lua(_config([_jammer()]))
    # Killed before the first burst: recorded in the dead_events ledger with the
    # "id | " prefix stripped, like Retribution's BDA path records scenery.
    h.lua.globals().dead_events = h.to_lua(["Comms Tower"])
    h.load_plugin_script(PLUGIN)

    h.advance_to(600)
    assert _tx(h) == []
    # Never announced, so no "ceased" cue either.
    assert h.records("texts") == []
    h.assert_no_lua_errors()


def test_destroyed_static_counts_as_dead() -> None:
    h = DcsPluginHarness()
    h.lua.globals().dcsRetribution = h.to_lua(_config([_jammer()]))
    # The placed static exists in the miz but no longer :isExist().
    h.add_static({"name": "0012 | Comms Tower object", "exists": False})
    h.load_plugin_script(PLUGIN)

    h.advance_to(600)
    assert _tx(h) == []
    h.assert_no_lua_errors()


def test_killing_the_last_jammer_silences_and_announces_ceased() -> None:
    h = DcsPluginHarness()
    h.lua.globals().dcsRetribution = h.to_lua(_config([_jammer()]))
    h.load_plugin_script(PLUGIN)

    h.advance_to(10)
    assert len(_tx(h)) == 2

    # Killed after the first burst.
    h.lua.globals().dead_events = h.to_lua(["0012 | Comms Tower"])
    h.advance_to(600)
    assert len(_tx(h)) == 2  # no further bursts
    texts = [t["text"] for t in h.records("texts")]
    assert any("jamming has ceased" in t for t in texts)
    h.assert_no_lua_errors()


def test_no_node_is_a_clean_noop() -> None:
    h = DcsPluginHarness()
    h.lua.globals().dcsRetribution = h.to_lua({"plugins": {}})
    h.load_plugin_script(PLUGIN)
    h.advance_to(600)
    assert _tx(h) == []
    assert h.pending_scheduled() == 0
    h.assert_no_lua_errors()
