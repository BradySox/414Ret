# 414Ret - 414th Joint Fighter Group's DCS Retribution Fork

This repository is the **414th Joint Fighter Group's customized build of
[DCS Retribution](https://github.com/dcs-retribution/dcs-retribution)** - a turn-based
dynamic campaign generator for [DCS World](https://www.digitalcombatsimulator.com/en/products/world/).

It is a snapshot of upstream Retribution (`dev` branch) **plus the 414th's own
air-defense, electronic-warfare, and assets-pack features**. The unmodified upstream
project README is preserved as [`README.upstream.md`](README.upstream.md).

> **For AI assistants / other Claude sessions:** read [`CLAUDE.md`](CLAUDE.md) first.
> It is the engineering handoff doc - architecture, where each feature lives, the
> branch layout, and what is still in flight.

---

## What's different from upstream

This fork is upstream `dev` at commit `dce851ea` with the following 414th additions
stacked on top (newest first):

### Data Transfer Cartridge (DTC) export
- **Native DCS DTC cartridge export** — Retribution can write a native Data Transfer
  Cartridge into the generated `.miz` so **F/A-18C** players spawn with the SA picture
  already built: player/AI **CAP racetracks and tanker tracks** drawn on the Hornet SA
  page. Off by default (`generate_dtc` setting). The cartridge is mirrored into
  `Saved Games\DCS\DTC` under a neutral, terrain-tagged name so it never collides with a
  player's own cartridge library.
  - *Current limitation:* ED's mission-start auto pre-load does not fire on the current
    DCS build, so the player loads the `Retribution <terrain> DTC_1` cartridge once from
    the DTC manager per sortie. Re-tested each DCS build.

### New flight types
- **`FlightType.JAMMING`** - standoff electronic-warfare support flown by the C-130J,
  acting as an EC-130H Compass Call / RC-130H Rivet Joint platform. Driven by the
  bundled `c130j_mission_systems.lua` plugin.
- **`FlightType.TARPS`** - player-flown F-14 photo-reconnaissance (all F-14 variants).
  Flies a single pass **directly over the target** ~5 minutes behind the strikers,
  carrying the `{F14-TARPS}` pod (station 6) plus a per-variant self-defense fit.
  Auto-planned into Strike / DEAD packages.
- **`FlightType.SCAR`** - player-flown Strike Coordination and Reconnaissance: work an
  area to find and kill a **moving** high-value target hidden among look-alike decoys and
  light AAA, before it reaches safety. Against a real enemy armor group or SCUD site it
  binds that group (the armor bugs out toward a town; the SCUD races to a firing position
  and launches); otherwise it spawns the whole picture. The scenario is timed to your
  on-station window, with F10 map cues for the target's signature and ingress. Driven by
  the bundled `scar` plugin (default ON). Player-selected for now — BAI stays the
  auto-planner's anti-armor task.
- **Recon intel-fog** - enemy ground sites appear on the map as targets you can plan
  packages against, but *what is actually there* - unit types, counts, damage state, and
  threat/detection rings - stays hidden until the site is **attacked, scouted by
  recon/TARPS, or has a unit destroyed**. That's what finally makes recon worth flying.
  AI planning and threat math always use true state, so auto-planning is unaffected.
  Existing campaigns stay revealed; the fog applies to new campaigns. Master switch:
  the `recon_intel_fog` campaign setting (default on).
- **BDA damage lag** - on top of that, a struck enemy site you *have* discovered keeps
  showing its units as alive until a TARPS pass confirms the kill, so you can't tell from
  the map alone whether a strike worked. Both fog rules run through one viewer-aware
  visibility layer (`alive_for` / `known_for`).
- **Tactical Air Recon (TARS)** plugin (MOOSE Ops.TARS, default ON) - an optional
  runtime engine for TARPS sorties: an F10 "film" menu, overfly-detection within a
  per-airframe sensor envelope, coalition-only F10 map markers, and scoring. Its landing
  debrief feeds the BDA fog-of-war the exact enemy units a surviving recon pass
  photographed, so confirmed BDA tracks what was actually seen rather than whole-target
  overflight. Enable in the plugins UI.

### Air-defense planning rework
- **Per-squadron QRA intercept reserve** from upstream PR `#782`. BARCAP-capable
  squadrons can hold aircraft back on alert via `intercept_reserve`, with coalition
  defaults and Moose `AI_A2A_DISPATCHER` runtime interception. Defaults are a
  **base-defense** posture (scramble within 60 NM, chase to 38 NM) so QRA defends its
  fields instead of screening forward over the front line; tunable on the Doctrine page.
- **Overlapping BARCAP waves** with jittered timing so CAP doesn't all arrive at once
  (`barcap_overlap_time` setting).
- **Forward CAP line** that pushes CAP toward friendly control points anchoring active
  front lines instead of orbiting deep.
- **Threat-weighted BARCAP volume** - contested sectors get more BARCAP waves (up to 2x)
  based on nearby enemy airfields and the jets parked on them, while quiet flanks keep
  the baseline coverage. Additive only, so no sector is ever left thinner than before.
- **AI routes around the ground battle** - the active front line is a navmesh routing
  hazard, so transiting flights cross it quickly at the least-bad point instead of
  loitering over the combat (CAS/BAI that target the front are unaffected).
- **Reworked legacy SAM site templates** - dedicated SA-2 / SA-3 / SA-5 / SA-6 battery
  layouts (circle & semicircle variants) plus an SA-2/SA-3 mixed site, replacing the
  old generic launcher rings.
- **Dog Ear (Sborka) search radar** now fielded at major Soviet IADS nodes (SA-2/3/5,
  S-300) and standalone Soviet SHORAD, not just bare SHORAD sites.
- OPFOR-aggressiveness direction fix and CAS / Armed-Recon engagement-range bumps.
- **Tunable cruise/patrol altitude** on the Doctrine page — a **minimum patrol altitude**
  floor (e.g. keep all CAP at 28,000 ft and up) plus an **altitude-scatter band** you can
  widen, bias high/low, or switch off entirely. Both default to the previous behavior, so
  existing campaigns are unchanged until you opt in.

### UI transparency
- **Target Intel panel** in every ground-object dialog — type, allegiance, valid
  mission types, known live/destroyed unit counts, detection/threat range, IADS
  membership, MFD visibility, and capturable/purchasable status.
- **Mission Impact summary** in the debrief — bases captured/lost, runway damage, and
  loss overview for both sides, above the detailed casualty tables.
- **Package context bar** — the ATO package window now shows primary task, flight
  count, player slots, actual TOT (`15:32:00 (ASAP)`), and departure bases in one line.
- **Flight-creation context** — a live summary explains the selected task/aircraft/
  squadron choice; squadron tooltips show role, spare aircraft, base, and target distance.
- **Player target location precision** setting (`Exact` / `Approximate target area`) —
  Approximate mode offsets player steerpoints 2–6 NM from the real target and suppresses
  exact F10 marks and kneeboard coordinates, so players have to visually acquire targets.
- **Building card cleanup** — scenery-object building cards no longer show the upstream
  "Missing Recon Picture" placeholder; cards with no icon show a compact name + value layout.
- **Bulk flight altitude** — the flight Waypoints tab has an *Apply to all* control that
  sets every en-route waypoint to one altitude at once, and the per-waypoint altitude
  arrows now step 1,000 ft instead of 1 ft.
- **Self-documenting plugin options** — the *LUA Plugins Options* page now shows a short
  description under each plugin explaining what it does, and the option labels across all
  plugins were cleaned up (typo fixes, consistent units, clearer wording).

### Quality-of-life & robustness
- **Auto-hide mobile SAMs (SHORAD/AAA/MANPAD) on the MFD** at campaign generation
  (`hide_on_mfd`), including escorts generated inside an armor or missile group
  (which previously slipped onto the datalink). Standalone MERAD/LORAD sites stay
  visible for SEAD.
- **Crash fixes:** flight-combat-exit `IndexError`, AWACS orbit stacking, tanker orbit
  placement/deconfliction, and malformed mod-aircraft payload Lua (e.g. CJS Super
  Hornet v2.4 files that use local-variable table indices).

### Frontline & ambiance
- **Troops In Contact (TIC)** plugin (Grendel's TIC v1.1, default ON) - replaces
  vanilla ground AI on frontline maneuver units with formation-keeping, prolonged
  scripted firefights plus a 414th ambient-fire extension. Toggle per game in the
  plugins UI.
- **Civilian background air traffic** via MOOSE RAT - routes invisible civilian
  flights as short regional hops between nearby neutral airfields for ambiance. They
  skip airbases Retribution is using for combat this turn, mostly avoid neutral fields
  in a keep-out bubble around the active front, and the regional distance cap keeps
  legs short so routes stay in the rear instead of cutting across the battle. The
  keep-out is deliberately soft - a small fraction of front-side fields stay in the
  pool, so once in a while a civilian strays into the fight if you're not watching.
  Density is kept light by design.
- **Frontline units spread along the line** instead of stacking on one tile - the
  generator steps perpendicular from the front to find valid ground rather than snapping
  every off-map group laterally onto the same patch.
- **Flight Control (ATC)** plugin (MOOSE FLIGHTCONTROL, default ON) - players-only
  tower comms (taxi/takeoff/landing sequencing with SRS voice, text-subtitle fallback)
  at friendly land airbases. AI limits are kept generous so it does not queue or strand
  AI scrambles. Enable in the plugins UI.

### Assets
- **CurrentHill Iran assets pack** support: Shahed-136, IRGCN FAC variants, and a
  dedicated `[CH] Iran 2020` faction, behind a new-game mod toggle.

A per-feature breakdown with file paths lives in [`CLAUDE.md`](CLAUDE.md).

---

## Download / Latest build

Pre-built `.exe` releases are published automatically every time `main` is updated.
No GitHub account needed — just grab the zip and run.

**[Download latest build](https://github.com/bradyccox/414Ret/releases/tag/latest)**

1. Download `414th-retribution-latest.zip` from the link above.
2. Extract anywhere.
3. Run `retribution_main.exe`.
4. Point it at your DCS World install on first launch.

> The `latest` release is a rolling pre-release that always reflects the current `main`
> branch. For pinned campaign builds, use versioned releases (tagged `v1.x.x`) if
> available.

---

## Running it (from source)

Same as upstream Retribution. Quick start (Windows, PowerShell):

```powershell
.\scripts\bootstrap-env.ps1
.\scripts\check-env.ps1
.\venv\Scripts\python.exe -m qt_ui.main
```

You need a working DCS World install and the MOOSE-dependent features assume the
bundled mission plugins under `resources/plugins/` are present. See
[`README.upstream.md`](README.upstream.md) for the full upstream setup, dependencies,
and wiki links.

### Windows environment sanity

This repo is sensitive to Python drift on Windows. If `.venv` was created from a Python
install that later moved, was removed, or lost execute permissions, all repo-local
commands will start failing in the same confusing way for humans and assistants.

Use these two scripts from the repo root:

```powershell
.\scripts\bootstrap-env.ps1  # find Python 3.11, recreate .venv, install requirements
.\scripts\check-env.ps1      # verify Python, venv, and Git LFS auth health
```

`check-env.ps1` also warns when Git LFS is unauthenticated, which is a common cause of
GitHub push/upload failures for repos with LFS-tracked content.

### Dev checks (must pass before pushing)

```powershell
.venv\Scripts\python.exe -m black --check .      # formatting
.venv\Scripts\python.exe -m mypy game tests       # type checking (CI only checks game + tests)
.venv\Scripts\python.exe -m pytest tests -q       # unit tests
```

---

## Relationship to the 414th workspace

The 414th also maintains a separate **mission-building workspace** (campaign plans,
`.miz` files, and any Mission-Editor-loaded scripts not yet integrated here, such as
the standalone MANTIS IADS). That workspace is private.

Features that started as standalone ME scripts and are now fully integrated into this
repo (do not use the standalone versions):
- **C-130J EW/ISR** → `resources/plugins/c130j/` (`FlightType.JAMMING`)
- **QRA / AI_A2A_DISPATCHER** → `resources/plugins/intercept/` (per-squadron `intercept_reserve`)
- **TARS recon** → `resources/plugins/tars/` (runtime engine for `FlightType.TARPS`)
- **Flight Control ATC** → `resources/plugins/flightcontrol/` (players-only tower comms)

This repo is the **engine-level** side: capabilities planned and spawned automatically
by the campaign generator rather than hand-placed in the Mission Editor.

---

## License & credit

DCS Retribution is licensed under the LGPL (see [`LICENSE`](LICENSE)). All upstream
authorship and the project's history are preserved. The 414th additions are provided
under the same terms. Upstream project: <https://github.com/dcs-retribution/dcs-retribution>.
