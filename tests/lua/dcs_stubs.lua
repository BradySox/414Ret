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
        radioTransmissions = {}, -- { file, x, y, z, mod, loop, hz, power, name, t }
        stoppedTransmissions = {}, -- transmission names

        infos = {},
        warnings = {},
        errors = {}, -- env.error + errors escaping scheduled functions
    },
    groupsByName = {},
    groupsBySideCat = {}, -- [side][category] -> list
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

function UnitFake:hasAttribute(attr)
    return (self.attributes or {})[attr] == true
end

function UnitFake:inAir()
    return self.airborne == true
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

local GroupFake = {}
GroupFake.__index = GroupFake

function GroupFake:isExist()
    return self.exists ~= false
end

function GroupFake:getName()
    return self.name
end

function GroupFake:getID()
    return self.id
end

function GroupFake:getUnits()
    return self.units
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

Group.getByName = function(name)
    return Harness.groupsByName[name]
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
            side = spec.side,
            group = grp,
        }, UnitFake)
        table.insert(grp.units, unit)
    end
    Harness.groupsByName[spec.name] = grp
    Harness.groupsBySideCat[spec.side] = Harness.groupsBySideCat[spec.side] or {}
    local byCat = Harness.groupsBySideCat[spec.side]
    byCat[spec.category] = byCat[spec.category] or {}
    table.insert(byCat[spec.category], grp)
    return grp
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

function WeaponFake:getTypeName()
    return self.typeName or "FAKE_WPN"
end

function WeaponFake:getPoint()
    return { x = self.x or 0, y = self.alt or 0, z = self.z or 0 }
end

function WeaponFake:getVelocity()
    return self.velocity or { x = 0, y = 0, z = 0 }
end

function Harness.makeWeapon(spec)
    return setmetatable({
        typeName = spec.typeName,
        x = spec.x,
        z = spec.z,
        alt = spec.alt,
        velocity = spec.velocity,
        exists = spec.exists,
        vanishAt = spec.vanishAt,
    }, WeaponFake)
end

-- Fire an S_EVENT_SHOT. spec = { weapon = { typeName, x, z, alt, velocity, vanishAt },
-- initiator = "<group name>" } -- the group's first unit is the shooter.
function Harness.fireShot(spec)
    local initiator = nil
    local g = spec.initiator and Harness.groupsByName[spec.initiator] or nil
    if g then
        initiator = g:getUnit(1)
    end
    Harness.fireEvent({
        id = world.event.S_EVENT_SHOT,
        weapon = Harness.makeWeapon(spec.weapon or {}),
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
        isExist = function(_)
            return spec.exists ~= false
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

function MooseGroup:TaskFireAtPoint(vec2, radius, rounds)
    return { point = vec2, radius = radius, rounds = rounds }
end

function MooseGroup:PushTask(task, _)
    table.insert(Harness.records.firedTasks, {
        group = self.group:getName(),
        x = task.point.x,
        y = task.point.y,
        radius = task.radius,
        rounds = task.rounds,
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
