# 414th PR #823 Frontline Merge Notes

How to adopt upstream **PR #823 — "Enhanced Front Line Stances + Movement"**
(`dcs-retribution/dcs-retribution#823`, branch `feat/dr-byba-frontline-movement`) onto a
fork build where **TIC is the default frontline driver**. Read this before merging #823 or
touching `game/missiongenerator/flotgenerator.py` / `game/ground_forces/ai_ground_planner.py`.
Pairs with `414th-tic-dynamic-fronts-notes.md` (the TIC movement design) and CLAUDE.md §9
(the TIC integration contract).

## TL;DR

PR #823 is two stacked features:

1. **Composition & spread** — proportional mixed armor *clusters* (largest-remainder
   allocation, `anchor`-linked members, even-slot placement) replacing single-type random
   groups.
2. **Cohesive maneuver** — clusters move as a unit via DCS AI tasks + pydcs formations
   (Vee/Line), with per-stance advance distances and an APC-into-wedge fix.

Against TIC these land very differently:

- **Composition + stance-default + spawn placement** are **orthogonal/upstream of TIC** and
  improve TIC's starting laydown → **adopt**.
- **Cohesive maneuver** is **overridden by TIC** for the armor/ATGM roles TIC owns
  (`plan_action_for_groups` short-circuits TANK/IFV/APC/ATGM into `_plan_tic_action` and
  `continue`s, and TIC drives movement by waypoint *name*, not DCS tasks). So #823's maneuver
  is **inert on a TIC build** → **guard behind `not self.tic_enabled`** so it only drives the
  TIC-off path.

No hard incompatibility (TIC intercepts first; nothing fights at runtime), but real merge
conflicts in `flotgenerator.py`, partly because **our fork already rewrote the same placement
functions** (the perpendicular-step anti-stacking logic).

## Why the maneuver half is redundant under TIC

`plan_action_for_groups` runs the TIC short-circuit first:

```python
if self.tic_enabled and self._tic_managed_role(group.role):   # TANK, IFV, APC, ATGM
    self._plan_tic_action(...)
    continue
```

TIC default is ON (`tic_enabled = bool(plugins.get("tic"))`, CLAUDE.md §9). So #823's
`_plan_follower_action`, APC-into-wedge, per-stance follower advance, and `move_formation`
Vee/Line formations — all of which live in the `elif` chain below that `continue` — never run
for the units TIC manages. They would only reach SHORAD/RECON (not TIC-managed). Additionally,
TIC groups are cloaked from DCS AI sensors by StormTrooper and move by waypoint name, so DCS
AI-task formations are doubly moot on them. The composition + spawn-placement halves, by
contrast, run *before* TIC tasking and feed it a better laydown.

## Bucket A — Adopt wholesale (orthogonal to TIC, no TIC code touched)

Cherry-pick as-is:

- `game/ground_forces/frontline_clustering.py` — **new file**: `allocate_largest_remainder`,
  `even_slot_centers`. Pure, no `game.*` imports.
- `game/ground_forces/ai_ground_planner.py` — full rewrite: proportional allocation,
  `Cluster` / `assemble_clusters`, the `anchor` field + `__setstate__` backfill, role tables.
  No TIC code here; TIC just consumes the resulting `CombatGroup` list. The removed
  `GROUP_SIZES_BY_COMBAT_STANCE` is **not** read anywhere in the fork's TIC path — safe.
- `game/settings/settings.py` — `default_front_line_stance` choices-option.
- `game/theater/controlpoint.py` — `seed_front_line_stances`,
  `apply_default_stance_on_capture` + the `capture()` call.
- `game/theater/start_generator.py` — `apply_default_player_stances` + the `generate()` call.
- Tests: `tests/ground_forces/*`, `tests/theater/test_default_front_line_stance*`,
  `tests/test_default_front_line_stance_settings.py` — bring over verbatim.

**Save migration:** `CombatGroup.__setstate__` backfills `anchor = None` for old pickles —
already in the PR; satisfies the save-migration rule.

## Bucket B — Reconcile against the fork's existing placement rewrite

This is the only tricky merge. The fork **already rewrote** `get_valid_position_for_group`
(perpendicular-step anti-stacking) and `_generate_groups`, so it's a 3-way: upstream baseline
→ fork rewrite → #823 rewrite. Keep **both** wins: #823's even-spread *along* the front +
the fork's anti-stacking *off* the front.

**`get_valid_position_for_group`** — add #823's `along_offset` param; keep the fork body.
Change the signature to `(self, distance_from_frontline, spawn_heading, along_offset)` and
replace only the lateral pick:

```python
# was: random.randint(0, self.conflict.size)
clamped = max(0, min(int(along_offset), self.conflict.size))
shifted = self.conflict.position.point_from_heading(
    self.conflict.heading.degrees, clamped
)
```

Everything from the `is_on_land(shifted)` degenerate-front guard down through the
perpendicular-step loop (the fork's rewrite) **stays**. Net: even-slot lateral position from
#823, anti-stacking depth search from the fork.

**`_generate_groups`** — adopt #823's two-pass body: `frontline_offsets(groups, size)`, the
wedge depth/jitter pre-pass, `CLUSTER_DEPTH_OFFSET` / `CLUSTER_LATERAL_JITTER`, and the
`along_offset=along[id(group)] + jitter` call. Keep the fork's APC/IFV → `tic_formation`
infantry block (the `TIC:`-prefix detection) — #823 dropped that arg because upstream has no
TIC; re-add it.

**New constants/imports for `flotgenerator.py`:** `frontline_offsets`,
`move_formation_for_role`, `_MOVE_FORMATION_BY_ROLE`, `INFANTRY_FORWARD_OFFSET`,
`INFANTRY_SCATTER_RADIUS`, `CLUSTER_LATERAL_JITTER`; import `CLUSTER_DEPTH_OFFSET`,
`WEDGE_ROLES`, `even_slot_centers`. Delete the now-dead `SPREAD_DISTANCE_FACTOR` /
`SPREAD_DISTANCE_SIZE_FACTOR` (already unused in the fork — #823 removing them is correct).

**`gen_infantry_group_for_group`** — merge, don't pick a side: keep the fork's `tic_formation`
param + `TIC:` naming **and** apply #823's forward-lead + scatter positioning
(`INFANTRY_FORWARD_OFFSET` / `INFANTRY_SCATTER_RADIUS`). Position-vs-naming; no semantic
conflict. Forward-lead infantry is fine under TIC.

**`_generate_group`** — adopt #823's `move_formation` param and pass it to
`self.mission.vehicle_group(...)`; keep the fork's TIC naming / `late_activation` /
`tic_groups` block intact. `move_formation` is harmless on TIC groups (TIC respawns
single-unit copies and drives them by waypoint name).

## Bucket C — Guard behind `not self.tic_enabled` (the DCS-task maneuver)

Bring in `follower_advance_distance`, `_plan_follower_action`, and the APC-into-wedge
regrouping — but gate the new maneuver so it only runs when TIC is off. Restructured
`plan_action_for_groups`:

```python
for dcs_group, group in ally_groups:
    if self.tic_enabled and self._tic_managed_role(group.role):
        self._plan_tic_action(stance, dcs_group, forward_heading, from_cp, to_cp)
        continue

    if group.role == CombatGroupRole.ARTILLERY:
        # unchanged — applies on both TIC and non-TIC builds
        if self.game.settings.perf_artillery:
            target = self.get_artillery_target_in_range(dcs_group, group, enemy_groups)
            if target is not None:
                self._plan_artillery_action(
                    stance, group, dcs_group, forward_heading, target
                )

    elif not self.tic_enabled:
        # ===== #823 cohesive maneuver — TIC-OFF path only =====
        if group.role in (
            CombatGroupRole.TANK,
            CombatGroupRole.IFV,
            CombatGroupRole.APC,
        ):
            self._plan_tank_ifv_action(
                stance, enemy_groups, dcs_group, forward_heading, to_cp
            )
        elif group.role in (
            CombatGroupRole.ATGM,
            CombatGroupRole.SHORAD,
            CombatGroupRole.RECON,
        ):
            if group.anchor is not None:
                self._plan_follower_action(stance, dcs_group, forward_heading, to_cp)
            else:
                self._plan_apc_atgm_action(stance, dcs_group, forward_heading, to_cp)
    # else: TIC build → SHORAD/RECON stay static (matches current fork behavior)

    if stance == CombatStance.RETREAT:
        ...  # shared fallback, unchanged
```

Why this shape:

- **TIC build (the 414th default):** TANK/IFV/APC/ATGM hit the short-circuit (unchanged).
  SHORAD/RECON fall through to nothing-but-RETREAT — **byte-for-byte today's behavior**. Only
  the *laydown* (Buckets A+B) changes; movement is untouched.
- **TIC-off build:** full #823 maneuver runs (cohesive clusters, APC-into-wedge fix,
  formations).
- `_plan_follower_action`'s contract (return `False` on RETREAT so the shared block adds the
  retreat waypoints, no double-add) is preserved by keeping the shared RETREAT block after the
  branch.

## Validation & risks

- **Lua:** none touched — no `lua-lint` exposure.
- **Run before pushing** (`docs/dev/CLAUDE-ci.md`): `black --check .`, `mypy game tests`,
  `pytest tests -q`.
- **Tests to add on top of #823's suite:** (1) with `tic_enabled=True`, a TANK group routes
  through `_plan_tic_action`, not `_plan_tank_ifv_action`; (2) SHORAD gets no maneuver waypoint
  on a TIC build. These lock the guard so a future refactor can't silently let #823's maneuver
  leak onto TIC groups.
- **Docs to sync (doc-hygiene order):** `414th-tic-dynamic-fronts-notes.md` (clustered laydown
  now feeds TIC), `docs/dev/414th-features.md` §9 + §6, `README.md` (player-visible:
  default-stance setting + mixed clusters), `docs/dev/414th-upstreaming-inventory.md` (record
  that we took #823's composition/stance but diverge on the maneuver guard).
- **Residual risk — in-game pass:** the merged laydown changes how front units spawn — a new
  variant of an existing UNTESTED-class behavior. Add a row to
  `docs/dev/414th-ingame-pass-checklist.md`, or fold it into the TIC in-game pass.

## Status

- **Bucket A — DONE (2026-06-26), uncommitted on `claude/peaceful-dhawan-52ad6b`.** Ported
  `frontline_clustering.py` (new), the `ai_ground_planner.py` rewrite (with the fork's
  `total_frontline_units` denominator preserved in place of #823's `total_armor`), the
  `default_front_line_stance` setting (+ `CombatStance` registered in
  `SERIALIZABLE_ENUM_TYPES` — the fork's safe-registry enum migration, which #823's
  eval-based upstream did not need), the `controlpoint.py` seed/capture methods + call, the
  `start_generator.py` new-game seeding, and 5 test files (the `ai_ground_planner` fakes
  adapted to set `total_frontline_units`). The two `tests/missiongenerator/test_flotgenerator_*`
  files were **held** for Bucket B/C (they import not-yet-ported flotgenerator helpers). CI
  gates green: black (whole tree), mypy (`game tests`), pytest (919 passed / 2 skipped, incl.
  35 new).
- **Buckets B + C — DONE (2026-06-26).** All in `game/missiongenerator/flotgenerator.py`:
  - **B (placement):** imported `CLUSTER_DEPTH_OFFSET`/`WEDGE_ROLES`/`even_slot_centers`;
    dropped the dead `SPREAD_DISTANCE_*` constants; added `frontline_offsets`, the
    `INFANTRY_FORWARD_OFFSET`/`SCATTER_RADIUS` wedge-lead infantry, `CLUSTER_LATERAL_JITTER`;
    rewrote `_generate_groups` to the two-pass even-spread + wedge depth/jitter; added the
    `along_offset` param to `get_valid_position_for_group` **on top of** the fork's existing
    perpendicular-step anti-stacking body (3-way reconciliation, both wins kept); threaded
    `move_formation` through `_generate_group` while keeping the fork's TIC naming /
    `late_activation` / `tic_groups` block and the APC/IFV → `tic_formation` infantry path.
  - **C (maneuver, TIC-guarded):** added `follower_advance_distance`,
    `move_formation_for_role`, and `_plan_follower_action`; restructured
    `plan_action_for_groups` so the TIC short-circuit stays first, artillery runs on both
    builds, and the #823 cohesive maneuver (APC-into-wedge + anchored-follower routing) runs
    **only when `not self.tic_enabled`**. On a TIC build SHORAD/RECON stay static (pre-#823
    behaviour) and TIC keeps sole ownership of armor/ATGM movement.
  - **Tests:** the two held `tests/missiongenerator/test_flotgenerator_{movement,placement}.py`
    (#823, verbatim) + a new `test_flotgenerator_tic_guard.py` (414th) that locks the guard:
    TANK/ATGM route to `_plan_tic_action` on a TIC build, SHORAD gets no maneuver, and the
    TIC-off path uses follower/apc-atgm/wedge correctly.
  - CI gates green: black (whole tree), mypy (`game tests`, 649 files), pytest (934 passed /
    2 skipped, incl. 21 new flotgenerator tests).

Drafted 2026-06-26 from analysis of PR #823 @ open against `dev`; Buckets A–C landed
2026-06-26.
