# 414th — Native DCS DTC export (design + reverse-engineered schema)

Goal: have Retribution auto-write **native DCS Data Transfer Cartridges** into the
generated `.miz` so F/A-18C players can load the coalition SA picture
(CAP tracks, corridors, FAOR/FLOT, MEZ threats), threat rings, TACAN, and (optionally)
the route already loaded.

This doc is the ground truth for the storage format. It was reverse-engineered from a
real ME-authored sample (`dtc_sample.miz`, F-16C + F/A-18C, all partitions filled),
decoded with `dtc_schema_dump.py` at the repo root. The reverse-engineering archive covers
both formats; the currently shipped generator is **F/A-18C only**.

---

## TL;DR architecture (this changes the earlier plan)

- **Cartridges are standalone JSON files inside the `.miz` archive**, in a `DTC/` folder:
  - `DTC/F-16CM bl.50 DTC_1.dtc`
  - `DTC/FA-18C Lot 20 DTC_1.dtc`
  - Current DCS also mirrors these into alternate native aliases such as
    `DTC/F-16C_50.dtc`, `DTC/F-16CM_bl.50_DTC_1.dtc`,
    `DTC/FA-18C_hornet.dtc`, and `DTC/FA-18C_Lot_20_DTC_1.dtc`.
    Retribution writes all observed aliases with identical JSON payloads so the mission
    import path can match whichever filename convention the current build prefers.
  - The file body is JSON (not Lua), pretty-printed.
- **There is NO per-unit reference in the `mission` table.** The unit dicts for the
  F-16/F-18 contained *zero* DTC linkage; the whole `mission` blob has no `dtc` substring.
  A thorough search of every other archive member (`options`, `warehouses`,
  `dictionary`, `mapResource`, `theatre`) found no linkage either.
- **Linkage is by aircraft TYPE + slot index.** The cartridge is matched to aircraft by
  the `"type"` field inside the `.dtc` (e.g. `F-16C_50`, `FA-18C_hornet`) and the
  filename. The `_1` suffix is the cartridge **slot**; `DTC_1` is the default/loaded one.

### Consequences for Retribution
- **We do NOT touch pydcs or the `mission` table.** Implementation = build JSON dicts and
  inject `DTC/*.dtc` entries into the zip *after* `self.mission.save(output)`
  (`game/missiongenerator/missiongenerator.py:140`). Much simpler than per-unit injection.
- **Cartridges are type-scoped.** All F-16s in a mission share one cartridge; all Hornets
  share another. We produce **one cartridge per (airframe type)** present on the player
  coalition. This is a natural fit for coalition-wide data (comms ladder, SA picture,
  threat rings, TACAN) but means a per-flight *own route* cannot differ between two
  flights of the same airframe. See "Route handling" below.
- Per-unit/per-cartridge assignment *may* exist in the in-sim "Load to group" flow, but
  its storage format is **unverified** (the sample did not produce it). Do not build on it
  without a fresh sample proving the format.

---

## Coordinates & units (verified from sample)

- All positions are **DCS world coordinates in meters**, fields `x` (north) / `y` (east) —
  the same projection pydcs/Retribution already use. `Point.x` -> `x`, `Point.y` -> `y`
  **directly, no conversion.**
- `alt` / `elev` are **meters**.
- **Threat ring radius units differ by airframe** (be careful):
  - F-16 `THREAT_PTS[].radius` is in **meters** (sample: `37040` = 20 nm).
  - F/A-18 `MEZ_THRTS[].threat_ring_radius` is in **nautical miles** (sample: `20`).
- TACAN `frequency` is in **Hz** (sample: `977000000`).
- COMM frequency is an **integer in MHz** (e.g. `305`, `124`).
- `modulation`: F-16 COMM used `1`; F-18 COMM used `0`. (AM/FM — confirm per radio.)

---

## File envelope (both airframes)

```json
{
  "data": { ...partitions... , "name": "", "terrain": "Caucasus", "type": "<TYPE>" },
  "name": "<TypeDisplayName> DTC_1",
  "type": "<TYPE>"
}
```

`terrain` is the map name; must match the mission's theatre. `<TYPE>` is the DCS unit
type id (`F-16C_50`, `FA-18C_hornet`).

---

## F-16C partitions (`data` children)

- `COMM`: `COMM1`, `COMM2`, each `Channel_1..Channel_20` = `{ "freq": <MHz int>,
  "modulation": <int> }`. Plus `mirror_COMM1`/`mirror_COMM2` bools.
  (NOTE: F-16 channel objects have **no** `name`; F-18 do — see below.)
- `ELINT`: `{ "RWR": { ... } }` — a large per-emitter priority/display table
  (`display`, `PRI`, `search`, `unknown` per radar). Big default table; preserve defaults.
- `MPD`:
  - `CMDS`: `CMDSBingoSettings` (`BINGO`,`ChaffNum`,`FlaresNum`,`Other1Num`,`Other2Num`,
    `FDBK`,`REQCTR`) + `CMDSProgramSettings` with programs `AUTO1..3`, `BYP`, `MAN1..4`,
    each `{ Chaff|Flare|Other1|Other2: { BurstInterval, BurstQuantity, SalvoInterval,
    SalvoQuantity } }`. Also a per-missile MWS threshold table.
  - `NAV_PTS`: array of steerpoints. Rich object: `id:"STPT<n>"`, `number`, `type:"STPT"`,
    `x`,`y`,`alt`, `altitudeType`, `speed`, `routeAltitude`, `TOS`/`isTOSEnabled`,
    OAP fields (`OAP_1_*`,`OAP_2_*`,`idOA1`,`idOA2`,`isOAP_1/2`), `R1/R2/R3`,
    `velocityType`, `note`.
  - `DEST`: array, ids `DEST81..` (steerpoints 81-99). `{ alt,id,note,number,text:"D81",x,y }`.
  - `GEO_LINES`: array, ids `GEO_LINES31..` (31-55). `{ alt,id,L1..L4(bool),note,number,x,y }`.
  - `THREAT_PTS`: array, ids `THREAT_PTS56..` (56-70).
    `{ alt,def_num,elev,id,number,radius(meters),ring(bool),text:"CST",threatName:"Custom",x,y }`.
  - `mirror_DEST`, `mirror_GEO_LINES`, `mirror_NAV_PTS`, `mirror_THREAT_PTS` bools.
  - `terrain`.

## F/A-18C partitions (`data` children)

- `COMM`: `COMM1`,`COMM2`, `Channel_1..20` = `{ "frequency": <MHz int>, "modulation":
  <int>, "name": "CH n" }`. (Key is `frequency` + has `name`, unlike F-16's `freq`.)
- `ALR67`: RWR/threat table (analogue of F-16 `ELINT`).
- `SA` (the SA-page graphics partition):
  - `CAP_PTS`: `{ id:"CAP_PTS_<n>", num, x, y, course, diameter(m), length(m),
    turn_direction:"Left"|"Right", note }`. A racetrack: diameter+length+course+turn.
  - `CORRIDORS`: `{ id:"CORR_<n>", num, note, points:[{id:"CORR_<n>_PT_<k>",x,y}] }`.
  - `FAOR_FLOT`: `{ FAOR:[{id,num,note,points:[{id,x,y}]}], FLOT:[...same...] }`.
  - `MEZ_THRTS`: `{ id:"MEZ_THRTS_<n>", num, text, threat_level(int), threat_ring_radius
    (NM), threat_type:"Custom", x, y }`.
  - `SETTINGS`: `DCLTR_SETTINGS` (`MREJ1`,`MREJ2` -> per-layer declutter bools) +
    `SENSORS_SETTINGS` (`FF_tracks`,`FRIEND_Symbols`,`PPLI_tracks`,`RWR_Symbols`,
    `SURV_tracks`,`UNK_tracks`).
  - `Default_CAP_Point`, `Default_CORRIDORS_Point`, `Default_FAOR_Line`,
    `Default_FLOT_Line`, `Default_MEZ_THRTS_Level` (ints), `mirror_MEZ_THRTS` bool.
- `TCN`: array of TACAN beacons `{ callsign, channel, display_name, elevation,
  frequency(Hz), x, y }`.
- `WYPT`: `{ mirror_NAV_PTS(bool), NAV_PTS:[{ id:"STPT<n>", alt, altitudeType, idOA,
  idOA_Line, isOA, OA_* fields, R1/R1_order/R2/R3, text_note, ... , x, y }] }`.
  (Single OA per point, vs F-16's OA1/OA2.)

---

## Retribution data -> DTC mapping

| DTC field | Retribution source |
|---|---|
| F-18 `SA.CAP_PTS` | BARCAP/TARCAP racetrack geometry (center, course, leg length) |
| F-18 `SA.CORRIDORS` | ingress/egress corridor + tanker tracks |
| F-18 `SA.FAOR_FLOT.FLOT` | front line trace |
| F-18 `SA.MEZ_THRTS` / F-16 `THREAT_PTS` | SAM network sites + threat radii |
| F-18 `TCN` | tanker/airfield TACAN beacons |
| `COMM` | per-coalition radio preset ladder |
| `MPD.CMDS` | faction/airframe countermeasure program defaults |
| `NAV_PTS` / `DEST` | package/flight waypoints (see route handling) |

## Route handling (the one open product decision)

Because cartridges are type-scoped, NAV_PTS/DEST can't differ between two flights of the
same airframe. Options:
- **(A, recommended)** Don't inject own-route waypoints. Inject only coalition-shared
  data: COMM, SA (CAP/CORRIDORS/FAOR/FLOT/MEZ), THREAT_PTS, TACAN, CMDS. No conflict with
  ME flight plans; every value is genuinely coalition-wide.
- **(B)** Also inject a shared route (identical steerpoints for all same-type jets) — only
  sensible for single-flight or single-airframe packages.

---

## Implementation outline

- `game/missiongenerator/dtc/` package:
  - `model.py` — typed dataclasses for the cartridge + partitions.
  - `f16.py`, `f18.py` — airframe-specific envelope/key differences.
  - `builders.py` — map Retribution (packages, flights, threat zones, front line,
    tankers, comms) -> partition dicts.
  - `injector.py` — write `DTC/<name>.dtc` JSON entries into the saved `.miz` zip.
- Hook after `self.mission.save(output)` in `missiongenerator.py`.
- Settings: a `generate_dtc` toggle (default off until in-game validated).
- Tests: builder unit tests from fakes; JSON round-trip; injector adds expected entries.

## Implemented (v1) vs deferred

Shipped (`game/missiongenerator/dtc/`, gated by the `generate_dtc` setting, default off):
- **F/A-18C only**, **`SA.CAP_PTS` only**: player/AI CAP racetracks **and** tanker tracks.
  That is the whole payload now -- see "Scope" in the gotchas above.
- Built by overlaying the CAP/tanker tracks onto the captured ME template
  (`resources/dtc/templates/FA-18C_hornet.dtc`), so COMM / ALR67 / CMDS keep their ME
  defaults and the cartridge stays structurally complete. Injected as `DTC/*.dtc` zip
  members after `mission.save()` **and** mirrored into `Saved Games\DCS\DTC`.

Removed on purpose (the 414th decided DCS already covers these, 2026-06-14):
- **Threat rings** (`F-18 MEZ_THRTS`, `F-16 THREAT_PTS`): DCS draws threat rings itself from
  intel, so carrying them was redundant (and produced a stray huge ring). All threat
  collection/build code is gone.
- **Front line** (`F-18 FAOR_FLOT.FLOT`) and the **entire F-16C cartridge** (it had no
  CAP/tanker partition, so it would only ever carry redundant threats or risk clobbering
  COMM/CMDS with template defaults).

Deferred (each needs more work or another decoded sample):
- **F-16 `GEO_LINES`** (front line / corridors as drawn lines): the per-point `L1`-`L4`
  line-connection flags were all `false` in the sample, so their semantics are undecoded.
  Decode with a sample that actually draws GEO lines before implementing.
- **`CORRIDORS`** (ingress/egress lanes) and **`TCN`** (airfield TACAN beacons): TCN needs
  beacon->map-position wiring (`Beacons` carries freq/channel but no position).
- **COMM / CMDS generation**: templates currently carry stock ME defaults; pydcs already
  bakes per-flight radio presets into units independently of DTC.
- **Per-flight own routes** (`NAV_PTS`/`DEST`): impossible under type-scoping (decided).
- Re-decode helper: `dtc_schema_dump.py` (repo root) against a fresh sample `.miz`.

## ROOT CAUSE + FIX (2026-06-14) — cartridge NAME collision, not format

The "lists but never auto-applies" bug was **not** the cartridge content and **not** the
mission Lua format. Both were verified correct:

- **Content correct.** A key-for-key diff of the embedded `DTC/*.dtc` against the native
  cartridges DCS itself wrote to `Saved Games\DCS\DTC\` is structurally identical.
- **Per-unit linkage format correct.** Opening a generated mission in the DCS ME and
  re-saving round-tripped our exact block unchanged —
  `["DTC"]={["AutoLoad"]=true,["Cartridges"]={[1]={["default"]=true,["name"]=...}}}` — and
  the ME DTC panel displayed it correctly ("Pre-load default DTC upon mission start" ✓ =
  `AutoLoad`; the cartridge row with **Def** ✓ = `Cartridges[1].default`). So this format
  is what the editor produces. It is required (the per-jet binding) but on its own it was
  not the failure.

**The actual bug:** DCS auto-loads a cartridge by its in-sim **name**, resolved against the
player's personal `Saved Games\DCS\DTC` library as well as the mission. The old names
copied ED's default airframe-variant convention (`FA-18C Lot 20 DTC_1`,
`F-16CM bl.50 DTC_1`) — exactly what a player's own cartridges are named. A stale personal
cartridge of the same name (observed: a `PersianGulf` one) shadowed the mission's `Iraq`
cartridge, and the terrain mismatch made DCS silently refuse to apply it. Removing the
stale library files made the mission cartridge resolve.

**The fix (robust for every squadron member's machine):** use a neutral, terrain-tagged
name `Retribution <terrain> DTC_1` (`cartridge.py` `_NEUTRAL_NAME_PREFIX` /
`cartridge_display_name(terrain_name)`). No player library will contain it, and the
terrain tag means a stale cartridge from another map can never shadow it. The name is
shared by both airframes; DCS disambiguates the file by the cartridge `type` field.
Archive members are now written under the **canonical type-id filename only**
(`DTC/FA-18C_hornet.dtc`, `DTC/F-16C_50.dtc`) — type-unique, matches DCS's own naming, and
the ED-default-name aliases (the collision source) are gone. The `AutoLoad`/`Cartridges`
unit block is kept as-is (verified correct above).

## KNOWN LIMITATION — auto pre-load does not fire (manual load works)

Verified 2026-06-14 with a fully correct setup: embedded cartridge named
`Retribution <terrain> DTC_1` with the CAP tracks, the matching `<name>.dtc` in
`Saved Games\DCS\DTC`, and every player Hornet carrying
`["DTC"]={["AutoLoad"]=true,["Cartridges"]={[1]={["default"]=true,["name"]=...}}}` (which
the ME reads back as "Pre-load default DTC upon mission start" checked).

Result in-sim: the cartridge does **not** auto-apply at spawn. The SA page stays empty
until the player opens the DTC manager and manually loads `Retribution <terrain> DTC_1`,
at which point the CAP/tanker tracks populate correctly. So the data path is sound; only
DCS's mission-start pre-load is not wiring up in this build. Nothing more to fix on the
Retribution side -- shipping behavior is **manual load once per sortie**. Re-test ED's
pre-load on future DCS builds before assuming it still needs the manual step.

## Gotchas learned in-game

- **DCS reads cartridges from `Saved Games\DCS\DTC`, not the embedded `.miz`** — and the
  library file must be named after the cartridge **name** (`<name>.dtc`), not the aircraft
  type. The per-unit AutoLoad block references the cartridge by name
  (`Retribution <terrain> DTC_1`), and DCS resolves a *named* cartridge to a `<name>.dtc`
  file; the type-default filename (`<type>_DTC.dtc`) is the *unnamed* slot. Writing the
  data under `<type>_DTC.dtc` left it importable (Import reads the raw file) but invisible
  to the name-keyed dropdown/auto-load, so the pre-load found nothing and the dropdown fell
  back to the default. `DtcGenerator._write_saved_games_library()` writes
  `<cartridge name>.dtc` (path from `persistency.base_path()`). The `.miz` injection is
  kept for the per-unit AutoLoad binding + portability. NOTE: this is a per-machine library
  write, so it does not distribute to other clients in multiplayer -- still open.
- **Scope (per the 414th): the deliverable is the Hornet SA page tanker + CAP tracks.**
  Threat rings draw themselves from DCS intel; COMM and waypoints load from the mission
  independently of DTC. So `CAP_PTS` (player/AI CAP racetracks + tanker tracks) is the
  partition that matters. `_collect_orbits()` includes AI flights (tankers are always AI)
  and excludes AEW&C; the old `client_count > 0` filter is gone (it was zeroing CAP_PTS).
- **Threat rings reuse the auto-hide-SAM MFD filtration.** `_collect_threats()`
  (`sadata.py`) skips any enemy TGO with `hide_on_mfd` set, so mobile SHORAD/AAA never
  generate DTC rings -- only MFD-visible static/standalone SAM sites do, matching what the
  player sees on the datalink.
- **`mirror_*` booleans gate whether a partition is APPLIED on load.** The templates were
  captured with empty arrays, so `MPD.mirror_THREAT_PTS` (F-16) and `SA.mirror_MEZ_THRTS`
  (F-18) ship `False`. Populating the arrays without flipping the flag produced a cartridge
  that auto-loaded but applied **no** threat rings (data present, silently ignored).
  `_build_f16()` / `_build_f18()` now set the matching `mirror_*` flag `True` whenever they
  write a non-empty partition. (CAP_PTS and FLOT have no mirror flag in `SA`.)
- **F-18 `WYPT` must be structurally complete.** The current DCS SA-partition build
  expects `WYPT` to carry `NAV_PTS`, `NAV_ROUTE`, `NAV_SETTINGS`, `terrain`, and
  `mirror_NAV_PTS`. A template captured from an older build had only
  `NAV_PTS`/`mirror_NAV_PTS`; DCS then rejected the whole cartridge and it never
  auto-loaded. Templates are rebuilt from a current ME-authored cartridge (SA arrays
  emptied) to stay structurally complete.
- **`terrain` appears in multiple places** (`data.terrain`, F-18 `WYPT.terrain`, F-16
  `MPD.terrain`). All must match the mission theatre or the cartridge fails to load.
  `build_cartridge()` sets each one present.

## Validation
- `black --check .`, `mypy game tests`, `pytest tests -q`
  (`tests/missiongenerator/test_dtc.py`).
- In-game: load a generated mission, ramp-start an F-16 and an F/A-18, confirm the default
  cartridge auto-loads with the expected COMM/SA/threat data.

## Scratch artifacts (delete before commit)
- `dtc_schema_dump.py`, `dtc_dump.txt` at repo root — analysis only, not part of the feature.
