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
  [the F-16C data](https://github.com/bradyccox/414Ret/blob/main/resources/units/aircraft/F-16C_50.yaml)
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
    [radios.py](https://github.com/bradyccox/414Ret/blob/main/game/radio/radios.py) for
    a list of known radio types. Add new radios to that list if necessary. Necessary for
    default channel assignments and non-conflicting intra-flight frequency assignments.
  - [ ] P2: [Fuel consumption data](https://github.com/bradyccox/414Ret/blob/main/docs/modding/fuel-consumption-measurement.md).
    Without this the kneeboard will not show minimum required fuel for each waypoint,
    and bingo/joker estimates may be extremely inaccurate. (**414th:** treat as P1 —
    see below.)
- [ ] P0: Flight planner priority lists. In the aircraft's
  `resources/units/aircraft/<id>.yaml` file under the `tasks` key, mapping each task
  name to an integer weight. A **higher integer is a higher priority**, so the planner
  prefers aircraft with the larger weight for a given task (e.g. an F-22 outranks an
  F-16 outranks a FW-190 for a fighter task). Omitting a task means the aircraft cannot
  fly it. Valid task-name strings are the `FlightType` values in
  [flighttype.py](https://github.com/bradyccox/414Ret/blob/main/game/ato/flighttype.py)
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
  [`docs/dev/design/414th-aircraft-task-rebalance-rubric.md`](https://github.com/bradyccox/414Ret/blob/main/docs/dev/design/414th-aircraft-task-rebalance-rubric.md).
  Watch task *aliases* too: an `air-to-ground` secondary includes DEAD/SEAD, which has
  fragged the wrong airframes at SAM rings (the Bombcat lesson).
- [ ] P1: **Recon and special classes.** Recon-capable airframes get a `TARPS` task
  weight. A drone must also be added to `UAV_DCS_IDS` in `game/data/units.py` (a drone
  is always filming — it banks BDA on whatever it overflies); a heavy bomber to
  `HEAVY_BOMBER_DCS_IDS` (Arc Light eligibility + low-level exemptions).
- [ ] P1: **Fuel consumption data** (upstream's P2 above): the fork's route-aware
  fuel-tank planning and the kneeboard fuel ladder read it, so it is effectively P1
  here.
- [ ] P1: **`date_gated_properties`** for era-defining cockpit properties (JHMCS-class
  helmet sights): the gate block lives in the aircraft's own yaml so a period campaign
  clamps them automatically.
- [ ] P2: **Navy jets:** add Hornet/Tomcat-family types to `MODEX_AIRCRAFT_IDS`
  (`game/missiongenerator/aircraft/modex.py`) so squadrons wear sequenced board numbers.
- [ ] P2: **Native DTC:** if the module ships a DCS Data Transfer Cartridge descriptor
  (F/A-18C and F-16C today; CH-47F and MiG-29 ship descriptors with no builder yet), add
  a cartridge builder under `game/missiongenerator/dtc/` so the jet spawns with the
  mission in the avionics.
