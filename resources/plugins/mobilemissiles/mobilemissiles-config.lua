---------------------------------------------------------------------------------------------------
-- Mobile missile relocation runtime (the SCUD hunt).
--
-- Each emitted theater-missile site's vehicle group(s) drive shoot-and-scoot: on a cadence, they
-- relocate to a fresh random point within the scoot radius of the site's campaign-map position, so
-- the launcher is never quite where the last recon photo froze it. Alarm-green + weapons hold while
-- moving -- they relocate, they don't stop to fight.
--
-- Movement ONLY. Kills record natively (the routed DCS group is the force model's own), the site
-- never migrates beyond the scoot radius (threat rings and the turn-boundary model stay honest),
-- and a dead site just stops being routed. Reads dcsRetribution.mobileMissiles, emitted by
-- game/missiongenerator/mobilemissileluadata.py; inert when that node is absent. pcall-guarded
-- throughout so a hiccup never takes the mission down. Definition order matters (Lua 5.1):
-- helpers precede use.
--
-- FIRE FIRST, THEN SCOOT: a group carrying a scripted fire mission (the missile-site
-- Hold -> FireAtPoint task, forwarded per-site as `fireHolds`) is held still until its launch
-- window (+ a margin) has passed -- mist.goRoute pushes the route with Controller:setTask, which
-- REPLACES the pending fire mission (the 2026-07-16 flown clobber: 12 of 13 batteries silently
-- lost their fire missions to the first relocation). Once the window is over, the spent fire
-- task is cleared with resetTask before routing (a fired launcher otherwise pins on the dead
-- task and never moves -- the BAT battery, same test).
---------------------------------------------------------------------------------------------------

if not (dcsRetribution and dcsRetribution.mobileMissiles and mist) then
    return
end

local data = dcsRetribution.mobileMissiles

-- Defaults (metric). Overridable via the plugin options (dcsRetribution.plugins.mobilemissiles).
local INTERVAL = 480 -- s between relocations
local RADIUS = 4000 -- m the site scoots from its campaign position
local SPEED = 30 -- km/h ground speed while relocating
local GRACE = 120 -- s before the first relocation
local FIRE_MARGIN = 300 -- s past a group's fire-mission window before it starts scooting

if dcsRetribution.plugins and dcsRetribution.plugins.mobilemissiles then
    local o = dcsRetribution.plugins.mobilemissiles
    INTERVAL = tonumber(o.scootIntervalS) or INTERVAL
    RADIUS = tonumber(o.scootRadiusM) or RADIUS
    SPEED = tonumber(o.scootSpeedKmph) or SPEED
    GRACE = tonumber(o.startGraceS) or GRACE
    FIRE_MARGIN = tonumber(o.fireMarginS) or FIRE_MARGIN
end

local function num(v)
    return tonumber(v) or 0
end

-- Every alive group named in a groups list (a site can hold several vehicle groups).
local function aliveGroups(groups)
    local out = {}
    if type(groups) ~= "table" then
        return out
    end
    for _, name in ipairs(groups) do
        local g = Group.getByName(name)
        if g and g:isExist() and g:getSize() > 0 then
            out[#out + 1] = g
        end
    end
    return out
end

-- Per-site fire-mission holds: group name -> hold deadline (s after mission start), the
-- generator's Hold -> FireAtPoint window forwarded by the emitter as the parallel arrays
-- fireHoldGroups / fireHoldS. Absent for groups without a fire mission.
local function fireHoldsOf(site)
    local holds = {}
    if type(site.fireHoldGroups) == "table" and type(site.fireHoldS) == "table" then
        for i, name in ipairs(site.fireHoldGroups) do
            holds[name] = tonumber(site.fireHoldS[i]) or 0
        end
    end
    return holds
end

-- Hold fire + alarm-green so the site relocates instead of stopping to fight, then route it
-- off-road to (x, y). x = north, y = east (the emitter's pydcs frame; mist.ground.buildWP maps it
-- straight onto the DCS ground waypoint). clearTask: the group carried a fire mission whose
-- window has passed -- clear the spent FireAtPoint first, or the controller stays pinned on the
-- dead task and ignores the route (the fired-battery-never-moves half of the clobber).
local function driveTo(group, x, y, speedKmph, clearTask)
    if not (group and group:isExist()) then
        return false
    end
    pcall(function()
        local con = group:getController()
        if con then
            if clearTask and con.resetTask then
                con:resetTask()
            end
            con:setOption(
                AI.Option.Ground.id.ALARM_STATE,
                AI.Option.Ground.val.ALARM_STATE.GREEN
            )
            con:setOption(AI.Option.Ground.id.ROE, AI.Option.Ground.val.ROE.WEAPON_HOLD)
        end
    end)
    -- A DCS ground group needs its route to START at its current position; a route with a
    -- single destination waypoint reads as "you are already there" and the group never drives
    -- (the launchers sat still the whole mission until this was found). Mirror MIST's own
    -- shoot-and-scoot helper mist.groupToRandomZone: current lead position -> destination.
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

-- One site: on a cadence, scoot every alive group to a fresh point around the site's
-- campaign-map centre (the anchor -- so the site wanders its area, it never migrates).
local function startSite(site)
    local cx, cy = num(site.x), num(site.y)
    local holds = fireHoldsOf(site)
    local function tick()
        local groups = aliveGroups(site.groups)
        if #groups == 0 then
            return nil -- site destroyed -> stop scheduling
        end
        local now = timer.getTime()
        for _, g in ipairs(groups) do
            local hold = holds[g:getName()]
            if hold and now < hold + FIRE_MARGIN then
                -- Fire first, THEN scoot: this group's Hold -> FireAtPoint rides its
                -- mission task and a route push would setTask-replace it. Sit tight
                -- until the launch window (+ margin) has passed.
                env.info("MOBILEMISSILES|: holding " .. g:getName() .. " for its fire mission")
            else
                local dest = mist.getRandPointInCircle({ x = cx, y = cy }, RADIUS)
                driveTo(g, dest.x, dest.y, SPEED, hold ~= nil)
            end
        end
        return timer.getTime() + INTERVAL
    end
    -- pcall-guarded: an error in a scheduled tick otherwise kills this site's
    -- scoot loop silently for the rest of the mission (log + retry instead).
    local function guarded()
        local ok, result = pcall(tick)
        if not ok then
            env.warning("mobilemissiles: scoot tick error (retrying): "
                .. tostring(result))
            return timer.getTime() + INTERVAL
        end
        return result
    end
    timer.scheduleFunction(guarded, {}, timer.getTime() + GRACE)
end

local ok, err = pcall(function()
    local count = 0
    if type(data.sites) == "table" then
        for _, site in ipairs(data.sites) do
            startSite(site)
            count = count + 1
        end
    end
    env.info(string.format("MOBILEMISSILES|: shoot-and-scoot armed on %d site(s)", count))
end)
if not ok then
    env.error("MOBILEMISSILES|: setup error: " .. tostring(err))
end
