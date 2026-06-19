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
  `QRA_AIRSTART_SPEED_MS` onto its waypoints so Moose in-air spawns do not drop early
  jets nearly stationary and stall them.
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
  `game/theater/missiontarget.py`, `game/pretense/pretenseaircraftgenerator.py`.

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
fully hides enemy command posts for the gated-OFF SCAR commander-capture feature — see
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
controls three behaviors together when set to Approximate:

- Player-only target steerpoints are offset to a randomised area within 2–6 NM of
  the real target rather than placed exactly on it. The waypoint is renamed
  `TARGET AREA`. AI attack logic is unaffected.
  (`game/ato/flightplans/waypointbuilder.py` `_player_visible_target_area_position()`)
- Objective F10 map marks are suppressed even if `generate_marks` is on.
  (`game/missiongenerator/triggergenerator.py`,
  `game/pretense/pretensetriggergenerator.py`)
- Strike / SEAD / DEAD kneeboard target pages omit exact coordinates and instead
  cue the player to search the target area.
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
  fixed-wing aircraft` (coarse on purpose: all fixed-wing, not just A2A; cheap +
  save-stable). `theaterstate.py` `threat_weighted_barcap_rounds()` = `baseline +
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
  navmesh routing hazard. `ThreatZones._front_line_threat_zone()` buffers a capsule along
  each active FrontLine (perpendicular to the blue->red axis, `FRONT_LINE_THREAT_BUFFER`
  = 10 NM) and folds it into `self.all` **only** — the geometry the navmesh + generic
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
  - `armor` (real `VehicleGroupGroundObject`): binds the REAL group as the HVT (flees to the
    city) and mixes in spawned decoys derived from its live composition.
  - `missile` (real `MissileSiteGroundObject`, SCUD): the launcher races to a firing position
    and actually launches at its target city on arrival (`FireAtPoint`) — the launch is the
    fail. Stock random fire task suppressed for SCAR targets (`MissileSiteGenerator._is_scar_target`).
- **Timing (important):** the scenario is anchored to the flight's **TOT**
  (`go_live_s = time_over_target − mission.start_time`), not mission start, with a generous
  window (`SCAR_WINDOW_S`, 20 min) and an early-start lead (`SCAR_START_LEAD_S`, 10 min) so
  the target is already on the move when the player arrives. Bound real groups move via
  `mist.goRoute` (a hand-rolled `setTask` did NOT reliably move them — don't revert).
  Distances/timing in `scarluadata.py` are first-pass tunables (`SCAR_TRAVEL_M` ~15 NM).
- **Results bridge:** the `scar` plugin (`resources/plugins/scar/`, default ON) writes the
  global `scar_results` (status per tasking); rides the proven TARS channel
  (`dcs_retribution.lua` `write_state` → `StateData.scar_results` in `debriefing.py` →
  `MissionResultsProcessor.commit_scar_results`, currently log-only). Verified round-trip
  in-game 2026-06-17/18 (`SCAR area scar-N: launched/failed`).
- **F10/briefing cues** (R11) drawn from the plugin: target signature, ingress axis,
  no-strike/firing-position marks, decoy warning, addressed to the SCAR flight's coalition.
- Tests: `tests/test_scar.py` (FlightType + dispatch), `tests/test_scar_bridge.py`
  (collection/emission/parse). **Lua needs in-game validation (not CI-runnable).**
- Commander-capture campaign engine — **Phase 1 BUILT (gated OFF, `scar_command_post_intel`
  setting, default OFF)**: enemy command posts (`commandcenter` TGOs) are hidden ENTIRELY from
  the player's map (`TheaterGroundObject.hidden_on_player_map(viewer)` gates `server/tgos/models.py`
  `all_in_game` + `triggergenerator.py` `_gen_markers`) until revealed by capturing a commander
  (`Coalition.captured_commander`, persisted + save-migrated; flipped by a `captured` SCAR result
  in `commit_scar_results`) OR the normal discovery (`_command_post_revealed()` = capture or
  `discovered_by_player`). `known_for` still gates composition. AI/planner use ground truth
  (`viewer=None`). SME-answered 2026-06-18: reveal ALL, permanent, full reveal w/ exact coords,
  ~2-3 posts/campaign. Tests: `tests/test_scar_command_post_fog.py`.
- Commander-capture **Phase 2a + 2c-1 BUILT (gated OFF, needs an in-game pass)** — the scripted SOF
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
- NOT yet built: **Phase 2c-2/2c-3** — player-flown air-assault/CTLD delivery replacing the
  scripted drop, then CSAR recovery on botch. SME: finite SOF ~2-3/campaign;
  botched = commander escapes but SOF recoverable via CSAR. mis-ID penalty stays NONE;
  Phase-3 auto-planning. **Coordinate with Tyler's C-130 `DEPLOYMENT` work** — his
  `PendingDeployments`/air-assault-CTLD pattern is the template for 2b/2c (shared `Coalition` +
  `MissionResultsProcessor` + `FlightType` surface).

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
