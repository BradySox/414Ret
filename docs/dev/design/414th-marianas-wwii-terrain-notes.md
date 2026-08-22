# Marianas WWII terrain support

Adding `MarianaIslandsWWII` (DCS install folder `MarianasWWII`, Early Access) to the fork.

Status 2026-08-22: **built and verified.** The terrain loads, projects, resolves its landmap
and carries all 11 airfields with 512 parking slots. No campaign is authored on it yet, so
players cannot reach it from the New Game wizard — that, and the 1944 faction gaps below,
are what stand between this and a playable Forager campaign.

Precedent followed: Kola, Afghanistan, Iraq and Germany Cold War, per
[Module Checklists](../wiki/Module-Checklists.md).

---

## What the map is

- Theatre id `MarianaIslandsWWII`; install folder `<DCS>\Mods\terrains\MarianasWWII`.
- Guam, Rota, Tinian, Saipan, Pagan. Frozen at 15 June – 10 August 1944 (Operation Forager).
- **No beacons at all.** `beacons.lua` declares `beacons = {}` — same as Normandy and The
  Channel. `resources/dcs/beacons/marianaislandswwii.json` is `{}` and that is correct, not
  a stub.
- 11 airfields. Ids follow their `radio.lua` `radioId` (`airfieldN_0` maps to id N), which
  was predicted before the export and confirmed by it.

  | id | Airfield | Island | Slots | 40x40+ | HF | VHF lo | VHF hi | UHF |
  |---|---|---|---|---|---|---|---|---|
  | 1 | Agana | Guam | 39 | 3 | 3.800 | 38.500 | 118.100 | 250.100 |
  | 2 | Orote | Guam | 33 | 4 | 3.825 | 38.550 | 118.150 | 250.150 |
  | 3 | Airfield 3 | Tinian | 81 | 13 | 3.850 | 38.600 | 118.200 | 250.200 |
  | 4 | Charon Kanoa | Saipan | 12 | 3 | 3.875 | 38.650 | 118.250 | 250.250 |
  | 5 | Gurguan Point | Tinian | 41 | 4 | 3.900 | 38.700 | 118.300 | 250.300 |
  | 6 | Isley | Saipan | 64 | 11 | 3.925 | 38.750 | 118.350 | 250.350 |
  | 7 | Kagman | Saipan | 33 | 8 | 3.950 | 38.800 | 118.400 | 250.400 |
  | 8 | Marpi | Saipan | 35 | 8 | 3.975 | 38.850 | 118.450 | 250.450 |
  | 9 | Rota | Rota | 52 | 10 | 4.000 | 38.900 | 118.500 | 250.500 |
  | 10 | Ushi | Tinian | 103 | 17 | 3.750 | 38.400 | 118.000 | 250.000 |
  | 11 | Pagan | Pagan | 19 | 0 | 3.775 | 38.450 | 118.050 | 250.050 |

  MHz. Frequencies read out of the terrain's own `radio.lua` **before** the export existed;
  all 11 sets matched it afterwards, which is what makes the export trustworthy.

  **The display names are shorter than the radio callsigns** — the export gives `Ushi`, not
  `Ushi Point Airfield`. The export is authoritative; do not "correct" it.

- **Airfield 3 is on Tinian, not Guam**, about 1.1 km from Ushi. Both belong to the North
  Field complex, which is historically right: Tinian numbered its strips 1 through 4.
- **No stand anywhere is 60x60, and none is flagged `large`.** Nothing heavy bases on this
  map by parking size. Ushi (17) and Airfield 3 (13) hold the most 40x40-or-better stands;
  Pagan has none at all. Per the 414th checklist addition, assert parking fit in a campaign's
  CI lock before basing anything big.

## The two terrains share a coordinate grid — proven

Load-bearing, because it is why the projection and the landmap were lifted from the modern
Marianas rather than re-derived.

The evidence that suggested it:

- `MissionGenerator/nodesMap.lua` is byte-identical on both terrains:
  `{ -296316.65625, -1072729.625, 1096283.375, 1252670.375 }`.
- Every town the two `map/towns.lua` files share carries identical lat/lon — Songsong on
  Rota is `14.139157, 145.139697` in both.

The evidence that settled it, from the airfield export itself:

- Every airfield projects onto its real island at its real coordinates. Isley comes out at
  **15.1196N 145.7262E** against a surveyed **15.119N 145.729E** for Aslito.
- **Pagan Airstrip exists on both terrains and lands 193 m apart.** A wrong central meridian
  or false easting would miss by kilometres.

So `tools/export_map_projection.py marianaislandswwii` was never run and does not need to be.
`projection.py` is `MarianaIslands`' file unchanged.

## The landmap is the modern Marianas landmap

`resources/theaters/marianaswwii/landmap.p` is `marianaislands/landmap.p` re-pickled under
shapely 2.x. Same grid, same islands, 6 land polys, 805 km2.

Two gaps, measured against every airfield's reference point:

- **Pagan is not in it, and Pagan Airstrip therefore sits in the sea zone — 313 km from the
  nearest land polygon.** The modern landmap stops at Saipan. **Do not base a campaign at
  Pagan** until the landmap is extended; the front line and navmesh will treat the whole
  island as ocean. This hole is inherited, not introduced — the modern Marianas terrain has
  had it all along.
- **Charon Kanoa's reference point is 21 m outside the nearest land polygon.** That is
  landmap coarseness at a beach airstrip, not a defect. The other nine are inside.

1944 shorelines also differ from 2020 — Apra Harbor's breakwaters, Tanapag's reclaimed land.
At the resolution the landmap is used for that is metres, and no front line runs there.

Fix either properly with GIS data rather than a hand-drawn polygon: shapefiles into
`unshipped_data/arcgis_maps/marianaswwii/{land,sea,exclusion}/`, then
`resources/tools/arcgis_landmap_import.py marianaswwii`.

## The substring trap

`ConflictTheater.landmap_path_for_terrain_name` matches theater directories by substring,
and `"marianaislands"` is a substring of `"marianaislandswwii"`. Without an explicit entry
the WWII theater silently loads **the modern Marianas landmap** — no error, wrong water.

Two things keep it correct and both must stay:

1. The theater directory is `marianaswwii`, not `marianaislandswwii`.
2. `theather_mapping` carries `"MarianaIslandsWWII": "marianaswwii"`.

## The icon folder is not the terrain name

Every other terrain installs under its own pydcs name. This one is theatre id
`MarianaIslandsWWII` in folder `MarianasWWII`, so `menu_thumbnail_dcs_relative_path` built a
path that does not exist and fell back to the shipped gif. `info.yaml` now takes an optional
`dcs_terrain_dir:` key for that case; `resources/theaters/marianaswwii/icon.gif` is the DCS
`Theme/icon.png` downscaled to the shipped 24x24.

---

## How the airfields were exported, and the two traps in doing it again

`airports.py` came from the Mission Editor stand-list dump described at the top of pydcs's
[`tools/airport_import.py`](https://github.com/dcs-retribution/pydcs/blob/master/tools/airport_import.py).
The helper that applies and reverts the patch is deliberately not in the repo — it hardcodes
an install path. Rebuild it from this section.

1. Patch `<DCS>\MissionEditor\modules\me_map_window.lua`: add `dumpairportdata()` and call it
   from `createAircraft()` under `pcall`. Back the file up first.
2. Start DCS, new mission on the terrain, place any aircraft. That fires the dump.
3. `tools/airport_import.py -t <terrain> <dumpfile>` in the pydcs checkout.
4. Restore the Lua file. A modified install file can trip DCS's integrity check.

**Trap 1 — the dump path must not contain backslashes.** A Windows path written straight into
the Lua source is a run of invalid escapes and a **syntax error that breaks the entire Mission
Editor**. Use forward slashes; `io.open` takes them on Windows. The first attempt here shipped
the broken form and was caught only by reading the patched file back before handing it over.

**Trap 2 — DCS loads the module once, at startup.** Patching a running DCS does nothing and
fails completely silently: the map loads, the aircraft places, no file appears, and `dcs.log`
says nothing, because ME `print` output was not observed reaching it. Restart DCS after
patching. Diagnose by file, not by log — write a step marker before touching any DCS API and
dump the `pcall` error to a second file, so one run distinguishes "never ran" from "ran and
threw".

---

## What DCS actually ships for 1944 in the Pacific

Checked against the install and pydcs on 2026-08-22, because three claims made from memory
during this work were wrong. The corrected picture:

| | |
|---|---|
| Japanese aircraft | **none.** `Japan().planes` is the generic list; no A6M, Ki- or G4M anywhere |
| Japanese ground | **8 real units** — Type 3 80mm, Type 88 75mm, Type 96 25mm and Type 94 25mm AA; Type 89 I Go and Type 98 Ke Ni tanks; Type 98 So Da APC; Type 94 truck |
| Japanese ships | **none.** No IJN hull of any kind |
| US carrier | **`Essex`, "Essex Class Carrier 1944"** — ships with DCS, with a `WW2Essex` preset group fielding USS Bennington (CV-20) |
| US Pacific aircraft | **F4U-1D Corsair ships.** No Hellcat, Avenger, Dauntless or B-29 |

DCS also ships **5 fictional IJN liveries for the Fw 190 A-8** and a **Japan livery for the
I-16**, so the stand-in path for red air is one ED built deliberately.

## Factions

Two campaign-specific factions, validated to load with **no dropped unit strings**:

- **`usa_1944_marianas.json`** — "USA 1944 (Marianas)". F4U-1D, P-47D-30 Early/Late, P-47D-40,
  A-20G, B-17G, C-47; the Essex, the LST and Ally Flak. The P-47D is not a stand-in: the 318th
  Fighter Group flew Thunderbolts off Aslito from 22 June 1944, and Aslito is Isley here. The
  P-51D is deliberately absent — it did not reach the Pacific until Iwo Jima in March 1945.
- **`japan_1944_marianas.json`** — "Japan 1944 (Marianas)". All eight real Japanese ground and
  AA types, no German armour. I-16 and Fw 190 A-8 in the shipped IJN liveries for air, German
  towed guns for field artillery, `Infantry Mauser 98` for infantry — DCS has no Japanese
  equivalent of any of the three. No navy. Its AA sites are the Japanese flak layout below,
  not generic placements.

The generic `japan_1944.json` and `usa_1944.json` are untouched; other campaigns use them.

**Silent-drop trap, hit during this work:** `Type_89_I_Go`'s pydcs name is `Tk Type 89 I Go`
but its Retribution yaml variant is `Type 89 I Go Tank`, and a faction naming the pydcs form
loads with the unit **silently missing**. Validate every faction string by loading the faction
and comparing counts; do not trust the pydcs name.

## The Essex is a real carrier, and its `HelicopterCarrier` class is a trigger

`resources/units/ships/Essex.yaml` declares `class: HelicopterCarrier`. **Do not "fix" that to
`AircraftCarrier`.** It is not a claim about the ship; it is the condition
`start_generator.transform_to_essex_if_needed` tests. A naval group whose units are
`HelicopterCarrier` and contain no `AircraftCarrier` gets its control point swapped for
`EssexCarrier`, and `EssexCarrier` subclasses **`Carrier`**, not `Lha`:

```python
class EssexCarrier(Carrier):
    def can_operate(self, aircraft: AircraftType) -> bool:
        return aircraft.lha_capable
```

So the result is a full carrier control point — carrier deck spawn, recovery heading, deck
decorations — that gates basing on `lha_capable` rather than `carrier_capable`, because a 1944
deck has no catapults. The ship itself is unambiguous in pydcs: `plane_num=90`,
`helicopter_num=1`, the most fixed-wing-dominant hull DCS ships. LHA-1 Tarawa, for contrast,
is 40 and 36.

Two consequences for a faction:

- **Hull names go in `helicopter_carrier_names`, not `carrier_names`**, because the unit class
  is still `HelicopterCarrier` when the faction loads. `allies_1944.json` already does this;
  `usa_1944_marianas.json` follows it. Names put in `carrier_names` are silently ignored.
- **Only `lha_capable` aircraft can base there.** Of this faction's seven types that is the
  **F4U-1D alone**, which is historically exact — Corsairs flew off carriers, Thunderbolts
  never did.

An earlier draft of this note claimed a Corsair on the Essex would take
`flightgroupspawner`'s VTOL path. That was wrong: the `is_vtol` line sits inside the
`isinstance(cp, Fob)` branch, and a carrier control point is handled by the
`isinstance(cp, NavalControlPoint)` branch above it. There is no VTOL involvement and no
in-game pass owed for it.

One real defect does follow from the classification, and is **not** fixed here: `theatergroup.py`
removes a sunk carrier's squadrons only when the dead unit's class is `AIRCRAFT_CARRIER`, so
sinking the Essex leaves its squadrons in place. Worth a separate change with its own test.

## The campaign: Operation Forager (1944)

`resources/campaigns/marianas_forager_1944.{yaml,miz}`, built by
`tools/build_marianas_forager_miz.py`. **Never hand-edit the miz** -- re-run the tool.
Locked by `tests/fourteenth/test_marianas_forager.py`.

15 June 1944. Blue holds the Charan Kanoa beach strip and a carrier; red holds the other
nine fields. Verified through the real `GameGenerator`: 11 control points, 5 squadrons all
fully manned, one front line (Charan Kanoa to Isley), 19 ground objects, three turns passed.

Topology, which the yaml carries rather than the miz:

- **Roads** (`supply_routes`): Saipan runs Charan Kanoa - Isley - Kagman - Marpi; Tinian runs
  Gurguan Point - Airfield 3 - Ushi; Guam runs Orote - Agana.
- **Sea** (`shipping_lanes`): Saipan-Tinian, Tinian-Rota, Rota-Guam. There is no road between
  islands, which is the point.

Four things went wrong building it, all now covered by the lock:

1. **Parking.** Blue was given 20 aircraft at a 12-stand beach strip. The second squadron
   generated with **zero aircraft and no error**. Charan Kanoa now carries one 8-ship
   squadron; air-to-air is the carrier's, which is how the CAP over Saipan was flown.
2. **Marker sentinels.** The AAA sites were authored as `Type_96_25mm_AA` -- the right gun and
   the wrong marker. `MizCampaignLoader` recognises only `AAA_UNIT_TYPES`, so all eight were
   silently dropped. `flak18` is the only WWII gun in that set. Strike targets are **statics**,
   not vehicles.
3. **The `theater:` key is the theater directory**, not the pydcs terrain name. `MarianasWWII`
   resolves; `MarianaIslandsWWII` does not.
4. **A colon inside an unquoted description** breaks the yaml parse. It is a block scalar.

Deferred, and neither blocks play:

- **Supply routes are approximate.** The corridor standard wants real 1944 roads via
  `tools/supply_route_geo.py`; these follow the island spines by eye.
- **Balance is unflown.** One blue field against nine is the history, not a tuning pass.

## Not done, and out of scope for the map itself

- **No campaign.** Nothing is authored on the terrain, so it does not appear in the New Game
  wizard and no changelog entry has been written. Supply routes on it must trace real 1944
  roads per the corridor standard — `tools/supply_route_geo.py` already carries Guam routes
  for the modern map and they transfer unchanged, since the grid is shared.
- **Pagan.** Airfield 11 is unusable until the landmap covers the island. See above.

## The Japanese flak site

`resources/layouts/anti_air/Japanese_Flak_Site.{miz,yaml}` plus the
`resources/groups/Japanese-Flak.yaml` preset group, wired into the red faction. Without it
red AA came from generic layouts, which is how `japan_1944.json` still works.

Thirteen units, laid out as a 1944 airfield battery rather than a ring of identical guns:

| Slot | Units | Placement | |
|---|---|---|---|
| 0 | 4x Type 88 75mm | inner ring, r=58 m | the IJA standard heavy AA gun |
| 1 | 2x Type 3 80mm | r=30 m | **optional** — the Navy's gun; an Army-only garrison has none |
| 2 | 6x Type 96 25mm | outer ring, r=102 m | the ubiquitous IJN light mount |
| 3 | 1x Type 94 truck | r=14 m | **optional**, `fill: false` — transport, not a firing slot |

Guns are headed outward from the battery centre.

**The `.miz` is generated, not drawn.** `build_japanese_flak_site.py` (scratchpad, not in the
repo — it hardcodes nothing but is a one-shot) authors it with pydcs so the geometry is
reviewable as radius/bearing numbers instead of editor clicks. Two things to know if it is
rebuilt: a fresh pydcs `Mission` carries **no CJTF countries**, so `Combined Joint Task Forces
Red` must be added to the red coalition first or `m.country(...)` returns `None`; and group
names must match the yaml exactly, or the loader silently drops the slot.

Verified headlessly: the layout loads with all 13 units placed, `ArmedForces` builds a
`Japanese Flak` force group for the faction — 13 groups against the generic faction's 12, so
nothing was swallowed by a `LayoutException` — and every slot resolves to exactly its intended
Japanese gun. `tests/test_layout_unit_types.py` locks the four `unit_types` strings.
