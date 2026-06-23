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
  high-elevation fields. Both are tunable and need an in-game pass.
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
  gives a **rough bullseye** (`Bullseye <brg> for <nm>`, bearing rounded to the
  nearest degree and range to the nearest NM, accurate to ~1 NM) as the Cue.
  DEAD always uses the bullseye cue even with Exact intel. The STPT column pairs each
  listed target to its per-target `TARGET_POINT` waypoint **by order** (not position),
  so it stays populated even when Approximate intel offsets the waypoint.
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
  2x. `TheaterState.from_game` wires it into `barcaps_needed`. **Volume only** — threat-
  weighted *orbit placement* is a deferred separate increment, not yet done. Design notes:
  `docs/dev/design/414th-air-defense-planning-notes.md`. Tests:
  `tests/test_barcap_threat_weighting.py`.
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
  stacking). **Lua-free but needs an in-game pass on a coastline map to confirm placement.**
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
(`dead_can_reach` geometry + `apply_effects` routing). **Lua-free; still wants an in-game pass
to confirm blue now defers deep strikes until the belt is actually down.**

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
- Tests: `tests/test_tars_bda_bridge.py`. Default ON; Lua still needs an in-game pass
  (not runnable in CI).

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
- Tests: `tests/test_flightcontrol_emit.py`. Default ON; Lua still needs an in-game pass
  (not runnable in CI).

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

A player-flown `FlightType.SCAR`: work a defined area to find and prosecute a moving
high-value target hidden among look-alike decoys + clutter and light AAA, before it
reaches safety. Design ground truth: `docs/dev/design/414th-scar-task-spec.md` (read
before touching). SME-facing open questions: `docs/dev/design/414th-scar-commander-sme-questions.md`.

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
  / `scarluadata.py` (`SCAR_TRAVEL_M` ~15 NM, `SCAR_WINDOW_S`). **Needs an in-game pass.**
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
  ~2-3 posts/campaign. Tests: `tests/test_scar_command_post_fog.py`.
- Commander-capture **Phase 2a + 2c-1 BUILT (gated, needs an in-game pass)** — the scripted SOF
  capture loop that PRODUCES the `captured` result. When `scar_command_post_intel` is on, the
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
  hostage); a botch **strands** it. See plan §9d.
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
    flip ownership).
  - Tests: `tests/test_scar_rescue.py`, `tests/test_scar_objectives.py`,
    `tests/test_aircraft_tasking_roles.py`, `tests/test_scar_command_post_fog.py`. Full design +
    the Python-vs-Lua resolution decision: plan §9e.
- NOT yet built: mis-ID penalty stays NONE; Phase-3 auto-planning. If Tyler's C-130 `DEPLOYMENT`
  work ever lands, our `FlightType.SOF` + inventory-debit-on-frag should converge onto his
  `PendingDeployments` shape (shared `Coalition` + `MissionResultsProcessor` + `FlightType`).

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
