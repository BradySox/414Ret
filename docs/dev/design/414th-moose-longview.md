# MOOSE capability inventory + long view (post-MIST)

**Status:** strategy / inventory (no code change) · **Date:** 2026-06-25
**Parent:** [`414th-moose-ops-opportunity-map.md`](414th-moose-ops-opportunity-map.md) (the Tier A/B/C
decision frame) · **Context:** MIST is retired; MOOSE is the sole runtime framework.

> The opportunity map answers *"should we lean into Ops?"* (yes, Tier A). This doc is the **deep
> inventory** behind that — the full bundled surface, what we already run, the untapped high-value
> set, and a near/mid/long-term horizon — so feature decisions can pick from a known menu instead of
> rediscovering it each time.

## The organizing lens (don't skip this)

Every adoption call reduces to one question from CLAUDE.md's **Planner/Lua split**: *does this module
**execute** a decision Python already made, or does it **make** the decision?*
- **Executes** → safe runtime service (Tier A). MOOSE makes a Python-planned thing behave better
  in-mission. This is the whole consolidation thesis.
- **Decides** (force tasking, procurement, what-to-attack, campaign state) → competes with the Python
  brain (Tier C). Different engine, not an add-on. Parked twice already (CLAUDE.md §17, `turnless.md`).

Performance/hygiene modules are a third, orthogonal bucket: they touch neither brain — pure FPS/UX.

## 1. The full surface — 252 classes, by family

| Family | Representative classes | Role |
|---|---|---|
| **Core/Wrapper** | `GROUP` `UNIT` `STATIC` `AIRBASE` `COORDINATE` `ZONE_*` `SET_*` `SPAWN` `SCHEDULER` `MESSAGE` `MENU_*` `FSM` `EVENT` `DATABASE` | the substrate — used everywhere |
| **Ops — tactical** | `OPSGROUP` `FLIGHTGROUP` `ARMYGROUP` `NAVYGROUP` `AUFTRAG` `TARGET` `OPSZONE` `OPSTRANSPORT` `OPERATION` | mission/group state machines |
| **Ops — strategic** | `CHIEF` `COMMANDER` `LEGION` `AIRWING` `BRIGADE` `FLEET` `SQUADRON` `COHORT` `PLATOON` `FLOTILLA` | runtime theater commander |
| **AI dispatchers** | `AI_A2A_DISPATCHER` `AI_A2G_DISPATCHER` `EASYGCICAP` `AI_CARGO_DISPATCHER*` `AI_ESCORT*` `AI_BALANCER` | auto force generation |
| **Detection / ISR** | `DETECTION_AREAS/UNITS/TYPES/ZONES` `DETECTION_MANAGER` `INTEL` `INTEL_DLINK` `TIRESIAS` | sensor fusion + reporting |
| **Player tasking** | `PLAYERTASK` `PLAYERTASKCONTROLLER` `PLAYERRECCE` `DESIGNATE` `TASK_*` (A2A/A2G/CARGO/CSAR/CAPTURE) `SCORING` | structured player missions + F10 |
| **Cargo / logistics** | `CTLD` `CTLD_CARGO` `CTLD_HERCULES` `DYNAMICCARGO` `CARGO_*` `WAREHOUSE` `STORAGE` `AMMOTRUCK` | troop/crate/supply |
| **CSAR / rescue** | `CSAR` `RESCUEHELO` `AICSAR` | downed-pilot recovery |
| **Ground combat** | `SUPPRESSION` `ARTY` `SHORAD` `SEAD` `MOVEMENT` | frontline behavior |
| **Air defense** | `MANTIS` `SHORAD` | IADS (MANTIS is ours now) |
| **Naval / carrier** | `AIRBOSS` `RECOVERYTANKER` `NAVYGROUP` `FLEET` `FLOTILLA` | carrier ops |
| **Comms / sound** | `MSRS` `MSRSQUEUE` `ATIS` `RADIO*` `SRS*` `RANGE` | speech/ATIS/range |
| **Hygiene / perf** | `TIRESIAS` `CLEANUP_AIRBASE` `PROFILER` | FPS + runway upkeep |
| **Strategic toys** | `STRATEGO` (node-graph conquest), `RANGE` `FOX` `MISSILETRAINER` | not campaign-relevant / Tier-C-ish |

## 2. What we already run (the baseline — we are MOOSE-heavy)

Retribution is **already deep into MOOSE**, not starting fresh:

| Adopted | Where | Notes |
|---|---|---|
| `MANTIS` | `mantisiads` | our default IADS engine |
| `CTLD` / `CTLD_CARGO` | `ctld` | logistics/sling-load |
| `AI_A2A_DISPATCHER` | `intercept` | QRA/GCI (upstream PR #782) |
| `INTEL` / `INTEL_DLINK` | `bigeye`, MANTIS | EWR + IADS detection |
| `AUFTRAG` (171 refs) + `FLIGHTGROUP` | `tars`, others | TARS recon runtime, mission tasking |
| `AIRBOSS` | `airboss` | carrier ops |
| `AUTOLASE` | `MooseAutolase` | front-line JTAC lasing |
| `RAT` | `civilian_traffic` | civilian air traffic |
| `MARKEROPS` | `MooseMarkerOps` | F10 marker commands |
| `MSRS`/`MSRSQUEUE` | several | SRS speech |

**Implication:** the muscle memory already exists. New Tier-A adoptions are incremental, not novel.

## 3. The untapped high-value set (the real menu)

Organized by the 414th's feature pillars, with the planner/Lua verdict for each.

### Player experience & tasking — *the biggest opportunity*
The 414th is unusually **player-flown-feature heavy** (SCAR, TARPS recon, C-130 EW/ISR, JAMMING),
yet each surfaces its own ad-hoc F10 menu / briefing. MOOSE has a unified layer:
- **`PLAYERTASK` / `PLAYERTASKCONTROLLER`** — structured player missions with auto F10 menus,
  mark-to-task creation, status tracking, multi-client. Could become the **common spine** under SCAR,
  TARS recon objectives, strike tasking. *Executes* (surfaces Python-planned targets) → **Tier A**.
- **`PLAYERRECCE`** — player recon/JTAC role: detect + lase + report ground targets. Direct fit for
  **TARPS recon** and a player-JTAC option. **Tier A.**
- **`DESIGNATE`** — target-designation/lasing menu. Complements AUTOLASE for *player-driven* lasing.
- **`SCORING`** — per-player stats/score; cheap engagement/immersion layer. **Tier A.**
- **`AWACS`** — full GCI/AWACS controller with player picture calls; richer than current support AWACS.

### Frontline / ground combat — *enrich TIC*
TIC (scripted frontline firefights, §9) is bespoke. MOOSE could deepen it:
- **`SUPPRESSION`** — infantry take cover / cease fire under incoming → far more believable firefights
  than constant-fire. *Executes* on Python-placed FLOT units → **Tier A**, scoped to TIC.
- **`ARTY`** — managed artillery fire missions (counter-battery, on-call) for the frontline.
- **`SHORAD`** — reactive SHORAD wake-up on nearby air threats (pairs with the §7 MFD-hide logic).

### Recon / ISR / detection — *unify the sensor story*
TARS, bigeye EWR, and C-130 ISR each do detection differently. The **`DETECTION_*` family**
(`AREAS`/`UNITS`/`TYPES`/`ZONES` + `DETECTION_MANAGER`) is MOOSE's sensor-fusion engine and already
underpins INTEL. A shared detection substrate could make recon/ISR outputs consistent (and feed the
Python BDA/fog layer more cleanly). **Tier A/B**, per-feature.

### CSAR / downed-pilot recovery — *ready-made*
- **`CSAR` / `RESCUEHELO` / `AICSAR`** — the **SCAR downed-team CSAR loop** (§15) is hand-rolled today.
  Ops.CSAR is the purpose-built version (player or AI rescue, beacons, pickup). Natural **Tier A**
  adoption; would also remove bespoke spawn code.

### Performance & hygiene — *free wins, zero brain conflict*
- **`TIRESIAS`** — switches off AI of far-away ground groups (re-enables within 25nm plane / 10nm
  helo), a big FPS win on dense GermanyCW-style fronts. Pure runtime; touches no decision. **Adopt.**
- **`CLEANUP_AIRBASE`** — clears wrecks/crashes off runways so airbases stay usable across a long
  mission. Cheap UX/FPS. **Adopt.**

### Naval / carrier
- **`RECOVERYTANKER`** — dedicated carrier recovery tanker (pairs with AIRBOSS). **Tier A** for
  carrier-heavy campaigns.

### Logistics
- **`DYNAMICCARGO`** — wraps DCS-native dynamic cargo (there's already an `enable_dcs_dynamic_cargo`
  setting); a MOOSE bridge could unify it with CTLD. **Tier A/B.**
- **`WAREHOUSE` / `STORAGE`** — runtime supply economy. **Careful:** Retribution's economy/logistics
  is a Python pillar — this edges toward **Tier C**. Keep in Python unless a turnless mode wants it.

### Zones / objectives
- **`OPSZONE` / `ZONE_CAPTURE_COALITION`** — runtime zone-capture detection. Useful as a *reporting/
  trigger* primitive (who holds X), **Tier A**; but if it starts driving campaign front movement it's
  duplicating Python's frontline model → keep read-only.
- **`OPERATION`** — mission phase/branch state machine; could structure multi-phase player missions.

## 4. The long view — three horizons

### Horizon 1 — opportunistic Tier-A wins (low risk, do as features touch them)
The "ride-along" adoptions — each an independent, opt-in, in-game-validated plugin, same shape as
MANTIS/CTLD:
1. **`TIRESIAS` + `CLEANUP_AIRBASE`** — pure FPS/hygiene, zero brain conflict, broadest benefit. The
   cheapest wins on the board; arguably do first.
2. **`Ops.CSAR`** alongside the SCAR CSAR loop — replaces hand-rolled spawn/recovery.
3. **`SUPPRESSION`** scoped into TIC — biggest believability jump for the frontline.

### Horizon 2 — a unified player-experience layer (mid-term, higher payoff)
The 414th's identity is its **player-flown depth**. Today that's N bespoke menus. A deliberate
**`PLAYERTASK`/`PLAYERRECCE`/`DESIGNATE` + `SCORING`** spine could make SCAR, TARPS recon, strike, and
JAMMING tasking feel like *one coherent system* — consistent F10, briefings, status, scoring — while
Python still decides *what* the tasks are. This is the highest-leverage Tier-A investment, but it's a
real design project (not a ride-along), so it earns its own spec.

### Horizon 3 — the strategic engine (parked, deliberate)
`CHIEF` / `COMMANDER` / `LEGION…` and `STRATEGO` are a **runtime AI theater commander** — they decide
force tasking, procurement, and territory, with their own persistence. That **is** Retribution's
Python brain, in Lua. The fork has declined this twice (§17 chose in-Python unpredictability;
`turnless.md` keeps the HTN in Python). **Verdict unchanged: out of scope as an add-on.** Its only
honest home is a *funded* turnless/real-time re-architecture that explicitly trades Python campaign
ownership for a MOOSE runtime engine — a strategic fork, not an increment.

## 5. Recommended first moves (if/when this becomes active work)

| Move | Tier | Effort | Why first |
|---|---|---|---|
| `TIRESIAS` (ground-AI culling) | A/perf | S | FPS for everyone, no design risk |
| `CLEANUP_AIRBASE` | A/perf | S | runway upkeep, trivial |
| `Ops.CSAR` for SCAR recovery | A | M | retires bespoke spawn code; flagship-adjacent |
| `SUPPRESSION` in TIC | A | M | frontline believability |
| `PLAYERTASK` spine (spec first) | A | L | the identity play — but design it deliberately |

**Anti-recommendation:** do **not** open `CHIEF`/`COMMANDER`/`WAREHOUSE`/`STORAGE` as "features" —
they're the Python brain's territory. Touch only inside a turnless re-architecture decision.

## Bottom line

Post-MIST, the menu is huge (252 classes) but the *useful* menu is sharp: **a handful of free
perf/hygiene wins, a ready-made CSAR, a frontline-realism boost, and one genuinely strategic
investment — a unified MOOSE player-task layer that would amplify the 414th's core identity.** The
strategic-commander tier stays where the fork twice put it: in Python. Lean into the runtime-service
tier; keep the brain where it is.
