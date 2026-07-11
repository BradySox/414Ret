---------------------------------------------------------------------------------------------------
-- Air-droppable minefields (CLAUDE.md 57) -- runtime.
--
-- DCS has no mine object, so we FAKE area mining. When a blue aircraft air-drops the designated
-- cluster dispenser (CBU-99, carried only by the "Aerial Minefield" loadout), the impact area
-- becomes a scripted proximity minefield. Any enemy (RED) ground unit -- a supply convoy -- that
-- drives inside a field's radius trips a mine: one trigger.action.explosion at the vehicle, one
-- charge spent. Each unit trips at most one mine (a slow convoy does not machine-gun a single
-- field), and a field with its charges exhausted clears. Fields are marked on the F10 map for the
-- friendly (BLUE) coalition only -- the enemy never sees them.
--
-- No phantom spawns / no invented losses: a mine kills a REAL convoy unit, so the loss is recorded
-- natively at debrief (dead convoy units never arrive). This script owns no kills beyond producing
-- the explosion. Blue-only (v1): red does not lay mines, and blue ground never trips them.
--
-- Two ways a field comes to exist:
--   * a drop THIS mission -- an S_EVENT_SHOT of the dispenser, tracked to its ground impact (the
--     Splash Damage / snake-and-nape land.getIP pattern), lays a field there; and
--   * a persisted field from a PRIOR turn -- dcsRetribution.minefields.fields, re-armed at load
--     (that emitter is Phase 2; absent in Phase 1, so the seed loop is simply empty).
--
-- Reads plugin options from dcsRetribution.plugins.minefields. Definition order matters
-- (Lua 5.1): helpers precede use. pcall-guarded throughout so a hiccup never takes the mission
-- down.
---------------------------------------------------------------------------------------------------

-- Defaults (metric). Overridable via the plugin options.
local RADIUS = 200 -- m: minefield radius
local CHARGES = 6 -- mines per air-dropped field
local TRIP_CHANCE = 0.6 -- probability a crossing unit trips a mine on a given scan (density)
local POWER = 100 -- explosion power (kg TNT eq): mobility-kills soft / light vehicles
local SCAN = 3 -- s between proximity scans
local COOLDOWN = 4 -- s minimum between two detonations in the same field (spacing)
local GRACE = 60 -- s before a field can detonate (no load-time artifacts)
local WEAPON_PATTERNS = "CBU_99" -- dispenser weapon type-name match (comma-separated substrings)
local TRACK_STEP = 0.5 -- s: weapon-track sample step
local MAX_TRACK = 60 -- s: give up tracking a released weapon after this

if dcsRetribution and dcsRetribution.plugins and dcsRetribution.plugins.minefields then
    local o = dcsRetribution.plugins.minefields
    RADIUS = tonumber(o.fieldRadiusM) or RADIUS
    CHARGES = tonumber(o.chargesPerField) or CHARGES
    if tonumber(o.tripChancePct) then
        TRIP_CHANCE = tonumber(o.tripChancePct) / 100
    end
    POWER = tonumber(o.detonationPower) or POWER
    SCAN = tonumber(o.scanIntervalS) or SCAN
    COOLDOWN = tonumber(o.detonationCooldownS) or COOLDOWN
    GRACE = tonumber(o.startGraceS) or GRACE
    if type(o.weaponPatterns) == "string" and o.weaponPatterns ~= "" then
        WEAPON_PATTERNS = o.weaponPatterns
    end
end

local function num(v)
    return tonumber(v) or 0
end

-- Dispenser matcher: lowercased plain-text finds against the weapon type name.
local patterns = {}
for pat in string.gmatch(WEAPON_PATTERNS, "[^,]+") do
    pat = string.gsub(string.gsub(pat, "^%s+", ""), "%s+$", "")
    if pat ~= "" then
        patterns[#patterns + 1] = string.lower(pat)
    end
end

local function isDispenser(typeName)
    local t = string.lower(typeName or "")
    if t == "" then
        return false
    end
    for i = 1, #patterns do
        if string.find(t, patterns[i], 1, true) then
            return true
        end
    end
    return false
end

local fields = {} -- active minefields: { x, z, radius, charges, tripped = {}, lastBoom, markId }
local markSeq = 74200 -- F10 mark id base (high to avoid collisions)
local scanArmed = false

-- One live F10 map mark per field for the friendly coalition, so the player can find where they
-- (or their AI) mined.
local function addMark(f, laid)
    markSeq = markSeq + 1
    f.markId = markSeq
    pcall(function()
        local h = land.getHeight({ x = f.x, y = f.z }) or 0
        local label = laid and "Minefield (laid)" or "Minefield"
        trigger.action.markToCoalition(
            f.markId,
            label,
            { x = f.x, y = h, z = f.z },
            coalition.side.BLUE,
            false,
            nil
        )
    end)
end

local function removeMark(f)
    if f.markId then
        pcall(trigger.action.removeMark, f.markId)
    end
end

-- Every alive RED ground unit within radius of (cx, cz). getPoint: x = north, z = east.
local function enemyGroundNear(cx, cz, radius)
    local out = {}
    local r2 = radius * radius
    local ok, groups = pcall(coalition.getGroups, coalition.side.RED, Group.Category.GROUND)
    if not (ok and type(groups) == "table") then
        return out
    end
    for _, g in ipairs(groups) do
        if g and g:isExist() then
            for _, u in ipairs(g:getUnits() or {}) do
                if u and u:isExist() then
                    local p = u:getPoint()
                    if p then
                        local dx, dz = cx - p.x, cz - p.z
                        if (dx * dx + dz * dz) <= r2 then
                            out[#out + 1] = u
                        end
                    end
                end
            end
        end
    end
    return out
end

-- Trip one mine against a unit: an explosion at its position, one charge spent, the unit marked
-- so it trips at most once.
local function detonate(f, unit)
    local p = unit:getPoint()
    pcall(trigger.action.explosion, p, POWER)
    f.tripped[unit:getName()] = true
    f.charges = f.charges - 1
    f.lastBoom = timer.getTime()
    pcall(
        trigger.action.outTextForCoalition,
        coalition.side.BLUE,
        "MINE STRIKE -- an enemy vehicle hit a minefield.",
        10
    )
end

-- One scan pass over every active field: exhausted fields clear; each other field may trip one
-- mine (paced by the cooldown) against a fresh crossing unit.
local function scanTick()
    local now = timer.getTime()
    local i = 1
    while i <= #fields do
        local f = fields[i]
        if f.charges <= 0 then
            removeMark(f)
            table.remove(fields, i)
        else
            if not f.lastBoom or (now - f.lastBoom) >= COOLDOWN then
                for _, u in ipairs(enemyGroundNear(f.x, f.z, f.radius)) do
                    if not f.tripped[u:getName()] and math.random() < TRIP_CHANCE then
                        detonate(f, u)
                        break -- one detonation per field per scan (spacing)
                    end
                end
            end
            i = i + 1
        end
    end
    if #fields == 0 then
        scanArmed = false
        return nil -- nothing left to watch; re-armed when the next field is laid
    end
    return now + SCAN
end

-- Start the scan loop if it is not already running; the first pass is held until the grace so a
-- persisted field never detonates the instant the mission loads.
local function ensureScan()
    if scanArmed then
        return
    end
    scanArmed = true
    local first = timer.getTime() + SCAN
    if first < GRACE then
        first = GRACE
    end
    timer.scheduleFunction(function()
        local ok, nextT = pcall(scanTick)
        if not ok then
            env.warning("minefields: scan error (continuing): " .. tostring(nextT))
            scanArmed = false
            return nil
        end
        return nextT
    end, {}, first)
end

local function addField(x, z, radius, charges, laid)
    local f = {
        x = x,
        z = z,
        radius = radius,
        charges = charges,
        tripped = {},
        lastBoom = nil,
    }
    fields[#fields + 1] = f
    addMark(f, laid)
    ensureScan()
    return f
end

---------------------------------------------------------------------------------------------------
-- Dispenser-drop detection: track the released weapon to its ground impact, lay a field there.
---------------------------------------------------------------------------------------------------

local tracked = {} -- in-flight dispensers: { wpn, pos, vel, shotTime }
local trackerArmed = false

-- Resolve a vanished weapon's impact point from its last sampled position/velocity: terrain-
-- intersect along the final flight path (the Splash Damage land.getIP pattern), falling back to
-- the last position snapped to ground height.
local function resolveImpact(track)
    local p, v = track.pos, track.vel
    if not p then
        return nil
    end
    if v then
        local spd = math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z)
        if spd > 1 then
            local dir = { x = v.x / spd, y = v.y / spd, z = v.z / spd }
            local okIp, ip = pcall(land.getIP, p, dir, math.max(spd * 0.5, 100))
            if okIp and ip then
                return ip
            end
        end
    end
    local h = land.getHeight({ x = p.x, y = p.z }) or 0
    return { x = p.x, y = h, z = p.z }
end

local function mineTrack()
    local now = timer.getTime()
    local i = 1
    while i <= #tracked do
        local track = tracked[i]
        local okExist, exists = pcall(function()
            return track.wpn:isExist()
        end)
        if okExist and exists then
            local okSample, p, v = pcall(function()
                return track.wpn:getPoint(), track.wpn:getVelocity()
            end)
            if okSample then
                track.pos = p or track.pos
                track.vel = v or track.vel
            end
            if (now - track.shotTime) > MAX_TRACK then
                table.remove(tracked, i)
            else
                i = i + 1
            end
        else
            local pt = resolveImpact(track)
            if pt then
                addField(pt.x, pt.z, RADIUS, CHARGES, true)
                pcall(
                    trigger.action.outTextForCoalition,
                    coalition.side.BLUE,
                    "MINEFIELD laid -- marked on the F10 map.",
                    15
                )
            end
            table.remove(tracked, i)
        end
    end
    if #tracked == 0 then
        trackerArmed = false
        return nil
    end
    return now + TRACK_STEP
end

local function mineTrackTick()
    local ok, err = pcall(mineTrack)
    if not ok then
        env.warning("minefields: track error (continuing): " .. tostring(err))
        trackerArmed = false
        return nil
    end
    if trackerArmed then
        return timer.getTime() + TRACK_STEP
    end
    return nil
end

-- Release gate: a blue drop of the dispenser starts a track. Any other weapon, or a red drop
-- (blue-only v1), is ignored -- the ordnance is the eligibility, no delivery-profile gate (mines
-- may be dropped from any run).
local function onShot(event)
    if event.id ~= world.event.S_EVENT_SHOT then
        return
    end
    local wpn, shooter = event.weapon, event.initiator
    if not (wpn and shooter) then
        return
    end
    local okName, typeName = pcall(function()
        return wpn:getTypeName()
    end)
    if not (okName and isDispenser(typeName)) then
        return
    end
    local okSide, side = pcall(function()
        return shooter:getCoalition()
    end)
    if not (okSide and side == coalition.side.BLUE) then
        return
    end
    tracked[#tracked + 1] = { wpn = wpn, pos = nil, vel = nil, shotTime = timer.getTime() }
    if not trackerArmed then
        trackerArmed = true
        timer.scheduleFunction(mineTrackTick, {}, timer.getTime() + TRACK_STEP)
    end
end

---------------------------------------------------------------------------------------------------
-- Arm.
---------------------------------------------------------------------------------------------------

-- Re-arm persisted fields from prior turns (Phase 2; the emitter is absent in Phase 1).
if
    dcsRetribution
    and dcsRetribution.minefields
    and type(dcsRetribution.minefields.fields) == "table"
then
    for _, pf in ipairs(dcsRetribution.minefields.fields) do
        local charges = num(pf.charges)
        if charges > 0 then
            local radius = num(pf.radius)
            if radius <= 0 then
                radius = RADIUS
            end
            addField(num(pf.x), num(pf.z), radius, charges, false)
        end
    end
end

world.addEventHandler({
    onEvent = function(self, event)
        local ok, err = pcall(onShot, event)
        if not ok then
            env.warning("minefields: shot handler error (continuing): " .. tostring(err))
        end
    end,
})

env.info(string.format(
    "DCSRetribution|Minefields armed (dispenser '%s', radius %.0fm, %d charges/field, power %d)",
    WEAPON_PATTERNS,
    RADIUS,
    CHARGES,
    POWER
))
