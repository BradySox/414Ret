-------------------------------------------------------------------------------------------------------------------------------------------------------------
-- Combat SAR configuration bridge for DCS Retribution -- SURVIVOR LEDGER rewrite
--
-- ROUTE 1 (locked 2026-06-28, docs/dev/design/414th-combat-sar-normal-task-notes.md):
-- replace the two disjoint MOOSE engines (player-only CSAR that owned scoring+capture;
-- AI-only AICSAR with anonymous clones) with ONE plugin-owned survivor ledger that is the
-- single source of truth. Player and AI rescues are judged by the SAME logic, so an AI->AI
-- rescue credits exactly like a player rescue, and AI ejections are capturable (-> POW).
-- Coalition-generic: blue is wired live from the existing data fields; red turns on the day
-- the generator emits dcsRetribution.CombatSAR.red (no further plugin changes needed).
--
-- Flow per downed pilot:
--   * S_EVENT_EJECTION (either coalition) -> register a survivor in the ledger, spawn a
--     downed-pilot group (cloned from that coalition's pilotTemplate), pop red smoke.
--   * Capture race: the OPPOSING coalition may push a snatch party; holding within range for
--     captureDwell s with the pilot un-rescued -> CAPTURED (append combat_sar_captures, POW).
--   * Rescue (engine-agnostic): a friendly helo (PLAYER, landed/low+slow within pickup range)
--     boards the survivor; delivering to any friendly airfield/FARP -> RESCUED (append
--     combat_sar_rescues, pilot spared at debrief). AI auto-rescue reuses MOOSE OPSTRANSPORT
--     (proven AICSAR routing) but carries the LEDGER's real identity, so it credits too.
--   * Stranded SOF teams (SCAR loop) ride the same pickup -> combat_sar_sof_recoveries.
--
-- The King (C-130) still lights an air-tracking TACAN and carries the LARS F10 locator, which
-- now reads the ledger. Vanilla DCS only; pcall-guarded throughout so a bad record degrades to
-- a logged warning, never a CTD. Writes the dcs_retribution core globals combat_sar_rescues /
-- combat_sar_captures / combat_sar_sof_recoveries (persisted to state.json), setting dirty_state.
-- see docs/dev/design/414th-combat-sar-spec.md
-------------------------------------------------------------------------------------------------------------------------------------------------------------

env.info("DCSRetribution|Combat SAR plugin - configuration (survivor ledger)")

if dcsRetribution and dcsRetribution.CombatSAR then

    local data = dcsRetribution.CombatSAR

    ---------------------------------------------------------------------------
    -- Tunables (overridable via dcsRetribution.plugins.combatsar)
    ---------------------------------------------------------------------------
    local POLL = 5                 -- s between ledger re-evaluations
    local PICKUP_RANGE = 150       -- m: helo-to-survivor horizontal distance to board
    local PICKUP_AGL = 30          -- m: helo must be landed / low-hover to board
    local PICKUP_SPEED = 60        -- km/h: ...and slow
    local HOME_RANGE = 2500        -- m: helo-to-friendly-airbase to count as delivered
    local AI_DISPATCH_DELAY = 60   -- s grace before AI auto-rescue launches
    local messageTime = 15

    local capture = {
        enabled = true,
        chance = 50,
        spawnDistance = 4000,
        captureRange = 150,
        captureDwell = 30,
        partySize = 5,    -- total infantry, split across `teams` small groups
        teams = 3,        -- spawn this many dispersed teams instead of one column
    }

    if dcsRetribution.plugins and dcsRetribution.plugins.combatsar then
        local o = dcsRetribution.plugins.combatsar
        if o.messageTime ~= nil then messageTime = tonumber(o.messageTime) or messageTime end
        if o.pickupRange ~= nil then PICKUP_RANGE = tonumber(o.pickupRange) or PICKUP_RANGE end
        if o.pickupAGL ~= nil then PICKUP_AGL = tonumber(o.pickupAGL) or PICKUP_AGL end
        if o.pickupSpeed ~= nil then PICKUP_SPEED = tonumber(o.pickupSpeed) or PICKUP_SPEED end
        if o.homeRange ~= nil then HOME_RANGE = tonumber(o.homeRange) or HOME_RANGE end
        if o.aiDispatchDelay ~= nil then AI_DISPATCH_DELAY = tonumber(o.aiDispatchDelay) or AI_DISPATCH_DELAY end
        if o.captureEnabled ~= nil then capture.enabled = o.captureEnabled end
        if o.captureChance ~= nil then capture.chance = tonumber(o.captureChance) or capture.chance end
        if o.captureSpawnDistance ~= nil then capture.spawnDistance = tonumber(o.captureSpawnDistance) or capture.spawnDistance end
        if o.captureRange ~= nil then capture.captureRange = tonumber(o.captureRange) or capture.captureRange end
        if o.captureDwell ~= nil then capture.captureDwell = tonumber(o.captureDwell) or capture.captureDwell end
        if o.capturePartySize ~= nil then capture.partySize = tonumber(o.capturePartySize) or capture.partySize end
        if o.captureTeams ~= nil then capture.teams = tonumber(o.captureTeams) or capture.teams end
    end

    ---------------------------------------------------------------------------
    -- Coalition configs (blue from the existing top-level fields for back-compat;
    -- red from data.red when the generator emits it -- the only thing red needs).
    ---------------------------------------------------------------------------
    local function readBool(v, default)
        if v == nil then return default end
        return (v == true) or (v == "true")
    end

    local configs = {}
    local cfgBySide = {}

    local function addConfig(color, side, enemySide, enemyCountry, c)
        if not c or not c.pilotTemplate then return end
        local helos = c.rescueHelos or {}
        if #helos == 0 then return end
        local cfg = {
            color = color,
            side = side,
            enemySide = enemySide,
            -- Prefer the generator-emitted enemy faction country (always registered on
            -- the enemy coalition in this .miz); the CJTF_* constant is only a fallback
            -- for older saves -- it is NOT registered when the factions use real/CH
            -- nations (e.g. Vietnam), which spawned the snatch party on the wrong side.
            enemyCountry = tonumber(c.enemyCountry) or enemyCountry,
            pilotTemplate = c.pilotTemplate,
            rescueHelos = helos,
            heloTemplate = c.heloTemplate,
            farp = c.farp,
            kings = c.kings or {},
            sofTeams = c.sofTeams or {},
            enableForAI = readBool(c.enableForAI, false),
        }
        configs[#configs + 1] = cfg
        cfgBySide[side] = cfg
    end

    addConfig("blue", coalition.side.BLUE, coalition.side.RED, country.id.CJTF_RED, data)
    if data.red then
        addConfig("red", coalition.side.RED, coalition.side.BLUE, country.id.CJTF_BLUE, data.red)
    end

    if #configs == 0 then
        env.info("DCSRetribution|Combat SAR plugin - no rescue helos/template; skipping")
        return
    end

    -- Live-updating friendly-helo sets (one per coalition) for player pickup detection.
    for _, cfg in ipairs(configs) do
        cfg.heloSet = SET_GROUP:New()
            :FilterCoalitions(cfg.color)
            :FilterCategoryHelicopter()
            :FilterStart()
    end

    ---------------------------------------------------------------------------
    -- The ledger: the single source of truth for every downed survivor.
    --   survivors[id] = { id, unit, isSof, color, side, cfg, group, groupName,
    --                     coord, state, party, dwell, dispatched, aiManaged,
    --                     heloName, credited, captureRolled, t0 }
    -- state: "down" -> "boarding" -> "rescued" | "captured" | "dead"
    ---------------------------------------------------------------------------
    local survivors = {}
    combat_sar_rescues = combat_sar_rescues or {}
    combat_sar_captures = combat_sar_captures or {}
    combat_sar_sof_recoveries = combat_sar_sof_recoveries or {}
    local spawnIndex = 0
    local snatchCounter = 0

    ---------------------------------------------------------------------------
    -- Helpers (defined before first use -- definition order matters in DCS Lua)
    ---------------------------------------------------------------------------
    local function msgToCoalition(side, text)
        pcall(trigger.action.outTextForCoalition, side, text, messageTime * 2)
    end

    -- A unit is "landed / low-hover and slow" (a deliberate pickup posture).
    local function unitLowSlow(u)
        if not u or not u:IsAlive() then return false end
        local c = u:GetCoordinate()
        if not c then return false end
        local agl = (u:GetHeight() or 0) - (c:GetLandHeight() or 0)
        local spd = u:GetVelocityKMH() or 999
        return agl <= PICKUP_AGL and spd <= PICKUP_SPEED
    end

    -- True if the coordinate is over water (no land-based snatch party there).
    local function isWater(coord)
        local ok, st = pcall(land.getSurfaceType, coord:GetVec2())
        return ok and (st == land.SurfaceType.WATER or st == land.SurfaceType.SHALLOW_WATER)
    end

    -- Nearest friendly airbase/FARP/ship point to a coordinate (delivery target).
    local function nearestFriendlyAirbase(side, coord)
        local okc, abs = pcall(coalition.getAirbases, side)
        if not okc or not abs then return nil, nil end
        local cv = coord:GetVec3()
        local best, bestd = nil, nil
        for _, ab in pairs(abs) do
            local okp, p = pcall(function() return ab:getPoint() end)
            if okp and p then
                local d = math.sqrt((p.x - cv.x) ^ 2 + (p.z - cv.z) ^ 2)
                if not bestd or d < bestd then bestd = d; best = p end
            end
        end
        return best, bestd
    end

    -- Spawn a downed-pilot group cloned from the coalition's late-activation template.
    local function spawnSurvivorGroup(cfg, coord, label)
        spawnIndex = spawnIndex + 1
        local alias = string.format("CombatSAR %s %d", label or "Survivor", spawnIndex)
        local grp = nil
        local ok, res = pcall(function()
            return SPAWN:NewWithAlias(cfg.pilotTemplate, alias)
                :InitDelayOff()
                :SpawnFromCoordinate(coord)
        end)
        if ok then grp = res else env.warning("combatsar: survivor spawn failed: " .. tostring(res)) end
        return grp
    end

    -- Spare/extract credit. Pilots -> combat_sar_rescues (spared at debrief); SOF teams ->
    -- combat_sar_sof_recoveries (recovered + refunded). Both keyed by the ORIGINAL unit name
    -- DCS reports in kill/crash events, so Retribution maps it straight back to the loss.
    local function creditRescue(entry)
        if entry.credited then return end
        entry.credited = true
        entry.state = "rescued"
        if entry.isSof then
            table.insert(combat_sar_sof_recoveries, entry.unit)
            env.info("DCSRetribution|Combat SAR - stranded SOF team " .. tostring(entry.unit)
                .. " extracted home; campaign will recover + refund it")
        else
            if entry.unit and entry.unit ~= "" then
                table.insert(combat_sar_rescues, entry.unit)
            end
            env.info("DCSRetribution|Combat SAR - pilot of " .. tostring(entry.unit)
                .. " delivered home; campaign will spare them")
        end
        dirty_state = true
        msgToCoalition(entry.side, "RESCUE COMPLETE: survivor delivered to a friendly field.")
    end

    -- Capture credit: hold the aviator as a recoverable POW (Python record_pow_captures reads
    -- unit/x/y; the extra coalition key is forward-compat for the red POW path, ignored today).
    local function recordCapture(entry)
        local v
        local u = entry.group and entry.group:GetUnit(1)
        local c = u and u:GetCoordinate()
        v = (c and c:GetVec2()) or entry.coord:GetVec2()
        table.insert(combat_sar_captures, {
            unit = entry.unit or "",
            x = v.x,
            y = v.y,
            coalition = entry.color,
        })
        dirty_state = true
        entry.state = "captured"
        msgToCoalition(entry.side, "Downed pilot CAPTURED by enemy forces -- now a POW. "
            .. "A recovery may be possible on a later turn.")
    end

    -- Spawn one small snatch team (a single ground group) of `size` soldiers at `teamCoord`,
    -- routed to converge on the survivor. Returns the spawned group name, or nil on failure.
    local function spawnSnatchTeam(cfg, teamCoord, sv, size)
        snatchCounter = snatchCounter + 1
        local gname = string.format("CSAR Snatch Party %d", snatchCounter)
        local sp = teamCoord:GetVec2()
        local units = {}
        for i = 1, math.max(1, size) do
            units[i] = {
                ["type"] = "Soldier AK",  -- vanilla DCS infantry
                ["name"] = string.format("%s U%d", gname, i),
                ["x"] = sp.x + math.random(-15, 15),
                ["y"] = sp.y + math.random(-15, 15),
                ["heading"] = 0,
                ["skill"] = "Average",
                ["playerCanDrive"] = false,
            }
        end
        local group_data = {
            ["visible"] = false,
            ["hidden"] = false,
            ["name"] = gname,
            ["task"] = {},
            ["category"] = Group.Category.GROUND,
            ["country"] = cfg.enemyCountry,
            ["units"] = units,
            ["route"] = {
                ["points"] = {
                    [1] = { ["x"] = sp.x, ["y"] = sp.y, ["type"] = "Turning Point",
                            ["action"] = "Off Road", ["speed"] = 5.5 },
                    [2] = { ["x"] = sv.x, ["y"] = sv.y, ["type"] = "Turning Point",
                            ["action"] = "Off Road", ["speed"] = 5.5 },
                },
            },
        }
        local ok, spawned = pcall(mist.dynAdd, group_data)
        if not ok or not spawned then
            env.warning("combatsar: snatch-team spawn failed: " .. tostring(spawned))
            return nil
        end
        pcall(trigger.action.smoke, { x = sp.x, y = 0, z = sp.y }, trigger.smokeColor.Red)
        return spawned.name or gname
    end

    -- Spawn the OPPOSING coalition's snatch party: several small teams ringed around the
    -- survivor at spawnDistance on different bearings, each routed in. Returns the list of
    -- spawned group names (nil if none spawned) -- one long marching column reads as a single
    -- target, so disperse the same total infantry into independent fire teams.
    local function spawnSnatchParty(cfg, survivorCoord)
        local total = math.max(1, capture.partySize)
        local teams = math.max(1, math.min(math.floor(capture.teams), total))
        local sv = survivorCoord:GetVec2()
        local baseBearing = math.random(0, 359)
        local names = {}
        local remaining = total
        for t = 1, teams do
            -- Even split of the remaining soldiers across the remaining teams.
            local size = math.ceil(remaining / (teams - t + 1))
            remaining = remaining - size
            local bearing = (baseBearing + (t - 1) * (360 / teams) + math.random(-20, 20)) % 360
            local teamCoord = survivorCoord:Translate(capture.spawnDistance, bearing)
            local name = spawnSnatchTeam(cfg, teamCoord, sv, size)
            if name then names[#names + 1] = name end
        end
        if #names == 0 then return nil end
        return names
    end

    -- Rescue helos currently committed to a survivor, so two ejections don't grab the same one and
    -- we don't re-task a helo already mid-rescue. Freed again when its survivor is delivered.
    local busyHelos = {}

    -- True if any unit in the group is player-crewed (never commandeer a human's helo).
    local function groupHasPlayer(g)
        local ok, units = pcall(function() return g:GetUnits() end)
        if not ok or not units then return false end
        for _, u in ipairs(units) do
            local okn, name = pcall(function() return u:GetPlayerName() end)
            if okn and name and name ~= "" then return true end
        end
        return false
    end

    -- Find the nearest alive, idle, AI rescue helo ALREADY in the mission (the planned Combat SAR
    -- flight orbiting the FLOT) to commandeer for this pickup, rather than spawning a fresh clone.
    local function commandeerRescueHelo(cfg, survivorCoord)
        local best, bestName, bestD = nil, nil, nil
        for _, name in ipairs(cfg.rescueHelos or {}) do
            if not busyHelos[name] then
                local g = GROUP:FindByName(name)
                if g and g:IsAlive() and not groupHasPlayer(g) then
                    local u = g:GetUnit(1)
                    local c = u and u:IsAlive() and u:GetCoordinate()
                    if c and survivorCoord then
                        local d = c:Get2DDistance(survivorCoord)
                        if not bestD or d < bestD then best, bestName, bestD = g, name, d end
                    end
                end
            end
        end
        return best, bestName
    end

    -- AI auto-rescue: send a helo to board the LEDGER's survivor as cargo (MOOSE OPSTRANSPORT, the
    -- proven AICSAR routing) and deliver it to the FARP, crediting the real unit on unload. PREFER to
    -- commandeer a rescue helo already flying the Combat SAR orbit; only clone a fresh one from the
    -- FARP when every planned rescue helo is dead or already committed. Identity lives in the ledger.
    local function dispatchAIRescue(entry)
        local ok, err = pcall(function()
            local cfg = entry.cfg
            if not cfg.farp then return end
            if not (entry.group and entry.group:IsAlive()) then return end
            local farp = AIRBASE:FindByName(cfg.farp)
            if not farp then
                env.warning("combatsar: AI dispatch - FARP '" .. tostring(cfg.farp) .. "' not found")
                return
            end
            local pickupzone = ZONE_GROUP:New(entry.groupName, entry.group, 300)
            local opstransport = OPSTRANSPORT:New(entry.group, pickupzone, farp:GetZone())

            local helo, heloName = commandeerRescueHelo(cfg, entry.group:GetCoordinate())
            local fg
            local commandeered = false
            if helo then
                fg = FLIGHTGROUP:New(helo)
                busyHelos[heloName] = true
                commandeered = true
            elseif cfg.heloTemplate then
                spawnIndex = spawnIndex + 1
                heloName = string.format("CombatSAR Rescue %d", spawnIndex)
                local newhelo = SPAWN:NewWithAlias(cfg.heloTemplate, heloName)
                    :InitUnControlled(true)
                    :InitDelayOff()
                    :Spawn()
                if not newhelo then return end
                fg = FLIGHTGROUP:New(newhelo)
                fg:Activate()
                heloName = newhelo:GetName()
            else
                return  -- nothing alive to commandeer and no template to clone
            end
            fg:SetHomebase(farp)
            fg:SetDefaultAltitude(1500)
            fg:SetDefaultSpeed(100)
            fg:AddOpsTransport(opstransport)
            entry.aiManaged = true
            entry.heloName = heloName
            -- Credit when the survivor cargo is unloaded at the FARP; release a commandeered helo
            -- so it can serve a later ejection instead of forcing a fresh clone every time.
            function fg:OnAfterUnloaded(_From, _Event, _To, _OpsGroupCargo)
                if entry.state ~= "rescued" and entry.state ~= "captured" then
                    creditRescue(entry)
                end
                if commandeered and heloName then busyHelos[heloName] = nil end
            end
            if commandeered then
                msgToCoalition(entry.side,
                    "RESCUE: a Combat SAR helo on station is diverting to the downed pilot.")
            else
                msgToCoalition(entry.side, "RESCUE: an AI helo has launched for the downed pilot.")
            end
        end)
        if not ok then
            env.warning("combatsar: AI dispatch error (continuing): " .. tostring(err))
        end
    end

    -- Register a new survivor + spawn its group. Deduped by id (caller guarantees uniqueness).
    local function registerSurvivor(cfg, unitName, coord, isSof)
        local id = unitName
        if not id or id == "" then
            spawnIndex = spawnIndex + 1
            id = "survivor_" .. spawnIndex
        end
        if survivors[id] then return end
        local grp = spawnSurvivorGroup(cfg, coord, isSof and "SOF" or "Survivor")
        if not grp then return end
        survivors[id] = {
            id = id,
            unit = unitName or "",
            isSof = isSof or false,
            color = cfg.color,
            side = cfg.side,
            cfg = cfg,
            group = grp,
            groupName = grp:GetName(),
            coord = coord,
            state = "down",
            party = nil,
            dwell = 0,
            dispatched = false,
            aiManaged = false,
            credited = false,
            captureRolled = false,
            t0 = timer.getTime(),
        }
        pcall(trigger.action.smoke, coord:GetVec3(), trigger.smokeColor.Red)
        if isSof then
            msgToCoalition(cfg.side, "Stranded team in the field -- Combat SAR can extract it.")
        else
            msgToCoalition(cfg.side, "MAYDAY: pilot down (red smoke) -- Combat SAR is on it.")
        end
    end

    -- Find a friendly helo deliberately picking up this survivor (landed/low+slow within range).
    -- Excludes the AI-managed transport helo (that path credits via OPSTRANSPORT, not geometry).
    local function findBoardingHelo(entry)
        local u0 = entry.group and entry.group:GetUnit(1)
        local sc = u0 and u0:GetCoordinate()
        if not sc then return nil end
        local found = nil
        entry.cfg.heloSet:ForEachGroupAlive(function(g)
            if found then return end
            local name = g:GetName()
            if entry.aiManaged and name == entry.heloName then return end
            local u = g:GetUnit(1)
            if not (u and u:IsAlive()) then return end
            local gc = u:GetCoordinate()
            if not gc then return end
            if gc:Get2DDistance(sc) <= PICKUP_RANGE and unitLowSlow(u) then
                found = g
            end
        end)
        return found
    end

    -- Advance (or stand down) the capture clock for a survivor with an active snatch party.
    -- entry.party is a list of team group names; the party is neutralized only when every
    -- team is dead, and any one surviving team holding on the pilot runs the capture clock.
    local function advanceCapture(entry)
        local alive = {}
        if entry.party then
            for _, gname in ipairs(entry.party) do
                local g = GROUP:FindByName(gname)
                if g and g:IsAlive() then alive[#alive + 1] = g end
            end
        end
        if #alive == 0 then
            if entry.party then
                msgToCoalition(entry.side, "Capture party neutralized -- the downed pilot is safe. "
                    .. "Continue the recovery.")
            end
            entry.party = nil
            entry.dwell = 0
            return
        end
        local pu = entry.group and entry.group:GetUnit(1)
        local pc = pu and pu:GetCoordinate()
        local inRange = false
        if pc then
            for _, g in ipairs(alive) do
                local gu = g:GetUnit(1)
                local gc = gu and gu:GetCoordinate()
                if gc and gc:Get2DDistance(pc) <= capture.captureRange then
                    inRange = true
                    break
                end
            end
        end
        if inRange then
            entry.dwell = (entry.dwell or 0) + POLL
            if entry.dwell >= capture.captureDwell then
                recordCapture(entry)
                pcall(function() entry.group:Destroy() end)
                for _, g in ipairs(alive) do
                    pcall(function() g:Destroy() end)
                end
                entry.party = nil
            end
        else
            entry.dwell = 0
        end
    end

    ---------------------------------------------------------------------------
    -- Eject handler: register every ejection for a configured coalition.
    ---------------------------------------------------------------------------
    local ejectSeen = {}  -- aircraft unit name -> true (one survivor per airframe)
    local ejectBridge = {}
    function ejectBridge:onEvent(event)
        local ok, err = pcall(function()
            if not event or event.id ~= world.event.S_EVENT_EJECTION then return end
            local init = event.initiator
            if not init then return end
            local okn, name = pcall(function() return init:getName() end)
            if not okn or not name or ejectSeen[name] then return end
            local okc, cn = pcall(function() return init:getCoalition() end)
            if not okc then return end
            local cfg = cfgBySide[cn]
            if not cfg then return end  -- coalition not wired (e.g. red before its data lands)
            local okp, pos = pcall(function() return init:getPosition().p end)
            if not okp or not pos then return end
            ejectSeen[name] = true
            registerSurvivor(cfg, name, COORDINATE:NewFromVec3(pos), false)
        end)
        if not ok then
            env.warning("combatsar: eject handler error (continuing): " .. tostring(err))
        end
    end
    world.addEventHandler(ejectBridge)

    ---------------------------------------------------------------------------
    -- Stranded SOF teams (SCAR commander-capture loop): each on-map team emitted by the
    -- generator becomes a ledger survivor the same rescue helo can extract. SOFRESCUE_ name
    -- is what Python recomputes to match the delivery; no capture race for these.
    ---------------------------------------------------------------------------
    for _, cfg in ipairs(configs) do
        for _, team in pairs(cfg.sofTeams) do
            local x = tonumber(team.x)
            local y = tonumber(team.y)
            if team.name and x and y then
                -- Generator emits pydcs (x = north, y = east); DCS vec3 = { x = north, y = 0, z = east }.
                registerSurvivor(cfg, team.name, COORDINATE:NewFromVec3({ x = x, y = 0, z = y }), true)
            end
        end
    end

    ---------------------------------------------------------------------------
    -- Main tick: drive every survivor through the ledger state machine.
    ---------------------------------------------------------------------------
    local function tick()
        local ok, err = pcall(function()
            for id, e in pairs(survivors) do
                if e.state == "down" then
                    -- Capture race: roll a snatch party once per survivor (pilots only, on land).
                    if capture.enabled and not e.isSof and not e.captureRolled then
                        e.captureRolled = true
                        local u = e.group and e.group:GetUnit(1)
                        local c = u and u:GetCoordinate()
                        if c and not isWater(c) and math.random(1, 100) <= capture.chance then
                            e.party = spawnSnatchParty(e.cfg, c)
                            if e.party then
                                msgToCoalition(e.side, "MAYDAY: enemy ground forces are moving to "
                                    .. "capture the downed pilot (red smoke). SANDY -- protect the "
                                    .. "survivor, kill the snatch party!")
                            end
                        end
                    end
                    -- Player / manual pickup (AI-managed survivors credit via OPSTRANSPORT instead).
                    if not e.aiManaged then
                        local helo = findBoardingHelo(e)
                        if helo then
                            e.state = "boarding"
                            e.heloName = helo:GetName()
                            pcall(function() e.group:Destroy() end)
                            msgToCoalition(e.side, "Survivor aboard -- RTB to a friendly field to "
                                .. "complete the rescue.")
                        end
                    end
                    -- AI auto-rescue after a short grace (lets a player or the orbiting alert react).
                    if e.state == "down" and e.cfg.enableForAI and not e.dispatched
                        and (timer.getTime() - e.t0) >= AI_DISPATCH_DELAY then
                        e.dispatched = true
                        dispatchAIRescue(e)
                    end
                    -- Capture clock (only meaningful while still down).
                    if e.party then advanceCapture(e) end

                elseif e.state == "boarding" and not e.aiManaged then
                    -- Player-carried survivor: rescued when the helo reaches a friendly field low+slow.
                    local helo = GROUP:FindByName(e.heloName)
                    if not (helo and helo:IsAlive()) then
                        -- Lost the ride: re-drop the survivor where they were.
                        e.state = "down"
                        e.heloName = nil
                        local grp = spawnSurvivorGroup(e.cfg, e.coord, "Survivor")
                        if grp then e.group = grp; e.groupName = grp:GetName() end
                    else
                        local u = helo:GetUnit(1)
                        local hc = u and u:GetCoordinate()
                        if hc then
                            local _, dist = nearestFriendlyAirbase(e.side, hc)
                            if dist and dist <= HOME_RANGE and unitLowSlow(u) then
                                creditRescue(e)
                            end
                        end
                    end
                end

                -- Reap finished entries.
                if e.state == "rescued" or e.state == "captured" or e.state == "dead" then
                    survivors[id] = nil
                end
            end
        end)
        if not ok then
            env.warning("combatsar: tick error (continuing): " .. tostring(err))
        end
        return timer.getTime() + POLL
    end
    timer.scheduleFunction(tick, {}, timer.getTime() + POLL)

    ---------------------------------------------------------------------------
    -- C-130 "King": air-tracking TACAN beacon + LARS survivor-locator menu (reads the ledger)
    ---------------------------------------------------------------------------
    local function larsReport(side, kingGroup)
        local ok, err = pcall(function()
            local kingUnit = kingGroup:GetUnit(1)
            if not kingUnit or not kingUnit:IsAlive() then return end
            local kingCoord = kingUnit:GetCoordinate()
            local entries = {}
            for _, e in pairs(survivors) do
                if e.side == side and (e.state == "down" or e.state == "boarding") then
                    local u = e.group and e.group:GetUnit(1)
                    local wc = u and u:GetCoordinate()
                    if wc then
                        local dist = kingCoord:Get2DDistance(wc)
                        local bearing = math.floor(kingCoord:HeadingTo(wc) + 0.5) % 360
                        entries[#entries + 1] = {
                            dist = dist,
                            text = string.format("%s: %s (brg %03d / %.0f nm)",
                                e.isSof and "SOF team" or "Survivor",
                                wc:ToStringMGRS(),
                                bearing,
                                UTILS.MetersToNM(dist)),
                        }
                    end
                end
            end
            table.sort(entries, function(a, b) return a.dist < b.dist end)
            local msg
            if #entries == 0 then
                msg = "LARS: no active survivors."
            else
                msg = "LARS - active survivors (nearest first):"
                for _, entry in ipairs(entries) do msg = msg .. "\n" .. entry.text end
            end
            MESSAGE:New(msg, messageTime * 2):ToGroup(kingGroup)
        end)
        if not ok then env.warning("combatsar: LARS report error (continuing): " .. tostring(err)) end
    end

    local kingByName = {}
    for _, cfg in ipairs(configs) do
        for _, king in pairs(cfg.kings) do
            if king.group then
                kingByName[king.group] = { king = king, side = cfg.side }
            end
        end
    end

    -- 2026-06-30 in-game finding: a live session never logged a single King
    -- activation across ~80 minutes despite correct group-name data (verified
    -- against the generated .miz), on either the mission-start scan or the
    -- Birth/PlayerEnterAircraft/PlayerEnterUnit event path. Every early-return
    -- below was silent, so there was no way to tell which guard was tripping.
    -- Each now logs why, and a periodic sweep (below, alongside the survivor
    -- tick) retries any King still unactivated instead of relying on a single
    -- event firing at the right moment.
    local activatedKings = {}
    local function activateKing(grp, reason)
        if not grp then return end
        local name = grp:GetName()
        if activatedKings[name] then return end
        local rec = kingByName[name]
        if not rec then return end
        if not grp:IsAlive() then
            env.info("DCSRetribution|Combat SAR King - '" .. name .. "' not yet alive ("
                .. tostring(reason or "unknown") .. "); will retry")
            return
        end
        local unit = grp:GetUnit(1)
        if not unit then
            env.info("DCSRetribution|Combat SAR King - '" .. name .. "' has no unit #1 ("
                .. tostring(reason or "unknown") .. "); will retry")
            return
        end
        local king = rec.king
        activatedKings[name] = true
        if king.tacanChannel then
            -- Only AI-controlled (no player) Kings get the scripted beacon command; a player
            -- King sets TACAN in-cockpit (the air-tracking beacon on a player unit is the
            -- suspected discrete-command-queue CTD trigger). LARS menu still attaches.
            if unit:IsAlive() and unit:GetPlayerName() == nil then
                pcall(function()
                    unit:GetBeacon():ActivateTACAN(
                        tonumber(king.tacanChannel),
                        king.tacanBand or "Y",
                        king.callsign or "KING",
                        true)
                end)
            end
        end
        local root = MENU_GROUP:New(grp, "Combat SAR")
        MENU_GROUP_COMMAND:New(grp, "LARS - Locate Survivors", root, larsReport, rec.side, grp)
        env.info(string.format(
            "DCSRetribution|Combat SAR King - activated '%s' via %s (TACAN %s%s, LARS menu attached)",
            name, tostring(reason or "unknown"),
            tostring(king.tacanChannel or "none"), tostring(king.tacanBand or "")))
    end

    for name, _ in pairs(kingByName) do
        local grp = GROUP:FindByName(name)
        if grp and grp:IsAlive() then
            activateKing(grp, "mission-start")
        else
            env.info("DCSRetribution|Combat SAR King - '" .. name
                .. "' not found/alive at mission-start; will retry")
        end
    end

    local function activateKingFromEvent(EventData, reason)
        local grp = EventData and EventData.IniGroup
        if not grp and EventData and EventData.IniGroupName then
            grp = GROUP:FindByName(EventData.IniGroupName)
        end
        -- Some event types populate IniUnit but not IniGroup/IniGroupName (observed
        -- 2026-06-30: PlayerEnterAircraft/PlayerEnterUnit never resolved a King via
        -- either field, so activation never fired) -- fall back to the unit's own
        -- owning group.
        if not grp and EventData and EventData.IniUnit then
            local ok, g = pcall(function() return EventData.IniUnit:GetGroup() end)
            if ok then grp = g end
        end
        if grp and kingByName[grp:GetName()] then
            activateKing(grp, reason)
            if not activatedKings[grp:GetName()] then
                local groupName = grp:GetName()
                timer.scheduleFunction(function()
                    activateKing(GROUP:FindByName(groupName), tostring(reason) .. "-deferred")
                end, nil, timer.getTime() + 1)
            end
        end
    end

    local kingBirthHandler = EVENTHANDLER:New()
    kingBirthHandler:HandleEvent(EVENTS.Birth, function(_, e) activateKingFromEvent(e, "birth") end)
    kingBirthHandler:HandleEvent(EVENTS.PlayerEnterAircraft, function(_, e) activateKingFromEvent(e, "player-enter") end)
    kingBirthHandler:HandleEvent(EVENTS.PlayerEnterUnit, function(_, e) activateKingFromEvent(e, "player-enter") end)

    -- Safety net: neither the mission-start scan nor the birth/player-enter events
    -- are guaranteed to catch a King the moment it becomes alive (e.g. a client
    -- slot that isn't truly queryable until the sim clock is actually running, or
    -- an event whose group fields didn't resolve). Re-sweep every POLL until every
    -- known King has activated, then stop.
    local function retryUnactivatedKings()
        local pending = false
        for name, _ in pairs(kingByName) do
            if not activatedKings[name] then
                pending = true
                local grp = GROUP:FindByName(name)
                if grp and grp:IsAlive() then
                    activateKing(grp, "retry-sweep")
                end
            end
        end
        if pending then
            return timer.getTime() + POLL
        end
        return nil
    end
    timer.scheduleFunction(retryUnactivatedKings, {}, timer.getTime() + POLL)

    local kingCount = 0
    for _ in pairs(kingByName) do kingCount = kingCount + 1 end
    env.info(string.format(
        "DCSRetribution|Combat SAR plugin - survivor ledger started (%d coalition(s), %d King(s), "
            .. "capture %s, AI-rescue %s)",
        #configs, kingCount,
        capture.enabled and "on" or "off",
        cfgBySide[coalition.side.BLUE] and cfgBySide[coalition.side.BLUE].enableForAI and "on" or "off"))

else
    env.info("DCSRetribution|Combat SAR plugin - dcsRetribution.CombatSAR not present; skipping")
end
