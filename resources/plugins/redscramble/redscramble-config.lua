---------------------------------------------------------------------------------------------------
-- Host red scramble (§61) -- the game master's "give the flight something to shoot" button.
--
-- Reads dcsRetribution.redScramble (emitted only when the host_red_scramble setting is on and red
-- fighter templates + red airfields exist; inert otherwise):
--   templates = { { group = "<late-activation .miz group>", label = "MiG-29S" }, ... }
--   bases     = { { name = "<red airfield name>" }, ... }   -- nearest-front first
--
-- An F10 "HOST: Red Scramble" menu (per-group for the configured host player names, or
-- coalition-wide for BLUE when none are configured) clones a 2/4-ship from a template at the
-- chosen base via MOOSE SPAWN:SpawnAtAirbase, sets it weapons free, and then a GCI loop re-vectors
-- every live bandit group onto the nearest airborne BLUE fighter (players preferred) each cycle --
-- the "force them to engage" half. Bandits are free, untracked event content by design (the
-- drop-spawn cheat precedent): their kills of players record natively, their own deaths change
-- nothing at the turn boundary.
--
-- Spawn mode notes (QRA history, intercept-config.lua): every GROUND spawn (cold/hot/runway) can
-- fail or stall on a congested ramp, so the default is an in-air spawn low over the field at a
-- scramble speed -- the same profile the QRA dispatcher uses (field elevation + AGL, InitSpeed).
-- The Moose SpawnAtAirbase air-spawn bug (mis-scheduled BASE.CreateEventTakeoff -> a logged error
-- 5 s after spawn) is harmless here: unlike the QRA dispatcher we never wait on the takeoff event,
-- and the intercept plugin's monkeypatch fixes it globally anyway when QRA is enabled.
--
-- Definition order matters (Lua 5.1): helpers precede use. pcall-guarded so a hiccup in a menu
-- press or a vector tick never takes the mission down.
---------------------------------------------------------------------------------------------------

if not (dcsRetribution and dcsRetribution.redScramble) then
    return
end

local data = dcsRetribution.redScramble

-- Defaults. Overridable via the plugin options (dcsRetribution.plugins.redscramble).
local HOST_NAMES = "" -- comma-separated DCS player names; empty = every BLUE client
local TAKEOFF = "air" -- air | hot | runway
local VECTOR_INTERVAL = 45 -- s between intercept vector updates

if dcsRetribution.plugins and dcsRetribution.plugins.redscramble then
    local o = dcsRetribution.plugins.redscramble
    if o.hostPlayers ~= nil then
        HOST_NAMES = tostring(o.hostPlayers)
    end
    if o.takeoff ~= nil then
        TAKEOFF = string.lower(tostring(o.takeoff))
    end
    VECTOR_INTERVAL = tonumber(o.vectorIntervalS) or VECTOR_INTERVAL
end

local MENU_MAX_BASES = 9 -- keep the base list on one F10 page (emit is nearest-front first)
local SCRAMBLE_AGL_M = 760 -- air-spawn altitude over the field (the QRA scramble profile)
local SCRAMBLE_SPEED_KT = 300 -- air-spawn speed (a ~0 kt clone spawns stalled; QRA lesson)
local MENU_SWEEP_INTERVAL = 30 -- s between host-player scans (slot-ins, re-slots)
local FIRST_VECTOR_DELAY = 5 -- s from spawn to the first intercept vector
local ANNOUNCE_SECONDS = 15

local template_count = 0
if type(data.templates) == "table" then
    template_count = #data.templates
end
local base_count = 0
if type(data.bases) == "table" then
    base_count = #data.bases
end
if template_count == 0 or base_count == 0 then
    env.info("REDSCRAMBLE|: no templates or bases emitted; menu not built")
    return
end

-- Parse the host allow-list (trimmed, case-insensitive). Each entry matches as a plain
-- SUBSTRING of the player name, so a squadron whose names carry a changing flight prefix
-- ("Viper 1-1 | Flash" today, "Hawg 2-3 | Flash" next event) can gate on the static tag
-- ("Flash") alone; a full exact name still matches (it contains itself). Empty list =
-- coalition-wide menu.
local host_tokens = {}
for name in string.gmatch(HOST_NAMES, "[^,]+") do
    local trimmed = name:gsub("^%s+", ""):gsub("%s+$", "")
    if trimmed ~= "" then
        host_tokens[#host_tokens + 1] = string.lower(trimmed)
    end
end
local host_count = #host_tokens

-- Feedback to whoever pressed the button: the host's group when known, else the BLUE coalition
-- (the coalition-wide menu has no requester group).
local function announce(requester_gid, text)
    if requester_gid then
        trigger.action.outTextForGroup(requester_gid, text, ANNOUNCE_SECONDS)
    else
        trigger.action.outTextForCoalition(coalition.side.BLUE, text, ANNOUNCE_SECONDS)
    end
end

---------------------------------------------------------------------------------------------------
-- Target picking: the nearest airborne BLUE fighter to a point, players first. The whole point of
-- the button is to feed the humans, so an airborne player always outranks a nearer AI flight.
---------------------------------------------------------------------------------------------------
local function nearest_airborne_unit(point, units)
    local best_unit, best_d2
    for _, u in ipairs(units or {}) do
        local ok = pcall(function()
            if u and u:isExist() and u:getLife() > 0 and u:inAir() then
                local p = u:getPoint()
                local dx, dz = p.x - point.x, p.z - point.z
                local d2 = dx * dx + dz * dz
                if not best_d2 or d2 < best_d2 then
                    best_unit, best_d2 = u, d2
                end
            end
        end)
        if not ok then
            -- a despawning unit mid-iteration; skip it
        end
    end
    return best_unit
end

local function nearest_blue_target(point)
    local players = nil
    pcall(function()
        players = coalition.getPlayers(coalition.side.BLUE)
    end)
    local target = nearest_airborne_unit(point, players)
    if target then
        return target
    end
    -- No airborne player: fall back to any airborne blue aircraft (one flat list so
    -- the nearest pick compares across every group).
    local candidates = {}
    for _, cat in ipairs({ Group.Category.AIRPLANE, Group.Category.HELICOPTER }) do
        local ok, groups = pcall(coalition.getGroups, coalition.side.BLUE, cat)
        if ok and groups then
            for _, grp in ipairs(groups) do
                for _, u in ipairs(grp:getUnits() or {}) do
                    candidates[#candidates + 1] = u
                end
            end
        end
    end
    return nearest_airborne_unit(point, candidates)
end

---------------------------------------------------------------------------------------------------
-- The GCI loop: every VECTOR_INTERVAL, each live bandit group gets (re)pointed at the nearest
-- airborne blue fighter via a hard AttackGroup task -- re-set only when the target changes so we
-- don't reset the AI's attack geometry every tick. Ground-started flights are left alone until
-- airborne (a task push mid-taxi can wedge the takeoff).
---------------------------------------------------------------------------------------------------
local active = {} -- { { name = <group name>, lastTarget = <groupId|nil> }, ... }
local loop_running = false

local function group_lead_point(grp)
    for _, u in ipairs(grp:getUnits() or {}) do
        if u and u:isExist() and u:getLife() > 0 then
            return u:getPoint()
        end
    end
    return nil
end

local function group_airborne(grp)
    for _, u in ipairs(grp:getUnits() or {}) do
        if u and u:isExist() and u:inAir() then
            return true
        end
    end
    return false
end

local function vector_bandits()
    local remaining = {}
    for _, rec in ipairs(active) do
        local grp = Group.getByName(rec.name)
        if grp and grp:isExist() and grp:getSize() > 0 then
            table.insert(remaining, rec)
            if group_airborne(grp) then
                local point = group_lead_point(grp)
                local target = point and nearest_blue_target(point)
                if target then
                    local tgt_group = target:getGroup()
                    local tgt_id = tgt_group and tgt_group:getID()
                    if tgt_id and tgt_id ~= rec.lastTarget then
                        rec.lastTarget = tgt_id
                        pcall(function()
                            grp:getController():setTask({
                                id = "AttackGroup",
                                params = { groupId = tgt_id },
                            })
                        end)
                    end
                end
            end
        end
    end
    active = remaining
    if #active == 0 then
        loop_running = false
        return nil -- every bandit is dead; stop polling until the next scramble
    end
    return timer.getTime() + VECTOR_INTERVAL
end

-- pcall-guarded: an error in a scheduled tick otherwise kills the loop silently for the rest of
-- the mission (log + retry instead).
local function guarded_vector()
    local ok, result = pcall(vector_bandits)
    if not ok then
        env.warning("REDSCRAMBLE|: vector error (retrying): " .. tostring(result))
        return timer.getTime() + VECTOR_INTERVAL
    end
    return result
end

local function start_vector_loop()
    if not loop_running then
        loop_running = true
        timer.scheduleFunction(guarded_vector, {}, timer.getTime() + FIRST_VECTOR_DELAY)
    end
end

---------------------------------------------------------------------------------------------------
-- Spawning. One MOOSE SPAWN per template, built lazily and reused so repeat presses get unique
-- clone names ("HOSTILE SCRAMBLE MiG-29S#001", ...).
---------------------------------------------------------------------------------------------------
local spawners = {}

local function spawner_for(template_index, template)
    if not spawners[template_index] then
        spawners[template_index] = SPAWN:NewWithAlias(
            template.group, "HOSTILE SCRAMBLE " .. tostring(template.label)
        )
    end
    return spawners[template_index]
end

local function do_scramble(base_name, template_index, size, requester_gid)
    local ok, err = pcall(function()
        local template = data.templates[template_index]
        if not template then
            return
        end
        local airbase = AIRBASE:FindByName(base_name)
        if not airbase then
            announce(requester_gid, "Red scramble: airbase '" .. tostring(base_name) .. "' not found.")
            return
        end
        -- A base captured mid-mission is the host's call -- warn, then launch anyway
        -- (the default air spawn works overhead whoever owns the ramp).
        pcall(function()
            if airbase:GetCoalition() ~= coalition.side.RED then
                announce(requester_gid, "Red scramble: " .. base_name .. " is no longer red -- launching overhead anyway.")
            end
        end)

        local sp = spawner_for(template_index, template)
        sp:InitGrouping(size)

        local takeoff = SPAWN.Takeoff.Air
        local altitude = nil
        if TAKEOFF == "hot" then
            takeoff = SPAWN.Takeoff.Hot
        elseif TAKEOFF == "runway" then
            takeoff = SPAWN.Takeoff.Runway
        else
            -- The QRA scramble profile: low over the field, at flying speed.
            local elevation = 0
            pcall(function()
                elevation = airbase:GetCoordinate():GetLandHeight() or 0
            end)
            altitude = elevation + SCRAMBLE_AGL_M
            pcall(function()
                sp:InitSpeedKnots(SCRAMBLE_SPEED_KT)
            end)
        end

        local grp = sp:SpawnAtAirbase(airbase, takeoff, altitude)
        if not grp then
            announce(requester_gid, "Red scramble FAILED at " .. base_name .. " (no spawn -- ramp full?).")
            env.warning("REDSCRAMBLE|: spawn failed: " .. tostring(template.group) .. " at " .. base_name)
            return
        end
        pcall(function()
            grp:OptionROEWeaponFree()
        end)
        pcall(function()
            grp:OptionROTEvadeFire()
        end)
        table.insert(active, { name = grp:GetName() })
        start_vector_loop()
        announce(requester_gid, string.format(
            "RED SCRAMBLE: %dx %s launching from %s.", size, tostring(template.label), base_name))
        env.info(string.format(
            "REDSCRAMBLE|: spawned %dx %s at %s (%s) -> %s",
            size, tostring(template.label), base_name, TAKEOFF, grp:GetName()))
    end)
    if not ok then
        env.error("REDSCRAMBLE|: scramble error: " .. tostring(err))
        announce(requester_gid, "Red scramble FAILED (script error -- see dcs.log).")
    end
end

-- The one-click emergency: first (best) template, 2-ship, from the listed base nearest to an
-- airborne blue player -- so the bandits arrive where the boys actually are. No airborne player
-- (everyone still on the ramp) falls back to the first listed base (nearest the front).
local function auto_scramble(requester_gid)
    local ok, err = pcall(function()
        local reference = nil
        pcall(function()
            local players = coalition.getPlayers(coalition.side.BLUE)
            for _, u in ipairs(players or {}) do
                if u and u:isExist() and u:inAir() then
                    reference = u:getPoint()
                    break
                end
            end
        end)
        local best_name = data.bases[1] and data.bases[1].name
        if reference then
            local best_d2
            local limit = math.min(base_count, MENU_MAX_BASES)
            for i = 1, limit do
                local base_name = data.bases[i].name
                local airbase = AIRBASE:FindByName(base_name)
                if airbase then
                    local v = airbase:GetVec2()
                    local dx, dz = v.x - reference.x, v.y - reference.z
                    local d2 = dx * dx + dz * dz
                    if not best_d2 or d2 < best_d2 then
                        best_name, best_d2 = base_name, d2
                    end
                end
            end
        end
        if best_name then
            do_scramble(best_name, 1, 2, requester_gid)
        end
    end)
    if not ok then
        env.error("REDSCRAMBLE|: auto-scramble error: " .. tostring(err))
    end
end

---------------------------------------------------------------------------------------------------
-- F10 menu. Per-group for matching host players (built on slot-in via S_EVENT_BIRTH plus a
-- periodic sweep -- the §58 pattern, which also covers the nil-getPlayerName BIRTH race), or
-- coalition-wide for BLUE when no host names are configured. NOTE: a group menu is visible to
-- every client in that group -- the host should fly their own flight (or trust their wingman).
---------------------------------------------------------------------------------------------------
local menu_built = {} -- gid -> true

local function add_menu(gid)
    -- gid == nil builds the coalition-wide BLUE variant with the same tree.
    local addSub, addCmd
    if gid then
        addSub = function(name, parent)
            return missionCommands.addSubMenuForGroup(gid, name, parent)
        end
        addCmd = function(name, parent, fn)
            return missionCommands.addCommandForGroup(gid, name, parent, fn)
        end
    else
        addSub = function(name, parent)
            return missionCommands.addSubMenuForCoalition(coalition.side.BLUE, name, parent)
        end
        addCmd = function(name, parent, fn)
            return missionCommands.addCommandForCoalition(coalition.side.BLUE, name, parent, fn)
        end
    end

    local root = addSub("HOST: Red Scramble", nil)
    addCmd("EMERGENCY: bandits toward the flight", root, function()
        auto_scramble(gid)
    end)
    local limit = math.min(base_count, MENU_MAX_BASES)
    for i = 1, limit do
        local base_name = data.bases[i].name
        local base_menu = addSub(base_name, root)
        for t = 1, template_count do
            local label = tostring(data.templates[t].label)
            addCmd(label .. " x2", base_menu, function()
                do_scramble(base_name, t, 2, gid)
            end)
            addCmd(label .. " x4", base_menu, function()
                do_scramble(base_name, t, 4, gid)
            end)
        end
    end
    if base_count > limit then
        env.info(string.format(
            "REDSCRAMBLE|: %d red base(s) beyond the %d-item menu cap dropped (nearest-front kept)",
            base_count - limit, MENU_MAX_BASES))
    end
end

local function build_menu_for_group(gid)
    if not gid or menu_built[gid] then
        return
    end
    menu_built[gid] = true
    add_menu(gid)
    env.info("REDSCRAMBLE|: host menu built for group id " .. tostring(gid))
end

local function unit_gid_if_host(u)
    local gid = nil
    pcall(function()
        if not (u and u.getPlayerName) then
            return
        end
        local player_name = u:getPlayerName()
        if not player_name then
            return
        end
        local lower_name = string.lower(player_name)
        for _, token in ipairs(host_tokens) do
            -- Plain find (no patterns): player names carry pattern-magic
            -- characters ("Viper 1-1 | Flash").
            if string.find(lower_name, token, 1, true) then
                local grp = u:getGroup()
                if grp then
                    gid = grp:getID()
                end
                return
            end
        end
    end)
    return gid
end

local function sweep_for_hosts()
    pcall(function()
        local players = coalition.getPlayers(coalition.side.BLUE)
        for _, u in ipairs(players or {}) do
            build_menu_for_group(unit_gid_if_host(u))
        end
    end)
    return timer.getTime() + MENU_SWEEP_INTERVAL
end

local birth_handler = {}
function birth_handler:onEvent(event)
    if not event or event.id ~= world.event.S_EVENT_BIRTH then
        return
    end
    build_menu_for_group(unit_gid_if_host(event.initiator))
end

local ok, err = pcall(function()
    if host_count == 0 then
        add_menu(nil)
        env.info(string.format(
            "REDSCRAMBLE|: no hostPlayers configured -- menu visible to ALL BLUE clients "
                .. "(%d base(s), %d type(s))", base_count, template_count))
    else
        world.addEventHandler(birth_handler)
        timer.scheduleFunction(sweep_for_hosts, {}, timer.getTime() + MENU_SWEEP_INTERVAL)
        env.info(string.format(
            "REDSCRAMBLE|: watching for %d host player name(s) (%d base(s), %d type(s))",
            host_count, base_count, template_count))
    end
end)
if not ok then
    env.error("REDSCRAMBLE|: setup error: " .. tostring(err))
end
