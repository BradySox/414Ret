# Vietnam Ops

**Vietnam Ops** is an umbrella suite of opt-in, period-authentic mechanics that recreate the
things the modern air-war engine never modelled — the missions and threats that *defined* the
Vietnam air war. Retribution's mission taxonomy (BARCAP/SEAD/DEAD/Strike) and threat model (SAM
rings, MEZ geometry) assume a SAM-and-MiG war. Vietnam was the opposite: **AAA-saturated,
FAC-directed, B-52-and-helicopter-heavy**, with naval gunfire, trail interdiction, and airbases
under near-constant siege. This suite layers those missing pieces on top of the same engine.

Everything here is a **runtime effect inside the generated mission**: Python plans the geometry
and force composition, and the bundled `vietnamops` Lua plugin executes the behaviour. None of it
touches the campaign brain (economy, planner, procurement, save format) — so a feature is
independently opt-in, and turning its toggle off removes its behaviour cleanly, exactly like
MANTIS, Combat SAR, and TIC.

> Most of these effects are **atmospheric / cosmetic** — they make the battlespace *feel* like
> Vietnam. Where a scripted effect overlaps a real target (an Arc Light box over a supply dump, a
> convoy you actually kill), the damage flows through the normal loss path, so it attrits
> natively. None of them add a hidden lethality model or a bespoke scoring system.

---

## The Vietnam Ops settings page

All seven toggles live on their own **Vietnam Ops** settings page (alongside Difficulty &
Realism, Air Doctrine, and the rest), split into two sections:

| Section | Toggle | Feature |
|---|---|---|
| Fire support | Arc Light area bombing (heavy bombers) | [§1 Arc Light](#1--arc-light) |
| Fire support | Naval gunfire support | [§3 Naval gunfire](#3--naval-gunfire-support) |
| Battlefield & interdiction | AAA flak gauntlet | [§2 Flak gauntlet](#2--aaa-flak-gauntlet) |
| Battlefield & interdiction | Truck-convoy interdiction | [§4 Convoy interdiction](#4--convoy-interdiction-steel-tiger) |
| Battlefield & interdiction | Airbase harassment (rocket/mortar siege) | [§5 Airbase harassment](#5--airbase-harassment-rocketmortar-siege) |
| Battlefield & interdiction | Super Gaggle hilltop resupply | [§6 Super Gaggle](#6--super-gaggle-hilltop-resupply) |
| Battlefield & interdiction | FAC(A) willie-pete target marking | [§7 FAC(A) marking](#7--faca-willie-pete-target-marking) |

**Gating model.** Every toggle defaults **OFF**, so a modern campaign never sees flak puffs or
carpet bombing. The Vietnam campaign YAMLs (Khe Sanh, Yankee Station) flip the relevant ones
**ON** through their `settings:` block, so a Vietnam game lights up out of the box while a
Cold-War campaign stays clean. You can flip any of them by hand on the settings page at any time.

The underlying capabilities are **era-flexible** — flak, Arc Light, naval gunfire, and convoy
interdiction all work in any era — but the page name follows the "Vietnam stuff" framing.

Each effect is **symmetric by construction** where it makes sense (either side's heavy bombers
carpet, either side's AAA flaks), but several are effectively blue-side in practice because only
one coalition fields the relevant unit (only OV-10 owners have FACs; the convoy and gaggle
emitters currently hard-pick the red road / blue outpost).

---

## 1 — Arc Light

*Toggle: **Arc Light area bombing (heavy bombers)** · in-game pass: ✅ verified*

Reframes the Operation Niagara **B-52 area strike** as an *effect of the existing Strike task* —
**not** a new mission type. When a **heavy bomber** (B-52H, B-1B, Tu-95MS, Tu-142, Tu-160,
Tu-22M3) flies a **Strike**, the runtime walks a **carpet of bombs** across the target area at the
run-in instead of dropping a single aimpoint.

**How to use it:** frag a normal Strike package with a heavy bomber against an area target. At the
run-in (inside ~8 NM of the target), the plugin fires a one-shot walking box of explosions
oriented along the bomber's bearing to the target — rows stepping along-track so it visibly walks,
columns spreading it cross-track. A **tactical striker** (F-4, A-4) on Strike is completely
unaffected — the heavy-bomber gate means only the big jets carpet.

- **Losses stay native.** A bomber shot down before the run-in simply never drops its carpet;
  where the box overlaps real ground targets the damage is real.
- **Tunable** (plugin options): carpet length/width, per-blast power, release range.

## 2 — AAA flak gauntlet

*Toggle: **AAA flak gauntlet** · in-game pass: ◐ partial (softened for lethality; re-fly owed)*

The single biggest **atmosphere** upgrade. The real Vietnam threat was **AAA, not SAMs or MiGs**,
and the engine's SAM/MEZ threat model barely represents it. With this on, fly within range and
below the ceiling of an **opposing AAA gun** and you draw **barrage flak** — and fly it
**predictably** and the flak tightens onto you.

- **No planning needed.** The plugin discovers AAA at runtime by the DCS `AAA` unit attribute, so
  frontline ZSU-23/Shilka belts *and* airfield guns all contribute. There's nothing to frag —
  just fly into defended airspace.
- **Predictability penalty.** Hold a steady heading and altitude and the bursts creep from loose
  (~150 m off) to tight (~70 m off); a sustained straight-and-level run occasionally draws a close
  "tracking" round. **Jink and vary your altitude** and the flak loosens right back off. It is
  pressure to manoeuvre — **not** a hidden hard-kill SAM.
- **Symmetric.** Both sides' AAA flaks the other side.

> **Balance note.** This is the trickiest feature to get *feel* right — the line between
> "atmospheric" and "unfair invisible threat." It has been softened twice after reading as too
> lethal; the current tuning is deliberately conservative. If it still bites too hard in your
> campaign, the burst power and miss distances are plugin options.

## 3 — Naval gunfire support

*Toggle: **Naval gunfire support** · in-game pass: ☐ untested · **coastal campaigns only***

Offshore **gun ships** — the iconic New Jersey 16″ batteries, plus cruisers/destroyers/frigates —
deliver shore bombardment, a capability the modern engine never had. Two modes run off the same
gun-ship list:

- **Player call-for-fire (F10).** Drop an F10 **map marker** on a target, then use the
  **"Naval Fire Mission → Fire on last F10 map marker"** radio command. The nearest in-range
  friendly gun ship shells the mark, with a "SHOT" / "no ship in range" call back.
- **Automatic coastal bombardment.** On a cadence, each gun ship shells the nearest **opposing**
  ground target within gun range on its own.

**Coastal by construction.** Ships sit offshore and the range gate is ~20 km, so this only ever
reaches **coastal** targets and **no-ops entirely inland** (Khe Sanh) — which is the historicity
gate: naval gunfire never reached the inland siege. Leave the toggle **off** for inland campaigns.
This belongs to Yankee Station / I-Corps coastal operations.

## 4 — Convoy interdiction (Steel Tiger)

*Toggle: **Truck-convoy interdiction** · in-game pass: partial (spawn cycle verified; right-click frag untested)*

A moving **enemy supply column** on the road behind the front — the Ho Chi Minh Trail / Operation
Steel Tiger — surfaced to the player through **Armed Recon**. The engine models logistics as an
abstract transfer; this makes one of those real supply routes a **flyable, interdictable target**
that keeps flowing.

- **Where it is.** Python picks the enemy supply road **nearest the front** (reusing the engine's
  real `convoy_routes`, so the target ties to actual red logistics) and spawns a truck column
  (default 8 × Ural-375) driving it end to end.
- **It reacts to being hunted.** The column **halts under cover** when an opposing aircraft closes
  inside the scatter range, then rolls again once the sky clears — the trucks "go to ground."
- **It keeps flowing.** A while after a column is wiped, a fresh one rolls out with a "convoy
  destroyed on the trail" cue, so the trail keeps producing targets across a long mission.
- **Right-click to frag.** Instead of hunting for the corridor, **right-click an enemy supply
  route** on the map to open the package dialog there with **Armed Recon pre-selected**. (A
  fully-friendly route won't offer it.)

## 5 — Airbase harassment (rocket/mortar siege)

*Toggle: **Airbase harassment (rocket/mortar siege)** · in-game pass: ☐ untested*

The Vietnam air war was fought as much *on the ground at the airbase* as in the air — Bien Hoa,
Tan Son Nhut, Da Nang, Chu Lai, and the Khe Sanh strip were under near-constant rocket / mortar /
sapper standoff attack for years. In the base engine an occupied airbase is a perfectly safe rear
area until the front reaches it. This makes the **forward strips feel contested** — the other half
of "the rear isn't safe" that the flak gauntlet started over the target.

- **Which fields.** Only **forward** (within ~200 km of a front), **occupied**, land
  airfields/FARPs draw fire. A deep-rear or peacetime field is never shelled.
- **Sporadic, not a metronome.** After a **startup grace period** each field takes a small
  scattered barrage near the parking area on a randomized cadence — mostly noise and smoke with a
  modest, tunable bite. A direct hit on a parked static is a bonus, not the goal.

> **You are never shelled on your own ramp.** Any field a client flight spawns from, arrives at,
> or diverts to this mission is **hard-excluded** from targeting (enforced in Python *and*
> re-checked in Lua), and the startup grace period means nobody is shelled mid-alignment. These
> are hard anti-grief guarantees, not options.

## 6 — Super Gaggle hilltop resupply

*Toggle: **Super Gaggle hilltop resupply** · in-game pass: ☐ untested · blue-side*

Models the Khe Sanh **"Super Gaggle"**: a formation of transport helos runs supplies into a
**cut-off forward friendly outpost** while you can fly escort. The base engine has no
besieged-outpost resupply; this makes the forward hilltops feel supplied-under-fire the way they
historically were.

- **What spawns.** Python picks the friendly **FOB/FARP nearest a front** as the besieged outpost
  and the nearest other friendly field as the launch point. The plugin flies a helo gaggle
  (default 3 × UH-1H) **launch → outpost → back**, announces "delivered" on arrival (or "down" if
  shot down en route), and **re-rolls a fresh run** on a cadence so the resupply keeps flowing.
- **Fast-mover suppression choreography.** Each run also launches a short **attack flight**
  (default 2 × A-4E-C — the historical suppressor) that works the AAA over the outpost while the
  helos get in, tied to the gaggle's lifecycle. Set the suppressor count to 0 to disable.
- **Fly escort.** The gaggle is the mission — you can shepherd it in. It needs a friendly forward
  outpost near the front, or it has no effect.

> **Runtime-cosmetic.** The delivery has no supply-economy effect (like the convoy); the value is
> the immersion and the escort opportunity. The suppressor spawns with its type's default loadout,
> so its actual bite against the guns is the #1 open tuning item.

## 7 — FAC(A) willie-pete target marking

*Toggle: **FAC(A) willie-pete target marking** · in-game pass: ☐ untested · blue-effective*

The iconic Vietnam **forward air controller (airborne)**. An **OV-10 Bronco** loitering over the
battle area marks nearby enemy ground with **white-phosphorus smoke** so the strikers — and you —
can visually acquire the target and roll in. The engine already has a **ground JTAC** that
stationarily *lases* targets; this is the distinct **airborne, smoke-marking** half it doesn't
cover, and it's the defining Vietnam FAC image (the Bronco putting willie pete on the target).

- **How it works.** With a friendly **OV-10 airborne** over the front, the plugin drops white
  smoke on the nearest opposing ground unit within ~3 NM of the Bronco on a cadence, plus a
  "target marked with willie pete — cleared hot" cue. No OV-10 airborne ⇒ nothing marked.
- **Marking only.** v1 puts smoke on the target; it doesn't auto-assign the target to a CAS
  package. The visual cue is the point.

---

## In-game pass status at a glance

Several of these are **runtime Lua that CI can't exercise** — they pass the syntax gate but need a
cockpit pass to confirm feel and behaviour. Current state:

| Feature | Status |
|---|---|
| Arc Light | ✅ Verified in the cockpit |
| Flak gauntlet | ◐ Partial — softened for lethality, re-fly owed |
| Convoy interdiction | ◐ Partial — spawn/respawn cycle verified; halt-under-threat + right-click frag untested |
| Naval gunfire | ☐ Untested (both runtime modes) |
| Airbase harassment | ☐ Untested |
| Super Gaggle | ☐ Untested |
| FAC(A) marking | ☐ Untested |

If you fly any of the untested effects, the biggest things to watch: the flak should *pressure you
to jink*, not hard-kill you; airbase harassment must **never** land on a player-spawn field; naval
gunfire should do nothing on an inland map.

## See also

- **[Khe Sanh — Campaign Briefing](Khe-Sanh-Campaign-Briefing)** — the inland Vietnam campaign
  that ships several of these toggles on.
- **[Combat SAR](Combat-SAR)** and **[SCAR](SCAR)** — the Sandy/King rescue package, the other
  half of the Vietnam-era content.
- **[Troops In Contact](Troops-In-Contact)** — the frontline firefight sim the flak/convoy effects
  reuse for their fire plumbing.
- **[Lua Plugins](Lua-Plugins)** — where the per-feature tunables (burst power, carpet size, convoy
  count, cadences) live as plugin options.
</content>
</invoke>
