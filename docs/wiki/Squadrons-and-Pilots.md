# Squadrons and Pilots

Your air force is squadrons of pilots flying one aircraft type each. This page covers how the wing
is assembled, how you shape it, and how pilots are gained and lost.

---

## How the wing is assembled

Four things decide it:

1. **The faction** — the pool of aircraft, helicopters, tankers, AWACS, ground units and naval
   assets legal for your side.
2. **The campaign's preset squadrons** — most campaigns ship named squadrons (livery, country,
   capable tasks) pinned to bases. Unfilled slots get an auto-generated generic squadron.
3. **The control points you own** — each base carries squadron slots tied to mission roles, and
   only suitable aircraft can fill them.
4. **What you buy** — budget and parking cap how large the wing grows.

Open a friendly base from the map to see its squadrons in **Airfield Command**. Each base exposes
profiles matching its infrastructure:

- **Airfields** — fast jets and support: BARCAP, SEAD/DEAD, Strike, AEW&C, refuelling.
- **Carriers** — carrier-capable roles: BARCAP, anti-ship, AEW&C, refuelling.
- **FOBs and FARPs** — heliport-only: CAS and Transport, flown by helicopters.

When the planner fills a slot it tries, in order: a squadron assigned to that role, then a
preferred airframe, then any compatible aircraft from the faction roster, then an auto-generated
squadron. Picking squadrons up front keeps packages flying the airframes you want.

### Buying

Add aircraft from a base's command panel with **+**. Purchases arrive **next turn**, are limited by
budget and parking, and can be cancelled before the turn rolls — sales are immediate and final.

You are equipping the whole faction's war, not just your own slot, so buy to cover the missions you
intend to plan.

Ground units come from **Ground Forces HQ**. Auto-purchase handles routine reinforcement so you
hand-buy only what you care about.

### Squadrons you need for the fork's player tasks

- **TARPS** photo-recon — any TARPS-tagged airframe; the F-14 is the modern carrier of the role.
- **JAMMING** standoff EW/ISR — a C-130J squadron.
- **CSAR** pilot rescue — a helicopter squadron makes the pickup; fixed-wing cannot. A C-130J
  squadron can fly the *King* on-scene orbit, added to the package by hand.

---

## Pilots

Each aircraft on a mission has one assigned pilot from its squadron.

- **Experience.** AI pilots start at the campaign's base skill level and gain a skill increase
  roughly every four missions, climbing toward ace.
- **Loss.** A pilot can be killed when their aircraft is destroyed, removing them from the squadron.
- **Replacements.** Squadrons can auto-recruit each turn at a limited rate, up to a maximum
  (default 24 per squadron).
- **Leave.** Send a pilot on leave to keep them out of auto-assignment.

**Player pilots are named individuals, not anonymous slots.** By default a player pilot cannot be
killed — the aircraft is still lost. Toggleable in the difficulty settings. The auto-planner offers
never-assign-players, no preference, or prefer-player-pilots.

### A rescued pilot is spared

When a pilot ejects they spawn on the ground with a beacon. Recover them with a rescue helicopter
and deliver them to any friendly field and the campaign **spares the aviator at debrief** — you
still lose the jet, but the experienced crew returns to the squadron.

A veteran you would otherwise replace from scratch can be brought home, so recovering downed
players has real campaign value. See [Combat SAR](Combat-SAR).

---

## Squadron identity

- **Predefined squadrons** load from YAML: name, aircraft, roles, pilot names, and optional custom
  **radio presets** (intra-flight channels and frequencies) for consistent multiplayer comms.
- **Generated squadrons** get randomised names when an aircraft type has no preset for the faction.

### Per-squadron nation

On a multinational coalition each squadron spawns its air units under **its own DCS country**
rather than one shared faction country, so a mixed-nation side gets nation-specific voiceovers and
radio comms instead of one voice for everyone.

A `CountryAssigner` resolves the country per squadron, registers each nation on the coalition, and
enforces the DCS **one-country-per-coalition** rule — blue claims a country first, and a colliding
red squadron falls back to the red faction country. It is a no-op for single-nation factions.

**Pilot names follow the nation.** Each roster is generated from its own country's name pool — a
Greek squadron gets Greek names, an Iranian one Persian — falling back to the faction's locale for
unmapped or multinational countries, so generation never breaks.

### Named liveries

The **Germany – Red Tide** campaign replaces generic mismatched paint with named historical units
wearing matching liveries — GSFG and VVS regiments on the red side, 414th Joint Fighter Group units
on the blue side — so the air war stops spawning aircraft in liveries that do not fit the unit
flying them.

## See also

- [Combat SAR](Combat-SAR)
- [The Ground War](The-Ground-War)
- [Mission Planning](Mission-planning)
- [Air Defense and the Air War](Air-Defense-and-the-Air-War)
