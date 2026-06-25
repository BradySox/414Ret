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
--   * variant "armor"   — the target IS a real armor group. It bugs out toward the
--                         city at spawn (decoys + command vehicle spawn alongside
--                         it). success = the group destroyed; fail = it reaches the
--                         city or the window expires. (BAI stays the AI task.)
--   * variant "missile" — the target IS a real SCUD site that RACES from its
--                         location to a firing position and launches on arrival.
--                         success = killed first; fail = it reaches the firing
--                         position (or the window ends) and fires at its city.
--
-- TIMING (2026-06-21): the whole picture (HVT + command + decoys + clutter) spawns
-- PARKED at mission start, so the discrimination puzzle is present whenever the
-- player arrives. The columns only bug out once the strike package crosses the
-- PROXIMITY ring (SCAR_PROXIMITY_M); the fail clock starts from that approach
-- (deadline = activation + window). This means the target is moving as the player
-- shows up but can never be "long gone" if the jets are slow (A-10 feedback
-- 2026-06-20). It replaces both the old TOT anchor (goLive — MP doesn't fly a TOT,
-- so the target only moved "right as we fired Mavs") and the interim move-from-spawn
-- (which leaned on slow pacing as the only escape guard). goLive is still read for
-- reference but no longer gates anything. A kill before activation still counts.
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
-- Decoy/clutter group name -> area, so a kill on a wrong convoy can be charged
-- as a mis-ID (R7). Only decoy/clutter roles are registered; the HVT, command
-- vehicle, and threat (SAM) groups are legitimate kills and stay out of this map.
local misid_group_index = {}

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
            "SOF ambush point — airdrop your SOF team here; the commander is " ..
            "CAPTURED if he reaches it (a scripted team stands in if none is dropped)",
            { x = area.sofX, y = 0, z = area.sofY }, side, true)
    end
end

local function brief_spawn(area, hvt_convoy)
    local side = scar_side(area)
    local sig = signature_text(hvt_convoy)
    local text = "SCAR INTEL (" .. area.id .. "):\n" ..
        "Target convoy signature: " .. sig .. "\n" ..
        "It starts moving as you arrive in the search area. Decoys share SOME but " ..
        "not ALL of these elements — do not prosecute a partial match.\nFind and " ..
        "destroy the full-signature convoy before it reaches its destination."
    pcall(trigger.action.outTextForCoalition, side, text, 30)

    -- Mark the search AREA (the box of traffic), not the HVT itself: the convoy is
    -- one of several in here and already moving, so the player has to ID it.
    local center_pt = { x = area.centerX, y = 0, z = area.centerY }
    local dest_pt = { x = area.destX, y = 0, z = area.destY }
    pcall(trigger.action.markToCoalition, next_mark_id(),
        "SCAR search area — convoy: " .. sig .. " (on the move)", center_pt, side, true)
    pcall(trigger.action.markToCoalition, next_mark_id(),
        "SCAR no-strike zone — stop the convoy before here", dest_pt, side, true)
    -- Flee axis (best-effort; non-fatal if the API rejects it).
    pcall(trigger.action.lineToAll, -1, next_mark_id(), center_pt, dest_pt,
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
    -- Carry any mis-ID count recorded before the area resolved (mark_result
    -- replaces the whole entry table, so it would otherwise be lost).
    scar_results[area.id] = { status = status, misId = area.misId }
    dirty_state = true
    scar_log("area " .. tostring(area.id) .. " (" .. area.variant .. ") -> " .. status)
end

-- Charge a mis-ID: the prosecuting side destroyed one of this area's decoy/
-- clutter convoys (R7). Tracked on the area and mirrored onto its scar_results
-- entry (preserving status), so a count survives both an already-resolved area
-- and one that never resolves (seeded "active").
local function record_misid(area)
    area.misId = (area.misId or 0) + 1
    local entry = scar_results[area.id]
    if entry == nil then
        entry = { status = "active" }
        scar_results[area.id] = entry
    end
    entry.misId = area.misId
    dirty_state = true
    scar_log("area " .. tostring(area.id) .. ": mis-ID #" .. area.misId ..
        " (wrong convoy prosecuted)")
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
        -- Spawn PARKED (single waypoint): the picture is present from mission start
        -- so the discrimination puzzle exists, but nothing moves until the player
        -- package reaches the activation ring, when set_group_route sends it to its
        -- destination (proximity trigger — the convoy can't be "long gone").
        ["route"] = {
            ["points"] = {
                [1] = {
                    ["x"] = spawn_x,
                    ["y"] = spawn_y,
                    ["type"] = "Turning Point",
                    ["action"] = "Off Road",
                    ["speed"] = 0,
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

-- Phase 2c-2: detect a player-DELIVERED SOF team near the ambush point. The
-- insert is a C-130 airdrop, so the human flies the team in and CTLD-unloads it
-- at the marked point; if a friendly ground group (that isn't one of our own
-- SCAR spawns) is sitting near sofX/sofY when the HVT closes in, capture binds to
-- THAT group. Returns the group name, or nil if nothing was delivered.
local SCAR_SOF_DELIVERY_RADIUS = 2500 -- how near the ambush point a real drop counts

local function find_delivered_sof(area)
    if not (area.sofX and area.sofY) then
        return nil
    end
    local ok, groups = pcall(coalition.getGroups, scar_side(area),
        Group.Category.GROUND)
    if not ok or groups == nil then
        return nil
    end
    local best_name = nil
    local best_d2 = SCAR_SOF_DELIVERY_RADIUS * SCAR_SOF_DELIVERY_RADIUS
    for _, group in ipairs(groups) do
        local okn, gname = pcall(function()
            return group:getName()
        end)
        -- Skip our own scripted spawns (convoys / threats / scripted SOF); only a
        -- player/CTLD-delivered group counts as a real drop.
        if okn and gname ~= nil and string.sub(gname, 1, 5) ~= "SCAR-" then
            local okp, pos = pcall(function()
                return group:getUnit(1):getPoint() -- {x = north, y = alt, z = east}
            end)
            if okp and pos ~= nil then
                local dx = pos.x - area.sofX
                local dz = pos.z - area.sofY
                local d2 = dx * dx + dz * dz
                if d2 <= best_d2 then
                    best_name, best_d2 = gname, d2
                end
            end
        end
    end
    return best_name
end

-- Put a friendly SOF team at the ambush point (area.sofX/Y). Called lazily as the
-- HVT closes in (maybe_bind_sof). Hybrid (Phase 2c-2): prefer the player-delivered
-- team; only scripted-spawn a fallback if none was delivered, so the capture loop
-- never silently dies. Capture itself is detected in scar_check against area.sofGroup.
local function spawn_sof(area)
    if not (area.sofX and area.sofRadius and area.sofRadius > 0) then
        return
    end
    local delivered = find_delivered_sof(area)
    if delivered ~= nil then
        area.sofGroup = delivered
        scar_log("area " .. tostring(area.id) ..
            ": capture bound to delivered SOF team " .. tostring(delivered))
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
    scar_log("area " .. tostring(area.id) ..
        ": no delivered team — scripted SOF fallback spawned")
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
    -- Coordinates alone are not a capture team. If dynAdd failed, or the team
    -- was killed before the HVT arrived, the commander must continue escaping.
    if area.sofGroup == nil then
        return false
    end
    local sof_group = Group.getByName(area.sofGroup)
    if sof_group == nil then
        return false
    end
    local oks, sof_size = pcall(function()
        return sof_group:getSize()
    end)
    if not oks or (sof_size or 0) <= 0 then
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

-- Phase 2c-3 CSAR: a botched capture leaves the delivered/scripted SOF team
-- stranded (alive) at the ambush point. Tag its position on the result so the
-- generator can stand up a next-turn CSAR objective to recover it. No tag (team
-- dead, or never delivered) = the team is written off.
local function report_stranded_sof(area)
    if area.sofGroup == nil then
        return
    end
    local group = Group.getByName(area.sofGroup)
    if group == nil then
        return
    end
    local ok, unit = pcall(function()
        return group:getUnit(1)
    end)
    if not ok or unit == nil then
        return
    end
    local okp, pos = pcall(function()
        return unit:getPoint() -- {x = north, y = alt, z = east}
    end)
    if not okp or pos == nil then
        return
    end
    local entry = scar_results[area.id]
    if type(entry) ~= "table" then
        entry = { status = "failed" }
        scar_results[area.id] = entry
    end
    entry.sofStrandedX = pos.x
    entry.sofStrandedY = pos.z
    dirty_state = true
    scar_log("area " .. tostring(area.id) .. ": SOF team stranded for CSAR pickup")
end

-- Bind the SOF capture team lazily, only as the HVT nears the ambush point. With
-- the scenario now live at spawn, binding at t=0 would always miss a player-flown
-- drop (none delivered yet) and fall straight to the scripted team; deferring until
-- the HVT closes gives the player time to airdrop one (Phase 2c-2). Binds once.
local SOF_PREBIND_M = 4000
local function maybe_bind_sof(area)
    if area.sofBound or not (area.sofRadius and area.sofRadius > 0) then
        return
    end
    local group = Group.getByName(area.groups[1])
    if group == nil then
        return
    end
    local ok, unit = pcall(function()
        return group:getUnit(1)
    end)
    if not ok or unit == nil then
        return
    end
    local pos = unit:getPoint() -- {x = north, y = alt, z = east}
    local dx = pos.x - area.sofX
    local dz = pos.z - area.sofY
    if (dx * dx + dz * dz) <= (SOF_PREBIND_M * SOF_PREBIND_M) then
        spawn_sof(area)
        area.sofBound = true
    end
end

-- Forward declaration: activate_movement (below) routes via set_group_route, which
-- is defined later in the file. Declaring the local here lets the closure capture
-- it as an upvalue; it's assigned by the time activation actually runs.
local set_group_route

-- Proximity activation (2026-06-21, A-10 feedback): the picture spawns PARKED at
-- mission start (the discrimination puzzle is present), and the HVT only bugs out
-- once the strike package crosses the activation ring. So the target is moving when
-- the player arrives but can never be "long gone" if the jets are slow — and the
-- fail clock starts from the approach, not mission start.
local SCAR_PROXIMITY_M = 50 * 1852 -- 50 NM activation ring (tunable)

-- True once a HUMAN-flown (client) SCAR-coalition aircraft is within the ring of
-- the area. Gating on player-controlled units -- not any friendly group -- keeps
-- AI tankers / AWACS / CAP that transit within the 50 NM ring from starting the
-- chase before the strike package actually arrives (which would re-open the very
-- "target's long gone" failure this proximity gate exists to prevent). Iterates
-- every unit so a human in a non-lead slot still counts.
local function package_near(area)
    local side = scar_side(area)
    local r2 = SCAR_PROXIMITY_M * SCAR_PROXIMITY_M
    for _, cat in ipairs({ Group.Category.AIRPLANE, Group.Category.HELICOPTER }) do
        local ok, groups = pcall(coalition.getGroups, side, cat)
        if ok and groups ~= nil then
            for _, g in ipairs(groups) do
                local oku, units = pcall(g.getUnits, g)
                if oku and units ~= nil then
                    for _, u in ipairs(units) do
                        local okp, pos = pcall(function()
                            -- getPlayerName() is nil for AI; only humans trigger.
                            if u:getPlayerName() == nil then
                                return nil
                            end
                            return u:getPoint() -- {x = north, y = alt, z = east}
                        end)
                        if okp and pos ~= nil then
                            local dx = pos.x - area.centerX
                            local dz = pos.z - area.centerY
                            if (dx * dx + dz * dz) <= r2 then
                                return true
                            end
                        end
                    end
                end
            end
        end
    end
    return false
end

-- Loiter-and-task rework: an area is STATIC when nothing is meant to move -- every
-- mover at speed 0, the case _make_static produces. A static area holds in place and
-- can only fail on the window timeout: no chase, no arrival-fail.
local function area_is_static(area)
    for _, m in ipairs(area.movers or {}) do
        if (m.speed or 0) > 0 then
            return false
        end
    end
    return true
end

-- Open the fail clock when the package arrives. A MOVING area also routes every
-- parked mover to its destination; a STATIC area just holds (speed-0 movers are
-- skipped, so nothing drives) and is serviced in place.
local function activate_movement(area)
    for _, m in ipairs(area.movers or {}) do
        if (m.speed or 0) > 0 then
            set_group_route(m.name, m.destX, m.destY, m.speed)
        end
    end
    area.activated = true
    area.deadline = timer.getTime() + (area.window or 1200)
    scar_log("area " .. tostring(area.id) .. " ACTIVATED (package within " ..
        math.floor(SCAR_PROXIMITY_M / 1852) .. " NM)" ..
        (area_is_static(area) and " [static hold]" or "") .. "; window " ..
        math.floor(area.window or 1200) .. "s")
end

local function scar_check()
    for _, area in ipairs(scar_areas) do
        if not area.done then
            -- Parked until the package reaches the ring; then it bugs out and the
            -- fail clock starts. A kill before activation still counts as success.
            if not area.activated and package_near(area) then
                activate_movement(area)
            end
            local live = area.activated == true
            local timed_out = live and area.deadline
                and timer.getTime() >= area.deadline
            local static = area_is_static(area)
            maybe_bind_sof(area)
            if all_groups_dead(area) then
                mark_result(area, "success")
            elseif area.variant == "missile" then
                if static then
                    -- Loiter rework: the SCUD holds for the flight to service -- it
                    -- neither relocates nor launches. Fail = the window timeout only.
                    if timed_out then
                        mark_result(area, "failed")
                    end
                elseif live and (hvt_in_fail_zone(area) or timed_out) then
                    -- Moving SCUD reached its firing position (or out of time).
                    launch_missile(area)
                    mark_result(area, "launched")
                end
            elseif static then
                -- Static armor/spawn: the target holds in the kill box, so the only
                -- loss is the window timeout. The instant arrival-fail (dest == centre)
                -- is gated off; the SOF commander-capture is the inverted-assault
                -- redesign (Phase 1b) and is not wired here yet.
                if timed_out then
                    mark_result(area, "failed")
                    report_stranded_sof(area)
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
                    report_stranded_sof(area)
                elseif timed_out then
                    -- Ran out of time; the convoy is still en route.
                    mark_result(area, "failed")
                    report_stranded_sof(area)
                end
            end
        end
    end
end

-- SHOT: missile launch = fail (any weapon release by a watched surface-to-surface
-- site). KILL: a decoy/clutter group destroyed by the prosecuting side = a mis-ID.
local scar_event_handler = {}
function scar_event_handler:onEvent(event)
    if event == nil or event.initiator == nil then
        return
    end
    if event.id == world.event.S_EVENT_SHOT then
        local ok, group_name = pcall(function()
            return event.initiator:getGroup():getName()
        end)
        if ok and group_name ~= nil then
            local area = missile_group_index[group_name]
            if area ~= nil and not area.done then
                mark_result(area, "launched")
            end
        end
        return
    end
    if event.id == world.event.S_EVENT_KILL and event.target ~= nil then
        local okt, target_group = pcall(function()
            return event.target:getGroup():getName()
        end)
        if not okt or target_group == nil then
            return
        end
        local area = misid_group_index[target_group]
        if area == nil then
            return
        end
        -- Only the prosecuting (SCAR) side striking the wrong convoy is a mis-ID;
        -- an ambiguous/unknown killer (nil coalition) is not charged.
        local okc, killer_side = pcall(function()
            return event.initiator:getCoalition()
        end)
        if okc and killer_side == scar_side(area) then
            record_misid(area)
        end
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
-- (Assigns the forward-declared `set_group_route` upvalue so activate_movement,
-- defined earlier, can call it.)
function set_group_route(group_name, dest_x, dest_y, speed)
    -- Static hold (loiter rework): a speed-0 "mover" must never be routed -- it stays
    -- put for the SCAR flight to service. activate_movement already skips these; guard
    -- here too so nothing can drive a static group.
    if not speed or speed <= 0 then
        return
    end
    local group = Group.getByName(group_name)
    if group == nil then
        -- DIAGNOSTIC (scar bound-group movement): a silent miss here means the
        -- name we were handed (the TGO group name from the generator) does not
        -- match the live DCS group, so the bound HVT/SCUD never gets routed.
        scar_log("set_group_route: group not found by name '" ..
            tostring(group_name) .. "' — bound HVT/SCUD will not move")
        return
    end
    -- Artillery/missile units (e.g. a BM-30 Smerch SCUD) sit in alarm-state RED
    -- (deployed, stationary, ready to fire) and IGNORE a move route, so the bound
    -- missile HVT never road-marched even though goRoute succeeded — while regular
    -- armor moves fine. Force the group to alarm-state GREEN so it actually drives.
    -- ROE stays WEAPON_HOLD (set by the caller), so it still won't shoot en route.
    pcall(function()
        local ctrl = group:getController()
        if ctrl then
            ctrl:setOption(
                AI.Option.Ground.id.ALARM_STATE,
                AI.Option.Ground.val.ALARM_STATE.GREEN
            )
        end
    end)
    local oku, unit = pcall(function()
        return group:getUnit(1)
    end)
    if not oku or unit == nil then
        scar_log("set_group_route: '" .. tostring(group_name) ..
            "' has no unit 1 — cannot route")
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
    else
        -- DIAGNOSTIC: confirm the route was applied and to where, so a "still not
        -- moving" report can be told apart from a bad/zero destination.
        scar_log("set_group_route: '" .. tostring(group_name) .. "' -> (" ..
            tostring(dest_x) .. ", " .. tostring(dest_y) .. ") @ " ..
            tostring(speed) .. " m/s")
        -- DIAGNOSTIC: 90s later, log how far the group actually travelled, so a
        -- "route applied but group not following goRoute" failure is distinct from
        -- normal movement. ~0 m = the group is ignoring the route.
        local start_x, start_z = pos.x, pos.z
        mist.scheduleFunction(function()
            local g = Group.getByName(group_name)
            if g == nil then
                return
            end
            local oku2, u2 = pcall(function()
                return g:getUnit(1)
            end)
            if not oku2 or u2 == nil then
                return
            end
            local p2 = u2:getPoint()
            local moved = math.sqrt(
                (p2.x - start_x) ^ 2 + (p2.z - start_z) ^ 2
            )
            scar_log("set_group_route: '" .. tostring(group_name) ..
                "' moved " .. string.format("%.0f", moved) ..
                " m in 90s after routing")
        end, {}, timer.getTime() + 90)
    end
end

-- Record a parked group that should drive to (dx, dy) at `speed` when the area
-- activates (proximity). Threats (speed 0, holding station) are not movers.
local function add_mover(area, name, dx, dy, speed)
    if name == nil then
        return
    end
    area.movers = area.movers or {}
    area.movers[#area.movers + 1] = { name = name, destX = dx, destY = dy, speed = speed }
end

-- Spawn variant: spawns the whole ground picture PARKED at mission start (the
-- discrimination puzzle is present from the off); the columns only start fleeing
-- when the package reaches the activation ring (scar_check -> activate_movement).
-- Only the HVT is tracked; decoys/clutter are the puzzle. The SOF capture team is
-- bound lazily (maybe_bind_sof).
local function activate_spawn_area(tasking, window)
    local country_id = scar_num(tasking.hvtCountryId)
    local area = {
        id = tostring(tasking.taskingId),
        variant = "spawn",
        coalition = tostring(tasking.coalition or "blue"),
        groups = {},
        done = false,
        activated = false,
        window = window,
        movers = {},
        centerX = scar_num(tasking.centerX, 0),
        centerY = scar_num(tasking.centerY, 0),
        destX = 0,
        destY = 0,
        radius = scar_num(tasking.failZoneRadius, 500),
        commandType = tostring(tasking.commandType or ""),
        -- Phase 2a SOF ambush (set only when scar_command_post_intel is on).
        sofX = scar_num(tasking.sofX),
        sofY = scar_num(tasking.sofY),
        sofRadius = scar_num(tasking.sofRadius),
        sofCountryId = scar_num(tasking.sofCountryId),
        sofUnitType = tostring(tasking.sofUnitType or ""),
    }
    local hvt_convoy = nil
    local spawn_index = 0
    for _, convoy in pairs(tasking.convoys or {}) do
        spawn_index = spawn_index + 1
        local name = spawn_convoy(tasking.taskingId, convoy, country_id, spawn_index)
        if name ~= nil then
            local role = tostring(convoy.role)
            if role ~= "threat" then
                add_mover(area, name, scar_num(convoy.destX, 0),
                    scar_num(convoy.destY, 0), scar_num(convoy.speed, 5))
            end
            if role == "hvt" then
                hvt_convoy = convoy
                area.groups = { name }
                area.destX = scar_num(convoy.destX, 0)
                area.destY = scar_num(convoy.destY, 0)
            elseif role == "decoy" or role == "clutter" then
                misid_group_index[name] = area
            end
        end
    end
    if #area.groups > 0 then
        table.insert(scar_areas, area)
        brief_spawn(area, hvt_convoy)
        scar_log("area " .. area.id .. " spawned (parked); window " ..
            math.floor(window) .. "s")
    else
        scar_log("spawn tasking " .. tostring(tasking.taskingId) ..
            ": no HVT convoy spawned")
    end
end

-- Missile variant: a real SCUD site that RACES from its location to a firing
-- position and launches on arrival. Held on WEAPON_HOLD so it can't fire en
-- route; the player must kill it before it reaches the firing position (or the
-- window expires), at which point it launches (fail). It starts racing AT SPAWN,
-- paced slow enough (over `window`) to stay catchable rather than firing early.
local function activate_missile_area(tasking, window)
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
        activated = false,
        window = window,
        movers = {},
        centerX = scar_num(tasking.centerX, 0),
        centerY = scar_num(tasking.centerY, 0),
        destX = scar_num(tasking.destX, 0),
        destY = scar_num(tasking.destY, 0),
        radius = scar_num(tasking.failZoneRadius, 2000),
        fireTargetX = scar_num(tasking.fireTargetX, 0),
        fireTargetY = scar_num(tasking.fireTargetY, 0),
    }
    local speed = scar_num(tasking.fleeSpeed, 5)
    for _, name in ipairs(groups) do
        missile_group_index[name] = area
        set_group_roe(name, AI.Option.Ground.val.ROE.WEAPON_HOLD)
        -- Held parked + WEAPON_HOLD until the package arrives; then it races to the
        -- firing position (activate_movement) and fires on arrival = the fail.
        add_mover(area, name, area.destX, area.destY, speed)
    end
    table.insert(scar_areas, area)
    brief_missile(area)
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
        "The real column starts moving as you arrive, with a command vehicle riding " ..
        "with it. Decoys share SOME elements — some even a command vehicle — so match the " ..
        "FULL signature and destroy it (command vehicle included) before it reaches " ..
        "the city."
    pcall(trigger.action.outTextForCoalition, side, text, 30)
    -- Mark the search AREA, not the exact column: it's moving and mixed in with
    -- decoys, so the player has to find and ID it (2026-06-20: a pin on the one
    -- correct group made it trivial).
    pcall(trigger.action.markToCoalition, next_mark_id(),
        "SCAR search area — find the HVT (" .. sig .. " + command vehicle) among the " ..
        "traffic; it's on the move", { x = area.centerX, y = 0, z = area.centerY },
        side, true)
    pcall(trigger.action.markToCoalition, next_mark_id(),
        "SCAR no-strike zone — armor safe haven", { x = area.destX, y = 0, z = area.destY },
        side, true)
    mark_sof(area, side)
end

-- Armor variant: bind the REAL armor group. It bugs out toward the city AT SPAWN,
-- with the decoy/clutter columns + command vehicle spawned alongside it from the
-- start (so the puzzle is present when the player arrives); success = killed, fail
-- = it reaches the city (its safe haven) or the window expires. The SOF capture
-- team is bound lazily (maybe_bind_sof) so a player-delivered team is still picked
-- up later instead of pre-empted by the t=0 fallback.
local function activate_armor_area(tasking, window)
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
        activated = false,
        window = window,
        movers = {},
        centerX = scar_num(tasking.centerX, 0),
        centerY = scar_num(tasking.centerY, 0),
        destX = scar_num(tasking.destX, 0),
        destY = scar_num(tasking.destY, 0),
        radius = scar_num(tasking.failZoneRadius, 2000),
        -- The command vehicle riding with the real column: tracked (must die for
        -- success) and the unit that despawns ("escapes") on reaching the city.
        commandType = tostring(tasking.commandType or ""),
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
    -- The real armor is a mover (parked until the package arrives, then bugs out)...
    for _, name in ipairs(area.groups) do
        add_mover(area, name, area.destX, area.destY, speed)
    end
    -- ...the decoy/clutter columns + command vehicle spawn PARKED alongside it (so
    -- the puzzle is present from the start) and flee on activation too; the command
    -- vehicle IS tracked, so append it to area.groups.
    local spawn_index = 0
    for _, convoy in pairs(tasking.convoys or {}) do
        spawn_index = spawn_index + 1
        local spawned = spawn_convoy(tasking.taskingId, convoy, country_id, spawn_index)
        if spawned ~= nil then
            local role = tostring(convoy.role)
            if role ~= "threat" then
                add_mover(area, spawned, scar_num(convoy.destX, 0),
                    scar_num(convoy.destY, 0), scar_num(convoy.speed, 5))
            end
            if role == "command" then
                table.insert(area.groups, spawned)
            elseif role == "decoy" or role == "clutter" then
                misid_group_index[spawned] = area
            end
        end
    end
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
        local window = scar_num(tasking.window, 1200)
        -- Seed the result now so a never-resolved area still reports as active.
        scar_results[tostring(tasking.taskingId)] = { status = "active" }
        dirty_state = true
        -- Trigger AT SPAWN (mission start): spawn the picture and start it moving
        -- now, so it's present and dynamic whenever the player arrives.
        if variant == "missile" then
            if activate_missile_area(tasking, window) then
                count = count + 1
            end
        elseif variant == "armor" then
            if activate_armor_area(tasking, window) then
                count = count + 1
            end
        else
            if pcall(activate_spawn_area, tasking, window) then
                count = count + 1
            end
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
