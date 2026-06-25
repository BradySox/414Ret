# Frontline Stances and Movement

The ground war in Retribution is fought along a **front line** that runs between
opposing **control points**. Each side's ground forces hold a **stance** that decides
how they behave, and the line itself shifts turn to turn based on who is winning the
ground battle. This page explains both halves: the stances you can set, and how combat
results push the front.

## Ground stances

A stance is a posture you assign to a side's frontline ground forces. It governs whether
units dig in, push forward, or fall back, and how aggressively they fight. The stock
stances are:

| Stance | Behavior |
|---|---|
| **Defensive** | Hold position and defend. Medium-sized groups, no advance. |
| **Ambush** | A defensive variant — ATGM and RPG infantry sit forward with the armor in smaller groups, still holding. |
| **Aggressive** | Tanks and IFVs close on the nearest enemy group and push forward (up to ~16 km), able to threaten bases in range. |
| **Elimination** | Like aggressive, but prioritizes destroying the nearest enemy groups before advancing. |
| **Breakthrough** | Large armored formations rush forward hard (up to ~35 km), prioritizing ground gained over kills. |
| **Retreat** | All units immediately fall back (up to ~20 km) and regroup at a friendly base if one is in range. |

Support units follow the lead: artillery engages anything in range and pulls back when
damaged (except during a retreat), while APCs and ATGMs follow the offensive movement
without over-extending. The AI picks its stance from the balance of forces — when it is
outnumbered it tends to gamble on aggressive postures; when you are weaker it leans
defensive.

## How the front line moves

The line's position is derived from the **strength ratings** of the connected control
points — a value from 0.0 to 1.0 for each side. The front sits at the share of total
strength the player owns, projected across the distance between the two control points,
so it starts at the midpoint and slides toward whoever is winning.

Mission outcomes adjust those ratings through a victory/defeat influence scaled by how
lopsided the ground fight was:

- **Strong** (about ±0.5): one side wiped out, a casualty ratio worse than 3:1, or a side
  in a **Retreat** stance.
- **Normal** (about ±0.3): casualty ratios between roughly 1.5:1 and 3:1.
- **Minor** (about ±0.1): closer fights, or certain defensive stances.

The winner is resolved in order: any side with zero survivors loses; a Retreat stance
forces a loss; otherwise the side that took heavier casualties loses. Between missions,
your control points drift by about ±0.2 strength per turn depending on whether you accept
or skip results.

## CAS and BAI: the real attrition source

The front moves on **kills you actually inflict**. Close Air Support (CAS) and Battlefield
Air Interdiction (BAI) flights are how you tip a frontline battle: every armor or
infantry unit your aircraft destroy counts against the enemy's casualty ratio for that
sector, which feeds directly into the influence calculation above. Convoy interdiction
matters for the same reason — see [Unit Transfers](Unit-Transfers).

## Fork differences: TIC and a distributed FLOT

This fork replaces vanilla ground AI on the front with **Troops In Contact (TIC)** — a
scripted frontline battle simulation that produces prolonged, formation-keeping firefights
with ambient suppressive fire, instead of letting stock ground AI erase the battle in
seconds. TIC shapes each formation's movement per stance (a defensive line digs in short
of the trace; attackers run slide-and-press assault cycles) and staggers the timing so the
line ripples rather than lurching. Crucially, **TIC's scripted fire is theatrical** — near
misses, not aimed lethality — so the campaign front still moves on **player kills**, not on
TIC's own attrition. See [Troops In Contact](Troops-In-Contact) for the full picture.

Two related fork changes round this out:

- **Distributed FLOT formations.** Frontline groups are spread along the line rather than
  piled onto one patch of terrain, so the battle looks and plays like a front instead of a
  single brawl.
- **Front-line navmesh routing hazard.** The active ground battle is treated as a transit
  hazard in the routing mesh, so unrelated AI flights stop loitering over the FLOT. CAS and
  BAI still target the front and reach it normally — only flights with no business over the
  fighting are nudged around it. This applies to both sides.

## See also

- [Troops In Contact](Troops-In-Contact)
- [Base Capture](Base-Capture)
- [Unit Transfers](Unit-Transfers)
- [Mission Planning](Mission-planning)
- [Fast Forward and Performance](Fast-Forward-and-Performance)
