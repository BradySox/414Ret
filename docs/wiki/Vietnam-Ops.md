# Vietnam Ops

**Vietnam Ops** is an umbrella suite of opt-in, period-authentic mechanics that recreate the
things the modern air-war engine never modelled — the missions and threats that *defined* the
Vietnam air war. Retribution's mission taxonomy (BARCAP/SEAD/DEAD/Strike) and threat model (SAM
rings, MEZ geometry) assume a SAM-and-MiG war. Vietnam was the opposite: **AAA-saturated,
FAC-directed, B-52-and-helicopter-heavy**, with naval gunfire, trail interdiction, napalm CAS,
and airbases under near-constant siege. This suite layers those missing pieces on top of the
same engine.

Most of the suite is a **runtime effect inside the generated mission**: Python plans the geometry
and force composition, and the bundled `vietnamops` Lua plugin executes the behaviour. Two
features go deeper — **convoy interdiction** and the **Super Gaggle** plug into the real force
model, so the trucks you kill and the helos you lose are genuine campaign assets (see their
sections). Every feature is independently opt-in, and turning its toggle off removes its
behaviour cleanly, exactly like MANTIS, Combat SAR, and TIC.

> Vietnam content now comes in **two layers**. This page is the *mission-level* Ops suite — flak,
> Arc Light, the trail, the gaggle. The *campaign-level* war — political will, the Rolling
> Thunder → Linebacker II ROE arc, ambush MiGs, the Easter Offensive — is
> **[The Vietnam Campaign Layer](Vietnam-Campaign-Layer)**.

---

## The Vietnam Ops settings page

The toggles live on their own **Vietnam Ops** settings page (alongside Difficulty & Realism, Air
Doctrine, and the rest). The mission-level suite:

| Section | Toggle | Feature |
|---|---|---|
| Fire support | Arc Light area bombing (heavy bombers) | [§1 Arc Light](#1--arc-light) |
| Fire support | Naval gunfire support | [§3 Naval gunfire](#3--naval-gunfire-support) |
| Battlefield & interdiction | AAA flak gauntlet | [§2 Flak gauntlet](#2--aaa-flak-gauntlet) |
| Battlefield & interdiction | Truck-convoy interdiction | [§4 Convoy interdiction](#4--convoy-interdiction-steel-tiger) |
| Battlefield & interdiction | Airbase harassment (rocket/mortar siege) | [§5 Airbase harassment](#5--airbase-harassment-rocketmortar-siege) |
| Battlefield & interdiction | Super Gaggle hilltop resupply | [§6 Super Gaggle](#6--super-gaggle-hilltop-resupply) |
| Battlefield & interdiction | FAC(A) willie-pete target marking | [§7 FAC(A) marking](#7--faca-willie-pete-target-marking) |
| Battlefield & interdiction | Snake and nape (napalm CAS) | [§8 Snake and nape](#8--snake-and-nape-napalm-cas) |
| Campaign | Political will tracking | [The Campaign Layer](Vietnam-Campaign-Layer) |
| Campaign | Static front (bounded siege line) | [The Campaign Layer](Vietnam-Campaign-Layer) |

**Gating model.** Every toggle defaults **OFF**, so a modern campaign never sees flak puffs or
carpet bombing. The Vietnam campaign YAMLs (1968 Yankee Station, Velvet Thunder, Red Flag
81-2) flip the relevant ones **ON** through their `settings:` block, so a Vietnam game lights up
out of the box while a Cold-War campaign stays clean. You can flip any of them by hand on the
settings page at any time.

The underlying capabilities are **era-flexible** — flak, Arc Light, naval gunfire, and convoy
interdiction all work in any era — but the page name follows the "Vietnam stuff" framing.

Each effect is **symmetric by construction** where it makes sense (either side's heavy bombers
carpet, either side's AAA flaks, either side's attack jets nape), but several are effectively
blue-side in practice because only one coalition fields the relevant unit (only OV-10 owners have
FACs; the gaggle draws from blue squadrons; the trail is the enemy's road).

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
- **Pairs with the campaign layer:** under Vietnam doctrine the B-52s now arrive as a massed,
  escorted [Alpha Strike](Vietnam-Campaign-Layer#the-real-alpha-strike) instead of a lone naked
  section — and losing one is a national event on the
  [political-will meter](Vietnam-Campaign-Layer#political-will).

## 2 — AAA flak gauntlet

*Toggle: **AAA flak gauntlet** · in-game pass: ✅ verified (after two lethality-softening passes)*

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

*Toggle: **Naval gunfire support** · in-game pass: ☐ untested (arms cleanly in flown sessions;
the firing legs themselves are unflown — no red ground has yet been inside a gun ship's range) ·
**coastal campaigns only***

Offshore **gun ships** — the iconic New Jersey 16″ batteries, plus cruisers/destroyers/frigates —
deliver shore bombardment, a capability the modern engine never had. Two modes run off the same
gun-ship list:

- **Player call-for-fire (F10).** Drop an F10 **map marker** on a target, then use the
  **"Naval Fire Mission → Fire on last F10 map marker"** radio command. The nearest in-range
  friendly gun ship shells the mark, with a "SHOT" / "no ship in range" call back.
- **Automatic coastal bombardment.** On a cadence, each gun ship shells the nearest **opposing**
  ground target within gun range on its own.

**Coastal by construction.** Ships sit offshore and the range gate is ~20 km, so this only ever
reaches **coastal** targets and **no-ops entirely inland** — which is the historicity
gate: naval gunfire never reached the inland battles. Leave the toggle **off** for inland campaigns.
This belongs to Yankee Station / I-Corps coastal operations.

## 4 — Convoy interdiction (Steel Tiger)

*Toggle: **Truck-convoy interdiction** · in-game pass: ◐ partial (the flown trail leg passed —
a real convoy hunted and killed by Armed Recon; the debrief leg is the remaining check)*

A moving **enemy supply column** on the road behind the front — the Ho Chi Minh Trail / Operation
Steel Tiger — surfaced to the player through **Armed Recon**. This is no longer a cosmetic truck
spawn: **the convoy is real**. Each turn the engine makes sure the enemy has genuine supply
columns flowing — actual ground units, debited from a rear base, moving up the road corridors
nearest the front through Retribution's own convoy system.

- **A real trail, not one lone truck.** The trail runs **two concurrent columns of up to ~10
  vehicles** (three during a surge), and fills its budget across **distinct roads** where the
  map has them — Yankee Station's full Ho Chi Minh Trail network, Red Flag 81-2's aggressor
  corridors — rather than stacking everything on one corridor. The columns are framed as **external logistics**: the
  Ho Chi Minh Trail's matériel came from over the border, so a picked source base is topped up
  with fresh whitelisted kit for the run rather than draining a dead local economy.
- **Kill it and it matters.** The trucks carry real reinforcements. Interdict the column and
  those units **never reach the line**; let it through and they do. The kill is recorded natively
  in the debrief — no bespoke scoring.
- **Where it is.** The corridors are the enemy-held roads nearest the fighting, resolved on the
  real control-point graph, so the target always ties to actual enemy logistics. (One documented
  no-op: **Velvet Thunder** — its Marianas island geography has no roads between enemy bases, so
  the toggle does nothing there.)
- **Right-click to frag.** Instead of hunting for the corridor, **right-click an enemy supply
  route** on the map to open the package dialog there with **Armed Recon pre-selected**. (A
  fully-friendly route won't offer it.) The Armed Recon flight plan sweeps the hunted road
  start-to-end rather than orbiting one point.
- **The trail surges during bombing halts.** On the authored Vietnam campaigns, the
  [Bombing Halt phase](Vietnam-Campaign-Layer#red-answers-the-arc) opens the logistics window
  Hanoi historically used: **two concurrent, bigger convoys** run the trail while the halt holds.
  More targets for you — and more reinforcements for them if you don't fly.

## 5 — Airbase harassment (rocket/mortar siege)

*Toggle: **Airbase harassment (rocket/mortar siege)** · in-game pass: ◐ partial (the in-mission
"Incoming" cue and the player-field exclusion are confirmed in flown sessions; the visual impact
confirm is still owed)*

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

*Toggle: **Super Gaggle hilltop resupply** · in-game pass: ◐ partial (two clean flown runs —
delivery, return, and shootdowns all behaved; the loss-accounting debrief check is the remaining
leg) · blue-side*

Models the Khe Sanh **"Super Gaggle"**: a formation of transport helos runs supplies into a
**cut-off forward friendly outpost** while you can fly escort. This is no longer a phantom spawn
on a respawn loop: **the gaggle is drawn from your real squadrons and its losses are real.**

- **What flies.** Each turn the engine picks the besieged blue FOB/FARP near a front, a rear
  launch field, a **real blue helo squadron** for the run and a **real blue attack squadron** for
  the AAA suppressors, and commits those exact airframes — once, no respawn loop.
- **Losses are charged.** A helo shot down on the run is a real airframe loss against its
  squadron at the debrief, exactly like any other flight. Survivors return; a delivered run
  credits the outpost a small ground-strength boost — so the gaggle now has stakes in both
  directions.
- **Fly escort — you can actually find it now.** The run launches on a **delay (~10 minutes,
  tunable)** so a cold-starting escort can plausibly be airborne, the spawn cue announces it,
  and the lead helo carries a **live F10 map mark** refreshed as it flies (removed on
  delivery/loss). It needs a friendly forward outpost near the front and a helo squadron with
  airframes, or it quietly stands down.

## 7 — FAC(A) willie-pete target marking

*Toggle: **FAC(A) willie-pete target marking** · in-game pass: ✅ verified (the named F10 mark
confirmed in a flown session) · blue-effective*

The iconic Vietnam **forward air controller (airborne)**. An **OV-10 Bronco** loitering over the
battle area marks nearby enemy ground with **white-phosphorus smoke** so the strikers — and you —
can visually acquire the target and roll in. The engine already has a **ground JTAC** that
stationarily *lases* targets; this is the distinct **airborne, smoke-marking** half it doesn't
cover, and it's the defining Vietnam FAC image (the Bronco putting willie pete on the target).

- **How it works.** With a friendly **OV-10 airborne** over the front, the plugin picks the
  **largest enemy ground concentration** in range (not whatever lone truck is nearest), drops
  white smoke on it on a cadence, and lays a **named, live F10 map mark** at the target — e.g.
  *"FAC(A): BTR-60 x6 — willie pete, cleared hot"* — refreshed as the FAC works, so the target
  is findable from anywhere and unambiguously the FAC's (the Bronco's own WP rockets make no
  F10 mark). No OV-10 airborne ⇒ nothing marked.
- **Marking only.** It puts smoke and a mark on the target; it doesn't auto-assign the target to
  a CAS package. The visual cue is the point.

## 8 — Snake and nape (napalm CAS)

*Toggle: **Snake and nape (napalm CAS)** · in-game pass: ◐ partial (the player leg is verified —
in-gate passes bloomed the fire walls, above-ceiling passes correctly drew none; the AI-flown leg
is the remaining check)*

The iconic low-level napalm delivery — "snake" for Snakeye retarded bombs, "nape" for napalm.
Where the [flak gauntlet](#2--aaa-flak-gauntlet) *punishes* predictable flying, this **rewards
pressing the CAS run in on the deck**.

- **How it works — anchored to your real bombs.** The runtime watches each **Snakeye-class
  retarded-bomb release** made from a qualifying profile — **low** (below the release ceiling
  AGL, ~500 ft) and **fast** — then **tracks the weapons to impact** and blooms **one fire wall
  + a modest real bite at each actual impact point**. The wall of fire emerges from your real
  ripple: a dry pass lays nothing, and a miss burns exactly where it missed.
- **It only fires on a deliberate pass.** High or slow releases do nothing — you have to fly the
  profile. There's no aircraft gate at all: **the ordnance is the eligibility**, on either side.
  (Mk-77 real fire bombs are excluded — Splash Damage already renders actual napalm; no
  double-burn.)
- **AI flies it too.** Under Vietnam doctrine, AI CAS/BAI/Armed-Recon flights press their combat
  legs down to ~500 ft, inside the release gate — so the AI can nape its own targets (the flown
  confirmation of that AI leg is still owed).
- **Tunable** (plugin options): release ceiling, minimum release speed, the eligible-weapon name
  patterns, per-impact power.

---

## In-game pass status at a glance

Several of these are **runtime Lua that CI can't exercise** — they pass the syntax gate but need a
cockpit pass to confirm feel and behaviour. Current state:

| Feature | Status |
|---|---|
| Arc Light | ✅ Verified in the cockpit |
| Flak gauntlet | ✅ Verified (after two lethality-softening passes) |
| Naval gunfire | ☐ Untested — arms cleanly in flown sessions; the firing legs are unflown |
| Convoy interdiction | ◐ Partial — the flown trail leg passed (a real convoy hunted and killed by Armed Recon); the debrief loss-recording leg is the remaining check |
| Airbase harassment | ◐ Partial — the barrage cue + player-field exclusion confirmed; visual impact confirm owed |
| Super Gaggle | ◐ Partial — two clean flown runs; the squadron loss-accounting check (and the new launch delay) still owed |
| FAC(A) marking | ✅ Verified — the named F10 mark confirmed in a flown session |
| Snake and nape | ◐ Partial — the player leg verified exactly to the gate; the AI-flown leg owed |

If you fly any of the open legs, the biggest things to watch: airbase harassment must **never**
land on a player-spawn field; naval gunfire should do nothing on an inland map; a dead convoy's
units should never arrive at the front; and two lost gaggle suppressors should show up as real
squadron airframe losses at the next debrief.

## See also

- **[The Vietnam Campaign Layer](Vietnam-Campaign-Layer)** — the war *over* the war: political
  will, the Rolling Thunder → Linebacker II ROE arc, ambush MiGs, Alpha Strikes, and the enemy's
  phase-coupled tempo.
- **[Combat SAR](Combat-SAR)** and **[SCAR](SCAR)** — the Sandy/King rescue package, the other
  half of the Vietnam-era content.
- **[Troops In Contact](Troops-In-Contact)** — the frontline firefight sim the flak/convoy effects
  reuse for their fire plumbing.
- **[Lua Plugins](Lua-Plugins)** — where the per-feature tunables (burst power, carpet size,
  cadences) live as plugin options.
