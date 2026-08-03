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
- **S-3B addendum (2026-07-16, the flown Scenic Route finding — the one the sweep missed):**
  the S-3B's `Retribution DEAD` preset was an **AGM-84E SLAM** (standoff land-attack, not an
  ARM — the DCS S-3B has no anti-radiation missile), and unlike the 20 above the yaml ALSO
  carried `DEAD: 280` in `task_priorities`, so the Viking was genuinely *offered and tasked*
  for DEAD (a flown 4-ship flew a DEAD sortie it could never perform). Both removed:
  the preset from `resources/customized_payloads/S-3B.lua` and the `DEAD` entry from
  `resources/units/aircraft/S-3B.yaml`. Strike/CAS/BAI/OCA/Anti-ship keep their presets.

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

## 2026-07-17 addendum — the F-14 TARPS-only strip was the real breakage

The one place the 2026-07-06 reset went too far: PR #457 stripped `F-14B.lua`,
`F-14A-135-GR.lua`, and `F-14A-135-GR-Early.lua` to the single `Retribution TARPS`
preset on the claim "non-recon tasking falls back to the pydcs default." **There is no
such fallback** — pydcs ships no payload files, so `Loadout.default_for_task_and_aircraft`
walks its name candidates, finds nothing, and returns `empty_loadout()`. Every
BARCAP/TARCAP/Escort-auto-planned Tomcat on **both** coalitions flew with zero pylons.
Never showed at home because the 414th's own campaigns fly the F-14 as TARPS-only; the
Persian Gulf "Scenic Route" test campaign exposed it (2026-07-17 turn-2 fly: four blue
F-14B BARCAP/Escort flights + red's two F-14A escort flights all launched clean; the four
blue BARCAP jets died on their correctly-planned station without a shot in reply — the
turn-3 "8 Tomcats fired zero A2A, SM-2s won every race" read was this same bug,
mis-attributed).

Fix: the three files are now **upstream/dev stock presets + the `Retribution TARPS`
preset appended** (the #457 intent done right), plus a fork correction upstream still
carries: **upstream's `F-14A-135-GR-Early.lua` declares `["unitType"] = "F-14A-135-GR"`**,
and pydcs binds payload files by that field (`FlyingType.scan_payload_dir` regex), so the
whole file never attaches to the Early jet — with it, the Early variant resolves nothing,
not even a preset that IS in the file. Upstream-carve candidate (one-line fix + the
observation that their Early Tomcat has no working presets at all).

New guard: `tests/test_f14_loadouts.py` — every F-14 variant must resolve an **armed**
loadout (an AIM on the rails, matched by weapon *name*, not CLSID — the AI F-14A's stores
are GUID CLSIDs) for BARCAP/TARCAP/Escort/Sweep/Intercept, TARPS must resolve the recon
preset, and the Early file's `unitType` field is pinned. Corollary to the reset policy
above: **a preset file must cover every task the airframe can be auto-planned on** —
"the engine will fall back" is never true; the fallback is an unarmed jet.

## 2026-08-02 addendum — carrier airframes carry the Navy case

Off the DM's ask that "the carrier should be using the *navy* version of bombs when able
to" (GBU-31(V)4/B white case, not the Air Force (V)3/B green case).

**The actionable set is smaller than it looks.** DCS models only three AF/Navy store pairs:
`GBU-31(V)1/B`↔`(V)2/B` (Mk-84 body), `GBU-31(V)3/B`↔`(V)4/B` (BLU-109 penetrator), and
`GBU-24A/B`↔`GBU-24B/B`. Everything else a carrier jet drops — GBU-10/12/16, GBU-38,
Mk-82/83/84 — is **one store shared by both services**, with the Navy variation expressed
through the cockpit fuzing menu rather than a separate weapon. So there is nothing to pick
for the 500 lb and 1000 lb classes; only the 2000 lb classes have a case to get wrong.

A sweep of every carrier-capable airframe's shipped fits found the fork already correct
almost everywhere: the player Hornet (`FA-18C_hornet.lua`) and the Bombcat (`F-14BU.lua`)
ship `GBU_31_V_2B`/`GBU_31_V_4B`, and the Harrier ships `GBU_32_V_2B` (the 1000 lb JDAM has
no AF twin in DCS). The one offender was the **CJS Super Hornet** — `FA-18E.lua` /
`FA-18F.lua`, fits `Retribution Strike` and `Retribution OCA/Runway`, flying 4× (V)3/B.

**The mod constrains the fix**, which is why the "when able to" clause is load-bearing.
CJS clears the Navy `(V)4/B` on **only the two midboard stations** — verified in the
installed mod's own `Entry/FA-18EFG_HARDPOINTS_V2.lua:479,753`, and matching the
`pydcs_extensions` tables — while the AF `(V)3/B` is cleared on four. A straight 4× swap is
impossible. The fits are re-authored to:

| pydcs pylon | station | store |
|---|---|---|
| 2 | STA 02 | `{SUPERHORNET_PYLON_02_OB_MK_1X_GBU-32}` — 1× GBU-32(V)2/B |
| 3 | STA 03 | `{SUPERHORNET_PYLON_03_MB_MK_1X_GBU-31_V_4B}` — 1× GBU-31(V)4/B |
| 7 | STA 09 | `{SUPERHORNET_PYLON_09_MB_MK_1X_GBU-31_V_4B}` — 1× GBU-31(V)4/B |
| 8 | STA 10 | `{SUPERHORNET_PYLON_10_OB_MK_1X_GBU-32}` — 1× GBU-32(V)2/B |

Four bombs as before, all white case, 6000 lb against the old 8000 lb — the mod's ceiling
for an all-Navy load that keeps a 2000 lb penetrator. The `NFP` fuze settings block
(`MDRN_B_A_PGM_TAILONLY` / `FMU139CB_LD`) carries over unchanged; it is JDAM-family generic.

**The gotcha worth remembering: a CJS pylon index is not a station.** Pylon 2 reaches
STA 02 *and* 03, pylon 3 reaches 03 and 04, pylon 7 reaches 08 and 09, pylon 8 reaches 09
and 10. The obvious "backfill the outboards with the BRU-55 2× GBU-32" idea puts those pairs
on STA 03/09 — the same midboards the `(V)4` now claims — which the mod's own
`SUPERHORNET_PYLON03_MIDBOARD_L_FORBIDDEN` / `..._PYLON09_MIDBOARD_R_FORBIDDEN` lists
reject. Both directions were checked before authoring: the outboard singles are absent from
those lists, and the outboard lists carry no GBU-32/`(V)4` entries. Because DCS strips an
illegal store **silently**, a station collision here reads as a naked jet with no error.

New guard: `tests/fourteenth/test_navy_bomb_variants.py` — a fork-wide sweep asserting no
carrier-capable airframe ships an AF-cased store on a pylon where the Navy twin is
mountable (confirmed to fail on the pre-fix data), plus a pin on the authored Super Hornet
fit including the four stores' pylon legality and that they resolve to four *distinct*
physical stations. Like the sweep above it reads the payload `.lua` files directly rather
than through `FlyingType.load_payloads`, so it asserts what this repo ships and never picks
up a developer's own `Saved Games/.../UnitPayloads` — which, note, **takes priority over the
shipped presets at runtime**, so a personal saved payload of the same name still wins.

Noted in passing, not fixed: `resources/customized_payloads/FA-18C.lua` binds
`unitType = "F/A-18C"` (the AI-only Hornet) and still carries AF `{GBU-31V3B}`, but that
airframe has **no unit data file** in this fork (`No data for F/A-18C; it will not be
available`), so the file is dead — as are the `F/A-18C` entries in the dozen factions that
list it. Same shape as the other AI twins of module aircraft (`F/A-18A`, `F-5E`, `Hawk`,
`L-39C`, `Mirage-F1C`), i.e. deliberate upstream behaviour, not a regression. Left alone;
the sweep skips it for the same reason.

### The other half — the white case is a *setting*, not a store

The store swap above only covers the 2000 lb classes, because those are the only
AF/Navy pairs DCS models as separate weapons. The **white (thermally protected) body**
at every other size is a per-loadout **visual setting**:

```lua
["settings"] = { ["NFP_VIS_DrawArgNo_57"] = 1 },   -- 1 = Navy white, 0 = green
```

written by the Mission Editor's weapon-settings ("fuzing") panel and applied to draw
argument 57 of the bomb model. **Reference: ED's own
`CoreMods/aircraft/F14/UnitPayloads/F-14BU.lua` sets `1` on every bomb the Bombcat
carries** (GBU-12/16/24E/38/31(V)2) — the canonical "Navy jet, all bombs white" layout.
Confirmed empirically by a DM-built test miz (2026-08-02) carrying the same
`{BRU55_2*GBU-38}` twice, one at `1` and one at `0`.

Three traps:

- **`0.1` on the same key is a missile visual** (AIM-9/9X seeker), not a casing. The
  argument is model-specific — only ever write it on bomb entries. A positive
  bomb-name gate is what keeps it off things like the A-6E's `{HB_A6E_D704}` buddy pod.
- **`NFP_PRESID`** (`MDRN_B_A_PGM_TWINWELL_USN`, `MDRN_B_A_PGM_HTP_USN`, …) is declared
  **by the weapon itself** (`AircraftWeaponPack/JDAM.lua` et al.), not chosen per
  loadout — it is *not* the casing selector, and its `_USN` variants exist only for the
  TWINWELL and HTP families. Likewise **"TP" in a DCS bomb name means Training
  Practice** (inert), not thermally protected.
- **Whether a store supports the setting at all is decidable**: a weapon declared with
  `Get_Combined_GUISettings_Preset(...)` has a fuze **and visual** section; one declared
  with `Get_Fuze_GUISettings_Preset(...)` has fuze only. Cluster munitions (Mk-20,
  CBU-99, CBU-105) are Fuze-only and correctly carry no casing. The preset *definitions*
  are compiled into DCS binaries — there is no readable Lua — so that declaration call
  is the only programmatic signal available.

The pass sets `= 1` on every bomb entry of the US Navy/USMC strike jets —
`FA-18C_hornet`, `FA-18E`/`F` (CJS), `AV8BNA`, `A6E`, `A-7E`, the three
`F-14A-135-GR`/`Early`/`F-14B`, and `F-14BU`.

**It writes the casing key and nothing else** (DM call 2026-08-02 — "keep everything
default besides the color"). An entry that already had a settings block gets the one key
set or inserted, every other key untouched; an entry with no block gets a block
containing only the casing key, so fuze type, arm/function delay and preset id all stay
at the DCS default exactly as before. The first cut authored a *full* ME-style block per
preset and was reverted: it silently introduced fuzing settings onto airframes that had
never carried any, which is a behaviour change nobody asked for and a much worse failure
mode than a bomb staying green. Worth recording anyway, since it is the trap if that
approach is ever revisited: the presets do **not** share fuze values —
`MDRN_B_A_PGM_HTP_USN` uses **FMU-143 at 5.5 / 0.03**, not the FMU-139 numbers of the
other JDAM presets.

Deliberately excluded: **`F-14A-95-GR`** is the Export (Iranian) Tomcat; the **VSN** and
**VWV** mods (wrong nation, and the coating postdates Vietnam); cluster munitions; and
`{BRU-32 GBU-24}` (Paveway III — no observed exemplar block, so the Tomcats' GBU-24 stays
green until one exists).

Guards added to `tests/fourteenth/test_navy_bomb_variants.py`: on a Navy jet the key may
be absent (that store has no visual section) but must never be `0`, and a floor list pins
that the jets this was actually asked for still carry it. Both were confirmed to fail
when reverted.

In-game pass = checklist **B36**.
