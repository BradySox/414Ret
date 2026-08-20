# 414Ret Wiki

**[Download the latest build](https://github.com/BradySox/414Ret/releases/tag/latest)** → extract →
run `retribution_main.exe` → point it at your DCS install on first launch. Windows releases publish
automatically on every push to `main`; no GitHub account needed.

**414Ret** is the 414th Joint Fighter Group's fork of
[DCS Retribution](https://github.com/dcs-retribution/dcs-retribution), a turn-based dynamic
campaign generator for [DCS World](https://www.digitalcombatsimulator.com/en/products/world/).

You plan air operations turn by turn, generate a `.miz` for each turn, fly or fast-forward it, and
the campaign carries the results forward — losses, captured bases, a moving front line, and an
enemy that reacts. The fork adds the 414th's recon, EW, search-and-rescue, frontline, air-defence
and quality-of-life work on top of upstream.

**New here:** [Getting Started](Getting-Started).
**Know upstream already:** [What's Different in the 414th Fork](414th-Fork-Overview).

---

## Playing

- [Getting Started](Getting-Started) — install, the New Game wizard, Turn Zero, your first turn.
- [The Retribution UI](The-Retribution-UI) — map, toolbar, ATO, layers panel, dialogs.
- [Mission Planning](Mission-planning) — packages, TOT, task types, the auto-planner.
- [Squadrons and Pilots](Squadrons-and-Pilots) — building the air wing, buying, pilots, liveries.
- [The Ground War](The-Ground-War) — stances, how the front moves, base capture, unit transfers.
- [Kneeboards](Kneeboards) — the deck, the SITREP page, threat cards, custom import.
- [Fast Forward and Performance](Fast-Forward-and-Performance) — sim, performance, auto-purchase.

## The air war

- [Air Defense and the Air War](Air-Defense-and-the-Air-War) — BARCAP, QRA, SEAD, support orbits,
  carrier ops.
- [IADS Engine: MANTIS](IADS-Engine-MANTIS) — the runtime air-defence brain.
- [Fog of War and Reconnaissance](Fog-of-War-and-Reconnaissance) — intel fog, hidden command posts,
  TARPS, approximate targeting.
- [Electronic Warfare and ISR](Electronic-Warfare-and-ISR) — the C-130J JAMMING platform.
- [Combat SAR](Combat-SAR) — rescuing a downed pilot.
- [Troops In Contact](Troops-In-Contact) — the frontline battle simulation.
- [Vietnam Ops](Vietnam-Ops) — opt-in period mechanics and the Vietnam campaign doctrine.

## What the fork changes

- [What's Different in the 414th Fork](414th-Fork-Overview) — the overview.

## Modding

- [Custom Campaigns](Custom-Campaigns)
- [Motorpools](Motorpools) — author strikeable reserve-armor depots.
- [Custom Factions](Custom-Factions)
- [Custom Loadouts](Custom-Loadouts)
- [Lua Plugins](Lua-Plugins)
- [Modded aircraft/unit support](Modded-Unit-Support) — the 11-step guide.
- [Layouts](https://github.com/BradySox/414Ret/blob/main/docs/modding/layouts.rst) — the
  ground-object layout format.

## Servers

- [Dedicated Server Guide](Dedicated-Server-Guide)

## Contributing

Upstream's contributing and development guides, adopted 2026-07-20 as the 414th's own standards.
Fork differences are called out in **414th:** notes on each page.

- [Contributing and releases](Contributing-to-DCS-Retribution) — where a contribution goes, and how
  builds ship.
- [Developer's Guide](Developers-Guide) — dev environment, linters, type checks, tests, PRs.
- [Campaign maintenance](Campaign-maintenance) — the campaign ownership model.
- [Module checklists](Module-Checklists) — adding a new aircraft or terrain module.
- [Creating shape files in QGIS](Creating-shape-files-in-QGIS-for-map-data) — map data.

---

Engineering internals:
[`docs/dev/414th-features.md`](https://github.com/BradySox/414Ret/blob/main/docs/dev/414th-features.md).
