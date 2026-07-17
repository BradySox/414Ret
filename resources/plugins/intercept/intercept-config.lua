-- Intercept (QRA) — drives AI_A2A_DISPATCHER per coalition from
-- dcsRetribution.Intercept. Aircraft are placed as late-activated template
-- groups by the mission generator; ParkDefender spawns parked instances and
-- recycles them on RTB, consuming a resource permanently on a kill.
--
-- Detection (dr-ktw0): the dispatcher's DETECTION_AREAS is fed from the real
-- EWR/SAM-as-EWR group names published in dcsRetribution.IADS for the
-- coalition (the same source Skynet uses). The previous FilterPrefixes("EWR")
-- matched almost nothing, because DCS EWR group names are suffix-form
-- ("1L13 EWR", "55G6 EWR").
--
-- Detection has two sources: the IADS EWR/SAM-as-EWR network (primary, wide
-- area) and a hidden/invisible/immortal backstop EWR at each alert base
-- (guaranteed fallback — catches anything that slips through or survives after
-- the EWR network is destroyed). The backstop always spawns; it is independent
-- of GciRadius.
--
-- GciRadius (groundControlledInterceptionMaxRadius, default 100 NM) caps how
-- far from a base a detected raid can trigger a scramble. The dispatcher only
-- scrambles GCI once AirbaseDistance <= GciRadius. The IADS network provides
-- the real detection range; GciRadius just prevents scrambling against very
-- distant threats heading elsewhere.
--
-- FORWARD DEFENSE (414th, qra_forward_defense). GciRadius alone cannot express
-- "rear bases answer raids at the front, but the front base does not chase deep
-- into enemy territory": it is one radius measured from EVERY base, so widening
-- it to bring rear fields forward simultaneously lets the forward field chase
-- just as far the other way. The two are separated by giving the dispatcher a
-- BORDER ZONE:
--
--   * SetBorderZone(zones) -> Detection:SetAcceptZones(zones). Moose drops any
--     detected object outside every accept zone, so the dispatcher cannot see --
--     cannot scramble against, cannot keep engaging -- a target beyond the
--     defended airspace. This decides WHERE a side may fight (geography).
--   * SetGciRadius decides HOW FAR a base will launch to get there (reach). It is
--     safe to open up once geography is bounded.
--   * SetDisengageRadius must open with it: Moose aborts a defender once
--     DistanceFromHomeBase > DisengageRadius (default 300 km ~= 162 NM), so a base
--     at the far edge of its reach would otherwise launch and turn around.
--
-- Widening the reach does NOT mass-launch every base. Moose's GCI loop keeps the
-- squadron with the shortest intercept distance among those inside GciRadius, and
-- only reaches back to a farther one once the closer squadron's alert is spent --
-- an echelon: the front field answers, the rear fields backfill.
--
-- The zones are emitted per coalition by the mission generator (one circle per
-- control point; a front-line CP's circle is grown to reach a little past its own
-- FLOT). No zones emitted => SetBorderZone is skipped => legacy behaviour.
--
-- The backstop EWR DCS type is supplied per record by the mission generator
-- (rec.backstopEwrType) rather than hardcoded here. If the type is unknown to
-- the running DCS build, mist.dynAdd silently spawns nothing; we therefore
-- verify each backstop group exists before trusting it as a detection source
-- and fall back to the EWR network for that base otherwise.
--
-- Build timing: backstop EWRs are spawned with mist.dynAdd up front, but the
-- detection SET_GROUP (and the dispatcher) are assembled BUILD_DELAY seconds
-- later. mist.dynAdd registers a group via a birth event on the next frame, so
-- a SET_GROUP:FilterStart() built synchronously would not yet see the backstop.
-- The short delay lets the groups register first.
--
-- AI_A2A_DISPATCHER:New() calls self:__Start(5) internally — no explicit
-- dispatcher:Start() call is needed or valid (no such method exists).
--
-- Spawn path: NON-VISIBLE / fresh-spawn-on-scramble. We deliberately do NOT
-- call SetSquadronVisible. That keeps Moose's AI_A2A_DISPATCHER:ResourceActivate
-- in its else branch, which spawns a fresh group at scramble time honoring the
-- configured takeoff method (SetDefaultTakeoffInAir below).
--
-- Takeoff method history (all validated in-DCS):
--   1. Visible/ParkDefender pre-park: ParkDefender hardcodes SPAWN.Takeoff.Cold
--      (ignores SetDefaultTakeoff*), so F-16s sat cold and never completed the
--      cold-start→taxi sequence. SetSquadronVisible also clamps ResourceCount to
--      free parking spots and forces Grouping=1. Abandoned.
--   2. Non-visible ParkingHot (warm): F-16s DID scramble warm but still never
--      taxied out of congested ramps (e.g. Tiyas, packed with OCA + ~30 rotary
--      BARCAP — confirmed in-DCS), while
--      the identical code launched fine from uncluttered bases like H3. Ground
--      movement, not takeoff method, was the blocker.
--   3. Runway: SetDefaultTakeoffFromRunway spawned fine at uncluttered H3 (jets on
--      the runway, immediate takeoff) but at saturated Tiyas Moose could not place
--      them on the runway and dumped them into hangars, where they sat. Every
--      ground spawn (cold/hot/runway) fails on a fully-packed ramp.
--   4. In-air (current): the only method that escapes the congested ground. It was
--      blocked by a Moose bug (air-spawn's BASE:CreateEventTakeoff is mis-scheduled
--      → self is a plain table → self:F() crash → defenders never activate). The
--      BASE.CreateEventTakeoff monkeypatch above repairs that without touching the
--      vendored Moose.lua, so in-air now works. Upstream fix filed as MOOSE PR
--      #2595 (Core/Spawn.lua: pass the args as varargs, not a single table);
--      drop the monkeypatch once that lands in the vendored Moose.lua.
--
-- The non-visible path keeps full reserve and real 2-ship grouping (the visible
-- path lost both).
--
-- SPAWN PROFILE (2026-06-21): the in-air spawn previously inherited the parking
-- template's ~0 kt speed and a global 2,000 m MSL altitude, so jets spawned stalled
-- and high and dove ~4,600 ft recovering (near-crash at Vaziani, Tacview 2026-06-20).
-- Each squadron now air-spawns at a forced scramble speed (InitSpeedKnots) and a
-- terrain-relative low altitude (field elevation + AGL). See SCRAMBLE_* below.
--
-- SetSquadronGci speed args are in km/h (WaypointAir divides by 3.6 to get m/s).
-- 900/1200 km/h ≈ 485/648 kt — reasonable for jet interceptors.

env.info("DCSRetribution|Intercept: configuring QRA dispatchers")

intercept_survivors = intercept_survivors or {}

do
    local _orig_message_to_players = DETECTION_MANAGER.MessageToPlayers
    function DETECTION_MANAGER:MessageToPlayers(Squadron, Message, DefenderGroup)
        if type(Message) == "string" then
            local lower_message = string.lower(Message)
            if string.find(lower_message, "landing at base", 1, true)
                or string.find(Message, "посадка на базу", 1, true)
            then
                return
            end
        end
        return _orig_message_to_players(self, Squadron, Message, DefenderGroup)
    end
end

-- Registry: maps squadronId -> { dispatcher, squadronName }. Populated by the
-- deferred dispatcher build (BUILD_DELAY seconds in), then read by the refresh
-- loop.
local intercept_registry = {}

-- QRA tuning (comms, GCI radius, engagement range) is sourced from the Campaign
-- Doctrine settings and carried on each Intercept record by the mission generator
-- (gciMaxRadiusNm/engagementRangeNm/commsEnabled). The values are global, so each
-- record in a coalition carries the same trio; build_dispatcher reads them from
-- records[1]. add_key_value serializes everything as a string, hence tonumber()
-- for the numerics and a string compare ("false") for the boolean.
local NM = 1852  -- metres per nautical mile
local DETECTION_GROUPING_M = 30000  -- contact-clustering radius for DETECTION_AREAS
local BUILD_DELAY = 5  -- seconds; let mist.dynAdd backstops register before SET_GROUP

-- QRA scramble spawn profile (414th tuning, 2026-06-21).
--   Speed: Moose's air-spawn (SpawnAtAirbase, Takeoff.Air) sets position + altitude
--   but NOT speed, so the cloned parking template spawns at ~0 kt. The jets spawn
--   stalled at altitude and dive ~4,600 ft clawing back airspeed — one Su-27 nearly
--   hit the ground at Vaziani (Tacview 2026-06-20). InitSpeed propagates to the
--   spawned units (Moose SpawnWithIndex), giving them a real scramble speed.
--   Altitude: SetDefaultTakeoffInAirAltitude is a single ABSOLUTE-MSL value for
--   every base, so a low global value spawns into terrain at high-elevation fields.
--   We instead anchor per-squadron to each base's field elevation + AGL, so they
--   come off the deck LOW like a scramble instead of materializing high with energy.
-- Both tunable; need an in-game pass.
local SCRAMBLE_SPEED_KT = 300   -- air-spawn airspeed (was effectively ~0 -> near-stall)
local SCRAMBLE_AGL_M = 760      -- ~2,500 ft above the LAUNCHING field's elevation

-- GCI-ambush hit-and-run leash (Vietnam campaign layer W5); applied only when the
-- generator marks a coalition's records ambushPosture=true (gci_ambush doctrine).
-- Both tunable; need an in-game pass (checklist M5).
local AMBUSH_DISENGAGE_NM = 50      -- break off when this far from home base (Moose default ~162 NM)
local AMBUSH_FUEL_THRESHOLD = 0.35  -- RTB at 35% fuel: one slash, then home (default 0.15)

-- ---------------------------------------------------------------------------
-- MOOSE BUG WORKAROUND — air-spawn takeoff event
-- Upstream fix filed as MOOSE PR #2595
-- (https://github.com/FlightControl-Master/MOOSE/pull/2595). REMOVE THIS WHOLE
-- `do … end` BLOCK once that PR is released and pulled into Retribution's
-- vendored resources/plugins/base/Moose.lua — check the SpawnAtAirbase call site
-- there passes the args as varargs (no surrounding braces) before deleting.
-- Core/Spawn.lua SpawnAtAirbase schedules the synthetic takeoff event as:
--   self:ScheduleOnce(5, BASE.CreateEventTakeoff, {GroupSpawned, time, dcsObject})
-- ScheduleOnce forwards its trailing args as VARARGS, so that single table becomes
-- argument #1 — i.e. CreateEventTakeoff runs with the {group,time,dcs} table as
-- `self`. A plain table has no :F(), so the first line (self:F(...)) errors, the
-- takeoff event never fires, and air-spawned AI_A2A_DISPATCHER defenders never
-- activate (observed: zero QRA flew on either side with takeoff=Air). A sibling
-- call site uses SCHEDULER:New(nil, fn, {args}, 5) — which DOES treat the table as
-- the arg list — and is correct; the SpawnAtAirbase one is the regression.
--
-- We don't touch the vendored Moose.lua: override BASE.CreateEventTakeoff to
-- detect the mis-packed call (self is the args table, has no :F) and fire a proper
-- takeoff event; all well-formed calls delegate to the original untouched. Remove
-- once the upstream fix is vendored. Upstream fix = drop the braces at that line so
-- the args pass as varargs.
-- ---------------------------------------------------------------------------
do
    local _orig_create_event_takeoff = BASE.CreateEventTakeoff
    function BASE:CreateEventTakeoff(EventTime, Initiator)
        if type(self) == "table" and type(self.F) ~= "function" then
            -- self is the mis-packed {GroupSpawned, time, dcsObject} table.
            world.onEvent({
                id = world.event.S_EVENT_TAKEOFF,
                time = self[2],
                initiator = self[3],
            })
            return
        end
        return _orig_create_event_takeoff(self, EventTime, Initiator)
    end
end

-- Build this coalition's defended-airspace zones (414th forward defense). Returns
-- an empty list when the generator emitted none (feature off, or no dispatcher),
-- in which case build_dispatcher skips SetBorderZone entirely.
--
-- DoNotRegisterZone=true: these are internal filter zones, not mission zones, so
-- they must not fire MOOSE's new-zone event for every control point on the map.
local function defense_zones_for(coalition_name)
    local zones = {}
    local all = dcsRetribution.Intercept and dcsRetribution.Intercept.ZONES
    local records = all and all[coalition_name]
    if not records then return zones end
    for _, rec in pairs(records) do
        local x = tonumber(rec.x)
        local y = tonumber(rec.y)
        local radius = tonumber(rec.radiusM)
        if x and y and radius and radius > 0 then
            zones[#zones + 1] = ZONE_RADIUS:New(rec.name, { x = x, y = y }, radius, true)
        end
    end
    return zones
end

-- Escape Lua pattern magic characters so a literal string can be used where
-- Moose treats it as a pattern (SET_GROUP:FilterPrefixes matches via string.find
-- with pattern semantics). We escape everything EXCEPT "-": Moose's FilterPrefixes
-- already gsubs "-" -> "%-" itself, so escaping it here would double-escape.
-- Same fix as mantis-config.lua's escape_prefix (the proven MANTIS FilterPrefixes
-- repair); the parenthesized capture makes "%1" valid in the replacement.
local function lua_pattern_escape(s)
    return (s:gsub("([%(%)%.%%%+%*%?%[%]%^%$])", "%%%1"))
end

-- Collect the EWR / SAM-as-EWR group names the IADS generator published for a
-- coalition. SamAsEwr entries already carry the DCS GROUP name, but standalone
-- Ewr entries carry the UNIT name (Skynet convention: dcs_name_for_group
-- returns unit_name for EWR/CC roles). SET_GROUP filters by group name, so we
-- resolve unit names to their parent group via UNIT:FindByName → GetGroup.
local function ewr_group_names(coalition_name)
    local names = {}
    local seen = {}
    local iads = dcsRetribution.IADS and dcsRetribution.IADS[coalition_name]
    if iads then
        for _, role in ipairs({ "Ewr", "SamAsEwr" }) do
            local list = iads[role]
            if list then
                for _, node in pairs(list) do
                    if node.dcsGroupName then
                        local group_name = node.dcsGroupName
                        local grp = GROUP:FindByName(group_name)
                        if not grp then
                            local unit = UNIT:FindByName(group_name)
                            if unit then
                                local parent = unit:GetGroup()
                                if parent then
                                    group_name = parent:GetName()
                                end
                            end
                        end
                        if not seen[group_name] then
                            seen[group_name] = true
                            names[#names + 1] = group_name
                        end
                    end
                end
            end
        end
    end
    return names
end

-- Make the backstop EWR invisible to enemy AI and immortal so the backstop
-- cannot be shot out. Deferred a few seconds so Moose has registered the
-- freshly spawned group.
local function protect_group(group_name)
    mist.scheduleFunction(function()
        local grp = GROUP:FindByName(group_name)
        if grp then
            grp:SetCommandInvisible(true)
            grp:SetCommandImmortal(true)
        end
    end, {}, timer.getTime() + 5)
end

-- Attempts to spawn a hidden backstop EWR. Returns true when a spawn was issued
-- (a valid type and country were supplied); the caller still verifies the group
-- actually exists before relying on it, since mist.dynAdd drops unknown types.
local function spawn_backstop_ewr(group_name, vec2, ewr_type, country_id)
    if not ewr_type or ewr_type == "" or not country_id then
        return false
    end
    mist.dynAdd({
        countryId = country_id,
        category = "vehicle",
        groupName = group_name,
        hidden = true,
        units = {
            {
                type = ewr_type,
                x = vec2.x,
                y = vec2.y,
                heading = 0,
                skill = "Excellent",
                name = group_name .. " radar",
            },
        },
    })
    protect_group(group_name)
    return true
end

local function build_dispatcher(coalition_name, records)
    if #records == 0 then return end

    -- Global QRA tuning, identical across this coalition's records (see header).
    local comms_enabled = records[1].commsEnabled ~= "false"
    local scramble_radius_nm = tonumber(records[1].gciMaxRadiusNm) or 60
    local engagement_range_nm = tonumber(records[1].engagementRangeNm) or 38
    -- Home-base disengage leash in NM (414th forward defense). 0/absent leaves
    -- Moose's own 300 km default alone, which is what pre-feature saves emit.
    local disengage_radius_nm = tonumber(records[1].disengageRadiusNm) or 0
    -- GCI-ambush posture (Vietnam campaign layer W5). The generator already
    -- shrank this side's engage/scramble radii for a late, close GCI slash; the
    -- Lua half is the hit-and-run leash below (disengage radius + fuel threshold).
    local ambush_posture = records[1].ambushPosture == "true"

    -- Always spawn a hidden backstop EWR at each defended base so there is a
    -- guaranteed detection source even when the IADS network is destroyed.
    -- This is independent of GciRadius — the backstop ensures detection, while
    -- GciRadius (set below) controls how far out a raid triggers a scramble.
    local backstop_names = {}
    do
        local seen_bases = {}
        for _, rec in ipairs(records) do
            local base_name = rec.airbaseName
            if not seen_bases[base_name] then
                seen_bases[base_name] = true
                local airbase = AIRBASE:FindByName(base_name)
                if airbase then
                    local vec2 = airbase:GetVec2()
                    -- Offset 300 m NE of the airbase centre so the invisible backstop
                    -- unit does not land on the runway and block ground traffic.
                    local ewr_vec2 = { x = vec2.x + 300, y = vec2.y + 300 }
                    local ewr_name = "QRA_Backstop_" .. coalition_name .. "_" .. base_name
                    if spawn_backstop_ewr(ewr_name, ewr_vec2, rec.backstopEwrType, tonumber(rec.countryId)) then
                        backstop_names[#backstop_names + 1] = ewr_name
                    end
                end
            end
        end
    end

    -- Assemble the dispatcher once the backstop groups have registered.
    mist.scheduleFunction(function()
        local detection_prefixes = ewr_group_names(coalition_name)
        for _, ewr_name in ipairs(backstop_names) do
            if GROUP:FindByName(ewr_name) then
                detection_prefixes[#detection_prefixes + 1] = ewr_name
            else
                env.info("DCSRetribution|Intercept: backstop EWR '"..ewr_name
                         .."' did not spawn (unknown type?); base falls back to EWR network.")
            end
        end

        if #detection_prefixes == 0 then
            env.info("DCSRetribution|Intercept: no detection sources for "
                     ..coalition_name.."; QRA will not scramble.")
            return
        end

        -- Moose SET_GROUP:FilterPrefixes matches names with Lua-pattern semantics
        -- (string.find, only "-" pre-escaped). Retribution IADS group names contain
        -- "(" / ")" (e.g. "0041 | LION (EWR)", "0114 | LORIKEET (S-300)"), which
        -- would be read as pattern captures and never match, leaving the wide-area
        -- EWR half of detection empty (only the paren-free QRA_Backstop_* names
        -- ever matched). Escape the full merged list — backstop names included —
        -- so each prefix matches its literal group name.
        local detection_patterns = {}
        for i, name in ipairs(detection_prefixes) do
            detection_patterns[i] = lua_pattern_escape(name)
        end

        local det_set = SET_GROUP:New()
            :FilterCoalitions(string.lower(coalition_name))
            :FilterPrefixes(detection_patterns)
            :FilterStart()

        local detection = DETECTION_AREAS:New(det_set, DETECTION_GROUPING_M)

        local dispatcher = AI_A2A_DISPATCHER:New(detection)
        -- Spawn interceptors already airborne near the base. See header for the
        -- full method history: every ground spawn (cold/hot/runway) leaves F-16s
        -- stuck on congested ramps like Tiyas; only in-air escapes it. In-air is
        -- viable here because the BASE.CreateEventTakeoff monkeypatch above fixes
        -- the Moose air-spawn crash that previously killed it. Altitude is metres.
        dispatcher:SetDefaultTakeoffInAir()
        -- Fallback only: each squadron overrides this with a terrain-relative low
        -- altitude below (SetSquadronTakeoffInAirAltitude). Kept as a safe MSL
        -- backstop if a base can't be resolved.
        dispatcher:SetDefaultTakeoffInAirAltitude(2000)  -- ~6,500 ft MSL (fallback)
        dispatcher:SetDefaultLandingAtEngineShutdown()
        dispatcher:SetIntercept(0)
        dispatcher:SetEngageRadius(engagement_range_nm * NM)
        dispatcher:SetTacticalDisplay(false)  -- debug F10 overview; off in normal play
        dispatcher:SetGciRadius(scramble_radius_nm * NM)
        -- Forward defense: confine this side to the airspace over its own bases and
        -- its own side of the front. Must be set BEFORE the first detection cycle
        -- resolves, which the BUILD_DELAY schedule already guarantees.
        local defense_zones = defense_zones_for(coalition_name)
        if #defense_zones > 0 then
            dispatcher:SetBorderZone(defense_zones)
            env.info("DCSRetribution|Intercept: " .. coalition_name .. " defends "
                     .. #defense_zones .. " zone(s); scramble radius "
                     .. scramble_radius_nm .. " NM")
        end
        if ambush_posture then
            -- Vietnam W5 hit-and-run: leash the defenders close to home
            -- (DistanceFromHomeBase > DisengageRadius aborts the engagement in
            -- Moose AI_AIR) and send them home early on fuel, so a MiG slashes
            -- the raid once and recovers instead of fighting to destruction.
            -- Moose's defaults are 300 km / 0.15.
            dispatcher:SetDisengageRadius(AMBUSH_DISENGAGE_NM * NM)
            dispatcher:SetDefaultFuelThreshold(AMBUSH_FUEL_THRESHOLD, 0)
        elseif disengage_radius_nm > 0 then
            -- Forward defense: a rear base transiting to the front would otherwise
            -- hit Moose's 300 km default and abort mid-intercept. The border zone
            -- above -- not this radius -- is what keeps defenders out of enemy
            -- airspace.
            dispatcher:SetDisengageRadius(disengage_radius_nm * NM)
        end
        if comms_enabled then
            dispatcher:SetSendMessages(true)
        end

        for _, rec in ipairs(records) do
            -- Moose keys squadrons by name; the squadron display name is not
            -- unique across bases (dr-wz6p), so append a short slice of the
            -- unique squadron id to avoid one base's QRA overwriting another's.
            local sq = rec.squadronName .. " #" .. string.sub(tostring(rec.squadronId), 1, 8)
            dispatcher:SetSquadron(sq, rec.airbaseName, { rec.templatePrefix }, tonumber(rec.resourceCount))
            dispatcher:SetSquadronGci(sq, 900, 1200)
            -- Scramble LOW: anchor the air-spawn to THIS base's field elevation
            -- + AGL so they come off the deck rather than spawning high with energy.
            -- (Global SetDefaultTakeoffInAirAltitude is absolute MSL and unsafe at
            -- high-elevation fields.) Falls back to the global default on lookup miss.
            local base = AIRBASE:FindByName(rec.airbaseName)
            if base then
                local ok_e, elev = pcall(function()
                    return base:GetCoordinate():GetLandHeight()
                end)
                if ok_e and elev then
                    dispatcher:SetSquadronTakeoffInAirAltitude(sq, elev + SCRAMBLE_AGL_M)
                end
            end
            -- Force a scramble airspeed. Moose air-spawn leaves the cloned parking
            -- template at ~0 kt (near-stall spawn); InitSpeed is applied to the
            -- air-spawned units, so they spawn fast enough to fly away cleanly.
            local sq_obj = dispatcher.DefenderSquadrons[sq]
            if sq_obj and sq_obj.Spawn then
                for _, sp in ipairs(sq_obj.Spawn) do
                    pcall(function() sp:InitSpeedKnots(SCRAMBLE_SPEED_KT) end)
                end
            end
            -- Aircraft launched per scramble. The generator rolls this per
            -- squadron toward a distributed-QRA posture (mostly singles, some
            -- pairs); fall back to a 2-ship if an older save omits the field.
            dispatcher:SetSquadronGrouping(sq, tonumber(rec.grouping) or 2)
            -- NOTE: deliberately NOT SetSquadronVisible — see header. Visible mode
            -- forces a cold pre-park (F-16 never taxis), clamps reserve to parking
            -- spots, and forces Grouping=1. Non-visible = in-air fresh-spawn on scramble.
            if comms_enabled then
                dispatcher:SetSquadronLanguage(sq, "EN")
            end
            intercept_survivors[rec.squadronId] = tonumber(rec.resourceCount)

            intercept_registry[rec.squadronId] = {
                dispatcher    = dispatcher,
                squadronName  = sq,
            }
        end
    end, {}, timer.getTime() + BUILD_DELAY)
end

-- ---------------------------------------------------------------------------
-- Survivor refresh
-- Formula: survivors(squadron) = parked ResourceCount
--                              + sum of GetSize() for each airborne Defender
--                                whose SquadronName matches.
--
-- GetSquadron throws on unknown name — we pcall it.
-- GetSize() returns nil when the GROUP has no DCS object; treat nil as 0.
-- DefenderTasks is keyed by Defender GROUP object; we iterate pairs() and
-- call GetDefenderTaskSquadronName(Defender) to match the squadron.
-- ---------------------------------------------------------------------------
local REFRESH_INTERVAL = 30  -- seconds between polls

local function refresh_survivors()
    for squadron_id, entry in pairs(intercept_registry) do
        local ok, err = pcall(function()
            local disp = entry.dispatcher
            local sq_name = entry.squadronName

            -- Parked count
            local parked = 0
            local sq_ok, sq_obj = pcall(function()
                return disp:GetSquadron(sq_name)
            end)
            if sq_ok and sq_obj and sq_obj.ResourceCount then
                parked = sq_obj.ResourceCount
            else
                -- GetSquadron threw or ResourceCount nil: keep last known value
                return
            end

            -- Airborne count: sum GetSize() for alive Defender groups in this squadron
            local airborne = 0
            local tasks = disp:GetDefenderTasks()
            for defender, _ in pairs(tasks) do
                local task_sq_name = disp:GetDefenderTaskSquadronName(defender)
                if task_sq_name == sq_name then
                    local sz = defender:GetSize()
                    if sz then
                        airborne = airborne + sz
                    end
                end
            end

            local survivors = math.max(0, parked + airborne)
            intercept_survivors[squadron_id] = survivors
        end)
        if not ok then
            env.info("DCSRetribution|Intercept: survivor refresh error for squadron "
                     ..tostring(squadron_id)..": "..tostring(err))
            -- keep last known value; do not write nil
        end
    end

    -- Self-reschedule (one-shot mist pattern, same as write_state_error_handling)
    mist.scheduleFunction(refresh_survivors, {}, timer.getTime() + REFRESH_INTERVAL)
end

-- ---------------------------------------------------------------------------
-- Player-manned QRA scramble cue (414th, §1 player-manning)
-- For each base with a player alert flight (dcsRetribution.Intercept.PLAYER_ALERT),
-- watch for hostile aircraft closing inside the cue radius and call the player to
-- scramble. The cue fires a lead margin BEYOND the AI scramble (GCI) radius so a
-- cold-started human has spool-up + taxi time. It is player-facing only and never
-- launches anything — the alert flight is a normal client flight the human flies.
-- Needs an in-game pass (checklist A4).
-- ---------------------------------------------------------------------------
local PLAYER_SCRAMBLE_LEAD_NM = 30   -- cue fires this far beyond the AI GCI radius
local PLAYER_ALERT_INTERVAL = 20     -- seconds between scans
local PLAYER_ALERT_REPEAT = 120      -- min seconds between re-announcements per base
local PLAYER_ALERT_DURATION = 25     -- seconds the on-screen call stays up

local COALITION_SIDE = { BLUE = coalition.side.BLUE, RED = coalition.side.RED }

-- base_vec2: MOOSE Vec2 {x=north, y=east}; p: DCS Vec3 {x=north, y=alt, z=east}.
local function alert_bearing_range(base_vec2, p)
    local north_delta = p.x - base_vec2.x
    local east_delta = p.z - base_vec2.y
    local brg = math.deg(math.atan2(east_delta, north_delta))
    if brg < 0 then brg = brg + 360 end
    local rng_nm = math.sqrt(north_delta * north_delta + east_delta * east_delta) / NM
    local angels = math.floor(((p.y or 0) * 3.28084) / 1000 + 0.5)
    return brg, rng_nm, angels
end

-- Nearest alive enemy aircraft (fixed- or rotary-wing) within max_dist_m of the
-- base, or nil. Uses the raw DCS coalition scan (cheap at QRA scale).
local function nearest_hostile(base_vec2, enemy_side, max_dist_m)
    local best_p, best_d
    for _, category in ipairs({ Group.Category.AIRPLANE, Group.Category.HELICOPTER }) do
        local ok, groups = pcall(coalition.getGroups, enemy_side, category)
        if ok and groups then
            for _, grp in ipairs(groups) do
                local units = grp:getUnits()
                if units then
                    for _, u in ipairs(units) do
                        if u:isExist() and u:getLife() > 0 then
                            local p = u:getPoint()
                            local dx = p.x - base_vec2.x
                            local dz = p.z - base_vec2.y
                            local d = math.sqrt(dx * dx + dz * dz)
                            if d <= max_dist_m and (not best_d or d < best_d) then
                                best_p, best_d = p, d
                            end
                        end
                    end
                end
            end
        end
    end
    return best_p
end

local function setup_player_alerts(records)
    if not records or #records == 0 then return end

    local bases = {}
    for _, rec in ipairs(records) do
        local airbase = AIRBASE:FindByName(rec.airbaseName)
        local own_side = COALITION_SIDE[rec.coalition]
        if airbase and own_side then
            local enemy_side = (own_side == coalition.side.BLUE)
                and coalition.side.RED or coalition.side.BLUE
            local scramble_nm = tonumber(rec.scrambleRadiusNm) or 60
            bases[#bases + 1] = {
                name = rec.airbaseName,
                vec2 = airbase:GetVec2(),
                own_side = own_side,
                enemy_side = enemy_side,
                cue_radius_m = (scramble_nm + PLAYER_SCRAMBLE_LEAD_NM) * NM,
            }
        end
    end
    if #bases == 0 then return end

    local last_alert = {}

    local function scan()
        local now = timer.getTime()
        for _, b in ipairs(bases) do
            local hostile = nearest_hostile(b.vec2, b.enemy_side, b.cue_radius_m)
            if hostile then
                local last = last_alert[b.name] or -1e9
                if now - last >= PLAYER_ALERT_REPEAT then
                    last_alert[b.name] = now
                    local brg, rng, angels = alert_bearing_range(b.vec2, hostile)
                    local msg = string.format(
                        "QRA SCRAMBLE -- %s: bandits %03d for %d nm, angels %d. Launch when ready.",
                        b.name, math.floor(brg + 0.5), math.floor(rng + 0.5), angels)
                    trigger.action.outTextForCoalition(b.own_side, msg, PLAYER_ALERT_DURATION)
                end
            end
        end
        mist.scheduleFunction(scan, {}, timer.getTime() + PLAYER_ALERT_INTERVAL)
    end

    -- Start after the dispatcher build window so the world is fully up.
    mist.scheduleFunction(scan, {}, timer.getTime() + BUILD_DELAY + 2)
end

if dcsRetribution.Intercept then
    local blue = dcsRetribution.Intercept.BLUE or {}
    local red = dcsRetribution.Intercept.RED or {}
    build_dispatcher("BLUE", blue)
    build_dispatcher("RED", red)

    setup_player_alerts(dcsRetribution.Intercept.PLAYER_ALERT or {})

    -- The registry is populated by the deferred build (BUILD_DELAY in); start the
    -- survivor poll well after that and after the dispatcher FSM auto-start.
    if #blue > 0 or #red > 0 then
        mist.scheduleFunction(refresh_survivors, {}, timer.getTime() + 15)
    end
end

-- Test hook: expose the pure filter helpers for tests/lua/test_intercept_filter.py.
-- The DCS plugin loader executes this chunk and discards its return value, so
-- this is inert in-mission.
return {
    pattern_escape = lua_pattern_escape,
}
