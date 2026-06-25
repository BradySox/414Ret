# Combat SAR

Combat SAR makes a downed pilot worth flying for. When a human pilot ejects in the operating
area, you can mount a rescue: a CH-47 goes in, picks the survivor up, and brings them home. If
you deliver them to a friendly field, the campaign **spares that aviator at debrief** — the
airframe is still lost, but the experienced pilot returns to the squadron instead of being
killed off. It turns an ejection from a flat loss into a gameplay loop.

This is a bespoke pilot-rescue flight type (`FlightType.COMBAT_SAR`), and it is **distinct**
from the SCAR SOF-recovery CSAR ([SCAR](SCAR)) — though, as below, a Combat SAR helo can also
extract a stranded SOF team.

## The package: rescuer + King

Combat SAR is flown as a two-element idea, both player-selectable:

| Element | Airframe | Role |
|---|---|---|
| **Rescuer** | **CH-47Fbl1** (the playable ED Chinook) | Orbits near the FLOT behind the threat rings; flies in, lands, picks up the survivor, and delivers them to any friendly field/FARP. Carries a door-gun loadout (port + starboard M60D) for self-protection on the way in. |
| **King** | **C-130J-30** | Flies the overhead **HC-130 "King"** on-scene-command orbit, lighting the homing beacon and running the survivor locator. |

An AI **CH-47D** is the fallback rescuer (no weapon stations). The King C-130 is overhead
presence and command, not a tanker — it is never wired into aerial refueling.

## How a rescue works

1. A **human** pilot ejects in the area. MOOSE CSAR (the runtime engine) spawns the downed
   pilot with a beacon.
2. The **King** lights an **air-tracking TACAN** beacon. This is the single homing solution —
   it follows the King's moving orbit, and every rescue helo we use has a TACAN receiver. (An
   ADF radio beacon was considered and dropped: MOOSE's radio beacon is fixed-point and the
   King is a mover, so it would gain nothing over the TACAN.)
3. The King also carries an F10 **Combat SAR → LARS** button (LARS = survivor locator). It
   reads the live downed-pilot table and reports each active survivor's position and
   bearing/range from the King, for the crew to relay.
4. The CH-47 homes on the King's TACAN, flies in, lands, boards the survivor, and delivers them
   to a friendly field.

## Rescue scoring — the payoff

The point of a rescue is to save the pilot, so the loop closes in the campaign model:

- When the helo lands and boards a survivor, the engine remembers that pilot's **original
  ejected aircraft**.
- On a successful **delivery to a friendly field**, those pilots are credited.
- At debrief, each credited pilot's loss is resolved so the airframe is still attrited but the
  **aviator survives** — `loss.pilot.kill()` is skipped for them.

A helo shot down with survivors aboard never reaches the delivery, so those pilots are
(correctly) never credited — you have to actually bring them home. The scoring is fail-safe: if
nothing is rescued, behavior is exactly as it is today (the pilot dies).

## AI standing alert (optional)

By default, Combat SAR is a thing you plan and fly. You can also enable an AI standing alert
with the **`auto_combat_sar`** setting (HQ automation, **default OFF**). With it on, the planner
auto-plans one Combat SAR orbit per turn for blue, and the engine is told it may commandeer an
orbiting AI CH-47 — which also makes **AI** ejections rescuable, not just human ones.

Combat SAR is **blue-only**: the engine is built for blue, so a red Combat SAR would just fly an
inert orbit and is never auto-tasked.

## Extracting a stranded SOF team

The same rescue helo can extract a stranded SCAR SOF team in-mission. The generator emits each
on-map "downed SOF team" and the plugin spawns it as a MOOSE CASEVAC ground pickup at its strand
point; the helo boards and delivers it just like a downed pilot. The campaign credits the
recovery — refunding the bought team — alongside (not replacing) the dedicated `FlightType.CSAR`
air-assault recovery. A team recovered by both paths still refunds only once. See
[SCAR](SCAR) for how teams get stranded in the first place.

The pilot-sparing channel and the SOF-recovery channel are kept distinct (routed by name), so
there is no double-counting and no double ejection-handling.

## Settings reference

| Setting | Default | Effect |
|---|---|---|
| `FlightType.COMBAT_SAR` | player-selectable | Plan a rescuer (CH-47) or King (C-130) orbit by hand |
| `auto_combat_sar` | OFF | AI standing alert: auto-plans a Combat SAR orbit per turn and makes AI ejections rescuable |
| King beacon | TACAN-only | Air-tracking TACAN the helo homes on; F10 LARS reports survivor positions |

## In-game pass status

Combat SAR is built (the rescue engine, AI alert, King TACAN/LARS, rescue scoring, SOF-team
extraction, the armed Chinook and flyable King, and the task kneeboard) and passes CI, but the
in-mission behavior has **not yet had a cockpit pass**. The relevant checklist rows are all
currently untested:

- **G8** — pilot rescue (CH-47 + MOOSE CSAR)
- **G9** — AI standing alert (`auto_combat_sar`)
- **G10** — King TACAN beacon + LARS
- **G11** — rescue scoring (pilot spared at debrief)
- **G12** — Combat SAR extracts a stranded SOF team
- **G13** — airframes (armed Chinook + flyable King)
- **H2** — Combat SAR task kneeboard

Treat the feature as flight-ready but unvalidated until those rows are cleared.

## See also

- [SCAR](SCAR)
- [Squadrons and Pilots](Squadrons-and-Pilots)
- [Mission planning](Mission-planning)
