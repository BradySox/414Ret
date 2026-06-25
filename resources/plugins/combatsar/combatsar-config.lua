-------------------------------------------------------------------------------------------------------------------------------------------------------------
-- Combat SAR configuration bridge for DCS Retribution
--
-- Stands up a MOOSE CSAR engine for the BLUE coalition from the
-- dcsRetribution.CombatSAR data table emitted by the mission generator. CSAR
-- ships inside the bundled MOOSE (base plugin's Moose.lua), so this plugin only
-- supplies configuration -- there is no separate script to load.
--
-- When a HUMAN pilot ejects, MOOSE CSAR spawns a downed pilot (cloned from the
-- late-activation `pilotTemplate` group the generator dropped into the .miz) with
-- a radio beacon. The CH-47 flights tasked Combat SAR (rescueHelos) can then fly
-- in and recover them. C-130 Combat SAR flights (kings) only fly the overhead
-- "King" orbit -- they are NOT in the rescue set and never land at a crash site.
--
-- v1 scope (blue, human-pilot, player-flown): enableForAI is left false, which
-- makes MOOSE CSAR act ONLY on human-initiated events (Moose.lua CSAR:_EventHandler
-- early-returns when enableForAI==false and IniPlayerName==nil) -- exactly the
-- "downed HUMAN pilots" behaviour. AI standing-alert rescue is a later phase.
--
-- Inert unless dcsRetribution.CombatSAR exists (the generator emits it only when
-- at least one blue Combat SAR flight is present). Independent of the SOF-recovery
-- CSAR (FlightType.CSAR / the SCAR loop): separate flight type, separate plugin.
-- see docs/dev/design/414th-combat-sar-spec.md
-------------------------------------------------------------------------------------------------------------------------------------------------------------

env.info("DCSRetribution|Combat SAR plugin - configuration")

if dcsRetribution and dcsRetribution.CombatSAR and CSAR then

    local data = dcsRetribution.CombatSAR
    local rescueHelos = data.rescueHelos or {}
    local pilotTemplate = data.pilotTemplate
    -- enableForAI is emitted as a string ("true"/"false"). On = AI standing alert
    -- (Settings.auto_combat_sar): MOOSE CSAR may commandeer an orbiting AI CH-47 to
    -- rescue, and AI ejections become rescuable too. Off = human-initiated only.
    local enableForAI = (data.enableForAI == "true") or (data.enableForAI == true)

    if not pilotTemplate or #rescueHelos == 0 then
        env.info("DCSRetribution|Combat SAR plugin - no rescue helos / template; skipping")
        return
    end

    -- specific options (defaults mirror MOOSE CSAR's own defaults)
    local autosmoke = false
    local loadDistance = 75
    local rescueHoverHeight = 20
    local messageTime = 15

    if dcsRetribution.plugins and dcsRetribution.plugins.combatsar then
        local opts = dcsRetribution.plugins.combatsar
        if opts.autosmoke ~= nil then autosmoke = opts.autosmoke end
        if opts.loadDistance ~= nil then loadDistance = opts.loadDistance end
        if opts.rescueHoverHeight ~= nil then rescueHoverHeight = opts.rescueHoverHeight end
        if opts.messageTime ~= nil then messageTime = opts.messageTime end
    end

    -- A prefix that no generated group name starts with, so an empty rescue set
    -- never collapses SET_GROUP:FilterPrefixes into a match-all (mirrors the
    -- MANTIS bridge). We already early-return on an empty set above, but keep the
    -- sentinel as a belt-and-braces guard.
    local NO_MATCH = "__RetributionCombatSARNoMatch__"
    local prefixes = {}
    for _, name in pairs(rescueHelos) do
        table.insert(prefixes, name)
    end
    if #prefixes == 0 then
        table.insert(prefixes, NO_MATCH)
    end

    -- Bind the rescue set to the EXACT generated CH-47 group names (each name
    -- matches itself as a prefix -- the same trick the MANTIS bridge uses, so no
    -- group renaming is required). FilterCategoryHelicopter() keeps the set to
    -- rotary wing even if a name ever collides with a non-helo group.
    local rescueSet = SET_GROUP:New()
        :FilterCoalitions("blue")
        :FilterPrefixes(prefixes)
        :FilterCategoryHelicopter()
        :FilterStart()

    -- Build the CSAR engine. Template = the downed-pilot group MOOSE clones at the
    -- crash site; Alias "CSAR" drives the menu/label.
    local csar = CSAR:New("blue", pilotTemplate, "CSAR")
    csar:SetOwnSetPilotGroups(rescueSet)

    -- Ejection-only, blue-side behaviour. enableForAI gates AI participation:
    -- false (default) = human-initiated only; true = AI standing-alert rescue.
    csar.enableForAI = enableForAI
    csar.csarOncrash = false          -- ejection rescues only, not every crash
    csar.allowDownedPilotCAcontrol = false
    csar.autosmoke = autosmoke
    csar.loadDistance = loadDistance
    csar.rescuehoverheight = rescueHoverHeight
    csar.messageTime = messageTime
    csar.allowFARPRescue = true       -- delivering to a friendly FARP/airfield counts

    csar:Start()

    env.info(
        string.format(
            "DCSRetribution|Combat SAR plugin - CSAR started with %d rescue helo group(s), template '%s', enableForAI=%s",
            #rescueHelos,
            tostring(pilotTemplate),
            tostring(enableForAI)
        )
    )

else
    env.info("DCSRetribution|Combat SAR plugin - dcsRetribution.CombatSAR / CSAR not present; skipping")
end
