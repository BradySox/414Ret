"""Headless checks of the combatsar ALWAYS-RUN survivor ledger (2026-07-10).

The flown 2026-07-10 test caught the plugin bailing out entirely whenever no
rescue asset existed (auto-CSAR off + a Sandy-only package): no snatch party ever
spawned, so the capture -> POW -> comms-jam chain could never fire. The rework
runs the ledger whenever the node exists -- rescue capability only shapes the
messaging. These run the REAL plugin script under Lua 5.1 with a small MOOSE/DCS
stub sandbox and assert:

* a config with NO rescue assets still starts the ledger ("capture race only"),
* an ejection registers a survivor, mirrors it into ``combat_sar_survivors``
  (the persistent-evader state), and spawns the enemy snatch party,
* ``persistentSurvivors`` (evaders from an earlier mission) re-spawn at start.

The stubs model no DCS AI/physics -- rescue/capture *outcomes* still ride the
in-game pass.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import lupa.lua51 as lua51

PLUGIN = (
    Path(__file__).resolve().parents[2]
    / "resources/plugins/combatsar/combatsar-config.lua"
)

# A minimal DCS + MOOSE sandbox: chainable no-op sets, spawn/coordinate stubs that
# carry positions, capture hooks for scheduled functions, the eject handler, output
# messages, and mist.dynAdd (the snatch-party spawn). Everything the plugin touches
# at file scope and on the eject -> first-tick path.
_SANDBOX = """
_infos = {}
_warnings = {}
_messages = {}
_snatches = {}
_scheduled = {}
env = {
    info = function(m) table.insert(_infos, m) end,
    warning = function(m) table.insert(_warnings, m) end,
}
coalition = { side = { BLUE = 2, RED = 1 } }
country = { id = { CJTF_RED = 82, CJTF_BLUE = 80 } }
world = {
    event = { S_EVENT_EJECTION = 6 },
    addEventHandler = function(h) _ejectHandler = h end,
}
timer = {
    getTime = function() return 0 end,
    scheduleFunction = function(fn, arg, t)
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
mist = {
    dynAdd = function(g)
        table.insert(_snatches, g)
        return { name = g.name }
    end,
}
land = {
    getSurfaceType = function() return 1 end,  -- LAND
    SurfaceType = { WATER = 3, SHALLOW_WATER = 2 },
}
Group = { Category = { GROUND = 2 } }  -- the DCS class (distinct from MOOSE GROUP)
-- Chainable no-op: every method returns the table itself (SET_GROUP:New()
-- :FilterCoalitions():FilterCategoryHelicopter():FilterStart(), ForEachGroupAlive...).
local chain = { __index = function(t, k) return function(...) return t end end }
SET_GROUP = setmetatable({}, chain)
EVENTS = { Birth = 1, PlayerEnterAircraft = 2, PlayerEnterUnit = 3 }
EVENTHANDLER = { New = function() return setmetatable({}, chain) end }
GROUP = { FindByName = function() return nil end }
COORDINATE = {
    NewFromVec2 = function(_, v)
        local c = { x = v.x, y = v.y }
        function c:GetVec2() return { x = self.x, y = self.y } end
        function c:GetVec3() return { x = self.x, y = 0, z = self.y } end
        function c:Translate(dist, bearing)
            return COORDINATE:NewFromVec2({ x = self.x + dist, y = self.y })
        end
        function c:Get2DDistance(other) return 999999 end
        return c
    end,
}
function COORDINATE.NewFromVec3(_, p)
    return COORDINATE:NewFromVec2({ x = p.x, y = p.z })
end
SPAWN = {
    NewWithAlias = function(_, template, alias)
        local s = {}
        function s:InitDelayOff() return self end
        function s:SpawnFromCoordinate(coord)
            local unit = {}
            function unit:IsAlive() return true end
            function unit:GetCoordinate() return coord end
            local g = { name = alias }
            function g:GetName() return self.name end
            function g:IsAlive() return true end
            function g:GetUnit(i) return unit end
            function g:GetUnits() return { unit } end
            function g:Destroy() end
            return g
        end
        return s
    end,
}
function _mkUnit(name, side, x, y)
    return {
        getName = function() return name end,
        getCoalition = function() return side end,
        getPosition = function() return { p = { x = x, y = 0, z = y } } end,
    }
end
dirty_state = false
"""


def _run(data: dict[str, Any], options: dict[str, Any] | None = None) -> Any:
    rt = lua51.LuaRuntime(unpack_returned_tuples=False)
    rt.execute(_SANDBOX)

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
        {"CombatSAR": data, "plugins": {"combatsar": options or {}}}
    )
    rt.execute(PLUGIN.read_text(encoding="utf-8"))
    return rt


def _lua_list(rt: Any, expr: str) -> list[str]:
    return [
        line
        for line in str(rt.eval(f'table.concat({expr}, "\\n")')).splitlines()
        if line
    ]


def test_ledger_starts_with_no_rescue_assets_at_all() -> None:
    # auto-CSAR off, no player helo, no template: the old plugin skipped entirely
    # ("no rescue helos/template") -- now the ledger starts, capture race only.
    rt = _run({"pilotTemplate": "Combat SAR Downed Pilot", "autoSpawn": "false"})
    infos = _lua_list(rt, "_infos")
    assert any("survivor ledger started" in line for line in infos), infos
    assert any("capture race only" in line for line in infos), infos
    assert not any("skipping" in line for line in infos), infos


def test_ejection_registers_survivor_syncs_state_and_spawns_the_snatch() -> None:
    # The user's exact scenario: no rescue capability, a blue pilot ejects -> the
    # survivor registers (with the "no rescue assets" MAYDAY), mirrors into
    # combat_sar_survivors (the persistent-evader state), and the snatch party
    # spawns on the first tick (chance forced to 100 to take the roll out).
    rt = _run(
        {"pilotTemplate": "Combat SAR Downed Pilot", "autoSpawn": "false"},
        options={"captureChance": 100},
    )
    rt.execute(
        "_ejectHandler:onEvent({ id = 6, "
        'initiator = _mkUnit("Enfield 1-1 | F-14B", 2, 1000, 2000) })'
    )
    assert rt.eval("#combat_sar_survivors") == 1
    assert str(rt.eval("combat_sar_survivors[1].unit")) == "Enfield 1-1 | F-14B"
    assert rt.eval("combat_sar_survivors[1].x") == 1000
    assert rt.eval("combat_sar_survivors[1].y") == 2000
    messages = _lua_list(rt, "_messages")
    assert any("no rescue assets available" in m for m in messages), messages

    # First tick: the capture race rolls (forced 100%) and the snatch party spawns
    # on the OPPOSING country, converging on the survivor.
    rt.execute("for _, s in ipairs(_scheduled) do s.fn(s.arg) end")
    assert rt.eval("#_snatches") > 0
    assert rt.eval("_snatches[1].country") == 82
    messages = _lua_list(rt, "_messages")
    assert any("moving to capture the downed pilot" in m for m in messages), messages


def test_persistent_evaders_respawn_at_mission_start() -> None:
    rt = _run(
        {
            "pilotTemplate": "Combat SAR Downed Pilot",
            "autoSpawn": "false",
            "persistentSurvivors": [
                {"name": "Enfield 1-1 | F-14B", "x": 5000, "y": -3000}
            ],
        }
    )
    infos = _lua_list(rt, "_infos")
    assert any("persistent evader(s) will re-spawn" in line for line in infos), infos

    # Fire the scheduled spawn: the evader registers like a fresh survivor (same
    # ledger, so the same capture race + rescue paths) with the EVADER cue.
    rt.execute("for _, s in ipairs(_scheduled) do s.fn(s.arg) end")
    assert rt.eval("#combat_sar_survivors") == 1
    assert str(rt.eval("combat_sar_survivors[1].unit")) == "Enfield 1-1 | F-14B"
    messages = _lua_list(rt, "_messages")
    assert any("EVADER" in m for m in messages), messages
