# AGENTS.md — 414Ret Agent Guide

The **414th Joint Fighter Group's fork of DCS Retribution** — a turn-based dynamic
campaign generator for DCS World, plus the 414th's air-defense, electronic-warfare,
recon, frontline, and assets-pack features on top of upstream.

- Base: upstream `dcs-retribution/dcs-retribution` `dev` @ `dce851ea`.
- GitHub (this fork): https://github.com/bradyccox/414Ret
- Read this before touching anything. The human-friendly overview is [`README.md`](README.md).

---

## Session Startup & Documentation Hygiene

**GitHub:** https://github.com/bradyccox/414Ret

**At the start of every new thread**, sync with GitHub before touching any code or docs:

```powershell
git fetch origin
git pull
git log origin/main -5 --oneline   # scan for new commits since last session
```

If the current branch is behind `main`, merge or rebase before editing anything — a branch
cut from a stale base produces exactly the duplicate-work + conflict mess that sinks a PR.
Never derive the state of the codebase from memory; always read the current files.

**Keeping docs in sync** — when a feature lands or changes, update in this order:

1. Relevant `docs/dev/design/` file — design rationale and technical details
2. Matching section in `docs/dev/414th-features.md` — engineering deep-dive, file paths, gotchas
3. `README.md` — if the change is player-visible
4. `CLAUDE.md` / `docs/dev/CLAUDE-architecture.md` — if the tech stack, architecture patterns, or feature list changed
5. `AGENTS.md` — sync to mirror `CLAUDE.md` (see Conventions)
6. `docs/dev/414th-ingame-pass-checklist.md` — add a row for any feature with runtime behavior that CI can't exercise

A push that moves code past its docs is a broken push.

---

## Project Docs

This file is the map. The territory is `docs/`. Read the relevant note **before** editing a
feature — each carries the design rationale, the flown-test findings, and the deferred work.

### Standing policies

- **Everything is upstreamable** (2026-07-19). "Clean and correct" is the bar; there is no
  permanent fork-only category. The one named exception is the Splash Damage tuning (see PINNED).
- **Upstream PR freeze is IN FORCE** until upstream's next beta. Updating existing PRs is fine;
  new PRs are not. **Only the DM lifts it** — never infer the lift from upstream commit activity.
- **Red Tide's feature lock was LIFTED 2026-08-03.** It takes new work on the same terms as any
  other campaign. Two exclusions survive as separate calls, not lock consequences: the §71 F-4E
  pack stays un-preseeded, and §57 minefields stay shelved fork-wide.
- **Campaign ownership**: every fork-authored campaign has an owning design note and a CI lock.
- **A generated `.miz` is never hand-edited** where a build tool owns it. Edit the tool.

### Tracking docs — start here

| Doc | What it is |
|---|---|
| [414th-features.md](docs/dev/414th-features.md) | **The deep dive.** Every feature with file paths, gotchas, tests, deferred work. |
| [414th-feature-index.md](docs/dev/414th-feature-index.md) | Generated catalog of every feature with its plugin and `Settings` wiring. |
| [414th-ingame-pass-checklist.md](docs/dev/414th-ingame-pass-checklist.md) | Every "needs an in-game pass" item with a pass criterion and fail signature. |
| [flycards/WATCH.md](docs/dev/flycards/WATCH.md) | The standing opportunistic watch list — rows to adjudicate on any flight. |
| [flycards/LOCAL.md](docs/dev/flycards/LOCAL.md) | The rolling local test card for contrived conditions. |
| [414th-early-systems-decision-ledger.md](docs/dev/414th-early-systems-decision-ledger.md) | The 2026-07-18 deep-audit verdicts on the early-systems core, with self-play evidence. |
| [414th-feature-debt-register.md](docs/dev/414th-feature-debt-register.md) | The verification plan and debt triage. Archive once the Aug-1 wave is processed. |
| [414th-upstreaming-inventory.md](docs/dev/414th-upstreaming-inventory.md) | The upstreaming queue, priority-ordered, with readiness marks. |
| [414th-community-contribution-roadmap.md](docs/dev/414th-community-contribution-roadmap.md) | The long view: community-value × carve-difficulty across every feature. |

### Campaign notes — `docs/dev/design/`

Read before touching a campaign's `.yaml`, `.miz` or build tool.

| Campaign | Note |
|---|---|
| Germany — Red Tide | `414th-red-tide-campaign-notes.md` (+ `-supply-routes-`, `-c2-real-buildings-HANDOFF`) |
| Operation Baltic Fury | `414th-baltic-fury-campaign-notes.md` |
| Marianas — Second Island Chain 2027 | `414th-marianas-2027-campaign-notes.md` |
| Iraq — Umm al-Ma'arik (Desert Storm) | `414th-desert-storm-campaign-notes.md` |
| Iraq — Operation Inherent Resolve | `414th-inherent-resolve-campaign-notes.md` |
| Afghanistan — Enduring Resolve (COIN) | `414th-coin-HANDOFF.md` — **start here for COIN** |
| Persian Gulf — The Tanker War 1988 | `414th-tanker-war-campaign-notes.md` |
| Nevada — Red Flag 81-2 | `414th-red-flag-81-campaign-notes.md` |
| Vietnam set | `414th-vietnam-retribution-HANDOFF.md`, `-notes.md`, `-ops-notes.md`, `-red-tempo-notes.md`, `-airbase-harassment-notes.md` |
| Iraq map 2.9.28 content | `414th-iraq-map-2928-notes.md` — authoring plan, not yet built |

### System notes — `docs/dev/design/`

- **IADS / air defense** — `414th-mantis-iads-HANDOFF.md` (**start here**),
  `-migration-notes`, `-vs-skynet-iads-parity`, `414th-sam-site-realism-notes.md`,
  `414th-air-defense-planning-notes.md`, `414th-qra-player-manning-notes.md`
- **EW / ISR / comms** — `414th-c130-ew-isr-notes.md`, `414th-comms-jam-notes.md`,
  `414th-comint-notes.md`, `414th-gps-jamming-notes.md`,
  `414th-iads-c2-consequences-notes.md`
- **Recon** — `414th-tars-recon-notes.md`
- **CSAR** — `414th-csar-notes.md` (**the one CSAR doc**; supersedes the eight earlier
  SCAR/CSAR notes, each bannered), `414th-scar-rescue-rework-notes.md`
- **COIN** — `414th-coin-insurgent-replenishment-notes.md`, `-reinfiltration-notes.md`
- **Naval** — `414th-cruise-missile-raids-notes.md`, `414th-naval-magazines-notes.md`,
  `414th-carrier-deck-decor-notes.md`
- **Ground / frontline** — `414th-tic-dynamic-fronts-notes.md`
- **Strike targets / BDA** — `414th-scenery-kill-tracking-notes.md` (why some scenery strike
  targets never register as killed; the M4 IADS stand-in; the §88 kill proxy that shipped and
  the position matcher still deferred)
- **Planning / doctrine** — `414th-airwar-planner-consolidation-notes.md`,
  `414th-aircraft-task-rebalance-rubric.md`, `414th-victory-conditions-notes.md`,
  `414th-wing-growth-notes.md`, `414th-single-player-loop-notes.md`
- **Cockpit / data** — `414th-dtc-cartridge-notes.md`, `414th-weapon-dates-proposal.md`,
  `414th-loadout-integrity-audit-notes.md`
- **Framework / tooling** — `414th-framework-consolidation-notes.md`,
  `414th-mist-moose-shim-notes.md` (**the shim that retired MIST**),
  `414th-moose-ops-opportunity-map.md`, `414th-lua-plugin-harness-notes.md`
- **Process** — `414th-verification-cadence-notes.md` (the fly-card throttle, proposed),
  `414th-dcs-olympus-notes.md`, `414th-ui-redesign-directions.md` (+ `-mockups.html`)

### Superseded, draft or historical

Kept for reading old notes and saves; **do not author against them**.

`414th-campaign-phases-*` · `414th-vietnam-political-will-roe-notes.md` ·
`414th-will-generalization-notes.md` · `414th-war-economy-notes.md` ·
`414th-red-intent-notes.md` · `414th-minefields-notes.md` (shelved) ·
`414th-khe-sanh-campaign-notes.md` (merged into Yankee Station) ·
`414th-ewrs-retirement-decision.md` · `414th-dismounts-decision.md` ·
`414th-ctld-mantis-style-port-scope.md` · `414th-scar-*` (superseded by the CSAR doc) ·
`414th-combat-sar-normal-task-notes.md` · `414th-mission-planning-wiki-rework.md` ·
`414th-scenery-import-notes.md` · `turnless.md`

### Other

- [README.upstream.md](README.upstream.md) — unmodified upstream README (setup, dependencies).
- [references/manuals/](references/manuals/) — the official DCS manuals for 11 aircraft
  modules plus the Supercarrier Operations Guide, copied from the local install. The PDFs are
  gitignored (843 MB); the per-folder `INDEX.md` page maps are tracked. **Read the folder's
  `INDEX.md` first, then extract only that range with `pdftotext -f N -l M <pdf> -`** — these
  run to 1,129 pages, and the Read tool cannot open them here (it renders via `pdftoppm`,
  which is not installed). Use them for procedure, systems behavior, cockpit description and
  carrier ops; **not** for loadouts (payload Lua), weapon dates (CLSID tables) or unit stats
  (pydcs export). The `dcs-aircraft-manuals` skill wraps this.
- [docs/wiki/](docs/wiki/) — the player and contributor wiki, mirrored to the GitHub wiki by
  `wiki-sync.yml` on every push to `main`. **Edit pages here, never in the wiki UI.** Also
  carries the adopted upstream dev-process standards, each with **414th:** delta notes.
- `AGENTS.md` mirrors this file — see **Conventions** for the sync process.

## Tech Stack

| Layer | Choice |
|---|---|
| Campaign engine | Python 3.11 (`game/`). Python library catalog (bookmark, reference-only — nothing to adopt now; browse if a new library is ever needed): https://github.com/vinta/awesome-python |
| UI | PyQt (`qt_ui/`) + React/Leaflet client (`client/`) — client NOT type-checked in CI |
| Mission scripting | **Lua 5.1** sandbox plugins (`resources/plugins/`) — no `os`/`io`, no `goto`, definition order matters |
| In-mission framework | **MOOSE** (bundled `Moose.lua`; some plugins vendor classes verbatim) — the standard. **MIST is RETIRED** (MIST → MOOSE consolidation complete, 2026-06-25): `base/plugin.json`'s `"mist"` work-order now loads `resources/plugins/base/mist_moose_shim.lua` — a vanilla-DCS shim implementing the 44 `mist.*` symbols the consumers (CTLD, SCAR, intercept glue, core `dcs_retribution.lua`, and the upstream land/water relocate scripts) actually call, so `mist_4_5_126.lua` no longer loads. **When merging upstream Lua, grep it for `mist.` — a symbol the shim lacks dies at runtime, not in CI** (the 2026-07-05 sync needed a new `mist.getGroupData` for `land_relocate.lua`/`water_relocate.lua`, checklist U1; the 2026-07-10 sync's escort-leash fix needed `mist.DBs.groupsById` — the rule keeps catching real ones). The old `mist_4_5_126.lua` file was **deleted 2026-07-10** (the final cleanup — the shim flew clean across campaigns, checklist G7); rollback = restore it from git history and re-point `plugin.json`'s `"mist"` work-order at it. Do NOT re-point the work-order without reason. See `414th-mist-moose-shim-notes.md`. MOOSE API docs (bookmark): https://flightcontrol-master.github.io/MOOSE_DOCS_DEVELOP/Documentation/index.html |
| Units / mission format | pydcs; CurrentHill mod packs in `pydcs_extensions/` |
| CI gates | Black + mypy + pytest + **Lua syntax gate** (`lua-lint.yml`, blocking) + advisory luacheck |
| Release | PyInstaller → rolling `latest` pre-release on GitHub |

---

## Key Architecture Patterns

**Planner / Lua split.** Python plans and spawns the mission (flight plans, ROE, templates);
runtime behavior (EW, ISR, recon scoring, frontline firefights) is driven by the Lua
plugins. When a feature has both, the Python side sets up and the Lua side executes — don't
move runtime logic into the planner or vice versa.

**Plugin script injection (the uniform late-init pass).** Most 414th plugins are normal
work-order plugins. TIC and MooseAtis additionally need their main script loaded **after**
every plugin's config table exists (their init reads `dcsRetribution.plugins.<name>` / MOOSE
at file scope) — an ordering the per-plugin work-order pass can't express. They are `LuaPlugin`
subclasses (`game/plugins/{tic,mooseatis}.py`, registered in `manager.py`'s `_PLUGIN_CLASSES`)
declaring `late_init_files()` / `late_init_preamble()` / `should_late_init()`; `inject_plugins()`
runs a **second pass** that calls `inject_late_init()` on each after the normal config pass. A
missing/renamed init file is now caught by a test (`game/plugins/tests/test_late_init.py`)
instead of the feature silently never starting. (Replaces the old hand-injected
`_inject_*_script()` "scramble pattern".)

**Viewer-aware visibility layer (recon fog).** One layer drives two player-facing fog rules.
AI planning and threat math always use ground truth (`viewer=None`); only the human (BLUE)
map/UI are fogged. `TheaterUnit.alive_for(viewer)` handles BDA damage lag;
`TheaterGroundObject.known_for(viewer)` handles recon intel-fog; `hidden_on_player_map(viewer)`
fully hides enemy command posts for the SCAR commander-capture feature (gated by
`scar_command_post_intel`, now default ON for new campaigns; §15). Every
accessor takes `viewer: Optional[Player] = None` defaulting to truth; consumers gate at the edge.
Do **not** reintroduce the old `_for_player`/`_for` method twins — that collapse is finished.
A runtime **overview toggle** (`game/theater/fogofwar.py`, transient/never-pickled) short-circuits
those three fog leaves (`alive_for`, `known_for`, `hidden_on_player_map`) to ground truth for any
viewer, so the *whole* render path + intel dialogs un-fog with **no** server-model changes. It is
a checkbox in the custom map layers panel (`MapLayersControl`, §18), driven by a state
`useEffect` (not a Leaflet add/remove layer — unmount doesn't reliably fire `remove`) that
`PUT`s `/fog-of-war/reveal` then re-pulls `/game`.
(`game/theater/theatergroup.py`, `theatergroundobject.py`; see features doc §3.)

**Save migration.** Removed/renamed enum *values* migrate in **one place**:
`FlightType._missing_` (`game/ato/flighttype.py`) maps legacy persisted strings to live
members via the `_LEGACY_FLIGHT_TYPE_VALUES` table. The unpickler (`persistency.py`
`_handle_flight_type`) calls `FlightType(value)`, which routes through `_missing_`, so it
carries **no** parallel remap table — only unknown-value tolerance (degrade to BARCAP).
Other persisted state (e.g. fog) migrates in each class's `__setstate__`. When you rename a
persisted enum value, add the entry to `_LEGACY_FLIGHT_TYPE_VALUES` only.

**Lua plugin discipline.** Lua 5.1 only, vanilla DCS units only (no HighDigitSAMs etc.),
define functions before first use. The `lua-lint.yml` CI workflow runs `luac5.1 -p` over
every `resources/plugins/**/*.lua` as a blocking syntax gate — it catches parse-time errors.
On top of that, the **headless Lua plugin harness** (`tests/lua/`, design note
`414th-lua-plugin-harness-notes.md`) runs the real plugin scripts on Lua 5.1 via `lupa`
against a faked DCS sandbox inside the normal pytest run — catching the "script errors at
runtime and the feature silently never starts" class + pinning safety invariants (grace
periods, exclusion lists, one-shot latches). First coverage: `vietnamops`. It models no DCS
AI/physics, so real behavior still needs an in-game pass (see the in-game-pass checklist).

---

## Features at a Glance

One line each. **Full internals — file paths, gotchas, tests, deferred work, flown-test findings
— are in [docs/dev/414th-features.md](docs/dev/414th-features.md) under the matching §N.** Read
that section before editing a feature; this list is an index, not a spec.

The generated catalog is [docs/dev/414th-feature-index.md](docs/dev/414th-feature-index.md); the
source of truth is the registry `game/fourteenth/features.py` (regenerate with
`python -m game.fourteenth.features`). **Register every new feature there** or CI fails.

### Hard constraints — established by flown tests, do not undo

These cost a mission or a crash to learn. Each is recorded in full in the features doc or the
linked design note.

- **Never toggle SAM radar emissions.** `enableEmission(false)` caused crashes. Suppression is
  ROE `WEAPON_HOLD` only. Applies to §51, §63, §77 and the C-130 script.
- **Never restore the per-base backstop EWR** (§1). DCS has no non-colliding ground unit — the
  mast sat on taxiways and broke AI taxi routing. Detection is the IADS network alone; a side
  with no EWR losing GCI is by design.
- **Never restore the generic `ewrj` fighter-pod jammer** (§2). Superseded by the C-130J
  platform.
- **Never unify §77 escort jamming with the C-130's standoff model.** §77 strengthens as the
  jammer closes; the C-130's burn-through weakens. Both are intentional and opposite.
- **Never add a land-attack weapon family to the §81 anti-ship pattern list.** §63 and §81 stay
  correct only because their weapon sets are disjoint.
- **Never run §60 radar doubling and a regiment model on the same system.** Pick one per system
  and record which.
- **`powerW` is range, not loudness** (§51, §70). Do not chase audio volume with it.
- **GPS jamming (§86): at most 3 sites per campaign, non-overlapping.** Bubbles are large and
  invisible on the map, and effects do not stack.
- **A mover's DCS group needs a 2-waypoint route** (§49). A 1-waypoint `mist.goRoute` never
  drives.
- **Ground movers must last 90 minutes.** Any player-interactable mover is paced so an intercept
  is still possible late in a mission.
- **Never spawn phantom units.** Every scripted force is a real, tracked unit whose loss records
  natively. Applies to §35, §37, §49, §50.
- **A plugin toggle is a second gate.** An unticked plugin silently kills its setting — campaigns
  must preseed both (the §36 lesson).

### Live features

1. **QRA intercept reserve** — per-squadron alert reserve feeding the Moose `AI_A2A_DISPATCHER`, with player-manned cold alert, a scramble cue, and forward-defense border zones.
2. **JAMMING flight type** — the C-130J as an EC-130H/RC-130H EW + ISR platform (`c130j` plugin).
3. **TARPS recon + BDA fog-of-war** — viewer-aware fog (damage lag + intel fog) plus concealed field forces drawn as offset "suspected activity" circles.
4. **UI transparency** — target intel panel, mission-impact debrief, package context bar.
5. **Player target location precision** — `Approximate` mode offsets steerpoints and hides exact coords.
6. **Air-defense planning rework** — overlapping jittered BARCAP waves, forward CAP line, threat-weighted volume, front anchors never abandoned.
7. **Auto-hide mobile SAMs on MFD** — SHORAD/AAA/MANPAD off datalink; MERAD/LORAD stay visible for SEAD.
8. **Robustness / crash fixes** — helo CFIT, carrier-recovery stagger, convoy runway spawns, support-flight radio collisions, locked speed/time route rejection.
9. **TIC — Troops In Contact** — scripted frontline firefights with per-stance movement and ambient fire.
10. **CurrentHill Iran assets pack** — Shahed-136, IRGCN FAC, `[CH] Iran 2020` faction.
12. **Recon engine** — the `recon` plugin: one capture rule for player and AI, shaped by sensor, altitude and cloud.
14. **Plugin Options UI** — `descriptionInUI` field plus label and default polish.
16. **Settings QOL audit** — dead-field cleanup and the `AiRadioBehavior` enum consolidation.
17. **Auto-planner target unpredictability** — opt-in per-side reordering of opportunistic offensive targets only.
18. **Fog-of-war overview toggle** — transient reveal, never persisted, and fenced out of generated missions.
19. **Unified map layers panel** — one grouped control with preset views; air-defence rows filter the master.
22. **Kneeboard space-utilisation + custom import** — per-campaign imported kneeboard images.
23. **Per-squadron DCS country** — nation-specific voiceovers and pilot names, pinnable per squadron.
24. **Date-gated aircraft properties** — era-gated payload-editor options under `restrict_props_by_date`.
26. **Off-mission combat fidelity** — capability-weighted auto-resolution plus the PLAYER_AT_IP fast-forward fix.
27. **Shared-airframe kneeboard index** — one index page when several client flights share a type.
28. **Settings IA reorg + difficulty presets** — metadata-driven layout, difficulty presets, search filter, and the 414th Features page.
29. **Campaign SITREP** — a last-turn digest on its own kneeboard page, the web ribbon, and the Qt debrief.
32. **Arc Light** — heavy bombers walk a bomb carpet across a Strike target *(Vietnam Ops)*.
33. **AAA flak gauntlet** — barrage flak that tightens against predictable run-ins *(Vietnam Ops)*.
34. **Naval gunfire support** — call-for-fire and automatic coastal bombardment *(Vietnam Ops)*.
35. **Convoy interdiction** — real tracked trail convoys hunted via Armed Recon *(Vietnam Ops)*.
36. **Airbase harassment** — standoff rocket/mortar fire on forward fields, never a player-spawn field *(Vietnam Ops)*.
37. **Super Gaggle** — real squadron helos resupplying a cut-off outpost *(Vietnam Ops)*.
38. **FAC(A) willie-pete marking** — an OV-10 marks the largest enemy concentration *(Vietnam Ops)*.
39. **Snake and nape** — detonation-anchored napalm fire from a low fast release *(Vietnam Ops)*.
41. **High Digit SAMs Ultimate Compilation** — S-400, S-300V4, SAMP/T, Pantsir-SM, period EWRs.
42. **Local DCS chart base layers** — locally installed XYZ tile pyramids as extra base maps.
43. **Per-aircraft flight defaults** — saved fuel and cockpit properties per airframe.
44. **Long-range carrier ops** — a deterministic package off a standoff boat, routed to its own tanker.
45. **Support-package F10 orbit markers** — tanker and AEW&C racetracks drawn with callsign, freq, TACAN.
46. **Route-aware fuel-tank planning** — tanks fitted to the sortie before tanker passes are decided, with a live payload-tab readout.
47. **Continuous campaign clock & weather** — one marched clock with weather evolving from the previous turn.
49. **Mobile missile relocation** — shoot-and-scoot theater missile sites; fire first, then scoot.
50. **Convoy ambush + ambient supply convoys** — untelegraphed ambush teams on friendly roads, authored as native DCS triggers.
51. **Enemy comms jamming** — IADS comms nodes jam briefed channels, gated behind a captured aircrew.
52. **Command-center decapitation** — a headless HQ picks targets worse and frags fewer offensive packages.
56. **Strikeable motorpool depots** — the reserve armor pool made bombable, 1:1 with no economy.
58. **Mission-start briefing popup** — per-pilot slot-in cards with a beep and the taxi call.
59. **Ground AI sleep** — the middle tier between keeping and culling, with AAA sites behind two guards.
60. **SAM guidance-radar redundancy** — two spaced track radars, so one HARM is not a site kill.
61. **Host red-interceptor scramble** — an F10 bandit spawner for a quiet event.
62. **Squadron-sequenced modexes** — per-squadron blocks numbered in sequence for Hornets and Tomcats.
63. **Ship-launched cruise missile raids** — finite no-rearm magazines, auto raids and an F10 call-for-fire, with a defender launch wake.
64. **Carrier deck spawn policy** — six-pack as last resort plus the MP slot-timing fix.
65. **Curated carrier comms** — per-hull TACAN, ident, ICLS, Link 4 and ATC feeding the CV Operations Data page.
66. **Generated-mission archive** — a dated copy of every generation, in a folder DCS lists.
67. **Weather-aware auto-planning** — rain grounds auto-recon; storms demote low-level attack.
68. **Adaptive procurement** — price-weighted buys and optional SAM site repair.
69. **SEAD-before-strike coordination** — strikes retimed behind the suppressor servicing their target.
70. **COMINT collection** — the §51 mirror: a surviving collector buys a tasking leak and one exact fix, plus an audible red UHF net.
71. **Expanded F-4E Weapons Pack** — AGM-78 Weasel fits gated on live pylon legality.
72. **Carrier deck decorations** — island-street and LSO dressing, plus a launch-corridor set struck below before recovery.
73. **Per-airframe default loadout for a task** — pin a fit for an airframe and task across campaigns.
74. **Native DTC data pre-population** — auto-loading cartridges for Hornets, Vipers and CJS Super Hornets, with a per-flight DTC tab.
75. **Custom victory conditions** — authored win/lose blocks plus generic domination and attrition endings.
76. **CTLD paratroopers** — fixed-wing Air Assault by paradrop, player and AI.
77. **Escort jamming** — EA-18G and EA-6B only; non-stacking spoof bubbles and SAM weapons-hold pulses.
78. **Sea-supply convoys + coastal anti-ship** — proportional convoy losses and batteries that actually engage.
79. **Decoy suspected-activity zones** — unitless fake contacts, human-only by construction.
80. **Mixed-hull ship groups** — task groups instead of copies of one hull, family-bounded.
81. **Cross-turn naval magazines** — staggered weapons-free release and finite anti-ship stock, released on attack.
82. **The Wing Grows** — announced mid-campaign squadron arrivals, SEAD before strike.
83. **SP Pilot Mode** — accept-and-fly-next, an aircraft-first sortie board, and a pre-turn reasons-to-continue brief.
85. **SAM/missile battery support sections** — refuellers, power and transload in the faction's own kit.
86. **GPS jamming** — satellite-guided weapons released inside the bubble land long.
87. **Naval station-keeping racetracks** — anchored ovals so ships hold station under way.
88. **Scenery strike-target kill proxies** — a registered marker on every map building, so the kill records when the terrain trigger misses.

### Retired, removed or shelved — do not restore

Kept numbered so old notes and saves stay readable. Details and rationale in the features doc.

| § | Feature | Status |
|---|---|---|
| 11 | Native DCS DTC cartridge export (v1) | Retired 2026-06-26 — superseded by §74 |
| 13 | Flight Control ATC | Retired 2026-06-26 |
| 20 | Drop-spawn map unit placement | Removed 2026-08-02 |
| 15 | SCAR — RESCAP "Sandy" rescue escort | Removed 2026-08-07 — see §21 |
| 21 | Combat SAR (fork implementation) | Removed 2026-08-07 — replaced by upstream dcs-retribution#929 |
| 25 | Compact 3–4 page kneeboard deck | Retired 2026-07-05 |
| 30 | Dedicated kneeboard cover page | Retired 2026-07-13 — new info folds into a stock page |
| 31 | One-page Brief Sheet | Retired 2026-07-13 — BLUF and code words survived |
| 40 | Campaign phases, ROE zones, target release | Removed 2026-07-21 |
| 48 | Commitment ceiling and the political-will economy | Removed 2026-07-21 |
| 53 | War economy | Removed 2026-07-21 |
| 54 | Munitions availability | Removed 2026-07-21 |
| 55 | Red Intent adaptive posture | Removed 2026-07-21 |
| 57 | Air-droppable minefields | **Shelved** 2026-07-30 — inert, code retained, resumable |
| 84 | Old-stock loadout attrition | Removed 2026-08-06 |

Also removed: the blank-start campaign maker (2026-08-02), the SOF capture economy (2026-07-01),
and the Skynet IADS engine (MANTIS is the sole engine).

## Repo & Branch Layout

- This repo (`bradyccox/414Ret`) `main` = the consolidated, most-up-to-date 414th build.
- Upstream is `dcs-retribution/dcs-retribution`; the 414th's PR fork is
  `bradyccox/dcs-retribution`.
- The 414th's primary "all features" working branch in the dev checkout is
  `414th-all-features`; `main` here = that + the Iran pack + a Black/mypy lint pass.

### DCS Liberation — the grandparent project, still alive (WATCH, established 2026-08-07)

Retribution forked from `dcs-liberation/dcs_liberation`, and **Liberation did not stop** — it is
actively developed on branch `develop` (792 stars; **15.0.0 released 2026-06-19**, 14.1.0 in
February, commits landing weekly). Do **not** treat it as an archive of pre-fork history. It is a
second upstream: a parallel evolution of the same codebase, with no shared PR flow and no
obligation in either direction. We take from it; we do not carve to it (upstreaming means
`dcs-retribution/dcs-retribution` — see `main-retribution-means-upstream`).

**The watch:** skim Liberation's release notes when a new version drops (`gh api
repos/dcs-liberation/dcs_liberation/releases`). Their notes are terse and tagged by area
(`[Engine]` / `[Campaign]` / `[Data]` / `[UI]`), so a pass costs minutes. Look for **`[Data]`
first** — data lands cleanly in the fork with no code change and no freeze implications, whereas
their engine/UI work usually collides with fork features that already solve the same problem.

Adopted so far:

| Date | Taken | Notes |
|---|---|---|
| 2026-08-07 | 12 hand-measured aircraft `fuel:` blocks (their 14.1.0 + earlier) | Coverage 22 → 40 aircraft types. Checklist **S7**; features doc §46. |

Checked and **already covered** — do not re-investigate without new evidence: carrier/LHA
auto-targeting, front-line spawn exclusion zones, weapons-by-date gating, turn-less mode. Their
auto-purchase model is **behind** ours (they document a fixed 30-unit front-line threshold; we have
`frontline_reserves_factor` / `reserves_procurement_target`). Genuinely open, not yet pursued:
campaign-designer control of on-road vs off-road front-line travel (15.0.0 — set on the supply
route's M-113 waypoints; we hardcode `PointAction.OnRoad` in `convoygenerator.py` +
`flotgenerator.py`), which would fit the driveable-corridor standard.

**Their docs are worth reading too.** Liberation publishes a Sphinx site at
https://dcs-liberation.readthedocs.io — and its **source is in our tree**, inherited through the
fork (`docs/*.rst`, `docs/conf.py`, `.readthedocs.yaml`). Nothing builds it here and it is stale
(`docs/index.rst` still titles the site "DCS Liberation"; `docs/game/index.rst` is an empty
toctree), but the content is live: `docs/modding/layouts.rst` is the authoritative writeup of the
layout system (`layout.miz` + `layout.yaml`, one group per unit type, the `layouts.p` pickle and
*Developer Tools → Import Layouts*), and `docs/modding/fuel-consumption-measurement.md` is the
procedure for measuring the ~217 airframes that still have no `fuel:` block.

### Upstream PR ledger (**refreshed 2026-07-20** — 50 PRs: 20 open / 8 merged / 22 closed. **Late 2026-07-20: the squadron-country surfacing carved as draft #896** — the Discord thread (Starfire's yaml `country:` ask + Toad's under-livery dropdown) answered the same day it ran; the fork's I6 pass flew clean that night ("896 is flown and good") but the draft is **HELD through the PR freeze below** (DM call — #896 was opened the same day the freeze was learned, so it stays a quiet draft until the freeze lifts; un-draft on a fresh explicit call then). **The 2026-07-20 QOL carve wave** (the DM's "ship the objective improvements back" call) opened six more drafts in one session: Dog Ear SHORAD #887, F-14A-Early payload #889, squadron-config guard #890, blue-block markers #891 (the upstream sweep found **465** dropped markers across 9 campaigns — Normandy's authored blue defenses dominate, flagged as a maintainer judgment call in the PR), the #791 refresh #892, and §60 radar redundancy #893 (stacked on #892, rationale attached). **#891 self-closed on review the same day**: Starfire13's density reaction ("352 EWRs in Normandy. Good lord…") plus the real ask — **CJTF block-convention consistency** ("for some objects you can only use one, yet for others both are acceptable"); the fork answered the ask same day (the loader's last single-block classes now chain both blocks — 3 shipped red-block factories resurrected, `test_miz_marker_binding.py`) but the **re-carve was DROPPED 2026-08-05** — the Custom-campaigns wiki's block spec table and upstream's loader already agree on all 19 classes, so there is no bug to carve (inventory item 17). Also learned in that session: **#791 closed with zero comments** (never reviewed — hence the refresh) and **#851 closed on a real objection** (juanjux: HDS Ultimate Compilation is NOT backward-compatible with Auranis HighDigitSAMs 2.1.0, which he runs — the S-300 renames collide; a re-carve must first answer which successor mod upstream standardizes on). **Held re-carve draft prepared 2026-07-20** — [docs/dev/414th-hds-recarve-draft.md](docs/dev/414th-hds-recarve-draft.md) (leads with UC-as-successor + migration note, offers the dual-toggle fallback; gated on the PR freeze lifting AND a fresh post-mod-update export). **Three fork PRs merged upstream 2026-07-19** (#805/#843/#854) and geofffranks' #859 (the §56 motorpool source) landed the same day — all four reconciled back into the fork in the `sync/upstream-dev-2026-07-19` merge. Same day, Wave 3 opened: the Splash Damage defaults PR #880 pushed (item 21, the first last-mile carve), the VWV v3.2.0 update #881 pushed (item 22), the §76 paradrop carve #884 opened (un-drafted late that evening + Starfire13 pinged for review), the **infrastructure pair #882 (Lua plugin harness) + #883 (MIST 51-symbol shim, stacked on #882)** opened as drafts, #828 was rebased — briefly un-drafted, then deliberately re-drafted minutes later (21:36→21:40Z per the PR timeline), so it sits as a draft with the un-draft call open — and the night closed with **two more last-mile carves: the §75 victory-conditions core as draft #885 and the Iran-pack re-carve (the #784 redo) as draft #886**. Still re-verify with `gh` before acting; this goes stale fast.

**Sync 2026-07-26 — upstream dev @ `e9b2387e`** (merge base moved `acf02b75` → `e9b2387e`; fork PR
[414Ret#726](https://github.com/BradySox/414Ret/pull/726)). Upstream shipped 12 commits over the
weekend, which reads like the beta release the PR freeze was waiting on — **re-verify whether the
freeze has lifted before pushing anything new** (the held items are listed under the freeze banner
below). Landed: **#904** DCS 2.9.28.26283 (pydcs pin, F-14B(U) module + 10 squadron presets +
payload, beacons, Syria landmap) · **#899 + #895** motorpool placement/planning (§56) · **#910**
EWR + motor-pool campaign pass and the new `operation_desert_trident` · **#911** faction updates for
F-14B(U) · **#908** campaign filter/sort · **#909** F-14A export loadout location · **#905** broken
Kola beacons · **#898** captive AIM-9M clsids · **#903** forum URL. **Our #889 merged** (see Merged
below). Where upstream had solved something the fork also touched, the fork **took upstream's shape**
— the campaign filter/sort framework (our era shell became a criterion inside it), the
velvet_thunder EWR miz (their 3 authored sites over our 1), the faction EWR restructure (borrowed
Flat Face/Tin Shield/Hawk search radars → dedicated `EWR 1L13`/`55G6`/`AN-FPS-117`, applied
semantically so fork-only units like `EWR P-14 Tall King` survive), the F-14A export preset, and the
captive-AIM-9M removal. Fork positions preserved: the `hercules` purge, `f111c` values, the
`[CH] B-21` → `B-1B Lancer` substitution, the §50 supply-route blocks, and our `_target_waypoints`
refactor (which already carried #895's `if targets:` fix, with the empty-list case documented).
**UH-60L un-cut** from `CUT_MOD_AIRCRAFT` (DM call): upstream standardizes on it across a dozen
campaigns + the new faction, and the fork's `uh_60l` ModSetting already ejects it in a mods-off game
— the same mod-with-fallback design the guard's docstring exempts. **New carve candidate:** upstream's
`F-14A-95-GR` + `F-14BU` payload files name a preset `"Retribution Fighter Sweep"`, but the loader
matches `FlightType.value` casing exactly (`Fighter sweep`), so both jets silently fly a fallback
loadout — fixed fork-side, worth carving back once the freeze lifts. **Line-ending gotcha for the
next sync:** base and upstream ship the campaign/faction files CRLF while the fork normalized them to
LF, so ~36 of them conflict as *whole files*; re-running `git merge-file` on `tr -d '\r'`-normalized
stages cuts that to 1–2 real hunks each.)

**⛔ UPSTREAM PR FREEZE — STILL IN FORCE, CONFIRMED BY THE DM 2026-08-05 ("its not lifted yet. Beta branch soon"):** dcs-retribution is accepting **no NEW PRs until their next beta release**; **updating existing PRs is fine** (merging current upstream into an open PR branch, pushing review fixes, and re-requesting review are all allowed and were exercised on all 13 open PRs on 2026-08-05). **Do NOT infer the lift from upstream activity** — that mistake was made twice: the 2026-07-26 sync read 12 weekend commits as "the release the freeze was waiting on", and the 2026-08-05 sync read another 36 commits (incl. their merge of our #889) the same way. Neither was the release. The observable facts as of 2026-08-05: **the newest published release is still v1.5.0 (2026-04-13)**, and the `test/1.6` branch was cut but its tip has not moved since **2026-07-25** while `dev` kept merging through 08-04. **Only the DM lifts this**, on word from upstream — never a `gh`/commit-activity inference. Holds until it lifts: the **HDS re-carve** (held draft prepared — [docs/dev/414th-hds-recarve-draft.md](docs/dev/414th-hds-recarve-draft.md); data re-verified post-mod-update, numbers hold — note that draft carries a SECOND gate of its own, and the real blocker is a *decision* upstream must make: which HDS successor mod they standardize on, since #851 died on a user running Auranis 2.1.0), the pydcs exporter-hardening PR candidate, and the `Retribution Fighter sweep` payload-casing fix from the 07-26 sync. **#896 is NOT on this list** — it is an *existing* open PR (never a draft; the earlier "un-draft #896" note was wrong): Druss99's 07-31 request-changes was answered in full the same day (`6dea2efa`, operator tables dropped), a re-review is **already pending on him**, and the standing `CHANGES_REQUESTED` decision is just the stale flag from that review, which clears only when he submits a new one. Nothing is owed on it. **The post-mod-update queue COMPLETED 2026-07-20 evening** (re-dump run; every export file parsed clean on the hardened exporter): extensions verified 386/386 pre-migration, **HDS unchanged** (the re-carve draft's numbers hold), and the update wave surfaced the real story — **ED has integrated CurrentHill units into base DCS** (`CoreMods/tech/Currenthill Assets Pack`, the `CHAP_*` ids; pydcs pin + 21 fork CHAP yamls already carry them) while the CH 1.5.0 packs renamed their remaining ids to `CH_`/dropped the ED-integrated ones. The fork migrated: Sweden 30 id renames + UK Type45/SkySabre + Ukraine BTR-4/MiG-29MU2/Su-24MU (extension ids + yaml filenames + LvS-103/Sky-Sabre layout refs + eject strings), 6 vanilla-superseded registrations retired (both Ukraine tanks, Scimitar/Scorpion re-pointed in blufor_current to the vanilla CHAP variants), and the **Ukraine pack was discovered double-nested in Saved Games (never loaded — fixed)**; its units export-verify on the next natural dump. The wave's adoption audit lives in [docs/dev/414th-ch-wave-adoption-backlog.md](docs/dev/414th-ch-wave-adoption-backlog.md): ~98 % already adopted (the extensions had tracked newer pack versions all along; every new AD system rides a factioned preset group) — **4 units genuinely open** (TigerUHT yaml, the B-21 faction call, the 2 Project 22160 hulls).

Carved out of this work, against `dcs-retribution/dcs-retribution` (all authored by `BradySox` — the renamed `bradyccox` account):

- **Open (awaiting review):**
  - [#896](https://github.com/dcs-retribution/dcs-retribution/pull/896) surface the squadron country — campaign yaml `country:` pin + Air Wing dialog selector (**draft**, opened 2026-07-20 on dev @ `3760cf2a`) — §23's surfacing follow-on (inventory item 26), answering that day's upstream Discord ask verbatim (Starfire: preset-for-the-nation-if-available-else-generated-set-to-it; Toad: dropdown under Livery): `SquadronConfig.country` → same-nation-only preset pick with def-generator fallthrough + `override_squadron_defaults` stamp, the `SquadronCountrySelector` (live-write, faithful mod-country display), preset dropdowns showing each preset's nation, Save/Load Config country round-trip, and the bind_data livery stale-squadron re-point fix. Upstream carries the 9 game-side tests; the offscreen-Qt selector test + the DS `country: USA` pins stay fork-side. 453 tests / black / mypy green. **I6 VERIFIED 2026-07-20** ("896 is flown and good"). **Druss99 request-changes 2026-07-31** — the operator tables are "a massive burden when adding a new aircraft module"; capitulated fully (DM call): `game/dcs/operatorcountries.py` + the operator-derived unpinned-CJTF default removed (fork + carve), the selector shows the full country list, and an unknown `country:` aborts New Game instead of degrading, reducing the PR to "yaml country pin, no default-behavior change." Fork side = branch `claude/pr-896-review-8kg5xf`; the carve still needs the same trim applied + re-request review.
  - [#893](https://github.com/dcs-retribution/dcs-retribution/pull/893) SAM guidance-radar redundancy (**draft**, opened 2026-07-20, **stacked on #892**) — §60 carried upstream with the realism-notes rationale spelled out in the body (a balance call, not TO&E; the regiment-model tension + "park it if you'd rather keep stock single-radar" offered explicitly): 21 layout yamls `unit_count` 1→2 across 23 slots + the 5 shared templates grafted a second radar position (45–121 m offsets, structurally copied from the fork's templates — the fork-only P-14 "EW Radar" groups deliberately NOT carried) + the 29-pair lockstep test (SAMP/T row dropped — HDS-Ultimate-only). 467 tests green.
  - [#892](https://github.com/dcs-retribution/dcs-retribution/pull/892) SAM site layout variety + EWR radar pool (**draft**, opened 2026-07-20) — the **refresh of #791**, which closed with zero comments (never reviewed): the June branch rebased onto dev @ `acf02b75` with zero conflicts, content unchanged, re-validated same day (68 preset groups load; all 131 factions resolve with 0 bad preset refs; 438 tests).
  - [#890](https://github.com/dcs-retribution/dcs-retribution/pull/890) squadron `aircraft:` empty-key New Game crash guard (**draft**, opened 2026-07-20) — inventory item 12, honestly re-pitched: current upstream campaigns no longer ship the pattern (the item's "two campaigns unplayable" claim was stale — upstream's Northern Guardian Transport squadron has since been filled in; the fork hit the crash when its mod purge emptied the key), so the PR sells it as the defensive guard it is (`data.get("aircraft") or []`; iterating None at defaultsquadronassigner.py:61 kills New Game).
  - [#887](https://github.com/dcs-retribution/dcs-retribution/pull/887) Soviet SHORAD Sborka "Dog Ear" acquisition radar (**draft**, opened 2026-07-20) — the fork's evolved slot-gated + marker-gated implementation (`_add_dog_ear_if_needed` in both `for_layout` + the preset loader, the SHORAD.yaml Search Radar slot, the 3-way test incl. the SAM-site/era exclusions); vanilla unit, no faction edits. Was never in the inventory queue — added as item 23.
  - [#886](https://github.com/dcs-retribution/dcs-retribution/pull/886) CurrentHill Iran Military Assets pack + `[CH] Iran 2020` faction (**draft**, opened late 2026-07-19) — the clean minimal redo of self-withdrawn #784 (that early upload was a monolith dragging in the C-130J plugin/QRA planner/scramble scripts): `pydcs_extensions/iranmilitaryassetspack` (Shahed 136 LM + the 2 IRGCN FACs) + the faction + the `iranmilitaryassetspack` ModSettings toggle/wizard checkbox + the FAC ship-radar registry entries + 3 unit yamls, nothing else — the exact pattern of the six CH packs upstream already carries. Headless probe on upstream dev: 20/20 aircraft / 10/10 preset groups / 6/6 naval / 2/2 missiles / 9/9 AD resolve; mod-off strip verified both ways. 438 tests / mypy / black green. **Export verification CLOSED 2026-07-20** (Druss99's export-provenance ask, same as #881): the wiki's `pydcs_export.lua` process was ACTUALLY RUN on the DM's install (CH Iran 2.0.0 loaded) — it caught `IranFAC_MG_AShM` threat/awd registered 25000 where the live DB says **1800** (the 25000 was `WS.maxTargetDetectionRange` conflated into the AA threat fields; 14× inflated ring), fixed on the branch (`9dffedff`, fork mirrored); `CH_Shahed136` + `IranFAC_MG` verify clean — 3/3 match. Reply posted in-thread with the verdict.
  - [#885](https://github.com/dcs-retribution/dcs-retribution/pull/885) custom victory conditions — **CLOSED-CEDED 2026-07-20, no longer open** (was: draft opened late 2026-07-19 carrying §75's generic core — `game/victory.py` minus the meter fields/negotiation absorption/SITREP surfaces, the `check_win_loss` branch, the two knobs, 28 ported tests). Druss99: "I have a local branch for this already so if you don't mind I'll be taking this one" — the DM closed the PR and handed the feature over the same morning. NOT a rejection, NOT a re-carve candidate: fork §75 is unaffected (B29 app pass still owed fork-side), and when Druss99's implementation lands upstream it becomes a **reconcile-on-merge / drift-watch** item vs the fork's shape.
  - [#884](https://github.com/dcs-retribution/dcs-retribution/pull/884) fixed-wing air assault by CTLD paradrop (opened 2026-07-19, **un-drafted late that evening** + Starfire13 pinged for review) — §76's generic core: the cabin-based planner gate (subsumes `is_hercules`; the Hercules keeps its initial-point ingress + gains a layout-shape pin), the `ctld-config.lua` drop runtime (airborne "Unload / Extract Troops" = jump, descent-delayed ground spawn, AI one-shot zone release, 3,000 ft player ceiling), the preload retry, and `Air Assault: 40` on the C-130J-30 yaml. The fork's lupa-harness runtime test stays fork-side (upstream has no lua harness); the §2 EW deny-list hunk is fork-only. On dev @ `acf02b75`; pytest/Black/mypy green. Fork side = [414Ret#681](https://github.com/BradySox/414Ret/pull/681).
  - [#883](https://github.com/dcs-retribution/dcs-retribution/pull/883) replace MIST with a tested 51-symbol compatibility shim (**draft**, opened 2026-07-19, **stacked on #882** — review the shim commit with/after the harness) — the fork's MIST retirement carried upstream: `mist_moose_shim.lua` extended with the eleven symbols only upstream's extra consumers call (dismounts `getGroupPoints`/`marker.remove`, EW-jammer pitch/roll/`makeVec3GL`, EWRS speed conversions, and the Pretense teleport/respawn family — **new implementations validated by the harness, never fork-flown**, since the fork ran no Pretense: the in-game watch item), `mist_4_5_126.lua` deleted, consumers byte-unchanged, one-line rollback. Bonus: the DB tier rebuilds on debounced BIRTH + a 30 s fallback instead of MIST's whole-mission poll. 462 tests green.
  - [#882](https://github.com/dcs-retribution/dcs-retribution/pull/882) headless Lua plugin test harness (**draft**, opened 2026-07-19) — the fork's `tests/lua/` lupa harness carried upstream (virtual clock with DCS reschedule semantics, recorded `trigger.action`/controller/spawn side effects, populated-world + weapon fakes, a minimal MOOSE facade, file-scope/tick/handler error capture; runs inside plain `pytest tests`, zero workflow changes). First consumer: Splash Damage 3 runtime pins (load + tracking start, the percent-normalization contract, track-to-impact, unknown-weapon ignore; power *values* deliberately unpinned while #880 is discussed). **The enabler for the Wave-5 Lua-feature carves.**
  - [#881](https://github.com/dcs-retribution/dcs-retribution/pull/881) Vietnam War Vessels support → v3.2.0 (inventory item 22, opened 2026-07-19) — upstream's VWV support was frozen at v3.0.0: registers the 3.1.0 Sampans ×5 + Junk civilian craft and the 5 never-registered hulls (Radford / Epperson / Everett F. Larson / Solon Turman / USNS Card; ids from the installed mod's own `Database/Navy/*.lua`), adds all 11 to the `faction.py` eject list, and bumps the wizard label + 4 stale faction `requirements` versions to v3.2.0. Registration-only parity with the fork (no unit yamls/prices — the fork hasn't authored them either). On dev @ `acf02b75`; pytest/Black/mypy green. Fork reconciled same day (same eject entries + its own 4 stale faction strings). **Review response 2026-07-20** (Druss99 asked whether the extension came from a pydcs export — the annotation comments read as AI-generated): comments stripped to exporter style, and the re-verification of all 11 hulls against the mod's public source (`tspindler-cms/tetet-vwv` @ tag `VWV_3.2.0`) caught that the removed **USNS Card** comment was WRONG — `Database/Navy/Card.lua` defines `airFindDist 45000` / `airWeaponDist 18650` (keeps a 5"/38 battery), so Card is now 45000/18650/18650 and Solon Turman carries explicit 15000/0/0 (branch commit `534fbd7`; fork mirrored the same fix). **Export verification CLOSED 2026-07-20**: the wiki's `pydcs_export.lua` process was ACTUALLY RUN on the DM's install (full VWV 3.2.0 fleet loaded; runbook + heavy-mod exporter gotchas in `tools/verify_mod_export.py`'s docstring — the stock exporter crashed twice on 50-mod data and needed nil-guards/pcall hardening, patched copy at `C:\Users\brady\dcs-export\pydcs_export.lua`, pydcs-PR candidate) and it FALSIFIED the tag-source reading: `Solon_Turman.lua` sets `GT.airWeaponDist = 13000` (not unarmed — Turman fixed 0→13000/13000), BHR `plane_num` is 40 (not 8), and 3.2.0 superseded the plain Maddox module with the Tonkin Incident module (id **`USS Maddox T`** — registered additively + eject-listed; The Sullivans left the 3.2.0 distribution entirely, legacy entries kept for old installs). All on the branch (`2ffa9057`, fork mirrored); Card's 45000/18650/18650 export-CONFIRMED; 120/124 registered VWV units match field-for-field (residual: 2 pre-existing cosmetic drifts, aligned fork-side). Reply posted in-thread. **The follow-on fork-wide sweep** (unfiltered `verify_mod_export.py` over every installed mod) then aligned ALL 363 registered units of every extension to the live export — 93 drifted (HDS NATO-name restyle + sensor retunes incl. SA-17 TELAR detection 120→18.5 km, CH UK renames/retunes, IDF SAM ranges, and the `oh6_vietnamassetpack` duplicate VAP registrations whose stale values silently raced `vietnamwarvessels`' at pydcs-injection time — values now agree; module retirement deferred for save-compat) — fork commits `1345a4002` + `2621d695c`; the §63 LACM hull-id audit came back clean (CH Russia Kalibr trio verified; the 4 CH USA ids target a newer pack than installed, no faction fields them).
  - [#874](https://github.com/dcs-retribution/dcs-retribution/pull/874) curated carrier comms (**draft**) — §65 verbatim (per-hull boat cards feeding the DCS-rendered CV Operations Data page: hull-number TACAN + boat ident with `alloc_near` nearest-neighbor degrade, hull-keyed ICLS via a shared `IclsAllocator`, 336-band Link 4, stable persisted ATC, flagship named by hull name). NO fork couplings; the port adds only the Pretense allocator-type adaptation (behavior untouched). On dev @ `ef576acc`; pytest/Black/mypy green — opened 2026-07-16. Fork side = [414Ret#611](https://github.com/bradyccox/414Ret/pull/611). See upstreaming-inventory item 19.
  - [#873](https://github.com/dcs-retribution/dcs-retribution/pull/873) culling: keep scenery-objective kill tracking in culled regions (**draft**) — opened 2026-07-16; `MERGEABLE`. (Added by the 2026-07-16 live refresh; it had never been recorded here. Fork-side context not yet written up.)
  - [#872](https://github.com/dcs-retribution/dcs-retribution/pull/872) ship-launched cruise missile strikes — generic core of fork [414Ret#599](https://github.com/bradyccox/414Ret/pull/599) (Tomahawk/Kalibr shore attack: F10 call-for-fire with marker-text salvo sizing, optional auto raids, persisted no-rearm magazine via the `cruise_missiles_state` debrief channel). **Ready for review 2026-07-19**: the branch carries the review-feedback stagger + un-cull + carrier-escort commits, a current-dev merge, and the flown **defender launch wake** ported from the fork (alarm-RED near the aimpoint for the missile flight window; Skynet-adapted comments) — un-drafted after the DM's local 10/10 fly. See upstreaming-inventory item 18.
  - [#880](https://github.com/dcs-retribution/dcs-retribution/pull/880) Splash Damage coherent field-tuned defaults — **CLOSED 2026-08-06, DM call: "it's a preference we use, not everyone else."** The tuning is a 414th taste call, not a defect owed upstream, so it stays fork-side permanently (a named exception to the everything-upstreamable policy; see the pinned block). Two real bugs surfaced in the closing audit and are **not** carried by anything now: upstream's `sd3-config` assigns `cluster_bomblet_reduction_modifier` while the script reads `cluster_bomblet_reductionmodifier` (the bomblet-reduction toggle is inert — fixed on the closed branch, so it needs re-carving if it is ever wanted), and upstream's parked-aircraft OCA block calls **`getAGL()`, which is defined nowhere in their tree** (nil-call for every damaged object, inside the `world.searchObjects` callback) — the fork's restored copy computes AGL inline instead. Original scope, for the record: it fixed upstream's broken percent plumbing (the "(%)" rocket spinner applied raw ×130; overall_scaling 3 = 3% with a second ÷100 in the bomblet path; test mode shipped enabled) and sets the 414th's flown values (60%/80%/static 1/radius 100%/wave ×2, big-iron explTable trims, shaped_charge flags on the 4 HEAT/AP rockets) in upstream's own plugin.json→sd3-config architecture. Plugin stays default-OFF upstream.
  - [#828](https://github.com/dcs-retribution/dcs-retribution/pull/828) recon fog-of-war (§3) — the flagship carve. **Rebased 2026-07-19**: squashed to one commit on dev @ `acf02b75`, re-validated (upstream pytest 451 passed; the new ship-movement test double gained the `game.settings` chain `known_for` reads), `MERGEABLE`. Briefly un-drafted, then **deliberately re-drafted the same evening** (21:36→21:40Z per the PR timeline) — currently a **draft**; un-draft when ready.
  - [#806](https://github.com/dcs-retribution/dcs-retribution/pull/806) configurable cruise/patrol altitude.
  - [#794](https://github.com/dcs-retribution/dcs-retribution/pull/794) hide mobile SAM in combined groups (§7).
  - [#792](https://github.com/dcs-retribution/dcs-retribution/pull/792) wind override UI.
  - [#788](https://github.com/dcs-retribution/dcs-retribution/pull/788) inflight final-waypoint crash (§8).
- **Merged (9):**
  - **2026-07-25:** [#889](https://github.com/dcs-retribution/dcs-retribution/pull/889) F-14A-135-GR-Early payload `unitType` fix (inventory item 20) — the Early Tomcat flew every tasking unarmed because the payload file declared the base `F-14A-135-GR`, and pydcs keys payload files by that field. Upstream merged the one-liner + the changelog note; the **guard test stayed fork-side** (`tests/test_f14_loadouts.py`), and the fork's copy additionally carries the 414th "Retribution TARPS" fit, so the two are convergent on the fix but not byte-identical. Reconciled in the 2026-07-26 sync.
  - **2026-07-19 (the contributor wave — all three reconciled into the fork by the same-day sync merge):**
    [#854](https://github.com/dcs-retribution/dcs-retribution/pull/854) per-squadron DCS country + nation-aware pilot names (§23; resolves upstream issue #627 — upstream's merged copy added `blue_country_ids`/`red_country_ids` helpers, adopted fork-side) ·
    [#843](https://github.com/dcs-retribution/dcs-retribution/pull/843) era-gate payload-editor options / JHMCS helmet cueing (§24 — **upstream merged the fork's final shape**: `date_gated_properties` blocks in the aircraft yamls + `restrict_props_by_date`, NOT the interim helmet-yaml layout from Druss99's first review; the two sides are byte-convergent. ⚠️ upstream's copy of the 4 aircraft yamls froze a **2026-06-29 snapshot of the fork's task priorities** that the rebalance rubric has since re-tuned — flagged for an upstream data-cleanup PR) ·
    [#805](https://github.com/dcs-retribution/dcs-retribution/pull/805) bulk waypoint altitude UI (upstream's merged version carries the full Druss99 skip-list — `DIVERT`/`CARGO_STOP`/target/pickup/dropoff/`REFUEL`/`RECOVERY_TANKER`; the fork's pre-review copy was upgraded to it in the sync).
  - **Earlier:** [#871](https://github.com/dcs-retribution/dcs-retribution/pull/871) targeting-pod era data (merged 2026-07-15) · [#841](https://github.com/dcs-retribution/dcs-retribution/pull/841) plugin `descriptionInUI` field (§14) · [#793](https://github.com/dcs-retribution/dcs-retribution/pull/793) building-card placeholder (§4) · [#826](https://github.com/dcs-retribution/dcs-retribution/pull/826) weapons coverage/repairs · [#789](https://github.com/dcs-retribution/dcs-retribution/pull/789) inverted OPFOR aggressiveness fix.
  - Also relevant: geofffranks' [#859](https://github.com/dcs-retribution/dcs-retribution/pull/859) motorpool depots merged 2026-07-19 — the fork pre-adopted it as §56 (+ the #625 drift port), and the sync brought the final extras (the `AttackMotorpools` HTN task, wired into the fork's offensive-emphasis lists; capture-zone warning already ported).
- **Closed unmerged — NEWLY CLOSED since the 2026-06-27 snapshot (⚠️ the ledger had all four listed as "open, awaiting review"; the *reason* each closed was NOT investigated — check the PR before re-carving):**
  - [#851](https://github.com/dcs-retribution/dcs-retribution/pull/851) High Digit SAMs **Ultimate Compilation** support (§41's generic core) — retargets the HDS toggle to the maintained mod: renamed-radar re-points, retired-unit tombstones, the 42 new units + 7 presets + SAMP/T layout, and the `remove_vehicle` id-vs-name strip fix. NO 414th faction enrichment (P-37/SA-7/S-400 wiring stays fork-side). Opened 2026-07-01. Landed on the fork as [414Ret#382](https://github.com/bradyccox/414Ret/pull/382), so the fork keeps it either way.
  - [#847](https://github.com/dcs-retribution/dcs-retribution/pull/847) F-4E-45MC (Heatblur) loadout rebuild **+** Maverick date-fallback fix (period AIM-7E2/9L baseline; AGM-65 date-fallback rerouted Walleye → Mk-20 Rockeye). Opened 2026-06-28; **consolidated the former #845 + #846** (both also closed). Landed on the fork as [414Ret#322](https://github.com/bradyccox/414Ret/pull/322) + [#325](https://github.com/bradyccox/414Ret/pull/325).
  - [#842](https://github.com/dcs-retribution/dcs-retribution/pull/842) landmap prepared-index perf (carve queue item 1) — opened 2026-06-27.
  - [#791](https://github.com/dcs-retribution/dcs-retribution/pull/791) SAM site layouts + EWR pool.
- **Self-withdrawn (NOT rejected, NOT upstream):** [#784](https://github.com/dcs-retribution/dcs-retribution/pull/784) Iran pack (**re-carved clean as draft #886, late 2026-07-19**) · [#786](https://github.com/dcs-retribution/dcs-retribution/pull/786) AAQ-33 era restriction (folded into the merged #843) · [#790](https://github.com/dcs-retribution/dcs-retribution/pull/790) orbit deconfliction (still fork-only — re-carve if wanted) · [#891](https://github.com/dcs-retribution/dcs-retribution/pull/891) blue-block miz markers (**closed by the DM 2026-07-20, 25 min after Starfire13's review** — "352 EWRs in Normandy. Good lord…" made the 443-marker Normandy resurrection a non-starter, and the comment's real ask was **CJTF block-convention consistency** across object classes ("SAMs have to be defined with CJTF Red, but AAA and static armour groups allow both"). The fork implemented the full consistency rule same day — every loader class reads both blocks; `factories` was the remaining silent-drop hole with 3 shipped red-block factories resurrected. **The re-carve was DROPPED 2026-08-05 (DM call) on a finding that invalidates its premise:** the Custom-campaigns wiki carries a **"Unit Type Quick Reference" spec table assigning a required CJTF block per object class**, and upstream's loader matches it **exactly on all 19 classes** (Red: EWR/all 3 SAM ranges/ship/missile/coastal/offshore/neutral-FOB · Blue: factory · Either: AAA/armor/ammo/strike/comms/power/command-center/FOB). So nothing is "silently dropped" — a blue-block SAM marker is dropped because the author placed it in the block the documentation forbids, and the fork's read-both-blocks rule is a **deliberate deviation from a documented upstream spec**, not a bugfix. Making it a carve would be a *spec change* (uniform "Either" + a wiki edit), which is a maintainer design call and was not worth pursuing. See inventory item 17).
- **Closed, superseded (the 2025-11-27 + 2026-06-09→11 early carve attempts; no action owed):** #621, #622 (the initial uploads) · #774/#776 (final-waypoint crash, superseded by #788) · #775/#777 (AWACS orbit flip) · #778/#781/#783 (SCRAMBLE/scramble-logic flight types — the retired ramp-scramble line, see §1) · #779/#780 (C-130J JAMMING, §2) · #845/#846 (folded into #847).
- **Era-gate payload options — DONE (opened 2026-06-27 as #843):** the combined **"era-gate payload-editor options"** PR = JHMCS property gating (§24) **+** a redo of the withdrawn #786 AAQ-33 pod fix. Self-contained, no 414th deps, builds on the upstream `restrict_weapons_by_date` toggle; Black/mypy/pytest validated locally before push. See upstreaming-inventory item 11.

**Crowded upstream zones — do NOT carve into these without coordinating** (active non-414th PRs):
- Planning revamps — prokop7 [#676](https://github.com/dcs-retribution/dcs-retribution/pull/676) BARCAP, [#674](https://github.com/dcs-retribution/dcs-retribution/pull/674) SEAD/DEAD, [#678](https://github.com/dcs-retribution/dcs-retribution/pull/678) BAI, [#677](https://github.com/dcs-retribution/dcs-retribution/pull/677) attack-infra.
- QRA — geofffranks [#782](https://github.com/dcs-retribution/dcs-retribution/pull/782) (our reserve *feeds* this; don't resubmit).
- Frontline — geofffranks [#823](https://github.com/dcs-retribution/dcs-retribution/pull/823) (already adopted into the fork), Druss99 [#681](https://github.com/dcs-retribution/dcs-retribution/pull/681).
- SEAD — geofffranks [#772](https://github.com/dcs-retribution/dcs-retribution/pull/772).
- Kneeboard — geofffranks [#754](https://github.com/dcs-retribution/dcs-retribution/pull/754) (wait for it to land before carving §25/§27/§29).
- ATC — fully saturated ([#821](https://github.com/dcs-retribution/dcs-retribution/pull/821)/[#692](https://github.com/dcs-retribution/dcs-retribution/pull/692)/[#564](https://github.com/dcs-retribution/dcs-retribution/pull/564)/[#568](https://github.com/dcs-retribution/dcs-retribution/pull/568)); the 414th retired its ATC, so nothing to give here.

---

@docs/dev/CLAUDE-ci.md

---

## PINNED — do not modify

**`latest` git tag** — owned by `softprops/action-gh-release@v2` inside `414th-latest.yml`.
Do NOT delete it or manually push it — breaking it breaks the URL the squadron bookmarks.

**`414th-latest.yml`** — the sole rolling-release mechanism. Do NOT modify it without
understanding the impact. Test in a branch and verify the `latest` release after merging.
Do NOT add Discord webhook or other org-level secrets — the workflow uses only `GITHUB_TOKEN`.

**Local Python runtime** — before deleting anything under `tmp/`, inspect `.venv/pyvenv.cfg`.
The current Windows virtual environment may have
`home = ...\tmp\uv-python\cpython-3.11.15-windows-x86_64-none`; when it does,
that `tmp/uv-python` directory is the base interpreter for `.venv`, **not a disposable
cache**. Deleting it breaks `run_retribution.bat` with "No Python at ...". Either preserve
the directory or rebuild `.venv` against a permanent Python 3.11 installation first.
Cleanup scripts and agents must never recursively delete `tmp/` without this check.

**`resources/plugins/splashdamage3/Splash_Damage_3.4.2_414th.lua`** — the 414th's
buddy-tuned Splash Damage build (`overall_scaling=0.6`, `rocket_multiplier=0.8`,
`static_damage_boost=1`, shaped-charge rocket flags, `game_messages=true`). Do NOT overwrite
it from upstream. Settings are LOCKED by design: `plugin.json` has no `specificOptions` and
`sd3-config.lua` was removed. Don't reintroduce the config layer. (The *values* are an
upstream candidate — inventory item 21. **That carve is OVER: PR #880 was CLOSED 2026-08-06
on the DM's call — "it's a preference we use, not everyone else."** The tuning is a 414th
preference, not a bug fix owed upstream, so it lives here permanently. This is a deliberate,
named exception to the everything-upstreamable policy; do not re-carve it without a fresh
call. The two genuine *bugs* found alongside it — see below — are a different matter.)
**Audited against upstream's `Splash_Damage_3.4.2_Standard_Retribution.lua` + the wiki's
Plugin-Options page 2026-08-06** — all 33 exposed options agree with our locked values (the
percent options map through upstream `sd3-config`'s `/100`: `overall_scaling` 60→0.6, rocket
80→0.8, dynamic blast 100→1), and the value drift is the documented tuning. Two
upstream-authored blocks are absent from our copy, both **deliberately dropped** by the
bake-in commit `6f3fc284b` (2026-06-11), which names them: **`shipRadarDamageEnable`**
(HARM → ship radar), which stays out — it works by `obj:enableEmission(false)`, the call the
C-130 constraint records as a crash cause — and **`oca_aircraft_damage_boost`** (3000×,
parked aircraft, "so OCA/Aircraft missions are viable"), **RESTORED 2026-08-06 on the DM's
call**. The two were one contiguous region of the same function, so the OCA half reads as
collateral to the crash-risk removal; restoring it costs OCA/Aircraft strikes nothing and
buys back the kill probability upstream added it for.
⚠️ **Upstream's own copy of the OCA block is broken and ours is not a verbatim copy**: it
calls `getAGL(obj)`, a helper defined **nowhere** — not in the script, `Moose.lua`, or the
MIST shim (grep the tree: zero definitions) — so it raises "attempt to call a nil value" for
every object past `cascade_damage_threshold`, inside the `world.searchObjects` `ifFound`
callback. The fork's port computes AGL inline (`getPoint().y - land.getHeight`) and only for
aircraft. Do NOT "resync" this block from upstream until they fix it.

---

## Conventions

- **Anything published to GitHub is written plain (STANDARD, 2026-08-07 user call — "I'm not
  reading 90% of your output text, you need to cleanse it of your bullshit").** README, wiki
  pages, PR bodies, changelog entries, issue comments and commit messages state what changed and
  why. They do not perform.
  - **No voiceover.** No dramatic reveals ("Some of those circles are lies"), no
    "X isn't a Y — it's a Z", no rhetorical build-ups, no closing flourish.
  - **One fact per line.** If a bullet needs three sentences to land, it is three bullets or it
    is a table. Long paragraphs are the failure mode — nobody reads a 120-word bullet.
  - **Bold marks a term, not emphasis.** If every other phrase is bold, none of it is.
  - **Lead with the thing the reader came for.** Download links, the command to run, the actual
    change — first, not after three paragraphs of context.
  - **No changelog-in-prose.** "This was reworked twice, first as X then as Y" belongs in the
    design note, not in a reference page. State what is true now.
  - **Two exemptions.** In-fiction campaign material (briefing packs, intel assessments, role
    cards) keeps its voice — it is read aloud to a squadron and the voice is the point. Mirrored
    upstream wiki pages keep upstream's wording, with fork deltas in **414th:** notes.
  - **A doc that describes a removed feature is worse than a wordy one.** When a feature is cut,
    grep the README and `docs/wiki/` for it in the same change.
- **ADHD-friendly agent output (STANDARD, 2026-07-20).** The reader has ADHD; every agent
  reply is shaped so an ADHD brain can act on it. The rules live in the vendored
  [`i-have-adhd`](https://github.com/ayghri/i-have-adhd) skill
  (`.claude/skills/i-have-adhd/SKILL.md`, MIT, byte-identical to upstream — update by
  re-copying upstream's `skills/i-have-adhd/SKILL.md`; keep the sibling `LICENSE`). Treat it
  as **always-on**, not invoke-on-request: lead with the next action, number multi-step work,
  end with one concrete next action, defer tangents, restate state each turn ("step 3 of 5"),
  concrete time estimates, visible wins, matter-of-fact errors, lists capped at 5, no
  preamble/recap/closing pleasantries. The skill's own exceptions apply (full explanations
  when asked, confirm destructive actions, stop iterating in a debug spiral, one clarifying
  question on real ambiguity). Composes with the question convention below: a needed decision
  still lands in the ❓ block at the end — that block IS the "one concrete next action."
- **Ask decisions via the AskUserQuestion widget (STANDARD, 2026-07-21 user call).** Whenever
  you need a decision or a choice from the user, use the **`AskUserQuestion` tool** — the
  interactive widget with clickable options — **not** a typed "1, 2, 3" list. Lead with your
  recommended option and mark it "(Recommended)"; give each option a one-line description of what
  it means / its trade-off. Use `multiSelect` when the choices aren't mutually exclusive, and a
  short set of questions (≤4) when several independent decisions are on the table. The user
  considers typed numbered option lists low-effort ("lazy") — the widget is the actual tool for
  this, so default to it.
  - **Fallback — plain highlighted markdown** — only for a quick inline either/or where the widget
    is overkill, or for a **free-text** question with no fixed options. Never bury it mid-paragraph
    or at the tail of a wall of prose: put it in its own block at the **end** of the message, set
    off with a bold marker + blockquote, and lead with your recommended option, e.g.:
    > ❓ **Need your call:** <the question>
  - Do NOT build a custom widget/visualization (`mcp__visualize`, an Artifact) to ask a question —
    `AskUserQuestion` is the one decision surface.
- **Never name a paid campaign anywhere in the repo (STANDARD, 2026-08-07 user call).**
  Third-party DCS campaigns are commercial products. The fork studies them and extracts
  factual data from them (deck-static coordinates, kneeboard page formats, ATC command
  vocabularies), and that is fine — but their **names** do not appear in our code, comments,
  commit messages, PR titles/bodies, docs or wiki pages.
  - **Use stable letters**: `campaign A`, `campaign B`, … Letters are consistent across docs —
    A and B are the two the carrier deck-decor note uses — so a set stays traceable to a
    specific source mission (`campaign A mission 3`) and rules like "never mix sets across
    missions within a zone" stay checkable. Add the airframe when it aids reading
    (`a paid FA-18C campaign`). Publishers get the same treatment.
  - **Install paths are generic** — `<DCS>\Mods\campaigns\<campaign A>`, never the real folder.
  - **This applies to commit messages and PR metadata, not just files.** They are as public as
    the code; a rewrite + force-push on an unmerged branch is the fix.
  - **Three things are NOT covered.** Real-world squadron names and nicknames (VFA-83
    "Rampagers" is a real squadron the campaign is named *after*, not the reverse); real-world
    operation names (Inherent Resolve); and the fork's own campaign names, even where one
    collides with a paid product (our `red_flag_81_2`).
  - **Check with the installed list, not from memory** — `ls "<DCS>\Mods\campaigns\"` is the
    authoritative set of names to avoid.
- **Supply lines follow the driveable corridor (STANDARD, 2026-07-03).** Every authored
  `supply_routes:` / shipping-lane drawing must trace the corridor you would actually *drive*
  between the two points — the road, the river valley, the pass — never a straight line across a
  ridgeline. Retribution binds a route to its CPs by the **first and last** waypoint only, so
  intermediate waypoints are free: use enough of them (3–5) to follow the real corridor. On
  real-world-coordinate maps (Afghanistan, Syria, Sinai, PG, Kola, Normandy, Caucasus…) author the
  intermediates from the **real road network's lat/lon** via `tools/supply_route_geo.py`
  (`Point.from_latlng` → terrain XY; calibrated to ~1–5 km on Afghanistan). For fictional-overlay
  campaigns (e.g. Vietnam-on-Caucasus) trace the on-map roads/valleys visually instead. The tool is
  **multi-campaign** (`python tools/supply_route_geo.py [coin|red_flag_81_2|caucasus_trail_fixes]`);
  the COIN campaign (`coin_enduring_resolve.yaml`, Highway 1 / Route 611 / the Uruzgan road) and Red
  Flag 81-2 (`red_flag_81_2.yaml`, real US-95 / US-6 / the NTS interior) are the reference
  implementations. The built campaigns were audited against this standard 2026-07-03 (see the
  supply-routes design note "Roll-out to the built campaigns"): Nevada re-traced, the worst
  Caucasus-trail defects fixed, the deep-mountain trail FOBs (Yankee Station / Steel Tiger R6–R13)
  left for an in-app by-eye pass, Germany already compliant.
- **SAM belts: legacy → §60 doubling, strategic → regiment-by-authoring (STANDARD, 2026-07-12).**
  When you lay out a **new campaign's** air defenses, choose the redundancy model by system class —
  don't just drop fat single-site batteries:
  - **Legacy / mobile systems** (SA-2, SA-3, SA-6, Hawk, and the generic launcher sites) — a lone
    site is realistic and the §60 two-guidance-radar doubling already baked into their layouts is the
    right fix (defeats the single-HARM kill). Place them as normal; nothing extra to do.
  - **Strategic belts** (S-300 / S-400 / SA-10/20/21, Patriot, the long-range LORAD systems) — prefer
    the **regiment-by-authoring** pattern: place **several single-radar fire units + a shared EWR/
    acquisition site** on the CP and let MANTIS net them into one IADS, rather than one doubled fat
    site. That is the historically faithful survivability model (kill one battalion's radar, the
    regiment fights on) and it's what the engine + MANTIS already represent when you place multiple
    sites.
  - **Guardrail — never double-count radars.** §60 doubling and a regiment layout both add engagement
    radars. If a future engine "regiment" construct ever lands for a strategic system, revert §60's
    doubling for that system, and **record which systems are regiment-modeled vs §60-doubled** the day
    that starts. Rationale + the deferred directions (geometry, acquisition separation, decoys) live in
    [docs/dev/design/414th-sam-site-realism-notes.md](docs/dev/design/414th-sam-site-realism-notes.md).
  - **Reference implementation:** Red Tide's three rear S-300 hubs (2026-07-12) — 3 clustered
    single-radar S-300 battalions + a shared EWR per hub, netted by range-mode advanced IADS, with §60
    reverted only for that campaign's S-300/SA-5 via the `Russia 1980 (Red Tide)` faction fork (the
    front's legacy MERAD screen keeps §60 doubling). See `414th-red-tide-campaign-notes.md`.
- **Upstream dev-process standards (ADOPTED as ours, 2026-07-20 user call).** The upstream wiki's
  Contributing + Core development guides are the fork's own customs and standards, mirrored with
  **414th:** delta notes in `docs/wiki/` (see Project Docs). In practice: follow the
  **Developer's Guide** for dev-env + PR practice (small PRs — one feature/bugfix/change per PR;
  type annotations on all new code; pre-commit runs Black), the **aircraft/terrain module
  checklists** (upstream's P0–P2 items plus the fork's additions on each page) when adding module
  support, the **QGIS shapefile guide** for landmap data, **Modded-Unit-Support** (the 11-step
  guide) for any new mod pack, **Motorpools** when authoring reserve depots into a campaign,
  **Campaign maintenance** for the campaign-ownership model (every fork-authored campaign is
  owned: design note + CI lock), and the **Release process** page for releases (the rolling
  `latest` IS the release; pinned tags are `v<X.Y.Z>-414th`; never `git push --tags`).
  **Upstream carves ship to these same standards** — they are upstream's own, so a carve is held
  to them by construction: target `dcs-retribution/dev` via the PR fork, one focused
  feature/bugfix per PR, upstream's gates validated locally on the upstream tree before push, a
  `changelog.md` note, fork-only couplings stripped (the harness/plugin extras stay here), and
  module/campaign content meeting the relevant checklist page. When an upstream page changes,
  refresh the mirror and re-annotate the deltas rather than letting the two drift.
- Keep the doc faces in sync: when a feature lands or changes, update **both**
  [`README.md`](README.md) (player-facing) and the relevant section of
  [docs/dev/414th-features.md](docs/dev/414th-features.md) (engineering), plus this map if the
  shape changed. A push that moves the code past its docs is a broken push.
- Keep player-facing plugin behavior and any overview docs in sync with code changes.
- **AGENTS.md sync** — `AGENTS.md` is a byte-identical mirror of this file (CLAUDE.md is
  authoritative; only line 1, the title, differs). After editing CLAUDE.md or any `@`-imported
  file, resync it: `cp CLAUDE.md AGENTS.md` then Edit line 1 back to `# AGENTS.md ...`
  (do NOT use `sed -i`; it flattens CRLF). The imported files (`docs/dev/CLAUDE-architecture.md`,
  `docs/dev/CLAUDE-ci.md`) are shared — both CLAUDE.md and AGENTS.md reference the same files.
