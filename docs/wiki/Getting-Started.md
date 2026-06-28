# Getting Started

Welcome to **414Ret**, the 414th Joint Fighter Group's fork of [DCS Retribution](https://github.com/dcs-retribution/dcs-retribution). Retribution is a turn-based dynamic campaign generator for [DCS World](https://www.digitalcombatsimulator.com/en/products/world/). It is an external program: it does not run inside DCS. Instead, it plans an air war and writes out a full, complex `.miz` mission that you fly in DCS, then reads the results back to advance a persistent front line. You plan a turn, fly (or let the AI resolve) the missions, and the campaign state — territory, losses, supply, and your air wing — carries forward.

This page covers what Retribution is, how to install 414Ret, the first launch, and where to go next.

## The turn-based campaign concept

A Retribution campaign is a loop:

1. **Plan the turn.** Open the map, look at the front line and known enemy intel, and build packages of flights into the Air Tasking Order (ATO). You assign tasks (CAP, strike, SEAD/DEAD, BAI, escort, and the fork's extra tasks), pick aircraft and loadouts, and set timings.
2. **Generate and fly.** Retribution writes a single `.miz` mission containing everything planned for both sides. You fly your slots in DCS (solo or co-op multiplayer); AI flies the rest.
3. **Debrief and advance.** Close the mission and Retribution reads what happened — kills, losses, runway and base damage, and front-line movement — then advances the campaign so the next turn reflects the new situation.

Because the state persists, a campaign is a series of connected operations rather than disconnected one-off missions. Aircraft, pilots, and ground forces are finite and must be managed.

## What's different in the 414th fork

> 414Ret keeps the upstream Retribution engine and adds a squadron-focused layer on top: incomplete enemy intelligence that makes recon worth flying, new player tasks (SCAR, Combat SAR, C-130J JAMMING, TARPS), reworked air-defense and front-line behavior, a unified dark-themed map layers panel, and the *Germany — Red Tide* campaign. Where this guide notes a difference, it links to the relevant page. For the full tour, see [414th Fork Overview](414th-Fork-Overview).

If you have used upstream Retribution before, the core workflow is unchanged — you will recognize the New Game wizard, the map, and the ATO. The differences are additive.

## Installing 414Ret

### Option A — download the pre-built Windows release (recommended)

Pre-built `.exe` releases auto-publish every time the fork's `main` branch updates. No GitHub account is needed.

1. Go to **https://github.com/bradyccox/414Ret/releases/tag/latest**.
2. Download `414th-retribution-latest.zip`.
3. Extract it somewhere outside `C:\Program Files` (your `Saved Games` folder or any normal user directory is fine — installing under Program Files can cause permission issues).
4. Run `retribution_main.exe`.

The `latest` release is a rolling pre-release that always reflects the current `main` branch. Delete any previous extracted copy before unzipping a new one rather than merging folders.

### Option B — run from source

If you want to run from source (for development or to follow `main` directly), the process matches upstream Retribution. From the repo root on Windows (PowerShell):

```powershell
.\scripts\bootstrap-env.ps1   # find Python 3.11, recreate .venv, install requirements
.\scripts\check-env.ps1        # verify Python, venv, and Git LFS auth health
.\venv\Scripts\python.exe -m qt_ui.main
```

You need a working DCS World install, and the MOOSE-dependent features assume the bundled mission plugins under `resources/plugins/` are present. See [`README.upstream.md`](https://github.com/bradyccox/414Ret/blob/main/README.upstream.md) for the full upstream setup, dependencies, and tooling notes.

## A note before you launch

Retribution temporarily modifies your DCS `MissionScripting.lua` so it can record mission events. This is normal and does not prevent you from passing the integrity check to join multiplayer servers. Launch Retribution **before** launching DCS; the original file is restored when Retribution closes. Advanced users can disable the automatic modification, but editing that file by hand carries its own risk — leave the default in place unless you know why you are changing it.

## First launch

On first run, point Retribution at your DCS World installation and your `Saved Games\DCS` folder when prompted. It uses these to detect your installed modules (which determines the aircraft and campaigns available to you) and to write generated missions into the right place.

Once it knows where DCS lives, start a campaign from the **New Game** wizard. The wizard walks you through:

- **Theater and date** — pick a campaign/map and a start date. Choose a smaller campaign for your first run rather than a high-unit-count one.
- **Factions** — pick the side you fly (blue) and the opponent (red). 414Ret adds the `[CH] Iran 2020` faction and the *Germany — Red Tide* campaign's historical 1988 NATO/Warsaw Pact factions.
- **Generator and difficulty options** — carriers/LHAs, navy presence, economy multipliers, and automation assists.
- **Air wing** — review and adjust the squadrons you start with.

## Where to go next

- [Air Wing Configuration](Air-Wing-Configuration) — set up your squadrons and aircraft before the campaign starts.
- [Squadrons and Pilots](Squadrons-and-Pilots) — how squadrons, pilots, and the alert/QRA reserve work over a campaign.
- [Turn Zero](Turn-Zero) — the opening turn and what to do before you fly anything.
- [Your First Operation](Your-First-Operation) — a walkthrough of planning and flying a first turn.
- [The Retribution UI](The-Retribution-UI) — a tour of the map, toolbar, ATO, and dialogs so you know where to click.
- [Mission Planning](Mission-planning) — building packages, tasks, and flight plans in depth.

## See also

- [Home](Home)
- [414th Fork Overview](414th-Fork-Overview)
- [The Retribution UI](The-Retribution-UI)
- [Mission Planning](Mission-planning)
- [Map Layers and Interface](Map-Layers-and-Interface)
