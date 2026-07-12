---------------------------------------------------------------------------------------------------
-- Mission-start briefing popup.
--
-- When a pilot slots into an aircraft, show them a short on-screen card -- campaign, mission,
-- date, time, callsign, aircraft, task, departure field -- the way the professional DCS campaigns
-- greet you at mission start. A SECOND card (the startup/taxi instruction, e.g. "Contact ground @
-- 249.50 when ready to taxi") is flashed right after the first and held the same duration. Reads
-- dcsRetribution.briefing (emitted by game/missiongenerator/briefingluadata.py: a shared header +
-- one record per player-crewed flight, keyed by DCS group name); inert when that node is absent.
--
-- Two paths cover every way a pilot reaches a seat: an S_EVENT_BIRTH handler (fires whenever a
-- pilot enters a slot -- mission start in SP, and any slot-in / rejoin on a server) plus a one-shot
-- mission-start sweep after a short grace, in case the player's birth fired before this script
-- registered its handler. A small per-unit debounce keeps the two from double-showing the same
-- slotting while still letting a genuine re-slot re-show.
--
-- Display ONLY: no gameplay-model change, no spawns, nothing persisted. pcall-guarded throughout so
-- a hiccup never takes the mission down. Definition order matters (Lua 5.1): helpers precede use.
--
-- Paused-dedicated-server note (the flown Red Tide M1 finding, 2026-07-11): while a server sits
-- PAUSED, timer.getTime() is frozen, so every pre-start slot-in schedules its card for the same
-- sim instant and they all fire ~START_DELAY s after UNPAUSE -- minutes after each pilot actually
-- sat down. That is the intended contract (the sandbox has no wall clock; nothing can fire during
-- a pause), and it is per-group text so each pilot still sees only their own card -- but it makes
-- the BEEP the attention cue that matters, and the beep was silently dead: an in-miz sound plays
-- ONLY with its "l10n/DEFAULT/" archive path, and the bare basename failed without an error.
---------------------------------------------------------------------------------------------------

if not (dcsRetribution and dcsRetribution.briefing) then
    return
end

local data = dcsRetribution.briefing

-- Defaults. Overridable via the plugin options (dcsRetribution.plugins.briefing).
local DURATION = 12 -- s each card stays on screen
local GRACE = 2 -- s before the mission-start sweep
local START_DELAY = 5 -- s after slot-in before the first card + beep (don't slam it up instantly)
local GROUND_FREQ = "249.50" -- the ground/startup freq on the taxi card (a fixed squadron freq)
local PLAY_SOUND = true -- play the beep as each card flashes
-- An ORIGINAL beep bundled with the plugin (otherResourceFiles), NOT copied from any campaign.
-- The wav lands in the miz at l10n/DEFAULT/, and DCS resolves in-miz sounds ONLY with that
-- archive-path prefix -- a bare basename fails SILENTLY (the flown Red Tide M1 dead-beep bug).
local SOUND_FILE = "l10n/DEFAULT/briefing-beep.wav"

if dcsRetribution.plugins and dcsRetribution.plugins.briefing then
    local o = dcsRetribution.plugins.briefing
    DURATION = tonumber(o.durationS) or DURATION
    GRACE = tonumber(o.startGraceS) or GRACE
    if tonumber(o.startDelayS) ~= nil then
        START_DELAY = tonumber(o.startDelayS)
    end
    if o.groundFreq ~= nil and tostring(o.groundFreq) ~= "" then
        GROUND_FREQ = tostring(o.groundFreq)
    end
    if o.playSound ~= nil then
        PLAY_SOUND = o.playSound == true or o.playSound == "true"
    end
end

-- Play the notification beep to one group (the card just flashed for them). outSoundForGroup DOES
-- exist (unlike outPictureForGroup), so the beep is per-pilot, on their slot-in.
local function beep(groupId)
    if not PLAY_SOUND then
        return
    end
    pcall(trigger.action.outSoundForGroup, groupId, SOUND_FILE)
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

-- The second card: the startup/taxi instruction, addressed to the pilot's callsign.
local function buildTaxiCard(rec)
    local lines = {
        str(rec.callsign, "-"),
        "",
        "Get started up, Contact ground @ " .. GROUND_FREQ .. " when ready to taxi.",
    }
    return table.concat(lines, "\n")
end

local shownAt = {} -- unit name -> last mission time the card was shown

-- Show the card to the group of a player unit, unless we just showed it (debounce).
local showFor -- forward declaration: the nil-player re-check below re-enters it
showFor = function(unit, retried)
    if not (unit and unit.isExist and unit:isExist()) then
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
    -- Players only: an AI birth returns nil here, so AI flights are never shown a card. BUT
    -- getPlayerName can also be nil AT the birth instant (a documented DCS event-timing race,
    -- MOOSE #806 -- the initiator isn't always fully registered when the handler runs), so a
    -- nil in a briefing-listed group gets ONE delayed re-check before being written off as AI.
    local player = unit:getPlayerName()
    if not player then
        if not retried then
            timer.scheduleFunction(function()
                pcall(showFor, unit, true)
                return nil
            end, {}, timer.getTime() + 2)
        end
        return
    end
    local uname = unit:getName()
    local last = shownAt[uname]
    if last and (timer.getTime() - last) < DEBOUNCE then
        return
    end
    shownAt[uname] = timer.getTime()
    local gname = grp:getName()
    local card = buildCard(rec)
    local taxi = buildTaxiCard(rec)
    -- Wait START_DELAY s after slot-in before the first card + beep (don't slam it up the instant
    -- the pilot takes the seat); the taxi card follows DURATION s after that. Both re-fetch the
    -- group by name at fire time so a pilot who left their seat is skipped. Each fire is logged --
    -- the M1 no-show hunt found the plugin had zero per-card logging, so dcs.log couldn't tell
    -- "card sent but unseen" from "card never sent"; the env.info lines are that discriminator.
    timer.scheduleFunction(function()
        local g = Group.getByName(gname)
        if g and g:isExist() then
            local gid = g:getID()
            trigger.action.outTextForGroup(gid, card, DURATION, false)
            env.info(
                string.format("BRIEFING|: card -> %s gid=%s t=%.0f", gname, tostring(gid), timer.getTime())
            )
            beep(gid)
            timer.scheduleFunction(function()
                local g2 = Group.getByName(gname)
                if g2 and g2:isExist() then
                    trigger.action.outTextForGroup(g2:getID(), taxi, DURATION, false)
                    env.info(
                        string.format(
                            "BRIEFING|: taxi -> %s gid=%s t=%.0f",
                            gname,
                            tostring(g2:getID()),
                            timer.getTime()
                        )
                    )
                    beep(g2:getID())
                end
                return nil
            end, {}, timer.getTime() + DURATION)
        else
            -- The pilot left before the card fired: it never showed, so don't let the debounce
            -- eat their next slot-in.
            shownAt[uname] = nil
            env.info("BRIEFING|: card skipped (group gone) -> " .. gname)
        end
        return nil
    end, {}, timer.getTime() + START_DELAY)
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
