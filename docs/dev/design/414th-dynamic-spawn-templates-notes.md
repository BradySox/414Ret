# Dynamic spawn templates — §101

Status: **BUILT 2026-09-15**, not flown. From the DM's ask: a pilot who takes a DCS
dynamic slot instead of a pre-fragged package gets a blank jet. Give that jet a package's
waypoints and comm card, even if the fit is not exact. Row `B125` owns the in-game verdict.

## 1. The problem

`dynamic_slots` (`game/settings/settings.py`) turns on the airbase flag and nothing else.
A dynamic-slot jet spawns with DCS's stock loadout, no route, no radio presets and no
aircraft properties. It is also invisible to the campaign: no loss recorded, no §58
briefing card, no §5 grounded steerpoint, no §74 cartridge. This note covers the blank jet
only. The invisibility is a separate and larger job.

## 2. What DCS provides

The mission editor has a **Dyn.SPAWN Template** checkbox on a Player-skill aircraft
group. It writes two keys into the miz:

| Where | Key | Value |
|---|---|---|
| the aircraft group | `dynSpawnTemplate` | `true` |
| the airbase warehouse entry, under `aircrafts.planes.<type>` or `aircrafts.helicopters.<type>` | `linkDynTempl` | the template's `groupId` |

One template per aircraft type per airbase. A dynamic F-16 at a field spawns from whatever
group that field's F-16 entry links to. Sources: the editor's own code
(`MissionEditor/modules/me_aircraft.lua`, `me_manager_resource.lua`, `me_mission.lua`) and the
community [Dynamic Spawn Template Manager](https://github.com/sevenfifty777/DCS-Dynamic-Spawn-Template-Manager),
which rewrites exactly those two keys.

Neither pydcs copy knew either key. The fork pin now carries `FlyingGroup.dyn_spawn_template`
(`BradySox/pydcs` branch `dyn-spawn-template`, one commit on the DTC pin; emitted only when
set, so every other miz serializes byte-identical). The airport's `aircrafts` table is a
plain dict that pydcs writes verbatim, so the link needed no pydcs change.

## 3. What was built

Python only. No plugin, no Lua.

- `game/missiongenerator/dynamicspawntemplates.py` — `DynamicSpawnTemplateGenerator`,
  called at the end of `MissionGenerator.generate_warehouses`, after the air units exist
  and the ship/heliport warehouses are emitted.
- **Donor:** one **client** flight per (departure control point, DCS type id), from both
  coalitions' ATOs. A ground start beats an in-flight start; otherwise ATO order wins.
  AI flights never qualify — the editor clears the flag on a non-player group
  (`me_aircraft.lua:1251`), so an AI template is the untested shape.
- **Mark:** the donor's own group gets `dynSpawnTemplate = true`. No clone: the DM confirmed
  in the editor (2026-09-15) that a template group stays in the slot list, so the fragged
  slot still flies as itself and also seeds the dynamic spawns of its type at that base.
- **Link:** an airfield's link goes on its pydcs `Airport.aircrafts`; a carrier's or
  FARP's goes on every ship/heliport warehouse of that control point (DCS filters the
  hulls it will not spawn from, as the existing warehouse comment says). The entry is the
  editor's own default shape — `initialAmount = 100`, `unlimited = false` (from
  `Config/AirportsEquipment.lua`), plus `linkDynTempl` — with no `wsType` (§4).
- **Gates:** `dynamic_slots` and the new `dynamic_slots_templates` (default on, enabled
  under it). The second exists so a squadron can keep dynamic slots if the link misbehaves
  in DCS; nothing else reads it.
- **Types with no client flight at a base stay blank**, as before.
- Tests: `tests/missiongenerator/test_dynamic_spawn_templates.py` pins both keys reaching
  the miz, the donor choice, the two gates, the helicopter category and the carrier path.

Accepted rough edge: the donor's times on target are frozen at mission start. A jet
spawning forty minutes in inherits stale timings. That matches the DM's bar of
"not 100% right".

Deferred: a synthesized donor (a BARCAP over the field) for types with no client flight
there. It needs a real planned flight through the planner, and the ME's player-only rule
means the synthesized group would have to be a client slot too.

## 4. The check — what the DCS code answers and what only a fly can

Read 2026-09-15 from the install's Lua. The sim side is C++, so two of the three stay open
in-game.

1. **Does the route carry?** **Open.** The slot-select dialog
   (`Scripts/UI/MultiplayerSelectRoleMap/MultiplayerSelectAirdromeDialog.lua`) reads three
   things from the template itself: `payload.pylons` (and `restricted`), `AddPropAircraft`
   and `livery_id`. It then hands the **whole** template (`addProps.unitTemplate`) to
   `DCS.create_client_aircraft`, which is native. Whether route and `Radio` presets are taken
   from it is decided there and is not readable. Loadout, properties and livery carry for
   certain.
2. **Does marking a group as a template hide it from the slot list?** **No** (DM, in the
   editor, 2026-09-15). The build marks the real flight; there is no clone.
3. **Does DCS need `wsType` in the warehouse entry?** **Open, leaning no.** The editor's
   loader (`me_mission.lua` `mergeWarehouses`) matches warehouse entries by **type-name
   key** and fills a missing `wsType` from the unit database, so the editor opens our miz
   cleanly. pydcs has written `aircrafts = {}` for years and DCS honours the airport; the
   entry we add is the editor's default minus `wsType`. If the sim's loader needs the id,
   the fail signature is a dynamic jet that spawns stock at a base where the link is
   present in the file — that is the one B125 records.

Write the in-game answers to 1 and 3 here.
