---------------------------------------------------------------------------------------------------
-- Smart Threat Reaction (§94) -- only the flight a missile is guiding on goes defensive.
--
-- DCS' default Evade Fire breaks EVERY aircraft that merely perceives a launch, so one naval or
-- S-300 salvo scatters dozens of jets from unrelated packages. This parks every airplane at
-- Passive Defense and flips only the group weapon:getTarget() names, until that missile is gone.
-- docs/dev/design/414th-ai-threat-reaction-notes.md.
--
-- Constraints, each learned the expensive way -- do not undo:
--   * The target comes from the native weapon:getTarget(), never from geometry. Guessing which
--     jet a missile is "probably" for is what this replaces.
--   * REACTION_ON_THREAT is a per-GROUP option, so the targeted FLIGHT evades, not the one jet.
--   * A sweep must only pay setOption on a state TRANSITION, and a shot that resolves to a
--     ship/ground target is dropped at S_EVENT_SHOT with no re-check. The first version did
--     neither and stalled the sim during an anti-ship salvo (juanjux/dcs-retribution, 2026-07-15).
--   * AIRPLANE only. Helicopters keep DCS' stock Evade Fire -- they have no formation to hold.
--   * §61's scrambled bandits are set Evade Fire on purpose; the baseline must not stomp them.
--     Any plugin can claim the same exemption via dcsRetribution.aiReactionExempt[groupName].
---------------------------------------------------------------------------------------------------

local DEBUG = false
if dcsRetribution and dcsRetribution.plugins and dcsRetribution.plugins.ai_reaction then
    DEBUG = dcsRetribution.plugins.ai_reaction.DEBUG == true
end

local OPT   = AI.Option.Air.id.REACTION_ON_THREAT
local PASS  = 1  -- PASSIVE_DEFENCE
local EVADE = 2  -- EVADE_FIRE

-- A sweep is nearly free because only transitions cost a setOption, so it can be relaxed; every
-- REASSERT_EVERY-th sweep re-applies to ALL groups to catch any the engine reset to Evade Fire on
-- activation and to prune destroyed groups. 10 s * 6 = a full re-assert about once a minute.
local BASELINE_INTERVAL = 10
local REASSERT_EVERY    = 6

local threatCount = {}  -- [groupName] -> number of live missiles guiding on it
local live        = {}  -- [weapon userdata] -> groupName it is guiding on
local passive     = {}  -- [groupName] -> true once parked at Passive (and no missile since)

local function dbg(msg)
    if not DEBUG then return end
    env.info("AIReaction| " .. msg)
    trigger.action.outText("AIReaction: " .. msg, 8)
end

-- DEBUG-gated so an anti-ship salvo cannot flood dcs.log.
local function info(msg)
    if DEBUG then env.info("AIReaction| " .. msg) end
end

local function wname(w)
    local ok, n = pcall(function() return w:getTypeName() end)
    return (ok and n) or "?"
end

local function evadingCount()
    local n = 0
    for _, c in pairs(threatCount) do if (c or 0) > 0 then n = n + 1 end end
    return n
end

-- Read lazily: a plugin that claims an exemption may load after this one.
local function isExempt(gname)
    local t = dcsRetribution and dcsRetribution.aiReactionExempt
    return t ~= nil and t[gname] == true
end

local function setOpt(grp, val)
    pcall(function()
        local c = grp:getController()
        if c then c:setOption(OPT, val) end
    end)
end

-- Tag the flight a weapon is guiding on -> Evade Fire. Status is "evade", "notarget" (no unit
-- target: a GPS weapon aimed at a point, or a lock not resolved yet) or "notair" (a ship/ground
-- unit resolved).
local function tryTag(w)
    local ok, tgt = pcall(function() return w:getTarget() end)
    if not ok or not tgt then return "notarget" end
    local okg, grp = pcall(function() return tgt:getGroup() end)
    if not okg or not grp then return "notarget" end
    local okc, cat = pcall(function() return grp:getCategory() end)
    if not okc or cat ~= Group.Category.AIRPLANE then return "notair" end
    local gname = grp:getName()
    setOpt(grp, EVADE)
    threatCount[gname] = (threatCount[gname] or 0) + 1
    live[w] = gname
    passive[gname] = nil  -- evading now; baseline must re-park it at Passive once clear
    dbg("SHOT " .. wname(w) .. " -> EVADE " .. gname .. "  [" .. evadingCount() .. " flights evading]")
    return "evade"
end

local passSweep = 0
local function baseline(_, time)
    passSweep = passSweep + 1
    if passSweep % REASSERT_EVERY == 0 then
        passive = {}
    end
    for _, side in pairs({ coalition.side.RED, coalition.side.BLUE }) do
        local ok, groups = pcall(coalition.getGroups, side, Group.Category.AIRPLANE)
        if ok and groups then
            for _, grp in pairs(groups) do
                local okn, gname = pcall(function() return grp:getName() end)
                if okn and gname and not passive[gname] and (threatCount[gname] or 0) == 0
                   and not isExempt(gname) then
                    setOpt(grp, PASS)
                    passive[gname] = true
                end
            end
        end
    end
    return time + BASELINE_INTERVAL
end

-- When a tracked missile no longer exists, release its target; the next baseline pass returns it
-- to Passive Defense once no missiles remain on it.
local function watch(_, time)
    for w, gname in pairs(live) do
        local ok, ex = pcall(function() return w:isExist() end)
        if not (ok and ex) then
            live[w] = nil
            threatCount[gname] = math.max(0, (threatCount[gname] or 1) - 1)
            if (threatCount[gname] or 0) == 0 then
                dbg(gname .. " clear -> Passive  [" .. evadingCount() .. " flights evading]")
            end
        end
    end
    return time + 1
end

local handler = {}
function handler:onEvent(event)
    if not event or event.id ~= world.event.S_EVENT_SHOT or not event.weapon then return end
    local w = event.weapon
    local status = tryTag(w)
    if status == "evade" then return end
    -- A ship/ground target can never become an airplane, so drop it with no re-check: this is the
    -- anti-ship salvo path that has to stay cheap.
    if status == "notair" then return end
    -- "notarget": a real A2A shot whose lock resolves a beat later, or a GPS weapon on a point.
    timer.scheduleFunction(function()
        local ok, ex = pcall(function() return w:isExist() end)
        if not (ok and ex) then
            info("SHOT " .. wname(w) .. " -> gone before a target resolved")
        elseif not live[w] then
            if tryTag(w) == "notarget" then
                info("SHOT " .. wname(w) .. " -> not tagged: no unit target (GPS weapon to a point)")
            end
        end
        return nil
    end, nil, timer.getTime() + 1)
end

world.addEventHandler(handler)
timer.scheduleFunction(baseline, nil, timer.getTime() + 2)
timer.scheduleFunction(watch, nil, timer.getTime() + 3)
env.info("AIReaction| Smart Threat Reaction loaded (DEBUG=" .. tostring(DEBUG) .. ")")
