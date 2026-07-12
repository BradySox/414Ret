---------------------------------------------------------------------------------------------------
-- Ground AI sleep runtime (performance).
--
-- Each emitted garrison vehicle group has its DCS controller switched off while no aircraft is
-- inside the wake radius, and switched back on when one closes. A sleeping group keeps existing --
-- it renders, it can be found and killed, death events fire like any other unit -- it just stops
-- running sensors/targeting, which is where the sim cost of hundreds of rear-area ground units
-- actually goes.
--
-- Eligibility is decided by the GENERATOR (game/missiongenerator/aisleepluadata.py), never here:
-- only rear-area garrison ("armor" category) groups are emitted; the air-defense network, the
-- front line, convoys and every scripted mover are excluded in Python by construction. Reads
-- dcsRetribution.aiSleep; inert when that node is absent. pcall-guarded throughout so a hiccup
-- never takes the mission down. Definition order matters (Lua 5.1): helpers precede use.
---------------------------------------------------------------------------------------------------

if not (dcsRetribution and dcsRetribution.aiSleep) then
    return
end

local data = dcsRetribution.aiSleep

-- Defaults. Overridable via the plugin options (dcsRetribution.plugins.aisleep).
local WAKE_RADIUS_NM = 15 -- aircraft inside this range wake a group
local POLL = 30 -- s between sleep/wake checks
local GRACE = 60 -- s before the first sleep pass

if dcsRetribution.plugins and dcsRetribution.plugins.aisleep then
    local o = dcsRetribution.plugins.aisleep
    WAKE_RADIUS_NM = tonumber(o.wakeRadiusNm) or WAKE_RADIUS_NM
    POLL = tonumber(o.pollIntervalS) or POLL
    GRACE = tonumber(o.startGraceS) or GRACE
end

-- Floor the wake radius at 10 NM: a garrison may carry embedded SHORAD/MANPAD escorts, and the
-- group must be awake long before anything enters their engagement envelope.
if WAKE_RADIUS_NM < 10 then
    WAKE_RADIUS_NM = 10
end

local WAKE_M = WAKE_RADIUS_NM * 1852
-- Sleep hysteresis: only put a group back to sleep once the nearest aircraft is 25% beyond the
-- wake radius, so an orbit riding the boundary doesn't flap the controller every poll.
local SLEEP_M = WAKE_M * 1.25
local WAKE_M2 = WAKE_M * WAKE_M
local SLEEP_M2 = SLEEP_M * SLEEP_M

-- managed[groupName] = { asleep = <bool> }. Everything starts awake (the DCS default); the
-- first pass after the grace sleeps whatever has an empty sky.
local managed = {}

local function setAI(group, on)
    pcall(function()
        local con = group:getController()
        if con then
            con:setOnOff(on)
        end
    end)
end

-- Every airborne aircraft position (either side, human or AI): a sleeping garrison must wake
-- for an inbound AI strike exactly as it does for a player.
local function airbornePoints()
    local pts = {}
    local sides = { coalition.side.NEUTRAL, coalition.side.RED, coalition.side.BLUE }
    local cats = { Group.Category.AIRPLANE, Group.Category.HELICOPTER }
    for _, side in ipairs(sides) do
        for _, cat in ipairs(cats) do
            local ok, groups = pcall(coalition.getGroups, side, cat)
            if ok and groups then
                for _, grp in ipairs(groups) do
                    if grp and grp:isExist() then
                        for _, u in ipairs(grp:getUnits()) do
                            if u and u:isExist() and u:inAir() then
                                local p = u:getPoint()
                                pts[#pts + 1] = { x = p.x, z = p.z }
                            end
                        end
                    end
                end
            end
        end
    end
    return pts
end

-- Squared 2D distance from a group's lead unit to the nearest airborne aircraft, with an
-- early-out inside the wake radius (the common "somebody is overhead" case).
local function nearestAir2(group, pts)
    local lead = group:getUnit(1)
    if not (lead and lead:isExist()) then
        return nil
    end
    local p = lead:getPoint()
    local best = math.huge
    for _, a in ipairs(pts) do
        local dx, dz = a.x - p.x, a.z - p.z
        local d2 = dx * dx + dz * dz
        if d2 < best then
            best = d2
            if best < WAKE_M2 then
                return best
            end
        end
    end
    return best
end

local function tick()
    local pts = airbornePoints()
    local remaining = 0
    for name, state in pairs(managed) do
        local g = Group.getByName(name)
        if not (g and g:isExist() and g:getSize() > 0) then
            managed[name] = nil -- dead group: nothing left to manage
        else
            remaining = remaining + 1
            local d2 = nearestAir2(g, pts)
            if d2 then
                if state.asleep and d2 < WAKE_M2 then
                    setAI(g, true)
                    state.asleep = false
                elseif not state.asleep and d2 > SLEEP_M2 then
                    setAI(g, false)
                    state.asleep = true
                end
            end
        end
    end
    if remaining == 0 then
        return nil -- everything managed is dead: stop polling
    end
    return timer.getTime() + POLL
end

-- pcall-guarded: an error in a scheduled tick otherwise kills the loop silently for the rest
-- of the mission (log + retry instead).
local function guarded()
    local ok, result = pcall(tick)
    if not ok then
        env.warning("AISLEEP|: poll error (retrying): " .. tostring(result))
        return timer.getTime() + POLL
    end
    return result
end

-- A hit wakes the victim immediately, whatever the range -- a standoff shot from beyond the
-- wake radius must never land on a group that cannot react.
local hitHandler = {}
function hitHandler:onEvent(event)
    if not event or event.id ~= world.event.S_EVENT_HIT then
        return
    end
    pcall(function()
        local target = event.target
        if not (target and target.getGroup) then
            return
        end
        local grp = target:getGroup()
        if not grp then
            return
        end
        local state = managed[grp:getName()]
        if state and state.asleep then
            setAI(grp, true)
            state.asleep = false
        end
    end)
end

local ok, err = pcall(function()
    local count = 0
    if type(data.groups) == "table" then
        for _, name in ipairs(data.groups) do
            managed[name] = { asleep = false }
            count = count + 1
        end
    end
    if count > 0 then
        world.addEventHandler(hitHandler)
        timer.scheduleFunction(guarded, {}, timer.getTime() + GRACE)
    end
    env.info(string.format(
        "AISLEEP|: managing %d garrison group(s), wake radius %d NM, poll %ds",
        count, WAKE_RADIUS_NM, POLL))
end)
if not ok then
    env.error("AISLEEP|: setup error: " .. tostring(err))
end
