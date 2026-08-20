# The Ground War

How the front moves, how bases change hands, and how you get reinforcements there.

Air power alone takes nothing. Territory shifts when ground units stand on it.

---

## Stances

A stance is the posture you assign a side's frontline ground forces.

| Stance | Behaviour |
|---|---|
| **Defensive** | Hold and defend. Medium groups, no advance. |
| **Ambush** | Defensive variant — ATGM and RPG infantry sit forward with the armour, in smaller groups. |
| **Aggressive** | Tanks and IFVs close on the nearest enemy group and push up to ~16 km. |
| **Elimination** | Aggressive, but destroys the nearest enemy groups before advancing. |
| **Breakthrough** | Large armoured formations rush up to ~35 km, prioritising ground over kills. |
| **Retreat** | Everything falls back up to ~20 km and regroups at a friendly base in range. |

Artillery engages what it can reach and pulls back when damaged, except during a retreat. APCs and
ATGMs follow the offensive movement without over-extending. The AI picks its stance from the force
balance — outnumbered, it gambles on aggressive postures.

---

## How the front moves

**The line's position counts the forces actually present.** Each base's weight is its strength
rating multiplied by the total value of its armour, so a base holding five hundred vehicles pushes
harder than one holding five. With no armour on either side it falls back to morale alone, so
air-only campaigns are unaffected.

**Terrain slows an advance.** Each segment carries a going multiplier — 1.0 for open country, up to
4.0 for ground vehicles cannot cross. Fronts stall at passes and river crossings and run in the
open. An even fight still sits at the midpoint whatever the terrain, so no campaign's front starts
anywhere new.

**The line bulges.** Sectors facing open ground sit forward of sectors backed against bad terrain.
Ground groups are placed along the bow and the F10 map draws it, so a salient is visible.

**Attacking costs more than defending.** The loser always yields the full delta. A winner that was
pushing forward banks only part of it; a winner that held banks the lot. Fronts hold until pushed
and give when they break.

**Reinforcement follows the supply lines.** A base only rebuilds if supply reaches it:

| Route back to a rear area | Recovery |
|---|---|
| Road or shipping | Full |
| Airfield-to-airfield only | A quarter |
| None | Nothing |

Take the crossroads behind an enemy base and it stops replacing what you kill.

Each of these five is a setting, all on by default; turning them all off restores upstream
behaviour exactly.

### Mission outcomes

Results adjust the strength ratings by an influence scaled to how lopsided the ground fight was —
strongest when one side is wiped out, when casualties run worse than 3:1, or when a side is in
**Retreat**; weakest on close fights. Any side with zero survivors loses, a Retreat stance forces a
loss, otherwise the heavier casualties lose.

**CAS and BAI are the attrition.** Every armour or infantry unit your aircraft destroy counts
against the enemy's casualty ratio for that sector. Convoy interdiction counts for the same reason.

### Troops In Contact

The fork replaces vanilla ground AI on the front with **Troops In Contact** — prolonged,
formation-keeping firefights with ambient suppressive fire, instead of stock AI erasing the battle
in seconds. TIC shapes movement per stance and staggers timing so the line ripples rather than
lurching.

**TIC's scripted fire is theatrical** — near misses, not aimed lethality — so the front still moves
on player kills, not on TIC's own attrition. See [Troops In Contact](Troops-In-Contact).

---

## Base capture

A control point flips when both are true:

- A **friendly ground unit is inside the base radius**, and
- **no enemy ground units remain inside it**.

Aircraft can soften a base; ground forces take it.

### When a base falls

Stationed units try to escape rather than be taken:

- **Aircraft** relocate to a friendly base that can operate the type, has parking, and is within
  about 200 nm. Carrier aircraft only fall back to carriers.
- **Ground units** move to a connected friendly control point.

Anything with no valid destination is captured and removed from play.

### Runway state

A runway hit hard enough is **out for repair** — nothing launches or recovers until it is fixed.
Repairs cost budget and take time; with auto-purchase on, runway repair takes top budget priority.
A base can only host types it has parking and facilities for, which is also why retreating aircraft
need a compatible field in range.

Striking an enemy runway suppresses its air operations ahead of a ground push.

---

## Moving units

Units travel a real route at about **one control point per turn**. Routes are re-evaluated at the
start of each turn, so an interrupted transfer reroutes if a path still exists. Cancelling returns
the units to inventory where they stand.

Transport method is chosen automatically, in priority order:

1. **Road** — a convoy drives the frontline road network.
2. **Shipping** — a freighter follows a shipping lane.
3. **Airlift** — between airports. Lowest priority, because it ties up aircraft. Helicopters carry
   one unit, cargo planes two.

**All three are attackable in transit.** Sinking a freighter or shooting down a transport destroys
what it carried. Interdicting an enemy convoy denies those reinforcements to its front line
directly, which is why anti-ground and anti-shipping tasks are planned missions rather than
afterthoughts.

**Airlift and Air Assault** player tasks rely on the in-mission CTLD scripting to load, carry and
deploy units, so those tasks need CTLD in the generated mission.

---

## See also

- [Troops In Contact](Troops-In-Contact)
- [Mission Planning](Mission-planning)
- [Fog of War and Reconnaissance](Fog-of-War-and-Reconnaissance)
- [Fast Forward and Performance](Fast-Forward-and-Performance)
