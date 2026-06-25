# Air Wing Configuration

Before you fly a single sortie, Retribution builds an *air wing* for your side: the squadrons,
aircraft, and bases that the campaign will spawn missions from. This page explains how that wing
is assembled, how you shape it, and what the 414Ret fork adds on top.

The air wing is decided by four things working together:

1. **The faction** you picked at new-game setup — it defines the pool of aircraft, helicopters,
   tankers, AWACS, ground units, and naval assets that are legal for your side.
2. **The campaign's preset squadrons** — most campaigns ship named squadrons (livery, country,
   capable task types) pinned to specific bases. If a needed slot has no preset, Retribution
   auto-generates a generic squadron to fill it.
3. **The control points you own** — each base, carrier, or FOB carries squadron slots tied to
   particular mission roles, and only aircraft suitable for that role can fill them.
4. **What you buy** — your budget and the available parking at each base cap how large the wing
   can grow.

## Squadrons, bases, and slots

Open a friendly base from the map to see its squadrons in the **Airfield Command** tab. Each base
exposes mission profiles appropriate to its infrastructure:

- **Airfields** host fast jets and support aircraft — BARCAP, SEAD/DEAD, Strike, AEW&C, refueling,
  and so on.
- **Carriers** add carrier-capable roles such as BARCAP, anti-ship, AEW&C, and refueling.
- **FOBs / FARPs** are heliport-only, so they carry CAS and Transport slots flown by helicopters.

When the planner needs a flight, it fills the slot in priority order: a specific squadron assigned
to that role first, then a specific preferred airframe, then any compatible aircraft from the
faction roster, and finally an auto-generated squadron if nothing else fits. Picking the right
squadrons up front keeps your packages flying the airframes you actually want.

## Buying aircraft and ground units

Add aircraft from a base's command panel with the **+** button. Purchases arrive **next turn**,
are limited by budget and parking, and can be cancelled before the turn rolls — but sales are
immediate and final. Remember you are equipping the whole faction's war, not just your own slot, so
buy to cover the missions you intend to plan: CAP/BARCAP, escort, SEAD/DEAD, Strike, CAS, and
support.

Ground units are recruited from **Ground Forces HQ**. On the first turn you can reinforce any
friendly control point; after that, ground recruitment is tied to control points with factories.
See [Turn Zero](Turn-Zero) for how the opening turn differs.

Auto-purchase can handle routine reinforcement for you so you only hand-buy the pieces you care
about. See the Auto Purchase settings on the new-game and turn screens.

## Fork specifics for 414Ret

414Ret keeps the upstream model above and layers a few squadron-level concerns on top:

- **QRA intercept reserve.** A squadron can hold part of its strength back as a quick-reaction
  alert reserve for runtime base defense instead of committing every airframe to the ATO. Plan for
  this when sizing fighter squadrons — see [Air Defense and the Air War](Air-Defense-and-the-Air-War).
- **Player-flyable task types need the right squadron.** The fork adds real player tasks that only
  certain airframes can perform, so make sure a suitable squadron exists if you want to fly them:
  - **TARPS** photo-recon — an F-14 squadron (feeds the recon intel system; see
    [Fog of War and Reconnaissance](Fog-of-War-and-Reconnaissance)).
  - **JAMMING** standoff EW/ISR — a C-130J squadron.
  - **SCAR** moving-target hunt and **Combat SAR** pilot rescue — strike-capable jets and the
    helo/C-130 rescue pairing respectively.

  See [Squadrons and Pilots](Squadrons-and-Pilots) for managing pilot rosters, and
  [Mission Planning](Mission-planning) for what each task actually does in the air.

## See also

- [Squadrons and Pilots](Squadrons-and-Pilots)
- [Turn Zero](Turn-Zero)
- [Your First Operation](Your-First-Operation)
- [Mission Planning](Mission-planning)
- [Air Defense and the Air War](Air-Defense-and-the-Air-War)
- [Fog of War and Reconnaissance](Fog-of-War-and-Reconnaissance)
