# Custom Campaigns

A campaign tells Retribution where the war is fought, who starts with what, and which
side you play. This page explains how campaigns are defined in 414Ret, how to author or
import one, and walks through the fork's **Germany - Red Tide** campaign as a worked
example.

## How a campaign is defined

Every campaign is two files that share a base name, living in `resources/campaigns/`:

| File | Purpose |
|---|---|
| `<name>.yaml` | The descriptor — metadata, recommended factions, economy, IADS mode, supply routes, starting squadrons. |
| `<name>.miz` | A DCS mission file that lays out the **theater**: control points (airbases, carriers, FARPs), objectives (SAM sites, factories, depots, ships), and front-line markers. |

Retribution loads the `.miz` through its `MizCampaignLoader`, reading control points and
objectives directly from the mission rather than the Mission Editor's scripting. You edit
the theater in the **DCS Mission Editor**; you edit metadata and balance in the YAML.

> Note: the upstream **Pretense** generator is **not** shipped in this fork — 414Ret runs
> only the standard YAML-plus-`.miz` campaign path. Don't look for Pretense settings or
> campaign files here.

### Key YAML fields

```yaml
name: Germany - Red Tide
theater: GermanyCW
authors: Starfire, 414th JFG
recommended_player_faction: Blufor Late Cold War (80s)
recommended_enemy_faction: Russia 1980
description: <p>...campaign briefing HTML...</p>
miz: red_tide.miz
recommended_start_date: 1988-07-13
advanced_iads: true
recommended_player_money: 800
recommended_enemy_money: 400
recommended_player_income_multiplier: 1.3
recommended_enemy_income_multiplier: 0.7
version: "10.8"
```

- `theater` names the DCS terrain (e.g. `GermanyCW`, `Caucasus`, `Syria`).
- `recommended_*_faction` must match faction names exactly (see [Custom Factions](Custom-Factions)).
- `recommended_start_date` gates date-restricted units and weapons.
- `advanced_iads: true` turns on networked air defense (see below).
- `recommended_*_money` / `*_income_multiplier` set the starting and per-turn economy per
  side — the lever for making one side the aggressor.
- These are **recommended** defaults; the new-game wizard can override them.

### Supply routes, IADS, and squadrons

- `supply_routes:` defines ground convoy paths and shipping lanes in YAML using DCS map
  `[x, y]` coordinates; each route's endpoints resolve to the nearest control points. This
  replaces baking front-line vehicle groups into the `.miz`.
- `advanced_iads: true` with **range mode** auto-wires each red SAM to nearby comms,
  power, and command-center structures placed in the `.miz`, producing destroyable
  per-base C2 cells. A by-name `iads_config:` block is only possible when the SAMs have
  fixed names.
- A `squadrons:` block (or per-base squadron entries) sets each side's starting air wing.
  A squadron entry can name a bare airframe, or reference a predefined squadron def under
  `resources/squadrons/<type>/<unit>.yaml` to pin a unit name and livery.

## Authoring and importing a campaign

1. Build the theater in the DCS Mission Editor: place airbases/carriers as warehouses,
   add objective groups (SAMs, factories, depots, ships) and front markers, then save the
   `.miz`.
2. Write the matching `<name>.yaml` next to it.
3. Drop both files in `resources/campaigns/` (or your Saved Games override directory) and
   restart Retribution — campaigns are scanned at startup, so changes need a restart.
4. The campaign appears in the new-game wizard, where you can flip the playable side,
   pick factions, and adjust the recommended economy.

The shipped campaign list (Caucasus, Syria, Persian Gulf, Falklands, GermanyCW, and
more) lives in `resources/campaigns/` — read those `.yaml` files as worked examples.

## Worked example: Germany - Red Tide

`red_tide.yaml` + `red_tide.miz` is the 414th's *Red Storm Rising*-flavoured 1988 NATO
counteroffensive on the **GermanyCW** terrain. It is a **fork of Crossing the Rubicon**,
left as a separate selectable campaign so the original is untouched.

What it demonstrates:

- **Economy skew as the offensive lever.** Blue gets more starting money and a higher
  income multiplier (1.3 vs 0.7) so NATO out-produces the culminated Soviet salient — no
  special "aggressor" flag, just the economy fields.
- **Theater edits in the `.miz`.** Hamburg is flipped to red (captured), Copenhagen
  (Kastrup) is added as a red enclave, Fulda is flipped blue as a forward FARP, and a
  carrier air wing is brought ashore — all hand-edits to the warehouse/country blocks.
- **Advanced IADS in range mode.** `advanced_iads: true` with co-located Command Center +
  Comms + power statics per red base, giving Skynet/MANTIS a destroyable C2 layer.
- **YAML supply routes** instead of baked front-line groups, re-anchored on exact control
  point coordinates.
- **Named, liveried squadrons.** Every squadron references a predefined squadron def, so
  real GSFG/VVS regiments fly Soviet liveries on the red side and 414th identities (VMF-29,
  Voodoo, the 414th TFS, JFG Hornets) fly on the blue side — no mismatched paint.

The full build log, including the `.miz` edit points and gotchas, is in
`docs/dev/design/414th-red-tide-campaign-notes.md`.

## See also

- [Custom Factions](Custom-Factions) — who fights and with what units
- [Custom Loadouts](Custom-Loadouts) — per-aircraft default payloads
- [Lua Plugins](Lua-Plugins) — the in-mission scripting layer
- [Turn Zero](Turn-Zero) — what happens when a campaign starts
