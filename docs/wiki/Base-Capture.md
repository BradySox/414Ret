# Base Capture

Control points — airfields, FARPs, carriers, and similar — change hands when the ground
war reaches them. Capturing a base is how territory actually shifts on the campaign map,
and it is driven by ground units, not by air power alone. This page explains the capture
conditions, what happens to the units stationed at a falling base, and the airfield states
you will see along the way.

## How a base is captured

A control point flips to the other side when both of these are true:

- A **friendly ground unit is inside the base radius**, and
- **No enemy ground units remain inside the base radius**.

In other words, your aircraft can soften a base, but it takes ground forces standing on it
— with the defenders cleared out — to take it. You can watch a base's status on the F10
map. Because capture depends on ground units arriving, pushing the front line toward a base
(see [Frontline Stances and Movement](Frontline-Stances-and-Movement)) and feeding
reinforcements forward (see [Unit Transfers](Unit-Transfers)) is the path to taking it.

## What happens when a base falls

When a base is captured, the units stationed there try to escape rather than be taken:

- **Aircraft** relocate to a friendly base that can operate that type, has parking, and is
  within about 200 nautical miles. Carrier aircraft can only fall back to carriers.
- **Ground units** move to a connected friendly control point.

Anything that cannot find a valid destination is **captured and removed from play** (sold).
So a base that is about to fall will bleed off whatever it can and lose the rest.

## Airfield and runway states

A captured base does not necessarily come online for you immediately, and a base you hold
can be knocked out of service:

- **Cratered / damaged runway.** A runway hit hard enough is **out for repair** — aircraft
  cannot launch from or recover to it until the surface is fixed. Repairs cost budget and
  take time; with auto-purchase enabled, runway repair takes top budget priority (see
  [Fast Forward and Performance](Fast-Forward-and-Performance)).
- **Parking and operability.** A base can only host aircraft types it has the parking and
  facilities for, which is also why retreating aircraft need a compatible field within
  range.

Striking an enemy runway is therefore a legitimate way to suppress a base's air operations
ahead of a ground push, and protecting your own runways keeps your forward fields in the
fight.

## Fork notes

This fork does not change the core capture rules, but several systems feed into base
capture indirectly. **Troops In Contact** governs how the frontline ground battle plays out
as forces close on a base ([Troops In Contact](Troops-In-Contact)), and the **drop-spawn**
sandbox tool (a gated cheat) lets you place ground units near a friendly command post for
testing or staging. Enemy command posts can also be hidden from the player map under the
recon fog-of-war rules until revealed — see [Squadrons and Pilots](Squadrons-and-Pilots)
and the fog-of-war notes in the project README.

## See also

- [Frontline Stances and Movement](Frontline-Stances-and-Movement)
- [Unit Transfers](Unit-Transfers)
- [Troops In Contact](Troops-In-Contact)
- [Mission Planning](Mission-planning)
