# TARPS Reconnaissance

> **TARPS currently banks no intelligence.** As of the 2026-08-18 recon rework, a site's fog is
> lifted by engaging it — ordnance on it, or a ground-attack sortie that reaches it — and a recon
> overflight reveals nothing. See
> [Fog of War and Reconnaissance](Fog-of-War-and-Reconnaissance).
>
> The flight type, the aircraft, the pod fits and the runtime all still work: you can task a
> TARPS pass, fly it, and the plugin still records what you photographed. Nothing in the campaign
> reads that record. Whether TARPS keeps a mechanical job is an open question.

TARPS is the **Tactical Airborne Reconnaissance Pod System**, the real F-14 recon pod. Here it is
a flight type (`FlightType.TARPS`) driven by the `recon` plugin. The flight type is
**airframe-agnostic** — the F-14 is the modern carrier of the role, but any aircraft tagged with
the `TARPS` task can fly it.

---

## Flying a pass

1. **Get tasked.** Build a `FlightType.TARPS` package by hand, or let the auto-planner append one
   (below).
2. **Overfly the target.** The target waypoint is a flyover, not an attack run. There is no menu
   and no film limit — crossing the site is what captures the take.
3. **Come home for the read-out.** The capture happens on the overfly; the confirmation message
   is held until you land.

A flight that is shot down or aborts before the pass records nothing.

### What shapes the take

- **Sensor.** A TARPS tasking reads a wider area than a drone's ball.
- **Altitude.** Full radius up to 20,000 ft, degrading to about 40% by 40,000 ft. A high, fast
  pass resolves less.
- **Weather.** Cloud cover from the campaign's own weather cuts what the cameras see. In rain or
  storms the auto-planner stops appending recon flights entirely.

**Drones are always filming.** Any drone records what it overflies regardless of its tasking —
solo recon, JTAC overwatch on a strike, or CAS. A manned jet only films when actually tasked
TARPS.

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

- Behind a Strike or DEAD shooter it arrives **2 minutes later**.
- On an Armed Recon package it flies **with** the shooters — a find-and-overwatch pass, not a
  post-strike one.
- It needs a TARPS-capable squadron in range. If none is free the recon flight is skipped; the
  strike is never scrubbed for it.
- On a drone-fielding faction the recon bird *is* the drone, so Predators and Reapers ride
  along.
- The tag-along never paces the package — a slow drone riding a fast strike keeps its own
  schedule instead of dragging the formation down to its speed.

---

## Settings

| Setting | Default | Effect |
|---|---|---|
| `auto_add_tarps_recon` | ON | Planner appends a recon flight to Strike / DEAD / Armed Recon packages |
| `recon` plugin | ON | The runtime that scores an overflight. Its output is currently unused |

## See also

- [Fog of War and Reconnaissance](Fog-of-War-and-Reconnaissance)
- [Mission planning](Mission-planning)
- [Air Defense and the Air War](Air-Defense-and-the-Air-War)
- [Custom Loadouts](Custom-Loadouts)
