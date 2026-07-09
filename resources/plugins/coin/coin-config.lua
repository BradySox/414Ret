---------------------------------------------------------------------------------------------------
-- COIN in-mission liveliness runtime.
--
-- Drives the COIN insurgency layer's moving objects that the turn-boundary force model can't
-- animate:
--   * the HVT convoy patrols a slow, random loop around its area (find it + run it down),
--   * each mobile VBIED drives for the nearest friendly base (intercept it, or it detonates),
--   * each dispersed field cell wanders a small loop of its patch of countryside, and
--   * the live re-infiltration cell creeps slowly toward the base it is infiltrating.
-- Plus one ambient-pressure layer:
--   * insurgent indirect fire -- friendly bases inside a stronghold's mortar reach (emitted by
--     Python, never a player-spawn field, double-guarded here) draw sporadic small barrages
--     after a startup grace (the vietnamops airbase-harassment shape).
--
-- Movement + cosmetics ONLY. The kill / fuse consequence lives in the campaign's turn logic (a
-- mover shot down is recorded natively, like any other unit; the harassment fire changes no force
-- model). Reads dcsRetribution.coin, emitted by game/missiongenerator/coinluadata.py; inert when
-- that node is absent. pcall-guarded throughout so a hiccup never takes the mission down.
-- Definition order matters (Lua 5.1): helpers precede use.
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
local CELL_INTERVAL = 150 -- s between a field cell's patrol legs
local CELL_RADIUS = 2000 -- m a field cell wanders from its patch centre
local CELL_SPEED = 20 -- km/h field-cell ground speed
local INFIL_SPEED = 15 -- km/h the infiltration cell creeps (dismounted pace)
local INFIL_INTERVAL = 180 -- s between re-issuing the infiltrator's creep order
local GRACE = 30 -- s before any movement begins
-- One-way movers (the VBIED drive, the infiltrator creep) are paced so their arrival
-- lands no earlier than this deep into the mission: players can take a long time to
-- get airborne, and an intercept that is over in 20 minutes is content nobody sees.
local MIN_JOURNEY = 5400 -- s (90 min) earliest one-way arrival after mission start
local PACE_FLOOR_KMPH = 5 -- but never slower than a crawl (a close target still creeps in)
local HARASS_INTERVAL = 300 -- s, mean seconds between barrages on a base (randomized)
local HARASS_ROUNDS = 4 -- impacts per barrage
local HARASS_DISPERSION = 250 -- m radius the impacts scatter around the base
local HARASS_POWER = 6 -- per-impact power (small -- mostly noise/smoke)
local HARASS_GRACE = 300 -- s, hard no-fire window at mission start (alignment)

if dcsRetribution.plugins and dcsRetribution.plugins.coin then
    local o = dcsRetribution.plugins.coin
    HVT_INTERVAL = tonumber(o.hvtPatrolIntervalS) or HVT_INTERVAL
    HVT_RADIUS = tonumber(o.hvtPatrolRadiusM) or HVT_RADIUS
    HVT_SPEED = tonumber(o.hvtSpeedKmph) or HVT_SPEED
    VBIED_SPEED = tonumber(o.vbiedSpeedKmph) or VBIED_SPEED
    VBIED_INTERVAL = tonumber(o.vbiedRepathS) or VBIED_INTERVAL
    CELL_INTERVAL = tonumber(o.cellPatrolIntervalS) or CELL_INTERVAL
    CELL_RADIUS = tonumber(o.cellPatrolRadiusM) or CELL_RADIUS
    CELL_SPEED = tonumber(o.cellSpeedKmph) or CELL_SPEED
    INFIL_SPEED = tonumber(o.infilSpeedKmph) or INFIL_SPEED
    INFIL_INTERVAL = tonumber(o.infilRepathS) or INFIL_INTERVAL
    GRACE = tonumber(o.startGraceS) or GRACE
    MIN_JOURNEY = tonumber(o.minJourneyS) or MIN_JOURNEY
    HARASS_INTERVAL = tonumber(o.harassIntervalS) or HARASS_INTERVAL
    HARASS_ROUNDS = tonumber(o.harassRoundsPerEvent) or HARASS_ROUNDS
    HARASS_DISPERSION = tonumber(o.harassDispersionM) or HARASS_DISPERSION
    HARASS_POWER = tonumber(o.harassBlastPower) or HARASS_POWER
    HARASS_GRACE = tonumber(o.harassGraceS) or HARASS_GRACE
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
    -- A DCS ground group needs its route to START at its current position; a route with a
    -- single destination waypoint reads as "you are already there" and the group never drives.
    -- Mirror MIST's own shoot-and-scoot helper mist.groupToRandomZone: lead position -> dest.
    local speedMps = mist.utils.kmphToMps(speedKmph)
    local route = {}
    local lead = group:getUnit(1)
    local here = lead and lead:isExist() and lead:getPoint()
    if here then
        route[#route + 1] = mist.ground.buildWP(here, "off road", speedMps)
    end
    route[#route + 1] = mist.ground.buildWP({ x = x, y = y }, "off road", speedMps)
    return mist.goRoute(group, route)
end

-- The speed that stretches a one-way drive so arrival lands no earlier than MIN_JOURNEY
-- after mission start. Recomputed on every repath from the CURRENT position and the time
-- left, so the pace self-corrects (a stall or detour just speeds the remainder up, capped
-- at the configured speed); once the window has passed, the configured speed applies
-- unchanged. Deliberately continuous pacing, not a proximity trigger -- the mover should
-- be visibly under way the whole time, wherever the player is.
local function pacedSpeed(group, tx, ty, maxKmph)
    local remaining = MIN_JOURNEY - timer.getTime()
    if remaining <= 0 then
        return maxKmph
    end
    local px, pz
    pcall(function()
        local units = group:getUnits()
        local p = units and units[1] and units[1]:getPoint()
        if p then
            px, pz = p.x, p.z
        end
    end)
    if not px then
        return maxKmph
    end
    local distKm = math.sqrt((tx - px) ^ 2 + (ty - pz) ^ 2) / 1000
    local kmph = distKm / (remaining / 3600)
    return math.min(maxKmph, math.max(PACE_FLOOR_KMPH, kmph))
end

-- pcall-guard a mover tick: a runtime error in a scheduled function otherwise kills
-- that mover's loop silently for the rest of the mission. Errors log and retry on
-- the mover's own cadence; a nil return (dead mover) still stops the schedule.
local function guardedTick(label, interval, body)
    return function()
        local ok, result = pcall(body)
        if not ok then
            env.warning("coin: " .. label .. " mover tick error (retrying): "
                .. tostring(result))
            return timer.getTime() + interval
        end
        return result
    end
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
    timer.scheduleFunction(guardedTick("HVT", HVT_INTERVAL, tick), {},
        timer.getTime() + GRACE)
end

-- A mobile VBIED: keep driving for the target base until it is intercepted or arrives.
-- Paced so the drive is still under way MIN_JOURNEY into the mission (the intercept
-- window must survive a slow player start).
local function startVbied(v)
    local tx, ty = num(v.targetX), num(v.targetY)
    local function tick()
        local g = firstAlive(v.groups)
        if not g then
            return nil -- intercepted -> stop scheduling
        end
        driveTo(g, tx, ty, pacedSpeed(g, tx, ty, VBIED_SPEED))
        return timer.getTime() + VBIED_INTERVAL
    end
    timer.scheduleFunction(guardedTick("VBIED", VBIED_INTERVAL, tick), {},
        timer.getTime() + GRACE)
end

-- A dispersed field cell: wander to a fresh random point within CELL_RADIUS of its patch
-- centre on a cadence -- patrolling for it means catching something moving.
local function startCell(cell)
    local cx, cy = num(cell.x), num(cell.y)
    local function tick()
        local g = firstAlive(cell.groups)
        if not g then
            return nil -- hunted down -> stop scheduling
        end
        local dest = mist.getRandPointInCircle({ x = cx, y = cy }, CELL_RADIUS)
        driveTo(g, dest.x, dest.y, CELL_SPEED)
        return timer.getTime() + CELL_INTERVAL
    end
    timer.scheduleFunction(guardedTick("cell", CELL_INTERVAL, tick), {},
        timer.getTime() + GRACE)
end

-- The re-infiltration cell: creep slowly toward the base it is infiltrating. Movement
-- only -- arriving changes nothing here; the staged flip lives in the turn model. Paced
-- like the VBIED so the creep is still visibly under way MIN_JOURNEY into the mission.
local function startInfiltrator(rec)
    local tx, ty = num(rec.targetX), num(rec.targetY)
    local function tick()
        local g = firstAlive(rec.groups)
        if not g then
            return nil -- killed -> stop scheduling
        end
        driveTo(g, tx, ty, pacedSpeed(g, tx, ty, INFIL_SPEED))
        return timer.getTime() + INFIL_INTERVAL
    end
    timer.scheduleFunction(guardedTick("infiltrator", INFIL_INTERVAL, tick), {},
        timer.getTime() + GRACE)
end

---------------------------------------------------------------------------------------------------
-- Insurgent indirect fire on forward friendly bases (the vietnamops §36 shape).
-- Python emitted only the eligible bases (blue, near a live stronghold, NEVER a
-- player-spawn field); excludedBases is the defense-in-depth double-guard -- honoring it
-- can only under-fire. Small dispersed trigger.action.explosion barrages on a randomized
-- cadence after a hard grace window.
---------------------------------------------------------------------------------------------------

local HARASS_STEP_TIME = 0.4 -- s between the impacts of one barrage (walking effect)
local HARASS_JITTER = 0.5 -- +/- fraction of HARASS_INTERVAL, so the cadence is sporadic

local function harassDelay()
    local jitter = 1 + (math.random() * 2 - 1) * HARASS_JITTER
    return math.max(20, HARASS_INTERVAL * jitter)
end

-- Land one dispersed barrage near (cx, cz) [north, east].
local function dropBarrage(cx, cz)
    for i = 1, HARASS_ROUNDS do
        local ang = math.random() * 2 * math.pi
        local r = HARASS_DISPERSION * math.sqrt(math.random()) -- uniform over the disc
        local north = cx + r * math.cos(ang)
        local east = cz + r * math.sin(ang)
        timer.scheduleFunction(function()
            local h = land.getHeight({ x = north, y = east }) or 0
            trigger.action.explosion({ x = north, y = h, z = east }, HARASS_POWER)
            return nil
        end, {}, timer.getTime() + (i - 1) * HARASS_STEP_TIME)
    end
end

local function startHarassment(harass)
    local excluded = {}
    if harass.excludedBases then
        for _, nm in pairs(harass.excludedBases) do
            excluded[tostring(nm)] = true
        end
    end

    local function watch(base)
        local name = base.name and tostring(base.name) or nil
        local cx = tonumber(base.x) -- north
        local cz = tonumber(base.y) -- east (pydcs y -> DCS z)
        if not cx or not cz then
            return
        end
        if name and excluded[name] then
            return -- a player field slipped through: never fire on it.
        end

        local function tick()
            local ok, err = pcall(function()
                dropBarrage(cx, cz)
                pcall(
                    trigger.action.outTextForCoalition,
                    coalition.side.BLUE,
                    "Incoming -- insurgent indirect fire on " .. (name or "the base") .. ".",
                    15
                )
            end)
            if not ok then
                env.warning("COIN|: harassment tick error (continuing): " .. tostring(err))
            end
            return timer.getTime() + harassDelay()
        end

        -- First barrage after the grace period, then on the randomized cadence.
        timer.scheduleFunction(tick, {}, timer.getTime() + HARASS_GRACE + harassDelay())
    end

    local count = 0
    if type(harass.bases) == "table" then
        for _, base in pairs(harass.bases) do
            watch(base)
            count = count + 1
        end
    end
    env.info(string.format("COIN|: indirect-fire harassment armed on %d base(s)", count))
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
    if type(data.cells) == "table" then
        for _, c in ipairs(data.cells) do
            startCell(c)
        end
    end
    if type(data.infiltrators) == "table" then
        for _, rec in ipairs(data.infiltrators) do
            startInfiltrator(rec)
        end
    end
    if type(data.harassment) == "table" then
        startHarassment(data.harassment)
    end
end)
if ok then
    env.info("COIN|: in-mission liveliness armed")
else
    env.error("COIN|: setup error: " .. tostring(err))
end
