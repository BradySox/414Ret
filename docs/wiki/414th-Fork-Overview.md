# What's Different in the 414th Fork

414Ret is the **414th Joint Fighter Group's build of DCS Retribution**. It is not a reskin
or a single extra aircraft pack — it changes how a Retribution campaign is *planned,
understood, and flown* by a multiplayer squadron. Everything upstream Retribution does still
works; this page is the map of what the fork adds on top, with links to the full pages.

If you have never used Retribution before, read **[Getting Started](Getting-Started)** first —
this page assumes you know the basic turn loop.

> The build tracks upstream Retribution's `dev` branch and layers the 414th feature set plus
> selected newer upstream fixes on top. Pre-built Windows releases publish automatically to
> the rolling **[latest build](https://github.com/bradyccox/414Ret/releases/tag/latest)**.

---

## Intelligence is incomplete — and recon has a purpose

Upstream shows you the enemy laydown. The fork fogs it, so reconnaissance becomes a real task.

- Enemy sites can be **known without their composition, strength, damage state, or threat
  rings** being known. Attacking or scouting a site reveals it; confirmed battle damage can
  require a surviving recon pass (BDA damage lag).
- **[TARPS](TARPS-Reconnaissance)** is a real player task (the F-14, plus the Vietnam-era
  **RF-101B Voodoo** and **RA-5C Vigilante** recon birds), backed by the **TARS** film-and-debrief
  engine — what the aircraft photographs is carried back into the campaign as confirmed intelligence.
- An optional **Approximate target area** mode removes perfect coordinates and offsets
  steerpoints, so visual acquisition, talk-ons, and recon matter. Mobile short-range defenses
  are kept off player datalinks while larger SAM sites stay available for deliberate SEAD/DEAD.
- When you need the ground truth anyway — debugging, planning the opposing side, or just
  checking the real laydown — tick **Reveal fog of war (overview)** in the map layer panel. It
  is a view toggle only; it never changes the campaign and is never saved.

Full detail: **[Fog of War and Reconnaissance](Fog-of-War-and-Reconnaissance)**.

---

## Missions are built for squadron play

- **[Combat SAR](Combat-SAR)** + **[SCAR "Sandy"](SCAR)** — makes a downed pilot worth flying
  for. A standing **rescue package** (a C-130 "King" overhead, a rescue helo "Jolly Green", and
  2–4 **Sandy** escorts on `FlightType.SCAR`) recovers a downed human pilot; deliver them to a
  friendly field and the campaign **spares the aviator** (you still lose the jet). The enemy may
  race a snatch party to **capture** the survivor — kill it, or the pilot becomes a **POW** you
  recover over later turns. (`FlightType.SCAR` was repurposed from a retired armor-hunt task into
  the Sandy role; the old SOF commander-capture loop was retired with it.)
- **[Electronic Warfare and ISR](Electronic-Warfare-and-ISR)** — the **JAMMING** flight type
  turns the C-130J into an EC-130H/RC-130H-style standoff jammer and ELINT/ISR platform. This is
  the only 414th scripted EW model; the old generic fighter-pod jammer is retired.
- Strike and DEAD packages can receive auto-planned **TARPS** follow-up, and AI SEAD can loiter,
  react to emitters, and break off on a computed timeline instead of a single inflexible pass.

---

## The air war behaves like a campaign, not a queue of sorties

- Squadrons can hold aircraft in a **QRA intercept reserve** for runtime base defense.
- **BARCAP** coverage uses overlapping, jittered, threat-weighted waves and a more useful
  forward defensive line — quiet sectors keep baseline coverage, contested sectors get more.
- **AWACS and tanker** racetracks are anchored on the front line and stand off into friendly
  airspace; a theater tanker is placed on receiver demand.
- The auto-planner no longer sends strikers through a SAM belt it only *intends* to clear: a
  strike that depends on a DEAD which can't actually reach its target is held back until the
  belt is genuinely down.
- An optional **auto-planner unpredictability** doctrine knob (per side, off by default) varies
  which offensive targets the enemy services first.
- Enemy air defenses run on the **MANTIS** IADS engine — the sole engine (Skynet was removed; older saves migrate automatically).

Full detail: **[Air Defense and the Air War](Air-Defense-and-the-Air-War)**.

---

## The generated mission feels occupied

- **[Troops In Contact (TIC)](Troops-In-Contact)** produces prolonged, formation-aware
  frontline firefights with ambient suppressive fire, instead of vanilla ground AI instantly
  erasing the battle. Frontline formations are distributed along the line, not piled on one spot.
- Civilian regional traffic adds light rear-area activity, and the 414th-tuned **Splash Damage 3**
  build improves weapon effects.

---

## Planning and debriefing expose what crews need

- Ground targets have an **intel panel** showing known strength, mission suitability, ranges,
  IADS membership, visibility, and capture/purchase state.
- Package and flight dialogs show task, TOT, player slots, departure bases, squadron fit, and
  target distance without hunting across windows.
- The **[unified map layers panel](Map-Layers-and-Interface)** replaces both stock Leaflet
  controls with one dark-themed, grouped, collapsible control — with one-click preset views
  (Default / SEAD / Recon / Clean) and remembered choices between sessions.
- The **[kneeboard deck](Kneeboards)** opens on a single cover page (op/turn header, the previous
  turn's SITREP, and a flight index) and can fold into a compact 3–4 page deck; you can also import
  your own kneeboard images per campaign.
- Debriefing begins with a **Mission Impact** summary — territorial changes, runway damage, and
  losses — before the full event detail.

---

## Additional content and tools

- **[Drop-Spawn Unit Placement](Drop-Spawn-Unit-Placement)** — right-click blank map space to
  place a unit group (gated behind cheat settings).
- **CurrentHill Iran** integration — Shahed-136 and IRGCN FAC assets plus a `[CH] Iran 2020`
  faction behind a new-game mod toggle (see **[Custom Factions](Custom-Factions)**).
- **Germany - Red Tide** — a *Red Storm Rising*-flavoured 1988 NATO counteroffensive campaign
  built for the 414th, with named historical squadrons and liveries.
- **Khe Sanh: Operation Niagara** — a historical 1968 siege campaign on Caucasus: an encircled
  blue base kept alive by air, where the threat is **AAA, not MiGs**. Both shipped 414th campaigns
  have a full player-facing **briefing pack** on the wiki (ORBAT, phase plan, mission-brief
  template, threat-defeat, role cards) — see the Campaigns section of **[Home](Home)** and
  **[Custom Campaigns](Custom-Campaigns)**.
- The **settings dialog** is reorganised into six focused pages with one-click **difficulty
  presets** (Casual / Normal / Veteran / Ace), and a settings audit removed dead/duplicate options
  and merged the AI-radio toggles into a single **AI wingman radio behavior** choice. Existing
  campaigns migrate automatically.
- Each squadron can spawn under its **own DCS nation** (nation-specific voiceovers) with
  **nation-aware pilot names** (see **[Squadrons and Pilots](Squadrons-and-Pilots)**).

Most campaign-facing systems have their own setting or plugin toggle. The **command-post intel
fog** (enemy command posts hidden until you find them by strike/scout/TARPS) is on by default for
new campaigns — toggle `SCAR command-post intel` on the Campaign Doctrine page to turn it off
(details on **[Fog of War and Reconnaissance](Fog-of-War-and-Reconnaissance)**).

---

## See also

- [Getting Started](Getting-Started)
- [Mission Planning](Mission-planning)
- [Fog of War and Reconnaissance](Fog-of-War-and-Reconnaissance)
- [Air Defense and the Air War](Air-Defense-and-the-Air-War)
- [Home](Home)
