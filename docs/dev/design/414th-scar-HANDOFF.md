# SCAR commander-capture — session handoff

One-screen pickup for the multi-session SCAR commander-capture feature. The territory
(design rationale, slice plan, de-risking) is in
[`414th-scar-phase2-sof-plan.md`](414th-scar-phase2-sof-plan.md) (§9/§9b/§9c); the
engineering deep-dive is [`../414th-features.md`](../414th-features.md) §15. This file is
just the map: where we stand, what's next, and the gotchas.

Last updated: 2026-06-18 (build current at `613f7d899`).

---

## Where `main` stands

All merged; the build is current.

| Area | Status |
|---|---|
| Phase 1 — command-post intel fog | ✅ merged, gated OFF (`scar_command_post_intel`) |
| Phase 2a — SOF capture loop | ✅ merged, confirmed in-game (`area scar-2 (armor) -> captured`) |
| Phase 2c-1 — finite bought SOF pool (#51) | ✅ merged, gated OFF |
| Perf fix (#49), `LEAD_FRAC` 0.7 (#50), decoy scatter (#52) | ✅ merged |
| Phase 2b — `Coalition.sof_teams` counter | superseded by 2c-1's inventory model (PR #36 closed) |

## To use it in-game

1. `git pull` in 414Ret → regenerate the mission.
2. Turn on `scar_command_post_intel` (Campaign Doctrine settings).
3. Buy a **SOF Team (BLUFOR)** at a base (price 8). Fly a SCAR sortie; if you don't kill
   the HVT, the SOF captures it → command posts reveal next turn → one SOF team is spent.

## What's NOT built yet (next session)

- **2c-2 — air-assault delivery.** `FlightType.SOF` on the existing `AirAssaultFlightPlan`
  + CTLD, replacing the scripted drop ("fly the team in"). This is the big remaining piece.
- **2c-3 — CSAR recovery** of a stranded team after a botched grab.

## Where everything lives

- Design + slice plan + de-risking: [`414th-scar-phase2-sof-plan.md`](414th-scar-phase2-sof-plan.md) (§9/§9b/§9c).
- Engineering deep-dive: [`../414th-features.md`](../414th-features.md) §15.
- Ground truth / SME answers: [`414th-scar-task-spec.md`](414th-scar-task-spec.md),
  [`414th-scar-commander-sme-questions.md`](414th-scar-commander-sme-questions.md).
- Python: `game/missiongenerator/scarluadata.py` (`_sof_ambush`, `sof_*` fields,
  `_emit_sof`).
- Lua: `resources/plugins/scar/scar_414_init.lua` (`spawn_sof`, `hvt_in_sof_zone`, the
  `captured` branch, `mark_sof`).
- Tests: `tests/test_scar_bridge.py` (SOF emission on/off + point-on-route).
- Worktrees: `414Ret-2c` is the SCAR worktree (off `scar-phase2c-sof`); leave
  `414Ret-scar` for quick side-branches — that split is what stopped the collisions.

## Gotchas for whoever picks it up

- The whole feature is **gated OFF**; the Lua half (capture/spawn) is validated by in-game
  passes, not CI.
- Tunables: `SCAR_SOF_LEAD_FRAC` (0.7), SOF price (8), spawn `spawn_weight` (0).
- 2c-2 lands on the same `Coalition` / `MissionResultsProcessor` / `FlightType` surface as
  Tyler's DEPLOYMENT work — he's hands-off, so **build on upstream air-assault**, using his
  notes as a reference pattern only.
