# Scope: Port `ctld` (MIST) → MOOSE `Ops.CTLD` (consolidation phase 4)

**Status:** scoping / not started (no code change yet)
**Date:** 2026-06-24
**Parent:** [`414th-framework-consolidation-notes.md`](414th-framework-consolidation-notes.md) phase 4.

## Summary

`ctld` is the **largest and highest-risk** MIST port: `resources/plugins/ctld/CTLD.lua` is ~8,710
lines, **default-ON** (`plugin.json: defaultValue: true`), upstream (Ciribob/VEAF), with ~26 distinct
MIST calls. MOOSE bundles **`Ops.CTLD`** (in `Moose.lua`, v1.3.38), so the **config-bridge pattern**
that works for Skynet→MANTIS applies here too — but `Ops.CTLD` is not a drop-in, and because CTLD is
default-on, any behavior drift hits many campaigns. **Estimated ~15–20 working days incl. in-game QA.**

This doc scopes the port; it does not commit to it. Recommended sequencing: **after** EWRS (delete)
and the SCAR/intercept glue, **before** dismounts.

## How CTLD is wired into Retribution (the part that carries over)

Python generates a `dcsRetribution.Logistics` data table; `ctld-config.lua` reads it and configures
the vendored CTLD. The port keeps the **Python side unchanged** and rewrites only the config bridge:

- Generator: `game/missiongenerator/luagenerator.py` (~L366–415) + `missiondata.py`
  (`LogisticsInfo`/`CargoInfo`); flight plans `game/ato/flightplans/airlift.py`, `airassault.py`.
- Emitted table: `dcsRetribution.Logistics.{flights,transports,crates,spawnable_crates}`.
- Naming conventions the bridge depends on (must be preserved): `<group>PICKUP_ZONE`,
  `<group>DROPOFF_ZONE`, `<group> TARGET_ZONE`, `<group>logistic`, `<group>crate_spawn`, and
  index-based crate "weights" (`"200"`, `"201"`, …) mapped to unit types.
- `tailorctld: true` clears CTLD defaults so the mission config is fully Python-driven — good, it
  means the bridge owns everything and there is little hidden upstream default behavior to preserve.

This is exactly the Skynet→MANTIS shape: **keep the generated data table as source of truth; swap the
Lua consumer.**

## Feature areas to preserve

Troop transport (custom 2/4/6/10/12/24 squad configs w/ JTAC/AT/AA mix), crate sling-load + unpack,
FOB build (3 crates → hub, 120 s), JTAC autolase (`dcsRetribution.JTACs[]`), AA-system build/repair,
radio beacons (battery life), smoke marking, vehicle repacking, per-aircraft cabin limits, and the
414th CH-47 AGL/`inAir()` workaround.

## `Ops.CTLD` coverage — verify before committing (do NOT take the gap list on faith)

A read of `Ops.CTLD` shows a broad API (`AddTroopsCargo`, `AddCratesCargo`, `AddStaticsCargo`,
`AddCratesRepair`, `SetUnitCapabilities`, `AddCTLDZone`, FSM events `TroopsPickedUp`/`CratesBuild`/…,
`EnableLoadSave`). The investigation flagged several **possible gaps** — but some of these are
**suspect and must be checked in the Phase-1 spike**, not assumed:

| Area | Flagged as | Skeptical note (verify) |
|---|---|---|
| F10 radio menus | "missing" | **Doubtful** — MOOSE `Ops.CTLD` is known to generate its own radio menus. Most likely present; verify the structure matches what players expect. |
| JTAC autolasing | "missing" | Plausibly not in `Ops.CTLD` — **but the fork already ships `MooseAutolase` (`Plugin_Autolase_JTAC.lua`)**. Wire JTACs to that rather than porting CTLD's 270-line `JTACAutoLase`. Cross-check `dcsRetribution.JTACs[]` against MooseAutolase. |
| FOB build / beacons / repacking / AA stacking | "partial / missing" | Genuinely the most likely real gaps. Confirm against `Ops.CTLD` methods; where absent, implement thin bridge logic (timers/state) rather than re-vendoring CTLD. |
| Smoke / cabin limits / dynamic cargo | present | `SmokePositionNow`, `SetUnitCapabilities`, GC handlers exist — likely fine. |

**Action: a Phase-1 spike must confirm the real coverage of `Ops.CTLD` in the bundled `Moose.lua`
before estimating the custom-bridge work.** The 15–20 day figure assumes JTAC reuses MooseAutolase
and FOB/beacons/repacking need modest bridge code; it grows if `Ops.CTLD` is thinner than it looks.

## Behavior-risk areas (default-ON → regressions hit real campaigns)

Highest-risk validation points for an in-game pass: crate weight→unit mapping and spawn positions;
troop squad composition + cabin limits; pickup/dropoff zone name matching and reinforcement caps;
JTAC deploy → radio callouts + laser actually tracking; FOB 120 s build + hub spawning; beacon
battery/retrieval; continuous smoke marking; and the CH-47 AGL workaround.

## Phased plan (config-bridge-first, mirrors Skynet→MANTIS)

1. **Spike / foundation (1–2 d):** new `moose_ctld_config.lua`; parse `dcsRetribution.Logistics`;
   `CTLD:New` per coalition; `AddTroopsCargo`/`AddCratesCargo`/`SetUnitCapabilities`/`AddCTLDZone`;
   `Start()`. **Confirm `Ops.CTLD` feature coverage here** — this answers the gap questions above.
2. **Core load/unload + menus (3–4 d):** validate F10 menus + troop/crate pickup/drop cycle.
3. **Advanced features (5–7 d):** JTAC (prefer wiring to **MooseAutolase**), FOB, beacons, repacking,
   AA build — implement only what `Ops.CTLD` genuinely lacks, as thin bridge code.
4. **Validation (5–7 d):** in-game pass across airlift / air-assault / logistics missions (default-on
   ⇒ must be thorough). Add rows to `414th-ingame-pass-checklist.md`.
5. **Cleanup (1 d):** drop `CTLD.lua` from `plugin.json`; docs. Removes ~26 MIST occurrences.

## Open questions for the Phase-1 spike

- Does the bundled `Ops.CTLD` expose load/unload via public methods/events, or only internals?
- Are its radio menus present and adequate (the suspect "missing" claim)?
- Can JTAC needs be met by the existing `MooseAutolase` plugin instead of a custom port?
- Does `EnableLoadSave` persistence survive Retribution's mission reload model?
- Must every Python-generated zone be registered via `AddZone`, or are trigger zones queryable by name?

## Effort

**~15–20 working days** (≈1 senior-dev week of build + ~1 week QA), MEDIUM–HIGH risk — dominated by
JTAC, FOB, and the default-on validation surface. The biggest single MIST port; do it after the cheap
wins (EWRS) so the program shows progress before taking on this one.
