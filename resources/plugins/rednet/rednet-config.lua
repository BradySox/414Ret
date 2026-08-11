---------------------------------------------------------------------------------------------------
-- Red comms net runtime (§70 COMINT, C1+C2): the enemy net, audible on the dial.
-- Design is in docs/dev/design/414th-comint-notes.md.
--
-- Stations key coded CW on their own UHF AM frequency via trigger.action.radioTransmission
-- from the node's map position, looped only while a window is open, so a DF needle points
-- only while they are on the air. Reads dcsRetribution.redNet
-- (game/missiongenerator/rednetluadata.py); inert when absent.
--
-- The load-bearing parts:
--
--  * Frequencies are Python-allocated at x.500 MHz and must clear a 100 kHz guard band
--    around every RadioRegistry allocation, so a net never keys on or one detent beside a
--    briefed channel. Station count is capped so the net cannot fill the UHF band.
--  * Audio and DF geometry only -- no kills, no gameplay model. A node goes off the air on
--    the MANTIS node_dead convention; a culled node correctly reads ALIVE.
--  * Window loops are staggered across the first gap (the §49 same-frame lesson).
---------------------------------------------------------------------------------------------------

if not (dcsRetribution and dcsRetribution.redNet) then
    return
end

local data = dcsRetribution.redNet

-- Defaults. Overridable via the plugin options (dcsRetribution.plugins.rednet).
local WINDOW_SEC = 45 -- s: transmission length per window (fixed C2 stations)
local GAP_SEC = 240 -- s: mean silence between a net's windows (jittered)
local CLAND_WINDOW_SEC = 20 -- s: a clandestine station's window (short -- catch it or wait)
local CLAND_GAP_SEC = 480 -- s: a clandestine station's mean silence (long -- the hunt)
local POWER_W = 10000 -- transmitter power (DCS models the falloff; range, not loudness)
local GRACE = 180 -- s before the first window

if dcsRetribution.plugins and dcsRetribution.plugins.rednet then
    local o = dcsRetribution.plugins.rednet
    WINDOW_SEC = tonumber(o.windowSec) or WINDOW_SEC
    GAP_SEC = tonumber(o.gapSec) or GAP_SEC
    CLAND_WINDOW_SEC = tonumber(o.clandestineWindowSec) or CLAND_WINDOW_SEC
    CLAND_GAP_SEC = tonumber(o.clandestineGapSec) or CLAND_GAP_SEC
    POWER_W = tonumber(o.powerW) or POWER_W
    GRACE = tonumber(o.startGraceS) or GRACE
end

local CW_FILE = "l10n/DEFAULT/rednet-cw.wav"

local function num(v)
    return tonumber(v) or 0
end

-- Death detection, the MANTIS C2 convention (commsjam-config.lua vendors it too): C2 nodes are
-- placed statics ("<name> object") or destructible scenery, so a node counts as dead only on
-- POSITIVE evidence -- an existed-and-destroyed static, or its name in the global dead_events
-- ledger (bare-name matched with the "id | " prefix stripped, like the rest of Retribution's
-- BDA path).
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

local function nodeAlive(node)
    if type(node.units) ~= "table" then
        return false
    end
    for _, name in ipairs(node.units) do
        if not unitDead(name) then
            return true
        end
    end
    return false
end

-- Collect the emitted nodes (name, unit names, position, frequency, schedule).
-- A clandestine station (concealed COIN spawn / authored concealed comms TGO)
-- keys the short-window/long-gap hunt schedule; fixed C2 stations key the
-- normal traffic cadence.
local nodes = {}
if type(data.nodes) == "table" then
    for _, rec in ipairs(data.nodes) do
        local mhz = num(rec.mhz)
        if mhz > 0 and type(rec.units) == "table" then
            local clandestine = (rec.clandestine == true or rec.clandestine == "true")
            nodes[#nodes + 1] = {
                name = tostring(rec.name or "C2 net"),
                units = rec.units,
                x = num(rec.x),
                y = num(rec.y),
                hz = mhz * 1000000,
                mhz = mhz,
                clandestine = clandestine,
                window = clandestine and CLAND_WINDOW_SEC or WINDOW_SEC,
                gap = clandestine and CLAND_GAP_SEC or GAP_SEC,
            }
        end
    end
end

if #nodes == 0 then
    env.info("REDNET|: no usable node emitted; plugin idle")
    return
end

local txSeq = 0 -- unique transmission names for stopRadioTransmission

-- One transmission window for one node: start the looped CW carrier, schedule its stop, and
-- return the next window time -- or nil (stop scheduling) once the node is positively dead.
local function windowCycle(node)
    if not nodeAlive(node) then
        if not node.deadLogged then
            node.deadLogged = true
            env.info(string.format("REDNET|: %s is off the air (node dead)", node.name))
        end
        return nil
    end

    local h = 0
    pcall(function()
        h = land.getHeight({ x = node.x, y = node.y }) or 0
    end)
    local origin = { x = node.x, y = h + 10, z = node.y }

    txSeq = txSeq + 1
    local txName = "rednet-" .. txSeq
    local ok = pcall(
        trigger.action.radioTransmission,
        CW_FILE,
        origin,
        0, -- AM: the UHF C2/air net
        true, -- loop the coded traffic for the window (a steady carrier for the DF needle)
        node.hz,
        POWER_W,
        txName
    )
    if ok then
        timer.scheduleFunction(function()
            pcall(trigger.action.stopRadioTransmission, txName)
            return nil
        end, {}, timer.getTime() + node.window)
    end

    -- Jittered cadence (0.6x - 1.4x the mean gap) so the net never feels metronomic.
    return timer.getTime() + node.window + node.gap * (0.6 + 0.8 * math.random())
end

-- Arm one node's window loop to first fire at mission-time `startAt`.
local function armNode(node, startAt)
    timer.scheduleFunction(function()
        local okTick, nextT = pcall(windowCycle, node)
        if not okTick then
            env.error("REDNET|: window error: " .. tostring(nextT))
            return timer.getTime() + GAP_SEC
        end
        return nextT
    end, {}, startAt)
end

local ok, err = pcall(function()
    local t0 = timer.getTime()
    -- Stagger the first windows across one gap length so nodes never key up in the
    -- same frame (§49) and the net reads as independent stations.
    local stagger = GAP_SEC / #nodes
    local summary = {}
    for i, node in ipairs(nodes) do
        armNode(node, t0 + GRACE + (i - 1) * stagger)
        summary[#summary + 1] = string.format(
            "%s @ %.3f AM%s",
            node.name,
            node.mhz,
            node.clandestine and " (clandestine)" or ""
        )
    end
    env.info(
        string.format(
            "REDNET|: armed -- %d net(s), first window in %ds: %s",
            #nodes,
            GRACE,
            table.concat(summary, "; ")
        )
    )
end)
if not ok then
    env.error("REDNET|: setup error: " .. tostring(err))
end
