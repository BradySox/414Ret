"""Headless runtime check for the blue voice net plugin (§89 P4).

Pins the delivery contract and the silent-failure class: a scheduled call keys
one non-looped clip from its LIVE group's position at the schedule time on the
emitted frequency; a dead or absent transmitter is silence (never a fallback
point, never an error); the subtitle option mirrors the call text to blue; an
early schedule time clamps to the 5 s floor; a mission with no emitted net is
a clean no-op.
"""

from __future__ import annotations

from typing import Any

from tests.lua.harness import DcsPluginHarness

PLUGIN = "resources/plugins/battlespacenet/battlespacenet-config.lua"


def _config(
    calls: list[dict[str, Any]], power: int = 250, subtitles: int = 0
) -> dict[str, Any]:
    return {
        "plugins": {"battlespacenet": {"powerW": power, "showSubtitles": subtitles}},
        "battlespaceNet": {"calls": calls},
    }


def _call(
    t: str = "30",
    group: str = "HAMMER 1",
    mhz: str = "251.0",
    file: str = "l10n/DEFAULT/bsnet_000.wav",
    text: str = "Magic, Hammer 1 1, airborne as fragged.",
) -> dict[str, Any]:
    return {"t": t, "group": group, "mhz": mhz, "file": file, "text": text}


def _hammer_group(h: DcsPluginHarness, exists: bool = True) -> None:
    h.add_group(
        {
            "name": "HAMMER 1",
            "side": 2,
            "category": 0,
            "exists": exists,
            "units": [{"name": "HAMMER 1-1", "x": 1234.0, "z": 5678.0, "alt": 800.0}],
        }
    )


def test_call_keys_once_from_the_live_group_at_schedule_time() -> None:
    h = DcsPluginHarness()
    _hammer_group(h)
    h.lua.globals().dcsRetribution = h.to_lua(_config([_call()]))
    h.load_plugin_script(PLUGIN)

    h.advance_to(29)
    assert h.records("radioTransmissions") == []

    h.advance_to(30)
    tx = h.records("radioTransmissions")
    assert len(tx) == 1
    assert tx[0]["hz"] == 251.0e6
    assert tx[0]["file"] == "l10n/DEFAULT/bsnet_000.wav"
    assert tx[0]["loop"] is False
    assert tx[0]["mod"] == 0
    assert tx[0]["power"] == 250
    assert tx[0]["x"] == 1234.0 and tx[0]["z"] == 5678.0

    # One-shot: nothing recurs and nothing needs stopping.
    h.advance_to(600)
    assert len(h.records("radioTransmissions")) == 1
    assert h.records("stoppedTransmissions") == []
    h.assert_no_lua_errors()


def test_absent_and_dead_transmitters_are_silence() -> None:
    h = DcsPluginHarness()
    # "GHOST 1" is never registered; "HAMMER 1" exists=False (shot down).
    _hammer_group(h, exists=False)
    h.lua.globals().dcsRetribution = h.to_lua(
        _config([_call(group="GHOST 1"), _call(t="40")])
    )
    h.load_plugin_script(PLUGIN)

    h.advance_to(600)
    assert h.records("radioTransmissions") == []
    h.assert_no_lua_errors()


def test_subtitle_option_mirrors_the_call_text() -> None:
    h = DcsPluginHarness()
    _hammer_group(h)
    h.lua.globals().dcsRetribution = h.to_lua(_config([_call()], subtitles=1))
    h.load_plugin_script(PLUGIN)

    h.advance_to(30)
    texts = h.records("texts")
    assert len(texts) == 1
    assert texts[0]["text"] == "Magic, Hammer 1 1, airborne as fragged."
    h.assert_no_lua_errors()


def test_no_subtitles_by_default() -> None:
    h = DcsPluginHarness()
    _hammer_group(h)
    h.lua.globals().dcsRetribution = h.to_lua(_config([_call()]))
    h.load_plugin_script(PLUGIN)

    h.advance_to(30)
    assert h.records("texts") == []
    h.assert_no_lua_errors()


def test_early_schedule_time_clamps_to_the_floor() -> None:
    h = DcsPluginHarness()
    _hammer_group(h)
    h.lua.globals().dcsRetribution = h.to_lua(_config([_call(t="1")]))
    h.load_plugin_script(PLUGIN)

    h.advance_to(4)
    assert h.records("radioTransmissions") == []
    h.advance_to(6)
    assert len(h.records("radioTransmissions")) == 1
    h.assert_no_lua_errors()


def test_no_emitted_net_is_a_clean_noop() -> None:
    h = DcsPluginHarness()
    h.lua.globals().dcsRetribution = h.to_lua({"plugins": {"battlespacenet": {}}})
    h.load_plugin_script(PLUGIN)
    h.advance_to(600)
    assert h.records("radioTransmissions") == []
    assert h.pending_scheduled() == 0
    h.assert_no_lua_errors()
