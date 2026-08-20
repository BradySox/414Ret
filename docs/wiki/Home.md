# 414Ret Wiki

**414Ret** is the 414th Joint Fighter Group's fork of
[DCS Retribution](https://github.com/dcs-retribution/dcs-retribution), a turn-based dynamic
campaign generator for [DCS World](https://www.digitalcombatsimulator.com/en/products/world/).

You plan air operations turn by turn, generate a `.miz` for each turn, fly or fast-forward it,
and the campaign carries the results forward — losses, captured bases, a moving front line, and
an enemy that reacts. 414Ret adds the 414th's recon, EW, search-and-rescue, frontline,
air-defence and quality-of-life work on top of upstream.

**New here:** [Getting Started](Getting-Started) → [Air Wing Configuration](Air-Wing-Configuration)
→ [Turn Zero](Turn-Zero) → [Your First Operation](Your-First-Operation).
**Know upstream already:** [What's Different in the 414th Fork](414th-Fork-Overview).

---

## Getting started

- [Getting Started](Getting-Started) — what Retribution is, install, first launch.
- [The Retribution UI](The-Retribution-UI) — map, toolbar, panels.
- [Air Wing Configuration](Air-Wing-Configuration) — squadrons and aircraft.
- [Turn Zero](Turn-Zero) — the special first turn.
- [Your First Operation](Your-First-Operation) — plan, generate, fly, debrief.

## Campaign mechanics

- [Mission Planning](Mission-planning) — packages, TOT, task types, the auto-planner.
- [Air Defense and the Air War](Air-Defense-and-the-Air-War) — BARCAP, QRA, SEAD, support orbits, carrier ops.
- [IADS Engine: MANTIS](IADS-Engine-MANTIS) — the runtime air-defence brain.
- [Frontline Stances and Movement](Frontline-Stances-and-Movement) — the ground war.
- [Base Capture](Base-Capture) — taking and losing control points.
- [Squadrons and Pilots](Squadrons-and-Pilots) — pilots, experience, replacements.
- [Unit Transfers](Unit-Transfers) — moving ground forces and logistics.
- [Fast Forward and Performance](Fast-Forward-and-Performance) — sim, performance, auto-purchase.

## 414th features

- [What's Different in the 414th Fork](414th-Fork-Overview) — the overview.
- [Fog of War and Reconnaissance](Fog-of-War-and-Reconnaissance) — intel fog, hidden command posts, approximate targeting.
- [TARPS Reconnaissance](TARPS-Reconnaissance) — player photo recon and the recon engine.
- [Combat SAR](Combat-SAR) — rescuing a downed pilot.
- [Electronic Warfare and ISR](Electronic-Warfare-and-ISR) — the C-130J JAMMING platform.
- [Troops In Contact](Troops-In-Contact) — the frontline battle simulation.
- [Map Layers and Interface](Map-Layers-and-Interface) — the layers panel and UI work.
- [Kneeboards](Kneeboards) — the deck, the SITREP page, threat cards, custom import.

## Vietnam Ops

[Vietnam Ops](Vietnam-Ops) is a suite of opt-in period mechanics. Every toggle defaults off;
the Vietnam campaigns flip the relevant ones on.

- [Arc Light](Vietnam-Ops#1--arc-light) — B-52s walk a bomb carpet across the target.
- [AAA Flak Gauntlet](Vietnam-Ops#2--aaa-flak-gauntlet) — barrage flak that tightens on predictable run-ins.
- [Naval Gunfire Support](Vietnam-Ops#3--naval-gunfire-support) — offshore guns shell coastal targets.
- [Convoy Interdiction](Vietnam-Ops#4--convoy-interdiction-steel-tiger) — hunt real Trail supply columns via Armed Recon.
- [Airbase Harassment](Vietnam-Ops#5--airbase-harassment-rocketmortar-siege) — forward fields under rocket/mortar siege.
- [Super Gaggle](Vietnam-Ops#6--super-gaggle-hilltop-resupply) — escort helos resupplying a cut-off outpost.
- [FAC(A) Marking](Vietnam-Ops#7--faca-willie-pete-target-marking) — an OV-10 marks targets with willie pete.
- [Snake and Nape](Vietnam-Ops#8--snake-and-nape-napalm-cas) — low fast napalm CAS.

[The Vietnam Campaign Layer](Vietnam-Campaign-Layer) does the same at campaign level: ambush
MiGs, Alpha Strikes, era planner ranges and taskings, and a red tempo tied to the campaign clock.

## Campaign briefings

Briefing material grounded in the campaign files — ORBAT, threats and economy read straight from
the campaign and faction data.

**Germany — Red Tide** *(1988 Cold War gone hot)*

- [Campaign Briefing](Red-Tide-Campaign-Briefing) — ORBAT, phase plan, op-night runbook, brief template, package recipes, comms card, threat-defeat reference.
- [Role Cards](Red-Tide-Role-Cards) — print-and-fly kneeboard cards per role.
- [First Three Turns](Red-Tide-First-Three-Turns) — worked example across the opening turns.
- [Intel Assessment](Red-Tide-Intel-Assessment) — in-fiction intel pack and spoken brief.
- [Visual Briefing](Red-Tide-Visual-Briefing) — theatre map, SAM-ring profile, ORBAT diagrams.

**Operation Enduring Resolve** *(Afghanistan 2006, living COIN — requires the Afghanistan map)*

- [Campaign Briefing](Enduring-Resolve-Campaign-Briefing) — the regenerating insurgency and its cache throttle, the ratline, the Disrupt → Clear and Hold arc, the carrier's war.

**Red Flag 81-2** *(Nevada 1981)*

- [Required Mods](Red-Flag-81-2-Required-Mods) — the install list. Read first.
- [Campaign Briefing](Red-Flag-81-2-Campaign-Briefing) — exercise framing, the escalation arc and the Box, ORBAT, package recipes, threat-defeat reference.
- [Role Cards](Red-Flag-81-2-Role-Cards) — kneeboard cards with period 1981 loadouts.
- [First Three Turns](Red-Flag-81-2-First-Three-Turns) — Week One worked example.
- [Intel Assessment](Red-Flag-81-2-Intel-Assessment) — the real-exercise study, threat card, spoken brief.

## Modding

- [Custom Campaigns](Custom-Campaigns)
- [Motorpools](Motorpools) — author strikeable reserve-armor depots (place a Garage A).
- [Custom Factions](Custom-Factions)
- [Layouts](https://github.com/BradySox/414Ret/blob/main/docs/modding/layouts.rst) — the ground-object layout format.
- [Lua Plugins](Lua-Plugins)
- [Custom Loadouts](Custom-Loadouts)
- [Modded aircraft/unit support](Modded-Unit-Support) — the 11-step guide to shipping mod support.

## Servers

- [Dedicated Server Guide](Dedicated-Server-Guide)

## Contributing and development

Upstream's contributing and development guides, adopted 2026-07-20 as the 414th's own standards.
Fork differences are called out in **414th:** notes on each page.

- [Contributing to DCS Retribution](Contributing-to-DCS-Retribution) — where a 414th contribution goes (fork PR → upstream carve).
- [Campaign maintenance](Campaign-maintenance) — the campaign ownership model.
- [Developer's Guide](Developers-Guide) — dev environment, linters, type checks, tests, PR workflow.
- [Adding a new aircraft module](New-aircraft-module-checklist)
- [Adding a new terrain module](New-terrain-module-checklist)
- [Creating shape files in QGIS for map data](Creating-shape-files-in-QGIS-for-map-data)
- [Release process](Release-process) — the rolling `latest` build and pinned `-414th` releases.

---

## Download

Windows releases publish automatically on every push to `main`. No GitHub account needed.

**[Download the latest build](https://github.com/BradySox/414Ret/releases/tag/latest)** → extract →
run `retribution_main.exe` → point it at your DCS install on first launch.

Engineering internals: [`docs/dev/414th-features.md`](https://github.com/BradySox/414Ret/blob/main/docs/dev/414th-features.md).
