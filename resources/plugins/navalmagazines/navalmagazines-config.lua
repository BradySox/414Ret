---------------------------------------------------------------------------------------------------
-- Cross-turn naval magazines runtime (§81).
--
-- Reads dcsRetribution.navalMagazines (game/missiongenerator/navalmagazineluadata.py):
--   stagger   = true|false   -- N1: ships generated ReturnFire, release them on a stagger
--   metered   = true|false   -- N2: enforce the campaign anti-ship magazine
--   magazines = { { group=, coalition=, remaining= }, ... }
--
-- Why this exists: a DCS ship is weapons-free with a RED alarm state from t=0 (ship weapons are
-- OPTION-driven -- there is no task to withhold them), and a modern anti-ship missile out-ranges
-- the whole theatre, so "in range" is true immediately and an entire fleet ripples its tubes in
-- the opening minute. Worse, a mission is a fresh spawn: without bookkeeping the fleet reloads
-- for free every single turn.
--
-- N1 -- STAGGERED RELEASE. The generator spawns ships ReturnFire (never WeaponHold), and each
-- group is released to weapons-free at its own moment inside [releaseMinS, releaseMaxS], so the
-- exchange develops across the mission instead of detonating at once.
--
-- RELEASE-ON-ATTACK (2026-08-05 flown finding, the B39 first fly): a DCS naval group on
-- ReturnFire mounts NO missile defense at all -- an LHA died to 13 Harpoons with its HHQ-16
-- escorts silent alongside, and a held fleet fired zero shots in 110 minutes. So the hold
-- shapes who STARTS the war, never who may defend: the first ENEMY weapon aimed at (SHOT
-- target) or landing on (HIT) a managed group releases it to weapons-free immediately -- held
-- OR winchester. An attacked winchester group may overshoot its magazine defending itself; the
-- overshoot is still counted and debited (the persisted stock clamps at zero).
--
-- ...AND ITS FORMATION WITH IT (the re-fly, same day): releasing only the TARGETED group is not
-- enough, because a Retribution carrier/LHA objective is TWO DCS groups -- the flagship and its
-- escort screen -- and the area-defence SAMs are on the ESCORTS. Attacked alone, the Type 071
-- fired its AK-630 CIWS (all the AAW it has) and died while the HHQ-16 escorts 1.91 km away sat
-- holding, never having been shot at themselves. So an attack also frees every managed friendly
-- group within `formationReleaseKm`. The measured geometry makes the radius unambiguous: a
-- screen rides ~2 km off its flagship, the next task force was 59 km away. ONE HOP, never a
-- cascade -- a released neighbour does not release ITS neighbours, so an attack cannot ripple
-- across the map.
--
-- N2 -- THE MAGAZINE. Each group's emitted `remaining` is this mission's hard anti-ship
-- expenditure cap. Every S_EVENT_SHOT whose weapon type matches the anti-ship pattern list
-- decrements it; at zero the group drops back to ReturnFire -- WINCHESTER, out of the anti-ship
-- fight until the campaign says otherwise (and, per the flown finding above, passive UNTIL
-- attacked -- release-on-attack is what lets a spent ship still fight back). There is no rearm:
-- expenditure mirrors into the naval_magazines_state debrief channel and Python debits the
-- persisted magazine at the turn boundary. A mission that fires nothing debits nothing.
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
local ROE_WEAPON_FREE = 0
local ROE_RETURN_FIRE = 3

-- Defaults. Overridable via the plugin options (dcsRetribution.plugins.navalmagazines).
local RELEASE_MIN = 120 -- s after mission start: the weapons-release window opens
local RELEASE_MAX = 900 -- s after mission start: the weapons-release window closes
local ANNOUNCE = true -- cue the owning coalition when a group goes winchester
-- Attacking one group frees its formation: a screen rides ~2 km off its flagship (measured),
-- the next task force was 59 km away. 0 disables (only the targeted group releases).
local FORMATION_KM = 15
local PATTERNS = "HARPOON,RGM_84,AGM_84,EXOCET,MM_38,MM_40,YJ,C_802,C_602,"
    .. "P_500,P_700,P_270,P_1000,KH_35,3M24,3M54,SS_N,NSM,RBS15,OTOMAT"

if dcsRetribution.plugins and dcsRetribution.plugins.navalmagazines then
    local o = dcsRetribution.plugins.navalmagazines
    RELEASE_MIN = tonumber(o.releaseMinS) or RELEASE_MIN
    RELEASE_MAX = tonumber(o.releaseMaxS) or RELEASE_MAX
    if RELEASE_MAX < RELEASE_MIN then
        RELEASE_MAX = RELEASE_MIN
    end
    if o.announceWinchester ~= nil then
        ANNOUNCE = o.announceWinchester
    end
    FORMATION_KM = tonumber(o.formationReleaseKm) or FORMATION_KM
    if type(o.ashmWeaponPatterns) == "string" and o.ashmWeaponPatterns ~= "" then
        PATTERNS = o.ashmWeaponPatterns
    end
end

-- Mirror-back channel: the base script serializes `naval_magazines_state` into the debrief and
-- Python debits each naval group's persisted magazine by its reported `fired`. One entry per
-- group, updated in place (the §57/§63 f.state pattern), with dirty_state flagged so write_state
-- actually flushes.
naval_magazines_state = naval_magazines_state or {}

local STAGGER = data.stagger == true or data.stagger == "true"
local METERED = data.metered == true or data.metered == "true"

local remaining = {} -- group name -> anti-ship missiles left this mission
local groupSide = {} -- group name -> coalition.side
local groupOrder = {} -- ordered group names, for the release stagger
local fired = {} -- group name -> its naval_magazines_state entry
local released = {} -- group name -> true once weapons-free (stagger or attack)
local underAttack = {} -- group name -> true once the enemy has fired at it

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
        groupOrder[#groupOrder + 1] = m.group
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

-- N1: release one group to weapons-free. A group whose magazine is already dry is deliberately
-- left at ReturnFire -- there is nothing to release it for. Idempotent: an attack release
-- earlier makes the scheduled release a no-op.
local function releaseGroup(groupName)
    if released[groupName] then
        return nil
    end
    if METERED and (remaining[groupName] or 0) <= 0 then
        env.info(string.format(
            "NAVALMAGAZINES|: %s stays ReturnFire at release (magazine dry)", groupName))
        return nil
    end
    released[groupName] = true
    setRoe(groupName, ROE_WEAPON_FREE)
    env.info(string.format("NAVALMAGAZINES|: %s released weapons-free", groupName))
    return nil
end

-- Release-on-attack: the hold shapes who STARTS the war, never who may defend (see the header --
-- a ReturnFire group is proven defenseless). Fires for held AND winchester groups; a dry group
-- released this way may overshoot its magazine defending itself, which stays counted.
-- Returns true when this call is what freed the group (never cascades on its own).
local function freeGroup(groupName, reason)
    if underAttack[groupName] then
        return false
    end
    underAttack[groupName] = true
    released[groupName] = true
    setRoe(groupName, ROE_WEAPON_FREE)
    env.info(string.format(
        "NAVALMAGAZINES|: %s %s -- released weapons-free", groupName, reason))
    return true
end

-- A managed group's position (its first alive unit), or nil if it is gone.
local function groupPoint(groupName)
    local ok, point = pcall(function()
        local grp = Group.getByName(groupName)
        if not (grp and grp:isExist()) then
            return nil
        end
        for _, unit in ipairs(grp:getUnits() or {}) do
            if unit and unit:isExist() then
                return unit:getPoint()
            end
        end
        return nil
    end)
    if ok then
        return point
    end
    return nil
end

-- The escort screen fights for its flagship: free every managed friendly group within
-- FORMATION_KM of the attacked one. ONE HOP -- these are freed via freeGroup, which does not
-- call back into here, so an attack can never ripple across the map.
local function releaseFormationAround(groupName)
    if FORMATION_KM <= 0 then
        return
    end
    local origin = groupPoint(groupName)
    if not origin then
        return
    end
    local limit = FORMATION_KM * 1000
    for _, other in ipairs(groupOrder) do
        if other ~= groupName
            and not underAttack[other]
            and groupSide[other] == groupSide[groupName]
        then
            local point = groupPoint(other)
            if point then
                local dx = point.x - origin.x
                local dz = point.z - origin.z
                if math.sqrt(dx * dx + dz * dz) <= limit then
                    freeGroup(other, "in the attacked formation")
                end
            end
        end
    end
end

local function releaseUnderAttack(groupName)
    if freeGroup(groupName, "under attack") then
        releaseFormationAround(groupName)
    end
end

-- Spread the releases evenly across the window rather than rolling each independently, so a
-- small fleet cannot randomly land every release in the same few seconds (the §49 stagger
-- lesson -- everything firing in one frame was itself a measured problem).
local function releaseTime(index, total)
    if total <= 1 or RELEASE_MAX <= RELEASE_MIN then
        return RELEASE_MIN
    end
    return RELEASE_MIN + (RELEASE_MAX - RELEASE_MIN) * (index - 1) / (total - 1)
end

-- N2: charge a shot against the shooter's magazine, and hold a spent group at ReturnFire.
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
        -- A group already under attack keeps weapons-free: dropping it back would
        -- re-defang a ship the enemy is actively shooting at (the flown ReturnFire
        -- finding). Its overshoot stays counted above.
        if not underAttack[groupName] then
            setRoe(groupName, ROE_RETURN_FIRE)
        end
        env.info(string.format("NAVALMAGAZINES|: %s WINCHESTER anti-ship", groupName))
        if ANNOUNCE then
            navMsg(groupSide[groupName] or coalition.side.BLUE, string.format(
                "WINCHESTER -- %s has expended its anti-ship missiles. No rearm this war.",
                groupName))
        end
    end
end

-- The managed group a world object belongs to, or nil. pcall-guarded: a weapon's target
-- can be scenery/a static with no getGroup.
local function managedGroupOfUnit(obj)
    if not obj then
        return nil
    end
    local ok, name = pcall(function()
        local grp = obj.getGroup and obj:getGroup() or nil
        return grp and grp:getName() or nil
    end)
    if ok and name and groupSide[name] ~= nil then
        return name
    end
    return nil
end

-- Friendly-fire guard (the §77 lesson): only ENEMY fire releases a held group.
local function isEnemyOf(initiator, groupName)
    local ok, side = pcall(function()
        return initiator:getCoalition()
    end)
    if not ok or side == nil then
        return false
    end
    return side ~= groupSide[groupName]
end

local handler = {}

function handler:onEvent(event)
    if not event then
        return
    end
    local ok, err = pcall(function()
        if event.id == world.event.S_EVENT_SHOT then
            local initiator, weapon = event.initiator, event.weapon
            if not weapon then
                return
            end
            -- N2: charge a real anti-ship release against the shooter's magazine.
            if METERED and initiator and isAntiShipWeapon(weapon:getTypeName()) then
                local grp = initiator:getGroup()
                if grp then
                    chargeShot(grp:getName())
                end
            end
            -- Release-on-attack: ANY enemy weapon aimed at a managed group frees it to
            -- defend -- not just anti-ship ordnance (a Maverick or an LGB is an attack too).
            local tOk, target = pcall(function()
                return weapon.getTarget and weapon:getTarget() or nil
            end)
            if tOk and target then
                local name = managedGroupOfUnit(target)
                if name and initiator and isEnemyOf(initiator, name) then
                    releaseUnderAttack(name)
                end
            end
        elseif event.id == world.event.S_EVENT_HIT then
            -- The backstop for weapons that carry no SHOT target (dumb bombs, guns). A nil
            -- initiator (debris, an unknown shooter) still releases -- being hit is reason
            -- enough to defend; a known FRIENDLY hit never does.
            local name = managedGroupOfUnit(event.target)
            if name and (not event.initiator or isEnemyOf(event.initiator, name)) then
                releaseUnderAttack(name)
            end
        end
    end)
    if not ok then
        env.warning("navalmagazines: shot handler error (continuing): " .. tostring(err))
    end
end

local ok, err = pcall(function()
    -- The handler always runs: N2 needs the shot metering, and release-on-attack must
    -- free a held group under either tier.
    world.addEventHandler(handler)
    if METERED then
        -- A group that starts the mission dry never gets to open fire with missiles it does not
        -- have. With the stagger on it is simply never released; without it, the generator left
        -- every ship weapons-free, so pull the dry ones back now.
        if not STAGGER then
            for _, name in ipairs(groupOrder) do
                if (remaining[name] or 0) <= 0 then
                    setRoe(name, ROE_RETURN_FIRE)
                end
            end
        end
    end
    if STAGGER then
        for index, name in ipairs(groupOrder) do
            timer.scheduleFunction(
                releaseGroup, name,
                timer.getTime() + releaseTime(index, #groupOrder)
            )
        end
    end
    env.info(string.format(
        "NAVALMAGAZINES|: armed -- %d naval group(s), stagger %s (%ds-%ds), metered %s",
        #groupOrder, tostring(STAGGER), RELEASE_MIN, RELEASE_MAX, tostring(METERED)))
end)
if not ok then
    env.error("NAVALMAGAZINES|: setup error: " .. tostring(err))
end
