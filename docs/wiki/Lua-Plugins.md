# Lua Plugins

Retribution plans and spawns a mission in Python, but the **runtime behavior** inside the
generated `.miz` — electronic warfare, recon scoring, frontline firefights, combat-SAR
rescues — is driven by **Lua plugins** injected into the mission. This page explains
how the plugin system works, the fork's hand-injected plugins, the Lua discipline the CI
gate enforces, and lists the notable 414Ret plugins.

## How the plugin system works

Plugins live in `resources/plugins/`, each in its own folder with a `plugin.json`
descriptor. The load order is the list in `resources/plugins/plugins.json`.

A `plugin.json` describes the plugin to both the loader and the settings UI:

| Field | Meaning |
|---|---|
| `nameInUI` / `descriptionInUI` | Title and explanation shown on the LUA Plugins settings page. |
| `skipUI` | Hide the plugin from the settings UI. |
| `defaultValue` | Whether the plugin starts enabled. |
| `specificOptions` | Per-plugin tunables (each with its own `mnemonic`, label, default, min/max) shown as settings. |
| `scriptsWorkOrders` | The Lua files to inject, with load/disable directives. |
| `configurationWorkOrders` | Configuration scripts, same shape. |

At mission generation Retribution reads the work orders and injects the referenced Lua
into the `.miz`, so the scripts run when the mission starts. The `base` plugin is the
mandatory core every mission loads.

### The late-init pass: load-after-config plugins

Most plugins are ordinary work-order plugins. But a couple of the fork's features —
**TIC** and **MooseAtis** — must load their main script **after** every plugin's
configuration has been injected, because their init reads `dcsRetribution.plugins.<name>`
(and MOOSE) the moment it loads. The normal work-order pass loads a plugin's scripts before
its own config, so it can't express that ordering.

These are `LuaPlugin` subclasses (`game/plugins/tic.py`, `game/plugins/mooseatis.py`,
registered in `game/plugins/manager.py`'s `_PLUGIN_CLASSES`) that declare what to load late via
`late_init_files()`, an optional `late_init_preamble()`, and a `should_late_init()` gate.
`inject_plugins()` then runs a **second pass** that loads each one's files after the normal
config pass — so the vendored MOOSE class plus the small `*_414_init.lua` that owns
construction land last, with everything they need already present.

The robustness win over the old hand-injected approach: a missing or renamed init file is
now caught by an automated test (`game/plugins/tests/test_late_init.py`) at CI time, instead
of the feature **silently never starting** in-game. (This replaces the former
`_inject_*_script()` "scramble pattern".)

## The framework: MOOSE (MIST is retired)

The in-mission framework is **MOOSE** (a bundled `Moose.lua`; some plugins vendor classes
verbatim). **MIST is retired** — the MIST-to-MOOSE consolidation is complete. The `base`
plugin's `"mist"` work order now loads `resources/plugins/base/mist_moose_shim.lua`, a
vanilla-DCS compatibility shim implementing only the `mist.*` symbols the remaining
consumers (CTLD, the intercept glue, the core script, the COIN and mobile-missile
runtimes, and the upstream land/water relocate scripts) actually call, so the old `mist_4_5_126.lua` no longer loads. Write new runtime logic against MOOSE.

MOOSE API docs:
https://flightcontrol-master.github.io/MOOSE_DOCS_DEVELOP/Documentation/index.html

## Lua discipline (the CI gate enforces it)

Plugins must follow strict rules:

- **Lua 5.1 only** — no `goto`, no later-version syntax.
- **Sandboxed** — no `os` / `io` (the mission-scripting sandbox blocks them).
- **Vanilla DCS units only** — no HighDigitSAMs or other mod units in plugin scripts.
- **Definition order matters** — define a function before it is first used.

The blocking **`lua-lint.yml`** CI workflow runs `luac5.1 -p` over every
`resources/plugins/**/*.lua` as a syntax gate; an advisory luacheck pass (scoped to
414th-authored scripts via `.luacheckrc`) reports counts but does not block. The syntax
gate catches parse-time errors only — **runtime behavior still needs an in-game pass**
(tracked in `docs/dev/414th-ingame-pass-checklist.md`).

## Per-plugin options UI

Each plugin's `specificOptions` render on the LUA Plugins settings page with
squadron-readable labels and units, and `descriptionInUI` explains what the system does.
For example, the C-130J plugin exposes EW-capacity regen, area/spot jam ranges, and max
ELINT tracks as sliders.

## The plugins

All 29, in `plugins.json` load order. "Inert unless" means the plugin ships in every mission
but does nothing until the mission generator emits its data — turning the matching campaign
setting off costs nothing at runtime.

### Core and framework

| Plugin | Default | What it does |
|---|---|---|
| `base` | on | Mandatory core scripts, the MIST→MOOSE shim, `Moose.lua`, and the sortie recorder. |
| `ctld` | on | CTLD — sling-loading crates, deploying troops and vehicles, JTAC autolasing. Also carries the §76 paradrop runtime. |
| `MooseSoundhandler` | off | Radio-call and combat sound effects on in-game events. |
| `MooseMarkerOps` | off | MOOSE MarkerOps — F10 map-marker command parsing. |
| `MooseAtis` | off | MOOSE ATIS broadcasts. (Late-init plugin.) |

### Air defense, EW and ISR

| Plugin | Default | What it does |
|---|---|---|
| `mantisiads` | on | MOOSE **MANTIS** — the sole IADS engine. SAM/EWR networking, emissions control, engagement tuning, EWR shoot-and-scoot. Skynet was removed; see [IADS Engine: MANTIS](IADS-Engine-MANTIS). |
| `c130j` | on | Turns the player C-130J into an EC-130H Compass Call (jamming) and RC-130H Rivet Joint (ISR/ELINT) platform — `FlightType.JAMMING`. Supersedes the retired generic `ewrj`. |
| `growler` | on | Escort jamming for the EA-18G and EA-6B: non-stacking spoof bubbles and SAM weapons-hold pulses. Inert unless an escort-jammer flight exists. |
| `gpsjamming` | on | GPS denial — satellite-guided weapons released inside the bubble land long. Inert unless a live GPS-jamming group is on the map. |
| `commsjam` | on | Enemy comms jamming from IADS C2 nodes. Inert unless the setting is on. |
| `rednet` | on | The audible, DF-able enemy radio net (§70 COMINT). Inert unless the setting is on. |
| `bigeye` | off | BigEye EWR — text threat reports to pilots, prioritised by contact danger. |
| `lotatc` | off | Exports anti-air sites to LotATC so GCI controllers see the SAM/AAA picture. |

### Ground war and the front line

| Plugin | Default | What it does |
|---|---|---|
| `tic` | on | Troops In Contact — formation-keeping frontline units fighting prolonged scripted firefights. (Late-init plugin.) |
| `coin` | on | The COIN insurgency layer's movers and ambient pressure. Inert unless a COIN campaign. |
| `mobilemissiles` | on | The SCUD hunt — shoot-and-scoot theater missile sites. Inert unless the setting is on. |
| `minefields` | off | Faked area mining via a designated cluster dispenser. **§57 is shelved** — inert, code retained. |
| `vietnamops` | on | The Vietnam Ops suite (Arc Light, flak gauntlet, naval gunfire, convoy interdiction, harassment, Super Gaggle, FAC(A), snake-and-nape) plus the generic frontline-artillery runtime. |

### Naval and carrier

| Plugin | Default | What it does |
|---|---|---|
| `airboss` | on | MOOSE Airboss — LSO and Marshal voice comms, the recovery window schedule, optional rescue helo and recovery tanker. |
| `deckdecor` | on | Carrier deck dressing (§72): strikes each boat's launch-phase statics below before recovery. |
| `cruisemissiles` | on | Ship-launched land-attack cruise missiles, F10 call-for-fire and auto raids. Inert unless the setting is on. |
| `navalmagazines` | on | The fleet's finite anti-ship missiles and staggered weapons-free release. Inert unless the setting is on. |

### Missions, pilots and hosting

| Plugin | Default | What it does |
|---|---|---|
| `opscsar` | on | **Combat SAR** — spawns downed pilots and runs the rescue via MOOSE `Ops.CSAR`. See [Combat SAR](Combat-SAR). |
| `intercept` | on | Per-squadron QRA intercept reserve feeding the MOOSE `AI_A2A_DISPATCHER`. |
| `reactivered` | on | Living battlespace reactive red — real alert fighters flying a defensive patrol over a struck objective. |
| `redscramble` | on | Host tool: an F10 menu to scramble red interceptors. Inert unless the setting is on. |
| `briefing` | on | The mission-start briefing card each pilot sees when they slot in. |
| `splashdamage3` | on | The squadron's locked, softened Splash Damage 3.4.2 build. No user-adjustable options by design. |
| `aisleep` | on | Ground AI sleep — distant garrisons stop thinking and wake on approach. Inert unless the performance setting is on. |

> **There is no recon plugin.** It was removed on 2026-08-20 along with its capture ledger:
> the 2026-08-18 rework made engaging a site the only reveal, so nothing read a capture.
> Recon's surviving job — finding hidden enemy command posts — is planner-side Python. See
> [Fog of War and Reconnaissance](Fog-of-War-and-Reconnaissance).

> Civilian background air traffic is **no longer a Lua plugin** — it was reimplemented
> as Python-planned, pydcs-spawned air traffic (`game/missiongenerator/civiliantraffic.py`),
> replacing the MOOSE RAT plugin that caused recurring sim crashes.

## Writing or modifying a plugin

Copy the closest existing plugin folder, edit its Lua and `plugin.json`, and add the folder
name to `plugins.json`. Keep to the Lua 5.1 / vanilla-units / define-before-use rules so
the syntax gate passes, and plan an in-game pass for the runtime behavior. For a feature
that needs both a Python planner side and a Lua runtime side, keep the split clean: Python
sets up and spawns, Lua executes — don't move runtime logic into the planner or vice versa.

## See also

- [Custom Campaigns](Custom-Campaigns) — campaigns and the IADS engine
- [Electronic Warfare and ISR](Electronic-Warfare-and-ISR) — the `c130j` plugin in play
- [Troops In Contact](Troops-In-Contact) — the `tic` plugin in play
- [Combat SAR](Combat-SAR) — the `opscsar` plugin in play
- [Dedicated Server Guide](Dedicated-Server-Guide) — running plugin-driven missions on a server
