# Electronic Warfare and ISR

414Ret models scripted electronic warfare and intelligence-gathering through a single platform:
the **C-130J flying the `JAMMING` flight type**, turned into an EC-130H Compass Call-style
standoff jammer and an RC-130H Rivet Joint-style ELINT collector. A ~1,950-line in-mission
script (`c130j_mission_systems.lua`) drives its runtime behavior from the cockpit. This is the
**only** scripted EW model in the fork — the old generic fighter-pod "EW Jammer Script" has been
retired and must not be restored.

> **In-game-pass status:** the JAMMING planner side is wired, but the retirement of the generic
> EW script (checklist G5) still owes a confirmation pass. The runtime EW/ISR behavior is driven
> entirely by the Lua, which CI can't exercise — treat the in-cockpit numbers below as "as
> built."

---

## The aircraft and how it's planned

When you plan a `JAMMING` task on a C-130J:

1. Make sure your faction has a **C-130J squadron** available.
2. Create a flight with the **JAMMING** task and assign the C-130J.
3. The planner gives it an **AWACS-style standoff racetrack outside the threat zone** with a
   `WEAPON_HOLD` ROE — it is a support asset, not a shooter. Position the package so the orbit
   sits within useful range of the emitters you want to jam or collect against.
4. If no parking is available, the spawner falls back to a runway start automatically.

Treat it like an AWACS or tanker: anchor it where it covers the area of interest but stays
survivable, and let escorts and SEAD handle the threats it lights up. Everything else happens at
runtime, through the jet's F10 menu.

> **Suppression is by ROE, not by toggling enemy radars.** The script never silences a SAM's
> emissions directly (doing so crashed DCS) — jamming degrades the enemy's *picture*, and the
> C-130J's own `WEAPON_HOLD` keeps it from behaving like a shooter. Don't expect a jammed SAM to
> go physically dark.

---

## Electronic attack (the EC-130H role)

The jammer runs on an **energy budget** — a capacity pool that drains while you jam and
regenerates while you're idle, with an overheat cutout if you redline it. Managing that budget
is the core of flying the EW role well.

### The three jamming modes

| Mode | Footprint | Energy cost | Reach (default) | Notes |
|---|---|---|---|---|
| **Area** | Omnidirectional | ~3 / sec | up to ~200 NM | Theater-wide but diluted — about 0.65× the focused effectiveness. Jam everything, weakly. |
| **Directional** | A chosen sector | ~1 / sec | — | Cheapest; concentrate on one bearing. Enable per direction. |
| **Spot** | One emitter | ~5 / sec | ~100 NM (full power within ~70 NM) | Strongest punch — recovers ~half of a system's ECCM resistance — but the most expensive and single-target. |

Capacity regenerates at ~5/sec when idle. Holding emitters down with area/directional jamming
costs extra drain per suppressed emitter, so the more you suppress, the faster the budget falls.
If you push capacity to zero the pods **overheat** and won't come back until capacity recovers
past a reset threshold, and you get a low-capacity warning at ~20%. The practical rhythm is to
**spot-jam the threat that matters, area-jam sparingly, and let the budget recover between
pushes.**

### Burn-through and frequency bands

Two deliberate modeling choices shape what actually gets jammed:

- **Burn-through rises with proximity.** Counter-intuitively, a *closer* threat is *harder* to
  jam — its radar return burns through your noise — so jam probability goes up with distance.
  Standing off helps the jam, not just survivability.
- **Frequency bands matter.** If your pods don't cover a system's band, effectiveness takes a
  cross-band penalty (~0.6×). Spot jamming punches through a fraction of a system's ECCM
  resistance regardless.

### Missile spoofing

The script attempts **range-banded, per-tick missile spoofing** against incoming missiles, with
a roughly **3 NM arming distance** so it never spoofs a missile still sitting next to its own
launcher. The spoof curve is intentionally steep at close range — it is a last-ditch defensive
aid in defined spoof zones, not an invulnerability bubble.

### EW F10 menu

The jet's F10 **EW** menu lets the crew run all of this: enable/disable **area** jamming, pick a
**direction** for directional jamming (enable per bearing, disable), toggle **spot** jamming on
the tracked emitter, and **Power OFF / Power ON** the jammer pods entirely (e.g. to bank
capacity or go quiet).

---

## ISR / ELINT (the RC-130H role)

Alongside jamming, the C-130J runs a passive ELINT picture:

- **Altitude-gated radar detection** of enemy emitters — you have to be high enough to see them.
- Up to **three simultaneous ELINT tracks** (tunable up to ten), each built with a **two-phase
  progressive lock**: an initial fix that takes **60–360 seconds** depending on range (closer =
  faster), then a refinement phase several times longer that walks confidence up to 100%.
- As confidence grows, the **position error shrinks** (from ~50 NM at 0% confidence) and the
  **bearing error** tightens (from ~30°), so an early track is a rough cue and a mature track is
  a precise fix.
- **F10 map marks** and **Bullseye reporting** on detected emitters, a coalition-wide
  **ELINT-Lock alert** when a track matures, and a **displacement alert** if a tracked emitter
  moves more than ~500 m (a mobile SAM relocating).

### ISR F10 menu

The **ISR** menu offers a **SIGINT Report** (the current emitter picture), **Stop All Tracks**,
**Toggle Auto-Triangulate** (let the script refine fixes automatically), and **Clear Map Marks**.

---

## Coordination — the COORD handoff

A **COORD** menu produces an EW/ISR **handoff brief** that can be delivered to any selected
friendly group, so a strike or SEAD package can be cued off exactly what the jammer has found —
the C-130J becomes the node that owns the emitter picture and feeds the shooters. This is the
"talk-on from the big-wing" workflow: collect, identify, then hand the fix to the flight that
will prosecute it.

---

## Plugin options (tunables)

All exposed in the Plugin Options UI under **C-130J Mission Systems** (default ON):

| Option | Default | Range | Effect |
|---|---|---|---|
| EW capacity regen / sec | 5 | 1–30 | How fast the energy budget recovers when idle |
| Area-jam drain / sec | 3 | 1–20 | Energy cost of area jamming |
| Spot-jam drain / sec | 5 | 1–30 | Energy cost of spot jamming |
| Max area-jam range (NM) | 200 | 25–270 | Reach of area jamming |
| Spot-jam range (NM) | 100 | 25–220 | Reach of spot jamming |
| Max simultaneous ELINT tracks | 3 | 1–10 | How many emitters you can track at once |
| On-screen message duration (s) | 15 | 5–60 | How long EW/ISR messages stay up |

## The retired generic EW model

The standalone `ewrj` / "EW Jammer Script 2.1" plugin is gone. Do **not** expect F-16 or A-10 ECM
pods to create an F10 "Jammer menu" — only the C-130J Mission Systems plugin owns scripted
jamming now. Fighter/attack ECM pods still exist as loadout equipment and DCS-native ECM, but
they drive no scripted 414th menu, and AI SEAD/DEAD flights no longer get the old generic jamming
waypoint actions. Legacy saved `ewrj` settings are purged automatically when an old campaign is
loaded.

## Tips

- **Stand off.** Burn-through and survivability both reward distance; the default ranges
  (200 NM area, 100 NM spot) are built for a deep orbit.
- **Spot the priority, area the rest.** Spot jamming is your punch but it's expensive and
  single-target; don't leave area jamming running flat-out or you'll overheat.
- **Let ELINT mature before you hand off.** An early track has tens of miles of position error;
  wait for the refinement phase before you pass a fix to a shooter via COORD.
- **It pairs with SEAD/DEAD, not replaces it.** The jammer degrades the enemy picture; the
  shooters still have to kill the site. See [Air Defense and the Air War](Air-Defense-and-the-Air-War).

## See also

- [Mission planning](Mission-planning)
- [Air Defense and the Air War](Air-Defense-and-the-Air-War)
- [IADS Engine: MANTIS](IADS-Engine-MANTIS)
- [Fog of War and Reconnaissance](Fog-of-War-and-Reconnaissance)
