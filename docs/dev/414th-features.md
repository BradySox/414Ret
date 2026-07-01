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

### Player-manned QRA (2026-06-29)

A human pilot can man part of a squadron's QRA reserve instead of leaving it all to the AI
dispatcher (design note `docs/dev/design/414th-qra-player-manning-notes.md`; in-game pass A3).
The AI QRA is a runtime MOOSE air-spawn with no ATO flight to take a slot on, so the player
share is fragged as a **real ATO flight** at planning instead — a cold-start, home-field
base-defense BARCAP the player sits on the pad and scrambles at will.

- Model: `Squadron.qra_player_manned` (per squadron, default 0, `__setstate__` migrates old
  saves) records how many of `intercept_reserve` the player flies. It only re-labels reserve
  airframes — `untasked_aircraft` already excludes the whole reserve, so the planner pool is
  untouched.
- Accounting (`game/squadrons/intercept_reserve.py`): `qra_player_manned_count()` clamps the
  setting to the reserve and owned airframes; `ai_qra_resource_count()` carves the manned
  airframes out of both the reserve and owned pool before the usual `qra_resource_count`
  clamp, so the AI dispatcher fields only the player's leftovers (no double-spawn). The
  available-pilot cap is *not* re-reduced — the alert flight already claimed its pilots at
  planning. Both the generator and the debrief baseline call `ai_qra_resource_count` so the
  AI count and its loss reconciliation always agree. Tests in
  `tests/squadrons/test_intercept_reserve.py`.
- Home-field orbit: `HomeBaseDefenseZone` (`game/theater/missiontarget.py`) is the package
  target; `CapBuilder.cap_racetrack_for_objective` (`game/ato/flightplans/capbuilder.py`) lays
  a short racetrack **straddling the base** (oriented toward the nearest enemy field) instead
  of pushing forward like a control-point BARCAP.
- Generation hook: `Coalition._plan_player_qra()` (`game/coalition.py`), called from
  `plan_missions` **BLUE only** after scheduling, frags one `HomeBaseDefenseZone` BARCAP
  package per eligible squadron (airfield-based, BARCAP-capable, flyable) with `manned`
  cold-start airframes, `claim_inv=False` (the airframes come from the reserve, not the
  untasked pool), every member marked a player slot, a normal flight plan + ASAP TOT. Because
  it's a real ATO flight it gets the full loadout/kneeboard/debrief treatment and is editable.
- Dispatcher debit: `spawn_intercept_templates()` now seeds the `InterceptEntry.resource_count`
  from `ai_qra_resource_count`, so the runtime dispatcher launches the reserve minus the
  player's share.
- UI: a dependent "…of which player-manned" spinbox under the QRA reserve in
  `qt_ui/windows/SquadronDialog.py`, bounded by the reserve and synced when it changes.
- Scramble cue (Phase 3): `spawn_intercept_templates` also emits a `PlayerAlertEntry`
  (`game/missiongenerator/interceptluadata.py`, `dcsRetribution.Intercept.PLAYER_ALERT`) per
  blue manned base; `resources/plugins/intercept/intercept-config.lua` runs a periodic scan
  that calls the player to scramble (`outTextForCoalition`, "QRA SCRAMBLE — base: bandits
  BRG/range, angels N") when a hostile aircraft closes inside the **cue radius** = the AI GCI
  radius **+ `PLAYER_SCRAMBLE_LEAD_NM`** (default 30 NM), so a cold start has spool-up + taxi
  time. Player-facing only — it never launches anything; the human decides. Debounced per base
  (`PLAYER_ALERT_REPEAT`). Needs an in-game pass (A4).
- AI-wingman crewing: `Squadron.qra_player_ai_wingman` (default False) flips how the alert
  flight is crewed without touching its size or the dispatcher debit —
  `qra_player_client_slots()` returns the whole flight (every airframe a client slot, co-op
  alert) when off, or just the lead (rest fly as AI wingmen, single-player section) when on.
  `Coalition._plan_player_qra` marks `member.pilot.player` per slot accordingly. UI: a "Fly
  lead, rest are AI wingmen" checkbox under the spinbox.
- Runtime (cold alert spawn + flight plan + scramble cue) **verified in-game 2026-07-01** (checklist
  A3/A4 — user pass "A3/A4 good").

Legacy note: the old ramp-scramble system has been fully retired — the upstream PR #782
dispatcher above is the only live QRA path. Both the `reactive_scramble.lua` script and the
`FlightType.SCRAMBLE` enum (plus its `Scramble:` aircraft-task weights and `- Scramble`
squadron mission-type entries in `resources/units|squadrons|campaigns/*.yaml`) have been
removed. SCRAMBLE always behaved as a BARCAP, so old saves are migrated SCRAMBLE -> BARCAP
in one place: `FlightType._missing_`'s `_LEGACY_FLIGHT_TYPE_VALUES` table (runtime lookups);
the unpickler (`persistency.py` `_handle_flight_type`) routes legacy values through
`FlightType(value)` → `_missing_`, so it no longer duplicates the remap.
`FlightType.INTERCEPTION` is the only remaining legacy A2A type and is kept for upstream save
compatibility.

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
settings are purged on load in `game/settings/settings.py`. **In-game pass ☑ VERIFIED
2026-06-25** (G5): no generic Jammer F10 menu on fighters, no `ewrj`/`EWJamming`/`startEWjamm`/
`startIAdefjamming` in the generated mission.

**C-130 EW hard constraints (carried over from the standalone ME script):** do NOT toggle
SAM radar emissions (`enableEmission(false)` crashed DCS - suppression is ROE WEAPON_HOLD
only); the burn-through model intentionally RAISES jam probability with distance; spot
jamming has flat altitude-independent range; the missile-spoof curve is intentionally steep
at close range. Don't "fix" these.

**IADS-engine compatibility (MANTIS / Skynet):** every SAM-state write the jammer makes is
funnelled through two helpers — `suppressSAMRoe()` / `restoreSAMRoe()` — which touch **only**
the group ROE (`WEAPON_HOLD` to jam, `OPEN_FIRE` to un-jam) and never `ALARM_STATE`. The
script makes **no `mist.*` calls**, so the MIST → MOOSE consolidation doesn't affect it.
Under **MANTIS** (default engine) SAMs are driven purely via `ALARM_STATE` and MANTIS never
writes ROE, so the jam composes cleanly (a MANTIS-live radar still won't fire while held) and
the C-130J's `OPEN_FIRE` restore is the only thing that lifts the hold. Under **Skynet** the
engine re-asserts ROE itself, so the writes stay self-healing. The one regression to avoid is
adding any `ALARM_STATE`/emission write to the jammer — that would fight MANTIS' EMCON. See
the design note's "IADS engine interaction" section.

**`perf_red_alert_state` removed (2026-06-27):** because the IADS engine (MANTIS/Skynet) sets each
networked SAM's `ALARM_STATE` at runtime, the legacy global "SAM starts in red alert mode" toggle
only fought the engine — it wrote `OptAlarmState(RED/GREEN)` at spawn, which MANTIS immediately
overrode (the log even shows `Setting SAM Start States`), so flipping it changed nothing for
networked SAMs and confused players (it looked like the SAMs ignored "red alert"). The setting and
both its writers (`tgogenerator.set_alarm_state`, `flotgenerator`) are removed; **non-IADS** ground
groups (frontline armor, ships, autonomous SHORAD, any unmatched SAM) now fall to DCS `AUTO`. Old
saves drop the field via `_migrate_legacy_settings`. See
`docs/dev/design/414th-mantis-migration-notes.md` §11.

---

## 3. TARPS photo-reconnaissance + BDA fog-of-war

`FlightType.TARPS` adds player-flown F-14 recon. All F-14 variants carry the
`{F14-TARPS}` pod on station 6 (editor-verified). The auto-planner appends a single
TARPS sortie to Strike / DEAD packages when `auto_add_tarps_recon` is enabled and a
TARPS-capable squadron is available. The flight type is **airframe-agnostic** — it is
gated purely by the `TARPS` task in the airframe's `tasks:` table, not hard-coded to the
F-14 — so the Vietnam-era recon birds carry it too (see below).

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
- **Vietnam-era recon birds (VWV mod):** the dedicated tactical photo-recon ships —
  **RF-101B Voodoo** (`vwv_rf101b`, USAF land-based) and **RA-5C Vigilante** (`vwv_ra-5`,
  USN carrier) — carry `TARPS: 700` as their **primary** task (their old `Armed Recon` is
  kept as a lower-priority fallback so a squadron is never idle). They are unarmed camera
  ships with built-in cameras (no external pod), so their `Retribution TARPS` payload is a
  clean, weaponless fit — empty pylons, matched by name; the runtime recon task is set by
  `configure_tarps`, so the payload's `tasks` tag is only ME role-menu placement.
  Files: `resources/units/aircraft/vwv_{rf101b,ra-5}.yaml` +
  `resources/customized_payloads/vwv_{rf101b,ra-5}.lua`. The **Khe Sanh (Niagara)** campaign
  fields one squadron of each, tasked `primary: TARPS`
  (`resources/campaigns/khe_sanh_niagara.yaml`).
- Tests: `tests/test_tarps_recon.py` (Tomcat + Vietnam-recon TARPS-capability gates).

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
  filter. Defaults off; the panel persists other layer choices to the campaign save (and a
  localStorage cache; see §18) but deliberately excludes the fog overview, so it is never
  restored on load.
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
leaves room for the directory and its pagination); (3) the Friendly Packages list renders in
**two side-by-side columns** once it would overflow a single column, using the wasted right
half of the page (only > ~2× a column's capacity still paginates). The recon pages are
untouched (still golden-tested). This is a visual change CI can't exercise — see in-game-pass
row **H1**/**H2**. **H1 (overflow pagination) in-game pass ☑ VERIFIED 2026-06-25**; H2 still
pending.

**Kneeboard de-duplication pass.** With every optional page enabled the deck printed the same
data several times; a single-home-per-datum pass fixes it, each change conditional on the
*other* page existing (so a deck with options off is byte-identical to before):
- **Weather** (temp / QNH / QFE / winds / clouds / sunrise-sunset) is dropped from the always-on
  **Mission Info** (`BriefingPage`, `omit_weather`) when the recon **Departure** page is generated
  for the flight (`_should_emit_departure`), which already carries the field-weather grid.
- The flight-plan **Min-fuel** column is dropped from Mission Info (`FlightPlanBuilder`,
  `include_min_fuel`) when the **Fuel Ladder** page is enabled — the ladder carries Min + Plan +
  Margin, so the bingo-at-waypoint figure isn't printed twice.
- The **Friendly Packages** list moved out of the bottom of Mission Info to its own
  `FriendlyPackagesPage` (still two-column + paginating), so the list isn't split across Mission
  Info and a near-empty spill page; the package targets **map** stays as the spatial complement.
- The standalone **SEAD/Strike Target Info** page is suppressed when the recon **Detail** page
  covers the same target — that page already lists the emitters + role + HARM **ALIC** over a
  satellite view — **but only in EXACT intel** (the recon page shows exact coords while the task
  page intentionally fuzzes them in Approximate mode, §5, so the fold never leaks a fuzzed target).
The wiring lives in `KneeboardGenerator.generate_flight_kneeboard`. Visual change → in-game pass
**H8 ☑ VERIFIED 2026-06-26**.

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
`tests/missiongenerator/test_custom_kneeboards.py`; the Qt dialog itself: in-game pass ☑ VERIFIED 2026-06-26 (H4).

**Threat Intel Brief kneeboard (auto-generated enemy AD dossier).** A `ThreatIntelBriefPage`
(`game/missiongenerator/kneeboard.py`) auto-generates the enemy air-defense dossier for a player
flight as **one card per system** (sites aggregated), modelled on the per-system threat cards in
professional campaign Intelligence Briefings (design note `414th-campaign-doc-ideas-harvest.md`).
`build_threat_intel_cards()` groups enemy `SamGroundObject` / `EwrGroundObject` by system and each
card pairs the **live** campaign numbers — engagement range (MEZ), detection range, HARM **ALIC**
code (`AlicCodes`), live/dead site counts, and bullseye cues — with a **curated reference** from the
new `game/data/threat_reference.py` (`ThreatReference` = guidance type, engagement ceiling, and a
**"how to defeat"** tactics note), keyed by the same DCS unit ids as `AlicCodes`. A card's **name and
reference** come from `_system_identity()`, which ranks a site's units by `_CARD_IDENTITY_PRIORITY` so
the **weapon system** (track radar / TELAR / launcher — the HARM-targetable shooter) is what names and
describes the card, *not* the co-located search / acquisition / EW radar whose DCS display name reads
"… SR". This is deliberately the inverse of the recon-map ring's `_greatest_alive_threat` (which keys
on the lethal radar to size the engagement ring): a SEAD/DEAD brief should read "SA-5 S-200 Square Pair
TR", not "ST-68U Tin Shield SR" — and it fixes a real bug where an SA-5 site pulled the weaponless EWR
reference ("No weapons") from its acquisition radar despite a 138 nm MEZ. A bare radar site (nothing
lethal co-located) still honestly names itself. **Recon-fog aware** (§3): a site the player has not identified
(`known_for(player)` False) contributes only to a per-band "Unidentified MERAD" card — system,
ring, HARM code and defeat note withheld until a TARPS overflight reveals it. The unidentified cards
also **withhold the count**: how many unidentified (often mobile) sites are in theatre is intel we
wouldn't realistically have, so they drop the "N site(s)" headline and the intro's running total, and
their detected-contact bearings overflow to an ellipsis (`_unknown_cues_text`) rather than a "+N" total
that would leak the count. Cards sort live-most-lethal → unidentified and pack down the
page; overflow flows onto `(cont.)` continuation pages via the page's own card-packing
`paginate()`. Gated by `generate_threat_intel_kneeboard` (default OFF); covered by
`tests/missiongenerator/test_threat_intel_kneeboard.py`. In-game pass ☑ VERIFIED 2026-06-26 (H5). *(Per-system
photos were evaluated and deferred — DCS ships only `.dds` model textures, not portraits; reading
+ converting them at gen-time is fragile for marginal value on a 960px page.)*

**Mission code words + Comms & Brevity card.** A squadron-grown idea, modelled on the Red Flag
81-2 kneeboards: the whole side shares **one mission-wide code-word table** — a **push word per
task** (`STRIKE / SEAD / OCA / CAS / ANTISHIP / CAP / EW`) plus the event words `SUCCESS` /
`ABORT` (+ `STOP JAM` only when an EW/jamming flight is in the ATO) — so a single call ("Cobalt")
tells everyone SEAD is pushing (`game/ato/codewords.py`: `MissionCodeWords`, `PushCategory`,
`push_category_for`). It's owned by the **`Coalition`** (a `code_words` property generated once per
turn from a randomly chosen *themed* word pool, stored so it's stable while a planner briefs and
regenerates the mission, and pickled; `getattr` migrates old saves), so one table feeds everything
and a new turn draws a fresh themed set. The pools are deliberately **short single words** (metals,
colors, stone, animals — `Steel / Spectrum / Bedrock / Pack`) chosen to be quick and unambiguous over
the radio, with no two-word phrases and nothing that collides with a stock DCS callsign or brevity term. Because **planners brief off it before the `.miz`
exists**, it's surfaced pre-generation as a **persistent code-word panel** in the ATO package list
(`qt_ui/widgets/ato.py` `QPackagePanel.refresh_code_words`, an HTML table refreshed on
`layoutChanged`), a per-package **tooltip** (`AtoModel` `ToolTipRole`, that package's push word +
events), and a **`PUSH <word>` tag echoed on the JOIN waypoint** for the flight's task
(`WaypointBuilder._join_pretty_name` — JOIN is the package commit point and never a `TARGET_POINT`,
so it can't leak into DTC slot tags). In-cockpit, the **Comms & Brevity** kneeboard page
(`BrevityCard`) lists the full push table (the flight's own task row marked `(you)`) + the events +
a **task-filtered brevity crib** (`game/data/brevity_reference.py`, keyed by `FlightType` → A2A /
SEAD / STRIKE / CAS / EW / CONTROL / GENERAL). All of it is a *human* comms aid — nothing scripts
off the words (multiplayer missions, not the single-player campaigns the idea came from). One
toggle, `enable_package_code_words` (default OFF), gates the panel, tooltip, waypoint echo, and
kneeboard page together. Covered by `tests/ato/test_codewords.py` +
`tests/data/test_brevity_reference.py`; in-game / planner-UI pass ☑ VERIFIED 2026-06-26 (H6).

**Fuel ladder kneeboard card.** The flight-plan page already shows the *minimum* fuel required at
each waypoint (`FlightWaypoint.min_fuel`, the bingo-at-waypoint value the waypoint generator
computes by walking the plan backward over the per-leg burn model). The **Fuel Ladder** card
(`FuelLadderCard`) adds the missing half — the **planned fuel remaining** at each steerpoint
(`FlightWaypoint.fuel_planned`, a new forward pass `WaypointGenerator._estimate_planned_fuel_for`
that subtracts each leg's burn from the starting load `flight.fuel × KG_TO_LBS − taxi`, topping
back up at a tanker `REFUEL` waypoint). The card shows **one glanceable `Fuel` column** (planned
remaining) per RTB steerpoint. It deliberately does **not** print the old Plan/Min/Margin three
columns: the per-waypoint margin (Plan − Min) is **constant across the whole route by construction**
(start fuel − total burn − reserve, since the two figures are walked from opposite ends with the same
per-leg burn), and Min is just Plan minus that constant — so both repeated the same number on every
row. They collapse to a single **RTB margin** call-out above the ladder (`+N` spare, or a `−N` "tank or
divert" warning), computed as the worst-case `min(fuel_planned − min_fuel)` so a tanker leg's reset is
still caught. Post-landing reference points (e.g. the bullseye, which carry a forward-burn `fuel` but no
min-to-RTB) are filtered off the ladder. The burn model is approximate (it's the same estimate that
drives `min_fuel`), so the card is labelled as planning figures. Gated by `generate_fuel_ladder_kneeboard`
(default OFF); the model is covered by `tests/missiongenerator/test_fuel_ladder.py` and the card render by
`tests/missiongenerator/test_fuel_ladder_card.py`. In-game pass ☑ VERIFIED 2026-06-26 (H7). The last of the
three kneeboard ideas harvested from the campaign-doc study (`414th-campaign-doc-ideas-harvest.md`).

*Estimated-fuel fallback for dataless airframes.* The ladder originally only rendered for the ~22
airframes that ship a hand-measured `fuel:` block (`AircraftType.fuel_consumption`); everything else —
including the **C-130J "King"**, the helicopters, and the warbirds — showed *"No fuel estimate available
for this aircraft."* `AircraftType.estimated_fuel_consumption` (`game/dcs/aircrafttype.py`) now
synthesises a rough `FuelConsumption` from the airframe's internal capacity (`fuel_max`) scaled by an
assumed still-air cruise endurance, bucketed **helicopter / heavy-transport / combat** (heavy detected
by pydcs default task — Transport/Refueling/AWACS/Reconnaissance — or airframe length ≥ 28 m). The
combat bucket is calibrated against the measured references (F/A-18C ~22 ppm, F-16C ~12 ppm; the
estimate lands at ~21 for the Hornet) and the heavy bucket against the C-130J (~16 ppm); climb/combat
are multiples of cruise. It is **kneeboard-scoped on purpose** — the waypoint generator's two estimate
passes (`_estimate_min_fuel_for` / `_estimate_planned_fuel_for`) resolve `fuel_consumption or
estimated_fuel_consumption` and thread the chosen one through `FlightPlan.fuel_consumption_between_points`
(now taking an optional `consumption` override), but **`unit_type.fuel_consumption` is left `None`**, so
the flight planner's tanker tasking (`formationattack`) and the in-flight fuel sim (`inflight.py`) keep
using measured data only and gain no new blast radius. A real `fuel:` block always wins. Covered by
`tests/dcs/test_estimated_fuel_consumption.py`.

**Compact 3-4 page kneeboard deck + BLUF.** With every optional page enabled the deck ran to
~10 pages, and players usually only read the first. `compact_kneeboard` (default **ON**,
`game/settings/settings.py`) consolidates the deck into **at most four pages**, folding the optional
*sections* into fixed pages instead of appending their own:

- **P1 Brief Sheet** (`BriefSheetPage`, replacing the old `BriefingPage` "Game Plan" — see §31) is the
  consolidated, scannable one-pager modelled on the squadron's printed Appendix A brief sheet: header,
  mission, a **labelled route with steerpoint numbers** (`HOLD 1 → JOIN 2 → IP 3 → TGT 5 → EGRESS 6`),
  admin (bingo/joker/divert), threats (air + SAM), game plan, comms, code words, bullseye, fields
  (RWY/ATC/TCN), loadout, laser codes and Combat SAR — all **auto-filled** by
  `KneeboardGenerator._build_brief_sheet_data` and **colour-coded** (blue nav/comms, amber threats/fuel,
  green success, red abort). The detailed steerpoint table + weather drop off the kneeboard (the one-line
  route covers nav; DCS shows the full plan in-sim). The `BriefingPage` "Game Plan" + BLUF survive for the
  **full (non-compact) deck** only.
- **P2 Threats & Targets** (`CombatIntelPage`) draws the flight's target ALIC/coords (the per-task page's
  new `render_into`) over the enemy-AD **threat cards** (`ThreatIntelBriefPage.render_cards`, which packs
  as many as fit, now **colour-coded** to match the Brief Sheet — amber MEZ/Detect, blue HARM code +
  bullseye cues, emphasised system name). Skipped entirely when a flight has neither (e.g. a BARCAP).
- **P3 Comms & Coordination** (`CommsCoordPage`) composes the support sections (comm ladder + AWACS/
  tanker/JTAC, via `SupportPage._render(draw_title=False, fill=False, include_airfield_dir=False)`) with
  the **colour-coded code words** (`BrevityCard.render_code_words` — push words blue, SUCCESS green, ABORT
  red, STOP JAM amber, matching the Brief Sheet) + brevity crib. Lower-priority sections draw only if they
  fit (`_draw_section_if_fits`), never spilling to a 5th. (The friendly-package list used to ride here /
  on the flex page and got squeezed out when the page was full; it now lives on the **cover page** — see
  below — so P3 has room for the brevity crib.)
- **P4 Flex** is adaptive: the **recon target photo** (`_recon_detail_page`, the `DetailReconPage`/
  `AirbaseReconPage`/`FrontLineDetailPage` only — not the Departure/Overview pages) when
  `generate_target_recon_kneeboard` is on, otherwise a text `FlexReferencePage` with just the **Fuel
  Ladder** (`FuelLadderCard.render_into`).

The **friendly-package coordination list** rides on the always-present **cover page** in compact mode
(`_build_cover_page`): with recon imagery owning the flex slot it had nowhere else to go, and the cover's
lower half is otherwise empty. It's coalition-wide, so it's built **once** for the whole shared-airframe
deck from a representative flight. `FriendlyPackagesPage.render_section` self-guards — its table is
**self-limiting** (drops overflow rather than paginating), so a host fit-check can't tell when zero rows
survive; the section probes its own post-heading capacity and draws **nothing** (no stranded "Friendly
Packages" heading) when not even one row fits.

The theater/package-targets **map** image and the **Notes** page are not generated in compact mode.
Turning `compact_kneeboard` **off** restores the full multi-page deck (every optional page standalone,
recon imagery included) byte-for-byte — the old page classes are unchanged; the compact deck is a
separate assembly path (`KneeboardGenerator._compact_kneeboard_pages`). Covered by
`tests/missiongenerator/test_compact_kneeboard.py` (BLUF composition + the page-2 composite render);
in-game pass ☑ VERIFIED 2026-06-26 (H9).

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
- **Emitters only, not the whole site.** Both tables list only the **HARM-targetable emitters**
  — units with an **ALIC** code (radars and self-contained TELs) via `_emitter_units` — not the
  launchers, command trucks and AAA guns that pad `strike_targets`. The cue table additionally
  **dedupes by type** (one row per `Description | ALIC`), so it neither enumerates every launcher
  nor publishes exact unit counts. A site with no coded emitter (a pure AAA/launcher group) falls
  back to the full unit list so the page is never blank. The exact view keeps one row per emitter
  (distinct coords) and preserves the by-order STPT pairing via the unit's original index.
- **Recon-fog redaction (§3).** Both the cue and exact views only list the emitters once the
  site is **identified**: `SeadTaskPage._target_identified` gates on
  `TheaterGroundObject.known_for(viewer)`, and an un-discovered site is redacted to its
  **intel-tier band** + a bullseye cue + "Composition not yet identified — fly TARPS recon…",
  withholding the emitter breakdown and HARM codes until the site is scouted/struck/photographed
  (the same way the Threat Intel Brief redacts unknown sites). Without this the SEAD target list
  handed over the full composition of any un-recon'd site, defeating recon's purpose. *Known gap:*
  the experimental recon **Detail** page still draws the composition from satellite imagery
  regardless of `known_for` — a deeper question for that page (it IS a recon product), tracked
  separately; the standalone SEAD page is the one fixed here.

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

**Carrier/fleet exception (2026-06-28).** Front-anchoring a support orbit makes sense for a
land-based AWACS/tanker, but it flung *carrier* AEW&C (E-2C) up to the land FLOT — covering the
fighting instead of the boat it launched from. The auto-planner already tasks one AEW&C per
carrier CP (`theaterstate.aewc_targets = [carrier CPs] + farthest-friendly CP`), so the *target*
already encodes which orbit belongs to which fleet; only the placement ignored it. Now
`support_orbit_anchor` checks `is_carrier`/`is_fleet` on the target (other `MissionTarget`s lack
the attribute → treated as land) and, for a carrier/fleet target, **anchors on the carrier and
only nudges clear of the threat zone** — no FLOT re-center, no forward/AI-deep march. So the E-2C
covers its task force while a land EC-121/E-3 still front-anchors for forward coverage, with no
map-specific tuning (purely `is_carrier`-keyed → campaign-agnostic). `aewc.py`'s lateral
anti-stack spread is also scoped to AEW&C flights sharing the **same target** (anchor), so a land
AWACS no longer shoves a carrier E-2 off its boat now that the two sit on different anchors.
Verified by recomputing the `auto gen` Caucasus save (2× E-2C + 1× EC-121, the same
headless-recompute method that VERIFIED the C1/C2 parent fix): the carrier E-2Cs went from
**~218 NM** off their carriers to **~32 NM** (centered on the boat); the EC-121 stays forward on
the front. Tests: `tests/test_support_orbit.py` (`test_carrier_target_holds_on_the_fleet`,
`test_fleet_target_also_holds_on_the_fleet`). **Lua-free; geometry change, no new in-game-pass row
(folds under the C1/C2 support-orbit item).**

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

Tests: `tests/test_tanker_demand.py` (scoring + ATO extraction). **In-game pass ☑ VERIFIED 2026-06-25** (C7).
**Deferred follow-up:** retargeting compatible receiver `REFUEL` waypoints onto the moved tanker
(the plan's conditional "when the detour is reasonable" half) — the tanker already sits at the
centroid of those points, so this is a refinement, not essential. First half of the Codex tanker
PLAN; the red forward-BARCAP companion shipped separately (§6).

### Per-method theater-tanker fragging (2026-06-26)

**Symptom (headless adjudication of the flown GermanyCW save).** The HTN seeded exactly one
theater-refueling target (`TheaterState.from_game` → `closest_friendly_control_point()`), so at
most **one** theater tanker was ever auto-planned. For a *dedicated* tanker package,
`PackageBuilder._required_refuel_methods` sees no in-package receivers (the real receivers live in
other packages), so the single tanker was selected **unconstrained** → priority-first = the boom
KC-135. A coalition fielding both boom and probe receivers (e.g. BLUE: F-15/F-16 boom **and**
F-14/F-18/Mirage/Tornado probe, with both a KC-135 and a KC-135 MPRS in the wing) got gas for only
one method; the other method's receivers flew unsupported even though the matching tanker sat idle
in inventory. The C5 compatibility machinery was correct — what was missing was multi-method
fragging.

**Fix — seed one theater tanker per servable receiver method.**
`game/commander/theaterstate.py::seed_refueling_targets(coalition, location)` scans the air wing
once and returns one `RefuelingTarget(location, method)` per **distinct boom/probe method our
receivers need *and* we can crew a tanker for**. The method rides through the plumbing:
`RefuelingTarget` → `PlanRefueling.method` → `ProposedFlight.refuel_method` →
`PackageBuilder._required_refuel_methods` (an explicit `refuel_method` now takes precedence over the
in-package inference, which still serves same-package buddy tankers). Each target is planned in its
own pass of the `plan_missions` `while` loop (its `apply_effects` removes it) — identical to how
multiple AEW&C / Combat SAR front targets already plan — and `reposition_theater_tankers` then
parks each tanker on the strongest cluster of demand for *its own* method.
- **Never plans fewer tankers than before:** an untagged receiver fleet, a permissive
  (method-less) tanker, or a needed method with no matching tanker all fall back to a single
  unconstrained target (the legacy behavior).
- `TheaterState` is transient (rebuilt each turn, never pickled), so the `list[MissionTarget]` →
  `list[RefuelingTarget]` field change needs **no save migration**.

Tests: `tests/test_refueling_targets.py` (mixed fleet → one tanker per method; boom-only/untagged/
permissive/no-matching-tanker fallbacks). **In-game pass ☑ VERIFIED 2026-06-26 (C5)** — planner/data
+ live-save confirmed (matching, per-method fragging, demand placement); the in-sim residual
(receivers physically plugging in) was not eyeballed.

### CAS decoupled from the ground-stance decision (2026-06-28)

**Symptom (headless adjudication of a Caucasus Vietnam save).** A side **winning** the ground war
got **zero** CAS. CAS was only reachable as the *last* alternative inside
`CaptureBase → DestroyEnemyGroundUnits` — behind the `BreakthroughAttack` / `EliminationAttack` /
`AggressiveAttack` ground-stance tasks (`game/commander/tasks/primitive/*.py`). Those win whenever a
side has a front-line force advantage (Aggressive ≥ 0.8, Elimination ≥ 1.5, Breakthrough ≥ 2.0), and a
winning `BreakthroughAttack` *removes the front from `active_front_lines` outright* — so `CaptureBase`
never re-runs and CAS is never even evaluated for that front. On the worked save (blue 87 vs red
15/123/15) the two fronts blue dominated set an aggressive stance and got no CAS; only the one front
where blue was outnumbered reached `PlanCas`.

**Fix — a dedicated CAS task, decoupled from the stance machinery.** New compound task
`PlanFrontLineCas` (`game/commander/tasks/compound/frontlinecas.py`) yields one `[PlanCas(front)]` per
**still-vulnerable** front, wired into `PlanNextAction` (`nextaction.py`) **after** `CaptureBases`. The
ground-stance logic is untouched — an aggressive stance and a CAS package now coexist on the same
front. Ordering and idempotency fall out of the existing model:
- `PlanCas.apply_effects` removes the front from `vulnerable_front_lines`, so a contested front already
  CAS'd by the original capture path (its higher-priority slot) is skipped — **nothing is
  double-planned**.
- Running *after* `CaptureBases` means the more urgent **losing** fronts keep first claim on the
  limited CAS/escort jets; the dominant fronts CAS in the lower slot the capture path left empty.
- `vulnerable_front_lines` is rebuilt each turn from the active fronts and only consumed by `PlanCas`,
  so it is exactly "fronts not yet CAS'd" — no new state, **no save migration**.

**Verified** by recomputing the worked save against the real remaining inventory: all three fronts now
fulfil a CAS package (CAS + SEAD_SWEEP + a TARCAP escort), where before only the outnumbered front was
even *reached*. (Co-requisite: the carrier's air group must be visible to the planner — see the VWV
Enterprise `runway_is_operational` fix — or the contested-front TARCAP escort can't be sourced.)
Tests: `tests/commander/test_frontlinecas.py`. **Lua-free; in-game pass pending.**

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
- **Loadout integrity (jets flying clean / wrong ordnance).** A fleet-wide audit found two
  silent failure modes that dropped whole presets: (1) a stray empty pylon (`["CLSID"] = ""`
  / `<CLEAN>`) made `Loadout.valid_payload` reject the entire loadout (244 presets across 44
  airframes) — fixed by skipping empty stations; and (2) stale/dead CLSIDs (AJS-37 `{Rb15}`,
  the F/A-18E/F STA-02 JSOW `BRU55`→`BRU` rename) — repaired in `resources/customized_payloads`.
  Plus `ANTISHIP` gained the Strike fallback every other A2G task already had (so an anti-ship
  jet without an anti-ship preset carries iron bombs, not nothing). Guarded by
  `tests/data/test_weapons.py` (`test_valid_payload_ignores_empty_stations`,
  `test_antiship_falls_back_to_strike_loadout_names`,
  `test_customized_payload_clsids_resolve_or_are_known_stragglers` — fails on any *new* dead
  CLSID). A follow-up pass fixed the **F-14A Block 135-GR Early** (its `.lua` had the *Late*
  variant's `unitType` so its ground presets were never applied), authored a missing
  **F-14A Block 95-GR Export** payload file (iron-bomb presets — no LANTIRN), and switched the
  **Tornado IDS STRIKE** preset from TGP-less LGBs to iron Mk-82. Methodology + remaining
  residuals (mod-weapon stragglers, low-impact early-date noise):
  `docs/dev/design/414th-loadout-integrity-audit-notes.md`.
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
  `ambientFire`). Script injection is NOT a work order - it runs in the uniform
  late-init pass: `TicPlugin` (`game/plugins/tic.py`, registered in
  `manager.py`) declares a `late_init_preamble()` (pre-seeds `GLSCO.*` from
  `dcsRetribution.plugins.tic.*` and sets `AutoInitialize/AutoStart = false`)
  plus `late_init_files()` (`TIC_v1.1.lua`, `tic_414_init.lua`), gated on
  `mission_data.tic_groups`; `inject_plugins()`'s second pass DoScriptFiles them
  after all plugin config. (Was `_inject_tic_script()` — the "scramble pattern".)
  `tic_414_init.lua` then
  installs the 414th ambient-fire extension (wraps
  `GLSCO_COMBATANT:simulate()`: combatants with no LOS target have a 50%
  chance per firing cycle to area-fire a salvo at 30-150 m around the nearest
  enemy formation within 6 km - tracers over LOS blockers, no aimed
  lethality) and then owns `GLSCO:Initialize()` + `battle:Activate()`.
  CRITICAL: TIC's auto-init is disabled, so if tic_414_init.lua is removed or
  fails, the battle never starts.
- Failsafe hardening (`tic_414_init.lua`): the 414th ambient-fire `simulate()` override and the
  battle init are `pcall`-contained, so a runtime error in the speculative-fire path can't throw
  out of the engine cycle (one combatant) and an init error logs rather than aborting the rest of
  the DO-SCRIPT-FILE chain. Same defensive pattern as SCAR's `scar_check` watchdog (§15) and the
  Combat SAR LARS query (§21) — see `414th-campaign-doc-ideas-harvest.md`.
- Generator contract: `game/missiongenerator/flotgenerator.py`. When the
  plugin is enabled, TANK/IFV/APC/ATGM frontline groups are named
  `TIC:<namegen name>` (one TIC formation per group), late-activated, and get
  TIC orders as waypoint NAMES (`t+N hdg=H roe=simulate`) via
  `_plan_tic_action()` instead of DCS tasks/triggers. Squad infantry joins
  the carrier's formation as `TIC:<formation>#<infantry name>`. Artillery and
  the manpads-only branch stay vanilla. TIC group names are recorded in
  `mission_data.tic_groups` (the injection gate).
- Frontline composition + laydown (PR #823 adoption, 2026-06-26): the ground
  planner (`game/ground_forces/ai_ground_planner.py` + new
  `frontline_clustering.py`) now deploys a *proportional mixed selection* of the
  base armor pool (largest-remainder allocation) as even-spread combat clusters —
  an armor wedge (5-7, type alternates between adjacent clusters) with embedded
  SHORAD, an ATGM standoff pair, and leading recon; artillery/logi to the rear —
  replacing single-type random groups. `flotgenerator._generate_groups` places
  them via `frontline_offsets` (even slots; members share their wedge's offset)
  layered on top of the fork's existing perpendicular-step anti-stacking. This
  sits *upstream* of TIC's waypoint orders, so it just gives TIC a better starting
  laydown — TIC still drives movement. **#823's DCS-task cohesive-maneuver half is
  TIC-guarded**: in `plan_action_for_groups` the new `_plan_follower_action` /
  APC-into-wedge routing runs ONLY when `not self.tic_enabled`; with TIC on,
  TANK/IFV/APC/ATGM short-circuit to `_plan_tic_action` and SHORAD/RECON stay
  static (pre-#823 behaviour), so TIC keeps sole ownership of armor/ATGM movement.
  The fork keeps `base.total_frontline_units` (not upstream `total_armor`) as the
  deploy denominator. Also adds the **default front-line stance** setting
  (`settings.default_front_line_stance`, HQ Automation; seeded at new-game time
  and on player capture when auto-stance management is off). Tests:
  `tests/ground_forces/`, `tests/missiongenerator/test_flotgenerator_*`,
  `tests/theater/test_default_front_line_stance*`. Full merge record + the
  Bucket A/B/C split: `docs/dev/design/414th-pr823-frontline-merge-notes.md`.
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
    (default 12, players set it in the plugin UI) sizes the battle arc to fit
    a single sortie (~45-75 min); lowered from 25 (~1.5-2 h) on 2026-06-26
    after a playtest showed the line hadn't pressed into contact within a sortie.
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
  units from DCS AI sensors - AI CAS flights cannot detect the enemy
  frontline. Human CAS is unaffected. Turn StormTrooper off for visible
  real-AI ground combat.
- AUTO-JTAC REMOVED (2026-06-26, 414th playtest): the MQ-9 Reaper FAC drone
  that used to orbit the FLOT (spawned by `flotgenerator`, gated by
  `faction.has_jtac`) was removed for EVERY faction - it was unwanted drone +
  F10-menu clutter. The `MooseAutolase` plugin (JTAC Alpha/Bravo autolase) was
  deleted too. `faction.has_jtac`/`jtac_unit` remain as DORMANT no-op fields
  (kept so faction JSONs + `test_factions` don't churn). The frontline-group
  membership recording was accidentally nested inside that JTAC `if` block; it
  now always runs (latent bug fixed in passing).
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

## 11. Native DCS DTC cartridge export — RETIRED (2026-06-26)

**Removed as a half-baked feature.** The native DCS Data Transfer Cartridge export
(`generate_dtc` setting + `game/missiongenerator/dtc/` package + the captured ME
templates under `resources/dtc/`) never worked end-to-end: ED's mission-start pre-load
did not fire on the shipping DCS build, so the player had to open the DTC manager and
manually load the cartridge once per sortie, and the mirrored Saved Games library write
did not distribute over multiplayer. With ED building a native DTC of their own, the
fork's reverse-engineered export was dead weight and has been deleted. Do **not** restore
it; revisit only if ED's native cartridge ships and a thin, reliable export is worth
rebuilding from scratch.

(The F-15E CDU data-cartridge slot labels on the strike-task kneeboard — the
`DTC M1.1` references in `kneeboard.py` — are an unrelated upstream feature and remain.)

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

## 13. Flight Control ATC — RETIRED (2026-06-26)

**Removed as a half-baked feature.** The players-only MOOSE **FLIGHTCONTROL** ATC plugin
(`resources/plugins/flightcontrol/`, the `_inject_flightcontrol_script()` /
`_flightcontrol_airbase_entries()` injection in `luagenerator.py`, and the
`flightcontrol` registry entry) tower-sequenced human players at friendly land airbases.
It added taxi/takeoff/landing comms but needed constant care to keep AI flow pass-through
(generous taxi/landing limits + orphan-parking reconciliation to silence MOOSE
parking-spot spam), and never earned its keep. It has been deleted.

Save migration: `Settings.__setstate__` drops the `flightcontrol` plugin option keys on
load (alongside the other retired plugins) and no longer force-enables it; the one-time
recon-plugins-default migration now flips only TARS. Do **not** restore the plugin.

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

## 15. SCAR — RESCAP "Sandy" rescue escort (rescue rework)

> **Rework complete (2026-06-27).** SCAR was repurposed from an armor-hunt task into the **RESCAP
> "Sandy"** rescue escort of the **Combat SAR package** (King + Jolly Green + Sandy). The old
> moving-HVT armor-hunt scenario *and* its auto-planner were **deleted** (detailed below); the
> SOF/CSAR recovery plumbing was repurposed for the POW path. Design source of truth:
> `docs/dev/design/414th-scar-rescue-rework-notes.md`.

**The shipped feature.** `FlightType.SCAR` is the **Sandy** rescue-escort role in the Combat SAR
package — it no longer hunts armor. The retired armor-hunt scenario (the moving-HVT "find the real
one among look-alike decoys" chase) and its opt-in auto-planner were **removed on 2026-06-27**:
`game/missiongenerator/scarluadata.py`, the `scar` Lua plugin (`resources/plugins/scar/`, dropped
from `plugins.json`), `game/plugins/scar.py` + its `manager.py` registration, `PlanScarHunts` /
`PlanScar`, the `scar_autoplan*` settings, the `mission_data.scar_taskings` plumbing, and the
`test_scar_bridge.py` / `test_scar_autoplan.py` suites are all gone. The only symbol that outlived
the armor hunt is the SOF-team unit-name pair (`SCAR_SOF_UNIT_BLUE` / `SCAR_SOF_UNIT_RED`),
relocated to the live rescue module `game/scar_rescue.py` (its only consumers are now the
rescue/POW objectives + scoring).

**Planner side (Python, CI-tested).** `FlightType.SCAR` (`game/ato/flighttype.py`) stays an
air-to-ground primary, eligible on the **A-10C / AH-64D** rescue-escort airframes. It is
**player-selectable**, and the AI fields it through the Combat SAR standing alert: `PlanCombatSar`
(`game/commander/tasks/primitive/combatsar.py`) proposes the package = **1 King (C-130) + 1 Jolly
Green (rescue helo) + 1 Sandy (SCAR)** when `auto_combat_sar` is on (`combat_sar_targets` is empty
otherwise, so the default-off path is a pure no-op). A free Sandy degrades gracefully — if no
A-10/Apache is available the fulfiller simply skips it. **BAI is untouched**; deleting the SCAR
auto-planner that used to *steal* enemy battle positions hands them all back to BAI.

**The enemy capture race (runtime — `combatsar` plugin).** On a downed-pilot spawn the `combatsar`
plugin rolls a chance to spawn an enemy **snatch party** that walks at the survivor (red smoke + a
MAYDAY cue); the King smokes/marks/calls it so Sandy engages. The party is now **several small,
dispersed teams** (default 3) ringed around the survivor on different bearings and converging
independently — the same total infantry split into fire teams rather than one long marching column,
which reads as a single target. The party spawns on the **enemy coalition**: Python emits the
opposing side's faction country (`enemyCountry`, always registered on the enemy coalition in the
`.miz`) and the plugin spawns the teams under it; the old hardcoded `CJTF_RED`/`CJTF_BLUE` constant
is only a fallback (those countries aren't registered when the factions use real/CH nations — e.g.
Vietnam — which previously put the snatch party on the wrong side). Kill the party to save the
pilot; let any team dwell on the survivor un-rescued and the pilot is **CAPTURED** — appended to the
`combat_sar_captures` state global (location + airframe unit name), parsed back by
`Debriefing.parse_combat_sar_captures`. Seven plugin tunables
(`captureEnabled` / `Chance` / `SpawnDistance` / `Range` / `Dwell` / `PartySize` / `Teams`).

**Capture → POW → recovery (Python).** `record_pow_captures` (`game/sim/missionresultsprocessor.py`)
turns each capture into a `PendingPowRecovery` (`game/pow_recovery.py`) on the blue coalition
(persisted, save-migrated, 4-turn clock); `commit_air_losses` spares a captured pilot the KIA (a
POW is not killed). Each turn `game/pow_objectives.py` rebuilds the POW as a
`CapturedPilotGroundObject` (`game/theater/theatergroundobject.py`) at the nearest **enemy
airfield**, offering **CSAR** recovery to the owning side. Recovery resolves two ways: a
**surviving CSAR raid** fragged at the holding field (`commit_pow_recoveries`, matched by airframe
unit name) frees the aviator; and `surviving_pows` (`game/pow_recovery.py`, run from
`Coalition.end_turn`) frees a POW whose **holding field is recaptured**, decrements the clock
otherwise, and **kills** an abandoned POW at zero (permanent loss). v1 fidelity gap: a held pilot
isn't pulled from the active roster.

**The rescue substrate (repurposed, live).** The SOF-recovery plumbing that once served the
armor-hunt commander-capture is now the POW/rescue substrate: `PendingSofRescue` +
`Coalition.pending_csars` + the turn-cap/overrun loss clock (`game/scar_rescue.py`), and
`DownedSofGroundObject` rebuilt each turn into a CP-anchored map objective (`game/scar_objectives.py`
`sync_downed_sof_objectives`), gated by `scar_command_post_intel`. `commit_sof_recoveries` refunds
a delivered SOF team. The **Sandy kneeboard** is `ScarTaskPage` (`game/missiongenerator/kneeboard.py`)
— role guidance for holding with the King/Jolly, suppressing the threats around the survivor, and
walking the rescue helo in.

**Settings / state.** `scar_command_post_intel` (Campaign Doctrine; gates the on-map POW/SOF
objectives) and `auto_combat_sar` (the AI standing alert). State globals: `combat_sar_captures`
(captures) and `combat_sar_rescues` (pilot-spared credit). **Tests:**
`tests/test_scar_command_post_fog.py` (intel-fog of the POW/command objectives + the SOF debit),
plus the Combat SAR / POW coverage in `tests/test_missionresultsprocessor.py`. The capture race +
King cueing + POW recovery **need an in-game pass** (checklist G8–G14).

**Sandy AI dynamic retasking (runtime — `combatsar` plugin, added 2026-07-01).** `ScarFlightPlan`/
`Builder` (`game/ato/flightplans/scar.py`) still plans Sandy's racetrack once at generation, centred
on the King's hold (or the FLOT centre with no King) — that part is unchanged. What was missing: the
box never moved to follow wherever a pilot actually ejected later in the mission (a 2026-06-30
in-game report — "Sandy's did nothing but fly their orbit path" — and the code's own comment flagging
this as "a combatsar runtime follow-up for the AI"). The runtime now closes that gap for **AI-crewed**
Sandys (player Sandys are untouched — voice/SRS coordination stays the intended path): `luagenerator.py`
buckets `FlightType.SCAR` flights per coalition into `dcsRetribution.CombatSAR(.red).sandys` (group
names only, alongside the existing `kings`/`rescueHelos`); `combatsar-config.lua` builds a
`sandyByName` map and, on every tick a survivor is `"down"`, `dispatchSandy` finds the nearest alive,
idle, **non-player** Sandy within `sandyMaxRangeM` (default 55.56 km / 30 NM) and pushes a combo DCS
task — `TaskOrbitCircleAtVec2` (hold near the survivor, at the Sandy's own current altitude/speed) plus
an `EnRouteTaskEngageTargetsInZone` sub-task (actively hunts `"Ground Units"` within
`sandyEngageRadiusM`, default 5.56 km / 3 NM, around the survivor) — replacing its DCS-assigned
racetrack task. `configure_scar`'s weapons-free ROE (unchanged) does the actual engaging once
retasked. Commits at most one Sandy per survivor (`busySandy`), retries every `POLL` (5s) until one
frees up, and releases it (`ClearTasks()`, which resumes the group's own planned route) once the
survivor is rescued/captured/dead. Two new plugin options: `sandyMaxRangeM`, `sandyEngageRadiusM`.
Python bucketing/emission is unit-tested
(`tests/missiongenerator/test_combat_sar_sandy_luadata.py`); the Lua runtime is **unflown** (no local
Lua interpreter — read-verified only) and needs a cockpit pass (checklist G23).

### SOF insert generation fixes (2026-06-22)

Two fixes so the SOF C-130 airdrop actually generates as a flyable ground sortie:

- **Forced air spawn → runway fallback** (`game/missiongenerator/aircraft/flightgroupspawner.py`,
  `generate_flight_at_departure`). On `NoParkingSlotError` Retribution force-converted a planned
  ground start to `IN_FLIGHT`; the SOF C-130 (a large aircraft that often finds no large parking
  slot) air-spawned despite a ground start being selected. The "try a runway start before the air
  start" retry was previously gated to `FlightType.JAMMING` only — now it applies to **any
  non-helo flight** with a cold/warm start at an airfield (runway starts need no parking slot).
  Helos (helipads/ground spawns) are unaffected.
- **EW plugin de-conflict** (`game/missiongenerator/luagenerator.py`,
  `_ew_excluded_c130j_groups` + the `c130j` plugin's `isEligible`). The C-130J Mission Systems
  (EW/ISR) plugin attaches to **every** `C-130J-30` by airframe alone
  (`eligibleTypeNames = {["C-130J-30"]=true}` in `c130j_mission_systems.lua`), so it would bolt
  the EW menu/behavior onto a SOF insert or Combat SAR King flown by the same airframe. The
  generator emits a **per-group deny-list** — `dcsRetribution.EwExcludedGroups`, the group names of
  C-130J-30 flights in a non-EW role (`FlightType.SOF`/`COMBAT_SAR`, both coalitions) — and the
  plugin's `isEligible` skips exactly those groups (by `getGroup():getName()`). This **replaced the
  old mission-wide plugin skip** (`_non_ew_c130j_present`), which also stripped EW from a co-present
  **JAMMING** C-130J-30; an EW jet and a SOF/King C-130J can now fly the same mission. The old
  whole-plugin skip was verified in-game 2026-06-23 ("the EW is gone" on the SOF C-130); the
  per-group version needs a fresh pass (checklist **J3**), as does the runway-fallback half.
  Upstream-PR candidate (fork-specific to the `c130j` plugin).

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
- **Consolidated the ground-start truck toggles** (2026-06-28). The "Ground start" section
  had four near-identical booleans — supply trucks and ground-power trucks each split across
  *airbase* and *roadbase* variants. Folded each pair into one airbase+roadbase toggle
  (`ground_start_trucks`, `ground_start_ground_power_trucks`); the two `*_roadbase` fields are
  removed from `Settings`, `_LAYOUT_SPEC`, and the runtime consumers (`tgogenerator.py`,
  `flightgroupspawner.py`). `_migrate_legacy_settings` OR-merges an old save's per-base-type
  values (enabled at *either* base type stays enabled) and drops the retired keys. Covered by
  `tests/settings/test_settings_qol_migration.py`.

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
  stays short; group + layer + base-map choices persist to the **campaign save** (with a
  `localStorage` cache, `fjg.mapLayers.v1` → bumped to `…v2`), except the fog overview (see §3).
  The panel `GET`s `/game/map-layers` on mount (the save wins over the localStorage seed) and
  `PUT`s the same blob back, debounced, on change; it is stored opaquely on
  `Game.client_map_layers` (`game/game.py`, `__setstate__` defaults it for old saves) and
  carried by the per-turn autosave, so choices survive turns and reopening the app (QtWebEngine
  drops `localStorage` on reload). Server side: `game/server/game/routes.py` (`MapLayersJs`).
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

- **`FlightType.COMBAT_SAR`** — player-selectable for the **CH-47 / UH-60A/L / UH-1H / CH-53E /
  Mi-8** rescue helos and the C-130 (King), so a faction without a Chinook still fields CSAR (the
  engine is airframe-agnostic; the task is granted per `resources/units/aircraft/*.yaml`). The
  **AI standing alert air-starts on station** (`packagebuilder` sets `StartType.IN_FLIGHT` for the
  non-client Combat SAR alert) so it is overhead *before* the first losses instead of spooling up at
  a rear field and transiting in — a slow helo from depth never reaches a deep ejection in time. A
  player-flown Combat SAR keeps the normal client start. It
  flies a **dedicated forward-hold plan** (`game/ato/flightplans/combatsar.py`,
  `CombatSarFlightPlan`): front-anchored like AEW&C, but with a **short threat buffer**
  (`COMBAT_SAR_THREAT_BUFFER`, 15 NM — just clear of FLOT SHORAD/MANPAD reach) and a
  **helo-sized racetrack** (`COMBAT_SAR_RACETRACK_HALF_DISTANCE`, 5 NM), so the rescue helo
  holds *near the front* where it can actually reach an ejection — **not** at the 80 NM AWACS
  standoff. `CombatSarFlightPlan` subclasses `AewcFlightPlan` (and its `Builder` subclasses the
  AEW&C `Builder`) purely to keep the existing support-flight integration that keys off
  `isinstance(.., AewcFlightPlan)` (AWACS-info registration) — only the
  geometry differs. Helos clamp to a helo-appropriate AGL via the shared `get_altitude` path.
  (Earlier builds reused the AEW&C builder outright, which parked the CH-47 at AWACS depth — a
  G9 in-game finding, fixed 2026-06-25.)
- **AI standing alert** — `Settings.auto_combat_sar` (HQ automation, default OFF) auto-plans
  one COMBAT_SAR orbit per turn for blue via `PlanCombatSar` / `PlanCombatSarSupport`
  (mirrors AEWC/refuel support). With it on, the generator emits `enableForAI=true` plus a
  `heloTemplate` (the first rescue flight's group, used as the clone-fallback template) and `farp`
  (that flight's departure field). **The AI rescue runs in the plugin's own survivor ledger, not
  MOOSE `AICSAR`/`CSAR`** (the 2026-06-26 playtest confirmed MOOSE CSAR's `enableForAI` only
  *tracks* AI ejections and never flies a helo — "Jolly Green flew a racetrack and did nothing").
  `combatsar-config.lua` registers every AI/player ejection through an **ejection bridge**
  (`world.addEventHandler` on `S_EVENT_EJECTION`, pcall-guarded, one survivor per airframe) — so a
  shoot-down dispatches immediately rather than waiting on the unreliable
  `S_EVENT_LANDING_AFTER_EJECTION` (the G9 fix). After `AI_DISPATCH_DELAY` grace (lets a player or
  on-station crew react), `dispatchAIRescue` flies a helo via MOOSE `OPSTRANSPORT` to board the
  ledger's survivor as cargo and deliver it to the FARP, **crediting the real unit** on unload
  (`OnAfterUnloaded` → `combat_sar_rescues`; no anonymous clone — identity lives in the ledger
  entry, so AI rescues score the spare-pilot credit too).
- **Commandeer-first dispatch (2026-06-29, G21 fix).** `dispatchAIRescue` used to **always** clone a
  fresh helo (`SPAWN:NewWithAlias("CombatSAR Rescue N", …)`) from the FARP, so every AI ejection
  piled a new helo on top of the rescue flight already orbiting the FLOT (Tacview-confirmed: 8+
  `CombatSAR Rescue N` clones spawned co-located with the idle `Front line … Combat SAR` helos).
  It now **commandeers the nearest alive, idle, AI-crewed rescue helo** already in the mission
  (`commandeerRescueHelo` over `cfg.rescueHelos`, wrapped in a `FLIGHTGROUP` + `AddOpsTransport`),
  marks it busy, and frees it again on delivery so it can serve the next ejection; it only falls
  back to cloning from `heloTemplate` when every planned rescue helo is dead or already committed.
  Player-crewed helos are skipped (`groupHasPlayer`), so it never competes with a human's CSAR. The
  live-group `FLIGHTGROUP` takeover of an orbiting AI flight is ◐ **PARTIAL** as of a 2026-06-30 flown
  session (checklist G21): the clone-fallback path is confirmed correct, but the row's own anticipated
  fail signature (`combatsar: AI dispatch error` — a Moose `_RegisterGroupTemplate` "table index is
  nil" on a nil `unitId`) also reproduced 9× in that session's `dcs.log`, `pcall`-guarded so it didn't
  block the 3 rescues that completed. **The earlier G9 eject-dispatch re-fly PASSED 2026-06-28 (audience pass, user "good").**
- **"Table index is nil" dispatch error root-caused + fixed (2026-07-01, G21).** The rescue helos are
  player-flyable (Client skill), and MOOSE's `DATABASE:_RegisterGroupTemplate` does
  `Templates.ClientsByID[unit.unitId] = unit` for every Client/Player-skill unit — which throws when a
  client slot's template carries a **nil `unitId`** (a `.miz`-generation quirk). The crash is on the
  **clone** path (`SPAWN(heloTemplate):Spawn()` re-registers the template); the commandeer path uses
  `_RegisterDynamicGroup`, which never touches that line. Three fixes: (1) an init sweep
  (`sanitizeClientTemplates`) backfills a synthetic collision-safe `unitId` on any nil-`unitId` client
  template so registration never indexes a nil — the root cause; (2) `dispatchAIRescue` now returns
  success and the caller retries a *failed* dispatch up to 3× with backoff instead of latching
  `e.dispatched` before the attempt (which abandoned the survivor on the first error); (3) the
  `busyHelos` mark moved to the success path so a mid-dispatch error can't strand a commandeered helo
  as permanently busy. Needs a re-fly to confirm (checklist G21).
  **v1 limitation (still open):** a player ejecting from a fixed-wing with no human helo up can be
  double-handled (cosmetic double-spawn).
- **King beacon = TACAN only.** Each King lights an **air-tracking TACAN** (follows the
  moving orbit; every rescue helo we use has a receiver) — the single homing solution.
  An ADF radio beacon was **considered and dropped** (MOOSE's `RadioBeacon` is fixed-point
  and the King is a mover, so it would need a position-refresh loop for no gain over the
  TACAN). The King also carries an F10 **Combat SAR → LARS** button that reads MOOSE CSAR's
  live downed-pilot table and reports each active survivor (position + bearing/range from
  the King) for the crew to relay.
  - **AI-only beacon activation (crash guard).** The scripted `ActivateTACAN` is pushed
    **only** to a live, AI-controlled King (`unit:IsAlive() and unit:GetPlayerName() == nil`
    in `combatsar-config.lua` `activateKing()`). A **player-occupied** King has no AI
    controller, so the `ActivateBeacon` command has *"no executor"* (logged as an
    `AI::Controller exception`) and — because an air-tracking beacon is re-evaluated every
    sim tick against the host unit — was the suspected trigger for an in-game `ACCESS_VIOLATION`
    CTD in DCS's discrete-command executor (`wSimCalendar::DoActionsUntil`). When a human flies
    the King, the crew **sets TACAN in-cockpit**; the LARS F10 menu still attaches either way.
    The Lua attaches King activation on mission-start live groups, group birth, and player-enter
    so client-slot Kings get the F10 menu after the pilot joins.
    (2026-06-25 in-game pass: C-130 King flown by the player → "No executor for command
    ActivateBeacon" + CTD; guard added.)
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
  Because the EW (`c130j`) plugin claims every C-130J-30 by airframe, the generator emits a
  per-group deny-list (`_ew_excluded_c130j_groups` → `dcsRetribution.EwExcludedGroups`) of the
  SOF-insert / Combat SAR King C-130J-30 group names so the King (and SOF) fly clean while a
  co-present JAMMING C-130J keeps its EW systems (see §15 EW de-conflict).

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
| Airframes | rescuer **CH-47Fbl1** (+ AI `CH-47D` fallback) plus utility-helo rescuers **UH-60A/L, UH-1H, CH-53E, Mi-8** (so non-Chinook factions still field CSAR), and King **C-130J-30** (the only C-130) carry `Combat SAR` in `resources/units/aircraft/*.yaml`; door-gun loadout in `resources/customized_payloads/CH-47Fbl1.lua` (`Retribution Combat SAR`). EW de-conflict: `luagenerator._ew_excluded_c130j_groups` (per-group deny-list) |
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

---

## §23 — Per-squadron DCS country (nation-specific voiceovers)

Implements the upstream request [dcs-retribution/dcs-retribution#627](https://github.com/dcs-retribution/dcs-retribution/issues/627):
let each squadron's units spawn under their own DCS *country* so a coalition (CJTF) side flying
liveries from several nations gets that nation's voiceovers/comms, instead of every unit on a
side sharing one faction country's radio voice.

### The change (the "last mile")

The data already existed — squadrons carry a `country` (`game/squadrons/squadrondef.py`, set by
preset YAML `country:` and inherited from the faction by auto-generated squadrons in
`game/campaignloader/squadrondefgenerator.py`). The gap was purely in mission generation, which
collapsed every group on a side onto the single faction country. This feature routes the squadron
country through the spawn path.

- **`game/missiongenerator/countryassigner.py` — `CountryAssigner`** is the resolver. At
  construction it walks `game.blue.air_wing.iter_squadrons()` / `game.red...`, and builds, per
  side, the set of canonical `dcs.country.Country` instances to register on the coalition plus a
  `for_squadron(squadron)` lookup. `primary_blue`/`primary_red` are the faction countries (the
  fallback). Exposes `blue_countries`, `red_countries`, `belligerent_ids`.
- **Conflict rule (the one real constraint):** a DCS country may belong to only **one** coalition
  in a `.miz`. **Blue claims its squadron countries first**; any red squadron whose country is
  already claimed by blue falls back to `primary_red`. (The common case — both sides on distinct
  CJTF primaries with non-overlapping real-nation squadrons — never hits this.)
- **Canonical-instance discipline:** pydcs attaches spawned groups to the `Country` instance via
  `country.add_aircraft_group` and only serializes countries reachable from the coalition, so the
  **same instance** must be both registered on the coalition (`add_country`) and passed at spawn.
  `CountryAssigner` interns one instance per id (`_instances`) and hands that same object to both
  paths. Passing a duplicate-id instance would silently drop its groups on save.

### Wiring

- `game/missiongenerator/missiongenerator.py` builds `self.country_assigner` in `__init__`
  (`p_country`/`e_country` are now `primary_blue`/`primary_red`), registers **all** per-side
  countries in `setup_mission_coalitions()`, and uses `belligerent_ids` to exclude belligerents
  from the neutrals pool.
- `game/missiongenerator/aircraft/aircraftgenerator.py` takes the assigner in its constructor and
  resolves the country **per flight/squadron** in `generate_flights`, `spawn_unused_aircraft`, and
  `spawn_intercept_templates` (these methods no longer take coalition-level country params).
  `FlightGroupSpawner` is unchanged — it already spawns under whatever country it's handed, and
  callsign generation (`namegen.next_aircraft_name`) flows from the same value.

### No-op for single-nation factions

For a non-CJTF faction the squadron loader (`game/squadrons/squadrondefloader.py`) already
restricts squadrons to the faction country, so every resolved country equals the faction country
and the generated mission is unchanged. The behavior only diverges for mixed-nation/CJTF sides —
exactly the intent.

### Files & tests

| Area | Path |
|---|---|
| Resolver | `game/missiongenerator/countryassigner.py` |
| Coalition registration | `game/missiongenerator/missiongenerator.py` (`setup_mission_coalitions`, `generate_air_units`) |
| Per-squadron spawn | `game/missiongenerator/aircraft/aircraftgenerator.py` |
| Tests | `tests/missiongenerator/test_country_assigner.py` (no-op, mixed-nation, cross-side collision, belligerent ids, instance identity) |

### Gotchas / deferred

- **Ground units stay on the faction country.** TGOs, statics, convoys, and the player helo group
  still spawn under `p_country`/`e_country` (`tgogenerator.py`, etc.) — harmless, since ground
  units have no nation voice comms. Only air units carry the per-squadron nation today.
- **In-game pass ☑ VERIFIED 2026-06-26 (I1).** Confirmed in flight — a mixed-nation CJTF side plays
  the per-nation voiceovers; the headless `CountryAssigner` adjudication held up live.

### Nation-aware pilot names (completes §23)

The country half landed first; the **roster** half completes it. Pilots were named by a single
per-coalition `Faker(self.faction.locales)` (`game/coalition.py`), so once §23 let a Greek
squadron fly under the Greek flag with Greek voiceovers, its *pilots* were still "John Smith" —
the faction locale, not the squadron's nation.

`game/squadrons/pilotnames.py` adds a curated **DCS country → Faker locale** table
(`COUNTRY_FAKER_LOCALES`, keyed by the exact pydcs `Country.name`) and `faker_for_country()`;
`Squadron.faker` now returns the squadron's own-country Faker instead of the coalition's. So a
Greek squadron rosters with Greek names, an Iranian one with Persian names, a Russian one with
surname-first patronymics, etc. — the same nation the §23 country/voiceover already targets.

Design notes:
- **Opt-in / permissive, never breaks generation.** Any unmapped country — including the
  multinational/irregular "countries" (the CJTFs, Insurgents, UN Peacekeepers) — falls back to
  the coalition's faction-locale Faker, so a roster is always produced. This can only *improve* a
  name. Single-nation factions are unchanged (their squadrons already equal the faction country).
- **Gender-aware guard.** The pilot generator needs `name_male()`/`name_female()` (for
  `female_pilot_percentage`), and a few shipped locales (e.g. `es_AR`) have no gendered name
  provider. `_faker_for_locale` validates this once (cached) and returns `None` → fallback if a
  locale can't do it, so a bad map entry degrades gracefully instead of crashing recruitment. The
  parametrised test asserts **every** mapped locale is usable, so a typo'd/non-gendered locale
  fails CI rather than shipping.
- **Pickle-safe.** The per-locale Fakers live in a module-level `lru_cache`, not on the pickled
  `Squadron`/`Coalition`, so saves are unaffected (the coalition already drops its Faker in
  `__getstate__`). No save migration needed.
- **Non-Latin names are intended** and consistent with the pre-existing Russian-locale behaviour
  (Qt + DCS are UTF-8). Faker's `name_male()` can occasionally include a title ("Herr …", "Dr.
  …") — that's a pre-existing quirk of the same call the old code used, not new.

| Area | Path |
|---|---|
| Country → locale table + resolver | `game/squadrons/pilotnames.py` |
| Wiring | `game/squadrons/squadron.py` (`Squadron.faker`) |
| Tests | `tests/squadrons/test_pilotnames.py` (mapped→own locale, unmapped/None→fallback, locale-cache, every mapped locale is gender-aware, squadron recruits named pilots) |

In-game pass row I5 (UI/roster eyeball only — the logic is fully unit-tested).

## §24 — Date-gated aircraft properties (helmet-mounted cueing)

Extends campaign date-gating from *weapons* to the per-airframe **properties** shown in the
payload editor (the "mission options" block: helmet device, datalink, etc.). Weapons already
disappear from the loadout when they postdate the campaign (`restrict_weapons_by_date` +
`Weapon.available_on`); the same toggle now also restricts era-defining property options. The
first curated gate is **JHMCS** (Joint Helmet-Mounted Cueing System, fielded ~2003): a pre-2003
campaign no longer offers — or silently ships — JHMCS.

This is the "curated start" of a deliberately small layer. Properties carry **no** introduction
date in pydcs (unlike weapons, which carry `WeaponGroup.introduction_year`), so the gate is a hand-
authored table, not bulk data. Only genuinely period-bound cueing systems are gated; everything
else (rate-of-fire, laser codes, fuel, NVG, the baseline visor) is left untouched.

### The data layer

`game/dcs/aircraftproperties.py` holds the table and four pure helpers
(`property_value_available_on`, `available_value_ids`, `period_correct_value`, and the private
`_introduction_year`). Two design choices matter:

- **Keyed by the value *label*, not the numeric id.** Across airframes the same id means different
  things — `HelmetMountedDevice` id `1` is `"JHMCS"` on the F/A-18 and F-16 but `"SURA Visor"` (a
  1980s Soviet helmet sight) on the Su-30/Su-35. An id-based gate would wrongly restrict the Soviet
  sight; a label key (`{"JHMCS": 2003}`) only catches the real JHMCS.
- **Scoped to the helmet-device identifiers** (`HelmetMountedDevice`, `HelmetMountedDeviceWSO`) so
  the gate can never touch an unrelated property that happens to share a gated label.

The period-correct fallback is the first still-available value, which on every affected airframe is
the baseline "no modern cueing" option (`Not installed` / `Visor Only`, id `0`).

### Two enforcement points (mirrors weapons)

- **UI (`qt_ui/.../payload/propertycombobox.py`).** When `restrict_weapons_by_date` is on, the
  dropdown lists only `available_value_ids(...)`, and a gated stored/default selection displays its
  `period_correct_value(...)` instead. Like the weapon editor, **storage is not mutated** — the
  player's choice is preserved and only the display + generated mission are clamped. `game` is
  threaded down via `PropertyEditor` (built with `game` in `QFlightPayloadTab`).
- **Generation (authoritative — `flightgroupconfigurator.py::degrade_props_for_date`).** Called from
  `setup_props` when the setting is on. Crucially it resolves each helmet prop against the unit
  type's **default**, because an unset helmet device still defaults to JHMCS in the `.miz` — so only
  inspecting `member.properties` would miss the (common) defaulted case. Force-sets the fallback
  when the effective value is too modern.

### Files & tests

| Area | Path |
|---|---|
| Data + helpers | `game/dcs/aircraftproperties.py` |
| Generation clamp | `game/missiongenerator/aircraft/flightgroupconfigurator.py` (`degrade_props_for_date`) |
| UI filter | `qt_ui/windows/mission/flight/payload/propertycombobox.py`, `propertyeditor.py`, `QFlightPayloadTab.py` |
| Tests | `tests/dcs/test_aircraftproperties.py` (JHMCS gated pre-2003, baseline/NVG always available, clamp-to-baseline, Soviet SURA Visor untouched, non-helmet property untouched) |

### Gotchas / deferred

- **Only JHMCS so far.** Add datalink/IFF-mode or other helmet systems (e.g. Scorpion) by
  extending `HELMET_CUEING_INTRODUCTION_YEARS` / `HELMET_DEVICE_PROPERTY_IDS` — the plumbing is
  generic. No new setting: it rides the existing `restrict_weapons_by_date` toggle.
- **No faction override.** Unlike weapons (`weapons_introduction_year_overrides`), the property gate
  uses a single global year. Add per-faction overrides only if a campaign needs them.
- **In-game pass ☑ VERIFIED 2026-06-26 (I3).** Confirmed in flight — a pre-2003 generated mission
  shows the baseline helmet option (not JHMCS) on an F/A-18/F-16; NVG and the Soviet SURA Visor untouched.

### Sibling gate — date-gated ground-support vehicles (FARP / airfield)

The same date-gating philosophy now also reaches the **ground-support trucks** spawned at FARP and
airfield ground-starts (the fuel tanker, ammo truck, and ground-power APA). Previously
`farp_truck_types_for_country` (`game/missiongenerator/tgogenerator.py`) was date-blind — a 1968
mission could spawn 1985 M978 HEMTT tankers on the ramp. The picker was also a ~155-line
`if country_id in [...]` chain.

The 2026-06-28 modernization pass made it **data-driven + date-aware**:

- The country→doctrine-bloc membership moved to module-level `frozenset`s
  (`_SOVIET_PATTERN_COUNTRIES`, `_WESTERN_PATTERN_COUNTRIES`, `_AXIS_PATTERN_COUNTRIES`) and the
  vehicle pools to module-level lists. Behavior is identical to the old chain (same countries, same
  pools) absent date-gating.
- A hand-authored `_GROUND_SUPPORT_INTRO_YEAR` table (pydcs carries no vehicle service dates, same
  as properties) drives `_support_vehicles_in_service(pool, year)`, which filters each pool to types
  in service by the mission year. It **rides the existing `restrict_weapons_by_date` toggle** — no
  new setting — with the year passed from `game.date.year` at the two call sites.
- **Fail-safe fallback:** an emptied pool falls back to its single oldest member, so generation
  never fails for want of a period-correct vehicle. This matters because vanilla DCS has **no**
  Vietnam-era US logistics truck — the M978 HEMTT (1985) is the oldest US tanker and stays the
  fallback, while the red/NVA side gets genuinely period-correct GAZ-66 (1964) / Ural-375 (1961).
- Covered by `tests/missiongenerator/test_farp_truck_dates.py` (filter keeps only in-service types,
  empty-pool fallback, Vietnam-era red is period-correct, US falls back without crashing, no-year =
  legacy behavior). Generic — a clean upstream-carve candidate alongside the §24 property gate.

## §26 — Off-mission combat fidelity + PLAYER_AT_IP fast-forward

The simulation auto-resolves the engagements the player does **not** fly — the AI-vs-AI fights that
happen while you fast-forward to first contact / your IP. Two coupled improvements.

### Capability-weighted abstract combat (was: coin flips)

The old resolution was numbers-only: in A2A the side with more flights won outright (ties 50/50) and
each survivor then died on a second 50/50; a SAM engagement was a flat 50% loss. So an obsolete jet
beat a modern one and SEAD's whole purpose was ignored.

`game/sim/combat/capability.py` weights the odds with data the planner already carries:
- **A2A strength** = best A2A `AircraftType.task_priority` (BARCAP/TARCAP/sweep/escort/intercept) ×
  number of airframes, with a floor so a non-fighter is weak but not auto-dead. Win probability is the
  strength share (`air_combat_win_probability`); winner survivor-loss scales with the margin
  (`air_combat_survivor_loss_chance`, clamped ≤ the legacy 0.5 so a winner is never *more* fragile than
  before — dominance only ever reduces losses).
- **SAM survival** (`sam_death_chance`) anchors at the legacy 0.5 for a generic flight vs one site,
  **halves** for a SEAD-role or SEAD-capable flight, **stacks** with each extra engaging site, clamped
  to [0.05, 0.95].

`aircombat.py` / `defendingsam.py` call these instead of `random.random() >= 0.5`. Deliberately coarse
— a campaign abstraction, not a DCS dogfight; `SKIP` is untouched and the player's flown missions are
still resolved by DCS.

### PLAYER_AT_IP actually reaches the IP

`FastForwardStopCondition.PLAYER_AT_IP` should spawn the player airborne at their IP. It was silently
defeated by `combat_resolution_method` defaulting to `PAUSE`: the fast-forward ended at the first
combat *anywhere* in the theater (`AircraftSimulation.on_game_tick`), which beats a ground-started
player flight to its IP, so generation spawned it at its configured start (`flightgroupspawner` reads
the sim state, which was still AtDeparture).

Fix: `AircraftSimulation._combat_pauses_fast_forward` — under `PLAYER_AT_IP`, an AI-only combat no
longer stops the fast-forward (it keeps ticking and resolves via the capability path above); only a
combat that **involves a player flight** still pauses (you fly that one). Applied to both stop-guards
in `on_game_tick`. Other stop conditions and `force_continue` are unchanged.

### Files & tests

| Area | Path |
|---|---|
| Capability scoring | `game/sim/combat/capability.py` |
| A2A / SAM resolve | `game/sim/combat/aircombat.py`, `game/sim/combat/defendingsam.py` |
| Fast-forward gate | `game/sim/aircraftsimulation.py` (`_combat_pauses_fast_forward`) |
| Tests | `tests/test_combat_resolution_capability.py`, `tests/test_player_at_ip_fast_forward.py` |

### Gotchas / deferred

- **Pilot experience not folded in yet** — capability is airframe + numbers + role only.
- **`task_priority` is a planner *suitability* score**, not a pure A2A rating, so the spread is
  compressed (≈480 MiG-21 → 665 F-15C). It orders matchups correctly; sharpen with an exponent or a
  dedicated rating only if outcomes feel too flat.
- **Needs an in-game pass:** confirm auto-resolved attrition reads believably, and that
  `PLAYER_AT_IP` + the default PAUSE resolution now spawns the player at the IP.

## §27 — Shared-airframe kneeboard index (co-op orientation)

> **Superseded surface (§30):** the standalone `KneeboardIndexPage` was folded into the always-present
> **cover page** — the index is now a *section* on the cover (shown only when 2+ client flights share
> the airframe). The grouping + start-page math below are preserved; only the host page changed.

DCS scopes kneeboards per *airframe*, not per group, so every pilot of a type sees all of that type's
flight decks stacked together (see the `client_flights_by_airframe` note). A 4-ship-of-Hornets
squadron flips through four decks to find theirs.

`KneeboardGenerator.generate` now keeps each flight's pages a **contiguous block** in deterministic
(callsign-sorted) order, and prepends a one-page **index** (`KneeboardIndexPage`) — callsign (+ custom
name), task, and start page per flight — **only when 2+ client flights share the airframe**. A lone
flight's deck is unchanged (no extra page). Start pages account for the index page itself (block 1
starts on page 2) and for `paginate()` expanding a flight's block. `pages_by_airframe()` became
`client_flights_by_airframe()` (grouped + sorted flights); `_build_kneeboard_index` builds the page.

### Files & tests

| Area | Path |
|---|---|
| Index page + generate | `game/missiongenerator/kneeboard.py` (`KneeboardIndexPage`, `generate`, `client_flights_by_airframe`, `_build_kneeboard_index`) |
| Tests | `tests/missiongenerator/test_kneeboard_index.py` |

### Gotchas / deferred

- **DCS limit, mitigated not removed.** Still no per-group kneeboard and no per-pilot ordering (every
  pilot of the type sees the same stack); the index just makes the stack navigable.
- **Needs an in-game pass:** confirm the index appears with correct start pages when 2+ client flights
  of one type are fragged, and is absent for a single flight.

## §28 — Settings IA reorg + difficulty presets

Two coupled UX wins on the settings surface (the in-game **Settings** dialog and the **New Game**
wizard both render from the same `QSettingsWidget`).

### The information-architecture reorg

The settings dialog is **100% metadata-driven**: `QSettingsWindow` builds every page → section →
control by walking `Settings.pages()` → `Settings.sections(page)` → `Settings.fields(page, section)`.
Historically those three yielded in raw **field-declaration order**, which had scattered ~150 settings
and left two grab-bag sections — `Campaign Doctrine / General` (34 settings) and
`Mission Generator / Gameplay` (37) — that no one could navigate.

The reorg introduces a single source of truth for the layout: **`FIELD_LAYOUT`** in
`game/settings/settings.py` (built from the readable `_LAYOUT_SPEC`), an *ordered* map of
`field name → (page, section)`. The three classmethods now resolve each field's group via
`_effective_layout` (FIELD_LAYOUT, falling back to the field's own `page=`/`section=` metadata so
nothing is ever dropped) and emit in FIELD_LAYOUT order via `_ordered_user_fields`. Net effect:

- **No field declarations moved, no behaviour change** — field names, values, and defaults are
  untouched, so there is **no save migration**. Only the UI grouping/order changes.
- The grab-bags are gone; the six content pages are **Difficulty & Realism · Air Doctrine ·
  Campaign Management · Mission Generation · Kneeboards · Performance**, each with focused sections
  (largest is the 13-item engagement-distance table). Difficulty-relevant settings that were
  scattered across pages (weapons-by-date, target-intel precision, recon fog, unlimited fuel,
  pilot/airframe limits) are **centralised onto Difficulty & Realism** so the preset has one home.
- Page icons for the renamed/new pages are aliased in `qt_ui/uiconstants.py` (and the page label is
  now `"Mission Generation"`, which matches its existing icon key — fixing a latent miss).

`tests/settings/test_field_layout.py` locks the invariants: FIELD_LAYOUT covers **every** user field
exactly once (a typo or omission fails CI), the UI walk emits each field once, the page order is the
designed order, and **no section exceeds 13 settings** (the anti-grab-bag guard).

### Difficulty presets

`game/settings/difficultypreset.py` adds a `DifficultyPreset` enum (**Casual / Normal / Veteran /
Ace**) and `PRESET_VALUES` — each preset sets the same 12 difficulty-defining fields (enemy skill ×2,
income ×2, pilot invulnerability, MANPADS, labels, map visibility, external views, easy comms, BDA,
weapons-by-date). `apply_preset(settings, preset)` sets just those fields; everything else is the
player's. **Normal mirrors the Settings defaults exactly** (a clean reset to stock), asserted in
`tests/settings/test_difficultypreset.py`. `detect_preset(settings)` returns the matching preset (or
`None` for a custom mix) to drive the "Current: …" readout.

The UI is a `DifficultyPresetBar` (`qt_ui/windows/settings/QSettingsWindow.py`) injected above the
auto-generated sections of the Difficulty & Realism page only: four buttons + a "Current:" label.
A click calls `apply_difficulty_preset` → `apply_preset` → `update_from_settings` (refreshes every
control from the mutated settings and re-highlights the bar) → `applySettings`. Player aids stay
fully editable afterward; the preset is a *starting point*, not a lock. Player coalition skill (AI
wingman quality, not a difficulty lever) is deliberately left alone by every preset.

### Files & tests

| Area | Path |
|---|---|
| Layout source of truth | `game/settings/settings.py` (`_LAYOUT_SPEC`, `FIELD_LAYOUT`, `_effective_layout`, `_ordered_user_fields`) |
| Preset engine | `game/settings/difficultypreset.py` (`DifficultyPreset`, `PRESET_VALUES`, `apply_preset`, `detect_preset`) |
| UI | `qt_ui/windows/settings/QSettingsWindow.py` (`DifficultyPresetBar`, page injection), `qt_ui/uiconstants.py` (icons) |
| Tests | `tests/settings/test_field_layout.py`, `tests/settings/test_difficultypreset.py` |

### Gotchas / deferred

- **The legacy per-field `page=`/`section=` kwargs are kept** as the fallback for any field absent
  from FIELD_LAYOUT; they no longer drive display. Leave them — they're the safety net.
- **The "Current:" highlight is best-effort.** It updates on preset click and on settings load, not
  live as the player hand-edits an individual control, so it can read "Custom" / stale until the next
  refresh. Acceptable for v1; wiring every difficulty control to re-detect is the follow-up.
- **Needs an in-game pass (UI eyeball):** open Settings and the New Game wizard, confirm the six
  pages/sections read cleanly, the preset bar tops Difficulty & Realism, each preset flips the
  expected controls, and "Current:" tracks. The build + apply flow is offscreen-smoke-verified and
  the logic is unit-tested; only the visual feel is unexercised by CI.

## §29 — Campaign SITREP kneeboard band

A "what happened last turn" digest on the player's next kneeboard — a morning intel brief in the
cockpit. It reads numbers the campaign already tallies; it does not recompute the war.

### Capture (`game/sitrep.py`)

`Sitrep` is a small frozen dataclass (turn, day, friendly/enemy `SideLosses`, captured/lost control
points, pilots recovered). `Sitrep.from_debriefing` reads straight off the `Debriefing` that
`MissionResultsProcessor.commit()` already has: per-side losses from `loss_counts()` (aircraft /
front-line / site units), captures from the **cached** `base_captures` snapshot, and Combat SAR
deliveries from `state_data.combat_sar_rescues`. A new last `commit()` sub-step, `record_sitrep`,
stores it as `game.last_sitrep`.

- **Enemy losses are framed as "claimed"** — same numbers, battle-damage phrasing — to stay
  consistent with the recon-fog model (§3). The campaign already committed the real losses; the band
  is the player-facing read-off.
- **Timing:** `commit()` runs (in `missionsimulation.py`) *before* the turn increments, so
  `game.turn` / `game.current_day` are the just-played turn. The band then shows on the **next**
  turn's kneeboard. Captured bases use the pre-commit `base_captures` attribute, **not** a re-call of
  `base_capture_events()`, which would re-evaluate ownership after `commit_captures` flipped the
  bases and drop them.
- **Persistence:** `game.last_sitrep` is pickled; `__setstate__` defaults it to `None` for old saves
  (no migration). `None` on turn 1.

### Surface (kneeboard cover band)

The model + capture live here; the **render surface is the dedicated cover page (§30)**. The generator
gates the SITREP with `sitrep_for_kneeboard(game.last_sitrep, settings.generate_sitrep_kneeboard)`
(returns the `Sitrep`, or `None` when the toggle is off / there is no prior turn / the previous turn
was quiet via `Sitrep.is_empty`), and `CoverPage` renders a "SITREP — Turn N" heading +
`Sitrep.kneeboard_lines()`. *(It shipped first as a band on the `BriefingPage` cover via
`_draw_section_if_fits`; §30 consolidated it onto a real always-present cover sheet alongside the
op/turn header and the shared-airframe index.)*

### Files & tests

| Area | Path |
|---|---|
| Model + builder + gate | `game/sitrep.py` (`Sitrep`, `SideLosses`, `sitrep_for_kneeboard`) |
| Capture hook | `game/sim/missionresultsprocessor.py` (`record_sitrep`, last in `commit`) |
| Persistence | `game/game.py` (`last_sitrep` + `__setstate__` default) |
| Setting | `game/settings/settings.py` (`generate_sitrep_kneeboard`, default ON, Kneeboards page) |
| Render | `game/missiongenerator/kneeboard.py` (`CoverPage`, `_cover_sitrep`) — see §30 |
| Tests | `tests/test_sitrep.py`; `COMMIT_STEPS` updated in `tests/test_missionresultsprocessor.py` |

### Gotchas / deferred

- **`commit` sub-step list is asserted.** `test_missionresultsprocessor.py` stubs every processor
  method and checks the exact set, so adding `record_sitrep` required adding it to `COMMIT_STEPS`.
- **v1 scope:** losses, captures, and Combat SAR rescues. **Front-line movement and the SCAR
  commander capture are deferred** — front movement needs a turn-over-turn position delta the
  debrief doesn't carry, and the SCAR signal isn't cleanly exposed at commit yet.
- **Player = BLUE** (the debrief-window convention). A RED-human setup would label sides from the
  wrong perspective; revisit if/when a campaign flips the human to red.
- **Needs an in-game pass (kneeboard eyeball):** folded into the §30 cover-page check — the SITREP now
  renders as a section on the always-present cover page (no fit guard). Confirm on turn 2 it shows the
  previous turn's losses/captures, and that turn 1 / a quiet turn shows no SITREP section. The numbers
  + render are smoke-verified; only the in-cockpit look is the residual.

## §30 — Dedicated kneeboard cover page

A single front sheet that **always** leads a flight's kneeboard deck, consolidating three things that
were previously scattered: the operation/turn header (new), the previous turn's SITREP (§29, was a band
competing for space at the bottom of the briefing page), and the shared-airframe flight index (§27, was
a separate page that only appeared for 2+ flights).

`CoverPage` (`game/missiongenerator/kneeboard.py`) is built by `_build_cover_page` and **always
prepended** in `generate()` (replacing the conditional `KneeboardIndexPage`). It draws:

- **Header (always):** `"<Operation> — Turn N"` + the in-game date (`game.campaign_name`, `game.turn`,
  `game.current_day`). So every deck opens telling you what op and turn you're flying. Because the cover
  is a standalone sheet it carries its own **oversized** type (48 pt op/turn, 26 pt date) — bigger than
  the rest of the deck — so it reads at a glance.
- **SITREP (when there's anything to report):** `"SITREP — Turn N-1"` + `Sitrep.kneeboard_lines()`,
  gated by `_cover_sitrep` → `sitrep_for_kneeboard` (§29). The model/capture are unchanged; only the
  render moved off the `BriefingPage` band onto the cover, so it's prominent and stops crowding the
  flight plan (the old `_draw_section_if_fits` band + `BriefingPage.sitrep_lines` were removed).
- **Flight index (when 2+ client flights share the airframe):** the §27 callsign → start-page table,
  folded in as a section. The cover is **page 1**, so the first flight's block starts on **page 2** (the
  start-page cursor is unchanged from §27; a lone flight simply gets a cover with no index section).
- **Friendly-package list (compact mode):** the coalition-wide package coordination list
  (`build_all_packages_rows` → `FriendlyPackagesPage.render_section`), built **once** for the shared deck
  from a representative flight. In the compact deck the recon photo owns the flex page, leaving the package
  list nowhere to go; the cover's otherwise-empty lower half is its home. Gated by
  `generate_all_packages_kneeboard` **and** `compact_kneeboard` (the full multi-page deck keeps its own
  standalone `FriendlyPackagesPage`, so the cover would duplicate it). `render_section` self-guards against
  a stranded heading when the cover is full.

### Why consolidate

The SITREP no longer competes for space on a busy Mission Info / Game Plan page, the index is no longer
a conditional standalone page, and a pilot **always** gets an at-a-glance "what op / what turn / what
happened / who's flying" sheet up front. Page numbering generalises cleanly (cover always page 1).

### Files & tests

| Area | Path |
|---|---|
| Cover page + assembly | `game/missiongenerator/kneeboard.py` (`CoverPage`, `_build_cover_page`, `_cover_sitrep`, `generate`) |
| SITREP gate | `game/sitrep.py` (`sitrep_for_kneeboard`) |
| Tests | `tests/missiongenerator/test_kneeboard_cover.py` (start-page math, lone-flight no-index, SITREP gating, render) |

### Gotchas / deferred

- **Replaces §27 + the §29 band surface.** `KneeboardIndexPage` / `_build_kneeboard_index` and
  `BriefingPage.sitrep_lines` / `_render_sitrep` are gone — folded into `CoverPage`. The §27 index
  behaviour (and its start-page math) is preserved, just hosted on the cover.
- **Every deck now has a cover**, including a single-flight deck (which previously had no extra page).
  That is intended — the op/turn header is the point.
- **Needs an in-game pass (kneeboard eyeball):** generate a mission and open the kneeboard. Page 1 is the
  cover: op name + turn + date always; the previous turn's SITREP section from turn 2 on (absent on
  turn 1 / a quiet turn); and a flight index when 2+ client flights share the airframe, whose start
  pages land on the right decks. The render is smoke-verified; only the in-cockpit look + live page
  numbers are the residual.

## §31 — One-page Brief Sheet + deck-wide colour scheme

The compact deck's lead page is the **Brief Sheet** (`BriefSheetPage`), a single scannable page modelled
on the squadron's printed **Appendix A** one-pager (the Red Tide briefing handbook, `docs/wiki/`). It
replaces the dense `BriefingPage` "Game Plan" (BLUF band over a full steerpoint table + weather) — the
page you open to first is now a *summary*, with the Threats/Comms detail pages behind it.

**Auto-fill (`KneeboardGenerator._build_brief_sheet_data`).** The page is a pure renderer of a
`BriefSheetData`; the generator pulls each field from data it already holds (the BLUF pattern):

- **Route** — `_brief_route` walks `flight.waypoints`, mapping types to `HOLD/JOIN/IP/TGT/EGRESS` and
  carrying each point's **steerpoint number** (the waypoint index, matching the old flight-plan `#`
  column) so the pilot can dial it up; the detailed steerpoint table is gone in compact mode.
- **Loadout** — `_brief_loadout` summarises the lead jet's generated pylons (`units[0].pylons` → `Weapon`)
  to the *ordnance*: counts by type, strips rack multipliers (`2xGBU-12` → `GBU-12`), collapses the TGP
  and HTS pods to `TGP`/`HTS`, and drops ECM / clean / unresolved stations.
- **Threats** — SAM from the threat cards (`_brief_sam_threats`, top live systems condensed); **air** from
  the enemy faction's fighters (`_brief_air_threats`, `faction.aircraft` filtered by
  `capable_of(BARCAP)`), kept loose to respect fog. **Game plan** = the most-lethal system's defeat note.
- The rest re-surface existing data: TOT, push/success/abort code words, bullseye, bingo/joker, divert,
  comms (`self.awacs/tankers` + package freq), fields (RWY/ATC/TCN via `_brief_fields`), laser codes
  (`_brief_laser`, gated as §25), and Combat SAR (`_brief_sar`: King/Jolly/Sandy from the side's flights).

**Fill-in blanks.** An empty field doesn't collapse — it renders a `______` rule (`_blank_line`) like the
printed template, so the layout is stable and the pilot can write the value in. A `NOTES` blank always
closes the sheet. (`LASER` is the one conditional row — gated to laser-capable loadouts, §25.)

**Deck-wide colour scheme.** A four-colour **semantic** palette lives on `KneeboardPageWriter`
(theme-aware: lighter shades on the night theme, darker on the day theme) with a new `text_runs`
primitive that draws a line of coloured segments: **blue** = nav/comms (route, freqs, bullseye, divert,
SAR callsigns, push), **amber** = caution (threats, bingo/joker), **green** = SUCCESS, **red** = ABORT +
the "if down" line. The same scheme is applied to **P2** (threat cards — amber MEZ/Detect, blue HARM
code + cues, emphasised system name) and **P3** (code words — push blue, SUCCESS green, ABORT red, STOP
JAM amber), so the whole deck reads as one product. The multi-column comm-ladder/AWACS/tanker tables stay
as plain `tabulate` reference tables (colouring cells is disproportionate).

### Files & tests

| Area | Path |
|---|---|
| Page + data + helpers | `game/missiongenerator/kneeboard.py` (`BriefSheetPage`, `BriefSheetData`, `_build_brief_sheet_data`, `_brief_*`, `KneeboardPageWriter.text_runs` + `col_*` palette) |
| Tests | `tests/missiongenerator/test_brief_sheet.py` (route/loadout/threats/mission helpers, render, end-to-end data build) |

### Gotchas / deferred

- **Replaces the compact `BriefingPage`/BLUF.** The full (non-compact) deck still uses `BriefingPage` +
  `_bluf_lines`; only the compact P1 changed.
- **Weather (`WX`) is left as a blank** for now — populating it from the `Weather` object is deferred; the
  blank lets a pilot write it. **Validated against a real `.miz`** (loadout cleanup + laser codes were
  caught that way); the residual is an **in-game pass** — generate a mission and eyeball the colours +
  auto-filled fields in the cockpit.

## §32 — Arc Light heavy-bomber Strike carpet (Vietnam Ops suite)

The first **Vietnam Ops suite** feature (suite design note
[`414th-vietnam-ops-notes.md`](design/414th-vietnam-ops-notes.md); the suite lives under a "Vietnam Ops"
settings page, §28). Retribution's modern engine never modelled the Operation Niagara **Arc Light** B-52
area strikes; this adds them as an **effect of the existing Strike task** — explicitly **not** a new
`FlightType` (the user's reframe). When a heavy bomber flies a `STRIKE`, the runtime walks a carpet of
bombs across the target at the run-in instead of dropping a single aimpoint.

### How it works (the Tier-A config bridge)

Python plans an ordinary Strike; the carpet is a runtime effect. `populate_vietnam_ops_lua`
(`game/missiongenerator/vietnamopsluadata.py`, called from `LuaGenerator.generate_plugin_data`) emits
`dcsRetribution.VietnamOps.arcLight` **only when** `Settings.vietnam_arc_light` is on, with one record per
eligible flight: a `STRIKE` whose `aircraft_type.dcs_unit_type.id` is in `HEAVY_BOMBER_DCS_IDS`
(`B-52H`/`B-1B`/`Tu-95MS`/`Tu-142`/`Tu-160`/`Tu-22M3` — vanilla DCS heavy bombers only). Each record carries
the bomber **group name** and its **target centre** (`package.target.position`, pydcs x=north / y=east).

The `vietnamops` plugin (`resources/plugins/vietnamops/vietnamops-config.lua`) watches each bomber group
on a 5 s poll; when the lead unit closes inside the release range (default 8 NM), it fires a **one-shot
carpet**: a box of `trigger.action.explosion` impacts oriented along the bomber's **bearing to the target**
(its run-in), rows stepping along-track with a small delay so it visibly walks, columns spreading it
cross-track, with per-impact jitter. Carpet length/width/per-blast power/release-range are plugin
`specificOptions` (defaults 1700×500 m, 300 kg, 8 NM). `pcall`-guarded throughout; inert with no
`VietnamOps` data, so non-Vietnam missions never load any of it.

### Why this shape

- **Losses stay native.** A bomber shot down before the run-in simply never fires its carpet, and where the
  box overlaps real ground TGOs the damage flows through the normal ground-loss path — no bespoke scoring.
- **Tactical strikers are untouched.** The heavy-bomber id gate means an F-4/A-4 Strike is an ordinary
  single-aimpoint strike.
- **Scripted carpet, not AI bombing.** AI B-52 bombing of a point target is inaccurate and unsatisfying; a
  scripted walking box over the area is both more reliable and more historical (Arc Light *boxes*).

### Files & tests

| Area | Path |
|---|---|
| Emitter | `game/missiongenerator/vietnamopsluadata.py` (`populate_vietnam_ops_lua`, `HEAVY_BOMBER_DCS_IDS`) |
| Hook | `game/missiongenerator/luagenerator.py` (call in `generate_plugin_data`) |
| Plugin | `resources/plugins/vietnamops/` (`plugin.json`, `vietnamops-config.lua`) |
| Setting | `game/settings/settings.py` (`vietnam_arc_light`, "Vietnam Ops" page) |
| Tests | `game/missiongenerator/tests/test_vietnamops_luadata.py` (eligibility gate, off = no node, no bombers = no record) |

### Gotchas / deferred — in-game pass ☑ VERIFIED 2026-06-28 (L1)

- **Blast power / density verified acceptable in the cockpit 2026-06-28** (checklist **L1**, audience pass,
  user verdict "good" — the carpet walks across the box, no FPS hit, no tuning requested). The knobs remain
  if a future campaign wants more/less: too weak and Arc Light underwhelms, too strong and it lags / over-kills.
- **Coordinate mapping:** pydcs Point (x=north, y=east) → DCS world vec3 `{x=north, y=alt, z=east}` is done
  Lua-side; ground height per impact from `land.getHeight`.
- **Symmetric by design:** any side's eligible heavy-bomber Strike carpets (a red Tu-95 too). Gated globally
  by the toggle; Vietnam campaign YAMLs flip it on.
- **Suite is Phase 1 of 5** — flak gauntlet, NGFS, convoy interdiction, Super Gaggle follow (see the suite
  design note).

## §33 — AAA flak gauntlet (Vietnam Ops suite)

The second **Vietnam Ops suite** feature. The fork's standing note is that the *real* Vietnam threat was
**AAA, not SAMs/MiGs**, yet Retribution's threat model is SAM/MEZ-centric and barely represents it. This adds
the AAA *atmosphere* campaign-wide: fly within range and below the ceiling of an opposing AAA gun and you draw
barrage flak; fly it predictably and the flak tightens.

### How it works

Unlike Arc Light, the flak needs **no per-mission threat data** — Python (`_populate_flak`) emits only an
on-marker `dcsRetribution.VietnamOps.flak = { enabled = "true" }` when `Settings.vietnam_flak_gauntlet` is on.
The `vietnamops` plugin does the rest:

- **AAA discovery (runtime).** Every ~30 s it sweeps both coalitions' ground units and keeps the ones with the
  DCS **`AAA`** attribute (so frontline ZSU-23/Shilka belts *and* airfield guns all contribute), grouped by
  side. No unit-name plumbing, and late-spawned guns are picked up.
- **Engagement.** Every 2.5 s, for each airborne aircraft between the floor (120 m AGL) and the ceiling
  (4500 m AGL), it counts alive **opposing** AAA guns within horizontal range (4500 m, capped at 3 for
  density) and, if any, spawns barrage bursts near the aircraft at its altitude.
- **Predictability.** A per-aircraft factor ramps up while heading (±8°) and altitude (±40 m) hold steady and
  drops fast on a jink. The barrage **miss distance** lerps from loose (250 m, jinking) to tight (70 m,
  predictable); a sustained predictable run (factor > 0.66) also draws one **close "tracking" round** per tick
  (tighter miss, ~2.5× power) — the modest bite that punishes straight-and-level flight.

Bursts are `trigger.action.explosion` airbursts (small default power) — **mostly visual pressure to jink, not
a hidden hard-kill SAM**. Symmetric: both sides' AAA flak the other side. `pcall`-guarded throughout; inert
without the `flak` marker.

### Files & tests

| Area | Path |
|---|---|
| Emitter (on-marker) | `game/missiongenerator/vietnamopsluadata.py` (`_populate_flak`) |
| Runtime | `resources/plugins/vietnamops/vietnamops-config.lua` (flak section) |
| Setting / options | `game/settings/settings.py` (`vietnam_flak_gauntlet`); plugin `specificOptions` (range/ceiling/miss/power) |
| Tests | `game/missiongenerator/tests/test_vietnamops_luadata.py` (marker on/off, independence from Arc Light) |

### Gotchas / deferred — in-game pass ◐ PARTIAL (checklist L2): too accurate on the 2026-06-28 pass; softened twice, re-fly owed

- **Lethality softened twice; re-fly owed.** The 2026-06-28 audience pass ("too accurate but working very
  well") read as a hard-kill threat rather than the intended mostly-visual pressure. The lever is the close
  **"tracking" round**. Two tuning passes since:
  - **2026-06-28:** `MIN_MISS` 70→110 m, tracking `miss ×0.35→×0.55` / `blast ×2.5→×2.0` and rarer
    (`factor > 0.66→0.8`), `BLAST` 8→6.
  - **2026-07-01 (L2):** the remaining lethality was the tracking round firing **every 2.5 s tick** once a jet
    held a steady line ~10 s. Now: base misses widened `MIN_MISS` 110→**150** / `MAX_MISS` 250→**320** m, and
    the tracking round is **occasional** — gated behind a sustained steady run (`factor > 0.85`) **and** a
    per-tick probability (`TRACKING_CHANCE = 0.3`) — and softened (`miss ×0.55→×0.75`, `blast ×2.0→×1.5`).
  Both passes changed `vietnamops-config.lua` **and** the matched `plugin.json` defaults. Still `◐ PARTIAL`
  until a re-fly confirms the feel (pressure to manoeuvre, no hard-kill). `flakBlastPower` / miss distances /
  range remain the campaign-side knobs.
- **Runtime cost:** the 2.5 s sweep iterates airborne aircraft × nearby AAA (capped). Bounded and pcall-
  guarded, but watch FPS on a very dense mission.
- **Deferred polish:** tracer streams from the airstrip AAA belts (v1 is barrage puffs only); a per-pilot
  "heavy flak — jink" cue.

## §34 — Naval gunfire support (Vietnam Ops suite)

The third **Vietnam Ops suite** feature: offshore gun ships (the iconic New Jersey 16″ batteries, plus
cruisers/destroyers/frigates) deliver shore bombardment — a capability the modern engine never modelled.

### How it works

`_populate_naval_gunfire` reuses the generator's existing ship-artillery classification — naval groups whose
lead unit is class **CRUISER / DESTROYER / FRIGATE** (the VWV battleship *New Jersey* is class `Destroyer`, so
it's covered) — and emits each as `dcsRetribution.VietnamOps.navalGunfire.ships[] = { group, coalition }`
(coalition from `TheaterGroundObject.faction_color`). Targets and ranging are resolved live, so the node only
needs which ships have guns and whose side they're on.

The `vietnamops` plugin runs **two modes** off that list (both via `MOOSE GROUP:TaskFireAtPoint` + `PushTask`,
the same path TIC uses for naval artillery):

- **Player call-for-fire (F10).** Each coalition that owns gun ships gets an F10 **"Naval Fire Mission →
  Fire on last F10 map marker"** command. It reads the coalition's most recent F10 mark
  (`world.getMarkPanels`) and fires the nearest in-range friendly gun ship there (with a "SHOT"/"no ship in
  range" call back).
- **Automatic coastal bombardment.** Every cadence (default 90 s), each alive gun ship shells the nearest
  **opposing** ground target within gun range. Because ships sit offshore and the range gate is ~20 km, this
  only ever reaches **coastal** targets — the feature is coastal-by-construction and **no-ops inland** (Khe
  Sanh), exactly as intended. Toggleable (`ngfsAuto`).

Symmetric (either side's gun ships). `pcall`-guarded; inert without the `navalGunfire` node.

### Files & tests

| Area | Path |
|---|---|
| Emitter | `game/missiongenerator/vietnamopsluadata.py` (`_populate_naval_gunfire`, `NAVAL_GUN_SHIP_CLASSES`) |
| Runtime | `resources/plugins/vietnamops/vietnamops-config.lua` (NGFS section) |
| Setting / options | `game/settings/settings.py` (`vietnam_naval_gunfire`); plugin `specificOptions` (range/rounds/salvo/auto/cadence) |
| Tests | `game/missiongenerator/tests/test_vietnamops_luadata.py` (gun-ship classification + coalition, carrier excluded, off / no-gun-ship = no node) |

### Gotchas / deferred — needs an in-game pass (checklist L3)

- **Coastal only.** Inland campaigns have no gun ship in range and correctly produce nothing; this is the
  historicity gate (Khe Sanh saw no naval gunfire). Keep `vietnam_naval_gunfire` **off** for inland YAMLs.
- **Gun reach is a selection gate, not a DCS truth.** `ngfsRangeM` (default 20 km) picks the ship/target; the
  actual round only impacts if the DCS gun can range it. Tune to the ship types in play during the pass.
- **Escort ships:** tasking a gun ship `FireAtPoint` can pull an *escort* off its station. Fine for a
  dedicated NGFS ship; watch it on a screening destroyer.
- **Deferred:** JTAC auto-lase → auto fire-mission (reading CTLD's laser target couples to CTLD internals);
  the F10 marker call + auto bombardment cover the capability for v1. "Fire on my position" (needs per-group
  menus) also deferred in favour of the marker call.

---

## §35 — Convoy interdiction (Steel Tiger) (Vietnam Ops suite)

The fourth **Vietnam Ops suite** feature: a moving enemy supply column on the road behind the FLOT — the
Ho Chi Minh Trail / Operation Steel Tiger — surfaced to the player through Armed Recon. The modern engine
models logistics as an abstract `convoy_routes` transfer; this makes one of those routes a **flyable,
interdictable target** that keeps flowing.

### How it works

**Python picks the corridor (`vietnamopsluadata.py` `_populate_convoy_interdiction`).** It walks the enemy
control points and their `convoy_routes`, keeps only **enemy→enemy** roads (an enemy→friendly road *is* the
contested front, not a rear supply line), and chooses the one whose midpoint is **nearest the FLOT**
(`game.theater.conflicts()`). Reusing the engine's real `convoy_routes` ties the target to actual red
logistics rather than inventing a road. It emits the chosen path + coalition as
`dcsRetribution.VietnamOps.convoy = { coalition = "RED", waypoints = { {x,y}, … } }`. No enemy road behind
the front (e.g. a single-CP front) ⇒ no node ⇒ the plugin no-ops.

**The `vietnamops` plugin runs the column at runtime** (vanilla DCS `coalition.addGroup`, `pcall`-guarded):
- Spawns a truck column (default 8 × `Ural-375`, strung out along the road) on the emitted corridor,
  driving it end to end **On Road**.
- **Halts under cover** (`Controller:setOnOff(false)`) whenever an opposing aircraft closes inside the
  scatter range (default 5 NM), and rolls again once the sky clears — the trucks "go to ground" when hunted.
- **Rolls a fresh column** a delay (default 600 s) after the old one is wiped, with a "convoy destroyed on
  the trail" cue, so the trail keeps producing targets across a long mission.
- Tunables (plugin `specificOptions`): speed, scatter range, respawn delay, truck count, truck type.

**Right-click planning (added per playtest).** Rather than hunting for the corridor, the player
**right-clicks an enemy supply route** on the map to frag the interdiction package:
`SupplyRoute.tsx`'s `contextmenu` on the wide invisible hit-line → `POST /qt/create-package/supply-route/{route_id}`
→ `interdiction_target_for_route_id` (`game/server/supplyroutes/models.py`) resolves the route id — which now
encodes both CP ids as `"<cp_a_id>:<cp_b_id>"` — to the **enemy end** (preferring the contested CP), and the
Qt new-package dialog opens there with the add-flight dialog auto-opened and **Armed Recon pre-selected**. A
friendly (all-blue) route resolves to nothing and 404s. Still an Armed Recon frag — just discoverable on the
route instead of requiring the player to know where to look.

### Files & tests

| Area | Path |
|---|---|
| Corridor emitter | `game/missiongenerator/vietnamopsluadata.py` (`_populate_convoy_interdiction`) |
| Runtime | `resources/plugins/vietnamops/vietnamops-config.lua` (convoy section) |
| Right-click server | `game/server/qt/routes.py` (`POST /qt/create-package/supply-route/{id}`), `game/server/supplyroutes/models.py` (`interdiction_target_for_route_id`, route id encodes both CP ids) |
| Right-click client | `client/src/components/supplyroute/SupplyRoute.tsx` (`contextmenu` → `useOpenNewSupplyRoutePackageDialogMutation`; hook hand-added to `_liberationApi.ts`) |
| Setting / options | `game/settings/settings.py` (`vietnam_convoy_interdiction`); plugin `specificOptions` (speed/scatter/respawn/count/type) |
| Tests | `game/missiongenerator/tests/test_vietnamops_luadata.py` (corridor pick: nearest enemy→enemy road, ignores the RED→BLUE front, off = no node); `tests/server/test_supply_route_interdiction.py` (route-id → enemy-end resolution, contested-CP preference, friendly/malformed → None) |

### Gotchas / deferred

- **Runtime spawn verified 2026-06-30** (checklist L6): a flown Khe Sanh session's `dcs.log` showed a
  complete spawn → drive → wipe → respawn cycle (`VietnamConvoy-1` then `VietnamConvoy-2` ~64 min later, no
  intervening reload), no `coalition.addGroup` Lua errors. The **halt-under-threat** (`setOnOff`) leg wasn't
  isolated in that pass — it needs a Tacview flown close enough to the corridor to force a halt.
- **Right-click path (checklist L7) needs an in-app pass + a CI client rebuild.** The server resolution is
  test-covered; the React `contextmenu` → Qt dialog path can't be exercised headless, and the client hook was
  **hand-added** to the generated `_liberationApi.ts` (codegen unavailable locally), so a stale `client/build`
  won't have it.
- **Corridor selection is deliberately "nearest enemy→enemy road."** On a theater with several rear roads it
  fragments to one; picking multiple / rotating corridors is a possible future refinement.
- **Blue-side symmetry not built:** the emitter hard-picks the RED supply road (the human fights red in the
  Vietnam case). A blue convoy for a red-player campaign would be a follow-on.

## §36 — Airbase harassment (rocket/mortar siege) (Vietnam Ops suite)

The fifth **Vietnam Ops suite** feature (design note `414th-vietnam-airbase-harassment-notes.md`, §F). The
Vietnam air war was fought as much *on the ground at the airbase* as in the air — Bien Hoa, Tan Son Nhut,
Da Nang, Chu Lai, and the Khe Sanh strip were under near-constant 122 mm rocket / 82 mm mortar / sapper
standoff attack for years. None of that exists in the base engine: an occupied airbase is a perfectly safe
rear area until the FLOT reaches it. This makes the forward strips feel contested — the missing other half of
the "the rear isn't safe" picture that §33 (flak over the *target*) started.

### How it works

**Python picks the eligible fields (`vietnamopsluadata.py` `_populate_airbase_harassment`).** For every land
airfield/FARP control point it keeps only those that are:

- **an airfield or FARP** (`HARASSABLE_CP_TYPES = {AIRBASE, FARP}`) — carriers/LHAs (their own control-point
  types) and ground-only FOBs are skipped; the siege modelled here is fire on a land ramp,
- **occupied** (`not cp.captured.is_neutral`),
- **forward** — within `HARASSMENT_FRONT_REACH_M` (≈ 200 km) of a front (`game.theater.conflicts()`), so a
  deep-rear field is never shelled; **no front ⇒ no node ⇒ the plugin no-ops** (forward-only by construction,
  the same posture as NGFS's gun-range gate), and
- **not a player-spawn field this mission** — the departure, arrival, or divert of any client flight, from
  `_client_spawn_control_points` (mirrors the `cull_farp_statics` walk in `tgogenerator.py`). This is the #1
  anti-grief guarantee: it is enforced **in Python** (an excluded field never enters the emitted `fields`
  list), and the exclude set is *also* emitted under `excludedFields` as a cheap Lua-side double-guard.

It emits `dcsRetribution.VietnamOps.airbaseHarassment = { fields = { {name,x,y,coalition}, … }, excludedFields
= { … } }` (the coalition is the field's owner, for the "incoming" cue and symmetry).

**The `vietnamops` plugin runs the siege at runtime** (vanilla DCS `trigger.action.explosion`, `pcall`-guarded):
- One scheduled loop per emitted field. The **first** event fires only after a **startup grace period**
  (default 300 s) so nobody is shelled mid-alignment, then repeats on a **randomized cadence** (default ~240 s
  ± 50 %) — historical harassment was sporadic, not a metronome.
- Each event lands a short **barrage** (default 5 impacts, walked 0.4 s apart) scattered uniformly over a
  **dispersion disc** (default 260 m) around the parking centroid, at a small **per-impact power** (default 8)
  — mostly noise/smoke with a modest, tunable bite. A direct hit on a parked static is a bonus, not the goal.
- A defensive Lua re-check skips any field whose name is in `excludedFields` (belt-and-suspenders over the
  Python filter), and announces "Incoming — standoff fire on <field>" to the owning coalition.
- Tunables (plugin `specificOptions`): interval, rounds/event, dispersion radius, per-blast power, grace.

### Files & tests

| Area | Path |
|---|---|
| Emitter | `game/missiongenerator/vietnamopsluadata.py` (`_populate_airbase_harassment`, `_client_spawn_control_points`, `HARASSABLE_CP_TYPES`, `HARASSMENT_FRONT_REACH_M`) |
| Runtime | `resources/plugins/vietnamops/vietnamops-config.lua` (airbase-harassment section) |
| Setting / options | `game/settings/settings.py` (`vietnam_airbase_harassment`); plugin `specificOptions` (interval/rounds/dispersion/power/grace) |
| Tests | `game/missiongenerator/tests/test_vietnamops_luadata.py` (forward occupied field emitted; rear / neutral / carrier / off / no-front → no node; a lone client-spawn field yields no node; a client-spawn field is excluded from targets but listed under `excludedFields`) |

### Gotchas / deferred

- **Never grief the cold-starting player.** The player-spawn exclusion + the startup grace period are **hard
  requirements**, not options (design note "critical design tension"). The Python filter is authoritative; the
  Lua exclude re-check and grace period are additional layers. The #1 in-game fail signature is any impact on
  or near a client-spawn field — watch for it on the pass (checklist L8).
- **Runtime is unflown (checklist L8).** The Lua passes the `luac5.1 -p` syntax gate but the scheduled loop,
  the explosion placement, and the grace/cadence timing can't be exercised headless — it needs a cockpit pass.
  Tune power/dispersion down if it reads as too lethal (as §33 flak did on its first audience pass).
- **Symmetric but forward-gated.** Both sides' forward fields qualify; a theater with no contested field near a
  front emits nothing. Optional low-rate harassment of the player's *own* forward strips (accepting the grief
  risk for immersion) was deliberately deferred — v1 excludes every player-spawn field unconditionally.
- **Runtime-cosmetic only.** Destroyed parking statics are runtime damage (like §33/§34); there is no BDA
  feedback into the campaign model.

## §37 — Super Gaggle hilltop resupply (Vietnam Ops suite)

The sixth **Vietnam Ops suite** feature (design note `414th-vietnam-ops-notes.md`, §E). Models the Khe Sanh
"Super Gaggle": a formation of transport helos runs supplies into a cut-off forward friendly outpost while the
player can fly escort. The base engine has no besieged-outpost resupply; this makes the forward hilltops feel
supplied-under-fire the way they historically were.

### Scope decision — runtime, not the planner

The design's v1 was a **planner-template** auto-frag (suppress + cargo + escort package, self-planned like
`auto_combat_sar`). That is **blocked on an auto-plannable CTLD cargo run the engine lacks** — there is no
FlightType/tasking that fragments a helo cargo-delivery to a specific outpost. Rather than build that whole
commander-brain capability, this ships **runtime-only**, exactly like the §35 convoy: Python picks the
geography and the `vietnamops` plugin spawns/flies the gaggle. The distinctive **fast-mover AAA-suppression
choreography** (the fast movers that worked the guns so the helos could get in — A-4 Skyhawks at the
historical Khe Sanh gaggle) **landed 2026-07-01** as a second increment (below), after the helo run shipped.

### How it works

**Python picks the geography (`vietnamopsluadata.py` `_populate_super_gaggle`).** It selects the friendly
(BLUE) **FOB/FARP nearest a front** as the besieged outpost — gated to within `GAGGLE_OUTPOST_FRONT_REACH_M`
(≈ 150 km) so a rear base is never chosen — and the nearest **other** friendly helo-capable field
(`AIRBASE`/`FARP`) as the launch point. It emits
`dcsRetribution.VietnamOps.superGaggle = { coalition = "BLUE", outpost = {name,x,y}, launch = {x,y} }`. No
forward friendly outpost, no launch field, or no front ⇒ no node ⇒ the plugin no-ops.

**The `vietnamops` plugin runs the gaggle at runtime** (vanilla DCS `coalition.addGroup`, `pcall`-guarded):
- Spawns a helo gaggle (default 3 × `UH-1H`, air-started over the launch field) routed **launch → outpost →
  back**, with a "SUPER GAGGLE — resupply helos inbound … Escort welcome" cue to the friendly coalition.
- A 10 s tick announces **"delivered"** once the lead helo reaches the outpost (within `DELIVER_RADIUS`), and
  **"down"** if the gaggle is destroyed en route (losses stay native).
- **Re-rolls a fresh run** a cadence (default 900 s) after the old one is delivered *or* lost, so the resupply
  keeps flowing across a long mission (a completed run is recycled after `MISSION_TIME`).
- **Fast-mover suppression choreography (2026-07-01).** Each gaggle also launches a short attack flight
  (default 2 × `A-4E-C` — the historical Super Gaggle suppressor) that flies **launch → over the outpost
  (CAS task, so the AI works the nearby AAA) → back** at a higher altitude, tied to the gaggle's lifecycle
  (spawned with it via `spawnSuppressors`, destroyed with it via `despawnSuppressors` at the single
  `scheduleRespawn` choke point). The "inbound" cue notes "Fast movers suppressing the guns" when they
  spawned. The whole suppressor spawn is its own `pcall`, so if the type's mod isn't loaded (or it fails to
  spawn) the helo run is untouched. Set the suppressor count to 0 to disable.
- Tunables (plugin `specificOptions`): helo type, count, transit speed, transit altitude, respawn cadence;
  suppressor count / type / altitude.

### Files & tests

| Area | Path |
|---|---|
| Emitter | `game/missiongenerator/vietnamopsluadata.py` (`_populate_super_gaggle`, `GAGGLE_OUTPOST_CP_TYPES`, `GAGGLE_LAUNCH_CP_TYPES`, `GAGGLE_OUTPOST_FRONT_REACH_M`) |
| Runtime | `resources/plugins/vietnamops/vietnamops-config.lua` (Super Gaggle section) |
| Setting / options | `game/settings/settings.py` (`vietnam_super_gaggle`); plugin `specificOptions` (helo type/count/speed/altitude/respawn) |
| Tests | `game/missiongenerator/tests/test_vietnamops_luadata.py` (emits outpost+launch+coalition when on; picks the nearest-front outpost + nearest launch; off / no-outpost / no-launch / no-front / enemy+rear outposts → no node) |

### Gotchas / deferred

- **Runtime is unflown (checklist L9).** The Lua passes the `luac5.1 -p` gate, but runtime helo spawning +
  routing + the deliver/respawn state machine can't be exercised headless — needs a cockpit pass. Watch that
  the helos actually reach the outpost (routing/altitude), the delivery/lost/respawn cues fire once each, and
  `coalition.addGroup` throws no Lua error in `dcs.log`.
- **Suppressor weapons are the #1 in-game tuning item.** The suppressor group spawns with DCS's *default*
  loadout for its type (no explicit `payload` — a per-mod pylon table is too fragile to hand-author blind), so
  its actual ordnance/effectiveness against the AAA is unverified: it may strafe, or it may be a visual-only
  presence. Confirm on the in-game pass and, if it needs teeth, give it an explicit payload or a scripted
  suppression effect. A spawn failure is already harmless (guarded → helo run proceeds, cue omits the line).
- **Runtime-cosmetic.** The delivery has no supply-economy effect (like the §35 convoy); the value is
  immersion + the escort opportunity.
- **Blue-only (symmetry deferred).** The emitter hard-picks the BLUE outpost (the human's cut-off hilltops),
  mirroring the convoy's RED-only stance; a red-player mirror would be a follow-on.
- **Not a helo-slot dependency.** The gaggle is spawned at runtime by coordinate, so the outpost can be a
  ground-only FOB (the Khe Sanh case) — the helos fly to its position, they don't need a parking slot there.
