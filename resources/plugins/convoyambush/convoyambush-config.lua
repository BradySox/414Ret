---------------------------------------------------------------------------------------------------
-- Convoy ambush runtime (spring the dug-in team).
--
-- Each emitted ambush team holds fire (alarm-green + weapons hold) until the friendly convoy it is
-- set against closes inside the trigger radius, then SPRINGS: goes weapons-free (alarm-red) with a
-- "troops in contact" cue + an F10 map mark. A team no convoy ever reaches opens up anyway after a
-- maximum hold, so a passing player always finds a fight. Springing begins only after a startup
-- grace so nothing opens up the instant the mission loads.
--
-- ROE / cue ONLY -- the plugin owns no kills. The convoy and the ambushers are real, tracked units,
-- so the firefight is reconciled natively at debrief (dead convoy units never arrive; dead
-- ambushers are a real enemy ground loss). This script only decides WHEN the dug-in team opens up.
-- Reads dcsRetribution.convoyAmbush, emitted by game/missiongenerator/convoyambushluadata.py; inert
-- when that node is absent. pcall-guarded throughout so a hiccup never takes the mission down.
-- Definition order matters (Lua 5.1): helpers precede use.
---------------------------------------------------------------------------------------------------

if not (dcsRetribution and dcsRetribution.convoyAmbush) then
    return
end

local data = dcsRetribution.convoyAmbush

-- Defaults (metric). Overridable via the plugin options (dcsRetribution.plugins.convoyambush).
local TRIGGER_RADIUS = 6000 -- m: convoy within this of the ambush centre springs it
local GRACE = 120 -- s before an ambush can spring
local POLL = 15 -- s between convoy-proximity checks
local MAX_HOLD = 1800 -- s: spring anyway after this even if no convoy closes

if dcsRetribution.plugins and dcsRetribution.plugins.convoyambush then
    local o = dcsRetribution.plugins.convoyambush
    TRIGGER_RADIUS = tonumber(o.triggerRadiusM) or TRIGGER_RADIUS
    GRACE = tonumber(o.startGraceS) or GRACE
    POLL = tonumber(o.pollIntervalS) or POLL
    MAX_HOLD = tonumber(o.maxHoldS) or MAX_HOLD
end

local markSeq = 73100 -- F10 mark id base (bumped per ambush; high to avoid collisions)

local function num(v)
    return tonumber(v) or 0
end

-- Every alive group named in a list (the ambush team, or the escorted convoy).
local function aliveGroups(names)
    local out = {}
    if type(names) ~= "table" then
        return out
    end
    for _, name in ipairs(names) do
        local g = Group.getByName(name)
        if g and g:isExist() and g:getSize() > 0 then
            out[#out + 1] = g
        end
    end
    return out
end

-- Set the whole team's ROE: hold = dug-in and silent (alarm-green, weapons hold); otherwise
-- sprung (alarm-red, weapons free). pcall-wrapped -- a controller/AI hiccup must never abort.
local function setHold(group, hold)
    pcall(function()
        local con = group:getController()
        if not con then
            return
        end
        if hold then
            con:setOption(
                AI.Option.Ground.id.ALARM_STATE,
                AI.Option.Ground.val.ALARM_STATE.GREEN
            )
            con:setOption(AI.Option.Ground.id.ROE, AI.Option.Ground.val.ROE.WEAPON_HOLD)
        else
            con:setOption(
                AI.Option.Ground.id.ALARM_STATE,
                AI.Option.Ground.val.ALARM_STATE.RED
            )
            con:setOption(AI.Option.Ground.id.ROE, AI.Option.Ground.val.ROE.WEAPON_FREE)
        end
    end)
end

-- Nearest distance (m) from the ambush centre (x = north, y = east) to any alive convoy unit,
-- or nil if the convoy has no live unit / no convoyGroups. getPoint: x = north, z = east.
local function nearestConvoyDist(ambush)
    local best = nil
    local cx, cy = num(ambush.x), num(ambush.y)
    for _, g in ipairs(aliveGroups(ambush.convoyGroups)) do
        pcall(function()
            for _, u in ipairs(g:getUnits() or {}) do
                if u and u:isExist() then
                    local p = u:getPoint()
                    if p then
                        local dx, dy = cx - p.x, cy - p.z
                        local d = math.sqrt(dx * dx + dy * dy)
                        if not best or d < best then
                            best = d
                        end
                    end
                end
            end
        end)
    end
    return best
end

-- Spring the ambush: team goes weapons-free, one cue to the player, one F10 mark on the position.
local function spring(ambush)
    for _, g in ipairs(aliveGroups(ambush.groups)) do
        setHold(g, false)
    end
    pcall(
        trigger.action.outTextForCoalition,
        coalition.side.BLUE,
        "TROOPS IN CONTACT -- a friendly convoy is under ambush. Escort needed.",
        20
    )
    pcall(function()
        local cx, cy = num(ambush.x), num(ambush.y)
        local h = land.getHeight({ x = cx, y = cy }) or 0
        trigger.action.markToCoalition(
            ambush._markId,
            "Convoy ambush",
            { x = cx, y = h, z = cy },
            coalition.side.BLUE,
            false,
            nil
        )
    end)
end

-- One ambush team: dig in holding fire after the grace, then poll for the convoy closing (or the
-- max hold elapsing) and spring once. A team wiped before it springs just stops scheduling.
local function startAmbush(ambush)
    markSeq = markSeq + 1
    ambush._markId = markSeq
    for _, g in ipairs(aliveGroups(ambush.groups)) do
        setHold(g, true)
    end

    local sprung = false
    local deadline = timer.getTime() + GRACE + MAX_HOLD
    local function tick()
        if sprung then
            return nil
        end
        if #aliveGroups(ambush.groups) == 0 then
            return nil -- team destroyed before it sprang -> stop scheduling
        end
        local dist = nearestConvoyDist(ambush)
        if (dist and dist <= TRIGGER_RADIUS) or timer.getTime() >= deadline then
            sprung = true
            spring(ambush)
            return nil
        end
        return timer.getTime() + POLL
    end
    timer.scheduleFunction(tick, {}, timer.getTime() + GRACE)
end

local ok, err = pcall(function()
    local count = 0
    if type(data.ambushes) == "table" then
        for _, ambush in ipairs(data.ambushes) do
            startAmbush(ambush)
            count = count + 1
        end
    end
    env.info(string.format("CONVOYAMBUSH|: armed %d ambush(es)", count))
end)
if not ok then
    env.error("CONVOYAMBUSH|: setup error: " .. tostring(err))
end
