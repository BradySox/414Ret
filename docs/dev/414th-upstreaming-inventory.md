# 414th Upstreaming Inventory

> Test paths shown ~~struck through~~ were deleted along with the feature they covered. They are left visible because the citation is part of the record; do not go looking for the file. Audited 2026-08-17.

Every generic fix the 414th carries that **isn't** upstreamed is a guaranteed
merge conflict on every `dcs-retribution/dcs-retribution` `dev` pull, forever.
The cure is to carve the non-fork-specific fixes out into PRs against the 414th's
PR fork (`bradyccox/dcs-retribution`) so they either land upstream or at least
live on a clean branch that rebases cleanly. This file is the **inventory +
queue**: what's genuinely generic, how ready it is, and — just as important —
what is fork-specific and must **never** go upstream.

> **Scope note.** This file is the *tactical carve queue* for the generic **bug-fixes**.
> Since **2026-08-20** it also carries the [upstream issue ledger](#upstream-issue-ledger) —
> the standing triage of `dcs-retribution/dcs-retribution/issues`, swept for the first time
> that day.
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

## 2026-07-20 standards audit (upstream dev-process adoption applied to the open PRs)

The day the upstream Contributing / dev-guide / modding wiki pages were adopted as the
fork's own standards (CLAUDE.md Conventions), the 21 open upstream PRs were audited
against them. Baseline: **compliant** — all dev-targeted via the PR fork, one focused
change per PR, upstream gates validated per PR, crowded zones respected. Gaps + calls:

- **Changelog entries** (their Developer's Guide + PR template ask): most open carves
  shipped without a `changelog.md` note. **APPLIED 2026-07-20** (per the DM call to
  draft them all and apply from the dev machine): all 14 open carves missing an entry
  got one, committed additively to their PR branches (#788 #792 #794 #806 #828 #874
  #881 #883 #886 #887 #889 #890 #892 #893). The flagged wordings were re-grounded in
  the real diffs before pasting — #788 covers any fast-forward flight running off its
  plan (not just air spawns), #806 is the scatter *band* + patrol floor (not "cruise
  altitude config"), and #892 **tightens** the EWR pool (the draft said "wider"; the
  layout's SearchRadar fallbacks are removed while period factions gain the new site
  presets). Verify-first caught that #872/#873/#880/#884 already carried theirs (the
  wave carves post-date the adopted rule); #882 stays exempt (dev-only harness). The
  two closed carves were never applied: #891 (**re-carve DROPPED 2026-08-05** — the wiki's
  block spec table and upstream's loader already agree on all 19 classes, so there is no
  bug to carve; see item 17) and #885 (**closed-ceded
  2026-07-20**: Druss99 has his own victory-conditions branch and asked to take the
  feature — a drift-watch item vs fork §75 when his lands, not a re-carve). The
  drafts handoff file is deleted per its own banner. New carves carry an entry from
  birth per the adopted standard.
- **#881 review loop**: in motion via fork PR #687 (the USNS Card data fix +
  `tools/verify_mod_export.py`); the held replies post after the desktop export run.
- **Pre-wave PRs #788/#792/#794/#806**: freshness-check against current dev when next
  touched (the #791 went-stale lesson; #892 is the refresh pattern).
- **#828**: in re-review — additive commits only from here (their large-PR
  no-force-push rule).
- **#886 icons/banners** (Modded-Unit-Support step 9): optional — the fork ships no
  Shahed UI art either (checked 2026-07-20); author fork-side first if wanted.

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
| 17 | **Blue-block miz markers load + bind blue** (`MizCampaignLoader`: every marker class also walks the BLUE country block — blue-block ships/SAM/EWR/missile/coastal/offshore markers were silently dropped, 22 authored markers across 7 upstream campaigns never generated (Dynamo's evacuation flotilla, Allied Sword's oil platforms, Falklands task-force ships…) — and a blue-block marker binds the nearest BLUE CP instead of nearest-any; red-block markers keep the coalition-agnostic proximity convention, plus an actionable `generate_ewrs` no-ForceGroup error naming the stranded marker/CP) | ⚪ WITHDRAWN → re-carve — pushed as draft [PR #891](https://github.com/dcs-retribution/dcs-retribution/pull/891) 2026-07-20 (the upstream sweep found **465 dropped markers across 9 campaigns**, normandy_full 352 + normandy_small 91 dominating; the PR flagged the Normandy resurrection as a maintainer judgment call). **Starfire13 reviewed same day** — "352 EWRs in Normandy. Good lord. You could string them together across the channel and walk back to England" (density a non-starter) — **and made the real ask: block-convention consistency** ("For some objects, you can only use one [CJTF block], yet for others, both are acceptable. For example, SAMs have to be defined with CJTF Red, but AAA and static armour groups allow both"); the DM self-closed 25 min later to redo rather than defend the resurrection (the #784→#886 pattern). **Fork answered the consistency ask same day:** the loader's last single-block classes now chain both blocks — `factories` was BLUE-only (the mirror hole: the campaign sweep found **3 shipped red-block factories silently dropped** — TblisiGap, RetakeTheFalklands, operation_allied_sword — now resurrected, headless-verified binding their red bases by proximity), and front-line paths / shipping lanes / cp-convoy spawns (blue-only) + neutral FOBs (red-only) chained with **zero** shipped cross-block instances (pure authoring tolerance); contract-locked in `tests/test_miz_marker_binding.py`. **⛔ RE-CARVE DROPPED 2026-08-05 (DM call) — the premise was wrong.** Before building it, the Custom-campaigns wiki was finally consulted (per the standing "read it FIRST for campaign miz/yaml work" rule) and it carries a **"Unit Type Quick Reference" spec table assigning a required CJTF block per object class**. Upstream's loader matches that table **exactly on all 19 classes** — Red: EWR / long+medium+short SAM / ship / missile / coastal / offshore / neutral-FOB · Blue: factory · Either: AAA / armor / ammo / strike / comms / power / command-center / FOB / invisible-FOB. **Zero discrepancies, so there is no bug to carve:** a blue-block SAM marker is dropped because the author placed it in the block the documentation forbids, and #891's "silently dropped authored content" framing was reading authoring errors as engine faults. Uniform-"Either" is a **spec change** (loader + wiki table) and a maintainer design call, not a fix to ship unasked. **Measured while establishing this** (probes: `MizCampaignLoader`'s own constants over every upstream campaign miz): the true content delta is **483 objects across 12 campaigns**, of which **443 (91 %) is Normandy** — `normandy_full` 352 (336 Tunguska + 9 Scud + 7 Silkworm, all under CJTF Blue; its RED block holds only 10 SKP-11 FOB markers, and its blue block also carries 656 `S-300PS 64H6E sr` groups matching **no** marker class at all) and `normandy_small` 91. Everything outside Normandy is **40 objects across 10 campaigns**. ⚠️ **Fork follow-up, still open:** the fork's read-both rule means **414Ret generates 336 short-range SAM sites on `normandy_full` where upstream generates 0** (75 vs 0 on `normandy_small`) — an unaudited content change from #590, not yet confirmed end-to-end through a theater load | n/a — dropped | n/a |
| 18 | **Ship-launched cruise missile strikes** (generic core of fork [414Ret#599](https://github.com/bradyccox/414Ret/pull/599): `game/cruisemissiles.py` LACM hull set + persisted no-rearm magazine + auto-raid planner, `cruisemissileluadata` emitter, `cruisemissiles` plugin — F10 call-for-fire with marker-text salvo sizing + magazine status — and the `cruise_missiles_state` debrief channel; fork couplings stripped: no ROE-zone gate, no `map_hidden`, no `enabled_when`) | 🔵 IN REVIEW | High (naval land-attack for every campaign; both settings default off) — **PR #872 ready for review 2026-07-19** (opened 2026-07-15 as draft; the branch since gained the review-feedback stagger, un-cull + carrier-escort commits, a dev merge, and the flown **defender launch wake** ported from the fork — alarm-RED near the aimpoint for the flight window, Skynet-adapted; un-drafted after the DM's local 10/10 fly) | n/a (unit-tested both sides; validated on dev @ `ef576acc`: pytest/Black/mypy clean) |
| 19 | **Curated carrier comms** (§65 verbatim: `game/data/carrier_comms.py` per-hull boat cards, `TacanRegistry.alloc_near` nearest-neighbor degrade + `alloc_for_band` marking, `IclsAllocator`, the four `_resolve_*` precedence helpers + flagship hull-naming; NO fork couplings — the port only adds the Pretense allocator-type adaptation the fork doesn't need) | 🔵 IN REVIEW | High (every carrier campaign's CV Ops Data page reads real, stable boat data) — **pushed as draft PR #874**, opened 2026-07-16 | B18 ☐ |
| 20 | **F-14A-135-GR-Early payload `unitType` fix** (upstream's `resources/customized_payloads/F-14A-135-GR-Early.lua` declares `["unitType"] = "F-14A-135-GR"`; pydcs binds payload files by that field, so the whole file never attaches to the Early jet — upstream's Early Tomcat resolves NO presets for any task and auto-plans with an empty loadout. One-line fix; found 2026-07-17 root-causing the fork's own F-14 empty-payload regression, see `414th-loadout-integrity-audit-notes.md` addendum) | 🔵 IN REVIEW — **pushed as draft [PR #889](https://github.com/dcs-retribution/dcs-retribution/pull/889)**, opened 2026-07-20 (the one-liner + a guard test pinning the field AND an armed-BARCAP resolution) | Medium (upstream's Early Tomcat flies every tasking unarmed) | n/a (guarded by `tests/test_f14_loadouts.py`) |
| 21 | **Splash Damage tuned values as upstream's new defaults** (the 2026-07-19 policy's first last-mile carve — and the forensics found upstream's shipped config **internally broken**, not merely hot: the "(%)" rocket spinner was never divided (default 130 applied as a raw ×130), overall_scaling default 3 = 3% with the cluster-bomblet path dividing by 100 a *second* time, static_damage_boost 2000, and the giant-explosion **test mode shipped enabled**. The PR fixes the two ÷100 bugs + test mode and sets the flown 414th values in upstream's own plugin.json → sd3-config architecture: overall 60% · rockets 80% · static boost 1 · blast radius 100% · ground-ordnance wave ×2 · messages+cluster on · big-iron explTable trims (582→450, 100→85) · shaped_charge flags on the 4 HEAT/AP rockets. The fork's settings-locked single-file packaging did NOT travel; fork-only structural deletions (OCA-boost block) deliberately excluded) | ⛔ **WITHDRAWN — [PR #880](https://github.com/dcs-retribution/dcs-retribution/pull/880) CLOSED 2026-08-06 (DM call: "it's a preference we use, not everyone else")**. The tuning is a 414th taste call, not a defect owed upstream, so it stays fork-side permanently — **a named exception to the everything-upstreamable policy**; do not re-open without a fresh call. **Two genuine upstream bugs found in the closing audit are now carried by NOTHING and are re-carve candidates on their own merits:** (a) `sd3-config` assigns `cluster_bomblet_reduction_modifier` but the script reads `cluster_bomblet_reductionmodifier`, so the "Bomblets Count Reduction Modifier" toggle is inert (one-line fix, sitting on the closed branch `splash-damage/sane-defaults` @ `c6203d5`); (b) upstream's parked-aircraft OCA block calls **`getAGL()`, defined nowhere in their tree** — grep is zero — so it raises `attempt to call a nil value` for every object past `cascade_damage_threshold`, inside the `world.searchObjects` `ifFound` callback. The fork's restored copy computes AGL inline instead of copying that call | n/a (fork-only by decision) | n/a (values flown across the fork's campaigns since the buddy-tune) |
| 22 | **Vietnam War Vessels support → v3.2.0** (upstream's VWV support was frozen at v3.0.0: registers the v3.1.0 civilian craft — the 5 Sampan variants + the Junk — and the 5 hulls the mod carries that were never registered (USS Radford DD-446, USS Epperson DD-719, USS Everett F. Larson DD-830, AD-30 Solon Turman, USNS Card T-AKV-40; ids read from the installed mod's own `Database/Navy/*.lua`), adds all 11 to the `faction.py` eject list so a faction citing them degrades cleanly with the mod off, and refreshes the stale labels — wizard checkbox v3.0.0 → v3.2.0 + the 4 faction `requirements` entries that had drifted to v0.9.0/v2.3.0/v3.0.0. Registration-only parity with the fork: deliberately NO unit yamls/prices for the new hulls (the fork hasn't authored them either — the civilian craft's gameplay wiring is the fork-only `civiliantraffic.py`)) | 🔵 IN REVIEW — **pushed as [PR #881](https://github.com/dcs-retribution/dcs-retribution/pull/881)**, opened 2026-07-19; validated on dev @ `acf02b75` (pytest 438 passed / Black / mypy clean). Fork side reconciled same day: the 11 eject entries + the fork's own 4 stale faction strings (usa_1970 v0.9.0, vietnam_1965 v3.0.0, vietnam_1970 + USA 1971 v2.3.0) | Medium/High (every Vietnam-era campaign gets the current mod roster; the stale labels sent players hunting v0.9.0–v3.0.0 downloads) | n/a (registration + version labels; upstream suite green) |
| 23 | **Soviet SHORAD Sborka "Dog Ear" acquisition radar** (the fork's slot-gated + marker-gated `_add_dog_ear_if_needed` in `forcegroup.py`, the SHORAD.yaml Search Radar slot, the 3-way test with the SAM-site/era exclusions; vanilla unit, no faction edits — was never queued here, added the day it shipped) | 🔵 IN REVIEW — **pushed as draft [PR #887](https://github.com/dcs-retribution/dcs-retribution/pull/887)**, opened 2026-07-20; 441 tests green | Medium/High (SA-9/13/15/19 batteries stop being eyeball-only; objective TO&E data) | n/a (unit-tested; generation-covered) |
| 24 | **SAM site layout variety + EWR radar pool — the #791 refresh** (the June branch rebased onto dev @ `acf02b75`, zero conflicts, content unchanged; #791 had closed with zero comments — never reviewed) | 🔵 IN REVIEW — **pushed as draft [PR #892](https://github.com/dcs-retribution/dcs-retribution/pull/892)**, opened 2026-07-20; re-validated same day (68 preset groups, 131 factions, 0 bad refs, 438 tests) | High (legacy SA-2/3/5/6 batteries become real sites; EWR buy menu stops offering SAM-system radars) | n/a (resources-only) |
| 25 | **§60 SAM guidance-radar redundancy** (21 layout yamls ×23 slots `unit_count` 1→2 + second radar positions grafted into the 5 shared templates — fork-only P-14 groups NOT carried; the 29-pair lockstep test, SAMP/T row dropped as HDS-Ultimate-only; the realism-notes rationale attached in the PR body per the roadmap's "balance opinion" classification) | 🔵 IN REVIEW — **pushed as draft [PR #893](https://github.com/dcs-retribution/dcs-retribution/pull/893)**, opened 2026-07-20, **stacked on #892**; 467 tests green | Medium (balance opinion, rationale attached; upstream may park it — offered explicitly) | B12 ☐ |
| 26 | **Squadron country surfaced — campaign yaml `country:` pin + Air Wing dialog Country selector** (§23 follow-on to the merged #854; `SquadronConfig.country` → same-nation-only preset pick with def-generator fallthrough + `override_squadron_defaults` stamp, the `SquadronCountrySelector` under Livery, preset dropdowns showing each preset's nation, Save/Load Config country round-trip, the livery stale-squadron bind_data fix. **This is literally the upstream Discord ask** — Starfire's "set the squadron nation in the campaign yaml … get a preset for that nation if available, or a randomly generated squadron set to that country", Toad's "drop down … under livery basically" — carved the same day the thread ran; the DS campaign pins stay fork-side) | 🔵 IN REVIEW — **pushed as draft [PR #896](https://github.com/dcs-retribution/dcs-retribution/pull/896)**, opened 2026-07-20 on dev @ `3760cf2a` (453 tests / black / mypy green after the operator-trim second commit; upstream carries the game-side tests — the offscreen-Qt selector test stays fork-side, no qt_ui test precedent upstream, the #884 lupa pattern); **I6 VERIFIED 2026-07-20** (user pass: "896 is flown and good") but **the draft is deliberately HELD through the upstream PR freeze** — DM call same day ("don't flip it just in case it was after the lock"; #896 was opened the day the no-new-PRs-until-next-beta freeze was learned), un-draft only on a fresh explicit call once the freeze lifts | High (asked for by name in upstream's Discord the day it was built) | I6 ☑ |
| 27 | **Upstream dead-code cleanup** (9 modules referenced nowhere in the whole tree — `game/aircraftparkinglocation.py` is a **0-byte file**; `game/commander/tasks/compound/frontlinedefense.py` was superseded by `frontlinecas.py`'s `PlanFrontLineCas` and is no longer reachable from the HTN root; `game/missiongenerator/airconflictdescription.py`; `game/savecompat.py` (an unused save-compat decorator utility); and five orphaned Qt widgets — `QDebriefingInformation.py`, `QF14FlightComputerEditor.py`, `QFlightAircraftEditor.py`, `QGroundObjectReplacementMenu.py`, `payload/propertyselector.py` (superseded by `propertycombobox.py` in §24). **All 9 are upstream-authored** (Dan Albert / Khopa, 2019–2023) — this is upstream debt, not fork debt, which is why it carves rather than lands fork-side: deleting them here would only manufacture merge friction on every dev-pull. Found by the 2026-08-02 code audit's whole-tree reference sweep (1,189 files); each was confirmed dead against `pydcs_extensions/` and `client/` too, not just `game/`+`qt_ui/`) | 🟢 READY — **not yet pushed**; hold until the upstream PR freeze is confirmed lifted (see the freeze banner in CLAUDE.md) | Low (no behavior change; pure surface reduction — but it removes a stale-comment trap: `nextaction.py` credited defensive CAS to the dead `FrontLineDefense`, fixed fork-side 2026-08-02) | n/a (deletions only; upstream suite must stay green) |
| 28 | **One theater tanker per boom/probe refuel method** (U15, reinstated fork-side 2026-08-17 as 414Ret#877: `ProposedFlight.refuel_methods` + `PackageBuilder._required_refuel_methods` precedence, `PlanRefueling` counting the coalition's methods, and `TANKER_ORBIT_SPACING` so a second tanker does not get the first one's racetrack. First tanker unconstrained and extras `optional`, so it can never plan fewer than upstream does) | 🟡 NEAR | High — **answers upstream issue [#243](https://github.com/dcs-retribution/dcs-retribution/issues/243), open since 2024**, whose recovery-tanker half upstream fixed in 2025 and whose theater half it did not. A mixed boom/probe wing currently has half its aircraft unable to tank. Depends on the fork's boom/probe data model (`AircraftType.tanker_refuel_types`, `can_refuel_from`), which upstream does **not** have — that model is the carve's first commit, not an assumption. Raffson proposed a coarser shape in-thread (count squadrons with unique aircraft); lead the PR with why method-counting is the smaller correct number and offer his as the fallback | B76 ☐ |
| 29 | **Per-airframe player startup allowance** (`startup_minutes:` on the aircraft yaml overriding `player_startup_time`, fork-side 2026-08-17 as 414Ret#878; 4 sourced values — F-16C 4, F-15E/ESE 3, F-4E 9 — every other airframe falling back, AI untouched at 2 min) | 🟢 READY | Medium/High — **answers upstream issue [#214](https://github.com/dcs-retribution/dcs-retribution/issues/214), open since 2023**, in the shape the maintainer asked for **twice** ("I think this should be defined in the aircraft yamls"). Fully self-contained: no fork couplings, no Lua, 12 tests. The carve should keep the design note (`414th-startup-times-notes.md`) — the sourcing rule is the point, not the four numbers, and the test that fails on an unsourced value is what stops the table filling with guesses. Carry Raffson's own E-3 ≈ 6 min data point in as a fifth value if he still stands behind it | B77 ☐ |
| 30 | **The briefed CSAR hover must clamp to `csar_player_hover_height`** — a defect in upstream's **own open PR [#929](https://github.com/dcs-retribution/dcs-retribution/pull/929)**, not a fork feature | 🕐 LAST-MILE | Medium — #929 Phase 5 turns MOOSE's hardcoded 20 m winch ceiling into a 5–100 m setting but leaves the pickup waypoint's briefed altitude fixed, so below ~19 m the mission briefs a hover the winch refuses and DCS says nothing. The fork's `briefed_hover_altitude()` returns `min(50 ft, 0.8 × setting)`. **This is a comment on #929, not a PR** — report it on the thread rather than opening anything, which also sidesteps the freeze. Do it before #929 merges, or it becomes a bug upstream has shipped | B74 ☐ |
| 31 | **Strike on a fully-destroyed objective divides by zero** (`add_strike_tasks` computes `len(units) / len(targets)`; an objective whose units are all dead leaves the strike waypoint with no targets and mission generation dies for the turn. Early return matching `add_bombing_tasks`, plus a regression test) | 🔵 IN REVIEW — **draft [PR #950](https://github.com/dcs-retribution/dcs-retribution/pull/950)**, opened 2026-08-20 on dev @ `59719b24`; Black / mypy 491 / pytest 453 green | High — **answers open upstream issue [#948](https://github.com/dcs-retribution/dcs-retribution/issues/948)**; the fork has carried the fix since 2026-06-17 (`167d4e6f8`), two months before it was reported there | n/a (unit-tested) |
| 32 | **Generic AAA sites auto-spawn a search radar** | ⛔ **WITHDRAWN — duplicate.** [PR #951](https://github.com/dcs-retribution/dcs-retribution/pull/951) opened and closed 2026-08-20: [PR #902](https://github.com/dcs-retribution/dcs-retribution/pull/902) (red-one1, 2026-07-22) already fixes it, and more completely — a dedicated `AAARadar` class and the Fire Can reclassified, so the slot cannot match a SAM search radar at all. Our `fill: false` is a subset of it | — (adopt #902's shape fork-side instead) | n/a |
| 33 | **Native DTC cartridge support in pydcs** — the per-unit `DTC` block + the `DTC/*.dtc` files. pydcs drops the block on re-save (units re-serialize from parsed fields only) and cannot author a cartridge, so §74 carries two shims in `game/missiongenerator/dtc/cartridge.py`: a `FlyingUnit.dict` wrap and a post-`Mission.save` zip append. **This is a pydcs PR, not a Retribution one** — [dcs-retribution/pydcs#39](https://github.com/dcs-retribution/pydcs/pull/39) — **#34 was closed in its favour 2026-08-22** (same change, one commit, short body; the long thread was a poor entry point). The dcs-retribution PR freeze does not bind pydcs | 🔵 IN REVIEW — opened non-draft 2026-08-22 on `retribution @ 3a79b8e`. Carries Starfire13's F-14B(U) correction: the DTC flag is set for the `F-14BU` rewrite alone. mypy, flake8 and the 141-test suite green | Medium (when it lands and the pin moves, `cartridge.py` shrinks to the model + builders) | n/a (pydcs-side `tests/test_dtc.py`; §74 behavior rides the §74 rows) |

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

### 2. DEAD reachability gate on follow-on strikes — ⚫ WITHDRAWN (reverted fork-side 2026-08-09)
- **What:** a follow-on strike behind a SAM belt is deferred until the belt is
  actually down, instead of trusting an optimistic DEAD clear. The DEAD itself is
  still tasked (with SEAD escort).
- **Why upstream cares:** this is upstream-core HTN behavior, not a 414th
  concept — a correctness fix to the stock planner.
- **Files:** `dead_can_reach` geometry + `apply_effects` routing in
  `game/commander/.../theatercommander.py`.
- **Tests:** ~~`tests/test_dead_planning.py`~~ (deleted with the feature).
- **⚫ WITHDRAWN 2026-08-09:** the planner re-convergence deleted this fork-side, so
  there is nothing left to carve. Rebuild from git history first if it is ever re-wanted;
  the collision note below still applies to whoever does.
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
- **Tests:** ~~`tests/test_support_orbit.py`~~.
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
  platform. (The `alive_for`/`alive_at_last_recon` BDA damage-lag it used to activate was
  removed fork-side 2026-08-18 — re-scope this item before carving it.)
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
  (~~`tests/test_combat_sar_scoring.py`~~).
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
- **Source of truth:** `docs/dev/design/414th-csar-notes.md`, features doc §21.

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
- **Tests:** ~~`tests/test_cruisemissiles.py`~~,
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

- **`resources/scripts/MissionScripting.original.lua` is untracked + gitignored**
  (2026-08-02). Upstream tracks this file, but it is not source: `liberation_install.py`
  `replace_mission_scripting_file()` **writes** it at launch by copying the file out of
  *the running machine's* DCS install, so tracking it pushes one person's DCS state to
  everyone and leaves every contributor's tree permanently dirty. Worse, the copy
  upstream ships is not a stock DCS file at all — its `sanitizeModule('os'/'io'/'lfs')`
  calls are commented out (it is a stale snapshot of an *old Retribution replacement*),
  so "Restore original" writes a **desanitized** `MissionScripting.lua` back to DCS
  while reporting success. Untracked here so each install captures its own faithful
  stock backup on first launch; `restore_original_mission_scripting()` already guards
  on `os.path.isfile`, so an absent backup degrades to a no-op. **Upstream carve
  candidate** (untrack it there too, or at minimum replace the seed with a genuine
  stock file) — not yet queued because it needs a decision from upstream on whether
  they want the seed at all. On a dev-pull, keep the file untracked: if a merge
  re-adds it, `git rm --cached` it again.
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

## Upstream issue ledger

> **First sweep 2026-08-20.** Before it the fork had never read
> `dcs-retribution/dcs-retribution/issues` as a list. Six issue numbers appeared anywhere in
> `docs/` — #104, #214, #243, #627, #863, #865 — and every one was found while doing something
> else. The Queue above stays the PR queue; this is the standing issue triage beside it.

Baseline at the sweep: **60 open issues**, oldest from 2023-01. Rows marked ✔ were checked
against the fork's own files. Rows marked · are a title/body match only and need a code check
before anyone acts on them.

**Freeze note — DM call 2026-08-20: the upstream PR freeze does not bind a PR that addresses
something on this list.** "Forget the PR freeze if its addressing something on this list." That is
a scoped exception, not a lift: a carve with no open upstream issue behind it still waits. The
freeze itself is still only lifted by the DM (CLAUDE.md).

### A. Fixed fork-side, still open upstream

| Issue | Their state | Fork state | Action |
|---|---|---|---|
| ✔ [#948](https://github.com/dcs-retribution/dcs-retribution/issues/948) Division by zero in `add_strike_tasks` | Bug, opened 2026-08-16, unresolved | Fixed **2026-06-17** in `167d4e6f8`, two months before they hit it. `add_strike_tasks` returns early when `waypoint.targets` is empty instead of dividing by `len(targets)`; `tests/missiongenerator/aircraft/test_strikeingress.py` pins it | **DONE — draft [PR #950](https://github.com/dcs-retribution/dcs-retribution/pull/950)**, opened 2026-08-20 under the freeze exception above. Carries the guard, the regression test and a changelog note; validated on dev @ `59719b24` (Black, mypy 491 files, pytest 453 passed). The PR body **offers the fix without claiming the diagnosis** — the reporter states their motor pool is filled, so whether their save takes the empty-target path is unverified, and it asks them to re-test against their attachment |
| ✔ [#901](https://github.com/dcs-retribution/dcs-retribution/issues/901) AAA sites get inappropriate search radars | Bug, opened 2026-07-22, unresolved | Fixed **2026-06-23** in `9ed1b2ac0` — `fill: false` on the `AAA_Site.yaml` radar slot, so a generic AAA site stays optically guided instead of auto-filling whatever `SearchRadar` the faction owns | ⛔ **WITHDRAWN — [PR #951](https://github.com/dcs-retribution/dcs-retribution/pull/951) was a DUPLICATE and was closed the same day.** red-one1 had already opened **[PR #902](https://github.com/dcs-retribution/dcs-retribution/pull/902)** on 2026-07-22, the day they filed the issue, and it is the better fix: it adds a dedicated `UnitClass.AAA_RADAR`, reclassifies the two SON-9 Fire Can variants out of `SearchRadar`, and sets the slot to `unit_classes: [AAARadar]` **plus** `fill: false`. Our one-line `fill: false` is a strict subset — it stops the auto-fill but leaves the slot still able to match a SAM search radar from a bundled preset. **Adopted fork-side 2026-08-20** as [414Ret#917](https://github.com/BradySox/414Ret/pull/917): `UnitClass.AAA_RADAR` added, both Fire Can variants reclassified, and both generic gun-AAA layouts narrowed to it — extended past #902 to `Cold_War_Flak_Site.yaml`, which upstream does not touch. This is the row that exposed the cross-reference hole; see *Re-running the sweep* |

Both are now queue items 31 and 32.

### B. A fork feature answers an open issue

Carve candidates. All freeze-bound.

| Issue | Fork feature | State |
|---|---|---|
| ✔ [#753](https://github.com/dcs-retribution/dcs-retribution/issues/753) Auto-hide mobile SAMs on MFD | §7 | **Closed as duplicate 2026-08-20 by BradySox**, mid-sweep. §7 is still fork-only: PR #794 self-closed on review because the reviewer wanted the behavior behind an option, and the fork has none — `hide_on_mfd` defaults by task type with a per-yaml override (`game/armedforces/forcegroup.py:163`, `:528`). **Adding the setting is the re-carve precondition**, closed issue or not |
| ✔ [#715](https://github.com/dcs-retribution/dcs-retribution/issues/715) Cargo/troop aircraft have no missions | §76 | Already carved as **open PR #884** (un-drafted). The PR does not reference the issue — linking it costs a comment and is not a new PR |
| ✔ [#561](https://github.com/dcs-retribution/dcs-retribution/issues/561) Frontline unit naming | §59 | The title is about naming; the body asks for Tiresias, which turns off AI for ground units far from opposing aircraft. §59 is that, built natively (`game/missiongenerator/aisleepluadata.py`, `perf_ground_ai_sleep`). We solved the problem the naming request was a workaround for. ⚠️ **Already claimed upstream** by draft [PR #568](https://github.com/dcs-retribution/dcs-retribution/pull/568) (cedriclmenard), which ports Tiresias itself — do not carve §59 against this issue without reading it first |
| ✔ [#864](https://github.com/dcs-retribution/dcs-retribution/issues/864) Configurable tanker/AWACS TACAN, freq, callsign | partial | Fork has squadron `callsign:` (`game/squadrons/squadrondef.py:44`). TACAN and frequency are not configurable — 1 ask of 3 |
| · [#479](https://github.com/dcs-retribution/dcs-retribution/issues/479) Escort flight improvements | partial | The fork fixed the pre-join ROE and escort release/spend; the join-waypoint geometry the issue leads with is untouched |
| [#865](https://github.com/dcs-retribution/dcs-retribution/issues/865) Realistic carrier recovery heading | §88 | Known. Built from geofffranks' `12d71346`; he is doing it upstream — drift-watch, not a carve |
| [#863](https://github.com/dcs-retribution/dcs-retribution/issues/863) / [#862](https://github.com/dcs-retribution/dcs-retribution/issues/862) Per-pilot modex / livery | §62 + parked | Known. §62 sequences per squadron and does **not** close #863; the per-pilot work is built and unpushed |
| [#104](https://github.com/dcs-retribution/dcs-retribution/issues/104) CSAR as a mission type | CSAR | Known. Answered by upstream's own open PR #929, which the fork re-adopts by phase |
| [#243](https://github.com/dcs-retribution/dcs-retribution/issues/243) Multiple tankers per refuel method | queue item 28 | Known |
| [#214](https://github.com/dcs-retribution/dcs-retribution/issues/214) Configurable startup times | queue item 29 | Known |

### C. Open gaps the fork shares

Build candidates, fork-first. Nothing here is a carve today.

| Issue | Fork state |
|---|---|
| ✔ [#869](https://github.com/dcs-retribution/dcs-retribution/issues/869) UI-configurable tanker speed | No tanker-speed setting exists fork-side |
| ✔ [#586](https://github.com/dcs-retribution/dcs-retribution/issues/586) Restrict frontline non-AD units from engaging air | Fork has the `manpads` setting only |
| ✔ [#244](https://github.com/dcs-retribution/dcs-retribution/issues/244) Customizable savegame folders | §66 archives generated missions; it does not make `layouts` / `groups` / `scripts` user-overridable |
| · [#734](https://github.com/dcs-retribution/dcs-retribution/issues/734) Aircraft spawn on occupied ramp slots | **Check this first.** A crash-on-spawn bug, and whether the fork carries it is unverified. §64 covers carrier decks only |
| · [#629](https://github.com/dcs-retribution/dcs-retribution/issues/629) Per-side mission statistics | §29 and §91 both carry per-side data; the Qt mission-status table does not split it |
| · [#131](https://github.com/dcs-retribution/dcs-retribution/issues/131) Airfield strike targets | Fork plans OCA/Strike against aircraft and runway only |
| · [#128](https://github.com/dcs-retribution/dcs-retribution/issues/128) Show parking-slot info | Slots are tracked in `aircraftgenerator.py`; nothing surfaces the count |
| · [#82](https://github.com/dcs-retribution/dcs-retribution/issues/82) SHORAD movement at the frontline | §90 moves the line; SHORAD waypointing unchecked |
| · [#508](https://github.com/dcs-retribution/dcs-retribution/issues/508) Track unit damage across turns | §91 records sorties, not unit damage state |
| · [#654](https://github.com/dcs-retribution/dcs-retribution/issues/654) Transport strike targets on supply routes | §50 / §56 / §78 hit convoys and depots, not route nodes. ⚠️ A draft PR already exists against it |
| · [#590](https://github.com/dcs-retribution/dcs-retribution/issues/590) Fuller CTLD incl. sling loading | §76 is paradrop only |
| · [#597](https://github.com/dcs-retribution/dcs-retribution/issues/597) OpFor client support | §27 kneeboards and §45 markers are blue-only |
| · [#708](https://github.com/dcs-retribution/dcs-retribution/issues/708) Start type in squadron config | §64 covers carrier decks only |
| · [#866](https://github.com/dcs-retribution/dcs-retribution/issues/866) Carrier standoff from land | geofffranks is rolling it into his #865 work — watch, do not build |
| · [#242](https://github.com/dcs-retribution/dcs-retribution/issues/242) / [#241](https://github.com/dcs-retribution/dcs-retribution/issues/241) RTB when winchester | A stock DCS AI option; nothing fork-side sets it |
| · [#102](https://github.com/dcs-retribution/dcs-retribution/issues/102) ATO sort · [#105](https://github.com/dcs-retribution/dcs-retribution/issues/105) highlight flights · [#54](https://github.com/dcs-retribution/dcs-retribution/issues/54) map legend · [#631](https://github.com/dcs-retribution/dcs-retribution/issues/631) module-vs-mod labels · [#671](https://github.com/dcs-retribution/dcs-retribution/issues/671) waypoint reordering | Cheap UI, none built fork-side. ⚠️ **#671 is already claimed upstream** by [PR #765](https://github.com/dcs-retribution/dcs-retribution/pull/765) (geofffranks: waypoint reorder, editable ToTs, on-station timing) |
| · [#628](https://github.com/dcs-retribution/dcs-retribution/issues/628) Neutral airports pick a side · [#878](https://github.com/dcs-retribution/dcs-retribution/issues/878) user templates · [#858](https://github.com/dcs-retribution/dcs-retribution/issues/858) opfor frontline options · [#498](https://github.com/dcs-retribution/dcs-retribution/issues/498) saved-mission resume · [#506](https://github.com/dcs-retribution/dcs-retribution/issues/506) block crashed-slot respawn · [#89](https://github.com/dcs-retribution/dcs-retribution/issues/89) channel presets · [#490](https://github.com/dcs-retribution/dcs-retribution/issues/490) DCS mission options · [#497](https://github.com/dcs-retribution/dcs-retribution/issues/497) WW2 big formation | Not built fork-side, no fork blocker recorded |

### D. Not ours

| Issue | Why |
|---|---|
| [#248](https://github.com/dcs-retribution/dcs-retribution/issues/248), [#187](https://github.com/dcs-retribution/dcs-retribution/issues/187) Ammunition economy | **Do not build.** §53 war economy and §54 munitions availability were removed 2026-07-21. Either is a re-litigation |
| [#107](https://github.com/dcs-retribution/dcs-retribution/issues/107) Overhaul BARCAP planner | **Do not build.** The fork's BARCAP geometry was reverted to upstream 2026-08-09 in the planner re-convergence. Settled |
| [#714](https://github.com/dcs-retribution/dcs-retribution/issues/714) Air Doctrine | Read `design/414th-red-brain-phase0-notes.md` first. Seam 7 is dropped and the analytic route failed three times. The stock-ME-AI-option half is separable and is **not** tombstoned |
| [#247](https://github.com/dcs-retribution/dcs-retribution/issues/247) Repair destroyed infrastructure | §68 repairs SAM sites only, so it is a real gap — but prokop7's #679 / #680 ground-repair PRs are in flight. Crowded zone |
| ✔ [#701](https://github.com/dcs-retribution/dcs-retribution/issues/701) Missing weapon `year` / `fallback` | **Measured 2026-08-20; no work owed.** The issue's counts are stale (227 files / 3 / 32, Feb 2026): upstream `dev` now reads **301 / 3 / 70** and the fork **304 / 4 / 70** — the same gap, not a fork regression. The counts also do not measure defects. A missing `fallback` is a chain terminator (`WeaponGroup.fallback` ends the `fallbacks()` walk), which is correct for the oldest weapon in a family — filling all 70 would be wrong. A missing `year` means `available_on` returns `True`, i.e. never date-gated; of the 4, `lantirn.yaml` is a **deliberate** fork decision documented in the file (`b823963c7`, un-gate the LANTIRN by era) and the other 3 are upstream's era-agnostic Hydra-70 and gun pods. If anything is owed it is a comment on the thread reporting the measurement, not a PR |
| [#527](https://github.com/dcs-retribution/dcs-retribution/issues/527) CH-47 logistics for Pretense | Pretense was removed fork-side |
| [#712](https://github.com/dcs-retribution/dcs-retribution/issues/712) CH UK pack, [#718](https://github.com/dcs-retribution/dcs-retribution/issues/718) Su-35s | Already shipped upstream (`pydcs_extensions/ukmilitaryassetspack`, `su35s`). Stale issues |
| [#727](https://github.com/dcs-retribution/dcs-retribution/issues/727) Rafale, [#716](https://github.com/dcs-retribution/dcs-retribution/issues/716) A-4E 2.3, [#411](https://github.com/dcs-retribution/dcs-retribution/issues/411) Tornado F3, [#350](https://github.com/dcs-retribution/dcs-retribution/issues/350) VSN Mirage III | Mod requests; neither tree carries them |
| [#401](https://github.com/dcs-retribution/dcs-retribution/issues/401) Webapp, [#361](https://github.com/dcs-retribution/dcs-retribution/issues/361) offline map | Upstream app-shape calls. §42 local tiles is adjacent to #361 but solves a different problem |
| [#83](https://github.com/dcs-retribution/dcs-retribution/issues/83) Frontline unit behavior, [#192](https://github.com/dcs-retribution/dcs-retribution/issues/192) SEAD TALDs deploy early, [#238](https://github.com/dcs-retribution/dcs-retribution/issues/238) FARP that follows the front | Planner and frontline surfaces upstream is actively working (geofffranks #823, Druss99 #681). Crowded zone — coordinate before touching |

### Re-running the sweep

**Step 1 — list the open issues.**

```
gh issue list --repo dcs-retribution/dcs-retribution --state open --limit 200 --json number,title,createdAt,labels
```

Read the **Bug**-labelled rows first: those are the ones the fork may already have fixed, and a
fix already in hand is the cheapest thing to offer. The tracker moves slowly — 60 open, most
untouched for months — so this is a low-frequency sweep, not a per-sync one.

**Step 2 — before carving anything, check the issue for an open PR. This step is not optional.**

```
gh api repos/dcs-retribution/dcs-retribution/issues/<N>/timeline --paginate --jq '.[] | select(.event=="cross-referenced") | select(.source.issue.pull_request != null) | .source.issue | "#\(.number) \(.state) \(.user.login): \(.title)"'
```

**Use the timeline, not a scan of PR bodies.** The first sweep carved #901 and had to withdraw
the PR the same day, because red-one1 had already opened #902 for it — on the day they filed the
issue. A body scan does not find that: #902 never writes "#901" anywhere in its title or body,
and the cross-reference link exists only because the PR was opened against the issue. Scanning
PR text found 3 of the 4 collisions and missed the one that mattered.

The 2026-08-20 pass, re-run properly, found open non-fork PRs on **#901** (#902), **#561** (#568),
**#82** (#823), **#654** (a draft) and **#671** (#765). Every one of those rows is annotated above.

**Step 3 — check the fork actually still carries what you think it does**, then carve. A row
marked · in the tables above has not had this done.

**What this sweep did not do.** It read titles and bodies, not the full comment threads, and it
did not check the closed issues for a fix the fork should adopt.

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
