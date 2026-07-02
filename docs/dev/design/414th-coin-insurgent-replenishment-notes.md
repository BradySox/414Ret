# 414th — COIN insurgent replenishment — design notes

**Status: DESIGN ONLY (2026-07-02).** Nothing here is built. This is the design-pass
blocker for the COIN campaign called out in `414th-will-generalization-notes.md` §5/§6
— squadron call 2026-07-02: COIN is the next campaign direction (Korea dropped), base
skeleton = a fork of **Operation Shattered Dagger**, and **no campaign work starts
until this model is agreed.**

---

## 1. The problem, confirmed in shipping content

Retribution's ground economy is a state army's: `ProcurementAi.reinforce_front_line`
spends coalition **budget** at control points that have a **ground-unit source**
(factory / logistics connectivity), and the units arrive by **transfer** down the
supply network. An insurgency fails every clause of that sentence — no treasury, no
factories, no convoys it depends on — and the shipped COIN campaigns prove the gap
two different ways:

- **Operation Shattered Dagger** zeroes it out (`recommended_enemy_money: 0`,
  `income_multiplier: 0.0`): the insurgents literally cannot replace a single
  technical. It plays as a clearance shooting gallery — kill the 49 placed groups and
  the war is over. One-shot, no living insurgency.
- **Valley of Rotary** funds it normally: the "insurgents" then reinforce through the
  stock buy-at-bases loop like a conventional army — wrong texture, and the classic
  failure the author of Shattered Dagger was avoiding (the engine happily buys the
  Taliban SAM batteries if the faction had any).

What COIN needs is regeneration that is **cheap, steady, dispersed, budget-less,
factory-less** — and throttled by the things the *player* can attack (caches, the
ratline), not by income.

## 2. Design principles (inherited hard lessons)

1. **Real units only.** No phantom runtime spawns — the §35 convoy and §37 Super
   Gaggle reworks both exist because `coalition.addGroup` units cost the enemy
   nothing and broke the debrief. Everything regenerated here lands in the force
   model (`Base.commission_units`, real TGOs) and dies through the normal loss path.
2. **Off = zero code paths.** Gated by a `coin_insurgency` setting (default OFF,
   campaign-preseeded like the Vietnam Ops suite). Non-COIN campaigns never touch it.
3. **The §17 boundary stands.** Regeneration is an economy layer; it never gates or
   randomizes reactive/defensive planning.
4. **Python plans, Lua executes** — and v1 needs **no Lua at all**: regeneration is a
   turn-boundary force-model operation, same shape as `ensure_enemy_trail_convoy`.

## 3. The model

One new module, `game/fourteenth/coin.py`, one entry point run from
`Game.finish_turn` next to the existing hooks (`ensure_enemy_trail_convoy` at
`game.py:382`, `plan_super_gaggle` at `:390`):

```
regenerate_insurgent_cells(game)   # no-op unless coin_insurgency is on
```

### 3.1 Cell regeneration (the trickle)

Each turn, every **insurgent-held control point** regenerates garrison strength:

- Units are commissioned **directly and free** into `cp.base.armor`
  (`Base.commission_units`) — no budget, no ground-unit source, no transfer. That is
  the point: infiltration, not logistics.
- **Rate**: a small base trickle (order 1–3 units/turn/CP, tunable) scaled by the
  CP's **cache health** (§3.2). The trickle is deliberately below what a purposeful
  BLUE clearance kills — attrition alone must be able to outpace it locally.
- **Cap**: each CP regenerates only **toward its campaign-start garrison** (a
  lazily-snapshotted anchor, the `static_front`/`PhaseBaseline` pattern). The
  insurgency refills; it never *grows* past turn 0. No snowballing.
- **Unit whitelist, hard-coded in the module**: infantry, technicals/scouts,
  AAA/SHORAD-class, light rocket artillery — drawn from what the faction actually
  fields (`insurgents`/`taliban_2001` rosters are already clean). Armor, IFVs, SAMs,
  and EWRs are **never** regenerated even if a faction somehow carries them. A
  companion `INSURGENT_GROUND_PROCUREMENT` ratios constant (the
  `VIETNAM_GROUND_PROCUREMENT` precedent, `game/data/doctrine.py:412`) fixes the mix
  for any budget the campaign *does* grant.

### 3.2 Caches (the thing BLUE actually fights)

The regeneration rate is throttled by **shadow infrastructure the player can find
and destroy** — no new TGO type needed:

- A CP's **caches** = its alive insurgent `BuildingGroundObject`s of category
  `ammo` (natively supported — `theatergroundobject.py:407`), optionally `factory`/
  `ware`, within a cache radius of the CP. The forked campaign authors 2–4 ammo-dump
  TGOs per stronghold in the miz.
- **Cache health** = alive fraction of the CP's turn-0 cache set (anchored like the
  garrison cap). Full caches ⇒ full trickle; each destroyed cache cuts it
  proportionally; **all caches dead ⇒ a residual floor trickle** (≈25% — infiltration
  never fully stops, but a cleared stronghold decays under any sustained pressure).
  The floor keeps "clear" from being a binary switch; the will economy (§4) is what
  actually ends the war.
- Caches are ordinary strike/BAI targets, visible under the existing recon fog —
  **TARPS/AI recon confirming a cache is the COIN intel loop for free.**

### 3.3 The ratline (reuse, not construction)

The §35 trail-convoy machinery is already the insurgent supply-interdiction
mechanic — `ensure_enemy_trail_convoy` just needs its gate widened (a shared helper
honoring `coin_insurgency` **or** `vietnam_convoy_interdiction`; the module is
already coalition-generic inside). A convoy killed on the ratline is a real loss and
(§4) a resolve hit. Deliberately *not* coupling convoy arrival to cache health in
v1 — one throttle (caches → regen) keeps the loop legible.

## 4. Will coupling (rides the #417 profiles)

The COIN campaign is the first real consumer of the authored `will:` block, and it
inverts the Vietnam weights — the insurgency's whole theory of victory is that
**killing its cells is worthless and killing patience is everything**:

| Feed | Vietnam default | COIN direction |
|---|---|---|
| `blue_airframe_loss` | 1.0 | **2.0+** — every loss is a news cycle |
| `blue_roe_violation` | 4.0 | **6.0+** — hearts-and-minds priced hard |
| `red_ground_unit_lost` | 0.25 | **~0.05** — body count buys nothing |
| `red_convoy_unit_lost` | 1.5 | keep — the ratline hurts |
| `red_base_lost` | 3.0 | **5.0+** — losing a stronghold is the real currency |
| `blue_passive_regen` | 0.5 | **lower/zero** — time itself drains the mandate |

Labels: BLUE ≈ "the Coalition's mandate", RED ≈ "the insurgency's momentum";
exhaustion = "The Coalition withdraws" / "The insurgency collapses".

**One small engine follow-on**: a `red_cache_lost` weight in `WillWeights`
(default **0.0** — inert everywhere else), fed by the coin module identifying its
cache TGOs in the turn's ground-object losses. Destroying caches is then the double
lever: throttles regeneration *and* drains momentum. (Without it, caches ride the
generic `ground_objects` count — acceptable v1 fallback, weaker signal.)

`blue_passive_regen: 0` in the profile already gives the "duration drain lite";
a true negative per-turn drain (`blue_turn_drain`) stays deferred until pacing play
shows it's needed (per the generalization note §6).

## 5. What stays stock

- BLUE's whole economy and planner: untouched. Air Assault remains the capture
  lever; territory victory (clear every stronghold) still works alongside the
  negotiation ending.
- Insurgent *air* (none) and IADS (none): nothing here spawns air or SAMs, ever.
- Red-only in v1 (the insurgent side is the opfor, matching every gated Vietnam
  piece). A "blue insurgency" symmetry is explicitly out of scope.

## 6. Delivery plan (one PR each, C-series)

- **C1 — the regen core**: `game/fourteenth/coin.py` (trickle + anchor cap + cache
  health + whitelist), the `coin_insurgency` setting, `finish_turn` hook, full unit
  tests (anchored cap, cache throttle + floor, whitelist, off-switch, no-op guards).
- **C1.5 — the re-infiltration design pass** (design only, squadron call §7.3):
  written **immediately after C1 is verified working** (headless multi-turn sanity —
  regen visibly refills a stronghold, cache kills visibly throttle it), before or in
  parallel with C3. Scope: the insurgency retaking neutral/lost CPs, cache-seeded and
  will-coupled; its own note.
- **C2 — will coupling**: `red_cache_lost` weight (default 0.0, default-equivalence
  preserved), the cache-loss feed, tests.
- **C3 — the campaign**: fork Shattered Dagger (credit Starfire, the Khe Sanh/
  Yankee Station precedent) — restore a real (small) insurgent income, preseed
  `coin_insurgency` + harassment (§36) + convoy interdiction (§35) + the `will:`
  profile, author the cache TGOs per stronghold and a Clear → Hold → Build `phases:`
  arc with ROE zones around towns.
- **C4 (later) — dispersed harassment cells**: occasional real TGO cells placed near
  contested CPs via the §20 `place_unit_group` machinery (mortar teams in the blue
  rear). Optional texture; not load-bearing.

## 7. Squadron calls — RESOLVED 2026-07-02

1. **Cache floor: [DECIDED] 25% residual trickle** when all caches are dead — a
   cleared stronghold decays under sustained pressure but infiltration never fully
   stops; the will economy is what ends the war.
2. **Cache categories: [DECIDED] `ammo` only** in the engine; the campaign author
   controls cache density in the miz.
3. **Re-infiltration: [DECIDED] deferred from v1** (the v1 insurgency defends and
   bleeds, never expands) — **but with a hard follow-up commitment**: a full
   re-infiltration design pass (its own note — the insurgency retaking neutral/lost
   ground, presumably cache-seeded and will-coupled) is owed **immediately after the
   C1 shell is verified working**, not parked indefinitely. See C1.5 in §6.
