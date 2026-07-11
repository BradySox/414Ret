# 414th — Air-droppable minefields (convoy interdiction) · §57

**Status:** DESIGN — spec of record, no code yet (authored 2026-07-11).
**Feature §57.** Blue-only v1. Delivered in three cohesive, individually-flyable PRs
(Phase 1 same-turn → Phase 2 persistence → Phase 3 auto-plannable toggle).

> DCS has no native mine object, but the delivery devices exist (cluster dispensers). This
> feature **fakes** area mining: a blue attack aircraft air-drops a designated cluster store,
> and the impact area becomes a **scripted proximity minefield** that detonates against any
> enemy ground unit — a supply convoy — that drives across it. Mines work **the same mission**
> they are laid (mine the road just ahead of an inbound convoy to stop it now), and any field
> left undisturbed at mission end is **tracked in campaign state and re-laid into the next
> turn's mission**. Optionally (a toggle), the AI auto-plans mining strikes ahead of enemy
> convoys.

This note is grounded in a four-seam investigation of the live engine (debrief channel, the
§56 motorpool new-TGO-category playbook, weapon/loadout modelling + Lua weapon detection, and
the planner hook). Every referenced file/function was read, not assumed.

---

## 1. The core insight — almost no Python at runtime

A minefield is a **scripted proximity zone**, not a set of DCS objects: a periodic scan for
enemy ground units inside a radius → `trigger.action.explosion` at the tripping unit. That one
decision collapses most of the complexity:

- **Same-turn mining is pure Lua.** The plugin detects the dispenser's impact, creates a live
  proximity field on the spot, and detonates it against crossing enemy units — all inside the
  running mission. A field laid at T+10 min is killing a convoy at T+20 min the same sortie.
  **No Python round-trip is needed for the tactical effect.**
- **Kills are recorded natively.** The explosion kills *real* convoy units (real
  `coalition.transfers` transfer units). Their deaths fire the DCS events `dcs_retribution.lua`
  already records → the debrief's killed-units list → the convoy-loss path (units that never
  arrive). This is exactly the §35/§50 discipline: **the plugin owns no force-model kills; it
  produces an explosion, and the engine records the consequence.** No phantom spawns.
- **No physical mine objects.** Because detonation feedback is a reported count/charge, we skip
  the heaviest half of the §56 motorpool recipe entirely — **no per-mine statics, no
  `MinefieldGenerator`, no `MinefieldPopulator`, no `UnitMap` bucket, no preset-locations, no
  `campaignloader`/`start_generator`/`migrator` placement.** Minefields are never placed at
  campaign start (the *only* way to lay one is to air-drop it), so all the campaign-start TGO
  machinery is irrelevant.

Persistence across turns is a thin turn-boundary reconciliation: at mission end the plugin
writes back the full state of every field it managed (`{id, x, z, radius, charges}`) through a
named-global channel; Python creates/updates/removes a persisted `Minefield` record and
**re-emits surviving fields into next turn's mission**.

---

## 2. Architecture — four pieces, three of them thin

```
  ┌─────────────────────────────────────────────────────────────────────┐
  │  RUNTIME  (Lua, the heart) — resources/plugins/minefields/           │
  │  • detect designated-CBU impact  → create live proximity field       │
  │  • read persisted fields (Phase 2) → re-arm them                     │
  │  • scan enemy ground in radius → trigger.action.explosion (real kill) │
  │  • F10 friendly marks; charge depletion; startup grace               │
  │  • write back minefields_state global  ── (Phase 2 channel) ──┐       │
  └──────────────────────────────────────────────────────────────┼───────┘
                                                                  │
  ┌───────────────────────────────────────────────────────────────▼──────┐
  │  FORCE MODEL  (Python, turn boundary) — game/fourteenth/minefields.py │
  │  • parse minefields_state (debriefing.py)                            │
  │  • reconcile: new field → create; existing → update charges;         │
  │    exhausted (0 charges) → remove                                    │
  │  • persist as game.minefields  (pickled list, __setstate__ default)  │
  └───────────────────────────────────────────────────────────────┬──────┘
                                                                   │
  ┌────────────────────────────────────────────────┐   ┌───────────▼──────┐
  │  MAP / EMIT  (Python)                           │   │  PLANNER (opt.)  │
  │  • minefieldluadata.py → dcsRetribution.minefields (persisted fields) │
  │  • DrawingsGenerator → F10/ME circles (friendly) │   │ convoy_mining.py │
  │  • GameJs.minefields → client MinefieldsLayer    │   │ frag mine strike │
  │    (friendly-only dashed circles)                │   │ ahead of convoy  │
  └────────────────────────────────────────────────┘   └──────────────────┘
                                                             (Phase 3 toggle)
  ┌─────────────────────────────────────────────────────────────────────┐
  │  WEAPON  — a dedicated "Minefield Dispenser (CBU-99)" store +         │
  │  an "Aerial Minefield" loadout on CBU-99-capable blue attackers  │
  └─────────────────────────────────────────────────────────────────────┘
```

---

## 3. The dispenser (weapon + loadout)

**Decision (user): a dedicated dispenser store, weapon-gated.** Any blue drop of the store lays
mines — no special tasking needed, so an ad-hoc tactical drop just works (load it and go).

Runtime Lua can only identify a weapon by its **DCS type name** (`weapon:getTypeName()` /
`getDesc().typeName`), never the pydcs CLSID (the CLSID is a Python-side store id and is not
retrievable in-mission). So the dispenser must be a store whose type name is **distinctly ours**
and **not used by any normal Retribution loadout** (or every ordinary drop of it would lay
mines).

**Chosen store: CBU-99.** It releases as runtime type `CBU_99` (distinct from Rockeye's
`ROCKEYE`, even though pydcs lumps both in the `Mk-20` group — the Splash Damage explosive
table already keys them separately, `Splash_Damage_3.4.2_414th.lua:704-705`). To make it
*clearly ours* and prevent collateral:

1. **Move** (never copy — a duplicate CLSID trips `Weapon.register`'s `ValueError`,
   `game/data/weapons.py:118`) the CBU-99 CLSIDs (`{CBU_99}`, `{BRU-32 CBU-99}`, `{CBU99_mod6}`,
   the `*CBU99*` racks) **out of** `resources/weapons/bombs/Mk-20.yaml` **into** a new
   `resources/weapons/bombs/Minefield-Dispenser.yaml` group `name: Minefield Dispenser (CBU-99)`
   (`year: 1968`, `fallback: Mk 82`). This gives a clean payload-editor label; runtime detection
   is unchanged (still `getTypeName() == "CBU_99"`).
2. Add a **"Aerial Minefield"** payload preset carrying the dispenser to the
   `customized_payloads/<UNIT>.lua` of every blue attack aircraft whose pydcs pylons accept
   CBU-99 (Hornet, Harrier, A-6, A-7, Tomcat, Su-25 family, …). "Multiple aircraft can" mine;
   each drop = one field; several drops build a bigger contiguous field.

**Consequence to accept (flagged):** CBU-99 is a naval/shipboard store, so mining is available on
**CBU-99-carriage aircraft**, not every land-based striker. This is fine for a blue naval/OEF
flavour and keeps detection clean. If land-only strikers must mine later, the options are a
different distinct-type store or shooter-gating — deferred, out of v1 scope.

**Fly-test confirmation item:** verify the exact `CBU_99` type string in-sim and that no stock
Retribution loadout carries CBU-99 (checklist row, Phase 1).

Detection + impact-tracking is a **verbatim structural clone of the snake-and-nape tracker**
(`resources/plugins/vietnamops/vietnamops-config.lua:1078-1229`): `S_EVENT_SHOT` → match type
name → push `{wpn, pos, vel, shooter, shotTime}` → `timer.scheduleFunction` poll → on
`not wpn:isExist()` resolve the impact with `land.getIP(pos, dir, lookahead)` (fallback
`land.getHeight`). The resolved impact point is the new minefield centre. Gate on
`initiator:getCoalition() == coalition.side.BLUE` (blue-only v1).

---

## 4. The runtime plugin (`resources/plugins/minefields/`)

A normal work-order plugin (no `LuaPlugin` late-init needed — it reads no other plugin's config
at file scope). Loaded after `dcs_retribution.lua` (so the base globals exist; guard them anyway
with `x = x or {}` for load-order safety, per `airecon-config.lua:27`).

**Inputs (read at start):**
- `dcsRetribution.minefields` — persisted fields from prior turns, each
  `{id, x, z, radius, charges, coalition}` (Phase 2; empty in Phase 1). Each becomes a live
  proximity field, re-armed with its remaining charges.
- Plugin options (`descriptionInUI`): field radius, charges-per-drop, trip chance (density),
  explosion power, scan interval, per-unit one-trip, detonation cooldown, startup grace,
  the CBU type-name pattern (configurable like `napeWeaponPatterns`).

**Runtime loop (per scan tick, after the startup grace):**
- For each active field with `charges > 0`, find enemy (RED) **ground** units within `radius`
  (`world.searchObjects(Object.Category.UNIT, sphere, handler)` — the efficient vanilla spatial
  query; filter `getCoalition() == RED` and `getCategoryEx() == Unit.Category.GROUND_UNIT`; skip
  units already in the field's `tripped` set).
- On a trip (`math.random() < tripChance`): `trigger.action.explosion(unit:getPoint(), power)`,
  add the unit to `tripped`, `charges = charges - 1`, set the field's detonation cooldown, and
  advance `minefields_state` for that field. One detonation per field per tick (spacing).
- When `charges <= 0`, the field is exhausted → drop it from the active set.
- Keep one live F10 map mark per active field for the **friendly** coalition
  (`markToCoalition` / `removeMark`, the convoy-ambush/super-gaggle pattern) so the player
  remembers where they mined.

**Detection (per `S_EVENT_SHOT`):** the snake-and-nape tracker above; on impact, create a new
active field at the impact point (`id = 0`, fresh `charges`, coalition = blue) and append it to
`minefields_state`.

**Output (Phase 2, at mission end):** write the **full state** of every field it managed —
persisted fields (with their known `id` and current `charges`) and newly-laid fields (`id = 0`)
— into the `minefields_state` named global, and set `dirty_state = true` (mandatory, or
`write_state` never flushes — `dcs_retribution.lua:166`). A field laid *and* fully consumed the
same mission reports `charges = 0` (or simply isn't re-listed) so it never persists — correct,
it did its job.

The plugin owns **no** kills and invents **no** persistence: explosions kill real units the
engine records, and the reported state is the ground truth Python reconciles. This is the
§35/§37/§49/§50 mover-discipline restated for mines.

Harness coverage from day one (`tests/lua/test_minefields_runtime.py`, modelled on
`tests/lua/test_convoyambush_runtime.py`): detection gate (right type / blue-only), proximity
trip → explosion, one-trip-per-unit, charge depletion to exhaustion, startup grace, F10 mark
lifecycle.

---

## 5. Persistence model (Python)

**Not a TGO.** A minefield is an **area** on a road, not a CP-anchored point installation, and it
spawns nothing — so the natural fit is a **persisted list + a friendly-only overlay**, matching
the prior art for area/zone map objects (restricted zones §40, supply nodes §53, concealment
circles §3) rather than the TGO/`ControlPoint` machinery (which §56 motorpool needs only because
motorpool spawns real units at a CP). This also sidesteps every "unit-less TGO confuses target
selection / IADS" edge case.

**`game/fourteenth/minefields.py`:**

```python
@dataclass
class Minefield:
    id: int              # stable id assigned by Python (monotonic via game.next_*_id or a counter)
    position: Point      # centre
    radius_m: float
    charges: int
    coalition_blue: bool = True   # v1 always True
    laid_turn: int = 0
```

- Stored on `game.minefields: list[Minefield]`, pickled, defaulted to `[]` in `Game.__setstate__`
  (the established getattr/`setdefault` pattern for new game-level state — cf. `game.downed_pilots`,
  `game.coin_state`, `game.will_ledger`, `game.last_sitrep`).
- **The named-global channel (the only new Lua→Python plumbing).** There is no general channel;
  everything is a hardcoded named global listed in both `write_state`'s `game_state` literal and
  `StateData.from_json`. Five edits:
  1. `dcs_retribution.lua` — declare `minefields_state = {}` global (by the other line-13 globals).
  2. `dcs_retribution.lua` — add `["minefields_state"] = minefields_state or {}` to the
     `game_state` literal (`write_state`, ~line 71).
  3. `minefields-config.lua` — the plugin appends to it + sets `dirty_state` (Phase 2 producer).
  4. `game/debriefing.py` — `StateData.minefields_state: list[tuple[...]]`, parsed in `from_json`
     with a defensive helper mirroring `parse_combat_sar_captures` (**guard the empty-table
     gotcha: an empty Lua table serialises as `[]`, not `{}`** — every existing parser defends
     against this).
  5. `game/sim/missionresultsprocessor.py` — a `commit_minefields(debriefing)` step in
     `commit()` (wrapped in `logged_duration`, next to `commit_super_gaggle`), delegating to
     `game/fourteenth/minefields.py`.
- **Reconcile** (`reconcile_minefields(game, debriefing)`):
  - reported `id` known → update that `Minefield.charges`; if `<= 0`, remove it.
  - reported `id == 0` (newly laid) with `charges > 0` → append a new `Minefield` (fresh id,
    `laid_turn = game.turn`).
  - a persisted field **not** reported → left unchanged (conservative: a field nobody drove over
    doesn't decay — "left undisturbed → re-laid next turn").
- **Emit** (`game/missiongenerator/minefieldluadata.py`, `populate_minefields`, wired in
  `luagenerator.py`) → `dcsRetribution.minefields = { {id, x, z, radius, charges, coalition}, … }`
  for the plugin to re-arm. Only blue fields are emitted (friendly).

---

## 6. Map presence & concealment

- **Enemy (red): never sees blue minefields.** They are friendly assets: not emitted in red's
  data, and the client overlay + F10/ME drawings are filtered to the friendly coalition. (Red AI
  pathing cannot be told to avoid them anyway — mines simply attrit whatever drives in. Realistic;
  noted, not a bug.)
- **Friendly (blue): sees them.** Three surfaces:
  - Cockpit F10 — the plugin's live per-field marks (runtime).
  - Generated `.miz` F10/ME map — `DrawingsGenerator.generate_minefields` draws a dashed circle
    (radius) per blue field, friendly-coalition only (the always-on drawings pass, cf.
    `generate_restricted_zones`).
  - Web campaign map — `GameJs.minefields` (`MinefieldJs`, blue-only filtered) →
    `client/src/components/minefields/MinefieldsLayer.tsx`, dashed circles (import the shared
    `mapColors` palette; a friendly/blue token, visually distinct from the amber "suspected
    activity" and red ROE circles). Added to the §19 map-layers panel ("Enemy intel" or a new
    "Friendly ops" group), default ON. Client-only → needs the CI client rebuild.

---

## 7. Auto-planner (Phase 3, the toggle)

**No new `FlightType`** — a mining drop is mechanically a strike at a ground point. Reuse `BAI`
(or `STRIKE`). The hook is the §44 carrier-ops pattern.

`game/fourteenth/convoy_mining.py` `plan_convoy_mining(coalition, now, tracer)`, hooked in
`game/coalition.py` `plan_missions` next to `plan_carrier_strike`:
1. Guards: `coalition.player.is_blue`, `game.settings.auto_plan_minefields`, and an idempotency
   check (one mining package per turn).
2. Pick an enemy convoy from `game.red.transfers.convoys` (prefer one `travelling_to` a hostile
   front, cf. `ObjectiveFinder.convoys()`).
3. Compute a **chokepoint ahead** of it on its road polyline:
   `convoy.origin.convoy_route_to(convoy.destination)` → interpolate a fraction just ahead of the
   convoy's current progress (the routes are oriented rear→front). This is a `count=1` clone of
   `game/fourteenth/convoy_ambush.py:_ambush_points`.
4. Place a lightweight, concealed red **aim-point target** at the chokepoint via
   `game.fourteenth.coin.spawn_red_ground_at(...)` (a cheap 1-unit `map_hidden` TGO — the §50
   route-anchored-TGO mechanism), because the STRIKE/BAI flight-plan builders require a
   `TheaterGroundObject` target and we want the drop *ahead of* the convoy, not on it.
5. Frag the strike with the mining loadout:
   `PackageFulfiller(...).plan_mission(ProposedMission(target, [ProposedFlight(FlightType.BAI, N)],
   asap=False), 0, now, tracer, ignore_range=True)` → `coalition.ato.add_package(package)`.
   Force the "Aerial Minefield" loadout on that flight so it drops the dispenser.
6. The AI drops the dispenser near the aim point → the runtime creates the minefield at the
   impact → **identical path to a player drop.** The aim-point TGO is disposable (cleaned up next
   turn like other transient §50 spawns).

**Phase-3 wrinkle (flagged):** step 4's decoy aim-point is the main complexity — the engine wants
a real target to drop on. Reusing `spawn_red_ground_at` keeps it in a proven groove, but it means
one throwaway concealed red unit per planned field. Acceptable; the alternative (targeting a bare
`MissionTarget` at a coordinate) the builders reject.

`auto_plan_minefields` default **OFF**; preseed **ON** in Red Tide (it has convoys, the ambient-
convoy layer, and the whole battlefield-life suite — the natural home).

---

## 8. Settings, registry, campaign preseed

- `game/settings/settings.py` (both listed in `_LAYOUT_SPEC`, Mission Generation → an
  "Interdiction"/"Battlefield life" section):
  - `air_droppable_minefields: bool` — master gate (the runtime plugin + persistence). Default
    **OFF** (kill-switch/opt-in), preseeded **ON** in Red Tide.
  - `auto_plan_minefields: bool` — the AI auto-plan toggle, `enabled_when="air_droppable_minefields"`,
    default **OFF**, preseeded **ON** in Red Tide.
- **Plugin preseed:** the runtime lives in a Lua plugin, so Red Tide's campaign yaml must also set
  `plugins: {minefields: true}` (the §36 lesson — a saved "plugin unticked" default silently kills
  the setting). Guard in `tests/fourteenth/test_campaign_plugin_preseed.py`.
- **Feature registry** `game/fourteenth/features.py`: append
  `Feature("air_droppable_minefields", "Air-droppable minefields", 57,
  settings_fields=("air_droppable_minefields", "auto_plan_minefields"), plugin_id="minefields")`;
  regenerate with `python -m game.fourteenth.features`. The registry test forces the companion
  edits: add §57 to **CLAUDE.md** "Features at a Glance", a §57 section to
  **docs/dev/414th-features.md**, and the checklist rows below.

---

## 9. Delivery plan — three PRs

### Phase 1 — same-turn mining (the headline, immediately flyable) — ✅ LANDED 2026-07-11

| File | Change |
|---|---|
| `resources/plugins/minefields/minefields-config.lua` + `plugin.json` | NEW — detect drop → proximity field → detonate → F10 marks (defaultValue **false**, opt-in) |
| `resources/plugins/plugins.json` | register `minefields` |
| `resources/customized_payloads/{A-7E,FA-18C_hornet,AV8BNA}.lua` | add "Aerial Minefield" preset; A-7E CAS loadout's CBU-99 → Rockeye (frees CBU-99 for exclusive mining use) |
| `tests/lua/dcs_stubs.lua` + `harness.py` | NEW `WeaponFake` + `fire_shot` (the snake-nape SHOT path had no weapon fake) |
| `tests/lua/test_minefields_runtime.py` | NEW — 6 harness tests |

**As-built deltas from the spec above (deliberate):**
- **Weapon-group split deferred.** The `Minefield-Dispenser.yaml` split was *not* done — runtime
  detection is pure `getTypeName() == "CBU_99"`, so the split only affects the payload-editor
  *label* (marginal) and would churn ~30 CLSIDs. Exclusivity is instead achieved by freeing CBU-99
  from the one stock loadout that used it (A-7E CAS → Rockeye). Revisit only if the editor label
  matters.
- **Loadout named `"Aerial Minefield"`, not `"Retribution Minefield"`.** The `Retribution <X>`
  namespace is guarded (`test_customized_payload_retribution_names_resolve_to_a_task`) to require an
  exact `FlightType.value`; there is no Minefield FlightType (we reuse BAI), so a plain name is
  correct. Phase 3 forces it by literal name.
- **Roster: A-7E + Hornet + Harrier** (verified pydcs-legal per pylon). The **A-6E Intruder cannot
  mount CBU-99** in this pydcs (Heatblur mod store set), despite being the thematic minelayer; the
  **F-14** carries CBU-99 on belly stations but has no ground-attack preset in-fork (TARPS only).
  Super Hornets (single pylon) + Tomcat bombcat are easy later additions.
- **No `§57` registry / CLAUDE.md / features.md / checklist edits** — those land with Phase 2's
  settings (the registry test fails on an unregistered `§N`; `plugins.json` has no reverse check, so
  the plugin is fine unregistered for now).

Deliverable: player loads the dispenser, drops it, the impact area mines, an inbound convoy that
crosses it takes real (recorded) losses **this mission**. No persistence, no auto-plan. Fly to
confirm the `CBU_99` detection + the kill.

### Phase 2 — persistence (carries across turns)

| File | Change |
|---|---|
| `resources/plugins/base/dcs_retribution.lua` | declare `minefields_state` + add to `game_state` |
| `resources/plugins/minefields/minefields-config.lua` | read persisted fields; write `minefields_state` + `dirty_state` |
| `game/fourteenth/minefields.py` | NEW — `Minefield`, `reconcile_minefields` |
| `game/game.py` | `game.minefields` + `__setstate__` default |
| `game/debriefing.py` | parse `minefields_state` (empty-table guard) |
| `game/sim/missionresultsprocessor.py` | `commit_minefields` step |
| `game/missiongenerator/minefieldluadata.py` + `luagenerator.py` | NEW emitter → `dcsRetribution.minefields` |
| `game/missiongenerator/drawingsgenerator.py` | friendly F10/ME circles |
| `game/server/game/models.py` + `client/src/components/minefields/` + map-layers panel | `MinefieldJs` + `MinefieldsLayer` |
| `game/settings/settings.py`, `game/fourteenth/features.py` | `air_droppable_minefields` + §57 registry |
| `tests/fourteenth/test_minefields.py`, `tests/missiongenerator/test_minefieldluadata.py`, `tests/lua/…` | reconcile / emit / parse |

Deliverable: a field left undisturbed is re-laid next turn; it depletes as convoys hit it and
vanishes when exhausted. Needs the CI client rebuild for the overlay.

### Phase 3 — auto-plannable toggle

| File | Change |
|---|---|
| `game/fourteenth/convoy_mining.py` | NEW — `plan_convoy_mining` (chokepoint frag) |
| `game/coalition.py` | hook in `plan_missions` |
| `game/settings/settings.py`, `features.py` | `auto_plan_minefields` (+ §57 fields) |
| `resources/campaigns/red_tide.yaml` | preseed both settings + `plugins:{minefields:true}` |
| `tests/fourteenth/test_convoy_mining.py`, `test_campaign_plugin_preseed.py` | guards + chokepoint + preseed |

Deliverable: with the toggle on, the AI frags a mining strike ahead of an enemy convoy; off =
player-only.

---

## 10. Invariants & discipline (do not violate)

- **Vanilla DCS only** — CBU-99 is a base-game store; `trigger.action.explosion` /
  `world.searchObjects` / `land.getIP` are vanilla; no mods, no MOOSE/MIST dependency.
- **Lua 5.1**, define-before-use, no `os`/`io`; `dirty_state = true` on every producer write;
  guard base globals (`x = x or {}`) for load order; empty tables serialise as `[]` (guard the
  Python parse).
- **No phantom spawns / no invented losses.** Mines spawn nothing; every kill is a real convoy
  unit DCS records; persistence is reconciled from a **reported** state, never fabricated.
- **Blue-only v1** — the detection gate, the emit, and the overlays are all coalition-filtered
  blue; symmetric is a later, additive change.
- **`air_droppable_minefields` OFF is an exact no-op** — the plugin no-ops (no emitted node),
  `game.minefields` stays empty, no reconcile, no overlay; a stock campaign is byte-identical.

---

## 11. Tuning knobs (plugin options + settings)

Field radius (default ~150–250 m), charges per dispenser drop (default ~6), trip chance /
density (default ~0.5), explosion power (default ~90–120; mobility-kills trucks/light armour, an
MBT may shrug one — a heavier field is several drops), scan interval (~3 s), detonation cooldown
(~4 s), startup grace (~120–300 s), CBU type-name pattern.

---

## 12. Decisions resolved / open consequences

- **Resolved (user):** blue-only v1; dedicated weapon-gated dispenser (CBU-99); full design note
  before any code.
- **Consequence:** mining is limited to CBU-99-carriage aircraft (naval/OEF flavour) — accepted.
- **Consequence:** the Phase-3 aim-point uses one throwaway concealed red unit per planned field
  (the engine needs a target to drop on) — accepted, reuses §50.
- **Deferred:** symmetric (red mines blue convoys); land-based-striker dispenser; a "clear the
  minefield" mechanic (DCS has no mine-clearing — fields clear only by exhaustion; an optional
  max-lifespan-in-turns cap can be added if maps accumulate fields).

---

## 13. In-game pass criteria (checklist rows, one per phase)

- **Phase 1:** load the "Aerial Minefield" loadout, drop the dispenser on a road, confirm
  (a) the `CBU_99` drop is detected (F10 mark appears), (b) an enemy convoy crossing the area
  takes losses, (c) the losses show in the debrief as convoy losses. *Fail:* no detection (wrong
  type string / CBU-99 in a stock loadout), or no detonation.
- **Phase 2:** lay a field, end the turn without the convoy reaching it, start the next mission →
  the field is re-laid at the same spot with the same charges; drive a convoy through it over two
  turns → charges deplete and the field disappears when exhausted. *Fail:* field lost across the
  turn, or charges not decrementing, or never disappearing.
- **Phase 3:** with `auto_plan_minefields` on (Red Tide), confirm the AI frags a mining strike
  ahead of a red convoy and the resulting drop lays a field. *Fail:* no package, or the drop
  lands on the convoy instead of ahead of it.

---

## 14. Doc-sync obligations when code lands (per CLAUDE.md order)

1. this note (per phase) → 2. `docs/dev/414th-features.md` §57 → 3. `README.md` (player-visible)
→ 4. `CLAUDE.md` §57 "Features at a Glance" (+ `AGENTS.md` resync via `cp` + line-1 edit)
→ 5. `docs/dev/414th-ingame-pass-checklist.md` rows → 6. `python -m game.fourteenth.features`
(regenerate `414th-feature-index.md`). A push that moves code past its docs is a broken push.
