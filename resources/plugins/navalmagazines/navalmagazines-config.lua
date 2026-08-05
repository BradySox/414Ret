---------------------------------------------------------------------------------------------------
-- Cross-turn naval magazines runtime (§81 N2 -- the magazine).
--
-- Reads dcsRetribution.navalMagazines (game/missiongenerator/navalmagazineluadata.py):
--   magazines = { { group=, coalition=, remaining= }, ... }
--
-- Why this exists: a DCS mission is a fresh spawn, so without bookkeeping a fleet reloads for free
-- every single turn and the naval war has no ammunition dimension at all -- sinking hulls was the
-- only way volume ever went down.
--
-- Each group's emitted `remaining` is this mission's hard anti-ship expenditure cap. Every
-- S_EVENT_SHOT whose weapon type matches the anti-ship pattern list decrements it; at zero the
-- group drops back to ReturnFire -- WINCHESTER, still able to defend itself but out of the
-- anti-ship fight until the campaign says otherwise. There is no rearm: expenditure mirrors into
-- the naval_magazines_state debrief channel and Python debits the persisted magazine at the turn
-- boundary. A mission that fires nothing debits nothing.
--
-- N1 (the staggered weapons release) is deliberately NOT here. "At time T, set this group's ROE"
-- is exactly what a DCS start condition expresses, so it is authored at generation as a
-- ControlledTask on each ship group (TgoGenerator.set_ship_engagement) -- no runtime, and nothing
-- a host can untick to silently disable it. Generation also handles the group that starts the
-- mission already dry: it is simply generated ReturnFire.
--
-- The land-attack cruise missiles §63 meters (Tomahawk, the 3M14 Kalibr) are deliberately absent
-- from the pattern list, so the two magazines meter disjoint weapon sets and can never both
-- charge the same shot. Never add a land-attack family here.
--
-- The plugin owns no kills and no spawns: it only sets ROE and counts real weapon releases.
-- Inert when the node is absent. pcall-guarded throughout; definition order matters (Lua 5.1):
-- helpers precede use.
---------------------------------------------------------------------------------------------------

if not (dcsRetribution and dcsRetribution.navalMagazines) then
    return
end

local data = dcsRetribution.navalMagazines

-- ROE option id is 0 for every unit category, and the naval value table mirrors the ground one.
-- Read the enums when DCS exposes them, fall back to the documented literals otherwise.
local ROE_ID = (AI and AI.Option and AI.Option.Naval and AI.Option.Naval.id
    and AI.Option.Naval.id.ROE) or 0
local ROE_RETURN_FIRE = 3

-- Defaults. Overridable via the plugin options (dcsRetribution.plugins.navalmagazines).
local ANNOUNCE = true -- cue the owning coalition when a group goes winchester
local PATTERNS = "HARPOON,RGM_84,AGM_84,EXOCET,MM_38,MM_40,YJ,C_802,C_602,"
    .. "P_500,P_700,P_270,P_1000,KH_35,3M24,3M54,SS_N,NSM,RBS15,OTOMAT"

if dcsRetribution.plugins and dcsRetribution.plugins.navalmagazines then
    local o = dcsRetribution.plugins.navalmagazines
    if o.announceWinchester ~= nil then
        ANNOUNCE = o.announceWinchester
    end
    if type(o.ashmWeaponPatterns) == "string" and o.ashmWeaponPatterns ~= "" then
        PATTERNS = o.ashmWeaponPatterns
    end
end

-- Mirror-back channel: the base script serializes `naval_magazines_state` into the debrief and
-- Python debits each naval group's persisted magazine by its reported `fired`. One entry per
-- group, updated in place (the §57/§63 f.state pattern), with dirty_state flagged so write_state
-- actually flushes.
naval_magazines_state = naval_magazines_state or {}

local remaining = {} -- group name -> anti-ship missiles left this mission
local groupSide = {} -- group name -> coalition.side
local fired = {} -- group name -> its naval_magazines_state entry

local function sideOf(name)
    if name == "red" then
        return coalition.side.RED
    end
    return coalition.side.BLUE
end

for _, m in ipairs(data.magazines or {}) do
    if m.group then
        remaining[m.group] = tonumber(m.remaining) or 0
        groupSide[m.group] = sideOf(m.coalition)
    end
end

-- Split the pattern list once. Matching is plain substring on the upper-cased weapon type name
-- (string.find with plain=true) -- never a Lua pattern, since weapon ids carry magic characters.
local weaponPatterns = {}
for token in string.gmatch(PATTERNS, "[^,]+") do
    local trimmed = token:match("^%s*(.-)%s*$")
    if trimmed ~= "" then
        weaponPatterns[#weaponPatterns + 1] = trimmed:upper()
    end
end

local function isAntiShipWeapon(typeName)
    if type(typeName) ~= "string" then
        return false
    end
    local upper = typeName:upper()
    for _, p in ipairs(weaponPatterns) do
        if string.find(upper, p, 1, true) then
            return true
        end
    end
    return false
end

local function setRoe(groupName, value)
    pcall(function()
        local grp = Group.getByName(groupName)
        if grp and grp:isExist() then
            grp:getController():setOption(ROE_ID, value)
        end
    end)
end

local function navMsg(side, text)
    pcall(trigger.action.outTextForCoalition, side, text, 15)
end

local function recordFired(groupName, count)
    local entry = fired[groupName]
    if not entry then
        entry = { group = groupName, fired = 0 }
        fired[groupName] = entry
        naval_magazines_state[#naval_magazines_state + 1] = entry
    end
    entry.fired = entry.fired + count
    dirty_state = true
end

-- Charge a shot against the shooter's magazine, and hold a spent group at ReturnFire.
local function chargeShot(groupName)
    local left = remaining[groupName]
    if left == nil then
        return
    end
    recordFired(groupName, 1)
    left = left - 1
    if left < 0 then
        left = 0
    end
    remaining[groupName] = left
    if left <= 0 then
        setRoe(groupName, ROE_RETURN_FIRE)
        env.info(string.format("NAVALMAGAZINES|: %s WINCHESTER anti-ship", groupName))
        if ANNOUNCE then
            navMsg(groupSide[groupName] or coalition.side.BLUE, string.format(
                "WINCHESTER -- %s has expended its anti-ship missiles. No rearm this war.",
                groupName))
        end
    end
end

local handler = {}

function handler:onEvent(event)
    if not (event and event.id == world.event.S_EVENT_SHOT) then
        return
    end
    local ok, err = pcall(function()
        local initiator, weapon = event.initiator, event.weapon
        if not (initiator and weapon) then
            return
        end
        if not isAntiShipWeapon(weapon:getTypeName()) then
            return
        end
        local grp = initiator:getGroup()
        if grp then
            chargeShot(grp:getName())
        end
    end)
    if not ok then
        env.warning("navalmagazines: shot handler error (continuing): " .. tostring(err))
    end
end

local ok, err = pcall(function()
    local count = 0
    for _ in pairs(remaining) do
        count = count + 1
    end
    world.addEventHandler(handler)
    env.info(string.format(
        "NAVALMAGAZINES|: armed -- metering %d naval group(s)", count))
end)
if not ok then
    env.error("NAVALMAGAZINES|: setup error: " .. tostring(err))
end
