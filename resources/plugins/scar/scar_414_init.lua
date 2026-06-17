-- SCAR scenario bridge (414th) — integration skeleton.
--
-- Reads dcsRetribution.Scar.taskings (emitted by the Retribution generator from
-- the ScarTasking model) and watches units the campaign ALREADY generates — no
-- spawning. Each tasking names the DCS group(s) of its target:
--   * variant "convoy"  — an enemy ground transfer. success = group destroyed.
--                         Surviving = the transfer completes (handled by the
--                         existing convoy-loss economy), so we just leave it
--                         unresolved ("active").
--   * variant "missile" — a surface-to-surface (SCUD) site. success = destroyed;
--                         fail = it launches (any weapon release by the site).
--
-- Outcomes go into the global scar_results table the base plugin serializes into
-- state.json, which Retribution reads back in the debrief. Skeleton: no scoring
-- yet (see docs/dev/design/414th-scar-task-spec.md). MOOSE/mist are loaded by
-- the base plugin first. Everything is defensive so a malformed tasking degrades
-- to a logged warning instead of breaking the mission.

local SCAR_CHECK_INTERVAL = 10 -- seconds between kill checks

local function scar_log(msg)
    if logger then
        logger:info("[SCAR] " .. msg)
    else
        env.info("[SCAR] " .. msg)
    end
end

-- Active areas we are watching: each is {id, variant, groups={names}, done}.
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

local function scar_check()
    for _, area in ipairs(scar_areas) do
        if not area.done and all_groups_dead(area) then
            mark_result(area, "success")
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

local function scar_init()
    if not (dcsRetribution and dcsRetribution.Scar and dcsRetribution.Scar.taskings) then
        scar_log("no dcsRetribution.Scar.taskings table; nothing to do")
        return
    end

    scar_results = scar_results or {}
    local count = 0
    for _, tasking in pairs(dcsRetribution.Scar.taskings) do
        local groups = tasking.targetGroups or {}
        if type(groups) == "table" and #groups > 0 then
            local area = {
                id = tostring(tasking.taskingId),
                variant = tostring(tasking.variant or "convoy"),
                groups = groups,
                done = false,
            }
            table.insert(scar_areas, area)
            scar_results[area.id] = { status = "active" }
            dirty_state = true
            if area.variant == "missile" then
                for _, name in ipairs(groups) do
                    missile_group_index[name] = area
                end
            end
            count = count + 1
        else
            scar_log("skipping tasking " .. tostring(tasking.taskingId) ..
                ": no target groups")
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
