# MOOSE `Ops.*` Opportunity Map (on top of the MIST → MOOSE consolidation)

**Status:** investigation / opportunity map (no code change)
**Date:** 2026-06-24
**Parent:** [`414th-framework-consolidation-notes.md`](414th-framework-consolidation-notes.md)
**Related:** CLAUDE.md §17 (auto-planner unpredictability), [`turnless.md`](turnless.md),
[`414th-mantis-migration-notes.md`](414th-mantis-migration-notes.md).

## One correction up front

Standardizing on MOOSE / removing MIST does **not** "unlock" the Ops section — **the entire Ops
stack is already bundled in `resources/plugins/base/Moose.lua` and usable today.** Ops is MOOSE; it
has no dependency on MIST being present or absent. What the consolidation actually buys is
**fluency and consistency**: once everything runtime is MOOSE, the natural reflex becomes "reach for
an Ops module" instead of "vendor a MIST-era standalone script." So the *direction* is right — lean
into Ops — but the mechanism is cultural/architectural, not a literal gate.

## What we already have (ground truth from bundled `Moose.lua`)

Every major Ops class is present (method counts as a rough size gauge):

| Strategic / force | Tactical / mission | Service / runtime |
|---|---|---|
| `CHIEF` (91), `COMMANDER` (51) | `OPSGROUP` (376), `AUFTRAG` (227) | `CSAR` (63), `RESCUEHELO` (43) |
| `LEGION` (61), `AIRWING` (58) | `FLIGHTGROUP` (141), `ARMYGROUP` (50), `NAVYGROUP` (58) | `AWACS` (121), `ATIS` (61) |
| `BRIGADE` (15), `FLEET` (13) | `TARGET` (53), `OPSZONE` (57) | `CTLD` (130), `MANTIS` (57) |
| `SQUADRON` (15), `COHORT` (52) | `INTEL` (75), `PLAYERTASK` (52) | `OPSTRANSPORT` (85) |

## The fault line: "Python plans, Lua executes"

Retribution's core architecture (CLAUDE.md "Planner / Lua split") is: **Python owns campaign state,
economy, force composition, mission planning (the HTN commander), and persistence between turns;
Lua executes runtime behavior inside the single generated `.miz`.** The Ops family lands on **both
sides** of that line, and that — not MIST — is what decides whether a given Ops module is an
"add-on" or an "architecture change."

## Tiered map

### Tier A — Service / runtime modules → **adopt opportunistically** (this IS the consolidation's natural extension)

These execute runtime behavior inside a mission — exactly the Lua side of the split. They
**complement** Retribution and carry zero conflict with the Python brain. Several are already in
flight:

- `MANTIS` — IADS engine (in progress, [`414th-mantis-migration-notes.md`](414th-mantis-migration-notes.md)).
- `CTLD` — logistics (scoped, [`414th-ctld-mantis-style-port-scope.md`](414th-ctld-mantis-style-port-scope.md)).
- `ATIS` — already shipping as the `MooseAtis` plugin.
- `INTEL` — already underpins the `bigeye` EWR (the EWRS successor).
- **New candidates worth piloting:**
  - `CSAR` / `RESCUEHELO` — natural fit for the **SCAR downed-team CSAR recovery loop** (CLAUDE.md
    §15), which today leans on the SCAR plugin's own `mist.dynAdd` spawning. Porting SCAR off MIST
    (consolidation phase 3) + adopting `Ops.CSAR` could land together.
  - `PLAYERTASK` — structured player tasking + F10 menus; could modernize how player flight tasks /
    SCAR / recon objectives surface in-mission.
  - `AWACS` — full GCI/AWACS controller, if we ever want richer player AWACS than current.

**These are the "add on to what we're doing" wins.** They ride directly on MOOSE-first and each is
an independent, opt-in, in-game-validated plugin — same shape as the MANTIS/CTLD work.

### Tier B — Tactical group / mission layer → **selective, scoped use only**

`OPSGROUP`/`FLIGHTGROUP`/`ARMYGROUP`, `AUFTRAG` (missions), `TARGET`, `OPSZONE`. These can enrich the
*runtime behavior* of specific groups (richer tasking, dynamic re-routing, mission state machines).
**Safe only when scoped to executing a task Python already decided** — i.e. Lua makes a
Python-planned flight behave more intelligently in-mission. The moment `AUFTRAG`/`OPSGROUP` start
*choosing* what to do, they cross into Tier C. Useful per-feature; never a blanket adoption.

### Tier C — Strategic commander layer → **NOT an add-on; a different engine**

`CHIEF`, `COMMANDER`, `LEGION`/`BRIGADE`/`AIRWING`/`FLEET`, `SQUADRON`/`COHORT`. This is a **runtime
AI theater commander**: it dynamically assigns missions, manages force providers, and captures/
defends zones *during* a running mission, with its own persistence. That **directly competes with
Retribution's Python brain** — campaign state, economy, procurement, the HTN planner, and save
format all live in Python. You cannot have two commanders owning force tasking.

This is not a new realization for the fork:
- **CLAUDE.md §17** explicitly frames the in-Python `ownfor_/opfor_planner_unpredictability` feature
  as *"the low-risk in-Python alternative to a runtime MOOSE `Ops.Chief` red rewrite."* The Ops.Chief
  route was considered and **deliberately declined.**
- **`turnless.md`** — even the real-time / BMS-style vision keeps the **AI Commander in Python**
  (HTN replanning, mission abort), not a MOOSE Chief.

So `Ops.Chief` is interesting precisely where the user pointed — but it belongs to a **ground-up
architectural alternative**, not an increment on the current design. Two honest homes for it:
1. A **bounded experiment** for a future turnless/real-time mode (where a runtime commander is
   actually wanted) — but `turnless.md`'s current plan reuses the Python HTN, so adopting Chief there
   would be a deliberate re-architecture, not a shortcut.
2. **Red-only autonomy** experiments — but §17 already chose the cheaper Python path for exactly this.

**Recommendation: keep Tier C out of the consolidation scope.** Flag it as a strategic-fork option,
not an add-on. Revisit only if/when turnless becomes a funded direction and the team explicitly
wants to trade Python campaign ownership for a MOOSE runtime engine.

## How this maps onto the consolidation roadmap

Add a parallel **"Tier A service-module adoption"** track to
[`414th-framework-consolidation-notes.md`](414th-framework-consolidation-notes.md) — it shares the
same config-bridge pattern (Python generates the data table; a MOOSE Ops module consumes it) and the
same per-feature in-game-pass discipline. Concretely:

- **Already on the roadmap:** MANTIS (phase 1), CTLD (phase 4), and `bigeye`/INTEL + ATIS (done).
- **Fold in as opportunistic Tier-A items:** `Ops.CSAR`/`RESCUEHELO` alongside the SCAR MIST port
  (phase 3); `Ops.PlayerTask` as a player-tasking modernization candidate.
- **Explicitly parked:** Tier C (`Chief`/`Commander`/`Legion`…) — pointer to §17 + `turnless.md`.

## Verdict

Worth investigating — and the answer is a clear split: **the service tier (Tier A) is a genuine,
low-risk extension of exactly what we're already doing** and should be folded into the consolidation
as opportunistic adoptions; **the strategic tier (Tier C, incl. `Ops.Chief`) is a fundamentally
different campaign engine** that the fork has already, twice, chosen to keep in Python. Lean hard
into Tier A; treat Tier C as a separate strategic decision, not an add-on.
