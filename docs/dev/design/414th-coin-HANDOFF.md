# 414th — COIN line HANDOFF (next-session pickup)

**Written 2026-07-02** at the end of the session that built the whole line. Start here;
the specs of record are `414th-coin-insurgent-replenishment-notes.md` (the model) and
`414th-coin-reinfiltration-notes.md` (the C1.5 design). Will-profile machinery:
`414th-will-generalization-notes.md`.

## Where the line stands (all merged to main 2026-07-02)

| Slice | PR | State |
|---|---|---|
| Will profiles + warship feed (the enabler) | #417 | ✅ merged |
| C1 — regen core (`game/fourteenth/coin.py`) | #419 | ✅ merged |
| C1.5 — re-infiltration **design** | #421 | ✅ merged (design only) |
| C2 — `red_cache_lost` will feed | #423 | ✅ merged |
| C3 — **Operation Enduring Resolve (COIN)** campaign + the TGO revival channel | #424 | ✅ merged |
| **P1 in-game pass** | — | ☐ **THE NEXT STEP** (checklist P1) |
| C4 — dispersed harassment cells (§20 placement machinery) | — | design-only, optional texture |
| C1.5 — re-infiltration **build** | — | slotted **after P1 tuning** |

## The next step is a cockpit, not a keyboard

Everything headless is done and CI-locked (engine probe verified regen/revival, the
cache throttle to the 0.25 floor, profile + arc resolution on the real campaign;
1407 tests green). **Fly checklist P1**: new campaign *"Afghanistan - Operation
Enduring Resolve (COIN)"*, 5+ turns. The experiment that proves the loop:

1. Strike one stronghold's **cells** without touching its caches → recon it 2 turns
   later → the cells are back (and the map lied to you until the recon — that's
   `alive_at_last_recon` working, not a bug).
2. Kill both its **caches** → the same stronghold stops refilling (floor trickle).
3. Watch the will message: mandate vs momentum, cache kills as labeled
   "ammo caches xN destroyed" movers. The **will ledger** (meter hover / SITREP
   movers) is the tuning instrument.

## The tuning levers (in expected order of need)

- **Pace of the insurgency**: `REGEN_BASE_UNITS_PER_TURN` (2.0) and
  `CACHE_HEALTH_FLOOR` (0.25) in `game/fourteenth/coin.py`.
- **The will economy**: the campaign's own `will: weights:` block in
  `resources/campaigns/coin_enduring_resolve.yaml` — no code change. Current COIN
  inversion: `red_cache_lost` 4.0, `red_ground_unit_lost` 0.05,
  `blue_passive_regen` 0.0, `blue_roe_violation` 6.0, bases 5.0 both sides.
- **Cache density**: the laydown table in `tools/build_coin_enduring_resolve_miz.py`
  (re-run it; **never hand-edit the miz**).
- **Arc pacing**: `phases:` min_turns (10/20) + `advance_when` thresholds (45/25).

## Gotchas discovered building it (don't relearn these)

- **This laydown has NO front lines** ⇒ `Base.armor` is empty everywhere; the
  insurgent force lives in the vehicle-group TGOs. That's why `coin.py` has TWO
  channels (garrison commission, then **TGO revival** toward `tgo_cap`). Any future
  COIN laydown with real ground routes exercises the garrison channel instead.
- The insurgent **technicals are class IFV** in the unit data — the whitelist is
  class set + **price ≤ 10**; the ceiling (not the class) is what excludes BMPs/Grads.
- **Bost never instantiates as a CP** (neutral field) — the population-center ring is
  **coordinate-anchored** (`x:`/`y:`), not `center:`-named.
- **A ROE ring must guard something** (user catch 2026-07-02: "the population centres
  are empty of objectives — why would we ever go there?"). The empty Herat ring was
  CUT; then the second user catch ("the horror of COIN is EVERYTHING is restricted")
  became **THE LATTICE**: the laydown turns out to have placed the strongholds ON the
  real towns (FOB Jackson = Sangin at 0 km, ANP Hill = Now Zad, Zeebrugge = Kajaki,
  Delaram II = Delaram, Tarinkot = Tarin Kowt — real lat/lons converted via pydcs),
  so **9 permanent population-center rings** (a YAML anchor, one list) cover them +
  Lashkar Gah/Gereshk/Musa Qala/Marjah. Census on the generated game: **26 red TGOs
  AI-legal / 26 in-ring player-only; 15 caches clean / 13 in-town** — the AI keeps a
  full desert war, the towns are the player's judgment. `blue_roe_violation` dropped
  **6.0 → 1.0** to match: CDE pressure per kill, not scandal (clearing Sangin costs
  real mandate but is survivable once; a carpet habit bleeds out). Geronimo's caches
  split Lashkar Gah/Marjah; the 611 corridor (ANP Hill → Musa Qala → Sangin) and the
  Helmand highway leg (Geronimo → Lashkar Gah → Gereshk → Kajaki) thread the rings.
- Never `locked_targets: [ammo]` in the arc — the caches must always be legal.
- **Toyota Al Gaib 2001 was missing most of the insurgent kit** (user catch 2026-07-02,
  fixed): the DIM' technicals, the §41 ERO ZU-23 family + preset group, and the SA-9
  now match the sibling insurgent factions (still no armor by design). The campaign
  preseeds `high_digit_sams` so the ERO units resolve.
- The ratline needed three fixes to actually run here (user catch 2026-07-02: "the
  ROE page talks about supplies on the trail but there is no supply lines"): the
  laydown had **zero CP connectivity** (now 8 authored red↔red `supply_routes:`
  corridors in the YAML — never red↔blue, that would create a front),
  `_pick_trail_corridor` **required front lines** (now falls back to orienting
  toward the opposing CPs when front-less), and every stronghold's `Base.armor` was
  **empty** so there was nothing to skim (now `coin_insurgency`-gated rear seeding:
  the source is topped up to 2× a convoy load with whitelisted kit — the
  external-support framing — so the skim ships a full column and leaves a stable
  rear buffer). Engine-probe verified: turn 1 ships Martello → Frontenac.

- **The OEF air package** (user direction 2026-07-03): fixed wing + air defenses.
  Two schema traps cost time: (1) campaign-YAML **preset squadrons are requested via
  the `aircraft:` list** (the WRL `VF-142` pattern) — the `name:` field only *renames*
  whatever got found, so `name: 322 Squadron` + `aircraft: [F-16CM...]` silently
  renames a random Viper preset; (2) the squadron-def loader **drops foreign-country
  presets unless the faction country is a "Combined Joint Task Forces"** — hence the
  new `OEF Coalition 2006` faction (usa_2005 roster, CJTF Blue country) so the RNLAF
  322 Squadron / RAF IV (AC) Squadron presets (new files) survive, and hence the
  US-preset pins on the Kiowa/tanker/Apache slots (CJTF otherwise casts any nation
  — the Tunisian Kiowa / Israeli Apache incidents). The **off-map air-spawn base was
  dropped 2026-07-03** (user: "get rid of the air spawn base"): the CENTAF heavies
  (F-15Es, B-1s, KC-135s) now home-base at **Kandahar** (the long runway takes them)
  instead of a floating F-15C off-map sentinel. The Hornets fly from a **REAL carrier
  in the Gulf of Oman** (user-proven positions from two editor mizzes — Retribution's
  Afghanistan landmap has no sea polys, so `is_in_sea` says no, but the carrier CP
  comes straight from the miz Stennis sentinel and DCS owns the water; the
  generator names the boat from the faction pool, e.g. CVN-72). The user also drew
  the **safe transit corridor** (two lines, recorded in the build tool): carrier
  cycles run it straight north to the AO (~780 km — the real OEF cycle, bracketed
  by the CENTAF tankers). Red AD: AAA markers at all 13
  strongholds + SHORAD at 7, and (user direction) a **light radar-SAM crust** —
  MERAD markers at Farah/Tarinkot/Frontenac fill from the faction's new SA-2/SA-3/
  SA-6 presets (probe drew a Kub battery at Farah, an S-125 at Tarinkot), with
  SA-8/13/15 joining the SHORAD pool. **None inside the town rings** — the SEAD/
  DEAD game this opens must stay AI-playable (an in-ring radar SAM would be
  DEAD-blocked forever). Turn-2 ATO confirms SEAD Sweep/Escort tasking. The Navy
  tanks itself: **VA-165 A-6E buddy tankers** on the boat (the `A-6E Tanker`
  variant, probe/drogue) cover the Hornets' cycle; CENTAF KC-135s cover the
  boom receivers.
- **Adding that AD deadlocked the whole strike planner** (the Vietnam P3 deadlock,
  re-found empirically: turn-2 census showed **0 AI-legal targets outside red
  threat, 51 inside**, ATO = helos only): the gun/IR envelopes blanket every
  objective, no SEAD/DEAD target exists to clear them, and modern doctrine refuses
  to strike into threat. Fix = the new **`COIN_DOCTRINE`** (faction key `"coin"`,
  `game/data/doctrine.py`): modern + `strike_through_air_defense_threat` +
  `plan_strikes_without_full_escort` — realistic vs guns/MANPADS-only enemies, and
  the OEF faction binds it. Verified: the turn-2 ATO fills with BAI from every
  fast-air squadron.

## After P1

- **Tune** from ledger data (levers above), update the P1 row status.
- **C1.5 build** (re-infiltration): spec is complete in its note; 4 open squadron
  calls in its §8 (hold threshold, 2+2 timers, one-attempt cap, neutral scope) —
  answer them from P1 feel, then build against real geometry.
- **C4** (dispersed cells via `place_unit_group`): optional texture; only if the
  played campaign feels too static between stronghold fights.
