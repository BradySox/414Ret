# Module checklists

Adding support for a new **aircraft** or **terrain** module. Both are upstream standards,
adopted 2026-07-20, with the fork’s additions appended. Refresh when upstream revises them.

---

# Adding a new aircraft module

> **Adopted standard (2026-07-20).** This page is the upstream
> [New aircraft module checklist](https://github.com/dcs-retribution/dcs-retribution/wiki/New-aircraft-module-checklist),
> adopted as the 414th's own standard, with the fork's additional unit-data requirements
> appended. When upstream revises their page, refresh this one.

This checklist describes the work needed to add support for a new aircraft module in
Retribution. The same steps apply to both official modules and mods, though mods are
often held to a lower standard.

The content below the line can be copied into the feature request for tracking the work.
Copy the source rather than the rendered view to preserve formatting in the bug. Mods
should replace the first task (pydcs export) with the instructions in the
[Modded aircraft/unit support](Modded-Unit-Support) guide.

---

The tasks below are rated P0-P2 to indicate their importance:

Priority | Description
--- | ---
P0 | Required. Module will not function in Retribution without completing these tasks. _Must_ be addressed before shipping in a release.
P1 | Most modules complete these tasks. Commonly available features will not be available for the module if these tasks are skipped. Expect bug reports. Should be addressed before shipping in a release.
P2 | Many modules don't complete these tasks. Completing these tasks is required for complete functionality. Can be addressed in future releases.

- [ ] P0: pydcs export
  1. Export latest DCS data by following the instructions at the top of
     [pydcs_export.lua](https://github.com/dcs-retribution/pydcs/blob/master/tools/pydcs_export.lua)
  2. Send PR to pydcs (the [dcs-retribution/pydcs](https://github.com/dcs-retribution/pydcs) fork)
  3. Update Retribution to the latest DCS
- [ ] P0: Add unit data to `resources/units/aircraft`. See
  [the F-16C data](https://github.com/BradySox/414Ret/blob/main/resources/units/aircraft/F-16C_50.yaml)
  for a complete example.
  - [ ] P0: Price. Compare to similar aircraft to determine what the price should be.
  - [ ] P0: Variants. These are the names that will be used in the UI. At least one is
    required, but variants should be added for faction-specific types as necessary
    (e.g. a CF-18 variant for the Canadian F/A-18).
  - [ ] P1: Maximum range estimate. This is the maximum range from departure to target
    that the auto-planner will consider. The defaults are extremely conservative to
    avoid planning missions that will kill AI flights that run out of fuel.
  - [ ] P1: Information sections (`description`, `introduced`, `manufacturer`, `origin`,
    and `role`).
  - [ ] P1: Radio configuration. See
    [radios.py](https://github.com/BradySox/414Ret/blob/main/game/radio/radios.py) for
    a list of known radio types. Add new radios to that list if necessary. Necessary for
    default channel assignments and non-conflicting intra-flight frequency assignments.
  - [ ] P2: [Fuel consumption data](https://github.com/BradySox/414Ret/blob/main/docs/modding/fuel-consumption-measurement.md).
    Without this the kneeboard will not show minimum required fuel for each waypoint,
    and bingo/joker estimates may be extremely inaccurate. (**414th:** treat as P1 —
    see below.)
- [ ] P0: Flight planner priority lists. In the aircraft's
  `resources/units/aircraft/<id>.yaml` file under the `tasks` key, mapping each task
  name to an integer weight. A **higher integer is a higher priority**, so the planner
  prefers aircraft with the larger weight for a given task (e.g. an F-22 outranks an
  F-16 outranks a FW-190 for a fighter task). Omitting a task means the aircraft cannot
  fly it. Valid task-name strings are the `FlightType` values in
  [flighttype.py](https://github.com/BradySox/414Ret/blob/main/game/ato/flighttype.py)
  — the ones commonly weighted per aircraft are: `Anti-ship`, `BAI`, `BARCAP`, `CAS`,
  `DEAD`, `Escort`, `Fighter sweep`, `Intercept`, `OCA/Aircraft`, `OCA/Runway`, `SEAD`,
  `SEAD Escort`, `Strike`, `TARCAP` (plus support tasks like `AEW&C`, `Refueling`,
  `Recovery`, `Transport`, `Air Assault` for the relevant aircraft).
- [ ] P0: Default loadouts for all supported mission types.
- [ ] P0: Add to relevant factions.
- [ ] P0: Aircraft specific waypoint behavior. Most aircraft, such as those capable of a
  large (20+) quantity of waypoints or have no built-in waypoint navigation do not need
  custom behavior. Aircraft like the Viggen and F-14 where waypoints are constrained
  and/or have specific meanings will need to complete this task.
- [ ] P1: Banners/icons. Place banners in `resources/ui/units/aircrafts/banners/`
  (720x360 JPEG) and icons in `resources/ui/units/aircrafts/icons/` (91x24 JPEG).

## 414th additions

The fork holds unit data to a few standards beyond the upstream checklist — each learned
from a flown failure:

- [ ] P0: **Honest `max_range`.** The engine default (~150 NM) silently grounds any
  airframe based in the rear — the planner just never assigns it, with no error (the
  Desert Storm Tornado GR4 and F1CR both shipped grounded this way). Any airframe
  expected to fly from a rear field needs a real figure.
- [ ] P0: **YAML discipline + a headless load.** A missing `-` list marker dissolves a
  whole squadron silently (the Desert Storm MiG-25 lesson — six squadron substitutions
  traced to one). Load a campaign fielding the aircraft headlessly and count the
  squadrons before shipping.
- [ ] P1: **Task priorities per the rebalance rubric.** Don't guess weights — follow
  [`docs/dev/design/414th-aircraft-task-rebalance-rubric.md`](https://github.com/BradySox/414Ret/blob/main/docs/dev/design/414th-aircraft-task-rebalance-rubric.md).
  Watch task *aliases* too: an `air-to-ground` secondary includes DEAD/SEAD, which has
  fragged the wrong airframes at SAM rings (the Bombcat lesson).
- [ ] P1: **Recon and special classes.** Recon-capable airframes get a `TARPS` task
  weight. A drone must also be added to `UAV_DCS_IDS` in `game/data/units.py` (a drone
  is always filming — it banks BDA on whatever it overflies); a heavy bomber to
  `HEAVY_BOMBER_DCS_IDS` (Arc Light eligibility + low-level exemptions).
- [ ] P1: **Fuel consumption data** (upstream's P2 above): tanker tasking, the in-flight
  fuel sim, the kneeboard fuel ladder and the Payload tab's fuel-plan line all read it, so
  it is effectively P1 here. Without a `fuel:` block the two readouts fall back to a
  synthesised estimate; tanker tasking and the fuel sim get nothing.
- [ ] P1: **`date_gated_properties`** for era-defining cockpit properties (JHMCS-class
  helmet sights): the gate block lives in the aircraft's own yaml so a period campaign
  clamps them automatically.
- [ ] P2: **Navy jets:** add Hornet/Tomcat-family types to `MODEX_AIRCRAFT_IDS`
  (`game/missiongenerator/aircraft/modex.py`) so squadrons wear sequenced board numbers.
- [ ] P2: **Native DTC:** if the module ships a DCS Data Transfer Cartridge descriptor
  (F/A-18C and F-16C today; CH-47F and MiG-29 ship descriptors with no builder yet), add
  a cartridge builder under `game/missiongenerator/dtc/` so the jet spawns with the
  mission in the avionics.

---

# Adding a new terrain module

> **Adopted standard (2026-07-20).** This page is the upstream
> [New terrain module checklist](https://github.com/dcs-retribution/dcs-retribution/wiki/New-terrain-module-checklist),
> adopted as the 414th's own standard, with the fork's additions appended. When upstream
> revises their page, refresh this one.

This checklist describes the work needed to add support for a new terrain module in
Retribution.

The content below the line can be copied into the feature request for tracking the work.
Copy the source rather than the rendered view to preserve formatting in the bug.

---

- [ ] pydcs export
  1. Export latest DCS data
     1. [airport_import.py](https://github.com/dcs-retribution/pydcs/blob/master/tools/airport_import.py)
     1. [coord_export.lua](https://github.com/dcs-retribution/pydcs/blob/master/tools/coord_export.lua)
     1. [export_map_projection.py](https://github.com/dcs-retribution/pydcs/blob/master/tools/export_map_projection.py)
  2. Send PR to pydcs (the [dcs-retribution/pydcs](https://github.com/dcs-retribution/pydcs) fork)
  3. Update Retribution to the latest DCS
- [ ] Add beacons for the new terrain
  1. The beacons file can be generated by running
     `resources/tools/import_beacons.py <DCS_PATH>`, where `<DCS_PATH>` is the required
     positional path to your DCS installation (running it without the argument produces
     a usage error).
  2. The beacons file needs to be added to `resources/dcs/beacons/NAME_OF_TERRAIN.json`
  3. You can use the existing files as a reference/template to ensure the correct output
  4. If the pydcs terrain `.name` (used to look up the beacon JSON file) differs from
     the beacon filename, add an entry to `beacons_filename_mapper` in
     `game/dcs/beacons.py` (for example, `sinaimap` -> `sinai` and `germanycw` ->
     `germanycoldwar`).
- [ ] Add the terrain info to `resources/theaters/NAME_OF_TERRAIN/info.yaml`
- [ ] Add the terrain icon to `resources/theaters/NAME_OF_TERRAIN/icon.gif`
  1. This icon will be used only as a fallback. By default, Retribution uses the icon
     from the user's DCS installation. However, the DCS installation will only have this
     icon in case the terrain in question is installed. The fallback is needed in order
     for icons to be displayed on all terrains, including the ones which the user might
     not own or have installed.
- [ ] Register the terrain in the theater loader
  1. Add the new terrain's pydcs terrain class (and its import) to `ALL_TERRAINS` in
     `game/theater/theaterloader.py`. `TERRAINS_BY_NAME` is derived from this list, so
     if the terrain is missing here, loading its `info.yaml` will raise a `KeyError`.
- [ ] Generate terrain landmap
  - [ ] Option 2 (recommended): Generate the zones from GIS data
    1. [Creating shape files in QGIS for map data](Creating-shape-files-in-QGIS-for-map-data)
    2. Once GIS maps have been added to `unshipped_data/arcgis_maps`, run
       `resources/tools/arcgis_landmap_import.py <theater_name>`. This writes the
       landmap to the correct location (`resources/theaters/<name>/landmap.p`) via
       `TheaterLoader.landmap_path`.
  - [ ] Option 1 (legacy / manual): Define sea zones, inclusion zones, exclusion zones
    in the mission editor.
    1. Exclusion zones are defined by the waypoints of USA F-15C plane groups
    2. Inclusion zones are defined by the waypoints of any other USA plane groups
    3. Sea zones are defined by the waypoints of USA ship groups
    4. After the mission is completed and saved in the correct folder
       (`resources/tools/NAME_OF_TERRAIN_terrain.miz`), add the new terrain's short-name
       to the hardcoded list in `resources/tools/generate_landmap.py` and run it.
    5. **Note:** `generate_landmap.py` writes its output to `resources/<name>landmap.p`
       (one level up from the tools directory), **not** to the theater subdirectory the
       loader reads from. You must manually move the generated file to
       `resources/theaters/<name>/landmap.p`, otherwise it will never be loaded. Prefer
       Option 2, which places the file correctly.

## 414th additions

- [ ] **Campaigns on the new terrain author real corridors.** When the first campaign
  comes to the terrain, its `supply_routes:` must trace the real driveable roads —
  `tools/supply_route_geo.py` converts real road lat/lon to terrain XY on
  real-world-coordinate maps (see the supply-lines standard in
  [Campaign maintenance](Campaign-maintenance)).
- [ ] **Optional — local chart base layer.** A locally-tiled chart of the DCS terrain
  (e.g. a community GeoTIFF) can be added as a campaign-map base layer with
  `tools/tile_geotiff.py`. Local only, never bundled or committed — community-chart
  copyright (see [The Retribution UI](The-Retribution-UI)).
- [ ] **Check parking before basing plans.** Slot dimensions decide what can actually
  base where (the Desert Storm lesson: the Iraq map has zero 60x60 heavy stands west of
  Baghdad, so big wings genuinely cannot base forward there). Campaigns on the new
  terrain should assert parking fit in their CI lock when they base large airframes.
