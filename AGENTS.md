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
    `414th-vietnam-political-will-roe-notes.md` (**the Vietnam campaign layer** — the approved
    month-scale rework, spec of record: (1) a symmetric **political-will economy** (BLUE
    Political Will / RED Regime Resolve on `Coalition`, fed from the existing `Debriefing` —
    weighted airframe losses with a B-52 multiplier, POWs draining per turn held, ROE
    violations, trail-logistics attrition for RED) with a **negotiation win/loss**
    (`check_win_loss` branch: break Hanoi's resolve before Washington's patience breaks —
    territory win stays) and (2) **ROE / Route-Package escalation** riding the campaign-phases
    spec's P0–P2 + two authored extensions (`restricted_zones` soft-enforced by will penalties,
    `target_release` gates with RESTRICTED map badges, a Rolling Thunder → Linebacker II arc
    for the 4 Vietnam campaigns; sanctuary airfields fall out of zones). Delivery W1–W5, one PR
    each (W5 = the thin QRA→GCI ambush adaptation). **W1 + W2 landed** — W1 = the observe-only
    will (`Coalition.political_will` + the `vietnam_political_will` toggle + the
    `record_political_will` debrief feed in `game/fourteenth/political_will.py` + the SITREP
    will band); W2 = the **negotiation ending** (`negotiation_verdict` backing a gated
    `check_win_loss` branch ahead of the territory checks — RED resolve exhausted → WIN "Hanoi
    agrees to terms", BLUE will exhausted → LOSS "Washington orders withdrawal", BLUE-loss
    precedence on a simultaneous collapse; territory victory untouched — plus once-only
    era-framed exhaustion banners and the 4 Vietnam campaigns preseeding the toggle; weight
    balance = checklist M1); **W2b landed** = the **static front** (`vietnam_static_front`,
    preseeded ×4 — `game/fourteenth/static_front.py` clamps each front's position to a ±10 %
    band around its campaign-start anchor via a `FrontLine._blue_route_progress` clamp hook,
    so the strength battle bends the line + feeds will but never sweep-captures a base; Air
    Assault stays the one territorial lever; armed/disarmed idempotently from
    `Game.initialize_turn`; in-game pass = checklist M2); **W3 landed** = campaign-phases P0+P1
    (feature §40 — generic, all campaigns, `campaign_phases` default ON); **W4 landed** = the ROE
    escalation layer (authored `phases:` arcs ×4 Vietnam campaigns — Rolling Thunder → Bombing
    Halt → Linebacker → Linebacker II — with `restricted_zones` soft-enforced by will penalties,
    `locked_targets` target-release gates + RESTRICTED badges, the red dashed map layer, and
    will-coupled `advance_when` escalation; in-game pass = checklist M4); **W5 landed** = the
    GCI-ambush adaptation (`Doctrine.gci_ambush` → late-scramble/close-engage dispatcher tuning
    + the intercept Lua's hit-and-run leash; sanctuary basing falls out of the W4 zones;
    checklist M5). **The campaign-layer arc W0–W5 is COMPLETE.** The
    Vietnam pieces stay default-off (`vietnam_political_will`/`vietnam_static_front` gated); no
    debrief-schema changes anywhere in the arc),
    `414th-campaign-phases-notes.md` (**campaign phases** — a thin doctrine-like *phase*
    layer, active per turn-range, that biases the auto-planner's offensive intent + shows in
    the UI/kneeboard; three authoring tiers over one `CampaignPhase` object — **Tier 0
    inference is the default for all 66 campaigns** (a turn-by-turn classifier reads live IADS
    ratio / air threat / front momentum / territory via existing accessors → rollback →
    interdiction → offensive, with hysteresis), Tier 1 = YAML-tuned, Tier 2 = authored arcs
    for the 3 hand-built campaigns; rides the `VIETNAM_DOCTRINE` override precedent, composes
    with doctrine, never a commander rewrite; reactive defense stays deterministic (§17
    boundary). A **6-campaign inference pilot** (4 modern + 2 Vietnam) is done — see
    `414th-campaign-phases-pilot.md` + the reusable `tools/campaign_phase_laydown.py`
    (`--lite` raw-`.miz` parse / `--engine` real pipeline); it surfaced two threshold
    refinements now in the spec: an **absolute long+medium-SAM floor** gate and EWR
    de-weighting. The **all-66 draft table is now `--engine`-authoritative** (re-run
    2026-07-01 on the real install) — `tools/campaign_phase_classify.py` (the offline §3.2
    classifier reference impl; `--laydown` consumes a saved engine dump) +
    `414th-campaign-phases-all66-draft.md` (57 Rollback / 5 Air Superiority / 4 Interdiction).
    The engine run closed all three `--lite` blind spots (mod-SAM undercount, auto-assign air,
    and the newly found **generator-filled AA slots**) and corrected the pilot's headline:
    **Khe Sanh actually fields 4 generated SA-2/SA-3 batteries ⇒ opens Rollback**; the genuine
    below-floor cases are Shattered Dagger / No Man's Land / Valley of Rotary / Northern
    Guardian, with Velvet Thunder exactly at the floor (3 sites, keeps Rollback). SAM banding
    reads TGO `GroupTask` LORAD/MERAD (the DEAD planner's own target set) — `IadsRole` can't
    band it (its SAM role swallows SHORAD). **P0+P1 LANDED** as feature §40 / Vietnam campaign
    layer W3 — Tier-0 inference + hysteresis + the HTN soft emphasis + the kneeboard/client
    status surfaces are live for all campaigns (`campaign_phases`, default ON; the runtime
    classifier bands by the same LORAD/MERAD set). **P2 + first P3 arcs LANDED** (Vietnam W4):
    the `phases:` YAML authoring tier, `advance_when` conditions, the ROE zones/release payload
    + planner gate, and the 4 Vietnam Rolling Thunder → Linebacker II arcs; still open =
    objectives checklist, per-phase whitelist deltas, `front_line_stance`, the 3 wiki-campaign
    arcs),
    `414th-airwar-planner-consolidation-notes.md` (behavior-preserving consolidation of the
    air-war planner's threat-field + standoff geometry onto one `AirspaceGeometry` service;
    keeps the brain in Python, Tier-C/`Ops.Chief` explicitly out of scope),
    `414th-scar-king-fac-notes.md` (SCAR rework: a player-first loiter/"hold" package tasked by
    the C-130 "King" on-scene commander onto real static armor TGOs so losses track natively;
    minimal-F10 designation; thin MOOSE bridge, not `Ops.Chief`; future auto-planned commander),
    `414th-combat-sar-normal-task-notes.md` (make Combat SAR a normal, default-on, **two-sided**
    auto-task: AI rescues AI on blue+red, players can drop in. **Route 1 (the owned survivor ledger)
    HAS since shipped** — `combatsar-config.lua` credits AI rescues by real identity and makes AI
    ejections capturable → POW, coalition-generic runtime (verified 2026-06-30, G11/G20); the note's
    "AI-rescue scoring is cosmetic / AICSAR anonymous clone" diagnosis is now stale. What's still
    **design-only** is the surrounding framing: default-on (`auto_combat_sar` still defaults OFF) +
    auto-planned **symmetric red** (only blue is auto-fragged today)),
    `414th-vietnam-ops-notes.md` (**Vietnam Ops suite** — a `Vietnam Ops` settings page gating five
    opt-in period mechanics: Arc Light as a heavy-bomber Strike *effect*, AAA flak gauntlet, naval
    gunfire support, Armed-Recon truck-convoy interdiction, Super Gaggle resupply; Tier-A runtime only,
    default OFF / campaign-flipped ON; **Phases 1–4 landed** = the settings page + §32 Arc Light + §33
    flak gauntlet + §34 naval gunfire + §35 convoy interdiction (the Steel Tiger trail; spawn Lua
    **verified 2026-06-30**, checklist L6); phase 5 (Super Gaggle) is blocked on an auto-plannable CTLD
    cargo run the engine lacks),
    `414th-vietnam-airbase-harassment-notes.md` (**Vietnam Ops §F — airbase harassment**: scoped-only
    sapper/mortar/rocket standoff fire on opposing-occupied fields, following the §33 flak runtime
    pattern; hard requirement = never target a player-spawn field + a startup grace period. **LANDED** as
    CLAUDE.md §36 — the emitter + plugin runtime are in; needs an in-game pass, checklist L8),
    `414th-vietnam-retribution-notes.md` (**"Vietnam Retribution" mode** — the *framing* layer the Ops
    suite lives inside: three thin layers over the one engine — a New Game "Vietnam" shell + content
    filter + a doctrine profile (`VIETNAM_DOCTRINE`) that renames taskings (MiGCAP/Iron Hand/Alpha
    Strike/Sandy) via a display-only override on `Doctrine` (never the persisted enum) and gates the
    planner whitelist. **P0 (era tags) + P1 (doctrine model + 10-faction repoint) + P1b (display read-path)
    + P1c (period-authentic planner *numbers*: A2A engagement ranges shortened to the early-missile/gun era
    — `cap_engagement_range` 35→22 NM, `escort_engagement_range` 20→10 NM so MiGCAP/escort fight close not
    BVR; `rtb_speed` 450→400 kt; and a `VIETNAM_GROUND_PROCUREMENT` OOB that is infantry/artillery/AAA-heavy
    with light armour and **no ATGM/IFV** — the ATGM-decisive war was Yom Kippur, not Vietnam. So the doctrine
    now makes the era *play* differently, not just read differently; rebadge-equality test extended + range/
    speed/ground-ratio tests added)
    + P2 era pre-seed (Vietnam campaigns auto-enable the Ops mechanics on select) + P2 New-Game "Vietnam" card
    (Intro `vietnamMode` radio → `TheaterConfiguration` filters the list to `era: vietnam` via
    `Campaign.matches_era`; needs an in-app pass) + P3 strike-deadlock fix + P3 tasking whitelist + P3 Alpha
    Strike sizing landed** — the design's phases are now all in (Iron Hand = Shrike-vs-emitter is moot now SEAD
    is dropped). **P3 strike-deadlock**: Vietnam has no SEAD, so
    retribution's "suppress the air defense before you strike" rule deadlocked the whole offensive fleet
    (0/28 strike + 0/13 BAI plannable — an upstream-shared behaviour, not a fork bug); two additive
    default-False `Doctrine` flags (`strike_through_air_defense_threat`, `plan_strikes_without_full_escort`)
    let Vietnam strike into threatened areas + fly unescorted (headless-verified 7→19 BLUE packages; needs a
    NEW game). **P3 tasking whitelist**: `VIETNAM_DOCTRINE.tasking_whitelist` drops SEAD/SEAD_ESCORT/
    SEAD_SWEEP/DEAD/ANTISHIP, gated in `PackagePlanningTask.fulfill_mission` (disallowed primary scrubs the
    package; disallowed escort is just dropped) — fixes era jets on wrong tasks (an A-1 on SEAD Sweep) and
    headless-verified SEAD/DEAD/anti-ship 13→0 while STRIKE 1→5 / BAI 6→13 rose. **P3 Alpha Strike**:
    `Doctrine.strike_flight_count` (default 1) can fan N coordinated, shared-TOT STRIKE sections onto one
    target in `PlanStrike` (reads the *planner's* doctrine via `target.coalition.opponent.doctrine` — the
    target is enemy-owned). Vietnam masses a **surge deck-load: up to 4 sections + a forced fighter escort**
    on ONE target — the real Alpha Strike (`strike_flight_count=4` + `always_escort_strikes`, which forces
    the A2A escort "needed" in `check_needed_escorts` even with no detected air threat; still pruned when no
    fighter is free). Only the first section is required — the rest are **surge sections**
    (`ProposedFlight.optional`, honored in `plan_mission`): they plan when a squadron has the jets and drop
    silently when not (no scrub, no purchase order), so the top-priority target absorbs the strike fleet and
    later strikes shrink toward single sections (replay: `WOLVERINE: STRIKE x2 ×4 + ESCORT x2 + TARPS`, 11
    aircraft on one target, while `NEWT` flies the leftover single section). The fan was briefly reverted to
    1 when the sections flew naked; restored once the fighter-economy levers held.
    The **"Alpha Strike" label is earned, not flat** (user playtest caught four separate 2-ships each
    wearing the name): `Package.is_massed_strike` (≥2 STRIKE sections totalling ≥4 bombers) gates the era
    rename at all three display sites (`package_description`, `Flight.task_display_name`,
    `FlightData.task_display_name`) — a lone section (or a pair of single-ships) reads plain "Strike".
    **No solo strikers**: strike section size is floored at 2 for every doctrine (1-unit targets were
    producing single A-4s flying strikes alone; a tiny target now draws a real 2-ship section or nothing). The
    **fighter-economy levers** landed after
    the Linebacker naked-B-52 playtest (2026-07-01): `Doctrine.escort_support_aircraft=False` (Vietnam) drops
    the AEWC/tanker fighter escorts that consumed 8 of 10 fighters before any strike planned
    (`fulfill_mission` filter), and `Doctrine.strike_escort_reserve=4` +
    `AirspaceGeometry.trim_rounds_for_escort_reserve` trims BARCAP volume (coldest CPs first, down to
    abandoning low-threat coverage but never the hottest location) so the fighter force escorts the
    *shooters* — save-replan verified: support escorts 8→0 jets, BARCAP 10→2. The reserve is also **fenced**
    (`PackageFulfiller.escort_reserve_withholds`, the strike-first escort priority): a non-STRIKE package
    (BAI, OCA, even CAS in a true famine) is refused its A2A escort whenever planning it would dip the live
    `AirWing.untasked_fighters()` pool below the reserve — only a STRIKE-led package may spend those last
    airframes, so the freed fighters actually reach the bombers instead of the first BAI section planned. A
    withheld escort is not a shortage (the package flies unescorted, no procurement order). Doctrines are
    pickled by value — a NEW game carries the new numbers. The Ops suite's Arc
    Light/flak/NGFS are this design's P4 flavor, already built)
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
   **Player-manned QRA**: `Squadron.qra_player_manned` carves N of the reserve into a
   cold-start, home-field base-defense BARCAP (`HomeBaseDefenseZone`) fragged for the human at
   planning (`Coalition._plan_player_qra`, BLUE only); those airframes are debited from the AI
   dispatcher (`ai_qra_resource_count`) so a jet is never both manned and air-spawned. A
   Phase-3 **scramble cue** (`PlayerAlertEntry` → `dcsRetribution.Intercept.PLAYER_ALERT` →
   `intercept-config.lua`) calls the player to scramble when a raid closes inside the GCI
   radius + a lead margin. Design note `414th-qra-player-manning-notes.md`; checklist A3/A4
   (need an in-game pass). **GCI-ambush posture** (Vietnam campaign layer W5):
   `Doctrine.gci_ambush` (VIETNAM only) makes a side's dispatcher fly era hit-and-run GCI —
   engage radius shrunk to the doctrine's 22 NM cap range, scramble capped at 40 NM (late
   launch, slash the strike package near its target), and a Lua-side leash (disengage 50 NM
   from home + RTB at 35 % fuel) so MiGs hit once and recover; other doctrines pass the QRA
   settings through unchanged (`dispatcher_tuning` in `interceptluadata.py`; checklist M5).
2. **JAMMING flight type** — C-130J as EC-130H/RC-130H EW+ISR platform (`c130j` plugin);
   the old generic `ewrj` fighter-pod jammer is retired and must not be restored.
3. **TARPS recon + BDA fog-of-war** — player F-14 photo recon; viewer-aware fog (damage lag +
   recon intel-fog) makes recon worth flying. **AI recon BDA capture** (`airecon` plugin, added
   2026-07-01) closes the G19 gap that the MOOSE TARS film path is **player-only** (its birth
   handler drops any non-player unit), so auto-paired *AI* recon flights confirmed nothing:
   `populate_ai_recon_lua` (`aireconluadata.py`) emits each AI-flown, player-coalition (BLUE)
   `TARPS` flight + its target; the `airecon` plugin watches each and, when it survives to overfly
   (within a trigger range of the target), records the enemy ground units there into the same
   `tars_recon_captures` ledger the player film menu feeds — so the debrief
   (`debriefing.py`→`tars_reconned_tgos`) treats an AI recon capture identically. A shot-down /
   aborting recon flight confirms nothing (one-shot). Player-crewed TARPS is never emitted (still
   the F10 film path); blue-only. Emitter-tested; runtime Lua needs an in-game pass (checklist G19).
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
    standing package = **1 King (C-130) + 1 Jolly Green (helo) + 2–4 Sandy**; Sandy's racetrack is
    planned once at generation, but an **AI-crewed** Sandy is now **dynamically diverted** at runtime
    (`combatsar` plugin, added 2026-07-01) off that racetrack to hold + actively engage
    (`EnRouteTaskEngageTargetsInZone`) near a live ejection once one occurs, freeing again once the
    survivor is resolved — a player-flown Sandy is untouched (voice/SRS coordination). "Walking the
    rescue helo in" itself is still voice-first only, not scripted, for either. features doc §15,
    checklist G23 (new — unflown). **Enemy-capture race**
    (`combatsar` plugin): on ejection an enemy snatch party (several small dispersed teams, spawned
    under the opposing faction's country) may race to seize the survivor — kill it
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
    Recon / Clean), and choices persisted to the campaign save (localStorage-cached), except the
    transient fog overview (`GET`/`PUT /game/map-layers` → `Game.client_map_layers`). The
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
    content into at most four pages instead of the ~10-page sprawl: **P1 Brief Sheet** (the consolidated
    colour-coded one-pager — §31 — replacing the old Game Plan/BLUF), **P2 Threats & Targets** (target ALIC
    over the enemy-AD threat cards, colour-coded to match), **P3 Comms & Coordination** (radios +
    AWACS/tanker/JTAC + colour-coded code words + brevity), and an
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
31. **One-page Brief Sheet + deck-wide colour scheme** — the compact deck's lead page is now a single
    scannable **Brief Sheet** (`BriefSheetPage`) modelled on the squadron's printed Appendix A one-pager
    (Red Tide handbook): header, mission, the **full labelled route — every steerpoint with number +
    planned time** (`HOLD 1 12:32 → TKR 2 12:38 → JOIN 3 12:49 → TGT 5-8 13:01 → LAND 10`; consecutive
    strike points collapse to a range), admin, threats (air + SAM), game plan, comms, code words,
    bullseye, fields (RWY/ATC/TCN), WX (departure-field QNH/QFE + surface wind), loadout, laser,
    Combat SAR — **auto-filled** by
    `_build_brief_sheet_data` (route from waypoints, loadout from the jet's pylons cleaned to ordnance, air
    threats from the enemy faction's fighters, the rest re-surfaced). It replaces the dense Game Plan/BLUF
    (which survives for the full non-compact deck). Empty fields render a `______` **fill-in blank**
    (`_blank_line`) like the printed template — the layout never collapses — plus a `NOTES` blank. A new
    **theme-aware four-colour semantic palette** on `KneeboardPageWriter` (+ a `text_runs` inline-colour
    primitive) — blue nav/comms, amber threats/fuel, green success, red abort — is applied across **P1**,
    the **P2 threat cards** (amber MEZ/Detect, blue HARM/cues) and the **P3 code words** (push blue, SUCCESS
    green, ABORT red) so the whole deck reads as one product. Loadout/laser validated against a real `.miz`.
    (`game/missiongenerator/kneeboard.py`; features doc §31, checklist needs an in-game pass.)
32. **Arc Light heavy-bomber Strike carpet** — the first **Vietnam Ops suite** feature (design note
    `414th-vietnam-ops-notes.md`; settings page §28 "Vietnam Ops"). Reframes Arc Light as an *effect of the
    Strike task*, **not** a new `FlightType`: when a heavy bomber (B-52H/B-1B/Tu-95MS/Tu-142/Tu-160/Tu-22M3)
    flies a `STRIKE`, the runtime walks a carpet of explosions across the target at the run-in instead of a
    single aimpoint, modelling Operation Niagara. Tier-A config bridge — Python emits `dcsRetribution.VietnamOps.arcLight`
    (each eligible bomber group + its target centre) only when the `vietnam_arc_light` toggle is on, and the
    `vietnamops` plugin watches each bomber, then on reaching the release range walks a box of `trigger.action.explosion`
    impacts oriented along the bomber's bearing-to-target (carpet length/width/power/release-range are plugin
    options). A bomber shot down before the run-in never fires — losses stay native; tactical strikers are
    untouched. (`game/missiongenerator/vietnamopsluadata.py`, `game/missiongenerator/luagenerator.py`,
    `resources/plugins/vietnamops/`, `game/settings/settings.py`; features doc §32, checklist L1.)
33. **AAA flak gauntlet** — the second **Vietnam Ops suite** feature: recreates the AAA-heavy Vietnam
    threat environment (the standing "real threat = AAA, not SAMs/MiGs" gap). With `vietnam_flak_gauntlet`
    on, the `vietnamops` plugin discovers AAA guns at **runtime** by the DCS `AAA` unit attribute (frontline
    ZSU/Shilka belts + airfield guns), and any opposing aircraft within an alive gun's range and below the
    effective ceiling draws **barrage flak bursts** (`trigger.action.explosion` airbursts at altitude). A
    steady, predictable heading+altitude **tightens** the bursts (and a sustained predictable run draws the
    occasional close "tracking" round); jinking/varying altitude widens them — atmospheric pressure to
    manoeuvre, mostly visual with a modest tunable bite, **not** a hidden hard-kill SAM. Python emits only an
    on-marker (`dcsRetribution.VietnamOps.flak`); range/ceiling/miss-distances/power are plugin options.
    Symmetric (both sides' AAA). (`game/missiongenerator/vietnamopsluadata.py`, `resources/plugins/vietnamops/`,
    `game/settings/settings.py`; features doc §33, checklist L2.)
34. **Naval gunfire support** — the third **Vietnam Ops suite** feature: offshore gun ships shell shore
    targets. Python (`_populate_naval_gunfire`) emits each naval gun ship (CRUISER/DESTROYER/FRIGATE — the
    VWV battleship New Jersey is class Destroyer, so it's covered) + its coalition; the `vietnamops` plugin
    runs **two modes** off that list: a **player F10 "Naval Fire Mission"** menu fires the nearest in-range
    friendly gun ship on the coalition's last F10 map marker (`world.getMarkPanels`), and an **automatic
    coastal bombardment** where each gun ship shells the nearest opposing ground target within gun range every
    cadence (`MOOSE TaskFireAtPoint`, the TIC artillery path). **Coastal by construction** — with no enemy
    ground (or no marker) in a ship's range nothing fires, so inland campaigns (Khe Sanh) no-op. Range/rounds/
    salvo/auto-cadence are plugin options. (`game/missiongenerator/vietnamopsluadata.py`,
    `resources/plugins/vietnamops/`, `game/settings/settings.py`; features doc §34, checklist L3.)
35. **Convoy interdiction (Steel Tiger)** — the fourth **Vietnam Ops suite** feature: a moving enemy supply
    column on the road behind the FLOT (Steel Tiger / Ho Chi Minh Trail), surfaced through Armed Recon. **Now a
    real, tracked convoy in the force model, not a phantom runtime spawn** (reworked 2026-07-01 to eliminate a
    "free non-existent unit" — the old `coalition.addGroup` trucks existed only in the `.miz`, so killing them
    cost the enemy nothing and no loss was recorded). Retribution already models convoys
    (`coalition.transfers.convoys` carry real ground units, spawn as road-moving groups via `ConvoyGenerator`,
    are Armed-Recon/BAI targets, and their loss is recorded as `enemy_convoy` so the units never arrive), so the
    feature now just **ensures one is flowing**: `ensure_enemy_trail_convoy` (`game/fourteenth/vietnam_convoy.py`,
    run once per turn from `finish_turn`) — when `vietnam_convoy_interdiction` is on and the opfor has no convoy
    travelling — moves a few of the opfor's **real** rear-area ground units toward the road corridor nearest the
    front, debited from the source base (`new_transfer` → `commit_losses`). So interdicting the trail now denies
    the enemy real reinforcements (kill it and they never reach the line; let it through and they do), and the
    kill is recorded natively. Fully guarded (no front / no rear units / no road corridor ⇒ no-op; the engine's
    organic convoys still serve). **No `vietnamops` plugin runtime** any longer — the emitter and the Lua convoy
    section are removed. (`game/fourteenth/vietnam_convoy.py`, `game/game.py`,
    `game/settings/settings.py`; features doc §35; checklist L6.)
    **Right-click planning (added per playtest):** the player **right-clicks an enemy supply route** on the
    map to frag the interdiction package — `SupplyRoute.tsx` `contextmenu` → `POST /qt/create-package/supply-route/{route_id}`
    → `interdiction_target_for_route_id` resolves the route (its id now encodes the two CP ids) to the enemy
    end (contested CP first) → the Qt package dialog opens there **pre-selected on Armed Recon** (the add-flight dialog auto-opens); friendly routes 404.
    Supersedes the old "no right-click" design stance; still an Armed Recon frag, just discoverable on the
    route. The client API hook is hand-added to the generated `_liberationApi.ts` (codegen unavailable
    locally). (`game/server/qt/routes.py`, `game/server/supplyroutes/models.py`,
    `client/src/components/supplyroute/SupplyRoute.tsx`; test `tests/server/test_supply_route_interdiction.py`;
    checklist L7 — needs an in-app pass + the CI client rebuild.)
36. **Airbase harassment (rocket/mortar siege)** — the fifth **Vietnam Ops suite** feature (design note
    `414th-vietnam-airbase-harassment-notes.md`, §F): forward, opposing-occupied airfields draw sporadic
    standoff rocket/mortar fire near the ramp, recreating the near-constant siege of Bien Hoa/Da Nang/the Khe
    Sanh strip — "the rear isn't a safe area." Same shape as §33 flak: Python emits a small target list and the
    `vietnamops` plugin runs the runtime. `_populate_airbase_harassment` (`vietnamopsluadata.py`) walks the
    airfield/FARP control points and emits each one that is **occupied** (non-neutral), **forward** (within
    `HARASSMENT_FRONT_REACH_M` ≈ 200 km of a front — so a deep-rear or peacetime field is never shelled; no
    front ⇒ no node ⇒ plugin no-ops), and **not a player-spawn field this mission** (departure/arrival/divert of
    any client flight — the hard anti-grief guarantee, filtered in Python so an excluded field can never become
    a target; the exclude set is also emitted under `excludedFields` as a Lua-side double-guard). Each record is
    `{ name, x, y, coalition }`. The plugin schedules a per-field loop that, **after a startup grace period**
    (default 300 s, so nobody is shelled mid-alignment), lands a small dispersed `trigger.action.explosion`
    barrage near the parking centroid on a randomized cadence — mostly noise/smoke with a modest, tunable bite,
    not precision counter-air. Symmetric (whichever side's forward fields qualify). Plugin options: interval,
    rounds/event, dispersion, per-blast power, grace. (`game/missiongenerator/vietnamopsluadata.py`,
    `resources/plugins/vietnamops/`, `game/settings/settings.py`; features doc §36, checklist L8 — needs an
    in-game pass.)
37. **Super Gaggle hilltop resupply** — the sixth **Vietnam Ops suite** feature (design note
    `414th-vietnam-ops-notes.md`, §E): a formation of transport helos (+ a fast-mover AAA-suppression flight)
    runs supplies into a cut-off forward friendly outpost while the player can fly escort — the Khe Sanh "Super
    Gaggle." **Drawn from real BLUE squadrons + losses tracked, not a phantom spawn** (reworked 2026-07-01 to
    eliminate free airframes — the old `coalition.addGroup` helos were unaccounted units on an **unbounded
    respawn loop**, so losing them cost nothing). The gaggle is now planned once per turn from **real squadrons**:
    `plan_super_gaggle` (`game/fourteenth/super_gaggle.py`, run from `finish_turn`) picks the besieged BLUE
    FOB/FARP near a front + a rear launch field, a **real BLUE helo squadron** to fly the run + a **real BLUE
    attack squadron** for the suppressors, and records a `SuperGaggleCommitment` (persisted on the game: the
    squadrons + the exact per-airframe unit names + geometry). `_populate_super_gaggle` emits that commitment; the
    `vietnamops` plugin spawns **exactly those** airframes, by name, **once** (no respawn — airframes are bounded
    to the commitment). At debrief, `reconcile_super_gaggle` (`missionresultsprocessor.commit_super_gaggle`) charges
    each committed unit name found in the debrief's killed units back to its squadron (`owned_aircraft -= lost`,
    `destroyed_aircraft += lost`) — a **real airframe loss**, exactly like any other; survivors cost nothing (a
    returning detachment, so no pre-debit/return), and a delivered run credits the outpost a small ground-strength
    boost. No base-Lua / debrief-schema change: the spawned units already fire the DCS death events
    `dcs_retribution.lua` records, so their names land in the debrief killed lists (as untracked ground units,
    since they aren't in the `UnitMap`) and are matched by name. Fully guarded (feature off / no outpost / no
    launch / no helo squadron with airframes ⇒ no commitment ⇒ no node ⇒ plugin no-ops). Blue-only (symmetry
    deferred). Plugin options now just speed/altitudes (type/count come from the squadrons). (`game/fourteenth/super_gaggle.py`,
    `game/game.py`, `game/sim/missionresultsprocessor.py`, `game/missiongenerator/vietnamopsluadata.py`,
    `resources/plugins/vietnamops/`, `game/settings/settings.py`; features doc §37, checklist L9 — needs an
    in-game pass.)
38. **FAC(A) willie-pete target marking** — the seventh **Vietnam Ops suite** feature: the iconic Vietnam
    forward air controller. An airborne OV-10 Bronco loitering over the battle area marks nearby enemy ground
    with **white-phosphorus smoke** so the player (and AI strikers) can visually acquire the target and roll in
    — the ground JTAC (which *lases*, stationary) already exists, so this is the distinct *airborne, smoke*
    half. Same shape as §33 flak (an on-marker + runtime discovery): Python emits only
    `dcsRetribution.VietnamOps.fac = { enabled }` (`_populate_fac`); the `vietnamops` plugin discovers airborne
    friendly units of the FAC type (default `Bronco-OV-10A`) at runtime and, on a cadence, drops white smoke
    (`trigger.action.smoke`, willie pete) on the nearest opposing ground unit within range + a "cleared hot"
    cue. Symmetric (only OV-10 owners have FACs, so blue-effective in practice); needs a friendly OV-10
    airborne over the front, or it no-ops. Runtime-cosmetic (a marker, no gameplay-model change). Plugin
    options: FAC type, spot/mark range, mark cadence. (`game/missiongenerator/vietnamopsluadata.py`,
    `resources/plugins/vietnamops/`, `game/settings/settings.py`; features doc §38, checklist L10 — needs an
    in-game pass.)
39. **Snake and nape (napalm CAS)** — the eighth **Vietnam Ops suite** feature: the iconic low-level napalm
    CAS delivery ("snake" = Snakeye retarded bombs, "nape" = napalm). Same shape as §33 flak / §38 FAC (an
    on-marker + runtime discovery): Python emits only `dcsRetribution.VietnamOps.snakeNape = { enabled }`
    (`_populate_snake_nape`); the `vietnamops` plugin discovers **attack aircraft** at runtime (by the DCS
    `Attack airplanes` attribute) making a **low** (≤ ceiling AGL), **fast** pass **close over an alive opposing
    ground unit**, and lays a **napalm swath** — a line of `trigger.action.effectSmokeBig` fires (auto-stopped
    after a burn time) + a modest per-node `trigger.action.explosion` bite — oriented along the run-in, once per
    pass (a per-aircraft cooldown). Unlike the flak gauntlet (which *punishes* predictable flight), this
    *rewards* pressing the CAS run in on the deck; napalm's real bite on soft targets is the point, and it only
    fires on a deliberate low pass over the enemy. Symmetric (both sides' attack jets); needs an attacker down
    low over enemy ground, or it no-ops. Plugin options: run-in ceiling, min speed, drop range, swath length,
    fire-node count, per-node power. (`game/missiongenerator/vietnamopsluadata.py`,
    `resources/plugins/vietnamops/`, `game/settings/settings.py`; features doc §39, checklist L11 — needs an
    in-game pass.)
40. **Campaign phases (inferred arc + planner emphasis)** — every campaign (all 66, zero authoring) knows what
    *phase* of the air war it is in, the UI shows it, and the auto-planner biases its offensive intent to match
    (spec `414th-campaign-phases-notes.md`; this is its **P0+P1**, landed as Vietnam campaign layer W3). A
    turn-by-turn Tier-0 classifier (`game/fourteenth/phases.py`) reads live state via existing accessors —
    alive enemy long+medium SAM **sites** (TGO `GroupTask` LORAD/MERAD, the DEAD planner's own set — the
    #379-corrected banding, never `IadsRole`) vs. a lazily-snapshotted turn-0 `PhaseBaseline`, enemy
    air-superiority airframes, mean front movement, last turn's captures — and picks **Air Superiority →
    Interdiction → Offensive** with the pilot's **absolute-SAM-floor gate** (a genuinely belt-less theater
    skips Rollback — Shattered Dagger/Valley of Rotary et al., NOT Khe Sanh, which the generator fills with
    SA-2/SA-3), a peer-fight guard, min-dwell hysteresis, and monotonic-forward defaulting
    (regression is authored-only, P2). The active phase reorders **only the offensive middle** of
    `PlanNextAction`'s HTN root methods (BLUE only; the reactive prefix + tail are fixed — the §17 boundary),
    shifting which objectives get first claim on offensive jets. Always explains itself (§3.4 legibility:
    "Interdiction — enemy IADS 22% · air threat low · front static") on the kneeboard **cover-page band** and
    a new **client campaign-status ribbon** (`CampaignStatusBar` over the map, fed by `GameJs.campaign_status`
    — which also carries campaign name/turn/date, previously never sent to the client, + the political-will
    meters on Vietnam campaigns). Gated by `campaign_phases` (default **ON** — [DECIDED] Tier-0 inference is
    the default; the toggle is the kill switch). **W4 added the authored tier (P2) + the ROE escalation
    layer**: a campaign `phases:` YAML block overrides Tier 0 (`parse_phases`/`authored_arc_for`, re-derived
    at load, never pickled) with `min_turn`-scheduled + `advance_when`-accelerated transitions
    (`blue_will_below` couples escalation to the will economy), **restricted zones** (AI planner gate
    `roe_blocks_target` in `PackagePlanningTask.fulfill_mission`, BLUE-only; sanctuary airfields fall out;
    the player is never hard-blocked — zone kills drain will via `count_roe_violations` +
    `BLUE_ROE_VIOLATION`), **target release** (`locked_targets` classes, RESTRICTED — ROE badge on the TGO
    tooltip instead of vanishing), a red dashed **map layer** (`GameJs.restricted_zones` →
    `RestrictedZonesLayer`, Enemy intel group, default ON), and the authored **Rolling Thunder → Bombing
    Halt → Linebacker → Linebacker II arcs in all 4 Vietnam campaigns** (Tbilisi/Sukhumi/Saipan play Hanoi
    per laydown). (`game/fourteenth/phases.py`, `game/game.py`,
    `game/commander/tasks/compound/nextaction.py`, `game/commander/tasks/packageplanningtask.py`,
    `game/fourteenth/political_will.py`, `game/missiongenerator/kneeboard.py`, `game/server/game/models.py`,
    `game/server/tgos/models.py`, `client/src/components/campaignstatus/`,
    `client/src/components/restrictedzones/`; features doc §40, checklist M3 + M4 — need an in-game pass +
    the CI client rebuild.)
41. **High Digit SAMs "Ultimate Compilation" support** — the HDS mod support retargeted from the abandoned
    original v1.4.0 to the maintained successor (https://github.com/dcs-sams/HighDigitSAMs-Ultimate-Compilation,
    v1.4.3+), same `high_digit_sams` toggle (wizard label updated). Unit data read from the **installed mod's
    own Database luas**. Absorbs the breaking changes — renamed S-300PS radars (`30N6 MAST tr`/`76N6E sr`/
    `64H6E MOD sr`) re-pointed in the S-300 Site layout + SA-10B preset + `radar_db.py`; dropped HDS
    KS-19/SON-9/SA-24 replaced by vanilla equivalents (retired pydcs classes + unit YAMLs kept as save-compat
    tombstones ONLY — never reference them) — and adds the new families: **S-400/SA-21 + S-300V4 + S-300PT**
    presets on the extended S-300 Site, **SAMP/T** (+NG) on a new Patriot-geometry `SAMP/T Battery` layout,
    **Pantsir-SM** SHORAD, **SA-7/7b manpads**, 4 EWRs (the **P-37 Bar Lock** closes the period red EWR
    blind-net gap across 16 factions), ERO **ZU-23 Toyota technicals** for insurgents. Era-respecting stock
    faction wiring (modern Russia/redfor, france_2005, 70s-80s Middle-East/NK reds get SA-7/7b, Vietnam reds
    the P-37 only — SA-7s dropped from the 4 Vietnam factions per squadron call — insurgents the technicals). MANTIS needs no
    change (the bridge bands SAMs by Retribution's emitted threat range, not MANTIS's unit-name scan). Fixed
    in passing: `Faction.remove_vehicle` matches DCS type **ids**, and the old name-based HDS strips silently
    never removed anything (upstream-carve candidate). (`pydcs_extensions/highdigitsams/`,
    `game/data/radar_db.py`, `game/factions/faction.py`, `resources/{groups,layouts,units,factions}/`;
    features doc §41, checklist N1 — needs an in-game pass.)
42. **Local DCS chart base layers (map tiles)** — locally installed XYZ tile pyramids appear as extra
    base-map choices in the map layers panel (§19), so the campaign map can show a chart of the *DCS*
    terrain (e.g. Flappie's "accurate DCS Caucasus map" GeoTIFF) instead of mismatching real-world Esri
    imagery. Purely local, never bundled (community-chart copyright): `tools/tile_geotiff.py` (standalone
    Pillow, no GDAL) slices an EPSG:3857 GeoTIFF into `Saved Games/Retribution/MapTiles/<name>/{z}/{x}/{y}.png`
    + a `tileset.json` sidecar; game-independent `/map-tiles` routes list/serve whatever exists there
    (traversal-safe name/int params); `MapLayersControl` fetches the list once and adds one segmented
    base-map button per set (`local:<name>`, persisted like the stock choices, Clarity fallback when tiles
    vanish). No Settings toggle — on-disk content is the switch. (`tools/tile_geotiff.py`,
    `game/persistency.py` `map_tiles_dir`, `game/server/maptiles/`,
    `client/src/components/maplayers/MapLayersControl.tsx`; features doc §42, checklist O1 — needs an
    in-app pass + the CI client rebuild.)

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
  - [#851](https://github.com/dcs-retribution/dcs-retribution/pull/851) High Digit SAMs **Ultimate Compilation** support (§41's generic core) — retargets the HDS toggle to the maintained mod: renamed-radar re-points, retired-unit tombstones, the 42 new units + 7 presets + SAMP/T layout, and the `remove_vehicle` id-vs-name strip fix. NO 414th faction enrichment (P-37/SA-7/S-400 wiring stays fork-side). Validated headless against upstream dev — opened 2026-07-01. Landed on the fork as [414Ret#382](https://github.com/bradyccox/414Ret/pull/382).
  - [#847](https://github.com/dcs-retribution/dcs-retribution/pull/847) F-4E-45MC (Heatblur) loadout rebuild **+** Maverick date-fallback fix — all 13 F-4E presets re-sourced from the module's built-in loadouts (period AIM-7E2/9L A2A baseline vs the old all-modern AIM-7M), **and** the AGM-65 family's date-fallback rerouted AGM-62 Walleye → Mk-20 Rockeye (Mavericks were degrading to Walleyes on pre-1972 campaigns). Data-only (2 files), validated headless against upstream (CLSID-resolve + station-legal + task-resolution + weapon-DB load) — opened 2026-06-28; **consolidates the former #845 + #846**. Landed on the fork as [414Ret#322](https://github.com/bradyccox/414Ret/pull/322) + [#325](https://github.com/bradyccox/414Ret/pull/325).
  - [#843](https://github.com/dcs-retribution/dcs-retribution/pull/843) era-gate payload-editor options: JHMCS property gating (§24) + targeting-pod era data (re-does withdrawn #786) (carve queue item 11) — opened 2026-06-27. **Druss99 CHANGES_REQUESTED addressed 2026-06-29**: helmet-cueing dates moved to `resources/aircraftproperties/helmets/*.yaml` (mirroring the weapons era model, per his ask) + extended to Soviet HMS/SURA Visor & A-10C HMCS; CI green. ⚠️ **Owes a reviewer re-request** — Druss99 is NOT in the re-request list, so the PR sits blocked with no signal for him to re-review.
  - [#842](https://github.com/dcs-retribution/dcs-retribution/pull/842) landmap prepared-index perf (carve queue item 1) — opened 2026-06-27.
  - [#841](https://github.com/dcs-retribution/dcs-retribution/pull/841) plugin `descriptionInUI` field (§14, carve queue item 10) — opened 2026-06-27.
  - [#828](https://github.com/dcs-retribution/dcs-retribution/pull/828) recon fog-of-war (§3) — the flagship carve, mergeable.
  - [#806](https://github.com/dcs-retribution/dcs-retribution/pull/806) configurable cruise/patrol altitude.
  - [#805](https://github.com/dcs-retribution/dcs-retribution/pull/805) bulk waypoint altitude UI — Druss99's CHANGES_REQUESTED **addressed** (verified 2026-06-29): `DIVERT`/`TARGET_POINT` + `REFUEL`/`RECOVERY_TANKER` (and target-group/ship, pickup/dropoff, cargo-stop, bullseye) now in the `BULK_ALTITUDE_SKIP_TYPES` skip-list. Druss99 **re-requested** — awaiting his re-review; no further action owed.
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
