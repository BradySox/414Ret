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
-- Each King lights a TACAN beacon (air-tracking, so it follows the orbit; every
-- rescue helo we use has a TACAN receiver) the helo homes on, and carries a "LARS"
-- F10 button that reads MOOSE CSAR's live downed-pilot table and reports every
-- active survivor (position + bearing/range from the King) for the King crew to
-- relay. TACAN is the single homing solution: an ADF radio beacon was dropped
-- (MOOSE's RadioBeacon is fixed-point and the King is a mover, so it would need a
-- position-refresh loop for no gain over the TACAN). King beacon/menu attach on
-- group BIRTH so a delayed or air-spawned (AI standing-alert) King is covered too.
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

    -- Ejection-only, blue-side, PLAYER-flown rescues. We force CSAR's own AI
    -- participation OFF: MOOSE CSAR's enableForAI merely *tracks* AI ejections, it
    -- never flies an AI helo to the survivor. The standing-alert AI auto-rescue is
    -- handled instead by MOOSE AICSAR below (gated on the same enableForAI flag).
    csar.enableForAI = false
    csar.csarOncrash = false          -- ejection rescues only, not every crash
    csar.allowDownedPilotCAcontrol = false
    csar.autosmoke = autosmoke
    csar.loadDistance = loadDistance
    csar.rescuehoverheight = rescueHoverHeight
    csar.messageTime = messageTime
    csar.allowFARPRescue = true       -- delivering to a friendly FARP/airfield counts

    csar:Start()

    -------------------------------------------------------------------------------
    -- AI standing alert (auto_combat_sar): MOOSE CSAR above is player-rescue only,
    -- so for real AI auto-rescue we stand up MOOSE AICSAR. AICSAR spawns its OWN
    -- rescue helos (cloned from heloTemplate) from a home AIRBASE and routes them to
    -- downed pilots, delivering to a ZONE_AIRBASE at that base. It auto-starts inside
    -- :New, and its autoonoff (default true) makes it stand down whenever a player is
    -- crewing a rescue helo -- so it never competes with the player-flown CSAR above.
    --
    -- KNOWN v1 LIMITATION (in-game pass): AICSAR spawns an anonymous pilot clone and
    -- destroys the original ejected unit, so it does NOT carry the lost airframe's
    -- unit name through to delivery -- the campaign spare-pilot scoring (combat_sar_
    -- rescues, fed by the player CSAR path above) is therefore NOT credited for an
    -- AICSAR auto-rescue yet. The v1 goal is the behaviour: an AI helo actually
    -- launches, flies out, picks the pilot up, and RTBs (the old path did nothing).
    -- Also: a player ejecting from a fixed-wing while no human is in any helo gets
    -- handled by BOTH engines (CSAR spawns a flyable downed pilot; AICSAR also spawns
    -- its clone + auto-rescues) -- a cosmetic double-spawn to evaluate in the pass.
    -------------------------------------------------------------------------------
    if enableForAI and AICSAR and data.heloTemplate and data.farp then
        local farpAirbase = AIRBASE:FindByName(data.farp)
        if farpAirbase then
            local mashZone = ZONE_AIRBASE:New(data.farp)
            local aicsar = AICSAR:New(
                "CSAR", "blue", pilotTemplate, data.heloTemplate, farpAirbase, mashZone
            )
            -- Default max reach is 50 NM from the FARP; a Combat SAR base often sits
            -- well behind the FLOT, so widen it so forward ejections are in range.
            aicsar.maxdistance = UTILS.NMToMeters(150)
            env.info(string.format(
                "DCSRetribution|Combat SAR - AICSAR AI standing alert armed "
                    .. "(helo template '%s', FARP '%s')",
                tostring(data.heloTemplate),
                tostring(data.farp)
            ))
        else
            env.warning(
                "DCSRetribution|Combat SAR - AICSAR: FARP airbase '"
                    .. tostring(data.farp)
                    .. "' not found; AI auto-rescue inactive."
            )
        end
    end

    -------------------------------------------------------------------------------
    -- Rescue scoring: report every pilot delivered home so the campaign can spare
    -- the aviator (the airframe is still lost, but the experienced pilot returns to
    -- the squadron instead of being killed at debrief).
    --
    -- MOOSE CSAR keeps the ejected aircraft's ORIGINAL unit name on each downed-pilot
    -- track and carries it into inTransitGroups when the pilot boards. We capture it
    -- on Boarded and only CREDIT it on Rescued -- the FSM event _RescuePilots fires
    -- after delivering the onboard pilots to a friendly field/FARP. A rescue helo
    -- shot down with pilots aboard never reaches Rescued, so those pilots are
    -- (correctly) never credited. The original unit name is exactly what DCS reports
    -- in the kill/crash events, so Retribution maps it straight back to the lost
    -- flight and skips killing that pilot. Appends to the dcsRetribution-core global
    -- combat_sar_rescues (written into state.json by dcs_retribution.lua).
    --
    -- The SAME pickup path also extracts stranded SCAR SOF teams (spawned as CASEVAC
    -- below): those carry a SOFRESCUE_<x>_<y> name, which we route to a separate
    -- combat_sar_sof_recoveries channel (clears the rescue + refunds the team)
    -- instead of the pilot-sparing one.
    -------------------------------------------------------------------------------
    local onboardByHeli = {}  -- heliName -> { woundedGroupName -> originalUnit }

    local function isSofRescue(name)
        return type(name) == "string" and string.sub(name, 1, 9) == "SOFRESCUE"
    end

    function csar:OnAfterBoarded(_From, _Event, _To, heliName, woundedGroupName, _desc)
        local transit = self.inTransitGroups[heliName]
        local entry = transit and transit[woundedGroupName]
        if entry and entry.originalUnit and entry.originalUnit ~= "" then
            onboardByHeli[heliName] = onboardByHeli[heliName] or {}
            onboardByHeli[heliName][woundedGroupName] = entry.originalUnit
        end
    end

    function csar:OnAfterRescued(_From, _Event, _To, _heliUnit, heliName, _pilotsSaved)
        local delivered = onboardByHeli[heliName]
        if not delivered then
            return
        end
        combat_sar_rescues = combat_sar_rescues or {}
        combat_sar_sof_recoveries = combat_sar_sof_recoveries or {}
        for _, originalUnit in pairs(delivered) do
            if isSofRescue(originalUnit) then
                table.insert(combat_sar_sof_recoveries, originalUnit)
                env.info("DCSRetribution|Combat SAR - stranded SOF team " .. tostring(originalUnit)
                    .. " extracted home; campaign will recover + refund it")
            else
                table.insert(combat_sar_rescues, originalUnit)
                env.info("DCSRetribution|Combat SAR - pilot of " .. tostring(originalUnit)
                    .. " delivered home; campaign will spare them")
            end
        end
        onboardByHeli[heliName] = nil
        dirty_state = true  -- force the next scheduled state write to include it
    end

    -------------------------------------------------------------------------------
    -- Stranded SOF teams (SCAR commander-capture loop): a botched capture leaves a
    -- SOF team in enemy territory. Spawn each on-map team (emitted by the generator)
    -- as a MOOSE CSAR CASEVAC at its strand point, so the same Combat SAR rescue
    -- helo can fly out, board it, and deliver it to a friendly field -- which clears
    -- the rescue and refunds the team at debrief. CASEVAC reuses the pilotTemplate
    -- group and the exact board/deliver path (so OnAfterRescued above sees it); the
    -- SOFRESCUE_ name is what Python recomputes to match the delivery. The C-130 SOF
    -- *insert* is unchanged (CTLD) -- only the recovery rides Combat SAR.
    -------------------------------------------------------------------------------
    local sofTeams = data.sofTeams or {}
    for _, team in pairs(sofTeams) do
        local x = tonumber(team.x)
        local y = tonumber(team.y)
        if team.name and x and y then
            -- Generator emits pydcs (x = north, y = east); the DCS world vec3 is
            -- { x = north, y = 0, z = east }, matching the SCAR plugin's convention.
            local coord = COORDINATE:NewFromVec3({ x = x, y = 0, z = y })
            csar:SpawnCASEVAC(coord, coalition.side.BLUE, "Stranded SOF team", false, team.name, "SOF Team", true)
        end
    end

    -------------------------------------------------------------------------------
    -- C-130 "King": TACAN beacon + LARS survivor-locator menu
    -------------------------------------------------------------------------------

    -- LARS: read the live downed-pilot table and message the King group a list of
    -- all active survivors (nearest first) with position and bearing/range from the
    -- King, for the crew to relay (the helo homes on the King's TACAN). Coordinate
    -- text reuses MOOSE CSAR's own settings-aware formatter so it matches the
    -- player's chosen coord system.
    local function larsReport(csarEngine, kingGroup)
        -- Failsafe discipline: an F10 LARS query reads MOOSE CSAR's live downed-pilot
        -- table (group handles can be stale, internal formatters can change); contain it
        -- so a runtime error can't throw out of the menu command.
        local ok, err = pcall(function()
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
                    table.insert(entries, {
                        dist = dist,
                        text = string.format(
                            "%s: %s (brg %03d / %.0f nm)",
                            tostring(pilot.desc or "Survivor"),
                            coordText,
                            bearing,
                            nm
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
        end)
        if not ok then
            env.warning("combatsar: LARS report error (continuing): " .. tostring(err))
        end
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
    local function activateKing(grp, reason)
        if not grp then
            return
        end
        local name = grp:GetName()
        if activatedKings[name] then
            return
        end
        local king = kingByName[name]
        if not king then
            return
        end
        if not grp:IsAlive() then
            return
        end
        local unit = grp:GetUnit(1)
        if not unit then
            return
        end
        activatedKings[name] = true
        if king.tacanChannel then
            -- Only push the scripted ActivateBeacon command to an AI-controlled, live
            -- unit. A player-occupied King has no AI controller, so the command has "no
            -- executor" (logged as an AI::Controller exception) and -- because an
            -- air-tracking beacon is re-evaluated every sim tick against the host unit --
            -- is the suspected trigger for the discrete-command-queue CTD seen in-game.
            -- Player crews set TACAN in-cockpit instead; the LARS menu still attaches.
            if unit and unit:IsAlive() and unit:GetPlayerName() == nil then
                unit:GetBeacon():ActivateTACAN(
                    tonumber(king.tacanChannel),
                    king.tacanBand or "Y",
                    king.callsign or "KING",
                    true
                )
            end
        end
        addLarsMenu(csar, grp)
        env.info(
            string.format(
                "DCSRetribution|Combat SAR King - activated '%s' via %s (TACAN %s%s, LARS menu attached)",
                name,
                tostring(reason or "unknown"),
                tostring(king.tacanChannel or "none"),
                tostring(king.tacanBand or "")
            )
        )
    end

    -- Kings already present at mission start...
    for name, _ in pairs(kingByName) do
        local grp = GROUP:FindByName(name)
        if grp and grp:IsAlive() then
            activateKing(grp, "mission-start")
        end
    end

    local function activateKingFromEvent(EventData, reason)
        local grp = EventData and EventData.IniGroup
        if not grp and EventData and EventData.IniGroupName then
            grp = GROUP:FindByName(EventData.IniGroupName)
        end
        if grp and kingByName[grp:GetName()] then
            -- Client-slot player entry can race F10 menu creation. Try now, then
            -- once more after DCS has fully attached the player to the group.
            activateKing(grp, reason)
            if not activatedKings[grp:GetName()] then
                local groupName = grp:GetName()
                timer.scheduleFunction(
                    function()
                        activateKing(
                            GROUP:FindByName(groupName),
                            tostring(reason) .. "-deferred"
                        )
                    end,
                    nil,
                    timer.getTime() + 1
                )
            end
        end
    end

    -- ...and any that spawn later (delayed / AI standing-alert Kings), plus client
    -- slot player-entry events where the group exists before it is truly usable.
    local function onKingBirth(self, EventData)
        activateKingFromEvent(EventData, "birth")
    end

    local function onKingPlayerEnter(self, EventData)
        activateKingFromEvent(EventData, "player-enter")
    end

    local kingBirthHandler = EVENTHANDLER:New()
    kingBirthHandler:HandleEvent(EVENTS.Birth, onKingBirth)
    kingBirthHandler:HandleEvent(EVENTS.PlayerEnterAircraft, onKingPlayerEnter)
    kingBirthHandler:HandleEvent(EVENTS.PlayerEnterUnit, onKingPlayerEnter)

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
