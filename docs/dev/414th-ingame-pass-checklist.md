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

### A5 — QRA forward defense (rear bases answer the front) · §1 · ◐ PARTIAL (2026-07-11 flown Red Tide M1 `csar-snatch-toggle-question-dfdb7a`, Tacview `Tacview-20260711-171935`: armed cleanly, closest-first launch order held, one rear Su-27 transited front-ward, zero fail signatures — but the marquee full-length 147 NM rear→front transit wasn't demonstrated end-to-end)
The emitter geometry, the reach/disengage arithmetic, the ambush-wins rule and the narrow player cue
are unit-tested (`tests/missiongenerator/test_qra_defense_zones.py`,
`tests/missiongenerator/test_interceptluadata.py`, `tests/test_vietnam_doctrine.py`), and the plugin
parses on Lua 5.1. What no test can cover: whether Moose's accept-zone filter actually *releases* an
already-engaged defender when its target leaves the zone, and whether a 150 NM transit really flies.
- **2026-07-17 night fly (Scenic Route Merged, session `tacview-test-analysis-5bb161`),
  consistent-with:** Bandar Abbas QRA F-5Es launched against the QUAIL Armed Recon raid working
  Bandar-e-Jask (~118 NM from BA) — the rear-base-answers-a-forward-CP shape under the opened
  reach + accept zones (see the A7 bullet for the same event). The transit never completed (all
  4 F-5s died to Phoenix en route), so the full-length demonstration is still owed.
- **2026-07-11 flown evidence (Red Tide M1 "with Mags happy", ~125-min MP, 12 player flights):** load
  line present — `Intercept: RED defends 9 zone(s); scramble radius 200 NM` (9 = red's non-neutral CP
  count on this save). **Closest-first held:** the front base answered first — Haina's own QRA (4×
  MiG-23MLD, t≈1240–1360) flew 43–66 km W/SW into the blue push and all four died fighting over the
  front. **Rear launch observed:** Sperenberg (147 NM back, ~30 km S of Berlin) scrambled 3 Su-27s at
  t≈5110–5200; #003 transited **52 NM out on bearing 246°** — near-exactly the bearing to the Fulda
  front (237°) — and was killed en route ~45 NM from base; #001/#002 stayed local (~8 NM, base
  defense). Fail signatures (a)–(e): **none occurred** — no turn-around-at-~162-NM, no chase deep
  into blue, not every base launched at once, no `SetBorderZone`/`ZONE_RADIUS` Lua error. **Still
  owed for VERIFIED:** an observed full-length rear→front transit (the one front-ward Su-27 died a
  third of the way there), the accept-zone *release* of an engaged defender, and the Vietnam
  ambush-leash regression check below.
- **Setup:** Red Tide, `qra_forward_defense` ON (default), red QRA reserve ≥ 2/squadron. Fly a blue
  package to the Fulda/Haina front. Confirm at load: `dcs.log` has
  `DCSRetribution|Intercept: RED defends N zone(s); scramble radius 200 NM` (N = red's non-neutral
  CP count; 9 on the flown M1 save).
- **Pass:** red interceptors launch from **rear** fields (Sperenberg / Schonefeld / Wittstock /
  Hamburg / Templin — 127–168 NM back) and transit to fight over Haina, *after* Haina's own MiG-23s
  answer first. Peenemunde (226 NM) and Kastrup (290 NM) never launch for this raid. Then egress
  west: red **breaks off** rather than following you to Frankfurt/Hahn/Ramstein (outside red's zones).
  Fulda (42 NM from Haina) is inside red's airspace, so a fight there is expected and correct.
- **Fail signature:** *(a)* rear fields launch and then turn around ~162 NM out ⇒
  `SetDisengageRadius` not applied (check `disengageRadiusNm` on the Intercept records); *(b)* red
  chases deep into blue ⇒ `SetBorderZone` never called (no "defends N zone(s)" log line) or the
  Vec2 axes are swapped in `defense_zones_for`; *(c)* red QRA never launches at all ⇒ zones too
  small / wrong coalition bucket, i.e. the accept-zone filter is eating its own airspace; *(d)*
  every base launches at once ⇒ Moose is not picking the closest squadron (would contradict the
  read of its GCI loop); *(e)* a `ZONE_RADIUS`/`SetBorderZone` Lua error in `dcs.log`.
- **Vietnam regression check:** on 1968 Yankee Station, red MiGs must still scramble **late** (40 NM)
  and break off at 50 NM from home — the ambush leash must not have been widened.
- **2026-07-16 detection-escape addendum (fold into this fly):** the PR #782 drift port escaped the
  Lua-pattern magic chars in the EWR detection prefixes (`intercept-config.lua`
  `lua_pattern_escape`) — before it, every parenthesized IADS group name ("0041 | LION (EWR)")
  failed Moose's `FilterPrefixes` pattern match, so QRA detection rode the paren-free
  `QRA_Backstop_*` base EWRs ONLY. All prior A1–A5 evidence was flown on backstop-only detection.
  When flying A5, also confirm the wide-area net: kill a base's backstop-adjacent raid picture by
  approaching from a direction only a *forward EWR site* covers and confirm the rear fields still
  see it (scramble fires before the raid is within backstop range of any alert base). Fail
  signature: detection behaves exactly base-local (scrambles only once a raid is nearly on top of
  an alert field) despite an alive forward EWR network, or `dcs.log` shows an empty detection set
  for a coalition with live `(EWR)` groups.

### A6 — Escort pre-join ROE: ReturnFire at spawn, OpenFire at JOIN · §8 · ☐ UNTESTED (built 2026-07-12 from the flown Red Tide M1 finding — the user-observed "locked until the package forms at join" behavior, code-confirmed: escorts spawned OptROE=OpenFire(2) = "engage ONLY designated targets" with their one designating task attaching at JOIN, so the whole hold/transit window had an EMPTY legal-target set — mechanically unable to return fire (TOAD Escort's MiG-29s died at t=2056/2078 with JOIN ETA 2055, merged at gun range, silent; SCARAB Escort fired post-join only). The spawn ROE for both escort types, the JOIN OptROE(OpenFire) escalation, and the non-escort no-op are unit-tested in `tests/missiongenerator/test_escort_prejoin_roe.py` — whether the DCS AI actually returns fire pre-join and escorts identically post-join is DCS-only)
- **What CI cannot exercise:** whether a pre-join escort under attack now actually returns fire (vs the old evade-only death), whether ReturnFire keeps it on its hold/join timeline (never freelancing at detected contacts), and whether post-join escort behavior is genuinely unchanged (engages fighters threatening the escorted flight at the doctrine range).
- **Setup:** any campaign with escorted packages on both sides (Red Tide M1 regenerated works). Watch (or Tacview) an enemy escort flight that gets engaged during its hold/transit-to-join phase, and another after join.
- **Pass:** an escort attacked pre-join defends itself with weapons (returns fire at its attacker) instead of evading silently to death; it does NOT chase targets that haven't engaged it; after JOIN it escorts exactly as before (commits on fighters near the escorted flight); the miz shows ReturnFire at waypoint 0 and an OpenFire option at JOIN for ESCORT/SEAD_ESCORT.
- **Fail signature:** a pre-join escort still dying without firing under direct gun/missile attack (ReturnFire not honored — would point back at the DCS-side employment issue, see the repro miz); an escort abandoning its hold to chase a detected contact pre-join (ReturnFire semantics drifted); post-join escorts NOT engaging (the JOIN OptROE order vs the ControlledTask broke); the same silent-death on an On-station BARCAP is NOT this row — that's the DCS R-27 employment issue (repro miz in `missions/red-tide/`).

### A7 — QRA react-task filter (AI QRA ignores sweeps/BARCAP/DEAD/Air Assault) · §1 · ◐ PARTIAL (2026-07-17 night fly: behavior consistent with the filter — red QRA sat through 20+ min of blue fighter presence and scrambled only once A/G packages pushed; not conclusive on intent)
- **2026-07-17 night fly (Scenic Route Merged turn 1, Tacview `Tacview-20260717-214932`, session
  `tacview-test-analysis-5bb161`), consistent-with evidence:** blue F-14B BARCAPs held near the
  strait from ~t=600 with **no red scramble**; the Bandar Abbas QRA F-5Es ("Intercept|Bandar Abbas
  Intl|…") launched only ~t=1450+, when the QUAIL Armed Recon/SEAD packages were working the
  Jask-area targets (Armed Recon IS in the react list; DEAD flights were also up but excluded
  types can't disprove — an included type was present). Also consistent with **A5**: Bandar Abbas
  answering a raid at Bandar-e-Jask (~118 NM away) is the rear-base-answers-forward shape under
  the opened reach + accept zones. The scrambled F-5s died 4-for-4 to a Khasab-BARCAP F-14B's
  AIM-54Cs before reaching the raid. Still owed for a clean pass: a *pure* fighter push pressed
  close against an alert base with zero A/G packages in the zone.
- **What CI cannot exercise:** whether the wrapped evaluators are actually what Moose's GCI loop
  calls at runtime (a Moose refactor renaming them would silently restore scramble-at-everything),
  and that a cluster's Set membership at evaluation time reflects the raid composition.
- **Setup:** any campaign with QRA reserves on both sides (Red Tide works). Fly (or watch) a pure
  blue fighter sweep/BARCAP push toward a red alert base, then a strike package on the same axis.
- **Pass:** the AI QRA sits through the pure fighter sweep (no scramble however close it presses),
  scrambles when the strike/BAI/OCA package closes, and still scrambles against an ESCORTED strike
  (any react-type member triggers the cluster). The player-manned scramble cue (A4) still fires for
  the sweep — it is deliberately task-blind.
- **Fail signature:** red QRA launching against a pure fighter sweep (the filter never engaged —
  check the group-name parse against the namegen convention and that the Evaluate wrap survived a
  Moose update); or QRA never launching against a clean strike package (over-filtering: the task
  suffix match broke, e.g. a namegen format change).

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

### B6 — Command-center decapitation degrades enemy planning · §52 · ☐ UNTESTED (built 2026-07-06, **A2 package throttle added 2026-07-17**; the health fraction, the linear unpredictability bonus, the off/intact/C2-less no-ops, the shuffler coupling, the SITREP line, and the A2 cap math + HTN-root gating are unit-tested in `tests/fourteenth/test_c2_decapitation.py` + `tests/test_planner_unpredictability.py` + `tests/test_sitrep.py` — whether red's *played* target selection visibly loosens and its offensive tempo visibly thins after its HQs are bombed needs a multi-turn campaign)
- **What CI cannot exercise:** whether a red side that has lost its command centers actually plans a visibly different/less-repetitive set of opportunistic offensive targets turn-over-turn (the shuffle is proven; the *felt* effect on a real ATO is not), whether its offensive package count visibly thins after heavy decapitation (the A2 throttle: red's ATO should carry fewer strike/BAI/OCA packages but keep planning BARCAP/defense and never drop to zero offense), and whether the SITREP band reads the enemy C2 status correctly across turns.
- **Setup:** **Germany — Red Tide** is now the reference case — its advanced_iads laydown fields a 9-node red command-center network and **preseeds `c2_decapitation_effects: true`** (2026-07-07), so a NEW Red Tide game exercises this directly. Play a few turns noting red's offensive targets, then bomb red's command center(s) and play a few more.
- **Pass:** with red's HQs intact, red's offensive target selection is its usual (near-)deterministic set; after the command centers are destroyed, red's opportunistic offensive targets visibly loosen (it services lower-priority strikes/OCA/BAI it wouldn't have before), while its **reactive defense is unchanged** (BARCAP/DEAD-response still deterministic); the next kneeboard SITREP shows "Enemy C2 degraded (claimed): N/M command posts operational". Turning the setting off restores the stock deterministic planner exactly.
- **Fail signature:** red plans identically before and after the HQ kill (the bonus isn't reaching the shuffler — check `_unpredictability_for` and that the campaign actually has `commandcenter` TGOs); red's *defensive* tasking changes too (the §17 boundary broke — only opportunistic tiers pass through `shuffled_by_priority`); the SITREP line never appears or shows wrong counts (`c2_status_line` / `red_c2_status` wiring); any change at all with the setting off (the gate broke).

### B7 — Red Intent: adaptive enemy posture · §55 · ☐ UNTESTED (built 2026-07-08; **made smarter 2026-07-10** — rolling trend memory + battle-reading + graduated intensity; the posture classifier, asymmetric hysteresis, all four seam helpers, the byte-identical no-ops when off/blue/stock, the offensive-order reorder, the stacked unpredictability + §52 C2 clamp, the aggressiveness bias, the stance-factor + `red_tempo` yield, **plus the new trend classifier, the blue-air-collapse opportunity window, the `_trend_lookback` selector, idempotent history recording, the intensity endpoints, and the intensity-graduated aggressiveness/commit seams** are unit-tested in `tests/fourteenth/test_red_intent.py` + `tests/test_planner_unpredictability.py`; whether red's *played* behaviour visibly changes with posture + trend across a multi-turn campaign needs a fly)
- **What CI cannot exercise:** whether a RED side actually plays *differently* as its posture shifts — surging (pressing captures/CAS, committing ground reserves at a lower advantage, focused targeting) when it holds the advantage vs consolidating (defending, husbanding, slightly erratic targeting) when it's been hit — and, new for the 2026-07-10 pass, whether red reads the **trend across turns**: digging in (CONSOLIDATE) while still ground-dominant once you've **bombed its SAM belt over a couple of turns** ("IADS falling"), its resolve collapses, or it's bleeding bases; and **surging at a lower ground bar** when your air-superiority force is spent ("enemy air spent"). Whether the graduated intensity is visible (a runaway-ahead red strips more bases / commits sooner than a marginally-ahead one; a collapsing red husbands harder). **Per-front (D):** on a **multi-front** map, whether red commits reserves on the front it is winning while it husbands on the front it is losing (the ribbon expander's per-front breakdown should show them diverge). **Tuning:** whether the `red_intent_boldness` dial visibly changes red's temperament (bolder = surges at a smaller edge and presses harder; timid = needs a clear advantage), and whether `red_intent_dwell_turns` / `red_intent_trend_window` change how sticky / how trend-reactive it is.
- **Setup:** **Germany — Red Tide** now **preseeds `red_intent` ON** (2026-07-08) — and `war_economy` too, so the supply→posture loop is live — so a NEW Red Tide game exercises this directly. Play several turns; deliberately swing the balance (win/lose ground, bomb/spare red's forces, **bomb red's SAM belt over consecutive turns**, and **bomb red's supply**) while watching the **"ENEMY &lt;posture&gt;" chip on the map ribbon** (which now reads e.g. "Surging (all-in)" / "Consolidating — IADS falling") + the "Enemy posture" SITREP line + red's ATO.
- **Pass:** the SITREP names a posture that tracks the war (surge when red is ahead, consolidate after red loses a base / is pushed back) and it doesn't flip every turn (hysteresis holds); **the trend memory reads** — sustained IADS/resolve/base attrition digs a still-ground-dominant red in (the detail names the driver), and a collapse of your fighters lets red surge at rough parity; **intensity shows** — the further ahead red is the harder it presses (higher aggressiveness / sooner aggressive stances), the deeper the trouble the harder it husbands; when SURGE, red visibly prioritises taking ground; when CONSOLIDATE, red defends/husbands and its target picks are a little less repetitive; **reactive defense is unchanged** throughout (§17 boundary); an active authored `red_tempo` pulse (Vietnam arcs) still owns the stances (P3 yields). Turning the setting off restores stock red exactly.
- **Fail signature:** red plays identically regardless of posture (a seam isn't reaching the planner — check `_offensive_order`'s red branch, `effective_aggressiveness`, `stance_commit_factor`); the posture flips every turn (hysteresis broke); the trend never bites (a ground-dominant red never digs in even as its whole SAM belt is bombed — the `red_intent_history`/`_trend_lookback` memory isn't wired, or the samples aren't banking); intensity looks flat (a 4:1 surge acts the same as a 1.5:1 one — `red_intent_intensity` isn't latching or the seams aren't reading it); consolidate forces red into RETREAT rather than DEFENSIVE (the attack-stance-only gate broke); any change with the setting off (the gate broke); the stance bias fights an authored `red_tempo` pulse (the yield broke).
- **Interim evidence (2026-07-15, headless Red Tide self-play probe, session `gallant-panini-5485e7` — 15
  AI-vs-AI turns through the real GameGenerator build with the campaign preseeds; NOT the played pass, the
  row stays open):** the classifier + trend memory + opportunity window all **moved on real campaign
  state** — turn 0 read "Attrition — ground 1.0x · air holding · front static", turn 1 picked up the real
  ground imbalance ("Attrition — ground 3.0x · gaining ground"), and from turn 2 red latched **"Surging
  (all-in)"** with the **"enemy air spent"** driver named in the detail — the blue-air-collapse opportunity
  window firing after the abstract air war gutted blue's fighters on turn 1. The posture then held stable
  for 13 straight turns (hysteresis: zero flapping). NOT exercised by the probe: CONSOLIDATE (nothing can
  bomb red's IADS/supply headless — ground kills are DCS-only, so supply pegged 100 %), the four planner
  seams' *played* effect, per-front divergence, and the tuning dials. **Caveat for readers:** the §26
  abstract air war INVERTED the flown M1 result (DCS M1 was a 34:0 blue sweep; the abstract model bled
  blue 36 jets on turn 1) — read the probe as "the classifier reacts correctly to the war it was shown",
  never as Red Tide air-balance evidence, and never adjudicate balance off fast-forwarded turns.

### B8 — Strikeable motorpool depots: strike the reserve, force a repurchase · §56 · ☐ UNTESTED (adopted from upstream PR dcs-retribution#859, 2026-07-08; the reserve split (`reserve_armor_for` == `plan_groundwar`), the populator cap/round-robin/idempotence, the generator's parked/weapon-hold/no-datalink render + offset depot, the 1:1 `base.armor` decrement, and the motorpool-vs-front-line loss separation are unit-tested across `tests/**/test_motorpool_*.py` + `tests/ground_forces/test_reserve_armor.py`; **Red Tide now authors a depot near Haina** — headless-verified to bind to Haina/RED + materialise one `MotorpoolGroundObject` (`tests/fourteenth/test_red_tide_motorpool.py`), so the map/in-mission render is finally flyable)
- **What CI cannot exercise:** whether the authored depot actually renders (the maintenance-facility icon on the map; the in-mission `Garage_A` building + the grid of parked reserve vehicles), whether killing a parked vehicle decrements the owner's `base.armor` and forces a repurchase next turn *without* shifting the front line, whether the spawn cap holds, and whether the debrief shows the motorpool losses.
- **Setup:** fly **Germany — Red Tide** (authors the Haina depot; `motorpool_enabled` on by default). The depot renders at Haina from turn 1, but its parked vehicles only appear once red has procured armor (`base.armor` is the purchase stock, empty at turn 0), so **play a couple of turns** before expecting vehicles; then strike some and end the turn. (Or author a `Garage_A` in any other campaign's ME.)
- **Pass:** the depot shows as a present maintenance-facility marker (never "destroyed"); in-mission it's a Garage A building + parked, non-firing, non-moving vehicles; each killed vehicle drops the owner's reserve by one (visible as a repurchase next turn) and appears on the debrief as "Motorpool units lost" / "`<type>` from motorpool"; the front line does **not** move from depot kills; the per-turn vehicle count respects `motorpool_spawn_cap`; a save with an authored depot loads with the motorpool injected.
- **Fail signature:** the depot renders "destroyed"/absent when empty (the `sidc_status` PRESENT pin broke); parked vehicles move or return fire (the passivate/alarm-green broke); a depot kill shifts the front line (the loss leaked into the front-line category — check `commit_motorpool_losses` vs `commit_front_line_losses`); `base.armor` double-decrements on a multi-motorpool CP (the shared-reserve round-robin broke); the per-turn count ignores `motorpool_spawn_cap` (the populator trim broke).
- **Interim evidence (2026-07-15, headless Red Tide self-play probe):** the reserve stock **actually
  accumulates** — Haina's `base.armor` marched 0 → 20 by turn 1 → 59 by turn 14 as red procurement banked
  undeployed armor — so the depot has vehicles to render within a couple of turns of a new game, exactly as
  this row's setup assumes (and well past the `motorpool_spawn_cap` 10, so the cap is live from early on).
  The render / kill / 1:1-decrement / debrief legs stay DCS-only.
- **Upstream drift sync (2026-07-16):** the parking grid + depot now rotate with the authored garage
  heading (upstream `401fbceda`) — when flying this row, also eyeball that the parked lot follows the
  `Garage_A`'s facing instead of sitting in a world-axis N/E grid (Haina's garage is authored at
  heading 0, where the rotation is a no-op — an ME-authored angled garage is what shows it plainly).
### B9 — Air-droppable minefields: mine a road, kill a convoy, carry the field across the turn · §57 · ☐ UNTESTED (built 2026-07-11; **Phase 1 same-turn + Phase 2 persistence shipped**. The drop→track-to-impact→lay→proximity-detonate loop, one-trip-per-unit, charge depletion, the blue-only + non-dispenser reject, the startup grace, and the `minefields_state` write-back (laid `id` 0 / seeded id / charge depletion) are harness-tested in `tests/lua/test_minefields_runtime.py`; the reconcile (create/update/exhaust-remove/untouched/off) + the emitter shape are unit-tested in `tests/fourteenth/test_minefields.py` + `tests/missiongenerator/test_minefieldluadata.py`. The harness models no DCS weapon flight, so the CBU-99 detection + the convoy kill are DCS-only.)
- **2026-07-11 flown Red Tide M1 (`csar-snatch-toggle-question-dfdb7a`): armed cleanly, nothing laid.**
  Load log `Minefields armed (dispenser 'CBU_99', radius 200m, 6 charges/field, power 100)`, zero Lua
  errors across ~125 min, `minefields_state: []` at exit — no CBU-99 was released this mission (none in
  the Tacview weapons log), so the drop→lay→kill→persist loop is still owed a deliberate mining sortie.
- **What CI cannot exercise:** the exact `CBU_99` runtime type string (the whole detection hinges on it), whether the tracked dispenser resolves to a sensible ground impact, whether the scripted explosion actually kills the crossing convoy vehicles and the loss lands as a convoy loss at debrief, the friendly-only F10 marks, and — across two turns — whether a field left undisturbed is re-laid at the same spot with the same charges and disappears once spent.
- **Setup:** enable **"Air-droppable minefields"** in Plugin Options (and, for persistence, the `air_droppable_minefields` setting). Fly an **A-7E / F/A-18C / AV-8B** with the **"Aerial Minefield"** loadout; drop a CBU-99 on a road a RED convoy uses. For persistence, end the turn without the convoy reaching the field, then start the next mission. For **auto-plan**, play **Red Tide** (preseeds `auto_plan_minefields` + the Hornet) and check the ATO for a fragged mining sortie against a red convoy.
- **Pass:** the drop lays a field (an F10 "Minefield (laid)" mark appears for your side); a RED convoy crossing it takes losses that show as convoy losses at debrief; with the setting on, an un-driven field is re-laid next mission at the same spot with the same charges, depletes as convoys hit it over turns, and vanishes once exhausted; the enemy never sees the field. **Auto-plan:** the ATO carries a Hornet BAI mining sortie targeting a red convoy, loaded with the "Aerial Minefield" CBU-99 loadout, and flying it (AI or player) drops the dispenser on the convoy's road and lays a field there.
- **Fail signature:** nothing detonates (the `CBU_99` type string is wrong, or the drop wasn't tracked to impact); a non-CBU-99 drop or a red drop lays a field (the weapon/coalition gate broke); the field detonates at t=0 (the grace broke); a field is lost across the turn or never depletes/disappears (the `minefields_state` channel or `reconcile_minefields` broke); the enemy sees the field.

### B10 — Mission-start briefing popup: the slot-in cards · §58 · ☑ VERIFIED (2026-07-15, user pass — the reworked cards + beep work, "just fine, no issues"; by-design limitation confirmed in the same report: a DCS **dynamic-slot** pilot gets no briefing — dynamic-slot jets aren't player-crewed ATO flights, so the emitter carries no record for them) (was ✗ REGRESSED on the first MP fly — 2026-07-11 flown Red Tide M1 `csar-snatch-toggle-question-dfdb7a`: **the fail signature occurred — NO card or beep was ever noticed by any pilot** (user eyewitness report, same session), despite `BRIEFING|: armed for 12 player flight(s)` at load and zero briefing-related Lua errors across ~125 min of MP with genuine slot-ins and re-slots. First-ever MP/dedicated-server fly of the feature. Built 2026-07-11, extended with the taxi card + raw-turn number; the emitter shape (shared header with the raw-turn mission number + one record per player-crewed flight, AI-only excluded, gated off) is unit-tested in `tests/missiongenerator/test_briefingluadata.py`, and the runtime (briefing card with every field + right group id/duration, the **taxi card flashing `DURATION` s later** with the callsign + ground freq, the `groundFreq` override, the mission-start sweep, AI/unknown/absent no-ops, the birth+sweep debounce) is harness-tested in `tests/lua/test_briefing_runtime.py`. The harness models no DCS UI, so whether the text actually renders on screen is DCS-only.)
- **Root cause (2026-07-11, adversarially cross-checked from dcs.log + the flown miz + the plugin source + DCS API
  research):** two compounding causes, no crash. **(1) Paused-server time compression** — the dedicated server sat
  PAUSED at frozen sim t=0 for ~33 min while all 8 pilots slotted in (wall 00:00–00:17); `timer.getTime()` is frozen
  during a pause, so every card was scheduled for sim t=5 and they ALL fired in one 12-s window right at unpause
  (00:19:40), 2–19 minutes after each pilot sat down, amid startup workload. The cards were almost certainly
  *delivered* (timers scheduled during the pause provably fired at unpause — water_relocate/MANTIS did; the un-pcall'd
  card closures produced zero timer errors; every pilot was seated at fire time) — nobody was looking, because
  **(2) the beep was silently dead**: the plugin passed the bare basename `briefing-beep.wav` to `outSoundForGroup`,
  but the wav lives at `l10n/DEFAULT/` inside the miz and DCS resolves in-miz sounds ONLY with that archive-path
  prefix — a wrong path fails without an error (the code's own comment promised the fallback but never implemented
  it; this row's own pass text predicted exactly this failure). Eliminated with evidence: the flown load DID arm the
  current #573 plugin (extracted byte-identical from the flown miz), BIRTH+`getPlayerName` provably worked for every
  join (Moose logged each by name), no dropped trigger, no timer error. **Residual (~30%):** the post-unpause
  re-slot/late-join cards were NOT compressed and should have painted normally — unverifiable because the plugin had
  zero per-card logging (its designed blind spot).
- **Rework applied (2026-07-11, same session):** (1) the beep path fixed to `l10n/DEFAULT/briefing-beep.wav`;
  (2) every card/taxi fire now logs `BRIEFING|: card -> <group> gid=<id> t=<time>` (and `card skipped (group gone)`)
  so the next fly discriminates "sent but unseen" from "never sent" straight from dcs.log; (3) a skipped fire (pilot
  left the seat before t+5) clears the debounce stamp so their next slot-in still gets the card; (4) a nil
  `getPlayerName` at the BIRTH instant in a briefing-listed group gets one +2 s re-check before being written off as
  AI (the documented MOOSE #806 event-timing race). Harness tests extended to pin all four
  (`tests/lua/test_briefing_runtime.py`, 13 green). The paused-server compression itself is **intended behavior**
  (the sandbox has no wall clock; nothing can fire during a pause) — with a working beep, "cards + beeps ~5 s after
  unpause" is the correct squadron-night contract, now documented in the plugin header.
- **Re-fly pass:** on a dedicated server (paused pre-start joins, then unpause), each pilot gets their own card +
  an audible beep ~5 s after unpause, the taxi card + beep ~12 s later, and dcs.log carries one `BRIEFING|: card ->`
  line per pilot; a mid-mission re-slot gets its cards ~5 s after slotting. **If the log shows the `card ->` lines
  while a watching pilot still sees nothing, escalate to the delivery investigation** (DCS MT/dedicated-server
  message-rendering regressions — forum topics 321287/369258) with the log as proof.
- **☑ VERIFIED (2026-07-15, user pass, session `gallant-panini-5485e7`):** the reworked popup was observed
  working — "our changes make it work just fine, no issues." One accepted limitation from the same report,
  **by design, not a bug:** a pilot who takes a DCS **dynamic slot** gets no briefing — dynamic-slot jets are
  not player-crewed ATO flights, so the emitter has no record for them (consistent with the wider
  dynamic-slots model gap: those airframes are invisible to the campaign layer).
- **What CI cannot exercise:** whether `trigger.action.outTextForGroup` actually paints the card on the pilot's screen, that it reads correctly (campaign / Mission N / date / time / callsign / aircraft / task / field), that the **taxi card follows it** (`<callsign> — Get started up, Contact ground @ 249.50 when ready to taxi`) and each clears after its duration, and — the two paths — that it fires both at mission start in single-player (the sweep) and on a mid-mission slot-in / rejoin on a server (the birth handler), each exactly once.
- **Setup:** leave **"Mission-start briefing popup"** on (default). Generate and fly any mission with a player flight; watch the screen the instant you take the slot, then ~12 s later for the taxi card. For the server path, join a running mission and slot in mid-flight.
- **Pass:** ~5 s after slot-in (not instantly) the briefing card appears for ~12 s (campaign name, `Mission N` matching the kneeboard's turn number, date + time, your callsign / aircraft / task / departure field) with a **short beep**; ~12 s later the taxi card flashes with your callsign + `Contact ground @ 249.50` (and its own beep); each shows once (no double-print), and a re-slot after the debounce re-shows them. (The beep is `briefing-beep.wav`, played by `outSoundForGroup` — if it's silent, the sound resource didn't resolve by basename; try the `l10n/DEFAULT/` path.)
- **Fail signature:** no card appears (the node wasn't emitted, or the birth handler + sweep both missed the slotting); the card double-prints on a single slot-in (the debounce broke); the taxi card never follows (the scheduleFunction broke) or shows the wrong freq; the mission number is turn+1 again (mismatches the kneeboard); an AI-only flight's pilot slot shows a card for a flight that isn't theirs (the group match broke).

### B11 — Ground AI sleep: distant garrisons stop thinking, wake on approach · §59 · ☐ UNTESTED (built 2026-07-12 off the MP-performance complaint; the emitter's positive list (garrisons in; air defense / missiles / ships / buildings / the concealed scripted movers / dead groups out; gated off) is unit-tested in `tests/missiongenerator/test_aisleepluadata.py`, and the runtime (sleep after grace, wake on approach, parked aircraft never wakes, hysteresis never flaps, a hit wakes a sleeper immediately, dead groups stop the poll, no node = no-op) is harness-tested in `tests/lua/test_aisleep_runtime.py`. The harness models no DCS AI, so what sleep actually buys — and that it's invisible — is DCS-only.)
- **What CI cannot exercise:** whether `Controller:setOnOff(false)` measurably reduces server load on a dense mission (the whole point), whether a slept group is visually indistinguishable (renders, killable, death recorded at debrief), whether the wake on approach is seamless (a garrison's embedded SHORAD is live before you're inside its envelope), and that MANTIS SAMs, TIC formations, convoys, SCUDs and the COIN/ambush movers are visibly untouched.
- **Setup:** enable **"Distant ground AI sleeps until aircraft approach"** (Mission Generation → Performance; default off) on a dense campaign (Red Tide — not preseeded, feature-locked). Check the log for `AISLEEP|: managing N garrison group(s)`. Fly toward a rear enemy base garrison, kill a slept unit, watch the debrief; compare server frame/CPU on a heavy turn against the same turn with the setting off.
- **Pass:** the arm line lists a plausible garrison count (not 0, not the whole world); a rear garrison behaves normally when you arrive (embedded SHORAD engages inside its envelope); a unit killed while slept records at debrief like any other; SAM/EWR sites, the FLOT firefight, convoys and every scripted mover behave exactly as with the setting off; a heavy mission runs measurably smoother server-side.
- **Fail signature:** `managing 0 group(s)` on a garrison-rich map (the emitter filter is too tight, or group names don't match the .miz); a SAM site or EWR goes blind (a non-armor TGO leaked into the list); a COIN cell / HVT convoy / VBIED / ambush team / SCUD stops moving (a concealed/map_hidden mover leaked); a garrison never reacts even at close range (the wake poll or the hit-wake broke — check `aiOnOff` semantics against the DCS controller); kills on slept units missing from the debrief (would falsify the setOnOff-keeps-death-events assumption — pull the feature back to default-off and re-scope).

### B12 — SAM guidance-radar redundancy: a site survives its first HARM · §60 · ☐ UNTESTED (built 2026-07-12 off the Red Tide finding "a single HARM kills the entire site"; the layout contract — every SAM layout asks for 2 guidance radars AND its .miz template carries ≥ 2 positions for the slot, across all 31 layout/slot pairs incl. the SA-6's 1S91, the mixed site's both channels, and the NASAMS/Sky Sabre search-slot engagement radars — is CI-locked in `tests/armedforces/test_sam_radar_redundancy.py`, and generation was probe-verified end-to-end (every preset spawns 2 radars of the right type). CI can't exercise DCS's actual guidance logic.)
- **What CI cannot exercise:** whether a site with one dead track radar actually keeps engaging in DCS (the second TR picks up guidance — the whole point), whether MANTIS keeps treating the half-decapitated site correctly (alive, in the network, threat rings honest), and whether AI SEAD re-targets the surviving radar instead of calling the site dead.
- **Setup:** NEW game on any SAM-rich campaign (Red Tide: SA-2/3/5/6 belts + the S-300s). Confirm on the map/intel card that a site shows 2 track radars. Fly SEAD (or let an AI SEAD flight shoot), kill exactly one TR, then press the site with a second aircraft.
- **Pass:** the site keeps launching after the first TR dies (guidance passes to the second radar); it only goes silent after BOTH are dead; MANTIS behaves (no Lua errors, the site stays networked while alive); the second radar sits far enough from the first that one HARM impact never kills both.
- **Fail signature:** a site with one dead TR stops engaging entirely (DCS group guidance doesn't fail over — would gut the feature, re-scope toward splitting radars across DCS groups); both radars die to one missile (positions too close — re-space the template); a LayoutException at generation (`unit_count` vs template positions drifted — the CI test should have caught it); MANTIS misclassifying the site after the first radar kill.

### B13 — Red Tide rear S-300 hubs are 3-battalion regiments · Red Tide (SAM-belt STANDARD) · ☐ UNTESTED (built 2026-07-12 — a pre-lock Red Tide change, recorded at the time as a feature-lock override; the marker laydown — 3 clustered LORAD battalions + a shared EWR at Sperenberg/Kastrup/Schönefeld — and the single-radar contract (fork faction `Russia 1980 (Red Tide)` LORAD presets → single-radar S-300/SA-5 layouts; base `S-300 Site` still §60-doubled) are CI-locked in `tests/fourteenth/test_red_tide_sam_regiments.py`, and the loader assignment (3 `long_range_sams` preset locations per hub CP) + single-radar generation were headless-verified. CI can't exercise MANTIS netting or DCS terrain.)
- **What CI cannot exercise:** whether the three battalions + EWR at a hub actually net into **one** MANTIS regiment (shared early warning, graceful degradation), whether the new battalion spots are **open ground** (pydcs has no GCW surface query — a spot could be forest/water), and whether the regiment now survives a SEAD pass instead of dying in one turn like the old single site.
- **Setup:** NEW game on Red Tide, **keep the recommended enemy faction `Russia 1980 (Red Tide)`** (single-radar only applies with the fork). Fly toward Sperenberg / Kastrup / Schönefeld; check the map shows 3 separate S-300 sites + an EWR per hub, each site with **one** track radar. Run a SEAD/DEAD pass and see how much of the regiment survives.
- **Pass:** each hub shows 3 dispersed single-radar LORAD fire units + a shared EWR, all one networked IADS (MANTIS); killing one battalion's radar drops that battalion but the regiment keeps engaging; the belt takes several sorties to roll back (not one HARM / one turn); every new battalion sits on open ground; front MERAD screen still shows its §60 two-radar sites. **Battalion composition (leaned 2026-07-12 after the generated-save review):** S-300 battalion = 1 search radar + C2 + 1 track radar + 4 TELs (+PD); SA-5 battalion = Tin Shield + Square Pair + 6 launchers (+PD), no battalion-level P-19/P-14 — the shared EWR is the regiment's early warning. A hub mixing S-300 and SA-5 battalions is expected (the loader fills LORAD markers with a random faction LORAD preset), not a fail.
- **Fail signature:** a battalion spawns in forest/water or on a building (re-place that marker in the ME); the three battalions don't net (spacing > comms range, or an EWR missing — check the F10 IADS view); a hub shows 2-radar S-300 sites (the fork faction wasn't selected, or §60 leaked into the single-radar layout); the regiment still evaporates turn 1 (too few battalions / netting broke); `Russia 1980 (Red Tide)` missing from the faction dropdown (faction JSON didn't load).
- **2026-07-12 in-app catch (user):** the fork's third single-radar preset `SA-10A/S-300PT (Single Radar)` was all High Digit SAMs units and showed in a no-mod game's buy menu (the mod-off strip matches preset *names* only). Preset removed; `apply_mod_settings` gained a provenance backstop + `Game.on_load` heals pickled `ArmedForces`; guards in `tests/fourteenth/test_faction_mod_presets.py`. The buy menu at a red CP should now offer only vanilla-unit groups.

### B14 — Host red scramble: the F10 bandit spawner feeds the flight · §61 · ☐ UNTESTED (built 2026-07-12 off the M1 debrief "once the first wave was over it felt quiet"; the emitter contract (gated, red airfields nearest-front first, templates best-interceptor first, no-template/no-base = no node) is unit-tested in `tests/missiongenerator/test_redscrambleluadata.py`, and the runtime (host-name menu gating incl. the pre-seated sweep, coalition fallback, spawn at the picked base with the QRA air profile, weapons-free + host announce, the AttackGroup vector onto the nearest airborne blue player, no re-task while the target holds, unique repeat clones, the 9-base menu cap) is harness-tested in `tests/lua/test_redscramble_runtime.py`. Whether the DCS AI actually presses the intercept is DCS-only.)
- **What CI cannot exercise:** whether the MOOSE `SpawnAtAirbase` air-spawn clone comes off the field flying (not stalled — the QRA InitSpeed lesson), whether the `AttackGroup` task makes the bandits genuinely commit to the players (and re-commit when re-vectored to a new target), whether the F10 menu renders per-group for only the named host in real MP, and that the armed template actually carries an A2A loadout (the pydcs default-task payload path).
- **Setup:** Red Tide preseeds the setting + plugin + `hostPlayers: Flash` (a **substring** match — the host's static name tag covers the changing `"<flight> 1-x | Flash"` prefix; empty = every BLUE client sees the menu). Generate, fly with at least one blue jet airborne, open F10 → Other → **HOST: Red Scramble**, press a base → `MiG-29S x2`, and separately the **EMERGENCY** command.
- **Pass:** only your slot sees the menu (a squadmate confirms theirs is clean); within seconds of the press the announce card appears and 2 armed bandits appear over/at the chosen base (log: `REDSCRAMBLE|: spawned ...`); they turn toward the nearest airborne blue fighters, commit, and shoot; the EMERGENCY press launches from the base nearest the airborne players; a second press spawns a fresh flight; killing them all ends it (no respawn) and nothing changes at the turn boundary.
- **Fail signature:** no menu for the named host (fragment mismatch — the match is a case-insensitive substring of the in-game name, so check the tag really appears in it; or the node wasn't emitted — check the setting + `REDSCRAMBLE|` arm line); everyone sees the menu despite a configured name (option didn't reach the miz — the §36 plugin-preseed lesson); a non-host sees the menu (their name contains the tag — pick a more distinctive fragment); bandits spawn stalled/diving (InitSpeedKnots didn't take — QRA history); bandits spawn then orbit ignoring the players (`AttackGroup` via `setTask` rejected — re-scope the vector push to a Mission-route task, the §15 combatsar lesson); a spawn press does nothing with `spawn failed` in the log on hot/runway mode (ramp congestion — use the default air mode); red QRA dispatcher errors right after a clone (alias collision with the `Intercept|` templates — rename).

### B15 — Squadron-sequenced Hornet/Tomcat board numbers · §62 · ✅ VERIFIED 2026-07-16 (user visual confirmation on the flown Scenic Route turn-3 test — a US Navy 2005 carrier campaign fielding both Hornets and Tomcats: *"The Modex on our fork is 100% working I watched it with the last test. Everyone's modex looked accurate."* This settles the row's one DCS-only unknown — **DCS does paint the mission's `onboard_num` on the airframe**, and it clears the specific doubt below about the Heatblur F-14's livery-driven BORT rendering ignoring it (8 Tomcats were airborne on that test). Built 2026-07-12 off the user finding "board/modex numbers are completely random"; the per-squadron 100/200/300 blocks, the cross-flight X00/X01/… sequence, Tomcats-before-Hornets block order, per-coalition blocks, the non-modex no-op, the whole-block country reservation, the nine-squadron wrap, and the pydcs id guard are unit-tested in `tests/missiongenerator/test_modex.py`.)
- **Scope of the confirmation:** a coarse visual pass ("everyone's looked accurate"), not a block-by-block audit — it establishes the *mechanism* (`onboard_num` → painted number), which is what every downstream design rests on. Not yet separately confirmed: a nine-squadron wrap, and any airframe outside `MODEX_AIRCRAFT_IDS` (moot today — the set is the whole feature; it matters only if upstream [#863](https://github.com/dcs-retribution/dcs-retribution/issues/863) per-pilot pins land, since a pin deliberately bypasses the id set and would apply to e.g. the A-4E-C).
- **What CI cannot exercise:** the rendered board number on the jet skin / in the F2 view — in particular the Heatblur F-14, whose BORT number rendering is livery-driven and may ignore the mission's `onboardNum`.
- **Setup:** Any campaign fielding a Hornet or Tomcat squadron (Red Tide fields the Hornet). Generate a mission with at least two flights from the same squadron; check the board numbers in the F2 view / mission editor (or open the `.miz` and read each unit's `onboard_num`).
- **Pass:** every jet of the squadron wears its block in sequence (first flight 100/101, the next flight continues 102/103, …); a second Hornet/Tomcat squadron wears a different hundred block; F-14 squadrons hold the 100/200 blocks when sharing a wing with Hornets; non-Hornet/Tomcat aircraft are unaffected.
- **Fail signature:** random three-digit numbers on a Hornet/Tomcat (allocator not reached — check the four `modex_allocator.assign` sites in `aircraftgenerator.py`); two squadrons sharing a block (air-wing iteration order unstable); a same-country non-Navy jet wearing a number inside a squadron block (the block reservation didn't take); the F-14 model showing a number different from the miz's `onboard_num` (Heatblur livery limitation — document, don't chase).

### B16 — Ship-launched cruise missile raids · §63 · ☑ VERIFIED (2026-07-16 flown Persian Gulf "Scenic Route" test, session `dcs-test-results-001fd7` — the scripted FireAtPoint push fires the exact commanded quantity, on BOTH vanilla hulls, and the whole magazine loop closed end-to-end)
- **2026-07-16 evidence (dcs.log + DCS debrief.log + the flown `retribution_nextturn.miz` + headless `test.retribution` dump):** auto raid `CRUISEMISSILES|: 0158 | GOSHAWK (Naval Two Ship) fired 6 at PADEMELON (10 left this mission)` at **+254 s** — inside the new [240, 900] s stagger window (#607); exactly **6 `shot` events, weapon `BGM-109C Tomahawk`, initiator `TICONDEROG`** — the hull the row called *least certain* fires cleanly (2×8 = the 16 magazine, validating the hull table); 7 `hit` events on the target `.Command Center` (killed — in the Qt debrief loss list) + a Tomahawk `kill` on a Ural-375 recorded **natively**; the raid target was the **C2 TGO** (C2-first pick) and the post-commit save already re-plans next turn's raid onto **INSECT, the next command center** (re-targeting after the kill); the state mirror round-tripped — Qt debrief row "**6 fired, 10 remaining**" and the save's `cruise_missile_magazines` reads `GOSHAWK: 16→10` (no rearm, no orphaned keys); an earlier same-night mission (separate save) also flew the **player F10 marker call-for-fire** (`0124 | BUFFALO (Escort) fired 4 at your F10 marker`) and a Burke-group auto raid (96→86) — both fire paths + both vanilla hulls demonstrated; zero plugin/script errors in either mission.
- **First ground-AD cruise-missile intercept observed (2026-07-17 flown Scenic Route Merged, Tacview `Tacview-20260717-172716`):** a red Tor killed one of the 6 raid BGM-109s ~12.7 km short of the aimpoint — INSIDE the 8 NM defender-wake ring — and 5/6 impacted the target. Suggestive of the wake working but **not conclusive**: the same mission's Tors were also engaging JSOW glide bombs at their own sites (5 intercepts), which makes them hot without §63's help. A raid against a quiet (un-bombed) defended target is still the clean wake test.
- **Observed gap (user-watched live, 2026-07-16): NO defender engages a cruise raid — the SHORAD-intercept half of §63 FAILED.** The target's point defense (`0011 | SLUG (SHORAD)`, 2× SA-15 Tor + Dog Ear SR, ~250 m from the impact point) sat **alive and idle** through the whole 6-missile salvo. Root cause, code-confirmed: SLUG ran **vanilla** (red MANTIS managed only the 3 "(SAM)" groups; red's SHORAD link armed **zero** PD groups — the bridge wraps only `IadsRole.POINT_DEFENSE` escorts hanging off SAM nodes, and SLUG is a standalone SHORAD TGO guarding a C2 site) with no alarm-state option in its miz group ⇒ DCS default **ALARM STATE AUTO, which never goes weapons-hot for a weapon object** (a cruise missile is not an "aircraft threat" to the auto-wake). The *managed* paths are equally blind by construction: MANTIS EMCON wakes off MOOSE `Detection` (scans **units**, never weapons), and the SHORAD link wakes only off `SHORAD.Harms`/`SHORAD.Mavs` (ARMs + Mavericks — **no BGM_109/Kalibr entry**) or MANTIS SEAD suppression. So no defender anywhere in the stack could wake for a cruise raid unless already hot for another reason. The B16 core-loop verdict stands (intercept was an explicit "CI cannot exercise" unknown, not a pass criterion).
- **Defender wake VERIFIED in the air (2026-07-17 night fly, Tacview `Tacview-20260717-214932`,
  session `tacview-test-analysis-5bb161`):** the launch logged `CRUISEMISSILES|: defender wake --
  7 AD group(s) near the aimpoint held RED` + `0048 | FERRET (Naval Two Ship) fired 6 at
  WATERBUCK (42 left this mission)` at sim t≈480 (inside the stagger window), and the woken Tors
  **killed all 6 BGM-109s** (Tor 9M330 terminals matched each TLAM terminal 52–240 m, 5–6 km
  short of the aimpoint). Conclusive this time — the raid ran t=500–1060, before any other blue
  weapon was in that area (Mavericks from t≈1387, HARMs from t≈3240), so the Tors had no other
  reason to be hot. Both pass criteria met (wake log + visible 9M331/9M330 engagement); the
  stand-down half wasn't disprovable from Tacview but nothing engaged abnormally later. **Balance
  observation:** a 6-missile raid against a woken 3-Tor defense = 0 leakers — with the wake live,
  small raids against intact PD are free intercepts; saturation (bigger `#N` salvos) or
  SEAD-first is now the real doctrine, which is the realistic outcome.
- **Fix BUILT same session (now flown, see above): the defender launch wake.** Every launch (raid + F10 call share `fireCruise`) now sets the opposing side's ground AD groups within `defenderWakeRadiusNm` (8 NM) of the **aimpoint** to **alarm state RED** — alarm state only, `enableEmission` untouched (the crash-history constraint) — held ~estimated missile arrival + `defenderWakeExtraS` (300 s), then restored to AUTO (per-group `wakeUntil` bookkeeping; overlapping launches extend the hold; a MANTIS-managed site keeps its own EMCON loop). Options `defenderWake`/`defenderWakeRadiusNm`/`defenderWakeExtraS`; harness-pinned (wake, stand-down, far/friendly/non-AD selectivity, kill switch) in `tests/lua/test_cruisemissiles_runtime.py`. **Re-fly pass:** the launch logs `CRUISEMISSILES|: defender wake -- N AD group(s) near the aimpoint held RED` and the SA-15 visibly engages the inbounds (Tacview: 9M331 launches at BGM-109s). **Fail signature:** the wake log fires but the Tor still never shoots (residual gap = DCS's own Tor-vs-TLAM engagement logic, not alarm state); or defenders stuck RED long after the raid (stand-down broke).
- **Second flown test, 2026-07-16 (turn 3, PRE-wake build — PR #610 unmerged when flown; Tacview `Tacview-20260716-014958`):** the raid re-targeted **INSECT** exactly as the post-commit save predicted, from the debited magazine (`fired 6 at INSECT (4 left)`), and a same-turn re-fly logged the identical `4 left` — **flown proof the debit is turn-boundary-only** (regeneration never double-counts, the §54 rule). Salvo fate: **2 of 6 killed by red NAVAL SAMs** — a Krivak pair (`0115 | NAUTILUS`) parked in the flight path fired 13 SA-N-4s (`SA9M33`), two Tomahawk removals matching the missile terminals to the second — **ship AD engages cruise missiles natively** (no alarm-state model afloat), so the saturation game is real wherever a defender can shoot; **1 terrain loss** descending through 1256 m over the interior mountains (no shot correlates — DCS's FireAtPoint route doesn't terrain-follow); **3 arrived** (two within 60 m of INSECT, one at 257 m). Meanwhile the target's own PD — `0122 | DINGO (PD)`, a **SHORAD-linked** Tor held dark (this laydown armed red's link: "3 point-defense group(s) held dark") — fired nothing: the **linked-PD variant of the gap is now flown-confirmed** (turn 2 confirmed the vanilla-AUTO variant). Launch at sim t≈736 s — inside the [240, 900] stagger window (wall-clock deltas were shorter; the user ran time acceleration). Bonus fix-coverage fact: the bridge builds SHORAD with `useEmOnOff = false`, so linked PD is darkened by **alarm GREEN** — the wake's alarm-RED override reaches it (no emission toggling needed).
- **Residual (minor):** the `#N` marker-text salvo sizing untested (default salvo 4 used); the CH `*_LACM` Kalibr hulls + a red-side raid unflown; full magazine exhaustion → "ship goes silent" untested.
- **What CI cannot exercise:** whether a scripted `PushTask(FireAtPoint, weaponType=CruiseMissile)` makes the ship AI fire exactly the commanded quantity (the ME-authored task is community-proven; the scripted push is the same task table but unflown); which curated hulls honor it — the vanilla `USS_Arleigh_Burke_IIa` is the near-certain case, the vanilla `TICONDEROG` Tomahawk fit the least certain, the CH `*_LACM` hulls per their mod's fits; DCS Tomahawk/Kalibr flight over terrain at range; and whether MANTIS/SHORAD (Tor/Pantsir/Patriot) actually engages the inbound missiles.
- **Setup:** any campaign whose `.miz` authors a ship TGO with a curated LACM hull in range of enemy ground (or drop-spawn one, §20). Turn ON `cruise_missile_strikes` + `cruise_missile_auto_raids` (Mission Generation → Naval strike; the `cruisemissiles` plugin defaults ON). Fly (or spectate) past the raid delay (default 240 s); separately place an F10 marker on a shore target and press F10 → Cruise Missile Strike → "Fire at last F10 map marker", then "Magazine status"; repeat with a marker whose text is just `2` (or `#2`) — the salvo should be exactly 2.
- **Pass:** at ~4 min the launching side gets "CRUISE MISSILES AWAY — N missile(s) from <ship> inbound to <target>" and the defender only "LAUNCH WARNING — enemy cruise missile launch detected" (log: `CRUISEMISSILES|: <group> fired N`); missiles visibly launch, cruise to the planned building/C2 target and impact (Tacview: BGM-109/Kalibr tracks); the F10 call lands a salvo near the marker (a `#N` marker text fires exactly N); "Magazine status" counts down by exactly what fired; next turn the debrief shows the killed TGO units as ordinary ground losses, and the following mission's magazine reads the debited stock (fire the whole magazine over 2-3 missions → the ship goes silent, menu answers "no ship with missiles in range").
- **Fail signature:** cue fires but no missile leaves the rail (the ship AI rejected the scripted FireAtPoint or the hull carries no cruise missiles — check the hull against the encyclopedia, drop it from `LACM_SHIP_DCS_IDS` if the fit is wrong); guns fire instead of missiles (weaponType flag ignored — re-check 2097152 reached the task table); the full VLS ripples ignoring `expendQty` (quantity not honored — cap the magazine emit as the only guard and note it); magazine never decrements across turns (`cruise_missiles_state` missing from the state json — the §57 dirty_state path); a raid fragged inside a ROE zone on a Vietnam/COIN campaign (the §40 gate didn't hold); missiles vanish into a ridge every time at max range (shorten `MAX_RAID_RANGE_M`).

### B17 — Carrier deck spawn policy (six-pack last resort + MP slot timing) · §64 · ☐ UNTESTED (built 2026-07-16 off the user finding "AI taxi into me on the supercarrier / get stuck between me and the catapult"; the placement/hold split — AI always ≥1s late-activated, player flights taking the 1s placement activation under LAST_RESORT and keeping the six-pack under SIXPACK_FIRST, the delayed-client uncontrolled+StartCommand path, the WARM/RUNWAY/airfield no-ops, and the boolean→enum save migration — is unit-tested in `tests/missiongenerator/test_carrier_deck_policy.py` + `tests/settings/test_carrier_deck_policy.py`. How DCS actually places and taxis the deck is DCS-only.)
- **What CI cannot exercise:** the two deliberate unknowns — (1) whether DCS genuinely overflows delayed spawns *into* the six-pack once the other deck spots are full (the literal "last resort" semantics; the 1-second trick is only proven to move spawns *off* it), and (2) deck crowding/behavior with several client flights parked uncontrolled from mission start (the reason upstream late-activated carrier flights). Plus the core payoff: does an AI flight still jam against the player now that the player is parked clear of the cat 1/2 taxi lane.
- **Thinned-deck data point (2026-07-17 night fly, fresh turn 1 post-#633 deck cut, session
  `tacview-test-analysis-5bb161`):** big improvement — every planned carrier package launched
  (Khasab BARCAP F-14Bs, E-2C, S-3B all flew; no lost SEAD/DEAD packages) and recoveries produced
  no crashes. Residual: **4 late-alert BARCAP jets despawned on deck** (the Stennis BARCAP F-14B
  pair at t=2061 and the "LHA-2 Saipan BARCAP" Hornet pair at t=2445, same-second pair removals
  at deck level, briefed departures 2:33–3:18 h — stuck-alert cleanup, not gridlock). **Flags found in passing (both resolved next session):** the
  "LHA-2 Saipan BARCAP" Hornets on the CVN deck were a MIS-READ — Retribution group names lead
  with the package TARGET, so those were CVN-based Hornets flying BARCAP *over* the Saipan CP
  (basing was always correct; no campaign edit needed). The real defect was the **CP-name/hull
  mismatch** (CP "CVN-74 John C. Stennis", hull CVN-71 Theodore Roosevelt + 71X card): the
  supercarrier upgrade keys on the CP name and "CVN-74" fell through its else-branch to CVN_71.
  **FIXED engine-side (new games):** `hull_consistent_carrier_name` deals a supercarrier game
  only upgrade-mapped names (the name picks WHICH supercarrier) and otherwise prefers the
  hull's own display name (free Stennis = CVN-74, Tarawa = LHA-1); existing saves keep their
  boat via the legacy CVN-71 fallback. Tests `tests/test_carrier_naming.py`; features doc §65.
- **Deck over-capacity data point (2026-07-17 flown Scenic Route Merged, AI-only):** the merged campaign bases **39 fixed-wing on the one CVN-71** (16 F-14B + 23 Hornets — two carriers' wings merged onto one boat). Consequences observed in the Tacview + log: the delayed CARACAL SEAD (2-ship) + CARACAL DEAD (4-ship) packages activated on deck at t≈18 min, **never taxied, and were silently despawned by DCS's stuck-AI cleanup** 53–58 min later (whole groups removed in the same second, no crash/ejection events — the mission simply lost its SEAD and DEAD), and **3 Stennis-Escort Hornets crashed during recovery** (real CRASH events + crew ejections → the sea survivors that drove the CSAR findings). Not a §64 bug — LAST_RESORT only moves spawns off the six-pack — but the campaign-authoring lesson is a deck-capacity ceiling: a boat carrying two air wings loses its delayed packages to gridlock and its recoveries to a fouled deck. Watch both signatures (same-second group despawns of never-taxied deck jets; landing crashes with ejections at the boat) on any crowded-carrier fly.
- **Setup:** a carrier campaign with a player Hornet flight + at least two AI carrier flights (cold starts). Leave `carrier_deck_policy` on its default (Six-pack is overflow parking); set `never_delay_player_flights` OFF and give one player flight a package TOT ≥ 15 min out to exercise the MP slot fix. Generate for multiplayer, slot in, start up slowly, watch the deck.
- **Pass:** the player jet spawns somewhere other than the six-pack (fantail/island/elevator spots); AI flights spawn elsewhere too, taxi to the cats, and launch without deadlocking on the player; the late-TOT player flight's slots are pickable from ~mission start (jet parked cold, engines off) and its AI members only crank at the planned push time; flipping the setting to "Players spawn on the six-pack" puts the player back on the six-pack.
- **Fail signature:** the player still spawns on the six-pack under last resort (the 1s activation didn't fire — check `FlightLateActivationTrigger<gid>` exists in the miz triggers); a delayed player flight's slots missing until push time (the uncontrolled path didn't take — check the group is `uncontrolled` with a `FlightStartTrigger<gid>`); AI wingmen of the delayed flight crank at mission start (StartCommand push not holding); aircraft spawning stacked/inside each other when the deck is heavily loaded (DCS refused to overflow gracefully — fall back to exempting overflow flights at generation, we know the deck count); a client slot unenterable in MP after the 1s activation (late-activated client groups misbehaving — revert clients to spawn-at-start and accept the six-pack in that mode).

### B18 — Curated carrier comms: the CV Operations Data page reads like a boat card · §65 · ☐ UNTESTED (built 2026-07-16 off the user complaint about the DCS-generated page ("Callsign: 0796 | CVN-71 …, TACAN 1X, Link 4 255.0"); the curated table invariants, the stored-wins / taken-degrades-to-neighbor precedence for all four resolvers, the shared-pool ICLS allocator, and the flagship-name collision guard are unit-tested in `tests/test_carrier_comms.py`, and the whole path is headless-verified through the real GameGenerator → MissionGenerator pipeline on Enduring Resolve (miz carries `CVN-74 John C. Stennis`, 73X `STN`, ICLS 14, Link 4 336.4, ATC 308.000). Whether DCS renders and radiates it is DCS-only.)
- **What CI cannot exercise:** the actual DCS kneeboard render of the auto-generated CV Operations Data page, and whether the boat's TACAN/ICLS/Link 4 beacons radiate on the curated channels for a real Hornet/Tomcat recovery (the ActivateBeacon/ICLS/Link4 commands are the same pydcs tasks as before — only the values changed — so the risk is low).
- **Setup:** any campaign with a vanilla carrier (Enduring Resolve fields the Stennis; any Caucasus CVN campaign works). Generate, slot a Hornet (or open the kneeboard as any deck aircraft), find the CV Operations Data page.
- **Pass:** the Callsign line reads the bare hull name (no `NNNN | ` prefix); TACAN reads the hull-flavored channel + boat ident (Stennis: 74X STN, or the nearest neighbor where the map owns the hull channel — 73X on Afghanistan since Bagram is 74X); ILS reads the hull-keyed channel (Stennis 14); Link 4 reads 336.x; ATC reads the stable 30x.000; the boat's TACAN needle/DME, ICLS bars, and ACLS lock actually work on those numbers; the same numbers come back on the next turn's mission.
- **Fail signature:** the id-prefixed name on the Callsign line (flagship naming didn't reach the unit — check `_flagship_name` / the duplicate guard); TACAN 1X with a changing ident (curated path not taken — the hull id isn't in `CARRIER_COMMS_PLANS`, e.g. a mod boat, which is by-design legacy); a dead TACAN needle on the curated channel (channel collision with a map beacon that `Beacons.iter_theater` doesn't know — mark it and re-pick the hull's channel); numbers changing between turns (persistence to the control point didn't stick — check `frequency`/`link4`/`icls_channel` on the CP in the save).

### B19 — Weather-aware auto-planning · §67 · ☐ UNTESTED (built 2026-07-17; the sky classifiers, the recon-suppression gate, the storm demotion's order preservation + factory-name lock, and the HTN integration are unit-tested in `tests/fourteenth/test_weather_planning.py` + `tests/test_armed_recon_planning.py` — whether a real stormy turn's ATO visibly reads different is app-level)
- **What CI cannot exercise:** a real campaign turn whose §47 weather rolled Raining/Thunderstorm producing an ATO with no auto-added TARPS/drone recon flights (rain+storm) and the CAS/BAI/interdiction packages planned after the strike/OCA/IADS ones (storm only) — and a clear-sky turn reading exactly like pre-feature.
- **Setup:** any campaign with `weather_aware_planning` ON (default). Ride turns until the SITREP/briefing weather shows rain or a storm (or force it by re-rolling turns); open the ATO.
- **Pass:** on a rain/storm turn no Strike/DEAD/Armed Recon package carries the optional TARPS/recon add-on flight (player-planned recon still plannable by hand); on a thunderstorm turn the offensive plan leads with strikes/OCA/IADS and the front-line CAS/BAI packages sit later in the plan (they still exist if jets remain); on a clear turn the ATO is indistinguishable from the setting OFF.
- **Fail signature:** recon birds fragged into a thunderstorm (the gate didn't reach `_maybe_plan_tarps_recon` — check `recon_suppressed` reads the right game); CAS vanishes entirely in a storm (demotion should reorder, never remove — check `demote_weather_hostile_methods` keeps the set); a clear-sky ATO differs with the setting toggled (the no-op contract broke); a crash on an old save without conditions (the getattr guards).

### B20 — Adaptive procurement: posture-coupled spending + SAM repair · §68 · ☐ UNTESTED (built 2026-07-17; the shift table, intensity scaling, clamps, the repair's gate/cap/priority/budget/exclusions/wreck-cleanup, and the weighted-choice gate are unit-tested in `tests/fourteenth/test_adaptive_procurement.py` — the felt economy needs a multi-turn campaign)
- **What CI cannot exercise:** red visibly rebuilding a struck SAM site over following turns (`auto_repair_air_defenses` ON): launchers/radar coming back alive at the same site a couple of units per turn, the site's threat ring re-growing, no duplicate wreck models under the repaired units; and (with `red_intent` ON) a surging red's ground purchases visibly outpacing its aircraft buys vs a consolidating red's.
- **Setup:** a campaign with a red SAM belt (Red Tide post-lock, or any modern laydown). Turn ON `auto_repair_air_defenses` (Campaign Management → Commander economy; `adaptive_procurement` is already default ON). DEAD a red SA-10/SA-2's radar + a launcher, end turn a few times, watch the site on the map/intel and red's Finances-visible behavior.
- **Pass:** the struck site regains ~2 units per turn (radar first) while red's budget shows the spend; a fully-dead site only rebuilds after the partially-alive ones; command centers/comms nodes never come back; with the toggle OFF the site stays dead forever (pre-feature behavior).
- **Fail signature:** the whole site back in one turn (the cap broke); a repaired unit standing next to its own wreck model (`_clear_wreck_near` didn't fire); C2/comms nodes regenerating (category filter broke — §51/§52 must stay permanent); threat rings not re-growing after repair (`invalidate_threat_poly` not reached); blue money spent on repairs when the player manages repairs manually (the `manage_runways` coupling broke).

### B21 — Cross-package SEAD-before-strike coordination · §69 · ☐ UNTESTED (built 2026-07-17; the pure window math and the scheduler wiring — ring matching, latest-provider windows, player/ASAP immunity, provider read-only, massing, the gate — are unit-tested in `tests/test_sead_strike_coordination.py`; whether the flown timeline actually reads "SEAD first, then the push" is Tacview-level)
- **What CI cannot exercise:** a real generated mission where an AI strike package tasked into a defended area arrives AFTER the SEAD/DEAD package servicing that SAM is on station (Tacview timeline: HARMs/suppression first, bombers 2–10 min behind), instead of the old random spread that could send the bombers in half an hour early.
- **Setup:** any campaign where the AI plans SEAD/DEAD + strikes into the same defended area (`sead_strike_coordination` default ON). Generate a turn with a red SAM covering a strike target; check package TOTs in the ATO, then fly/spectate and read the Tacview.
- **Pass:** the ATO shows the strike/BAI/OCA packages targeting SAM-covered objectives with TOTs ~2–10 min after their covering SEAD/DEAD package's TOT (several strikes may share one window — the push); packages against undefended targets keep the random spread; a player package's TOT is never moved by this (and a player-flown SEAD still has AI strikes timed behind it).
- **Fail signature:** a strike still arriving before its SEAD with both AI (the ring match missed — check the SAM TGO's `max_threat_range` and that the SEAD's target is the TGO); strike TOTs pushed absurdly late (the window should clamp to `earliest_tot` — check `coordinated_strike_tot`); player packages rescheduled (the movability gate broke); mass mid-airs at the shared TOT (packages route separately, but if seen, widen `SEAD_WINDOW_LEAD` spacing per client or stagger within the window).

### B22 — COMINT collection: the campaign take (tiering + leak + reveal) · §70 · ☐ UNTESTED (built 2026-07-18; the tier gating incl. dead-net-beats-collector, the OFF exact no-op, the survivor requirement, drone eligibility, leak determinism, the reveal's range/known/`map_hidden` rules + re-init idempotence, and the posture-detail earn are unit-tested in `tests/fourteenth/test_comint.py` — the kneeboard render + the map snap are app-level)
- **What CI cannot exercise:** the rendered COMINT block on a real Mission Info kneeboard page, and the map experience of a Tier-2 reveal (an amber suspected-activity circle replaced by the exact enemy symbol at turn start). An in-APP pass (no DCS flight needed beyond generating/ending turns).
- **Setup:** a COIN campaign (Enduring/Inherent Resolve — insurgent spawns are both sources and reveal candidates) with `comint_collection` ON (Campaign Management → Campaign features). Plan a drone or C-130J JAMMING sortie, end the turn with it surviving, open the next turn's kneeboard + map. Then kill every red comms/CC node (or on COIN, clear the concealed spawns) and end another turn.
- **Pass:** turn A (net up, no collector): the kneeboard COMINT block reads "Enemy net active … ambient take only" and the SITREP still shows the enemy-posture detail (when `red_intent` is on). Turn B (collector survived): the block adds "Collection sortie banked a full take", an "Intercepted tasking traffic: …" line naming a real red package/objective with a ±30 min window, and — when an eligible concealed site sat within 60 km of a source — a "Transmissions localized: …" line with that circle now an exact symbol on the map (one site only). With `red_comms_net` also on, the block additionally lists the **active nets** (fixed C2 stations by name + frequency + area; each concealed spawn as "suspected clandestine net @ <freq> — <area> area" — NEVER the cell's identity or type; ≤5 lines + a "+N more" tail). Net dead: the block reads "Enemy C2 net silent — no COMINT take." and the posture detail line disappears from the SITREP.
- **Fail signature:** a COMINT block while the net is dead (source walk broke); two circles snapping in one turn or a snap repeating after a cheat-capture/TGO-purchase re-init (the `comint_reveal_turn` stamp broke); a §50 convoy-ambush team appearing on the map (the `map_hidden` exclusion broke — nothing may telegraph those); the leak naming a different package after a mission re-generation (determinism broke); any COMINT output with the setting OFF.

### B23 — Red comms net: audible + DF-able enemy C2 · §70 · ☐ UNTESTED (built 2026-07-18; the emitter's frequency plan — x.500 off-grid, GUARD skip, registry reservation, cross-mission determinism, collision probing — and the runtime invariants — grace, per-node stagger, loop+stop windows, `node_dead`, clean no-op — are pinned in `tests/missiongenerator/test_rednetluadata.py` + `tests/lua/test_rednet_runtime.py`; audibility, per-module DF needle behavior against a scripted transmission, and power reach are DCS-only)
- **What CI cannot exercise:** actual cockpit audio (is the CW clip clearly receivable at the emitted power from realistic ranges), each module's ADF/DF needle behavior against a scripted looped transmission, and whether the windowed cadence reads as traffic rather than a beacon.
- **Setup:** any campaign with red `comms`/`commandcenter` TGOs (Red Tide post-lock is ideal — its 9-node C2 net). Turn ON `red_comms_net` (Mission Generation → Battlefield life; the "Red comms net" plugin ships enabled). Generate, then read the assigned freqs from dcs.log (`REDNET|: armed -- N net(s), first window in 180s: <name> @ 271.500 AM; …`). Fly a UHF-DF airframe (F-4E ADF mode / F-14 ARC-182 "V/UHF 2" DF / F/A-18C UFC ADF / F-5E radio-1 DF) toward the front and tune a listed frequency.
- **Pass:** morse beeps audible on the tuned freq during a window (~45 s roughly every 4–5 min per node) and silence between windows; the DF needle points at the node while it transmits and drops when the window closes; two nodes never key up in the same moment (stagger); killing the node ends its windows for the rest of the mission (`REDNET|: <name> is off the air` in the log); nothing ever transmits on a briefed blue channel. **The clandestine hunt (C2, a COIN campaign):** each concealed insurgent spawn transmits SHORT windows (~20 s) with LONG silence (~8 min), tagged "(clandestine)" in the arm log; a needle cut caught during a window points inside that spawn's dashed suspected-activity circle; killing the cell ends its net.
- **Fail signature:** total silence (check dcs.log for `REDNET|: armed` — absent = the setting/plugin gate; present but inaudible = the `l10n/DEFAULT` path or power too low — raise `powerW`, it is range not loudness, §51); a net on a briefed blue channel (the x.500 offset broke — check the emitted mhz values); the needle still pointing between windows (`stopRadioTransmission` failed — the loop never ended); all nodes keying simultaneously (the stagger broke); a dead node still transmitting all mission (the `node_dead` walk broke — check the unit names vs the `<name> object` static convention); a §50 convoy-ambush team transmitting or listed on the kneeboard (the `map_hidden` exclusion broke — nothing may telegraph those); a kneeboard nets line naming a concealed cell's identity (the clandestine label broke).

### B24 — Expanded F-4E Weapons Pack: ARM Weasel fits · §71 · ☐ UNTESTED (built 2026-07-18; the (XW) selection incl. the AGM-78B preference, the editor-only HARM fit, the Shrike fallback, the editor hiding, and the 1988 era-gate tripwires are unit-tested in `tests/fourteenth/test_f4e_expanded_weapons.py` and the Red Tide no-preseed is pinned — whether DCS itself mounts and employs the injected ARMs on the Heatblur F-4E is mod/DCS-only)
- **What CI cannot exercise:** the modded jet in DCS — whether the installed mod build actually accepts the AGM-78B/AGM-88C on stations 1/3/11/13 as generated (a mod update can rename/renumber stores), whether an AI Phantom employs them against emitters (the AGM-78 is a mod-defined missile — its seeker/guidance behavior is entirely the mod's), whether the AGM-78's per-target seeker-band `target_overrides` reach the miz, and the mod-off failure mode (stores stripped at spawn).
- **Setup:** a personal NEW game (any campaign whose blue faction carries the F-4E-45MC — e.g. a personal Red Tide) with the Mods-page "Expanded F-4E Weapons Pack" box **checked by hand** (preseeded nowhere — it is the DM's personal option, never the squadron build) and DSplayer's mod installed in that DCS. Add an F-4E-45MC squadron via the air-wing dialog (none is authored) and plan it on SEAD; confirm the Payload tab defaults to "Retribution SEAD (XW)" with 4 AGM-78B Standards and offers "Retribution SEAD HARM (XW)" (4 AGM-88C) in the list; fly or spectate it against an emitting red SAM.
- **Pass:** the Phantom spawns carrying 4 AGM-78Bs (rearm screen shows them mounted), SEAD/SEAD Escort/SEAD Sweep all default to their Standard-ARM (XW) fits, swapping to the HARM (XW) fit in the editor mounts 4 AGM-88Cs, an AI-flown flight launches its ARMs at emitters, and §54 scarcity debits the same `arm` family the Hornets draw from. On an otherwise-identical game with the box UNCHECKED: the same flight defaults to "Retribution SEAD" (Shrikes) and the payload editor lists no (XW) fits.
- **Fail signature:** Phantom spawns with EMPTY ARM stations (DCS stripped the stores — mod missing on the server, or a mod update changed the pylon acceptance; re-verify against the installed mod's lua, the §41 HDS drill); an (XW) fit selected in a mod-off game (the pylon gate broke — check `Loadout.pylons_allow` and that `eject_F4E` ran via `apply_mod_settings`); the AGM-78 flying dumb/never guiding (mod-side seeker behavior or the seeker-band settings never landed — check the unit's payload `settings` in the generated miz); AI SEAD Phantoms holding fire inside range (distinct from simply not being tasked — the F-4E's SEAD task priority is a deliberate 120, so it flies SEAD on frag/overflow, not first pick).

### B25 — Carrier deck decorations: OCN 2 deck dressing · §72 · ☐ UNTESTED (built 2026-07-18; the parking-spot guard over every variant, the safe-envelope integrity, the hull gate + per-turn rotation determinism, and the three-level linked-static serialization are unit-tested in `tests/missiongenerator/test_carrier_deck_decor.py`; whether DCS renders/rides the linked statics and honors every parking spot with them present is DCS-only)
- **What CI cannot exercise:** the linked statics actually riding the steaming carrier (offsets are re-derived per frame by DCS — a wrong link would leave gear floating in the wake), DCS's parking allocator with the dressing present (does a max-density cold spawn still fill every spot), and AI recovery taxi behavior around the island-street gear (the wiki says AI clips through statics, but "slowed taxi past the Patio→El 1 zone" is a documented near-miss).
- **Setup:** any carrier campaign (Scenic Route or a fresh PG naval game). Leave `carrier_deck_decorations` ON (Mission Generation → Carrier, the default). Generate a mission with several carrier cold-start flights (client + AI — the §64 deck policy fills spots), take off, and watch the boat through a recovery cycle. For the capacity check, plan enough carrier cold starts to demand the deep spots (6+ fixed-wing).
- **Pass:** tow tractors / P-25 / forklift / deck hands visible along the island street and the 4 LSO figures on the port-aft platform, all riding the deck as the boat steams (no gear left behind in the water, none sliding); every cold-start flight spawns at a real parking spot exactly as without the feature (no "flight delayed" that a decoration-off regen doesn't also show); AI recoveries taxi and park normally; next turn the street arrangement differs (variant rotation). **FIRST FLOWN 2026-07-18 (CVN-73, 30 late-activated deck starts): two FAILs, both root-caused + fixed same day** — (1) late-activated A-6s spawned INTO the then-permanent Seahawk statics (the SC manual's "blocked spot is skipped" claim is FALSE for late activations ⇒ the permanent static-aircraft class was REMOVED outright; positions kept as learned spot anchors); (2) the corridor E-2 was struck below at ~5 min (launch traffic turning back past the boat false-tripped the astern cone ⇒ hardened: 1000 ft ceiling + closing ≥30 kt + 2-poll debounce). **Re-fly owed on the fixed build.** **The launch-cycle set** (flip `carrier_deck_decorations_aircraft` ON): an E-2C stands on the stern round-down and gear/hands dress the port junk row by the LSO platform through the launch cycle — it must SURVIVE the launch cycle (no clear while jets are merely launching/turning back past the boat) — then ALL of it VANISHES — silently, no explosion, no wreck — at the EARLIEST of: friendly fixed-wing genuinely running in low astern, ~5 min before the Airboss recovery window opens (with the default airboss plugin ON + its default +30-min window, expect the clear at ~25 min — the armed log line says "clear by 1500s (airboss recovery window)"), or the 35-min plain fallback (airboss unticked). Fly a practice CASE I: by the time you're on the initial up the wake at 800 ft the deck must already be clean; `dcs.log` shows `DECKDECOR|: <boat>: struck N launch-phase static(s) below (<why>)` + the "deck respotted for recovery" text. **No aircraft may ever spawn into ANY remaining static** (street gear/LSO/corridor set — with 30+ deck starts, zero interpenetration is the bar). **Fail signatures:** any corridor static still standing when you cross the ramp (cone + fallback both failed — check the log for `DECKDECOR|: armed`; absent = emit/plugin gate); a static exploding or leaving a wreck on destroy (would need a different removal path); the despawn yanking one mid-view while the boat maneuvers (cosmetic, note severity); the cue text spamming (once-only latch broke).
- **Fail signature:** gear floating at the mission-start anchor while the boat sails away (the linkUnit id didn't match the hull — check the route-point `linkUnit` against the carrier's `unitId` in the miz); a cold-start spawn missing/delayed vs a decoration-off control (a static ate a spot — re-measure `KNOWN_PARKING_SPOTS`, the envelope claim is broken); statics half-sunk in the deck or clipped into the island (offset frame error — check the offsets sign convention against an OCN miz); AI recovery taxi jamming against street gear it should clip through.

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

### C8 — AI helicopter terrain clearance (cruise AGL + terrain anchors + AGL air starts) · §8 · ☐ UNTESTED (built 2026-07-12 from the flown Red Tide M1 CFIT pattern; the cruise-setting return, the ≤5 NM leg subdivision with speed-locked RADIO "TERRAIN" points, the racetrack/BARO/short-leg/human exclusions, and the unit-record alt_type stamp in both air-start paths are unit-tested in `tests/ato/flightplans/test_helo_cruise_altitude.py` + `tests/missiongenerator/test_helo_terrain_anchors.py` + `tests/missiongenerator/test_airstart_unit_alt_type.py` — whether the DCS helo AI actually clears the ridges on the anchored profile is DCS-only. **First fail signature already caught + fixed 2026-07-12, same day:** the first generated Red Tide M2 hit the DCS mission-start rejection "waypoints ... has both unlocked speed and time and not surrounded by waypoints with locked time" on all three subdivided-RTB helo flights — the anchors inserted both-unlocked; they now insert speed-locked with the existing conflict resolver unlocking any anchor bracketed by TOT locks, and a full-route lock-flag sweep of a regenerated M2 shows 0 violations)
- **What CI cannot exercise:** whether an AI Mi-8/Mi-24 flying the anchored route actually clears the Harz/Sauerland ridge lines (DCS's RADIO-altitude interpolation between the 5 NM anchors), whether the extra Turning Points upset formation/escort behavior or ETA timing, and whether an air-started helo now spawns at a sane height over high-terrain FARPs.
- **Setup:** Red Tide (GermanyCW), NEW mission generation with red Air Assault fragged (Bienenfarm-class targets across the Harz are the stress case — the flown M1 killed 3 Mi-8s + 1 Mi-24 to terrain in exactly this geometry). Optionally bump `heli_combat_alt_agl` back to the 200 ft default (the flown save ran 100).
- **Pass:** the generated miz shows helo transit waypoints at the *cruise* AGL (500 ft default, not 100-200) with "TERRAIN" points every ≤5 NM on long legs, and air-start helo units carry `alt_type=RADIO`; in-game, the assault Mi-8s cross the Harz and deliver their troops (the H FRG 12-style clean run becomes the norm), no helo CFITs into ridge lines, racetrack orbits fly normally, human helo flights see no extra waypoints.
- **Fail signature:** a helo still flies a straight low line into a ridge between anchors (DCS not honoring the RADIO re-anchoring — would need tighter spacing); formation escorts breaking at the inserted points; DCS rejecting the route at start (a locked-speed/time conflict from the inserted points — they are emitted unlocked, so this would be an engine surprise); an air-started helo spawning at 500 m MSL below terrain (the unit stamp not honored).

### C9 — Carrier-recovery stagger (same-boat package landings spaced) · §8 · ☐ UNTESTED (built 2026-07-16 from the flown Scenic Route turn-3 midair — an OX S-3B and a CATERPILLAR Hornet from two different packages converged co-altitude at ~1,000 ft in the DCS overhead and collided 2.7 NM from CVN-71; the slotting math, the fixed-entry behavior for player/CAP/AEW&C/SCAR/ASAP packages, the recovery-tanker-ETA re-collection ordering, and the helo/shore exclusions are unit-tested in `tests/test_carrier_recovery_stagger.py` + `tests/test_missionscheduler.py` — whether 5-minute arrival spacing actually keeps DCS's pattern AI from converging is DCS-only)
- **Pass:** on a carrier mission with several AI packages recovering to the same boat, arrivals reach the overhead one package at a time (Tacview: no two packages' flights co-altitude within ~1 NM in the pattern); the generated ATO shows same-boat landing times ≥5 min apart for AI packages; a player package's TOT is unchanged from what the plan would otherwise assign.
- **Fail signature:** two AI packages still converging co-altitude in the overhead within a minute of each other (the DCS pattern ignores the spacing — consider widening `CARRIER_RECOVERY_INTERVAL`), or strike TOTs visibly piling up late in the mission window (over-aggressive delays on a crowded deck).

### C10 — Player CAS steerpoints mark the ground · §8 · ☐ UNTESTED (built 2026-07-16 from a user-reported flown Hornet CAS deck — "sometimes target waypoints generate in the air and are unable to be found", FLOT start/end both reading 22000. The CAS FLOT boundaries are planned at `get_combat_altitude` and stamped RADIO, i.e. ~22,000 ft **AGL** — correct for the AI, whose waypoint *is* the track, but a human's steerpoint diamond floats 22,000 ft over the terrain with nothing under it. Every other target waypoint already ships at `meters(0)`; `cas()`'s `meters(1000)` is a FLOOR so it never pulled it down, and `FlightWaypointType.CAS` has no generator dispatch entry so no generation pass touched it. The fix lifts the pre-existing client-zeroing in `PydcsWaypointBuilder.build()` out of its `if self.waypoint.flyover:` nesting onto a shared `FlightWaypoint.marks_ground_for_player`, and the kneeboard derives from the same predicate (it reads the planning model, so a generation-only fix would print 22000 against a grounded steerpoint). The predicate, the kneeboard Alt column, and the flyover non-regression are unit-tested in `tests/ato/test_flightwaypoint_ground_marked.py` + `tests/missiongenerator/test_kneeboard_cas_altitude.py` — whether the cockpit steerpoint actually lands on the deck and a pod will slave to it is DCS-only)
- **What CI cannot exercise:** whether the 0-AGL steerpoint renders on the deck in the cockpit and a TGP/weapon will actually slave to it, and whether zeroing the FLOT waypoints changes anything about how a *player* flight's route reads or flies (the AI path is untouched by construction).
- **Setup:** Any campaign with a front line; frag a **player-crewed CAS** flight (the observed case was an F/A-18C off Bandar-e-Jask). A second, **AI-crewed** CAS flight in the same mission is the control.
- **Pass:** the player flight's FLOT START/FLOT END steerpoints sit **on the terrain** — the HUD/HSI diamond marks ground you can look at, a TGP slaves to it, and the kneeboard Flight Plan prints **0** in the Alt column for those rows (not 22000). The AI CAS flight is **unchanged**: its generated waypoints still carry the combat altitude and it flies its normal track, not a dive at the dirt.
- **Fail signature:** the diamond still floats (the client zeroing didn't fire — check `client_count > 0` at generation, i.e. that the flight really is player-crewed and not a dynamic slot); the kneeboard and the cockpit **disagree** on the altitude (the two consumers drifted apart); or — the one that would matter — an **AI** CAS flight descending toward the ground over the FLOT (the predicate leaking to AI; would mean `client_count` is non-zero for an AI flight, or the layout got the split baked in after all).
- **Note:** a dynamic-slot pilot isn't a player-crewed ATO flight, so their jet won't get the grounded steerpoint — same limitation as the §58 briefing card.

### C11 — Front-less AEW&C stations forward · §8-adjacent (support orbits) · ☑ VERIFIED (2026-07-17 night fly — all three halves confirmed in the air; one follow-up observation on the support-escort attrition inside the west S-200 MEZ)
- **2026-07-17 night fly (fresh Scenic Route Merged turn 1, Tacview `Tacview-20260717-214932`,
  session `tacview-test-analysis-5bb161`): every coded half worked.** Squadron preference: the
  **E-3A flew the Khasab land station from Al Dhafra** and the **E-2C stayed 26 NM off the CVN**
  (no E-2 dragged to the land station, no idle E-3s). Placement: the blue E-3A/KC-135/S-3B stack
  orbited the **southwest gulf** (the #635 save-verified position), on the friendly side, never in
  the Jask pocket; the **red A-50 held ~86 NM behind Havadarya** (vs 424 NM from the fleet
  pre-fix) and the red IL-78 even deeper — neither red HVU was ever engaged. **Follow-up
  observation (not a C11 fail):** the SW-gulf stations sit ~100–123 NM from a west-side S-200
  site (Kish area) whose paper MEZ reaches them; the HVUs survived the whole mission (the SA-5
  preferred fighters) but **5 support-escort jets died to that site one by one** while nothing
  ever tasked SEAD/DEAD against it (its 4 Square Pair radars alive at end, 13 launches, 6–7
  kills — the mission's deadliest red asset). Whether that's an escort-orbit placement question
  or an auto-planner threat-priority question (service the S-200 whose MEZ covers friendly
  support stations) is a separate item. — 424 NM from the enemy fleet, orbiting its own rearmost base. The #613 no-front fix correctly stopped the runaway depth march (the orbit holds AT its anchor), which exposed the OTHER half: `theaterstate.aewc_targets` picked `farthest_friendly_control_point()` — the rear-safe choice that only makes sense when a front exists for the orbit geometry to work against. On a front-less theater the non-carrier AEW&C target is now `closest_friendly_control_point()` — the friendly field nearest the enemy. Fronted campaigns byte-identical; carrier targets untouched. Unit-tested in `tests/test_aewc_targets.py`; where the orbit actually ends up is DCS-only)
- **Placement half (found 2026-07-17 on the user's first look at the fixed build):** the forward anchor exposed the no-front nearest-threat-boundary bearing in `support_orbit_anchor` — from an anchor inside a big fighter zone it threads the gap BETWEEN enemy fields; the blue E-2/tanker stack was placed 27–45 NM from Bandar-e-Jask's Tomcat ramp (the flown KC-135 died to an Iranian AIM-54 in exactly that pocket). Fixed: with enemy land CPs the orbit faces the **nearest enemy CP** and stands **one buffer** behind the anchor for both sides (no 2.5× AI depth on a front-less map); the boundary bearing survives only for carrier orbits and no-enemy-land theaters. Save-verified placements: blue support southwest gulf 206/183 NM from Bandar Abbas; red A-50 78 NM behind Havadarya. Tests `tests/test_support_orbit.py`.
- **Squadron-preference half (found 2026-07-17, user nitpick on the same game):** with 2 E-2 (boat) + 2 E-3 (Al Dhafra), the plan double-tasked the E-2s (one dragged 160 NM to the land station) while both E-3s sat idle — the generic ranking measures base-to-*target* distance, and the CVN sat closer to Khasab (126 NM) than Al Dhafra did (147 NM). `PlanAewc._preferred_aewc_type` now pins basing: a **carrier** station is covered by that boat's own squadron, a **land** station by the nearest **land-based** AWACS squadron; no matching squadron with untasked jets ⇒ None (generic ranking — an all-carrier wing still covers the land station with an E-2). Save-verified: Khasab station → E-3A. Tests in `tests/test_aewc_targets.py`.
- **Setup:** a front-less campaign with a land-based AWACS on either side (Scenic Route Merged is the reference case, both sides). NEW game or a replan (aewc targets are re-derived each plan pass).
- **Pass:** the red A-50 orbits ~80 NM behind its forward field (Havadarya area), facing the strait, feeding MANTIS (`CheckLoop` climbing while it's airborne); the blue E-2/tankers orbit on the FRIENDLY side of their anchor (southwest gulf), never in the pocket between Bandar Abbas and Jask; nobody inside a threat ring.
- **Fail signature:** the AWACS still orbiting a deep-rear field 300+ NM out (the target pick not taking effect — check `front_lines()` actually yields nothing on this laydown); a support orbit parked between two enemy fields again (the enemy-CP bearing not engaging — check the theater actually has enemy land CPs); or an AWACS INSIDE a threat ring (the clearance floor failing).

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
  (no marker, not in target list) until normally discovered (strike/scout/
  TARPS); then they reveal with exact coords, permanently. AI/planner are
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
  wrong-shaped symbol). **Final cleanup DONE (2026-07-10):** `mist_4_5_126.lua` deleted after
  weeks of clean flights across campaigns — rollback is now `git checkout <pre-deletion-sha> --
  resources/plugins/base/mist_4_5_126.lua` + re-pointing `base/plugin.json`'s `"mist"`
  work-order back at it.

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

### G9 — Combat SAR AI on-demand rescue (`auto_combat_sar`) · §21 · ◐ PARTIAL (2026-07-17 flown PG "Scenic Route Merged", Tacview `Tacview-20260717-172716`, session `dcs-mission-test-040ece`: **both spawn paths fired live** — the fly-critical parked-first path WORKED (3 of the 4 Khasab ramp UH-60As started in place ~7 min after the first ejections and flew 95–113 km toward the correct survivors; the closest ended the mission 3.0 km from its survivor) and the clone fallback spawned for the later survivors ("CombatSAR Rescue 6", a real flying UH-1H). **Zero pickups completed** — not a code failure but geometry: survivors 115–140 km (land, deep Iran) and ~370 km (the fleet survivors vs the clone's rear-field spawn) from the rescue sources, so a 130 kt helo arrives as the mission ends ("after 1.4 h the rescue helos are just getting to the pilots" — the finding that drove the §21 pilot-recovery surge, G31). **Open items:** "CombatSAR Rescue 8" spawned and was removed within 1 s (a failed clone spawn — one lost rescue); NO enemy snatch party spawned all mission despite 3 land survivors (3× ~50% rolls all missing is possible but unlucky — watch it next fly; the 3 sea survivors can't draw one by construction); and the actual OPSTRANSPORT pickup+delivery loop is still unexercised because nothing ever got close enough. REWORKED 2026-07-06 — the standing orbit is retired; `auto_combat_sar` spawns an on-demand rescue **parked-first / clone-fallback** when a pilot goes down and no player CSAR package is up. The gate + parked/clone emit are unit-tested (`tests/missiongenerator/test_combat_sar_sandy_luadata.py` + `test_combat_sar_templates.py`). The old orbit's 2026-06-28 "good" verdict below is moot — NEW model)
- **What changed (2026-07-06 on-demand rework, §21):** the auto-fragged orbit (`PlanCombatSar`) is deleted; when a pilot goes down with no player CSAR/SCAR package fragged, the combatsar runtime rescues from, in order, **(1) a real rescue helo parked cold on the ramp** (`parkedHelos` — `commandeerParkedHelo` + `StartUncontrolled`; a *tracked* `UnitMap` airframe, loss recorded) or **(2) a cold clone template** (`heloTemplate`) when the ramp is bare. Both fly the OPSTRANSPORT pickup — a *parked* start replaces the retired commandeer of an *airborne* helo. **Pass:** with `auto_combat_sar` ON and NO CSAR package fragged, eject near the front → `dcs.log` cue "a rescue helo is launching from the ramp" (or "an AI rescue helo has launched" for a clone) + an OPSTRANSPORT to a friendly field + a delivered survivor spared at debrief; a killed parked rescue helo is a **recorded** loss; with a player CSAR package fragged, NO auto spawn (`autoSpawn=false`). **Fail:** the parked helo is commandeered but never starts/moves (the `StartUncontrolled` path — the fly-critical unknown; if so, make the clone primary), never reaches the survivor, or a spawn happens despite a fragged player package (the gate broke). The historical orbit-era notes below are retained for context only.
- **Gate NARROWED (2026-07-15, squadron call — the resolved "AI-rescue off" investigation):** the flown
  M1 log's `AI-rescue off` was this row's suppression gate firing on a **bare player Sandy** (`0 King(s),
  1 Sandy(s)` — a SCAR escort with no helo counts as "a player package"), which left the mission with zero
  rescue capability. The gate now counts only **rescue-capable** flights: a player CSAR **helo** suppresses
  the AI spawn; a bare Sandy/King **draws** the AI helo and escorts/tracks it
  (`tests/missiongenerator/test_combat_sar_sandy_luadata.py::test_bare_sandy_does_not_suppress_autospawn`
  / `::test_bare_king_does_not_suppress_autospawn`). The **Pass** line above updates accordingly: with a
  player *Sandy-only* plan, expect `autoSpawn=true` + the AI helo launching alongside the Sandy.
- **Generation-crash HOTFIX (2026-07-07, found on the first in-game generation attempt):** `spawn_combat_sar_templates` crashed the whole miz generation with `ValueError: 'Jolly' is not in list`. Root cause: the cold clone-template flight was built as a `COMBAT_SAR` flight, which carries the fork-custom **'Jolly'** role callsign; when the helo squadron's helipads were full the spawner fell through to the airfield path, where pydcs `_assign_callsign` can't resolve 'Jolly'. Fixed: build the template flight as a **BARCAP** (airfield-valid callsign — exactly what `_spawn_unused_for`/QRA templates use), and wrap template creation in a broad `except` so an optional rescue template can **never** break generation (it degrades to the parked-ramp helos). Regression tests in `tests/missiongenerator/test_combat_sar_templates.py`. The G9 fly can now proceed.
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
- **2026-07-06 (Inherent Resolve session `jovial-gates-574c9c`): the OTHER activation path re-verified** —
  an AI-flown King alive at t=0 activated directly via mission-start ("Combat SAR King - activated
  'Front line Balad Airbase/Tikrit Combat SAR|2|21|C-130J-30|' via mission-start (TACAN 37Y, LARS menu
  attached)"), zero errors. Both activation paths (mission-start and birth-on-player-board) have now each
  passed in a flown session; the tune-37Y + LARS-use items are still the open half of this row.
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

### G19 — TARPS on Vietnam-era recon birds (RF-101B / RA-5C) · §3 · ◐ PARTIAL (capture-side gap ROOT-CAUSED + fixed 2026-07-01 via the `airecon` plugin; the airecon runtime itself VERIFIED 2026-07-06 on the drone path — the Vietnam-bird re-fly is what's left)
- **airecon runtime VERIFIED in a flown session (2026-07-06, Inherent Resolve, session `jovial-gates-574c9c`):**
  `dcs.log` shows "AI Recon armed for 3 AI recon flight(s)" at config and then
  "AI Recon - 'Shirqat Armed Recon|80|6|MQ-9 Reaper|' captured 22 unit(s)" + "'MYNA BAI|80|2|MQ-9 Reaper|'
  captured 23 unit(s)" — zero Lua errors; the Tacview confirms the Shirqat package drone physically overflew
  the target CP at 0.4 km. The G19 capture machinery works in-game; what remains owed for this row is only
  the Vietnam-campaign fly with the RF-101B/RA-5C airframes specifically.
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

### G20b — Combat SAR snatch-party safety cap + ledger dead-reference cleanup · §15 · ☐ UNTESTED (fix 2026-07-09, root-caused from a user `dcs.log` hang)
- **Root cause:** a heavy Red Tide (Germany Cold War) mission **hung** ~13 min in — the log stopped
  mid-flood of MOOSE `UNIT.GetVec3` / `GROUP.GetCoordinate` errors with **no crash dump** (a
  scripting/sim-thread hang, not a CTD; the 20-core/130 GB rig was never the limit). The capture race
  had spawned **80 infantry** (8 parties × 10) across two ejections because a **saved plugin-option
  override** (~40/4) was in force vs the 5/3 default — the dominant dynamic spawn on top of
  MANTIS-over-62-groups + TIC/GLSCO + SplashDamage + airbase harassment + TARS.
- **Fix (CI-tested):** `capturePartySize`/`captureTeams` **hard-clamped at load** (≤ 12 / ≤ 4, warned
  once) so no config can pile enough units on to freeze the sim; the survivor ledger **prunes dead
  teams** out of `entry.party` each cycle + reads positions via `firstAliveCoord` (never
  `GetCoordinate` on a dead lead unit) + **reaps a ground-killed pilot** via the designed-but-unused
  `dead` state — together ending the dead-object poll flood. Behavioral cap test:
  `tests/lua/test_combatsar_capture_cap.py` (runs the real plugin under Lua 5.1).
- **Pass:** on a heavy Red Tide game with the capture race on, several ejections over a long mission do
  **not** bog/hang; `dcs.log` shows a one-time `combatsar: capture party clamped …` line if a saved
  override exceeds the cap, and **no** sustained `GetVec3`/`GetCoordinate` flood after snatch
  teams/survivors die.
- **Fail signature:** the `GetVec3`/`GetCoordinate` flood returns (a poll path still reads a dead
  object), or the mission still hangs with the capture race on (another unbounded spawn/scheduler —
  count dynamic units in `dcs.log`).

### G21 — Combat SAR AI rescue commandeers an on-station helo (no duplicate spawn) · §21 · ✗ SUPERSEDED by the 2026-07-06 on-demand rework — the commandeer path (and the standing orbit it commandeered from) is RETIRED. The bug this row tracked (a commandeered airborne helo RTBs instead of rescuing) is designed out: the runtime now clones a cold template *into* the mission (the path that always worked). Re-verify as G9. Kept for history.
- **2026-07-06 flown Inherent Resolve session (`jovial-gates-574c9c`, dcs.log + Tacview trace):** two
  ejections (CROW Su-25 t≈1096, JELLYFISH M-2000C t≈3009), zero `combatsar:` errors. **The preference
  finally showed itself:** ejection #1 produced **no clone** (the planned
  `Front line Balad Airbase/Tikrit Combat SAR|2|20|UH-60A|` was alive and idle → commandeered), and only
  ejection #2 — with the planned helo now committed — spawned `CombatSAR Rescue 3#001` (which air-spawned
  at the planned helo's FLOT-station template anchor). That is exactly the designed commandeer-first /
  clone-on-busy order. **But the commandeered helo never executed the rescue:** it kept its planned
  racetrack for ~11 min after dispatch, then transited to **Balad** (its `SetHomebase`) and loitered there
  to file end — distance to its survivor 97→140 km, never closing. Best read of
  `dispatchAIRescue`: `FLIGHTGROUP:New` over an **airborne, already-routed** group + `AddOpsTransport`
  doesn't preempt the group's current route — it finishes/abandons the racetrack and goes to the homebase
  instead of the pickup zone (the fresh-clone path, AICSAR's proven shape, activates into the transport
  mission directly, which is why clones historically worked). **Next step is a code decision, not a
  re-fly:** either cancel/clear the commandeered group's current mission-queue before `AddOpsTransport`
  (MOOSE-risky, needs a fly), or drop the commandeer and always clone (reverses this row's design intent
  but uses the only proven path). The survivor stand-in rendering as a **2B11 mortar** (the INFANTRY-class
  pick on OIR) was also caught here and fixed same day (`LuaGenerator.survivor_unit_type`).
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

### G23 — Sandy AI dynamic retasking toward a live ejection · §15 · ✗ REGRESSED → rework applied 2026-07-02 (root-caused; needs a re-fly). **FROZEN, pass-or-delete (2026-07-03 CSAR rescope):** this re-fly is the divert's last chance — pass and it stays as-is (frozen, no further iteration); fail and the divert is deleted rather than reworked a third time (a player Sandy is untouched either way). **NOTE (2026-07-06 on-demand rework):** with the standing orbit retired, this divert now only applies to an **AI-crewed Sandy inside a PLAYER-fragged package** (there is no AI-spawned Sandy in v1 — that's the §21 v2). So it's only exercisable when the player frags a package with an AI Sandy seat. **SCOPE CLARIFIED (2026-07-15, squadron call): this is a SINGLE-PLAYER feature** — the AI-crewed-Sandy-in-a-player-package configuration is exactly how a solo player runs CSAR (they fly one seat, the AI flies the Sandy); the 414th's own events are MP DM-style (the user builds, the squadron crews the seats), so an MP event was never this row's natural arbiter. The pass-or-delete rule stands, but the arbiter is an **SP re-fly** whenever one happens — do NOT delete it for lack of MP-event exercise.
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
- **Road-pinned IED variant (2026-07-05, user call — "we know what highway it's on but not which street"):** a roadside IED/VBIED's circle no longer jitters radially (which could park it out in the fields off the road) — the centre slides **far ALONG its supply road** (5–25 km on the polyline, deterministic, clamped to the road; `TheaterGroundObject.concealed_route`, set at plant). Deliberately, the device may sit **outside** the drawn circle — the highway itself is the search domain. **Pass (adds to the P4 sweep):** an IED circle sits ON the road, well away from the device; sweeping/TARPS-ing along that road finds it. **Fail:** an IED circle centred off-road in open ground (route not stored / slide broken), or the circle on a *different* road than the intel message names.
- **Blank-map regression FIXED same day (2026-07-05, user report on the `iraq.retribution` save):** with fog on, the whole map (bar the base layer) failed to draw; fog-reveal drew fine. Root cause: the jitter rebuilt the offset point via `pos.__class__(x, y, terrain)`, but a real TGO's position is a **`PresetLocation`** (`(name, position, heading)` constructor), so every concealed TGO raised and one exception 500'd the whole `/game` payload (reveal bypassed the jitter via `known_for`, which is why fog-off worked). Fix: build a plain `dcs.mapping.Point`; a regression test pins the real `PresetLocation` type; headless-verified on the user's save (97/97 TGOs serialize, 60 circles).
- **What it is:** with `concealed_enemy_forces` on (default ON, new campaigns), an **un-scouted** enemy
  field force — a mobile SAM site (MERAD/SHORAD/AAA), a deployed vehicle group, a missile site — shows
  as a dashed **amber** **"suspected enemy activity" circle** (4 km; 3 km for vehicle groups — amber
  since the §28 UI audit; a dashed **red** circle now exclusively means an ROE off-limits zone) whose centre is
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

### G25 — Armed Recon package: recon drone + SEAD Viper escort + 4-ship sweep · §3 · ◐ PARTIAL (drone-in-package + TARPS-vs-CP + the convoy hunt VERIFIED in a 2026-07-06 flown session; the auto-planner 4-ship + SEAD-escort composition and the post-standoff AI hunt still owed)
- **Flown evidence (2026-07-06, Inherent Resolve turn 1, session `jovial-gates-574c9c`, Tacview + dcs.log):**
  the player's "Shirqat Armed Recon" package (player F/A-18C 2-ship + MQ-9 Reaper) worked end-to-end — the
  TARPS-vs-CP drone flew, overflew the target CP at 0.4 km, and banked a 22-unit `airecon` capture (G19); the
  §50 red convoy (10 gun trucks) departed the FOB down the corridor and the flight found and destroyed all 10
  (Mavericks + a gun pass); no generation errors. NOT yet shown: the auto-planner's fixed 4-ship primary + the
  threat-gated 2-ship SEAD Viper escort composition in a planned (non-player-built) package.
- **Same session's finding → fix to re-verify:** the ARMED RECON fly-over waypoint sat **dead-centre on the
  Shirqat FOB** (SA-13/ZU-23 garrison) — the player had to improvise a ~4 km offset and standoff Mavericks.
  Fixed 2026-07-06: `Builder._stand_off_search_point` pulls the point back along the ingress bearing (target's
  longest threat ring + 2 NM, floor 5 NM, capped at the engage-zone radius / ingress distance); the hunt zone
  re-centres on the moved point. **Next fly:** confirm the steerpoint sits off the FOB and the AI flight still
  finds/engages the corridor traffic from the offset point.
- **What it is:** each auto-planned Armed Recon package now composes as **1 recon drone + 2 SEAD Vipers + 4 armed recon** on a UAV-fielding faction (OIR). The primary is a fixed 4-ship; the SEAD escort (`propose_common_escorts`, 2-ship, threat-gated) resolves to the F-16CM; and the auto-recon hook (`auto_add_tarps_recon`, default ON) frags one TARPS flight — which on OIR is a Predator/Reaper, since the drones are the faction's TARPS birds. The drone is optional (drops if none free, never scrubs the package) and the SEAD is pruned when no radar-SAM threat sits on the route.
- **Setup:** NEW "Iraq - Operation Inherent Resolve (COIN)" (has the drones + the SA-6/8 crust + Viper SEAD). Let the auto-planner build a turn; open an Armed Recon package in the ATO.
- **Pass:** an Armed Recon package shows a 4-ship recon primary + a 1-ship drone (Predator/Reaper) recon flight; where a radar SAM threatens the route, 2 F-16CM SEAD ride too; the drone overflies the swept corridor (TARPS-against-a-CP flies, no `InvalidObjectiveLocation`) and its overflight confirms BDA on the area next turn; a package with no TARPS bird free still plans (drone just omitted).
- **Fail signature:** the drone never appears (`auto_add_tarps_recon` off, or no TARPS-capable squadron — the drones need their `TARPS: 700` from the #491 unit data); the package errors on generation with `InvalidObjectiveLocation` (the TARPS-vs-CP widening didn't take); armed recon plans a 2/3-ship instead of 4; the drone flies TARPS but never reaches the corridor (range/TOT — the drone cruise is slow, check the +2 min offset holds it under the escort window).

### G26 — Packaged drone is a lasing JTAC (autolase + smoke for the shooters) · §3 · ☐ UNTESTED (built 2026-07-05, 414th call; the qualification gate + laser-code choice are unit-tested in `tests/missiongenerator/test_drone_jtac.py` — the actual runtime lasing needs a fly)
- **What it is:** an AI-flown flight of the faction's `jtac_unit` (the MQ-9/Predator) in an A/G package (Armed Recon / CAS / BAI / Strike) is emitted as a `JtacInfo` → `dcsRetribution.JTACs` → CTLD `JTACAutoLase` (autolase + smoke default ON). So the packaged drone lazes + smoke-marks ground targets for the shooters and shows on the kneeboard/radio like a JTAC — replacing the retired FLOT auto-JTAC glued to the front line. Blue + AI only; a real asset (not invisible/immortal).
- **Setup:** NEW "Iraq - Operation Inherent Resolve (COIN)" (OIR fields the MQ-9/Predator + CTLD is on). Let the planner build a turn with an Armed Recon (or CAS/BAI/Strike) package that includes a drone; fly it and watch the drone over the target area.
- **Pass:** the drone appears on the kneeboard JTAC card with a laser code + radio; in-mission it autolases ground targets in the package's target area and drops smoke on them; the AI shooters (or you) can attack the lased/marked targets; the drone is killable (not immortal). A JTAC radio menu is present (CTLD).
- **Fail signature:** no JTAC on the kneeboard (the `JtacInfo` didn't emit — check the flight is the faction's `jtac_unit`, AI, blue, in an A/G package; or CTLD autolase is off); the drone never lases (CTLD `autolase` option off, or the moving/overflying drone never dwells near a target long enough — this is the **loiter question**: if a single overflight can't sustain a useful lase, the drone needs an orbit/loiter profile over the target); every drone lases even in non-A/G packages (the `_JTAC_PACKAGE_PRIMARIES` gate broke); a red or player drone lases (the blue/AI gate broke).

### G27 — Auto-fielded JTAC drone squadron on a non-drone campaign · §3 · ☐ UNTESTED (built 2026-07-05, 414th call; the gate + rear-base pick are unit-tested in `tests/fourteenth/test_jtac_drone.py`, the gate is verified to qualify real modern factions — the fielded-and-fragged loop needs a fly)
- **What it is:** at New Game, a blue side whose faction declares a drone `jtac_unit` (MQ-9/Predator) and doesn't already field one gets a small (2-ship) TARPS-tasked drone squadron auto-added at its rear-most airfield, so the drone-JTAC (G26) works on the ~55 campaigns that never listed a drone. Gated by `auto_jtac_drone` (default ON); skips campaigns that hand-place drones (OIR untouched); blue-only; **era-gated** (a 1988 campaign like Red Tide never gets a Reaper — service-year floor).
- **Setup:** NEW game on a **modern** campaign that does **not** list an MQ-9 squadron (any modern Western blufor campaign — e.g. a Persian Gulf / Syria / Caucasus modern scenario). Check the blue ATO/air wing.
- **Pass:** a 2-ship MQ-9 Reaper (or Predator) squadron exists at a rear blue airfield that didn't have one in the campaign yaml; the auto-planner frags it into an A/G package (TARPS/overwatch), it reaches the target area, lases (G26), and films (drone-always-films). On OIR (already fields drones) **no second** drone squadron is auto-added. Turning `auto_jtac_drone` off yields the campaign's authored air wing exactly.
- **Fail signature:** no drone squadron appears (gate: `has_jtac`/`jtac_unit` a drone/TARPS-capable, setting on, campaign year ≥ the drone's service year — check the faction JSON + start date); a **second** drone squadron on a campaign that already fields one (the existing-drone skip broke); the drone based at the front line or an inoperable field (rear/`can_operate` pick broke); a red drone squadron auto-fielded (blue-only gate broke); **an anachronistic MQ-9 on a Cold-War campaign** (the era gate broke — Red Tide 1988 must stay drone-free); the drone sits idle and never frags (no A/G packages that turn, or the auto-recon hook off — `auto_add_tarps_recon`).

### G28 — POW mechanics: captured pilot benched, held, surfaced, brought home · §21 · ☐ UNTESTED (built 2026-07-06; the POW status transitions, will-aware indefinite hold, invulnerable-player-respecting write-off, Homecoming, SITREP lines, and the §51 compromise expiry are unit-tested in `tests/test_pow_recovery.py` + `tests/squadrons/test_squadron_pilots.py` + `tests/test_sitrep.py` + `tests/missiongenerator/test_commsjamluadata.py` — the multi-turn campaign feel + the roster/SITREP read need a played campaign)
- **What CI cannot exercise:** whether a captured pilot genuinely disappears from the schedulable roster next turn and reads as "POW" in the squadron dialog; whether the SITREP band names the POW + holding field + clock each turn; whether recapturing the holding field returns the pilot; on a will campaign, whether the indefinite hold keeps draining will (never auto-killing) and whether a negotiated win brings the POWs home; and whether an invulnerable-player POW is returned rather than killed at a normal-campaign clock expiry.
- **Setup:** lose the Combat SAR race (eject + get captured) on **(a)** a normal campaign (4-turn clock) and **(b)** a Vietnam will campaign (`vietnam_political_will` on, indefinite hold). Note the pilot name. Advance turns watching the squadron roster + the next mission's kneeboard SITREP band; recapture the holding field in one run and ride the clock/war-end in another. **Fast test (thumb on the scale):** tick `[TEST] Combat SAR: force every downed pilot to be captured` (Campaign Management → HQ Automation) so you don't have to lose the race by chance — any ejection near the front becomes a POW in seconds.
- **Pass:** the captured pilot shows **POW** in the squadron dialog and is never fragged while captive; the SITREP band carries a "POW: <name> — held at <field> (N turns left / held)" line each turn; recapturing the holding field returns the pilot to Active (and clears the line); on a normal campaign the pilot is written off at the 4-turn clock (or, with invulnerable player pilots on, a *player* POW returns instead of dying); on a will campaign the POW is held indefinitely (will keeps bleeding, no death) and a **negotiated win repatriates every POW** (Homecoming) while a withdrawal loss writes them off; §51 jamming from a held POW stops after ~4 turns even if the POW is still held.
- **Fail signature:** the captured pilot flies again next turn (status not flipped / `active_pilots` still includes POWs); no POW line in the SITREP (the `pows_held` wiring); recapturing the field doesn't free them (`repatriate` / holding-cp match); a player POW killed at clock expiry despite invulnerable-player-pilots (the `_write_off` gate); a will-campaign POW killed at 4 turns (the indefinite branch); no Homecoming on a won will campaign (the `process_win_loss` hook); §51 jams forever off an indefinitely-held POW (the `COMMS_COMPROMISE_TURNS` window / `captured_turn` stamp).

### G29 — Persistent evaders + the always-run snatch race · §21 · ◐ PARTIAL (2026-07-11 flown Red Tide M1 `csar-snatch-toggle-question-dfdb7a`: the always-run half is proven live — the no-asset path armed instead of bailing (`Combat SAR - blue has no rescue asset this mission; capture race only` → `survivor ledger started (1 coalition(s), 0 King(s), 1 Sandy(s), capture on, AI-rescue off)`; the old "skipping" line is gone) and `combat_sar_survivors` WAS written (1 unresolved entry at exit; ~20 other ejections were resolved in-mission as their pilot units despawned). **Caveat found:** the one surviving entry was a **DCS dynamic-slot** jet — a player self-spawned a MiG-29A at blue Frankfurt (`dynamic_slots` was ON at generation; DCS names these `<Airbase>_<type>_<n>`) and ramp-ejected to leave (Tacview shows no shoot-down, the jet removed 723 m from its spawn AT the field). `record_downed_pilots` discards it correctly (`unit_map.flight() is None` → "not an airframe this campaign tracks"), so no phantom MIA — but note a dynamic-slot pilot can never go MIA/POW by design. The MIA flip → SITREP/roster → next-mission evader respawn arc still needs a real tracked-airframe shoot-down. Built 2026-07-10, squadron call; the always-emit node, the no-rescue-capability ledger start, the eject → `combat_sar_survivors` sync → snatch spawn, the evader respawn, the MIA record/retire, the depth-weighted turn roll, and the SITREP/roster surfaces are unit-tested in `tests/lua/test_combatsar_ledger.py` + `tests/fourteenth/test_downed_pilots.py` + `tests/test_combat_sar_scoring.py` + `tests/missiongenerator/test_combat_sar_sandy_luadata.py` — the in-DCS snatch spawn without any rescue asset, the evader respawn feel, and the multi-turn evade/capture arc need a fly)
- **2026-07-17 night fly (fresh Scenic Route Merged turn 1, Tacview `Tacview-20260717-214932`,
  session `tacview-test-analysis-5bb161`): the at-scale live run — MIA banking + ledger hygiene
  VERIFIED, and a NEW finding: the snatch race resolves by infantry ballistics, never by the
  capture clock.** 10 survivor groups spawned across the mission's ejections; 12 CSAR Snatch
  Parties spawned (the ~50% roll firing repeatedly); state.json flushed clean with
  `combat_sar_survivors: 8` — the persistent-evader mirror banked every unresolved pilot,
  **including the player's own** (Flash, killed by the CHICKEN SA-17 TELAR at t=3625, evader at
  the death point deep in Iran) — and the two resolved survivors were correctly dropped (10−2=8,
  no leak). **But `combat_sar_captures` = 0 across 12 parties:** the capture dwell never
  completed because DCS infantry gunfights pre-empt it both ways — the **M249-armed survivor
  outguns the AK teams** (parties 1–3 all died 276–677 m into their 1.4 km march on Survivor 5,
  who is alive in the MIA ledger; blue air working the same area may have helped), and when
  teams DID close, **the survivor was shot dead instead of captured** (Survivors 9 + 15 killed
  on the ground → the `dead`-state reap, which worked). **FIX BUILT next session (unflown):**
  `setNonCombatant` in the plugin now spawns both the survivor group and every snatch team
  **ROE weapons-hold + alarm-green** (the survivor via the MOOSE spawn's real `#001` group
  name), so the capture clock + airpower against the party decide the race, never small arms;
  garrison units near the ejection still kill evaders by design. Pinned in
  `tests/lua/test_combatsar_ledger.py::test_survivor_and_snatch_teams_spawn_weapons_hold`;
  design note §"Non-combatant capture race" in `414th-csar-notes.md`. **Re-fly pass:** a
  snatch team closes under fire without stopping to shoot, the survivor never fires, a
  completed dwell yields "CAPTURED … now a POW" + a `combat_sar_captures` entry. **Fail
  signature:** a survivor still mowing down teams (the `#001` name resolution missed — check
  dcs.log for the spawn alias) or a team shooting the survivor dead at contact (ROE not
  applied to `mist.dynAdd` spawns). Zero rescues again (all 10 on-demand clones spawned at Al Dhafra,
  115–300+ km from the survivors; closest approach 2.8 km at mission end) — exactly the transit
  problem G31 exists for, and this save is now the ready-made G31 test.
- **What it is:** the survivor ledger runs whenever the CombatSAR node exists — **no rescue capability no longer skips the plugin** (the flown 2026-07-10 gap: auto-CSAR off + Sandy-only package = no snatch AI, comms jam never armed). An un-rescued, un-captured pilot goes **MIA** (`combat_sar_persistent_pilots`, default ON): re-spawns at his position next mission (fresh smoke + snatch race, "EVADER" cue), walks home if on friendly ground at turn end, else rolls a **depth-weighted capture** each turn (10% near the front → 90% at 40 NM deep; no death clock). Capture = the normal POW chain (G28 + S4).
- **Setup:** auto-CSAR **off**, no CSAR/SCAR flights fragged, `[TEST] force capture` **on**; get a blue pilot down near the front. Then a second run with force-capture **off**: leave the survivor unresolved, end the mission, advance the turn, and generate the next mission.
- **Pass:** run 1 — the snatch party spawns and captures despite zero rescue assets (dcs.log shows "capture race only", the MAYDAY reads "no rescue assets available"), the POW + comms jam fire. Run 2 — the debrief spares the pilot (roster shows **MIA**, SITREP shows "MIA: <name> — evading near <CP> (downed this turn)"), the next mission re-spawns the survivor at the same spot with red smoke + the EVADER message, and the on-demand AI rescue (if re-enabled) or a player package can still recover him; a deep evader left alone converts to POW within a turn or two (message "Evader captured"), a near-front one keeps evading.
- **Fail signature:** dcs.log still shows "no rescue helos/template; skipping" (the old bail; stale plugin) or "dcsRetribution.CombatSAR not present" (the emitter early-return resurfaced); no snatch with force-capture on (G20 regression); the un-rescued pilot dies at debrief with the toggle on (the `_combat_sar_mia_unit_ids` sparing / `combat_sar_survivors` state never written — check state.json); no re-spawn next mission (`persistentSurvivors` missing from the miz's CombatSAR node); the same evader duplicated in the ledger (turn_downed reset); an evader stranded MIA forever after toggling the setting off mid-campaign (the always-resolve contract broke); a capture roll that never fires even 40 NM deep (`resolve_downed_pilots` not hooked in `finish_turn`).

### G30 — MANTIS SHORAD link: the point defense ambushes the HARM shot · MANTIS migration · ☐ UNTESTED (built 2026-07-12 off the "which MANTIS features aren't we using?" audit; the bridge plumbing — PD-name collection/dedupe from the per-SAM `PD` arrays, Lua-pattern prefix escaping, one SHORAD per coalition defending `mantis.SAM_Group`, `autoshorad=false` captured AT `Start()` time, option threading, and the off/no-PD no-ops — is harness-tested in `tests/lua/test_mantis_shorad_link.py` with recording MANTIS/SHORAD fakes. The fake models no DCS AI: the actual sleep/wake and the intercept are DCS-only.)
- **What it is:** each SAM site's co-located PD escorts (the "… (PD)" Tor/Tunguska/Avenger groups) are now wrapped in a MOOSE SHORAD object linked to MANTIS (`shoradLink` plugin option, default ON). The PD **sleeps** (alarm green / dark) until a **HARM or Maverick launch** against a defended SAM — or a MANTIS SEAD suppression within ~13.5 NM — **wakes it for 600 s** to engage the incoming shot while the big radar hides, then it goes back to sleep. OFF restores the old always-alert PD.
- **What CI cannot exercise:** whether the woken Tor/Tunguska actually shoots down the inbound HARM (the whole point), whether the sleeping PD is genuinely dark on ingress (no radar emission before the wake), whether it re-sleeps after the wake window, and that the PD still records kills/losses natively.
- **Setup:** any MANTIS campaign with PD-escorted SAMs. **Red Tide is the testbed since 2026-07-12:** the fork faction gained the **SA-15 Tor + SA-19 Tunguska** (era-correct '86/'82; user call off the roster audit — before that red's SHORAD was IR-only SA-9/13 + the Osa, none of which DCS tasks against missiles, so G30 would have been a red no-op; guarded in `tests/fourteenth/test_red_tide_faction_era.py`). Gen-probed: the S-300 regiment battalions draw Tor PD. NEW game required for the Tor (faction is generation-time); the SHORAD link itself is runtime-only. Check dcs.log for `SHORAD link armed: N point-defense group(s)`. Ingress on a site with an RWR: confirm no Tor emission while inbound (IR PD like SA-9/13 has no RWR signature — judge those by fire discipline, not emissions). Fire a HARM at the site from inside ~10 NM; watch the PD.
- **Pass:** the arm line shows a plausible PD count; the PD is silent on ingress (no SA-15 RWR nails before any shot); on the HARM launch the PD wakes (RWR lights up) and engages the missile — a HARM intercepted mid-flight is the marquee proof; after ~10 min without triggers the PD goes quiet again; a killed PD unit shows in the debrief like any other loss.
- **Fail signature:** `SHORAD link armed: 0` on a PD-rich campaign (the PD arrays stopped being emitted, or the prefix escaping broke — same class as the G6 zero-resolve bug); the PD radiates/engages strikers all mission with the link ON (autoshorad overwrite — the MOOSE Start() ordering broke); the PD never wakes on a HARM shot (SHORAD's shot watch not seeing the launch — check DefendHarms and the weapon name patterns); a SAM's OWN radar staying dark after its PD woke is fine (separate systems), but the PD staying asleep while its SAM dies to the HARM is the feature failing at its one job.

### G31 — Pilot recovery surge (next-turn "drop everything" rescue package) · §21 · ☐ UNTESTED (built 2026-07-17 off the flown Scenic Route Merged finding "after 1.4 h the rescue helos are just getting to the pilots" — same-mission rescue can't beat helo transit time, so the NEXT turn opens with the recovery op already airborne. `plan_pilot_recovery_surge` (`game/fourteenth/csar_surge.py`, hooked in `Coalition.plan_missions` BEFORE the commander) frags one coordinated package at a `PilotRecoveryZone` centred on the MIA evaders: required Jolly rescue helo + optional second Jolly / King C-130 / 2-ship Sandy SCAR / A2A escort, ASAP TOT, `ignore_range` — and the existing `PackageBuilder` rule air-starts AI COMBAT_SAR flights, so the op is on station at mission start. **Gate:** once per downed pilot (`DownedPilot.surge_turn` stamp); gated `combat_sar_surge` (default ON, requires `combat_sar_persistent_pilots`). Guards/gate/composition unit-tested in `tests/fourteenth/test_csar_surge.py`; the fulfiller build, the air-start position, and the runtime pickup are DCS-only.)
- **What CI cannot exercise:** whether the air-started Jolly actually spawns near its recovery hold (not at the departure field), whether the combatsar ledger dispatches the PACKAGE helo onto the re-spawned evader (`persistentSurvivors`) promptly, whether the pickup + delivery complete inside a normal mission, and whether the surge package suppresses the on-demand clone (`autoSpawn=false` when the surge helo is fragged).
- **READY-MADE TEST STATE (2026-07-17 night fly, session `tacview-test-analysis-5bb161`):** the
  fresh Scenic Route Merged turn-1 mission ended with **8 MIA evaders banked** in state.json —
  including the **player's own pilot** (Flash, down ~40 NM deep near the CHICKEN site → the
  depth-weighted roll runs ~90% capture, racing the surge) and **5 evaders over west-gulf
  water** (watch how `resolve_downed_pilots`' walks-home/depth roll treats water positions on a
  front-less theater). Process that turn and the next mission is the G31 exercise: expect ONE
  Recovery package air-started at the evader cluster, `surge_turn` stamps preventing re-surges,
  and the on-demand clone suppressed by the package helo.
- **Setup:** any campaign with a rescue-helo squadron; get a blue pilot down behind the lines (easiest: `combat_sar_test_easy_rescue` off + fly a jet into a SAM), end the mission un-rescued (pilot goes MIA), advance the turn. The ATO should show a "Recovery: <pilot>" package; the campaign log the "Pilot recovery surge" message.
- **Pass:** next mission opens with the Jolly airborne near the evader, the evader re-spawns (~30 s), the helo is dispatched onto them within minutes, pickup + delivery complete, the pilot returns to the roster at debrief, and no second surge is fragged on later turns for the same evader.
- **Fail signature:** the surge package exists but the helo spawns at its field and transits (air-start not applying — check `required_aircraft_start_type` on the departure), the helo orbits its hold and never dives to the survivor (the ledger not adopting package helos for persistent survivors), or a surge re-frags every turn for the same pilot (the `surge_turn` stamp not persisting).

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

### H6 — Mission code words + Comms & Brevity card · §4 · ☑ VERIFIED (2026-06-26, user in-game pass) — **surface superseded 2026-07-13**: the Comms & Brevity card + brevity crib are deleted in the back-to-upstream rework; the code words live in the Mission Info BLUF + a Support Info block (re-check under H12). The planner panel/tooltip/JOIN-tag checks below remain valid.
- **Setup:** Enable **Package code words** (Mission Generator → Kneeboard) on
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

### H7 — Fuel ladder kneeboard card · §4 · ☑ VERIFIED (2026-06-26, user in-game pass) — **surface superseded 2026-07-05**: the standalone page + `generate_fuel_ladder_kneeboard` are deleted; the ladder rides in the flight plan as a `Fuel` column + RTB-margin line (re-check under H12)
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

### H8 — Kneeboard de-duplication · §4 · ☑ VERIFIED (2026-06-26, user in-game pass) — the Min-fuel-column half is obsolete since 2026-07-05 (the flight plan always carries the folded `Fuel` column; there is no Fuel Ladder page to de-dup against)
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

### H9 — Compact 3-4 page kneeboard deck · §4 · ⊘ RETIRED (2026-07-05, back-to-basics rework; was ☑ VERIFIED 2026-06-26)
- **What happened:** the compact folding machinery (`compact_kneeboard`, the composite
  P2/P3/flex pages, `_draw_section_if_fits`) was deleted in the kneeboard back-to-basics rework.
  The 2026-07-13 back-to-upstream rework then retired the Brief Sheet + cover page too (§30/§31);
  the colour palette and the threat-intel cards (default ON) survive on the upstream-shaped deck.
  The current deck shape is checked under **H12**.

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
- **Gated 2026-07-12 (`civilian_air_traffic`, Mission Generation → Battlefield life, default ON —
  every campaign byte-identical):** the flown M1 found the ~40 NM front keep-out is no protection
  for a campaign whose air war runs 100+ NM behind the lines — a neutral IL-76 at FL230 transited
  the deep BVR corridor and died to a player's double Phoenix (an airliner profile is
  indistinguishable from a military transport on an AWG-9), and 5 more civs self-crashed into the
  session logs. A campaign wanting a sterile picture can preseed it off. **Red Tide briefly
  preseeded OFF (#580) then reversed same-day by squadron call — Red Tide KEEPS its civilians**
  (the ambient life is worth the occasional Aeroflot incident; BVR discrimination past the FLOT is
  on the shooter); guard `test_red_tide_keeps_civilian_air_traffic`.
- **Setup:** Generate any campaign mission (civilian traffic defaults on) and fly/observe the rear
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
- **Reworked 2026-07-15 (no re-fly needed):** the data moved into each aircraft's own yaml
  (`date_gated_properties` → `AircraftType.property_date_gate`) and the gate now rides its **own
  `restrict_props_by_date` toggle** instead of the weapons one; the clamp path is unchanged and
  fully re-unit-tested (registry gates exactly the four `HelmetMountedDevice` airframes + a pydcs
  label pin). SURA Visor was dropped (mod-only airframe); the A-10C II HMCS (2012) and MiG-29 HMS
  (1983) gates are new data. When re-flying anything here, use the NEW setting.
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

### H10 — Shared-airframe kneeboard index · §27 · ☐ UNTESTED (standalone page again since the 2026-07-13 back-to-upstream rework; condition not met in the 2026-06-28 pass)
- **Not exercised (2026-06-28, audience pass — user confirmed the condition wasn't set up):** the mission did **not** have 2+ client flights of the same airframe, so the index had nothing to render — no observation either way, **not** a fail.
- **Surface history:** briefly a section on the §30 cover page; the 2026-07-13 back-to-upstream
  rework retired the cover and the index is a **standalone conditional page** again
  (`KneeboardIndexPage`, only when 2+ client flights share the airframe). Page-math + lone-flight
  no-index regression in `tests/missiongenerator/test_kneeboard_index.py`.
- **Headless adjudication (2026-06-26, re-valid 2026-07-13):** the tests cover the
  start-page math (index is page 1, blocks start at 2 and advance by block size), callsign grouping +
  sort, and the index page render. **Residual (in-sim only):** the index actually appears in-cockpit
  and its page numbers line up with the stacked deck DCS builds.
- **Setup:** Frag **2+ client flights of the same airframe** (e.g. two F/A-18 flights) in a mission;
  generate and open the kneeboard. Also frag a single flight of another type as the control.
- **Pass:** page 1 of the shared airframe is an index listing each flight's callsign / task / start
  page; flipping to a listed page lands on that flight's deck; the single-flight type has **no** index.
- **Fail signature:** no index when 2+ share a type; wrong start pages; an index wrongly added for a
  lone flight; flights out of the listed order.

### H11 — Estimated fuel figures for dataless airframes · §4 · ☐ UNTESTED (estimate sanity-banded in `tests/dcs/test_estimated_fuel_consumption.py`, 2026-06-27; the surface moved 2026-07-05 — the figures now render in the flight plan's `Fuel` column on Mission Info, not a Fuel Ladder page)
- **Deferred (2026-06-28, user: "update after kneeboard update"):** revisit once the pending kneeboard changes land — re-check the C-130J King / helo Fuel Ladder against the current deck so the estimate is validated against the updated kneeboard rather than the old one.
- **What it is:** `AircraftType.estimated_fuel_consumption` synthesises a rough `FuelConsumption` from
  the airframe's `fuel_max` (bucketed helicopter / heavy-transport / combat) so the Fuel Ladder card
  renders for airframes with **no** hand-measured `fuel:` block — the **C-130J "King"**, helicopters,
  warbirds, etc. Kneeboard-scoped: planner tanker tasking + in-flight sim are untouched.
- **Setup:** frag a player flight in an airframe with no measured fuel data — ideally the
  **C-130J King** (the reported case) and a helicopter — and open the Mission Info kneeboard page.
  Cross-check against an airframe that *does* have measured data (e.g. F/A-18C).
- **Pass:** the King / helo flight plan's **`Fuel` column renders a descending ladder** with the RTB
  margin call-out under the table, instead of all-blank cells. Numbers are plausible planning
  figures (the King cruises ~16 lb/NM, full ~43k lb, so it should *not* read negative-margin on a
  normal sortie). Measured-data airframes are unchanged.
- **Fail signature:** an all-`-`/blank Fuel column for the King/helo (no planned figures —
  `flight.fuel` missing or the estimate not engaging); wildly implausible numbers (e.g. the King
  reading ~80 lb/NM, a sign the heavy bucket isn't being picked — check `_is_heavy_airframe`); any
  change to a measured-data airframe's figures (the estimate must never override a real `fuel:`
  block); planner suddenly fragging tankers for the King (the fallback must stay out of
  `unit_type.fuel_consumption`).

### H12 — Back-to-upstream kneeboard deck (upstream pages + folded 414th info) · §31 / §30 · ☐ UNTESTED (reworked 2026-07-13; the 2026-07-05 back-to-basics render pass covered the now-retired cover/Brief-Sheet deck)
- **What it is:** the 2026-07-13 back-to-upstream rework (user markup pass on a flown Scenic Route Merged
  deck) — the cover page, Brief Sheet and Comms & Brevity card are **deleted**; the deck is
  upstream's page set with the kept 414th info folded in. Per flight: **Mission Info** (BLUF —
  task/TOT, push words, JAM BACKUP, compact THREATS AIR/SAM, LOADOUT, SAR if-down — then airfield
  table, flight plan with Fuel column + RTB margin, upstream's `Bullseye:` line, weather,
  bingo/joker, laser, and the SITREP section at the bottom) → **Support Info** (comm ladder /
  AEW&C / tankers / JTAC / airfield directory + the colour-keyed **Code Words block** when
  `enable_package_code_words` is on) → Notes/task page → the setting-gated extras (threat cards
  default ON). A **flight index** page fronts the airframe deck only when 2+ client flights share
  the type (H10).
- **Headless adjudication (2026-07-13):** deck composition + BLUF lines + code-words block covered by
  `tests/missiongenerator/test_kneeboard_bluf.py`, `test_kneeboard_index.py`,
  `test_threat_intel_kneeboard.py`, `test_flightplan_fuel_column.py`; full suite green.
  **Residual (in-sim only):** the in-cockpit read of the reworked Mission Info page (BLUF density,
  SITREP fitting under the flight plan) and the Support page's code-words block.
- **Setup:** generate a mission with a client Strike/SEAD flight on defaults (code words ON for the
  Support block); open the kneeboard on turn 2+ so a SITREP exists.
- **Pass:** the flight's deck opens on Mission Info (no cover, no Brief Sheet); BLUF shows task,
  threats, loadout, SAR; the Bullseye line sits under the flight plan; the SITREP section renders at
  the bottom without clipping; Support Info shows the code-words block; no Comms & Brevity page.
- **Fail signature:** a cover/Brief-Sheet page still generated (stale build); the SITREP clipped off
  the page bottom on a long flight plan; TOP THREAT prose back in the BLUF; the code-words block
  missing with the toggle ON; threat cards absent on defaults.

### H13 — Target recon kneeboard: markers line up on the satellite tiles · kneeboard_recon alignment fix · ☐ UNTESTED (fixed 2026-07-18, the maintenance-day flesh-out-or-kill call on the default-OFF pipeline; two measured causes closed — (1) the dominant DCS-vs-real-world terrain georeference offset (~350 m median on Caucasus/GermanyCW, ~740 m Normandy — tens of page px at detail scale) was only corrected on airbase-anchored pages, and target/corridor/overview pages now apply the robust regional offset of the nearest measured airports (`airport_imagery.offset_near`: median-of-3, 2 km outlier cap, 250 km relevance limit); (2) the whole-page bilinear QUAD warp's interior curvature residual (up to ~5 page px / ~1.9 km ground on a 300 km overview, measured on real terrains) is removed by an n×n MESH warp whose cell corners are each projected exactly (`_mesh_cell_count`: 1 cell ≤ 40 km — detail pages byte-identical — up to 8). Anchor-airport precedence, the offset lookup's gates, the mesh selection/tiling, and the QUAD/MESH wiring are unit-tested in the kneeboard_recon suite (189 green), and the whole path is headless-verified on real Caucasus — the no-anchor regional offset near Anapa lands ~333 m, right on the terrain median. The setting `generate_target_recon_kneeboard` stays default OFF pending this pass.)
- **What CI cannot exercise:** the actual visual overlay — whether the aimpoint triangles/threat rings/runway markers sit ON the imagery features in a rendered page (the imagery itself is fetched live from Esri, which CI never touches).
- **Setup:** any Caucasus or GermanyCW campaign (the offset-heavy maps) with `generate_target_recon_kneeboard` ON and network up. Plan a Strike package + open the generated deck's recon pages: the airbase page, a target detail page, and the corridor overview.
- **Pass:** on the detail page the aimpoint markers sit on the target buildings/revetments in the imagery (within a marker-width, not hundreds of meters off); the airbase page's runway/threshold markers lie on the imaged runway; on the overview the route/threat rings track the imaged coastline/terrain rather than floating a few pixels off mid-page; a no-network run still degrades to the OFFLINE banner fallback.
- **Fail signature:** detail-page markers still displaced by a consistent regional shift (offset_near returned None or picked junk — log `airport_imagery`; check the terrain JSON has measured `imagery_offset_deg` entries near the target); mid-page-only drift on the overview with corners fine (the mesh didn't engage — `_mesh_cell_count` span read); a visible seam/discontinuity at mesh cell boundaries (cell corner projection mismatch — should be impossible since shared corners project identically; if seen, check PIL MESH box rounding); pages crash/blank on a terrain without an imagery JSON (must degrade to no offset, not fail). · §26 · ☑ VERIFIED (2026-06-28, audience in-game pass — user "good, I think"; off-mission auto-resolve looked right, not deeply scrutinized)
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
- **Second IA pass (2026-07-05), re-opens the UI-eyeball leg for the wizard.** The New Game wizard
  audit moved the world-shaping generator options onto the **Theater** page ("Forces & Budget" group,
  re-seeded per campaign on select) and made the old Generator page a grouped **Mods** page; plus the
  legacy sweep (Vietnam card text, "Advanced IADS (MANTIS)", sorted time periods with a named default,
  `Default.zip` subtitle, `SettingNames.py` deleted, OH-6 relabel) and the section regroup ("Campaign
  features" + "Commander economy" on Campaign Management, "Battlefield life" on Mission Generation,
  the Air Doctrine threat wall split into 4 sections). All walk-verified headless (7 pages, 174
  fields) + the wizard files compile. **In-app re-check:** run the wizard end-to-end — the Theater
  page shows and re-seeds Forces & Budget when switching campaigns (e.g. Red Tide 800/400), the Mods
  page reads in its three groups, a generated game honors the checkboxes/budgets exactly as before
  (`accept()` reads the same field names), the Vietnam card lists the right campaigns, and the time
  preset defaults to Mid-90s Summer. **Fail:** a wizard field silently unregistered (game generates
  with defaults — budgets ignored is the tell), the Theater page overflowing at 1080p, campaign
  switching not re-seeding the group, or the settings dialog missing any of the new sections.

### K2 — Campaign SITREP band on the Mission Info page · §29 · ☐ UNTESTED (surface moved 2026-07-13; the cover-page host it was ☑ VERIFIED on 2026-06-28 is retired)
- **History:** the SITREP band shipped on the briefing page, moved to the §30 cover page (where this
  row was VERIFIED 2026-06-28 — numbers across turns OK, "Kneeboards look fantastic"), and returned
  to the **bottom of the Mission Info page** when the 2026-07-13 back-to-upstream rework retired the
  cover. The model/capture/gating are unchanged; only the render surface moved, so the residual is
  the new placement's in-cockpit read.
- **Headless adjudication (2026-06-27, re-valid 2026-07-13):** `tests/test_sitrep.py` covers the
  SITREP model + formatting (side split, captured/lost by side, Combat SAR count, "claimed" enemy
  phrasing, singular/plural) and `sitrep_for_kneeboard` gating (off / no prior turn / quiet turn);
  `tests/missiongenerator/test_kneeboard_index.py` covers the generator's `_briefing_sitrep` gate.
  `record_sitrep` is wired into `commit()` (asserted in `COMMIT_STEPS`).
- **Setup:** Generate a mission (and fly a turn so turn 2 has a prior-turn SITREP); open the Mission
  Info kneeboard page.
- **Pass:** a **"SITREP — Turn N-1"** section renders at the bottom of Mission Info from turn 2 on
  (friendly + enemy-claimed losses, bases captured/lost, pilots recovered, matching the previous
  turn), fitting under the laser-code table. **Turn 1 / a quiet turn / toggle off** → no SITREP
  section.
- **Fail signature:** SITREP present on turn 1 or after a quiet turn (gating wrong); numbers not
  matching the debrief; enemy losses not "claimed"; the section clipped off the page bottom on a
  long flight plan; a stale SITREP from two turns ago (capture not running each `commit`).

### K3 — UI audit follow-up: settings greying + web map discoverability/legend · §28 audit · ☐ UNTESTED (built 2026-07-10)
- **Headless adjudication (2026-07-10):** `tests/test_settings_dependencies.py` locks the greying
  engine — every `enabled_when` master is a real setting, all ~21 pairs verified same-page/same-section
  (so the live refresh fires), and offscreen-Qt tests prove a child control + label grey on open and
  un-grey live when the master toggles, including the inverse `default_front_line_stance ←
  (automate_front_line_stance, False)` pair. The web half (palette tokens, legend, right-click hints)
  is jest-covered for render (all 12 suites green) but its look/interaction is client-runtime only.
  **Residual (UI eyeball only):** the in-app feel of both halves.
- **Setup:** Open **Settings** in a campaign (Qt), then the web map on a campaign with enemy TGOs, a
  front line, and enemy supply routes (Red Tide works).
- **Pass:** *Qt:* children grey with their masters (e.g. the four `red_intent_*` knobs grey until
  **Red intent** is ticked; **Default front stance** greys while automation is ON) and come back live;
  long setting details read as one summary line with the full text on hover. *Web:* the bottom-right
  **Legend** button expands to the colour key and doesn't block map clicks under it; the concealed
  "suspected activity" circle reads **amber** (dashed red = ROE only); front lines / enemy supply
  routes show a pointer cursor + a hover hint naming the right-click action, and right-click still
  frags the package (front line) / interdiction (enemy route); a friendly route offers no
  interdiction hint; a user-placed TGO's tooltip says right-click **removes** it (and it does).
- **Fail signature:** a child stuck greyed after its master is enabled (or greyed on the wrong
  master); a truncated detail with no hover full-text; the legend swatches disagreeing with the
  drawn overlay colours (token drift); the invisible front-line/route hit-band swallowing
  left-clicks meant for markers under it; a right-click hint shown where the action 404s.

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
- **Generic artillery mode (added 2026-07-05, needs its own pass):** the new `artillery_base_harassment`
  setting drives this same emitter+runtime with the tight `ARTILLERY_FRONT_REACH_M` (35 km) — **Red Tide
  preseeds it**, so on a NEW Red Tide game the **Fulda forward FARP** and red's **Haina** (both on the
  Fulda↔Haina front) should draw sporadic artillery harassment after the grace, while Ramstein/Spangdahlem/
  Hahn (100+ km back) stay silent. **Pass:** fire only on the frontline fields; a player cold-starting at
  Fulda is NEVER shelled (the spawn exclusion — cold-start there to prove it); the emitted `fields` list in
  the mission Lua holds only front-adjacent fields. **Fail:** a rear field shelled (the 35 km reach not
  applied — check the Vietnam toggle isn't also on, which widens the reach by design); any impact on a
  player-spawn field; harassment on a campaign with the setting off. Tests:
  `tests/missiongenerator/test_vietnamops_harassment.py`.
  **2026-07-10 flown Red Tide turn 1 (session `gallant-panini-5485e7`): found silent no-op BY GEOMETRY →
  FIXED, needs a re-fly.** The generated miz carried `VietnamOps = {}` — nothing emitted — because the
  turn-1 Fulda↔Haina front sits at the route midpoint, putting **Fulda ~39.3 km and Haina ~39.6 km from the
  FLOT, both ~4 km past the old 35 km `ARTILLERY_FRONT_REACH_M`** (distances read off the emitted QRA-zone
  radii: grown radius − 25 NM). Fix (user call: make it tunable + bump Red Tide): the reach is now a
  campaign-tunable setting **`artillery_harassment_reach_km`** (default 35, unchanged for every other
  campaign; `enabled_when=artillery_base_harassment`), and **Red Tide preseeds 42 km** so both fields fall
  inside from turn 1 (WP BM-27 Uragan MRLs reach ~35 km, so ~42 km is period-honest). Emitter reads
  `settings.artillery_harassment_reach_km * 1000` for the generic mode; the Vietnam siege keeps its
  theater-wide reach. Guard `test_artillery_reach_is_campaign_tunable`. **Re-fly pass:** on a NEW Red Tide
  game, Fulda + Haina both draw harassment after the grace; a player cold-starting at Fulda is still never
  shelled (spawn exclusion); Ramstein/Spangdahlem/Hahn (100+ km back) stay silent.
  **2026-07-11 flown Red Tide M1 (`csar-snatch-toggle-question-dfdb7a`): the 42 km reach emitted; the
  spawn exclusion held by construction.** Load log `Vietnam Ops - Airbase harassment armed for 1 field(s)
  (every ~240s, 5 rounds, dispersion 259m, power 8, grace 300s)` — the 1 field is **Haina** (red);
  **Fulda AND Frankfurt were this mission's client-spawn fields**, so both landed in `excludedFields`
  (confirmed in the emitted miz node), and the intended "shell both Fulda and Haina" correctly collapses
  to Haina-only whenever players base at Fulda — the anti-grief rule doing its job, not a reach failure.
  Zero Lua errors across ~125 min. Still owed: eyes on the **Haina ramp** for the actual impacts/cadence
  (the visual confirm this row has owed since `intelligent-dubinsky`) — note `trigger.action.explosion`
  barrages leave no Tacview objects, so this can only be observed live (or via the "Incoming" cue on red's
  side, which no human can see on Red Tide).

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
  reconcile (charges only killed committed names, floors at 0, **losses-only — no delivery strength credit**
  (2026-07-07 design call), clears the commitment). `test_vietnamops_luadata.py` locks the emitter (serializes the commitment; no commitment → no
  node). The runtime helo spawn + routing + the single-run cue are Lua, exercisable only live.
- **Setup:** A Vietnam campaign with **Vietnam Ops → Super Gaggle** on and a **friendly forward FOB/FARP** near
  the front plus a friendly rear airfield/FARP to launch from (Khe Sanh laydown qualifies), and a BLUE
  helicopter squadron with airframes. Advance a turn (so `plan_super_gaggle` runs), then fly/fast-forward.
- **Pass:** a helo gaggle drawn from the real helo squadron (its own aircraft type) spawns over the launch
  field, flies to the outpost, and announces "SUPER GAGGLE inbound … Marked on the F10 map" then "delivered" on
  arrival — **once, no re-roll**. A **live F10 map mark** tracks the gaggle the whole way (moves with the lead
  helo, disappears on delivery/loss) so it's findable and escortable from anywhere on the map. `dcs.log` shows
  "Super Gaggle armed (outpost …, Nx …, single run)". **Critically:** a shot-down gaggle helo shows up at
  debrief as a **real airframe loss to that squadron** (its `owned_aircraft` drops). **Losses-only
  (2026-07-07 design call):** a clean run gives **no** garrison-strength boost — there is no runtime
  "delivered" signal, so "survived" can't be told from "never spawned"; the gaggle costs only the airframes
  it actually loses.
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
- **Interim evidence (2026-07-15, session `gallant-panini-5485e7` — projector re-run + a real-engine
  AI-vs-AI self-play probe; NOT the played pass, the row stays open):**
  `tools/will_pacing_model.py` on the shipped weights still reproduces the documented full-feed pacing
  exactly (elite folds Hanoi turn 8 / average → Linebacker II win turn 16 / flounder → withdrawal turn 11 —
  no drift since the 07-04 redo). A 20-turn headless Yankee Station self-play (real GameGenerator + campaign
  preseeds + the §26 abstract combat auto-resolving every mission, air-war feeds only — no POW/ROE/convoy
  channels) verified the machinery live: the −0.4/turn war-weariness ratchet, per-feed ledger attribution,
  the will-coupled `advance_when` acceleration (a collapsing blue raced Rolling Thunder → Linebacker II by
  turn 2, charging both escalation taxes), and the M9 ceiling tracking will in BOTH directions. **Two
  balance watch-items for the played pass:** (1) **an auto-resolved (unflown) turn is drastically bloodier
  than a DCS-flown one** — the planner frags B-52s into the un-rolled-back IADS from turn 1
  (`strike_through_air_defense_threat`) and the SEAD-less abstract SAM model killed 8 BUFFs + 40 jets on
  turn 1 (−85 will in one turn); never adjudicate pacing off fast-forwarded turns, and expect a player who
  skips/fast-forwards a turn to nuke their own meter. (2) **the claimed-MiG-kill restore can grind** — at
  +0.3/claim, a blue side taking zero losses out-earns the −0.4 weariness by +3–6/turn (the probe climbed
  will 0.4 → 63.9 over 16 turns while red bled −3/turn from its own airframe losses toward a turtle win
  ~turn 30): a patient BARCAP-only squadron could fold Hanoi without ever striking. Consider a per-turn cap
  or diminishing returns on the kill restore at this row's tuning pass.
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
  between the web map and the F10/ME map (the kneeboard CAMPAIGN PHASE band that also listed them as
  OFF LIMITS retired with the §30 cover, 2026-07-13); a
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
- **Interim evidence (2026-07-15, the M1 self-play probe — see the M1 row):** the ceiling tracked will
  live in **both directions** (×1.00 → ×0.53 at will ~3, back to ×1.00 as will recovered past 60), and the
  **loss-spiral this row worries about did not manifest even from will 0.4 at the ×0.5 budget floor** —
  the probe's blue recovered fully. The floor is doing its "gentle by design" job in the degenerate worst
  case; what's left for the fly is the *felt* pressure on a human-played losing line.
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
- **Concealed "in here somewhere" areas (covers P3–P6, added 2026-07-05):** an **un-reconned** hidden insurgent object (re-infiltration cell P3, roadside IED/VBIED P4, HVT convoy P5, dispersed cell P6) no longer draws an exact marker at all — the web map shows a **dashed amber uncertainty circle** (~4 km, centre jittered off the true position server-side; the true coordinates never reach the client; amber since the §28 UI audit — dashed red is ROE-only) with a "Suspected insurgent activity — fly recon to localize" tooltip. The circle is clickable/right-clickable like a marker (frag TARPS/CAS onto it); once TARPS/attack discovers the TGO it **snaps to the exact symbol** at the real position. Caches and the stronghold garrisons stay exact (infrastructure). Needs an **in-app pass + the CI client rebuild**: on Enduring/Inherent Resolve confirm new IEDs/HVTs/cells appear as circles (not diamonds), the object is NOT at the circle centre, the circle doesn't wander across refreshes/turns, recon snaps it to the marker, and the fog-overview reveal shows everything exact. **Fail:** a circle centred dead-on the object (jitter not applied / seed broken), the marker AND circle both drawn, the circle jumping between refreshes (non-deterministic seed), a revealed/killed object still circled (`known_for` not consulted), or caches/garrisons circled (concealed flag leaked to non-hidden spawns).
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
- **Drone wing added (2026-07-05, from the installed-inventory audit):** Baghdad now hosts the OIR-signature UAVs — **RQ-1A Predator ×4 on TARPS** (the persistent ISR orbits; the `airecon` plugin banks their AI overflights as confirmed BDA, so the drones are what localize the concealed IED/cell circles) and **MQ-9 Reaper ×4 on BAI** (armed overwatch of the ratline). Unit data gained `TARPS: 700` + honest `max_range` (800/400 NM — the 150 NM default gated them out of Balad→Mosul). **Pass addition:** drone flights appear on the ATO (Predators fragged/paired onto recon, Reapers on interdiction), reach the Mosul area, and an AI Predator overflight flips a suspected-activity circle to a confirmed symbol next turn. **Fail:** drones never planned (faction strings dropped — check the loader log), or they frag but never arrive (range/speed — the slow cruise may need the TOT window checked in play). NEW game required.
- **Setup:** a **NEW** "Iraq - Operation Inherent Resolve (COIN)" game (all COIN toggles + `vietnam_political_will`/`campaign_phases`/`high_digit_sams` preseed on). Requires the DCS Iraq map. Check the New Game list shows it; open the F10/ME map for the Mosul + Old City restricted boxes; fly a turn off Qayyarah West.
- **Pass:** the campaign appears and starts; **6 airfields total** (not a ton) — RED holds 3 (Mosul + SA-6, Erbil, Kirkuk + SA-6) + **10 FOBs** filling the corridor + belt (Tikrit, Bayji, Shirqat, Qayyarah, Hammam al-Alil, Bartella, Tal Afar, Hawija, Makhmur, Gwer — no 100 km empty gaps between towns), **each furnished** (2 garrisons of technicals/gun-trucks + AAA + SHORAD + a strongpoint + caches, not a lone marker); the ME-authored towns sit on the real terrain (the base miz) and the generator-added in-between towns are roughly placed (nudge in the ME if needed); BLUE bases from the south only — **Balad the forward player field (Q-West is gone)**, Al-Taquddum strike, Baghdad support; **one front** sits partway up the Balad → Tikrit (Highway 1) axis and moves under pressure; the COIN feed (caches / IEDs / VBIEDs / emirs / dispersed cells) fires as on Enduring Resolve; SEAD has a job (SA-6 at Mosul + Kirkuk) while SA-8/9/13 + ZU-23 punish the deck; a fixed strike inside the Mosul box costs mandate.
- **Fail signature:** campaign hidden from New Game (version gate) or errors on load; a FOB/airfield in water or off-map; a squadron fragged from a dropped/red field (Qayyarah id 6, Erbil id 4); the front never forms (Balad↔Tikrit route missing) or captures a base by sweep; the crust never fills (faction SAM presets dropped) so SEAD has nothing; red strongholds still read barebones (furnishing not applied); the will meters/phases don't move; the ISIS spawns read as US armor (fiction-kit retype not applied).

### P8 — COIN in-mission liveliness: cell movers + insurgent indirect fire on the FOBs · COIN · ☐ UNTESTED (built 2026-07-05, the "systems feel static" part 3; the emitter shapes/gates/player-field exclusion and the Lua grace + double-guard + mover routing are covered in `tests/missiongenerator/test_coinluadata.py` + `tests/lua/test_coin_runtime.py` — the real DCS driving, the barrage look/feel, and whether the pressure reads need a campaign)
- **90-minute mover pacing (2026-07-05, user rule — "sometimes it takes guys a long time to get up in the air"):** the one-way drives (VBIED, infiltrator creep) are **paced** so arrival lands no earlier than `minJourneyS` (default 5,400 s / 90 min) after mission start — every repath recomputes speed = remaining distance / remaining window, capped at the configured speed, floored at a 5 km/h crawl; past the window the configured speed applies. Continuous pacing, not a proximity trigger (the user rejected range-based starts as "lazy and not immersive"). Loop movers (HVT patrol, cell wander) never end, so they already comply. Harness-pinned (`test_coin_runtime.py` pacing tests). **Pass addition:** a VBIED spawned at mission start is still on the road (interceptable) at T+60–80 min, visibly driving the whole time. **Fail:** a VBIED parked at its target base inside the first hour, or a mover teleport-sprinting after the window flips over.
- **What CI cannot exercise:** whether the DCS ground AI actually drives the dispersed-cell wander and the infiltrator creep (the harness models routing calls, not movement); whether the mortar barrages *look* like insurgent IDF (dispersion/power feel) and land clear of parked aircraft; and whether the pressure changes how the campaign feels between stronghold fights.
- **Setup:** NEW "Afghanistan - Operation Enduring Resolve (COIN)" or "Iraq - Operation Inherent Resolve (COIN)" (`coin_harassment` preseeds on; the movers ride the existing `coin_dispersed_cells`/`coin_reinfiltration` preseeds). Fly (or time-accelerate over) a base within ~40 km of a live stronghold; separately, TARPS a dispersed-cell uncertainty circle twice a few minutes apart.
- **Pass:** after the ~5-minute grace, a base near a stronghold draws occasional small impact clusters ("Incoming — insurgent indirect fire on {base}") that are noise/smoke pressure, not aircraft-killers; a player-spawn field is NEVER shelled (cold-start on the nearest base to a stronghold to prove it); a found dispersed cell is *moving* (not parked where the circle was an hour ago); the re-infiltration cell measurably creeps toward its target base over the mission; killing a mover stops its movement (no ghost routing errors in dcs.log).
- **Fail signature:** a barrage lands on a field the player spawns at or recovers to (the exclusion walk missed a package type — check `excludedBases` in the emitted config); fire before the grace expires; barrages on a base with no living stronghold in reach (the 40 km gate broke); every base in the theater shelled (blue filter broke); cells sit motionless all mission (`cells`/`infiltrators` node missing — check the toggles emitted, or `mist.goRoute` errors in dcs.log); `COIN|: setup error` in dcs.log.

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
- **Also eyeball (2026-07-06 layout cleanup):** the tab now reads as grouped sections — *Flight members* /
  *Aircraft settings* (laser codes + properties scrolling, fuel + defaults pinned below) / a labeled
  *Loadout:* row + the pylon editor. The property list should no longer cut off mid-row on a normal window.
  The bold AI-loadout warning appears only while "Use same loadout for all flight members" is unchecked. On
  an **AI-crewed** flight (e.g. an AI F-4E escort) the *Aircraft settings* box should be **compact** — its
  aircraft-property list is player-only so it renders empty, and the box no longer leaves a big blank gap
  between the laser rows and the fuel slider (2026-07-06 follow-up 1). The **weapons loadout at the bottom
  must show all/most pylons, not be crushed into a few** — the pylon list is a natural full-height grid (no
  inner scroll), so the dialog opens tall enough to show every station (2026-07-06 follow-up 2, after a
  player F-16 came up showing only ~5 of 12). Offscreen-instantiation smoke passed headlessly (AI F-4E
  settings-box h=66 vs player F-4E h=288; F-16 lays out all 12 pylons); the visual proportions are the
  in-app question.
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

### S1 — Route-aware fuel-tank planning (fuel-first) · §46 · ◐ PARTIAL (original gen-time top-up ☑ VERIFIED 2026-07-04, user pass — "S1 good I think", tentative; the **2026-07-12 fuel-first rework** — tank-aware tanker decision + the plan-time jammer-pod trade — is ☐ UNTESTED and needs its own pass)
- **Headless adjudication (original top-up):** `top_up_for_route` fills an empty tank station on a far route,
  is a no-op on a short route / empty / custom loadout / setting-off, and **never removes or replaces an
  existing store** (asserted on the Hornet pylon tables). A before/after script showed the COIN Hornet Strike
  going 2→3 tanks on the empty centerline with zero swaps, the Hornet BAI staying 1 tank (no empty station,
  Mavericks untouched), and the short route unchanged.
- **Headless adjudication (2026-07-12 fuel-first rework):** the pre/post-vul tanker decision now counts
  external-tank fuel, `plan_sortie_fuel` fits tanks at plan time (empties first, then the JAMMER-typed pod on
  a tank-capable station when the extra bag strictly saves a tanker pass — or on any shortfall when no tanker
  exists), custom loadouts/shared-object members/idempotence all pinned in
  `tests/fourteenth/test_range_fuel.py` + the Viper BOTH→POST_VUL end-to-end in
  `tests/ato/flightplans/test_fuel_first_tanking.py`. What CI *cannot* adjudicate: whether the AI actually
  flies the single planned pass sensibly in-sim, whether the drag-free burn model leaves enough margin on a
  three-bag jet, and how often the pod trade fires across real campaigns (it should be the exception, not the
  norm).
- **Setup:** a campaign whose strike/SEAD legs outrun internal fuel with a tanker in theater (Red Tide or the
  COIN campaigns); plan a turn, open a SEAD/Strike F-16 package with `auto_range_fuel_tanks` +
  `fuel_tanks_over_jammers` ON (defaults).
- **Pass:** a Viper that used to plan pre+post-vul refueling now shows **3 bags** (centerline tank in the
  payload editor, ALQ-184 gone) and only **one** REFUEL waypoint (or none); its HARMs/AMRAAMs are untouched;
  the kneeboard flight plan's fuel column/RTB margin reads consistent with the bags (no "-short, tank or
  divert" on a sortie the bags cover); a jet whose extra bag would NOT save a pass keeps its jammer; a
  hand-edited (custom) loadout is never touched.
- **In-APP pass (the §46 fuel-plan readout, no DCS needed):** open Edit flight → Payload on any planned
  jet — a "Fuel plan: burns ~X · carries Y (… internal + N tanks …) · N tanker pass(es) · RTB margin ±Z"
  line sits under the fuel slider; drag the fuel slider down / clear a bag pylon and watch the margin fall
  (amber + "short of getting home" when negative); switch members and loadouts and it follows; "(estimated)"
  shows on airframes with no measured fuel block. Fail signature: the line contradicting the kneeboard
  ladder for the same flight (they share the walk — a divergence means the loadout/fuel inputs differ), a
  frozen line after a pylon edit (the `pylon_changed` hook), or a huge phantom burn (the walk failed to stop
  at the landing point and priced the bullseye leg).
- **Fail signature:** a pod traded with no pass saved (the pass-count gate broken); ordnance/TGP/decoy missing
  (the JAMMER-type filter broken — only `type: JAMMER` yaml pods may ever be displaced); a jet with bags still
  planned through two refuel passes (`flight_external_fuel_lbs` not reaching the decision); the fuel ladder
  contradicting the tanker plan (waypointgenerator's external-fuel term); tanks piling up across plan rebuilds
  (idempotence broken). Knobs: `auto_range_fuel_tanks`, `fuel_tanks_over_jammers` (Mission Generation →
  Loadouts).

### S2 — Mobile missile sites relocate (the SCUD hunt) · §49 · ☑ VERIFIED (2026-07-17 night fly: stagger + immobile-exclusion + give-up all proven live, FPS storm gone; one noted collateral — slow-recovering fired SCUDs can be given up before they finish packing)
- **2026-07-17 night fly (fresh Scenic Route Merged turn 1 on the #631/#632 build, Tacview
  `Tacview-20260717-214932`, session `tacview-test-analysis-5bb161`): all three FPS fixes
  VERIFIED.** (1) **Stagger:** move onsets of the 16 never-fired/scooting sites spread
  t=352→3748 s (gaps +12 s to +724 s) — no same-frame mass route push; (2) **immobile
  exclusion:** `armed on 31 site(s)` (the Silkworm sites dropped from the emit), all 20
  `hy_launcher` at 0 m, and **zero `maxDeviationRoll` lines in dcs.log** (vs ~5.9k in the
  storm mission); ANTIFREEZE shows no continuous flood — background 1–4/min with bursts
  (12–26/min) only during the 165-Shahed mass-launch windows, not on scoot ticks; (3)
  **give-up:** 15 `MOBILEMISSILES|: giving up on <group>` lines in-mission — all fired
  CH_Shahed136 sites went silent after their 2 dry pushes exactly as designed. **Noted
  collateral (judgment call, not a regression):** fired vanilla Scud_B batteries split into
  fast recoverers (~10–17 min post-volley: ZEBU/TANG/HERMITCRAB/SPARROW/KANGAROO scooted
  855–3677 m) and **slow recoverers (~40 min pack-up)**: MOUSE/GROUPER were given up (2 dry
  pushes ≈ 16 min of stillness) and then **drove anyway** at t=2936/3748 on their last
  stale route once DCS finished the pack-up animation; TAIPAN/VULTURE/QUAGGA/PARROT hadn't
  moved by recording end (1,500–2,400 s post-fire, 3 of them given up — likely the same
  slow pack-up class). Defensible under the rule's own rationale (a fired battery's
  magazine is empty — the scoot protects loaded launchers, same argument as the Shahed
  pin), and the stale-route quirk means a given-up group that later recovers still
  relocates once. Optional tweak if fired-SCUD scooting is wanted: a larger dry-push
  allowance (e.g. 4) for fire-tasked groups only.
- **2026-07-17 evening fly (PG "Scenic Route Merged" 39-site game, Tacview
  `Tacview-20260717-172716`, session `dcs-mission-test-040ece`): the fire-window fix is
  PROVEN on vanilla hardware — and the residual pin is the CH Shahed launcher, not the
  task.** Every vanilla SCUD battery that fired then scooted: **13/13** Scud_B sites drove
  546–3057 m after their volleys (including every KS-19/ZSU-57 towed-AAA-escorted site —
  the 2026-07-17 morning suspicion about towed escorts is disproven), and never-fired
  sites kept scooting normally. **NEW residual:** all **8 fired `CH_Shahed136` sites
  stayed pinned post-salvo** (post-fire max movement 23–172 m — the escort-creep
  signature) while the two never-fired Shahed sites drove 2.1–2.7 km, so the truck's
  drive physics are fine and the 22 s salvo sits comfortably inside the 240 s window:
  the fired CH launcher is left in a state DCS will not drive out of (mod-side, likely
  its deploy/anim state machine; `resetTask` + alarm-green don't clear it). **Mitigation
  (unflown):** the plugin now **gives up** on a group after 2 consecutive dry route
  pushes (<100 m progress) — the pinned battery is left alone (it is empty anyway; the
  scoot matters for loaded sites) instead of drawing 6 futile pushes/hour
  (`test_stuck_group_is_given_up_after_dry_pushes` + `test_moving_group_is_never_given_up`).
  The same mission confirmed both FPS-storm signatures live (it flew WITHOUT the
  stagger/Silkworm fixes): `ANTIFREEZE` from the first scoot tick + ~5.9k
  `hy_launcher`/`Silkworm_SR` leveling errors — and ONLY those two ids, so the
  `IMMOBILE_UNIT_IDS` set covers everything observed.
  - **Pass (next fly):** a fired Shahed site draws exactly 3 route pushes then a
    `MOBILEMISSILES|: giving up on <group>` log line and silence; fired SCUDs keep
    scooting; playable FPS with no leveling flood.
  - **Fail signature:** give-up lines for groups that DID move (threshold too tight), or
    a healthy site stopping mid-mission.
- **2026-07-17 re-fly (flown PG Scenic Route turn 2, Tacview `Tacview-20260716-230024`,
  session `dcs-mission-test-040ece`): the fire half of the 2026-07-16 fix is PROVEN, a residual
  post-fire pin was found and fixed.** 9/10 fire-tasked batteries launched their full volleys
  12–15 s after their forwarded hold deadlines (18 SCUD + 45 Shahed, launches attributed to
  their batteries at 3–6 m; holds released on schedule; zero tick errors; PEREGRINE alone never
  fired — its task likely aborted as unreachable, and it scooted normally). COUGAR and LAMPREY
  **fired then scooted** (1.4–2.3 km) — the end-to-end sequence. **Residual:** the other 7 fired
  batteries never drove afterward — a bare `FireAtPoint` has no round limit/stop condition, so a
  dry battery's task never ends and the launchers stay pinned deployed; `resetTask()` recovered
  only 2/9 while all 4 never-fired groups drove (sitters' escorts crept 20–80 m and stalled —
  the fail signature the 2026-07-16 row predicted, now root-caused; combat exposure ruled out,
  zero shells near any site). **Fix (unflown):** the generator wraps the fire task in a
  `ControlledTask` stopped at hold + `MISSILE_FIRE_WINDOW_S` (240 s — flown volleys finish
  within ~40 s), ending it through the normal completion path before the plugin's 300 s
  `fireMarginS` routes the group; coupling pinned by
  `test_fire_window_stays_inside_the_plugin_scoot_margin`.
  - **Pass (the re-fly):** fired batteries (not just 2/9) relocate after their volley — watch a
    KS-19/ZSU-57-escorted SCUD site specifically.
  - **Fail signature:** fired batteries still frozen past deadline + 300 s (the stop condition
    didn't stow the launchers either → next lever is an explicit `rounds=` expend count), or a
    volley truncated mid-ripple (window too tight — didn't happen in the flown data, 40 s vs 240 s).
- **2026-07-17 FPS storm found + fixed (the first flown test on the fixed build — fresh 39-site
  game, log-only report):** single-digit FPS with continuous DCS `ANTIFREEZE` from the FIRST scoot
  tick (21:28, grace + 120 s) — before any Shahed launched, so the drones are exonerated. Causes:
  all 39 sites' loops were synchronized (every route push in the same frame each interval, and at
  30 km/h a 4 km scoot spans the whole interval so the fleet never stops driving), and the coastal
  Silkworm hardware (`hy_launcher`/`Silkworm_SR`) has no drive physics — routing it made ~15k
  per-frame `GT.maxDeviationRoll` ground-AI errors in one minute and zero movement (user
  confirmation: Silkworms were never mobile). Fixed (unflown): emitter `IMMOBILE_UNIT_IDS` group
  exclusion + per-site `(i-1)·interval/N` loop stagger in the plugin.
  - **Pass:** a many-site campaign holds playable FPS with `mobile_missile_relocation` on; no
    `woCar` leveling flood in the log; scoots still happen (spread over the interval, not at one
    tick).
  - **Fail signature:** `ANTIFREEZE ENABLED` recurring in dcs.log after the grace window, or
    `has request to level` spam from any routed type (another immobile unit id to add to the
    exclusion set).
- **2026-07-16 fire-vs-scoot clobber found + fixed (flown PG Scenic Route turn 3, Tacview
  `Tacview-20260716-014958`; unflown fix):** the scoot itself re-verified on a third campaign —
  12 of 13 missile groups (4 Scud + 9 Shahed batteries) relocated 1.9–4.0 km inside the anchor —
  but the upstream missile-site **fire task and the scoot clobber each other**: `mist.goRoute`
  pushes routes via `Controller:setTask`, which replaces the waypoint-0 `Hold → FireAtPoint`, so
  every battery that scooted before its Hold expired silently lost its fire mission, and the ONE
  battery that fired (BAT, hold ≈117 s — under the 120 s grace) then sat pinned on the spent task
  and never scooted. Fixed (fire first, THEN scoot): fire-hold deadlines forwarded per-site
  (`fireHoldGroups`/`fireHoldS` via `MissionData.missile_fire_missions`), the plugin holds such
  groups until deadline + `fireMarginS` (300 s), then routes with a `resetTask()` first. Harness
  tests pin the hold/release/reset; **the re-fly is the arbiter**.
  - **Pass:** a fire-tasked battery launches at its hold time AND relocates afterward; the other
    batteries scoot as before.
  - **Fail signature:** a fired battery still frozen after deadline + margin (the resetTask didn't
    un-pin it in DCS — acceptable, it's out of missiles, note and move on), or held batteries
    never scooting at all (holds mis-forwarded).
- **2026-07-11 re-confirm (Red Tide M1 "with Mags happy" `csar-snatch-toggle-question-dfdb7a`, Tacview
  `Tacview-20260711-171935`, ~125 min MP):** both batteries scooted again on the real event save —
  `0015 | CROW` launchers net 107–341 m, `0138 | TETRA` launchers net 1.1–1.2 km, escorts (Ural /
  ZU-23) moving with them; **every SAM/SHORAD/AAA group net 0 m** (category filter intact); and this
  time the load line was captured: `MOBILEMISSILES|: shoot-and-scoot armed on 2 site(s)` (the 07-10
  pass had lost its dcs.log). Battery names are save-generated (ROACH/TOUCAN on the 07-10 save;
  CROW/TETRA here).
- **2026-07-10 re-fly evidence (Tacview `Tacview-20260710-195823`, 49-min Red Tide turn 1; dcs.log lost):**
  ALL 6 `Scud_B` launchers moved — both batteries (`0015 | ROACH` near Wittstock and `0137 | TOUCAN` off
  Haina), net displacement ~1.5 km each over the mission (inside the 4 km scoot radius — the anchor held),
  escorts moving with them (ROACH's Ural-375 + ZSU-57-2; TOUCAN's Ural + Osa until they were killed by the
  player package's Mavericks at t≈2166–2191). No Scud ballistic launch (alarm-green held), and **no SAM site
  moved** (GULL/TURTLE/SNAKE/BUMBLEBEE all static — category filter intact). Killing TOUCAN's escorts did
  not stop the surviving launchers relocating. Still unobserved: the §3 concealment interplay and the
  per-cadence hop pattern (Tacview gives net displacement; the ~6 expected cycles weren't decoded
  individually), and the dcs.log "armed on N site(s)" line (log lost) — none of these block the pass.
- **2026-07-09 flown Red Tide test (`dcs.log` + Tacview `Tacview-20260709-175837`):** `MOBILEMISSILES|: shoot-and-scoot armed on 2 site(s)` armed cleanly, zero runtime error — but **all 6 `Scud_B` launchers stayed put the whole 53-min mission** (Tacview: a single position record each = never moved). Root cause: `driveTo` issued a **1-waypoint** `mist.goRoute` (destination only); a DCS ground group needs its route to START at its current position or it has no leg to drive (see the memory note / MIST's own `groupToRandomZone` uses 2 WPs). **The identical bug was in the COIN mover `coin-config.lua`** (copy-paste) → also affected §P4/P8. Fixed both to a 2-WP route (`{current, dest}`); harness tests assert `points == 2`.
- **Pass:** on a mission a couple of relocation intervals long (~8 min each), the SCUD launchers visibly move to fresh spots within the scoot radius; with recon fog on, they're not where the last photo froze them.
- **Fail signature:** launchers still stationary in Tacview (a single position record) despite the armed line — the 2-WP route didn't take, or the `Scud_B` refuses to path off-road from its spot.
- **What CI cannot exercise:** real off-road pathing (a site authored in rough terrain may fail to move —
  status quo ante, but watch for it), whether the wander reads as shoot-and-scoot at the 8-min/4-km defaults,
  and the interplay with §3 concealment (circle says "in here somewhere", the launcher has moved inside it).
- **Setup:** **Germany — Red Tide** now fields two red SS-1C Scud-B batteries (off Haina, near Wittstock) and
  preseeds the setting + `mobilemissiles` plugin (2026-07-07), so a NEW Red Tide game is the reference case;
  any other campaign with a mobile missile site works too (`mobile_missile_relocation` is default ON). Open the
  F10 map (or the ME) on the site's area; observe over ~15+ minutes, then kill one launcher and keep watching.
  Watch the two GermanyCW SCUD spots aren't in forest/water (blind-placed like every GCW object).
- **Pass:** after the ~2-min grace the site's vehicles pick up and drive to a new spot within a few km, and
  again on the cadence; they hold fire while moving (alarm-green); the site never wanders far from its
  campaign position; killing all its vehicles stops the movement with no dcs.log errors; the SAM network
  (SA-2/6/10 sites etc.) never moves; `dcs.log` shows "MOBILEMISSILES|: shoot-and-scoot armed on N site(s)".
- **Fail signature:** a **SAM site moves** (category filter broken — MANTIS/IADS depends on emitter positions);
  a site migrates kilometers beyond its scoot radius (anchor not applied — the wander must re-anchor on the
  campaign centre, not the last waypoint); launchers stop dead mid-road en masse with repeated `goRoute`
  errors (pathing — consider the off-road action or a smaller radius); movement before the grace; a
  `MOBILEMISSILES|: setup error` in dcs.log; sites still moving with the setting off (gate broken).

### S3 — Friendly convoy ambush (a chance, never telegraphed) · §50 · ◐ PARTIAL (2026-07-06 flown Inherent Resolve session `jovial-gates-574c9c`: the whole chain up to the spring VERIFIED — but the spring itself was blocked by the S5 parked-blue-convoy bug)
- **2026-07-11 flown Red Tide M1 (`csar-snatch-toggle-question-dfdb7a`): quiet mission — inconclusive
  by design.** The blue column (`Convoy 001`, M-113/VAB ×6) drove its full 61 km corridor untouched and
  no "TROOPS IN CONTACT" cue fired; with the 50 % per-convoy roll (and the ≤4-team theater cap) a quiet
  run is an expected outcome, so this neither passes nor fails the row. The light-raider-kit + cap
  re-fly criteria from the 2026-07-09 tuning still stand.
- **Tuned 2026-07-09 (flown Red Tide test — "excessive, and should be light not MBTs"):** the ambush teams spawned as **front-line armor (MBT groups)** and **too many** (a 2-convoy turn maxed to 12 teams). Two fixes: (1) the teams now use a **light raider kit** (`coin.ambush_unit_types` — an armed gun-truck + riflemen from the faction's own roster, `CELL_SIDC` infantry symbol) instead of `GroupTask.FRONT_LINE` armor; (2) `MAX_AMBUSHES_PER_ROUTE` 6→3 **plus** a theater-wide `MAX_TOTAL_AMBUSHES` (4) so several convoys losing the roll on one turn can never swarm the backline. Tests in `test_convoy_ambush.py` + `test_coin_units.py`.
- **Pass (still owed):** an ambush springs with "TROOPS IN CONTACT" and the contact is a handful of **light** vehicles/infantry (not a tank platoon); the theater never shows more than ~4 hidden teams; and the spring fires once a convoy actually reaches it (blocked before by S5).
- **2026-07-06 flown evidence (dcs.log + miz + Tacview):** `CONVOYAMBUSH|: armed 2 ambush(es)`, and the miz
  carries the exact pairing — hidden teams `0104 | OKAPI` (4× tt_KORD, 17.7 km up the Baghdad→Balad corridor)
  and `0105 | WALRUS` (4× tt_DSHK, 46 km up) both keyed to blue `Convoy 003`, a genuine 2-contact gauntlet on
  the real highway. **The hiding contract held in the flown mission:** both teams sat alive, silent, and
  never fired for 52 minutes (alarm-green dug-in, nothing telegraphed — the player flew the whole session
  unaware, which is the design). **The spring never fired because the convoy never drove** (see S5 — blue
  `Convoy 003` sat parked at its Baghdad spawn all mission, so nothing ever entered the 6 km trigger). The
  S3 fly re-runs for free once S5's parked-column bug is fixed.
- **Build/rework history (2026-07-05/06):** the ambush is a per-convoy chance roll seeding 1..6 fully map-hidden teams along the route, the escort auto-frag is DELETED, and a team its convoy never reaches stays silent; the blue convoy top-up, the chance roll + gauntlet placement, the `map_hidden` contract (client/SSE/planner) + every guard are in `tests/fourteenth/test_convoy_ambush.py`, the emit shape/gates in `tests/missiongenerator/test_convoyambushluadata.py`, and the plugin's grace/spring-on-close/silent-without-convoy/dead-team/no-node in `tests/lua/test_convoyambush_runtime.py` — the actual firefight and the spring feel need a mission. **2026-07-05 flown attempt (session `practical-germain`, pre-merge Shattered Dagger COIN save): NOT a pass of the mechanic** — the save predated the preseeds so the feature was correctly gated off (adjudicated from dcs.log + the flown miz + a headless save load: no node, no plugin line, clean no-op) — but it EXPOSED the blue→blue-road prerequisite gap: both COIN campaigns shipped all-red supply graphs, so even a new game could never field the escort convoy. Fixed same day: geo-authored blue rear corridors (ER Kandahar↔Bastion; IR Baghdad↔Balad + Baghdad↔Al-Taquddum) + the `test_preseeded_campaigns_have_a_blue_to_blue_road` CI guard.
- **What CI cannot exercise:** whether the DCS ground AI ambush actually engages the passing convoy and grinds it down; whether the spring reads as an ambush (fires when the column is close, not at max range); whether a multi-team roll reads as a gauntlet of separate contacts down the road; whether flying to the TIC call and clearing a team actually saves the rest of the column; and whether convoy losses + ambush losses both land in the debrief.
- **Setup:** any road-bearing campaign (the `ROAD_BEARING_CAMPAIGNS` inventory in `tests/fourteenth/test_convoy_ambush.py` — since the 2026-07-06 standardization both `convoy_ambush` and `ambient_supply_convoys` default ON for a **NEW game**; the flagship four — COIN Enduring/Inherent Resolve, 1968 Yankee Station, Red Tide — additionally preseed the `convoyambush` plugin ON over any saved-off default). Advance a turn; on the F10 map find a friendly convoy moving between two blue bases (it looks like any other convoy — there is deliberately NO ambush marker and NO escort package in the ATO). Fly anything, and decide on the TIC call whether to divert. May take a few turns to catch a hit roll (~50 % per convoy; `dcs.log` "CONVOYAMBUSH|: armed N ambush(es)" > 0 confirms a live one without spoiling positions).
- **Pass:** the convoy drives its road; NOTHING about the ambush shows anywhere beforehand (no map marker, no uncertainty circle, no ATO package, no F10 mark); when the column closes on a hidden team, it springs (a "TROOPS IN CONTACT" cue + an F10 mark at the fight) and engages; on a multi-team roll the column is hit again further down the road; diverting air onto the mark and killing the team lets the convoy drive on, ignoring the call grinds it down (fewer/no units delivered); the debrief records the dead convoy units (never arrive) AND the dead ambushers (real red ground loss); some turns the road is simply quiet ("armed 0 ambush(es)" / no node).
- **Fail signature:** no friendly convoy ever appears (blue corridor/road missing — check the campaign has a blue→blue `supply_routes` road and `ambient_supply_convoys` is on); an ambush team is visible on the campaign map / web map / F10 before it springs, or a "suspected activity" circle appears on the road (the map_hidden contract broken — check `TgoJs.all_in_game`, the SSE filter in `GameUpdateEventsJs.from_events`, and `triggergenerator._gen_markers`); a BAI package targeting the ambush appears in the ATO (the `BattlePositions` skip broken); a team fires at max range the instant the mission loads (grace/spring broken); a TIC cue with no convoy anywhere near (the removed max-hold fallback resurrected, or trigger radius huge); every convoy every turn is ambushed (the chance roll broken); a `CONVOYAMBUSH|: setup error` in dcs.log; ambushers or convoy losses missing from the debrief (a phantom-spawn regression — both must be real, tracked units).

### S4 — Enemy comms jamming: capture the intel, then the C2 belt steps on the radios · §51 · ☐ UNTESTED (2026-07-11 flown Red Tide M1 `csar-snatch-toggle-question-dfdb7a`: the dormant leg observed — `COMMSJAM|: intel gate armed -- 18 C2 jammer(s), 3 channel(s), dormant until an aircrew capture` at load, radios stayed clean all ~125 min with zero captures, no Lua errors. Correct behavior, but silence-while-dormant can't distinguish "correctly gated" from "broken and silent", so the status stays UNTESTED until a capture→jam moment is heard — use the `[TEST] force capture` toggle. Built 2026-07-06, intel gate added same day; the plan ordering / GUARD filter / cap / backup collision re-roll / intel-gate flags / emit shape are in `tests/missiongenerator/test_commsjamluadata.py`, and the plugin's grace / burst-stop-rotation / dead-jammer silence (both death paths) / ceased cue / intel-gate dormancy + live-capture + POW-story + watch-bail / no-node no-op in `tests/lua/test_commsjam_runtime.py` — whether the static is audible on a tuned radio, the falloff feel, the capture→jam moment, and the kill-to-silence loop need a mission)
- **What CI cannot exercise:** whether `trigger.action.radioTransmission` static is actually audible on a cockpit radio tuned to a jammed channel (and through SRS, which tunes off the cockpit); whether the power falloff reads (loud near the C2 belt, faint near home plate); whether the duty cycle pressures but never fully denies coordination; whether the live capture→compromise→jamming sequence lands dramatically (the real combatsar plugin appending `combat_sar_captures` mid-mission — the harness fakes it); and whether killing the comms node silences it with the "ceased" cue.
- **Setup:** Red Tide, **NEW game** (`enemy_comms_jamming` + the `commsjam` plugin preseeded ON; the intel gate `comms_jam_requires_capture` defaults ON). Note the JAM BACKUP line on the Mission Info kneeboard page (BLUF, next to the code words). **Intel-gate leg:** with no POW held, fly with clean radios; get a pilot ejected + captured (lose the Combat SAR race). **POW leg:** advance the turn with the POW still held and fly the next mission. **Ambient leg (optional):** untick the intel gate and confirm the v1 always-on behavior. **Fast test (thumb on the scale):** tick `[TEST] Combat SAR: force every downed pilot to be captured` (Campaign Management → HQ Automation) so any ejection near the front is seized in seconds → guaranteed POW; advance the turn and the next mission opens jammed (or hear it same-mission after the exploitation delay). To just hear jamming with no capture at all, untick the intel gate.
- **Pass:** radios stay clean while no capture has happened (dormant, `dcs.log` "COMMSJAM|: intel gate armed … dormant until an aircrew capture"); on a capture, an "AIRCREW CAPTURED — assume the comms plan is compromised" cue fires and static bursts begin ~2 min later (the exploitation delay) on the briefed intra-flight/AWACS channels (worse closer to red's C2 belt); with a POW held, the NEXT mission opens with the "COMMS COMPROMISED: enemy interrogation of captured aircrew" cue and jams from the grace; freeing the POW (or the 4-turn clock expiring) returns clean missions; GUARD 243.0, ATC and the JAM BACKUP channel always stay clean; switching to the backup escapes the noise; striking the emitting comms mast/command bunker stops the bursts and (once all emitted nodes are dead) cues "comms jamming has ceased".
- **Fail signature:** jamming before any capture with the intel gate on (`captureOnly` flag not emitted/read); no jamming ever after a confirmed capture (the `combat_sar_captures` global name/shape drifted between the combatsar and commsjam plugins — check both, and that a CombatSAR node was emitted at all: no blue rescue helo = no capture race); the POW leg opens clean (`pending_pow_recoveries` not read — check `plan_comms_jam`); no static ever plays on a jammed channel (sound file missing from the miz — check `commsjam-noise.wav` landed in `l10n/DEFAULT`, or radioTransmission Hz/modulation wrong); static on GUARD/ATC/the backup (the Python positive-list broken); continuous unbroken noise on every channel at once (duty cycle/rotation broken — check `burstSec`/`intervalSec`/`maxFreqsPerBurst` plugin options); jamming continues after the node is confirmed destroyed (death detection — the static `" object"` suffix or the `dead_events` ledger path); a `COMMSJAM|: setup error` in dcs.log; bursts before the startup grace.

### S5 — Ambient supply convoys: both sides' roads have randomized traffic · §50 · ◐ PARTIAL (post-fix flown evidence on Red Tide is clean — 2026-07-11 M1 `csar-snatch-toggle-question-dfdb7a`: BOTH sides' columns drove their full corridors end-to-end (blue `Convoy 001` M-113/VAB 61 km, red `Convoy 002` BTR-80/Grad 65 km, one real transfer per corridor, ~125 min); the original fail signature was Inherent-Resolve-specific (the Baghdad mega-column), so promoting fully off this row still needs the IR re-fly where it actually failed. Was ✗ REGRESSED: 2026-07-06 flown Inherent Resolve session `jovial-gates-574c9c` — red's ambient columns drove their roads, but the BLUE column sat PARKED at its Baghdad spawn for the entire 52-minute mission, the "columns don't drive" fail signature, blue-side)
- **2026-07-09 Red Tide test: convoys DROVE fine here** (Tacview: 62 ground units moved >2 km, top columns 23–26 km, BOTH NATO and Soviet). So the parked-convoy bug is **not** universal — it may be Inherent-Resolve-specific (a coalesced/oversized transfer on a shared corridor — the S5 distinct-road fix). NOTE: ambient convoys are native `coalition.transfers` groups with a real `.miz` route, **not** the `mist.goRoute` movers, so the SCUD/COIN 2-WP fix (S2) does NOT touch this. Re-check on Inherent Resolve after the distinct-corridor sampling.
- **2026-07-06 flown evidence (Tacview + miz):** red ambient convoys worked — `Convoy 001` (Tikrit, drove
  21.6 km), `Convoy 002` (Shirqat FOB, drove 13.4 km down the corridor until the player killed it), `Convoy
  004` (NE belt, drove 18.8 km). **Blue `Convoy 003` — 24 mixed vehicles (MRAPs, Strykers, LAVs, Bradleys,
  Abrams) — spawned at the Baghdad corridor start (x=-142, y=160) and never moved an inch** (one ACMI
  position sample at t=0, max movement 0.0 km over 52 min), despite a well-formed On-Road route in the miz
  (waypoints marching up the corridor at 40 km/h, same shape as the red convoys that drove). Two leads:
  **(1) the merge** — the ambient top-up rolled ≥3 blue columns onto the same Baghdad→Balad corridor and the
  transfer system merged them into ONE 24-vehicle column (3×`AMBIENT_CONVOY_UNITS`=24 ✓); a 24-unit mixed
  tracked/wheeled group line-spawned into unauthored positions (no `convoy_spawns` at Baghdad — the
  ConvoyGenerator "convoy may experience issues at mission start" path) is exactly the form-up-deadlock
  shape. **(2) the spawn terrain** — Baghdad's corridor start may leave part of the line off-road/in scenery
  where the lead can't path. Red's columns were 8–10 light trucks at open-desert FOBs. **Next step:** cap or
  split same-corridor ambient transfers (distinct-road preference like the §35 `exclude_sources`, or one
  transfer per corridor per turn) so no mega-column forms, and/or verify the Baghdad route start sits on the
  highway; then re-fly (which also unblocks S3's spring). NOTE: this also blocked the S3 ambush spring this
  session — the teams were in place but nothing ever drove into them.
- **2026-07-07 (PR follow-up — root cause fixed, needs a re-fly):** two changes landed. **(1) Skim-only**
  (the economy-honesty design call): ambient columns now skim existing rear units instead of
  `commission_units`-ing free ones. **(2) Distinct-road (the S5 fix itself):** the convoy map keys transports
  by `(origin, destination)` (`TransportMap.add`), so the 3 same-corridor blue transfers were coalescing into
  ONE 24-vehicle column that line-spawned into unauthored positions and deadlocked. `_top_up_side` now samples
  **distinct** corridors (`_RNG.sample`, one column per road, capped at the road count), so no mega-column can
  form — the exact lead this row identified. This **trades away** the sketched "some columns share a road"
  texture, which the merge made unachievable anyway (a shared road was one parked blob, not two columns). The
  parked-column root cause is addressed in code; **the re-fly is what promotes this off REGRESSED** (confirm
  both sides' columns drive, and the S3 ambush spring unblocks).
- **What CI cannot exercise:** whether the columns actually drive their roads in-mission on both sides (the engine's own `ConvoyGenerator` path, but now exercised on ~27 campaigns instead of a handful); whether the turn-to-turn variation (1–3 per side, on distinct roads) reads as ambient life rather than a scripted parade; and whether red's ambient columns surface naturally as Armed Recon/BAI targets.
- **Setup:** any road-bearing campaign (`ROAD_BEARING_CAMPAIGNS`), **NEW game**, `ambient_supply_convoys` ON (default). Advance 2–3 turns without flying, checking the map each turn; then fly a mission and find the columns on the F10 map.
- **Pass:** blue AND red convoys appear on their own roads most turns (counts varying, occasionally two columns sharing a road, occasionally a quiet side); columns drive rear→front; red's columns can be right-clicked/fragged as ordinary Armed Recon/BAI targets and their kills count at debrief; a side with no same-side road (e.g. an island map) simply shows none, with no errors.
- **Fail signature:** no convoys ever on a campaign listed in `ROAD_BEARING_CAMPAIGNS` (corridor enumeration or the setting gate broken); the exact same number of convoys on the exact same roads every turn (the RNG not driving); convoys stacking unboundedly (existing convoys not counted toward the target); columns driving front→rear (orientation inverted); convoy units appearing from nowhere at debrief or kills not recorded (a phantom-spawn regression — every column must be a real `coalition.transfers` transfer).

### S6 — Tanker fragged for a no-`fuel:`-block airframe on a long sortie · §46 · ☐ UNTESTED (built 2026-07-08 from a player F-4E report — a −4259 lb OCA/Runway RTB margin with no tanker; `_refuel_tasking` now falls back to `estimated_fuel_consumption`; the fallback / measured-wins / no-tanker-squadron / helo / no-fuel-data gates are locked in `tests/ato/flightplans/test_refuel_tasking_estimate_fallback.py`, but whether the tanker + rendezvous actually close the RTB margin in-mission needs a flight)
- **What CI cannot exercise:** whether the fragged pre/post-vul tanker + the AI rendezvous actually get the F-4E home (the planning is unit-tested; the flying isn't), and whether the estimate's threshold reads right across mod airframes (too eager → tankers on hops that internal + drop tanks already cover; too shy → still short).
- **Setup:** a campaign with an F-4E-45MC squadron **and** a tanker in the wing (e.g. **Germany — Red Tide**, KC-135MPRS), `auto_ato_behavior_tankers` ON. Auto-plan a long-legged OCA/Runway or Strike for the F-4E against a deep target; open the flight's kneeboard flight-plan page.
- **Pass:** the F-4E package now carries a **REFUEL** waypoint (pre- or post-strike) routed to a tanker, and the RTB-margin line reads **+N lb** (or at least far less negative) instead of the old bare −4259 lb "tank or divert". A short-hop F-4E is unchanged (no spurious tanker). A campaign with **no** tanker still shows the −N lb warning (correct — nothing to frag).
- **Fail signature:** a long F-4E sortie still fragged with no tanker while the kneeboard shows a large negative RTB margin (the fallback didn't fire — check `_refuel_tasking` reads `fuel_consumption or estimated_fuel_consumption` and that `can_auto_plan(REFUELING)` is true for the wing); tankers appearing on short hops that internal fuel covers (the estimate's `cruise_nm` bucket is too hungry — `AircraftType.estimated_fuel_consumption`); a measured-fuel airframe's behaviour changed (the `or` should never reach the estimate when measured data exists).

## T. Campaign flow

### T1 — Continuous clock marches + weather evolves across turns · §47 · ☐ UNTESTED (built 2026-07-04; the march-forward-within-3–7 h band, time-of-day-derived-from-clock, midnight date-roll, and previous-turn weather bias are locked in `tests/weather/test_continuous_campaign_clock.py`; the multi-turn *feel* needs a play session)
- **Headless adjudication:** `Conditions.advance` steps `start_time` forward 3–7 whole hours each turn, derives
  time-of-day from the marched clock, and rolls the date at midnight; `generate_weather(previous=...)` biases
  the seasonal draw toward the previous rung on the Clear→Cloudy→Rain→Storm ladder while still honouring a
  zero seasonal chance — all in `tests/weather/test_continuous_campaign_clock.py`. What CI *cannot* adjudicate:
  whether several turns in a row *read* as one continuous timeline (believable clock progression, weather that
  builds and clears rather than flickers) and whether the 3–7 h pacing feels right.
- **Interim evidence (2026-07-15, headless Red Tide self-play probe — 15 turns):** the marched clock held
  the contract on every advance — steps of 3–7 whole hours (07-13 10:00 → 16:00 → 19:00 → 07-14 02:00 → …
  → 07-15 20:00; ~2.4 game-days over 14 turns), dates rolling only at midnight — and the weather **evolved
  as systems, not draws**: ClearSkies → Cloudy (2 turns) → Raining (4 turns) → Cloudy (6 turns), adjacent-rung
  moves with multi-turn persistence, zero clear↔storm teleports. What's left for the fly is only the *read*
  (does it feel like one timeline from the cockpit/briefing).
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

### T2 — Persian Gulf "The Tanker War (1988)" campaign plays · Tanker War campaign · ☐ UNTESTED (built 2026-07-07, Phases 1–3 headless-verified; the laydown — PG theater, US Navy 1985 vs Iran 1988 at a 1988 start, the will profile + authored phase arc parse, the naval preseeds (`vietnam_political_will`, `campaign_phases`, `mobile_missile_relocation`, `coastal_missile_relocation`) — is CI-locked in `tests/fourteenth/test_tanker_war.py`; row added 2026-07-18 — the maintenance sweep found the campaign shipped with no checklist row, the design note's "docs registration" leftover)
- **What CI cannot exercise:** the played campaign — the 1988 CVW off the boat, the ships-not-territory will economy moving from sunk hulls, the shipping-lane ROE corridor gating targets, the coastal Silkworm batteries' fire missions on the period laydown, and above all the **oil-platform AAA gun forts rendering ON the rig decks** (the design note's flagged riskiest render — units placed on platform decks ride the alt-unset rule).
- **Setup:** New Game → "Persian Gulf — The Tanker War (1988)" (US Navy 1985 vs Iran 1988). Generate turn 1; fly or spectate the Strait box (Abu Musa / Qeshm / Bandar Abbas / the oil platforms).
- **Pass:** generates + loads clean; platform AAA stands on the rig decks (not in the sea / floating); the will meters read the naval framing and move when a hull sinks; the phase arc + shipping-lane corridor render on the ribbon/map; the shore Silkworm sites fire their held missions inside the fire window (note: vanilla Silkworm hardware is immobile by design — the emitter never routes it, so fire-without-scoot is CORRECT there, not the (§49) pinned-battery fail signature).
- **Fail signature:** platform guns spawned in the water at the rig position (deck placement broke — nudge `DECK_OFFSET` in `tools/build_tanker_war_miz.py` or hand-place in the ME); a dead will meter when a ship dies (the campaign `will:` block parse degraded silently — it falls back to Vietnam framing); the corridor missing from the map (phase parse degraded); a red S-300 appearing (a long-range band marker escaped the period re-factioning — `iran_1988` fields no long SAM).

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
