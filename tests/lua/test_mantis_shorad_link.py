"""MANTIS bridge: the SEAD-triggered point-defense (SHORAD) link.

Runs the real ``resources/plugins/mantisiads/mantis-config.lua`` against the
harness with a recording fake of the MOOSE ``MANTIS``/``SHORAD`` classes (the
bundled Moose.lua models real DCS AI and cannot run headless). Pins the
bridge-side plumbing the lua-lint syntax gate cannot:

* the per-SAM ``PD`` connection arrays are collected and DEDUPED into one
  SHORAD object per coalition, built with Lua-pattern-escaped prefixes (the
  same ``FilterPrefixes`` gotcha as the SAM/EWR sets — an unescaped
  ``"... (PD)"`` name never matches its own group);
* ``mantis.autoshorad`` goes false before Start so MANTIS' own auto-SHORAD
  cannot overwrite the linked object (the MOOSE ``onafterStart`` ordering);
* no PD groups / ``shoradLink=false`` leave MANTIS' defaults untouched.

What the fake cannot model: SHORAD's real sleep/wake AI, HARM shot events and
the intercept itself — that is the in-game pass (checklist G30).
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.lua.harness import DcsPluginHarness

PLUGIN = "resources/plugins/mantisiads/mantis-config.lua"

# A recording fake of the two MOOSE classes the bridge touches. MANTIS:New
# returns an object that records tuning calls; SHORAD:New records its args.
MOOSE_FAKE = """
MantisTest = { mantis = {}, shorad = {}, addshorad = {} }

MANTIS = {
    SamType = { LONG = "LONG", MEDIUM = "MEDIUM", SHORT = "SHORT", POINT = "POINT" },
    radiusscale = {},
}
function MANTIS._GetSAMRange(self, grpname) return 0, 0, "POINT", 0 end
function MANTIS:New(name, samprefixes, ewrprefixes, hq, coa, dynamic, awacs, emonoff)
    local obj = {
        name = name,
        coalition = coa,
        autoshorad = true,   -- the MOOSE default the bridge must flip
        ShoradActDistance = 25000,
        SAM_Group = { CountAlive = function() return 0 end },
        EWR_Group = { CountAlive = function() return 0 end },
    }
    function obj:SetSAMRange(...) end
    function obj:SetDetectInterval(...) end
    function obj:SetEWRGrouping(...) end
    function obj:SetMaxActiveSAMs(...) end
    function obj:SetAutoRelocate(...) end
    function obj:Debug(...) end
    function obj:Start()
        self.started = true
        -- capture the flag AT Start time: MOOSE's onafterStart overwrites the
        -- linked SHORAD unless autoshorad is already false by this point
        self.autoshorad_at_start = self.autoshorad
    end
    function obj:AddShorad(shorad, time)
        table.insert(MantisTest.addshorad,
            { mantis = self.name, shorad = shorad.name, time = time })
    end
    table.insert(MantisTest.mantis, obj)
    return obj
end

SHORAD = {}
function SHORAD:New(name, prefixes, samset, radius, activetimer, coa, emonoff)
    local obj = {
        name = name, prefixes = prefixes, samset = samset,
        radius = radius, activetimer = activetimer, coalition = coa,
    }
    table.insert(MantisTest.shorad, obj)
    return obj
end
"""


def _load(
    harness: DcsPluginHarness,
    iads: dict[str, Any],
    plugin_options: dict[str, Any] | None = None,
) -> None:
    harness.set_retribution_config(plugin_options={"mantisiads": plugin_options or {}})
    harness.lua.globals().dcsRetribution.IADS = harness.to_lua(iads)
    harness.lua.execute(MOOSE_FAKE)
    harness.load_plugin_script(PLUGIN)


def _mantis_objects(harness: DcsPluginHarness) -> list[dict[str, Any]]:
    out = []
    test = harness.lua.globals().MantisTest
    for obj in test.mantis.values():
        out.append(
            {
                "name": obj.name,
                "coalition": obj.coalition,
                "autoshorad": obj.autoshorad,
                "autoshorad_at_start": obj.autoshorad_at_start,
                "act_distance": obj.ShoradActDistance,
                "started": obj.started,
            }
        )
    return out


def _shorad_objects(harness: DcsPluginHarness) -> list[dict[str, Any]]:
    out = []
    test = harness.lua.globals().MantisTest
    for obj in test.shorad.values():
        out.append(
            {
                "name": obj.name,
                "prefixes": harness.to_python(obj.prefixes),
                "radius": obj.radius,
                "activetimer": obj.activetimer,
                "coalition": obj.coalition,
                "has_samset": obj.samset is not None,
            }
        )
    return out


RED_IADS_WITH_PD = {
    "RED": {
        "Sam": [
            {
                "dcsGroupName": "0146 | KILO (SAM)",
                # two SAMs share one PD group: must dedupe to a single prefix
                "PD": ["0146 | KILO (PD)"],
            },
            {
                "dcsGroupName": "0147 | LIMA (SAM)",
                "PD": ["0146 | KILO (PD)", "0147 | LIMA (PD)"],
            },
        ],
        "SamAsEwr": [
            {
                "dcsGroupName": "0148 | MIKE (SAM)",
                "PD": ["0148 | MIKE (PD)"],
            }
        ],
        "Ewr": [{"dcsGroupName": "0149 | EWR NOVEMBER"}],
    },
    "BLUE": {},
}


def test_pd_groups_build_one_linked_shorad_per_coalition() -> None:
    harness = DcsPluginHarness()
    _load(harness, RED_IADS_WITH_PD)
    harness.assert_no_lua_errors()

    shorads = _shorad_objects(harness)
    assert len(shorads) == 1, "one SHORAD for RED, none for the empty BLUE"
    shorad = shorads[0]
    assert shorad["coalition"] == "red"
    assert shorad["has_samset"], "SHORAD must defend MANTIS' own SAM set"
    # 3 deduped PD names, each Lua-pattern escaped so "(PD)" matches literally
    assert len(shorad["prefixes"]) == 3
    assert "0146 | KILO %(PD%)" in shorad["prefixes"]
    assert "0147 | LIMA %(PD%)" in shorad["prefixes"]
    assert "0148 | MIKE %(PD%)" in shorad["prefixes"]
    # defaults: 10.8 NM defense radius, 600 s wake
    assert shorad["radius"] == pytest.approx(10.8 * 1852)
    assert shorad["activetimer"] == 600

    mantis = _mantis_objects(harness)
    red = next(m for m in mantis if m["coalition"] == "red")
    assert red["autoshorad"] is False
    assert red["autoshorad_at_start"] is False, (
        "autoshorad must be disabled BEFORE Start or MOOSE overwrites the "
        "linked SHORAD in onafterStart"
    )
    assert red["act_distance"] == pytest.approx(13.5 * 1852)
    assert red["started"] is True

    test = harness.lua.globals().MantisTest
    linked = harness.to_python(test.addshorad)
    assert len(linked) == 1
    assert linked[0]["shorad"] == shorad["name"]
    assert linked[0]["time"] == 600


def test_no_pd_groups_leaves_mantis_defaults_untouched() -> None:
    harness = DcsPluginHarness()
    _load(
        harness,
        {
            "RED": {
                "Sam": [{"dcsGroupName": "0146 | KILO (SAM)"}],
                "Ewr": [{"dcsGroupName": "0149 | EWR NOVEMBER"}],
            },
            "BLUE": {},
        },
    )
    harness.assert_no_lua_errors()
    assert _shorad_objects(harness) == []
    red = next(m for m in _mantis_objects(harness) if m["coalition"] == "red")
    assert red["autoshorad"] is True, "no PD => MANTIS' own default behavior"


def test_shorad_link_option_off_restores_old_behavior() -> None:
    harness = DcsPluginHarness()
    _load(harness, RED_IADS_WITH_PD, plugin_options={"shoradLink": False})
    harness.assert_no_lua_errors()
    assert _shorad_objects(harness) == []
    red = next(m for m in _mantis_objects(harness) if m["coalition"] == "red")
    assert red["autoshorad"] is True


def test_wake_options_thread_through() -> None:
    harness = DcsPluginHarness()
    _load(
        harness,
        RED_IADS_WITH_PD,
        plugin_options={
            "shoradTime": 300,
            "shoradRadiusNm": 5.4,
            "shoradActDistanceNm": 8.1,
        },
    )
    harness.assert_no_lua_errors()
    shorad = _shorad_objects(harness)[0]
    assert shorad["radius"] == pytest.approx(5.4 * 1852)
    assert shorad["activetimer"] == 300
    red = next(m for m in _mantis_objects(harness) if m["coalition"] == "red")
    assert red["act_distance"] == pytest.approx(8.1 * 1852)
    test = harness.lua.globals().MantisTest
    assert harness.to_python(test.addshorad)[0]["time"] == 300
