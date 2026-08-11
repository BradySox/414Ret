-- Intercept (QRA) — drives AI_A2A_DISPATCHER per coalition from
-- dcsRetribution.Intercept. Rationale, the flown-test history and the tuning
-- record are in docs/dev/414th-features.md §1. The load-bearing parts:
--
--  * Never restore the per-base backstop EWR. DCS has no non-colliding ground
--    unit, so the mast blocked AI taxi routing (flown Red Tide 2026-08-06;
--    upstream #782 removed it for the same reason). Detection is the IADS
--    network alone; a side with no EWR losing GCI is by design.
--  * Never call SetSquadronVisible. It forces Moose's ParkDefender branch
--    (hardcoded Cold takeoff) and clamps the reserve to parking spots. Every
--    ground spawn fails on a saturated ramp -- in-air is the only method left.
--  * The BASE.CreateEventTakeoff monkeypatch below works around MOOSE #2595.
--    Delete it once that lands in the vendored Moose.lua.
--  * SetSquadronGci speeds are km/h, not m/s.
--  * SetBorderZone bounds WHERE a side may fight; GciRadius bounds how far it
--    launches to get there. Open DisengageRadius with GciRadius or a distant
--    base launches and turns straight around.

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
local BUILD_DELAY = 5  -- seconds; let the mission's groups register before SET_GROUP

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

-- ---------------------------------------------------------------------------
-- Task-type reaction filter (upstream PR #782)
-- QRA only scrambles against air-to-ground raids. The enemy flight's Retribution
-- task type is embedded in its DCS group name by namegen.next_aircraft_name as
-- "{target} {flight_type}|{country}|{n}|{variant}|" (game/naming.py). We react
-- only when a detected cluster contains a group whose type is in QRA_REACT_TASKS;
-- CAP/sweep/escort/intercept/SEAD/CAS/DEAD/Air Assault/support are ignored.
-- Non-ATO enemy air (not named by namegen) has no matching suffix and is never
-- reacted to.
-- ---------------------------------------------------------------------------
local QRA_REACT_TASKS = {
    ["Strike"] = true,
    ["BAI"] = true,
    ["OCA/Runway"] = true,
    ["OCA/Aircraft"] = true,
    ["Anti-ship"] = true,
    ["Armed Recon"] = true,
}

local function ends_with(str, suffix)
    return str:sub(-#suffix) == suffix
end

-- True if the group name's task-type suffix is a react-type. We require the
-- namegen "{target} {flight_type}|..." format and match the first "|"-field:
-- a name with no "|" is not a Retribution ATO flight, so we cannot classify it
-- and never react (this enforces the documented non-ATO limitation and stops a
-- mission-editor/Combined-Arms group coincidentally named e.g. "Eagle Strike"
-- from false-matching). Within the field we suffix-match " " .. task so
-- multi-word target names (e.g. "Al Dhafra Strike") and any multi-word react
-- type both work; the leading space keeps a target name that merely ends in the
-- task word (no separator) from matching.
local function qra_group_reacts(group_name)
    if type(group_name) ~= "string" then return false end
    local field = group_name:match("^([^|]+)|")  -- "{target} {flight_type}" up to the first "|"
    if not field then return false end
    for task, _ in pairs(QRA_REACT_TASKS) do
        if ends_with(field, " " .. task) then
            return true
        end
    end
    return false
end

-- True if any unit in the detected cluster belongs to a react-type group. A
-- cluster reacts as soon as one react-type group is present (escorted strikes
-- still trigger).
local function qra_cluster_has_react(detected_item)
    local set = detected_item and detected_item.Set
    if not set then return false end
    local found = false
    set:ForEachUnit(function(unit)
        if found then return end  -- short-circuit; ForEachUnit has no early break
        local group = unit:GetGroup()
        if group and qra_group_reacts(group:GetName()) then
            found = true
        end
    end)
    return found
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

    -- Assemble the dispatcher once the mission's groups have registered.
    mist.scheduleFunction(function()
        local detection_prefixes = ewr_group_names(coalition_name)

        if #detection_prefixes == 0 then
            env.info("DCSRetribution|Intercept: no detection sources for "
                     ..coalition_name.."; QRA will not scramble.")
            return
        end

        -- Moose SET_GROUP:FilterPrefixes matches names with Lua-pattern semantics
        -- (string.find, only "-" pre-escaped). Retribution IADS group names contain
        -- "(" / ")" (e.g. "0041 | LION (EWR)", "0114 | LORIKEET (S-300)"), which
        -- would be read as pattern captures and never match, leaving the detection
        -- set empty (no QRA scramble ever). Escape the magic chars so each prefix
        -- matches its literal group name.
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
        -- Only scramble against air-to-ground raids (upstream PR #782). Wrap this
        -- instance's per-cluster evaluation so a detected cluster with no
        -- react-type group is skipped; otherwise delegate to Moose's original.
        -- Per-instance (not class-level) so it applies to this coalition's
        -- dispatcher only. EvaluateGCI returns (DefendersMissing, Friendlies);
        -- nil,nil means "no scramble". EvaluateENGAGE returns Friendlies or nil.
        local orig_evaluate_gci = dispatcher.EvaluateGCI
        function dispatcher:EvaluateGCI(detected_item)
            if not qra_cluster_has_react(detected_item) then
                return nil, nil
            end
            return orig_evaluate_gci(self, detected_item)
        end
        local orig_evaluate_engage = dispatcher.EvaluateENGAGE
        function dispatcher:EvaluateENGAGE(detected_item)
            if not qra_cluster_has_react(detected_item) then
                return nil
            end
            return orig_evaluate_engage(self, detected_item)
        end
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
-- Deliberately task-blind (no QRA_REACT_TASKS filter): the cue informs, the
-- human judges whether a closing sweep is worth scrambling for.
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
    group_reacts = qra_group_reacts,
    cluster_has_react = qra_cluster_has_react,
}
