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

    -- specific options (defaults)
    local createRedIADS = true
    local createBlueIADS = true
    local useEmOnOff = true
    local debugRED = false
    local debugBLUE = false

    if dcsRetribution.plugins and dcsRetribution.plugins.mantisiads then
        local opts = dcsRetribution.plugins.mantisiads
        if opts.createRedIADS ~= nil then createRedIADS = opts.createRedIADS end
        if opts.createBlueIADS ~= nil then createBlueIADS = opts.createBlueIADS end
        if opts.useEmOnOff ~= nil then useEmOnOff = opts.useEmOnOff end
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
        if debug then
            mantis:Debug(true)
        end
        mantis:Start()
    end

    if createRedIADS then
        build("RED", coalition.side.RED, "red", debugRED)
    end
    if createBlueIADS then
        build("BLUE", coalition.side.BLUE, "blue", debugBLUE)
    end

end
