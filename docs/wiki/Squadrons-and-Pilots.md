# Squadrons and Pilots

Your air force is organized into **squadrons**, each a group of **pilots** flying a single
aircraft type. Pilots gain experience, can be lost, and are replaced over time. This page
covers how squadrons and pilots work, and the fork-specific wrinkles — most notably that a
downed pilot you rescue can be **spared** at debrief.

## Squadrons

A squadron is a pool of pilots flying one aircraft type with a defined set of roles. Each
squadron has a fixed livery and operates from a shore base, a carrier, or both, depending on
what the airframe supports.

- **Predefined squadrons** load from YAML files that set the squadron name, aircraft, roles,
  and pilot names. YAML squadrons can also carry custom **radio presets** (intra-flight
  channels and frequencies) for consistent multiplayer comms.
- **Generated squadrons** are created automatically with randomized names when an aircraft
  type has no predefined squadron for the faction.

## Pilots

Each aircraft on a mission has one assigned pilot from its squadron.

- **Experience.** AI pilots start at a base skill level set in campaign settings and gain a
  skill increase roughly every four missions completed, climbing toward ace.
- **Loss.** A pilot can be killed when their aircraft is destroyed, which removes them from
  the squadron and requires a replacement.
- **Replacements.** Squadrons can optionally auto-recruit new pilots each turn, up to a
  limited rate, while below their maximum (default 24 pilots per squadron).
- **Leave.** You can send a pilot on leave to keep them from being auto-assigned to
  missions.

## Player pilots

Players are treated as individual named pilots rather than as anonymous slots. By default a
**player pilot cannot be killed** (the aircraft is still lost) — this is toggleable in the
difficulty settings. The auto-planner offers preferences for whether players are assigned at
all: never assign players, no preference, or prefer player pilots.

## Fork difference: Combat SAR can spare an experienced pilot

This fork adds a **Combat SAR** flight type that makes a downed aviator worth flying for.
When a human pilot ejects, they spawn on the ground with a beacon. If you recover them with
the rescue helicopter and deliver them to any friendly field, the campaign **spares the
aviator at debrief** — you still lose the jet, but the experienced pilot returns to the
squadron instead of being counted as lost. The rescue closes the loop end to end: the
delivery is what removes that pilot from the loss list. If no rescue is flown (or it fails),
the loss applies as normal.

This is a meaningful change to pilot economy: a veteran crew you would otherwise have to
replace from scratch can be brought home, so protecting and recovering downed players has
real campaign value. See [Combat SAR](Combat-SAR) for how to fly it.

## Fork content: named-livery squadrons in Red Tide

The fork's **Germany – Red Tide** campaign replaces generic, mismatched paint schemes with
**named historical units wearing matching liveries**. Every squadron in that campaign is a
real identity — GSFG and VVS regiments on the red side, 414th Joint Fighter Group units
(VMF-29, Voodoo, the 414th TFS, JFG Hornets) on the blue side — so the air war no longer
spawns aircraft in liveries that do not fit the unit flying them.

## See also

- [Combat SAR](Combat-SAR)
- [Unit Transfers](Unit-Transfers)
- [Base Capture](Base-Capture)
- [Mission Planning](Mission-Planning)
- [Fast Forward and Performance](Fast-Forward-and-Performance)
