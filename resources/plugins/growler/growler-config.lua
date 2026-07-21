-- Growler escort jamming (EA-18G) -- runtime for the ESCORT_JAMMER role.
--
-- Descends from the Timberwolf/Matador EW script family (the same lineage as the
-- C-130 Mission Systems script and upstream's player-only ewrj plugin), reshaped
-- into an AI auto-policy: the "AI can't use it" folklore was a wiring gap -- the
-- effect model is geometry + dice and needs no AI intelligence, only a decision
-- layer, which this file is.
--
-- Effects (ROE ONLY -- radar emissions are NEVER toggled; enableEmission crashed
-- DCS in the C-130 line and MANTIS owns alarm/EMCON state):
--  * Defensive bubble: a radar-guided missile closing on the Growler or any
--    protected package member rolls per second against a distance-banded spoof
--    chance centred on the Growler -- closer to the jammer is harder to survive
--    as a missile. A spoofed missile is destroyed silently (no explosion at the
--    launcher; a minimum-travel guard prevents "explodes on launch").
--  * Offensive pulse: a radar SAM group inside jamming range whose position
--    threatens the protected flights can be forced onto ROE WEAPON_HOLD for a
--    short pulse, then restored to OPEN_FIRE. Escort geometry: effectiveness
--    RISES as the Growler closes (penetration escort physics -- deliberately the
--    opposite of the C-130's standoff burn-through model; do not unify them).
--
-- AI Growlers jam automatically after a startup grace. A player-flown Growler
-- gets an F10 group menu (jamming ON/OFF/status) instead of the auto-policy.
-- A dead/landed Growler projects nothing. The plugin owns no kills beyond the
-- spoofed weapon; SAM kills, Growler losses etc. record natively.

local function growlerLog(msg)
    env.info("GROWLER|: " .. tostring(msg))
end

if not dcsRetribution or not dcsRetribution.growler then
    growlerLog("no growler node emitted -- plugin inert")
    return
end

-- ── options ────────────────────────────────────────────────────────────────
local opts = (dcsRetribution.plugins and dcsRetribution.plugins.growler) or {}
local TICK_SEC = tonumber(opts.tickSec) or 10
local START_GRACE_S = tonumber(opts.startGraceS) or 120
local OFF_POWER = tonumber(opts.offensivePower) or 1.0
local DEF_POWER = tonumber(opts.defensivePower) or 1.0
local MAX_RANGE_M = (tonumber(opts.maxRangeNm) or 40) * 1852
local HOLD_SEC = tonumber(opts.holdSec) or 20
local SPOOF_MIN_TRAVEL_M = tonumber(opts.spoofMinTravelM) or 2000
-- Balance: after a suppressed SAM is released it CANNOT be re-held for this long,
-- guaranteeing a shoot-back window. Without it, many FULL jammers re-hold a SAM
-- the instant it releases and it is effectively dead forever. This makes jamming
-- intermittent (held HOLD_SEC, then free >= RECOVERY_SEC) at any jammer count.
local RECOVERY_SEC = tonumber(opts.recoverySec) or 30

-- Defensive spoof bands (metres from the Growler -> % chance per second).
-- The Matador bubble, scaled by DEF_POWER.
local SPOOF_BANDS = {
    { dist = 500, pk = 85 },
    { dist = 1000, pk = 65 },
    { dist = 2000, pk = 50 },
    { dist = 4000, pk = 30 },
    { dist = 7000, pk = 15 },
}

-- Offensive success chance per tick by Growler->SAM distance (escort model:
-- closer = stronger), scaled by OFF_POWER.
local OFF_BANDS = {
    { dist = 18520, prob = 0.85 }, -- <= 10 NM: pods burning right down the throat
    { dist = 37040, prob = 0.65 }, -- <= 20 NM
    { dist = 74080, prob = 0.45 }, -- <= 40 NM
    { dist = 111120, prob = 0.25 }, -- <= 60 NM (only reachable if maxRangeNm raised)
}

-- ── state ──────────────────────────────────────────────────────────────────
local jammers = {} -- [i] = { groupName, side, isPlayer, protected = {names}, active }
local heldSams = {} -- [groupName] = releaseTime (weapons-hold pulse in effect)
local samRecoverUntil = {} -- [groupName] = time until which it can't be re-held
local trackedShots = {} -- [i] = { weapon, originX, originZ, victimSide }

for _, rec in ipairs(dcsRetribution.growler.jammers or {}) do
    local prot = {}
    for _, member in ipairs(rec.protected or {}) do
        prot[#prot + 1] = member.groupName
    end
    -- Graduated tier (§77): the emitter derives these from the airframe's EW kit.
    -- defensivePower scales this jammer's spoof bubble; offensive gates whether it
    -- suppresses SAMs at all (only the dedicated FULL tier does). Missing fields
    -- (old saves / hand-authored nodes) default to a full-strength dedicated jammer.
    local defPower = tonumber(rec.defensivePower) or 1.0
    local offensive = rec.offensive == nil or tostring(rec.offensive) == "1"
    jammers[#jammers + 1] = {
        groupName = rec.groupName,
        side = tonumber(rec.side) or 2,
        isPlayer = tostring(rec.isPlayer) == "1",
        tier = rec.tier or "full",
        defensivePower = defPower,
        offensive = offensive,
        protected = prot,
        -- AI jams automatically (after grace); a player jammer starts OFF and
        -- toggles via the F10 menu.
        active = tostring(rec.isPlayer) ~= "1",
    }
end

local function flatDist(a, b)
    local dx = a.x - b.x
    local dz = a.z - b.z
    return math.sqrt(dx * dx + dz * dz)
end

-- First alive, airborne unit of a group, or nil.
local function aliveAirborneUnit(groupName)
    local group = Group.getByName(groupName)
    if not group or not group:isExist() then
        return nil
    end
    for _, unit in ipairs(group:getUnits() or {}) do
        if unit and unit:isExist() and unit:inAir() then
            return unit
        end
    end
    return nil
end

-- Any alive unit position of a named group (airborne not required -- a package
-- member on its takeoff roll is still protected), or nil.
local function aliveUnitPoint(groupName)
    local group = Group.getByName(groupName)
    if not group or not group:isExist() then
        return nil
    end
    for _, unit in ipairs(group:getUnits() or {}) do
        if unit and unit:isExist() then
            return unit:getPoint()
        end
    end
    return nil
end

-- A jammer entry's live emitting unit: alive, airborne, and switched on.
local function emittingUnit(jam)
    if not jam.active then
        return nil
    end
    return aliveAirborneUnit(jam.groupName)
end

-- ── defensive bubble ───────────────────────────────────────────────────────
-- Radar guidance ids in the DCS weapon desc (RADAR_ACTIVE / RADAR_SEMI_ACTIVE).
local function isRadarGuided(weapon)
    if not weapon.getDesc then
        -- Harness fakes carry no desc; treat as radar-guided so the spoof path
        -- is exercisable headlessly. Real DCS always provides the desc.
        return true
    end
    local ok, desc = pcall(weapon.getDesc, weapon)
    if not ok or type(desc) ~= "table" or desc.guidance == nil then
        return true
    end
    return desc.guidance == 3 or desc.guidance == 4
end

local function onShot(event)
    if not event.weapon then
        return
    end
    if not isRadarGuided(event.weapon) then
        return
    end
    local shooterSide = nil
    if event.initiator and event.initiator.getCoalition then
        local ok, side = pcall(event.initiator.getCoalition, event.initiator)
        if ok then
            shooterSide = side
        end
    end
    local origin = event.weapon:getPoint()
    trackedShots[#trackedShots + 1] = {
        weapon = event.weapon,
        originX = origin.x,
        originZ = origin.z,
        shooterSide = shooterSide,
    }
end

-- Per-second spoof pass over every tracked in-flight weapon.
local function spoofTick()
    if DEF_POWER <= 0 then
        trackedShots = {}
        return
    end
    local kept = {}
    for _, shot in ipairs(trackedShots) do
        local weapon = shot.weapon
        local alive = weapon and weapon:isExist()
        if alive then
            local wp = weapon:getPoint()
            local traveled = flatDist(wp, { x = shot.originX, z = shot.originZ })
            local spoofed = false
            if traveled >= SPOOF_MIN_TRAVEL_M then
                -- NON-STACKING (balance): find the single STRONGEST bubble covering
                -- this missile and roll ONCE against it -- do NOT roll once per
                -- jammer and OR the results, or N overlapping bubbles drive the
                -- spoof chance to ~100% (the "12 jammers in the air" problem). The
                -- best jammer for a missile is the one giving the highest effective
                -- pk (nearest band x its tier power); more jammers widen coverage,
                -- they never raise a single missile's odds beyond one good jammer.
                local bestPk = 0
                local bestName = nil
                for _, jam in ipairs(jammers) do
                    -- A red-fired missile is spoofed by a blue jammer and vice
                    -- versa; a friendly missile is never touched.
                    if shot.shooterSide == nil or shot.shooterSide ~= jam.side then
                        local unit = emittingUnit(jam)
                        if unit then
                            local d = flatDist(wp, unit:getPoint())
                            for _, band in ipairs(SPOOF_BANDS) do
                                if d <= band.dist then
                                    local pk = band.pk * DEF_POWER * jam.defensivePower
                                    if pk > bestPk then
                                        bestPk = pk
                                        bestName = jam.groupName
                                    end
                                    break -- only the tightest matching band counts
                                end
                            end
                        end
                    end
                end
                if bestPk > 0 and math.random(100) <= bestPk then
                    weapon:destroy()
                    spoofed = true
                    growlerLog(
                        "spoofed "
                            .. tostring(weapon:getTypeName())
                            .. " (best bubble "
                            .. tostring(bestName)
                            .. ", pk "
                            .. math.floor(bestPk)
                            .. ")"
                    )
                end
            end
            if not spoofed then
                kept[#kept + 1] = shot
            end
        end
    end
    trackedShots = kept
end

-- ── offensive pulses ───────────────────────────────────────────────────────
local function isRadarSamGroup(group)
    for _, unit in ipairs(group:getUnits() or {}) do
        if unit and unit:isExist() and unit.hasAttribute then
            if unit:hasAttribute("SAM TR") then
                return true
            end
        end
    end
    return false
end

local function releaseDue(now)
    for name, releaseAt in pairs(heldSams) do
        if now >= releaseAt then
            heldSams[name] = nil
            -- Open a mandatory recovery window before this SAM can be re-held.
            samRecoverUntil[name] = now + RECOVERY_SEC
            local group = Group.getByName(name)
            if group and group:isExist() then
                local controller = group:getController()
                if controller then
                    controller:setOption(
                        AI.Option.Ground.id.ROE,
                        AI.Option.Ground.val.ROE.OPEN_FIRE
                    )
                end
            end
        end
    end
end

local function offensiveTick(now)
    if OFF_POWER <= 0 then
        return
    end
    for _, jam in ipairs(jammers) do
        -- Only the dedicated FULL tier suppresses SAMs; ECM/self-protect/loose
        -- jammers defend the package but never pulse a radar onto weapons-hold.
        local unit = jam.offensive and emittingUnit(jam) or nil
        if unit then
            local jp = unit:getPoint()
            local enemySide = (jam.side == 2) and 1 or 2
            for _, group in ipairs(coalition.getGroups(enemySide, Group.Category.GROUND) or {}) do
                local gname = group and group:getName()
                -- Skip a SAM that is already held OR still inside its post-release
                -- recovery window (the guaranteed shoot-back gap that keeps jamming
                -- intermittent no matter how many jammers pile on).
                if
                    group
                    and group:isExist()
                    and heldSams[gname] == nil
                    and now >= (samRecoverUntil[gname] or 0)
                then
                    if isRadarSamGroup(group) then
                        local gu = group:getUnits()[1]
                        if gu and gu:isExist() then
                            local d = flatDist(jp, gu:getPoint())
                            if d <= MAX_RANGE_M then
                                for _, band in ipairs(OFF_BANDS) do
                                    if d <= band.dist then
                                        if math.random() <= band.prob * OFF_POWER then
                                            local controller = group:getController()
                                            if controller then
                                                controller:setOption(
                                                    AI.Option.Ground.id.ROE,
                                                    AI.Option.Ground.val.ROE.WEAPON_HOLD
                                                )
                                                heldSams[group:getName()] = now + HOLD_SEC
                                                growlerLog(
                                                    jam.groupName
                                                        .. " holding down "
                                                        .. group:getName()
                                                        .. " for "
                                                        .. HOLD_SEC
                                                        .. " s"
                                                )
                                            end
                                        end
                                        break -- nearest band only
                                    end
                                end
                            end
                        end
                    end
                end
            end
        end
    end
end

-- ── player F10 menu ────────────────────────────────────────────────────────
local function setJamming(jam, on)
    jam.active = on
    local group = Group.getByName(jam.groupName)
    if group and group:isExist() then
        trigger.action.outTextForGroup(
            group:getID(),
            "GROWLER: jamming " .. (on and "ON" or "OFF"),
            10
        )
    end
end

local function jammingStatus(jam)
    local group = Group.getByName(jam.groupName)
    if not group or not group:isExist() then
        return
    end
    local held = 0
    for _ in pairs(heldSams) do
        held = held + 1
    end
    trigger.action.outTextForGroup(
        group:getID(),
        "GROWLER: jamming "
            .. (jam.active and "ON" or "OFF")
            .. " -- "
            .. held
            .. " emitter(s) currently suppressed",
        10
    )
end

local function addPlayerMenus()
    for _, jam in ipairs(jammers) do
        if jam.isPlayer then
            local group = Group.getByName(jam.groupName)
            if group and group:isExist() then
                local groupId = group:getID()
                local root =
                    missionCommands.addSubMenuForGroup(groupId, "Growler jamming")
                missionCommands.addCommandForGroup(groupId, "Jamming ON", root, function()
                    setJamming(jam, true)
                end)
                missionCommands.addCommandForGroup(groupId, "Jamming OFF", root, function()
                    setJamming(jam, false)
                end)
                missionCommands.addCommandForGroup(groupId, "Status", root, function()
                    jammingStatus(jam)
                end)
            end
        end
    end
end

-- ── wiring ─────────────────────────────────────────────────────────────────
local shotHandler = {}
function shotHandler:onEvent(event)
    if event.id == world.event.S_EVENT_SHOT then
        local ok, err = pcall(onShot, event)
        if not ok then
            growlerLog("shot handler error: " .. tostring(err))
        end
    end
end
world.addEventHandler(shotHandler)

local function spoofLoop()
    local ok, err = pcall(spoofTick)
    if not ok then
        growlerLog("spoof tick error: " .. tostring(err))
    end
    return timer.getTime() + 1
end

local function offensiveLoop()
    local now = timer.getTime()
    local ok, err = pcall(function()
        releaseDue(now)
        offensiveTick(now)
    end)
    if not ok then
        growlerLog("offensive tick error: " .. tostring(err))
    end
    return now + TICK_SEC
end

-- The defensive bubble arms immediately (a missile in the air is a missile in
-- the air); the offensive auto-policy waits out the startup grace so nobody's
-- SAM is held down while players are still aligning on the ramp.
timer.scheduleFunction(spoofLoop, nil, timer.getTime() + 1)
timer.scheduleFunction(offensiveLoop, nil, timer.getTime() + START_GRACE_S)
timer.scheduleFunction(function()
    local ok, err = pcall(addPlayerMenus)
    if not ok then
        growlerLog("menu setup error: " .. tostring(err))
    end
    return nil
end, nil, timer.getTime() + 10)

growlerLog(
    "armed -- "
        .. #jammers
        .. " escort jammer(s), grace "
        .. START_GRACE_S
        .. " s, max range "
        .. math.floor(MAX_RANGE_M / 1852)
        .. " NM"
)
