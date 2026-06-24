# MIST retirement via a MOOSE-backed `mist` compatibility shim

**Status:** ✅ **all 42 symbols implemented (2026-06-24); shim still inert.** Next: `base/plugin.json`
load-order swap (`mist_4_5_126.lua` → `mist_moose_shim.lua`) + in-game pass, then delete MIST.
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
sides/categories every 5 s and rebuilds `unitsByName`/`unitsById`/`groupsByName`/`humansByName` as real
tables; `_mistBuildZones()` builds `zonesByName` once from `env.mission.triggers.zones` (static). Run
once at load + scheduled.

## Rollout plan (each step keeps `main` safe)

1. **Foundation:** new `resources/plugins/base/mist_moose_shim.lua`. **✅ DONE — all 42 symbols.**
   Tier 1 (utils/geo) + Tier 2 (object DB) + Tier 3 (sched/events/wp + spawn/route) + Tier 4 (msg/log),
   replicated from MIST or thin vanilla-DCS/`UTILS` wrappers. Notes: `tostringLL` delegates to
   `UTILS.tostringLL` (cosmetic, verify format in-game); `getUnitsLOS`/`getGroupRoute`/bracket-form
   `makeUnitTable` serve the CTLD JTAC-autolase path, which is **disabled** in Retribution (best-effort
   impls). **NOT yet in `base/plugin.json`** → `mist_4_5_126.lua` still loads, `main` unchanged until
   the swap.
2. **Fill tiers 2–4**, verifying entry shapes against each consumer's reads.
3. **Validation swap (gated/branch):** in `base/plugin.json`, replace `mist_4_5_126.lua` with the shim
   (must load **after** `Moose.lua`, **before** consumers). In-game pass: CTLD troop/crate/FOB cycle,
   SCAR capture + CSAR, intercept/QRA, Skynet IADS (if selected), core glue. Add checklist rows.
4. **Cleanup:** delete `mist_4_5_126.lua`; drop its `base/plugin.json` entry; update Tech-Stack docs
   (MIST row → retired). Definition of done for the whole MIST→MOOSE consolidation.

## Risks / watch-items

- **Entry-shape fidelity** is the main correctness risk — a missing field silently breaks a consumer
  at runtime (not parse time). Validate field-by-field against consumer reads.
- **Load order** in `base/plugin.json` is load-bearing: shim after MOOSE, before consumers.
- **Skynet** still uses MIST (`skynet-iads-compiled.lua`); the shim must cover it while Skynet remains
  selectable. Once Skynet is retired (post-MANTIS-default), that consumer drops out.
- Lua 5.1 only; define before use; the `lua-lint.yml` `luac5.1 -p` gate catches parse errors but not
  behavior — every tier needs the in-game pass.
