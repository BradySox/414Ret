# TARPS Reconnaissance

Enemy sites can sit on your map without their composition, strength or damage state being known,
and a struck target keeps showing alive until someone confirms the kill (see
[Fog of War and Reconnaissance](Fog-of-War-and-Reconnaissance)). **TARPS** is the player task that
resolves that: fly a photo-recon pass over the site and what you overfly comes back as confirmed
intelligence.

TARPS is the **Tactical Airborne Reconnaissance Pod System**, the real F-14 recon pod. Here it is
a flight type (`FlightType.TARPS`) driven by the `recon` plugin. The flight type is
**airframe-agnostic** — the F-14 is the modern carrier of the role, but any aircraft tagged with
the `TARPS` task can fly it.

---

## Why fly it

Two fog rules make recon worth the sortie:

- **Battle-damage lag.** After you strike a site your map keeps showing those units alive until a
  recon pass confirms the kill. Without it you are guessing whether the SAM you bombed died.
- **Recon intel-fog.** A newly-seen site appears as a marker — position, category, allegiance —
  but its unit types, counts and threat rings stay hidden until it is attacked, scouted, or has a
  unit destroyed.

Overfly a site you just hit to confirm the BDA, or a freshly-discovered one to learn what is
there before committing a strike package.

![An in-cockpit Threat Intel Brief kneeboard page listing enemy air defenses as "Unidentified AAA / LORAD / MERAD / SHORAD", each line tagged "fly TARPS recon to ID"](https://raw.githubusercontent.com/BradySox/414Ret/main/docs/wiki/img/kneeboard-recon-fog.jpg)

*Enemy air defences show as **Unidentified** with a "fly TARPS recon to ID" prompt until a pass
lifts the fog.*

The AI planner and threat math always use ground truth, so flying or skipping TARPS never
disadvantages the auto-planner. The fog is a player-facing layer only.

---

## Flying a pass

1. **Get tasked.** Build a `FlightType.TARPS` package by hand, or let the auto-planner append one
   (below).
2. **Overfly the target.** The target waypoint is a flyover, not an attack run. There is no menu
   and no film limit — crossing the site is what captures the take.
3. **Come home for the read-out.** The capture happens on the overfly, but the confirmation
   message is held until you land. The intelligence is already banked; landing is when you're
   told what you got.

A flight that is shot down or aborts before the pass confirms nothing.

### What shapes the take

- **Sensor.** A TARPS tasking reads a wider area than a drone's ball.
- **Altitude.** Full radius up to 20,000 ft, degrading to about 40% by 40,000 ft. A high, fast
  pass resolves less.
- **Weather.** Cloud cover from the campaign's own weather cuts what the cameras see. In rain or
  storms the auto-planner stops appending recon flights entirely.

**Drones are always filming.** Any drone banks what it overflies regardless of its tasking — solo
recon, JTAC overwatch on a strike, or CAS. A manned jet only films when actually tasked TARPS.

---

## The aircraft

All F-14 variants carry the `{F14-TARPS}` pod on station 6 via the **Retribution TARPS** payload,
paired with a self-defence fit so the recon bird can protect itself without being a striker. The
flight plan uses a recon ingress, not a strike ingress, so the AI doesn't get bombing tasks dumped
on it and turn back at the ingress point.

### Vietnam-era recon birds

Two dedicated period photo-recon aircraft fly TARPS as their **primary** job:

| Aircraft | Service | Notes |
|---|---|---|
| **RF-101B Voodoo** | USAF, land-based | Supersonic low-level photo recon |
| **RA-5C Vigilante** | US Navy, carrier-based | Carrier recon over Yankee Station |

Both are unarmed camera ships with built-in cameras rather than an external pod, so their TARPS
loadout is a clean weaponless fit. They keep a low-priority Armed Recon fallback so a squadron is
never stranded. **1968 Yankee Station** fields both — RF-101B at Da Nang, RA-5C on the carriers.

---

## Auto-planned recon

With **`auto_add_tarps_recon`** on (default), the planner appends a single TARPS sortie to
**Strike**, **DEAD** and **Armed Recon** packages against high-value targets.

- Behind a Strike or DEAD shooter it arrives **2 minutes later** for a post-strike BDA look.
- On an Armed Recon package it flies **with** the shooters — a find-and-overwatch pass, not a
  post-strike one.
- It needs a TARPS-capable squadron in range. If none is free the recon flight is skipped; the
  strike is never scrubbed for it.
- On a drone-fielding faction the recon bird *is* the drone, so Predators and Reapers ride along
  and bank BDA on everything they pass.
- The tag-along never paces the package — a slow drone riding a fast strike keeps its own
  schedule instead of dragging the formation down to its speed.

This makes BDA largely take care of itself on packages you'd fly anyway.

---

## Settings

| Setting | Default | Effect |
|---|---|---|
| `auto_add_tarps_recon` | ON | Planner appends a recon flight to Strike / DEAD / Armed Recon packages |
| `recon_intel_fog` | ON | The fog TARPS lifts — site composition hidden until scouted |
| `recon` plugin | ON | The runtime that banks an overflight as confirmed BDA |

## See also

- [Fog of War and Reconnaissance](Fog-of-War-and-Reconnaissance)
- [Mission planning](Mission-planning)
- [Air Defense and the Air War](Air-Defense-and-the-Air-War)
- [Custom Loadouts](Custom-Loadouts)
