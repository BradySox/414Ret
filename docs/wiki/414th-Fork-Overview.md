# What's Different in the 414th Fork

414Ret is the 414th Joint Fighter Group's build of DCS Retribution. Everything upstream does
still works; this page maps what the fork adds, with links to the full pages.

If you have never used Retribution, read [Getting Started](Getting-Started) first — this page
assumes you know the turn loop.

The build tracks upstream's `dev` branch plus the 414th feature set and selected upstream fixes.
Windows releases publish automatically to the rolling
[latest build](https://github.com/BradySox/414Ret/releases/tag/latest).

---

## Recon and intelligence

Upstream shows you the enemy laydown. The fork fogs it.

- Enemy sites can be known without their composition, strength, damage state or threat rings
  being known. Scouting or attacking reveals them; confirmed battle damage can require a
  surviving recon pass.
- Unscouted mobile forces draw a dashed circle offset from their true position instead of an
  exact marker. Fixed infrastructure stays exact.
- [TARPS](TARPS-Reconnaissance) is a player task — the F-14 plus the Vietnam-era RF-101B Voodoo
  and RA-5C Vigilante. Recon is automatic on overfly: fly the profile over the target and the
  take is banked as confirmed intelligence. Drones film whatever they overfly regardless of
  their tasking.
- Optional **Approximate target area** mode removes perfect coordinates and offsets steerpoints,
  so visual acquisition and talk-ons matter. Mobile short-range defences are kept off player
  datalinks; larger SAM sites stay visible for deliberate SEAD/DEAD.
- **Reveal fog of war (overview)** in the map layers panel shows ground truth. It is a view
  toggle only — never saved, never changes the campaign, and never leaks into a generated
  mission.

Full detail: [Fog of War and Reconnaissance](Fog-of-War-and-Reconnaissance).

---

## Squadron missions

- [Combat SAR](Combat-SAR) and the [SCAR "Sandy"](SCAR) escort. Recovering a downed aviator
  spares the pilot; you still lose the jet. You can plan the package yourself (King + helo +
  Sandy), or with none fragged an AI helo launches on demand. The enemy may race a snatch party
  to capture the survivor — kill it, or the pilot becomes a POW who leaves your roster until you
  retake the holding field, the hold clock runs out, or you win the war. A pilot neither rescued
  nor captured goes MIA and keeps evading, and the next turn opens with a rescue package already
  airborne at their position.
- [Electronic Warfare and ISR](Electronic-Warfare-and-ISR) — the **JAMMING** flight type turns
  the C-130J into an EC-130H/RC-130H-style standoff jammer and ELINT platform. The old generic
  fighter-pod jammer is retired.
- **Escort jamming** is flown by the EA-18G Growler and EA-6B Prowler only. The jammer rides the
  package, spoofs radar missiles fired at anything under its bubble, and pulses tracking SAMs to
  weapons-hold. Effect strengthens with proximity.
- Fixed-wing transports fly **Air Assault as a paradrop**. Players run in below 3,000 ft AGL and
  use the CTLD *Unload / Extract Troops* call; AI releases over the drop zone automatically.
- Strike, DEAD and Armed Recon packages can receive an auto-planned TARPS follow-up.

---

## The air war

- Squadrons hold aircraft in a **QRA intercept reserve** for base defence. Part of it can be
  player-manned as cold alert.
- **BARCAP** uses overlapping, jittered waves so coverage hands off instead of arriving all at
  once at mission start.
- **AWACS and tanker** racetracks are drawn on the generated mission's F10 map with callsign,
  frequency and TACAN.
- Native DCS **data cartridges** auto-load in Hornets, Vipers and CJS Super Hornets: comms
  matching the kneeboard, route with push times, boat recovery aids, and the recon-confirmed SAM
  picture. A per-flight DTC tab controls it.
- **Strike packages are timed behind the SEAD** servicing their target instead of arriving
  early.
- **SAM batteries field two guidance radars**, so one HARM no longer kills a site.
- Optional per-side **auto-planner unpredictability** varies which offensive targets the enemy
  services first.
- Enemy air defences run on the **MANTIS** IADS engine — the sole engine (Skynet was removed;
  older saves migrate automatically).

Full detail: [Air Defense and the Air War](Air-Defense-and-the-Air-War).

---

## Campaign systems

- Campaigns can author [custom victory conditions](Custom-Campaigns) — capture these bases,
  destroy these targets, hold this much territory, break the enemy air arm — shown live on the
  status ribbon and the SITREP, instead of grinding the map flat.
- Campaigns can schedule **squadron arrivals**: new airframes land on announced turns, so the
  wing you start with is not the wing you end with.
- **SP Pilot Mode** gives solo players an express lane — accept the debrief, pick an aircraft
  from the whole wing, take one seat in a sortie the war decided. The map and planner are
  untouched.
- Destroying enemy **command posts** degrades its target selection and thins its offensive
  tempo. With **COMINT** on, those same nodes are your intel source.
- **GPS jamming** sites deny satellite guidance over an area — a JDAM released inside lands off
  the aimpoint until you kill the jammer.
- Warships fire **cruise missile raids** from finite magazines that never rearm, and anti-ship
  magazines carry across turns.
- The shipped flavours: the [Vietnam campaign layer](Vietnam-Campaign-Layer) (ambush MiGs, Alpha
  Strikes, era planner ranges, a red tempo tied to the campaign clock) and the
  [COIN model](Enduring-Resolve-Campaign-Briefing) (an insurgency that regenerates from ammo
  caches, re-infiltrates cleared ground, and hides among the population).
- [Vietnam Ops](Vietnam-Ops) adds the era's mission-level mechanics — Arc Light, flak gauntlet,
  naval gunfire, trail interdiction, airbase harassment, Super Gaggle, FAC(A) marking, snake and
  nape. All opt-in, preseeded by the era campaigns.
- **Long-range carrier ops** put a standoff carrier in the war: a deterministic package (strike
  + buddy tanker + E-2) off the boat's own squadrons, with carrier flights routed to tank from
  the boat's own tanker.

> Removed 2026-07-21: the inferred campaign-phase arc, the ROE zone layer, and the political-will
> economy. Kept for historical reference only on
> [Campaign Phases and ROE](Campaign-Phases-and-ROE) — do not author against it.

---

## The generated mission

- [Troops In Contact](Troops-In-Contact) produces prolonged, formation-aware frontline firefights
  with ambient suppressive fire. Formations are distributed along the line, not piled on a spot.
- Supply convoys run both sides' road networks, and friendly routes sometimes hide ambush teams.
- Sea shipments sail as convoys of cargo ships past coastal anti-ship batteries that actually
  engage.
- Ship groups generate as mixed task groups rather than copies of one hull.
- Missile batteries generate with a support park in the faction's own kit.
- Carrier comms match the hull, Navy jets wear sequential squadron modexes, and the deck carries
  dressing placed clear of every spot and catapult.
- Civilian traffic and the 414th-tuned Splash Damage 3 build.

---

## Planning and debriefing

- Ground targets have an **intel panel**: known strength, mission suitability, ranges, IADS
  membership, visibility, capture and purchase state.
- Package and flight dialogs show task, TOT, player slots, departure bases, squadron fit and
  target distance in one place.
- The [unified map layers panel](Map-Layers-and-Interface) replaces both stock Leaflet controls
  with one grouped, collapsible control, preset views (Default / SEAD / Recon / Clean) and
  remembered choices.
- The [kneeboard deck](Kneeboards) is the stock deck with 414th content folded in — a BLUF on
  Mission Info, the fuel ladder in the flight plan, a SITREP page, threat cards, and custom
  image import per campaign.
- The Payload tab saves **per-aircraft flight defaults** (fuel, spawn type, aircraft options)
  and can pin a loadout as the default for an airframe and task — see
  [Custom Loadouts](Custom-Loadouts#per-aircraft-flight-defaults-fuel--aircraft-options).
- Debriefing opens with a **Mission Impact** summary — territory, runway damage, losses — before
  the full event detail.

---

## Content and tools

- **Eight built campaigns**: Red Tide (Germany 1988), 1968 Yankee Station (Vietnam), Operation
  Enduring Resolve (Afghanistan COIN), Red Flag 81-2 (Nevada 1981), Operation Inherent Resolve
  (Iraq 2016), Umm al-Ma'arik (Desert Storm 1991), Second Island Chain (Marianas 2027) and
  Operation Baltic Fury. Briefing packs for several are in the
  Campaigns section of [Home](Home).
- **Mod integration**: CurrentHill Iran (Shahed-136, IRGCN FAC, `[CH] Iran 2020` faction), High
  Digit SAMs Ultimate Compilation, and the optional Expanded F-4E Weapons Pack. All behind
  new-game mod toggles — see [Custom Factions](Custom-Factions).
- The **settings dialog** is reorganised into focused pages with one-click difficulty presets
  (Casual / Normal / Veteran / Ace), a search filter, an "only changed" view, and a dedicated
  414th Features page. Existing campaigns migrate automatically.
- Each squadron spawns under its **own DCS nation** with nation-aware pilot names — see
  [Squadrons and Pilots](Squadrons-and-Pilots).

Most campaign-facing systems have their own setting or plugin toggle. **Hidden enemy command
posts** (Difficulty & Realism → Realism & restrictions) is on by default for new campaigns —
details on [Fog of War and Reconnaissance](Fog-of-War-and-Reconnaissance).

---

## See also

- [Getting Started](Getting-Started)
- [Mission Planning](Mission-planning)
- [Fog of War and Reconnaissance](Fog-of-War-and-Reconnaissance)
- [Air Defense and the Air War](Air-Defense-and-the-Air-War)
- [Home](Home)
