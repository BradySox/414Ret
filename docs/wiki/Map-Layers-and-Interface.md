# Map Layers and Interface

414Ret reworks the campaign map's layer controls into a single panel and surfaces more
planner reasoning in the dialogs you use to plan and debrief. This page covers the **unified
map layers panel**, the **UI transparency improvements**, and **Flight Control ATC**.

## Unified map layers panel

The two stock map controls — the flat white overlay list at top-right and the separate
top-left threat-zone / navmesh / terrain box — are replaced by **one custom, dark-themed
control** that matches the rest of the app. It owns the visibility of every overlay and adds
grouping, presets, and persistence.

- **Collapsible grouped sections.** Layers are organized into groups — Friendly & shared,
  Air defences, Enemy intel, Allied & flight plans, Threat zones, and Navmesh & terrain. The
  advanced groups start collapsed so the list stays short.
- **Preset views.** One click switches the whole map to **Default**, **SEAD**, **Recon**, or
  **Clean**, plus a "Hide all overlays" button. Use these to jump straight to the set of
  layers a given planning task needs.
- **Persisted choices.** Your group, layer, and base-map selections are saved to the browser's
  `localStorage` and restored between sessions — so the map comes back the way you left it.
- **Folded-in legacy layers.** The old top-left control's threat zones, navmesh, terrain
  zones, and culling overlays now live inside this one panel.

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

## UI transparency improvements

Several planning and debriefing dialogs were reworked to show *why* the planner did something,
not just raw numbers:

- **Target Intel panel.** Every ground-object dialog opens with a read-only intel block:
  target type, allegiance, which mission types are valid against it, known live/destroyed unit
  counts, detection and threat range, IADS membership, the hide-on-MFD flag, and
  capturable/purchasable status. (Sites you haven't scouted read "composition unknown" — that
  is the recon fog at work.)
- **Mission Impact debrief summary.** The debriefing now leads with a Mission Impact block —
  mission end-state, bases captured/lost, runway damage, and loss counts for both sides —
  above the full casualty tables.
- **Package context bar.** The package summary line shows primary task, flight count, player
  slots, the actual time-on-target, and departure bases in one line.
- **Flight-creation context.** Creating a flight shows a live summary of what your selected
  task / aircraft / squadron choice means; squadron hover text lists primary role,
  auto-assignability, spare aircraft, base, and distance to target.

## Flight Control ATC

**Flight Control** adds players-only tower comms at friendly land airbases — taxi, takeoff,
and landing sequencing with **SRS voice** and an optional **text-subtitle fallback**. It is a
**plugin, default ON**. Tower comms are aimed at human pilots; AI flow (including QRA and CAP
launches) is left as a pass-through so AI departures are not held up. Only land airdromes get
a tower — FARPs and ships are not eligible.

## See also

- [Fog-of-War-and-Reconnaissance](Fog-of-War-and-Reconnaissance)
- [The-Retribution-UI](The-Retribution-UI)
