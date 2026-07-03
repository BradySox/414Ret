# 414th — COIN re-infiltration (the insurgency retakes ground) — design notes

**Status: LANDED (2026-07-03).** Built in `game/fourteenth/coin.py`
(`advance_reinfiltration` + the staged pipeline + `consume_reinfiltration_flips`),
hooked from `Game.finish_turn` right after `regenerate_insurgent_cells`, gated
`coin_reinfiltration` (default OFF, preseeded ON in the campaign), will handoff wired
into `update_political_will` (charged at the `blue_base_lost` weight). The four §8
squadron calls were resolved to the proposed defaults (HOLD_THRESHOLD=4, 2+2 timers,
one attempt theater-wide, neutral+lost scope). Tests: `tests/fourteenth/test_coin_reinfiltration.py`
(off-switch, eligibility clauses, conservation bound, stage advance/seed/revert/flip,
abort+cooldown, will consume). **One implementation change vs the sketch, forced by the
engine:** a TGO's allegiance follows its parent CP's owner (`is_friendly`/`coalition`
read `control_point.captured`), so a *red* cell cannot attach to a blue/neutral target
CP — it would render blue. The cell + cache therefore attach to the **source red
stronghold** (positioned near the target via `_infiltration_point`) and are **reparented
to the target on flip** (`_reparent`), which is where they become the new stronghold's
starting militia + first cache. In-game pass owed (checklist P3). Original design below.

This is the **C1.5** pass committed in
`414th-coin-insurgent-replenishment-notes.md` §7.3 (squadron call: re-infiltration
deferred from v1 *with a hard follow-up commitment* — this note, written immediately
after the C1 shell met its headless bar). Read that note first; this one extends its
model and inherits its principles wholesale.

---

## 1. Why — C1 alone still loses to sequential clearance

C1 makes an insurgent stronghold *resilient* (it refills toward its anchor), but
ground taken from it stays taken forever: BLUE can clear strongholds one at a time,
garrison nothing, and grind to a territory win with patience the will economy may
not fully price. The COIN triad is **clear → hold → build**, and C1 only implements
the enemy side of *clear*. Re-infiltration is what makes **HOLD a real decision**:
a cleared stronghold left ungarrisoned is an invitation, and the player must spend
finite ground forces (and Air Assault lift) holding ground that no longer shoots
back — or watch it quietly change hands again.

## 2. Design principles (inherited + two new)

All of C1's rails apply (real units/TGOs only, off = zero code paths, §17 planner
boundary, no Lua — everything is turn-boundary force-model work). Two additions:

1. **Legible and counterable, never instant.** Re-infiltration is a *staged,
   announced pipeline* over several turns. Every stage produces something the
   player can see (an intel message, a real TGO on the map) and attack. A flip
   must never feel like the campaign cheated; it must feel like a warning the
   player ignored three times.
2. **Conservation — relocate, never grow.** The insurgency's total stronghold
   count never exceeds its turn-0 count. While it still holds everything it
   started with, it cannot infiltrate anywhere; once BLUE takes a stronghold, the
   insurgency may re-establish — at the lost CP *or* an eligible neutral one (the
   squadron-approved "neutral/lost" scope). The C1 "refill, never grow" philosophy
   at the territorial level.

## 3. The model — a three-stage pipeline

One attempt active theater-wide at a time (v1 — legible, not whack-a-mole),
evaluated once per turn from `finish_turn` immediately after C1's regeneration,
state-machined in `game.coin_state` (a `"reinfiltration"` sub-dict, plain
primitives).

### 3.0 Target eligibility

A CP qualifies as an infiltration target when ALL hold:

- **BLUE-held or NEUTRAL** (never red — that's C1's job), and not a carrier/LHA
  (`capture` raises there by design) or off-map point.
- **Under-held**: BLUE garrison at the CP ≤ `HOLD_THRESHOLD` (proposed: **4
  ground units** — a token picket doesn't count as holding). Neutral CPs have no
  garrison and always pass this clause.
- **Reachable**: within `INFILTRATION_RANGE` (proposed: **~60 km**) of a live
  insurgent stronghold whose C1 **cache health ≥ 0.5** — a strangled stronghold
  cannot project. (This is the second payoff of cache strikes: they suppress both
  regeneration *and* expansion.)
- **Never a player field**: not the departure/arrival/divert of any client flight
  and no based BLUE squadrons — the §36 anti-grief guarantee, applied to ground.
- **Conservation**: current red CP count < turn-0 red CP count.

Preference when several qualify: formerly-red CPs first (retaking home turf),
then the eligible neutral CP nearest a live stronghold.

### 3.1 Stage 1 — the infiltration cell (announced)

A small **real cell TGO** (2–3 whitelisted units — the C1 pool: infantry/
technicals, spawned free via the §20 `place_unit_group` machinery near the target
CP) appears, and BLUE gets an intel message: *"Intel: infiltration reported near
{CP}."* The cell is an ordinary Armed Recon/BAI/CAS target under normal recon fog.

- Cell killed → the attempt **aborts** and the pipeline cools down
  (`COOLDOWN_TURNS`, proposed 3) before any new attempt anywhere.
- Target garrisoned above `HOLD_THRESHOLD` at any stage → the attempt aborts the
  same way (holding ground works without firing a shot).

### 3.2 Stage 2 — the established cache (the seed)

If the cell survives `STAGE1_TURNS` (proposed **2**) with the target still
under-held, a **cache TGO** (`category == "ammo"`) spawns beside it + a sharper
message: *"Infiltrators are established near {CP} — a supply cache has been
located."* Killing the cache reverts the attempt to stage 1; killing the cell
still aborts. This cache is deliberately the same object C1 throttles on — if the
flip succeeds it becomes the new stronghold's first cache.

### 3.3 Stage 3 — the flip

After `STAGE2_TURNS` more (proposed **2** — so ~4 turns of escalating warnings
end to end), the CP flips at the turn boundary via the engine-native
`ControlPoint.capture(game, events, Player.RED)` (which already retreats units,
refunds orders, releases parking, resets strength, and rebuilds front lines), and
a small **re-infiltration garrison** is commissioned from the C1 pool
(`REINFIL_GARRISON`, proposed **6 units** — well below any original anchor). C1
then re-anchors the CP automatically at that small garrison + the one seeded
cache: **retaken strongholds come back weak** and must regrow under the same
cache-throttled trickle, so a flip is a setback for BLUE, not a reset of the war.

## 4. Counterplay (what HOLD means, concretely)

Every stage has a distinct counter, in escalating cost order:

1. **Garrison it** (≥ `HOLD_THRESHOLD` ground units at the CP) — blocks
   eligibility outright; the passive, force-hungry answer.
2. **Kill the cell** (stage 1) — one CAS/Armed Recon tasking; aborts + cooldown.
3. **Kill the cache** (stage 2) — a strike; knocks the attempt back a stage.
4. **Strangle the source** — C1 cache strikes on the projecting stronghold drop
   its health below the projection gate; no new attempts can originate there.

## 5. Will coupling

A completed flip must drain BLUE will like a lost base — but a `finish_turn` flip
never appears in the debriefing's `bases_lost` (that count is built from in-mission
capture events), so the coin module records the flip in `coin_state` and the next
`update_political_will` consumes it as an explicit labeled move
(*"stronghold re-infiltrated x1"*) at the **`blue_base_lost` weight** (no new
weight — same currency as any base loss; the COIN campaign's `will:` block already
prices bases high). Stage messages ride the normal Information feed → the client
events panel and SITREP for free. No RED-side will effect (re-establishing costs
the insurgency nothing but time — historically honest).

## 6. Out of scope / never

- Expansion past the conservation bound (a *growing* insurgency is a different
  campaign premise; authored via campaign design if ever wanted).
- Any red auto-planner change (§17 stands; this is an economy/territory layer).
- Flipping carriers, off-map spawns, or any player-used field (hard-excluded).
- Runtime Lua. The cells fight in-mission as ordinary TGO units.

## 7. Implementation sketch (when the build slot opens)

Extends `game/fourteenth/coin.py` (~150 lines): an `advance_reinfiltration(game,
events)` called from `finish_turn` right after `regenerate_insurgent_cells`; a
`coin_reinfiltration` setting (default OFF, separate from `coin_insurgency` so C3
can stage the rollout; both preseeded by the campaign); TGO spawn through the §20
`place_unit_group` internals with `free=True` (terrain validation included);
`events` threaded from `finish_turn`'s existing parameter. Tests mirror C1's:
eligibility clauses (each gate independently), stage advance/abort/revert paths,
cooldown, conservation bound, the flip (real `capture` called, garrison
commissioned, C1 re-anchor at the weak cap), the will handoff record, and a
multi-turn "ignored three warnings" scenario.

**Build slot: after C3** (the campaign fork) — the timers/thresholds above need
tuning against real Shattered Dagger geometry, and until C3 exists nothing can
exercise a flip in play. Ship default-OFF regardless.

## 8. Open squadron calls (before the build, not blocking C2/C3)

1. `HOLD_THRESHOLD` = 4 ground units? (What a "token picket" is, is a feel call.)
2. Timers: 2 + 2 turns (≈4 turns of warnings) — right pace for a ~30-turn campaign?
3. One attempt theater-wide confirmed, or allow 2 concurrent on large maps?
4. Neutral-CP infiltration under the conservation bound confirmed (per §7.3's
   "neutral/lost" wording), or lost-ground-only for v1?
