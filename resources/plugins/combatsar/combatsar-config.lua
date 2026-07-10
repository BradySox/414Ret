-------------------------------------------------------------------------------------------------------------------------------------------------------------
-- Combat SAR configuration bridge for DCS Retribution -- SURVIVOR LEDGER rewrite
--
-- ROUTE 1 (locked 2026-06-28, docs/dev/design/414th-combat-sar-normal-task-notes.md):
-- replace the two disjoint MOOSE engines (player-only CSAR that owned scoring+capture;
-- AI-only AICSAR with anonymous clones) with ONE plugin-owned survivor ledger that is the
-- single source of truth. Player and AI rescues are judged by the SAME logic, so an AI->AI
-- rescue credits exactly like a player rescue, and AI ejections are capturable (-> POW).
-- Coalition-generic: blue is wired live from the existing data fields; red would turn on the
-- day the generator emits dcsRetribution.CombatSAR.red (no further plugin changes needed) --
-- but per the squadron call of 2026-07-01 the generator DELIBERATELY never emits it: red flies
-- no CSAR, red ejections register no survivor, and no BLUE snatch party spawns to race a red
-- pilot (that traffic was pure noise). The red path below stays as dormant capability.
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
--
-- The King (C-130) still lights an air-tracking TACAN and carries the LARS F10 locator, which
-- now reads the ledger. Vanilla DCS only; pcall-guarded throughout so a bad record degrades to
-- a logged warning, never a CTD. Writes the dcs_retribution core globals combat_sar_rescues /
-- combat_sar_captures (persisted to state.json), setting dirty_state.
-- see docs/dev/design/414th-combat-sar-spec.md
-------------------------------------------------------------------------------------------------------------------------------------------------------------

env.info("DCSRetribution|Combat SAR plugin - configuration (survivor ledger)")

if dcsRetribution and dcsRetribution.CombatSAR then

    local data = dcsRetribution.CombatSAR

    ---------------------------------------------------------------------------
    -- Tunables (overridable via dcsRetribution.plugins.combatsar)
    ---------------------------------------------------------------------------
    -- Distance/speed options are authored in imperial units (ft / NM / kts) -- the units
    -- the squadron flies in -- and converted here once; internal math stays metric
    -- (MOOSE/DCS native; PICKUP_SPEED stays km/h because it compares GetVelocityKMH()).
    local FT_TO_M = 0.3048
    local NM_TO_M = 1852
    local KTS_TO_KMH = 1.852

    local POLL = 5                 -- s between ledger re-evaluations
    local PICKUP_RANGE = 500 * FT_TO_M  -- m: helo-to-survivor horizontal distance to board (option in ft)
    local PICKUP_AGL = 100 * FT_TO_M    -- m: helo must be landed / low-hover to board (option in ft)
    local PICKUP_SPEED = 30 * KTS_TO_KMH  -- km/h: ...and slow (option in kts)
    local HOME_RANGE = 1.5 * NM_TO_M    -- m: helo-to-friendly-airbase to count as delivered (option in NM)
    local AI_DISPATCH_DELAY = 60   -- s grace before AI auto-rescue launches
    local AI_DISPATCH_RETRY = 20   -- s backoff before retrying a failed AI dispatch
    local AI_DISPATCH_MAX_TRIES = 3  -- give up AI dispatch after this many failed attempts
    local messageTime = 15
    local SANDY_MAX_RANGE = 30 * NM_TO_M     -- m: max distance to retask a free AI Sandy (option in NM)
    local SANDY_ENGAGE_RADIUS = 3 * NM_TO_M  -- m: EngageTargetsInZone radius around the survivor (option in NM)

    local capture = {
        enabled = true,
        chance = 50,
        -- Party spawns this far from the survivor and walks in at ~5.5 m/s. At the old
        -- 2 NM this was an ~11-min march, so a capture essentially never completed in a
        -- mission window; 0.75 NM (~4-min approach, still killable by a Sandy) makes a
        -- capture a real, occasional outcome. Overridable per-mission via the option.
        spawnDistance = 0.75 * NM_TO_M, -- m (option in NM)
        captureRange = 500 * FT_TO_M,   -- m (option in ft)
        captureDwell = 30,
        partySize = 5,    -- total infantry, split across `teams` small groups
        teams = 3,        -- spawn this many dispersed teams instead of one column
    }

    if dcsRetribution.plugins and dcsRetribution.plugins.combatsar then
        local o = dcsRetribution.plugins.combatsar
        if o.messageTime ~= nil then messageTime = tonumber(o.messageTime) or messageTime end
        if o.pickupRangeFt ~= nil then PICKUP_RANGE = (tonumber(o.pickupRangeFt) or 500) * FT_TO_M end
        if o.pickupAGLFt ~= nil then PICKUP_AGL = (tonumber(o.pickupAGLFt) or 100) * FT_TO_M end
        if o.pickupSpeedKts ~= nil then PICKUP_SPEED = (tonumber(o.pickupSpeedKts) or 30) * KTS_TO_KMH end
        if o.homeRangeNm ~= nil then HOME_RANGE = (tonumber(o.homeRangeNm) or 1.5) * NM_TO_M end
        if o.aiDispatchDelay ~= nil then AI_DISPATCH_DELAY = tonumber(o.aiDispatchDelay) or AI_DISPATCH_DELAY end
        if o.captureEnabled ~= nil then capture.enabled = o.captureEnabled end
        if o.captureChance ~= nil then capture.chance = tonumber(o.captureChance) or capture.chance end
        if o.captureSpawnDistanceNm ~= nil then capture.spawnDistance = (tonumber(o.captureSpawnDistanceNm) or 2) * NM_TO_M end
        if o.captureRangeFt ~= nil then capture.captureRange = (tonumber(o.captureRangeFt) or 500) * FT_TO_M end
        if o.captureDwell ~= nil then capture.captureDwell = tonumber(o.captureDwell) or capture.captureDwell end
        if o.capturePartySize ~= nil then capture.partySize = tonumber(o.capturePartySize) or capture.partySize end
        if o.captureTeams ~= nil then capture.teams = tonumber(o.captureTeams) or capture.teams end
        if o.sandyMaxRangeNm ~= nil then SANDY_MAX_RANGE = (tonumber(o.sandyMaxRangeNm) or 30) * NM_TO_M end
        if o.sandyEngageRadiusNm ~= nil then SANDY_ENGAGE_RADIUS = (tonumber(o.sandyEngageRadiusNm) or 3) * NM_TO_M end
    end

    -- Safety cap on the snatch party (2026-07-08). The capture party is REAL infantry spawned
    -- onto DCS's single scripting/sim thread, so a cranked capturePartySize / captureTeams -- or a
    -- stale saved override -- piles on dozens of units per ejection and, over a few ejections, can
    -- bog a heavy mission into a hang (observed: a saved 40-strong / 4-team value spawned 80
    -- soldiers across two ejections on a full Red Tide map -> sim lock-up, no crash dump). Clamp to
    -- a sane ceiling regardless of the option, so the capture race can never be the thing that
    -- freezes the sim. The shipped defaults (5 / 3) sit well inside this; the cap only bites an
    -- over-tuned value, warning once so the player knows it was reined in.
    local MAX_PARTY_SIZE = 12
    local MAX_TEAMS = 4
    local reqParty = math.floor(tonumber(capture.partySize) or 5)
    local reqTeams = math.floor(tonumber(capture.teams) or 3)
    capture.partySize = math.max(1, math.min(reqParty, MAX_PARTY_SIZE))
    capture.teams = math.max(1, math.min(reqTeams, MAX_TEAMS))
    if reqParty > MAX_PARTY_SIZE or reqTeams > MAX_TEAMS then
        env.warning(string.format(
            "combatsar: capture party clamped to %d infantry / %d teams (requested %d/%d) -- guards "
            .. "against a scripting overload that can hang the sim.",
            capture.partySize, capture.teams, reqParty, reqTeams))
    end

    ---------------------------------------------------------------------------
    -- [TEST] thumb-on-the-scale overrides (emitted on dcsRetribution.CombatSAR
    -- only when the matching Settings toggle is on -- both default OFF). Rig the
    -- capture/pickup so a Saturday test reliably fires one path without fighting
    -- the RNG. Applied AFTER the normal options so they win; force-capture is
    -- applied last so it beats easy-rescue if both are somehow set. The scalar is
    -- emitted with set_value("true"), which can arrive as bool true or string
    -- "true" -- accept both (the readBool convention, inlined since readBool is
    -- defined later).
    local function testFlag(v) return v == true or v == "true" end
    if testFlag(data.testEasyRescue) then
        capture.enabled = false
        PICKUP_RANGE = 2000 * FT_TO_M
        PICKUP_AGL = 300 * FT_TO_M
        PICKUP_SPEED = 80 * KTS_TO_KMH
        HOME_RANGE = 3 * NM_TO_M
        AI_DISPATCH_DELAY = 30
        env.info("DCSRetribution|Combat SAR: [TEST] easy-rescue overrides applied")
    end
    if testFlag(data.testForceCapture) then
        capture.enabled = true
        capture.chance = 100
        capture.spawnDistance = 0.2 * NM_TO_M
        capture.captureRange = 1000 * FT_TO_M
        capture.captureDwell = 5
        env.info("DCSRetribution|Combat SAR: [TEST] force-capture overrides applied")
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
        -- autoSpawn (§21 on-demand rework): with no player CSAR package fragged, the
        -- runtime rescues from, in order, a real PARKED ramp helo (parkedHelos --
        -- tracked, started in place) then a cold clone template (heloTemplate). The
        -- plugin needs SOME way to rescue -- a player-crewed helo on the ledger
        -- (rescueHelos, for player pickup geometry), a parked helo, or the clone
        -- template. None -> nothing to do. (Was: bail whenever rescueHelos empty,
        -- which killed the whole ledger in the no-player-package case.)
        local autoSpawn = readBool(c.autoSpawn, false)
        local parked = c.parkedHelos or {}
        if #helos == 0 and not (autoSpawn and (#parked > 0 or c.heloTemplate)) then
            return
        end
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
            parkedHelos = parked,
            heloTemplate = c.heloTemplate,
            farp = c.farp,
            kings = c.kings or {},
            sandys = c.sandys or {},
            autoSpawn = autoSpawn,
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

    -- Root-cause guard for the "Moose.lua:11714 table index is nil" crash seen when the AI
    -- rescue dispatch CLONES a Combat SAR helo (G21). MOOSE's DATABASE:_RegisterGroupTemplate
    -- does `Templates.ClientsByID[unit.unitId] = unit` for every Client/Player-skill unit,
    -- which throws when a client slot's template carries a nil unitId (a mission-generation
    -- quirk). The rescue helos are player-flyable (Client skill), so SPAWN:Spawn() re-registers
    -- their template and trips this. Backfill a synthetic, collision-safe unitId on any client
    -- template missing one, so registration never indexes a nil. Only touches already-broken
    -- (nil-unitId) templates; pcall-guarded so it can never break init.
    local function sanitizeClientTemplates()
        if not (_DATABASE and _DATABASE.Templates and _DATABASE.Templates.Groups) then
            return 0
        end
        local synthetic = 9000000  -- above any real DCS unitId, so ClientsByID never collides
        local patched = 0
        for _, groupEntry in pairs(_DATABASE.Templates.Groups) do
            local template = groupEntry and groupEntry.Template
            local units = template and template.units
            if type(units) == "table" then
                for _, unit in pairs(units) do
                    if type(unit) == "table"
                        and (unit.skill == "Client" or unit.skill == "Player")
                        and unit.unitId == nil then
                        synthetic = synthetic + 1
                        unit.unitId = synthetic
                        patched = patched + 1
                    end
                end
            end
        end
        return patched
    end
    local okSanitize, patchedCount = pcall(sanitizeClientTemplates)
    if okSanitize and patchedCount and patchedCount > 0 then
        env.info(string.format(
            "DCSRetribution|Combat SAR plugin - backfilled unitId on %d client template(s) "
                .. "(Moose _RegisterGroupTemplate nil-index guard)", patchedCount))
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

    -- Nearest friendly field to a coordinate, resolved to a MOOSE AIRBASE *object* that
    -- the AI rescue can home to (SetHomebase / GetZone need the object, not a point).
    -- Retribution passes the control-point *display* name for the delivery field (e.g.
    -- "FOB Khe Sanh"); that matches a real airfield's DCS name but NOT a generated FARP,
    -- whose DCS object is "<CP> FARP 0" -- so a FARP-based King's delivery lookup always
    -- missed. Fall back to the closest field MOOSE can actually resolve (delivering to ANY
    -- friendly field is the feature's contract anyway).
    local function nearestFriendlyAirbaseObject(side, coord)
        local okc, abs = pcall(coalition.getAirbases, side)
        if not okc or not abs then return nil end
        local cv = coord:GetVec3()
        local best, bestd = nil, nil
        for _, ab in pairs(abs) do
            local okn, nm = pcall(function() return ab:getName() end)
            if okn and nm then
                local mab = AIRBASE:FindByName(nm)
                if mab then
                    local okp, p = pcall(function() return ab:getPoint() end)
                    if okp and p then
                        local d = (p.x - cv.x) ^ 2 + (p.z - cv.z) ^ 2
                        if not bestd or d < bestd then bestd = d; best = mab end
                    end
                end
            end
        end
        return best
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

    -- Spare credit: pilots -> combat_sar_rescues (spared at debrief), keyed by the
    -- ORIGINAL unit name DCS reports in kill/crash events, so Retribution maps it
    -- straight back to the loss.
    local function creditRescue(entry)
        if entry.credited then return end
        entry.credited = true
        entry.state = "rescued"
        if entry.unit and entry.unit ~= "" then
            table.insert(combat_sar_rescues, entry.unit)
        end
        env.info("DCSRetribution|Combat SAR - pilot of " .. tostring(entry.unit)
            .. " delivered home; campaign will spare them")
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

    -- Coordinate of a group's first ALIVE unit, pcall-guarded (nil if none alive). MOOSE's
    -- GROUP/UNIT:GetCoordinate() logs an error the moment the underlying DCS object is gone, so a
    -- group that still reports alive while its LEAD unit is dead spams the log on every poll (the
    -- GetVec3 / GetCoordinate flood seen on a bogged sim). Reading the first LIVING unit avoids the
    -- dead-object call entirely, so an attrited party stops generating error traffic.
    local function firstAliveCoord(g)
        if not g then return nil end
        local ok, units = pcall(function() return g:GetUnits() end)
        if not ok or not units then return nil end
        for _, u in ipairs(units) do
            local oka, alive = pcall(function() return u:IsAlive() end)
            if oka and alive then
                local okc, c = pcall(function() return u:GetCoordinate() end)
                if okc and c then return c end
            end
        end
        return nil
    end

    -- Find the nearest alive, idle, AI rescue helo PARKED cold on the ramp (a real,
    -- tracked untasked airframe -- §21) to commandeer for this pickup, preferred over
    -- cloning a fresh template. Nearest to the survivor first. These sit uncontrolled
    -- until started (see the dispatch below); commandeering a *parked* helo is the fix
    -- for the retired commandeer of an *airborne*, already-routed orbit helo (G21).
    local function commandeerParkedHelo(cfg, survivorCoord)
        local best, bestName, bestD = nil, nil, nil
        for _, name in ipairs(cfg.parkedHelos or {}) do
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
    -- proven AICSAR routing) and deliver it to the FARP, crediting the real unit on unload. PREFER a
    -- real PARKED ramp helo (tracked -- started in place, so its loss is recorded); only clone a
    -- fresh template when every parked helo is dead/committed or the ramp is bare. Identity lives in
    -- the ledger.
    local function dispatchAIRescue(entry)
        local ok, err = pcall(function()
            local cfg = entry.cfg
            if not cfg.farp then return end
            if not (entry.group and entry.group:IsAlive()) then return end
            local farp = AIRBASE:FindByName(cfg.farp)
            if not farp then
                -- cfg.farp is the CP display name; a generated FARP's DCS object is named
                -- "<CP> FARP 0", so this misses for a FARP-based King. Deliver to the
                -- nearest resolvable friendly field to the survivor instead of giving up.
                farp = nearestFriendlyAirbaseObject(entry.side, entry.group:GetCoordinate())
            end
            if not farp then
                env.warning("combatsar: AI dispatch - no friendly delivery field found (configured '"
                    .. tostring(cfg.farp) .. "')")
                return
            end
            local pickupzone = ZONE_GROUP:New(entry.groupName, entry.group, 300)
            local opstransport = OPSTRANSPORT:New(entry.group, pickupzone, farp:GetZone())

            local helo, heloName = commandeerParkedHelo(cfg, entry.group:GetCoordinate())
            local fg
            local commandeered = false
            if helo then
                fg = FLIGHTGROUP:New(helo)
                -- The parked ramp helo sits cold + uncontrolled; start it so it launches
                -- into the transport (a *parked* start, not the retired airborne re-task).
                -- pcall so a missing MOOSE method never aborts the dispatch -- OPSGROUP also
                -- starts an uncontrolled group when it runs the transport, so this is belt +
                -- suspenders.
                pcall(function() helo:StartUncontrolled() end)
                -- NB: mark busy only on the success path below, so a mid-dispatch error
                -- never strands a commandeered helo as permanently busy (it stays available
                -- for the retry).
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
            -- Past the last throwing call: commit the commandeer now, so an error above never
            -- leaked a busy mark.
            if commandeered and heloName then busyHelos[heloName] = true end
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
                    "RESCUE: a rescue helo is launching from the ramp for the downed pilot.")
            else
                msgToCoalition(entry.side, "RESCUE: an AI rescue helo has launched for the downed pilot.")
            end
            return true  -- dispatch fully set up
        end)
        if not ok then
            env.warning("combatsar: AI dispatch error (continuing): " .. tostring(err))
            return false  -- a Lua error (e.g. a MOOSE template crash) -> the caller may retry
        end
        return true  -- success or a clean give-up (no FARP/template) -> settled, no retry
    end

    -- Register a new survivor + spawn its group. Deduped by id (caller guarantees uniqueness).
    local function registerSurvivor(cfg, unitName, coord)
        local id = unitName
        if not id or id == "" then
            spawnIndex = spawnIndex + 1
            id = "survivor_" .. spawnIndex
        end
        if survivors[id] then return end
        local grp = spawnSurvivorGroup(cfg, coord, "Survivor")
        if not grp then return end
        survivors[id] = {
            id = id,
            unit = unitName or "",
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
            sandyName = nil,
            credited = false,
            captureRolled = false,
            t0 = timer.getTime(),
        }
        pcall(trigger.action.smoke, coord:GetVec3(), trigger.smokeColor.Red)
        msgToCoalition(cfg.side, "MAYDAY: pilot down (red smoke) -- Combat SAR is on it.")
    end

    -- Find a friendly helo deliberately picking up this survivor (landed/low+slow within range).
    -- Excludes the AI-managed transport helo (that path credits via OPSTRANSPORT, not geometry).
    local function findBoardingHelo(entry)
        local sc = firstAliveCoord(entry.group)
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
        local aliveNames = {}
        if entry.party then
            for _, gname in ipairs(entry.party) do
                local g = GROUP:FindByName(gname)
                if g and g:IsAlive() then
                    alive[#alive + 1] = g
                    aliveNames[#aliveNames + 1] = gname
                end
            end
            -- Drop dead teams from the ledger so a killed snatch group is never FindByName-polled
            -- again -- the per-cycle work shrinks as the party is attrited, instead of re-scanning
            -- the full original list every poll for the life of the survivor.
            entry.party = aliveNames
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
        local pc = firstAliveCoord(entry.group)
        local inRange = false
        if pc then
            for _, g in ipairs(alive) do
                local gc = firstAliveCoord(g)
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
            registerSurvivor(cfg, name, COORDINATE:NewFromVec3(pos))
        end)
        if not ok then
            env.warning("combatsar: eject handler error (continuing): " .. tostring(err))
        end
    end
    world.addEventHandler(ejectBridge)

    ---------------------------------------------------------------------------
    -- Sandy (SCAR) AI retasking: divert a free AI-crewed Sandy off its planned
    -- racetrack to hold and actively engage near a live ejection instead of
    -- staying in its static pre-planned box (previously the only behaviour --
    -- see 414th-features.md §15). The Sandy's own weapons-free ROE + CAS task
    -- (configure_scar, set at generation) does the actual shooting once
    -- retasked; this just moves where it's looking. Player-flown Sandys are
    -- never touched (voice/SRS coordination is the intended path for those).
    ---------------------------------------------------------------------------
    local sandyByName = {}
    for _, cfg in ipairs(configs) do
        for _, name in ipairs(cfg.sandys) do
            sandyByName[name] = cfg.side
        end
    end

    local busySandy = {}  -- sandy group name -> survivor id it's committed to

    -- Hold height over the survivor (m above ground) for the diverted Sandy's
    -- waypoint + orbit anchor: low enough to work the area, high enough to
    -- clear small arms.
    local SANDY_HOLD_ALT = 450

    -- Nearest alive, idle, AI-crewed Sandy of the right side within range of coord.
    local function findFreeSandy(side, coord)
        local best, bestName, bestD = nil, nil, nil
        for name, sandySide in pairs(sandyByName) do
            if sandySide == side and not busySandy[name] then
                local g = GROUP:FindByName(name)
                if g and g:IsAlive() and not groupHasPlayer(g) then
                    local u = g:GetUnit(1)
                    local c = u and u:IsAlive() and u:GetCoordinate()
                    if c then
                        local d = c:Get2DDistance(coord)
                        if d <= SANDY_MAX_RANGE and (not bestD or d < bestD) then
                            best, bestName, bestD = g, name, d
                        end
                    end
                end
            end
        end
        return best, bestName
    end

    -- Divert a free Sandy to hold near and actively work the area around this
    -- survivor. Commits at most one Sandy per survivor; retries every tick
    -- until one frees up (all busy/dead/out of range this tick -> just wait).
    local function dispatchSandy(entry)
        if entry.sandyName then return end
        local pu = entry.group and entry.group:GetUnit(1)
        local pc = pu and pu:IsAlive() and pu:GetCoordinate()
        if not pc then return end
        local sandy, sandyName = findFreeSandy(entry.side, pc)
        if not sandy then return end
        local ok, err = pcall(function()
            local u = sandy:GetUnit(1)
            local speed = u:GetVelocityMPS()
            if not speed or speed < UTILS.KnotsToMps(80) then
                speed = UTILS.KnotsToMps(150)
            end
            local point = pc:GetVec2()
            -- Route push, NOT SetTask: EngageTargetsInZone is an EN-ROUTE task,
            -- and the DCS controller silently rejects a main-task ComboTask that
            -- contains one -- the flown G23 signature was exactly "divert
            -- message, no movement" (Trail 2, 2026-07-02). En-route tasks are
            -- valid in a waypoint's task list, and the transit leg physically
            -- flies the Sandy to the survivor (the stock MOOSE
            -- transit-then-orbit pattern). Waypoint speeds are km/h in MOOSE.
            local from = u:GetCoordinate()
            local hold = COORDINATE:NewFromVec2(point, SANDY_HOLD_ALT)
            -- TaskOrbitCircleAtVec2 adds land.getHeight itself: pass the AGL
            -- offset, never hold.y (terrain+alt), or the orbit ends up at
            -- 2x terrain + alt MSL over high ground.
            local orbit = sandy:TaskOrbitCircleAtVec2(point, SANDY_HOLD_ALT, speed)
            local engage = sandy:EnRouteTaskEngageTargetsInZone(
                point, SANDY_ENGAGE_RADIUS, { "Ground Units" }, 0)
            entry.sandyReturn = from:GetVec2()  -- station anchor for the release
            sandy:Route({
                from:WaypointAirTurningPoint("BARO", speed * 3.6, {}, "SANDY divert"),
                hold:WaypointAirTurningPoint(
                    "BARO", speed * 3.6, { engage, orbit }, "SANDY hold over survivor"),
            }, 1)
        end)
        if not ok then
            env.warning("combatsar: Sandy dispatch error (continuing): " .. tostring(err))
            return
        end
        busySandy[sandyName] = entry.id
        entry.sandyName = sandyName
        msgToCoalition(entry.side, "SANDY " .. sandyName
            .. " is diverting to hold over the downed pilot.")
    end

    -- Free a committed Sandy once its survivor is resolved (rescued/captured/
    -- dead) so it can serve a later ejection. The divert replaced the group's
    -- tasking with our route, so a bare ClearTasks() would leave it flying a
    -- straight line -- route it back to the station it was diverted from and
    -- hold there, available for the next ejection.
    local function releaseSandy(entry)
        if not entry.sandyName then return end
        busySandy[entry.sandyName] = nil
        local g = GROUP:FindByName(entry.sandyName)
        entry.sandyName = nil
        if g and g:IsAlive() then
            pcall(function()
                g:ClearTasks()
                local ret = entry.sandyReturn
                if not ret then return end
                local u = g:GetUnit(1)
                if not (u and u:IsAlive()) then return end
                local speed = u:GetVelocityMPS()
                if not speed or speed < UTILS.KnotsToMps(80) then
                    speed = UTILS.KnotsToMps(150)
                end
                local from = u:GetCoordinate()
                local station = COORDINATE:NewFromVec2(ret, SANDY_HOLD_ALT)
                -- AGL offset, not station.y: see the divert orbit above.
                local orbit = g:TaskOrbitCircleAtVec2(ret, SANDY_HOLD_ALT, speed)
                g:Route({
                    from:WaypointAirTurningPoint("BARO", speed * 3.6, {}, "SANDY released"),
                    station:WaypointAirTurningPoint(
                        "BARO", speed * 3.6, { orbit }, "SANDY back on station"),
                }, 1)
            end)
        end
        entry.sandyReturn = nil
    end

    ---------------------------------------------------------------------------
    -- Main tick: drive every survivor through the ledger state machine.
    ---------------------------------------------------------------------------
    local function tick()
        local ok, err = pcall(function()
            for id, e in pairs(survivors) do
                -- Retire a downed pilot KILLED on the ground before rescue/capture. The reap below
                -- only fires on rescued/captured/dead, but nothing ever set "dead" -- so a pilot
                -- killed while down lingered in the ledger forever, and every tick polled its dead
                -- group (the UNIT GetVec3 flood seen on a bogged sim). A live pickup/capture flips
                -- the state first, so this only catches an unresolved death (group had spawned and
                -- is now gone); a never-spawned group (e.group nil) is left untouched.
                if e.state == "down" and e.group and not e.group:IsAlive() then
                    e.state = "dead"
                end
                if e.state == "down" then
                    -- Capture race: roll a snatch party once per survivor (on land).
                    if capture.enabled and not e.captureRolled then
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
                    -- AI auto-rescue after a short grace (lets a player or the orbiting alert
                    -- react). Retry a FAILED dispatch (a MOOSE template error, etc.) a few times
                    -- with backoff rather than abandoning the survivor on the first error --
                    -- `e.dispatched` is only latched once the dispatch actually succeeds.
                    if e.state == "down" and e.cfg.autoSpawn and not e.dispatched
                        and (timer.getTime() - e.t0) >= AI_DISPATCH_DELAY
                        and (not e.nextDispatchAt or timer.getTime() >= e.nextDispatchAt) then
                        if dispatchAIRescue(e) then
                            e.dispatched = true
                        else
                            e.dispatchTries = (e.dispatchTries or 0) + 1
                            if e.dispatchTries >= AI_DISPATCH_MAX_TRIES then
                                e.dispatched = true  -- give up; leave the survivor to a player pickup
                            else
                                e.nextDispatchAt = timer.getTime() + AI_DISPATCH_RETRY
                            end
                        end
                    end
                    -- Sandy retasking: no grace period -- protecting the survivor starts
                    -- immediately. Retries every tick until a free AI Sandy is found.
                    if e.state == "down" then
                        dispatchSandy(e)
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
                    releaseSandy(e)
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
                            text = string.format("Survivor: %s (brg %03d / %.0f nm)",
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
    local sandyCount = 0
    for _ in pairs(sandyByName) do sandyCount = sandyCount + 1 end
    env.info(string.format(
        "DCSRetribution|Combat SAR plugin - survivor ledger started (%d coalition(s), %d King(s), "
            .. "%d Sandy(s), capture %s, AI-rescue %s)",
        #configs, kingCount, sandyCount,
        capture.enabled and "on" or "off",
        cfgBySide[coalition.side.BLUE] and cfgBySide[coalition.side.BLUE].autoSpawn and "on" or "off"))

else
    env.info("DCSRetribution|Combat SAR plugin - dcsRetribution.CombatSAR not present; skipping")
end
