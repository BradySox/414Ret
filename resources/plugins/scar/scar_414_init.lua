-- SCAR scenario bridge (414th) — integration skeleton.
--
-- Reads dcsRetribution.Scar.taskings (emitted by the Retribution generator from
-- the ScarTasking model) and runs one of two paths per tasking:
--   * variant "spawn"   — AI convoys are rare, so the generator spawns a moving
--                         HVT (placeholder: one vanilla truck) and routes it to
--                         a no-strike destination. success = HVT destroyed;
--                         fail  = HVT reaches the destination zone.
--   * variant "missile" — the target IS a real surface-to-surface (SCUD) site;
--                         watch it, no spawn. success = site destroyed;
--                         fail  = it launches (any weapon release by a site unit).
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

-- Spawn one HVT vehicle and route it to the no-strike destination. Returns the
-- spawned group name or nil.
local function spawn_hvt(tasking)
    local group_name = "SCAR-HVT-" .. tostring(tasking.taskingId)
    local spawn_x = scar_num(tasking.hvtSpawnX)
    local spawn_y = scar_num(tasking.hvtSpawnY)
    local dest_x = scar_num(tasking.hvtDestX)
    local dest_y = scar_num(tasking.hvtDestY)
    local country_id = scar_num(tasking.hvtCountryId)
    local hvt_type = tasking.hvtType or "Ural-375"
    if not (spawn_x and spawn_y and dest_x and dest_y and country_id) then
        scar_log("skipping spawn tasking " .. tostring(tasking.taskingId) ..
            ": incomplete coordinates")
        return nil
    end

    local group_data = {
        ["visible"] = false,
        ["hidden"] = false,
        ["name"] = group_name,
        ["task"] = {},
        ["category"] = Group.Category.GROUND,
        ["country"] = country_id,
        ["units"] = {
            [1] = {
                ["type"] = hvt_type,
                ["name"] = group_name .. "-1",
                ["x"] = spawn_x,
                ["y"] = spawn_y,
                ["heading"] = 0,
                ["skill"] = "Average",
                ["playerCanDrive"] = false,
            },
        },
        ["route"] = {
            ["points"] = {
                [1] = {
                    ["x"] = spawn_x,
                    ["y"] = spawn_y,
                    ["type"] = "Turning Point",
                    ["action"] = "Off Road",
                    ["speed"] = 20,
                },
                [2] = {
                    ["x"] = dest_x,
                    ["y"] = dest_y,
                    ["type"] = "Turning Point",
                    ["action"] = "Off Road",
                    ["speed"] = 20,
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

local function scar_check()
    for _, area in ipairs(scar_areas) do
        if not area.done then
            if all_groups_dead(area) then
                mark_result(area, "success")
            elseif area.variant ~= "missile" and hvt_in_fail_zone(area) then
                mark_result(area, "failed")
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

local function register_area(area)
    table.insert(scar_areas, area)
    scar_results[area.id] = { status = "active" }
    dirty_state = true
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
        if variant == "missile" then
            local groups = tasking.targetGroups or {}
            if type(groups) == "table" and #groups > 0 then
                local area = {
                    id = tostring(tasking.taskingId),
                    variant = "missile",
                    groups = groups,
                    done = false,
                }
                for _, name in ipairs(groups) do
                    missile_group_index[name] = area
                end
                register_area(area)
                count = count + 1
            else
                scar_log("skipping missile tasking " .. tostring(tasking.taskingId) ..
                    ": no target groups")
            end
        else
            local group_name = spawn_hvt(tasking)
            if group_name then
                register_area({
                    id = tostring(tasking.taskingId),
                    variant = "spawn",
                    groups = { group_name },
                    done = false,
                    destX = scar_num(tasking.hvtDestX, 0),
                    destY = scar_num(tasking.hvtDestY, 0),
                    radius = scar_num(tasking.failZoneRadius, 500),
                })
                count = count + 1
            end
        end
    end

    if count == 0 then
        scar_log("no SCAR areas registered")
        return
    end

    world.addEventHandler(scar_event_handler)
    scar_log("watching " .. count .. " SCAR area(s) every " ..
        SCAR_CHECK_INTERVAL .. "s")
    mist.scheduleFunction(scar_check, {}, timer.getTime() + SCAR_CHECK_INTERVAL,
        SCAR_CHECK_INTERVAL)
end

local ok, err = pcall(scar_init)
if not ok then
    scar_log("initialization error: " .. tostring(err))
end
