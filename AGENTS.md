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
7. **If a feature's RULE changed (not just its internals): grep the docs for the phrases the
   change falsified.** Steps 1-6 cover the feature's own faces; they do not cover the other
   notes that merely mention it. `§3` is named in **50 doc files** — the 2026-08-18 rework
   updated 16 and left **8 stale claims**, two of them on the published wiki. Grep for the old
   rule in its own words ("until scouted", "BDA lag", the removed setting name), not for the
   `§N`. Audited in `docs/dev/design/414th-doc-mass-notes.md`.

   **Run the audit rather than the grep** — `python tools/audit_stale_docs.py` checks every
   published file (README and `docs/wiki/`) against a table of removed
   features and exits non-zero on a hit. It is only as good as that table: **when you remove
   a feature, add its `Removed` row in the same change.** The 2026-08-07 CSAR replacement is
   why it exists — the design note was updated and five published pages, one of them
   sidebar-linked and written in the present tense, went on briefing a package that no
   longer existed for thirteen days.

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
| [414th-upstreaming-inventory.md](docs/dev/414th-upstreaming-inventory.md) | The upstreaming queue, priority-ordered, with readiness marks. Also carries the **upstream issue ledger** — the standing triage of upstream's open issues, first swept 2026-08-20. |
| [414th-community-contribution-roadmap.md](docs/dev/414th-community-contribution-roadmap.md) | The long view: community-value × carve-difficulty across every feature. |
| [414th-retribution-long-view.md](docs/dev/design/414th-retribution-long-view.md) | Structural read of the engine (2026-08-17): what Retribution is, measured, and the seven seams that follow. **1 (mission→campaign reporting) and 4 (the front line) are BUILT** as §91 and §90; **2 (the intel model) and 5 (time between turns) are accepted, not started**; 3 is analysis only; 6 is scoped in its own note. **Seam 7 (the enemy) is DROPPED** — three framings, three Phase 0s, no observable defect found; read §8 and [414th-red-brain-phase0-notes.md](docs/dev/design/414th-red-brain-phase0-notes.md) before proposing anything about red, because §55 tried the obvious shape and the analytic route has now failed three times. |
| [414th-campaign-architecture-notes.md](docs/dev/design/414th-campaign-architecture-notes.md) | **Direction note (2026-08-20, DM call): the one-substrate architecture.** The graveyard's shared diagnosis (private numbers, no substrate), five pillars (flow-network substrate, mission-as-transaction, event-driven turns, red legibility, command-by-weight), the four admission rules, and rungs R0–R7 with gates and falsifiers. Nothing built; no tombstone lifted — each rung lands on its own call. |

### Campaign notes — `docs/dev/design/`

Read before touching a campaign's `.yaml`, `.miz` or build tool.

| Campaign | Note |
|---|---|
| Germany — Red Tide | `414th-red-tide-campaign-notes.md` (+ `-supply-routes-`, `-c2-real-buildings-HANDOFF`) |
| Operation Baltic Fury | `414th-baltic-fury-campaign-notes.md` |
| Marianas — Second Island Chain 2027 | `414th-marianas-2027-campaign-notes.md` |
| Marianas — Operation Forager (1944) | `414th-marianas-wwii-terrain-notes.md` (the terrain note owns it) |
| Iraq — Umm al-Ma'arik (Desert Storm) | `414th-desert-storm-campaign-notes.md` |
| Iraq — Operation Inherent Resolve | `414th-inherent-resolve-campaign-notes.md` |
| Afghanistan — Enduring Resolve (COIN) | `414th-coin-HANDOFF.md` — **start here for COIN** |
| Caucasus — Iron Gate | `414th-iron-gate-campaign-notes.md` |
| Nevada — Red Flag 81-2 | `414th-red-flag-81-campaign-notes.md` |
| Vietnam set | `414th-vietnam-retribution-HANDOFF.md`, `-notes.md`, `-ops-notes.md`, `-red-tempo-notes.md`, `-airbase-harassment-notes.md` |
| Iraq map 2.9.28 content | `414th-iraq-map-2928-notes.md` — authoring plan, not yet built |

### System notes — `docs/dev/design/`

- **IADS / air defense** — `414th-mantis-iads-HANDOFF.md` (**start here**),
  `-migration-notes`, `-vs-skynet-iads-parity`, `414th-sam-site-realism-notes.md`,
  `414th-air-defense-planning-notes.md`, `414th-qra-player-manning-notes.md`,
  `414th-sam-magazines-notes.md` (**scoping only, nothing built** — cross-turn SAM missile
  stock on the §81 architecture; the MANTIS/ROE seam is verified clean and the off-mission
  drain hook found, so it is buildable on a decision)
- **EW / ISR / comms** — `414th-c130-ew-isr-notes.md`, `414th-comms-jam-notes.md`,
  `414th-comint-notes.md`, `414th-gps-jamming-notes.md`,
  `414th-iads-c2-consequences-notes.md`
- **Recon** — `414th-tars-recon-notes.md`, `414th-recon-role-scoping-notes.md`
  (**scoping only, nothing built** — what job recon gets now that engaging a site is the
  only reveal; also records the command-post hole the rework opened)
- **CSAR** — `414th-csar-notes.md` (**the one CSAR doc**; supersedes the eight earlier
  SCAR/CSAR notes, each bannered), `414th-scar-rescue-rework-notes.md`
- **COIN** — `414th-coin-insurgent-replenishment-notes.md`, `-reinfiltration-notes.md`
- **Naval** — `414th-cruise-missile-raids-notes.md`, `414th-naval-magazines-notes.md`,
  `414th-carrier-deck-decor-notes.md`
- **Ground / frontline** — `414th-tic-dynamic-fronts-notes.md`
- **AI behaviour** — `414th-ai-threat-reaction-notes.md` (**§94, adopted 2026-08-24 from
  juanjux #63** — why the baseline is Passive Defense, the `aiReactionExempt` protocol any
  plugin setting reaction-on-threat must use, why we took his head and not the merged PR,
  and the pre-registered falsifier if AI attrition rises)
- **Neutral factions** — `414th-neutral-border-defense-notes.md` (**§96** — the engine
  verdict on why a true neutral cannot fire, the opposing-coalition clone mechanism, the
  DM-locked rules incl. derived alignment (airfield-hosting decides the side), the
  overflight/refuses split, the accepted shadow-risk and its recorded fallback, the
  real-data border pipeline, and the DECIDED-not-built automagic direction;
  fictional-overlay campaigns are out of scope),
  `414th-national-postures-notes.md` (**RESEARCHED 2026-08-25, data drafted, nothing
  wired** — `resources/borders/national_postures.yaml`: 47 countries, 244 dated posture
  ranges, both blocs, five buckets. Also the measured country-per-map table that
  **corrected four errors in the research brief's from-memory list** (India on the
  Afghanistan map; no Qatar/Bahrain/Saudi on the Persian Gulf map; Belgium not Germany
  on Normandy/Channel; Saudi Arabia on the Syria map), the two rules that decide the
  hard cases, and the four gaps between the data and §96 as built. **Armenia and
  Azerbaijan are not pydcs countries either** — the same hole as Turkmenistan, on the
  most-used terrain). **Answers the pre-1991 geometry blocker**: CShapes 2.0 is
  CC BY-NC-SA and historical-basemaps is GPL-3, both gated, but **GSHHG/CIA World
  Data Bank II is LGPL over US-Government public domain** and its 1972-77 vintage
  covers every boundary the fork needs — the work is assembling its line segments
  into polygons, not finding data
- **Strike targets / BDA** — `414th-scenery-kill-tracking-notes.md` (why some scenery strike
  targets never register as killed; the M4 IADS stand-in; the proxy unit that was built and
  reverted, and the position matcher measured to have no input. **The reported failure was never
  reproduced — read §8.1 before building anything here**)
- **Planning / doctrine** — `414th-planner-doctrine-mining-notes.md` (**the working
  procedure for teaching the scripted planner, and the queue** — juanjux's LLM played six
  campaigns as red and wrote down what a competent commander must do; we mine that for
  things our planner *cannot express*, and build them as ordinary Python. **No LLM runs in
  this fork under this programme** — not behind a setting, not opt-in. Read its guardrails
  before proposing anything: seam 7 stays dropped, and the method changes the cost of a
  candidate, never the standard of proof. First one built is §69's CAS extension),
  `414th-falcon-bms-campaign-notes.md` (**study note** — what the
  BMS dynamic campaign actually does, the full crosswalk to fork features, four gated
  candidates, and the tombstones it must not resurrect — §48/§53/§54 and turnless),
  `414th-region-priorities-notes.md` (**BUILT 2026-08-20 as §93** — per-CP blue planning
  priorities: upstream #686's surface × BMS's PAK weight; the fence stays dead with §40;
  B89 app pass owed),
  `414th-campaign-architecture-notes.md` (**direction note** — the one-substrate architecture
  and rungs R0–R7; see the tracking table),
  `414th-substrate-inventory-notes.md` (**R0, done 2026-08-20** — every campaign quantity's
  writers/readers/cockpit path with receipts; verdict: the core is already coherent, two
  private ledgers exist (§81/§63 magazines), five couplings missing; R1 reshaped smaller),
  `414th-substrate-HANDOFF.md` (**start here to continue the substrate work** — repo state,
  the local-only queue incl. the B65–B68 and B89 passes, R1's opening moves, reserved
  decisions, and this line's traps),
  `414th-airwar-planner-consolidation-notes.md`,
  `414th-aircraft-task-rebalance-rubric.md`, `414th-victory-conditions-notes.md`,
  `414th-wing-growth-notes.md`, `414th-single-player-loop-notes.md`,
  `414th-living-battlespace-notes.md` (all five slices — pre-roll, residue, follow-on
  waves, reactive red — landed 2026-08-15 as §89; the voice net was REMOVED 2026-08-18; in-game passes B56/B57/B60 owed),
  `414th-autoplanner-upstream-divergence-audit.md` (**the full fork-vs-upstream planner
  diff**, 2026-08-09: every divergence classified by gate and default; read before
  reverting or carving planner behavior)
- **Cockpit / data** — `414th-dtc-cartridge-notes.md`, `414th-weapon-dates-proposal.md`,
  `414th-startup-times-notes.md` (**where a `startup_minutes:` value may come from** — read
  before adding one; unsourced numbers are the failure mode),
  `414th-loadout-integrity-audit-notes.md`
- **Terrain / maps** — `414th-marianas-wwii-terrain-notes.md` (**Marianas 1944,
  `MarianaIslandsWWII`: BUILT 2026-08-22** — 11 airfields exported and verified, the
  shared-grid proof that let the projection and landmap be lifted from the modern
  Marianas, and the traps to re-read before doing this again: the stand-list export's
  backslash and module-reload traps, the landmap-directory substring collision, the DCS
  install folder not matching the theatre id, and **Pagan sitting in the sea zone**.
  No campaign authored, so it is not reachable from the New Game wizard yet)
- **Framework / tooling** — `414th-framework-consolidation-notes.md`,
  `414th-mist-moose-shim-notes.md` (**the shim that retired MIST**),
  `414th-moose-ops-opportunity-map.md`, `414th-lua-plugin-harness-notes.md`
- **Structure / debt** — `414th-doc-mass-notes.md` — the 2026-08-19 trim of
  `414th-features.md` (104.3k → 95.8k words, all 91 sections and every §N anchor intact):
  what was cut, the constraints extracted out of removed features before cutting, the six
  sections still needing sub-headings, and **how to replace a section without destroying its
  neighbours** — the first attempt silently deleted four live sections.
- **Process** — `414th-verification-cadence-notes.md` (the fly-card throttle, proposed),
  `414th-dcs-olympus-notes.md`, `414th-ui-redesign-directions.md` (+ `-mockups.html`),
  `414th-juanjux-fork-watch-notes.md` (**the second fork we watch** — his adoption ledger,
  what is already ours, and the OPFOR-AI precedent for seam 7),
  `414th-red-brain-phase0-notes.md` (**read before proposing anything about red** — seam 7
  framing 3 and its Phase 0; no headroom found, and the pre-registered card that would
  reopen it),
  `414th-mist-author-repos-notes.md` (**the licence gate on the MIST author's repos, and the
  one worth reading** — his published in-game unit dump is a second ground truth for sensor
  ranges; MIST and SLmod are GPL-3 and his misc-scripts repo is unlicensed, so none of it may
  be vendored into this LGPL-3 tree; per the naming convention his name/handle stay out of
  this repo)

### Superseded, draft or historical

Kept for reading old notes and saves; **do not author against them**.

`414th-minefields-notes.md` (shelved) · `414th-ewrs-retirement-decision.md` ·
`414th-dismounts-decision.md` · `414th-ctld-mantis-style-port-scope.md` ·
`414th-mission-planning-wiki-rework.md` · `414th-scenery-import-notes.md` ·
`turnless.md`

### Deleted design notes (2026-08-20)

**18 notes, 44,910 words, whose own opening line said "do not author against this."** Each
described a feature that had already been removed, so they were a grep tax with no reader:
the whole point of the file was to tell you not to read it. **They are in git history —
`git show 5db34150f:docs/dev/design/<name>` — and that is the only place they should be.**

| Notes | What they described | Feature removed |
|---|---|---|
| the eight `414th-scar-*` / `414th-combat-sar-*` notes | the fork’s own CSAR and the Sandy escort | §21/§15, 2026-08-07 |
| the three `414th-campaign-phases-*` notes | the phase classifier and ROE zone layer | §40, 2026-07-21 |
| `414th-vietnam-political-will-roe-notes.md`, `414th-will-generalization-notes.md`, `414th-war-economy-notes.md` | the will and war economies | §48/§53/§54, 2026-07-21 |
| `414th-red-intent-notes.md` | Red Intent adaptive posture | §55, 2026-07-21 |
| `414th-tars-recon-notes.md` | the MOOSE Ops.TARS recon engine | cut 2026-08-05; its `recon` successor removed 2026-08-20 (§12) |
| `414th-airwar-planner-consolidation-notes.md` | the planner consolidation | reverted 2026-08-09 |
| `414th-khe-sanh-campaign-notes.md` | the standalone Khe Sanh campaign | merged into Yankee Station |

**Do not re-add a note here when you remove a feature.** Banner-instead-of-delete is what
produced these: a removal writes a banner, the banner is never revisited, and the file
accumulates. Record the removal in the features doc §N and delete the note. The one thing a
deleted note must leave behind is any **constraint learned from a flown test** — lift those
into the hard-constraints list or the surviving design note *before* deleting.

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
runtime behavior (EW, ISR, frontline firefights) is driven by the Lua
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

**Viewer-aware visibility layer (recon fog).** AI planning and threat math always use ground
truth (`viewer=None`); only the human (BLUE) map/UI are fogged. **One question, asked in one
place**: `TheaterGroundObject.visibility_for(viewer)` returns HIDDEN / UNKNOWN / KNOWN, and
`known_for` + `hidden_on_player_map` are its two leaves. `known_for` gates composition and
threat/detection rings (`recon_intel_fog`); `hidden_on_player_map` fully hides enemy command
posts (`scar_command_post_intel`) and §50's ambush teams. Nothing else is viewer-aware except
`standard_identity_for` (COIN's suspect-until-engaged symbol).
**A site is revealed by engaging it — ordnance on it, or any ground-attack sortie that reaches
it — and is then known completely and permanently, damage included.** Recon/TARPS reveals
nothing except a hidden command post within 3 NM of its target (`reveal_scouted_command_posts`
— the one thing engagement cannot reach, because a hidden post has no marker to frag at).
There is no BDA damage lag: `alive_at_last_recon` / `sync_confirmed_status` /
`alive_for` were deleted 2026-08-18 and `alive`/`is_dead`/`dead_units`/`max_threat_range`/… are
plain truth. Do **not** reintroduce a viewer parameter on those, and do **not** reintroduce the
old `_for_player`/`_for` method twins — that collapse is finished.
**Anything that picks targets FOR blue automatically must gate on the fog** — auto raids
(§63), the carrier strike (§44), any future fire mission. Use
`fogofwar.hidden_from(Player.BLUE, tgo)`, never a bare `hidden_on_player_map`: it wraps
`fog_intact()`, so a host who ticked the reveal overview before passing the turn cannot get
a different target than one who did not. Naming a site the player cannot see hands them a
find they were meant to earn, and the strike that follows makes it permanent. Red is never
fogged. Keep the §50 `map_hidden` skip separate — it applies to both sides.
A runtime **overview toggle** (`game/theater/fogofwar.py`, transient/never-pickled)
short-circuits both fog leaves to ground truth for any viewer, so the *whole* render path +
intel dialogs un-fog with **no** server-model changes. It is a checkbox in the custom map
layers panel (`MapLayersControl`, §18), driven by a state `useEffect` (not a Leaflet
add/remove layer — unmount doesn't reliably fire `remove`) that `PUT`s `/fog-of-war/reveal`
then re-pulls `/game`.
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
- **The C-130J cues; it never lases or designates.** It carries no targeting sensor in DCS,
  so any laser work stays with the strike aircraft. Retribution also has no FAC(A) task
  type — §38 does the marking job through Vietnam Ops, not as a taskable role. (Lifted out
  of `414th-scar-task-spec.md` before that note was deleted 2026-08-20; it was the one
  constraint in the 18 recorded nowhere else.)
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
3. **Recon intel fog** — an enemy site's composition stays hidden until you engage it (ordnance on it, or any ground-attack sortie that reaches it); once engaged it is known completely and permanently. There is no BDA damage lag. Recon's only job is finding the enemy command posts, which are hidden from the map outright and so cannot be engaged at all.
4. **UI transparency** — target intel panel, mission-impact debrief, package context bar.
5. **Player target location precision** — `Approximate` mode offsets steerpoints and hides exact coords.
6. **Air-defense planning rework** — overlapping jittered BARCAP waves. **The geometry/volume half was REVERTED to upstream 2026-08-09** (re-convergence work order D): no forward CAP line, no threat-weighted volume or orbit bias, no front-anchor guarantee, no forward-middle layer, no front-anchored support orbits, no FLOT navmesh hazard. Kept: the overlap waves, the `cap_orbit_distance_band` fix, the Vietnam-only escort-reserve trim.
7. **Auto-hide mobile SAMs on MFD** — SHORAD/AAA/MANPAD off datalink; MERAD/LORAD stay visible for SEAD.
8. **Robustness / crash fixes** — helo CFIT, carrier-recovery stagger, convoy runway spawns, support-flight radio collisions, locked speed/time route rejection.
9. **TIC — Troops In Contact** — scripted frontline firefights with per-stance movement and ambient fire.
10. **CurrentHill Iran assets pack** — Shahed-136, IRGCN FAC, `[CH] Iran 2020` faction.
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
47. **Continuous campaign clock & weather** — one marched clock with weather evolving from the previous turn.
49. **Mobile missile relocation** — shoot-and-scoot theater missile sites; fire first, then scoot.
50. **Convoy ambush + ambient supply convoys** — untelegraphed ambush teams on friendly roads, authored as native DCS triggers.
51. **Enemy comms jamming** — IADS comms nodes jam briefed channels whenever one is alive; the captured-aircrew gate went with §21 on 2026-08-07.
52. **Command-center decapitation** — a headless HQ picks targets worse and frags fewer offensive packages.
56. **Strikeable motorpool depots** — the reserve armor pool made bombable, 1:1 with no economy.
58. **Mission-start briefing popup** — per-pilot slot-in cards with a beep and the taxi call.
59. **Ground AI sleep** — the middle tier between keeping and culling, with AAA sites behind two guards.
60. **SAM guidance-radar redundancy** — two spaced track radars, so one HARM is not a site kill.
61. **Host red-interceptor scramble** — an F10 bandit spawner for a quiet event.
62. **Squadron-sequenced modexes** — per-squadron blocks numbered in sequence for Hornets; the Tomcat paints its number into the livery, so its squadrons fly a CAG bird and line jets instead.
63. **Ship-launched cruise missile raids** — finite no-rearm magazines, auto raids and an F10 call-for-fire, with a defender launch wake.
64. **Carrier deck spawn policy** — six-pack as last resort plus the MP slot-timing fix.
65. **Curated carrier comms** — per-hull TACAN, ident, ICLS, Link 4 and ATC feeding the CV Operations Data page.
66. **Generated-mission archive** — a dated copy of every generation, in a folder DCS lists.
67. **Weather-aware auto-planning** — rain grounds auto-recon; storms demote low-level attack.
68. **Adaptive procurement** — price-weighted buys and optional SAM site repair.
69. **SEAD-before-strike coordination** — strikes retimed behind the suppressor servicing their target.
70. **COMINT collection** — the §51 mirror: a surviving collector buys a tasking leak and one exact fix, plus an audible red UHF net.
71. **Expanded F-4E Weapons Pack** — AGM-78 Weasel fits gated on live pylon legality.
72. **Carrier deck decorations** — island-street and LSO dressing, clear of every parking spot and standing for the whole mission.
73. **Per-airframe default loadout for a task** — pin a fit for an airframe and task across campaigns.
74. **Native DTC data pre-population** — auto-loading cartridges for Hornets, Vipers and F-14B(U)s, with a per-flight DTC tab.
75. **Custom victory conditions** — authored win/lose blocks plus generic domination and attrition endings.
76. **CTLD paratroopers** — fixed-wing Air Assault by paradrop, player and AI.
77. **Escort jamming** — EA-18G and EA-6B only; non-stacking spoof bubbles and SAM weapons-hold pulses.
78. **Sea-supply convoys + coastal anti-ship** — proportional convoy losses and batteries that actually engage.
80. **Mixed-hull ship groups** — task groups instead of copies of one hull, family-bounded.
81. **Cross-turn naval magazines** — staggered weapons-free release and finite anti-ship stock, released on attack.
83. **SP Pilot Mode** — accept-and-fly-next, an aircraft-first sortie board, and a pre-turn reasons-to-continue brief.
85. **SAM/missile battery support sections** — refuellers, power and transload in the faction's own kit.
86. **GPS jamming** — satellite-guided weapons released inside the bubble land long.
87. **Naval station-keeping racetracks** — anchored ovals so ships hold station under way.
88. **Angled-deck carrier recovery heading** — the boat steams for 25 kt down the angled deck, not the bow.
89. **Living battlespace** — phase-aware mid-cycle mission starts: earlier packages are already airborne or parked back home when you walk out, follow-on waves launch behind you, the briefing carries the day's running score, and real red alert fighters fly a defensive patrol over a struck objective.
90. **Front-line model** — reinforcement follows the supply lines, attacking costs more than defending, the line's position counts the forces actually present, terrain slows the advance, and the front bulges instead of running straight.
91. **Per-flight sortie records** — the mission reports back what each flight did: track, time airborne, fuel, shots and hits, not just which units died.
92. **What's New** — a toolbar window listing the recent player-visible changes, each with what to look for in the next mission.
93. **Region priorities** — per-control-point BLUE planning emphasis: emphasized regions rank closer, deprioritized farther, ignored left to manual packages. A weight, never a fence.
94. **Smart threat reaction** — only the flight a missile is actually guiding on goes defensive; everything else holds formation and uses countermeasures.
95. **Pinned bullseye** — one bullseye for the campaign instead of a new one every turn, never anchored on a ship or an off-map spawn; the kneeboard names the place it sits on and flags the rare turn it moves.
96. **Neutral-faction border defense** — every nation bordering the war is drawn with its real border: alignment derived from who holds the airfields inside it (red/blue colour families; red-aligned airspace joins §1's QRA accept zones), and a true neutral either permits overflight or defends — cross below the floor and an alert flight (spawned on your enemy's coalition) shadows and warns; press, and it engages and the SAM wakes. Players only; AI is shadowed, never engaged.

### Retired, removed or shelved — do not restore

Kept numbered so old notes and saves stay readable. Details and rationale in the features doc.

| § | Feature | Status |
|---|---|---|
| 11 | Native DCS DTC cartridge export (v1) | Retired 2026-06-26 — superseded by §74 |
| 12 | Recon engine (TARPS + drone BDA) | Removed 2026-08-20 — the §3 rework left its captures with no consumer |
| 13 | Flight Control ATC | Retired 2026-06-26 |
| 20 | Drop-spawn map unit placement | Removed 2026-08-02 |
| 15 | SCAR — RESCAP "Sandy" rescue escort | Removed 2026-08-07 — see §21 |
| 21 | Combat SAR (fork implementation) | Removed 2026-08-07 — replaced by upstream dcs-retribution#929, which is **an OPEN PR, not merged** (zero reviews as of 2026-08-17). We re-adopt its phases by hand; Phase 5 landed 2026-08-17. See the adoption log in `414th-csar-notes.md` before touching the hover height |
| 25 | Compact 3–4 page kneeboard deck | Retired 2026-07-05 |
| 30 | Dedicated kneeboard cover page | Retired 2026-07-13 — new info folds into a stock page |
| 31 | One-page Brief Sheet | Retired 2026-07-13 — BLUF and code words survived |
| 40 | Campaign phases, ROE zones, target release | Removed 2026-07-21 |
| 46 | Route-aware fuel-tank planning (fuel-first) | **Reverted 2026-08-09** — planner re-convergence work order C; tanker tasking is upstream's again and nothing fits tanks. The external-fuel *accounting* helpers survive for the fuel readouts |
| 48 | Commitment ceiling and the political-will economy | Removed 2026-07-21 |
| 53 | War economy | Removed 2026-07-21 |
| 54 | Munitions availability | Removed 2026-07-21 |
| 55 | Red Intent adaptive posture | Removed 2026-07-21 |
| 57 | Air-droppable minefields | **Shelved** 2026-07-30 — inert, code retained, resumable |
| 79 | Decoy suspected-activity zones | Removed 2026-08-18 — real forces no longer hide behind circles, so a lone circle would obviously be fake |
| 82 | The Wing Grows (scheduled squadron arrivals) | Removed 2026-08-16 — "doesn't add much except in very specific campaigns" |
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

### juanjux's fork — a second high-signal source (WATCH, established 2026-08-19)

`juanjux/dcs-retribution` is upstream's most prolific non-maintainer contributor's personal
fork: **64 PRs to upstream (28 merged)**, **100 of his own internal PRs**, and **954 commits /
300 files ahead of upstream `dev`** — the same scale as ours, on a different philosophy. He is
also the reviewer whose objection closed our #851.

**The watch:** skim his fork's PR list; read the `[FIX]` ones first, since those land in our
tree unchanged while his feature PRs usually collide with something we solved differently.

```
gh pr list --repo juanjux/dcs-retribution --state all --limit 40 --json number,title,state,createdAt
```

**Verify every claim against our own files before acting** — of the five defects reviewed on
2026-08-19, four were live here and one was not, and the one that was not reads identical at a
glance. The four were fixed the same day (hold-release clamp, two front-line hold causes, and
the IADS C2 graph). Open candidates, the OPFOR-AI precedent for seam 7, and the full ledger are
in [414th-juanjux-fork-watch-notes.md](docs/dev/design/414th-juanjux-fork-watch-notes.md).

### The MIST author's repositories — read-only, licence-gated (ASSESSED 2026-08-20)

The author of MIST and SLmod — one of DCS's longest-standing mission scripters — has 7 public
repositories, assessed in full; **one is worth reading and none may be copied.** Per the naming
convention (paid-campaign treatment, 2026-08-20 user call) his name and handle appear nowhere in
this repo, PR metadata or commit messages; the DM holds the link.

- **The licence gate is hard.** MIST and SLmod are **GPL-3.0**; `DCS-miscScripts` has **no
  licence file at all**. This tree is **LGPL-3.0**. Read his work, verify our numbers against
  it, reimplement a mechanism from the DCS API if we want it — never vendor a file, never
  commit his data. (Retiring MIST on 2026-07-10 removed the tree's only GPL-3 file.)
- **The one live repo is his misc-scripts collection** (updated Feb 2026). `ObjectDB2/everyObject.lua` is a
  published in-game dump of `getDesc()` + `getSensors()` + `getAmmo()` for 625 DCS objects — a
  **second ground truth** for sensor ranges that needs no DCS box, unlike `verify_mod_export.py`.
  `IADScript/script_iads_dev.lua` carries a 24-system SAM database with radar rotation periods,
  per-launcher magazine sizes and rearm times.
- **Detection-range candidate — CHECKED 2026-08-20, no defect found. Do not re-run it.** The
  runtime dump and the mission-editor database are not measured against the same target: across
  every unit in the note's table `database ÷ runtime` is a constant **1.4953 = 5^¼** (radar range
  scales as RCS^¼). Normalised, the **Buk SR is exact** and the "~2×" was an artifact. pydcs is
  also not stale — the DM's own 2026-07-20 export matches it on all seven units. Three units still
  disagree (64H6E sr high 33 %, 40B6MD sr low 50 %, Patriot str low 38 %) and need `getSensors()`
  run on our own install to settle; they are vanilla values faithfully mirroring the database, so
  changing them is a data divergence needing its own call, not a bug fix.
- **Corroborated, do not re-litigate:** his IADS calls `enableEmission` **zero** times — same
  conclusion as our hard constraint. And measured Dog Ear detection is 23.4 km against 1L13's
  200.6 km, which confirms Ramius007's objection that closed #887.

Full assessment, including the SAM-magazine and radar-sweep ideas MANTIS lacks, is in
[414th-mist-author-repos-notes.md](docs/dev/design/414th-mist-author-repos-notes.md).

**He reverted one of ours and was right**: his #40 backed out the support-orbit port because
the FLOT anchoring sent AWACS and tankers over enemy ship groups. We reverted the same geometry
independently on 2026-08-09. Two forks, same verdict, different evidence — do not re-litigate.

### Upstream PR ledger (**refreshed 2026-08-16 — read the 08-16 note directly below first; the 07-20 narrative that follows it is kept for history but its open/closed counts are wrong.** Was: refreshed 2026-07-20 — 50 PRs: 20 open / 8 merged / 22 closed. **Late 2026-07-20: the squadron-country surfacing carved as draft #896** — the Discord thread (Starfire's yaml `country:` ask + Toad's under-livery dropdown) answered the same day it ran; the fork's I6 pass flew clean that night ("896 is flown and good") but the draft is **HELD through the PR freeze below** (DM call — #896 was opened the same day the freeze was learned, so it stays a quiet draft until the freeze lifts; un-draft on a fresh explicit call then). **The 2026-07-20 QOL carve wave** (the DM's "ship the objective improvements back" call) opened six more drafts in one session: Dog Ear SHORAD #887, F-14A-Early payload #889, squadron-config guard #890, blue-block markers #891 (the upstream sweep found **465** dropped markers across 9 campaigns — Normandy's authored blue defenses dominate, flagged as a maintainer judgment call in the PR), the #791 refresh #892, and §60 radar redundancy #893 (stacked on #892, rationale attached). **#891 self-closed on review the same day**: Starfire13's density reaction ("352 EWRs in Normandy. Good lord…") plus the real ask — **CJTF block-convention consistency** ("for some objects you can only use one, yet for others both are acceptable"); the fork answered the ask same day (the loader's last single-block classes now chain both blocks — 3 shipped red-block factories resurrected, `test_miz_marker_binding.py`) but the **re-carve was DROPPED 2026-08-05** — the Custom-campaigns wiki's block spec table and upstream's loader already agree on all 19 classes, so there is no bug to carve (inventory item 17). Also learned in that session: **#791 closed with zero comments** (never reviewed — hence the refresh) and **#851 closed on a real objection** (juanjux: HDS Ultimate Compilation is NOT backward-compatible with Auranis HighDigitSAMs 2.1.0, which he runs — the S-300 renames collide; a re-carve must first answer which successor mod upstream standardizes on). **Held re-carve draft prepared 2026-07-20** — [docs/dev/414th-hds-recarve-draft.md](docs/dev/414th-hds-recarve-draft.md) (leads with UC-as-successor + migration note, offers the dual-toggle fallback; gated on the PR freeze lifting AND a fresh post-mod-update export). **Three fork PRs merged upstream 2026-07-19** (#805/#843/#854) and geofffranks' #859 (the §56 motorpool source) landed the same day — all four reconciled back into the fork in the `sync/upstream-dev-2026-07-19` merge. Same day, Wave 3 opened: the Splash Damage defaults PR #880 pushed (item 21, the first last-mile carve), the VWV v3.2.0 update #881 pushed (item 22), the §76 paradrop carve #884 opened (un-drafted late that evening + Starfire13 pinged for review), the **infrastructure pair #882 (Lua plugin harness) + #883 (MIST 51-symbol shim, stacked on #882)** opened as drafts, #828 was rebased — briefly un-drafted, then deliberately re-drafted minutes later (21:36→21:40Z per the PR timeline), so it sits as a draft with the un-draft call open — and the night closed with **two more last-mile carves: the §75 victory-conditions core as draft #885 and the Iran-pack re-carve (the #784 redo) as draft #886**. Still re-verify with `gh` before acting; this goes stale fast.

**Ledger refresh 2026-08-16 — 10 of ours open, 9 merged.** The 07-20 counts above are stale. Corrections, all verified with `gh`:

- **Nine PRs the ledger listed as open are closed, and we closed every one of them ourselves** — #893, #892, #890, #887, #883, #882, #828, #806, #794. None was rejected by upstream. Reasons per PR are in the **Closed on review** list below; the two that matter most are #828 (Druss99 wants recon rebuilt as a larger opt-in effort with its own issue — re-offer against that, not as this PR) and #892 (Ramius007 says the stock SA-11/SA-17/BUK-M3 layouts are wrong for a battalion, so the layout work needs redoing first).
- **Two of ours were never in the ledger at all:** #925 (patrol altitude on the yamls, the #806 follow-up) and #920 (bulk waypoint altitude, the #805 follow-on).
- **Upstream is arguing about which HDS mod to standardize on, and it is trending our way.** #937 updates their build to Auranis HDS 2.1.0 and #940 adds the S-400/S-300V4 on top of it, but on the #940 thread juanjux — the objection that killed our #851 — [now says](https://github.com/dcs-retribution/dcs-retribution/pull/940#issuecomment-5281713144) "I am also in favor of HDSUC as it's the better option, we just cant have both", and Starfire13 raised the same point (their HDS build has no SA-21; Ultimate does). The fork stays on Ultimate Compilation regardless — this only decides whether the held re-carve draft ever ships. **Do not act on it unbidden**: #851 is closed, so re-offering is a NEW PR and the freeze still applies.
- **Freeze indicators unchanged as of 2026-08-16:** newest published release is still v1.5.0 (2026-04-13) and `test/1.6`'s tip has not moved since 2026-07-25, while `dev` merged through 08-15. Still only the DM lifts it.
- **"Alpha build" means the CI `Build` workflow's latest run on `dev`, not a GitHub Release/tag.** Upstream publishes no alpha/beta releases or tags — `/releases` and `/tags` only ever show stable `v1.x.y`. The actual per-commit build (what the `#dev-builds` Discord bot posts as "Build #NNNN available!") is `actions/workflows/build.yml` filtered to `branch:dev`; its top row's commit SHA is upstream's current tip. Check that, not the releases page, when asked "what's the latest alpha." **As of 2026-08-19: build #3186 (commit `59719b2`, 2026-08-18) = the #928 convoy-counter fix, already ported fork-side via [414Ret#852](https://github.com/BradySox/414Ret/pull/852)** — so the fork was caught up as of the latest alpha build. Re-check the workflow's top `dev` row each time; PR-branch builds (e.g. `joruaz:MapTypes`) show above it in the unfiltered list and are not `dev`.
- **Sync landed:** upstream dev @ `df9dbf39` merged in fork PR [414Ret#851](https://github.com/BradySox/414Ret/pull/851) (8 commits — the #931 TACAN/beacon conflict fix, UH-60L 2.1.5, the `CH_B-21.lua` payload rename, campaign data).
- **Adopted from an open upstream PR:** #928's convoy name-collision fix, ported in fork PR [414Ret#852](https://github.com/BradySox/414Ret/pull/852). We were carrying the bug — `reset_numbers()` reset the convoy counters, so a long campaign eventually died on "Duplicate convoy unit" with no way out of the save.
- **Watch, not yet adopted:** #926 (motorpool display/targeting follow-up, §56) · #930 (QComboBox plugin options, extends our merged #841) · #916 (bases-captured in the mission summary) · #934/#936 (map option persistence + new basemaps — collides with §19 and §42). #938 (CH Ukraine id renames) and #939 (P-14 into the SA-5 group) are already done fork-side; upstream is converging on us there.
- **Adopted in full from an open upstream PR: #927** (cloud presets). Both commits are in:
  the selectable pack half landed 2026-08-03 (fork #773), the ATMOS-X live-weather half
  2026-08-19. **Drift-watch when #927 merges** — the fork's port is not byte-identical, and
  the divergences are deliberate: our migration rides `_migrate_legacy_settings`, the enum is
  registered in `SERIALIZABLE_ENUM_TYPES`, and the ATMOS-X options are gated with the fork's
  existing `enabled_when` (greys out, live across pages) rather than upstream's parallel
  `visible_when` (hides). The live-weather half also needed three fork couplings upstream has
  no reason to carry — §47's weather ladder, `Conditions.advance`, and §67's planner all had
  to learn what a `LiveWeather` is. **A fourth divergence was added 2026-08-20 and is the one
  that must not be resynced**: the station picker reads each control point's
  `starting_coalition`, not `captured`. Our port predated upstream's own fix for the same
  crash (`ControlPoint not fully initialized` — conditions are generated inside
  `Game.__init__`, before the coalitions are wired, and the raise killed New Game), and
  upstream's fix returns an empty base list, which sends `choose_station` to an arbitrary
  field. See
  [414th-atmosx-live-weather-notes.md](docs/dev/design/414th-atmosx-live-weather-notes.md).

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

**⛔ UPSTREAM PR FREEZE — STILL IN FORCE, CONFIRMED BY THE DM 2026-08-05 ("its not lifted yet. Beta branch soon"):** dcs-retribution is accepting **no NEW PRs until their next beta release**; **updating existing PRs is fine** (merging current upstream into an open PR branch, pushing review fixes, and re-requesting review are all allowed and were exercised on all 13 open PRs on 2026-08-05). **Do NOT infer the lift from upstream activity** — that mistake was made twice: the 2026-07-26 sync read 12 weekend commits as "the release the freeze was waiting on", and the 2026-08-05 sync read another 36 commits (incl. their merge of our #889) the same way. Neither was the release. The observable facts as of 2026-08-05: **the newest published release is still v1.5.0 (2026-04-13)**, and the `test/1.6` branch was cut but its tip has not moved since **2026-07-25** while `dev` kept merging through 08-04. **Only the DM lifts this**, on word from upstream — never a `gh`/commit-activity inference. **One-off exception granted 2026-08-19** for the two-line F-16C UTC-kneeboard fix (#949), on the DM's call after the freeze was flagged to them: "This is so small and its a simple fix for a long standing bug." That is an exception for that PR, not a lift — the freeze still binds everything else on this list. **A second, broader exception was granted 2026-08-20 (DM): "forget the PR freeze if its addressing something on this list", meaning the [upstream issue ledger](docs/dev/414th-upstreaming-inventory.md#upstream-issue-ledger).** A PR that answers an open upstream issue may be opened; a carve with no issue behind it still waits. Exercised the same day for [#950](https://github.com/dcs-retribution/dcs-retribution/pull/950) (issue #948, open) and [#951](https://github.com/dcs-retribution/dcs-retribution/pull/951) (issue #901) — **#951 was closed hours later as a duplicate of red-one1's [#902](https://github.com/dcs-retribution/dcs-retribution/pull/902), the lesson being that an issue must be checked for linked PRs via its timeline before carving; see the issue ledger's *Re-running the sweep*.** Still a scoped exception, not a lift — only the DM lifts the freeze. Holds until it lifts: the **HDS re-carve** (held draft prepared — [docs/dev/414th-hds-recarve-draft.md](docs/dev/414th-hds-recarve-draft.md); data re-verified post-mod-update, numbers hold — note that draft carries a SECOND gate of its own, and the real blocker is a *decision* upstream must make: which HDS successor mod they standardize on, since #851 died on a user running Auranis 2.1.0 — **that decision started moving 2026-08-13 and is trending toward Ultimate; see the 2026-08-16 ledger refresh**, but the freeze still binds because re-offering #851 means a NEW PR), the pydcs exporter-hardening PR candidate, the `Retribution Fighter sweep` payload-casing fix from the 07-26 sync, and the two 2026-08-17 answers to open upstream issues — **inventory item 28** (theater tanker per refuel method, upstream #243) and **item 29** (per-airframe startup times, upstream #214, in the shape the maintainer asked for twice). **Inventory item 30 is NOT held**: it is a defect report on upstream's own open PR #929, so it is a thread comment rather than a new PR — and it wants doing before #929 merges. **#896 is NOT on this list** — it is an *existing* open PR (never a draft; the earlier "un-draft #896" note was wrong): Druss99's 07-31 request-changes was answered in full the same day (`6dea2efa`, operator tables dropped), a re-review is **already pending on him**, and the standing `CHANGES_REQUESTED` decision is just the stale flag from that review, which clears only when he submits a new one. Nothing is owed on it. **The post-mod-update queue COMPLETED 2026-07-20 evening** (re-dump run; every export file parsed clean on the hardened exporter): extensions verified 386/386 pre-migration, **HDS unchanged** (the re-carve draft's numbers hold), and the update wave surfaced the real story — **ED has integrated CurrentHill units into base DCS** (`CoreMods/tech/Currenthill Assets Pack`, the `CHAP_*` ids; pydcs pin + 21 fork CHAP yamls already carry them) while the CH 1.5.0 packs renamed their remaining ids to `CH_`/dropped the ED-integrated ones. The fork migrated: Sweden 30 id renames + UK Type45/SkySabre + Ukraine BTR-4/MiG-29MU2/Su-24MU (extension ids + yaml filenames + LvS-103/Sky-Sabre layout refs + eject strings — **the layout-refs half of that claim was FALSE and was fixed 2026-08-08**: all 20 `unit_types` entries across the four `LvS-103*.yaml` layouts still named the pre-1.5.0 ids, so `unit_type_from_name` returned None, `GroupLayoutMapping.from_dict` dropped them silently, the mandatory groups emptied, and every LvS-103 site raised `LayoutException` — measured: Sweden 2020 went from 7 usable LORAD layouts to 5, losing its only national long-range SAM. Sky Sabre's launcher slot named the pydcs *class* `CH_SkySabreLN` instead of the id `CH_SkySabre` and only survived on its `Launcher` class fallback, generating the wrong launcher. Both now locked by `tests/test_layout_unit_types.py`), 6 vanilla-superseded registrations retired (both Ukraine tanks, Scimitar/Scorpion re-pointed in blufor_current to the vanilla CHAP variants), and the **Ukraine pack was discovered double-nested in Saved Games (never loaded — fixed)**; its units export-verify on the next natural dump. The wave's adoption audit lives in [docs/dev/414th-ch-wave-adoption-backlog.md](docs/dev/414th-ch-wave-adoption-backlog.md): ~98 % already adopted (the extensions had tracked newer pack versions all along; every new AD system rides a factioned preset group) — **4 units genuinely open** (TigerUHT yaml, the B-21 faction call, the 2 Project 22160 hulls).

Carved out of this work, against `dcs-retribution/dcs-retribution` (all authored by `BradySox` — the renamed `bradyccox` account):

- **Open (awaiting review) — verified with `gh` 2026-08-16, 10 PRs, plus #949 opened 2026-08-19 and #950 opened 2026-08-20 (#951 opened and closed the same day, duplicate of #902):** #950 (draft) · #949 (draft) · #925 (draft) · #920 · #896 · #886 · #884 · #881 · #874 · #872 · #792 · #788. Everything else the ledger once listed here is closed; see **Closed on review** below.
  - [#949](https://github.com/dcs-retribution/dcs-retribution/pull/949) use UTC kneeboard times for the F-16C (**draft**, opened 2026-08-19). Two lines: `utc_kneeboard: true` on the Viper yaml plus a changelog note. The kneeboard printed mission-local times while the jet's avionics run Zulu — System Time on the DED/HUD is "based on Zulu time (UTC)" (EA guide p103, p115) and the CRUS TOS page derives required ground speed from TOS minus System Time (p107) — so card and DED disagreed by the map offset. The flag and its conversion are already upstream's; the Hornet has used it since it was added. Only the F-16C is touched; other airframes are explicitly not audited. Upstream suite green (452 passed). **Opened under an explicit DM exception to the freeze below — the freeze itself is NOT lifted; do not read this PR as evidence that it is.** Fork side landed with the §74 Zulu cartridge fix.
  - [#925](https://github.com/dcs-retribution/dcs-retribution/pull/925) author `patrol.altitude` on the 117 BARCAP-tasked aircraft yamls (**draft**, opened 2026-08-02) — the follow-up #806 was closed in favour of, taking Druss99's suggested direction: per-airframe yaml values instead of a campaign-wide settings band. `AircraftType.preferred_patrol_altitude` already read a yaml override; no aircraft used it.
  - [#920](https://github.com/dcs-retribution/dcs-retribution/pull/920) bulk waypoint altitude moves every leg that is flown (opened 2026-07-31) — the follow-on to merged #805, rewritten on review. The filter ended with `alt_type != "RADIO"`, so it skipped every AGL waypoint: CAS FLOT boundaries always, and on a helo or low-level plan "Apply to all" did nothing at all.
  - [#896](https://github.com/dcs-retribution/dcs-retribution/pull/896) surface the squadron country — campaign yaml `country:` pin + Air Wing dialog selector (**open, not a draft**, opened 2026-07-20 on dev @ `3760cf2a`; head `554c0a3` after the 2026-08-22 dev merge) — §23's surfacing follow-on (inventory item 26), answering that day's upstream Discord ask verbatim (Starfire: preset-for-the-nation-if-available-else-generated-set-to-it; Toad: dropdown under Livery): `SquadronConfig.country` → same-nation-only preset pick with def-generator fallthrough + `override_squadron_defaults` stamp, the `SquadronCountrySelector` (live-write, faithful mod-country display), preset dropdowns showing each preset's nation, Save/Load Config country round-trip, and the bind_data livery stale-squadron re-point fix. Upstream carries the 12 game-side tests; the offscreen-Qt selector test + the campaign `country:` pins stay fork-side. black / mypy / 453 tests green *on opening day* — do not requote that count, head has moved. **I6 VERIFIED 2026-07-20** ("896 is flown and good"). **Druss99 request-changes 2026-07-31** — the operator tables are "a massive burden when adding a new aircraft module"; capitulated fully (DM call): `game/dcs/operatorcountries.py` + the operator-derived unpinned-CJTF default removed (fork + carve), the selector shows the full country list, and an unknown `country:` aborts New Game instead of degrading, reducing the PR to "yaml country pin, no default-behavior change." **The trim is applied on BOTH sides and the re-review is already requested — verified 2026-08-25** against head `554c0a3`: no `game/dcs/operatorcountries.py`, `resolve_config_country` raises `ValueError`, `SquadronCountrySelector` lists every DCS country, 12 pin tests fork-side and carve-side. Branch `claude/pr-896-review-8kg5xf` no longer exists on the fork remote; that work is on `main`. **What IS owed is the PR description** — it was never edited after the 07-31 trim, so the published body still sells the operator tables (`game/dcs/operatorcountries.py`, the four-step resolution chain, `tests/dcs/test_operator_countries.py`) and still says an unknown `country:` "log[s] and degrade[s] … (never abort New Game)", which is the opposite of the shipped code and the opposite of what Druss99 asked for. Replacement body drafted at [docs/dev/414th-pr896-body-refresh.md](docs/dev/414th-pr896-body-refresh.md); pasting it is a description edit, allowed under the freeze.
  - [#886](https://github.com/dcs-retribution/dcs-retribution/pull/886) CurrentHill Iran Military Assets pack + `[CH] Iran 2020` faction (**draft**, opened late 2026-07-19) — the clean minimal redo of self-withdrawn #784 (that early upload was a monolith dragging in the C-130J plugin/QRA planner/scramble scripts): `pydcs_extensions/iranmilitaryassetspack` (Shahed 136 LM + the 2 IRGCN FACs) + the faction + the `iranmilitaryassetspack` ModSettings toggle/wizard checkbox + the FAC ship-radar registry entries + 3 unit yamls, nothing else — the exact pattern of the six CH packs upstream already carries. Headless probe on upstream dev: 20/20 aircraft / 10/10 preset groups / 6/6 naval / 2/2 missiles / 9/9 AD resolve; mod-off strip verified both ways. 438 tests / mypy / black green. **Export verification CLOSED 2026-07-20** (Druss99's export-provenance ask, same as #881): the wiki's `pydcs_export.lua` process was ACTUALLY RUN on the DM's install (CH Iran 2.0.0 loaded) — it caught `IranFAC_MG_AShM` threat/awd registered 25000 where the live DB says **1800** (the 25000 was `WS.maxTargetDetectionRange` conflated into the AA threat fields; 14× inflated ring), fixed on the branch (`9dffedff`, fork mirrored); `CH_Shahed136` + `IranFAC_MG` verify clean — 3/3 match. Reply posted in-thread with the verdict.
  - [#884](https://github.com/dcs-retribution/dcs-retribution/pull/884) fixed-wing air assault by CTLD paradrop (opened 2026-07-19, **un-drafted late that evening** + Starfire13 pinged for review) — §76's generic core: the cabin-based planner gate (subsumes `is_hercules`; the Hercules keeps its initial-point ingress + gains a layout-shape pin), the `ctld-config.lua` drop runtime (airborne "Unload / Extract Troops" = jump, descent-delayed ground spawn, AI one-shot zone release, 3,000 ft player ceiling), the preload retry, and `Air Assault: 40` on the C-130J-30 yaml. The fork's lupa-harness runtime test stays fork-side (upstream has no lua harness); the §2 EW deny-list hunk is fork-only. On dev @ `acf02b75`; pytest/Black/mypy green. Fork side = [414Ret#681](https://github.com/BradySox/414Ret/pull/681).
  - [#881](https://github.com/dcs-retribution/dcs-retribution/pull/881) Vietnam War Vessels support → v3.2.0 (inventory item 22, opened 2026-07-19) — upstream's VWV support was frozen at v3.0.0: registers the 3.1.0 Sampans ×5 + Junk civilian craft and the 5 never-registered hulls (Radford / Epperson / Everett F. Larson / Solon Turman / USNS Card; ids from the installed mod's own `Database/Navy/*.lua`), adds all 11 to the `faction.py` eject list, and bumps the wizard label + 4 stale faction `requirements` versions to v3.2.0. Registration-only parity with the fork (no unit yamls/prices — the fork hasn't authored them either). On dev @ `acf02b75`; pytest/Black/mypy green. Fork reconciled same day (same eject entries + its own 4 stale faction strings). **Review response 2026-07-20** (Druss99 asked whether the extension came from a pydcs export — the annotation comments read as AI-generated): comments stripped to exporter style, and the re-verification of all 11 hulls against the mod's public source (`tspindler-cms/tetet-vwv` @ tag `VWV_3.2.0`) caught that the removed **USNS Card** comment was WRONG — `Database/Navy/Card.lua` defines `airFindDist 45000` / `airWeaponDist 18650` (keeps a 5"/38 battery), so Card is now 45000/18650/18650 and Solon Turman carries explicit 15000/0/0 (branch commit `534fbd7`; fork mirrored the same fix). **Export verification CLOSED 2026-07-20**: the wiki's `pydcs_export.lua` process was ACTUALLY RUN on the DM's install (full VWV 3.2.0 fleet loaded; runbook + heavy-mod exporter gotchas in `tools/verify_mod_export.py`'s docstring — the stock exporter crashed twice on 50-mod data and needed nil-guards/pcall hardening, patched copy at `C:\Users\brady\dcs-export\pydcs_export.lua`, pydcs-PR candidate) and it FALSIFIED the tag-source reading: `Solon_Turman.lua` sets `GT.airWeaponDist = 13000` (not unarmed — Turman fixed 0→13000/13000), BHR `plane_num` is 40 (not 8), and 3.2.0 superseded the plain Maddox module with the Tonkin Incident module (id **`USS Maddox T`** — registered additively + eject-listed; The Sullivans left the 3.2.0 distribution entirely, legacy entries kept for old installs). All on the branch (`2ffa9057`, fork mirrored); Card's 45000/18650/18650 export-CONFIRMED; 120/124 registered VWV units match field-for-field (residual: 2 pre-existing cosmetic drifts, aligned fork-side). Reply posted in-thread. **The follow-on fork-wide sweep** (unfiltered `verify_mod_export.py` over every installed mod) then aligned ALL 363 registered units of every extension to the live export — 93 drifted (HDS NATO-name restyle + sensor retunes incl. SA-17 TELAR detection 120→18.5 km, CH UK renames/retunes, IDF SAM ranges, and the `oh6_vietnamassetpack` duplicate VAP registrations whose stale values silently raced `vietnamwarvessels`' at pydcs-injection time — values now agree; module retirement deferred for save-compat) — fork commits `1345a4002` + `2621d695c`; the §63 LACM hull-id audit came back clean (CH Russia Kalibr trio verified; the 4 CH USA ids target a newer pack than installed, no faction fields them).
  - [#874](https://github.com/dcs-retribution/dcs-retribution/pull/874) curated carrier comms (**draft**) — §65 verbatim (per-hull boat cards feeding the DCS-rendered CV Operations Data page: hull-number TACAN + boat ident with `alloc_near` nearest-neighbor degrade, hull-keyed ICLS via a shared `IclsAllocator`, 336-band Link 4, stable persisted ATC, flagship named by hull name). NO fork couplings; the port adds only the Pretense allocator-type adaptation (behavior untouched). On dev @ `ef576acc`; pytest/Black/mypy green — opened 2026-07-16. Fork side = [414Ret#611](https://github.com/bradyccox/414Ret/pull/611). See upstreaming-inventory item 19.
  - [#872](https://github.com/dcs-retribution/dcs-retribution/pull/872) ship-launched cruise missile strikes — generic core of fork [414Ret#599](https://github.com/bradyccox/414Ret/pull/599) (Tomahawk/Kalibr shore attack: F10 call-for-fire with marker-text salvo sizing, optional auto raids, persisted no-rearm magazine via the `cruise_missiles_state` debrief channel). **Ready for review 2026-07-19**: the branch carries the review-feedback stagger + un-cull + carrier-escort commits, a current-dev merge, and the flown **defender launch wake** ported from the fork (alarm-RED near the aimpoint for the missile flight window; Skynet-adapted comments) — un-drafted after the DM's local 10/10 fly. See upstreaming-inventory item 18.
  - [#792](https://github.com/dcs-retribution/dcs-retribution/pull/792) wind override UI.
  - [#788](https://github.com/dcs-retribution/dcs-retribution/pull/788) inflight final-waypoint crash (§8).
- **Closed on review, 2026-07-20 → 08-11 — every one SELF-closed by us, not rejected by upstream (⚠️ the ledger listed all of these as open):**
  - [#893](https://github.com/dcs-retribution/dcs-retribution/pull/893) **Self-closed 2026-08-02**, with its base #892. Was: SAM guidance-radar redundancy (**draft**, opened 2026-07-20, **stacked on #892**) — §60 carried upstream with the realism-notes rationale spelled out in the body (a balance call, not TO&E; the regiment-model tension + "park it if you'd rather keep stock single-radar" offered explicitly): 21 layout yamls `unit_count` 1→2 across 23 slots + the 5 shared templates grafted a second radar position (45–121 m offsets, structurally copied from the fork's templates — the fork-only P-14 "EW Radar" groups deliberately NOT carried) + the 29-pair lockstep test (SAMP/T row dropped — HDS-Ultimate-only). 467 tests green.
  - [#892](https://github.com/dcs-retribution/dcs-retribution/pull/892) **Self-closed 2026-08-02** on Ramius007's review: the SA-11/SA-17/BUK-M3 stock layouts are wrong for a battalion (he wants 6 launchers + 3 reloaders + SR + C2, or a 2-launcher battery with no C2), so the layout work needs redoing before it is worth re-offering. Was: SAM site layout variety + EWR radar pool (**draft**, opened 2026-07-20) — the **refresh of #791**, which closed with zero comments (never reviewed): the June branch rebased onto dev @ `acf02b75` with zero conflicts, content unchanged, re-validated same day (68 preset groups load; all 131 factions resolve with 0 bad preset refs; 438 tests).
  - [#890](https://github.com/dcs-retribution/dcs-retribution/pull/890) **Self-closed 2026-07-20** — "Makes sense, close it or is there any usefulness we can take out of it?" A defensive guard upstream did not need. Was: squadron `aircraft:` empty-key New Game crash guard (**draft**, opened 2026-07-20) — inventory item 12, honestly re-pitched: current upstream campaigns no longer ship the pattern (the item's "two campaigns unplayable" claim was stale — upstream's Northern Guardian Transport squadron has since been filled in; the fork hit the crash when its mod purge emptied the key), so the PR sells it as the defensive guard it is (`data.get("aircraft") or []`; iterating None at defaultsquadronassigner.py:61 kills New Game).
  - [#887](https://github.com/dcs-retribution/dcs-retribution/pull/887) **Self-closed 2026-08-11** on Ramius007's review: those systems either carry their own radar or gain nothing from the Dog Ear, and an EWR gives the same benefit at far greater range. Fork §-equivalent unaffected. Was: Soviet SHORAD Sborka "Dog Ear" acquisition radar (**draft**, opened 2026-07-20) — the fork's evolved slot-gated + marker-gated implementation (`_add_dog_ear_if_needed` in both `for_layout` + the preset loader, the SHORAD.yaml Search Radar slot, the 3-way test incl. the SAM-site/era exclusions); vanilla unit, no faction edits. Was never in the inventory queue — added as item 23.
  - [#885](https://github.com/dcs-retribution/dcs-retribution/pull/885) custom victory conditions — **CLOSED-CEDED 2026-07-20, no longer open** (was: draft opened late 2026-07-19 carrying §75's generic core — `game/victory.py` minus the meter fields/negotiation absorption/SITREP surfaces, the `check_win_loss` branch, the two knobs, 28 ported tests). Druss99: "I have a local branch for this already so if you don't mind I'll be taking this one" — the DM closed the PR and handed the feature over the same morning. NOT a rejection, NOT a re-carve candidate: fork §75 is unaffected (B29 app pass still owed fork-side), and when Druss99's implementation lands upstream it becomes a **reconcile-on-merge / drift-watch** item vs the fork's shape.
  - [#883](https://github.com/dcs-retribution/dcs-retribution/pull/883) **Self-closed 2026-07-20**, with its base #882. Was: replace MIST with a tested 51-symbol compatibility shim (**draft**, opened 2026-07-19, **stacked on #882** — review the shim commit with/after the harness) — the fork's MIST retirement carried upstream: `mist_moose_shim.lua` extended with the eleven symbols only upstream's extra consumers call (dismounts `getGroupPoints`/`marker.remove`, EW-jammer pitch/roll/`makeVec3GL`, EWRS speed conversions, and the Pretense teleport/respawn family — **new implementations validated by the harness, never fork-flown**, since the fork ran no Pretense: the in-game watch item), `mist_4_5_126.lua` deleted, consumers byte-unchanged, one-line rollback. Bonus: the DB tier rebuilds on debounced BIRTH + a 30 s fallback instead of MIST's whole-mission poll. 462 tests green.
  - [#882](https://github.com/dcs-retribution/dcs-retribution/pull/882) **Self-closed 2026-08-02.** The Wave-5 Lua carves it was meant to enable never followed. Was: headless Lua plugin test harness (**draft**, opened 2026-07-19) — the fork's `tests/lua/` lupa harness carried upstream (virtual clock with DCS reschedule semantics, recorded `trigger.action`/controller/spawn side effects, populated-world + weapon fakes, a minimal MOOSE facade, file-scope/tick/handler error capture; runs inside plain `pytest tests`, zero workflow changes). First consumer: Splash Damage 3 runtime pins (load + tracking start, the percent-normalization contract, track-to-impact, unknown-weapon ignore; power *values* deliberately unpinned while #880 is discussed). **The enabler for the Wave-5 Lua-feature carves.**
  - [#880](https://github.com/dcs-retribution/dcs-retribution/pull/880) Splash Damage coherent field-tuned defaults — **CLOSED 2026-08-06, DM call: "it's a preference we use, not everyone else."** The tuning is a 414th taste call, not a defect owed upstream, so it stays fork-side permanently (a named exception to the everything-upstreamable policy; see the pinned block). Two real bugs surfaced in the closing audit and are **not** carried by anything now: upstream's `sd3-config` assigns `cluster_bomblet_reduction_modifier` while the script reads `cluster_bomblet_reductionmodifier` (the bomblet-reduction toggle is inert — fixed on the closed branch, so it needs re-carving if it is ever wanted), and upstream's parked-aircraft OCA block calls **`getAGL()`, which is defined nowhere in their tree** (nil-call for every damaged object, inside the `world.searchObjects` callback) — the fork's restored copy computes AGL inline instead. Original scope, for the record: it fixed upstream's broken percent plumbing (the "(%)" rocket spinner applied raw ×130; overall_scaling 3 = 3% with a second ÷100 in the bomblet path; test mode shipped enabled) and sets the 414th's flown values (60%/80%/static 1/radius 100%/wave ×2, big-iron explTable trims, shaped_charge flags on the 4 HEAT/AP rockets) in upstream's own plugin.json→sd3-config architecture. Plugin stays default-OFF upstream.
  - [#828](https://github.com/dcs-retribution/dcs-retribution/pull/828) **Self-closed 2026-07-20** on Druss99's review — NOT a rejection: he wants recon built as a larger opt-in effort (a new mission type, an optional script, and options for what must be scouted vs what starts known) and said he would write the GitHub issue for it. Re-offer against that issue, not as this PR. Was: recon fog-of-war (§3) — the flagship carve. **Rebased 2026-07-19**: squashed to one commit on dev @ `acf02b75`, re-validated (upstream pytest 451 passed; the new ship-movement test double gained the `game.settings` chain `known_for` reads), `MERGEABLE`. Briefly un-drafted, then **deliberately re-drafted the same evening** (21:36→21:40Z per the PR timeline) — currently a **draft**; un-draft when ready.
  - [#806](https://github.com/dcs-retribution/dcs-retribution/pull/806) **Self-closed 2026-08-02** in favour of #925, which takes Druss99's suggested direction. Was: configurable cruise/patrol altitude.
  - [#794](https://github.com/dcs-retribution/dcs-retribution/pull/794) **Self-closed 2026-08-11** on review: a reviewer argued mobile AA should be gated behind an option and that DCS has no real-time satellite datalink to justify the MFD hide. Fork §7 unaffected. Was: hide mobile SAM in combined groups (§7).
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
- **Self-withdrawn (NOT rejected, NOT upstream):** [#873](https://github.com/dcs-retribution/dcs-retribution/pull/873) culling: keep scenery-objective kill tracking in culled regions (opened 2026-07-16, **self-closed 2026-07-21**; the ledger listed it as open until 2026-08-08). **Do NOT re-carve — the premise is wrong and two maintainers said so.** Starfire13 in review: a map-object strike target that is a package's objective is not actually culled, which the code confirms (`compute_unculled_zones` adds every non-BARCAP package target; `position_culled` spares everything within `perf_culling_distance`, 100 km by default). The primary dev, 2026-08-08: culling then striking a culled area is cheating, because the air defences that protected that target were deleted for frame rate. Both hold, and together they mean the only scenery this path reaches is a deep-rear opportunity kill on an undefended building — so upstream's early return is correct behaviour, not a bug. **The fork keeps its own exemption** (`perf_culling` is default `False`; consistency is worth more to a squadron campaign than an exploit nobody runs). One separable half is still a real upstream defect and is NOT carved while the freeze is on: the same early return skips `generate_destruction_trigger_rule`, so scenery destroyed in an earlier turn renders intact in culled regions. See `414th-scenery-kill-tracking-notes.md` §4. · [#784](https://github.com/dcs-retribution/dcs-retribution/pull/784) Iran pack (**re-carved clean as draft #886, late 2026-07-19**) · [#786](https://github.com/dcs-retribution/dcs-retribution/pull/786) AAQ-33 era restriction (folded into the merged #843) · [#790](https://github.com/dcs-retribution/dcs-retribution/pull/790) orbit deconfliction (still fork-only — re-carve if wanted) · [#891](https://github.com/dcs-retribution/dcs-retribution/pull/891) blue-block miz markers (**closed by the DM 2026-07-20, 25 min after Starfire13's review** — "352 EWRs in Normandy. Good lord…" made the 443-marker Normandy resurrection a non-starter, and the comment's real ask was **CJTF block-convention consistency** across object classes ("SAMs have to be defined with CJTF Red, but AAA and static armour groups allow both"). The fork implemented the full consistency rule same day — every loader class reads both blocks; `factories` was the remaining silent-drop hole with 3 shipped red-block factories resurrected. **The re-carve was DROPPED 2026-08-05 (DM call) on a finding that invalidates its premise:** the Custom-campaigns wiki carries a **"Unit Type Quick Reference" spec table assigning a required CJTF block per object class**, and upstream's loader matches it **exactly on all 19 classes** (Red: EWR/all 3 SAM ranges/ship/missile/coastal/offshore/neutral-FOB · Blue: factory · Either: AAA/armor/ammo/strike/comms/power/command-center/FOB). So nothing is "silently dropped" — a blue-block SAM marker is dropped because the author placed it in the block the documentation forbids, and the fork's read-both-blocks rule is a **deliberate deviation from a documented upstream spec**, not a bugfix. Making it a carve would be a *spec change* (uniform "Either" + a wiki edit), which is a maintainer design call and was not worth pursuing. See inventory item 17).
- **Closed, superseded (the 2025-11-27 + 2026-06-09→11 early carve attempts; no action owed):** #621, #622 (the initial uploads) · #774/#776 (final-waypoint crash, superseded by #788) · #775/#777 (AWACS orbit flip) · #778/#781/#783 (SCRAMBLE/scramble-logic flight types — the retired ramp-scramble line, see §1) · #779/#780 (C-130J JAMMING, §2) · #845/#846 (folded into #847).
- **Era-gate payload options — DONE (opened 2026-06-27 as #843):** the combined **"era-gate payload-editor options"** PR = JHMCS property gating (§24) **+** a redo of the withdrawn #786 AAQ-33 pod fix. Self-contained, no 414th deps, builds on the upstream `restrict_weapons_by_date` toggle; Black/mypy/pytest validated locally before push. See upstreaming-inventory item 11.

**Crowded upstream zones — do NOT carve into these without coordinating** (active non-414th PRs):
- Planning revamps — prokop7 [#676](https://github.com/dcs-retribution/dcs-retribution/pull/676) BARCAP, [#674](https://github.com/dcs-retribution/dcs-retribution/pull/674) SEAD/DEAD, [#678](https://github.com/dcs-retribution/dcs-retribution/pull/678) BAI, [#677](https://github.com/dcs-retribution/dcs-retribution/pull/677) attack-infra.
- Player region control — red-one1 [#686](https://github.com/dcs-retribution/dcs-retribution/pull/686) (WIP draft: navmesh-polygon AO hard-limiting A2G missions). The BMS study note's candidate 4 is the *weighting* version of this territory; the fork's own *constraint* version was §40's ROE zones, removed 2026-07-21.
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
- **Code comments record why, never what (STANDARD, 2026-08-11 user call).** A comment earns
  its place by saying something the code cannot: a constraint learned from a flown test, a
  deliberate exclusion, an upstream bug being worked around. Never narrate the next line.
  - **Cap a block at ~3 lines.** Longer rationale belongs in the feature's
    `docs/dev/design/` note; the comment becomes one line pointing at it.
  - **A plugin or module file header may run to ~15 lines** — it is the entry point for a
    reader who has no other. Shape: one line of purpose, the `docs/` pointer, then the
    constraints a reader could undo by accident, one line each. Everything else goes in the
    note. Reference: `resources/plugins/intercept/intercept-config.lua` (104 → 16 lines).
  - **A pointer must resolve.** Confirm the file exists before committing the reference — a
    dead `docs/dev/...` pointer is worse than none, and one shipped in the first draft of
    this very sweep.
  - **Data files carry values, not essays.** A unit yaml gets the number and nothing else —
    the reasoning lives in the design note. The `Air Assault:` priorities are the reference
    case: a tier scheme with per-file justifications was written and stripped the same day.
  - **Compress a constraint comment, never delete it.** The hard-constraints list above exists
    because those cost missions to learn, and most of them live in comments. Wordiness is a
    smaller failure than re-opening a settled question.
  - Measured 2026-08-11: the fork ran **8.3%** comment density against upstream's **4.8%**, and
    2.5× its rate of multi-line blocks. Re-measure before claiming a cleanup worked.
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
- **When the evidence contradicts the instruction, lead with that and stop (STANDARD,
  2026-08-23 user call — "I am very often wrong and if you find EVIDENCE that im going
  down the wrong path then speak up and say it").** If something in the tree, a manual,
  a log or a generated artifact contradicts what was asked, the reply opens with that
  finding. Do not build the thing and record the contradiction in a design note — a
  buried contradiction changes nothing and costs the work twice.
  - **The case this exists to prevent** (2026-08-23, the F-14's "7 waypoints"): the ask
    was to drop target waypoints to fit a seven-waypoint route cap. The Heatblur manual
    says the CDNU stores twelve flight plans of fifty waypoints, and that the *PTID
    displays* eighteen at a time under a priority ranking — "seven" is `Priority WP 1-3`
    plus `Generic 4-7`, a display rank, not a capacity. There was no cap to fit. The
    route was trimmed anyway and the finding went into the note.
  - **Evidence means checkable**: a file, a manual page, a measurement, a log line. Name
    the source in the same breath. A *preference* cannot be contradicted by evidence —
    taste calls stand, and "the LAR should read conservative" needs no defence.
  - **Two sentences, then the question.** Not a lecture, not a refusal. If the call is
    reaffirmed, build it in full and say plainly that it was reaffirmed.
  - This outranks agreeableness. Saying "yes" to a call the evidence has already
    answered is the expensive failure, not the polite one.
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
