# Getting Started

**414Ret** is the 414th Joint Fighter Group's fork of
[DCS Retribution](https://github.com/dcs-retribution/dcs-retribution), a turn-based dynamic
campaign generator for [DCS World](https://www.digitalcombatsimulator.com/en/products/world/).

It runs **outside** DCS. It plans an air war, writes a full `.miz` mission you fly in DCS, then
reads the results back to advance a persistent front line. Territory, losses, supply and your air
wing all carry forward.

## The turn loop

1. **Plan.** Open the map, read the front line and known enemy intel, and build packages of
   flights into the Air Tasking Order. Assign tasks, aircraft, loadouts and timings.
2. **Generate and fly.** Retribution writes one `.miz` containing everything planned for both
   sides. You fly your slots solo or in co-op; AI flies the rest.
3. **Debrief.** Close the mission and Retribution reads kills, losses, runway and base damage, and
   front-line movement, then advances the campaign.

State persists, so a campaign is a series of connected operations rather than one-off missions.
Aircraft, pilots and ground forces are finite.

## What the fork adds

414Ret keeps the upstream engine and adds a squadron-focused layer: incomplete enemy intelligence
that makes recon worth flying, new player tasks (SCAR, Combat SAR, C-130J JAMMING, TARPS),
reworked air-defence and front-line behaviour, a Vietnam campaign layer, and nine built campaigns.
Full tour: [414th Fork Overview](414th-Fork-Overview).

If you know upstream Retribution, the core workflow is unchanged — the New Game wizard, the map
and the ATO all work the same way. The differences are additive.

## Installing

### Option A — pre-built Windows release (recommended)

Releases auto-publish on every push to `main`. No GitHub account needed.

1. Go to **https://github.com/BradySox/414Ret/releases/tag/latest**.
2. Download `414th-retribution-latest.zip`.
3. Extract it **outside `C:\Program Files`** — Program Files causes permission problems.
4. Run `retribution_main.exe`.

Delete the previous extracted copy before unzipping a new one. Do not merge folders.

### Option B — from source

Matches upstream. From the repo root in PowerShell:

```powershell
.\scripts\bootstrap-env.ps1   # find Python 3.11, recreate .venv, install requirements
.\scripts\check-env.ps1       # verify Python, venv, and Git LFS auth
.\venv\Scripts\python.exe -m qt_ui.main
```

You need a working DCS install, and MOOSE-dependent features assume the bundled plugins under
`resources/plugins/` are present. Full upstream setup:
[`README.upstream.md`](https://github.com/BradySox/414Ret/blob/main/README.upstream.md).

## Before you launch

Retribution temporarily modifies your DCS `MissionScripting.lua` so it can record mission events.
This does not break the multiplayer integrity check.

**Launch Retribution before DCS.** The original file is restored when Retribution closes. You can
disable the automatic modification, but leave it alone unless you know why you're changing it.

## First launch

Point Retribution at your DCS World installation and your `Saved Games\DCS` folder when prompted.
It uses these to detect your installed modules and to write generated missions to the right place.

![The New Game wizard's Introduction page, with the campaign-type radio buttons: Play an included campaign, and Vietnam (period Vietnam-only content)](https://raw.githubusercontent.com/BradySox/414Ret/main/docs/wiki/img/new-game-wizard.png)

*The New Game wizard. The fork adds a **Vietnam** content shell alongside the included campaigns.*

Then start a campaign from the **New Game** wizard:

- **Theater and date** — pick a campaign, map and start date. Choose a small campaign for your
  first run, not a high-unit-count one.
- **Factions** — your side (blue) and the opponent (red). The fork adds `[CH] Iran 2020` and the
  built campaigns' historical factions.
- **Generator and difficulty** — carriers and LHAs, navy presence, economy multipliers,
  automation assists.
- **Air wing** — review and adjust your starting squadrons.

## Next

- [Air Wing Configuration](Air-Wing-Configuration) — squadrons and aircraft before the campaign starts.
- [Squadrons and Pilots](Squadrons-and-Pilots) — pilots and the QRA reserve over a campaign.
- [Turn Zero](Turn-Zero) — the opening turn.
- [Your First Operation](Your-First-Operation) — planning and flying a first turn.
- [The Retribution UI](The-Retribution-UI) — map, toolbar, ATO, dialogs.
- [Mission Planning](Mission-planning) — packages, tasks and flight plans in depth.

## See also

- [Home](Home)
- [414th Fork Overview](414th-Fork-Overview)
- [Map Layers and Interface](Map-Layers-and-Interface)
