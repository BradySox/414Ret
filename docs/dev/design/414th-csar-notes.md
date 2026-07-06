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

## What ships (the architecture that survived)

**Two flight types:**
- `COMBAT_SAR` — the standing package: rescue helo (CH-47/UH-1…) holding a forward FLOT
  racetrack + the HC-130 "King" overhead (air-tracking TACAN + the LARS F10 survivor locator).
  Auto-fragged per active front by `PlanCombatSar` when `auto_combat_sar` is on (BLUE only —
  red flies NO CSAR, squadron call 2026-07-01); a player can fly any seat.
- `SCAR` — the "Sandy" rescue escort (A-10/AH-64) in that package; protects the survivor,
  kills the snatch party, walks the helo in. Player-first; the AI divert is the frozen G23.

**The survivor ledger** (`resources/plugins/combatsar/combatsar-config.lua` — Route 1, the one
source of truth): every ejection registers a survivor (red smoke + mayday); player and AI
rescues are judged by the same land-near/low-slow geometry; a delivered survivor appends the
real airframe unit name to `combat_sar_rescues` (the pilot is spared at debrief — G11
verified); the opposing side may spawn a dispersed snatch party (G20 verified) and a party
holding on the pilot long enough CAPTURES them → `combat_sar_captures` → the held-POW model
above. AI dispatch prefers commandeering the on-station rescue helo over cloning (G21).

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
`game/commander/tasks/primitive/combatsar.py` (the standing package),
`game/ato/flightplans/combatsar.py` (the forward hold). Save-compat tombstones for the retired
SOF economy live in `game/scar_rescue.py`.

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
