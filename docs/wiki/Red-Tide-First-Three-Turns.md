# Operation Red Tide — Worked Example: The First Three Turns

*A filled-in model for the [Campaign Briefing Handbook](Red-Tide-Campaign-Briefing) mission-brief
template. These three turns walk Phases 0→2 of the [phase plan](Red-Tide-Campaign-Briefing#5--campaign-conops--the-phase-plan):
**win the air over the Fulda front → pry the western SAM belt open → take Haina and blind him.** Copy
the shape, not the specifics.*

> **How to read this.** Squadrons, airframes, bases and the phase logic are **real** (from
> `red_tide.yaml`). **Callsigns, frequencies, code words, TOTs and exact target coordinates are
> illustrative** — marked *(ex.)* — because they come from the mission you generate each turn, not
> from the campaign file. Red Tide is **dynamic**: the front, the threats, and what red did last
> turn will reshuffle this. Use it as a starting template, then plan off the live map and the SITREP.

---

## Turn 1 — Win the air over the Fulda front *(Phase 0)*

**Intent:** own the sky on the Fulda→Haina axis so strikers can work next turn. Don't go deep yet —
establish CAP, take the first measure of red's SAMs from standoff, and keep the FLOT covered.

```
========================  RED TIDE — MISSION BRIEF  ========================
OP / TURN / DATE: Red Tide · Turn 1 · 13 JUL 1988
MISSION #: 001      MC: AXEMAN (ex.)

1. SITUATION
   Last turn (SITREP): campaign open — no prior turn.
   FLOT now: front runs Fulda (BLUE FARP) ↔ Haina (RED). Red holds centre/north/east.
   Enemy: Haina fighters (MiG-23MLD 33rd IAP, MiG-27K 19th Gv) contest the front; Hamburg
          MiG-29s (85th GvIAP) may push south. Mobile SA-6/SA-11 west of Haina, exact sites TBD.
   Friendly: ground holding the Gap; our push starts in the air this turn.
   Weather / light: day, [ceiling/vis from the gen] (ex.).

2. MISSION
   "414th air-superiority package will sweep and hold a BARCAP/TARCAP wall on the Fulda–Haina
    axis, and a DEAD element will probe the western SAM belt from standoff, in order to win local
    air superiority over the front and set the corridor for Turn 2."

3. EXECUTION
   a. Commander's intent / main effort: OWN THE AIR over the front. Strikers don't push until the
      CAP wall is up. DEAD probe is reconnaissance-by-HARM — find/punish, don't get dragged deep.
   b. Scheme of maneuver:
        - PUSH 0+00. Marshal: bullseye "ANVIL" (ex.). On-station block 0+15 to Joker.
        - SLAYER 1-2  — F-14B (VMF-29) — high BARCAP, owns BVR over the Gap. AIM-54/7/9.
        - EAGLE 1-2   — F-15C (493rd, AI) — TARCAP, second CAP layer / sweep.
        - MOELDER 1-2 — GAF JG 74 F-4E — forward TARCAP, low/medium, mops vectored Floggers.
        - VOODOO 1-2  — F-16CM (414th Voodoo) — DEAD probe, HARM standoff on western SA-6/11.
        - HORNET 1-2  — F/A-18C (414th JFG) — SEAD escort for VOODOO; reactive HARM.
        - HOG 1-2     — A-10C (81st TFS) + WIDOW (1-1 ARB AH-64D, Fulda) — FLOT CAS as tasked.
   c. Game plan vs. threats:
        - Air: SLAYER owns BVR; commit on AWACS picture; no solo merges with Fulcrums (extend,
          re-attack). MOELDER/EAGLE backstop. Abort a chase that drags you over Haina's SAMs.
        - SAM: VOODOO/HORNET stay OUTSIDE the suspected S-300 ring; HARM the mobiles if they light
          up, then crank away. Do NOT prosecute fixed long-range sites this turn.
        - Floor near FLOT: no lower than [hard deck] over contested ground (SHORAD/ZSU).
   d. Loadout: see role cards. Period-correct '88 A2A + HARM.
   e. Success: CAP wall held, front air contested in our favour, ≥1 western SAM located/suppressed.
      Abort: lose 2+ of the CAP wall, or AWACS down → consolidate, RTB, re-plan.

4. COORDINATION & COMMS                (all freqs ex. — set in tool)
   AWACS: OVERLORD 251.0   Tanker(boom): TEXACO 252.0   Tanker(drogue): ARCO 253.0
   Package: 254.0   Inter-flight: own   Guard: 243.0   Bullseye: ANVIL
   Code — PUSH "SABRE"  SUCCESS "HOMERUN"  ABORT "KNOCK-IT-OFF"  THREAT "SNAKES"

5. ADMIN & SAR
   Bingo/Joker per fuel card. Divert: Frankfurt/Ramstein.
   Combat SAR: KING (910th C-130J) overhead for EW/ISR + on-scene cmd; SANDY = HOG flight if needed.
   If you eject: clear the area, high ground, guard freq, KING runs it. (See SAR caveats — handbook §11.)

6. CONTINGENCIES
   - Tanker no-show: shorten on-station, stagger RTB.
   - SAM corridor hotter than expected: VOODOO/HORNET stand off, mark sites for Turn 2, don't press.
   - CAP committed away: strikers/CAS hold south of the FLOT until re-covered.
===========================================================================
```

---

## Turn 2 — Pry the western SAM belt open *(Phase 1)*

**Intent:** with the air contested in our favour, punch a SEAD corridor toward Haina and start
killing the convoys feeding red's front. This is the turn the strikers earn their keep.

```
========================  RED TIDE — MISSION BRIEF  ========================
OP / TURN / DATE: Red Tide · Turn 2 · 13 JUL 1988 (+1)
MISSION #: 002      MC: AXEMAN (ex.)

1. SITUATION
   Last turn (SITREP): [Turn 1 losses/claims from the kneeboard cover]. Western SAM picture from
   Turn 1's probe — fly TODAY's recon, the mobiles may have moved.
   FLOT now: Fulda↔Haina, [any movement].
   Enemy: SA-6/SA-11 belt W of Haina; fixed S-300/S-200 deeper. Haina CAP attrited but present.
   Friendly: CAP wall re-established first; strikers follow.

2. MISSION
   "DEAD package will open and hold a SEAD corridor through the western SAM belt while a BAI
    element interdicts the Haina-bound convoys, in order to make Haina strikeable on Turn 3 and
    bleed red's ability to reinforce the front."

3. EXECUTION
   a. Main effort: the SEAD CORRIDOR. The BAI strike only pushes once the corridor is declared open.
   b. Scheme of maneuver:
        - PUSH 0+00. CAP up first (SLAYER/EAGLE). Corridor declared on VOODOO's call.
        - VOODOO 1-4 — F-16CM (414th Voodoo) — DEAD lead. HARM + Maverick, kill the mobiles,
          hold the lane. Pre-emptive + reactive HARM.
        - HORNET 1-2 — F/A-18C (414th JFG) — SEAD escort, suppress pop-ups along the route.
        - PANZER 1-2 — Tornado IDS (JBG 31, AI) — SEAD escort backup / loft.
        - BOLT 1-4   — F-15E (414th TFS) — BAI on the convoy column [grid from recon] (ex.).
        - SLAYER 1-2 — F-14B (VMF-29) — TARCAP, shields the package from Haina/ Hamburg fighters.
   c. Game plan vs. threats:
        - SAM: route AROUND the fixed S-300/S-200 rings (handbook §10); VOODOO services the mobile
          SA-6/SA-11 in the lane. "MAGNUM" calls deconflicted on package freq.
        - Air: SLAYER commits forward of the strikers; BOLT runs in only inside the declared corridor.
        - Watch the Su-24M (Fencer) — it's red's SEAD shooter and will hunt VOODOO/HORNET on egress.
   d. Loadout: VOODOO/HORNET HARM-heavy; BOLT CBU/Mk-82/Maverick. Role cards.
   e. Success: corridor open + held through the BAI run; convoy serviced. Abort the strike (not the
      SEAD) if the corridor can't be opened — keep the SEAD, drag the strikers home.

4. COORDINATION & COMMS   (ex.)
   AWACS OVERLORD 251.0 · TEXACO 252.0 (boom) · ARCO 253.0 (drogue) · Pkg 254.0 · Guard 243.0
   Bullseye ANVIL · PUSH "SABRE" · SUCCESS "HOMERUN" · ABORT "KNOCK-IT-OFF" · CORRIDOR OPEN "GATEWAY"

5. ADMIN & SAR
   KING overhead (EW/ISR + cmd). SANDY = a HOG/Apache element on alert. Eject contract per §11.

6. CONTINGENCIES
   - Mobile SAMs relocated/no joy: VOODOO sanitizes; if the lane won't open, BAI aborts to a
     softer target off the IADS, SEAD covers the egress.
   - Fencer threat on egress: SLAYER sweeps the egress lane; everyone checks six off target.
===========================================================================
```

---

## Turn 3 — Take Haina and blind him *(Phase 2 opens)*

**Intent:** with a corridor open, strangle Haina (OCA on its runway + parked jets), keep the CAS
pressure on the FLOT to push it past Haina, and set up the deliberate hunt for red's A-50/Il-78
enablers at Schönefeld.

```
========================  RED TIDE — MISSION BRIEF  ========================
OP / TURN / DATE: Red Tide · Turn 3 · 13 JUL 1988 (+2)
MISSION #: 003      MC: AXEMAN (ex.)

1. SITUATION
   Last turn (SITREP): [Turn 2 losses/claims]; corridor opened W of Haina; convoy hit.
   FLOT now: pressing toward Haina.
   Enemy: Haina degraded but defended; A-50 (144th) + Il-78 (203rd) operating from Schönefeld feed
          his GCI/fuel; Hamburg MiG-29s the northern wildcard.
   Friendly: corridor from Turn 2 (re-verify it's still open); ground ready to exploit a Haina hit.

2. MISSION
   "OCA package will strangle Haina airfield through the open corridor while a CAS element pushes
    the FLOT and a CAP/long-stick element sets conditions to hunt the A-50/Il-78, in order to
    take Haina and begin breaking red's eyes-and-reach."

3. EXECUTION
   a. Main effort: OCA on HAINA. Secondary: CAS exploitation + enabler-hunt setup.
   b. Scheme of maneuver:
        - VOODOO 1-2 + HORNET 1-2 — re-open/hold the corridor (SEAD/DEAD) ahead of the strike.
        - PHANTOM 1-4 — F-4E (512th TFS) — OCA/Runway on Haina (craters/cluster).
        - LANCER 1-2  — B-1B (37th BS, AI) — heavy OCA follow-up if tasked.
        - HOG 1-2 + WIDOW (Fulda AH-64D/OH-58D) — CAS on the FLOT W of Haina, walk the ground in.
        - SLAYER 1-2  — F-14B (VMF-29) — long-stick TARCAP toward the Schönefeld approaches;
          range/ID the A-50; this is the recce for the Phase-2 enabler kill (don't overcommit solo).
   c. Game plan vs. threats:
        - SAM: corridor must be live before PHANTOM pushes — VOODOO declares "GATEWAY" or the strike
          holds. Route the fixed rings as always.
        - Air: SLAYER screens the OCA from Hamburg/CPH fighters; if the A-50 is reachable under
          escort, flag it for a dedicated enabler-hunt next turn (handbook §8 "Enabler hunt").
        - CAS floor: stay above the ZSU/SHORAD floor; Apaches use terrain.
   d. Loadout: PHANTOM runway-cratering; CAS Maverick/Hellfire/gun/rockets. Role cards.
   e. Success: Haina cratered/strangled and trending blue; FLOT advanced; A-50 located + a kill plan
      built. Abort the OCA if the corridor collapses; keep CAS + CAP working the front.

4. COORDINATION & COMMS   (ex.)
   AWACS OVERLORD 251.0 · TEXACO/ARCO tankers · Pkg 254.0 · Guard 243.0 · Bullseye ANVIL
   PUSH "SABRE" · SUCCESS "HOMERUN" · ABORT "KNOCK-IT-OFF" · CORRIDOR "GATEWAY" · BIG-EYE (A-50) "PEEPER"

5. ADMIN & SAR
   KING overhead; SANDY on alert. Deep-ish push — brief the eject/SAR contract hard (§11).

6. CONTINGENCIES
   - Corridor closed again: PHANTOM holds; VOODOO/HORNET re-open or the OCA slips a turn.
   - A-50 pulls back deep: don't chase unescorted; build the escorted enabler-hunt for next turn.
   - Hamburg MiGs push during the OCA: SLAYER + AWACS prioritise the strike's protection over the chase.
===========================================================================
```

---

## After Turn 3 — where this goes

Per the [phase plan](Red-Tide-Campaign-Briefing#5--campaign-conops--the-phase-plan): finish
**Phase 2** (capture Haina, run the deliberate **A-50/Il-78 enabler hunt** out of Schönefeld), then
roll into **Phase 3** (the Berlin cluster + choke red's rear factories at Sperenberg/Schönefeld),
**Phase 4** (retake Hamburg up the A24 corridor), and the **Phase 5** climax — burn the 924th
Backfires and liberate Copenhagen, opening the Straits.

> Re-plan every turn off the **live map + SITREP**, not this script. The value here is the *shape*: CAP
> wall first → SEAD corridor → strike through it → exploit on the ground → take down his eyes. Repeat
> that loop eastward.

---

*Companion docs: [Campaign Briefing Handbook](Red-Tide-Campaign-Briefing) ·
[Role kneeboard cards](Red-Tide-Role-Cards) ·
[Intel assessment (lore)](Red-Tide-Intel-Assessment) ·
[Visual briefing](Red-Tide-Visual-Briefing). Callsigns/freqs/code words here are illustrative and
freely editable; the ORBAT and phase logic are from the campaign files.*


---

*This page is the online copy of [`docs/campaigns/red-tide-first-three-turns.md`](https://github.com/bradyccox/414Ret/blob/main/docs/campaigns/red-tide-first-three-turns.md) in the repo. Edit that file; the wiki is mirrored from `docs/wiki/` on merge to `main`.*
