---------------------------------------------------------------------------------------------------
-- Carrier deck dressing -- the dynamic respot (feature 72's runtime half).
--
-- The aircraft tier may place deck statics that stand INSIDE the recovery corridor -- OCN's
-- round-down E-2C -- because they only exist while the deck is a launch deck. Statics cannot
-- drive (no AI controller), so "moving" one means striking it below: this script despawns each
-- boat's launch-phase statics (StaticObject:destroy, silent -- the elevator ride, narratively)
-- when EITHER fires first:
--   * the astern cone: any friendly fixed-wing aircraft airborne low astern of the boat
--     (CASE I initial runs up the wake at ~800 ft from ~3 NM; CASE III straight-in from
--     further out -- both enter the cone long before the groove), or
--   * the fallback timer -- launches are long over, clear the deck regardless, so a hazard
--     never waits on detection.
--
-- Reads dcsRetribution.deckDecor (emitted by game/missiongenerator/deckdecorluadata.py: one
-- record per boat -- ship group name, flagship unit name, side, generation-time BRC, and the
-- static unit names to clear); inert when that node is absent. The BRC comes from generation
-- (the boat steams into wind on that course all mission), so no runtime orientation API is
-- needed: the astern bearing is BRC + 180.
--
-- Despawn ONLY -- no spawns, no gameplay-model change, nothing persisted; a dead/absent static
-- name is skipped silently (culled, or already destroyed). pcall-guarded tick so a hiccup never
-- takes the mission down. Definition order matters (Lua 5.1): helpers precede use.
---------------------------------------------------------------------------------------------------

if not (dcsRetribution and dcsRetribution.deckDecor and dcsRetribution.deckDecor.boats) then
    return
end

local boatsData = dcsRetribution.deckDecor.boats

-- Defaults. Overridable via the plugin options (dcsRetribution.plugins.deckdecor).
local POLL_S = 10 -- s between astern-cone checks
local GRACE_S = 60 -- s before the watch starts (startup storm protection)
local FALLBACK_MIN = 35 -- minutes after mission start: clear regardless
local CONE_DIST_NM = 4.5 -- cone range astern
local CONE_ALT_FT = 3000 -- only traffic below this trips the cone
local CONE_HALF_DEG = 50 -- half-angle either side of dead astern
local SHOW_CUE = true -- one-line "deck respotted" message on clear

if dcsRetribution.plugins and dcsRetribution.plugins.deckdecor then
    local o = dcsRetribution.plugins.deckdecor
    POLL_S = tonumber(o.pollS) or POLL_S
    GRACE_S = tonumber(o.graceS) or GRACE_S
    FALLBACK_MIN = tonumber(o.fallbackMin) or FALLBACK_MIN
    CONE_DIST_NM = tonumber(o.coneDistNm) or CONE_DIST_NM
    CONE_ALT_FT = tonumber(o.coneAltFt) or CONE_ALT_FT
    CONE_HALF_DEG = tonumber(o.coneHalfDeg) or CONE_HALF_DEG
    if o.showCue ~= nil then
        SHOW_CUE = o.showCue == true or o.showCue == "true"
    end
end

local AB_MARGIN_S = 300 -- clear this long before the Airboss recovery window
if dcsRetribution.plugins and dcsRetribution.plugins.deckdecor then
    AB_MARGIN_S = tonumber(dcsRetribution.plugins.deckdecor.airbossMarginS) or AB_MARGIN_S
end

local CONE_DIST_M = CONE_DIST_NM * 1852.0
local CONE_ALT_M = CONE_ALT_FT * 0.3048
local CONE_COS = math.cos(math.rad(CONE_HALF_DEG))

-- The Airboss tie-in: the sibling airboss plugin (default ON) schedules its
-- recovery window windowStartOption minutes into the mission and STEERS the
-- boat into wind (with U-turns) while the window is open -- both reasons the
-- corridor must already be clean by then. When that plugin's options are
-- present in the mission, pull the clear deadline forward to window start
-- minus the margin; the astern cone still handles early or unscheduled
-- traffic, and the plain fallback covers missions without Airboss.
local CLEAR_DEADLINE_S = FALLBACK_MIN * 60.0
local DEADLINE_WHY = "fallback timer"
do
    local ab = dcsRetribution.plugins and dcsRetribution.plugins.airboss
    local windowStartMin = ab and tonumber(ab.windowStartOption)
    if windowStartMin then
        local byWindow = windowStartMin * 60.0 - AB_MARGIN_S
        local floorS = GRACE_S + POLL_S
        if byWindow < floorS then
            byWindow = floorS
        end
        if byWindow < CLEAR_DEADLINE_S then
            CLEAR_DEADLINE_S = byWindow
            DEADLINE_WHY = "airboss recovery window"
        end
    end
end

local function log(msg)
    env.info("DECKDECOR|: " .. msg)
end

-- Mutable per-boat state built from the emitted records.
local boats = {}
for i = 1, #boatsData do
    local b = boatsData[i]
    local brc = tonumber(b.brc) or 0
    table.insert(boats, {
        group = tostring(b.group or ""),
        unit = tostring(b.unit or ""),
        side = tonumber(b.side) or 2,
        -- Unit astern vector in map coords (x = north, z = east): the reciprocal
        -- of the BRC the boat steams all mission.
        sternX = -math.cos(math.rad(brc)),
        sternZ = -math.sin(math.rad(brc)),
        clearNames = b.clearNames or {},
        cleared = false,
    })
end

local function boatPosition(boat)
    local grp = Group.getByName(boat.group)
    if not grp or not grp:isExist() then
        return nil
    end
    local units = grp:getUnits()
    for i = 1, #units do
        local u = units[i]
        if u and u:isExist() then
            return u:getPoint()
        end
    end
    return nil
end

local function clearBoat(boat, why)
    boat.cleared = true
    local n = 0
    for i = 1, #boat.clearNames do
        local s = StaticObject.getByName(boat.clearNames[i])
        if s then
            s:destroy()
            n = n + 1
        end
    end
    log(boat.unit .. ": struck " .. n .. " launch-phase static(s) below (" .. why .. ")")
    if SHOW_CUE and n > 0 then
        trigger.action.outTextForCoalition(
            boat.side,
            boat.unit .. " deck respotted for recovery -- the alert aircraft are struck below.",
            8
        )
    end
end

local function approachDetected(boat)
    local bp = boatPosition(boat)
    if bp == nil then
        -- Boat gone (sunk/despawned): nothing to protect, count as done.
        return true
    end
    local groups = coalition.getGroups(boat.side, Group.Category.AIRPLANE)
    for i = 1, #groups do
        local units = groups[i]:getUnits()
        for j = 1, #units do
            local u = units[j]
            if u and u:isExist() and u:inAir() then
                local p = u:getPoint()
                if p.y - bp.y < CONE_ALT_M then
                    local dx = p.x - bp.x
                    local dz = p.z - bp.z
                    local dist = math.sqrt(dx * dx + dz * dz)
                    if dist > 100 and dist < CONE_DIST_M then
                        local cosang = (dx * boat.sternX + dz * boat.sternZ) / dist
                        if cosang > CONE_COS then
                            return true
                        end
                    end
                end
            end
        end
    end
    return false
end

local function tick()
    local pending = 0
    for i = 1, #boats do
        local boat = boats[i]
        if not boat.cleared then
            if timer.getTime() >= CLEAR_DEADLINE_S then
                clearBoat(boat, DEADLINE_WHY)
            else
                local ok, tripped = pcall(approachDetected, boat)
                if ok and tripped then
                    clearBoat(boat, "recovery traffic astern")
                end
            end
        end
        if not boat.cleared then
            pending = pending + 1
        end
    end
    if pending > 0 then
        return timer.getTime() + POLL_S
    end
    return nil
end

if #boats > 0 then
    timer.scheduleFunction(function(_, _)
        return tick()
    end, {}, timer.getTime() + GRACE_S)
    log("armed -- " .. #boats .. " boat(s), clear by " ..
        string.format("%.0f", CLEAR_DEADLINE_S) .. "s (" .. DEADLINE_WHY .. "), cone " ..
        CONE_DIST_NM .. " NM/" .. CONE_ALT_FT .. " ft astern")
end
