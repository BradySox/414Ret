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
        "captureReactionS": 40,
    }
}

# The capture-watch poll cadence is a plugin constant (CAPTURE_POLL), not an option.
CAPTURE_POLL = 30

_FREQS = [
    {"mhz": "251.0", "mod": "AM"},
    {"mhz": "254.5", "mod": "AM"},
    {"mhz": "30.0", "mod": "FM"},
]


def _config(
    jammers: list[dict[str, Any]],
    backup: str | None = "271.0",
    capture_only: bool = False,
    active_from_start: bool = True,
) -> dict[str, Any]:
    comms_jam: dict[str, Any] = {
        "jammers": jammers,
        "freqs": _FREQS,
        # The emitter serializes booleans as strings; mirror that.
        "captureOnly": "true" if capture_only else "false",
        "activeFromStart": "true" if active_from_start else "false",
    }
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


def test_max_channels_caps_to_the_top_priority_channels() -> None:
    # maxChannels concentrates the jamming: with a cap of 1, only the FIRST
    # (highest-priority) briefed channel is ever stepped on -- the window can't
    # rotate onto the others because they're truncated away. The generator emits
    # the list human-flights-then-AWACS-first, so "first" == "most important".
    import copy

    h = DcsPluginHarness()
    cfg = _config([_jammer()])
    cfg["plugins"] = copy.deepcopy(cfg["plugins"])
    cfg["plugins"]["commsjam"]["maxChannels"] = 1
    h.lua.globals().dcsRetribution = h.to_lua(cfg)
    h.load_plugin_script(PLUGIN)

    # Run well past several rotation cycles (grace 10, burst 5, interval ~20).
    h.advance_to(400)
    jammed = {t["hz"] for t in _tx(h)}
    assert jammed == {251.0e6}, jammed  # 254.5 and 30.0 stay clean
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


def test_intel_gate_stays_dormant_without_a_capture() -> None:
    h = DcsPluginHarness()
    h.lua.globals().dcsRetribution = h.to_lua(
        _config([_jammer()], capture_only=True, active_from_start=False)
    )
    h.load_plugin_script(PLUGIN)

    h.advance_to(900)
    assert _tx(h) == []
    assert h.records("texts") == []
    h.assert_no_lua_errors()


def test_intel_gate_ignores_red_captures() -> None:
    h = DcsPluginHarness()
    h.lua.globals().dcsRetribution = h.to_lua(
        _config([_jammer()], capture_only=True, active_from_start=False)
    )
    h.load_plugin_script(PLUGIN)
    h.lua.globals().combat_sar_captures = h.to_lua(
        [{"unit": "MiG-21", "x": 0, "y": 0, "coalition": "red"}]
    )
    h.advance_to(900)
    assert _tx(h) == []
    h.assert_no_lua_errors()


def test_live_capture_cues_then_jams_after_the_exploitation_delay() -> None:
    h = DcsPluginHarness()
    h.lua.globals().dcsRetribution = h.to_lua(
        _config([_jammer()], capture_only=True, active_from_start=False)
    )
    h.load_plugin_script(PLUGIN)

    # Combat SAR records a blue capture at t=25 -- the watch (30 s cadence)
    # sees it on its first tick.
    h.advance_to(25)
    h.lua.globals().combat_sar_captures = h.to_lua(
        [{"unit": "Colt 1-1", "x": 1.0, "y": 2.0, "coalition": "blue"}]
    )
    h.advance_to(CAPTURE_POLL)
    texts = [t["text"] for t in h.records("texts")]
    assert any("AIRCREW CAPTURED" in t and "271.000 MHz" in t for t in texts)
    assert _tx(h) == []  # cue first; jamming waits out the exploitation delay

    # First burst at capture-detection (30) + captureReactionS (40) = 70.
    h.advance_to(69)
    assert _tx(h) == []
    h.advance_to(70)
    assert len(_tx(h)) == 2
    # No second "first burst" announcement -- the capture cue was it.
    texts = [t["text"] for t in h.records("texts")]
    assert len([t for t in texts if "271.000 MHz" in t]) == 1
    h.assert_no_lua_errors()


def test_pow_compromise_jams_from_the_grace_with_the_pow_story() -> None:
    h = DcsPluginHarness()
    h.lua.globals().dcsRetribution = h.to_lua(
        _config([_jammer()], capture_only=True, active_from_start=True)
    )
    h.load_plugin_script(PLUGIN)

    h.advance_to(10)
    assert len(_tx(h)) == 2
    texts = [t["text"] for t in h.records("texts")]
    assert any("COMMS COMPROMISED" in t and "captured aircrew" in t for t in texts)
    h.assert_no_lua_errors()


def test_intel_gate_watch_stops_when_the_c2_net_dies() -> None:
    h = DcsPluginHarness()
    h.lua.globals().dcsRetribution = h.to_lua(
        _config([_jammer()], capture_only=True, active_from_start=False)
    )
    h.lua.globals().dead_events = h.to_lua(["0012 | Comms Tower"])
    h.load_plugin_script(PLUGIN)

    h.advance_to(CAPTURE_POLL)
    assert h.pending_scheduled() == 0  # the watch bailed: nothing left to transmit
    h.assert_no_lua_errors()


def test_no_node_is_a_clean_noop() -> None:
    h = DcsPluginHarness()
    h.lua.globals().dcsRetribution = h.to_lua({"plugins": {}})
    h.load_plugin_script(PLUGIN)
    h.advance_to(600)
    assert _tx(h) == []
    assert h.pending_scheduled() == 0
    h.assert_no_lua_errors()
