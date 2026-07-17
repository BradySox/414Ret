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
  escaped before it reaches ``FilterPrefixes``;
* the task-type reaction filter: QRA reacts only to air-to-ground taskings
  parsed from the namegen group name (Strike/BAI/OCA-Runway/OCA-Aircraft/
  Anti-ship/Armed Recon — no DEAD, no Air Assault), a cluster reacts as soon
  as one member is a react type (escorted strikes still trigger), and the
  per-instance ``EvaluateGCI``/``EvaluateENGAGE`` wrap skips react-free
  clusters without touching Moose's originals.

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

-- A detected cluster the shape qra_cluster_has_react walks: a Set of units,
-- each carrying its group name.
function InterceptTest.fakeItem(groupNames)
    local units = {}
    for _, n in ipairs(groupNames) do
        local group = { GetName = function() return n end }
        units[#units + 1] = { GetGroup = function() return group end }
    end
    return {
        Set = {
            ForEachUnit = function(_, fn)
                for _, u in ipairs(units) do
                    fn(u)
                end
            end,
        },
    }
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


def test_group_reacts_only_to_air_to_ground_taskings() -> None:
    """React list: Strike/BAI/OCA-Runway/OCA-Aircraft/Anti-ship/Armed Recon.

    NO DEAD, NO Air Assault (upstream f0bd1b63's final list); CAP/sweep/escort
    and non-ATO names never react."""
    harness = DcsPluginHarness()
    module = _load(harness, ewr_names=list(PAREN_NAMES))
    reacts = module.group_reacts

    assert reacts("PKG Strike|USA|1|F-16C_50|")
    assert reacts("Al Dhafra BAI|21|2|F-15E|")
    assert reacts("Incirlik OCA/Runway|2|3|B-1B|")
    assert reacts("Incirlik OCA/Aircraft|2|4|F-16C_50|")
    assert reacts("CVN-71 Anti-ship|1|5|Su-24M|")
    assert reacts("Haina Armed Recon|1|6|A-10C|")

    assert not reacts("PKG BARCAP|USA|7|F-14B|")
    assert not reacts("PKG DEAD|USA|8|F-16C_50|")
    assert not reacts("LZ Air Assault|21|9|Mi-8MT|")
    assert not reacts("PKG Fighter sweep|USA|10|F-15C|")
    assert not reacts("PKG Escort|USA|11|F-16C_50|")
    # Non-ATO group (no namegen "|" fields) is unclassifiable -> never reacts,
    # even when coincidentally named like a task.
    assert not reacts("Eagle Strike")
    assert not reacts(None)


def test_cluster_reacts_when_any_member_is_react_type() -> None:
    """An escorted strike still triggers; a pure fighter cluster never does."""
    harness = DcsPluginHarness()
    module = _load(harness, ewr_names=list(PAREN_NAMES))
    fake_item = harness.lua.globals().InterceptTest.fakeItem

    escorted_strike = fake_item(
        harness.to_lua(["PKG Escort|USA|1|F-16C_50|", "PKG Strike|USA|2|F-15E|"])
    )
    pure_fighters = fake_item(
        harness.to_lua(["PKG Fighter sweep|USA|3|F-15C|", "PKG BARCAP|USA|4|F-14B|"])
    )
    assert module.cluster_has_react(escorted_strike)
    assert not module.cluster_has_react(pure_fighters)
    assert not module.cluster_has_react(harness.to_lua({}))


def test_dispatcher_evaluation_skips_react_free_clusters() -> None:
    """The per-instance EvaluateGCI/EvaluateENGAGE wrap: a cluster with no
    react-type group returns nil (no scramble) without touching Moose's
    original; a react cluster delegates."""
    harness = DcsPluginHarness()
    _load(harness, ewr_names=["0041 | LION (EWR)"])
    harness.advance_to(BUILD_DELAY_S + 1)
    harness.assert_no_lua_errors()

    test_globals = harness.lua.globals().InterceptTest
    dispatcher = test_globals.dispatchers[1]
    fake_item = test_globals.fakeItem

    # lupa surfaces Lua multi-returns as tuples: "nil, nil" -> (None, None).
    sweep = fake_item(harness.to_lua(["PKG Fighter sweep|USA|1|F-15C|"]))
    assert dispatcher.EvaluateGCI(dispatcher, sweep) == (None, None)
    assert dispatcher.EvaluateENGAGE(dispatcher, sweep) is None
    assert len(dispatcher.gciCalls) == 0
    assert len(dispatcher.engageCalls) == 0

    strike = fake_item(harness.to_lua(["PKG Strike|USA|2|F-15E|"]))
    assert dispatcher.EvaluateGCI(dispatcher, strike) == (
        "defenders-missing",
        "friendlies",
    )
    assert dispatcher.EvaluateENGAGE(dispatcher, strike) == "friendlies"
    assert len(dispatcher.gciCalls) == 1
    assert len(dispatcher.engageCalls) == 1
