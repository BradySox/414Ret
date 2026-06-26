-- 414th TARS (Tactical Air Recon System) initialization & Retribution bridge.
-- Loaded by the mission generator immediately AFTER TARS.lua, which is loaded
-- after the base plugin's Moose.lua. TARS.lua only defines the class; it does
-- NOT self-instantiate, so this file owns TARS:New() and all 414th config.
--
-- Three jobs:
--   1. Override the two TARS defaults that are wrong for a Retribution theater:
--      targetNameFilter (stock keywords USA/USSR would hide every Retribution
--      target) and the allowedAmmo loadout whitelist (stock list excludes
--      AIM-7/AIM-54, so the shipped F-14 TARPS payload would fail ground
--      validation and the F10 film menu would never unlock).
--   2. Apply the player-facing plugin options (scoring, film limit, menu scope).
--   3. Bridge captured-target snapshots back to Retribution's BDA fog-of-war by
--      appending them to the global tars_recon_captures table that
--      dcs_retribution.lua serializes into state.json (see game/debriefing.py
--      and game/sim/missionresultsprocessor.py for the Python side).

if TARS == nil then
    env.warning("tars_414_init: TARS is not loaded; skipping 414th TARS setup")
    return
end

local function opt(key, default)
    if dcsRetribution
        and dcsRetribution.plugins
        and dcsRetribution.plugins.tars
        and dcsRetribution.plugins.tars[key] ~= nil
    then
        return dcsRetribution.plugins.tars[key]
    end
    return default
end

-- ---------------------------------------------------------------------------
-- Theater-correct defaults (must run before any capture session starts).
-- ---------------------------------------------------------------------------

-- Detect ALL enemy units. Stock TARS ships an enabled name filter keyed to
-- "USA"/"USSR"; Retribution never names units that way, so leaving it on would
-- silently report nothing.
TARS.targetNameFilter = TARS.targetNameFilter or {}
TARS.targetNameFilter.enabled = false

-- Photograph ground + naval targets (the things BDA cares about), not aircraft.
TARS.units = { air = false, ground = true, ship = true }

-- Loadout whitelist. enforceLoadout defaults OFF: Retribution builds the TARPS
-- loadout deterministically, so the anti-cheat whitelist adds little and would
-- otherwise block the menu whenever the payload carries a weapon whose DCS
-- displayName is not in the stock list (e.g. AIM-7/AIM-54). With it off we make
-- the whitelist accept any weapon via an __index metatable returning true --
-- this needs no guessing at exact DCS displayName strings. With it on, the stock
-- whitelist applies (plus the F-14 AAMs added below as a best effort).
if opt("enforceLoadout", false) == true then
    TARS.allowedAmmo = TARS.allowedAmmo or {}
    -- Best-effort additions so the common F-14 air-to-air fit still validates.
    for _, name in ipairs({
        "AIM-7E", "AIM-7F", "AIM-7M", "AIM-7MH", "AIM-7P",
        "AIM-54A-Mk47", "AIM-54A-Mk60", "AIM-54C-Mk47",
    }) do
        TARS.allowedAmmo[name] = true
    end
else
    TARS.allowedAmmo = setmetatable({}, {
        __index = function()
            return true
        end,
    })
end

-- ---------------------------------------------------------------------------
-- Player-facing options.
-- ---------------------------------------------------------------------------
TARS.mooseScoring = opt("scoring", true) == true
TARS.valueScoring = tonumber(opt("scoreValue", 100)) or 100
local filmLimit = tonumber(opt("filmLimit", 25))
if filmLimit and filmLimit > 0 then
    TARS.filmLimitEnabled = true
    TARS.filmLimitMax = filmLimit
end

-- Restrict the F10 film menu to flights whose group name carries the keyword
-- (Retribution names auto-paired recon flights "TARPS ..."). Off by default so
-- any player in a recon-capable airframe gets the menu.
if opt("restrictToNamed", false) == true then
    TARS.recoNameFilter = { enabled = true, keyword = "TARPS" }
else
    TARS.recoNameFilter = { enabled = false, keyword = "TARPS" }
end

-- ---------------------------------------------------------------------------
-- Instantiate. TARS:New() registers all DCS event handlers internally.
-- ---------------------------------------------------------------------------
local mytars = TARS:New(opt("locale", "en"))
if mytars == nil then
    env.warning("tars_414_init: TARS:New() returned nil; recon disabled")
    return
end

if opt("srs", false) == true then
    -- nil path -> MOOSE auto-detects the server-side SRS install (MSRS.path).
    -- TARS reads its own srsPort option (defaults to the common SRS port 5002).
    local port = tonumber(opt("srsPort", 5002)) or 5002
    pcall(function()
        mytars:SetSRS(nil, 251, radio.modulation.AM, nil, nil, nil, nil, port)
    end)
end

-- ---------------------------------------------------------------------------
-- BDA bridge: record every photographed enemy unit into tars_recon_captures so
-- the Retribution debrief can confirm exactly what was seen (not just "a TARPS
-- flight overflew the target area"). tars_recon_captures + dirty_state are
-- globals owned by dcs_retribution.lua; guard in case load order ever changes.
-- ---------------------------------------------------------------------------
tars_recon_captures = tars_recon_captures or {}
local _logged_first_snapshot = false

function mytars:OnAfterDataProcessing(snap)
    if snap == nil then
        return self
    end

    -- One-time raw dump so the exact Snapshot schema can be confirmed in-game.
    if not _logged_first_snapshot then
        _logged_first_snapshot = true
        local keys = {}
        for k, _ in pairs(snap) do
            keys[#keys + 1] = tostring(k)
        end
        env.info(
            "DCSRetribution|TARS: first capture snapshot fields: "
                .. table.concat(keys, ", ")
        )
    end

    local name = snap.name or snap.unitName or snap.UnitName
    if type(name) == "string" and name ~= "" then
        tars_recon_captures[#tars_recon_captures + 1] = {
            unit = name,
            life = tonumber(snap.life),
            type = snap.type,
        }
        -- Make sure dcs_retribution.lua flushes the new capture.
        dirty_state = true
        env.info("DCSRetribution|TARS: recorded BDA capture for " .. name)
    end

    return self
end

env.info("DCSRetribution|TARS: initialised (v" .. tostring(TARS.version) .. ")")
