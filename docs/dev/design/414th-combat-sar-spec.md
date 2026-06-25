# Combat SAR — bespoke pilot-rescue flight task (spec)

**Status:** spec / design (no code yet) · **Date:** 2026-06-25
**Related:** [`414th-moose-longview.md`](414th-moose-longview.md) (Tier-A `Ops.CSAR` candidate),
CLAUDE.md §15 (SCAR + the *existing* SOF-recovery `CSAR`), `414th-scar-HANDOFF.md`.
**The first "add a MOOSE Ops capability" feature post-MIST.**

## Vision (user's words, locked)

> A bespoke CSAR flight task — **CH-47s and C-130s can fly it**, they **orbit near the battle**, and
> when a **human pilot ejects** they go pick them up.

## Decisions (settled)

1. **Roles (realistic split):** the **CH-47 does the pickup** (lands at the downed pilot); the
   **C-130 orbits as the HC-130 "King"** — on-scene command / overhead presence (and, later, tanker).
   A C-130 never lands at an ejection site.
2. **Both player- and AI-flown:** players can take the task for the challenge; AI flies a **standing
   alert** so a downed human gets rescued even with no player CSAR up.
3. **New `FlightType.COMBAT_SAR`** — distinct from the existing `FlightType.CSAR` (which stays the
   point-specific SOF-team recovery in the SCAR loop). Reactive pilot-rescue should not be tangled
   with scripted SOF recovery.

## Runtime engine: MOOSE `CSAR`

`CSAR:New(Coalition, Template, Alias)` already hooks `EVENTS.Ejection` / `PlayerLeaveUnit` / `Crash`,
spawns the downed pilot, and runs the pickup FSM. It supports **human/player** pilots and a configured
set of **rescue aircraft**. This is exactly the engine — we drive it from a thin config bridge, same
shape as the MANTIS / CTLD plugins.

## Architecture (Python plans, Lua executes)

### Python side
1. **`FlightType.COMBAT_SAR = "Combat SAR"`** (`game/ato/flighttype.py`) + an `AirEntity` mapping
   (rescue/transport-class) in the entity table.
2. **Flight plan = FLOT-anchored orbit.** Reuse the **AEWC / support-orbit** builder
   (`game/ato/flightplans/aewc.py` + `flightplanbuildertypes.py`): takeoff → racetrack **behind the
   FLOT, near the battle but clear of threat rings** (same anchor logic AWACS/tanker already use) →
   RTB. *Not* the air-assault layout the SOF `CSAR` uses.
3. **Aircraft eligibility:** add `COMBAT_SAR` to **CH-47** and **C-130** task capabilities
   (`game/dcs/aircrafttype.py` / the task-priority rubric). CH-47 = rescue; C-130 = command orbit.
4. **Planning:**
   - **Player-selectable:** `COMBAT_SAR` surfaces in flight creation for CH-47/C-130.
   - **AI standing alert:** auto-plan one COMBAT_SAR orbit per side when enabled (mirror
     auto-AWACS/tanker support planning), gated by a new `auto_combat_sar` setting (default OFF until
     flown).
5. **Emit the CSAR data** into `dcsRetribution` (which groups are CSAR CH-47s = the rescue set; the
   C-130s = orbit only), like every other plugin's data table.

### Lua side — new `combatsar` config-bridge plugin
- `CSAR:New("blue", <late-activation template helo>, "Combat SAR")`, then:
  - **Rescue set = the CH-47 COMBAT_SAR groups** (from the emitted data). C-130s are **excluded** from
    the rescue set (they only fly the orbit).
  - **Pilots = humans:** enable player-pilot rescue (`rescueOnlyPilots`/player options); AI ejections
    optional/off for v1 to match "downed HUMAN pilots."
  - Wire pickup/board ranges, smoke/beacon on the downed pilot, deliver-to-base (or to the orbiting
    flight's home).
- Load order / injection: normal work-order plugin (after `Moose.lua`), same as `mantisiads`.

## Phased build (each phase its own branch + in-game pass; never merge unflown)

| Phase | Scope | Validates | Status |
|---|---|---|---|
| **1 — Python task** | `COMBAT_SAR` FlightType + FLOT-orbit flight plan + CH-47/C-130 eligibility + entity map; player-selectable | Generate a mission, see a CH-47/C-130 fly a FLOT orbit; Python tests green | ✅ landed (#170) |
| **2 — Lua CSAR bridge** | `combatsar` plugin: MOOSE `CSAR` for human ejections, CH-47 rescue set | Eject a player near the FLOT → the CH-47 flies in and recovers them; `dcs.log` clean | ⏳ built, **pending in-game pass** |
| **3 — AI standing alert** | auto-plan one CSAR orbit/side + `auto_combat_sar` setting | AI CSAR up with no player; auto-rescue works | ⏳ built, **pending in-game pass** |
| **4 — polish** | C-130 "King" on-scene-command role (TACAN beacon + LARS survivor-locator), kneeboard card, helo orbit-altitude tuning, scoring hook | nice-to-haves | ◐ kneeboard + altitude + King beacon/LARS done; ADF beacon + scoring deferred |

### Phase 4 — as built (partial)

- **Kneeboard card** (`CombatSarTaskPage` in `game/missiongenerator/kneeboard.py`, wired into
  `generate_task_page`): a role-aware player briefing — CH-47 gets the **pickup** procedure (hover/
  land at the beacon, doors open, deliver to any friendly field/FARP to score); C-130 gets the
  **on-scene-command** brief (hold overhead, don't land). Both explain the F10 `CSAR` menu. Guidance,
  not exact tunables (MOOSE shows live ranges in-game).
- **Helo orbit altitude — already handled, no code.** COMBAT_SAR reuses the AEWC flight plan, whose
  `builder.get_patrol_altitude` routes every helo through `get_altitude`, which clamps to
  `Settings.heli_combat_alt_agl` (the same path air-assault/CSAR helos use). The CH-47 orbits at a
  helo-appropriate AGL altitude; the C-130 gets a normal fixed-wing patrol altitude. Nothing to tune.
- **C-130 "King" TACAN beacon** (`combatsar-config.lua`). Each King lights a TACAN the rescue helo
  homes on. **TACAN, not ADF, by design:** `ActivateTACAN` auto-detects an aircraft and uses the
  air-tracking (tanker) beacon system so it **follows the moving orbit** ([Moose.lua:6187]), and the
  DCS CH-47F has a TACAN receiver. (MOOSE's `RadioBeacon`/ADF is fixed-point — it would need a refresh
  loop to track a mover — so the **ADF beacon is deferred**; the 40.0 MHz FM freq is reserved for it.)
  Python allocates the channel from the shared TACAN pool (`register_combat_sar_king`, best-effort) and
  emits it per King; the Lua attaches the beacon on group **birth** so a delayed/AI-spawned King is
  covered, with a dedup guard.
- **LARS — survivor-locator (SME ask).** An F10 **"Combat SAR → LARS - Locate Survivors"** button on
  each King reads MOOSE CSAR's live `downedPilots` table and messages the King a nearest-first list of
  every active survivor: **position** (reusing CSAR's settings-aware coord formatter), **bearing/range
  from the King**, and **ADF freq**. It's the King-side equivalent of the helo's built-in active-SAR
  display (which is gated to rescue helicopters). Player-King utility; an AI King just radiates the
  beacon. "Become the beacon" = the King's continuous TACAN; LARS = the coordinate readout to relay.
  The data carries each King's `callsign`/`tacanChannel`/`tacanBand` (+ reserved `beaconFreqHz`).
- **Still open (optional):** the deferred **ADF radio beacon** (helo-universal homing; needs a
  position-refresh loop for the moving King) and a **scoring/economy hook** for successful rescues.

> **C-130 tanker role is OFF the table.** The C-130 **cannot act as an aerial-refueling tanker in
> DCS currently** (user-confirmed, 2026-06-25), and the CH-47 rescue helo couldn't take fuel from it
> anyway. So the Phase-4 "C-130 King" stays an **overhead presence / on-scene-command** role
> (orbit + callsign, maybe a beacon/relay) — do **not** wire it to the refueling system.

### Phase 2 — as built

- **`combatsar` config-bridge plugin** (`resources/plugins/combatsar/`, registered in `plugins.json`
  after `scar`). Pattern mirrors the MANTIS bridge: a `configurationWorkOrders` plugin, no script of
  its own, runs after `Moose.lua`. Inert unless `dcsRetribution.CombatSAR` exists.
- **Rescue-set binding** uses the MANTIS exact-name-as-prefix trick:
  `SET_GROUP:FilterPrefixes(<CH-47 group names>):FilterCategoryHelicopter():FilterStart()` →
  `CSAR:SetOwnSetPilotGroups(set)`. No group renaming required; `FilterStart()` also picks up the
  helo when it spawns late.
- **Human-only / ejection-only for free:** `enableForAI=false` makes MOOSE CSAR's `_EventHandler`
  early-return on any non-human-initiated event (`Moose.lua` CSAR:_EventHandler — `IniPlayerName==nil`
  → return), and `csarOncrash=false` limits it to ejections. `allowFARPRescue=true` lets the helo
  deliver to any friendly airfield/FARP, so no MASH group is required.
- **Downed-pilot template:** MOOSE CSAR clones a `.miz` group at each crash site
  (`SPAWN:NewWithAlias(self.template,…)`), so the generator drops **one** hidden, late-activation
  infantry group named `Combat SAR Downed Pilot` (`LuaGenerator._generate_combat_sar_pilot_template`,
  blue faction infantry with a vanilla `Soldier_M4` fallback, anchored at a blue CP). Emitted only
  when a blue Combat SAR flight exists, so no orphan group otherwise.
- **Plumbing:** `FlightData` gained a `group_name` field (set from the pydcs group) so
  `LuaGenerator._generate_combat_sar` can emit `dcsRetribution.CombatSAR = { pilotTemplate,
  rescueHelos = {…CH-47…}, kings = {…C-130…} }`. `kings` is recorded now for the Phase-4 King role;
  v1 does nothing with it (C-130s just fly the orbit).
- **Plugin options:** `autosmoke` (off), `loadDistance` (75 m), `rescueHoverHeight` (20 m),
  `messageTime` (15 s) — surfaced in the Plugin Options UI.

### Phase 3 — as built

- **`auto_combat_sar` setting** (`Settings`, HQ automation section, **default OFF**). Off → no CSAR
  is ever auto-planned and the runtime stays human-initiated only (Phase 2 behaviour).
- **HTN auto-planning** mirrors AEWC/refueling support:
  - `TheaterState.combat_sar_targets` = the active front lines, but **only** for the (blue) player
    coalition and **only** when the setting is on (empty otherwise — red and off are pure no-ops).
  - `PlanCombatSar` primitive (`game/commander/tasks/primitive/combatsar.py`) — gated on the setting,
    proposes one `COMBAT_SAR` flight, `asap=True` so the alert is up before the first losses.
  - `PlanCombatSarSupport` compound (`…/compound/combatsarsupport.py`), wired into `TheaterSupport`
    alongside `PlanAewcSupport` / `PlanRefuelingSupport`. Airframe scarcity self-limits: no
    CH-47 available → the fulfiller simply doesn't plan it.
- **AI rescue flag:** the generator emits `enableForAI` in `dcsRetribution.CombatSAR` from the
  setting. On → MOOSE CSAR may commandeer an orbiting **AI** CH-47 to fly the pickup (and AI
  ejections become rescuable too); off → human-initiated only. The Lua bridge reads it instead of
  the hard-coded `false`.
- **Scope note:** still blue-only (the CSAR engine is built for `"blue"`); a red `COMBAT_SAR` would
  just fly an inert orbit, so red is never auto-tasked.

## Open questions / risks

- **C-130 "King" role depth:** C-130 just flies the orbit (overhead presence / on-scene command).
  Tanking the helos is **not possible** — the C-130 can't be a DCS tanker (see the Phase-4 note), so
  the King role never touches the refueling system.
- **MOOSE CSAR rescue-aircraft binding:** confirm CSAR's API binds the rescue set by **group-name
  prefix** vs. explicit names (drives what Python must emit) — pin in Phase 2 against `Moose.lua`.
- **Downed-pilot template:** MOOSE CSAR spawns a downed-pilot unit; confirm whether it needs a
  late-activation template in the `.miz` (like the CTLD/Ops template model) — if so, Python must emit
  one (a small generation add).
- **Interaction with the SOF `CSAR`:** none by design (separate FlightType, separate plugin) — but
  both may run MOOSE/CTLD machinery; verify no double event-handling on ejection.
- **Scope creep:** keep v1 to **blue-side, human-pilot, CH-47 pickup, FLOT orbit.** Red CSAR, AI-pilot
  rescue, multi-helo coordination = later.

## Definition of done (v1)

A player flying a CH-47 (or an AI CSAR alert) tasked **Combat SAR** orbits near the FLOT; when a human
pilot ejects in the area, the downed pilot spawns with a beacon and the CH-47 recovers them — with the
C-130 holding overhead. No `dcs.log` errors; doesn't disturb the existing SOF-recovery `CSAR`.
