---------------------------------------------------------------------------------------------------
-- Mission-start briefing popup.
--
-- When a pilot slots into an aircraft, show them a short on-screen card -- campaign, mission,
-- date, time, callsign, aircraft, task, departure field -- the way the professional DCS campaigns
-- greet you at mission start. Reads dcsRetribution.briefing (emitted by
-- game/missiongenerator/briefingluadata.py: a shared header + one record per player-crewed flight,
-- keyed by DCS group name); inert when that node is absent.
--
-- Two paths cover every way a pilot reaches a seat: an S_EVENT_BIRTH handler (fires whenever a
-- pilot enters a slot -- mission start in SP, and any slot-in / rejoin on a server) plus a one-shot
-- mission-start sweep after a short grace, in case the player's birth fired before this script
-- registered its handler. A small per-unit debounce keeps the two from double-showing the same
-- slotting while still letting a genuine re-slot re-show.
--
-- Display ONLY: no gameplay-model change, no spawns, nothing persisted. pcall-guarded throughout so
-- a hiccup never takes the mission down. Definition order matters (Lua 5.1): helpers precede use.
---------------------------------------------------------------------------------------------------

if not (dcsRetribution and dcsRetribution.briefing) then
    return
end

local data = dcsRetribution.briefing

-- Defaults. Overridable via the plugin options (dcsRetribution.plugins.briefing).
local DURATION = 12 -- s the card stays on screen
local GRACE = 2 -- s before the mission-start sweep

if dcsRetribution.plugins and dcsRetribution.plugins.briefing then
    local o = dcsRetribution.plugins.briefing
    DURATION = tonumber(o.durationS) or DURATION
    GRACE = tonumber(o.startGraceS) or GRACE
end

-- Dedupe window for the birth-handler + mission-start-sweep double fire; comfortably above the
-- grace so both catch the same slotting exactly once, small enough that a later re-slot re-shows.
local DEBOUNCE = GRACE + 5

-- group name -> flight record, from the emitted flights list.
local byGroup = {}
if type(data.flights) == "table" then
    for _, rec in ipairs(data.flights) do
        if rec.group then
            byGroup[rec.group] = rec
        end
    end
end

local function str(v, fallback)
    if v == nil or v == "" then
        return fallback or ""
    end
    return tostring(v)
end

-- The shared header line, built once from dcsRetribution.briefing.header.
local function headerText()
    local h = data.header or {}
    local title = str(h.campaign, "Campaign")
    local line2 = "Mission " .. str(h.mission, "?")
    if h.date and h.date ~= "" then
        line2 = line2 .. "  |  " .. tostring(h.date)
    end
    if h.time and h.time ~= "" then
        line2 = line2 .. "  |  " .. tostring(h.time)
    end
    return title .. "\n" .. line2
end

local HEADER = headerText()

-- The full card for one flight: shared header + this pilot's own details.
local function buildCard(rec)
    local lines = {
        HEADER,
        "",
        "Callsign:   " .. str(rec.callsign, "-"),
        "Aircraft:   " .. str(rec.aircraft, "-"),
        "Task:       " .. str(rec.task, "-"),
        "Departure:  " .. str(rec.airfield, "-"),
    }
    return table.concat(lines, "\n")
end

local shownAt = {} -- unit name -> last mission time the card was shown

-- Show the card to the group of a player unit, unless we just showed it (debounce).
local function showFor(unit)
    if not (unit and unit.isExist and unit:isExist()) then
        return
    end
    -- Players only: an AI birth returns nil here, so AI flights are never shown a card.
    local player = unit:getPlayerName()
    if not player then
        return
    end
    local grp = unit:getGroup()
    if not (grp and grp:isExist()) then
        return
    end
    local rec = byGroup[grp:getName()]
    if not rec then
        return
    end
    local uname = unit:getName()
    local last = shownAt[uname]
    if last and (timer.getTime() - last) < DEBOUNCE then
        return
    end
    shownAt[uname] = timer.getTime()
    trigger.action.outTextForGroup(grp:getID(), buildCard(rec), DURATION, false)
end

-- Ongoing path: whenever a pilot enters a slot.
local handler = {}
function handler:onEvent(event)
    if event and event.id == world.event.S_EVENT_BIRTH and event.initiator then
        pcall(showFor, event.initiator)
    end
end

-- One-shot mission-start sweep: catch a player already in a seat whose birth may have fired before
-- this handler registered (single-player). Only iterates the known briefing groups.
local function initialSweep()
    for name in pairs(byGroup) do
        local grp = Group.getByName(name)
        if grp and grp:isExist() then
            local units = grp:getUnits() or {}
            for _, unit in ipairs(units) do
                pcall(showFor, unit)
            end
        end
    end
    return nil
end

local ok, err = pcall(function()
    world.addEventHandler(handler)
    timer.scheduleFunction(function()
        local swept, serr = pcall(initialSweep)
        if not swept then
            env.warning("briefing: sweep error: " .. tostring(serr))
        end
        return nil
    end, {}, timer.getTime() + GRACE)
    local count = 0
    for _ in pairs(byGroup) do
        count = count + 1
    end
    env.info(string.format("BRIEFING|: armed for %d player flight(s)", count))
end)
if not ok then
    env.error("BRIEFING|: setup error: " .. tostring(err))
end
