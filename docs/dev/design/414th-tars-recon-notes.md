# 414th — TARS recon integration (design notes)

Goal: make MOOSE **Ops.TARS** (Tactical Air Recon System, v2.3.2) the runtime engine
for the existing `FlightType.TARPS` recon flights, and feed its landing-debrief results
back into the 414th **BDA fog-of-war** so confirmed BDA tracks the units a recon pass
*actually photographed* — not just "a TARPS flight overflew the package target."

Plugin default: **ON** (414th choice). When off, TARPS behaves exactly as before
(geometric overflight reveal); the bridge is additive and a no-op. The Lua is not
runnable in CI, so it still warrants an in-game pass.

---

## Why TARS had to be vendored as a standalone script

`FLIGHTCONTROL` ships inside the vendored `resources/plugins/base/Moose.lua`, but **TARS
does not** — the bundle (Jun 2026) predates it. TARS is, however, a real MOOSE develop
file (`Moose Development/Moose/Ops/TARS.lua`) and is **API-compatible** with the vendored
bundle: every MOOSE class it calls (`BASE, CLIENT, COORDINATE, MENU_GROUP[_COMMAND],
MESSAGE, SCORING, SET_UNIT, UNIT, ZONE_RADIUS`) already exists there. So we vendor
`TARS.lua` verbatim (attribution preserved: FMD/Fredy + Applevangelist) and load it after
Moose.lua.

If the vendored Moose.lua is ever upgraded to a build that bundles TARS, drop the vendored
copy to avoid a double definition.

## Load order & why a custom injector (not scriptsWorkOrders)

TARS.lua **defines the class but does not self-instantiate** (the file ends on method
defs; event handlers are registered inside `TARS:New()`). Our `tars_414_init.lua` owns
`TARS:New()` and all config.

`_inject_tars_script()` in `game/missiongenerator/luagenerator.py` mirrors
`_inject_tic_script()`: it is appended **after** `inject_plugins()` in `generate()`, so
`dcsRetribution.plugins.tars.*` already exists when the init runs. (Plugin
`scriptsWorkOrders` inject *before* that plugin's config table, which is why TARS — like
TIC — uses a manual injector and leaves `scriptsWorkOrders` empty.) Trigger order:
base/Moose.lua → … → `TARS.lua` → `tars_414_init.lua`.

## Two TARS defaults that are wrong for a Retribution theater

Both are overridden in `tars_414_init.lua` and are the load-bearing fixes:

1. **`targetNameFilter`** ships `enabled=true` with keywords `USA`/`USSR`. Retribution
   never names units that way, so leaving it on reports nothing. → `enabled=false`.
2. **`allowedAmmo`** is a ground-validation whitelist that excludes AIM-7/AIM-54; the
   shipped F-14 TARPS payload carries `{SHOULDER AIM-7MH}`, so stock TARS would refuse
   the loadout and the F10 film menu would never unlock. The match key is
   `weapon.desc.displayName` (exact DCS strings, unverifiable in-sandbox). Rather than
   guess display names or nerf the payload, when the `enforceLoadout` option is OFF
   (default) we set `setmetatable(TARS.allowedAmmo, {__index=function() return true end})`
   so the whitelist accepts any weapon. With `enforceLoadout` ON, the stock whitelist
   applies plus a best-effort list of F-14 AAM display names.

Other config: `units = {air=false, ground=true, ship=true}`; scoring / score value /
film limit / `recoNameFilter` from plugin options; optional SRS via `mytars:SetSRS()`.

## BDA bridge (the deep integration)

`tars_414_init.lua` overrides `mytars:OnAfterDataProcessing(snap)` (fired per captured
object during the landing debrief). The `Snapshot` schema is documented in TARS.lua:
`snap.name` (DCS unit name — the bridge key), `snap.life` (0–100), `snap.type`,
`snap.coa`. The override appends `{unit, life, type}` to the global
`tars_recon_captures` and sets `dirty_state = true` (both owned by
`resources/plugins/base/dcs_retribution.lua`). The first capture logs the raw snapshot
field names so the schema can be re-confirmed in-game; key reads are defensive
(`name`/`unitName`/`UnitName`).

`dirty_state` matters: `dcs_retribution.lua`'s periodic `write_state()` only writes when
`dirty_state` is set, so without it captures could be lost.

Python side:
- `dcs_retribution.lua` `write_state()` serializes `tars_recon_captures` into state.json.
- `game/debriefing.py` `StateData` gains `tars_recon_captures: List[str]` +
  `parse_tars_captures()` (tolerates Lua `[]`-for-empty, dict entries, or bare strings).
- `game/sim/missionresultsprocessor.py` `tars_reconned_tgos()` resolves each captured
  unit name via `unit_map.theater_units(name).theater_unit.ground_object` and
  `update_confirmed_bda()` calls `sync_confirmed_status()` on those TGOs. It guards
  missing `state_data`/`unit_map` (lightweight test/UI Debriefings) with `getattr`.

This runs **in addition to** the legacy `reconned_tgos_this_turn()` overflight reveal,
so disabling TARS changes nothing.

## Known limitations / in-game validation
- Default ON; still warrants an in-game pass. Confirm: F10 film menu unlocks with the shipped
  F-14 TARPS payload (the `allowedAmmo` fix), overfly a struck enemy TGO, land at a
  friendly base, and verify the BDA map confirms exactly the photographed units.
- `Snapshot` field names are pinned from the first in-game capture log line.
- Markers/scoring are coalition-local; MP distribution of any per-machine state is the
  same open question as other plugins.
- Tests: `tests/test_tars_bda_bridge.py` (parse + reveal). Lua is not runnable in CI.
