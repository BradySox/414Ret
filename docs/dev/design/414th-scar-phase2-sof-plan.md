# SCAR Phase 2 — SOF airdrop + commander capture (implementation plan)

Status: **2a BUILT** (scripted capture loop), gated OFF behind `scar_command_post_intel`;
**2b/2c not started**. Phase 1 (the reveal/intel side) is built and merged. This doc plans
Phase 2: the mechanic that **produces a `captured` SCAR result**, which Phase 1 consumes.

Read first: `414th-scar-task-spec.md` (§9 capture design) and
`414th-scar-commander-sme-questions.md` (SME answers 2026-06-18).

> **2a as built (first pass, decisions confirmed 2026-06-18):** scripted auto-drop +
> ambush-on-route + guaranteed-on-proximity. When `scar_command_post_intel` is on, the
> generator drops a friendly SOF team (`ctld`-independent `mist.dynAdd` infantry) at
> `SCAR_SOF_LEAD_FRAC` (0.7) of the HVT's spawn→dest route; the SCAR plugin's `scar_check`
> resolves `captured` when the (un-killed) command vehicle drives within
> `SCAR_SOF_CAPTURE_RADIUS_M` (600 m). Outcome priority: killed (success) > captured > escaped
> /timeout (fail). Spawn + armor variants only (a SCUD is not a commander). **Known 2a
> simplification:** the team always drops and capture is automatic on proximity, so with the
> setting on, an un-killed HVT is effectively always captured — that becomes a deliberate
> choice once SOF is finite/player-delivered (2b/2c). Files:
> `game/missiongenerator/scarluadata.py` (`_sof_ambush`, `sof_*` fields, `_emit_sof`),
> `resources/plugins/scar/scar_414_init.lua` (`spawn_sof`, `hvt_in_sof_zone`, the `captured`
> branch, `mark_sof`). Tests: `tests/test_scar_bridge.py` (SOF emission on/off + point on
> route). Lua still needs an in-game pass.

---

## 1. Goal

Let the player **capture** the fleeing SCAR HVT commander instead of only killing/missing
it. A SOF team is delivered ahead of the HVT; if the HVT is taken, the SCAR area resolves
`captured` → Phase 1 reveals the enemy command posts next turn. A botched grab = the
commander escapes (fail) **but the SOF team is recoverable via CSAR** (SME #6).

What Phase 1 already gives us (don't rebuild):
- `Coalition.captured_commander` (persisted + migrated) and the reveal gating
  (`hidden_on_player_map` / `_command_post_revealed`).
- `MissionResultsProcessor.commit_scar_results` flips the flag on a `captured` result.
- The SCAR **armor/spawn HVT already carries a command vehicle** (`SCAR_COMMAND =
  "Ural-375 PBU"`, PR #29) — that is the capture target. It's tracked in `area.groups`
  and `area.commandType` in `scar_414_init.lua`.

## 2. SME rulings driving Phase 2

- **#5 finite SOF: yes** — consumable teams. **#7 scale:** ~2–3 per campaign.
- **#6 botched capture:** the commander **escapes** (the area still fails), but the SOF
  team is **recoverable** (CSAR / extract) — it is not automatically lost.

## 3. Building blocks already in the repo (reuse, don't write from scratch)

- **`resources/plugins/ctld/` — CTLD 1.6.1** (ciribob, ON by default; updated in PR #32).
  Spawns/loads/unloads troops + crates, JTAC autolase. Config in `ctld-config.lua`.
- **CTLD is already wired into Retribution** for air assault / airlift:
  `game/theater/interfaces/CTLD.py`, `game/ato/flightplans/airassault.py`,
  `game/ato/flightplans/airlift.py`, `game/ato/flightplans/_common_ctld.py`. The
  `dcsRetribution.Logistics` Lua table (transports, pickup/drop/target zones, crates) is
  the existing seam.
- **MOOSE `Ops.CSAR`** (`CSAR:New(Coalition,Template,Alias)`) and **`Ops.CTLD`**
  (`CTLD:New(...)`) in `resources/plugins/base/Moose.lua` — for the recovery leg.
- **`dismounts`** plugin (infantry) and the SCAR plugin's own `mist.dynAdd` spawning
  (`spawn_convoy` in `scar_414_init.lua`) — either can spawn the SOF team.
- The proven SCAR **results channel**: `scar_results` (global) → `dcs_retribution.lua`
  `write_state` → `StateData` → `commit_scar_results`.

> ⚠️ CTLD's header warns it needs **its bundled MIST version** for dynamic spawns —
> confirm Retribution's MIST is current enough during 2a in-game testing.

## 4. The loop (design)

1. **Deliver** a SOF team to a drop point **ahead of the HVT** on its spawn→dest route
   (ambush model — SOF on foot can't chase a moving convoy; the HVT drives into them).
2. **Capture**: while the SCAR area is live, track distance between the SOF group and the
   HVT command vehicle. When the command vehicle enters `SOF_CAPTURE_RADIUS`, resolve
   `captured`: despawn the command vehicle as *taken* (not "escaped"), mark
   `scar_results[id] = "captured"`.
3. **Botched** (HVT reaches the city / window expires before capture): the area fails as
   today, and the SOF team is left on the ground as a **CSAR pickup**.
4. **Recover**: a player helo extracts the SOF team → the team returns to the finite pool.
   Not extracted by mission end → team lost (pool not refunded).
5. **Carryover**: `commit_scar_results` already flips `captured_commander` on `captured`;
   Phase 2 additionally adjusts the SOF pool from the team's disposition.

## 5. Component breakdown + integration points

### Python
- **Finite SOF asset**: `Coalition.sof_teams: int` (persisted, `__setstate__` migration
  default ~2–3). Decrement on commit when a team is deployed; restore on CSAR recovery.
  Pattern to copy: `game/squadrons/intercept_reserve.py` + `Coalition.captured_commander`.
- **Delivery** (decision in §7): either a new `FlightType.SOF` (air-assault-like, reuse
  `airassault.py` + CTLD) or a SCAR sub-option that scripts the drop. Start scripted (2a).
- **scarluadata**: emit the SOF drop point + capture params per SCAR tasking (drop point =
  a point on the HVT route a set distance ahead of the HVT spawn).
- **Results**: extend `commit_scar_results` (or a parallel `sof_results`) to adjust
  `sof_teams` from `captured` / `sof_recovered` / `sof_lost`.
- **UI**: SOF pool count + per-turn use, likely on the Campaign Doctrine page (where the
  SCAR + QRA settings already live), or a small recruitment-style panel.

### Lua (`scar_414_init.lua`, or a new `sof` plugin mirroring the SCAR inject)
- Spawn/track the SOF team (CTLD troop group or `mist.dynAdd` infantry).
- Proximity-capture vs `area.commandType` / the command group already tracked in `area.groups`.
- On botch, register the SOF group with MOOSE `Ops.CSAR` (or CTLD) as a downed-team pickup.

## 6. Build order (sub-phases — ship + validate each)

- **2a — core capture loop (scripted, infinite SOF). ✅ BUILT** (gated OFF; needs an in-game
  pass). Scripted SOF ambush dropped ahead of the HVT + proximity capture producing
  `captured`. No pool yet. Reuses the SCAR Lua + command vehicle. See the status note at the
  top of this doc for the files and the known first-pass simplification.
- **2b — finite SOF asset.** `Coalition.sof_teams` + decrement-on-use + UI + the carryover
  in `commit_scar_results`.
- **2c — CSAR recovery + (optional) player-flown delivery.** MOOSE `Ops.CSAR`/CTLD pickup
  on botch returning teams to the pool; optionally a real player-flown SOF insert via CTLD
  instead of the scripted drop.

## 7. Open questions to settle before/early in 2a (don't guess)

1. **Delivery:** scripted auto-drop (start here) vs player-flown SOF insert (CTLD radio
   menu / air-assault)? *Recommendation: scripted for 2a to prove the loop; add player-flown
   in 2c.*
2. **Capture trigger:** ambush-on-route (drop ahead, HVT drives in — *recommended, matches
   "drop ahead of the HVT"*) vs catch-when-stopped (player must immobilize the HVT first)?
3. **Capture success:** guaranteed on proximity, or probabilistic (and is there any AAA/
   escort interaction)?
4. **CSAR tech:** MOOSE `Ops.CSAR` vs CTLD's own CSAR vs a simple "auto-recover if the SOF
   group survived to mission end"? (Cheapest first.)
5. **SOF pool UI location** + default count (SME #7 says 2–3).

## 8. First-thing-tomorrow recon checklist

- [ ] CTLD 1.6.1: find the function to spawn an infantry group at arbitrary coords
      (`ctld.spawnGroup` / `deployTroops` / equivalent) and how `airassault.py` drives it.
- [ ] MOOSE `Ops.CSAR:New` usage + how to register an existing ground group as a CSAR
      target (vs spawning a downed pilot).
- [ ] Re-read `scar_414_init.lua` capture handles: `area.commandType`, the command group
      name appended to `area.groups`, and where to add a `scar_check` proximity branch.
- [ ] Confirm Retribution's MIST version vs CTLD 1.6.1's requirement (dynamic spawns).
- [ ] Decide §7 Q1/Q2 with the user, then implement 2a.
