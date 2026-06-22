# 414Ret — Claude Code Guide

The **414th Joint Fighter Group's fork of DCS Retribution** — a turn-based dynamic
campaign generator for DCS World, plus the 414th's air-defense, electronic-warfare,
recon, frontline, and assets-pack features on top of upstream.

- Base: upstream `dcs-retribution/dcs-retribution` `dev` @ `dce851ea`.
- GitHub (this fork): https://github.com/bradyccox/414Ret
- Read this before touching anything. The human-friendly overview is [`README.md`](README.md).

---

## Project Docs

The per-feature engineering internals and design rationale live in `docs/`, not in this
file. This guide is the map; those are the territory.

- [docs/dev/414th-features.md](docs/dev/414th-features.md) — **the deep dive**: every 414th
  feature with file paths, gotchas, tests, and deferred work. Read the relevant section
  before editing a feature.
- [docs/dev/design/](docs/dev/design/) — per-feature design notes (read before touching the
  matching code):
  - `414th-air-defense-planning-notes.md` — CAP/BARCAP/QRA planning intent
  - `414th-tic-dynamic-fronts-notes.md` — TIC stance/cadence movement design
  - `414th-tars-recon-notes.md` — TARS recon engine
  - `414th-flightcontrol-notes.md` — Flight Control ATC
  - `414th-dtc-export-notes.md` — DTC cartridge format + reverse-engineered schema
  - `414th-scar-task-spec.md` + `414th-scar-commander-sme-questions.md` — SCAR ground truth
  - `414th-scar-phase2-sof-plan.md` + `414th-scar-HANDOFF.md` — SCAR commander-capture plan + next-session pickup
  - `414th-aircraft-task-rebalance-rubric.md` — aircraft task-priority rebalance rubric
  - `414th-red-tide-campaign-notes.md` — Red Tide campaign laydown + `.miz`/faction edits
- [README.upstream.md](README.upstream.md) — unmodified upstream project README (setup,
  dependencies, wiki links).
- `AGENTS.md` is a **byte-identical mirror of this file** (CLAUDE.md is the authoritative
  source; only line 1, the title, differs). After editing CLAUDE.md, resync it —
  `cp CLAUDE.md AGENTS.md` then Edit line 1 back to the `# AGENTS.md ...` title (do NOT use
  `sed -i`; it flattens CRLF and shows the whole file as changed).

---

## Tech Stack

| Layer | Choice |
|---|---|
| Campaign engine | Python 3.11 (`game/`) |
| UI | PyQt (`qt_ui/`) — NOT type-checked in CI, but Black-checked |
| Mission scripting | **Lua 5.1** sandbox plugins (`resources/plugins/`) — no `os`/`io`, no `goto`, definition order matters |
| In-mission framework | MOOSE (bundled `Moose.lua`; some plugins vendor classes verbatim) |
| Units / mission format | pydcs; CurrentHill mod packs in `pydcs_extensions/` |
| CI gates | Black (`--check .` whole tree) + mypy (`game tests` only) + pytest |
| Release | PyInstaller → rolling `latest` pre-release on GitHub |

---

## Key Architecture Patterns

**Planner / Lua split.** Python plans and spawns the mission (flight plans, ROE, templates);
runtime behavior (EW, ISR, recon scoring, frontline firefights, ATC) is driven by the Lua
plugins. When a feature has both, the Python side sets up and the Lua side executes — don't
move runtime logic into the planner or vice versa.

**Plugin script injection (the "scramble pattern").** Most 414th plugins are normal work-order
plugins, but TIC, TARS, Flight Control, and SCAR are injected by hand in
`game/missiongenerator/luagenerator.py` (`_inject_*_script()`), appended **after**
`inject_plugins()` so `dcsRetribution.plugins.<name>` already exists, then `DoScriptFile`
the vendored class + a `*_414_init.lua` that owns construction. If the init file is removed
or errors, that feature silently never starts.

**Viewer-aware visibility layer (recon fog).** One layer drives two player-facing fog rules.
AI planning and threat math always use ground truth (`viewer=None`); only the human (BLUE)
map/UI are fogged. `TheaterUnit.alive_for(viewer)` handles BDA damage lag;
`TheaterGroundObject.known_for(viewer)` handles recon intel-fog; `hidden_on_player_map(viewer)`
fully hides enemy command posts for the SCAR commander-capture feature (gated by
`scar_command_post_intel`, now default ON for new campaigns; §15). Every
accessor takes `viewer: Optional[Player] = None` defaulting to truth; consumers gate at the edge.
Do **not** reintroduce the old `_for_player`/`_for` method twins — that collapse is finished.
(`game/theater/theatergroup.py`, `theatergroundobject.py`; see features doc §3.)

**Save migration.** Removed/renamed enums migrate old pickles in `FlightType._missing_`
(runtime) and `persistency.py` `_handle_flight_type` (unpickler); fog state migrates in
`__setstate__`. When you remove or rename a persisted field, add the migration in both
places so existing campaigns don't brick.

**Lua plugin discipline.** Lua 5.1 only, vanilla DCS units only (no HighDigitSAMs etc.),
define functions before first use.

---

## Features at a Glance

Full internals for each are in [docs/dev/414th-features.md](docs/dev/414th-features.md)
(section numbers below).

1. **QRA intercept reserve** — per-squadron alert reserve feeding the upstream PR #782 Moose
   `AI_A2A_DISPATCHER`. Base-defense posture by default. (Old ramp-scramble is retired.)
2. **JAMMING flight type** — C-130J as EC-130H/RC-130H EW+ISR platform (`c130j` plugin).
3. **TARPS recon + BDA fog-of-war** — player F-14 photo recon; viewer-aware fog (damage lag +
   recon intel-fog) makes recon worth flying.
4. **UI transparency** — Target Intel panel, Mission Impact debrief summary, package context
   bar, flight-creation context, building-card cleanup.
5. **Player target location precision** — `Approximate` mode offsets steerpoints + hides exact
   marks/coords so players must visually acquire.
6. **Air-defense planning rework** — overlapping/jittered BARCAP waves, forward CAP line,
   threat-weighted BARCAP volume, front-line navmesh routing hazard, unstacked FLOT units.
7. **Auto-hide mobile SAMs on MFD** — SHORAD/AAA/MANPAD hidden from datalink, including
   escorts inside armor/missile groups; standalone MERAD/LORAD stay visible for SEAD.
8. **Robustness / crash fixes** — flight-exit IndexError, AWACS/tanker orbit, malformed mod
   payload Lua.
9. **TIC — Troops In Contact** — scripted frontline firefights with per-stance movement +
   414th ambient-fire extension (plugin, default ON).
10. **CurrentHill Iran assets pack** — Shahed-136, IRGCN FAC, `[CH] Iran 2020` faction.
11. **Native DCS DTC cartridge export** — F/A-18C SA picture pre-built (default OFF).
12. **TARS recon engine** — MOOSE Ops.TARS runtime for TARPS, feeds confirmed BDA (default ON).
13. **Flight Control ATC** — MOOSE FLIGHTCONTROL players-only tower comms (default ON).
14. **Plugin Options UI** — `descriptionInUI` field + label/default polish across all plugins.
15. **SCAR** — player-flown Strike Coordination and Reconnaissance against a moving HVT
    (flight type + scenario `scar` plugin, default ON), plus a commander-capture path using
    finite purchased SOF inventory + a downed-team CSAR recovery loop (gated by
    `scar_command_post_intel`, now default ON for new campaigns while it is playtested).
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

---

## Repo & Branch Layout

- This repo (`bradyccox/414Ret`) `main` = the consolidated, most-up-to-date 414th build.
- Upstream is `dcs-retribution/dcs-retribution`; the 414th's PR fork is
  `bradyccox/dcs-retribution`. Open upstream PRs carved out of this work:
  - **#784** `codex/currenthill-iran-pack` — the Iran pack (branch also carries the full
    feature stack).
  - **#786** `codex/fix-aaq33-era-restriction` — targeting-pod era-restriction fix (separate,
    small; NOT part of the feature stack on `main`).
- The 414th's primary "all features" working branch in the dev checkout is
  `414th-all-features`; `main` here = that + the Iran pack + a Black/mypy lint pass.

---

## Local Verification (before every push)

```powershell
.venv\Scripts\python.exe -m black --check .      # 0 files to reformat
.venv\Scripts\python.exe -m mypy game tests       # 0 new errors
.venv\Scripts\python.exe -m pytest tests -q       # all green
```

Notes learned the hard way:
- CI Black checks the **whole tree** (`.`), including `qt_ui` and `tests`. CI mypy only
  checks `game` and `tests`. A type error in `qt_ui` passes CI; a formatting miss anywhere
  fails it.
- `qt_ui/main.py` has ~5 PRE-EXISTING mypy errors that also exist on upstream `dev`. Don't
  "fix" those — they're not in the CI mypy path and aren't ours.
- For test files that fake Retribution objects (duck-typed `Coalition`, `Faction`,
  `AircraftType`), prefer a narrow `# type: ignore[arg-type]` over restructuring, matching
  how the existing fakes are annotated.
- The Lua plugins can't be run/compiled here — validation is careful reading. When changing
  plugin behavior, tell the user what to watch for in-game; several features explicitly note
  "Lua still needs an in-game pass (not CI-runnable)."

---

## CI & Release Pipeline

Every push to `main` runs three workflows in sequence:

1. **`lint.yml`** — Black (`--check .` whole tree) + mypy (`game tests` only).
2. **`test.yml`** — pytest.
3. **`414th-latest.yml`** (needs lint + test) — PyInstaller build on `windows-latest`, then
   upserts a rolling pre-release tagged `latest`.

The release asset `414th-retribution-latest.zip` (`retribution_main.exe`) is what the
squadron downloads; it always reflects current `main`. The permanent download URL is
https://github.com/bradyccox/414Ret/releases/tag/latest. A separate `release.yml` (from
upstream) triggers on semver tags (`v1.0.0`) for pinned campaign builds and does NOT affect
`latest`. Build/SHA are stamped into `resources/buildnumber` + `resources/gitsha` at build
time (not in the repo).

**PINNED — do not touch:**
- Do NOT delete or manually push the `latest` git tag — it's owned by
  `softprops/action-gh-release@v2` inside `414th-latest.yml`. Breaking it breaks the URL the
  squadron bookmarks.
- Do NOT modify `.github/workflows/414th-latest.yml` without understanding it's the sole
  rolling-release mechanism. Test in a branch and verify the `latest` release after merging.
- Do NOT add Discord webhook or other org-level secrets — those are upstream-only. The
  workflow uses only `GITHUB_TOKEN`.

---

## PINNED — do not modify

**Local Python runtime:** before deleting anything under `tmp/`, inspect
`.venv/pyvenv.cfg`. The current Windows virtual environment may have
`home = ...\tmp\uv-python\cpython-3.11.15-windows-x86_64-none`; when it does,
that `tmp/uv-python` directory is the base interpreter for `.venv`, **not a disposable
cache**. Deleting it breaks `run_retribution.bat` with “No Python at ...”. Either preserve
the directory or rebuild `.venv` against a permanent Python 3.11 installation first.
Cleanup scripts and agents must never recursively delete `tmp/` without this check.

**`resources/plugins/splashdamage3/Splash_Damage_3.4.2_414th.lua`** is the 414th's
**buddy-tuned** Splash Damage build (softened weapon table, `overall_scaling=0.6`,
`rocket_multiplier=0.8`, `static_damage_boost=1`, shaped-charge rocket flags,
`game_messages=true`). Do NOT overwrite it from upstream stevey/source — the 414th prefers
this version. If you must update it, diff against the tuned build and preserve these values.
- Settings are LOCKED by design (Tyler's call): `plugin.json` has no `specificOptions` and
  `sd3-config.lua` was removed, so the baked-in values always apply and nothing in the app UI
  can override them. Don't reintroduce the config layer.
- Merge note (2026-06-12): `main` and the splash-script branch pinned byte-identical builds
  independently; the only delta was `game_messages` (resolved to `true` — flip the single
  line if the squadron prefers silence).

---

## Conventions

- Match the surrounding code's style; run the three validation commands above before pushing.
- Keep the doc faces in sync: when a feature lands or changes, update **both**
  [`README.md`](README.md) (player-facing) and the relevant section of
  [docs/dev/414th-features.md](docs/dev/414th-features.md) (engineering), plus this map if the
  shape changed. A push that moves the code past its docs is a broken push.
- Keep player-facing plugin behavior and any overview docs in sync with code changes.
