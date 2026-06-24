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

`flightcontrol`, `tars`, `tic`, `scar`, `c130j` (414th features); plus `MooseAtis`,
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
2. **EWRS → retire or fold into MANTIS** — evaluate whether MANTIS EWR makes the standalone `ewrs`
   plugin redundant. If so, delete it (≈13 refs gone for near-zero cost); else port to MOOSE detection.
3. **SCAR + intercept glue** — port their handful of MIST helper calls to MOOSE (both already load
   MOOSE). 414th-owned, so no upstream coordination needed. ~20 refs.
4. **CTLD → `Ops.CTLD`** — the large one. Swap the vendored MIST-based `CTLD.lua` for MOOSE
   `Ops.CTLD` + a config bridge (mirrors the Skynet→MANTIS pattern). Behavior-sensitive; needs a
   careful in-game pass on transport/CSAR flows. ~84 refs.
5. **dismounts** — decide: rewrite on MOOSE, keep MIST *only* for this one plugin (no full drop), or
   retire the feature. This is the gating decision for whether MIST leaves the build entirely.
6. **Core glue** (`dcs_retribution.lua`) — port the 5 MIST calls above to native/MOOSE.
7. **Drop MIST** — remove `mist_4_5_126.lua` from `base/plugin.json`. **Definition of done.**

## Upstream coordination

Most MIST consumers are **upstream Retribution plugins** (`ctld`, `dismounts`, `ewrs`, the vendored
`skynetiads`, `mist` itself, core `dcs_retribution.lua`). Replacing them is the kind of generic,
broadly-valuable modernization that belongs upstream, not as a fork-only divergence:

- Coordinate each phase with [`414th-upstreaming-inventory.md`](414th-upstreaming-inventory.md) — these
  are strong upstream-PR candidates (MANTIS, `Ops.CTLD`, MIST retirement).
- 414th-authored pieces (`scar`, `intercept`, `c130j`, TIC/TARS/Flight Control) are already MOOSE and
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
