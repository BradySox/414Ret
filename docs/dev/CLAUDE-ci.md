## CI & Release Pipeline

Every push to `main` runs these workflows:

1. **`lint.yml`** — Black (`--check .` whole tree) + mypy (`game tests` only).
2. **`test.yml`** — pytest over `tests` **plus the three out-of-tree test dirs under
   `game/`** (`game/missiongenerator/tests`, `game/missiongenerator/kneeboard_recon/tests`,
   `game/plugins/tests`) — added 2026-07-10; before that those ~245 tests never ran in CI.
   Both test jobs upload coverage to **Codecov**
   (https://app.codecov.io/gh/BradySox/414Ret) via `codecov/codecov-action@v5` with
   **OIDC** (`use_oidc` — no `CODECOV_TOKEN` secret; requires the Codecov GitHub App
   installed on the repo, and the *calling* workflow's job to grant
   `id-token: write` — `build.yml` + `414th-latest.yml` both do). The inherited
   `codecov.yaml` keeps both statuses `informational`, so coverage never blocks a PR
   or the rolling release; an upload failure is also non-fatal by default — check the
   step log, not just the green check (the fork's uploads 404'd silently
   "Repository not found" from fork day one until 2026-07-20, when the repo was
   activated on codecov.io and the upload switched from deprecated tokenless
   `@v3` to `@v5` + OIDC). Upstream PRs need none of this — carve PRs get coverage
   comments from upstream's own Codecov registration automatically.
3. **`lua-lint.yml`** — Lua syntax gate (blocking): `luac5.1 -p` over every
   `resources/plugins/**/*.lua`. Advisory luacheck (scoped to 414th-authored scripts via
   `.luacheckrc`) runs continue-on-error and reports counts to Step Summary. Decoupled from
   `414th-latest.yml` so it can never block the rolling release.
4. **`414th-latest.yml`** (needs lint + test) — PyInstaller build on `windows-latest`, then
   upserts a rolling pre-release tagged `latest`.

The release asset `414th-retribution-latest.zip` (`retribution_main.exe`) is what the
squadron downloads; it always reflects current `main`. The permanent download URL is
https://github.com/bradyccox/414Ret/releases/tag/latest. A separate `release.yml` (from
upstream) triggers on semver tags (`v1.0.0`) for pinned campaign builds and does NOT affect
`latest`. Build/SHA are stamped into `resources/buildnumber` + `resources/gitsha` at build
time (not in the repo).

### Local Verification (before every push)

```powershell
.venv\Scripts\python.exe -m black --check .      # 0 files to reformat
.venv\Scripts\python.exe -m mypy game tests       # 0 new errors
.venv\Scripts\python.exe -m pytest tests game/missiongenerator/tests game/missiongenerator/kneeboard_recon/tests game/plugins/tests -q  # all green
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
- The Lua plugins CAN now be exercised headlessly: `tests/lua/` runs the real plugin
  scripts on Lua 5.1 via `lupa` against a faked DCS sandbox (`dcs_stubs.lua`), inside the
  normal pytest run — see `docs/dev/design/414th-lua-plugin-harness-notes.md` for scope and
  how to extend it. The `lua-lint.yml` syntax gate still catches parse-time errors; the
  harness catches "script errors at runtime and the feature silently never starts"; actual
  DCS behavior (AI, physics, feel) still needs an in-game pass. See
  `docs/dev/414th-ingame-pass-checklist.md` for the tracker. When touching a plugin that
  has harness coverage (currently `vietnamops`), run/extend its tests.
