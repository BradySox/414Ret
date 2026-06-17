-- SCAR scenario bridge (414th) — integration skeleton.
--
-- Reads dcsRetribution.Scar.taskings (emitted by the Retribution generator from
-- the ScarTasking model), and for each tasking proves the end-to-end loop:
--   spawn a placeholder HVT  ->  route it to a no-strike destination  ->
--   pass (HVT destroyed) / fail (HVT reaches destination)  ->  write the
--   outcome into the global scar_results table the base plugin serializes into
--   state.json, which Retribution reads back in the debrief.
--
-- This is deliberately minimal: ONE vanilla truck per area, no decoys/clutter/
-- threat/signature and no scoring. Those are later increments (see
-- docs/dev/design/414th-scar-task-spec.md). MOOSE/mist are loaded by the base
-- plugin before this runs. Everything is defensive so a malformed tasking
-- degrades to a logged warning instead of breaking the mission.

local SCAR_CHECK_INTERVAL = 10 -- seconds between pass/fail checks

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

-- Active areas we are watching: each is {id, groupName, destX, destY, radius, done}.
local scar_areas = {}

local function spawn_hvt(tasking)
    local group_name = "SCAR-HVT-" .. tostring(tasking.taskingId)
    local spawn_x = scar_num(tasking.hvtSpawnX)
    local spawn_y = scar_num(tasking.hvtSpawnY)
    local dest_x = scar_num(tasking.hvtDestX)
    local dest_y = scar_num(tasking.hvtDestY)
    local country_id = scar_num(tasking.hvtCountryId)
    local hvt_type = tasking.hvtType or "Ural-375"
    if not (spawn_x and spawn_y and dest_x and dest_y and country_id) then
        scar_log("skipping tasking " .. tostring(tasking.taskingId) ..
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
        scar_log("mist.dynAdd failed for " .. group_name .. ": " ..
            tostring(spawned))
        return nil
    end
    return spawned.name or group_name
end

local function mark_result(area, status)
    area.done = true
    scar_results[area.id] = { status = status }
    dirty_state = true
    scar_log("area " .. tostring(area.id) .. " -> " .. status)
end

local function hvt_group_dead(group_name)
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

local function hvt_in_fail_zone(area)
    local group = Group.getByName(area.groupName)
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
            if hvt_group_dead(area.groupName) then
                mark_result(area, "success")
            elseif hvt_in_fail_zone(area) then
                mark_result(area, "failed")
            end
        end
    end
end

local function scar_init()
    if not (dcsRetribution and dcsRetribution.Scar and dcsRetribution.Scar.taskings) then
        scar_log("no dcsRetribution.Scar.taskings table; nothing to do")
        return
    end

    scar_results = scar_results or {}
    local count = 0
    for _, tasking in pairs(dcsRetribution.Scar.taskings) do
        local group_name = spawn_hvt(tasking)
        if group_name then
            local area = {
                id = tostring(tasking.taskingId),
                groupName = group_name,
                destX = scar_num(tasking.hvtDestX, 0),
                destY = scar_num(tasking.hvtDestY, 0),
                radius = scar_num(tasking.failZoneRadius, 500),
                done = false,
            }
            table.insert(scar_areas, area)
            scar_results[area.id] = { status = "active" }
            dirty_state = true
            count = count + 1
        end
    end

    if count == 0 then
        scar_log("no SCAR areas spawned")
        return
    end

    scar_log("initialized " .. count .. " SCAR area(s); watching every " ..
        SCAR_CHECK_INTERVAL .. "s")
    mist.scheduleFunction(scar_check, {}, timer.getTime() + SCAR_CHECK_INTERVAL,
        SCAR_CHECK_INTERVAL)
end

local ok, err = pcall(scar_init)
if not ok then
    scar_log("initialization error: " .. tostring(err))
end
