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

-- Plugin options are authored in imperial units (ft / NM / kts / lb) -- the units the
-- squadron flies in -- while the DCS API is metric, so every option is converted to
-- meters / m/s / kg exactly once, here at read time. Internal math stays metric.
local FT_TO_M = 0.3048
local NM_TO_M = 1852
local KTS_TO_MS = 0.514444
local LB_TO_KG = 0.453592

-------------------------------------------------------------------------------
-- Arc Light: heavy-bomber Strike carpet
-------------------------------------------------------------------------------
if suite.arcLight and suite.arcLight.strikes then
    -- Tunables (plugin specificOptions, imperial), with safe defaults. Release at 3 NM
    -- so the carpet lands with the bomber nearly overhead (the ballistic forward throw
    -- from ~30k ft is ~2.5-3 NM); the old 8 NM fired the box a full minute early.
    local CARPET_LENGTH = 6000 * FT_TO_M  -- m, along the run-in (option in ft)
    local CARPET_WIDTH = 1500 * FT_TO_M   -- m, across the run-in (option in ft)
    local BLAST_POWER = 660 * LB_TO_KG    -- per-impact power (option in lb TNT equiv.)
    local RELEASE_RANGE = 3 * NM_TO_M     -- m from target to begin the pass
    if dcsRetribution.plugins and dcsRetribution.plugins.vietnamops then
        local o = dcsRetribution.plugins.vietnamops
        CARPET_LENGTH = (tonumber(o.arcLightLengthFt) or 6000) * FT_TO_M
        CARPET_WIDTH = (tonumber(o.arcLightWidthFt) or 1500) * FT_TO_M
        BLAST_POWER = (tonumber(o.arcLightBlastLb) or 660) * LB_TO_KG
        RELEASE_RANGE = (tonumber(o.arcLightReleaseNm) or 3) * NM_TO_M
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
            .. "(carpet %.0fx%.0fm, power %.0f, release %.1f NM)",
        count, CARPET_LENGTH, CARPET_WIDTH, BLAST_POWER, RELEASE_RANGE / NM_TO_M))
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
    -- Imperial options; the L2 softening (2026-07-01: miss 150/320 m, blast 6) carries
    -- into the imperial defaults (500/1000 ft). The mnemonic rename also flushes any
    -- stale pre-softening per-campaign values (the L2 config-mismatch finding).
    local ENGAGE_RANGE = 2.5 * NM_TO_M   -- m, horizontal gun reach (option in NM)
    local CEILING = 15000 * FT_TO_M      -- m AGL, effective flak ceiling (option in ft)
    local FLOOR = 120                    -- m AGL, below this the aircraft is on the deck
    local MIN_MISS = 500 * FT_TO_M       -- m, tightest barrage miss (option in ft)
    local MAX_MISS = 1000 * FT_TO_M      -- m, loosest barrage miss, jinking (option in ft)
    local BLAST = 6                      -- per-burst power (small -- mostly visual)
    local BURSTS_PER_SITE = 1
    local MAX_SITES = 3         -- cap stacked density from many guns
    if dcsRetribution.plugins and dcsRetribution.plugins.vietnamops then
        local o = dcsRetribution.plugins.vietnamops
        ENGAGE_RANGE = (tonumber(o.flakRangeNm) or 2.5) * NM_TO_M
        CEILING = (tonumber(o.flakCeilingFt) or 15000) * FT_TO_M
        MIN_MISS = (tonumber(o.flakMinMissFt) or 500) * FT_TO_M
        MAX_MISS = (tonumber(o.flakMaxMissFt) or 1000) * FT_TO_M
        BLAST = tonumber(o.flakBurstPower) or BLAST
    end

    local POLL = 2.5            -- s between flak evaluations
    local HDG_STEADY_DEG = 8    -- heading change under this counts as "steady"
    local ALT_STEADY_M = 40     -- altitude change under this counts as "steady"
    local FACTOR_STEP = 0.2     -- predictability ramp per steady tick
    local AAA_REFRESH = 30      -- s between AAA-unit rediscovery sweeps
    -- Tracking rounds are the "bite" for flying a predictable line, but firing one EVERY
    -- tick (2.5 s) once steady is what read as a hard-kill on the L2 pass. Gate them: they
    -- need a *sustained* steady run (TRACKING_FACTOR) and only land occasionally
    -- (TRACKING_CHANCE per eligible tick) -- "the occasional close round," per the design.
    local TRACKING_FACTOR = 0.85   -- predictability above which a tracking round is possible (was 0.8)
    local TRACKING_CHANCE = 0.3    -- per-tick probability one lands, so it is occasional not constant

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
            miss = MIN_MISS * 0.75   -- a closer tracking round for a sustained steady run (widened 2026-07-01, L2; was 0.55)
            blast = BLAST * 1.5      -- softened 2026-07-01 (L2; was 2.0)
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
                                            -- One occasional close "tracking" round only on a
                                            -- sustained steady run -- not every tick (L2 fix).
                                            local tracking = factor > TRACKING_FACTOR
                                                and math.random() < TRACKING_CHANCE
                                            for i = 1, sites * BURSTS_PER_SITE do
                                                flakBurst(p, factor, i == 1 and tracking)
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
        "DCSRetribution|Vietnam Ops - AAA flak gauntlet armed (range %.0fm, ceiling %.0fm, "
            .. "miss %.0f-%.0fm, power %d)",
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
    local RANGE = 10 * NM_TO_M       -- m, gun reach for ship/target selection (option in NM)
    local ROUNDS = 12                -- shells per fire mission
    local SALVO_RADIUS = 250 * FT_TO_M  -- m, dispersion radius (option in ft)
    local AUTO = true                -- automatic coastal bombardment on
    local AUTO_INTERVAL = 90         -- s between automatic fire missions
    if dcsRetribution.plugins and dcsRetribution.plugins.vietnamops then
        local o = dcsRetribution.plugins.vietnamops
        RANGE = (tonumber(o.ngfsRangeNm) or 10) * NM_TO_M
        ROUNDS = tonumber(o.ngfsRounds) or ROUNDS
        SALVO_RADIUS = (tonumber(o.ngfsSalvoRadiusFt) or 250) * FT_TO_M
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
            .. "range %.0fm, %d rounds, auto %s)",
        #shipsBySide[coalition.side.BLUE], #shipsBySide[coalition.side.RED],
        RANGE, ROUNDS, tostring(AUTO)))
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
    local DISPERSION = 850 * FT_TO_M  -- m, radius the impacts scatter over the ramp (option in ft)
    local BLAST = 8             -- per-impact power (small -- mostly noise/smoke)
    local GRACE = 300           -- s, hard no-fire window at mission start (alignment)
    if dcsRetribution.plugins and dcsRetribution.plugins.vietnamops then
        local o = dcsRetribution.plugins.vietnamops
        INTERVAL = tonumber(o.harassIntervalS) or INTERVAL
        ROUNDS = tonumber(o.harassRoundsPerEvent) or ROUNDS
        DISPERSION = (tonumber(o.harassDispersionFt) or 850) * FT_TO_M
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
            .. "(every ~%ds, %d rounds, dispersion %.0fm, power %d, grace %ds)",
        count, INTERVAL, ROUNDS, DISPERSION, BLAST, GRACE))
end

-------------------------------------------------------------------------------
-- Super Gaggle hilltop resupply
--
-- Models the Khe Sanh "Super Gaggle": a formation of transport helos (with a fast-mover
-- AAA-suppression flight) runs supplies into a cut-off forward friendly outpost while the
-- player can fly escort. The airframes are DRAWN FROM REAL BLUE SQUADRONS (§37): the
-- generator (game/fourteenth/super_gaggle.py) picks real helo + attack squadrons and emits
-- the exact per-unit names (superGaggle.helo.names / superGaggle.suppressor.names) + their
-- squadron aircraft types. This spawns EXACTLY those airframes, by name, ONCE -- there is no
-- respawn loop (airframes are bounded to the commitment; the old unbounded free helos are
-- gone), and a killed name is charged back to its squadron at debrief. Vanilla-DCS spawning +
-- pcall-guarded. NEEDS A COCKPIT PASS: runtime helo spawning + routing can't be exercised
-- headless.
-------------------------------------------------------------------------------
if suite.superGaggle and suite.superGaggle.outpost and suite.superGaggle.launch
    and suite.superGaggle.helo and suite.superGaggle.helo.names then
    pcall(function()
        local SPEED = 110 * KTS_TO_MS      -- m/s (~110 kts loaded-Huey cruise; option in kts)
        local ALT = 500 * FT_TO_M          -- m, radio-altitude air start / transit height (option in ft AGL)
        local SUPPRESS_ALT = 6500 * FT_TO_M  -- m (baro) transit/attack altitude (option in ft MSL)
        if dcsRetribution.plugins and dcsRetribution.plugins.vietnamops then
            local o = dcsRetribution.plugins.vietnamops
            SPEED = (tonumber(o.gaggleSpeedKts) or 110) * KTS_TO_MS
            ALT = (tonumber(o.gaggleAltFt) or 500) * FT_TO_M
            SUPPRESS_ALT = (tonumber(o.gaggleSuppressorAltFt) or 6500) * FT_TO_M
        end

        local DELIVER_RADIUS = 1500  -- m: within this of the outpost counts as delivered
        local POLL = 10

        local SIDE = (suite.superGaggle.coalition == "RED") and coalition.side.RED
            or coalition.side.BLUE
        -- Spawn under the country the generator emitted (the owning faction's
        -- country, registered on the right coalition in this .miz). The hardcoded
        -- USA/RUSSIA fallback only survives for pre-fix saves: a country not on
        -- the owning coalition would spawn the gaggle NEUTRAL.
        local COUNTRY = tonumber(suite.superGaggle.countryId)
            or ((SIDE == coalition.side.RED) and country.id.RUSSIA or country.id.USA)

        local outpost = {
            x = tonumber(suite.superGaggle.outpost.x),
            y = tonumber(suite.superGaggle.outpost.y),
        }
        local outpostName = suite.superGaggle.outpost.name or "the outpost"
        local launch = {
            x = tonumber(suite.superGaggle.launch.x),
            y = tonumber(suite.superGaggle.launch.y),
        }
        if not (outpost.x and outpost.y and launch.x and launch.y) then
            return
        end

        local heloType = suite.superGaggle.helo.type or "UH-1H"
        local heloNames = suite.superGaggle.helo.names
        if #heloNames < 1 then
            return
        end

        local function wp(px, py, alt, altType, speed)
            return {
                x = px,
                y = py,
                alt = alt,
                alt_type = altType,
                type = "Turning Point",
                action = "Turning Point",
                speed = speed,
                ETA = 0,
                ETA_locked = false,
                formation_template = "",
                speed_locked = true,
            }
        end

        -- Fast-mover suppression flight (the committed attack airframes, if any): launch ->
        -- over the outpost (CAS, so the AI works the nearby AAA) -> back. pcall-guarded, so a
        -- bad/unloaded type never breaks the helo run. Returns true if it spawned.
        local function spawnSuppressors()
            local supp = suite.superGaggle.suppressor
            if not (supp and supp.type and supp.names and #supp.names > 0) then
                return false
            end
            local units = {}
            for i, nm in ipairs(supp.names) do
                units[i] = {
                    type = supp.type,
                    name = nm,
                    x = launch.x - (i - 1) * 60,
                    y = launch.y,
                    alt = SUPPRESS_ALT,
                    alt_type = "BARO",
                    heading = 0,
                    skill = "Good",
                }
            end
            local groupData = {
                visible = false,
                hidden = false,
                name = "SuperGaggleSandy",
                start_time = 0,
                task = "CAS",
                route = {
                    points = {
                        wp(launch.x, launch.y, SUPPRESS_ALT, "BARO", 250),
                        wp(outpost.x, outpost.y, SUPPRESS_ALT, "BARO", 250),
                        wp(launch.x, launch.y, SUPPRESS_ALT, "BARO", 250),
                    },
                },
                units = units,
            }
            return pcall(coalition.addGroup, COUNTRY, Group.Category.AIRPLANE, groupData)
        end

        -- Spawn the committed helo airframes, by name, once.
        local units = {}
        for i, nm in ipairs(heloNames) do
            units[i] = {
                type = heloType,
                name = nm,
                x = launch.x - (i - 1) * 40, -- string the gaggle out over the field
                y = launch.y,
                alt = ALT,
                alt_type = "RADIO",
                heading = 0,
                skill = "Average",
            }
        end
        local groupData = {
            visible = false,
            hidden = false,
            name = "SuperGaggleHelos",
            start_time = 0,
            task = "Transport",
            route = {
                points = {
                    wp(launch.x, launch.y, ALT, "RADIO", SPEED),
                    wp(outpost.x, outpost.y, ALT, "RADIO", SPEED),
                    wp(launch.x, launch.y, ALT, "RADIO", SPEED),
                },
            },
            units = units,
        }
        if not pcall(coalition.addGroup, COUNTRY, Group.Category.HELICOPTER, groupData) then
            return
        end
        local suppressing = spawnSuppressors()
        trigger.action.outTextForCoalition(
            SIDE,
            "SUPER GAGGLE -- resupply helos inbound to " .. outpostName .. "."
                .. (suppressing and " Fast movers suppressing the guns." or "")
                .. " Escort welcome.",
            20
        )

        -- Watch the single run to delivery or loss, then stop (no respawn). Airframe losses
        -- are charged to the squadrons at debrief via the committed unit names, so nothing
        -- needs writing here -- this is only the player cue.
        local function tick()
            local ok, done = pcall(function()
                local g = Group.getByName("SuperGaggleHelos")
                local pos = nil
                if g and g:getSize() > 0 then
                    local u = g:getUnit(1)
                    if u and u:isExist() then
                        pos = u:getPoint()
                    end
                end
                if pos == nil then
                    trigger.action.outTextForCoalition(
                        SIDE,
                        "Super Gaggle down -- resupply run lost inbound to " .. outpostName .. ".",
                        15
                    )
                    return true  -- run over
                end
                local dx, dz = pos.x - outpost.x, pos.z - outpost.y
                if (dx * dx + dz * dz) <= (DELIVER_RADIUS * DELIVER_RADIUS) then
                    trigger.action.outTextForCoalition(
                        SIDE,
                        "Super Gaggle delivered -- " .. outpostName .. " resupplied.",
                        15
                    )
                    return true  -- delivered
                end
                return false
            end)
            if not ok then
                env.warning("vietnamops: super gaggle tick error (continuing): " .. tostring(done))
                return timer.getTime() + POLL
            end
            if done then
                return nil  -- stop polling
            end
            return timer.getTime() + POLL
        end

        timer.scheduleFunction(tick, {}, timer.getTime() + POLL)
        env.info(string.format(
            "DCSRetribution|Vietnam Ops - Super Gaggle armed (outpost %s, %dx %s, single run)",
            outpostName, #heloNames, heloType))
    end)
end

-------------------------------------------------------------------------------
-- FAC(A) willie-pete target marking
--
-- The iconic Vietnam forward air controller: an OV-10 Bronco loitering over the battle
-- area marks enemy ground with white-phosphorus smoke so the strikers (and the player)
-- can visually acquire the target and roll in. Like the flak gauntlet, the runtime
-- discovers the FAC aircraft itself (airborne friendly units of the FAC type) and marks
-- the nearest opposing ground unit in range on a cadence -- so it needs a friendly OV-10
-- airborne over the front to do anything. Pure DCS (trigger.action.smoke), pcall-guarded.
-- Gated on dcsRetribution.VietnamOps.fac.
-------------------------------------------------------------------------------
if suite.fac and suite.fac.enabled then
    local FAC_TYPE = "Bronco-OV-10A"  -- the DCS unit type of the FAC aircraft
    local FAC_RANGE = 3 * NM_TO_M     -- m: how far the FAC spots + marks ground (option in NM)
    local FAC_INTERVAL = 120          -- s between marks per FAC (smoke lasts ~5 min)
    if dcsRetribution.plugins and dcsRetribution.plugins.vietnamops then
        local o = dcsRetribution.plugins.vietnamops
        FAC_TYPE = o.facType or FAC_TYPE
        FAC_RANGE = (tonumber(o.facRangeNm) or 3) * NM_TO_M
        FAC_INTERVAL = tonumber(o.facIntervalS) or FAC_INTERVAL
    end

    local WHITE_SMOKE = 2  -- trigger.smokeColor: 0 green, 1 red, 2 white (willie pete), 3 orange, 4 blue

    local function facOpposite(side)
        if side == coalition.side.RED then
            return coalition.side.BLUE
        end
        return coalition.side.RED
    end

    -- Nearest alive opposing ground unit within FAC_RANGE of (fx, fz) [north, east].
    local function nearestEnemyGround(enemySide, fx, fz)
        local best, bestD = nil, nil
        for _, grp in pairs(coalition.getGroups(enemySide, Group.Category.GROUND) or {}) do
            for _, u in pairs(grp:getUnits() or {}) do
                if u:isExist() and u:getLife() > 0 then
                    local p = u:getPoint()
                    local dx, dz = p.x - fx, p.z - fz
                    local d2 = dx * dx + dz * dz
                    if d2 <= (FAC_RANGE * FAC_RANGE) and (not bestD or d2 < bestD) then
                        best, bestD = p, d2
                    end
                end
            end
        end
        return best
    end

    local function facTick()
        local ok, err = pcall(function()
            for _, side in pairs({ coalition.side.RED, coalition.side.BLUE }) do
                local enemySide = facOpposite(side)
                for _, grp in pairs(coalition.getGroups(side, Group.Category.AIRPLANE) or {}) do
                    for _, u in pairs(grp:getUnits() or {}) do
                        if u:isExist() and u:getLife() > 0 and u:inAir()
                            and u:getTypeName() == FAC_TYPE then
                            local fp = u:getPoint()
                            local tgt = nearestEnemyGround(enemySide, fp.x, fp.z)
                            if tgt then
                                local h = land.getHeight({ x = tgt.x, y = tgt.z }) or tgt.y
                                trigger.action.smoke({ x = tgt.x, y = h, z = tgt.z }, WHITE_SMOKE)
                                pcall(
                                    trigger.action.outTextForCoalition,
                                    side,
                                    "FAC: target marked with willie pete -- cleared hot.",
                                    20
                                )
                            end
                        end
                    end
                end
            end
        end)
        if not ok then
            env.warning("vietnamops: FAC tick error (continuing): " .. tostring(err))
        end
        return timer.getTime() + FAC_INTERVAL
    end

    timer.scheduleFunction(facTick, {}, timer.getTime() + FAC_INTERVAL)
    env.info(string.format(
        "DCSRetribution|Vietnam Ops - FAC(A) marking armed (type %s, range %.0fm, every %ds)",
        FAC_TYPE, FAC_RANGE, FAC_INTERVAL))
end

-------------------------------------------------------------------------------
-- Snake and nape: low-level napalm CAS delivery
--
-- The iconic Vietnam close-air-support pass: an attack aircraft rolls in low and fast and
-- lays a wall of fire ("snake" = Snakeye retarded bombs, "nape" = napalm) across the enemy.
-- Like the flak gauntlet and FAC, the runtime discovers the delivering aircraft itself --
-- an airborne attack plane (DCS "Attack airplanes" attribute) that is LOW (below the run-in
-- ceiling), FAST, and passing close over an alive opposing ground unit -- and lays a napalm
-- swath (a line of fire effects + a modest per-node bite) oriented along the run-in, once
-- per pass (a per-aircraft cooldown). Rewards flying the CAS run in on the deck rather than
-- lobbing from altitude; symmetric (both sides' attack jets). Pure DCS
-- (trigger.action.effectSmokeBig + explosion), pcall-guarded. Gated on
-- dcsRetribution.VietnamOps.snakeNape.
-------------------------------------------------------------------------------
if suite.snakeNape and suite.snakeNape.enabled then
    local CEILING = 500 * FT_TO_M      -- m AGL, at/below this counts as a napalm run (option in ft)
    local MIN_SPEED = 180 * KTS_TO_MS  -- m/s ground speed, a fast delivery pass (option in kts;
                                       -- 180 kts keeps a loaded A-1 Skyraider run eligible)
    local DROP_RANGE = 1300 * FT_TO_M  -- m from an enemy ground unit that triggers the lay (option in ft)
    local SWATH_LENGTH = 800 * FT_TO_M -- m, length of the fire line along the run-in (option in ft)
    local FIRE_NODES = 5        -- fire effects laid along the swath
    local FIRE_PRESET = 2       -- effectSmokeBig preset: 1 small .. 4 huge smoke-and-fire
    local FIRE_DENSITY = 0.5    -- 0..1 effect density
    local BURN_TIME = 90        -- s each fire burns before it is stopped
    local BLAST = 40            -- per-node explosion power (napalm's bite on soft targets)
    local COOLDOWN = 25         -- s per aircraft between lays (one pass = one wall of fire)
    if dcsRetribution.plugins and dcsRetribution.plugins.vietnamops then
        local o = dcsRetribution.plugins.vietnamops
        CEILING = (tonumber(o.napeCeilingFt) or 500) * FT_TO_M
        MIN_SPEED = (tonumber(o.napeMinSpeedKts) or 180) * KTS_TO_MS
        DROP_RANGE = (tonumber(o.napeDropRangeFt) or 1300) * FT_TO_M
        SWATH_LENGTH = (tonumber(o.napeSwathLengthFt) or 800) * FT_TO_M
        FIRE_NODES = tonumber(o.napeFireNodes) or FIRE_NODES
        BLAST = tonumber(o.napeBlastPower) or BLAST
    end

    local POLL = 2              -- s between delivery-pass evaluations
    local JITTER = 20           -- m random scatter per fire/impact node
    local fireId = 0            -- unique-name counter for effectSmokeBig / stopEffect

    local function napeOpposite(side)
        if side == coalition.side.RED then
            return coalition.side.BLUE
        end
        return coalition.side.RED
    end

    -- Run-in heading (radians) in the (north, east) frame from the aircraft velocity, or
    -- nil if it is too slow to read a direction.
    local function runInHeading(u)
        local v = u:getVelocity()
        if not v then
            return nil
        end
        if math.sqrt(v.x * v.x + v.z * v.z) < 1 then
            return nil
        end
        return math.atan2(v.z, v.x)  -- atan2(east, north)
    end

    -- Nearest alive opposing ground unit within DROP_RANGE of (fx, fz) [north, east].
    local function nearestEnemyGround(enemySide, fx, fz)
        local best, bestD = nil, nil
        for _, grp in pairs(coalition.getGroups(enemySide, Group.Category.GROUND) or {}) do
            for _, u in pairs(grp:getUnits() or {}) do
                if u:isExist() and u:getLife() > 0 then
                    local p = u:getPoint()
                    local dx, dz = p.x - fx, p.z - fz
                    local d2 = dx * dx + dz * dz
                    if d2 <= (DROP_RANGE * DROP_RANGE) and (not bestD or d2 < bestD) then
                        best, bestD = p, d2
                    end
                end
            end
        end
        return best
    end

    -- Lay a line of fire across (cx, cz) [north, east] oriented along headingRad.
    local function layNapalm(cx, cz, headingRad)
        local cosH, sinH = math.cos(headingRad), math.sin(headingRad)
        local span = (FIRE_NODES > 1) and (FIRE_NODES - 1) or 1
        for i = 0, FIRE_NODES - 1 do
            local along = (i / span - 0.5) * SWATH_LENGTH
            local north = cx + along * cosH + math.random(-JITTER, JITTER)
            local east = cz + along * sinH + math.random(-JITTER, JITTER)
            local h = land.getHeight({ x = north, y = east }) or 0
            local pt = { x = north, y = h, z = east }
            fireId = fireId + 1
            local ename = "vnnape-" .. fireId
            pcall(trigger.action.effectSmokeBig, pt, FIRE_PRESET, FIRE_DENSITY, ename)
            timer.scheduleFunction(function()
                pcall(trigger.action.stopEffect, ename)
                return nil
            end, {}, timer.getTime() + BURN_TIME)
            if BLAST > 0 then
                trigger.action.explosion(pt, BLAST)
            end
        end
    end

    local lastLay = {}  -- unit name -> last-lay time (per-aircraft cooldown)

    local function napeTick()
        local ok, err = pcall(function()
            local now = timer.getTime()
            for _, side in pairs({ coalition.side.RED, coalition.side.BLUE }) do
                local enemySide = napeOpposite(side)
                for _, grp in pairs(coalition.getGroups(side, Group.Category.AIRPLANE) or {}) do
                    for _, u in pairs(grp:getUnits() or {}) do
                        if u:isExist() and u:getLife() > 0 and u:inAir()
                            and u:hasAttribute("Attack airplanes") then
                            local name = u:getName()
                            if not lastLay[name] or (now - lastLay[name]) >= COOLDOWN then
                                local p = u:getPoint()
                                local agl = p.y - (land.getHeight({ x = p.x, y = p.z }) or 0)
                                local v = u:getVelocity()
                                local spd = v and math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z) or 0
                                if agl <= CEILING and spd >= MIN_SPEED then
                                    local tgt = nearestEnemyGround(enemySide, p.x, p.z)
                                    if tgt then
                                        local hdg = runInHeading(u) or 0
                                        layNapalm(tgt.x, tgt.z, hdg)
                                        lastLay[name] = now
                                        pcall(
                                            trigger.action.outTextForCoalition,
                                            side,
                                            "SNAKE AND NAPE -- napalm on the deck.",
                                            15
                                        )
                                    end
                                end
                            end
                        end
                    end
                end
            end
        end)
        if not ok then
            env.warning("vietnamops: snake-and-nape tick error (continuing): " .. tostring(err))
        end
        return timer.getTime() + POLL
    end

    timer.scheduleFunction(napeTick, {}, timer.getTime() + POLL)
    env.info(string.format(
        "DCSRetribution|Vietnam Ops - Snake and nape armed (ceiling %.0fm AGL, min speed %.0fm/s, "
            .. "drop range %.0fm, swath %.0fm x %d nodes, blast %d)",
        CEILING, MIN_SPEED, DROP_RANGE, SWATH_LENGTH, FIRE_NODES, BLAST))
end
