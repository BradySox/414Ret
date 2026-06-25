<!-- 414Ret wiki: Mission planning. Modeled on the upstream DCS Retribution wiki
     page (same section order: Mission timing, Rendezvous planning, Unlimited fuel,
     Task types), reworked with the consolidated TOT-by-task offset table and one
     standardized per-task template grouped by family, and extended with the fork's
     player task types (TARPS, SCAR, Combat SAR, JAMMING). -->

# Mission planning

A **package** is a group of one or more flights all working toward the same goal, arriving at
a shared time-over-target. This page covers how packages are built, how the planner schedules
them, and what every task type actually does — both when you fly it and when the AI does.

For how 414Ret plans the wider air war around your packages — QRA, BARCAP layering, support
orbits, SEAD/DEAD reachability, and the IADS engine — see
[Air-Defense-and-the-Air-War](Air-Defense-and-the-Air-War).

## Packages and the auto-planner

Each turn the campaign's auto-planner builds an air tasking order (ATO) for both sides: it
picks targets, assembles packages, and selects airframes by capability and availability. You
can take any auto-planned package and edit it, delete it, or build your own from scratch.

A few things worth knowing before you frag:

- **Airframe selection is by capability**, not a fixed list. The "typical airframes" noted per
  task below are illustrative — the planner chooses from what your squadrons can actually
  field for that task.
- **Most non-CAP tasks request escorts automatically.** A strike or DEAD whose route passes
  through air-defence reach picks up SEAD/air-to-air escorts without you asking.
- **Opportunistic enemy targeting can be made unpredictable.** An opt-in, per-side doctrine
  knob (`ownfor_/opfor_planner_unpredictability`, default 0) varies which *opportunistic*
  offensive targets the enemy services first, so red stops hitting the same things in the same
  order every turn. Reactive threat response stays strictly deterministic — variety never
  delays a real defensive reaction. See
  [Air-Defense-and-the-Air-War](Air-Defense-and-the-Air-War).

# Mission timing

Each package has an assigned time-over-target (TOT). The event the TOT corresponds to
varies by task — for a strike it is weapons impact, for a CAP it is the start of the patrol.
The system schedules every other waypoint, takeoff sequence, and startup around that TOT, so
all flights in a package arrive at the target together.

The handling of delayed flights varies by flight composition and origin:

- AI shore-based flights spawn uncontrolled until mission start.
- Carrier-based AI flights activate late to reduce flight-deck congestion.
- Cold-start player flights from shore spawn uncontrolled; cockpit access is restricted until
  mission start.
- Other shore player start types spawn immediately.
- Player carrier flights spawn immediately.

The campaign settings include a **Never delay player flights** option for multiplayer
squadrons. This does not alter your mission time — it only lets you sit in the cockpit while
you wait.

For immediate mission generation, use the **ASAP** button next to the TOT field.

## Time-over-target by task

The TOT a flight is assigned is **not** always the moment its task occurs. Each task
interprets TOT differently, and several are deliberately offset from the package TOT so
coverage is established before the strikers arrive. The full set of rules, in one place:

| Task | TOT means… | Offset from package TOT | Notes |
|------|------------|-------------------------|-------|
| Strike | Weapons impact target | 0 (package TOT) | AI cannot be given exact impact timing; approximate. |
| DEAD | Weapons on target | 0 (package TOT) | Scores the kill the SEAD flight enables. |
| Anti-ship | Weapons released at IP | 0 (package TOT) | — |
| OCA/Aircraft | Attack run at field | 0 (package TOT) | — |
| OCA/Runway | Bomb run on runway | 0 (package TOT) | — |
| SEAD | Weapons/decoys at IP | **−3 min** | Fixed; arrives 3 min ahead so suppression is up before the package. |
| SEAD Escort | Matches escorted flight | follows package | Same plan as the flight it protects. |
| SEAD Sweep | Matches package route | **−2 min** | Engages route threats between Join and Split. |
| Escort | Matches package | 0 (join TOT shared) | Joins at the package join point. |
| Fighter sweep | Area cleared of fighters | **−5 min** | Sweeps ahead of the package toward the target. |
| TARCAP | On station | **−2 min (vs join)** | Poor choice near enemy SAMs — early arrival exposes it. |
| BARCAP | Patrol start | 0 (patrol begins at TOT) | 60 min default on-station (configurable 30–150), racetrack toward nearest enemy base. |
| CAS | Loiter / search start | 0 (patrol begins at TOT) | — |
| Armed Recon | Search start | 0 (patrol begins at TOT) | — |
| BAI | Weapons on target | 0 (package TOT) | Against a stationary armour group. |
| SCAR | On-station / search start | 0 (patrol-start) | Player hunt for a moving HVT; see [SCAR](SCAR). |
| TARPS | On-station / photo run start | 0 (patrol-start) | Player photo recon; see [Fog-of-War-and-Reconnaissance](Fog-of-War-and-Reconnaissance). |
| JAMMING | Standoff orbit start | 0 (orbit begins at TOT) | C-130J EW/ISR racetrack outside the threat zone; see [Electronic-Warfare-and-ISR](Electronic-Warfare-and-ISR). |
| Combat SAR | On-station / orbit start | 0 (patrol-start) | Player pilot-rescue; see [Combat-SAR](Combat-SAR). |
| Air Assault | Insert sequencing | n/a (helo plan) | Requires CTLD plugin. |
| Airlift | Transfer sequencing | n/a | CTLD creates pickup/dropoff zones for player flights only. |

**Hold:** every rendezvousing flight is planned with ~5 min of hold after the ascent point to
absorb takeoff delays, baked in before the join, independent of the offsets above.

# Rendezvous planning

Some task types add multiple waypoints for coordination:

A **hold point** follows the ascent point — climb to altitude and orbit until the assigned
departure time. This accommodates roughly five minutes of preparation time.

A **join point** enables package rendezvous, with a synchronised TOT across all flights heading
toward the target.

A **split point** follows egress, allowing flights to separate for return-to-base procedures.

# Unlimited fuel

Turning on unlimited fuel does not mean AI aircraft will never run out of fuel — that would
make air-to-air refuelling flights pointless.

AI aircraft maintain unlimited fuel (their fuel level cannot drop below 40%) from startup
through the Join waypoint, then revert to limited fuel until the Split waypoint, where
unlimited fuel reactivates. This prevents a premature RTB before ingress while avoiding
fuel-starvation during landing.

# Task types

Each task below uses the same field order so the page is scannable:

- **Purpose** — one line.
- **Valid targets** — what you can frag it against.
- **Package role** — lead (the reason the package exists) or support.
- **Typical airframes** — shown *only* where the airframe conveys a real capability constraint
  (e.g. anti-runway munitions, helicopter transport). The planner otherwise selects on
  capability and availability, so generic fighter lists are omitted.
- **TOT meaning** — what the assigned TOT actually triggers (see *Time-over-target by task*).
- **Player technique** — how a human flies it well.
- **AI limitations** — what to expect when the AI flies it.
- **IADS notes** — behaviour changes under the runtime IADS engine, where relevant
  (air-defence tasks). 414Ret defaults new campaigns to MANTIS; Skynet stays selectable, and
  existing saves keep their engine. Both shut radars down reactively, so the notes apply to
  either — see [Air-Defense-and-the-Air-War](Air-Defense-and-the-Air-War).

Tasks are grouped by family: Air-to-Air, Suppression (SEAD/DEAD), Air-to-Ground strike,
Battlefield support, and Support & logistics. The fork's player task types — SCAR, TARPS,
Combat SAR, and JAMMING — appear in their families with a link to their dedicated page.

## Air-to-Air

### BARCAP (Barrier CAP)

- **Purpose:** Prevent enemy aircraft from entering a friendly area.
- **Valid targets:** Any friendly objective area.
- **Package role:** Lead / standalone (does not request escorts).
- **TOT meaning:** Start of the patrol. Flies a racetrack oriented toward the nearest enemy
  airbase; 60 min default on-station (configurable 30–150 on the Campaign Doctrine page).
- **Player technique:** Hold the racetrack between the two patrol points; commit on threats
  inside the engagement zone and recover the CAP.
- **AI limitations:** Waypoints can look offset from the objective, but coverage is by
  engagement zone — verify with "Display Selected BARCAP Commit Range". 414Ret schedules
  BARCAP as overlapping, jittered, threat-weighted waves; see
  [Air-Defense-and-the-Air-War](Air-Defense-and-the-Air-War).

### TARCAP (Target-area CAP)

- **Purpose:** Localised fighter cover over an enemy objective for the package's benefit.
- **Valid targets:** Any enemy objective area.
- **Package role:** Support (covers escort-requesting members).
- **TOT meaning:** On station **2 min ahead of the package join**; on-station time is the
  doctrine CAP duration (~30 min in the stock doctrines).
- **Player technique:** Arrive early, sanitise the target area, stay between the package and
  the threat axis.
- **AI limitations:** Early arrival means it is a **poor choice near enemy SAMs** — the CAP
  gets exposed before the package even shows.

### Fighter sweep

- **Purpose:** Clear the target area of enemy fighters ahead of the package.
- **Valid targets:** Any enemy objective.
- **Package role:** Support (clears the path for the lead).
- **TOT meaning:** Area cleared **~5 min before** the package arrives.
- **Player technique:** Push to a point near the package join, then sweep toward the target
  killing fighters en route.
- **AI limitations:** RTBs when bingo, winchester, or on reaching the target area with no
  fighters found.

### Escort

- **Purpose:** Protect package members from aerial threats.
- **Valid targets:** n/a (defends a flight, not a target).
- **Package role:** Support (attaches to escort-requesting flights).
- **TOT meaning:** Matches the package (shared join TOT).
- **Player technique:** Stay with the escorted flight; defeat air threats without abandoning
  the package.
- **AI limitations:** Most non-CAP tasks request an escort automatically; escort engages air
  threats only.

## Suppression (SEAD / DEAD cluster)

Four suppression-adjacent tasks — the difference between them is the single most common source
of misfragged packages. Decision guide first.

### Choosing a suppression task

| You want to… | Use | Why |
|--------------|-----|-----|
| Kill a specific radar SAM at the package target | **DEAD** (usually + SEAD) | DEAD carries bombs/ATGMs to kill TELs/launchers, not just the emitter. |
| Keep a specific target's radar quiet so DEAD can kill it | **SEAD** | Suppression, not a kill — decoys or ARMs on the package target. |
| Protect one specific flight whose route runs through a SAM ring | **SEAD Escort** | Flies that flight's plan and reacts to defences threatening it. |
| Keep the whole route clear of *any* defences between join and split | **SEAD Sweep** | Engages any SAM/AAA near the path, not just the package target. |

Rule of thumb: **DEAD = kill the named site. SEAD = silence the named site. SEAD Escort =
guard a flight. SEAD Sweep = guard the corridor.**

In 414Ret, mobile short-range defences (SHORAD/AAA/MANPAD) are hidden from player datalinks,
while larger radar SAM sites (MERAD/LORAD) remain visible and targetable — so your SEAD/DEAD
planning is aimed at the sites that actually warrant a deliberate package. See
[Air-Defense-and-the-Air-War](Air-Defense-and-the-Air-War).

### SEAD

- **Purpose:** Suppress the package target's radar so the DEAD flight can kill it. Not a kill
  task.
- **Valid targets:** The package's target SAM (radar-guided).
- **Package role:** Support (paired with a DEAD lead).
- **Typical airframes:** HARM-capable types — the Viper's HTS and the Hornet are the usual SEAD
  platforms.
- **TOT meaning:** Weapons/decoys at the IP, **TOT −3 min** ahead of the package, so
  suppression is established before the strikers arrive.
- **Player technique:** Fire HARMs in **PB mode** so weapon TOT roughly aligns with package TOT
  even if the emitter is off. Stagger launches ~1 min apart; keep one HARM in flight near the
  site to hold suppression. With decoys the principle is identical — estimate the decoy's TOT.
- **AI limitations:** AI may kill the emitter incidentally but won't reliably finish the site —
  that's DEAD's job. In 414Ret the AI SEAD can loiter near the target, react to emitters, and
  break off on a computed timeline rather than making one inflexible pass.
- **IADS notes:** Sites shut radars down reactively, so HARMs are **less** likely to score
  emitter kills than against a dumb SAM. Plan SEAD as genuine suppression; let DEAD close the
  kill.

### DEAD

- **Purpose:** Destroy enemy air defences outright.
- **Valid targets:** Enemy air-defence sites; most effective against radar SAMs when paired with
  SEAD.
- **Package role:** **Lead** (the package exists to kill the site).
- **TOT meaning:** Weapons on target at the **package TOT**.
- **Player technique:** Ingress while the radar is held down by SEAD; target launchers/TELs and
  command vehicles that ARMs won't kill.
- **AI limitations:** Carries bombs/missiles rather than ARMs/decoys so it can destroy the
  non-emitting parts. Without SEAD support against a live radar SAM, expect losses. 414Ret's
  planner will **not** send the follow-on strike through a belt the DEAD can't actually reach —
  the strike is held until the SAM is genuinely down (DEAD reachability gate; see
  [Air-Defense-and-the-Air-War](Air-Defense-and-the-Air-War)).
- **IADS notes:** With emitters kept dark, the bomb/ATGM kill DEAD provides is often the *only*
  reliable way to remove the site — SEAD alone frequently won't.

### SEAD Escort

- **Purpose:** Protect a specific flight from air defences along its route.
- **Valid targets:** Defences that threaten the escorted flight's flight plan.
- **Package role:** Support (attached to a requesting flight).
- **TOT meaning:** Follows the escorted flight — same plan and timing.
- **Player technique:** Stay with the protected flight and prosecute any defence that comes up
  against it, rather than ranging ahead.
- **AI limitations:** Requested automatically when a flight plan passes within range of air
  defences; reactive to detected emitters only.
- **IADS notes:** Reactive suppression is degraded against radar shutdown — treat as
  deterrence, not a guaranteed clear.

### SEAD Sweep

- **Purpose:** Clear the package's corridor of any air defences between join and split.
- **Valid targets:** Any SAM or AAA near the flight path — not just the package target.
- **Package role:** Support (corridor protection for the whole package).
- **TOT meaning:** Follows the package route, arriving **2 min ahead** (TOT −2 min) to sweep
  the corridor before the package transits it.
- **Player technique:** Fly the route hunting threats — TOO in the Hornet, HTS in the Viper —
  and engage any emitter that begins to threaten the package. Broad-area counterpart to SEAD.
- **AI limitations:** Engages defences near the path between join and split; won't range
  off-route to hunt.
- **IADS notes:** Same reactive-suppression caveat as the other SEAD variants.

## Air-to-Ground strike

### Strike

- **Purpose:** Destroy fixed enemy ground targets.
- **Valid targets:** Static targets — buildings, infrastructure. Coordinates, not units.
- **Package role:** Lead.
- **Typical airframes:** Any strike-capable type; bombers for large/area targets.
- **TOT meaning:** Weapons impact at the **package TOT**.
- **Player technique:** Plan the attack so the weapon TOT matches the package; mind the
  coordinate-based nature — moving targets will not be there.
- **AI limitations:** Assigned coordinates, not units — **if the target moves the flight
  misses**. Usable against ground units only in poor weather where visual acquisition fails
  anyway, with non-optimal effect.

### Anti-ship

- **Purpose:** Sink or cripple enemy naval groups.
- **Valid targets:** Enemy ships.
- **Package role:** Lead.
- **Typical airframes:** Naval-strike-capable types.
- **TOT meaning:** Weapons released at the IP at the **package TOT**.
- **Player technique:** Mass weapons — **large numbers are usually needed to overwhelm point
  defences.** AI may split weapons across multiple ships.
- **AI limitations:** Fires at the IP, then RTBs; no reattack judgment.

### OCA/Aircraft

- **Purpose:** Destroy enemy aircraft on the ground.
- **Valid targets:** Enemy airfields (parked aircraft).
- **Package role:** Lead.
- **TOT meaning:** Attack run at the field at the **package TOT**.
- **Player technique:** Hit revetments/ramps; sequence with SEAD if the field is defended.
- **AI limitations:** Searches for and attacks grounded aircraft at the target field.

### OCA/Runway

- **Purpose:** Crater a runway to deny the airbase.
- **Valid targets:** Enemy runways.
- **Package role:** Lead.
- **Typical airframes:** Anything that can carry a 2000 lb bomb or dedicated anti-runway
  munitions (e.g. BLU-107).
- **TOT meaning:** Bomb run on the runway at the **package TOT**.
- **Player technique:** A **single 2000 lb bomb** (any type) kills a runway; dedicated
  anti-runway munitions always work with one hit. Lower-yield bombs may need several. Only one
  runway need be cut if the field has multiple.
- **AI limitations:** Lines up and bombs the runway. A dead runway shows in the debrief as a
  "dead" event with initiator "0". The field is unusable until repaired (4 turns / $100M).

## Battlefield support

### CAS (Close Air Support)

- **Purpose:** Support friendly ground forces at a front line.
- **Valid targets:** Targets within range of the front-line centre (right-click the front line
  to plan).
- **Package role:** Lead / standalone.
- **Typical airframes:** A-10-class types excel; any CAS-capable airframe works.
- **TOT meaning:** Loiter/search start. Searches until bingo or winchester.
- **Player technique:** Work the front-line area; coordinate with ground stance for effect. In
  414Ret the front is a prolonged, formation-aware firefight (Troops In Contact), so there are
  usually live engagements to support.
- **AI limitations:** **AI will not actively hunt** — it engages only what enters visual range,
  and is degraded in poor weather, so it may miss targets on the line.

### BAI (Battlefield Air Interdiction)

- **Purpose:** Eliminate a specific stationary enemy armour group behind the line.
- **Valid targets:** Ground-vehicle groups at enemy objective areas. **Convoy interdiction** is
  a subset — from the originating CP's *Departing Convoys* tab, click Attack, then build a
  package.
- **Package role:** Lead.
- **TOT meaning:** Weapons on the group at the **package TOT**.
- **Player technique:** Like CAS but against a known fixed group rather than troops in contact.
  BAI remains the normal planner task for conventional anti-armour work.
- **AI limitations:** Best against a stationary group; same visual-acquisition caveats apply.

### SCAR (Strike Coordination and Reconnaissance)

- **Purpose:** Find and kill a designated **moving** high-value target (HVT) in a defined area
  before it reaches safety (or, for a SCUD, its launch point).
- **Valid targets:** One HVT with a complete, recognisable signature, hidden among plain-truck
  clutter and partial-signature decoys. A real armour or missile site can become the moving
  objective instead of a disposable scripted stand-in.
- **Package role:** Lead / standalone; coordination with other flights is player-run.
- **TOT meaning:** Start of the on-station/search window (patrol-start).
- **Player technique:** Sweep the box, read convoy signatures, prosecute the HVT — and **don't
  hit the wrong convoy**: a mis-ID costs budget (tunable via the `SCAR mis-ID penalty` Campaign
  Doctrine setting). A fail clock runs as the HVT drives toward where it can no longer be
  struck.
- **AI limitations:** The find/ID/handoff judgment is a live-player capability; this is a player
  task. An opt-in `SCAR auto-planning` setting can frag it into your ATO automatically. See
  [SCAR](SCAR).

### Armed Recon

- **Purpose:** Mop up stragglers / engage targets of opportunity in a small radius.
- **Valid targets:** Any objective or enemy target; engages ground targets within a small
  defined radius.
- **Package role:** Lead / standalone.
- **TOT meaning:** Search start. RTBs if no targets found.
- **Player technique:** Useful after DEAD/BAI to clean up what's left.
- **AI limitations:** Effectiveness is weather-affected (like CAS); engages what's in the radius
  rather than hunting widely.

## Support & logistics

### TARPS (Tactical Airborne Reconnaissance)

- **Purpose:** Photograph enemy sites to bring back confirmed intelligence and battle-damage
  assessment.
- **Valid targets:** Enemy ground objectives within camera range along the recon track.
- **Package role:** Lead / standalone (player F-14 task). Strike and DEAD packages can receive
  an auto-planned TARPS follow-up.
- **TOT meaning:** Start of the on-station / photo-run window (patrol-start).
- **Player technique:** Overfly the assigned sites — what the aircraft photographs is carried
  back as confirmed intel, lifting the recon fog on composition, strength, and damage state.
- **AI limitations:** Driven at runtime by the TARS film-and-debrief engine; the value is in
  flying the pass yourself. See [Fog-of-War-and-Reconnaissance](Fog-of-War-and-Reconnaissance).

### JAMMING (Electronic warfare & ISR)

- **Purpose:** Standoff jamming and ELINT — the C-130J as an EC-130H/RC-130H-style EW + ISR
  platform.
- **Valid targets:** Area/directional/spot jamming against enemy emitters; ELINT tracking of
  radars within detection range.
- **Package role:** Lead / standalone.
- **Typical airframes:** C-130J (the only 414th scripted EW model — the old generic fighter-pod
  jammer is retired).
- **TOT meaning:** Start of the standoff orbit (an AWACS-style racetrack placed outside the
  threat zone).
- **Player technique:** Hold the standoff orbit; work the EW/ISR menus to jam, spoof missiles,
  and build ELINT tracks, then hand off the picture to a friendly group.
- **AI limitations:** Runtime EW/ISR is driven by the Lua, not the planner; the planner only
  places the standoff orbit and sets weapons-hold ROE. See
  [Electronic-Warfare-and-ISR](Electronic-Warfare-and-ISR).

### Combat SAR

- **Purpose:** Recover a downed pilot and return them to a friendly field.
- **Valid targets:** A downed (ejected) friendly pilot near the front line.
- **Package role:** Lead / standalone (player pilot-rescue task). A CH-47 orbits the FLOT as the
  rescuer; a C-130 flies the HC-130 "King" overhead orbit.
- **Typical airframes:** CH-47 (rescuer) + C-130 (King); helicopter recovery.
- **TOT meaning:** Start of the on-station / orbit window (patrol-start).
- **Player technique:** Home on the survivor's air-tracking TACAN, use the F10 survivor-locator
  readout, pick the pilot up, and deliver them to any friendly field — the campaign then
  **spares the aviator** (you still lose the jet).
- **AI limitations:** Player-flown, with an optional AI standing alert (`auto_combat_sar`,
  default off). Distinct from the SCAR SOF-recovery CSAR. See [Combat-SAR](Combat-SAR).

### Air Assault

- **Purpose:** Insert troops to capture an enemy control point.
- **Valid targets:** Enemy control points.
- **Package role:** Lead (helo).
- **Typical airframes:** Helicopter transports.
- **TOT meaning:** Insert sequencing (helo plan; no package offset).
- **Player technique:** Ensure the **drop-off waypoint sits inside the Assault Waypoint zone**
  or troops won't move to the target. From a carrier, troops load from the deck — no pickup leg.
- **AI limitations:** **Requires the CTLD plugin** for troop load/extract.

### Airlift (Transport)

- **Purpose:** Transfer a unit between points.
- **Valid targets:** n/a (logistics).
- **Package role:** Lead (transport).
- **Typical airframes:** Transport aircraft / helicopters.
- **TOT meaning:** Transfer sequencing.
- **Player technique:** Created from the Unit-transfer dialog (or auto-created when no convoy/
  ship route exists). **Check the actual pickup/drop-off waypoint positions** — with CTLD the
  zones are placed there. Zones generate for **player flights only**.
- **AI limitations:** AI does not use the CTLD-specific logic.

## See also

- [Air-Defense-and-the-Air-War](Air-Defense-and-the-Air-War) — how 414Ret plans the air war
  around your packages (QRA, BARCAP layering, support orbits, SEAD/DEAD reachability, IADS).
- [Fog-of-War-and-Reconnaissance](Fog-of-War-and-Reconnaissance) — recon fog, TARPS, and the
  overview reveal toggle.
- [SCAR](SCAR) — the moving-HVT hunt and the optional commander-capture / SOF path.
- [Combat-SAR](Combat-SAR) — the downed-pilot rescue loop.
- [Electronic-Warfare-and-ISR](Electronic-Warfare-and-ISR) — the C-130J JAMMING platform.
- [Getting-Started](Getting-Started) — first-campaign walkthrough.
- [Air-Wing-Configuration](Air-Wing-Configuration) — squadron and reserve setup.
