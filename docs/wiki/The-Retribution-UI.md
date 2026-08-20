# The Retribution UI

Where to click. Retribution is a desktop app that runs outside DCS: a live theater **map** in the
centre, planning controls around it, and dialogs for inspecting the enemy, building packages and
reading the debrief. Most planning starts by clicking something on the map.

New here? Read [Getting Started](Getting-Started) first.

![The 414Ret main window: the campaign control strip across the top, the ATO/packages and flights panels down the left, the live theater map in the center, the unified map layers panel at right, and the info panel along the bottom](https://raw.githubusercontent.com/BradySox/414Ret/main/docs/wiki/img/ui-overview.jpg)

*Turn planning: top control strip, ATO and flights columns on the left, the map (a clicked SAM
site's intel popup showing), and the layers panel on the right.*

---

## The map

Shows the theater, both sides' bases, the front line, known ground objects and air defences, and
planned flight routes.

- **Click a base, ground target or front-line sector** to select it — usually the first step in
  fragging a package.
- **Click an air-defence site or known ground object** to open its intel dialog.
- **Right-click an enemy supply route** to frag an interdiction package: the dialog opens at the
  route's enemy end with **Armed Recon** pre-selected.
- **Right-click a front line** to plan CAS.

Short-range mobile defences are kept off player datalinks; SEAD-sized sites stay visible.

### The campaign-status ribbon

A slim ribbon over the map carries the campaign name, turn and date, the **LAST TURN** SITREP
digest, and — on a campaign authoring a `victory:` block — a green **VICTORY** chip that expands
into the live win/lose checklist.

---

## The toolbar

- **Save / load / New Game.**
- **Settings** — organised into focused pages (Difficulty & Realism · Air Doctrine · Campaign
  Management · Mission Generation · Kneeboards · Performance · Vietnam Ops) with one-click
  difficulty presets (Casual / Normal / Veteran / Ace).
- **Generate the mission / take off.**
- **Advance the turn / fast-forward.**
- **Air Wing** and the finance/intel summaries.

---

## The ATO and packages panel

The **Air Tasking Order** lists every package planned for the turn, and each package its flights.

- A **package** groups flights with a shared objective and timing — a strike with its escort and
  SEAD.
- Selecting a package or flight shows task, time-on-target, player slots, departure base, squadron
  fit, available aircraft and target distance.
- Add flights, set tasks (including the fork's **JAMMING**, **TARPS** and **CSAR**), choose
  loadouts, edit waypoints and altitudes.

Full workflow: [Mission Planning](Mission-planning).

---

## The map layers panel

Upstream splits map display across two stock Leaflet controls. The fork replaces both with one
dark-themed grouped panel.

![The unified map layers panel: Default/SEAD/Recon/Clean preset buttons and a Clarity/Firefly/Topographic basemap row across the top, then collapsible groups — Friendly & shared, Air defences, Enemy intel (with the Reveal fog of war overview toggle), Allied & flight plans, Threat zones, Navmesh & terrain — and a Hide all overlays button](https://raw.githubusercontent.com/BradySox/414Ret/main/docs/wiki/img/map-layers-panel.png)

- **Grouped, collapsible sections** — Friendly & shared, Air defences, Enemy intel, Allied & flight
  plans, Threat zones, Navmesh & terrain. Advanced groups start collapsed.
- **Preset views** — **Default**, **SEAD**, **Recon**, **Clean**, plus "Hide all overlays".
- **Choices persist** with the campaign and are restored between sessions.
- **Local chart base maps** — tile sets in `Saved Games/Retribution/MapTiles/` appear as extra
  base-map buttons beside Clarity/Firefly/Topographic, so the map can show a chart of the *DCS*
  terrain instead of mismatched real-world imagery. Sliced with `tools/tile_geotiff.py`.

### Reveal fog of war

A transient checkbox in the Enemy intel group. It forces every player-facing fog rule to ground
truth, so the map and the intel dialogs un-fog together — full enemy composition, threat rings, and
otherwise-hidden command posts.

**View toggle only.** It never changes the campaign and is deliberately never persisted, so a saved
game can never carry a god-view. See
[Fog of War and Reconnaissance](Fog-of-War-and-Reconnaissance).

---

## What the DCS F10 map shows

Planning information is painted into every generated mission, so it survives into the cockpit with
no DTC and no screenshots:

- **Front lines** — solid red arrowed lines.
- **Supply routes** — convoy corridors coloured by ownership. On campaigns authored to the
  [corridor standard](Custom-Campaigns#supply-routes-follow-the-driveable-corridor) these follow
  the real driveable roads.
- **Control points** — a coloured capture-radius circle per airbase and FARP.
- **Tanker and AWACS orbits** — each racetrack as a cyan dashed capsule labelled with callsign,
  type, frequency and TACAN (`Texaco 1-1 KC-135 · 251.0 AM TCN 31Y`). *(Pending its first
  in-cockpit check, checklist R1.)*

---

## Intel and planning dialogs

Clicking a ground object opens its **intel dialog**: known strength, valid mission types, weapon
and detection ranges, IADS membership, the hide-on-MFD flag, and capture/purchase state.

**Intelligence is deliberately incomplete.** A site can be known to exist while its composition,
strength, damage and threat rings read `Unknown (not engaged)`. Engage it — ordnance on it, or any
ground-attack sortie that reaches it — and you know all of it permanently, damage included. There
is no separate confirmation pass.

Three other dialogs surface planner reasoning rather than raw numbers:

- **Package context bar** — primary task, flight count, player slots, actual TOT and departure
  bases on one line.
- **Flight creation** — a live summary of what the selected task, aircraft and squadron mean;
  squadron hover text gives primary role, auto-assignability, spare aircraft, base and distance to
  target.
- **Debrief** — leads with **Mission Impact**: end-state, bases captured and lost, runway damage
  and loss counts, above the full casualty tables.

![The debrief's Casualty report, leading with a Mission Impact block — mission status, bases lost/captured, runway damage — above the per-side loss lists for both coalitions](https://raw.githubusercontent.com/BradySox/414Ret/main/docs/wiki/img/debrief-mission-impact.png)

---

## See also

- [Mission Planning](Mission-planning)
- [Fog of War and Reconnaissance](Fog-of-War-and-Reconnaissance)
- [414th Fork Overview](414th-Fork-Overview)
