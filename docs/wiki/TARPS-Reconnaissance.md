# TARPS Reconnaissance

In this fork, reconnaissance is a real job with a real payoff. Enemy sites can be on your map
without their composition, strength, or damage state being known, and a struck target keeps
showing alive until someone confirms the kill (see
[Fog of War and Reconnaissance](Fog-of-War-and-Reconnaissance)). **TARPS** is the player task
that resolves that uncertainty: an F-14 flies a photo-recon pass and what it photographs comes
back into the campaign as **confirmed intelligence**.

TARPS stands for the **Tactical Airborne Reconnaissance Pod System** — the real F-14 recon pod.
Here it is a dedicated flight type (`FlightType.TARPS`) backed by the **TARS** (Tactical Air
Recon System) runtime engine, which films what the jet overflies and feeds the results into the
campaign's battle-damage picture at debrief.

> **In-game-pass status:** TARS is **default ON** and code-complete, but the Lua can't run in CI
> so it still warrants a cockpit pass — confirm the F10 film menu unlocks with the shipped F-14
> TARPS payload, overfly a struck enemy site, land, and check the BDA map confirms exactly the
> photographed units.

---

## Why fly it

Two fog rules in the campaign make recon worth the sortie:

- **Battle-damage lag.** When you strike an enemy site, your map keeps showing those units alive
  until a recon pass confirms the kill. Without confirmation you are guessing whether the SAM
  you bombed is actually dead.
- **Recon intel-fog.** A newly-seen enemy site appears as a targetable marker — position,
  category, allegiance — but its unit types, counts, and threat/detection rings stay hidden until
  it is attacked, scouted, or has a unit destroyed.

A TARPS overflight is the clean way to lift both: photograph a site you just hit to confirm the
BDA, or photograph a freshly-discovered site to learn what is actually there before you commit a
strike package to it.

The AI planner and threat math always use full ground truth, so flying (or skipping) TARPS never
disadvantages the auto-planner — the fog is a **player-facing** information layer only.

---

## The aircraft and pod

All F-14 variants carry the `{F14-TARPS}` pod on station 6, fitted by the **Retribution TARPS**
payload. That payload pairs the pod with a per-variant self-defense fit (a mix of AIM-54/AIM-7
and AIM-9 wingtips depending on the variant) so the recon bird can defend itself but is not a
striker.

The TARPS jet is **weaponless against the ground by design**. Its flight plan uses a recon
ingress, not a strike ingress, so the AI doesn't get bombing tasks dumped on it — without that,
the AI would fly an aborting attack pattern and never cleanly cross the target. The target
waypoint is a **flyover**, so the jet actually overflies the site instead of turning back at the
ingress point.

> If you ever see the F10 film menu fail to unlock, it is almost always a stale weapon CLSID in
> the loadout — DCS rejects the whole payload and silently drops the pod with it. See
> [Custom Loadouts](Custom-Loadouts) for the CLSID-currency gotcha.

---

## Flying a TARPS pass

1. **Get tasked.** Either build a `FlightType.TARPS` package by hand, or let the auto-planner
   append one (below). The flight plan is a single overflight waypoint set roughly **5 minutes
   behind the strikers** so the photos catch the post-strike state.
2. **Overfly the target.** Cross the site at the planned waypoint — the pass is a flyover, not an
   attack run. TARS films ground and naval objects in the camera footprint (air contacts are not
   filmed).
3. **Land at a friendly base.** TARS processes the film during the **landing debrief** — you have
   to **recover the jet** for the intelligence to count. A photographed site whose jet never
   lands is not confirmed.
4. **Read the result.** Each photographed unit is resolved back to its site, and that site's
   confirmed battle-damage snaps to truth: the map now shows what is really alive or dead there.

The discipline is simple: **photograph it, then bring the film home.**

---

## Auto-planned TARPS follow-up

The auto-planner can append a single TARPS sortie to **Strike** and **DEAD** packages against
high-value targets (air defenses, factories, command posts, bridges), controlled by the
**`auto_add_tarps_recon`** setting (Campaign Doctrine, **default ON**):

- The recon bird overflies the target about 5 minutes behind the strikers for a post-strike BDA
  pass.
- It requires a **TARPS-capable squadron in range**. If none is available the recon flight is
  simply skipped — the strike is never scrubbed for lack of a recon escort.

This is what makes BDA mostly take care of itself on packages you would fly anyway: hit the SAM,
and the trailing F-14 confirms whether it actually died.

---

## The TARS engine (under the hood)

TARS is MOOSE's **Ops.TARS** module, vendored into the plugin set and driven by a 414th init
script. A few facts worth knowing:

- **It feeds confirmed BDA, not just "a flight overflew the target."** When TARS processes a
  captured object at the landing debrief, the bridge records that unit and its life value, and
  the campaign confirms battle damage for **exactly the units photographed**.
- **It runs in addition to** the legacy geometric overflight reveal, so turning the plugin off
  changes nothing about how TARPS behaves — the engine is purely additive.
- **It is filtered for a Retribution theater.** Two stock TARS defaults are overridden: the
  USA/USSR name filter (which Retribution unit names never match) is disabled, and the ammo
  whitelist is opened up (default) so the shipped F-14 TARPS payload doesn't get refused and lock
  the film menu.
- **Scoring/markers are coalition-local**, and there is an optional SRS readout.

## Settings reference

| Setting | Default | Effect |
|---|---|---|
| `auto_add_tarps_recon` | ON | Auto-planner appends a TARPS recon flight to Strike/DEAD packages against high-value targets, ~5 min behind the strikers |
| `recon_intel_fog` | ON | The intel-fog that TARPS lifts: enemy site composition hidden until scouted (see [Fog of War and Reconnaissance](Fog-of-War-and-Reconnaissance)) |
| TARS plugin | ON | The film-and-debrief engine that turns photos into confirmed BDA; off = plain geometric overflight reveal |

## See also

- [Fog of War and Reconnaissance](Fog-of-War-and-Reconnaissance)
- [Mission planning](Mission-planning)
- [Air Defense and the Air War](Air-Defense-and-the-Air-War)
- [Custom Loadouts](Custom-Loadouts)
