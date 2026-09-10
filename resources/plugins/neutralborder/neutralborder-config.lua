---------------------------------------------------------------------------------------------------
-- Neutral-faction border defense (§98) -- a neutral country's airspace, defended.
--
-- Reads dcsRetribution.neutralBorder (emitted only when neutral_border_defense is on and the
-- generator could build the map's zones; inert otherwise). Design + decisions:
-- docs/dev/design/414th-neutral-border-defense-notes.md. Constraints a reader could undo:
--   * A country stands SEVERAL batteries, one per stretch of war-facing frontier. One site
--     covered 3.5 % of Pakistan's border on the Afghanistan map, so the whole zone escalates
--     together -- never just the site the intruder happens to be near.
--   * They sit as true neutrals and swap to the intruder's OPPOSING coalition to shoot,
--     because a true-neutral unit cannot fire, ever -- do not "fix" the spawn to neutral.
--   * AI intruders are warned but NEVER escalated on (DM call). Only players earn the attack.
--   * The batteries are LIVE and neutral from t=0, not late-activated: the border has to have
--     something in it before you cross. sam_groups may still be empty for a zone that could
--     not be built, so guard it.
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
local WARN_DWELL_S = 30 -- inside the border this long -> second radio call
local ENGAGE_DWELL_S = 180 -- a PLAYER inside this long -> engaged
local SCAN_INTERVAL_S = 10 -- border scan cadence
local RETARGET_INTERVAL_S = 20 -- how often a hostile patrol re-picks its nearest target
local DRAW_BORDERS = true -- F10 border polylines (the §86 invisible-bubble lesson)

--: Vertices the FILL may use. The outline is one freeform however many points
--: it carries, and the web map draws them for free -- but DCS will not fill a
--: concave shape, so the fill is handed to MOOSE and comes back as one markup
--: per triangle. Measured: F10 markup count tracks vertex count about 1:1.
--:
--: So detail is free on the line and expensive in the wash. The border rings
--: ship at full resolution and only the fill is thinned to this, which keeps
--: the F10 cost where it was while the outline gets every point. At 5% alpha
--: under a precise outline the thinning is not visible.
local FILL_MAX_VERTS = 96

if dcsRetribution.plugins and dcsRetribution.plugins.neutralborder then
    local o = dcsRetribution.plugins.neutralborder
    WARN_DWELL_S = tonumber(o.warnDwellS) or WARN_DWELL_S
    ENGAGE_DWELL_S = tonumber(o.engageDwellS) or ENGAGE_DWELL_S
    SCAN_INTERVAL_S = tonumber(o.scanIntervalS) or SCAN_INTERVAL_S
    if o.drawBorders ~= nil then
        DRAW_BORDERS = (o.drawBorders == true) or (o.drawBorders == "true")
    end
end

local EXIT_GRACE_S = 120 -- outside this long (pre-escalation) -> intruder state cleared

local FT_TO_M = 0.3048
local MARKUP_ID_BASE = 96000 -- §98 block; one freeform id per zone
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
        -- An enforcing zone needs a battery to enforce with.
        -- Several batteries per country. Emitted as a list of { name = ... }.
        local sam_groups = {}
        for _, entry in ipairs(raw.samGroups or {}) do
            if entry.name then
                sam_groups[#sam_groups + 1] = tostring(entry.name)
            end
        end
        local usable = (not enforces) or (#sam_groups > 0 and has_origin)
        if #verts >= 3 and usable then
            zones[#zones + 1] = {
                -- Its own position in `zones`, so an intruder state (which
                -- stores the zone index) can be matched back to it.
                index = #zones + 1,
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
                origin_label = tostring(raw.originLabel or "defended"),
                -- Where to write the country's name: inside the polygon by
                -- construction (shapely's representative point), which a
                -- centroid is not on a concave country.
                label_x = tonumber(raw.labelX),
                label_z = tonumber(raw.labelZ),
                -- The STANDING batteries' group names. Live neutral groups from
                -- mission start, not templates to clone. Empty for a zone the
                -- generator could not build, which never enforces.
                sam_groups = sam_groups,
                red_country = tonumber(raw.redCountryId),
                blue_country = tonumber(raw.blueCountryId),
                verts = verts,
                bbox = { minx = minx, maxx = maxx, minz = minz, maxz = maxz },
                -- runtime
                swapped = false, -- the battery has been made hostile and stays so
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
        -- The country's name is already the line above, so a label that repeats
        -- it says it twice. The origin used to be an airfield and no longer is.
        local origin = zone.origin_label
        local prefix = zone.country .. " "
        if origin:sub(1, #prefix) == prefix then
            origin = origin:sub(#prefix + 1)
        end
        return "CLOSED - " .. origin
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
            -- Even stride, first vertex always kept, so the thinned ring still
            -- closes on itself and keeps the shape's extremes.
            local n = #zone.verts
            local stride = 1
            if n > FILL_MAX_VERTS then
                stride = math.ceil(n / FILL_MAX_VERTS)
            end
            local pts = {}
            for i = 1, n, stride do
                local v = zone.verts[i]
                pts[#pts + 1] = { x = v.x, y = v.z }
            end
            if #pts < 3 then
                return
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

local intruders = {} -- group name -> state

---------------------------------------------------------------------------------------------------
-- The standing patrol, and the one moment it stops being neutral.
--
-- The CAP is a real group, airborne from mission start, flying an orbit inside its own border under
-- a NEUTRAL country. A neutral cannot fire (the engine verdict), and it does not need to while
-- nobody is violating. On escalation its coalition is swapped in place so it can.
--
-- Why not scramble one: measured 2026-08-28/29. Cold on the ramp took 270 s to get airborne; a
-- runway start still launched behind the intruder; and once up it could not hold a standoff,
-- because the closing geometry belongs to the intruder -- 22.8 NM to 6.5 NM while still shadowing.
-- A patrol already on station never plays that game, and it is visible BEFORE you cross, which is
-- the deterrence the scramble could never provide.
---------------------------------------------------------------------------------------------------

--: A second battery, for the case where BOTH sides violate the same country.
--:
--: A battery can only be on one coalition, and once swapped it is an ALLY of
--: the other side -- it will not fire on them. A country fighting both at once
--: needs a second site, cloned from its own template onto the other coalition.
local function second_battery(zone, intruder_side)
    if zone.second_groups then
        return zone.second_groups
    end
    if #zone.sam_groups == 0 then
        return nil
    end
    local clones = {}
    for index, source in ipairs(zone.sam_groups) do
        local name = "NEUTRAL SAM2 " .. zone.country .. " " .. index
        local ok, err = pcall(function()
            local sp = SPAWN:NewWithAlias(source, name)
            sp:InitCountry(clone_country(zone, intruder_side))
            sp:InitCoalition(opposing(intruder_side))
            -- 0 = no cap. A nonzero unit cap smaller than the template silently
            -- refuses the whole spawn (Moose.lua:21358).
            sp:InitLimit(0, 0)
            sp:Spawn()
        end)
        if ok then
            clones[#clones + 1] = name
        else
            log("second battery failed for " .. zone.country .. ": " .. tostring(err))
        end
    end
    if #clones == 0 then
        return nil
    end
    zone.second_groups = clones
    zone.second_side = intruder_side
    log(zone.country .. " put " .. #clones .. " more batteries up against the other side")
    return clones
end

--: Swap the standing neutral battery onto the coalition opposing the intruder.
--:
--: This is the whole feature in one call: a true neutral cannot fire, ever, so
--: the only way the border bites is to stop being neutral at the moment it
--: does. Respawn is a Destroy(false) plus a re-add 0.1 s later -- for a ground
--: battery that is free, since it has no velocity to lose (the aircraft patrol
--: this replaced measured 211 m/s within 5 s of the same call, 2026-09-01).
local function swap_to_shooting(zone, intruder_side)
    if #zone.sam_groups == 0 then
        return nil -- nothing was built here
    end
    if zone.swapped then
        if intruder_side ~= zone.engaged_side then
            return second_battery(zone, intruder_side)
        end
        return zone.sam_groups
    end
    -- The COUNTRY escalates, not the site you happened to fly past: every
    -- battery it stands swaps together, or the rest of the border stays a
    -- neutral you can cross unopposed after being declared hostile.
    local swapped = {}
    for _, name in ipairs(zone.sam_groups) do
        local grp = GROUP:FindByName(name)
        if grp and grp:IsAlive() then
            local ok, err = pcall(function()
                local template = grp:GetTemplate()
                template.CountryID = clone_country(zone, intruder_side)
                template.CoalitionID = opposing(intruder_side)
                grp:Respawn(template, true)
            end)
            if ok then
                swapped[#swapped + 1] = name
            else
                log("coalition swap failed for " .. name .. ": " .. tostring(err))
            end
        end
    end
    if #swapped == 0 then
        log("no standing battery for " .. zone.country .. " -- nothing to engage with")
        return nil
    end
    zone.swapped = true
    zone.engaged_side = intruder_side
    log(zone.country .. " turned " .. #swapped .. " batteries hostile to the intruder")
    return swapped
end

--: Which groups are answering a given intruder side.
local function batteries_for(zone, intruder_side)
    if zone.swapped and intruder_side ~= zone.engaged_side then
        return zone.second_groups or {}
    end
    return zone.sam_groups
end

local function escalate(state, intruder_group)
    if state.escalated or not state.is_player then
        return
    end
    state.escalated = true
    local zone = zones[state.zone]
    announce(intruder_group, string.format(
        "%s AIR FORCE: You were warned. %s air defense is ENGAGING.",
        string.upper(zone.country), zone.country))
    swap_to_shooting(zone, state.side)
    -- No attack task, and none is wanted: a SAM acquires and engages whatever
    -- enters its envelope once it is weapons-free, so the retarget loop the
    -- fighter patrol needed is gone with it. Respawn re-adds 0.1 s later, so
    -- ask DCS the group exists before MOOSE touches it.
    timer.scheduleFunction(function()
        pcall(function()
            for _, bname in ipairs(batteries_for(zone, state.side)) do
                local dg = Group.getByName(bname)
                if dg and dg:isExist() then
                    local mg = GROUP:FindByName(bname)
                    if mg then
                        mg:OptionROEWeaponFree()
                        mg:OptionAlarmStateRed()
                    end
                end
            end
        end)
        return nil
    end, {}, timer.getTime() + 2)
    log("ESCALATED on " .. state.name)
end

---------------------------------------------------------------------------------------------------
-- The border watch.
---------------------------------------------------------------------------------------------------
-- The radio call, on the FIRST scan that finds you inside. It used to wait for
-- WARN_DWELL_S, which put the hail half a minute after the crossing that caused
-- it -- flown 2026-08-28: "pop it immediately on entry to airspace". The scan
-- interval bounds "immediately" at SCAN_INTERVAL_S.
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

-- The second radio call, at WARN_DWELL_S. Nothing is launched or tasked: the
-- batteries have been standing since mission start and stay neutral until the
-- escalation swap. This call is the last warning before that.
local function warn(state, intruder_group)
    state.warned = true
    local zone = zones[state.zone]
    if state.is_player then
        announce(intruder_group, string.format(
            "%s AIR FORCE: Our air defenses are tracking you. Leave %s airspace.",
            string.upper(zone.country), zone.country))
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
    -- A country's own units are never its intruders. The scan is airborne
    -- groups only, so a ground battery cannot appear here -- the guard is kept
    -- for the second battery's spawn name and costs a string compare.
    if string.find(name, "NeutralBorder|", 1, true)
        or string.find(name, "NEUTRAL AF", 1, true)
        or string.find(name, "NEUTRAL SAM", 1, true) then
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
            -- Players only, by DM call: AI intruders are warned, never engaged.
            if state.is_player and not state.escalated and state.dwell >= ENGAGE_DWELL_S then
                escalate(state, group)
            end
            return
        end
    end
    -- Outside every zone long enough: forget the intruder. The patrol never
    -- left its orbit, so there is nothing to recall -- and an escalated zone
    -- stays hostile, because a country that has been shot at does not un-swap.
    if state and not state.escalated and (now - state.last_inside) > EXIT_GRACE_S then
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
-- Hostile-act escalation: a weapon released inside the border, or fire on the patrol.
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
            -- that has just warned you is unambiguous whenever it happens.
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
