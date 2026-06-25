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
-- Each King lights a TACAN beacon (air-tracking, so it follows the orbit; the
-- CH-47F rescue helo has a TACAN receiver) the helo homes on, and carries a "LARS"
-- F10 button that reads MOOSE CSAR's live downed-pilot table and reports every
-- active survivor (position + bearing/range from the King + ADF freq). The ADF
-- radio beacon is deferred: MOOSE's RadioBeacon is fixed-point and would need a
-- refresh loop to track a moving King. King beacon/menu attach on group BIRTH so a
-- delayed or air-spawned (AI standing-alert) King is covered too.
--
-- Blue-side. enableForAI is driven by the auto_combat_sar setting (carried in the
-- data): OFF (default) makes MOOSE CSAR act ONLY on human-initiated events
-- (Moose.lua CSAR:_EventHandler early-returns when enableForAI==false and
-- IniPlayerName==nil) -- the "downed HUMAN pilots, player-flown" behaviour; ON lets
-- AI rescue helos be commandeered for a standing alert (AI ejections count too).
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

    -------------------------------------------------------------------------------
    -- C-130 "King": TACAN beacon + LARS survivor-locator menu
    -------------------------------------------------------------------------------

    -- LARS: read the live downed-pilot table and message the King group a list of
    -- all active survivors (nearest first) with position, bearing/range from the
    -- King, and ADF frequency. Coordinate text reuses MOOSE CSAR's own
    -- settings-aware formatter so it matches the player's chosen coord system.
    local function larsReport(csarEngine, kingGroup)
        local kingUnit = kingGroup:GetUnit(1)
        if not kingUnit or not kingUnit:IsAlive() then
            return
        end
        local kingCoord = kingUnit:GetCoordinate()
        local entries = {}
        for _, pilot in pairs(csarEngine.downedPilots or {}) do
            if pilot.group and pilot.alive then
                local woundedCoord = pilot.group:GetCoordinate()
                if woundedCoord then
                    local coordText = csarEngine:_GetPositionOfWounded(
                        pilot.group, kingUnit
                    )
                    local dist = kingCoord:Get2DDistance(woundedCoord)
                    local bearing = math.floor(kingCoord:HeadingTo(woundedCoord) + 0.5) % 360
                    local nm = UTILS.MetersToNM(dist)
                    local adf = ""
                    if pilot.frequency and pilot.frequency > 0 then
                        adf = string.format(", %.2f kHz ADF", pilot.frequency / 1000)
                    end
                    table.insert(entries, {
                        dist = dist,
                        text = string.format(
                            "%s: %s (brg %03d / %.0f nm%s)",
                            tostring(pilot.desc or "Survivor"),
                            coordText,
                            bearing,
                            nm,
                            adf
                        ),
                    })
                end
            end
        end
        table.sort(entries, function(a, b) return a.dist < b.dist end)
        local msg
        if #entries == 0 then
            msg = "LARS: no active survivor radios."
        else
            msg = "LARS - active survivors (nearest first):"
            for _, entry in pairs(entries) do
                msg = msg .. "\n" .. entry.text
            end
        end
        MESSAGE:New(msg, messageTime * 2):ToGroup(kingGroup)
    end

    local function addLarsMenu(csarEngine, kingGroup)
        local root = MENU_GROUP:New(kingGroup, "Combat SAR")
        MENU_GROUP_COMMAND:New(
            kingGroup, "LARS - Locate Survivors", root, larsReport, csarEngine, kingGroup
        )
    end

    local kings = data.kings or {}
    local kingByName = {}
    for _, king in pairs(kings) do
        if king.group then
            kingByName[king.group] = king
        end
    end

    -- Activate a King's TACAN beacon + LARS menu once (dedup so the start sweep and
    -- the birth handler can't double up the F10 menu).
    local activatedKings = {}
    local function activateKing(grp)
        local name = grp:GetName()
        if activatedKings[name] then
            return
        end
        local king = kingByName[name]
        if not king then
            return
        end
        activatedKings[name] = true
        if king.tacanChannel then
            local unit = grp:GetUnit(1)
            if unit then
                unit:GetBeacon():ActivateTACAN(
                    tonumber(king.tacanChannel),
                    king.tacanBand or "Y",
                    king.callsign or "KING",
                    true
                )
            end
        end
        addLarsMenu(csar, grp)
    end

    -- Kings already present at mission start...
    for name, _ in pairs(kingByName) do
        local grp = GROUP:FindByName(name)
        if grp and grp:IsAlive() then
            activateKing(grp)
        end
    end

    -- ...and any that spawn later (delayed / AI standing-alert Kings).
    local function onKingBirth(self, EventData)
        local grp = EventData and EventData.IniGroup
        if grp and kingByName[grp:GetName()] then
            activateKing(grp)
        end
    end
    local kingBirthHandler = EVENTHANDLER:New()
    kingBirthHandler:HandleEvent(EVENTS.Birth, onKingBirth)

    env.info(
        string.format(
            "DCSRetribution|Combat SAR plugin - CSAR started with %d rescue helo group(s), %d King(s), template '%s', enableForAI=%s",
            #rescueHelos,
            #kings,
            tostring(pilotTemplate),
            tostring(enableForAI)
        )
    )

else
    env.info("DCSRetribution|Combat SAR plugin - dcsRetribution.CombatSAR / CSAR not present; skipping")
end
