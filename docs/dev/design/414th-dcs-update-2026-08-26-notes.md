# DCS update 2026-08-26 - what it does to the fork

Triage of the 2026-08-26 DCS patch against this tree.

**Verified against the updated install on 2026-08-26** (`autoupdate.cfg` reports
`2.9.29.27278`, stamped `20260826-084519`). **Sections 1 to 4 are settled from the
install** — sections 1 and 2 from its own Lua, sections 3 and 4 from two cartridges
saved by the ME's DTC editor on the updated build. Sections 5 onward are still read
from the published patch notes and our own files, and say so where it matters.

Two claims in the first draft were **falsified** by that reading and are marked as such
in place: that nothing could be settled before running the export (§1), and that the
stock F-16C ROE table marks blue's own JF-17 hostile (§4.3).

**The pin moved the same day.** `requirements.txt:37` now points at
`BradySox/pydcs@bfdbb4d` -- the pin commit plus a surgical 2.9.29 delta cut from a
full-install export run on the updated machine: the AGM-45B pair on the F-4E's four
LAU-34 pylons, ten new base-game vehicles (the CHAP transporters and TechWeaponPack
trailers among them), and the BMP-3's in-place update. The patch's weapon display-name
renames are deliberately not carried -- that churn belongs to upstream's ordinary
wholesale refresh when they cut one.

## 1. The export gates the pin, not the triage

The first draft of this note said nothing below could be settled without running the
wiki's `pydcs_export.lua` process. **That was wrong, and it cost nothing to find out.**
All three questions in section 2 are questions about what DCS declares, and DCS
declares it in plain Lua inside the install. Reading those files answered all three,
with no DCS launch.

The export ran the same day (output in `C:/Users/brady/dcs-export/dcs-20260826/`,
July's runs preserved beside it) and both of its real jobs are done:

1. **The pin moved** -- pydcs branch `dcs-2.9.29-surgical` (`bfdbb4d`), cut from the
   pin commit so the fork gets exactly pin + delta. The join was export-vs-pin per
   clsid/unit id, provenance-filtered to declarations living in the DCS install
   itself; Saved Games mod content excluded. The July export could not have served
   as the baseline: it ran with the 414th's OVGME F-4E pack applied, so for anything
   that pack touched it is stock-2.9.28 + pack, not stock.
2. **The extension sweep found four mismatches; two were drift and two were
   deliberate.** Fixed: the two Ukraine-pack jets' un-prefixed `livery_name`s,
   caught on the pack's first real load since the double-nesting fix. NOT fixed,
   on purpose: the CJS trainer Hornets read `networked_datalink = False` where the
   mod says True -- pydcs's `DataLink.for_aircraft_id` has no entry for the trainer
   ids and raises at spawn, so True kills mission generation.
   `tests/fourteenth/test_super_hornet_datalink.py` locks this, and CI proved it
   does: the first push of this change "fixed" the flag to True over the
   in-file comment saying not to, and the suite failed exactly there. A sweep
   mismatch is a lead, not an instruction.

**The surgical branch was then validated against a second, clean-stock export**
(all Saved Games mods disabled, same install, output in
`C:/Users/brady/dcs-export/dcs-20260826-stock/`): every vehicle add field-exact,
BMP-3 exact, F-4E pylons attribute-identical, zero missed vehicle or plane classes.
One gap found and closed -- `{MB339_AIM-9B}`, the patch's one MB-339 addition
(commit `bfdbb4d`). Two side notes from that run: a clean install lets the exporter
finish the countries pass, so `dcs-20260826-stock/countries.py` is a full 1.76 MB
country-wiring dump the modded runs never produced; and settings-bearing weapons are
invisible to `ast.literal_eval`-based diffing (their `settings` is a registry
subscript) -- string-match clsids before concluding a weapon is absent.

The runbook and the heavy-mod gotchas are in `tools/verify_mod_export.py`'s docstring;
the nil-guarded exporter is at `C:\Users\brady\dcs-export\pydcs_export.lua`.

**Read the install first, export second.** For any question of the form "did ED rename
or remove X", the install is ground truth and is greppable now.

## 2. Three silent-breakage candidates - all three settled

| # | Candidate | Predicted | Verdict |
|---|---|---|---|
| 2.1 | BMP-3 id rename | `LayoutException` | **Falsified** - id unchanged. A different break found instead. |
| 2.2 | AGM-45B clsid collision | our stale dict wins | **Confirmed** - stock now declares the clsid. |
| 2.3 | F-4E SUU-23 migration | payload Lua names a dead clsid | **Confirmed, different exposure** - the Lua is clean; the pylon wiring is not. |

### 2.1 "BMP-3 IFV (replaces the old model)" - no LayoutException, but TIC lost its override

**The predicted failure does not happen.** "Replaces" means replaced in place, keeping
the id. `CoreMods/tech/Currenthill Assets Pack/Database/Vehicles/CHAP_BMP3.lua:274`
sets `GT.Name = "BMP-3"`, and no vanilla `BMP-3.lua` survives anywhere under `CoreMods`
or `Scripts` - the CurrentHill file is now the sole definition of the vanilla id.
`db_countries.lua` still assigns `"BMP-3"` to countries. So
`resources/units/ground_units/BMP-3.yaml` (which keys `variants: BMP-3`) and every
layout naming `BMP-3` keep resolving, and `tests/test_layout_unit_types.py` stays green.

**A different break is real.** The same file sets
`GT.DisplayName = _("IFV BMP-3 [CH]")`. `resources/plugins/tic/TIC_v1.1.lua` keys its
per-unit profile table by **DisplayName**, not by id:

- `:512` - `self.displayName = units[1]:GetDesc().displayName or ""`
- `:2300` - `local override = profile[self:GetDisplayName()] or {}`

`profile["IFV BMP-3 [CH]"]` is nil, `or {}` swallows the miss, and the BMP-3 entry's
`SalvoQty = 1` ("These are more like tanks, so need to decrease") silently reverts to
the generic profile. No error, no log line.

**Fixed** in this change: the lookup falls back to the name with a trailing vendor
suffix stripped, so both spellings match and older DCS installs are unaffected.
Verified on Lua 5.1 - `IFV BMP-3 [CH]` and `IFV BMP-3` both resolve to `SalvoQty = 1`,
`APC BTR-80` is untouched, and an unknown name still falls through to default.

**Scope of the sweep.** Two CurrentHill files claim a non-CH id: `CHAP_BMP3.lua`
(`BMP-3`) and `CHAP_T90A.lua` (`T-90`, DisplayName `MBT T-90A [CH]`). TIC is the only
consumer in the tree that keys by DisplayName, it holds five real unit keys
(`IFV BMP-3`, `APC BTR-80`, `APC BTR-82A`, `APC M113`, `SAM Avenger (Stinger)`), and
only `IFV BMP-3` collides. `Moose.lua`'s `IFV BMP-3 [32912lb]` entries are cargo
weights in a different namespace and are unaffected.

**The general lesson, worth more than the fix.** Keying a table by DCS DisplayName is
load-bearing on a string ED can change in any patch, and `or {}` makes the failure
silent. TIC has no harness coverage (`tests/lua/` covers `vietnamops` only), so nothing
catches the next one.

### 2.2 AGM-45B clsid collision (§71) - confirmed

`CoreMods/aircraft/AircraftWeaponPack/anti-radiation missiles.lua:1250-1252` now
declares both clsids natively:

```lua
local AGM_45B_name = "AGM-45B Shrike ARM (LAU-34)"
declare_loadout(LoadAGM45(true,  AGM_45B, AGM_45B_name, "{LAU_34_AGM_45B_SWA}"))
declare_loadout(LoadAGM45(false, AGM_45B, AGM_45B_name, "{LAU_34_AGM_45B}"))
```

Stock settings come from `Get_RFGU_GUISettings_Preset("AGM_45")`.
`pydcs_extensions/f4e_expanded_weapons/f4e_expanded_weapons.py:9` injects the same
`{LAU_34_AGM_45B}` with `Weapons.AGM_45A_Shrike_ARM["settings"]` borrowed, and
`weapon_injector.py` writes with a bare `setattr` plus a bare `weapon_ids[clsid] =`,
with no collision check. Injection runs after import, so **our stale copy wins** -
against a missile whose FM this patch reworked from scratch.

**LANDED with the pin bump.** The two stale dicts are deleted from
`WeaponsF4EExpanded`, and the six AGM-45B pylon rows went with them -- pydcs `bfdbb4d`
carries all six natively, and an injected copy would have made `eject_F4E` strip a
stock store whenever the mod toggles off. Verified: the native entry (full RF-guidance
settings block) sits on pylons 1/3/11/13 after inject and survives eject.

`resources/weapons/standoff/AGM-45B.yaml` already lists the clsid, so the 1972 date
gate holds either way.

### 2.3 F-4E SUU-23 migration - confirmed, and the exposure is not where the note looked

**The payload Lua is clean.** `resources/customized_payloads/F-4E.lua` and
`F-4E-45MC.lua` contain no SUU-23 reference at all, so the upstream-#889 failure mode
does not apply to them.

**The pylon wiring is the exposure.** HB split the pod into `{SUU_23_POD_Wing}` and
`{SUU_23_POD_Centerline}`, and `{SUU_23_POD}` is no longer declared as a loadout
anywhere in the module. The migration ED shipped is a fixed table
(`CoreMods/aircraft/F-4E/Entry/F-4E.lua:1140-1154`) covering **three pylons**:

```lua
local deprecated_loadouts = {
    [pylon_1]  = {["{SUU_23_POD}"] = "{SUU_23_POD_Wing}"},
    [pylon_7]  = {["{SUU_23_POD}"] = "{SUU_23_POD_Centerline}"},
    [pylon_13] = {["{SUU_23_POD}"] = "{SUU_23_POD_Wing}"},
}
```

`f4e_expanded_weapons.py:256` and `:416` wire `Weapons.SUU_23` on pylons **3 and 11** -
the inner wing stations, which our §71 pack added and stock never carried. They are
outside the migration table, so nothing remaps them.

**LANDED, and the live defect was worse than predicted.** pydcs has carried the split
pods since the 2.9.28.26283 update -- with shuffled attribute names: `Weapons.SUU_23`
became the **Centerline** pod, `Weapons.SUU_23_` the Wing pod. Our pylons 3/11 had
therefore been wiring the centerline clsid onto wing stations since the July sync, not
the dead `{SUU_23_POD}` this note predicted. Both re-pointed to `Weapons.SUU_23_`
(`{SUU_23_POD_Wing}`), matching ED's own per-pylon migration for wing stations.

### 2.4 The §71 OVGME mod is unapplied and stale - read before re-enabling it

Not predicted by the first draft, and the most urgent item here for anyone about to fly.

The DCS update overwrote the 414th's `Expanded_F-4E_Weapons_Pack` OVGME mod. The live
`CoreMods/aircraft/F-4E/Entry/F-4E.lua` is stock (43,501 bytes, stamped Aug 26 15:36);
the mod's copy under `OVGME MODS/` is 56,917 bytes, stamped Jul 18. They differ, so the
mod is currently **not applied**.

The mod's July copies predate everything this patch did to the F-4E:

- Zero occurrences of `SUU_23_POD_Wing`, `SUU_23_POD_Centerline` or
  `deprecated_loadouts` - it still ships the single `{SUU_23_POD}`.
- Its own `{LAU_34_AGM_45B}` declaration, which stock now owns.

**Re-enabling it in OVGME as-is reverts ED's 2026-08-26 F-4E work** - the AGM-45B FM
rework and the SUU-23 pod split both go back to July. The four files it ships
(`anti-radiation missiles.lua`, `aim9_family.lua`, `F-4E.lua`, `Weapons.lua`) need
rebasing onto the new stock files before the pack goes back on.

This is a DCS-install matter, not a repo change, so nothing in this PR fixes it.

## 3. AH-64D DTC — BUILT 2026-08-26 (`apache.py`, checklist B105)

**The cartridge's on-disk shape was the one thing blocking this, and it is now known.**
Read from a cartridge saved by the ME's own DTC editor on 2.9.29.27278
(`Saved Games/DCS/DTC/AH-64D BLK.II DTC_1.dtc`, 310 KB).

It is plain JSON. Top level is `{name, type, data}` with `type = "AH-64D_BLK_II"`, and
`data` additionally carries `terrain` — the cartridge is **terrain-scoped**, which the
existing three writers do not have to think about.

```
data
├── NAV
│   ├── MissionFile            int (which mission slot is active)
│   ├── Mission_1              ← the whole nav picture, twice
│   │   ├── Points             {WPTHZ, CTRLM, TGT}, each {isEnabled, POINTS[]}
│   │   ├── Routes             10 named routes: ALPHA, BRAVO, DELTA, ECHO, ...
│   │   ├── Lines              [{note, text, type_num, vertices[{x,y}]}]
│   │   ├── Areas              polygons + caption_pos
│   │   ├── Zones              {NFZ, PFZ}
│   │   └── ADF                Preset_1..Preset_10, each {Freq, ID}
│   └── Mission_2              same shape
├── Presets     {COMM, MPS}    MPS = the 10 text messages, {Title, Option, OptionID, TextLine1..4}
├── Radios      {FM, IFF, InitialRadioSettings, UHF_GuardReceiver}
├── Radios_HF   []
├── Laser       {ChannelsCodes A..K each {One,Two,Three,Four}, DevicesSettings}
├── Weapon      {MissileChannels, SelectedChannels, OtherSettings{PLT, CPG}}
├── MISC        {ASE, PERF, RFI, RLWR}
└── IDM         []
```

**A point is `{num, id, alt, text, note, x, y}`, and `x`/`y` are map metres** — the same
frame `Point` already uses, so no projection work. Example: `{"num": 51, "text": "C51",
"alt": 109, "x": -79974.96, "y": -77762.26}`.

### 3.1 What this changes about the §74 estimate

The mapping in the first draft was taken from the patch notes' description of the cockpit
pages. The file agrees with it, and is simpler:

| Partition | What we already build | Note |
|---|---|---|
| `NAV.Mission_1.Points.WPTHZ` / `.CTRLM` | `DtcOptions.route` | numbered points with alt + label |
| `NAV.Mission_1.Points.TGT` | `DtcOptions.threat_rings` | recon-fogged SAM rings |
| `NAV.Mission_1.Lines` / `.Areas` / `.Zones` | `DtcOptions.flot_and_zones` | NFZ/PFZ are the front line |
| `Presets.COMM` + `Radios` | `DtcOptions.comms` | the radio allocator's channels |
| `NAV.Mission_1.ADF` | CSAR's 260 kHz survivor beacon | **checklist G33** — 10 slots, `{Freq, ID}` |

Still computed nowhere: `Laser.ChannelsCodes`, `MISC.ASE`, `MISC.RLWR`, `MISC.PERF`, and
`Presets.MPS`.

`game/missiongenerator/dtc/` holds `viper.py`, `hornet.py` and `tomcat.py` behind a shared
`common.py` and one `generator.py`. An `apache.py` is a fourth sibling on a settled
pattern, and the format is friendlier than the note assumed.

**Two things to settle before writing it.** `NAV.MissionFile` selects between `Mission_1`
and `Mission_2` and nothing here says which the aircraft loads by default. And the ADF
`Freq` values in this cartridge are bare integers (106, 103, 100) with no unit stated, so
the 260 kHz beacon needs one confirmed round-trip before G33 can rely on it.

The Apache is an Iron Gate and COIN airframe, so it earns its place in those campaigns
rather than being a demo. Lock it against the ME's schemas in
`tests/missiongenerator/test_dtc.py` the way the existing three are.

## 4. The F-16C ROE tab (§74) — BUILT 2026-08-26 (`roedata.py`, checklist B104)

**Read from `Saved Games/DCS/DTC/F-16CM bl.50 DTC_1.dtc` (1.2 MB) on 2.9.29.27278.**
The partition is `data.MPD.ROE`; the colour partition is `data.COLR` (65 scalar entries).

### 4.1 What the tab is

Two checkboxes and a table, and the file names them exactly:

```json
"ROE": { "Settings": { "Mode4Status": true, "TypeSovereignty": true }, "List": [ ... ] }
```

Each of the 48 `List` rows is:

```json
{ "group_name": "A-10", "hint": "A-10A\nA-10C\nA-10C II", "sovereignty": 3,
  "threats": [ {"unit_type": "A-10A", "wstype": [], "displayName": ""}, ... ] }
```

The MMC feeds Type Sovereignty into an ROE tree: Friendly needs one factor, Hostile two,
Suspect one indicating hostile, Unknown nothing. Type comes from NCTR or from another
aircraft on TNDL; Mode 4 status can only come from TNDL.

### 4.2 The family mapping does not need authoring — it is in the cartridge

The first draft budgeted "a fixed `AircraftType` → ATDT-family mapping of roughly 30-40
rows, held as data". **That work is already done by ED and shipped in the file.** The 48
rows carry **87 distinct `unit_type` ids** between them, and those ids are pydcs unit ids:
`F-14` holds seven (`F-14A`, `F-14A-135-GR`, `F-14A-135-GR-Early`, `F-14A-95-GR`, `F-14B`,
`F-14BU`, `F-14D`), `Mirage F1` holds 25, `MiG-29` four.

So the derivation is: read the rows, map each `unit_type` to the coalitions flying it, and
set `sovereignty` per row — Friendly if only blue, Hostile if only red, Unknown if both.
The family-level collision rule from the first draft still holds and is still the point;
it just does not need a hand-written table to apply it.

### 4.3 The claim that the stock table is wrong — FALSIFIED

The first draft said the published default marks **JF-17 HOSTILE**, leaving blue's own
jets on the hostile side of blue's ROE tree on `northern_russia` (Kutaisi, CP 25). It
named AJS-37 as an unclaimed friendly and MiG-23MLD as needing an explicit Unknown.

**No part of that survives contact with the file.** Every one of the 48 rows ships
`"sovereignty": 3` — one uniform value, JF-17 included. Nothing is marked Hostile,
nothing is marked Friendly, and there is no per-type default to be wrong about.

Nor is there a shipped table to check it against: the install carries **no `.dtc` file at
all**, and no ROE defaults are declared in the F-16C module's Lua. The cartridge the ME
writes on a fresh save is the only default that exists.

**The case for building this is unchanged and is now simply the plain one** — the ATDT is
per-campaign data that no single shipped default could supply, and the payoff is the green
Friendly declarations that stop blue-on-blue. It never rested on a defect.

### 4.4 The cartridge's traps dissolved against the install's own files

The saved cartridge made two things look like blockers — seven rows identifying only
by `wstype` quadruple, and `F-15C` absent from every `unit_type` list. **Both were
artefacts of reading the save instead of the schema.** The jet's loader
(`MPD/ROE.lua` `make_ROE_table`) compiles row membership from the install's
`threat_base.lua` and reads **only `sovereignty`** from the cartridge — and
threat_base's `F-15` row covers the F-15C via the `F_15_` wsType, its `hint` strings
naming every member in plain text. So the built derivation ships
`{group_name, sovereignty}` rows, mirrors membership repo-side purely to *derive*
the verdicts (wsType families hand-resolved from the hints), and pins every
mirrored id to pydcs in `test_atdt_ids_all_exist_in_pydcs`. One hint lied the same
way the BMP-3 did: threat_base's Tu-95 says "[CH]" but the live DB id is still
`Tu-95MS` — the CHAP model replaced it in place.

### 4.5 The sovereignty enum -- SETTLED 2026-08-26

The one-more-cartridge experiment ran the same day: the DM hand-set a handful of rows
in the ME's DTC editor ("they all start neutral") and re-saved. Five rows moved off
the default, in two values:

| Value | Meaning | Evidence |
|---|---|---|
| `1` | FRIENDLY | KC-135 (the blue tanker), An-30 |
| `2` | HOSTILE | MiG-23, Mirage F1, Tu-95 |
| `3` | UNKNOWN / neutral | the starting state of all 48 rows, DM-confirmed |

The mapping is DM-confirmed row by row, not inferred: "a 30 is friend, mig 23 is
hostile." It also matches ED's own tab description enumerating the states as
"FRIENDLY, HOSTILE or UNKNOWN" -- 1, 2, 3 in listing order. An all-UNKNOWN shipping
default is the sane one, reinforcing §4.3. Nothing blocks the ATDT derivation now
except the §4.4 wsType rows and the F-15C absence.

### 4.6 Before ~2003 nothing can ever read Hostile, and that is fine

Mode 4 status requires TNDL, and Hostile requires two factors. Where a campaign has no
datalink, Type Sovereignty is the only factor available and every red track tops out at a
yellow Suspect square.

`datalink_introduced` on the 14 airframes that carry it
(`resources/units/aircraft/F-16C_50.yaml:100` is 2003) plus the `DatalinkPolicy` setting
already tell us which campaigns those are: Red Tide, Desert Storm, Red Flag 81-2 and
Northern Russia (1995).

This is correct behaviour, not a defect, and it means the payoff is overwhelmingly the
green Friendly declarations — which is also the half that prevents blue-on-blue.

### 4.7 The correlation half — nothing owed

Offboard datalink tracks now correlate only with real FCR tracks, capped by sub-mode
(SAM/STT 1, DT SAM/DTT 2, TWS 10); uncorrelated datalink symbols overlay Search Targets
instead. The datalink declutter setting no longer disables ROE factors.

§7 hides mobile SAMs from the datalink, but that is ground symbology on the HSD and is
untouched by any of this. **B64** (the datalink era gate) is the row to re-run; there is no
code change here.

**COLR partition — shape known, value low.** `data.COLR` is 65 flat integer entries keyed
by symbol (`HSDHAD_AcquisitionCursor`, `HSDHAD_BullseyeLineOfSight`, …), all `1` in the
sample. Trivial to write and nothing in the campaign derives a colour, so it stays
recorded rather than queued.

### 4.8 Two smaller §74 items

- **"F-16 DTC Multiple in multiplayer loads only first DTC" is fixed.** The §74
  checklist row's open question is whether `AutoLoad` fires on the two §64 spawn
  paths (uncontrolled carrier client, late-activated delayed flight). This fix is
  adjacent to that and may close part of it for free. Do not mark the row on the
  strength of a patch note — fly it.
- **F/A-18C DTC HARM TOO default moved PRI → ALL.** `hornet.py` writes no HARM
  partition, so there is nothing to reconcile. Recorded so the next reader does not
  re-check it.

## 5. Behaviour shifts with no code owed

### 5.1 The airfield taxi and parking rework

ED rebuilt AI taxiway pathing to use aircraft dimensions, and states the change
alters parking placement and increases the number of slots for large aircraft.

Three of ours sit on that surface:

- `game/missiongenerator/aircraft/flightgroupspawner.py:277` and `:316` classify
  "large" as `dcs_unit_type.width > 40`, then fall back through
  `ground_spawns_large`. The threshold is ours; the slot supply underneath it is
  DCS's, and it just moved.
- **B96** (Iron Gate's fields fill without an aircraft losing its stand) is ◐
  PARTIAL and is a stand-count row.
- Iron Gate and Northern Russia both had every squadron's `size:` hand-fitted to
  its base's stand count within the last month. If slot counts changed, those
  numbers are stale in both directions — oversubscription starves the bottom of the
  list silently, and undersubscription just wastes ramp.

The hard constraint stands unchanged: **never restore the per-base backstop EWR**
(§1). It was removed because a ground unit sat on taxiways and broke AI taxi
routing, and the routing code is what just changed. A rework is not evidence the
constraint lapsed.

### 5.2 Legacy SAM belts got more dangerous at low level

- SA-2 (V755) and SA-3 (5V27) gained "the missing K-method of guidance (Half-lead,
  elevated by constant) **for low-level targets**".
- SA-8 (9M33 Osa) moved to a new CFD-derived FM with real motor data and CLOS
  guidance enabled.
- Patriot MIM-104 DLZ corrected against ballistic targets.

Nothing on our side changes — threat rings come from pydcs sensor data, and
guidance method is not in it. But low ingress against a legacy MERAD screen is the
Red Tide, Desert Storm and Vietnam profile, and it is now a different proposition.
Worth telling the squadron before they fly it, not after.

### 5.3 Red SEAD got worse

Kh-25MP had a guidance error added — the note says it plainly, "this missile was
too accurate" — plus a corrected loft shape and a 1 s control delay. Red Weasel
Fitters and Fencers will miss more.

Blue's AGM-45 was reworked from scratch: slightly worse ballistics, substantially
lower steering losses, a wider A/B split. Roughly a wash.

### 5.4 AI air combat

- Radar shots now fly an attack curve to the intercept point; IR shots fly a pure
  pursuit curve.
- The crank is restricted to head-on engagements inside ±60 degrees of the enemy
  axis; otherwise the fighter keeps closing.

§1's QRA reserve feeds the MOOSE `AI_A2A_DISPATCHER`, so red intercepts will play
differently. No change owed; expect different outcomes and do not read them as a
§1 regression.

### 5.5 The AI waypoint fix

"In some cases the AI group does not follow pre-planned waypoint altitude and
speed" is fixed. That is the engine half of what upstream #920 and #925 are about,
and of checklist rows **B79** (ground-level waypoints read the field's elevation)
and **B85** (a flight with an unreachable TOT flies instead of orbiting). Re-run
both after the update; the fix may move them without any work here.

### 5.6 F-16C jammer burnthrough ranges fixed

§77 escort jamming and §2's C-130J both model jamming script-side — spoof bubbles
and ROE weapons-hold pulses — so there is no collision with the engine's burnthrough
math. But **B31** and **B52** are both ◐ PARTIAL jamming rows, and what burnthrough
looks like from the cockpit has changed. Note it on the fly card rather than
re-verifying blind.

## 6. Smaller opportunities

### 6.1 Native trailers (§85)

ED added trailer ATZ-60 for the MAZ-7410, and trailers TZ-22 and **S-75** for the
KrAZ-258B1 and ZIL-131. The S-75 trailer is the SA-2 missile transporter.

§85 already dresses SAM batteries with refuellers and power in the faction's own
kit. A period-correct transloader for every SA-2 site we place is the obvious
extension.

**Gate before promising it:** the patch says "In ME, use the task to attach/detach a
trailer". That is a *task*, not a static or a separate unit. Confirm pydcs can
express it from the generator at all — if it cannot, this is a nice idea with no
route to the miz.

### 6.2 The "Cadet" AI skill

`game/settings/skilloption.py:21` hardcodes
`["Average", "Good", "High", "Excellent"]`. Adding "Cadet" is one line there once
pydcs exposes the enum value, plus a slot in `difficultypreset.py` (the Easy preset
currently uses `Average` for both `enemy_skill` and `enemy_vehicle_skill`).

Clean, self-contained, and an obvious upstream carve. **It answers no open upstream
issue**, so the freeze binds it — the 2026-08-20 issue-ledger exception does not
cover it, and the 2026-08-25 §69 precedent says put it to the DM as a call rather
than infer.

### 6.3 F-14 TARPS — the largest opportunity in the patch

**Re-read against the published notes 2026-08-26 (DM's own paste).** The first draft
of this section listed three of the eleven TARPS lines and called the rest a design
seam. That undersold it: the three lines it skipped are the ones that decide whether
the fork can field recon at all.

The full TARPS block, and what each line costs or buys us:

| Patch line | Why it matters here |
|---|---|
| **"Significantly reduced performance impact"** | The barrier that actually mattered. Frame rate is a first-order constraint in this fork — Yankee Station measures 2-4x sim load and dense TIC sieges are a known sink. An expensive TARPS was an unfieldable TARPS. |
| **"As pilot: hold Store Release button to record (or use Jester wheel)"** + a dedicated Jester submenu + TARPS on the Jester Wheel's new AG → Utilities menu | TARPS was RIO work. It is now a **single-seat sortie** — the difference between a squadron feature and one needing two humans in one jet. Directly relevant to §83 SP Pilot Mode. |
| **KA-99 panoramic camera**, plus KS-87 FWD mode and a *decreased* photo interval | One pass covers materially more ground than the frame camera did. This is the line that bears on `TARPS_POD_RADIUS_NM` — see below. |
| "Images are only visible only after finishing a flight" | The landing gate. Matches §3's own shape: our reveal is processed at debrief for the same reason. Convergence, not conflict. |
| **"intel analysis department"** — circles units found, adds descriptions | DCS now produces an annotated identification product in the cockpit. |
| "Fixed first photo being empty", exposure evening-out | Quality-of-life; nothing owed. |

**The intel is NOT script-reachable.** Verified against the install: TARPS is
`F14Avionics::TARPS` in `bin/F14-Avionics.dll`, rendering to the
`ccTARPS_KS87` / `ccTARPS_KA99` cockpit indicators
(`Cockpit/device_init.lua:202-203`). No file output, no export hook, nothing in
Saved Games. **The campaign cannot read what a photo contains**, and any design that
assumes otherwise is dead on arrival.

**What this unlocks: candidate C in
[414th-recon-role-scoping-notes.md](414th-recon-role-scoping-notes.md).** That note
calls C "the only candidate that is purely additive — it can never conflict with the
reveal rule because it never writes campaign state", and says its machinery already
exists needing only "a reason to be on". The reason shipped in this patch, and the
un-readability above is *why C is the right shape*: we cannot consume DCS's imagery,
but we can put our own card in the same pilot's hands for the same pass. The two
halves are complementary rather than redundant —

- **our card** (`game/missiongenerator/kneeboard_recon/`, gated by
  `generate_target_recon_kneeboard`, default off) is the planning half: aimpoints,
  revetment layout, approach notes. *How to hit it.*
- **DCS's photos** are the verification half: circled, described units, after
  landing. *What was actually there.*

**`TARPS_POD_RADIUS_NM = 3.0` is an orphan** (`game/sim/missionresultsprocessor.py:36`).
Its own comment records that it was the deleted recon plugin's pod radius and that the
command-post reveal "is the only thing that ever read it" — it was never sized against
a camera. The KA-99 is a legitimate reason to revisit it. **Do not pick a new number
from the patch notes**: they state no swath, and an unsourced figure is the failure
mode the startup-times note exists to prevent. It needs a real spec or a flown
measurement.

**The §3 seam is sharper than the first draft said, and still not ours to resolve.**
A pilot can now obtain identification solo and cheaply, and the Threat Intel kneeboard
rows were rewritten from "Fly TARPS to ID" to "Engage to ID" in the same month. So the
pilot gets circled pictures the campaign declines to act on. That is a design question
for the DM — §3's rework is recent, deliberate, and cost eight doc files. **Do not
resolve it in code.** Candidate C is deliberately the path that does not require
resolving it.

## 7. Nothing owed

Checked and clear, recorded so they are not re-checked:

- **Disembark-from-start crash fix** — we set it nowhere. The only tree hit is a
  comment in `resources/plugins/opscsar/OpsCSAR.lua:633`.
- **Removed CA missile player control** for Pantsir-S1, Tor M2 and Project 22160's
  Tor M2KM. We field `CHAP_PantsirS1`, `CHAP_TorM2` and `CHAP_Project22160`, but
  only Combined Arms is affected; the generator never gave a player those seats.
- **F-100D added to the Quick Action Generator** — unrelated to our `f100`
  extension.
- MB-339 AIM-9B, JF-17 airspace drawing, NS430 radio, the P-47D campaign, the new
  "Start Here" menu.

## 8. Rows to re-run after the update

Existing checklist rows this patch touches, none of them rewritten here:

| Row | Why this patch touches it |
|---|---|
| B79, B85 | The AI pre-planned waypoint altitude/speed fix (§5.5) |
| B96 | Stand counts after the parking rework (§5.1) |
| B17 | §64 carrier spawn policy — dynamic spawn parking/FARP improvements |
| B31, B52 | Jammer burnthrough changed in the cockpit (§5.6) |
| G19, G40 | TARPS behaviour and imagery changed under §3 (§6.3) |
| B64 | FCR/TNDL correlation reworked; the datalink era gate is the row that sees it (§4.6) |

New rows added by this triage: **B100**, **B101**, **B102** — see
[414th-ingame-pass-checklist.md](../414th-ingame-pass-checklist.md).
