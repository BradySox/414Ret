# Formation Lead Trainer — design notes

**Status: BUILT 2026-08-31 as §96. Never flown — checklist row B110 is owed.**

Feature: `resources/plugins/formationlead/` · tests: `tests/lua/test_formation_lead_trainer.py`
· mission builder: `tools/build_formation_lead_mission.py`

---

## 1. The problem

Stated by the DM: *"When you fly with the AI, they stay glued in place. Flying with a
human, dramatic turns cause wrecks."*

Both halves are one problem. The DCS AI wingman holds position with no energy model, so
a lead can fly anything and get no signal. A human wingman is solving a real geometry and
energy problem, and a lead who has only ever flown with the AI has never been told which
of his turns are unflyable. He finds out when somebody overshoots into him.

Nothing existing solves this. Range scripts score bombs and strafe; written doctrine
(FlyAndWire's flight-lead guide, the FFI formation standards) states the rules but
measures nothing. There is no tool that grades whether *your* leading is followable.

## 2. The model

The whole thing reduces to two equations. A wingman at lateral offset `d` on the outside
of a turn at rate `ω` must:

- fly faster by **`Δv = ω · d`**, and
- acquire that speed at **`a = d · ω̇`**.

Both scale **linearly with spacing**. That single fact is the lesson the tool exists to
teach, and every limit in the script is derived from it rather than hand-set per
formation:

| Formation | Lateral | Turn limit | Roll-in limit | Roll-rate limit |
|---|---|---|---|---|
| Fingertip | 59 ft | 95.5 °/s | 7.96 °/s² | 33.3 °/s |
| Route | 492 ft | 11.5 °/s | 0.96 °/s² | 30.0 °/s |
| Cruise (0.5 nm) | 2953 ft | 1.91 °/s | 0.16 °/s² | 25.0 °/s |
| Combat spread (1.5 nm) | 9121 ft | 0.62 °/s | 0.05 °/s² | 20.0 °/s |

The combat-spread row is the point. At 1.5 nm no bank angle is followable, which is
**why tactical turns exist** — the tool derives that rather than asserting it.

The roll-rate limit comes from the wingman losing `lag` seconds of bank and having
`catchup_time` to erase it while still matching the ongoing rate:
`limit = roll_max / (1 + lag / catchup)`.

## 3. The virtual wingman

A point mass, integrated at 10 Hz, chasing the slot with a delayed, saturated PID:

- **Perception is instant; the command is delayed.** Light is instant — a wingman sees
  where the lead is and is late *reacting*. Delaying perceived position instead makes the
  model trail by `v·τ` and hides the real failure mode.
- **Saturation is what makes it human.** Longitudinal command is clamped by thrust and
  drag (+2.5 / −3.5 m/s²), perpendicular by available G (4 g). This is the entire reason
  it is not the DCS AI.
- **Lag and gain scale with spacing.** A fingertip wingman is locked on a wingtip 60 ft
  away and tracks continuously (0.30 s, high gain); at 1.5 nm he is cross-checking every
  few seconds (1.50 s, low gain). Constant gains cannot fit both.
- **The integral term is load-bearing.** Without it a sustained turn leaves a permanent
  offset and every steady turn grades as a fault — the opposite of the lesson. Transients
  are the lead's doing; steady state is the wingman's to trim out.

## 4. Three bugs found by running the model, not by reading it

All three were invisible to the syntax gate and to inspection, and each is pinned by a
test now.

1. **The `v·dt` measurement bias.** The error was computed from `self.pos` *after*
   integrating a step, against the slot *before* it — a constant 15.4 m at 300 kt,
   independent of gain, reading as a permanent acute error. Found because a gain sweep
   moved the steady error not at all: 15.66 → 15.48 m across a 7× gain range. A control
   bug responds to gain; a bookkeeping bug does not. **That is the diagnostic.**
2. **Priming returned early**, skipping the integration step, so the next sample saw a
   `v·dt` gap and reported it as a peak. Snap and fall through.
3. **The mid-air threshold was absolute** at 60 m — wider than the entire fingertip
   formation (21.7 m nominal), so it reported a mid-air every time a close wingman closed
   at all. It is now `min(60 m, half the briefed spacing)`.

## 5. Validation

`tests/lua/test_formation_lead_trainer.py` flies synthetic profiles through the real
plugin code on Lua 5.1. The discrimination it pins:

| Formation | Profile | Score | Faults |
|---|---|---|---|
| Fingertip | 30° @ 8 °/s | 100 % | none |
| Fingertip | 60° @ 75 °/s | 90 % | roll, wide |
| Route | 25° @ 6 °/s | 100 % | none |
| Route | 60° @ 75 °/s | 87 % | roll, accel, wide |
| Cruise | 8° @ 1.5 °/s | 100 % | none |
| Cruise | 30° @ 8 °/s | 3 % | turn, accel |
| Spread | 6° @ 0.8 °/s | 100 % | none |
| Spread | 15° @ 5 °/s | 3 % | turn, accel |

Every doctrinally correct profile is clean; every bad one is caught. **This is a model
test, not a flight test** — it says the maths is self-consistent, not that 27 °/s is the
right number for a Hornet. Only B110 can say that.

## 6. Constraints

- **Read-only.** Spawns nothing, commands nothing, owns no kills. Rule 1 of the
  plugin discipline is satisfied trivially, which is why there is no Python emitter.
- **Vanilla scripting engine only** — no MOOSE, no MIST, no mod units. It has to run in
  any mission, including third-party campaigns and MP servers.
- **Roll is horizon-referenced** via `forward × world-up`, which degenerates pointing
  straight up or down. Guarded here; **MOOSE's `POSITIONABLE:GetRoll()` is not** and
  returns nan going vertical. Do not "simplify" this back to MOOSE's copy.
- **Faults are episodes, not samples.** Per-sample counting reported `wide=177` for a
  single roll-in and made the debrief unreadable.
- **Default off.** It is a training aid, not campaign behaviour.

## 7. Deferred

- **The numbers are unflown.** `wm_roll_max`, `wm_accel_max`, `wm_decel_max`,
  `wm_spare_speed` and the per-formation lag/gains are reasoned defaults, not measured
  ones. The honest way to calibrate them is to fly a real two-ship, record both jets, and
  fit the wingman model to what the human actually did. Until that happens the *relative*
  grading is trustworthy and the *absolute* thresholds are an opinion.
- **Airframe-specific envelopes.** A Hornet and a Viggen have different throttle margins.
  One table for all types is a simplification.
- **Trail and echelon** are not modelled — only line-abreast-with-sweep offsets.
- **Tac turns are not detected.** The tool says a spread formation cannot be banked
  around; it cannot yet recognise that you flew a correct cross turn instead. That is the
  obvious next build and would need heading-change-vs-time pattern matching.
