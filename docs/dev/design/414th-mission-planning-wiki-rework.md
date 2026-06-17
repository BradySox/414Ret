# Mission Planning — Task Types (Full Rework Draft)

> Draft for a wiki PR against `dcs-retribution/dcs-retribution`, replacing the **Mission
> timing** and **Task types** content on the *Mission planning* page. Every task uses one
> standardized template so the page is scannable and gaps are obvious.
>
> **Airframe lists are *typical auto-planner picks*, not guarantees** — the planner selects on
> capability and availability. Decide before PR whether maintainers want these kept or cut.

---

## 1. Consolidated TOT offsets

The TOT a flight is assigned is **not** the same as the moment its task occurs. Each task
interprets TOT differently, and several are deliberately offset from the package TOT so
coverage is established before the strikers arrive. These rules are otherwise scattered across
individual entries; collected here.

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
| Air Assault | Insert sequencing | n/a (helo plan) | Requires CTLD plugin. |
| Airlift | Transfer sequencing | n/a | CTLD creates pickup/dropoff zones for player flights only. |
| *SCAR (proposed)* | *On-station / search start* | *0 (patrol-start)* | *See §6 — not yet implemented.* |

**Hold:** every rendezvousing flight is planned with ~5 min of hold after the ascent point to
absorb takeoff delays, baked in before the join, independent of the offsets above.

---

## 2. Standardized task entry template

Every entry uses the same field order:

- **Purpose** — one line.
- **Valid targets** — what you can frag it against.
- **Package role** — lead (the reason the package exists) or support.
- **Typical airframes** — usual auto-planner picks; not authoritative.
- **TOT meaning** — what the assigned TOT actually triggers (cross-ref §1).
- **Player technique** — how a human flies it well.
- **AI limitations** — what to expect when the AI flies it.
- **Skynet notes** — behavior changes under Skynet IADS, where relevant (air-defense tasks only).

Tasks are grouped by family: Air-to-Air, Suppression (SEAD/DEAD), Air-to-Ground Strike,
Battlefield Support, and Support/Logistics.

---

## 3. Air-to-Air tasks

### 3.1 BARCAP (Barrier CAP)

- **Purpose:** Prevent enemy aircraft from entering a friendly area.
- **Valid targets:** Any friendly objective area.
- **Package role:** Lead / standalone (does not request escorts).
- **Typical airframes:** F-15C, F-16C, F/A-18C, F-14.
- **TOT meaning:** Start of the patrol (§1). Flies a racetrack oriented toward the nearest
  enemy airbase; 60 min default on-station (configurable 30–150 on the Campaign Doctrine page).
- **Player technique:** Hold the racetrack between the two patrol points; commit on threats
  inside the engagement zone and recover the CAP.
- **AI limitations:** Waypoints can look offset from the objective but coverage is by
  engagement zone — verify with "Display Selected BARCAP Commit Range".

### 3.2 TARCAP (Target-area CAP)

- **Purpose:** Localized fighter cover over an enemy objective for the package's benefit.
- **Valid targets:** Any enemy objective area.
- **Package role:** Support (covers escort-requesting members).
- **Typical airframes:** F-15C, F-16C, F/A-18C, F-14.
- **TOT meaning:** On station **2 min ahead of the package join** (§1); on-station time is the
  doctrine CAP duration (~30 min in the stock doctrines).
- **Player technique:** Arrive early, sanitize the target area, stay between the package and
  the threat axis.
- **AI limitations:** Early arrival means **poor choice near enemy SAMs** — the CAP gets
  exposed before the package even shows.

### 3.3 Fighter sweep

- **Purpose:** Clear the target area of enemy fighters ahead of the package.
- **Valid targets:** Any enemy objective.
- **Package role:** Support (clears the path for the lead).
- **Typical airframes:** F-15C, F-16C, F/A-18C, F-14.
- **TOT meaning:** Area cleared **~5 min before** the package arrives (§1).
- **Player technique:** Push to a point near the package join, then sweep toward the target
  killing fighters en route.
- **AI limitations:** RTBs when bingo, winchester, or on reaching the target area with no
  fighters found.

### 3.4 Escort

- **Purpose:** Protect package members from aerial threats.
- **Valid targets:** n/a (defends a flight, not a target).
- **Package role:** Support (attaches to escort-requesting flights).
- **Typical airframes:** F-15C, F-16C, F/A-18C, F-14.
- **TOT meaning:** Matches the package (shared join TOT).
- **Player technique:** Stay with the escorted flight; defeat air threats without abandoning
  the package.
- **AI limitations:** Most non-CAP tasks request an escort automatically; escort engages air
  threats only.

---

## 4. Suppression tasks (SEAD / DEAD cluster)

Four suppression-adjacent tasks — the difference between them is the single most common source
of misfragged packages. Decision guide first.

### 4.1 Choosing a suppression task

| You want to… | Use | Why |
|--------------|-----|-----|
| Kill a specific radar SAM at the package target | **DEAD** (usually + SEAD) | DEAD carries bombs/ATGMs to kill TELs/launchers, not just the emitter. |
| Keep a specific target's radar quiet so DEAD can kill it | **SEAD** | Suppression, not a kill — decoys or ARMs on the package target. |
| Protect one specific flight whose route runs through a SAM ring | **SEAD Escort** | Flies that flight's plan and reacts to defenses threatening it. |
| Keep the whole route clear of *any* defenses between join and split | **SEAD Sweep** | Engages any SAM/AAA near the path, not just the package target. |

Rule of thumb: **DEAD = kill the named site. SEAD = silence the named site. SEAD Escort =
guard a flight. SEAD Sweep = guard the corridor.**

### 4.2 SEAD

- **Purpose:** Suppress the package target's radar so the DEAD flight can kill it. Not a kill task.
- **Valid targets:** The package's target SAM (radar-guided).
- **Package role:** Support (paired with a DEAD lead).
- **Typical airframes:** F-16C (HTS), F/A-18C, F-15E.
- **TOT meaning:** Weapons/decoys at the IP, **TOT −3 min** ahead of the package (§1), so suppression is established before the strikers arrive.
- **Player technique:** Fire HARMs in **PB mode** so weapon TOT roughly aligns with package TOT even if the emitter is off. Stagger launches ~1 min apart; keep one HARM in flight near the site to hold suppression. With decoys the principle is identical — estimate the decoy's TOT.
- **AI limitations:** AI may kill the emitter incidentally but won't reliably finish the site — that's DEAD's job.
- **Skynet notes:** Sites shut radars down reactively under Skynet, so HARMs are **less** likely to score emitter kills than against vanilla SAMs. Plan SEAD as genuine suppression; let DEAD close the kill.

### 4.3 DEAD

- **Purpose:** Destroy enemy air defenses outright.
- **Valid targets:** Enemy air defense sites; most effective against radar SAMs when paired with SEAD.
- **Package role:** **Lead** (the package exists to kill the site).
- **Typical airframes:** F/A-18C, F-16C, F-15E carrying bombs/ATGMs.
- **TOT meaning:** Weapons on target at the **package TOT** (§1).
- **Player technique:** Ingress while the radar is held down by SEAD; target launchers/TELs and command vehicles that ARMs won't kill.
- **AI limitations:** Carries bombs/missiles rather than ARMs/decoys so it can destroy the non-emitting parts. Without SEAD support against a live radar SAM, expect losses.
- **Skynet notes:** Skynet keeps emitters dark, so the bomb/ATGM kill DEAD provides is often the *only* reliable way to remove the site — SEAD alone frequently won't.

### 4.4 SEAD Escort

- **Purpose:** Protect a specific flight from air defenses along its route.
- **Valid targets:** Defenses that threaten the escorted flight's flight plan.
- **Package role:** Support (attached to a requesting flight).
- **Typical airframes:** F-16C (HTS), F/A-18C.
- **TOT meaning:** Follows the escorted flight — same plan and timing.
- **Player technique:** Stay with the protected flight and prosecute any defense that comes up against it, rather than ranging ahead.
- **AI limitations:** Requested automatically when a flight plan passes within range of air defenses; reactive to detected emitters only.
- **Skynet notes:** Reactive suppression is degraded against Skynet (shutdown) — treat as deterrence, not a guaranteed clear.

### 4.5 SEAD Sweep

- **Purpose:** Clear the package's corridor of any air defenses between join and split.
- **Valid targets:** Any SAM or AAA near the flight path — not just the package target.
- **Package role:** Support (corridor protection for the whole package).
- **Typical airframes:** F-16C (HTS), F/A-18C (TOO).
- **TOT meaning:** Follows the package route, arriving **2 min ahead** (TOT −2 min) to sweep the corridor before the package transits it.
- **Player technique:** Fly the route hunting threats — TOO in the Hornet, HTS in the Viper — and engage any emitter that begins to threaten the package. Broad-area counterpart to SEAD.
- **AI limitations:** Engages defenses near the path between join and split; won't range off-route to hunt.
- **Skynet notes:** Same reactive-suppression caveat as the other SEAD variants.

---

## 5. Air-to-Ground strike tasks

### 5.1 Strike

- **Purpose:** Destroy fixed enemy ground targets.
- **Valid targets:** Static targets — buildings, infrastructure. Coordinates, not units.
- **Package role:** Lead.
- **Typical airframes:** F/A-18C, F-16C, F-15E, A-10C; bombers for area targets.
- **TOT meaning:** Weapons impact at the **package TOT** (§1).
- **Player technique:** Plan the attack so the weapon TOT matches the package; mind the
  coordinate-based nature — moving targets will not be there.
- **AI limitations:** Assigned coordinates, not units — **if the target moves the flight
  misses**. Usable against ground units only in poor weather where visual acquisition fails
  anyway, with non-optimal effect.

### 5.2 Anti-ship

- **Purpose:** Sink or cripple enemy naval groups.
- **Valid targets:** Enemy ships.
- **Package role:** Lead.
- **Typical airframes:** F/A-18C, F-16C, naval-strike-capable types.
- **TOT meaning:** Weapons released at the IP at the **package TOT** (§1).
- **Player technique:** Mass weapons — **large numbers are usually needed to overwhelm point
  defenses.** AI may split weapons across multiple ships.
- **AI limitations:** Fires at the IP, then RTBs; no reattack judgment.

### 5.3 OCA/Aircraft

- **Purpose:** Destroy enemy aircraft on the ground.
- **Valid targets:** Enemy airfields (parked aircraft).
- **Package role:** Lead.
- **Typical airframes:** F/A-18C, F-16C, F-15E, A-10C.
- **TOT meaning:** Attack run at the field at the **package TOT** (§1).
- **Player technique:** Hit revetments/ramps; sequence with SEAD if the field is defended.
- **AI limitations:** Searches for and attacks grounded aircraft at the target field.

### 5.4 OCA/Runway

- **Purpose:** Crater a runway to deny the airbase.
- **Valid targets:** Enemy runways.
- **Package role:** Lead.
- **Typical airframes:** F-15E, F/A-18C, bombers; anything that can carry 2000 lb / anti-runway munitions.
- **TOT meaning:** Bomb run on the runway at the **package TOT** (§1).
- **Player technique:** A **single 2000 lb bomb** (any type) kills a runway; dedicated
  anti-runway munitions (BLU-107) always work with one hit. Lower-yield bombs may need
  several. Only one runway need be cut if the field has multiple.
- **AI limitations:** Lines up and bombs the runway. A dead runway shows in the debrief as a
  "dead" event with initiator "0". Field is unusable until repaired (4 turns / $100M).

---

## 6. Battlefield support tasks

### 6.1 CAS (Close Air Support)

- **Purpose:** Support friendly ground forces at a front line.
- **Valid targets:** Targets within range of the front-line center (right-click the front line to plan).
- **Package role:** Lead / standalone.
- **Typical airframes:** A-10C, F/A-18C, F-16C, AH-64D.
- **TOT meaning:** Loiter/search start (§1). Searches until bingo or winchester.
- **Player technique:** Work the front-line area; coordinate with ground stance for effect.
- **AI limitations:** **AI will not actively hunt** — it engages only what enters visual
  range, and is degraded in poor weather, so it may miss targets on the line.

### 6.2 BAI (Battlefield Air Interdiction)

- **Purpose:** Eliminate a specific stationary enemy armour group behind the line.
- **Valid targets:** Ground-vehicle groups at enemy objective areas. **Convoy interdiction** is
  a subset — from the originating CP's *Departing Convoys* tab, click Attack, then build a
  package.
- **Package role:** Lead.
- **Typical airframes:** A-10C, F/A-18C, F-16C, F-15E.
- **TOT meaning:** Weapons on the group at the **package TOT** (§1).
- **Player technique:** Like CAS but against a known fixed group rather than troops in contact.
- **AI limitations:** Best against a stationary group; same visual-acquisition caveats apply.

### 6.3 Armed Recon

- **Purpose:** Mop up stragglers / engage targets of opportunity in a small radius.
- **Valid targets:** Any objective or enemy target; engages ground targets within a small
  defined radius.
- **Package role:** Lead / standalone.
- **Typical airframes:** A-10C, F/A-18C, F-16C.
- **TOT meaning:** Search start (§1). RTBs if no targets found.
- **Player technique:** Useful after DEAD/BAI to clean up what's left.
- **AI limitations:** Effectiveness is weather-affected (like CAS); engages what's in the
  radius rather than hunting widely.

---

## 7. Support & logistics tasks

### 7.1 Air Assault

- **Purpose:** Insert troops to capture an enemy control point.
- **Valid targets:** Enemy control points.
- **Package role:** Lead (helo).
- **Typical airframes:** UH-1H, Mi-8, helo transports.
- **TOT meaning:** Insert sequencing (helo plan; no package offset).
- **Player technique:** Ensure the **drop-off waypoint sits inside the Assault Waypoint zone**
  or troops won't move to the target. From a carrier, troops load from the deck — no pickup leg.
- **AI limitations:** **Requires the CTLD plugin** for troop load/extract.

### 7.2 Airlift (Transport)

- **Purpose:** Transfer a unit between points.
- **Valid targets:** n/a (logistics).
- **Package role:** Lead (transport).
- **Typical airframes:** C-130-class / helo transports.
- **TOT meaning:** Transfer sequencing.
- **Player technique:** Created from the Unit-transfer dialog (or auto-created when no convoy/
  ship route exists). **Check the actual pickup/drop-off waypoint positions** — with CTLD the
  zones are placed there. Zones generate for **player flights only**.
- **AI limitations:** AI does not use the CTLD-specific logic.

---

## 8. Proposed: SCAR (Strike Coordination and Reconnaissance)

> **Not yet implemented.** Full design + integration work exists separately as
> `SCAR-concept-v2.md` (SME-approved) and `SCAR-task-spec.md` (formal spec). This is the
> wiki-facing summary; roll it into the live page only once the task ships.

### 8.1 What it is

A flight works a defined area to **find and prosecute a single moving high-value target (HVT)
hidden among clutter and light threats**, before the HVT reaches a location where it can no
longer be struck. The skill is *discrimination* — picking the right target out of the noise —
not a free-fire sweep. It sits between CAS (needs troops in contact), BAI (preplanned known
group), and Armed Recon (small-radius targets of opportunity).

### 8.2 Entry (template form — provisional)

- **Purpose:** Find and kill a designated moving HVT in a defined area before it reaches a no-strike location.
- **Valid targets:** One HVT with a complete, recognizable signature (e.g. SA-9 + command + 2 support trucks), among plain-truck clutter and ≤2 partial-signature decoys.
- **Package role:** Lead / standalone; coordination with other flights is player-run.
- **Typical airframes:** A-10C primary; F/A-18C, F-16C, F-15E secondary.
- **TOT meaning:** Start of the on-station/search window (patrol-start, §1); 15–30 min scaled by airframe (shorter fast jets, longer A-10).
- **Player technique:** Sweep the ~10×10 mi box, read convoy signatures, prosecute the HVT; pass talk-ons to other flights as desired. Fail clock runs as the HVT drives to its no-strike zone.
- **AI limitations:** Engages via existing tasking only; **no AI discrimination or handoff** — the find/ID judgment is a live-player capability. Weather-degraded like CAS.

### 8.3 Why it's "lite"

A true FAC-A SCAR with AI target handoff isn't feasible — DCS AI can't dynamically pass targets
across packages. The generator produces only the search-and-engage behavior plus the scenario
(HVT/clutter/decoys/threat/movement/fail); coordination stays with the player.

### 8.4 Rollability

This entry drops into §6 (Battlefield support) once implemented. Until then it lives here as a
proposal so the page stays accurate. Implementation, MOOSE wiring, and phased build are in
`SCAR-task-spec.md` — including that in **Phase 1–2 the player hand-builds the package** (it is
not auto-fragged), and only at **Phase 3** does it appear in the ATO automatically.

---

## 9. Notes for the PR

- Decide the **airframe-list policy** (keep as "typical" vs. cut for airframe-agnostic).
- The SCAR section (§8) should **not** ship to the live wiki until the task is implemented —
  keep it in the PR description or a "proposed" branch of the page, not the task list proper.
- The TOT table (§1) and standardized template (§2) are the highest-value changes and can ship
  independently of any SCAR work.
