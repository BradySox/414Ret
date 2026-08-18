---------------------------------------------------------------------------------------------------
-- Mobile missile relocation runtime (§49, the SCUD hunt). Design and the flown
-- findings are in docs/dev/414th-features.md §49.
--
-- Theater-missile sites shoot-and-scoot to a fresh point inside the scoot radius,
-- alarm-green and weapons-hold while moving. Movement only -- kills record natively,
-- the site never leaves the radius, a dead site stops being routed. Reads
-- dcsRetribution.mobileMissiles; inert when absent.
--
-- The load-bearing parts:
--
--  * FIRE FIRST, THEN SCOOT. mist.goRoute routes via Controller:setTask, which
--    REPLACES a pending fire mission -- 12 of 13 batteries silently lost theirs to
--    the first relocation (2026-07-16). Groups with a fire window are held until it
--    passes.
--  * NEVER resetTask before the route push. It was added to clear the spent fire
--    task and did the opposite: setTask already replaces the queue, so the reset
--    was redundant, and issuing both in one frame let the reset land last and wipe
--    the route. Flown 2026-08-17: of three sites in one mission, the only one that
--    moved (3.5 km) was the one with no fire mission and therefore no reset; both
--    held-then-released sites got the reset and moved under 21 m. Unit type is not
--    the discriminator -- two of the three were the same Scud battery.
--  * fireMarginS MUST stay above MISSILE_FIRE_WINDOW_S (240 s, set in tgogenerator),
--    so the first route push lands after the fire task has ended on its own.
--  * Two dry pushes and a group is dropped from the loop. Some mod launchers enter a
--    post-salvo state DCS will not drive out of, and each one drew 6 futile
--    pushes/hour.
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
-- straight onto the DCS ground waypoint). No resetTask here, deliberately -- see the header.
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
    -- The distinct DCS type names still alive in a group, for the give-up log.
    -- A group that will not drive is pinned by ONE of its members, and which one
    -- is the whole question: every entry in the emitter's IMMOBILE_UNIT_IDS was
    -- found by reading a Tacview after the fact, because the log only ever said
    -- which GROUP was stuck. Naming the types turns the next flown mission into a
    -- one-line verdict ("giving up on X [CH_CJ10, CH_SX2190]") instead of
    -- archaeology.
    local function typesOf(g)
        local seen, names = {}, {}
        pcall(function()
            for _, u in ipairs(g:getUnits() or {}) do
                if u and u:isExist() then
                    local t = u:getTypeName()
                    if t and not seen[t] then
                        seen[t] = true
                        names[#names + 1] = t
                    end
                end
            end
        end)
        table.sort(names)
        return table.concat(names, ", ")
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
                            .. " [" .. typesOf(g) .. "]"
                            .. " (no movement across " .. rec.dry .. " route pushes)")
                    end
                end
                if not (rec and rec.stuck) then
                    local dest = mist.getRandPointInCircle({ x = cx, y = cy }, RADIUS)
                    driveTo(g, dest.x, dest.y, SPEED)
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
