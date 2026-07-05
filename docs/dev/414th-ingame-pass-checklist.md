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

### A3 — Player-manned QRA alert flight · §1 · ☑ VERIFIED (2026-07-01, user pass — "A3 good")
- **Verified (2026-07-01, user in-app/in-game pass):** the player-manned QRA alert flight generated and
  behaved per the pass criteria — no double-spawn, no depleted-pool error, the alert flight held over its
  own field. Fail signature did not occur.
- **Setup:** A BARCAP-capable, player-flyable squadron at an airfield; set its
  "…of which player-manned" spinbox (under QRA reserve) ≥ 1. Take the turn and generate.
- **Pass:** A cold-start BARCAP package named "QRA Alert (<squadron>)" appears in the player
  ATO, parked on the alert pad, flyable, orbiting **over its own field** (not pushed forward);
  the AI QRA dispatcher for that base fields the reserve **minus** the manned airframes (no
  duplicate jet both parked-as-player and air-spawned). Losses reconcile correctly at debrief.
- **Fail signature:** the alert flight's racetrack pushed forward toward the FLOT; the same
  airframe both manned and air-spawned by the dispatcher (double-spawn); a depleted-pool error
  on generation; or the AI dispatcher count not dropping when the player mans some.

### A4 — Player QRA scramble cue · §1 · ☑ VERIFIED (2026-07-01, user pass — "A4 good")
- **Verified (2026-07-01, user in-game pass):** the scramble cue fired as designed — no missing message,
  no spam, sane BRA. Fail signature did not occur.
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

### G10 — Combat SAR King TACAN beacon + LARS · Combat SAR Phase 4 · ◐ PARTIAL (2026-07-02 flown Trail 2 session `wonderful-chatterjee`: the 2026-06-30 activation fix WORKED — `dcs.log` shows the mission-start miss falling back cleanly ("not found/alive at mission-start; will retry") and then "activated … via birth (TACAN 37Y, LARS menu attached)" when the player boarded the King C-130; zero combatsar errors. Still owed = a wingman actually tuning 37Y to confirm the beacon radiates + an in-mission LARS menu use)
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

### G12 — Combat SAR extracts a stranded SOF team · Combat SAR + SCAR · ✗ RETIRED (2026-07-01 — the dormant SOF capture economy was removed; nothing can strand a team, so there is nothing to extract)
- The whole channel this row tested (`sofTeams` emission → `SOFRESCUE` CASEVAC → `combat_sar_sof_recoveries`
  → `commit_sof_recoveries` refund) was deleted with the rest of the dead commander-capture loop
  (features doc §15). The scoring layer had been headless-adjudicated 2026-06-26 but the path was
  unreachable in a normal campaign since the armor-hunt plugin was removed (#266). Do not re-fly.

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

### G19 — TARPS on Vietnam-era recon birds (RF-101B / RA-5C) · §3 · ◐ PARTIAL (capture-side gap ROOT-CAUSED + fixed 2026-07-01 via the `airecon` plugin; needs a re-fly)
- **Root cause of the "0 captures for AI survivors" gap + fix (2026-07-01).** Traced it to the MOOSE
  TARS film engine being **player-only**: `TARS.lua`'s birth handler does
  `if not unit or not unit:GetPlayerName() then return end`, so an AI-flown recon flight is dropped
  outright — no menu, no filming, no capture, *ever*, regardless of survival or overflight. So the AI
  recon birds could never confirm BDA; it was never a survivability or overflight bug on the capture
  side. **Fixed** by a new **`airecon` plugin** (features doc §3): Python emits each AI-flown,
  player-coalition `TARPS` flight + its target (`aireconluadata.py`), and the plugin records the enemy
  ground units at the target into the same `tars_recon_captures` ledger when the flight survives to
  overfly (within the trigger range), so the debrief credits it exactly like a player capture. A
  shot-down / aborting recon flight still confirms nothing. Emitter-tested; **needs a re-fly** to
  confirm a surviving AI recon bird now yields `tars_recon_captures` entries (was 0) and that
  `airecon` logs "armed for N flight(s)" / "captured N unit(s)" with no Lua error. The separate
  *survivability* work (tighter recon TOT offset, TARPS-only tasking) already landed below.
- **Tacview trace (2026-07-01, `Tacview-20260630-171831…`, per user request):** the earlier "all shot
  down" read was too strong. Tracing all four TARPS ships:
  - `BLOODHOUND TARPS #1` — **survived** to end of recording (bubble-culled far away = RTB, not a kill).
  - `BLOODHOUND TARPS #2` — **killed** at 00:56:17, ~941 m alt.
  - `RAVEN TARPS #1` — **killed** at 00:38:50, ~47 m alt (low — flew into terrain / shot down on the deck).
  - `RAVEN TARPS #2` — **survived** to end of recording (bubble-culled far away = RTB).
  So **2 of 4 died, one from each 2-ship survived** — the survivability picture is materially better than
  "recon bird always dies," consistent with the user's "seemed fine last time." **BUT `tars_recon_captures`
  is still `0`** — the two survivors produced **no BDA confirmation**. That reframes the gap: it is no longer
  purely survivability. Even a surviving TARPS ship isn't yielding a capture, which points at a **second
  issue** — either the survivors RTB'd **without overflying** the target (lead lost / abort), or the TARS
  capture path isn't firing for them. **Next diagnostic:** confirm whether either survivor actually crossed
  its target (needs the target coords from the `.miz` waypoints) before blaming the capture path.
- **Also seen in this Tacview (separate bug, likely stale-save):** RF-101Bs were **also** flying
  `Tbilisi-Lochini BARCAP` — the "recon bird auto-tasked BARCAP" bug the 2026-06-28 fix was supposed to kill
  (stripped `vwv_rf101b`/`vwv_ra-5` to TARPS-only). This campaign is a **turn-5 save on Caucasus** almost
  certainly **started before that fix** (a stale save freezes squadron capabilities at gen — see
  [[stale-save-vs-clobber]]), and the fix only touched the Khe Sanh squadron blocks, so a NEW game is needed
  to confirm the BARCAP-tasking is actually gone here.
- **Prior (2026-06-30, `state.json`):** `RAVEN TARPS #1` + `BLOODHOUND TARPS #2` in `crash_events`,
  `tars_recon_captures` empty — matches the Tacview (the two that died are exactly those two).
- **In-game (2026-06-28, audience pass — user: "fly the path for it but get shot down"):** the tasking + ingress half is confirmed — the RF-101B/RA-5C spawns clean on the `Retribution TARPS` loadout and flies the recon path — but it is **shot down en route to / over the target**, so the overflight→BDA-confirm half is never reached. The TARPS plumbing is structurally fine; this is a **survivability** gap (a lone, unescorted, weaponless recon bird into a Vietnam AAA/SAM environment). OPEN: harden survivability (escort, ingress altitude, routing, or a larger time offset behind the strikers) vs. accept it as period-realistic. PARTIAL until decided.
- **Altitude analysis (2026-06-28, read from code):** the RF-101B/RA-5C YAMLs set no `combat_altitude`, and `COMBAT_ALTITUDE_BAND_KFT = (20, 20)` (`game/dcs/aircrafttype.py`) flattens the estimate to **20,000 ft** regardless of speed — i.e. the recon overflight is **already above the 4500 m (~14,800 ft) flak ceiling**. So the AAA/flak gauntlet (§33) is **not** the killer, and *lowering* the bird (the intuitive fix) would push it **into** the AAA, not out of danger. At 20k ft, alone and ~5 min behind the strike package (`TarpsFlightPlan.default_tot_offset` = 5 min, after the package escort has egressed), the realistic killer is a **MiG (BARCAP)** or a **SAM** — so the right hardening is **escort coverage / recon timing / routing**, not altitude. NB `TarpsFlightPlan` is shared with the F-14 TARPS path (G2, VERIFIED) — any flight-plan change must not regress it; an altitude change should be data-only per-airframe (`combat_altitude:` in the YAML), but altitude is the wrong lever here. Kill-cause (MiG vs SAM) pending the user.
- **Kill-cause = MiGs (user, 2026-06-28) → FIX APPLIED.** Confirmed via `EscortFlightPlan.split_time`: the AI escort splits at the **strikers'** egress and turns back ~7–9 NM short of the target without loitering, so a recon bird +5 min behind flew the threatened ingress corridor **alone** after the escort RTB'd. Fix: keep it **high** (20k, above the AAA — unchanged) and **tighten `TarpsFlightPlan.default_tot_offset` 5 min → 2 min** so it ingresses **within** the package/escort window instead of as a lone straggler (`game/ato/flightplans/tarps.py` + 5 doc sites + `tests/test_tarps_recon.py`). Black/mypy/pytest green. **Shared with the F-14 path (G2):** the tighter offset is functionally safe for it (still a positive post-strike pass) but G2 wants a quick confirming re-fly. **Re-fly owed** on both — the recon bird should now survive to confirm BDA when the package has fighter cover (in a fighter-starved Vietnam turn with no escort planned it can still die, which is a campaign-balance matter, not this fix).
- **2nd bug (user, 2026-06-28): birds were auto-tasked ARMED RECON / Strike instead of a photo pass → FIXED.** The `vwv_rf101b`/`vwv_ra-5` YAMLs listed `Armed Recon: 435/410` + `Strike/BARCAP/CAS: 1`, and the `CAS` entry also auto-enriches `ARMED_RECON` (`aircrafttype.py` lines ~821-829). Auto-assignable = `aircraft caps − secondary_tasks` ∩ the campaign squadron config's `auto_assignable` (`{primary}|{secondary}|{TARPS}`), and Khe Sanh pinned `secondary: air-to-ground` on both recon squadrons — so the intersection handed these **unarmed** birds Armed Recon/Strike/CAS (they'd spawn with the weaponless TARPS loadout and fly an aborting attack). Fix: stripped both YAMLs to **`TARPS` only** (single-task is fine — tankers/AWACS are single-task) and removed the `secondary: air-to-ground` from both Khe Sanh squadron blocks. Guard test `tests/test_tarps_recon.py::test_vietnam_recon_planes_are_tarps_only` (asserts NOT capable of ARMED_RECON/STRIKE/CAS/BAI/BARCAP/ESCORT). Black/mypy/pytest green; Khe Sanh YAML re-parses + loads the two airframes. The bird should now only ever be fragged TARPS.
- **Context:** TARPS was extended off the F-14 onto the two dedicated Vietnam photo-recon ships —
  **RF-101B Voodoo** (`vwv_rf101b`, land-based) and **RA-5C Vigilante** (`vwv_ra-5`, carrier). They
  carry `TARPS: 700` as their primary task and a clean, weaponless **Retribution TARPS** payload
  (built-in cameras, empty pylons). The **1968 Yankee Station** campaign fields both `primary: TARPS`
  (RF-101B at Da Nang, RA-5C on the carriers). Headless-verified 2026-06-28: both report
  `capable_of(TARPS)`, the loadout resolves to `Retribution TARPS`, and `primary: TARPS` parses as a
  squadron config.
- **Setup:** Generate **1968 Yankee Station** with `auto_add_tarps_recon` on; let the
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

### G21 — Combat SAR AI rescue commandeers an on-station helo (no duplicate spawn) · §21 · ◐ PARTIAL (dispatch-error fix VERIFIED 2026-07-01 re-fly — 0 errors across 5 dispatches; the commandeer-vs-clone preference itself still unproven)
- **Re-fly (2026-07-01, flown Yankee Station session `intelligent-dubinsky` — `dcs.log` + Tacview):** the
  "table index is nil" dispatch error did **not** reproduce — zero `combatsar: AI dispatch error` lines across
  **5** AI rescue dispatches (`CombatSAR Rescue 4/5/9/11/13`, Mi-8s red + CH-53Es blue — the ledger ran
  coalition-generically on 4 separate ejections, 16 snatch parties spawned on both sides). The 2026-07-01 fix
  held. **Still unproven:** the commandeer preference — blue clones 11/13 spawned while the planned
  `Front line … Combat SAR|2|43|CH-53E` was still alive; it may have been legitimately busy with the earlier
  AH-1W-crew survivors (the artifacts can't distinguish busy from skipped), and red's planned Mi-8 died at
  t≈109 s so red's clones were correct fallback. No rescue *completed* inside the 33-min window
  (`combat_sar_rescues`/`combat_sar_captures` both empty at mission end — races still running), so watch a
  longer session for the divert message + a delivery. **Caveat:** this flight predates
  [#407](https://github.com/bradyccox/414Ret/pull/407) — red-side Combat SAR (the red dispatches 4/5/9 and
  the blue snatch parties racing red ejections observed here) has since been removed by squadron call;
  future sessions will only show the blue rescue/capture loop. The dispatch-fix evidence stands (same code
  path).
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
- **Root-cause fix applied 2026-07-01 (the "dispatch error / table index is nil" leg).** Traced the
  `Moose.lua:11714: table index is nil` to `DATABASE:_RegisterGroupTemplate` doing
  `Templates.ClientsByID[unit.unitId] = unit` for every Client/Player-skill unit — which throws when a
  client slot's template has a **nil `unitId`**. The Combat SAR rescue helos are player-flyable (Client
  skill), and the crash is on the **clone** path (`SPAWN(cfg.heloTemplate):Spawn()` →
  `DATABASE:Spawn` → `_RegisterGroupTemplate`; the commandeer path goes through `_RegisterDynamicGroup`,
  which never touches line 11714). Three changes in `combatsar-config.lua`:
  1. **Root cause — init sweep** (`sanitizeClientTemplates`): at plugin init, backfill a synthetic,
     collision-safe `unitId` (≥ 9000001) on any Client/Player template carrying a nil one, so
     registration never indexes a nil. `pcall`-guarded; only touches already-broken templates.
  2. **Bounded retry:** `dispatchAIRescue` now returns success; the caller only latches `e.dispatched`
     once it actually succeeds, retrying a *failed* dispatch up to 3× with a 20 s backoff (was: latch
     before dispatch, so one error abandoned the survivor forever).
  3. **Leak-proof commandeer:** the `busyHelos` mark now happens only on the success path, so a
     mid-dispatch error can't strand a commandeered helo as permanently busy (it stays available for the
     retry).
  Lua syntax gate green. **Needs a re-fly** to confirm the 11714 error is gone from `dcs.log` and every
  errored survivor now gets rescued (was 9 errored attempts / 3 completed).

### G22 — Captured-pilot POW recovery raid: planning crash + map marker · §15 · ✗ RETIRED (2026-07-03 CSAR rescope — the POW recovery raid is SHELVED: the `CSAR` raid flight type, the `CapturedPilotGroundObject` map objective, and `commit_pow_recoveries` are removed, so there is no raid to plan and nothing to re-fly. The held-POW model — freed by field capture, killed on the 4-turn clock, draining will — stays and is CI-tested in `tests/test_pow_recovery.py`. See `414th-csar-notes.md`.)
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

### G23 — Sandy AI dynamic retasking toward a live ejection · §15 · ✗ REGRESSED → rework applied 2026-07-02 (root-caused; needs a re-fly). **FROZEN, pass-or-delete (2026-07-03 CSAR rescope):** this re-fly is the divert's last chance — pass and it stays as-is (frozen, no further iteration); fail and the divert is deleted rather than reworked a third time (a player Sandy is untouched either way).
- **Fail signature reproduced (2026-07-02 flown Trail 2 session `wonderful-chatterjee`, user-confirmed):**
  an F-4E ejection at t=1118 registered a survivor (2 snatch parties spawned 2 s later ~11 km from
  Gudauta), the **"SANDY … is diverting to hold over the downed pilot" message fired** (user saw it),
  the A-1H Sandys closed to **24.2 NM** — inside the 30 NM `sandyMaxRangeNm` gate — yet Tacview shows
  **no Sandy ever left the racetrack** toward the survivor. No "Sandy dispatch error" lines: the Lua
  call succeeded, the sim ignored the task.
- **Root cause:** `dispatchSandy` used `SetTask(TaskCombo{ EnRouteTaskEngageTargetsInZone, Orbit })` —
  `EngageTargetsInZone` is an **en-route** task, which the DCS controller silently rejects inside a
  main-task ComboTask. Message-then-no-movement is exactly that signature.
- **Rework (2026-07-02, same session):** divert is now a **route push** — transit waypoint → hold
  waypoint over the survivor (450 m AGL) carrying the orbit + the en-route engage as *waypoint* tasks
  (the stock MOOSE transit-then-orbit pattern), so the flight physically transits; release routes the
  Sandy back to its recorded station (`entry.sandyReturn`) instead of a bare `ClearTasks()` (which
  would leave it flying a straight line, since the divert replaced its planned route).
- **Re-fly pass:** an AI Sandy visibly leaves the racetrack, flies to the survivor, orbits/engages
  there, and returns to station once the survivor resolves. **Fail:** message with no transit (again),
  a `combatsar: Sandy dispatch error` line, or the released Sandy wandering off in a straight line.
- **Context (user request, 2026-06-30):** after G21/G22, the user asked to build the AI Sandy
  retasking that G21's investigation found was designed-but-never-built (the code's own comment
  called it "a combatsar runtime follow-up for the AI"; a 2026-06-30 in-game report — "Sandy's did
  nothing but fly their orbit path" — was consistent with that gap, not a bug at the time).
- **Built (2026-07-01):** `luagenerator.py` now buckets `FlightType.SCAR` flights per coalition into
  `dcsRetribution.CombatSAR(.red).sandys` (group names, alongside the existing `kings`/`rescueHelos`
  — Sandy was previously **absent** from the CombatSAR data table entirely, so the runtime had no way
  to know which groups were Sandys). `combatsar-config.lua` builds `sandyByName`, and on every tick a
  survivor is `"down"`, `dispatchSandy` finds the nearest alive, idle, **non-player** Sandy within
  `sandyMaxRangeNm` (default 30 NM; imperial-unit rename 2026-07-01, was `sandyMaxRangeM`) and pushes
  a combo task — `TaskOrbitCircleAtVec2` (hold near the survivor, inheriting the Sandy's own current
  altitude/speed) + `EnRouteTaskEngageTargetsInZone` (actively hunts `"Ground Units"` within
  `sandyEngageRadiusNm`, default 3 NM) — replacing its planned racetrack task. Commits one Sandy per
  survivor (`busySandy`), retries every 5s `POLL` until one frees up, releases it (`ClearTasks()`,
  resuming its own planned route) once the survivor is rescued/captured/dead. A player-flown Sandy is
  never retasked (`groupHasPlayer` guard, same pattern as rescue-helo commandeering). Two new plugin
  options: `sandyMaxRangeNm`, `sandyEngageRadiusNm`.
- **Test coverage:** the Python bucketing/emission is unit-tested
  (`tests/missiongenerator/test_combat_sar_sandy_luadata.py` — a SCAR flight lands in `sandys`, never
  `rescueHelos`/`kings`; red/blue route to the right node; empty when no Sandy present). **The Lua
  runtime is entirely unflown** — no local Lua interpreter (CLAUDE.md constraint), read-verified only
  (balanced blocks, correct Moose API signatures cross-checked against `Moose.lua` — `TaskOrbitCircleAtVec2`,
  `EnRouteTaskEngageTargetsInZone`, `TaskCombo`, `SetTask`, `ClearTasks`, `GetVelocityMPS` all confirmed
  to exist with the parameter orders used). The Lua 5.1 syntax gate (CI, blocking) passed on the PR.
- **Setup:** A campaign with an AI-crewed Sandy (SCAR) flight in a Combat SAR package — `auto_combat_sar`
  on for the safety-net package, or a player-fragged package with an AI Sandy wingman/second flight.
  Eject an AI or player pilot near the FLOT within Sandy's `sandyMaxRangeNm`.
- **Pass:** Within one `POLL` (5s) of the ejection, the AI Sandy breaks from its racetrack, holds near
  the survivor's position, and actively engages any snatch party / hostile ground unit that enters its
  engage radius — visibly more assertive than passively orbiting its old box. A coalition message
  ("SANDY \<name\> is diverting…") announces the divert. Once the survivor is rescued/captured/dead, the
  Sandy resumes its normal patrol. A **player-flown** Sandy is completely unaffected (still just files
  its planned racetrack, no forced retask).
- **Fail signature:** no divert at all (Sandy stays on its old racetrack — check
  `dcsRetribution.CombatSAR.sandys` is populated in the generated `.miz` and `combatsar: Sandy dispatch
  error` in `dcs.log`); a **player-flown** Sandy gets yanked off its route (the `groupHasPlayer` guard
  failed); the Sandy never returns to patrol after release (`ClearTasks()` didn't resume the route); two
  survivors fight over the same Sandy (`busySandy` bookkeeping broken); a Lua error in `dcs.log`
  (`combatsar-config.lua` around `dispatchSandy`/`findFreeSandy`/`releaseSandy`).

### G24 — Concealed enemy field forces: uncertainty circles until scouted · §3 · ☐ UNTESTED (built 2026-07-05; the qualifier + jitter determinism/bounds are unit-tested — the map read + the play feel need an in-app pass + the CI client rebuild)
- **What it is:** with `concealed_enemy_forces` on (default ON, new campaigns), an **un-scouted** enemy
  field force — a mobile SAM site (MERAD/SHORAD/AAA), a deployed vehicle group, a missile site — shows
  as a dashed red **"suspected enemy activity" circle** (4 km; 3 km for vehicle groups) whose centre is
  **jittered off the true position** (deterministic per TGO — it must not wander between refreshes)
  instead of an exact marker. Fixed infrastructure stays exact: LORAD strategic sites, EWRs, buildings,
  ships, airfields, user-placed TGOs. The COIN insurgent spawns conceal intrinsically regardless of the
  setting (the P3 concealment bullet).
- **Setup:** NEW campaign (any theater — e.g. Red Tide), `recon_intel_fog` + `concealed_enemy_forces`
  on. Look at the turn-0 map, then fly/plan TARPS over a circled area and re-check.
- **Pass:** enemy MERAD/SHORAD/AAA sites, armor groups, and missile sites appear only as circles (no
  diamond at the true spot); LORAD/EWR/buildings/ships keep exact markers; the object is NOT at the
  circle centre; circles hold position across refreshes and turns; right-clicking a circle opens the
  package dialog (recon plannable); a TARPS pass / strike snaps the site to its exact symbol; the
  fog-overview reveal shows everything exact; turning the setting off restores all exact markers.
- **Fail signature:** a circle centred dead-on the site (jitter broken); marker AND circle both drawn;
  circles jumping between refreshes (seed broken); LORAD/EWR/buildings circled (qualifier too broad);
  a discovered/killed site still circled (`known_for` not consulted); the map unreadable around big
  bases (too many overlapping circles — the tuning lever is `FIELD_FORCE_RADIUS_M`/`CONCEALED_RADIUS_M`
  in `game/server/tgos/models.py`).

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
- **Default retune 2026-07-01 (imperial-unit options):** release range moved **8 → 3 NM** (`arcLightReleaseNm`)
  so the carpet lands with the bomber nearly overhead (matching the ~2.5–3 NM ballistic forward throw from
  ~30k ft) instead of firing a full minute early; carpet defaults re-expressed as 6,000×1,500 ft / 660 lb
  (≈ the verified 1700×500 m / 300 kg). Mechanics unchanged — the VERIFIED verdict stands; just note the
  carpet now appears later on the run-in.
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

### L2 — AAA flak gauntlet · §33 · ☑ VERIFIED (2026-07-01 flown Yankee Station session `intelligent-dubinsky`, user pass: bursts "light but fairer" after the 2nd softening — the too-accurate/lethal fail signature did not recur; player death that mission was a MiG gun kill, not flak. If it now reads *too* light, raise `flakPower`/narrow the miss band)
- **Second softening applied 2026-07-01 (L2 tuning owed from the 2026-06-28 pass).** The lethality that
  remained was the close **"tracking" round firing every 2.5 s tick** once a jet held a steady line for ~10 s
  (`factor > 0.8`), reading as a hard-kill rather than pressure. Changes (`vietnamops-config.lua` + matched
  `plugin.json` defaults): base misses **widened** `MIN_MISS` 110→**150** m / `MAX_MISS` 250→**320** m; the
  tracking round is now **occasional not constant** — gated behind a sustained steady run (`factor > 0.85`,
  was 0.8) **and** a per-tick probability (`TRACKING_CHANCE = 0.3`), and softened (`miss ×0.55→×0.75`,
  `blast ×2.0→×1.5`). Net: a predictable line now draws bursts ~90–210 m (was ~66–154 m) with only the
  *occasional* ~85–160 m close round instead of one every tick; jinking stays loose. `BLAST` unchanged (6).
  Lua syntax gate + `plugin.json` parse green. **Re-fly owed** to confirm the feel is right (pressure to
  manoeuvre, no hard-kill) — this is why the row stays PARTIAL.
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
  the current 6/4500 defaults, not a stale 8/5000. **RESOLVED BY THE 2026-07-01 IMPERIAL RENAME:** the
  flak options are now `flakRangeNm`/`flakCeilingFt`/`flakMinMissFt`/`flakMaxMissFt`/`flakBurstPower`
  (2.5 NM / 15,000 ft / 500 ft / 1,000 ft / 6) — the old metric keys are ignored, so every campaign
  re-seeds the softened defaults and the stale-`8/5000` mismatch can't recur. Re-fly on the new defaults.
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

### L3 — Naval gunfire support · §34 · ☑ VERIFIED (2026-07-04, user pass — "L3 good") (was ☐ UNTESTED: emitter test-covered; both runtime modes are Lua, need a cockpit pass. 2026-07-02 Trail 2 session `wonderful-chatterjee`: armed cleanly — 2 BLUE gun ships, auto on, zero errors — but the carriers' escorts sat 40+ NM offshore, no red ground within the 10 NM gun range and no player F10 fire mission called, so **zero ship gun events**: the coastal-by-construction no-op behaved correctly, the firing legs remain unflown. To exercise it, drop an F10 mark on coastal red within ~10 NM of an escort)
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

### L4 — Vietnam compressed-theater support-orbit standoff · PR #314 · ☑ VERIFIED (2026-07-01, user map read — working as designed; tuning question open)
- **Verified (2026-07-01, user in-app map read):** the AEW&C/tanker orbit reads "fine" on the planner map —
  sits ~**40–50 miles** (≈65–80 km) behind the front, matching the headless calc (83/74 km at the 25/20 NM
  buffer) and clear of the map edge. The fail signature (orbit ~150 km back / flung to the edge) did not
  occur — the PR #314 tightening is confirmed applied on a live campaign.
- **⚠️ Tuning question (user, 2026-07-01): "40–50 miles seems pretty long."** This is the tightened value
  *working as designed* — but the user still finds it far for a compressed Vietnam theater. If we want it
  closer, the lever is the per-campaign `aewc_threat_buffer` / `tanker_threat_buffer` (currently 25/20 NM);
  dropping them further pulls the orbit in, at the cost of less standoff from forward threats. **Not a bug —
  a balance call.** Left VERIFIED (the fix works); a follow-up buffer-tune is optional. NB the orbit also
  carries a racetrack half-length on top of the buffer, so the *near* end sits closer than the buffer figure
  alone.
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
- **Pass:** Selecting **Vietnam** → the next (Theater) page is titled "Vietnam" and lists **only** the
  `era: vietnam` campaigns (1968 Yankee Station, Velvet Thunder, Red Flag 81-2); selecting one still pre-loads its settings +
  recommended factions. Going **back** and choosing "Play an included campaign" restores the full list;
  "blank canvas" still shows the terrain picker. The "Show incompatible campaigns" toggle keeps the Vietnam
  filter applied.
- **Fail signature:** no Vietnam radio; Vietnam shows all campaigns (filter not applied) or an empty list;
  switching back to "included" stays filtered; the "show incompatible" toggle drops the era filter; a crash
  arriving on the Theater page.

### L6 — Convoy interdiction (Steel Tiger) · §35 · ◐ PARTIAL (2026-07-02 flown Trail 2 session `wonderful-chatterjee`: the reworked real-convoy runtime leg PASSED — `Convoy 001` (2× PT-76 + Grad-URAL, real force-model units) drove the trail road, the player Armed Recon Phantoms found it and killed all 3 with Mk-82 Snakeyes (Tacview removals t=3195/3609/3610); still owed = the debrief leg — next-turn processing must record the loss as `enemy_convoy` so the units never arrive. ⚠ blocked on the REAL server-side `state.json` — the dedicated host wrote it to its **TEMP fallback**: `dcs.log` says "The state.json file will be created in TEMP : (C:\Users\admin.dcs\AppData\Local\Temp\state.json)" (no `RETRIBUTION_EXPORT_DIR` set on the server + the client installPath doesn't exist there); the local `Missions\state.json` the user first pulled is a stale Jun-20 file from a different campaign. Fetch the TEMP file to process the turn, and set `RETRIBUTION_EXPORT_DIR` on the server for a stable path going forward)
- **Sizing/variety rework (2026-07-03), re-opens the runtime leg.** Player feedback off the above flight
  ("only 3 vehicles, only 1 convoy") drove a rework in `game/fourteenth/vietnam_convoy.py`: a
  concurrent-convoy **budget** (`BASE_MAX_CONVOYS` 1→2, `SURGE_MAX_CONVOYS` 2→3 under `trail_surge` ≥ 2.0)
  replaces the old "is one already flowing" check, and `_pick_trail_corridor` gained `exclude_sources` so
  filling the budget **prefers distinct roads** — several campaigns (Yankee Station/Steel Tiger's full
  trail network, Khe Sanh's two rear feeders, Red Flag 81-2's aggressor corridors) genuinely have more
  than one opfor-opfor road to spread onto. A single-corridor map still caps at one convoy (no regression).
- **Root cause found + fixed same day: the real gate was an empty rear economy, not the cap.** A headless
  engine load found every rear opfor CP's `Base.armor` at **zero at turn 0** across all 4 land Vietnam
  campaigns — it's the coalition's production/income stock, not a garrison, so turn 1 (when the flown
  session above found only 3 vehicles) genuinely had almost nothing to skim regardless of
  `MAX_CONVOY_UNITS`. `_seed_trail_source` now tops a picked source to a standing stock (2× a convoy load,
  same bound as the pre-existing COIN ratline) before every skim — from the coalition's real
  `Faction.frontline_units` roster outside COIN, framed as external logistics support (the Ho Chi Minh
  Trail's actual historical character — matériel from China/the USSR, not local production).
  `MAX_CONVOY_UNITS` also raised 4→10 now that it's the real constraint. **Verified with a real engine
  load** (turn 1): Yankee Station spawned 2 convoys of 10 units each on 2 distinct roads (20 vehicles
  total, vs. the old 3-vehicle single column); Khe Sanh spawned 2 convoys of 10 on its 2 rear feeders. 19
  unit tests updated/added (`tests/fourteenth/test_vietnam_convoy.py`, `tests/fourteenth/test_red_tempo.py`),
  all green; mypy/black clean; full suite green (1433 passed).
  **Re-fly pass:** confirm more than one convoy can be on the map at once on a multi-corridor campaign
  (Yankee Station/Steel Tiger/Khe Sanh/Red Flag 81-2), each on a visibly different road, each carrying up
  to 10 vehicles — a visibly bigger trail than the original single 3-4 vehicle column.
- **Known gap, flagged not fixed:** `operation_velvet_thunder.yaml` has **no `supply_routes` block at
  all** — its theater (Marianas islands: Guam/Rota/Tinian/Saipan) has no roads between the separate
  islands for a convoy to drive, so `vietnam_convoy_interdiction: true` is a silent no-op there. Either
  drop the toggle from that campaign or design an island-appropriate reinterpretation (naval convoy?) —
  out of scope for this session.
- **What changed:** the convoy is no longer a `vietnamops`-plugin `coalition.addGroup` phantom (a free,
  unrecorded unit). It is now a **real, tracked enemy convoy** created in the force model
  (`game/fourteenth/vietnam_convoy.py` `ensure_enemy_trail_convoy`, run once per turn from `finish_turn`):
  it skims a few of the opfor's real rear units and moves them toward the front via a real `TransferOrder`,
  so interdicting it denies real reinforcements and the loss is recorded as `enemy_convoy`. The prior
  2026-06-30 runtime-cycle verification no longer applies (there is no runtime spawn to verify).
- **Headless adjudication:** `tests/fourteenth/test_vietnam_convoy.py` locks the corridor pick (nearest
  opfor→opfor road, ignores the opfor→friendly front), the unit skim (fraction cap), the guards (setting off /
  convoy already flowing / turn 0 → no-op), and that a real `TransferOrder` of skimmed rear units is created.
  `test_vietnamops_luadata.py` asserts the emitter never emits a `convoy` node. The end-to-end convoy spawn +
  BAI-objective + loss-recording is engine behaviour that only a flown turn exercises.
- **Setup:** Start a **NEW** game with **Vietnam Ops → Convoy interdiction** on (a Vietnam campaign with an
  enemy supply road behind the front — Khe Sanh). Advance a turn so `finish_turn` runs, then inspect the map.
- **Pass:** a **real red convoy** is present on a road behind the front (visible on the map, and offered as an
  **Armed Recon / BAI objective**); flying the Armed Recon and destroying it registers an **enemy_convoy loss**
  at debrief and those units **do not arrive** at their destination CP (the source CP's armour dropped by the
  skimmed count when the convoy was created). Right-clicking the enemy supply route still frags Armed Recon
  onto that corridor (L7).
- **Fail signature:** no convoy ever appears despite the opfor having rear armour and a road corridor (corridor
  pick / transfer creation broken); the convoy isn't a targetable objective; killing it records nothing at
  debrief (it wasn't a real `Convoy` — check `arrange_transport` took the Road leg); the source CP is gutted
  (skim cap wrong).

### L7 — Right-click supply-route interdiction · §35 · ☑ VERIFIED (2026-07-04, user pass — "L7 good") (was ☐ UNTESTED after 2026-07-01: "still nothing" root-caused to a STALE LOCAL CLIENT BUILD, not a code bug — client rebuilt, needs a re-test)
- **2026-07-01 — "still nothing" is a build problem, not the feature.** The user right-clicked an enemy
  supply route and nothing happened (same as the prior session). Root cause confirmed: the local checkout's
  `client/build/static/js/main.9ba023ba.js` was dated **June 23** and contained **zero** occurrences of
  `create-package/supply-route` — i.e. the compiled client predates the feature (merged in #349/#351). The
  **source** on `main` is correct (`SupplyRoute.tsx` `contextmenu` → `useOpenNewSupplyRoutePackageDialogMutation`;
  the hook + endpoint in `_liberationApi.ts`), it was just never compiled into what the user runs
  (`run_retribution.bat` serves the local `client/build`, not a CI build). **Fix applied 2026-07-01:** rebuilt
  the client (`cd client && CI=false npm run build`) → new bundle `main.c050b70d.js` **does** contain the
  endpoint; the stale bundle is replaced. **Re-test after restarting the app** (or run the fresh `latest`
  release, which ships a CI-built client). This is the same stale-`client/build` trap as the
  [[local-client-rebuild-for-react-features]] memory — any React feature needs a client rebuild the local run
  won't do automatically.
- **Headless adjudication (unchanged):** the server resolution is test-covered
  (`tests/server/test_supply_route_interdiction.py`); only the React `contextmenu` → Qt dialog path needs the
  in-app pass — now unblocked by the rebuild.
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

### L8 — Airbase harassment (rocket/mortar siege) · §36 · ◐ PARTIAL (2026-07-01 flown Yankee Station session `intelligent-dubinsky`: armed for 4 fields, user saw the "Incoming — standoff fire on …" cue in-mission → the barrage loop fires past the grace period; the impacts themselves + the player-spawn-field exclusion not yet visually confirmed. 2026-07-02 Trail 2 session `wonderful-chatterjee`: armed for 3 red fields (Sukhumi/Gudauta/Senaki) with all 5 blue player fields excluded in the emitted data, zero errors across a 90-min mission — the Python-side exclusion held by construction; the visual impact confirm still owed)
- **Headless adjudication:** `game/missiongenerator/tests/test_vietnamops_luadata.py` locks the emitter — a
  forward, occupied airfield/FARP is emitted; a rear / neutral / carrier / off / no-front field yields no node;
  a **lone client-spawn field yields no node** and a client-spawn field alongside an enemy field is excluded
  from the targets but listed under `excludedFields`. The scheduled per-field loop, the grace period, the
  randomized cadence, and the `trigger.action.explosion` placement are runtime Lua, exercisable only live.
- **Setup:** A Vietnam campaign with **Vietnam Ops → Airbase harassment** on and a forward, **AI-occupied**
  enemy airfield/FARP within ~200 km of the front (Da Nang / Khe Sanh laydowns qualify). Fly (or fast-forward)
  past the startup grace period (default 5 min) and watch the enemy ramp.
- **Pass:** After the grace period, small dispersed explosion barrages land near the enemy field's parking area
  on a sporadic cadence, with an "Incoming — standoff fire on <field>" cue to the owning side. **Your own spawn
  field(s) are never touched.** `dcs.log` shows "Airbase harassment armed for N field(s)" and no Lua errors.
- **Fail signature (the #1 watch-item): ANY impact on or near a client-spawn field** — the anti-grief guarantee
  is broken. Also: fire during the grace window; a steady metronome instead of a sporadic cadence; impacts
  wildly off the ramp (centroid/dispersion wrong); too lethal to parked jets (dial power/dispersion down, as
  §33 flak needed); a `trigger.action.explosion` / `land.getHeight` / `timer.scheduleFunction` Lua error.

### L9 — Super Gaggle hilltop resupply · §37 · ◐ PARTIAL (2026-07-01 `intelligent-dubinsky` runtime run PASSED; **2026-07-02 Trail 2 session `wonderful-chatterjee`: second clean run — both CH-53Es closed to 140 m of FOB Khe Sanh at t≈306, returned, landed and shut down; BOTH F-4E suppressors (`SuperGaggle-T1-Sandy-1/-2`) were shot down (t=973 — its wreck also killed a friendly soldier — and t=2897), so the loss-accounting leg is finally armed**: after the turn is processed with the real server `state.json`, the next-turn debrief must charge 2 F-4E airframes to the suppressor squadron and 0 CH-53s — that check is what remains)
- **Launch-delay rework (2026-07-03), re-opens the runtime leg.** The flown pass above found the whole
  run over by t≈306 s — the helos spawn at t=0 (mission-config load, before anyone can plausibly be
  airborne). `resources/plugins/vietnamops/vietnamops-config.lua`'s Super Gaggle block now wraps the
  entire spawn (helos, suppressors, cue, F10-mark tick) in a local `spawnGaggle()` and fires it via
  `timer.scheduleFunction(..., timer.getTime() + DELAY)` instead of immediately; `DELAY` defaults to
  **600 s** (new plugin option `gaggleDelaySec`). The "armed … launching in Ns" log line still fires at
  config time so ops get immediate confirmation; only the spawn itself is deferred.
  **Re-fly pass:** confirm nothing spawns before `DELAY` elapses, the delayed run then behaves exactly
  like the already-verified 2026-07-02 pass (delivery, losses charged), and a `dcs.log` warning appears
  (not a silent failure) if the deferred `spawnGaggle` call ever errors.
- **Partial (2026-07-01, flown session — Tacview + `dcs.log`):** `dcs.log` shows `Super Gaggle armed
  (outpost FOB Khe Sanh, 2x CH-53E, single run)`; `SuperGaggleHelos` (2× CH-53E, the committed real-squadron
  airframes by name) + `SuperGaggleSandy` (2× F-4E suppressors) spawned **once** at t≈73 s. Tacview: the helo
  pair launched from Sochi-Adler, flew the 13 km run and **overflew FOB Khe Sanh at t≈300 s** (~180 m), then
  returned, loitered and **landed back at the launch field** — no re-roll, no respawn, no `coalition.addGroup`
  error. The Sandys escorted the run window (Sandy-1 landed + despawned at ~1,076 s). **Unexercised:** both
  helos survived, so the debrief charge-back (`reconcile_super_gaggle`) and the outpost ground-strength credit
  weren't stressed — the row's key check still needs a session where a gaggle helo is shot down.
- **What changed:** the gaggle is no longer a phantom, unbounded-respawn `coalition.addGroup` spawn. It is
  planned once per turn from **real BLUE squadrons** (`game/fourteenth/super_gaggle.py` `plan_super_gaggle`),
  spawns **exactly** the committed airframes (by name) **once** (no respawn), and a shot-down committed airframe
  is charged back to its squadron at debrief (`reconcile_super_gaggle`). The **key new check** is the loss
  accounting, not the spawn.
- **Headless adjudication:** `tests/fourteenth/test_super_gaggle.py` locks the plan (draws real squadron
  airframes, counts capped by `owned_aircraft`, clears when off / no outpost / no helo squadron) and the
  reconcile (charges only killed committed names, floors at 0, credits delivery on any-helo-survival, clears the
  commitment). `test_vietnamops_luadata.py` locks the emitter (serializes the commitment; no commitment → no
  node). The runtime helo spawn + routing + the single-run cue are Lua, exercisable only live.
- **Setup:** A Vietnam campaign with **Vietnam Ops → Super Gaggle** on and a **friendly forward FOB/FARP** near
  the front plus a friendly rear airfield/FARP to launch from (Khe Sanh laydown qualifies), and a BLUE
  helicopter squadron with airframes. Advance a turn (so `plan_super_gaggle` runs), then fly/fast-forward.
- **Pass:** a helo gaggle drawn from the real helo squadron (its own aircraft type) spawns over the launch
  field, flies to the outpost, and announces "SUPER GAGGLE inbound … Marked on the F10 map" then "delivered" on
  arrival — **once, no re-roll**. A **live F10 map mark** tracks the gaggle the whole way (moves with the lead
  helo, disappears on delivery/loss) so it's findable and escortable from anywhere on the map. `dcs.log` shows
  "Super Gaggle armed (outpost …, Nx …, single run)". **Critically:** a shot-down gaggle helo shows up at
  debrief as a **real airframe loss to that squadron** (its `owned_aircraft` drops); a clean delivery bolsters
  the outpost's ground strength.
- **Choreography:** a fast-mover suppression flight (the committed attack squadron's airframes) spawns with the
  gaggle, flies over the outpost, and its losses are likewise charged back. The suppressors spawn with their
  squadron aircraft's default loadout — confirm whether they actually attack the AAA or are visual-only. A
  suppressor spawn failure must NOT affect the helo run (guarded); the cue then omits the "fast movers" line.
- **Fail signature:** no gaggle despite a helo squadron + outpost + launch (plan/commitment broken); the gaggle
  **re-rolls** (respawn not removed); a killed gaggle helo is **not** charged to the squadron at debrief (the
  loss-accounting failed — its unit name didn't reach the debrief killed lists, or the squadron-id lookup
  missed); the outpost isn't bolstered on a clean run; a `coalition.addGroup` / `Group.getByName` Lua error in
  `dcs.log`; the squadron owned count goes negative (floor failed).

### L10 — FAC(A) willie-pete target marking · §38 · ☑ VERIFIED (2026-07-02 flown Trail 2 session `wonderful-chatterjee` — user confirmed the named FAC(A) F10 map mark appeared at the target; the mark is unambiguously the plugin's, since the Bronco's own WP rockets make no F10 mark. Armed cleanly in `dcs.log`, zero Lua errors; the OV-10s worked the front ~23 min before being shot down at t=1382. Earlier ambiguity from `intelligent-dubinsky` — smoke that might have been the AI's own rockets — resolved by the 2026-07-02 findability pass's named mark)
- **Headless adjudication:** `game/missiongenerator/tests/test_vietnamops_luadata.py` locks the `fac` on-marker
  (emitted when `vietnam_fac_marking` is on, independent of the other suite features; off = no node). The
  runtime OV-10 discovery, the nearest-enemy scan, and `trigger.action.smoke` placement are runtime Lua,
  exercisable only live.
- **Setup:** A Vietnam campaign with **Vietnam Ops → FAC(A) marking** on and a friendly **OV-10 Bronco**
  airborne over the front within ~3 NM of enemy ground (the campaigns field OV-10 CAS squadrons). Fly near a
  Bronco working the battle area and watch for the smoke.
- **Pass:** the Bronco periodically drops **white** smoke on the largest enemy ground concentration in range
  **and** a named **F10 map mark** appears there (e.g. "FAC(A): BTR-60 x6 — willie pete, cleared hot"), with a
  "FAC: … marked — see F10, cleared hot" cue to its coalition; `dcs.log` shows "FAC(A) marking armed". The F10
  mark refreshes as the FAC re-marks and is the tell that distinguishes the feature from the Bronco's own WP
  rockets (rockets leave no map mark).
- **Fail signature:** smoke lands on friendlies or empty ground (wrong side / no nearest-enemy gate); no smoke
  despite an OV-10 over enemy ground (type-name mismatch — confirm `Bronco-OV-10A` is the mod's DCS type, or
  set `facType`); wrong smoke colour; a `trigger.action.smoke` / `land.getHeight` / `getTypeName` Lua error;
  the mark cadence is far too frequent (smoke spam) or never fires.

### L11 — Snake and nape (napalm CAS) · §39 · ◐ PARTIAL (**player leg VERIFIED** 2026-07-02 flown Trail 2 session `wonderful-chatterjee`: 4 real player Snakeye deliveries, zero plugin errors, and the user confirmed the split exactly matched the gate — Toxic's two in-gate passes (≈119 m and ≈111 m AGL at 153/274 m/s vs the 152 m / 93 m/s gate) bloomed the fire walls ("it was awesome"), Bulldog's two above-ceiling passes (≈213 m and ≈177 m AGL) correctly drew none. Still owed = the **AI leg**: an AI CAS/BAI flight pressing to the §P1c 500 ft deck and tripping the release gate itself)
- **Detonation-anchored (2026-07-02 rework — this row tests the NEW trigger):** fire now keys off a **real
  eligible-bomb release** (weapon type name vs the `napeWeaponPatterns` option, default `SNAKEYE`; Mk-77 cans
  excluded — Splash Damage owns real napalm) made from a low + fast **release profile**, with each weapon
  tracked to impact and one fire node + bite laid **at the real impact point**. A dry pass lays nothing; a
  miss burns where it missed; the swath is your actual ripple.
- **AI leg (2026-07-02 — the doctrine low-level attack profile, supersedes the "player-only in practice"
  note):** the 2026-07-01 diagnosis (AI attack flights never fly the deck — the session's A-1s sat at
  6,400 m, so AI could never pass the release gate) is now addressed in the planner:
  `Doctrine.low_level_attack_altitude` (Vietnam = 500 ft, = the `napeCeilingFt` default) presses Vietnam
  **CAS/BAI/Armed Recon** plans onto the deck (RADIO/AGL legs; Strike/helos/heavies exempt — §39 features
  note). Gate helper + waypoint clamp are unit-tested; **the flown question** is whether the DCS AI's own
  `AttackGroup` delivery then releases ≤ 500 ft AGL or climbs to dive-bomb anyway. Watch an AI Interdiction/
  CAS A-1/A-4 with Snakeyes over the front: **pass** = it runs in low and its impacts lay §39 fire; **fail
  signature** = the flight presses in at ~500 ft AGL but pops to altitude at the attack and no fire lays
  (next levers: `altitude=` on the BAI `AttackGroup` task, or raise `napeCeilingFt`). Needs a NEW game
  (doctrines pickle by value). Terrain check rides along: no AI CFIT on the low legs in Caucasus valleys.
- **Headless adjudication:** `game/missiongenerator/tests/test_vietnamops_luadata.py` locks the `snakeNape`
  on-marker (emitted when `vietnam_snake_and_nape` is on, independent of the other suite features; off = no
  node). The `S_EVENT_SHOT` matching, the release-profile gate, the weapon tracking/`land.getIP` impact
  resolution, and the `effectSmokeBig`/`explosion` placement are runtime Lua, exercisable only live.
- **Setup:** A Vietnam campaign with **Vietnam Ops → Snake and nape** on. **Fly it yourself** in anything
  carrying **Mk-82 (or Mk-81) Snakeyes** (A-4/A-1/F-4 etc. — no aircraft-type gate any more): ripple a pair+
  off a **low, fast** delivery (≤500 ft AGL, ≥180 kts ground speed at release) onto enemy ground. Also fly
  one **control**: a dry low pass (no release) and, if flying the A-4E-C, one **Mk-77** drop.
- **Pass:** each Snakeye impact point erupts in a smoke-and-fire node a beat after release (at the bombs'
  fall line — the ripple draws the wall of fire), nearby soft targets take the extra bite, and one
  "SNAKE AND NAPE — napalm on the deck" cue appears per salvo (not per bomb); the fires burn ~90 s then stop;
  the dry pass lays **nothing**; a deliberate miss burns at the miss point, not on the target; a Mk-77 drop
  shows only the Splash Damage napalm (no doubled §39 fire on top); `dcs.log` shows "Snake and nape armed
  (release gate …, ordnance 'SNAKEYE' …)" with no Lua error.
- **Fail signature:** no fire despite a low/fast Snakeye release (the **weapon type name doesn't match the
  pattern list** — the #1 suspect, esp. mod-pack Snakeyes; check `dcs.log`, widen `napeWeaponPatterns`); fire
  at the release point or the aircraft instead of the impacts (tracking/`land.getIP` bug); fire on a dry pass
  (release gate broken); a doubled effect on Mk-77 (exclusion broken); fires never stop (permanent infernos —
  `stopEffect` failing); a cue per bomb instead of per salvo; an `S_EVENT_SHOT` handler error in `dcs.log`
  (the handler is pcall-wrapped — any "snake-and-nape shot handler error" line counts); it triggers from
  altitude or at low speed (the release ceiling/speed gate wrong); the bite far too strong/weak
  (`napeBlastPower`).

### M1 — Political will pacing & feed weights (campaign layer W1+W2; 2026-07-04 morale-ratchet redo) · §48 · ☐ UNTESTED (the **pre-redo** 2-line-override economy got a user "M1 good" pass 2026-07-04 — but the **same-day morale-ratchet redo re-tuned the whole economy** (design note §8): BLUE ratchet + POW sore, RED broadened past the trail, the escalation tax + richer opening, so the shipped numbers are new and the earlier pass no longer covers them. Numbers derived with `tools/will_pacing_model.py` (elite folds Hanoi ~turn 8, average → Linebacker II win ~turn 16, flounder → withdrawal ~turn 11); the model is play-archetype driven, so the *played* pacing of the redo is exactly this row. The verified-good pre-redo baseline is the sanity floor: the redo should feel no worse)
- **Headless adjudication:** the feed model and the negotiation verdict are locked in
  `tests/fourteenth/test_political_will.py` (weighted losses, POW trickle, rescue refund, clamps, off-switch,
  win/loss/precedence, crossing-edge banners) and the SITREP band in the sitrep tests. What CI *cannot*
  adjudicate is **pacing**: whether the design-§7 weights drive either side to zero on a satisfying arc
  (~15–30 turns of a normal Vietnam campaign), or collapse/stall the war absurdly fast/slow.
- **Setup:** a NEW Vietnam campaign (any of the four — `vietnam_political_will` preseeds on). Play several
  turns normally; read the per-turn "Political will" message + the SITREP will band. The 2026-07-02
  **attribution ledger** is the instrument for this pass: hover the ribbon WILL/RESOLVE meters (or read the
  SITREP "Will movers"/"Enemy resolve movers" lines) to see exactly which feed moved the number each turn —
  tune weights from that, not from guessing.
- **Pass:** both meters move visibly each flown turn but neither side loses double digits from an ordinary
  turn; a B-52 loss or a POW visibly dents BLUE; convoy kills visibly dent RED; a quiet turn heals slightly;
  the arc feels like it *would* resolve in 15–30 turns of consistent play; the movers lines name the feeds
  you'd expect from the turn you just flew.
- **Fail signature:** will collapses in <5 turns of normal play (weights too hot — halve the loss weights);
  the meters barely move by turn 10 (too cold); the passive regen out-heals ordinary attrition so the meters
  pin at 100 (regen too high vs. weights); the exhaustion banner fires repeatedly every turn at zero
  (crossing-edge regression); a non-Vietnam campaign shows the will message at all (gating regression).
  Tune the `BLUE_*`/`RED_*` weights in `game/fourteenth/political_will.py` — or, since the 2026-07-02
  will-profile generalization, per campaign via a `will: weights:` YAML block (no code change; see
  `414th-will-generalization-notes.md`). The new warship feed (`blue_ship_lost`/`red_ship_lost`) barely
  moves on the Vietnam defaults — a sunk vessel showing an outsized will swing means a profile weight, not
  this pass.

### M2 — Static front holds the band (campaign layer W2b) · Vietnam campaign layer · ☑ VERIFIED (2026-07-04, user pass — "m2 good") (was ☐ UNTESTED, built 2026-07-01; clamp math + arm/disarm/anchor fully unit-tested, the multi-turn map behaviour needs a played campaign)
- **Headless adjudication:** the band math, arm/disarm idempotence, anchor-once capture, and the real
  `FrontLine` clamp path at strength extremes are locked in `tests/fourteenth/test_static_front.py`. What CI
  *cannot* adjudicate is the **multi-turn map feel**: whether a ±10 % band reads as a living siege line over a
  played campaign (pressure visibly bends the front) rather than a dead-still one, and that the interplay with
  captures behaves in a real game.
- **Setup:** a NEW Vietnam campaign (any of the four — `vietnam_static_front` preseeds on). Play several turns
  letting the ground war swing (win some front engagements, lose some); watch the front line on the map.
- **Pass:** the front visibly shifts turn-to-turn with the strength battle but stays inside a narrow band
  around its campaign-start position; neither side's front ever reaches/captures a base by ground sweep even
  after a lopsided run of turns; a deliberate **Air Assault still captures** its target base; a non-Vietnam
  campaign's fronts sweep exactly as before.
- **Fail signature:** the front sits pinned dead-still across turns while strengths swing (clamp too tight /
  band effectively 0 — check `STATIC_FRONT_BAND` and that the anchor wasn't captured from an already-clamped
  position); the front walks onto a base and captures it (arming missed — `apply_static_front` not running in
  `initialize_turn`, or the setting didn't preseed); an Air Assault fails to capture (the clamp leaked into
  the capture path — it must only touch `_blue_route_progress`); a **non-Vietnam** campaign's front stops
  short of a base it should capture (disarm/gating regression — the clamp must clear when the setting is
  off). Knob: `STATIC_FRONT_BAND` in `game/fourteenth/static_front.py`.

### M3 — Campaign phase arc & planner emphasis · §40 · ◐ PARTIAL (2026-07-01 live Khe Sanh session: ribbon + arc expander + phase copy render correctly on the rebuilt client, authored opening = Rolling Thunder as expected; still owed = a Tier-0 (non-Vietnam) campaign's inferred arc pacing + visible ATO tilt across a transition)
- **Headless adjudication:** the §3.2 thresholds (SAM floor, peer guard, offensive gate), §3.3 hysteresis
  (dwell, monotonic-forward, the asymmetric regression margin), the §3.4 legibility string, the update
  gating/idempotence, and the `PlanNextAction` reactive-prefix/emphasis contract are all locked in
  `tests/fourteenth/test_phases.py`. What CI *cannot* adjudicate: whether the inferred arc **advances at a
  believable pace** over a real campaign and whether the emphasis **visibly shifts the ATO** without starving
  anything critical.
- **Setup:** any campaign (default ON). Ideal probes: a dense-IADS modern campaign (should open in Air
  Superiority) and a genuine below-floor campaign — Shattered Dagger / Battle for No Man's Land / Valley of
  Rotary / Northern Guardian (should open in Interdiction; **not** Khe Sanh — the generator fills 4 SA-2/SA-3
  batteries there, so it opens in Air Superiority per the #379 engine-authoritative all-66 table). Read the
  phase on the map ribbon + the kneeboard cover band; play/auto-resolve turns while SEAD attrites the belt.
- **Pass:** the opening phase matches the engine-authoritative all-66 draft table for the campaign; the
  ribbon/cover show the same phase + a sensible "why" line; as the SAM belt drops below ~half, the campaign
  announces and enters Interdiction (after the 2-turn dwell), and the BLUE ATO visibly tilts (more
  BAI/Armed Recon/OCA, less DEAD-first); with the front advancing and IADS <30 % it enters Offensive (CAS/
  capture-weighted); the phase never regresses; red planning and reactive defense (BARCAP/QRA/DefendBases)
  look unchanged; toggling `campaign_phases` off clears the ribbon band and restores stock planning.
  **2026-07-02 additions** (need a client rebuild): each expander row shows its **objectives checklist**
  (the measurable IADS goals tick ✓ as the belt drops — verify a tick actually flips across a played
  transition) and its **transition line** ("Advances once the enemy IADS falls below 50%…" on Tier-0 rows;
  "Escalates early if will falls below 65 (now …)" with live values on the current authored phase).
- **Fail signature:** phase flaps turn-to-turn (dwell broken); a genuine below-floor campaign opens in Air
  Superiority (floor gate miscounting — check `_enemy_sam_sites`, which bands enemy TGOs by `GroupTask`
  LORAD/MERAD, the DEAD planner's own target set, NOT `IadsRole`); the phase never leaves Air
  Superiority though the belt is dead (air-threat signal stuck — check red air-superiority squadron counts);
  the ATO shows no tilt at all across a phase change (emphasis not reaching the planner — check
  `_offensive_order` and that the coalition is BLUE); defensive flights change with the phase (§17 boundary
  breach); the ribbon shows nothing on a new game (client build stale — the L7 lesson — or
  `campaign_status` missing from `/game`); a transition announces every turn (message-once regression).
  Knobs: the `ROLLBACK_SAM_FLOOR`/`IADS_*`/`PHASE_MIN_DWELL_TURNS` constants in `game/fourteenth/phases.py`.

### M4 — ROE escalation arc: zones, target release, will coupling (campaign layer W4) · §40 · ◐ PARTIAL (2026-07-01 live Khe Sanh playthrough, session jolly-einstein: **phase-1 AI obedience VERIFIED** — turn-1 save `Hanoi.retribution` adjudicated headless: 10 BLUE packages (1 CAS / 5 BAI / 3 STRIKE / 1 CSAR), **0 ROE violations**, 34 legal vs 42 locked red TGOs, no planner starvation; **scheduled Halt transition VERIFIED in-game** — turn 8 entered The Bombing Halt on the min_turn pin, zone expanded 20→28 NM, tooltip detail + "Eases at Linebacker (~turn 11)" correct. **Linebacker release redirect VERIFIED** — turn-11 save adjudicated: entered Linebacker on schedule, zone shrunk 28→8 NM (inner ring), STRIKE volume 3→11 with targets pouring onto the freed classes (ware ×4 / factory / comms ×2 / power / fuel), Armed Recon onto the released airfields (Senaki-Kolkhi, Kobuleti), census 34→58 legal, still 0 AI violations. **Linebacker II VERIFIED** — turn-16 save: zone list empty, no locked classes, full arc 1→8→11→16 ran exactly as authored across one fast-forwarded campaign. Still owed = the player-violation will penalty firing live (needs a flown strike into an active zone) + the M1/M2/M5 flown-combat rows. Known observation, not a regression: at Linebacker tempo all strike escorts prune (fighter pool fully consumed by BARCAP/support first — the documented deferred 'reserve a fighter ahead of BARCAP' lever, see the always_escort_strikes note))
- **Headless adjudication:** authored-arc parsing (all 4 Vietnam YAMLs guarded in
  `tests/test_vietnam_content.py`), sequential/scheduled/will-accelerated advancement, the planner ROE gate
  (zone + locked class), and the violation counter are locked in `tests/fourteenth/test_phases.py`. What CI
  *cannot* adjudicate: whether the arc **feels like Rolling Thunder** in play (restraint that visibly binds,
  then releases) and whether the AI planner meaningfully redirects rather than starves.
- **Setup:** a NEW Vietnam campaign (arcs ship in all four). Open the map: the **red dashed sanctuary
  circles** (Kutaisi/Hanoi + Senaki/Haiphong plus the permanent Tbilisi "PRC border" ring at Yankee
  Station/Steel Tiger — the coastal-ladder recast; Sukhumi at Khe Sanh, Saipan at Velvet Thunder) should
  draw, and deep factories/airfields inside show **RESTRICTED — ROE** on hover. Play turns through the arc
  (Bombing Halt ≈ turn 8, Linebacker ≈ 11, Linebacker II ≈ 16 — earlier if your will bleeds).
- **Pass:** phase 1: the BLUE auto-planner never frags strike/OCA into the zone or against locked classes
  (factories/power/airfields), while the front/trail war runs normally; **you** can still strike the zone —
  the package dialog shows the amber **pre-flight "⚠ ROE" warning** (2026-07-02) when you frag it, the
  strike flies anyway, and doing so posts "ROE violation" and visibly dents Political Will next debrief
  (read the exact −4/kill on the meter-hover attribution ledger); transitions announce
  once, the ribbon/kneeboard track the arc ("phase 2 of 4"), zones shrink at Linebacker and vanish at
  Linebacker II (except the permanent PRC ring on the Yankee Station/Steel Tiger laydown, which must keep
  drawing and keep the AI off Tbilisi forever), after which the planner hits the deep targets; a non-Vietnam
  campaign shows no zones and plans stock, and its package dialog never shows the ROE line.
- **Fail signature:** the AI strikes into the sanctuary in phase 1 (gate not reached — check
  `roe_blocks_target` wiring in `PackagePlanningTask.fulfill_mission`); the player is hard-blocked from
  striking the zone (enforcement must stay soft); no will penalty after a zone kill (violation counter not
  seeing debrief positions); the arc never advances (min_turns/`advance_when` mis-parsed — check the YAML) or
  skips straight to Linebacker II on turn 1 (min_turn 0 bug); the zone circle doesn't draw (client build
  stale — the L7 lesson — or `restricted_zones` missing from `/game`); zones linger after Linebacker II
  (stale `active_restricted_zones`); the planner deadlocks with nothing to strike in phase 1 (locked-class
  list too broad for that campaign's target set — trim `locked_targets` in the campaign YAML).

### M5 — GCI-ambush MiGs: late scramble, one slash, home (campaign layer W5) · §1 · ☑ VERIFIED (2026-07-02 flown Trail 2 session `wonderful-chatterjee` — the 40 NM late-launch trigger measured in Tacview: Sukhumi 4-ship scrambled with the nearest BLUE at **37.6 NM**, Senaki 4-ship at **31.5 NM**, both inside the 40 NM cap; slash + leash already VERIFIED 2026-07-01 `intelligent-dubinsky`)
- **Verified (2026-07-02, flown multiplayer session `wonderful-chatterjee` — `Tacview-20260702-171945-…-Trail 2`):**
  both red GCI scrambles launched **late**, exactly per the W5 design: the Sukhumi ambush 4-ship spawned at
  t=460 s with the nearest BLUE aircraft (the front-line TARCAP F-4E) **37.6 NM** from the field; the
  Senaki 4-ship at t=1150 s with the nearest BLUE (HIPPO Escort F-8E) **31.5 NM** out — no launch at the
  100 NM setting border. All 8 MiG-17Fs fought close (37mm gun events in `dcs.log`, no BVR) and were
  progressively lost t=1064–3594 — the posture works; MiG survivability is a balance observation, not a
  mechanism failure. No `intercept-config.lua` errors.
- **Partial (2026-07-01, flown session — Tacview `Tacview-20260701-225522-…retribution_nextturn` + `dcs.log`):**
  a red `Intercept|Sukhumi-Babushara|…` MiG-17F pair launched at t≈460 s, ran a **close** intercept into the
  Gudauta fight (~25 NM from its base), and **gunned down the player's F-4E** (Flash, Gudauta Armed Recon) at
  ~1,150 m with the MiG inside ~1–2 km — a slashing merge, no BVR duel. The lead was traded (killed by a GAR-8
  at t≈876 s); the survivor **broke off** after the fight, climbed to ~4,500 m and egressed SE toward home
  plate — no chase-to-map-edge, no fight-to-destruction, no `intercept-config.lua` error in `dcs.log`. The
  leash behaviour (one slash, disengage, RTB at altitude) is exactly the W5 design. **Not yet measured:** the
  40 NM late-scramble trigger (couldn't reconstruct which raid the dispatcher launched against, so the launch
  radius is unconfirmed) and blue-side parity.
- **Headless adjudication:** `Doctrine.gci_ambush` (Vietnam-only), the `dispatcher_tuning` radii math
  (engage → 22 NM cap range, scramble capped at 40 NM, tighter settings still win), the `ambushPosture`
  record serialization, and the W4 sanctuary-basing fallout (an airfield inside a zone can't be OCA'd) are
  all locked in tests. What CI *cannot* adjudicate: the actual Moose defender behaviour under the leash
  (`SetDisengageRadius` 50 NM + fuel threshold 0.35).
- **Setup:** a NEW Vietnam campaign; fly a BLUE strike package toward a red QRA field (with the Rolling
  Thunder sanctuary active, the MiG base itself is un-OCA-able — the classic problem). Watch `dcs.log` /
  the F10 map for the red scramble.
- **Pass:** MiGs scramble **late** (raid inside ~40 NM of the field, not at the 100 NM border), run a
  **close** intercept (engage ≤ ~22 NM — a slashing merge, not a BVR duel), **break off** rather than chase
  beyond ~50 NM from their base, and RTB early on fuel — the raid gets hit once, hard, and the MiGs live to
  ambush again next mission; blue QRA (same doctrine) behaves alike; a modern campaign's QRA is byte-for-byte
  unchanged (settings pass through).
- **Fail signature:** MiGs still launch at the full setting radius (tuning not reaching the record — check
  `dispatcher_tuning` wiring / `ambushPosture` in the generated `dcsRetribution.Intercept`); defenders chase
  to the map edge or fight to destruction (leash not applied — the records[1] read or the
  `SetDisengageRadius`/`SetDefaultFuelThreshold` calls); no scramble at all (backstop/detection regression —
  unrelated to W5, see A2); a Lua error in `intercept-config.lua` (the `AMBUSH_*` locals are file-scope,
  defined before build_dispatcher — verify load order if edited). Knobs: `AMBUSH_GCI_RADIUS_NM`
  (interceptluadata.py), `AMBUSH_DISENGAGE_NM` / `AMBUSH_FUEL_THRESHOLD` (intercept-config.lua).

### M6 — Phase-coupled red tempo: halt surge, Easter pulse, resolve regen (campaign layer W6) · Vietnam campaign layer · ☐ UNTESTED (built 2026-07-01; parse/window/stance/regen/convoy-surge all unit-tested, the multi-turn campaign feel needs a played arc)
- **Headless adjudication:** the `red_tempo:` parse, the ground-offensive window math, the raise-only
  stance pulse, the once-per-turn regen guard, the end-to-end convoy surge (second column + doubled skim),
  and the 4 arcs' authored blocks are all locked in `tests/fourteenth/test_red_tempo.py`. What CI cannot
  adjudicate: the multi-turn *feel* — whether the Halt reads as a logistics window and the Linebacker-entry
  ground pulse reads as the Easter Offensive.
- **Setup:** a NEW Vietnam campaign (Khe Sanh or Yankee Station) with `vietnam_political_will` +
  `vietnam_convoy_interdiction` on; play (or fast-forward) into the Bombing Halt (~turn 8) and across the
  Linebacker entry (~turn 11).
- **Pass:** during the Halt, up to TWO trail convoys flow at once with bigger loads (Armed Recon has
  visibly more trail targets) and Hanoi's resolve ticks UP ~1.5/turn on the Stats will chart while blue's
  deep war is locked; on Linebacker entry, red front stances go aggressive for ~3 turns (the front presses
  BLUE inside the W2b band — pressure, not sweep-captures) with the trail surging alongside; after the
  pulse window red reverts to the commander's own stance choices; a modern (non-authored) campaign shows
  zero change.
- **Fail signature:** resolve regenerating every init of the same turn (the `red_tempo_regen_turn` guard);
  red stances stuck aggressive after the window (the raise should stop applying — check
  `ground_offensive_active` window math); three+ convoys stacking (the `max_convoys` cap); a Tier-0
  campaign surging (only *authored* phases may carry `red_tempo` — check `_active_authored_phase`).
  Knobs: the per-phase `red_tempo:` YAML values; `GROUND_OFFENSIVE_MIN_SURGE` (red_tempo.py).

### M7 — ROE zone shapes: box/corridor painted on the F10/ME map (Path A) + `from_drawing` reader (Path B) · §40 · ☐ UNTESTED (built 2026-07-02/03; parse/resolve/containment/rotation + the drawing reader/resolver locked in `tests/fourteenth/test_phases.py` + `test_zone_drawings.py`, painter/latlng + real `.miz` write/reload seams engine-probed; the drawn shapes + the ME round-trip need an in-game eyeball)
- **Headless adjudication (Path A):** `_parse_restricted_zone` (circle/box/corridor + the rejects),
  `_resolve_zone` geometry, `zone.contains` for all kinds, and box `heading` rotation are locked in
  `tests/fourteenth/test_phases.py`; a real-pydcs probe confirmed `add_freeform_polygon` (box 4-pt, corridor
  buffered) and `point_in_world(...).latlng()` serialize cleanly.
- **Headless adjudication (Path B):** `read_zone_drawings` (Circle → circle, FreeFormPolygon → polygon, skips
  Rectangle/Oval/TextBox/unnamed) is locked in `tests/fourteenth/test_zone_drawings.py` via a real
  `dict()`→`load_from_dict` round-trip; `from_drawing` parse + `_resolve_drawing_zone` in
  `test_phases.py`; a probe wrote a `.miz` with a drawn circle + polygon, reloaded it via `Mission.load_file`
  (the `MizCampaignLoader` path), and read both back. What CI *cannot* adjudicate: whether DCS renders the
  painted zones on the F10 map, whether they land where authored, and whether a shape drawn by hand in the ME
  is read back correctly.
- **Setup (Path A):** author a `box` and a `corridor` `restricted_zones` entry into an active phase of a
  Vietnam campaign's `phases:` block (see §40 for the schema), start a NEW game, generate the mission, open the
  `.miz` in the ME (or fly it and check the F10 map).
- **Setup (Path B):** draw a FreeFormPolygon and a Circle on the campaign `.miz`'s Author layer, name them,
  reference them with `{from_drawing: "<name>"}` in an active phase, start a NEW game.
- **Pass:** the box (rotated per `heading`) and the corridor lane appear as red dashed shapes on the F10/ME
  map at the authored location, matching the web map layer; a `from_drawing` zone gates the planner + paints
  identically to a typed one; a legacy circle zone is unchanged; a player kill inside any zone drains will.
- **Fail signature:** a box/corridor drawn in the wrong place or orientation (the `_box_corners` heading
  convention or the freeform-polygon offset anchoring — anchor must be `outline[0]` with local offsets, per
  `generate_routes`); a `from_drawing` zone resolving to nothing ("references ME drawing … not found" — name
  mismatch, or the drawing is a Rectangle/Oval which v1 skips, or it's unnamed); the web map showing a shape
  the F10 map doesn't (they share `active_restricted_zones`, so a divergence is a rendering bug on one side).
  Knobs: `ROE_ZONE_LINE`/`ROE_ZONE_FILL` (drawingsgenerator.py); the corridor buffer resolution + the
  supported-drawing-types list (`zone_drawings.py`).

### M8 — COIN positive-control valleys: box/corridor no-strike ROE in play · §40 · ☑ VERIFIED (2026-07-04, user pass — "m8 good") (was ☐ UNTESTED, built 2026-07-03; ROE-shape rework replaced the earlier free-fire kill boxes with 4 box/corridor restricted valleys, all-phase, CI-locked in `tests/fourteenth/test_coin.py` (4 zones/phase — 2 box + 2 corridor, no free-fire); the played feel + red rendering need a campaign)
- **Headless adjudication:** the 4 restricted valleys (2 corridors + 2 boxes) parse, resolve to shapely
  geometry, and are shared across all 3 phases; no phase carries free-fire; the ROE gate + violation weight
  are unit-tested. What CI *cannot* adjudicate: the red box/corridor pockets rendering (web + F10 painted
  outline), whether the AI planner still fields strike/BAI packages with the valleys off-limits (it should —
  the desert and the caches stay legal), and whether striking near the towns actually bleeds the mandate.
- **Setup:** a NEW "Afghanistan - Operation Enduring Resolve (COIN)" game. Check the web map + the F10/ME
  map on turn 1 (Disrupt); the 4 valleys are permanent, so they look the same across the arc.
- **Pass:** 4 red dashed no-strike areas on the map — the two corridor lanes (Helmand green zone
  Kajaki→Marjah; the Musa Qala 611 feeder) + two boxes (Tarin Kowt bowl, Delaram junction) — matching
  between the web map and the F10/ME map; the kneeboard CAMPAIGN PHASE band lists them as OFF LIMITS; a
  player fixed strike *inside* a valley drains the mandate with an "ROE violation" note; a strike in the open
  desert does not; Armed Recon vs trail convoys flies anywhere and never counts; retaking a stronghold (air
  assault) never drains the mandate even when the CP sits in a valley.
- **Fail signature:** AI planner starvation (zero strike packages — the valleys resolved but swallowed every
  legal target; the caches should still be strikeable in the desert edges); a capture bleeding the mandate
  (an air assault mis-counted as a fixed strike); the box/corridor outlines missing while the gate works (a
  render-only bug — the server payload `restricted_zones` vs `RestrictedZonesLayer`, or the
  `DrawingsGenerator` outline); violations counted for convoy kills (the `target_class is None` exemption
  failed).
  Knobs: the `&population_centers` restricted-zone anchor in `coin_enduring_resolve.yaml` (valley
  extents/widths); `blue_roe_violation` weight (the CDE price).

### M9 — Commitment ceiling: will-coupled war budget draws down (§48) · §48 · ☐ UNTESTED (built 2026-07-04; multiplier shape + gating + message unit-tested in `tests/fourteenth/test_commitment_ceiling.py`; the played draw-down feel + the loss-spiral risk need a campaign)
- **Headless adjudication:** `will_budget_multiplier` is 1.0 at/above will 60, ramps linearly to 0.5× at
  will 0; `apply_commitment_ceiling` cuts only BLUE income, only with both `vietnam_commitment_ceiling` +
  `vietnam_political_will` on, and messages on the cut. What CI *cannot* adjudicate: whether the budget cut
  feels like meaningful pressure without a death spiral (less budget → fewer replacements → more relative
  losses → less will), and whether the message reads clearly in a flown campaign.
- **Setup:** a NEW 1968 Yankee Station game (both toggles preseed on). Play a *losing* line (take losses,
  ignore the trail) so BLUE will drops below 60; watch the Finances dialog + the "War budget cut" message.
- **Pass:** while BLUE will ≥ 60 the war budget is untouched; below 60 the per-turn income is visibly trimmed
  (a "War budget cut" message names the %); at very low will the cut approaches but never exceeds 50%; RED's
  income is never touched; turning `vietnam_commitment_ceiling` off restores full funding. The pressure feels
  like a squeeze, not an unrecoverable spiral.
- **Fail signature:** the cut triggers while will is still healthy (threshold wrong); RED income is cut
  (BLUE-only gate failed); the budget hits zero (floor failed); the message spams every turn at low will
  (it should fire only on turns the cut applies); the player is locked into an unrecoverable death spiral
  (floor too low / ramp too steep — raise `CEILING_FLOOR_MULT` or `CEILING_FULL_WILL`).
  Knobs: `CEILING_FULL_WILL` (where the cut starts) + `CEILING_FLOOR_MULT` (the floor) in
  `game/fourteenth/commitment_ceiling.py`.

## N. Mod support

### N1 — High Digit SAMs Ultimate Compilation units in-game · §41 · ☑ VERIFIED (2026-07-04, user pass — "n1 good") (was ☐ UNTESTED, built 2026-07-01; unit data read from the installed mod, factions/presets/layouts headless-verified)
- **Headless adjudication:** every new unit name resolves, all presets/layouts load, and all 25+ touched
  factions parse and strip correctly with the toggle both ways (the id-correct `remove_vehicle` fix verified
  headless). What CI *cannot* adjudicate is DCS itself accepting the unit type ids at spawn and the runtime
  behavior of the new sites.
- **Setup:** the Ultimate Compilation (v1.4.3+) installed; a NEW campaign vs. a modern Russia faction
  (russia_2020 / redfor_current) with the "High Digit SAMs - Ultimate Compilation" toggle ON. For the period
  layer, a Vietnam campaign with the toggle ON (the P-37 Bar Lock EWR; for SA-7 launches use a 70s
  Middle-East red like syria_1973 — the Vietnam factions deliberately carry no SA-7).
- **Pass:** S-400 / S-300V4 / SAMP-T / S-300PT sites generate and the mission loads without a "unit type not
  found" DCS error; their threat rings render at the new ranges; MANTIS resolves them into the IADS (the
  "resolved N/M SAM" dcs.log line counts them) and they engage at standoff; Pantsir-SM fills SHORAD slots;
  SA-7 infantry actually launch (syria_1973 etc.); the P-37 feeds MANTIS EWR detection on period red factions; insurgent
  ZU-23 technicals spawn at AAA sites.
- **Fail signature:** DCS refuses the mission / silently drops a group (a type-id typo — cross-check the id
  against the mod's `entry.lua` unit list); MANTIS logs "Could not match radar data" AND the site never
  wakes (the banding override failed — check `dcsRetribution.RedAA` emits the group); a 40N6E site
  dominates a small map absurdly (keep the `SA-21/S-400` preset out of small campaigns); SA-7 teams never
  fire (manpad class/attribute mismatch).

## O. Client map

### O1 — Local DCS chart base layer renders + aligns · §42 · ☐ UNTESTED (built 2026-07-01; routes test-covered, tiles generated locally; needs an in-app pass + the CI client rebuild)
- **What CI covers:** the `/map-tiles` listing/serving routes (meta parse, malformed-meta skip, 404s,
  traversal guard) are unit-tested, and the tiler ran clean over Flappie's Caucasus GeoTIFF. What CI cannot
  adjudicate is the chart actually rendering in the app and *aligning* with the campaign overlays.
- **Setup:** tiles installed at `Saved Games\Retribution\MapTiles\caucasus_flappie` (slice with
  `tools/tile_geotiff.py` if absent); any **Caucasus** campaign loaded; a client build that includes the
  base-map button.
- **Pass:** a "DCS Caucasus chart" button appears in the map layers panel's base-map row; selecting it swaps
  the basemap to the chart with no gray holes inside the theater at zooms ~6-12; control points / front
  lines / TGO markers sit on the chart exactly where they sat on Esri imagery (spot-check an airfield: the
  CP marker on its chart runway symbol); the choice survives a reload; on a machine/dir without tiles the
  button simply doesn't appear.
- **Fail signature:** markers visibly offset from the chart (georeference/tiling math bug — check one tile's
  bounds against the TIFF's ModelTiepoint); gray tiles inside the theater (pyramid gaps — re-run the tiler);
  the button never appears with tiles present (GET `/map-tiles/` — malformed `tileset.json` is skipped with
  a server-log warning); the map goes blank after selecting (tile URL/port mismatch — the layer URL must ride
  `HTTP_URL` like every other backend call).

---

### P1 — COIN Enduring Resolve: the living insurgency in play · COIN C-series · ☐ UNTESTED (built 2026-07-02; the whole stack headless-verified on the real campaign — regen/revival, cache throttle to the 0.25 floor, will profile, 3-phase arc — the played feel needs a campaign)
- **Headless adjudication:** the campaign loads through the real `GameGenerator` pipeline (probe 2026-07-02):
  13 insurgent strongholds each carry their authored ammo caches (28 total), `coin_state` anchors all 13
  (garrison + eligible-cell caps + cache totals), killing cells revives at 2/turn toward the anchor and never
  past it, killing both of a stronghold's caches drops its regen to the 0.25 floor, `will_profile_for`
  resolves "The Coalition's mandate"/"the insurgency's momentum" with `red_cache_lost` 4.0, and the
  Disrupt → Clear and Hold → Break the Momentum arc parses with the coordinate-anchored Lashkar Gah/Herat
  population-center rings. What CI cannot adjudicate is the **played loop**.
- **Setup:** NEW campaign "Afghanistan - Operation Enduring Resolve (COIN)" (all COIN toggles preseed on).
  Play 5+ turns: strike a stronghold's cells one turn WITHOUT touching its caches; recon it two turns later.
  Then kill both its caches and repeat.
- **Pass:** the cleared cells come back within ~2 turns while caches stand (and the recon-fog picture shows
  them dead until re-reconned — "it's shooting again"); after the caches die the same stronghold visibly
  stops refilling (floor trickle only); the will message reads mandate vs momentum with cache kills as
  labeled "ammo caches xN destroyed" movers; trail convoys flow (the ratline); FOB standoff fire lands on
  forward fields; the phase ribbon opens on "Disrupt the Network"; a strike near the Lashkar Gah ring draws
  the ROE warning in the package dialog and a violation drains the mandate.
- **Fail signature:** strongholds never refill (regen dead — check `coin_insurgency` survived the preseed and
  `coin_state` anchors exist / anchor caps are 0); refill continues at full rate with all caches dead
  (throttle broken); revived units invisible in the next mission (TGO revival not reaching the generated
  miz); the will message shows Washington/Hanoi (profile lookup failed — name mismatch degrades to defaults);
  the arc opens on a Tier-0 phase (authored parse failed); zone rings missing from the map (x/y anchor bug).

### P2 — Long-range carrier ops: the boat joins the war · §44 · ☑ VERIFIED (2026-07-04, user pass — "p2 good") (was ☐ UNTESTED, built 2026-07-03; the deterministic package is engine-probe verified on the real COIN save — Hornet Strike x2 + A-6E Refueling + E-2C AEW&C off the boat, valid flight plans + shared TOT, plus the commander flying spare Hornets on SEAD — the played feel needs a campaign)
- **Headless probe:** on the user's 2026-07-03 Enduring Resolve save, `plan_carrier_strike` fragged
  `PKG → target = F/A-18C Strike x2 + A-6E Refueling x1 + E-2C AEW&C x1`, all departing the carrier, with valid
  flight plans (13/5/7 waypoints) and a shared TOT; the range-gate preseed (`max_mission_range_planes: 600`)
  made the carrier air assignable so the commander also flew spare Hornets on SEAD. What CI cannot exercise is
  the **in-mission behaviour** — the A-6 actually giving gas on ingress/egress/recovery and the E-2 holding a
  useful AEWC orbit at that standoff.
- **Buddy-tanker routing (added 2026-07-03):** the commander's carrier SEAD Sweep/Escort Hornets used to get a
  refuel waypoint ~560 km from the A-6 (a dry tank). `route_carrier_flights_to_buddy_tanker` now pins them onto
  the A-6 orbit — probe-verified on the same save: both carrier SEAD Hornets' REFUEL waypoints moved from ~560 km
  away to 0 km from the A-6 orbit center, land-based flights untouched. In-mission tanking still needs a fly.
- **Setup:** NEW campaign "Afghanistan - Operation Enduring Resolve (COIN)" (`long_range_carrier_ops` preseeds
  on). Generate turn 1 and inspect the ATO / fly the carrier package.
- **Pass:** exactly one carrier strike package appears each turn — a Hornet strike section off the boat onto an
  enemy target (a cache when one is legal), with the A-6E tanking the package (launch join + egress/recovery)
  and the E-2 airborne on station; the land air still fights the rest of the war and spare Hornets show up on
  SEAD. The Hornets reach the target and RTB to the boat with the A-6's help, **and the carrier SEAD Hornets
  tank from that same A-6** (their refuel point is on the A-6 orbit, not up-range dry).
- **Fail signature:** carrier still idle (range preseed didn't take / `long_range_carrier_ops` off — check the
  campaign `settings:` block survived); Hornets launch but the A-6/E-2 don't (they pruned — confirm they are
  primary flights, not refuel escorts); two carrier packages a turn (the `_already_planned_from` guard broke);
  the package fragged into a population ring (ROE filter bypassed); Hornets can't make it home (TOT/fuel math
  off at the 400-500 NM standoff — the tanker orbit isn't being used).

### P3 — COIN re-infiltration: the insurgency retakes ground · COIN C1.5 · ☐ UNTESTED (built 2026-07-03; the staged pipeline / eligibility / conservation bound / stage machine / flip + will handoff are fully unit-tested with fakes, and the campaign preseed + module wiring are headless-verified — the real TGO spawn + engine capture flip + the played feel need a campaign)
- **Fiction-kit note (2026-07-04):** the infiltration cell now shares the P4/P5/P6 unit retype (`_spawn_cell` → `cell_unit_types`) — an armed technical + infantry rather than the faction front-line armor. First-fly should confirm the seeded cell reads as an insurgent element.
- **What CI cannot exercise:** the real `ForceGroup.generate` spawn of a red cell/cache near a blue/neutral target (attached to the source stronghold, per the allegiance constraint), the engine-native `ControlPoint.capture` flip, and the reparent of the seeded cell+cache onto the flipped CP. The design note itself flags this as in-play-only (timers need tuning against real Shattered Dagger geometry).
- **Setup:** NEW "Afghanistan - Operation Enduring Resolve (COIN)" (`coin_reinfiltration` preseeds on). Clear an insurgent stronghold's approach and take a nearby base, then **leave it ungarrisoned** (≤ 4 ground units) while the source stronghold still has healthy caches. Play ~5+ turns watching the info feed.
- **Pass:** an intel line "infiltration reported near {base}" appears; a real red cell shows up near that base on the next mission; ~2 turns later "a supply cache has been located" + a cache TGO; ~2 turns after that the base **flips to red** with a small garrison and one cache, and the mandate drops with a labeled "strongholds re-infiltrated x1" will mover. Each stage is strikeable: killing the cell aborts (+cooldown), killing the cache reverts a stage, garrisoning the base above 4 units aborts it, and killing the source stronghold's caches stops new attempts. The total red base count never exceeds turn 0.
- **Fail signature:** the cell/cache render **blue** (allegiance/reparent bug — they must attach to the red source stronghold); an attempt starts against a garrisoned/player-spawn/out-of-range base (eligibility gate); the red base count grows past turn 0 (conservation broken); a flip fires with no warnings (stage timers skipped); the mandate doesn't move on a flip (`consume_reinfiltration_flips` / will handoff not wired); the flipped CP comes back at full strength instead of the weak re-anchor.
- **Concealed "in here somewhere" areas (covers P3–P6, added 2026-07-05):** an **un-reconned** hidden insurgent object (re-infiltration cell P3, roadside IED/VBIED P4, HVT convoy P5, dispersed cell P6) no longer draws an exact marker at all — the web map shows a **dashed red uncertainty circle** (~4 km, centre jittered off the true position server-side; the true coordinates never reach the client) with a "Suspected insurgent activity — fly recon to localize" tooltip. The circle is clickable/right-clickable like a marker (frag TARPS/CAS onto it); once TARPS/attack discovers the TGO it **snaps to the exact symbol** at the real position. Caches and the stronghold garrisons stay exact (infrastructure). Needs an **in-app pass + the CI client rebuild**: on Enduring/Inherent Resolve confirm new IEDs/HVTs/cells appear as circles (not diamonds), the object is NOT at the circle centre, the circle doesn't wander across refreshes/turns, recon snaps it to the marker, and the fog-overview reveal shows everything exact. **Fail:** a circle centred dead-on the object (jitter not applied / seed broken), the marker AND circle both drawn, the circle jumping between refreshes (non-deterministic seed), a revealed/killed object still circled (`known_for` not consulted), or caches/garrisons circled (concealed flag leaked to non-hidden spawns).
- **Map symbology (covers P3–P6, added 2026-07-03):** insurgent contacts must read on the map as an insurgency, not an armor park. Two observables: **(a) suspect-until-reconned** — an un-reconned insurgent contact shows as a **SUSPECT** track (yellow frame); after TARPS/strike confirms it, it flips to **HOSTILE** (red). **(b) real NATO symbol** once confirmed — infantry for a re-infiltration cell (P3) / dispersed cell (P6) / a stronghold's standing militia, the IED activity glyph for a roadside IED (P4), the dismounted individual-leader glyph for an HVT (P5); ammo caches keep the cache symbol and the fixed radar-SAM crust keeps its air-defense symbol. All the SIDCs (hostile + suspect framings) were render-verified in the pinned milsymbol 3.0.4 (distinct valid glyphs), so this is a look-right confirm, not an unknown. **Fail:** a confirmed contact still draws the hostile-armor diamond (`sidc_entity_override` didn't reach the TGO / the garrison pass didn't run), an un-reconned contact shows hostile-red immediately (suspect framing not applied — check `recon_intel_fog` is on), the SAM crust or a friendly unit turns into infantry (composition scope leaked), or any contact draws an empty "unknown" frame (wrong entity code for the pinned lib).

### P4 — COIN roadside IEDs: sweep the trail or pay · COIN · ◐ PARTIAL (2026-07-04, user pass — "good but needs reworked"; **REWORK APPLIED 2026-07-04** in two parts: fiction-kit retype + IED-vs-mobile-VBIED variety with an in-mission suicide-vehicle drive (see the two rework bullets); **REWORKED AGAIN 2026-07-05** — the static variant is now a static-object emplacement + security team (third rework bullet) — needs a re-fly to confirm the static emplacement reads right AND the VBIED variant drives at a friendly base and is interceptable) (was ☐ UNTESTED, built 2026-07-03; the fuse state machine / clear-vs-detonate / concurrent cap / road-nearest-the-front placement / mandate feed are fully unit-tested with fakes, and the campaign preseed + red-red ratline are verified — the real emplacement spawn + recon-fog visibility + played feel need a campaign)
- **Rework (2026-07-04) — fiction-appropriate unit kit.** The COIN objects were generated as trimmed FRONT_LINE force groups with only the *map symbol* overridden, so the metal underneath was the faction's armor (a BMP-1 wearing an IED icon on a conventional faction; a plain technical on Toyota). `spawn_red_ground_at` now takes a `unit_types` list and `_retype_units` (`game/fourteenth/coin.py`) re-points the trimmed units' DCS *types* (+ names) to kit drawn from the red faction's own roster: an **IED = a lone soft supply truck** (`ied_unit_types`), an **HVT = a leader's jeep + a 2-rifle escort** (`hvt_unit_types`), a **cell = an armed technical + infantry** (`cell_unit_types`). On the Enduring Resolve Toyota Al Gaib faction that resolves to Ural-375 / UAZ-469 + 2× Insurgent AK-74 / DShK gun-truck + Insurgent AK-74 (verified headless). Selection reads only the faction's resolved roster (never a hardcoded, possibly-unregistered id) and no-ops to the old generated group if the faction can't fill the roles. Covered by `tests/fourteenth/test_coin_units.py`. **Re-fly = confirm the IED now reads as a suspicious truck (not a combat vehicle) and is still findable+killable.**
- **Rework (2026-07-04, part 2) — static IED vs mobile suicide VBIED + in-mission movement.** Each plant now deterministically alternates a **static roadside IED** (buried, `FUSE_TURNS` 3) and a **mobile VBIED** — a suicide vehicle that drives for the nearest friendly base (`_nearest_blue_cp`) on a shorter `VBIED_FUSE_TURNS` (2). Same fuse→detonation→`ied_detonations`→mandate consequence; distinct "intercept it before it arrives" / "VBIED reached {base}" messaging (`game/fourteenth/coin_ied.py`, tested in `test_coin_ied.py`). The **driving** is COIN's first Lua runtime: `game/missiongenerator/coinluadata.py` emits each mobile VBIED's DCS group name + target base as `dcsRetribution.coin.vbieds`, and the new `resources/plugins/coin/` plugin routes it via `mist.goRoute` (`tests/missiongenerator/test_coinluadata.py` + `tests/lua/test_coin_runtime.py`). **Movement only** — kill it en route and it's recorded natively as intercepted; let it reach the turn end and the fuse resolves against the mandate. **Re-fly (Lua, cockpit-only) = watch a VBIED actually drive toward a friendly field, kill one before it arrives (see "intercepted"), and let one run (see the mandate hit); confirm a static IED sits still.**
- **Rework (2026-07-05) — the static IED is a static-object emplacement with guys around it.** User call ("change the IED back to the proposed static object but spawn some guys around it"): the *static* variant is no longer a lone supply truck — `ied_emplacement_unit_types` (`game/fourteenth/coin.py`) builds an emplaced **device** (a vanilla `Fortification.Oil_Barrel` static — faction-independent, never degrades) guarded by **two riflemen** from the faction's own infantry (Toyota Al Gaib → 2× Insurgent AK-74, real-roster verified); the mixed static+infantry group splits correctly at mission generation (statics and vehicles are already generated separately per unit). **Clearing is device-anchored** (`_ied_intact` in `coin_ied.py`): destroy the barrel and the IED is cleared even if the team survives (they melt away); killing the team alone leaves the fuse ticking. The VBIED keeps the lone-truck kit; pre-rework saves' truck emplacements (no static in the group) keep the old any-unit-alive clearing. A rifle-less faction gets the bare device sized to 1 unit (never cycled barrel copies). Covered by `tests/fourteenth/test_coin_units.py` + `test_coin_ied.py`. **Re-fly = confirm the emplacement reads as a small roadside object with dismounts around it (not a parked truck), that killing the barrel clears it, and that strafing only the team does NOT clear it.**
- **What CI cannot exercise:** the real `ForceGroup.generate` spawn of a red emplacement on a ratline waypoint (attached to the forward red stronghold for allegiance), the retyped static actually rendering/dying as a destroyable object in DCS, whether it reads as a recon-fogged Armed-Recon/CAS target, and whether an AI Armed Recon flight auto-services it.
- **Setup:** NEW "Afghanistan - Operation Enduring Resolve (COIN)" (`coin_ied` preseeds on). Watch the info feed for "IED activity reported on the road near {stronghold}"; TARPS that trail segment to ID the emplacement, then frag CAS/Armed Recon on it.
- **Pass:** up to 2 hidden IED emplacements sit on the insurgent supply roads (recon-fogged until TARPS'd); striking one within ~3 turns clears it ("Roadside IED … cleared") with no mandate hit; ignoring one past the fuse detonates ("IED detonation … coalition casualties") and drops the mandate with a labeled "IED detonations xN" will mover; a cleared/detonated IED is replaced on the next turn (staying at the cap), and two IEDs never sit on the same road segment.
- **Fail signature:** IEDs render **blue** (allegiance bug — must attach to the red stronghold); none appear (no red-red `convoy_routes` — the ratline didn't build, or the faction has no FRONT_LINE group); the emplacement is fully visible with no recon fog (TGO fog not applying); a detonation doesn't move the mandate (`blue_ied_detonation` weight 0 / `consume_ied_detonations` not wired); IEDs pile onto one road (the used-road de-dup broke); the count runs away past the cap.

### P5 — COIN high-value targets: hunt the leadership · COIN · ◐ PARTIAL (2026-07-04, user pass — "same as above"; **REWORK APPLIED 2026-07-04** in two parts: fiction-kit retype (a small convoy, not 3 BTR-80s) + an in-mission random patrol you have to run down (see the two rework bullets) — needs a re-fly) (was ☐ UNTESTED, built 2026-07-03; the window state machine / kill-vs-escape / nearest-front pick / cooldown / momentum feed are fully unit-tested with fakes, and the campaign preseed + wiring are verified — the real named-emplacement spawn + recon-fog + the in-ring CDE interaction + played feel need a campaign)
- **Rework (2026-07-04) — fiction-appropriate unit kit.** Same change as P4 (`_retype_units` + `hvt_unit_types` in `game/fourteenth/coin.py`): the HVT group's DCS unit types are re-pointed from the faction's front-line armor to a **command team** — a leader's jeep (`UAZ-469` on Toyota Al Gaib) plus two riflemen (`Insurgent AK-74`), drawn from the faction roster. Verified headless. Covered by `tests/fourteenth/test_coin_units.py`. **Re-fly = confirm the HVT now reads as a small leadership element (a jeep + escort) rather than an APC platoon.**
- **Rework (2026-07-04, part 2) — the HVT convoy moves in-mission.** The HVT is now a small **convoy** (`HVT_UNITS` 3→4: leader jeep + armed technical + 2 rifles) that **patrols a slow random loop around its area** rather than sitting parked, so you have to find and run it down — the old armor-hunt movement fused with the new HVT. COIN's first Lua runtime drives it: `game/missiongenerator/coinluadata.py` emits the live HVT's DCS group name + centre as `dcsRetribution.coin.hvt`, and `resources/plugins/coin/` routes it via `mist.goRoute` (alarm-green) to a fresh `mist.getRandPointInCircle` destination within `hvtPatrolRadiusM` each cadence, after a startup grace (`tests/missiongenerator/test_coinluadata.py` + `tests/lua/test_coin_runtime.py`). **Movement only** — killing the convoy inside the window is still the turn-boundary `hvt_kills` momentum blow (a decapitated convoy just stops being routed); the CDE dilemma (a kill inside a §40 ring also charges the mandate) is unchanged. **Re-fly (Lua, cockpit-only) = confirm the convoy actually drives a wandering patrol in its area, that you can track + kill it on the move, and that it stops moving once dead.**
- **What CI cannot exercise:** the real `ForceGroup.generate` spawn of a named 3-unit HVT group near the forward stronghold, whether it reads as a recon-fogged strike target, and — crucially — the **CDE interaction**: an HVT sitting inside a population ring should make his kill *both* an `hvt_kills` momentum blow *and* a §40 `count_roe_violations` mandate hit (the dilemma is emergent from the existing ROE machinery, not special-cased here).
- **Setup:** NEW "Afghanistan - Operation Enduring Resolve (COIN)" (`coin_hvt` preseeds on). Watch the info feed for "Intel: HVT {name} located near {stronghold} — a window to strike"; TARPS to ID him, then decide whether to take the shot (note if he's inside a town ring).
- **Pass:** one named HVT surfaces near the most-contested stronghold, recon-fogged, live for ~4 turns; killing him inside the window drops the insurgency's **momentum** with a labeled "HVT leaders xN killed" will mover ("HVT … eliminated"); killing him **inside a population ring** *also* drains the **mandate** via the ROE-violation charge (the dilemma); letting the window pass with no kill just closes it ("gone to ground") with no penalty; a new HVT surfaces after the cooldown; only one HVT is ever live at a time.
- **Fail signature:** the HVT renders **blue** (allegiance bug); none appears (no red strongholds, or the faction has no FRONT_LINE group); no recon fog on the emplacement; a kill doesn't move red momentum (`red_hvt_killed` weight 0 / `consume_hvt_kills` not wired); an in-ring kill charges *only* momentum and not the mandate (the ROE zones aren't covering him — a placement/zone-overlap issue, not this feature); two HVTs live at once (the active-guard broke); a missed window drains will (escape must be free).

### P6 — COIN dispersed cells: patrol the countryside · COIN C4 · ☐ UNTESTED (built 2026-07-03; the seed/attrite/coalesce state machine, one-cell-per-stronghold spread, the open-field placement gate, and the coalesce-revives-a-dead-cache hook are fully unit-tested with fakes, and the campaign preseed + wiring are verified — the real field spawn + recon-fog + the played feel need a campaign)
- **Fiction-kit note (2026-07-04):** the field cell now shares the P4/P5 unit retype — `cell_unit_types` re-points it to an **armed technical + infantry** (a DShK gun-truck + Insurgent AK-74 on Toyota Al Gaib) instead of the faction front-line armor. First-fly should confirm the cell reads as an insurgent fire team, not an armor group.
- **What CI cannot exercise:** the real `ForceGroup.generate` spawn of a 2-unit red cell out in the open field (on the stronghold→coalition line, ≥ 12 km from every CP), whether it reads as a recon-fogged Armed-Recon/CAS target you can find by patrolling, and the coalesce's cache-revival actually re-opening C1 regen in the *next* mission.
- **Setup:** NEW "Afghanistan - Operation Enduring Resolve (COIN)" (`coin_dispersed_cells` preseeds on). Watch the info feed for "insurgent activity reported in the countryside near {stronghold}"; **first destroy a stronghold's caches** (to starve its regen), then leave the field cells alone for a few turns and watch whether that stronghold's cache — and its regen — comes back. Contrast with a run where you hunt the field cells down.
- **Pass:** up to 3 recon-fogged cells sit out in the countryside (one per stronghold, not stacked, ≥ ~12 km off every base); killing one is ordinary attrition and denies the resupply; leaving one ~3 turns coalesces it into its home stronghold and brings a **dead ammo cache back online** ("a supply cache is back in operation") — visibly re-opening that stronghold's C1 regeneration next turn; a stronghold with no dead cache instead gets a small garrison reinforce (bounded by its anchor) or the cell just "melts in"; cells reseed to the cap each turn.
- **Fail signature:** cells render **blue** (allegiance bug); cells spawn on top of a base (< 12 km — the open-field gate broke) or all stack at one spot (the one-per-stronghold spread broke); no recon fog; the coalesce doesn't revive the cache (the cache-revival path not firing / anchor read wrong); a coalesce grows a stronghold **past** its turn-0 anchor (the militia-revive cap broke — must never exceed `tgo_cap`); cells never appear (no red↔blue geometry, or the faction has no FRONT_LINE group).

### P7 — Iraq "Operation Inherent Resolve" (Mosul) COIN campaign plays · Iraq COIN campaign · ☐ UNTESTED (built 2026-07-04; the whole laydown is headless-verified — the from-scratch generator loads to 18 CPs with caches/garrisons/the SA-6/8/9/13 crust/the southern front all binding, and the will profile + 3-phase arc parse — CI-locked in `tests/fourteenth/test_inherent_resolve.py`; the played feel needs a flown campaign)
- **What CI cannot exercise:** whether the DCS Iraq map + the generated `iraq_inherent_resolve.miz` actually load and play in-app; whether the two new factions (`CJTF-OIR 2016`, `Islamic State 2016`) cast sensible squadrons; whether the single southern front (Q-West → Hammam al-Alil) grinds; whether the COIN mechanics (VBIEDs, caches, HVTs, the ratline west to Tal Afar) surface as in the Enduring Resolve P-series; and whether the Mosul / Old City positive-control CDE boxes read on the F10/ME map and price into the mandate. Design note `docs/dev/design/414th-inherent-resolve-campaign-notes.md`.
- **Setup:** a **NEW** "Iraq - Operation Inherent Resolve (COIN)" game (all COIN toggles + `vietnam_political_will`/`campaign_phases`/`high_digit_sams` preseed on). Requires the DCS Iraq map. Check the New Game list shows it; open the F10/ME map for the Mosul + Old City restricted boxes; fly a turn off Qayyarah West.
- **Pass:** the campaign appears and starts; **6 airfields total** (not a ton) — RED holds 3 (Mosul + SA-6, Erbil, Kirkuk + SA-6) + **10 FOBs** filling the corridor + belt (Tikrit, Bayji, Shirqat, Qayyarah, Hammam al-Alil, Bartella, Tal Afar, Hawija, Makhmur, Gwer — no 100 km empty gaps between towns), **each furnished** (2 garrisons of technicals/gun-trucks + AAA + SHORAD + a strongpoint + caches, not a lone marker); the ME-authored towns sit on the real terrain (the base miz) and the generator-added in-between towns are roughly placed (nudge in the ME if needed); BLUE bases from the south only — **Balad the forward player field (Q-West is gone)**, Al-Taquddum strike, Baghdad support; **one front** sits partway up the Balad → Tikrit (Highway 1) axis and moves under pressure; the COIN feed (caches / IEDs / VBIEDs / emirs / dispersed cells) fires as on Enduring Resolve; SEAD has a job (SA-6 at Mosul + Kirkuk) while SA-8/9/13 + ZU-23 punish the deck; a fixed strike inside the Mosul box costs mandate.
- **Fail signature:** campaign hidden from New Game (version gate) or errors on load; a FOB/airfield in water or off-map; a squadron fragged from a dropped/red field (Qayyarah id 6, Erbil id 4); the front never forms (Balad↔Tikrit route missing) or captures a base by sweep; the crust never fills (faction SAM presets dropped) so SEAD has nothing; red strongholds still read barebones (furnishing not applied); the will meters/phases don't move; the ISIS spawns read as US armor (fiction-kit retype not applied).

---

## Q. Planner / payload UI

### Q1 — Per-aircraft flight defaults save + apply · §43 · ☐ UNTESTED (built 2026-07-02; store/apply fully unit-tested, the button + the "new flight opens pre-configured" behaviour is Qt UI)
- **Headless adjudication:** the store round-trips (save → reload from disk), `apply_flight_defaults` seeds
  fuel + `member.properties` for a BLUE fresh flight, skips RED, no-ops with no saved entry, clamps fuel to
  the airframe tank, and stays silent when persistency isn't set up — all in
  `tests/fourteenth/test_flight_defaults.py`. What CI can't exercise is the Qt button and the "the box opens
  already set the way I want" experience.
- **Setup:** any campaign; open a flight's **Edit flight → Payload** tab. Change Internal Fuel (e.g. to 80%),
  Aircraft Condition, Wear & Tear, and/or Spawn Type; click **Save as default**. Then create a *new* package
  with a flight of the **same airframe** and open its Payload tab.
- **Pass:** the new flight's Payload tab already shows the saved fuel + property values (no re-entry); **Clear
  default** is enabled once a default exists and, after clicking it, a further new flight of that airframe is
  back to stock values; the store lives at `Saved Games\Retribution\flight_defaults.json` and survives an app
  restart / a New Game; a *different* airframe is unaffected; enemy (RED) flights are never altered.
- **Fail signature:** new flights still open at stock fuel/condition (apply not firing — confirm the flight is
  BLUE and freshly created, not a clone; check `flight_defaults.json` wrote); a saved sub-full fuel default
  never appears (fuel stored in kg — a unit mixup would show a clamped-to-max value); a crash on flight
  creation (the apply path must be a silent no-op on any error — it is wrapped, so a stack trace means the
  guard was bypassed); RED flights changing (the `coalition.player.is_blue` gate failed).

## R. Mission map / F10 drawings

### R1 — Support-package F10 orbit markers render + labelled · §45 · ☑ VERIFIED (2026-07-04, user pass — "looks great" on COIN; NOT COIN-only — `generate_support_orbits` is called unconditionally in `DrawingsGenerator.generate`, gated only on blue REFUELING/AEWC flights existing, so every campaign with a blue tanker/AWACS gets the markers) (was ☐ UNTESTED, built 2026-07-03; the emitter — racetrack-end pick, blue/support filter, group-name label match, oblong/circle draw — is locked in `tests/missiongenerator/test_support_orbit_drawings.py` and a real `.miz` `drawings.dict()` serialize probe passed; the on-map render needs an in-cockpit eyeball)
- **Headless adjudication:** `generate_support_orbits` draws a labelled racetrack for a blue `REFUELING`/`AEWC`
  flight, skips non-support + RED + `mission_data=None`, and the label carries callsign/type/freq/TACAN (AWACS
  without TACAN drops it) — all in `tests/missiongenerator/test_support_orbit_drawings.py`. A probe confirmed
  the `add_oblong` capsule + `add_text_box` serialize into the `.miz` drawings table. What CI *cannot*
  adjudicate: whether DCS renders the racetrack + label on the F10 map and whether it sits over the actual
  tanker/AWACS orbit.
- **Setup:** any campaign with a blue tanker and/or AWACS package; generate the mission, then open the `.miz`
  in the ME (or fly it and open the F10 map).
- **Pass:** each blue tanker/AWACS shows a cyan dashed **racetrack** at its orbit with a **label** reading
  `<callsign>  <type>` over `<freq>  TCN <tacan>` (AWACS shows no TCN); the racetrack sits where the flight
  actually orbits; no marker for enemy or non-support flights.
- **Fail signature:** no markers at all (the flight-plan has no `PATROL_TRACK`/`PATROL` pair, or `mission_data`
  wasn't threaded into `DrawingsGenerator` — check `missiongenerator.py`); a marker in the wrong place (the
  racetrack-end waypoint pick); a blank/partial label (the `group_name` match to `TankerInfo`/`AwacsInfo`
  failed — freq/TACAN come from there, not `FlightData`); a red tanker marked (the `friendly.is_blue` gate).
  Knobs: `SUPPORT_ORBIT_LINE`/`SUPPORT_ORBIT_RADIUS_M`/`SUPPORT_LABEL_*` (drawingsgenerator.py).

### S1 — Route-aware fuel-tank top-up adds a bag on a far-AO route · §46 · ☑ VERIFIED (2026-07-04, user pass — "S1 good I think", tentative) (was ☐ UNTESTED, built 2026-07-03; the add-logic + the safety contract "never removes/replaces a store" are locked against the real F/A-18C pylon tables in `tests/fourteenth/test_range_fuel.py`, and a before/after on the reset Hornet Strike/BAI + F-16 loadouts confirmed empties-only; the in-mission fuel/endurance feel needs a flight)
- **Headless adjudication:** `top_up_for_route` fills an empty tank station on a far route, is a no-op on a
  short route / empty / custom loadout / setting-off, and **never removes or replaces an existing store**
  (asserted on the Hornet pylon tables). A before/after script showed the COIN Hornet Strike going 2→3 tanks on
  the empty centerline with zero swaps, the Hornet BAI staying 1 tank (no empty station, Mavericks untouched),
  and the short route unchanged. What CI *cannot* adjudicate: whether the added fuel actually gets the AI jet to
  the target and home in-sim, and whether the trigger threshold feels right across campaigns.
- **Setup:** the COIN **Enduring Resolve** campaign (carrier ~800 km off the AO), or any campaign with a
  long-range strike/CAS package; generate the mission and open a Hornet strike flight's loadout in the ME (or
  fly it) — with `auto_range_fuel_tanks` ON (default).
- **Pass:** the Hornet Strike flies with **3 tanks** (the centerline bag added); the TGP, AMRAAM, AIM-9, and
  JDAMs are all still present; a short-range campaign's Hornet is unchanged (2 tanks); a loadout you edited by
  hand is untouched.
- **Fail signature:** a store missing from a jet that should be intact (the fill touched an occupied station —
  a bug, since it should only fill empties); tanks added on a short route (the required-fuel estimate is too
  hungry — `_required_fuel_lbs`); no tank added on the COIN carrier route (the route length or fuel estimate
  under-counts, or the airframe has no empty tank-capable station — expected for the F-16/Hornet-BAI). Knob:
  `auto_range_fuel_tanks` (Mission Generation → Loadouts).

## T. Campaign flow

### T1 — Continuous clock marches + weather evolves across turns · §47 · ☐ UNTESTED (built 2026-07-04; the march-forward-within-3–7 h band, time-of-day-derived-from-clock, midnight date-roll, and previous-turn weather bias are locked in `tests/weather/test_continuous_campaign_clock.py`; the multi-turn *feel* needs a play session)
- **Headless adjudication:** `Conditions.advance` steps `start_time` forward 3–7 whole hours each turn, derives
  time-of-day from the marched clock, and rolls the date at midnight; `generate_weather(previous=...)` biases
  the seasonal draw toward the previous rung on the Clear→Cloudy→Rain→Storm ladder while still honouring a
  zero seasonal chance — all in `tests/weather/test_continuous_campaign_clock.py`. What CI *cannot* adjudicate:
  whether several turns in a row *read* as one continuous timeline (believable clock progression, weather that
  builds and clears rather than flickers) and whether the 3–7 h pacing feels right.
- **Setup:** any day-and-night campaign with `continuous_campaign_clock` ON (default). Note the mission
  start date/time on turn 1, then pass ~5–6 turns without flying, checking the mission clock + weather each turn.
- **Pass:** the clock advances a few hours each turn and never jumps backward; the date increments only when the
  clock crosses midnight (not every 4 turns); time-of-day (dawn/day/dusk/night) follows the actual clock;
  weather trends between adjacent states over turns (e.g. clear → cloudy → rain → clearing) rather than
  teleporting clear↔storm. With the setting OFF, the stock behaviour returns (slot rotation + random weather).
- **Fail signature:** the clock jumps by a random large amount or goes backward (the advance interval / the
  `continuous_clock_active` gate — check `night_day_missions` isn't forcing day/night-only, which falls back by
  design); the date ticks every 4 turns regardless of the clock (`current_day` not reading `conditions`);
  weather still flickers with no correlation (the `previous=` bias not being passed from `Conditions.advance`).
  Knobs: `MIN/MAX_TURN_ADVANCE_HOURS`, `_WEATHER_PERSISTENCE_KERNEL` (`game/weather/conditions.py`).

## U. Upstream-sync runtime adoptions

### U1 — Water/land relocate scripts run on the MIST shim · base plugin · ☐ UNTESTED (adopted from upstream 2026-07-05 with the upstream/dev merge; upstream #767/#838 run on full MIST — the fork's shim needed a new `mist.getGroupData` (43rd symbol), contract pinned in `tests/lua/test_mist_shim_getgroupdata.py`)
- **Headless adjudication:** both scripts parse on Lua 5.1, register after `mist_moose_shim.lua` in the base
  plugin work orders (`tests/missiongenerator/test_*_relocate_plugin.py`), and the shim's `getGroupData`
  returns a dynAdd-shaped mission-table entry (units x/y/name, route, country, category) with fresh copies
  and nil for unknown groups (`tests/lua/test_mist_shim_getgroupdata.py`). What CI *cannot* adjudicate:
  whether `mist.dynAdd`'s `coalition.addGroup` same-name re-add actually swaps the beached group in live DCS
  without firing loss events, and whether the relocated positions are sane (ships in open water, ground
  units on land).
- **Setup:** any campaign whose generation beaches a naval escort or drops a ground unit in water (island
  maps are the natural stress; a carrier parked near shore beaches escorts).
- **Pass:** within the first minute, `dcs.log` shows `land_relocate:` / `water_relocate:` info lines for the
  moved groups and no script errors; the moved ships sit in open water under their original names; the
  campaign's kill/loss tracking still works for a relocated unit (kill one, it shows in the debrief).
- **Fail signature:** `attempt to call field 'getGroupData'` (shim symbol regression) or an error inside
  `run()` in either script; a relocated group vanishing or duplicating (the same-name addGroup swap not
  behaving); a relocated unit's kill missing from the debrief (name not preserved). Knobs: constants at the
  top of `resources/plugins/base/land_relocate.lua` / `water_relocate.lua`.

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

**Status (user, 2026-07-01): the core UI worked in a prior pass** — "drop spawn was good [in a prior]
form." Takes **20-A** (right-click blank map → Qt dialog) and **20-B** (confirm → marker appears
immediately) as user-confirmed. The remaining rows (20-H off-default guard, 20-C remove, 20-D deploy-next-turn,
20-E terrain, 20-F range, 20-G free-placement) are **not individually confirmed** — check them the next time
the placement dialog is open.

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
