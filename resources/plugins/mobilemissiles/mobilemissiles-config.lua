---------------------------------------------------------------------------------------------------
-- Mobile missile relocation runtime (the SCUD hunt).
--
-- Each emitted theater-missile site's vehicle group(s) drive shoot-and-scoot: on a cadence, they
-- relocate to a fresh random point within the scoot radius of the site's campaign-map position, so
-- the launcher is never quite where the last recon photo froze it. Alarm-green + weapons hold while
-- moving -- they relocate, they don't stop to fight.
--
-- Movement ONLY. Kills record natively (the routed DCS group is the force model's own), the site
-- never migrates beyond the scoot radius (threat rings and the turn-boundary model stay honest),
-- and a dead site just stops being routed. Reads dcsRetribution.mobileMissiles, emitted by
-- game/missiongenerator/mobilemissileluadata.py; inert when that node is absent. pcall-guarded
-- throughout so a hiccup never takes the mission down. Definition order matters (Lua 5.1):
-- helpers precede use.
---------------------------------------------------------------------------------------------------

if not (dcsRetribution and dcsRetribution.mobileMissiles and mist) then
    return
end

local data = dcsRetribution.mobileMissiles

-- Defaults (metric). Overridable via the plugin options (dcsRetribution.plugins.mobilemissiles).
local INTERVAL = 480 -- s between relocations
local RADIUS = 4000 -- m the site scoots from its campaign position
local SPEED = 30 -- km/h ground speed while relocating
local GRACE = 120 -- s before the first relocation

if dcsRetribution.plugins and dcsRetribution.plugins.mobilemissiles then
    local o = dcsRetribution.plugins.mobilemissiles
    INTERVAL = tonumber(o.scootIntervalS) or INTERVAL
    RADIUS = tonumber(o.scootRadiusM) or RADIUS
    SPEED = tonumber(o.scootSpeedKmph) or SPEED
    GRACE = tonumber(o.startGraceS) or GRACE
end

local function num(v)
    return tonumber(v) or 0
end

-- Every alive group named in a groups list (a site can hold several vehicle groups).
local function aliveGroups(groups)
    local out = {}
    if type(groups) ~= "table" then
        return out
    end
    for _, name in ipairs(groups) do
        local g = Group.getByName(name)
        if g and g:isExist() and g:getSize() > 0 then
            out[#out + 1] = g
        end
    end
    return out
end

-- Hold fire + alarm-green so the site relocates instead of stopping to fight, then route it
-- off-road to (x, y). x = north, y = east (the emitter's pydcs frame; mist.ground.buildWP maps it
-- straight onto the DCS ground waypoint).
local function driveTo(group, x, y, speedKmph)
    if not (group and group:isExist()) then
        return false
    end
    pcall(function()
        local con = group:getController()
        if con then
            con:setOption(
                AI.Option.Ground.id.ALARM_STATE,
                AI.Option.Ground.val.ALARM_STATE.GREEN
            )
            con:setOption(AI.Option.Ground.id.ROE, AI.Option.Ground.val.ROE.WEAPON_HOLD)
        end
    end)
    local wp = mist.ground.buildWP({ x = x, y = y }, "off road", mist.utils.kmphToMps(speedKmph))
    return mist.goRoute(group, { wp })
end

-- One site: on a cadence, scoot every alive group to a fresh point around the site's
-- campaign-map centre (the anchor -- so the site wanders its area, it never migrates).
local function startSite(site)
    local cx, cy = num(site.x), num(site.y)
    local function tick()
        local groups = aliveGroups(site.groups)
        if #groups == 0 then
            return nil -- site destroyed -> stop scheduling
        end
        for _, g in ipairs(groups) do
            local dest = mist.getRandPointInCircle({ x = cx, y = cy }, RADIUS)
            driveTo(g, dest.x, dest.y, SPEED)
        end
        return timer.getTime() + INTERVAL
    end
    timer.scheduleFunction(tick, {}, timer.getTime() + GRACE)
end

local ok, err = pcall(function()
    local count = 0
    if type(data.sites) == "table" then
        for _, site in ipairs(data.sites) do
            startSite(site)
            count = count + 1
        end
    end
    env.info(string.format("MOBILEMISSILES|: shoot-and-scoot armed on %d site(s)", count))
end)
if not ok then
    env.error("MOBILEMISSILES|: setup error: " .. tostring(err))
end
