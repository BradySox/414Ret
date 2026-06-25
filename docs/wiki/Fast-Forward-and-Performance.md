# Fast Forward and Performance

This page collects three short, closely related topics: **fast-forward** (jumping into a
mission already in progress), **performance options** (keeping framerate sane on large
campaigns), and **auto-purchase** (letting the campaign spend your budget for you between
turns).

## Fast forward

Fast-forward accelerates mission time so you spawn into a conflict that is already underway
instead of waiting through startup, taxi, and a long transit before anything happens.

Fast-forward begins **when you push the take-off button** and runs until it reaches the
first of these:

- **First contact** — an enemy threat range or an ingress waypoint.
- **Startup, taxi, or takeoff** of a player flight.

You enable it under **Settings → Mission Generator**, "Fast forward mission to first
contact." Related options:

- **Player missions interrupt fast forward.** If a player's startup falls before first
  contact, fast-forward pauses for that startup/taxi/takeoff. Testing tip: add a "+15 min
  past ASAP TOT" offset to player flights.
- **Auto-resolve combat.** If takeoff would occur after first contact, the system simulates
  the combat and starts the mission at your take-off time. Note the documented warning:
  combining auto-resolve with "Never" for player interruptions means fast-forward will never
  stop.

Once you push **Take off**, you cannot change settings — to make changes you must reload the
game state.

## Performance options

Large campaigns can stress CPU and GPU. These options trade detail for framerate:

- **Distant unit culling.** Removes ground units and buildings beyond a set distance from
  exclusion zones (front lines, airfields, mission targets). Air units are never culled. Set
  it too large and culling does little; too small and the experience suffers.
- **Budget / aircraft counts.** Lower budgets and income reduce how many aircraft can be
  bought. Keeping the maximum under roughly **150 aircraft per side** helps performance.
- **Smoke on frontline.** Frontline smoke can hurt GPU framerate, especially during CAS.
- **Convoy distances.** Disabling full-distance convoy driving reduces CPU-heavy pathfinding.
- **Infantry squads.** Removing them cuts unit count without changing gameplay outcomes.
- **Destroyed unit carcasses.** Unchecking removes dead-unit wrecks to recover performance.
- **IADS script.** A SAM-management script keeps SAMs inactive until threatened, improving
  performance. (See the fork note below on the IADS engine.)
- **Tacview.** Recording everything it tracks can cause significant framerate drops.
- **Dedicated server.** On modern multi-threaded systems an external server is no longer a
  performance win; it mainly matters for multiplayer.

### Fork note: IADS engine

Upstream's performance IADS is Skynet. This fork defaults new campaigns to a **MANTIS**
IADS engine (Skynet is still selectable, and existing saves stay on whatever they were saved
with). Functionally it serves the same role — managing SAM activation — so the performance
guidance above still applies. See the project README and IADS design notes for detail.

## Auto-purchase options

Auto-purchase lets the campaign spend your budget for you each turn, mirroring how the
opponent AI buys. There are three independently toggleable behaviors, applied in this
priority order:

1. **Runway repair.** Damaged runways automatically begin repairs when affordable — top
   budget priority, so your fields come back online (see [Base Capture](Base-Capture)).
2. **Front line reinforcement.** Up to half the remaining budget buys ground units,
   prioritizing active fronts with fewer than ~30 units, then distributing extras across
   active points.
3. **Aircraft reinforcement.** Remaining funds buy aircraft to fill out incomplete missions,
   preferring fields outside enemy threat zones. If nothing affordable is in range, the
   leftover budget carries over to the next turn.

## See also

- [Base Capture](Base-Capture)
- [Frontline Stances and Movement](Frontline-Stances-and-Movement)
- [Unit Transfers](Unit-Transfers)
- [Mission Planning](Mission-Planning)
