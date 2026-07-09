# CSAR — the one document (vision, shipped architecture, and the 2026-07-03 rescope)

**Status: AUTHORITATIVE.** This supersedes the eight earlier CSAR/SCAR design notes (each now
carries a banner pointing here). Read this before touching anything rescue-related.

## The point (the user's vision, locked 2026-06-27)

> "I want the system to work where it's auto-fragged for AI to go pick up AIs and players can
> drop in if they wish. **Just a normal task.**"

Pilot goes down → everyone knows → somebody (AI or player) goes and gets him → the campaign
remembers. Everything below serves that; anything that doesn't is out.

## The 2026-07-03 rescope (squadron call — the course-correct)

A wide review found the feature had been stacked, rebuilt, and reshifted past its point: three
flight types, a 978-line plugin, eight design docs, eleven checklist rows — and the one thing
the vision asked for (default ON) never shipped. The call:

1. **Default ON.** `auto_combat_sar` now defaults ON for new campaigns (existing saves keep
   their stored choice). Rescue is a normal task.
2. **The AI-drama layer is FROZEN.** The Sandy auto-divert (G23) gets its one owed re-fly of
   the 2026-07-02 route-push rework: pass → it stays, frozen; fail → delete the divert (a
   player Sandy is untouched either way). No further iteration on AI-performs-the-rescue
   choreography — player-facing findability (smoke, F10 marks, LARS) is where investment goes.
3. **The POW recovery raid is SHELVED.** Capture is a campaign *consequence*, not a plannable
   mission. Removed: the `CSAR` raid flight type (persisted saves degrade it to TRANSPORT via
   `_LEGACY_FLIGHT_TYPE_VALUES`), the dynamic `CapturedPilotGroundObject` map objective (class
   kept as a save-compat tombstone; `purge_pow_objectives` sweeps old saves), and
   `commit_pow_recoveries`. **Kept — the held-POW model** (expanded 2026-07-06, see below): a
   captured pilot becomes a `PendingPowRecovery` held at the nearest enemy field (resolved at
   capture time), **freed if that field falls**, and **draining political will every turn held**
   (the Vietnam W1 feed — this is why the ledger stays).
4. **One doc.** This file. The old eight are historical record only.

## POW mechanics rework (2026-07-06)

Follow-up on the §51 comms-jamming intel gate (which made "a held POW compromises your comms"
a real consequence): a survey of the POW path found three gaps, all now fixed.

1. **A captured pilot was still flyable.** `PilotStatus` had only Active/OnLeave/Dead, and the
   squadron rebuilds its available pool from *Active* pilots — so the aviator in Hanoi could be
   fragged next turn while also draining will and compromising comms. New **`PilotStatus.POW`**:
   `record_pow_captures` calls `pilot.capture()` (Active → POW; `alive` stays True), which drops
   them from `active_pilots` (scheduling + the available-pool rebuild) until recovered. Freeing
   sets them back Active (`repatriate()`).
2. **POWs were invisible.** Nothing surfaced a held POW after the capture message. Now a
   **SITREP band line** per POW — `"Capt Mitchell — held at Mozdok (2 turns left)"`, or
   `"(held)"` on an indefinite-hold will campaign — and the **squadron roster** shows the POW
   status. The two levers (recapture the field / the clock) are finally legible, on every
   campaign (the SITREP works without the will meter).
3. **The 4-turn death clock was era-wrong on will campaigns and self-cauterized the running
   sore.** §48 made the per-turn POW drain "the one lever the GCI-ambush enemy has to pressure
   Washington" — but the pilot was killed after 4 turns, stopping the bleed. Now
   **`surviving_pows` holds indefinitely when `vietnam_political_will` is on** (the drain
   continues until freed or the war ends); non-will campaigns keep the 4-turn clock. The
   **Homecoming**: `resolve_pows_at_game_end` (from `process_win_loss`) repatriates every held
   blue POW on a negotiated **win** (a felt payoff) and writes them off on a withdrawal **loss**.

**Built on the existing pilot-mortality setting.** Every POW write-off (clock expiry *and* the
loss-ending) routes through `_write_off`, which respects `invulnerable_player_pilots` exactly
like the other kill paths: the player's own POW is **repatriated** rather than killed; an AI POW
is a permanent loss. This also fixed a latent bug — the old `surviving_pows` killed a player's
captured pilot at clock expiry even with invulnerable pilots set.

**§51 coupling stays honest.** "POW held = comms compromised" is time-boxed to
`COMMS_COMPROMISE_TURNS` (4) via a `captured_turn` stamp, so an indefinitely-held POW does not
jam the net forever — the squadron rotates its comms plan after a few turns even while the pilot
is still captive.

Files: `game/squadrons/pilot.py` (the POW status/`capture`/`repatriate`), `game/pow_recovery.py`
(`surviving_pows` will-awareness + `_write_off` + `resolve_pows_at_game_end`),
`game/sim/missionresultsprocessor.py` (capture flips status + stamps turn; the SITREP POW
lines), `game/game.py` (`process_win_loss` Homecoming), `game/sitrep.py` (`pows_held`),
`qt_ui/windows/SquadronDialog.py` (roster status), `game/missiongenerator/commsjamluadata.py`
(the compromise expiry). Tests: `tests/test_pow_recovery.py`,
`tests/squadrons/test_squadron_pilots.py`, `tests/test_sitrep.py`,
`tests/missiongenerator/test_commsjamluadata.py`. In-game pass: checklist G28. **Not shipped**
(unchanged from the rescope): the POW recovery raid stays shelved, red-side POWs stay out.

## On-demand rescue rework (2026-07-06) — the standing orbit is retired

The 2026-07-03 rescope kept the standing orbit + froze the AI-drama layer. A flown Inherent
Resolve session (`jovial-gates-574c9c`) then showed the orbit model does not work: two pilots
ejected, and the orbiting rescue helo the runtime tried to **commandeer** never flew the
pickup — it finished its racetrack and RTB'd to its homebase (checklist G21). Re-tasking an
already-airborne, already-routed group to a rescue is the thing that fails; **spawning fresh
into the rescue mission** (the clone path) is the thing that works.

So the user re-directed the model (squadron call): **make CSAR a plannable human package, and
replace the standing orbit with an on-demand AI rescue that spawns only when nobody fragged
one.** Three scenarios: (A) human in the King, AI in the other seats → don't spawn extra; (B)
full human package → don't spawn; (C) no package, players on the front line → spawn an AI
rescue to go get the downed pilot.

**What landed (v1):**
- **The standing orbit is removed.** `PlanCombatSar` / `PlanCombatSarSupport` /
  `combat_sar_targets` are gone; `auto_combat_sar` no longer auto-frags an orbiting package.
- **Player-plannable package** already existed and stays — `FrontLine.mission_types` offers
  `COMBAT_SAR` + `SCAR`, so a player builds a C-130 + helo(s) + A-10 Sandys off the FLOT.
- **On-demand AI rescue — parked-first, clone-fallback.** When a pilot goes down with no player
  package up, the runtime rescues from, in preference order:
  1. a **real untasked rescue helo parked cold on the ramp** — Retribution already spawns each
     squadron's spare airframes via `_spawn_unused_for` → `create_idle_aircraft` (uncontrolled,
     **and added to the `UnitMap`**). `spawn_combat_sar_templates` collects the BLUE CSAR-capable
     ones (`mission_data.parked_rescue_helos`); the plugin starts one in place
     (`StartUncontrolled`) and flies the OPSTRANSPORT pickup. Because it's a real `UnitMap`
     airframe, **its loss is recorded** — the tracked source. This is the user's insight (the
     armed C-130s/A-10s/helos already on the ramp) applied to the helo.
  2. a **cold late-activation clone template** (the QRA `spawn_intercept_templates` pattern) as the
     fallback when the ramp is bare (`perf_disable_untasked_blufor_aircraft`, or a fully-tasked
     wing) — SPAWN-cloned; the clone is **untracked**, like the pre-rework rescue clones.

  Both go straight into the pickup (the clone-into-mission path that works). **Why parked and not
  the old commandeer:** the retired dispatch commandeered an *airborne, already-routed* orbit helo,
  which RTB'd instead of rescuing (G21). A *parked* start is much closer to "fresh into mission" —
  the thing that works. BLUE only.
- **The gate:** a player CSAR/SCAR flight in the ATO ⟺ a player package ⟹ `autoSpawn=false`
  (no AI spawn; the package + ledger handle it). Nothing fragged ⟹ `autoSpawn=true`. Emitted as
  `dcsRetribution.CombatSAR.autoSpawn` + `parkedHelos` (preferred) + `heloTemplate`/`farp` (fallback).

**Deferred (v2, clearly marked so nobody assumes it shipped):**
- On-demand **Sandy + King** launches. The helo needs no loadout (it does OPSTRANSPORT), but a
  Sandy needs an armed payload (the configurator pass — neither a parked untasked airframe nor a
  cold template carries weapons: both are generated `maintask=None` / clean-wing) and a King needs
  its TACAN-beacon setup (`register_combat_sar_king`, only run for tasked King flights). So v1
  fields the essential rescuer only.
- **Multi-survivor chaining** ("grab the other guy on the way") — OPSTRANSPORT multi-cargo, once
  the core is flown.
- **Packaged-AI-helo auto-pickup** (scenario A's AI helo auto-flying the rescue) — that is the
  commandeer-an-airborne-helo problem; for now a player package coordinates the pickup
  (LARS/F10/voice), which scenario B does anyway.

**The fly-critical unknown:** the parked-helo *start-in-place* path (`GROUP:StartUncontrolled()` +
`FLIGHTGROUP:AddOpsTransport`) is a runtime path I can't verify headlessly — likely fine, but
unproven. It degrades safely: if a parked helo is commandeered but never launches, that survivor
isn't rescued that dispatch; the clone fallback covers the no-parked case. If the fly shows the
start-in-place doesn't work, make the clone primary.

Files: `game/commander/tasks/compound/theatersupport.py` (orbit removed),
`game/missiongenerator/aircraft/aircraftgenerator.py` (`spawn_combat_sar_templates` +
`_spawn_unused_for` collecting the parked pool),
`game/missiongenerator/aircraft/flightgroupspawner.py` (`create_combat_sar_template`),
`game/missiongenerator/missiondata.py` (`CombatSarTemplates` + `parked_rescue_helos`),
`game/missiongenerator/luagenerator.py` (`autoSpawn` gate + `parkedHelos`/template emit),
`resources/plugins/combatsar/combatsar-config.lua` (`autoSpawn` rename, the empty-`rescueHelos`
guard fix, `commandeerParkedHelo` + `StartUncontrolled`). Tests:
`tests/missiongenerator/test_combat_sar_sandy_luadata.py` (the gating + parked/clone emit),
`tests/missiongenerator/test_combat_sar_templates.py` (the template-spawn guards). In-game pass:
checklist G9 (the on-demand rescue actually flying + delivering). NEW game required (the orbit
task is gone + the parked pool / cold template is generated at start).

## Runtime hardening — snatch-party safety cap + ledger cleanup (2026-07-09)

Diagnosed from a user `dcs.log`: a heavy Red Tide (Germany Cold War) mission **hung** ~13 min in
— the log stopped mid-flood of MOOSE `UNIT.GetVec3` / `GROUP.GetCoordinate` errors with **no
crash dump** (a scripting/sim-thread hang, not a CTD; the 20-core / 130 GB rig was never the
limit — DCS runs scripting + the sim on one thread). Root cause: the enemy **capture race** had
spawned **8 snatch parties of 10 = 80 infantry** across two ejections. The plugin default is
5 infantry / 3 teams, but a **saved plugin-option override** (~40 / 4) was in force, so every
ejection dumped 40 real ground units — the dominant dynamic-spawn source — onto an already-heavy
plugin stack (MANTIS over 62 AD groups + TIC/GLSCO + SplashDamage + airbase harassment + TARS),
and the single-threaded sim bogged until it locked. Two fixes:

1. **Hard safety cap.** After the option parse, `capturePartySize` / `captureTeams` are clamped to
   `MAX_PARTY_SIZE` 12 / `MAX_TEAMS` 4 (floored at 1), warning once when a value is reined in. The
   capture race can no longer be the thing that freezes the sim regardless of a cranked or
   stale-saved value; the shipped defaults sit well inside the cap. plugin.json labels state both
   caps.
2. **Dead-reference cleanup** (the `GetVec3`/`GetCoordinate` flood was MOOSE polling dead DCS
   objects): `advanceCapture` now **prunes killed teams** out of `entry.party` each cycle (the
   per-poll scan shrinks as the party is attrited instead of re-scanning the full original list
   forever) and reads positions via a new `firstAliveCoord` helper (first *living* unit's
   coordinate, pcall-guarded — never calls `GetCoordinate` on a group whose lead unit is dead,
   which otherwise logged every poll). The main `tick` also **reaps a downed pilot killed on the
   ground** by finally assigning the designed-but-unused `dead` state — previously a pilot killed
   while `down` (never rescued, never captured) lingered in the ledger forever and had its dead
   group polled every 5 s.

`firstAliveCoord` also backs `findBoardingHelo`'s survivor read. Behavioral test:
`tests/lua/test_combatsar_capture_cap.py` runs the **real** plugin under Lua 5.1 with a cranked
config and asserts the clamp fires with the right numbers (combatsar is MOOSE-heavy and not in
the `DcsPluginHarness`, but the cap runs at file scope before any MOOSE wiring, so a tiny sandbox
drives it end to end). No `.miz` / save / New-Game requirement — it's a plugin-runtime fix that
takes effect on the next mission generation.

## What ships (the architecture that survived)

**Two flight types:**
- `COMBAT_SAR` — the rescue helo (CH-47/UH-1…) + the HC-130 "King" (air-tracking TACAN + the LARS
  F10 survivor locator). **Player-planned** off the FLOT, or spawned **on demand** by the runtime
  when no player package is up (the 2026-07-06 rework above; the standing orbit is retired). BLUE
  only — red flies NO CSAR, squadron call 2026-07-01.
- `SCAR` — the "Sandy" rescue escort (A-10/AH-64) in that package; protects the survivor,
  kills the snatch party, walks the helo in. Player-first; the AI divert (frozen G23) now applies
  only to a player-package's AI-crewed Sandy (no orbit to divert from in the AI-spawn path).

**The survivor ledger** (`resources/plugins/combatsar/combatsar-config.lua` — Route 1, the one
source of truth): every ejection registers a survivor (red smoke + mayday); player and AI
rescues are judged by the same land-near/low-slow geometry; a delivered survivor appends the
real airframe unit name to `combat_sar_rescues` (the pilot is spared at debrief — G11
verified); the opposing side may spawn a dispersed snatch party (G20 verified) and a party
holding on the pilot long enough CAPTURES them → `combat_sar_captures` → the held-POW model
above. AI dispatch **clones the cold rescue template into the mission** (the 2026-07-06 rework —
the old commandeer-the-orbit path is retired with the orbit; G21).

**AI-rescue delivery field (fixed 2026-07-03, flown Yankee Station):** the AI dispatch needs a
delivery airbase resolved via MOOSE `AIRBASE:FindByName`. Python passes the King's departure
*control-point display name* (`rescue_flights[0].departure.airfield_name`, `luagenerator.py`),
which matches a real airfield's DCS name but **not** a generated FARP — whose DCS object is
`"<CP> FARP 0"` (`tgogenerator.create_helipad`). So a FARP-based King (the Vietnam FOB case)
logged `combatsar: AI dispatch - FARP '<CP>' not found` on every ejection and never delivered.
`dispatchAIRescue` now falls back to `nearestFriendlyAirbaseObject` — the closest friendly field
MOOSE *can* resolve to the survivor — when the configured name misses (airbase-based Kings keep
their exact field; only the previously-broken FARP path changes). Consistent with the feature's
"deliver to ANY friendly field" contract. Needs a re-fly to confirm the AI actually completes the
delivery (G21/G23).

**Python side:** `game/pow_recovery.py` (the held-POW model + the tombstone purge),
`record_pow_captures` / `commit_air_losses` in `missionresultsprocessor.py` (scoring),
`game/missiongenerator/aircraft/aircraftgenerator.py` (`spawn_combat_sar_templates`, the
on-demand rescue). `game/ato/flightplans/combatsar.py` (the forward hold) is now only used by a
**player-planned** COMBAT_SAR flight — the standing-orbit auto-frag (`PlanCombatSar`) is deleted.
Save-compat tombstones for the retired SOF economy live in `game/scar_rescue.py`.

## Testing aids — thumb on the scale (2026-07-09)

A flown session left **both** downed pilots unresolved (no pickup, no capture), so G10/G23/G28
and the capture-gated §51 comms jamming (S4) all went unexercised end-to-end. Two problems: the
AI rescue is the flaky path, and a capture essentially never completes — the snatch party spawned
**2 NM** out and walked in at ~5.5 m/s (~11-min march, easily killed or simply out of the mission
window). Fixes:

- **Real tuning:** the snatch-party spawn default drops **2 NM → 0.75 NM** (`captureSpawnDistanceNm`
  in `plugin.json` + the Lua `capture.spawnDistance` fallback). ~4-min approach, still killable by a
  Sandy — a capture is now a real, occasional outcome in normal play instead of ~never. NEW game (or
  set the option) to take effect.
- **Two test toggles** (Settings → Campaign Management → HQ Automation, both **default OFF**), emitted
  as scalar flags on `dcsRetribution.CombatSAR` and honored by the plugin (applied *after* the normal
  options; force-capture wins if both set):
  - `combat_sar_test_force_capture` → `testForceCapture`: capture on, chance 100%, spawn 0.2 NM, seize
    radius 1000 ft, dwell 5 s. Every ejection → a fast, guaranteed **capture → POW**, which unlocks the
    capture-gated comms jam. The reliable way to exercise **G28 + S4**.
  - `combat_sar_test_easy_rescue` → `testEasyRescue`: capture off, pickup range 2000 ft / AGL 300 ft /
    speed 80 kt / delivery 3 NM, AI dispatch 30 s. A rough landing near the smoke boards the survivor —
    the reliable way to exercise **G10 King + G23 Sandy + the rescue/delivery loop**.

  Both are test aids, not gameplay — leave OFF for normal play. Emitter test:
  `tests/missiongenerator/test_combat_sar_sandy_luadata.py`.

## What is deliberately NOT here

- **No POW recovery raid** (2026-07-03, above). If a future squadron call wants it back, it
  needs a fresh design that makes the raid *player-first*, not another AI objective.
- **No red CSAR** (2026-07-01): the generator never emits `dcsRetribution.CombatSAR.red`; the
  plugin's red path is dormant capability only. Do not re-enable without a squadron call.
- **No SOF capture economy** (removed 2026-07-01) and **no armor-hunt SCAR** (deleted
  2026-06-27). The command-post intel fog (`scar_command_post_intel`) survived and lives with
  the recon-fog layer, not here.
- **No new AI choreography.** See freeze, above.

## Checklist map (docs/dev/414th-ingame-pass-checklist.md)

Verified: G8 (rescue), G9 (standing alert), G11 (scoring), G13 (airframes), G20 (snatch
party). Open: G10 (King TACAN radiating + LARS use — partial), G21 (commandeer preference —
partial), G23 (Sandy divert — the ONE re-fly, pass-or-delete). G22 (POW raid) is RETIRED with
the raid. Default-ON behavior rides G9's verified verdict.

## Superseded documents (historical record only)

`414th-combat-sar-spec.md` · `414th-combat-sar-normal-task-notes.md` ·
`414th-scar-rescue-rework-notes.md` · `414th-scar-task-spec.md` ·
`414th-scar-commander-sme-questions.md` · `414th-scar-phase2-sof-plan.md` ·
`414th-scar-HANDOFF.md` · `414th-scar-king-fac-notes.md`
