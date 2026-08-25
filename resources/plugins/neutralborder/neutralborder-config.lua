---------------------------------------------------------------------------------------------------
-- Neutral-faction border defense (§96) -- a neutral country's airspace, defended.
--
-- Reads dcsRetribution.neutralBorder (emitted only when neutral_border_defense is on and the
-- campaign authored zones the generator could build; inert otherwise). Design + decisions:
-- docs/dev/design/414th-neutral-border-defense-notes.md. Constraints a reader could undo:
--   * The shadow spawns on the intruder's OPPOSING coalition (SPAWN:InitCountry/InitCoalition)
--     because a true-neutral unit cannot fire, ever -- do not "fix" the spawn to neutral.
--   * Shadow-phase ROE is RETURN FIRE, not weapons hold: it defends, never initiates (DM call).
--   * AI intruders are shadowed but NEVER escalated on (DM call). Only players earn the attack.
--   * Escalation is ROE + tasking only. Never enableEmission (hard constraint).
--   * Spawns are free, untracked event content (the §61 precedent).
-- Values arrive as Lua strings (LuaItem contract) -- tonumber() everything numeric here.
-- Border verts are terrain XY: vert.x = DCS x (north), vert.y = DCS z (east).
-- Definition order matters (Lua 5.1): helpers precede use. pcall-guarded throughout.
---------------------------------------------------------------------------------------------------

if not (dcsRetribution and dcsRetribution.neutralBorder) then
    return
end

local data = dcsRetribution.neutralBorder

-- Defaults. Overridable via the plugin options (dcsRetribution.plugins.neutralborder).
local WARN_DWELL_S = 30 -- inside the border this long -> warning + shadow launch
local ENGAGE_DWELL_S = 180 -- a PLAYER inside this long -> engaged
local SCAN_INTERVAL_S = 10 -- border scan cadence
local VECTOR_INTERVAL_S = 45 -- shadow vector cadence
local MAX_SHADOWS = 2 -- concurrent shadow flights per zone
local DRAW_BORDERS = true -- F10 border polylines (the §86 invisible-bubble lesson)

if dcsRetribution.plugins and dcsRetribution.plugins.neutralborder then
    local o = dcsRetribution.plugins.neutralborder
    WARN_DWELL_S = tonumber(o.warnDwellS) or WARN_DWELL_S
    ENGAGE_DWELL_S = tonumber(o.engageDwellS) or ENGAGE_DWELL_S
    SCAN_INTERVAL_S = tonumber(o.scanIntervalS) or SCAN_INTERVAL_S
    VECTOR_INTERVAL_S = tonumber(o.vectorIntervalS) or VECTOR_INTERVAL_S
    MAX_SHADOWS = tonumber(o.maxShadows) or MAX_SHADOWS
    if o.drawBorders ~= nil then
        DRAW_BORDERS = (o.drawBorders == true) or (o.drawBorders == "true")
    end
end

local EXIT_GRACE_S = 120 -- outside this long (pre-escalation) -> shadow stands down
local SHADOW_AGL_M = 760 -- air-spawn altitude over the field (the QRA scramble profile)
local SHADOW_SPEED_KT = 300 -- air-spawn speed (a ~0 kt clone spawns stalled; QRA lesson)
local SHADOW_DESPAWN_S = 300 -- stood-down shadow lifetime after the RTB vector
local FT_TO_M = 0.3048
local MARKUP_ID_BASE = 96000 -- §96 block; one freeform id per zone

local function log(msg)
    env.info("NEUTRALBORDER|: " .. tostring(msg))
end

---------------------------------------------------------------------------------------------------
-- Zone parse. A zone that cannot be parsed is dropped, never fatal.
---------------------------------------------------------------------------------------------------
local zones = {}

for _, raw in ipairs(data.zones or {}) do
    local ok = pcall(function()
        local verts = {}
        local minx, maxx, minz, maxz
        for _, v in ipairs(raw.border or {}) do
            local x, z = tonumber(v.x), tonumber(v.y)
            if x and z then
                verts[#verts + 1] = { x = x, z = z }
                if not minx or x < minx then minx = x end
                if not maxx or x > maxx then maxx = x end
                if not minz or z < minz then minz = z end
                if not maxz or z > maxz then maxz = z end
            end
        end
        if #verts >= 3 and raw.fighterTemplate and raw.field then
            zones[#zones + 1] = {
                country = tostring(raw.country or "Neutral"),
                field = tostring(raw.field),
                floor_m = (tonumber(raw.floorFt) or 10000) * FT_TO_M,
                floor_ft = tonumber(raw.floorFt) or 10000,
                fighter_template = tostring(raw.fighterTemplate),
                sam_template = raw.samTemplate and tostring(raw.samTemplate) or nil,
                red_country = tonumber(raw.redCountryId),
                blue_country = tonumber(raw.blueCountryId),
                verts = verts,
                bbox = { minx = minx, maxx = maxx, minz = minz, maxz = maxz },
                -- runtime
                spawners = {}, -- per clone side: [side] = SPAWN
                shadows = {}, -- shadow name -> record
                shadow_count = 0,
                sam_spawner = nil,
                sam_spawned = false,
            }
        end
    end)
    if not ok then
        log("zone parse error -- zone dropped")
    end
end

if #zones == 0 then
    log("no usable zones -- inert")
    return
end

---------------------------------------------------------------------------------------------------
-- Geometry. Ray-cast point-in-polygon against unit getPoint() (p.x north, p.z east).
---------------------------------------------------------------------------------------------------
local function in_bbox(zone, px, pz)
    local b = zone.bbox
    return px >= b.minx and px <= b.maxx and pz >= b.minz and pz <= b.maxz
end

local function in_polygon(zone, px, pz)
    local inside = false
    local verts = zone.verts
    local j = #verts
    for i = 1, #verts do
        local vi, vj = verts[i], verts[j]
        if ((vi.z > pz) ~= (vj.z > pz))
            and (px < (vj.x - vi.x) * (pz - vi.z) / (vj.z - vi.z) + vi.x) then
            inside = not inside
        end
        j = i
    end
    return inside
end

---------------------------------------------------------------------------------------------------
-- Small helpers.
---------------------------------------------------------------------------------------------------
local function opposing(side)
    if side == coalition.side.BLUE then
        return coalition.side.RED
    end
    return coalition.side.BLUE
end

local function clone_country(zone, intruder_side)
    if intruder_side == coalition.side.BLUE then
        return zone.red_country
    end
    return zone.blue_country
end

local function lead_unit(group)
    if not group then
        return nil
    end
    local units = group:getUnits()
    if not units then
        return nil
    end
    for _, u in ipairs(units) do
        if u and u:isExist() then
            return u
        end
    end
    return nil
end

local function is_player_group(group)
    local found = false
    pcall(function()
        for _, u in ipairs(group:getUnits() or {}) do
            if u and u:isExist() and u.getPlayerName and u:getPlayerName() then
                found = true
                return
            end
        end
    end)
    return found
end

local function announce(group, msg)
    pcall(function()
        trigger.action.outTextForGroup(group:getID(), msg, 20)
    end)
end

---------------------------------------------------------------------------------------------------
-- F10 border polylines (drawn once at start; the border must be visible -- §86 lesson).
---------------------------------------------------------------------------------------------------
local function draw_borders()
    if not DRAW_BORDERS then
        return
    end
    for zi, zone in ipairs(zones) do
        pcall(function()
            local args = { 7, -1, MARKUP_ID_BASE + zi } -- freeform, all coalitions
            for _, v in ipairs(zone.verts) do
                args[#args + 1] = { x = v.x, y = 0, z = v.z }
            end
            -- close the ring
            args[#args + 1] = { x = zone.verts[1].x, y = 0, z = zone.verts[1].z }
            -- APP-6 neutral green, matching the planner map's border colour
            -- (client/src/theme/mapColors.ts). Amber is SUSPECTED there.
            args[#args + 1] = { 0.25, 0.69, 0.42, 0.9 } -- line
            args[#args + 1] = { 0.25, 0.69, 0.42, 0.05 } -- fill
            args[#args + 1] = 2 -- dashed
            args[#args + 1] = true -- read only
            trigger.action.markupToAll(unpack(args))
        end)
    end
end

---------------------------------------------------------------------------------------------------
-- Shadow flights: spawn on the intruder's opposing coalition, return-fire, and vector loop.
---------------------------------------------------------------------------------------------------
local intruders = {} -- group name -> state
local vector_loop_running = false
local vector_tick -- forward declaration comment only; defined below before first use in start_vector_loop

local function spawner_for(zone, zi, clone_side)
    if not zone.spawners[clone_side] then
        local tag = (clone_side == coalition.side.RED) and "R" or "B"
        zone.spawners[clone_side] = SPAWN:NewWithAlias(
            zone.fighter_template,
            "NEUTRAL AF " .. zone.country .. " " .. tag .. zi
        )
    end
    return zone.spawners[clone_side]
end

local function spawn_shadow(zone, zi, intruder_name, intruder_side)
    if zone.shadow_count >= MAX_SHADOWS then
        return nil
    end
    local shadow = nil
    local ok, err = pcall(function()
        local airbase = AIRBASE:FindByName(zone.field)
        if not airbase then
            log("airbase '" .. zone.field .. "' not found -- no shadow")
            return
        end
        local clone_side_id = opposing(intruder_side)
        local sp = spawner_for(zone, zi, clone_side_id)
        sp:InitGrouping(2)
        local country = clone_country(zone, intruder_side)
        if country and sp.InitCountry then
            sp:InitCountry(country)
        end
        if sp.InitCoalition then
            sp:InitCoalition(clone_side_id)
        end
        local elevation = 0
        pcall(function()
            elevation = airbase:GetCoordinate():GetLandHeight() or 0
        end)
        pcall(function()
            sp:InitSpeedKnots(SHADOW_SPEED_KT)
        end)
        local grp = sp:SpawnAtAirbase(airbase, SPAWN.Takeoff.Air, elevation + SHADOW_AGL_M)
        if not grp then
            return
        end
        -- Return fire, never initiate: the shadow-phase ROE (DM call). EvadeFire
        -- so a shot at it is answered with defense, not a parade-ground death.
        pcall(function()
            grp:OptionROEReturnFire()
        end)
        pcall(function()
            grp:OptionROTEvadeFire()
        end)
        shadow = {
            name = grp:GetName(),
            group = grp,
            intruder = intruder_name,
            zone = zi,
            escalated = false,
            stood_down = false,
        }
        zone.shadows[shadow.name] = shadow
        zone.shadow_count = zone.shadow_count + 1
        log(string.format(
            "shadow %s up from %s vs %s", shadow.name, zone.field, intruder_name))
    end)
    if not ok then
        log("shadow spawn error: " .. tostring(err))
    end
    return shadow
end

local function shadow_for(intruder_name)
    for _, zone in ipairs(zones) do
        for _, shadow in pairs(zone.shadows) do
            if shadow.intruder == intruder_name and not shadow.stood_down then
                return shadow
            end
        end
    end
    return nil
end

local function destroy_shadow_later(zone, shadow)
    timer.scheduleFunction(function()
        pcall(function()
            if shadow.group and shadow.group:IsAlive() then
                shadow.group:Destroy(false)
            end
        end)
        if zone.shadows[shadow.name] then
            zone.shadows[shadow.name] = nil
            zone.shadow_count = math.max(0, zone.shadow_count - 1)
        end
        return nil
    end, {}, timer.getTime() + SHADOW_DESPAWN_S)
end

local function stand_down(zone, shadow)
    if shadow.stood_down or shadow.escalated then
        return
    end
    shadow.stood_down = true
    pcall(function()
        local airbase = AIRBASE:FindByName(zone.field)
        if airbase then
            local c = airbase:GetCoordinate()
            shadow.group:RouteToVec3({ x = c.x, y = (c.y or 0) + SHADOW_AGL_M, z = c.z }, 200)
        end
    end)
    destroy_shadow_later(zone, shadow)
    log("shadow " .. shadow.name .. " standing down")
end

-- The SAM wake: clone the battery on the escalating intruder's opposing side. Alarm
-- state and ROE come with the fresh spawn; never touch radar emissions.
local function wake_sam(zone, intruder_side)
    if zone.sam_spawned or not zone.sam_template then
        return
    end
    zone.sam_spawned = true
    local ok, err = pcall(function()
        if not zone.sam_spawner then
            zone.sam_spawner = SPAWN:NewWithAlias(
                zone.sam_template, "NEUTRAL SAM " .. zone.country)
        end
        local sp = zone.sam_spawner
        local country = clone_country(zone, intruder_side)
        if country and sp.InitCountry then
            sp:InitCountry(country)
        end
        if sp.InitCoalition then
            sp:InitCoalition(opposing(intruder_side))
        end
        sp:Spawn()
        log("SAM battery awake at " .. zone.field)
    end)
    if not ok then
        zone.sam_spawned = false
        log("SAM wake error: " .. tostring(err))
    end
end

local function escalate(state, intruder_group)
    if state.escalated or not state.is_player then
        return
    end
    state.escalated = true
    local zone = zones[state.zone]
    announce(intruder_group, string.format(
        "%s AIR FORCE: You were warned. %s fighters are ENGAGING.",
        string.upper(zone.country), zone.country))
    local shadow = shadow_for(state.name)
    if shadow then
        shadow.escalated = true
        pcall(function()
            shadow.group:OptionROEWeaponFree()
        end)
        -- The §61 shape: a hard AttackGroup task on the raw controller,
        -- re-set by the vector loop only when the target changes.
        pcall(function()
            local sg = Group.getByName(shadow.name)
            local tgt = Group.getByName(state.name)
            if sg and tgt then
                shadow.last_target = tgt:getID()
                sg:getController():setTask({
                    id = "AttackGroup",
                    params = { groupId = tgt:getID() },
                })
            end
        end)
    end
    wake_sam(zone, state.side)
    log("ESCALATED on " .. state.name)
end

---------------------------------------------------------------------------------------------------
-- Vector loop: pre-escalation shadows chase a point beside the intruder; escalated
-- shadows get their attack task refreshed (the §61 pattern -- a dead task never sticks).
---------------------------------------------------------------------------------------------------
vector_tick = function()
    for _, zone in ipairs(zones) do
        for _, shadow in pairs(zone.shadows) do
            if not shadow.stood_down then
                pcall(function()
                    local intruder = Group.getByName(shadow.intruder)
                    local lead = lead_unit(intruder)
                    if not lead then
                        stand_down(zone, shadow)
                        return
                    end
                    if shadow.escalated then
                        -- Re-set only when the target id changed (the §61 rule:
                        -- a repeated identical setTask resets the AI's attack run).
                        local tid = intruder:getID()
                        if tid and tid ~= shadow.last_target then
                            shadow.last_target = tid
                            local sg = Group.getByName(shadow.name)
                            if sg then
                                sg:getController():setTask({
                                    id = "AttackGroup",
                                    params = { groupId = tid },
                                })
                            end
                        end
                        return
                    end
                    local p = lead:getPoint()
                    -- Offset abeam, never the exact point: a co-located waypoint
                    -- reads as a collision course to the AI.
                    shadow.group:RouteToVec3(
                        { x = p.x + 1200, y = p.y, z = p.z + 1200 }, 250)
                end)
            end
        end
    end
    return timer.getTime() + VECTOR_INTERVAL_S
end

local function start_vector_loop()
    if not vector_loop_running then
        vector_loop_running = true
        timer.scheduleFunction(function()
            return vector_tick()
        end, {}, timer.getTime() + 5)
    end
end

---------------------------------------------------------------------------------------------------
-- The border watch.
---------------------------------------------------------------------------------------------------
local function warn(state, intruder_group)
    state.warned = true
    local zone = zones[state.zone]
    if state.is_player then
        announce(intruder_group, string.format(
            "%s AIR FORCE: You are violating %s airspace below %d ft. "
                .. "Exit immediately or you will be engaged.",
            string.upper(zone.country), zone.country, zone.floor_ft))
    end
    local zi = state.zone
    local shadow = spawn_shadow(zone, zi, state.name, state.side)
    if shadow then
        start_vector_loop()
    end
end

local function scan_group(group, side, now)
    local lead = lead_unit(group)
    if not lead then
        return
    end
    local in_air = true
    pcall(function()
        in_air = lead:inAir()
    end)
    if not in_air then
        return
    end
    local name = group:getName() or ""
    if string.find(name, "NEUTRAL AF", 1, true) or string.find(name, "NEUTRAL SAM", 1, true) then
        return
    end
    local p = lead:getPoint()
    local state = intruders[name]
    for zi, zone in ipairs(zones) do
        if p.y < zone.floor_m and in_bbox(zone, p.x, p.z) and in_polygon(zone, p.x, p.z) then
            if not state then
                state = {
                    name = name,
                    zone = zi,
                    side = side,
                    dwell = 0,
                    warned = false,
                    escalated = false,
                    is_player = false,
                    last_inside = now,
                }
                intruders[name] = state
            end
            state.zone = zi
            state.dwell = state.dwell + SCAN_INTERVAL_S
            state.last_inside = now
            state.is_player = is_player_group(group)
            if not state.warned and state.dwell >= WARN_DWELL_S then
                warn(state, group)
            end
            -- Players only, by DM call: AI intruders are shadowed, never engaged.
            if state.is_player and not state.escalated and state.dwell >= ENGAGE_DWELL_S then
                escalate(state, group)
            end
            return
        end
    end
    -- Outside every zone: pre-escalation states cool off and stand their shadow down.
    if state and not state.escalated and (now - state.last_inside) > EXIT_GRACE_S then
        local zone = zones[state.zone]
        local shadow = shadow_for(name)
        if shadow then
            stand_down(zone, shadow)
        end
        intruders[name] = nil
    end
end

local function scan()
    local now = timer.getTime()
    for _, side in ipairs({ coalition.side.RED, coalition.side.BLUE }) do
        for _, category in ipairs({ Group.Category.AIRPLANE, Group.Category.HELICOPTER }) do
            pcall(function()
                for _, group in ipairs(coalition.getGroups(side, category) or {}) do
                    pcall(function()
                        scan_group(group, side, now)
                    end)
                end
            end)
        end
    end
    return now + SCAN_INTERVAL_S
end

---------------------------------------------------------------------------------------------------
-- Hostile-act escalation: a weapon released inside the border, or fire on the shadower.
---------------------------------------------------------------------------------------------------
local event_handler = {}
function event_handler:onEvent(event)
    pcall(function()
        if not event or not event.initiator then
            return
        end
        if event.id == world.event.S_EVENT_SHOT then
            local grp = event.initiator.getGroup and event.initiator:getGroup()
            if not grp then
                return
            end
            local state = intruders[grp:getName() or ""]
            if state and state.warned and not state.escalated and state.is_player then
                escalate(state, grp)
            end
        elseif event.id == world.event.S_EVENT_HIT then
            local target = event.target
            if not target or not target.getGroup then
                return
            end
            local tgroup = target:getGroup()
            local tname = tgroup and tgroup:getName() or ""
            if not string.find(tname, "NEUTRAL AF", 1, true) then
                return
            end
            local grp = event.initiator.getGroup and event.initiator:getGroup()
            if not grp then
                return
            end
            local state = intruders[grp:getName() or ""]
            if state and not state.escalated and state.is_player then
                escalate(state, grp)
            end
        end
    end)
end

---------------------------------------------------------------------------------------------------
-- Start.
---------------------------------------------------------------------------------------------------
local ok, err = pcall(function()
    draw_borders()
    world.addEventHandler(event_handler)
    timer.scheduleFunction(function()
        return scan()
    end, {}, timer.getTime() + SCAN_INTERVAL_S)
    log(string.format(
        "watching %d neutral border zone(s); warn %ds, engage %ds",
        #zones, WARN_DWELL_S, ENGAGE_DWELL_S))
end)
if not ok then
    env.error("NEUTRALBORDER|: setup error: " .. tostring(err))
end
