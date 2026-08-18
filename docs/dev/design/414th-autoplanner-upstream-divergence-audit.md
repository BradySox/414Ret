# 414th auto-planner — upstream divergence audit

**Date:** 2026-08-09 · audit only, no code changed.
**Baseline:** upstream `dev` @ `1a669cac` (the merge base; upstream's 4 newer commits touch no `game/` code, so this equals current upstream).
Diffed all of `game/commander/`, `game/ato/`, doctrine, threat zones, procurement, settings, squadrons, and the aircraft `tasks:` data.
**Related:** [consolidation notes](414th-airwar-planner-consolidation-notes.md) · [rebalance rubric](../414th-aircraft-task-rebalance-rubric.md) · fork PR [#820](https://github.com/BradySox/414Ret/pull/820).

## Verdict

- The planner diverges substantially; almost all of it is deliberate and documented (§6 air-defense rework, §46 fuel, §69 SEAD windows, the rubric data, flown-failure fixes).
- 43 ungated changes fire in every default game; 10 setting gates ship ON; 212 of 224 changed aircraft yamls differ in task weights.
- The opt-in features (§17, §52, §44, QRA, minefields, air starts) are clean: parity at defaults.
- Three items look accidental — see **Needs a call** below.
- There is no single revert switch — see **Levers**.

## Ungated — differs in every default game

One line each. Ref = the flown/documented reason where one exists.

**Planning (commander)**
- U1 Front-anchor CPs always BARCAP'd; aggressiveness roll never abandons them, and is seeded per (turn, CP) (§6; Red Tide flew the lone anchor abandoned ~1 turn in 5).
- U2 BARCAP volume threat-weighted: up to +2 rounds at the hottest sector, fleet doubling kept, never below legacy (§6).
- U3 MODERN doctrine `strike_escort_reserve=8`: BARCAP trimmed + non-STRIKE escorts withheld to keep fighters for strike escorts (Marianas: 22-BARCAP/2-offensive ATO became 14/25). **Doctrine data — no setting.**
- U4 `PlanFrontLineCas`: CAS on every contested front, even when winning.
- U5 Common escorts drop SEAD_SWEEP (2 fewer jets per threatened package).
- U6 DEAD escorts: ESCORT + one SEAD flavor + jammer, not all three flavors.
- U7 DEAD reachability gate: a SAM shielded by another live ring is not optimistically cleared; dependent strikes wait.
- U8 Armed Recon fixed 4-ship (was 2–4 roll).
- U9 Strike floor 2-ship (no solo strikers).
- U10 Escort need tested vs fighter *engagement* reach, not the clamped orbit zone (front packages now get escorts).
- U11 TARCAP counts as A2A-escort capability (CAS proposes TARCAP).
- U12 Every AEW&C package is ASAP, paired with a 60 NM lateral spread — simultaneous AWACS, not chained relief. Uncommented.
- U13 Front-less theater: AEW&C anchors nearest the enemy, not farthest (flown: A-50 parked 424 NM out).
- U14 AEW&C squadron pick basing-aware (boat station → boat squadron; flown: E-2s double-tasked, E-3s idle).
- U15 One theater tanker per boom/probe method needed (never fewer than before).
- U16 Theater tankers repositioned post-planning onto actual receiver demand.
- U17 Red-only forward-middle BARCAP screen per active front on large maps (§6).
- U18 CSAR packages (≤2/turn, closest pilot first, never into a live ring) — pre-adoption of upstream #929, convergent.
- U19 §50 map-hidden ambush groups excluded from both planners.

**Scheduling**
- U20/U21 Land BARCAP: overlapping jittered waves; default 15 min overlap makes 2 rounds/CP where upstream plans 1 (0 restores upstream exactly).
- U22 §69: movable AI strikes retimed 2–10 min behind their covering SEAD/DEAD.
- U23 Same-boat recoveries spaced ≥5 min (flown midair 2.7 NM from the boat).
- U24 SEAD TOT −1 → −3 min. Under-documented.
- U25 Patrol legs cost `patrol_duration` in schedule sums (ETAs no longer collapse early).
- U26 Push time walks the real route incl. a pre-vul tanker stop.
- U27 §46 receiver dwell (`4×size+1` min) charged when departing a tanker — #820 exempts AI.
- U28 auto-ASAP checked before the DCA branch (enables U12).

**Routing / geometry**
- U29 Support orbits front-anchored, FLOT-parallel; AI sits 2.5× the buffer back, player 1× (§6; flown pathologies both directions).
- U30 Multi-orbit lateral spread (AWACS 60 NM same-target; tankers 40 NM coalition-wide).
- U31 Tanker tasking fuel-driven: pre-vul/post-vul/both/none per leg-costed route — replaces upstream's every-flight-tanks; pre-vul refuel is a waypoint class upstream never emits (§46).
- U32 §46 tank fitting before the tanker decision (`auto_range_fuel_tanks`, ON).
- U33 Package-tanker window skips tankers + incompatible receivers, opens early for pre-vul (also fixes an upstream `for self.flight` rebinding bug).
- U34 Racetrack laps charged to fuel (a CAP's on-station burn was missing everywhere).
- U35 Tanker fallback patrol speed from preferred altitude, not flat 400 kt.
- U36 CAP band no longer collapses/negative when the defended point is inside the threat zone (upstream bug).
- U37 BARCAP orbit biased up to 75% forward in the band by threat (0 threat = upstream).
- U38 DEAD/SEAD get per-unit TARGET_POINTs at default EXACT intel (APPROXIMATE = one fuzzed area point; no value reproduces upstream).
- U39 SEAD loiter: bounded `SEAD_LOITER` orbit (20 min cap or package-mate-gated); standoff 0.8× for everyone — non-ARM was 1.1×. Quiet default shift.
- U40 Armed Recon steerpoint pushed ≥5 NM off the garrison center (the #406 road sweep was tried and reverted).
- U41 Helo transit 500 ft AGL, was 200 (Red Tide M1 CFIT pattern).
- U42 10 NM FLOT hazard capsule in the navmesh (3× cost) — transits cross the front, not loiter over it.
- U43 Air assault: any `cabin_size > 0` fixed-wing may paradrop (§76, carve #884 open).

**Data + loadouts**
- 212 yamls rebalanced per the rubric; `Intercept` retired from 123 (2 misses below); `secondary_tasks` on 29 blocks auto-assign only.
- Fork lanes: TARPS 700 on 10 airframes, Escort Jammer on EA-18G/EA-6B, Jamming on the C-130J, CSAR on airlift helos (+code-derived for `cabin_size > 0` helos); heavy bombers stripped of ARMED_RECON.
- F-14B(U): upstream ships a byte-copy of the F-14B block; fork rebalanced it (+10 family bump, SEAD out, TARPS in) and fixed the `Retribution Fighter sweep` payload casing upstream still gets wrong (queued carve).
- Loadouts: ANTISHIP→Strike fallback (upstream flies clean), empty/`<CLEAN>` stations no longer invalidate a preset, Litening date-gated, `(XW)` fits mod-gated.
- Removed upstream surface: Pretense (flight type + planning state) and plannable INTERCEPTION (QRA reserve replaced it).

## Default-ON gates — one click back each

| Setting | Default | Upstream when |
|---|---|---|
| `barcap_overlap_time` | 15 min | 0 |
| `sead_strike_coordination` | ON | off |
| `auto_add_tarps_recon` | ON | off |
| `weather_aware_planning` | ON | off (no-op in clear skies) |
| `max_escort_jammers` | 4 | 0 (needs a Growler/Prowler anyway) |
| `csar_enabled(_red)` | ON | off (#929 brings it upstream anyway) |
| `adaptive_procurement` | ON | off |
| `auto_range_fuel_tanks` | ON | off (U31 stays either way) |
| `continuous_campaign_clock` | ON | off |
| `target_intel_precision` | EXACT | neither value matches upstream (U38) |

Era doctrine levers (Vietnam pair, COIN) are no-ops outside those campaigns — U3 is the one doctrine-data change that hits ordinary campaigns.

## PR #820

Exempts AI from the U27 dwell. Upstream has no dwell, so #820 moves AI timing *toward* upstream; no conflict with this audit.

## Needs a call

1. `F-14A-95-GR.yaml` missed the F-14 rebalance (still `Intercept: 520`, no TARPS); `F-100D.yaml` is the other Intercept miss.
2. U39: restore 1.1× for non-ARM SEAD, or document 0.8× as intended.
3. U24 (−3 min SEAD) and U12 (all-ASAP AWACS): document or revert.

## DECIDED 2026-08-09 — re-converge to upstream (DM call)

The DM's call, same day as the audit: **default planner behavior returns to upstream.**
"I do not care that it was deliberate then." Scope:

- **Defaults flip to upstream parity** (every default-ON gate ships OFF); one "414th
  planner suite" preset re-enables the kept features per campaign.
- **Keep only three groups** (argued and accepted): the 8 failure fixes, the feature
  plumbing (flight-type lanes, CSAR #929, §50 hide, Intercept retirement/QRA), and the
  3 data wrong-role fixes (bombers off Armed Recon, S-3B sea control, payload casing).
- **Everything else in §Ungated reverts to upstream behavior** — including the §6
  geometry/volume suite and §46 fuel-driven tanking, both **reverted outright** (not
  re-gated); rebuildable from git history if ever re-wanted.
- **The 212-file weight rebalance reverts to upstream numbers** except the kept
  wrong-role fixes and the fork-only task lanes; Intercept stays retired.
- **#820 sequencing:** stays valid and mergeable until the §46 revert deletes the
  receiver dwell entirely; then it closes as superseded.

Work orders: **A** defaults flip + preset · **B** small ungated commander reverts ·
**C** §46 revert · **D** §6 geometry revert · **E** data-layer weight restore.
Each lands as its own PR with its fork-behavior tests removed or retargeted.

### Amendment 2026-08-17 — U15 reinstated, ungated

**U15 (one theater tanker per boom/probe method needed) is back on by default.** Fresh DM call,
reversing work order B's revert of that one item. Nothing else in the decision above changes.

It came back up because upstream issue #243 asks for exactly this and has been open since 2024;
the fork was carrying the gap deliberately, not by inheritance, which was not obvious from the
code. Re-implemented in a different shape — the constraint is stated on `ProposedFlight` rather
than seeded as extra `refueling_targets` — so it is one package with two tankers, not two
packages. Details in the features doc.

The rest of the ungated reverts stay reverted. This amendment is the authority for U15 only; do
not read it as re-opening §6 or §46.

## Levers, if pulling back (superseded by the decision above; kept for the record)

1. "Stock planner" settings preset (the §28 preset machinery exists): flips the whole default-ON table above in one click. Can't touch the ungated items.
2. Revert MODERN `strike_escort_reserve` 8→0 — the highest-leverage ungated item, pure data.
3. Don't revert the flown-failure fixes (U13/U14, U23, U25, U34, U36, U40, U41) — each is pinned to a measured failure, several upstream-owed.
4. The big systems (§6, §46, rubric data) are the fork's identity — reverting is a product decision; carving them upstream post-freeze is the reviewability answer.

## Post-freeze carve additions from this audit

U36 CAP band bug · U33 tanker accounting · `<CLEAN>` payload validity · U10/U11 escort gates · U13/U14 AEW&C fixes · U23 recovery stagger · (already queued) the Fighter-sweep casing fix.
