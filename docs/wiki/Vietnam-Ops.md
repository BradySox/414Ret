# Vietnam Ops

Opt-in period mechanics for the Vietnam air war, in two layers: **mission-level** effects inside a
generated mission, and a **campaign-level** doctrine that changes how the war is planned.

Retribution's taxonomy and threat model assume a SAM-and-MiG war. Vietnam was the opposite —
AAA-saturated, FAC-directed, B-52-and-helicopter-heavy, with naval gunfire, trail interdiction,
napalm CAS, and airbases under near-constant siege.

**Everything defaults OFF.** The Vietnam campaigns (1968 Yankee Station · Operation Velvet Thunder ·
Red Flag 81-2) pre-seed the relevant toggles through their `settings:` block. A modern or Cold-War
campaign sees none of it.

The underlying capabilities are era-flexible — flak, Arc Light, naval gunfire and convoy
interdiction work in any era — but the page name follows the framing.

> **New game required** for the campaign-layer half. Alpha Strikes, ambush MiGs, the fighter
> economy and the period planner ranges are baked in at campaign creation.

Pass status for every feature below is tracked in
[`docs/dev/414th-ingame-pass-checklist.md`](https://github.com/BradySox/414Ret/blob/main/docs/dev/414th-ingame-pass-checklist.md).

---

# Mission-level: the Ops suite

Python plans the geometry and force composition; the bundled `vietnamops` Lua plugin executes the
behaviour. Two features go deeper — **convoy interdiction** and the **Super Gaggle** plug into the
real force model, so the trucks you kill and the helos you lose are genuine campaign assets.

Each effect is symmetric by construction where that makes sense, though several are
blue-side in practice because only one coalition fields the unit — only OV-10 owners have FACs, the
gaggle draws from blue squadrons, and the trail is the enemy's road.

## 1 — Arc Light

Reframes the B-52 area strike as an **effect of the existing Strike task**, not a new mission type.

When a **heavy bomber** (B-52H, B-1B, Tu-95MS, Tu-142, Tu-160, Tu-22M3) flies a Strike, the runtime
walks a carpet of bombs across the target at the run-in instead of dropping a single aimpoint.
Inside ~8 NM it fires a one-shot walking box oriented along the bomber's bearing — rows stepping
along-track so it visibly walks, columns spreading it cross-track.

A tactical striker (F-4, A-4) on Strike is unaffected. Losses stay native: a bomber shot down
before the run-in never drops its carpet, and where the box overlaps real ground targets the damage
is real. Carpet length and width, per-blast power and release range are plugin options.

## 2 — AAA flak gauntlet

The real Vietnam threat was **AAA, not SAMs or MiGs**, and the engine's SAM/MEZ model barely
represents it. Fly within range and below the ceiling of an opposing AAA gun and you draw barrage
flak.

- **Nothing to frag.** The plugin discovers AAA at runtime by the DCS `AAA` unit attribute, so
  frontline ZSU-23 belts and airfield guns all contribute.
- **Predictability is punished.** Hold a steady heading and altitude and bursts creep from ~150 m
  off to ~70 m; a sustained straight-and-level run occasionally draws a close tracking round. Jink
  and vary altitude and it loosens right back off.
- **Symmetric.** Both sides' AAA flaks the other.

It is pressure to manoeuvre, not a hidden hard-kill SAM. The tuning has been softened twice after
reading as too lethal and is deliberately conservative; burst power and miss distances are plugin
options.

## 3 — Naval gunfire support

Offshore gun ships — New Jersey's 16″ batteries, plus cruisers, destroyers and frigates — deliver
shore bombardment. Two modes off the same gun-ship list:

- **Player call-for-fire.** Drop an F10 map marker, then **Naval Fire Mission → Fire on last F10
  map marker**. The nearest in-range friendly gun ship shells it, with a "SHOT" or "no ship in
  range" call back.
- **Automatic coastal bombardment.** On a cadence each gun ship shells the nearest opposing ground
  target within gun range.

**Coastal by construction.** Ships sit offshore and the range gate is ~20 km, so this reaches only
coastal targets and no-ops entirely inland — the historicity gate. Leave it off for inland
campaigns.

## 4 — Convoy interdiction (Steel Tiger)

A moving enemy supply column on the road behind the front, surfaced through **Armed Recon**. The
convoy is real: actual ground units, debited from a rear base, moving up the road corridors nearest
the front through Retribution's own convoy system.

- **A real trail.** Two concurrent columns of up to ~10 vehicles, three during a surge, spread
  across distinct roads where the map has them rather than stacked on one corridor. Columns are
  framed as external logistics — a source base is topped up with fresh whitelisted kit rather than
  draining a dead local economy.
- **Kill it and it matters.** Interdict the column and those units never reach the line. The kill
  records natively in the debrief; no bespoke scoring.
- **Right-click an enemy supply route** to open the package dialog with Armed Recon pre-selected.
  The flight plan sweeps the hunted road start-to-end rather than orbiting a point.

One documented no-op: **Velvet Thunder**, whose Marianas island geography has no roads between
enemy bases.

## 5 — Airbase harassment

Forward strips were under near-constant rocket, mortar and sapper standoff attack for years. In the
base engine an occupied airbase is a perfectly safe rear area until the front reaches it.

- **Which fields.** Only forward (within ~200 km of a front), occupied, land airfields and FARPs. A
  deep-rear field is never shelled.
- **Sporadic, not a metronome.** After a startup grace period each field takes a small scattered
  barrage near the parking area on a randomised cadence — mostly noise and smoke with a modest,
  tunable bite.

> **You are never shelled on your own ramp.** Any field a client flight spawns from, arrives at or
> diverts to is hard-excluded, enforced in Python and re-checked in Lua, and the grace period means
> nobody is shelled mid-alignment. Hard anti-grief guarantees, not options.

## 6 — Super Gaggle

The Khe Sanh "Super Gaggle": transport helos run supplies into a cut-off forward outpost while you
fly escort. **Drawn from your real squadrons, and its losses are real.**

- Each turn the engine picks the besieged blue FOB near a front, a rear launch field, a real blue
  helo squadron for the run and a real blue attack squadron for the AAA suppressors, and commits
  those exact airframes — once, no respawn loop.
- A helo shot down is a real airframe loss against its squadron at debrief. A delivered run credits
  the outpost a small ground-strength boost.
- The run launches on a **~10 minute delay** so a cold-starting escort can be airborne, the spawn
  cue announces it, and the lead helo carries a live F10 mark refreshed as it flies.

No friendly forward outpost near the front, or no helo squadron with airframes, and it quietly
stands down.

## 7 — FAC(A) willie-pete marking

An **OV-10 Bronco** loitering over the battle marks nearby enemy ground with white phosphorus so
strikers can visually acquire and roll in. The engine's ground JTAC stationarily *lases*; this is
the airborne smoke-marking half it does not cover.

With a friendly OV-10 airborne the plugin picks the **largest** enemy ground concentration in range
— not the nearest lone truck — drops white smoke on a cadence, and lays a named live F10 mark:
*"FAC(A): BTR-60 x6 — willie pete, cleared hot"*. The Bronco's own WP rockets make no mark, so the
mark is unambiguously the FAC's. No OV-10 airborne, nothing marked.

**Marking only.** It does not auto-assign the target to a CAS package.

## 8 — Snake and nape

Where the flak gauntlet punishes predictable flying, this **rewards pressing the CAS run in on the
deck**.

The runtime watches each **Snakeye-class retarded-bomb release** from a qualifying profile — below
the release ceiling (~500 ft AGL) and fast — then tracks the weapons to impact and blooms one fire
wall plus a modest real bite at each actual impact point. A dry pass lays nothing; a miss burns
exactly where it missed.

High or slow releases do nothing. There is no aircraft gate — **the ordnance is the eligibility**,
on either side. Mk-77 real fire bombs are excluded because Splash Damage already renders actual
napalm.

Under Vietnam doctrine AI CAS, BAI and Armed Recon flights press their combat legs to ~500 ft,
inside the release gate, so the AI napes its own targets. Release ceiling, minimum speed, weapon
name patterns and per-impact power are plugin options.

---

# Campaign-level: the doctrine layer

The war *over* the war — how the campaign plans, not what happens inside one mission.

## Your air war fights like 1968

- **Era taskings.** MiGCAP, GCI Intercept, Iron Hand, Interdiction, College Eye — the display layer
  renames taskings to the period vocabulary. The underlying mission types are unchanged.
- **No SEAD, and strikes go anyway.** Vietnam wings have no reliable defence suppression, so the
  modern suppress-before-you-strike rule is off: strikes press into defended areas and fly without
  a full escort rather than deadlocking the offensive fleet.
- **Knife-fight ranges.** Early Sparrows and short-range Sidewinders mean CAP and escorts engage at
  roughly 22/10 NM, not modern BVR standoff.
- **The real Alpha Strike.** The planner masses a deck-load on one target: up to **four coordinated
  strike sections sharing a time-on-target**, plus a forced fighter escort. Only the first section
  is guaranteed; the rest surge on as squadron inventory allows, so the top-priority target absorbs
  the strike fleet and later targets get the leftovers. Only a package massing ≥2 sections and ≥4
  bombers is named "Alpha Strike"; a lone section reads plain Strike. Strike sections are floored
  at 2 ships.
- **The fighter economy serves the bombers.** Rear support orbits fly unescorted — they hold
  stations the leashed MiGs cannot reach — and a fighter reserve is fenced for strike escorts.
  BARCAP thins from the coldest bases first, never the hottest, and non-strike packages cannot
  spend the last fighters.

## Red flies air defence, not your playbook

Red Vietnam factions run a dedicated **air-defence doctrine**: full MiGCAP stacks over their bases,
no massed strikes, no fighters wasted escorting raids the NVAF never flew.

**Ambush MiGs.** Red interceptors scramble **late** — raid ~40 NM out, not at the border — run a
close slashing intercept at knife-fight ranges, then break off and run home on a leash ~50 NM from
base plus an early fuel bingo. You get hit once, hard, near your target, by MiGs that live to
ambush again.

## Red tempo

A campaign can author a top-level **`red_tempo:`** schedule — a list of turn-windows, each opening
at a `from_turn`. The window in effect is the last whose `from_turn` has been reached, so tempo
escalates as the war drags on.

```yaml
red_tempo:
  - from_turn: 1
    name: Rolling Thunder
    trail_surge: 1.5
  - from_turn: 8
    name: The Bombing Halt
    trail_surge: 2.0
  - from_turn: 11
    name: Linebacker
    ground_offensive: 3
```

Two levers:

- **`trail_surge`** multiplies the trail-convoy budget and allows a second concurrent column while
  the window holds. A surged trail is more Armed Recon targets carrying real units — interdiction
  is the counter.
- **`ground_offensive: N`** raises RED's front stances to aggressive (never lowers them) for N
  turns from the window's opening, and the trail surges alongside at least 2.0×.

Only campaigns that author a schedule are affected; every entry point is a guarded no-op without
one. Six campaigns author it, including all three Vietnam ones.

> The layer originally carried a political-will economy, a static front and a Rolling Thunder →
> Linebacker ROE arc that gated what you could hit. **All three were removed 2026-07-21**, along
> with the `will:`, `phases:` and zone blocks that authored them. Red tempo and the GCI ambush
> posture are what survive.

---

## Practical notes

- **Turning it off.** Each piece has its own toggle on the Vietnam Ops settings page. Toggling
  mid-campaign is safe; the layer arms and disarms cleanly.
- **New Game.** The wizard's **Vietnam** card filters the campaign list to the era, and selecting a
  Vietnam campaign pre-seeds the Ops and campaign-layer toggles in one step.
- **Watch your losses, not just your kills.** Squadrons are finite and a captured pilot stops
  flying, so rescue sorties and trail interdiction are strategic acts here.

## See also

- [Combat SAR](Combat-SAR)
- [Troops In Contact](Troops-In-Contact) — the firefight sim the flak and convoy effects reuse
- [Lua Plugins](Lua-Plugins) — where the per-feature tunables live
- [Air Defense and the Air War](Air-Defense-and-the-Air-War)
