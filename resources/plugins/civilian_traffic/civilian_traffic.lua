-- Civilian background air traffic injected by the 414Ret civilian_traffic plugin.
-- Do not edit in the Mission Editor. Edit the plugin source in 414Ret instead.
--
-- The Python preamble bakes in four globals:
--   _CIVILIAN_TRAFFIC_EXCL      every airbase Retribution assigned to combat ops
--                               this turn (skipped as a departure/destination).
--   _CIVILIAN_TRAFFIC_FRONTS    active front-line contested points {x=, y=}
--                               (x = DCS x, y = DCS z) -- a keep-out bubble is
--                               dropped around each so civilians never spawn in
--                               the fight.
--   _CIVILIAN_TRAFFIC_KEEPOUT   keep-out radius in metres.
--   _CIVILIAN_TRAFFIC_MAXDIST_* per-layer regional route cap in km.
--   _CIVILIAN_TRAFFIC_STRAY_CHANCE  prob. a field inside the keep-out is kept
--                               anyway (soft keep-out -- rare strays into the fight).
--
-- Two traffic layers:
--   FIXED-WING  (C-130, An-26, An-30, Yak-52)
--       -> fly between neutral AIRDROMES only (need a proper runway)
--   ROTARY      (Mi-8, UH-1, SA342)
--       -> fly between neutral AIRDROMES only (heliports/FARPs dropped 2026-06-21:
--          unresolvable heliport ids spawned malformed helos that crashed the sim)
--
-- Routing intent: RAT flies a STRAIGHT LINE from departure to destination with no
-- along-route avoidance, so to keep civilians clear of the battle we shape the
-- ENDPOINTS. We (1) usually drop neutral fields inside the front keep-out bubble and
-- (2) cap each leg's distance so flights are short regional hops between nearby
-- fields rather than random cross-theatre legs that cut through the front. A
-- distance cap alone made RAT spam "No valid destination airport could be found"
-- when an isolated field had no partner in range, so we first PRUNE the pool to
-- fields that have a neighbour within the cap (i.e. keep only fields in a cluster
-- of >= 2). Templates are named RAT_CIV_* and placed late-activated by the Python
-- mission generator. RAT clones them at runtime under neutral colours. Density
-- scales automatically with the (pruned) number of available fields.

local _excl = {}
for _, b in ipairs(_CIVILIAN_TRAFFIC_EXCL or {}) do
    _excl[b] = true
end

-- ── Silence RAT's benign routing-failure spam ────────────────────────────────
-- On large/sparse neutral maps a randomly chosen departure field sometimes has
-- no destination within the AIRCRAFT'S OWN range. That -- not our distance cap --
-- is the binding limit for short-range types (helos, light prop), which is why
-- uncapping SetMaxDistance alone never fully silenced it. MOOSE RAT broadcasts
-- "No valid destination..." / "Destination and departure are identical..." to
-- ALL players and re-fires it on every respawn. The condition is harmless -- RAT
-- just skips that spawn and retries -- so we drop only those two on-screen
-- messages. RAT still logs them via self:E, so nothing is lost for debugging.
-- Installed once, mission-wide; exact substring match so no other message is hit.
-- (MESSAGE is always defined here: civilian_traffic loads after Moose.lua.)
if MESSAGE and not _G._CIV_RAT_MSG_SILENCED then
    _G._CIV_RAT_MSG_SILENCED = true
    local _orig_ToAll = MESSAGE.ToAll
    local _rat_spam = {
        "No valid destination airport could be found",
        "Destination and departure are identical",
    }
    function MESSAGE:ToAll(Settings, Delay)
        local txt = self.MessageText or ""
        for _, sig in ipairs(_rat_spam) do
            if string.find(txt, sig, 1, true) then
                return self  -- swallow the broadcast; RAT's log line still fires
            end
        end
        return _orig_ToAll(self, Settings, Delay)
    end
end

-- Front-line contested points, normalised to {x, z} (horizontal plane) so they
-- compare directly against airbase points from getPoint().
local _fronts = {}
for _, f in ipairs(_CIVILIAN_TRAFFIC_FRONTS or {}) do
    _fronts[#_fronts + 1] = { x = f.x, z = f.y }
end
local _keepout2 = (_CIVILIAN_TRAFFIC_KEEPOUT or 0) ^ 2
local _maxdist_fw_km   = _CIVILIAN_TRAFFIC_MAXDIST_FW    -- nil => no cap (legacy)
local _maxdist_helo_km = _CIVILIAN_TRAFFIC_MAXDIST_HELO
-- Soft keep-out: a field inside the front bubble is usually dropped, but kept
-- with this small probability so civilians occasionally stray into the fight.
local _stray_chance = _CIVILIAN_TRAFFIC_STRAY_CHANCE or 0

local function _contains(text, needle)
    return string.find(text, needle, 1, true) ~= nil
end

-- A field that isn't a real runway airfield, even if DCS reports it as AIRDROME.
-- The category check alone is NOT enough: on some maps (notably GermanyCW) FARPs /
-- helipads are registered with Airbase.Category.AIRDROME AND named without the literal
-- "Heliport"/"FARP" substrings (e.g. "H GDR 05", "H Med FRG 24", "H Radar GDR 01",
-- "... Invisible FARP 0"), so they slip past both gates into the civilian pool. RAT then
-- spawns at an unresolvable heliport id ("No heliport NNNN found ... aircraft spawn on
-- land"), producing a malformed / "Corrupt damage model" helo whose descriptor is nil;
-- FLIGHTGROUP:New fails and the orphaned hot-start unit crashes the sim in the
-- scheduled-action path (wSimCalendar::DoActionsUntil). Crash reproduced on a GermanyCW
-- Red Tide turn 1, 2026-06-24. Exclude the CWG helipad naming convention ("H " prefix:
-- "H <NATION> NN", "H Med ...", "H Radar ...") plus any HELIPAD / Invisible-FARP field.
-- Real CWG airdromes (Hahn, Haina, Hamburg, Kiel, Cologne, ...) have no "H " (H+space)
-- prefix, so this never excludes a real runway.
local function _is_nonrunway_field(name)
    return _contains(name, "Heliport")
        or _contains(name, "HELIPAD")
        or _contains(name, "FARP")
        or _contains(name, "Invisible")
        or string.find(name, "^H ") ~= nil
end

local function _usable_fixed_wing_field(name, desc)
    return desc
        and desc.category == Airbase.Category.AIRDROME
        and not _is_nonrunway_field(name)
end

local function _usable_rotary_field(name, desc)
    -- Restricted to real airdromes (2026-06-21 crash fix, hardened 2026-06-24): RAT picks
    -- a heliport/FARP id DCS can't resolve at spawn, producing a malformed helo whose
    -- descriptor is nil; FLIGHTGROUP:New fails and the orphaned hot-start unit crashes the
    -- sim. The 2026-06-21 category+name gate missed GermanyCW's AIRDROME-categorised FARPs
    -- (see _is_nonrunway_field). Real runways spawn helos cleanly. Trades the city-hop
    -- helipads for crash safety; helos still fly between neutral airfields.
    return desc
        and desc.category == Airbase.Category.AIRDROME
        and not _is_nonrunway_field(name)
end

-- ── Geometry helpers ──────────────────────────────────────────────────────────
-- Squared horizontal distance between two {x, z} points (no sqrt in hot loops).
local function _dist2(a, b)
    local dx = a.x - b.x
    local dz = a.z - b.z
    return dx * dx + dz * dz
end

-- A field is "in the combat zone" if it sits within the keep-out radius of any
-- active front. With no fronts (or no keep-out) this is always false.
local function _in_combat_zone(pt)
    if _keepout2 <= 0 then return false end
    for _, f in ipairs(_fronts) do
        if _dist2(pt, f) <= _keepout2 then return true end
    end
    return false
end

-- Whether a neutral field is admitted to the civilian pool. Fields clear of the
-- front always qualify; fields inside the keep-out bubble qualify only on a rare
-- "stray" roll, so the front stays mostly clear but isn't perfectly sterile.
local function _field_admitted(pt)
    if not _in_combat_zone(pt) then return true end
    return math.random() < _stray_chance
end

-- Horizontal {x, z} of an airbase (getPoint() y is altitude, ignored).
local function _field_point(ab)
    local p = ab:getPoint()
    return { x = p.x, z = p.z }
end

-- ── Reachable-neighbour prune ───────────────────────────────────────────────────
-- Drop any field with no OTHER field within cap_km, repeating until stable, so
-- every surviving field is guaranteed a valid destination within the cap. This is
-- what makes the distance cap safe (no "no valid destination" spam). With no cap
-- the whole pool is reachable, matching the legacy uncapped behaviour.
-- `fields` is an array of { name=, pt={x,z} }; returns the kept subset.
local function _prune_to_reachable(fields, cap_km)
    if not cap_km or cap_km <= 0 then
        return fields
    end
    local cap2 = (cap_km * 1000) ^ 2
    local kept = fields
    repeat
        local changed = false
        local next_kept = {}
        for i, a in ipairs(kept) do
            local has_neighbour = false
            for j, b in ipairs(kept) do
                if i ~= j and _dist2(a.pt, b.pt) <= cap2 then
                    has_neighbour = true
                    break
                end
            end
            if has_neighbour then
                next_kept[#next_kept + 1] = a
            else
                changed = true
            end
        end
        kept = next_kept
    until not changed
    return kept
end

local function _names(fields)
    local t = {}
    for _, f in ipairs(fields) do
        t[#t + 1] = f.name
    end
    return t
end

-- ── Airdrome pool (fixed-wing) ────────────────────────────────────────────────
-- Neutral airfields that are NOT being used by Retribution this turn and NOT
-- sitting in the front keep-out bubble. Heliports/FARPs excluded.
local _airdromes = {}
for _, ab in pairs(world.getAirbases()) do
    local name = ab:getName()
    local desc = ab:getDesc()
    if not _excl[name]
        and ab:getCoalition() == coalition.side.NEUTRAL
        and _usable_fixed_wing_field(name, desc)
    then
        local pt = _field_point(ab)
        if _field_admitted(pt) then
            _airdromes[#_airdromes + 1] = { name = name, pt = pt }
        end
    end
end

-- ── Rotary pool (airdromes only) ──────────────────────────────────────────────
-- Neutral airdromes only, same keep-out. Heliports/FARPs were dropped (2026-06-21):
-- on some maps RAT couldn't resolve a heliport id and spawned a malformed helo that
-- crashed the sim. Helos spawn cleanly at real runways.
local _helipads = {}
for _, ab in pairs(world.getAirbases()) do
    local name = ab:getName()
    local desc = ab:getDesc()
    if not _excl[name]
        and ab:getCoalition() == coalition.side.NEUTRAL
        and _usable_rotary_field(name, desc)
    then
        local pt = _field_point(ab)
        if _field_admitted(pt) then
            _helipads[#_helipads + 1] = { name = name, pt = pt }
        end
    end
end

local _airdromes_n = #_airdromes
local _helipads_n  = #_helipads
_airdromes = _prune_to_reachable(_airdromes, _maxdist_fw_km)
_helipads  = _prune_to_reachable(_helipads,  _maxdist_helo_km)

-- ── Density helper ────────────────────────────────────────────────────────────
-- Returns flights-per-template scaled to pool size, clamped to [lo, hi].
local function _density(pool_size, lo, hi)
    -- Keep the civilian layer light: roughly a quarter of the original density
    -- (halved again after playtest feedback that traffic was still too busy),
    -- while still leaving a little life on sparse maps.
    local n = math.ceil(pool_size * 0.15)
    if n < lo then n = lo end
    if n > hi then n = hi end
    return n
end

-- ── Spawn helper ──────────────────────────────────────────────────────────────
-- Creates a RAT instance from a named template and assigns it to the given pool.
-- Returns true on success, false if the template group wasn't found.
local function _spawn_rat(tmpl, pool, count, max_dist_km)
    local ok, r = pcall(function() return RAT:New(tmpl) end)
    if not (ok and r) then return false end
    r:SetDeparture(pool)
    r:SetDestination(pool)
    r:SetMinDistance(5)           -- avoid same-field hops
    if max_dist_km then
        -- Regional cap: keeps civilian legs short so straight-line routes stay
        -- in the rear and don't cut across the front. Safe because the pool was
        -- pruned to fields that have a neighbour within this cap.
        r:SetMaxDistance(max_dist_km)
    end
    r:SetTakeoff("hot")
    r:SetROE("hold")
    r:SetROT("evade")
    r:Invisible()
    -- Silence RAT's ATC broadcasts. With RespawnAfterLanding the civilian pool
    -- lands and respawns constantly, and RAT.ATC.messages (default ON) spams every
    -- player "cleared for landing"/"welcome to <field>" on each cycle. This only
    -- gates the MESSAGE:ToAll text; ATC landing sequencing (ClearToLand) still runs.
    r:ATC_Messages(false)
    r:RespawnAfterLanding(90)
    r:Spawn(count)
    return true
end

-- ── Fixed-wing templates ──────────────────────────────────────────────────────
local _fw_count  = 0
local _fw_spawns = 0

if #_airdromes >= 2 then
    local pool = _names(_airdromes)
    local n = _density(#_airdromes, 1, 3)    -- lighter fixed-wing band
    local fw_templates = {
        "RAT_CIV_C130",
        "RAT_CIV_AN26",
        "RAT_CIV_AN30",
        "RAT_CIV_YAK52",
    }
    for _, tmpl in ipairs(fw_templates) do
        if _spawn_rat(tmpl, pool, n, _maxdist_fw_km) then
            _fw_count  = _fw_count  + 1
            _fw_spawns = _fw_spawns + n
        end
    end
end

-- ── Rotary templates ── DISABLED (sim-crash safety) ───────────────────────────
-- Civilian helicopters are intentionally NOT spawned. RAT helo spawns repeatedly
-- produced a malformed unit with a nil descriptor ("Corrupt damage model"), which
-- DCS then HARD-CRASHES on inside Transport.dll via woCharacterHuman::GetPosition.
-- This was whack-a-moled for weeks with progressively tighter spawn-field gates
-- (real-runways-only, category + name filters for FARP/heliport ids) -- but a
-- leaked RAT_CIV_UH1 still crashed the sim (dcs.log 2026-06-25, GermanyCW). The
-- fixed-wing civilian layer above carries the immersion and never crashes, so the
-- rotary layer is dropped entirely for stability. (_helipads is still computed
-- above so the summary line reports the pool size.) Re-enable ONLY if RAT's
-- malformed-helo / descriptor-nil spawn bug is genuinely fixed upstream.
local _helo_count  = 0
local _helo_spawns = 0

env.info(string.format(
    "414Ret civilian_traffic: %d front keep-out(s) | " ..
    "fixed-wing: %d->%d neutral airdromes (after prune), %d type(s), %d flights | " ..
    "rotary: %d->%d helipads+airdromes (after prune), %d type(s), %d flights",
    #_fronts,
    _airdromes_n, #_airdromes, _fw_count,   _fw_spawns,
    _helipads_n,  #_helipads,  _helo_count, _helo_spawns))
