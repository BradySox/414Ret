-- Records what each aircraft actually did, into state.json's sortie_records.
-- See docs/dev/design/414th-retribution-long-view.md seam 1.
--
-- Vanilla DCS only. Tacview is a paid third-party program, so nothing here may
-- depend on it or its .acmi export.
--
-- Constraints learned the hard way:
--  * Records are keyed by UNIT, never by group. group:getUnits() returns only
--    the living units, so a fixed index is not a fixed aircraft -- keying by
--    group and sampling units[1] teleported the track onto a wingman the moment
--    the lead died, and counted the jump as distance flown.
--  * Every human-crewed slot is sampled; AI groups only sample one anchor jet.
--    Four humans in one group do not fly the same track. Sixty AI in formation
--    do, so paying per-unit for them buys nothing.
--  * The track is emitted ONLY in the final write. state.json is rewritten every
--    15 s -- 480 times over a two-hour mission -- and a 60v60 track set is ~1 MB,
--    so including it in every write means half a gigabyte of json:encode on the
--    sim thread of a mission that already has no frames spare.
--  * Every entry point is wrapped by the caller in pcall. A recorder fault must
--    never take down the loss reporting that shares this file.

SORTIE_RECORD_VERSION = 1

-- Seconds between position samples.
local SAMPLE_INTERVAL_S = 30

-- Most samples kept per aircraft: four hours at the interval above. Long enough
-- that an AWACS or tanker orbiting the whole mission keeps its start. Costs only
-- an in-memory table, because the track is not in the periodic writes.
local MAX_SAMPLES = 480

sortie_records = { version = SORTIE_RECORD_VERSION, flights = {} }

-- Metres of movement between sweeps below which the aircraft is parked. A jet
-- sitting on the ramp jitters well under a metre; the slowest thing worth a
-- sample covers hundreds over 30 s.
local STATIONARY_M = 25

-- unit name -> true for the one AI jet per group whose position is sampled.
local anchors = {}

-- unit name -> true while the last sample continued a stationary run, so the
-- run is stored as its two endpoints instead of one row per sweep. The idle
-- ramp is why: `_spawn_unused_for` parks a squadron's untasked airframes as
-- 1-ship Completed groups and this sweep cannot tell them from flights, so 82
-- of test 12's 158 records were parked jets writing 86 identical samples each
-- -- 68% of a 1.18 MB state.json. Kept OUT of the record so nothing new is
-- serialized.
local parked = {}

local function safe(unit, method)
    if not unit then
        return nil
    end
    local ok, value = pcall(function()
        return unit[method](unit)
    end)
    if not ok then
        return nil
    end
    return value
end

-- Resolve a unit's group without assuming the unit is still alive: getGroup()
-- returns nil for a destroyed unit, and the shot/hit handlers can fire either
-- side of a kill.
local function group_name_of(unit)
    local group = safe(unit, "getGroup")
    if not group then
        return nil
    end
    local ok, name = pcall(function()
        return group:getName()
    end)
    if not ok then
        return nil
    end
    return name
end

-- Fall back to the documented numeric values so a sandbox without the Unit
-- table cannot take the whole recorder down at file scope.
local CAT_AIRPLANE = (Unit and Unit.Category and Unit.Category.AIRPLANE) or 0
local CAT_HELICOPTER = (Unit and Unit.Category and Unit.Category.HELICOPTER) or 1

local function is_aircraft(unit)
    local desc = safe(unit, "getDesc")
    if type(desc) ~= "table" then
        return false
    end
    return desc.category == CAT_AIRPLANE or desc.category == CAT_HELICOPTER
end

local function record_for(unit)
    local unit_name = safe(unit, "getName")
    -- A shell or bomb reaches the hit handler as the initiator and its getName
    -- is "", which collided every cannon round in the mission into one record.
    if not unit_name or unit_name == "" then
        return nil
    end
    local record = sortie_records.flights[unit_name]
    if record then
        return record
    end
    -- Only aircraft belong in a per-FLIGHT record; the AAA and armour that shot
    -- at the package are initiators too. Checked only when creating, so a jet
    -- whose getDesc fails after it dies keeps counting on its existing record.
    if not is_aircraft(unit) then
        return nil
    end
    record = {
        group = group_name_of(unit) or unit_name,
        type = safe(unit, "getTypeName") or "",
        coalition = safe(unit, "getCoalition") or 0,
        player = safe(unit, "getPlayerName") ~= nil,
        first_seen = -1,
        last_seen = -1,
        track = {},
        shots = 0,
        hits = 0,
        ejected = false,
    }
    sortie_records.flights[unit_name] = record
    return record
end

local function sample_unit(unit, now)
    local point = safe(unit, "getPoint")
    if not point then
        return
    end
    local record = record_for(unit)
    if not record then
        return
    end
    local unit_name = safe(unit, "getName")
    if not unit_name then
        return
    end
    if record.first_seen < 0 then
        record.first_seen = now
    end
    record.last_seen = now
    -- Re-read each sweep: a slot can be taken by a human mid-mission.
    if safe(unit, "getPlayerName") ~= nil then
        record.player = true
    end

    local sample = {
        t = now,
        x = point.x,
        z = point.z,
        alt = point.y,
        fuel = safe(unit, "getFuel") or 0,
    }
    local tail = record.track[#record.track]
    if
        tail
        and math.abs(sample.x - tail.x) < STATIONARY_M
        and math.abs(sample.z - tail.z) < STATIONARY_M
    then
        -- Second and later sweeps of a stationary run overwrite the run's tail,
        -- so the run costs two rows however long it lasts. The run's first row
        -- always survives, and last_seen above is already current.
        if parked[unit_name] then
            record.track[#record.track] = sample
            return
        end
        parked[unit_name] = true
    else
        parked[unit_name] = nil
    end

    table.insert(record.track, sample)
    if #record.track > MAX_SAMPLES then
        table.remove(record.track, 1)
    end
end

-- Shot-to-first-impact matching. DCS raises one S_EVENT_SHOT per weapon released
-- but one S_EVENT_HIT per IMPACTING object, and a cluster weapon's submunitions are
-- different objects from the one that left the rail -- so two CBU-105 releases
-- scored 68 "hits" and the SITREP read 106 shots for 381 hits (test 8, 2026-08-18).
-- A hit is now counted only against a weapon we saw fired, and only the first time
-- that weapon strikes, which makes shots and hits commensurable.
local pending_shots = {} -- [weapon key] = fired-at time
local PENDING_TTL_S = 900

-- DCS Weapon:getName() returns the object's runtime id; id_ is the raw field MOOSE
-- reads. A weapon we cannot key (a gun round raises no shot at all) is not counted
-- rather than guessed at -- an uncountable shot must not become a free hit.
local function weapon_key(weapon)
    if not weapon then
        return nil
    end
    local name = safe(weapon, "getName")
    if name and name ~= "" then
        return tostring(name)
    end
    local ok, raw_id = pcall(function()
        return weapon.id_
    end)
    if ok and raw_id then
        return tostring(raw_id)
    end
    return nil
end

local function prune_pending(now)
    for key, fired_at in pairs(pending_shots) do
        if now - fired_at > PENDING_TTL_S then
            pending_shots[key] = nil
        end
    end
end

-- Whether this unit's position is worth sampling. Humans always; for AI, the
-- first jet of the group still alive, held until it dies rather than read off a
-- fixed index.
local function should_sample(unit, group_has_anchor)
    if safe(unit, "getPlayerName") ~= nil then
        return true
    end
    local unit_name = safe(unit, "getName")
    if not unit_name then
        return false
    end
    if anchors[unit_name] then
        return true
    end
    if group_has_anchor then
        return false
    end
    anchors[unit_name] = true
    return true
end

-- One sweep over both coalitions' airborne groups.
function sortie_recorder_sample()
    local now = timer.getTime()
    prune_pending(now)
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
                        -- The group category above already guarantees aircraft.
                        local group_has_anchor = false
                        for _, unit in pairs(units) do
                            local unit_name = safe(unit, "getName")
                            if unit_name and anchors[unit_name] then
                                group_has_anchor = true
                            end
                        end
                        for _, unit in pairs(units) do
                            if should_sample(unit, group_has_anchor) then
                                sample_unit(unit, now)
                                group_has_anchor = true
                            end
                        end
                    end
                end
            end
        end
    end
    dirty_state = true
end

local function count_on(initiator, field)
    local record = record_for(initiator)
    if record then
        record[field] = record[field] + 1
        dirty_state = true
    end
end

function sortie_recorder_on_shot(initiator, weapon)
    count_on(initiator, "shots")
    local key = weapon_key(weapon)
    if key then
        pending_shots[key] = timer.getTime()
    end
end

function sortie_recorder_on_hit(initiator, weapon)
    local key = weapon_key(weapon)
    if not key or not pending_shots[key] then
        -- A submunition, a gun round, or a weapon released before the recorder
        -- started. Counting these is what made hits exceed shots.
        return
    end
    pending_shots[key] = nil -- first impact only
    count_on(initiator, "hits")
end

function sortie_recorder_on_ejection(initiator)
    local record = record_for(initiator)
    if record then
        record.ejected = true
        dirty_state = true
    end
end

-- What write_state encodes. The track rides only on the final write; see the
-- header. A crash mid-mission therefore costs the track but keeps the counters,
-- which is what every write carried before this feature existed.
function sortie_recorder_payload(include_track)
    if include_track then
        return sortie_records
    end
    local light = { version = SORTIE_RECORD_VERSION, flights = {} }
    for unit_name, record in pairs(sortie_records.flights) do
        light.flights[unit_name] = {
            group = record.group,
            type = record.type,
            coalition = record.coalition,
            player = record.player,
            first_seen = record.first_seen,
            last_seen = record.last_seen,
            track = {},
            shots = record.shots,
            hits = record.hits,
            ejected = record.ejected,
        }
    end
    return light
end

function sortie_recorder_start()
    mist.scheduleFunction(function()
        pcall(sortie_recorder_sample)
        sortie_recorder_start()
    end, {}, timer.getTime() + SAMPLE_INTERVAL_S)
end
