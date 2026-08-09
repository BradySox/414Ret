# 414th auto-planner — upstream divergence audit

**Status:** audit complete, no code changed · **Date:** 2026-08-09
**Baseline:** upstream `dcs-retribution/dev` @ `1a669cac` (2026-08-01, the current merge base).
Upstream has moved 4 commits since; none touch `game/` code, so this baseline equals
current upstream `dev` for every file below.
**Trigger:** the concern that the auto-planner has strayed too far from upstream behavior.
**Related:** [414th-airwar-planner-consolidation-notes.md](414th-airwar-planner-consolidation-notes.md),
[414th-aircraft-task-rebalance-rubric.md](../414th-aircraft-task-rebalance-rubric.md),
[414th-air-defense-planning-notes.md](414th-air-defense-planning-notes.md),
fork PR [#820](https://github.com/BradySox/414Ret/pull/820) (open; §7 below).

## 1. Method

- Diffed every planner-area file against the merge base: `game/commander/` (30 files,
  +1,607/−126), `game/ato/` (54 files, +3,426/−506), plus `coalition.py`, `game.py`,
  `procurement.py`, `data/doctrine.py`, `threatzones.py`, `transfers.py`, `settings/`,
  `squadrons/`, and the aircraft data layer (`resources/units/aircraft/`).
- Every behavioral change was classified by its gate: **ungated** (fires in every
  default game), **default-ON setting**, **opt-in setting** (parity at defaults),
  **doctrine/campaign data** (era campaigns only), or **bug fix**.
- The audit question, per the standing rule ("audit = also diff vs upstream"): with all
  414th toggles at their defaults, where does the planner still behave differently from
  upstream — and is each such difference deliberate, documented, and wanted?

## 2. The short answer

- The planner diverges from upstream **substantially, and most of it is deliberate and
  documented** — §6 (air-defense rework), §46 (fuel planning), §69 (SEAD windows), the
  task-rebalance rubric, and a set of flown-failure fixes account for nearly all of it.
- **The divergence is NOT one thing to revert.** It is ~40 independent changes in five
  layers. About half are ungated; the rest sit behind settings that ship ON.
- **Out of the box, the biggest visible deltas vs upstream:** BARCAP force structure
  (2 rounds/CP vs upstream's 1, 4 vs 2 on fleets, +threat weighting, +forward CAP line,
  −escort-reserve trim), support-orbit placement (front-anchored vs target-anchored),
  tanker behavior (fuel-driven vs always-tank), DEAD/SEAD shape (per-unit waypoints,
  restructured escorts, −3 min TOT, closer loiter), and the aircraft task-weight data
  (212 yamls differ).
- **Three items look accidental or under-documented** and deserve a call (§8): the
  F-14A-95-GR/F-100D rebalance misses, the SEAD non-ARM loiter standoff (1.1×→0.8×,
  closer to the SAM), and the SEAD −3 min TOT offset.
- There is **no single switch** that restores upstream planner behavior. §9 lists the
  practical levers, including a settings preset that would get ~70% of the way back.

## 3. Ungated divergences — differ in every default game

### 3.1 What gets planned (the commander)

| # | Change | Upstream | Fork | Why |
|---|---|---|---|---|
| U1 | Forward defensive CAP line | A CP is BARCAP-worthy only if an enemy airfield is within `airbase_threat_range` | A CP that anchors an active front is always defended; the OPFOR aggressiveness roll can never abandon a front anchor; the roll is seeded per (turn, CP) instead of re-rolled per call | §6; Red Tide flew the sole front anchor abandoned ~1 turn in 5 |
| U2 | Threat-weighted BARCAP volume | Flat: 1× rounds, 2× on fleets | `AirspaceGeometry.barcap_rounds`: additive threat bonus up to +2 rounds at the hottest sector; fleet doubling retained; never below the legacy baseline | §6 |
| U3 | Strike-escort reserve (MODERN doctrine) | No reserve | `strike_escort_reserve=8` in MODERN doctrine data: BARCAP demand trimmed at least-threatened CPs, and non-STRIKE packages may not dip the fighter pool below the reserve | Marianas probe: 26-package ATO was 22 BARCAP / 2 offensive; with the reserve, 14 BARCAP / 25 offensive |
| U4 | CAS on winning fronts | CAS only reachable inside `CaptureBase`; a side winning the ground war set an aggressive stance and fragged no CAS | `PlanFrontLineCas` plans CAS on every still-contested front after `CaptureBases` | Decouples CAS from the capture decision |
| U5 | Common escort mix | Threatened packages propose SEAD_ESCORT + ESCORT + SEAD_SWEEP | SEAD_SWEEP dropped from the common set (kept where proposed directly, e.g. CAS); jammer added when a capable airframe exists | "Overstuffed package" fix, generalized from upstream's own PlanDead comment |
| U6 | DEAD escort mix | `propose_common_escorts()` (all three SEAD flavors) | ESCORT + exactly one SEAD flavor (SEAD if the target still radiates, else SEAD_ESCORT) + jammer | Same rationale |
| U7 | DEAD reachability gate | Planned DEAD optimistically clears the SAM, unblocking dependent strikes | A DEAD whose route crosses another live radar-SAM ring does not clear its target; dependent strikes stay deferred; the package is not re-planned every pass | Stops tasking strikers into a live belt |
| U8 | Armed Recon size | 2–4 ship weighted roll | Fixed 4-ship | "414th call" (documented in code) |
| U9 | Strike size floor | 1-ship strikes possible on 1–2 unit targets | 2-ship minimum | No solo strikers; mutual support |
| U10 | Escort need test | Route threat tested against the defensively-clamped BARCAP *orbit* zone | Tested against the uncapped fighter *engagement* zone (`waypoints_threatened_by_aircraft_engagement`) | Packages near the front now get the A2A escort the orbit-zone test missed |
| U11 | A2A escort capability | Wing must plan ESCORT | ESCORT or TARCAP counts (CAS proposes its A2A escort as TARCAP) | Gate/proposal mismatch fix |
| U12 | AEW&C ASAP | Only the first AWACS package (none airborne yet) is ASAP | Every AEW&C package is ASAP (`asap = self.asap`); pairs with the new lateral spread so simultaneous AWACS separate by 60 NM | Uncommented in the diff — see §8 |
| U13 | AEW&C anchor, no-front theater | Land anchor is the CP farthest from threats — on a front-less theater the A-50 parked 424 NM from the war | With no front, anchor at the friendly CP nearest the enemy | Flown finding, 2026-07-17 |
| U14 | AEW&C squadron pick | Generic base-to-target distance ranking | Carrier station → that boat's own squadron; land station → nearest land AWACS squadron | Flown finding: both E-2s double-tasked while two E-3s sat idle |
| U15 | Theater tanker seeding | One tanker at the closest friendly CP | One tanker per distinct boom/probe method the receiver fleet needs (never fewer than before); squadron pick filters by method | Mixed boom+probe fleets were half-unsupported |
| U16 | Theater tanker placement | Planned blind to receivers | Post-planning pass moves each theater tanker onto the strongest cluster of compatible receiver demand | `tankerdemand.py` |
| U17 | Red forward-middle BARCAP | Not present | On large maps (rear CP farther from the FLOT than `cap_max_distance_from_cp`), red adds one forward-middle BARCAP screen per active front | §6, red side only |
| U18 | CSAR | Not present at this baseline | Downed pilots accumulate; up to `max_csar_flights`(2)/turn rescue packages, closest-first, never into a live SAM ring | Pre-adoption of upstream PR #929 — convergent with upstream's own future |
| U19 | Battle positions | All live vehicle groups targetable | Map-hidden groups (§50 ambush teams) excluded from both sides' planners | Feature-internal; no effect unless §50 content exists |

### 3.2 Scheduling — when packages fly

| # | Change | Upstream | Fork | Why |
|---|---|---|---|---|
| U20 | Land BARCAP schedule | Back-to-back waves, first wave at mission start | Overlapping waves (`barcap_overlap_time`, default 15 min) with a jittered first wave; `0` restores upstream exactly | §6; attackers could wait out the deterministic front-loaded CAP |
| U21 | BARCAP round count | `ceil(mission/barcap)` = 1 round at defaults | `ceil(mission/(barcap−overlap))` = 2 rounds at defaults | Follows from U20 |
| U22 | SEAD windows (§69) | Packages timed independently; a strike could push 30 min before its SEAD | Movable AI strikes retimed into the window 2–10 min behind the latest covering SEAD/DEAD TOT (`sead_strike_coordination`, default ON) | §69 |
| U23 | Carrier recovery spacing | None | Same-boat recoveries spaced ≥5 min; only movable AI packages shift | Flown midair 2.7 NM from the boat, 2026-07-16 |
| U24 | SEAD TOT offset | −1 min vs package | −3 min | Under-documented — see §8 |
| U25 | Patrol leg schedule | `patrol_start→patrol_end` costed at straight-line flight time in per-leg sums | Costed at `patrol_duration` | Later-waypoint ETAs collapsed early otherwise |
| U26 | Formation push time | Hold→join costed as one straight line | Walks the real route edges, including a pre-vul tanker stop | Pairs with U31 |
| U27 | Receiver tanker dwell | No dwell concept | Legs departing a REFUEL waypoint charge `4×size+1` min (§46) | PR #820 (open) exempts AI — see §7 |
| U28 | Scheduler branch order | DCA branch tested before auto-ASAP | auto-ASAP tested first | Enables U12; the AEWC chain branch is now effectively dead |

### 3.3 Routing and geometry — where flights go

| # | Change | Upstream | Fork | Why |
|---|---|---|---|---|
| U29 | Support-orbit anchor | AWACS/tanker racetrack anchored on the package target, stepped toward the nearest threat boundary | Front-anchored, FLOT-parallel (`support_orbit_anchor`); carrier stations hold with the boat; AI orbits sit 2.5× the buffer back, player 1× | §6; flown pathologies both directions (E-2 27 NM from an enemy Tomcat ramp; A-50 326 NM behind the front) |
| U30 | Multi-orbit spread | Stacked | AWACS sharing a target spread 60 NM laterally; all tankers coalition-wide spread 40 NM | No-op with one orbit |
| U31 | Tanker tasking | Every non-helo formation-attack/escort flight gets a refuel waypoint whenever the wing can plan REFUELING | Fuel-driven: the route is costed leg-by-leg; the flight tanks pre-vul, post-vul, both, or not at all (`refueltasking.py`); pre-vul refuel is a waypoint class upstream never emits | §46. Most flights upstream sent to a tanker now don't go |
| U32 | Sortie tank fitting | Not present | Empty tank-capable stations filled (jammer pods traded for bags) before the tanker decision (`auto_range_fuel_tanks`, default ON) | §46 |
| U33 | Package-tanker window | `5 + Σ(4×size+1)` over every package flight, tankers and incompatible receivers included; also a latent `for self.flight in ...` rebinding bug | Skips tankers and boom/probe-incompatible receivers; opens early for pre-vul receivers; extends to still cover post-vul | Upstream-owed fix candidate |
| U34 | Patrol fuel accounting | Racetrack laps not charged (straight-line only) | On-station burn charged at patrol speed × duration | Most of a CAP's gas was missing from every fuel consumer |
| U35 | Tanker fallback patrol speed | Flat 400 kt | `preferred_patrol_speed(preferred_patrol_altitude)` | Consistency with orbit altitude |
| U36 | CAP band under pressure | Orbit band collapses (can go negative) when the defended point sits inside the enemy threat zone — racetrack lands behind the point | Falls back to the full doctrine band | Genuine upstream bug — carve candidate |
| U37 | BARCAP forward bias | Uniform placement in the band | Lower bound raised by threat × 0.75 of the band; at threat 0, byte-identical to upstream | §6 volume/placement pairing |
| U38 | DEAD/SEAD target waypoints | One area waypoint | One `TARGET_POINT` per live unit at the default `EXACT` intel precision (`APPROXIMATE` gives one fuzzed area waypoint — neither value reproduces upstream exactly) | TOO designation |
| U39 | SEAD loiter | `NAV` waypoint, unbounded search; standoff 0.8× threat range with an ARM, 1.1× without | `SEAD_LOITER` waypoint with a bounded orbit (`loiter_end_time`: gated by package-mates' departure, else 20 min); standoff `sead_loiter_standoff_factor` = 0.8 for everyone | The non-ARM 1.1→0.8 change is a quiet default shift — see §8 |
| U40 | Armed Recon steerpoint | On the target CP center (over the garrison's SHORAD) | Pushed back ≥5 NM (threat range + 2 NM, clamped) | Flown finding; the #406 road-polyline sweep was tried and reverted 2026-07-05 |
| U41 | Helo cruise altitude | 200 ft AGL (combat altitude reused for transit) | 500 ft AGL transit legs (`heli_cruise_alt_agl`) | Red Tide M1 helo CFIT pattern |
| U42 | FLOT routing hazard | None | 10 NM capsule along each active front added to `ThreatZones.all`; navmesh penalizes (3× cost) crossing it | Transiting flights cross the FLOT perpendicular instead of loitering over the ground battle |
| U43 | Air assault eligibility | Helo or Anubis Hercules only | Helo or any `cabin_size > 0` fixed-wing (paradrop, §76); ingress geometry unified | §76; upstream carve #884 open |

### 3.4 Who flies it — the data layer

- **212 of 224 changed aircraft yamls** differ from upstream in `tasks:` or
  `secondary_tasks:`. This is the task-rebalance rubric + the S-3B/A-6E pass + the
  `Intercept` retirement, all documented in the rubric note.
- **`Intercept` deleted from 123 yamls** (QRA reserve replaced it as the intercept
  model). Two files were missed — see §8.
- **`secondary_tasks:` exists on 29 yamls** (0 upstream): blocks auto-assignment
  while keeping manual fragging (bombers off Armed Recon, pure fighters off mud).
- **Fork-only task lanes:** TARPS at 700 on 10 airframes (F-14 family, Mirage F1CT,
  MQ-9, RQ-1, RA-5C, RF-101), Escort Jammer on EA-18G (800) / EA-6B (790), Jamming on
  the C-130J-30 (140), explicit CSAR on 8 airlift airframes plus a code-derived CSAR
  lane for every helo with `cabin_size > 0`.
- **Heavy bombers** (6 DCS ids) have ARMED_RECON stripped in code; mod bombers get the
  weaker `secondary_tasks` treatment.
- **F-14B(U):** upstream ships its `tasks:` as a byte-copy of the F-14B block. The fork
  rebalanced it onto the family shape (+10 over the F-14B, SEAD removed, TARPS added).
  Upstream's F-14B(U)/F-14A-95 payload files also name a preset `"Retribution Fighter
  Sweep"` that their loader never matches (casing) — the fork's data fixes the casing,
  so those jets fly a real sweep loadout here and a fallback upstream. Already on the
  post-freeze carve list.

### 3.5 Loadout selection

- ANTISHIP falls back to Strike (upstream: no fallback — a jet without an anti-ship
  preset flew clean).
- A payload with an empty/`<CLEAN>` station is valid (upstream: the whole preset was
  silently skipped and a fallback flown).
- Litening pod availability date-gated for F-16 (2005) / Hornet (2003) with fallback
  substitution.
- `(XW)` expanded-weapons fits tried first, selected only while the mod's pylons are
  injected (§71).
- New fallback chains for the fork task lanes (ESCORT_JAMMER→SEAD Escort,
  JAMMING→Transport, TARPS→BARCAP).

### 3.6 Removed upstream planner surface

- **Pretense** is gone: `FlightType.PRETENSE_CARGO`, `pretensecargo.py`, and the
  pretense planning state (deliberate, 2026-06; re-run the removal runbook after
  upstream pulls).
- **INTERCEPTION** is no longer plannable (save-compat value retained); the QRA
  squadron reserve + Moose dispatcher replaced it (§1).

## 4. Default-ON setting gates — one click back each

| Setting | Default | Restores upstream when |
|---|---|---|
| `barcap_overlap_time` | 15 min | 0 (byte-identical schedule, wave count, and jitter) |
| `sead_strike_coordination` | ON | off |
| `auto_add_tarps_recon` | ON | off (also naturally off in wings with no TARPS airframe) |
| `weather_aware_planning` | ON | off (no-op in clear skies anyway) |
| `max_escort_jammers` | 4 | 0 (also naturally off without an EA-18G/EA-6B squadron) |
| `csar_enabled` / `csar_enabled_red` | ON | off (note: upstream #929 will bring this to upstream anyway) |
| `adaptive_procurement` | ON | off (uniform ground-unit rolls return) |
| `auto_range_fuel_tanks` | ON | off (stops §46 tank fitting; the fuel-driven tanker decision U31 stays) |
| `continuous_campaign_clock` | ON | off (per-turn time rotation + memoryless weather return) |
| `target_intel_precision` | EXACT | no value reproduces upstream for DEAD/SEAD (U38) |

## 5. Opt-in gates — parity at defaults

`ownfor/opfor_planner_unpredictability` (0, §17) · `c2_decapitation_effects` (off, §52)
· `long_range_carrier_ops` (off, §44) · `opfor_air_start` / `support_air_start` (off) ·
QRA reserves (`*_default_qra_reserve` 0, §1) · player QRA manning (0) ·
`auto_plan_minefields` (off, §57 shelved) · `min_patrol_altitude` (0) ·
`enable_package_code_words` (off) · manual flight timing (player action) ·
per-airframe loadout/flight defaults (§43/§73, user data).

These are clean: at defaults the planner is byte-identical to the fork's own no-feature
path, and tests pin several of them.

## 6. Doctrine/campaign-gated — era campaigns only

The Vietnam pair and COIN doctrines carry the era levers (tasking whitelist, display
renames, `strike_through_air_defense_threat`, `plan_strikes_without_full_escort`,
Alpha Strike fan `strike_flight_count=4`, `always_escort_strikes`, `gci_ambush`,
`strike_escort_reserve=4`, `escort_support_aircraft=False`, 500 ft low-level attack
profile, knife-fight A2A ranges, the infantry/artillery ground OOB). All are no-ops for
every faction on MODERN/COLDWAR/WWII doctrine — **except** U3 above: the
`strike_escort_reserve=8` on MODERN itself is the one doctrine-data change that fires
in ordinary campaigns.

## 7. PR #820

[#820](https://github.com/BradySox/414Ret/pull/820) edits `FlightPlan.refuel_duration`
(U27): AI flights stop being charged the §46 receiver dwell they never fly. Upstream
has no dwell at all, so **merging #820 moves AI timing back toward upstream** — the
dwell remains only for player flights, where it models real time on the boom. This
audit and #820 do not conflict; nothing here re-touches that property. If §46's dwell
were ever removed wholesale (not recommended — it is the fix for players arriving late
to their own join), #820 is subsumed.

## 8. Findings — likely accidents and under-documented calls

1. **`F-14A-95-GR.yaml` missed the F-14 family rebalance.** It still carries
   `Intercept: 520`, has no `TARPS`, and none of the family weight moves — its only
   change is the `SEAD` removal. Every other F-14 got the full treatment. Looks like a
   miss, not a call.
2. **`F-100D.yaml` still carries `Intercept: 280`** — the other survivor of the
   123-file Intercept retirement. Same shape: a miss.
3. **SEAD non-ARM loiter standoff quietly moved from 1.1× to 0.8× threat range** (U39).
   The settings-ization kept only the ARM value as the default for everyone, so a
   SEAD flight without an ARM now loiters *inside* the range it used to stand off
   from. No design note records this as intended.
4. **SEAD TOT offset −1 → −3 min** (U24). Plausibly deliberate (more suppression lead
   ahead of the §69 window), but no comment or note says so.
5. **`asap = self.asap`** (U12) has no comment. The paired lateral-spread code implies
   simultaneous AWACS is the design, but the change that makes them simultaneous is
   uncredited. Worth one comment or a revert decision.
6. **`packagerefueling` receiver accounting** (U33) silently fixed an upstream bug
   (`for self.flight in ...` rebinding). Fine to keep; belongs on the carve list so
   upstream gets it too.

## 9. Re-convergence levers, if wanted

Ranked by how much upstream behavior each restores per unit of loss:

1. **A "stock planner" settings preset** (the §28 preset machinery already exists):
   overlap 0, SEAD coordination off, TARPS auto-add off, weather off, jammers 0,
   adaptive procurement off, range tanks off, continuous clock off. Gets the
   *scheduling and support* layers back to upstream in one click. Cannot touch the
   ungated geometry/doctrine items (U1–U19, U29–U43, U3).
2. **Doctrine data:** revert `MODERN_DOCTRINE.strike_escort_reserve` 8→0 if the
   Marianas-style escort famine is judged rarer than the BARCAP thinning it costs.
   This is the single highest-leverage ungated item, and it is data, not code.
3. **Decide the §8 items** — two yaml misses (trivial), the SEAD standoff/TOT numbers
   (either document them as intended or restore 1.1×/−1), and the ASAP comment.
4. **Do not revert the flown-failure fixes** (U13/U14, U23, U36, U40, U41, U25/U34,
   loadout validity): each is pinned to a measured in-game failure, and several are
   upstream-owed.
5. **The big intentional systems** (§6 geometry/volume, §46 fuel, the rubric data)
   are the fork's identity. Reverting them is a product decision, not a cleanup; if
   the concern is reviewability rather than behavior, the better move is carving them
   upstream after the freeze (several are already queued).

## 10. Post-freeze upstream carve candidates surfaced by this audit

Additions to the existing queue (all bug-fix class, small, self-contained):

- CAP orbit band collapse under pressure (U36).
- Package-tanker receiver accounting + rebinding bug (U33).
- Payload validity: empty/`<CLEAN>` stations (loadouts).
- Escort-need engagement-zone test (U10) and the ESCORT/TARCAP gate mismatch (U11).
- AEW&C front-less anchor + basing-aware squadron pick (U13/U14).
- Carrier recovery stagger (U23).
- Already queued: the `Retribution Fighter sweep` payload casing fix.
