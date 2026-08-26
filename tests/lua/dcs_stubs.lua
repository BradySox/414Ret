-------------------------------------------------------------------------------
-- Headless fake of the vanilla-DCS mission scripting environment, for running
-- resources/plugins/**.lua under pytest via lupa (Lua 5.1 -- the DCS dialect).
--
-- Scope: just enough of the sandbox API for plugin smoke tests -- a virtual
-- clock driving timer.scheduleFunction, recording trigger.action.* calls, and
-- a tiny unit/group world the tests populate. It does NOT model DCS AI, LoS,
-- physics, or weapons flight; anything behavioral still needs the in-game pass
-- (docs/dev/414th-ingame-pass-checklist.md). What it catches is the class of
-- "the script errors at file scope / in a timer tick and the feature silently
-- never runs" bug that luac -p cannot see.
--
-- Conventions mirrored from DCS:
--   * timer.scheduleFunction(fn, args, t): fn(args, time) -> next time | nil.
--   * Points are { x = north, y = up, z = east }; Vec2 is { x = north, y = east }.
--   * land.getHeight takes a Vec2 ({ x, y = east }).
-- The test harness object is exposed as the DcsHarness global.
-------------------------------------------------------------------------------

local Harness = {
    now = 0,
    records = {
        explosions = {}, -- { x, y, z, power, t }
        smokes = {}, -- { x, y, z, color, t }
        bigSmokes = {}, -- { x, y, z, preset, density, name, t }
        stoppedEffects = {},
        texts = {}, -- { side, text, duration, t }
        marks = {}, -- { id, text, x, y, z, side, t }
        removedMarks = {},
        menus = {}, -- { side, path }
        firedTasks = {}, -- { group, x, y, radius, rounds, t }
        aiOnOff = {}, -- { group, on, t } from Controller:setOnOff
        controllerTasks = {}, -- { group, taskId, targetGroupId, x, y, t } from Controller:setTask
        controllerResets = {}, -- { group, t } from Controller:resetTask
        activations = {}, -- group names from Group:activate (late-activation launches)
        controllerCommands = {}, -- { group, commandId, t } from Controller:setCommand
        options = {}, -- { group, option, value, t } from Controller:setOption
        weaponDestroys = {}, -- { name, t } from Weapon:destroy (growler spoof)
        spawns = {}, -- { template, alias, base, takeoff, altitude, grouping, speedKt, t }
        roe = {}, -- { group, option, t } from MOOSE Option* calls
        routes = {}, -- { group, x, y, z, speed, t } from MOOSE RouteToVec3
        destroys = {}, -- group names from MOOSE GROUP:Destroy
        radioTransmissions = {}, -- { file, x, y, z, mod, loop, hz, power, name, t }
        stoppedTransmissions = {}, -- transmission names
        sounds = {}, -- { groupId, file, t } from outSound*
        destroyedStatics = {}, -- static unit names removed via StaticObject:destroy
        markups = {}, -- { shape, id, points, color, fill, lineType, t } from markupToAll
        mapTexts = {}, -- { id, x, z, color, fill, fontSize, text } from textToAll
        zoneFills = {}, -- { name, points, coalition, color, alpha } from ZONE_POLYGON:ReFill

        infos = {},
        warnings = {},
        errors = {}, -- env.error + errors escaping scheduled functions
    },
    groupsByName = {},
    unitsByName = {},
    groupsBySideCat = {}, -- [side][category] -> list
    airbases = {}, -- name -> AirbaseFake (Harness.addAirbase)
    markPanels = {},
    terrainHeight = 0,
}
DcsHarness = Harness

-------------------------------------------------------------------------------
-- env
-------------------------------------------------------------------------------
env = {
    info = function(msg)
        table.insert(Harness.records.infos, tostring(msg))
    end,
    warning = function(msg)
        table.insert(Harness.records.warnings, tostring(msg))
    end,
    error = function(msg)
        table.insert(Harness.records.errors, tostring(msg))
    end,
}

-------------------------------------------------------------------------------
-- timer: a virtual clock. Nothing runs until the test advances time.
-------------------------------------------------------------------------------
local schedule = {} -- { fn, args, t, id }
local nextScheduleId = 0

timer = {
    getTime = function()
        return Harness.now
    end,
    scheduleFunction = function(fn, args, t)
        nextScheduleId = nextScheduleId + 1
        table.insert(schedule, { fn = fn, args = args, t = t or Harness.now, id = nextScheduleId })
        return nextScheduleId
    end,
    removeFunction = function(id)
        for i, e in ipairs(schedule) do
            if e.id == id then
                table.remove(schedule, i)
                return
            end
        end
    end,
}

function Harness.pendingCount()
    return #schedule
end

-- Run every scheduled function due up to (and including) t, in time order,
-- honoring DCS reschedule-by-return semantics. Then park the clock at t.
function Harness.advanceTo(t)
    while true do
        local best, bestIndex
        for i, e in ipairs(schedule) do
            if e.t <= t and (not best or e.t < best.t or (e.t == best.t and e.id < best.id)) then
                best, bestIndex = e, i
            end
        end
        if not best then
            break
        end
        table.remove(schedule, bestIndex)
        Harness.now = best.t
        local ok, nextT = pcall(best.fn, best.args, Harness.now)
        if not ok then
            table.insert(Harness.records.errors, "scheduled function error: " .. tostring(nextT))
        elseif type(nextT) == "number" then
            best.t = nextT
            table.insert(schedule, best)
        end
    end
    Harness.now = t
end

-------------------------------------------------------------------------------
-- Units and groups
-------------------------------------------------------------------------------
coalition = {
    side = { NEUTRAL = 0, RED = 1, BLUE = 2 },
}

Group = {
    Category = { AIRPLANE = 0, HELICOPTER = 1, GROUND = 2, SHIP = 3, TRAIN = 4 },
}

-- The vanilla AI option enums a plugin needs to set alarm states / ROE via
-- Controller:setOption (values match the DCS mission scripting environment).
AI = {
    Option = {
        Ground = {
            id = { ROE = 0, ALARM_STATE = 9 },
            val = {
                ALARM_STATE = { AUTO = 0, GREEN = 1, RED = 2 },
                -- Ground ROE values (match the DCS mission scripting env);
                -- the growler plugin's weapons-hold pulse sets these.
                ROE = { OPEN_FIRE = 2, RETURN_FIRE = 3, WEAPON_HOLD = 4 },
            },
        },
    },
}

country = {
    id = { RUSSIA = 0, USA = 2 },
}

local UnitFake = {}
UnitFake.__index = UnitFake

function UnitFake:isExist()
    return self.exists ~= false
end

function UnitFake:getLife()
    return self.life or 1
end

function UnitFake:getPoint()
    return { x = self.x or 0, y = self.alt or 0, z = self.z or 0 }
end

function UnitFake:getVelocity()
    return self.velocity or { x = 0, y = 0, z = 0 }
end

function UnitFake:getName()
    return self.name
end

function UnitFake:getTypeName()
    return self.typeName or "FAKE"
end

-- desc.category is how a consumer separates an aircraft from the AAA that shot
-- at it. Follows the owning group unless the unit spec overrides it.
function UnitFake:getDesc()
    return {
        category = self.category
            or (self.group and self.group.category)
            or Unit.Category.AIRPLANE,
    }
end

function UnitFake:hasAttribute(attr)
    return (self.attributes or {})[attr] == true
end

function UnitFake:inAir()
    return self.airborne == true
end

-- Internal fuel fraction, 0-1. Defaults full so a spec that does not care about
-- fuel still reads as a plausible aircraft.
function UnitFake:getFuel()
    return self.fuel or 1.0
end

function UnitFake:getCoalition()
    return self.side
end

function UnitFake:getGroup()
    return self.group
end

-- nil for AI; a per-unit spec {playerName = ...} models a human-crewed slot.
function UnitFake:getPlayerName()
    return self.playerName
end

-- Group-level controller: records setOnOff (the ground AI sleep lever). Extend with
-- setOption/setTask recording if a plugin under test needs them.
local ControllerFake = {}
ControllerFake.__index = ControllerFake

function ControllerFake:setOnOff(on)
    table.insert(Harness.records.aiOnOff, {
        group = self.group:getName(),
        on = on == true,
        t = Harness.now,
    })
end

function ControllerFake:setTask(task)
    local point = task and task.params and task.params.point
    table.insert(Harness.records.controllerTasks, {
        group = self.group:getName(),
        taskId = task and task.id,
        targetGroupId = task and task.params and task.params.groupId,
        x = point and point.x,
        y = point and point.y,
        t = Harness.now,
    })
end

-- Controller commands. `Start` is the only way to launch an UNCONTROLLED group
-- (Group:activate() does nothing to one), which is how a COLD AI flight at an
-- airfield is generated -- the shape §89 P5 was silently broken on.
function ControllerFake:setCommand(command)
    local id = command and command.id
    if id == "Start" then
        self.group.uncontrolled = nil
    end
    table.insert(Harness.records.controllerCommands, {
        group = self.group:getName(),
        commandId = id,
        t = Harness.now,
    })
end

function ControllerFake:resetTask()
    table.insert(Harness.records.controllerResets, {
        group = self.group:getName(),
        t = Harness.now,
    })
end

function ControllerFake:setOption(optionId, value)
    table.insert(Harness.records.options, {
        group = self.group:getName(),
        option = optionId,
        value = value,
        t = Harness.now,
    })
end

local GroupFake = {}
GroupFake.__index = GroupFake

function GroupFake:isExist()
    return self.exists ~= false
end

function GroupFake:getController()
    self.controller = self.controller or setmetatable({ group = self }, ControllerFake)
    return self.controller
end

function GroupFake:getName()
    return self.name
end

function GroupFake:getID()
    return self.id
end

-- DCS returns only the LIVING units, so a fixed index is not a fixed aircraft:
-- units[1] becomes a different jet once the lead dies. Modelling that is what
-- catches "sample the lead" bugs (the sortie recorder had one).
function GroupFake:getUnits()
    local alive = {}
    for _, unit in ipairs(self.units) do
        if unit:isExist() then
            table.insert(alive, unit)
        end
    end
    return alive
end

function GroupFake:getUnit(i)
    return self.units[i]
end

function GroupFake:getSize()
    return #self.units
end

function GroupFake:getCoalition()
    return self.side
end

-- Late-activation launch (the §89 P5 reactivered lever): recorded, and the
-- group reads as existing from then on. An `uncontrolled = true` group is
-- already in the world with its engines off, and DCS's activate() does nothing
-- to it -- modelled, because assuming otherwise is what left reactive red
-- unable to launch for five days (test 12, 2026-08-20).
function GroupFake:activate()
    if self.uncontrolled then
        return
    end
    self.exists = true
    table.insert(Harness.records.activations, self.name)
end

Group.getByName = function(name)
    return Harness.groupsByName[name]
end

-- Unit.getByName: the per-unit lookup the gpsjamming plugin uses so a jammer's
-- liveness is its own, not its group's.
Unit = Unit or {}
-- Real DCS exposes Unit.Category next to Group.Category; the two agree on the
-- AIRPLANE/HELICOPTER values a consumer uses to tell aircraft from everything else.
Unit.Category = Unit.Category
    or { AIRPLANE = 0, HELICOPTER = 1, GROUND_UNIT = 2, SHIP = 3, STRUCTURE = 4 }
Unit.getByName = function(name)
    return Harness.unitsByName[name]
end

-- spec = { name, side, category, units = { { name, type, x, z, alt, agl?, life,
-- exists, airborne, attributes = {...}, velocity = {x,y,z} }, ... } }
function Harness.addGroup(spec)
    local grp = setmetatable({
        name = spec.name,
        id = spec.id,
        side = spec.side,
        category = spec.category,
        exists = spec.exists,
        uncontrolled = spec.uncontrolled,
        units = {},
    }, GroupFake)
    for _, u in ipairs(spec.units or {}) do
        local unit = setmetatable({
            name = u.name,
            typeName = u.type,
            x = u.x,
            z = u.z,
            alt = u.alt or 0,
            life = u.life,
            exists = u.exists,
            airborne = u.airborne,
            attributes = u.attributes,
            velocity = u.velocity,
            playerName = u.playerName,
            fuel = u.fuel,
            category = u.category,
            side = spec.side,
            group = grp,
        }, UnitFake)
        table.insert(grp.units, unit)
        Harness.unitsByName[unit.name] = unit
    end
    Harness.groupsByName[spec.name] = grp
    Harness.groupsBySideCat[spec.side] = Harness.groupsBySideCat[spec.side] or {}
    local byCat = Harness.groupsBySideCat[spec.side]
    byCat[spec.category] = byCat[spec.category] or {}
    table.insert(byCat[spec.category], grp)
    return grp
end

-- Mutate a live unit's fields mid-test (teleport, airborne flip, velocity...):
-- the harness has no physics, so mover tests reposition units by hand.
function Harness.updateUnit(groupName, unitIndex, fields)
    local g = Harness.groupsByName[groupName]
    if not g then
        error("updateUnit: no such group " .. tostring(groupName))
    end
    local u = g.units[unitIndex]
    if not u then
        error(
            "updateUnit: no unit " .. tostring(unitIndex) .. " in " .. tostring(groupName)
        )
    end
    for k, v in pairs(fields) do
        u[k] = v
    end
end

coalition.getGroups = function(side, category)
    local byCat = Harness.groupsBySideCat[side]
    if not byCat then
        return {}
    end
    if category == nil then
        local all = {}
        for _, groups in pairs(byCat) do
            for _, g in ipairs(groups) do
                table.insert(all, g)
            end
        end
        return all
    end
    return byCat[category] or {}
end

-- Units currently crewed by a human (playerName set), DCS coalition.getPlayers shape.
coalition.getPlayers = function(side)
    local players = {}
    local byCat = Harness.groupsBySideCat[side]
    if byCat then
        for _, groups in pairs(byCat) do
            for _, g in ipairs(groups) do
                for _, u in ipairs(g:getUnits()) do
                    if u.playerName and u:isExist() then
                        table.insert(players, u)
                    end
                end
            end
        end
    end
    return players
end

coalition.addGroup = function(countryId, category, data)
    -- Late-spawn path (Super Gaggle et al.): register the group so subsequent
    -- Group.getByName / GROUP:FindByName lookups see it.
    local units = {}
    for _, u in ipairs((data or {}).units or {}) do
        table.insert(units, {
            name = u.name,
            type = u.type,
            x = u.x,
            z = u.y, -- mission-format y is east
            alt = u.alt,
            airborne = (u.alt or 0) > 0,
        })
    end
    return Harness.addGroup({
        name = (data or {}).name or ("spawned-" .. tostring(countryId)),
        side = Harness.countrySide and Harness.countrySide[countryId] or coalition.side.RED,
        category = category,
        units = units,
    })
end

-------------------------------------------------------------------------------
-- land / world / trigger / missionCommands
-------------------------------------------------------------------------------
land = {
    getHeight = function(_)
        return Harness.terrainHeight
    end,
    getIP = function(_, _, _)
        return nil
    end,
}

local eventHandlers = {}

world = {
    event = {
        S_EVENT_SHOT = 1,
        S_EVENT_HIT = 2,
        S_EVENT_DEAD = 8,
        S_EVENT_BIRTH = 15,
        S_EVENT_EJECTION = 6,
        S_EVENT_LAND = 4,
    },
    addEventHandler = function(handler)
        table.insert(eventHandlers, handler)
    end,
    getMarkPanels = function()
        return Harness.markPanels
    end,
}

function Harness.fireEvent(event)
    for _, h in ipairs(eventHandlers) do
        local ok, err = pcall(h.onEvent, h, event)
        if not ok then
            table.insert(Harness.records.errors, "event handler error: " .. tostring(err))
        end
    end
end

-------------------------------------------------------------------------------
-- Weapon fake for S_EVENT_SHOT tests. A released weapon that a plugin tracks to
-- impact: it exists until vanishAt (relative to the virtual clock), then the
-- tracker resolves its last sampled position as the impact point.
-------------------------------------------------------------------------------
local WeaponFake = {}
WeaponFake.__index = WeaponFake

function WeaponFake:isExist()
    if self.vanishAt and Harness.now >= self.vanishAt then
        return false
    end
    return self.exists ~= false
end

-- Weapon:getName() returns the object's runtime id in DCS, which is how a hit is
-- matched back to the shot that released it. Distinct per weapon, so a spec that
-- fires twice gets two keys.
function WeaponFake:getName()
    return self.name or tostring(self.id_ or "weapon")
end

function WeaponFake:getTypeName()
    return self.typeName or "FAKE_WPN"
end

-- A released weapon FLIES: its position integrates its velocity from the moment of
-- release, so a plugin that gates on altitude (the GPS-jamming terminal gate) sees a
-- store actually descend. A weapon with no velocity (the default) never moves, so
-- every pre-existing test is unaffected.
function WeaponFake:getPoint()
    local x, y, z = self.x or 0, self.alt or 0, self.z or 0
    local v = self.velocity
    if v then
        local dt = Harness.now - (self.bornAt or 0)
        x = x + (v.x or 0) * dt
        y = y + (v.y or 0) * dt
        z = z + (v.z or 0) * dt
    end
    return { x = x, y = y, z = z }
end

function WeaponFake:getVelocity()
    return self.velocity or { x = 0, y = 0, z = 0 }
end

-- Weapon:getDesc() -- the gpsjamming plugin reads desc.warhead.explosiveMass so a
-- miss detonates with the store's own warhead. A spec with no warhead models the
-- thin-descriptor case (a mod store), which must fall back to the flat power.
function WeaponFake:getDesc()
    if self.warhead == nil then
        return {}
    end
    return { warhead = self.warhead }
end

-- Weapon:getTarget() -- the unit a guided shot is aimed at (nil for dumb ordnance),
-- set via fireShot's optional `target` group name.
function WeaponFake:getTarget()
    return self.target
end

-- Object:destroy() -- removes the weapon from the world (the growler plugin's
-- missile spoof). Recorded so tests can assert the spoof fired.
function WeaponFake:destroy()
    self.exists = false
    table.insert(
        Harness.records.weaponDestroys,
        { name = self:getTypeName(), t = Harness.now }
    )
end

function Harness.makeWeapon(spec)
    return setmetatable({
        -- Distinct per weapon: a hit is matched back to its shot by this key.
        name = spec.name,
        typeName = spec.typeName,
        x = spec.x,
        z = spec.z,
        alt = spec.alt,
        velocity = spec.velocity,
        exists = spec.exists,
        vanishAt = spec.vanishAt,
        warhead = spec.warhead,
        bornAt = Harness.now,
    }, WeaponFake)
end

-- Fire an S_EVENT_SHOT. spec = { weapon = { typeName, x, z, alt, velocity, vanishAt },
-- initiator = "<group name>", target = "<group name>" } -- the group's first unit is the
-- shooter; target (optional) sets weapon:getTarget() to that group's first unit, the DCS
-- shape a guided anti-ship/AG shot carries.
function Harness.fireShot(spec)
    local initiator = nil
    local g = spec.initiator and Harness.groupsByName[spec.initiator] or nil
    if g then
        initiator = g:getUnit(1)
    end
    local weapon = Harness.makeWeapon(spec.weapon or {})
    local tg = spec.target and Harness.groupsByName[spec.target] or nil
    if tg then
        weapon.target = tg:getUnit(1)
    end
    Harness.fireEvent({
        id = world.event.S_EVENT_SHOT,
        weapon = weapon,
        initiator = initiator,
    })
end

-- Fire an S_EVENT_BIRTH for a group's first unit (the slotting pilot). The unit
-- object is the real UnitFake, so getGroup()/getPlayerName()/getID() work.
function Harness.fireBirth(groupName)
    local g = Harness.groupsByName[groupName]
    Harness.fireEvent({
        id = world.event.S_EVENT_BIRTH,
        initiator = g and g:getUnit(1) or nil,
    })
end

-- Fire an S_EVENT_HIT on a group's first unit (the victim). The target is the
-- real UnitFake, so getGroup()/getName() work in the handler.
function Harness.fireHit(groupName)
    local g = Harness.groupsByName[groupName]
    Harness.fireEvent({
        id = world.event.S_EVENT_HIT,
        target = g and g:getUnit(1) or nil,
    })
end

-- Fire an S_EVENT_DEAD for a registered unit (by UNIT name). The initiator is
-- the real UnitFake, matching DCS's dead-event shape, so handlers that pcall
-- initiator:getName() see the true name.
function Harness.fireDead(unitName)
    Harness.fireEvent({
        id = world.event.S_EVENT_DEAD,
        initiator = Harness.unitsByName[unitName],
    })
end

-- Fire an S_EVENT_LAND for a group's first unit (the aircraft touching down).
-- The initiator is the real UnitFake so getGroup():getName() works in the handler,
-- which is how the recon plugin matches a landing back to its pending BDA cue.
function Harness.fireLand(groupName)
    local g = Harness.groupsByName[groupName]
    Harness.fireEvent({
        id = world.event.S_EVENT_LAND,
        initiator = g and g:getUnit(1) or nil,
    })
end

trigger = {
    smokeColor = { Green = 0, Red = 1, White = 2, Orange = 3, Blue = 4 },
    action = {
        explosion = function(point, power)
            table.insert(Harness.records.explosions, {
                x = point.x,
                y = point.y,
                z = point.z,
                power = power,
                t = Harness.now,
            })
        end,
        smoke = function(point, color)
            table.insert(Harness.records.smokes, {
                x = point.x,
                y = point.y,
                z = point.z,
                color = color,
                t = Harness.now,
            })
        end,
        effectSmokeBig = function(point, preset, density, name)
            table.insert(Harness.records.bigSmokes, {
                x = point.x,
                y = point.y,
                z = point.z,
                preset = preset,
                density = density,
                name = name,
                t = Harness.now,
            })
        end,
        effectSmokeStop = function(name)
            table.insert(Harness.records.stoppedEffects, name)
        end,
        stopEffect = function(name)
            table.insert(Harness.records.stoppedEffects, name)
        end,
        outTextForCoalition = function(side, text, duration)
            table.insert(Harness.records.texts, {
                side = side,
                text = tostring(text),
                duration = duration,
                t = Harness.now,
            })
        end,
        outText = function(text, duration)
            table.insert(Harness.records.texts, {
                side = -1,
                text = tostring(text),
                duration = duration,
                t = Harness.now,
            })
        end,
        outTextForGroup = function(groupId, text, duration, clearview)
            table.insert(Harness.records.texts, {
                groupId = groupId,
                text = tostring(text),
                duration = duration,
                clearview = clearview,
                t = Harness.now,
            })
        end,
        outSoundForGroup = function(groupId, file)
            table.insert(Harness.records.sounds, {
                groupId = groupId,
                file = tostring(file),
                t = Harness.now,
            })
        end,
        markToCoalition = function(id, text, point, side)
            table.insert(Harness.records.marks, {
                id = id,
                text = tostring(text),
                x = point.x,
                y = point.y,
                z = point.z,
                side = side,
                t = Harness.now,
            })
        end,
        -- F10 map text. Recorded for the same reason as markupToAll: the label
        -- is what tells a pilot what a drawn border IS without hovering it.
        textToAll = function(coalition, id, point, color, fillColor, fontSize, readOnly, text)
            table.insert(Harness.records.mapTexts, {
                coalition = coalition,
                id = id,
                x = point and point.x,
                z = point and point.z,
                color = color,
                fill = fillColor,
                fontSize = fontSize,
                text = tostring(text),
            })
        end,
        -- Freeform/shape drawing. Recorded rather than ignored because the F10
        -- border draw is the half of §96 a player sees before ever entering a
        -- polygon, and it failed silently once already.
        markupToAll = function(...)
            local args = { ... }
            local points, color, fill, lineType = {}, nil, nil, nil
            for i = 4, #args do
                local a = args[i]
                if type(a) == "table" and a.x ~= nil then
                    points[#points + 1] = { x = a.x, y = a.y, z = a.z }
                elseif type(a) == "table" and color == nil then
                    color = a
                elseif type(a) == "table" then
                    fill = a
                elseif type(a) == "number" then
                    lineType = a
                end
            end
            table.insert(Harness.records.markups, {
                shape = args[1],
                coalition = args[2],
                id = args[3],
                points = points,
                color = color,
                fill = fill,
                lineType = lineType,
                t = Harness.now,
            })
        end,
        removeMark = function(id)
            table.insert(Harness.records.removedMarks, id)
        end,
        radioTransmission = function(file, point, modulation, loop, frequency, power, name)
            table.insert(Harness.records.radioTransmissions, {
                file = tostring(file),
                x = point.x,
                y = point.y,
                z = point.z,
                mod = modulation,
                loop = loop,
                hz = frequency,
                power = power,
                name = name and tostring(name) or nil,
                t = Harness.now,
            })
        end,
        stopRadioTransmission = function(name)
            table.insert(Harness.records.stoppedTransmissions, tostring(name))
        end,
    },
}

-------------------------------------------------------------------------------
-- StaticObject: placed statics by name. Tests register them via
-- Harness.addStatic{ name = ..., exists = true|false }; getByName returns nil
-- for anything unregistered (a culled / never-spawned / scenery object).
-------------------------------------------------------------------------------
local staticsByName = {}

StaticObject = {
    getByName = function(name)
        return staticsByName[name]
    end,
}

function Harness.addStatic(spec)
    staticsByName[spec.name] = {
        isExist = function(self)
            return not self.destroyed and spec.exists ~= false
        end,
        destroy = function(self)
            self.destroyed = true
            staticsByName[spec.name] = nil
            table.insert(Harness.records.destroyedStatics, spec.name)
        end,
    }
end

missionCommands = {
    addSubMenuForCoalition = function(side, name, parent)
        table.insert(Harness.records.menus, { side = side, path = tostring(name) })
        return { name }
    end,
    addCommandForCoalition = function(side, name, parent, fn, arg)
        table.insert(Harness.records.menus, { side = side, path = tostring(name), fn = fn, arg = arg })
        return { name }
    end,
    removeItemForCoalition = function(_, _) end,
    addSubMenuForGroup = function(gid, name, parent)
        table.insert(Harness.records.menus, { gid = gid, path = tostring(name) })
        return { name }
    end,
    addCommandForGroup = function(gid, name, parent, fn, arg)
        table.insert(Harness.records.menus, { gid = gid, path = tostring(name), fn = fn, arg = arg })
        return { name }
    end,
    removeItemForGroup = function(_, _) end,
}

-------------------------------------------------------------------------------
-- Minimal MOOSE facade (only the surface the plugins under test touch).
-- Wraps the fake groups/units above -- NOT the real Moose.lua.
-------------------------------------------------------------------------------
local MooseCoord = {}
MooseCoord.__index = MooseCoord

function MooseCoord:GetVec2()
    return { x = self.x, y = self.z } -- MOOSE Vec2: x = north, y = east
end

function MooseCoord:GetLandHeight()
    return Harness.terrainHeight
end

local MooseUnit = {}
MooseUnit.__index = MooseUnit

function MooseUnit:IsAlive()
    return self.unit:isExist() and self.unit:getLife() > 0
end

function MooseUnit:GetCoordinate()
    local p = self.unit:getPoint()
    return setmetatable({ x = p.x, y = p.y, z = p.z }, MooseCoord)
end

function MooseUnit:GetCoalition()
    return self.unit:getCoalition()
end

local MooseGroup = {}
MooseGroup.__index = MooseGroup

function MooseGroup:IsAlive()
    if not self.group:isExist() then
        return false
    end
    for _, u in ipairs(self.group:getUnits()) do
        if u:isExist() and u:getLife() > 0 then
            return true
        end
    end
    return false
end

function MooseGroup:GetUnit(i)
    local u = self.group:getUnit(i)
    if not u then
        return nil
    end
    return setmetatable({ unit = u }, MooseUnit)
end

function MooseGroup:GetCoordinate()
    local u = self.group:getUnit(1)
    if not u then
        return nil
    end
    local p = u:getPoint()
    return setmetatable({ x = p.x, y = p.y, z = p.z }, MooseCoord)
end

function MooseGroup:GetCoalition()
    return self.group:getCoalition()
end

function MooseGroup:TaskFireAtPoint(vec2, radius, rounds, weaponType)
    return { point = vec2, radius = radius, rounds = rounds, weaponType = weaponType }
end

function MooseGroup:PushTask(task, _)
    table.insert(Harness.records.firedTasks, {
        group = self.group:getName(),
        x = task.point.x,
        y = task.point.y,
        radius = task.radius,
        rounds = task.rounds,
        weaponType = task.weaponType,
        t = Harness.now,
    })
end

GROUP = {}

function GROUP.FindByName(_, name)
    local g = Harness.groupsByName[name]
    if not g then
        return nil
    end
    return setmetatable({ group = g }, MooseGroup)
end

function MooseGroup:GetName()
    return self.group:getName()
end

function MooseGroup:OptionROEWeaponFree()
    table.insert(Harness.records.roe, {
        group = self.group:getName(),
        option = "WeaponFree",
        t = Harness.now,
    })
end

function MooseGroup:OptionROTEvadeFire()
    table.insert(Harness.records.roe, {
        group = self.group:getName(),
        option = "EvadeFire",
        t = Harness.now,
    })
end

function MooseGroup:OptionROEReturnFire()
    table.insert(Harness.records.roe, {
        group = self.group:getName(),
        option = "ReturnFire",
        t = Harness.now,
    })
end

-- neutralborder shadow vectoring: record the fly-to point, no movement model.
function MooseGroup:RouteToVec3(point, speed)
    table.insert(Harness.records.routes, {
        group = self.group:getName(),
        x = point.x,
        y = point.y,
        z = point.z,
        speed = speed,
        t = Harness.now,
    })
end

function MooseGroup:Destroy(_)
    local name = self.group:getName()
    table.insert(Harness.records.destroys, name)
    Harness.groupsByName[name] = nil
end

UNIT = {}

function UNIT.FindByName(_, name)
    for _, g in pairs(Harness.groupsByName) do
        for _, u in ipairs(g:getUnits()) do
            if u:getName() == name then
                return setmetatable({ unit = u }, MooseUnit)
            end
        end
    end
    return nil
end

-------------------------------------------------------------------------------
-- ZONE_POLYGON: only the surface §96 touches. DCS will not fill a concave
-- freeform, so the plugin hands the ring to MOOSE, whose ReFill triangulates.
-- The triangulation is MOOSE's business and is not modelled here; what IS
-- pinned is that the plugin asks for the fill at all, and with what.
ZONE_POLYGON = {}
ZONE_POLYGON.__index = ZONE_POLYGON

function ZONE_POLYGON:NewFromPointsArray(name, points)
    local copy = {}
    for i = 1, #points do
        copy[i] = { x = points[i].x, y = points[i].y }
    end
    return setmetatable({ name = name, points = copy, coalition = nil }, ZONE_POLYGON)
end

function ZONE_POLYGON:SetDrawCoalition(side)
    self.coalition = side
    return self
end

function ZONE_POLYGON:ReFill(color, alpha)
    table.insert(Harness.records.zoneFills, {
        name = self.name,
        points = self.points,
        coalition = self.coalition,
        color = color,
        alpha = alpha,
    })
    return self
end

-- AIRBASE / SPAWN fakes (MOOSE surface for the redscramble plugin). Airbases
-- are registered by tests via Harness.addAirbase{ name, x, z, elev, side };
-- SPAWN:SpawnAtAirbase records the spawn and synthesizes a real harness group
-- (units at the airbase, airborne when Takeoff.Air) so the plugin's own vector
-- loop can find and task it.
-------------------------------------------------------------------------------
local AirbaseFake = {}
AirbaseFake.__index = AirbaseFake

function AirbaseFake:GetVec2()
    return { x = self.x, y = self.z } -- MOOSE Vec2: x = north, y = east
end

function AirbaseFake:GetCoordinate()
    return setmetatable({ x = self.x, y = self.elev or 0, z = self.z }, MooseCoord)
end

function AirbaseFake:GetCoalition()
    return self.side
end

AIRBASE = {}

function AIRBASE.FindByName(_, name)
    return Harness.airbases[name]
end

function Harness.addAirbase(spec)
    Harness.airbases[spec.name] = setmetatable({
        name = spec.name,
        x = spec.x or 0,
        z = spec.z or 0,
        elev = spec.elev or 0,
        side = spec.side,
    }, AirbaseFake)
end

SPAWN = { Takeoff = { Air = 1, Runway = 2, Hot = 3, Cold = 4 } }

local SpawnFake = {}
SpawnFake.__index = SpawnFake

function SPAWN.NewWithAlias(_, template, alias)
    return setmetatable({
        template = template,
        alias = alias,
        counter = 0,
        grouping = 2,
        speedKt = nil,
        countryId = nil,
        coalitionId = nil,
    }, SpawnFake)
end

function SpawnFake:InitGrouping(n)
    self.grouping = n
    return self
end

function SpawnFake:InitSpeedKnots(kt)
    self.speedKt = kt
    return self
end

-- Spawn-time coalition choice (neutralborder): the clone joins the given
-- country/coalition, like MOOSE's template CountryID/CoalitionID override.
function SpawnFake:InitCountry(id)
    self.countryId = id
    return self
end

function SpawnFake:InitCoalition(side)
    self.coalitionId = side
    return self
end

local nextSpawnGroupId = 9000

function SpawnFake:SpawnAtAirbase(airbase, takeoff, altitude)
    self.counter = self.counter + 1
    local name = self.alias .. "#" .. string.format("%03d", self.counter)
    table.insert(Harness.records.spawns, {
        template = self.template,
        alias = self.alias,
        base = airbase and airbase.name or "?",
        takeoff = takeoff,
        altitude = altitude,
        grouping = self.grouping,
        speedKt = self.speedKt,
        countryId = self.countryId,
        coalitionId = self.coalitionId,
        t = Harness.now,
    })
    nextSpawnGroupId = nextSpawnGroupId + 1
    local units = {}
    for i = 1, self.grouping do
        units[#units + 1] = {
            name = name .. "-" .. i,
            type = "FAKE_FIGHTER",
            x = airbase and airbase.x or 0,
            z = airbase and airbase.z or 0,
            alt = altitude or 0,
            airborne = takeoff == SPAWN.Takeoff.Air,
        }
    end
    local grp = Harness.addGroup({
        name = name,
        id = nextSpawnGroupId,
        side = self.coalitionId or coalition.side.RED,
        category = Group.Category.AIRPLANE,
        units = units,
    })
    return setmetatable({ group = grp }, MooseGroup)
end

-- Air-spawn at an arbitrary coordinate (neutralborder point-spawned CAP, for a
-- neutral with no airfield on the map). MOOSE takes altitude as the Vec3 y.
function SpawnFake:SpawnFromVec3(vec3)
    self.counter = self.counter + 1
    local name = self.alias .. "#" .. string.format("%03d", self.counter)
    table.insert(Harness.records.spawns, {
        template = self.template,
        alias = self.alias,
        base = "point",
        x = vec3.x,
        z = vec3.z,
        altitude = vec3.y,
        grouping = self.grouping,
        speedKt = self.speedKt,
        countryId = self.countryId,
        coalitionId = self.coalitionId,
        t = Harness.now,
    })
    nextSpawnGroupId = nextSpawnGroupId + 1
    local units = {}
    for i = 1, self.grouping do
        units[#units + 1] = {
            name = name .. "-" .. i,
            type = "FAKE_FIGHTER",
            x = vec3.x,
            z = vec3.z,
            alt = vec3.y,
            airborne = true,
        }
    end
    local grp = Harness.addGroup({
        name = name,
        id = nextSpawnGroupId,
        side = self.coalitionId or coalition.side.RED,
        category = Group.Category.AIRPLANE,
        units = units,
    })
    return setmetatable({ group = grp }, MooseGroup)
end

-- In-place clone at the template's own position (neutralborder SAM wake):
-- MOOSE SPAWN:Spawn() spawns the next group where the template stands.
function SpawnFake:Spawn()
    self.counter = self.counter + 1
    local name = self.alias .. "#" .. string.format("%03d", self.counter)
    table.insert(Harness.records.spawns, {
        template = self.template,
        alias = self.alias,
        base = "template",
        takeoff = nil,
        altitude = nil,
        grouping = self.grouping,
        countryId = self.countryId,
        coalitionId = self.coalitionId,
        t = Harness.now,
    })
    nextSpawnGroupId = nextSpawnGroupId + 1
    local grp = Harness.addGroup({
        name = name,
        id = nextSpawnGroupId,
        side = self.coalitionId or coalition.side.RED,
        category = Group.Category.GROUND,
        units = { { name = name .. "-1", type = "FAKE_SAM", x = 0, z = 0 } },
    })
    return setmetatable({ group = grp }, MooseGroup)
end
