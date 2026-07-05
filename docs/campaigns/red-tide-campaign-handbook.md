# Operation Red Tide — Campaign Briefing Handbook

*The 414th's working reference for **Germany - Red Tide** (GermanyCW, 13 July 1988). This is the
**brief-builder**: accurate friendly order of battle, a fill-in mission-brief template, package
recipes, comms and code-word cards, a phased campaign plan, and threat-defeat references you reuse
every op night. Print it, fork it, scribble on it.*

> **The Red Tide doc set — use the right tool:**
> 1. **This handbook** — the operational working reference. Real ORBAT, brief templates, package
>    recipes, comms cards, phase plan, threat-defeat. *Start here to build a brief.*
> 2. **[red-tide-intel-assessment.md](red-tide-intel-assessment.md)** — the in-fiction intel pack:
>    backstory, enemy ORBAT with lore, courses of action, the read-aloud spoken brief, and the
>    one-page pilot threat card. *Use it for narrative colour and the mass brief.*
> 3. **[red-tide-visual-briefing.md](red-tide-visual-briefing.md)** — the picture brief: theater
>    map, SAM-ring profile, target-priority flow, ORBAT diagrams. *Use it for the screen-share.*
>
> Everything tactical here is grounded in the actual `red_tide.yaml` / `red_tide.miz` files. The
> regiment names, callsigns, and "ZAPAD" operation name are *Red Storm Rising*-style fiction and
> freely editable.

> 🟢🟡 **Provenance & confidence — read this.** The three companion lore docs above were written
> *ahead of the build* as narrative; treat them as flavour, not spec. In **this** handbook:
> - **File-confirmed (trust it):** friendly & enemy ORBAT (squadron names / airframes / sizes /
>   bases), economy & settings, supply routes — all read straight from `red_tide.yaml`; the enemy
>   SAM/EWR/Scud/naval list — read straight from `russia_1980.json`.
> - **Designed but not yet flown (verify in-game):** the **IADS networking** behaviour (whether
>   killing a base's C2/power actually drops its SAMs), the **dedicated red EWR coverage** (markers
>   added 2026-06-28, headless-validated only), and the **Combat SAR** capture/rescue mechanics —
>   all carry open items on the in-game-pass checklist. These are flagged 🟡 where they appear.
>   Don't promise them as facts in a mass brief until someone's flown them.

---

## Table of contents

1. [Campaign at a glance](#1--campaign-at-a-glance)
2. [Win conditions & how the front moves](#2--win-conditions--how-the-front-moves)
3. [Friendly order of battle (real, from the campaign)](#3--friendly-order-of-battle)
4. [The enemy in one screen](#4--the-enemy-in-one-screen)
5. [Campaign CONOPS — the phase plan](#5--campaign-conops--the-phase-plan)
6. [Weekly op-night runbook](#6--weekly-op-night-runbook)
7. [The mission brief template (fill-in)](#7--the-mission-brief-template)
8. [Package recipes (build a package fast)](#8--package-recipes)
9. [Comms & code-word card](#9--comms--code-word-card)
10. [Threat-defeat quick reference](#10--threat-defeat-quick-reference)
11. [Combat SAR — when a pilot goes down](#11--combat-sar--when-a-pilot-goes-down)
12. [Loadout & role pairing notes](#12--loadout--role-pairing-notes)
13. [Appendix A — blank one-page brief sheet](#appendix-a--blank-one-page-brief-sheet)
14. [Appendix B — mission log / debrief sheet](#appendix-b--mission-log--debrief-sheet)

---

## 1 · Campaign at a glance

| Item | Value |
|---|---|
| **Campaign** | Germany - Red Tide (fork of Crossing the Rubicon) |
| **Theater** | GermanyCW (Cold War Germany) |
| **Date / setting** | 13 July 1988 — *Red Storm Rising*-style WP–NATO war, gone hot |
| **Our side** | **Blufor Late Cold War (80s)** — the 414th Joint Fighter Group, multinational NATO wing |
| **Enemy** | **Russia 1980** — 16th Air Army + Frontal/Naval Aviation + Baltic Fleet |
| **Posture** | **NATO counteroffensive.** The Soviet thrust has *culminated*; we attack to roll it back |
| **Economy skew** | Blue favoured — start $800 / income ×1.3 vs red $400 / ×0.7 |
| **IADS** | `advanced_iads: true` set in the YAML; per-base C2 statics placed in the `.miz`. 🟡 Networked "kill-C2-to-drop-SAMs" behaviour is **unverified in-game** (see §4/§10) |
| **Auto-planner** | Tuned **human-led**: blue AI flies cautious so *your* sorties are the spearhead |
| **Op night** | Saturdays, 8 PM EST (squadron op) |

**The one-sentence situation:** the Warsaw Pact opened the war, took Hamburg and Copenhagen, then
ran out of fuel and air cover; the line held; **now we take it all back before he can dig in.**

---

## 2 · Win conditions & how the front moves

Red Tide is a **dynamic campaign** — the front line moves turn-to-turn based on what happens in the
air and on the ground. There is no scripted ending; you win by **capturing red control points and
pushing the FLOT east** until the red salient collapses.

**The objective set (geography):**

- **Near term:** clear the **Fulda → Haina** axis (the front line runs through it) and take **Haina**
  (161), red's forward air hub on the western tip of the salient.
- **Mid term:** roll the centre — **Wittstock, Templin, Schönefeld, Sperenberg** (the Berlin cluster
  rear) — and **retake Hamburg** (17) on the northern shoulder.
- **End state:** **liberate Copenhagen / Kastrup** (41), break the Baltic Fleet's sea denial, and
  reopen the Straits.

**What makes the front advance:** winning the **air-superiority** fight over a sector, **killing red
ground forces** (BAI/CAS on the convoys and the FLOT), and **starving red's economy** (the factories
at Sperenberg/Schönefeld feed red convoys down toward the front; the depots arm them). Knock those
down and red can't replace losses, so each turn his line gets thinner.

**The blue economy advantage is deliberate** — you out-produce and out-buy him. Spend it on the
fights that move the line, not on vanity strikes deep in the IADS.

---

## 3 · Friendly order of battle

*Exact, from `red_tide.yaml`. "P" = player-flyable airframe in this campaign; "AI" = support/filler
the auto-planner flies. Sizes are starting squadron strength.*

### Ramstein (165) — main fighter/strike base, SW

| Squadron | Airframe | Role | Size | |
|---|---|---|---|---|
| 81st Tactical Fighter Squadron | **A-10C (Suite 3)** | CAS | 8 | **P** |
| Ala 14 | Mirage-F1EE | Escort | 6 | AI |

### Spangdahlem (162) — fighters + Fulda-Gap helos

| Squadron | Airframe | Role | Size | |
|---|---|---|---|---|
| VMF-29 | **F-14B Tomcat** | Escort | 8 | **P** |
| GAF JG 74 *"Mölders"* | **F-4E-45MC** (Luftwaffe) | TARCAP | 8 | AI |
| 493rd Fighter Squadron | F-15C Eagle | TARCAP | 6 | AI |
| 414th Aviation Detachment | UH-1H Iroquois | Air Assault | 4 | **P** |
| HMLA-167 | AH-1W SuperCobra | Escort | 4 | **P** |

### Hahn (155) — the strike & SEAD powerhouse

| Squadron | Airframe | Role | Size | |
|---|---|---|---|---|
| 414th Voodoo Squadron | **F-16CM (Block 50)** | DEAD | 12 | **P** |
| 414th JFG Hornets | **F/A-18C (Lot 20)** | SEAD | 12 | **P** |
| 414th Tactical Fighter Squadron | **F-15E Strike Eagle (Suite 4+)** | BAI | 12 | **P** |
| 20th Bomb Squadron | B-52H Stratofortress | Strike | 4 | AI |

### Frankfurt (163) — support, lift & enablers

| Squadron | Airframe | Role | Size | |
|---|---|---|---|---|
| 910th Airlift Wing | **C-130J-30** | Transport / **King / EW-ISR** | 2 | **P** |
| 5th Bn 159th Aviation | **CH-47F Block I** | Air Assault / **Jolly Green** | 4 | **P** |
| 12th Combat Aviation Brigade | **AH-64D Apache** | Escort | 4 | **P** |
| 1-17 Cavalry | **OH-58D(R) Kiowa** | Escort | 4 | **P** |
| 126th Air Refueling Squadron | KC-135 | Refueling (boom) | 2 | AI |
| 340th Expeditionary ARS | KC-135 **MPRS** | Refueling (**drogue**) | 2 | AI |
| NATO E-3A Component | E-3A | AEW&C | 2 | AI |

### Fulda (166) — forward FARP in the Gap *(flipped neutral→BLUE)*

| Squadron | Airframe | Role | Size | |
|---|---|---|---|---|
| 1-1 Attack Reconnaissance Bn | **AH-64D Apache** | CAS | 4 | **P** |
| 1-6 Cavalry | **OH-58D(R) Kiowa** | Armed Recon | 4 | **P** |
| 159th Aviation Det (Fwd) | **UH-1H Iroquois** | Air Assault | 4 | **P** |

**Reading the roster for tasking:**

- **Air superiority / escort:** F-14B (VMF-29), F-15C (493rd), GAF JG 74 Phantoms. The Tomcat is
  your long-stick escort; the Eagle is the AI sweep.
- **SEAD/DEAD (pry the IADS open):** F-16CM Voodoo (DEAD — kills SAMs), F/A-18C Hornet (SEAD —
  suppresses). **Hahn is your SEAD airfield.**
- **Strike / interdiction (move the line):** F-15E (BAI), B-52H (Strike).
- **CAS / front:** A-10C (Ramstein), AH-64D (Fulda + Frankfurt), OH-58D, AH-1W. Fulda is your
  forward rotary base — short legs to the Haina front.
- **Enablers & special:** C-130J (the **King** on-scene commander + EW/ISR jammer), E-3A AWACS,
  KC-135 boom + KC-135 MPRS drogue (drogue feeds the Hornets/Tomcats),
  CH-47F + UH-1H lift.

> ⚠️ **Tanker note:** the **boom** KC-135 feeds the F-16/F-15/A-10/B-52 (and the Phantoms); the
> **drogue** KC-135 MPRS feeds probe jets (F/A-18C, F-14B). Build packages so each striker has a
> compatible tanker on the route, or plan a hot pit.

---

## 4 · The enemy in one screen

Full enemy ORBAT, lore, and courses of action are in
**[red-tide-intel-assessment.md](red-tide-intel-assessment.md)**. The working summary:

**Priority kills (worth a squadron each):**

| Target | Where | Why |
|---|---|---|
| **924th GMRAP "Baltic Backfires"** — Tu-22M3 (AS-4 anti-ship) | Copenhagen / Kastrup (41) | Reaches the reinforcement convoys. The single highest-value set on the board. |
| **A-50 "Mainstay"** (144th) | Schönefeld (26) | His GCI eye. Kill it and the fighters go dumb. |
| **Il-78M "Midas"** (203rd) | Schönefeld (26) | His tanker. Kill it and the Flankers/Backfires lose reach. |

**Fighters — respect at the merge:**

- **MiG-29A Fulcrum** (Hamburg, Copenhagen, Peenemünde) — R-73 + helmet sight. **No turn fight** —
  kill BVR or extend.
- **Su-27 Flanker** (831st, Sperenberg) — long-range barrier CAP; respect the R-27ER.
- **MiG-23MLD / MiG-21bis** (Haina / Templin) — GCI-dependent, dangerous only in vectored mass.
- His **Su-24M Fencer** doubles as his **SEAD shooter** — it hunts the same SAM-killers you push
  forward.

**SAMs — it's a range fight, not an altitude one (you can't out-climb these):**

| System | Type | Play |
|---|---|---|
| **S-300PS (SA-10)** | Fixed, long-range (~45 nm) | Established & on. **Route the ring or dedicated SEAD.** |
| **S-200 (SA-5)** | Fixed, very long range | Reaches AWACS/tankers. Keep enablers back. Site now co-hosts a **P-14 "Tall King"** EW radar — a fat ELINT/strike signature. |
| **SA-11 Buk** | Mobile shoot-&-scoot (~22 nm) | Rides with the spearhead. Catch in transit; fly *today's* recon. |
| **SA-6 Gainful** | Mobile shoot-&-scoot (~13 nm) | Don't trust yesterday's picture. |
| **SA-2 / SA-3 + KS-19** | Fixed belt | In depth around fixed assets. |
| **SA-8/9/13 + ZSU guns** | Mobile low (~9 nm) | Don't loiter low near the FLOT. |

**The IADS is set advanced/networked** (`advanced_iads: true`), and each red SAM base has a
**command center + comms + power** cell placed in the `.miz` (some on real destroyable map
buildings). 🟡 **Caveat:** that laydown was designed against the old **Skynet** range-mode engine —
which has since been **replaced by MANTIS** as the fork's sole IADS engine — and the "kill the C2
and the wired SAMs go dark" effect is **not yet confirmed in-game** on the current build. Treat
killing C2/power as a *probable* way to degrade a base's net, not a guaranteed one, until it's been
flown. What *is* solid: the faction fields **dedicated early-warning radars — the 1L13 "Box Spring"
and the P-14 "Tall King" (both vanilla DCS, no mods)** plus the **A-50** — killing the EWR/AWACS
picture to make the net reactive is the dependable lever.

**Naval:** Tarantul/Grisha SAGs in the W. Baltic and off Copenhagen — **no organic air** beyond the
Copenhagen fighters. Kill the fighters, then the corvettes are anti-ship fodder and the Straits
reopen.

---

## 5 · Campaign CONOPS — the phase plan

The campaign target deck (intel assessment §IX) becomes a phased plan. Phases overlap; the FLOT and
red's reaction will reshuffle priorities, but this is the spine.

### Phase 0 — Win the air over the Fulda front *(turns 1–2)*
- **Objective:** local air superiority on the **Fulda → Haina** axis so strikers can work.
- **Fly:** BARCAP/TARCAP (F-14B, F-15C, JG 74) forward; DEAD/SEAD (Voodoo F-16, Hornet F/A-18) to
  start peeling the western SAMs; A-10C/AH-64D on the FLOT.
- **Win when:** you own the sky over the front and Haina's CAP stops contesting it.

### Phase 1 — Pry the lid off *(turns 2–4)*
- **Objective:** punch a SEAD corridor through the western IADS belt; kill mobile Buk/SA-6 in
  transit; suppress or route the fixed S-300 rings.
- **Fly:** DEAD packages (F-16CM + Hornet), recon to find the movers, BAI on the
  convoys feeding the front. Hit red's **C2/power** at Haina to unplug its net.
- **Win when:** strikers can reach Haina and the western convoys without running a SAM gauntlet.

### Phase 2 — Take Haina & blind him *(turns 4–7)*
- **Objective:** capture **Haina**; kill the **A-50 Mainstay** and **Il-78 Midas** at Schönefeld.
- **Fly:** OCA/Runway + BAI to strangle Haina; a deliberate AWACS/tanker-hunt (escorted long-range
  intercept on the enablers); CAS to push the FLOT past Haina.
- **Win when:** Haina is blue, and red's GCI/refuelling picture is broken (fighters go reactive).

### Phase 3 — Roll the centre *(turns 7–12)*
- **Objective:** the Berlin cluster — **Wittstock, Templin, Schönefeld, Sperenberg**.
- **Fly:** sustained interdiction of the rear factories/depots (Sperenberg, Schönefeld) to choke
  red's production; strike the heavy iron (Tu-95/Tu-22M3) on the ground at Sperenberg; keep the
  SEAD corridor open as the FLOT advances.
- **Win when:** red's economy is broken and the centre is collapsing.

### Phase 4 — Retake Hamburg *(parallel with Phase 3)*
- **Objective:** **Hamburg** (17), the northern shoulder.
- **Fly:** OCA on Hamburg's MiG-29/Su-25; BAI/CAS on the A24 supply corridor feeding the salient;
  strangle the air bridge (An-26).
- **Win when:** Hamburg flips blue and the northern shoulder is secure.

### Phase 5 — Open the Straits, liberate Copenhagen *(end game)*
- **Objective:** **burn the 924th Backfires** at Copenhagen, kill the Copenhagen fighter umbrella,
  then the Baltic SAGs, then take **Kastrup** (41).
- **Fly:** the big set-piece — escorted anti-ship/OCA strike across the water with full SEAD and
  tanker support. This is the campaign's climax.
- **Win when:** Copenhagen is blue and the Baltic Fleet is neutralized.

> **Carry this rule through every phase:** *tempo is ours now.* Every turn red gets to re-site SAMs
> and dig in, the next phase costs more. Keep him reeling.

---

## 6 · Weekly op-night runbook

A repeatable Saturday flow. The **mission commander (MC)** owns the plan; everyone else fills it.

**Before op night (MC, in the Retribution tool):**
1. Sync the save, read the **SITREP** on last turn's debrief / kneeboard cover page (losses,
   captures, rescues) and the current FLOT.
2. Pick **this turn's objective** off the phase plan (§5). One main effort, maybe one supporting.
3. Lay the **packages** (§8): main-effort strike/OCA/DEAD + escort + SEAD + tanker + AWACS, plus a
   CAS/front package and a Combat SAR alert package if helos are available.
4. Set **player slots** — assign the human flights to the packages that move the line; let the AI
   fill BARCAP/filler.
5. Generate the mission. Confirm tanker types match the receivers, AWACS/tanker orbits are on the
   front anchor, and kneeboards generated.

**At the brief (MC, ~10 min):** run the §7 template. Use the
[spoken brief](red-tide-intel-assessment.md#part-3--five-minute-spoken-brief-read-aloud-script) for
colour and the [visual briefing](red-tide-visual-briefing.md) on screen.

**Flight leads:** brief your own flight's game plan, comms, and contracts off the package brief.

**After the flight (MC):** run the §Appendix B debrief, fly the turn forward in the tool, capture
the SITREP for next week.

**Role slate (assign each op night):**

| Role | Typical airframe | Job |
|---|---|---|
| Mission Commander | any | Owns the plan & timeline |
| Strike/OCA lead | F-15E | Puts bombs on the target |
| DEAD lead | F-16CM Voodoo | Kills the SAMs in the way |
| SEAD escort | F/A-18C Hornet | Suppresses pop-up threats for the package |
| CAP/Escort lead | F-14B / F-15C | Owns the air picture, protects the package |
| CAS/FAC | A-10C / AH-64D | Works the FLOT with the ground commander |
| King (on-scene cdr) | C-130J | EW/ISR + Combat SAR command (talking player) |
| Sandy lead | A-10C / AH-64D | Combat SAR rescue escort |

---

## 7 · The mission brief template

*Copy this for each mission. Fill the brackets. This is the standard package brief — flight leads
brief their slice off it. A stripped one-pager is in [Appendix A](#appendix-a--blank-one-page-brief-sheet).*

```
========================  RED TIDE — MISSION BRIEF  ========================
OP / TURN / DATE: Red Tide · Turn [N] · 13 JUL 1988 (+[turns])
MISSION #: [____]      OP NIGHT: [date]      MC: [callsign]

1. SITUATION
   Last turn (SITREP): [losses / base captures / rescues from the kneeboard cover]
   FLOT now: [where the front is]
   Enemy: [what red did / is expected to do this sector — see intel §VIII COAs]
   Friendly: [adjacent packages, ground push, who else is airborne]
   Weather / light: [ceiling / vis / wind / day-night]

2. MISSION (who-what-where-when-why)
   "[Package callsign] will [task] [target] vic [location] at [TOT]
    in order to [phase objective — e.g. open the SEAD corridor to Haina]."

3. EXECUTION
   a. Commander's intent / main effort: [the one thing that must happen]
   b. Scheme of maneuver (package flow):
        - Push: [time]   Marshal/IP: [point]   TOT: [time]
        - [Flight] — [role] — [push order, ingress, what they do, egress]
        - [Flight] — [role] — ...
   c. Game plan vs. threats:
        - Air: [CAP contract — who owns BVR, commit/abort criteria, bullseye]
        - SAM: [DEAD/SEAD plan — corridor, route the fixed rings, kill the movers]
        - Floor/ceiling: [hard deck, no-lower-than near the FLOT]
   d. Weapons / loadout per flight: [§12]
   e. Success criteria / abort criteria: [what "done" looks like; when to bug out]

4. COORDINATION & COMMS (§9 card)
   AWACS: [callsign / freq]      Tanker: [callsign / freq / type / track]
   Package freq: [____]   Inter-flight: [____]   Guard: 243.0
   Code words — PUSH: [____]  SUCCESS: [____]  ABORT: [____]  THREAT: [____]
   Bullseye: [name / where]

5. ADMIN & SAR (§11)
   Bingo / Joker: [____]   Divert: [field]
   Combat SAR: King [callsign/freq], Jolly [callsign], Sandy [flight]
   If you eject: [SAR contract — squawk, get to high ground, comms]
   ROE / IFF: [____]

6. CONTINGENCIES ("what if")
   - Tanker no-show: [plan B]
   - SAM corridor closed: [reroute / abort target]
   - Package CAP committed away: [strikers' fallback]
   - Blue air down: [Combat SAR trigger, who covers]
===========================================================================
```

---

## 8 · Package recipes

Fast templates for building a package in the tool. Scale flight counts to what's available and to
the threat. "+tkr/+AWACS" assumed on every offensive package.

| Package | Core | Escort | SEAD/DEAD | Notes |
|---|---|---|---|---|
| **DEAD (kill the SAM)** | 2× F-16CM Voodoo (HARM/Mav) | 2× F-14B or F-15C | self-escort + 2× F/A-18C SEAD | The lid-opener. Lead with this into a new sector. |
| **Deliberate strike / OCA** | 2–4× F-15E (PGM/dumb) | 2× F-14B TARCAP | 2× F/A-18C SEAD escort | Strike the fixed target after the corridor's open. |
| **OCA/Runway (airfield)** | 2–4× F-15E or B-52H | 2× F-15C | 2× Hornet SEAD | Strangle Haina/Hamburg fields. |
| **BAI / interdiction** | 2–4× F-15E | TARCAP as needed | as needed | Hit convoys/echelons feeding the front — moves the line. |
| **BARCAP / TARCAP** | 2–4× F-14B / F-15C / JG 74 | — | — | Own the air over the sector before strikers push. |
| **CAS / front** | A-10C + AH-64D | OH-58D recon/FAC | — | Works the FLOT with the ground commander. Fulda helos are closest. |
| **Enabler hunt (A-50/Il-78)** | 2× F-14B (long stick) | +2 escort | — | Deliberate, escorted intercept on Schönefeld's high-value enablers. |
| **Anti-ship (Baltic SAGs)** | F/A-18C (Harpoon) | F-14B escort | Hornet SEAD | End-game; kill Copenhagen fighters first. |
| **Combat SAR (§11)** | 1× **King** (C-130J) + 1× **Jolly** (CH-47F) | 2–4× **Sandy** (A-10C/AH-64D) | — | Stand it up when a pilot is down; can be a standing alert. |

> Put the **C-130J King** up on any deep/contested push as the EW/ISR + on-scene commander — it
> jams, builds the ELINT picture, and is already overhead if someone goes down.

---

## 9 · Comms & code-word card

*Fill the blanks per mission; the structure stays constant. Brevity below is the squadron-standard
subset — keep it short on the radio.*

```
NETS
  Package (primary) ....... [____]      Guard ................... 243.0 / 121.5
  Inter-flight ............ [____]      SRS (squadron) ......... [____]
  AWACS ("Magic"/[name]) .. [____]      Tanker ([name]) ........ [____]
  King (Combat SAR) ....... [____]      JTAC/FAC ............... [____]

CODE WORDS  (set fresh each mission — these print on the kneeboard cover/game plan)
  PUSH ......... [____]   (commit / start the run-in)
  SUCCESS ...... [____]   (target serviced / objective met)
  ABORT ........ [____]   (knock it off, egress)
  THREAT/TOP .. [____]    (high threat up — defensive)

BULLSEYE: [name] @ [where]    — all BRA/bullseye calls reference this

KEY BREVITY
  PICTURE / DECLARE ... ask AWACS for the air picture / ID a contact
  BOGEY / BANDIT ...... unknown / confirmed hostile
  FOX 1/2/3 ........... SARH / IR / active missile away
  SPIKE / NAILS ....... RWR lock / search emitter (give clock + type)
  MUD [type] .......... surface (SAM) radar on you (give type + direction)
  MAGNUM .............. HARM away (everyone deconflict)
  DEFENDING .......... in a SAM/AAM defensive (drop everything, support)
  WINCHESTER / BINGO . out of weapons / fuel to RTB
  POPEYE ............. in the weather/clouds
```

> Keep **Combat SAR on its own contract**: the **King (C-130J)** is a *talking player* over SRS who
> runs the on-scene picture. Scripted aids (TACAN beacon, F10 LARS survivor locator) complement his
> voice — they don't replace it.

---

## 10 · Threat-defeat quick reference

*Carry this on the kneeboard. "Defeat" = the practical play in this campaign.*

### Fighters

| Threat | Defeat |
|---|---|
| **MiG-29A** | No turn fight (R-73 + HMS out-stick you close in). Kill BVR with AIM-7/120/54, or extend and re-attack. Use AWACS picture; don't merge alone. |
| **Su-27** | Long-range R-27ER — respect first-shot range. Crank/notch after your shot; don't drag straight. Numbers + AWACS. |
| **MiG-23MLD / MiG-21bis** | GCI-dependent — break the picture (kill A-50, jam) and they go dumb. Dangerous only when vectored in mass. |
| **Su-24M (as SEAD)** | It hunts *your* SAM-killers. Escort the SEAD package; watch your six on the egress. |

### SAMs — route the fixed, catch the movers

| Threat | Defeat |
|---|---|
| **S-300 (SA-10)** | Fixed, ~45 nm, all-altitude inside the ring. **Don't out-climb it.** Route around, terrain-mask, or dedicated DEAD (HARM + standoff). Kill its **C2/power** to unplug it. |
| **S-200 (SA-5)** | Fixed, very long range — keep AWACS/tankers/high-flyers outside the ring. |
| **SA-11 Buk** | Mobile ~22 nm, shoots & scoots with the spearhead. Fly **today's** recon; catch it in transit; pop-up + HARM. |
| **SA-6** | Mobile ~13 nm. Same play — don't trust yesterday's picture. |
| **SA-2/SA-3 + KS-19** | Fixed belt in depth. Notch, chaff, terrain; HARM if it's in the way. |
| **SA-8/9/13 + ZSU** | Mobile low block ~9 nm. **Don't loiter low** near the FLOT; stay above the gun floor or treetop-fast. |

**The IADS levers:** the dependable one is **killing the picture** — drop the **ground EWRs (1L13
"Box Spring" + P-14 "Tall King")** and the **A-50** and the net goes reactive instead of cued (the
faction fields all of them; confirmed). 🟡 The
**C2/power cells** at each base are placed to let you *unplug* the SAMs wired to them, but that
networked behaviour was built against the retired Skynet engine and isn't yet confirmed under the
current MANTIS engine — try it, but don't bet a package on it until it's flown.

---

## 11 · Combat SAR — when a pilot goes down

Red Tide has the airframes to fly the 414th's **Combat SAR** package (the C-130J, CH-47F, A-10C and
AH-64D are all in the roster — confirmed), and the design has red **race to capture** downed
aviators. 🟡 **Status caveat:** Combat SAR is **built but still in in-game testing** — several of its
pieces are UNTESTED on the checklist and the AI auto-rescue actually *failed* a flight on 2026-06-28
(a fix landed; a re-fly is owed). So fly it, but brief it as a capability we're shaking out, not a
guaranteed safety net. The mechanics below are the *intended* design.

**The package:** **1 King + 1 Jolly Green + 2–4 Sandy.**

- **King** — **C-130J-30** (910th AW). On-scene commander: flies the HC-130 "King" overhead orbit, a
  **TACAN-only** air-tracking beacon + **F10 LARS** survivor locator, and runs the rescue over SRS
  voice. Also the EW/ISR jammer.
- **Jolly Green** — **CH-47F** (5-159) or UH-1H. The rescue helo that picks the survivor up.
- **Sandy** — **A-10C / AH-64D** (2–4). Protect the downed pilot, suppress the threats around them,
  and walk the helo in (the SCAR "Sandy"/RESCAP role).

**The capture race:** on ejection, a **CJTF_RED snatch party** may race to seize the survivor.
- **Kill the snatch party** and a surviving rescue → the aviator is **spared at debrief** (the
  airframe is still lost, but you keep the pilot).
- **Lose the race** → the pilot is **CAPTURED**, held as a **POW at an enemy airfield**, and offered
  back as a **CSAR objective**. A surviving CSAR raid — or **recapturing the field** — frees them. A
  POW abandoned past the **4-turn clock is killed.**

**AI safety net:** with `auto_combat_sar` on, an AI King + Jolly + 1 Sandy is *designed* to stand
alert and go after downed pilots you don't reach. 🟡 This is the exact path that failed its
2026-06-28 flight (fix landed, re-fly owed) — don't rely on it yet; fly the human SAR package.

**Pilot SAR contract (put it in §5 of the brief):**
- Eject → get clear, get to high/defensible ground, conserve.
- Comms on the SAR/guard freq; King runs the show — follow his calls.
- Squawk / authenticate per the day's plan.

> Stand up a **Combat SAR alert** package any op night you're pushing into contested airspace — and
> put the **King** overhead anyway for the EW/ISR picture, so it's already on station if it's needed.

---

## 12 · Loadout & role pairing notes

General pairing guidance — tune to the threat and what the tool offers per turn.

| Role | Airframe(s) | Typical load | Notes |
|---|---|---|---|
| **DEAD** | F-16CM Voodoo | AGM-88 HARM ×2 + AGM-65 Maverick + AIM-120/9 | Kills the SAM. Lead the corridor. |
| **SEAD escort** | F/A-18C Hornet | HARM ×2 + AIM-120/7/9 | Suppress pop-ups for the package; reactive HARM. |
| **Strike (PGM)** | F-15E, F/A-18C | GBU/Maverick + A2A self-defense | Precision on fixed targets after SEAD. |
| **OCA/Runway** | F-15E, B-52H | runway-cratering / cluster + dumb | Strangle the fields. |
| **BAI / interdiction** | F-15E | CBU/Mk-82/Maverick | Convoys & echelons — moves the line. |
| **Air superiority** | F-14B, F-15C | AIM-54/7/120 + AIM-9 | Long stick. F-14B = your reach. |
| **CAS** | A-10C, AH-64D | Mav/Hellfire + gun + rockets | Work the FLOT with the ground cdr. |
| **Sandy (CSAR escort)** | A-10C, AH-64D | gun + rockets + Mav/Hellfire | Suppress around the survivor; walk the helo in. |
| **King / EW-ISR** | C-130J-30 | EW pods (per the C-130 systems) | Jam, ELINT, on-scene SAR command. |

**Receiver/tanker pairing (don't strand a striker):**
- **Boom (KC-135):** F-16, F-15C/E, A-10, B-52H (and the JG 74 Phantoms).
- **Drogue (KC-135 MPRS):** F/A-18C, F-14B.

---

## Appendix A — blank one-page brief sheet

*Print one per flight lead.*

```
RED TIDE  ·  TURN [__]  ·  MSN #[____]            MC: [______]

CALLSIGN: [______]  AIRFRAME: [______]  #SHIP: [__]  ROLE: [__________]

MISSION: ________________________________________________________________
TARGET / AREA: __________________________  TOT: [______]  PUSH: [______]

ROUTE:  IP [________]  →  TGT [________]  →  EGRESS [________]
HARD DECK: [______]   BINGO: [______]   JOKER: [______]   DIVERT: [______]

THREATS (air): _________________________________________________________
THREATS (SAM): _________________________________________________________
GAME PLAN: _____________________________________________________________

COMMS:  PKG [______]  AWACS [______]  TKR [______/type]  GUARD 243.0
CODE:   PUSH [____]  SUCCESS [____]  ABORT [____]  THREAT [____]
BULLSEYE: [__________]

LOADOUT: _______________________________________________________________
SAR: King [______]  Jolly [______]  Sandy [______]   If down: ___________
NOTES: _________________________________________________________________
```

---

## Appendix B — mission log / debrief sheet

*One per mission; feeds next turn's SITREP.*

```
RED TIDE DEBRIEF  ·  TURN [__]  ·  MSN #[____]  ·  [date]

OBJECTIVE THIS TURN: ____________________________________________________
RESULT:  [ ] MET   [ ] PARTIAL   [ ] NOT MET

BLUE LOSSES:  a/c ____  pilots ____ (KIA __ / RESCUED __ / POW __)
RED CLAIMED:  air ____  SAM ____  ground ____  ships ____
BASES:  captured ______________   lost ______________
FLOT MOVEMENT:  ________________________________________________________

WHAT WORKED: ___________________________________________________________
WHAT DIDN'T: ___________________________________________________________
NEXT TURN MAIN EFFORT (per §5 phase plan): _____________________________

OPEN SAR / POW (4-turn clock): _________________________________________
```

---

*Companion docs: in-fiction lore & spoken brief →
[red-tide-intel-assessment.md](red-tide-intel-assessment.md); picture brief & maps →
[red-tide-visual-briefing.md](red-tide-visual-briefing.md). Build/edit notes for the campaign
itself → [../dev/design/414th-red-tide-campaign-notes.md](../dev/design/414th-red-tide-campaign-notes.md).
All regiments, callsigns, personalities, and the "ZAPAD" operation name are fiction in the* Red Storm
Rising *tradition and freely editable.*
