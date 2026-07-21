# 414th — Campaign Phases: 6-campaign inference pilot

> **SUPERSEDED / REMOVED 2026-07-21** — the campaign-phases feature (§40) was removed from the fork (ROE mechanic drop). This pilot note is kept as a historical record.

**Status:** pilot complete (2026-07-01). Companion to
[`414th-campaign-phases-notes.md`](414th-campaign-phases-notes.md) (the spec). This validates
the Tier-0 classifier's §3.2 thresholds against real laydowns and drafts an inferred arc per
campaign. Two threshold refinements landed back into the spec as a result.

> **⚠️ Engine-re-run addendum (2026-07-01, same day, later).** The `--engine --all` re-run
> ([`414th-campaign-phases-all66-draft.md`](414th-campaign-phases-all66-draft.md)) surfaced a
> **third `--lite` blind spot** this pilot never saw: Retribution *generates* SAM sites into a
> campaign's air-defense TGO slots from the faction, and `--lite` only reads units authored in
> the `.miz`. That corrects this note's headline example: **Khe Sanh is NOT a 0-SAM theater in
> actual gameplay** — the generator fills 4 real SA-75/S-125 batteries for the NVA (Sukhumi /
> Senaki / Kobuleti), so it opens in **Rollback** under engine truth. The **absolute-SAM-floor
> gate itself survives** (refinement 1 stands): the genuine below-floor cases are Shattered
> Dagger, Battle for No Man's Land, Valley of Rotary, and Northern Guardian, and Velvet Thunder
> sits exactly at the floor (3 SA-2 sites) and keeps Rollback. The "same era, opposite arc"
> value proposition still holds — decided by laydown — just not on the Khe Sanh↔Velvet pair.

## Method

The real engine can't run in the CI sandbox (the pinned pydcs is dcs-retribution's fork, whose
GitHub source is egress-blocked here). So this pilot used the **`--lite`** path of
`tools/campaign_phase_laydown.py` — it parses each `.miz`'s `mission` + `warehouses` Lua tables
directly via `dcs.lua` (no fork units needed) and reads airfield ownership + an AD-tier count
off a hand-curated vanilla-DCS type table, plus the campaign YAML's `squadrons:` block for the
air order of battle. **Lower fidelity than the engine** (ownership == raw
DCS airfield coalition; no Retribution front model; SAM tiers approximate), but more than enough
to pressure-test the phase boundaries. Re-run with **`--engine`** on a real Retribution install
for the authoritative numbers (control-point ownership, `IadsRole`, front lines, squadron
inventory, threat-zone area).

Spread chosen for structural variety (per user: weight modern + Vietnam; drop WWII/Falklands/niche):
4 modern + 2 Vietnam, 4 theaters, 1968→2026, dense-IADS↔no-IADS, symmetric↔asymmetric.

## The laydowns

| Campaign | Era | Theater | Enemy L+M SAM (L/M) | SHORAD/AAA | EWR | Airfields B/R/N | Ground grps B/R |
|---|---|---|---:|---:|---:|:--|:--|
| Black Sea | 2004 | Caucasus | **13** (8/5) | 47 | 50 | 5/5/11 | 35/175 |
| Slava Ukraini | 2026 | Caucasus | 7 (5/2) | 13 | 0 | 2/3/16 | 19/36 |
| Anvil of War | 2007 | Kola | **21** (5/16) | 15 | 0 | 8/8/17 | 20/67 |
| Noisy Cricket | 2019 | Persian Gulf | **25** (4/21) | 10 | 0 | 2/6/21 | 13/54 |
| Khe Sanh (Niagara) | 1968 | Caucasus | **0** | 31 | 0 | 3/3/15 | 8/48 |
| Velvet Thunder | 1970 | Marianas | 12 (1/11) | 23 | 0 | 2/3/3 | 8/77 |

(Player is BLUE in all six; "enemy" = RED.)

### Air order of battle (from the YAML `squadrons:` block)

The `.miz` carries the ground/IADS picture, but the campaign **YAML** carries the air order of
battle — a `squadrons:` block keyed by control-point id (== the DCS airbase id for airfields),
which the extractor attributes to a side via `.miz` airport ownership. This is read directly
from plain-text YAML (no engine), and it supplies the **air-threat** signal that IADS counts
alone miss:

| Campaign | BLUE fig/SEAD/strike | RED fig/SEAD/strike | Note |
|---|:--|:--|---|
| Black Sea | 16/12/32 | 16/12/36 | symmetric air |
| Slava Ukraini | 24/24/24 | **24**/12/24 | **peer air** — empirically confirms the §3.2 peer-fight guard |
| Anvil of War | 40/52/36 | 40/36/44 | large symmetric air war |
| Noisy Cricket | 28/**72**/20 | **58**/28/20 | RED fighter-superior (58); blue's 72 SEAD vs the Iran belt |
| Khe Sanh | 0/0/0 | 0/0/0 | **no explicit block** → faction auto-assign (lite blind spot) |
| Velvet Thunder | 16/16/36 | 16/**0**/8 | RED **0 SEAD** = era-correct |

Takeaways: **enemy fighter count is a first-class phase driver** (Noisy Cricket's RED 58 makes
"win the air first" a real task even before IADS), and **symmetric fighter counts detect the
peer fight** (Slava 24-vs-24) that gates the Rollback→Interdiction transition on
`air_threat_absent AND iads_down`. **Caveat:** campaigns that omit the block and rely on
`DefaultSquadronAssigner` (Khe Sanh) read as 0/0/0 in `--lite` — the `--engine` mode, which sees
the assigned squadrons, closes this.

## Drafted arcs (what the Tier-0 classifier should infer)

- **Black Sea** — textbook. **Rollback** (dense S-300 belt, 13 L+M) → **Interdiction** (cut the
  175-group red ground mass) → **Offensive** (take the 11 neutral fields). Clean 3-phase; the
  baseline the thresholds were tuned around.
- **Slava Ukraini** — **Rollback** (short; 7 L+M) → **Interdiction** → **Offensive** over a huge
  16-field neutral pool ⇒ *long* campaign. **Peer fight** (Ukraine vs Russia): red air is a real
  threat, so "air won" should gate on *air-threat-absent AND IADS-down*, not IADS alone — else it
  advances too early.
- **Anvil of War** — heaviest IADS (**21** L+M, medium-heavy) on a 33-field map ⇒ **long,
  dominant Rollback**, then Interdiction → Offensive. Stresses "how long does Rollback hold" →
  pacing must scale with SAM density.
- **Noisy Cricket** — densest medium belt (**25** L+M, Iran) + blue outnumbered on fields (2 vs 6)
  ⇒ **long Rollback + early self-defense**, littoral (red ships ⇒ anti-ship live), then Interdiction
  → amphibious **Offensive** over 21 neutral fields.
- **Khe Sanh (Niagara)** — **the edge case, and it behaved exactly as the design predicted.**
  **Zero** long/medium SAM, 31 AAA groups. A ratio-only classifier would open in Rollback and
  spin on a SAM belt that doesn't exist. Correct behavior: **skip Rollback entirely**, open in
  **Interdiction** (Steel Tiger — cut the 48-group NVA siege force) with the AAA gauntlet (§33) as
  ambient threat, then **Offensive/relief**. Vietnam doctrine renames the labels.
- **Velvet Thunder** — the counter-proof. Also Vietnam-era, but a real **SA-2 belt** (12 L+M) ⇒
  the classifier **keeps Rollback** ("Wild Weasel / Iron Hand" vs SA-2) where Khe Sanh dropped it.
  **Same era, opposite arc — decided by laydown, not a hardcoded era assumption.** This is the
  whole value proposition of state-inference, demonstrated on two 1968–70 campaigns.

## Threshold refinements (folded into the spec §3.2)

1. **Absolute SAM-floor gate for Rollback (new, important).** Ratio alone can't fire correctly:
   at turn 0 every campaign's `iads_ratio == 1.0`, yet Khe Sanh (0 SAM) and Noisy Cricket (25 SAM)
   must not open in the same phase. Add: **if the turn-0 baseline of long+medium SAM launchers is
   below a floor (≈ 3), there is no meaningful Rollback phase — open in Interdiction.** Khe Sanh
   (0) skips; Velvet Thunder (12) keeps; all four modern keep. This is the single most valuable
   thing the pilot surfaced.
2. **De-weight EWR as an IADS-strength signal.** EWR counts are wildly author-dependent (Black Sea
   50, every other campaign 0 — most authors let SAM radars do EWR duty). Use **long+medium
   launcher count** as the primary IADS-strength metric; treat EWR as flavor only.
3. **Pace phases by SAM density + capturable pool.** Rollback min-dwell should scale with L+M SAM
   count (Anvil 21 / Noisy 25 ⇒ long Rollback; Slava 7 ⇒ short). Overall campaign length tracks the
   neutral-airfield pool (Slava 16 / Noisy 21 ⇒ long; Velvet 3 ⇒ short). Feeds the hysteresis /
   min-dwell defaults.
4. **Peer-fight "air won" transition.** When the sides are air-symmetric (Slava Ukraini), gate the
   Rollback→Interdiction transition on `air_threat_absent AND iads_down`, not IADS alone.

## Next steps

- Re-run `tools/campaign_phase_laydown.py --engine --all` on a real install for authoritative
  numbers, then extend the drafts across all 66 (pilot → fan-out, spec §7).
- The absolute-floor gate (refinement 1) is now a P1 requirement, not a nice-to-have.
