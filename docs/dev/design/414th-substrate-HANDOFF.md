# Substrate work — HANDOFF (start here)

For the local agent continuing the campaign-architecture line of work. Written 2026-08-20 by
the remote session that shipped #912 and opened #913. Everything here is verifiable in the
repo; where this note and the repo disagree, the repo wins.

## 0. Read first, in this order

1. `docs/dev/design/414th-campaign-architecture-notes.md` — the direction: five pillars,
   four admission rules, rungs R0–R7. **No tombstone is lifted by it**; each rung lands on
   its own DM call.
2. `docs/dev/design/414th-substrate-inventory-notes.md` — R0, done. The verdict that
   reshaped R1: the core is already coherent; two private ledgers (§81/§63 magazines); five
   missing couplings.
3. `docs/dev/design/414th-falcon-bms-campaign-notes.md` — the BMS study. Candidates 1 and 2
   are the scoped versions of rungs R2 and R7.
4. `docs/dev/design/414th-region-priorities-notes.md` — §93, BUILT; the template for every
   command lever (weight, never fence).
5. `docs/dev/design/414th-sam-magazines-notes.md` — parked; becomes R3 *on the substrate*,
   not a third standalone channel.
6. CLAUDE.md as always — the standing rules apply unchanged (upstream PR freeze, naming
   conventions, doc-sync order, AGENTS.md mirror).

## 1. Where things stand (2026-08-20 evening UTC)

| Thing | State |
|---|---|
| `main` | `ee75401cf` — #913 merged 2026-08-20 (R0 inventory + the R1 reshape) on top of #912's §93 region priorities, study notes and architecture note. |
| PR **#913** | **Merged 2026-08-20.** The watch it carried is closed. Branch from `main`, never from `claude/substrate-r0-inventory`. |
| Branch `claude/grimes-dcs-repositories-pnf9ut` | Stale on the remote — holds only #912's already-merged history. Safe to delete on the DM's word; nothing references it. |
| §93 checklist row | **B89** ☐ UNTESTED — the app pass below. |
| §90 checklist rows | **B65–B68** ☐ UNTESTED — the fly pass that gates R2. |

## 2. What only the local machine can do (why this handoff exists)

Highest value first. Each is blocked remotely (needs DCS, the real app, or the local install).

1. **B65–B68 fly pass** (~1 evening; gates rung R2). Germany Red Tide is the natural
   campaign. Criteria per row in `docs/dev/414th-ingame-pass-checklist.md`: reinforcement
   follows supply lines (A), attacking costs more than defending (B), the line counts forces
   present (C), terrain slows the advance (D). Record pass/fail per row; R2 is buildable the
   day these pass.
2. **B89 app pass for §93** (~20 min). Enable `region_priorities` (Settings → Campaign
   doctrine), set an enemy CP EMPHASIZED and another IGNORED from the base dialog, pass the
   turn twice, and compare the ATO's target distribution against a NORMAL baseline. Fail
   signature: no visible shift, or a rescue/manual package suppressed (both would be bugs —
   the exemptions are tested but the app path is not).
3. ~~The detection-range check~~ **DONE 2026-08-20 — no defect found.** The two columns are not
   measured against the same target; `database ÷ runtime` is a flat 5^¼ across the table, the Buk
   SR is exact once normalised, and the DM's own export matches pydcs on all seven units. Three
   units still disagree and would need `getSensors()` run on this install to settle — that part
   *is* a DCS-box task if it is ever wanted. Written up in `414th-mist-author-repos-notes.md` §3.
4. **The standing fly cards** — `docs/dev/flycards/WATCH.md` (zero setup) and `LOCAL.md`
   (arranged on purpose) as always.

## 3. Code work available to any machine, in order

1. ~~Merge #913 first~~ **DONE** — merged 2026-08-20 as `ee75401cf`. Branch fresh from `main`;
   do not reuse the stale branch.
2. ~~R1 opening move — answer inventory open question 1~~ **DONE 2026-08-20**, written up in
   the inventory note §5.1. Verdict: transfers are already network-gated, but a factory on the
   destination control point commissions units at full rate with no supply read. That folds
   into gap 1 (income route-coupling), so **R1 carries no delivery-gating fix**.
3. **R1 proper on the DM's call** — one persistence home for magazine stocks: absorb
   `game/fourteenth/naval_magazines.py` (§81) and the §63 cruise state channel, shaped so
   the parked SAM magazines land in it as a third row, not a third mechanism. Inventory
   §5 question 3 (extend §81's shape vs a new owner) is the first design decision — put it
   to the DM with a recommendation before writing code.
4. **R2 after the B65–B68 pass** — supply scales combat effectiveness. Already scoped:
   BMS note candidate 1. The build is an `EFFECTIVENESS_MULTIPLIER` sibling beside
   `RECOVERY_MULTIPLIER` in `game/theater/supply.py`, applied where rung C counts forces
   (`game/theater/frontline.py:298–314`). Mind `supply.py`'s two docstring warnings.

## 4. Decisions reserved for the DM — do not bulldoze

- Which rung runs next, and every rung's go/no-go (architecture note §6 gates).
- Income route-coupling and its fractions (inventory §5 question 2).
- R2's factor values (0.5/0.7-style tuning is a flown call, not a coded one).
- Deleting the stale branch.
- Anything touching the upstream PR freeze — still IN FORCE; only the DM lifts it.

## 5. Traps specific to this line of work

- **The MIST author's name/handle appear nowhere in the repo, commits, or PR metadata**
  (2026-08-20 user call, paid-campaign treatment). His repos are read-only regardless:
  GPL-3/unlicensed vs our LGPL-3. Verify against, reimplement from the DCS API, never vendor.
- **The architecture note lifts no tombstones.** §53/§54/§55 stay removed; the note
  *subsumes* them as substrate reads, and only a landed rung changes anything. Do not
  restore a removed feature because the note discusses it.
- **Weight, never fence** — every player lever shapes the auto-planner only; §40 stays dead.
  Red never reads blue's levers; rescue tasking is never weighted (tested — keep it so).
- **Merged-PR branch restart**: a merged branch restarts from `main` under the same name and
  needs a force-push the permission layer may block — name the force-push to the DM or use a
  fresh branch (this session hit exactly that; #913's branch is the result).
- Local verification before any push, per `docs/dev/CLAUDE-ci.md`: Black check whole tree,
  mypy `game tests`, pytest incl. the three out-of-tree dirs. On Linux containers, mypy's 9
  `atmosxliveweather` `winreg` errors and ~15 font/GL test failures are baseline, not yours.
- Doc-sync order on any change (CLAUDE.md "Keeping docs in sync"), and `cp CLAUDE.md
  AGENTS.md` + retitle line 1 after any CLAUDE.md edit.
