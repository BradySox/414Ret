# Marianas WWII terrain support

Adding `MarianaIslandsWWII` (DCS install folder `MarianasWWII`, Early Access) to the fork.

Status 2026-08-22: **wiring built, airfield data blocked on a DCS export.** The terrain
loads, projects, resolves its landmap and appears in the theater list. It has zero
airfields until the Mission Editor stand-list export below is run, so no mission can be
generated on it yet.

Precedent followed: Kola, Afghanistan, Iraq and Germany Cold War, per
[Module Checklists](../wiki/Module-Checklists.md).

---

## What the map is

- Theatre id `MarianaIslandsWWII`; install folder `E:\DCS World\Mods\terrains\MarianasWWII`.
- Guam, Rota, Tinian, Saipan, Pagan. Frozen at 15 June – 10 August 1944 (Operation Forager).
- **No beacons at all.** `beacons.lua` declares `beacons = {}` — same as Normandy and The
  Channel. `resources/dcs/beacons/marianaislandswwii.json` is `{}` and that is correct, not
  a stub.
- 11 airfields, ids taken from their `radio.lua` `radioId` (`airfieldN_0` → id N):

  | id | Airfield | Island | HF | VHF low | VHF high | UHF |
  |---|---|---|---|---|---|---|
  | 1 | Agana Airfield | Guam | 3.800 | 38.500 | 118.100 | 250.100 |
  | 2 | Orote Airfield | Guam | 3.825 | 38.550 | 118.150 | 250.150 |
  | 3 | Airfield 3 | Guam | 3.850 | 38.600 | 118.200 | 250.200 |
  | 4 | Charon Kanoa Strip | Saipan | 3.875 | 38.650 | 118.250 | 250.250 |
  | 5 | Gurguan Point Airfield | Tinian | 3.900 | 38.700 | 118.300 | 250.300 |
  | 6 | Isley Field | Saipan | 3.925 | 38.750 | 118.350 | 250.350 |
  | 7 | Kagman Point Airfield | Saipan | 3.950 | 38.800 | 118.400 | 250.400 |
  | 8 | Marpi Point Strip | Saipan | 3.975 | 38.850 | 118.450 | 250.450 |
  | 9 | Rota Airfield | Rota | 4.000 | 38.900 | 118.500 | 250.500 |
  | 10 | Ushi Point Airfield | Tinian | 3.750 | 38.400 | 118.000 | 250.000 |
  | 11 | Pagan Airstrip | Pagan | 3.775 | 38.450 | 118.050 | 250.050 |

  MHz. Read out of the terrain's own `radio.lua`; use it to check the export landed right.

## The two terrains share a coordinate grid

Load-bearing, because it is why the projection and the landmap could be lifted from the
modern Marianas rather than re-derived.

- `MissionGenerator/nodesMap.lua` is byte-identical on both terrains:
  `{ -296316.65625, -1072729.625, 1096283.375, 1252670.375 }`.
- Every town the two `map/towns.lua` files share carries identical lat/lon — Songsong on
  Rota is `14.139157, 145.139697` in both.

**Still unproven, and cheap to prove.** Run `tools/export_map_projection.py marianaislandswwii`
in the pydcs checkout; it errors out per-airport if the parameters are wrong. Do that before
any campaign is authored on the terrain.

## The landmap is the modern Marianas landmap

`resources/theaters/marianaswwii/landmap.p` is `marianaislands/landmap.p` re-pickled under
shapely 2.x. Same grid, same four islands, 6 land polys / 805 km².

Known gaps, neither blocking:

- **Pagan is not in it.** The modern landmap stops at Saipan; Pagan Airstrip is ~430 km
  north of the inclusion bounds. A campaign that bases at Pagan needs the landmap extended.
- **1944 shorelines are not 2020 shorelines.** Apra Harbor's breakwaters and Tanapag's
  reclaimed land differ. At the resolution the landmap is used for — land/sea for the front
  line and the navmesh — this is metres, and no front line runs there.

Redo it properly from GIS data if either bites: shapefiles into
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
`Theme/icon.png` downscaled to the shipped 24×24.

---

## Runbook — the DCS-side export (needs DCS, ~30 min)

Everything above is done. This is what is left, and it cannot be done headlessly.

### 1. Airfields — `airports.py`

1. Open `<DCS>\MissionEditor\modules\me_map_window.lua`. **Back it up first.**
2. Paste the `dumpairportdata()` function from the docstring at the top of
   [`tools/airport_import.py`](https://github.com/dcs-retribution/pydcs/blob/master/tools/airport_import.py),
   and call it from `createAircraft()`.
3. Start DCS, new mission on **Marianas WWII**, place any aircraft. That fires the dump.
   If clicking places nothing, the script is broken — read `dcs.log`.
4. `C:\standlist.lua` is written. Then, in the pydcs checkout:

   ```
   tools/airport_import.py -t marianaislandswwii C:\standlist.lua
   ```

5. Restore `me_map_window.lua`.
6. Check the result against the frequency table above — all 11 airfields, ids 1–11.

### 2. Projection — confirm `projection.py`

```
tools/export_map_projection.py --dcs "E:\DCS World" marianaislandswwii
```

It writes a mission to Saved Games, waits for you to run it, then recomputes the parameters
and prints a per-airport error if they are wrong. Expect it to reproduce the file already
committed. If it does not, the shared-grid claim above is wrong and the landmap must be
regenerated too.

### 3. Bump the pin

`requirements.txt` points `pydcs` at a commit. Bump it once the pydcs branch is merged or
pushed. Editing `requirements.txt` does **not** touch `.venv` — reinstall, or local mypy
goes falsely green while the app fails on "Could not find aircraft X".

---

## Not done, and out of scope for the map itself

- **Factions.** `japan_1944.json` exists but fields an I-16 and an Fw 190 A-8 as stand-ins —
  there is no WW2 asset pack requirement and no Japanese airframe in DCS. `usa_1944.json` is
  a western-front army: P-47s, P-51s, B-17s, no Corsairs or Hellcats. A Pacific campaign
  needs both reworked.
- **Carriers.** Operation Forager is a carrier war and DCS ships no WWII US carrier.
- **A campaign.** None authored. Supply routes on this terrain must trace real 1944 roads
  per the corridor standard — `tools/supply_route_geo.py` already carries Guam routes for
  the modern map and they transfer, since the grid is shared.
