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
--   * variant "armor"   — the target IS a real armor group. It's static until
--                         go_live, then bugs out toward the city. success = the
--                         group destroyed; fail = it reaches the city or the
--                         window expires. (BAI stays the AI/auto-planner task.)
--   * variant "missile" — the target IS a real SCUD site that RACES from its
--                         location to a firing position and launches on arrival.
--                         success = killed first; fail = it reaches the firing
--                         position (or the window ends) and fires at its city.
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
-- Start moving this long BEFORE the flight's TOT so the target is already on the
-- move when the player arrives (in-game feedback: "doing more for longer"). The
-- fail deadline still anchors to go_live + window. Keep in sync with the Python
-- SCAR_START_LEAD_S (used for speed pacing).
local SCAR_START_LEAD = 600

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

-- Phase 2a: F10 cue for the SOF ambush point (only when a team is set).
local function mark_sof(area, side)
    if area.sofX and area.sofRadius and area.sofRadius > 0 then
        pcall(trigger.action.markToCoalition, next_mark_id(),
            "SOF team in position — the commander is CAPTURED if he reaches here",
            { x = area.sofX, y = 0, z = area.sofY }, side, true)
    end
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
    mark_sof(area, side)
end

local function brief_missile(area)
    local side = scar_side(area)
    local text = "SCAR INTEL (" .. area.id .. "):\n" ..
        "Mobile SCUD racing to its firing position. Destroy it BEFORE it gets " ..
        "there and launches."
    pcall(trigger.action.outTextForCoalition, side, text, 30)
    pcall(trigger.action.markToCoalition, next_mark_id(),
        "SCUD firing position — kill it before it arrives",
        { x = area.destX, y = 0, z = area.destY }, side, true)

    local group = Group.getByName(area.groups[1])
    if group == nil then
        return
    end
    local ok, unit = pcall(function()
        return group:getUnit(1)
    end)
    if ok and unit ~= nil then
        pcall(trigger.action.markToCoalition, next_mark_id(),
            "SCUD launcher — on the move", unit:getPoint(), side, true)
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
-- Phase 2a SOF ambush: a stationary friendly team dropped on the HVT's flee route.
-- If the un-killed command vehicle reaches them, the commander is CAPTURED.
local SCAR_SOF_UNIT = "Soldier M4" -- dynAdd uses the model for any country
local SCAR_SOF_COUNT = 4

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

-- Phase 2a: drop a stationary friendly SOF team at the ambush point (area.sofX/Y).
-- Spawned at go_live alongside the picture; capture is detected in scar_check.
local function spawn_sof(area)
    if not (area.sofX and area.sofRadius and area.sofRadius > 0) then
        return
    end
    local group_name = "SCAR-" .. tostring(area.id) .. "-sof"
    -- The bought SOF unit's DCS type (Phase 2c); fall back to the default model.
    local unit_type = area.sofUnitType
    if unit_type == nil or unit_type == "" then
        unit_type = SCAR_SOF_UNIT
    end
    local units = {}
    for i = 1, SCAR_SOF_COUNT do
        units[i] = {
            ["type"] = unit_type,
            ["name"] = group_name .. "-" .. i,
            ["x"] = area.sofX + (i - 1) * 5,
            ["y"] = area.sofY,
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
        ["country"] = area.sofCountryId,
        ["units"] = units,
        ["route"] = {
            ["points"] = {
                [1] = {
                    ["x"] = area.sofX,
                    ["y"] = area.sofY,
                    ["type"] = "Turning Point",
                    ["action"] = "Off Road",
                    ["speed"] = 0,
                },
            },
        },
    }
    local ok, spawned = pcall(mist.dynAdd, group_data)
    if not ok or not spawned then
        scar_log("SOF mist.dynAdd failed for " .. group_name .. ": " .. tostring(spawned))
        return
    end
    area.sofGroup = spawned.name or group_name
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

-- Phase 2a: has the HVT command vehicle (riding with the lead group) reached the
-- waiting SOF team? Uses the same lead-unit position as the fail-zone check.
local function hvt_in_sof_zone(area)
    if not (area.sofX and area.sofRadius and area.sofRadius > 0) then
        return false
    end
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
    local pos = unit:getPoint()
    local dx = pos.x - area.sofX
    local dz = pos.z - area.sofY
    return (dx * dx + dz * dz) <= (area.sofRadius * area.sofRadius)
end

-- The HVT command vehicle slips into the city (despawns) on arrival. Scans every
-- tracked group: the spawn variant carries it inside the HVT convoy, the armor
-- variant as a co-located command group appended to area.groups.
local function despawn_command(area)
    if not area.commandType or area.commandType == "" then
        return
    end
    for _, gname in ipairs(area.groups) do
        local group = Group.getByName(gname)
        if group ~= nil then
            local ok, units = pcall(function()
                return group:getUnits()
            end)
            if ok and units ~= nil then
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
        end
    end
end

-- A SCUD reaching its firing position launches at its target city = the failure
-- (a missile now flies at civilians/allies). Make it actually fire.
local function launch_missile(area)
    for _, name in ipairs(area.groups) do
        local group = Group.getByName(name)
        if group ~= nil then
            local ok, ctrl = pcall(function()
                return group:getController()
            end)
            if ok and ctrl then
                pcall(function()
                    ctrl:setOption(AI.Option.Ground.id.ROE,
                        AI.Option.Ground.val.ROE.OPEN_FIRE)
                end)
                pcall(function()
                    ctrl:pushTask({
                        id = "FireAtPoint",
                        params = {
                            point = { x = area.fireTargetX, y = area.fireTargetY },
                            radius = 100,
                            expendQty = 1,
                            expendQtyEnabled = true,
                        },
                    })
                end)
            end
        end
    end
end

local function scar_check()
    for _, area in ipairs(scar_areas) do
        if not area.done then
            local timed_out = area.deadline and timer.getTime() >= area.deadline
            -- Bound real groups (armor/missile) exist from mission start but are
            -- static until they start moving (go_live - lead). Don't run the
            -- arrival/fail check before then, or a target that spawns near its
            -- dest fails before the player's window even opens. (The spawn variant
            -- has no liveAt -- its HVT only exists once spawned at go_live.)
            local live = (area.liveAt == nil) or (timer.getTime() >= area.liveAt)
            if all_groups_dead(area) then
                mark_result(area, "success")
            elseif area.variant == "missile" then
                -- Reached its firing position (or out of time): it launches.
                if (live and hvt_in_fail_zone(area)) or timed_out then
                    launch_missile(area)
                    mark_result(area, "launched")
                end
            else
                if live and hvt_in_sof_zone(area) then
                    -- SOF ambush (Phase 2a): the commander is taken alive before he
                    -- reaches the city. Despawn the command vehicle as captured.
                    despawn_command(area)
                    mark_result(area, "captured")
                elseif live and hvt_in_fail_zone(area) then
                    -- Reached the city: the command vehicle escapes into it.
                    despawn_command(area)
                    mark_result(area, "failed")
                elseif timed_out then
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

-- Order a real ground group to drive from its current position to (dest_x,
-- dest_y) at the given speed (armor flees to the city; a SCUD races to its
-- firing position). Uses mist.goRoute, which builds a valid ground route — a
-- hand-rolled setTask was not reliably moving real bound groups in-game.
local function set_group_route(group_name, dest_x, dest_y, speed)
    local group = Group.getByName(group_name)
    if group == nil then
        return
    end
    local oku, unit = pcall(function()
        return group:getUnit(1)
    end)
    if not oku or unit == nil then
        return
    end
    local pos = unit:getPoint() -- {x = north, y = alt, z = east}
    local ok, err = pcall(function()
        local wp1 = mist.ground.buildWP({ x = pos.x, y = pos.z }, "off road", speed)
        local wp2 = mist.ground.buildWP({ x = dest_x, y = dest_y }, "off road", speed)
        mist.goRoute(group_name, { wp1, wp2 })
    end)
    if not ok then
        scar_log("set_group_route failed for " .. group_name .. ": " .. tostring(err))
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
                -- Started SCAR_START_LEAD early, so add it back: deadline still
                -- lands at go_live + window (the player's window from TOT).
                deadline = timer.getTime() + window + SCAR_START_LEAD,
                -- Phase 2a SOF ambush (set only when scar_command_post_intel is on).
                sofX = scar_num(tasking.sofX),
                sofY = scar_num(tasking.sofY),
                sofRadius = scar_num(tasking.sofRadius),
                sofCountryId = scar_num(tasking.sofCountryId),
                sofUnitType = tostring(tasking.sofUnitType or ""),
            }
        end
    end
    if hvt_area then
        table.insert(scar_areas, hvt_area)
        spawn_sof(hvt_area)
        brief_spawn(hvt_area, hvt_convoy)
        scar_log("area " .. hvt_area.id .. " live; window " ..
            math.floor(window) .. "s")
    else
        scar_log("spawn tasking " .. tostring(tasking.taskingId) ..
            ": no HVT convoy spawned")
    end
end

-- Missile variant: a real SCUD site that RACES from its location to a firing
-- position and launches on arrival. Held on WEAPON_HOLD so it can't fire en
-- route; the player must kill it before it reaches the firing position (or the
-- window expires), at which point it launches (fail). Registered at init so an
-- early kill counts; it starts moving at go_live.
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
        destX = scar_num(tasking.destX, 0),
        destY = scar_num(tasking.destY, 0),
        radius = scar_num(tasking.failZoneRadius, 2000),
        fireTargetX = scar_num(tasking.fireTargetX, 0),
        fireTargetY = scar_num(tasking.fireTargetY, 0),
        deadline = timer.getTime() + go_live + window,
        -- Static until it starts racing; only then can it "arrive" and fire.
        liveAt = timer.getTime() + math.max(0, go_live - SCAR_START_LEAD),
    }
    for _, name in ipairs(groups) do
        missile_group_index[name] = area
        set_group_roe(name, AI.Option.Ground.val.ROE.WEAPON_HOLD)
    end
    table.insert(scar_areas, area)
    brief_missile(area)
    local speed = scar_num(tasking.fleeSpeed, 5)
    mist.scheduleFunction(function()
        for _, name in ipairs(area.groups) do
            set_group_route(name, area.destX, area.destY, speed)
        end
    end, {}, timer.getTime() + math.max(0, go_live - SCAR_START_LEAD))
    return true
end

-- The real armor group's live composition, e.g. "3x T-55 + 1x command vehicle".
local function live_signature(group_name)
    local group = Group.getByName(group_name)
    if group == nil then
        return "armor"
    end
    local ok, units = pcall(function()
        return group:getUnits()
    end)
    if not ok or units == nil then
        return "armor"
    end
    local counts, order = {}, {}
    for _, unit in ipairs(units) do
        local okt, type_name = pcall(function()
            return unit:getTypeName()
        end)
        if okt and type_name then
            if counts[type_name] == nil then
                table.insert(order, type_name)
            end
            counts[type_name] = (counts[type_name] or 0) + 1
        end
    end
    local parts = {}
    for _, type_name in ipairs(order) do
        table.insert(parts, counts[type_name] .. "x " .. friendly_name(type_name))
    end
    if #parts == 0 then
        return "armor"
    end
    return table.concat(parts, " + ")
end

local function brief_armor(area)
    local side = scar_side(area)
    local sig = live_signature(area.groups[1])
    local text = "SCAR INTEL (" .. area.id .. "):\n" ..
        "Target signature: " .. sig .. " + 1x command vehicle (the HVT)\n" ..
        "The real column has a command vehicle riding with it. Decoys share SOME " ..
        "elements — some even a command vehicle — so match the FULL signature and " ..
        "destroy it (command vehicle included) before it reaches the city."
    pcall(trigger.action.outTextForCoalition, side, text, 30)
    local group = Group.getByName(area.groups[1])
    if group ~= nil then
        local ok, unit = pcall(function()
            return group:getUnit(1)
        end)
        if ok and unit ~= nil then
            pcall(trigger.action.markToCoalition, next_mark_id(),
                "SCAR target — " .. sig, unit:getPoint(), side, true)
        end
    end
    pcall(trigger.action.markToCoalition, next_mark_id(),
        "SCAR no-strike zone — armor safe haven", { x = area.destX, y = 0, z = area.destY },
        side, true)
    mark_sof(area, side)
end

-- Armor variant: bind the REAL armor group. It's static until go_live, then it
-- flees to the city; success = killed, fail = reaches the city (its safe haven)
-- or the window expires. Registered at init so an early kill still counts.
local function activate_armor_area(tasking, go_live, window)
    local groups = tasking.targetGroups or {}
    if type(groups) ~= "table" or #groups == 0 then
        scar_log("skipping armor tasking " .. tostring(tasking.taskingId) ..
            ": no target groups")
        return false
    end
    local area = {
        id = tostring(tasking.taskingId),
        variant = "armor",
        coalition = tostring(tasking.coalition or "blue"),
        groups = groups,
        done = false,
        destX = scar_num(tasking.destX, 0),
        destY = scar_num(tasking.destY, 0),
        radius = scar_num(tasking.failZoneRadius, 2000),
        -- The command vehicle riding with the real column: tracked (must die for
        -- success) and the unit that despawns ("escapes") on reaching the city.
        commandType = tostring(tasking.commandType or ""),
        deadline = timer.getTime() + go_live + window,
        -- Static until it bugs out; only then can it "reach" the city = fail.
        liveAt = timer.getTime() + math.max(0, go_live - SCAR_START_LEAD),
        -- Phase 2a SOF ambush (set only when scar_command_post_intel is on).
        sofX = scar_num(tasking.sofX),
        sofY = scar_num(tasking.sofY),
        sofRadius = scar_num(tasking.sofRadius),
        sofCountryId = scar_num(tasking.sofCountryId),
        sofUnitType = tostring(tasking.sofUnitType or ""),
    }
    table.insert(scar_areas, area)
    brief_armor(area)
    local speed = scar_num(tasking.fleeSpeed, 5)
    local country_id = scar_num(tasking.hvtCountryId)
    local convoys = tasking.convoys or {}
    mist.scheduleFunction(function()
        -- The real armor bugs out...
        for _, name in ipairs(area.groups) do
            set_group_route(name, area.destX, area.destY, speed)
        end
        -- ...the SOF team lands ahead on its route (Phase 2a ambush)...
        spawn_sof(area)
        -- ...and the decoy/clutter columns spawn and flee alongside it (untracked),
        -- plus the command vehicle, which IS tracked: append it to area.groups so
        -- success requires killing it and it's found by despawn_command on arrival.
        local spawn_index = 0
        for _, convoy in pairs(convoys) do
            spawn_index = spawn_index + 1
            local spawned = spawn_convoy(tasking.taskingId, convoy, country_id, spawn_index)
            if convoy.role == "command" and spawned ~= nil then
                table.insert(area.groups, spawned)
            end
        end
    end, {}, timer.getTime() + math.max(0, go_live - SCAR_START_LEAD))
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
        elseif variant == "armor" then
            if activate_armor_area(tasking, go_live, window) then
                count = count + 1
            end
        else
            -- Spawn at the flight's TOT so the convoy isn't long gone before the
            -- player arrives. The closure captures this tasking.
            local t = tasking
            mist.scheduleFunction(function()
                pcall(activate_spawn_area, t, window)
            end, {}, timer.getTime() + math.max(0, go_live - SCAR_START_LEAD))
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
