# Map Layers and Interface

414Ret reworks the campaign map's layer controls into a single panel, adds new campaign-state
overlays (the status ribbon, the ROE zone layer), paints planning information onto the **DCS F10
map** so it survives into the cockpit, and surfaces more planner reasoning in the dialogs you use
to plan and debrief.

## Unified map layers panel

The two stock map controls — the flat white overlay list at top-right and the separate
top-left threat-zone / navmesh / terrain box — are replaced by **one custom, dark-themed
control** that matches the rest of the app. It owns the visibility of every overlay and adds
grouping, presets, and persistence.

![The unified map layers panel: Default/SEAD/Recon/Clean preset buttons and a Clarity/Firefly/Topographic basemap row across the top, then collapsible groups — Friendly & shared, Air defences, Enemy intel (with the Reveal fog of war overview toggle), Allied & flight plans, Threat zones, Navmesh & terrain — and a Hide all overlays button](https://raw.githubusercontent.com/bradyccox/414Ret/main/docs/wiki/img/map-layers-panel.png)

*The panel: preset views and basemap selector at the top, then the grouped, collapsible layer toggles. The advanced groups (Allied & flight plans, Threat zones, Navmesh & terrain) start collapsed.*

- **Collapsible grouped sections.** Layers are organized into groups — Friendly & shared,
  Air defences, Enemy intel, Allied & flight plans, Threat zones, and Navmesh & terrain. The
  advanced groups start collapsed so the list stays short.
- **Preset views.** One click switches the whole map to **Default**, **SEAD**, **Recon**, or
  **Clean**, plus a "Hide all overlays" button. Use these to jump straight to the set of
  layers a given planning task needs.
- **Persisted choices.** Your group, layer, and base-map selections are saved with the campaign
  (and cached in the browser), and restored between sessions — the map comes back the way you
  left it.
- **Folded-in legacy layers.** The old top-left control's threat zones, navmesh, terrain
  zones, and culling overlays now live inside this one panel.
- **Local chart base maps.** Locally installed tile sets (e.g. a community "accurate DCS
  Caucasus" chart sliced with `tools/tile_geotiff.py` into `Saved Games/Retribution/MapTiles/`)
  appear as extra base-map buttons next to Clarity/Firefly/Topographic — so the campaign map can
  show a chart of the *DCS* terrain instead of mismatching real-world imagery. Purely local
  content; whatever is on disk is what appears.

### ROE zones (restricted & weapons-free)

On a campaign with an authored [ROE layer](Campaign-Phases-and-ROE#the-roe-layer), the Enemy
intel group carries a **zones layer** (default on):

- **Red dashed** shapes — restricted (no-strike) zones: sanctuary circles, Route-Package boxes,
  off-limits corridors. Tooltip: *"RESTRICTED (ROE)"* plus what the zone is and when it eases.
- **Green dashed** shapes — free-fire kill boxes on an inverted-ROE (COIN) campaign. Tooltip:
  *"WEAPONS FREE (ROE)"*.

The same shapes are painted into the generated mission's **F10 map** (below), so the web map and
the cockpit always agree. Locked target classes additionally show a **RESTRICTED — ROE badge**
on their map tooltip instead of vanishing.

### Reveal fog of war

The panel also carries a transient **"Reveal fog of war"** checkbox (in the Enemy intel
group). Ticking it forces every player-facing fog rule to resolve to ground truth, so the
**whole map and the intel dialogs** un-fog at once: full enemy composition, threat rings, and
otherwise-hidden command posts all become visible.

It is a **view toggle only** — it never changes the campaign, and it is **deliberately not
persisted**, so it is always off when you reopen a campaign and a saved game can never carry a
god-view. It is the tool to reach for when you want the real laydown for debugging a campaign,
planning the opposing side, or just checking the truth. See
[Fog-of-War-and-Reconnaissance](Fog-of-War-and-Reconnaissance) for how the fog itself works.

## The campaign-status ribbon

A slim ribbon over the map shows the campaign's live strategic state: **campaign name, turn,
date**, and the current **[campaign phase](Campaign-Phases-and-ROE)** chip ("Interdiction —
enemy IADS 22% · air threat low · front static"). Click the chip to expand the whole phase arc —
every phase's restrictions and releases, the objectives checklist with live ticks, and what
advances the current phase. On a political-will campaign the two **will meters** ride the ribbon
too; hovering shows the labeled movers from the will ledger.

## Right-click actions on the map

- **Enemy supply routes** — right-click an enemy (or contested) supply-route line to frag an
  interdiction package: the package dialog opens at the route's enemy end with **Armed Recon
  pre-selected**, and the flight sweeps the hunted road start-to-end. A fully friendly route
  doesn't offer it. See [Vietnam Ops § Convoy interdiction](Vietnam-Ops#4--convoy-interdiction-steel-tiger).
- **Blank map space** — right-click to place a unit group (cheat-gated); right-click a
  user-placed group to remove it. See [Drop-Spawn Unit Placement](Drop-Spawn-Unit-Placement).
- **Front lines** — right-click to plan CAS packages (stock behaviour, still there).

## What the DCS F10 map shows

Planning information is **painted into every generated mission**, so it survives from the web
map into the cockpit — briefable on the F10 map with no DTC and no screenshots:

- **Front lines** — solid red arrowed lines along every active front.
- **Supply routes** — the convoy road corridors, colored by ownership (blue / red / light-red
  contested). These follow the *actual driveable roads* on campaigns authored to the
  [corridor standard](Custom-Campaigns#supply-routes-follow-the-driveable-corridor), so the
  line on the map is the road the trucks are on.
- **Control points** — a colored capture-radius circle per airbase/FARP (blue/red/gray).
- **ROE zones** — active restricted zones in dashed red, free-fire kill boxes in dashed green,
  named; identical geometry to the web layer.
- **Tanker & AWACS orbits** — every blue tanker and AEW&C racetrack as a **cyan dashed capsule**
  with a label: callsign, type, **radio frequency, and TACAN** (e.g. `Texaco 1-1 KC-135 ·
  251.0 AM TCN 31Y`). The reliable, DTC-free answer to "where's my gas?" — check F10, read the
  freq, go tank. *(New — pending its first in-cockpit eyeball, checklist R1.)*

## UI transparency improvements

Several planning and debriefing dialogs were reworked to show *why* the planner did something,
not just raw numbers:

- **Target Intel panel.** Every ground-object dialog opens with a read-only intel block:
  target type, allegiance, which mission types are valid against it, known live/destroyed unit
  counts, detection and threat range, IADS membership, the hide-on-MFD flag, and
  capturable/purchasable status. (Sites you haven't scouted read "composition unknown" — that
  is the recon fog at work.)

  ![The target intel dialog for an unscouted enemy SAM site, with known units, detection range, and threat range all reading "Unknown (not scouted)"](https://raw.githubusercontent.com/bradyccox/414Ret/main/docs/wiki/img/fog-intel-not-scouted.png)

  *The Target Intel panel on an unscouted site — the counts and ranges read "Unknown (not scouted)" until you scout it. See [Fog-of-War-and-Reconnaissance](Fog-of-War-and-Reconnaissance) for the before/after.*
- **Mission Impact debrief summary.** The debriefing now leads with a Mission Impact block —
  mission end-state, bases captured/lost, runway damage, and loss counts for both sides —
  above the full casualty tables.
- **Package context bar.** The package summary line shows primary task, flight count, player
  slots, the actual time-on-target, and departure bases in one line. On an ROE campaign it also
  carries the **pre-flight ROE warning** when the target is restricted — it prices the choice,
  it never blocks it.
- **Flight-creation context.** Creating a flight shows a live summary of what your selected
  task / aircraft / squadron choice means; squadron hover text lists primary role,
  auto-assignability, spare aircraft, base, and distance to target.

## See also

- [Campaign-Phases-and-ROE](Campaign-Phases-and-ROE) — the ribbon, zones, and will meters
- [Fog-of-War-and-Reconnaissance](Fog-of-War-and-Reconnaissance)
- [The-Retribution-UI](The-Retribution-UI)
- [Custom-Campaigns](Custom-Campaigns) — authoring the supply corridors and zones the map draws
