# Upstream DCS Retribution Rules (distilled from the official wiki)

Source: https://github.com/dcs-retribution/dcs-retribution/wiki (Developer's Guide, Contributing, Adding Lua Plugins). Wiki last verified: August 2026. The repo code is the final authority if the wiki is stale.

> **This file describes UPSTREAM.** The 414Ret fork adopted these as its own standards
> (2026-07-20), with the deltas flagged inline below as **414th:**. Where a delta exists, the
> fork's value governs fork work and upstream's value governs anything carved back.

## Project identity

| Fact | Detail |
|---|---|
| What it is | External DCS mission generator: turn-based dynamic campaign, generates `retribution_nextturn.miz` each turn, captures mission state afterward |
| Tech stack | Python 3.10+, Qt6 (PySide6) UI, pyDCS for mission generation, web frontend built with npm — **414th: pinned to Python 3.11** |
| Lineage | 2022 fork of DCS Liberation (which forked from shdwp's 2018 original) |
| Building blocks | Campaigns (templates) + Factions (unit availability) + Squadrons/pilots |

## Branches (plain English)

A branch is a named line of work inside a repository — like a separate saved-game slot for code.

- **`dev`** — the one integration branch. Default on a fresh clone. May be unstable. **All PRs target `dev`.**
- New work: cut a new branch from `dev`, do the work there, PR it back to `dev`.
- Never PR against `main`.

## Pull Request rules

1. Branch from `dev`, PR to `dcs-retribution/dev`.
2. **One PR per feature/bugfix/change.** Maintainers can only merge or revert whole PRs, and testers can't isolate bugs below the PR level.
3. **Small is fast.** Review latency grows faster than PR size — smaller PRs get reviewed sooner.
4. **Changelog**: add a note to `changelog.md` (project root, upcoming-release section) for anything user-visible. Skip for refactors and for bugs that never shipped in a release build.
5. Campaigns can be contributed without code — via the Discord "campaigns" channel or as a PR.

## Dev environment setup (Windows)

```
git clone https://github.com/<username>/dcs-retribution.git
cd dcs-retribution
python -m venv ./venv
.\venv\Scripts\Activate.ps1        # PowerShell (git-bash: source venv/Scripts/activate)
python -m pip install -r requirements.txt
pre-commit install
```

Activate the venv **before** installing, or dependencies land in system Python. The venv folder name `venv` matches CI. Re-activate in every new terminal.

Frontend (needed to see the map):
```
cd client
npm install        # first time only
npm run build      # every time the repo is updated
```

Run from source: `PYTHONPATH=. python ./qt_ui/main.py`

Useful flags/subcommands on `qt_ui/main.py`: `--dev`, `new-game` (headless generation with `--blue`, `--red`, `--date`, `--advanced-iads` etc.), `lint-weapons <aircraft>`, `dump-task-priorities`.

## Quality gates

| Tool | What | When |
|---|---|---|
| black | Auto-formatter | Runs automatically on commit via pre-commit hook |
| mypy | Type checker: `mypy game` and `mypy tests` | Required CI gate on PRs. Run before uploading a PR; mandatory before push to `dev`. Not part of pre-commit (to allow WIP commits) |

**414th:** CI black checks the **whole tree** (`.`), CI mypy only `game tests` — so a `qt_ui`
type error passes and a formatting miss anywhere fails. The fork adds a **blocking Lua syntax
gate** (`luac5.1 -p` over `resources/plugins/**/*.lua`) plus a headless Lua runtime harness
(`tests/lua/`) inside normal pytest, and runs pytest over three out-of-tree dirs under `game/`.

All new code gets type annotations. Annotate any function you touch. `qt_ui` is exempt from checking (PySide6 patterns break mypy) but annotate anyway for readers.

Consider contributing aircraft/unit data fixes to pyDCS (github.com/pydcs/dcs) — upstream considers that indirect contribution.

## Lua plugin system

Plugins inject Lua scripts into generated missions. This is the sanctioned way to add mission-runtime Lua — **not** freestanding scripts.

- Plugins live in `resources/plugins/<plugin-folder>/`, one folder each.
- `resources/plugins/plugins.json` lists which plugins load, in order. The folder name is the plugin's identifier in settings.
- Each plugin folder has a `plugin.json` describing it. Study the bundled *base* plugin as the canonical example. Easiest custom plugin: copy an existing one and modify.

`plugin.json` fields:

| Field | Meaning |
|---|---|
| `skipUI` | true = hidden from the plugin selection UI (forces a plugin on/off, like *base*) |
| `nameInUI` / `descriptionInUI` | Title and help text in the plugin settings UI |
| `defaultValue` | Selected by default on install |
| `otherResourceFiles` | Extra files (e.g. .ogg/.wav audio) bundled into the .miz alongside the scripts |
| `specificOptions` | Per-plugin options: each has `nameInUI`, `mnemonic` (the Lua variable name and settings key), `defaultValue`, and for numerics `minimumValue`/`maximumValue` (defaults 0/10000) |
| `scriptsWorkOrders` | Which Lua files to load: `file`, `mnemonic` (dedupe/disable key), `disable` |
| `configurationWorkOrders` | Same shape, for configuration Lua scripts |

## Contribution etiquette

- Search existing GitHub issues (including closed ones) before filing a bug.
- Bugs can also go to the Discord #bugs channel.
- Code of Conduct applies to all project interactions.
