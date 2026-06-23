-- luacheck configuration for the 414th DCS Lua plugins.
--
-- Target runtime is DCS World's Lua 5.1 (LuaJIT) server sandbox. This config
-- powers the *advisory* luacheck job in .github/workflows/lua-lint.yml. The
-- BLOCKING gate in that workflow is `luac5.1 -p` (pure syntax) over every
-- plugin file; luacheck adds typo / undefined-global detection on top, scoped
-- to the 414th-authored scripts only (vendored MOOSE/CTLD/Skynet/etc. would
-- drown the signal). Tune the ignore list as real warnings surface — keep it
-- low-noise so the output stays trusted rather than reflexively skipped.

std = "lua51"
max_line_length = false
codes = true

-- DCS plugin scripts assign module-level globals freely and read a large host
-- API; don't flag every top-level definition as an accidental global.
allow_defined = true
allow_defined_top = true

-- Quiet the high-noise, low-signal warnings so that the things we actually
-- care about (syntax slips, undefined/typo'd calls) stand out.
ignore = {
    "211", -- unused local variable
    "212", -- unused argument
    "213", -- unused loop variable
    "311", -- value assigned to a local is never used (overwritten)
    "542", -- empty if branch
    "631", -- line too long (belt-and-suspenders with max_line_length=false)
}

-- Mutable globals shared across plugin scripts at runtime (written, not just
-- read) — e.g. the TARS bridge table the init script appends capture rows to.
globals = {
    "tars_recon_captures",
}

read_globals = {
    -- DCS World scripting API (server-side sandbox; no os/io/lfs)
    "env", "timer", "trigger", "coalition", "country", "world", "land",
    "atmosphere", "coord", "missionCommands", "radio", "net", "Controller",
    "Unit", "Group", "StaticObject", "Object", "Airbase", "Weapon", "Spot",
    "AI", "Warehouse", "VoiceChat", "SceneryObject", "CoalitionObject",

    -- Retribution generator bridge table (emitted into the .miz by the planner)
    "dcsRetribution",

    -- MOOSE framework surface (bundled base/Moose.lua)
    "BASE", "GROUP", "UNIT", "STATIC", "AIRBASE", "COORDINATE", "POINT_VEC2",
    "POINT_VEC3", "ZONE", "ZONE_RADIUS", "ZONE_POLYGON", "SET_GROUP",
    "SET_UNIT", "SET_STATIC", "SET_CLIENT", "SPAWN", "SCHEDULER", "MESSAGE",
    "MENU_MISSION", "MENU_MISSION_COMMAND", "MENU_COALITION",
    "MENU_COALITION_COMMAND", "MENU_GROUP", "MENU_GROUP_COMMAND", "CLIENT",
    "DETECTION_AREAS", "FLIGHTCONTROL", "AI_A2A_DISPATCHER", "DESIGNATE",
    "SETTINGS", "TARS", "Ops", "UTILS", "routines", "mist",

    -- Plugin-defined globals the 414th init scripts probe before using
    "GLSCO", "GLSCO_COMBATANT", "GLSCO_BATTLEFIELD",
}
