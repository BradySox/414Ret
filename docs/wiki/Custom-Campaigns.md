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

### Which CJTF block does each object go in?

Every object in the `.miz` is a **marker**: you place a specific unit type, and
`MizCampaignLoader` reads its **position** to create an objective — the actual system that
spawns is filled from the recommended faction's roster. Which **country block** you place
the marker in is part of the convention, and getting it wrong is the single most common
authoring mistake, because a mis-blocked marker is **ignored silently** — no warning, no
error, the objective simply never exists.

This mirrors upstream's *Unit Type Quick Reference*; the **414th:** note below records
where this fork differs.

| Objective | Block | Marker unit |
|---|---|---|
| EWR | **Red** | EWR 1L13 |
| Long range SAM | **Red** | Patriot LN M901 · S-300PS TEL C · S-300PS TEL D |
| Medium range SAM | **Red** | Hawk LN M192 · NASAMS LN AIM-120B/C · SA-2 LN SM-90 · SA-3 5P73 |
| Short range SAM | **Red** | Avenger · Rapier LN · SA-19 Tunguska · SA-9 Strela 1 |
| Ship | **Red** | Arleigh Burke IIa |
| Missile site | **Red** | SSM SS-1C Scud-B |
| Coastal defense | **Red** | AShM SS-N-2 Silkworm |
| Offshore strike target | **Red** | Oil Platform |
| Neutral FOB | **Red** | KrAZ6322 |
| Factory | **Blue** | Workshop A |
| Supply route | **Blue** | M113 (with waypoints) |
| Shipping lane | **Blue** | Bulker Handy Wind (with waypoints) |
| AAA | Either | Flak 18 · Vulcan M163 · ZSU-23-4 Shilka |
| Armor group / garrison | Either | MBT M1A2 Abrams |
| Ammo depot | Either | Ammunition depot |
| Strike target | Either | Tech combine |
| Comms · Power · Command Center | Either | Comms tower M · GeneratorF · Command Center |
| FOB · Invisible FOB | Either — **the block sets the owner** | Truck SKP-11 · Truck M939 Heavy |
| Carrier · LHA · Off-map spawn | Either — **the block sets the owner** | Stennis · Tarawa · F-15C |

For the last two rows the block is not a convention but the **declaration of who starts
owning it** — a CJTF Blue carrier is blue's, a CJTF Red FOB is red's. Everywhere else the
owner comes from proximity to the nearest control point, not from the block.

> **414th:** this fork's `MizCampaignLoader` reads **both** country blocks for **every**
> class, so a mis-blocked marker that upstream ignores **will** generate here. That is a
> deliberate deviation (it also rescues genuinely mis-blocked authored content), but it
> cuts both ways: authoring mistakes become live objectives instead of staying inert.
> Measured against the upstream campaign set, the difference is 483 objects across 12
> campaigns — **443 of them in the two Normandy campaigns alone**, where 336 short-range
> SAM markers sit under CJTF Blue. **Author to the table above anyway**: it keeps a
> campaign portable to upstream, and it keeps "did I mean to place this?" an explicit
> choice rather than an accident.

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
- `control_point_strengths:` (optional) overrides a base's starting strength (`0..1`). The
  front between two bases sits at `strength × route-length` from the blue base, so a weak base
  pulls the front in toward itself — used by **1968 Yankee Station** to start the DMZ siege
  pressed in around a depleted Da Nang (`Sochi-Adler: 0.35`).
- These are **recommended** defaults; the new-game wizard can override them.

### Supply routes, IADS, and squadrons

- `supply_routes:` defines ground convoy paths and shipping lanes in YAML using DCS map
  `[x, y]` coordinates; each route's endpoints resolve to the nearest control points. This
  replaces baking front-line vehicle groups into the `.miz`. **Routes must follow the
  driveable corridor** — see the standard below.
- `advanced_iads: true` with **range mode** auto-wires each red SAM to nearby comms,
  power, and command-center structures placed in the `.miz`, producing destroyable
  per-base C2 cells. A by-name `iads_config:` block is only possible when the SAMs have
  fixed names.
- A `squadrons:` block (or per-base squadron entries) sets each side's starting air wing.
  A squadron entry can name a bare airframe, or reference a predefined squadron def under
  `resources/squadrons/<type>/<unit>.yaml` to pin a unit name and livery.

### Supply routes follow the driveable corridor

**The standard (2026-07-03, applies to every authored route):** a supply route must trace the
corridor you would actually *drive* between its two points — the road, the river valley, the
pass — never a straight line across a ridgeline. The engine binds a route to its control points
by the **first and last waypoint only**, so every intermediate waypoint is free shape: use
enough of them (3–5+) to follow the real corridor. The payoff is visible everywhere the route
is drawn — the map line *is* the road the convoys run.

Two ways to author the intermediates:

- **Real-world-coordinate maps** (Afghanistan, Syria, Nevada, Caucasus…): take the real road
  network's lat/lon junctions and convert them to terrain XY with **`tools/supply_route_geo.py`**
  — it emits a ready-to-paste `supply_routes:` block with exact CP endpoints kept verbatim.
  The shipped reference implementations: `python tools/supply_route_geo.py coin` (Highway 1 /
  Route 611 / the Uruzgan road) and `red_flag_81_2` (US-95 / US-6 / the NTS interior roads).
- **Fictional-overlay campaigns** (Vietnam-on-Caucasus): trace the on-map roads and valleys by
  eye in the Mission Editor / F10 map.

The built campaigns were audited to this standard: Nevada fully re-traced, the worst Caucasus
trail defects fixed, Red Tide already compliant.

### Generated `.miz` files — never hand-edit

Several shipped campaigns' `.miz` files are **generated by a script**, not hand-built:
Red Flag 81-2 (`tools/build_red_flag_81_2_miz.py`) and Operation Enduring Resolve
(`tools/build_coin_enduring_resolve_miz.py`). For those, the laydown tables in the script are
the source of truth — edit the script and re-run it; a hand edit to the `.miz` is lost on the
next build. Hand-authored campaigns (Red Tide, 1968 Yankee Station) still edit the `.miz` directly.

<a name="authoring-the-campaign-layer"></a>
## Removed: phases, ROE zones, and political will

Earlier versions of this fork let a campaign author a `phases:` arc, ROE
restricted/free-fire zones, and a `will:` political-will profile. **All three were removed
on 2026-07-21** along with the war economy they fed, and the settings and YAML keys that
drove them no longer exist.

If you are reading an older campaign YAML or an old design note, treat those blocks as
historical: they are ignored at load, not honoured. Do not re-add them.

| Removed | What replaced it |
|---|---|
| `phases:` and the inferred phase arc | Nothing — campaign shape is expressed through the laydown, supply routes, and squadron availability |
| ROE restricted / free-fire zones | Nothing — the map's ROE overlays went with it |
| `will:` profiles, BLUE Political Will / RED Regime Resolve, the negotiation ending | An authored `victory:` block — explicit win/lose conditions (captured CPs, destroyed targets or categories, territory and strength thresholds, each with an optional `min_turn` guard). Used by Baltic Fury, Red Flag 81-2, Enduring Resolve and 1968 Yankee Station |

## The `settings:` block

The `settings:` block flips feature toggles on for anyone who selects the campaign, so a
campaign ships with the mechanics it was designed around already enabled. Five campaigns
currently preseed parts of the [Vietnam Ops](Vietnam-Ops) suite (1968 Yankee Station,
Velvet Thunder, Red Flag 81-2, and both COIN campaigns), and Enduring Resolve additionally
preseeds the COIN stack (`coin_insurgency`, `coin_reinfiltration`, `coin_ied`, `coin_hvt`,
`coin_dispersed_cells`, …), `high_digit_sams`, and the carrier pair
`long_range_carrier_ops` + `max_mission_range_planes` (widen the range gate so a standoff
carrier's squadrons are assignable at all — see
[Air Defense and the Air War](Air-Defense-and-the-Air-War#long-range-carrier-ops)).

A preseed only sets the **default** for a new campaign — the player can still change any of
it in Settings before starting.

> A setting that a campaign preseeds but the feature's **plugin** is left unticked is a
> silent no-op: the toggle is on and nothing runs. If a campaign depends on a Lua feature,
> preseed the plugin too.

## Authoring and importing a campaign

1. Build the theater in the DCS Mission Editor: place airbases/carriers as warehouses,
   add objective groups (SAMs, factories, depots, ships) and front markers, then save the
   `.miz`.

   **Which country block a marker goes in matters.** Markers under the **Combined Joint
   Task Forces Red** country are the coalition-agnostic default: each binds to the
   *nearest* control point of either side, which is how blue air defenses are usually
   authored (a red-block SAM marker next to a blue field becomes that field's SAM site).
   Watch the placement, though — a marker meant for one side that happens to sit nearest
   the *other* side's control point binds there instead. Markers under **Combined Joint
   Task Forces Blue** are an explicit blue-ownership declaration: they bind to the
   nearest **blue** control point even if an enemy field is closer (before 2026-07-12
   most blue-block marker classes were silently ignored — if an old campaign of yours
   has blue-block ships/SAMs/EWRs that never appeared, they will now).
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
  Comms + power statics per red base, giving MANTIS a destroyable C2 layer.
- **YAML supply routes** instead of baked front-line groups, re-anchored on exact control
  point coordinates.
- **Named, liveried squadrons.** Every squadron references a predefined squadron def, so
  real GSFG/VVS regiments fly Soviet liveries on the red side and 414th identities (VMF-29,
  Voodoo, the 414th TFS, JFG Hornets) fly on the blue side — no mismatched paint.

The full build log, including the `.miz` edit points and gotchas, is in
`docs/dev/design/414th-red-tide-campaign-notes.md`. For the player-facing briefing pack, see the
**[Red Tide — Campaign Briefing](Red-Tide-Campaign-Briefing)** and its companion pages.

## Worked example: 1968 Yankee Station

`1968_Yankee_Station.yaml` + `1968_Yankee_Station.miz` is the 414th's Vietnam campaign on the
**Caucasus** terrain — the whole in-country air war on one map: the coastal route packages, the
Ho Chi Minh Trail interdiction, and the DMZ siege. Where Red Tide is Tom Clancy flavour, this one
is rooted in the real 1968 war. It demonstrates a different toolbox:

- **Siege topology + `control_point_strengths`.** Blue's DMZ front-holder (Da Nang =
  `Sochi-Adler`) starts at `0.35` strength, so the single Sochi↔Gudauta front begins pressed in
  near the wire — the Operation Niagara siege pressure — instead of at the route midpoint.
- **Asymmetric design through factions, not flags.** `USA 1970 Vietnam War` (air-rich) vs
  `Vietnam 1970` (ground-heavy, air-light) — the threat is **AAA**, not MiGs, and there are **no
  MANPADS** (period-correct). Red gets few air squadrons so its economy flows to the ground.
- **OOB tilt through squadron roles** — a couple of `BAI` armed-recon squadrons (Navy A-4E, Da
  Nang A-1H) point the fleet at the Ho Chi Minh Trail convoys, alongside the route-package strikers.
- **Mod-pack toggles in the campaign `settings:` block** — `vietnamwarvessels`,
  `russianmilitaryassetspack` (`[CH]` armor), `ov10a_bronco`, `a4_skyhawk`, etc.
- **Carrier-capable airframes only on carriers** — A-4E/A-6/F-8E/E-2C/RA-5C, not the land-based
  DCS F-4 (a real gotcha; see [Squadrons and Pilots](Squadrons-and-Pilots)).
- **The whole Vietnam Ops suite** — Arc Light, flak, naval gunfire, convoy interdiction,
  airbase harassment, Super Gaggle — pre-seeded in the `settings:` block, plus a
  `red_tempo:` schedule so Hanoi answers the campaign clock. (It also carried the
  political-will economy and a Rolling Thunder → Linebacker II ROE arc; both were removed
  on 2026-07-21 — see [Removed](#removed-phases-roe-zones-and-political-will) above.)

Design log: `docs/dev/design/414th-vietnam-retribution-notes.md` (framing) +
`docs/dev/design/414th-vietnam-ops-notes.md` (the mechanics). See also
**[The Vietnam Campaign Layer](Vietnam-Campaign-Layer)** and **[Vietnam Ops](Vietnam-Ops)**.

## Worked example: Operation Enduring Resolve (COIN)

`coin_enduring_resolve.yaml` + `coin_enduring_resolve.miz` (Afghanistan terrain) is the richest
demonstration of the **campaign-layer authoring surface** — nearly every block this page
describes, used in anger:

- **A generated `.miz`** (`tools/build_coin_enduring_resolve_miz.py`) — the stronghold/cache
  laydown lives in the script's tables, never in hand edits.
- **A `red_tempo:` schedule** — turn-windows that surge the insurgent ratline and raise red's
  ground stance, so the campaign's pressure changes over its run.
- **Corridor-standard `supply_routes`** authored from real road lat/lons via
  `tools/supply_route_geo.py` (Highway 1, Route 611, the Uruzgan road).
- **`settings:` preseeds** for the whole COIN stack plus the carrier pair
  (`long_range_carrier_ops` + `max_mission_range_planes: 600`).

Player-facing briefing: **[Operation Enduring Resolve (COIN)](Enduring-Resolve-Campaign-Briefing)**.
Design logs: `docs/dev/design/414th-coin-*.md`.

## See also

- ~~Campaign Phases and ROE~~ — the feature was removed on 2026-07-21; that page is retained
  only as a record of how it worked
- [Custom Factions](Custom-Factions) — who fights and with what units
- [Custom Loadouts](Custom-Loadouts) — per-aircraft default payloads
- [Lua Plugins](Lua-Plugins) — the in-mission scripting layer
- [Turn Zero](Turn-Zero) — what happens when a campaign starts
