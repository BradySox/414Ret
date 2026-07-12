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

  > **Fork note:** the auto-resolver is **capability-weighted**, not a coin flip. Air-to-air is
  > decided by best A2A task-priority × aircraft count (a modern fighter beats an obsolete one, and
  > escorts matter), and SAM survival scales with SEAD role/capability and the number of engaging
  > sites. AI-only combats also keep resolving during a *Player at IP* fast-forward, so a
  > ground-started player still spawns at its IP instead of the fast-forward halting at the first
  > unrelated fight.

Once you push **Take off**, you cannot change settings — to make changes you must reload the
game state.

## Performance options

Large campaigns can stress CPU and GPU. These options trade detail for framerate:

- **Ground AI sleep** *(fork feature)*. **"Distant ground AI sleeps until aircraft approach"**
  (Mission Generation → Performance) is the middle ground culling never had: rear-area
  garrisons keep existing — visible, strikeable, kills count normally — but their AI is
  switched off while no aircraft is within ~15 NM, cutting the cost of hundreds of thinking
  ground units without deleting anything. SAM sites, the front line, convoys and every
  scripted mover are never touched. Off by default until it has an in-game pass.
- **Distant unit culling.** Removes ground units and buildings beyond a set distance from
  exclusion zones (front lines, airfields, mission targets). Air units are never culled. Set
  it too large and culling does little; too small and the experience suffers. Note the
  exclusion zones include **every mission target from both sides' ATOs**, so on a busy turn
  most of the map is exempt — if enabling it seems to change nothing, that is why. Prefer
  Ground AI sleep first; keep culling for what you never want to exist at all.
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

Upstream's performance IADS is Skynet. This fork runs the **MANTIS** IADS engine instead —
Skynet was removed, and older saves migrate automatically. Functionally it serves the same role
— managing SAM activation and networking — so the performance guidance above still applies. See
[IADS Engine: MANTIS](IADS-Engine-MANTIS) for detail.

## Squadron MP event loadout (host checklist)

For a big multiplayer event night on a dense campaign (Red Tide deep into a war, a heavy COIN
turn), set these **in the campaign save before generating the mission**. Where the frames
actually go: **server stutter** comes from thinking ground units (each armed unit runs sensors
and targeting every frame), **client FPS** comes from particle effects (smoke, fires) and unit
draw, and in multiplayer every scripted explosion or shot is also a network event for every
client. So the levers, in order of payoff:

| Setting | Where | Event night | What it buys |
|---|---|---|---|
| Maximum ground units deployed per frontline | Mission Generation → Performance | **60 → 30** | The single biggest lever — halves the FLOT vehicles, their infantry escorts, and the TIC battle script's workload (which scales super-linearly with combatants) |
| Distant ground AI sleeps until aircraft approach | Mission Generation → Performance | **On** | Rear garrisons stop running AI until someone actually flies there; nothing is deleted |
| Generate infantry squads alongside vehicles | Mission Generation → Performance | Off | Removes ~5 infantry per armor group (MANPAD coverage partially remains) |
| Ambient suppressive fire | Plugin Options → Troops In Contact | Off | Stops the constant scripted tracer fire on the FLOT — every burst is a network event in MP |
| Front-line smoke effects | Mission Generation → Performance | Off (or spacing 6000+) | Smoke columns are pure client-side GPU cost, worst exactly where CAS flies |
| Battle damage at depleted bases (fires, smoke, wreckage) | Mission Generation | Off | Burning bases look great and cost real FPS for everyone nearby |
| Generate carcasses for units destroyed in previous turns | Mission Generation → Performance | Off | Wrecks accumulate every turn; a campaign 10+ turns in carries hundreds |
| Disable untasked OPFOR (and OWNFOR) aircraft at airfields | Mission Generation → Performance | On | Deletes decorative parked jets nobody will fight |
| Culling of distant units | Mission Generation → Performance | Optional, ~70 km | Modest gains (see the caveat above); try it after the rest |
| Moving ground units | Mission Generation → Performance | Last resort: Off | The FLOT stands and fights in place — kills the battle's movement, keeps the shooting |

**Not worth disabling:** the feature plugins that sound heavy mostly aren't. Combat SAR, comms
jamming, the briefing cards, minefields, mobile-missile scoot, convoy ambushes and TARS are
event-driven and near-idle until their moment comes — turning them off buys nothing measurable.
The battlefield's *density* and the *effects* are the cost, not the feature scripts.

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
- [Mission Planning](Mission-planning)
