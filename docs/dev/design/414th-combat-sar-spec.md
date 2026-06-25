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

| Phase | Scope | Validates |
|---|---|---|
| **1 — Python task** | `COMBAT_SAR` FlightType + FLOT-orbit flight plan + CH-47/C-130 eligibility + entity map; player-selectable | Generate a mission, see a CH-47/C-130 fly a FLOT orbit; Python tests green |
| **2 — Lua CSAR bridge** | `combatsar` plugin: MOOSE `CSAR` for human ejections, CH-47 rescue set | Eject a player near the FLOT → the CH-47 flies in and recovers them; `dcs.log` clean |
| **3 — AI standing alert** | auto-plan one CSAR orbit/side + `auto_combat_sar` setting | AI CSAR up with no player; auto-rescue works |
| **4 — polish** | C-130 → tanker/command role (reuse refuel system), kneeboard card, scoring hook | nice-to-haves |

## Open questions / risks

- **C-130 "King" role depth (v1):** simplest v1 = C-130 just flies the orbit (presence). Wiring it as
  an actual **tanker** for the helos reuses the existing refueling system but is Phase 4, not v1.
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
