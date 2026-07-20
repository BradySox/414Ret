# 414th Upstreaming Inventory

Every generic fix the 414th carries that **isn't** upstreamed is a guaranteed
merge conflict on every `dcs-retribution/dcs-retribution` `dev` pull, forever.
The cure is to carve the non-fork-specific fixes out into PRs against the 414th's
PR fork (`bradyccox/dcs-retribution`) so they either land upstream or at least
live on a clean branch that rebases cleanly. This file is the **inventory +
queue**: what's genuinely generic, how ready it is, and — just as important —
what is fork-specific and must **never** go upstream.

> **Scope note.** This file is the *tactical carve queue* for the generic **bug-fixes**.
> For the longer view — that every 414th *feature* is community-upstreamable once
> packaged — see
> [414th-community-contribution-roadmap.md](414th-community-contribution-roadmap.md).
> **Policy 2026-07-19: everything is upstreamable** ("clean and correct" is the bar;
> squadron directive). The old ⛔ NEVER category is retired — its section below now
> distinguishes **last-mile items** (need packaging/rationale, queue when ready) from
> **merge-discipline divergences** (fork resolutions to preserve on dev-pulls, e.g.
> where upstream already rejected a change).

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
| 🕐 LAST-MILE | Needs packaging (identity strip / defaults-with-rationale) before it can queue — nothing is permanently fork-only (2026-07-19 policy) |

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
| 1 | Landmap terrain-query perf | ⚪ WITHDRAWN → re-carve | High (broad: ~7 min off ground-gen) — PR #842 **closed unmerged** (2026-07 refresh); ⚠️ overlaps juanjux's open #876 `shapely.contains_xy` PR — review theirs first, re-carve only the non-overlapping half (pickle re-prepare) | n/a (perf, gen-covered) |
| 2 | DEAD reachability gate on follow-on strikes | 🟢 READY | High (planner correctness) | B2 ☑ |
| 3 | Support-orbit depth + front-anchor | 🟢 READY | High (red AWACS/tanker placement) | C1, C2 ☑ |
| 4 | Player-despawn loss accounting | 🟠 CARE | High (false combat losses) | D1 ☑ |
| 5 | SOF C-130 runway-start fallback | 🟢 READY | Medium (general spawner fix) | E ☑ |
| 6 | Negative-start-packages takeoff-time check | 🟢 READY | Low/Medium (UI false-warn) | n/a |
| 7 | AAQ-33 targeting-pod era restriction | ⚪ WITHDRAWN → ↪ item 11 | — (PR #786 self-closed; re-carve bundled with §24, see item 11) | — |
| 8 | Recon fog-of-war (PR #1: intel-fog + overview toggle) | 🔵 IN REVIEW | Medium (player-facing) — **pushed as PR #828**, awaiting review | — |
| 9 | Combat SAR — pilot rescue flight type + scoring | 🟠 CARE / 🟡 NEAR | High (whole new playable loop) | G8–G11, H2 ☐ |
| 10 | Plugin `descriptionInUI` field (Plugin Options UI, §14) | 🔵 IN REVIEW | High (discoverability) — **pushed as PR #841** | — |
| 11 | Era-gate payload-editor options (JHMCS property gating §24 **+** AAQ-33 redo) | 🔵 **MERGED 2026-07-19** (PR #843; upstream took the fork's final `date_gated_properties` shape — reconciled in the 2026-07-19 sync. ⚠️ upstream's aircraft-yaml copies froze a stale fork task-priority snapshot — owe a data-cleanup PR) | High (era realism, opt-in) | I3 ☐ |
| 12 | Empty `aircraft:` key crashes New Game (`SquadronConfig.from_data` None guard; upstream's own *Northern Guardian* + *WRL Noisy Cricket Redux* ship the pattern) | 🔵 IN REVIEW — **pushed as draft [PR #890](https://github.com/dcs-retribution/dcs-retribution/pull/890)**, opened 2026-07-20. ⚠️ The "two shipped campaigns unplayable" claim went stale: current upstream campaigns no longer carry the pattern (Northern Guardian's Transport squadron was filled in upstream; the fork hit the crash when its own mod purge emptied the key) — the PR pitches it honestly as a defensive guard | Medium (defensive; the crash still fires on any author-emptied key) | n/a (unit-tested, generation-covered) |
| 13 | High Digit SAMs **Ultimate Compilation** support (§41 generic core: retarget the toggle, renamed radars, 42 new units/7 presets/SAMP-T layout, `remove_vehicle` id-vs-name strip fix; no 414th faction enrichment) | ⚪ WITHDRAWN → re-carve | High (the original mod is dead; unlocks S-400/V4/SAMP-T for everyone) — PR #851 **closed unmerged**. **Reason investigated 2026-07-20:** juanjux tested it and found the Ultimate Compilation is **NOT backward-compatible with Auranis HighDigitSAMs 2.1.0** (the competing successor mod he runs — the S-300 renames collide). A re-carve must first answer which successor mod upstream standardizes on (or support both); not a quick win | N1 ☐ |
| 14 | **Germany - Red Tide campaign publication** (content-only: campaign yaml + miz with routes re-baked as M-113/HandyWind groups, new `Russia 1988` faction, 1-line blufor MPRS add, 44 historical squadron defs; 414th identity stripped from the upstream copy) | 🟡 NEAR | High (a full authored GermanyCW scenario campaign for everyone) — **payload READY** in `docs/dev/upstreaming/red-tide/` (`build_payload.py` regenerates; validated vs dev @ `dce851ea`); needs the current-dev headless validation + PR push from the Windows box (this sandbox can't reach the PR fork) | n/a (content; validated at carve) |
| 15 | Per-squadron DCS country for nation-specific voiceovers + nation-aware pilot names (§23, generic core: `CountryAssigner` + `pilotnames.py`; no 414th faction content) | 🔵 **MERGED 2026-07-19** (PR #854, resolves upstream issue #627; upstream's copy adds `blue/red_country_ids` — adopted fork-side in the 2026-07-19 sync) | Medium/High (mixed-nation CJTF sides get per-nation voices/comms/rosters) | I1 ☑, I5 ☑ |
| 16 | **AI helicopter terrain CFIT trio** (helo cruise waypoints at the dead `heli_cruise_alt_agl` setting; ≤5 NM RADIO terrain-anchor subdivision of long AI helo legs; air-start unit records mirroring the point `alt_type` — all three verified verbatim in upstream `dev`) | 🟡 NEAR | High (AI helos CFIT on every hilly map; the flown Red Tide M1 lost 3 Mi-8 + 1 Mi-24 to it) | C8 ☐ |
| 17 | **Blue-block miz markers load + bind blue** (`MizCampaignLoader`: every marker class also walks the BLUE country block — blue-block ships/SAM/EWR/missile/coastal/offshore markers were silently dropped, 22 authored markers across 7 upstream campaigns never generated (Dynamo's evacuation flotilla, Allied Sword's oil platforms, Falklands task-force ships…) — and a blue-block marker binds the nearest BLUE CP instead of nearest-any; red-block markers keep the coalition-agnostic proximity convention, plus an actionable `generate_ewrs` no-ForceGroup error naming the stranded marker/CP) | ⚪ WITHDRAWN → re-carve — pushed as draft [PR #891](https://github.com/dcs-retribution/dcs-retribution/pull/891) 2026-07-20 (the upstream sweep found **465 dropped markers across 9 campaigns**, normandy_full 352 + normandy_small 91 dominating; the PR flagged the Normandy resurrection as a maintainer judgment call). **Starfire13 reviewed same day** — "352 EWRs in Normandy. Good lord. You could string them together across the channel and walk back to England" (density a non-starter) — **and made the real ask: block-convention consistency** ("For some objects, you can only use one [CJTF block], yet for others, both are acceptable. For example, SAMs have to be defined with CJTF Red, but AAA and static armour groups allow both"); the DM self-closed 25 min later to redo rather than defend the resurrection (the #784→#886 pattern). **Fork answered the consistency ask same day:** the loader's last single-block classes now chain both blocks — `factories` was BLUE-only (the mirror hole: the campaign sweep found **3 shipped red-block factories silently dropped** — TblisiGap, RetakeTheFalklands, operation_allied_sword — now resurrected, headless-verified binding their red bases by proximity), and front-line paths / shipping lanes / cp-convoy spawns (blue-only) + neutral FOBs (red-only) chained with **zero** shipped cross-block instances (pure authoring tolerance); contract-locked in `tests/test_miz_marker_binding.py`. **Re-carve shape:** lead with the reviewer's own consistency story (every class reads both blocks; the block means ownership only for the CP classes + the bounded blue-marker preference), carry the factories fix, and **exclude the Normandy resurrection** — prune the 443 Normandy markers from the two miz in the same PR so shipped generation stays byte-identical, offering a curated subset if upstream wants some of that density back | High (restores authored content in 9 shipped campaigns; kills a silent authoring foot-gun; the consistency framing is now the reviewer's own request) | n/a (tests/test_miz_marker_binding.py + normandy_small headless-verified on the patched loader) |
| 18 | **Ship-launched cruise missile strikes** (generic core of fork [414Ret#599](https://github.com/bradyccox/414Ret/pull/599): `game/cruisemissiles.py` LACM hull set + persisted no-rearm magazine + auto-raid planner, `cruisemissileluadata` emitter, `cruisemissiles` plugin — F10 call-for-fire with marker-text salvo sizing + magazine status — and the `cruise_missiles_state` debrief channel; fork couplings stripped: no ROE-zone gate, no `map_hidden`, no `enabled_when`) | 🔵 IN REVIEW | High (naval land-attack for every campaign; both settings default off) — **PR #872 ready for review 2026-07-19** (opened 2026-07-15 as draft; the branch since gained the review-feedback stagger, un-cull + carrier-escort commits, a dev merge, and the flown **defender launch wake** ported from the fork — alarm-RED near the aimpoint for the flight window, Skynet-adapted; un-drafted after the DM's local 10/10 fly) | n/a (unit-tested both sides; validated on dev @ `ef576acc`: pytest/Black/mypy clean) |
| 19 | **Curated carrier comms** (§65 verbatim: `game/data/carrier_comms.py` per-hull boat cards, `TacanRegistry.alloc_near` nearest-neighbor degrade + `alloc_for_band` marking, `IclsAllocator`, the four `_resolve_*` precedence helpers + flagship hull-naming; NO fork couplings — the port only adds the Pretense allocator-type adaptation the fork doesn't need) | 🔵 IN REVIEW | High (every carrier campaign's CV Ops Data page reads real, stable boat data) — **pushed as draft PR #874**, opened 2026-07-16 | B18 ☐ |
| 20 | **F-14A-135-GR-Early payload `unitType` fix** (upstream's `resources/customized_payloads/F-14A-135-GR-Early.lua` declares `["unitType"] = "F-14A-135-GR"`; pydcs binds payload files by that field, so the whole file never attaches to the Early jet — upstream's Early Tomcat resolves NO presets for any task and auto-plans with an empty loadout. One-line fix; found 2026-07-17 root-causing the fork's own F-14 empty-payload regression, see `414th-loadout-integrity-audit-notes.md` addendum) | 🔵 IN REVIEW — **pushed as draft [PR #889](https://github.com/dcs-retribution/dcs-retribution/pull/889)**, opened 2026-07-20 (the one-liner + a guard test pinning the field AND an armed-BARCAP resolution) | Medium (upstream's Early Tomcat flies every tasking unarmed) | n/a (guarded by `tests/test_f14_loadouts.py`) |
| 21 | **Splash Damage tuned values as upstream's new defaults** (the 2026-07-19 policy's first last-mile carve — and the forensics found upstream's shipped config **internally broken**, not merely hot: the "(%)" rocket spinner was never divided (default 130 applied as a raw ×130), overall_scaling default 3 = 3% with the cluster-bomblet path dividing by 100 a *second* time, static_damage_boost 2000, and the giant-explosion **test mode shipped enabled**. The PR fixes the two ÷100 bugs + test mode and sets the flown 414th values in upstream's own plugin.json → sd3-config architecture: overall 60% · rockets 80% · static boost 1 · blast radius 100% · ground-ordnance wave ×2 · messages+cluster on · big-iron explTable trims (582→450, 100→85) · shaped_charge flags on the 4 HEAT/AP rockets. The fork's settings-locked single-file packaging did NOT travel; fork-only structural deletions (OCA-boost block) deliberately excluded) | 🔵 IN REVIEW — **pushed as [PR #880](https://github.com/dcs-retribution/dcs-retribution/pull/880)**, opened 2026-07-19; both Lua files compile clean under Lua 5.1 | High (every campaign's ground strikes stop over-killing scenery) | n/a (values flown across the fork's campaigns since the buddy-tune) |
| 22 | **Vietnam War Vessels support → v3.2.0** (upstream's VWV support was frozen at v3.0.0: registers the v3.1.0 civilian craft — the 5 Sampan variants + the Junk — and the 5 hulls the mod carries that were never registered (USS Radford DD-446, USS Epperson DD-719, USS Everett F. Larson DD-830, AD-30 Solon Turman, USNS Card T-AKV-40; ids read from the installed mod's own `Database/Navy/*.lua`), adds all 11 to the `faction.py` eject list so a faction citing them degrades cleanly with the mod off, and refreshes the stale labels — wizard checkbox v3.0.0 → v3.2.0 + the 4 faction `requirements` entries that had drifted to v0.9.0/v2.3.0/v3.0.0. Registration-only parity with the fork: deliberately NO unit yamls/prices for the new hulls (the fork hasn't authored them either — the civilian craft's gameplay wiring is the fork-only `civiliantraffic.py`)) | 🔵 IN REVIEW — **pushed as [PR #881](https://github.com/dcs-retribution/dcs-retribution/pull/881)**, opened 2026-07-19; validated on dev @ `acf02b75` (pytest 438 passed / Black / mypy clean). Fork side reconciled same day: the 11 eject entries + the fork's own 4 stale faction strings (usa_1970 v0.9.0, vietnam_1965 v3.0.0, vietnam_1970 + USA 1971 v2.3.0) | Medium/High (every Vietnam-era campaign gets the current mod roster; the stale labels sent players hunting v0.9.0–v3.0.0 downloads) | n/a (registration + version labels; upstream suite green) |
| 23 | **Soviet SHORAD Sborka "Dog Ear" acquisition radar** (the fork's slot-gated + marker-gated `_add_dog_ear_if_needed` in `forcegroup.py`, the SHORAD.yaml Search Radar slot, the 3-way test with the SAM-site/era exclusions; vanilla unit, no faction edits — was never queued here, added the day it shipped) | 🔵 IN REVIEW — **pushed as draft [PR #887](https://github.com/dcs-retribution/dcs-retribution/pull/887)**, opened 2026-07-20; 441 tests green | Medium/High (SA-9/13/15/19 batteries stop being eyeball-only; objective TO&E data) | n/a (unit-tested; generation-covered) |
| 24 | **SAM site layout variety + EWR radar pool — the #791 refresh** (the June branch rebased onto dev @ `acf02b75`, zero conflicts, content unchanged; #791 had closed with zero comments — never reviewed) | 🔵 IN REVIEW — **pushed as draft [PR #892](https://github.com/dcs-retribution/dcs-retribution/pull/892)**, opened 2026-07-20; re-validated same day (68 preset groups, 131 factions, 0 bad refs, 438 tests) | High (legacy SA-2/3/5/6 batteries become real sites; EWR buy menu stops offering SAM-system radars) | n/a (resources-only) |
| 25 | **§60 SAM guidance-radar redundancy** (21 layout yamls ×23 slots `unit_count` 1→2 + second radar positions grafted into the 5 shared templates — fork-only P-14 groups NOT carried; the 29-pair lockstep test, SAMP/T row dropped as HDS-Ultimate-only; the realism-notes rationale attached in the PR body per the roadmap's "balance opinion" classification) | 🔵 IN REVIEW — **pushed as draft [PR #893](https://github.com/dcs-retribution/dcs-retribution/pull/893)**, opened 2026-07-20, **stacked on #892**; 467 tests green | Medium (balance opinion, rationale attached; upstream may park it — offered explicitly) | B12 ☐ |
| 26 | **Squadron country surfaced — campaign yaml `country:` pin + Air Wing dialog Country selector** (§23 follow-on to the merged #854; `SquadronConfig.country` → same-nation-only preset pick with def-generator fallthrough + `override_squadron_defaults` stamp, the `SquadronCountrySelector` under Livery, preset dropdowns showing each preset's nation, Save/Load Config country round-trip, the livery stale-squadron bind_data fix. **This is literally the upstream Discord ask** — Starfire's "set the squadron nation in the campaign yaml … get a preset for that nation if available, or a randomly generated squadron set to that country", Toad's "drop down … under livery basically" — carved the same day the thread ran; the DS campaign pins stay fork-side) | 🔵 IN REVIEW — **pushed as draft [PR #896](https://github.com/dcs-retribution/dcs-retribution/pull/896)**, opened 2026-07-20 on dev @ `3760cf2a` (447 tests / black / mypy green; upstream carries the game-side tests — the offscreen-Qt selector test stays fork-side, no qt_ui test precedent upstream, the #884 lupa pattern); **draft until the fork's I6 app pass** (#874 pattern) | High (asked for by name in upstream's Discord the day it was built) | I6 ☐ |

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

### 8. Recon fog-of-war — 🔵 IN REVIEW (pushed as PR #828; rebased + un-drafted 2026-07-19)
- **Pushed:** carved + opened upstream as **[PR #828](https://github.com/dcs-retribution/dcs-retribution/pull/828)**
  (2026-06-23, +473/-14). **Rebased 2026-07-19** onto dev @ `acf02b75` and squashed to a
  single commit (the branch had been tracking dev via merge commits), re-validated on that
  base (Black/mypy clean, pytest 451 passed — upstream's new ship-movement test double
  gained the minimal `game.settings` chain `known_for` consults for enemy viewers), and
  **marked ready for review** (was draft). Awaiting a maintainer review; no action owed
  beyond responding to feedback when it arrives.
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

### 18. Ship-launched cruise missile strikes — 🔵 IN REVIEW (PR #872; ready-for-review 2026-07-19)
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

## 🕐 Last-mile queue + merge-discipline divergences

> **2026-07-19 policy: nothing is permanently fork-only.** The old ⛔ section split
> into two different things. **Last-mile items** are upstreamable once packaged —
> each carries its upstream story in the
> [roadmap's last-mile queue](414th-community-contribution-roadmap.md) (Splash
> Damage defaults = queue item 21 above; Iran pack re-carve; doctrine
> defaults-with-rationale; the C-130J physics constants and TIC tuning riding their
> Tier-3 feature carves; campaign content after identity-strip passes).
> **Merge-discipline divergences** (below) are fork resolutions to *preserve on
> dev-pulls* — either upstream already ruled on them, or they exist because the two
> codebases' architectures differ. They are not upstream candidates, but for
> concrete recorded reasons, not by category.

- **C-130J EW (`c130j`) plugin de-conflict on SOF inserts**
  (`game/missiongenerator/luagenerator.py` `_sof_c130_present`): fork glue between
  two fork features — travels with the C-130J framework carve, never alone.
- **Splash Damage 414th build packaging** — the *values* are queue item 21 (ship
  upstream as new defaults with the mile-away-building-damage rationale). The
  fork-side *packaging* (single pinned file, settings locked, no `sd3-config.lua`)
  stays a fork choice: do not overwrite the pinned file from upstream, and do not
  reintroduce the config layer locally, even after the values land upstream.
- **AGM-65 Maverick date-fallback → Mk-20 Rockeye** (`resources/weapons/standoff/AGM-65A.yaml`,
  `fallback: Mk-20 Rockeye`). **Upstream ruled on this** (PR #847, Druss99: fallbacks
  target AI mission performance; Walleye preferred), so #847's AGM-65A was reverted
  upstream. Keep the Rockeye reroute on the fork — do NOT let a future carve or
  dev-pull "fix" it back to Walleye, and do not re-propose without new evidence.
- **#879 alarm-state adaptation** (2026-07-19 sync): upstream forces GREEN/RED on
  every TGO group via `perf_red_alert_state`; the fork removed that toggle (#231 —
  MANTIS owns networked SAM alarm state at runtime), so the fork's
  `set_alarm_state` writes RED only for ships (`force_red`) and dedicated EWR
  sites, and nothing otherwise (DCS AUTO). Preserve on every dev-pull;
  `tests/missiongenerator/test_ewr_enroute_task.py` pins the fork contract.
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
