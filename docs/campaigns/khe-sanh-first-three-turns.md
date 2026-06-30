# Khe Sanh: Operation Niagara — Worked Example: The First Three Turns

*A filled-in model for the [Campaign Briefing Handbook](khe-sanh-campaign-handbook.md) mission-brief
template. These three turns walk Phases 0→2 of the
[phase plan](khe-sanh-campaign-handbook.md#5--campaign-conops--the-phase-plan):
**hold the perimeter and the lifeline → beat down the guns → kill the Lang Vei armor.** Copy the
shape, not the specifics.*

> **How to read this.** The phase logic, ORBAT, geography, and historical references are **real**
> (from `khe_sanh_niagara.yaml` and the record of the siege). **Callsigns, frequencies, code words,
> TOTs and exact target coordinates are illustrative** — marked *(ex.)* — they come from the mission
> you generate each turn, not the campaign file. Khe Sanh is **dynamic**: the automated NVA Route 9
> corridor keeps pressing, so re-plan each turn off the live map and the SITREP. The arc mirrors the real
> opening: the 21 Jan bombardment, the early hill fights, and the 6–7 Feb Lang Vei armor assault.

---

## Turn 1 — Hold the perimeter & keep the lifeline open *(Phase 0)*

**Intent:** don't lose Khe Sanh on day one. Blunt the closest assault, keep the airlift flowing into
Kutaisi + Hill 881S, and start finding the guns. (Historically: 21 Jan — the ammo dump is gone, Hill
861 is under assault, the siege is on.)

```
======================  KHE SANH — MISSION BRIEF  ======================
OP / TURN / DATE: Niagara · Turn 1 · 21 JAN 1968
MISSION #: 001      MC: COVEY LEAD (ex.)

1. SITUATION
   Last turn (SITREP): campaign open — the ammo dump is hit, the base is encircled.
   Siege now: the Route 9 front sits tight against Kutaisi (0.25). Airlift is the only lifeline.
   Enemy: hill artillery + AAA (Sukhumi); armor reported toward Lang Vei (Kobuleti);
          Co Roc guns range the base. No MiGs over the base; flak everywhere.
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
        - CRUSADER 1-2 — F-8E — light BARCAP (token MiG insurance), flex to armed recon.
   c. Game plan vs. the GUNS:
        - Hard deck / roll-in: stay above the auto-AAA floor; COVEY calls the active guns.
        - Run-in: vary axis every pass; NO repeat passes on one heading. Shilka up -> new axis.
        - Airlift: suppress any gun ranging the strip before TRASH 1 commits.
   d. Loadout: SANDY napalm + snake + guns; see role cards.
   e. Success: perimeter held, airlift delivered, ≥1 gun position located/marked.
      Abort: weather below mins -> radar-bomb or divert; FAC off-station -> no uncontrolled drops.

4. COORDINATION & COMMS              (all freqs ex. — set in tool)
   FAC(A) COVEY: 35.0 FM   AWACS (EC-121) "ETHAN": 271.0   Khe Sanh tower: [____]
   Package: 254.0   Guard: 243.0   Bullseye: ROCKPILE
   Code — PUSH "NIAGARA"  CLEARED HOT "CLEARED HOT"  ABORT "KNOCK-IT-OFF"  TIC "BROKEN ARROW"

5. ADMIN & SAR
   Bingo/Joker per fuel card. Divert: Da Nang (Batumi) / carrier.
   Combat SAR: SANDY doubles as rescue escort; DUSTOFF (UH-1H) on alert. (Pilots invuln this campaign.)
   If down: off the LZ-side slope to cover, guard freq, SANDY runs it.

6. CONTINGENCIES
   - Crachin closes the target: shift to radar bombing (Skyspot/TPQ) or divert.
   - Gun ranging the strip: SANDY/HOG suppress before the C-130 commits.
   - Assault on a hill (TIC): COVEY prioritises danger-close CAS on the assault.
========================================================================
```

---

## Turn 2 — Beat down the guns & find the armor *(Phase 1)*

**Intent:** suppress the hill AAA so strikers can work, start killing the artillery (Co Roc + hill
guns), and pin down where the Lang Vei armor is staging.

```
======================  KHE SANH — MISSION BRIEF  ======================
OP / TURN / DATE: Niagara · Turn 2 · 21 JAN 1968 (+1)
MISSION #: 002      MC: COVEY LEAD (ex.)

1. SITUATION
   Last turn (SITREP): [Turn 1 — perimeter held? airlift in? guns located?]
   Siege now: the Route 9 front is holding; artillery still ranging the base from the hills + Co Roc.
   Enemy: AAA on the Sukhumi hills; PT-76/T-54 staging toward Lang Vei (Kobuleti).
   Friendly: airlift continuing; recon up to map the guns and the armor.

2. MISSION
   "The Niagara package will conduct FAC-controlled strikes to suppress the hill AAA and
    destroy located artillery, while armed recon fixes the Lang Vei armor, in order to set
    conditions for the anti-armor strike and keep the perimeter safe."

3. EXECUTION
   a. Main effort: SUPPRESS THE GUNS + FIND THE ARMOR. Keep the airlift flowing.
   b. Scheme of maneuver:
        - SLICE 1-2 (RF-101B / RA-5C) — recon: map the AAA, the hill artillery, the armor.
        - COVEY 1 (OV-10) — FAC: mark the active guns; run the strike stack.
        - HObo 1-4 (A-4E / F-100D) — beat down the hill AAA; hit located artillery.
        - BUFF 1 (B-52) — first Arc Light box on a massed assembly area [grid from recon] (ex.).
        - SANDY 1-2 (A-1H) — on-call perimeter CAS; airlift escort as needed.
   c. Game plan vs. the GUNS:
        - Roll in from above the 57mm ceiling; Rockeye/CBU on the gun pits COVEY marks.
        - Shilka called -> terrain-mask, re-attack new axis. One pass when hot.
        - Arc Light box deconflicted by time/area from all tac air.
   d. Loadout: HObo Rockeye/snake/napalm; BUFF area load. See role cards.
   e. Success: hill AAA degraded, ≥1 artillery position killed, armor located + a strike planned.
      Abort the strike (not the FAC) if weather closes it — keep CAS + airlift going.

4. COORDINATION & COMMS   (ex.)
   COVEY 35.0 FM · ETHAN (EC-121) 271.0 · Pkg 254.0 · Guard 243.0 · Bullseye ROCKPILE
   PUSH "NIAGARA" · CLEARED HOT · ABORT "KNOCK-IT-OFF" · ARC LIGHT BOX HOT "HEAVY HAND"

5. ADMIN & SAR
   SANDY rescue escort + DUSTOFF on alert. Eject contract per handbook §11.

6. CONTINGENCIES
   - Armor not located: SLICE re-tasks; anti-armor strike slips to Turn 3 fully.
   - Heavy AAA on the briefed axis: COVEY shifts the IP; attack from a new bearing.
   - Arc Light weathered out: hold the box, re-time; tac air keeps suppressing.
========================================================================
```

---

## Turn 3 — Kill the Lang Vei armor *(Phase 2 opens)*

**Intent:** destroy the PT-76/T-54 at Lang Vei before it can repeat history against a hill or the
wire, keep pounding the artillery, and start driving the Route 9 front back from the perimeter toward
Senaki (Pegasus). (Historically: the night of 6–7 Feb, NVA armor overran Lang Vei — beat them to it.)

```
======================  KHE SANH — MISSION BRIEF  ======================
OP / TURN / DATE: Niagara · Turn 3 · 21 JAN 1968 (+2)
MISSION #: 003      MC: COVEY LEAD (ex.)

1. SITUATION
   Last turn (SITREP): [Turn 2 — AAA degraded? artillery hit? armor fixed at Lang Vei?]
   Siege now: the Route 9 front is holding; armor massed at Lang Vei (Kobuleti) feeding the Senaki spearhead — the danger.
   Enemy: PT-76/T-54 at Lang Vei; residual hill AAA; Co Roc guns still firing.
   Friendly: airlift steady; the Khe Sanh perimeter ready to start the Pegasus push out along Route 9.

2. MISSION
   "The Niagara package will destroy the Lang Vei armor and continue counter-battery strikes,
    while the ground force begins the push up Route 9, in order to remove the armor threat and
    open Phase 2/Pegasus."

3. EXECUTION
   a. Main effort: KILL THE ARMOR at Lang Vei (Kobuleti). Secondary: counter-battery + CAS.
   b. Scheme of maneuver:
        - COVEY 1 (OV-10) — FAC over Lang Vei; mark the armor; control the strike.
        - INTRUDER 1-4 (A-6E) — ROCKEYE on the PT-76/T-54 column under COVEY.
        - HObo 1-2 (A-4E) — flak suppression around the armor + counter-battery on hill guns.
        - BUFF 1 (B-52) — Arc Light on the NVA assembly/rear feeding the armor.
        - SANDY 1-2 (A-1H) — perimeter CAS / airlift escort continues (don't drop the lifeline).
   c. Game plan vs. the GUNS:
        - Medium-alt Rockeye deliveries; HObo suppresses the guns around the armor first.
        - Vary axis; Shilka -> mask + new axis; one pass when hot.
   d. Loadout: INTRUDER Rockeye-heavy; see role cards.
   e. Success: armor destroyed; counter-battery continued; the Senaki front starts to yield up Route 9.
      Abort the armor strike if the FAC can't fix it / weather closes it — keep CAS + airlift.

4. COORDINATION & COMMS   (ex.)
   COVEY 35.0 FM · ETHAN (EC-121) 271.0 · Pkg 254.0 · Guard 243.0 · Bullseye ROCKPILE
   PUSH "NIAGARA" · CLEARED HOT · ABORT "KNOCK-IT-OFF" · ARMOR KILLED "STEEL RAIN"

5. ADMIN & SAR
   SANDY + DUSTOFF on alert; deep-ish push toward Lang Vei — brief the eject/SAR contract (§11).

6. CONTINGENCIES
   - Armor already moving on the wire (TIC): COVEY runs danger-close CAS to stop it first.
   - Weather closes Lang Vei: A-6E radar deliveries or slip the strike; keep counter-battery up.
   - Front stalls: more BAI/CAS on the Senaki spearhead (and its Lang Vei/hill feeders) before pushing again.
========================================================================
```

---

## After Turn 3 — where this goes

Per the [phase plan](khe-sanh-campaign-handbook.md#5--campaign-conops--the-phase-plan): finish
**Phase 2** (clear the armor and the worst of the hill artillery), then run **Phase 3 — Operation
Pegasus**: drive the **Senaki front** back off the Khe Sanh perimeter and **retake Senaki** to break
the siege, then roll up the now-frontline feeder bases (**Lang Vei/Kobuleti**, the **hills/Sukhumi**) —
with CAS/BAI ahead of the advance, bridge interdiction on the NVA supply spans, Arc Light on the
divisional rear, and the airlift running until the road opens. (Historically: Pegasus, 1–14 April
1968 — the 1st Cavalry up Route 9, link-up 8 April.)

> Re-plan every turn off the **live map + SITREP**, not this script. The value is the *loop*: keep
> the base fed → suppress the guns → kill the massed ground (armor, artillery, infantry) → push the
> relief. **The air keeps the base alive; the ground fight wins it.**

---

*Companion docs: [Campaign Briefing Handbook](khe-sanh-campaign-handbook.md) ·
[Role kneeboard cards](khe-sanh-role-cards.md) ·
[Intel assessment (history)](khe-sanh-intel-assessment.md) ·
[Visual briefing](khe-sanh-visual-briefing.md). Callsigns/freqs/code words here are illustrative and
freely editable; the ORBAT, phase logic, and historical references are from the campaign files and
the record of the siege.*
