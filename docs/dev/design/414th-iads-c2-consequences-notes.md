# 414th — IADS C2 family: felt consequences for command-center & power nodes (design notes)

**Status: Feature A LANDED 2026-07-06 (§52); Feature B deferred.** Follow-on to §51 (enemy comms
jamming). Feature A phase A1 (command-center → planner unpredictability + SITREP legibility) shipped
as feature §52 — the shape below is what landed; the A2 package-count throttle and all of Feature B
remain as scoped here. §51 gave the IADS
**comms** node a player-felt consequence; this note scopes the same treatment for its two
data-model siblings — **command centers** and **power sources** — which today have gameplay only
inside MANTIS's runtime SAM-autonomy graph and nothing the player can *see* or feel.

The design bar is the one §51 met: an object the model already tracks → a legible consequence
chain → counterable by an ordinary strike → **no phantom spawns, no force-model rewrite** (the
consequence rides the existing turn model or the existing MANTIS AI axis, never a bespoke one).

---

## The DCS-feasibility frame (why these two, and not datalink/GPS)

The abandoned sibling idea — *red EW degrading the player's datalink / GPS / radar picture* — was
found **not feasible** (2026-07-06): DCS mission scripting exposes levers over **AI units** and
exactly **one** lever into the human cockpit's own systems — audio radio
(`trigger.action.radioTransmission`, which is *why* §51 was buildable). There is no scripting API
to deny a player's GPS, fog their datalink, or degrade their radar on command; the fork's entire
"EW" is scripted effects on AI units (the C-130J EW holds a **red SAM's ROE**; §7 "hide from MFD"
is a **static generation flag**, `hide_on_mfd`). Do not re-propose datalink/GPS jamming — it needs
a cockpit lever DCS doesn't provide.

Both features below are feasible precisely because they act on the levers we *do* have:

- **Command-center → planning** acts on the **Python turn model** (the auto-planner). Zero DCS
  integration risk.
- **Power → radar blackout** acts on **red SAM/EWR AI** (emissions off) — and largely *already
  happens* via MANTIS; the work is legibility + breadth, on an axis MANTIS owns.

---

## Feature A — Command-center → degraded enemy planning (the strong, genuinely-new half)

### The gap

Killing a red command center has a **runtime** consequence (MANTIS: when every CC is dead, its
SAMs go autonomous — `mantis-config.lua` `setup_c2`), but **no campaign-layer consequence**: red's
*planning* is untouched. Red's offensive tempo is governed by aircraft/target availability and the
static `opfor_planner_unpredictability` setting (§17, `game/commander/tasks/targetorder.py`
`shuffled_by_priority`) — a fixed 0-100 knob coupled to nothing on the map. So "bomb the enemy HQ"
is a strike checkbox, not a strategic move. Note §40 campaign-phase emphasis is **BLUE-only**, so
red planning is genuinely unoccupied territory.

### The design

Couple red's planning quality to its **C2 health** — the fraction of red `commandcenter` TGOs
still alive, measured at plan time exactly as §51's `_enemy_jammer_nodes` measures comms nodes
(iterate red CPs' `ground_objects`, `category == "commandcenter"`, alive units). As CCs fall:

1. **Sloppier targeting** — scale the *effective* `opfor_planner_unpredictability` up (a decapitated
   HQ services worse targets, hits the same things less reliably). Cleanest seam:
   `_unpredictability_for(state)` reads a C2-health modifier instead of the raw setting. Reuses the
   §17 machinery wholesale; at full C2 health the value is unchanged (byte-identical to today).
2. **(Optional, phase 2) Thinner tempo** — cap red's *offensive* package count when C2 is
   decapitated (a throttle in the HTN root, mirroring how §40 reorders the offensive middle — but
   trimming, not reordering). Reactive threat response stays deterministic and uncapped (**the §17
   boundary is inviolable** — a decapitated enemy still defends itself; it just plans worse
   offense).

### Legibility (the §51/§40 "explain itself" rule)

The effect is on the *enemy's* next turn, so the player needs to be told the strike worked: a
SITREP line ("Enemy command-and-control degraded — HQ 2/3") and/or a one-time cue when a CC falls.
Without this the coupling is invisible and reads as RNG.

### Guardrails

- **Never zero red out.** A floor on the throttle (red always plans *some* offense) — the goal is
  pressure, not a walkover.
- **Blue-strikes-red only** in practice (the `ownfor_` side stays the player's own setting); the
  coupling is symmetric in code but only red has a HTN auto-planner the player degrades.
- **Reactive defense deterministic** (§17). Only the opportunistic/offensive tiers are touched.
- Turn-model only — **no DCS risk, no `.miz` change, no Lua.**

---

## Feature B — Power → rolling radar blackout (mostly LEGIBILITY, not a new system)

### What already exists (be honest)

MANTIS **already** degrades SAMs on C2 loss (`mantis-config.lua` `setup_c2`):

- **power lost → SAM offline** (`SetAIOff`) — the dependent radars literally go dark;
- **comms lost → SAM autonomous** (`OptionAlarmStateRed`, or `SetAIOff` under a dark policy).

So "strike the power node → its dependent SAM radars go down" is **already the behavior** — it's
observable on the player's RWR (emitters drop off). The genuine gaps are three, and all smaller
than "build a blackout system":

1. **Invisibility.** Nothing links the strike to the effect — no cue says "grid down, N radars
   offline," so a player may never connect the two. (Same failure §51's first-burst cue fixed.)
2. **Permanence, not "rolling."** A dead node stays dead, so the blackout is permanent (correct,
   but not the temporary "rolling" window the name implied). A *temporary* window would need a
   repairable/again-powered node — a bigger model change; **defer**, keep it permanent v1.
3. **Breadth.** Only graph-dependent SAMs are covered. **EWR** sites and **airfield search radars**
   aren't necessarily on a power dependency, and **night airfield lighting** isn't modeled at all —
   both natural extensions of "the grid is down."

### The design (v1 = make it felt + widen it)

- **Cue it.** When a power (or comms) node dies, emit a "hostile air-defense grid degraded — <N>
  emitters offline near <area>" cue + a SITREP line. This is the whole felt payoff and it's cheap.
- **Widen it.** Author/extend power dependencies so **EWR** emissions and **airfield radars** drop
  with the grid (data/YAML, not code), and optionally cut **night airfield lighting** at the struck
  field (a generation/runtime lighting toggle — verify DCS exposes it before committing).

### The MANTIS-ownership boundary (the c130j lesson, verbatim)

Power/emissions live on the **`ALARM_STATE` / `EmOnOff` / `SetAIOff` axis, which MANTIS owns**
(`c130j_mission_systems.lua:646` — the EW plugin touches ONLY ROE and never writes ALARM_STATE for
exactly this reason). **Feature B must compose with MANTIS, not fight it**: it may *cue* the effect
MANTIS produces and *extend the dependency graph* MANTIS reads, but it must never write ALARM_STATE
itself — that would race the engine. This is the single biggest implementation constraint and the
reason B is "cue + data," not a new runtime controller.

---

## Recommendation & sequencing

1. **Feature A first** (command-center → planning). It is the genuinely-new, higher-value half,
   pure turn-model, zero DCS risk, and reuses the §17 unpredictability seam. Ship phase 1 (the
   unpredictability coupling + legibility) before the optional package-count throttle.
2. **Feature B second** (power/comms cue + breadth). Smaller — it makes an *existing* MANTIS
   consequence felt and wider — but must respect the MANTIS ALARM_STATE boundary, so it's cue +
   data, and the "rolling/temporary" and night-lighting pieces are each gated on a DCS-capability
   check before building.

Both are opt-in settings, default consistent with the fork's stance (A: a new
`c2_decapitation_effects`-style toggle; B: rides on / near the MANTIS + §51 wiring). Preseed on the
IADS-heavy campaigns (Red Tide) once flown.

## Explicitly out of scope / not feasible

- **Datalink / GPS / radar denial to the player** — no DCS scripting lever (see the feasibility
  frame). Recorded here so it isn't re-proposed.
- **Temporary/repairable power ("rolling" in the literal sense)** — needs a node-repair model;
  deferred, v1 blackout is permanent-on-kill.
- **Red reactive-defense degradation** — the §17 boundary; a decapitated enemy still defends.

## Delivery sketch

| Phase | Scope | Risk |
|---|---|---|
| A1 | red CC health → effective `opfor_planner_unpredictability` + SITREP/cue legibility | low (Python, reuses §17) |
| A2 | optional red offensive package-count throttle (floored) | low-med (HTN root) |
| B1 | power/comms node-death cue + SITREP line (compose with MANTIS, no ALARM_STATE writes) | low |
| B2 | widen the dependency graph to EWR/airfield radars (data/YAML) | low, data-only |
| B3 | night airfield lighting cut on the struck field | gated on a DCS-capability check |

Tests: A on the planner/unpredictability path (health→modifier, floor, deterministic-reactive
guard); B on the emitter/cue + the MANTIS-compose invariant (never writes ALARM_STATE). In-game
pass rows for the felt effects (A: red plays visibly worse after an HQ kill; B: RWR clears + the
cue fires when the grid drops). No debrief-schema changes anywhere.
