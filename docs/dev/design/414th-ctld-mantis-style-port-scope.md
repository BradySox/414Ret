# Scope: Port `ctld` (MIST) → MOOSE `Ops.CTLD` (consolidation phase 4)

**Status:** Phase-1 spike COMPLETE (2026-06-24) — `Ops.CTLD` coverage confirmed, gap table resolved,
JTAC dropped from scope. No bridge code written yet; Phase-1 *foundation* is the next step.
**Date:** 2026-06-24
**Parent:** [`414th-framework-consolidation-notes.md`](414th-framework-consolidation-notes.md) phase 4.

## Summary

`ctld` is the **largest and highest-risk** MIST port: `resources/plugins/ctld/CTLD.lua` is ~8,710
lines, **default-ON** (`plugin.json: defaultValue: true`), upstream (Ciribob/VEAF), with ~26 distinct
MIST calls. MOOSE bundles **`Ops.CTLD`** (in `Moose.lua`, v1.3.38), so the **config-bridge pattern**
that works for Skynet→MANTIS applies here too — but `Ops.CTLD` is not a drop-in, and because CTLD is
default-on, any behavior drift hits many campaigns. **Estimated ~8–12 working days incl. in-game QA**
(revised down after the Phase-1 spike confirmed `Ops.CTLD` covers everything Retribution uses and JTAC
was dropped — see coverage section; the dominant cost is now the default-on validation + SCAR pass).

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

## ⚠️ Cross-feature intersection — CTLD is NOT a clean, isolatable port (the key risk)

Unlike Skynet/IADS (a self-contained Lua consumer), CTLD is **woven into Python flight-planning and a
flagship feature**, so it cannot be swapped behind a simple gate as cleanly as MANTIS:

- **Flight-planning layer:** `game/ato/flightplans/airlift.py` + `airassault.py` build CTLD
  pickup/drop-off zones into the plan, and `game/theater/interfaces/CTLD.py` mixes `ctld_zones` onto
  control points. The AirLift/AirAssault flight plans assume the legacy CTLD's zone/menu model.
- **SCAR depends on it.** `game/dcs/aircrafttype.py` is explicit: the SCAR commander-capture path
  delivers its team "via the air-assault CTLD machinery," and the downed-team **CSAR recovery loop
  reuses that same machinery.** SCAR is a default-ON flagship (§15). **Porting CTLD can therefore
  break SCAR's capture + CSAR flows** even if airlift/logistics look fine.

**Consequence:** a gated `ctld_engine: legacy | moose` bridge keeps *new* logistics inert, but the
moment it is exercised it must satisfy SCAR's air-assault/CSAR expectations too — so the in-game pass
**must include a full SCAR capture + CSAR run**, not just airlift/logistics. Coordinate with the SCAR
owner before flipping the default. This is the main reason CTLD is sequenced last among the live ports
and should not be blind-ported in one pass.

## Feature areas to preserve

Troop transport (custom 2/4/6/10/12/24 squad configs w/ JTAC/AT/AA mix), crate sling-load + unpack,
FOB build (3 crates → hub, 120 s), JTAC autolase (`dcsRetribution.JTACs[]`), AA-system build/repair,
radio beacons (battery life), smoke marking, vehicle repacking, per-aircraft cabin limits, and the
414th CH-47 AGL/`inAir()` workaround.

## `Ops.CTLD` coverage — ✅ Phase-1 spike COMPLETE (2026-06-24)

A read of the bundled `Moose.lua` (v1.3.38, `CTLD` class @ ~L73306, **71 public methods**) **refutes
most of the suspected gaps.** Verified directly against the source — do NOT revert to the old "gap"
assumptions:

| Area | Was flagged | **Verified result (Moose.lua)** |
|---|---|---|
| F10 radio menus | "missing" | ✅ **PRESENT** — `_RefreshF10Menus()` (@L2030 within CTLD) auto-builds the full `MENU_GROUP` tree (CTLD → Manage Troops → Load troops → subcategory menus). |
| FOB build / AA build+repair | "most likely real gaps" | ✅ **PRESENT** — `_BuildCrates`, `_BuildObjectFromCrates`, `_RepairCrates`, `_RepairObjectFromCrates`, `AddCratesRepair`. |
| Beacons | "partial/missing" | ✅ **PRESENT** — `DropBeaconNow`, `CheckDroppedBeacons`. |
| Smoke / cabin limits | present | ✅ Confirmed — `SmokePositionNow`, `SmokeZoneNearBy`, `SetUnitCapabilities`. |
| Save/load persistence | open question | ✅ Event path present — `onbeforeSave`/`onafterSave`/`onbeforeLoad`/`onafterLoad` (confirm survives Retribution reload model during build). |
| Load/unload model | open question | ✅ **Full FSM** — `TroopsPickedUp`/`CratesPickedUp`/`TroopsDeployed`/`CratesDropped`/`CratesBuild`/`TroopsRTB` events + `onbefore`/`onafter` hooks. |
| Hover/load mechanics (CH-47) | n/a | ✅ `IsCorrectHover`, `CanHoverLoad`, `AutoHoverLoad`, `IsUnitInAir` — basis for the AGL workaround. |
| **JTAC autolasing** | "missing → port or MooseAutolase" | ⛔ **OUT OF SCOPE — drop entirely.** See below. |

### JTAC autolase is dropped from the port (not ported, not bridged)

CTLD's JTAC autolase is **disabled and unused in Retribution**, and front-line target lasing is a
**separate, independent system**:

- `ctld-config.lua` defaults `autolase = false`; the runtime log confirms `CTLD plugin - JTAC AutoLase
  enabled = false` on every mission load. It is only enabled by the `ctld.autolase` plugin option,
  which Retribution does not set.
- Front-line forward air control is the **flotgenerator MQ-9 Reaper AFAC** (`game/missiongenerator/
  flotgenerator.py` ~L260–300): a Python-spawned drone over the FLOT with DCS-native `FAC` tasking +
  per-front laser code, invisible/immortal, orbiting at 5000ft. **It does not touch CTLD or
  MooseAutolase at all.**
- `dcsRetribution.JTACs[]` is still emitted (`luagenerator.py` ~L354) but as **metadata describing
  those AFAC drones** (callsign/freq/laser code for kneeboard/radio reference), NOT input to CTLD
  autolase. The CTLD port ignores it.

**Net:** no `JTACAutoLase` port, no MooseAutolase wiring. This was the *only* confirmed gap, so with
it dropped, **`Ops.CTLD` covers everything Retribution actually uses.**

### Revised assessment

The gap table is effectively empty: every CTLD feature Retribution exercises (troops, crates, FOB,
AA build/repair, beacons, smoke, cabin limits, zones, F10 menus, save/load) has a native `Ops.CTLD`
counterpart. The port therefore collapses to **(1) faithful config-bridge translation** of
`dcsRetribution.Logistics` → `Ops.CTLD` calls, and **(2) SCAR capture + CSAR validation** (the real
remaining risk — CTLD is the machinery SCAR's flagship reuses). No custom feature reimplementation is
expected. **Effort revised down from 15–20 days / HIGH to ~8–12 days / MEDIUM**, dominated by the
default-on validation surface and the SCAR integration pass rather than capability gaps.

## Behavior-risk areas (default-ON → regressions hit real campaigns)

Highest-risk validation points for an in-game pass: crate weight→unit mapping and spawn positions;
troop squad composition + cabin limits; pickup/dropoff zone name matching and reinforcement caps;
JTAC deploy → radio callouts + laser actually tracking; FOB 120 s build + hub spawning; beacon
battery/retrieval; continuous smoke marking; and the CH-47 AGL workaround.

## Phased plan (config-bridge-first, mirrors Skynet→MANTIS)

1. **Spike (✅ DONE 2026-06-24) / foundation (1–2 d):** coverage spike complete — `Ops.CTLD` confirmed
   to cover everything Retribution uses (see coverage section). **Foundation still to build:** new
   `moose_ctld_config.lua`; parse `dcsRetribution.Logistics`; `CTLD:New` per coalition;
   `AddTroopsCargo`/`AddCratesCargo`/`SetUnitCapabilities`/`AddCTLDZone`; `Start()`.
2. **Core load/unload + menus (3–4 d):** validate F10 menus + troop/crate pickup/drop cycle.
3. **Advanced features (5–7 d):** JTAC (prefer wiring to **MooseAutolase**), FOB, beacons, repacking,
   AA build — implement only what `Ops.CTLD` genuinely lacks, as thin bridge code.
4. **Validation (5–7 d):** in-game pass across airlift / air-assault / logistics missions (default-on
   ⇒ must be thorough). Add rows to `414th-ingame-pass-checklist.md`.
5. **Cleanup (1 d):** drop `CTLD.lua` from `plugin.json`; docs. Removes ~26 MIST occurrences.

## Open questions — Phase-1 spike answers (2026-06-24)

- ✅ **Load/unload via public methods/events?** Yes — full FSM event model
  (`TroopsPickedUp`/`CratesBuild`/`TroopsDeployed`/…) plus `onbefore`/`onafter` hooks.
- ✅ **Radio menus present and adequate?** Yes — `_RefreshF10Menus()` auto-builds the menu tree; the
  "missing" claim was wrong. (Still verify the structure matches player expectations during build.)
- ✅ **JTAC via MooseAutolase?** Moot — CTLD JTAC autolase is disabled/unused in Retribution and
  front-line FAC is the independent flotgenerator MQ-9 AFAC, so **JTAC is dropped, not ported.**
- 🟡 **`EnableLoadSave` survives Retribution's reload model?** Save/load event handlers exist; the
  reload-survival question carries into the foundation build (confirm with a real save/reload).
- 🟡 **Zone registration — `AddZone` vs name-queryable trigger zones?** `AddZone`/`AddCTLDZone`/
  `GetCTLDZone`/`AddCTLDZoneFromAirbase` all exist; pin down the exact registration path against the
  Python-generated `<group>PICKUP_ZONE`/`DROPOFF_ZONE`/`TARGET_ZONE` names in the foundation step.

## Effort

**~8–12 working days, MEDIUM risk** (revised down from 15–20 / HIGH after the Phase-1 spike). JTAC and
the feared FOB/beacon/menu gaps are gone — `Ops.CTLD` covers them. Remaining cost is dominated by the
**default-on validation surface** and the **SCAR capture + CSAR integration pass** (CTLD is SCAR's
machinery), not capability reimplementation. Still the biggest single MIST port; EWRS/dismounts are
already retired, so this is the next live target.
