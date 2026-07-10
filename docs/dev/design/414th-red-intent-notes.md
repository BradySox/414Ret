# Red Intent — a thinking red opponent (the deferred red arc)

**Status: P0–P4 LANDED** (feature **§55**, registered — the four planner seams below are all wired
and unit-tested, gated `red_intent` default OFF; **P4 (the §53 supply coupling) went live when the
sibling war economy landed**, exactly as the read-only drop-in predicted). The sibling of the
campaign-phases arc (§40) for RED: a per-turn-resolved **posture** that
biases red's planning and, unlike the blue arc, carries *memory* across turns. §55 sits beside the
war-economy pair **§53** (War Economy) / **§54** (Munitions Availability) the other agent scoped in
`414th-war-economy-notes.md` (that branch owns §53/§54; §55 is on this one). Mirrors
`game/fourteenth/phases.py` almost structure-for-structure and hooks the four planner seams that
existed and were previously either blue-gated or driven by a static setting.

Phase status: **P0** observe-only resolver + SITREP · **P1** offensive emphasis · **P2** unpredictability
+ aggressiveness · **P3** ground husbanding (yields to authored `red_tempo`) · **P4** economy coupling
(`_red_supply_health` reads `war_economy.coalition_supply_health`; returns None whenever `war_economy`
is off, so a non-economy campaign is unaffected) — all landed. In-game pass: checklist B7.

**Refinement — "make red smarter" (2026-07-10).** The P0–P4 build shipped the four seams but its
"memory" was thinner than this note always described: it snapshotted turn 0 (a straight copy of
`PhaseBaseline`) and never rolled, so the promised *"blue has hit my IADS two turns running → stay
defensive"* trend reading did not actually exist. This pass builds it, on three axes — all pure
turn-model, all no-ops until real trend/margin data appears (the v1 constants are reproduced exactly
at the default intensity, so every prior test held byte-for-byte):

- **A — Rolling trend memory.** A bounded per-turn `red_intent_history` of turn-stable *levels*
  (`RedIntentSample`: resolve, cumulative front advance, red SAM-site count, both sides' fighter
  counts, red base count, supply) lives on the `Game` (getattr-guarded + `__setstate__` default,
  trimmed to `MEMORY_LENGTH` = 6). Each turn the classifier differences the current sample against a
  **lookback sample** (`_trend_lookback`, ~`TREND_LOOKBACK_TURNS` = 2 back, oldest-available early in
  the game, `None` on turn 1) to read *trends*: the IADS being dismantled (`iads_trend`), resolve
  collapsing (`resolve_trend`, the derivative the instantaneous floor misses), bases bleeding
  (`base_trend`), the front eroding again after a plateau (`front_trend`). Recording is idempotent
  (a same-turn re-init replaces, never appends; the lookback excludes the current turn).
- **C — Richer battle-reading.** Those trends bias a *ground-dominant* red toward `CONSOLIDATE` even
  at a paper edge (the design's central "closing the interdiction→behaviour loop" promise, now driven
  by red's own IADS/resolve/base attrition, not only the §53 supply meter). And a **blue-air-collapse
  opportunity window** (`blue_air_collapsing`: blue lost ≥ `BLUE_AIR_COLLAPSE_FRAC` = 35 % of its
  air-superiority force over the window while red's air holds) lets red `SURGE` at a **reduced ground
  bar** (`SURGE_OPPORTUNITY_GROUND_RATIO` = 1.2 vs the normal 1.5) — red pounces on a transient gap.
- **B — Graduated intensity.** The classifier also yields an **`intensity`** ∈ [0, 1] (how strongly
  the posture is held — a runaway 4:1 surge vs a marginal one; a mild hold vs a collapsing regime),
  latched as `game.red_intent_intensity` and read by the **aggressiveness** and **ground-commit**
  seams so their magnitude scales instead of a flat per-posture constant. The graduated formulas are
  anchored at `DEFAULT_INTENSITY` (0.5) to the v1 midpoints (+/−30 aggressiveness, ×1.35 / ×0.7
  commit), so a *typical* posture is unchanged and only the extremes move. Unpredictability + emphasis
  stay posture-only (bounded blast radius; unpredictability already stacks with §52 C2 decap). The
  intensity also surfaces a "how committed" word on the status detail ("Surging (all-in)",
  "Consolidating (dug in)") via `_intensity_word`, and `_legibility` names the trend driver ("IADS
  falling" / "resolve collapsing" / "losing bases" / "enemy air spent") so a memory-based decision
  explains itself rather than looking like it fired on a healthy snapshot.

  **Made visible (not hover-only), 2026-07-10.** The smart read is surfaced on both player UIs, not
  just the ribbon-chip tooltip: the **kneeboard SITREP** "Enemy posture" line renders the full detail
  (`Sitrep.red_posture_detail` via `sitrep_posture_detail`, recorded in `record_sitrep`) — Python-only,
  so it shows in-game with no client rebuild; and the **web ribbon chip** shows the intensity word
  inline ("ENEMY Surging · all-in", `CampaignStatusJs.red_posture_intensity` via `intensity_word`) with
  an "Enemy intent" block in the expander carrying the full "why" (`red_posture_detail`). Guarded in
  `tests/test_sitrep.py` + the `sitrep_posture_detail`/`intensity_word` tests in `test_red_intent.py`.

  New/extended tests in `tests/fourteenth/test_red_intent.py` cover the trend classifier, the
  opportunity window, the lookback selector, idempotent history recording, the intensity endpoints,
  and the graduated seams (all anchored so the v1 seam tests are unchanged).

**Per-front posture + tuning settings (2026-07-10, follow-on).** The two pieces deferred above:

- **Per-front posture (D).** A theater-wide posture treated a two-front war as one stance — on a map
  where red is 4:1 on one front and 1:4 on another, the aggregate reads ~even and red neither commits
  nor husbands anywhere. Now `_update_front_postures` classifies **each active front** from *its own*
  ground balance (`_front_ground_ratio`) plus the shared theater air/resolve/supply/**trend** read,
  with per-front hysteresis, latching a `FrontPosture` per front on `game.red_intent_fronts` (keyed by
  the cp-id pair; getattr-guarded + `__setstate__` `{}`). The **ground-husbanding seam (4)** is the one
  that goes per-front: `FrontLineStanceTask._posture_commit_factor` passes `self.front_line`, and
  `stance_commit_factor(game, front)` reads that front's posture/intensity via
  `_front_posture_and_intensity` — so red commits reserves on the front it is winning and husbands on
  the one it is losing. The **global seams (emphasis / unpredictability / aggressiveness) stay
  theater-wide** (they are whole-planning-run decisions), as does the UI headline; the per-front
  breakdown surfaces in the ribbon **expander** (`front_postures` → `CampaignStatusJs.front_postures`
  → a list under the "Enemy intent" block, shown only for 2+ divergent fronts). `_front_key` is
  defensive (a duck-typed front → theater fallback), so the seam never raises. Gated
  `red_intent_per_front` (default ON); off clears the dict and every front uses the theater posture.
  Verified end-to-end: on a Berlin-4:1 / Fulda-1:4 board red surges (commit ×1.4–1.7) on Berlin while
  digging in (×0.5–0.7) on Fulda under a theater-"Attrition" aggregate.
- **Tuning settings (the temperament dials).** A `RedIntentTuning` object (default = the base
  constants, so `DEFAULT_TUNING` and a positional `classify_red_intent(m)` are byte-identical) threads
  the settings-derived knobs through the classifier + seams via `tuning_for(game)`:
  **`red_intent_boldness`** (0–100, 50 = neutral) is the master dial — higher lowers the
  surge/opportunity/consolidate ground bars (surges at a smaller edge, turtles only when badly
  outnumbered) and raises `seam_scale` (presses harder once committed: bigger aggressiveness delta +
  commit deviation); **`red_intent_dwell_turns`** tunes the escalation hysteresis; **`red_intent_trend_window`**
  tunes the trend-lookback. All on the Air Doctrine page under Red Intent, all no-ops at their defaults.
  The seam formulas are re-anchored so `seam_scale`=1 + intensity=0.5 reproduce the v1 numbers exactly.
  Tests cover `tuning_for`, the boldness-widened surge zone, the scaled seams, the dwell/window
  overrides, the per-front helpers, and the full per-front divergence + fallback.

Decided calls (session 2026-07-08):

- **[DECIDED] Three postures** — `CONSOLIDATE / ATTRITION / SURGE`. The earlier fourth
  ("Feint") is folded into `ATTRITION` as a moderate-unpredictability default rather than its
  own posture.
- **[DECIDED] Full memory from v1** — the classifier reads current state **plus last-turn
  deltas plus red resolve**, so red has genuine multi-turn continuity from the first build (the
  whole point of "thinking"). No current-state-only interim step.
- **[DECIDED] Authored windows win** — during an active `red_tempo` pulse (the authored Vietnam
  arc, W6) emergent red_intent **yields its ground-stance hook** so it never overrides a
  campaign author. See Composition.

---

## The gap

Red has no brain across turns. Confirmed in code:

- Both coalitions run the **same** HTN commander (`TheaterCommander`,
  `game/commander/theatercommander.py`), and `TheaterState.from_game`
  (`game/commander/theaterstate.py`) rebuilds the entire world snapshot **from scratch every
  turn**. There is no persisted planner state, no reserve concept, no record of what the player
  did last turn.
- The campaign-phase emphasis — the fork's whole "what should I prioritize" reorder — is
  **blue-only**: `PlanNextAction._offensive_order` (`game/commander/tasks/compound/nextaction.py:66`)
  early-returns the stock order for `not coalition.player.is_blue`, and its docstring says
  outright that *"a red arc is deferred."* **This feature is that deferred arc.**
- The one red-specific knob, `ObjectiveFinder._offensive_roll`
  (`game/commander/objectivefinder.py:199`), is re-seeded per `(turn, cp.name)` — coherent
  within a turn, amnesiac between them, so red's posture never *builds*.
- `game.red.political_will` (Regime Resolve) is tracked by the will economy but drives
  **nothing** in planning. Red intent is where that signal finally reaches the commander.

The result reads as "scripted": red plays the same reactive defense + default offensive
ordering every turn, whatever the state of the war.

## Design — a red posture, resolved each turn, mirroring `phases.py`

A new `game/fourteenth/red_intent.py`, built as a near-carbon-copy of the phase machinery:

- **`RedPosture`** — three legible intents, each a permutation of levers red already responds
  to:
  - **`CONSOLIDATE`** (turtle) — defend everything, husband reserves, focused targeting.
    Under pressure: losing ground, low resolve, or just lost a base.
  - **`ATTRITION`** (default) — the stock offensive ordering with a *moderate* unpredictability
    floor (this absorbs the dropped "Feint" idea — red is never perfectly deterministic, but it
    neither commits nor turtles). Grind and trade.
  - **`SURGE`** (push) — abandon defense to commit fighters, commit ground reserves,
    `CaptureBases`/`PlanFrontLineCas` emphasis. On a materiel/air advantage or a window.
- **Emphasis tuples** per posture over `OFFENSIVE_METHODS`
  (`game/fourteenth/phases.py:251`, the fixed set the two modules share) — kept as **class-name
  strings** exactly like the phases so this module never imports the commander (no cycles); the
  same sync-lock test that guards phases is extended to cover these.
- **`classify_red_intent(metrics) -> RedPosture`** mirroring `phases.classify`, and
  **`update_red_intent(game)`** mirroring `update_campaign_phase` — hooked in
  `Game.initialize_turn` **right after** `update_campaign_phase(self)`
  (`game/game.py:722`), **before** either coalition plans (so the fresh posture is in place when
  the red commander runs at `game.py:735`).
- **Latched state on `Game`**, getattr-guarded + `__setstate__` `setdefault` (the
  `current_phase_key`/`phase_entered_on_turn` precedent at `game/game.py:133,237`):
  `red_intent_key`, `red_intent_entered_on_turn`, and the memory snapshot below. Everything
  derived is recomputed, never pickled.
- **`active_red_intent(game) -> Optional[RedPosture]`** — the resolver the four seams consume,
  exactly as `active_phase` is consumed. Returns `None` (⇒ stock behavior) when the feature is
  off, red fields no relevant CPs, or a pre-feature save hasn't been classified yet.

### Memory (the new capability — [DECIDED] 2a)

Everything the seams touch, red already *reacts* to within a turn; the new thing is reading
**prior-turn state** to choose the posture. `classify_red_intent` reads a
`RedIntentMetrics` (mirroring `PhaseMetrics`) built from:

- **Current ground balance** — red deployable front-line units / blue, across active fronts
  (`ControlPoint.deployable_front_line_units`, the same ratio the stance tasks use).
- **Air/IADS health** — is red's fighter force / SAM belt intact (the accessors the phase
  classifier already uses).
- **Red resolve** — `game.red.political_will`, previously unused by planning.
- **Last-turn deltas** — front movement, base captures for/against, and losses taken vs claimed
  since last turn. Sourced from a rolling snapshot updated each `update_red_intent` and diffed
  against this turn — the **same lazy-snapshot technique as `PhaseBaseline`**
  (`game/fourteenth/phases.py`), but rolling rather than turn-0-only. This is what gives red
  continuity: "blue has hit my IADS two turns running → stay defensive," "I've been pushed back
  → CONSOLIDATE and husband," "I broke through last turn → press the SURGE."

**Hysteresis, asymmetric.** Min-dwell before escalating (a jump to `SURGE` needs the advantage
to hold for ≥N turns — no lunging at a one-turn fluke), but **de-escalation to `CONSOLIDATE` is
immediate** — a real command reacts to a lost base at once. Same dwell machinery as the phase
classifier, with the one-way fast path added.

## The four consumption seams (all confirmed, all pre-cut)

1. **Offensive emphasis — primary.** `nextaction.py:_offensive_order` (line 66) today
   early-returns `stock` for non-blue. Replace that branch: red + `active_red_intent` → the
   posture's emphasis ordering, resolved through the **same name-keyed `_OFFENSIVE_FACTORIES`
   indirection** (`nextaction.py:47`) the blue phases already use. The unknown-name / missing-name
   guards there apply unchanged. The reactive prefix (`TheaterSupport`/`ProtectAirSpace`/
   `DefendBases`) and the `RecoverySupport` tail are **never** touched — the §17 boundary.
2. **Unpredictability.** `targetorder.py:_unpredictability_for` (line 29) — add a red-intent
   modifier **right beside** the C2-decap `unpredictability_bonus`, same clamp-to-100 path.
   `ATTRITION` sets a small floor; `SURGE` → ~0 (focused); `CONSOLIDATE` → low. C2 decapitation
   is the exact template — a clean additive per-side modifier already plugged in here — and the
   two **stack** (a decapitated, attrition-postured red is more erratic; correct).
3. **Aggressiveness.** `objectivefinder.py:vulnerable_control_points` (line 151) + `_offensive_roll`
   (line 199), red-only already. Route the static `settings.opfor_autoplanner_aggressiveness`
   read through an `effective_aggressiveness(game)` that intent biases: `SURGE` raises it (red
   abandons more bases to attack), `CONSOLIDATE` lowers it toward 0 (defend everything).
4. **Ground husbanding.** The stance thresholds (`have_sufficient_front_line_advantage` in
   `frontlinestancetask.py` + `breakthroughattack.py` ≥2.0, `aggressiveattack.py`,
   `eliminationattack.py`) and the raise-only `red_tempo._apply_ground_offensive` hook. `SURGE`
   lowers the ratio needed to commit (spend reserves); `CONSOLIDATE` raises it (hold reserves).
   Deepest hook — built last (P3).

## Tie-in with the war economy (§53) — the read-only contract

This is where red_intent becomes *fully* interesting, and it must dovetail cleanly with the
other agent's war-economy build without either feature reaching into the other's state.

**Direction is one-way: red_intent READS economy state; it never writes it. The economy never
reads intent.** The economy owns the *material* model (production → transport → per-base
`Base.supply` → combat effectiveness); red_intent is a *cognitive* layer that reads whether red
*can* fight and lets that decide how red *chooses* to fight.

### Interface stub — §53 implements against this

The whole coupling rides **one pure read accessor**, and §53's own design already provides the
per-CP primitive it needs. §53 confirmed (in `414th-war-economy-notes.md`) an **accumulating
`Base.supply` stockpile** with a per-CP **`supply_factor`** (`Base.supply / demand`, clamped to
[0, 1]) as the input to its combat bite. Our accessor is just that factor **aggregated over the
active-front CPs** — so the one `TODO` below is not new math, it's *"reuse §53's `supply_factor`."*
**[LOCKED 2026-07-08]** §53 ships `supply_factor(cp)` as a **module-level function** in
`war_economy.py` from its **P0** (the ratio needs only `Base.supply` + a demand baseline, both
present in P0). So red_intent's P4 integration is unblocked from day one — **no shim needed**,
and P0–P3 stay economy-independent. (§53 already computes the same factor internally for its
combat bite at [game.py:515](../../../game/game.py) /
[`front_line_capacity_with`](../../../game/theater/controlpoint.py:1209).)

```python
# game/fourteenth/war_economy.py  (OWNED BY §53 — red_intent only calls it)

def coalition_supply_health(game: "Game", coalition: "Coalition") -> float:
    """Materiel readiness of ``coalition`` in [0.0, 1.0]. PURE READ, no side effects.

    1.0 = the coalition's fighting front is fully supplied; 0.0 = starved.
    Aggregate over the coalition's *active-front* control points (the CPs whose
    front actually matters this turn), so cutting the supply feeding the fight
    moves this number even while deep-rear depots stay full.

    Robust to whichever model §53 chose:
      * stockpile  -> current Base.supply / that base's full-supply capacity
      * per-turn flow -> delivered supply this turn / required-for-full-effect
    Clamp each base to [0, 1] and average (weight by front size if convenient).
    Return 1.0 for a coalition with no active front (no fight to starve).
    """
    total = 0.0
    count = 0
    for cp in game.theater.control_points_for(coalition.player):
        if not cp.has_active_frontline:      # only the CPs in the fight
            continue
        # §53 already computes this as its per-CP combat-bite input -- reuse it:
        total += supply_factor(cp)   # Base.supply / demand, clamped to [0, 1]
        count += 1
    return 1.0 if count == 0 else total / count
```

**Consumer side (ours, P4) — lazy import + graceful absence, so P0–P3 need none of this:**

```python
# game/fourteenth/red_intent.py  (in the RedIntentMetrics builder)
def _red_supply_health(game: "Game") -> float | None:
    """Red materiel readiness, or None when §53 is absent/off -> term drops out."""
    if not game.settings.plugin_option("war_economy") ...:   # or the real gate check
        return None
    try:
        from game.fourteenth.war_economy import coalition_supply_health
    except ImportError:
        return None                                          # §53 not present yet
    return coalition_supply_health(game, game.red)
```

`classify_red_intent` treats `None` as "no supply signal" — the posture falls back to the
ground/air/resolve reading. So the accessor's **absence is a first-class, tested case**, not a
crash: P0–P3 ship and work with `war_economy` entirely unbuilt.

`red_intent` imports it **lazily** and degrades gracefully: if the economy feature is off or the
module/accessor isn't present, the supply term simply **drops out** of `RedIntentMetrics` and
the classifier falls back to the ground/air/resolve reading (so red_intent P0–P3 ship and work
with `war_economy` absent).

**How supply modulates the posture (P4):**

- **Starved supply forces `CONSOLIDATE`** regardless of a favorable ground ratio — red can't
  press an offensive it can't fuel. This is the key coupling: without it, red would "surge" on a
  paper advantage while its logistics are cut; with it, **interdicting red's supply visibly makes
  red turtle**, closing the loop between the player's strike campaign and the enemy's behavior.
- **Healthy supply + advantage → `SURGE`** — red presses only when it can sustain the push.
- The reciprocal is emergent, not coded: the economy's combat model spends supply as red fights,
  so a `SURGE` red drains its own stock faster and a starved front stops recovering (§53's
  `affect_strength` scaling) — red_intent doesn't spend anything, it just reads the meter and
  reacts next turn. Clean separation, no shared writes.

**Coordination status — LOCKED 2026-07-08:** §53 ships `supply_factor(cp)` module-level from its
P0, so `coalition_supply_health` (which just aggregates it over active-front CPs) has a
guaranteed callee — no shim, no signature negotiation left. P0–P3 still carry **no** dependency
on §53 and land first; P4 drops in against a function that already exists.

## Composition & boundaries

- **[DECIDED] Authored `red_tempo` wins.** When `red_tempo.ground_offensive_active(game)` is
  true (an authored Vietnam pulse — Tet/Easter), red_intent **suppresses its own seam-4 stance
  bias** and lets `apply_red_tempo` own the stances (it already runs later in `initialize_turn`,
  `game/game.py:775`, and is raise-only). Emphasis/unpredictability/aggressiveness (seams 1–3)
  may still apply — they don't conflict with the authored pulse. Net: the campaign author's
  scripted moment is never double-driven or overridden.
- **Composes with the blue campaign-phase arc.** Blue's "intent" is the phase arc (§40); red's
  is this. They read independent state and touch disjoint code paths (`_offensive_order` is
  gated per coalition). No interaction to manage beyond the shared `OFFENSIVE_METHODS` name set.
- **The §17 boundary holds.** Red's *reactive* defense (`TheaterSupport`/`ProtectAirSpace`/
  `DefendBases`) stays deterministic. Intent biases only the offensive ordering, the
  opportunistic-target shuffle, the offensive/defensive commit roll, and (authored-permitting)
  the ground-stance thresholds — never the reactive prefix.
- **Red-only by design.** Blue-AI intent (for red-playing humans) is a possible later mirror but
  out of scope — blue already has the phase arc.
- **No save-schema pain.** Only the latched key + entry turn + the rolling memory snapshot
  persist, all getattr-guarded with `__setstate__` defaults; a pre-feature save classifies fresh
  on first load (identical to how phases bootstrap the turn-0 baseline).

## Phasing — each independently shippable, fastest-visible first

- **P0 — Resolver + observe-only.** The module, classifier (with memory + hysteresis), the
  `update_red_intent` hook, the latched state, and a **SITREP band + client ribbon line**
  ("Enemy posture: consolidating"). **No planner effect yet** — watch red's *read* of the war
  for a few turns to validate the classifier (the will/phases W1 observe-only precedent).
- **P1 — Offensive emphasis (seam 1).** The fastest visible bite: red visibly reprioritizes by
  posture. Self-contained; the docstring invites it.
- **P2 — Unpredictability + aggressiveness (seams 2 + 3).** Both single-function modifier
  inserts on the C2-decap template.
- **P3 — Ground husbanding (seam 4).** The reserves logic on the stance thresholds, yielding to
  authored `red_tempo` per the decided composition.
- **P4 — Economy coupling.** Wire `coalition_supply_health` into `RedIntentMetrics` once §53
  lands. Read-only; no collision with the economy build.

## Gating / testbed / tests / docs

- **Gating:** a `red_intent` setting (Air Doctrine page), **default OFF**, kill-switch pattern;
  preseeded **ON** in the testbed campaign.
- **Testbed:** **Red Tide** — a peer fight where red has real offensive agency (advanced IADS,
  symmetric front), so posture actually shows. Composes with, and is a good stress test
  alongside, §53 (also preseeded there).
- **Tests:** `tests/fourteenth/test_red_intent.py` — `classify_red_intent` picks the right
  posture per metrics; asymmetric hysteresis (dwell to escalate, immediate to `CONSOLIDATE`);
  the emphasis tuples all resolve against `_OFFENSIVE_FACTORIES` (extend the nextaction sync-lock
  test); the unpredictability/aggressiveness modifier math; off / blue / no-red-CP / pre-feature-
  save no-ops; the `red_tempo`-active seam-4 suppression; the graceful `war_economy`-absent
  fallback. Extend `tests/test_planner_unpredictability.py` for the stacked red-intent + C2-decap
  clamp.
- **Docs:** register §55 in `game/fourteenth/features.py`; add sections to
  `docs/dev/414th-features.md` and `README.md` (player-visible: "red now plays with intent");
  sync `CLAUDE.md`/`AGENTS.md`; add a `docs/dev/414th-ingame-pass-checklist.md` row (pass
  criterion: red visibly changes how it plays as the war turns — surges when ahead/supplied,
  consolidates when hit/starved).

## Delivery

One PR per phase (P0 → P4), each green through Black/mypy/pytest and each leaving red_intent in a
coherent state. P0–P3 land independent of §53; P4 drops in against §53's `supply_factor(cp)`
(LOCKED module-level from §53's P0), so it has no wait — `coalition_supply_health` just
aggregates that factor over active-front CPs.
