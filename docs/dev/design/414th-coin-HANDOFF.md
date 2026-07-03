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

- **The 800-km carrier was idle** (user save 2026-07-03: "the auto planner never
  expected these distances"). The stock plane range gate (`Squadron.capable_of` vs
  `max_mission_range_planes`, default 150-200 NM) hard-rejects every carrier squadron
  at ~400-500 NM, so Hornets/A-6/E-2 never launched while the land air did the whole
  war. Two-part fix: (1) preseed `max_mission_range_planes: 600` so the carrier air is
  *assignable* to the wider war (the commander then flies the spare Hornets on SEAD);
  (2) `game/fourteenth/carrier_ops.py` + `long_range_carrier_ops` (default OFF,
  preseeded) frags ONE deterministic carrier package a turn from the boat's own
  squadrons -- a Hornet **STRIKE** section + an A-6E tanker + an E-2, pinned via
  `ProposedFlight.preferred_type` and forced through the gate with `ignore_range=True`
  via the engine's own `PackageFulfiller`. Two traps found: `EscortType.Refuel` is a
  dead end (`check_needed_escorts` never marks refuel "needed" -> the tanker always
  prunes), so the A-6 and E-2 ride as **primary** package flights, not escorts; and the
  hook must run in `Coalition.plan_missions` **before** `TheaterCommander` or the
  commander spends the Hornets on nearer SEAD first and leaves none for the package.
  Engine-probe verified: PKG -> target = Hornet Strike x2 + A-6E Refueling + E-2 AEW&C,
  all off the boat, valid flight plans + shared TOT.

- **Every COIN contact looked like a tank platoon on the planning map** (user 2026-07-03).
  The four COIN spawn types (C1.5 re-infiltration cells, roadside IEDs, HVT leaders, C4
  dispersed cells) all go through `spawn_red_ground_at` as `FRONT_LINE` vehicle groups, so
  once recon reveals them they rendered as the `VehicleGroupGroundObject` default -- hostile
  ARMOR. The map already draws real NATO APP-6(D) symbols client-side from a server SIDC
  (`game/sidc.py` -> milsymbol), so the fix is server-only, **no client change**: a new
  optional `TheaterGroundObject.sidc_entity_override` (a `(SymbolSet, Entity)` pair,
  `getattr`-guarded for old saves) that `sidc_for` honors ahead of the class default.
  `spawn_red_ground_at` takes a `sidc_override=` and the callers pass one of three shipped
  constants in `coin.py` -- `CELL_SIDC` (Land Unit / **Infantry** 121100, used for cells +
  dispersed cells), `IED_SIDC` (Activity / **IED** 110300), `HVT_SIDC` (Dismounted Individual
  / **individual-leader** 110220). Entity codes verified against milsymbol's own APP-6(D)
  render tables (`src/numbersidc/sidc/*.js`). Ammo caches were already correct
  (`AMMUNITION_CACHE`). Two follow-ons landed the same day:
  - **The standing garrisons too, not just the discrete spawns.** `symbol_insurgent_garrisons`
    (`coin.py`, run each turn incl. turn 0 from `regenerate_insurgent_cells`) sets `CELL_SIDC`
    on every insurgent-held CP's militia TGO -- scoped by *composition* (a non-cache TGO whose
    units all pass the C1 `_revival_eligible` whitelist), which cleanly leaves the radar-SAM
    crust + EWRs alone (their launchers/radars fail the whitelist), skips caches, and never
    re-points a discrete spawn (already has an override). So a whole COIN stronghold reads as
    an insurgency, not an armor park.
  - **Suspect until reconned.** A viewer-aware `TheaterGroundObject.standard_identity_for(viewer)`
    (the fog-layer sibling of `sidc_status_for`) renders an insurgent contact carrying an
    override that the human hasn't discovered as **SUSPECT** (yellow), flipping to **HOSTILE**
    once TARPS/strike confirms it. Rides `known_for` (so the recon-fog setting + reveal-overview
    toggle both collapse it to confirmed), gated on `coin_insurgency` so no other campaign's map
    changes, and ground truth (`viewer=None`: AI/planner) is never fogged.
  Guarded by `tests/theater/test_theatergroundobject.py` (the real `sidc_for` serialization
  path, the suspect-until-reconned identity, the old-save fallback) + `tests/fourteenth/test_coin.py`
  (the garrison pass: militia symboled, SAM/cache/blue/discrete-spawn left alone). Both
  render-verified in the pinned milsymbol 3.0.4.

## After P1

- **Tune** from ledger data (levers above), update the P1 row status.
- **C1.5 build** (re-infiltration): spec is complete in its note; 4 open squadron
  calls in its §8 (hold threshold, 2+2 timers, one-attempt cap, neutral scope) —
  answer them from P1 feel, then build against real geometry.
- **C4** (dispersed cells via `place_unit_group`): optional texture; only if the
  played campaign feels too static between stronghold fights.
