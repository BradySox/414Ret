# Your First Operation

With [Turn Zero](Turn-Zero) committed, you are on Turn 1 — the first turn you actually plan,
generate, and fly. This page walks the full loop end to end: build a package, assign flights and
slots, set the timing, generate the mission, fly or skip it, and advance the turn on the debrief.

Throughout, remember the core rule: **only what happens inside the running mission changes the
campaign.** Everything you do on the planning map is preparation for that one mission.

## The war you are fighting

Your objective is to take all enemy control points. You do that by advancing your ground forces,
killing enemy aircraft, destroying the enemy's income-producing buildings, and dismantling air
defenses. The front line moves based on the results of each mission, so air power and ground
posture work together.

## Plan a package

A *package* is a group of flights that share a common objective and timing. From the **Air Tasking
Order (ATO)** panel you can let the auto-planner frag packages for you, or build your own:

1. Pick a target or mission objective on the map.
2. Add one or more flights to the package, choosing the **task** (BARCAP, SEAD/DEAD, Strike, CAS,
   escort, support, and the fork's player tasks below), the squadron, and the airframe.
3. Retribution routes each flight and shows you departure base, squadron fit, available aircraft,
   and target distance so you can plan without hunting across windows.

See [Mission Planning](Mission-planning) for what each task does and how to size and route a
package properly.

## Assign flights and player slots

To fly a flight yourself, select its package in the ATO and add **client slots** to the group
(double-click the group / use the player-slot control). You can put as many human slots as the
group allows; the rest fly as AI.

Watch the timing when you add player slots. Giving a flight a **cold start** can shift its takeoff
earlier and may push a start time negative — if that happens, adjust the package **Time on Target
(TOT)** or the flight's start type until the schedule is valid.

## Set the Time on Target

A package is built around its **TOT** — the moment its primary flights are meant to be over the
target. Retribution back-plans takeoffs, joins, and support timing from that. Nudge the TOT to
deconflict packages, to give yourself a comfortable start, or to sequence SEAD ahead of strikers.

## Generate the mission

When the plan is ready, generate the mission (the **Take Off** / generate control). Retribution
writes the `.miz` and holds it open.

> Do not close the generation window until your flight is complete. The generated mission is only
> valid while that window stays open. If you change the plan, regenerate and reload.

## Fly it — or skip it

Open DCS World, load the generated `retribution_nextturn.miz`, and pick your assigned slot from the
briefing screen. Your mission details — steerpoints, TOT, comms, and the package picture — are on
the kneeboard (Right Shift + K by default). A BARCAP, for example, orbits its station until its
departure time; a Strike runs in on its target at TOT.

If you do not want to fly a given turn, you can **skip** and let the simulation resolve the mission
automatically. Either way, the campaign only advances when the mission has been resolved.

### Fork player tasks

414Ret adds player tasks worth flying on your first operations once you have the right squadron:
**TARPS** photo-recon (turns guesses into confirmed intel — see
[Fog of War and Reconnaissance](Fog-of-War-and-Reconnaissance)), **SCAR** moving-target hunts,
**Combat SAR** pilot rescue, and **JAMMING** standoff EW/ISR. See [Mission Planning](Mission-planning).

## Debrief and advance the turn

Exit DCS and accept the results to process the mission. 414Ret leads the debrief with a **Mission
Impact** summary — territorial changes, runway damage, and losses up front — before the full
event-by-event detail, so you can see at a glance whether the front moved and what it cost. Note
that battle damage can take a recon pass to *confirm* under the fork's intel-fog, so the picture you
see may firm up over the next turn or two.

Accepting results advances the front line and rolls you into the next turn, where the loop begins
again: buy, plan, generate, fly, debrief.

## See also

- [Turn Zero](Turn-Zero)
- [Air Wing Configuration](Air-Wing-Configuration)
- [Mission Planning](Mission-planning)
- [Fog of War and Reconnaissance](Fog-of-War-and-Reconnaissance)
- [Air Defense and the Air War](Air-Defense-and-the-Air-War)
