# MIST retirement via a MOOSE-backed `mist` compatibility shim

**Status:** ✅ **DONE — MIST retired (2026-06-25).** The shim is live in `base/plugin.json` (the
`"mist"` work-order loads `mist_moose_shim.lua`); `mist_4_5_126.lua` no longer loads. All 43 symbols,
100% vanilla DCS (no MOOSE dep), in mist's existing slot (no reorder). Flight-validated on GermanyCW
(shim logged zero errors; the two crashes seen during testing were pre-existing bugs — civ-helo RAT
crash and a CTLD smoke-zone format bug — fixed separately in #166). The **first** go-live attempt was
reverted for a `dynAdd` shape bug (intercept passes a string `category = "vehicle"`; CTLD passes a
numeric `Group.Category`) → fixed with `_resolve_group_category` + a full audit of every consumer call
site (`dynAdd`'s string category was the only mismatch). **`mist_4_5_126.lua` is kept as a one-line
rollback** until the shim is flown across more campaigns, then delete it (final cleanup).

**Lesson / fix (2026-06-24):** the first swap was merged to `main` without flying it and crashed
immediately — `dynAdd` only handled CTLD's numeric `Group.Category`, but the intercept glue passes a
string (`category = "vehicle"`). Fixed with `_resolve_group_category` (string→`Group.Category`). Then
a **full audit of every consumer call site** against every shim function was done; `dynAdd`'s string
category was the only mismatch (the others — `dynAddStatic`, `goRoute`, `scheduleFunction` incl.
skynet's `rep`-recurring form, `buildWP`, `makeUnitTable`, `groupToRandomZone` — all matched). Old
`mist_4_5_126.lua` kept for one-line rollback. **This time: fly the branch first, merge only on a
clean pass.** After the pass: delete MIST.
**43rd symbol (2026-07-05):** the upstream/dev merge brought in `land_relocate.lua` /
`water_relocate.lua` (upstream #767/#838, part of the base plugin), which call
`mist.getGroupData(name)` and feed the result to `mist.dynAdd`. Upstream runs full MIST; the shim
had no `getGroupData`, so the relocate pass would have died at runtime ("attempt to call field
'getGroupData'"). Added to the shim's Tier 2: a lazily-built mission-editor group DB read from
`env.mission` (names via `env.getValueDictByKey`, deep-copied entries carrying units/route/
country/category — the dynAdd shape). Contract pinned in `tests/lua/test_mist_shim_getgroupdata.py`;
the relocate behavior itself still needs an in-game pass (checklist U1). **When merging future
upstream Lua, grep it for `mist.` and check every symbol against the shim.**

**44th symbol (2026-07-10):** the upstream/dev sync brought the escort-leash fix (upstream #850),
which resolves a mission group id to a name via `mist.DBs.groupsById[id].groupName` — a DB table
the shim didn't build (the read is nil-guarded upstream, so under the shim the leash's id fallback
would have silently resolved nothing rather than died). `_mistRefreshDBs` now also populates
`groupsById` (same entry object as `groupsByName`, keyed by the numeric group id). Contract pinned
in `tests/lua/test_mist_shim_groupsbyid.py`. The U1 grep rule caught it — keep running it on every
upstream Lua merge.

**Supersedes:** the per-consumer MOOSE-native port plan (esp. the `Ops.CTLD` port in
[`414th-ctld-mantis-style-port-scope.md`](414th-ctld-mantis-style-port-scope.md), now shelved).
**Parent:** [`414th-framework-consolidation-notes.md`](414th-framework-consolidation-notes.md).

## The reframing

The goal was always **"drop `mist_4_5_126.lua`,"** not "adopt `Ops.CTLD`." Auditing what MIST actually
does for its consumers shows it fills exactly two roles:

1. **A utility library** — `deepCopy`, `round`, vector math, distances, `metersToNM`, coordinate
   string formatting, etc.
2. **A runtime object database** — `mist.DBs.*` (units/groups/zones/humans by name) + spawn / route /
   schedule / marker helpers.

**MOOSE — already loaded as the standard framework — provides both** (`UTILS.*`, `_DATABASE` +
`UNIT`/`GROUP`/`ZONE:FindByName`, `SCHEDULER`/`MESSAGE`/`MARKER`, plus vanilla `coalition.addGroup`).
So instead of rewriting four consumers (CTLD, SCAR, intercept glue, core `dcs_retribution.lua`) to be
MOOSE-native, we **replace `mist_4_5_126.lua` with a thin `mist` table that delegates to MOOSE.**

**Why this wins:** one artifact retires MIST across *all* consumers; consumers stay byte-for-byte
unchanged (no behavior drift, **SCAR capture/CSAR cannot break** because CTLD is untouched); the
`Ops.CTLD` template-model mismatch (see the shelved port doc) never arises. Tradeoff: call sites stay
`mist.*`-shaped (MOOSE-backed, not "pure MOOSE-native") — acceptable, since the 5,000-line MIST file is
gone and MOOSE does the work.

## The exact surface to implement (42 distinct symbols)

Authoritative — the union of `mist.*` calls across `base/dcs_retribution.lua`, `ctld/CTLD.lua`,
`ctld/ctld-config.lua`, `intercept/intercept-config.lua`, `scar/scar_414_init.lua`,
`skynetiads/skynet-iads-compiled.lua`. (MIST's *internal* self-references are NOT in scope.)

| Tier | Symbols | Backing |
|---|---|---|
| **1 — utils** | `utils.deepCopy` `utils.round` `utils.get2DDist` `utils.get3DDist` `utils.getDir` `utils.toDegree` `utils.metersToNM` `utils.metersToFeet` `utils.makeVec2` `utils.makeVec3` `utils.getHeadingPoints` `utils.zoneToVec3` `utils.tableShow` `vec.mag` `vec.dp` `vec.sub` | `UTILS.*` / `math` / 1-liners |
| **1 — geo/coord** | `getHeading` `getAvgPos` `getLeadPos` `getRandPointInCircle` `terrainHeightDiff` `tostringLL` `tostringMGRS` `getUnitsLOS` `random` | `UTILS.tostringLL`, `coord.*`, `land.*`, vanilla |
| **2 — object DB** | `DBs.unitsByName` `DBs.unitsById` `DBs.groupsByName` `DBs.zonesByName` `DBs.humansByName` | **periodic refresh from `_DATABASE`** (see keystone) |
| **3 — spawn/route/sched** | `dynAdd` `dynAddStatic` `goRoute` `getGroupRoute` `groupToRandomZone` `ground.buildWP` `makeUnitTable` `scheduleFunction` `removeFunction` `addEventHandler` | vanilla `coalition.addGroup`/`addStaticObject`, controller tasking, `timer.*`, `world.addEventHandler` |
| **4 — msg/log** | `message.add` `Logger` | `MESSAGE`/`trigger.action.outText`, `env.info` wrapper |

## Keystone: the DB tier (the only non-trivial part)

The `mist.DBs.*` tables are **both indexed AND iterated** by consumers:
- indexed: `mist.DBs.unitsById[id]`, `mist.DBs.humansByName[name]`, `mist.DBs.zonesByName[name]`;
- **iterated**: `pairs(mist.DBs.unitsByName)` (CTLD L2013), `pairs(mist.DBs.unitsByName)` /
  `pairs(mist.DBs.groupsByName)` (skynet L1264/L1329).

**DCS Lua 5.1 has no `__pairs` metamethod**, so a lazy metatable cannot satisfy iteration. The tables
must hold **real entries**. Approach: a `_refreshDBs()` that walks MOOSE `_DATABASE` (`ForEachUnit`/
`ForEachGroup`, zones) and rebuilds `mist.DBs.*` as real tables of **MIST-shaped entries**, scheduled
periodically (mirroring MIST's own ~5 s DB cadence) and once at start. MOOSE already does the
event-driven tracking; the shim only reshapes.

**Entry shape — ✅ verified against consumer source (2026-06-24); far less is read than expected:**
- `pairs(unitsByName)` (CTLD L2013, skynet L1264) and `pairs(groupsByName)` (skynet L1329) use **only
  the key** — the value is ignored and re-fetched via `Unit.getByName`/`Group.getByName`. So entry
  values can be minimal; only the **key set** must be complete.
- `unitsById[id]` (CTLD L6444) reads **only `.groupId`**.
- `zonesByName[name]` (skynet L3741) reads **only `.point`** (Vec3).
- `humansByName[name]` (CTLD) needs **existence** (truthy table keyed by player unit name) + accept a
  mutable `.losMarkIds` (JTAC autolase, disabled — preserved across refresh defensively).

**Implementation (✅ done):** `_mistRefreshDBs()` scans `coalition.getGroups(side, cat)` over all
sides/categories and rebuilds `unitsByName`/`unitsById`/`groupsByName`/`humansByName` as real
tables; `_mistBuildZones()` builds `zonesByName` once from `env.mission.triggers.zones` (static). Run
once at load + scheduled.

**Refresh cadence reworked (2026-07-12, the MP-performance pass):** the original flat **5 s**
whole-mission rescan was the heaviest standing poll in the plugin stack on a dense mission (every
group of every side/category, every 5 s, all mission long — the 2026-07-12 plugin-load survey's one
"always-on baseline" finding). It is now **birth-driven + a 30 s fallback**: an `S_EVENT_BIRTH`
(QRA clones, Combat SAR, CTLD, Super Gaggle, a player slotting in) schedules one **debounced**
rebuild (2 s, a burst of births coalesces into one), so a late spawn reaches the DBs *faster* than
the old scan guaranteed; the periodic pass — slowed to 30 s — only bounds staleness for
**removals** (a dead group's entry lingers up to one period). That staleness is safe by the
consumer contract above: every consumer uses the key set and re-fetches via
`Group.getByName`/`Unit.getByName`, so a stale entry resolves nil and is skipped, never acted on.
Pinned by `tests/lua/test_mist_shim_db_refresh.py` (birth-triggered refresh, burst coalescing, the
birthless-spawn fallback, dead-entry drop).

## Rollout plan (each step keeps `main` safe)

1. **Foundation:** `resources/plugins/base/mist_moose_shim.lua`. **✅ DONE — all 42 symbols**, all
   replicated verbatim from MIST or thin vanilla-DCS wrappers. **It ended up 100% vanilla DCS — no
   MOOSE dependency at all** (`tostringLL` is now inlined rather than delegating to `UTILS`). Dead-path
   best-effort impls: `getUnitsLOS`/`getGroupRoute`/bracket-form `makeUnitTable` (CTLD JTAC autolase,
   disabled in Retribution).
2. **Swap (✅ staged on this branch, awaiting in-game pass):** `base/plugin.json`'s `"mist"` work-order
   now points at `mist_moose_shim.lua` instead of `mist_4_5_126.lua`. Because the shim has no MOOSE
   dependency, it stays in mist's **existing first slot — no reordering.** The old `mist_4_5_126.lua`
   file is **kept in the repo** so rollback is a one-line `plugin.json` revert.
   ⚠️ **This is the go-live change** — merging it to `main` ships to the whole squadron via the rolling
   release. Fly it from this branch FIRST. In-game pass: CTLD troop/crate/FOB sling-load cycle, SCAR
   capture + CSAR, intercept/QRA, Skynet IADS (if selected), core glue (state-write/messages).
3. **Cleanup (✅ DONE 2026-07-10):** `mist_4_5_126.lua` deleted after weeks of clean flights
   (checklist G7 VERIFIED 2026-06-25 and no shim errors since); Tech-Stack docs updated.
   Rollback is no longer one line: restore the file from git history AND re-point
   `base/plugin.json`'s `"mist"` work-order at it. The MIST→MOOSE consolidation is done.

## Risks / watch-items

- **Entry-shape fidelity** is the main correctness risk — a missing field silently breaks a consumer
  at runtime (not parse time). Validate field-by-field against consumer reads.
- **Load order** in `base/plugin.json` is load-bearing: shim after MOOSE, before consumers.
- **Skynet** still uses MIST (`skynet-iads-compiled.lua`); the shim must cover it while Skynet remains
  selectable. Once Skynet is retired (post-MANTIS-default), that consumer drops out.
- Lua 5.1 only; define before use; the `lua-lint.yml` `luac5.1 -p` gate catches parse errors but not
  behavior — every tier needs the in-game pass.
