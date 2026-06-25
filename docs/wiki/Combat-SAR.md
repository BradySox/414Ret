# Combat SAR

Combat SAR (combat search and rescue) makes a downed pilot worth flying for. In stock
Retribution an ejection is a flat loss: the airframe is gone and the aviator is written off.
This fork turns that moment into a mission. When a **human** pilot ejects in the operating
area, you can launch a rescue — a CH-47 goes in, lands at the survivor, picks them up, and
flies them home. Deliver them to any friendly field and the campaign **spares that aviator at
debrief**: you still lose the jet, but the experienced pilot returns to the squadron instead of
being killed off.

It is a bespoke flight type (`FlightType.COMBAT_SAR`) built on the **MOOSE CSAR** runtime
engine, and it is **distinct** from the SCAR SOF-recovery `CSAR` task (see
[SOF and Commander Capture](SOF-and-Commander-Capture)) — though, as below, a Combat SAR helo
can also extract a stranded SOF team.

> **In-game-pass status:** the whole feature is built, wired, and passes CI, but it has **not
> yet had a cockpit pass**. Checklist rows G8–G13 and H2 are all currently UNTESTED. Treat it
> as flight-ready but unvalidated — everything below describes how it is built to work.

---

## The two roles: rescuer and King

Combat SAR is flown as a two-element idea, modeled on a real HC-130 + helo package. Both
elements are player-selectable when you build the package, and both fly a **support-style orbit
anchored on the front line** — the same FLOT-anchored racetrack that AWACS and tankers use, sat
behind the threat rings rather than over them.

| Element | Airframe | Role |
|---|---|---|
| **Rescuer** | **CH-47Fbl1** (the player-flyable ED Chinook) | Orbits near the FLOT behind the threat rings; flies in, lands, boards the survivor, and delivers them to any friendly field or FARP. Carries a door-gun fit (port + starboard M60D) for self-protection on the ingress. |
| **King** | **C-130J-30** | Flies the overhead **HC-130 "King"** on-scene-command orbit: lights the homing beacon and runs the survivor locator. It never lands at a crash site. |

An AI **CH-47D** is the fallback rescuer (no weapon stations). The King is *overhead presence and
command*, **not** a tanker — the C-130 cannot act as a DCS aerial-refueling tanker, and the
Chinook couldn't take fuel from it anyway, so the King role is deliberately never wired into the
refueling system.

Because the rescuer reuses the support-orbit flight plan, its loiter altitude is clamped to the
campaign's helicopter combat altitude automatically — you do not tune it.

---

## How a rescue works, step by step

1. A **human** pilot ejects in the area. The MOOSE CSAR engine catches the ejection event and
   spawns the downed pilot on the ground with a beacon. (It only reacts to **human** ejections
   and only to **ejections** — not AI, not ordinary crashes — unless the AI standing alert is
   on; see below.)
2. The **King** lights an **air-tracking TACAN** beacon. This is the single homing solution: it
   follows the King's moving orbit, and every rescue helo carries a TACAN receiver. (An ADF
   radio beacon was considered and deliberately dropped — MOOSE's radio beacon is fixed-point,
   so chasing a moving King with it would buy nothing over the TACAN.)
3. The King's crew can press an F10 **Combat SAR → LARS — Locate Survivors** button. LARS reads
   the live downed-pilot table and reports each active survivor nearest-first: position, plus
   bearing and range **from the King** — exactly the readout the crew relays to the helo.
4. The **CH-47** homes on the King's TACAN, flies to the survivor, lands (or hovers at the
   pickup height), boards them, and delivers them to a friendly field/FARP.

The whole pickup is driven through the helo's own F10 **CSAR** menu, which MOOSE adds to any
human helo in the mission. Plugin options let you tune the feel:

| Plugin option | Default | Effect |
|---|---|---|
| `autosmoke` | off | Auto-pop smoke at the survivor |
| `loadDistance` | 75 m | How close the helo must be to board the survivor |
| `rescueHoverHeight` | 20 m | Hover height that counts as a pickup if you don't land |
| `messageTime` | 15 s | How long CSAR radio messages stay on screen |

---

## Rescue scoring — the payoff

The point of a rescue is to save the pilot, so the loop closes inside the campaign model:

- When the helo **boards** a survivor, the engine records that pilot's **original ejected
  aircraft** (by the exact unit name DCS reports in its crash/kill event).
- On a successful **delivery to a friendly field**, those pilots are credited.
- At debrief, each credited pilot's loss is resolved so the **airframe is still attrited but the
  aviator survives** — the kill on that pilot is skipped.

Two properties make this safe:

- **You have to actually bring them home.** A rescue helo shot down with survivors aboard never
  reaches the delivery, so those pilots are never credited.
- **Fail-safe.** If nothing is rescued, the result is identical to today's behavior — the pilot
  dies. An empty rescue list is exactly the pre-scoring outcome.

See [Squadrons and Pilots](Squadrons-and-Pilots) for why keeping an experienced aviator matters
over a campaign.

---

## AI standing alert (optional)

By default Combat SAR is something you plan and fly. You can also enable an AI standing alert
with the **`auto_combat_sar`** setting (HQ automation page, **default OFF**). With it on:

- the planner auto-plans one Combat SAR orbit per turn for blue, ASAP, so the alert is up before
  the first losses; and
- the engine is told it may **commandeer an orbiting AI CH-47** to fly the pickup — which also
  makes **AI** ejections rescuable, not just human ones.

Airframe scarcity self-limits the alert: no CH-47 available, no orbit planned. Combat SAR is
**blue-only** — the engine is built for blue, so a red Combat SAR would just fly an inert orbit
and is never auto-tasked.

---

## Extracting a stranded SOF team

The same rescue helo can extract a stranded SCAR **SOF team** in-mission. When the SCAR
commander-capture feature is on and a team has been stranded by a botched grab, the generator
emits that on-map "downed SOF team" and the plugin spawns it as a MOOSE **CASEVAC** ground
pickup at its strand point. A Combat SAR helo boards and delivers it exactly like a downed
pilot, and the campaign credits the recovery — refunding the bought team.

This runs **alongside** the dedicated `FlightType.CSAR` air-assault recovery, not instead of it;
a team recovered by either path refunds only once. The pilot-sparing channel and the
SOF-recovery channel are kept distinct (routed by a `SOFRESCUE` name prefix) so there is no
double-counting and no double ejection-handling. See
[SOF and Commander Capture](SOF-and-Commander-Capture) for how teams get stranded in the first
place.

> With the AI alert on, an AI Combat SAR helo can be commandeered to extract a team too — and it
> *will* penetrate deep enemy territory to reach the strand, which is risky by design.

---

## Settings reference

| Setting / option | Default | Effect |
|---|---|---|
| `FlightType.COMBAT_SAR` | player-selectable | Plan a rescuer (CH-47) or King (C-130) orbit by hand |
| `auto_combat_sar` | OFF | AI standing alert: auto-plans a Combat SAR orbit per turn and makes AI ejections rescuable |
| King beacon | TACAN-only | Air-tracking TACAN the helo homes on; F10 LARS reports survivor positions |
| `loadDistance` / `rescueHoverHeight` / `autosmoke` / `messageTime` | 75 m / 20 m / off / 15 s | CSAR pickup feel (plugin options) |

## Tips

- **Put a King up if you can.** The helo can be rescued without one, but the TACAN homing and
  LARS readout make finding the survivor far less of a needle-in-a-haystack.
- **Bring escorts.** The rescuer orbits behind the rings but the pickup itself often pushes
  toward the fight; the door guns are for self-defense, not for clearing a hot LZ.
- **Deliver to the nearest friendly field or FARP** — `allowFARPRescue` is on, so you do not
  need a dedicated MASH; any friendly airfield/FARP scores the save.

## See also

- [SCAR](SCAR)
- [SOF and Commander Capture](SOF-and-Commander-Capture)
- [Squadrons and Pilots](Squadrons-and-Pilots)
- [Air Defense and the Air War](Air-Defense-and-the-Air-War)
- [Mission planning](Mission-planning)
