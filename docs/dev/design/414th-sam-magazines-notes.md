# Cross-turn SAM magazines — scoping note

Status: **scoping only, nothing built.** Written 2026-08-20, out of the MIST author's repository
assessment (`414th-mist-author-repos-notes.md` §4, owed-work item 3). Every claim about
our own code below was verified against the tree on the branch this note landed on.

## 1. The problem

A DCS mission is a fresh spawn, so every SAM site starts every turn with full tubes. Saturating
a site achieves nothing that survives the debrief: the campaign has no ammunition dimension for
ground air defense. This is the same defect §81 fixed for the fleet ("a fleet re-dumps a full
magazine every turn") — the naval magazines note records it as the third of the three facts
that motivated §81. Ships got a magazine; SAM sites did not.

What a magazine buys, campaign-side:

- Saturation becomes a strategy. Emptying an S-300 battalion is worth something even when no
  launcher dies.
- SEAD gets a second currency. A site that survived the HARMs but spent its stock is degraded
  in a way the campaign now remembers.
- Supply becomes targetable in a new way. Missiles arriving along the §90 supply lines give
  interdiction and depot strikes (§56) a concrete air-defense payoff.

## 2. Prior art

**In-house — §81 naval magazines** (`game/fourteenth/naval_magazines.py`,
`resources/plugins/navalmagazines/navalmagazines-config.lua`,
`game/missiongenerator/navalmagazineluadata.py`). The proven architecture, and the one this
feature copies:

- Persisted per-group stock, lazily seeded at first sight, keyed by `TheaterGroup.group_name`
  (the stable `"<id> | <name>"` string that survives regeneration).
- Stock emitted into the mission as this mission's hard cap.
- The plugin counts real `S_EVENT_SHOT` releases and clamps ROE when a group reaches its cap.
- Expenditure mirrors to a debrief channel (`naval_magazines_state`); Python debits at the turn
  boundary in `missionresultsprocessor.py`. **Generation never debits** — regenerating a
  mission is free (the §54/§63 lesson).
- Four-test pattern to mirror: `tests/fourteenth/test_naval_magazines.py`,
  `tests/missiongenerator/test_navalmagazineluadata.py`, `tests/test_missionresultsprocessor.py`,
  `tests/lua/test_navalmagazines_runtime.py`.

**External — the MIST author's `script_iads_dev.lua`** (read-only; unlicensed, so ideas and DCS facts
only, never code). His `rearm` setting names the design space: `sim` (DCS-native rearm from
placed logistics), `auto` (spawn warehouses to feed it), `infinite`, and `virtual` — which his
own comment marks "N/A currently". The mode he stubbed is exactly the one a campaign layer can
do and a mission script cannot: a persistent ledger across missions. That is the fork's edge
here. His per-launcher `missiles` counts (S-300 TEL 4, Buk TELAR 4, Kub 3, Hawk 3, Tor 8,
Osa 6…) are DCS facts we re-derive from our own export path, not values we copy.

## 3. DCS reality — what forces the shape

1. **You cannot spawn a ground unit with partial ammo.** Neither the mission format nor
   scripting exposes it (no `setAmmo`). So a site that starts the turn with 2 missiles left
   must be *clamped by script* after it has fired 2 — the ledger is enforced virtually, exactly
   as §81 does for ships.
2. **`S_EVENT_SHOT` fires for SAM launches** and the weapon's `getDesc().missileCategory` is
   `2` for a SAM (verified in the author's runtime dump: the SA-11's 9M38M1 reports
   `missileCategory = 2`). That gives the counter a **category filter instead of a name-pattern
   list** — cleaner than §63/§81's pattern lists and disjoint from both by construction
   (anti-ship is category 4, cruise is 5). The §81 "never add a land-attack family" constraint
   has no analog here to get wrong.
3. **DCS natively rearms launchers from nearby logistics.** the script's `warehouseDef` names the
   providers (Ural-375, GAZ-66, M 818, warehouses, ammo depots) — and §85 put exactly these
   cargo trucks inside our S-300-family sites. So in a long mission a launcher beside its §85
   trucks may physically reload. The clamp makes this harmless: fired-count is compared against
   the *campaign* stock, so a physical reload past the ledger just meets the ROE hold sooner.
4. **The clamp must be ROE, never emissions.** Hard constraint (the `enableEmission` crash);
   that script independently reaches the same conclusion (zero `enableEmission` calls).

## 4. The MANTIS seam — verified clean

The worry was that MANTIS would un-clamp a dry site when it wakes it. Verified against the
bundled `Moose.lua`: in our configuration (`useEmOnOff = false`,
`resources/plugins/mantisiads/mantis-config.lua`), MANTIS start state and every wake/sleep
transition touch **only** `OptionAlarmStateGreen/Red` and `OptionEngageRange` — ROE is never
set anywhere in the MANTIS class body or the SEAD evasion path. So:

- A dry site on `WEAPON_HOLD` still cycles alarm states under MANTIS — **it still radiates when
  cued, still draws SEAD, still looks dangerous. It just cannot shoot.** That is the right
  semantics (winchester, not dead) and it costs the IADS's deterrent face nothing.
- The §77 growler plugin already drives ground SAM ROE (`AI.Option.Ground.id.ROE` hold/restore
  pulses), so the mechanism is proven in-tree. One interaction rule: the magazine clamp is a
  **one-way latch per mission** (dry stays dry), so §77's *restore* pulse must never lift it —
  the growler restore re-asserts OPEN_FIRE; the magazine plugin must re-assert HOLD on a short
  timer for dry groups, the same defensive re-assert the harness pins elsewhere.

`WEAPON_HOLD`, not §81's `ReturnFire`: for ships ReturnFire keeps the SAM umbrella up, which is
the point of that choice. For a ground launcher group ReturnFire would *fire missiles* when
shot at — leaking the very stock the ledger says is spent. Site AAA lives in separate DCS
groups in our templates (the `S-300 Site AAA-0` origin group, MANTIS point-defense sets), so
holding the launcher group does not silence the guns.

## 5. The off-mission drain — the make-or-break piece

Most packages resolve off-screen (§26). If only flown missions drain magazines, red's belt
never drains except where the player personally flies, and the feature reads as fake. This was
the open question going in; the resolver turns out to hand us the hook:
`DefendingSam.resolve()` (`game/sim/combat/defendingsam.py`) holds
`self.air_defenses: list[TheaterGroundObject]` — the exact engaging sites — at the moment an
abstract SAM engagement resolves. The rule:

- Each engaging site with stock debits **K missiles per resolved abstract engagement**
  (default K=2, a doctrinal two-missile engagement; crude, documented as such).
- A site at stock 0 is excluded from `iter_threatening_sams`
  (`game/sim/combat/samengagementzones.py`) — it cannot kill you, so it no longer triggers or
  weights abstract combat. This is ground truth, not fog: the site genuinely cannot engage.
  Flying over a dry belt becoming safe **is the feature working**.

Planner threat rings stay unchanged in v1 (a dry site still repels routing). Two reasons: the
blue auto-planner must not act on enemy stock the player cannot see (§3's auto-target rule —
`fogofwar.hidden_from`, the same host-vs-player consistency argument), and red planning on its
own known stock is fine but not worth the coupling yet. Deferred, recorded in §9.

## 6. Sizing

`capacity = Σ over alive launcher units (tubes[unit_type_id]) × reserve_factor`, computed at
first sight like §81's `_group_capacity`.

- **The tubes table is the launcher filter.** Radars, C2, §85 trucks and power stations are
  simply absent from it and contribute 0. ~20 vanilla launcher ids to author (S-300 TEL 4,
  SA-11 TELAR 4, SA-6 TEL 3, SA-3 4, SA-2 1, Hawk 3, Patriot 4, SA-8 6, Tor 8, …) plus the HDS
  and CH launchers the fork fields; `DEFAULT_TUBES = 4` for anything unlisted. Values come from
  our own export data (`tools/verify_mod_export.py` / pydcs `getAmmo`), cross-checkable against
  the author's dump for vanilla — sourced facts, not copied tables.
- **`reserve_factor` default 2.0** (ready load + one reload set at the site), a setting.
  Balance number, not TO&E — the §81 stance, said in the docstring the same way.
- Per-system overrides only if a flown test shows a system needs one.

## 7. Resupply — what makes it a campaign feature

§81 ships no-rearm and that is right for ships (a port call is out of scope). For SAM belts it
would be wrong: over a 30-turn campaign, no-rearm decays red's IADS monotonically — a snowball,
not a fight. Options considered:

| Option | Shape | Verdict |
|---|---|---|
| A — supply-gated trickle | +R missiles/turn toward capacity (R default = one launcher's tubes) while the site's CP is supply-connected; a cut line (§90 rung A's connectivity) stops it | **Recommended v1.** Small, legible, makes interdiction matter |
| B — procurement-funded | refills spend the coalition's §68 budget, riding the SAM-repair pipeline | Good v2 — priced missiles compete with aircraft, a real decision. More coupling |
| C — explicit resupply convoys | §50-style convoys physically deliver | Too deep. A convoy ambush already has its own feature; do not fuse them |

A dead site's ledger entry orphans harmlessly (§81 behavior). §68 repair restores *units*, not
missiles; a repaired launcher raises capacity at the next seed only if the group was never
seeded — otherwise stock stays as the ledger says, which is correct (repair welds metal, it
does not conjure missiles; the trickle refills).

## 8. Proposed v1 scope

Symmetric (blue Hawks drain like red S-300s — the upstreamable standard), default OFF, both
gates preseeded where a campaign wants it (§36 lesson: plugin toggle + setting).

1. `game/fourteenth/sam_magazines.py` — ledger, seeding, capacity, reconcile (≈ §81's 285
   lines).
2. `game/missiongenerator/sammagazineluadata.py` — emit `dcsRetribution.samMagazines`.
3. `resources/plugins/sammagazines/` — plugin.json + config.lua: count `missileCategory == 2`
   shots per emitted group, latch `WEAPON_HOLD` at the cap with a re-assert timer, mirror
   `{group=, fired=}` into `sam_magazines_state`; announce winchester to the owning coalition.
4. One line in `resources/plugins/base/dcs_retribution.lua`'s state serializer; parse in
   `debriefing.py`; reconcile call in `missionresultsprocessor.py` beside §81's.
5. §26 hook: K-per-engagement debit in `DefendingSam.resolve`, stock-0 exclusion in
   `SamEngagementZones`.
6. Resupply option A.
7. Surfaces: friendly stock rows in the ground-object dialog (§81's `tgo_magazines` pattern,
   caller owns the friendly-side gate — enemy stock is never a click away), SITREP winchester
   lines, a What's New entry (§92).
8. Registry entry in `game/fourteenth/features.py` (CI-enforced), settings page, docs faces,
   in-game-pass rows.

Explicitly deferred: planner awareness of stock (both sides), option B economy coupling,
missile-depot TGOs, per-system reserve overrides, §89 pre-roll expenditure (pre-rolled
packages' abstract engagements already route through §26 — verify in the pass, don't build).

Tests: mirror the §81 quartet (model / luadata / resultsprocessor / lupa runtime). Lupa pins:
the category filter, the per-mission latch (never un-clamps, including against a §77 restore
pulse), the debrief mirror shape, and the untracked-group no-op.

In-game pass rows (new B-series): a stock-2 site fires exactly 2 then holds with radar still
cycling under MANTIS; §85-truck native reload does not defeat the clamp; winchester announce;
next-turn stock reflects the debrief.

## 9. Open questions

| # | Question | Leaning |
|---|---|---|
| 1 | v1 rearm: option A trickle, or ship §81-style no-rearm first and add A in a follow-up? | A in v1 — no-rearm SAM belts snowball (see §7) |
| 2 | K (abstract-engagement debit) and R (trickle rate) defaults | K=2, R=one launcher's tubes; tune on the first campaign flown with it |
| 3 | Does the AI SAM actually stop at WEAPON_HOLD mid-engagement, or finish its salvo? | In-game pass question; §81 tolerates overshoot (`overshootFired`) — mirror that |
| 4 | Should a dry LORAD still contribute *detection* to MANTIS? | Yes — radar up is the point; no change needed, MANTIS detection rides EWR/alarm, not ROE |
