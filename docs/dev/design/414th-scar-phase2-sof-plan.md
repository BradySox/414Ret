# SCAR Phase 2 — SOF airdrop + commander capture (implementation plan)

Status: **2a + 2c-1 BUILT** (scripted capture loop + finite bought inventory asset), gated
OFF behind `scar_command_post_intel`; **2c-2/2c-3 not started**. Phase 1 (the reveal/intel
side) is built and merged. This doc plans
Phase 2: the mechanic that **produces a `captured` SCAR result**, which Phase 1 consumes.

Read first: `414th-scar-task-spec.md` (§9 capture design) and
`414th-scar-commander-sme-questions.md` (SME answers 2026-06-18).

> **2a as built (first pass, decisions confirmed 2026-06-18):** scripted auto-drop +
> ambush-on-route + guaranteed-on-proximity. When `scar_command_post_intel` is on, the
> generator drops a friendly SOF team (`ctld`-independent `mist.dynAdd` infantry) at
> `SCAR_SOF_LEAD_FRAC` (0.7) of the HVT's spawn→dest route; the SCAR plugin's `scar_check`
> resolves `captured` when the (un-killed) command vehicle drives within
> `SCAR_SOF_CAPTURE_RADIUS_M` (600 m) and the spawned SOF group still has survivors.
> Outcome priority: killed (success) > captured > escaped
> /timeout (fail). Spawn + armor variants only (a SCUD is not a commander). **Current
> simplification:** delivery is still scripted and capture is automatic on proximity when a
> bought team is available and survives; player-flown delivery arrives in 2c-2. Files:
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

---

## 9. Phase 2c full design — inventory-backed SOF + air-assault insert (CHOSEN 2026-06-18)

Decision: the SOF is a **real, procurable, naturally-finite campaign asset** delivered by an
**air-assault insert**, not an abstract counter with a scripted drop. (Generic CP→CP transfers
were considered and rejected: `TransferOrder` only routes between friendly control points over
the transit network — it can't deliver to the HVT's ambush point in enemy territory.) Tyler is
hands-off, so this builds on the **existing upstream air-assault** (`AirAssaultFlightPlan` +
CTLD), using his `DEPLOYMENT` notes only as a reference pattern — not a dependency.

### Grounding (verified in-tree)
- Inventory: `ControlPoint.base.armor: dict[GroundUnitType, int]`; `Base.commission_units` /
  `commit_losses`; ground procurement via `game/groundunitorders.py`. `UnitClass.INFANTRY`
  exists; factions expose `infantry_units` + `infantry_with_class(UnitClass)`.
- Delivery: `FlightType.AIR_ASSAULT` + `AirAssaultFlightPlan` (CTLD target zone, pickup,
  `ctld_target_zone_radius`) already air-deliver troops to an arbitrary zone, incl. enemy.

### Model
- **SOF asset** = a faction-valid infantry `GroundUnitType` (selected via `infantry_with_class`,
  or a designated per-faction SOF unit), held in `base.armor`. The **pool** is the coalition's
  inventory count of that unit — this REPLACES `Coalition.sof_teams` (supersedes PR #36's
  counter). Seed a couple at rear bases at campaign start and/or let players buy them.
- **Delivery** = a SOF insert flight (a new `FlightType.SOF`, air-assault-shaped, reusing
  `AirAssaultFlightPlan`) targeting the SCAR area's ambush point. Fragging the flight debits one
  SOF unit from the origin base (like air-assault consumes its troops). The delivered team is
  the capture team.
- **Capture** = the existing 2a Lua proximity check, pointed at the delivered team's drop point
  (the air-assault target zone == the SCAR `sof` point) instead of the scripted `spawn_sof`.
  Keep `spawn_sof` only as a dev/fallback when no SOF flight is planned (or drop it).
- **Outcome accounting** (`commit_scar_results` + end-turn): captured = team did its job;
  botched = stranded → CSAR. Recovery re-commissions the unit into a base; un-recovered = lost
  (inventory not refunded).

### Slice order (each ships gated OFF + CI-green; Lua needs an in-game pass)
- **2c-1 — `FlightType.SOF` + air-assault delivery spine.** New flight type (categorize like
  AIR_ASSAULT; dispatch to `AirAssaultFlightPlan`; save migration), offered against SCAR-eligible
  targets; delivers a team (CTLD troops for now) to the SCAR ambush zone. Wire the 2a capture to
  the delivered team. Cargo still abstract (no inventory yet).
- **2c-2 — inventory backing.** SOF = an infantry `GroundUnitType`; pool = inventory count
  (replace `Coalition.sof_teams`); debit on frag; gate the insert on availability; seed/procure.
  Retire the counter (and PR #36's approach).
- **2c-3 — CSAR recovery.** Stranded SOF → MOOSE `Ops.CSAR`/CTLD pickup → re-commission on
  extract; else lost. Refines the "deploy-but-no-capture" accounting left open by 2b.

### Tyler-coordination seams (he's a reference, not a blocker)
Shared surface his `DEPLOYMENT` also touches — keep diffs small + update the `COMMIT_STEPS`
test if both add commit steps: `game/ato/flighttype.py` (enum + migration), `Coalition`,
`MissionResultsProcessor`, and the air-assault/CTLD wiring. If his branch ever lands, our
`FlightType.SOF` + inventory-debit-on-frag should converge onto his `PendingDeployments` shape.

### 9b. Chosen asset model (2026-06-18): **dedicated SOF unit, bought**

The SOF team is a **distinct, buyable** ground unit (not reused front-line infantry). Implications
+ concrete steps (each a small, CI-green commit; gated behind `scar_command_post_intel`):

- **Define the unit.** Add SOF `GroundUnitType` YAML(s) under `resources/units/ground_units/`
  backed by a vanilla DCS infantry model, faction-appropriate per side (blue ≈ `Soldier M4 GRG`,
  red ≈ `Infantry AK Ins`/`Paratrooper RPG-16`), with a `price` and `unit_class: INFANTRY`.
  Distinct `variant_id` (e.g. "SOF Team (BLUFOR)") so it reads as a separate asset and the
  capture Lua can spawn that exact type.
- **Make it buyable without editing every faction JSON.** Most factions are WWII/irrelevant, and
  the feature is gated. Inject the side-appropriate SOF unit into the buyable set **in code**,
  only when `scar_command_post_intel` is on — extend the procurement/`accessible_units` path
  rather than touching dozens of `resources/factions/*.json`.
- **Pool = inventory count.** Sum the SOF unit across the coalition's `control_point.base.armor`.
  Replaces any counter. Generation gate (`build_scar_taskings`): emit a SOF drop only while the
  pool has teams (cap per turn = available count).
- **Consume.** `commit_scar_results`: a `captured` result debits one SOF unit from a base
  (`base.commit_losses`). (2c-3 CSAR can re-`commission_units` a recovered team.)
- **Spawn the bought type.** The capture team the Lua drops uses the SOF unit's DCS type
  (emit it from Python), snapped onto land via `_on_land`.

**Revised slice order:** 2c-1 inventory asset (unit + buyability + pool + gate + consume +
land-snap; scripted drop for now) → 2c-2 air-assault SOF insert (`FlightType.SOF`, the real
"fly it in", debit on frag) → 2c-3 CSAR recovery. Note `SCAR_SOF_LEAD_FRAC` is temporarily 0.3
(restore to 0.7) — a separate test knob, not part of this work.

### 9c. 2c-1 buyability/pool — de-risked design (verified 2026-06-18)

Key finding: `base.armor` is the front-line combat pool, BUT `ai_ground_planner` only deploys
TANK/APC/ARTILLERY/IFV/LOGI/ATGM/SHORAD/AAA/RECON classes — **INFANTRY falls through to the
`else` and is skipped**. And AI ground procurement (`procurement.affordable_ground_unit_of_class`)
draws only from `faction.frontline_units`/`artillery_units`. So a SOF unit of class INFANTRY:
- is **never auto-deployed to the front** (skipped by the planner), and
- is **never bought/used by the AI** as long as we keep it OUT of `frontline_units`.

So no faction mutation and no procurement guard are needed. Implementation (all gated on
`scar_command_post_intel`):
1. **Buyable (player only):** in `qt_ui/.../QArmorRecruitmentMenu.py`, add the side's SOF unit
   (`SOF Team (BLUFOR)`/`(OPFOR)`) to the buy list when the setting is on. The AI's
   `frontline_units`-based procurement is untouched, so only the human can buy SOF.
2. **Pool = inventory count:** sum the side's SOF `GroundUnitType` across the coalition's
   `control_point.base.armor`. `build_scar_taskings` gates SOF drops on it (cap per turn =
   count), replacing the always-drop.
3. **Spawn the bought type:** emit the SOF unit's DCS id in the tasking; the Lua spawns that
   instead of the hard-coded `Soldier M4`. Snap via `_on_land`.
4. **Consume:** `commit_scar_results` debits one SOF unit from a base (`base.commit_losses`)
   per `captured`.

Units defined + verified (commit 81bc1fb69): `SOF Team (BLUFOR)` (Soldier M4 GRG) / `(OPFOR)`
(Infantry AK), price 8, spawn_weight 0.

**2c-1 BUILT (gated OFF; Lua needs an in-game pass).** All four steps above are wired:
`_sof_asset` (pool count), the `build_scar_taskings` gate + per-turn cap, `sofUnitType`
emission + Lua `spawn_sof` using it, and `_consume_sof_teams` on capture. Tests in
`test_scar_bridge.py` (pool gate / cap / unit-type) + `test_scar_command_post_fog.py`
(capture consumes a team). Follow-up audit fixes keep SOF out of front-line deployment /
strength / redeployment math, require a living spawned team for capture, prefix tasking IDs
with coalition so RED results cannot spend/reveal BLUE assets, and spend BLUE inventory before
base-capture ownership flips. **Remaining:** 2c-2 air-assault delivery (`FlightType.SOF`)
replacing the scripted drop; 2c-3 CSAR recovery.
