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
--   [x] Tier 1a  vector + math utils
--   [x] Tier 1b  geo/coord (getHeading, getAvgPos, getLeadPos, getRandPointInCircle,
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

---------------------------------------------------------------------------------------------------
-- Tier 1b -- geo / coordinate helpers (replicated from mist_4_5_126.lua unless noted)
-- Defined before first use: getNorthCorrection -> getHeading/getDir -> getHeadingPoints.
---------------------------------------------------------------------------------------------------

-- True-north correction at a point (internal helper used by getHeading / getDir).
function mist.getNorthCorrection(gPoint)
    local point = mist.utils.deepCopy(gPoint)
    if not point.z then -- Vec2 -> Vec3
        point.z = point.y
        point.y = 0
    end
    local lat, lon = coord.LOtoLL(point)
    local north_posit = coord.LLtoLO(lat + 1, lon)
    return math.atan2(north_posit.z - point.z, north_posit.x - point.x)
end

function mist.getHeading(unit, rawHeading)
    local unitpos = unit:getPosition()
    if unitpos then
        local heading = math.atan2(unitpos.x.z, unitpos.x.x)
        if not rawHeading then
            heading = heading + mist.getNorthCorrection(unitpos.p)
        end
        if heading < 0 then
            heading = heading + 2 * math.pi
        end
        return heading
    end
end

function mist.utils.getDir(vec, point)
    local dir = math.atan2(vec.z, vec.x)
    if point then
        dir = dir + mist.getNorthCorrection(point)
    end
    if dir < 0 then
        dir = dir + 2 * math.pi
    end
    return dir
end

function mist.utils.getHeadingPoints(point1, point2, north)
    if north then
        local p1 = mist.utils.get3DDist(point1)
        return mist.utils.getDir(mist.vec.sub(mist.utils.makeVec3(point2), p1), p1)
    else
        return mist.utils.getDir(mist.vec.sub(mist.utils.makeVec3(point2), mist.utils.makeVec3(point1)))
    end
end

function mist.getAvgPos(unitNames)
    local avgX, avgY, avgZ, totNum = 0, 0, 0, 0
    for i = 1, #unitNames do
        local unit
        if Unit.getByName(unitNames[i]) then
            unit = Unit.getByName(unitNames[i])
        elseif StaticObject.getByName(unitNames[i]) then
            unit = StaticObject.getByName(unitNames[i])
        end
        if unit and unit:isExist() == true then
            local pos = unit:getPosition().p
            if pos then
                avgX = avgX + pos.x
                avgY = avgY + pos.y
                avgZ = avgZ + pos.z
                totNum = totNum + 1
            end
        end
    end
    if totNum ~= 0 then
        return { x = avgX / totNum, y = avgY / totNum, z = avgZ / totNum }
    end
end

function mist.getLeadPos(group)
    local gObj
    if type(group) == "string" then
        gObj = Group.getByName(group)
    elseif type(group) == "table" then
        gObj = group
    end
    if gObj then
        local units = gObj:getUnits()
        local leader = units[1]
        if leader then
            if Unit.isExist(leader) then
                return leader:getPoint()
            elseif #units > 1 then
                for i = 2, #units do
                    if Unit.isExist(units[i]) then
                        return units[i]:getPoint()
                    end
                end
            end
        end
    end
end

function mist.utils.zoneToVec3(zone, gl)
    local new = {}
    if type(zone) == "table" then
        if zone.point then
            new.x = zone.point.x
            new.y = zone.point.y
            new.z = zone.point.z
        elseif zone.x and zone.y and zone.z then
            new = mist.utils.deepCopy(zone)
        end
        return new
    elseif type(zone) == "string" then
        zone = trigger.misc.getZone(zone)
        if zone then
            new.x = zone.point.x
            new.y = zone.point.y
            new.z = zone.point.z
        end
    end
    if new.x and gl then
        new.y = land.getHeight({ x = new.x, y = new.z })
    end
    return new
end

function mist.terrainHeightDiff(coordArg, searchSize)
    local searchRadius = searchSize or 5
    if type(coordArg) == "string" then
        coordArg = mist.utils.zoneToVec3(coordArg)
    end
    coordArg = mist.utils.makeVec2(coordArg)
    local samples = {}
    samples[#samples + 1] = land.getHeight(coordArg)
    for i = 0, 360, 30 do
        samples[#samples + 1] = land.getHeight({
            x = coordArg.x + (math.sin(math.rad(i)) * searchRadius),
            y = coordArg.y + (math.cos(math.rad(i)) * searchRadius),
        })
        if searchRadius >= 20 then
            samples[#samples + 1] = land.getHeight({
                x = coordArg.x + (math.sin(math.rad(i)) * (searchRadius / 2)),
                y = coordArg.y + (math.cos(math.rad(i)) * (searchRadius / 2)),
            })
        end
    end
    local tMax, tMin = samples[1], samples[1]
    for _, height in pairs(samples) do
        if height > tMax then tMax = height end
        if height < tMin then tMin = height end
    end
    return mist.utils.round(tMax - tMin, 2)
end

-- Anti-clustering random over an integer range (MIST semantics).
function mist.random(firstNum, secondNum)
    local lowNum, highNum
    if not secondNum then
        highNum = firstNum
        lowNum = 1
    else
        lowNum = firstNum
        highNum = secondNum
    end
    local total = 1
    if math.abs(highNum - lowNum + 1) < 50 then
        total = math.modf(50 / math.abs(highNum - lowNum + 1))
    end
    local choices = {}
    for _ = 1, total do
        for x = lowNum, highNum do
            choices[#choices + 1] = x
        end
    end
    local rtnVal = math.random(#choices)
    for _ = 1, 10 do
        rtnVal = math.random(#choices)
    end
    return choices[rtnVal]
end

function mist.getRandPointInCircle(p, r, innerRadius, maxA, minA)
    local point = mist.utils.makeVec3(p)
    local theta = 2 * math.pi * math.random()
    local radius = r or 1000
    local minR = innerRadius or 0
    if maxA and not minA then
        theta = math.rad(math.random(0, maxA - math.random()))
    elseif maxA and minA then
        if minA < maxA then
            theta = math.rad(math.random(minA, maxA) - math.random())
        else
            theta = math.rad(math.random(maxA, minA) - math.random())
        end
    end
    local rad = math.random() + math.random()
    if rad > 1 then
        rad = 2 - rad
    end
    local radMult
    if minR and minR <= radius then
        radMult = radius * math.sqrt((minR ^ 2 + (radius ^ 2 - minR ^ 2) * math.random()) / radius ^ 2)
    else
        radMult = radius * rad
    end
    local rndCoord
    if radius > 0 then
        rndCoord = { x = math.cos(theta) * radMult + point.x, y = math.sin(theta) * radMult + point.z }
    else
        rndCoord = { x = point.x, y = point.z }
    end
    return rndCoord
end

---------------------------------------------------------------------------------------------------
-- Tier 1b -- coordinate string formatting
---------------------------------------------------------------------------------------------------

-- MGRS table (from coord.LLtoMGRS) -> string. Replicated verbatim from MIST.
function mist.tostringMGRS(MGRS, acc)
    if acc == 0 then
        return MGRS.UTMZone .. " " .. MGRS.MGRSDigraph
    else
        return MGRS.UTMZone .. " " .. MGRS.MGRSDigraph
            .. " " .. string.format("%0" .. acc .. "d", mist.utils.round(MGRS.Easting / (10 ^ (5 - acc)), 0))
            .. " " .. string.format("%0" .. acc .. "d", mist.utils.round(MGRS.Northing / (10 ^ (5 - acc)), 0))
    end
end

-- LL formatting: MOOSE UTILS.tostringLL has the identical (lat, lon, acc, DMS) signature.
-- Delegated (cosmetic; verify format parity during the in-game pass).
mist.tostringLL = UTILS.tostringLL

---------------------------------------------------------------------------------------------------
-- Tier 1b -- line-of-sight (only reached by CTLD JTAC autolase, which is DISABLED in Retribution;
-- compact best-effort impl over land.isVisible so the symbol is never nil).
---------------------------------------------------------------------------------------------------

function mist.getUnitsLOS(unitset1, altoffset1, unitset2, altoffset2, radius)
    radius = radius or math.huge
    altoffset1 = altoffset1 or 0
    altoffset2 = altoffset2 or 0
    local function collect(names)
        local out = {}
        for i = 1, #names do
            local u = Unit.getByName(names[i])
            if u and u:isExist() == true then
                out[#out + 1] = { unit = u, pos = u:getPosition().p }
            end
        end
        return out
    end
    local info1, info2 = collect(unitset1), collect(unitset2)
    local los = {}
    for _, a in ipairs(info1) do
        for _, b in ipairs(info2) do
            local pa = { x = a.pos.x, y = a.pos.y + altoffset1, z = a.pos.z }
            local pb = { x = b.pos.x, y = b.pos.y + altoffset2, z = b.pos.z }
            if mist.utils.get3DDist(pa, pb) <= radius and land.isVisible(pa, pb) then
                los[#los + 1] = { from = a.unit, to = b.unit }
            end
        end
    end
    return los
end

---------------------------------------------------------------------------------------------------
-- Tier 1b -- debug table serializer (mist.utils.tableShow). Debug-only; format need not match MIST.
---------------------------------------------------------------------------------------------------

function mist.utils.tableShow(tbl, loc, indent, tableshow_tbls)
    tableshow_tbls = tableshow_tbls or {}
    indent = indent or ""
    if type(tbl) ~= "table" then
        return tostring(tbl)
    end
    if tableshow_tbls[tbl] then
        return tostring(tbl) .. " (recursion)"
    end
    tableshow_tbls[tbl] = true
    local out = "{\n"
    for k, v in pairs(tbl) do
        local key
        if type(k) == "number" then
            key = "[" .. k .. "]"
        else
            key = "[\"" .. tostring(k) .. "\"]"
        end
        out = out .. indent .. "  " .. key .. " = "
        if type(v) == "table" then
            out = out .. mist.utils.tableShow(v, loc, indent .. "  ", tableshow_tbls)
        elseif type(v) == "string" then
            out = out .. "\"" .. v .. "\""
        else
            out = out .. tostring(v)
        end
        out = out .. ",\n"
    end
    out = out .. indent .. "}"
    return out
end

-- Tiers 2 / 3 / 4 are appended as they are implemented; see the design doc's rollout plan.
-- Until every called symbol is provided, the load-order swap in base/plugin.json
-- (mist_4_5_126.lua -> this file) must NOT be made.

