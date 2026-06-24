# Decision: `dismounts` — the MIST-drop Blocker (consolidation phase 5)

**Status:** ✅ RESOLVED — **Option B (retire)** chosen and executed 2026-06-24 (squadron confirmed
unused). `resources/plugins/dismounts/` removed; settings drop orphaned `dismounts` keys on load;
changelog updated.
**Date:** 2026-06-24
**Parent:** [`414th-framework-consolidation-notes.md`](414th-framework-consolidation-notes.md) phase 5.

> **Note discovered during execution:** `dismounts` was **not listed in
> `resources/plugins/plugins.json`** (the authoritative load list in `game/plugins/manager.py`), so it
> was already **dormant/unloaded** — not actually enable-able in current builds. Retirement was
> therefore pure dead-code removal with zero runtime impact, which made Option B the obvious call.

## The question

Is `dismounts` superseded or needed, and what do we do with it given we want to drop MIST?

## Findings

**Not superseded.** Unlike `ewrs` (replaced by the MOOSE `bigeye`), **nothing in the fork
replicates dismounts** — there is no MOOSE-based equivalent feature. Retiring MIST does not
"free" this one; it has no successor waiting.

**What it does.** `resources/plugins/dismounts/dcs_dismounts.lua` (~2,256 lines) spawns infantry
squads (8–21 soldiers) that auto-deploy from transport vehicles (APC/IFV/truck) when the vehicle
stops, and re-mount when it moves off; squad composition varies by vehicle/country; players can
direct squads via F10 markers. It's an **immersion/density** feature.

**Niche, not load-bearing.**
- `plugin.json`: `defaultValue: false` — **default OFF**, UI label literally **"DCS Dismounts
  (FPS-killer)"**.
- No `game/` Python or core dependency (one incidental regex in `unitmap.py` for TIC group-name
  parsing — not a hard dependency). Cleanly removable.

**Why it's the MIST-drop blocker.** Spawning itself uses native `coalition.addGroup` (not MIST,
not MOOSE `SPAWN`). MIST is used for ~58 occurrences across ~12 function families, but only a few
are hard:

| MIST function | Role | Port difficulty |
|---|---|---|
| `mist.ground.buildWP` + `mist.goRoute` | dismounted-squad **routing/waypoints** | **Hard** — no single MOOSE equivalent; build DCS route tables + `Controller:setTask`, or `GROUP:Route()` |
| `mist.makeUnitTable('[all][vehicle]')` | find candidate vehicles | Medium — custom iteration |
| `mist.getLeadPos` / `getGroupPoints` | positions/waypoints | Easy–Medium — `GROUP:GetLeadUnit():GetPosition()` etc. |
| `mist.random`, `mist.utils.deepCopy`, `mist.vec.mag`, `makeVec2`, `get2DDist` | RNG / utils / vector math | Easy — `math.random`, `UTILS.DeepCopy`/`UTILS.VecDist*` (already in `Moose.lua`) |
| `mist.utils.tableShow`, `mist.marker.*` | debug / marker cleanup | Trivial / mostly disabled |

A full MOOSE rewrite is estimated **~15–20 h dev + test**.

## The three honest options

| Option | Effort | Enables full MIST drop? | Trade-off |
|---|---:|---|---|
| **A. Rewrite on MOOSE** | ~15–20 h | ✅ yes | Keeps the feature *and* lets MIST leave the build. The "have your cake" option, if the feature is worth 2–3 weeks. |
| **B. Retire the feature** | ~2–4 h | ✅ yes | Lowest-cost path to a MIST-free build. Loses a niche, default-off immersion feature. Missions that enabled it silently skip (safe). |
| **C. Keep MIST just for dismounts** | 0 h | ❌ **no** | MIST stays vendored forever for one default-off plugin — **defeats the consolidation goal.** |

## Recommendation

**Decide by squadron usage, and avoid option C.** Option C keeps an entire framework alive for one
opt-in FPS-killer — the worst outcome for the "single framework" goal. So:

- **If the squadron actually flies with dismounts on** → **Option A** (MOOSE rewrite). It's the only
  way to keep the feature *and* finish the MIST drop. Sequence it last in the consolidation (after
  EWRS, SCAR/intercept glue, CTLD), since it's the hardest port and the feature is niche.
- **If it's effectively unused** (likely, given default-off + FPS warning) → **Option B** (retire).
  Cheapest route to a MIST-free runtime; the code investment is small relative to the maintenance
  win.

Either A or B unblocks dropping `mist_4_5_126.lua` from `base/plugin.json`. **Option C should be a
deliberate, temporary fallback only** — e.g. "ship the MIST drop for everything else, leave dismounts
on a still-loaded MIST for one release" — never the permanent answer.

> ❓ **The one input needed from the squadron:** does anyone actually run dismounts? That single
> answer picks A vs B. If nobody uses it, retire it and the MIST drop gets materially easier.

## Evidence

- `resources/plugins/dismounts/dcs_dismounts.lua` (~2,256 lines), `dismounts-config.lua` (29-line
  passthrough), `plugin.json` (`defaultValue: false`, "FPS-killer" label).
- Spawn path: native `coalition.addGroup(...)` (lines ~1831, ~2014) — not MIST/MOOSE.
- Hard MIST deps: `mist.ground.buildWP` (L1031/1033/1041/1043), `mist.goRoute` (L1036/1046),
  `mist.makeUnitTable` (L1670/1717).
- MOOSE replacements present in `Moose.lua`: `UTILS.DeepCopy`, `UTILS.VecDist2D/3D`, `SPAWN`,
  `GROUP`/`UNIT` accessors.
- No force-enable in `game/`; only an incidental name-parse regex in `unitmap.py`.
