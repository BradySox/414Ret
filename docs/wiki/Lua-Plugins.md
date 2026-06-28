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
**TIC** and **TARS** — must load their main script **after** every plugin's
configuration has been injected, because their init reads `dcsRetribution.plugins.<name>`
(and MOOSE) the moment it loads. The normal work-order pass loads a plugin's scripts before
its own config, so it can't express that ordering.

These are `LuaPlugin` subclasses (`game/plugins/tic.py`, `tars.py`,
registered in `game/plugins/manager.py`) that declare what to load late via
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
consumers (CTLD, the intercept glue, the core script, and the combat-SAR plugin) actually
call, so the old `mist_4_5_126.lua` no longer loads. Write new runtime logic against MOOSE.

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

## Notable 414Ret plugins

| Plugin | What it does |
|---|---|
| `base` | Mandatory core scripts, the MIST→MOOSE shim, and `Moose.lua`. |
| `c130j` | Turns the C-130J into an EC-130H/RC-130H EW + ISR/ELINT platform (`FlightType.JAMMING`). Replaces the retired generic `ewrj` jammer. |
| `tic` | Troops In Contact — prolonged, formation-aware frontline firefights with ambient suppressive fire. (Late-init plugin.) |
| `tars` | TARS recon engine — films TARPS passes and feeds confirmed BDA back to the campaign. (Late-init plugin.) |
| `combatsar` | The combat-SAR package runtime: rescue helo (Jolly Green) + HC-130 "King" (TACAN/LARS) + the MOOSE `CSAR`/`AICSAR` engines, the enemy snatch-party **capture race**, and rescue scoring. |
| `intercept` | Per-squadron QRA intercept reserve feeding the MOOSE `AI_A2A_DISPATCHER`. |
| `mantisiads` | The IADS engine — MOOSE **MANTIS**. The sole IADS engine; Skynet was removed (see [IADS Engine: MANTIS](IADS-Engine-MANTIS)). |
| `splashdamage3` | The 414th's buddy-tuned Splash Damage 3 weapon-effects build (settings locked by design — do not re-add the config layer). |
| `lotatc` | LotATC export — feeds the campaign's air picture to a LotATC controller. |
| `bigeye` | BigEye — EWR/early-warning radar reporting. |
| `ctld`, `airboss`, plus `Moose*` helpers (`MooseSoundhandler`, `MooseMarkerOps`, `MooseAtis`) | Stock MOOSE-based logistics, carrier, and utility plugins. |

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
- [Combat SAR](Combat-SAR) — the `combatsar` plugin in play
- [Dedicated Server Guide](Dedicated-Server-Guide) — running plugin-driven missions on a server
