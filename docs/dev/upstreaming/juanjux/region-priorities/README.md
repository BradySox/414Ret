# Region priorities (core)

414Ret §93, landed 2026-08-20 — two days after his review window closed, so it is not in
any of his ledgers.

## What it is

Per-control-point planning emphasis for the **blue** auto-planner. Emphasized regions'
targets rank as if at half their distance, deprioritized as if at double, ignored are
left to manual packages.

It is the *weighting* answer to the territory red-one1's upstream
[#686](https://github.com/dcs-retribution/dcs-retribution/pull/686) hard-limits with
navmesh polygons — and to the PAK-weight idea from BMS.

**A weight, never a fence.** IGNORED mutes the auto-planner only; a manual package is
never blocked, and ROE and rescue tasking are untouched. We built the fence version once
(ROE zones) and removed it; this is deliberately not that.

Two axes multiply:

- **Place** — per control point, with a per-target override that beats it in *both*
  directions, so one target inside an ignored base can still be marked normal and
  planned.
- **Kind** — seven target families (air defense, C2, infrastructure, logistics, armor,
  naval, missile sites). An IGNORED family is absolute: no target of that kind anywhere,
  and no per-target override reopens it.

Blue only, by design — the enemy planner never reads it. Anchored on control points
because navmesh polygon ids are rebuilt from threat zones every turn.

Off by default (`region_priorities`, Campaign Doctrine → General).

## What is in this patch, and what is not

**In — the engine.** It works with no UI at all; the fields are ordinary attributes.

- `game/regionpriorities.py` (new, 176 lines) — renamed off our `game/fourteenth/`
  package. Self-contained: duck-typed `getattr` access throughout, `ControlPoint`
  imported only inside functions, so there is no import cycle.
- `objectivefinder.py` — the weighting, at both sort sites (`_targets_by_range` gains a
  `weighted` kwarg; `strike_targets` carries its own sort for the multi-TGO dedup).
- `controlpoint.py` — the `blue_region_priority` property, getattr-guarded so old saves
  read NORMAL.
- `theatergroundobject.py` — the per-target override.
- `settings.py` — the toggle and the family dict.

**Not in:**

- **The tasking gate.** `auto_planning_skips` exists in the new module but nothing calls
  it here. In our tree it gates `AttackShips`, `DegradeIads` and
  `AttackBattlePositions` — needed because `enemy_ships` is *threat data as well as* a
  target list, so filtering the list itself would route blue over a carrier it had been
  told to ignore. **Gate the tasking, never the threat picture.** Without those three
  call sites an IGNORED region's ships and SAMs still get tasked at those tiers.
- **The Qt surfaces** — the CP dialog control, the per-target combo, the target-families
  window.
- **The React tooltip.**

## Applying

```
git apply region-priorities-core.patch
cp test_region_priorities.py tests/
```

Verified to apply at `ca780fd2`. Six files, one new.

18 tests ship here and cover the factor gates, both axes, the override in both
directions, the ordering effect and the drops. **Five more exist in our copy** and are
omitted because they exercise the tasking-gate consumers above.

## Verification status here

**☑ VERIFIED** (our row B89) — the CP-dialog control shifts the ATO. Note that row was
verified through the Qt surface, which is not in this patch; the engine underneath it is
what ships here.
