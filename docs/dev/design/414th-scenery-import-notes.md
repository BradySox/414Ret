# 414th — Scenery Strike-Target Import (Phase 1) — design notes

**Status:** design only, no code yet. Scoped 2026-06-23.
**Goal:** turn the build-time **CWG scenery scanner** dump into planner-taskable
`BuildingGroundObject` strike targets, replacing the manual Mission-Editor
trigger-zone authoring step. This is Phase 1 of the longer-horizon "campaign
builder" idea — it stands on its own (any campaign gets richer, *real* strike
targets) and is the piece the scanner breakthrough directly unblocks.

Related: [`cwg-scenery-scanner` memory], `Saved Games\DCS\Scripts\cwg_scenery_scanner.lua`,
the campaign-builder feasibility discussion (drop-spawn §20 is the sibling
runtime placement primitive).

---

## Current state / prior art (READ FIRST — don't re-invent)

This is **not** a greenfield design. As of 2026-06-23 there is already a working
build-time tool: `_scenerytools/cwg_scenery_emitter.py` (gitignored dir, pure
stdlib). It already does, and is the source of truth for:

- **Categorization** — `categorize()` + `CATEGORY_PATTERNS`
  (INDUSTRIAL→factory, TRANSFORMER→power, WAREHOUSE/SILO→ware,
  ANTENNA/RW_TOWER/WEATHER→comms).
- **Clustering** — `cluster()`: grid union-find, `CLUSTER_CELL=150m`,
  `BUILD_CAP=20` members/objective, blue-circle radius from member spread.
- **Laydown selection** — `select()`: greedy-by-size with `MIN_SEP=4km`,
  `REGION_CAP=2`/category, front-region guarantee. Target
  factory8/power6/ware8/comms4.
- **Report mode** works today; **`--inject` is the only unbuilt piece.**

The emitter's chosen integration is **Strategy A** below (write trigger zones into
a `red_tide.miz` copy → flows through the *existing* `from_trigger_zones` path,
zero Python-runtime change). It is Red-Tide-specific.

**The design question this note actually answers** is not "how do we cluster
scenery" (done) but **"which integration strategy carries us from a Red-Tide hack
to the all-maps campaign-builder data layer"** — and how to avoid building the
clustering twice.

---

## The load-bearing finding

The existing scenery pipeline is **position-keyed, never ID-keyed**:

1. Campaign designer draws ME trigger zones (a blue *definition* zone + white
   *target* zones inside it) with a category property.
2. `SceneryGroup.from_trigger_zones()` (`game/scenery_group.py`) aggregates them.
3. `StartGenerator.generate_tgo_for_scenery()` (`game/theater/start_generator.py:555`)
   builds one `BuildingGroundObject` (or `IadsBuildingGroundObject`) per group,
   with a `TheaterGroup` holding one `SceneryUnit` per white zone. Each
   `SceneryUnit` carries its `TriggerZone` in `.zone`.
4. At mission-gen, `TgoGenerator.add_trigger_zone_for_scenery()`
   (`game/missiongenerator/tgogenerator.py:467`) lays a **tiny 16-ft trigger zone
   over the object's position**; DCS resolves destruction via `MapObjectIsDead` /
   `SceneryDestructionZone` **by proximity**. *(The comment there: "As long as the
   triggerzone is over the scenery object, we're ok.")*

> **Consequence:** the DCS map-object ID is irrelevant to kill detection. The
> scanner dump's `x, z` world coordinates are everything the chain needs. We can
> synthesize `SceneryGroup` objects entirely from the dump and inject them at the
> same point ME-authored scenery enters the model — no ME authoring, no new
> runtime mechanism.

Attachment point: `MizCampaignLoader` (`game/campaignloader/mizcampaignloader.py:716`)
attaches each `SceneryGroup` to the nearest CP:
`closest.preset_locations.scenery.append(scenery_group)`
(`preset_locations.scenery: List[SceneryGroup]`, `controlpoint.py:156`). Imported
groups join that same list and inherit nearest-CP ownership for free.

---

## Coordinate convention (confirmed)

Scanner dump fields `x, z` are DCS world coords (`obj:getPoint()`, x=N/S, z=E/W).
pydcs `Point` is `(x, y)` over a terrain where **pydcs `y` == DCS `z`**. The
scanner header already states "dump-x == yaml-x, dump-z == yaml-y", matching how
`red_tide.yaml` CP coords were derived. So:

```
Point(record.x, record.z, theater.terrain)   # pydcs (x=north, y=east)
```

MGRS / lat / lon in the dump are not needed by the importer (eyeball-only).

---

## Two integration strategies (the actual decision)

Both consume the **same** clustered/categorized objectives the emitter already
produces. They differ only in *where the scenery enters the engine*:

| | **A — `.miz` injection (emitter `--inject`)** | **B — runtime importer (this note)** |
|---|---|---|
| Mechanism | Write blue/white trigger zones into a campaign `.miz` copy; existing `from_trigger_zones` ingests them | Read a curated per-map catalog at campaign-gen; synthesize `SceneryGroup`s in Python; append to `MizCampaignLoader.scenery` |
| Python change | None | New `sceneryimport` module + a settings flag + one `MizCampaignLoader` hook |
| Scope | One campaign at a time (must re-inject each `.miz`) | Any campaign on a scanned map, automatically |
| Ships | **Now** — only `--inject` left | After the importer is written + playtested |
| Per-map cost | Re-run emitter against each campaign `.miz` | One curated `resources/scenery/<terrain>.json` per map; campaigns get it free |
| Fits "campaign builder" | No — `.miz` surgery doesn't scale to a blank-theater editor | **Yes** — data-driven, map-agnostic, the layer Phase 3 consumes |

**Recommendation:**

- **Keep Strategy A as the Red Tide deliverable** — finish `--inject`, ship real
  strike targets into Red Tide now. It's nearly done and is the fastest path to a
  playable win. Tracked in [`cwg-scenery-scanner` memory].
- **Build Strategy B as the generalization** (this note's Phase 1) — but **do not
  re-implement clustering/categorization/selection**. Lift the emitter's
  `categorize` / `cluster` / `select` into a shared, importable module
  (e.g. `game/campaignloader/scenerycatalog.py`) that *both* the emitter and the
  runtime importer call. The emitter becomes a thin CLI over the shared core; the
  importer becomes a thin campaign-load adapter over the same core. One clustering
  implementation, two front-ends.

The rest of this note specs Strategy B.

## Pipeline (Strategy B)

```
 BUILD TIME (per map, once)            CURATION (commit)              RUNTIME (campaign gen)
 ─────────────────────────            ─────────────────              ──────────────────────
 cwg_scenery_scanner.lua      →       resources/scenery/      →      sceneryimport.load_catalog(terrain)
 (fly grid, dump Logs/*.csv)          <TerrainName>.json              → cluster into objectives
                                      (curated, deduped)              → map type → category
                                                                      → synthesize SceneryGroups
                                                                      → MizCampaignLoader attaches
                                                                        to nearest CP (existing loop)
```

### 1. Curated data file — `resources/scenery/<TerrainName>.json`

The raw `cwg_scenery_dump.csv` is ~1 MB / thousands of rows and noisy. Commit a
**curated, terrain-keyed** file instead of the raw dump. Minimum per record:
`type`, `x`, `z`, `life0`. Keyed by the pydcs terrain name (`theater.terrain.name`
— confirm exact id for Germany Cold War; the dump we have is that map's
Berlin/Brandenburg + Fulda regions).

Open question — format: a hand-curatable JSON/YAML vs. shipping the scanner's
returnable `.lua` table directly. Recommend **JSON** (CI-diffable, no Lua loader
in Python, lets us prune/annotate). A tiny converter (`_scenerytools/`, gitignored,
like `_wpntools/`) turns a raw dump → curated JSON.

### 2. Clustering + 3. Category mapping — REUSE the emitter core

These already exist in `_scenerytools/cwg_scenery_emitter.py` (`cluster()`,
`categorize()`, `select()`, `Cluster.finalize()`). The work here is **extraction,
not authorship**: lift them into the shared module so the importer calls the same
code. Do not re-derive the cluster radius, build cap, or category table — they are
already tuned (`CLUSTER_CELL=150m`, `BUILD_CAP=20`, `MIN_SEP=4km`, `REGION_CAP=2`)
and the category table maps to exactly the strings
`SceneryGroup.group_task_for_scenery_group_category()` already knows
(`factory`/`power`/`ware`/`comms`). `IadsRole.for_category()` then decides
`IadsBuildingGroundObject` vs plain `BuildingGroundObject` inside
`generate_tgo_for_scenery` — the importer only sets the category string.

The one importer-specific addition: where the emitter's `REGIONS`/`select()` are
Red-Tide-AO-specific (six hand-picked scan boxes, front-region guarantee), the
generic importer needs a **map-agnostic** selection policy — e.g. attach every
clustered objective to its nearest CP and let per-CP/per-side caps (below) bound
the count, rather than a fixed target laydown. Keep the AO-specific selection in
the emitter CLI; keep the generic policy in the importer adapter.

### 4. Synthesize `SceneryGroup`s

`SceneryGroup.__init__(zone_def, zones, category)` takes real `TriggerZone`s.
Bypass `from_trigger_zones` (ME-specific) and construct directly:

- `zone_def` = synthesized `TriggerZoneCircular` at the cluster **centroid**,
  carrying the category in `properties[1]` (the format `from_trigger_zones` reads
  at `properties[1].get("value")`).
- `zones` = one tiny `TriggerZoneCircular` per building at its `Point(x, z)`.
- Unique, Lua-safe zone names (`escape_string_for_lua`, already applied in
  `generate_tgo_for_scenery`); avoid id collisions with ME zones.

Cleaner alternative to evaluate during build: a `SceneryGroup.from_dump_records()`
classmethod, so synthesis lives next to `from_trigger_zones`.

### 5. Injection point

Add a step in `MizCampaignLoader` (or its `add_*` sequence) that, when enabled,
calls `sceneryimport.load_catalog(terrain)` and appends the synthesized groups to
`self.scenery` **before** the nearest-CP attach loop at line 716 — so imported and
ME-authored scenery share one attach + ownership path. No change to
`start_generator` or `tgogenerator` required.

---

## Gating, balance, de-dup

- **Settings flag** `import_scenery_strike_targets`, **default OFF** while
  playtested (fork convention; mirrors how SCAR/DTC shipped). Document in
  features doc §N + add an in-game-pass-checklist row.
- **Economy balance:** `factory` objectives feed the economy. Importing every
  industrial cluster could swing the economy hard — cap factory objectives per
  CP and/or per side; treat economy impact as a tuning knob, not a given.
- **De-dup vs existing TGOs:** skip an imported cluster whose centroid is within
  `D` of any already-placed objective (ME scenery, IADS buildings, other TGOs) so
  we don't stack a strike target on an existing site.
- **Life filter:** the scanner already drops `life0 == 0` and the ~9.99e+37
  invulnerable sentinels; the curated file should preserve `life0` so the importer
  can re-filter if curation widened the net.

---

## Save / migration

Imported groups are created during campaign generation exactly like ME scenery, so
existing pickles are unaffected and **no migration is needed**. `SceneryGroup` /
`SceneryUnit` already pickle (campaigns persist them today). The settings flag
needs the standard default in `Settings` + (if added mid-stream) a trivial
`getattr`-style default on unpickle.

---

## Testing

Pure-Python, unit-testable without DCS:

- `Point(x, z)` conversion round-trips a known dump row.
- Clustering: a hand-built mini-dump (two type-families, two spatial clusters)
  yields the expected objective count + membership.
- Category mapping table: each sample type → expected category/GroupTask.
- De-dup: a cluster centroid near a seeded TGO is dropped.

The mission-gen leg (16-ft zones actually register kills in-game) is an **in-game
pass**, not CI — add the checklist row with the fail signature
("strike targets show but never register destroyed").

---

## "For all maps" — the longer arc

Phase 1 ships the importer + the one map we already scanned (Germany Cold War,
Berlin/Brandenburg + Fulda). Every additional theater is **one scan pass** of the
build-time scanner → curated `resources/scenery/<terrain>.json`. The importer code
is map-agnostic; coverage accretes file-by-file. This is the data layer the
"campaign builder" (Phase 3) consumes when a designer drops strike targets onto a
blank theater.

## Security reminder

The scanner requires `MissionScripting.lua` desanitized (`io`/`lfs` re-enabled).
That is an **offline build-time-only** change and must be reverted before flying
online/downloaded missions. **Never ship a desanitized `MissionScripting*.lua`**
in any release artifact — the importer consumes a committed *data* file, not the
live desanitized state.

---

## Open questions to resolve at build time

1. Exact pydcs terrain id for Germany Cold War (`theater.terrain.name`) → catalog key.
2. Cluster radius `R` and per-objective / per-CP caps (tune in-game).
3. Curated file format (JSON recommended) + whether the converter lives in
   gitignored `_scenerytools/`.
4. Economy cap policy for imported `factory` objectives.
5. Whether to also import `village`/`oil`/`fuel` families later, or keep Phase 1
   to factory/power/ware/comms.
