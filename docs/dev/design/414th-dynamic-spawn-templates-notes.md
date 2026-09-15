# Dynamic spawn templates — scoping note

Status: **scoping only, nothing built.** Written 2026-09-15 from the DM's ask: a pilot who
takes a DCS dynamic slot instead of a pre-fragged package gets a blank jet. Give that jet a
package's waypoints and comm card, even if the fit is not exact. Gated on the check in §4.

## 1. The problem

`dynamic_slots` (`game/settings/settings.py`) turns on the airbase flag and nothing else
(`game/missiongenerator/missiongenerator.py`, `generate_warehouses`). A dynamic-slot jet
spawns with DCS's stock loadout, no route, no radio presets and no aircraft properties. It
is also invisible to the campaign: no loss recorded, no §58 briefing card, no §5 grounded
steerpoint, no §74 cartridge. This note covers the blank jet only. The invisibility is a
separate and larger job.

## 2. What DCS provides

The mission editor has a **Dyn.SPAWN Template** checkbox on a Player-skill aircraft
group. It writes two keys into the miz:

| Where | Key | Value |
|---|---|---|
| the aircraft group | `dynSpawnTemplate` | `true` |
| the airbase warehouse entry, under `aircrafts.planes.<type>` or `aircrafts.helicopters.<type>` | `linkDynTempl` | the template's `groupId` |

One template per aircraft type per airbase. A dynamic F-16 at a field spawns from whatever
group that field's F-16 entry links to. Source: the community
[Dynamic Spawn Template Manager](https://github.com/sevenfifty777/DCS-Dynamic-Spawn-Template-Manager),
which rewrites exactly those two keys (`extract_templates` and the `linkDynTempl` writer in
`DynamicSpawnTemplateManager.py`). The ED forum threads on the feature are not reachable
from the session box, so what the template carries beyond loadout is unverified. See §4.

Neither pydcs copy knows either key. The fork's pin (`BradySox/pydcs` at the SHA in
`requirements.txt`) and upstream `pydcs/dcs` both serialize `dynamicSpawn`,
`allowHotStart` and `dynamicCargo` on the airport and nothing on the group. The airport's
`aircrafts` table is loaded from the terrain data and is empty for every terrain pydcs
ships, so the per-type entry has to be emitted by us.

## 3. The shape, if the check passes

Python only. No plugin, no Lua.

1. **Pick one donor flight per airbase and aircraft type.** Prefer a player-crewed flight
   of that type at that base. If none, synthesize a BARCAP over the field so the jet gets
   the base's comm card and a sane orbit.
2. **Mark the donor's own group** `dynSpawnTemplate`. No clone: the DM confirmed
   2026-09-15 that a template group stays in the slot list, so the pre-fragged slot still
   flies as itself and also seeds the dynamic spawns of its type at that field.
3. **Write the airbase link** into the warehouse entry the generator already emits.
4. **Gate on `dynamic_slots`.** Nothing changes for a game with it off.
5. **pydcs:** a `dyn_spawn_template` field on `FlyingGroup.dict()` and a per-type
   `aircrafts` entry on `Airport.dict()`, on the fork pin.

Accepted rough edge: the donor's times on target are frozen at mission start. A jet
spawning forty minutes in inherits stale timings. That matches the DM's bar of
"not 100% right".

Standing cost: this is another feature nobody can verify without a dynamic spawn on a
server. It needs its checklist row (`B125`) before it lands, not after.

## 4. The check that gates the build

Ten minutes in the mission editor, before any code. Row `B125` on the checklist and item 3
on `docs/dev/flycards/LOCAL.md` carry the procedure.

1. **Does the route carry?** Loadout and radios almost certainly do. If waypoints do not,
   the build shrinks to comms and loadout and the donor choice barely matters.
2. **Does marking a group as a template hide it from the slot list?** **Answered
   2026-09-15 (DM, in the editor): no.** The template group is still slottable. §3 step 2
   marks the real flight and there is no clone.
3. **Does DCS need the `wsType` id in the warehouse entry?** The editor writes a four-int
   `wsType` next to `linkDynTempl`. pydcs carries no such id for aircraft. If DCS matches
   on the key name alone, the entry is cheap. If it needs `wsType`, that is a data table
   to build first.

Questions 1 and 3 are still open. Write their answers here; they decide the rest of §3.
