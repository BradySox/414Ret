# AGENTS.md — 414Ret Claude Code Guide

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

The per-feature engineering internals and design rationale live in `docs/`, not in this
file. This guide is the map; those are the territory.

- [docs/dev/414th-features.md](docs/dev/414th-features.md) — **the deep dive**: every 414th
  feature with file paths, gotchas, tests, and deferred work. Read the relevant section
  before editing a feature.
- [docs/dev/414th-feature-index.md](docs/dev/414th-feature-index.md) — the generated **feature
  index**: a table of every numbered "Features at a Glance" feature (plus the engine plugins)
  with its plugin and `Settings` wiring. Source of truth is the **feature registry**
  `game/fourteenth/features.py` (regenerate with `python -m game.fourteenth.features`); a test
  (`tests/fourteenth/`) fails CI if a setting/plugin reference goes stale, the registry and the
  feature list fall out of sync, a checklist row points at an unregistered feature, or this doc
  drifts. **Register every new feature there** (add its §N) so the list, catalog, and checklist
  stay in lockstep.
- [docs/dev/414th-ingame-pass-checklist.md](docs/dev/414th-ingame-pass-checklist.md) — the
  **in-game pass tracker**: every "needs an in-game pass" item with an observable pass
  criterion + the fail signature to watch for. Update status when you fly it; clear the tag
  in `414th-features.md` when it reaches VERIFIED.
- [docs/dev/414th-upstreaming-inventory.md](docs/dev/414th-upstreaming-inventory.md) — the
  **upstreaming queue**: which generic fixes to carve toward `bradyccox/dcs-retribution`
  (priority-ordered, with readiness marks) and which fork-specific bits must NEVER go upstream.
- [docs/dev/414th-community-contribution-roadmap.md](docs/dev/414th-community-contribution-roadmap.md) —
  the **long view**: a two-axis (community-value × carve-difficulty) re-classification of
  *every* feature, separating the thin genuinely-414th content/identity/economy layer from the
  large generic-capability set, with a strip-list per feature and the ordered contribution waves
  for giving the rest back upstream.
- [docs/dev/design/](docs/dev/design/) — per-feature design notes (read before touching the
  matching code):
  - `414th-air-defense-planning-notes.md` — CAP/BARCAP/QRA planning intent
  - `414th-tic-dynamic-fronts-notes.md` — TIC stance/cadence movement design
  - `414th-tars-recon-notes.md` — TARS recon engine
  - `414th-c130-ew-isr-notes.md` — C-130J EW/ISR source of truth + retired `ewrj` warning
  - `414th-scar-task-spec.md` + `414th-scar-commander-sme-questions.md` — SCAR ground truth
  - `414th-scar-phase2-sof-plan.md` + `414th-scar-HANDOFF.md` — SCAR commander-capture plan + next-session pickup
  - `414th-aircraft-task-rebalance-rubric.md` — aircraft task-priority rebalance rubric
  - `414th-red-tide-campaign-notes.md` — Red Tide campaign laydown + `.miz`/faction edits
  - `414th-red-tide-supply-routes-notes.md` — YAML supply routes + Kastrup preset patch
  - `414th-campaign-maker-notes.md` — blank-start campaign maker (policy core landed; glue/wizard in progress)
  - `414th-weapon-dates-proposal.md` — weapon-coverage completion plan + the modern-weapon date-gating rule
  - **MIST → MOOSE consolidation & IADS engine** (✅ COMPLETE 2026-06-25 — MIST retired; read before
    touching IADS/plugins):
    `414th-mantis-iads-HANDOFF.md` (**start here** — MANTIS G6 in-game pass PASSED 2026-06-24
    (routing + networking + C2); MANTIS is the default IADS engine),
    `414th-framework-consolidation-notes.md` (the MIST-retirement roadmap + per-phase plan, now done),
    `414th-mantis-migration-notes.md` + `414th-mantis-vs-skynet-iads-parity.md` (the Skynet → MANTIS
    IADS engine migration, now **complete**: **MANTIS is the sole IADS engine — Skynet is removed**
    (the `skynetiads` plugin, the `iads_engine` selector, and the dual-engine wiring are all dropped;
    a tiny `IadsEngine` enum stub remains only so pre-removal saves unpickle before the value is
    migrated out). The shared IADS data model — `IadsNetwork`, `IadsRole`, `IadsProperties` and the
    `Skynet*` back-compat aliases — stays; MANTIS consumes it),
    `414th-moose-ops-opportunity-map.md` (which MOOSE `Ops.*` modules to adopt vs. keep in Python —
    e.g. `Ops.Chief` stays out; **the next phase now that MIST is gone**), and the per-plugin decisions
    `414th-ewrs-retirement-decision.md`, `414th-dismounts-decision.md` (both retired),
    `414th-mist-moose-shim-notes.md` (**the shim that retired MIST** — a vanilla-DCS `mist` compat shim
    live in `base/plugin.json`, replacing the shelved `414th-ctld-mantis-style-port-scope.md` `Ops.CTLD` port)
  - Drafts / not-yet-landed (design only): `414th-mission-planning-wiki-rework.md`
    (upstream wiki rewrite), `414th-scenery-import-notes.md` (scenery strike targets),
    `turnless.md` (turnless-campaign exploration),
    `414th-airwar-planner-consolidation-notes.md` (behavior-preserving consolidation of the
    air-war planner's threat-field + standoff geometry onto one `AirspaceGeometry` service;
    keeps the brain in Python, Tier-C/`Ops.Chief` explicitly out of scope),
    `414th-scar-king-fac-notes.md` (SCAR rework: a player-first loiter/"hold" package tasked by
    the C-130 "King" on-scene commander onto real static armor TGOs so losses track natively;
    minimal-F10 designation; thin MOOSE bridge, not `Ops.Chief`; future auto-planned commander),
    `414th-combat-sar-normal-task-notes.md` (make Combat SAR a normal, default-on, **two-sided**
    auto-task: AI rescues AI on blue+red, players can drop in; phased verify-blue → default-on →
    AI-rescue scoring → symmetric red; today the engine is blue-only + the AI-rescue scoring is cosmetic)
- [README.upstream.md](README.upstream.md) — unmodified upstream project README (setup,
  dependencies, wiki links).
- `AGENTS.md` mirrors this file — see **Conventions** below for the sync process.

---

## Tech Stack

| Layer | Choice |
|---|---|
| Campaign engine | Python 3.11 (`game/`) |
| UI | PyQt (`qt_ui/`) + React/Leaflet client (`client/`) — client NOT type-checked in CI |
| Mission scripting | **Lua 5.1** sandbox plugins (`resources/plugins/`) — no `os`/`io`, no `goto`, definition order matters |
| In-mission framework | **MOOSE** (bundled `Moose.lua`; some plugins vendor classes verbatim) — the standard. **MIST is RETIRED** (MIST → MOOSE consolidation complete, 2026-06-25): `base/plugin.json`'s `"mist"` work-order now loads `resources/plugins/base/mist_moose_shim.lua` — a vanilla-DCS shim implementing the 42 `mist.*` symbols the consumers (CTLD, SCAR, intercept glue, core `dcs_retribution.lua`, Skynet) actually call, so `mist_4_5_126.lua` no longer loads. The old `mist_4_5_126.lua` file is **kept in the repo as a one-line rollback** (revert `plugin.json`) until the shim has been flown across more campaigns; delete it as the final cleanup. Do NOT re-point the work-order back without reason. See `414th-mist-moose-shim-notes.md`. MOOSE API docs (bookmark): https://flightcontrol-master.github.io/MOOSE_DOCS_DEVELOP/Documentation/index.html |
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
work-order plugins. TIC, TARS, and SCAR additionally need their main script loaded **after**
every plugin's config table exists (their init reads `dcsRetribution.plugins.<name>` / MOOSE
at file scope) — an ordering the per-plugin work-order pass can't express. They are `LuaPlugin`
subclasses (`game/plugins/{tic,tars,scar}.py`, registered in `manager.py`'s `_PLUGIN_CLASSES`)
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
every `resources/plugins/**/*.lua` as a blocking syntax gate — it catches parse-time errors,
but runtime behavior still needs an in-game pass (see the in-game-pass checklist).

---

## Features at a Glance

Full internals for each are in [docs/dev/414th-features.md](docs/dev/414th-features.md)
(section numbers below).

1. **QRA intercept reserve** — per-squadron alert reserve feeding the upstream PR #782 Moose
   `AI_A2A_DISPATCHER`. Base-defense posture by default. (Old ramp-scramble is retired.)
2. **JAMMING flight type** — C-130J as EC-130H/RC-130H EW+ISR platform (`c130j` plugin);
   the old generic `ewrj` fighter-pod jammer is retired and must not be restored.
3. **TARPS recon + BDA fog-of-war** — player F-14 photo recon; viewer-aware fog (damage lag +
   recon intel-fog) makes recon worth flying.
4. **UI transparency** — Target Intel panel, Mission Impact debrief summary, package context
   bar, flight-creation context, building-card cleanup.
5. **Player target location precision** — `Approximate` mode offsets steerpoints + hides exact
   marks/coords so players must visually acquire.
6. **Air-defense planning rework** — overlapping/jittered BARCAP waves, forward CAP line,
   threat-weighted BARCAP volume, a map-scaled **red forward-middle BARCAP layer** (added,
   not relocated; via a `ForwardBarcapZone` target), front-line navmesh routing hazard,
   unstacked FLOT units.
7. **Auto-hide mobile SAMs on MFD** — SHORAD/AAA/MANPAD hidden from datalink, including
   escorts inside armor/missile groups; standalone MERAD/LORAD stay visible for SEAD.
8. **Robustness / crash fixes** — flight-exit IndexError, AWACS/tanker orbit, malformed mod
   payload Lua.
9. **TIC — Troops In Contact** — scripted frontline firefights with per-stance movement +
   414th ambient-fire extension (plugin, default ON).
10. **CurrentHill Iran assets pack** — Shahed-136, IRGCN FAC, `[CH] Iran 2020` faction.
11. **Native DCS DTC cartridge export** — RETIRED (2026-06-26): half-baked; never
    pre-loaded reliably and ED is shipping native DTC. Do not restore. (§11)
12. **TARS recon engine** — MOOSE Ops.TARS runtime for TARPS, feeds confirmed BDA (default ON).
13. **Flight Control ATC** — RETIRED (2026-06-26): half-baked MOOSE FLIGHTCONTROL tower
    comms plugin; removed. Do not restore. (§13)
14. **Plugin Options UI** — `descriptionInUI` field + label/default polish across all plugins.
15. **SCAR — RESCAP "Sandy" rescue escort** — repurposed (rescue rework, design note
    `414th-scar-rescue-rework-notes.md`) from the **retired** armor-hunt task into the rescue-escort
    role of the **Combat SAR package** (`FlightType.SCAR`, A-10C/AH-64D, scoped to the FLOT). The
    standing package = **1 King (C-130) + 1 Jolly Green (helo) + 2–4 Sandy**; Sandy protects the downed
    pilot, suppresses the threats around them, and walks the rescue helo in. **Enemy-capture race**
    (`combatsar` plugin): on ejection a CJTF_RED snatch party may race to seize the survivor — kill it
    to save, or the pilot is **CAPTURED** (`combat_sar_captures` state global) and held as a **POW at
    an enemy airfield** (`PendingPowRecovery` + `CapturedPilotGroundObject`, offering CSAR). A
    **surviving CSAR raid** or **recapturing the field** frees the aviator; a POW abandoned past the
    4-turn clock is **killed**. AI safety-net package via `auto_combat_sar` (King + Jolly + 1 Sandy).
    The old armor-hunt scenario + its auto-planner are **deleted** (2026-06-27: `scarluadata.py`, the
    `scar` plugin, `PlanScarHunts`/`PlanScar`, `scar_autoplan*`); the SOF/CSAR recovery plumbing was
    repurposed for the POW path. features doc §15.
16. **Settings QOL audit** — dead/duplicate setting cleanup (four fields removed), AI-radio
    booleans consolidated into the `AiRadioBehavior` enum with deterministic save migration,
    plugin wording, and a UI-layer grouping/dependency handoff
    ([docs/dev/settings-qol-audit.md](docs/dev/settings-qol-audit.md)).
17. **Auto-planner target unpredictability** — opt-in, per-side
    (`ownfor_/opfor_planner_unpredictability`, default 0) weighted-random reordering of the
    HTN's *opportunistic* offensive targets (strike/OCA/BAI/anti-ship/non-threatening DEAD)
    so red stops hitting the same things every turn; reactive threat response stays strictly
    deterministic. The low-risk in-Python alternative to a runtime MOOSE `Ops.Chief` red
    rewrite (`game/commander/tasks/targetorder.py`; features doc §17).
18. **Fog-of-war overview toggle** — a transient **"Reveal fog of war"** checkbox in the unified
    map layers panel (#19, "Enemy intel" group) that short-circuits the three recon-fog
    leaves to ground truth, un-fogging the whole map + intel dialogs (enemy composition, threat
    rings, hidden command posts) with no server-model changes. `PUT /fog-of-war/reveal` flips the
    flag, then the client re-pulls `/game`. Never persisted; defaults off
    (`game/theater/fogofwar.py`, `game/server/fogofwar/`; features doc §3).
19. **Unified map layers panel** — one custom, dark-themed Leaflet control
    (`client/src/components/maplayers/MapLayersControl.tsx`) replacing both stock layer controls:
    collapsible grouped sections (advanced groups start collapsed), preset views (Default / SEAD /
    Recon / Clean), and `localStorage`-persisted choices (except the transient fog overview). The
    old top-left threat-zone/navmesh/terrain control is folded in; side-effect toggles run via
    `useEffect`, not Leaflet add/remove. Client-only; needs the CI client rebuild (features doc §18).
20. **Drop-spawn: map right-click unit placement** — right-click blank map space → Qt dialog
    (coalition / category / unit-type picker from all 66 named `LAYOUTS` / unit rows / deploy-timing
    / respawn) → `place_unit_group()` validates terrain + 200 km range, creates TGO, fires SSE so
    the marker appears immediately. Right-click a user-placed TGO to remove it (`DELETE /tgos/{id}`).
    Deploy Next Turn queues a `PendingUnitPlacement` materialised at turn start. Two cheat settings:
    `enable_unit_placement` (unlock) + `enable_free_unit_placement` (no cost).
    (`game/theater/unitplacement.py`, `qt_ui/windows/groundobject/QPlaceUnitGroupDialog.py`,
    `client/src/components/liberationmap/MapContextMenu.tsx`; features doc §20.)
21. **Combat SAR** — bespoke player pilot-rescue flight type (`FlightType.COMBAT_SAR`): a CH-47
    orbits the FLOT as the rescuer, a C-130 flies the HC-130 "King" overhead orbit (air-tracking
    **TACAN-only** beacon — no ADF — + F10 LARS survivor-locator), driven at runtime by the bundled
    MOOSE `CSAR` engine (`combatsar` plugin). Optional AI standing alert (`auto_combat_sar`, default
    OFF). **Rescue scoring closes the loop:** delivering a downed pilot to a friendly field spares the
    aviator at debrief (airframe still lost) — the `combatsar` plugin's `OnAfterBoarded`/`OnAfterRescued`
    hooks append the ejected unit name to the `combat_sar_rescues` state global, and
    `commit_air_losses` skips that pilot's kill (fail-safe: empty list = pre-scoring behaviour).
    Distinct from the SCAR SOF-recovery `FlightType.CSAR` (§15). (`game/ato/flighttype.py`,
    `game/commander/tasks/primitive/combatsar.py`, `game/sim/missionresultsprocessor.py`,
    `resources/plugins/combatsar/`; features doc §21, spec `414th-combat-sar-spec.md`.)
22. **Kneeboard space-utilisation + custom import** — sparse kneeboard pages (Combat SAR,
    Support, Mission Info) restyled to fill the page with a *light* heading + underline-rule +
    whitespace layout (no boxes), and the Friendly Packages list flows into two columns when
    long (`KneeboardPageWriter.rule()`/`vspace()`/`table_two_column_paginated()`). Plus a
    **custom-kneeboard import** UI (`QCustomKneeboardsWindow`, *Kneeboards* toolbar action):
    import an image once → stored in the campaign save as `game.custom_kneeboards`
    (`CustomKneeboard` = name + PNG bytes + optional `airframe_id`) → injected into every client
    flight (or one airframe) at generation by `KneeboardGenerator._inject_custom_kneeboards()`.
    Per-campaign (no cross-campaign leak like the global `Kneeboards/` folder); old saves migrate
    via `__setstate__`. (`game/customkneeboard.py`, `game/missiongenerator/kneeboard.py`,
    `qt_ui/windows/kneeboards/QCustomKneeboardsWindow.py`; features doc §4, checklist H1/H2/H4.)
23. **Per-squadron DCS country** — each squadron's air units spawn under their own DCS *country*
    (`squadron.country`, already set by preset YAML / inherited from the faction) so a mixed-nation
    CJTF side gets nation-specific voiceovers/comms instead of one shared faction voice. A
    `CountryAssigner` (`game/missiongenerator/countryassigner.py`) resolves the country per
    squadron, registers every per-side nation on the coalition, and enforces the DCS one-country-
    per-coalition rule (blue claims first; colliding red squadrons fall back to the red faction
    country) while interning one canonical `Country` instance per id (pydcs attaches groups to the
    instance). No-op for single-nation factions (the squadron loader already restricts them to the
    faction country). Implements upstream issue #627. **Nation-aware pilot names** complete the
    arc: `Squadron.faker` now draws from the squadron's own DCS country (a curated country→Faker-
    locale table in `game/squadrons/pilotnames.py`) instead of the shared faction locale, so the
    Greek squadron rosters with Greek names, the Iranian with Persian, etc.; unmapped/multinational
    countries fall back to the faction faker (never breaks generation), and the logic is fully
    unit-tested (`tests/squadrons/test_pilotnames.py`). (`game/missiongenerator/missiongenerator.py`,
    `game/missiongenerator/aircraft/aircraftgenerator.py`, `game/squadrons/pilotnames.py`;
    features doc §23, checklist I1/I5.)
24. **Date-gated aircraft properties** — extends the existing `restrict_weapons_by_date` toggle from
    weapons to era-defining payload-editor *properties*. First curated gate: **JHMCS** helmet cueing
    (fielded ~2003) is hidden from the dropdown and clamped to the baseline visor when generating a
    pre-2003 mission. A small hand-authored table (pydcs carries no property dates) keyed by value
    *label* — so the F/A-18/F-16 "JHMCS" is gated but the Su-30/Su-35 "SURA Visor" (same id) is not —
    scoped to the helmet-device identifiers. UI filters the dropdown; the generator
    (`degrade_props_for_date`) is authoritative and resolves against the unit-type default so the
    defaulted-JHMCS case is caught. (`game/dcs/aircraftproperties.py`,
    `game/missiongenerator/aircraft/flightgroupconfigurator.py`,
    `qt_ui/windows/mission/flight/payload/propertycombobox.py`; features doc §24, checklist I3.)
25. **Compact 3-4 page kneeboard deck** — `compact_kneeboard` (default ON) folds the optional kneeboard
    content into at most four pages instead of the ~10-page sprawl: **P1 Game Plan** (a **BLUF** band —
    task/target/TOT, push + success/abort code words, top live threat + how-to-defeat, bullseye — over
    airfields/route/fuel/weather), **P2 Threats & Targets** (target ALIC over the enemy-AD threat cards),
    **P3 Comms & Coordination** (radios + AWACS/tanker/JTAC + code words + brevity), and an
    adaptive **P4 Flex** (recon target photo when target-recon imagery is on, else just the Fuel Ladder).
    The **friendly-package list** rides on the always-present **cover page** (§30) in compact mode (recon
    imagery owns the flex slot, so it had nowhere else; built once per shared-airframe deck). The **Fuel
    Ladder** is one glanceable `Fuel` column (planned remaining) per steerpoint with the RTB surplus —
    constant across the route by construction — surfaced once, replacing the redundant Plan/Min/Margin trio.
    The composite pages reuse the existing page classes via new `render_into`/`render_*` section methods +
    `_draw_section_if_fits` (lower-priority sections drop rather than spill past 4; `render_section`
    self-guards so a dropped package list never strands a lonely heading); the BLUF strings come from
    `_bluf_lines` (top-threat is always-on). The map image + Notes page aren't generated in this mode;
    turning it **off** restores the full multi-page deck byte-for-byte (separate assembly path
    `_compact_kneeboard_pages`). (`game/missiongenerator/kneeboard.py`, `game/settings/settings.py`;
    features doc §4, checklist H9.)
26. **Off-mission combat fidelity + PLAYER_AT_IP fix** — the sim auto-resolves engagements the player
    doesn't fly. Abstract combat was numbers-only coin flips (more flights win; survivors die 50/50; SAMs a
    flat 50%), so obsolete jets beat modern ones and SEAD meant nothing. `game/sim/combat/capability.py`
    now weights A2A by best A2A `task_priority` × count (win = strength share, survivor loss scales with
    margin, clamped ≤ legacy 0.5) and SAM survival by SEAD role/capability + engaging-site count; `aircombat.py`
    / `defendingsam.py` call it (`SKIP` untouched). Separately, **"Player at IP"** was silently defeated by
    the default `PAUSE` resolution ending the fast-forward at the first combat *anywhere* before a
    ground-started player reached its IP; `AircraftSimulation._combat_pauses_fast_forward` now lets AI-only
    combats keep resolving during a `PLAYER_AT_IP` fast-forward (only player-involving combats pause).
    (`game/sim/combat/`, `game/sim/aircraftsimulation.py`; features doc §26, checklist J1/J2.)
27. **Shared-airframe kneeboard index** — DCS scopes kneeboards per *airframe*, so every pilot of a type
    sees all that type's flight decks stacked. `KneeboardGenerator.generate` keeps each flight's pages a
    contiguous, callsign-sorted block and prepends a one-page **index** (callsign / task / start page) only
    when 2+ client flights share the airframe (a lone flight is unchanged). `pages_by_airframe` →
    `client_flights_by_airframe` + `_build_kneeboard_index` + `KneeboardIndexPage`.
    (`game/missiongenerator/kneeboard.py`; features doc §27, checklist H10.)
28. **Settings IA reorg + difficulty presets** — the settings dialog + New Game wizard are
    100% metadata-driven (they walk `Settings.pages()/sections()/fields()`), so a single ordered
    `FIELD_LAYOUT` table (`game/settings/settings.py`, from `_LAYOUT_SPEC`) now drives the whole
    layout — no field declarations moved, no behaviour change, no save migration. It kills the two
    34/37-item "General"/"Gameplay" grab-bags, regroups everything into six focused pages
    (**Difficulty & Realism · Air Doctrine · Campaign Management · Mission Generation · Kneeboards ·
    Performance**), and centralises scattered difficulty knobs onto Difficulty & Realism. On top of
    that, **difficulty presets** (`game/settings/difficultypreset.py`: `DifficultyPreset` Casual/
    Normal/Veteran/Ace + `apply_preset`/`detect_preset`) — a one-click `DifficultyPresetBar` atop the
    Difficulty & Realism page sets 12 difficulty-defining fields together (Normal == stock defaults);
    every setting stays hand-editable after. The classmethods fall back to a field's own
    `page=`/`section=` metadata for anything absent from FIELD_LAYOUT, so nothing is ever dropped.
    (`game/settings/settings.py`, `game/settings/difficultypreset.py`,
    `qt_ui/windows/settings/QSettingsWindow.py`, `qt_ui/uiconstants.py`; features doc §28,
    checklist K1.)
29. **Campaign SITREP kneeboard band** — a "what happened last turn" digest on the next mission's
    kneeboard cover page (a cockpit intel brief). `MissionResultsProcessor.commit()` gets a final
    `record_sitrep` step that reads the debriefing it already has — per-side losses (`loss_counts`),
    base captures (the cached pre-commit snapshot), Combat SAR rescues — into a `Sitrep`
    (`game/sitrep.py`) stored as `game.last_sitrep` (pickled, `__setstate__` default None). Enemy
    losses are framed as **"claimed"** to respect the recon-fog model. The SITREP renders on the
    always-present **cover page (§30)** as a "SITREP — Turn N" section, gated by `sitrep_for_kneeboard`;
    hidden on turn 1 / a quiet turn / when the `generate_sitrep_kneeboard` toggle (Kneeboards page,
    default ON) is off. v1 covers losses/captures/rescues; front movement + SCAR commander capture are
    deferred. (`game/sitrep.py`, `game/sim/missionresultsprocessor.py`, `game/game.py`,
    `game/missiongenerator/kneeboard.py`, `game/settings/settings.py`; features doc §29,
    checklist K2.)
30. **Dedicated kneeboard cover page** — a single front sheet that **always** leads a flight's deck,
    consolidating four things: the **operation/turn/date header** (new — every deck opens telling you
    what op + turn), the previous turn's **SITREP** (§29, moved off the briefing-page band so it stops
    crowding the flight plan), the shared-airframe **flight index** (§27, was a separate conditional
    page), and — in compact mode — the coalition-wide **friendly-package list** (moved here because the
    recon photo owns the flex page, and the cover's lower half was empty; §25). `CoverPage`
    (`_build_cover_page`) is always prepended in `KneeboardGenerator.generate`, replacing the conditional
    `KneeboardIndexPage` and the `BriefingPage` SITREP band. The cover is page 1 so decks start on page 2
    (the §27 start-page math is preserved); the index section appears only for 2+ shared-airframe flights,
    the SITREP section only when there's something to report, and the packages section only in compact mode
    (the full deck keeps its standalone `FriendlyPackagesPage`).
    (`game/missiongenerator/kneeboard.py`, `game/sitrep.py`; features doc §30, checklist K2/H10.)

---

## Repo & Branch Layout

- This repo (`bradyccox/414Ret`) `main` = the consolidated, most-up-to-date 414th build.
- Upstream is `dcs-retribution/dcs-retribution`; the 414th's PR fork is
  `bradyccox/dcs-retribution`.
- The 414th's primary "all features" working branch in the dev checkout is
  `414th-all-features`; `main` here = that + the Iran pack + a Black/mypy lint pass.

### Upstream PR ledger (snapshot 2026-06-27 — re-verify with `gh pr list`, don't trust this stale)

Carved out of this work, against `dcs-retribution/dcs-retribution` (all authored by `bradyccox`):

- **Open (awaiting review):**
  - [#843](https://github.com/dcs-retribution/dcs-retribution/pull/843) era-gate payload-editor options: JHMCS property gating (§24) + targeting-pod era data (re-does withdrawn #786) (carve queue item 11) — opened 2026-06-27.
  - [#842](https://github.com/dcs-retribution/dcs-retribution/pull/842) landmap prepared-index perf (carve queue item 1) — opened 2026-06-27.
  - [#841](https://github.com/dcs-retribution/dcs-retribution/pull/841) plugin `descriptionInUI` field (§14, carve queue item 10) — opened 2026-06-27.
  - [#828](https://github.com/dcs-retribution/dcs-retribution/pull/828) recon fog-of-war (§3) — the flagship carve, mergeable.
  - [#806](https://github.com/dcs-retribution/dcs-retribution/pull/806) configurable cruise/patrol altitude.
  - [#805](https://github.com/dcs-retribution/dcs-retribution/pull/805) bulk waypoint altitude UI — ⚠️ **CHANGES_REQUESTED, action owed**.
  - [#794](https://github.com/dcs-retribution/dcs-retribution/pull/794) hide mobile SAM in combined groups (§7).
  - [#793](https://github.com/dcs-retribution/dcs-retribution/pull/793) building-card placeholder (§4).
  - [#792](https://github.com/dcs-retribution/dcs-retribution/pull/792) wind override UI.
  - [#791](https://github.com/dcs-retribution/dcs-retribution/pull/791) SAM site layouts + EWR pool.
  - [#788](https://github.com/dcs-retribution/dcs-retribution/pull/788) inflight final-waypoint crash (§8).
  - Several created mid-June show `mergeable: UNKNOWN` — **likely need a rebase on current `dev`**.
- **Merged:** [#826](https://github.com/dcs-retribution/dcs-retribution/pull/826) weapons coverage/repairs · [#789](https://github.com/dcs-retribution/dcs-retribution/pull/789) inverted OPFOR aggressiveness fix.
- **Self-withdrawn (NOT rejected, NOT upstream):** [#784](https://github.com/dcs-retribution/dcs-retribution/pull/784) Iran pack · [#786](https://github.com/dcs-retribution/dcs-retribution/pull/786) AAQ-33 era restriction · [#790](https://github.com/dcs-retribution/dcs-retribution/pull/790) orbit deconfliction. The Iran pack and AAQ-33 fix are therefore **still fork-only** — re-carve if wanted.
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
`sd3-config.lua` was removed. Don't reintroduce the config layer.

---

## Conventions

- **Highlight questions to the user.** Whenever you need a decision or answer from the
  user, make the question visually prominent — never bury it mid-paragraph or at the tail of
  a wall of prose. Put it in its own block at the **end** of the message, set off with a bold
  marker and a blockquote, e.g.:
  > ❓ **Need your call:** <the question>

  When you offer choices, **number them (1, 2, 3, …)** and lead with your recommended option,
  so the user can reply with just a number. List multiple questions as a short numbered set so
  each can be answered individually. Use **plain highlighted markdown only** (bold + blockquote)
  — do NOT build a widget or visualization for this. (The `AskUserQuestion` tool already renders
  prominently and satisfies the convention; otherwise it is for free-text questions in ordinary
  replies.)
- Match the surrounding code's style; run the three validation commands (in `CLAUDE-ci.md`) before pushing.
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
