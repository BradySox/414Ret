---------------------------------------------------------------------------------------------------
-- Carrier deck dressing -- §72's runtime half. Design and the flown findings are in
-- docs/dev/design/414th-carrier-deck-decor-notes.md.
--
-- Statics cannot drive, so clearing the recovery corridor means striking them below
-- (StaticObject:destroy). Fires on whichever comes first: a friendly fixed-wing in
-- the astern cone, or a fallback timer so a hazard never waits on detection.
--
-- Reads dcsRetribution.deckDecor (game/missiongenerator/deckdecorluadata.py); inert
-- when absent. BRC is generation-time, so astern is BRC + 180 with no runtime
-- orientation API.
--
-- The load-bearing parts:
--
--  * The cone's three gates each exist because a flown test falsified the naive
--    version (2026-07-18) -- see the gate comments at the call site before relaxing
--    any of them.
--  * ONE sanctioned spawn, for the recovery-phase tier only, because gear ranged
--    forward cannot be generated into the miz. Do not widen it: a second spawn
--    caller makes this a spawner, with a different failure surface.
---------------------------------------------------------------------------------------------------

if not (dcsRetribution and dcsRetribution.deckDecor and dcsRetribution.deckDecor.boats) then
    return
end

local boatsData = dcsRetribution.deckDecor.boats

-- Defaults. Overridable via the plugin options (dcsRetribution.plugins.deckdecor).
local POLL_S = 10 -- s between astern-cone checks
local GRACE_S = 60 -- s before the watch starts (startup storm protection)
local FALLBACK_MIN = 35 -- minutes after mission start: clear regardless
local CONE_DIST_NM = 4.5 -- cone range astern
-- 1000 ft, not the recovery-pattern 3000: the flown false trip (2026-07-18)
-- was freshly-launched jets turning back past the boat low astern -- they are
-- through 1000 ft within a minute of the cat, while a CASE I initial (800 ft)
-- and a CASE III final both fly below it.
local CONE_ALT_FT = 1000 -- only traffic below this trips the cone
local CONE_HALF_DEG = 50 -- half-angle either side of dead astern
local CONE_CLOSING_KTS = 30 -- must be closing on the boat at least this fast
local CONE_POLLS = 2 -- consecutive qualifying polls before the clear fires
local SHOW_CUE = true -- one-line "deck respotted" message on clear

if dcsRetribution.plugins and dcsRetribution.plugins.deckdecor then
    local o = dcsRetribution.plugins.deckdecor
    POLL_S = tonumber(o.pollS) or POLL_S
    GRACE_S = tonumber(o.graceS) or GRACE_S
    FALLBACK_MIN = tonumber(o.fallbackMin) or FALLBACK_MIN
    CONE_DIST_NM = tonumber(o.coneDistNm) or CONE_DIST_NM
    CONE_ALT_FT = tonumber(o.coneAltFt) or CONE_ALT_FT
    CONE_HALF_DEG = tonumber(o.coneHalfDeg) or CONE_HALF_DEG
    CONE_CLOSING_KTS = tonumber(o.coneClosingKts) or CONE_CLOSING_KTS
    if o.showCue ~= nil then
        SHOW_CUE = o.showCue == true or o.showCue == "true"
    end
end

local AB_MARGIN_S = 300 -- clear this long before the Airboss recovery window
if dcsRetribution.plugins and dcsRetribution.plugins.deckdecor then
    AB_MARGIN_S = tonumber(dcsRetribution.plugins.deckdecor.airbossMarginS) or AB_MARGIN_S
end

local CONE_DIST_M = CONE_DIST_NM * 1852.0
local CONE_ALT_M = CONE_ALT_FT * 0.3048
local CONE_COS = math.cos(math.rad(CONE_HALF_DEG))
local CONE_CLOSING_MS = CONE_CLOSING_KTS * 0.51444

-- The Airboss tie-in: the sibling airboss plugin (default ON) schedules its
-- recovery window windowStartOption minutes into the mission and STEERS the
-- boat into wind (with U-turns) while the window is open -- both reasons the
-- corridor must already be clean by then. When that plugin's options are
-- present in the mission, pull the clear deadline forward to window start
-- minus the margin; the astern cone still handles early or unscheduled
-- traffic, and the plain fallback covers missions without Airboss.
local CLEAR_DEADLINE_S = FALLBACK_MIN * 60.0
local DEADLINE_WHY = "fallback timer"
do
    local ab = dcsRetribution.plugins and dcsRetribution.plugins.airboss
    local windowStartMin = ab and tonumber(ab.windowStartOption)
    if windowStartMin then
        local byWindow = windowStartMin * 60.0 - AB_MARGIN_S
        local floorS = GRACE_S + POLL_S
        if byWindow < floorS then
            byWindow = floorS
        end
        if byWindow < CLEAR_DEADLINE_S then
            CLEAR_DEADLINE_S = byWindow
            DEADLINE_WHY = "airboss recovery window"
        end
    end
end

local function log(msg)
    env.info("DECKDECOR|: " .. msg)
end

-- Mutable per-boat state built from the emitted records.
local boats = {}
for i = 1, #boatsData do
    local b = boatsData[i]
    local brc = tonumber(b.brc) or 0
    -- Recovery-phase placements arrive as emitted strings (the Lua bridge
    -- writes every scalar as one); normalise once here so the spawn path can
    -- do arithmetic. A malformed row is dropped, not defaulted to 0/0 -- that
    -- would put deck gear on the ship's own origin.
    local recoverySpawns = {}
    for j = 1, #(b.recoverySpawns or {}) do
        local r = b.recoverySpawns[j]
        local rx, ry, ra = tonumber(r.x), tonumber(r.y), tonumber(r.angle)
        if rx and ry and ra and r.type and r.category then
            table.insert(recoverySpawns, {
                type = tostring(r.type),
                category = tostring(r.category),
                shape = r.shape and tostring(r.shape) or nil,
                x = rx,
                y = ry,
                angle = ra,
            })
        end
    end
    table.insert(boats, {
        group = tostring(b.group or ""),
        unit = tostring(b.unit or ""),
        side = tonumber(b.side) or 2,
        brc = brc,
        -- No respot while this deck is still launching. The generator knows the
        -- last departure off this boat (deckdecorluadata.launch_cycle_ends_at);
        -- 0 means nothing launches here, so the cone and the deadline stay in
        -- sole charge. Flown 2026-08-16: the recovery set spawned at t+79 s,
        -- 375 s before the player's takeoff roll, putting three static Hornets
        -- in his taxi lane -- one 8.66 m off his track. The cone had tripped on
        -- something not identifiable from the recording, so this bounds what a
        -- spurious trip can do instead of relying on finding every trip source.
        earliestClearS = tonumber(b.earliestClearS) or 0,
        recoverySpawns = recoverySpawns,
        spawnedRecovery = false,
        -- Unit astern vector in map coords (x = north, z = east): the reciprocal
        -- of the BRC the boat steams all mission.
        sternX = -math.cos(math.rad(brc)),
        sternZ = -math.sin(math.rad(brc)),
        clearNames = b.clearNames or {},
        cleared = false,
        -- unit name -> last time it was seen within DECK_STAMP_M of the boat;
        -- bounded by the airframes that ever touch the deck.
        outboundRoster = {},
    })
end

-- The 2026-07-18 night fly falsified the world-frame closing gate twice (GW at
-- t+74s pre-hardening, TR at t+171s post-hardening): deck-parked jets RIDE the
-- steaming boat, DCS reports units on a moving deck as inAir(), and the aft
-- parking rows sit 130-170 m astern of the ship's pivot point -- so the parked
-- row itself read as "low astern, closing at boat speed", and a jet fresh off
-- the cat is low astern and genuinely closing as it turns back. Three rules
-- kill the family for good:
--   * closing is SHIP-RELATIVE (a deck rider closes at ~0 however fast the
--     boat steams; a real recovery closes at 120+ kt regardless),
--   * nothing within DECK_STAMP_M of the boat can trip -- that is the deck
--     footprint and the launch bubble, not approach airspace,
--   * the outbound roster: a unit seen inside DECK_STAMP_M -- parked, taxiing,
--     or on the cat stroke -- is stamped as this boat's own traffic and cannot
--     read as recovery traffic for OUTBOUND_SUPPRESS_S after it was last seen
--     there. A genuine recovery starts miles out and is never stamped.
local DECK_STAMP_M = 400
local OUTBOUND_SUPPRESS_S = 600

local function boatUnit(boat)
    local grp = Group.getByName(boat.group)
    if not grp or not grp:isExist() then
        return nil
    end
    local units = grp:getUnits()
    for i = 1, #units do
        local u = units[i]
        if u and u:isExist() then
            return u
        end
    end
    return nil
end

-- Recovery-phase respot: the mirror of striking the launch set below. These
-- placements are deliberately absent from the mission file -- the bow has to
-- be a launch deck until launches are over -- so they are SPAWNED here, on the
-- same trigger, linked to the moving hull.
--
-- MOOSE's SPAWNSTATIC is the only path that writes the three-level linked
-- static (linkUnit + linkOffset + offsets{x,y,angle}) at runtime; a plain
-- coalition.addStaticObject would drop the gear at a world point and the boat
-- would steam out from under it. Absent MOOSE, this no-ops and the strike-below
-- half still runs -- the recovery tier is cosmetic and must never be able to
-- take the rest of the script down with it.
local function spawnRecovery(boat)
    if boat.spawnedRecovery or not boat.recoverySpawns or #boat.recoverySpawns == 0 then
        return 0
    end
    boat.spawnedRecovery = true
    if not (SPAWNSTATIC and UNIT and COORDINATE) then
        log(boat.unit .. ": MOOSE absent, recovery-phase dressing skipped")
        return 0
    end
    local dcsUnit = boatUnit(boat)
    local mooseUnit = UNIT:FindByName(boat.unit)
    if not (dcsUnit and mooseUnit) then
        return 0
    end
    local countryId = dcsUnit:getCountry()
    local p = dcsUnit:getPoint()
    local n = 0
    for i = 1, #boat.recoverySpawns do
        local it = boat.recoverySpawns[i]
        local ok = pcall(function()
            local sp = SPAWNSTATIC:NewFromType(it.type, it.category, countryId)
            if it.shape then
                sp:InitShape(it.shape)
            end
            -- Offsets are the ship-frame placement; DCS re-derives the world
            -- position every frame, so the coordinate below is only a t=0
            -- fallback. Heading likewise: BRC is the course the boat steams
            -- all mission, so BRC + the authored facing reads correctly.
            sp:InitLinkToUnit(mooseUnit, it.x, it.y, it.angle)
            sp:SpawnFromCoordinate(
                COORDINATE:New(p.x, p.y, p.z),
                (boat.brc + it.angle) % 360,
                boat.unit .. " recovery decor " .. string.format("%02d", i)
            )
        end)
        if ok then
            n = n + 1
        end
    end
    log(boat.unit .. ": spawned " .. n .. " recovery-phase static(s) forward")
    return n
end

local function clearBoat(boat, why)
    boat.cleared = true
    local n = 0
    for i = 1, #boat.clearNames do
        local s = StaticObject.getByName(boat.clearNames[i])
        if s then
            s:destroy()
            n = n + 1
        end
    end
    spawnRecovery(boat)
    log(boat.unit .. ": struck " .. n .. " launch-phase static(s) below (" .. why .. ")")
    if SHOW_CUE and n > 0 then
        trigger.action.outTextForCoalition(
            boat.side,
            boat.unit .. " deck respotted for recovery -- the alert aircraft are struck below.",
            8
        )
    end
end

local function approachDetected(boat, bp, bv, now)
    -- Returns the tripping unit's signature, or nil. Trips only for traffic
    -- that LOOKS like a recovery: low, astern, CLOSING on the boat in the
    -- boat's own frame, and not something this deck just launched (the
    -- outbound roster). The caller additionally debounces over CONE_POLLS
    -- consecutive polls so a transient closing moment never clears the deck.
    -- Keeps walking after a trip so every deck unit still gets its roster
    -- stamp for this poll.
    --
    -- The signature is returned rather than a bare boolean because the cone
    -- fired once with nothing in it (flown 2026-08-16): a faithful replay of
    -- this function over the whole Tacview never trips, and the only objects
    -- ever inside CONE_DIST_M were four deck Hornets inside the stamp bubble,
    -- the boat's own rescue helo (a rotorcraft this scan cannot see, and ahead
    -- of the beam anyway) and a cruiser 129 degrees off the stern. An
    -- unattributable clear costs a Tacview forensics session; a named one
    -- costs a log line.
    local roster = boat.outboundRoster
    local tripped = nil
    local groups = coalition.getGroups(boat.side, Group.Category.AIRPLANE)
    for i = 1, #groups do
        local units = groups[i]:getUnits()
        for j = 1, #units do
            local u = units[j]
            if u and u:isExist() then
                local p = u:getPoint()
                local dx = p.x - bp.x
                local dz = p.z - bp.z
                local dist = math.sqrt(dx * dx + dz * dz)
                if dist < DECK_STAMP_M then
                    -- On or over the deck (parked, taxiing, cat stroke,
                    -- bolter): this boat's own traffic, never a trip source.
                    roster[u:getName()] = now
                elseif tripped == nil and u:inAir() and dist < CONE_DIST_M then
                    local stamped = roster[u:getName()]
                    if
                        (stamped == nil or now - stamped > OUTBOUND_SUPPRESS_S)
                        and p.y - bp.y < CONE_ALT_M
                    then
                        local cosang = (dx * boat.sternX + dz * boat.sternZ) / dist
                        if cosang > CONE_COS then
                            local v = u:getVelocity()
                            local closing = -(
                                ((v.x or 0) - (bv.x or 0)) * dx
                                + ((v.z or 0) - (bv.z or 0)) * dz
                            ) / dist
                            if closing > CONE_CLOSING_MS then
                                tripped = string.format(
                                    "%s at %.2f NM, %.0f deg off stern, %.0f ft, closing %.0f kt",
                                    tostring(u:getName()),
                                    dist / 1852.0,
                                    math.deg(math.acos(math.max(-1, math.min(1, cosang)))),
                                    (p.y - bp.y) / 0.3048,
                                    closing / 0.51444
                                )
                            end
                        end
                    end
                end
            end
        end
    end
    return tripped
end

local function tick()
    local pending = 0
    for i = 1, #boats do
        local boat = boats[i]
        -- A launching deck is never a recovery deck. Holds BOTH the cone and
        -- the deadline: the deadline is the airboss recovery window, and a
        -- window that opens mid-launch is itself the thing being guarded
        -- against.
        local launching = timer.getTime() < boat.earliestClearS
        if launching and not boat.loggedHold then
            boat.loggedHold = true
            log(boat.unit .. ": still launching, respot held until " ..
                string.format("%.0f", boat.earliestClearS) .. "s")
        end
        if not boat.cleared and not launching then
            if timer.getTime() >= CLEAR_DEADLINE_S then
                clearBoat(boat, DEADLINE_WHY)
            else
                local bu = boatUnit(boat)
                if bu == nil then
                    -- Boat gone (sunk/despawned): nothing left to protect. Say
                    -- so -- this exit stopped the watch silently for a month
                    -- when an emitter bug shipped an empty group name, and a
                    -- deck that never respots looks identical to a disabled
                    -- feature (flown 2026-08-16).
                    boat.cleared = true
                    log("no unit for group '" .. boat.group ..
                        "'; stopping the watch for this boat")
                else
                    local bp = bu:getPoint()
                    local bv = bu:getVelocity()
                    local ok, tripped =
                        pcall(approachDetected, boat, bp, bv, timer.getTime())
                    if not ok then
                        log(boat.unit .. ": cone check errored -- " .. tostring(tripped))
                    end
                    if ok and tripped then
                        boat.approachPolls = (boat.approachPolls or 0) + 1
                        -- Every trip poll, not just the one that clears: a
                        -- single spurious trip is the early warning for the
                        -- pair that respots the deck.
                        log(boat.unit .. ": cone trip " .. boat.approachPolls ..
                            "/" .. CONE_POLLS .. " -- " .. tripped)
                        if boat.approachPolls >= CONE_POLLS then
                            clearBoat(boat, "recovery traffic astern: " .. tripped)
                        end
                    else
                        boat.approachPolls = 0
                    end
                end
            end
        end
        if not boat.cleared then
            pending = pending + 1
        end
    end
    if pending > 0 then
        return timer.getTime() + POLL_S
    end
    return nil
end

if #boats > 0 then
    timer.scheduleFunction(function(_, _)
        return tick()
    end, {}, timer.getTime() + GRACE_S)
    log("armed -- " .. #boats .. " boat(s), clear by " ..
        string.format("%.0f", CLEAR_DEADLINE_S) .. "s (" .. DEADLINE_WHY .. "), cone " ..
        CONE_DIST_NM .. " NM/" .. CONE_ALT_FT .. " ft astern")
end
