# Pretense removal runbook

**Goal:** rip every tie to the upstream **Pretense** campaign generator out of the 414th
fork. Pretense is an upstream Retribution feature the 414th does not ship.

**This is a recurring runbook, not a one-shot.** Pretense is actively developed upstream,
so every future merge from `dcs-retribution/dev` reintroduces the files and re-conflicts
the shared hotspots (`settings.py`, `flighttype.py`, `QLiberationWindow.py`). Re-run this
list after each upstream pull lands on `main`.

**Sequencing (important):** always do the removal **after** an upstream-sync lands, never
before — removing first turns the sync merge into delete-vs-modify conflicts on every
Pretense file. Land the sync, branch from the synced `main`, then work this list (or
cherry-pick the prior removal commit and resolve the `settings.py`/`flighttype.py`
overlaps).

First executed against `main` @ `56434b2ed`; re-applied onto the 20-PR upstream backport
(#69) @ `9d3a5a50a`. Expect the inventory below to **grow** with whatever upstream adds —
re-grep before assuming it's complete.

---

## 0. Re-scope first

```
rg -il pretense
```

Confirm the file list matches (or supersedes) the inventory below. New `pretense_*`
settings, new generator files, or new menu wiring may have appeared in the sync.

## 1. Delete dedicated files/dirs (`git rm -r`)

- [ ] `game/pretense/` — whole package (mission/lua/tgo/aircraft/trigger/flightgroup
      generators; was 7 files)
- [ ] `resources/plugins/pretense/` — whole dir (compiled + `init_*.lua`; was 7 files)
- [ ] `game/ato/flightplans/pretensecargo.py` — the `PRETENSE_CARGO` flight plan
- [ ] `tests/test_pretense_transaction.py`
- [ ] `resources/campaigns/persian_gulf_full.yaml`
- [ ] `resources/campaigns/nevada_full.yaml`
- [ ] `resources/campaigns/marianas_full.yaml`
- [ ] `resources/campaigns/afghanistan_full.yaml`
      *(the 4 `*_full.yaml` are the Pretense-tuned full-map campaigns; squadron decision
      was to delete, not de-pretense. Re-confirm none became a default campaign in the
      sync.)*
- [ ] `resources/ui/misc/pretense.png`
- [ ] `resources/ui/misc/pretense_discord.png`
- [ ] `resources/ui/misc/pretense_generate.png`

## 2. Edit integration points

- [ ] **`game/game.py`** — remove the `pretense_ground_supply`, `pretense_ground_assault`,
      `pretense_air`, `pretense_air_groups`, `pretense_carrier_zones` attributes set in
      `__init__`/init (was the block just before `self.on_load(...)`).
- [ ] **`game/persistency.py`** — remove `pre_pretense_backups_dir()`.
- [ ] **`game/ato/flighttype.py`** — remove the `PRETENSE_CARGO = "Cargo Transport"` enum
      member and its `AirEntity.UTILITY` mapping. **Add a `_missing_` migration** so stray
      persisted values survive:
      ```python
      if value == "Cargo Transport":
          return cls.TRANSPORT
      ```
      (The pickle path in `persistency._handle_flight_type` falls through to
      `FlightType(value)`, so `_missing_` covers it — no separate edit there.)
- [ ] **`game/ato/flightplans/flightplanbuildertypes.py`** — remove the
      `from .pretensecargo import PretenseCargoFlightPlan` import and the
      `FlightType.PRETENSE_CARGO: PretenseCargoFlightPlan.builder_type()` map entry.
- [ ] **`game/settings/settings.py`** —
  - remove the `PRETENSE_PAGE = "Pretense"` constant;
  - delete the whole block of `pretense_*` settings (was ~11: `maxdistfromfront_distance`,
    `controllable_carrier`, `carrier_steams_into_wind`, `carrier_zones_navmesh`,
    `extra_zone_connections`, `sead/cas/bai/strike/barcap_flights_per_cp`,
    `ai_aircraft_per_flight`, `player_flights_per_type`, `ai_cargo_planes_per_side`);
  - add every removed key name to the obsolete-key drop list in the settings migration
    (alongside the already-present `pretense_num_of_cargo_planes`) so old saves load clean.
- [ ] **`qt_ui/windows/QLiberationWindow.py`** — remove `pretenseLinkAction`,
      `newPretenseAction`, their `links_bar.addAction(...)` calls, the `newPretenseCampaign`
      method, and the imports `from game.persistency import pre_pretense_backups_dir` and
      `from game.pretense.pretensemissiongenerator import PretenseMissionGenerator`. Drop
      the now-unused `from datetime import datetime` if nothing else uses it.
- [ ] **`qt_ui/uiconstants.py`** — remove the `ICONS["Pretense"]`, `["Pretense_discord"]`,
      `["Pretense_generate"]` entries.
- [ ] **`.gitignore`** — remove `/resources/plugins/pretense/pretense_output.lua`.

## 3. Docs

- [ ] **`changelog.md`** — add a `**[414th]**` removal entry. Leave historical Pretense
      lines intact.
- [ ] **`docs/dev/414th-features.md`** — drop the two file-path references to
      `game/pretense/...` (C-130 loadout wiring list; F10-mark-suppression list).
- [ ] **`docs/dev/settings-qol-audit.md`** — remove the `### Pretense` settings-page
      section. Leave the historical `pretense_num_of_cargo_planes` table row.
- [ ] **Keep this runbook** — it is the recipe for the next upstream pull. Update the
      "first executed / re-applied against" line with each new base commit.

## 4. Validate (from repo root, against the synced tree)

```powershell
.venv\Scripts\python.exe -m black --check .      # 0 files to reformat
.venv\Scripts\python.exe -m mypy game tests       # 0 new errors
.venv\Scripts\python.exe -m pytest tests -q       # all green
```

Then a final `rg -il pretense` — the only survivors should be intentional: the migration
key names in `settings.py`, the `_missing_` comment/branch in `flighttype.py`, the
migration test `tests/settings/test_settings_qol_migration.py`, and the historical
changelog/doc lines.

## 5. Watch in-game (not CI-runnable)

- Confirm the toolbar no longer shows the Pretense link / "Generate a Pretense Campaign"
  buttons and the app launches.
- Load a pre-removal `.retribution` save and confirm it migrates without error (dropped
  settings, no `PRETENSE_CARGO` flights).

---

**Fork-drift note:** this is a deliberate fork-only divergence from upstream. Every future
merge from `dcs-retribution/dev` will reintroduce Pretense files and re-conflict the shared
hotspots — re-run this checklist on each upstream pull.
