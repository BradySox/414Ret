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

### QRA forward defense — rear bases answer raids at the front (2026-07-09)

`qra_forward_defense` (Air Doctrine → Air defense & QRA, **default ON**; the kill switch) +
`qra_defense_depth_nm` (default 60). Checklist **A5**.

The problem: `SetGciRadius` is **one radius per coalition, measured from every base**
(`AirbaseDistance <= self.GciRadius`, Moose's GCI loop). At the stock 60 NM a rear field never
scrambles for a raid at the front — on Red Tide, five of red's six fighter squadrons sit 126–290 NM
from Haina, so 20 of red's 24 alert airframes only ever defended Berlin. But simply widening the
radius so Sperenberg reaches Haina *also* lets Haina's own alert chase 200 NM the other way, deep
into blue.

The two are separated by giving each dispatcher a **border zone**:

- **`SetBorderZone(zones)` → `Detection:SetAcceptZones(zones)`.** Moose drops any detected object
  outside every accept zone, so the dispatcher cannot see — cannot scramble against, cannot keep
  engaging — a target beyond the defended airspace. This decides **where** a side may fight.
- **`SetGciRadius`** then decides only **how far a base will launch** to get there, and opens to
  `QRA_FORWARD_REACH_NM` (200). Safe, because geography is now bounded independently.
- **`SetDisengageRadius`** must open with it (`reach + engage + DISENGAGE_MARGIN_NM`): Moose aborts a
  defender once `DistanceFromHomeBase > DisengageRadius` (default 300 km ≈ 162 NM), so a base at the
  far edge of its reach would otherwise launch and turn around mid-transit. This is the non-obvious
  half — without it the feature silently does nothing for the farther fields.

**A wide reach does not mass-launch.** Moose's GCI loop keeps the squadron with the shortest
*intercept* distance among those inside `GciRadius`, and only reaches back to a farther one once the
closer squadron's alert is spent — an echelon: the front field answers, the rear fields backfill.

Zones are built by `defense_zone_entries` (`interceptluadata.py`): one circle per non-neutral,
non-`OffMapSpawn` control point, radius `qra_defense_depth_nm`; a CP anchoring an active front is
**grown to `distance(cp, front) + FRONT_FORWARD_MARGIN_NM` (25 NM)** so the contested airspace is
always defended however far back the anchor sits. That margin is the *only* place a side's airspace
crosses the line. Emitted per coalition under `dcsRetribution.Intercept.ZONES`; an empty bucket ⇒ the
Lua skips `SetBorderZone` ⇒ pre-feature behaviour.

Non-regressive by construction: with `depth == qra_gci_max_radius_nm` (both default 60), the set of
raids that used to trigger a GCI (within that radius of *some* base) is exactly the union of the
circles.

Interactions: **an ambush doctrine wins outright** — `dispatcher_tuning` returns the Vietnam W5 radii
unchanged and `disengage_nm = 0`, because the late, close GCI slash is the whole point of that
posture and forward defense must not widen it. The **player scramble cue** keeps the narrow radius
(`min(tuning.scramble_nm, setting)`), since the human's alert flight defends its own field — cueing
it for a raid 200 NM away would be constant false alarms, and `min` also preserves the ambush
doctrine's *shrunk* cue.

Red Tide, verified against a live save: red's airspace covers Haina, the FLOT and Fulda (42 NM, the
blue front base) but excludes Frankfurt (94 NM), Hahn, Spangdahlem and Ramstein; the 200 NM reach
brings Sperenberg/Schonefeld/Wittstock/Hamburg/Templin while Peenemunde (226) and Kastrup (290) stay
home. Tests: `tests/missiongenerator/test_qra_defense_zones.py`,
`tests/missiongenerator/test_interceptluadata.py`, `tests/test_vietnam_doctrine.py`.

### GCI-ambush posture (Vietnam campaign layer W5)

The Vietnam adaptation of the QRA dispatcher (will-note §6; checklist **M5**). `Doctrine.gci_ambush`
(True only on `VIETNAM_DOCTRINE`) flips a side's dispatcher from the modern stand-and-fight duel to the
era's GCI hit-and-run:

- **Python** (`dispatcher_tuning` in `game/missiongenerator/interceptluadata.py`, called per side in
  `spawn_intercept_templates`): the engage radius shrinks to the doctrine's `cap_engagement_range`
  (22 NM — the P1c close-fight number) and the scramble (GCI) radius caps at `AMBUSH_GCI_RADIUS_NM`
  (40 NM) so the MiGs launch **late** and slash the strike package near its target instead of meeting
  the sweep at the border. A tighter user setting always wins (min). The `ambush` flag rides each
  `InterceptEntry` (`ambushPosture` in the Lua table).
- **Lua** (`intercept-config.lua`): an ambush coalition's dispatcher gets the hit-and-run leash —
  `SetDisengageRadius(50 NM)` (Moose aborts the engagement when the defender is that far from home) and
  `SetDefaultFuelThreshold(0.35)` (one slash, then RTB to re-arm) versus Moose's 162 NM / 0.15 defaults.
- **Sanctuary basing** falls out of the W4 restricted zones for free: an airfield inside an active zone
  can't be OCA'd (test-locked in `tests/fourteenth/test_phases.py`), so the MiGs are safe on the ground
  until the arc's escalation lifts the zone — the Rolling Thunder problem, on purpose.
- Symmetric by doctrine (a Vietnam-doctrine blue side gets the same posture); every other doctrine
  passes the QRA settings through untouched (test-locked in `tests/test_vietnam_doctrine.py` +
  `tests/missiongenerator/test_interceptluadata.py`).

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

**Recon drone in each Armed Recon package (2026-07-05, 414th call).** The auto-recon
hook (`PackageFulfiller._maybe_plan_tarps_recon`) now also frags a recon flight into
**Armed Recon** packages, not just Strike/DEAD. Two supporting changes: `TarpsFlightPlan`
was widened to accept a `ControlPoint` target (an armed-recon sweep targets a CP corridor,
not a TGO — the base `recon_area` overflight already handles any `MissionTarget`), and the
armed-recon hook skips the `warrants_recon` TGO gate (a swept corridor always warrants an
overwatch pass). It stays **optional** (drops silently if no TARPS bird is free — never
scrubs the package) and gated by the same `auto_add_tarps_recon` setting. Because the recon
bird is whatever is `TARPS`-capable in the faction, on a **UAV-fielding faction (OIR:
Predator/Reaper carry `TARPS`) this frags a drone into every armed recon package** — and
the `airecon` plugin banks that AI drone overflight as confirmed BDA, so the drone is what
localizes the swept area's concealed contacts (§3 concealment loop). Alongside, the Armed
Recon primary is a fixed **4-ship** (`PlanArmedRecon.ARMED_RECON_FLIGHT_SIZE`) and the
existing threat-gated SEAD escort (`propose_common_escorts`, 2-ship) resolves to the Viper
on OIR/Red Tide — so a full armed recon package reads **1 drone + 2 SEAD Vipers + 4 recon**
(`game/commander/packagefulfiller.py`, `game/ato/flightplans/tarps.py`,
`game/commander/tasks/primitive/armedrecon.py`; tests `tests/test_armed_recon_planning.py`;
checklist G25 — the in-mission composition needs a fly).

**That drone is a lasing JTAC (2026-07-05, 414th call).** The 414th ripped out the old FLOT
auto-JTAC (a `jtac_unit` MQ-9 glued to the front line); `JtacInfo` went unproduced and
`jtac_unit` dormant, but the CTLD JTAC-autolase runtime + the kneeboard/radio consumers stayed
live. `AircraftGenerator._maybe_configure_jtac` revives it, hung on the **packaged drone**
instead of a FLOT unit: an AI-flown flight of the faction's `jtac_unit` (the MQ-9/Predator) in
an **air-to-ground package** (`_JTAC_PACKAGE_PRIMARIES` = Armed Recon / CAS / BAI / Strike —
option 1; may narrow to {Armed Recon, CAS} later) is emitted as a `JtacInfo` (group name +
allocated laser code + UHF freq + callsign + the target as its region). That flows to
`dcsRetribution.JTACs` → `ctld-config.lua` `ctld.JTACAutoLase` (**autolase + smoke both default
ON**), so the drone lazes and smoke-marks ground targets for the shooters and shows on the
kneeboard/radio like any JTAC. **No DCS task is added** — the drone flies its own package
mission (recon overwatch / attack) and lases what it overflies; CTLD does the designation.
**Blue + AI only** (a player drone is not an autolase JTAC), **not** invisible/immortal (unlike
the old FLOT JTAC — the packaged drone is a real asset that can be shot down). The laser code is
allocated per JTAC (or forced to 1113 when the `ctld.fc3LaserCode` option is on, for FC3
receivers). (`game/missiongenerator/aircraft/aircraftgenerator.py`; tests
`tests/missiongenerator/test_drone_jtac.py`; checklist G26 — needs an in-game pass, including
whether a moving/overflying drone sustains a useful lase or wants a loiter profile.)

**Auto-fielding the JTAC drone squadron (2026-07-05, 414th call).** The packaged drone-JTAC
only fires if a drone squadron *exists and gets fragged* — but squadrons are created only from
a campaign's `squadrons:` block, so the 55+ campaigns that never list a drone would show no
JTAC (the old FLOT auto-JTAC was always spawned by a special code path — that's gone). This
restores "every JTAC-capable side has a JTAC" as a real squadron: at New Game
(`Coalition.configure_default_air_wing` → `ensure_jtac_drone_squadron`,
`game/fourteenth/jtac_drone.py`), each **blue** side whose faction declares a **drone**
`jtac_unit` (in `UAV_DCS_IDS`, TARPS-capable) and doesn't **already field a drone** gets one
small (2-ship) **TARPS-tasked** drone squadron auto-fielded at the **rear-most airfield** (the
blue field farthest from the nearest enemy base that `can_operate` it). The auto-recon hook
then frags it forward into A/G packages, where it becomes the JTAC and films the whole time.
Deliberately conservative: **skips a campaign that already hand-places drones** (e.g. Operation
Inherent Resolve — untouched), blue-only, and gated by `auto_jtac_drone` (default **ON**) as a
kill switch for balance-sensitive campaigns. **Era-gated** (`_UAV_SERVICE_YEAR`): many factions
carry a lazy default `jtac_unit: MQ-9` even in the 1980s/90s, so the auto-field never drops a
drone that didn't exist yet — Red Tide is **1988**, and the Reaper (2007) / Predator (1995) /
WingLoong (2014) are all skipped there (12 Cold-War factions carry the default MQ-9). The floor
applies only to the AUTO-field; a campaign that deliberately fields a drone is its author's call.
Verified: the gate qualifies real modern factions (bluefor_modern / usa_2005 / israel_2017 →
MQ-9, drone + TARPS-capable) and the era floor skips a 1988 start. Tests
`tests/fourteenth/test_jtac_drone.py`; checklist G27 — the fielded-and-fragged loop needs a fly.

- Enum + behavior: `game/ato/flighttype.py`, `game/missiongenerator/aircraft/aircraftbehavior.py`
  `configure_tarps()` — a single flyover of the target area, ReturnFire ROE, no offensive
  stores. It sets the recon *behavior*; the *timing* lives in the flight plan (below).
- **Role-aware TOT** (`TarpsFlightPlan.default_tot_offset`): the recon bird does two different
  jobs and they want opposite timing. On a **Strike/DEAD** package it is a **post-strike BDA**
  pass — overfly **+2 min** after the shooters to photograph the damage (tight so it stays
  under the escort window, G19). On an **Armed Recon** package (or a standalone recon mission)
  there is no strike moment to trail, so it is a **find/overwatch** pass — **0 offset**, on
  station with the package to scout/localize, not two minutes behind an event that never
  happens. (This replaced a flat +2 min that was BDA-only reasoning applied to every package —
  the 2026-07 recon-rework de-jumble.)
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
  `resources/customized_payloads/vwv_{rf101b,ra-5}.lua`. The **1968 Yankee Station** campaign
  fields both (RF-101B at Da Nang, RA-5C on the carriers), tasked `primary: TARPS`
  (`resources/campaigns/1968_Yankee_Station.yaml`).
- Tests: `tests/test_tarps_recon.py` (Tomcat + Vietnam-recon TARPS-capability gates).

**AI recon BDA capture (`airecon` plugin, 2026-07-01 — closes G19).** The MOOSE TARS film engine
(§12) that turns a TARPS overflight into a confirmed BDA capture is **player-only** — its birth
handler drops any unit that isn't player-crewed (`TARS.lua`:
`if not unit or not unit:GetPlayerName() then return end`). So an *AI-flown* recon flight (the
auto-paired recon birds, or a whole squadron of them) flew the recon path but recorded **zero**
captures no matter that it survived and overflew — the checklist G19 "capture-side gap." The
`airecon` plugin closes it without touching the player path:
- **Emitter** (`game/missiongenerator/aireconluadata.py` `populate_ai_recon_lua`, dispatched from
  `luagenerator.py`): emits `dcsRetribution.AIRecon = { flights = { {group,label,target,x,y}, … } }` for
  each **AI-flown** (`not flight.client_units`), **player-coalition** (`flight.friendly is Player.BLUE`)
  **recon-capable** flight + its package target. `label` (callsign + airframe, e.g. "Chevy 9 (MQ-9
  Reaper)") and `target` (the package target's name) exist purely for the coalition cue — the 2026-07-06
  flown session had two identical "recon flight confirmed BDA" popups minutes apart with no way to tell
  which drone or where, so the cue now reads "TARPS: Chevy 9 (MQ-9 Reaper) confirmed BDA on 23 target(s)
  at Shirqat." (the plugin falls back to the raw group name / no location for records without the fields). Recon-capable (`_feeds_ai_recon`) = a **TARPS-tasked**
  flight (any airframe — the auto-paired recon bird) **OR a drone** (`UAV_DCS_IDS`) **regardless of its
  tasked mission** — the 414th "**a drone is always filming**" rule: a UAV is a sensor first, so whether
  it is off on a solo recon, riding a strike as the JTAC (§3 drone-JTAC), or working CAS, it still banks
  BDA on whatever it overflies (a *manned* combat jet only feeds it when actually tasked TARPS). A
  player-crewed flight is never emitted (it still films via the F10 menu); a red flight is never emitted
  (only the human's recon feeds the player's BDA). No such flights ⇒ no node ⇒ the plugin no-ops.
- **Runtime** (`resources/plugins/airecon/airecon-config.lua`): watches each emitted flight and, when
  its lead unit survives to close within the trigger range (default 5 NM) of the target, records the
  enemy (RED) ground units within the capture radius (default 4 km) of the target into the **same**
  `tars_recon_captures` ledger the player film menu appends to (identical `{ unit, life, type }`
  schema), sets `dirty_state`, and one-shots. A recon flight shot down or aborting before the target
  confirms nothing. So the Retribution debrief (`game/debriefing.py` `parse_tars_captures` →
  `MissionResultsProcessor.tars_reconned_tgos`) lifts the fog on what an AI recon flight photographed
  exactly as it does for a player. Plugin options: trigger range, capture radius, per-flight cap, poll.
- Emitter-tested (`game/missiongenerator/tests/test_airecon_luadata.py`: AI-blue TARPS emitted; a drone
  emitted on any task; manned-non-TARPS / player-crewed / red / no-target skipped; empty → no node).
  Runtime Lua needs an in-game pass (checklist G19). Blue-only + player-only-exclusion by design.

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

**Concealed field forces — "in here somewhere" uncertainty areas (2026-07-05).** The recon
intel-fog above hides *composition* but the marker still X-marks the exact spot, so "finding"
a hidden site was fiction. A fourth rule fixes the *position* half: while `known_for(BLUE)`
is False, a qualifying TGO's map presence is a dashed amber **uncertainty circle** (amber
since the §28 UI audit — dashed red now exclusively means an ROE off-limits zone) instead of
an exact marker — centred on a **deterministically jittered** point (seeded from the TGO id
so it never wanders between refreshes; offset 15–60 % of the radius so the truth always sits
inside) with the true coordinates **never sent to the client** while concealed. Two ways in:
- **COIN intrinsic** — the hidden insurgent spawns (roadside IED/VBIED, HVT convoy,
  dispersed/re-infiltration cells) carry `TheaterGroundObject.concealed = True` from
  `spawn_red_ground_at(concealed=True)`, independent of any setting (it's their identity);
  caches + stronghold garrisons stay exact.
- **`concealed_enemy_forces` setting** (Difficulty & Realism, default **ON**; only meaningful
  while `recon_intel_fog` is on since discovery funnels through `known_for`) — enemy **field**
  forces qualify by kind: mobile SAM sites (`category == "aa"` with task MERAD/SHORAD/AAA —
  the Weasel hunt), deployed vehicle groups (`"armor"`, tighter 3 km circle), and missile
  sites (`"missile"` — the SCUD hunt). **Fixed infrastructure stays exact**: LORAD strategic
  sites, EWRs (they emit — passively geolocatable), buildings, ships, airfields, and
  user-placed (drop-spawn) TGOs.

**Road-pinned variant (2026-07-05, user call):** a TGO carrying
`TheaterGroundObject.concealed_route` (a polyline of `(x, y)` map coordinates — the roadside-IED
layer stores its supply road at plant time) slides its suspected-activity centre **far ALONG that
route** (5–25 km, deterministic, clamped/bounced at the road's ends — `_route_jitter` in
`game/server/tgos/models.py`) instead of the radial offset: "we know what highway it's on, not
which street." Deliberately, the truth may sit **outside** the drawn circle here — the road itself
is the search domain (sweep the highway), and the radial invariant (truth always inside) applies
only to non-route concealment. A degenerate route (< 2 points / zero length, or a pre-feature
save) falls back to the radial jitter.

The circle keeps the marker's click/right-click contract (plan TARPS/strike against the
suspected area); discovery (attacked/scouted/TARPS — the same `discovered_by_player` gate),
recon fog off, or the overview reveal snaps it to the exact symbol. Two consequences by
design: a killed-but-not-reconned concealed site keeps its circle until BDA confirms it (the
recon loop), and auto-planned routes still bend around SAMs the map claims are un-located
(threat math is ground truth — the standing §3 rule, just more visible now). Known accepted
leak: a package planned against a concealed TGO puts its steerpoint at the true position
(that IS the localization mission; §5 Approximate precision covers player steerpoints).
Implementation: `concealed_uncertainty`/`_concealed_radius` in `game/server/tgos/models.py`
(both the `/game` pull and the SSE `updated_tgos` path go through it),
`client/src/components/tgos/Tgo.tsx` (`ConcealedTgo`), `Tgo.uncertainty_radius_m` in the API
model. Tests: `tests/fourteenth/test_coin_concealment.py`. Checklist **G24** + the COIN P3
concealment bullet — needs an in-app pass + the CI client rebuild.

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

**Right-edge clipping fit.** Wide content that used to run off the right edge (and silently lose
data) is now fitted to the page: `KneeboardPageWriter.table()` measures `tabulate`'s *actual*
rendered width and, when it overruns, passes `maxcolwidths` (via `_fit_col_widths`, shrinking the
widest column first to a legibility floor) so the over-wide column **word-wraps** instead of
clipping — the Comms & Coordination support ladders were losing FREQ / Departure / TOT when a
package sat on three radio channels. A table that already fits returns `None` (byte-identical
output, so every narrow table is unchanged). Alongside it: the `SupportPage` package FREQ/TOT
header line splits FREQ and TOT onto separate lines when the one-line form would overrun, and the
`ThreatIntelBriefPage` bullseye **cue lists** (drawn with the non-wrapping `text_runs`) truncate to
the pixels left on the line via `_fit_cues` (unidentified cards keep the count-withholding "…";
identified keep "+N"). Tests: `tests/missiongenerator/test_kneeboard_bluf.py` (table wraps/​leaves-fitting-untouched),
`tests/missiongenerator/test_threat_intel_kneeboard.py` (cue width truncation).

**Kneeboard de-duplication pass.** With every optional page enabled the deck printed the same
data several times; a single-home-per-datum pass fixes it, each change conditional on the
*other* page existing (so a deck with options off is byte-identical to before):
- **Weather** (temp / QNH / QFE / winds / clouds / sunrise-sunset) is dropped from the always-on
  **Mission Info** (`BriefingPage`, `omit_weather`) when the recon **Departure** page is generated
  for the flight (`_should_emit_departure`), which already carries the field-weather grid.
- The flight-plan fuel column: originally a Min-fuel column that was dropped when the Fuel Ladder
  page was enabled; since 2026-07-05 the ladder is **folded into the flight plan** (see the fuel
  ladder block below), so there is one home by construction — a `Fuel` column + a one-line RTB
  margin call-out on Mission Info, and no separate page.
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

**Fuel ladder — folded into the flight plan (2026-07-05).** The flight-plan table on Mission Info
carries a **`Fuel` column**: the **planned fuel remaining** at each RTB steerpoint
(`FlightWaypoint.fuel_planned`, the forward pass `WaypointGenerator._estimate_planned_fuel_for`
that subtracts each leg's burn from the starting load `flight.fuel × KG_TO_LBS − taxi`, topping
back up at a tanker `REFUEL` waypoint). It deliberately does **not** print the old Plan/Min/Margin
trio: the per-waypoint margin (Plan − Min) is **constant across the whole route by construction**
(start fuel − total burn − reserve, since the two figures are walked from opposite ends with the same
per-leg burn), and Min is just Plan minus that constant — so both repeated the same number on every
row. They collapse to a single **RTB margin** call-out under the table (`+N` spare, or an
amber `−N` "tank or divert" warning), computed as the worst-case `min(fuel_planned − min_fuel)` so a
tanker leg's reset is still caught (`FlightPlanBuilder._format_fuel` / `fuel_margin_line`).
Post-landing reference points (e.g. the bullseye, which carry a forward-burn `fuel` but no
min-to-RTB) get a blank cell. The burn model is approximate (it's the same estimate that drives
`min_fuel`), so treat the figures as planning numbers. **History:** this began as a standalone
`FuelLadderCard` page (gated `generate_fuel_ladder_kneeboard`, in-game ☑ VERIFIED 2026-06-26, H7 —
one of the three kneeboard ideas harvested from the campaign-doc study,
`414th-campaign-doc-ideas-harvest.md`); the back-to-basics pass exposed it as a near-empty page, so
per the user's call ("why can you not build the fuel table into the flight plan?") the page + the
setting were deleted and the column always rides in the flight plan. Model covered by
`tests/missiongenerator/test_fuel_ladder.py`; the column + margin semantics by
`tests/missiongenerator/test_flightplan_fuel_column.py`.

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

**Compact 3-4 page kneeboard deck — RETIRED (2026-07-05, the back-to-basics rework).** The compact
folding machinery (`compact_kneeboard`, `_compact_kneeboard_pages`, the `CombatIntelPage`/
`CommsCoordPage`/`FlexReferencePage` composites, `_draw_section_if_fits`, the adaptive flex page and
the fuel-ladder backfill) was the fork's biggest source of `kneeboard.py` churn against upstream and
the most fragile part of the deck. It is **deleted**; the pieces the squadron actually liked survive
on the stock full deck, which is now the only assembly path:

- Every deck opens on the **cover page** (§30 — op/turn/date, SITREP, shared-airframe index, phase/ROE
  band).
- Every flight's block leads with the **Brief Sheet** (§31 — the colour-coded one-pager), followed by
  the stock `BriefingPage` "Game Plan" (which keeps the **BLUF lines** — task/TOT, push words when code
  words are on, top threat) and the rest of the standard pages.
- The **Threat Intel Brief** page (`generate_threat_intel_kneeboard`) flipped its default to **ON** —
  the colour-coded per-system threat cards were a kept piece and no longer have a composite page to
  ride on.
- The other optional pages (target recon imagery, friendly packages + map, code words/brevity, fuel
  ladder) are unchanged and stay default OFF.

BLUF composition is covered by `tests/missiongenerator/test_kneeboard_bluf.py` (renamed from
`test_compact_kneeboard.py`, which also lost the composite-page tests). The old H9 checklist row is
superseded by this retirement.

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
  **A front anchor is never abandoned** (2026-07-09): `_offensive_roll` still lets OPFOR
  abandon a *rear* CP to free its fighters for offense, but a CP holding the FLOT is exempt
  — stripping the front in order to push forward is incoherent, and on a single-front
  theater the roll deleted the *only* CAP over the front. On Red Tide, Haina is the sole
  front anchor, carries the theater's highest threat-weighted round count (2 vs the rear
  fields' 1), and was abandoned on ~1 turn in 5 (turns 2, 8 and 9 of the first ten), leaving
  red's entire BARCAP layer 126–188 NM behind the FLOT around Berlin. Tests:
  `tests/test_objectivefinder_barcap.py`.
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

### Refuel stops budgeted into flight-plan timing (2026-07-01)

**Symptom (player report, screenshot of a DEAD flight's waypoint list).** A flight with a
pre-vul tanker stop had under three minutes between its `REFUEL` waypoint and the join — the
schedule budgeted **zero** time on the boom. The tanker's own plan already budgeted service time
per receiver (`4 min × flight size + 1`), but the receiver's timeline treated `REFUEL` as a plain
nav point, so a tanking flight was always late to the join/TOT. Worse, the package tanker's
on-station window (`patrol_start_time`) was anchored **post-vul only** (TOT + egress legs), so a
pre-vul receiver reached the track long before the tanker existed there.

**Fix — both sides of the rendezvous budget the same stop** (shared
`refuel_service_time(flight_size)` in `game/ato/refueltasking.py`):

- **Receiver dwell** — `FlightPlan.total_time_between_waypoints` adds `refuel_duration`
  (= the tanker's per-receiver budget) to any edge leaving a `REFUEL` waypoint. Because takeoff
  time and the chained waypoint ETAs sum this method per leg, everything before the tanker
  (takeoff included) shifts earlier and everything after keeps its time.
- **Hold push through the tanker** — `FormationFlightPlan.push_time` now follows the actual
  route from the hold to the join (nav legs + the pre-vul stop) instead of the straight
  hold→join line, so the flight departs the hold early enough to tank and still make the join.
- **Sim sync** — the fast-forward sim (`flightstate/inflight.py`) spends the planned stop on the
  `REFUEL` leg too, so simulated positions don't run minutes ahead of the DCS-written ETAs.
- **Tanker window opens pre-vul** — `PackageRefuelingFlightPlan.patrol_start_time` is
  `min(post-vul anchor, earliest pre-vul receiver arrival − 1.5 min)` (receiver arrival via its
  `chained_tot_for_waypoint(refuel_pre)`), and `patrol_duration` stretches by the early opening
  so `patrol_end_time` still covers the post-vul service.

Also fixed in passing: the stale `FormationAttackLayout.refuel_pre` comment ("at most one is
set" — `BOTH` tasking sets pre- *and* post-vul points).

Tests: `tests/ato/flightplans/test_refuel_timing.py` (dwell on the refuel edge, per-size service
time, push time with/without a pre-vul stop, tanker window post-vul-only vs early-open). Needs an
in-game sanity pass only in the sense that AI tanking pace varies; the schedule now budgets the
same time the tanker always reserved.

### Tanker tasking falls back to the fuel estimate (2026-07-08)

**Symptom (player report, F-4E-45MC kneeboard).** An F-4E OCA/Runway strike on Hamburg was
fragged with **no tanker** and a kneeboard RTB margin of **−4259 lb** ("short of getting home as
planned; tank or divert"). The theater could crew a tanker; the planner just never considered
one for this sortie.

**Root cause — the deficit and the tanker decision read different fuel sources.** The
kneeboard fuel ladder / RTB margin (§46, `waypointgenerator._estimate_planned_fuel_for`) falls
back to `AircraftType.estimated_fuel_consumption` when an airframe ships no hand-measured `fuel:`
block, so it *computes and prints* the deficit. But `FormationAttackBuilder._refuel_tasking`
(`game/ato/flightplans/formationattack.py`) read **only** the measured `unit_type.fuel_consumption`
and returned `RefuelTasking.NONE` the moment it was absent — so the whole strike family
(OCA/Runway, OCA/Aircraft, Strike, BAI, DEAD, SEAD/SEAD Sweep, Anti-ship, Armed Recon, Escort,
TARPS, Air Assault) never fragged a pre- or post-vul tanker for a no-`fuel:`-block airframe,
however long the leg. The `F-4E-45MC.yaml` (a Heatblur mod jet) has no `fuel:` block, so its
tanker decision was permanently blind while its ladder screamed.

**Fix — one source for both.** `_refuel_tasking` now reads
`fuel_consumption or estimated_fuel_consumption`, mirroring the ladder/bingo fallback: if we
trust the estimate enough to warn the player "you won't make it home," we trust it enough to
frag the tanker the theater can already crew. Deliberately narrow — `fuel_consumption` itself is
unchanged, so the in-flight fuel sim keeps using measured data only (no new blast radius, per
the `estimated_fuel_consumption` docstring's contract). The decision stays gated by
`can_auto_plan(FlightType.REFUELING)`, so it is a no-op when the campaign fields no tanker
(the −N lb margin is then a genuine "divert" situation), and helos / airframes with no fuel
capacity at all are still skipped. Short hops are unaffected — the estimate over a short route
resolves to `NONE`, exactly as measured data would. A hand-measured `fuel:` block for the
F-4E-45MC (needs in-game measurement) would give tighter numbers still, but is a separate
follow-up; this closes the *inconsistency* for every mod airframe at once.

Tests: `tests/ato/flightplans/test_refuel_tasking_estimate_fallback.py` (no-measured-fuel tanks
from the estimate; measured data still wins; no tanker squadron / helo / no-fuel-data stay
hands-off). Shares the pure decision coverage in `tests/ato/test_refuel_tasking.py`. Needs an
in-game pass (the F-4E OCA case now shows a pre/post-strike tanker + a non-negative RTB margin).

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
- New Game crash on an authored-but-empty `aircraft:` key (2026-07-01): a campaign-YAML
  squadron whose `aircraft:` key exists but has no entries parses as `None`, and
  `DefaultSquadronAssigner.find_squadron_for` iterated it —
  `TypeError: 'NoneType' object is not iterable` at game generation. *Northern Guardian* and
  *WRL Noisy Cricket (Redux)* both ship such squadrons, so New Game on either crashed (found
  by the campaign-phases `--engine --all` batch, which exercises the real generation pipeline
  for every campaign). `SquadronConfig.from_data` now treats it as `[]` — the existing "any
  aircraft compatible with the primary task" fallback — in
  `game/campaignloader/campaignairwingconfig.py`. Generic upstream-code fix on upstream
  campaigns (upstream-PR candidate). Test:
  `tests/test_campaignairwingconfig_empty.py::test_authored_empty_aircraft_key_reads_as_any`.

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

> **Rework complete (2026-06-27) + CSAR rescope (2026-07-03).** SCAR was repurposed from an
> armor-hunt task into the **RESCAP "Sandy"** rescue escort of the **Combat SAR package** (King +
> Jolly Green + Sandy). The old moving-HVT armor-hunt scenario *and* its auto-planner were
> **deleted** (detailed below). The 2026-07-03 rescope then **shelved the POW recovery raid**
> (capture is a campaign consequence, not a plannable mission — the held-POW model below stays)
> and **froze the AI-drama layer** (the Sandy auto-divert gets its one owed G23 re-fly,
> pass-or-delete; no further AI-choreography iteration). Design source of truth:
> `docs/dev/design/414th-csar-notes.md` (supersedes the eight earlier CSAR/SCAR notes).
>
> **Dormant SOF capture economy REMOVED (2026-07-01).** The unreachable remnant of the old loop —
> `FlightType.SOF` (the C-130 insert), the commander-capture reveal/refund + mis-ID penalty
> (`commit_scar_results`/`commit_sof_*`, the `scar_misid_penalty` setting), the stranded-team
> objectives (`game/scar_objectives.py`, `Coalition.pending_csars`), and the plugin's
> `sofTeams`/`SOFRESCUE` CASEVAC channel — is deleted. Nothing had triggered it since the armor-hunt
> plugin was removed. Save-compat tombstones: `PendingSofRescue` + `purge_legacy_sof_state` in
> `game/scar_rescue.py`, the no-tasking `DownedSofGroundObject` class, the `"SOF Insert"` →
> `TRANSPORT` legacy flight-type remap, and `Coalition.__setstate__` dropping `pending_csars`.
> Still live: the command-post fog (`scar_command_post_intel`), the persisted `captured_commander`
> reveal an old save may carry, and the whole POW loop below.

**The shipped feature.** `FlightType.SCAR` is the **Sandy** rescue-escort role in the Combat SAR
package — it no longer hunts armor. The retired armor-hunt scenario (the moving-HVT "find the real
one among look-alike decoys" chase) and its opt-in auto-planner were **removed on 2026-06-27**:
`game/missiongenerator/scarluadata.py`, the `scar` Lua plugin (`resources/plugins/scar/`, dropped
from `plugins.json`), `game/plugins/scar.py` + its `manager.py` registration, `PlanScarHunts` /
`PlanScar`, the `scar_autoplan*` settings, the `mission_data.scar_taskings` plumbing, and the
`test_scar_bridge.py` / `test_scar_autoplan.py` suites are all gone. (The "SOF Team" unit YAML
variants that once stood in for the POW body are kept as save-compat tombstones only — the POW
map objective that consumed them was shelved with the recovery raid, 2026-07-03.)

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
MAYDAY cue); the King smokes/marks/calls it so Sandy engages. **BLUE survivors only** (squadron
call 2026-07-01: red flies NO CSAR — `combat_sar_targets` seeding is blue-gated in
`theaterstate.py` and `_generate_combat_sar` never emits the `CombatSAR.red` Lua node, so a red
ejection registers no survivor and no BLUE snatch party ever spawns to race it; the plugin's
coalition-generic red path stays dormant capability). The party is now **several small,
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

**Safety cap + dead-reference cleanup (2026-07-09).** The snatch party is REAL infantry on
DCS's single scripting/sim thread, so `capturePartySize` / `captureTeams` are **hard-clamped at
load** (≤ `MAX_PARTY_SIZE` 12 infantry across ≤ `MAX_TEAMS` 4 teams, `env.warning` once when a
value is reined in). A cranked or stale-saved override can no longer pile enough units on to
freeze the mission — the motivating incident (2026-07-08) was a saved 40-strong / 4-team value
that spawned **80 soldiers across two ejections** on a heavy Red Tide (Germany Cold War) map and
hung the sim (the log stopped mid-`GetVec3`/`GetCoordinate` flood with **no crash dump** — the
signature of a scripting/sim-thread hang, not a CTD). Separately, the survivor ledger now **drops
dead references** so an attrited rescue stops generating MOOSE error traffic: `advanceCapture`
prunes killed teams out of `entry.party` each cycle (bounding the per-poll work as the party
dies) and reads every position through `firstAliveCoord` (a first-living-unit helper that never
calls `GetCoordinate` on a dead DCS object — a group that reports alive while its lead unit is
gone otherwise spammed the log every poll), and the main `tick` **reaps a downed pilot killed on
the ground** by finally assigning the designed-but-unused `dead` state (a pilot killed while
`down` used to linger in the ledger forever, polled every 5 s). The cap is exercised end-to-end
against the real plugin under Lua 5.1 in `tests/lua/test_combatsar_capture_cap.py` (combatsar is
MOOSE-heavy and not in the `DcsPluginHarness`, but the cap runs at file scope before any MOOSE
wiring, so a tiny sandbox drives it). The plugin.json labels now state both caps.

**Capture → held POW (Python; the raid is SHELVED, 2026-07-03; the model reworked 2026-07-06).**
`record_pow_captures` (`game/sim/missionresultsprocessor.py`) turns each capture into a
`PendingPowRecovery` (`game/pow_recovery.py`) on the survivor's coalition (persisted,
save-migrated), resolving the **holding enemy airfield at capture time**
(`resolve_holding_airfield`) and stamping the `captured_turn`. `commit_air_losses` spares a
captured pilot the KIA, and the capture now flips the aviator to **`PilotStatus.POW`**
(`pilot.capture()`) so the squadron stops scheduling them while captive (they leave
`active_pilots`). The POW resolves by: `surviving_pows` (from `Coalition.end_turn`) **frees**
(`repatriate()` → Active) a POW whose holding field is recaptured; otherwise the hold is a
**4-turn clock on a normal campaign but INDEFINITE when `vietnam_political_will` is on** (the §48
running sore drains until freed or the war ends). The **Homecoming** (`resolve_pows_at_game_end`,
from `process_win_loss`) repatriates all held blue POWs on a negotiated **win** and writes them
off on a withdrawal **loss**. Every write-off routes through `_write_off`, which **respects
`invulnerable_player_pilots`** (a player POW is repatriated, not killed). A held POW is surfaced
on the **SITREP band** (`Sitrep.pows_held` — name @ holding field + clock/"held") and the
**squadron roster status** (`SquadronDialog`); while held it **drains political will per turn**
(the Vietnam W1 `blue_pow_held_per_turn` feed). The §51 comms compromise it triggers is time-boxed
to `COMMS_COMPROMISE_TURNS` off `captured_turn`, so an indefinitely-held POW doesn't jam forever. The dedicated
recovery *raid* — the `CSAR` flight type + the dynamic `CapturedPilotGroundObject` map objective
+ `commit_pow_recoveries` — was **shelved in the 2026-07-03 rescope** (`game/pow_objectives.py`
deleted; the TGO class remains a save-compat tombstone; `purge_pow_objectives` sweeps
pre-rescope saves at turn init; a persisted `"CSAR"` flight degrades to TRANSPORT via
`_LEGACY_FLIGHT_TYPE_VALUES`). v1 fidelity gap unchanged: a held pilot isn't pulled from the
active roster.

**The Sandy kneeboard** is `ScarTaskPage` (`game/missiongenerator/kneeboard.py`) — role guidance
for holding with the King/Jolly, suppressing the threats around the survivor, and walking the
rescue helo in.

**Settings / state.** `scar_command_post_intel` (Campaign Doctrine; gates the command-post fog)
and `auto_combat_sar` (the AI standing alert). State globals: `combat_sar_captures`
(captures) and `combat_sar_rescues` (pilot-spared credit). **Tests:**
`tests/test_scar_command_post_fog.py` (the command-post intel fog),
`tests/test_scar_rescue.py` (the SOF save-compat tombstones + purge), plus the Combat SAR / POW
coverage in `tests/test_missionresultsprocessor.py`. The capture race +
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
idle, **non-player** Sandy within `sandyMaxRangeNm` (default 30 NM) and **pushes a route** to the
survivor — a transit waypoint from the Sandy's current position to a hold waypoint over the survivor
(450 m above ground) carrying `TaskOrbitCircleAtVec2` (the hold anchor) plus an
`EnRouteTaskEngageTargetsInZone` waypoint task (actively hunts `"Ground Units"` within
`sandyEngageRadiusNm`, default 3 NM, around the survivor). **Reworked 2026-07-02** from the original
`SetTask(TaskCombo{engage, orbit})` after the Trail 2 flown session reproduced the fail signature
(divert message, no movement): `EngageTargetsInZone` is an *en-route* task, which the DCS controller
silently rejects inside a main-task ComboTask — en-route tasks only execute from a waypoint task
list, and the transit leg physically flies the Sandy there (the stock MOOSE transit-then-orbit
pattern). `configure_scar`'s weapons-free ROE (unchanged) does the actual engaging once
retasked. Commits at most one Sandy per survivor (`busySandy`), retries every `POLL` (5s) until one
frees up, and releases it once the survivor is rescued/captured/dead — the release routes the Sandy
back to the station it was diverted from (`entry.sandyReturn`) and holds it there, since the divert
replaced the group's planned route and a bare `ClearTasks()` would leave it flying a straight line.
Two plugin options: `sandyMaxRangeNm`, `sandyEngageRadiusNm`
(imperial-unit options since 2026-07-01; the whole Combat SAR option set is now ft / NM / kts —
`pickupRangeFt`/`pickupAGLFt`/`pickupSpeedKts`/`homeRangeNm`/`captureSpawnDistanceNm`/`captureRangeFt`
— converted to metric at read time in the Lua, defaults equivalent to the old metric values).
Python bucketing/emission is unit-tested
(`tests/missiongenerator/test_combat_sar_sandy_luadata.py`); the routed-divert Lua needs a re-fly
(checklist G23 — the pre-rework dispatch was flown 2026-07-02 and confirmed not to move the flight).
**Freeze policy (2026-07-03 rescope):** G23's re-fly is pass-or-delete — if the route-push rework
flies, the divert stays as-is, frozen; if it fails again the divert is removed rather than reworked
a third time. Either way, no further AI-rescue choreography is added.

### SOF insert generation fixes (2026-06-22)

> **Historical.** The SOF insert itself was removed with the dormant capture economy (2026-07-01,
> §15). The two fixes below outlived it in generalized form: the runway fallback applies to any
> non-helo flight, and the EW deny-list still covers the Combat SAR King (`FlightType.SOF` is
> simply no longer in the non-EW set).

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

**Status:** Built + rescue scoring verified (G8/G9/G11/G13); G10 partial. **Default ON since the
2026-07-03 CSAR rescope** (`auto_combat_sar` default True for new campaigns; existing saves keep
their stored choice) — rescue is a normal, standing task per the locked vision. Python plans +
scores; the plugin's **survivor ledger** (Lua) executes. Design source of truth:
[`docs/dev/design/414th-csar-notes.md`](design/414th-csar-notes.md).

**Testing aids (2026-07-09):** the enemy snatch-party spawn default dropped **2 NM → 0.75 NM** so a
capture can actually complete in a mission window (the old 2 NM was an ~11-min march ⇒ captures
~never fired). Plus two **default-OFF** test toggles (Campaign Management → HQ Automation) that emit
scalar flags on `dcsRetribution.CombatSAR` for the plugin to honor: `combat_sar_test_force_capture`
(every ejection → a fast guaranteed **capture → POW**, unlocking the §51 capture-gated comms jam —
the reliable way to exercise **G28 + S4**) and `combat_sar_test_easy_rescue` (capture off + forgiving
pickup/delivery — exercises **G10 King / G23 Sandy / the pickup loop**). Leave OFF for normal play.

The bespoke pilot-rescue flight task. A **CH-47** orbits near the FLOT as the rescuer; a
**C-130** flies the overhead **HC-130 "King"** on-scene-command orbit. When a pilot (human or
AI) ejects in the area, the ledger spawns the downed pilot with red smoke and a friendly helo —
player-flown or AI — flies in, lands, and delivers them to any friendly field/FARP; the campaign
**spares that aviator** at debrief (the airframe is still lost; the experienced pilot returns to
the squadron).

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
- **On-demand AI rescue (2026-07-06 rework — replaced the standing orbit).** The auto-fragged
  COMBAT_SAR orbit (`PlanCombatSar` / `PlanCombatSarSupport`) is **removed** — the orbiting helo
  never reliably flew the pickup (the runtime commandeered an airborne, already-routed group, which
  RTB'd instead of rescuing; checklist G21, a flown finding). Now `Settings.auto_combat_sar` (HQ
  automation, **default ON**) drives an **on-demand spawn**, sourced parked-first / clone-fallback
  **only when no player CSAR/SCAR package is fragged**:
  1. **A real rescue helo parked cold on the ramp** — Retribution already spawns each squadron's
     untasked airframes (`_spawn_unused_for` → `create_idle_aircraft`, uncontrolled + **in the
     `UnitMap`**); `spawn_combat_sar_templates` collects the BLUE CSAR-capable ones
     (`mission_data.parked_rescue_helos`, emitted as `parkedHelos`). The plugin's
     `commandeerParkedHelo` picks the nearest, `StartUncontrolled`-launches it, and OPSTRANSPORTs the
     pickup — a **tracked** airframe (its loss is recorded). This is the user's "use the C-130s/A-10s
     already on the ramp" insight applied to the helo.
  2. **A cold late-activation clone template** (the QRA `spawn_intercept_templates` pattern), emitted
     as `heloTemplate` + `farp`, as the **fallback** when the ramp is bare (`perf_disable_untasked_
     blufor_aircraft` / fully-tasked wing). SPAWN-cloned; the clone is untracked.

  Both go straight into the OPSTRANSPORT pickup (the clone-into-mission path that works); a *parked*
  start is the fix for the retired commandeer of an *airborne* helo. A player-fragged package ⟹
  `autoSpawn=false`, no AI spawn (the package + ledger handle it). The helo needs no loadout (it does
  OPSTRANSPORT); on-demand **Sandy** (needs an armed payload — parked untasked + cold-template
  airframes are both `maintask=None`/clean-wing) + **King** (needs the TACAN-beacon setup) launches +
  multi-survivor chaining are the §21 **v2**. **The AI rescue runs in the plugin's own survivor ledger, not
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
- **Delivery-field resolution (2026-07-03, flown Yankee Station).** The delivery airbase is resolved
  from `cfg.farp` via MOOSE `AIRBASE:FindByName`; Python passes the King's departure *control-point
  display name* (`rescue_flights[0].departure.airfield_name`), which matches a real airfield's DCS
  name but **not** a generated FARP — whose DCS object is `"<CP> FARP 0"`
  (`tgogenerator.create_helipad`). So a **FARP-based King** (the Vietnam FOB case) logged
  `combatsar: AI dispatch - FARP '<CP>' not found` on every ejection and delivered nothing. Fixed:
  `dispatchAIRescue` now falls back to `nearestFriendlyAirbaseObject(entry.side, survivorCoord)` —
  the closest field MOOSE *can* resolve — whenever the configured name misses; airbase-based Kings
  keep their exact departure field, only the previously-dead FARP path changes. Matches the "deliver
  to ANY friendly field" contract. Needs a re-fly to confirm delivery completes (G21/G23).
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
  Combat SAR King C-130J-30 group names so the King flies clean while a co-present JAMMING C-130J
  keeps its EW systems (see §15 EW de-conflict).

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
| Flight plan | `game/ato/flightplans/combatsar.py` (forward FLOT hold) — a **player-planned** COMBAT_SAR flight only; the auto-fragged orbit is retired |
| Planning | **Player-plannable** off the FLOT (`game/theater/frontline.py` `mission_types` → COMBAT_SAR/SCAR). The standing-orbit auto-frag (`PlanCombatSar`/`PlanCombatSarSupport`/`combat_sar_targets`) was **deleted** in the 2026-07-06 on-demand rework |
| On-demand rescue | **Parked-first, clone-fallback.** `aircraftgenerator.py` — `_spawn_unused_for` collects BLUE CSAR-capable **parked untasked helos** (`mission_data.parked_rescue_helos`, real + in the `UnitMap` → tracked); `spawn_combat_sar_templates` folds them into `CombatSarTemplates` alongside a cold clone template (`create_combat_sar_template` in `flightgroupspawner.py`, the fallback). Plugin `commandeerParkedHelo` + `StartUncontrolled` launches a parked helo; falls back to SPAWN-cloning `heloTemplate`. Tests: `tests/missiongenerator/test_combat_sar_templates.py` |
| Setting | `game/settings/settings.py` — `auto_combat_sar` (now drives the on-demand spawn, not an orbit) |
| King beacon | `game/missiongenerator/aircraft/flightdata.py` (`CombatSarKingBeacon`, TACAN-only), `flightgroupconfigurator.py` (`register_combat_sar_king`) |
| Emit data | `game/missiongenerator/luagenerator.py` — `_generate_combat_sar` (rescueHelos / kings / pilotTemplate / **`autoSpawn`** + **`parkedHelos`** (preferred) + `heloTemplate`/`farp` (fallback) when auto-spawning). The pilot template uses `survivor_unit_type` — the first faction INFANTRY-class unit whose id names a *person* (soldier/infantry/paratrooper/insurgent), vanilla `Soldier M4` fallback — because the INFANTRY class also carries crew-served weapons and OIR's first pick was the 2B11, rendering every downed pilot as a mortar tube (2026-07-06 flown finding). Tests: `tests/missiongenerator/test_combat_sar_sandy_luadata.py` (gating + parked/clone emit + survivor) |
| Kneeboard | `game/missiongenerator/kneeboard.py` — `CombatSarTaskPage` |
| Scoring (Lua) | `resources/plugins/base/dcs_retribution.lua` (`combat_sar_rescues` global + `write_state`), `resources/plugins/combatsar/combatsar-config.lua` (CSAR bridge + `OnAfterBoarded`/`OnAfterRescued`) |
| Scoring (Py) | `game/debriefing.py` (`StateData.combat_sar_rescues`), `game/sim/missionresultsprocessor.py` (`commit_air_losses` spares rescued pilots) |
| Tests | `tests/test_combat_sar_scoring.py` |

### Gotchas

- **The SOF-recovery CASEVAC channel is gone** (removed 2026-07-01 with the dormant capture
  economy, §15): the ledger tracks ejected pilots only; there is no `sofTeams` emission,
  `SOFRESCUE` routing, or `combat_sar_sof_recoveries` global any more.
- **No double ejection-handling.** The survivor ledger is the only ejection listener (CTLD's
  handler is commented out, `CTLD.lua:8254`). The F10 "CSAR" menu shows on any
  helo player, but pickups are gated to the Combat SAR rescue set.
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
| Tests | `tests/missiongenerator/test_country_assigner.py` (no-op, mixed-nation, cross-side collision, mirror-match distinct primaries, unknown-id skip, belligerent ids, instance identity) |

### Gotchas / deferred

- **Ground units stay on the faction country.** TGOs, statics, convoys, and the player helo group
  still spawn under `p_country`/`e_country` (`tgogenerator.py`, etc.) — harmless, since ground
  units have no nation voice comms. Only air units carry the per-squadron nation today.
- **Review hardening (upstream PR #854 feedback).** Four edge-case fixes carried back from the
  upstream carve review: (1) **mirror match** — when both factions share a country id, `primary_red`
  gets its *own* instance (not the interned blue one), so each side registers a distinct object under
  the shared id instead of adding one object to both coalitions (an unloadable `.miz`); (2)
  **unknown country id** — a squadron country pydcs doesn't know (version drop / uninstalled mod) is
  skipped with a debug log and falls back to the faction country, never a `KeyError` that aborts
  generation; (3) **`Game.neutral_country`** now excludes belligerents **by country id** (pydcs
  `Country` has identity equality, so the old instance-set membership never matched) and spans every
  squadron's country, so a CJTF side fielding a Swiss/UN squadron can't also hand that nation to the
  neutral coalition; (4) `for_squadron`'s faction-primary fallback logs at debug like every other
  skip. Plus perf: the squadron `faker` is resolved once per recruit batch, not once per pilot, and
  the pilot-name locale table is cross-checked against pydcs in a test so a stale key fails CI.
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

### The 2026-07-05 New Game wizard + section pass

A full audit of every New Game page and setting (user call: "complete reorder — there is legacy
we are overlooking") landed a second IA pass on both surfaces:

- **Wizard flow**: the old *Generator settings* page's world-shaping options — the four no-carrier/
  no-navy checkboxes, "Squadrons start at full capacity", and both budget sliders — moved onto the
  **Theater** page as a "Forces & Budget" group (re-seeded from each campaign on select, exactly as
  before; field names unchanged so `accept()` is untouched), and the remainder became a dedicated
  **Mods** page: three groups (Aircraft modules / Asset packs / Air defense), alphabetized, in two
  columns. The wizard is now Intro → Theater (world) → Factions → Mods → Campaign options → Finish.
- **Legacy sweep**: the Intro "Vietnam" card no longer advertises the deleted Khe Sanh campaign
  (now 1968 Yankee Station / Velvet Thunder / Red Flag 81-2); "Advanced IADS **(WIP)**" is relabeled
  **(MANTIS)** with a real tooltip (it has been the flown default engine since June); the
  Campaign-options subtitle no longer tells players to overwrite `Default.zip` (the save path writes
  `Default.json`); `TIME_PERIODS` is chronologically sorted (the stranded "Gulf War – Fall [1990]"
  and the unsorted scenario tail fixed) with the default selected **by name** instead of positional
  index 21; the dead `SettingNames.py` (zero imports) is deleted; the OH-6 pack checkbox is
  relabeled "ground objects" (the OH-6A helicopter left every faction 2026-06-30 — the toggle now
  gates only the pack's `vap_*` ground objects); the Theater page's docs links lead with the 414th
  wiki. The mod list stays the curated 16-of-~50 `ModSettings` (the hidden rest are deliberately
  retired/scrubbed content) — now stated in the Mods page docstring so the subset is a decision,
  not an accident.
- **Section regroup** (FIELD_LAYOUT-only, no field moved, no save impact): Campaign Management's
  three one-field orphan sections merged into a **"Campaign features"** opener
  (phases/clock/carrier-ops) and "Economy & reserves" renamed **"Commander economy"**; Mission
  Generation's "World & systems" split out a **"Battlefield life"** section (base battle damage,
  artillery harassment, mobile missile relocation); Air Doctrine's 13-field "Threat & engagement
  distances" wall split into **Engagement ranges / SEAD standoff / Support-orbit standoff / Mission
  range limits**. Still 7 pages, all 174 fields accounted for (walk-verified).

### Dependency greying + detail summarisation (2026-07-10, the settings UI audit follow-up)

The metadata-driven renderer gained the **dependent-setting greying** the §16 QOL audit deferred, plus
a declutter pass:

- **`enabled_when` dependency greying.** `OptionDescription` gained a keyword-only
  `enabled_when: (master_field, enabled_value)` (a bare `"master"` is shorthand for
  `("master", True)`; normalized by `normalize_enabled_when`). Keyword-only so adding it to the frozen
  base never disturbed the subclasses' positional fields (`invert`, `min`/`max`, `choices`). Every
  `*_option` factory threads it. `AutoSettingsLayout` now stores each field's **label** (not just its
  control) and, after building a section, wires every master's change signal to `refresh_enabled_states`
  — which greys a child's **control + label** whenever `settings.<master> != enabled_value`. All ~21
  wired pairs are same-section, so greying is live; the initial pass sets state on open, and
  `update_from_settings` re-applies it after a difficulty preset. Wired: the four `red_intent_*` ←
  `red_intent`, the `coin_*` family ← `coin_insurgency`, `qra_defense_depth_nm` ← `qra_forward_defense`,
  `motorpool_spawn_cap` ← `motorpool_enabled`, `comms_jam_requires_capture` ← `enemy_comms_jamming`,
  `concealed_enemy_forces` ← `recon_intel_fog`, `perf_culling_distance` ← `perf_culling`,
  `perf_smoke_spacing` ← `perf_smoke_gen`, `dynamic_slots_hot` ← `dynamic_slots`,
  `supercarrier_deck_crew` ← `supercarrier`, the two squadron-limit knobs ← `enable_squadron_pilot_limits`,
  `vietnam_commitment_ceiling` ← `vietnam_political_will`, and the **inverse**
  `default_front_line_stance` ← `("automate_front_line_stance", False)` (editable only when automation
  is off). A guard test (`tests/test_settings_dependencies.py`) fails CI if any `enabled_when` master
  isn't a real setting, plus offscreen-Qt tests prove a child greys/ungreys live with its master.
- **Detail summarisation.** A `detail` longer than `INLINE_DETAIL_MAX` (150) now renders only its first
  sentence inline (`_summary_line`) with the **full text on hover** (the previously near-dead `tooltip`
  field), so the dense pages stop reading as walls of text; short details are unchanged.

### UI audit bug fixes (2026-07-10)

The same audit surfaced correctness defects across the Qt UI + web client, fixed alongside: the
end-of-campaign dialog branched on the enum member `TurnState.WIN` (always truthy) so a **defeat showed
"Victory!"** (`QLiberationWindow.onEndGame`); the Air Wing **player-slots caption was inverted** for a
valid blue+flyable squadron (`AirWingConfigurationDialog`); every auxiliary window shared one
`self.dialog` reference so opening a second could **garbage-collect the first** (distinct attributes
now); the repair routine **mutated the list it iterated** and skipped nearby wrecks (`QGroundObjectMenu`,
iterate a copy); the web **TGO markers keyed by `tgo.name`** (not unique) → key by `tgo.id`
(`TgosLayer`); Help/About/repo/**Releases links pointed at upstream** instead of the 414th fork
(`uiconstants` + About); and a dead `EmitterHighlightToggle` component + duplicate `.air-defense-ring-hit`
/ unused `.ml-collapse` CSS were removed. The full 56-finding audit is tracked separately.

### Web map: discoverability + a shared palette (2026-07-10, audit tracks 3+4)

The web client's overlays each hardcoded their own colours (so "red" meant six things and two dashed
circles read alike), and the map's core planning actions were invisible right-clicks with no affordance.

- **Shared semantic palette.** `client/src/theme/mapColors.ts` is the single source of truth — named
  tokens (`friendly`/`enemy`/`flot`, `suspected`/`offLimits`/`weaponsFree`, `supplyOk`…`supplyCritical`,
  `route*`). The overlays (threat zones, front line, supply layer + routes, restricted zones, the
  concealed TGO + the ROE tooltip) import from it instead of inline hexes. Two deliberate reconciliations:
  the **concealed "suspected activity" circle moved off red onto amber** so it no longer looks like the
  red ROE off-limits circle (finding #2), and the near-invisible navy **friendly supply route was lifted
  to a legible blue** (finding #10).
- **A map legend.** `components/legend/MapLegend` — a compact, collapsible bottom-right key decoding the
  allegiance / ROE / supply / suspected-activity colours + shapes (dark-panel styled, clears the other
  corners).
- **Right-click discoverability.** The interactive vectors (front line, supply route) and the suspected-
  activity circle now carry a **`cursor: pointer`** (via a `.map-interactive` Leaflet class) and a **hover
  hint** ("Right-click: plan a mission here" / "frag interdiction"; TGO/tooltip gets "Left-click: intel ·
  Right-click: plan a package") so the otherwise-hidden fragging actions are findable. Client-only;
  type-checked (`tsc`) + the `FrontLine` test mock extended; the full `react-scripts` build/test runs in
  CI. Deferred: a full right-click *context menu* and theming the light Leaflet tooltips.

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

(The cover briefly also hosted the friendly-package list in the retired compact mode; with the
2026-07-05 back-to-basics rework the list lives only on its standalone `FriendlyPackagesPage`, gated by
`generate_all_packages_kneeboard`.)

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

Every flight's block leads with the **Brief Sheet** (`BriefSheetPage`), a single scannable page modelled
on the squadron's printed **Appendix A** one-pager (the Red Tide briefing handbook, `docs/wiki/`). Since
the 2026-07-05 back-to-basics rework it fronts the **full deck**: the page you open to first is a
*summary*, with the stock `BriefingPage` "Game Plan" (steerpoint table + BLUF) and the detail pages
behind it.

**Auto-fill (`KneeboardGenerator._build_brief_sheet_data`).** The page is a pure renderer of a
`BriefSheetData`; the generator pulls each field from data it already holds (the BLUF pattern):

- **Route** — `_brief_route` walks `flight.waypoints`, mapping types to `HOLD/JOIN/IP/TGT/EGRESS` and
  carrying each point's **steerpoint number** (the waypoint index, matching the flight-plan `#`
  column) so the pilot can dial it up; the full steerpoint table follows on the `BriefingPage`.
- **Loadout** — `_brief_loadout` summarises the lead jet's generated pylons (`units[0].pylons` → `Weapon`)
  to the *ordnance*: counts by type, strips rack multipliers (`2xGBU-12` → `GBU-12`), collapses the TGP
  and HTS pods to `TGP`/`HTS`, and drops ECM / clean / unresolved stations.
- **Threats** — SAM from the threat cards (`_brief_sam_threats`, top live systems condensed); **air** from
  the enemy faction's fighters (`_brief_air_threats`, `faction.aircraft` filtered by
  `capable_of(BARCAP)`), kept loose to respect fog. **Game plan** = the most-lethal system's defeat note.
- The rest re-surface existing data: TOT, push/success/abort code words, bullseye, bingo/joker, divert,
  comms (`self.awacs/tankers` + package freq), fields (RWY/ATC/TCN via `_brief_fields`), WX
  (`_brief_weather`: departure-field QNH — temperature-corrected via `_airfield_elevation_m`, the same
  lookup the full deck's weather block and recon ATIS use — QFE when the elevation is known, + surface
  wind; best-effort, empty on any missing source), laser codes
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
JAM amber), so the whole deck reads as one product — the threat cards now live on the standalone
Threat Intel Brief page (default ON) and the code words on the optional Comms & Brevity card. The
multi-column comm-ladder/AWACS/tanker tables stay as plain `tabulate` reference tables (colouring
cells is disproportionate).

### Files & tests

| Area | Path |
|---|---|
| Page + data + helpers | `game/missiongenerator/kneeboard.py` (`BriefSheetPage`, `BriefSheetData`, `_build_brief_sheet_data`, `_brief_*`, `KneeboardPageWriter.text_runs` + `col_*` palette) |
| Tests | `tests/missiongenerator/test_brief_sheet.py` (route/loadout/threats/mission helpers, render, end-to-end data build) |

### Gotchas / deferred

- **Complements, no longer replaces, the `BriefingPage`.** Since the compact deck's retirement the
  Brief Sheet is an *additional* lead page; the stock `BriefingPage` + `_bluf_lines` follow it in
  every deck.
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
on a 5 s poll; when the lead unit closes inside the release range (default 3 NM — retuned 2026-07-01 from
8 NM so the carpet lands with the bomber nearly overhead, matching the ~2.5–3 NM ballistic forward throw
from ~30k ft, instead of firing a full minute early), it fires a **one-shot carpet**: a box of
`trigger.action.explosion` impacts oriented along the bomber's **bearing to the target** (its run-in), rows
stepping along-track with a small delay so it visibly walks, columns spreading it cross-track, with
per-impact jitter. Carpet length/width/per-blast power/release-range are plugin `specificOptions`
(**imperial-unit options since 2026-07-01**; defaults 6,000×1,500 ft, 660 lb TNT, 3 NM — the Lua converts
to metric at read time). `pcall`-guarded throughout; inert with no `VietnamOps` data, so non-Vietnam
missions never load any of it.

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
  (default 15,000 ft AGL), it counts alive **opposing** AAA guns within horizontal range (default 2.5 NM,
  capped at 3 for density) and, if any, spawns barrage bursts near the aircraft at its altitude.
- **Predictability.** A per-aircraft factor ramps up while heading (±8°) and altitude (±40 m) hold steady and
  drops fast on a jink. The barrage **miss distance** lerps from loose (1,000 ft, jinking) to tight (500 ft,
  predictable); a *sustained* predictable run (factor > 0.85) also occasionally (30 %/tick) draws one **close
  "tracking" round** (tighter miss, ×1.5 power) — the modest bite that punishes straight-and-level flight.

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

### Gotchas / deferred — in-game pass ☑ VERIFIED 2026-07-01 (checklist L2): 2nd softening flown, user pass "light but fairer"

- **Lethality softened twice; re-fly owed.** The 2026-06-28 audience pass ("too accurate but working very
  well") read as a hard-kill threat rather than the intended mostly-visual pressure. The lever is the close
  **"tracking" round**. Two tuning passes since:
  - **2026-06-28:** `MIN_MISS` 70→110 m, tracking `miss ×0.35→×0.55` / `blast ×2.5→×2.0` and rarer
    (`factor > 0.66→0.8`), `BLAST` 8→6.
  - **2026-07-01 (L2):** the remaining lethality was the tracking round firing **every 2.5 s tick** once a jet
    held a steady line ~10 s. Now: base misses widened `MIN_MISS` 110→**150** / `MAX_MISS` 250→**320** m, and
    the tracking round is **occasional** — gated behind a sustained steady run (`factor > 0.85`) **and** a
    per-tick probability (`TRACKING_CHANCE = 0.3`) — and softened (`miss ×0.55→×0.75`, `blast ×2.0→×1.5`).
  Both passes changed `vietnamops-config.lua` **and** the matched `plugin.json` defaults. **The 2026-07-01
  re-fly (Yankee Station, session `intelligent-dubinsky`) confirmed the feel** — user pass: bursts "light but
  fairer", no hard-kill (the mission's player loss was a MiG gun kill, not flak) → `☑ VERIFIED`. If the
  gauntlet now reads *too* light, `flakBurstPower` / miss distances / range remain the campaign-side knobs.
- **Imperial-unit options (2026-07-01).** All flak options are now authored in imperial units and the
  mnemonics were renamed (`flakRangeNm` 2.5 NM / `flakCeilingFt` 15,000 ft / `flakMinMissFt` 500 ft /
  `flakMaxMissFt` 1,000 ft / `flakBurstPower` 6); the Lua converts to metric at read time. The rename also
  deliberately **flushes stale per-campaign saved options** — the L2 config-mismatch finding (a flown session
  still reading pre-softening `110/250/8` + `ceiling 5000`) can't recur, because the old metric keys are
  simply ignored and the softened imperial defaults seed fresh.
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
  **opposing** ground target within gun range. Because ships sit offshore and the range gate is ~10 NM, this
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
- **Gun reach is a selection gate, not a DCS truth.** `ngfsRangeNm` (default 10 NM; imperial-unit options
  since 2026-07-01) picks the ship/target; the actual round only impacts if the DCS gun can range it. Tune to
  the ship types in play during the pass (a 5″ destroyer ranges ~9 NM; the New Jersey's 16″ far more).
- **Escort ships:** tasking a gun ship `FireAtPoint` can pull an *escort* off its station. Fine for a
  dedicated NGFS ship; watch it on a screening destroyer.
- **Deferred:** JTAC auto-lase → auto fire-mission (reading CTLD's laser target couples to CTLD internals);
  the F10 marker call + auto bombardment cover the capability for v1. "Fire on my position" (needs per-group
  menus) also deferred in favour of the marker call.

---

## §35 — Convoy interdiction (Steel Tiger) (Vietnam Ops suite)

The fourth **Vietnam Ops suite** feature: a moving enemy supply column on the road behind the FLOT — the
Ho Chi Minh Trail / Operation Steel Tiger — surfaced to the player through Armed Recon.

### How it works — a *real* convoy in the force model (reworked 2026-07-01)

**The problem with the original.** v1 emitted a corridor and the `vietnamops` plugin spawned a vanilla truck
column at runtime (`coalition.addGroup`). Those trucks existed **only inside the generated `.miz`** —
Retribution's force model and debrief never knew about them (their names weren't in the `UnitMap`), so
killing the convoy **cost the enemy nothing** and the loss was never recorded. That is exactly a "free,
non-existent unit": a target with no consequence. A respawn loop made it worse (unbounded free trucks).

**The fix: use the engine's real convoy system.** Retribution already models convoys as first-class,
tracked objects — `coalition.transfers.convoys` carry **real ground units** between control points, spawn as
road-moving `VehicleGroup`s (`ConvoyGenerator`), are already **Armed-Recon / BAI objectives**
(`ObjectiveFinder.convoys`), and their destruction is recorded (`Debriefing.dead_ground_units` →
`enemy_convoy`) so the transferred units **never arrive**. So convoy interdiction no longer *invents* a
convoy — it **ensures a real one is flowing on the trail**:

- **`ensure_enemy_trail_convoy` (`game/fourteenth/vietnam_convoy.py`)** runs **once per turn** from
  `Game.finish_turn` (after the AI's own transfer processing, so it's idempotent — it does nothing if the
  opfor already has a convoy travelling). When `vietnam_convoy_interdiction` is on it:
  - picks the road **corridor nearest the front** on the real control-point graph — a rear opfor base with
    spare armour (`_pick_trail_corridor`) feeding the road-connected opfor base nearest the FLOT (the end
    nearer the front is the destination; opfor→friendly roads are the contested front and are skipped);
  - **skims a few real rear units** off the source base (`_skim_units`, capped at `MAX_CONVOY_UNITS` = 10 and
    never more than half the base's armour, so a source is never gutted);
  - creates a real `TransferOrder` via `coalition.transfers.new_transfer`, which **debits the units from the
    source base** (`commit_losses`) and — on a road first-leg — spawns a real, tracked `Convoy`.
- **Result:** interdicting the trail now **denies the enemy real reinforcements** (kill the convoy and those
  units never reach the line; let it through and they do), and the kill is recorded natively as an
  `enemy_convoy` loss. It is genuine force planning, not a cosmetic effect.
- **Fully guarded / no-op safe:** no front, no rear units, no road corridor, or the concurrent-convoy budget
  already full ⇒ it does nothing, and the engine's organic convoys still serve as targets. **The `vietnamops`
  plugin has no convoy runtime at all** now — the emitter (`_populate_convoy_interdiction`) and the Lua convoy
  section are deleted, and the convoy `specificOptions` are removed.

**More units, more concurrent convoys, spread across distinct roads (2026-07-03 rework).** A flown Trail 2
session found `MAX_CONVOY_UNITS` = 4 and the one-convoy rule thin — a single 3-vehicle column was the whole
hunt. The driver now keeps a **concurrent budget** (`BASE_MAX_CONVOYS` = 2, `SURGE_MAX_CONVOYS` = 3 under a
W6 `trail_surge` ≥ 2.0 — up from the old 1/2) instead of a single "is one already flowing" check. Filling
that budget isn't "spawn N more on the same road": `_pick_trail_corridor` gained an `exclude_sources`
parameter, and `ensure_enemy_trail_convoy` walks it in a loop, excluding each corridor's source as it's
committed, so **concurrent convoys prefer distinct roads** — several Vietnam campaigns actually have more
than one opfor-opfor corridor to offer (Yankee Station / Steel Tiger's full Ho Chi Minh Trail network of 8
legs, Khe Sanh's two rear feeders — Kobuleti→Senaki and Sukhumi→Senaki, Red Flag 81-2's several
aggressor-hub corridors). A campaign with only one qualifying road (or no distinct second source) simply
stays capped at one convoy that call, exactly as before the rework — never stacks a second column onto the
one road in use.

**The real gate wasn't the cap — it was an empty rear economy (same-day follow-up).** A headless engine
probe across the 4 land Vietnam campaigns found every rear opfor CP's `Base.armor` at **zero at turn 0** —
it's the coalition's turn-by-turn production/income stock, not a static garrison, so a fresh campaign's
trail was never actually gated by `MAX_CONVOY_UNITS`; it was gated by how little the rear base had
*accumulated* by turn 1. `_seed_trail_source` now tops a picked source up to a standing stock (2× a convoy
load, same bound as the pre-existing COIN ratline: "relocate, never grow") before every skim, sourced from
the coalition's real ground roster (`Faction.frontline_units` — e.g. the PT-76/ZU-23/S-60/MT-LB actually
seen in the probe below) rather than the tight COIN insurgent whitelist. Framed as **external logistics
support** (matériel from China/the USSR, not local production) — the historically accurate character of the
Ho Chi Minh Trail specifically. `MAX_CONVOY_UNITS` was also raised **6 → 10** now that it's the real
constraint rather than a number the source stock immediately clamped away. **Verified with a real engine
load** (turn 1, `ensure_enemy_trail_convoy` called directly): Yankee Station spawned 2 convoys of 10 units
each on 2 distinct roads (FOB Tchepone→Gudauta, FOB Ky Son→Sukhumi-Babushara — 20 vehicles total vs. the old
3-vehicle single column); Khe Sanh spawned 2 convoys of 10 on its 2 rear feeders
(Sukhumi-Babushara→Senaki-Kolkhi, Kobuleti→Senaki-Kolkhi).

**Velvet Thunder has no `supply_routes` block at all** (its theater is the Marianas island chain —
Guam/Rota/Tinian/Saipan — with no roads between the separate islands a truck convoy could physically
drive), so `vietnam_convoy_interdiction: true` there is a documented no-op regardless of the seeding rework
(no corridor is ever picked); the toggle should probably come off that campaign's settings, or the feature
needs an island-appropriate reinterpretation (a naval convoy?) — flagged as a follow-up, not fixed here.

**Right-click planning (added per playtest).** Rather than hunting for the corridor, the player
**right-clicks an enemy supply route** on the map to frag the interdiction package:
`SupplyRoute.tsx`'s `contextmenu` on the wide invisible hit-line → `POST /qt/create-package/supply-route/{route_id}`
→ `interdiction_target_for_route_id` (`game/server/supplyroutes/models.py`) resolves the route id — which now
encodes both CP ids as `"<cp_a_id>:<cp_b_id>"` — to the **enemy end** (preferring the contested CP), and the
Qt new-package dialog opens there with the add-flight dialog auto-opened and **Armed Recon pre-selected**. A
friendly (all-blue) route resolves to nothing and 404s. Still an Armed Recon frag — just discoverable on the
route instead of requiring the player to know where to look.

**Armed Recon is an area search — "look in the area and find them" (2026-07-05, restored).** A prior
playtest pass (#406) had replaced the classic single target waypoint with a **road-polyline sweep**
(SEARCH START / MID / END down `cp.convoy_routes`, ordered away from ingress). The 414th call reverted it:
marching a specific road wasn't a *look-in-the-area* search, and the runtime engage zone is already huge —
`armedreconingress.py` anchors an `EngageTargetsInZone` of radius `armed_recon_engagement_range_distance`
(**default 10 NM ≈ 18.5 km**), so a **single** area waypoint already blankets the whole corridor. So
`ArmedReconFlightPlan`'s builder (`game/ato/flightplans/armedrecon.py`) is back to the stock single
`armed_recon_area` overflight of the target area; the AI hunts everything in that ~18.5 km zone, and the
map's engagement ring (`ui_zone`) draws the searched area. Convoy / supply-route interdiction (§35) still
frags armed recon on the road's **enemy end** (the right-click flow); the flight now area-searches that
end instead of following the exact polyline. The road-follow overrides (`_search_track`/`_hunted_route`/
`_interdiction_route_for`) and the `armed_recon_point` waypoint helper were removed with their test file.
The AI's actual hunt behaviour rides the L7 in-game re-fly.

**The search point stands off the target area (2026-07-06).** A flown Inherent Resolve test caught the
fly-over waypoint sitting **dead-centre on the Shirqat FOB** — the armed-recon anchor is usually an enemy
control point, and `armed_recon_area` placed the steerpoint (`flyover=True`) on the CP position, i.e. on
top of the garrison's SA-13/ZU-23 (the player had to improvise a ~4 km offset and standoff Mavericks; the
plan should not route anyone over the FOB). `Builder._stand_off_search_point` (`armedrecon.py`) now pulls
the ARMED RECON point back along the target→ingress bearing after the layout builds: standoff = the
target CP's own longest TGO threat ring (`max_threat_range`, ground truth) + a 2 NM buffer, floored at
**5 NM** for an undefended area, and capped at both the engage-zone radius (so the target area always
stays inside the hunt zone, which `armedreconingress.py` centres on this waypoint — the zone shifts
toward the corridor where the convoys actually drive) and the distance to the ingress point. TOT/package
sync math is untouched (`travel_time_to_target` already measures to the package target, not the fly-over
point). Tests: the standoff cases in `tests/test_armed_recon_planning.py`.

### Files & tests

| Area | Path |
|---|---|
| Force-model convoy | `game/fourteenth/vietnam_convoy.py` (`ensure_enemy_trail_convoy`, `_pick_trail_corridor`, `_skim_units`) |
| Turn hook | `game/game.py` (`finish_turn`, once per turn after transfer processing) |
| Right-click server | `game/server/qt/routes.py` (`POST /qt/create-package/supply-route/{id}`), `game/server/supplyroutes/models.py` (`interdiction_target_for_route_id`, route id encodes both CP ids) |
| Right-click client | `client/src/components/supplyroute/SupplyRoute.tsx` (`contextmenu` → `useOpenNewSupplyRoutePackageDialogMutation`; hook hand-added to `_liberationApi.ts`) |
| Setting | `game/settings/settings.py` (`vietnam_convoy_interdiction`) — no plugin options (the plugin has no convoy runtime) |
| Tests | `tests/fourteenth/test_vietnam_convoy.py` (corridor pick incl. `exclude_sources`; unit skim respects the fraction cap; setting-off / budget-full / turn-0 no-op; tops the budget up to the deficit; concurrent convoys spread across distinct corridors; a single-corridor campaign stays capped at one; COIN seeds from the insurgent whitelist; **a non-COIN Vietnam campaign seeds an empty source from `Faction.frontline_units`**; no pool available degrades to a no-op). `tests/fourteenth/test_red_tempo.py` (the surge-widened budget + doubled skim, still source-fraction-clamped). `game/missiongenerator/tests/test_vietnamops_luadata.py` asserts the emitter **never** emits a `convoy` node. `tests/server/test_supply_route_interdiction.py` (route-id → enemy-end resolution). |

### Gotchas / deferred

- **The convoy is a real force change, gated behind the toggle.** Because it moves real enemy units toward
  the front, it slightly *helps* the enemy reinforce — which is the point of interdiction: the player pays
  for *not* flying the Armed Recon. It only runs when `vietnam_convoy_interdiction` is on (Vietnam campaigns),
  so the blast radius is contained.
- **Convoy leg VERIFIED (checklist L6, 2026-07-02 Trail 2 flown session `wonderful-chatterjee`, on the
  pre-rework sizing).** A real `Convoy 001` (2× PT-76 + a Grad-URAL) drove the trail, was found and fully
  killed by the player's Armed Recon Phantoms. That session's "only 3 vehicles, only 1 convoy" feedback
  drove the 2026-07-03 sizing + seeding reworks above; the debit/`enemy_convoy` debrief leg still needs
  confirming against a real (non-stale) `state.json`. The multi-corridor spread + the external-seeding
  10-unit convoys are headless-verified against a real engine load (see above) but unflown in the cockpit.
- **The external-seeding framing is a real design shift, not a bug fix, and it's a deliberate trade.** Before
  this rework the trail was gated by the coalition's own accumulated economy (a scarcity model: the player
  taxes what little the enemy has produced); now the trail always has stock to skim from, framed as external
  logistics support arriving from outside the theater. This is the historically accurate picture for the Ho
  Chi Minh Trail specifically, and it's what "many more vehicles on the trail" required — the coalition's
  turn-1 economy genuinely had nothing to skim. It also means the trail's size no longer reflects how the
  war is actually going for the enemy (it won't visibly shrink as the coalition's economy is strangled some
  other way) — a possible follow-on would be scaling the seeded stock to the coalition's own resolve/will
  state instead of a flat 2× load.
- **Velvet Thunder's missing `supply_routes` is a real gap, not fixed here.** No corridor is ever picked
  there regardless of the seeding rework (its island geography has no opfor-opfor road at all) — it may need
  a different interdiction concept entirely rather than a road.
- **Right-click path (checklist L7) needs an in-app pass + a CI client rebuild.** The server resolution is
  test-covered; the React `contextmenu` → Qt dialog path can't be exercised headless, and the client hook was
  **hand-added** to the generated `_liberationApi.ts` (codegen unavailable locally), so a stale `client/build`
  won't have it. It now frags Armed Recon onto the corridor where the **real** convoy travels.
- **Opfor is hard-picked as RED** (the human fights red in the Vietnam case). A blue-side convoy for a
  red-player campaign would be a follow-on.
- **Reliably-present, not always-present.** If the opfor has no spare rear armour or no road corridor, no
  convoy is nudged that turn (the engine's organic transfers may still produce one). Guaranteeing a target
  every single turn regardless of the enemy's stock is a possible refinement.

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
- Tunables (plugin `specificOptions`): interval, rounds/event, dispersion radius (ft, `harassDispersionFt` —
  imperial-unit options since 2026-07-01), per-blast power, grace.

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

### The generic artillery mode (`artillery_base_harassment`, added 2026-07-05)

The same emitter + runtime, opened to conventional campaigns: a new **`artillery_base_harassment`**
setting (Mission Generation → World & systems, default OFF) drives `_populate_airbase_harassment`
with the tight **`ARTILLERY_FRONT_REACH_M`** (≈ 35 km — real tube/rocket range off the FLOT) instead
of the Vietnam siege's theater-wide 200 km, so only a field genuinely *on* the front sits under fire.
When both toggles are on the wider Vietnam reach wins. **Red Tide preseeds it** — the Fulda forward
FARP (~2.5 km off the Fulda↔Haina front) and red's Haina spearhead now live under sporadic artillery
harassment, "the Gap is not a safe ramp". Every §36 guarantee carries over unchanged (player-spawn
exclusion, grace, forward-only, symmetric). The emitted node stays `VietnamOps.airbaseHarassment`
(the `vietnamops` plugin owns the runtime; its non-harassment sections stay gated off).
**Plugin dependency (user-caught 2026-07-05):** the setting is dead if the *vietnamops plugin* is
disabled — and a conventional-campaign player has every reason to have unticked "Vietnam Ops" in
their saved defaults. **Red Tide therefore preseeds `plugins: {vietnamops: true}`** in its campaign
`settings:` block (the wizard layers campaign plugins over the player's saved defaults — the same
recommended-default mechanism as every other preseed; still uncheckable in the wizard); the plugin
is renamed "Vietnam Ops **& standoff harassment**" and both its description and the setting's
detail state the coupling. Guard: `tests/fourteenth/test_campaign_plugin_preseed.py` (the preseed
exists, survives `deserialize_state_dict`, and wins the wizard layering). Tests:
`tests/missiongenerator/test_vietnamops_harassment.py` (reach + gates). In-game pass: the L8 row's
artillery bullet.

## §37 — Super Gaggle hilltop resupply (Vietnam Ops suite)

The sixth **Vietnam Ops suite** feature (design note `414th-vietnam-ops-notes.md`, §E). Models the Khe Sanh
"Super Gaggle": a formation of transport helos runs supplies into a cut-off forward friendly outpost while the
player can fly escort. The base engine has no besieged-outpost resupply; this makes the forward hilltops feel
supplied-under-fire the way they historically were.

### Scope decision — real squadron airframes, not the planner (reworked 2026-07-01)

The design's v1 was a **planner-template** auto-frag (suppress + cargo + escort package, self-planned like
`auto_combat_sar`), **blocked on an auto-plannable CTLD cargo run the engine lacks**. v1 shipped runtime-only
like the §35 convoy — but that spawned **phantom** helos + suppressors (`coalition.addGroup`) on an
**unbounded respawn loop**: free BLUE airframes the campaign never accounted for, whose loss was never a real
loss. The rework keeps the runtime spawn (still no CTLD dependency) but makes the airframes **real**: they are
drawn from real BLUE squadrons and their losses are charged back at debrief ("debit a squadron + track
losses").

### How it works

**Python plans the run from real squadrons once per turn (`game/fourteenth/super_gaggle.py`
`plan_super_gaggle`, from `finish_turn`).** It selects the besieged BLUE **FOB/FARP nearest a front** (within
`OUTPOST_FRONT_REACH_M` ≈ 150 km) + the nearest **other** BLUE helo-capable field as the launch point, a
**real BLUE helicopter squadron** (nearest the launch field, with airframes) to fly the gaggle, and a **real
BLUE attack squadron** (CAS-capable) for the suppressors. It records a `SuperGaggleCommitment` on the game
(persisted, `__setstate__` default `None`): the squadron ids, the squadrons' own aircraft types, the **exact
per-airframe unit names** the plugin will spawn (`SuperGaggle-T{turn}-Helo-N` / `-Sandy-N`), and the geometry.
Counts are `DESIRED_HELOS` (3) / `DESIRED_SUPPRESSORS` (2), each **capped by the squadron's `owned_aircraft`**.
No feature / no outpost / no launch / no helo squadron with airframes ⇒ **no commitment** (the gaggle is never
free-spawned).

**The emitter serializes the commitment (`vietnamopsluadata.py` `_populate_super_gaggle`).** It reads
`game.super_gaggle_commitment` and emits
`superGaggle = { coalition, countryId, outpost{name,x,y}, launch{x,y}, helo{type,names[]}, suppressor{type,names[]} }`.
No commitment ⇒ no node. `countryId` is the BLUE faction's DCS country (2026-07-01 audit fix): the plugin
spawns under it because `coalition.addGroup` places units on whatever coalition owns the country — the old
hardcoded USA fallback (kept only for pre-fix saves) spawned the gaggle NEUTRAL for any non-US blue faction.

**The `vietnamops` plugin spawns exactly the committed airframes, once, after a delay** (vanilla DCS
`coalition.addGroup`, `pcall`-guarded): a helo group named with the committed helo unit names (launch →
outpost → back), and the suppressor attack flight with the committed suppressor names (launch → over the
outpost on a CAS task → back). **No respawn loop** — the run flies once (airframes are bounded to the
commitment), and a single tick fires the "delivered" / "down" cue then stops. The "inbound" cue notes the
suppressors when they spawned. **Launch is delayed, not immediate (2026-07-03 rework):** the whole spawn
was firing at t=0 (mission-config load), and a flown session's helos delivered by t≈306 s — the run was
over before a cold-starting player could plausibly be airborne to escort it. The plugin now defers the
entire spawn (helos, suppressors, cue, F10-mark-refresh tick loop — everything, wrapped in a local
`spawnGaggle()`) behind `timer.scheduleFunction(..., timer.getTime() + DELAY)`, `DELAY` defaulting to 600 s
(`gaggleDelaySec` plugin option) — enough for a typical cold start, taxi, and takeoff. The "armed" log line
still fires immediately (naming the delay), so ops can confirm the config without waiting; only the actual
spawn is deferred.

**Losses are charged back at debrief (`missionresultsprocessor.commit_super_gaggle` →
`super_gaggle.reconcile_super_gaggle`).** Because the spawned units aren't in the `UnitMap`, a killed gaggle
airframe's name lands in the debrief's **`killed_ground_units`** (see `Debriefing.from_json` — aircraft
classification requires a `UnitMap` flight). Reconcile counts each committed unit name found in either killed
list and debits its squadron (`owned_aircraft -= lost`, `destroyed_aircraft += lost`) — a **real airframe
loss**. Survivors cost nothing (a returning detachment — no pre-debit/return bookkeeping), and if any helo
survived the run is treated as **delivered** and the outpost gets a small `affect_strength` boost. The
commitment is then cleared (charged once). **No base-Lua / debrief-schema change** was needed — the existing
`dcs_retribution.lua` death-event capture already records the names.

### Files & tests

| Area | Path |
|---|---|
| Plan + reconcile | `game/fourteenth/super_gaggle.py` (`plan_super_gaggle`, `reconcile_super_gaggle`, `SuperGaggleCommitment`) |
| Turn hook / debrief | `game/game.py` (`finish_turn` → `plan_super_gaggle`; `super_gaggle_commitment` persisted), `game/sim/missionresultsprocessor.py` (`commit_super_gaggle`) |
| Emitter | `game/missiongenerator/vietnamopsluadata.py` (`_populate_super_gaggle`, reads the commitment) |
| Runtime | `resources/plugins/vietnamops/vietnamops-config.lua` (Super Gaggle section — single run, committed names) |
| Setting / options | `game/settings/settings.py` (`vietnam_super_gaggle`); plugin `specificOptions` (transit speed / altitudes / launch delay `gaggleDelaySec` — type & count come from the squadrons) |
| Tests | `tests/fourteenth/test_super_gaggle.py` (plan draws real squadron airframes with capped counts, clears when off / no outpost / no helo squadron; reconcile charges only killed names, floors at 0, credits delivery on survival, clears the commitment). `game/missiongenerator/tests/test_vietnamops_luadata.py` (emitter serializes a commitment's outpost/launch/helo+suppressor names; no commitment → no node). |

### Gotchas / deferred

- **Runtime run VERIFIED (checklist L9, 2026-07-02 Trail 2 flown session `wonderful-chatterjee`, on the
  pre-rework immediate-launch timing).** Both CH-53Es closed to 140 m of FOB Khe Sanh, delivered, and
  returned; both F-4E suppressors were shot down en route (one wreck also killed a friendly soldier) — the
  loss-accounting leg is now armed. The debrief charging exactly 2 F-4E airframes (and 0 CH-53s) to the
  suppressor squadron still needs confirming against a real (non-stale) `state.json`.
- **The launch-delay rework (2026-07-03) is itself unflown.** The Lua passes `luac5.1 -p`, but the deferred
  `timer.scheduleFunction` spawn hasn't been watched in a cockpit: confirm the "armed … launching in Ns" log
  line fires immediately, nothing spawns before `DELAY` elapses, and the run then proceeds exactly as the
  2026-07-02 pass already verified (helos reach the outpost, delivery/down cue fires once, losses charge back).
- **Loss accounting rides on the committed unit names appearing in the debrief.** If DCS ever failed to emit a
  death event for a runtime-spawned unit, that airframe wouldn't be charged (it would read as a survivor). The
  in-game pass should confirm a killed gaggle name lands in the state / debrief.
- **Suppressor weapons are still a tuning item.** The suppressor spawns with its squadron aircraft's *default*
  loadout (no explicit `payload`), so its effectiveness against the AAA is unverified — it may strafe or be a
  visual presence. A spawn failure stays harmless (guarded; the helo run proceeds).
- **Blue-only (symmetry deferred).** The plan hard-picks the BLUE outpost; a red-player mirror is a follow-on.
- **Losses-only — no delivery credit (2026-07-07 design call).** The earlier survival-gated
  `DELIVERY_STRENGTH_BONUS` (a clean run nudged the outpost's ground strength) is **removed**. The only signal
  the debrief carries is which committed airframes died, and an airframe's *absence* from the kill list is
  "survived and delivered" OR "never spawned at all" (e.g. the player ended the mission before the launch
  delay) — indistinguishable without a runtime "delivered" signal the plugin does not emit, and emitting one
  would need exactly the Lua/debrief-schema change this module avoids. So the gaggle costs the wing only the
  airframes it actually loses; a clean run is free. Re-introducing the credit is deferred behind a real
  delivery signal (the plugin writing a "reached the outpost" marker the debrief can read).

## §38 — FAC(A) willie-pete target marking (Vietnam Ops suite)

The seventh **Vietnam Ops suite** feature: the iconic Vietnam **forward air controller (airborne)**. An
OV-10 Bronco loitering over the battle area marks nearby enemy ground with **white-phosphorus smoke** so the
strikers — and the player — can visually acquire the target and roll in. The engine already has a **ground
JTAC** (stationary, *lases* targets for CAS); this is the distinct **airborne, smoke-marking** half that the
JTAC doesn't cover, and it's the defining Vietnam FAC image (the Bronco putting willie pete on the target).

### How it works

Same shape as §33 flak — an **on-marker + runtime discovery**, no per-mission data:
- **Python** (`vietnamopsluadata.py` `_populate_fac`) emits only
  `dcsRetribution.VietnamOps.fac = { enabled = true }` when `vietnam_fac_marking` is on.
- **The `vietnamops` plugin** discovers the FAC aircraft itself at runtime — airborne, alive friendly units
  whose DCS type matches the FAC type (default `Bronco-OV-10A`) — and, on a cadence (default 120 s, so the
  ~5 min smoke stays fresh), drops **white smoke** (`trigger.action.smoke`, willie pete) on the **nearest
  opposing ground unit** within the spot/mark range (default 3 NM) of the FAC, plus a "target marked with
  willie pete — cleared hot" cue to the FAC's coalition. Symmetric by construction (both sides scanned), but
  only OV-10 owners have FACs, so it's blue-effective in practice. No friendly OV-10 airborne over the front
  ⇒ nothing marked.
- Tunables (plugin `specificOptions`): FAC aircraft type, spot/mark range (NM, `facRangeNm` — imperial-unit
  options since 2026-07-01), mark cadence.

### Files & tests

| Area | Path |
|---|---|
| Emitter | `game/missiongenerator/vietnamopsluadata.py` (`_populate_fac`) |
| Runtime | `resources/plugins/vietnamops/vietnamops-config.lua` (FAC section) |
| Setting / options | `game/settings/settings.py` (`vietnam_fac_marking`); plugin `specificOptions` (type/range/cadence) |
| Tests | `game/missiongenerator/tests/test_vietnamops_luadata.py` (the `fac` on-marker is emitted when the setting is on, independent of the other suite features; off = no node) |

### Gotchas / deferred

- **Runtime VERIFIED (checklist L10, 2026-07-02 Trail 2 flown session `wonderful-chatterjee`).** The
  named F10 map mark appeared at the target cluster in a flown multiplayer session (user-confirmed),
  "FAC(A) marking armed" in `dcs.log`, no Lua error — the mark is unambiguously the plugin's (the
  Bronco's own WP rockets make no F10 mark).
- **Marking only — no auto-assignment (deferred).** v1 marks the target with smoke; it does **not** assign the
  target to a CAS package or coordinate a strike (that overlaps the ground-JTAC/tasking systems). The
  smoke-mark is the iconic, low-risk core; FAC→CAS coordination is a possible later increment.
- **Runtime-cosmetic.** A smoke plume, no gameplay-model change — the value is the visual target cue.
- **FAC type is a single configurable id.** Default `Bronco-OV-10A`; the O-2 Skymaster or another light FAC
  could be added as a discovered type in a later pass.

## §39 — Snake and nape (napalm CAS) (Vietnam Ops suite)

The eighth **Vietnam Ops suite** feature: the iconic low-level napalm close-air-support delivery — **"snake
and nape"** ("snake" = Snakeye retarded/high-drag bombs, "nape" = napalm canisters), the signature Vietnam CAS
run where an attacker rolls in low and fast and lays a **wall of fire** across the enemy. DCS doesn't model
napalm as an effective AI/soft-target weapon, so this is the flavor layer that makes the on-the-deck run *do*
something visible and lethal to troops in the open. **Detonation-anchored since 2026-07-02**: the fire is
tied to real ordnance impacts, not a proximity heuristic.

### How it works

The on-marker is the §33 flak / §38 FAC shape; the runtime is **event-driven** (the Splash Damage
weapon-tracking pattern), no per-mission data:
- **Python** (`vietnamopsluadata.py` `_populate_snake_nape`) emits only
  `dcsRetribution.VietnamOps.snakeNape = { enabled = true }` when `vietnam_snake_and_nape` is on.
- **Release gate.** A `world.addEventHandler` `S_EVENT_SHOT` handler catches each release of an **eligible
  retarded bomb** — the weapon's DCS type name matched (case-insensitive plain-text, comma-separated
  patterns; default `SNAKEYE`, which catches the native `MK_82SNAKEYE` and the mod packs' Mk-81/82 Snakeye
  variants) — made from a qualifying **delivery profile at the moment of release**: the shooter airborne,
  at/below the run-in ceiling AGL (default 500 ft) and at/above the min ground speed (default 180 kts — keeps
  a loaded A-1 Skyraider run eligible). High, slow, or ineligible-ordnance releases are ignored: the ordnance
  **and** the profile are both the cost of the fire.
- **Track to detonation.** Each caught weapon joins a fast sample loop (0.1 s steps, alive only while an
  eligible weapon is in flight — a low Snakeye flies ~2–6 s) recording position/velocity. When the weapon
  stops existing it has detonated: the impact point is resolved by terrain-intersecting the final flight path
  (`land.getIP` on the last sample — the Splash Damage pattern, with a snap-to-ground fallback) and **one
  fire node** (`trigger.action.effectSmokeBig`, medium preset, auto-**stopped** after 90 s) **+ a modest
  `trigger.action.explosion` bite** (default 40 — napalm's real soft-target lethality, on top of the bomb's
  own native HE) is laid **at the real impact point**. The **wall of fire emerges from your actual ripple
  spacing** — a 6-bomb ripple burns as a 6-node line along the fall line; a dry pass lays nothing; a miss
  burns where it missed. The "SNAKE AND NAPE — napalm on the deck" cue fires once per salvo (a short
  per-shooter window), not per bomb.
- **Real napalm is excluded.** Mk-77 fire bombs (`MK77mod0/1-WPN`, the A-4E-C's cans) are skipped whatever
  the pattern list says — the bundled (locked) Splash Damage build already renders real napalm end-to-end
  (`napalm_mk77_enabled`: tracked impact fireballs, phosphor, unit damage), and double-rendering would stack
  effects. SD owns real nape; §39 owns the Snakeye stand-in.
- **Rewards, doesn't punish.** Unlike the flak gauntlet (which *thickens* against a predictable straight run),
  snake-and-nape *pays off* pressing the CAS run in on the deck — the risk of getting low is the trade for
  laying effective fire, and now the aim matters too.
- Symmetric by construction (any side's qualifying release; no aircraft-attribute gate — carrying and
  dropping the ordnance low **is** the eligibility, so a Snakeye-armed F-4 counts even though it lacks the
  `Attack airplanes` attribute the v1 scan required).
- Tunables (plugin `specificOptions`, imperial): release ceiling (ft AGL), min release speed (kts), the
  ordnance pattern list (`napeWeaponPatterns` — add e.g. `MK_82` to let plain slick low drops count),
  per-impact power.

### Files & tests

| Area | Path |
|---|---|
| Emitter | `game/missiongenerator/vietnamopsluadata.py` (`_populate_snake_nape`) |
| Runtime | `resources/plugins/vietnamops/vietnamops-config.lua` (Snake and nape section) |
| Setting / options | `game/settings/settings.py` (`vietnam_snake_and_nape`); plugin `specificOptions` (release ceiling/speed, weapon patterns, per-impact power) |
| Tests | `game/missiongenerator/tests/test_vietnamops_luadata.py` (the `snakeNape` on-marker is emitted when the setting is on, independent of the other suite features; off = no node) |

### Gotchas / deferred

- **Runtime is unflown (checklist L11).** The Lua passes the `luac5.1 -p` gate, but the `S_EVENT_SHOT`
  handler, the weapon tracking, and the `effectSmokeBig`/`explosion` placement can't be exercised headless.
  #1 thing to confirm in the cockpit: the released Snakeye's **type name actually matches the pattern list**
  across the flown modules (native + A-4E-C/mod-pack variants) — if a wanted bomb doesn't lay fire, check
  `dcs.log` for the armed line and widen `napeWeaponPatterns`. Also watch that the fire appears **at the
  impact points** (seconds after release, not at the release), that the fires **stop** after the burn time
  (no permanent infernos), and that a Mk-77 drop shows **only** the Splash Damage napalm (no doubled effect).
- **AI eligibility is now authored (2026-07-02): the doctrine low-level attack profile.** The 2026-07-01
  squadron call ("player-triggered only in practice — AI attack flights never fly the deck"; the Yankee
  Station session's A-1s sat at 6,400 m all mission) is addressed by the planner increment it named:
  `Doctrine.low_level_attack_altitude` (`game/data/doctrine.py`, Vietnam = **500 ft**, matching the
  `napeCeilingFt` default) caps the combat-altitude legs — ingress, the attack run, egress, and the attack
  plan's nav legs — of **CAS / BAI / Armed Recon** flights in `WaypointBuilder.get_combat_altitude` (+ the
  `cas()` 1,000 m track floor is bypassed), so era attackers press their runs in on the deck at RADIO/AGL
  waypoints. Strike is deliberately exempt (Alpha Strike dive deliveries + B-52 Arc Light, which rides
  Strike), as are helos (own AGL logic) and heavies (`HEAVY_BOMBER_DCS_IDS`, now shared from
  `game/data/units.py`). Gate helper `low_level_attack_altitude_for` is unit-tested
  (`tests/ato/flightplans/test_low_level_attack_profile.py`); the **flown half is still owed** — the plan
  puts the AI low, but whether the DCS AI's own `AttackGroup` delivery releases ≤ 500 ft AGL is an L11
  cockpit question (if it climbs to dive-bomb anyway, next levers: pass `altitude=` on the BAI
  `AttackGroup` task or raise `napeCeilingFt`). The §33 flak interplay (low + steady = tighter bursts) now
  applies to AI runs too — that trade is the point. NEW game required (doctrines pickle by value).
- **Detonation-anchored (2026-07-02 rework).** v1 was proximity-triggered — a 2 s poll laying a fixed swath
  on the *nearest enemy unit* whenever an `Attack airplanes`-attributed aircraft crossed a low/fast/near
  gate. That fired with **no ordnance released** (a dry low pass = a free napalm wall), made **aim
  irrelevant** (you couldn't miss — and a perfect drop just outside the scan range rendered nothing), and
  mistimed/misoriented the fire. The rework ties everything to real releases and real impacts; the retired
  options (`napeDropRangeFt`/`napeSwathLengthFt`/`napeFireNodes`, plus the per-aircraft cooldown) gave way
  to `napeWeaponPatterns` — bombs are the cost now, so no cooldown is needed.
- **The per-impact bite is real (by design).** Unlike flak's mostly-visual power, the default blast is tuned
  to hurt soft targets — that *is* the feature (napalm was devastating to infantry/trucks), stacked on the
  Snakeye's own native HE. Dial `napeBlastPower` down (or to 0) for a purely-cosmetic wall of fire.

## §40 — Campaign phases (inferred arc + planner emphasis)

Every campaign — including the 63 base-Retribution campaigns that ship with nothing but a YAML header —
knows what **phase** of the air war it is in, the UI shows it, and the auto-planner biases its offensive
intent to match. A phase is a doctrine-like profile, **time-sliced instead of campaign-wide**, resolved fresh
each turn from live campaign state (the VIETNAM_DOCTRINE display-and-gate precedent — never a commander
rewrite, never a persisted-enum mutation). Spec of record:
[`414th-campaign-phases-notes.md`](design/414th-campaign-phases-notes.md); this landing is **P0 + P1**
(Tier-0 inference for all campaigns; Tier 1/2 YAML authoring + advance_when conditions + whitelist deltas are
P2, riding the Vietnam W4 arcs).

### How it works

- **The model** (`game/fourteenth/phases.py`): three generic `CampaignPhase`s — **Air Superiority**
  (`rollback`), **Interdiction**, **Offensive** — each carrying a narrative and an `emphasis` ordering of
  `PlanNextAction`'s offensive HTN root methods (kept as class *names* so the module never imports the
  commander; a sync test locks the two).
- **The classifier** (spec §3.2, thresholds refined by the 6-campaign pilot + the #379 engine-authoritative
  all-66 re-run): each turn it reads pre-existing accessors — alive enemy long+medium SAM **sites** banded by
  the TGO's `GroupTask` LORAD/MERAD, the exact set `degradeiads.py` rolls back (the §3.1 correction:
  `IadsRole` **cannot** band this — its `SAM` role swallows SHORAD and its `EWR` role swallows AAA/navy; EWR
  stays excluded as author-noise), enemy air-superiority airframes off the red air wing, mean front movement
  vs. the turn-0 anchor, base ratio, last turn's captures off the SITREP — and picks the phase.
  The **absolute-SAM-floor gate** (`ROLLBACK_SAM_FLOOR` = 3) is the pilot's key finding, with the engine-run
  corrected examples: the genuine below-floor campaigns are Shattered Dagger / Battle for No Man's Land /
  Valley of Rotary / Northern Guardian (open in Interdiction); Velvet Thunder sits exactly at the floor and
  keeps Rollback; **Khe Sanh is not below the floor in real gameplay** (the generator fills 4 SA-2/SA-3
  batteries — the pilot's original 0-SAM read was a `--lite` artifact). Real enemy air without a belt still
  holds the air-superiority fight. The **peer-fight guard** falls out of the same shape:
  Rollback only releases when the IADS is down AND the air threat is gone.
- **Hysteresis** (spec §3.3, mandatory): min-dwell `PHASE_MIN_DWELL_TURNS` = 2, **monotonic-forward** by
  default (regression is authored-only/P2; the asymmetric `IADS_ROLLBACK_REENTER` = 0.6 margin is implemented
  and test-locked behind the flag).
- **Baselines** (spec §5): nothing in the engine persists an initial front line or IADS count, so
  `PhaseBaseline` snapshots them lazily on the classifier's first gated run (turn 0 for a new game; first
  load for an old save — the accepted migration). Persisted on `Game` with the phase pointer
  (`current_phase_key`, `phase_entered_on_turn`, `phase_status_line`) via `__setstate__` setdefaults.
- **Planner consumption** (spec §4): `PlanNextAction.each_valid_method` keeps the reactive prefix
  (`TheaterSupport`/`ProtectAirSpace`/`DefendBases`) and the `RecoverySupport` tail **fixed** — the §17
  boundary, reactive defense stays deterministic — and reorders only the offensive middle per the active
  phase's `emphasis`, which shifts which objectives get first claim on the limited offensive aircraft.
  **BLUE only**: the phase is the campaign's (blue-perspective) arc; red keeps stock order.
- **Legibility** (spec §3.4): the phase always explains itself — "Interdiction — enemy IADS 22% · air threat
  low · front static" — via `legibility()`, stored as `game.phase_status_line`. Phase *transitions* post an
  Information message once (the campaign-start assignment is silent).
- **Surfaces**: the kneeboard **cover page** (§30) gains a CAMPAIGN PHASE band (status line + narrative + —
  per playtest ask on 1968 Yankee Station — the **ROE spelled out**: `roe_summary_lines(game)` in
  `phases.py` renders OFF LIMITS (sanctuary zones with radii, amber) / LOCKED (withheld target classes,
  amber) / CLEARED (classes the enemy actually fields and the phase released — derived from the live
  laydown, villages never advertised — plus the never-gated front-line fight, green), so "ROE restrictions
  active" isn't a guessing game; empty on phases with no ROE payload); the
  web client gains a **campaign-status ribbon** over the map (`CampaignStatusBar`) fed by a new
  `GameJs.campaign_status` payload (campaign name / turn / date — previously never sent to the client at all —
  + phase + the political-will meters on Vietnam campaigns, each segment self-hiding when absent); and the
  **Qt intel box** (`qt_ui/widgets/QIntelBox.py`) gains Campaign phase + Political will rows (tooltips carry
  the §3.4 "why" string and the negotiation framing; both rows hide entirely on games without the feature, so
  a stock campaign's box is unchanged).

| Piece | Where |
|---|---|
| Model + classifier + hysteresis | `game/fourteenth/phases.py` |
| Game state + migration + per-turn hook | `game/game.py` (`initialize_turn`, `__setstate__`) |
| Planner emphasis | `game/commander/tasks/compound/nextaction.py` (`_offensive_order`) |
| Kneeboard band | `game/missiongenerator/kneeboard.py` (`CoverPage`) |
| Server payload | `game/server/game/models.py` (`CampaignStatusJs`) |
| Client ribbon | `client/src/components/campaignstatus/` + `api/campaignStatusSlice.ts` |
| Setting | `game/settings/settings.py` (`campaign_phases`, default ON, Campaign Management) |
| Tests | `tests/fourteenth/test_phases.py` (thresholds, hysteresis, legibility, update gating, emphasis sync + ordering) |

### Gotchas / deferred

- **Default ON for every campaign** ([DECIDED] Tier-0 inference is the default). The `campaign_phases`
  toggle is the kill switch if the emphasis misbehaves in a live campaign — checklist **M3**.
- **The phase never gates reactive defense** (§17 boundary) and never forbids a task in Tier 0 — it is a
  bias and a narrative, not a new commander. Hard whitelist deltas are authored-only (P2).
- **Client ribbon needs the CI client rebuild** (`_liberationApi.ts` types hand-added; no local npm).
- **Deferred**: Consolidation phase (spec leaves it optional, v1 ships three), a red-perspective arc,
  New Game wizard arc preview, SAM-density-scaled Rollback dwell. (Tier 1/2 authoring + `advance_when`
  landed with W4; the objectives checklist + transition transparency landed 2026-07-02 — see below.)

### W4 — the authored tier (P2) + the ROE escalation layer

Vietnam campaign layer **W4** rides this feature: a campaign YAML may now carry a `phases:` block of
**authored phases** that override Tier-0 inference (`parse_phases` + `authored_arc_for`, cached per process,
re-derived at load per spec §5 — never pickled). Authored transitions: the next phase's `min_turn` is the
scheduled escalation date; the current phase's `advance_when` (any-of `min_turn` / `blue_will_below` /
`enemy_iads_below`) accelerates it — bleeding political will speeds escalation. The ROE payload:

- **`restricted_zones`** — shape-typed areas where offensive tasking is forbidden. `RestrictedZone.kind`
  selects the geometry (all authored in NM, `_parse_restricted_zone` dispatches on `shape:`; a legacy
  `{center, radius_nm}` block parses to a **circle** byte-identically, so the 4 Vietnam campaigns are
  unchanged):
  - `circle` — `center` (CP name) or `x`/`y` + `radius_nm`.
  - `box` — a rotatable rectangle: `center` (CP or x/y) + `width_nm` × `height_nm` + optional `heading`
    degrees (the Nevada range / a Route-Package rectangle).
  - `corridor` — a lane: a `path` of ≥2 anchors (CP names and/or `{x, y}`) + `width_nm`, a shapely
    buffered polyline (an ingress route / the Ho Chi Minh trail).

  `_resolve_zone` turns each into a `ResolvedZone` carrying a shapely geometry; `zone.contains(pos)` is the
  one containment primitive both enforcement points use — circles keep the exact distance test, box/corridor
  use shapely point-in-polygon. The **AI planner gate** sits in `PackagePlanningTask.fulfill_mission` next to
  the Vietnam `tasking_whitelist` read (`roe_blocks_target`, BLUE-only); sanctuary airfields fall out (a CP
  inside a zone can't be OCA'd). The **player is never hard-blocked**: kills inside an active zone are counted
  at debrief (`count_roe_violations`) and drain Political Will sharply (`BLUE_ROE_VIOLATION` in
  `political_will.py`, with an "ROE violation" message).
- **`locked_targets`** (target_release) — TGO `category` strings (+ special `airfield`) still locked in a
  phase; blocked in the same planner gate, badged **RESTRICTED — ROE** on the TGO tooltip
  (`TgoJs.roe_restricted`) instead of vanishing — the defining Rolling Thunder frustration, on purpose.
- **`free_fire_zones` — inverted ROE (the COIN kill boxes)** — when a phase authors this list, the polarity
  flips: the whole map is **weapons-hold for fixed strikes**, cleared only inside these pockets (the OIR
  Blue-Kill-Box model — see the Rampagers reference library). Same shape system (`circle`/`box`/`corridor`/
  `from_drawing`), resolved by the same `_resolve_zone`. Gate: `roe_restriction_reason` returns "outside the
  weapons-free area" for a class-carrying target outside every pocket (fail-open if none resolve);
  **front-line forces / convoys are never gated** (`target_class is None`) — the ground fight stays legal.
  A `restricted_zone` still carves a no-strike hole *inside* a pocket (checked first), so a kill box over a
  stronghold clears the annulus around the town, never the town core. `count_roe_violations` adds the
  inverted count: a kill **outside every pocket** is a violation (restricted-zone hits still count as
  before). `roe_summary_lines` leads with a **WEAPONS FREE** row ("KB SANGIN 12 nm · … (all else
  off-limits)") and `phase_status_line` lights "ROE restrictions active" for free-fire-only phases too.
  **The COIN campaign does NOT use free-fire (ROE-shape rework, 2026-07-03).** The capability stays in the
  engine, but `coin_enduring_resolve.yaml` was reworked from an earlier 9-town-ring restricted + whole-map
  free-fire inversion to **4 big box/corridor no-strike "positive-control valleys"** over the real populated
  river valleys, shared by all three phases via the `&population_centers` YAML anchor — no `free_fire_zones`
  in any phase. The 4: two corridors (**Helmand Green Zone** Kajaki→Sangin→Gereshk→Lashkar Gah→Marjah, 22 nm
  wide; the **Musa Qala** 611 feeder Now Zad→Musa Qala→Kajaki, 18 nm) + two boxes (the **Tarin Kowt** bowl
  34×28 nm; the **Delaram** junction 30×26 nm). A fixed strike inside a valley prices CDE into the mandate
  (violation weight 1.0 — pressure, not taboo); the open desert and the northern gate are simply
  unrestricted; trail convoys / TIC are never gated and air assaults (captures) are never blocked, so the
  arc still retakes its objectives. Exercises both the box and corridor shapes. CI-locked in
  `test_enduring_resolve_campaign_definition` (4 zones/phase — 2 box + 2 corridor, correct names, no
  free-fire).
- **Map layer** — `GameJs.restricted_zones` + `GameJs.free_fire_zones` (each carries `kind` +
  `center`/`radius_m` for circles and an `outline` polygon ring for box/corridor) → `RestrictedZonesLayer`
  draws a dashed `<Circle>` or `<Polygon>` by kind (+ sticky tooltip) — **red for restricted, green for
  free-fire** (tooltip "WEAPONS FREE (ROE)"); free-fire renders under restricted so a carve-out sits on top.
  In the layers panel "Enemy intel" group, default ON (renders nothing outside authored ROE campaigns).
- **F10 / Mission-Editor drawing** — `DrawingsGenerator.generate_restricted_zones` paints the same resolved
  zones into every generated `.miz` (dashed **red** restricted + dashed **green** free-fire via the shared
  `_paint_zones`, alongside the always-on frontline/route/CP drawings):
  `add_circle` for a circle, `add_freeform_polygon` of the outline for a box/corridor. Reuses
  `active_restricted_zones`, so the cockpit F10 map and the web map show identical geometry. No-op outside an
  authored ROE phase.
- **`from_drawing` — read author-drawn ME shapes back (Path B)** — instead of typing coordinates, an author
  *draws* the zone in the campaign `.miz`'s Mission Editor and references it by name:
  `restricted_zones: [{from_drawing: "Hanoi Box"}]`. `game/fourteenth/zone_drawings.py`
  (`read_zone_drawings`) walks the loaded mission's drawing layers and normalizes each supported shape into a
  named `DrawnZone` (v1: **Circle** → circle, **FreeFormPolygon** → polygon area; Rectangle/Oval/TextBox and
  unnamed drawings are skipped — Rectangle/Oval carry a centre-vs-corner/axis convention unverifiable without
  an in-game pass, and a box/corridor is drawn with the polygon tool). `MizCampaignLoader.populate_theater`
  reads them once into `theater.zone_drawings` (pickled with the theater; getattr-guarded for pre-Path-B
  saves); `_parse_restricted_zone` turns `from_drawing` into a `kind="drawing"` `RestrictedZone`, and
  `_resolve_drawing_zone` looks the name up and builds the same `ResolvedZone`/shapely geometry — so a drawn
  zone gates the planner, drains will, and paints on both maps identically to a typed one. A reference to a
  missing drawing resolves to nothing (logged), never a crash.
- **The authored arcs** — all 4 Vietnam campaigns ship **Rolling Thunder → The Bombing Halt → Linebacker →
  Linebacker II** (sanctuary on Kutaisi/Hanoi + Senaki/Haiphong for Yankee Station/Steel Tiger — the 2026-07
  coastal-ladder recast — plus a **permanent Tbilisi-Lochini "PRC border" ring those two keep in every
  phase, Linebacker II included**; Sukhumi-Babushara for Khe Sanh, Saipan Intl for Velvet Thunder; zones
  shrink then release, target classes release, schedule ~turns 8/11/16 accelerated by will). Structure
  guarded in `tests/test_vietnam_content.py`; behaviour in `tests/fourteenth/test_phases.py`. In-game pass:
  checklist **M4**.
- **Phase-coupled red tempo (W6)** — Hanoi *answers* the arc (design note
  `414th-vietnam-red-tempo-notes.md`): an optional authored per-phase `red_tempo:` block parsed onto
  `CampaignPhase` (`trail_surge` / `ground_offensive` / `resolve_regen`), applied by
  `game/fourteenth/red_tempo.py`. The Bombing Halt is a **logistics window** — the trail runs two
  concurrent, bigger convoys (`ensure_enemy_trail_convoy` reads `trail_surge_multiplier`) and Regime
  Resolve regains 1.5/turn (once-per-turn guard `Game.red_tempo_regen_turn`), so waiting out the halt
  costs Washington leverage; Linebacker entry fires a 3-turn **Tet/Easter ground-offensive pulse**
  (`apply_red_tempo` in `initialize_turn`, after the coalitions plan and before GroundPlanner reads
  `cp.stances`) that raises red's front stances to AGGRESSIVE (raise-only — a winning commander keeps
  BREAKTHROUGH) with the trail surging alongside (`GROUND_OFFENSIVE_MIN_SURGE`); the W2b static-front
  clamp still bounds the movement, so the pulse bleeds BLUE's will rather than sweep-capturing. Authored
  phases only — Tier-0/generic campaigns are complete no-ops. Tests: `tests/fourteenth/test_red_tempo.py`.
  In-game pass: checklist **M6**.

### The legibility pass (2026-07-02) — transitions, objectives, will attribution, pre-flight ROE

Four additions that make the *dynamics* readable — the UI showed state well but not why things move or
when they'll move next:

- **Transition transparency** — the arc expander spells out how the arc LEAVES each phase. Authored
  phases render their `advance_when` acceleration with **live values on the current phase**
  ("Escalates early if will falls below 65 (now 100) or enemy IADS falls below 40% (now 78%)");
  Tier-0 phases spell out the classifier thresholds they advance on (`_TIER0_ADVANCE`), so an inferred
  arc explains its transitions the same way an authored one does. `_describe_condition` +
  `_advance_display` in `phases.py` → `arc_overview`'s `advance` string → `PhaseArcEntryJs.advance` →
  the `.campaign-phase-advance` footnote row.
- **Objectives checklist** (the P2 "objectives" leftover) — each phase carries a
  `PhaseObjective` tuple (text + optional `done_when: PhaseCondition`), shown in the expander with live
  ticks (✓ done / ○ open / • display-only). The three Tier-0 phases ship built-in objectives (measurable
  IADS goals tick off live state), and all 4 Vietnam arcs author two per phase (`objectives:` YAML —
  plain string or `{text, done_when}`; Linebacker's "Break the SAM belt" ticks on `enemy_iads_below`,
  Linebacker II's "Break Hanoi's resolve" on the new `red_resolve_below`). `PhaseCondition` also gains
  **`capture_cp`** (a named CP falling to BLUE) — both new fields double as `advance_when` triggers.
  Objectives are display guidance, never a gate — transitions stay owned by min_turn/advance_when.
- **Will-attribution ledger** (`political_will.py`) — `_blue_moves`/`_red_moves` now return labeled
  `(label, value)` components ("heavy bombers x1 down −6.0", "POWs held x3 −1.5", "trail convoys x4
  −6.0"), summed into the same deltas as before (weights untouched). A `WillLedgerEntry` per flown turn
  persists on `Game.will_ledger` (capped `WILL_LEDGER_CAP` = 60, `__setstate__` default). Surfaced via
  `ledger_notes()`: the ribbon meter **hover** + an expander notes row (client), the **SITREP band**
  ("Will movers: …" / "Enemy resolve movers: …" under the will line), and the per-turn "Political will"
  Information message now names the top movers. This is also the instrument for the **M1** pacing pass —
  tuning weights from a played campaign no longer means guessing which feed moved the number.
- **Pre-flight ROE warning** (`QPackageDialog.update_roe_warning`) — creating/editing a package on a
  restricted target shows an amber "⚠ ROE — …" line (reusing `roe_restriction_reason`, BLUE-only):
  the player can still frag it, but the will cost is a knowing choice at planning instead of a surprise
  at debrief. Hidden on clean targets; the "drain political will" clause only renders when
  `vietnam_political_will` is on.

Tests: `tests/fourteenth/test_phases.py` (advance strings authored+Tier-0, objective ticks, new
condition fields, parse rejections), `tests/fourteenth/test_political_will.py` (ledger components/cap/
off-switch, `format_moves` ranking), `tests/test_sitrep.py` (movers lines). The client side needs the
CI client rebuild; the expander/ROE-warning visuals fold into the existing **M3/M4** in-game passes.

Still open from P2: per-phase `tasking_whitelist` deltas and `front_line_stance` nudges (the W6 red
pulse covers the red half; a blue-side authored stance nudge is still open); plus the 3 wiki-campaign
arcs (P3).

### Will profiles (2026-07-02) — the any-era generalization

The will economy's Vietnam framing and weights are now only the **defaults** of a campaign-authorable
**will profile** (design note `414th-will-generalization-notes.md`). A campaign YAML's `will:` block
(sibling of `phases:`) re-labels both meters and their exhaustion banners (`blue:`/`red:` →
`WillSideCopy`: `label`, `exhaustion_title`, `exhaustion_body`) and re-weights every feed (`weights:` →
`WillWeights`, one field per constant; unknown keys are parse errors so a typo never silently no-ops a
rebalance). Profiles follow the phases-S5 rule — re-derived from the campaign YAML by name
(`will_profile_for`, cached in `_PROFILE_CACHE`), never pickled, any failure degrading to the defaults
with a log — so the 4 Vietnam campaigns (no block) are byte-identical to the pre-profile behavior
(`test_default_profile_is_the_vietnam_framing`). A new **warship feed** closes the naval gap
(Falklands prerequisite): `blue_ship_lost` 4.0 / `red_ship_lost` 0.5, counted from the debriefing's
ground-object losses by `TheaterUnit.is_ship`, with RED's ships subtracted from the generic
ground-attrition pool (never double-counted). COIN C2 added `red_cache_lost` (default 0.0 — inert outside COIN): each RED ammo-category TGO destroyed this turn (fully dead, per-TGO dedup, post-loss-commit) drains resolve at the campaign's price, on top of generic attrition. Label surfaces that follow the profile: the per-turn
message + exhaustion banners, the client ribbon meter tooltips (`CampaignStatusJs.blue/red_will_label`,
Vietnam-string fallbacks in `CampaignStatusBar.tsx`), the Qt intel-box tooltip, and the Stats
will-chart legend. Tests: the "will profiles" section of `tests/fourteenth/test_political_will.py`
(default-equivalence, parse/degrade, ship feed, authored labels driving banners). No new runtime Lua —
the M1 pacing pass now also covers tuning via `will: weights:`.

## §41 — High Digit SAMs "Ultimate Compilation" support

Retribution's High Digit SAMs mod support targeted the original **HighDigitSAMs v1.4.0**, a mod that has
been unmaintained for years. The fork now targets its actively-maintained successor, the
**[HighDigitSAMs Ultimate Compilation](https://github.com/dcs-sams/HighDigitSAMs-Ultimate-Compilation)**
(v1.4.3+ — HighDigitSAMs + SAM Pack + SAM Sites Asset Pack + IDF Assets Pack in one install). The same
`high_digit_sams` New Game toggle gates everything (relabeled in the wizard, plus a **fork-mismatch
warning** — an always-visible note under the mod list + a control tooltip naming the exact dcs-sams build
and explaining that the original Auranis mod / other forks rename units and silently break); no save
migration is needed.
All unit data was read from the **installed mod's own Database lua files** (launcher threat = missile
`distanceMax`, tracker detection = the vehicle-file tracking range), not guessed from specs.

### What changed vs. v1.4.0

- **Dropped by the mod** (DCS core now has vanilla equivalents): the HDS `KS19` / `Fire Can radar` AAA pair
  (vanilla KS-19/SON-9 and the existing `KS-19/SON-9` preset replace them — the redundant `KS-19_HDS`
  preset is deleted) and the `SA-24 Igla-S manpad` (factions re-pointed to the vanilla SA-18 Igla-S).
- **Renamed S-300PS radars**: `40B6M MAST tr` → `30N6 MAST tr`, `40B6MD MAST sr` → `76N6E sr`,
  `64H6E TRAILER sr` → `64H6E MOD sr` — the S-300 Site layout, the SA-10B preset, `radar_db.py`, and the
  Morocco faction livery map were re-pointed. The retired pydcs classes (and their unit YAMLs) are **kept
  registered for save-compat only** — do not reference them in factions/presets/layouts.
- **New families added** (38 → 80 registered units): **S-400/SA-21** (3 LN types incl. the 400 km 40N6E,
  2 TR, 3 SR, CP), **S-300V4** (3 LN incl. the 380 km 9M82MDE, TR, 2 SR, CP), the **S-300PT** launcher,
  a PMU2 mast TR, **Pantsir-SM** (SHORAD class), the **SAMP/T battery** (ARABEL/Ground Fire 300 STRs, C2,
  ECS, EPP, Block 1/1NT TELs), **SA-7/SA-7b manpads**, four **EWRs** (P-37 Bar Lock, 55G6U Nebo-U, 1L119
  Nebo-SVU, generic tower), and the **ERO pack** (ZU-23 Toyota technicals, insurgent ZU-23, SA-2 site
  props). The IDF pack the compilation bundles was already supported via the separate `irondome` toggle
  (identical unit ids).

### Wiring

- **Presets** (`resources/groups/`): new `SA-21/S-400`, `SA-23B/S-300V4`, `SA-10A/S-300PT` (all riding the
  extended S-300 Site layout), `SAMP/T` + `SAMP/T NG` (new `SAMP/T Battery` layout reusing
  `Patriot_Battery.miz` geometry), `Pantsir-SM SHORAD`, `ZU-23 Technicals (ERO)`.
- **Factions**: modern Russia/redfor get S-400 + V4 + Pantsir-SM + Nebo EWRs; russia_1980 gets the S-300PT;
  france_2005 gets SAMP/T; 70s-80s Middle-East/NK reds get SA-7/7b and Vietnam-era + Cold-War reds the
  P-37 Bar Lock (which also closes the
  "red faction has zero EWR units" MANTIS blind-net gap for 16 period factions); insurgents get the ERO
  technicals.
- **MANTIS needs no changes**: the 414th bridge already bands every SAM by Retribution's own emitted threat
  range (overriding MANTIS's `SamData` unit-name scan), so the new units classify correctly from the pydcs
  threat ranges.
- **Bug fixed in passing**: `Faction.remove_vehicle` matches the DCS unit type **id**, but the pre-existing
  HDS strips passed display *names* — so `SAM SA-14 Strela-3 manpad`/`SA-24`/`Polyana-D4M1` were silently
  never stripped when the mod was off. All strips now use ids (upstream-carve candidate).

### Files & tests

| Area | Path |
|---|---|
| Unit registry | `pydcs_extensions/highdigitsams/highdigitsams.py` (new families + retired-unit tombstones) |
| Unit YAMLs | `resources/units/ground_units/` (42 new files, filename = DCS type id) |
| Radar DB | `game/data/radar_db.py` (new TRs/STRs, launcher→tracker pairs, SR/EWR radar labels) |
| Layouts / presets | `resources/layouts/anti_air/S-300_Site.yaml` (extended), `SAMPT_Battery.yaml` (new), `resources/groups/` |
| Mod gating | `game/factions/faction.py` (id-correct strip list), `qt_ui/.../QGeneratorSettings.py` (label + fork-mismatch note/tooltip) |
| Factions | 25+ `resources/factions/*.json` (fixes + era-respecting enrichment) |
| Tests | suite-wide faction/layout loading; headless smoke: all preset units resolve, all factions load with the toggle both ways |

### Gotchas / deferred

- **Needs an in-game pass (checklist N1).** Spawn/engagement of the new sites (S-400/V4/SAMP-T), MANTIS
  banding of the 300+ km launchers, and SA-7 infantry launches can't be exercised headless. (Per squadron
  call, the SA-7/7b are NOT wired into the 4 Vietnam factions — they keep only the P-37; the manpads stay
  on syria_1973/1982, iraq_1991, north_korea_2000, iran_1988 and remain available to custom factions.)
- Detection/threat ranges intentionally mirror the *mod's* numbers, not real-world spec sheets — a 400 km
  40N6E MEZ ring is dominating on any map; treat the `SA-21/S-400` preset as a strategic-tier buy.
- The `SAMPT_MLT` (Aster-15) and Block 2 TELs, the ZPU-2 Toyota variants, and the Gazetchik-decoy UNITS_WITH_RADAR
  entry are **not** loaded/registered — the mod's own `entry.lua` comments the first three out; match it.
- Old saves referencing retired units keep unpickling (classes + YAMLs kept), but a pre-migration campaign
  generating a mission with a retired unit id will fail against the new mod in DCS — start a new game.

## §42 — Local DCS chart base layers (map tiles)

The client map's three stock base layers are real-world Esri imagery, which does not match the terrain DCS
actually models (roads, towns, forests, even coastlines differ). This feature lets a **locally installed**
tile pyramid — e.g. one sliced from Flappie's community "accurate DCS Caucasus map" GeoTIFF, which is drawn
from the DCS terrain itself — appear as an extra base-map choice in the unified map layers panel (§19), so
the campaign map shows what the pilot will actually see in the sim.

**Purely local content, never bundled.** Tiles live under
`Saved Games/Retribution/MapTiles/<name>/{z}/{x}/{y}.png` with a `tileset.json` sidecar (display name, zoom
range, WGS84 bounds, attribution). The server advertises whatever exists there; on machines with no tiles
the panel shows only the three stock buttons and nothing else changes. Copyright is the reason for the
local-only design: community charts are redistributed at their authors' pleasure, so the repo carries the
*tooling*, not the imagery.

### Wiring

- **Tiler** — `tools/tile_geotiff.py`: standalone Pillow-only tool (no GDAL) that slices an **EPSG:3857**
  GeoTIFF into a z5..native XYZ pyramid + writes the `tileset.json`. The georeference is read from the
  TIFF's ModelPixelScale/ModelTiepoint tags; non-Web-Mercator inputs are rejected (no reprojection).
  Native zoom = finest standard zoom at least as fine as the source (Flappie's 39.1 m/px Caucasus → z12).
- **Storage** — `persistency.map_tiles_dir()` → `<Saved Games>/Retribution/MapTiles`.
- **Server** — `game/server/maptiles/`: `GET /map-tiles/` lists installed sets (malformed
  `tileset.json` is skipped with a warning, never fatal); `GET /map-tiles/{name}/{z}/{x}/{y}.png` serves a
  tile or 404s. Game-independent (no campaign loaded required). Traversal-safe: `{name}` is restricted to
  `[A-Za-z0-9_-]+` and z/x/y are typed ints.
- **Client** — `MapLayersControl.tsx`: fetches `/map-tiles/` once on mount; each set adds a segmented
  base-map button (`local:<name>`, persisted like the stock choices). Selected → a react-leaflet
  `TileLayer` pointed at the server URL with the set's bounds/min/maxNativeZoom/attribution; a persisted
  choice whose tiles are gone falls back to Clarity.

### Files & tests

| Area | Path |
|---|---|
| Tiler tool | `tools/tile_geotiff.py` |
| Storage | `game/persistency.py` (`map_tiles_dir`) |
| Server routes | `game/server/maptiles/{routes,models}.py`, registered in `game/server/app.py` |
| Client | `client/src/components/maplayers/MapLayersControl.tsx` + `.css` |
| Tests | `tests/server/test_map_tiles_routes.py` (listing, meta, malformed-meta skip, tile serving, 404s, traversal) |

### Gotchas / deferred

- **Needs an in-app pass (checklist O1):** the chart rendering/alignment over the campaign overlays can't
  be exercised headless, and the client change needs the CI client rebuild.
- The tile pyramid is ~10k PNGs (~0.5 GB) per theater at z12 — regenerate with the tiler, delete the set's
  folder to uninstall. Zooming past the native zoom upscales (maxZoom 19), which is expected to look soft.
- The base-map button appears for every installed set regardless of the loaded campaign's theater — a
  Caucasus chart on a Syria campaign just renders off-map (its `bounds` stop tile requests); switch back
  to a stock base map. Theater-aware filtering is deferred until a second theater chart exists.

## §43 — Per-aircraft flight defaults (save fuel + properties)

The Edit-flight → **Payload** tab's aircraft knobs — **Internal Fuel Quantity**, **Aircraft Condition**,
**Aircraft Wear and Tear**, **Aircraft Type On Spawn**, and any other property-editor value (HMD, ripple,
etc.) — are re-seeded from the pydcs engine defaults every time a flight is created. A player who always
wants (say) their F/A-18C to spawn hot with 80% fuel had to redo those on every package. This feature gives
that box the same persistence the loadout dropdown already has (its **Save Payload** button) and the player
laser code already has (a campaign-wide setting): a **"Save as default"** button that remembers the current
fuel + properties **per airframe**, so every new flight of that type starts pre-configured.

**Opt-in and inert until used.** No Settings toggle — on-disk content is the switch, exactly like the DCS
`UnitPayloads` files. Until a user saves a default for an airframe, nothing changes.

### Wiring

- **Store** — `game/fourteenth/flight_defaults.py`: a JSON file
  (`game/persistency.py` `flight_defaults_path()` → `<Saved Games>/Retribution/flight_defaults.json`),
  keyed by DCS aircraft id → `{"fuel": <kg>, "properties": {<prop id>: <scalar>}}`. **Global** (survives
  across campaigns), **never part of a save game** — the same shape and lifetime as the `UnitPayloads`
  files. Loaded once and cached in a module global (`invalidate_cache()` for tests); the writers keep the
  cache and file in lockstep. `properties` holds only what the user actually set in the property editor (an
  untouched knob isn't stored and falls back to the engine default).
- **Apply** — `apply_flight_defaults(flight)` is called from `Flight.__init__` immediately after
  `initialize_fuel()`, but **only when `roster is None`** (a genuinely fresh flight, never a clone that
  already carries member edits) and **only for the BLUE coalition** (`coalition.player.is_blue` — a `Player`
  enum, never bare truthiness), so enemy AI is never touched. It clamps the saved fuel to the airframe's
  tank and `update()`s each member's `properties`. Everything is best-effort: a missing store (persistency
  not set up in a headless test), a malformed file, or an airframe with no entry is a silent no-op — it can
  never break flight generation.
- **UI** — `qt_ui/windows/mission/flight/payload/QFlightPayloadTab.py`: a row under the fuel slider with
  **Save as default** (captures the selected member's `properties` + `flight.fuel`) and **Clear default**
  (enabled only when a default exists, via `has_defaults_for`). Both confirm with a `QMessageBox`.
- **Payload-tab layout cleanup (2026-07-06)** — the whole tab was regrouped into labeled sections:
  a **Flight members** group (member spinner + the two "same for all" checkboxes; the bold AI-loadout
  warning now only shows while the loadout checkbox is *unchecked*), an **Aircraft settings** group
  (laser codes + property editor in the scroll area — content now top-aligned, the "pre-configured at
  mission start" explainer moved to a tooltip — with the fuel slider + this defaults row pinned below),
  and a labeled **Loadout:** preset row above the custom-loadout editor. Pure layout — no signal/logic
  changes; verified by an offscreen headless instantiation across 7/10/11/12/14-pylon airframes (member
  rebind, warning visibility, custom-loadout round-trip).
  **Follow-up 1 (same day):** the *Aircraft settings* scroll now sizes to its content
  (`AdjustToContents` + `Maximum` size policy, capped at 400px, no layout stretch) instead of taking a
  fixed share of the tab. On an **AI-crewed** flight every F-4-style aircraft property is `player_only`,
  so the property editor renders empty and the box was ballooning into a large blank gap between the
  laser rows and the fuel slider; it's now compact (scroll `sizeHint` ~66px, just the two laser rows).
  A **player** F-4E still grows to fit its 23 controls, bounded at the 400px cap so the full list scrolls
  rather than pushing the loadout off the bottom (verified headlessly: AI F-4E box h=66 vs player F-4E
  h=288, both under the cap; other airframes scale with their property count).
  **Follow-up 2 (same day) — pylon-scroll reverted:** the initial cleanup had wrapped `QLoadoutEditor`'s
  pylon list in its own `QScrollArea` (to kill a hypothetical dead-gap below the last pylon). That
  **collapsed the loadout's size hint**, so the `QEditFlightDialog` (which has no fixed size — it opens at
  its content `sizeHint`) opened shorter *and* trapped the pylons in a mini-scroll — a player F-16
  (12 stations) showed only ~5-6. The pylon grid is now laid out at its **natural full height again** (as
  before the rework), so its size hint drives a tall dialog that shows every pylon at once; the aircraft
  scroll (which *can* shrink) absorbs the squeeze on a short screen. Net: the loadout is the dominant
  element and is never crushed.
- **Display point** — the property widgets already read `member.properties.get(id, default)` (see
  `propertyspinbox.py` / `propertycombobox.py`), so a seeded value shows immediately when the tab opens for
  a new flight — the whole point of the feature.

### Files & tests

| Area | Path |
|---|---|
| Store | `game/fourteenth/flight_defaults.py` |
| Path | `game/persistency.py` (`flight_defaults_path`) |
| Apply hook | `game/ato/flight.py` (`Flight.__init__`, after `initialize_fuel`) |
| UI | `qt_ui/windows/mission/flight/payload/QFlightPayloadTab.py` |
| Tests | `tests/fourteenth/test_flight_defaults.py` (round-trip + reload, BLUE-only apply, red/no-entry no-ops, fuel clamp, clear, missing-persistency silence) |

### Gotchas / deferred

- **Applies to BLUE AI flights too, including fuel.** "Default for this aircraft" means every fresh BLUE
  flight of the type, not only the ones you fly — so a saved sub-full fuel default reduces the starting fuel
  of BLUE AI flights of that airframe as well (same as dragging the slider would). This is intended; it
  mirrors the manual slider and only ever affects your own side. Red is never touched.
- **Captures what's currently in the property editor**, i.e. the selected flight member. With "use same
  loadout for all members" on (the norm), that's uniform; per-member property divergence isn't saved.
- **Needs an in-app pass (checklist Q1):** the button + the "new flight opens pre-configured" behaviour is
  Qt UI that CI can't exercise. The store/apply logic itself is unit-tested.

---

## §44 — Long-range carrier ops

A deterministic carrier strike package for campaigns that park the carrier far beyond the auto-planner's
reach. **Operation Enduring Resolve (COIN)** stands the boat ~800 km off the Helmand AO — the real OEF
Arabian-Sea carrier cycle — and the stock planner never anticipated that standoff.

### The problem

The auto-planner gates every squadron by a plane range check: `Squadron.capable_of` compares the
distance-to-target against `max(aircraft.max_mission_range, settings.max_mission_range_planes)`. With the
carrier 400-500 NM from the Helmand targets and the default range ceiling, **every** carrier squadron is
rejected, so the Hornets, the A-6 tankers, and the E-2 all sit on the deck while the land-based air fights
the whole war. Simply raising the range ceiling gets the Hornets *assignable* to the commander's ATO, but the
theater support planner still won't crew the boat's own tanker/AEWC out there (the tanker orbit sits at the
nearest land field the probe A-6 can't reach, and the AEWC/tanker support packages prune when the
fighter-poor COIN wing can't spare their escorts).

### The fix (two parts)

1. **Range ceiling** — the campaign preseeds a wider `max_mission_range_planes` (600 in Enduring Resolve) so
   the carrier air is *assignable* to the wider war. The commander flies spare Hornets on nearer tasks (SEAD)
   once the deterministic package below has claimed its section.
2. **The deterministic package** — `plan_carrier_strike` (`game/fourteenth/carrier_ops.py`) frags **one**
   carrier package per plan pass from the boat's own squadrons: a Hornet **STRIKE** section
   (`STRIKE_SECTION_SIZE = 2`) + an A-6E tanker + an E-2 on AEW&C. It pins the carrier airframes via
   `ProposedFlight.preferred_type` and forces them through the range gate with `ignore_range=True`, building
   the package through the engine's own `PackageFulfiller` so it gets proper flight plans, waypoints, fuel,
   and a shared TOT. `coalition.ato.add_package(package)` adds the result.

### Wiring

- **Hook** — `game/coalition.py` `plan_missions`, inside a tracer span, calls `plan_carrier_strike`
  **before** `TheaterCommander(...).plan_missions(...)`. Ordering matters: run it first so the boat's Hornets
  are claimed for this package, then the commander flies any spares. Run *after* the commander and it finds no
  Hornets left (the commander spends them on nearer SEAD).
- **Support as PRIMARY flights, not escorts** — the tanker and the E-2 are appended as primary
  `ProposedFlight`s (`FlightType.REFUELING` / `FlightType.AEWC`), never as `EscortType.Refuel` escorts.
  `EscortType.Refuel` is a dead end: `check_needed_escorts` only ever marks `AirToAir`/`Sead` escorts
  "needed", so a refuel escort (and an AEWC escort) always prunes. As primaries the A-6 gets a tanker orbit
  off the boat (launch + recovery gas — ingress/egress/recovery tanking) and the E-2 an AEWC orbit.
- **Target choice** — `_nearest_legal_strike_target` walks the red control points' alive ground objects,
  skips anything ROE-blocked (`game.fourteenth.phases.roe_blocks_target` — the same restraint the rest of the
  BLUE planner honors, so the carrier never gets fragged into a population ring), and returns the nearest,
  **preferring ammo caches** (the COIN cache throttle — thematically the carrier's job) over other strikeable
  TGOs.
- **Selection helpers** — `_friendly_carrier` (the BLUE-owned carrier CP), `_carrier_squadron` (the biggest
  stocked carrier squadron that `capable_of` a task), `_carrier_aircraft` (its `AircraftType`), and
  `_already_planned_from` (one carrier STRIKE package per pass — a commander package that used the boat
  doesn't get doubled).

### Buddy-tanker routing for the boat's other flights

The strike package's A-6 holds one orbit on the carrier's egress corridor. But the commander separately frags
the boat's *other* carrier flights — the SEAD Sweep and SEAD Escort Hornets — in their **own** packages, and
those packages carry no tanker. The stock planner builds their `REFUEL` waypoint from the package geometry
(`RefuelZoneGeometry`, between origin and join), which for a carrier package lands ~500+ NM up-range near the
target, where **no tanker exists**. On the real COIN save the carrier SEAD Hornets' refuel points sat ~560 km
from the A-6 — a dry tank.

`route_carrier_flights_to_buddy_tanker` (run **after** `TheaterCommander.plan_missions`, so the commander
packages exist) fixes this. It finds the carrier's buddy tanker (a `REFUELING` flight off the boat whose
package is *not* a dedicated tanker package), takes its orbit center (`_orbit_center` — the midpoint of the
racetrack/patrol legs), and for every other carrier-departing flight whose package has no tanker of its own
and that carries a `REFUEL` waypoint, pins that flight's refuel point onto the A-6 orbit and rebuilds its
flight plan. Since the A-6 sits on the launch/recovery route, the Hornets now tank from the boat's own held
tanker on ingress top-off and egress recovery.

This mirrors `reposition_theater_tankers` (§tanker demand) but in the other direction: the buddy A-6 is pinned
to the strike package and can't move, so instead of moving the tanker to the receivers, the pass moves the
receivers to the tanker.

- **The override** — `Flight.refuel_point_override` (a `Point`, default `None`, `getattr`-guarded for old
  saves) set by the pass. The three refuel-waypoint builders (`formationattack.py`, `tarcap.py`, `escort.py`)
  build their `REFUEL` waypoint at `flight.refuel_waypoint_position(package.waypoints.refuel)`, which returns
  the override when set and the shared package point otherwise — a one-line, behavior-preserving change for
  every non-carrier flight.
- **Scope guards** — BLUE only; only flights whose `departure` is the carrier; only packages **without** their
  own tanker (so the strike package's own Hornets, which tank in-package, are left alone); land-based flights
  are never touched (verified on the real save — the Kandahar/Bastion flights kept their refuel points).

### Gating

Behind `long_range_carrier_ops` (`Settings`, Campaign Management → Carrier operations, **default OFF**),
BLUE only, guarded at every step — no carrier, no Hornets, no legal target ⇒ silent no-op. Preseeded ON in
`resources/campaigns/coin_enduring_resolve.yaml` alongside `max_mission_range_planes: 600`; every other
campaign is byte-for-byte untouched.

### Files & tests

| Area | Path |
|---|---|
| Planner | `game/fourteenth/carrier_ops.py` (`plan_carrier_strike` + `route_carrier_flights_to_buddy_tanker`) |
| Hook | `game/coalition.py` (`plan_missions`: strike before `TheaterCommander`, buddy-tanker routing after) |
| Refuel override | `game/ato/flight.py` (`refuel_point_override` + `refuel_waypoint_position`); `game/ato/flightplans/{formationattack,tarcap,escort}.py` (builders honor it) |
| Setting | `game/settings/settings.py` (`long_range_carrier_ops` + `_LAYOUT_SPEC` "Carrier operations") |
| Preseed | `resources/campaigns/coin_enduring_resolve.yaml` (`settings:` block) |
| Tests | `tests/fourteenth/test_carrier_ops.py` (off-switch, red no-op, carrier discovery, squadron pick, already-planned guard, ROE-respecting nearest-cache target, buddy-tanker routing); `tests/fourteenth/test_coin.py` (the campaign preseed lock) |

### Gotchas / deferred

- **Engine-probe verified, not yet flown (checklist P2).** The full package build (Hornet strike + A-6 tanker
  + E-2, forced through the range gate) was proven on the real COIN save — `PKG → target = F/A-18C Strike x2 +
  A-6E Refueling x1 + E-2C AEW&C x1`, all off the boat, valid flight plans + shared TOT, with the commander
  also flying spare Hornets on SEAD. The unit tests lock the pure guards/selection; the package build itself
  is not something CI can exercise, so it needs an in-game pass.
- **One package a turn, by design** — `STRIKE_SECTION_SIZE = 2` and the `_already_planned_from` guard keep
  this to a single sustainable coordinated package, not the whole air wing surged off the deck.

## §45 — Support-package F10 orbit markers

At generation, each **blue tanker + AEW&C** orbit is painted onto the F10 / Mission-Editor map as a labelled
racetrack, so a pilot can find their tanker/AWACS in the cockpit. The reliable, **DTC-free** answer to
"where's my gas?" — an object on the shared F10 map every player sees in flight, no cartridge / pre-load /
per-airframe device.

### How it works

`DrawingsGenerator.generate_support_orbits` runs in the drawings pass (`missiongenerator.py`, right after
`generate_air_units`, so `MissionData` is fully populated):

- **Which flights** — `mission_data.flights` filtered to `flight_type in {REFUELING, AEWC}` and
  `friendly.is_blue`. Enemy + non-support flights are skipped.
- **The orbit** — the flight's racetrack ends come from its waypoints: `race_track_start` is emitted as a
  `PATROL_TRACK` waypoint and `race_track_end` as a `PATROL` waypoint (the waypoint builder), so the pair
  defines the leg. Drawn with `add_oblong(start, end, SUPPORT_ORBIT_RADIUS_M)` — a capsule that reads as a
  racetrack — or `add_circle` if the ends coincide. Cyan, dashed (`SUPPORT_ORBIT_LINE`).
- **The label** — `add_text_box` at the racetrack start: `<callsign>  <type>` on line 1, `<freq>  TCN <tacan>`
  on line 2. Callsign/type come from the `FlightData`; freq/TACAN come from the matching `TankerInfo`/
  `AwacsInfo` (looked up by `group_name` — `FlightData` doesn't carry the advertised freq/TACAN). AWACS has no
  TACAN, so that bit drops.

`MissionData` is now threaded into `DrawingsGenerator` (was `mission` + `game` only); a `None` `mission_data`
makes the pass a no-op (so existing/other callers are unaffected).

### Gating

Always-on, like the other F10/ME map drawings (frontlines, routes, CPs, ROE zones) — no Settings toggle. A
toggle (default on) is a possible follow-up if the racetrack clutter is unwanted.

### Files & tests

| Area | Path |
|---|---|
| Painter | `game/missiongenerator/drawingsgenerator.py` (`generate_support_orbits`, `_racetrack_ends`, `_support_label`) |
| Wiring | `game/missiongenerator/missiongenerator.py` (`MissionData` passed to `DrawingsGenerator`) |
| Tests | `tests/missiongenerator/test_support_orbit_drawings.py` (tanker w/ label, AWACS w/o TACAN, non-support/enemy skip, None-data no-op) |

### Gotchas / deferred

- **Emitter-tested + serialize-probed, not yet flown (checklist R1).** The test uses a real pydcs `Mission`
  (so `add_oblong`/`add_text_box` are exercised) and a probe confirmed the drawings serialize into the `.miz`
  table; whether DCS renders the racetrack over the actual orbit needs an in-game pass.
- **Blue-only.** Enemy support isn't marked (it's not intel the player should have for free).
- **Label freq/TACAN depend on the `group_name` match.** If a support flight's `FlightData.group_name`
  doesn't match its `TankerInfo`/`AwacsInfo`, the orbit + callsign still draw but the freq/TACAN line is
  dropped rather than wrong.

## §46 — Route-aware fuel-tank top-up

Long-AO campaigns strand flights the auto-planner frags with too little fuel for the leg. The motivating case
is the COIN **Enduring Resolve** carrier, which sits ~800 km off the Helmand AO: a Hornet on internal fuel
plus its two stock wing tanks still can't make the round trip. This adds drop tanks to a flight at
**mission-generation time** when — and only when — its planned route needs the range, so the COIN Hornet
Strike always comes out with its third bag.

### The safety contract (why it only fills empty stations)

The user's guiding constraint: *don't degrade the loadouts we just restored to upstream.* The blocker to a
"swap a low-value store for a tank" step is that **weapon type can't tell a self-defense missile from primary
ordnance** — an AIM-9X, an AIM-120, a GBU-31, and an AGM-65 all resolve to `WeaponType.UNKNOWN` in the
Retribution model, and the pydcs weapon record carries no category flag. So there is no safe, general way to
identify "the spare Sidewinder" to trade for fuel without risking a TGP, ECM pod, or bomb. The tank-capable
stations that *are* occupied on the reset loadouts hold exactly those things (the F-16's only free tank
station is its ALQ-184 ECM; the Hornet BAI's are Mavericks).

**Therefore the feature only fills stations that are already empty.** By construction it can never remove or
replace a store. That still hits the goal: the reset upstream Hornet **Strike** leaves the centerline empty,
so a COIN Hornet Strike gains its third tank there with zero swaps. A fully-loaded jet (the F-16, the Hornet
BAI) is simply left as-is — under-fueled-but-intact beats gutted.

### How it works

`add_range_fuel_tanks(flight, loadout, settings)` (`game/fourteenth/range_fuel.py`) runs in
`FlightGroupConfigurator.setup_payload`, **after** the date-degrade and **before** the pylons are equipped:

1. **Guards** — no-op unless `settings.auto_range_fuel_tanks`, and always a no-op for a `is_custom` loadout
   (respect explicit player edits), an empty/clean loadout, or a missing flight plan.
2. **Required fuel** — `_required_fuel_lbs = taxi + cruise·route_nm + min_safe`, using the airframe's measured
   `fuel_consumption` or the synthesised `estimated_fuel_consumption` that every airframe has (so it works
   fleet-wide). `route_nm` is the summed leg length of the flight-plan waypoints. Tankers on the route are
   **intentionally ignored** — we would rather over-fuel (an unused tank) than under-fuel.
3. **Available fuel** — internal `max_fuel` (kg→lb) plus the parsed capacity of any tank already on the
   loadout. If available ≥ required, return the loadout unchanged.
4. **Fill** — walk the airframe's empty, tank-capable stations in order, adding a tank to each (matching a tank
   already on the jet for consistency, else the largest compatible tank) until available ≥ required or no
   stations remain. Returns a **new** `Loadout` — the persisted ATO loadout is never mutated, so it is
   re-evaluated every turn as routes move and saves are untouched.

**Tank detection** has no `WeaponType` to lean on, so `is_fuel_tank` matches the DCS display name with a
narrow regex (`fuel tank`, `drop tank`, `external tank`, `gal`/`gallon`, `liter fuel`, `kg fuel`, `PTB-`, …)
that deliberately excludes a "Color Oil Tank" or a fuel-air bomb, and skips the `(Empty)` ferry shells.
`tank_capacity_lbs` parses the number + unit from the name (gallons ×6.7, liters ×1.75, kg ×2.205; a 2000-lb
default when the name gives no number).

### Gating

`auto_range_fuel_tanks` — Mission Generation → Loadouts, **default ON**. It is inert on short-range routes
(internal + stock tanks already cover the leg), so it only acts where a route genuinely exceeds internal fuel.
No campaign preseed is needed (default ON already reaches the COIN campaign).

### Files & tests

| Area | Path |
|---|---|
| Core | `game/fourteenth/range_fuel.py` (`add_range_fuel_tanks`, `top_up_for_route`, `is_fuel_tank`, `tank_capacity_lbs`, `route_length_nm`) |
| Hook | `game/missiongenerator/aircraft/flightgroupconfigurator.py` (`setup_payload`) |
| Setting | `game/settings/settings.py` (`auto_range_fuel_tanks`) |
| Tests | `tests/fourteenth/test_range_fuel.py` (fills an empty tank station on a far route; **never removes/replaces a store**; short-route/empty/custom/setting-off no-ops; tank detection + capacity; route length) |

### Gotchas / deferred (checklist S1 — needs an in-game pass)

- **Fill-empties only, by design.** A jet whose tank stations are all occupied gains nothing (the F-16 with 2
  tanks + ECM, the Hornet BAI with Mavericks on every wing station). Reaching a higher tank count on those
  would require dropping a store, which can't be made safe generically (see the safety contract) — deferred as
  an explicit opt-in if ever wanted.
- **Estimate, not a measurement.** The synthesised fuel model is a planning approximation; the trigger is
  intentionally generous (ignores tankers) so it errs toward carrying a tank rather than launching short.
- **Generation-time only.** The added tank shows in the `.miz`, not in the in-app loadout editor (which shows
  the base ATO loadout). Fine for AI; a player who wants to see/adjust it edits their loadout (which then
  becomes `is_custom` and is left alone).

---

## §47 — Continuous campaign clock & weather

A stock turn advanced the campaign by re-rolling two things from scratch: the time-of-day rotated through a
fixed **Dawn → Day → Dusk → Night** slot cycle (one slot per turn) with the *actual* clock picked as a
**random hour inside that slot's band**, so consecutive turns teleported ~4–8 h with no continuity, and the
date only ticked once every four turns (`start_date + turn // 4`). Weather was an **independent, memoryless
draw** each turn from the season's probability table — a thunderstorm could be followed by clear skies followed
by rain, with no fronts moving through. Neither system carried any state forward, so a campaign never felt like
one continuous timeline.

This ties date, time-of-day, and weather to **one marched clock** anchored to the campaign's chosen start date,
so the war flows: the clock steps forward a believable few hours each turn, the date rolls over at midnight, and
weather systems roll in and clear over several turns. It composes cleanly with the campaign-phases arc (§40),
which already advances over turns — the calendar now advances in step instead of jumping.

### The two levers

1. **Continuous clock (`Conditions.advance`).** Instead of "slot rotation + random hour," the actual
   `start_time` is carried forward from the previous turn's conditions and advanced by a jittered interval —
   `random.randint(MIN_TURN_ADVANCE_HOURS, MAX_TURN_ADVANCE_HOURS)` = **3–7 whole hours** (a sortie plus
   turnaround; whole hours keep the "missions start on the hour" property). **Time of day is then *derived*
   from the marched clock** via `daytime_map.best_guess_time_of_day_at`, and the date rolls over naturally as
   the clock crosses midnight — the season (and thus the weather table + temperature/pressure interpolation)
   updates on its own as the calendar marches through the months.

2. **Weather with memory (`Conditions._evolve_weather_type`).** The archetypes sit on a severity ladder
   `_WEATHER_LADDER = [ClearSkies, Cloudy, Raining, Thunderstorm]`. When a `previous` weather is passed, the next
   turn is a **Metropolis–Hastings** step: a *proposal* drawn from `_WEATHER_PERSISTENCE_KERNEL[distance]`
   (`{0: 3.0, 1: 1.0, 2: 0.3, 3: 0.1}`, distance = rungs from the previous archetype — a strong pull to stay,
   moderate to step one rung, small to jump), then *accepted* against the seasonal chances with probability
   `min(1, (chance_j · Z_i) / (chance_i · Z_j))` (the `Z` terms normalise the per-rung proposal; the kernel
   cancels). With no `previous` (turn 0 seed, or the legacy path) the draw is the original memoryless behaviour,
   byte-identical.

   **Why MH and not a plain reweight.** The obvious "multiply each seasonal chance by the kernel and draw"
   makes weather autocorrelated but **skews the long-run climatology** toward the calm end — a symmetric kernel
   over asymmetric seasonal weights pools probability in the common states. Measured on real Caucasus-summer
   chances (`clear 55 / cloudy 35 / rain 10 / storm 1`), the naive reweight **more than halved the rain
   frequency** (9.9% → 4.7%) and cut storms to a sixth. MH fixes the marginal exactly: the accept step gives
   the chain a stationary distribution equal to the seasonal chances, so over a long run the authored rain/storm
   frequencies are preserved (measured skew ≤ ~1pp) **and** a zero seasonal chance is still never reachable —
   while the near-rung proposal keeps transitions gradual (measured: stay-same ~75–80%, jumps ≥2 rungs ~1–3%,
   mean dwell ~4–5 turns, vs ~40% / ~14% / ~1.6 turns memoryless). The
   `tests/weather/test_continuous_campaign_clock.py` chain tests pin both properties.

### Wiring

- `Game.continuous_clock_active` gates the whole feature: `getattr(settings, "continuous_campaign_clock",
  False)` **and** `settings.night_day_missions == NightMissions.DayAndNight`. The day-only / night-only mission
  settings explicitly opt out of the natural cycle, so they fall back to the per-turn rotation; the `getattr`
  keeps pre-feature saves on the legacy path.
- `Game.current_day` / `Game.current_turn_time_of_day` become authoritative off `self.conditions` when the
  clock is active (`conditions.start_time.date()` / `conditions.time_of_day`), else the legacy `turn // 4` /
  slot-rotation formulas. Both `getattr`-guard `conditions` because it isn't built yet during the turn-0 seed
  (which reads these properties → legacy path → identical seed).
- `Game.finish_turn` calls `advance_conditions()` (→ `Conditions.advance`) instead of `generate_conditions()`
  when the clock is active, for `turn > 1` (turn 0 and 1 still share the seed, unchanged).

### Save compatibility

`Settings.__setstate__` builds a fresh `Settings()` and overlays the old state, so an existing save picks up
`continuous_campaign_clock=True` on load. This is **seamless mid-campaign**: the last conditions were generated
from `current_day` (the `turn // 4` date), so `conditions.start_time.date()` already equals that date — the
clock reads the same date and simply begins marching forward from there. No jump, no migration entry needed.

### Gating

`continuous_campaign_clock` — Campaign Management → **Campaign clock & weather**, **default ON**. Turning it
off restores the stock per-turn rotation + memoryless weather exactly. Requires day-and-night missions (above).

### Files & tests

| Area | Path |
|---|---|
| Clock + weather | `game/weather/conditions.py` (`Conditions.advance`, the `previous=` path in `generate_weather` → `_evolve_weather_type` MH step, `MIN/MAX_TURN_ADVANCE_HOURS`, `_WEATHER_LADDER`, `_WEATHER_PERSISTENCE_KERNEL`) |
| Game wiring | `game/game.py` (`continuous_clock_active`, `advance_conditions`, `current_day`, `current_turn_time_of_day`, `finish_turn`) |
| Setting | `game/settings/settings.py` (`continuous_campaign_clock`) |
| Tests | `tests/weather/test_continuous_campaign_clock.py` (monotonic march within the 3–7 h band; time-of-day derived; date rolls at midnight; weather biased toward the previous rung; zero seasonal chance still honoured; memoryless without `previous`) |

### Gotchas / deferred (checklist T1 — needs an in-game pass)

- **Atmospheric continuity is archetype-level, not fine-grained.** Pressure/temperature/wind are still
  instantiated fresh per turn (anchored to seasonal + time-of-day averages), so they don't wildly swing while
  the archetype is stable, but a persistent low-pressure *system* carried numerically across turns is a
  possible follow-up. Archetype persistence is the dominant visual signal and is what this ships.
- **Day-only / night-only opt out.** By design — those settings mean "I don't want the natural cycle." The
  continuous clock only runs under day-and-night missions.
- **Interval is fixed-band, not a setting.** The 3–7 h advance is a module constant; exposing it as a tunable
  is a trivial follow-up if the pacing wants tuning after an in-game pass.

## §48 — Commitment ceiling (will-coupled war budget)

The **model-3 capstone of the 2026-07-04 "morale ratchet" will redo** (design note
`docs/dev/design/414th-vietnam-political-will-roe-notes.md` §8). The political-will economy (§40 / the
Vietnam campaign layer) decides the war at the negotiating table, but until a side actually breaks, a
flagging war had no *material* cost — you kept the same income whether the home front was behind you or
not. Historically it was the opposite: in Victory Games' *Vietnam 1965-1975*, **US commitment can never
exceed morale** — as morale falls, forces are drawn down and the war is taken out of your hands.

This couples the will economy to the BLUE war budget. As **Political Will** falls below
`CEILING_FULL_WILL` (60), `Coalition.end_turn`'s income is scaled down linearly toward
`CEILING_FLOOR_MULT` (0.5× at will 0) — Congress trims the war budget, so a losing war is starved of
replacements. Full funding while will stays high; the cut only bites once patience is already low, and
the floor keeps *some* budget flowing (it pressures, it never hard-locks procurement). BLUE only
(Washington's appropriation; the insurgent-style regime is not coupled — the VG asymmetry).

**Files.** `game/fourteenth/commitment_ceiling.py` (`will_budget_multiplier` + `apply_commitment_ceiling`),
hooked at the one BLUE income site (`game/coalition.py` `Coalition.end_turn`). Setting
`vietnam_commitment_ceiling` (Vietnam Ops page, "Campaign" section, default OFF, preseeded ON in
`1968_Yankee_Station.yaml`); gated **also** by `vietnam_political_will` (no will economy ⇒ nothing to
couple to). Off with either toggle ⇒ income is returned untouched, so non-Vietnam campaigns and
pre-feature saves are unaffected. Messages the player on the turn the budget is cut, so the draw-down is
legible.

**Companion pieces of the same redo (not §48, documented in the design note §8):** the *escalation tax*
(`CampaignPhase.blue_will_on_entry` — widening the war costs will even when sanctioned; charged once per
phase entry via `phases.consume_phase_escalation_cost`, surfaced in the will ledger from
`political_will._blue_moves`), the ratchet re-weighting of the whole `will:` block, and the offline
`tools/will_pacing_model.py` projector used to derive the numbers.

**Tests.** `tests/fourteenth/test_commitment_ceiling.py` (multiplier shape + BLUE-only/both-toggle gating +
message), the escalation-tax tests in `tests/fourteenth/test_phases.py` /
`tests/fourteenth/test_political_will.py`, the pacing-tool guard `tests/fourteenth/test_will_pacing_model.py`,
and the campaign guards in `tests/test_vietnam_content.py`. In-game passes: checklist **M1** (will pacing)
+ **M9** (commitment ceiling draw-down). Needs an in-game pass.

## §49 — Mobile missile relocation (the SCUD hunt)

A mobile theater-missile site — a SCUD/SSM group, `TheaterGroundObject.category == "missile"` — has
always spawned parked exactly where the campaign map says it is, every mission, forever. "Hunting" it
was flying to a coordinate. Real shoot-and-scoot launchers were the archetypal Desert Storm needle in a
haystack: the Weasel/SCUD hunt is a hunt precisely because the target *moves*. With the concealment
layer (§3 `concealed_enemy_forces`) already denying the exact map position until recon localizes it,
the last missing half was the launcher itself sitting still once you got there.

### How it works

**Emitter (`game/missiongenerator/mobilemissileluadata.py` `populate_mobile_missiles_lua`).** When the
`mobile_missile_relocation` setting is on, every `category == "missile"` TGO (both sides) with at least
one **alive vehicle** emits its drivable `TheaterGroup.group_name`s + the TGO's campaign position as
`dcsRetribution.mobileMissiles = { sites = { {groups, x, y}, … } }`. **The `coastal_missile_relocation`
setting (default OFF) opts `category == "coastal"` sites — Silkworm-style anti-ship batteries — into the
same set**, a naval-campaign lever (the Tanker War turns it on) so a shore battery is never quite where
the last recon photo froze it either; the two categories compose (either, both, or neither), feeding the
same category-agnostic plugin. Statics-only or fully-dead sites are skipped; anti-air (the MANTIS-run SAM
network) and buildings are other categories entirely and are **never** emitted — the IADS never moves. No
sites (or both settings off) ⇒ no node ⇒ the plugin no-ops.

**Runtime (`resources/plugins/mobilemissiles/`).** One scheduled loop per site: after a startup grace
(default 120 s), every alive group of the site drives (alarm-green + weapons-hold — they relocate, they
don't stop to fight) to a fresh `mist.getRandPointInCircle` point within the **scoot radius** (default
4 km) of the site's **campaign-map centre**, re-rolled every `scootIntervalS` (default 480 s). Anchoring
the wander on the campaign position (not the last waypoint) means the site works its area but never
migrates — threat rings and the turn-boundary model stay honest. A destroyed site stops being routed.
Options: interval, radius, speed, grace.

**Movement only** (the Combat-SAR / COIN mover discipline): the routed DCS groups are the force model's
own spawned units, so kills record natively; nothing changes at turn end; there is no Lua-owned scoring
or spawning. Composes with §3 concealment (the map shows "in here somewhere", and when you get there the
launcher has moved within its patch) and §5 Approximate mode (fuzzed steerpoints against mobile SAMs —
same philosophy, different object class).

### Files & tests

| Area | Path |
|---|---|
| Emitter | `game/missiongenerator/mobilemissileluadata.py` (wired in `luagenerator.py` after the COIN emitter) |
| Runtime | `resources/plugins/mobilemissiles/` (`plugin.json` + `mobilemissiles-config.lua`) |
| Setting | `game/settings/settings.py` (`mobile_missile_relocation`, Mission Generation → World & systems, default **ON** — the toggle is the kill switch) |
| Coastal opt-in | `coastal_missile_relocation` (Mission Generation → Battlefield life, default **OFF**) — adds `category == "coastal"` (Silkworm) sites to the scoot; the naval-campaign lever, preseeded ON in the Tanker War (§Persian Gulf — The Tanker War) |
| Tests | `tests/missiongenerator/test_mobilemissileluadata.py` (emit shape, category/dead/static gates, setting gate); `tests/lua/test_mobilemissiles_runtime.py` (grace, per-group scoot around the anchor, destroyed-site stop, no-node no-op) |

### Gotchas / deferred

- **Default ON.** Movement-only, pcall-guarded, and node-gated, so the blast radius of a failure is "the
  launchers don't move" — but it does change every campaign with missile sites; the setting is the kill
  switch (the §40 `campaign_phases` precedent). In-game pass: checklist **S2**.
- **The SAM network is out by construction.** Only `category == "missile"` is emitted. Do not extend this
  to SAM TGOs without solving the MANTIS-emitter-position question first.
- **A campaign must actually place a missile TGO** or this is inert. **Germany — Red Tide** is the first
  414th campaign to do so on purpose: its laydown carries **two red SS-1C Scud-B batteries** (a forward
  one off Haina, a rear/mid one near Wittstock) and preseeds `mobile_missile_relocation: true` + the
  `mobilemissiles` plugin, so the SCUD hunt is live there (see the Red Tide design note).
- **DCS pathing risk.** A site authored in rough terrain may fail to path off-road; worst case the group
  sits (status quo ante). Watch dcs.log for repeated goRoute failures on the pass.
- **Movement bug fixed 2026-07-09.** The first flown Red Tide test found the launchers **never moved**
  (Tacview: a single position record for all 6 `Scud_B`) despite `shoot-and-scoot armed` and **no**
  error. Root cause: `driveTo` built a **1-waypoint** `mist.goRoute` (destination only), and a DCS ground
  group needs its route to START at its current position or it reads as "already there" and never drives
  — MIST's own `groupToRandomZone` prepends the lead position (2 WPs). Fixed to a 2-WP route
  `{ buildWP(lead:getPoint()), buildWP(dest) }`. **The identical `driveTo` in `coin-config.lua` had the
  same bug** (copy-paste) so every COIN mover was silently affected too (§P4/P8, all "untested"). The
  fix is strictly more correct (start=current is always valid, so it can't regress a working mover);
  the harness tests assert `points == 2`. Needs an in-game re-fly (the harness fakes goRoute). See the
  memory note `dcs-ground-movers-need-2wp-route`.
- **Deferred:** per-side gating (currently symmetric), and coupling the *fired* missile events to a
  scoot-away reaction (real shoot-THEN-scoot needs an S_EVENT_SHOT hook — v2 if the wander plays well).

## §50 — Convoy ambush (a chance, never telegraphed) + ambient supply convoys

The **mirror of the §35 Vietnam-Ops convoy interdiction.** Interdiction gives the player *enemy* convoys
to hunt (fly Armed Recon, kill the trucks, deny the enemy reinforcements). This gives the player *friendly*
convoys that might need protecting: real BLUE supply columns run the roads behind the front, and —
**sometimes; it is a chance roll, never a certainty** — hidden RED ambush teams dig in along their route:
one contact, or a gauntlet of five or six down the same road. **Nothing is telegraphed in the Retribution
UI** (reworked 2026-07-06 from the original always-one-ambush + auto-fragged-escort design, per the
squadron call): the convoy looks like any other friendly convoy, the ambush teams have **no map presence
at all** (no marker, no §3 uncertainty circle, nothing to right-click or plan against), and **no escort
package is auto-fragged into the ATO**. The first sign of trouble is the in-mission "TROOPS IN CONTACT"
call when an ambush springs — and supporting the column (or not) is the player's decision.

**Standardized to every campaign the same day (the ambient-convoy layer).** The squadron call: convoys
present in every miz, both sides, "a few convoys per side, some on the same route, some on different
routes, randomized — don't force numbers." `game/fourteenth/ambient_convoys.py` `ensure_ambient_convoys`
tops **each side's** convoy flow up to a `randint(MIN_AMBIENT_CONVOYS, MAX_AMBIENT_CONVOYS)` (1..3) target
every turn on **randomly chosen DISTINCT** same-side corridors (`_RNG.sample` — one column per road, the
count capped at the road count); organic transfers and the §35 trail convoys count toward the target, so
nothing stacks on top of existing traffic. **Distinct roads, one transfer per corridor (2026-07-07 S5 fix).**
The convoy map keys transports by `(origin, destination)` (`TransportMap.add` in `game/transfers.py`), so two
transfers on the SAME corridor **coalesce into one oversized group** that line-spawns into unauthored
positions and **deadlocks** at mission start — the flown S5 regression (a 24-vehicle blue column parked at
Baghdad the whole mission, which also blocked the §50 ambush spring). Sampling *distinct* corridors keeps
every column a separate, driveable group; it trades away the originally-sketched "some columns share a road"
texture, which the merge made unachievable anyway (a shared road was never two columns — it was one parked
blob). Corridors are enumerated once per road and oriented rear→front off the §35 `_reference_points`
(fronts, or the opposing CPs on a front-less laydown); each column carries the real units already in its rear
base's roster. **Skim-only — no free unit seeding
(2026-07-07 design call).** Ambient columns **relocate** existing rear units (`_skim_units`) and never call
`commission_units` to invent free ones. The §35 Vietnam trail's `_seed_trail_source` external-logistics
free-seed is *right for that feature* — red-only, Vietnam-gated, the Ho Chi Minh Trail's documented
character — but generalizing it here would top up **both** sides' rear bases with un-budgeted units every
turn on **every** campaign (up to ~48 net-new free ground units/turn game-wide, permanently reinforcing
front-ward bases), which the squadron never asked for: they asked for *traffic to hunt and protect*, not a
free-reinforcement firehose. So a rear base too thin to skim (< 2 armor) simply yields no column that turn
(`new_transfer` debits the source immediately, so re-picking a source in the loop reads its live stock).
This **replaces the old blue-only `ensure_blue_escort_convoy`**: the
ambush roll below covers every blue convoy whatever created it, and red's ambient columns are ordinary
Armed Recon / BAI targets. Gated `ambient_supply_convoys` (Mission Generation → Battlefield life, default
**ON**); a side with no same-side road (island maps, all-red graphs) is a silent no-op. Both `convoy_ambush`
and `ambient_supply_convoys` default **ON** (the §49 kill-switch precedent; existing saves keep stored
values, and the new field arrives ON via the `Settings.__setstate__` default merge).

### No phantom spawns (the §35/§37 lesson)

The whole feature is built on **real, tracked units** so every loss is reconciled natively — the exact
discipline the interdiction and Super Gaggle reworks established:

- **The convoy is a real `coalition.transfers` transfer.** Its destruction is units that never arrive:
  `MissionResultsProcessor.commit_convoy_losses` already iterates *both* coalitions' convoys and calls
  `convoy.kill_unit`, and the debrief recognizes `convoy.player_owned.is_blue`. So a blue convoy shot up in
  an ambush costs the player real reinforcements — no new loss plumbing.
- **Each ambush team is a real, map-hidden red TGO** placed by `game.fourteenth.coin.spawn_red_ground_at`
  (the same reusable spawn the COIN dispersed cells / IEDs / HVTs use) at an arbitrary land point, anchored
  to a red CP for allegiance. Killing it is a real red ground loss in the debrief.

The Lua plugin therefore owns **no** kills. It only decides *when* a dug-in team opens up.

### The `map_hidden` visibility flag

The §3 `concealed` circle would still advertise "something is on this road", so the ambush teams introduced
a stronger leaf on the viewer-aware visibility layer: `TheaterGroundObject.map_hidden` (pickle-safe,
`setdefault` in `__setstate__`). While set, `hidden_on_player_map(viewer)` returns True for any enemy
viewer **unconditionally** — no reveal key, unlike the SCAR command posts — so the site never reaches the
client (`TgoJs.all_in_game` skips it, and `GameUpdateEventsJs.from_events` now filters `updated_tgos` the
same way, closing the SSE leak where a debrief-time unit kill would have pushed the hidden TGO to the map),
never gets an F10 mark (`triggergenerator._gen_markers` already gates on the same leaf), and is skipped by
`BattlePositions.for_control_point` so **neither side's HTN planner frags a package against it** (a blue
AI BAI package in the ATO would have revealed it). `viewer=None` (AI/threat math) and the §18 fog-reveal
debug toggle still see ground truth.

### How it works

**Force model (from `Game.finish_turn`, in order: the §35 trail top-up → ambient convoys → ambush seeding):**

- `ensure_ambient_convoys` (`game/fourteenth/ambient_convoys.py`) — both sides, the randomized top-up
  described above. Reuses the §35 coalition-generic helpers `_reference_points` + `_skim_units` (skim-only —
  it does **not** call `_seed_trail_source`, so no free units are commissioned) with its own
  `_same_side_corridors` enumeration; `AMBIENT_CONVOY_UNITS` (8) per column. The dice live in a module-level
  `_RNG` so tests script them.
- `seed_convoy_ambushes` (`game/fourteenth/convoy_ambush.py`) — despawns last turn's ambush teams first
  (an ambush is a one-mission event —
  cleared or run-past, it does not persist; reuses `coin._despawn`/`_tgo_by_id`), then **rolls each active
  blue convoy against `AMBUSH_CHANCE` (0.5)**. A convoy that misses the roll drives a quiet road. A convoy
  that hits gets `randint(MIN_AMBUSHES_PER_ROUTE, MAX_AMBUSHES_PER_ROUTE)` (1..6) teams of
  `AMBUSH_TEAM_SIZE` (4) — each a `map_hidden` red `GroupTask.FRONT_LINE` TGO placed by `_ambush_points`:
  stratified-random slots along the route polyline inside `ROUTE_END_MARGIN` (15 %) of either endpoint,
  **interpolated along the road's segments** (`heading_between_point`/`point_from_heading` — the authored
  corridors carry only 3–5 waypoints, far fewer than the teams they can host), so a six-team roll reads as
  a spread gauntlet of separate contacts, never a stack. Records `{tgo_id, convoy}` pairings on
  `game.convoy_ambush_state` (declared in `Game.__init__`, `setdefault` in `__setstate__` for old saves).
  The dice live in a module-level `_RNG` so tests script them.

**No auto-frag.** The old `plan_convoy_escort` hook (a BAI package auto-fragged from
`Coalition.plan_missions`) is **deleted** — an ATO package pointing at the ambush would both telegraph it
and take the decision away from the player. If the player wants air over the column, they frag it
themselves (or divert something already airborne when the TIC call comes).

**Emitter (`game/missiongenerator/convoyambushluadata.py` `populate_convoy_ambush_lua`, wired in
`luagenerator.py` after the mobile-missile emitter).** For each live pairing it emits the ambush team's
alive `group_name`s + centre and the targeted convoy's group name (the generated `VehicleGroup` name =
`convoy.name`) as `dcsRetribution.convoyAmbush = { ambushes = { {groups, x, y, convoyGroups}, … } }`. A
pairing whose TGO is gone or fully dead is dropped; setting off ⇒ no node ⇒ plugin no-ops.

**Runtime (`resources/plugins/convoyambush/`).** One scheduled loop per ambush team. The team starts dug
in — alarm-green + weapons-hold (all ROE calls `pcall`-wrapped). After a startup grace (default 120 s) it
polls every `pollIntervalS` (15 s): when any convoy unit closes inside `triggerRadiusM` (6 km) of the
ambush centre it **springs** — weapons-free + alarm-red, one "TROOPS IN CONTACT — support welcome" cue to
BLUE, one F10 mark on the position, then latches. A team the convoy never reaches (or whose convoy is
already gone) **stays dug in and silent** — the old max-hold "spring anyway" fallback is removed, because
a TIC call with no convoy under fire would telegraph a fight nobody drove into. A team wiped before it
springs stops scheduling.

### Files & tests

| Area | Path |
|---|---|
| Force model | `game/fourteenth/ambient_convoys.py` (`ensure_ambient_convoys`, both sides) + `game/fourteenth/convoy_ambush.py` (`seed_convoy_ambushes`), hooked in order in `game/game.py` `finish_turn` |
| Visibility | `game/theater/theatergroundobject.py` (`map_hidden` + the `hidden_on_player_map` leaf), `game/server/eventstream/models.py` (SSE filter), `game/commander/battlepositions.py` (planner skip) |
| State | `game.convoy_ambush_state` (declared in `Game.__init__`, `setdefault` in `__setstate__`) |
| Emitter | `game/missiongenerator/convoyambushluadata.py` (wired in `luagenerator.py` after the mobile-missile emitter) |
| Runtime | `resources/plugins/convoyambush/` (`plugin.json` + `convoyambush-config.lua`; registered in `plugins.json`) |
| Settings | `game/settings/settings.py` (`ambient_supply_convoys` + `convoy_ambush`, Mission Generation → Battlefield life, both default **ON**) |
| Tests | `tests/fourteenth/test_ambient_convoys.py` (the randomized both-sides top-up, same-road stacking, corridor orientation, COIN kit, every guard); `tests/fourteenth/test_convoy_ambush.py` (the chance roll + gauntlet placement + the map_hidden contract + the `ROAD_BEARING_CAMPAIGNS` inventory guard); `tests/missiongenerator/test_convoyambushluadata.py` (emit shape/gates); `tests/lua/test_convoyambush_runtime.py` (grace, spring-on-close, silent-without-convoy, dead-team, no-node) |

### Gotchas / deferred

- **Support is an emergent job, not a computed one.** There is no "is escorted" flag — the ambushers
  engage the convoy whenever the DCS AI can, and clearing them is whatever air the player brings (a
  pre-fragged CAS of their own, or a diversion when the TIC call comes). Losing the convoy is a campaign
  consequence surfaced in the SITREP, not a modal event.
- **The chance is rolled at the turn boundary, not in-mission.** `seed_convoy_ambushes` rolls the dice
  when the turn is finalized, because the teams must be real units in the force model and the `.miz`.
  From the cockpit it is indistinguishable from an in-mission roll — nothing about the outcome is
  visible anywhere until an ambush springs.
- **Plugin dependency (the §36 lesson).** The ambush runtime is the `convoyambush` plugin; a saved default
  of it unticked silently kills the `convoy_ambush` setting (the ambient convoys themselves are pure engine
  and need no plugin). The four flagship campaigns still preseed `plugins: {convoyambush: true}` (and the
  setting, now redundantly — kept as explicit intent that forces it ON over a user's saved-off default).
- **Standard since 2026-07-06:** both settings default **ON** for new games (existing saves keep their
  stored `convoy_ambush` choice; `ambient_supply_convoys` arrives ON via the `__setstate__` default merge).
- **A blue→blue supply road is the hard prerequisite for the blue half** (found by the 2026-07-05 flown
  test): with an all-red supply graph no blue convoy — and with it the entire ambush loop — can ever
  exist. Both COIN campaigns originally shipped exactly that way; their blue rear corridors are
  geo-authored (`tools/supply_route_geo.py`: ER Kandahar↔Camp Bastion up Highway 1 — the literal
  ambush alley; IR Baghdad↔Balad + Baghdad↔Al-Taquddum). The **2026-07-06 standardization survey** loaded
  all 67 shipping campaigns: **27 bound a blue→blue road** natively, and the **same-day batch-1
  corridor-authoring pass** (`BATCH1_BLUE_REAR` in `tools/supply_route_geo.py` — every route a real
  highway traced by lat/lon per the driveable-corridor standard, spliced into the campaign yamls and
  headless-verified to bind its intended blue pair) **added 21 more** across ten maps: the Tbilisi
  Kakheti-Highway hop (TblisiGap, Vectron's Claw), west Georgia's E60/S2 (Battle4Georgia,
  Kutaisi2Vaziani), Anapa↔Novorossiysk (Slava Ukraini), the Turkish O-52/E91 rear (Long Road to H3,
  Syria full map, Aleppo Insurgency, Battle4SyriaNorth), the H4↔H3 pipeline highway (Task Force
  Thunder), US-95 (Battle4area51), the UAE E11 (Noisy Cricket ×2, Scenic Merge), Israel's route 40
  (Gazelle) + the Egyptian Delta (Red Sea Rising), the Baghdad ring (Desert Aladeen), Highway 1
  Kandahar↔Bastion (Shattered Dagger), Guam's Marine Corps Drive (Velvet Thunder — the red-side §35
  no-op there is unchanged), the New Forest A-roads (Final Countdown 2), and the Swedish/Norwegian
  E10/E45/E6 chain (Anvil of War). **48 of 67 campaigns** now field the feature; the remaining **19 are
  genuine no-ops** (0–1 blue land control points, or a blue pair separated by sea/strait — the Falklands
  set, Peace Spring's Cyprus rear, Abu Dhabi/PG-Wargames' Hormuz split, Caen-to-Evreux's Channel — plus
  Caucasus_Multi_Russia and Syrian Shield, whose only blue pairs would need a corridor through the red
  heartland, deferred as a judgment call). All 48 are CI-locked as `ROAD_BEARING_CAMPAIGNS`
  (`test_road_bearing_campaign_keeps_its_blue_road` loads each theater;
  `test_batch1_corridor_campaigns_are_in_the_inventory` keeps the tool and the inventory in lockstep),
  so a laydown edit can't silently drop a road; when a new corridor is authored, ADD the campaign to
  the inventory.
- **A red→red road is the same prerequisite for the red half** — no red road, no red ambient convoys, and
  no columns for the player to interdict. The **batch-2 pass (2026-07-07, `BATCH2_RED_REAR` in the tool)**
  authored red rear corridors for the **nine campaigns** whose red side had none: the Aleppo belt
  (Aleppo↔Kuweires↔Jirah + the M5/Azaz legs) for WRL Aleppo Insurgency and Battle4SyriaNorth (which also
  gets its Turkish FOB line E91/O-52 chain), the Iranian mainland highways (Bandar Abbas↔Kerman via
  Sirjan, Bandar Abbas↔Shiraz via Lar/Jahrom, Shiraz↔Bushehr via Kazerun) for both Noisy Crickets,
  Cyprus's A1/A2/A5 motorways for Aegean Aegis, the Calais N43/E40 for Operation Dynamo (the tool's first
  TheChannel terrain), the **Enduring Resolve ratline reused verbatim** for Shattered Dagger (same
  laydown — ER is its fork; minus the blue Kandahar↔Bastion entry batch 1 already gave it), Saipan's
  Middle Road + Tinian's Broadway for Velvet Thunder (island-internal — so the §35 "no red trail" note
  there softens: red convoys now exist per island), and the Guam road — red-owned there — for Pacific
  Repartee. All headless-verified to bind; guarded by `test_batch2_campaign_keeps_its_red_road`
  (parametrized straight off the tool table). After both batches, **every campaign fields at least one
  side's convoys** except the few with no two same-side land bases anywhere.
- **Ambush is BLUE-only; ambience is symmetric.** The ambush teams target the player's convoys (red's
  ambient columns are instead the player's Armed Recon/BAI targets — §35 from the other side). A symmetric
  red-convoy ambush (AI escorting its own columns against player-hunts) stays deferred.
- **Light raiders, capped (2026-07-09).** A flown Red Tide test flagged the ambush as "excessive, and the
  enemy should be light — trucks, infantry, rockets — not MBTs in our backline." Two fixes: (1) the teams
  were `GroupTask.FRONT_LINE` **armor** (MBT groups); they now re-type to a **light raider kit**
  (`coin.ambush_unit_types` — an armed gun-truck + riflemen from the red faction's own roster, price-capped
  so no real IFV/MBT slips in, with the `CELL_SIDC` infantry map symbol), via the `unit_types` /
  `sidc_override` path the COIN fiction-kit already uses; a faction with no soft vehicle falls to a supply
  truck + infantry. (2) The count is bounded — `MAX_AMBUSHES_PER_ROUTE` 6→3 **plus** a theater-wide
  `MAX_TOTAL_AMBUSHES` (4), so several convoys losing the roll on one turn can never pile a swarm of hidden
  teams (the 12-team pile-up the test saw) into the backline. Tests in `test_convoy_ambush.py`
  (cap + light-kit passthrough) + `test_coin_units.py` (the kit composition).
- **In-game pass: checklist S3 + S5.** The Python force model + emitter + plugin runtime are unit/harness
  tested, but the actual firefight (ambushers engaging the column, the spring feel, whether flying to the
  TIC call and clearing the team saves the convoy) needs a flown pass — plus the ambient layer's read
  (columns on both sides' roads, counts varying turn to turn, stacking vs spreading). Watch: the convoy
  actually drives its road; nothing about the ambush shows on any map before it springs; the springs come
  near the column, not at max range; convoy/ambush losses both show in the debrief.
- **Deferred:** an off-road (beside-the-road) ambush position is a follow-up (teams currently dig in on
  the road polyline itself). Convoy size/team strength/`AMBUSH_CHANCE`/the ambient 1..3 band are fixed
  constants — tune from the S3/S5 passes. (The multi-team gauntlet landed with the 2026-07-06 chance
  rework; the Tier-2 corridor-authoring pass landed the same day as batch 1 — every road-less campaign
  with a viable blue pair now has its corridor, and the 19 left out are genuine geography no-ops.) The
  batch-1 corridors are headless-verified to bind; their on-map read (does the drawn line hug the
  road?) rides the normal by-eye pass whenever each campaign is next flown, like the Vietnam trail
  FOB roads before them. Syrian Shield / Caucasus_Multi_Russia could still gain a corridor if a
  through-red supply line is ever wanted.

## §51 — Enemy comms jamming (IADS comms nodes)

**The IADS comms nodes, given a voice.** The IADS data model has always carried communications nodes
(`IadsRole.CONNECTION_NODE`, TGO category `comms` — the masts and bunkers MANTIS's C2-degradation graph
watches), but their only gameplay was as silent connection glue. With `enemy_comms_jamming` on, every alive
enemy comms / command-center node becomes a **standoff comms jammer**: duty-cycled barrage noise transmitted
on a rotating subset of the BLUE side's *briefed* radio channels, so the interference arrives in the
player's headset and the strike that silences it is the same strike that degrades the IADS.

**By default the jamming is intel-driven** (`comms_jam_requires_capture`, default ON): red can only jam
channels it *knows*, and it learns them from a **captured aircrew's comms plan** — see "The intel gate"
below. Turn that second toggle off for ambient jamming whenever a C2 node is alive.

### No SRS dependency — the transmission is DCS-native

The delivery mechanism is `trigger.action.radioTransmission` from the node's campaign-map position:

- **Real power/distance falloff.** DCS models transmitter power and range natively — the jamming is worst
  deep in enemy territory near the C2 belt and fades toward friendly airspace. No line drawn in Lua.
- **SRS users hear it anyway.** SRS tunes off the cockpit radios, so a player sitting on 251.0 in SRS is
  tuned to 251.0 in the jet — the looping static on that frequency plays through DCS's own radio path.
  Injecting audio into the actual SRS network (SRS-ExternalAudio.exe, MOOSE MSRS) was considered and
  **dropped**: it needs a server-side install, spawns a process per transmission, and buys nothing the
  in-game path doesn't already deliver.
- The noise file is `commsjam-noise.wav` (synthesized shaped static, committed in the plugin dir), injected
  into the miz via the plugin's `otherResourceFiles` and referenced as `l10n/DEFAULT/commsjam-noise.wav`.

### What gets jammed (positive list, never GUARD/ATC)

Python owns the target list (`_blue_briefed_frequencies`): the blue flights' **intra-flight channels**
(human-crewed flights first, then AI) plus the blue **AWACS/GCI** freqs, deduped, GUARD (243.0 / 121.5)
defensively filtered, capped at `MAX_JAMMED_FREQUENCIES` (10). ATC, ATIS and tanker channels are never
listed **by construction** — ground ops and emergencies stay clean (the §36 anti-grief bar, applied to
audio). The plugin then steps on only `maxFreqsPerBurst` (3) channels per burst cycle, rotating the window,
so coordination is pressured but never fully denied — and switching to a channel the jammer isn't currently
on is real, dynamic comms discipline.

**The JAM BACKUP channel closes the loop:** the planner allocates one fresh UHF frequency from the same
`RadioRegistry` every briefed channel came out of (so nothing else uses it and it can never be jammed),
re-rolling past the freak allocator-reuse collision, and publishes it as a `JAM BACKUP` line in the
kneeboard **Mission Info BLUF** — next to the `PUSH / SUCCESS / ABORT` code words (comms-plan data), not
the Support Info package table where it borrowed the viewing flight's Type/#A/C columns and read as a
phantom flight (+ echoed in the first-burst cue). Pushing the package to the backup is a briefed play,
not a mystery.

### The intel gate: capture-gated jamming (default)

With `comms_jam_requires_capture` on (the default), the jammer holds its fire until red actually holds a
captured pilot's comms plan — coupling §51 to the **§15/§21 Combat SAR enemy-capture race** and giving SAR a
second campaign-level stake:

- **Live capture, mid-mission**: the dormant plugin polls the `combatsar` plugin's `combat_sar_captures`
  state global (`CAPTURE_POLL` 30 s, blue entries only). On the first capture it cues **"AIRCREW CAPTURED —
  assume the comms plan is compromised… rotate off them now"** (naming the JAM BACKUP) and starts the burst
  loop after an **exploitation delay** (`captureReactionS`, default 120 s; never before the startup grace).
  Winning the SAR race keeps the net clean; losing it has an immediate, felt cost.
- **POW held, cross-turn**: `plan_comms_jam` checks `Coalition.pending_pow_recoveries` — a POW currently
  held means red took the comms plan on an earlier turn, so the mission opens with `activeFromStart` and the
  jamming runs from the grace under a distinct **"COMMS COMPROMISED: enemy interrogation of captured
  aircrew…"** story. **Freeing the POW** (recapture the holding field) or the **4-turn hold clock expiring**
  (the loss is written off and the squadron rotates its comms plan) ends the compromise — both fall out of
  the existing POW machinery with zero new state.
- The C2 node stays the *transmitter* in every mode: no alive comms/command-center node ⇒ no jamming (the
  capture watch bails once the net is dead), and killing it still silences the mission regardless of what
  red knows.
- Dependency: live captures require the Combat SAR capture race to be running (a blue rescue helo emitted —
  `auto_combat_sar` default ON makes that the norm); a mission without it can still be jammed via the POW
  path.

### Who jams, and how it dies

`_enemy_jammer_nodes` lists every alive enemy TGO of category `comms` / `commandcenter` (the same objects
the MANTIS C2 graph watches — never SAMs, never EWRs, never generic buildings), emitting the **unit names**
per the MANTIS naming convention. The plugin's death detection is the MANTIS `node_dead` pattern verbatim:
a node counts as dead only on *positive evidence* — a placed static (`<name> object`) that existed and no
longer `:isExist()`, or its name in the global `dead_events` ledger (bare-name matched). A culled /
never-spawned node reads ALIVE, which is correct: it can't be killed this mission, and the standing
pressure is what motivates fragging a strike at it next turn (which un-culls it). Each burst cycle rotates
the transmitting node across the alive jammers; once every emitted node is positively dead the plugin stops
scheduling and (if jamming had been announced) cues "comms jamming has ceased."

**Audio pressure ONLY** — the §36/§49 discipline: no force-model change, the plugin owns no kills. Killing
the node is an ordinary strike on an ordinary IADS TGO, recorded natively, with its existing IADS
consequence (MANTIS C2 degradation) untouched.

### Files & tests

| Area | Path |
|---|---|
| Planner + emitter | `game/missiongenerator/commsjamluadata.py` (`plan_comms_jam` → `MissionData.comms_jam`, `populate_comms_jam_lua`); planned in `missiongenerator.py` before the Lua pass, emitted in `luagenerator.py` after the convoy-ambush emitter |
| Kneeboard | `missiongenerator.py` registers the `JAM BACKUP` channel on the generator (`add_comm(JAM_BACKUP_COMM_NAME, …)`) when a plan with a backup exists; `kneeboard.py` `_bluf_lines` surfaces it as a **Mission Info BLUF** line and filters it out of the **Support Info** comms ladder (so it never reads as a phantom flight). `JAM_BACKUP_COMM_NAME` (in `commsjamluadata.py`) is the shared label so producer and consumers can't drift |
| Runtime | `resources/plugins/commsjam/` (`plugin.json` + `commsjam-config.lua` + `commsjam-noise.wav`; registered in `plugins.json`) |
| Settings | `game/settings/settings.py` (`enemy_comms_jamming`, default **OFF**; `comms_jam_requires_capture` — the intel gate, default **ON** — both Mission Generation → Battlefield life) |
| Tests | `tests/missiongenerator/test_commsjamluadata.py` (plan ordering, GUARD filter, cap, backup collision re-roll, intel-gate flags, emit shape, gates); `tests/missiongenerator/test_kneeboard_bluf.py` (the JAM BACKUP BLUF line present-with-backup / absent-without); `tests/lua/test_commsjam_runtime.py` (grace, burst/stop/rotation, dead-jammer silence via both death paths, ceased cue, intel-gate dormancy/live-capture/POW-story/red-capture-ignored/watch-bail, no-node no-op) |

### Gotchas / deferred

- **Plugin dependency (the §36 lesson).** The runtime is the `commsjam` plugin; a saved default of it
  unticked silently kills the setting. Red Tide preseeds `enemy_comms_jamming: true` **and**
  `plugins: {commsjam: true}` (guarded in `tests/fourteenth/test_campaign_plugin_preseed.py`).
- **Needs comms/command-center TGOs to exist.** A campaign whose laydown fields no `comms`/`commandcenter`
  category objects emits nothing and the feature silently no-ops — correct (no C2, no jammer), but worth
  knowing when preseeding it elsewhere. Red Tide's `advanced_iads` range mode wires them per base.
- **Burst timing is wall-clock, not tactical.** The jammer doesn't react to what the player is doing —
  bursts are a jittered cadence. A reactive jammer (step on a channel *when it's in use*) needs a radio
  event DCS doesn't expose; out of scope.
- **BLUE-victim only.** The target list is blue's briefed channels; red AI doesn't care about audio.
  A symmetric blue jammer already exists as the §2 C-130J EW platform's radar side — extending it to
  comms is a possible follow-up.
- **The "rotation" at POW-clock expiry is a gameplay mercy.** Squadrons with authored `radio_presets` keep
  the same intra-flight channel across turns, so red "forgetting" the plan when the POW is written off is
  fiction; actually re-rolling compromised presets the turn after a capture is the honest follow-up
  (deferred, see the design note).
- **NEW game not required** (no persisted state; the plan is rebuilt every generation), but the Red Tide
  preseed only applies to a NEW campaign.

## §52 — Command-center decapitation degrades enemy planning

**The campaign-layer complement to §51.** §51 gave the IADS **comms** node a runtime voice; this gives
its **command center** sibling a *turn-model* consequence. A command center
(`category == "commandcenter"`, `IadsRole.COMMAND_CENTER`) had gameplay only inside MANTIS's runtime
SAM-autonomy graph — killing it made SAMs go autonomous, but red's **planning** was untouched, so
"bomb the enemy HQ" was a strike checkbox, not a strategic move. Now a side's auto-planner quality is
coupled to its own command-network health.

### How it works

`game/fourteenth/c2_decapitation.py`:

- `_command_centers(coalition, theater)` → `(alive, total)` command-center TGOs on the coalition's own
  bases (a CC is alive while any of its units is alive — the same test the IADS emitter uses).
- `c2_health` → the alive fraction (1.0 when the side fields no command centers — a C2-less campaign is
  unaffected).
- `unpredictability_bonus(coalition, theater, settings)` → `round((1 − health) × MAX_DECAP_UNPREDICTABILITY)`
  (60 pts at full decapitation), or **0** when the feature is off or the network is intact.

The bonus is read at plan time in `game/commander/tasks/targetorder.py` `_unpredictability_for`, added
on top of the side's base `*_planner_unpredictability` (§17) and clamped to the shuffler's 0–100 domain.
So as a side's HQs die, `shuffled_by_priority` progressively loosens its **opportunistic offensive**
target order — it services lower-priority strikes/OCA/BAI/anti-ship it wouldn't have before, and hits
the same things less reliably turn to turn.

### The §17 boundary (inviolable)

Only the offensive/opportunistic tiers pass through `shuffled_by_priority`; **reactive defensive tasking
stays strictly deterministic**. A decapitated enemy still defends itself — it just plans worse *offense*.
This is the same boundary §17 (auto-planner unpredictability) established; §52 rides the exact same lever,
just sourced from C2 health instead of a static slider.

### Legibility

The effect lands on the *enemy's* next turn, so the player is told the strike worked: a SITREP band line
(`Sitrep.red_c2_status` → "Enemy C2 degraded (claimed): 1/3 command posts operational", built by
`c2_status_line`). Framed as **claimed** (the player's own BDA) to respect the recon-fog model, and it
**rides along with real news** — like the will band, it never forces a SITREP onto an otherwise-quiet turn
(`is_empty` ignores it).

### Files & tests

| Area | Path |
|---|---|
| Core | `game/fourteenth/c2_decapitation.py` (`c2_health`, `unpredictability_bonus`, `c2_status_line`) |
| Planner hook | `game/commander/tasks/targetorder.py` `_unpredictability_for` (adds the bonus, clamps to 100) |
| Legibility | `game/sitrep.py` (`red_c2_status`), `game/sim/missionresultsprocessor.py` `record_sitrep` |
| Setting | `game/settings/settings.py` (`c2_decapitation_effects`, Air Doctrine, default **OFF**) |
| Tests | `tests/fourteenth/test_c2_decapitation.py` (health/bonus/status/gates); `tests/test_planner_unpredictability.py` (the shuffler coupling + intact/off determinism); `tests/test_sitrep.py` (the band line, rides-along) |

### Gotchas / deferred

- **Pure turn-model.** No `.miz`, no Lua, no DCS integration — zero runtime risk. It reuses the §17
  shuffler wholesale, so at full C2 health (or feature off) the planner is byte-identical to today and all
  existing determinism tests hold.
- **Symmetric in code, red in practice.** Each side reads its own C2 health, but only a side with an HTN
  auto-planner (red, in a normal player-vs-AI game) is affected by the player's strikes. Blue's own
  auto-planned (AI-filled) slots would loosen too if the player let blue HQs die — intended and fair.
- **Phase A2 deferred — the offensive package-count throttle.** The design note's second lever (cap red's
  *number* of offensive packages when decapitated, floored so red is never zeroed out) is not built; A1 is
  the unpredictability coupling only. Unpredictability alone never reduces red's package count, so there is
  no starvation risk in A1.
- **Preseeded on Red Tide (2026-07-07).** Default OFF everywhere; **Germany — Red Tide** flips it ON
  (`c2_decapitation_effects: true`) because its advanced-IADS build is one of the very few laydowns with a
  real, per-base **destroyable command-center network** (9 red Command Center cells) for §52 to key on —
  see the Red Tide design note. The B6 in-game pass now rides on that campaign.
- **NEW game not required** (no persisted state; C2 health is measured live each turn).

---

## §53 — War economy

**A per-base materiel supply economy on top of the money budget** (design note
`docs/dev/design/414th-war-economy-notes.md`). Closes the standing gap that nothing you bomb
traceably changes what the enemy can field: `game/fourteenth/war_economy.py` runs a
produce → transport → consume → **bite** loop from `Game.finish_turn`, gated `war_economy`
(default OFF; Red Tide preseeds).

**The loop.** `Base.supply` is a per-base stockpile (seeded to capacity once via
`war_economy_seeded`, `__setstate__`-defaulted). Each turn `advance_war_economy`: producers
(factory/oil/derrick) accrue `production_rate`; every active-front CP consumes a turn's
`frontline_demand` and refills from its connected producers over the transit graph
(`_external_supply_sources` via `ControlPoint.transitive_connected_friendly_destinations`),
neediest first — a front cut off from production can't refill and drains (the interdiction loop).
`stockpile_capacity` scales with production so a rear factory can hold what it ships.

**The bite (P2).** One `supply_effectiveness(cp) → [_BITE_FLOOR=0.5, 1.0]` multiplier (1.0 when off
or before the first seed, so turn-1 combat is never penalised) is applied at three sites: the `+0.2`
per-turn strength recovery (`game.py`, BLUE — only `player_points()` recover), the deployable-unit
cap (`ControlPoint.front_line_capacity_with`), and the ground-combat `delta`
(`missionresultsprocessor.py`, scaled by the *winner's* supply). A starved side recovers less,
deploys fewer units, and gains less ground. **The decoupling trap is solved:** `frontline_demand`
keys off `base.total_frontline_units` (raw force), never the supply-scaled cap, so `supply_factor`
can drive the cap bite without recursion.

**Fuel → air readiness (P3).** `fuel_readiness(cp)` scales a base's alive fuel-depot fraction into a
sortie multiplier `[0.5, 1.0]`, applied at the single per-turn chokepoint
`Squadron.return_all_pilots_and_aircraft` (`untasked_aircraft = int((owned − reserve) ×
fuel_readiness(location))`). Both the AI planner and the player's flight-creation UI read
`untasked_aircraft`, so bombing a base's fuel grounds part of its air for both; bases still *own*
their jets. Own setting `fuel_air_readiness` (default OFF; Red Tide preseeds). Wires the
previously-dead `active_fuel_depots_count`.

**Legibility (P4a).** The SITREP gains `blue_supply`/`red_supply`, fed from `coalition_supply_health`
in `record_sitrep`, rendering "Front supply X% -- enemy Y% (claimed)" on the kneeboard cover so the
player reads *why* a front stalled.

**Map + base-card legibility (P4b, landed 2026-07-08 post-merge).** Two surfaces:
- **Base card** (`QBaseMenu2.update_intel_summary`): a **Front supply: X%** line (friendly, active-front
  CPs only), and `generate_intel_tooltip` now spells out the supply multiplier when it is biting so the
  displayed deployable-limit reconciles with the P2 cap bite (`int(base × supply_effectiveness)`).
- **Map overlay** (`SupplyLayer`, wired into the §19 layers panel as "Supply status", default ON):
  `SupplyNodeJs.all_in_game` emits each BLUE front (coloured green→amber→red by `supply_factor`) + each
  producer (a blue dashed source ring), fed through `supplySlice`. Empty (layer hidden) unless
  `war_economy` is on; BLUE-only so enemy logistics stay fogged. `tests/server/test_supply_nodes.py`
  guards the off→empty / fronts+producers-only / enemy-excluded selection contract.

**Interface for §55.** `coalition_supply_health(game, coalition)` + `supply_factor(cp)` are
module-level pure reads; §55 red intent consumes the former (a starved red consolidates).

Symmetric; OFF is a proven exact no-op (regression across the combat/controlpoint/frontline/
ground-planner suites). Tests `tests/fourteenth/test_war_economy.py`. Landed via #531 (merged
2026-07-08, alongside §55). **Needs an in-game pass:** the multi-turn FLOT response + fuel grounding.

---

## §54 — Munitions availability

**The air axis of the war economy (§53): an airfield out of a scarce munition can't load it.**

**Taxonomy (M0).** A curated, hand-audited `_SCARCE_MUNITIONS` map in `game/data/weapons.py` — 5
families (`a2a_medium` / `arm` / `pgm_bomb` / `standoff` / `guided_asm`), keyed by exact
`WeaponGroup.name` (every rack variant listed) — drives the `WeaponGroup.scarce_family` property.
Explicit-and-central by design so the tracked set is exactly what was signed off; a guard test
(`tests/fourteenth/test_scarce_munitions.py`) fails CI if any mapped name stops resolving to a real
weapon group (the §46 dead-CLSID lesson). Only munitions worth running out of are tracked;
everything else is infinite.

**Stock + debit (M1).** Each base holds `Base.munitions` (family → loads, `__setstate__` `{}`).
`advance_munitions` (from `finish_turn`, gated `restrict_weapons_by_stock`): seeds each base to
`MUNITIONS_CAPACITY`, **debits what the ATO loaded** — iterate `coalition.ato.packages → flights`,
sum `weapon.weapon_group.scarce_family` per flight, decrement `flight.departure.base` — then
**rearms** toward capacity scaled by `supply_effectiveness` (a supply-cut base can't fully re-arm).
The debit is a **once-per-turn turn-boundary step, not a per-generation debit**, so mission
re-generation never double-counts.

**The gate (M2).** `Loadout.degrade_for_stock(munitions, …)` in `setup_payload` swaps a scarce store
the base is out of down to the first stocked/non-scarce fallback in `weapon.fallbacks`
(`_stocked_fallback_for` — JDAM → dumb bomb) or clears the pylon; gated on the setting **and**
`munitions_seeded` (pre-seed turns aren't falsely starved). This is the authoritative enforcement.
The payload editor (`QPylonEditor`) additionally greys out + labels "(out of stock)" the depleted
scarce stores as guidance (the current selection stays selectable).

**Base-card readout (M3, landed 2026-07-08 post-merge).** `QBaseMenu2.update_intel_summary` adds a
**Munitions** section listing each family's `N/24` stock (with a "(low)" tag at zero), labelled from
the shared `SCARCE_FAMILY_LABELS` map (`game/data/weapons.py`, a test guards label↔family coverage),
friendly bases only. Gated on `restrict_weapons_by_stock`.

Gated `restrict_weapons_by_stock` (Mission Generation → Loadouts, default OFF); OFF is an exact
no-op. Tests `tests/fourteenth/test_munitions_gate.py` (against the real F/A-18C) +
`test_scarce_munitions.py` + `test_war_economy.py`. Landed via #531 (merged 2026-07-08). **Needs an
in-app pass:** the loadout grey-out.

---

## §55 — Red Intent — adaptive enemy posture

**The "thinking red opponent."** Stock Retribution runs the *same* HTN commander for both sides,
rebuilt from scratch every turn (`TheaterCommander` / `TheaterState.from_game`) — no memory, no
reserve concept, no intent, so red plays the same reactive defense + default offensive ordering
every turn. This is the mirror of the BLUE campaign-phases arc (§40) for RED, and unlike the blue
arc it carries **memory** across turns. It is the deferred "red arc" the `nextaction._offensive_order`
docstring called out.

### The posture

`game/fourteenth/red_intent.py` resolves one of three RED postures each turn, latched on `Game`
(`red_intent_key` + `red_intent_entered_on_turn` + a turn-0 `RedIntentBaseline`; getattr-guarded,
recompute-not-pickle exactly like the phase pointer, resolved in `Game.initialize_turn` right after
`update_campaign_phase`):

- **`CONSOLIDATE`** — under pressure (outnumbered on the ground, low resolve, a base lost last turn,
  or ground given up vs the baseline): defend, husband reserves.
- **`ATTRITION`** — the neutral default: stock priorities with a modest unpredictability floor.
- **`SURGE`** — a clear ground advantage + air not suppressed: commit and take ground.

`classify_red_intent` reads live state (ground-force ratio across active fronts, red vs blue
air-superiority strength, `red.political_will`) **plus last-turn deltas** (mean blue front-progress
vs the turn-0 baseline, `last_sitrep.captured` = a red base lost last turn) **plus rolling trends**
(see below). `_next_posture` applies **asymmetric hysteresis**: escalating (→ATTRITION/→SURGE) waits
out a min-dwell; de-escalating toward CONSOLIDATE is immediate (a command reacts to a setback at
once).

### Rolling trend memory + graduated intensity (2026-07-10)

The original build snapshotted turn 0 only, so the design's promised *"blue has hit my IADS two turns
running → stay defensive"* trend reading never actually existed. It does now, on three axes, all pure
turn-model and all no-ops until real trend/margin data appears (the v1 constants are reproduced exactly
at the default intensity, so every prior test held byte-for-byte):

- **Rolling memory (A).** A bounded per-turn `red_intent_history` of turn-stable levels
  (`RedIntentSample`: resolve, cumulative front advance, red SAM-site count, both sides' fighters, red
  base count, supply) lives on `Game` (getattr-guarded + `__setstate__` default, trimmed to
  `MEMORY_LENGTH` = 6). The classifier differences the current sample against a **lookback sample**
  (`_trend_lookback`, ~2 turns back, `None` on turn 1) for trends: `iads_trend` (SAM belt dismantled),
  `resolve_trend` (regime cracking — the derivative the level floor misses), `base_trend` (bleeding
  bases), `front_trend` (front eroding again). Recording is idempotent (same-turn re-init replaces).
- **Richer battle-reading (C).** Those trends bias a *ground-dominant* red toward **CONSOLIDATE** even
  at a paper edge — so bombing red's IADS/bases visibly makes a winning red dig in, closing the
  interdiction→behaviour loop via red's own attrition (not only the §53 supply meter). A
  **blue-air-collapse opportunity window** (`blue_air_collapsing`: blue lost ≥35 % of its
  air-superiority force over the window while red's air holds) lets red **SURGE at a lower ground bar**
  (1.2× vs 1.5×) — pouncing on a transient gap.
- **Graduated intensity (B).** The classifier also yields an **`intensity`** ∈ [0, 1] (how strongly the
  posture is held), latched as `game.red_intent_intensity`, read by the aggressiveness + ground-commit
  seams so their magnitude *scales* — a runaway 4:1 surge strips more bases and attacks at a lower
  advantage than a marginal one; a collapsing regime husbands harder than a mild hold — instead of a
  flat per-posture constant. Anchored at `DEFAULT_INTENSITY` (0.5) to the v1 midpoints, so a typical
  posture is unchanged and only the extremes move. Surfaced as a "how committed" word on the status
  detail ("Surging (all-in)", "Consolidating (dug in)"), and `_legibility` names the trend driver
  ("IADS falling" / "resolve collapsing" / "losing bases" / "enemy air spent"). **Per-front posture is
  deferred** (one theater-wide posture stands; a distinct intent per front is the stretch).

### The four planner seams

All four are **no-ops for blue, a stock red, or when `red_intent` is off** — the planner is
byte-identical to before until red is actively consolidating or surging.

1. **Offensive emphasis** (`game/commander/tasks/compound/nextaction.py` `_offensive_order`) — the RED
   branch (previously an early `return stock`) now returns the posture's emphasis ordering over the
   offensive methods, resolved through the same name-keyed `_OFFENSIVE_FACTORIES` indirection the BLUE
   campaign phases use. Surge fronts `CaptureBases`/`PlanFrontLineCas`; consolidate leans
   `InterdictReinforcements`/`AttackBattlePositions`/`DegradeIads`.
2. **Unpredictability** (`game/commander/tasks/targetorder.py` `_unpredictability_for`) —
   `unpredictability_modifier` adds to `opfor_planner_unpredictability` (ATTRITION +15 — the folded-in
   "feint", SURGE 0, CONSOLIDATE +5), **stacking with the §52 C2-decap bonus** on the same clamp. Red
   only; blue never picks up red's posture. Flat per posture (not intensity-graduated).
3. **Aggressiveness** (`game/commander/objectivefinder.py` `vulnerable_control_points`) —
   `effective_aggressiveness` biases `opfor_autoplanner_aggressiveness` (SURGE → abandon more bases to
   attack, CONSOLIDATE → defend everything), clamped 0–100. The delta is **intensity-scaled** about the
   v1 ±30 midpoint (±15 at a marginal posture, ±45 at a runaway one).
4. **Ground husbanding** (`game/commander/tasks/frontlinestancetask.py` `_posture_commit_factor`) —
   `stance_commit_factor` scales the **perceived** `ground_force_balance` the *attack* stance thresholds
   test (SURGE commits reserves sooner, CONSOLIDATE husbands). **Intensity-scaled** about the v1
   midpoints (SURGE ×1.35 → ×1.15…×1.55, CONSOLIDATE ×0.7 → ×0.5…×0.85). Only the attacking stances
   (AGGRESSIVE/ELIMINATION/BREAKTHROUGH) are biased — DEFENSIVE/RETREAT keep the raw balance, so
   consolidate tempers the attack **without ever forcing a retreat**. **Yields** (factor 1.0) while an
   authored `red_tempo` ground-offensive pulse is active, so a campaign author's Tet/Easter offensive is
   never double-driven. **This seam goes per-front (D, below); the other three stay theater-wide.**

### Per-front posture + tuning (2026-07-10)

- **Per-front posture (D)** (`red_intent_per_front`, default **ON**). A theater-wide posture treated a
  two-front war as one stance. Now `_update_front_postures` classifies **each active front** from *its
  own* ground balance (`_front_ground_ratio`) plus the shared theater air/resolve/supply/**trend** read,
  with per-front hysteresis, latching a `FrontPosture` per front on `game.red_intent_fronts` (keyed by
  the cp-id pair, getattr-guarded + `__setstate__` `{}`). The **ground-husbanding seam (4)** reads it:
  `stance_commit_factor(game, front)` uses that front's posture/intensity, so red **commits reserves on
  the front it is winning and husbands on the one it is losing**. The global seams (emphasis /
  unpredictability / aggressiveness) + the UI headline stay theater-wide; the per-front breakdown shows
  in the ribbon expander (`front_postures` → `CampaignStatusJs.front_postures`, 2+ divergent fronts
  only). Off clears the dict and every front uses the theater posture; `_front_key` is defensive so the
  seam never raises. Verified: Berlin-4:1 / Fulda-1:4 → red surges (commit ×1.4–1.7) on Berlin, digs in
  (×0.5–0.7) on Fulda, under a theater-"Attrition" aggregate.
- **Tuning — the temperament dials** (Air Doctrine → Auto-planner behavior). A `RedIntentTuning` object
  (default = the base constants, so `DEFAULT_TUNING`/positional `classify_red_intent(m)` are
  byte-identical) threads settings-derived knobs through the classifier + seams via `tuning_for(game)`:
  - **`red_intent_boldness`** (0–100, 50 = neutral) — the master dial. Higher lowers the surge / opportunity
    / consolidate ground bars (red surges at a smaller edge, turtles only when badly outnumbered) and
    raises `seam_scale` (presses harder once committed — bigger aggressiveness delta + commit deviation).
  - **`red_intent_dwell_turns`** (1–6, default 2) — the escalation hysteresis (how sticky the posture is).
  - **`red_intent_trend_window`** (1–5, default 2) — how many turns back the trend read compares over.

  All getattr-defaulted (a pre-feature save = `DEFAULT_TUNING`) and re-anchored so `seam_scale`=1 +
  intensity=0.5 reproduce the v1 numbers exactly.

### Legibility

Three surfaces, all **surfacing the smart trend/intensity read visibly** (not only as a hover tooltip):

- **Kneeboard SITREP band** — the "Enemy posture" line renders the **detail** (`Sitrep.red_posture_detail`
  via `sitrep_posture_detail`, recorded next to `red_posture` in `record_sitrep`): the intensity word + the
  trend drivers — *"Enemy posture: Surging (all-in) — ground 4.0x · air holding · IADS falling"* — so the
  cockpit reads *why*, not just *what*. Falls back to the bare word for pre-refinement pickled sitreps.
  Rides-along like the will/C2 bands (never forces a SITREP onto a quiet turn). **Python-only — visible
  in-game with no client rebuild.**
- **Campaign-status ribbon chip** (web map, `CampaignStatusBar`) — the chip shows `ENEMY Surging` plus the
  **intensity word inline** (`CampaignStatusJs.red_posture_intensity` via `intensity_word` → *"ENEMY Surging
  · all-in"*), coloured by mood (surging red, consolidating amber, attrition neutral). The expander (click
  the phase chip) carries an **"Enemy intent" block** showing the full `red_posture_detail` "why" line —
  plus, on a divergent multi-front war, a **per-front breakdown** (`front_postures` → `CampaignStatusJs.front_postures`,
  one row per front: *"Berlin — Surging · all-in / Fulda — Consolidating · dug in"*). Hidden when off.
- **Per-turn transition message** ("Enemy posture: Surging" + the narrative + legibility) in the info log.

So the enemy's stance *and the reason for it* read on both the kneeboard and the planning map.

### The §53 coupling (P4 — LIVE)

`_red_supply_health` reads the war-economy's `coalition_supply_health(game, red)` (§53,
`game/fourteenth/war_economy.py`) via a dynamic `importlib` import (so it neither errored where §53 was
absent nor became an unused ignore once it landed), degrading to `None` when the economy is off/absent — so
P0–P3 stayed economy-independent. **§53 has landed, so the coupling is live:** starved supply forces
`CONSOLIDATE` even on a paper advantage, closing the interdiction→behaviour loop (bomb red's supply and a
winning red digs in). **Red Tide preseeds both `war_economy` and `red_intent` ON**, so the full loop runs
there out of the box; verified end-to-end against a stubbed economy in `test_red_intent.py`.

### Files & tests

| Area | Path |
|---|---|
| Core | `game/fourteenth/red_intent.py` (postures, classifier, rolling-trend memory + `RedIntentSample`, intensity, hysteresis, `RedIntentTuning`/`tuning_for`, per-front `FrontPosture`/`_update_front_postures`, the four seam helpers) |
| Seams | `nextaction.py` `_offensive_order`; `targetorder.py` `_unpredictability_for`; `objectivefinder.py` `vulnerable_control_points`; `frontlinestancetask.py` `_posture_commit_factor` (aggressiveness + commit are intensity- + boldness-scaled; commit is per-front) |
| Hook / state | `game/game.py` (`update_red_intent` in `initialize_turn`; latched `red_intent_*` fields incl. `red_intent_history` + `red_intent_intensity` + `red_intent_fronts`, `__setstate__` defaults) |
| Legibility | `game/sitrep.py` (`red_posture` + `red_posture_detail`) + `record_sitrep` (`sitrep_posture_detail`); `game/server/game/models.py` (`CampaignStatusJs.red_posture` / `red_posture_detail` / `red_posture_intensity` / `front_postures`) + `client/src/components/campaignstatus/CampaignStatusBar` (chip intensity word + expander "Enemy intent" + per-front breakdown + CSS) |
| Setting | `game/settings/settings.py` (`red_intent` default **OFF**; `red_intent_per_front` default **ON**, `red_intent_boldness`/`red_intent_dwell_turns`/`red_intent_trend_window` — all Air Doctrine → Auto-planner behavior) |
| Tests | `tests/fourteenth/test_red_intent.py` (classifier/trends/intensity/tuning/per-front); `tests/test_sitrep.py`; `tests/test_planner_unpredictability.py` (stacked red-intent + C2 clamp) |

### Gotchas / deferred

- **Pure turn-model.** No `.miz`, no Lua, no DCS — zero runtime risk. Every seam returns the
  neutral/raw value for blue, a stock red, or feature-off, so the full suite is unchanged.
- **Red-only by design.** Blue's "intent" is the campaign-phase arc (§40); a blue-AI mirror (for
  red-playing humans) is a possible later follow-up, out of scope.
- **P4 (§53 supply coupling) is LIVE** — §53 shipped `coalition_supply_health`, so a starved red
  consolidates; Red Tide preseeds both features ON. It stays a graceful no-op on campaigns without the war
  economy.
- **The web ribbon needs the CI client rebuild** to appear (the Python payload + hand-added generated type
  ship in this repo; the built bundle is produced by CI). The kneeboard/SITREP surfaces need no rebuild.
- **NEW game not required** (only a small latched pointer + baseline + the rolling `red_intent_history`
  + latched `red_intent_intensity` persist; posture/trends/intensity re-derive each turn — a pre-feature
  or pre-refinement save just starts its trend memory empty and fills it as the war turns). Design note:
  `docs/dev/design/414th-red-intent-notes.md`.

---

## §56 — Strikeable motorpool depots

**Adopted from upstream PR [dcs-retribution#859](https://github.com/dcs-retribution/dcs-retribution/pull/859)**
(geofffranks, "Strikeable motorpool depots", closes upstream #655). Cherry-picked onto the fork
verbatim (4 commits, Geoff retained as author) plus one fork-adaptation commit; the Pretense hunk was
dropped because the fork has no Pretense. This is an *upstream-authored* capability given a 414th §N
so it rides the same registry/checklist discipline as the fork's own features — not a 414th-original.

### What it does

Retribution's ground war holds a **reserve**: `GroundPlanner.plan_groundwar` sends only a slice of a
control point's `base.armor` to the front (proportional to `frontline_unit_count_limit`, and *nothing*
from a CP with no connected enemy). The rest sat purely as an economy number — you could only attrit it
by meeting it at the FLOT after it deployed. This projects that **not-yet-deployed reserve** as a
**strikeable motor pool** at the CP, so a player can bomb the depot and thin the enemy's armor reserve
directly.

### Shape (Python-only; no Lua plugin)

- **`MotorpoolGroundObject`** (`game/theater/theatergroundobject.py`, category `"motorpool"`) — a
  maintenance-facility map symbol (`LandInstallationEntity.MAINTENANCE_FACILITY`), visually distinct
  from an armor group. `sidc_status` is pinned **`PRESENT`** — an empty depot is its normal resting
  state (vehicles populate ephemerally at mission-gen), never rendered damaged/destroyed; `is_dead` is
  left intact so AI target-selection/capture/IADS logic is unaffected. `capturable`/`purchasable`/
  `should_head_to_conflict` are all `False`; `mission_types` offers **BAI** to the opponent.
- **Placement** — gated on an authored `Fortification.Garage_A` static (`MizCampaignLoader.motorpools`
  → `PresetLocations.motorpools`), materialised by `start_generator.generate_motorpools` (new games)
  and injected on load by `migrator._ensure_motorpool_tgos` (existing saves). **Red Tide authors one**
  (2026-07-08) — a `Garage_A` ~4 km NE of **Haina**, the forward Soviet base at the Fulda Gap, so the
  feature is exercised on the fork's flagship armor campaign ("bomb the motor pool before its armor
  reaches the front"). Headless-verified through the real `GameGenerator` pipeline: the static binds to
  Haina (RED) and materialises exactly one `MotorpoolGroundObject` (CI-locked in
  `tests/fourteenth/test_red_tide_motorpool.py`). Every other campaign is **inert until it places a
  `Garage_A`** — it changes nothing until a depot is authored.
- **Population** — `MotorpoolPopulator` (`game/missiongenerator/motorpoolpopulator.py`), run once per
  mission-gen before the TGO generator, rebuilds each motorpool's vehicle groups from the CP's current
  reserve slice. `ai_ground_planner.reserve_armor_for` computes the reserve as *exactly*
  `base.armor − deployable_armor` (a `plan_groundwar`-faithful duplicate — deliberately not refactored
  to share, since `plan_groundwar` has no tests on this base), capped by `motorpool_spawn_cap`
  (largest-remainder proportional trim). Multiple motorpools on one CP round-robin the **single** shared
  reserve pool (never each render it in full, which would double-decrement `base.armor` on a strike). The
  populated groups are **ephemeral** — never persisted; rebuilt every mission.
- **Rendering** — `MotorpoolGenerator` (`game/missiongenerator/motorpoolgenerator.py`, a
  `GroundObjectGenerator` subclass) lays the vehicles in a grid (so DCS doesn't drop overlapping spawns),
  **weapon-hold + alarm-green + `player_can_drive=False` + no EPLRS** (parked, unmanned, no datalink),
  plus an inert `Garage_A` depot static offset clear of the grid. Vehicles register into
  `UnitMap.motorpool_units` (a distinct registry), **not** as theater objects — so a theater-object
  death never touches `base.armor`.

### 1:1 grind, no economy, no front shift

A killed reserve vehicle is a **distinct loss category** end-to-end: `Debriefing.dead_ground_units`
buckets it into `player_/enemy_motorpool` (via `unit_map.motorpool_unit`), and
`missionresultsprocessor.commit_motorpool_losses` decrements `base.armor[unit_type]` by one. Because it
is *not* a front-line loss, it feeds neither `casualty_count` nor `commit_front_line_battle_impact` —
**a depot strike forces a repurchase next turn but never moves the front line**. Losses surface on the
debrief (the "Motorpool units lost" faction row + per-type "`<type>` from motorpool" rows).

### Settings & fork interactions

- Gated `motorpool_enabled` (**Campaign Management → Campaign features**, default **ON**) +
  `motorpool_spawn_cap` (default 10, 0–50 — a perf lever). Both registered in the §28 `FIELD_LAYOUT`.
- **§3 recon fog** leaves a motorpool an **exact** marker — category `motorpool` isn't in the
  concealable set (`game/server/tgos/models.py` conceals only armor/missile/concealable-SAM), so the
  depot reads like an ammo depot/building, not a dashed "suspected activity" circle. Sensible: you see
  the depot and strike it.
- **Not supported in Pretense** (no loss reconciliation there) — the fork has no Pretense, so this is
  moot here; the upstream skip hunk was dropped.

### Fork-adaptation notes (vs the upstream PR)

Two fork-only changes on top of the verbatim cherry-picks: the two new settings were registered in the
fork's `FIELD_LAYOUT` (§28 requires every user setting listed exactly once), and the loss-separation
test's fake front-line group gained a `.name` (the fork's `add_front_line_units` also records the group
by name for TIC clones, §9). All conflicts were keep-both adjacent insertions (settings block, unitmap
registries, `ai_ground_planner` helpers, the two save-compat tombstones + `MotorpoolGroundObject`,
`test_debriefing`).

Tests: the PR's suite (`tests/**/test_motorpool_*.py`, `tests/ground_forces/test_reserve_armor.py`,
`tests/campaignloader/test_motorpool_recognition.py`) rides along, plus
`tests/fourteenth/test_red_tide_motorpool.py` locking the authored Haina depot. **In-game pass** =
checklist B8 — fly **Red Tide** (the depot renders at Haina immediately; its parked vehicles appear
once red has procured armor, a couple of turns in, since `base.armor` is empty at turn 0 by design)
to exercise the map icon, in-mission depot + parked vehicles, the strike→decrement→repurchase grind,
the no-front-shift guarantee, and the debrief rows.

---

## Code audit fixes — 2026-07-07

A full read-only audit of the 414th surface (campaign layer, mission-generator emitters,
Lua runtimes, server/API + fog, save-compat, planner/sim) produced this batch of
correctness fixes. Each brings the code to what its feature section already documents;
none change a feature's intended shape.

- **§ COIN `_despawn` (`game/fourteenth/coin.py`)** — `events.delete_tgo` takes a `UUID`,
  not the TGO object; passing the object poisoned `GameUpdateEventsJs` serialization and
  dropped the whole `/eventstream` turn-end batch on any turn that despawned a COIN
  IED/HVT/dispersed cell or a §50 convoy-ambush team (default ON). Fixed to `tgo.id`.
- **§34 `faction_color` (`game/theater/theatergroundobject.py`)** — `control_point.captured`
  is the `Player` enum (always truthy), so `"BLUE" if captured else "RED"` labeled every
  TGO BLUE; the naval-gunfire emitter put red gun ships on the blue side. Now reads
  `captured.is_blue`.
- **§21 Combat SAR templates (`game/missiongenerator/missiongenerator.py`)** —
  `spawn_combat_sar_templates()` ran *before* `spawn_unused_aircraft()` populated
  `parked_rescue_helos`, so the preferred tracked parked-helo source was always empty and
  the runtime always fell back to the untracked clone. Reordered.
- **§40 ROE gate (`game/fourteenth/phases.py`)** — the authored `airfield` target lock had
  no ownership check, so during Rolling Thunder/Bombing Halt the BLUE auto-planner was
  scrubbed from planning its own BARCAP/AEW&C/tankers (friendly CPs classify as
  `airfield`), and a permanent positive-control box kept blocking a base after BLUE
  captured it. `roe_restriction_reason` now exempts friendly-owned targets and only
  zone-gates class-carrying (CP/ground-object) targets. Also: the escalation tax now
  charges each phase skipped in a same-turn chained advance (a set-based latch), not just
  the final one.
- **§1 COIN anchors (`game/fourteenth/coin.py`, `game/game.py`)** — the "turn 0" anchor
  snapshot never ran at turn 0 (`finish_turn` increments the turn before its hooks), so the
  caps were baselined *after* mission 1's losses. `snapshot_campaign_start_anchors` runs
  from `initialize_turn` at turn 0. Transient COIN spawns are tagged `coin_spawned` so they
  no longer count toward / get revived by the C1 anchor machinery; a stronghold capture is
  no longer double-charged as an HVT kill; a matured dispersed cell no longer revives a
  cache at a now-BLUE base; the reinfiltration flip re-validates the conservation bound and
  player-field exclusion at flip time and skips `OffMapSpawn` targets; and mid-campaign
  toggle-off of the COIN/ambush layers now sweeps their hidden TGOs instead of stranding
  them. The carrier strike picker skips `map_hidden` teams.
- **§36 airbase harassment (`game/missiongenerator/vietnamopsluadata.py`)** — nothing in
  the engine constructs `ControlPointType.FARP` (FARPs load as FOB-type CPs with helipads),
  so the documented airfield/FARP siege never shelled a FARP. Eligibility now goes through
  `_harassable_cp` (airfields always; FOB-type CPs with helipads).
- **§3 / server fog (`game/server/`)** — enemy carrier/LHA groups (CP-attached TGOs) shipped
  ground-truth composition/BDA/rings with no `known_for` gate; the concealment jitter was
  seeded from the public TGO id alone (recomputable client-side — now id XOR a per-campaign
  server-held `concealment_salt`); `DefendingSam` combat events broadcast exact positions of
  concealed SAMs engaging AI-only flights; unknown-id route lookups 500'd instead of 404'd
  (a `KeyError` handler now maps them); and the fog-overview reveal is reset on save load /
  new-campaign start.
- **Persistence (`game/data/weapons.py`, `game/fourteenth/flight_defaults.py`)** — an unknown
  weapon clsid left an empty `Weapon` object (deferred `AttributeError`) and an unknown weapon
  group name hard-aborted the whole load; both now keep the pickled state (FlightType-style
  tolerance). The flight-defaults write is now guarded (a locked store no longer throws
  through the Qt click handler).
- **Lua runtimes** — the Sandy divert/release orbits passed terrain+alt to
  `TaskOrbitCircleAtVec2` (which adds terrain again → 2× height over high ground); the
  coin/mobilemissiles mover ticks and the Arc Light watcher leaked/polled forever; a dead
  FAC left its F10 mark; and the mist shim's `getHeadingPoints(north=true)` would throw
  while `scheduleFunction` swallowed consumer errors silently.
- **§20 drop-spawn (`game/theater/unitplacement.py`)** — a Deploy-Next-Turn placement charged
  at queue time is now refunded when it can't be materialised (CP lost / terrain changed).

### Deferred design calls — resolved 2026-07-07

The audit deliberately left three items untouched because they needed a *design* decision, not a
code fix. Resolved (with the user) as a follow-up:

- **§50 ambient-convoy free seeding → skim-only.** `ensure_ambient_convoys` was calling the §35
  `_seed_trail_source`, `commission_units`-ing free (un-budgeted) units into **both** sides' rear
  bases every turn on **every** campaign — a firehose of ~48 net-new free ground units/turn
  game-wide, permanently reinforcing front-ward bases. That external-supply free-seed is right for
  the §35 Vietnam trail (red-only, Vietnam-gated, its documented character) but wrong to generalize:
  the squadron asked for *traffic*, not free reinforcement. Ambient columns now **skim only** —
  relocate units that already exist (`_skim_units`), never commission free ones — so a rear base too
  thin to skim yields no column that turn. §35 is untouched.
- **§37 Super Gaggle "never-spawned delivery credit" → losses-only.** `reconcile_super_gaggle`
  credited a garrison strength boost whenever a committed helo was *absent* from the debrief kill
  list — but "absent" is "survived and delivered" OR "never spawned" (mission ended before the launch
  delay), indistinguishable without a runtime "delivered" signal the plugin does not emit. Dropped the
  `DELIVERY_STRENGTH_BONUS` credit (and `_credit_delivery`); the gaggle is now losses-only. Real
  delivery credit is deferred behind a real signal (Lua/debrief-schema change this module avoids).
- **§15 combatsar Sandy divert (G23) → kept frozen, awaiting the re-fly.** The 2026-07-02 route-push
  rework is the correct MOOSE transit-then-orbit pattern and reads sound; "pass-or-delete" is decided
  by an in-game re-fly, not a code review. Kept as-is (no change) — the checklist re-fly is the arbiter.
