"""Headless checks of the AI-crewed package-rescue-helo dispatch (2026-07-30 fix).

Flown-test finding: a player fragged a full recovery package (CH-47 rescue helo +
AH-1W Sandy + C-130 King) and flew the King himself, leaving the CH-47 AI-crewed.
With ``autoSpawn`` off (a rescue-capable helo WAS fragged) the only rescue path was
the geometry pickup -- which merely DETECTS a helo a human already flew low+slow onto
the survivor, and never ROUTES the AI helo. The CH-47 flew its planned CSAR orbit and
never approached the pilot (Tacview: never closer than 23 km).

The fix actively commandeers an AI-crewed rescue helo from ``cfg.rescueHelos`` and
flies the proven OPSTRANSPORT pickup, even with ``autoSpawn`` off. A PLAYER-crewed
rescue helo is left alone (the human flies it; the geometry path credits it).

These run the REAL plugin under Lua 5.1 with a MOOSE/DCS stub sandbox that records the
commandeer (FLIGHTGROUP creation + AddOpsTransport) and assert the DECISION: an
AI-crewed helo is commandeered, a player-crewed one is not. The actual flying +
delivery still ride the in-game pass.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import lupa.lua51 as lua51

PLUGIN = (
    Path(__file__).resolve().parents[2]
    / "resources/plugins/combatsar/combatsar-config.lua"
)

# A richer sandbox than the ledger test: GROUP:FindByName resolves configurable helo
# groups (with a player-name field per group so groupHasPlayer works), plus the MOOSE
# transport stack (FLIGHTGROUP / OPSTRANSPORT / AIRBASE / ZONE_GROUP), coalition
# airbases, and a mutable clock so the dispatch grace can elapse.
_SANDBOX = """
_infos = {}
_warnings = {}
_messages = {}
_commandeered = {}   -- helo group name -> true when FLIGHTGROUP:New wraps it
_now = 0
env = {
    info = function(m) table.insert(_infos, m) end,
    warning = function(m) table.insert(_warnings, m) end,
}
coalition = {
    side = { BLUE = 2, RED = 1 },
    getAirbases = function(side)
        local ab = { getName = function() return "Home Field" end,
                     getPoint = function() return { x = 0, y = 0, z = 0 } end }
        return { ab }
    end,
}
country = { id = { CJTF_RED = 82, CJTF_BLUE = 80 } }
world = {
    event = { S_EVENT_EJECTION = 6 },
    addEventHandler = function(h) _ejectHandler = h end,
}
timer = {
    getTime = function() return _now end,
    scheduleFunction = function(fn, arg, t)
        _scheduled = _scheduled or {}
        table.insert(_scheduled, { fn = fn, arg = arg, t = t })
    end,
}
trigger = {
    smokeColor = { Red = 1 },
    action = {
        smoke = function() end,
        outTextForCoalition = function(side, text) table.insert(_messages, text) end,
    },
}
mist = { dynAdd = function(g) return { name = g.name } end }
land = {
    getSurfaceType = function() return 1 end,
    SurfaceType = { WATER = 3, SHALLOW_WATER = 2 },
}
AI = {
    Option = {
        Ground = {
            id = { ROE = 0, ALARM_STATE = 9 },
            val = { ROE = { WEAPON_HOLD = 4 }, ALARM_STATE = { GREEN = 1 } },
        },
        Air = { id = { ROE = 0 }, val = { ROE = { WEAPON_FREE = 0 } } },
    },
}
Group = {
    Category = { GROUND = 2 },
    getByName = function(name)
        local g = { name = name }
        function g:isExist() return true end
        function g:getController()
            return { setOption = function() end }
        end
        return g
    end,
}
local chain = { __index = function(t, k) return function(...) return t end end }
SET_GROUP = setmetatable({}, chain)
EVENTS = { Birth = 1, PlayerEnterAircraft = 2, PlayerEnterUnit = 3 }
EVENTHANDLER = { New = function() return setmetatable({}, chain) end }

-- Configurable helo groups. _helos[name] = { player = bool }. FindByName returns a
-- MOOSE-GROUP-like object; anything not registered is nil (no such group).
_helos = {}
local function _mkHeloGroup(name)
    local g = { name = name }
    function g:GetName() return self.name end
    function g:IsAlive() return true end
    function g:StartUncontrolled() end
    function g:GetCoordinate()
        local c = {}
        function c:Get2DDistance(o) return 1000 end
        function c:GetVec2() return { x = 0, y = 0 } end
        function c:GetVec3() return { x = 0, y = 0, z = 0 } end
        return c
    end
    local unit = {}
    function unit:IsAlive() return true end
    function unit:GetCoordinate() return g:GetCoordinate() end
    function unit:GetPlayerName()
        local cfg = _helos[name]
        if cfg and cfg.player then return "SomePlayer" end
        return nil
    end
    function g:GetUnit(i) return unit end
    function g:GetUnits() return { unit } end
    return g
end
GROUP = {
    FindByName = function(_, name)
        if _helos[name] then return _mkHeloGroup(name) end
        return nil
    end,
}
AIRBASE = { FindByName = function(_, name)
    local a = { name = name }
    function a:GetZone() return { zone = true } end
    return a
end }
ZONE_GROUP = { New = function() return { zone = true } end }
OPSTRANSPORT = { New = function() return { transport = true } end }
FLIGHTGROUP = {
    New = function(_, grp)
        _commandeered[grp:GetName()] = true
        local fg = {}
        function fg:SetHomebase() end
        function fg:SetDefaultAltitude() end
        function fg:SetDefaultSpeed() end
        function fg:AddOpsTransport() end
        function fg:Activate() end
        return fg
    end,
}
SPAWN = {
    NewWithAlias = function(_, template, alias)
        local s = {}
        function s:InitDelayOff() return self end
        function s:InitUnControlled() return self end
        function s:SpawnFromCoordinate(coord)
            local unit = {}
            function unit:IsAlive() return true end
            function unit:GetCoordinate() return coord end
            local g = { name = alias }
            function g:GetName() return self.name end
            function g:IsAlive() return true end
            function g:GetUnit(i) return unit end
            function g:GetUnits() return { unit } end
            function g:GetCoordinate() return coord end
            function g:Destroy() end
            return g
        end
        return s
    end,
}
COORDINATE = {
    NewFromVec2 = function(_, v)
        local c = { x = v.x, y = v.y }
        function c:GetVec2() return { x = self.x, y = self.y } end
        function c:GetVec3() return { x = self.x, y = 0, z = self.y } end
        function c:Translate(dist, bearing) return COORDINATE:NewFromVec2({ x = self.x, y = self.y }) end
        function c:Get2DDistance(o) return 1000 end
        return c
    end,
}
function COORDINATE.NewFromVec3(_, p) return COORDINATE:NewFromVec2({ x = p.x, y = p.z }) end
function _mkUnit(name, side, x, y)
    return {
        getName = function() return name end,
        getCoalition = function() return side end,
        getPosition = function() return { p = { x = x, y = 0, z = y } } end,
    }
end
dirty_state = false
_scheduled = {}
"""


def _run(data: dict[str, Any], helos: dict[str, bool]) -> Any:
    rt = lua51.LuaRuntime(unpack_returned_tuples=False)
    rt.execute(_SANDBOX)
    # Register the helo groups the sandbox's FindByName should resolve.
    for name, is_player in helos.items():
        rt.execute(
            f'_helos["{name}"] = {{ player = {"true" if is_player else "false"} }}'
        )

    def to_lua(value: Any) -> Any:
        if isinstance(value, dict):
            table = rt.table()
            for key, item in value.items():
                table[key] = to_lua(item)
            return table
        if isinstance(value, (list, tuple)):
            table = rt.table()
            for index, item in enumerate(value, start=1):
                table[index] = to_lua(item)
            return table
        return value

    rt.globals().dcsRetribution = to_lua(
        {"CombatSAR": data, "plugins": {"combatsar": {}}}
    )
    rt.execute(PLUGIN.read_text(encoding="utf-8"))
    return rt


def _eject_then_run_ticks(rt: Any) -> None:
    # A blue pilot ejects, then the clock is advanced past the dispatch grace (60 s)
    # and every scheduled tick is fired a few times so the dispatch block runs.
    rt.execute(
        "_ejectHandler:onEvent({ id = 6, "
        'initiator = _mkUnit("Enfield 1-1 | F-14B", 2, 0, 0) })'
    )
    rt.execute("_now = 120")
    rt.execute("for _ = 1, 3 do for _, s in ipairs(_scheduled) do s.fn(s.arg) end end")


HELO = "Recovery: Jason Rogers Combat SAR|2|28|CH-47D|"


def test_ai_crewed_package_helo_is_commandeered_with_autospawn_off() -> None:
    rt = _run(
        {
            "pilotTemplate": "Combat SAR Downed Pilot",
            "autoSpawn": "false",
            "rescueHelos": [HELO],
        },
        helos={HELO: False},  # AI-crewed
    )
    _eject_then_run_ticks(rt)
    assert bool(rt.eval(f'_commandeered["{HELO}"]')), rt.eval(
        'table.concat(_warnings, "\\n")'
    )
    messages = [m for m in str(rt.eval('table.concat(_messages, "\\n")')).splitlines()]
    assert any("inbound to pick up" in m for m in messages), messages


def test_player_crewed_package_helo_is_left_for_the_human() -> None:
    rt = _run(
        {
            "pilotTemplate": "Combat SAR Downed Pilot",
            "autoSpawn": "false",
            "rescueHelos": [HELO],
        },
        helos={HELO: True},  # player-crewed
    )
    _eject_then_run_ticks(rt)
    # Never commandeer a helo a human is flying -- the geometry pickup path handles it.
    assert not rt.eval(f'_commandeered["{HELO}"]')
    messages = [m for m in str(rt.eval('table.concat(_messages, "\\n")')).splitlines()]
    assert not any("inbound to pick up" in m for m in messages), messages
