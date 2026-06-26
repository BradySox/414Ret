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

## Status legend

| Mark | Meaning |
|---|---|
| ☐ UNTESTED | Built; no in-game observation yet |
| ◐ PARTIAL | Flown, but not under the conditions that stress the fix |
| ☑ VERIFIED | Watched for the fail signature in-game; did not occur (note date/Tacview) |
| ✗ REGRESSED | Fail signature reproduced in-game — reopen the fix |

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

### C3 — Tanker racetrack speed estimate · ☐ UNTESTED
- **Setup:** Plan a package that takes fuel from a **buddy tanker** — the airframes
  that ship *without* a `patrol:` speed/altitude block (the F/A-18E/F tankers; the
  A-6E buddy tank before it got its own `patrol:` block). The dedicated tankers
  (KC-135/KC-130/MPRS/S-3B Tanker, and now the A-6E Tanker) define their own patrol
  speed and are unaffected. For the buddy tankers the new
  `preferred_patrol_speed(preferred_patrol_altitude)` estimate now drives the orbit.
- **Pass:** Tanker flies its racetrack at a sane, steady speed and receivers
  rendezvous and take fuel without falling behind or overrunning.
- **Fail signature:** Tanker orbit speed too slow/fast for receivers to join (e.g.
  fighters S-turning to stay behind, or unable to close). If seen, revisit
  `RefuelingFlightPlan.patrol_speed` in `game/ato/flightplans/refuelingflightplan.py`.

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

### C5 — Boom/probe refuel-method compatibility · ☐ UNTESTED
- **Setup note (2026-06-25):** still untested — the faction flown in the 2026-06-25 session
  did **not** carry both a boom and a drogue tanker, so there was no method split to observe.
  Requires a faction with **both** a boom (KC-135) and a drogue (KC-135 MPRS / KC-130 / S-3B
  Tanker) tanker to exercise this row.
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

### F3 — Player-flown SOF insert + C-130 EW exclusion · #56 / §15 · ☑ VERIFIED (2026-06-23)
- **Verified (2026-06-23):** flown — "the EW is gone": the `c130j` EW menu/behavior
  is correctly absent on the SOF insert C-130J-30 (the de-conflict gate fires).
- **Pass:** The player can fly the air-assault-shaped delivery; the `c130j` EW
  plugin is skipped for that mission (logged).
- **Fail signature (watched, did not occur):** EW menu appears on the SOF insert;
  or the insert can't be planned/flown by the fixed-wing transport.

### F4 — Results bridge round-trip · §15 · ☑ VERIFIED (2026-06-17/18)
- Verified in-game: `SCAR area scar-N: launched/failed` round-tripped through
  the TARS channel into the debrief. No action; listed for completeness.

### F5 — Mis-ID budget penalty (R7) · §15 · ☐ UNTESTED
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

### F7 — SCAR loiter/static hold (no chase, fail = window) · §15 / PR #187 · ☐ UNTESTED
- **Setup:** Plan a SCAR flight against a real enemy armor TGO. Fly to the kill box.
- **Pass:** The bound armor (and any spawned decoys/clutter) **holds in place** — nothing drives off
  toward a city; a bound missile site stays inert (no relocation, no launch). Killing the armor
  attrits it natively at debrief (shows in losses) with no SCAR-specific scoring. If you never kill
  it, the area resolves **failed on the window timeout only** — never an instant fail on arrival.
- **Fail signature:** anything drives/flees; a SCUD relocates or launches; an instant "failed" the
  moment the area goes live (the arrival-fail gate leaked); a `scar_414_init.lua` Lua error.

### F8 — SCAR inverted SOF capture (dwell on the live commander) · §15 / PR #187 · ☐ UNTESTED
- **Setup:** `scar_command_post_intel` ON, a SOF team in stock, a SOF insert fragged onto the SCAR
  package. Deliver the team near the held target; leave the command vehicle ALIVE.
- **Pass:** With the SOF team holding on the **live** command vehicle for ~`SCAR_SOF_DWELL_S` (30s),
  the area resolves **captured** (commander reveal + SOF refund next turn). Killing the command
  vehicle instead forfeits the capture (it's just a kill); leaving the commander resets the dwell.
- **Fail signature:** instant capture on co-location (dwell not enforced); capture fires with the
  commander already dead; or no capture path at all when a live team holds on a live commander.
  Known v1 nuance to watch: the scripted-fallback team spawns at the held commander, so a capture
  can auto-complete without a real player delivery (Phase-2c tuning).

### F9 — SCAR King talk-on gate (Phase 2 + 3) · §15 / PR #189 · ☐ UNTESTED
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

### F10 — SCAR King laser/IR designation (Phase 3b) · §15 / PR #189 · ☐ UNTESTED
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

### F11 — SCAR designation polish: night illum + "say again" F10 (Phase 4) · §15 / PR #189 · ☐ UNTESTED
- **Setup:** Fly a SCAR at **night** to the box; also try the F10 entry by day.
- **Pass:** At night each smoke cue (GREEN box / RED target) is accompanied by an **illumination
  flare** over the cue point (smoke alone is invisible after dark). F10 shows **one** entry — "MAGIC:
  say again SCAR target" — that re-pops the current cue (and re-calls the laser code) for your active
  target; with no active target it says so. By day, no illum (smoke only).
- **Fail signature:** no flare at night / flare in daylight (bad `is_night`); the F10 missing or
  duplicated; "say again" cues the wrong stage or a resolved area; or a Lua error.

---

## G. Plugin runtime (Lua, not CI-runnable)

### G1 — Flight Control: AI flow unaffected + no spot spam · §13 · ☑ VERIFIED (2026-06-24)
- **Setup:** Default ON; a base where Retribution parks STATIC objects on ramp
  spots (e.g. Kutaisi/Kutaisi-like).
- **Pass:** AI QRA/CAP **launch normally** from FLIGHTCONTROL bases (players-only
  is pragmatic, not a hard gate); no "Number of parking spots does not match!"
  spam (orphan spots marked `RetributionStatic`).
- **Fail signature:** AI scrambles queued/strangled, or the parking-mismatch
  warning every cycle (138× in one playtest before the orphan-reconcile fix).

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

### G8 — Combat SAR pilot rescue (`combatsar` / MOOSE CSAR) · Combat SAR Phase 2 · ☐ UNTESTED
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

### G9 — Combat SAR AI standing alert (`auto_combat_sar`) · Combat SAR Phase 3 · ☐ UNTESTED
- **Orbit-placement fix 2026-06-25 (found in-game, fixed — re-observe):** the standing-alert orbit
  used to **mirror the AWACS** (it reused the AEW&C builder → 80 NM standoff + 60 NM racetrack), so a
  CH-47 could never reach an ejection. Combat SAR now flies a **dedicated forward hold**
  (`game/ato/flightplans/combatsar.py`): front-anchored, **15 NM** threat buffer, **5 NM** racetrack
  half-length. Re-observe that the planned CSAR orbit now sits **near the FLOT**, not back at AWACS depth.
- **Setup:** Enable **Automatic Combat SAR** (HQ automation settings; default OFF). Campaign with a
  blue **CH-47** squadron + budget. Auto-plan turn 1 (observe-only, don't fly the CSAR).
- **Pass:** A blue **AI** `Combat SAR` package appears in the ATO, **holding a tight racetrack near an
  active front** (one per front, capped by available CH-47s) — clearly forward of the AWACS/tanker
  orbits, clear of enemy threat rings. The generator logs `enableForAI=true`. When a pilot ejects in
  range, the orbiting AI CH-47 diverts, recovers, and returns — with no player CSAR up.
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

### G10 — Combat SAR King TACAN beacon + LARS · Combat SAR Phase 4 · ◐ PARTIAL (player King = no scripted TACAN by design; AI King untested)
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

### G11 — Combat SAR rescue scoring (pilot spared at debrief) · Combat SAR Phase 4 · ☐ UNTESTED
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

### G12 — Combat SAR extracts a stranded SOF team · Combat SAR + SCAR · ☐ UNTESTED
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

### G13 — Combat SAR airframes: armed Chinook + flyable King · Combat SAR · ◐ PARTIAL
- **In-game 2026-06-25:** tasking offered on **both** airframes ✅; CH-47Fbl1 spawns with its
  **door M60D guns** ✅ ("loadout good"). **Found:** the C-130J-30 King spawned with **no loadout /
  no wing tanks** — the documented removable-pylon case. **Fixed 2026-06-25:** added a
  `Retribution Combat SAR` payload for the C-130J-30
  (`resources/customized_payloads/C-130J-30.lua`) mounting the two external wing tanks
  (`{C130J_Ext_Tank_L}` Pylon 1 + `{C130J_Ext_Tank_R}` Pylon 2; CLSIDs validated against the module).
  **Re-observe:** the King now spawns with visible underwing tanks. **Still to verify:** the King
  flies **clean of the EW/ISR menu** (the other half of this row — `_non_ew_c130j_present` suppression).
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
  payload); the King wears the EW/ISR menu (the `_non_ew_c130j_present` suppression didn't fire); an
  old save with a "C-130" squadron fails to load (the `C-130 → C-130J-30` migrator alias is missing).

### G14 — C-130J jamming vs MANTIS IADS (no EMCON interference) · §2 / MANTIS migration · ☐ UNTESTED
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

### H3 — SCAR task kneeboard (Phase 4) · §15 / PR #189 · ☐ UNTESTED
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

### H4 — Custom kneeboard import (UI) · §4 · ☐ UNTESTED
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

---

## I. Mission generation

### I1 — Per-squadron DCS country / nation voiceovers · §23 · ☐ UNTESTED
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
- A2 (QRA base-defense doctrine), B2 (DEAD reachability gate), B3 (threat-weighted
  BARCAP orbit), B4 (TARCAP/escort reach), C1 + C2 (AWACS/tanker front-anchor +
  depth), F6 (SCAR auto-plan appears in ATO).
- Setup needs: active land front, enemy airbase ≈90 NM from FLOT, an armor
  concentration near the front, AWACS+tanker support, `scar_autoplan` ON.

### Session 2 — Fly a strike package off that campaign
- A1 (QRA scramble profile — trigger a raid, include a high-elev alert base),
  C3 (tanker speed), C5 (boom/probe match), C6 (fuel-driven pre/post-vul tanking),
  C4 (A-6E attack/tanker split — buy both), H1 (kneeboard overflow on a busy
  theater), D1 (player-despawn loss — land/despawn then end).

### Session 3 — SCAR commander-capture campaign
- F2 (capture → permanent reveal carryover across turns), F5 (mis-ID penalty —
  kill a decoy), E (SOF C-130 insert ground-starts + EW skipped), G2 (TARS BDA
  bridge via an F-14 TARPS pass).

### Session 4 — Plugin-runtime sweep, fly over an active front
- G3 (TIC ambient fire / LOS-blocked positions), G1 (Flight Control: AI launches
  normally, no parking-spot spam), G4 (C-130J EW/ISR — fly the JAMMING slot).

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
(merged), #138 (open, finalize button). **Remaining gap = Increment C support buildings**
(finalized save has 0 ground objects → no economy / +0.0M income). BC-D fly-half + BC-E
need DCS; BC-F still pending.

| # | Layer | Observable criterion | Fail signature | Status |
|---|---|---|---|---|
| BC-A | Retribution | "Build your own (blank canvas)" → map opens with **every** airfield **gray/yellow** (neutral), no fronts, no units | Crash on generate; bases pre-coloured; preset units present | **VERIFIED** (after #133) |
| BC-B | Retribution | **Left-click** cycles gray→blue→red→gray (live SSE); **right-click** reverses | Opens info dialog; no recolor; 403 | **VERIFIED** (needed client rebuild) |
| BC-C | Retribution | **Finalize Campaign** prunes unpainted gray bases, draws a front between blue/red | Gray bases remain; no front; crash in finalize | **VERIFIED** (0 neutral, 5 fronts) |
| BC-D | build=Retribution / fly=.miz | Finalize → air-wing dialog → add squadrons from scratch → plan + fly a package | Dialog empty/errors with 0 preconfigured; no flyable aircraft | build VERIFIED (1 sq/side); **fly pending** |
| BC-E | .miz | Drop-spawn (§20) places SAMs/armor onto the finalized map | Placement broken on a hand-built theater | pending |
| BC-F | Retribution | Paint inert in a **normal** (non-setup) campaign — click opens info dialog | Bases repaint in a real game (guard not firing) | pending |
