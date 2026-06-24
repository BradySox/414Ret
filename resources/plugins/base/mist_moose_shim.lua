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
--   [x] Tier 2   object DB (DBs.unitsByName/unitsById/groupsByName/zonesByName/humansByName)
--   [~] Tier 3   sched/events/wp DONE (scheduleFunction, removeFunction, addEventHandler,
--                ground.buildWP); spawn/route REMAINING (dynAdd, dynAddStatic, goRoute,
--                getGroupRoute, groupToRandomZone, makeUnitTable) -- dedicated pass
--   [x] Tier 4   msg/log (message.add, Logger)
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

---------------------------------------------------------------------------------------------------
-- Tier 2 -- object database (mist.DBs.*)
--
-- Verified against consumer source: the entries are barely read --
--   * pairs(unitsByName) / pairs(groupsByName): only the KEY is used (value re-fetched via
--     Unit.getByName / Group.getByName), so entry values can be minimal.
--   * unitsById[id]: only .groupId.   * zonesByName[name]: only .point (Vec3).
--   * humansByName[name]: existence + a mutable .losMarkIds (CTLD JTAC autolase, disabled).
-- DCS Lua 5.1 has no __pairs, so these must be REAL tables. We rebuild them on a periodic scan of
-- coalition.getGroups (cheap; mirrors MIST's own DB cadence). Zones are static -> built once.
---------------------------------------------------------------------------------------------------

mist.DBs.unitsByName = mist.DBs.unitsByName or {}
mist.DBs.unitsById = mist.DBs.unitsById or {}
mist.DBs.groupsByName = mist.DBs.groupsByName or {}
mist.DBs.humansByName = mist.DBs.humansByName or {}
mist.DBs.zonesByName = mist.DBs.zonesByName or {}

local _MIST_DB_REFRESH = 5 -- seconds between unit/group DB refreshes

local function _mistBuildZones()
    local zones = {}
    if env and env.mission and env.mission.triggers and env.mission.triggers.zones then
        for _, z in pairs(env.mission.triggers.zones) do
            local gl = 0
            pcall(function() gl = land.getHeight({ x = z.x, y = z.y }) end)
            zones[z.name] = {
                name = z.name,
                point = { x = z.x, y = gl, z = z.y },
                radius = z.radius,
                verticies = z.verticies,
            }
        end
    end
    mist.DBs.zonesByName = zones
end

local function _mistRefreshDBs()
    local unitsByName, unitsById, groupsByName, humansByName = {}, {}, {}, {}
    local sides = { coalition.side.NEUTRAL, coalition.side.RED, coalition.side.BLUE }
    local cats = {
        Group.Category.AIRPLANE,
        Group.Category.HELICOPTER,
        Group.Category.GROUND,
        Group.Category.SHIP,
    }
    for _, side in pairs(sides) do
        for _, cat in pairs(cats) do
            local ok, groups = pcall(coalition.getGroups, side, cat)
            if ok and groups then
                for _, grp in pairs(groups) do
                    if grp and grp:isExist() then
                        local gname = grp:getName()
                        local gid = grp:getID()
                        groupsByName[gname] = { groupName = gname, groupId = gid }
                        for _, u in pairs(grp:getUnits()) do
                            if u and u:isExist() then
                                local uname = u:getName()
                                local entry = { unitName = uname, groupName = gname, groupId = gid }
                                unitsByName[uname] = entry
                                local okid, uid = pcall(function() return u:getID() end)
                                if okid and uid then
                                    unitsById[tonumber(uid)] = entry
                                end
                                local pname
                                pcall(function() pname = u:getPlayerName() end)
                                if pname then
                                    local prev = mist.DBs.humansByName[uname]
                                    humansByName[uname] = {
                                        unitName = uname,
                                        groupName = gname,
                                        groupId = gid,
                                        playerName = pname,
                                        losMarkIds = prev and prev.losMarkIds or nil,
                                    }
                                end
                            end
                        end
                    end
                end
            end
        end
    end
    mist.DBs.unitsByName = unitsByName
    mist.DBs.unitsById = unitsById
    mist.DBs.groupsByName = groupsByName
    mist.DBs.humansByName = humansByName
end

local function _mistDBLoop()
    _mistRefreshDBs()
    return timer.getTime() + _MIST_DB_REFRESH
end

-- Initial population + periodic refresh. Safe at load: coalition.getGroups, env.mission and
-- timer.* are all available at mission start; the shim loads before any consumer reads mist.DBs.
_mistBuildZones()
_mistRefreshDBs()
timer.scheduleFunction(_mistDBLoop, nil, timer.getTime() + _MIST_DB_REFRESH)

---------------------------------------------------------------------------------------------------
-- Tier 3 (sched/events/wp) + Tier 4 (msg/log). The complex live spawn/route functions
-- (dynAdd, dynAddStatic, goRoute, getGroupRoute, groupToRandomZone, makeUnitTable) are done in a
-- dedicated pass -- they need per-function fidelity (CTLD crate spawning, SCAR/skynet movement).
---------------------------------------------------------------------------------------------------

-- internal helper used by ground.buildWP (not consumer-facing)
function mist.utils.kmphToMps(kmph)
    return kmph * 1000 / 3600
end

local _mistTasks = {} -- mist taskId -> DCS scheduler id
local _mistNextTaskId = 0

-- Run f(unpack(vars)) at time t; if rep, repeat every rep s; if st, stop after st.
-- Returns an id usable with mist.removeFunction. Backed by vanilla timer.scheduleFunction.
function mist.scheduleFunction(f, vars, t, rep, st)
    vars = vars or {}
    _mistNextTaskId = _mistNextTaskId + 1
    local myId = _mistNextTaskId
    local function run(_, now)
        if st and now >= st then
            _mistTasks[myId] = nil
            return nil
        end
        pcall(f, unpack(vars))
        if rep then
            return now + rep
        end
        _mistTasks[myId] = nil
        return nil
    end
    _mistTasks[myId] = timer.scheduleFunction(run, nil, t)
    return myId
end

function mist.removeFunction(id)
    local dcsId = _mistTasks[id]
    if dcsId then
        pcall(timer.removeFunction, dcsId)
        _mistTasks[id] = nil
        return true
    end
    return false
end

local _mistNextEventId = 0
function mist.addEventHandler(f)
    _mistNextEventId = _mistNextEventId + 1
    local handler = { id = _mistNextEventId, f = f }
    function handler:onEvent(event)
        self.f(event)
    end
    world.addEventHandler(handler)
    return handler.id
end

-- msg = { text, displayTime, msgFor = { coa = {...} } }. Retribution only broadcasts to all.
function mist.message.add(msg)
    if not msg or not msg.text then
        return
    end
    trigger.action.outText(tostring(msg.text), msg.displayTime or 20)
end

-- mist.Logger:new(name, level) -> logger with :info/:warn/:error/:alert. Retribution passes
-- pre-formatted strings (no $1 substitution), so these are thin env.* wrappers.
mist.Logger = mist.Logger or {}
mist.Logger.__index = mist.Logger
function mist.Logger:new(name, level)
    return setmetatable({ name = name or "", level = level }, mist.Logger)
end
function mist.Logger:info(msg)
    env.info((self.name or "") .. "|" .. tostring(msg))
end
function mist.Logger:warn(msg)
    env.warning((self.name or "") .. "|" .. tostring(msg))
end
function mist.Logger:error(msg)
    env.error((self.name or "") .. "|" .. tostring(msg))
end
function mist.Logger:alert(msg)
    env.error((self.name or "") .. "|" .. tostring(msg))
end

function mist.ground.buildWP(point, overRideForm, overRideSpeed)
    local wp = {}
    wp.x = point.x
    if point.z then
        wp.y = point.z
    else
        wp.y = point.y
    end
    local form
    if point.speed and not overRideSpeed then
        wp.speed = point.speed
    elseif type(overRideSpeed) == "number" then
        wp.speed = overRideSpeed
    else
        wp.speed = mist.utils.kmphToMps(20)
    end
    if point.form and not overRideForm then
        form = point.form
    else
        form = overRideForm
    end
    if not form then
        wp.action = "Cone"
    else
        form = string.lower(form)
        if form == "off_road" or form == "off road" then
            wp.action = "Off Road"
        elseif form == "on_road" or form == "on road" then
            wp.action = "On Road"
        elseif form == "rank" or form == "line_abrest" or form == "line abrest" or form == "lineabrest" then
            wp.action = "Rank"
        elseif form == "cone" then
            wp.action = "Cone"
        elseif form == "diamond" then
            wp.action = "Diamond"
        elseif form == "vee" then
            wp.action = "Vee"
        elseif form == "echelon_left" or form == "echelon left" or form == "echelonl" then
            wp.action = "EchelonL"
        elseif form == "echelon_right" or form == "echelon right" or form == "echelonr" then
            wp.action = "EchelonR"
        else
            wp.action = "Cone"
        end
    end
    wp.type = "Turning Point"
    return wp
end

-- REMAINING (dedicated pass): mist.dynAdd, mist.dynAddStatic, mist.goRoute, mist.getGroupRoute,
-- mist.groupToRandomZone, mist.makeUnitTable -- the live CTLD spawn + SCAR/skynet route family.
-- Until ALL are provided, the load-order swap in base/plugin.json (mist_4_5_126.lua -> this file)
-- must NOT be made.

