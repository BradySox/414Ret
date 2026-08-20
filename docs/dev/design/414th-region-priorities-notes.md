# Region priorities — scoping note

Status: **scoping only, nothing built.** Written 2026-08-20 on the DM's proposal: take
upstream [#686](https://github.com/dcs-retribution/dcs-retribution/pull/686)'s idea and
rework it with the BMS study note in mind — the weight, not the fence.
Origin: BMS-note candidate 4 (`414th-falcon-bms-campaign-notes.md` §4) × red-one1's #686.

## 1. The synthesis

Three inputs, one feature:

- **BMS's PAK system** proves the semantics: a per-region priority the player sets, entering
  target selection as a *weight*. Emphasis, not a fence — 0 approximates a fence, everything
  between exists. (BMS wiki / study note §2.2.)
- **Upstream #686** (red-one1, WIP draft, v1.6 milestone, no reviews) proves the appetite and
  the surface: click regions on the map, the planner respects them. Its mechanism is a hard
  filter — A2G missions *only* inside selected navmesh polygons. LGPL-3 like everything
  upstream, so unlike the session's other externals this one is **licence-clean to adopt**,
  with attribution per fork custom (#859/#928/#929 precedent).
- **§40's tombstone** rules the fence out fork-side: the removed ROE-zones layer was the
  constraint version of this idea, dropped 2026-07-21. The rework is the weighting version
  or nothing.

## 2. Why #686 cannot be taken as-is

Verified against the tree, not just read from the PR:

1. **The selection anchor is unstable.** #686 stores selected **navmesh polygon IDs**
   (`blueSelection: number[]`). But the navmesh is rebuilt from threat zones every turn
   (`Game.initialize_turn` → `Coalition.compute_nav_meshes` →
   `NavMesh.from_threat_zones`, `game/game.py:857`, `game/coalition.py:201`), and poly
   `ident`s are assigned at triangulation. Kill one SAM and the mesh re-triangulates — the
   stored IDs silently bind to different terrain. A selection that dissolves or teleports
   every turn is not a foundation.
2. **It carries a red-side selection.** `redSelection` steers the *enemy's* planner — fork-side
   that is the player puppeting red (seam 7 territory, and cheat-adjacent under the fog
   rules). Dropped.
3. **It is a fence** — §1's third input. The per-mission-type "AOO Selected Tasks" checkbox
   panel gates which task types the fence applies to; the weight model replaces both.
4. WIP quality: the branch includes the author's agent-workflow files (`AGENT_MEMORY.md`)
   that could never merge. Take the shape, not the diff.

**What does survive from #686:** the interaction pattern (a clickable map surface driving a
`PUT` selection endpoint, mirrored into planner state) — the same shape as the fork's own §18
fog toggle (`PUT /fog-of-war/reveal` → re-pull `/game`) — and the validation that players
want this control at the map, not in a settings dialog.

## 3. The fork-shaped anchor: control points

Retribution's theater is a CP graph, and **every plannable target already hangs off a control
point** (`cp.connected_objectives`; `objectivefinder`'s iterators walk CPs). So the stable
region is not a polygon at all — **it is the CP.** A per-CP priority covers every TGO, front
and airfield attached to it, survives every save and every navmesh rebuild, and needs zero
new geometry, serialization or hit-testing.

- **Levels, not a slider:** `EMPHASIZED` / `NORMAL` / `DEPRIORITIZED` / `IGNORED`.
  Factor into the target sort key (see §4): ~0.5 / 1.0 / 2.0 / excluded.
- **`IGNORED` is auto-planner-only.** Manual packages against that CP work exactly as today —
  which is what keeps it clear of §40's corpse: §40 constrained *missions and ROE in the
  mission*; this only shapes what the auto-planner proposes. The player's own hand is never
  fenced.
- **Blue-only.** Red's planner untouched. Fog-safe by construction — a planning prior on
  your own side reveals nothing and reads identically for host and client.

## 4. Mechanism — one multiplication site

`objectivefinder._targets_by_range` is the single sort every offensive iterator routes
through (strike, ships, OCA, the capturable/isolated CP orderings — verified callers at
lines 80–432). The whole planner-side change is its sort key:

```
sort_key = min_range_to_friendly_cp * level_factor(owning_cp)
```

with `IGNORED` targets dropped from the iterator (auto-planning only). One site, every
offensive task, no per-task plumbing — the same one-question-one-place property §3's
`visibility_for` set as fork style. BMS-note candidate 3 (front-distance term) lands in this
same key later; compose, don't co-build.

## 5. v1 scope

1. `ControlPoint.blue_priority` (enum, default `NORMAL`), persisted; getattr-guarded for old
   saves — no migration.
2. The sort-key factor + `IGNORED` drop in `_targets_by_range` / its iterators, gated on a
   default-OFF setting (`region_priorities`) — a new row in the autoplanner divergence
   audit's gate/default table, riding the planner-suite discipline (B54).
3. UI: the CP dialog (web) gains the four-way priority control; the map badges non-NORMAL
   CPs. Qt parity can trail (§18 precedent: the map interaction layer is web-first).
   No navmesh click-selection in v1 — the anchor argument above.
4. Registry entry (`game/fourteenth/features.py`), docs faces, in-game-pass row
   (headless-checkable: generate a turn with an EMPHASIZED axis, compare the ATO's target
   distribution against a NORMAL baseline; plus one UI pass).
5. Attribution: this note + the landing commit credit #686 as the surface's origin.

Deferred: drawn/geometry zones (only if per-CP granularity ever proves too coarse), any red
control (never, absent a seam-7 reopening), weighting defensive tasks (BARCAP placement is
geometry-driven and upstream's — do not touch), candidate 3's front-distance term (same key,
own decision).

## 6. Upstream posture

The freeze bars a new upstream PR, and #686 is another author's open WIP in exactly this
territory (now on the crowded-zones list). So: fork feature first, flown and settled. When
the freeze lifts and #686 moves, the fork's experience is review input on red-one1's PR —
"the weight shape survived play, the ID anchor didn't" — or a coordinated follow-up, not a
competing carve.

## 7. Open questions

| # | Question | Leaning |
|---|---|---|
| 1 | Factors for EMPHASIZED/DEPRIORITIZED | 0.5 / 2.0 — distance-equivalent halving/doubling; tune from the first campaign |
| 2 | Does `IGNORED` also skip §63 auto raids / §44 carrier strikes? | Yes — they are auto-planning; the §3 auto-target rule already makes them fog-gated, this adds the same courtesy |
| 3 | Per-side or per-player in MP? | Per-coalition (blue), host-set — same as every other campaign-level control |
