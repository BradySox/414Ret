-- SCAR scenario bridge (414th) — integration skeleton.
--
-- Reads dcsRetribution.Scar.taskings (emitted by the Retribution generator from
-- the ScarTasking model) and runs one of two paths per tasking:
--   * variant "spawn"   — AI convoys are rare, so the generator spawns the whole
--                         ground picture (an HVT signature convoy + decoy convoys
--                         + plain-truck clutter) and routes the HVT toward a city
--                         (the nearest enemy control point). Only the HVT is
--                         tracked: success = HVT destroyed; fail = it reaches the
--                         city (its command vehicle despawns there) or the window
--                         expires. Decoys/clutter are the discrimination puzzle.
--   * variant "missile" — the target IS a real surface-to-surface (SCUD) site;
--                         watch it, no spawn. success = site destroyed;
--                         fail  = it launches (any weapon release by a site unit).
--
-- TIMING: each scenario is anchored to the SCAR flight's TOT (goLive, seconds
-- from mission start) so it doesn't resolve before the player can be on station.
-- The spawn picture appears at goLive; the SCUD is held on WEAPON_HOLD until
-- goLive+window. The player then has `window` seconds to find + kill the HVT.
--
-- Outcomes go into the global scar_results table the base plugin serializes into
-- state.json, which Retribution reads back in the debrief. Skeleton: no scoring
-- yet (see docs/dev/design/414th-scar-task-spec.md). MOOSE/mist are loaded by
-- the base plugin first. Everything is defensive so a malformed tasking degrades
-- to a logged warning instead of breaking the mission.

local SCAR_CHECK_INTERVAL = 10 -- seconds between kill/arrival checks

local function scar_log(msg)
    if logger then
        logger:info("[SCAR] " .. msg)
    else
        env.info("[SCAR] " .. msg)
    end
end

local function scar_num(value, fallback)
    return tonumber(value) or fallback
end

-- Active areas: {id, variant, groups={names}, done, destX, destY, radius}.
local scar_areas = {}
-- group name -> area, for missile launch detection via the shot event.
local missile_group_index = {}

-- ---- Briefing / F10 map cues (spec §7, R11) --------------------------------------
local scar_mark_id = 88000 -- high base to avoid colliding with other plugins' marks
local function next_mark_id()
    scar_mark_id = scar_mark_id + 1
    return scar_mark_id
end

-- Plain-language names for the signature brief (fall back to the raw type id).
local SCAR_UNIT_NAMES = {
    ["Strela-1 9P31"] = "SA-9",
    ["Ural-375 PBU"] = "command vehicle",
    ["Ural-375"] = "truck",
    ["ZSU-23-4 Shilka"] = "ZSU-23-4",
    ["ZU-23 Emplacement"] = "ZU-23",
}

local function friendly_name(unit_type)
    return SCAR_UNIT_NAMES[unit_type] or tostring(unit_type)
end

local function scar_side(area)
    if area.coalition == "red" then
        return coalition.side.RED
    end
    return coalition.side.BLUE
end

-- "1x SA-9 + 1x command vehicle + 2x truck" from a convoy's unit list.
local function signature_text(convoy)
    local counts, order = {}, {}
    for _, unit_type in ipairs(convoy.units or {}) do
        if counts[unit_type] == nil then
            table.insert(order, unit_type)
        end
        counts[unit_type] = (counts[unit_type] or 0) + 1
    end
    local parts = {}
    for _, unit_type in ipairs(order) do
        table.insert(parts, counts[unit_type] .. "x " .. friendly_name(unit_type))
    end
    return table.concat(parts, " + ")
end

local function brief_spawn(area, hvt_convoy)
    local side = scar_side(area)
    local sig = signature_text(hvt_convoy)
    local text = "SCAR INTEL (" .. area.id .. "):\n" ..
        "Target convoy signature: " .. sig .. "\n" ..
        "Decoys may share SOME but not ALL of these elements — do not prosecute a " ..
        "partial match.\nFind and destroy the full-signature convoy before it reaches " ..
        "its destination."
    pcall(trigger.action.outTextForCoalition, side, text, 30)

    local start_pt = {
        x = scar_num(hvt_convoy.spawnX, 0),
        y = 0,
        z = scar_num(hvt_convoy.spawnY, 0),
    }
    local dest_pt = { x = area.destX, y = 0, z = area.destY }
    pcall(trigger.action.markToCoalition, next_mark_id(),
        "SCAR target area — convoy: " .. sig, start_pt, side, true)
    pcall(trigger.action.markToCoalition, next_mark_id(),
        "SCAR no-strike zone — stop the convoy before here", dest_pt, side, true)
    -- Ingress axis (best-effort; non-fatal if the API rejects it).
    pcall(trigger.action.lineToAll, -1, next_mark_id(), start_pt, dest_pt,
        { 1, 0, 0, 0.6 }, 2, true)
end

local function brief_missile(area)
    local side = scar_side(area)
    local text = "SCAR INTEL (" .. area.id .. "):\n" ..
        "Surface-to-surface (SCUD) missile site. Destroy it BEFORE it launches."
    pcall(trigger.action.outTextForCoalition, side, text, 30)

    local group = Group.getByName(area.groups[1])
    if group == nil then
        return
    end
    local ok, unit = pcall(function()
        return group:getUnit(1)
    end)
    if ok and unit ~= nil then
        pcall(trigger.action.markToCoalition, next_mark_id(),
            "SCUD site — destroy before launch", unit:getPoint(), side, true)
    end
end

local function mark_result(area, status)
    if area.done then
        return
    end
    area.done = true
    scar_results[area.id] = { status = status }
    dirty_state = true
    scar_log("area " .. tostring(area.id) .. " (" .. area.variant .. ") -> " .. status)
end

local function group_dead(group_name)
    local group = Group.getByName(group_name)
    if group == nil then
        return true
    end
    local ok, size = pcall(function()
        return group:getSize()
    end)
    if not ok then
        return false
    end
    return (size or 0) <= 0
end

local function all_groups_dead(area)
    for _, name in ipairs(area.groups) do
        if not group_dead(name) then
            return false
        end
    end
    return true
end

-- Spawn one convoy group (HVT / decoy / clutter) and route it spawn -> dest.
-- Returns the spawned group name or nil.
local SCAR_UNIT_SPACING = 25 -- metres between units in a convoy line

local function spawn_convoy(tasking_id, convoy, country_id, index)
    -- index keeps the group name unique (several convoys share a role).
    local group_name = "SCAR-" .. tostring(tasking_id) .. "-" ..
        tostring(convoy.role) .. "-" .. tostring(index)
    local spawn_x = scar_num(convoy.spawnX)
    local spawn_y = scar_num(convoy.spawnY)
    local dest_x = scar_num(convoy.destX)
    local dest_y = scar_num(convoy.destY)
    local speed = scar_num(convoy.speed, 5)
    local types = convoy.units or {}
    if not (spawn_x and spawn_y and dest_x and dest_y) or #types == 0 then
        scar_log("skipping convoy " .. group_name .. ": incomplete data")
        return nil
    end

    local units = {}
    for i, unit_type in ipairs(types) do
        units[i] = {
            ["type"] = unit_type,
            ["name"] = group_name .. "-" .. i,
            ["x"] = spawn_x + (i - 1) * SCAR_UNIT_SPACING,
            ["y"] = spawn_y,
            ["heading"] = 0,
            ["skill"] = "Average",
            ["playerCanDrive"] = false,
        }
    end

    local group_data = {
        ["visible"] = false,
        ["hidden"] = false,
        ["name"] = group_name,
        ["task"] = {},
        ["category"] = Group.Category.GROUND,
        ["country"] = country_id,
        ["units"] = units,
        -- Speed is set by the generator: the HVT is paced to reach the city ~as
        -- the window expires; decoys/clutter just crawl as traffic.
        ["route"] = {
            ["points"] = {
                [1] = {
                    ["x"] = spawn_x,
                    ["y"] = spawn_y,
                    ["type"] = "Turning Point",
                    ["action"] = "Off Road",
                    ["speed"] = speed,
                },
                [2] = {
                    ["x"] = dest_x,
                    ["y"] = dest_y,
                    ["type"] = "Turning Point",
                    ["action"] = "Off Road",
                    ["speed"] = speed,
                },
            },
        },
    }

    local ok, spawned = pcall(mist.dynAdd, group_data)
    if not ok or not spawned then
        scar_log("mist.dynAdd failed for " .. group_name .. ": " .. tostring(spawned))
        return nil
    end
    return spawned.name or group_name
end

-- Spawn variant only: has the spawned HVT reached its no-strike destination?
local function hvt_in_fail_zone(area)
    local group = Group.getByName(area.groups[1])
    if group == nil then
        return false
    end
    local ok, unit = pcall(function()
        return group:getUnit(1)
    end)
    if not ok or unit == nil then
        return false
    end
    local pos = unit:getPoint() -- {x = north, y = alt, z = east}
    -- destX is Point.x (north), destY is Point.y (east) -> compare to z.
    local dx = pos.x - area.destX
    local dz = pos.z - area.destY
    return (dx * dx + dz * dz) <= (area.radius * area.radius)
end

-- The HVT command vehicle slips into the city (despawns) on arrival.
local function despawn_command(area)
    if not area.commandType or area.commandType == "" then
        return
    end
    local group = Group.getByName(area.groups[1])
    if group == nil then
        return
    end
    local ok, units = pcall(function()
        return group:getUnits()
    end)
    if not ok or units == nil then
        return
    end
    for _, unit in ipairs(units) do
        local okt, type_name = pcall(function()
            return unit:getTypeName()
        end)
        if okt and type_name == area.commandType then
            pcall(function()
                unit:destroy()
            end)
            return
        end
    end
end

local function scar_check()
    for _, area in ipairs(scar_areas) do
        if not area.done then
            if all_groups_dead(area) then
                mark_result(area, "success")
            elseif area.variant ~= "missile" then
                if hvt_in_fail_zone(area) then
                    -- Reached the city: the command vehicle escapes into it.
                    despawn_command(area)
                    mark_result(area, "failed")
                elseif area.deadline and timer.getTime() >= area.deadline then
                    -- Ran out of time; the convoy is still en route.
                    mark_result(area, "failed")
                end
            end
        end
    end
end

-- Missile launch = fail. Any weapon release by a unit in a watched missile site
-- group (these are surface-to-surface sites) counts.
local scar_event_handler = {}
function scar_event_handler:onEvent(event)
    if event == nil or event.id ~= world.event.S_EVENT_SHOT then
        return
    end
    if event.initiator == nil then
        return
    end
    local ok, group_name = pcall(function()
        return event.initiator:getGroup():getName()
    end)
    if not ok or group_name == nil then
        return
    end
    local area = missile_group_index[group_name]
    if area ~= nil and not area.done then
        mark_result(area, "launched")
    end
end

local function set_group_roe(group_name, roe_val)
    local group = Group.getByName(group_name)
    if group == nil then
        return
    end
    local ok, ctrl = pcall(function()
        return group:getController()
    end)
    if ok and ctrl then
        pcall(function()
            ctrl:setOption(AI.Option.Ground.id.ROE, roe_val)
        end)
    end
end

-- Spawn variant: runs at the flight's TOT (go_live). Spawns the whole ground
-- picture and starts the HVT's window. Only the HVT is tracked; decoys/clutter
-- are the discrimination puzzle (mis-ID scoring is a later increment).
local function activate_spawn_area(tasking, window)
    local country_id = scar_num(tasking.hvtCountryId)
    local hvt_area, hvt_convoy = nil, nil
    local spawn_index = 0
    for _, convoy in pairs(tasking.convoys or {}) do
        spawn_index = spawn_index + 1
        local group_name =
            spawn_convoy(tasking.taskingId, convoy, country_id, spawn_index)
        if group_name and tostring(convoy.role) == "hvt" then
            hvt_convoy = convoy
            hvt_area = {
                id = tostring(tasking.taskingId),
                variant = "spawn",
                coalition = tostring(tasking.coalition or "blue"),
                groups = { group_name },
                done = false,
                destX = scar_num(convoy.destX, 0),
                destY = scar_num(convoy.destY, 0),
                radius = scar_num(tasking.failZoneRadius, 500),
                commandType = tostring(tasking.commandType or ""),
                deadline = timer.getTime() + window,
            }
        end
    end
    if hvt_area then
        table.insert(scar_areas, hvt_area)
        brief_spawn(hvt_area, hvt_convoy)
        scar_log("area " .. hvt_area.id .. " live; window " ..
            math.floor(window) .. "s")
    else
        scar_log("spawn tasking " .. tostring(tasking.taskingId) ..
            ": no HVT convoy spawned")
    end
end

-- Missile variant: the site is a real unit, so it's held on WEAPON_HOLD from the
-- start (stops it firing before the player can get there) and only released to
-- fire after go_live + window, at which point an un-killed site launches (fail).
local function activate_missile_area(tasking, go_live, window)
    local groups = tasking.targetGroups or {}
    if type(groups) ~= "table" or #groups == 0 then
        scar_log("skipping missile tasking " .. tostring(tasking.taskingId) ..
            ": no target groups")
        return false
    end
    local area = {
        id = tostring(tasking.taskingId),
        variant = "missile",
        coalition = tostring(tasking.coalition or "blue"),
        groups = groups,
        done = false,
    }
    for _, name in ipairs(groups) do
        missile_group_index[name] = area
        set_group_roe(name, AI.Option.Ground.val.ROE.WEAPON_HOLD)
    end
    table.insert(scar_areas, area)
    brief_missile(area)
    mist.scheduleFunction(function()
        if not area.done then
            for _, name in ipairs(area.groups) do
                set_group_roe(name, AI.Option.Ground.val.ROE.OPEN_FIRE)
            end
            mark_result(area, "launched")
        end
    end, {}, timer.getTime() + go_live + window)
    return true
end

local function scar_init()
    if not (dcsRetribution and dcsRetribution.Scar and dcsRetribution.Scar.taskings) then
        scar_log("no dcsRetribution.Scar.taskings table; nothing to do")
        return
    end

    scar_results = scar_results or {}
    local count = 0
    for _, tasking in pairs(dcsRetribution.Scar.taskings) do
        local variant = tostring(tasking.variant or "spawn")
        local go_live = scar_num(tasking.goLive, 0)
        local window = scar_num(tasking.window, 1200)
        -- Seed the result now so a never-resolved area still reports as active.
        scar_results[tostring(tasking.taskingId)] = { status = "active" }
        dirty_state = true
        if variant == "missile" then
            if activate_missile_area(tasking, go_live, window) then
                count = count + 1
            end
        else
            -- Spawn at the flight's TOT so the convoy isn't long gone before the
            -- player arrives. The closure captures this tasking.
            local t = tasking
            mist.scheduleFunction(function()
                pcall(activate_spawn_area, t, window)
            end, {}, timer.getTime() + go_live)
            count = count + 1
        end
    end

    if count == 0 then
        scar_log("no SCAR areas registered")
        return
    end

    world.addEventHandler(scar_event_handler)
    scar_log("registered " .. count .. " SCAR area(s); check every " ..
        SCAR_CHECK_INTERVAL .. "s")
    mist.scheduleFunction(scar_check, {}, timer.getTime() + SCAR_CHECK_INTERVAL,
        SCAR_CHECK_INTERVAL)
end

local ok, err = pcall(scar_init)
if not ok then
    scar_log("initialization error: " .. tostring(err))
end
