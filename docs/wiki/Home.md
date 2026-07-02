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
- **[Air Defense and the Air War](Air-Defense-and-the-Air-War)** — BARCAP, QRA, SEAD, support orbits.
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
SAM-and-MiG engine never modelled. Every toggle defaults off; the Vietnam campaigns (Khe Sanh,
Yankee Station, Velvet Thunder, Steel Tiger) flip the relevant ones on. See the
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
the *campaign* play like the era: a **political-will economy** decided at the negotiating table
(break Hanoi's resolve before Washington's patience runs out), a **static siege-line front**, the
authored **Rolling Thunder → Linebacker II ROE arc** (sanctuary zones, target release, escalation
coupled to your bleeding will), **GCI-ambush MiGs** flying Hanoi's actual air-defense doctrine,
massed escorted **Alpha Strikes**, and a red side whose **tempo answers the arc** — the trail
surges during bombing halts and the Easter Offensive lands when Linebacker opens.

## Campaigns

Briefing material for the 414th's campaigns — built to plan and brief an op, grounded in the
campaign files (ORBAT, threats, and economy read straight from the campaign + faction data).

### Germany — Red Tide *(Cold-War-gone-hot, 1988 — Tom Clancy flavour)*

- **[Red Tide — Campaign Briefing](Red-Tide-Campaign-Briefing)** — the brief-builder: friendly/enemy ORBAT, phase plan, op-night runbook, a fill-in mission-brief template, package recipes, comms/code-word card, and threat-defeat reference.
- **[Red Tide — Role Cards](Red-Tide-Role-Cards)** — print-and-fly kneeboard cards for each player role.
- **[Red Tide — First Three Turns](Red-Tide-First-Three-Turns)** — a worked example of the brief template across the opening turns.
- **[Red Tide — Intel Assessment](Red-Tide-Intel-Assessment)** — in-fiction intel pack: backstory, enemy ORBAT, courses of action, threat card, and the read-aloud spoken brief.
- **[Red Tide — Visual Briefing](Red-Tide-Visual-Briefing)** — theater map, SAM-ring profile, and target-priority / ORBAT diagrams.

### Khe Sanh: Operation Niagara *(historical, 1968 — rooted in the real siege)*

- **[Khe Sanh — Required Mods](Khe-Sanh-Required-Mods)** — the squadron install list: every required mod/module, what it adds, whether it's free, and where to download it. Read this first.
- **[Khe Sanh — Campaign Briefing](Khe-Sanh-Campaign-Briefing)** — the brief-builder: friendly/enemy ORBAT, the siege win-geometry, phase plan, op-night runbook, mission-brief template, package recipes, comms/FAC card, and the AAA threat-defeat reference.
- **[Khe Sanh — Role Cards](Khe-Sanh-Role-Cards)** — print-and-fly kneeboard cards per player role, with period-1968 loadouts.
- **[Khe Sanh — First Three Turns](Khe-Sanh-First-Three-Turns)** — a worked example of the brief template across the opening turns.
- **[Khe Sanh — Intel Assessment](Khe-Sanh-Intel-Assessment)** — the historical intelligence pack (real OOB, commanders, Niagara/Pegasus) + threat card + read-aloud brief.
- **[Khe Sanh — Visual Briefing](Khe-Sanh-Visual-Briefing)** — the siege map, AAA threat profile, and target-priority / ORBAT diagrams.

## Customization and modding

- **[Custom Campaigns](Custom-Campaigns)**
- **[Custom Factions](Custom-Factions)**
- **[Custom Loadouts](Custom-Loadouts)**
- **[Lua Plugins](Lua-Plugins)**

## Servers

- **[Dedicated Server Guide](Dedicated-Server-Guide)**

---

## Download

Pre-built Windows releases publish automatically every time the fork's `main` branch
updates — no GitHub account needed.

**[Download the latest build](https://github.com/bradyccox/414Ret/releases/tag/latest)** →
extract → run `retribution_main.exe` → point it at your DCS World install on first launch.

For engineering internals, see [`docs/dev/414th-features.md`](https://github.com/bradyccox/414Ret/blob/main/docs/dev/414th-features.md) in the repository.
