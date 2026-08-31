-- Formation Lead Trainer -- grades how followable YOUR flying is, not where you put bombs.
--
-- See docs/dev/design/414th-formation-lead-trainer-notes.md
--
-- Runs a point-mass virtual wingman that is deliberately NOT glued to your wing: it
-- perceives instantly but responds through a reaction delay, and its thrust, drag and
-- G are saturated. It falls out of position exactly where a human would.
--
-- Vanilla DCS scripting engine only -- no MOOSE, no MIST, no mod units. Load it with a
-- DO SCRIPT FILE trigger in any mission, or tick the plugin in Retribution.
--
-- Constraints that shape the code:
--  * The whole model reduces to dv = omega * d and a = d * omega_dot -- the wingman's
--    speed and acceleration demand both scale LINEARLY with formation spacing. Every
--    limit below is derived from those two, never hand-set per formation.
--  * Reaction lag belongs on the CONTROL command, not on perceived position. Light is
--    instant; a wingman sees where you are and is late reacting to it. Delaying the
--    position instead makes the model trail you by v*tau and hides the real failure.
--  * Roll is horizon-referenced via forward x world-up, which degenerates at vertical.
--    Guarded, because MOOSE's copy of this formula is not and returns nan going up.
--  * Read-only. This script spawns nothing, commands nothing and owns no kills.

FormationLeadTrainer = {}
local FLT = FormationLeadTrainer

FLT.VERSION = "1.0"

-- ---------------------------------------------------------------------------
-- Tunables
-- ---------------------------------------------------------------------------

FLT.cfg = {
    sample_hz = 10,

    -- Fallback lag, used only if a formation omits its own. Real lag is per-spacing
    -- (see FORMATIONS): a fingertip wingman is locked on a wingtip 60 ft away and
    -- tracks continuously; at 1.5 nm he is cross-checking every few seconds.
    reaction_lag = 0.7,

    -- Seconds the wingman is allowed to take to erase a bank mismatch before it
    -- counts as divergence. Sets the roll-rate limit together with reaction_lag.
    catchup_time = 1.5,

    -- Roll rate a wingman can actually USE while also holding a position. Nothing
    -- like the airframe's 200+ deg/s -- they are flying formation, not rolling.
    wm_roll_max = 40.0,

    -- Range inside which closure is a mid-air, metres. Absolute, never a fraction of
    -- spacing -- being 1000 ft apart in combat spread is close formation, not danger.
    danger_range = 60.0,

    -- Point-mass envelope. accel/decel are longitudinal (throttle and drag);
    -- g_max is incremental manoeuvre load, so gravity is not modelled separately.
    wm_accel_max = 2.5,
    wm_decel_max = 3.5,
    wm_g_max = 4.0,

    -- Short-term speed the wingman can trade to stay outside in a turn.
    wm_spare_speed = 30.0,

    -- Position errors that earn a call, in metres, scaled by formation spacing.
    err_warn_frac = 0.35,
    err_lost_frac = 1.50,

    min_speed = 60.0,   -- m/s below which nothing is graded (taxi, takeoff roll)
    min_agl = 60.0,     -- m AGL below which nothing is graded (pattern, landing)

    msg_cooldown = 6.0, -- seconds between repeats of the same coaching call
}

-- Lateral / aft / vertical offset of the virtual wingman, in the lead's body frame.
-- Metres, centre to centre. Spacing is the ONLY thing that changes between these --
-- every limit is derived from it.
-- lag is the wingman's control delay; kp/kd/ki are his tracking loop. All tighten as
-- the formation closes up, which is why a fingertip wingman survives a roll-in that
-- would strip a spread wingman off the formation entirely.
FLT.FORMATIONS = {
    { key = "fingertip", name = "Fingertip", right = 18, aft = 12, down = 2,
      lag = 0.30, kp = 3.0, kd = 3.0, ki = 0.80 },
    { key = "route", name = "Route", right = 150, aft = 60, down = 0,
      lag = 0.50, kp = 1.0, kd = 1.8, ki = 0.30 },
    { key = "cruise", name = "Cruise (0.5nm)", right = 900, aft = 150, down = 0,
      lag = 0.90, kp = 0.3, kd = 1.0, ki = 0.10 },
    { key = "spread", name = "Combat spread (1.5nm)", right = 2780, aft = 0, down = 0,
      lag = 1.50, kp = 0.2, kd = 0.8, ki = 0.05 },
}

local G = 9.80665
local MPS_TO_KT = 1.94384
local M_TO_FT = 3.28084

-- ---------------------------------------------------------------------------
-- Vector helpers
-- ---------------------------------------------------------------------------

local function vadd(a, b) return { x = a.x + b.x, y = a.y + b.y, z = a.z + b.z } end
local function vsub(a, b) return { x = a.x - b.x, y = a.y - b.y, z = a.z - b.z } end
local function vscale(a, s) return { x = a.x * s, y = a.y * s, z = a.z * s } end
local function vdot(a, b) return a.x * b.x + a.y * b.y + a.z * b.z end
local function vlen(a) return math.sqrt(vdot(a, a)) end

local function vcross(a, b)
    return {
        x = a.y * b.z - a.z * b.y,
        y = a.z * b.x - a.x * b.z,
        z = a.x * b.y - a.y * b.x,
    }
end

local function vnorm(a)
    local l = vlen(a)
    if l < 1e-6 then return { x = 0, y = 0, z = 0 } end
    return vscale(a, 1.0 / l)
end

-- Clamp a vector's magnitude, keeping direction.
local function vclamp(a, maxlen)
    local l = vlen(a)
    if l <= maxlen or l < 1e-6 then return a end
    return vscale(a, maxlen / l)
end

local function clamp(v, lo, hi)
    if v < lo then return lo end
    if v > hi then return hi end
    return v
end

-- Shortest signed difference between two headings, radians.
local function angdiff(a, b)
    local d = a - b
    while d > math.pi do d = d - 2 * math.pi end
    while d < -math.pi do d = d + 2 * math.pi end
    return d
end

-- ---------------------------------------------------------------------------
-- Attitude from a DCS orientation matrix
-- ---------------------------------------------------------------------------

-- pos.x is forward, pos.y is up, pos.z is right, in world axes (y is altitude).
local function headingOf(pos)
    local h = math.atan2(pos.x.z, pos.x.x)
    if h < 0 then h = h + 2 * math.pi end
    return h
end

local function pitchOf(pos)
    return math.asin(clamp(pos.x.y, -1, 1))
end

-- Horizon-referenced roll: right bank positive. The cross product shrinks to zero
-- pointing straight up or down, so bail rather than divide by it -- the alternative
-- is a nan that poisons every rate downstream.
local function rollOf(pos)
    local cp = vcross(pos.x, { x = 0, y = 1, z = 0 })
    local n = vlen(cp)
    if n < 1e-3 then return nil end
    local r = math.acos(clamp(vdot(cp, pos.z) / n, -1, 1))
    if pos.z.y > 0 then r = -r end
    return r
end

-- ---------------------------------------------------------------------------
-- Delay line, for the wingman's reaction lag
-- ---------------------------------------------------------------------------

local Delay = {}
Delay.__index = Delay

function Delay.new(slots)
    return setmetatable({ buf = {}, n = math.max(1, slots), i = 0 }, Delay)
end

-- Push the newest command and return the one from `n` samples ago, or the newest
-- while the buffer is still filling.
function Delay:push(v)
    self.i = self.i + 1
    local out = self.buf[(self.i % self.n) + 1] or v
    self.buf[(self.i % self.n) + 1] = v
    return out
end

-- ---------------------------------------------------------------------------
-- The virtual wingman
-- ---------------------------------------------------------------------------

local Wingman = {}
Wingman.__index = Wingman

function Wingman.new(cfg, formation, lead)
    local self = setmetatable({}, Wingman)
    self.cfg = cfg
    self.formation = formation
    self.lag = formation.lag or cfg.reaction_lag
    self.kp = formation.kp or 1.0
    self.kd = formation.kd or 1.6
    self.ki = formation.ki or 0.0
    self.integ = { x = 0, y = 0, z = 0 }
    self.delay = Delay.new(math.floor(self.lag * cfg.sample_hz + 0.5))
    self.pos = self:desiredPoint(lead)
    self.vel = { x = lead.vel.x, y = lead.vel.y, z = lead.vel.z }
    return self
end

-- Where the wingman is trying to be, in world axes.
function Wingman:desiredPoint(lead)
    local f = self.formation
    local o = lead.orient
    return vadd(lead.pos, vadd(vadd(
        vscale(o.z, f.right),
        vscale(o.x, -f.aft)),
        vscale(o.y, -f.down)))
end

function Wingman:spacing()
    local f = self.formation
    return math.sqrt(f.right * f.right + f.aft * f.aft + f.down * f.down)
end

function Wingman:update(lead, prevLead, dt)
    local des = self:desiredPoint(lead)

    -- Velocity of the desired point, not of the lead: in a turn the outside slot
    -- moves faster than the jet it hangs off. That difference IS omega * d.
    local desVel = lead.vel
    if prevLead then
        local prevDes = self:desiredPoint(prevLead)
        desVel = vscale(vsub(des, prevDes), 1.0 / dt)
    end

    -- Snap to the slot on the first real sample. Seeding from the lead's own position
    -- and velocity in the constructor puts the wingman one sample (v*dt -- 15 m at
    -- 300 kt) behind the slot, and the loop then saturates fighting a lag it invented.
    -- Fall through after snapping, never return early: an early return skips the
    -- integration step, so the next sample sees a v*dt gap and reports it as a peak.
    if not self.primed then
        self.primed = true
        self.pos = des
        self.vel = desVel
    end

    local errP = vsub(des, self.pos)
    local errV = vsub(desVel, self.vel)

    -- Measure BEFORE integrating. Reporting self.pos after the step compares the
    -- wingman at t+dt against the slot at t, which is a constant v*dt bias -- 15 m at
    -- 300 kt, gain-independent, and it reads as a permanent acute error.
    local e = vscale(errP, -1)
    local report = {
        aft = -vdot(e, lead.orient.x),
        lateral = vdot(e, lead.orient.z),
        vertical = vdot(e, lead.orient.y),
        total = vlen(e),
        closure = vdot(vsub(self.vel, lead.vel), vnorm(vsub(lead.pos, self.pos))),
        range = vlen(vsub(self.pos, lead.pos)),
    }

    self.integ = vclamp(vadd(self.integ, vscale(errP, dt)),
        self.cfg.wm_accel_max / math.max(self.ki, 0.01))
    local cmd = vadd(vadd(vscale(errP, self.kp), vscale(errV, self.kd)),
        vscale(self.integ, self.ki))

    -- Lag the command, never the perception. Then saturate it the way an airframe
    -- does: longitudinally by thrust and drag, laterally by available G.
    local a = self.delay:push(cmd)
    local vhat = vnorm(self.vel)
    local along = vdot(a, vhat)
    local perp = vsub(a, vscale(vhat, along))
    along = clamp(along, -self.cfg.wm_decel_max, self.cfg.wm_accel_max)
    perp = vclamp(perp, self.cfg.wm_g_max * G)
    a = vadd(vscale(vhat, along), perp)

    self.vel = vadd(self.vel, vscale(a, dt))
    self.pos = vadd(self.pos, vscale(self.vel, dt))

    return report
end

-- Exposed for the headless harness; nothing in the mission reads these.
FLT.Wingman = Wingman
FLT.Delay = Delay

-- ---------------------------------------------------------------------------
-- Derived limits -- all of them fall out of spacing
-- ---------------------------------------------------------------------------

-- Fastest roll-in the wingman can still match: they lose reaction_lag of bank and
-- must erase it inside catchup_time while also matching the ongoing rate.
function FLT.rollRateLimit(cfg, formation)
    local lag = (formation and formation.lag) or cfg.reaction_lag
    return cfg.wm_roll_max / (1.0 + lag / cfg.catchup_time)
end

-- Turn rate at which the outside man runs out of spare speed: dv = omega * d.
function FLT.turnRateLimit(cfg, right)
    if right < 1.0 then return math.huge end
    return math.deg(cfg.wm_spare_speed / right)
end

-- Roll acceleration at which the outside man cannot ACQUIRE the speed: a = d * omega_dot.
function FLT.turnAccelLimit(cfg, right)
    if right < 1.0 then return math.huge end
    return math.deg(cfg.wm_accel_max / right)
end

-- ---------------------------------------------------------------------------
-- Per-player session
-- ---------------------------------------------------------------------------

local Session = {}
Session.__index = Session

function Session.new(unitName, groupId)
    local self = setmetatable({}, Session)
    self.unitName = unitName
    self.groupId = groupId
    self.formation = FLT.FORMATIONS[2]  -- route: the spacing most flights actually cruise
    self.lastMsg = {}
    self:reset()
    return self
end

function Session:reset()
    self.wingman = nil
    self.prevLead = nil
    self.rollRate = 0
    self.turnRate = 0
    self.turnAccel = 0
    self.gradedTime = 0
    self.goodTime = 0
    self.events = {}
    self.active = {}
    self.worst = { roll = 0, turn = 0, accel = 0, g = 1, err = 0 }
    self.minRange = nil
    self.started = false
end

function Session:count(key)
    self.events[key] = (self.events[key] or 0) + 1
end

-- Coaching calls are rate-limited per kind, not globally -- two different faults in
-- the same turn are two different lessons and both should land.
function Session:say(key, text, secs)
    local now = timer.getTime()
    if self.lastMsg[key] and now - self.lastMsg[key] < FLT.cfg.msg_cooldown then
        return
    end
    self.lastMsg[key] = now
    trigger.action.outTextForGroup(self.groupId, text, secs or 7)
end

-- ---------------------------------------------------------------------------
-- Sampling
-- ---------------------------------------------------------------------------

local function readLead(unit)
    local pos = unit:getPosition()
    local vel = unit:getVelocity()
    if not pos or not vel then return nil end
    local roll = rollOf(pos)
    if not roll then return nil end
    local p = pos.p
    return {
        pos = p,
        vel = vel,
        orient = { x = pos.x, y = pos.y, z = pos.z },
        speed = vlen(vel),
        heading = headingOf(pos),
        pitch = pitchOf(pos),
        roll = roll,
        alt = p.y,
        agl = p.y - land.getHeight({ x = p.x, y = p.z }),
        t = timer.getTime(),
    }
end

-- Exponential smoothing: raw finite differences on a 10 Hz orientation are far too
-- noisy to grade against a 27 deg/s threshold.
local function smooth(old, new, alpha)
    return old + alpha * (new - old)
end

function Session:step(unit, dt)
    local lead = readLead(unit)
    if not lead then return end

    if lead.speed < FLT.cfg.min_speed or lead.agl < FLT.cfg.min_agl then
        self.prevLead = lead
        return
    end

    if not self.started then
        self.started = true
        self.wingman = Wingman.new(FLT.cfg, self.formation, lead)
        self.prevLead = lead
        return
    end

    local prev = self.prevLead
    if not prev then self.prevLead = lead return end

    local prevTurn = self.turnRate
    self.rollRate = smooth(self.rollRate, math.deg(angdiff(lead.roll, prev.roll)) / dt, 0.35)
    self.turnRate = smooth(self.turnRate, math.deg(angdiff(lead.heading, prev.heading)) / dt, 0.35)
    self.turnAccel = smooth(self.turnAccel, (self.turnRate - prevTurn) / dt, 0.25)

    -- Turn G from rate and speed rather than differentiating velocity: same number,
    -- a fraction of the noise.
    local gload = math.sqrt(1 + (math.rad(self.turnRate) * lead.speed / G) ^ 2)

    if not self.wingman then
        self.wingman = Wingman.new(FLT.cfg, self.formation, lead)
    end
    local err = self.wingman:update(lead, prev, dt)
    self.lastErr = err

    self:grade(lead, err, gload, dt)
    self.prevLead = lead
end

-- ---------------------------------------------------------------------------
-- Grading
-- ---------------------------------------------------------------------------

function Session:grade(lead, err, gload, dt)
    local cfg = FLT.cfg
    local f = self.formation
    local spacing = self.wingman:spacing()

    self.gradedTime = self.gradedTime + dt

    local rollLim = FLT.rollRateLimit(cfg, f)
    local turnLim = FLT.turnRateLimit(cfg, f.right)
    local accelLim = FLT.turnAccelLimit(cfg, f.right)

    local absRoll = math.abs(self.rollRate)
    local absTurn = math.abs(self.turnRate)
    local absAccel = math.abs(self.turnAccel)

    if absRoll > self.worst.roll then self.worst.roll = absRoll end
    if absTurn > self.worst.turn then self.worst.turn = absTurn end
    if absAccel > self.worst.accel then self.worst.accel = absAccel end
    if gload > self.worst.g then self.worst.g = gload end
    if err.total > self.worst.err then self.worst.err = err.total end
    if self.minRange == nil or err.range < self.minRange then self.minRange = err.range end

    -- A fault is an EPISODE, not a sample. Counting samples turns one botched turn
    -- into "wide=177" and buries how many separate mistakes were actually made.
    local fired = {}
    local function fault(key, text, ...)
        fired[key] = true
        if not self.active[key] then
            self:count(key)
        end
        if text then self:say(key, string.format(text, ...)) end
    end

    if absRoll > rollLim then
        fault("roll",
            "ROLL-IN TOO FAST  %.0f deg/s  (limit %.0f in %s)\n" ..
            "Smooth it -- your wingman is %.1fs behind you.",
            absRoll, rollLim, f.name, self.wingman.lag)
    end

    if absTurn > turnLim then
        fault("turn",
            "TURN TOO TIGHT FOR %s  %.1f deg/s (limit %.1f)\n" ..
            "Outside man needs +%.0f kt he has not got. Use a tac turn.",
            f.name, absTurn, turnLim, math.rad(absTurn) * f.right * MPS_TO_KT)
    end

    if absAccel > accelLim then
        fault("accel",
            "ROLL-IN TOO ABRUPT FOR %s -- needs %.1fg of throttle from the outside man.\n" ..
            "Ease into the turn.",
            f.name, math.rad(absAccel) * f.right / G)
    end

    if gload > 3.0 then
        fault("g", "%.1fG IN FORMATION -- you are pulling away from the flight.", gload)
    end

    -- One change at a time. Compounding heading, altitude and speed is the fault that
    -- hides behind three individually legal numbers.
    local climbing = math.abs(lead.vel.y) > 7.5
    local turning = absTurn > turnLim * 0.5
    local accelerating = self.prevLead
        and math.abs(lead.speed - self.prevLead.speed) / dt > 1.5
    if climbing and turning and accelerating then
        fault("compound",
            "TURNING, CLIMBING AND ACCELERATING AT ONCE.\n" ..
            "Give the flight one thing to solve at a time.")
    end

    -- What the simulated wingman actually ended up doing.
    local warn = spacing * cfg.err_warn_frac
    local lost = spacing * cfg.err_lost_frac

    -- Mid-air range is absolute OR half the briefed spacing, whichever is tighter:
    -- 60 m is wider than the whole fingertip formation, so the flat value alone
    -- reports a mid-air every time a close wingman closes at all.
    local dangerR = math.min(cfg.danger_range, spacing * 0.5)
    if err.range < dangerR and err.closure > 5 then
        fault("danger",
            "OVERSHOOT -- #2 is inside %.0f ft closing at %.0f kt. This is the mid-air.",
            err.range * M_TO_FT, err.closure * MPS_TO_KT)
    elseif err.total > lost then
        fault("lost", "#2 HAS LOST THE FORMATION -- %.0f ft out of position.",
            err.total * M_TO_FT)
    elseif err.total > warn then
        if err.aft > warn * 0.6 then
            fault("wide", "#2 SUCKED %.0f ft. Unload or ease the turn.", err.aft * M_TO_FT)
        else
            fault("wide", "#2 OUT OF POSITION %.0f ft.", err.total * M_TO_FT)
        end
    end

    self.active = fired
    if next(fired) == nil then
        self.goodTime = self.goodTime + dt
    end
end

-- ---------------------------------------------------------------------------
-- Debrief
-- ---------------------------------------------------------------------------

local function pct(a, b)
    if b <= 0 then return 0 end
    return 100.0 * a / b
end

function Session:debrief()
    local cfg = FLT.cfg
    local f = self.formation
    local lines = {}
    local function add(s) lines[#lines + 1] = s end

    add("=== FORMATION LEAD DEBRIEF ===")
    add(string.format("Formation graded against: %s  (%.0f ft lateral)", f.name, f.right * M_TO_FT))

    if self.gradedTime < 5 then
        add("")
        add("Not enough time in the air to grade. Get airborne, above 200 ft, over 120 kt.")
        return table.concat(lines, "\n")
    end

    local score = pct(self.goodTime, self.gradedTime)
    add(string.format("Time graded: %.0f s", self.gradedTime))
    add(string.format("FOLLOWABLE: %.0f%%   <- time your wingman could hold position", score))
    add("")
    add(string.format("Limits for this spacing:  roll %.0f deg/s | turn %.1f deg/s | roll-in %.2f deg/s2",
        FLT.rollRateLimit(cfg, f), FLT.turnRateLimit(cfg, f.right), FLT.turnAccelLimit(cfg, f.right)))
    add(string.format("Your worst:               roll %.0f deg/s | turn %.1f deg/s | roll-in %.2f deg/s2",
        self.worst.roll, self.worst.turn, self.worst.accel))
    add(string.format("Peak G %.1f | worst #2 error %.0f ft | closest #2 got %.0f ft",
        self.worst.g, self.worst.err * M_TO_FT, (self.minRange or 0) * M_TO_FT))
    add("")

    local faults = {
        { "roll",     "Rolled in faster than #2 could match" },
        { "accel",    "Snapped into turns -- #2 could not acquire the speed" },
        { "turn",     "Turned tighter than the spacing allows" },
        { "g",        "Pulled formation-breaking G" },
        { "compound", "Changed heading, altitude and speed together" },
        { "wide",     "#2 driven out of position" },
        { "lost",     "#2 lost the formation" },
        { "danger",   "#2 overshot into you -- mid-air geometry" },
    }
    local any = false
    for _, row in ipairs(faults) do
        local n = self.events[row[1]]
        if n and n > 0 then
            any = true
            add(string.format("  %-4d  %s", n, row[2]))
        end
    end
    if not any then
        add("  No faults. Every turn you flew was one a human could stay with.")
    end

    add("")
    if score >= 95 then
        add("Verdict: lead-qualified flying. Take a human wingman up.")
    elseif score >= 80 then
        add("Verdict: solid. Tighten the roll-ins and it is there.")
    elseif score >= 60 then
        add("Verdict: your wingman is working too hard. Slow every roll-in by half.")
    else
        add("Verdict: unflyable as briefed. Try Fingertip first, then widen out.")
    end
    return table.concat(lines, "\n")
end

FLT.Session = Session

-- ---------------------------------------------------------------------------
-- Wiring
-- ---------------------------------------------------------------------------

FLT.sessions = {}

local function sessionFor(unit)
    local name = unit:getName()
    local s = FLT.sessions[name]
    if not s then
        local grp = unit:getGroup()
        if not grp then return nil end
        s = Session.new(name, grp:getID())
        FLT.sessions[name] = s
        FLT.buildMenu(s)
    end
    return s
end

function FLT.buildMenu(s)
    local root = missionCommands.addSubMenuForGroup(s.groupId, "Formation Lead Trainer")
    missionCommands.addCommandForGroup(s.groupId, "Debrief", root, function()
        trigger.action.outTextForGroup(s.groupId, s:debrief(), 45)
    end)
    missionCommands.addCommandForGroup(s.groupId, "Reset run", root, function()
        s:reset()
        trigger.action.outTextForGroup(s.groupId, "Formation Lead Trainer: run reset.", 8)
    end)
    local fmenu = missionCommands.addSubMenuForGroup(s.groupId, "Set formation", root)
    for _, f in ipairs(FLT.FORMATIONS) do
        missionCommands.addCommandForGroup(s.groupId, f.name, fmenu, function()
            s.formation = f
            s:reset()
            trigger.action.outTextForGroup(s.groupId, string.format(
                "Grading against %s.\nRoll limit %.0f deg/s | turn limit %.1f deg/s",
                f.name, FLT.rollRateLimit(FLT.cfg, f), FLT.turnRateLimit(FLT.cfg, f.right)), 12)
        end)
    end
end

local function tick()
    local dt = 1.0 / FLT.cfg.sample_hz
    for _, coa in pairs({ coalition.side.BLUE, coalition.side.RED }) do
        local groups = coalition.getGroups(coa, Group.Category.AIRPLANE) or {}
        local helos = coalition.getGroups(coa, Group.Category.HELICOPTER) or {}
        for _, list in pairs({ groups, helos }) do
            for _, grp in pairs(list) do
                for _, unit in pairs(grp:getUnits() or {}) do
                    if unit:isExist() and unit:getPlayerName() then
                        local s = sessionFor(unit)
                        if s then s:step(unit, dt) end
                    end
                end
            end
        end
    end
end

local function loop()
    local ok, err = pcall(tick)
    if not ok then
        env.error("FormationLeadTrainer: " .. tostring(err), false)
    end
    return timer.getTime() + (1.0 / FLT.cfg.sample_hz)
end

timer.scheduleFunction(function(_, t)
    local ok, nxt = pcall(loop)
    if not ok then return t + 1.0 end
    return nxt
end, nil, timer.getTime() + 2)

env.info("FormationLeadTrainer " .. FLT.VERSION .. " loaded")
