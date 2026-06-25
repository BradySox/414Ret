# Unit Transfers

Ground units do not teleport to where you need them. To reinforce a front or stage a
push, you move units between control points, and they travel over a real route — by road,
by sea, or by air — taking time and exposing themselves to attack on the way. This page
explains how transfers work and how they tie into base capture and mission planning.

## Moving units between control points

To transfer ground units, open the origin base's menu and pick a destination that has a
safe path. The units then travel along an available transit route toward that destination
at a rate of about **one control point per turn**. Routes are **re-evaluated at the start
of each turn**, so an interrupted transfer can reroute if a path is still available. If a
transfer is cancelled, the units are returned to inventory at their current location.

## Transport methods

The system automatically chooses how to move each transfer, in priority order:

1. **Road (convoy)** — units drive along the frontline road network as a convoy.
2. **Shipping (cargo ship)** — units cross water on designated shipping lanes as a freighter.
3. **Airlift** — units fly between airports; lowest priority because it ties up aircraft.

### Convoys

Road transfers spawn as **convoys** at the origin and drive on-road toward the destination.
Convoys appear in the generated mission and are **vulnerable to attack** — interdicting an
enemy convoy denies those reinforcements to its front line, which directly affects whether
that sector can hold or advance (see
[Frontline Stances and Movement](Frontline-Stances-and-Movement)).

### Cargo ships

Sea transfers appear as a **freighter** following a shipping lane. Like convoys, ships can
be attacked en route, and sinking one destroys the units it carries.

### Airlift

Air transfers move units between airports. **Helicopters carry one unit**; **cargo planes
carry up to two**. Shooting down a transport aircraft destroys whatever it was carrying, so
airlift is both the most flexible and the most fragile option.

## Relation to base capture

Transfers are how you concentrate ground combat power where it matters. Capturing a base
requires friendly ground units on it with the defenders cleared, so feeding units forward
through transfers is a prerequisite for taking territory — see [Base Capture](Base-Capture).
The same logic works defensively: reinforce a threatened sector before the enemy front
reaches it.

## Relation to mission planning

Convoys and freighters in transit are live targets, which is why **anti-ground and
anti-shipping tasks** exist — interdicting enemy reinforcements is a planned mission type,
not an afterthought.

Airlift also connects to player tasking. **Airlift and Air Assault** mission tasks rely on
the in-mission cargo/troop-transport scripting (CTLD) to load, carry, and deploy units, so
those tasks need CTLD present in the generated mission. See [Mission Planning](Mission-Planning)
for how these tasks are fragged.

## See also

- [Base Capture](Base-Capture)
- [Frontline Stances and Movement](Frontline-Stances-and-Movement)
- [Mission Planning](Mission-Planning)
- [Squadrons and Pilots](Squadrons-and-Pilots)
