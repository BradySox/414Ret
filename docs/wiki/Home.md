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
- **[IADS Engines: MANTIS and Skynet](IADS-Engines-MANTIS-and-Skynet)** — the runtime air-defense brain.
- **[Frontline Stances and Movement](Frontline-Stances-and-Movement)** — the ground war.
- **[Base Capture](Base-Capture)** — taking and losing control points.
- **[Squadrons and Pilots](Squadrons-and-Pilots)** — pilots, experience, replacements.
- **[Unit Transfers](Unit-Transfers)** — moving ground forces and logistics.
- **[Fast Forward and Performance](Fast-Forward-and-Performance)** — sim, performance, auto-purchase.

## 414th features

- **[What's Different in the 414th Fork](414th-Fork-Overview)** — the overview.
- **[Fog of War and Reconnaissance](Fog-of-War-and-Reconnaissance)** — recon intel-fog, BDA lag, approximate targeting.
- **[TARPS Reconnaissance](TARPS-Reconnaissance)** — fly the F-14 photo recon; the TARS film engine.
- **[SCAR](SCAR)** — hunt a moving high-value target among decoys.
- **[SOF and Commander Capture](SOF-and-Commander-Capture)** — the finite SOF-team capture/recovery loop.
- **[Combat SAR](Combat-SAR)** — rescue a downed pilot and get them home.
- **[Electronic Warfare and ISR](Electronic-Warfare-and-ISR)** — the C-130J JAMMING platform.
- **[Troops In Contact](Troops-In-Contact)** — the frontline battle simulation.
- **[Map Layers and Interface](Map-Layers-and-Interface)** — the unified layers panel and UI work.
- **[Drop-Spawn Unit Placement](Drop-Spawn-Unit-Placement)** — right-click sandbox placement.
- **[DTC Cartridge Export](DTC-Cartridge-Export)** — native F/A-18C data-cartridge export.

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
