# 414th — Political Will & ROE escalation (the Vietnam campaign layer) — design notes

**Status:** **W1 LANDED** (the observe-only political-will model: `Coalition.political_will`,
the `vietnam_political_will` setting, the debrief feed `game/fourteenth/political_will.py` via
`missionresultsprocessor.record_political_will`, and the SITREP band line; tests
`tests/fourteenth/test_political_will.py` + the sitrep will-band tests). W2–W5 outstanding.
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

## 6. GCI-ambush MiGs + sanctuaries (thin — adaptation, not construction)

User call 2026-07-01: "mostly there with QRA, probably just needs adapting." Agreed. The QRA
reserve already feeds the Moose `AI_A2A_DISPATCHER` (§1) — scramble-on-detection *is* the
GCI model. The Vietnam adaptation, deferred to W5:

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
