# 414th — DCS Campaign Documentation: Ideas Harvest

A study of the **professional, commercially-shipped DCS campaigns** installed locally
(`E:\DCS World\Mods\campaigns\`), mined for design patterns the 414th's Retribution fork
can steal. This is **inspiration / pattern notes** — not content to copy. It feeds the
kneeboard work (features §4 / §22, checklist **H3/H4**), the intel/recon-fog layer (§3),
the Mission Impact debrief (§4), and the IADS/EW runtime (§2 + MANTIS).

> Source corpus: **23 installed campaigns, 511 PDFs, ~5,498 pages.** This pass read deeply
> across **11 priority campaigns** (the ones the squadron flies: F-4E Red Flag 81-2,
> F-16C Arctic Thunder / FIWOS / LOWOS / Gamblers, FA-18C Cerberus North 1&2 /
> Raven One 1&2 / Rampagers, F-4 MIG Killers).

---

## 0. How to read the corpus (tooling)

The campaign `Doc/` PDFs split into two kinds:

| Kind | Examples | Extract with |
|---|---|---|
| **Text/vector** | guides, briefings, SPINS text, lineups | `pdftotext -layout` (mingw64) **or** PyMuPDF `page.get_text()` |
| **Image/scanned** | kneeboards, intel assessments, target photos, checklists | **render to PNG** then read visually |

- `pdftotext` is available (mingw64). **poppler `pdftoppm` is NOT installed**, so the built-in
  Read-a-PDF path fails on rendering.
- Working renderer: **PyMuPDF**, scratch-installed *without touching the project venv*:
  `.venv\Scripts\python.exe -m pip install --target <scratch>\pylibs pymupdf`, then
  `PYTHONPATH=<scratch>\pylibs python render.py <pdf> <p0> <p1> <prefix> <dpi> <outdir>`.
  (135 dpi reads fine for intel prose; 150 dpi for kneeboards.)
- Per-campaign text/image split + a full text dump of every text PDF was produced during this
  pass (scratchpad). Re-runnable any time the install updates.

---

## 1. Kneeboard design → feeds **H3/H4**

> **Local reference set** (not in the repo — extracted from the commercial `.miz`, kept local):
> `C:\Users\brady\Desktop\414th-Joint-Fighter-Group\kneeboard-references\<campaign>\` —
> **1,215 unique** full-res kneeboard cards across the 11 campaigns, deduped, each campaign with a
> browsable `_contact_sheet.png`. Use these as the styling reference when building generator cards.

Two visual idioms over one shared structure:

- **Handwritten-on-paper** (Ground Pounder Sims — FIWOS/LOWOS): warm, "filled in by the
  aviator," graph-paper/manila stock. Immersive.
- **Printed grid** (Rampagers, F-4E Red Flag 81-2): clean boxed tables, **color-coded radio
  presets** (BLUE 1 / PURPLE 1 / GREY 9 matching DCS preset colors).

The 414th generator currently leans printed-clean (§22 light-heading restyle). Both idioms are
valid; the *card taxonomy* is what matters. The recurring **"deck"** (one mission = these cards):

1. **Flight / Mission Data + Loadout** — mission #, ATO id, callsign; engine-start/taxi/
   takeoff/TOT times; weather at 2–3 altitude bands; A/C # / pilot / TACAN / ramp-spot table;
   a **per-station loadout row** (stns 1–9: 120C, 9X, AGM-88, TGP, ALQ-184, HTS, fuel…);
   chaff/flare, gun ammo type, fuel, gross weight.
2. **Comms** — agency / callsign / freq for every player-relevant entity (AWACS, Rivet Joint,
   ABCCC, tankers w/ TACAN, JTAC, ATC), **plus the COMM1-UHF / COMM2-VHF 20-channel preset
   ladder**, color-coded.
3. **Flight Plan + Fuel ladder** — waypoint list with leg descriptions ("PATROL 25K FT M0.7"),
   **fuel-remaining per waypoint**, Bingo, Bullseye name.
4. **Threats & Codes** — per-SAM **MEZ range + max-engagement-altitude + HARM HAD class**
   (e.g. `SA-6: MEZ 15nm, max 40,000 ft, HAD Class 2`). A SEAD/Weasel reference card.
5. **Maps** — (a) route over terrain with WP circles + tanker track; (b) threat/situational map
   with FEBA + named control zones + named SAM threats; (c) **annotated target recon photos**
   (target ringed, SHORAD/AAA/command labeled, zoom inset).
6. **Brevity / code-word table** (F-4E) — push-channel names + success/fail/stop-jam code words
   (`OCA PUSH = Pineapple Juice`, `SUCCESS = Coconut Cream`, `STOP JAM = Angry Baboon`).
7. **SPINS extract** — base/airspace/ROE procedure pages, embedded so the rules ride in-cockpit.

**Why this matters:** Retribution already owns the data for cards 1–5. It knows the flight plan,
the loadout, the bullseye, the tanker + TACAN, and (critically) the **enemy SAM OOB** — so a
**Threats & Codes card** and an **auto-annotated threat map** are generatable with no new data,
only new kneeboard templates. Card 5c (target imagery) overlaps the existing **TARPS recon
imagery** (§3). This is the most actionable H3/H4 lift: add card *types*, not just restyle.

---

## 2. Intel assessment → an auto-generated **threat dossier** kneeboard/PDF

The Ground Pounder **"Intelligence Assessment"** (FIWOS 75 pp, LOWOS 76 pp, Cerberus North 2
59 pp) is the standout artifact. Structure:

- **"TOP SECRET" red banner** on every page; typewriter/monospace body for the classified feel.
- **Contents page** cataloguing the whole threat environment: political/faction background
  (each nation + non-state group), **EW radar types** (1L13 Box Spring, P-19 Flat Face, 55G6
  Tall Rack, ST-68U Tin Shield, 9S80M1 Dog Ear), **every SAM system** (SA-2/3/5/6/8/9/10/11/13/
  15/18), named airbases & facilities, **threat aircraft / AAM / helicopter tables**, Russian
  facilities.
- **Per-system pages**: a capability map (site locations, kill-Xs on dead ones) + descriptive
  prose + **a data table** (AAM table = name / NATO designation / seeker / max range / speed)
  + frequently **"how to defeat it"** advice.
- **Handwritten margin annotations** from a named senior officer ("*Dan, here is your copy of the
  intel brief… Study it well! — Lt. Col Doyle*", "*JSTF have killed numerous EW radars already*").
  This personalization is most of the immersion.

**Two production templates seen, same content model:**
- **Typewriter dossier** (FIWOS == LOWOS — *identical* doc: TOP SECRET banner, prose + maps +
  data tables + handwritten margin notes). Warm, hand-built feel.
- **Printed data-card** (Cerberus North 2 — the cleaner evolution): sectioned with header bars
  (`FACTIONS - OVERVIEW`, `THREAT ANALYSIS`), faction prose pages, an `AREAS OF CONTROL` legend
  map, and — critically — **one structured "threat card" per system**: a photo + a stat block
  (`GUIDANCE / ACQUISITION RANGE / ENGAGEMENT RANGE / MAX CEILING / WARHEAD / FUZING`) + a green
  diamond **HARM HAD-class badge** + a `NOTES` line (e.g. "SA-3 often paired with SA-2; deployed
  with P-19 'Flat Face'"). **This card is effectively a database record rendered to a layout** —
  the ideal auto-generation target.

**Steal:** Retribution *generates* the red OOB, so it can emit a themed, per-campaign
**threat dossier** — one **Cerberus-North-2-style threat card** per present SAM/EW/aircraft type
(stat block + HAD badge + defeat note), a faction-control map, and an editable flavor intro. It
dovetails with **recon fog (§3)** (only *known* systems appear; unknown ones redacted = a natural
in-fiction reason for fog) and the **overview reveal toggle** (un-redacts everything). v1 = one
generated "Intel Brief" kneeboard page (known threats + MEZ + HAD); v2 = the full carded dossier.

> ✅ **BUILT (v2).** A **Threat Intel Brief** kneeboard page auto-generates the enemy
> air-defense dossier as **one card per system** (sites aggregated): a curated stat block
> (guidance, engagement ceiling, and a **"how to defeat"** tactics note) over the live campaign
> numbers (MEZ, detection, HARM ALIC, live/dead counts, bullseye cues). Recon-fog aware —
> undiscovered sites collapse into per-band "Unidentified MERAD" cards until a TARPS overflight
> reveals them — and cards pack/paginate down the page. The curated layer lives in
> `game/data/threat_reference.py`; the page + `build_threat_intel_cards` in
> `game/missiongenerator/kneeboard.py`. Gated by `generate_threat_intel_kneeboard` (default off);
> see 414th features §4. **Photos deferred:** DCS ships only `.dds` model textures (not
> portraits), so a per-system photo would mean reading + converting the user's DCS install at
> gen-time — fragile, path-dependent, low value on a 960px page.

---

## 3. Runtime systems worth stealing

> ⚠️ **Multiplayer caveat (do NOT pursue the F10-menu mechanics).** These campaigns are
> **single-player**; their signature device — per-player **F10-radio-menu** flows (ATC scoring,
> `Declare Emergency`, `Immortal On`, abort, buy-support) — depends on single-client per-player
> trigger/score state that does **not** translate to the 414th's **multiplayer** missions. Treat
> every F10-menu idea below (and the whole §3b F10 taxonomy) as **out of scope** unless a
> genuinely MP-safe reframing exists. The portable, MP-safe steals are the **kneeboard/intel
> artifacts** (§1, §2) and the **failsafe-trigger discipline**.

- **"Weasel System"** (FIWOS/LOWOS) — a custom AI air-defense layer that *wakes SAMs as you
  approach*, *controls SAM radar emissions*, and *approximates EW jamming effects*. This is the
  same problem space the 414th already solved with the **MANTIS IADS engine** + **C-130J EW**
  (§2). Validation that the approach is right; also a reminder that "scripted story × dynamic
  AI air-defense = emergent replayability" is the selling point to lean on in player docs.
- **"Gauntlet Ops"** (FIWOS; also Cerberus North, Dominant Fury) — at mission start the player
  can override the scripted mission and instead get a **random target (with photo + coords)** and
  **a budget of points to spend via the F10 menu on support** (KC-135, Wild-Weasel HARM shooter,
  EW Growler, CAP), free loadout choice, then "go kill it and RTB." A roguelite single-mission
  mode. **Maps cleanly onto Retribution's purchase economy + drop-spawn (§20)** — a "quick strike"
  / practice generator picking a random known TGO and letting the player buy a support package.
- **Mission scoring model** (LOWOS scoring guide) — `50 pts on start + ~10–15 ATC + ~35 performance
  = 100`, with: **weighted per-objective points**, **negative ROE penalties** (airspace
  violation, no-fire-zone hit, unauthorized HARM), **airmanship bonuses** (correct IP/attack
  heading, "stayed low," ATC procedure), **protect-the-friendly objectives** ("Canine 4-4 saved",
  "Archangel 2 survived"), and an **immortal-mode score cap (≤60)**. Directly enriches the
  **Mission Impact debrief (§4)** beyond pure BDA — reward ROE/escort/airmanship, not just kills.
- **Custom home-base ATC tied to score** — procedural taxi/departure/approach/landing comms via
  F10, frequency-gated. Heavy to build; noted for completeness.
- **Failsafe backup triggers on every AI task** — "if an AI unit goes AWOL, a backup trigger
  fires within ~5 min and progresses the mission." A **robustness pattern** the 414th Lua
  features (SCAR, Combat SAR, TIC) should adopt: never let a stalled AI soft-lock a scripted beat.
- **Abort-on-damage + declare-emergency** via F10 (graceful exit / immediate landing, at a
  documented score cost). Good UX for player-flown SCAR/CSAR.
- **Two-part mission split at the tanker** — part 1 ends at the AAR track, part 2 resumes
  post-refuel; gives a checkpoint *and* spares the AI from having to tank. Clever structural trick.
- **Immortal mode** (accessibility, score-capped) — chosen pre-taxi, locked after.
- **Brevity / code-word comms** (F-4E) — named push channels + success/abort/stop-jam code words
  on the kneeboard; cheap immersion + radio discipline.

---

## 3b. The `.miz` teardown (what's readable, what's locked)

Every campaign also ships its mission `.miz` files (each a plain **zip** — *not* encrypted, so
openable). Across all 11 priority campaigns:

- **The trigger/scripting LOGIC is locked.** Every mission uses DCS's **`["ext_loader"]`**
  mechanism — `["trig"]`, `["trigrules"]`, `["triggers"]` are empty and the logic is compiled
  into a protected external **library** in the campaign folder (`["library"]` + a `["miz_id"]`
  hash). So the *implementation* of the Weasel System / ATC / scoring is **not** human-readable.
  (Confirmed: 0 inline `a_do_script`/triggers in any sampled mission.)
- **The content design IS fully readable** via `l10n/DEFAULT/dictionary` (33K–231K each;
  LOWOS M1 = **3,914 string entries**) plus the embedded **kneeboard JPGs** (14–69 per mission,
  higher-fidelity than the PDFs) and the **`.ogg` voice inventory** (the comms cast).
- Read it with Python `zipfile` → `dictionary`, regex `\["key"\] = "value"`; render JPGs/PNGs
  straight from the zip.

What the LOWOS M1 dictionary reveals (player-facing design, even with logic locked):

- **F10-menu-driven ATC**: menu items `Request taxi / Engine Start / Takeoff / Landing`,
  `Declare emergency`, `Immortal On`, "Press space to request clearance to attack" — with real
  enforcement strings (`TOWER: NO PERMISSION TO ENTER RUNWAY`, "Next time make sure you request
  clearance to takeoff!").
- **ROE escalation hard-fails**: "You engaged Russian aircraft, mission failed!", "approached
  Russian bases… mission failed", "provoked the Russians… mission failed" — geopolitical ROE as
  explicit fail states (distinct from the soft per-objective point penalties).
- **Emissions-discipline scoring**: `3 BUTTONS ON - HEAT PENALTY` / `HEAT PENALTY REMOVED` — a
  jammer/EW-usage penalty toggle.
- **Dynamic task + abort, delivered as a message**: "Suppress the SA-6 threatening Mastiff. This
  task can be aborted anytime by contacting Mastiff 3 using the F10 menu." This is precisely the
  **SCAR / C-130 "King" talk-on** pattern (§15) — on-scene tasking + F10 abort.
- A full **wingman + package radio-call script** (named agencies Akrotiri Ground/Tower/Approach/
  Departure, Incirlik/H4 Arrival, RAPCON; wingman "Bug"; SEAD package "Mastiff 3") — a model for
  the tone/structure of 414th scripted comms.

**Takeaway:** we can't lift their trigger code, but the dictionaries are a large, legal corpus of
**radio-call phrasing, F10-menu taxonomy, and scoring-feedback wording** to model the 414th's own
scripted comms and Mission-Impact messages on.

**Cross-campaign sweep (one mission each, all 11)** — the F10-menu taxonomy is remarkably
consistent and worth mirroring; developer styles differ:

- **Ground Pounder** (FIWOS/LOWOS/Cerberus North 1&2): the full set — `Request Taxi / Engine
  Start / Takeoff / Landing`, `Declare Emergency`, `Abort Mission`, `Immortal On`, "Press space
  to request clearance to attack." Cerberus North 2 even adds **`Disable Custom ATC`** (opt out of
  the ATC scoring layer) and **`Declare emergency and rig barricade`** (carrier barricade). Live
  wingman threat-callouts ("BUG: Pop up threat! AAA west of waypoint 5…").
- **Reflected** (Red Flag 81-2 / MIG Killers): training-range idiom — `Skip mission`,
  spacebar-progression ("PRESS SPACEBAR TO CONTACT NELLIS APPROACH… WHEN YOU REACH POINT RAMM"),
  RIO/instructor banter (`[JESTER] Well done, great flying, man!`), big `***MISSION COMPLETE***`
  cards.
- **Arctic Thunder**: `Press SPACEBAR to insert the DTC`, `…when you're fenced in`,
  `…to call WINCHESTER` — checklist/state-gated prompts.
- **Gamblers / SEAD**: JTAC-style **effects feedback** ("good effects on Aim Point One",
  "negative effects on Aim Point One", "Good job on that Abrams") — a model for BDA call wording.
- ROE escalation hard-fails recur ("You got too close to the Russian FOB. Mission failed").

## 4. Narrative / immersion craft (cheap, high-impact)

- **Personalized framing** — docs addressed to the player's character by a named CO; squadron
  **character bios** (Arctic Thunder devotes pages to personalities); **voice-acting credits**.
- **"Grounded but fictional" disclaimer** — every Ground Pounder/Sandman campaign opens with the
  same legal/immersion note. Worth mirroring in 414th campaign intros.
- **SPINS as living, kneeboard-embedded rules** — Special Instructions aren't flavor; score and
  safety depend on them, and they ride in every mission's kneeboard.

---

## 5. Mapping to the 414th backlog

| Idea | Existing 414th hook | Effort | Note |
|---|---|---|---|
| Threat dossier kneeboard (MEZ/HAD/defeat) | recon fog §3; SEAD §6/§7 | **Low/Med** | ✅ **BUILT** — Threat Intel Brief (§4) |
| Auto-annotated threat/target map card | TARPS imagery §3; map layers §19 | Med | Reuse recon imagery + known-TGO data |
| Fuel-ladder flight-plan card | kneeboard gen | **Low** | ✅ **BUILT** — planned remaining + margin (§4) |
| Mission code words (per-task push table) + brevity | kneeboard + planner UI | **Med** | ✅ **BUILT** — Red Flag-style, `enable_package_code_words` (§4) |
| Richer Mission Impact (ROE/airmanship/escort scoring) | Mission Impact debrief §4 | Med | Add weighted + penalty terms |
| "Gauntlet"/quick-strike buy-support mode | purchase economy; drop-spawn §20 | Med/High | Random known TGO + support package |
| Failsafe driver-loop hardening (pcall) | SCAR §15 / Combat SAR §21 / TIC §9 Lua | **Low** | ✅ **BUILT** — a tick error can't kill a watchdog / break the battle loop |
| Personalized CO framing + bios + disclaimer | campaign intro docs | **Low** | Copy-writing, not code |

**Shipped so far:** the Threat Intel Brief dossier, the mission code words + Comms & Brevity card,
and the **fuel-ladder card** — the three kneeboard ideas from this study are all in.
The **failsafe-trigger discipline** is applied too — but adapted: the 414th's runtime features are
emergent/continuous rather than the linear scripted beats of an SP campaign, so the genuine
soft-lock risk isn't a missing per-beat timer (SCAR already has its window deadline; Combat SAR is
MOOSE-driven) but a **driver loop dying on a runtime error** (DCS drops a scheduled function that
throws). So the SCAR watchdog (`scar_check`), the TIC ambient-fire `simulate()` wrapper + battle
init, and the Combat SAR LARS F10 query are each **`pcall`-contained** — a tick error logs and the
loop survives instead of soft-locking (§9 / §15 / §21).

**Still open (low effort, high payoff):** the richer Mission Impact scoring (ROE/airmanship/escort,
not just BDA).

> **Note (multiplayer):** the code words are a *human* SRS aid — nothing scripts off them, unlike
> the single-player campaigns the idea came from. The F10-menu mechanics those campaigns use stay
> out of scope (see §3 caveat).
