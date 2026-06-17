-- 414th Flight Control (ATC tower comms) initialization.
-- Loaded by the mission generator after the base plugin's Moose.lua. The
-- generator emits a dcsRetribution.FlightControl table holding the friendly
-- airdrome list (name + ATC frequency) plus SRS/limit options; this file spins
-- up one MOOSE FLIGHTCONTROL instance per airbase.
--
-- Scope is PLAYERS-ONLY by intent. FLIGHTCONTROL inherently observes AI flights
-- at its airbase, but we keep the AI taxi/landing limits generous so it does not
-- queue/strangle AI scrambles (QRA/CAP), and only transmits when players are
-- present. The main in-game check is that AI launches from these bases are
-- unaffected.
--
-- FLIGHTCONTROL:New() returns nil for anything that is not an AIRDROME (FARPs and
-- ships are skipped by MOOSE itself) and builds its own backup holding pattern,
-- so no per-base zone setup is required here. SRS voice is auto-detected from the
-- server-side install (MSRS.path); with no SRS it degrades to text subtitles.

if FLIGHTCONTROL == nil then
    env.warning("flightcontrol_414_init: FLIGHTCONTROL not in this MOOSE build; skipping")
    return
end

local cfg = dcsRetribution and dcsRetribution.FlightControl
if cfg == nil or type(cfg.airbases) ~= "table" then
    env.info("DCSRetribution|FlightControl: no airbases supplied; nothing to do")
    return
end

-- Player-facing options come from the plugin.json mnemonics; the airbase list is
-- emitted separately by the mission generator into dcsRetribution.FlightControl.
local function opt(key, default)
    if dcsRetribution.plugins
        and dcsRetribution.plugins.flightcontrol
        and dcsRetribution.plugins.flightcontrol[key] ~= nil
    then
        return dcsRetribution.plugins.flightcontrol[key]
    end
    return default
end

local port = tonumber(opt("srsPort", 5002)) or 5002
local subtitles = opt("subtitles", true) ~= false
-- Generous so AI flow stays effectively pass-through (players-only intent).
local maxLanding = tonumber(opt("maxLanding", 99)) or 99
local maxTaxi = tonumber(opt("maxTaxi", 99)) or 99

-- MOOSE FLIGHTCONTROL identifies a busy parking spot's occupant with
-- FindClosestUnit, which only sees UNITs. Retribution parks STATIC objects on
-- some ramp spots (Kutaisi is the usual offender), so those spots are left
-- untracked ("NOT FREE but no unit could be found there") and the status loop
-- then warns "Number of parking spots does not match!" every cycle for the whole
-- mission. Mark each orphan (Status == nil after init) OCCUPIED so the counts
-- reconcile -- killing the recurring log spam -- and FLIGHTCONTROL keeps the
-- static-held spots out of its taxi/assignment pool. _InitParkingSpots() runs
-- synchronously inside fc:Start(), so fc.parking is populated by the time we run.
local function reconcile_orphan_parking(fc)
    if type(fc.parking) ~= "table" then
        return 0
    end
    local fixed = 0
    for _, spot in pairs(fc.parking) do
        if spot.Status == nil then
            fc:SetParkingOccupied(spot, "RetributionStatic")
            fixed = fixed + 1
        end
    end
    return fixed
end

local started = 0
for _, ab in ipairs(cfg.airbases) do
    local ok, err = pcall(function()
        if type(ab.name) ~= "string" or ab.name == "" then
            return
        end
        local freq = tonumber(ab.freq) or 305
        local mod = tonumber(ab.modulation) or radio.modulation.AM

        local fc = FLIGHTCONTROL:New(ab.name, freq, mod, nil, port)
        if fc == nil then
            -- Not an airdrome, or airbase not found on this theater.
            return
        end

        fc:SetLimitLanding(maxLanding, maxLanding)
        fc:SetLimitTaxi(maxTaxi, false, maxLanding)
        fc:SetTransmitOnlyWithPlayers(true)
        fc:SetRadioOnlyIfPlayers(true)
        if subtitles then
            fc:SwitchSubtitlesOn()
        else
            fc:SwitchSubtitlesOff()
        end
        fc:Start()
        local fixed = reconcile_orphan_parking(fc)
        if fixed > 0 then
            env.info(string.format(
                "DCSRetribution|FlightControl: %s reconciled %d static-occupied parking spot(s)",
                ab.name,
                fixed
            ))
        end
        started = started + 1
    end)
    if not ok then
        env.warning(
            "DCSRetribution|FlightControl: failed to start ATC at "
                .. tostring(ab.name) .. ": " .. tostring(err)
        )
    end
end

env.info("DCSRetribution|FlightControl: started ATC at " .. tostring(started) .. " airbase(s)")
