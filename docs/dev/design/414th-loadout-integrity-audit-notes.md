# 414th loadout/task/date integrity audit + fixes

Status: **passes 1 + 2 landed** (2026-06-27); **upstream-baseline reset + preset-name guard
landed** (2026-07-06, see that section below). Systemic root-cause fixes, the verifiable
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

## 2026-07-06 — upstream-baseline reset + preset-name guard

Follow-up prompted by "our preset loadouts are fucked up for every aircraft — reset them to
upstream Retribution's standard, and make sure we don't go backwards." Investigation +
scoped reset. **The premise was mostly wrong**, and writing that down is half the point of
this section.

### Why "every aircraft looks broken" was a false alarm

A fresh diff of `resources/customized_payloads/` against upstream `dev` shows ~90 files
changed, which *reads* like fleet-wide breakage. It is not. The divergence is three things,
in order of file count:

1. **Cosmetic preset-name fixes (~54 files, the bulk).** The loader matches a flight's
   `FlightType` to a preset by **exact name** (`Loadout.default_loadout_names_for` →
   `"Retribution {value}"` / `"Liberation {value}"` + legacy aliases). The 2026-06
   name-standardization pass (`1aafeb8de`) lower-cased/renamed ~58 presets to match. **Upstream
   still ships the un-matched names** (e.g. `"Retribution Fighter Sweep"` vs the enum's lowercase
   `"Fighter sweep"`), so those are *fork fixes* — reverting them re-introduces the silent
   fallback bug. Do **not** reset these.
2. **Deliberate fork content.** F-4E-45MC (Heatblur rebuild), the F-14 TARPS-only fits, the
   C-130J-30 EW platform, the Hercules mod-purge deletion, the Vietnam/mod birds, the Iran
   pack — all wanted. Never reset.
3. **The genuinely-bad "early work".** Commit `f6d769b5e "Rewrite player aircraft loadouts"`
   over-stuffed the modern Western player jets. It only ever touched **5 files**, and 4 were
   already reset to upstream stock by `8ebb75808` (#455, F-16A/F-16C_50) and `c6aec441d`
   (#457, F-15ESE/FA-18C/A-10C_2); the 5th (F-14B) is deliberately TARPS-only. So the real
   damage was already ~90 % cleaned up before this pass.

**The lesson: a blind `git checkout upstream/dev -- resources/customized_payloads/` is
actively harmful** — it deletes fork features and re-introduces upstream's own latent
name/CLSID bugs. Scope every reset.

### What this pass did (the scoped reset)

Decision (with the user): reset **plain stock-DCS aircraft** to upstream byte-for-byte,
**drop the fork-added `Retribution DEAD` presets**, and preserve the keep-set (name-fixes,
C-130J EW, F-4E Heatblur, F-14 TARPS, Vietnam/mod birds, Iran). Stock-vs-mod was decided by
`unitType` membership in the `pydcs_extensions` mod-id set (note: F-15D/F-22A/MiG-31BM/the
Su-30·35·57 export variants/B2_Spirit are **mods**; F-117A/MiG-27K/Su-17M4/Su-34/Tu-160 are
stock DCS *AI* aircraft).

- **12 stock jets reset to upstream** (their only fork change was an added DEAD preset, so the
  reset drops it and restores stock): A-10A, A-10C, F-117A, JF-17, MiG-27K, Su-17M4, Su-25,
  Su-25T, Su-30, Su-34, Tu-160, **AV8BNA** (also reverts a Maverick→JDAM swap — fine, Mavericks
  are safe for the AI).
- **8 mod birds kept, DEAD dropped surgically** (kept the mod tuning, removed only the
  fork-added `Retribution DEAD` block): CH_Tu-160M2, F-15D, Su-35S, Su-57, VSN_F35A/B/C_AG,
  VSN_SEM.
- **20 fork-added DEAD presets removed in total** (12 via reset + 8 surgical). **Upstream's
  *own* DEAD presets (~78 files: F-16C, F/A-18C, F-15E, EA-18G, …) were left intact** — those
  are the *upstream standard*; stripping them would be a regression, not a return to it. NB:
  the DEAD *preset* is inert for tasking — `AircraftType.capable_of` reads the YAML
  `task_priorities`, never the payloads — so this changes what a DEAD-tasked jet *carries*
  (now falls back DEAD→BAI→CAS), never *whether* it gets tasked DEAD.

### Corrections — where "byte-for-byte upstream" would have gone backwards

Three cases where a naive reset re-introduced a bug and was instead handled surgically. These
are the "don't go backwards" saves:

- **AJS37** — upstream's ANTISHIP preset uses the dead CLSID `{Rb15}`; the fork fixed it to
  `{Rb15AI}` (RB-15F). Kept the fork file, dropped only its added DEAD → Rb15AI preserved.
  (Caught by `test_customized_payload_clsids_resolve_or_are_known_stragglers`.)
- **B-1B / B-52H** — the fork's Strike preset swaps the GBU-31 **V3** penetrator for
  **V1/Mk-84** (`2b7777c0d`, #81) because the AI refuses to drop V3 JDAMs on soft ground.
  **Preserved** (not reset) — reverting re-introduces the "AI bombers won't drop" bug.
- **F-15ESE / F-16C_50** — the earlier #455/#457 stock resets *byte-for-byte* re-introduced
  upstream's dead `"Retribution Fighter Sweep"` (capital S) name on the two most-flown player
  jets, so their Fighter-Sweep loadout silently fell back to TARCAP. Renamed to
  `"Retribution Fighter sweep"`. (Caught by the new name guard below.)

### The task-priority *rebalance* is a separate system — left alone

Distinct from loadout presets: the fork ran a fleet-wide `tasks:` reweight (196 aircraft,
`6b16d8d66` + `5647b67aa`, per `414th-aircraft-task-rebalance-rubric.md`) that changes *which
airframe the planner prefers for each role*. It is deliberate, principled (tier × archetype),
and modest (±~100 on 0–800), and it is **not** what makes a loadout look wrong in the payload
editor. Deliberately not touched here (user call). If "the wrong jet flew this mission" is ever
the complaint, that reweight — not the DEAD presets — is the lever.

### Guard against recurrence

Two file-reading guards in `tests/data/test_weapons.py` now cover both silent-drop mechanisms:

- `test_customized_payload_clsids_resolve_or_are_known_stragglers` — dead **CLSID** (preset
  dropped at validation).
- `test_customized_payload_retribution_names_resolve_to_a_task` (**new**) — dead **name** in
  the `Retribution `/`Liberation ` namespace (preset never matched → silent fallback). This is
  what would have caught the F-15ESE/F-16C_50 sweep regression at PR time. Two documented
  orphan names are allowlisted (`Retribution CEAD` ×3, `Retribution Strike - Toilet` on the
  A-1 — an intentional cosmetic extra alongside a real `Retribution Strike`).

**Policy for future upstream syncs / loadout edits:** never blind-reset the payloads dir. When
a stock jet's loadout genuinely needs to go back to upstream, reset it, then run both guards —
if either fails, the upstream file carries a latent bug the fork had fixed; re-apply the fix
(the name-standardization casing, the Rb15AI CLSID, etc.) on top of the reset.

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
