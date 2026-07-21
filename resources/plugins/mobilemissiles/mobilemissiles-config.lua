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
--
-- The generator now also gives the FireAtPoint its own stop condition (hold deadline +
-- MISSILE_FIRE_WINDOW_S = 240 s in tgogenerator.py), because a dry, never-ending fire task
-- left the launchers pinned in their deployed state and resetTask alone recovered only 2 of
-- 9 fired batteries (2026-07-17 Scenic Route fly). fireMarginS MUST stay above that 240 s
-- window so the first route push arrives after the task has ended on its own; the resetTask
-- here stays as a belt-and-braces for pre-window missions.
--
-- GIVE-UP: a group whose consecutive route pushes produce essentially no movement is
-- dropped from the loop (2026-07-17 Scenic Route Merged fly: all 8 fired CH_Shahed136 sites
-- stayed pinned post-salvo -- a mod launcher state DCS will not drive out of, while the
-- never-fired ones drove fine -- and each drew 6 more futile pushes/hour). Two dry
-- pushes and the group is left alone; real movement resets the count.
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
local MIN_PROGRESS_M = 100 -- a push that moved the group less than this counts as dry
local GIVE_UP_PUSHES = 2 -- consecutive dry pushes before a group stops being routed

if dcsRetribution.plugins and dcsRetribution.plugins.mobilemissiles then
    local o = dcsRetribution.plugins.mobilemissiles
    INTERVAL = tonumber(o.scootIntervalS) or INTERVAL
    RADIUS = (tonumber(o.scootRadiusNm) or RADIUS / 1852) * 1852 -- NM (UI) -> m
    SPEED = (tonumber(o.scootSpeedKt) or SPEED / 1.852) * 1.852 -- kt (UI) -> km/h
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
-- startDelay staggers this site's loop relative to the others: with every site armed at
-- the same moment, all of them used to route in the SAME frame every INTERVAL -- at 39
-- sites (2026-07-17 Scenic Route fly) that synchronized pathing spike pegged the sim
-- thread (continuous ANTIFREEZE, single-digit FPS). Spreading the first ticks across
-- the interval keeps at most one site's route push per slice; each site still re-routes
-- every INTERVAL thereafter.
local function startSite(site, startDelay)
    local cx, cy = num(site.x), num(site.y)
    local holds = fireHoldsOf(site)
    -- Per-group push ledger for the give-up rule: group name ->
    -- { x, z: lead position at the last route push, dry: consecutive dry pushes,
    --   stuck: true once given up }.
    local pushes = {}
    local function leadPos(g)
        local ok, p = pcall(function()
            local lead = g:getUnit(1)
            return lead and lead:isExist() and lead:getPoint() or nil
        end)
        return ok and p or nil
    end
    local function tick()
        local groups = aliveGroups(site.groups)
        if #groups == 0 then
            return nil -- site destroyed -> stop scheduling
        end
        local now = timer.getTime()
        for _, g in ipairs(groups) do
            local name = g:getName()
            local hold = holds[name]
            local rec = pushes[name]
            if rec and rec.stuck then
                -- Given up: a launcher DCS will not drive (the fired CH_Shahed136
                -- state) -- stop hammering it with routes it cannot fly.
            elseif hold and now < hold + FIRE_MARGIN then
                -- Fire first, THEN scoot: this group's Hold -> FireAtPoint rides its
                -- mission task and a route push would setTask-replace it. Sit tight
                -- until the launch window (+ margin) has passed.
                env.info("MOBILEMISSILES|: holding " .. name .. " for its fire mission")
            else
                local here = leadPos(g)
                if rec and here then
                    local dx = (here.x or 0) - rec.x
                    local dz = (here.z or 0) - rec.z
                    if math.sqrt(dx * dx + dz * dz) < MIN_PROGRESS_M then
                        rec.dry = rec.dry + 1
                    else
                        rec.dry = 0
                    end
                    if rec.dry >= GIVE_UP_PUSHES then
                        rec.stuck = true
                        env.info("MOBILEMISSILES|: giving up on " .. name
                            .. " (no movement across " .. rec.dry .. " route pushes)")
                    end
                end
                if not (rec and rec.stuck) then
                    local dest = mist.getRandPointInCircle({ x = cx, y = cy }, RADIUS)
                    driveTo(g, dest.x, dest.y, SPEED, hold ~= nil)
                    if here then
                        pushes[name] = {
                            x = here.x or 0,
                            z = here.z or 0,
                            dry = rec and rec.dry or 0,
                            stuck = false,
                        }
                    end
                end
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
    timer.scheduleFunction(guarded, {}, timer.getTime() + GRACE + (startDelay or 0))
end

local ok, err = pcall(function()
    local count = 0
    local total = (type(data.sites) == "table") and #data.sites or 0
    local stagger = total > 0 and (INTERVAL / total) or 0
    if type(data.sites) == "table" then
        for i, site in ipairs(data.sites) do
            startSite(site, (i - 1) * stagger)
            count = count + 1
        end
    end
    env.info(string.format("MOBILEMISSILES|: shoot-and-scoot armed on %d site(s)", count))
end)
if not ok then
    env.error("MOBILEMISSILES|: setup error: " .. tostring(err))
end
