# Electronic Warfare and ISR

414Ret models scripted electronic warfare and intelligence-gathering through a single
platform: the **C-130J flying the `JAMMING` flight type** as an EC-130H Compass Call /
RC-130H Rivet Joint-style standoff jammer and ELINT collector. This is the **only** scripted
EW model in the fork. The old generic fighter-pod "EW Jammer Script" — F-16/A-10 ECM-pod
jamming with an F10 "Jammer menu" — has been **retired** and must not be restored.

## What the JAMMING flight does

When you plan a `JAMMING` task on a C-130J, the planner spawns it as a standoff support
aircraft and a ~1,950-line in-mission script (`c130j_mission_systems.lua`) drives its
runtime behavior. It splits into two roles:

### Electronic attack (EC-130H Compass Call)

- **Area, directional, and spot jamming** of enemy emitters.
- **Range-banded per-tick missile spoofing** — the script attempts to defeat incoming
  missiles, with a roughly 3 nm arming distance so it never spoofs a missile still sitting
  next to its own launcher.
- The jamming model is deliberate, not a bug: the **burn-through model raises jam
  probability with distance** (closer threats are harder to jam), spot jamming has a flat
  altitude-independent range, and the missile-spoof curve is intentionally steep at close
  range.

Note that jamming does **not** silence SAM radars — suppression is achieved through a
`WEAPON_HOLD` ROE on the C-130J itself, not by toggling enemy emissions.

### ISR / ELINT (RC-130H Rivet Joint)

- **Altitude-gated radar detection** of enemy emitters.
- Up to **three simultaneous ELINT tracks** with progressive lock (60–360 seconds depending
  on range).
- **F10 map marks** and **Bullseye reporting** on detected emitters, plus a coalition-wide
  **ELINT-Lock alert** when a track locks.

### Coordination

A **COORD** menu produces an EW/ISR handoff brief that can be delivered to any selected
friendly group, so a strike or SEAD package can be cued off what the jammer has found.

## How to plan it

1. Make sure your faction has a C-130J squadron available.
2. Create a flight with the **JAMMING** task and assign the C-130J.
3. The planner gives it an AWACS-style standoff racetrack **outside the threat zone** with a
   `WEAPON_HOLD` ROE — it is a support asset, not a shooter. Position the package so the
   orbit sits within useful range of the emitters you want jammed or collected.
4. If no parking is available, the spawner falls back to a runway start automatically.

Because the C-130J holds well behind the threat ring, treat it the way you would an AWACS or
tanker: anchor it where it covers the area of interest but stays survivable, and let escorts
and SEAD handle the threats it lights up.

## The retired generic EW model

The standalone `ewrj` / "EW Jammer Script 2.1" plugin is gone. Do not expect F-16 or A-10
ECM pods to create an F10 "Jammer menu" — only the C-130J Mission Systems plugin owns
scripted jamming now. Legacy saved `ewrj` settings are purged automatically when an old
campaign is loaded.

## See also

- [Mission-planning](Mission-planning)
- [Air-Defense-and-the-Air-War](Air-Defense-and-the-Air-War)
