---------------------------------------------------------------------------------------------------
-- Neutral-faction border defense (§96) -- a neutral country's airspace, defended.
--
-- Reads dcsRetribution.neutralBorder (emitted only when neutral_border_defense is on and the
-- generator could build the map's zones; inert otherwise). Design + decisions:
-- docs/dev/design/414th-neutral-border-defense-notes.md. Constraints a reader could undo:
--   * The shadow spawns on the intruder's OPPOSING coalition (SPAWN:InitCountry/InitCoalition)
--     because a true-neutral unit cannot fire, ever -- do not "fix" the spawn to neutral.
--   * Shadow-phase ROE is RETURN FIRE, not weapons hold: it defends, never initiates (DM call).
--   * AI intruders are shadowed but NEVER escalated on (DM call). Only players earn the attack.
--   * Escalation is ROE + tasking only. Never enableEmission (hard constraint).
--   * Spawns are free, untracked event content (the §61 precedent).
-- Values arrive as Lua strings (LuaItem contract) -- tonumber() everything numeric here.
-- Border verts are terrain XY: vert.x = DCS x (north), vert.y = DCS z (east).
-- Definition order matters (Lua 5.1): helpers precede use. pcall-guarded throughout.
---------------------------------------------------------------------------------------------------

if not (dcsRetribution and dcsRetribution.neutralBorder) then
    return
end

local data = dcsRetribution.neutralBorder

-- Defaults. Overridable via the plugin options (dcsRetribution.plugins.neutralborder).
local WARN_DWELL_S = 30 -- inside the border this long -> warning + shadow launch
local ENGAGE_DWELL_S = 180 -- a PLAYER inside this long -> engaged
local SCAN_INTERVAL_S = 10 -- border scan cadence
local VECTOR_INTERVAL_S = 45 -- shadow vector cadence
local MAX_SHADOWS = 2 -- concurrent shadow flights per zone
local DRAW_BORDERS = true -- F10 border polylines (the §86 invisible-bubble lesson)
--: How far an UN-escalated shadow keeps from the intruder.
--:
--: It used to route to the intruder's own position +1200 m, i.e. it closed to a
--: merge. At return-fire ROE it cannot shoot first, so it arrived inside an
--: escorted flight's engagement envelope and was killed for free -- flown
--: 2026-08-28, all four alert aircraft lost and the un-escalated pair shot down
--: having fired nothing. It shepherds from here instead.
--:
--: This reduces the loss rate; it does not fix it. The shadow spawns on the
--: intruder's OPPOSING coalition, so it is a hostile contact to that side and a
--: CAP tasked over the area will hunt it at any range. Standing off buys time,
--: not safety. The real lever is the return-fire ROE, and changing that
--: re-opens the "defends, never initiates" call.
local SHADOW_HOLD_M = 37040 -- 20 NM

if dcsRetribution.plugins and dcsRetribution.plugins.neutralborder then
    local o = dcsRetribution.plugins.neutralborder
    WARN_DWELL_S = tonumber(o.warnDwellS) or WARN_DWELL_S
    ENGAGE_DWELL_S = tonumber(o.engageDwellS) or ENGAGE_DWELL_S
    SCAN_INTERVAL_S = tonumber(o.scanIntervalS) or SCAN_INTERVAL_S
    VECTOR_INTERVAL_S = tonumber(o.vectorIntervalS) or VECTOR_INTERVAL_S
    if tonumber(o.shadowHoldNm) then
        SHADOW_HOLD_M = tonumber(o.shadowHoldNm) * 1852
    end
    MAX_SHADOWS = tonumber(o.maxShadows) or MAX_SHADOWS
    if o.drawBorders ~= nil then
        DRAW_BORDERS = (o.drawBorders == true) or (o.drawBorders == "true")
    end
end

local EXIT_GRACE_S = 120 -- outside this long (pre-escalation) -> shadow stands down
local SHADOW_AGL_M = 760 -- AGL for the off-field launch point and the vector loop
local SHADOW_SPEED_KT = 300 -- air-spawn speed (a ~0 kt clone spawns stalled; QRA lesson)
-- How far from the intruder the alert flight comes up when its own origin is
-- further away than this. MEASURED 2026-08-25 (Tacview, Inherent Resolve): Iran's
-- origin is the representative point of its clipped polygon, so the pair spawned
-- 224 NM behind an F-15E and closed to 127 NM in twelve minutes before giving up
-- -- a MiG-29A has ~80 kt on a cruising Strike Eagle, and a stern chase from
-- there never converges. 25 NM is ~3 min at the shadow's speed, which is the
-- engage dwell, so the shadow is present when the timer it exists to enforce
-- expires. Nearer than this and the origin is used as-is, so a small country
-- still scrambles off its own runway.
local SHADOW_STANDOFF_M = 46300
local SHADOW_DESPAWN_S = 300 -- stood-down shadow lifetime after the RTB vector

local FT_TO_M = 0.3048
local MARKUP_ID_BASE = 96000 -- §96 block; one freeform id per zone
--: The name labels sit in their own half of the block so an outline id and a
--: label id can never collide.
local LABEL_ID_OFFSET = 500
local LABEL_FONT_SIZE = 16

local function log(msg)
    env.info("NEUTRALBORDER|: " .. tostring(msg))
end

---------------------------------------------------------------------------------------------------
-- Zone parse. A zone that cannot be parsed is dropped, never fatal.
---------------------------------------------------------------------------------------------------
local zones = {}

for _, raw in ipairs(data.zones or {}) do
    local ok = pcall(function()
        local verts = {}
        local minx, maxx, minz, maxz
        for _, v in ipairs(raw.border or {}) do
            local x, z = tonumber(v.x), tonumber(v.y)
            if x and z then
                verts[#verts + 1] = { x = x, z = z }
                if not minx or x < minx then minx = x end
                if not maxx or x > maxx then maxx = x end
                if not minz or z < minz then minz = z end
                if not maxz or z > maxz then maxz = z end
            end
        end
        -- A zone launches from a FIELD or from a POINT. Afghanistan's neighbours
        -- have no airbase on the map at all, so those air-spawn a standing CAP
        -- over their own side instead (see the design note).
        local spawn_x, spawn_z = tonumber(raw.spawnX), tonumber(raw.spawnZ)
        local has_origin = raw.field ~= nil or (spawn_x ~= nil and spawn_z ~= nil)
        local posture = tostring(raw.posture or "neutral")
        local function flag(v) return (v == "true" or v == true) end
        -- Transit consent is PER SIDE: a country may let one bloc through and
        -- refuse the other, so each intruder is checked against its own flag.
        local ofBlue = flag(raw.overflightBlue)
        local ofRed = flag(raw.overflightRed)
        -- Only an uninvolved country that refuses SOMEONE enforces. An aligned
        -- one is defended by its own side's QRA (§1 accept zones) and a
        -- fully-permitting neutral is a line on the map, so both are drawn and
        -- never scanned, carry no templates, and need no origin to be usable.
        local enforces = (posture == "neutral") and not (ofBlue and ofRed)
        local usable = (not enforces)
            or (raw.fighterTemplate ~= nil and has_origin)
        if #verts >= 3 and usable then
            zones[#zones + 1] = {
                country = tostring(raw.country or "Neutral"),
                posture = posture,
                enforces = enforces,
                permits_blue = ofBlue,
                permits_red = ofRed,
                -- nil = no safe altitude for that side. A floor means "high
                -- transit is tolerated", which a closed or hostile country
                -- does not offer at any height (DM call).
                floor_blue_m = tonumber(raw.floorBlueFt)
                    and tonumber(raw.floorBlueFt) * FT_TO_M or nil,
                floor_red_m = tonumber(raw.floorRedFt)
                    and tonumber(raw.floorRedFt) * FT_TO_M or nil,
                field = raw.field and tostring(raw.field) or nil,
                spawn_x = spawn_x,
                spawn_z = spawn_z,
                spawn_alt_m = tonumber(raw.spawnAltM) or 6000,
                origin_label = tostring(raw.originLabel or raw.field or "border CAP"),
                -- Where to write the country's name: inside the polygon by
                -- construction (shapely's representative point), which a
                -- centroid is not on a concave country.
                label_x = tonumber(raw.labelX),
                label_z = tonumber(raw.labelZ),
                fighter_template = tostring(raw.fighterTemplate),
                sam_template = raw.samTemplate and tostring(raw.samTemplate) or nil,
                red_country = tonumber(raw.redCountryId),
                blue_country = tonumber(raw.blueCountryId),
                verts = verts,
                bbox = { minx = minx, maxx = maxx, minz = minz, maxz = maxz },
                -- runtime
                spawners = {}, -- per clone side: [side] = SPAWN
                shadows = {}, -- shadow name -> record
                shadow_count = 0,
                sam_spawner = nil,
                sam_spawned = false,
            }
        end
    end)
    if not ok then
        log("zone parse error -- zone dropped")
    end
end

if #zones == 0 then
    log("no usable zones -- inert")
    return
end

---------------------------------------------------------------------------------------------------
-- Geometry. Ray-cast point-in-polygon against unit getPoint() (p.x north, p.z east).
---------------------------------------------------------------------------------------------------
local function in_bbox(zone, px, pz)
    local b = zone.bbox
    return px >= b.minx and px <= b.maxx and pz >= b.minz and pz <= b.maxz
end

local function in_polygon(zone, px, pz)
    local inside = false
    local verts = zone.verts
    local j = #verts
    for i = 1, #verts do
        local vi, vj = verts[i], verts[j]
        if ((vi.z > pz) ~= (vj.z > pz))
            and (px < (vj.x - vi.x) * (pz - vi.z) / (vj.z - vi.z) + vi.x) then
            inside = not inside
        end
        j = i
    end
    return inside
end

---------------------------------------------------------------------------------------------------
-- Small helpers.
---------------------------------------------------------------------------------------------------
local function opposing(side)
    if side == coalition.side.BLUE then
        return coalition.side.RED
    end
    return coalition.side.BLUE
end

local function clone_country(zone, intruder_side)
    if intruder_side == coalition.side.BLUE then
        return zone.red_country
    end
    return zone.blue_country
end

local function lead_unit(group)
    if not group then
        return nil
    end
    local units = group:getUnits()
    if not units then
        return nil
    end
    for _, u in ipairs(units) do
        if u and u:isExist() then
            return u
        end
    end
    return nil
end

local function is_player_group(group)
    local found = false
    pcall(function()
        for _, u in ipairs(group:getUnits() or {}) do
            if u and u:isExist() and u.getPlayerName and u:getPlayerName() then
                found = true
                return
            end
        end
    end)
    return found
end

local function announce(group, msg)
    pcall(function()
        trigger.action.outTextForGroup(group:getID(), msg, 20)
    end)
end

---------------------------------------------------------------------------------------------------
-- F10 border drawing (once at start; the border must be visible -- §86 lesson).
---------------------------------------------------------------------------------------------------
-- The colour grammar, shared with the planning map's layer (mapColors.ts):
--   HUE  - whose airspace: red enemy-held, blue friendly, mint uninvolved.
--   SHADE- will it intercept you. Only an uninvolved country that refuses you
--          transit gets a real one; a country IN the war is context, because
--          its own QRA governs it and the unit icons already say whose it is.
local function border_theme(zone)
    if zone.posture == "blue" then
        return { 0.0, 0.52, 1.0 }, 0.06, 1 -- in the war, friendly: solid, faint
    elseif zone.posture == "red" then
        return { 0.78, 0.31, 0.31 }, 0.06, 1 -- in the war, enemy: solid, faint
    elseif zone.posture == "contested" then
        -- Both sides hold fields in it. Grey because the two allegiance hues
        -- are the two answers that are NOT true here.
        return { 0.73, 0.69, 0.65 }, 0.06, 1
    elseif zone.enforces then
        -- Crimson: a third party that refuses transit and WILL intercept. Red
        -- because hue answers "will this engage me", not "whose side is it on"
        -- -- drawing this green put Iran in the same colour as a country that
        -- waves you through.
        return { 0.88, 0.33, 0.37 }, 0.20, 5 -- long dash: firm, legal
    end
    return { 0.62, 0.85, 0.72 }, 0.10, 2 -- pale mint: neutral, you may cross
end

-- What the F10 label says under the country's name. A pilot reading the map
-- wants one thing from a border: may I cross it, and if not what happens.
local function border_caption(zone)
    if zone.posture == "blue" then
        return "friendly"
    elseif zone.posture == "red" then
        return "enemy-held"
    elseif zone.posture == "contested" then
        return "contested"
    elseif zone.enforces then
        -- The country's name is already the line above, so a spawn-point zone's
        -- "<country> border CAP" would say it twice.
        local origin = zone.origin_label
        local prefix = zone.country .. " "
        if origin:sub(1, #prefix) == prefix then
            origin = origin:sub(#prefix + 1)
        end
        return "CLOSED - alert from " .. origin
    end
    return "transit permitted"
end

local function draw_borders()
    if not DRAW_BORDERS then
        return
    end
    for zi, zone in ipairs(zones) do
        local rgb, fill_alpha, line_type = border_theme(zone)
        -- The FILL, first so the outline lands on top.
        --
        -- DCS will not fill a concave freeform: it draws the outline and stops.
        -- A national border is about as concave as a shape gets, so every zone
        -- came out as a bare line (reported 2026-08-25 on the Iraq map). MOOSE
        -- hit the same wall -- ZONE_POLYGON_BASE:DrawZone triangulates and fills
        -- triangle by triangle, and its single-freeform path is dead-coded
        -- behind `if false then`. Reuse its triangulation rather than repeat the
        -- discovery.
        pcall(function()
            local pts = {}
            for _, v in ipairs(zone.verts) do
                pts[#pts + 1] = { x = v.x, y = v.z }
            end
            local poly = ZONE_POLYGON:NewFromPointsArray("NB96-" .. zi, pts)
            poly:SetDrawCoalition(-1)
            poly:ReFill(rgb, fill_alpha)
        end)
        -- The NAME, so the map says what the shape is without a hover. Same
        -- hue as its border, so the label and the line read as one thing and
        -- neither is confusable with the cyan §45 support orbits.
        if zone.label_x and zone.label_z then
            pcall(function()
                local y = 0
                pcall(function()
                    y = land.getHeight({ x = zone.label_x, y = zone.label_z }) or 0
                end)
                trigger.action.textToAll(
                    -1,
                    MARKUP_ID_BASE + LABEL_ID_OFFSET + zi,
                    { x = zone.label_x, y = y, z = zone.label_z },
                    { rgb[1], rgb[2], rgb[3], 1.0 },
                    { 0, 0, 0, 0.45 },
                    LABEL_FONT_SIZE,
                    true,
                    string.upper(zone.country) .. "\n" .. border_caption(zone)
                )
            end)
        end

        -- The OUTLINE: one freeform for the whole ring, which DCS does honour,
        -- and which keeps the dash pattern the fill triangles cannot carry.
        pcall(function()
            local args = { 7, -1, MARKUP_ID_BASE + zi } -- freeform, all coalitions
            for _, v in ipairs(zone.verts) do
                args[#args + 1] = { x = v.x, y = 0, z = v.z }
            end
            args[#args + 1] = { rgb[1], rgb[2], rgb[3], 0.95 }
            args[#args + 1] = { 0, 0, 0, 0 } -- fill is the triangles' job
            args[#args + 1] = line_type
            args[#args + 1] = true -- read only
            trigger.action.markupToAll(unpack(args))
        end)
    end
end

---------------------------------------------------------------------------------------------------
-- Shadow flights: spawn on the intruder's opposing coalition, return-fire, and vector loop.
---------------------------------------------------------------------------------------------------
local intruders = {} -- group name -> state
local vector_loop_running = false
local vector_tick -- forward declaration comment only; defined below before first use in start_vector_loop

local function spawner_for(zone, zi, clone_side)
    if not zone.spawners[clone_side] then
        local tag = (clone_side == coalition.side.RED) and "R" or "B"
        zone.spawners[clone_side] = SPAWN:NewWithAlias(
            zone.fighter_template,
            "NEUTRAL AF " .. zone.country .. " " .. tag .. zi
        )
    end
    return zone.spawners[clone_side]
end

-- Where the alert flight comes up: its own origin when that is close enough to
-- matter, otherwise a stand-off point between the intruder and that origin. The
-- origin keeps its name either way -- the radio call and the log still say which
-- field launched it.
local function launch_point(zone, ix, iz)
    local ox, oz
    local alt = zone.spawn_alt_m
    if zone.field then
        local airbase = AIRBASE:FindByName(zone.field)
        if not airbase then
            return nil
        end
        local c = airbase:GetCoordinate()
        ox, oz = c.x, c.z
    else
        ox, oz = zone.spawn_x, zone.spawn_z
    end
    if ox == nil or oz == nil then
        return nil
    end
    if ix == nil or iz == nil then
        return { x = ox, y = alt, z = oz, at_origin = true }
    end
    local dx, dz = ox - ix, oz - iz
    local dist = math.sqrt(dx * dx + dz * dz)
    if dist <= SHADOW_STANDOFF_M then
        return { x = ox, y = alt, z = oz, at_origin = true }
    end
    local f = SHADOW_STANDOFF_M / dist
    local lx, lz = ix + dx * f, iz + dz * f
    -- A concave border can put the straight line briefly outside the country.
    -- Launching a national alert flight over the neighbour is worse than a slow
    -- response, so that case falls back to the origin.
    if not in_polygon(zone, lx, lz) then
        return { x = ox, y = alt, z = oz, at_origin = true }
    end
    return { x = lx, y = alt, z = lz, at_origin = false }
end

local function spawn_shadow(zone, zi, intruder_name, intruder_side, ix, iz)
    if zone.shadow_count >= MAX_SHADOWS then
        return nil
    end
    local shadow = nil
    local ok, err = pcall(function()
        local clone_side_id = opposing(intruder_side)
        local sp = spawner_for(zone, zi, clone_side_id)
        sp:InitGrouping(2)
        local country = clone_country(zone, intruder_side)
        if country and sp.InitCountry then
            sp:InitCountry(country)
        end
        if sp.InitCoalition then
            sp:InitCoalition(clone_side_id)
        end
        pcall(function()
            sp:InitSpeedKnots(SHADOW_SPEED_KT)
        end)

        local at = launch_point(zone, ix, iz)
        if not at then
            log("no usable origin for " .. zone.country .. " -- no shadow")
            return
        end
        local grp
        if at.at_origin and zone.field then
            local airbase = AIRBASE:FindByName(zone.field)
            -- Runway, matching the template's own start type. Takeoff.Air was
            -- asked for here until 2026-08-28 and silently did not happen:
            -- SpawnAtAirbase keeps the template's start type, so a cold ramp
            -- template stayed a cold ramp start and took 270 s to get up.
            grp = sp:SpawnAtAirbase(airbase, SPAWN.Takeoff.Runway)
        else
            -- MOOSE takes the altitude as the Vec3 y.
            grp = sp:SpawnFromVec3({ x = at.x, y = at.y, z = at.z })
        end
        if not grp then
            return
        end
        -- Return fire, never initiate: the shadow-phase ROE (DM call). EvadeFire
        -- so a shot at it is answered with defense, not a parade-ground death.
        pcall(function()
            grp:OptionROEReturnFire()
        end)
        pcall(function()
            grp:OptionROTEvadeFire()
        end)
        shadow = {
            name = grp:GetName(),
            group = grp,
            intruder = intruder_name,
            zone = zi,
            escalated = false,
            stood_down = false,
        }
        zone.shadows[shadow.name] = shadow
        zone.shadow_count = zone.shadow_count + 1
        log(string.format(
            "shadow %s up from %s vs %s",
            shadow.name, zone.origin_label, intruder_name))
    end)
    if not ok then
        log("shadow spawn error: " .. tostring(err))
    end
    return shadow
end

local function shadow_for(intruder_name)
    for _, zone in ipairs(zones) do
        for _, shadow in pairs(zone.shadows) do
            if shadow.intruder == intruder_name and not shadow.stood_down then
                return shadow
            end
        end
    end
    return nil
end

local function destroy_shadow_later(zone, shadow)
    timer.scheduleFunction(function()
        pcall(function()
            if shadow.group and shadow.group:IsAlive() then
                shadow.group:Destroy(false)
            end
        end)
        if zone.shadows[shadow.name] then
            zone.shadows[shadow.name] = nil
            zone.shadow_count = math.max(0, zone.shadow_count - 1)
        end
        return nil
    end, {}, timer.getTime() + SHADOW_DESPAWN_S)
end

local function stand_down(zone, shadow)
    if shadow.stood_down or shadow.escalated then
        return
    end
    shadow.stood_down = true
    pcall(function()
        if zone.field then
            local airbase = AIRBASE:FindByName(zone.field)
            if airbase then
                local c = airbase:GetCoordinate()
                shadow.group:RouteToVec3(
                    { x = c.x, y = (c.y or 0) + SHADOW_AGL_M, z = c.z }, 200)
            end
        else
            -- Point-spawned CAP: send it back to its own station.
            shadow.group:RouteToVec3(
                { x = zone.spawn_x, y = zone.spawn_alt_m, z = zone.spawn_z }, 200)
        end
    end)
    destroy_shadow_later(zone, shadow)
    log("shadow " .. shadow.name .. " standing down")
end

-- The SAM wake: clone the battery on the escalating intruder's opposing side. Alarm
-- state and ROE come with the fresh spawn; never touch radar emissions.
local function wake_sam(zone, intruder_side)
    if zone.sam_spawned then
        return
    end
    if not zone.sam_template then
        -- Say so. This returned silently until 2026-08-28, so a mission where
        -- the escalation fired and no battery woke looked identical to one
        -- where the ladder had not run at all.
        log("no SAM template for " .. zone.country .. " -- nothing to wake")
        zone.sam_spawned = true
        return
    end
    zone.sam_spawned = true
    local ok, err = pcall(function()
        if not zone.sam_spawner then
            zone.sam_spawner = SPAWN:NewWithAlias(
                zone.sam_template, "NEUTRAL SAM " .. zone.country)
        end
        local sp = zone.sam_spawner
        local country = clone_country(zone, intruder_side)
        if country and sp.InitCountry then
            sp:InitCountry(country)
        end
        if sp.InitCoalition then
            sp:InitCoalition(opposing(intruder_side))
        end
        sp:Spawn()
        log("SAM battery awake at " .. zone.origin_label)
    end)
    if not ok then
        zone.sam_spawned = false
        log("SAM wake error: " .. tostring(err))
    end
end

local function escalate(state, intruder_group)
    if state.escalated or not state.is_player then
        return
    end
    state.escalated = true
    local zone = zones[state.zone]
    announce(intruder_group, string.format(
        "%s AIR FORCE: You were warned. %s fighters are ENGAGING.",
        string.upper(zone.country), zone.country))
    local shadow = shadow_for(state.name)
    if shadow then
        shadow.escalated = true
        pcall(function()
            shadow.group:OptionROEWeaponFree()
        end)
        -- The §61 shape: a hard AttackGroup task on the raw controller,
        -- re-set by the vector loop only when the target changes.
        pcall(function()
            local sg = Group.getByName(shadow.name)
            local tgt = Group.getByName(state.name)
            if sg and tgt then
                shadow.last_target = tgt:getID()
                sg:getController():setTask({
                    id = "AttackGroup",
                    params = { groupId = tgt:getID() },
                })
            end
        end)
    end
    wake_sam(zone, state.side)
    log("ESCALATED on " .. state.name)
end

---------------------------------------------------------------------------------------------------
-- Vector loop: pre-escalation shadows chase a point beside the intruder; escalated
-- shadows get their attack task refreshed (the §61 pattern -- a dead task never sticks).
---------------------------------------------------------------------------------------------------
vector_tick = function()
    for _, zone in ipairs(zones) do
        for _, shadow in pairs(zone.shadows) do
            if not shadow.stood_down then
                pcall(function()
                    local intruder = Group.getByName(shadow.intruder)
                    local lead = lead_unit(intruder)
                    if not lead then
                        stand_down(zone, shadow)
                        return
                    end
                    if shadow.escalated then
                        -- Re-set only when the target id changed (the §61 rule:
                        -- a repeated identical setTask resets the AI's attack run).
                        local tid = intruder:getID()
                        if tid and tid ~= shadow.last_target then
                            shadow.last_target = tid
                            local sg = Group.getByName(shadow.name)
                            if sg then
                                sg:getController():setTask({
                                    id = "AttackGroup",
                                    params = { groupId = tid },
                                })
                            end
                        end
                        return
                    end
                    local p = lead:getPoint()
                    -- Shepherd from SHADOW_HOLD_M, on whatever bearing the
                    -- shadow already sits, rather than closing on the intruder.
                    -- Routing to its position +1200 m was a merge, and a
                    -- return-fire flight that merges with an escorted one dies
                    -- without shooting (flown 2026-08-28, 4 of 4 lost).
                    local sx, sz = p.x + SHADOW_HOLD_M, p.z
                    local slead = lead_unit(Group.getByName(shadow.name))
                    if slead then
                        local sp = slead:getPoint()
                        local dx, dz = sp.x - p.x, sp.z - p.z
                        local dist = math.sqrt(dx * dx + dz * dz)
                        if dist > 1 then
                            local f = SHADOW_HOLD_M / dist
                            sx, sz = p.x + dx * f, p.z + dz * f
                        end
                    end
                    shadow.group:RouteToVec3({ x = sx, y = p.y, z = sz }, 250)
                end)
            end
        end
    end
    return timer.getTime() + VECTOR_INTERVAL_S
end

local function start_vector_loop()
    if not vector_loop_running then
        vector_loop_running = true
        timer.scheduleFunction(function()
            return vector_tick()
        end, {}, timer.getTime() + 5)
    end
end

---------------------------------------------------------------------------------------------------
-- The border watch.
---------------------------------------------------------------------------------------------------
-- The radio call, on the FIRST scan that finds you inside. It used to wait for
-- WARN_DWELL_S along with the shadow launch, which put the hail half a minute
-- after the crossing that caused it -- flown 2026-08-28: "pop it immediately on
-- entry to airspace". The scan interval bounds "immediately" at SCAN_INTERVAL_S.
-- Launching the shadow still waits: being told is instant, being intercepted is
-- not.
local function hail(state, intruder_group)
    state.hailed = true
    local zone = zones[state.zone]
    if state.is_player then
        -- A country that grants no safe altitude must not be radioed as though
        -- climbing would fix it. A floor is authored by the campaign only.
        -- NOT `cond and a or b`: a nil floor is the normal case (no safe
        -- altitude), and that idiom falls through to the other side's floor.
        local floor = zone.floor_red_m
        if state.side == coalition.side.BLUE then
            floor = zone.floor_blue_m
        end
        local msg
        if floor then
            msg = string.format(
                "%s AIR FORCE: You are violating %s airspace below %d ft. "
                    .. "Climb above it or exit, or you will be engaged.",
                string.upper(zone.country), zone.country, floor / FT_TO_M)
        else
            msg = string.format(
                "%s AIR FORCE: You are violating %s airspace. "
                    .. "Exit immediately or you will be engaged.",
                string.upper(zone.country), zone.country)
        end
        announce(intruder_group, msg)
    end
end

-- The shadow launch, at WARN_DWELL_S. Separate from the hail above so the
-- radio call is immediate and the interceptor is not.
local function warn(state, intruder_group)
    state.warned = true
    local zone = zones[state.zone]
    local zi = state.zone
    local shadow = spawn_shadow(zone, zi, state.name, state.side, state.px, state.pz)
    if shadow then
        start_vector_loop()
    end
end

local function scan_group(group, side, now)
    local lead = lead_unit(group)
    if not lead then
        return
    end
    local in_air = true
    pcall(function()
        in_air = lead:inAir()
    end)
    if not in_air then
        return
    end
    local name = group:getName() or ""
    if string.find(name, "NEUTRAL AF", 1, true) or string.find(name, "NEUTRAL SAM", 1, true) then
        return
    end
    local p = lead:getPoint()
    local state = intruders[name]
    for zi, zone in ipairs(zones) do
        -- This intruder's own side decides: a country open to blue and closed
        -- to red must wave one through and intercept the other.
        local is_blue = (side == coalition.side.BLUE)
        local permitted = is_blue and zone.permits_blue
            or (side == coalition.side.RED) and zone.permits_red
        -- No floor for this side means no sanctuary: any altitude trips it.
        -- Written long-hand deliberately: `is_blue and floor_blue_m or
        -- floor_red_m` reads the RED floor whenever blue's is nil, which is
        -- exactly the no-floor case this line exists to handle.
        local floor = zone.floor_red_m
        if is_blue then
            floor = zone.floor_blue_m
        end
        local below = (floor == nil) or (p.y < floor)
        if zone.enforces
            and not permitted
            and below
            and in_bbox(zone, p.x, p.z)
            and in_polygon(zone, p.x, p.z) then
            if not state then
                state = {
                    name = name,
                    zone = zi,
                    side = side,
                    dwell = 0,
                    hailed = false,
                    warned = false,
                    escalated = false,
                    is_player = false,
                    last_inside = now,
                }
                intruders[name] = state
            end
            -- Kept fresh every scan: the alert flight launches relative to
            -- where the intruder actually is, not to the country's midpoint.
            state.px, state.pz = p.x, p.z
            state.zone = zi
            state.dwell = state.dwell + SCAN_INTERVAL_S
            state.last_inside = now
            state.is_player = is_player_group(group)
            -- Told at once; intercepted only if you stay.
            if not state.hailed then
                hail(state, group)
            end
            if not state.warned and state.dwell >= WARN_DWELL_S then
                warn(state, group)
            end
            -- Players only, by DM call: AI intruders are shadowed, never engaged.
            if state.is_player and not state.escalated and state.dwell >= ENGAGE_DWELL_S then
                escalate(state, group)
            end
            return
        end
    end
    -- Outside every zone: pre-escalation states cool off and stand their shadow down.
    if state and not state.escalated and (now - state.last_inside) > EXIT_GRACE_S then
        local zone = zones[state.zone]
        local shadow = shadow_for(name)
        if shadow then
            stand_down(zone, shadow)
        end
        intruders[name] = nil
    end
end

local function scan()
    local now = timer.getTime()
    for _, side in ipairs({ coalition.side.RED, coalition.side.BLUE }) do
        for _, category in ipairs({ Group.Category.AIRPLANE, Group.Category.HELICOPTER }) do
            pcall(function()
                for _, group in ipairs(coalition.getGroups(side, category) or {}) do
                    pcall(function()
                        scan_group(group, side, now)
                    end)
                end
            end)
        end
    end
    return now + SCAN_INTERVAL_S
end

---------------------------------------------------------------------------------------------------
-- Hostile-act escalation: a weapon released inside the border, or fire on the shadower.
---------------------------------------------------------------------------------------------------
local event_handler = {}
function event_handler:onEvent(event)
    pcall(function()
        if not event or not event.initiator then
            return
        end
        if event.id == world.event.S_EVENT_SHOT then
            local grp = event.initiator.getGroup and event.initiator:getGroup()
            if not grp then
                return
            end
            local state = intruders[grp:getName() or ""]
            -- `warned` is required here and deliberately NOT on the HIT branch
            -- below: a bomb dropped before they have said anything is a strike
            -- that happens to be inside the border, but shooting at the flight
            -- shadowing you is unambiguous whenever it happens.
            if state and state.warned and not state.escalated and state.is_player then
                escalate(state, grp)
            end
        elseif event.id == world.event.S_EVENT_HIT then
            local target = event.target
            if not target or not target.getGroup then
                return
            end
            local tgroup = target:getGroup()
            local tname = tgroup and tgroup:getName() or ""
            if not string.find(tname, "NEUTRAL AF", 1, true) then
                return
            end
            local grp = event.initiator.getGroup and event.initiator:getGroup()
            if not grp then
                return
            end
            local state = intruders[grp:getName() or ""]
            if state and not state.escalated and state.is_player then
                escalate(state, grp)
            end
        end
    end)
end

---------------------------------------------------------------------------------------------------
-- Start.
---------------------------------------------------------------------------------------------------
local ok, err = pcall(function()
    draw_borders()
    world.addEventHandler(event_handler)
    timer.scheduleFunction(function()
        return scan()
    end, {}, timer.getTime() + SCAN_INTERVAL_S)
    local hostile = 0
    for _, z in ipairs(zones) do
        if z.enforces then
            hostile = hostile + 1
        end
    end
    log(string.format(
        "%d border zone(s) drawn, %d defended; warn %ds, engage %ds",
        #zones, hostile, WARN_DWELL_S, ENGAGE_DWELL_S))
end)
if not ok then
    env.error("NEUTRALBORDER|: setup error: " .. tostring(err))
end
