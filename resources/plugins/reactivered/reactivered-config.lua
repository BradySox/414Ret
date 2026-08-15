-- Living battlespace reactive red (§89 P5): when a listed red objective loses
-- a unit, one planner-fragged alert flight activates after a tasking delay and
-- orbits the struck objective.
-- Design + positive-list contract: docs/dev/design/414th-living-battlespace-notes.md
-- and game/missiongenerator/reactiveredluadata.py (the emitter).
-- Constraints a reader could undo by accident:
--   * Positive list only: the plugin may activate ONLY the emitted groups and
--     orbit ONLY the emitted objectives. It never widens either.
--   * No spawns, no kills. The alert flights are real claimed ATO airframes
--     parked late-activation; activate() is the only launch path.
--   * One reaction per objective; the fragged pool is the hard cap.
--   * The orbit task is pushed only once the flight is airborne -- a task push
--     mid-taxi can wedge the takeoff (the §61 redscramble lesson).

local cfg = dcsRetribution
    and dcsRetribution.plugins
    and dcsRetribution.plugins.reactivered
if not cfg then
    return
end

local net = dcsRetribution and dcsRetribution.reactiveRed
if
    not net
    or type(net.groups) ~= "table"
    or #net.groups == 0
    or type(net.objectives) ~= "table"
    or #net.objectives == 0
then
    env.info("REACTRED|: nothing emitted; plugin idle")
    return
end

local DELAY_S = tonumber(cfg.reactionDelaySec) or 420
local ORBIT_ALT_M = tonumber(cfg.orbitAltM) or 5500
local ORBIT_SPEED_MS = 180
local AIRBORNE_POLL_S = 15

local objectives = {}
local watched = {} -- unit name -> objective record
for _, rec in ipairs(net.objectives) do
    local objective = {
        name = tostring(rec.name or "objective"),
        x = tonumber(rec.x) or 0,
        y = tonumber(rec.y) or 0,
        reacted = false,
    }
    objectives[#objectives + 1] = objective
    if type(rec.units) == "table" then
        for _, unit_name in ipairs(rec.units) do
            watched[tostring(unit_name)] = objective
        end
    end
end

local pool = {}
for _, group_name in ipairs(net.groups) do
    pool[#pool + 1] = tostring(group_name)
end
local next_group = 1

local function group_airborne(grp)
    for _, u in ipairs(grp:getUnits() or {}) do
        if u and u:isExist() and u:inAir() then
            return true
        end
    end
    return false
end

-- Push the patrol orbit once the alert flight is airborne (poll; a mid-taxi
-- task push can wedge the takeoff). Gives up quietly if the flight dies first.
local function task_when_airborne(group_name, objective)
    local grp = Group.getByName(group_name)
    if not grp or not grp:isExist() or grp:getSize() == 0 then
        env.info("REACTRED|: " .. group_name .. " lost before tasking; reaction ends")
        return nil
    end
    if not group_airborne(grp) then
        return timer.getTime() + AIRBORNE_POLL_S
    end
    local ok = pcall(function()
        grp:getController():setTask({
            id = "Orbit",
            params = {
                pattern = "Circle",
                point = { x = objective.x, y = objective.y },
                altitude = ORBIT_ALT_M,
                speed = ORBIT_SPEED_MS,
            },
        })
    end)
    if ok then
        env.info(
            "REACTRED|: " .. group_name .. " on station over " .. objective.name
        )
    else
        env.warning("REACTRED|: orbit task push failed for " .. group_name)
    end
    return nil
end

local function launch_reaction(objective)
    if next_group > #pool then
        env.info("REACTRED|: reaction pool exhausted; no launch for " .. objective.name)
        return
    end
    local group_name = pool[next_group]
    next_group = next_group + 1
    local grp = Group.getByName(group_name)
    if not grp then
        env.info("REACTRED|: " .. group_name .. " not present; reaction skipped")
        return
    end
    local ok = pcall(function()
        grp:activate()
    end)
    if not ok then
        env.warning("REACTRED|: activate failed for " .. group_name)
        return
    end
    env.info(
        "REACTRED|: " .. group_name .. " scrambling over " .. objective.name
    )
    timer.scheduleFunction(function()
        local okTick, nextT = pcall(task_when_airborne, group_name, objective)
        if not okTick then
            env.error("REACTRED|: tasking error: " .. tostring(nextT))
            return nil
        end
        return nextT
    end, {}, timer.getTime() + AIRBORNE_POLL_S)
end

local handler = {}
function handler:onEvent(event)
    if not event or event.id ~= world.event.S_EVENT_DEAD then
        return
    end
    local unit = event.initiator
    if not unit then
        return
    end
    local ok, name = pcall(function()
        return unit:getName()
    end)
    if not ok or not name then
        return
    end
    local objective = watched[tostring(name)]
    if not objective or objective.reacted then
        return
    end
    objective.reacted = true
    env.info(
        "REACTRED|: "
            .. objective.name
            .. " struck; alert launch in "
            .. tostring(DELAY_S)
            .. " s"
    )
    timer.scheduleFunction(function()
        local okLaunch, err = pcall(launch_reaction, objective)
        if not okLaunch then
            env.error("REACTRED|: launch error: " .. tostring(err))
        end
        return nil
    end, {}, timer.getTime() + DELAY_S)
end

world.addEventHandler(handler)
env.info(
    string.format(
        "REACTRED|: armed -- %d objectives watched, %d alert flights in the pool",
        #objectives,
        #pool
    )
)
