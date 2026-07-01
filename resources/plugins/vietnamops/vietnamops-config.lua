-------------------------------------------------------------------------------------------------------------------------------------------------------------
-- Vietnam Ops suite configuration bridge for DCS Retribution
--
-- Runs the opt-in Vietnam-era period mechanics from the dcsRetribution.VietnamOps
-- data table emitted by the mission generator (game/missiongenerator/vietnamopsluadata.py).
-- Each sub-feature is present in the table ONLY when its 'Vietnam Ops' setting is on, so
-- this plugin gates purely on data presence -- inert (early-return) for a non-Vietnam
-- mission. Vanilla DCS + bundled MOOSE only; pcall-guarded so a malformed record degrades
-- to a logged warning, never a CTD. See docs/dev/design/414th-vietnam-ops-notes.md.
--
-- Phase 1 -- Arc Light: a heavy-bomber Strike (B-52, etc.) walks a carpet of explosions
-- across its target at the run-in, modelling the Operation Niagara Arc Light strikes. The
-- generator emits each eligible bomber group + its target centre; this script watches the
-- bomber and, when it closes inside the release range, walks a box of impacts oriented
-- along its run-in (bearing to the target). A bomber shot down before the run-in never
-- fires its carpet -- losses stay native.
-------------------------------------------------------------------------------------------------------------------------------------------------------------

env.info("DCSRetribution|Vietnam Ops plugin - configuration")

if not (dcsRetribution and dcsRetribution.VietnamOps) then
    env.info("DCSRetribution|Vietnam Ops plugin - no VietnamOps data; skipping")
    return
end

local suite = dcsRetribution.VietnamOps

-------------------------------------------------------------------------------
-- Arc Light: heavy-bomber Strike carpet
-------------------------------------------------------------------------------
if suite.arcLight and suite.arcLight.strikes then
    -- Tunables (plugin specificOptions), with safe defaults.
    local CARPET_LENGTH = 1700      -- m, along the run-in
    local CARPET_WIDTH = 500        -- m, across the run-in
    local BLAST_POWER = 300         -- per-impact kg TNT equivalent
    local RELEASE_RANGE = 8 * 1852  -- m from target to begin the pass
    if dcsRetribution.plugins and dcsRetribution.plugins.vietnamops then
        local o = dcsRetribution.plugins.vietnamops
        CARPET_LENGTH = tonumber(o.arcLightLength) or CARPET_LENGTH
        CARPET_WIDTH = tonumber(o.arcLightWidth) or CARPET_WIDTH
        BLAST_POWER = tonumber(o.arcLightBlastPower) or BLAST_POWER
        if o.arcLightTriggerNm ~= nil then
            RELEASE_RANGE = (tonumber(o.arcLightTriggerNm) or 8) * 1852
        end
    end

    local ROWS = 14         -- along-track sticks (each a delayed step -> the "walk")
    local COLS = 5          -- cross-track lanes
    local STEP_TIME = 0.25  -- s between along-track rows
    local JITTER = 40       -- m random scatter per impact
    local POLL = 5          -- s between bomber range checks

    -- Walk a box of explosions across (cx, cz) [north, east], oriented along headingRad
    -- (the bomber's bearing to the target at release). Rows step along-track with a small
    -- delay so the carpet visibly walks; columns spread it cross-track.
    local function dropCarpet(cx, cz, headingRad)
        local cosH = math.cos(headingRad)
        local sinH = math.sin(headingRad)
        for row = 0, ROWS - 1 do
            local along = (row / (ROWS - 1) - 0.5) * CARPET_LENGTH
            local delay = row * STEP_TIME
            for col = 0, COLS - 1 do
                local cross = (col / (COLS - 1) - 0.5) * CARPET_WIDTH
                -- along-track unit vec = (cosH, sinH); cross-track = (-sinH, cosH).
                local north = cx + along * cosH - cross * sinH + math.random(-JITTER, JITTER)
                local east = cz + along * sinH + cross * cosH + math.random(-JITTER, JITTER)
                timer.scheduleFunction(function()
                    local h = land.getHeight({ x = north, y = east }) or 0
                    trigger.action.explosion({ x = north, y = h, z = east }, BLAST_POWER)
                    return nil
                end, {}, timer.getTime() + delay)
            end
        end
    end

    local armed = {}  -- group name -> true once its carpet has fired (one-shot)

    local function watch(entry)
        local gname = entry.group
        local tx = tonumber(entry.x)  -- north
        local tz = tonumber(entry.y)  -- east (pydcs y -> DCS z)
        if not gname or not tx or not tz then
            return
        end

        local function tick()
            local ok, err = pcall(function()
                if armed[gname] then
                    return
                end
                local grp = GROUP:FindByName(gname)
                if not (grp and grp:IsAlive()) then
                    return  -- bomber gone before the run-in: no carpet (native loss).
                end
                local unit = grp:GetUnit(1)
                if not (unit and unit:IsAlive()) then
                    return
                end
                local coord = unit:GetCoordinate()
                if not coord then
                    return
                end
                local uv = coord:GetVec2()  -- { x = north, y = east }
                local dn = tx - uv.x
                local de = tz - uv.y
                local dist = math.sqrt(dn * dn + de * de)
                if dist <= RELEASE_RANGE then
                    armed[gname] = true
                    -- Run-in heading = bearing from the bomber to the target (it is
                    -- inbound), in the (north, east) frame: atan2(east, north).
                    local headingRad = math.atan2(de, dn)
                    dropCarpet(tx, tz, headingRad)
                    pcall(
                        trigger.action.outTextForCoalition,
                        unit:GetCoalition(),
                        "ARC LIGHT inbound -- heavy bomber cell on target.",
                        20
                    )
                    env.info("DCSRetribution|Vietnam Ops - Arc Light carpet released by '"
                        .. tostring(gname) .. "'")
                end
            end)
            if not ok then
                env.warning("vietnamops: Arc Light tick error (continuing): " .. tostring(err))
            end
            if armed[gname] then
                return nil  -- stop polling once the carpet has fired.
            end
            return timer.getTime() + POLL
        end

        timer.scheduleFunction(tick, {}, timer.getTime() + POLL)
    end

    local count = 0
    for _, entry in pairs(suite.arcLight.strikes) do
        watch(entry)
        count = count + 1
    end
    env.info(string.format(
        "DCSRetribution|Vietnam Ops - Arc Light armed for %d heavy-bomber strike(s) "
            .. "(carpet %dx%dm, power %d, release %.1f NM)",
        count, CARPET_LENGTH, CARPET_WIDTH, BLAST_POWER, RELEASE_RANGE / 1852))
end

-------------------------------------------------------------------------------
-- AAA flak gauntlet
--
-- Recreates the AAA-heavy Vietnam threat environment: any aircraft flying within
-- range and below the effective ceiling of an opposing, alive AAA gun draws barrage
-- flak bursts. A steady, predictable heading + altitude TIGHTENS the bursts (and a
-- sustained predictable run draws the occasional close "tracking" round); jinking and
-- varying altitude widens them. Atmospheric pressure to jink -- mostly visual puffs
-- with a modest, tunable bite for straight-and-level flight; NOT a hidden hard-kill SAM.
--
-- AAA guns are discovered at runtime by the DCS "AAA" attribute (so frontline ZSU/
-- Shilka belts and airfield guns all count), refreshed periodically. Pure DCS API,
-- pcall-guarded. Gated on dcsRetribution.VietnamOps.flak.
-------------------------------------------------------------------------------
if suite.flak and suite.flak.enabled then
    local ENGAGE_RANGE = 4500   -- m, horizontal gun reach
    local CEILING = 4500        -- m AGL, effective flak ceiling
    local FLOOR = 120           -- m AGL, below this the aircraft is on the deck
    local MIN_MISS = 110        -- m, tightest barrage miss (fully predictable) -- softened 2026-06-28 (L2: was too accurate)
    local MAX_MISS = 250        -- m, loosest barrage miss (jinking)
    local BLAST = 6             -- per-burst power (small -- mostly visual) -- softened 2026-06-28 (L2)
    local BURSTS_PER_SITE = 1
    local MAX_SITES = 3         -- cap stacked density from many guns
    if dcsRetribution.plugins and dcsRetribution.plugins.vietnamops then
        local o = dcsRetribution.plugins.vietnamops
        ENGAGE_RANGE = tonumber(o.flakEngageRangeM) or ENGAGE_RANGE
        CEILING = tonumber(o.flakCeilingM) or CEILING
        MIN_MISS = tonumber(o.flakMinMissM) or MIN_MISS
        MAX_MISS = tonumber(o.flakMaxMissM) or MAX_MISS
        BLAST = tonumber(o.flakBlastPower) or BLAST
    end

    local POLL = 2.5            -- s between flak evaluations
    local HDG_STEADY_DEG = 8    -- heading change under this counts as "steady"
    local ALT_STEADY_M = 40     -- altitude change under this counts as "steady"
    local FACTOR_STEP = 0.2     -- predictability ramp per steady tick
    local AAA_REFRESH = 30      -- s between AAA-unit rediscovery sweeps

    local function opposite(side)
        if side == coalition.side.RED then
            return coalition.side.BLUE
        end
        return coalition.side.RED
    end

    -- Discover alive AAA guns, grouped by coalition. Cached + refreshed (guns die /
    -- spawn late). `fresh` (not `next`) avoids shadowing the Lua builtin.
    local aaaCache = { [coalition.side.RED] = {}, [coalition.side.BLUE] = {} }
    local function refreshAAA()
        local ok = pcall(function()
            local fresh = { [coalition.side.RED] = {}, [coalition.side.BLUE] = {} }
            for _, side in pairs({ coalition.side.RED, coalition.side.BLUE }) do
                for _, grp in pairs(coalition.getGroups(side, Group.Category.GROUND) or {}) do
                    for _, u in pairs(grp:getUnits() or {}) do
                        if u:isExist() and u:getLife() > 0 and u:hasAttribute("AAA") then
                            table.insert(fresh[side], u)
                        end
                    end
                end
            end
            aaaCache = fresh
        end)
        if not ok then
            env.warning("vietnamops: flak AAA refresh error (continuing)")
        end
        return timer.getTime() + AAA_REFRESH
    end

    local steady = {}  -- unit name -> { hdg, alt, factor }

    local function angleDiff(a, b)
        local d = math.abs(a - b) % 360
        if d > 180 then
            d = 360 - d
        end
        return d
    end

    local function unitHeading(u)
        local v = u:getVelocity()
        if not v then
            return nil
        end
        local spd = math.sqrt(v.x * v.x + v.z * v.z)
        if spd < 1 then
            return nil  -- too slow to read a heading
        end
        local h = math.deg(math.atan2(v.z, v.x))
        if h < 0 then
            h = h + 360
        end
        return h
    end

    -- 0 (just arrived / jinking) .. 1 (long steady, predictable run).
    local function predictability(u, p)
        local name = u:getName()
        local hdg = unitHeading(u)
        local alt = p.y
        local s = steady[name]
        if not s then
            steady[name] = { hdg = hdg or 0, alt = alt, factor = 0 }
            return 0
        end
        if hdg and angleDiff(hdg, s.hdg) < HDG_STEADY_DEG
            and math.abs(alt - s.alt) < ALT_STEADY_M then
            s.factor = math.min(1, s.factor + FACTOR_STEP)
        else
            s.factor = math.max(0, s.factor - FACTOR_STEP * 2)  -- jink drops it fast
        end
        s.hdg = hdg or s.hdg
        s.alt = alt
        return s.factor
    end

    local function flakBurst(p, factor, tracking)
        local miss, blast
        if tracking then
            miss = MIN_MISS * 0.55   -- a close tracking round for a sustained steady run (softened 2026-06-28, L2)
            blast = BLAST * 2.0
        else
            miss = MAX_MISS - (MAX_MISS - MIN_MISS) * factor
            blast = BLAST
        end
        local ang = math.random() * 2 * math.pi
        local r = miss * (0.6 + 0.8 * math.random())
        local bx = p.x + r * math.cos(ang)
        local bz = p.z + r * math.sin(ang)
        local by = p.y + math.random(-40, 40)
        trigger.action.explosion({ x = bx, y = by, z = bz }, blast)
    end

    local function flakTick()
        local ok, err = pcall(function()
            for _, side in pairs({ coalition.side.RED, coalition.side.BLUE }) do
                local guns = aaaCache[opposite(side)]
                if guns and #guns > 0 then
                    for _, cat in pairs({ Group.Category.AIRPLANE, Group.Category.HELICOPTER }) do
                        for _, grp in pairs(coalition.getGroups(side, cat) or {}) do
                            for _, u in pairs(grp:getUnits() or {}) do
                                if u:isExist() and u:getLife() > 0 and u:inAir() then
                                    local p = u:getPoint()
                                    local agl = p.y - (land.getHeight({ x = p.x, y = p.z }) or 0)
                                    if agl >= FLOOR and agl <= CEILING then
                                        local sites = 0
                                        for _, gun in pairs(guns) do
                                            if gun:isExist() and gun:getLife() > 0 then
                                                local gp = gun:getPoint()
                                                local dx, dz = p.x - gp.x, p.z - gp.z
                                                if (dx * dx + dz * dz) <= (ENGAGE_RANGE * ENGAGE_RANGE) then
                                                    sites = sites + 1
                                                    if sites >= MAX_SITES then
                                                        break
                                                    end
                                                end
                                            end
                                        end
                                        if sites > 0 then
                                            local factor = predictability(u, p)
                                            for i = 1, sites * BURSTS_PER_SITE do
                                                flakBurst(p, factor, i == 1 and factor > 0.8)
                                            end
                                        else
                                            steady[u:getName()] = nil
                                        end
                                    end
                                end
                            end
                        end
                    end
                end
            end
        end)
        if not ok then
            env.warning("vietnamops: flak tick error (continuing): " .. tostring(err))
        end
        return timer.getTime() + POLL
    end

    refreshAAA()  -- populate immediately so the first tick has guns
    timer.scheduleFunction(refreshAAA, {}, timer.getTime() + AAA_REFRESH)
    timer.scheduleFunction(flakTick, {}, timer.getTime() + POLL)
    env.info(string.format(
        "DCSRetribution|Vietnam Ops - AAA flak gauntlet armed (range %dm, ceiling %dm, "
            .. "miss %d-%dm, power %d)",
        ENGAGE_RANGE, CEILING, MIN_MISS, MAX_MISS, BLAST))
end

-------------------------------------------------------------------------------
-- Naval gunfire support (NGFS)
--
-- Offshore gun ships (battleship/cruiser/destroyer/frigate main batteries) deliver
-- shore bombardment in two modes:
--   * PLAYER call-for-fire: an F10 "Naval Fire Mission" menu fires the nearest in-range
--     friendly gun ship on the coalition's last F10 map marker.
--   * AUTOMATIC coastal bombardment: every cadence each gun ship shells the nearest
--     opposing ground target within gun range (so it only ever reaches the coast).
--
-- The generator emits each gun ship + coalition (dcsRetribution.VietnamOps.navalGunfire);
-- targets + ranging are resolved live. Coastal only by construction -- with no enemy ground
-- (or no friendly ground to mark) in a ship's range, nothing fires. MOOSE TaskFireAtPoint
-- (as the TIC artillery path uses) + raw DCS for target discovery / menus. pcall-guarded.
-------------------------------------------------------------------------------
if suite.navalGunfire and suite.navalGunfire.ships then
    local RANGE = 20000         -- m, gun reach for ship/target selection
    local ROUNDS = 12           -- shells per fire mission
    local SALVO_RADIUS = 80     -- m, dispersion radius
    local AUTO = true           -- automatic coastal bombardment on
    local AUTO_INTERVAL = 90    -- s between automatic fire missions
    if dcsRetribution.plugins and dcsRetribution.plugins.vietnamops then
        local o = dcsRetribution.plugins.vietnamops
        RANGE = tonumber(o.ngfsRangeM) or RANGE
        ROUNDS = tonumber(o.ngfsRounds) or ROUNDS
        SALVO_RADIUS = tonumber(o.ngfsSalvoRadiusM) or SALVO_RADIUS
        if o.ngfsAuto ~= nil then AUTO = o.ngfsAuto end
        AUTO_INTERVAL = tonumber(o.ngfsAutoIntervalS) or AUTO_INTERVAL
    end

    -- Gun ships grouped by coalition side.
    local shipsBySide = { [coalition.side.RED] = {}, [coalition.side.BLUE] = {} }
    for _, s in pairs(suite.navalGunfire.ships) do
        if s.group then
            local side = (s.coalition == "RED") and coalition.side.RED or coalition.side.BLUE
            table.insert(shipsBySide[side], s.group)
        end
    end

    local function ngfsOpposite(side)
        if side == coalition.side.RED then
            return coalition.side.BLUE
        end
        return coalition.side.RED
    end

    local function ngfsMsg(side, text)
        trigger.action.outTextForCoalition(side, text, 20)
    end

    -- Fire the nearest in-range, alive friendly gun ship at target vec2 {x=north,y=east}.
    local function fireMission(side, target)
        local bestShip, bestD
        for _, name in pairs(shipsBySide[side] or {}) do
            local grp = GROUP:FindByName(name)
            if grp and grp:IsAlive() then
                local sv = grp:GetCoordinate():GetVec2()
                local d = math.sqrt((sv.x - target.x) ^ 2 + (sv.y - target.y) ^ 2)
                if d <= RANGE and (not bestD or d < bestD) then
                    bestShip, bestD = grp, d
                end
            end
        end
        if not bestShip then
            return false
        end
        local task = bestShip:TaskFireAtPoint(target, SALVO_RADIUS, ROUNDS)
        bestShip:PushTask(task, 1)
        return true
    end

    -- PLAYER: fire on the coalition's most recent F10 map marker.
    local function fireOnLastMark(side)
        local ok, err = pcall(function()
            local panels = world.getMarkPanels() or {}
            local best
            for _, m in pairs(panels) do
                if m.pos and (m.coalition == side or m.coalition == -1) then
                    if not best or (m.idx or 0) > (best.idx or 0) then
                        best = m
                    end
                end
            end
            if not best then
                ngfsMsg(side, "Naval fire: place an F10 map marker on the target first.")
                return
            end
            -- mark pos is a DCS vec3 { x = north, y = alt, z = east }.
            if fireMission(side, { x = best.pos.x, y = best.pos.z }) then
                ngfsMsg(side, "SHOT -- naval gunfire on the way to your marker.")
            else
                ngfsMsg(side, "Naval fire: no gun ship in range of that marker.")
            end
        end)
        if not ok then
            env.warning("vietnamops: NGFS fire-on-mark error (continuing): " .. tostring(err))
        end
    end

    -- AUTO: each gun ship shells the nearest opposing ground target within range.
    local function autoTick()
        local ok, err = pcall(function()
            for _, side in pairs({ coalition.side.RED, coalition.side.BLUE }) do
                local enemy = ngfsOpposite(side)
                for _, name in pairs(shipsBySide[side] or {}) do
                    local grp = GROUP:FindByName(name)
                    if grp and grp:IsAlive() then
                        local sv = grp:GetCoordinate():GetVec2()
                        local best, bestD
                        for _, eg in pairs(coalition.getGroups(enemy, Group.Category.GROUND) or {}) do
                            local u = eg:getUnit(1)
                            if u and u:isExist() and u:getLife() > 0 then
                                local p = u:getPoint()
                                local d = math.sqrt((sv.x - p.x) ^ 2 + (sv.y - p.z) ^ 2)
                                if d <= RANGE and (not bestD or d < bestD) then
                                    best, bestD = { x = p.x, y = p.z }, d
                                end
                            end
                        end
                        if best then
                            local task = grp:TaskFireAtPoint(best, SALVO_RADIUS, ROUNDS)
                            grp:PushTask(task, 1)
                        end
                    end
                end
            end
        end)
        if not ok then
            env.warning("vietnamops: NGFS auto tick error (continuing): " .. tostring(err))
        end
        return timer.getTime() + AUTO_INTERVAL
    end

    -- F10 call-for-fire menu, per coalition that owns gun ships.
    for _, side in pairs({ coalition.side.RED, coalition.side.BLUE }) do
        if #shipsBySide[side] > 0 then
            local root = missionCommands.addSubMenuForCoalition(side, "Naval Fire Mission")
            missionCommands.addCommandForCoalition(
                side, "Fire on last F10 map marker", root, fireOnLastMark, side
            )
        end
    end

    if AUTO then
        timer.scheduleFunction(autoTick, {}, timer.getTime() + AUTO_INTERVAL)
    end
    env.info(string.format(
        "DCSRetribution|Vietnam Ops - Naval gunfire armed (%d/%d gun ship(s) blue/red, "
            .. "range %dm, %d rounds, auto %s)",
        #shipsBySide[coalition.side.BLUE], #shipsBySide[coalition.side.RED],
        RANGE, ROUNDS, tostring(AUTO)))
end

-------------------------------------------------------------------------------
-- Convoy interdiction: a moving enemy supply column on the road behind the FLOT
-- (Steel Tiger / Ho Chi Minh Trail). The generator emits the corridor waypoints +
-- coalition (dcsRetribution.VietnamOps.convoy, the enemy reinforcement road nearest
-- the fighting); this spawns a truck column that drives that road, HALTS when an
-- opposing aircraft closes in (it goes to ground under cover), and rolls a fresh
-- column a while after the old one is wiped, so the trail keeps flowing. Surfaced to
-- the player through an Armed Recon corridor frag. Vanilla-DCS spawning + pcall-guarded.
-- NEEDS A COCKPIT PASS: runtime unit spawning (the coalition.addGroup group-data, the
-- red country, and the halt-under-threat behaviour) can't be exercised headless.
-------------------------------------------------------------------------------
if suite.convoy and suite.convoy.waypoints then
    pcall(function()
        local SPEED = 30 / 3.6 -- m/s (~30 kph trail speed)
        local SCATTER = 9260 -- 5 NM: halt if an enemy aircraft is this close
        local RESPAWN = 600 -- s after a wipe before a fresh column rolls
        local UNITS = 8
        local TRUCK = "Ural-375"
        local POLL = 10
        if dcsRetribution.plugins and dcsRetribution.plugins.vietnamops then
            local o = dcsRetribution.plugins.vietnamops
            SPEED = (tonumber(o.convoySpeedKph) or 30) / 3.6
            SCATTER = tonumber(o.convoyScatterRangeM) or SCATTER
            RESPAWN = tonumber(o.convoyRespawnS) or RESPAWN
            UNITS = tonumber(o.convoyUnits) or UNITS
            TRUCK = o.convoyTruckType or TRUCK
        end

        -- The emitted corridor is the enemy's supply road; spawn the column on that side.
        local CONVOY_SIDE = (suite.convoy.coalition == "BLUE") and coalition.side.BLUE
            or coalition.side.RED
        local CONVOY_COUNTRY = (CONVOY_SIDE == coalition.side.BLUE) and country.id.USA
            or country.id.RUSSIA
        local HUNTER_SIDE = (CONVOY_SIDE == coalition.side.BLUE) and coalition.side.RED
            or coalition.side.BLUE

        local wps = {}
        for _, w in ipairs(suite.convoy.waypoints) do
            wps[#wps + 1] = { x = tonumber(w.x), y = tonumber(w.y) } -- x=north, y=east
        end
        if #wps < 2 then
            return
        end

        local spawnCount = 0
        local currentName = nil

        local function spawnConvoy()
            spawnCount = spawnCount + 1
            local gname = "VietnamConvoy-" .. spawnCount
            local units = {}
            for i = 1, UNITS do
                units[i] = {
                    type = TRUCK,
                    name = gname .. "-" .. i,
                    x = wps[1].x - (i - 1) * 25, -- string the trucks out along the road
                    y = wps[1].y,
                    heading = 0,
                    skill = "Average",
                    playerCanDrive = false,
                }
            end
            local points = {}
            for i, w in ipairs(wps) do
                points[i] = {
                    x = w.x,
                    y = w.y,
                    type = "Turning Point",
                    action = "On Road",
                    speed = SPEED,
                    ETA = 0,
                    ETA_locked = false,
                    formation_template = "",
                    speed_locked = true,
                }
            end
            local groupData = {
                visible = false,
                hidden = false,
                name = gname,
                start_time = 0,
                task = "Ground Nothing",
                route = { points = points },
                units = units,
            }
            if pcall(coalition.addGroup, CONVOY_COUNTRY, Group.Category.GROUND, groupData) then
                currentName = gname
            else
                currentName = nil
            end
        end

        local function convoyLeadPoint()
            local g = currentName and Group.getByName(currentName) or nil
            if g == nil or g:getSize() == 0 then
                return nil
            end
            local u = g:getUnit(1)
            if u == nil or not u:isExist() then
                return nil
            end
            return u:getPoint()
        end

        local function hunterNear(pos)
            for _, cat in pairs({ Group.Category.AIRPLANE, Group.Category.HELICOPTER }) do
                for _, g in pairs(coalition.getGroups(HUNTER_SIDE, cat) or {}) do
                    for _, u in pairs(g:getUnits() or {}) do
                        if u:isExist() and u:inAir() then
                            local p = u:getPoint()
                            local dx, dz = p.x - pos.x, p.z - pos.z
                            if (dx * dx + dz * dz) < (SCATTER * SCATTER) then
                                return true
                            end
                        end
                    end
                end
            end
            return false
        end

        local function tick()
            local pos = convoyLeadPoint()
            if pos == nil then
                if currentName ~= nil then
                    trigger.action.outTextForCoalition(
                        HUNTER_SIDE,
                        "Enemy supply convoy destroyed on the trail.",
                        15
                    )
                    currentName = nil
                    timer.scheduleFunction(function()
                        spawnConvoy()
                        return nil
                    end, {}, timer.getTime() + RESPAWN)
                end
                return timer.getTime() + POLL
            end
            local g = Group.getByName(currentName)
            if g then
                local ctrl = g:getController()
                -- Halt (go to ground) while hunted; roll again once the sky is clear.
                if ctrl then
                    ctrl:setOnOff(not hunterNear(pos))
                end
            end
            return timer.getTime() + POLL
        end

        spawnConvoy()
        timer.scheduleFunction(tick, {}, timer.getTime() + POLL)
        env.info(
            "DCSRetribution|Vietnam Ops - Convoy interdiction armed ("
                .. #wps
                .. " waypoint corridor)"
        )
    end)
end

-------------------------------------------------------------------------------
-- Airbase harassment: sporadic standoff rocket/mortar fire on forward fields
--
-- Recreates the near-constant siege of the Vietnam-era airfields (Bien Hoa, Da Nang,
-- the Khe Sanh strip): each forward, occupied field the generator emitted draws a small,
-- dispersed cluster of impacts near the ramp on a randomized cadence. Mostly noise/smoke
-- with a modest, tunable bite -- NOT precision counter-air. The generator has already
-- filtered out every player-spawn field (so a cold-and-dark player is never shelled), and
-- a startup grace period suppresses all fire while everyone is still aligning. Vanilla
-- DCS (trigger.action.explosion), pcall-guarded. Gated on
-- dcsRetribution.VietnamOps.airbaseHarassment.
-------------------------------------------------------------------------------
if suite.airbaseHarassment and suite.airbaseHarassment.fields then
    local INTERVAL = 240        -- s, mean seconds between events on a field (randomized)
    local ROUNDS = 5            -- impacts per event (a short barrage)
    local DISPERSION = 260      -- m, radius the impacts scatter over the ramp
    local BLAST = 8             -- per-impact power (small -- mostly noise/smoke)
    local GRACE = 300           -- s, hard no-fire window at mission start (alignment)
    if dcsRetribution.plugins and dcsRetribution.plugins.vietnamops then
        local o = dcsRetribution.plugins.vietnamops
        INTERVAL = tonumber(o.harassIntervalS) or INTERVAL
        ROUNDS = tonumber(o.harassRoundsPerEvent) or ROUNDS
        DISPERSION = tonumber(o.harassDispersionM) or DISPERSION
        BLAST = tonumber(o.harassBlastPower) or BLAST
        GRACE = tonumber(o.harassGraceS) or GRACE
    end

    local STEP_TIME = 0.4       -- s between the impacts of one barrage (walking effect)
    local INTERVAL_JITTER = 0.5 -- +/- fraction of INTERVAL, so the cadence is sporadic

    -- Defense-in-depth: names the generator says must never be touched. Python already
    -- excludes them from `fields`, but honor the list too so a mismatch can only under-fire.
    local excluded = {}
    if suite.airbaseHarassment.excludedFields then
        for _, nm in pairs(suite.airbaseHarassment.excludedFields) do
            excluded[tostring(nm)] = true
        end
    end

    -- Land one dispersed barrage near (cx, cz) [north, east].
    local function dropBarrage(cx, cz)
        for i = 1, ROUNDS do
            local ang = math.random() * 2 * math.pi
            local r = DISPERSION * math.sqrt(math.random())  -- uniform over the disc
            local north = cx + r * math.cos(ang)
            local east = cz + r * math.sin(ang)
            timer.scheduleFunction(function()
                local h = land.getHeight({ x = north, y = east }) or 0
                trigger.action.explosion({ x = north, y = h, z = east }, BLAST)
                return nil
            end, {}, timer.getTime() + (i - 1) * STEP_TIME)
        end
    end

    local function nextDelay()
        local jitter = 1 + (math.random() * 2 - 1) * INTERVAL_JITTER
        return math.max(20, INTERVAL * jitter)
    end

    local function watch(field)
        local name = field.name and tostring(field.name) or nil
        local cx = tonumber(field.x)  -- north
        local cz = tonumber(field.y)  -- east (pydcs y -> DCS z)
        if not cx or not cz then
            return
        end
        if name and excluded[name] then
            return  -- a player field slipped through: never fire on it.
        end
        local side = (field.coalition == "BLUE") and coalition.side.BLUE or coalition.side.RED

        local function tick()
            local ok, err = pcall(function()
                dropBarrage(cx, cz)
                pcall(
                    trigger.action.outTextForCoalition,
                    side,
                    "Incoming -- standoff fire on " .. (name or "the field") .. ".",
                    15
                )
            end)
            if not ok then
                env.warning("vietnamops: harassment tick error (continuing): " .. tostring(err))
            end
            return timer.getTime() + nextDelay()
        end

        -- First event after the grace period, then on the randomized cadence.
        timer.scheduleFunction(tick, {}, timer.getTime() + GRACE + nextDelay())
    end

    local count = 0
    for _, field in pairs(suite.airbaseHarassment.fields) do
        watch(field)
        count = count + 1
    end
    env.info(string.format(
        "DCSRetribution|Vietnam Ops - Airbase harassment armed for %d field(s) "
            .. "(every ~%ds, %d rounds, dispersion %dm, power %d, grace %ds)",
        count, INTERVAL, ROUNDS, DISPERSION, BLAST, GRACE))
end
