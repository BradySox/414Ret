---------------------------------------------------------------------------------------------------
-- COIN in-mission movement runtime.
--
-- Drives the COIN insurgency layer's moving objects that the turn-boundary force model can't
-- animate:
--   * the HVT convoy patrols a slow, random loop around its area (find it + run it down), and
--   * each mobile VBIED drives for the nearest friendly base (intercept it, or it detonates).
--
-- Movement ONLY. The kill / fuse consequence lives in the campaign's turn logic (a mover shot down
-- is recorded natively, like any other unit). Reads dcsRetribution.coin, emitted by
-- game/missiongenerator/coinluadata.py; inert when that node is absent. pcall-guarded throughout so
-- a hiccup never takes the mission down. Definition order matters (Lua 5.1): helpers precede use.
---------------------------------------------------------------------------------------------------

if not (dcsRetribution and dcsRetribution.coin and mist) then
    return
end

local data = dcsRetribution.coin

-- Defaults (metric). Overridable via the plugin options (dcsRetribution.plugins.coin).
local HVT_INTERVAL = 90 -- s between HVT patrol legs
local HVT_RADIUS = 4000 -- m the HVT wanders from his area centre
local HVT_SPEED = 25 -- km/h convoy ground speed
local VBIED_SPEED = 45 -- km/h (the suicide vehicle drives harder)
local VBIED_INTERVAL = 120 -- s between re-issuing the VBIED drive order
local GRACE = 30 -- s before any movement begins

if dcsRetribution.plugins and dcsRetribution.plugins.coin then
    local o = dcsRetribution.plugins.coin
    HVT_INTERVAL = tonumber(o.hvtPatrolIntervalS) or HVT_INTERVAL
    HVT_RADIUS = tonumber(o.hvtPatrolRadiusM) or HVT_RADIUS
    HVT_SPEED = tonumber(o.hvtSpeedKmph) or HVT_SPEED
    VBIED_SPEED = tonumber(o.vbiedSpeedKmph) or VBIED_SPEED
    VBIED_INTERVAL = tonumber(o.vbiedRepathS) or VBIED_INTERVAL
    GRACE = tonumber(o.startGraceS) or GRACE
end

local function num(v)
    return tonumber(v) or 0
end

-- The first alive group named in a groups list, or nil (killed / despawned).
local function firstAlive(groups)
    if type(groups) ~= "table" then
        return nil
    end
    for _, name in ipairs(groups) do
        local g = Group.getByName(name)
        if g and g:isExist() and g:getSize() > 0 then
            return g
        end
    end
    return nil
end

-- Hold fire + alarm-green so the mover relocates instead of stopping to fight, then route it
-- off-road to (x, y). x = north, y = east (the emitter's pydcs frame; mist.ground.buildWP maps it
-- straight onto the DCS ground waypoint).
local function driveTo(group, x, y, speedKmph)
    if not (group and group:isExist()) then
        return false
    end
    pcall(function()
        local con = group:getController()
        if con then
            con:setOption(
                AI.Option.Ground.id.ALARM_STATE,
                AI.Option.Ground.val.ALARM_STATE.GREEN
            )
            con:setOption(AI.Option.Ground.id.ROE, AI.Option.Ground.val.ROE.WEAPON_HOLD)
        end
    end)
    local wp = mist.ground.buildWP({ x = x, y = y }, "off road", mist.utils.kmphToMps(speedKmph))
    return mist.goRoute(group, { wp })
end

-- The HVT convoy: on a cadence, wander to a fresh random point within HVT_RADIUS of its centre.
local function startHvt(hvt)
    local cx, cy = num(hvt.x), num(hvt.y)
    local function tick()
        local g = firstAlive(hvt.groups)
        if not g then
            return nil -- decapitated -> stop scheduling
        end
        local dest = mist.getRandPointInCircle({ x = cx, y = cy }, HVT_RADIUS)
        driveTo(g, dest.x, dest.y, HVT_SPEED)
        return timer.getTime() + HVT_INTERVAL
    end
    timer.scheduleFunction(tick, {}, timer.getTime() + GRACE)
end

-- A mobile VBIED: keep driving for the target base until it is intercepted or arrives.
local function startVbied(v)
    local tx, ty = num(v.targetX), num(v.targetY)
    local function tick()
        local g = firstAlive(v.groups)
        if not g then
            return nil -- intercepted -> stop scheduling
        end
        driveTo(g, tx, ty, VBIED_SPEED)
        return timer.getTime() + VBIED_INTERVAL
    end
    timer.scheduleFunction(tick, {}, timer.getTime() + GRACE)
end

local ok, err = pcall(function()
    if type(data.hvt) == "table" then
        startHvt(data.hvt)
    end
    if type(data.vbieds) == "table" then
        for _, v in ipairs(data.vbieds) do
            startVbied(v)
        end
    end
end)
if ok then
    env.info("COIN|: in-mission movement armed")
else
    env.error("COIN|: setup error: " .. tostring(err))
end
