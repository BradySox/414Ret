"""bigeye-config.lua: the coalition sensor toggles reach INTEL:SetDetectionTypes.

The "BLUE/RED has datalink/RWR/IRST" plugin options were a silent no-op: the main
script configured the MOOSE Ops.INTEL fusion at load with bare (nil) globals, and
the config file set ``EWR.*HasDLINK`` afterward but never re-applied the detection
types -- so flipping the UI checkbox changed nothing. The fix re-calls
``SetDetectionTypes`` from the config once the coalition sensor values are set.

The full 847-line main script needs a MOOSE Ops.INTEL facade the harness does not
carry, so this pins the *fix's* contract directly: load ONLY the config against
recording ``blueIntel``/``redIntel`` stubs and assert the configured
datalink/RWR/IRST booleans flow into the SetDetectionTypes call.
"""

from __future__ import annotations

from typing import Any

from .harness import DcsPluginHarness

CONFIG = "resources/plugins/bigeye/bigeye-config.lua"

# INTEL:SetDetectionTypes(DetectVisual, DetectOptical, DetectRadar,
#                         DetectIRST, DetectRWR, DetectDLINK)
_RECORDER = """
_detrec = {}
local function mk(name)
    return {
        SetDetectionTypes = function(self, visual, optical, radar, irst, rwr, dlink)
            _detrec[name] = {
                visual = visual, optical = optical, radar = radar,
                irst = irst, rwr = rwr, dlink = dlink,
            }
        end,
    }
end
EWR = {}
blueIntel = mk("blue")
redIntel = mk("red")
"""

_FULL_OPTIONS: dict[str, Any] = {
    "displayMessageTime": 10,
    "highReportFrequencyPreference": 15,
    "defaultReportFrequencyPreference": 30,
    "lowReportFrequencyPreference": 60,
    "gciReportFrequency": 5,
    "defaultEnableReportPreference": True,
    "maxReportUnits": 5,
    "isAvailableNCTR": True,
    "reportUnitNameNATO": True,
    # the sensor toggles under test:
    "blueHasDLINK": False,
    "blueHasRWR": True,
    "blueHasIRST": False,
    "redHasDLINK": False,
    "redHasRWR": False,
    "redHasIRST": False,
}


def _run(sensor_overrides: dict[str, Any]) -> dict[str, Any]:
    harness = DcsPluginHarness()
    options = {**_FULL_OPTIONS, **sensor_overrides}
    harness.set_retribution_config(plugin_options={"bigeye": options})
    harness.lua.execute(_RECORDER)
    harness.load_plugin_script(CONFIG)
    harness.assert_no_lua_errors()
    return harness.to_python(harness.lua.eval("_detrec"))


def test_default_sensor_options_reach_detection_types() -> None:
    rec = _run({})
    # Visual/Optical/Radar are always on; the sensor toggles flow through verbatim.
    assert rec["blue"] == {
        "visual": True,
        "optical": True,
        "radar": True,
        "irst": False,
        "rwr": True,
        "dlink": False,
    }
    assert rec["red"]["rwr"] is False
    assert rec["red"]["dlink"] is False


def test_blue_datalink_toggle_flows_through() -> None:
    # The exact bug reported: "BLUE has datalink" must reach the fusion engine.
    rec = _run({"blueHasDLINK": True})
    assert rec["blue"]["dlink"] is True


def test_every_sensor_toggle_flows_through() -> None:
    rec = _run(
        {
            "blueHasDLINK": True,
            "blueHasRWR": False,
            "blueHasIRST": True,
            "redHasDLINK": True,
            "redHasRWR": True,
            "redHasIRST": True,
        }
    )
    assert rec["blue"]["dlink"] is True
    assert rec["blue"]["rwr"] is False
    assert rec["blue"]["irst"] is True
    assert rec["red"]["dlink"] is True
    assert rec["red"]["rwr"] is True
    assert rec["red"]["irst"] is True
