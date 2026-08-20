# TARPS Reconnaissance

> **What TARPS is for: finding enemy command posts.** Ordinary enemy sites are already on your
> map, and their composition is revealed by engaging them, not by scouting — so a recon pass over
> one tells you nothing. Command posts are the exception: they are hidden outright, so there is
> nothing to put ordnance on until recon finds them. See
> [Fog of War and Reconnaissance](Fog-of-War-and-Reconnaissance).

TARPS is the **Tactical Airborne Reconnaissance Pod System**, the real F-14 recon pod. Here it is
a flight type (`FlightType.TARPS`). The flight type is **airframe-agnostic** — the F-14 is the
modern carrier of the role, but any aircraft tagged with the `TARPS` task can fly it.

---

## Flying a pass

1. **Get tasked.** Build a `FlightType.TARPS` package by hand, or let the auto-planner append one
   (below).
2. **Bring the flight home.** The find is credited if at least one aircraft of the recon flight
   survives the mission. A flight wiped out finds nothing.

At debrief, any hidden command post within about 3 NM of the **package's target** is revealed,
with a "RECON: enemy command post located" message. Nothing else about the area changes — an
un-engaged site's composition stays fogged whether you photographed it or not.

### What does not change the find

Altitude, speed, cloud cover and which sensor you carry make no difference, and there is no film
menu or per-sortie limit. The plugin that scored an overflight that way was removed in August
2026, once the reveal rules left it with nothing to feed.

Weather still matters one step earlier: in rain or storms the auto-planner stops appending recon
flights at all.

A drone can be fragged as the recon bird like any other TARPS-capable airframe, but a drone flying
some other tasking no longer contributes anything — the "a drone is always filming" rule went with
the plugin.

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

## See also

- [Fog of War and Reconnaissance](Fog-of-War-and-Reconnaissance)
- [Mission planning](Mission-planning)
- [Air Defense and the Air War](Air-Defense-and-the-Air-War)
- [Custom Loadouts](Custom-Loadouts)
