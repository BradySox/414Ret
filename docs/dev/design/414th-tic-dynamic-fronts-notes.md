# 414th TIC Dynamic Fronts Notes

Design intent for making the TIC (Troops In Contact) frontline battle look and feel
dynamic instead of "two walls of troops shooting at each other." Read this before
touching `_plan_tic_action()` or the TIC stance mapping in
`game/missiongenerator/flotgenerator.py`. Pairs with CLAUDE.md §9 (the TIC integration
contract) — that section is the hard contract; this note is the *why* behind the
movement design.

## The problem

TIC replaces vanilla frontline ground AI with formation-keeping scripted firefights.
The 414th drives TIC entirely through waypoint NAMES (`t+N hdg=H roe=simulate`) — no DCS
tasks/triggers — and uses the "simulate" ROE, which fires theatrical near-miss salvos
**only while stationary**. Moving formations are silent.

Two things made the result read as two static walls:

1. **Symmetric posture.** The original `_plan_tic_action()` collapsed every stance into
   one of three behaviors:
   - `AGGRESSIVE` / `BREAKTHROUGH` / `ELIMINATION` → one **identical** 3-leg advance
     (standoff → lateral slide → press past trace).
   - `DEFENSIVE` / `AMBUSH` → `return False`, i.e. idle at the rear spawn.
   - `RETREAT` → fall back.

   So two aggressive sides ran the same script and collided in a symmetric line, and a
   defending side did literally nothing while the attacker walked up.

2. **Lockstep timing.** Legs were gated on `boundPause` with only a 0–3 min step-off
   (`TIC_STEP_OFF`) and ±25% per-leg jitter (`_tic_jitter()`). That's tight enough that
   the whole line stepped off and halted together — synchronized movement reads as a
   wall, and because moving = silent / stationary = fire, the whole line also went quiet
   and opened up in unison.

Latent geometry bug in the idle-defender case: a `DEFENSIVE`/`AMBUSH` group parked at
its rear spawn can sit **outside** TIC's ~2 NM targeting bubble, so when the attacker
presses to its fighting line it can arrive at an empty trace and find no one to fight.

## Key constraint we design around

`simulate` ROE: **stationary = fires, moving = silent.** This is a built-in rhythm, not
an obstacle. If we desynchronize *who is moving vs. dug-in* at any given moment, the line
stops reading as a wall almost for free — some groups advancing quietly while others are
halted and firing.

## Design A — Desynchronize the cadence

Break the lockstep. All in `flotgenerator.py`, no new plugin options (`boundPause` stays
the single player-facing tempo knob; new values are module-level `TIC_*` constants).

- **Widen step-off.** Scale `TIC_STEP_OFF` to the battle tempo (e.g. `(0, boundPause // 2)`)
  so groups begin advancing across a multi-minute window rather than nearly together.
- **Loosen leg jitter.** Widen `_tic_jitter()` from ±25% toward ±40–50% so leg
  transitions don't re-cluster after step-off.
- **Per-group tempo.** Seed a per-group tempo/speed variation (fast vs. slow movers) so
  formations don't all reach the firing line on the same beat.

Net: at any instant some groups are advancing (silent), some dug in and firing, some
sliding. The contact line ripples instead of lurching.

## Design B — Differentiate posture

The campaign **already** carries independent per-side stances —
`player_cp.stances[enemy_cp.id]` and the reverse are passed separately into
`FlotGenerator` (`missiongenerator.py`). The asymmetry exists in the data model; the old
TIC mapping discarded it. Stop collapsing the stances; give each a distinct movement
profile:

- **AGGRESSIVE** — measured advance: standoff + slide + *light* push. The attack meeting
  resistance.
- **BREAKTHROUGH** — spearhead: deeper push, less lateral dithering, faster cadence. A
  thrust, not a broad shove.
- **ELIMINATION** — close-in hunter: extra slide/press cycle to chew through LOS
  deadlocks.
- **DEFENSIVE** — *no longer idle.* One short forward bound to a fighting line just
  behind the trace (this also fixes the out-of-bubble geometry bug), then hold, with a
  **low per-group probability of an occasional local counterattack leg**. A dug-in line
  that sometimes lunges.
- **AMBUSH** — hold close to spawn but still inside engagement range; weapons-tight feel,
  shortest forward bound. Distinct from DEFENSIVE by being more passive/rearward.
- **RETREAT** — unchanged.

Combined with A, one front reads as *an attack pressing a defense* with both sides'
groups desynchronized — not two synchronized walls.

## Why C (terrain anchoring) is out

Seating defenders on ridgelines/town edges and routing attackers through covered
approaches would be the biggest visual win, but it requires terrain queries (cover,
elevation, LOS pathing) that Retribution does not expose to this generation path. TIC
targeting is LOS-checked and TIC does **not** path around terrain (the Dzhukhur lesson),
so we cannot fake it either. C is shelved; A + B are pure waypoint-generation changes
with no terrain dependency.

## Constraints (carry-over from CLAUDE.md §9 — do not break)

- All orders stay as `t+N hdg=H roe=simulate` waypoint names. No DCS tasks/triggers on
  TIC-managed groups.
- Keep the LOS-breaking **lateral slide** leg in every advancing branch — it's hard-won
  (the Dzhukhur lesson: TIC targeting is LOS-checked and TIC doesn't path around terrain).
- `simulate` ROE and the stationary-only fire behavior are intentional. Don't switch to
  `roe=kill` (judged too lethal/accurate by the 414th).
- The campaign front moves on **player** kills, not TIC kills. Scripted near-miss
  attrition stays sparse by design; this rework is about *look and feel*, not lethality.
- Audience is the **human flying over the front** (StormTrooper-on cloaks these groups
  from DCS AI sensors). "Dynamic" here = visually legible from the cockpit, not tactically
  reactive to AI.

## Implementation areas

- `game/missiongenerator/flotgenerator.py` — `_plan_tic_action()`, `_tic_jitter()`, the
  `TIC_*` constants, and stance branching.
- Tests: `tests/` TIC suite — assert DEFENSIVE now emits a forward bound, the aggressive
  stances diverge, and the occasional counterattack fires probabilistically.
- Keep CLAUDE.md §9's ROE/waypoint-design paragraph in sync with whatever lands.
