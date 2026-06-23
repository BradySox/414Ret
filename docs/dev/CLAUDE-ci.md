## CI & Release Pipeline

Every push to `main` runs these workflows:

1. **`lint.yml`** — Black (`--check .` whole tree) + mypy (`game tests` only).
2. **`test.yml`** — pytest.
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
- The Lua plugins can't be run/compiled here — validation is careful reading. The
  `lua-lint.yml` syntax gate catches parse-time errors; runtime behavior still needs an
  in-game pass. See `docs/dev/414th-ingame-pass-checklist.md` for the tracker.
