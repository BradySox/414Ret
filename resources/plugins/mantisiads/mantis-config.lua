-------------------------------------------------------------------------------------------------------------------------------------------------------------
-- MANTIS IADS configuration bridge for DCS Retribution
--
-- Builds a MOOSE MANTIS air-defense network per coalition from the
-- dcsRetribution.IADS data table emitted by the mission generator. MANTIS ships
-- inside the bundled MOOSE (base plugin's Moose.lua), so this plugin only
-- supplies configuration -- there is no separate script to load.
--
-- This bridge only acts when the selected IADS engine is "mantis"
-- (dcsRetribution.IADS.engine, set from Settings.iads_engine). Otherwise it
-- no-ops so the Skynet bridge (skynetiads-config.lua) runs instead.
--
-- Phase 1 scope: core networking (SAM/EWR detection coordination + emissions
-- control). NOT yet implemented: shoot-and-scoot relocation, command-center /
-- comms / power C2 degradation, explicit point-defense pairing, per-unit tuning.
-- see docs/dev/design/414th-mantis-migration-notes.md
-------------------------------------------------------------------------------------------------------------------------------------------------------------

env.info("DCSRetribution|MANTIS-IADS plugin - configuration")

-- MANTIS is the sole IADS engine (Skynet removed); this bridge always runs when
-- there is IADS data and the bundled MOOSE MANTIS class is present.
if dcsRetribution and dcsRetribution.IADS and MANTIS then

    -- specific options (defaults mirror MANTIS' own defaults)
    local createRedIADS = true
    local createBlueIADS = true
    -- Emissions control default OFF. With it ON, MANTIS forces every SAM radar dark
    -- (EnableEmission(false)) until the network cues it, so the SAMs contribute
    -- nothing to detection (MANTIS' IntelTwo) and the whole network depends on the
    -- handful of dedicated EWRs -- which routinely miss a low/forward target, leaving
    -- the detection set empty (CheckLoop 0) and NO SAM ever engaging. OFF lets every
    -- SAM (and SAM-as-EWR) search on its own radar, feed detection, and engage what's
    -- in range -- a reliable, RWR-visible IADS. Flip it back on for a stealthy
    -- EWR-cued network once detection coverage is proven.
    local useEmOnOff = false
    local samRange = 95
    -- 15s (was 30) so the IADS cues/hands off briskly -- a 30s poll let targets
    -- slip through a SAM's (now range-correct) ring before it reacted.
    local detectInterval = 15
    local ewrGrouping = 5000
    -- Max simultaneously-active SAMs per band; 0 = unlimited (every in-range SAM
    -- of that band engages). Long/medium default uncapped so the strategic IADS is
    -- a real SEAD fight you can't fly through; short/point keep a rolling cap so the
    -- SHORAD layer doesn't all light up at once on a low ingress.
    local maxActiveShort = 2
    local maxActiveMid = 0
    local maxActiveLong = 0
    local maxActivePoint = 6
    local autoRelocateEwr = false
    local enableC2Degradation = true
    local commsLossGoesDark = false
    local c2PollInterval = 20
    local debugRED = false
    local debugBLUE = false

    if dcsRetribution.plugins and dcsRetribution.plugins.mantisiads then
        local opts = dcsRetribution.plugins.mantisiads
        if opts.createRedIADS ~= nil then createRedIADS = opts.createRedIADS end
        if opts.createBlueIADS ~= nil then createBlueIADS = opts.createBlueIADS end
        if opts.useEmOnOff ~= nil then useEmOnOff = opts.useEmOnOff end
        if opts.samRange ~= nil then samRange = opts.samRange end
        if opts.detectInterval ~= nil then detectInterval = opts.detectInterval end
        if opts.ewrGrouping ~= nil then ewrGrouping = opts.ewrGrouping end
        if opts.maxActiveShort ~= nil then maxActiveShort = opts.maxActiveShort end
        if opts.maxActiveMid ~= nil then maxActiveMid = opts.maxActiveMid end
        if opts.maxActiveLong ~= nil then maxActiveLong = opts.maxActiveLong end
        if opts.maxActivePoint ~= nil then maxActivePoint = opts.maxActivePoint end
        if opts.autoRelocateEwr ~= nil then autoRelocateEwr = opts.autoRelocateEwr end
        if opts.enableC2Degradation ~= nil then enableC2Degradation = opts.enableC2Degradation end
        if opts.commsLossGoesDark ~= nil then commsLossGoesDark = opts.commsLossGoesDark end
        if opts.c2PollInterval ~= nil then c2PollInterval = opts.c2PollInterval end
        if opts.debugRED ~= nil then debugRED = opts.debugRED end
        if opts.debugBLUE ~= nil then debugBLUE = opts.debugBLUE end
    end

    -- A prefix that no generated group name starts with, used so that an empty
    -- SAM or EWR set never collapses MANTIS' FilterPrefixes into a match-all.
    local NO_MATCH = "__RetributionMantisNoMatch__"

    -- MANTIS' SET_GROUP:FilterPrefixes matches each "prefix" with string.find
    -- WITHOUT the plain flag (Moose.lua ~13321) -- i.e. it treats the prefix as a
    -- Lua PATTERN, escaping only "-". Every Retribution group name carries
    -- pattern-magic characters (e.g. "0145 | GRYPHON (SAM)" has "(" and ")"), so an
    -- unescaped name never matches its own group: MANTIS ends up controlling ZERO
    -- SAMs and they run vanilla DCS AI with radars always on (the "SAM track radar
    -- emitting in search mode on ingress / no EMCON" bug). Escape the magic chars
    -- (except "-", which MANTIS' own gsub already handles -- escaping it here would
    -- double-escape it) so each prefix matches its literal group name.
    local function escape_prefix(name)
        -- Capture the magic char so "%1" is valid in the replacement (a no-capture
        -- pattern with "%1" raises "invalid capture index" at runtime in Lua 5.1).
        return (name:gsub("([%(%)%.%%%+%*%?%[%]%^%$])", "%%%1"))
    end
    local function escape_prefixes(names)
        local out = {}
        for i = 1, #names do
            out[i] = escape_prefix(names[i])
        end
        return out
    end

    -- Collect the exact DCS group names for a coalition's SAM and EWR sets.
    -- MANTIS:New accepts a table of name prefixes and matches any group whose name
    -- CONTAINS an entry (Lua-pattern string.find). We escape each name with
    -- escape_prefix before handing it to MANTIS (see above), so a generated name
    -- matches its own group literally and no group renaming is required.
    -- (Known caveat: if one group name is a substring of another, the shorter would
    --  also match the longer -- watch for this in the in-game pass.)
    local function collect(coalition_iads)
        local sam_names = {}
        local ewr_names = {}
        if coalition_iads.Sam then
            for _, unit in pairs(coalition_iads.Sam) do
                table.insert(sam_names, unit.dcsGroupName)
            end
        end
        if coalition_iads.SamAsEwr then
            for _, unit in pairs(coalition_iads.SamAsEwr) do
                -- A SAM that also serves as an EWR: include in both sets.
                table.insert(sam_names, unit.dcsGroupName)
                table.insert(ewr_names, unit.dcsGroupName)
            end
        end
        if coalition_iads.Ewr then
            for _, unit in pairs(coalition_iads.Ewr) do
                table.insert(ewr_names, unit.dcsGroupName)
            end
        end
        return sam_names, ewr_names
    end

    -- Fold any AWACS for this coalition into the EWR set (by group name).
    local function add_awacs(ewr_names, coalition_side)
        if dcsRetribution.AWACs then
            for _, data in pairs(dcsRetribution.AWACs) do
                local group = Group.getByName(data.dcsGroupName)
                if group and group:getCoalition() == coalition_side then
                    table.insert(ewr_names, data.dcsGroupName)
                end
            end
        end
    end

    -- Phase-5 C2 layer: re-implement Skynet's comms / power / command-center
    -- degradation on top of MANTIS (which has no connection graph of its own).
    -- The per-SAM ConnectionNode/PowerSource arrays and the coalition's
    -- CommandCenter list are already in the IADS data table; we watch those
    -- static objects and degrade the dependent SAMs when they die:
    --   * power lost  -> SAM offline (SetAIOff)
    --   * comms lost  -> SAM autonomous (alarm state RED) or dark, per policy
    --   * all command centers lost -> whole coalition network decapitated
    -- Only advanced_iads campaigns populate these; basic-mode is a no-op.
    --
    -- KNOWN UNTESTED RISK (in-game pass G6): MANTIS owns the SAMs' emissions, so
    -- it may re-enable a SAM we disabled on its next detection cycle. If the G6
    -- pass shows degradation not "sticking", the fix is to also drop the SAM from
    -- MANTIS' managed set (no clean public API yet) rather than only toggling the
    -- group. Gated behind iads_engine=MANTIS, so this never affects Skynet missions.
    local function setup_c2(coalition_prefix, coalition_iads, sam_groups, policy_dark)
        local comms_deps = {} -- comms unit name -> { dependent SAM group names }
        local power_deps = {} -- power unit name -> { dependent SAM group names }
        local cc_names = {}   -- command-center static names

        local function add_deps(map, conn_list, sam_group)
            if conn_list then
                for _, n in pairs(conn_list) do
                    map[n] = map[n] or {}
                    table.insert(map[n], sam_group)
                end
            end
        end

        local function scan(list)
            if not list then return end
            for _, sam in pairs(list) do
                add_deps(comms_deps, sam.ConnectionNode, sam.dcsGroupName)
                add_deps(power_deps, sam.PowerSource, sam.dcsGroupName)
            end
        end
        scan(coalition_iads.Sam)
        scan(coalition_iads.SamAsEwr)

        if coalition_iads.CommandCenter then
            for _, cc in pairs(coalition_iads.CommandCenter) do
                table.insert(cc_names, cc.dcsGroupName)
            end
        end

        -- Basic-mode campaigns have no C2 graph: nothing to watch.
        if next(comms_deps) == nil and next(power_deps) == nil and #cc_names == 0 then
            return
        end

        -- Death detection. C2 nodes are NOT all placed statics: many (comms masts, power
        -- hubs, VOR/DME, beacons, ...) are destructible *scenery* / map objects, which
        -- StaticObject.getByName never finds. The original "(so == nil) -> dead" test therefore
        -- read every scenery node as destroyed on the first poll and falsely decapitated the
        -- whole network at mission start. So a node counts as dead only when we have POSITIVE
        -- evidence it died:
        --   (a) a placed static of that name exists but no longer :isExist(), or
        --   (b) its name was recorded in the global `dead_events` table (the same S_EVENT_DEAD /
        --       scenery-trigger record the rest of Retribution uses for BDA). dead_events stores
        --       the bare object name for scenery, so we match the node name with the "id | "
        --       prefix stripped as well as verbatim.
        local function bare_name(node_name)
            return node_name:match("|%s*(.+)$") or node_name
        end
        local function node_dead(node_name)
            local so = StaticObject.getByName(node_name .. " object")
            if so ~= nil and not so:isExist() then
                return true -- a real static that existed and is now destroyed
            end
            if type(dead_events) == "table" then
                local bare = bare_name(node_name)
                for _, dn in pairs(dead_events) do
                    if dn == node_name or dn == bare then
                        return true -- recorded dead (scenery or unit) via dead_events
                    end
                end
            end
            return false
        end

        local function set_offline(sam_group)
            local grp = GROUP:FindByName(sam_group)
            if grp and grp:IsAlive() then grp:SetAIOff() end
        end
        local function set_autonomous(sam_group)
            local grp = GROUP:FindByName(sam_group)
            if grp and grp:IsAlive() then
                if policy_dark then grp:SetAIOff() else grp:OptionAlarmStateRed() end
            end
        end

        local handled = {} -- fire each degradation event only once

        local function poll()
            for comms_name, sams in pairs(comms_deps) do
                local key = "comms:" .. comms_name
                if not handled[key] and node_dead(comms_name) then
                    handled[key] = true
                    for _, s in pairs(sams) do set_autonomous(s) end
                    env.info(string.format(
                        "DCSRetribution|MANTIS C2 - comms '%s' lost; degrading %d SAM(s)",
                        comms_name, #sams))
                end
            end
            for power_name, sams in pairs(power_deps) do
                local key = "power:" .. power_name
                if not handled[key] and node_dead(power_name) then
                    handled[key] = true
                    for _, s in pairs(sams) do set_offline(s) end
                    env.info(string.format(
                        "DCSRetribution|MANTIS C2 - power '%s' lost; %d SAM(s) offline",
                        power_name, #sams))
                end
            end
            if #cc_names > 0 and not handled["cc:all"] then
                local all_dead = true
                for _, cc in pairs(cc_names) do
                    if not node_dead(cc) then all_dead = false break end
                end
                if all_dead then
                    handled["cc:all"] = true
                    for _, s in pairs(sam_groups) do set_autonomous(s) end
                    env.info("DCSRetribution|MANTIS C2 - all command centers lost for "
                        .. coalition_prefix .. "; network decapitated")
                end
            end
            return timer.getTime() + c2PollInterval
        end

        timer.scheduleFunction(poll, nil, timer.getTime() + c2PollInterval)
        env.info(string.format(
            "DCSRetribution|MANTIS C2 - watcher armed for %s (poll %ds)",
            coalition_prefix, c2PollInterval))
    end

    local function build(coalition_prefix, coalition_side, coalition_str, debug)
        local coalition_iads = dcsRetribution.IADS[coalition_prefix]
        if not coalition_iads then return end

        local sam_names, ewr_names = collect(coalition_iads)
        add_awacs(ewr_names, coalition_side)

        if #sam_names == 0 and #ewr_names == 0 then
            env.info(
                string.format(
                    "DCSRetribution|MANTIS-IADS plugin - no IADS groups for %s; skipping",
                    coalition_prefix
                )
            )
            return
        end

        -- Guard against an empty set becoming a match-all prefix filter.
        if #sam_names == 0 then sam_names = { NO_MATCH } end
        if #ewr_names == 0 then ewr_names = { NO_MATCH } end

        local name = "Retribution-" .. coalition_prefix .. "-IADS"
        env.info(
            string.format(
                "DCSRetribution|MANTIS-IADS plugin - building %s (%d SAM, %d EWR group names)",
                name, #sam_names, #ewr_names
            )
        )

        -- MANTIS:New(name, samprefix, ewrprefix, hq, coalition, dynamic, awacs, EmOnOff, Padding, Zones)
        -- Pass FilterPrefixes-safe (Lua-pattern-escaped) names so MANTIS actually
        -- resolves our parenthesized "... (SAM)" group names (see escape_prefix). The
        -- raw sam_names stay for the exact-match C2 lookups (GROUP:FindByName) below.
        local mantis = MANTIS:New(
            name, escape_prefixes(sam_names), escape_prefixes(ewr_names), nil,
            coalition_str, true, nil, useEmOnOff, nil, nil
        )

        -- Phase-4 tuning (applied before Start so detection/engagement pick them up).
        mantis:SetSAMRange(samRange)
        mantis:SetDetectInterval(detectInterval)
        mantis:SetEWRGrouping(ewrGrouping)
        -- 0 means "no cap" for us; MANTIS wants a number, so pass one larger than
        -- any campaign's SAM count to let every in-range SAM of that band engage.
        local function uncap(n)
            if n == nil or n == 0 then return 9999 end
            return n
        end
        mantis:SetMaxActiveSAMs(
            uncap(maxActiveShort),
            uncap(maxActiveMid),
            uncap(maxActiveLong),
            nil,
            uncap(maxActivePoint)
        )
        if autoRelocateEwr then
            -- EWR-only relocation; HQ relocation needs a command center (phase 5).
            mantis:SetAutoRelocate(false, true)
        end
        -- NB: reactive SAM shoot-and-scoot is automatic via MANTIS' integrated SEAD
        -- evasion (drivable SAMs go dark and relocate when an ARM is inbound).
        -- Proactive SHORAD scoot between zones (AddScootZones) needs Python-generated
        -- zones and is deferred. Advanced mode (SetAdvancedMode) is deferred to the
        -- C2 phase: it requires an HQ/command center and otherwise nags every player.

        if debug then
            mantis:Debug(true)
        end
        mantis:Start()

        -- Diagnostic (the EMCON ground truth): how many real groups MANTIS resolved
        -- from our names. If SAM resolves to 0 (or fewer than we passed), the
        -- FilterPrefixes match is failing and the SAMs are running vanilla DCS AI
        -- (radars always on, no EMCON). With the escape_prefix fix it should match
        -- the SAM/EWR counts we passed. Watch this line on the next in-game pass.
        local resolved_sams = (mantis.SAM_Group and mantis.SAM_Group:CountAlive()) or 0
        local resolved_ewrs = (mantis.EWR_Group and mantis.EWR_Group:CountAlive()) or 0
        env.info(
            string.format(
                "DCSRetribution|MANTIS-IADS plugin - %s resolved %d/%d SAM + %d EWR live "
                    .. "group(s) (0 SAM = name match failed -> SAMs run vanilla, no EMCON)",
                name, resolved_sams, #sam_names, resolved_ewrs
            )
        )

        -- Phase-5: arm the comms/power/command-center C2 degradation watcher.
        if enableC2Degradation then
            setup_c2(coalition_prefix, coalition_iads, sam_names, commsLossGoesDark)
        end
    end

    -- -------------------------------------------------------------------------
    -- SAM range/type override (414th SEAD fix).
    --
    -- MANTIS classifies a SAM's range/band by scanning the group's unit type
    -- names against its built-in SamData table, breaking on the FIRST match
    -- (MANTIS:_GetSAMRange / _GetSAMDataFromUnits). Retribution SAM sites carry
    -- MULTIPLE radars (search + track + launchers + a co-located "Dog Ear" EWR in
    -- many sites), so that scan picks the wrong radar and mis-types medium/long
    -- SAMs (SA-6 / SA-10 / SA-11) as POINT. A POINT SAM drops into MANTIS' autono-
    -- mous-SHORAD set instead of the network, never gets EMCON-coordinated, and
    -- only engages at point-blank range -- so nothing emits at standoff and there
    -- is nothing to SEAD (the "SAMs never engaged / stayed GREEN" report).
    --
    -- Fix: classify each SAM from Retribution's OWN threat range, which the planner
    -- already computes and emits per group as dcsRetribution.{Red,Blue}AA[].range
    -- (the MEZ, in metres). We override _GetSAMRange to return that range + the
    -- band it implies, bypassing the broken unit scan. Pure Lua in our bridge, no
    -- MOOSE-source edit; any group we can't resolve falls back to MANTIS' native
    -- logic, so this can only improve classification, never crash it.
    local retribution_sam_range = {}  -- codename -> threat range (metres)
    local function index_aa(aa)
        if type(aa) ~= "table" then return end
        for _, item in pairs(aa) do
            if item.name and item.range then
                -- A single SAM site (codename) often has SEVERAL groups -- the main
                -- SAM plus a co-located point-defense (SA-9/SA-13/SA-8). Each emits a
                -- range under the same codename, so keep the LONGEST: the site bands
                -- by its real reach. Keeping the last-seen instead under-bands an
                -- SA-5/SA-6/SA-2 site to POINT when its short escort is emitted last.
                local r = tonumber(item.range)
                local current = retribution_sam_range[item.name]
                if r and (current == nil or r > current) then
                    retribution_sam_range[item.name] = r
                end
            end
        end
    end
    index_aa(dcsRetribution.RedAA)
    index_aa(dcsRetribution.BlueAA)
    local _rangecount = 0
    for _ in pairs(retribution_sam_range) do _rangecount = _rangecount + 1 end
    env.info(string.format(
        "DCSRetribution|MANTIS-IADS plugin - SAM range override active (%d AD group "
            .. "range(s) from Retribution; SAMs banded by true MEZ, not unit scan)",
        _rangecount))

    -- Range thresholds (metres) -> MANTIS band, mirroring MANTIS' own SamData bands
    -- (LONG = SA-10/SA-5/Patriot, MEDIUM = SA-2/6/11, SHORT = SA-3/8/Rapier,
    -- POINT = SA-9/15/Gepard/AAA). Engagement ceiling per band feeds MANTIS' height
    -- pre-filter so a long SAM still services high targets and a point SAM does not.
    local BAND_LONG_M = 50000
    local BAND_MEDIUM_M = 18000
    local BAND_SHORT_M = 8000
    local CEILING_M = {
        [MANTIS.SamType.LONG] = 25000,
        [MANTIS.SamType.MEDIUM] = 15000,
        [MANTIS.SamType.SHORT] = 8000,
        [MANTIS.SamType.POINT] = 4000,
    }

    local function retribution_range_for(grpname)
        for codename, rng in pairs(retribution_sam_range) do
            if codename ~= "" and string.find(grpname, codename, 1, true) then
                return rng
            end
        end
        return nil
    end

    local _orig_GetSAMRange = MANTIS._GetSAMRange
    function MANTIS:_GetSAMRange(grpname)
        local rng = retribution_range_for(grpname)
        if rng and rng > 0 then
            local band
            if rng >= BAND_LONG_M then band = MANTIS.SamType.LONG
            elseif rng >= BAND_MEDIUM_M then band = MANTIS.SamType.MEDIUM
            elseif rng >= BAND_SHORT_M then band = MANTIS.SamType.SHORT
            else band = MANTIS.SamType.POINT end
            -- Match MANTIS' own detection-radius padding (radiusscale) so a SAM
            -- still wakes a little before a target reaches lethal range.
            local scale = MANTIS.radiusscale[band] or 1
            return rng * scale, CEILING_M[band], band, 0
        end
        return _orig_GetSAMRange(self, grpname)
    end

    if createRedIADS then
        build("RED", coalition.side.RED, "red", debugRED)
    end
    if createBlueIADS then
        build("BLUE", coalition.side.BLUE, "blue", debugBLUE)
    end

end
