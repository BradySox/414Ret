# 414th features — deep dive

The per-feature engineering internals for the 414th's additions on top of upstream
DCS Retribution. [`CLAUDE.md`](../../CLAUDE.md) is the clean map and points here; this
file is the deep version for the next coding session — file paths, hard-won gotchas,
tests, and the deferred work.

Design notes for individual features live under [`docs/dev/design/`](design/) and are
linked from each section below. Read those before touching the corresponding code.

---

## 1. QRA intercept reserve

Retribution now uses the upstream PR `#782` QRA path. The old 414th ramp-scramble system
is legacy only and should not be extended.

- Squadron model: `game/squadrons/squadron.py` stores `intercept_reserve` per squadron.
  `untasked_aircraft` is now `owned_aircraft - intercept_reserve`, so the auto-planner
  leaves those aircraft available for QRA instead of fragging them.
- Reserve helpers: `game/squadrons/intercept_reserve.py` owns clamping, default seeding,
  live-campaign repropagation when coalition doctrine defaults change, and
  `qra_scramble_grouping()`.
- Distributed-QRA scramble size: `qra_scramble_grouping()` rolls **1 ship 75% / 2 ships
  25%** (`QRA_SINGLE_SHIP_PROBABILITY`) per fielded QRA squadron, carried on each
  `InterceptEntry.grouping` and applied as `SetSquadronGrouping` in `intercept-config.lua`
  (was a hardcoded 2-ship). Intent: many alert bases each putting up a *small* response so
  a raid draws interceptors from several directions, rather than one base scrambling a big
  formation. MOOSE grouping is per-squadron (fixed for the mission, re-rolled each turn),
  so the per-launch single/pair mix emerges across the theater's alert bases; true
  per-scramble variation would need a dispatcher GCI hook (deferred). Lua falls back to 2
  if an old save omits the field. Tests: `tests/squadrons/test_intercept_reserve.py`.
- Campaign doctrine: `game/settings/settings.py` exposes
  `ownfor_default_qra_reserve`, `opfor_default_qra_reserve`,
  `qra_gci_max_radius_nm`, `qra_engagement_range_nm`, and `qra_comms_enabled`.
  Defaults are a **base-defense** posture (lowered after playtest feedback that QRA
  screened forward over the FLOT): `qra_gci_max_radius_nm` 100→**60** (scramble only when
  a raid closes within 60 NM) and `qra_engagement_range_nm` 60→**38** (interceptors chase
  less far). The Lua fallbacks in `intercept-config.lua` match. These are live doctrine
  settings, so existing campaigns can re-tune them on the Campaign Doctrine page.
- Mission generation: `game/missiongenerator/aircraft/aircraftgenerator.py`
  `spawn_intercept_templates()` emits late-activated parked template groups and
  appends `mission_data.intercept_entries`.
- Template spawn details: `game/missiongenerator/aircraft/flightgroupspawner.py`
  `create_intercept_template()` places the parked template and seeds
  `QRA_AIRSTART_SPEED_MS` onto its waypoints (en-route pace only).
- Air-spawn profile (2026-06-21): waypoint speed does NOT set the spawn-*instant*
  velocity — Moose air-spawns the cloned parking template at ~0 kt, so jets spawned
  stalled at altitude and dove ~4,600 ft clawing back airspeed (an Su-27 nearly hit
  the ground at Vaziani, Tacview 2026-06-20). `intercept-config.lua` now forces a real
  scramble speed via `SPAWN:InitSpeedKnots` (`SCRAMBLE_SPEED_KT`, applied to the
  spawned units in Moose `SpawnWithIndex`) and a terrain-relative LOW spawn altitude
  per base via `SetSquadronTakeoffInAirAltitude` (field elevation + `SCRAMBLE_AGL_M`),
  replacing the global absolute-MSL `SetDefaultTakeoffInAirAltitude` that was unsafe at
  high-elevation fields. Both are tunable; in-game pass ☑ VERIFIED 2026-06-24 (A1,
  Tacview) — scrambled MiG-29As air-spawned at ~750 m AGL / 240–510 kt and climbed
  under control, no stall or ground-clawing dive.
- Lua/config path: `game/missiongenerator/interceptluadata.py` populates
  `dcsRetribution.Intercept`, and `resources/plugins/intercept/intercept-config.lua`
  instantiates Moose `AI_A2A_DISPATCHER` behavior from that table.
- Results/debrief: `resources/plugins/base/dcs_retribution.lua` writes
  `intercept_survivors`; `game/debriefing.py` and
  `game/sim/missionresultsprocessor.py` reconcile those survivor counts back into
  squadron aircraft and pilot losses.
- UI touchpoints: QRA reserve editing and display now live in
  `qt_ui/windows/AirWingConfigurationDialog.py`,
  `qt_ui/windows/SquadronDialog.py`,
  `qt_ui/windows/basemenu/airfield/QAircraftRecruitmentMenu.py`,
  `qt_ui/windows/basemenu/QBaseMenu2.py`, and the debrief/settings windows.

Legacy note: the old ramp-scramble system has been fully retired — the upstream PR #782
dispatcher above is the only live QRA path. Both the `reactive_scramble.lua` script and the
`FlightType.SCRAMBLE` enum (plus its `Scramble:` aircraft-task weights and `- Scramble`
squadron mission-type entries in `resources/units|squadrons|campaigns/*.yaml`) have been
removed. SCRAMBLE always behaved as a BARCAP, so old saves are migrated SCRAMBLE -> BARCAP
in two places: `FlightType._missing_` (runtime lookups) and `persistency.py`
`_handle_flight_type` (the unpickler). `FlightType.INTERCEPTION` is the only remaining
legacy A2A type and is kept for upstream save compatibility.

---

## 2. JAMMING flight type — C-130J EW/ISR

A ~1,950-line script (`c130j_mission_systems.lua`) turning the C-130J into an
EC-130H Compass Call (EW) + RC-130H Rivet Joint (ISR) platform. EW: area,
directional, and spot jamming, plus range-banded per-tick missile spoofing (with
a ~3 nm arming distance so it never spoofs a missile still next to its launcher).
ISR: altitude-gated radar detection, up to 3 simultaneous ELINT tracks with
progressive lock (60-360 s by range), F10 map marks, Bullseye reporting, and an
ELINT-Lock coalition alert. COORD: an EW/ISR handoff brief deliverable to any
selected friendly group.

- Enum: `game/ato/flighttype.py` (`FlightType.JAMMING` ->
  `AirEntity.ELECTRONIC_COMBAT_JAMMER`).
- Behavior: `game/missiongenerator/aircraft/aircraftbehavior.py` `configure_jamming()`
  -- AWACS task + `AewcFlightPlan` standoff racetrack outside the threat zone +
  `WEAPON_HOLD` ROE. Runtime EW/ISR is driven by the Lua, not the planner.
- Spawn fallback: `game/missiongenerator/aircraft/flightgroupspawner.py` tries RUNWAY
  start when no parking is available.
- Script loading: registered as a normal plugin (`c130j` in `plugins.json`,
  `scriptsWorkOrders` in `resources/plugins/c130j/plugin.json`) since the
  2026-06-11 refactor.
- Plugin script: `resources/plugins/c130j/c130j_mission_systems.lua` (+ `plugin.json`).
- Loadout/package wiring: `game/ato/loadouts.py`, `game/ato/package.py`,
  `game/theater/missiontarget.py`.
- Design note: `docs/dev/design/414th-c130-ew-isr-notes.md`.

**Retired generic EW plugin:** the old `ewrj` / "EW Jammer Script 2.1" plugin
was removed. The C-130J JAMMING flight supersedes it for 414th scripted EW.
Do not re-add `ewrj` to `resources/plugins/plugins.json` or restore the old
`EWJamming` / `startEWjamm` / `startIAdefjamming` Python hooks. F-16/A-10 ECM
pods should not create the old generic F10 "Jammer menu"; only the C-130J
Mission Systems plugin owns 414th scripted jamming now. Legacy saved `ewrj`
settings are purged on load in `game/settings/settings.py`.

**C-130 EW hard constraints (carried over from the standalone ME script):** do NOT toggle
SAM radar emissions (`enableEmission(false)` crashed DCS - suppression is ROE WEAPON_HOLD
only); the burn-through model intentionally RAISES jam probability with distance; spot
jamming has flat altitude-independent range; the missile-spoof curve is intentionally steep
at close range. Don't "fix" these.

---

## 3. TARPS photo-reconnaissance + BDA fog-of-war

`FlightType.TARPS` adds player-flown F-14 recon. All F-14 variants carry the
`{F14-TARPS}` pod on station 6 (editor-verified). The auto-planner appends a single
TARPS sortie to Strike / DEAD packages when `auto_add_tarps_recon` is enabled and a
TARPS-capable squadron is available.

- Enum + behavior: `game/ato/flighttype.py`, `game/missiongenerator/aircraft/aircraftbehavior.py`
  `configure_tarps()` — single overflight waypoint ~5 min behind the strikers.
- Flight plan: `game/ato/flightplans/tarps.py` uses `FlightWaypointType.INGRESS_RECON`
  (NOT `INGRESS_STRIKE`) so the weaponless recon bird gets **no Bombing tasks** on its
  ingress — `INGRESS_STRIKE` dumped one Bombing task per target-group unit onto the
  ingress, making the AI fly an aborting attack pattern and never cleanly overfly.
  `INGRESS_RECON` → `ReconIngressBuilder` (no attack tasks,
  `game/missiongenerator/aircraft/waypoints/reconingress.py`); the target waypoint is a
  **flyover** (`WaypointBuilder.recon_area`, `flyover=True`) so the AI actually crosses
  the target instead of turning back at the IP. (Player-only target waypoints are
  filtered for AI, so without the flyover the AI never reaches the target.)
- Auto-planner: `game/commander/packagefulfiller.py` `_try_add_tarps_recon()` with
  explicit debug logging for every skip reason.
- Aircraft: `TARPS: 700` task priority in `resources/units/aircraft/F-14*.yaml`;
  payloads in `resources/customized_payloads/F-14*.lua`. The `Retribution TARPS` payload
  carries `{F14-TARPS}` on station 6 (station 5 clean) plus a per-variant self-defense
  fit, verified from the `Aerial-1/2/3` groups in `Tues test 1.miz`: F-14B = AIM-54A
  (Mk60 L / Mk47 R), F-14A-135-GR-Early = AIM-54A (Mk47 L/R), F-14A-135-GR = AIM-7M, all
  with AIM-9L wingtips. **CLSIDs must be current** — stale ones (`{SHOULDER AIM-7MH}`,
  `{LAU-138 wtip - AIM-9M}`) made DCS reject the whole loadout on load and silently drop
  the TARPS pod with it. The vanilla `F-14A.lua` still uses the old GUID-form loadout.
- Tests: `tests/test_tarps_recon.py`.

**Visibility / recon fog** — one viewer-aware layer drives two player-facing fog rules.
AI planning and threat math always use ground truth (`viewer=None`); only the human
(BLUE) map/UI are fogged.

The unified layer (replaced the old sprawling `_for_player`/`_for` method twins — collapse
finished, do not reintroduce twins):
- `TheaterUnit.alive_for(viewer=None)` — `None`/friendly → truth; enemy → `alive_at_last_recon`
  (post-strike BDA damage lag). `sync_confirmed_status()` snaps it to truth.
- `TheaterGroundObject.known_for(viewer=None)` — `None`/friendly → True; enemy → the sticky
  `discovered_by_player` flag (gated by the `recon_intel_fog` setting).
- Every accessor takes `viewer: Optional[Player] = None` (truth by default): unit
  `threat_range`/`detection_range`, group `alive_units`/`max_threat_range`/`max_detection_range`,
  TGO `is_dead`/`dead_units`/`alive_unit_count`/`max_threat_range`/`max_detection_range`/
  `sidc_status_for`/`sidc_for`. `display_name`/`short_name` keep a truth `@property` that
  delegates to the `*_for(viewer)` worker (they had too many truth callers to convert).
  Files: `game/theater/theatergroup.py`, `game/theater/theatergroundobject.py`.

*Two fog rules on that layer:*
1. **BDA damage lag** (`alive_for`): struck *enemy* units keep showing alive until recon
   confirms the kill. `game/sim/missionresultsprocessor.py` applies true kills, then
   `sync_confirmed_status()` only on friendly TGOs and enemy TGOs reconned this turn
   (TARPS package targets + actual TARS captures).
2. **Recon intel-fog** (`known_for`): a new *enemy* site shows on the map as a targetable
   marker (position/category/allegiance) but its composition + threat/detection rings stay
   hidden until **attacked, scouted, or destroyed**. `discovered_by_player` is flipped
   (sticky, enemy-only) by `reveal_discovered_sites()` in `missionresultsprocessor.py` from
   the struck / reconned / TARS / attacked sets. `__setstate__` migrates old saves to
   `discovered_by_player=True` (existing campaigns stay revealed; the fog is felt on new
   campaigns). Master switch: `recon_intel_fog` setting (default ON, Campaign Doctrine).

- Consumers gate at the edge: `game/server/tgos/models.py` emits a fogged payload (empty
  rings, hidden units) when `not known_for(BLUE)`; `qt_ui/windows/groundobject/QGroundObjectMenu.py`
  + `QBuildingInfo.py` pass `self.viewer` and show "Not yet scouted — composition unknown".
- Tests: `tests/test_bda_tarps_reveal.py` (damage lag), `tests/test_recon_intel_fog.py`
  (discovery gate, migration, setting).

A third gate rides the same viewer-aware layer: `TheaterGroundObject.hidden_on_player_map(viewer)`
fully hides enemy command posts for the SCAR commander-capture feature (gated by
`scar_command_post_intel`, default ON for new campaigns) — see
[§15](#15-scar--strike-coordination-and-reconnaissance-flight-type--scenario-plugin).

**Overview reveal toggle ("show the real picture").** A single runtime switch that forces
every player-facing fog rule above to resolve to ground truth, for whoever is looking. It
exploits the fact that all three player-facing fog rules funnel through exactly three leaf
methods, so it is implemented as a one-line short-circuit in each rather than re-threading
viewers through ~15 call sites:

- Flag: `game/theater/fogofwar.py` — `fog_revealed()` / `set_fog_revealed()` over a
  process-global `bool`. **Transient by design**: never pickled, so a save can never carry a
  god-view, and a shared campaign can't leak one. The module imports nothing (cycle-free) so
  the theater layer can pull it in freely.
- Chokepoints: `TheaterUnit.alive_for`, `TheaterGroundObject.known_for`, and
  `hidden_on_player_map` each gained `or fog_revealed()` in their `viewer is None …` guard.
  Because `display_name_for`/`short_name_for`, unit `threat_range`/`detection_range`, group
  `alive_units`/`max_threat_range`/`max_detection_range`, TGO `is_dead`/`dead_units`/
  `sidc_status_for`, and `ThreatZones.for_faction` (`known_for` gate + `max_threat_range`) all
  delegate to those three leaves, the toggle un-fogs the **entire** map render path
  (`TgoJs`, the red `ThreatZonesJs`, `IadsConnectionJs`) **and** the intel dialogs at once —
  with **zero server-model changes**, since those still pass `Player.BLUE` and the leaves
  short-circuit internally. AI/planner/threat math pass `viewer=None` and are unaffected.
- UI: a **"Reveal fog of war"** checkbox in the custom map layers panel
  (`client/src/components/maplayers/MapLayersControl.tsx`, "Enemy intel" group; see §18), not
  the Qt chrome. It is driven by a state `useEffect`, **not** a Leaflet `add`/`remove` layer —
  that approach proved unreliable: on unmount react-leaflet tears the layer down without firing
  `remove`, so unchecking left the overview stuck on. The effect `PUT`s
  `/fog-of-war/reveal?revealed=…` (`game/server/fogofwar/routes.py`, registered in
  `game/server/app.py`) then calls `reloadGameState(dispatch, true)` — a **no-recenter** full
  re-pull of `/game`, whose `tgos`/`iads_network`/`threat_zones` are rebuilt through the (now
  short-circuiting) fog paths, so composition, rings, and hidden command posts appear — and
  re-hide when unchecked, because `TgoJs.all_in_game` re-applies the `hidden_on_player_map`
  filter. Defaults off; the panel persists other layer choices to localStorage but deliberately
  excludes the fog overview, so it is never restored on load.
- Note: it lives entirely in the React client, so it needs the rebuilt bundle — CI's
  `npm run build` ships it in the `latest` release. The Python chokepoints + the
  `/fog-of-war/reveal` endpoint are covered by the existing fog tests
  (`tests/test_recon_intel_fog.py`, `tests/test_bda_tarps_reveal.py`) and a route test
  (`tests/server/test_fogofwar_route.py`). The client panel has no JS test (the project ships
  none for the map layers).

---

## 4. UI transparency improvements

Several player-facing dialogs were reworked to surface planner reasoning instead of
just raw data.

**Target Intel panel** (`qt_ui/windows/groundobject/QGroundObjectMenu.py`):
Every ground-object dialog now opens with a read-only `Target Intel` group showing
target type, allegiance, mission types valid against it, known live/destroyed unit
counts, detection/threat range, IADS membership, hide-on-MFD flag, and
capturable/purchasable status.

**Mission Impact summary** (`qt_ui/windows/QDebriefingWindow.py`):
Debrief prepends a `Mission Impact` group above the casualty tables: mission
end-state, bases captured/lost, runway damage, and loss counts for both sides.

**Package context bar** (`qt_ui/windows/mission/QPackageDialog.py`):
The package summary line now renders primary task, flight count, player slots,
actual TOT (e.g. `TOT: 15:32:00 (ASAP)`), and departure bases in one line.

**Flight-creation context** (`qt_ui/windows/mission/flight/QFlightCreator.py`,
`qt_ui/windows/mission/flight/SquadronSelector.py`):
A live summary explains what the selected task/aircraft/squadron choice means.
Squadron hover text shows primary role, auto-assignability, spare aircraft, base,
and distance to target.

**Building card cleanup** (`qt_ui/windows/groundobject/QBuildingInfo.py`):
`SceneryUnit.icon` always returns `"missing"`, so every scenery building previously
loaded `missing.png` (which contains the literal text "Missing Recon Picture").
Cards now skip the image widget when no real icon exists and show a compact
name + value layout instead.

**Flight altitude editing** (`qt_ui/windows/mission/flight/waypoints/QFlightWaypointTab.py`,
`QFlightWaypointList.py`):
Changing a flight's cruise altitude used to mean editing every waypoint's `Alt (ft)`
cell one at a time, and that cell's spin box stepped by the `QDoubleSpinBox` default of
**1 ft** — useless arrows. Two fixes: (1) an `Altitude` block at the top of the
Waypoints tab's action column — a 1000-ft-step spin box + **Apply to all** that writes one
MSL altitude onto every *en-route* waypoint at once (`on_apply_bulk_altitude()`;
`BULK_ALTITUDE_SKIP_TYPES` + the `RADIO` check exempt takeoff/landing/descent/AGL/Bullseye,
so only cruise/patrol/ingress legs move; the spinner seeds from the highest planned
en-route altitude). (2) the per-waypoint `Alt (ft)` cell editor now steps by 1000 ft and
drops decimals. Per-waypoint editing is untouched, so a low-level ingress leg can still be
hand-tuned after a bulk set. UI-only; no save-format or planner change. Upstreamed as
[dcs-retribution#805](https://github.com/dcs-retribution/dcs-retribution/pull/805).

**Kneeboard consolidation + overflow pagination** (`game/missiongenerator/kneeboard.py`,
`kneeboard_page.py`): kneeboards are built once per `.miz` by `KneeboardGenerator.generate()`,
which buckets pages per **airframe** (DCS can't do per-group kneeboards) and writes each
`KneeboardPage` to a PNG. PR #73 folded the standalone Airfield Directory into the bottom of
the Support Info page and the Friendly Packages list into the bottom of the Mission Info page
to cut page count — but **neither host page paginated**, so on busy theaters those folded
tables ran off the bottom edge and the rows were simply lost. The fix: a `paginate()` hook on
`KneeboardPage` (default `[self]`, flattened in `generate()`) plus a `KneeboardPageWriter`
that can measure remaining vertical space (`remaining_table_rows()`) and render only the rows
that fit (`table_paginated()`, returning the overflow). `BriefingPage`/`SupportPage` render
the rows that fit inline and spill the remainder onto an auto-paginating generic
`TableKneeboardPage` continuation page (titled "… Friendly Packages" / "… Airfield Directory",
later pages marked "(cont.)"). The folded inline list is unchanged when everything fits, so
small theaters see no extra pages. The Friendly Packages list + package-targets map are gated
by `generate_all_packages_kneeboard`, now **default OFF** (it adds pages and can paginate on
busy theaters); the Airfield Directory still folds in whenever ATIS is present. Covered by
`tests/test_airfield_directory_page.py::test_support_page_spills_long_airfield_directory_to_continuation`.
The satellite-imagery recon pages remain gated OFF by `generate_target_recon_kneeboard`
(marker overlays don't reliably line up with the tiles — a known, separate geometry bug).

**Space-utilisation pass (light headings + two-column lists).** Sparse pages used to leave
the bottom (and right) two-thirds of the image blank. The fix uses a deliberately *light*
style (no heavy boxes): a bold heading, a thin underline `rule()`, then the content, with
sections spread by whitespace (`vspace()`) so the page breathes top-to-bottom. Two small
`KneeboardPageWriter` primitives were added — `rule()` (a hairline separator under a heading)
and `vspace()` (vertical breathing room) — plus `table_two_column_paginated()`. Three pages
were reworked: (1) **`CombatSarTaskPage`** — each guidance section (ROLE / HOW IT WORKS /
PICKUP|ON-SCENE COMMAND / BEACON) is a heading + rule + larger body text, with the leftover
height distributed as capped even gaps so a short brief doesn't yawn; (2) **`SupportPage`** —
the Package / AEW&C / Tankers / JTAC tables get the same heading+rule treatment, spaced to
span the page (gap grows when there's no Airfield Directory below; otherwise a fixed gap
leaves room for the directory and its pagination); (3) **`BriefingPage`** — the Friendly
Packages list renders in **two side-by-side columns** once it would overflow a single column,
using the wasted right half of the page and eliminating the near-empty continuation page in
the common case (only > ~2× a column's capacity still paginates). The recon pages are
untouched (still golden-tested). This is a visual change CI can't exercise — see in-game-pass
row **H1**/**H2**.

**Custom kneeboard import (UI, stored in the save).** DCS kneeboards are per-**airframe**, not
per-flight, so to add your own kneeboard page to a fleet of player flights you'd otherwise
hand-edit each `.miz`. The **Kneeboards** toolbar/menu action (`QCustomKneeboardsWindow`) lets
the campaign owner import an image once — normalised to PNG bytes and stored in the campaign
save as `game.custom_kneeboards` (a list of `CustomKneeboard` = name + bytes + optional
`airframe_id`) — and have it injected into every client flight's kneeboard at generation, or
scoped to a single airframe (the finest grain DCS allows). Injection is
`KneeboardGenerator._inject_custom_kneeboards()`: bytes → temp PNG → `mission.custom_kneeboards`
(the `""` key = all client flights, an airframe id = that type only), mirroring the existing
global `Saved Games/.../Retribution/Kneeboards` folder loader but **per-campaign** (no
cross-campaign leakage). Old saves migrate via a `__setstate__` `setdefault`. Covered by
`tests/missiongenerator/test_custom_kneeboards.py`; the Qt dialog itself needs an in-game pass.

---

## 5. Player target location precision

`TargetIntelPrecision` enum (`EXACT` / `APPROXIMATE`) in `game/settings/settings.py`
controls four behaviors together when set to Approximate:

- Player-only target steerpoints are offset to a randomised area within 1–3 NM of
  the real target rather than placed exactly on it. The waypoint is renamed
  `TARGET AREA`. AI attack logic is unaffected.
  (`game/ato/flightplans/waypointbuilder.py` `_player_visible_target_area_position()`)
- DEAD and SEAD flights drop the per-emitter `TARGET_POINT` waypoints entirely and
  fly a single fuzzed target-area waypoint instead — mobile SAMs relocate between
  intel updates, so handing the player an exact fix per launcher/radar defeats the
  "go find it" intent. The `Builder.layout()` of both flight types passes the
  per-unit list only under Exact intel, falling back to the area waypoint otherwise
  (`game/ato/flightplans/dead.py`, `sead.py`). **Strike is deliberately exempt**:
  its targets are fixed installations (buildings, bunkers, bridges) whose
  coordinates are reliable, so `strike_point()` always emits exact per-unit points
  regardless of the setting (`waypointbuilder.py` `_target_point(..., approximate=False)`).
- Objective F10 map marks are suppressed even if `generate_marks` is on.
  (`game/missiongenerator/triggergenerator.py`)
- Strike / SEAD / DEAD kneeboard target pages omit exact coordinates. The Strike
  page cues the player to search the target area; the SEAD/DEAD page (`SeadTaskPage`)
  in **cue mode** (DEAD always, or Approximate intel) shows **one consolidated cue**:
  a heading line with a single **rough bullseye** for the **center of the site**
  (`Bullseye <brg> for <nm>`, ~1 NM accurate) plus the single **target-area STPT** (the
  per-target waypoint nearest the site center), then a `Description | ALIC` table of the
  site's emitters. This replaced a per-unit bullseye on every row, which was cluttered.
  In **exact** mode (SEAD with Exact intel) the page keeps the per-emitter
  `STPT | Description | ALIC | Location` table with precise coords; that STPT pairs each
  target to its `TARGET_POINT` waypoint **by order** (not position), so it stays
  populated even when Approximate intel offsets the waypoint.
  (`game/missiongenerator/kneeboard.py`)

---

## 6. Air-defense planning rework

Design notes: `docs/dev/design/414th-air-defense-planning-notes.md` (read this for intent).
- Overlapping CAP waves + jitter: `game/commander/missionscheduler.py` (uses
  `barcap_overlap_time`); rounds math in `game/commander/theaterstate.py`.
  **Land CPs only** schedule overlapping waves; carriers keep the legacy
  simultaneous-stacking behavior. The jitter applies to the **first wave only**,
  capped at `min(barcap_overlap_time, 5 min)`, so CAP no longer deterministically
  arrives at mission start (which let attackers wait it out). With
  `barcap_overlap_time == 0` this reproduces the old back-to-back schedule exactly.
- Forward CAP line: `game/commander/objectivefinder.py` `vulnerable_control_points()`
  (checks `cp.has_active_frontline`; also fixes an inverted aggressiveness comparison).
- Threat-weighted BARCAP volume (the `barcap-threat-weighting` branch's headline):
  contested sectors get more BARCAP waves, **additive only** so coverage never regresses
  (an earlier up-and-down rework collapsed quiet bases to one wave and was reverted —
  `c8b1b8c32`). `ObjectiveFinder.air_threat_score(cp)` scores enemy air threat = sum over
  operational enemy airfields within `airbase_threat_range` of `proximity * present
  **A2A-capable** aircraft` (BARCAP/TARCAP-capable types only, so a base of
  bombers/tankers/transports doesn't read as an air threat), **plus a
  `FRONT_LINE_AIR_THREAT` floor** for any CP anchoring an active front line so
  front-line-only sectors earn extra waves instead of scoring 0 (see Fixes below).
  `theaterstate.py` `threat_weighted_barcap_rounds()` = `baseline +
  round((score/max_score) * baseline * (BARCAP_THREAT_CEILING-1))`, ceiling 2x; a
  zero-threat CP gets exactly the legacy duration-derived `barcap_rounds`, fleet keeps its
  2x. `TheaterState.from_game` wires it into `barcaps_needed`. Threat-weighted *orbit
  placement* (the companion increment) is now also live: `ObjectiveFinder`
  `normalized_air_threat(cp)` gives a deterministic 0..1 factor (normalized against
  `friendly_control_points()`, not the random vulnerable set) and `CapBuilder`
  `cap_racetrack_for_objective` raises the forward-distance floor by
  `factor * BARCAP_THREAT_FORWARD_BIAS` (0.75) so contested sectors orbit further forward;
  factor 0 reproduces the legacy uniform spread and TARCAPs are untouched. Design notes:
  `docs/dev/design/414th-air-defense-planning-notes.md`. Tests:
  `tests/test_barcap_threat_weighting.py`.
- **Red forward-middle BARCAP layer** (large maps): the rear BARCAP heads its orbit
  from the CP toward the *nearest enemy airfield*, so on a big map a red front CP whose
  nearest blue field is off-axis gets a screen flung far from the FLOT (observed 144–187 NM
  off the Fulda/Haina front). This adds **one extra** BARCAP per red CP anchoring an active
  front — placed **forward-middle** (≈ halfway rear-CP→FLOT, clear of blue threats by
  `cap_engagement_range + 5 NM`), parallel to the FLOT — **in addition to** the unchanged
  rear/base BARCAP. Map-scaled: only fires when the rear CP sits farther from the FLOT than
  the rear BARCAP's own reach (`cap_max_distance_from_cp`), so small maps are unaffected;
  front-relative geometry, no hardcoded distances. Red (AI) side only; QRA/intercept reserve
  untouched. Wired as an **added** layer via a new package target type (so no save
  migration): `ForwardBarcapZone` (`game/theater/missiontarget.py`) carries the
  forward-middle center + enemy-facing heading computed in `TheaterState.from_game`
  (transient `forward_barcaps_needed`); `forward_cap_front_anchor`
  (`game/ato/flightplans/supportorbit.py`) is the geometry; `PlanForwardBarcap` +
  `ProtectAirSpace` plan it; `CapBuilder.cap_racetrack_for_objective` lays the zone
  racetrack and leaves every other target on the legacy path. Tests:
  `tests/test_forward_barcap.py`. **In-game pass ☑ VERIFIED 2026-06-25** (checklist B5). The
  theater-tanker-demand companion from the same plan is **not** in this change.
- A2A escort-need uses fighter **engagement reach**, not BARCAP **orbit** reach
  (`game/threatzones.py` `air_engagement` zone + `aircraft_engagement_range`;
  `PackageFulfiller.check_needed_escorts` now calls
  `waypoints_threatened_by_aircraft_engagement`). `barcap_threat_range` clamps the
  `airbases` orbit zone to ~45% of the way to friendly territory (keeps enemy CAP
  non-offensive for the navmesh + BARCAP placement). The CAS patrol sits on the FLOT
  (~50%), so its escorted waypoints fell in the gap, the A2A escort was pruned every
  time, and — since CAS is the **only** proposer of `FlightType.TARCAP` (`cas.py:35`,
  no standalone `PlanTarcap` task) — TARCAP was never planned at all. Forward DEAD/BAI
  near the front lost their `ESCORT` the same way. The new `air_engagement` zone
  (uncapped `cap_max_distance_from_cp + cap_engagement_range`) is a strict superset of
  `airbases`, so escorts are only *added*, never lost; the clamped zone still drives
  the navmesh, IP/hold/join geometry, BARCAP placement (incl. §6 orbit forward-bias),
  and the map overlay. `ThreatZones` is recomputed each load (excluded from pickling),
  so no save migration. `can_plan_escort(AirToAir)` was also corrected to gate on
  `ESCORT` **or** `TARCAP` (CAS's A2A escort is TARCAP, not ESCORT) instead of `ESCORT`
  alone. Tests: `tests/test_aircraft_engagement_escort_zone.py`.
  In-game pass ☑ VERIFIED 2026-06-24 (B4, Tacview) — CAS (`Front line Fulda/Haina
  CAS`) spawned with a TARCAP + SEAD Sweep, and forward DEAD/BAI/SEAD packages all
  carried A2A + SEAD escorts.
- Engagement-range bumps: `game/settings/settings.py` (`cas_engagement_range_distance`
  10->15 nm, `armed_recon_engagement_range_distance` 5->10 nm).
- Cruise/patrol altitude doctrine (Campaign Doctrine page, all default to **no behavior
  change**, settable per campaign so the squadron tunes altitude to taste rather than the
  hardcoded ~24k Hornet CAP):
  - **Altitude scatter band** — replaced the single symmetric `max_plane_altitude_offset`
    (rolled `randint(0,max) * +/-1`) with a `[min_plane_altitude_offset,
    max_plane_altitude_offset]` band (x1000 ft, defaults -2/+2 = the old +/-2k spread).
    Equal bounds disable scatter (0/0 = none); an asymmetric band biases it (0/+4 =
    climb-only). The roll is the pure, tested `roll_plane_altitude_offset(low, high)` in
    `game/ato/flight.py` (used by `Flight.__init__`).
  - **Minimum patrol altitude** (`min_patrol_altitude`, x1000 ft, default 0 = off) — floors
    CAP/patrol legs to at least this altitude *after* the scatter, capped by the doctrine's
    `max_combat_altitude`; flights already higher are untouched, helos exempt. Pure helper
    `apply_patrol_altitude_floor()` called from `WaypointBuilder.get_patrol_altitude`
    (`game/ato/flightplans/waypointbuilder.py`).
  - New fields auto-default on old saves via `Settings.__setstate__` and render on the
    Campaign Doctrine page (no UI wiring). Tests: `tests/test_flight_altitude_settings.py`.
- Route around the front line: `game/threatzones.py` adds the **active front** as a
  navmesh routing hazard. `ThreatZones._front_line_threat_zone(left, right)` buffers a
  capsule along each active FrontLine — built from the **land-clipped FLOT endpoints**
  (`FrontLineConflictDescription.frontline_bounds`, the same geometry the FLOT generator
  uses), `FRONT_LINE_THREAT_BUFFER` = 10 NM — and folds it into `self.all` **only** — the geometry the navmesh + generic
  `threatened()`/path checks use. The SAM (`air_defenses`) and CAP (`airbases`) views stay
  clean, so air-defense/barcap planning is untouched. The navmesh penalizes 3x rather than
  forbids, so transiting flights cross the FLOT perpendicularly at the least-bad point
  instead of loitering; CAS/BAI target the front and reach it on the un-routed ingress leg,
  so they're unaffected. Added to every faction's projected threat (each coalition's
  navmesh is built from its opponent's zone), so both sides avoid it. Tests:
  `tests/test_front_line_threat_zone.py`.
- Front-line units no longer stack: `game/missiongenerator/flotgenerator.py`
  `get_valid_position_for_group()` steps perpendicular from the (valid) front toward the
  requested depth instead of snapping laterally via `find_ground_position()` — the old
  lateral snap collapsed every off-map group onto the same patch, piling units on one tile
  (worst for deep roles: artillery/logistics at 16-20 km).

### Jank fixes (2026-06-21)

A consumer-level audit of the above (everything except QRA/scrambling, §1) found four real
problems; all four are fixed:

- **HIGH — FLOT units spawned *on* the front line.** `flotgenerator.py`
  `get_valid_position_for_group()` returned the depth-0 point the instant the first 250 m
  perpendicular step hit water/off-map, so on coastal/river/narrow-land fronts deep roles
  (artillery, logistics) spawned in direct contact — the same stacking class the rework was
  meant to fix, relocated to depth 0. Now, if the perpendicular walk can't reach at least
  half the requested depth, it falls back to a lateral `find_ground_position` search around
  the **intended-depth** point so the group keeps its depth (and spreads instead of
  stacking). **Lua-free; in-game pass ☑ VERIFIED 2026-06-25 (checklist B1, coastline map).**
- **MEDIUM — red's defensive posture flickered.** The per-CP "plan offensively instead of
  defending" decision in `vulnerable_control_points()` was an **unseeded** `randint` re-rolled
  every planning pass, so red defended a base one pass and abandoned it the next for identical
  board state. Now `ObjectiveFinder._offensive_roll(cp)` seeds a `random.Random` per
  `(turn, cp.name)`: stable across all passes within a turn (coherent posture), still varies
  turn to turn.
- **MEDIUM — threat score counted the wrong aircraft.** `air_threat_score` summed **all**
  present fixed-wing (bombers/tankers/transports included), so a non-fighter base stole BARCAP
  waves from a sector facing actual fighters. Now counts only BARCAP/TARCAP-capable types.
- **MEDIUM — front-line-only sectors got no volume boost** (the two flagship pieces were
  decoupled). A CP vulnerable *only* via `has_active_frontline` scored 0 and never earned
  extra waves. Now such CPs get a `FRONT_LINE_AIR_THREAT` floor (additive with any nearby-
  airbase score), so a contested front earns roughly half the threat bonus even with no enemy
  airbase in range. (Intent confirmed by the maintainer: hot fronts *should* get more waves.)
- **Capsule clipping (from the same audit):** the navmesh front-line hazard now uses the
  land-clipped FLOT bounds instead of the full nominal 80 km width centered on the raw
  strength-derived point, so the ~117 km × 37 km band no longer spills across water/empty
  flanks or sits laterally offset from the actual battle (see the route-around bullet above).

Tests: `tests/test_objectivefinder_barcap.py`, `tests/test_barcap_threat_weighting.py`,
`tests/test_front_line_threat_zone.py`. Remaining LOW audit items (e.g. no clamp on
`barcap_rounds` when `barcap_overlap_time` ≥ mission duration, one-sided lateral spread,
250 m magic step) are deferred.

### Front-anchored support-orbit placement (AEW&C + tanker) (2026-06-22)

**Symptom (fresh Red Tide save, AI-generated turn):** the AI's AWACS and tanker racetracks
were placed nonsensically. Red AWACS targeting a far-north CP (Kastrup) was generated
**~326 NM behind the front and ~175 NM off-axis** (out over the Baltic); the red tanker sat
only ~28 NM behind the FLOT (exposed); a blue tanker whose nearest-friendly target was its own
departure field could clamp **onto the home runway**. Brady hand-moved them to sane,
front-centered positions — that edit is the spec this reproduces.

**Root cause.** `aewc.py` and `theaterrefueling.py` independently anchored the orbit on
`package.target` (a CP — *nearest* friendly for tankers, **farthest** friendly for AWACS) and
offset it along the bearing from that CP to the nearest enemy threat-zone boundary. For a
rear/flank CP that bearing is unstable (it swings as the front shifts), so the orbit flung
off-axis; the blue tanker also had a `max(0, …)` clamp that pinned it to the anchor when the
field was within the buffer of the front.

**Fix** (`game/ato/flightplans/supportorbit.py`, new shared helper used by both builders):
`support_orbit_anchor()` anchors on the **FLOT center** of the active front nearest the
supported area, then pushes the orbit into friendly airspace along the **stable enemy→friendly
axis** (`friendly_cp → enemy_cp` heading) until it is at least the configured buffer from the
enemy threat zone (`threat_zones.distance_to_threat` / `threatened`). Result: centered on the
front, on the coalition's own side, at a sane standoff, no forward/clamp special-casing. Falls
back to the old target-anchored standoff when there is no active front (opening turn). Buffers
unchanged: `aewc_threat_buffer_min_distance` (80 NM) / `tanker_threat_buffer_min_distance`
(70 NM).

**Depth asymmetry (`AI_SUPPORT_DEPTH_FACTOR`, default 2.5):** the *player* coalition holds
forward at 1x the buffer behind the FLOT (coverage); the *AI* coalition holds deep at
`factor x buffer` so red tankers/AWACS don't loiter near the front. Both are then pushed
further if needed to clear the enemy threat zone. Tying depth to the threat zone alone left red
right on the FLOT when the player had no forward SAMs reaching the front; the factor decouples
"how deep the AI sits" from "how strong the player's threat is." With a campaign buffer of 40
NM this puts red ~100 NM back and blue ~50 NM; at the default 80/70 buffers red is ~200/175 NM
deep. Verified by recomputing the broken save: red AWACS `+326/−175 NM → centered, ~100 NM
behind`, blue forward-but-centered. Tests: `tests/test_support_orbit.py`. Upstream-core
flight-plan code, so an upstream-PR candidate. **Lua-free; in-game pass ☑ VERIFIED 2026-06-24 (C1/C2).**

### Theater tanker placement from receiver demand (2026-06-25)

**Symptom.** A shared theater tanker is planned at `closest_friendly_control_point()` then
front-anchored (above), but receiver `REFUEL` waypoints are generated independently
(`RefuelZoneGeometry`), so the tanker could orbit 50–80+ NM from the flights that actually
need it.

**Fix — a post-planning reposition pass** (`game/commander/tankerdemand.py`). The tanker task
runs first in the HTN (before offensive packages) and `PackagePlanningTask.execute()` only adds
packages to `coalition.ato` *after* the search, so the demand isn't visible during planning.
Rather than reorder the HTN (which would change budget order for every campaign), a pass runs
**after** `TheaterCommander.plan_missions` has built the full ATO:
- `theater_refuel_demand(coalition)` collects one weighted `RefuelDemand` per non-tanker flight
  that has a `REFUEL` waypoint (method = the flight's `air_refuel_type`, weight = aircraft
  count). Flights whose own package carries a buddy tanker are excluded (served in-package).
- `best_tanker_service_point()` returns the count-weighted centroid of the strongest cluster of
  **compatible** demand (boom/probe honored, untagged permissive — mirrors `can_refuel_from`),
  or `None`. Greedy single-link clustering, 60 NM default radius.
- For each shared theater tanker (a `REFUELING` flight whose package `primary_task` is
  `REFUELING`), the pass sets `Flight.refueling_service_point` and calls
  `recreate_flight_plan()`. `TheaterRefuelingFlightPlan` centers the orbit on that point
  (nudged clear of enemy threat zones) instead of the front anchor; the override is read via
  `getattr` so old saves / un-repositioned tankers keep the legacy anchor with **no migration**.
- No compatible demand → tanker untouched (legacy front anchor). Same-package buddy tankers are
  never moved.

Tests: `tests/test_tanker_demand.py` (scoring + ATO extraction). **Needs an in-game pass** (C7).
**Deferred follow-up:** retargeting compatible receiver `REFUEL` waypoints onto the moved tanker
(the plan's conditional "when the detour is reasonable" half) — the tanker already sits at the
centroid of those points, so this is a refinement, not essential. First half of the Codex tanker
PLAN; the red forward-BARCAP companion shipped separately (§6).

### DEAD reachability gate — no more bombers tasked into a live belt (2026-06-22)

**Symptom (Red Tide AI test):** blue B-1/B-52/F-15E strikes were tasked ~30 km behind the
FLOT, *inside* an un-suppressed S-200/SA-3/SA-8 belt, then turned around by threat-reaction
ROE before employing (zero A-G dropped). Root cause was **not** loadouts (that was a
separate fix) — it was the planner's optimism.

**Mechanism.** The HTN re-plans within a turn against a mutating `TheaterState`
(`theatercommander.py`). A strike on a SAM-covered target is correctly deferred by
`PackagePlanningTask.target_area_preconditions_met` (gates on the **target point** only),
which records the SAM in `threatening_air_defenses`. `DegradeIads` then plans a DEAD against
it, and `PlanDead.apply_effects` called `state.eliminate_air_defense(target)` — removing the
SAM from `enemy_air_defenses` **as if already destroyed**. The loop re-plans, the threat gate
now passes, and the bomber is tasked through a corridor that is clear only on paper. In-sim
that DEAD launched from ~200 km away, can't penetrate the belt to reach the deep SAM, the SAM
lives, and the strikers fly into it. (Settings modulate, not cause: default
`autoplanner_aggressiveness` is 20; the trigger is simply *blue having DEAD squadrons* that
form a package the fulfiller can't range past the belt.)

**Fix — reachability gate on the optimistic clear** (`game/commander/tasks/primitive/dead.py`,
`game/commander/theaterstate.py`, `game/threatzones.py`):
- `PlanDead.apply_effects` now only calls `eliminate_air_defense` when
  `TheaterState.dead_can_reach(target, dead_flights)` is true — i.e. the DEAD's **actual
  routed flight plan** reaches the SAM without its waypoints crossing **another** live
  radar-SAM ring (`route.distance(center) < radius`, the target's own ring excluded).
- Reachability is judged against `initial_radar_sam_rings` — an **immutable turn-start
  (ground-truth) snapshot** built once in `from_game` via the new
  `ThreatZones.radar_sam_rings()` (same `radar_only` range / >3 NM floor / `max_threat_range`
  cap as `for_threats`, but kept per-site so a target can be excluded). Using the live list
  would re-introduce the bug one layer deeper, since earlier optimistic clears would make a
  shielded SAM look reachable.
- Unreachable SAMs are recorded in a new persistent `unreachable_air_defenses` set (shared by
  reference through `clone`, like the threat lists). `PlanDead.preconditions_met` early-returns
  on members so we don't re-build/re-task an un-rangeable DEAD every loop; the SAM stays in
  `enemy_air_defenses`, so the dependent strike stays **deferred until real BDA confirms the
  kill on a later turn** (correct layer-by-layer IADS rollback).
- **No regression for reachable SAMs:** a close SAM whose DEAD route is clear is still cleared
  same-turn, preserving today's legit same-turn SEAD-escort-then-strike behavior.

The DEAD itself is still tasked (blue still tries to peel the belt, with its SEAD escort) — we
only changed whether the *follow-on strike* trusts the kill. This is upstream-core HTN
behavior, so it's an upstream-PR candidate. Tests: `tests/test_dead_planning.py`
(`dead_can_reach` geometry + `apply_effects` routing). **Lua-free; in-game pass ☑ VERIFIED
2026-06-24 (B2) — blue defers deep strikes until the belt is actually down.**

---

## 7. Auto-hide mobile SAMs on MFD

- Task-level (`game/armedforces/forcegroup.py`): `hide_on_mfd` field,
  `_MOBILE_TASKS = {SHORAD, AAA}`, propagated through `for_layout()` /
  `from_preset_group()` / `create_ground_object_for_layout()`. `hide_on_mfd` is a
  per-task default that YAML can override explicitly (`data.get("hide_on_mfd", ...)`).
- Unit-level (`game/missiongenerator/tgogenerator.py` `GroundObjectGenerator`):
  `hidden_on_mfd` is a group-level DCS property, so the task-based flag missed
  SHORAD/AAA/MANPAD escorts generated *inside* a non-air-defense group (armor or
  missile site) -- they stayed on the datalink. `_contains_mobile_air_defense()`
  now also hides a generated vehicle/ship group when it contains a unit of class
  `MOBILE_AIR_DEFENSE_UNIT_CLASSES = {AAA, SHORAD, MANPAD}` (`game/data/units.py`).
  TELAR and radar/launcher classes are excluded on purpose, so standalone mobile
  MERAD/LORAD sites (SA-6/11, SA-2/3/5/10) stay visible/targetable for SEAD.

---

## 8. Robustness / crash fixes

- Flight-combat-exit `IndexError`: `game/ato/flightstate/inflight.py` guards in
  `__init__` and `next_waypoint_state()`.
- AWACS orbit stacking + direction: `game/ato/flightplans/aewc.py`.
- Tanker orbit placement/deconfliction: `game/ato/flightplans/theaterrefueling.py`.
- Malformed mod payload Lua (CJS Super Hornet v2.4 uses local-var table indices that the
  pydcs Lua parser rejects with `ValueError`): patched loader in `qt_ui/main.py`
  (`_patch_pydcs_payload_loader()`), plus the offending files are skipped with a warning.
- Spurious "past start times" warning for player CAP: a BARCAP/TARCAP is meant to be
  on-station at mission start, so a cold-start spin-up legitimately begins before mission
  start — and the scheduler reserves only the 2-min AI startup while a player-flown flight
  gets the larger `player_startup_time` allowance, so a player-occupied cold-start CAP tripped
  the warning every turn. `QTopPanel.negative_start_packages` now checks **takeoff** time (not
  startup) for DCA patrols, so a genuine "can't even take off in time" misplan still warns but
  the normal cold-start CAP does not. Tests: `tests/test_negative_start_packages.py`.
- Player-despawn counted as a combat loss (2026-06-20): a player dropping to spectator — or
  the mission ending with players still airborne — makes DCS fire `S_EVENT_CRASH`/`DEAD` for
  that jet, which `dcs_retribution.lua` recorded into `crash_events`/`dead_events`, so
  `debriefing.py` attrited the airframe + pilot even though they survived (GERBIL F-14s logged
  lost while alive at mission end; confirmed in Tacview, none in `destroyed_objects_positions`).
  The plugin now marks a unit on `S_EVENT_PLAYER_LEAVE_UNIT` and suppresses the crash/dead/lost
  that follows within `PLAYER_LEAVE_GRACE_S` (`is_player_despawn`). A real shootdown fires the
  loss event **before** the player leaves the seat, and **ejections are excluded** (an ejection
  is a real loss), so both still count. This is upstream loss-accounting (good upstream-PR
  candidate). Tests: `tests/test_debriefing.py::test_lua_suppresses_player_despawn_loss_events`.
  **Residual to watch in-game:** if the engine tears the mission down without per-player
  `PLAYER_LEAVE_UNIT` events, those despawn-crashes aren't caught — land/despawn before ending
  remains the belt-and-suspenders.

---

## 9. TIC — Troops In Contact frontline battle sim (plugin, default ON)

Grendel's TIC v1.1 (MIT, lua globals named `GLSCO*`) replaces vanilla ground AI
with formation-keeping, prolonged scripted firefights for frontline maneuver
units. Enable per-game via the plugins UI ("Troops In Contact").

Dynamic-front movement design (why the stance/cadence logic looks the way it does):
`docs/dev/design/414th-tic-dynamic-fronts-notes.md`. Read it before touching
`_plan_tic_action()` or the TIC stance mapping.

- Plugin: `resources/plugins/tic/` (`TIC_v1.1.lua` + `tic_414_init.lua` +
  `plugin.json`; options: `stormtrooper`, `createMenus`, `boundPause`,
  `ambientFire`). Script injection is NOT a work order - it's
  `_inject_tic_script()` in `game/missiongenerator/luagenerator.py` (scramble
  pattern): a DoScript preamble pre-seeds `GLSCO.*` from
  `dcsRetribution.plugins.tic.*` and sets `AutoInitialize/AutoStart = false`,
  then DoScriptFile TIC_v1.1.lua, then DoScriptFile `tic_414_init.lua`, which
  installs the 414th ambient-fire extension (wraps
  `GLSCO_COMBATANT:simulate()`: combatants with no LOS target have a 50%
  chance per firing cycle to area-fire a salvo at 30-150 m around the nearest
  enemy formation within 6 km - tracers over LOS blockers, no aimed
  lethality) and then owns `GLSCO:Initialize()` + `battle:Activate()`.
  CRITICAL: TIC's auto-init is disabled, so if tic_414_init.lua is removed or
  fails, the battle never starts.
- Generator contract: `game/missiongenerator/flotgenerator.py`. When the
  plugin is enabled, TANK/IFV/APC/ATGM frontline groups are named
  `TIC:<namegen name>` (one TIC formation per group), late-activated, and get
  TIC orders as waypoint NAMES (`t+N hdg=H roe=simulate`) via
  `_plan_tic_action()` instead of DCS tasks/triggers. Squad infantry joins
  the carrier's formation as `TIC:<formation>#<infantry name>`. Artillery and
  the manpads-only branch stay vanilla. TIC group names are recorded in
  `mission_data.tic_groups` (the injection gate).
- ROE/waypoint design (settled after in-game testing, intentional - keep):
  TIC's "simulate" ROE fires theatrical near-miss salvos ONLY while
  stationary; moving units don't shoot at all, and `roe=kill` was judged too
  lethal/accurate by the 414th. `_plan_tic_action()` shapes movement PER
  CombatStance (`TIC_STANCE_PROFILES` / `_tic_stance_profile()`) so opposing
  sides don't run the same script and collide as a symmetric wall - the
  campaign already feeds independent per-side stances. Full design rationale:
  `docs/dev/design/414th-tic-dynamic-fronts-notes.md`.
  - Every formation takes an opening bound to a fighting line short of the
    trace (`_tic_distance_to_front()` projects the group onto the forward axis;
    `find_offensive_point()` places the bound), inside TIC's ~2 NM targeting
    bubble. ATTACKERS then run slide/press assault cycles past the trace;
    DEFENSIVE/AMBUSH dig in at the bound instead of idling at the rear spawn
    (which could sit OUTSIDE the bubble, leaving an attacker pressing an empty
    line).
  - Stance profiles: AGGRESSIVE = standoff (600-900 m) + 1 slide + light press;
    BREAKTHROUGH = straight thrust, no lateral slide, deeper press
    (`TIC_BREAKTHROUGH_DEPTH_SCALE` 1.8) + faster cadence (0.7); ELIMINATION =
    2 slide/press cycles to hunt LOS; DEFENSIVE = dig in at
    `TIC_DEFENSIVE_STANDOFF` (900-1400 m) + a low-chance occasional
    counterattack (`TIC_COUNTERATTACK_CHANCE` 0.25); AMBUSH = most rearward
    hold at `TIC_AMBUSH_STANDOFF` (1400-2200 m), never counterattacks;
    RETREAT = single fallback leg.
  - Slide legs use TIC_LATERAL_SLIDE (1.5-3 km) to break LOS deadlocks behind
    towns/ridges (the Dzhukhur lesson: TIC targeting is LOS-checked and TIC
    does not path around terrain). Press legs use TIC_PUSH_DEPTH (400-800 m)
    times the stance depth scale.
  - Cadence is staggered per group so the line ripples instead of lurching:
    `_tic_step_off()` spreads the opening bound across a `boundPause`-scaled
    window, `_tic_jitter()` is boundPause +/-45% (loosened from +/-25%), and
    `_tic_leg_gap()` further scales each gap by a per-group tempo
    (`TIC_GROUP_TEMPO` 0.7-1.4) and the stance cadence. `tic.boundPause`
    (default 25, players set it in the plugin UI) sizes the battle arc to
    ~1.5-2 h.
  - Losses from scripted fire are sparse near-miss kills by design; players
    flying CAS are the real attrition source. The campaign front moves on
    player kills, not TIC kills. (Terrain-anchored positioning was considered
    and rejected - Retribution exposes no terrain queries on this path; see the
    design note.) Tests: `tests/test_tic_dynamic_fronts.py`.
- Loss tracking: TIC destroys originals (no dead event - scripted destroy is
  silent) and respawns single-unit clones renamed by MOOSE SPAWN to
  `<group>-<i>#NNN-UU`. `game/unitmap.py` registers `front_line_groups` and
  `front_line_unit_from_tic_clone()` strips the suffixes (regex
  `TIC_CLONE_NAME`, handles nested respawn generations); `game/debriefing.py`
  falls back to it when the exact unit-name lookup misses. Tests:
  `tests/test_tic_clone_mapping.py`.
- KNOWN LIMITATION: with StormTrooper AI on (default), TIC cloaks managed
  units from DCS AI sensors - AI CAS flights and the AFAC JTAC cannot detect
  the enemy frontline. Human CAS is unaffected. Turn StormTrooper off for
  visible real-AI ground combat.
- Do NOT call `ScanAndRegisterFormations` twice and do not ME-activate TIC
  groups - TIC owns their lifecycle.

---

## 10. CurrentHill Iran assets pack

- Unit defs: `pydcs_extensions/iranmilitaryassetspack/` (Shahed-136 `CH_Shahed136`,
  `IranFAC_MG`, `IranFAC_MG_AShM`), re-exported from `pydcs_extensions/__init__.py`.
- Radar DB: `game/data/radar_db.py`. Mod removal logic: `game/factions/faction.py`.
- New-game toggle: `game/theater/start_generator.py` (`iranmilitaryassetspack` field),
  `qt_ui/windows/newgame/...` wizard pages.
- Faction: `resources/factions/CH_iran_2020.json` (`[CH] Iran 2020`).

---

## 11. Native DCS DTC cartridge export (plugin-less, gated OFF by default)

Auto-writes a **native DCS Data Transfer Cartridge** into the generated `.miz` so
players spawn with the SA picture pre-built. **F/A-18C only**, and the shipped payload
is the **`SA.CAP_PTS` partition only**: player/AI CAP racetracks + tanker tracks drawn
on the Hornet SA page. Gated by the `generate_dtc` setting (default OFF until ED's
mission-start pre-load is confirmed working on a future build).
- Design ground truth + reverse-engineered schema: `docs/dev/design/414th-dtc-export-notes.md`
  (read this before touching the format).
- Package: `game/missiongenerator/dtc/` — `cartridge.py` (envelope + the neutral,
  terrain-tagged name `Retribution <terrain> DTC_1` that avoids colliding with a
  player's personal cartridge library), `sadata.py` (`_collect_orbits()` /
  `_collect_threats()` Retribution→partition mapping; reuses the `hide_on_mfd` filter so
  hidden mobile SAMs never generate rings), `generator.py`, `injector.py`,
  `diagnostics.py`.
- Build path: overlay tracks onto the captured ME template
  (`resources/dtc/templates/FA-18C_hornet.dtc`, `F-16C_50.dtc`) so COMM/ALR67/CMDS keep
  their ME defaults and the cartridge stays structurally complete, then inject
  `DTC/<type>.dtc` zip members **after** `self.mission.save(output)` in
  `game/missiongenerator/missiongenerator.py`, and **also** mirror the file into
  `Saved Games\DCS\DTC\<cartridge name>.dtc` (DCS resolves named cartridges from there,
  not the `.miz`).
- Per-unit binding: every player Hornet carries
  `["DTC"]={["AutoLoad"]=true,["Cartridges"]={[1]={["default"]=true,["name"]=...}}}`.
- Tests: `tests/missiongenerator/test_dtc.py`, `tests/missiongenerator/test_dtc_diagnostics.py`.
- **KNOWN LIMITATION (verified 2026-06-14):** ED's mission-start *pre-load* does not fire
  on the current DCS build even with a fully correct setup — the player must open the DTC
  manager and **manually load** `Retribution <terrain> DTC_1` once per sortie, after which
  the tracks populate correctly. Re-test pre-load on future DCS builds before assuming the
  manual step is still needed. Mirrored library write is per-machine, so it does not
  distribute over multiplayer — still open.

---

## 12. TARS recon engine (plugin, default ON)

Design notes: `docs/dev/design/414th-tars-recon-notes.md` (read before touching).
MOOSE **Ops.TARS** v2.3.2 becomes the runtime engine for `FlightType.TARPS`: F10 "film"
menu, overfly detection, coalition F10 markers, scoring, and a landing debrief that
feeds the BDA fog-of-war the exact enemy units a surviving recon pass photographed.

- Plugin: `resources/plugins/tars/` (`TARS.lua` vendored verbatim from MOOSE develop —
  NOT in the bundled Moose.lua, but API-compatible with it; `tars_414_init.lua`;
  `plugin.json`, default ON; options: scoring, scoreValue, filmLimit, restrictToNamed,
  enforceLoadout, srs, srsPort). Option defaults (playtest-aligned 2026-06-17):
  `scoring` OFF, `restrictToNamed` ON, `srs` ON, `filmLimit` 25, `scoreValue` 100;
  `enforceLoadout` stays OFF on purpose (ON falls back to the stock `allowedAmmo`
  whitelist + a best-effort AAM list and can leave the F10 film menu locked — see the
  loadout-whitelist note below).
- Injection: NOT a work order. `_inject_tars_script()` in
  `game/missiongenerator/luagenerator.py` mirrors the TIC pattern — appended after
  `inject_plugins()` so `dcsRetribution.plugins.tars` exists, then DoScriptFile
  `TARS.lua` + `tars_414_init.lua`. TARS.lua only defines the class; `tars_414_init.lua`
  owns `TARS:New()`.
- TWO theater-correct overrides are load-bearing (`tars_414_init.lua`):
  `targetNameFilter.enabled=false` (stock USA/USSR keywords hide all Retribution
  targets) and the `allowedAmmo` loadout whitelist (stock list excludes AIM-7/AIM-54, so
  the shipped F-14 TARPS payload — carrying `{SHOULDER AIM-7MH}` — would fail ground
  validation and the F10 menu would never unlock). With `enforceLoadout` OFF (default) we
  make the whitelist accept anything via an `__index` metatable returning true — no
  guessing at DCS `weapon.desc.displayName` strings, no payload nerf.
- BDA bridge: `OnAfterDataProcessing` override appends `{unit,life,type}` to the global
  `tars_recon_captures` and sets `dirty_state=true`; `dcs_retribution.lua` `write_state()`
  serializes it; `game/debriefing.py` `StateData.parse_tars_captures()` parses it;
  `game/sim/missionresultsprocessor.py` `tars_reconned_tgos()` resolves names via
  `unit_map.theater_units(...).theater_unit.ground_object` and `update_confirmed_bda()`
  syncs those TGOs. Additive — empty/no-op when the plugin is OFF. Snapshot schema
  (`snap.name/life/type/coa`) is documented in TARS.lua and logged once in-game.
- Tests: `tests/test_tars_bda_bridge.py`. Default ON; Lua in-game pass ☑ VERIFIED
  2026-06-24 (G2 — TARPS captures feed Retribution BDA).

---

## 13. Flight Control ATC (plugin, default ON, players-only)

Design notes: `docs/dev/design/414th-flightcontrol-notes.md`.
MOOSE **FLIGHTCONTROL** v0.7.7 (already in the vendored Moose.lua) gives players-only
tower comms (taxi/takeoff/landing sequencing + SRS voice, text-subtitle fallback) at
friendly land airbases.

- Plugin: `resources/plugins/flightcontrol/` (`flightcontrol_414_init.lua`; `plugin.json`,
  default ON; options: subtitles, srsPort, maxLanding, maxTaxi).
- Injection: `_inject_flightcontrol_script()` in `luagenerator.py` (after
  `inject_plugins()`, gated on enabled) emits the blue-airdrome list via
  `_flightcontrol_airbase_entries()` into `dcsRetribution.FlightControl.airbases` (name +
  ATC freq/modulation from `mission_data.runways` where present), then DoScriptFile the
  init. AIRDROME-only (FARPs/ships rejected by `FLIGHTCONTROL:New()` itself); SRS path is
  nil so MOOSE auto-detects the server install.
- Players-only is PRAGMATIC, not a hard switch: MOOSE observes AI at the airbase, so we
  set generous `SetLimitLanding`/`SetLimitTaxi` (default 99) + `SetRadioOnlyIfPlayers` so
  AI flow stays pass-through. PRIMARY in-game check: AI QRA/CAP launches from these bases
  are unaffected.
- Orphan-parking reconciliation (`reconcile_orphan_parking()` in the init, after
  `fc:Start()`): MOOSE `_InitParkingSpots()` IDs a busy spot's occupant with
  `FindClosestUnit`, which only sees UNITs. Retribution parks STATIC objects on some ramp
  spots (Kutaisi), so those spots are left `Status==nil` ("NOT FREE but no unit could be
  found there") and the status loop then spams "Number of parking spots does not match!"
  every cycle all mission (138x in one playtest). The fix marks each orphan spot OCCUPIED
  (`"RetributionStatic"`) so the counts balance and the static-held spots stay out of the
  taxi pool. Cosmetic-only: AI flow was already unaffected. `_InitParkingSpots` runs
  synchronously inside `:Start()`, so `fc.parking` is populated when the pass runs.
- Tests: `tests/test_flightcontrol_emit.py`. Default ON; Lua in-game pass ☑ VERIFIED
  2026-06-24 (G1 — AI flow unaffected, no parking-spot spam).

---

## 14. Plugin Options UI — section descriptions + label/default pass

A polish pass over the **LUA Plugins Options** page so every plugin explains itself.
- New `descriptionInUI` field on `plugin.json` (optional, top-level). Parsed in
  `game/plugins/luaplugin.py` (`LuaPluginDefinition.description` +
  `LuaPlugin.description`) and rendered as an italic, word-wrapped line spanning the
  group-box header in `qt_ui/windows/settings/plugins.py` (`PluginOptionsBox` now drives
  its own `row` counter so the description sits above the option grid). Backward
  compatible: a plugin without the field renders no description. Documented in
  `resources/plugins/_doc/plugins_readme.md`.
- Section descriptions + clearer option labels added to all 15 options-bearing
  `plugin.json` files (414th + upstream): typo fixes (`Scipt`→`Script`,
  `Multipler`→`Multiplier`, BigEye's unclosed paren), unit/casing consistency
  (`NM`, `minutes`, `seconds`, `MHz`), and sentence-case wording. **Mnemonics and
  defaults were untouched except** the TARPS defaults below — so saved settings are
  unaffected (labels/descriptions are display-only; mnemonics are the settings keys).
- TARPS defaults re-seeded to match playtest usage (new campaigns only):
  `scoring` true→false, `restrictToNamed` false→true, `srs` false→true. See the TARS
  section above.
- Note: `AGENTS.md` is a byte-identical mirror of `CLAUDE.md` (the authoritative source);
  resync it after editing CLAUDE.md.

---

## 15. SCAR — Strike Coordination and Reconnaissance (flight type + scenario plugin)

A player-flown `FlightType.SCAR`: work a defined area to find and prosecute a high-value
target hidden among look-alike decoys + clutter and light AAA. Design ground truth:
`docs/dev/design/414th-scar-task-spec.md` (the original moving model) and
`docs/dev/design/414th-scar-king-fac-notes.md` (the loiter rework — read this first now).
SME-facing open questions: `docs/dev/design/414th-scar-commander-sme-questions.md`.

> 🔄 **Loiter-and-task rework — Phase 1 (PR #187, draft; pending in-game pass).** The original
> design was a **chase**: the HVT (spawned runner / bound real armor / bound SCUD) fled to a
> city and "fail" was it arriving. That is **retired**. SCAR now plans like the Combat SAR
> package — the flight **loiters over a STATIC kill box** and the **C-130 "King" on-scene
> commander** designates a **real, static armor TGO** to service. Because the target is a real
> campaign TGO, kills attrit the enemy through the **normal ground-loss/debrief path** — there is
> **no SCAR-specific success/failed scoring** (the plugin still emits those statuses, but they're
> log-only; `commit_scar_results` only acts on `captured` + mis-ID + strandings). What's landed
> on the branch:
> - **`_make_static`** (`scarluadata.py`) zeroes all movement: the bound real group + spawned
>   decoys hold (dest == spawn, speed 0), the tasking dest/fire-point collapse onto the area
>   centre, and the SOF capture point moves onto the held target.
> - **Lua static guards** (`scar_414_init.lua`): nothing drives, the SCUD stays inert
>   (WEAPON_HOLD), the instant arrival-fail is gated off — **fail = window timeout only**.
> - **Inverted SOF capture**: the SOF team (player-delivered, bound by `maybe_bind_sof`) assaults
>   the **held command vehicle** and must hold on the **live** commander for `SCAR_SOF_DWELL_S`
>   (the dwell stops co-location instant-firing); killing the commander forfeits the capture.
> - The bridge tests are rewritten to the static contract.
>
> **Still to do** (later phases, separate PRs): the **King designation bridge** (smoke / map mark /
> laser / IR / message) + the **talk-on ID puzzle** + R7, then polish. ⚠️ **Designation is
> voice-first:** the King is a *player* who talks the strikers on over **SRS live voice** — the
> scripted aids are **additive, skippable complements** (for an AI King / silent comms), never a
> scripted-popup-only flow. The moving-model details below describe the retired path (code is
> bypassed, not yet deleted).

- **Planner side (Python, CI-tested):** `FlightType.SCAR` (`game/ato/flighttype.py`,
  air-to-ground primary, `ATTACK_STRIKE`); `ScarFlightPlan` cloned from Armed Recon
  (`game/ato/flightplans/scar.py`) + builder dispatch; `configure_scar`
  (`aircraftbehavior.py`, CAS-family task); fixed-wing-only capability enrichment
  (`game/dcs/aircrafttype.py`); `mission_types` exposure (`missiontarget.py`); CAS loadout
  fallback (`loadouts.py`); primary-task order (`package.py`). SCAR is player-selectable;
  the auto-planner never frags it (no commander task) — auto-planning is a later phase.
  **BAI is deliberately untouched** (still the AI/auto-planner anti-armor/convoy task).
- **Scenario bridge:** `game/missiongenerator/scarluadata.py` builds a `ScarTasking` per
  SCAR-targeted area (`build_scar_taskings(game, mission_start)`), emitted as
  `dcsRetribution.Scar` via `populate_scar_lua`; injected by `_inject_scar_script()` in
  `luagenerator.py` (gated on the `scar` plugin + a planned SCAR flight, mirrors the TARS
  inject pattern). Three variants by target type:
  - `spawn` (generic/rare convoy): spawns the whole ground picture — HVT signature convoy
    (SA-9 + command + 2 trucks) + 2 partial-signature decoys + plain-truck clutter +
    a light threat laydown — fleeing to the nearest enemy-held CP (the "city"). success =
    HVT killed; fail = it reaches the city (command vehicle despawns) or the window expires.
  - `armor` (real, **fully-mobile** `VehicleGroupGroundObject`): binds the REAL group as the
    HVT (flees to the city) and mixes in spawned decoys derived from its live composition. A
    group containing towed/static units (`SCAR_IMMOBILE_GROUND_TYPES` — e.g. a KS-19 flak gun;
    `_group_is_mobile`) is NOT bound (it would strand the immobile unit, 2026-06-20 feedback) —
    it falls through to the fully-mobile `spawn` picture instead.
  - `missile` (real `MissileSiteGroundObject`, SCUD): the launcher races to a firing position
    and actually launches at its target city on arrival (`FireAtPoint`) — the launch is the
    fail. Stock random fire task suppressed for SCAR targets (`MissileSiteGenerator._is_scar_target`).
- **Timing (important — proximity-gated as of 2026-06-21):** the whole picture (HVT + command
  + decoys + clutter) **spawns PARKED at mission start** so the discrimination puzzle is present
  whenever the player arrives, but the columns only **bug out once the strike package crosses the
  activation ring** (`SCAR_PROXIMITY_M`, 50 NM; `package_near` in `scar_414_init.lua`, which counts
  only **human-flown (client) aircraft** so an AI tanker/AWACS/CAP transiting the ring can't start
  the chase before the player gets there). The fail
  clock opens **on activation** (`activate_movement`: `deadline = now + window`), not at mission
  start. This is the A-10 crews' fix (2026-06-20): the target is moving as you arrive but can
  never be "long gone" if the jets are slow. It supersedes two earlier models — the original
  TOT anchor (`go_live_s`; MP doesn't fly a TOT, so it only moved "right as we fired Mavs") and
  the interim move-from-spawn (which leaned on slow pacing as the only escape guard). `go_live_s`
  is still emitted but gates nothing; a kill before activation still counts as success. Each
  parked group is recorded as a `mover` (`add_mover`) and routed on activation via `set_group_route`
  (which forces alarm-GREEN so towed/SCUD groups actually drive; `mist.goRoute` — a hand-rolled
  `setTask` did NOT reliably move them, don't revert). SOF capture binds **lazily** as the HVT
  nears the ambush point (`maybe_bind_sof`). Tunables in `scar_414_init.lua` (`SCAR_PROXIMITY_M`)
  / `scarluadata.py` (`SCAR_TRAVEL_M` ~15 NM, `SCAR_WINDOW_S`). **Verified in-game 2026-06-23**
  (HVT drives/flees on activation; no alarm-RED pinning — checklist F1).
- **Results bridge:** the `scar` plugin (`resources/plugins/scar/`, default ON) writes the
  global `scar_results` (status per tasking); rides the proven TARS channel
  (`dcs_retribution.lua` `write_state` → `StateData.scar_results` in `debriefing.py` →
  `MissionResultsProcessor.commit_scar_results`, currently log-only). Verified round-trip
  in-game 2026-06-17/18 (`SCAR area scar-N: launched/failed`).
- **F10/briefing cues** (R11) drawn from the plugin: target signature, no-strike/firing-position
  marks, decoy warning, addressed to the SCAR flight's coalition. The target mark now points at
  the **search area center** (`centerX/centerY` on the tasking), NOT the exact HVT unit
  (2026-06-20: a pin on the one correct group made it trivial) — combined with spawn-time decoys
  and the HVT moving off its start point, the player must reconnoiter to ID it.
- Tests: `tests/test_scar.py` (FlightType + dispatch), `tests/test_scar_bridge.py`
  (collection/emission/parse). **Lua needs in-game validation (not CI-runnable).**
- Commander-capture campaign engine — **Phase 1 BUILT (gated by `scar_command_post_intel`,
  now default ON for new campaigns while the feature is playtested; existing saves keep their
  stored value)**: the whole commander-capture / SOF / CSAR stack below hangs off this one
  setting (the "(gated …)" markers mean "behind this gate"). Enemy command posts
  (`commandcenter` TGOs) are hidden ENTIRELY from
  the player's map (`TheaterGroundObject.hidden_on_player_map(viewer)` gates `server/tgos/models.py`
  `all_in_game` + `triggergenerator.py` `_gen_markers`) until revealed by capturing a commander
  (`Coalition.captured_commander`, persisted + save-migrated; flipped by a `captured` SCAR result
  in `commit_scar_results`) OR the normal discovery (`_command_post_revealed()` = capture or
  `discovered_by_player`). `known_for` still gates composition. AI/planner use ground truth
  (`viewer=None`). SME-answered 2026-06-18: reveal ALL, permanent, full reveal w/ exact coords,
  ~2-3 posts/campaign. Tests: `tests/test_scar_command_post_fog.py`. **UI/fog side confirmed
  in-game 2026-06-23** (posts hidden; the "Reveal fog of war" overview toggle shows both sides) —
  the full capture→permanent-reveal carryover across turns still owes a pass (checklist F2).
- Commander-capture **Phase 2a + 2c-1 BUILT (gated; capture loop verified in-game 2026-06-23,
  checklist F1)** — the scripted SOF capture loop that PRODUCES the `captured` result. When `scar_command_post_intel` is on, the
  generator allocates a bought, dedicated SOF infantry asset from friendly base inventory and
  drops that team (`mist.dynAdd`, no CTLD dependency yet) at
  `SCAR_SOF_LEAD_FRAC` (0.7) of the HVT's spawn→dest route; the SCAR plugin's `scar_check`
  resolves `captured` when the un-killed command vehicle drives within `SCAR_SOF_CAPTURE_RADIUS_M`
  (600 m) **and the spawned SOF group is still alive**. Priority killed > captured >
  escaped/timeout; spawn + armor variants only. The finite pool uses the distinct
  `SOF Team (BLUFOR|OPFOR)` GroundUnitTypes (price 8); SOF inventory is excluded from
  front-line deployment ratios, combat-strength scoring, and automatic redeployment. A BLUE
  capture spends one BLUE team before base-capture ownership changes are committed. Files:
  `scarluadata.py` (`_sof_ambush`, `sof_*` fields, `_emit_sof`), `scar_414_init.lua`
  (`spawn_sof`, `hvt_in_sof_zone`, the `captured` branch, `mark_sof`). First-pass simplification:
  scripted delivery + auto-on-proximity; the actual player-flown insert is still deferred.
  Plan: `docs/dev/design/414th-scar-phase2-sof-plan.md`. Tests: `tests/test_scar_bridge.py`.
- Commander-capture **Phase 2c-2 BUILT (gated, #56)** — the player-flown insert. A
  `FlightType.SOF` air-assault-shaped delivery flyable by **fixed-wing transports** (the C-130
  "drop"; helos are reserved for recovery) inserts the capture team at the SCAR ambush point; the
  hybrid capture binds to a player-delivered team if one is near, else scripted-spawns a fallback.
  Economy is **debit-on-frag** (`commit_sof_deployments`): one bought team per fragged insert,
  regardless of capture outcome. A clean capture **refunds** the team (it escapes with the
  hostage); a botch **strands** it. See plan §9d. **EW exclusion verified in-game 2026-06-23**
  ("the EW is gone" — the `c130j` plugin is correctly skipped on the SOF C-130; checklist F3).
- Commander-capture **Phase 2c-3 / slice C BUILT (gated; recovery resolves in pure Python, no
  new Lua)** — a botched/late capture strands the team, surfaced next turn as a first-class CSAR
  objective:
  - **Lifecycle** (`game/scar_rescue.py`): `PendingSofRescue` on each `Coalition.pending_csars`
    (save-migrated) ages one turn per `Coalition.end_turn` and is written off at the turn cap
    (default 3) **or** when its anchor base is overrun (`surviving_rescues`).
  - **Surfacing** (`game/scar_objectives.py`, `DownedSofGroundObject`): rebuilt each
    `initialize_turn` into a friendly "downed SOF team" TGO at the strand point, anchored to the
    nearest friendly control point and registered in `db.tgos`; carries the physical team and
    offers only `FlightType.CSAR` to the owning side.
  - **Recovery** (`FlightType.CSAR` → `AirAssaultFlightPlan`, helo-only): a helo extraction;
    `commit_sof_recoveries` recovers the team when a CSAR flight was flown at the objective and the
    helo survived the deep sortie → refunds the bought team + clears the rescue (before captures
    flip ownership). **A Combat SAR flight (§21) can also extract the team** in-mission (MOOSE
    CASEVAC) — `commit_sof_recoveries` credits either path, refunding once.
  - Tests: `tests/test_scar_rescue.py`, `tests/test_scar_objectives.py`,
    `tests/test_aircraft_tasking_roles.py`, `tests/test_scar_command_post_fog.py`. Full design +
    the Python-vs-Lua resolution decision: plan §9e.
- **Mis-ID penalty BUILT (R7, gated by `scar_misid_penalty`)** — destroying one of an area's
  decoy/clutter convoys on a SCAR sortie now costs budget, so picking out the real HVT matters.
  Lua (`scar_414_init.lua`): decoy/clutter spawns register in `misid_group_index`; a new
  `S_EVENT_KILL` branch in `scar_event_handler:onEvent` charges a mis-ID (`record_misid`) only
  when the killer's coalition is the prosecuting (SCAR) side, mirroring a running `misId` count
  onto the area's `scar_results` entry (preserved across `mark_result`). Python:
  `debriefing.py` parses `misId` into `StateData.scar_misid`; `MissionResultsProcessor`
  `_commit_scar_misid` debits `scar_misid_penalty` × count from the offending side's budget
  (`Coalition.adjust_budget`), per blue/red prefix (legacy unprefixed = blue). The setting
  (Campaign Doctrine, default **8** ≈ one SOF team; 0 disables and only logs) makes it tunable
  and additive. Tests: `tests/test_scar_command_post_fog.py` (debit by side, legacy-id, zero
  penalty, no-misid), `tests/test_scar_bridge.py` (parse + Lua-handler wiring). **Lua needs an
  in-game pass.**
- **Phase-3 auto-planning BUILT (opt-in, gated by `scar_autoplan`, default OFF)** — "SCAR
  shows up in the turn's ATO without the player building it." `PlanScarHunts`
  (`game/commander/tasks/compound/scarhunts.py`) frags **one** player-flyable SCAR package per
  turn against the highest-priority enemy battle position, via the thin `PlanScar`
  (`primitive/scar.py`, BAI-shaped: `FlightType.SCAR` + common escorts). Wired late/low-priority
  in `PlanNextAction` (after `DegradeIads`). **Blue-only by design** — SCAR is a human
  discrimination puzzle, so the AI keeps using BAI for anti-armor and never frags SCAR for
  itself. Default OFF so it's a strict no-op until the SCAR in-mission Lua (F1/F3/F5) has had a
  cockpit pass; flip the setting (or its default) once that's done. Tests:
  `tests/test_scar_autoplan.py` (off/red/no-target no-op, blue picks top battle position,
  `PlanScar` proposes SCAR + escorts). If Tyler's C-130 `DEPLOYMENT` work ever lands, our
  `FlightType.SOF` + inventory-debit-on-frag should converge onto his `PendingDeployments`
  shape (shared `Coalition` + `MissionResultsProcessor` + `FlightType`).

### SOF insert generation fixes (2026-06-22)

Two fixes so the SOF C-130 airdrop actually generates as a flyable ground sortie:

- **Forced air spawn → runway fallback** (`game/missiongenerator/aircraft/flightgroupspawner.py`,
  `generate_flight_at_departure`). On `NoParkingSlotError` Retribution force-converted a planned
  ground start to `IN_FLIGHT`; the SOF C-130 (a large aircraft that often finds no large parking
  slot) air-spawned despite a ground start being selected. The "try a runway start before the air
  start" retry was previously gated to `FlightType.JAMMING` only — now it applies to **any
  non-helo flight** with a cold/warm start at an airfield (runway starts need no parking slot).
  Helos (helipads/ground spawns) are unaffected.
- **EW plugin de-conflict** (`game/missiongenerator/luagenerator.py`, `inject_plugins` +
  `_sof_c130_present`). The C-130J Mission Systems (EW/ISR) plugin attaches to **every**
  `C-130J-30` by airframe alone (`eligibleTypeNames = {["C-130J-30"]=true}` in
  `c130j_mission_systems.lua`), so it would bolt the EW menu/behavior onto a SOF insert flown by
  the same airframe. When any planned `FlightType.SOF` flight is a C-130J-30, the `c130j` plugin
  is skipped for that mission (logged). Tradeoff: you can't fly the EW jet and run a SOF insert in
  the same mission; letting them coexist would need a Lua-side per-group exclusion instead.
  **EW de-conflict verified in-game 2026-06-23** ("the EW is gone" on the SOF C-130; checklist
  F3); the runway-fallback half still wants a pass. Both are upstream-PR candidates (the runway
  fallback is a general spawner fix; the EW gate is fork-specific to the `c130j` plugin).

---

## 16. Settings semantic cleanup and audit

The core settings model and every active plugin definition received a consumer-level
audit (2026-06-18). UI work is intentionally separate; the full grouping/dependency
handoff lives in [`docs/dev/settings-qol-audit.md`](settings-qol-audit.md).

- **Removed four dead/duplicate fields** (`game/settings/settings.py`): unused
  `prefer_squadrons_with_matching_primary_task`, duplicate `pretense_num_of_cargo_planes`,
  permanently-disabled `nevatim_parking_fix` (plus its Nevatim/Ramon restricted-slot code
  in `flightgroupspawner.py` and the `Migrator` force-off line), and the hidden legacy
  `only_player_takeoff`.
- **Consolidated the AI-radio booleans** (`limit_ai_radios` + `silence_ai_radios`) into the
  `AiRadioBehavior` enum (`FULL`, `LIMITED`, `SILENT`). `Settings.__setstate__` runs
  `_migrate_legacy_settings` to map every old boolean combination deterministically and
  strip the retired keys, so existing campaign/settings files load without carrying dead
  state forward. The new enum is registered in `SERIALIZABLE_ENUM_TYPES` so the hardened
  enum-deserialization path accepts it. Covered by `tests/settings/test_settings_qol_migration.py`.
- **Plugin wording**: `descriptionInUI` added to the QRA `intercept` and `splashdamage3`
  plugins (the latter notes its tuning is locked by design). Splash Damage values and the
  tuned script are unchanged.

---

## 17. Auto-planner target unpredictability

The theater commander's HTN (`game/commander/theatercommander.py`) is a deterministic,
strict-priority planner: given the same campaign state it picks the same targets in the
same order every turn, which reads as "scripted" in game (the enemy hits the same things
on the same cadence). This feature adds an opt-in, tunable amount of randomness to which
*opportunistic* offensive targets get serviced first, without ever deferring a real
defensive threat response.

- **The lever** is `game/commander/tasks/targetorder.py` `shuffled_by_priority(items, state)`.
  It takes an already-priority-sorted candidate list and reorders it with
  Efraimidis–Spirakis weighted sampling (weight `decay**rank`, `decay = strength/100`). At
  strength 0 it returns the list unchanged (strict priority); as strength rises, lower-rank
  targets become progressively more likely to be picked first, while the top target stays
  the single most likely pick at any non-extreme setting.
- **Two settings** (`game/settings/settings.py`, Campaign Doctrine / General):
  `ownfor_planner_unpredictability` and `opfor_planner_unpredictability` (0–100, **default 0**).
  The helper reads the knob for the planning coalition's side. Default 0 preserves the exact
  deterministic planner, so existing campaigns and tests are unchanged.
- **Wired into the opportunistic compound tasks only**: `AttackBuildings` (strike),
  `AttackShips` (anti-ship), `AttackAirInfrastructure` (OCA), `AttackBattlePositions` (BAI),
  and the **non-threatening** tiers of `DegradeIads` (opportunistic DEAD / detector
  suppression). The reactive `DegradeIads` tier (`state.threatening_air_defenses` — SAMs
  actually threatening a planned target) is left strictly deterministic on purpose, as are
  BARCAP wave scheduling, escort sizing, and the QRA dispatcher. Variety never delays a
  threat response.
- **Tests**: `tests/test_planner_unpredictability.py` (identity at 0, correct-side knob,
  permutation invariant, top-priority favored).

This is the low-risk, in-Python alternative to a runtime MOOSE `Ops.Chief` rewrite of red
planning: it makes red's offensive target selection feel less repetitive while keeping the
campaign economy, attrition, and BDA coupling intact and unit-testable.

---

## Still in flight / deferred

- Aircraft task-priority rebalance: a **conservative, intent-preserving outliers pass**
  landed 2026-06-15 (20 files, 31 changes) driven by a documented role-band rubric —
  `docs/dev/design/414th-aircraft-task-rebalance-rubric.md` + `tools/rebalance_aircraft_tasks.py`.
  It excludes discarded-mod airframes, only tightens over-high secondary roles (never adds
  roles or inflates deliberate suppressions). The **full "tighten everywhere" rebalance
  remains held** until in-game scramble/CAP validation. Earlier targeted fixes also landed
  (Tu-22M3 anti-ship 815, M-2000C A2A).
- Reactive scramble is **retired** — the old 414th ramp-scramble system (border trigger
  -> cold start -> takeoff -> intercept) was replaced by the upstream PR #782 QRA
  dispatcher (see [§1 QRA intercept reserve](#1-qra-intercept-reserve) above), and
  `reactive_scramble.lua` + `FlightType.SCRAMBLE` were removed. The live A2A path to
  validate in-game is now the Moose `AI_A2A_DISPATCHER` QRA flow, not ramp-scramble.

---

## 18. Unified map layers panel

The two stock react-leaflet layer controls (a flat 23-item white box top-right, plus a
second top-left box for threat zones / navmesh / terrain) are replaced by one custom,
dark-themed control: `client/src/components/maplayers/MapLayersControl.tsx` (+ `.css`).

- It is a Leaflet `L.Control` that `createPortal`s a React panel onto the map and owns the
  visibility of every overlay. Each layer is conditionally rendered from state instead of
  via `LayersControl.Overlay`, so the panel can group, theme, collapse, and preset freely.
- **Collapsible groups** (Friendly & shared / Air defences / Enemy intel / Allied & flight
  plans / Threat zones / Navmesh & terrain). The advanced groups start collapsed so the list
  stays short; group + layer + base-map choices persist to `localStorage`
  (`fjg.mapLayers.v1` → bumped to `…v2`), except the fog overview (see §3).
- **Preset views** — Default / SEAD / Recon / Clean, plus a "Hide all overlays" button.
- **Folded in the old top-left control**: threat zones render via the existing
  `ThreatZonesLayer` (+ `ThreatZoneFilter`) and navmesh via `NavMeshLayer` (both already raw);
  terrain and culling gained raw-layer exports (`Inclusion/Exclusion/SeaZonesLayer`,
  `CullingExclusionLayer`) so they render without a `LayersControl`. The hard-disabled
  waypoint join/hold debug zones were dropped.
- **Side-effect toggles** (fog reveal, radar-emitter highlight) are driven by `useEffect` on
  their checkbox state, NOT by Leaflet `add`/`remove` — unmount does not reliably fire
  `remove`, which previously left the fog overview stuck on. The old `FogOfWarToggle` /
  `EmitterHighlightToggle` components were removed.
- Client-only (TS/CSS); needs the rebuilt bundle (CI `npm run build`). `LiberationMap.tsx`
  now mounts just `MapLayersControl` (plus scale + ruler).
- Cleanup done: the orphaned `CoalitionThreatZones` / `WaypointDebugZonesControls`
  components were removed, and `TerrainZonesLayers`/`CullingExclusionZones` now export only
  the raw-layer variants the panel uses (no dead default exports). The remaining
  `getDebugHoldZones`/`getDebugJoinZones` names are generated API bindings, not UI.

---

## §20 — Drop-spawn: Map Right-Click Unit Placement

**Status:** Functional; needs an in-game pass (§20 checklist rows 20-A…20-G).
No Lua component — Python/Qt planner + React client only.

Right-click on blank map space → Qt dialog → spawn a new unit group (armor,
SAM, EWR, ship, missile/coastal) at any map position, attached to the nearest
friendly CP.

**Cheat-gated (important).** The map right-click only opens the placement dialog
when `enable_unit_placement` is on (default OFF). With the cheat off, a plain
right-click stays free for normal map use — e.g. right-clicking a target marker to
plan a package — and never pops the buy dialog. The gate is enforced in
`QLiberationWindow.open_place_unit_group_dialog` (the single Qt chokepoint every
map right-click funnels through); the client still posts to `/qt/place-unit-group`
on every right-click, which simply no-ops when the cheat is disabled. *(Regression
fixed 2026-06-25: the gate was previously missing, so the dialog hijacked every
right-click — including package-planning ones — regardless of the setting.)*

### Files

| Layer | File |
|---|---|
| Data model | `game/theater/theatergroundobject.py` (`user_placed`, `respawn_enabled`, `pending_deploy`) |
| Core logic | `game/theater/unitplacement.py` — `place_unit_group()`, `PendingUnitPlacement`, `process_pending_placements()`, `process_respawns()` |
| Settings | `game/settings/settings.py` — `enable_unit_placement`, `enable_free_unit_placement` |
| Game state | `game/game.py` — `pending_unit_placements: list[Any]`, turn hook, `__setstate__` migration |
| Server | `game/server/qt/routes.py` — `POST /qt/place-unit-group` |
| Server | `game/server/tgos/routes.py` — `DELETE /tgos/{id}` |
| Server | `game/server/tgos/models.py` — `TgoJs.user_placed` |
| Server events | `game/sim/gameupdateevents.py` — `deleted_tgos`, `delete_tgo()` |
| Server events | `game/server/eventstream/models.py` — `GameUpdateEventsJs.deleted_tgos` |
| Qt callback | `game/server/dependencies.py` — `QtCallbacks.open_place_unit_group_dialog` |
| Qt dialog | `qt_ui/windows/groundobject/QPlaceUnitGroupDialog.py` |
| Qt window | `qt_ui/windows/QLiberationWindow.py` — `place_unit_group_signal` |
| Qt settings | `qt_ui/windows/settings/QSettingsWindow.py` — two cheat checkboxes |
| React API | `client/src/api/_liberationApi.ts` — `openPlaceUnitGroupDialog`, `deleteUserPlacedTgo`, `Tgo.user_placed` |
| React state | `client/src/api/tgosSlice.ts` — `removeTgo` |
| React events | `client/src/api/eventstream.tsx` — `deleted_tgos` dispatch |
| React map | `client/src/components/liberationmap/MapContextMenu.tsx` |
| React map | `client/src/components/liberationmap/LiberationMap.tsx` — mounts `MapContextMenu` |
| React TGO | `client/src/components/tgos/Tgo.tsx` — right-click Remove for `user_placed` |

### Behaviour

- Right-click blank map → `MapContextMenu` fires `POST /qt/place-unit-group(lat, lng)`.
- Qt signal opens `QPlaceUnitGroupDialog`:
  - **Coalition** selector (Red locked behind `enable_enemy_buy_sell` cheat).
  - **Category** dropdown — Air Defense SAM/AAA, EWR, Coastal/Missile, Ground Force, Navy.
  - **Unit type** dropdown — populated from `LAYOUTS.layouts` directly (not `ArmedForces`), so every named layout usable by the faction appears (S-300, SA-2, Patriot, NASAMS, Early-Warning Radar, etc.), not just what the faction normally auto-spawns. `ForceGroup.for_layout(layout, faction)` is created on-the-fly per selection.
  - **Unit rows** — `QTgoLayoutGroupRow` widgets (reuse buy-menu pattern): unit type selector + count spinner per layout group.
  - **Deploy timing** — Spawn Now / Deploy Next Turn.
  - **Respawn** checkbox — auto-revive on destruction each turn.
  - **Cost / budget** label; Place button disabled when over budget (unless free cheat).
- On confirm: `place_unit_group()` validates terrain + range (200 km from nearest friendly CP, bypassed by `enable_free_unit_placement`), creates TGO, attaches to CP, registers in `game.db.tgos`, fires SSE `update_tgo` so the marker appears immediately.
- Deploy Next Turn: queues `PendingUnitPlacement` on `game.pending_unit_placements`; materialised by `process_pending_placements()` at turn start. Budget deducted at queue time.
- Auto-respawn: `process_respawns()` revives a destroyed user-placed TGO each turn.
- Right-click on a user-placed TGO → **Remove** → `DELETE /tgos/{id}` → SSE `delete_tgo` → marker removed from React map.

### Dialog unit-type enumeration

The dialog uses `LAYOUTS.layouts` + `ForceGroup.for_layout(layout, faction)` instead of the
faction's `ArmedForces` groups. This is intentional: `ArmedForces` only contains groups the
faction is configured to auto-spawn (preset groups + generic layouts that passed faction unit
checks at game-start). The LAYOUTS approach gives the full menu of 66 named layouts — every
SAM system, EWR variant, and ship class the campaign engine knows about — filtered down to
what the selected faction can actually field. If a category shows "(no compatible units for
this faction)" the faction has no units in the matching `unit_classes` for that layout type.

### Deferred

- Terrain ring overlay (`PlacementModeOverlay.tsx`) — visual land/sea feedback while hovering before click.
- Pending markers layer — semi-transparent map markers for "deploy next turn" TGOs.
- FOB establishment — via the same dialog, creates a `Fob` control point dynamically.
- Relocate — delete + re-place with pre-filled dialog.
- Budget refund on Remove — `TheaterUnit` lacks a stored price field; needs separate cost tracking on `TheaterGroundObject`.

---

## §21 — Combat SAR — pilot rescue (flight type + `combatsar` plugin, scoring ON)

**Status:** Built (phases 1–4) + rescue scoring; needs an in-game pass (checklist
G8–G10, H2, and the G11 scoring row). Python plans + scores; MOOSE CSAR (Lua) executes.
Design source of truth: [`docs/dev/design/414th-combat-sar-spec.md`](design/414th-combat-sar-spec.md).

A bespoke pilot-rescue flight task, distinct from the SOF-recovery `FlightType.CSAR`
in the SCAR loop (§15). A **CH-47** orbits near the FLOT as the rescuer; a **C-130**
flies the overhead **HC-130 "King"** on-scene-command orbit. When a **human** pilot
ejects in the area, MOOSE CSAR spawns the downed pilot with a beacon and the CH-47
flies in, lands, and delivers them to any friendly field/FARP — and the campaign
**spares that aviator** at debrief (the airframe is still lost; the experienced pilot
returns to the squadron).

### Architecture (Python plans + scores, Lua executes)

- **`FlightType.COMBAT_SAR`** — player-selectable for CH-47 (rescue) and C-130 (King). It
  flies a **dedicated forward-hold plan** (`game/ato/flightplans/combatsar.py`,
  `CombatSarFlightPlan`): front-anchored like AEW&C, but with a **short threat buffer**
  (`COMBAT_SAR_THREAT_BUFFER`, 15 NM — just clear of FLOT SHORAD/MANPAD reach) and a
  **helo-sized racetrack** (`COMBAT_SAR_RACETRACK_HALF_DISTANCE`, 5 NM), so the rescue helo
  holds *near the front* where it can actually reach an ejection — **not** at the 80 NM AWACS
  standoff. `CombatSarFlightPlan` subclasses `AewcFlightPlan` (and its `Builder` subclasses the
  AEW&C `Builder`) purely to keep the existing support-flight integration that keys off
  `isinstance(.., AewcFlightPlan)` (AWACS-info registration, DTC orbit exclusion) — only the
  geometry differs. Helos clamp to a helo-appropriate AGL via the shared `get_altitude` path.
  (Earlier builds reused the AEW&C builder outright, which parked the CH-47 at AWACS depth — a
  G9 in-game finding, fixed 2026-06-25.)
- **AI standing alert** — `Settings.auto_combat_sar` (HQ automation, default OFF) auto-plans
  one COMBAT_SAR orbit per turn for blue via `PlanCombatSar` / `PlanCombatSarSupport`
  (mirrors AEWC/refuel support). With it on, the generator emits `enableForAI=true`, so
  MOOSE CSAR may commandeer an orbiting AI CH-47 and AI ejections become rescuable.
- **King beacon = TACAN only.** Each King lights an **air-tracking TACAN** (follows the
  moving orbit; every rescue helo we use has a receiver) — the single homing solution.
  An ADF radio beacon was **considered and dropped** (MOOSE's `RadioBeacon` is fixed-point
  and the King is a mover, so it would need a position-refresh loop for no gain over the
  TACAN). The King also carries an F10 **Combat SAR → LARS** button that reads MOOSE CSAR's
  live downed-pilot table and reports each active survivor (position + bearing/range from
  the King) for the crew to relay.
- **Airframes (player-flyable + armed).** The rescuer is the **CH-47Fbl1** (the playable ED
  Chinook, `Combat SAR: 85` in its yaml) with a **`Retribution Combat SAR` payload that mounts
  the port + starboard door M60D guns** (`{CH47_PORT_M60D}`/`{CH47_STBD_M60D}`,
  `resources/customized_payloads/CH-47Fbl1.lua`) for self-protection on the way in; the AI
  **CH-47D** stays a `Combat SAR` fallback (no weapon stations). The King is the
  **C-130J-30** — the player-flyable Airplane Simulation Company module, now the **only** C-130
  in the fork (the stock AI C-130 was retired; see "C-130 consolidation" below). Its external
  underwing tanks are a **removable module pylon, not model-default**, so the King gets its own
  **`Retribution Combat SAR` payload** mounting both wing tanks (`{C130J_Ext_Tank_L}` Pylon 1 +
  `{C130J_Ext_Tank_R}` Pylon 2, `resources/customized_payloads/C-130J-30.lua`) — without it the
  King spawned clean / tankless (a G13 in-game finding, fixed 2026-06-25). (Loadout names resolve
  `Retribution Combat SAR` → `Liberation Combat SAR` → empty; an airframe with no Combat SAR
  payload just flies clean.)
  Because the EW (`c130j`) plugin claims every C-130J-30 by airframe, the generator suppresses
  it for any mission with a SOF-insert or Combat SAR King C-130J-30 (`_non_ew_c130j_present`) so
  the King flies clean.

### Rescue scoring (the gameplay-loop payoff)

The whole point of a rescue is to save the pilot, so the loop closes in the campaign model:

- **Lua** (`combatsar-config.lua`): FSM hooks `OnAfterBoarded` capture each onboard pilot's
  **original ejected aircraft unit name** (MOOSE CSAR keeps it on the downed-pilot track and
  carries it into `inTransitGroups`); `OnAfterRescued` — fired only on a successful **delivery
  to a friendly field** — appends those names to the shared `combat_sar_rescues` global and
  marks `dirty_state` so `dcs_retribution.lua` writes them into `state.json`. A helo shot down
  with pilots aboard never reaches `Rescued`, so those pilots are (correctly) never credited.
- **Python**: `StateData.combat_sar_rescues` parses the list (`debriefing.py`);
  `MissionResultsProcessor.commit_air_losses` resolves each name through the unit map to its
  loss and **skips `loss.pilot.kill()`** for it — the airframe is still attrited, the aviator
  survives. **Fail-safe:** an empty/absent list is exactly today's behaviour (pilot dies).

### Files

| Layer | File |
|---|---|
| Flight type | `game/ato/flighttype.py` — `COMBAT_SAR` |
| Airframes | rescuer **CH-47Fbl1** (+ AI `CH-47D` fallback) and King **C-130J-30** (the only C-130) carry `Combat SAR` in `resources/units/aircraft/*.yaml`; door-gun loadout in `resources/customized_payloads/CH-47Fbl1.lua` (`Retribution Combat SAR`). EW de-conflict: `luagenerator._non_ew_c130j_present` |
| Flight plan | reuses `game/ato/flightplans/aewc.py` (FLOT support orbit) |
| Planning | `game/commander/tasks/primitive/combatsar.py`, `…/compound/combatsarsupport.py`, `theaterstate.py` (`combat_sar_targets`) |
| Setting | `game/settings/settings.py` — `auto_combat_sar` |
| King beacon | `game/missiongenerator/aircraft/flightdata.py` (`CombatSarKingBeacon`, TACAN-only), `flightgroupconfigurator.py` (`register_combat_sar_king`) |
| Emit data | `game/missiongenerator/luagenerator.py` — `_generate_combat_sar` (rescueHelos / kings / pilotTemplate / enableForAI) |
| Kneeboard | `game/missiongenerator/kneeboard.py` — `CombatSarTaskPage` |
| Scoring (Lua) | `resources/plugins/base/dcs_retribution.lua` (`combat_sar_rescues` global + `write_state`), `resources/plugins/combatsar/combatsar-config.lua` (CSAR bridge + `OnAfterBoarded`/`OnAfterRescued`) |
| Scoring (Py) | `game/debriefing.py` (`StateData.combat_sar_rescues`), `game/sim/missionresultsprocessor.py` (`commit_air_losses` spares rescued pilots) |
| SOF recovery | `game/scar_rescue.py` (`sof_rescue_pickup_name`), `luagenerator.py` (emits `sofTeams`), `combatsar-config.lua` (`SpawnCASEVAC` + `SOFRESCUE` routing → `combat_sar_sof_recoveries`), `dcs_retribution.lua` (global), `debriefing.py` (`StateData.combat_sar_sof_recoveries`), `missionresultsprocessor.py` (`commit_sof_recoveries` credits a delivered team) |
| Tests | `tests/test_combat_sar_scoring.py` |

### Gotchas

- **Combat SAR also handles the SOF recovery** (§15): the same rescue helo can extract a stranded
  SCAR SOF team in-mission. The generator emits each on-map team (`self.game.blue.pending_csars`,
  anchored) and the plugin spawns it as a MOOSE CSAR **CASEVAC** (`SpawnCASEVAC`) at its strand
  point; the helo boards + delivers it like a downed pilot. The CASEVAC name is
  `SOFRESCUE_<x>_<y>` (`sof_rescue_pickup_name`), routed by `OnAfterRescued` to the
  `combat_sar_sof_recoveries` global; `commit_sof_recoveries` recomputes the name per
  `PendingSofRescue` to clear it + refund the team — *alongside* (not replacing) the dedicated
  `FlightType.CSAR` air-assault recovery, and a team recovered by both refunds once. The SOF
  *insert* (CTLD C-130) is untouched. AI participation follows `auto_combat_sar` (the AI alert will
  divert deep to extract a team — risky by design).
- **No double ejection-handling.** The MOOSE `CSAR` engine is the only ejection listener (CTLD's
  handler is commented out, `CTLD.lua:8254`); the SOF *team* is a CASEVAC ground pickup, never an
  ejection. The pilot-sparing (`combat_sar_rescues`) and SOF-recovery (`combat_sar_sof_recoveries`)
  channels stay distinct, routed by the `SOFRESCUE` name prefix. The F10 "CSAR" menu shows on any
  helo player, but pickups are gated to the Combat SAR rescue set (`SetOwnSetPilotGroups`).
- **Blue-only.** The CSAR engine is built for `"blue"`; a red COMBAT_SAR would just fly an
  inert orbit, so red is never auto-tasked.
- **King ≠ tanker.** The C-130 cannot be a DCS aerial-refueling tanker, and the CH-47 couldn't
  take its fuel anyway — the King is overhead presence / on-scene command, never wired to the
  refueling system.
