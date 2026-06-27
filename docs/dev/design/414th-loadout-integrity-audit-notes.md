# 414th loadout/task/date integrity audit + fixes

Status: **passes 1 + 2 landed** (2026-06-27). Systemic root-cause fixes, the verifiable
data repairs, and the F-14A / Tornado preset fixes are in; the remaining residuals are
mod-weapon stragglers and low-impact early-date noise (tracked below).

## Why this exists

Loadouts had been "screwed up for a while" — the classic symptom was a jet fragged for a
ground/SEAD role that took off carrying only air-to-air missiles (e.g. an F-15E on DEAD with
Sidewinders/AMRAAMs and no A2G). A fleet-wide audit (every aircraft × every assigned
ground-attack/SEAD task × campaign years 1972→2024, resolving the real
`Loadout.default_for_task_and_aircraft` + `degrade_for_date`) traced it to **two distinct
failure modes**, plus one resolver gap.

## Root causes & fixes

1. **Stray empty pylons nuked whole presets (systemic).** 244 presets across 44 airframes
   carry a station with `["CLSID"] = ""` (or the `<CLEAN>` sentinel). `Loadout.valid_payload`
   ran `Weapon.with_clsid("") is None → return False`, discarding the *entire* preset; the
   planner then flew a fallback (often clean A2A) or nothing. Empty stations are valid empty
   pylons — they already drop out when the `Loadout` is built (None pylons are filtered in
   `__init__`). **Fix:** `valid_payload` skips `""`/`<CLEAN>` instead of failing
   (`game/ato/loadouts.py`). Upstream's `valid_payload` is byte-identical, so this is a
   genuine improvement worth upstreaming. Cleared the Tornado IDS/GR4, Mosquito, and many
   other presets in one change.

2. **Dead CLSIDs in presets.** A non-empty but stale weapon id (renamed/removed by a DCS or
   mod update) also makes `valid_payload` reject the preset. Coverage of `resources/weapons`
   is otherwise complete (the audit found **0** valid-pydcs-but-uncovered CLSIDs — #826 did
   its job). Verifiable repairs landed:
   - **AJS-37 ANTISHIP:** `{Rb15}` → `{Rb15AI}` (RB-15F, covered in `RB-15F.yaml`).
   - **F/A-18E / F/A-18F Retribution DEAD + OCA/Aircraft:** the mod renamed the STA-02 JSOW
     rack `…_2X_BRU55_AGM-154C` → `…_2X_BRU_AGM-154C`; the preset still pointed at the dead
     `BRU55` form while `AGM-154C.yaml` already covers the live `BRU` one. Swapped.

3. **Anti-ship had no loadout fallback (resolver gap).** Every other A2G task falls back
   (BAI→CAS, DEAD→BAI, OCA/Runway→Strike), but `ANTISHIP` resolved only its own preset, so a
   jet tasked anti-ship without an anti-ship preset got an EMPTY loadout. **Fix:** added
   `ANTISHIP.extend(STRIKE)` in `default_loadout_names_for` — its own preset is still
   preferred first, then iron bombs on shipping instead of nothing.

## Regression guard

`tests/data/test_weapons.py`:
- `test_valid_payload_ignores_empty_stations` — empty/`<CLEAN>` tolerated; a real dead id
  still invalidates.
- `test_antiship_falls_back_to_strike_loadout_names` — anti-ship prefers its own preset, then
  the Strike family.
- `test_customized_payload_clsids_resolve_or_are_known_stragglers` — **the durable guard**:
  every CLSID in `resources/customized_payloads` either is an empty marker, resolves via
  `Weapon.with_clsid`, or is in the documented `_KNOWN_MOD_STRAGGLER_CLSIDS` allowlist. Any
  *new* dead CLSID fails the build loudly (this is the bug that previously rotted silently).

## Pass 2 fixes (2026-06-27)

- **F-14A "Block 135 Early": one-line `unitType` bug.** `F-14A-135-GR-Early.lua` already
  carried every ground preset, but its `["unitType"]` said `"F-14A-135-GR"` (the *Late*
  variant's dcs id, a copy-paste error), so the loader never applied them to the Early jet
  (dcs id `F-14A-135-GR-Early`). Fixed the `unitType`. The Early *can* mount LANTIRN, so its
  LGB presets resolve intact.
- **F-14A "Block 95 Export": no payload file at all.** Created `F-14A-95-GR.lua` (dcs id
  `F-14A-95-GR`) with **iron-bomb** ground presets (CAS/Strike = Mk-82, BAI/DEAD = Mk-20,
  OCA = Mk-82) — the Iranian F-14A had no LANTIRN/PGM, so no LGBs.
- **Tornado IDS STRIKE: LGBs without a TGP.** The empty-pylon fix made the preset resolve,
  exposing GBU-16 LGBs with no targeting pod (no Tornado TGP exists in base pydcs), so
  `replace_lgbs_if_no_tgp` stripped them. Switched STRIKE to 6× Mk-82 iron (matching its
  working CAS preset). Verified all three resolve to real A2G at 2010.

## Tracked residuals (low priority — NOT fixed)

- **Mod-weapon dead CLSIDs (allowlisted).** ~26 ids on mod airframes (SA342 Gazelle, Su-57,
  Mirage F1, the F-22A pack, Rafale, Super Étendard, UH-60L, OH-6A) reference weapons absent
  from base pydcs *and* `pydcs_extensions`. They degrade via the fallback chain (not fatal)
  and can't be resolved without the mod. Listed in `_KNOWN_MOD_STRAGGLER_CLSIDS`. Fix = install
  the mod's current ids or strip those weapons from the affected presets (a per-preset call).
- **Early-date A2A-only degrade — mostly noise.** The audit flagged ~47 (aircraft, task) pairs
  resolving A2A-only, but the bulk are **not real**: anachronistic test dates (MQ-9/Predator
  drones and the F-16A tested "in 1972", before they existed — the intro-year filter
  under-excludes when `year_introduced` is non-numeric) plus `[CH]` CurrentHill mod aircraft.
  The genuine remainder is a handful of Cold-War bombers/interceptors (Tu-16, H-6J, F-104)
  whose sole A2G is a date-gated weapon at a pre-~1995 date. Low impact unless flying early-era;
  no clean root-weapon cluster, so deferred rather than a 47-preset churn.

## Re-running the audit

The audit/scan scripts are not committed (one-shot tooling). To regenerate: load all aircraft
headless (`persistency.setup` + `qt_ui.main._patch_pydcs_payload_loader()` +
`PayloadDirectories.set_fallback("resources/customized_payloads")`), then for each
`AircraftType.iter_all()` × its `task_priorities`, resolve
`Loadout.default_for_task_and_aircraft` + `degrade_for_date(..., faction=None)` across a span
of dates and classify the resulting pylons by the `resources/weapons` folder taxonomy
(`a2a-missiles` = A2A; `bombs`/`rockets`/`standoff` = A2G; `type: ARM` = anti-radiation;
`pods` = support). Note: iterating `AircraftType.iter_all()` misses some mod airframes whose
payloads exist only as `.lua` files — the file-reading test guard above is the complete check.
