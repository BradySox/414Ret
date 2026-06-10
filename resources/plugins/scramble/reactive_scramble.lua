-- ============================================================================
-- REACTIVE SCRAMBLE v2.2  (Retribution GCI Scramble Plugin)
-- Bundled automatically into every Retribution-generated .miz that has a
-- non-empty RED untasked-aircraft scramble pool.
-- ============================================================================
--
-- Retribution spawns each RED squadron's leftover ("untasked") aircraft cold on
-- the ramp as UNCONTROLLED groups — parked, engines off, no route. The mission
-- generator records the air-to-air-capable ones in dcsRetribution.scramble_pool.
--
-- This script holds those groups dormant until a Blue aircraft penetrates RED
-- airspace (the dcsRetribution.scramble_border polygon), then wakes the nearest
-- available one (StartUncontrolled) and tasks it to intercept (EngageTargets).
-- When no border polygon is supplied it falls back to the legacy behaviour:
-- a Blue aircraft detected by the RED radar network within CFG_engageRadius.
--
-- Cold-ramp behaviour is intentional: an idle group does a full cold start,
-- taxis, takes off, and hunts. Nothing flies until a threat appears.
--
-- ── API NOTES ───────────────────────────────────────────────────────────────
--  GROUP:StartUncontrolled() — issues the {id='Start'} command to a parked
--                              uncontrolled group (cold start + taxi + takeoff)
--  ctrl:setTask()            — replaces the entire task so the group hunts air
--  EngageTargets             — correct DCS task id for air intercept
-- ============================================================================

local CFG_scanInterval   = 15     -- seconds between threat scans
local CFG_engageRadius   = 95000  -- metres (~51 nm); radar-range detection fallback
local CFG_interceptRange = 185000 -- metres (~100 nm); how far a scrambled QRA pursues
local CFG_reengageDelay  = 180    -- seconds before a busy group re-qualifies
local CFG_spawnDelay     = 5.0    -- seconds after Start before tasking the intercept
local CFG_debug          = true   -- periodic status line in dcs.log (radars/border)

-- ── Retribution plugin config override ────────────────────────────────────
-- If a dcsRetribution.plugins.scramble block exists, apply it on the next tick
-- after mission-start data triggers have fired.
-- CFG_scanInterval is intentionally excluded — the SCHEDULER interval is
-- captured at creation time and cannot be changed after the fact.
timer.scheduleFunction(function()
    if not (dcsRetribution and dcsRetribution.plugins and dcsRetribution.plugins.scramble) then return end
    local c = dcsRetribution.plugins.scramble
    if c.engageRadius   ~= nil then CFG_engageRadius   = c.engageRadius * 1852 end  -- NM → metres
    if c.interceptRange ~= nil then CFG_interceptRange = c.interceptRange * 1852 end -- NM → metres
    if c.reengageDelay  ~= nil then CFG_reengageDelay  = c.reengageDelay end
end, nil, timer.getTime() + 0)

local _groups = {}   -- name -> record
local _border = nil  -- list of { x=, z= } points (RED airspace polygon) or nil

-- ── UTILITIES ────────────────────────────────────────────────────────────────

local function log(msg) BASE:E("=== SCRAMBLE: " .. tostring(msg)) end

local function dist3D(p1, p2)
    local dx, dy, dz = p1.x-p2.x, (p1.y or 0)-(p2.y or 0), p1.z-p2.z
    return math.sqrt(dx*dx + dy*dy + dz*dz)
end

-- Ray-casting point-in-polygon on the map plane (DCS x / z). poly is a list of
-- { x=, z= } vertices (the buffered convex hull of RED control points).
local function pointInPolygon(p, poly)
    local inside, n = false, #poly
    local j = n
    for i = 1, n do
        local xi, zi = poly[i].x, poly[i].z
        local xj, zj = poly[j].x, poly[j].z
        if ((zi > p.z) ~= (zj > p.z))
           and (p.x < (xj - xi) * (p.z - zi) / (zj - zi) + xi) then
            inside = not inside
        end
        j = i
    end
    return inside
end

-- A Blue contact is a threat once it crosses into RED airspace. Border crossing
-- is the primary trigger; raw radar range is the fallback when no border exists.
local function threatActive(pos, radarPts)
    if _border then
        return pointInPolygon(pos, _border)
    end
    for _, rp in ipairs(radarPts) do
        if dist3D(pos, rp) <= CFG_engageRadius then return true end
    end
    return false
end

-- ── TASK APPLICATION ─────────────────────────────────────────────────────────

local function taskIntercept(rec)
    local mg = GROUP:FindByName(rec.name)
    if not mg or not mg:IsAlive() then return end
    rec.group = mg
    mg:OptionROEWeaponFree()
    mg:OptionROTEvadeFire()

    local ctrl = mg:GetController()
    if ctrl then
        ctrl:setTask({
            id     = "EngageTargets",
            params = {
                targetTypes = { "Air" },
                maxDist     = CFG_interceptRange,
                priority    = 0,
            },
        })
    end
end

-- Wake a dormant uncontrolled group and send it to intercept.
--
-- The pool groups are generated with a single TakeOffParking point and no onward
-- route, so StartUncontrolled() alone only spins up engines — it will NOT take
-- off. The EngageTargets task is what makes the cold-started AI taxi, take off
-- and hunt. So: Start first, then (after a short delay so the Start command is
-- processed) push the intercept task, which drives the takeoff.
local function spawnAndIntercept(rec)
    local mg = GROUP:FindByName(rec.name)
    if not mg then
        log("ERROR: cannot find pool group: " .. rec.name)
        return
    end
    rec.group   = mg
    rec.spawned = true
    mg:StartUncontrolled()
    log("Waking dormant group (cold start): " .. rec.name)
    timer.scheduleFunction(function()
        taskIntercept(rec)
        log("Tasked intercept (takeoff + hunt): " .. rec.name)
    end, nil, timer.getTime() + CFG_spawnDelay)
end

-- ── REGISTRATION: read dcsRetribution.scramble_pool ──────────────────────────
-- The pool table is written by a TriggerStart DoScript that runs at mission
-- start; we read it on the next tick so it is guaranteed populated.

timer.scheduleFunction(function()
    local border = dcsRetribution and dcsRetribution.scramble_border
    if border and #border >= 3 then
        _border = border
        log(string.format("RED airspace border loaded (%d vertices)", #border))
    else
        log("No scramble border supplied — falling back to radar-range detection")
    end

    local pool = dcsRetribution and dcsRetribution.scramble_pool
    if not pool then
        log("WARNING: dcsRetribution.scramble_pool not available — no interceptors registered")
        return
    end
    for _, name in ipairs(pool) do
        if not _groups[name] then
            local mg = GROUP:FindByName(name)
            _groups[name] = {
                name       = name,
                group      = mg,      -- uncontrolled groups exist at T=0
                busy       = false,
                lastTasked = 0,
                spawned    = false,
            }
            log("Registered dormant interceptor: " .. name)
        end
    end
end, nil, timer.getTime() + 0.1)

-- ── THREAT SCAN ──────────────────────────────────────────────────────────────

local function getRedRadarPositions()
    local pts = {}
    for _, cat in ipairs({ Group.Category.GROUND, Group.Category.SHIP }) do
        for _, g in ipairs(coalition.getGroups(coalition.side.RED, cat) or {}) do
            if g and g:isExist() then
                for _, u in ipairs(g:getUnits() or {}) do
                    if u and u:isExist() then
                        local d = u:getDesc()
                        if d and d.sensor and d.sensor.radar then
                            pts[#pts + 1] = u:getPoint()
                            break
                        end
                    end
                end
            end
        end
    end
    return pts
end

local function detectBlueThreats(radarPts)
    local threats, seen = {}, {}
    for _, g in ipairs(coalition.getGroups(coalition.side.BLUE, Group.Category.AIRPLANE) or {}) do
        if g and g:isExist() and not seen[g:getName()] then
            local units = g:getUnits()
            local u = units and units[1]
            if u and u:isExist() then
                local pos = u:getPoint()
                if threatActive(pos, radarPts) then
                    threats[#threats + 1] = { group = g, pos = pos }
                    seen[g:getName()] = true
                end
            end
        end
    end
    return threats
end

-- Nearest available pool group to the threat. Dormant groups report their
-- parked position fine, so distance ranking works before they spawn.
local function selectGroup(threatPos)
    local now = timer.getTime()
    local best, bestDist = nil, math.huge
    for _, rec in pairs(_groups) do
        local available = not rec.busy or (now - rec.lastTasked) > CFG_reengageDelay
        local mg = rec.group or GROUP:FindByName(rec.name)
        if available and mg and mg:IsAlive() then
            rec.group = mg
            local u1 = mg:GetUnit(1)
            if u1 and u1:IsAlive() then
                local d = dist3D(u1:GetVec3(), threatPos)
                if d < bestDist then
                    best, bestDist = rec, d
                end
            end
        end
    end
    return best
end

SCHEDULER:New(nil, function()
    local radars = getRedRadarPositions()
    -- With a border polygon we trigger on penetration and don't need radars;
    -- without one we rely on radar detection, so nothing to do with no radars.
    if #radars == 0 and not _border then return end

    local threats = detectBlueThreats(radars)

    if #threats == 0 then
        local now = timer.getTime()
        for _, rec in pairs(_groups) do
            if rec.busy and (now - rec.lastTasked) > CFG_reengageDelay then
                rec.busy = false
                log("Released: " .. rec.name)
            end
        end
        return
    end

    for _, threat in ipairs(threats) do
        local rec = selectGroup(threat.pos)
        if rec then
            local now = timer.getTime()
            if not rec.busy or (now - rec.lastTasked) > CFG_reengageDelay then
                rec.busy       = true
                rec.lastTasked = now
                if rec.spawned then
                    taskIntercept(rec)
                else
                    spawnAndIntercept(rec)
                end
                log("Scramble: " .. rec.name .. " -> " .. threat.group:getName())
                MESSAGE:New("SCRAMBLE: interceptors launching!", 12):ToAll()
            end
        end
    end
end, {}, 10, CFG_scanInterval)

-- ── STARTUP REPORT ───────────────────────────────────────────────────────────

timer.scheduleFunction(function()
    local n = 0
    for _ in pairs(_groups) do n = n + 1 end
    log(string.format("ONLINE — %d dormant interceptor group(s)", n))
    MESSAGE:New(string.format(
        "REACTIVE SCRAMBLE ONLINE: %d dormant interceptor group(s)", n), 12):ToAll()
end, nil, timer.getTime() + 2)

-- ── DEBUG STATUS ─────────────────────────────────────────────────────────────
-- Periodic one-liner so a test run can confirm from dcs.log that detection is
-- wired up (radar count, whether a border loaded, live threats). Set
-- CFG_debug = false to silence.
if CFG_debug then
    timer.scheduleFunction(function()
        local radars = getRedRadarPositions()
        local n = 0
        for _ in pairs(_groups) do n = n + 1 end
        local threats = detectBlueThreats(radars)
        log(string.format(
            "status: groups=%d radars=%d border=%s threats=%d",
            n, #radars, _border and "yes" or "no", #threats))
        return timer.getTime() + 60
    end, nil, timer.getTime() + 25)
end
