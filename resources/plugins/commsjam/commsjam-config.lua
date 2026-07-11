---------------------------------------------------------------------------------------------------
-- Enemy comms jamming runtime (the IADS comms nodes, given a voice).
--
-- While at least one emitted enemy C2 node (comms mast / command center) is alive, transmit
-- duty-cycled barrage noise on a rotating subset of the briefed BLUE channels via
-- trigger.action.radioTransmission from the node's map position: real power/distance falloff,
-- audible on the cockpit radio (and therefore to SRS users, whose radios tune off the cockpit).
-- GUARD/ATC are never in the emitted list (filtered in Python by construction); the kneeboard
-- carries a JAM BACKUP channel the jammer never touches, echoed in the first-burst cue.
--
-- THE INTEL GATE (captureOnly): red can only jam channels it KNOWS, and it learns them from a
-- captured aircrew's comms plan. With captureOnly set and activeFromStart false, the plugin stays
-- dormant, watching the Combat SAR plugin's `combat_sar_captures` state global (appended when the
-- §15 enemy-capture race is lost); on the first blue capture it announces the compromise and
-- starts the burst loop after an exploitation delay (captureReactionS). activeFromStart true means
-- a POW held from an earlier turn already compromised the net -- jam from the grace as usual.
-- Rescue the pilot and the net stays clean.
--
-- Audio pressure ONLY -- the plugin owns no kills. Killing the node is an ordinary strike on an
-- ordinary IADS TGO, recorded natively; this script merely stops transmitting once every emitted
-- node is positively dead (the MANTIS C2 node_dead convention: a placed static that existed and
-- no longer :isExist(), or a name recorded in the global dead_events ledger -- a culled or
-- never-spawned node reads ALIVE, which is correct: it can't be killed this mission, and the
-- standing pressure is what motivates fragging it next turn).
--
-- Reads dcsRetribution.commsJam, emitted by game/missiongenerator/commsjamluadata.py; inert when
-- that node is absent. pcall-guarded throughout so a hiccup never takes the mission down.
-- Definition order matters (Lua 5.1): helpers precede use.
---------------------------------------------------------------------------------------------------

if not (dcsRetribution and dcsRetribution.commsJam) then
    return
end

local data = dcsRetribution.commsJam

-- Defaults. Overridable via the plugin options (dcsRetribution.plugins.commsjam).
local BURST_SEC = 25 -- s: noise transmission length per jammed channel
local INTERVAL_SEC = 90 -- s: mean pause between burst cycles (jittered)
local MAX_FREQS = 3 -- channels stepped on per burst cycle
local MAX_CHANNELS = 10 -- cap on the total distinct channels jammed at all (top-priority first)
local POWER_W = 100 -- transmitter power (DCS models the falloff)
local GRACE = 240 -- s before the first burst
local CAPTURE_REACTION = 120 -- s from a live capture to the first burst (exploitation delay)
local CAPTURE_POLL = 30 -- s between capture-ledger checks while dormant

if dcsRetribution.plugins and dcsRetribution.plugins.commsjam then
    local o = dcsRetribution.plugins.commsjam
    BURST_SEC = tonumber(o.burstSec) or BURST_SEC
    INTERVAL_SEC = tonumber(o.intervalSec) or INTERVAL_SEC
    MAX_FREQS = tonumber(o.maxFreqsPerBurst) or MAX_FREQS
    MAX_CHANNELS = tonumber(o.maxChannels) or MAX_CHANNELS
    POWER_W = tonumber(o.powerW) or POWER_W
    GRACE = tonumber(o.startGraceS) or GRACE
    CAPTURE_REACTION = tonumber(o.captureReactionS) or CAPTURE_REACTION
end

local NOISE_FILE = "l10n/DEFAULT/commsjam-noise.wav"

local function num(v)
    return tonumber(v) or 0
end

-- Death detection, the MANTIS C2 convention (mantis-config.lua): C2 nodes are placed statics
-- ("<name> object") or destructible scenery, so a node counts as dead only on POSITIVE evidence
-- -- an existed-and-destroyed static, or its name in the global dead_events ledger (bare-name
-- matched with the "id | " prefix stripped, like the rest of Retribution's BDA path).
local function bareName(name)
    return name:match("|%s*(.+)$") or name
end

local function unitDead(name)
    local so = StaticObject.getByName(name .. " object")
    if so ~= nil and not so:isExist() then
        return true
    end
    if type(dead_events) == "table" then
        local bare = bareName(name)
        for _, dn in pairs(dead_events) do
            if dn == name or dn == bare then
                return true
            end
        end
    end
    return false
end

local function jammerAlive(jammer)
    if type(jammer.units) ~= "table" then
        return false
    end
    for _, name in ipairs(jammer.units) do
        if not unitDead(name) then
            return true
        end
    end
    return false
end

local function aliveJammers()
    local out = {}
    if type(data.jammers) == "table" then
        for _, jammer in ipairs(data.jammers) do
            if jammerAlive(jammer) then
                out[#out + 1] = jammer
            end
        end
    end
    return out
end

local freqs = {}
if type(data.freqs) == "table" then
    for _, f in ipairs(data.freqs) do
        local mhz = num(f.mhz)
        if mhz > 0 then
            freqs[#freqs + 1] = { hz = mhz * 1000000, mod = (f.mod == "FM") and 1 or 0, mhz = mhz }
        end
    end
end

-- Concentrate on the top-priority channels. The generator emits them priority-ordered
-- (human-crewed flights first, then AWACS, then AI flights), so keeping the FIRST
-- MAX_CHANNELS jams the ones that matter and leaves the rest of the net clean. A lower
-- MAX_CHANNELS + a longer burst / shorter pause = continuous pressure on a few channels
-- instead of duty-cycled coverage of many.
if MAX_CHANNELS >= 1 then
    while #freqs > MAX_CHANNELS do
        freqs[#freqs] = nil
    end
end

local cursor = 0 -- rotating window over freqs, so every channel gets its turn
local burstIndex = 0 -- rotates the transmitting node across alive jammers
local txSeq = 0 -- unique transmission names for stopRadioTransmission
local announced = false
local ceased = false

local function backupSuffix()
    local backup = num(data.backupMhz)
    if backup > 0 then
        return string.format(" JAM BACKUP: %.3f MHz (see kneeboard).", backup)
    end
    return ""
end

-- Set before the burst loop is armed: which story the first-burst cue tells.
-- "ambient" = a C2 node is alive (the intel gate is off); "pow" = a POW held
-- from an earlier turn already compromised the comms plan.
local announceReason = "ambient"

local function announceOnce()
    if announced then
        return
    end
    announced = true
    local text
    if announceReason == "pow" then
        text = "COMMS COMPROMISED: enemy interrogation of captured aircrew has yielded "
            .. "the comms plan -- hostile jamming on briefed channels. Destroy enemy "
            .. "C2/communications nodes to silence it."
    else
        text = "COMMS JAMMING: hostile interference on briefed channels. "
            .. "Suspected source: enemy C2/communications nodes -- destroy them to silence it."
    end
    pcall(
        trigger.action.outTextForCoalition,
        coalition.side.BLUE,
        text .. backupSuffix(),
        25
    )
end

local function announceCeased()
    if ceased then
        return
    end
    ceased = true
    pcall(
        trigger.action.outTextForCoalition,
        coalition.side.BLUE,
        "Comms jamming has ceased -- the enemy C2 network is off the air.",
        20
    )
end

-- One burst cycle: pick the next alive jammer, step on the next MAX_FREQS channels for
-- BURST_SEC, then go quiet until the next (jittered) cycle. Returns the next cycle time,
-- or nil (stop scheduling) once every jammer is dead.
local function burstCycle()
    local alive = aliveJammers()
    if #alive == 0 then
        if announced then
            announceCeased()
        end
        return nil
    end
    if #freqs == 0 then
        return nil
    end

    burstIndex = burstIndex + 1
    local jammer = alive[((burstIndex - 1) % #alive) + 1]
    local jx, jy = num(jammer.x), num(jammer.y)
    local h = 0
    pcall(function()
        h = land.getHeight({ x = jx, y = jy }) or 0
    end)
    local origin = { x = jx, y = h + 10, z = jy }

    local names = {}
    local count = math.min(MAX_FREQS, #freqs)
    for _ = 1, count do
        cursor = (cursor % #freqs) + 1
        local f = freqs[cursor]
        txSeq = txSeq + 1
        local name = "commsjam-" .. txSeq
        local ok = pcall(
            trigger.action.radioTransmission,
            NOISE_FILE,
            origin,
            f.mod,
            true, -- loop the static for the burst duration
            f.hz,
            POWER_W,
            name
        )
        if ok then
            names[#names + 1] = name
        end
    end

    if #names > 0 then
        announceOnce()
        timer.scheduleFunction(function()
            for _, name in ipairs(names) do
                pcall(trigger.action.stopRadioTransmission, name)
            end
            return nil
        end, {}, timer.getTime() + BURST_SEC)
    end

    -- Jittered cadence (0.6x - 1.4x the mean) so the interference never feels metronomic.
    return timer.getTime() + BURST_SEC + INTERVAL_SEC * (0.6 + 0.8 * math.random())
end

-- Arm the burst loop to first fire at mission-time `startAt`.
local function armBurstLoop(startAt)
    timer.scheduleFunction(function()
        local okTick, nextT = pcall(burstCycle)
        if not okTick then
            env.error("COMMSJAM|: burst error: " .. tostring(nextT))
            return timer.getTime() + INTERVAL_SEC
        end
        return nextT
    end, {}, startAt)
end

-- Has the Combat SAR enemy-capture race recorded a BLUE capture this mission?
-- combat_sar_captures is the combatsar plugin's state global (appended on each
-- capture; entries carry a forward-compat coalition key -- red never emitted
-- today, but filter anyway).
local function blueCaptureRecorded()
    if type(combat_sar_captures) ~= "table" then
        return false
    end
    for _, entry in ipairs(combat_sar_captures) do
        if type(entry) == "table" and entry.coalition ~= "red" then
            return true
        end
    end
    return false
end

local ok, err = pcall(function()
    local jammerCount = (type(data.jammers) == "table") and #data.jammers or 0
    if jammerCount == 0 or #freqs == 0 then
        env.info("COMMSJAM|: nothing to do (no jammer or no channel emitted)")
        return
    end

    local captureOnly = (data.captureOnly == true or data.captureOnly == "true")
    local activeFromStart =
        not (data.activeFromStart == false or data.activeFromStart == "false")
    local t0 = timer.getTime()

    if not captureOnly or activeFromStart then
        if captureOnly then
            announceReason = "pow" -- a held POW compromised the plan on an earlier turn
        end
        armBurstLoop(t0 + GRACE)
        env.info(
            string.format(
                "COMMSJAM|: armed -- %d C2 jammer(s), %d channel(s), first burst in %ds%s",
                jammerCount,
                #freqs,
                GRACE,
                captureOnly and " (comms plan compromised by a held POW)" or ""
            )
        )
        return
    end

    -- Intel gate: dormant until the Combat SAR capture race is lost. On the
    -- first blue capture, cue the compromise immediately and start jamming
    -- after the exploitation delay (never before the startup grace). Stops
    -- watching if every jammer dies first.
    timer.scheduleFunction(function()
        if #aliveJammers() == 0 then
            return nil -- the C2 net died before it ever got its intel
        end
        if not blueCaptureRecorded() then
            return timer.getTime() + CAPTURE_POLL
        end
        announced = true -- this cue IS the announcement; no second first-burst cue
        pcall(
            trigger.action.outTextForCoalition,
            coalition.side.BLUE,
            "AIRCREW CAPTURED -- assume the comms plan is compromised. Expect hostile "
                .. "jamming on briefed channels; rotate off them now."
                .. backupSuffix(),
            25
        )
        armBurstLoop(math.max(timer.getTime() + CAPTURE_REACTION, t0 + GRACE))
        env.info("COMMSJAM|: capture detected -- jamming begins after the exploitation delay")
        return nil
    end, {}, t0 + CAPTURE_POLL)
    env.info(
        string.format(
            "COMMSJAM|: intel gate armed -- %d C2 jammer(s), %d channel(s), "
                .. "dormant until an aircrew capture",
            jammerCount,
            #freqs
        )
    )
end)
if not ok then
    env.error("COMMSJAM|: setup error: " .. tostring(err))
end
