# Framework Consolidation — Retire MIST, Standardize on MOOSE

**Status:** strategy / proposal (not started). Phase 1 (Skynet → MANTIS) is in progress under
[`414th-mantis-migration-notes.md`](414th-mantis-migration-notes.md).
**Date:** 2026-06-24

## Thesis

The mission-scripting layer currently loads **two** Lua frameworks as core dependencies: **MIST**
(`mist_4_5_126.lua`, a low-level utility library, largely maintenance-mode) and **MOOSE**
(`Moose.lua`, the modern, actively-developed OOP framework). They are **independent** — `Moose.lua`
references MIST **zero** times; MOOSE is fully self-contained. Every system we run is built on one or
the other, and a few use both.

Standardizing on a single framework — **MOOSE** — and retiring MIST would give us: one modern,
maintained framework instead of one modern + one stale; less mission load-time and a smaller runtime
surface; and one mental model for everyone touching plugins. This doc inventories the work and
sequences it. **The Skynet → MANTIS migration is phase 1** of this larger arc — Skynet is the single
biggest MIST consumer that already has a first-class MOOSE replacement.

> This is a multi-feature *program*, not a single change, and it touches upstream-shared plugins.
> It should be done incrementally, each step behind validation, and coordinated with the upstreaming
> strategy ([`414th-upstreaming-inventory.md`](414th-upstreaming-inventory.md)).

## Current state

`resources/plugins/base/plugin.json` load order: **`mist_4_5_126.lua` → `json.lua` →
`dcs_retribution.lua` → `Moose.lua`**. MIST loads first as a base dependency; the core glue
(`dcs_retribution.lua`) is written against it.

### MIST consumers (the retirement work list)

Ref counts are `mist[._]` occurrences — a rough gauge of porting cost, not an exact measure.

| Plugin | MIST refs | Author | MOOSE equivalent | Notes |
|---|---:|---|---|---|
| `ctld` | 84 | upstream | ✅ `Ops.CTLD` (bundled in `Moose.lua`) | Largest single port; behavior-sensitive (logistics/CSAR). |
| `dismounts` | 58 | upstream | ❌ none | No clean MOOSE analogue — rewrite, or keep MIST solely for this, or retire the feature. **The real blocker to a *full* MIST drop.** |
| `skynetiads` | 50 | upstream (vendored) | ✅ **MANTIS** | **Phase 1, in progress.** Removes the biggest "has a replacement" chunk. |
| `ewrs` | 13 | upstream | ✅ MANTIS EWR / MOOSE detection | Likely becomes **redundant** once MANTIS owns EWR — may delete rather than port. |
| `scar` init | 10 | **414th** | partial | Already uses MOOSE too; port the MIST helper calls to MOOSE utils. |
| `intercept-config` | 10 | 414th/retribution glue | partial | Already uses MOOSE too; same as SCAR. |
| `base/dcs_retribution.lua` | 5 | retribution core | ✅ all 5 portable | The core gate — see below. |

### MOOSE consumers (already on the target framework)

`tars`, `tic`, `scar`, `c130j` (414th features); plus `MooseAtis`,
`MooseAutolase`, `MooseSoundhandler`, `MooseMarkerOps`, `intercept`, `civilian_traffic`, `bigeye`,
`airboss`, and `skynetiads` (transitional, uses both). MOOSE also bundles ready equivalents we don't
yet exploit: `Ops.CTLD`, `ATIS`, `AUTOLASE`, `RANGE`, `DETECTION_AREAS`, `MANTIS`.

### Confirmed MIST-free

`splashdamage3` (the 414th PINNED locked build) has **zero** MIST dependency — the only matches are
comments. Retiring MIST does **not** touch the locked Splash Damage build.

## The core gate: `base/dcs_retribution.lua`

MIST cannot be dropped from `base/plugin.json` until the core glue stops using it. It uses MIST for
exactly **5** things, each with a native-DCS or MOOSE replacement:

| MIST call | Replacement |
|---|---|
| `mist.Logger:new(...)` | MOOSE `BASE` logging (`:I()/:E()`) or `env.info` |
| `mist.message.add(msg)` | MOOSE `MESSAGE` or native `trigger.action.outText` |
| `mist.scheduleFunction(...)` | MOOSE `SCHEDULER` or native `timer.scheduleFunction` |
| `mist.getHeading(unit)` | MOOSE `UNIT:GetHeading()` or compute from `getPosition` |
| `mist.addEventHandler(onEvent)` | MOOSE `EVENT` handler or native `world.addEventHandler` |

Small, mechanical, and self-contained — this is the *last* step (drop MIST), not the first.

## Phased retirement plan

Ordered by replacement-readiness and risk. Each phase is independently shippable and gated by its
own in-game pass (Lua can't be CI-exercised).

1. **Skynet → MANTIS** *(in progress)* — biggest MIST consumer with a first-class MOOSE replacement.
   See the MANTIS migration notes. Removes ~50 MIST refs.
2. **EWRS → DELETE** — ✅ **DONE (2026-06-24)**: redundant with the fork's MOOSE `bigeye`; removed
   (was already dormant — not in `plugins.json`).
   See [`414th-ewrs-retirement-decision.md`](414th-ewrs-retirement-decision.md).
3. **SCAR + intercept glue** — ⚠️ **reclassified (2026-06-24): NOT "helper calls."** These are
   **core dynamic spawning + ground routing**: `mist.dynAdd` spawns SCAR's HVT convoy + SOF teams
   and the intercept EWR backstops; `mist.goRoute`/`mist.ground.buildWP` drive SCAR convoy routing;
   plus `mist.scheduleFunction`. Porting blind in **default-ON flagship SCAR** risks silently
   breaking convoy/SOF spawning (only caught in-game). Same risk class as CTLD — needs in-game
   validation, not a blind swap. `mist.scheduleFunction` → native `timer.scheduleFunction` is the
   only clean 1:1; `dynAdd` → `coalition.addGroup` and `goRoute` → MOOSE ground routing both need
   careful behavior-matching + a SCAR/QRA flight test.
4. **CTLD → `Ops.CTLD`** — the large one (~8.7k lines, default-ON, ~26 distinct MIST calls). Config-
   bridge swap mirroring Skynet→MANTIS. **✅ Phase-1 spike done (2026-06-24):** `Ops.CTLD` covers
   everything Retribution uses (menus/FOB/AA-repair/beacons/smoke/cabin-limits/save-load all native);
   JTAC autolase dropped (disabled in Retribution; front-line FAC is the independent flotgenerator
   MQ-9 AFAC). **Revised to ~8–12 days, MEDIUM risk.** **⚠️ Still not a clean isolatable port:** it's
   woven into Python flight-planning and the **SCAR feature reuses the air-assault CTLD machinery**
   (capture + CSAR), so even a gated bridge must be SCAR-validated and must not be blind-ported in one
   pass. Full findings in [`414th-ctld-mantis-style-port-scope.md`](414th-ctld-mantis-style-port-scope.md).
5. **dismounts** — ✅ **RETIRED (2026-06-24)**. Was the would-be MIST-drop blocker (no MOOSE
   successor), but turned out to be already dormant (not in `plugins.json`), so it was deleted
   outright. See [`414th-dismounts-decision.md`](414th-dismounts-decision.md). No longer blocks the
   MIST drop.
6. **Core glue** (`dcs_retribution.lua`) — port the 5 MIST calls above to native/MOOSE.
7. **Drop MIST** — remove `mist_4_5_126.lua` from `base/plugin.json`. **Definition of done.**

### ⭐ STRATEGY CHANGE (2026-06-24) — retire MIST with a MOOSE-backed shim, not per-consumer ports

Phases 3/4/6 above (rewrite SCAR/intercept, CTLD, and core glue to be MOOSE-native) are **no longer
the plan.** An audit of what MIST actually does for its consumers showed it fills exactly two roles —
a **utility library** and a **runtime object database** — and **MOOSE (already loaded) provides
both** (`UTILS.*`, `_DATABASE`, `SCHEDULER`/`MESSAGE`/`MARKER`, + vanilla `coalition.addGroup`).

So instead of rewriting four consumers, we **replace `mist_4_5_126.lua` with a thin `mist` table that
delegates to MOOSE** — implementing only the **42 distinct symbols** the consumers actually call. One
artifact retires MIST everywhere; consumers stay byte-for-byte unchanged (no behavior drift, **SCAR
capture/CSAR cannot break**); the `Ops.CTLD` template-model mismatch never arises. This makes the old
"CTLD is the gate, batch everything at the end" sequencing moot.

**Active plan:** [`414th-mist-moose-shim-notes.md`](414th-mist-moose-shim-notes.md) (surface, tier
breakdown, the DB-from-`_DATABASE` keystone, rollout). The `Ops.CTLD` port is **shelved**
([`414th-ctld-mantis-style-port-scope.md`](414th-ctld-mantis-style-port-scope.md)). Foundation
(`resources/plugins/base/mist_moose_shim.lua`, Tier-1a) is in; it is **not yet in `base/plugin.json`**,
so MIST still loads and `main` is unaffected until the validation swap.

The completed phases (dismounts, ewrs) were **deletions of dead code** — still correct, independent of
this change. The MANTIS G6 pass (done) was likewise independent.

## Parallel track: lean into the MOOSE `Ops.*` family

Going MOOSE-first makes the whole bundled `Ops.*` stack the natural toolbox (it's already in
`Moose.lua` — not gated by the MIST removal). The **service tier** (`Ops.CSAR`/`RescueHelo`,
`PlayerTask`, `Intel`, `ATIS`, `CTLD`, `MANTIS`) is a low-risk, opt-in extension of exactly this
consolidation and should be folded in opportunistically (e.g. `Ops.CSAR` alongside the SCAR MIST
port). The **strategic tier** (`Ops.Chief`/`Commander`/`Legion`…) is a *different campaign engine*
that conflicts with Retribution's Python brain and is explicitly **out of scope** (the fork already
chose the Python path — CLAUDE.md §17, `turnless.md`). Full breakdown:
[`414th-moose-ops-opportunity-map.md`](414th-moose-ops-opportunity-map.md).

## Upstream coordination

Most MIST consumers are **upstream Retribution plugins** (`ctld`, `dismounts`, `ewrs`, the vendored
`skynetiads`, `mist` itself, core `dcs_retribution.lua`). Replacing them is the kind of generic,
broadly-valuable modernization that belongs upstream, not as a fork-only divergence:

- Coordinate each phase with [`414th-upstreaming-inventory.md`](414th-upstreaming-inventory.md) — these
  are strong upstream-PR candidates (MANTIS, `Ops.CTLD`, MIST retirement).
- 414th-authored pieces (`scar`, `intercept`, `c130j`, TIC/TARS) are already MOOSE and
  need no upstream coordination.
- The 414th PINNED Splash Damage build is unaffected (MIST-free).

## Risks / non-goals

| Item | Note |
|---|---|
| `dismounts` has no MOOSE equivalent | Hard blocker to a *full* MIST drop. Phase 5 is a real decision, not a port. Until resolved, MIST may have to stay solely for dismounts. |
| CTLD behavior drift | `Ops.CTLD` ≠ the vendored CTLD line-for-line; logistics/CSAR feel must be validated in-game. |
| Upstream-shared churn | Don't diverge the fork further; carve these as upstream contributions where possible. |
| Splash Damage | PINNED, locked, MIST-free — **do not touch** during this work. |
| Not a rewrite-everything mandate | The goal is *one framework*, reached incrementally; if a plugin has no MOOSE path and low value, retiring the feature is a valid outcome. |

## Definition of done

`mist_4_5_126.lua` is removed from `resources/plugins/base/plugin.json`, every former MIST consumer
runs on MOOSE (or is retired), and the mission loads a single scripting framework.
