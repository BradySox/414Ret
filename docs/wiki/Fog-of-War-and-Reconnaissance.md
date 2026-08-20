# Fog of War and Reconnaissance

Every enemy site is on your map from turn one, at its real position. What is parked there is not.
Composition, unit counts, and threat and detection rings stay hidden until you **engage** the site
— and once you do, you know everything about it, permanently.

Fog applies only to the human (BLUE) map and dialogs. The AI planner and all threat math always use
ground truth, so the enemy never gets dumber because you are fogged.

---

## What you know

| | Shown | Hidden |
|---|---|---|
| Un-engaged site | position, category, allegiance, air-defence band, valid mission types | unit types, counts, live/dead state, threat ring, detection ring |
| Engaged site | everything, including current damage | nothing |

![The target intel dialog for an un-engaged enemy SAM site: known live units, detection range, and threat range all read Unknown, and the units list reads composition unknown](https://raw.githubusercontent.com/BradySox/414Ret/main/docs/wiki/img/fog-intel-not-scouted.png)

*Before — you know it exists, its band, and which missions are valid against it.*

![The same site after engagement: known live units 9/9, detection range 54 NM, threat range 27 NM, and the full unit list resolved to SA-11 Buk Gadfly launchers, command, search radar, and support vehicles](https://raw.githubusercontent.com/BradySox/414Ret/main/docs/wiki/img/fog-intel-scouted.png)

*After — 9/9 live, 54 NM detection, 27 NM threat, and the actual SA-11 Buk composition you now
have to plan against.*

## What counts as engaging it

Either of these, flown by your side:

- **Ordnance on the site.** Any unit destroyed there reveals it.
- **A ground-attack sortie that reaches it and comes home** — Strike, DEAD, SEAD, SEAD Sweep, SEAD
  Escort, Anti-ship, BAI, CAS or Armed Recon. Kills are not required; the crews saw what was there.

A flight shot down before it arrives reveals nothing.

**Recon does not reveal an ordinary site.** The fog is lifted by attacking, not by scouting.

Discovery is permanent and total. There is no second confirmation step and no damage lag — you see
the damage the moment the strike lands, and it stays known across save and load.

Master switch: **`recon_intel_fog`** (Campaign Doctrine, default ON). Saves predating the feature
load fully revealed.

---

## Hidden command posts — the one thing recon is for

The **"Hidden enemy command posts"** setting (default ON) hides enemy command posts entirely — no
marker, not plannable, not strikable.

That makes them the one target engagement cannot reach: you cannot put ordnance on something you
cannot see. **Flying TARPS recon is how you find them.**

A recon flight that comes home reveals any hidden command post within about **3 NM of the area it
was sent to photograph**, with a "RECON: enemy command post located" message. Once found it shows
fully, with exact coordinates, and can be planned against.

Mapping the enemy command network is its own campaign task, and recon is the tool for it.

### Flying a pass

1. Build a `FlightType.TARPS` package by hand, or let the auto-planner append one.
2. **Bring the flight home.** The find is credited if at least one aircraft survives.

**Altitude, speed, cloud cover and sensor make no difference**, and there is no film menu or
per-sortie limit. The plugin that scored an overflight that way was removed in August 2026 once the
reveal rules left it with nothing to feed. A drone can be fragged as the recon bird like any other
TARPS-capable airframe, but a drone flying some other tasking contributes nothing.

Weather still matters one step earlier: in rain or storms the auto-planner stops appending recon
flights at all.

### The aircraft

TARPS is airframe-agnostic — any aircraft tagged with the `TARPS` task can fly it.

All F-14 variants carry the `{F14-TARPS}` pod on station 6 via the **Retribution TARPS** payload,
paired with a self-defence fit. The flight plan uses a recon ingress, not a strike ingress, so the
AI does not get bombing tasks dumped on it and turn back at the ingress point.

Two Vietnam-era camera ships fly TARPS as their primary job — the **RF-101B Voodoo** (USAF,
land-based) and the **RA-5C Vigilante** (US Navy, carrier-based). Both are unarmed, with built-in
cameras rather than a pod, so their TARPS loadout is a clean weaponless fit. Both keep a
low-priority Armed Recon fallback. **1968 Yankee Station** fields them at Da Nang and on the
carriers.

### Auto-planned recon

With **`auto_add_tarps_recon`** on (default), the planner appends one TARPS sortie to **Strike**,
**DEAD** and **Armed Recon** packages against high-value targets.

- Behind a Strike or DEAD shooter it arrives **2 minutes later**.
- On Armed Recon it flies **with** the shooters — find-and-overwatch, not post-strike.
- Needs a TARPS-capable squadron in range. If none is free the recon flight is skipped; the strike
  is never scrubbed for it.
- On a drone-fielding faction the recon bird *is* the drone.
- It never paces the package — a slow drone keeps its own schedule instead of dragging the
  formation down.

---

## Uncertainty circles

One class of contact gets no exact marker: the insurgent spawns on the COIN campaign — roadside
IEDs and VBIEDs, HVT convoys, dispersed cells. Those draw a dashed amber "somewhere in here" circle
offset from the true position, because localising them is the point of that campaign. A roadside
IED's circle slides along its highway rather than off into the fields: you know what road it is on,
not which stretch.

The circle clicks and right-clicks like a marker, so you can plan against the suspected area.
Engaging snaps the contact to its real symbol. Ordinary enemy sites are never circled.

---

## Approximate target area

The **target location precision** setting (`EXACT` / `APPROXIMATE`) changes how much help your
steerpoints and kneeboards give you. In **Approximate**:

- Player target steerpoints are offset to a randomised area **1–3 NM** from the real target and
  renamed `TARGET AREA`. You fly there and visually acquire. AI attack logic is unaffected.
- **DEAD and SEAD** drop per-emitter target points for a single fuzzed target-area waypoint.
- Objective F10 map marks are suppressed.
- Kneeboards omit exact coordinates. The SEAD/DEAD page gives one consolidated cue — a rough
  bullseye for the site centre (about 1 NM) plus the target-area steerpoint, then a
  description/ALIC table of the emitters.

**Strike is deliberately exempt.** Its targets are fixed installations with reliable coordinates,
so Strike always gets exact per-unit points.

## Mobile SAMs hidden from the datalink

SHORAD, AAA and MANPADS are hidden from the MFD datalink picture, including escort SAMs riding
inside armour or missile groups. Standalone medium- and long-range SAMs stay visible so SEAD can
plan against them. You do not get a free, perfect datalink fix on every pop-up MANPAD.

## Reveal fog of war (overview)

Tick **Reveal fog of war** in the map's layer panel (Enemy intel group) to force every
player-facing fog rule to ground truth — composition, rings and hidden command posts all at once.

**Transient by design: it is never saved.** A campaign file can never carry a god-view, and a
shared campaign can never leak one. It is the only layer choice the panel deliberately does not
remember.

---

## Settings

| Setting | Default | Effect |
|---|---|---|
| `recon_intel_fog` | ON | Master switch. Hides an un-engaged site's composition and rings |
| Hidden enemy command posts | ON | Hides enemy command posts entirely until recon finds them |
| `auto_add_tarps_recon` | ON | Planner appends a recon flight to Strike / DEAD / Armed Recon |
| Target location precision | EXACT | Offsets steerpoints, hides marks and coords, consolidates the DEAD bullseye |
| Reveal fog of war (map toggle) | OFF, never saved | Short-circuits all fog to ground truth |

## Caveats

- Fog is BLUE-only on purpose; red always plays against the truth.
- The satellite-imagery recon **kneeboard** pages ship default-off. The marker/tile misalignment
  that gated them was fixed 2026-07-18; the toggle stays off until the fix gets an in-game pass.
  Turn on `Generate target recon kneeboard pages` to try them.

## See also

- [The Retribution UI](The-Retribution-UI)
- [Mission Planning](Mission-planning)
- [Air Defense and the Air War](Air-Defense-and-the-Air-War)
