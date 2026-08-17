-- Records what each flight actually did, into state.json's sortie_records.
-- See docs/dev/design/414th-retribution-long-view.md seam 1.
--
-- Vanilla DCS only. Tacview is a paid third-party program, so nothing here may
-- depend on it or its .acmi export.
--
-- Constraints learned the hard way:
--  * Sampling is throttled and aircraft-only. A dense mission already runs out
--    of frames on ground-unit count; a per-tick sweep of every group would make
--    that worse for data nobody watches live.
--  * The track is capped per flight. An unbounded table on a three-hour mission
--    grows the state file without bound, and state.json is rewritten every 15 s.
--  * Every entry point is wrapped by the caller in pcall. A recorder fault must
--    never take down the loss reporting that shares this file.

SORTIE_RECORD_VERSION = 1

-- Seconds between position samples. 30 s gives a readable track shape over a
-- typical sortie without making the state file large.
local SAMPLE_INTERVAL_S = 30

-- Most samples kept per flight. At 30 s that is two hours airborne; beyond it
-- the oldest samples are dropped so the newest picture is always present.
local MAX_SAMPLES = 240

sortie_records = { version = SORTIE_RECORD_VERSION, flights = {} }

local function record_for(group_name)
    local record = sortie_records.flights[group_name]
    if record then
        return record
    end
    record = {
        type = "",
        coalition = 0,
        first_seen = -1,
        last_seen = -1,
        track = {},
        shots = 0,
        hits = 0,
        ejected = false,
    }
    sortie_records.flights[group_name] = record
    return record
end

-- Resolve the group name for a unit without assuming the unit is still alive:
-- Unit.getGroup() returns nil for a destroyed unit, and the shot/hit handlers
-- can fire either side of a kill.
local function group_name_of(unit)
    if not unit then
        return nil
    end
    local ok, group = pcall(function()
        return unit:getGroup()
    end)
    if not ok or not group then
        return nil
    end
    local named_ok, name = pcall(function()
        return group:getName()
    end)
    if not named_ok or not name then
        return nil
    end
    return name
end

local function sample_unit(unit, now)
    local name = group_name_of(unit)
    if not name then
        return
    end
    local ok, point = pcall(function()
        return unit:getPoint()
    end)
    if not ok or not point then
        return
    end

    local record = record_for(name)
    if record.first_seen < 0 then
        record.first_seen = now
        local typed_ok, type_name = pcall(function()
            return unit:getTypeName()
        end)
        if typed_ok and type_name then
            record.type = type_name
        end
        local coa_ok, coa = pcall(function()
            return unit:getCoalition()
        end)
        if coa_ok and coa then
            record.coalition = coa
        end
    end
    record.last_seen = now

    local fuel = 0
    local fuel_ok, fuel_value = pcall(function()
        return unit:getFuel()
    end)
    if fuel_ok and fuel_value then
        fuel = fuel_value
    end

    table.insert(record.track, {
        t = now,
        x = point.x,
        z = point.z,
        alt = point.y,
        fuel = fuel,
    })
    if #record.track > MAX_SAMPLES then
        table.remove(record.track, 1)
    end
end

-- One sweep over both coalitions' airborne groups.
function sortie_recorder_sample()
    local now = timer.getTime()
    for _, side in pairs({ coalition.side.RED, coalition.side.BLUE }) do
        for _, category in pairs({ Group.Category.AIRPLANE, Group.Category.HELICOPTER }) do
            local ok, groups = pcall(function()
                return coalition.getGroups(side, category)
            end)
            if ok and groups then
                for _, group in pairs(groups) do
                    local units_ok, units = pcall(function()
                        return group:getUnits()
                    end)
                    if units_ok and units then
                        -- The lead is enough: a flight's members fly the same
                        -- track, and sampling all of them multiplies the state
                        -- file by the group size for no extra information. The
                        -- group category above already guarantees an aircraft.
                        local lead = units[1]
                        if lead then
                            sample_unit(lead, now)
                        end
                    end
                end
            end
        end
    end
    dirty_state = true
end

function sortie_recorder_on_shot(initiator)
    local name = group_name_of(initiator)
    if name then
        record_for(name).shots = record_for(name).shots + 1
        dirty_state = true
    end
end

function sortie_recorder_on_hit(initiator)
    local name = group_name_of(initiator)
    if name then
        record_for(name).hits = record_for(name).hits + 1
        dirty_state = true
    end
end

function sortie_recorder_on_ejection(initiator)
    local name = group_name_of(initiator)
    if name then
        record_for(name).ejected = true
        dirty_state = true
    end
end

function sortie_recorder_start()
    mist.scheduleFunction(function()
        pcall(sortie_recorder_sample)
        sortie_recorder_start()
    end, {}, timer.getTime() + SAMPLE_INTERVAL_S)
end
