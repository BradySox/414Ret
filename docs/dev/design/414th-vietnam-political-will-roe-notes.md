# 414th — Political Will & ROE escalation (the Vietnam campaign layer) — design notes

**Status:** **W1 + W2 LANDED.** W1 = the observe-only political-will model
(`Coalition.political_will`, the `vietnam_political_will` setting, the debrief feed
`game/fourteenth/political_will.py` via `missionresultsprocessor.record_political_will`, the
SITREP band line). W2 = the **negotiation ending**: `negotiation_verdict` backs a gated branch
in `Game.check_win_loss` ahead of the territory checks (RED resolve exhausted → WIN "Hanoi
agrees to terms"; BLUE will exhausted → LOSS "Washington orders withdrawal"; BLUE-loss
precedence on a simultaneous collapse; territory victory untouched), era-framed exhaustion
banners fire once on the crossing edge, and the 4 Vietnam campaigns preseed
`vietnam_political_will: true` (guarded in `_ERA_PRESEED`). The design-§7 feed weights shipped
as-is — the balance pass moved to the first played campaign (checklist M1). **W2b (the static
front) LANDED**: `vietnam_static_front` clamps each front's position to a ±10 % band around its
campaign-start anchor (§2b below; checklist M2). **W3 LANDED**: campaign-phases P0+P1 per the
phases spec (feature §40 — Tier-0 inference + hysteresis + planner emphasis + status surfaces,
generic across all campaigns). **W4 LANDED**: the §3 ROE escalation layer — authored `phases:`
arcs (P2 transitions: `min_turn` schedule + `advance_when` acceleration incl. `blue_will_below`,
so bleeding will speeds escalation), `restricted_zones` (AI planner gate in
`PackagePlanningTask.fulfill_mission`; the player is never hard-blocked — kills inside a zone
drain will sharply via `count_roe_violations` + `BLUE_ROE_VIOLATION`), `target_release` as
per-phase `locked_targets` classes (RESTRICTED badge on the TGO tooltip; sanctuary airfields
fall out of the zones), the red dashed map layer, and the authored **Rolling Thunder → Bombing
Halt → Linebacker → Linebacker II** arcs in all 4 Vietnam campaigns (Kutaisi/Sukhumi/Saipan
play Hanoi per laydown after the 2026-07 Yankee Station coastal-ladder recast, which also keeps
a permanent Tbilisi "PRC border" ring in every phase; in-game pass = checklist M4). **W5 LANDED** — the §6 GCI-ambush
adaptation: `Doctrine.gci_ambush` (VIETNAM only) shrinks the QRA dispatcher's engage radius
to `cap_engagement_range` + caps the scramble radius at 40 NM (`dispatcher_tuning` in
`interceptluadata.py`, per-side in `spawn_intercept_templates`), and the intercept Lua leashes
ambush defenders (disengage 50 NM from home + RTB at 35 % fuel — hit, run, recover); sanctuary
basing falls out of the W4 zones (test-locked). In-game pass = checklist M5.
**The campaign-layer arc W0–W5 is COMPLETE.**
This is the **spec of record** for the month-scale
rework that makes Vietnam mode different at the *campaign* layer, approved 2026-07-01:
**(1) a political-will economy with a negotiation victory** and **(2) an ROE / Route-Package
escalation system** riding the campaign-phases spec
([`414th-campaign-phases-notes.md`](414th-campaign-phases-notes.md)). A third piece —
GCI-ambush MiG behavior — is deliberately thin here: the QRA reserve/dispatcher (§1) is most
of the machinery already and needs *adapting*, not building (see §6).

**Why:** the Vietnam Ops suite (§32–§39) made the era *tactically* authentic, but the
campaign underneath still plays like modern Retribution — capture bases, push the front, win
by territory. The real war was the opposite: fought under Washington's target restrictions
and won/lost by **political pressure**, not conquest. These two systems change *why* you fly
(will, not territory) and *what* you may hit (released targets, not everything you see).

---

## 1. Political will — the resource

One mechanic, two labels: BLUE tracks **Political Will** (Washington/home-front patience),
RED tracks **Regime Resolve** (Hanoi's capacity to absorb punishment). Doctrine supplies the
display name (the §P1b display-layer precedent); the model is symmetric.

> **Generalized 2026-07-02:** the Washington/Hanoi framing and the feed weights are now
> only the *defaults* of a campaign-authorable **will profile** (`will:` YAML block —
> labels, exhaustion banners, per-feed weights, plus a new warship-loss feed). See
> `414th-will-generalization-notes.md`; the model below is unchanged.

- **Model:** `Coalition.political_will: float` (0–100, start 100; tunable per campaign via
  the `settings:` block). Persisted; migrated with a `__setstate__` default so old saves
  load (the `last_sitrep`/`super_gaggle_commitment` pattern).
- **Feeds (all read from the `Debriefing` the results processor already has — the §29 SITREP
  and §37 reconcile precedent; no new Lua, no schema change):**
  - **Airframe losses** drain will, weighted: heavy bombers (the §32 `HEAVY_BOMBER_DCS_IDS`
    set) cost several times a tactical jet — a shot-down B-52 is a national event.
  - **Aviators**: a pilot rescued (Combat SAR, §21) costs airframe-only; a pilot KIA costs
    more; a pilot **captured** (POW, §15) costs more still **and keeps draining a trickle
    every turn he sits in captivity** — the existing 4-turn POW clock and recovery raids
    stop being flavor and become economy. A successful POW recovery refunds the trickle and
    pays a morale bonus.
  - **ROE violations** (from §3 below) drain will sharply — the coupling that makes the
    restriction system self-enforcing for the *player* without hard-blocking them.
  - **Base/territory losses** drain a modest amount (losing ground looks bad on the news).
  - **Restores:** enemy attrition (claimed kills, per the recon-fog framing), captured
    bases, met phase objectives (once §3 lands), and a slow passive regeneration floor so a
    quiet turn heals slightly.
- **Red is symmetric but tuned differently:** Hanoi's resolve is *hard* — it drains mostly
  from **logistics strangulation** (trail convoy losses — §35 is now real and tracked — and
  ground-unit attrition) and from sustained pressure phases, barely from airframe losses.
  This is historically honest (they absorbed catastrophic loss ratios) and creates the real
  strategic question: can you break their logistics before they break your patience?

### Invariants

- Will **never** gates reactive/defensive planning (the §17 boundary). It is an economy +
  win-condition layer, not a commander input in v1. (A later increment may let low RED
  resolve bias the classifier toward defensive phases — deferred.)
- Everything is **default OFF** behind `vietnam_political_will` (Vietnam Ops page,
  campaign-preseeded like the rest of the suite). Off ⇒ zero code paths touched — the
  `check_win_loss` branch and the processor feed both early-return.

## 2. The negotiation victory

With `vietnam_political_will` on, `Game.check_win_loss` gains a branch **ahead of** the
territory checks (which remain as-is — capturing everything still wins):

- **RED resolve exhausted → WIN** ("Hanoi agrees to terms" — the Paris-talks ending). You
  never had to take a single base.
- **BLUE will exhausted → LOSS** ("Washington orders withdrawal") — even with the front
  intact. Losses, POWs, and ROE violations beat you, not the NVA.

The turn-state dialog copy is era-framed (negotiation/withdrawal, not victory/defeat
absolutes). The SITREP (§29) and kneeboard cover (§30) carry a will band every turn —
players must be able to *see* the pressure meter move in the cockpit, or the whole system
is invisible bookkeeping. A client status band lands with the phases P0 payload (§3).

## 2b. The static front (W2b) — bounded oscillation, no sweep-captures

Vietnam's ground war was static attrition — Khe Sanh sat besieged for 77 days without the
line *going* anywhere — but the engine's front position is a pure function of the two bases'
strength ratio (`FrontLine._blue_route_progress` = `blue_strength/total × route_length`, then
the 5 km min-CP-distance adjustment). A sustained strength edge therefore sweeps the front
onto a base and captures it (captures are *physical only*: front reaches a base → frontline
units spawn on its doorstep → runtime `base_captures` events → `commit_captures`; there is no
capture-on-strength-zero code path). That maneuver-war outcome is wrong for the era, and it
short-circuits the whole campaign layer: the war should end at the table (§2), with attrition
paying out through will (§1) — not with the front strolling into Hanoi.

**User decisions (2026-07-01):** bounded oscillation with a **±10 % band** (not a frozen
front — pressure must still read on the map), and **Air Assault captures stay** (deliberate
heliborne ops remain the one territorial lever; only the automatic front-sweep capture path
is removed).

**Mechanism** (`game/fourteenth/static_front.py` + a clamp hook in
`FrontLine._blue_route_progress`):

- `apply_static_front(game)` runs from `Game.initialize_turn` right before ground-war
  planning (idempotent — initialize_turn can run several times per turn). Setting off ⇒
  every front's clamp is cleared (clean disarm; non-Vietnam campaigns and toggled-off saves
  get stock behaviour). Setting on ⇒ each front gets an **anchor** captured once from its
  raw, unclamped position — turn 0 for a new campaign; the current position when enabled
  mid-campaign (documented as acceptable); a front that first appears after an Air Assault
  capture is anchored where it forms — and a clamp of
  `±STATIC_FRONT_BAND (0.10) × route_length` around that anchor.
- The clamp applies to the *position mapping only*, before the min-CP-distance adjustment.
  The strength battle underneath is fully alive: pushes bend the line inside the band and
  keep feeding the will economy; the front just can never reach a base.
- Pickle safety: `FrontLine` has no `__setstate__` and a pickle-sensitive identity
  `__hash__` (untouched). The two new attrs (`static_front_clamp`, `static_front_anchor`)
  are **class-level defaults** read with `getattr(..., None)`, so pre-feature saves resolve
  to "unarmed" and nothing new is required instance state.
- Setting: `vietnam_static_front` (default OFF, Vietnam Ops page, "Campaign" section next to
  the will toggle), preseeded `true` in the 4 Vietnam campaign YAMLs (guarded in
  `_ERA_PRESEED`). Tests: `tests/fourteenth/test_static_front.py` (band math, arm/disarm/
  anchor-once, the real `FrontLine` clamp path at strength extremes, min-dist-after-clamp).
  In-game pass: checklist **M2**.

## 3. ROE / Route-Package escalation (rides campaign phases)

Implements the campaign-phases spec's P0–P2 (`CampaignPhase` plumbing + inference +
conditions) exactly as written — that work benefits **all 66 campaigns** — then adds two
Vietnam-authored extensions to the phase object (both optional, both Tier-2 authored, so
Tier-0 campaigns never see them):

1. **`restricted_zones`** — per-phase circles (center = a named CP or explicit x/y in the
   campaign YAML, radius in NM) where **offensive tasking is forbidden**: the planner gate
   sits in `PackagePlanningTask.fulfill_mission` next to the existing `tasking_whitelist`
   read (a disallowed target scrubs the package, exactly the Vietnam-whitelist mechanics).
   Zones draw on the map (a new layer in the §19 unified panel, styled like threat rings).
   **Player enforcement is soft:** the player *can* strike into a zone — the debrief detects
   kills inside an active zone and charges a sharp will penalty (§1). No hard blocking; the
   LBJ-era pilot could always break the rules and answer for it.
   **Sanctuary airfields** are the special case that matters: enemy airbases inside a zone
   can't be OCA'd — which is what §6's ambush MiGs fly home to.
2. **`target_release`** — per-phase gates on strike-target *classes* (e.g. no
   POWER/FACTORY until phase 2, no airfields until phase 3), checked in the same planner
   gate; locked targets get a "RESTRICTED" badge in the map intel UI instead of vanishing
   (you can see the SAM assembly area; you may not hit it — the defining Rolling Thunder
   frustration, on purpose).
3. **The authored arc** — the 4 Vietnam campaigns get Tier-2 `phases:` blocks modelling
   **Rolling Thunder → pause → Linebacker → Linebacker II**: zones shrink and targets
   release as phases advance. `advance_when` conditions couple to §1: bleeding will
   *accelerates* escalation (Washington's patience for restraint runs out — historically
   backwards-sounding, historically true).

## 4. Delivery plan (each phase = one PR, nothing merges unflown-critical)

| PR | Scope | Risk |
|---|---|---|
| **W0** | This design note | none |
| **W1** | Will model on `Coalition` + debrief feeds + SITREP/kneeboard band. **Observe-only** — no win-condition change, numbers just move. | low (additive; the §29/§37 processor pattern) |
| **W2** | `check_win_loss` branch + `vietnam_political_will` setting + campaign preseeds + feed-weight balance pass | low-medium (win logic; gated) |
| **W2b** | `vietnam_static_front` — the bounded-oscillation front clamp (§2b) so attrition pays out in will, not sweep-captures | low (position mapping only; gated + disarmable) |
| **W3** | Campaign-phases **P0 + P1** exactly per the phases spec (plumbing, classifier, soft emphasis, status band) — all campaigns | medium (commander-adjacent; spec is written) |
| **W4** | `restricted_zones` + `target_release` + will coupling + the authored Vietnam arcs + map layer | medium-high (planner gate + UI) |
| **W5** | §6 QRA→GCI ambush adaptation + sanctuary integration | medium (mostly tuning) |

W1/W2 are independent of W3/W4 and land first — the will economy makes the *existing*
features (CSAR, POW, flak attrition, convoy) matter immediately, before phases exist.

## 5. Persistence & compatibility

- `Coalition.political_will` + the per-turn POW-trickle bookkeeping: `__setstate__`
  defaults; a pre-rework save loads with will full and the feature off.
- Phase state persists per the phases spec §5 (pointer only; definitions re-derived).
- No debrief/state-schema or base-Lua changes anywhere in W1–W4 — every feed reads data the
  `Debriefing` already carries (the lesson of §35/§37: the campaign layer is where the
  accounting belongs).

## 6. GCI-ambush MiGs + sanctuaries (thin — adaptation, not construction) — ✅ LANDED (W5)

User call 2026-07-01: "mostly there with QRA, probably just needs adapting." Agreed. The QRA
reserve already feeds the Moose `AI_A2A_DISPATCHER` (§1) — scramble-on-detection *is* the
GCI model. The Vietnam adaptation, landed as W5 exactly per the plan below
(`Doctrine.gci_ambush` → `dispatcher_tuning` → the intercept plugin's hit-and-run leash;
sanctuary basing verified test-side off the W4 zones; checklist M5):

- **Dispatcher posture per doctrine:** Vietnam-doctrine squadrons get ambush parameters —
  short engagement radius (the P1c 22 NM already helps), hit-and-run disengage (engage
  briefly, then RTB rather than fight to destruction), scramble timed to slash the *strike
  package* rather than duel the sweep.
- **Sanctuary basing:** QRA squadrons based at fields inside an active §3 restricted zone
  are effectively invulnerable on the ground until the zone lifts — which is precisely the
  Rolling Thunder MiG problem, and it emerges from §3 for free.
- No new plumbing expected; a design pass on `game/plugins`/dispatcher parameters + an
  in-game pass. If it grows beyond parameter adaptation, it gets its own note.

## 7. Open decisions (carried, none blocking W1)

- Exact feed weights (start: tactical jet −1, helo −1, B-52 −6, KIA +1 extra, POW −2 &
  −0.5/turn held, ROE violation −5, base lost −3; passive regen +0.5/turn) — tune in W2
  against a played campaign.
- Whether RED resolve should also feed from Arc Light tonnage (a "bombing pressure" term)
  or stay logistics-only in v1.
- Will floor/ceiling effects short of loss (e.g. low will shrinking the BLUE budget) —
  deferred; v1 keeps will → win/loss only, no second-order economy coupling.
- Zone/violation detection granularity at debrief (kill positions are already recorded via
  `destroyed_objects_positions`; confirm coverage is enough before W4).
