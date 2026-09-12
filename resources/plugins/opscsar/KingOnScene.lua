-- The King's on-scene systems: a player-flown fixed-wing CSAR C-130J finds the
-- survivor by DF and builds a threat picture for the Sandys and the helicopter.
-- See docs/dev/design/414th-csar-notes.md (the King on-scene section) and §100.
--
-- Reads dcsRetribution.CSAR (downedPilots, rescueFlights, beaconHz) written by
-- luagenerator.generate_csar_data. Loads after OpsCSAR.lua; touches nothing of it.
--
-- Constraints a reader could undo by accident:
--  * The King cues. It never lases, designates, or pushes a task onto an AI flight.
--    Briefs and marks go to PLAYER groups only (the §15 divert lesson).
--  * A threat is reported as a CLASS and a ROUGH position, never a unit type or an
--    exact point -- the fog rule: nothing here names a site's composition.
--  * A fix comes from DF cuts, not from knowing where the pilot is. The survivor's
--    true position is read only to noise a bearing from it, and to snap the fix
--    once the King is inside pod range with line of sight.
--  * math.random is never seeded in the DCS mission environment; the LCG below is
--    the only randomness used, and it is seeded per King so tests are repeatable.

local cfg = dcsRetribution and dcsRetribution.CSAR
if type(cfg) ~= "table" then
    return
end

-- ---------------------------------------------------------------------------
-- Tuning
-- ---------------------------------------------------------------------------
local DF_MAX_RANGE_M = 80 * 1852 -- beacon is receivable inside this
local DF_BEARING_ERROR_DEG = 3 -- each cut is off by up to this much, either way
local MIN_CUT_SEPARATION_DEG = 15 -- two cuts closer than this do not make a fix
local POD_RANGE_M = 15 * 1852 -- inside this with LOS the pod has the survivor
local POD_SWEEP_RANGE_M = 40 * 1852 -- the King must be this close to sweep threats
local SWEEP_RADIUS_M = 8 * 1852 -- around the fix, not around the true survivor
local SWEEP_MAX_THREATS = 5
local THREAT_JITTER_M = 460 -- ~0.25 nm: a cue, not a targeting solution
local TICK_SECONDS = 10
local MSG_SECONDS = 30
local BRIEF_SECONDS = 45
local MARK_ID_BASE = 7100000 -- clear of the c130j ISR marks and MOOSE's

-- ---------------------------------------------------------------------------
-- Small helpers
-- ---------------------------------------------------------------------------
local function log(msg)
    env.info("[KingOnScene] " .. tostring(msg))
end

local function warn(msg)
    env.warning("[KingOnScene] " .. tostring(msg))
end

-- Deterministic per-King randomness (see the file header).
local function makeRng(seed)
    local state = math.floor(seed) % 2147483647
    if state <= 0 then
        state = state + 2147483646
    end
    return function()
        state = (state * 48271) % 2147483647
        return state / 2147483647
    end
end

local function dist2d(a, b)
    local dx, dz = a.x - b.x, a.z - b.z
    return math.sqrt(dx * dx + dz * dz)
end

-- DCS ground coordinates: x north, z east. Bearing in degrees, 0-360.
local function bearingDeg(from, to)
    local brg = math.deg(math.atan2(to.z - from.z, to.x - from.x))
    if brg < 0 then
        brg = brg + 360
    end
    return brg
end

local function normalizeDeg(d)
    d = d % 360
    if d < 0 then
        d = d + 360
    end
    return d
end

local function separationDeg(a, b)
    local d = math.abs(normalizeDeg(a) - normalizeDeg(b))
    if d > 180 then
        d = 360 - d
    end
    return d
end

local function nm(m)
    return m / 1852
end

local function fmtNm(m)
    return string.format("%.1fnm", nm(m))
end

local function fmtBrg(deg)
    return string.format("%03d", math.floor(normalizeDeg(deg) + 0.5) % 360)
end

local function groundPoint(x, z)
    local ok, h = pcall(land.getHeight, { x = x, y = z })
    return { x = x, y = (ok and h) or 0, z = z }
end

local function groupHasPlayer(g)
    if not g or not g.isExist or not g:isExist() then
        return false
    end
    for _, u in ipairs(g:getUnits() or {}) do
        if u and u.isExist and u:isExist() and u.getPlayerName and u:getPlayerName() then
            return true
        end
    end
    return false
end

local function firstAliveUnit(g)
    for _, u in ipairs(g:getUnits() or {}) do
        if u and u.isExist and u:isExist() then
            return u
        end
    end
    return nil
end

-- Line of sight is a pcall because the harness does not model terrain and a
-- missing land.isVisible must read as "visible", not as a dead menu.
local function hasLos(a, b)
    if not land or not land.isVisible then
        return true
    end
    local ok, visible = pcall(land.isVisible, a, b)
    if not ok then
        return true
    end
    return visible ~= false
end

local function sideConst(name)
    if name == "red" then
        return coalition.side.RED
    end
    return coalition.side.BLUE
end

local function enemyOf(side)
    if side == coalition.side.RED then
        return coalition.side.BLUE
    end
    return coalition.side.RED
end

-- ---------------------------------------------------------------------------
-- Mission data
-- ---------------------------------------------------------------------------
local survivors = {} -- id -> { id, name, aircraft, unitName, side, spawnX, spawnZ }
local kings = {} -- groupName -> { groupName, survivorId, side }
local briefable = {} -- { groupName, role, side } for sandy / jolly player flights
local beaconHz = tonumber(cfg.beaconHz) or 0

if type(cfg.downedPilots) == "table" then
    for _, dp in pairs(cfg.downedPilots) do
        if dp.id then
            survivors[dp.id] = {
                id = dp.id,
                name = dp.description or "Downed pilot",
                aircraft = dp.aircraft or "",
                unitName = dp.unitName,
                side = sideConst(dp.coalition),
                spawnX = tonumber(dp.x) or 0,
                spawnZ = tonumber(dp.z) or 0,
            }
        end
    end
end

if type(cfg.rescueFlights) == "table" then
    for _, rf in pairs(cfg.rescueFlights) do
        if rf.groupName and rf.groupName ~= "" then
            local entry = {
                groupName = rf.groupName,
                role = rf.role or "",
                side = sideConst(rf.side),
                survivorId = rf.survivorId,
            }
            if entry.role == "king" and rf.player == "true" then
                kings[entry.groupName] = entry
            elseif entry.role == "sandy" or entry.role == "jolly" then
                table.insert(briefable, entry)
            end
        end
    end
end

if next(kings) == nil then
    log("No player-flown King this mission; on-scene systems idle.")
    return
end

-- Where the survivor is standing, or nil once they are not (rescued, killed).
local function survivorPoint(sv)
    if sv.unitName then
        local u = Unit.getByName(sv.unitName)
        if u and u:isExist() then
            return u:getPoint()
        end
        return nil
    end
    return groundPoint(sv.spawnX, sv.spawnZ)
end

-- ---------------------------------------------------------------------------
-- Per-King state
-- ---------------------------------------------------------------------------
local stations = {} -- groupName -> station
local markCounter = 0

local function nextMarkId()
    markCounter = markCounter + 1
    return MARK_ID_BASE + markCounter
end

local function newStation(entry, gid)
    return {
        groupName = entry.groupName,
        gid = gid,
        side = entry.side,
        survivorId = entry.survivorId,
        rng = makeRng((timer.getTime() * 1000) + gid * 7919),
        cuts = {}, -- { x, z, brg }
        fix = nil, -- { x, z, err }
        snapped = false,
        threats = {}, -- { class, x, z, brg, range }
        marksByGid = {}, -- gid -> { ids }
        passMenu = nil,
        passCmds = {},
    }
end

local function say(st, text, secs)
    trigger.action.outTextForGroup(st.gid, "KING | " .. text, secs or MSG_SECONDS)
end

local function kingPoint(st)
    local g = Group.getByName(st.groupName)
    if not g or not g:isExist() then
        return nil
    end
    local u = firstAliveUnit(g)
    return u and u:getPoint() or nil
end

-- The King's survivor: the one its package was fragged for, else the nearest
-- friendly survivor still on the ground.
local function survivorFor(st)
    local sv = st.survivorId and survivors[st.survivorId]
    if sv and survivorPoint(sv) then
        return sv
    end
    local kp = kingPoint(st)
    local best, bestD = nil, nil
    for _, cand in pairs(survivors) do
        if cand.side == st.side then
            local p = survivorPoint(cand)
            if p then
                local d = kp and dist2d(kp, p) or 0
                if not best or d < bestD then
                    best, bestD = cand, d
                end
            end
        end
    end
    return best
end

local function clearMarksFor(st, gid)
    for _, id in ipairs(st.marksByGid[gid] or {}) do
        trigger.action.removeMark(id)
    end
    st.marksByGid[gid] = {}
end

local function markFor(st, gid, text, point)
    local id = nextMarkId()
    trigger.action.markToGroup(id, text, point, gid, true)
    st.marksByGid[gid] = st.marksByGid[gid] or {}
    table.insert(st.marksByGid[gid], id)
    return id
end

-- ---------------------------------------------------------------------------
-- The fix: intersect DF cuts
-- ---------------------------------------------------------------------------
local function intersectCuts(a, b)
    local ax, az = math.cos(math.rad(a.brg)), math.sin(math.rad(a.brg))
    local bx, bz = math.cos(math.rad(b.brg)), math.sin(math.rad(b.brg))
    local det = ax * bz - az * bx
    if math.abs(det) < 1e-6 then
        return nil
    end
    local dx, dz = b.x - a.x, b.z - a.z
    local t = (dx * bz - dz * bx) / det
    if t < 0 then
        return nil -- behind the King: the cuts do not converge ahead of it
    end
    return { x = a.x + ax * t, z = a.z + az * t }
end

local function computeFix(st)
    local points, bestSep, pairs_ = {}, 0, 0
    for i = 1, #st.cuts do
        for j = i + 1, #st.cuts do
            local sep = separationDeg(st.cuts[i].brg, st.cuts[j].brg)
            if sep >= MIN_CUT_SEPARATION_DEG then
                local p = intersectCuts(st.cuts[i], st.cuts[j])
                if p then
                    table.insert(points, p)
                    pairs_ = pairs_ + 1
                    if sep > bestSep then
                        bestSep = sep
                    end
                end
            end
        end
    end
    if #points == 0 then
        return nil
    end
    local sx, sz = 0, 0
    for _, p in ipairs(points) do
        sx, sz = sx + p.x, sz + p.z
    end
    local est = { x = sx / #points, z = sz / #points }
    -- Error budget: the bearing error projected at the last cut's range, opened
    -- up by poor cut geometry, tightened by averaging more pairs.
    local last = st.cuts[#st.cuts]
    local range = dist2d(last, est)
    local err = range * math.tan(math.rad(DF_BEARING_ERROR_DEG))
        / math.max(math.sin(math.rad(bestSep)), 0.1)
        / math.sqrt(pairs_)
    est.err = math.max(err, 150)
    return est
end

local function describeFix(st)
    if not st.fix then
        return "no fix"
    end
    if st.snapped then
        return "POD CONTACT (exact)"
    end
    return string.format("fix +/- %s (%d cuts)", fmtNm(st.fix.err), #st.cuts)
end

local function drawSurvivorMark(st, gid, sv)
    local p = groundPoint(st.fix.x, st.fix.z)
    local label = st.snapped and "SURVIVOR " .. sv.name .. " (pod contact)"
        or string.format("SURVIVOR %s (est. +/- %s)", sv.name, fmtNm(st.fix.err))
    markFor(st, gid, label, p)
end

-- Inside pod range with line of sight the King simply sees the survivor.
local function tryPodSnap(st, kp, truePoint)
    if dist2d(kp, truePoint) <= POD_RANGE_M and hasLos(kp, truePoint) then
        st.fix = { x = truePoint.x, z = truePoint.z, err = 0 }
        st.snapped = true
        return true
    end
    return false
end

local function takeCut(st)
    local sv = survivorFor(st)
    local kp = kingPoint(st)
    if not sv or not kp then
        say(st, "No survivor on the beacon.")
        return
    end
    local truePoint = survivorPoint(sv)
    local range = dist2d(kp, truePoint)
    if range > DF_MAX_RANGE_M then
        say(st, string.format("Beacon not received. Close to inside %s.", fmtNm(DF_MAX_RANGE_M)))
        return
    end

    if tryPodSnap(st, kp, truePoint) then
        clearMarksFor(st, st.gid)
        drawSurvivorMark(st, st.gid, sv)
        say(st, string.format("Pod contact. %s in sight, %s at %s from us.",
            sv.name, fmtBrg(bearingDeg(kp, truePoint)), fmtNm(range)))
        return
    end

    local noise = (st.rng() * 2 - 1) * DF_BEARING_ERROR_DEG
    local brg = normalizeDeg(bearingDeg(kp, truePoint) + noise)
    table.insert(st.cuts, { x = kp.x, z = kp.z, brg = brg })

    local fix = computeFix(st)
    if fix then
        st.fix = fix
        st.snapped = false
        clearMarksFor(st, st.gid)
        drawSurvivorMark(st, st.gid, sv)
        say(st, string.format(
            "DF cut %d: bearing %s. Fix on %s: %s at %s, %s. Marked on the map.",
            #st.cuts, fmtBrg(brg), sv.name, fmtBrg(bearingDeg(kp, fix)),
            fmtNm(dist2d(kp, fix)), describeFix(st)))
    else
        say(st, string.format(
            "DF cut %d: bearing %s to the beacon. Take another cut from a position at least %d degrees around the survivor for a fix.",
            #st.cuts, fmtBrg(brg), MIN_CUT_SEPARATION_DEG))
    end
end

local function survivorStatus(st)
    local sv = survivorFor(st)
    local kp = kingPoint(st)
    if not sv or not kp then
        say(st, "No survivor on the beacon.")
        return
    end
    local lines = {
        string.format("Survivor: %s (%s)", sv.name, sv.aircraft),
        string.format("Beacon: %.0f kHz", beaconHz / 1000),
        "Fix: " .. describeFix(st),
    }
    if st.fix then
        table.insert(lines, string.format("Fix bears %s at %s from us.",
            fmtBrg(bearingDeg(kp, st.fix)), fmtNm(dist2d(kp, st.fix))))
    end
    say(st, table.concat(lines, "\n"))
end

-- ---------------------------------------------------------------------------
-- The threat sweep: class and rough position, around the fix
-- ---------------------------------------------------------------------------
local CLASS_ORDER = {
    { "SAM", "SAM" }, { "SAM TR", "SAM" }, { "SAM SR", "SAM" }, { "SAM LL", "SAM" },
    { "MANPADS", "MANPADS" },
    { "AAA", "AAA" },
    { "Tanks", "ARMOUR" }, { "IFV", "ARMOUR" }, { "APC", "ARMOUR" },
    { "Armored vehicles", "ARMOUR" },
    { "Infantry", "TROOPS" },
}

local function classify(unit)
    if not unit.hasAttribute then
        return "VEHICLES"
    end
    for _, pair in ipairs(CLASS_ORDER) do
        local ok, has = pcall(unit.hasAttribute, unit, pair[1])
        if ok and has then
            return pair[2]
        end
    end
    return "VEHICLES"
end

local function sweepThreats(st)
    local sv = survivorFor(st)
    local kp = kingPoint(st)
    if not sv or not kp then
        say(st, "No survivor to sweep around.")
        return
    end
    if not st.fix then
        say(st, "No fix yet. Take DF cuts first -- the pod looks where the fix is.")
        return
    end
    if dist2d(kp, st.fix) > POD_SWEEP_RANGE_M then
        say(st, string.format("Fix is outside pod range. Close to inside %s.", fmtNm(POD_SWEEP_RANGE_M)))
        return
    end

    local centre = { x = st.fix.x, z = st.fix.z }
    local found = {}
    for _, g in ipairs(coalition.getGroups(enemyOf(st.side), Group.Category.GROUND) or {}) do
        if g and g.isExist and g:isExist() then
            local nearest, nearestD = nil, nil
            for _, u in ipairs(g:getUnits() or {}) do
                if u and u.isExist and u:isExist() then
                    local d = dist2d(centre, u:getPoint())
                    if not nearest or d < nearestD then
                        nearest, nearestD = u, d
                    end
                end
            end
            if nearest and nearestD <= SWEEP_RADIUS_M then
                local p = nearest:getPoint()
                table.insert(found, {
                    class = classify(nearest),
                    x = p.x, z = p.z, range = nearestD,
                })
            end
        end
    end
    table.sort(found, function(a, b)
        return a.range < b.range
    end)

    st.threats = {}
    for i = 1, math.min(#found, SWEEP_MAX_THREATS) do
        local t = found[i]
        local ang = st.rng() * 2 * math.pi
        local r = st.rng() * THREAT_JITTER_M
        t.x = t.x + math.cos(ang) * r
        t.z = t.z + math.sin(ang) * r
        t.brg = bearingDeg(centre, t)
        t.range = dist2d(centre, t)
        t.index = i
        table.insert(st.threats, t)
    end

    clearMarksFor(st, st.gid)
    drawSurvivorMark(st, st.gid, sv)
    local lines = { string.format("Threat sweep, %s around the fix (%s):", fmtNm(SWEEP_RADIUS_M), describeFix(st)) }
    if #st.threats == 0 then
        table.insert(lines, "No ground threats inside the sweep.")
    end
    for _, t in ipairs(st.threats) do
        local label = string.format("T%d %s ~%s at %s from the survivor", t.index, t.class, fmtNm(t.range), fmtBrg(t.brg))
        table.insert(lines, label)
        markFor(st, st.gid, label, groundPoint(t.x, t.z))
    end
    if #found > SWEEP_MAX_THREATS then
        table.insert(lines, string.format("(%d more beyond the closest %d)", #found - SWEEP_MAX_THREATS, SWEEP_MAX_THREATS))
    end
    say(st, table.concat(lines, "\n"), BRIEF_SECONDS)
end

-- ---------------------------------------------------------------------------
-- Passing the picture to the rescue flights
-- ---------------------------------------------------------------------------
local function briefText(st, sv)
    local lines = { string.format("KING picture for %s (%s):", sv.name, sv.aircraft) }
    if st.fix then
        table.insert(lines, "Survivor " .. describeFix(st) .. " -- marked on your map.")
    else
        table.insert(lines, "Survivor: no fix yet.")
    end
    if #st.threats == 0 then
        table.insert(lines, "Threats: none swept.")
    end
    for _, t in ipairs(st.threats) do
        table.insert(lines, string.format("T%d %s ~%s at %s from the survivor", t.index, t.class, fmtNm(t.range), fmtBrg(t.brg)))
    end
    table.insert(lines, string.format("Beacon %.0f kHz.", beaconHz / 1000))
    return table.concat(lines, "\n")
end

local function passPictureTo(st, gid)
    local sv = survivorFor(st)
    if not sv then
        say(st, "No survivor to brief on.")
        return
    end
    clearMarksFor(st, gid)
    if st.fix then
        drawSurvivorMark(st, gid, sv)
    end
    for _, t in ipairs(st.threats) do
        markFor(st, gid, string.format("T%d %s ~%s at %s from the survivor", t.index, t.class, fmtNm(t.range), fmtBrg(t.brg)),
            groundPoint(t.x, t.z))
    end
    trigger.action.outTextForGroup(gid, briefText(st, sv), BRIEF_SECONDS)
end

-- The player-crewed Sandy and helo groups on the King's side, alive right now.
local function briefableGroups(st)
    local out = {}
    for _, entry in ipairs(briefable) do
        if entry.side == st.side then
            local g = Group.getByName(entry.groupName)
            if groupHasPlayer(g) and g:getID() ~= st.gid then
                table.insert(out, { gid = g:getID(), label = string.upper(entry.role) .. " " .. entry.groupName })
            end
        end
    end
    return out
end

local function rebuildPassMenu(st)
    for _, cmd in ipairs(st.passCmds) do
        missionCommands.removeItemForGroup(st.gid, cmd)
    end
    st.passCmds = {}
    local targets = briefableGroups(st)
    for _, target in ipairs(targets) do
        local cmd = missionCommands.addCommandForGroup(st.gid, target.label, st.passMenu, function()
            passPictureTo(st, target.gid)
            say(st, "Picture passed to " .. target.label .. ".")
        end)
        table.insert(st.passCmds, cmd)
    end
    if #targets > 0 then
        local cmd = missionCommands.addCommandForGroup(st.gid, "All rescue flights", st.passMenu, function()
            for _, target in ipairs(briefableGroups(st)) do
                passPictureTo(st, target.gid)
            end
            say(st, "Picture passed to all rescue flights.")
        end)
        table.insert(st.passCmds, cmd)
    end
end

-- ---------------------------------------------------------------------------
-- Menu and registration
-- ---------------------------------------------------------------------------
local function buildMenu(st)
    local root = missionCommands.addSubMenuForGroup(st.gid, "KING | On-Scene Commander")
    missionCommands.addCommandForGroup(st.gid, "Survivor status", root, function()
        survivorStatus(st)
    end)
    missionCommands.addCommandForGroup(st.gid, "Take DF cut on the beacon", root, function()
        takeCut(st)
    end)
    missionCommands.addCommandForGroup(st.gid, "Threat sweep around the fix", root, function()
        sweepThreats(st)
    end)
    st.passMenu = missionCommands.addSubMenuForGroup(st.gid, "Pass picture to", root)
    missionCommands.addCommandForGroup(st.gid, "Clear my marks", root, function()
        clearMarksFor(st, st.gid)
        say(st, "Marks cleared.")
    end)
    rebuildPassMenu(st)
end

local function registerKing(entry)
    local g = Group.getByName(entry.groupName)
    if not groupHasPlayer(g) then
        return
    end
    local gid = g:getID()
    if stations[entry.groupName] then
        return
    end
    local st = newStation(entry, gid)
    stations[entry.groupName] = st
    buildMenu(st)
    local sv = survivorFor(st)
    if sv then
        say(st, string.format("On-scene systems up. Survivor %s (%s), beacon %.0f kHz. Take DF cuts to fix them.",
            sv.name, sv.aircraft, beaconHz / 1000))
    else
        say(st, "On-scene systems up. No survivor on the beacon.")
    end
    log("Registered King " .. entry.groupName)
end

local function tick()
    for _, entry in pairs(kings) do
        registerKing(entry)
    end
    for _, st in pairs(stations) do
        rebuildPassMenu(st)
    end
    return timer.getTime() + TICK_SECONDS
end

timer.scheduleFunction(function()
    local ok, err = pcall(tick)
    if not ok then
        warn("tick failed: " .. tostring(err))
    end
    return timer.getTime() + TICK_SECONDS
end, nil, timer.getTime() + 1)

log("Loaded; waiting for a player-flown King.")
