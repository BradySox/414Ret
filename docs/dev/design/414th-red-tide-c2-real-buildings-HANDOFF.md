# Red Tide — replace placed IADS C2 statics with real buildings — HANDOFF

**Status:** investigation done, no code written yet. Handed off 2026-06-24.
**Goal (user request):** the advanced-IADS command/comms/power nodes at red airfields
are hand-placed `.miz` statics that landed **on airfield aprons** — they block aircraft
spawns and look bad (seen at Haina). Replace them with **real existing map buildings**
registered as IADS targets (so they're destroyable C2 that Skynet still wires), and
**remove the placed statics**.

This is the IADS-C2 application of the scenery-import pipeline
([`414th-scenery-import-notes.md`](414th-scenery-import-notes.md)). It is NOT the same as
the shipped scenery **strike** targets (factories/power/ware) — those never touched the C2
nodes, which is why the statics are still there.

---

## The 12 placed C2 statics (red_tide.miz)

Per-field statics, with DCS world coords (`.miz` `["x"]`, `["y"]`; note `y` = world **Z**):

| Field | Command Center (`.Command Center`) | Comms (`Comms tower M`) | Power (`GeneratorF`) |
|---|---|---|---|
| Kastrup/Copenhagen | x132865.1 y-489500.6 | x134902.1 y-490781.4 | x134957.2 y-488663.1 |
| Hamburg | x-63413.3 y-690454.7 | x-63567.4 y-691579.4 | x-62386.4 y-690362.9 |
| **Haina** | x-359296.9 y-702956.9 | x-360120.8 y-700996.8 | — |
| Peenemünde | x-36875.5 y-435876.8 | x-35552.6 y-437008.0 | x-35644.0 y-435421.9 |
| Templin | — | x-162087.7 y-467432.8 | — |

(Statics are named `<Field> Command Center` / `<Field> Comms` / `<Field> Power`, e.g.
`Haina Command Center`, shape `ComCenter`, category `Fortifications`.)

---

## Feasibility — DECISIVE: scanner dump only covers 2 of 5 fields

Queried `~/Saved Games/DCS/Logs/cwg_scenery_dump.csv` (216,626 rows) for real buildings
within 4 km of each field's C2 coords:

| Field | Real buildings available? | Detail |
|---|---|---|
| **Haina** | ✅ full cell | `commandcenter` **KDP_USSR @261 m**, `comms` RSP-10MA radar @658 m, `power` TRANSFORMER_BOOTH_USSR @728 m (also factory @808 m, fuel @615 m) |
| **Templin** | ✅ workable, further | `commandcenter` BARRACK_SMALL @2571 m, `comms` NDB_RADIO @2599 m, `power` TRANSFORMER @1274 m |
| Kastrup | ❌ no data | nearest scanned object **261 km** away |
| Hamburg | ❌ no data | **165 km** away |
| Peenemünde | ❌ no data | **118 km** away |

**Dump coverage bbox:** `x[-409611 .. -125991]  z[-775394 .. -457279]` — i.e. the central
front only. Kastrup/Hamburg/Peenemünde are far outside it and need a **re-scan** before they
can get real buildings (fly the CWG scenery scanner over those areas in-game, re-export the
dump). The scanner loader lives at `Saved Games\DCS\Scripts\cwg_scenery_scanner.lua` (see the
`cwg-scenery-scanner` memory; the desanitize step is the user's).

---

## How the pipeline turns a real building into a destroyable IADS C2 node

1. Trigger zones in the `.miz`: a **blue definition zone** (first property = category, e.g.
   `commandcenter` / `comms` / `power`) + **white target zones** over each real building.
2. `SceneryGroup.from_trigger_zones()` (`game/scenery_group.py`) aggregates them; the category
   must be in `NAME_BY_CATEGORY`.
3. `StartGenerator.generate_tgo_for_scenery()` (`game/theater/start_generator.py:555`):
   `IadsRole.for_category(category)` → if `iads_role.participate`, the TGO is an
   **`IadsBuildingGroundObject`** (else plain `BuildingGroundObject`). Category→task map
   (`group_task_for_scenery_group_category`): `commandcenter`→`COMMAND_CENTER`,
   `comms`→`COMMS`, `power`→`POWER` — all three participate in IADS.
4. At mission-gen, `TgoGenerator.add_trigger_zone_for_scenery()` lays a tiny ~16 ft kill zone
   over the object; DCS resolves destruction **by proximity** (`MapObjectIsDead` /
   `SceneryDestructionZone`). **The DCS map-object ID is irrelevant** — position is what matters.
5. The TGO anchors to the **nearest control point**, so Haina's real-building C2 must sit
   closest to Haina (161) to associate with it. Skynet (advanced IADS, range mode) then wires
   the base's SAMs to the comms (<15 nm) / power (<35 nm) / command-center nodes — the real
   buildings at Haina are sub-1 km, well inside range.

---

## Tooling (already exists)

- **Dump:** `~/Saved Games/DCS/Logs/cwg_scenery_dump.csv` — header `id,type,life0,x,z,y,lat,lon,mgrs`.
  Convention: dump `x` = world X, dump `z` = world Z; in a `.miz` zone, `["x"]`=dump.x, `["y"]`=dump.z.
- **Emitter (build-time, gitignored):** `_scenerytools/cwg_scenery_emitter.py`.
  `--inject` is **implemented**: clusters dump buildings, writes blue/white zones into an
  `OUT_MIZ` copy, and `remove_covered_statics()` deletes generic statics covered by a real
  cluster (asserts brace balance after). BUT its `select()` picks a **generic strike laydown**
  (factory/power/ware/comms, map-wide, MIN_SEP 4 km) — it does **not** target C2 near specific
  airfields, and `commandcenter` is not in its `TARGET`. So it needs either a new "C2-per-base"
  mode or hand-authored zones for just Haina+Templin.
- **Shared core:** `game/campaignloader/scenerycatalog.py` (`categorize`, `cluster`); has
  `commandcenter`/`comms`/`power` categories + `CATEGORY_PATTERNS`.

---

## Recommended plan

**Phase 1 (now, no re-scan):** Haina + Templin real-building C2.
- Haina is the demonstrated bad case and the best case (real `KDP_USSR` command post @261 m).
- Cleanest: a **surgical `.miz` edit** — add the blue+white trigger zones over the real
  buildings (Haina: KDP_USSR=commandcenter, RSP-10MA=comms, transformer=power; Templin: the
  three from the table) and **remove** the matching placed statics (Haina CC+Comms,
  Templin Comms). Avoids a full emitter regen of the whole campaign.
- Verify each new IADS TGO anchors to the right CP (Haina 161 / Templin 15).

**Phase 2 (needs user re-scan):** Kastrup, Hamburg, Peenemünde.
- User flies the CWG scenery scanner over those 3 regions → re-export dump → repeat Phase 1
  there. Until then, those statics remain (or relocate/remove as an interim — user's call;
  the user chose "real buildings" as the end-state).

---

## Gotchas

- **pydcs save is BROKEN in this checkout** (per `red-tide-economy-iads` memory) — `.miz`
  edits are **hand-edited Lua + zipfile**, not pydcs. Verify `{`/`}` brace balance after every
  edit (the emitter asserts this; do the same by hand).
- The `.miz` embeds plugin Lua at generation; unrelated to zones, but remember a regenerated
  campaign is needed to pick up any plugin change.
- **Needs an in-game pass:** confirm (a) the kill zones actually sit on the real scenery
  objects, (b) the statics are gone (apron clear, spawns unblocked), (c) Skynet still wires the
  base SAMs to the new real-building C2 (destroying them degrades the IADS).
- Don't confuse with the shipped scenery **strike** targets — different category set, different
  purpose.

---

## Quick repro of the feasibility query

```python
import csv, math, sys
sys.path.insert(0, "game/campaignloader")
from scenerycatalog import categorize
DUMP = r"C:\Users\brady\Saved Games\DCS\Logs\cwg_scenery_dump.csv"
fields = {"Haina": (-359296, -702956), "Templin": (-162087, -467432)}  # add the others post-rescan
rows = [(float(r["x"]), float(r["z"]), r["type"]) for r in csv.DictReader(open(DUMP, newline=""))]
for name, (fx, fz) in fields.items():
    for x, z, t in rows:
        if math.hypot(x - fx, z - fz) <= 4000:
            print(name, categorize(t), round(math.hypot(x - fx, z - fz)), t)
```
