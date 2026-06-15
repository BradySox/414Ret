-- Civilian background air traffic injected by the 414Ret civilian_traffic plugin.
-- Do not edit in the Mission Editor. Edit the plugin source in 414Ret instead.
--
-- _CIVILIAN_TRAFFIC_EXCL is baked in by the Python preamble and contains every
-- airbase Retribution has assigned to combat operations this turn. Everything
-- else on the map (neutral only) becomes the civilian pool.
--
-- Two traffic layers:
--   FIXED-WING  (C-130, An-26, An-30, Yak-52, Christen Eagle)
--       -> fly between neutral AIRDROMES only (need a proper runway)
--   ROTARY      (Mi-8, UH-1, SA342)
--       -> fly between neutral AIRDROMES + HELIPORTS/FARPs (city hops)
--
-- Templates are named RAT_CIV_* and placed late-activated by the Python
-- mission generator. RAT clones them at runtime under neutral colours.
-- All distance limits removed -- any neutral field can reach any other.
-- Density scales automatically with the number of available fields.

local _excl = {}
for _, b in ipairs(_CIVILIAN_TRAFFIC_EXCL) do
    _excl[b] = true
end

local function _contains(text, needle)
    return string.find(text, needle, 1, true) ~= nil
end

local function _usable_fixed_wing_field(name, desc)
    return desc
        and desc.category == Airbase.Category.AIRDROME
        and not _contains(name, "Heliport")
        and not _contains(name, "FARP")
end

local function _usable_rotary_field(name, desc)
    return desc
        and (desc.category == Airbase.Category.AIRDROME
             or desc.category == Airbase.Category.HELIPAD)
        and not _contains(name, "Invisible FARP")
end

-- ── Airdrome pool (fixed-wing) ────────────────────────────────────────────────
-- Neutral airfields that are NOT being used by Retribution this turn.
-- Heliports/FARPs excluded -- fixed-wing can't taxi there.
local _airdromes = {}
for _, ab in pairs(world.getAirbases()) do
    local name = ab:getName()
    local desc = ab:getDesc()
    if not _excl[name]
        and ab:getCoalition() == coalition.side.NEUTRAL
        and _usable_fixed_wing_field(name, desc)
    then
        _airdromes[#_airdromes + 1] = name
    end
end

-- ── Helipad pool (rotary) ─────────────────────────────────────────────────────
-- Neutral heliports/FARPs + airdromes (helos can land anywhere).
-- Retribution's FARPs are in the exclusion list if they're assigned this turn.
local _helipads = {}
for _, ab in pairs(world.getAirbases()) do
    local name = ab:getName()
    local desc = ab:getDesc()
    if not _excl[name]
        and ab:getCoalition() == coalition.side.NEUTRAL
        and _usable_rotary_field(name, desc)
    then
        _helipads[#_helipads + 1] = name
    end
end

-- ── Density helper ────────────────────────────────────────────────────────────
-- Returns flights-per-template scaled to pool size, clamped to [lo, hi].
local function _density(pool_size, lo, hi)
    -- Keep the civilian layer materially lighter: about half the old density,
    -- while still leaving a little life on sparse maps.
    local n = math.ceil(pool_size * 0.3)
    if n < lo then n = lo end
    if n > hi then n = hi end
    return n
end

-- ── Spawn helper ──────────────────────────────────────────────────────────────
-- Creates a RAT instance from a named template and assigns it to the given pool.
-- Returns true on success, false if the template group wasn't found.
local function _spawn_rat(tmpl, pool, count, max_dist_nm)
    local ok, r = pcall(function() return RAT:New(tmpl) end)
    if not (ok and r) then return false end
    r:SetDeparture(pool)
    r:SetDestination(pool)
    r:SetMinDistance(5)           -- avoid same-field hops
    if max_dist_nm then
        r:SetMaxDistance(max_dist_nm)
    end
    r:SetTakeoff("hot")
    r:SetROE("hold")
    r:SetROT("evade")
    r:Invisible()
    r:RespawnAfterLanding(90)
    r:Spawn(count)
    return true
end

-- ── Fixed-wing templates ──────────────────────────────────────────────────────
local _fw_count  = 0
local _fw_spawns = 0

if #_airdromes >= 2 then
    local n = _density(#_airdromes, 1, 5)    -- half the old 2-10 density band
    local fw_templates = {
        "RAT_CIV_C130",
        "RAT_CIV_AN26",
        "RAT_CIV_AN30",
        "RAT_CIV_YAK52",
    }
    for _, tmpl in ipairs(fw_templates) do
        if _spawn_rat(tmpl, _airdromes, n, nil) then   -- no distance cap
            _fw_count  = _fw_count  + 1
            _fw_spawns = _fw_spawns + n
        end
    end
end

-- ── Rotary templates ──────────────────────────────────────────────────────────
local _helo_count  = 0
local _helo_spawns = 0

if #_helipads >= 2 then
    local n = _density(#_helipads, 1, 4)     -- half the old 2-8 density band
    local helo_templates = {
        "RAT_CIV_MI8",
        "RAT_CIV_UH1",
        "RAT_CIV_SA342",
    }
    for _, tmpl in ipairs(helo_templates) do
        -- No distance cap: on large/sparse maps a 100 nm cap left isolated departure
        -- fields with no reachable destination, so RAT spammed "No valid destination
        -- airport could be found" every respawn. Uncapped matches the error-free
        -- fixed-wing layer; SetMinDistance(5) still prevents same-field hops.
        if _spawn_rat(tmpl, _helipads, n, nil) then
            _helo_count  = _helo_count  + 1
            _helo_spawns = _helo_spawns + n
        end
    end
end

env.info(string.format(
    "414Ret civilian_traffic: fixed-wing: %d neutral airdromes, %d type(s), %d flights | " ..
    "rotary: %d helipads+airdromes, %d type(s), %d flights",
    #_airdromes, _fw_count,   _fw_spawns,
    #_helipads,  _helo_count, _helo_spawns))
