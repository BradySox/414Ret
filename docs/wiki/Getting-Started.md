# Getting Started

Install, set up a campaign, and fly your first turn.

**414Ret** is the 414th Joint Fighter Group's fork of
[DCS Retribution](https://github.com/dcs-retribution/dcs-retribution), a turn-based dynamic
campaign generator for [DCS World](https://www.digitalcombatsimulator.com/en/products/world/).

It runs **outside** DCS. It plans an air war, writes a `.miz` you fly in DCS, then reads the
results back and advances the campaign. Territory, losses, supply and your air wing carry forward.

**One rule governs everything: only what happens inside a running mission changes the campaign.**

---

## Install

### Pre-built Windows release (recommended)

Releases publish automatically on every push to `main`. No GitHub account needed.

1. **[Download the latest build](https://github.com/BradySox/414Ret/releases/tag/latest)** —
   `414th-retribution-latest.zip`.
2. Extract it **outside `C:\Program Files`**. Program Files causes permission problems.
3. Run `retribution_main.exe`.

Delete the previous extracted copy before unzipping a new one. Do not merge folders.

### From source

```powershell
.\scripts\bootstrap-env.ps1   # find Python 3.11, recreate .venv, install requirements
.\scripts\check-env.ps1       # verify Python, venv, and Git LFS auth
.\.venv\Scripts\python.exe -m qt_ui.main
```

You need a working DCS install. Full upstream setup:
[`README.upstream.md`](https://github.com/BradySox/414Ret/blob/main/README.upstream.md).

### Before you launch

Retribution temporarily modifies your DCS `MissionScripting.lua` so it can record mission events.
This does not break the multiplayer integrity check, and the original is restored on exit.

**Launch Retribution before DCS.**

---

## First launch

Point Retribution at your DCS World install and your `Saved Games\DCS` folder when prompted. It
uses both to detect your modules and to write generated missions.

![The New Game wizard's Introduction page, with the campaign-type radio buttons: Play an included campaign, and Vietnam (period Vietnam-only content)](https://raw.githubusercontent.com/BradySox/414Ret/main/docs/wiki/img/new-game-wizard.png)

*The New Game wizard. The fork adds a **Vietnam** content shell alongside the included campaigns.*

In the **New Game** wizard:

- **Theater and date** — pick a campaign, map and start date. Choose a small campaign first, not a
  high-unit-count one.
- **Factions** — blue and red. The fork adds `[CH] Iran 2020` and its campaigns' historical factions.
- **Generator and difficulty** — carriers and LHAs, navy presence, economy multipliers, automation.
- **Air wing** — your starting squadrons. See [Squadrons and Pilots](Squadrons-and-Pilots).

---

## Turn Zero

The setup turn. You fly nothing. You spend the opening budget, position forces, and commit into
Turn 1.

On load the campaign builds your air wing from the faction and campaign presets, establishes the
front line and seeds ground forces along it, initialises the enemy IADS, and grants your budget.

**Aircraft.** Each base's **Airfield Command** tab, **+** to buy. Purchases arrive next turn and
are capped by budget and parking. Cancellable before you commit; sales are final.

**Ground units.** **Ground Forces HQ**. Turn Zero is unusually permissive — you can reinforce *any*
friendly control point. Afterwards recruitment needs a control point with a **factory**, and a
convoy advances one supply-route segment per turn. Set offensive or defensive stance now.

**Auto Purchase** reinforces routine needs for you if you would rather hand-buy only what you care
about.

**The enemy picture is deliberately incomplete.** A site's composition, strength, damage and threat
rings stay hidden until you **engage** it. Recon does not reveal them — its one job is finding
hidden enemy command posts. Plan your opening turns expecting to discover the defences. See
[Fog of War and Reconnaissance](Fog-of-War-and-Reconnaissance).

To see the real laydown anyway — sanity-checking a campaign, or planning the opposing side — tick
**Reveal fog of war (overview)** in the map's layer panel. It is a view toggle only: never saved,
never alters the campaign.

Commit with **Begin Campaign** to advance to Turn 1.

---

## Your first operation

### Plan a package

A *package* is a group of flights sharing an objective and timing. From the **Air Tasking Order**
panel, let the auto-planner frag packages or build your own:

1. Pick a target on the map.
2. Add flights, choosing the **task**, squadron and airframe.
3. Retribution routes each flight and shows departure base, squadron fit, available aircraft and
   target distance.

See [Mission Planning](Mission-planning) for what each task does.

### Add player slots

Select the package in the ATO and add **client slots** to the group. The rest fly as AI.

Watch the timing: a **cold start** shifts takeoff earlier and can push a start time negative. If it
does, adjust the package **Time on Target** or the flight's start type.

### Set the Time on Target

The TOT is when the package's primary flights are over the target. Retribution back-plans takeoffs,
joins and support timing from it. Nudge it to deconflict packages or to sequence SEAD ahead of
strikers.

### Generate and fly

Generate the mission (**Take Off**).

> Do not close the generation window until your flight is complete. The mission is only valid while
> that window stays open. If you change the plan, regenerate and reload.

Load `retribution_nextturn.miz` in DCS and pick your slot. Steerpoints, TOT, comms and the package
picture are on the kneeboard (Right Shift + K). Or **skip** the turn and let the simulation resolve
it.

The fork's player tasks are **TARPS** photo-recon, **CSAR** pilot rescue, and **JAMMING** standoff
EW/ISR on the C-130J.

### Debrief

Exit DCS and accept the results. The debrief leads with a **Mission Impact** summary — territorial
changes, runway damage, losses — before the event detail. Damage is reported as it happened; there
is no confirmation lag.

Accepting advances the front line and rolls the next turn.

---

## Next

- [Squadrons and Pilots](Squadrons-and-Pilots) — squadrons and aircraft.
- [Mission Planning](Mission-planning) — packages, tasks and flight plans in depth.
- [The Retribution UI](The-Retribution-UI) — map, toolbar, panels, layers.
- [414th Fork Overview](414th-Fork-Overview) — what the fork changes.
