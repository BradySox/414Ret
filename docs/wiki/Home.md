# 414Ret Wiki

Welcome to the wiki for **414Ret** — the **414th Joint Fighter Group's fork of
[DCS Retribution](https://github.com/dcs-retribution/dcs-retribution)**, a turn-based
dynamic campaign generator for [DCS World](https://www.digitalcombatsimulator.com/en/products/world/).

Retribution builds and manages a persistent, evolving conflict for DCS: you plan air
operations turn by turn, generate a `.miz` mission for each turn, fly (or fast-forward)
it, and the campaign carries the results forward — losses, captured bases, a moving front
line, and an enemy that reacts. 414Ret keeps everything upstream Retribution does and adds
the 414th's intelligence, reconnaissance, electronic-warfare, search-and-rescue, frontline,
air-defense, and quality-of-life work on top.

> **New here?** Start with **[Getting Started](Getting-Started)**, then read
> **[Air Wing Configuration](Air-Wing-Configuration)**, **[Turn Zero](Turn-Zero)**, and
> **[Your First Operation](Your-First-Operation)**. If you already know upstream Retribution,
> jump to **[What's Different in the 414th Fork](414th-Fork-Overview)**.

This wiki is modeled on the upstream Retribution wiki — same topics, brought up to date and
adapted to how this fork actually plans and flies a campaign.

---

## Getting started

- **[Getting Started](Getting-Started)** — what Retribution is, install, first launch.
- **[The Retribution UI](The-Retribution-UI)** — a tour of the map, toolbar, and panels.
- **[Air Wing Configuration](Air-Wing-Configuration)** — set up your squadrons and aircraft.
- **[Turn Zero](Turn-Zero)** — the special first turn.
- **[Your First Operation](Your-First-Operation)** — plan, generate, fly, and debrief.

## Campaign mechanics

- **[Mission Planning](Mission-planning)** — packages, TOT, task types, the auto-planner.
- **[Campaign Phases and ROE](Campaign-Phases-and-ROE)** — the phase arc every campaign tracks,
  restricted zones and kill boxes, and the political-will economy.
- **[Air Defense and the Air War](Air-Defense-and-the-Air-War)** — BARCAP, QRA, SEAD, support orbits, carrier ops.
- **[IADS Engine: MANTIS](IADS-Engine-MANTIS)** — the runtime air-defense brain.
- **[Frontline Stances and Movement](Frontline-Stances-and-Movement)** — the ground war.
- **[Base Capture](Base-Capture)** — taking and losing control points.
- **[Squadrons and Pilots](Squadrons-and-Pilots)** — pilots, experience, replacements.
- **[Unit Transfers](Unit-Transfers)** — moving ground forces and logistics.
- **[Fast Forward and Performance](Fast-Forward-and-Performance)** — sim, performance, auto-purchase.

## 414th features

- **[What's Different in the 414th Fork](414th-Fork-Overview)** — the overview.
- **[Fog of War and Reconnaissance](Fog-of-War-and-Reconnaissance)** — recon intel-fog, BDA lag, approximate targeting.
- **[TARPS Reconnaissance](TARPS-Reconnaissance)** — fly the F-14 photo recon; the TARS film engine.
- **[SCAR](SCAR)** — the "Sandy" rescue escort for a downed pilot.
- **[Combat SAR](Combat-SAR)** — rescue a downed pilot and get them home.
- **[Electronic Warfare and ISR](Electronic-Warfare-and-ISR)** — the C-130J JAMMING platform.
- **[Troops In Contact](Troops-In-Contact)** — the frontline battle simulation.
- **[Map Layers and Interface](Map-Layers-and-Interface)** — the unified layers panel and UI work.
- **[Kneeboards](Kneeboards)** — the cover page, compact 3–4 page deck, SITREP band, and custom import.
- **[Drop-Spawn Unit Placement](Drop-Spawn-Unit-Placement)** — right-click sandbox placement.

## Vietnam Ops

The **[Vietnam Ops](Vietnam-Ops)** suite is a set of opt-in, period-authentic mechanics that
recreate the missions and threats that defined the Vietnam air war — the things the modern
SAM-and-MiG engine never modelled. Every toggle defaults off; the Vietnam campaigns (1968
Yankee Station, Velvet Thunder, Red Flag 81-2) flip the relevant ones on. See the
**[Vietnam Ops](Vietnam-Ops)** page for the full suite, the settings-page gating model, and
per-feature how-to.

- **[Arc Light](Vietnam-Ops#1--arc-light)** — B-52 heavy bombers walk a carpet of bombs across the target.
- **[AAA Flak Gauntlet](Vietnam-Ops#2--aaa-flak-gauntlet)** — barrage flak that thickens against predictable run-ins.
- **[Naval Gunfire Support](Vietnam-Ops#3--naval-gunfire-support)** — offshore gun ships shell coastal targets (call-for-fire + auto).
- **[Convoy Interdiction](Vietnam-Ops#4--convoy-interdiction-steel-tiger)** — a real Ho Chi Minh Trail supply column you hunt via Armed Recon; kill it and its reinforcements never arrive.
- **[Airbase Harassment](Vietnam-Ops#5--airbase-harassment-rocketmortar-siege)** — forward airfields under sporadic rocket/mortar siege.
- **[Super Gaggle](Vietnam-Ops#6--super-gaggle-hilltop-resupply)** — escort real squadron helos resupplying a cut-off hilltop outpost.
- **[FAC(A) Marking](Vietnam-Ops#7--faca-willie-pete-target-marking)** — an OV-10 Bronco marks targets with willie-pete smoke.
- **[Snake and Nape](Vietnam-Ops#8--snake-and-nape-napalm-cas)** — a low, fast CAS pass over the enemy lays a burning napalm swath.

On top of the mission-level suite, **[The Vietnam Campaign Layer](Vietnam-Campaign-Layer)** makes
the *campaign* play like the era — the political-will economy, the Rolling Thunder → Linebacker II
ROE arc, ambush MiGs, Alpha Strikes, and a red tempo that answers the arc. (The underlying
phase/ROE/will machinery is generic and documented on
**[Campaign Phases and ROE](Campaign-Phases-and-ROE)**.)

## Campaigns

Briefing material for the 414th's campaigns — built to plan and brief an op, grounded in the
campaign files (ORBAT, threats, and economy read straight from the campaign + faction data).

### Germany — Red Tide *(Cold-War-gone-hot, 1988 — Tom Clancy flavour)*

- **[Red Tide — Campaign Briefing](Red-Tide-Campaign-Briefing)** — the brief-builder: friendly/enemy ORBAT, phase plan, op-night runbook, a fill-in mission-brief template, package recipes, comms/code-word card, and threat-defeat reference.
- **[Red Tide — Role Cards](Red-Tide-Role-Cards)** — print-and-fly kneeboard cards for each player role.
- **[Red Tide — First Three Turns](Red-Tide-First-Three-Turns)** — a worked example of the brief template across the opening turns.
- **[Red Tide — Intel Assessment](Red-Tide-Intel-Assessment)** — in-fiction intel pack: backstory, enemy ORBAT, courses of action, threat card, and the read-aloud spoken brief.
- **[Red Tide — Visual Briefing](Red-Tide-Visual-Briefing)** — theater map, SAM-ring profile, and target-priority / ORBAT diagrams.

### Operation Enduring Resolve *(Afghanistan, 2006 — the living counter-insurgency)*

- **[Operation Enduring Resolve (COIN) — Campaign Briefing](Enduring-Resolve-Campaign-Briefing)** —
  the full brief: the regenerating insurgency and its ammo-cache throttle, the ratline, the
  Disrupt → Clear and Hold → Break the Momentum arc, kill-box ROE over the Helmand towns, the
  inverted will economy, the carrier's war, and how to fight it. Requires the DCS Afghanistan map.

### Red Flag 81-2 *(Nevada, 1981 — the exercise played as the war it rehearses)*

- **[Red Flag 81-2 — Required Mods](Red-Flag-81-2-Required-Mods)** — the (short) install list: VWV + the OV-10, plus the era modules. Read this first.
- **[Red Flag 81-2 — Campaign Briefing](Red-Flag-81-2-Campaign-Briefing)** — the brief-builder: the exercise framing, the escalation arc and **the Box**, ORBAT, package recipes, and the emulator-array threat-defeat reference.
- **[Red Flag 81-2 — Role Cards](Red-Flag-81-2-Role-Cards)** — print-and-fly kneeboard cards per player role, with period-1981 loadouts.
- **[Red Flag 81-2 — First Three Turns](Red-Flag-81-2-First-Three-Turns)** — a worked example of Week One: map the array, Iron Hand the corridor, kill the armor.
- **[Red Flag 81-2 — Intel Assessment](Red-Flag-81-2-Intel-Assessment)** — the real-exercise study (Red Baron → Red Flag, the aggressors, Constant Peg at Tonopah, the range array) + threat card + read-aloud brief.

## Modding Retribution

- **[Custom Campaigns](Custom-Campaigns)**
- **[Motorpools](Motorpools)** — author strikeable reserve-armor depots into a campaign (place a Garage A).
- **[Custom Factions](Custom-Factions)**
- **[Layouts](https://github.com/bradyccox/414Ret/blob/main/docs/modding/layouts.rst)** — the ground-object layout format (repo doc).
- **[Lua Plugins](Lua-Plugins)**
- **[Custom Loadouts](Custom-Loadouts)**
- **[Modded aircraft/unit support](Modded-Unit-Support)** — the 11-step guide to shipping support for a DCS mod.

## Servers

- **[Dedicated Server Guide](Dedicated-Server-Guide)**

## Contributing and development

The upstream project's contributing and core development guides, adopted 2026-07-20 as
the 414th's own customs and standards — we do things upstream's way, with fork
differences called out in **414th:** notes on each page.

- **[Contributing to DCS Retribution](Contributing-to-DCS-Retribution)** — ways to contribute, and where a 414th contribution goes (fork PR → upstream carve).
- **[Campaign maintenance](Campaign-maintenance)** — the campaign ownership model, plus the fork's campaign standards.
- **[Developer's Guide](Developers-Guide)** — dev environment, running from sources, linters/type checks/tests, and the PR workflow.
- **[Adding a new aircraft module](New-aircraft-module-checklist)** — the P0–P2 checklist, plus the 414th's extra unit-data requirements.
- **[Adding a new terrain module](New-terrain-module-checklist)** — beacons, theater info, and the landmap.
- **[Creating shape files in QGIS for map data](Creating-shape-files-in-QGIS-for-map-data)** — the GIS landmap workflow.
- **[Release process](Release-process)** — the rolling `latest` build and pinned `-414th` releases.

---

## Download

Pre-built Windows releases publish automatically every time the fork's `main` branch
updates — no GitHub account needed.

**[Download the latest build](https://github.com/bradyccox/414Ret/releases/tag/latest)** →
extract → run `retribution_main.exe` → point it at your DCS World install on first launch.

For engineering internals, see [`docs/dev/414th-features.md`](https://github.com/bradyccox/414Ret/blob/main/docs/dev/414th-features.md) in the repository.
