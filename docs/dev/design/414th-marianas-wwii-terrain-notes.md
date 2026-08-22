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

## Not done, and out of scope for the map itself

- **No campaign.** Nothing is authored on the terrain, so it does not appear in the New Game
  wizard and no changelog entry has been written. Supply routes on it must trace real 1944
  roads per the corridor standard — `tools/supply_route_geo.py` already carries Guam routes
  for the modern map and they transfer unchanged, since the grid is shared.
- **Factions.** `japan_1944.json` fields an I-16 and an Fw 190 A-8 as stand-ins; DCS ships no
  Japanese airframe. `usa_1944.json` is a western-front army — P-47s, P-51s, B-17s, no
  Corsairs or Hellcats. A Pacific campaign needs both reworked.
- **Carriers.** Operation Forager is a carrier war and DCS ships no WWII US carrier.
- **Pagan.** Airfield 11 is unusable until the landmap covers the island. See above.
