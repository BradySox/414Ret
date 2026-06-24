-------------------------------------------------------------------------------------------------------------------------------------------------------------
-- MIST -> MOOSE compatibility shim for DCS Retribution
--
-- Goal: retire the ~5,000-line mist_4_5_126.lua by providing the *exact* subset of
-- the `mist` API that Retribution's plugins actually call (42 distinct symbols),
-- backed by MOOSE (already loaded as the standard framework) + vanilla DCS, so the
-- consumers (CTLD, SCAR, intercept glue, core dcs_retribution.lua, Skynet) stay
-- byte-for-byte unchanged. See docs/dev/design/414th-mist-moose-shim-notes.md.
--
-- LOAD ORDER (once wired into base/plugin.json): AFTER Moose.lua, BEFORE consumers.
-- This file is NOT yet in base/plugin.json: mist_4_5_126.lua still loads and main is
-- unaffected until the validation swap (see the design doc rollout plan).
--
-- Lua 5.1 only. Define before first use. Behavior is replicated from the MIST
-- source verbatim (semantics matter -- a subtly-wrong vector/distance silently
-- breaks a consumer at runtime, not parse time).
--
-- BUILD STATUS:
--   [x] Tier 1a  vector + math utils (this file)
--   [ ] Tier 1b  geo/coord (getHeading, getAvgPos, getLeadPos, getRandPointInCircle,
--                terrainHeightDiff, tostringLL, tostringMGRS, getUnitsLOS, random,
--                utils.getDir, utils.getHeadingPoints, utils.zoneToVec3, utils.tableShow)
--   [ ] Tier 2   object DB (DBs.unitsByName/unitsById/groupsByName/zonesByName/humansByName)
--   [ ] Tier 3   spawn/route/sched (dynAdd, dynAddStatic, goRoute, getGroupRoute,
--                groupToRandomZone, ground.buildWP, makeUnitTable, scheduleFunction,
--                removeFunction, addEventHandler)
--   [ ] Tier 4   msg/log (message.add, Logger)
-------------------------------------------------------------------------------------------------------------------------------------------------------------

mist = mist or {}
mist.utils = mist.utils or {}
mist.vec = mist.vec or {}
mist.ground = mist.ground or {}
mist.DBs = mist.DBs or {}
mist.message = mist.message or {}

---------------------------------------------------------------------------------------------------
-- Tier 1a -- vectors (replicated verbatim from mist_4_5_126.lua; DCS Vec3 = {x, y, z}, y = altitude)
---------------------------------------------------------------------------------------------------

function mist.vec.sub(vec1, vec2)
    return { x = vec1.x - vec2.x, y = vec1.y - vec2.y, z = vec1.z - vec2.z }
end

function mist.vec.dp(vec1, vec2)
    return vec1.x * vec2.x + vec1.y * vec2.y + vec1.z * vec2.z
end

function mist.vec.mag(vec)
    return (vec.x ^ 2 + vec.y ^ 2 + vec.z ^ 2) ^ 0.5
end

---------------------------------------------------------------------------------------------------
-- Tier 1a -- scalar / unit conversions
---------------------------------------------------------------------------------------------------

function mist.utils.round(num, idp)
    local mult = 10 ^ (idp or 0)
    return math.floor(num * mult + 0.5) / mult
end

function mist.utils.toDegree(angle)
    return angle * 180 / math.pi
end

function mist.utils.metersToNM(meters)
    return meters / 1852
end

function mist.utils.metersToFeet(meters)
    return meters / 0.3048
end

---------------------------------------------------------------------------------------------------
-- Tier 1a -- vector constructors (note MIST's axis remap: Vec2.y carries Vec3.z)
---------------------------------------------------------------------------------------------------

function mist.utils.makeVec2(vec)
    if vec.z then
        return { x = vec.x, y = vec.z }
    else
        return { x = vec.x, y = vec.y } -- was already a Vec2
    end
end

function mist.utils.makeVec3(vec, y)
    if not vec.z then
        if vec.alt and not y then
            y = vec.alt
        elseif not y then
            y = 0
        end
        return { x = vec.x, y = y, z = vec.y }
    else
        return { x = vec.x, y = vec.y, z = vec.z } -- was already a Vec3
    end
end

---------------------------------------------------------------------------------------------------
-- Tier 1a -- distances (defined after makeVec3 / vec.mag, which they use)
---------------------------------------------------------------------------------------------------

function mist.utils.get2DDist(point1, point2)
    point1 = mist.utils.makeVec3(point1)
    point2 = mist.utils.makeVec3(point2)
    return mist.vec.mag({ x = point1.x - point2.x, y = 0, z = point1.z - point2.z })
end

function mist.utils.get3DDist(point1, point2)
    return mist.vec.mag({
        x = point1.x - point2.x,
        y = point1.y - point2.y,
        z = point1.z - point2.z,
    })
end

---------------------------------------------------------------------------------------------------
-- Tier 1a -- deep copy (recursive table copy, preserves metatable, like MIST's deepCopy)
---------------------------------------------------------------------------------------------------

function mist.utils.deepCopy(object)
    local lookup_table = {}
    local function _copy(obj)
        if type(obj) ~= "table" then
            return obj
        elseif lookup_table[obj] then
            return lookup_table[obj]
        end
        local new_table = {}
        lookup_table[obj] = new_table
        for index, value in pairs(obj) do
            new_table[_copy(index)] = _copy(value)
        end
        return setmetatable(new_table, getmetatable(obj))
    end
    return _copy(object)
end

-- Tiers 1b / 2 / 3 / 4 are appended as they are implemented; see the design doc's
-- rollout plan. Until every called symbol above is provided, the load-order swap in
-- base/plugin.json (mist_4_5_126.lua -> this file) must NOT be made.
