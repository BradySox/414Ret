"""Intercept (QRA): the detection-prefix escape (upstream PR #782 drift).

Runs the real ``resources/plugins/intercept/intercept-config.lua`` against the
harness with a recording fake of the MOOSE surface it touches (the bundled
Moose.lua models real DCS AI and cannot run headless). Pins the FilterPrefixes
gotcha the lua-lint syntax gate cannot:

* Moose ``SET_GROUP:FilterPrefixes`` matches names with Lua-pattern semantics
  (``string.find``, only ``-`` pre-escaped), so a raw parenthesized Retribution
  group name ("0041 | LION (EWR)") reads as a pattern capture and never matches
  its own group — the wide-area EWR half of QRA detection was empty (masked by
  the paren-free ``QRA_Backstop_*`` names);
* the FULL merged detection list — IADS EWR network AND backstop names — is
  escaped before it reaches ``FilterPrefixes``.

What the fake cannot model: Moose's real detection cycle and the scramble
itself — that is the in-game pass (checklist A5).
"""

from __future__ import annotations

from typing import Any

from tests.lua.harness import REPO_ROOT, DcsPluginHarness

PLUGIN = "resources/plugins/intercept/intercept-config.lua"

BUILD_DELAY_S = 5  # intercept-config.lua BUILD_DELAY; the dispatcher builds then

#: Real Retribution IADS group-name shapes: every one carries "(" / ")".
PAREN_NAMES = [
    "0041 | LION (EWR)",
    "0035 | ELEPHANT (Naval Two Ship)",
    "0114 | LORIKEET (S-300)",
    "0178 | OPOSSUM (Patriot)",
]

# A recording fake of the MOOSE classes intercept-config.lua touches at load
# and during the deferred dispatcher build. SET_GROUP records the prefixes it
# was given; AI_A2A_DISPATCHER records tuning calls and keeps live
# EvaluateGCI/EvaluateENGAGE originals so the plugin's per-instance wrap (the
# react-task filter) can be exercised. mist.dynAdd registers the backstop EWR
# as a real harness group so the build's existence check passes.
MOOSE_FAKE = """
InterceptTest = { filterPrefixes = nil, dispatchers = {} }

DETECTION_MANAGER = {}
function DETECTION_MANAGER:MessageToPlayers(Squadron, Message, DefenderGroup) end

BASE = {}
function BASE:CreateEventTakeoff(EventTime, Initiator) end

ZONE_RADIUS = {}
function ZONE_RADIUS:New(name, vec2, radius, doNotRegister)
    return { name = name, radius = radius }
end

SET_GROUP = {}
function SET_GROUP:New()
    local obj = {}
    function obj:FilterCoalitions(c)
        self.coalitions = c
        return self
    end
    function obj:FilterPrefixes(prefixes)
        InterceptTest.filterPrefixes = prefixes
        return self
    end
    function obj:FilterStart()
        return self
    end
    return obj
end

DETECTION_AREAS = {}
function DETECTION_AREAS:New(set, radius)
    return { set = set, radius = radius }
end

AI_A2A_DISPATCHER = {}
function AI_A2A_DISPATCHER:New(detection)
    local obj = { detection = detection, DefenderSquadrons = {}, gciCalls = {}, engageCalls = {} }
    function obj:SetDefaultTakeoffInAir() end
    function obj:SetDefaultTakeoffInAirAltitude(alt) end
    function obj:SetDefaultLandingAtEngineShutdown() end
    function obj:SetIntercept(delay) end
    function obj:SetEngageRadius(radius) end
    function obj:SetTacticalDisplay(onoff) end
    function obj:SetGciRadius(radius) end
    function obj:SetBorderZone(zones) end
    function obj:SetDisengageRadius(radius) end
    function obj:SetDefaultFuelThreshold(threshold, time) end
    function obj:SetSendMessages(onoff) end
    function obj:SetSquadron(name, base, templates, count)
        self.DefenderSquadrons[name] = { Spawn = {} }
    end
    function obj:SetSquadronGci(name, minSpeed, maxSpeed) end
    function obj:SetSquadronTakeoffInAirAltitude(name, alt) end
    function obj:SetSquadronGrouping(name, n) end
    function obj:SetSquadronLanguage(name, lang) end
    function obj:EvaluateGCI(item)
        table.insert(self.gciCalls, item)
        return "defenders-missing", "friendlies"
    end
    function obj:EvaluateENGAGE(item)
        table.insert(self.engageCalls, item)
        return "friendlies"
    end
    table.insert(InterceptTest.dispatchers, obj)
    return obj
end

mist = {}
function mist.scheduleFunction(fn, vars, t)
    return timer.scheduleFunction(function()
        return fn(unpack(vars or {}))
    end, {}, t)
end
function mist.dynAdd(spec)
    -- Register the spawned backstop EWR as a real harness group so the build's
    -- GROUP:FindByName existence check sees it.
    local units = {}
    for _, u in ipairs(spec.units or {}) do
        units[#units + 1] = { name = u.name, type = u.type, x = u.x, z = u.y }
    end
    DcsHarness.addGroup({
        name = spec.groupName,
        side = coalition.side.BLUE,
        category = Group.Category.GROUND,
        units = units,
    })
end

-- protect_group calls these on the freshly spawned backstop; the harness
-- MooseGroup metatable (shared by every GROUP:FindByName result) lacks them.
do
    DcsHarness.addGroup({ name = "__metatable_probe__", side = 0, category = 2, units = {} })
    local mt = getmetatable(GROUP:FindByName("__metatable_probe__"))
    mt.SetCommandInvisible = function() end
    mt.SetCommandImmortal = function() end
end

-- Moose SET_GROUP:FilterPrefixes matcher (Moose.lua): string.find with the
-- prefix as a Lua PATTERN, only "-" pre-escaped. What an escaped prefix must
-- survive to land its group in the detection set.
function InterceptTest.mooseMatches(name, prefix)
    return string.find(name, (prefix:gsub("%-", "%%-")), 1) ~= nil
end
"""


def _intercept_record(airbase: str, squadron_id: str) -> dict[str, str]:
    """One dcsRetribution.Intercept record (add_key_value emits all strings)."""
    return {
        "squadronId": squadron_id,
        "squadronName": "Test Squadron",
        "airbaseName": airbase,
        "templatePrefix": f"Intercept|{airbase}|{squadron_id}",
        "coalition": "BLUE",
        "resourceCount": "2",
        "grouping": "2",
        "engagementRangeNm": "38",
        "gciMaxRadiusNm": "60",
        "commsEnabled": "false",
        "countryId": "2",
        "backstopEwrType": "FPS-117",
        "ambushPosture": "false",
        "disengageRadiusNm": "0",
    }


def _load(harness: DcsPluginHarness, ewr_names: list[str]) -> Any:
    """Load the real plugin with one BLUE alert base and the given EWR net."""
    harness.add_airbase({"name": "Test AFB", "x": 0.0, "z": 0.0, "elev": 100.0})
    for name in ewr_names:
        harness.add_group(
            {
                "name": name,
                "side": harness.side.BLUE,
                "category": harness.category.GROUND,
                "units": [{"name": f"{name} radar", "type": "FPS-117"}],
            }
        )
    harness.set_retribution_config(plugin_options={})
    config = harness.lua.globals().dcsRetribution
    config.Intercept = harness.to_lua({"BLUE": [_intercept_record("Test AFB", "sq-1")]})
    config.IADS = harness.to_lua(
        {"BLUE": {"Ewr": [{"dcsGroupName": name} for name in ewr_names]}}
    )
    harness.lua.execute(MOOSE_FAKE)
    script = (REPO_ROOT / PLUGIN).read_text(encoding="utf-8")
    # The chunk's return value is the plugin's test hook (inert in DCS, which
    # discards it); harness.load_plugin_script would throw it away.
    return harness.lua.execute(script)


def test_escaped_prefix_matches_where_raw_fails() -> None:
    """A parenthesized group name survives the escape and matches itself."""
    harness = DcsPluginHarness()
    module = _load(harness, ewr_names=list(PAREN_NAMES))
    matches = harness.lua.globals().InterceptTest.mooseMatches
    for name in PAREN_NAMES:
        # Raw prefix: "(" / ")" read as pattern captures -> never matches.
        assert not matches(name, name), f"raw prefix unexpectedly matched: {name}"
        # Escaped prefix: matches its literal group name.
        assert matches(name, module.pattern_escape(name)), f"no match: {name}"


def test_full_merged_detection_list_is_escaped() -> None:
    """FilterPrefixes receives the escaped EWR network AND the backstop name."""
    harness = DcsPluginHarness()
    _load(harness, ewr_names=["0041 | LION (EWR)", "0114 | LORIKEET (S-300)"])
    harness.advance_to(BUILD_DELAY_S + 1)
    harness.assert_no_lua_errors()

    prefixes = harness.to_python(harness.lua.globals().InterceptTest.filterPrefixes)
    assert prefixes == [
        "0041 | LION %(EWR%)",
        "0114 | LORIKEET %(S-300%)",  # "-" stays raw for Moose's own gsub
        "QRA_Backstop_BLUE_Test AFB",
    ]


def test_escape_leaves_dash_for_moose() -> None:
    """ "-" must stay raw: Moose's own FilterPrefixes gsub escapes it (escaping
    here would double-escape and break the match)."""
    harness = DcsPluginHarness()
    module = _load(harness, ewr_names=list(PAREN_NAMES))
    assert (
        module.pattern_escape("0114 | LORIKEET (S-300)") == "0114 | LORIKEET %(S-300%)"
    )
