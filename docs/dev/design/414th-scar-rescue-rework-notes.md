# SCAR rework — survivor rescue: the King / Jolly Green / Sandy package (design)

**Status:** **Phases 1–3 MERGED** (PRs #241 / #243 / #245). **Phase 4 BUILT** (PR #247 — the POW
recovery loop: a CSAR raid or recapturing the holding airfield **frees** the held aviator; an abandoned
POW is **killed**). **Phase 5** (AI safety-net package + polish) designed below, not started. Supersedes
the armor-hunting "loiter-and-task under the King" rework (`414th-scar-king-fac-notes.md` — **retired**;
PR #189 to be abandoned, not merged). **Date:** 2026-06-27.

Phase 4 as built (Python): the held aviator is now a real stake. `PendingPowRecovery` carries the
captured `Pilot`. `commit_pow_recoveries` frees a POW when a **surviving CSAR flight** is fragged
against its `CapturedPilotGroundObject` (matched back by airframe unit name) — the aviator stays in the
squadron. `Coalition.end_turn` → `surviving_pows` applies the rest each turn: **recapturing the holding
airfield frees** the POW (pilot lives); the recovery **clock decrements** otherwise; at zero the POW is
abandoned and the **pilot is killed** (permanent loss). v1 limitation: a held pilot isn't pulled from
the active roster (minor fidelity gap); the freed/killed outcomes are the mechanic. (Doc-conflict
lesson: edit only this status block + append phase notes; don't fork the status across branches.)

Phase 2 as built: the `combatsar` plugin rolls a per-survivor chance that an enemy CJTF_RED infantry
**snatch party** (`mist.dynAdd`) spawns `captureSpawnDistance` from a downed pilot and walks at them
(red smoke + a coalition MAYDAY cue). A 5 s poll advances a capture clock while a party holds within
`captureRange`; at `captureDwell` seconds (pilot un-rescued) the pilot is **CAPTURED** — retired from
CSAR (`_RemoveNameFromDownedPilots`), its group destroyed, and `{unit, x, y}` appended to the
`combat_sar_captures` state global (declared + serialised in `dcs_retribution.lua`). Killing the party
first **saves** the pilot. Six plugin tunables (`captureEnabled`/`Chance`/`SpawnDistance`/`Range`/
`Dwell`/`PartySize`).

> **Phase 2 in-game pass owed:** eject near a blue Combat SAR package → sometimes red smoke + a snatch
> party appears and walks in → kill it = "party neutralized"; let it reach the survivor for the dwell =
> "CAPTURED" + the survivor despawns; `dcs.log` clean; `state.json` carries `combat_sar_captures`.

Phase 3 as built (Python; consumes the Phase 2 `combat_sar_captures` state global): `commit_air_losses`
spares a captured pilot the kill (a POW is not KIA) and `record_pow_captures` creates a
`PendingPowRecovery` (`game/pow_recovery.py`) on the blue coalition — persisted, save-migrated, aged on
a 4-turn recovery clock. `game/pow_objectives.py` rebuilds each POW every turn as a
`CapturedPilotGroundObject` at the nearest **enemy airfield** (anchored to a friendly CP for
ownership), offering **CSAR** recovery to the owning side only. Fail-safe: no captures = no-op. Phase 4
wires the actual recovery (delivering the POW home spares the aviator + an airfield-captured-frees-POW
path).

> **Doc sync owed:** `414th-features.md` §15, `README.md`, CLAUDE.md §15, and the in-game-pass checklist
> (F5/F7–F11 armor-SCAR rows) still describe the retired armor hunt — sync them once the rework's phases
> are merged, not before.
**Related:** [`414th-combat-sar-spec.md`](414th-combat-sar-spec.md) (the King + Jolly Green + MOOSE
`CSAR` engine this builds on), `414th-scar-king-fac-notes.md` (the retired armor direction),
`414th-scar-task-spec.md` (the original SCAR — fully superseded), CLAUDE.md §15 (SCAR) + §21 (Combat
SAR).

## Vision (user's words, locked 2026-06-27)

> SCAR is clunky and **SCAR should be for survivor rescue**. Big picture: a standing package of **1
> KING, 1 JOLLY GREEN, and 2–4 SCAR players** (A-10s or Apaches) to assist the downed pilot. And **a
> random element where the enemy will try to grab the downed pilot.**

This is textbook USAF combat-SAR doctrine. SCAR stops being "Strike Coordination and Reconnaissance"
and becomes the **rescue-escort ("Sandy")** role inside a combat-SAR package:

| Element | Doctrinal role | Airframe | Source |
|---|---|---|---|
| **KING** | Airborne mission commander | C-130J | reuse Combat SAR King (TACAN + LARS + voice-first cueing) |
| **JOLLY GREEN** | The rescue / pickup | helo (CH-47…) | reuse Combat SAR rescue helo + MOOSE `CSAR` engine + debrief scoring |
| **SANDY** ×2–4 | RESCAP escort — protect the survivor, kill threats, walk Jolly in | A-10C / AH-64D | **repurposed `FlightType.SCAR`** |

## The three locked forks (AskUserQuestion, 2026-06-27)

1. **Repurpose `FlightType.SCAR` → rescue escort.** Retire the armor-hunting identity entirely; stop
   and **do not merge #189**. The UI label stays **"SCAR"** (zero save migration; the squadron knows
   the name) — only the role changes.
2. **Both player + AI safety net.** Players fly the package; an AI standing alert (extend
   `auto_combat_sar`) fields **King + Jolly + 1 Sandy** so a downed human gets a rescue attempt even
   with no players up. (Players bring the other 1–3 Sandys.)
3. **Captured = POW, recoverable by a SOF raid.** If the enemy grabs the survivor, the pilot becomes a
   **POW held at an enemy location (an airfield / holding point)** — worse than simply un-rescued, but
   you can mount a **raid to get them back**. Recovering them spares the aviator at debrief.

## Core architecture decision: it all rides on the `combatsar` plugin

The `combatsar` plugin (`resources/plugins/combatsar/combatsar-config.lua`) already owns the **entire
rescue lifecycle** for a downed pilot: it hooks MOOSE `CSAR`'s ejection event, spawns the downed pilot
with a beacon, runs the board/deliver FSM, scores the rescue (`combat_sar_rescues`), runs the King's
TACAN/LARS, **and** already extracts stranded SOF teams via a CASEVAC path (`SOFRESCUE_` channel).

So the rework does **not** introduce a second runtime brain. The capture race and the Sandy cueing
ride on the existing `dcsRetribution.CombatSAR` data table — the one place that already knows where
every survivor is. The retiring `scar` plugin's armor-hunt scenario is **not** the substrate.

- **KING + JOLLY GREEN** = the existing `COMBAT_SAR` flights (C-130 = King, helo = pickup). Reused.
- **SANDY** = `FlightType.SCAR`, gutted of armor-hunting and rebuilt as a RESCAP escort role planned
  into the package; its runtime cueing comes through `combatsar`, not a separate scenario script.

## What gets retired vs. kept vs. repurposed

**Retire (the clunky armor-hunt machinery):**
- The spawned/`armor`/`missile` **runner scenario** — the moving-HVT chase that flees to a city
  (`game/missiongenerator/scarluadata.py` HVT/decoy/clutter picture + routing; the
  `spawn`/`armor`/`missile` paths in `resources/plugins/scar/scar_414_init.lua`).
- The **SCAR auto-planner**: `PlanScarHunts` (`compound/scarhunts.py`) + `PlanScar`
  (`primitive/scar.py`) + the `scar_autoplan` / `scar_autoplan_per_turn` settings +
  `scar_hunts_planned` state. **This is what restores BAI** — the auto-planner was *stealing* enemy
  armor battle-positions from BAI; removing it lets BAI claim them all again. `bai.py` itself is
  untouched.
- The `scar_results` scoring skeleton (never needed — see below).
- The offensive **capture-an-enemy-commander objective** (it hung off the armor picture's command
  vehicle; with the armor picture gone it has no anchor). ⚠️ **Confirm with user** — see open items.

**Keep & repurpose (the rescue substrate — this is the win):**
- `game/scar_rescue.py` `PendingSofRescue` + `Coalition.pending_csars` + the turn-cap/overrun loss
  clock + inventory refund → the model for `PendingPowRecovery`.
- `game/scar_objectives.py` (`DownedSofGroundObject`, rebuilt each turn as a CP-anchored map
  objective) → the model for the **POW-held-at-airfield** objective.
- The `combatsar` CASEVAC recovery path + the `SOFRESCUE_` name-routing channel → the model for the
  POW pickup/recovery channel.
- `FlightType.CSAR` (helo recovery) + `FlightType.SOF` (C-130 insert) — the raid airframes that grab
  the POW. Untouched.

**Repurpose:**
- `FlightType.SCAR` enum **value stays `"SCAR"`** (save-compat); docstring/intent → Sandy RESCAP
  escort. Membership in `is_air_to_ground` stays (it shoots); revisit `is_primary_package_task`.
- The SCAR flight plan → a RESCAP escort orbit anchored on the rescue area / FLOT (reuse the
  `CombatSarFlightPlan` front-anchored geometry, **not** the armor kill-box loiter).

## Phased build (each phase = own branch + in-game pass; never merge unflown)

| Phase | Scope | Verifiable by |
|---|---|---|
| **1 — Repurpose SCAR + clear the deck** | Gut the armor runner scenario + `scar_results`; remove `PlanScarHunts`/`PlanScar` + `scar_autoplan*` (restores BAI); abandon #189. Rewrite `FlightType.SCAR` → Sandy; rescue-escort orbit flight plan; SCAR task eligibility on **A-10C + AH-64D**. Confirm King + Jolly + 2–4 Sandy frag as one package. | Retribution app (no DCS): generation succeeds, Black/mypy/pytest green |
| **2 — The enemy capture race** | Emit capture params into `dcsRetribution.CombatSAR`. On downed-pilot spawn, sometimes spawn an enemy **snatch party** that races to the survivor; King smokes/marks/calls it so Sandy engages; party reaches survivor first → **CAPTURED** (despawn pilot, write a new `combat_sar_captures` state global). | In-game `.miz`: eject → snatch party races → kill it to save / let it arrive to lose; `dcs.log` clean |
| **3 — Capture → POW objective** | Python parses `combat_sar_captures`; a captured pilot becomes a **POW** at debrief (distinct from KIA and from un-rescued) and creates a `PendingPowRecovery` **anchored at an enemy airfield/holding point**, surfaced as a map objective (mirror `scar_objectives.py`). | Retribution app: capture → debrief shows POW + a recovery objective at an enemy field |
| **4 — Raid to recover the POW** | Wire `PendingPowRecovery` into the recovery path (SOF/CSAR raid or Combat SAR CASEVAC at the holding field): recovering the POW **spares the aviator** (deferred `combat_sar_rescues` credit). Turn-cap/overrun loss clock from `scar_rescue.py`. | Retribution app: capture turn N → raid turn N+1 → pilot back |
| **5 — AI safety net + polish** | Extend `auto_combat_sar` to field King + Jolly + **1** Sandy. Kneeboards (Sandy RESCAP page; King capture callouts), SITREP line, night/illum cues, naming polish. | In-game + app |

### Why scoring is nearly free
Killing the snatch party attrits enemy ground units through the **normal ground-loss path** (real
TGOs). Saving the pilot reuses the **existing** `combat_sar_rescues` debrief credit. The POW recovery
reuses the **existing** `commit_sof_recoveries` shape. Net-new scoring code is just the
`combat_sar_captures` → POW bridge (Phase 3).

## The capture race (net-new mechanic, Phase 2) — design

- **Trigger:** MOOSE `CSAR` downed-pilot spawn (the `combatsar` plugin already sees this).
- **Roll:** with a configurable probability, spawn an enemy **snatch party** (technicals / infantry /
  light APC — vanilla DCS units) a configurable distance from the survivor, ordered to move to them.
- **Cue (voice-first, additive):** King smokes/marks the snatch party + one MAGIC call ("troops
  moving on your survivor, bearing X") so Sandy is vectored to kill it. Same additive/skippable rule
  as the existing King designation ([[king-is-a-talking-player-srs]]).
- **Capture check:** if a snatch-party unit dwells within capture range of the survivor for N seconds
  *and* the pilot hasn't been picked up → **CAPTURED**: despawn the downed pilot, append to
  `combat_sar_captures` (location + original airframe unit name, like `combat_sar_rescues`).
- **Tunables (plugin options):** spawn probability, party composition, spawn distance / time-to-arrive,
  capture range, dwell-to-capture seconds, enable flag.

## POW-held-at-airfield (Phase 3/4) — design

`combat_sar_captures` (location + airframe name) → a `PendingPowRecovery` on the coalition (mirror
`PendingSofRescue`: `turns_remaining`, `anchor_cp_id`, refund/credit on recovery). The POW is **moved
to / held at the nearest enemy airfield or holding point** (user call: "an airfield we have to grab
them at") rather than left at the ejection site — so the recovery is a **raid objective** at a real
enemy field, not a quiet pickup. Surfaced each turn as a map objective (mirror
`sync_downed_sof_objectives`). Recovering it (SOF/CSAR raid or CASEVAC delivery home) routes through a
`POW_` name channel → spares the aviator at debrief. Loss clock: the existing turn-cap/overrun model.

## Open items to confirm

1. **Fate of the offensive commander-capture objective (§15) — deferred, not a Phase 1 blocker.**
   Phase 1 does **not** delete it: leave the whole SOF/CSAR insert-capture-recovery machinery
   **dormant** (Phase 1 just stops producing armor scenarios, so there's nothing to capture from) and
   **repurpose** it for POW rescue in Phase 3/4. Final call on whether the offensive
   "capture-an-enemy-commander" *objective* is revived or dropped happens when Phase 3 wires the POW
   producer — by then we'll know exactly how much of the plumbing the POW path reuses.
2. **Where exactly the POW is held** — nearest enemy airfield vs. nearest enemy CP vs. a dedicated
   holding point. Default: nearest enemy airfield (matches the user's framing). Settle in Phase 3.
3. **AI Sandy airframe cost** — King + Jolly + 1 Sandy per side when `auto_combat_sar` is on. Confirm
   in Phase 5.
4. **`scar_command_post_intel` setting** — currently gates the SOF map objectives; likely renamed /
   repurposed to gate the POW objective in Phase 3.

## Definition of done (v1, the full arc)

A player frags (or the AI alert fields) a **King + Jolly Green + 2–4 Sandy** package. A human ejects;
the downed pilot spawns with a beacon. Sometimes an enemy snatch party races to grab them — the King
cues the Sandys, who kill it to protect the survivor; Jolly Green lands and recovers the pilot, who is
**spared at debrief** (airframe still lost). If the snatch party wins, the pilot is a **POW held at an
enemy airfield**, recoverable next turn by a **SOF/CSAR raid**. Killing the snatch party attrits the
enemy natively. No `dcs.log` errors; the SOF-recovery plumbing is intact and repurposed, not deleted.
