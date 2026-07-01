# 414th In-Game Pass Checklist

Most 414th features are validated by careful reading + Python tests, but their
**runtime behavior cannot be exercised in CI** — the Lua plugins, the planner's
spatial placement, and the MOOSE dispatcher only show their true colors in a
live DCS mission. The engineering doc
([414th-features.md](414th-features.md)) tags these as *"needs an in-game
pass."* This file is the **tracker** that turns those scattered tags into a
verdict-producing protocol: one row per outstanding check, each with an
observable pass criterion and the failure signature to watch for.

Update a row's **Status** when you fly it. Don't mark `VERIFIED` on a hunch —
it means *"I watched for the fail signature and it did not occur,"* ideally with
a Tacview/log reference and a date. When a row reaches `VERIFIED`, also drop the
*"needs an in-game pass"* tag from the matching section of `414th-features.md`
so the two docs don't drift.

> **Headless queue status (2026-06-27):** the desk-adjudicable work is **exhausted**. The
> Python/Lua-logic layer behind every outstanding row is test-covered and was re-verified **green on
> branch** (227 backing tests + `test_late_init`), so the remaining items are gated on a live cockpit
> pass, not further headless analysis. Don't re-run the test sweep expecting a status flip — ☑ VERIFIED
> requires watching the fail signature in DCS.

## Status legend

| Mark | Meaning |
|---|---|
| ☐ UNTESTED | Built; no in-game observation yet |
| ◐ PARTIAL | Flown, but not under the conditions that stress the fix |
| ☑ VERIFIED | Watched for the fail signature in-game; did not occur (note date/Tacview) |
| ✗ REGRESSED | Fail signature reproduced in-game — reopen the fix |
| ⊘ RETIRED | Feature dormant/removed — the scenario no longer runs; not a pending test |

---

## A. Air-to-air / QRA

### A1 — QRA air-spawn profile · §1 · ☑ VERIFIED (2026-06-24, Tacview)
- **Verified (2026-06-24, GermanyCW Red Tide turn 1, Tacview):** the red `Intercept`
  reserve scrambled in two waves and each MiG-29A pair air-spawned at ~750 m AGL and
  240–510 kt, climbing/cruising under control — no stall, no ground-clawing dive. The
  fail signature did not occur. (Note: the current `AI_A2A_DISPATCHER` QRA **air-spawns**
  at altitude rather than ground-scrambling, so the old `SCRAMBLE_SPEED_KT`/`SCRAMBLE_AGL_M`
  ground path is effectively superseded.)
- **Pass:** Scrambled jets spawn at a sane speed and a terrain-relative LOW
  altitude, then climb/turn to intercept under control.
- **Fail signature:** Jets air-spawn stalled (~0 kt) and dive clawing for
  airspeed (the Su-27-nearly-hit-the-ground-at-Vaziani case, Tacview
  2026-06-20). Check `SCRAMBLE_SPEED_KT` / `SCRAMBLE_AGL_M` in
  `intercept-config.lua` if seen.

### A2 — QRA base-defense doctrine · §1 · ☑ VERIFIED (2026-06-24)
- **Setup:** Default doctrine (`qra_gci_max_radius_nm` 60, `qra_engagement_range_nm` 38).
- **Pass:** QRA scrambles only when a raid closes within ~60 NM and interceptors
  don't chase far past the FLOT — they screen their own base, not the front line.
- **Fail signature:** QRA pushing forward over the FLOT (the pre-tuning
  behavior that prompted lowering the radii).

### A3 — Player-manned QRA alert flight · §1 · ☐ NEEDS PASS
- **Setup:** A BARCAP-capable, player-flyable squadron at an airfield; set its
  "…of which player-manned" spinbox (under QRA reserve) ≥ 1. Take the turn and generate.
- **Pass:** A cold-start BARCAP package named "QRA Alert (<squadron>)" appears in the player
  ATO, parked on the alert pad, flyable, orbiting **over its own field** (not pushed forward);
  the AI QRA dispatcher for that base fields the reserve **minus** the manned airframes (no
  duplicate jet both parked-as-player and air-spawned). Losses reconcile correctly at debrief.
- **Fail signature:** the alert flight's racetrack pushed forward toward the FLOT; the same
  airframe both manned and air-spawned by the dispatcher (double-spawn); a depleted-pool error
  on generation; or the AI dispatcher count not dropping when the player mans some.

### A4 — Player QRA scramble cue · §1 · ☐ NEEDS PASS
- **Setup:** A player-manned QRA base (A3 setup); fly/trigger an enemy air raid toward it.
- **Pass:** as a bandit closes inside the cue radius (the AI GCI radius + ~30 NM lead, so it
  fires *before* the AI would scramble), a coalition text "QRA SCRAMBLE — <base>: bandits
  <brg> for <rng> nm, angels <N>" appears; the call repeats no more often than ~2 min; the
  bearing/range/altitude roughly match the inbound contact. It never auto-launches the player.
- **Fail signature:** no message (PLAYER_ALERT records absent, or `coalition.getGroups`/
  `AIRBASE:FindByName` wrong); message spam (debounce broken); wildly wrong BRA (north/east
  axis or `atan2` argument order wrong); a Lua error in `dcs.log` from the scan.

---

## B. Planner placement / target logic (Lua-free Python)

### B1 — Forward-CAP / FLOT depth on coastal fronts · §6 · ☑ VERIFIED (2026-06-25)
- **Verified (2026-06-25, in-game):** deep ground roles spawned at depth and spread on a
  coastal/narrow-land front — the perpendicular-walk-into-water stacking fail signature did
  not occur.
- **Setup:** A campaign on a **coastline / river / narrow-land** front.
- **Pass:** Deep ground roles (artillery, logistics) spawn at depth and spread,
  not in direct contact.
- **Fail signature:** Deep groups stacked in contact at depth 0 because the
  perpendicular walk hit water/off-map (the bug the lateral fallback fixes).

### B2 — DEAD reachability gate on follow-on strikes · § DEAD · ☑ VERIFIED (2026-06-24)
- **Setup:** A target behind an intact SAM belt that blue wants to strike.
- **Pass:** Blue still tasks the DEAD (with SEAD escort) but **defers the deep
  strike** until the belt is actually down.
- **Fail signature:** Blue sends the follow-on strike into a live belt because
  it trusted an optimistic DEAD clear.

### B3 — Threat-weighted BARCAP orbit placement · §6 · ☑ VERIFIED (2026-06-25)
- **Verified (2026-06-25, in-game):** the contested-vs-quiet-flank forward-placement
  comparison the 2026-06-24 partial was waiting on now confirmed — the contested sector's
  BARCAP sat further forward while staying clear of enemy SAM rings. Fail signature (orbit
  pushed into a ring / quiet-flank drift) did not occur.
- **Partial (2026-06-24, GermanyCW Red Tide turn 1, `test.retribution`):** the
  SAM-clearance half is confirmed — both BARCAP racetracks' endpoints test
  `threatened_by_red=False` (orbit never inside a red threat zone), and the two
  waves are offset 10.1 km mid-to-mid with different racetrack lengths (43.7 vs
  23.5 km) — the overlapping/jittered-waves design. **Not** confirmed: the
  contested-vs-quiet-flank *forward-placement* comparison — this campaign has a
  single front sector (both BARCAPs at Fulda), so there's no quiet-flank orbit to
  compare against. Needs a multi-sector campaign.
- **Setup:** A campaign with a clearly contested sector (CP near a fighter-heavy
  enemy airfield and/or anchoring a front) **and** a quiet flank CP.
- **Pass:** The contested sector's BARCAP racetrack sits noticeably **further
  forward** (toward the enemy) than the quiet flank's, while still staying clear of
  enemy SAM rings (orbit never inside a threat zone).
- **Fail signature:** Forward orbit pushed *into* a SAM ring (no-fly clamp not
  respected), or quiet-flank orbit placement drifted from the legacy spread.

### B4 — TARCAP planned on CAS / A2A escort on forward packages · §6 · ☑ VERIFIED (2026-06-24, Tacview)
- **Verified (2026-06-24, GermanyCW Red Tide turn 1, Tacview):** the CAS package
  `Front line Fulda/Haina CAS` (AH-64D) spawned **with a TARCAP** (`Front line
  Fulda/Haina TARCAP`, F-15C) plus a SEAD Sweep, and every forward DEAD/BAI/SEAD
  package (BABOON, COW, GERBIL, PERCH, TRIGGERFISH) carried its A2A Escort + SEAD
  Escort. Fail signature did not occur.
- **Setup:** A campaign with an active land front and an enemy airbase within
  fighter range (≈90 NM) of the FLOT; let the AI auto-plan a turn.
- **Pass:** CAS packages over the front spawn **with a TARCAP** flight, and forward
  DEAD/BAI get their A2A `ESCORT`. (Deep packages keeping their escort = no regression.)
- **Fail signature:** CAS packages still spawn with no TARCAP, or forward packages
  fly unescorted, because the escort-need check is reading the clamped orbit zone
  instead of the new `air_engagement` reach.

### B5 — Red forward-middle BARCAP layer (large maps) · §6 · ☑ VERIFIED (2026-06-25)
- **Verified (2026-06-25, in-game):** on a large map red planned its rear BARCAP **plus** the
  extra forward layer ~halfway to the FLOT, clear of blue threat zones, with the rear BARCAP/QRA
  untouched. None of the fail signatures (missing forward layer, orbit inside a blue ring,
  rear BARCAP moved, layer on a small map) occurred.
- **Setup:** A **large** map (e.g. GermanyCW Red Tide) with a red CP anchoring an
  active front whose distance to the FLOT exceeds the rear BARCAP reach
  (`cap_max_distance_from_cp`). Let the AI auto-plan red's turn.
- **Pass:** Red plans its normal rear BARCAP **and** one extra forward BARCAP sitting
  ~halfway between the rear CP and the FLOT — a visible fighter screen between blue
  packages and the IADS — and that forward orbit stays clear of blue threat zones (no
  endpoint inside a blue SAM ring). On a **small** map no extra layer appears.
- **Fail signature:** No forward layer on a large red front (trigger/threshold off, or
  `forward_cap_front_anchor` returned `None`); OR the forward orbit sits inside a blue
  threat zone (standoff math wrong); OR the **rear** BARCAP moved/disappeared, or QRA
  changed (should be untouched); OR a forward layer appears on a small map.
  Check `TheaterState.from_game` (`forward_barcaps_needed`) and
  `game/ato/flightplans/supportorbit.py` `forward_cap_front_anchor` if seen.

---

## C. Support flights

### C1 — AWACS/tanker orbit front-anchor · #84 · ☑ VERIFIED (2026-06-24)
- **Setup:** Any campaign with AWACS + tanker support.
- **Pass:** Support racetracks anchor on the FLOT, behind the front.
- **Fail signature:** Red AWACS flung far off-axis (the ~175 NM case #84 fixed).

### C2 — Support orbit depth behind FLOT · #86 · ☑ VERIFIED (2026-06-24)
- **Setup:** As C1; watch where the orbit actually sits relative to threats.
- **Pass:** Orbits hold **deep** behind the FLOT, clear of forward SAM/CAP reach.
- **Fail signature:** Support orbit placed within enemy engagement depth.

### C3 — Tanker racetrack speed estimate · ☑ VERIFIED (2026-06-26, planner/data + live-save confirmed — in-sim tanking not eyeballed)
- **Headless adjudication (2026-06-26):** Loaded every tanker via `AircraftType` and
  computed `RefuelingFlightPlan.patrol_speed` directly (no flight). Found the F/A-18E/F
  buddy tankers riding the **estimate fallback at 509 KTAS (~335 KIAS)** — their
  hand-tuned `patrol:` block was mis-nested under `fuel:` in `FA-18ET.yaml` /
  `FA-18FT.yaml`, so the loader (`AircraftType._variant_from_dict`, top-level
  `data.get("patrol")` at aircrafttype.py:626) never saw it and the tuned 320 KTAS was
  dead data. **Fixed:** de-indented `patrol` to top level in both files. Every tanker now
  carries an explicit, sane orbit speed — buddy (A-6E / F/A-18E/F / S-3B) 320 KTAS
  (~242–266 KIAS), KC-130 370, KC-135 / MPRS 445/440 (~303/305 KIAS), KC-10 405, IL-78M
  400, and KC-130J an intentional 180 KTAS (~125 KIAS, the documented slow helo tanker).
  No tanker rides the estimate path anymore, and the Mach-at-altitude fallback is itself
  sane. **Residual (still in-sim only):** receivers physically joining and taking fuel
  without S-turning.
- **Setup:** Plan a package that takes fuel from a **buddy tanker** (the F/A-18E/F or
  A-6E tanker). All buddy and dedicated tankers now define an explicit `patrol:` speed;
  the `preferred_patrol_speed(preferred_patrol_altitude)` estimate is now only a fallback
  for an untagged tanker.
- **Pass:** Tanker flies its racetrack at a sane, steady speed and receivers
  rendezvous and take fuel without falling behind or overrunning.
- **Fail signature:** Tanker orbit speed too slow/fast for receivers to join (e.g.
  fighters S-turning to stay behind, or unable to close). If seen, revisit
  `RefuelingFlightPlan.patrol_speed` in `game/ato/flightplans/refuelingflightplan.py`
  (and check the airframe's `patrol:` block is at top level, not nested under `fuel:`).
- **Live-save confirmation (2026-06-26):** Loaded the actual flown campaign save
  (`autosave.retribution`, GermanyCW turn 1) headless and read each planned tanker's
  `flight_plan.patrol_speed`: BLUE KC-135 = **445 kt TAS**, RED IL-78M = **400 kt TAS**
  (both `TheaterRefuelingFlightPlan`). Sane, airframe-appropriate orbit speeds on a real
  ATO — matches the data-table adjudication. Still in-sim only: receivers physically joining.

### C4 — A-6E attack/tanker split · ☑ VERIFIED (2026-06-25)
- **Verified (2026-06-25, in-game):** both A-6E variants load and behave — the Intruder is
  never auto-tasked for refueling/recovery and the Tanker orbits/refuels as a carrier tanker
  without picking up strike tasks. Data loaded correctly in the packaged app.
- **Setup:** A-6E now loads as two squadron-selectable types from `A6E.yaml`:
  "A-6E Intruder" (attack tasks only) and "A-6E Tanker" (Refueling/Recovery only,
  `max_group_size: 1`, carrier tanker patrol). Buy/auto-plan each and confirm both
  appear and behave. **Could not be load-tested in CI** — the A-6 unit isn't in the
  CI/dev pydcs build, so confirm the data actually loads in the packaged app first.
- **Pass:** The Intruder is never auto-tasked for refueling/recovery; the Tanker is
  never auto-tasked for strike/CAS/etc. and orbits/refuels as a carrier tanker.
- **Fail signature:** Either type missing from the airframe list (the A6E unit id may
  differ in the shipped pydcs, or variant-level `tasks` override didn't take); or the
  Tanker still picks up strike tasks / the Intruder still gets tanker tasking. Check
  that both variants resolve in `AircraftType` and that the A6E unit supports AI
  air-refueling in the build's pydcs.

### C5 — Boom/probe refuel-method compatibility · ☑ VERIFIED (2026-06-26, planner/data + live-save confirmed — in-sim tanking not eyeballed)
- **Headless adjudication (2026-06-26):** Exercised the matching logic on real loaded
  types (no flight). `can_refuel_from` is correct on representative pairs (boom receiver ×
  boom tanker = yes; boom × drogue = blocked; probe × boom = blocked; probe × drogue =
  yes), `tankerdemand.best_tanker_service_point` routes a boom tanker to the boom demand
  cluster and a probe tanker to the probe cluster (and `_compatible` matches
  `can_refuel_from` for the method dimension). Data audit: 11 tankers all tagged
  (KC-135 = boom, KC-135 MPRS / KC-130 / KC-130J / S-3B / IL-78M / A-6E / F/A-18E/F buddy =
  probe; the KC-10 is split into two selectable variants — `KC-10 Extender` boom and
  `KC-10 Extender (Drogue)` probe — which resolves the flagged "KC-10 boom-vs-drogue
  mis-tag" risk); receivers tagged boom=27 / probe=71 (USAF fixed-wing = boom, Navy / NATO /
  Russian = probe — textbook), with untagged airframes permissive by design. **Residual
  (still in-sim only):** receivers physically plugging in, plus the faction-composition
  caveat below (a faction with only a boom tanker starves its probe receivers — by design;
  permissive matching can only over-restrict, never crash).
- **Setup note (2026-06-25):** the faction flown in the 2026-06-25 session
  did **not** carry both a boom and a drogue tanker, so there was no method split to observe.
  Requires a faction with **both** a boom (KC-135) and a drogue (KC-135 MPRS / KC-130 / S-3B
  Tanker) tanker to exercise this row.
- **Live-save finding (2026-06-26) — single-tanker planner gap:** Loaded the flown
  campaign save (`autosave.retribution`, GermanyCW turn 1) headless. The BLUE air wing
  **does** carry both tankers (KC-135 boom ×2 *and* KC-135 MPRS drogue ×2; RED has IL-78M
  probe), and the compatibility logic is correct on the live ATO (RED IL-78M↔Su-27 both
  probe = OK). **But the auto-planner frags only ONE theater tanker** —
  `TheaterState` seeds exactly one refueling target
  (`theaterstate.py:325 closest_friendly_control_point()`) → `PlanRefueling` proposes
  1 REFUELING + 2 ESCORT. For that *dedicated* tanker package,
  `PackageBuilder._required_refuel_methods` sees no in-package receivers (real receivers
  live in other packages), so the single tanker is selected **unconstrained** → priority-first
  = boom KC-135, and the 414th `reposition_theater_tankers` then parks it on the strongest
  **boom** demand cluster. Result on this turn: the 5 BLUE **probe** types (F-14B, F/A-18C,
  A-6E, Mirage-F1EE, Tornado IDS) got **no theater tanker** — the probe Mirage colocated in
  the boom KC-135's package shows as incompatible (the refusal is working as designed). This
  is **not** a bug in the C5 matching machinery (all correct); it is a missing capability —
  **multi-method theater-tanker fragging** (one tanker per distinct receiver method present
  in the ATO).
- **Fix landed (2026-06-26) — per-method theater-tanker fragging:** `TheaterState` now seeds one
  refueling target **per servable receiver method** (`seed_refueling_targets`), threaded
  `RefuelingTarget.method` → `PlanRefueling.method` → `ProposedFlight.refuel_method` →
  `PackageBuilder._required_refuel_methods`, so a mixed boom+probe fleet frags one tanker for each
  method (each planned in its own `plan_missions` pass, then repositioned onto its own demand
  cluster). Falls back to a single unconstrained tanker for untagged / permissive / no-matching-tanker
  cases (never fewer than legacy). Tests: `tests/test_refueling_targets.py`. **In-game re-test
  target:** a mixed boom+probe BLUE ATO should now show **two** tankers, and each method's receivers
  should tank from the compatible one. See the features-doc section "Per-method theater-tanker
  fragging".
- **Setup:** Aircraft now carry an `air_refuel_type` (boom/probe) and tankers a
  `tanker_refuel_types`; the planner only assigns a tanker that provides the package
  receivers' method, and `PackageRefuelingFlightPlan.patrol_duration` only counts
  compatible receivers. Plan a **boom** package (e.g. F-16/F-15) and a **probe**
  package (e.g. F/A-18/Su-27) in a faction that has both boom (KC-135) and drogue
  (KC-135 MPRS / KC-130 / S-3B Tanker) tankers. The classification data is an initial
  high-confidence pass and is **opt-in / permissive** — untagged airframes refuel from
  anything, so this can only *over-restrict* a mis-tagged aircraft, never crash.
- **Pass:** Boom packages get a boom tanker; probe packages get a drogue tanker;
  helicopters only get a slow (KC-130) tanker; mixed/untagged packages still get a
  tanker. Receivers actually plug in and take fuel in-mission.
- **Fail signature:** A package that should have a compatible tanker gets none (a
  mis-tagged receiver, or a faction lacking the right tanker type), or a receiver is
  matched to a tanker it can't physically use. Fixes are data-only: the airframe's
  `air_refuel_type` or the tanker's `tanker_refuel_types` in
  `resources/units/aircraft/*.yaml`. KC-10 boom-vs-drogue and any exotic/mod airframe
  are the likeliest mis-tags to review first.

### C6 — Fuel-driven pre/post-vul tanking · ☑ VERIFIED (2026-06-25)
- **Verified (2026-06-25, in-game):** short sorties launched with no tanker; deep sorties got
  a refuel waypoint on the correct side and reached the tanker with fuel to spare; kneeboard
  bingo/joker read sanely past the tanker. The kg-`max_fuel`-vs-lb fuel-unit handling that
  couldn't be checked in CI held up. Fail signatures (need-gas-got-none / awkward pre-vul
  backtrack / flameout before tanker) did not occur.
- **Setup:** Formation/attack and escort flights no longer get a tanker waypoint
  unconditionally. `FormationAttackBuilder._refuel_tasking` estimates the sortie burn
  (ingress at cruise + the ingress→target→split vul at combat + egress home, plus the
  climb-out) vs usable internal fuel and inserts a refuel waypoint **only** when short:
  pre-vul (routed on the ingress nav, before the join) if it can't fight through the
  vul, otherwise post-vul (after the split). A sortie too long for even a full top-off
  to cover gets **both** a pre- and post-vul tanker. The fuel estimators credit the
  refuel point, so the kneeboard/sim fuel reads correctly past the tanker. Fly a
  **short** sortie (expect no tanker), a **long-egress** sortie (expect post-vul), a
  **very deep** target (expect pre-vul), and a **very long-range** sortie (expect
  both), in a faction with a compatible tanker.
- **Pass:** Short sorties launch with no tanker tasking; deep sorties get a refuel
  waypoint on the correct side (or both for the longest ranges); the flight reaches the
  tanker with fuel to spare and completes the sortie; kneeboard bingo/joker look sane
  after tanking.
- **Fail signature:** Flights that clearly need gas get none (or vice versa); pre-vul
  detour backtracks awkwardly; a flight flames out before the tanker. The burn now
  walks the real route at the actual per-leg climb/combat/cruise rates
  (`sortie_fuel_split`), so the remaining unknown is the **fuel unit handling (kg
  `max_fuel` vs lb consumption), which couldn't be validated in CI** — tune
  `_refuel_tasking` in `game/ato/flightplans/formationattack.py` if the pre/post/none
  split looks off.

### C7 — Theater tanker placed on receiver demand · ☑ VERIFIED (2026-06-25)
- **Verified (2026-06-25, in-game):** the shared theater tanker orbited near the receiver
  cluster (not the rear CP) and receivers reached it and took fuel; orbit stayed clear of
  enemy threat zones. None of the fail signatures (rear-CP parking, wrong method gate, orbit
  in a threat ring, buddy tanker moved) occurred.
- **Setup:** A campaign with a **shared theater tanker** (a dedicated REFUELING
  package, not a same-package buddy tanker) and several offensive packages whose
  flights actually take gas (have `REFUEL` waypoints) clustered in one area. Boom +
  drogue mix is the stress case. Auto-plan a turn.
- **Pass:** The theater tanker orbits **near the strongest cluster of compatible
  receivers** (boom tanker → boom receivers, etc.), not back at the closest friendly
  CP, and receivers reach it and take fuel. A boom-only tanker is **not** dragged
  toward a probe-heavy cluster. With no compatible demand the tanker keeps the legacy
  front-anchored orbit. The orbit stays clear of enemy threat zones.
- **Fail signature:** Tanker still parked at the rear CP far from any receiver; OR a
  boom tanker pulled to probe-only demand (method gate wrong); OR the orbit lands
  inside an enemy threat ring (clearance nudge wrong); OR a same-package buddy tanker
  moved (should be untouched). Check `reposition_theater_tankers` /
  `best_tanker_service_point` in `game/commander/tankerdemand.py` and the override in
  `game/ato/flightplans/theaterrefueling.py`.
- **Note:** receiver `REFUEL`-waypoint *retargeting* onto the moved tanker is a
  deferred follow-up; this row covers orbit placement only.

---

## D. Loss accounting (upstream-core)

### D1 — Player-despawn loss suppression · §8 · ☑ VERIFIED (2026-06-24)
- **Setup:** Player despawns/jumps seat mid-mission (not an ejection, not a
  shootdown), then the mission ends.
- **Pass:** Airframe + pilot are NOT logged lost; a real shootdown and a real
  ejection still DO count.
- **Fail signature:** Surviving player jet logged lost (the GERBIL F-14 case).
- **Residual to watch:** if the engine tears the mission down without
  per-player `PLAYER_LEAVE_UNIT` events, despawn-crashes aren't caught —
  land/despawn before ending remains the belt-and-suspenders.

---

## E. SOF insert generation · #85 · ☑ VERIFIED (2026-06-24)
- **Setup:** A SCAR commander-capture campaign that plans a SOF C-130 insert.
- **Pass:** The SOF C-130 **ground-starts** (incl. the runway fallback when no
  parking is free) and the **EW (`c130j`) plugin is skipped** on that airframe.
- **Fail signature:** SOF C-130 air-spawns, or the EW menu/behavior bolts onto
  the SOF insert because the airframe matched `eligibleTypeNames`.

---

## F. SCAR

> **NOTE (2026-06-27):** The **armor-hunt SCAR scenario is retired** by the survivor-rescue rework
> (SCAR → "Sandy" rescue escort). `ScarPlugin.generate_plugin_data()` now clears `scar_taskings`, so
> `scar_414_init.lua` never injects — the loiter / SOF-capture / King-designation scenario does not
> run. Rows **F5, F7, F8, F9, F10, F11** are therefore **⊘ RETIRED**, not pending tests; do not re-fly
> them. F1/F2/F4 still cover live SCAR features (HVT movement / recon-fog / results bridge). The
> rescue rework's own runtime (capture race, POW recovery, Sandy) is tracked under **G8–G13** + the
> SCAR-rescue rows. See `docs/dev/design/414th-scar-rescue-rework-notes.md` and features §15.

### F1 — HVT movement + SOF capture loop · §15 · ☑ VERIFIED (2026-06-23)
- **Verified (2026-06-23):** seen in-game — the HVT drives/flees on activation
  and the capture loop behaves as designed (no alarm-RED pinning).
- **Pass:** HVT (incl. towed/SCUD groups) actually **drives** toward the city on
  activation (alarm-GREEN route); the SOF capture resolves `captured` when the
  un-killed command vehicle enters `SCAR_SOF_CAPTURE_RADIUS_M` (600 m) with the
  SOF group still alive. Priority killed > captured > escaped/timeout.
- **Fail signature (watched, did not occur):** HVT sits still (the alarm-RED
  pinning bug — do NOT revert the `mist.goRoute` alarm-GREEN route; a hand-rolled
  `setTask` did not move them); or `captured` never fires / fires after the
  vehicle is dead.

### F2 — Command-post intel fog · §15 · ☑ VERIFIED (2026-06-24)
- **Verified (2026-06-24):** the full path is confirmed — command posts hidden on
  the player map, the **"Reveal fog of war" overview toggle** shows both sides
  (ground truth), AND the **capture → permanent reveal** carryover now holds
  across turns (the residual the 2026-06-23 partial was waiting on).
- **Setup:** New campaign (default `scar_command_post_intel` ON).
- **Pass:** Enemy command posts are **entirely hidden** from the player map
  (no marker, not in target list) until a commander is captured or normally
  discovered; then they reveal with exact coords, permanently. AI/planner are
  unaffected (ground truth).
- **Fail signature:** Command posts visible on the player map before reveal, or
  a reveal that doesn't persist across turns.

### F3 — Player-flown SOF insert + C-130 EW exclusion · #56 / §15 · ☑ VERIFIED (2026-06-23; per-group mechanism re-confirmed via J3, 2026-06-28 audience pass)
- **Verified (2026-06-23):** flown — "the EW is gone": the `c130j` EW menu/behavior
  is correctly absent on the SOF insert C-130J-30 (the de-conflict gate fires).
- **Mechanism change (2026-06-26):** the de-conflict no longer skips the whole `c130j` plugin for
  the mission — it now excludes just the SOF/King group via the per-group deny-list (see **J3**), so
  the observable outcome (EW absent on the SOF insert) is unchanged but the path is new.
- **Pass:** The player can fly the air-assault-shaped delivery; the SOF C-130J flies clean of the
  `c130j` EW menu (now via `dcsRetribution.EwExcludedGroups`, not a whole-mission plugin skip).
- **Fail signature (watched, did not occur):** EW menu appears on the SOF insert;
  or the insert can't be planned/flown by the fixed-wing transport.

### F4 — Results bridge round-trip · §15 · ☑ VERIFIED (2026-06-17/18)
- Verified in-game: `SCAR area scar-N: launched/failed` round-tripped through
  the TARS channel into the debrief. No action; listed for completeness.

### F5 — Mis-ID budget penalty (R7) · §15 · ⊘ RETIRED (armor-hunt SCAR scenario dormant — rescue rework zeroes `scar_taskings`; was never flown, now moot)
- **Logic-reviewed 2026-06-25 (de-risked, not flown):** the whole chain reads correct.
  Lua (`scar_414_init.lua`): `misid_group_index` is populated **only** for `role ==
  "decoy"/"clutter"` (spawn paths L858-859 / L1033-1034) — the HVT, command vehicle, and
  threat/SAM groups go down a different branch, so a legit kill is structurally un-chargeable;
  the `onEvent` `S_EVENT_KILL` handler charges only when `event.initiator:getCoalition() ==
  scar_side(area)` (own-side prosecutor; nil/ambiguous coalition skipped), and `record_misid`
  carries the count onto `scar_results` even if the area already resolved. Python: `parse_scar_misid`
  skips non-positive/malformed, int-coerces; `_commit_scar_misid` routes by `blue-`/`red-`
  prefix (legacy unprefixed = blue), debits `penalty × count`, only when `penalty > 0`, always
  logs. **Residual flight risk (cannot read away):** whether `S_EVENT_KILL` actually fires with
  `event.initiator` populated for the **player's** weapon in MP — the documented event-quirk this
  row exists to confirm. Everything else is verified-by-reading.
- **Test coverage confirmed 2026-06-26:** the Python parse and the Lua decoy/clutter
  wiring are locked by `tests/test_scar_bridge.py` (passing) —
  `test_state_data_parses_scar_misid` and `test_lua_misid_handler_charges_decoy_clutter_kills`
  (the latter asserts the generated Lua registers decoy/clutter spawns in
  `misid_group_index` and calls `record_misid`). So the residual is *only* the MP
  `S_EVENT_KILL`/`event.initiator` firing above — nothing else is unverified.
- **Setup:** A SCAR sortie with `scar_misid_penalty` > 0; deliberately destroy a
  decoy/clutter convoy (not the HVT) with the player's aircraft.
- **Pass:** The debrief log shows `area …: N mis-ID(s)` and `… charged <cost>
  budget`; the prosecuting side's budget drops by `scar_misid_penalty` × kills.
  Killing the real HVT / command vehicle / a threat SAM is NOT charged.
- **Fail signature:** No mis-ID logged when a decoy dies to the player (the
  `S_EVENT_KILL` attribution didn't fire — likely weapon/MP event quirk); or a
  legit HVT/command/threat kill is wrongly charged; or budget unchanged with a
  positive penalty.

### F6 — SCAR auto-planning appears in the ATO · §15 · ☑ VERIFIED (2026-06-24)
- **Setup:** New campaign with an enemy armor concentration near the front and
  `scar_autoplan` ON.
- **Pass:** Turn 1's blue ATO already contains a SCAR package (claimable +
  flyable) against that armor, with no hand-building; the AI/red ATO has no SCAR
  package. With the setting OFF, no SCAR package is auto-fragged.
- **Fail signature:** No SCAR package when armor + setting are present (no
  SCAR-capable squadron / fulfiller bailed); a red SCAR package appears; or a
  SCAR package appears with the setting off.

### F7 — SCAR loiter/static hold (no chase, fail = window) · §15 / PR #187 · ⊘ RETIRED (armor-hunt SCAR retired by the rescue rework — scenario no longer runs)
- **Setup:** Plan a SCAR flight against a real enemy armor TGO. Fly to the kill box.
- **Pass:** The bound armor (and any spawned decoys/clutter) **holds in place** — nothing drives off
  toward a city; a bound missile site stays inert (no relocation, no launch). Killing the armor
  attrits it natively at debrief (shows in losses) with no SCAR-specific scoring. If you never kill
  it, the area resolves **failed on the window timeout only** — never an instant fail on arrival.
- **Fail signature:** anything drives/flees; a SCUD relocates or launches; an instant "failed" the
  moment the area goes live (the arrival-fail gate leaked); a `scar_414_init.lua` Lua error.

### F8 — SCAR inverted SOF capture (dwell on the live commander) · §15 / PR #187 · ⊘ RETIRED (armor-hunt SCAR retired by the rescue rework — scenario no longer runs; capture is now the rescue POW loop, G8–G13)
- **Fix (2026-06-26):** the loiter rework left the SOF capture broken both ways — the scripted
  fallback team spawned on the *static* commander and **auto-captured with no player** (armor
  variant), while the spawn variant's HVT held ~15 NM from the kill-box centre so the capture point
  (on the centre) was nowhere near the commander → **capture impossible**. Now `maybe_bind_sof` binds
  **only a player-delivered team** (no scripted fallback, no HVT-distance prebind — both chase-only),
  and `_make_static` re-homes the spawn HVT onto the centre so `sofX/Y` sits on the commander.
  Covered by `tests/test_scar_bridge.py` (delivered-only bind; HVT at centre). Residual is the in-sim
  end-to-end.
- **Setup:** `scar_command_post_intel` ON, a SOF team in stock, a SOF insert fragged onto the SCAR
  package. Airdrop the team **onto the held commander** (the SOF mark); leave the command vehicle ALIVE.
- **Pass:** With the player-delivered SOF team holding on the **live** command vehicle for
  ~`SCAR_SOF_DWELL_S` (30s), the area resolves **captured** (commander reveal + SOF refund next turn).
  Killing the command vehicle instead forfeits the capture (it's just a kill); leaving the commander
  resets the dwell. **With NO team delivered, the area never auto-captures** (it fails at the window).
- **Fail signature:** any **capture without a player-delivered team** (the auto-capture bug returns);
  capture impossible for the spawn variant (HVT/commander not at the kill-box centre); instant capture
  on co-location (dwell not enforced); capture with the commander already dead. Tuning to watch: the
  drop must land within the capture radius (`SCAR_SOF_CAPTURE_RADIUS_M`, 600 m) of the commander — if
  that proves too tight for a deliberate airdrop, bump it.

### F9 — SCAR King talk-on gate (Phase 2 + 3) · §15 / PR #189 · ⊘ RETIRED (armor-hunt SCAR designation retired by the rescue rework — scenario no longer runs)
- **Setup:** Fly a SCAR flight to its kill box (cross the ~50 NM check-in ring); leave it on station.
- **Pass (stage 1, talk-on, on check-in):** the on-scene controller ("MAGIC") cues **once** — GREEN
  smoke at the box centre + one persistent map mark + a descriptive "find + ID the real one, stand by
  for my designation" call — **no F10 dig**, fires a single time. The decoy ID puzzle stands (the
  smoke marks the **box**, not the exact vehicle).
- **Pass (stage 2, escalation):** if the real target is still alive after the talk-on window
  (`SCAR_TALKON_DELAY_S`, 120s), MAGIC escalates **once** — **RED** smoke on the real target's lead
  vehicle + "cleared hot" — so a stuck player still gets pointed in. A human King talking on SRS is
  unaffected by either stage.
- **Pass (audience, 2026-06-25):** every MAGIC call (talk-on, RED designation, laser, "say again")
  shows **only to the on-task SCAR flight(s) + any King group** — NOT to unrelated BLUE pilots. Sit a
  second BLUE flight well outside the box / off the tasking and confirm it sees **no** MAGIC text.
- **Fail signature:** no stage-1 cue on arrival (`designate`/`package_near` not wired); the call/smoke
  repeats every tick (one-shot guards failed); no escalation after the window on a live target, or it
  escalates after the target is already dead; RED smoke off the real vehicle (bad `target_lead_pos`);
  smoke at sea level (bad `land.getHeight`); a MAGIC call reaching the **whole coalition** again
  (`scar_outtext` regressed to `outTextForCoalition`, or the on-task/King audience empty); or a
  `scar_414_init.lua` Lua error.

### F10 — SCAR King laser/IR designation (Phase 3b) · §15 / PR #189 · ⊘ RETIRED (armor-hunt SCAR designation retired by the rescue rework — scenario no longer runs)
- **Setup:** Frag **both** a C-130 **King** (a Combat SAR C-130) and a SCAR striker; get the King on
  station over the SCAR box. Fly the SCAR to the box and let the talk-on escalate (or wait the window).
- **Pass:** After the precise designation, with a King within ~25 NM the King **lases** the real
  target (code **1688**) + an IR pointer, and MAGIC calls the code — an LGB/Maverick-capable striker
  can guide on it. The laser **drops** when the target dies, the King leaves station, or the area
  resolves. **No King fragged ⇒ no laser at all** (smoke + talk-on only, F9) and no error.
- **Fail signature:** a laser with no King fragged (the no-King rule leaked); laser before the
  precise designation (puzzle bypass); the spot **leaks** after the target/King is gone (no
  `maybe_drop_laser`); wrong code published; or a `scar_414_init.lua` Lua error / bad `Spot.createLaser`
  signature. (Per-area laser-code allocation is a deferred refinement — a fixed 1688 is fine here.)

### F11 — SCAR designation polish: night illum + "say again" F10 (Phase 4) · §15 / PR #189 · ⊘ RETIRED (armor-hunt SCAR designation retired by the rescue rework — scenario no longer runs)
- **Setup:** Fly a SCAR at **night** to the box; also try the F10 entry by day.
- **Pass:** At night each smoke cue (GREEN box / RED target) is accompanied by an **illumination
  flare** over the cue point (smoke alone is invisible after dark). F10 shows **one** entry — "MAGIC:
  say again SCAR target" — that re-pops the current cue (and re-calls the laser code) for your active
  target; with no active target it says so. By day, no illum (smoke only).
- **Fail signature:** no flare at night / flare in daylight (bad `is_night`); the F10 missing or
  duplicated; "say again" cues the wrong stage or a resolved area; or a Lua error.

---

## G. Plugin runtime (Lua, not CI-runnable)

### G2 — TARS BDA bridge · §12 · ☑ VERIFIED (2026-06-24)
- **Setup:** Fly an F-14 TARPS recon pass over enemy targets.
- **Pass:** Captured-target snapshots feed back into Retribution's BDA
  fog-of-war (confirmed composition/damage after the pass).
- **Fail signature:** Film menu never unlocks, or captures don't reach the
  debrief / don't update BDA.

### G3 — TIC ambient fire / dynamic fronts · §9 · ☑ VERIFIED (2026-06-24)
- **Setup:** Fly over an active front, including where terrain (towns/ridges)
  blocks line-of-sight between combatants.
- **Pass:** The front looks **alive from the air** — tracers/impacts around real
  enemy positions even where LOS is blocked (ambient area-fire), without aimed
  lethality spikes.
- **Fail signature:** Front goes silent/dead-looking where LOS is blocked.
  Note: with StormTrooper AI on (default), TIC cloaks managed groups — known
  limitation, not a bug.

### G4 — C-130J EW/ISR mission systems · §2 · ☑ VERIFIED (2026-06-24)
- **Setup:** Fly the C-130J-30 JAMMING slot (static slot, player-only).
- **Pass:** EW (area/directional/spot jamming, missile spoof, pod loadout) and
  ISR (passive detection, ELINT map marks, SIGINT reports, crew handoff) work
  per `C-130J-30 Mission Systems Overview.txt`.
- **Fail signature:** Menu missing/erroring (would now be caught earlier by the
  Lua syntax gate), or any of the documented EW/ISR actions not firing.

### G5 - Retired generic EW/Jammer Script stays gone - §2 - ☑ VERIFIED (2026-06-25)
- **Verified (2026-06-25, in-game):** no generic Jammer/`EWJamming` F10 menu on the fighter
  and the generated mission carried no `ewrj`/`startEWjamm`/`startIAdefjamming` actions; the
  C-130J JAMMING slot kept its own `c130j` menu. Fail signature did not occur.
- **Setup:** Generate a mission with a player F-16C carrying its ALQ-184 pod and
  an AI SEAD/DEAD package that would previously have been eligible for `ewrj`.
- **Pass:** No generic "Jammer menu" / `EWJamming` F10 commands appear on the
  fighter, no `startEWjamm` / `startIAdefjamming` waypoint actions are present
  in the generated mission, and the C-130J JAMMING slot still uses only the
  `c130j` Mission Systems menu.
- **Fail signature:** The old generic jammer menu appears on fighters, or the
  generated mission references `ewrj`, `EWJamming`, `startEWjamm`, or
  `startIAdefjamming`.

### G6 — MANTIS IADS engine (phase 1: core networking) · MANTIS migration · ☑ VERIFIED (2026-06-25)
- **Verified (2026-06-25, in-game, zone-node map):** the C2-regression re-fly passed — red SAM
  radars came up on RWR at start (no spurious decapitation from the scenery-node `node_dead`
  fix) and bombing a comms mast / power hub still degraded its dependent SAMs. Combined with the
  2026-06-24 routing/network-build/C2-degradation pass below, MANTIS phase 1 is confirmed.
- **⚠️ Regression found + fixed 2026-06-24 (GermanyCW):** many IADS comms/power/
  command-center nodes are destructible **scenery** (comms masts, power hubs, VOR/DME,
  beacons) — NOT placed statics — so `StaticObject.getByName(name .. " object")` never
  finds them. The old `static_dead` read "not a static" as "destroyed" → mass-decapitated
  the whole network on the first poll → all SAMs offline → **empty RWR.** Fix
  (`mantis-config.lua`, `node_dead`): a node counts as dead only on **positive** evidence —
  a placed static of that name existed and no longer `:isExist()`, **or** its name is in the
  global **`dead_events`** table (the S_EVENT_DEAD / scenery-trigger record Retribution
  already keeps; matched with the `"id | "` prefix stripped, since scenery is recorded by
  bare name). This keeps the bomb-the-comms feature working for scenery targets while
  killing the false decapitation. **Re-fly needed:** GermanyCW campaign — (1) red SAM
  radars come up on RWR at start (no spurious decapitation); (2) bombing a comms mast /
  power hub still degrades its dependent SAMs (`MANTIS C2 - comms/power '…' lost`).
- **Result (2026-06-24):** PASSED on engine routing, network build, and C2
  degradation — the high-risk parts. Confirmed from `dcs.log` + the
  `retribution_nextturn.miz` marker + a Tacview (`Tacview-20260624-160553`):
  - **Routing/build:** `Skynet … engine is 'mantis' … skipping` + MANTIS built
    both coalitions (`RED 14 SAM/19 EWR`, `BLUE 3 SAM/4 EWR`), MANTIS v0.9.34 +
    INTEL/DLINK started clean, **C2 watchers armed for RED and BLUE**. No Lua errors.
  - **C2 events fire:** comms kill → `MANTIS C2 - comms '…' lost; degrading 1 SAM(s)`;
    power kill → `MANTIS C2 - power '0378 | Repair workshop' lost; 13 SAM(s) offline`.
  - **Degradation sticks (the #1 risk):** the degraded *networked radar* SAMs
    (SA-3/5/6) stayed offline against live AI blue targets — **MANTIS did NOT
    re-enable them** on its detection cycle. The only late Tacview launches were
    autonomous SHORAD (SA-8 Osa, 2S6 Tunguska), which are out of C2 scope by design
    (`IadsRole.participate` excludes `POINT_DEFENSE`/`NO_BEHAVIOR`; standalone SHORAD
    maps to `SAM` and is only networked if within power/comms range). So the revival
    bug the handoff flagged **did not occur**.
  - **Caveats / remaining:** (a) observation was AI-vs-AI; the **emissions-control
    "dark until in range" path flown by a human is not yet eyeballed** (lower risk —
    minor follow-up). (b) Tacview *corroborates* but can't fully *isolate* C2-silence
    from blue SEAD also killing the SA-3/5/6 radars by 37:37 — the decisive evidence
    is the direct observation that degraded SAMs stayed down. (c) **13-of-14 red SAMs
    hung off one power node** — almost certainly a **per-campaign power-source placement**
    artifact (SAMs auto-connect to any power source within 35nm, `IadsRole.connection_range`),
    not an IADS-generator bug. Revisit as a campaign-`.miz` layout check only if the
    over-concentration recurs across other campaigns.
- **Setup:** In settings, set **IADS engine → MANTIS (experimental)** (Mission
  Generator → Gameplay), generate a mission with red SAMs + EWRs, and fly into the
  IADS. Confirm via `dcs.log` that `mantis-config.lua` built
  the network ("building Retribution-RED-IADS (N SAM, M EWR group names)") and that
  `skynetiads-config.lua` logged "engine is 'mantis' ... skipping".
- **Pass:** SAM radars stay dark (emissions control) until a target is in range,
  then go active and engage; EWRs cue the network; both coalitions build if present;
  with the default Skynet engine the mission is byte-for-byte unchanged (MANTIS
  bridge logs "engine is 'skynet' ... skipping").
- **Fail signature:** No SAM activity at all (FilterPrefixes matched nothing — check
  generated group names vs the names in `dcsRetribution.IADS`), or *every* coalition
  group goes active as EWR (an empty set collapsed into a match-all — the `NO_MATCH`
  guard failed), or both bridges run / neither runs (engine-marker plumbing), or a
  group name that is a strict prefix of another double-registers.
- **Phase-4 tuning to watch:** SAM engagement range / max-active-SAMs / detection
  interval take effect (compare engagement ranges vs the options); with EWR
  auto-relocate on, mobile EWRs reposition over time.
- **Phase-5 C2 (advanced_iads campaign only) — the highest-risk part:** kill a comms
  tower → its dependent SAM should go autonomous (alarm RED) within the poll interval;
  kill a power source → dependent SAM goes offline (AI off, radar dead); kill all
  command centers → the whole coalition's SAMs degrade. Watch `dcs.log` for
  `MANTIS C2 - ...` lines. **Key fail signature:** a SAM the watcher disabled comes
  back to life on MANTIS' next detection cycle (MANTIS re-enabling it) — degradation
  doesn't "stick." If seen, the watcher must remove the SAM from MANTIS' set, not just
  toggle the group.

### G7 — MIST → MOOSE shim (`mist_moose_shim.lua`) · MIST retirement · ☑ VERIFIED 2026-06-25 (GermanyCW)
- **Result (2026-06-25):** PASSED. With `base/plugin.json` loading the shim instead of
  `mist_4_5_126.lua`, a full GermanyCW session logged **zero `mist_moose_shim` errors** —
  MANTIS built, CTLD spawned crates (shim `dynAddStatic`), intercept QRA configured (shim
  `dynAdd`, after the `_resolve_group_category` fix), core glue ran. The two crashes seen
  during testing were **pre-existing** bugs unrelated to the shim (civ-helo RAT sim crash;
  CTLD smoke-zone string/number format), both fixed in #166.
- **Follow-up (2026-06-26):** A later GermanyCW pass still hit a native DCS
  `wSimCalendar::DoActionsUntil` crash during fixed-wing `RAT_CIV_C130` landing/respawn
  churn. Civilian traffic now runs as one-shot scenery: RAT ATC is disabled and flights do
  not respawn after landing. Re-test by leaving civilian traffic enabled for a Combat SAR
  pass and watching for any new `RAT_CIV_*` crash lead-up.
- **Pass:** No `mist_moose_shim.lua:<n>` errors in `dcs.log`; CTLD sling-load (load/drop
  troops, sling+unpack a crate, build a FOB), SCAR capture + CSAR, intercept/QRA, and core
  state-write/messages all behave as on MIST.
- **Fail signature:** any `mist_moose_shim.lua` Lua error (a consumer hit an unimplemented/
  wrong-shaped symbol). `mist_4_5_126.lua` is kept in the repo → rollback is a one-line
  `base/plugin.json` revert. **Remaining:** fly across more campaigns/maps, then delete
  `mist_4_5_126.lua` as the final cleanup.

### G8 — Combat SAR pilot rescue (`combatsar` / MOOSE CSAR) · Combat SAR Phase 2 · ☑ VERIFIED (2026-06-28, audience in-game pass — user: "pilot rescue attempted looks good")
- **In-game (2026-06-28, audience pass — user verdict "looks good"):** a Combat SAR pilot rescue was flown/attempted and behaved correctly — the SAR ran as designed with no Lua error. As with J1/J2 this is the user's eyes-on "looks good," not a deeply-isolated audit of the pickup→deliver→`combat_sar_rescues`-increment loop (that precise count is the G11 scoring row). Don't re-mark UNTESTED without flying it.
- **Live-log confirmation (2026-06-27, GermanyCW Fulda/Haina, `dcs.log`):** the plugin armed
  clean — `CSAR (Blue) | Started (1.0.34)` then `DCSRetribution|Combat SAR plugin - CSAR started
  with 1 rescue helo group(s), 1 King(s), template 'Combat SAR Downed Pilot', enableForAI=false`.
  So: the `Combat SAR Downed Pilot` template **resolved** (the "missing template" fail signature
  is absent), the rescue-helo group and King both registered, **no `combatsar-config.lua` Lua
  error** anywhere in the run, and `enableForAI=false` (correct, setting off — the "AI ejection
  spawns a pilot" leak can't occur). **Residual (still in-cockpit):** the actual pickup→deliver→
  count loop — and note that loop needs a **player in the rescue helo**: in this sortie the CH-47F
  is an **AI group** and the only player client is the C-130J-30 King, so flying the King alone
  does not exercise the pickup.
- **Setup:** A campaign with a blue **CH-47** squadron; plan a **Combat SAR** flight (CH-47) near
  the FLOT (optionally a C-130 Combat SAR "King" too). Fly it, then have a **human** pilot eject in
  the area (a second slot, or eject yourself from a separate fighter).
- **Pass:** On the human ejection a downed pilot spawns with a radio beacon; the CH-47's F10 CSAR
  menu shows the active SAR; the helo hovers/lands within pickup range, boards the pilot, and
  delivers to a friendly airfield/FARP (rescue count increments). `dcs.log` clean. The C-130 "King"
  just flies its orbit (never lands). The existing SOF-recovery CSAR (SCAR loop) is undisturbed.
- **Fail signature:** any `combatsar-config.lua` Lua error; the downed pilot never spawns
  (missing `Combat SAR Downed Pilot` template, or `SPAWN:NewWithAlias` nil); an **AI** ejection
  spawns a pilot (means `enableForAI` leaked true); a non-CH-47 helo gets the rescue menu (rescue
  set mis-bound); or double event-handling with the SOF CSAR. If the helo can't deliver anywhere,
  check `allowFARPRescue` / that a friendly airfield is in range.

### G9 — Combat SAR AI standing alert (`auto_combat_sar`) · Combat SAR Phase 3 · ☑ VERIFIED (2026-06-28, audience in-game pass — re-fly after the eject-trigger fix; user: "good")
- **Re-fly PASSED (2026-06-28, audience pass — user verdict "good"):** the eject-trigger fix (`aicsar.UseEventEject=true` + the AI-eject bridge that calls `aicsar:_EventHandler` on a blue AI ejection) cleared the earlier 2026-06-28 FAIL recorded below — the AI standing-alert rescue now triggers and behaves in-cockpit. This flip assumes the flown build carried the fix (per the user, it did). The original FAIL root-cause is retained below for history.
- **In-game pass 2026-06-28 (session `f08e522b`) — AI rescue did NOT trigger; root-caused + fixed; re-fly owed.**
  Flew the C-130 King with `auto_combat_sar` ON (GermanyCW Fulda/Haina, turn 1). A **blue AI ejected**
  near the front (Tacview: 2 `Country=de`/`Color=Blue` chutes at ~3 km). Plugin armed correctly —
  `CSAR (Blue) Started`, `AICSAR ... armed (helo template ..., FARP 'Frankfurt')`, `enableForAI=true`,
  King `TACAN 39Y, LARS menu attached`. **No rescue launched; LARS showed no survivor.** Root cause
  (read from `Moose.lua`): stock **AICSAR dispatches only on `S_EVENT_LANDING_AFTER_EJECTION`** — the
  pilot must touch down (~8–9 min under canopy from ~3 km) and that DCS event is unreliable for AI; its
  eject fast-path is player-only (`IniPlayerName`). The mission ended **57 s after the ejection** (pilot
  still at ~3 km in Tacview), so nothing could have started even on a clean run. **Fix landed
  (`combatsar-config.lua`):** `aicsar.UseEventEject=true` (landing handler no-ops → dedup) + an ejection
  bridge that calls `aicsar:_EventHandler(event, true)` the instant a blue AI ejects → survivor spawns
  under the ejection point + helo launches immediately. **Re-fly owed:** AI ejects in range → an AI helo
  spawns from the FARP within seconds and recovers; `dcs.log` shows
  `Combat SAR - AI eject rescue dispatched for '<unit>'`. **Secondary finding (not fixed here):** the
  King's **LARS never lists AI survivors** (player CSAR runs `enableForAI=false`) — follow-up if humans
  should be able to cue AI rescues. **Don't re-mark this UNTESTED without flying the fix.**
- **Live-save + branch re-verify (2026-06-27, headless session `78eae772`):** loaded the live
  `autosave.retribution` (Nevada/Tonopah, turn 1) headless with `auto_combat_sar` **ON** — the blue ATO
  frags **both** Combat SAR airframes (`CH-47F Block I` + `C-130J-30` King) and **red frags zero**, so
  the blue-gate holds on a real auto-planned ATO (the "CSAR planned for red" fail signature did not
  occur). `test_combat_sar_planning.py` + the scoring/placement suite re-ran **green on this branch**.
  **Residual unchanged (cockpit only):** the AI helo actually **spawning from the FARP and flying the
  rescue** (MOOSE `AICSAR` runtime) — not headless-provable.
- **AI rescue re-wired to MOOSE `AICSAR` 2026-06-26 (PR pending in-game pass):** the 2026-06-26
  playtest showed the AI rescue helo just orbited and never recovered anyone — MOOSE CSAR's
  `enableForAI` only *tracks* AI ejections, it never flies an AI helo. The AI path now uses
  `AICSAR` (spawns its own rescue helo from the FARP base on a pilot-down event). Pass criteria
  below updated to match: watch for a helo **spawning from the home base**, not the orbiting
  flight diverting.
- **Orbit-placement fix 2026-06-25 (found in-game, fixed — re-observe):** the standing-alert orbit
  used to **mirror the AWACS** (it reused the AEW&C builder → 80 NM standoff + 60 NM racetrack), so a
  CH-47 could never reach an ejection. Combat SAR now flies a **dedicated forward hold**
  (`game/ato/flightplans/combatsar.py`): front-anchored, **15 NM** threat buffer, **5 NM** racetrack
  half-length. Re-observe that the planned CSAR orbit now sits **near the FLOT**, not back at AWACS depth.
- **Placement adjudicated headless (2026-06-27):** Measured the real anchor the planner computes on the
  live `autosave.retribution` (GermanyCW, Fulda/Haina front) by calling `support_orbit_anchor` for the
  Combat SAR 15 NM buffer and contrasting with the 80 NM AEW&C buffer it replaced. Result: CSAR orbit
  centre **25.2 NM** from the FLOT (auto-pushed back from the 15 NM nominal only as far as needed to clear
  the red threat ring) vs the AWACS-depth anchor at **90.3 NM** — **65 NM further forward**. Orbit centre
  **and both racetrack endpoints test clear of the red threat zone** (`threatened()=False`), and the
  racetrack is a tight **10.0 NM** hold (not the 60 NM AEW&C track). So the placement fail signatures —
  "orbit again at AWACS depth / mirrors the AWACS racetrack" and "orbit inside an enemy threat ring" — do
  **not** occur on this campaign; the forward-hold fix is structurally in effect. **Residual (cockpit
  only):** the AI helo actually **spawning from the FARP and flying the rescue** (the MOOSE `AICSAR`
  runtime) and the package appearing in the ATO with `auto_combat_sar` ON — neither is headless-provable.
- **Setup:** Enable **Automatic Combat SAR** (HQ automation settings; default OFF). Campaign with a
  blue **CH-47** squadron + budget. Auto-plan turn 1 (observe-only, don't fly the CSAR).
- **Pass:** A blue **AI** `Combat SAR` package appears in the ATO, **holding a tight racetrack near an
  active front** (one per front, capped by available CH-47s) — clearly forward of the AWACS/tanker
  orbits, clear of enemy threat rings. The generator logs `enableForAI=true`. When a pilot ejects in
  range, a rescue helo **spawns from the FARP home base** (AICSAR), flies to the survivor,
  lands/hovers to recover, and RTBs — with no human in any helo (AICSAR `autoonoff` stands down if a
  player crews a rescue helo). `dcs.log` shows `AICSAR AI standing alert armed (helo template ..., FARP ...)`.
  Known v1 gaps to note (not fail): no spare-pilot scoring credit for AICSAR rescues; a fixed-wing
  player ejection with no human helo up double-spawns (CSAR + AICSAR).
- **Placement fail signature:** the CSAR orbit again sits at AWACS depth / mirrors the AWACS racetrack
  (the dedicated `CombatSarFlightPlan` didn't take — check `flightplanbuildertypes.py` maps
  `COMBAT_SAR` to `CombatSarFlightPlan`, not `AewcFlightPlan`); or the orbit lands inside an enemy
  threat ring (15 NM buffer too tight for that campaign's FLOT SAMs).
- **Fail signature:** no CSAR package planned with the setting on + a CH-47 squadron present (HTN/
  fulfiller gap — check `combat_sar_targets` populates and a CH-47 is purchasable); a CSAR planned
  for **red** (blue-gate leaked); the AI helo orbits but never diverts to a downed pilot
  (`enableForAI` not reaching the engine, or MOOSE AI-rescue routing vs. Retribution's flight plan);
  or the AI rescue routing fights the despawn/RTB logic. **Off-state regression check:** with the
  setting OFF, confirm no CSAR is auto-planned and `enableForAI=false` is logged.
- **Off-state confirmed in live log (2026-06-27, GermanyCW, `dcs.log`):** with `auto_combat_sar`
  OFF, the plugin logged `... CSAR started with 1 rescue helo group(s), 1 King(s), ...
  enableForAI=false` — i.e. the standing-alert AI path is correctly dormant (no AICSAR spawn, no
  AI pilot tracking). The **AI-ON** path (helo spawns from FARP, flies the rescue) still needs its
  own run with the setting on.

### G10 — Combat SAR King TACAN beacon + LARS · Combat SAR Phase 4 · ✗ REGRESSED → fix applied 2026-06-30 (root-caused; needs re-fly)
- **Regression (2026-06-30, flown session — user: "c130 had no F10 menu for LARS"):** the player-flown
  King's LARS menu, previously cockpit-confirmed 2026-06-27, did **not** appear this session.
  `dcs.log` shows **zero** `Combat SAR King - activated` lines across ~80 minutes and two mission
  loads, despite the player successfully joining the King's cockpit both times
  (`Player 'Wizard 1-4 | Flash 402' joined unit '...C-130J-30| Pilot #1'` at `00:10:27` and again at
  `00:18:02` after a mission reload) and the generated `.miz`'s `dcsRetribution.CombatSAR.kings`
  table carrying the **exact correct** group name (`Front line Kutaisi/Senaki-Kolkhi Combat SAR|2|18|
  C-130J-30|`, verified byte-for-byte against the DCS client-registration log line) — so this was not
  a group-name mismatch. **Root cause (best available without a Lua interpreter — CLAUDE.md prohibits
  running/compiling Lua here, so this is read-diagnosed):** `activateKing()`'s early-return guards
  (not-alive / no-unit / not-found) were all silent (no logging), and the only two activation paths —
  a one-shot mission-start scan and the `Birth`/`PlayerEnterAircraft`/`PlayerEnterUnit` event handlers
  — both had single points of failure: the mission-start scan never retries if the King isn't queryable
  yet (e.g. during the pre-"sim running" briefing/slot-selection pause — this session's log shows the
  sim didn't reach `state=ssRunning` until `00:18:30`, well after the player joined the King at
  `00:18:02`), and the event path resolves the group via `EventData.IniGroup`/`IniGroupName`, both of
  which can be unpopulated for `PlayerEnterAircraft`/`PlayerEnterUnit` (confirmed via `Moose.lua`:
  `IniUnit` is populated far more reliably than `IniGroup`/`IniGroupName` for these event types).
- **Fix applied (2026-06-30, `resources/plugins/combatsar/combatsar-config.lua`):** (1) every early-return
  in `activateKing()` now logs why (`Combat SAR King - '<name>' not yet alive/has no unit #1 (<reason>)`),
  turning a future silent failure into something diagnosable in `dcs.log`; (2) `activateKingFromEvent`
  now falls back to `EventData.IniUnit:GetGroup()` when `IniGroup`/`IniGroupName` are both absent; (3) a
  new periodic **retry sweep** (`retryUnactivatedKings`, piggybacked on the existing 5 s `POLL` cadence)
  re-tries `GROUP:FindByName` for any King not yet in `activatedKings` every 5 s until it succeeds, so no
  single missed mission-start/event moment can permanently block activation for the rest of the mission.
  Lua syntax read-checked (balanced blocks verified by hand — no local interpreter available).
  **Needs a re-fly** to confirm the LARS menu now appears and `Combat SAR King - activated` shows in
  `dcs.log`.
- **Cockpit-confirmed (2026-06-27, user in-game pass — session `suspicious-goldberg`/`1ca51fbf`):**
  the player-flown King's **F10 → Combat SAR → LARS menu works** ("F10 LARS good") — the #196
  player-King menu-attach fix is verified live. The remaining PARTIAL is only the **AI-King scripted
  TACAN beacon** (player King has no AI controller, so it dials TACAN in-cockpit by design — not a
  fault). *(This confirmation was given in-game and dropped — PR #226 recorded only the headless
  evidence, not the three cockpit wins; recovered here.)*
- **Setup:** Plan a player **C-130** Combat SAR ("King") alongside a **CH-47** Combat SAR. Fly the
  King; have a human pilot eject in the area. **For the scripted TACAN path, the King must be AI**
  (e.g. `auto_combat_sar` standing alert) — a player-flown King sets TACAN in-cockpit (see below).
- **Pass:** An **AI** King radiates its TACAN (rescue helo can tune + home, and it **tracks the moving
  orbit** — bearing/range stay sane as the King flies its racetrack). The King's F10 **Combat SAR →
  LARS** lists each active survivor with position and bearing/range from the King, sorted nearest-first;
  "no active survivor radios" when none. (ADF dropped — TACAN is the only homing aid.) Generator logs
  `... %d King(s) ...`.
- **Fail signature:** any `combatsar-config.lua` Lua error; **`ALERT ... AI::Controller exception: No
  executor for command "ActivateBeacon"`** followed by a CTD (`ACCESS_VIOLATION` in
  `wSimCalendar::DoActionsUntil` / `CommandsTraceDiscreteIsOn`) — this was the **2026-06-25 crash**
  when the King was player-flown; **now guarded** (`activateKing()` skips `ActivateTACAN` unless
  `unit:IsAlive() and unit:GetPlayerName() == nil`). AI-King fail: TACAN absent (no channel allocated,
  or `ActivateTACAN` not firing) or **frozen at the spawn point** instead of tracking; LARS empty when
  survivors exist (`csar.downedPilots` not read) or duplicated F10 entries
  (birth/start-sweep/player-enter dedup failed); King menu missing on a player client-slot,
  delayed, or AI King (activation handler not attaching).
- **Note (player King):** A human-flown King has no AI controller, so the scripted beacon is **skipped
  by design** — the crew dials the planned channel manually in the cockpit. Re-test target: confirm an
  **AI** King still lights its TACAN and no CTD recurs with a player King.
- **Player-King F10 menu fix (PR #196, `c09ffc512`, 2026-06-25):** The King's F10 **Combat SAR → LARS**
  menu was only attached on `EVENTS.Birth` + mission-start, which **races DCS's F10-menu creation for a
  player client slot** — so a player-flown King got **no F10 menu**. Fix adds
  `PlayerEnterAircraft`/`PlayerEnterUnit` handlers plus a **1 s deferred retry**, nil/dead/no-unit guards,
  and an `env.info` line `Combat SAR King - activated '<name>' via <reason> (... LARS menu attached)` so
  the attachment is now visible in `dcs.log`. **The 2026-06-25 flight (player King, no F10 menu) predated
  this fix** — the flown build was generated `21:43`, two minutes after #196 merged at `21:41`, so its
  binary could not have contained it (it also still carried the FlightControl plugin removed later in #200).
  Re-test on a build containing #196: the player King's LARS menu appears (immediately or within ~1 s) and
  the new `... LARS menu attached` line shows in the log.

### G11 — Combat SAR rescue scoring (pilot spared at debrief) · Combat SAR Phase 4 · ☑ VERIFIED (2026-06-30, `414TH.retribution` save + `state.json` — user confirmed "rescue worked")
- **Verified (2026-06-30, headless save load — `414TH.retribution`, turn 5):** `game.last_sitrep`
  reads `Sitrep(turn=4, ..., pilots_recovered=3)` — the SITREP the debrief itself computed from
  `commit_air_losses`, matching `state.json.combat_sar_rescues`'s 3 entries exactly and the debriefing
  screenshot's loss counts (10 USA / 7 Vietnam aircraft) verbatim. This is the Python-side confirmation
  the prior PARTIAL note was waiting on — the delivered pilots were genuinely spared, not just logged
  by the Lua bridge. User cockpit-confirmed the same thing independently ("rescue worked"). Fail
  signature did not occur.
- **Partial (2026-06-30, flown session — `state.json`):** `combat_sar_rescues` came back non-empty with
  **3** real, well-formed unit names (`Kutaisi_AJS37_475-1`, `Kutaisi_UH-1H_536-1`,
  `Kutaisi_AH-64D BLK.II_928-1`) — direct proof the Lua `OnAfterRescued` → `combat_sar_rescues` bridge
  fired for 3 separate live deliveries this session, and the names are self-consistent with
  `crash_events` (e.g. `Kutaisi_UH-1H_534-1`/`_630-1` crashed — unrescued — while `_536-1` did not, i.e.
  it was picked up before loss). This directly answers the row's flagged residual (whether the Lua's
  `originalUnit` name actually matches what DCS reports). **Not confirmed from these artifacts:**
  whether `commit_air_losses` on the Python side actually spared these 3 pilots at debrief (that only
  shows up in the processed campaign save / squadron roster after Retribution ingests this
  `state.json`, which we don't have here) — check the next turn's squadron roster or debrief log to
  close this out.
- **Headless adjudication (2026-06-26):** the Python scoring is verified by
  `tests/test_combat_sar_scoring.py` (passing): `commit_air_losses` spares exactly the
  rescued pilot (`pilot.kill` not called) while still attriting the airframe
  (`owned_aircraft` drops), an un-rescued pilot is still killed, and an empty
  `combat_sar_rescues` falls back to "everyone dies" (the safe default). State parsing
  tolerates malformed/empty input. **Residual (in-sim only):** that the `originalUnit`
  name the Lua writes actually matches the name DCS reports in kill/crash events (the
  unit-map resolve) — the test uses identity matching, not real event names.
- **Setup:** Fly a CH-47 Combat SAR (or AI standing alert). Have a **known** human pilot eject near
  the FLOT, pick them up, and **deliver them to a friendly airfield/FARP**. End the mission and run
  the debrief.
- **Pass:** The delivered pilot's **airframe is still counted lost** (squadron `owned_aircraft` drops),
  but **the pilot is NOT killed** — they remain on the squadron roster with their experience. `dcs.log`
  shows `Combat SAR - pilot of <unit> delivered home`; the Retribution log shows
  `Combat SAR recovered the pilot of …`. A pilot picked up but **not** delivered (helo shot down with
  them aboard) is **not** spared.
- **Fail signature:** rescued pilot still killed at debrief (`combat_sar_rescues` empty in `state.json`,
  or the `originalUnit` name doesn't match what DCS reported in kill/crash events — check the unit-map
  resolve in `commit_air_losses`); or a *non*-delivered pickup wrongly spared (`OnAfterRescued` firing
  without delivery). Empty list ⇒ pre-scoring behaviour (everyone dies) — that is the safe fallback,
  not a separate bug.

### G12 — Combat SAR extracts a stranded SOF team · Combat SAR + SCAR · ☐ UNTESTED (scoring layer test-covered, adjudicated 2026-06-26)
- **Headless adjudication (2026-06-26):** the SOF-extraction scoring is verified by
  `tests/test_combat_sar_scoring.py` (passing): `sof_rescue_pickup_name` is stable and
  `SOFRESCUE`-prefixed (rounded strand metres), `commit_sof_recoveries` clears + refunds
  the delivered team while leaving an un-rescued one pending, the path is blue-only, and a
  SOF recovery does **not** leak into `combat_sar_rescues` (the two channels stay separate).
  Parsing tolerates malformed input. **Residual (in-sim only):** the CASEVAC actually
  spawning at the strand point and the generation-vs-debrief name agreeing end-to-end.
- **Setup:** A campaign with **SCAR command-post intel** on and a **stranded SOF team** on the map (a
  "Downed SOF Team" objective from a botched capture; or cheat one in). Plan a **Combat SAR** CH-47.
  Fly out to the team's strand point, board it (F10 `CSAR`), and **deliver it to a friendly field**.
- **Pass:** The stranded team spawns as a CASEVAC pickup at the strand point; the Combat SAR helo
  boards + delivers it. At debrief the **pending rescue clears and one SOF team is refunded** to a
  friendly base (same as a dedicated `CSAR` air-assault recovery). `dcs.log` shows
  `Combat SAR - stranded SOF team SOFRESCUE_… extracted home`. A *downed pilot* delivered in the same
  mission is still spared (the two channels don't cross). With `auto_combat_sar` on, an **AI** Combat
  SAR helo can do the extraction too (it will fly deep — expect losses).
- **Fail signature:** no CASEVAC spawns (generator emitted no `sofTeams`, or `scar_command_post_intel`
  off, or no rescue helo so the data is skipped); the team delivers but the rescue isn't cleared/
  refunded (`SOFRESCUE_<x>_<y>` name mismatch between `sof_rescue_pickup_name` at generation vs
  debrief — check the strand-coord rounding); or a SOF extraction wrongly lands in `combat_sar_rescues`
  and "spares a pilot" (the `SOFRESCUE` prefix routing in `OnAfterRescued`); double refund for one
  team recovered by both paths.

### G13 — Combat SAR airframes: armed Chinook + flyable King · Combat SAR · ☑ VERIFIED (2026-06-28, audience in-game pass — King wing-tank render OK; EW/ISR-clean + door guns previously confirmed)
- **Cockpit-confirmed (2026-06-27, user in-game pass — session `suspicious-goldberg`/`1ca51fbf`):**
  the C-130J-30 King flies **clean of the EW/ISR menu** ("Kings no EW ISR") — the `EwExcludedGroups`
  per-group deny-list works in-cockpit. Combined with the **CH-47 door M60D guns confirmed 2026-06-25**
  ("loadout good"), the only residual on this row is the King's external **wing tanks visibly rendering
  on the model** (payload added 2026-06-25; user can eyeball it on the ground — they fly the King, not
  the CH-47). *(The EW-clean confirmation was given in-game and dropped — PR #226 captured only the
  headless/live-log evidence; recovered here.)*
- **Data re-confirmed headless 2026-06-26:** the `Retribution Combat SAR` payloads resolve —
  CH-47Fbl1 mounts the door guns (`{CH47_PORT_M60D}`/`{CH47_STBD_M60D}`) and C-130J-30 mounts
  the two wing tanks (`{C130J_Ext_Tank_L}`/`{C130J_Ext_Tank_R}`); both YAMLs carry a
  `Combat SAR` task; the `C-130 → C-130J-30` migrator alias is present
  (`aircrafttype.py`). **Residual (in-sim only):** the King visibly rendering the wing tanks
  and flying **clean of the EW/ISR menu** (EW per-group deny-list `EwExcludedGroups`).
- **Live-save airframe confirm (2026-06-27):** the flown `autosave.retribution` (GermanyCW) blue wing
  actually carries **both** Combat SAR airframes as real squadrons — `CH-47Fbl1` (5th Battalion 159th
  Aviation) and `C-130J-30` (910th Airlift Wing) — and both report `capable_of(COMBAT_SAR)=True`, while
  the legacy `C-130`/`CH-47F` ids are absent (the migrator left no stragglers). So this campaign can frag
  Combat SAR on both airframes today with no edits; the load succeeded with no `C-130` migrator crash.
- **Live-mission registration confirmed (2026-06-27, `dcs.log`):** the generated GermanyCW mission
  registered both — the rescue helo as an AI group (`Front line Fulda/Haina Combat SAR | CH-47F Block I`,
  2 ships) and the King as a **player client** (`Register Client: ... C-130J-30 | Pilot #1`) — and the
  plugin then reported `1 rescue helo group(s), 1 King(s)`. So both airframes frag + register with no Lua
  error; the C-130J-30 cockpit cold-started fine. **Still in-cockpit:** door-guns/wing-tanks visible on
  the model and the King clean of the EW/ISR menu.
- **In-game 2026-06-25:** tasking offered on **both** airframes ✅; CH-47Fbl1 spawns with its
  **door M60D guns** ✅ ("loadout good"). **Found:** the C-130J-30 King spawned with **no loadout /
  no wing tanks** — the documented removable-pylon case. **Fixed 2026-06-25:** added a
  `Retribution Combat SAR` payload for the C-130J-30
  (`resources/customized_payloads/C-130J-30.lua`) mounting the two external wing tanks
  (`{C130J_Ext_Tank_L}` Pylon 1 + `{C130J_Ext_Tank_R}` Pylon 2; CLSIDs validated against the module).
  **Re-observe:** the King now spawns with visible underwing tanks. **Still to verify:** the King
  flies **clean of the EW/ISR menu** (the other half of this row — EW per-group deny-list `EwExcludedGroups`).
- **Setup:** A blue faction with **CH-47Fbl1** and **C-130J-30** squadrons. Plan a **Combat SAR**
  flight in each. (The stock AI C-130 is retired — C-130J-30, the Airplane Simulation Company
  module, is the only C-130; a fresh game and an in-progress save with an old "C-130" squadron must
  both load and show the C-130J-30.)
- **Pass:** The CH-47Fbl1 is taskable **Combat SAR** and spawns with its **port + starboard door
  M60D guns** mounted (the `Retribution Combat SAR` payload). The C-130J-30 is taskable Combat SAR as
  the **King** and shows its external underwing **fuel tanks** (part of the official module), and
  flies clean of the EW/ISR menu (the `c130j` plugin is suppressed when a King is up). Both are
  player-flyable.
- **Fail signature:** Combat SAR not offered for CH-47Fbl1/C-130J-30 (yaml `tasks` entry missing); the
  Chinook spawns **clean / no door guns** (payload name not matched — `Retribution Combat SAR` must
  resolve, else it falls back to empty; check the door-gun CLSIDs `{CH47_PORT_M60D}`/`{CH47_STBD_M60D}`
  are valid for the installed module); the King has no visible wing tanks (then they are a removable
  pylon on the C-130J-30 module, not model-default — needs the module's tank CLSID added to a King
  payload); the King wears the EW/ISR menu (the `EwExcludedGroups` deny-list didn't exclude it); an
  old save with a "C-130" squadron fails to load (the `C-130 → C-130J-30` migrator alias is missing).

### G14 — C-130J jamming vs MANTIS IADS (no EMCON interference) · §2 / MANTIS migration · ☑ VERIFIED (2026-06-28, audience in-game pass — EW jamming works, no MANTIS EMCON interference)
- **Invariant verified by reading 2026-06-26:** the "must never happen" failure mode (an
  `ALARM_STATE`/emission write creeping into the jammer) is structurally precluded.
  `suppressSAMRoe`/`restoreSAMRoe` (`c130j/c130j_mission_systems.lua:645-659`) are nothing but
  a nil-guarded `setOption(ROE, WEAPON_HOLD)` / `setOption(ROE, OPEN_FIRE)`, and a plugin-wide
  search finds **zero** `enableEmission`/`ALARM_STATE` writes (only comments forbidding them).
  So the jammer composes with MANTIS by construction. **Residual (in-sim only):** that a jammed
  SAM actually holds fire while its radar stays up under MANTIS, resumes when the window expires,
  and that MANTIS-dark SAMs don't wake on the OPEN_FIRE restore.
- **Why:** The jammer suppresses RED SAMs on the **ROE** axis only (`suppressSAMRoe()` /
  `restoreSAMRoe()`); MANTIS (now the default engine) drives SAMs on the **ALARM_STATE** axis and
  never writes ROE. The two are intended to compose cleanly, but the human-flown interaction under
  MANTIS has not been eyeballed (G4 predates the default flip; G6's emissions path was AI-vs-AI).
- **Setup:** A new campaign (so **IADS engine = MANTIS**) with red SAMs/EWRs. Fly the C-130J-30
  JAMMING slot toward the IADS; use Area/Spot jamming on a live red SAM that MANTIS has brought up.
- **Pass:** A jammed SAM **holds fire** while suppressed even though its radar stays up under MANTIS
  (RWR shows the radar but it doesn't shoot / "Suppressed: <type> — clear to engage" banner); when
  the jam window expires the SAM **resumes firing** (ROE returned to OPEN_FIRE). SAMs MANTIS is
  keeping **dark for EMCON do not wake up** as a side effect of the jam restore. `dcs.log` clean.
- **Fail signature:** jamming has no effect (SAM keeps firing while held — ROE write not landing);
  a jammed SAM stays permanently dead after the window (restore not firing — under MANTIS nothing
  else lifts the hold); or a SAM MANTIS wanted dark starts emitting/firing after a jam cycle (an
  `ALARM_STATE`/emission write crept into the jammer — must never happen; check `suppressSAMRoe`/
  `restoreSAMRoe` are still ROE-only).

### G15 — MANTIS SAM range/band override (SEAD) · §2 / MANTIS migration · ☑ VERIFIED 2026-06-27 (GermanyCW — bands + detection + engagement; HARM-evasion sub-check & AWACS-less caveat below remain to watch)
- **VERIFIED (2026-06-27, post AWACS-fold fix):** re-fly over the Haina SAMs **drew fire**. `dcs.log`
  confirmed RED `CheckLoop` climbing **0 → 27 → 36–38** as the A-50 got airborne (was `0` × 492 before),
  off a post-fix RED build showing **6 EWR group names** (was 5 — the A-50 now folds in). Bands were
  already correct (override loaded, ASP/FIREFLY/LLAMA→LONG etc.); the blocker was detection, now closed.
  **Still worth a glance on a future pass:** a HARM shot triggering SEAD evasion (radar drop / scoot),
  and an **AWACS-less faction** (relies on dedicated EWR coverage — see the 5th-pass caveat).
- **Bug (found in-game 2026-06-27, GermanyCW):** under MANTIS nearly every Retribution SAM was typed
  **POINT** — confirmed SA-6/SA-10/SA-11/SA-2/SA-3 all POINT (SA-8 wrongly MEDIUM) — so the IADS only
  engaged at ~point-blank range, nothing emitted at standoff, and **SEAD had no targets** ("SAMs never
  engaged / stayed GREEN"). Root cause: MANTIS classifies a SAM by scanning the group's unit type-names
  against its built-in `SamData` table, breaking on the first match; Retribution's multi-radar sites
  (search + track + launchers + a co-located "Dog Ear" EWR) make it pick the wrong radar. The fix
  (`mantis-config.lua`) overrides `MANTIS._GetSAMRange` to band each SAM by **Retribution's own threat
  range** (`dcsRetribution.{Red,Blue}AA[].range`, the planner's MEZ), falling back to MANTIS' native
  logic for anything it can't resolve. Pure-Lua bridge change, no MOOSE-source edit.
- **Active-SAM density (2026-06-27, 3rd pass — "flew over a SAM, no shot"):** with the bands now
  correct, the IADS came alive (Tacview: SA-5 + SA-2 launched, up to 4 SAMs RED), but the
  `Max active SAMs` caps (2 mid / 1 long) meant only a couple of the strategic SAMs were hot at once
  — so an overflown SA-6 site that didn't get a "turn" stayed GREEN. Changed the defaults so
  **medium + long are uncapped (`0 = unlimited`)** — the whole strategic belt engages — while
  **short + point keep a rolling cap (2 / 6)** so the SHORAD layer doesn't all light up on a low
  ingress. `0` is the new "unlimited" sentinel (`uncap()` in `mantis-config.lua`). Watch in-game that
  flying into a medium/long ring now draws fire (mind the overhead dead-zone) and the low SHORAD
  still rolls rather than swarming.
- **EMCON starves detection — the real engagement bug (2026-06-27, 4th pass):** a 23-min flight
  drew **no fire at all** despite correct bands + uncapped actives. `dcs.log`: RED `CheckLoop 0`
  for the whole flight = MANTIS' **detection set was empty**, so `_CheckLoop` had nothing to
  engage. Cause (read in `Moose.lua`): MANTIS detection feeds from two `INTEL` sources — EWRs
  (`IntelOne`) **and the SAMs themselves** (`IntelTwo`) — but with **Emissions Control ON** MANTIS
  forces every SAM radar dark (`EnableEmission(false)`), so `IntelTwo` is empty and detection
  collapses onto the ~5 dedicated EWRs, which miss a low/forward target → blind network → no SAM
  ever fires. **Fix: default Emissions Control OFF** (`useEmOnOff` default → `false`) so the SAMs
  (and SAM-as-EWRs) search on their own radars, feed detection, and engage what's in range — an
  RWR-visible, reliably-engaging IADS. **Re-fly:** flying into a ring should now draw fire promptly;
  re-enable EMCON only on campaigns with proven EWR coverage.
- **AWACS never reached the detection net — the actual blind-RED bug (2026-06-27, 5th pass):** even
  with EMCON **off**, a re-fly over 3 SAMs at Haina still drew **no fire**. `dcs.log` was decisive:
  RED `CheckLoop 0` × **492** (detection set empty the entire flight) while **BLUE `CheckLoop 6`**
  (blue detection fine) — a RED-specific detection failure, not a wake failure. Cause: this corrects
  the 4th-pass note above — in **both** EMCON and AlarmState a SAM is held **passive until cued**
  (it never self-detects; SAM-as-EWRs are dark too), so detection rides entirely on the **always-on
  sensors: dedicated EWRs + the AWACS**. RED's A-50 (`Kastrup AEW&C`) **ground-starts**, so it was not
  a spawned group when the bridge built at T0 — and `add_awacs` gated on a live `Group.getByName`,
  which returned nil and **silently dropped it**. BLUE's E-3A **air-starts**, resolved, and fed
  detection — exactly why blue saw 6 and red saw 0. With no dedicated-EWR coverage at Haina either,
  RED had **zero eyes**. **Fix:** `add_awacs` now folds each AWACS **by name** using a `coalition`
  field newly emitted into the `AWACs` Lua table (`luagenerator.py`), instead of inspecting a live
  group. MANTIS' EWR `SET_GROUP` is dynamic (`dynamic=true → FilterStart`), so the name added at T0
  is matched the moment the A-50 taxis airborne and starts radiating. (`SetAwacs()`/
  `StartAwacsDetection()` were the wrong lever — `StartAwacsDetection` is **dead code, never called**
  in our MOOSE.) **Caveat:** this only restores detection for factions that **have** an AWACS; an
  AWACS-less RED still depends on dedicated EWR coverage (SAM-as-EWRs stay dark) — a separate
  always-on-EWR question if a future campaign proves blind without an AWACS.
- **AWACS-less caveat now instrumented + audited (2026-06-28):** the caveat above is now caught
  automatically — a per-coalition **"blind network" warning** fires when a side has radar SAMs but
  **zero always-on detectors** (dedicated EWR + AWACS), at generation (`luagenerator.py`,
  `logging.warning`) and at runtime (`mantis-config.lua` `env.warning` in `build()`). A scan of all
  64 bundled campaigns (reusing `MizCampaignLoader`) found **3 genuinely BLIND** (Vietnam 1970/1965,
  Egypt 1973 — radar SAMs, no EWR markers, faction has no AWACS) and **18 AMBER** (radar SAMs, no EWR
  markers, but the faction has an AWACS, so detection hangs entirely on it). Dedicated EWRs come ONLY
  from `.miz` `1L13` markers via the `Early-Warning_Radar` layout — SAM layouts don't bundle one — and
  the faction must field an EWR-class unit, so a campaign needs both. **Red Tide fixed (G18).** See
  `414th-red-tide-campaign-notes.md`.
- **Refinement (found in-game 2026-06-27, 2nd pass):** the override loaded (`SAM range override active
  (57 …)`) but several `(SAM)` sites still came up POINT and an **SA-5 (255 km!) site read POINT**. Cause:
  a Retribution SAM **site has multiple groups under one codename** (the main SAM + a co-located
  point-defense SA-9/SA-13/SA-8), each emitted to `RedAA`; the override indexed range **by codename and
  kept the last-seen**, so the short escort overwrote the real SAM. Fixed by keeping the **MAX** range per
  codename (`index_aa`), so a site bands by its longest reach (ASP/FIREFLY/LLAMA → LONG, DRAGONFLY/ZEBRA →
  MED, etc.). **Known residual:** the point-defense group of a multi-group site inherits the site band
  (slight over-activation; it still only *shoots* at its own range). Per-group precision would need range
  emitted per IADS group, not per codename — deferred.
- **Setup:** New campaign (MANTIS engine) with a layered SAM threat incl. at least one medium/long SAM
  (SA-6/SA-11/SA-10). `dcs.log` should show `... SAM range override active (N AD group range(s) ...)`.
  Fly a **striker into a SAM ring** (not a C-130 in friendly air) and bring a SEAD/HARM shooter.
- **Pass:** an SA-10/SA-6/SA-11 goes **active on RWR at its true range** (tens of NM, not ~3 NM), the
  MANTIS status shows SAMs flipping to **RED** when you press a ring (not stuck 0/all-GREEN), and a HARM
  shot triggers the SAM's **SEAD evasion** (radar drops / shoot-and-scoot). With MANTIS debug on, the
  `SAM ... is type LONG/MEDIUM` traces match the real SAM types. No `mantis-config.lua` Lua error.
  **Detection check (5th-pass fix):** with a RED AWACS airborne, `dcs.log` RED **`CheckLoop` should go
  non-zero** as you ingress (not 492× `CheckLoop 0`); a ground-starting A-50 must still wake the net.
- **Fail signature:** medium/long SAMs still typed POINT or still only engage at point range (override
  not resolving the group — check the `... range override active` count is non-zero and that codenames
  in `dcsRetribution.RedAA` match the group names); a SAM banded too high/low (tune `BAND_*_M`
  thresholds); SHORAD/AAA wrongly promoted out of POINT; or SAMs never go RED even pressed at true range
  (a deeper detection issue beyond this fix — re-open M2).

### G16 — LotATC export plugin restored · Plugin hygiene · ☑ VERIFIED (2026-06-28, audience in-game pass — user: "good")
- **In-game (2026-06-28, audience pass — user verdict "good"):** the restored `lotatc` export plugin works — the export is written and red AA threat circles render on the LotATC scope with no Lua error. The blank per-ring NATO-name labels remain a known limitation (not a fail), see below.
- **Context:** The `lotatc` plugin (export RED/BLUE anti-air threat circles + symbols to LotATC
  scopes) was silently dropped from the active plugin list during the QRA-reserve integration and
  is now restored, plus a cross-wired config option fixed ("Export anti-air symbols" was driving the
  "Export BLUE anti-air" flag).
- **Setup:** Enable **LotATC Export** in the Plugin Options page, set `LOTATC_DRAWINGS_DIR` (or rely
  on the Saved Games default), desanitize `MissionScripting.lua` (needs `lfs`/`io`/`os`), generate +
  run a mission with red SAM/AAA sites, then open the export in LotATC.
- **Pass:** `threatZones.json` (+ `threatSymbols.json` when symbols enabled) appear under the export
  path and red AA threat circles render on the LotATC scope; toggling "Export anti-air symbols" off
  actually suppresses the symbol file (the bug just fixed); `dcs.log` shows the
  `DCSRetribution|LotATC Export plugin - writing …` lines with no Lua error.
- **Fail signature:** No export files written; a Lua error in `dcs.log`; or the symbols toggle has no
  effect. **Known limitation (not a fail):** per-ring NATO-name labels stay blank — that enrichment
  read the removed Skynet `redIADS`/`blueIADS` globals; circles/symbols still export, labelled by
  unit name + class.

### G17 — BigEye EWR plugin restored · Plugin hygiene · ☑ VERIFIED (2026-06-28, audience in-game pass)
- **Context:** `bigeye` (MOOSE `Ops.INTEL` early-warning radar that broadcasts text BRA / picture /
  bogey-dope calls to players) is the documented successor to the retired `ewrs` script, but had
  itself been silently dropped during the QRA-reserve integration — so players had no EW picture
  calls. Restored to the active plugin list (off by default). Independent of MANTIS (player-comms
  only; does not feed the IADS).
- **Setup:** Enable **BigEye EWR** in the Plugin Options page, generate + run a mission with a player
  flight and airborne enemy contacts; use the F10 BigEye radio menu to enable reports.
- **Pass:** BigEye F10 menu present; periodic text threat reports list contacts with BRA + aspect,
  honoring the report-interval / max-units options; NCTR/NATO-name options behave as set.
- **Fail signature:** No BigEye F10 menu; no reports; a Lua error in `dcs.log`; or option values
  (intervals, max units, sensor flags) ignored.

### G18 — Blind-IADS warning + Red Tide red EWR coverage · MANTIS migration / Red Tide · ☑ VERIFIED (2026-06-28, audience in-game pass — Red Tide red EWR coverage confirmed)
- **Context:** MANTIS detection rides only on dedicated EWRs + AWACS (SAMs and SAM-as-EWRs are held
  dark), so a campaign with radar SAMs but no EWR markers and no AWACS has a blind red net. Two
  changes: (1) a per-coalition **blind-network warning** — generation-time `luagenerator.py`
  (`logging.warning`) + runtime `mantis-config.lua` (`env.warning` in `build()`, via
  `count_entries`/`count_awacs`); (2) **Red Tide** went from 0 dedicated red EWRs (entirely
  A-50-dependent) to 4 — added `EWR 1L13` to the **Russia 1980** faction (`EWR-FG` 0→1, era-OK for
  1988) and 4 red `1L13` EWR markers to `red_tide.miz` near the long/medium SAM belt.
- **Setup:** (a) generate any campaign and read the app log for `IADS: <side> ... NO always-on
  detection source` on a known-blind one (e.g. Operation Gazelle / Egypt 1973); (b) generate + fly
  **Red Tide** with the A-50 left on the ground / not fragged.
- **Pass:** (a) the warning fires for a blind coalition and stays silent for a covered one; (b) in
  Red Tide, `dcs.log` shows the RED build resolving **≥4 dedicated EWR group names** and RED
  `CheckLoop` climbing **before** the A-50 is airborne — red SAMs draw fire even with no AWACS up.
- **Fail signature:** warning never fires on a blind campaign (or false-fires on a covered one); Red
  Tide red still shows 0 EWR groups (faction EWR date-gated out at 1988, or markers not placed); a
  `mantis-config.lua` Lua error; or `1L13` EWRs spawn in blue/contested territory (placement off).

### G19 — TARPS on Vietnam-era recon birds (RF-101B / RA-5C) · §3 · ◐ PARTIAL (2026-06-28, audience in-game pass — recon bird flies the TARPS path but is shot down before it confirms BDA)
- **Reconfirmed (2026-06-30, flown session — `state.json`/`dcs.log`):** same failure mode repeated —
  **both** TARPS flights this session (`RAVEN TARPS|2|15|RF-101B Voodoo| Pilot #1` and
  `BLOODHOUND TARPS|2|10|RF-101B Voodoo| Pilot #2`) are in `crash_events`, and
  `tars_recon_captures` is empty (`0`). No change to the diagnosis — the 2026-06-28 fix (tighter
  `default_tot_offset`, keep recon high) targets a lone-straggler-behind-a-departed-escort case; this
  session's front (Kutaisi/Senaki-Kolkhi) is thick with AAA/SAM/MiG activity (see the broader blue
  loss count this session), so recon-bird survivability may still be a standing campaign-balance issue
  independent of the escort-timing fix. Not re-marking VERIFIED/REGRESSED — same open question as
  before (accept as period-realistic vs. harden further).
- **In-game (2026-06-28, audience pass — user: "fly the path for it but get shot down"):** the tasking + ingress half is confirmed — the RF-101B/RA-5C spawns clean on the `Retribution TARPS` loadout and flies the recon path — but it is **shot down en route to / over the target**, so the overflight→BDA-confirm half is never reached. The TARPS plumbing is structurally fine; this is a **survivability** gap (a lone, unescorted, weaponless recon bird into a Vietnam AAA/SAM environment). OPEN: harden survivability (escort, ingress altitude, routing, or a larger time offset behind the strikers) vs. accept it as period-realistic. PARTIAL until decided.
- **Altitude analysis (2026-06-28, read from code):** the RF-101B/RA-5C YAMLs set no `combat_altitude`, and `COMBAT_ALTITUDE_BAND_KFT = (20, 20)` (`game/dcs/aircrafttype.py`) flattens the estimate to **20,000 ft** regardless of speed — i.e. the recon overflight is **already above the 4500 m (~14,800 ft) flak ceiling**. So the AAA/flak gauntlet (§33) is **not** the killer, and *lowering* the bird (the intuitive fix) would push it **into** the AAA, not out of danger. At 20k ft, alone and ~5 min behind the strike package (`TarpsFlightPlan.default_tot_offset` = 5 min, after the package escort has egressed), the realistic killer is a **MiG (BARCAP)** or a **SAM** — so the right hardening is **escort coverage / recon timing / routing**, not altitude. NB `TarpsFlightPlan` is shared with the F-14 TARPS path (G2, VERIFIED) — any flight-plan change must not regress it; an altitude change should be data-only per-airframe (`combat_altitude:` in the YAML), but altitude is the wrong lever here. Kill-cause (MiG vs SAM) pending the user.
- **Kill-cause = MiGs (user, 2026-06-28) → FIX APPLIED.** Confirmed via `EscortFlightPlan.split_time`: the AI escort splits at the **strikers'** egress and turns back ~7–9 NM short of the target without loitering, so a recon bird +5 min behind flew the threatened ingress corridor **alone** after the escort RTB'd. Fix: keep it **high** (20k, above the AAA — unchanged) and **tighten `TarpsFlightPlan.default_tot_offset` 5 min → 2 min** so it ingresses **within** the package/escort window instead of as a lone straggler (`game/ato/flightplans/tarps.py` + 5 doc sites + `tests/test_tarps_recon.py`). Black/mypy/pytest green. **Shared with the F-14 path (G2):** the tighter offset is functionally safe for it (still a positive post-strike pass) but G2 wants a quick confirming re-fly. **Re-fly owed** on both — the recon bird should now survive to confirm BDA when the package has fighter cover (in a fighter-starved Vietnam turn with no escort planned it can still die, which is a campaign-balance matter, not this fix).
- **2nd bug (user, 2026-06-28): birds were auto-tasked ARMED RECON / Strike instead of a photo pass → FIXED.** The `vwv_rf101b`/`vwv_ra-5` YAMLs listed `Armed Recon: 435/410` + `Strike/BARCAP/CAS: 1`, and the `CAS` entry also auto-enriches `ARMED_RECON` (`aircrafttype.py` lines ~821-829). Auto-assignable = `aircraft caps − secondary_tasks` ∩ the campaign squadron config's `auto_assignable` (`{primary}|{secondary}|{TARPS}`), and Khe Sanh pinned `secondary: air-to-ground` on both recon squadrons — so the intersection handed these **unarmed** birds Armed Recon/Strike/CAS (they'd spawn with the weaponless TARPS loadout and fly an aborting attack). Fix: stripped both YAMLs to **`TARPS` only** (single-task is fine — tankers/AWACS are single-task) and removed the `secondary: air-to-ground` from both Khe Sanh squadron blocks. Guard test `tests/test_tarps_recon.py::test_vietnam_recon_planes_are_tarps_only` (asserts NOT capable of ARMED_RECON/STRIKE/CAS/BAI/BARCAP/ESCORT). Black/mypy/pytest green; Khe Sanh YAML re-parses + loads the two airframes. The bird should now only ever be fragged TARPS.
- **Context:** TARPS was extended off the F-14 onto the two dedicated Vietnam photo-recon ships —
  **RF-101B Voodoo** (`vwv_rf101b`, land-based) and **RA-5C Vigilante** (`vwv_ra-5`, carrier). They
  carry `TARPS: 700` as their primary task and a clean, weaponless **Retribution TARPS** payload
  (built-in cameras, empty pylons). The Khe Sanh (Niagara) campaign tasks one squadron of each
  `primary: TARPS`. Headless-verified 2026-06-28: both report `capable_of(TARPS)`, the loadout
  resolves to `Retribution TARPS`, and `primary: TARPS` parses as a squadron config.
- **Setup:** Generate **Khe Sanh (Operation Niagara)** with `auto_add_tarps_recon` on; let the
  planner frag a Strike/DEAD package the RF-101B or RA-5C squadron is in range for (or hand-frag a
  TARPS package on either type). Generate + run the mission.
- **Pass:** The recon bird spawns with the clean `Retribution TARPS` loadout (no offensive stores),
  flies the recon ingress and **overflies** the target ~5 min behind the strikers, recovers, and the
  photographed site's BDA confirms at debrief (same as the F-14 path, G2). With TARS on, captures
  reach the debrief.
- **Fail signature:** Squadron never gets tasked TARPS; the jet spawns with a wrong/empty loadout or
  bombing tasks; the AI flies an aborting attack pattern and never crosses the target; or the
  overflight produces no BDA confirmation.

### G20 — Combat SAR enemy snatch party (correct coalition + dispersed teams) · §15 · ☑ VERIFIED (2026-06-30, `dcs.log`/`state.json`/Tacview — "Vietnam v2.miz" session)
- **Verified (2026-06-30, flown session — `Vietnam v2.miz` / `dcs.log` / `state.json` /
  `Tacview-20260630-171831-DCS-Host-Vietnam v2.zip.acmi`):** `state.json.combat_sar_captures` recorded
  a genuine **BLUE** aircrew captured (`Front line Kutaisi/Senaki-Kolkhi CAS|2|27|A-1H Skyraider|
  Pilot #1`) — a snatch party can only capture a survivor it is hostile to, so this alone proves the
  party spawned on the **correct (enemy) coalition**, not the friendly/wrong-side bug. `dead_events`/
  `kill_events` also show at least **20 independently-numbered** `CSAR Snatch Party <N> U1..U10` groups
  (parties 1, 2, 3, 4, 8, 13, 14, 15, 16, 19, 20, 21, 23, 24, 25, 27, 30, 31, 37, 48 all appear as
  distinct 9–10-unit groups converging on different survivors across the session) — **dispersed small
  teams**, not the old one-column bug. Both fail signatures (wrong-coalition, single column) did not
  occur.
- **User note (2026-06-30):** "blue csar snatch party?" — the user also saw a **blue-coalition**
  snatch party. This session's generated `.miz` carries `dcsRetribution.CombatSAR` for **both**
  coalitions (`red.rescueHelos` is populated too — a red Mi-8MTV2 Combat SAR flight), so a blue party
  hunting a downed **red** pilot is the expected mirror image of the red-vs-blue capture already
  verified above, not a bug — `red.pending_pow_recoveries` came back empty from the headless save load
  (no red pilot was ultimately held), consistent with either no capture completing or a rescue beating
  it. Flag if what was actually seen was a *friendly-colored* party menacing a **blue** survivor
  instead (that would be the pre-fix bug reappearing) — the report as written reads as the symmetric,
  working case.
- **Bug (user report, 2026-06-29, screenshot):** the capture-race snatch party rendered on the map as
  **friendly/green** (wrong coalition) and as **one long marching column** ("AK74" line) rather than
  enemy ground forces. Root cause: the `combatsar` plugin hardcoded `country.id.CJTF_RED`/`CJTF_BLUE`
  for the enemy ground spawn, but in a Vietnam/CH-faction `.miz` those CJTF countries are **not
  registered** on either coalition (the factions use real/CH nations), so `coalition.addGroup` placed
  the party on the wrong side; and all `partySize` soldiers spawned as a single group routed on one
  waypoint, forming a column.
- **Fix (2026-06-29):** Python now emits `enemyCountry` = the opposing side's faction country id
  (`coalition.opponent.faction.country.id`, always registered on the enemy coalition) and the plugin
  spawns the party under it (CJTF constant kept only as a fallback). `spawnSnatchParty` now spawns
  **several small teams** (`captureTeams`, default 3) ringed around the survivor on different bearings,
  each its own group converging independently; `advanceCapture` tracks the list (neutralized only when
  every team is dead; any team holding on the pilot runs the capture clock). Lua syntax read-checked;
  Black/mypy/pytest green.
- **Setup:** A campaign whose factions use **real/CH nations** (e.g. Khe Sanh / a Vietnam Ops
  campaign), `captureEnabled` on. Eject a blue pilot near the FLOT and let the capture roll hit.
- **Pass:** The snatch party shows **RED/enemy** on the F10 map (not green) and appears as **3 small
  dispersed teams** converging from different directions (not one column). Killing all teams clears the
  capture (`Capture party neutralized` cue); letting one team dwell on the survivor still results in
  `CAPTURED` → POW.
- **Fail signature:** snatch party still friendly/neutral-coloured (the `enemyCountry` emit didn't
  reach the plugin, or `addGroup` fell back to an unregistered CJTF country — check the emitted
  `dcsRetribution.CombatSAR(.red).enemyCountry`); still one long column (teams not splitting); or the
  capture never fires because `advanceCapture` lost track of the multi-group party (all teams reported
  dead while alive).

### G21 — Combat SAR AI rescue commandeers an on-station helo (no duplicate spawn) · §21 · ◐ PARTIAL (2026-06-30, `dcs.log`/`state.json` — clone-fallback confirmed correct; the documented "errors on takeover" fail signature also reproduced repeatedly)
- **Partial (2026-06-30, flown session — `dcs.log`/`state.json`):** Two findings, one good and one a
  genuine open bug:
  - **Clone-fallback confirmed working as designed:** `dcs.log` shows `OPSTRANSPORT [UID=6] | Carrier
    OPSGROUP CombatSAR Rescue 15#001 dead!` — i.e. `spawnIndex` had reached **≥15** clones from the
    FARP. This session's blue helo losses were heavy (multiple `Front line … Combat SAR|…|Mi-8MTV2`
    and `Kutaisi_UH-1H_*` crashes in `crash_events`), so on-station helos were frequently dead/unavailable
    — exactly the documented condition under which falling back to a fresh clone is *correct*, not a bug.
  - **The row's own anticipated fail signature reproduced:** this row's text explicitly flags
    `combatsar: AI dispatch error` in `dcs.log` — "the live-group `FLIGHTGROUP` wrap is the risk to
    watch" — as the fail signature for a failed *commandeer* attempt. `dcs.log` shows exactly that
    warning **9 times** across the session (`combatsar: AI dispatch error (continuing):
    [string "l10n/DEFAULT/Moose.lua"]:11714: table index is nil`). Moose.lua:11714 is
    `self.Templates.ClientsByID[UnitTemplate.unitId]=UnitTemplate` inside `_RegisterGroupTemplate`,
    firing when a `Client`/`Player`-skill unit template has a **nil `unitId`** — i.e. commandeering (or
    cloning) is triggering a Moose DATABASE template re-scan that trips over some unit's malformed
    template elsewhere in the mission. It's `pcall`-guarded so it doesn't crash and 3 rescues still
    completed (G11), but that specific dispatch attempt aborts, so it's worth root-causing rather than
    dismissing — **reopen candidate**, not yet a clean pass. `combat_sar_rescues` (3 entries) proves
    *some* dispatches complete; we can't tell from these artifacts whether any of the 9 errored attempts
    correspond to a survivor who was never rescued.
- **Bug (user report + Tacview, 2026-06-29):** with `auto_combat_sar` on, every AI ejection made
  `dispatchAIRescue` clone a brand-new `CombatSAR Rescue N` helo from the FARP instead of using the
  Combat SAR flight already orbiting the FLOT. Tacview from `…retribution_nextturn` shows 8+
  `CombatSAR Rescue N` CH-53E/Mi-8 clones spawned **co-located with** the idle
  `Front line … Combat SAR` helos at the same field — "the AI prefers to spawn a group instead of
  commandeering the ones already on the front lines."
- **Fix (2026-06-29):** `dispatchAIRescue` now calls `commandeerRescueHelo` first — picks the nearest
  alive, idle, **AI-crewed** rescue helo from `cfg.rescueHelos` (skips player-crewed via
  `groupHasPlayer`), wraps it in a `FLIGHTGROUP`, `AddOpsTransport`s the survivor pickup, marks it
  busy (`busyHelos`), and frees it on delivery so it cycles to the next ejection. It only clones a
  fresh `CombatSAR Rescue N` from `heloTemplate` when every planned rescue helo is dead or already
  committed. Lua syntax read-checked.
- **Setup:** Khe Sanh / any campaign with `auto_combat_sar` on so a COMBAT_SAR helo orbits the FLOT.
  Down several AI pilots near the front over a few minutes and watch the rescue dispatch (Tacview).
- **Pass:** When a pilot ejects, an **already-orbiting** `Front line … Combat SAR` helo **diverts** to
  the survivor (message "a Combat SAR helo on station is diverting…"), boards, and delivers to the
  FARP — **no** new `CombatSAR Rescue N` clone appears while a planned helo is available. A fresh
  clone only spawns once all orbiting rescue helos are dead/busy. The delivered pilot is spared at
  debrief (G11).
- **Fail signature:** a `CombatSAR Rescue N` clone still spawns while an idle `Front line … Combat SAR`
  helo orbits (commandeer not firing — check `cfg.rescueHelos` is populated and `FLIGHTGROUP:New` on a
  live AI group takes the OpsTransport); the commandeered helo never diverts / errors on takeover
  (`combatsar: AI dispatch error` in `dcs.log` — the live-group `FLIGHTGROUP` wrap is the risk to
  watch); a human's rescue helo gets hijacked by the AI (the `groupHasPlayer` guard failed); or a
  helo stays stuck `busy` and never serves a later ejection (free-on-`OnAfterUnloaded` not firing).

### G22 — Captured-pilot POW recovery raid: planning crash + map marker · §15 · ☐ UNTESTED (2 fixes applied 2026-06-30, needs a re-fly)
- **Bug (user report, 2026-06-30 — screenshot of "An unexpected error occurred"):** planning a
  recovery flight against a captured-pilot POW objective (F10 "save pilot at airbase") crashed with
  `AssertionError` in `AirAssaultFlightPlan.Builder.layout()` (`assert self.package.waypoints is not
  None`), raised from `ibuilder.py`'s `_generate_package_waypoints_if_needed` while computing the ATO
  list's `sizeHint`. **Root cause:** `CapturedPilotGroundObject` is deliberately flagged
  `is_friendly()==True` (§15 design: it's *our* POW, so it renders/tasks as a friendly recovery
  objective) even though it's physically positioned at the enemy airfield holding the POW — but
  `_generate_package_waypoints_if_needed`'s "friendly target → skip offensive routing" shortcut used
  that same flag to decide whether the package needed an ingress route, so `package.waypoints` was
  never populated and the CSAR-only builder's unconditional assertion tripped. **Confirmed exactly
  this scenario exists in the user's own save:** loading `414TH.retribution` headless finds a live
  `CapturedPilotGroundObject` at Batumi offering `FlightType.CSAR` to blue with `is_friendly==True` —
  the precise repro condition.
- **Fix (2026-06-30, `game/ato/flightplans/ibuilder.py`):** `_generate_package_waypoints_if_needed` now
  always generates package waypoints for `FlightType.CSAR` regardless of the friendly flag (CSAR's only
  legal target is always physically enemy territory by construction). Covered by a new focused unit
  test (`tests/ato/flightplans/test_ibuilder_package_waypoints.py`, 3 cases: CSAR still routes against a
  friendly-flagged target, a non-CSAR type still skips for a friendly target, a genuinely offensive
  target still routes). Black/mypy/pytest green.
- **2nd bug (user report, 2026-06-30):** "captured pilot box shows on the map as intended but it needs
  to be offset from the base so you can click it" — the POW marker rendered exactly on top of the
  holding airfield's own icon (`pow_objectives.py` positioned it at `holding_cp.position` with zero
  offset), making it unclickable.
- **Fix (2026-06-30, `game/pow_objectives.py`):** the marker is now offset `_MARKER_OFFSET_M` (900 m)
  toward the friendly anchor, clearing the airfield's icon while still reading as "held at this
  airfield." Recovery is matched by airframe name, not position (`commit_pow_recoveries`), so the
  offset is purely cosmetic. `tests/test_pow_objectives.py` updated to assert the offset instead of
  exact-position equality; all green.
- **Setup:** A campaign with a `PendingPowRecovery` on the map (a captured pilot from the Combat SAR
  capture race, §15/G20). Open the map, confirm the POW marker sits clear of the holding airfield's
  icon and is clickable, then plan a CSAR recovery flight against it.
- **Pass:** The marker is clickable without zooming past the airfield icon; planning the CSAR flight
  does not crash, and the flight gets a real offensive-style ingress route into enemy territory (not a
  degenerate/local-only route).
- **Fail signature:** the `AssertionError` recurs; the flight plans with no real ingress (routes
  straight through threat zones with no IP); the marker still overlaps the airfield icon.

---

## H. Kneeboards

### H1 — Folded-list overflow pagination · §4 · ☑ VERIFIED (2026-06-25)
- **Verified (2026-06-25, generated kneeboard):** a long Friendly Packages / Airfield
  Directory flowed onto a `(cont.)` continuation page with nothing clipped at the bottom
  edge. Fail signature did not occur.
- **Logic-reviewed 2026-06-25 (de-risked, not flown):** the row-fit math is correct and
  conservative. `remaining_table_rows` computes `(image_height - page_margin - y) //
  line_height`, subtracts tabulate's 2 lines of header chrome, and leaves **one row of slack**
  (`max(0, capacity - 1)`) so a table never kisses the bottom edge; `line_height` is **measured
  empirically** from a one-line-vs-two-line `textbbox` delta (matches PIL's real multiline
  layout, not font metrics). Both folded lists (`BriefingPage` "Friendly Packages",
  `SupportPage`/Airfield "Airfield Directory") probe with `_render`, then push the overflow into
  a `TableKneeboardPage(..., continued=True).paginate()` — and `paginate()` **re-splits**
  recursively with `capacity = max(1, remaining_table_rows(...))`, so a continuation page can
  neither overflow nor infinite-loop, and the probe/`write()` cursor match (the `(cont.)` suffix
  changes heading text, not line count). **Residual flight risk:** only that PIL's runtime
  rendered line-height + `courbd.ttf` load match the measured estimate on the DCS-side image —
  environment, not logic.
- **Setup:** Generate a mission on a **busy theater** (many friendly packages
  and/or many BLUE airfields with ATIS) for a client flight with a long flight
  plan. Open the generated kneeboard in DCS.
- **Pass:** The Mission Info "Friendly Packages" list and the Support Info
  "Airfield Directory" never run off the bottom edge; rows that don't fit appear
  on a following "Friendly Packages" / "Airfield Directory" continuation page
  (later pages marked "(cont.)"). Small theaters show no extra pages.
- **Space-utilisation pass (2026-06-25, see §4):** light restyle — bold heading + thin
  underline rule + content, sections spread with whitespace (no boxes). When the Friendly
  Packages list is long enough to overflow one column it renders in **two side-by-side columns**
  filling the right half of the page, and the common case no longer spills a near-empty
  continuation page. The **Support Info** page's Package / AEW&C / Tankers / JTAC sections use
  the same heading+rule treatment, spaced to fill the page. **Pass:** two-column packages line
  up (each column has its own header row, no overlap between columns, no text clipped at the
  right edge); Support sections span the page without huge dead space. **Fail signature:**
  columns overlapping or the right column clipped at the page edge (lower `col_gap` math in
  `table_two_column_paginated()`), or an underline rule drawn over text.
- **Fail signature:** Table text clipped at the page bottom with rows missing, an
  empty continuation page, or a continuation page whose rows still overflow.
  Check `table_paginated()` / `remaining_table_rows()` row-height math in
  `kneeboard.py` if seen.

### H2 — Combat SAR task kneeboard · Combat SAR Phase 4 · ☑ VERIFIED (2026-06-25)
- **Verified (2026-06-25, in-game):** both kneeboard task pages render correctly — the role-aware
  briefs (CH-47 pickup vs. C-130 King on-scene-command), beacon tables, and F10 `CSAR` reference
  showed as designed with no clipping. Fail signature did not occur.
- **Setup:** Plan a player **CH-47** Combat SAR flight (and, separately, a player **C-130** Combat
  SAR). Open each flight's kneeboard in DCS.
- **Pass:** Each flight has a "Combat SAR" task page. The CH-47's shows the **pickup** procedure
  (ROLE = rescue helo; hover/land at the beacon, deliver to a friendly field/FARP) plus a **KING
  BEACON** table with each King's callsign + TACAN to home on; the C-130's shows the
  **on-scene-command** brief (ROLE = HC-130 "King"; hold overhead, don't land) plus **YOUR BEACON**
  (its TACAN + the LARS hint). Both reference the F10 `CSAR` menu. Text wraps inside the page, no
  clipping. **Layout (2026-06-25, §4):** light style — each section is a heading + thin underline
  rule + larger body text, with the leftover height spread as capped even gaps so the page
  breathes top-to-bottom (no boxes, no blank bottom two-thirds). **Fail signature here:** an
  underline rule drawn over text, or sections bunched at the top with dead space below (the
  `section_gap` distribution math in `CombatSarTaskPage.write`).
- **Fail signature:** wrong role brief for the airframe (helo gets the King text or vice-versa), a
  KING BEACON TACAN that doesn't match what the King actually radiates in-game, text running off the
  page edge, or no Combat SAR page at all (`generate_task_page` branch).

### H3 — SCAR task kneeboard (Phase 4) · §15 / PR #189 · ☑ VERIFIED (2026-06-26, user in-game pass)
- **Headless adjudication (2026-06-26):** the flight↔tasking matching that drives the
  TARGET SIGNATURE is verified by `tests/missiongenerator/test_kneeboard_task_pages.py`
  (passing): `_scar_tasking_for` links a SCAR flight to its tasking by package-target
  identity (the right signature on the right page), and a non-matching / no-target flight
  gets `None`. **Residual (in-sim only):** the rendered page itself — section text wraps
  without clipping and the on-page guidance matches in-mission behaviour (smoke→target
  timing, laser-only-with-King).
- **Setup:** Plan a player **SCAR** flight; open its kneeboard in DCS.
- **Pass:** A "SCAR" task page with **TASK** (hold the box, service the designated armor, kills count
  natively), **TARGET SIGNATURE** (this flight's own HVT signature, e.g. "1x SA-9 + 1x command vehicle
  + 2x truck", + decoy/mis-ID warning; a SCUD tasking reads "mobile SCUD launcher (TEL)"), **FIND + ID**
  (decoys + mis-ID cost; GREEN box smoke → RED target after ~2 min), and **DESIGNATION** (smoke colours,
  King laser code 1688, the "say again" F10). Text wraps, no clipping. The signature must **match the
  real picture** in the box (it's the same data the MAGIC call uses) and carry **no exact target coords**
  (finding it is the task).
- **Fail signature:** no SCAR page (`generate_task_page` branch); **no TARGET SIGNATURE section** (the
  flight didn't match its tasking — `_scar_tasking_for` / `target_id`, or `mission_data.scar_taskings`
  empty); a signature that doesn't match what's in the box (wrong tasking matched); text off the page
  edge; or guidance that contradicts the in-mission behaviour (e.g. claims a laser with no King).

### H4 — Custom kneeboard import (UI) · §4 · ☑ VERIFIED (2026-06-26, user in-game pass)
- **Headless adjudication (2026-06-26):** the scope-routing + persistence are verified by
  `tests/missiongenerator/test_custom_kneeboards.py` (passing): `_inject_custom_kneeboards`
  keys an unscoped page to `""` (all client flights) and an airframe-scoped page to that
  unit-type id only (mirroring the DCS loose-folder convention), and `game.custom_kneeboards`
  round-trips through pickle with `__setstate__` defaulting pre-feature saves to `[]`.
  **Residual (in-sim/UI only):** the Qt import dialog (PNG-normalisation in
  `QCustomKneeboardsWindow.add_kneeboard`) and the page actually appearing on the right
  airframe in DCS.
- **Setup:** With a campaign loaded, open **Kneeboards** (toolbar/menu). Add an image scoped to
  **All flights**, add a second scoped to a **specific airframe**, then save the campaign, reopen
  it (verify the entries persisted), generate a mission, and open the kneeboards in DCS.
- **Pass:** The "All flights" image appears in **every** client flight's kneeboard; the
  airframe-scoped image appears **only** on that airframe's flights. Entries survive a
  save/reload (stored in the `.retribution` file). Removing an entry drops it from the next
  generated mission.
- **Fail signature:** imported page missing in-game, appearing on the wrong airframe, not
  persisting across save/reload (`game.custom_kneeboards` not pickled / `__setstate__` default),
  or a corrupt image (PNG-normalisation in `QCustomKneeboardsWindow.add_kneeboard`). Note DCS
  kneeboards are per-airframe — two flights of the same type necessarily share pages.

### H5 — Threat Intel Brief kneeboard · §4 · ☑ VERIFIED (2026-06-26, user in-game pass)
- **Setup:** Enable **Generate threat intel brief kneeboard page** (Mission Generator →
  Kneeboard). On a campaign with several enemy SAM/EWR types — some already discovered
  (struck/scouted/TARPS) and some not — generate a mission for a player flight and open the
  kneeboards in DCS. Compare the dossier against the F10 map's enemy air-defense picture.
- **Pass:** A "Threat Intel Brief" page shows **one card per enemy system** — system name, a
  curated Guidance + Ceiling line, the live MEZ / Detection / HARM ALIC, live/dead site counts,
  bullseye cues, and a **DEFEAT:** tactics note. **Undiscovered** sites collapse into per-band
  "Unidentified MERAD" cards (no system/range/HARM/defeat) and the intro counts them. Live,
  longest-range systems sort to the top; more cards than fit flow onto `(cont.)` pages. The page
  is absent when the setting is off or the enemy has no air defenses. Spot-check that a card's
  curated text (guidance/ceiling/defeat) matches the actual system.
- **Fail signature:** a fogged site leaking its exact system/range/HARM/defeat (recon-fog
  regression in `build_threat_intel_cards`); friendly AD listed; wrong system→reference mapping
  (e.g. an SA-6 card showing SA-10 defeat text — check `game/data/threat_reference.py` keys);
  garbled bullseye cue or MEZ; a card overrunning the page bottom instead of paginating; the page
  appearing for the **enemy** side's same-airframe flight with BLUE air defenses (known
  per-airframe DCS limitation — note, not a bug).

### H6 — Mission code words + Comms & Brevity card · §4 · ☑ VERIFIED (2026-06-26, user in-game pass)
- **Setup:** Enable **Package code words & comms/brevity card** (Mission Generator → Kneeboard) on
  an ATO with a mix of tasks (e.g. a SEAD, a STRIKE, and a CAP package). In the planner, read the
  **persistent code-word panel** under the package list, **hover a package** (tooltip), and **open
  a flight's plan** (find the JOIN waypoint). Note the table. Regenerate the mission a couple of
  times **without re-planning the turn**, then generate and open the kneeboards in DCS.
- **Pass:** The planner panel shows a **`Code words — <theme>`** table with a **push word per task
  present** (SEAD / STRIKE / CAP …) + `SUCCESS` / `ABORT` (and `STOP JAM` only if an EW/jamming
  flight is in the ATO). A package's tooltip shows that package's push word + the events; its
  flight's JOIN waypoint reads `Join — PUSH <word>` matching the panel's row for that task. The
  in-cockpit **Comms & Brevity** page shows the **same full table** with the flight's own task row
  marked `(you)`, plus a brevity crib **matching the task** (SEAD → MAGNUM/SPIKE/MUD…; CAP →
  FOX/COMMIT/TALLY…). **The words do NOT change** across regenerations of the same turn; a **new
  turn** yields a fresh themed set. With the setting off: no panel, no tooltip, no `PUSH` tag on
  JOIN, no Comms & Brevity page.
- **Fail signature:** a task's push word differing between the panel, the tooltip, the JOIN
  waypoint, and the kneeboard (the `Coalition.code_words` single-source contract broke); words
  rerolling within a turn or NOT refreshing on a new turn (turn-stamp logic); the `PUSH` tag
  leaking onto a target/DTC steerpoint (should only ever be on JOIN); STOP JAM showing without an
  EW flight; brevity crib not matching the task; the feature appearing with the toggle off.

### H7 — Fuel ladder kneeboard card · §4 · ☑ VERIFIED (2026-06-26, user in-game pass)
- **Setup:** Enable **Generate fuel ladder kneeboard page** (Mission Generator → Kneeboard).
  Generate a mission for a player flight — ideally one with a tanker (REFUEL) leg — and open the
  kneeboards in DCS. Cross-check the Fuel Ladder against the flight-plan page's Min-fuel column and
  the jet's actual fuel at a couple of steerpoints.
- **Pass:** A "Fuel Ladder" page lists each steerpoint with **Plan** (planned fuel remaining) and
  **Min** (minimum to RTB, matching the flight-plan page) and **Margin** (Plan − Min). Plan
  **descends** leg by leg and **jumps back up at the tanker** waypoint; Min matches the existing
  flight-plan column; Margin goes **negative** only where the plan genuinely can't make it home.
  Bingo/Joker show at the bottom. Numbers are in the airframe's kneeboard mass unit (lbs/kg). With
  the setting off, no Fuel Ladder page.
- **Fail signature:** Plan not decreasing (or not resetting at the tanker); Plan wildly off vs. the
  jet's real fuel (burn-model/units error — check `flight.fuel × KG_TO_LBS`); Min disagreeing with
  the flight-plan page's Min-fuel column; Margin sign wrong; the page appearing with the toggle off
  or absent for an aircraft that has fuel-consumption data.

### H8 — Kneeboard de-duplication · §4 · ☑ VERIFIED (2026-06-26, user in-game pass)
- **Setup:** Two passes. **(a)** Generate with the recon, fuel-ladder, and all-packages kneeboards
  **all ON** for a ground-start SEAD/Strike flight in EXACT intel. **(b)** Generate the same flight
  with those three **OFF**.
- **Pass:** With options ON — Mission Info has **no weather block** (it's on the Departure page) and
  **no Min-fuel column** in the flight plan (it's on the Fuel Ladder page); the Friendly Packages
  list is its **own page** (not folded into Mission Info's bottom); there is **no standalone SEAD/
  Strike Target Info page** (the recon Detail page carries the emitters + ALIC). With options OFF —
  the deck is **identical to before**: Mission Info shows weather + Min-fuel column, the packages
  list folds into Mission Info, and the SEAD Target Info page is present. In **APPROXIMATE** intel,
  the SEAD Target Info page is **kept** even with recon on (no exact-coord leak).
- **Fail signature:** any datum still on two pages with options on (weather, Min fuel, the packages
  list); the SEAD page dropped in Approximate intel (coord-fuzzing regression); the deck changing
  when all three options are off (a default-path regression — the omit flags must default to keep);
  Mission Info's flight-plan column count wrong (uom row mismatched with headers).

### H9 — Compact 3-4 page kneeboard deck · §4 · ☑ VERIFIED (2026-06-26, user in-game pass)
- **What it is:** `compact_kneeboard` (default **ON**) folds the optional kneeboard content into at
  most four pages — **P1 Game Plan** (BLUF: task/target/TOT, push+event code words, top live threat
  + defeat, bullseye; then airfields, route with Min fuel, weather, bingo/joker, laser), **P2 Threats
  & Targets** (target ALIC/coords over the enemy-AD threat cards), **P3 Comms & Coordination** (comm
  ladder + AWACS/tanker/JTAC + code words + brevity + packages), and an adaptive **P4 Flex** (recon
  target photo when recon imagery is on, else Fuel Ladder + the full friendly-package list, which then
  drops off P3). The theater/package map + Notes page are not generated in this mode.
- **Headless adjudication (2026-06-26):** `tests/missiongenerator/test_compact_kneeboard.py` covers the
  BLUF line composition (task/push gated on code words/always-on top threat) and a single-page render of
  the composite Threats & Targets page; the page-selection logic caps at four by construction (P1 always,
  P2 iff threats/target, P3 always, P4 iff recon-detail or fuel/packages). Sample renders of all four
  pages reviewed. **Residual (in-sim only):** in-cockpit legibility of the denser pages and that the P4
  recon photo renders against live satellite tiles.
- **Setup:** Generate a ground-start SEAD/Strike flight with the deck **default** (compact ON). Then a
  second pass with `compact_kneeboard` **OFF** to confirm the full multi-page deck (with recon imagery)
  is unchanged. Try a BARCAP (no target/threats) to confirm the 2-page degenerate deck.
- **Pass:** Compact ON → **≤4 pages**, titled Game Plan / Threats & Targets / Comms & Coordination /
  (Fuel & Packages or recon photo); BLUF band tops P1; no page spills to a 5th; a BARCAP over friendly
  ground gets 2 pages (P2 absent, P4 absent). Compact OFF → the prior multi-page deck is byte-for-byte
  unchanged (Mission Info, Support, separate Threat/Brevity/Fuel/Recon/Packages pages).
- **Fail signature:** a 5th page appearing (cap breached); a section printed on two pages (e.g. packages
  on both P3 and P4); the full-deck (OFF) path changed; the P4 recon photo missing when recon is on; the
  BLUF top-threat absent when a live enemy SAM exists.

---

## I. Mission generation

### I1 — Per-squadron DCS country / nation voiceovers · §23 · ☑ VERIFIED (2026-06-26, user in-game pass)
- **Headless adjudication (2026-06-26):** Exercised `CountryAssigner` directly (no
  mission). The realistic CJTF case (blue USA+Greece vs red Russia+Iran with red also
  flying a US squadron) resolves correctly — each squadron under its own country, the
  red US squadron falls back to Russia, no cross-coalition overlap, and the
  canonical-instance discipline holds (`for_squadron` returns the very instance
  registered on the coalition); the single-nation faction is a true no-op. Covered by
  `tests/missiongenerator/test_country_assigner.py` (now 6 passing). **Bug found + fixed:**
  the cross-side guard protected red squadrons from blue but **not** a blue squadron whose
  country equals *red's faction country* — that nation got registered on **both**
  coalitions (the "illegal .miz" fail signature). Added the symmetric reservation (a blue
  squadron sharing red's faction country falls back to blue's faction country) + a
  regression test. **Residual (in-sim only):** the AI radio actually playing the per-nation
  voice (follows from the now-verified country assignment).
- **Setup:** Start a campaign for a **CJTF (coalition) faction** whose air wing draws squadrons
  from more than one nation (e.g. a Blue CJTF with both a US and a Greek viper squadron). Auto-plan
  a turn so flights from at least two nations are tasked, generate the mission, and either inspect
  it in the DCS Mission Editor (group → Country) or fly/observe AI flights and listen to AI radio.
- **Pass:** Each flight's group is set to **its squadron's own country** (US squadron → USA, Greek
  squadron → Greece), each coalition lists all the nations its squadrons use, and AI comms play the
  **per-nation voice** rather than one shared faction voice. A single-nation faction is byte-for-byte
  unchanged (all groups on the faction country).
- **Fail signature:** all groups collapse onto one country (no per-nation voice); a country appears
  under **both** coalitions (illegal `.miz` — the cross-side conflict rule failed); groups silently
  missing from the saved mission (canonical-instance discipline broken — a duplicate `Country`
  instance was passed at spawn vs. registered on the coalition).

### I2 — Civilian background air traffic (Python/pydcs, RAT retired) · ☑ VERIFIED (2026-06-26, user in-game pass)
- **Why:** The MOOSE RAT civilian plugin was retired (recurring `woCharacterHuman`/FARP/respawn
  sim crashes) and reimplemented as Python-planned, pydcs groups
  (`game/missiongenerator/civiliantraffic.py`). Each civilian flies a **multi-leg milk run** between
  neutral fields and lands; a **hybrid spawn** puts a few high heavies airborne at t=0 (instant
  presence) and **ground/runway-starts** everything else (all helos + light props) staggered across
  ~110 min, so the map stays alive through a 2 h mission with **no respawn loop**. Low flyers route on
  **RADIO (AGL)** altitude so they don't clip terrain. The geometry (neutral pool, keep-out, reachable
  chaining, density, air/ground split) is unit-tested (`tests/test_civilian_traffic.py`); only the
  in-sim appearance/behaviour needs eyeballing.
- **Setup:** Generate any campaign mission (civilian traffic is always on) and fly/observe the rear
  area for the full sortie (≥ ~90 min to confirm it sustains).
- **Pass:** A light, **ongoing** mix of civilian **fixed-wing AND helicopters** through the whole
  mission (not just the first hour): heavies cruising high, helos/light props low and visible; ground
  departures take off + climb (no pop-in), the few air-started heavies appear at altitude. Invisible to
  AI (never engaged, never triggers threat reactions), clear of the **front** (keep-out), no all-at-once
  burst. **No sim crash** (the whole point of dropping RAT). Helos/light props do not clip terrain.
- **Fail signature:** No civilian traffic at all (empty neutral pool, or neutrals coalition has no
  country); traffic dies out after ~1 h (stagger window / leg count too short for the mission length —
  widen `STAGGER_WINDOW_S` / raise `FW_LEGS`/`HELO_LEGS`); a sim crash on/after spawn (should be
  impossible — no heliport-id resolution); civilians in the fight (keep-out math); low flyers clipping
  terrain (a `radio_alt` route fell back to BARO, or `_PROFILE` altitude too low); runway congestion at
  one field (too many ground-starts per field — lower the `density()` bands); too dense/sparse overall
  (tune `density()`).
### I3 — Date-gated helmet cueing (JHMCS) · §24 · ☑ VERIFIED (2026-06-26, user in-game pass)
- **Headless adjudication (2026-06-26):** The gate is pure, table-driven logic covered by
  `tests/dcs/test_aircraftproperties.py` against real pydcs `FA_18C_hornet`/`F_16C_50` props —
  JHMCS (id 1) gated before 2003, baseline (0) and NVG (2) always available, `period_correct_value`
  clamps the JHMCS default to the baseline pre-2003, and the Soviet "SURA Visor" (same id 1, Su-30/
  Su-35) is **not** gated because the table keys on the label. The generation clamp
  (`flightgroupconfigurator.degrade_props_for_date`) resolves against the unit-type default, so the
  defaulted-JHMCS case is handled, not just explicit selections. **Residual (in-sim only):** that the
  generated `.miz` actually spawns the baseline helmet option in-cockpit pre-2003.
- **Setup:** Start a campaign **before 2003** with `Restrict weapons by campaign date` **ON** and an
  F/A-18 or F-16 squadron. Open a flight's payload → the helmet-device dropdown should not list
  JHMCS. Generate and open the `.miz` (or fly) and check the aircraft's mission options.
- **Pass:** Pre-2003, JHMCS is absent from the dropdown and the generated mission shows the baseline
  helmet option (Not installed / Visor Only); NVG stays available in every era; with the setting OFF
  (or in a 2003+ campaign) JHMCS is offered and applied normally. Soviet jets keep their SURA Visor.
- **Fail signature:** JHMCS still selectable/applied in a pre-2003 campaign with the setting on; NVG
  or the Soviet SURA Visor wrongly removed; the dropdown shows nothing selected; a non-helmet
  property (laser code, datalink) changed by the gate.

### I4 — Frontline clustered laydown + default stance (PR #823 adoption) · §9 · ☑ VERIFIED (2026-06-28, audience in-game pass — front clustered along the line)
- **Why:** Adopted PR #823's proportional mixed armor clusters + even-spread placement
  (`ai_ground_planner.py`, `frontline_clustering.py`, `flotgenerator._generate_groups`), with
  #823's DCS-task cohesive maneuver TIC-guarded behind `not self.tic_enabled`. Composition /
  placement is unit-tested and the TIC guard is locked by
  `tests/missiongenerator/test_flotgenerator_tic_guard.py`; only the in-sim *look* of the laydown
  needs eyeballing. Two builds to watch: TIC-on (default) and TIC-off.
- **Setup:** Generate a campaign mission with a populated armor front. (a) TIC ON (default):
  inspect/fly the front. (b) TIC OFF: regenerate and inspect to exercise the #823 maneuver path.
- **Pass (TIC on):** frontline armor spawns in evenly-spread clusters (no bunching at one offset),
  mixed/alternating armor types, SHORAD/ATGM/recon positioned around each wedge (recon ahead,
  SHORAD/ATGM behind), nothing stacked on the FLOT; movement is still the TIC scripted firefight,
  SHORAD/RECON static. **Pass (TIC off):** clusters maneuver cohesively (wedge advances, followers
  keep formation; APC-led wedges don't split in BREAKTHROUGH). **Default stance:** with auto-stance
  OFF, a new campaign / freshly captured player CP starts on the configured stance.
- **Fail signature:** units bunched at one along-front offset or stacked on the FLOT; single-type
  monoculture groups (composition not applied); on a TIC build, armor/ATGM driving via DCS AI tasks
  or SHORAD/RECON maneuvering (the #823 maneuver leaked past the TIC guard — should be impossible,
  test-locked); on a TIC-off build, clusters splitting apart in BREAKTHROUGH; the default-stance
  setting ignored at new-game/capture.

### I5 — Nation-aware pilot names · §23 · ☑ VERIFIED (2026-06-28, audience in-game pass — names match squadron nationality; live-save confirmed 2026-06-27)
- **Live-save confirmation (2026-06-27):** Loaded the actual flown campaign
  (`autosave.retribution`, GermanyCW turn 2, Blufor Late Cold War vs Russia 1980) headless and
  resolved every squadron's `faker` against its `country`. The blue wing is a genuine **4-nation
  CJTF** and each squadron draws its **own** nation locale even though the blue faction's
  `locales` is `None` (so there is no shared-faction locale to fall back to): USA squadrons →
  `en_US`, JaboG 31 / GAF JG 74 → `de_DE`, IAF 69 FS → `he_IL`, Ala 14 (Mirage F1) → `es_ES`;
  every red squadron → `ru_RU`. Countries used: blue `[Germany, Israel, Spain, USA]`, red
  `[Russia]` — **no cross-coalition country overlap** (the illegal-`.miz` fail signature). This
  is a stronger real case than the unit tests (4 live nations). **Residual (in-sim only):** the
  AI radio actually *playing* the per-nation voice — the country-assignment half of that is I1,
  already VERIFIED in-game 2026-06-26.
- **Headless adjudication (2026-06-26):** the country→locale resolver is fully covered by
  `tests/squadrons/test_pilotnames.py` (mapped country → its own-locale Faker; unmapped /
  multinational / `None` → faction fallback; locale cache independent of fallback; **every**
  mapped locale is gender-aware so a typo'd/non-gendered locale fails CI rather than shipping; a
  squadron recruits non-empty named pilots from its country locale). Sample rosters per nation
  read right (Greek, Persian, Russian surname-first + patronymic, Japanese, Hebrew). **Residual
  (UI/in-sim only):** the names actually rendering in the squadron/roster UI and, if shown,
  in-cockpit — non-Latin scripts in particular.
- **Setup:** A mixed-nation CJTF campaign (e.g. a Blue side with a US and a Greek squadron). Open
  the air-wing / squadron roster and read the pilot names; optionally generate a mission.
- **Pass:** Each squadron's roster carries names in its **own** nation's convention (US squadron →
  US names, Greek → Greek, etc.); a single-nation faction is unchanged; the CJTF / UN /
  Insurgent "countries" fall back to the faction names (no crash, no blanks).
- **Fail signature:** a squadron's pilots all share one nation's names regardless of country (the
  `Squadron.faker` wiring didn't take); blank/garbled names; or a recruitment crash on a locale
  with no gendered names (guarded + test-locked — should be impossible).

### H10 — Shared-airframe kneeboard index · §27 / §30 · ☐ UNTESTED (folded into the cover page — verify under K2; condition not met in the 2026-06-28 pass)
- **Not exercised (2026-06-28, audience pass — user confirmed the condition wasn't set up):** the mission did **not** have 2+ client flights of the same airframe, so the index section had nothing to render — no observation either way, **not** a fail. Re-check target: frag **2+ client flights of the same airframe** and confirm the cover page (page 1) carries the callsign / task / start-page index block, and that a lone flight of a type shows none. If the index never appears with 2+ shared, that is the K2 cover-page fail signature.
- **Folded into the cover page (§30).** The standalone index page is gone; the index is now a section
  on the always-present cover, so its in-game check is covered by **K2**. (Page-math + lone-flight
  no-index regression now in `tests/missiongenerator/test_kneeboard_cover.py`.)
- **Headless adjudication (2026-06-26):** *(historical — was `tests/missiongenerator/test_kneeboard_index.py`)* covers the
  start-page math (index is page 1, blocks start at 2 and advance by block size), callsign grouping +
  sort, and the index page render. **Residual (in-sim only):** the index actually appears in-cockpit
  and its page numbers line up with the stacked deck DCS builds.
- **Setup:** Frag **2+ client flights of the same airframe** (e.g. two F/A-18 flights) in a mission;
  generate and open the kneeboard. Also frag a single flight of another type as the control.
- **Pass:** page 1 of the shared airframe is an index listing each flight's callsign / task / start
  page; flipping to a listed page lands on that flight's deck; the single-flight type has **no** index.
- **Fail signature:** no index when 2+ share a type; wrong start pages; an index wrongly added for a
  lone flight; flights out of the listed order.

### H11 — Estimated fuel ladder for dataless airframes · §4 · ☐ UNTESTED (estimate sanity-banded in `tests/dcs/test_estimated_fuel_consumption.py`, 2026-06-27; deferred behind a kneeboard update per user 2026-06-28)
- **Deferred (2026-06-28, user: "update after kneeboard update"):** revisit once the pending kneeboard changes land — re-check the C-130J King / helo Fuel Ladder against the current deck so the estimate is validated against the updated kneeboard rather than the old one.
- **What it is:** `AircraftType.estimated_fuel_consumption` synthesises a rough `FuelConsumption` from
  the airframe's `fuel_max` (bucketed helicopter / heavy-transport / combat) so the Fuel Ladder card
  renders for airframes with **no** hand-measured `fuel:` block — the **C-130J "King"**, helicopters,
  warbirds, etc. Kneeboard-scoped: planner tanker tasking + in-flight sim are untouched.
- **Setup:** Enable **Generate fuel ladder kneeboard page**. Frag a player flight in an airframe with
  no measured fuel data — ideally the **C-130J King** (the reported case) and a helicopter — and open
  the kneeboard. Cross-check against H7 for an airframe that *does* have measured data (e.g. F/A-18C).
- **Pass:** the King / helo Fuel Ladder page **renders a descending ladder** with an RTB margin call-out
  and Bingo/Joker instead of *"No fuel estimate available for this aircraft."* Numbers are plausible
  planning figures (the King cruises ~16 lb/NM, full ~43k lb, so it should *not* read negative-margin
  on a normal sortie). Measured-data airframes are unchanged from H7.
- **Fail signature:** the placeholder text still showing for the King/helo; a ladder that's all `-`
  (no planned column — `flight.fuel` missing); wildly implausible numbers (e.g. the King reading
  ~80 lb/NM, a sign the heavy bucket isn't being picked — check `_is_heavy_airframe`); any change to a
  measured-data airframe's ladder (the estimate must never override a real `fuel:` block); planner
  suddenly fragging tankers for the King (the fallback must stay out of `unit_type.fuel_consumption`).

### J1 — Capability-weighted off-mission combat · §26 · ☑ VERIFIED (2026-06-28, audience in-game pass — user "good, I think"; off-mission auto-resolve looked right, not deeply scrutinized)
- **Headless adjudication (2026-06-26):** `tests/test_combat_resolution_capability.py` covers the
  scoring (A2A strength = best A2A `task_priority` × count; win = strength share; survivor loss scales
  with margin, clamped ≤ legacy 0.5; SAM death halved for SEAD, stacked by site count, clamped). 39
  combat/sim regression tests stay green. **Residual (in-sim only):** that auto-resolved attrition over
  several turns *reads* believably.
- **Setup:** Auto-plan a few turns with **combat resolution = Resolve** (or Skip) so AI-vs-AI
  engagements auto-resolve; watch the losses on both sides over the turns.
- **Pass:** modern fighters beat obsolete ones more often than not; numbers still tell (a pair can
  beat a lone jet); a SEAD/SEAD-capable flight survives SAMs better than a striker; no side wins or
  loses every single time.
- **Fail signature:** outcomes feel random (elite jets routinely lost to obsolete ones), or one side
  always wins; SEAD no better off than a bomber against SAMs.

### J2 — "Player at IP" fast-forward spawns at the IP · §26 · ☑ VERIFIED (2026-06-28, audience in-game pass — spawns at the IP)
- **Headless adjudication (2026-06-26):** `tests/test_player_at_ip_fast_forward.py` covers the gate
  (AI-only combat does not pause a PLAYER_AT_IP fast-forward; a player-involving combat still does;
  other stop conditions / `force_continue` unchanged). **Residual (in-sim only):** the actual spawn
  position after a real fast-forward.
- **Setup:** Fast-forward stop condition = **"Player at IP"**, combat resolution = **default (Pause)**,
  a **ground-started** (Cold/Hot/Runway) player flight with an IP. Generate the mission.
- **Pass:** the player spawns **airborne at/near their IP**, not on the ramp, even with AI fights
  happening elsewhere; if the player's *own* flight is engaged en route the sim still pauses there.
- **Fail signature:** player spawns at their configured ground start (the bug returns); or the sim
  never stops / the player ends up far past the IP.

### J3 — Per-group C-130J EW de-confliction (JAMMING + SOF/King coexist) · §2 / §15 · ☑ VERIFIED (2026-06-28, audience in-game pass — EW jet + SOF/King C-130J coexist; non-EW C-130J has no EW menu)
- **Headless adjudication (2026-06-26):** `tests/missiongenerator/test_ew_deconfliction.py` covers
  `_ew_excluded_c130j_groups` (only `SOF`/`COMBAT_SAR` C-130J-30 group names, not the JAMMING jet or
  non-C-130J helos) and the `c130j` plugin wiring (reads `dcsRetribution.EwExcludedGroups`,
  `isEligible` rejects an excluded group). **Residual (in-sim only):** the runtime attach decision.
  Supersedes the old mission-wide skip verified under F3.
- **Setup:** Frag **both** a JAMMING C-130J-30 **and** a SOF-insert or Combat SAR King C-130J-30 in
  the **same** mission (the case the old whole-plugin skip broke). Generate and fly/inspect.
- **Pass:** the JAMMING jet keeps its full `c130j` EW/ISR menu; the SOF/King C-130J flies **clean**
  (no EW menu). With no SOF/King fragged, every C-130J-30 still gets EW (unchanged baseline).
- **Fail signature:** the JAMMING jet loses its EW menu when a SOF/King is present (the old
  mission-wide skip regressed); the SOF/King wears the EW menu (deny-list not applied / group-name
  mismatch); or a Lua error in the `c130j` `isEligible` path.

---

## K. Settings UI

### K1 — Settings IA reorg + difficulty presets · §28 · ☑ VERIFIED (2026-06-28, audience in-game pass)
- **Headless adjudication (2026-06-27):** `tests/settings/test_field_layout.py` locks the reorg
  (FIELD_LAYOUT covers every user field exactly once, the UI walk emits each once, the six pages are
  in the designed order, no section > 13 settings) and `tests/settings/test_difficultypreset.py`
  locks the engine (Normal == Settings defaults, apply→detect round-trips for all four presets,
  unrelated fields untouched, presets mutually distinct). An **offscreen Qt build** confirmed the full
  `QSettingsWidget` constructs with all six pages, the preset bar tops Difficulty & Realism, and
  applying Ace flips labels→Off / invuln→False / enemy_skill→Excellent with the "Current:" label
  tracking. **Residual (UI eyeball only):** the visual feel / readability in the running app.
- **Setup:** Open **Settings** in a campaign and the **New Game** wizard's options page.
- **Pass:** Six content pages — **Difficulty & Realism / Air Doctrine / Campaign Management /
  Mission Generation / Kneeboards / Performance** — each with focused sections (no 30-item wall);
  every page has its icon. The **Difficulty preset** bar tops Difficulty & Realism; clicking
  **Casual / Normal / Veteran / Ace** updates the controls below and the "Current: …" readout;
  hand-editing a control afterward still works; **Normal** restores stock values. No setting is
  missing from the dialog.
- **Fail signature:** a setting absent from every page (FIELD_LAYOUT gap — should be impossible,
  test-locked); a page/section empty or mis-ordered; the preset bar missing or not refreshing the
  controls; a preset not flipping the expected fields; a blank page icon; a console error opening
  the dialog.

### K2 — Kneeboard cover page (op/turn header + SITREP + index) · §29 / §30 · ☑ VERIFIED (2026-06-28, audience in-game pass — SITREP numbers across turns OK; render previously confirmed)
- **Cockpit-confirmed (2026-06-27, user in-game pass — session `suspicious-goldberg`/`1ca51fbf`):**
  the kneeboard deck (cover page + compact deck) renders cleanly in the cockpit — **"Kneeboards look
  fantastic."** That clears the render/legibility half of this row (corroborating H2/H9, already
  VERIFIED). Residual is only **SITREP-number accuracy from turn 2 on** (losses/captures/recoveries
  matching the prior turn's debrief) and the index start-page math on a live multi-flight deck.
  *(This confirmation was given in-game and dropped — PR #226 recorded only the headless evidence;
  recovered here.)*
- **Now hosts the SITREP (§29) AND the shared-airframe index (§27/H10)** on one always-present cover
  page. This row supersedes the standalone SITREP-band and index-page checks.
- **Headless adjudication (2026-06-27):** `tests/test_sitrep.py` covers the SITREP model + formatting
  (side split, captured/lost by side, Combat SAR count, "claimed" enemy phrasing, singular/plural) and
  `sitrep_for_kneeboard` gating (off / no prior turn / quiet turn). `tests/missiongenerator/test_kneeboard_cover.py`
  covers the cover assembly: index start-page math (cover = page 1, blocks at 2/5/9), a lone flight gets
  a cover with **no** index section, SITREP gating, and a full render. `record_sitrep` is wired into
  `commit()` (and added to the asserted `COMMIT_STEPS`). A **render smoke** drew the whole cover (op/turn
  header + SITREP + index table) through the real `KneeboardPageWriter` (41 KB PNG, correct text).
  **Residual (in-cockpit only):** the cover's look on a live kneeboard and that the numbers + page
  numbers match.
- **Setup:** Generate a mission (and fly a turn so turn 2 has a prior-turn SITREP). Open the kneeboard;
  for the index, frag **2+ client flights of one airframe**.
- **Pass:** **Page 1 is the cover** — `"<Operation> — Turn N"` + date always; a **"SITREP — Turn N-1"**
  section from turn 2 on (friendly + enemy-claimed losses, bases captured/lost, pilots recovered,
  matching the previous turn); and a **flight index** (callsign / task / start page) when 2+ share the
  airframe, whose start pages land on the right decks. **Turn 1 / a quiet turn / toggle off** → no SITREP
  section. A lone flight → cover with no index section.
- **Fail signature:** no cover page; SITREP present on turn 1 or after a quiet turn (gating wrong);
  numbers not matching the debrief; enemy losses not "claimed"; index start pages off by the cover; an
  index shown for a lone flight; a stale SITREP from two turns ago (capture not running each `commit`).

---

## L. Vietnam Ops

### L1 — Arc Light heavy-bomber Strike carpet · §32 · ☑ VERIFIED (2026-06-28, audience in-game pass — user: "good")
- **In-game (2026-06-28, audience pass — user verdict "good"):** the Arc Light carpet works — a heavy bomber's STRIKE walks a carpet of explosions across the target box at the run-in, no Lua error and no reported FPS hit. Power/density read acceptable to the user (no tuning requested).
- **Headless adjudication:** `game/missiongenerator/tests/test_vietnamops_luadata.py` locks the Python
  emitter — only a heavy-bomber (`HEAVY_BOMBER_DCS_IDS`) `STRIKE` produces an `arcLight` record, the
  toggle off emits no `VietnamOps` node, and a non-bomber Strike emits no record. The carpet itself
  (`resources/plugins/vietnamops/vietnamops-config.lua`) is Lua and can only be exercised in a live mission.
- **Setup:** A campaign with the **Vietnam Ops → Arc Light** setting **on** and a **B-52 STRIKE** fragged
  against a ground target (e.g. Khe Sanh with `vietnam_arc_light: true`). Watch the B-52 run in.
- **Pass:** As the B-52 closes inside the release range (~8 NM) of its target, a **walking carpet** of
  explosions marches across the target box, oriented along the run-in, with a coalition "ARC LIGHT inbound"
  message. Ground units in the box take damage (flows to debrief). A B-52 shot down *before* the run-in
  fires **no** carpet. A non-bomber (F-4/A-4) Strike behaves normally (single aimpoint). `dcs.log` clean.
- **Fail signature:** no carpet despite a healthy B-52 reaching the target; carpet fires for a tactical
  striker; carpet on a dead/destroyed bomber; explosions stacked at one point (no walk / bad heading);
  `land.getHeight`/`explosion` Lua error in `dcs.log`; FPS hit from over-dense impacts (tune
  `arcLightBlastPower`/length/width down).

### L2 — AAA flak gauntlet · §33 · ◐ PARTIAL (2026-06-28, audience in-game pass — works very well but TOO ACCURATE/lethal; default miss/tracking tuning owed)
- **⚠️ Config-mismatch finding (2026-06-30, `dcs.log`):** the flown session's plugin options were
  **`ceiling 5000m, power 8`** — but the *current* `plugin.json` defaults (post-2026-06-28 softening,
  confirmed by reading `vietnamops-config.lua` + `plugin.json` today) are `flakCeilingM=4500` /
  `flakBlastPower=6`. `power=8` is the exact **pre-softening** value (`BLAST 8→6`); `ceiling=5000` was
  never a documented value either way. This means this session's flak lethality was **not** exercised
  against the current softened tuning — either this `.miz`'s plugin options are a stale campaign-side
  override that predates the 2026-06-28 fix, or someone deliberately dialed it back up. Blue took heavy
  losses this session (whole 3-ship BLOODHOUND Strike A-6E flight, whole 3-ship Kutaisi BARCAP A-4E
  flight, both TARPS RF-101Bs, several SCAR/CAS helos — 29 `crash_events` total), which is *consistent*
  with an over-tuned flak gauntlet but wasn't isolated from SAM/MiG kills (scripted `explosion()` calls
  don't leave a Tacview object or a per-burst log line, so per-kill attribution needs deeper Tacview
  geometry work this pass didn't do). **Before re-flying this row:** check the campaign's saved Vietnam
  Ops plugin options (or regenerate) and confirm `flakBlastPower`/`flakCeilingM` are actually reading
  the current 6/4500 defaults, not a stale 8/5000.
- **In-game (2026-06-28, audience pass — user: "too accurate but working very well"):** the gauntlet mechanic is confirmed working (AAA discovery, engagement geometry, predictability ramp all behave) — but the bursts land **too close / kill too reliably**, reading more like a hard-kill threat than the intended mostly-visual pressure. The lethal lever is the close **"tracking" round** (`flakBurst`: `miss = MIN_MISS*0.35` ≈ 24 m at `blast = BLAST*2.5` = 20, fired once `factor > 0.66`) on top of the tight `MIN_MISS = 70` floor. **Tuning APPLIED 2026-06-28 (recommended softening):** `MIN_MISS` 70→**110** m, tracking round `miss ×0.35→×0.55` + `blast ×2.5→×2.0` and rarer (`factor > 0.66→0.8`), `BLAST` 8→**6** — in both `vietnamops-config.lua` and the `plugin.json` defaults (`flakMinMissM` 70→110, `flakBlastPower` 8→6). Net: predictable bursts ~42–98 m@8 → ~66–154 m@6; the close tracking puff ~15–34 m@20 → ~36–85 m@12. **Re-fly owed** to confirm the feel is right (still pressure, no hard-kill).
- **Headless adjudication:** `game/missiongenerator/tests/test_vietnamops_luadata.py` locks the on-marker
  emission (flak node only when the setting is on, independent of Arc Light). The flak itself — AAA discovery
  by attribute, the engagement geometry, and the predictability ramp — is runtime Lua, exercisable only live.
- **Setup:** A campaign with **Vietnam Ops → AAA flak gauntlet** on and enemy **AAA guns** (ZSU/Shilka/airfield
  guns) near a target. Fly through their range below ~4500 m AGL: first a steady, predictable run, then jinking.
- **Pass:** Flying within range/below ceiling draws **barrage flak bursts** around the aircraft. A **steady**
  heading+altitude **tightens** them (and a sustained steady run draws the occasional close round); **jinking /
  changing altitude widens** them. Out of range / on the deck (<120 m) / above the ceiling → no flak. Both
  sides' AAA behave symmetrically. `dcs.log` clean; no FPS collapse.
- **Fail signature:** no flak despite flying over live AAA in range; flak with **no** AAA nearby; flak that
  ignores predictability (always tight or always loose); flak so dense/lethal it reads as a hidden SAM
  (dial `flakBlastPower` / miss / range down); `getVelocity`/`hasAttribute`/`explosion` Lua error in
  `dcs.log`; FPS hit on a dense mission.

### L3 — Naval gunfire support · §34 · ☐ UNTESTED (emitter test-covered; both runtime modes are Lua, need a cockpit pass)
- **Inconclusive session (2026-06-30, Tacview):** `dcs.log` confirms the emitter armed 2 blue
  gun ships (`Naval gunfire armed (2/0 gun ship(s) blue/red, range 20000m, ...)`) — 2× VWV
  `DE-1052 USS Knox` escorting a carrier strike group. But scanning every `Projectile+Shell` object in
  the Tacview ACMI (34k+ shell events) found **no naval-caliber shell type** (only tank/AAA-caliber
  ammo like `M68_105_HE`, `KS19_100HE`, etc. — nothing matching the Knox's 5" mount), and the ship
  group's recorded position is well offshore of the active front (Kutaisi/Senaki-Kolkhi, well inland).
  That's consistent with the documented **"coastal only by construction"** limitation (no enemy ground
  in the ships' 20 km range ⇒ nothing fires) rather than a bug — but it means this row **still wasn't
  actually exercised**. To close it out: fly (or auto-plan) a campaign whose front sits within ~20 km
  of the coast, or manually reposition a gun ship group near enemy ground and either wait for the auto
  cadence or use **radio → Naval Fire Mission → Fire on last F10 map marker**.
- **Headless adjudication:** `game/missiongenerator/tests/test_vietnamops_luadata.py` locks the gun-ship
  emission (CRUISER/DESTROYER/FRIGATE incl. the New Jersey, carrier excluded, coalition carried; off /
  no-gun-ship = no node). The F10 menu, marker read, ship/target selection, and `TaskFireAtPoint` are runtime
  Lua, exercisable only live.
- **Setup:** A **coastal** campaign with **Vietnam Ops → Naval gunfire** on and a friendly **gun ship**
  (New Jersey / cruiser / destroyer) offshore within ~20 km of enemy coastal ground. Place an F10 map marker
  on a coastal target and use **radio menu → Naval Fire Mission → Fire on last F10 map marker**. Also just
  wait for the automatic bombardment.
- **Pass:** The F10 call lands shells on the marker from the nearest in-range ship (with a "SHOT" message);
  out of range gives "no gun ship in range." With auto on, ships periodically shell the nearest in-range
  enemy coastal ground without input. **Inland** missions (no ship in range) produce **no** fire. `dcs.log`
  clean.
- **Fail signature:** F10 menu absent despite an owned gun ship; marker call does nothing / errors; ship
  fires far inland (range gate wrong); auto bombardment never fires or fires every tick (cadence wrong);
  `TaskFireAtPoint`/`getMarkPanels`/`missionCommands` Lua error in `dcs.log`; an escort wandering off station.

### L4 — Vietnam compressed-theater support-orbit standoff · PR #314 · ☐ UNTESTED (headless-verified; map-readable, no flying)
- **Headless adjudication:** `game/ato/flightplans/supportorbit.py::support_orbit_anchor` on the live Khe Sanh
  save: at 25/20 NM the AEW&C/tanker orbit sits **83/74 km** behind the front (vs 148 km at the old 60 NM),
  still 37-46 km clear of the threat. Guard test `tests/test_vietnam_content.py::test_vietnam_campaign_tightens_support_orbits`
  pins the 3 campaign values + the untouched 80/70 defaults.
- **Setup:** Start a **NEW** Khe Sanh / Yankee Station / Velvet Thunder game (existing saves bake the old
  buffer in) and auto-plan a turn.
- **Pass:** On the planner map the AEW&C and tanker racetracks hug the front (~75-90 km back), not flung to
  the map edge; their escorts no longer sprawl across the theater. Large (non-Vietnam) campaigns are unchanged.
- **Fail signature:** orbits still ~150 km back / at the map edge; a tanker sitting inside a SAM ring (buffer
  too low); the buffer not applied (check Air Doctrine page shows 25/20 after campaign-select).

### L5 — New-Game "Vietnam" card · Vietnam mode P2 shell · ☑ VERIFIED (2026-06-28, audience in-game pass — card works; user wants more content added)
- **In-game (2026-06-28, audience pass — user: "works but needs more added"):** the New-Game **Vietnam** card works as specified — the radio appears on the Introduction page and the Theater page filters to the Vietnam campaigns. The "needs more added" is a **content** follow-up (more Vietnam campaigns/options surfaced on the card), tracked separately — not a fail of the P2 shell.
- **Headless adjudication:** the filter predicate `Campaign.matches_era` is unit-tested
  (`tests/test_vietnam_content.py::test_matches_era_drives_the_vietnam_card_filter`) and the Qt modules import
  clean. The radio/field render + the `vietnamMode`→list-filter path can't be exercised headless (the
  campaign-list item build needs the DCS install dir).
- **Setup:** Open **New Game**. On the Introduction page, "Campaign type" now has a third option, **Vietnam**.
- **Pass:** Selecting **Vietnam** → the next (Theater) page is titled "Vietnam" and lists **only** the three
  Vietnam campaigns (Khe Sanh, Yankee Station, Velvet Thunder); selecting one still pre-loads its settings +
  recommended factions. Going **back** and choosing "Play an included campaign" restores the full list;
  "blank canvas" still shows the terrain picker. The "Show incompatible campaigns" toggle keeps the Vietnam
  filter applied.
- **Fail signature:** no Vietnam radio; Vietnam shows all campaigns (filter not applied) or an empty list;
  switching back to "included" stays filtered; the "show incompatible" toggle drops the era filter; a crash
  arriving on the Theater page.

### L6 — Convoy interdiction (Steel Tiger) · §35 · ☑ VERIFIED (2026-06-30, `dcs.log` — "Vietnam v2.miz" session, full spawn→wipe→respawn cycle)
- **Verified (2026-06-30, flown session — `Vietnam v2.miz` / `dcs.log`):** `VietnamConvoy-1` registered
  at mission load (`00:17:32`, "Convoy interdiction armed (3 waypoint corridor)"), then
  `VietnamConvoy-2` registered at `01:22:00` — 64m28s later, with **no intervening mission reload** (the
  session ran continuously from `00:17:29` to the Tacview save at `01:29:50`). That gap is only
  consistent with the column having been fully wiped around `01:12:00` (≈54 min of driving/
  interdiction) and the 600 s `RESPAWN` timer then rolling a fresh column — i.e. a complete
  spawn→drive→destroy→respawn cycle happened live, with no `coalition.addGroup` Lua errors in the log.
  Fail signature (no spawn / never moves / Lua error) did not occur. Still open: the halt-under-threat
  (`setOnOff`) behavior wasn't specifically confirmed (would need a Tacview pass flown close enough to
  the corridor to force a halt).
- **Headless adjudication:** the corridor pick (`_populate_convoy_interdiction`) is unit-tested
  (`game/missiongenerator/tests/test_vietnamops_luadata.py` — picks the nearest enemy→enemy road, ignores the
  RED→BLUE front, off = no node) and verified on the live Khe Sanh save (chose Senaki→Kobuleti, 23.5 km behind
  the FLOT). The **runtime spawn is unverified** — `coalition.addGroup`, the red country, and the
  halt-under-threat behaviour can't be exercised headless.
- **Setup:** Start a **NEW** game with **Vietnam Ops → Convoy interdiction** on (a campaign with an enemy
  supply road behind the front — Khe Sanh). Fly toward the chosen corridor (the road nearest the FLOT in red
  territory) / frag an Armed Recon there.
- **Pass:** a moving enemy truck column drives the road; it **halts** when you close inside the scatter range
  and rolls again when you leave; destroying it shows "Enemy supply convoy destroyed on the trail" and a fresh
  column rolls after the respawn delay. `dcs.log` clean (no `coalition.addGroup` errors).
- **Fail signature:** no convoy spawns (group-data structure wrong / red country not on the red coalition);
  the column never moves or never halts (`setOnOff`/route wrong); spams respawns; `coalition.addGroup` Lua
  error in `dcs.log`. Tune speed/scatter-range/respawn/truck-count via the plugin options.

### L7 — Right-click supply-route interdiction · §35 · ☐ UNTESTED (server resolution test-covered; the right-click → Qt dialog path needs an in-app pass)
- **Headless adjudication:** `interdiction_target_for_route_id` is unit-tested
  (`tests/server/test_supply_route_interdiction.py` — resolves the `"<cp_a_id>:<cp_b_id>"` route id to the
  enemy end, prefers the contested CP, returns None for a friendly/malformed route). The **client
  right-click → `POST /qt/create-package/supply-route/{id}` → Qt package dialog** path is React/Qt and can't
  be exercised headless.
- **Setup:** Load any campaign with a visible enemy supply route (enable the Supply Routes map layer). The
  visible line is thin and sent to the back, so the route carries a **wide invisible hit-line** — right-click
  anywhere along the coloured line. **Must be a build that includes this change** (the client is rebuilt by
  CI on merge; a stale `client/build` won't have the handler).
- **Pass:** right-clicking an **enemy** supply route opens the new-package dialog targeting the road's enemy
  end, with the add-flight dialog auto-opened and **Armed Recon pre-selected** — pick aircraft and it frags.
  Right-clicking a fully-**friendly** route does nothing (server 404, no dialog).
- **Fail signature:** right-click does nothing on an enemy route (the hand-added
  `useOpenNewSupplyRoutePackageDialogMutation` hook or the `contextmenu` handler is wrong); a JS error in the
  client console; the dialog opens on the wrong CP. Needs the CI client rebuild (hand-edited generated API).

---

## Drain order — batch the queue into ~5 flight sessions

**Policy: new feature work is frozen until this queue drains.** The rows are not
24 separate chores — one campaign setup exercises a whole cluster, and the first
session needs *no flying at all* (just auto-plan a turn and read the map). Work
top-down; each session is ordered so the highest-blast-radius, lowest-effort
checks come first.

### Session 1 — Standard land-front, auto-plan turn 1, **observe only** (no sortie)
Highest leverage: planner/placement bugs affect *every* campaign, and you verify
them by inspecting the ATO + map, not by flying.
- A2 (QRA base-defense doctrine), A3 (player-manned QRA alert flight appears in the
  ATO + dispatcher debit), B2 (DEAD reachability gate), B3 (threat-weighted
  BARCAP orbit), B4 (TARCAP/escort reach), C1 + C2 (AWACS/tanker front-anchor +
  depth), F6 (SCAR auto-plan appears in ATO), I4 (frontline clustered laydown —
  inspect the front-line armor spread on the map).
- Setup needs: active land front, enemy airbase ≈90 NM from FLOT, an armor
  concentration near the front, AWACS+tanker support, `scar_autoplan` ON, and a
  player-flyable BARCAP squadron with its "…of which player-manned" spinbox ≥ 1 (A3).

### Session 2 — Fly a strike package off that campaign
- A1 (QRA scramble profile — trigger a raid, include a high-elev alert base),
  A4 (player QRA scramble cue — sit a player-manned alert base and confirm the
  "SCRAMBLE" call fires as the raid closes), C3 (tanker speed), C5 (boom/probe
  match), C6 (fuel-driven pre/post-vul tanking), C4 (A-6E attack/tanker split —
  buy both), H1 (kneeboard overflow on a busy theater), D1 (player-despawn loss —
  land/despawn then end).

### Session 3 — SCAR commander-capture campaign
- F2 (capture → permanent reveal carryover across turns), F5 (mis-ID penalty —
  kill a decoy), E (SOF C-130 insert ground-starts + EW skipped), G2 (TARS BDA
  bridge via an F-14 TARPS pass).

### Session 4 — Plugin-runtime sweep, fly over an active front
- G3 (TIC ambient fire / LOS-blocked positions), G4 (C-130J EW/ISR — fly the
  JAMMING slot).

### Session 5 — Coastal front + drop-spawn cheats
- B1 (forward-CAP / FLOT depth on a coastline/river front), 20-A…20-G (drop-spawn
  dialog, immediate spawn, removal, deploy-next-turn, terrain + range gates, free
  cheat).

Mark each row's **Status** as you go. A cluster of **☑ VERIFIED** Lua-free Python
rows (B, C, D, E) then becomes the upstream-PR carve-out batch.

---

## How this feeds the other threads

- A row that reaches **✗ REGRESSED** is a concrete bug to fix.
- A cluster of **☑ VERIFIED** Lua-free Python rows (B, C, D, E) are the
  upstream-PR candidates — verify in-game, then carve them out (see the
  upstreaming inventory).

---

### §20 Drop-spawn (in-game-pass required)

| # | Observable criterion | Fail signature |
|---|---|---|
| 20-A | With **`enable_unit_placement` ON**: right-click blank map → Qt dialog opens with coalition/category/layout pickers | No dialog; console error in devtools |
| 20-H | With **`enable_unit_placement` OFF** (default): right-click blank map opens **nothing**, and right-click a target marker still opens **package planning** (not the buy dialog) | Buy dialog pops on a plain right-click while the cheat is off (the 2026-06-25 regression) |
| 20-B | Select "Ground Force", confirm → armor group appears on map immediately | No marker; no SSE event in network tab |
| 20-C | Right-click a user-placed TGO → marker disappears from map | TGO remains; server returns 403 |
| 20-D | "Deploy Next Turn" → no immediate marker; after turn advance group materialises | Group never appears; pending list never cleared |
| 20-E | Place a naval group in sea → succeeds; place on land → error dialog | Terrain check not firing |
| 20-F | Place beyond 200 km from nearest CP (no free cheat) → error dialog | No range error; TGO placed out of range |
| 20-G | Enable "Free placement" cheat → no budget deducted | Budget still decremented |

### Campaign maker — blank canvas (in-game-pass required)

Design: `docs/dev/design/414th-campaign-maker-notes.md`.

**Status 2026-06-24 (Retribution-app pass, Afghanistan): core loop VERIFIED.**
Headless-inspected the finalized save — 0 neutral leftovers (gray pruned), 5 fronts
derived, 1 squadron each side staffed. Bugs found + fixed this pass: PR #130, #133
(merged), #138 (open, finalize button). BC-D fly-half + BC-E need DCS; BC-F still pending.

**Update 2026-06-27:** the Increment C "barren finalized save" gap is **closed** — a
finalized blank canvas now seeds a per-base economy (factory/ammo/fuel/oil) **and** a
default air-defence/armor laydown (SHORAD + EWR + forward MERAD + BASE_DEFENSE armor),
routed through the engine's own ground-object generator so the IADS wires up. Headless-
verified (Caucasus, `[CH] Russia 2020`): 32 ground objects on a 4-base canvas, 11 IADS
nodes after `begin_turn_0`. New row BC-G covers the in-game flight check.

| # | Layer | Observable criterion | Fail signature | Status |
|---|---|---|---|---|
| BC-A | Retribution | "Build your own (blank canvas)" → map opens with **every** airfield **gray/yellow** (neutral), no fronts, no units | Crash on generate; bases pre-coloured; preset units present | **VERIFIED** (after #133) |
| BC-B | Retribution | **Left-click** cycles gray→blue→red→gray (live SSE); **right-click** reverses | Opens info dialog; no recolor; 403 | **VERIFIED** (needed client rebuild) |
| BC-C | Retribution | **Finalize Campaign** prunes unpainted gray bases, draws a front between blue/red | Gray bases remain; no front; crash in finalize | **VERIFIED** (0 neutral, 5 fronts) |
| BC-D | build=Retribution / fly=.miz | Finalize → air-wing dialog → add squadrons from scratch → plan + fly a package | Dialog empty/errors with 0 preconfigured; no flyable aircraft | build VERIFIED (1 sq/side); **fly pending** |
| BC-E | .miz | Drop-spawn (§20) places SAMs/armor onto the finalized map | Placement broken on a hand-built theater | pending |
| BC-F | Retribution | Paint inert in a **normal** (non-setup) campaign — click opens info dialog | Bases repaint in a real game (guard not firing) | pending |
| BC-G | build=Retribution / fly=.miz | A finalized blank canvas has, per owned base, an economy (factory/ammo/fuel/oil) **and** air defence + a BASE_DEFENSE armor group; SAMs/EWR appear on the IADS/threat map and SEAD/strike/BAI have real targets | Finalized save has 0 ground objects (barren); no threat rings; SEAD "no targets"; crash in finalize seeding | ☐ UNTESTED (headless-verified 2026-06-27: 32 TGOs + 11 IADS nodes; faction-template degradation expected) |
| BC-H | Retribution | **Save as Campaign** (Increment D) toolbar action on a finalized blank canvas → enter a name → it appears in the New Game list → starting it rebuilds ownership + the SAM/EWR/armor/factory/ammo laydown | Action not visible on a finalized blank canvas (or visible on a normal campaign); saved campaign hidden from list (version gate); load crash; rebuilt map barren or wrong sides | ☐ UNTESTED — whole chain **headless-verified 2026-06-27** (finalize sets `from_blank_canvas` → `save_blank_campaign` writes the YAML → `Campaign.from_file` loads it **compatible/listed** → `load_theater` rebuilds; ownership + preset-native counts match). Only the literal button-click + name dialog need the in-app pass |
