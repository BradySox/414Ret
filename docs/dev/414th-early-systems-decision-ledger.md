# Early-Systems Decision Ledger — the 2026-07-18 deep audit

The squadron's terms for this audit: **the bar is "does it change decisions in play"** — a
system that works but never changes what the DM or the squadron actually does is noise and
gets a kill recommendation; kills are recommended here with evidence and **decided by the
squadron**, per system. Triggers: the DM's own play-feel ("systems feel hollow/static") +
maintenance dread (69 features deep, load-bearing vs cruft unclear). Scope: the
early-systems core (fog/recon, the COIN line, HVT/IED, CSAR/MIA/POW, campaign maker,
will economy).

## Method — three passes, all evidence on disk

1. **Empirical self-play probes** (`tools/system_probe.py`, new): real campaigns generated
   through the engine pipeline, marched 8–18 turns with `pass_turn(no_action=True)`, every
   early system sampled per turn (JSONL). **Intervention scripts** model the player's
   counter-move (`engage` sweeps IEDs/strikes HVTs/kills caches; `throttle_fed`/
   `throttle_starved` isolate the cache throttle; `capture` runs the re-infiltration design
   scenario via the real `ControlPoint.capture`). Ignore-cost vs engage-payoff = the
   decision weight, measured. ~120 self-played turns total, zero crashes.
   *Limitation:* `pass_turn` resolves no combat, so AI-vs-AI attrition is out of scope here
   (flown sessions cover it); turn-boundary systems and cadences are exactly in scope.
2. **Adversarial code reads** of everything the probes flagged (gate step-throughs, e.g.
   the re-infiltration `_best_target` chain evaluated live against the capture scenario).
3. **Eyes-on**: the wave-1/2 client bundle built locally and served against a live
   6-turn Enduring Resolve game (`FastAPI` on `[::1]:16881` + the built client on
   `localhost:3000`); overlays verified in the DOM, circle clustering measured from the
   real `/game/` payload.

## Verdicts

| System | Verdict | Evidence |
|---|---|---|
| C1 regen + cache throttle | **KEEP** | Throttle measured **4:1**: identical 30-unit militia losses refill at +4/turn with caches alive vs +1/turn with all caches dead (`throttle_fed` vs `throttle_starved`). The COIN core loop works. |
| C4 dispersed cells / coalesce | **KEEP** | Under total cache suppression the field cells re-opened 3→6 caches within ~4 turns (both `engage` and `throttle_starved` runs) — the designed whack-a-mole, emergent and real. |
| Roadside IEDs / VBIEDs | **KEEP** | Ignored: 13 detonations / 18 turns ≈ **1.8 mandate/turn** (~a third of the meter over a campaign at ER's 2.5 pricing). Swept every turn: zero, for ~2 standing CAS taskings. Real dilemma, both sides priced. |
| HVT hunt | **KEEP + fixed** | Engaged: 4 momentum kills banked / 18 turns (×4.0 will each). **Fixed this audit:** the ignore-cadence (window 4 + cooldown 3 + resurface = 8) exactly aliased the 8-name table — the same "Qari Zakir" resurfaced eternally; names now rotate by surface count. **Open squadron call:** a lapsed window costs nothing by design — accept, or price a small red-momentum gain on escape. |
| C1.5 re-infiltration | **KEEP** | End-to-end verified empirically for the first time: engine-capture a stronghold at T4, leave it bare → cell T5 → cache T7 → **flipped back red T9**, conservation exact. Garrison-or-lose-it is a real standing decision. (A first probe with a shortcut coalition swap "never fired" — which proved the garrison gate correctly reads surviving defenders as "held".) |
| Ambient convoys + §50 ambush on COIN | **FIX or descope — squadron call** | Blue convoys ran **zero times in 33 measured turns** on ER/IR: the skim-only rule needs `Base.armor ≥ 2` at a blue rear base, and COIN blue forces live entirely as TGO garrisons (front-less ⇒ ~no ground procurement). The §50 ambush rolls per active blue convoy ⇒ the "protect the column" moment cannot occur on exactly the two campaigns that preseed it. Options: (a) garrison-skim fallback, (b) small budgeted blue logistics seed on COIN, (c) un-preseed `convoy_ambush` on ER/IR and own it as a conventional-campaign feature. |
| §35 trail on ER (the ratline) | **FIX — squadron call on shape** | The external-support seeding is an **unbounded free-armor pump on front-less maps**: red `Base.armor` grows +20/turn linearly (0→186 in 8 turns measured; ~600 by turn 30) with no identified consumer — the source re-tops after every delivery, nothing drains the sinks. At minimum it distorts everything reading `total_armor` (garrison counts, assault difficulty). Options: cap the *destination* stock, gate seeding on a front existing, or accept-with-cap. |
| Concealment (§3 + COIN) | **KEEP mechanics, FIX presentation** | Eyes-on: **66 of 104 TGOs concealed on ER**; Tarinkot draws **9 overlapping 3–4 km amber circles** (garrison armor ×3 + AAA ×6 each concealed separately), Frontenac/Jackson 8 apiece — every stronghold is an indistinct amber blob, colliding with the COIN intent that garrisons read exact. Fix direction: merge overlapping suspected circles per cluster server-side (one consolidated circle per site), and/or exempt stronghold garrisons from the generic qualifier on COIN campaigns. |
| Fog of war (§3/§18) | **KEEP** | Morning audit: no dead code, collapse finished, all settings live; flown-verified (G2). Nothing new owed beyond in-app rows. |
| TARS / recon / airecon | **KEEP** | Flown-verified (G2, G19 drone path, G25 partial); the remaining rows are airframe-specific re-flies. |
| Campaign maker | **KEEP** | Not half-baked — landed through Increment D (wizard→paint→finalize→save-as-campaign), BC-A/B/C app-verified 2026-06-24; stale "in progress" docs corrected in PR #638. Owed: the BC-D fly-half (squadron item). Killing it would break saved `blank_canvas` campaigns. |
| kneeboard_recon | **KEPT + fixed** | The flesh-out-or-kill call landed "fix": both measured misalignment causes closed in PR #638 (regional georeference offset ~350 m median now applied to every page; mesh warp kills the ~5 px curvature residual on overviews). Default stays OFF pending checklist H13. |
| CSAR / MIA / POW | **KEEP** | Flown evidence (Scenic Merged: both spawn paths live, 8 MIA banked) + wave-1 made the ledger map-visible (verified rendering live in this audit's eyes-on pass). |
| Will economy | **KEEP** | Feeds bank correctly on skipped turns (probe-verified: counters accumulate, meters move only at debrief commit — by design); the M1 pacing pass stays a flown item. |

**No outright KILL recommendations.** Under the "changes decisions" bar, every early system
either passes with measured numbers or has a concrete, cheap fix; the two squadron calls
(§50-on-COIN, the ER trail pump) are scope decisions, not deletions.

## Fixed during the audit

- HVT leader-name rotation (surface-count indexed; regression test
  `test_leaders_rotate_even_on_the_natural_cadence`).
- The probe harness itself (`tools/system_probe.py`) is committed as reusable audit
  tooling — samplers for every early system + the four intervention scripts.

## Squadron calls — DECIDED (same day) and SHIPPED

1. **§50 on COIN → garrison-skim fallback** (`ambient_convoys._garrison_to_stock`, BLUE
   only): when the stock skim comes up empty, garrison vehicles move into `Base.armor`
   so the normal skim runs — real units, conservation exact, the CP keeps ≥6 garrison
   vehicles and every group keeps ≥2; red never garrison-skims (its militia is the
   C1-anchored insurgency, and §35 already feeds its flow). Blue columns — and the §50
   ambush — now exist on the COIN campaigns.
2. **ER trail pump → destination stock cap** (`TRAIL_DESTINATION_STOCK_CAP` = 3 convoy
   loads): a corridor whose destination already banks that much stops drawing convoys.
   Bounds the front-less-map bank at ~30/corridor; fronted maps drain stock so it
   rarely binds.
3. **HVT lapse → priced as propaganda** (`red_hvt_escaped`, new `WillWeights` field,
   default 0.0; ER/IR price it at 1.5 vs the kill's 4.0): a lapsed window banks a
   small POSITIVE red-resolve move ("propaganda coup"). Counter drains even unpriced;
   the stronghold-fall path never counts as an escape.
4. **Concealment → per-cluster circle merge** (server-side, in `concealed_uncertainty`):
   every concealed radial TGO at a control point shares ONE merged circle (centroid of
   the members' jitters, radius covering every member, capped 8 km) — computed
   statelessly from the CP's siblings so `/game` and SSE always agree, each member
   keeps its own click contract, discovery snaps only that marker to truth, and
   road-pinned IED circles never join. Tarinkot's 9 rings become one blob of suspicion.

## Probe runbook (repeatable)

```
python tools/system_probe.py coin_enduring_resolve --turns 18                       # ignore-cost
python tools/system_probe.py coin_enduring_resolve --turns 18 --script engage       # engage-payoff
python tools/system_probe.py coin_enduring_resolve --turns 12 --script throttle_fed
python tools/system_probe.py coin_enduring_resolve --turns 12 --script throttle_starved
python tools/system_probe.py coin_enduring_resolve --turns 14 --script capture      # C1.5 scenario
```

Set `PROBE_SAVED_GAMES` to a scratch dir (autosaves land there). Output: one JSONL per run.
