# 414th Upstreaming Inventory

Every generic fix the 414th carries that **isn't** upstreamed is a guaranteed
merge conflict on every `dcs-retribution/dcs-retribution` `dev` pull, forever.
The cure is to carve the non-fork-specific fixes out into PRs against the 414th's
PR fork (`bradyccox/dcs-retribution`) so they either land upstream or at least
live on a clean branch that rebases cleanly. This file is the **inventory +
queue**: what's genuinely generic, how ready it is, and — just as important —
what is fork-specific and must **never** go upstream.

> **Scope note.** This file is the *tactical carve queue* for the generic **bug-fixes**.
> For the longer view — that almost every 414th *feature* (SCAR, TIC, TARS, Flight
> Control, QRA, the campaign maker) is also community-upstreamable once split from the
> 414th content/identity layer — see
> [414th-community-contribution-roadmap.md](414th-community-contribution-roadmap.md).
> The ⛔ list below is **genuinely fork-specific** (content, identity, doctrine
> *defaults*); it is *not* the list of "things the community wouldn't want."

Working clones live at `..\retribution-pr` (and `..\pydcs-pr` for pydcs); see
the [upstreaming-prs memory] / `docs/` runbook for the carve-out mechanics.
Verify each candidate in-game first (cross-ref
[414th-ingame-pass-checklist.md](414th-ingame-pass-checklist.md)) — an
unvalidated "fix" is not something to ask upstream to take.

## Readiness legend

| Mark | Meaning |
|---|---|
| 🟢 READY | Lua-free, tested, in-game VERIFIED — carve the PR now |
| 🟡 NEAR | Tested but needs an in-game pass (checklist row) before submitting |
| 🟠 CARE | Touches Lua / a vendored script — split the upstreamable Python from the fork glue |
| 🔵 DONE / IN REVIEW | Already a merged or open upstream PR |
| ⚪ WITHDRAWN | Was pushed, then self-closed — NOT upstream; re-carve if wanted |
| ⛔ NEVER | Fork-specific — keep on `main`, do not upstream |

> **⚠️ Crowded-zone check before any carve (added 2026-06-27).** Upstream `dev` is now
> actively worked by **prokop7** (a full planning-revamp suite: #676 BARCAP, #674 SEAD/DEAD,
> #678 BAI, #677 attack-infra, #679/#680 ground repairs) and **geofffranks** (#782 QRA,
> #772 SEAD, #823 frontline, #754 kneeboard, #765 waypoints, #821 ATIS). **Do not carve any
> planning / SEAD / DEAD / BARCAP / QRA / frontline / kneeboard item without first checking
> `gh pr list -R dcs-retribution/dcs-retribution` for an in-flight PR on the same surface** —
> that is exactly the "stepping on others" the squadron flagged. The safe lane right now is
> the Lua-free items nobody else is touching (landmap perf, `descriptionInUI`, weapon dates,
> target precision, negative-start check, settings QOL). See the live ledger in `CLAUDE.md`.

---

## Queue (priority order)

| # | Fix | Readiness | Value | Checklist |
|---|---|---|---|---|
| 1 | Landmap terrain-query perf | 🔵 IN REVIEW | High (broad: ~7 min off ground-gen) — **pushed as PR #842** | n/a (perf, gen-covered) |
| 2 | DEAD reachability gate on follow-on strikes | 🟢 READY | High (planner correctness) | B2 ☑ |
| 3 | Support-orbit depth + front-anchor | 🟢 READY | High (red AWACS/tanker placement) | C1, C2 ☑ |
| 4 | Player-despawn loss accounting | 🟠 CARE | High (false combat losses) | D1 ☑ |
| 5 | SOF C-130 runway-start fallback | 🟢 READY | Medium (general spawner fix) | E ☑ |
| 6 | Negative-start-packages takeoff-time check | 🟢 READY | Low/Medium (UI false-warn) | n/a |
| 7 | AAQ-33 targeting-pod era restriction | ⚪ WITHDRAWN → ↪ item 11 | — (PR #786 self-closed; re-carve bundled with §24, see item 11) | — |
| 8 | Recon fog-of-war (PR #1: intel-fog + overview toggle) | 🔵 IN REVIEW | Medium (player-facing) — **pushed as PR #828**, awaiting review | — |
| 9 | Combat SAR — pilot rescue flight type + scoring | 🟠 CARE / 🟡 NEAR | High (whole new playable loop) | G8–G11, H2 ☐ |
| 10 | Plugin `descriptionInUI` field (Plugin Options UI, §14) | 🔵 IN REVIEW | High (discoverability) — **pushed as PR #841** | — |
| 11 | Era-gate payload-editor options (JHMCS property gating §24 **+** AAQ-33 redo) | 🔵 IN REVIEW | High (era realism, opt-in) — **pushed as PR #843** | I3 ☐ |
| 12 | Empty `aircraft:` key crashes New Game (`SquadronConfig.from_data` None guard; upstream's own *Northern Guardian* + *WRL Noisy Cricket Redux* ship the pattern) | 🟢 READY | Medium (two shipped campaigns unplayable) | n/a (unit-tested, generation-covered) |
| 13 | High Digit SAMs **Ultimate Compilation** support (§41 generic core: retarget the toggle, renamed radars, 42 new units/7 presets/SAMP-T layout, `remove_vehicle` id-vs-name strip fix; no 414th faction enrichment) | 🔵 IN REVIEW | High (the original mod is dead; unlocks S-400/V4/SAMP-T for everyone) — **pushed as PR #851**, opened 2026-07-01 | N1 ☐ |
| 14 | **Germany - Red Tide campaign publication** (content-only: campaign yaml + miz with routes re-baked as M-113/HandyWind groups, new `Russia 1988` faction, 1-line blufor MPRS add, 44 historical squadron defs; 414th identity stripped from the upstream copy) | 🟡 NEAR | High (a full authored GermanyCW scenario campaign for everyone) — **payload READY** in `docs/dev/upstreaming/red-tide/` (`build_payload.py` regenerates; validated vs dev @ `dce851ea`); needs the current-dev headless validation + PR push from the Windows box (this sandbox can't reach the PR fork) | n/a (content; validated at carve) |
| 15 | Per-squadron DCS country for nation-specific voiceovers + nation-aware pilot names (§23, generic core: `CountryAssigner` + `pilotnames.py`; no 414th faction content) | 🔵 IN REVIEW | Medium/High (mixed-nation CJTF sides get per-nation voices/comms/rosters) — resolves upstream issue #627; **pushed as PR #854**, opened 2026-07-03 | I1 ☑, I5 ☑ |
| 16 | **AI helicopter terrain CFIT trio** (helo cruise waypoints at the dead `heli_cruise_alt_agl` setting; ≤5 NM RADIO terrain-anchor subdivision of long AI helo legs; air-start unit records mirroring the point `alt_type` — all three verified verbatim in upstream `dev`) | 🟡 NEAR | High (AI helos CFIT on every hilly map; the flown Red Tide M1 lost 3 Mi-8 + 1 Mi-24 to it) | C8 ☐ |
| 17 | **Blue-block miz markers load + bind blue** (`MizCampaignLoader`: every marker class also walks the BLUE country block — blue-block ships/SAM/EWR/missile/coastal/offshore markers were silently dropped, 22 authored markers across 7 upstream campaigns never generated (Dynamo's evacuation flotilla, Allied Sword's oil platforms, Falklands task-force ships…) — and a blue-block marker binds the nearest BLUE CP instead of nearest-any; red-block markers keep the coalition-agnostic proximity convention, plus an actionable `generate_ewrs` no-ForceGroup error naming the stranded marker/CP) | 🟢 READY | High (restores authored content in 7 shipped campaigns; kills a silent authoring foot-gun) | n/a (tests/test_miz_marker_binding.py + the 7 campaigns headless-verified) |
| 18 | **Ship-launched cruise missile strikes** (generic core of fork [414Ret#599](https://github.com/bradyccox/414Ret/pull/599): `game/cruisemissiles.py` LACM hull set + persisted no-rearm magazine + auto-raid planner, `cruisemissileluadata` emitter, `cruisemissiles` plugin — F10 call-for-fire with marker-text salvo sizing + magazine status — and the `cruise_missiles_state` debrief channel; fork couplings stripped: no ROE-zone gate, no `map_hidden`, no `enabled_when`) | 🔵 IN REVIEW | High (naval land-attack for every campaign; both settings default off) — **pushed as draft PR #872**, opened 2026-07-15 | n/a (unit-tested both sides; validated on dev @ `ef576acc`: pytest/Black/mypy clean) |
| 19 | **Curated carrier comms** (§65 verbatim: `game/data/carrier_comms.py` per-hull boat cards, `TacanRegistry.alloc_near` nearest-neighbor degrade + `alloc_for_band` marking, `IclsAllocator`, the four `_resolve_*` precedence helpers + flagship hull-naming; NO fork couplings — the port only adds the Pretense allocator-type adaptation the fork doesn't need) | 🔵 IN REVIEW | High (every carrier campaign's CV Ops Data page reads real, stable boat data) — **pushed as draft PR #874**, opened 2026-07-16 | B18 ☐ |

---

## Details

### 1. Landmap terrain-query perf — 🔵 IN REVIEW (pushed as PR #842, 2026-06-27)
- **What:** `is_on_land`/`is_in_sea` must test the **prepared** `MultiPolygon`,
  and `pickle` bypasses `__post_init__`, so the spatial index has to be rebuilt
  on load. Fixing both cut a ~7-minute ground-generation stall.
- **Carve note (corrected on carve):** upstream **already** prepares the index in
  `Landmap.__post_init__` — but it's dead at runtime because landmaps always load
  from pickle. The genuine delta carved into PR #842 was (a) `is_on_land`/`is_in_sea`
  testing the whole prepared `MultiPolygon` instead of looping `.geoms`, and (b)
  `load_landmap` re-running `Landmap.prepare()` after the pickle load. **Files:**
  `game/theater/landmap.py` + `game/theater/conflicttheater.py` (not `__setstate__`).
- **Why upstream cares:** pure perf, zero behavior change, benefits every
  theater/campaign — the easiest possible upstream sell.
- **In-game pass:** not required — it's a generation-time perf fix already
  exercised by the normal campaign-gen path.
- **Note:** confirm whether the prepared-geometry dependency is satisfied in a
  clean upstream checkout (Shapely version) before submitting.

### 2. DEAD reachability gate on follow-on strikes — 🟢 READY
- **What:** a follow-on strike behind a SAM belt is deferred until the belt is
  actually down, instead of trusting an optimistic DEAD clear. The DEAD itself is
  still tasked (with SEAD escort).
- **Why upstream cares:** this is upstream-core HTN behavior, not a 414th
  concept — a correctness fix to the stock planner.
- **Files:** `dead_can_reach` geometry + `apply_effects` routing in
  `game/commander/.../theatercommander.py`.
- **Tests:** `tests/test_dead_planning.py`.
- **In-game pass:** B2 ☑ VERIFIED 2026-06-24 — blue defers deep strikes until the
  belt is down. Cleared to carve.
- **⚠️ Collision (2026-06-27):** prokop7's **#674 (SEAD/DEAD revamp)** and geofffranks'
  **#772 (SEAD loiter-and-react)** are both live on this exact surface. **HOLD** — review
  theirs and check for overlap before opening a competing DEAD-gate PR.

### 3. Support-orbit depth + front-anchor — 🟢 READY
- **What:** AWACS/tanker racetracks anchored on the FLOT (#84) and held at a
  depth decoupled from the player's threat strength via
  `AI_SUPPORT_DEPTH_FACTOR` (#86), so red support doesn't loiter on the front.
- **Why upstream cares:** upstream-core flight-plan code; the off-axis red AWACS
  fling is a stock bug.
- **Files:** `game/ato/flightplans/supportorbit.py`.
- **Tests:** `tests/test_support_orbit.py`.
- **In-game pass:** C1 + C2 ☑ VERIFIED 2026-06-24. Cleared to carve.
- **⚠️ Note (2026-06-27):** the related lateral-deconfliction carve was opened as **PR #790
  and then self-withdrawn** — so support-orbit work is **not** upstream. The depth/front-anchor
  fix here is distinct from #790; re-confirm no overlap with prokop7's #676 (BARCAP, touches
  orbit geometry) before re-pushing.

### 4. Player-despawn loss accounting — 🟠 CARE
- **What:** a player dropping to spectator (or a mission ending with players
  airborne) made DCS fire `S_EVENT_CRASH`/`DEAD`, attriting a surviving jet +
  pilot. The fix marks the unit on `S_EVENT_PLAYER_LEAVE_UNIT` and suppresses the
  loss within `PLAYER_LEAVE_GRACE_S`; real shootdowns (loss event fires before
  leaving the seat) and ejections still count.
- **Why upstream cares:** loss-accounting correctness, airframe-agnostic.
- **Files:** `game/debriefing.py` (Python) **+** `dcs_retribution.lua` (the
  plugin-side `PLAYER_LEAVE_UNIT` marking). **Split the PR:** the Python debrief
  logic is clean; the Lua hook lives in the bundled runtime script, so confirm
  the upstream `dcs_retribution.lua` has the same event surface before porting.
- **Tests:** `tests/test_debriefing.py::test_lua_suppresses_player_despawn_loss_events`.
- **In-game pass:** D1 ☑ VERIFIED 2026-06-24. 🟠 CARE is about the **carve**, not
  the test: the Lua hook lives in the bundled runtime, so split the PR (Python
  debrief logic vs the `dcs_retribution.lua` event surface) before porting.

### 5. SOF C-130 runway-start fallback — 🟢 READY
- **What:** on `NoParkingSlotError`, retry a **runway start** before forcing an
  air spawn — previously gated to `FlightType.JAMMING`, now any non-helo
  cold/warm start at an airfield. Stops large aircraft air-spawning when a ground
  start was selected.
- **Why upstream cares:** general spawner robustness, not SOF-specific.
- **Files:** `game/missiongenerator/aircraft/flightgroupspawner.py`
  (`generate_flight_at_departure`).
- **In-game pass:** E ☑ VERIFIED 2026-06-24 (SOF C-130 ground-starts, EW skipped).
  The runway-fallback logic is also exercisable by any large-aircraft ground start.
- **⚠️ Carve carefully:** ship ONLY the runway fallback. The **EW plugin
  de-conflict** that ships alongside it (§ below) is fork-specific.

### 6. Negative-start-packages takeoff-time check — 🟢 READY
- **What:** `QTopPanel.negative_start_packages` checks **takeoff** time (not
  startup) for DCA patrols, so a normal player-occupied cold-start CAP stops
  tripping the "can't start in time" warning while a genuine misplan still warns.
- **Why upstream cares:** stock UI false-positive fix.
- **Files:** `qt_ui/.../QTopPanel.py`.
- **Tests:** `tests/test_negative_start_packages.py`.
- **Note:** `qt_ui` isn't in the CI mypy path upstream either; Black-clean is the
  bar.

### 7. AAQ-33 targeting-pod era restriction — ⚪ WITHDRAWN → re-carve as part of item 11
- Was opened as upstream **#786** (`codex/fix-aaq33-era-restriction`), then
  **self-closed by bradyccox on 2026-06-13** (no maintainer rejection). It is therefore
  **NOT upstream and still fork-only.**
- **Decision (2026-06-27):** do not re-open #786 standalone. **Bundle it with the JHMCS
  property gating (§24) into one "era-gate payload-editor options" PR** — see item 11.
  Both share the theme of gating payload-editor choices by campaign date off the existing
  `restrict_weapons_by_date` toggle, so they present better together.

### 8. Recon fog-of-war — 🔵 IN REVIEW (pushed as PR #828)
- **Pushed:** carved + opened upstream as **[PR #828](https://github.com/dcs-retribution/dcs-retribution/pull/828)**
  (2026-06-23, +473/-14, `mergeable`, `REVIEW_REQUIRED`). Awaiting a maintainer review;
  no action owed beyond responding to feedback when it arrives.
- **History:** `fog-of-war-complete.patch` (17 files, +473/-14) applied cleanly on upstream
  `dev` `a31357b` and passed `black`, `mypy game tests` (439 files), and 9 fog `pytest`s in a
  clean upstream checkout before being pushed as #828.
- **What:** the recon intel-fog (enemy site composition + threat/detection rings
  hidden until the site is attacked/scouted/destroyed) plus the transient
  "Reveal fog of war" overview toggle. Carved as a **2-PR stack**: PR #1 = the fog
  mechanic alone (aircraft-agnostic, reveal-on-engage), PR #2 = the TARPS recon
  platform + the `alive_for`/`alive_at_last_recon` BDA damage-lag it activates.
- **Why re-scoped:** this was previously parked under ⛔ as "fork feature." It is
  upstreamable once split from the SCAR command-post gate and the F-14 TARPS specifics;
  PR #1 is genuinely generic. Tyler/Brady call.
- **Kit:** `docs/dev/upstreaming/fog-of-war/` — `PR.md` (title + body),
  `CARVE-MANIFEST.md` (exact per-file hunks, generic vs ⛔ SCAR vs ⏭ PR #2),
  `0001-fog-of-war-new-files.patch` (the portable new files; apply on the upstream clone).
- **⚠️ Carve carefully:** drop `hidden_on_player_map` / `_command_post_revealed` /
  `scar_command_post_intel` (SCAR), and the TARPS/TARS reveal triggers + the whole
  `alive_for` damage-lag layer (→ PR #2). The client checkbox must land in upstream's
  own map-layer control, not the fork's custom panel.
- **In-game pass:** the Python is test-covered; the player-facing fog still wants an
  in-game pass on a fresh campaign (composition hidden → reveals on strike; overview
  toggle un-fogs and re-fogs).

### 9. Combat SAR — pilot rescue flight type + scoring — 🟠 CARE / 🟡 NEAR
- **What:** a generic `FlightType.COMBAT_SAR` (CH-47 rescuer + C-130 "King" orbit) driven
  by the bundled MOOSE `CSAR` engine, an `auto_combat_sar` AI standing alert, the King TACAN
  beacon + LARS, the kneeboard card, and the **rescue-scoring loop** (a delivered pilot is
  spared at debrief; the airframe is still lost). Test-covered in Python
  (`tests/test_combat_sar_scoring.py`).
- **Why it's a candidate:** a whole new playable rescue loop with broad community value, and
  almost entirely generic (vanilla CH-47/C-130, bundled MOOSE — no HighDigitSAM/mod deps).
- **🟠 CARE — the Lua + glue:** the engine config lives in `resources/plugins/combatsar/` and
  the scoring rides the fork's `state.json` export globals (`combat_sar_rescues` in
  `dcs_retribution.lua`) + the `commit_air_losses` hook. Carve the **Python task + flight plan
  + scoring** as the upstreamable core; the MOOSE `CSAR` bridge ships as the plugin. Keep it
  blue-only-by-default scoping that exists today.
- **🟡 NEAR — unflown:** code-complete but G8–G11 + H2 are all ☐ UNTESTED. **Do not submit
  before the in-game pass** — per the readiness legend, a runtime feature gets carved after it
  is flown, not before. The scoring is fail-safe (empty export = pre-scoring behaviour), which
  de-risks the carve but does not substitute for flying it.
- **Source of truth:** `docs/dev/design/414th-combat-sar-spec.md`, features doc §21.

### 10. Plugin `descriptionInUI` field — 🔵 IN REVIEW (pushed as PR #841, 2026-06-27)
- **What:** an optional `descriptionInUI` string in the plugin manifest, rendered as an
  italic word-wrapped line atop that plugin's options box. Backward-compatible (defaults
  to `""`); also populated for 8 bundled upstream plugins so the field is demonstrated.
- **Files:** `game/plugins/luaplugin.py` + `qt_ui/windows/settings/plugins.py` + 8
  `resources/plugins/*/plugin.json`. No 414th deps; the cheapest community win in the repo.
- **Carve note:** the fork's `splashdamage3` description is 414th-specific (pinned build) —
  intentionally **not** carried to upstream.

### 11. Era-gate payload-editor options (JHMCS §24 + AAQ-33 redo) — 🔵 IN REVIEW (pushed as PR #843, 2026-06-27)
- **What:** extend the already-upstream `restrict_weapons_by_date` toggle from weapons to
  payload-editor *properties* and *targeting pods*. Two pieces, one PR:
  - **JHMCS property gating (§24):** the new self-contained `game/dcs/aircraftproperties.py`
    (103 lines, pydcs-only) + `degrade_props_for_date` in
    `game/missiongenerator/aircraft/flightgroupconfigurator.py` + the dropdown filter in
    `qt_ui/windows/mission/flight/payload/propertycombobox.py`. Hides/clamps JHMCS
    (fielded ~2003) in pre-2003 missions. Keyed by value *label* so the Su-30/Su-35 "SURA
    Visor" (same id) is **not** gated.
  - **AAQ-33 targeting-pod era restriction:** the fix from withdrawn #786 (item 7).
- **Why combined:** same theme (gate payload-editor choices by campaign date off one
  existing toggle); historically grounded (a fact, not a balance opinion); no overlap with
  any open upstream PR; entirely fork-only today (verified 2026-06-27: no `degrade_props`/
  JHMCS anywhere upstream). Cleaner than the weapon-date *balance* rule (which overlaps the
  already-merged #826 and is opinion-based — keep that on `main`).
- **Status:** opened 2026-06-27 as **[PR #843](https://github.com/dcs-retribution/dcs-retribution/pull/843)** (15 files: new `aircraftproperties.py` + generator gate + payload-editor UI chain + 6 pod yamls + 2 tests). Black/mypy/pytest validated locally (28 tests pass). The #786 patch re-applied cleanly on current `dev` and the custom-payload coverage test still passes. **In-game pass I3 ☐** still pending a flight.

### 18. Ship-launched cruise missile strikes — 🔵 IN REVIEW (pushed as draft PR #872, 2026-07-15)
- **What:** warships with land-attack cruise missiles (vanilla Burke/Ticonderoga,
  CurrentHill Kalibr LACM/CMP hulls) strike shore targets via a scripted
  `FireAtPoint` push carrying the cruise-missile weapon flag (2097152) — the
  mission-editor mechanism. F10 "Cruise Missile Strike" call-for-fire on the
  coalition's last map marker (marker text `6`/`#6` sizes the salvo), optional
  one-raid-per-side-per-turn auto planner (command/comms first, then war
  industry), and a persisted per-ship-group campaign magazine with **no rearm**,
  debited only from what the plugin reports fired via the new
  `cruise_missiles_state` debrief channel at the turn boundary — generation
  never debits, so re-generating a mission cannot double-count.
- **Why upstream cares:** a naval land-attack capability the engine never
  modelled, fully symmetric; the missiles are real weapons from real, sinkable
  ships (kills record natively, point defense can intercept, a sunk shooter
  fires nothing); both settings default off.
- **Carve note:** generic core of fork [414Ret#599](https://github.com/bradyccox/414Ret/pull/599);
  carved clean of the fork's `game/fourteenth/` namespace, ROE-zone gate,
  `map_hidden` coupling, `enabled_when`, Lua-harness tests, and §-number references.
- **Files:** `game/cruisemissiles.py`, `game/missiongenerator/cruisemissileluadata.py`
  (+ `luagenerator.py` wiring), `resources/plugins/cruisemissiles/`,
  `game/debriefing.py` + `game/sim/missionresultsprocessor.py` +
  `resources/plugins/base/dcs_retribution.lua` (the debrief channel),
  `game/settings/settings.py` (`cruise_missile_strikes` + `cruise_missile_auto_raids`).
- **Tests:** `tests/test_cruisemissiles.py`,
  `tests/missiongenerator/test_cruisemissileluadata.py`.
- **Status:** opened 2026-07-15 as **draft [PR #872](https://github.com/dcs-retribution/dcs-retribution/pull/872)**
  (19 files, +1364, two commits: core + UI surfacing). Rebased onto dev @
  `ef576acc` at push time (one trivial changelog conflict); re-validated on
  that base: pytest 249 passed/0 failed, Black clean, mypy `game`+`tests`
  clean. The second commit pre-empts the obvious review ask: the player's
  tasked raid + magazines in the mission briefing, a magazine box in the
  naval TGO dialog (friendly side only), and per-group expenditure in the
  debrief window — all driven by tested helpers in `game/cruisemissiles.py`.

### 19. Curated carrier comms — 🔵 IN REVIEW (pushed as draft PR #874, 2026-07-16)
- **What:** the fork's §65 verbatim — DCS renders the "CV Operations Data"
  kneeboard page straight from the miz, and the generator fed it allocator
  junk (the boat "named" `0796 | CVN-71 …`, TACAN 1X + a random ident
  re-rolled every mission, Link 4 on a random UHF, a fresh random ATC every
  turn). A curated per-hull boat card (`game/data/carrier_comms.py`:
  hull-number TACAN + boat ident, hull-keyed ICLS, Link 4 in the ACLS
  336 MHz band, stable ATC) resolved with stored-values-win precedence;
  `TacanRegistry.alloc_near` degrades a map-owned hull channel to the
  nearest valid free neighbor (Bagram owns 74X on Afghanistan); a shared
  `IclsAllocator`; every value persists to the control point; the flagship
  unit named by its hull name (before UnitMap registration).
- **Why upstream cares:** every carrier campaign's kneeboard/briefing carrier
  data becomes stable and realistic; the `alloc_for_band` marking also fixes a
  latent cross-usage TACAN double-issue (the X-band T/R and A/A pools overlap
  at 37–46 and 100–126 and neither iterator marked its picks). No settings, no
  save-format change.
- **Carve note:** zero fork couplings — the port is the fork code verbatim
  minus §-number comments, plus adapting upstream's Pretense generators
  (`Iterator[int]` → `IclsAllocator`; `alloc()` keeps the same sequential
  walk, Pretense behavior untouched — the fork has no Pretense).
- **Files:** `game/data/carrier_comms.py`, `game/radio/tacan.py`,
  `game/missiongenerator/tgogenerator.py`, `game/pretense/pretensetgogenerator.py`.
- **Tests:** `tests/test_carrier_comms.py` (24 tests, ported verbatim).
- **Status:** opened 2026-07-16 as **draft [PR #874](https://github.com/dcs-retribution/dcs-retribution/pull/874)**
  on dev @ `ef576acc`; validated on that base: pytest 256 passed, Black clean,
  mypy clean (the fork side landed as [414Ret#611](https://github.com/bradyccox/414Ret/pull/611)).

---

## ⛔ Fork-specific — do NOT upstream

- **C-130J EW (`c130j`) plugin de-conflict on SOF inserts**
  (`game/missiongenerator/luagenerator.py` `_sof_c130_present`): skips the 414th
  EW/ISR plugin when a `FlightType.SOF` flight is a C-130J-30. Depends entirely
  on the fork's `c130j` plugin and `FlightType.SOF` — meaningless upstream.
- **The 414th content + identity + multi-turn-economy layer** — the Red Tide and
  Operation Shattered Dagger campaigns, the [CH] Iran 2020 faction (CurrentHill mod
  dependency), the doctrine *default values* (QRA radii/probability), the SCAR
  commander-capture / SOF / CSAR economy loop, the C-130J EW *physics constants*, and
  the TIC stance tuning. These stay on `main`.
  > **Re-scoped:** the *feature mechanisms* underneath — the SCAR base task, TIC, TARS,
  > the QRA reserve model, the `FlightType.JAMMING` framework — are
  > **high community value, hard carve**, not "never want." They moved out of this ⛔
  > list into the
  > [community contribution roadmap](414th-community-contribution-roadmap.md) (Tier 3),
  > the same way recon fog moved from ⛔ to queue item 8. Only the doctrine/economy
  > slivers above stay here.
- **Splash Damage 3.4.2 414th buddy-tuned build** — pinned, intentionally
  divergent from upstream/source. Never push upstream or overwrite from it.
- **AGM-65 Maverick date-fallback → Mk-20 Rockeye** (`resources/weapons/standoff/AGM-65A.yaml`,
  `fallback: Mk-20 Rockeye`). The whole AGM-65 family chains its pre-1972 degrade through this
  node; the fork degrades Mavericks to an anti-armor cluster (Rockeye) rather than the
  ~1100 lb TV-guided AGM-62 Walleye, because a Maverick is a CAS/anti-armor PGM. **Upstream
  rejected this** on PR #847 (Druss99: loadout/fallback choices target AI mission performance,
  not historical accuracy, and the Walleye is the preferred standoff-class fallback), so #847's
  AGM-65A was reverted to the upstream `AGM-62 Walleye II`. **Keep the Rockeye reroute on the
  fork** — do NOT let a future carve or dev-pull "fix" it back to Walleye. (The expanded AGM-65A
  CLSID coverage is shared with upstream and is fine to keep in sync.)
- **PR #823 frontline merge divergences** (adopted 2026-06-26, not a carve-out —
  the inverse: we pulled upstream PR #823's composition/stance *into* the fork).
  Two fork-specific divergences to **preserve when #823 (or its descendants) lands
  on `dev`** — do not let a future dev-pull stomp them:
  (1) the #823 DCS-task cohesive maneuver in `flotgenerator.plan_action_for_groups`
  is gated behind `not self.tic_enabled` so TIC keeps ownership of armor movement
  (upstream has no TIC, so it runs the maneuver unconditionally — keep our guard);
  (2) `ai_ground_planner.plan_groundwar` uses the fork's `base.total_frontline_units`
  denominator, not upstream's `total_armor`. The clustering/placement/stance code
  itself matches upstream and needs no carve. Full record:
  `docs/dev/design/414th-pr823-frontline-merge-notes.md`.

---

## Carve-out checklist (per PR)

1. Branch off a **clean** `dcs-retribution/dev` in `..\retribution-pr` (not off
   `main` — that drags the whole feature stack).
2. Cherry-pick / re-apply only the files listed for that item; drop any
   fork-specific glue (see ⛔).
3. Run the upstream repo's own lint/test gates (not the 414th's).
4. Confirm the matching [in-game pass](414th-ingame-pass-checklist.md) row is
   ☑ VERIFIED before opening the PR.
5. Open against `dcs-retribution/dcs-retribution`; record the PR number back in
   the Queue table here and flip readiness to 🔵 DONE.

[upstreaming-prs memory]: how generic 414Ret fixes become upstream PRs; working
clones in `..\retribution-pr` and `..\pydcs-pr`.
