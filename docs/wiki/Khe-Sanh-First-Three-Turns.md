# Khe Sanh: Operation Niagara — Worked Example: The First Three Turns

*A filled-in model for the [Campaign Briefing Handbook](Khe-Sanh-Campaign-Briefing) mission-brief
template. These three turns open **Act I — Rolling Thunder** of the
[campaign plan](Khe-Sanh-Campaign-Briefing#6--campaign-conops--the-phase-plan):
**hold the perimeter and the lifeline → beat down the guns → kill the Lang Vei armor.** Copy the
shape, not the specifics.*

> **How to read this.** The phase logic, ORBAT, geography, ROE, and historical references are
> **real** (from `khe_sanh_niagara.yaml` and the record of the siege). **Callsigns, frequencies,
> code words, TOTs, meter values and exact target coordinates are illustrative** — marked *(ex.)* —
> they come from the mission you generate each turn, not the campaign file. Khe Sanh is
> **dynamic**: the automated NVA axis keeps pressing, so re-plan each turn off the live map, the
> SITREP, and the **campaign status ribbon** (phase + Political Will + Regime Resolve). The arc
> mirrors the real opening: the opening bombardment, the early hill fights, and the Lang Vei
> armor threat. *(The campaign clock reads 15 July 1968 — a snow-avoidance concession; the history
> is January–April.)*

> **The standing ROE (Act I — Rolling Thunder):** the **Sukhumi sanctuary (20 NM)** is off-limits
> and the deep target classes (factories, depots, airfields…) are **locked**. Everything in these
> three briefs is legal: the perimeter, the guns, the armor, the convoys, the bridges. The kneeboard
> cover page prints the ROE every mission — check it before you frag anything deep.

---

## Turn 1 — Hold the perimeter & keep the lifeline open

**Intent:** don't lose Khe Sanh on day one. Blunt the closest assault, keep the airlift flowing into
Kutaisi + Hill 881S, and start finding the guns. (Historically: 21 Jan — the ammo dump is gone, Hill
861 is under assault, the siege is on.)

```
======================  KHE SANH — MISSION BRIEF  ======================
OP / TURN / DATE: Niagara · Turn 1 · 15 JUL 1968
MISSION #: 001      MC: COVEY LEAD (ex.)

1. SITUATION
   Last turn (SITREP): campaign open — the ammo dump is hit, the base is encircled.
   The meters: WILL 100 · RESOLVE 100 (ex.) · Phase: ROLLING THUNDER —
     Sukhumi sanctuary 20 NM, deep classes locked (cover page).
   Siege now: single front ~7 km off the wire on the Senaki axis. Airlift is the lifeline.
   Enemy: hill artillery + AAA; armor reported toward Lang Vei (Kobuleti);
          expect rocket/mortar harassment on the strip. No MiGs over the base; flak everywhere.
   Friendly: 26th Marines holding the hills (881S/861); airlift inbound.
   Weather / light: DAY. [ceiling/vis — expect monsoon crachin] (ex.).

2. MISSION
   "The Niagara package will fly FAC-controlled CAS on the Khe Sanh perimeter and escort the
    airlift into Kutaisi/Hill 881S, in order to hold the base and keep the lifeline open."

3. EXECUTION
   a. Main effort: KEEP THE BASE ALIVE — perimeter CAS + protect the airlift. Find the guns.
   b. Scheme of maneuver:
        - PUSH 0+00. Contact pt: bullseye "ROCKPILE" (ex.). FAC on station first.
        - COVEY 1   — OV-10 FAC(A) — finds/marks the assault + ranging guns; runs the stack.
        - SANDY 1-2 — A-1H Skyraider — perimeter CAS under COVEY (napalm/snake/guns).
        - HOG 1-2   — AH-1W gunships — close perimeter / hill-side suppression.
        - TRASH 1   — C-130 — airlift into Kutaisi; HOOK 1 (UH-1H) medevac/resupply Hill 881S.
        - CRUSADER 1-2 — F-8E — light BARCAP (the MiGs ambush late and close — stay between
          them and the strikers).
   c. Game plan vs. the GUNS:
        - Hard deck / roll-in: stay above the auto-AAA floor; COVEY calls the active guns.
        - Run-in: vary axis every pass; NO repeat passes on one heading. Shilka up -> new axis.
          (The flak gauntlet tightens on steady flying — jink and it loosens.)
        - Airlift: suppress any gun ranging the strip before TRASH 1 commits.
   d. ROE check: all targets are perimeter/road — legal. Nothing within 20 NM of Sukhumi.
   e. Loadout: SANDY napalm + snake + guns; see role cards. (Editor enforces the '68 list.)
   f. Success: perimeter held, airlift delivered, ≥1 gun position located/marked.
      Abort: weather below mins -> radar-bomb or divert; FAC off-station -> no uncontrolled drops.

4. COORDINATION & COMMS              (all freqs ex. — set in tool)
   FAC(A) COVEY: 35.0 FM   AWACS (EC-121) "ETHAN": 271.0   Khe Sanh tower: [____]
   Package: 254.0   Guard: 243.0   Bullseye: ROCKPILE
   Code — PUSH "NIAGARA"  CLEARED HOT "CLEARED HOT"  ABORT "KNOCK-IT-OFF"  TIC "BROKEN ARROW"

5. ADMIN & SAR
   Bingo/Joker per fuel card. Divert: Da Nang (Batumi) / carrier.
   Combat SAR: SANDY doubles as rescue escort; pickup helo on alert. A downed pilot is a RACE —
   the NVA snatch teams go for the survivor, and a POW drains Will every turn held.
   If down: off the LZ-side slope to cover, guard freq, SANDY runs it.

6. CONTINGENCIES
   - Crachin closes the target: shift to radar bombing (Skyspot/TPQ) or divert.
   - Gun ranging the strip: SANDY/HOG suppress before the C-130 commits.
   - Assault on a hill (TIC): COVEY prioritises danger-close CAS on the assault.
========================================================================
```

---

## Turn 2 — Beat down the guns & find the armor

**Intent:** suppress the hill AAA so strikers can work, start killing the artillery (Co Roc + hill
guns), and pin down where the Lang Vei armor is staging.

```
======================  KHE SANH — MISSION BRIEF  ======================
OP / TURN / DATE: Niagara · Turn 2 · 15 JUL 1968 (+1)
MISSION #: 002      MC: COVEY LEAD (ex.)

1. SITUATION
   Last turn (SITREP): [Turn 1 — perimeter held? airlift in? guns located? losses/rescues?]
   The meters: WILL [___] · RESOLVE [___] · Phase: ROLLING THUNDER (unchanged).
   Siege now: front holding near the wire; artillery still ranging the base from the hills.
   Enemy: AAA on the hill mass; PT-76/T-54 staging toward Lang Vei (Kobuleti);
          convoy traffic reported on Route 9 behind the front.
   Friendly: airlift continuing; recon up to map the guns and the armor.

2. MISSION
   "The Niagara package will conduct FAC-controlled strikes to suppress the hill AAA and
    destroy located artillery, while photo recon fixes the Lang Vei armor, in order to set
    conditions for the anti-armor strike and keep the perimeter safe."

3. EXECUTION
   a. Main effort: SUPPRESS THE GUNS + FIND THE ARMOR. Keep the airlift flowing.
   b. Scheme of maneuver:
        - SLICE 1 (RF-101B) / EYE 1 (RA-5C) — TARPS photo recon: film the AAA, the artillery,
          the armor. (Film = confirmed intel; what you don't photograph stays fogged.)
        - COVEY 1 (OV-10) — FAC: mark the active guns; run the strike stack.
        - HOBO 1-4 (A-4E / F-100D) — beat down the hill AAA; hit located artillery.
        - BUFF 1 (B-52) — first Arc Light box on a massed assembly area [grid from recon] (ex.)
          — OUTSIDE the sanctuary ring, always. One BUFF lost = a Will crater; keep it high
          and clear of the 57mm.
        - SANDY 1-2 (A-1H) — on-call perimeter CAS; airlift escort as needed.
   c. Game plan vs. the GUNS:
        - Roll in from above the 57mm ceiling; Rockeye/CBU on the gun pits COVEY marks.
        - Shilka called -> terrain-mask, re-attack new axis. One pass when hot.
        - Arc Light box deconflicted by time/area from all tac air.
   d. ROE check: Arc Light box + all strikes verified outside 20 NM of Sukhumi; no locked
      classes on the frag.
   e. Success: hill AAA degraded, ≥1 artillery position killed, armor photographed + a strike
      planned. Abort the strike (not the FAC) if weather closes it — keep CAS + airlift going.

4. COORDINATION & COMMS   (ex.)
   COVEY 35.0 FM · ETHAN (EC-121) 271.0 · Pkg 254.0 · Guard 243.0 · Bullseye ROCKPILE
   PUSH "NIAGARA" · CLEARED HOT · ABORT "KNOCK-IT-OFF" · ARC LIGHT BOX HOT "HEAVY HAND"

5. ADMIN & SAR
   SANDY rescue escort + pickup on alert. Eject contract per handbook §12 — win the race.

6. CONTINGENCIES
   - Armor not photographed: SLICE re-tasks; anti-armor strike slips to Turn 3 fully.
   - Heavy AAA on the briefed axis: COVEY shifts the IP; attack from a new bearing.
   - Arc Light weathered out: hold the box, re-time; tac air keeps suppressing.
========================================================================
```

---

## Turn 3 — Kill the Lang Vei armor & cut the road

**Intent:** destroy the PT-76/T-54 at Lang Vei before it can repeat history against a hill or the
wire, keep pounding the artillery, and open the convoy war on Route 9.
(Historically: the night of 6–7 Feb, NVA armor overran Lang Vei — beat them to it.)

```
======================  KHE SANH — MISSION BRIEF  ======================
OP / TURN / DATE: Niagara · Turn 3 · 15 JUL 1968 (+2)
MISSION #: 003      MC: COVEY LEAD (ex.)

1. SITUATION
   Last turn (SITREP): [Turn 2 — AAA degraded? artillery hit? armor filmed at Lang Vei?]
   The meters: WILL [___] · RESOLVE [___] · Phase: ROLLING THUNDER.
   Siege now: front holding; armor massed near Lang Vei (Kobuleti) — the danger.
   Enemy: PT-76/T-54 at Lang Vei; residual hill AAA; convoys feeding the spearhead
          down Route 9 (every leg crosses a bridge).
   Friendly: airlift steady; the anti-armor strike is fragged off Turn 2's film.

2. MISSION
   "The Niagara package will destroy the Lang Vei armor and interdict the Route 9 supply
    flow, in order to remove the armor threat and start starving the siege."

3. EXECUTION
   a. Main effort: KILL THE ARMOR at Lang Vei (Kobuleti). Secondary: the road + counter-battery.
   b. Scheme of maneuver:
        - COVEY 1 (OV-10) — FAC over Lang Vei; mark the armor; control the strike.
        - INTRUDER 1-4 (A-6E) — ROCKEYE on the PT-76/T-54 column under COVEY.
        - HOBO 1-2 (A-4E) — flak suppression around the armor + counter-battery on hill guns.
        - TRAIL 1-2 (A-1H) — Armed Recon on Route 9 (right-click the supply route on the map
          — the package pre-fills). Kill the convoy; drop a span behind it.
        - SANDY 1-2 (A-1H) — perimeter CAS / airlift escort continues (don't drop the lifeline).
   c. Game plan vs. the GUNS:
        - Medium-alt Rockeye deliveries; HOBO suppresses the guns around the armor first.
        - Vary axis; Shilka -> mask + new axis; one pass when hot.
   d. ROE check: Lang Vei, the road, and the bridges are all legal Act-I targets.
   e. Success: armor destroyed; a convoy killed or a span dropped; counter-battery continued.
      Abort the armor strike if the FAC can't fix it / weather closes it — keep CAS + airlift.

4. COORDINATION & COMMS   (ex.)
   COVEY 35.0 FM · ETHAN (EC-121) 271.0 · Pkg 254.0 · Guard 243.0 · Bullseye ROCKPILE
   PUSH "NIAGARA" · CLEARED HOT · ABORT "KNOCK-IT-OFF" · ARMOR KILLED "STEEL RAIN"

5. ADMIN & SAR
   SANDY + pickup on alert; deep-ish push toward Lang Vei — brief the eject/SAR contract (§12):
   the snatch teams will race you, and a POW bleeds Will every turn.

6. CONTINGENCIES
   - Armor already moving on the wire (TIC): COVEY runs danger-close CAS to stop it first.
   - Weather closes Lang Vei: A-6E radar deliveries or slip the strike; keep counter-battery up.
   - Convoy through before TRAIL arrives: it reinforces the front — expect a harder wire.
========================================================================
```

---

## After Turn 3 — where this goes

Per the [campaign plan](Khe-Sanh-Campaign-Briefing#6--campaign-conops--the-phase-plan), the
authored arc takes over the calendar:

- **~Turn 8 — The Bombing Halt:** the sanctuary expands to 28 NM, **red surges the trail and
  Hanoi's resolve regenerates**. The convoy war (TRAIL packages, bridge cuts) becomes the main
  effort — the Halt punishes a passive blue.
- **~Turn 11 — Linebacker:** the deep classes **release** (depots, ammo, **Senaki airfield**) and
  red answers with a **3-turn ground offensive** at the wire. Survive the push, then roll back the
  freed target set.
- **~Turn 16 — Linebacker II:** no sanctuaries, no locked classes. Force the ending — grind
  **Regime Resolve** to zero, or take the ring by **Air Assault** (the static front never sweeps;
  the helos are the territorial lever — Operation Pegasus, heliborne).

Bleeding Political Will accelerates every one of those dates — Washington's patience for restraint
runs out faster when the war is going badly.

> Re-plan every turn off the **live map, the SITREP, and the two meters**, not this script. The
> value is the *loop*: keep the base fed → suppress the guns → kill the massed ground (armor,
> artillery, convoys) → manage the arc → break them. **The air keeps the base alive; the ground
> fight and the meters win it.**

---

*Companion docs: [Campaign Briefing Handbook](Khe-Sanh-Campaign-Briefing) ·
[Role kneeboard cards](Khe-Sanh-Role-Cards) ·
[Intel assessment (history)](Khe-Sanh-Intel-Assessment) ·
[Visual briefing](Khe-Sanh-Visual-Briefing) ·
[Vietnam Campaign Layer](Vietnam-Campaign-Layer) (the will/ROE mechanics) ·
[Vietnam Ops](Vietnam-Ops) (the period runtime suite). Callsigns/freqs/code words here are
illustrative and freely editable; the ORBAT, phase logic, ROE, and historical references are from
the campaign files and the record of the siege.*


---

*This page is the online copy of [`docs/campaigns/khe-sanh-first-three-turns.md`](https://github.com/bradyccox/414Ret/blob/main/docs/campaigns/khe-sanh-first-three-turns.md) in the repo. Edit that file; the wiki is mirrored from `docs/wiki/` on merge to `main`.*
