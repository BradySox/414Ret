"""Headless runtime check for the base plugin's ejection bookkeeping.

`ejection_events` is how a downed pilot reaches the campaign: the ejection
records the aircraft's position, and the parachute landing that follows refines
it to where the pilot actually came down. The landing carries no unit name, so it
has to be matched back to an ejection.

The match used to be "the most recent ejection without a landing". DCS fires one
landing per crew member, so a two-seat crew touching down wrote its second
landing onto whichever other survivor had none -- test 30 (2026-09-13, Persian
Gulf) recorded an AV-8B pilot who came down in the Strait of Hormuz as landed
170 km away beside an F-4E's crash. The landing is now matched to the nearest
open ejection within `LANDING_MATCH_M`, and a landing that matches nothing is
dropped.

The script's file-scope side effects (MIST logger, state-file discovery, the
event registration) run against the stubs below; nothing here models DCS.
"""

from __future__ import annotations

from typing import Any

from tests.lua.harness import DcsPluginHarness

PLUGIN = "resources/plugins/base/dcs_retribution.lua"

# What dcs_retribution.lua touches at file scope beyond the harness's DCS surface:
# MIST's logger/scheduler/event registration, the json library, and the state-file
# path probe. `os`/`lfs` are removed so the probe finds no folder and never opens
# a file on the developer's machine.
_PRELUDE = """
os = nil
lfs = nil
json = { encode = function(_, t) return "{}" end }
mist = {
    Logger = { new = function() return {
        info = function() end, warn = function() end, error = function() end,
    } end },
    message = { add = function() end },
    scheduleFunction = function() end,
    addEventHandler = function(fn)
        world.addEventHandler({ onEvent = function(_, e) return fn(e) end })
    end,
    getHeading = function() return 0 end,
    DBs = {},
}
"""


def _load() -> DcsPluginHarness:
    harness = DcsPluginHarness()
    harness.lua.execute(_PRELUDE)
    harness.load_plugin_script(PLUGIN)
    harness.assert_no_lua_errors()
    return harness


def _eject(harness: DcsPluginHarness, unit: str, x: float, z: float) -> None:
    initiator = harness.lua.eval(
        "function(n, x, z) return {"
        "  getName = function(self) return n end,"
        "  getPosition = function(self) return { p = { x = x, y = 0, z = z } } end,"
        "} end"
    )(unit, x, z)
    harness.fire_event({"id": 6, "initiator": initiator})
    harness.assert_no_lua_errors()


def _land(harness: DcsPluginHarness, x: float, z: float) -> None:
    initiator = harness.lua.eval(
        "function(x, z) return {"
        "  getPoint = function(self) return { x = x, y = 0, z = z } end,"
        "} end"
    )(x, z)
    harness.fire_event({"id": 31, "initiator": initiator})
    harness.assert_no_lua_errors()


def _ejections(harness: DcsPluginHarness) -> dict[str, dict[str, Any]]:
    raw = harness.to_python(harness.lua.eval("ejection_events"))
    assert isinstance(raw, list)
    return {str(e["unit"]): e for e in raw}


def test_the_script_loads_without_erroring() -> None:
    harness = _load()
    assert harness.to_python(harness.lua.eval("LANDING_MATCH_M")) == 20000


def test_a_landing_refines_the_ejection_it_is_nearest_to() -> None:
    harness = _load()
    _eject(harness, "Harrier-1", 0.0, 0.0)
    _eject(harness, "Harrier-2", 1800.0, 0.0)

    # The lead's chute comes down first, closer to the lead's ejection point
    # than to the wingman's, even though the wingman ejected last.
    _land(harness, 300.0, -100.0)

    events = _ejections(harness)
    assert events["Harrier-1"]["landed"] is True
    assert events["Harrier-1"]["x"] == 300.0
    assert events["Harrier-1"]["z"] == -100.0
    assert "landed" not in events["Harrier-2"]
    assert events["Harrier-2"]["x"] == 1800.0


def test_a_second_crew_member_landing_does_not_move_another_survivor() -> None:
    harness = _load()
    _eject(harness, "Harrier-4", -60040.0, 159481.0)
    _eject(harness, "Phantom-1", 110519.0, 120.0)

    # Both Phantom crew land beside the Phantom's crash. The second landing has
    # no open ejection within reach and must not be written onto the Harrier.
    _land(harness, 110433.0, -161.0)
    _land(harness, 110389.0, -76.0)

    events = _ejections(harness)
    assert events["Phantom-1"]["landed"] is True
    assert events["Phantom-1"]["x"] == 110433.0
    assert "landed" not in events["Harrier-4"]
    assert events["Harrier-4"]["x"] == -60040.0
    assert events["Harrier-4"]["z"] == 159481.0


def test_a_landing_with_no_ejection_in_reach_is_dropped() -> None:
    harness = _load()
    _eject(harness, "Hornet-1", 0.0, 0.0)

    _land(harness, 50000.0, 0.0)

    events = _ejections(harness)
    assert "landed" not in events["Hornet-1"]
    assert events["Hornet-1"]["x"] == 0.0


def test_an_ejection_without_a_position_never_claims_a_landing() -> None:
    harness = _load()
    initiator = harness.lua.eval(
        "function() return { getName = function(self) return 'Blind-1' end } end"
    )()
    harness.fire_event({"id": 6, "initiator": initiator})
    harness.assert_no_lua_errors()
    _eject(harness, "Hornet-1", 500.0, 500.0)

    _land(harness, 600.0, 400.0)

    events = _ejections(harness)
    assert "x" not in events["Blind-1"]
    assert "landed" not in events["Blind-1"]
    assert events["Hornet-1"]["landed"] is True
