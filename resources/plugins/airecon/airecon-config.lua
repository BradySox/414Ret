-------------------------------------------------------------------------------------------------------------------------------------------------------------
-- AI recon BDA capture for DCS Retribution
--
-- The MOOSE TARS engine that turns a TARPS overflight into a confirmed-BDA capture is
-- PLAYER-ONLY: its birth handler drops any unit that isn't player-crewed. So the campaign's
-- auto-paired AI recon flights fly the recon path but never confirm a single target
-- (checklist G19). This closes that gap without touching the player TARS path.
--
-- The mission generator emits dcsRetribution.AIRecon = { flights = { {group,x,y}, ... } }
-- for each AI-flown, player-coalition (BLUE) TARPS flight + its target point (only when such
-- flights exist, so this plugin no-ops otherwise). Each flight is watched; when its lead
-- unit closes within the trigger range of the target, the enemy (RED) ground units within
-- the capture radius of the target are written into the shared tars_recon_captures ledger --
-- the exact table + schema ({ unit, life, type }) the player film menu feeds, so the
-- Retribution debrief (game/debriefing.py parse_tars_captures -> tars_reconned_tgos) treats
-- an AI recon capture identically to a player one. A recon flight shot down or aborting
-- before the target confirms nothing (one-shot per flight). Vanilla DCS + pcall-guarded.
-------------------------------------------------------------------------------------------------------------------------------------------------------------

env.info("DCSRetribution|AI Recon plugin - configuration")

if not (dcsRetribution and dcsRetribution.AIRecon and dcsRetribution.AIRecon.flights) then
    env.info("DCSRetribution|AI Recon plugin - no AIRecon data; skipping")
    return
end

tars_recon_captures = tars_recon_captures or {}

local TRIGGER_RANGE = 5 * 1852  -- m: the flight must close within this of the target to "photograph" it
local CAPTURE_RADIUS = 2 * 1852 -- m: enemy ground within this of the target is captured (option in NM)
local CAPTURE_CAP = 25          -- max units recorded per recon flight
local POLL = 10                 -- s between position checks
if dcsRetribution.plugins and dcsRetribution.plugins.airecon then
    local o = dcsRetribution.plugins.airecon
    if o.triggerRangeNm ~= nil then
        TRIGGER_RANGE = (tonumber(o.triggerRangeNm) or 5) * 1852
    end
    if o.captureRadiusNm ~= nil then
        CAPTURE_RADIUS = (tonumber(o.captureRadiusNm) or 2) * 1852
    end
    CAPTURE_CAP = tonumber(o.captureCap) or CAPTURE_CAP
    POLL = tonumber(o.pollS) or POLL
end

-- Record the enemy (RED -- recon flights are blue-gated in Python) ground + ship units
-- within CAPTURE_RADIUS of (tx, tz) [north, east] into the shared BDA ledger (the same
-- ground+ship scope the player TARS path photographs). Returns the count.
local function captureAt(tx, tz)
    local recorded = 0
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
                    if (dx * dx + dz * dz) <= (CAPTURE_RADIUS * CAPTURE_RADIUS) then
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

local function watch(entry)
    local gname = entry.group
    local tx = tonumber(entry.x)  -- north
    local tz = tonumber(entry.y)  -- east
    if not gname or not tx or not tz then
        return
    end
    -- Display identity for the coalition cue: the flight's callsign+type and the
    -- target it photographed. Falls back to the raw group name / a generic area so
    -- a record emitted by an older generator still reads sanely.
    local label = entry.label or tostring(gname)
    local targetName = entry.target
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
                local n = captureAt(tx, tz)
                if n > 0 then
                    local where = ""
                    if targetName and targetName ~= "" then
                        where = " at " .. tostring(targetName)
                    end
                    pcall(
                        trigger.action.outTextForCoalition,
                        coalition.side.BLUE,
                        string.format(
                            "TARPS: %s confirmed BDA on %d target(s)%s.",
                            label, n, where
                        ),
                        20
                    )
                    env.info("DCSRetribution|AI Recon - '" .. tostring(gname)
                        .. "' captured " .. n .. " unit(s)"
                        .. (targetName and (" at " .. tostring(targetName)) or ""))
                end
            end
        end)
        if not ok then
            env.warning("airecon: tick error (continuing): " .. tostring(err))
        end
        if done then
            return nil
        end
        return timer.getTime() + POLL
    end

    timer.scheduleFunction(tick, {}, timer.getTime() + POLL)
end

local count = 0
for _, entry in pairs(dcsRetribution.AIRecon.flights) do
    watch(entry)
    count = count + 1
end
env.info(string.format(
    "DCSRetribution|AI Recon armed for %d AI recon flight(s) "
        .. "(trigger %.1f NM, capture %dm, cap %d)",
    count, TRIGGER_RANGE / 1852, CAPTURE_RADIUS, CAPTURE_CAP))
