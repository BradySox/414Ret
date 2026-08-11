-------------------------------------------------------------------------------------------------------------------------------------------------------------
-- Recon -> BDA capture (§12). ONE mechanism for player and AI both; the MOOSE
-- Ops.TARS split was cut 2026-08-05. Design is in docs/dev/414th-features.md §12.
--
-- Reads dcsRetribution.Recon (game/missiongenerator/reconluadata.py) and writes the
-- shared tars_recon_captures ledger the debrief already parses.
--
-- The load-bearing parts:
--
--  * CAPTURE on overfly, CUE on landing. Missions routinely end before flights land,
--    so gating the take on touchdown would silently destroy most recon. The cue is
--    cosmetic -- a flight that never lands still counts its capture.
--  * The sensor radius is degraded by altitude and by campaign cloud cover, so a high
--    fast pass resolves less than a real recon profile.
--  * One-shot per flight: shot down or aborting before the target confirms nothing.
-------------------------------------------------------------------------------------------------------------------------------------------------------------

env.info("DCSRetribution|Recon plugin - configuration")

if not (dcsRetribution and dcsRetribution.Recon and dcsRetribution.Recon.flights) then
    env.info("DCSRetribution|Recon plugin - no Recon data; skipping")
    return
end

tars_recon_captures = tars_recon_captures or {}

local TRIGGER_RANGE = 5 * 1852  -- m: the flight must close within this of the target
local CAPTURE_CAP = 25          -- max units recorded per recon flight
local POLL = 10                 -- s between position checks
local CUE_SECONDS = 20
-- Altitude degradation. At or below OPTIMAL_ALT the sensor reads at full radius; by
-- CEILING_ALT it is down to MIN_ALT_FACTOR. A recon profile is a real profile.
local OPTIMAL_ALT = 6000        -- m AGL (~20,000 ft)
local CEILING_ALT = 12000       -- m AGL (~40,000 ft)
local MIN_ALT_FACTOR = 0.4
if dcsRetribution.plugins and dcsRetribution.plugins.recon then
    local o = dcsRetribution.plugins.recon
    if o.triggerRangeNm ~= nil then
        TRIGGER_RANGE = (tonumber(o.triggerRangeNm) or 5) * 1852
    end
    CAPTURE_CAP = tonumber(o.captureCap) or CAPTURE_CAP
    POLL = tonumber(o.pollS) or POLL
    if o.optimalAltFt ~= nil then
        OPTIMAL_ALT = (tonumber(o.optimalAltFt) or 20000) * 0.3048
    end
    if o.ceilingAltFt ~= nil then
        CEILING_ALT = (tonumber(o.ceilingAltFt) or 40000) * 0.3048
    end
    if o.minAltitudeFactor ~= nil then
        -- Authored as a PERCENT in plugin.json (spinners read better that way);
        -- the maths here wants a fraction.
        local pct = tonumber(o.minAltitudeFactor)
        if pct then
            MIN_ALT_FACTOR = math.max(0.01, math.min(1.0, pct / 100))
        end
    end
end

local CLOUD_FACTOR = tonumber(dcsRetribution.Recon.cloudFactor) or 1.0

-- How much of its sensor reach the aircraft keeps at this height. Flat at full radius up
-- to OPTIMAL_ALT, then falls linearly to MIN_ALT_FACTOR at CEILING_ALT and stays there.
local function altitudeFactor(agl)
    if agl <= OPTIMAL_ALT then
        return 1.0
    end
    if agl >= CEILING_ALT then
        return MIN_ALT_FACTOR
    end
    local span = CEILING_ALT - OPTIMAL_ALT
    if span <= 0 then
        return MIN_ALT_FACTOR
    end
    return 1.0 - (1.0 - MIN_ALT_FACTOR) * ((agl - OPTIMAL_ALT) / span)
end

-- Record the enemy (RED -- recon flights are blue-gated in Python) ground + ship units
-- within `radius` of (tx, tz) [north, east] into the shared BDA ledger. Returns the count.
local function captureAt(tx, tz, radius)
    local recorded = 0
    local r2 = radius * radius
    local cats = { Group.Category.GROUND, Group.Category.SHIP }
    for _, cat in pairs(cats) do
        for _, grp in pairs(coalition.getGroups(coalition.side.RED, cat) or {}) do
            for _, u in pairs(grp:getUnits() or {}) do
                if recorded >= CAPTURE_CAP then
                    break
                end
                if u:isExist() and u:getLife() > 0 then
                    local p = u:getPoint()
                    local dx, dz = p.x - tx, p.z - tz
                    if (dx * dx + dz * dz) <= r2 then
                        tars_recon_captures[#tars_recon_captures + 1] = {
                            unit = u:getName(),
                            life = u:getLife(),
                            type = u:getTypeName(),
                        }
                        recorded = recorded + 1
                    end
                end
            end
            if recorded >= CAPTURE_CAP then
                break
            end
        end
        if recorded >= CAPTURE_CAP then
            break
        end
    end
    if recorded > 0 then
        dirty_state = true  -- make dcs_retribution.lua flush the new captures into state.json
    end
    return recorded
end

-- Cues held until the flight lands. Keyed by group name; the landing handler drains them.
local pendingCues = {}

local function fireCue(gname)
    local cue = pendingCues[gname]
    if cue == nil then
        return
    end
    pendingCues[gname] = nil
    pcall(trigger.action.outTextForCoalition, coalition.side.BLUE, cue, CUE_SECONDS)
    env.info("DCSRetribution|Recon - cue delivered on landing for '" .. tostring(gname) .. "'")
end

-- The take is read out when it gets home, not over the target.
local landingHandler = {}
function landingHandler:onEvent(event)
    if event == nil or event.id ~= world.event.S_EVENT_LAND then
        return
    end
    local ok, err = pcall(function()
        local unit = event.initiator
        if unit == nil or not unit.getGroup then
            return
        end
        local grp = unit:getGroup()
        if grp == nil then
            return
        end
        fireCue(grp:getName())
    end)
    if not ok then
        env.warning("recon: landing handler error (continuing): " .. tostring(err))
    end
end
world.addEventHandler(landingHandler)

local function watch(entry)
    local gname = entry.group
    local tx = tonumber(entry.x)  -- north
    local tz = tonumber(entry.y)  -- east
    if not gname or not tx or not tz then
        return
    end
    -- Display identity for the coalition cue: the flight's callsign+type and the target
    -- it photographed. Falls back to the raw group name so a record emitted by an older
    -- generator still reads sanely.
    local label = entry.label or tostring(gname)
    local targetName = entry.target
    local sensorRange = (tonumber(entry.sensorNm) or 2) * 1852
    local done = false

    local function tick()
        if done then
            return nil
        end
        local ok, err = pcall(function()
            local g = Group.getByName(gname)
            if g == nil or g:getSize() == 0 then
                done = true  -- flight gone (destroyed or bubble-culled after RTB): no BDA
                return
            end
            local u = g:getUnit(1)
            if u == nil or not u:isExist() then
                return  -- transient; keep polling
            end
            local p = u:getPoint()
            local dx, dz = p.x - tx, p.z - tz
            if (dx * dx + dz * dz) <= (TRIGGER_RANGE * TRIGGER_RANGE) then
                done = true  -- one-shot: the flight has reached (overflown) its target
                local agl = p.y - (land.getHeight({ x = p.x, y = p.z }) or 0)
                local radius = sensorRange * altitudeFactor(agl) * CLOUD_FACTOR
                local n = captureAt(tx, tz, radius)
                if n > 0 then
                    local where = ""
                    if targetName and targetName ~= "" then
                        where = " at " .. tostring(targetName)
                    end
                    -- Held until the flight lands: the take is read out once it is home.
                    pendingCues[gname] = string.format(
                        "RECON: %s confirmed BDA on %d target(s)%s.", label, n, where
                    )
                    env.info("DCSRetribution|Recon - '" .. tostring(gname)
                        .. "' captured " .. n .. " unit(s)"
                        .. (targetName and (" at " .. tostring(targetName)) or "")
                        .. string.format(" (agl %.0fm, radius %.0fm)", agl, radius))
                end
            end
        end)
        if not ok then
            env.warning("recon: tick error (continuing): " .. tostring(err))
        end
        if done then
            return nil
        end
        return timer.getTime() + POLL
    end

    timer.scheduleFunction(tick, {}, timer.getTime() + POLL)
end

local count = 0
for _, entry in pairs(dcsRetribution.Recon.flights) do
    watch(entry)
    count = count + 1
end
env.info(string.format(
    "DCSRetribution|Recon armed for %d recon flight(s) "
        .. "(trigger %.1f NM, cap %d, cloud factor %.2f)",
    count, TRIGGER_RANGE / 1852, CAPTURE_CAP, CLOUD_FACTOR))
