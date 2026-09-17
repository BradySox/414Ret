# Gameplay Mechanics (distilled from wiki Manual: Mission planning, Stances, Frontline Movement, Base Capture, Transfers, Fast Forward, Auto-purchase, Turn Zero, AI tips)

## Core loop

Turn-based: only events during the flown mission count ("Take Off" → fly → "Accept Results"). Quitting a mission early = no combat simulated. Exceptions: ferry flights and airfield repairs. Turn 0 is a setup phase (ground units appear anywhere instantly, no factory/convoy needed).

## Packages, ATO, TOT

- **Package** = flights working one goal (strike + SEAD + escort). All fragged packages = the **ATO**.
- **TOT** meaning varies: weapons-on-target time for Strike/DEAD, patrol start for CAP. Everything else (takeoff, waypoint times) is back-planned from TOT.
- Delayed-start behavior: AI shore flights spawn uncontrolled (parked, targets/ambience); AI carrier flights late-activate (deck space); cold-start players from shore spawn uncontrolled and locked out until mission start time; carrier players spawn immediately.
- "Player flights ignore TOT and spawn immediately" only changes how you WAIT (for group pre-flight checks) — it doesn't move mission time. To actually start at your time, use Fast Forward. "ASAP" checkbox = plan the package as early as possible.
- Waypoint sequence: **HOLD** (orbit until published departure time; ~5 min budgeted) → **JOIN** (package forms up) → **INGRESS** → **TARGET** → **EGRESS** → **SPLIT** (break for RTB). Times shown on map pins and the in-cockpit kneeboard. Timing discipline is on the pilot: early = orbit longer at HOLD; late = cut the hold to catch up.
- SEAD flights get TOT −1 min vs the package; stretch to 3 min manually if using TALDs.
- Any flight's route (friendly or AI) can be dragged on the map; timings auto-recalculate to hold TOT. Use terrain masking — the map zooms far enough to route through valleys.
- Auto-Create button builds a full package (primary + support) with auto-planner logic. OPFOR ATO is fully viewable/editable.
- Flight edit dialog: callsign, custom fuel, per-flight/per-pilot livery override, datalink (VCL/VCN/network ID). NAV waypoints can be inserted and NAV/REFUEL/DIVERT deleted without degrading to a custom plan.
- Unlimited fuel (if on): AI fuel floors at 40% from startup to JOIN and again from SPLIT onward; limited in between (CAP flights: boundary is racetrack start/end instead). Intent: no RTB-before-ingress, no flameouts in the landing queue.

## Task types (quick table)

| Type | Target | Key behavior |
|---|---|---|
| BARCAP | Friendly objective | Racetrack toward nearest enemy airbase; 60 min default on-station |
| TARCAP | Enemy objective | On station 2 min before package join; poor near SAMs |
| CAS | Front line | Searches visual range only (DCS limit); weather hurts it |
| Armed Recon | Any objective/target | Engages ground targets in a small radius; mop-up role |
| BAI | Enemy armor groups | Kills a specific stationary group; convoy interdiction is a BAI subset (Departing Convoys tab → Attack) |
| Strike | Static coordinates | Attacks coordinates, NOT units — moving targets escape |
| DEAD | Air defenses | Kill shot, usually paired with SEAD suppression |
| SEAD | Package target | Suppress, not kill: keep radar off/busy for the DEAD flight; fire HARMs PB-mode staggered ~1/min |
| SEAD Escort | Escorted flight | Engages air defenses threatening the escorted route |
| SEAD Sweep | Route | Engages ANY air defense between join and split |
| Escort | Requesting flights | A2A defense of the package |
| Fighter sweep | Enemy objective | Clears fighters 5 min ahead of package |
| OCA/Aircraft | Airfield | Kills parked aircraft |
| OCA/Runway | Airfield | One 2000lb-class hit kills a runway; repair = 4 turns + $100M; dead runway blocks ops and purchases |
| Anti-ship | Naval group | Mass weapons to beat point defense |
| Air Assault | Enemy CP | Helo troop capture; requires CTLD plugin; drop-off must be inside the assault zone |
| Airlift | Transfer | From Unit Transfer dialog; CTLD zones generated for player flights only |
| Refueling (package) / Recovery Tanker / Theater tanker | — | Package-tied vs carrier-orbit vs general orbit |

## Frontline stances and movement

Stances (Ground Forces HQ per enemy-connected CP; auto-managed by default under Campaign Management → HQ Automation):

| Stance | Behavior |
|---|---|
| DEFENSIVE | Hold, groups of [2,4,6] |
| AMBUSH | Same as DEFENSIVE but small groups [1,1,2,2,2,2,4]; player-only, AI never picks it |
| AGGRESSIVE | Tanks/IFVs advance up to 16 km, attack base if inside |
| ELIMINATION | Attack 3 nearest groups first, then base if ≤16 km; kills over ground |
| BREAKTHROUGH | Rush up to 35 km; ground over kills |
| RETREAT | Everything falls back up to 20 km |

Support units: APC/ATGM follow offensives up to 16 km, never lead; artillery fires in range, falls back when damaged. AI stance pick is deterministic by force balance (friendly/enemy): ≥2.0 BREAKTHROUGH, ≥1.5 ELIMINATION, ≥0.8 AGGRESSIVE, ≥0.5 DEFENSIVE, else RETREAT.

Frontline position = player's share of the two connected CPs' Strength Ratings (0.0–1.0 each), applied along the supply route, never closer than 5 km to a CP. CPs start 1.0; captured = reset 0.0; +0.2/turn regen on flown turns (skip turn = no change). After each mission a winner is computed (survivors → RETREAT auto-loses → casualties; a player taking more casualties still wins with >2x remaining units AND an aggressive stance), then Strength shifts by the Victory Influence: STRONG 0.5 (wipeout, RETREAT, casualty ratio >3, BREAKTHROUGH win... or BREAKTHROUGH LOSS — overextension is punished), Normal 0.3 (ratio 1.5–3), MINOR 0.1 (ratio <1.5, defensive-stance wins). Casualty ratio = (1+enemy)/(1+allied).

## Base capture and transfers

Capture = friendly ground unit inside base radius AND no enemy units inside. Airfields and FOBs only — never carriers/LHAs/off-map. On capture, units try to retreat: aircraft to a compatible base within ~2x their mission range with parking (carrier-capable ≠ LHA-capable); ground units to a connected CP; failures are captured and sold.

Transfers: squadrons move whole (Air Wing pane), never individual airframes. Ground transfers move 1 CP/turn along transit routes; priority road → ship → airlift (airlift last because it consumes airframes). Convoys/freighters/transport aircraft are physically present and interdictable; killing them kills the cargo. Cancelling returns units to the ORIGIN base. Cut-off transfers re-route or cancel in place; surrounded transfers are destroyed. Purchases auto-create factory→destination transfers.

## Fast forward and auto-purchase

Fast forward (Mission Generator → Gameplay): "Fast forward until" = No FF / Player startup (default) / taxi / takeoff / at IP / First contact / Manual (`--show-sim-speed-controls`). Combat during FF: Pause (default) / Resolve (WIP, brutal losses) / Skip. Upstream tip: try a +15 min past-ASAP TOT offset on the player flight (up to +20 on big maps). Settings lock after Take Off — reload state to change.

Auto-purchase (Campaign Management → HQ Automation, same logic AI uses): priority runway repair → front-line units (budget split governed by ground-ratio setting, default 50%; front lines filled to limit × reserves factor 130%, then reserves elsewhere to target 10) → aircraft (bought to fill unplanned missions, best airframe by task-score YAML weights, nearest safe airfield with parking; deterministic, no dice). Unspent budget rolls over.

## Taxi congestion (Tips for AI Handling)

Primary fix: **Player startup time** (Campaign Doctrine → General) — default 10 min player vs 2 min AI head start; raise it, re-plan packages to apply. Combine with: wait for AI to taxi first; spread take-off times 2+ minutes.
