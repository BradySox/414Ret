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

if dcsRetribution and dcsRetribution.IADS and MANTIS then

    local engine = dcsRetribution.IADS.engine or "skynet"
    if engine ~= "mantis" then
        env.info(
            string.format(
                "DCSRetribution|MANTIS-IADS plugin - IADS engine is '%s', not 'mantis'; skipping",
                tostring(engine)
            )
        )
        return
    end

    -- specific options (defaults mirror MANTIS' own defaults)
    local createRedIADS = true
    local createBlueIADS = true
    local useEmOnOff = true
    local samRange = 95
    local detectInterval = 30
    local ewrGrouping = 5000
    local maxActiveShort = 2
    local maxActiveMid = 2
    local maxActiveLong = 1
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

    -- Collect the exact DCS group names for a coalition's SAM and EWR sets.
    -- MANTIS:New accepts a table of name prefixes and matches any group whose
    -- name starts with an entry; passing exact generated group names makes each
    -- group match itself, so no group renaming is required.
    -- (Known v1 caveat: if one group name is a strict prefix of another, the
    --  shorter would also match the longer -- watch for this in the in-game pass.)
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

        -- pydcs registers comms/power/command-center statics with a " object" suffix.
        -- A node is only WATCHABLE if it resolves to a real, existing StaticObject. On some
        -- maps an IADS connection node is a trigger ZONE / map feature (e.g. a VOR/DME or
        -- radio beacon) rather than a placed static -- such a node can never be "destroyed",
        -- so watching it would make its "not a static" lookup read as DEAD and falsely
        -- decapitate the entire network the instant the watcher first polls. So we only watch
        -- nodes that are actual statics at setup; zone/non-static nodes are skipped.
        local function static_present(unit_name)
            local so = StaticObject.getByName(unit_name .. " object")
            return so ~= nil and so:isExist()
        end
        local function static_dead(unit_name)
            return not static_present(unit_name)
        end

        local skipped = 0
        local function add_deps(map, conn_list, sam_group)
            if conn_list then
                for _, n in pairs(conn_list) do
                    if static_present(n) then
                        map[n] = map[n] or {}
                        table.insert(map[n], sam_group)
                    else
                        skipped = skipped + 1
                    end
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
                if static_present(cc.dcsGroupName) then
                    table.insert(cc_names, cc.dcsGroupName)
                else
                    skipped = skipped + 1
                end
            end
        end

        -- Basic-mode campaigns (and maps whose C2 nodes are all zones) have nothing to watch.
        if next(comms_deps) == nil and next(power_deps) == nil and #cc_names == 0 then
            if skipped > 0 then
                env.info(string.format(
                    "DCSRetribution|MANTIS C2 - %s: no destructible C2 statics (%d zone/non-static node(s)); watcher idle",
                    coalition_prefix, skipped))
            end
            return
        end
        if skipped > 0 then
            env.info(string.format(
                "DCSRetribution|MANTIS C2 - %s: skipped %d zone/non-static C2 node(s)",
                coalition_prefix, skipped))
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
                if not handled[key] and static_dead(comms_name) then
                    handled[key] = true
                    for _, s in pairs(sams) do set_autonomous(s) end
                    env.info(string.format(
                        "DCSRetribution|MANTIS C2 - comms '%s' lost; degrading %d SAM(s)",
                        comms_name, #sams))
                end
            end
            for power_name, sams in pairs(power_deps) do
                local key = "power:" .. power_name
                if not handled[key] and static_dead(power_name) then
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
                    if not static_dead(cc) then all_dead = false break end
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
        local mantis = MANTIS:New(
            name, sam_names, ewr_names, nil, coalition_str, true, nil, useEmOnOff, nil, nil
        )

        -- Phase-4 tuning (applied before Start so detection/engagement pick them up).
        mantis:SetSAMRange(samRange)
        mantis:SetDetectInterval(detectInterval)
        mantis:SetEWRGrouping(ewrGrouping)
        mantis:SetMaxActiveSAMs(maxActiveShort, maxActiveMid, maxActiveLong, nil, maxActivePoint)
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

        -- Phase-5: arm the comms/power/command-center C2 degradation watcher.
        if enableC2Degradation then
            setup_c2(coalition_prefix, coalition_iads, sam_names, commsLossGoesDark)
        end
    end

    if createRedIADS then
        build("RED", coalition.side.RED, "red", debugRED)
    end
    if createBlueIADS then
        build("BLUE", coalition.side.BLUE, "blue", debugBLUE)
    end

end
