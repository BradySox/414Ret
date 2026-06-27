# 414th Red Tide Campaign Notes

Design and build notes for **Germany - Red Tide** (`resources/campaigns/red_tide.yaml`
+ `red_tide.miz`), the 414th's reworked GermanyCW scenario. Read this before editing the
campaign or re-touching its `.miz`; it records *what* was changed, *where* in the binary,
and the gotchas that bit us.

Red Tide is a **fork of `crossing_the_rubicon`**, not a rewrite of it. The original
campaign is preserved untouched (it kept only an unrelated `An-26B` variant-id fix). Red
Tide is a separate, selectable campaign that carries the heavier 414th laydown.

## Premise

13 July 1988, in the spirit of Tom Clancy's *Red Storm Rising* (nodded to in the in-app
description). A conventional Warsaw Pact invasion through the Fulda Gap **opened** the war —
Hamburg fell and Copenhagen was seized — but the campaign is framed from the moment the
Soviet offensive has **culminated**: overextended, exposed, and not yet dug in. The player
inside the **414th Joint Fighter Group** (a multinational NATO wing that happened to be
forward-based when it kicked off) now leads the **NATO counteroffensive** — clawing back the
skies and rolling the front east to retake Hamburg, liberate Copenhagen, and drive the Red
Army back. Setting stays 1988-07-13; player faction `Blufor Late Cold War (80s)`, enemy
`Russia 1980`. The red-heavy laydown (red still holds the north, centre, and east) is *why*
the offensive framing works — that captured ground is the objective set the 414th attacks.

> **Posture note.** The reframe is narrative; the **blue-offensive tuning below has now been
> APPLIED** (no playtest). One **base-ownership / front-line change has since been made**:
> the neutral **Fulda** airfield (id 166) was flipped BLUE as a forward FARP and the front
> re-routed through it (see *Fulda forward heli base* under Changes). Other map/base-ownership
> shifts remain out of scope.
>
> 1. **Economy skew — APPLIED.** `recommended_player_money: 800` / `recommended_enemy_money: 400`,
>    `recommended_player_income_multiplier: 1.3` / `recommended_enemy_income_multiplier: 0.7`. Blue
>    out-produces and out-buys the culminated Soviet salient.
> 2. **Squadron balance — APPLIED, then re-skewed toward the human (2026-06-23).** The original
>    blue offensive `size` bumps (A-6E 8→12, F-16CM 8→12, F/A-18C 8→12, F-15E 8→12, Tornado 8→10,
>    B-1B 4→6) were later **partially walked back** to put the *human* 414th sorties at the centre
>    of the offensive rather than drowning them in AI flights (see *Human-led offensive retune*
>    under Changes). The **player-flyable 414th airframes stay large** (F-16CM 12, F/A-18C 12,
>    F-15E 12, F-14B 8, A-10C 8, all F-4E 8); the **AI-only support/bomber** squadrons were
>    trimmed (A-6E 12→6, B-1B 6→4, Mirage-F1 8→6, AV-8B 8→6, F-15C 8→6, Tornado 10→8). Red
>    fighter trims unchanged: Peenemünde MIG-29 8→4, Hamburg MiG-29A 8→6, Sperenberg Su-27 8→6.
> 3. **Red posture / AI — no knob needed.** Red's QRA reserve (`opfor_default_qra_reserve`) and
>    planner unpredictability are already at the defaults that favor a blue offensive (reserve 0,
>    deterministic). *Raising* red's QRA would make red defend better (backfire); it can't go
>    lower than 0. The intended "red stays reactive" effect instead falls out of (1)+(2) — cutting
>    red's economy and fighter mass naturally shrinks red's offensive air. Left at defaults.
>
> 4. **Auto-planner restraint (human-led ATO) — APPLIED (2026-06-23).** A campaign `settings:`
>    block recommends two new-game defaults that make the **blue** auto-planner fill fewer
>    offensive ATO slots, so the human's flights are the spearhead:
>    `ownfor_autoplanner_aggressiveness: 10` (default 20 — blue AI ignores less of red's
>    threat radius, so it won't auto-throw strike/SEAD packages deep into the IADS belt) and
>    `oca_target_autoplanner_min_aircraft_count: 40` (default 20 — airfield attack becomes a
>    human-chosen objective, since red squadrons are 4–8 jets and now fall below the bar).
>    OPFOR aggressiveness is untouched. These are *recommended* defaults the wizard can override.
>
> **Out of scope (ruled out):** flipping bases (e.g. Haina) to blue, adding a blue northern base,
> or nudging the FLOT east. Map kept as-is. Tune the (1)/(2)/(4) numbers if the balance needs it
> — the easiest next dial is `recommended_player_income_multiplier` (1.3) if blue still
> out-flies the human.

## Force laydown

GermanyCW coordinate convention: **larger x = further north**, **larger (less negative)
y = further east**. The blue/red split is intentionally clean — every blue base sits in the
south-west (the real Rhineland NATO cluster), every red base to the north/centre/east.

### Blue (NATO) — south-west cluster
| Base | id | Squadrons |
|---|---|---|
| Ramstein | 165 | B-1B (OCA/Runway), **A-10C Suite 3 (CAS)**, Mirage-F1EE (Escort), F-4E-45MC (SEAD Sweep, 480th TFS Weasels — replaced the dropped VMA-231 AV-8B), **A-6E (OCA/Aircraft)** |
| Spangdahlem | 162 | F-15C (TARCAP), **F-14B (Escort)**, **GAF JG 74 (TARCAP)**, F-4E-45MC (BAI), UH-1H, AH-1W |
| Hahn | 155 | B-52H (Strike), F-16CM (DEAD), Tornado IDS (SEAD Escort), F-4E-45MC (OCA/Runway), **F/A-18C (SEAD)**, **F-15E (BAI)** |
| Frankfurt | 163 | KC-135, **KC-135MPRS (drogue tanker)**, C-130J, CH-47F, AH-64D, **E-3A (AEW&C)**, **OH-58D Kiowa (Escort)** |
| **Fulda** | **166** | **Forward FARP (flipped neutral→BLUE).** Forward heli base in the Fulda Gap: AH-64D (CAS, 1-1 ARB), OH-58D (Armed Recon, 1-6 Cav), UH-1H (Air Assault, 159th Avn Det Fwd) |

### Red (Soviet/WP) — north, centre, east
| Base | id | Notes |
|---|---|---|
| Hamburg | 17 | **Captured** (flipped BLUE→RED). Forward airhead: MiG-29A, Su-25, Su-24M, Mi-24P, Mi-8MTV2 |
| Kastrup / Copenhagen | 41 | **Soviet-seized far-north enclave.** Maritime-strike base: MiG-29A (BARCAP), Tu-22M3 (Anti-ship), Su-24M (SEAD), An-26B |
| Haina | 161 | Western Soviet spearhead (Mi-24P, Mi-8MTV2, Su-25, MiG-23MLD, MiG-27K) |
| Sperenberg | 101 | Tu-95MS, Tu-22M3, Su-27 |
| Schönefeld | 26 | A-50, IL-78M, An-26B |
| Templin | 15 | Su-24M, MiG-21bis |
| Wittstock | 1 | Su-17M4 |
| Peenemünde | 25 | MiG-29 (Baltic coast) |

The north is deliberately **all-red and uncontested** (no blue base north of Frankfurt) —
a chosen design point emphasising a desperate NATO defence, not an oversight. Adding a blue
northern base (Kiel id 42 / Nordholz id 47, both available on the expanded map) was
considered and declined.

## Changes vs. Crossing the Rubicon

### `.miz` edits (hand-edited Lua, brace-balance verified each time)
1. **Carrier removed.** Deleted the blue `Blue-CV` (Stennis) ship group from the blue
   country block. Its air wing came ashore in the yaml: F-14 → Spangdahlem, F/A-18C → Hahn,
   A-6E → Ramstein. The S-3B Viking, S-3B Tanker and E-2C were dropped; the E-3A was moved
   to Frankfurt so blue keeps AEW&C.
2. **Hamburg captured.** `warehouses` airport `[17]` coalition `BLUE` → `RED`.
3. **Copenhagen added.** Airport `[41]` (Kastrup) had **no warehouse entry** — this `.miz`
   predates the map's northern-airfield expansion (ids 33–52 are absent from `warehouses`).
   Added a `[41]` warehouse block (copied from a red template, re-keyed) with coalition
   `RED` so pydcs sees it as owned rather than neutral.
4. **Red naval groups** (over-water front). Each is a single `USS_Arleigh_Burke_IIa`
   *marker* in the **red** country `["ship"]` block; Retribution's `MizCampaignLoader.ships`
   turns each into a naval objective populated from the controlling faction's `naval_units`,
   and the objective's **coalition follows the nearest control point** — so markers must sit
   nearest a *red* base to spawn red.
   - `Blue LHA-1` — legacy marker, north-central (x≈-40680, y≈-406076). Retained.
   - `Red Navy North` — Baltic off red Peenemünde (x≈-23956, y≈-421081). Northern Guardian
     supplied the known-valid Baltic water coordinate.
   - `Red Navy Copenhagen` — open SW Baltic off Copenhagen (x≈80000, y≈-430000).
   New groups use unique `groupId`/`unitId` (274/624, 275/625) past the mission max.
5. **Fulda flipped BLUE (forward FARP).** `warehouses` airport `[166]` (Fulda) was neutral
   with `["dynamicSpawn"] = true`. The loader (`control_point_from_airport`) forces any
   `dynamic_spawn` airport to NEUTRAL **before** checking coalition, so **two** fields were
   changed inside the `[166]` block: `dynamicSpawn true → false` **and**
   `coalition "NEUTRAL" → "BLUE"`. Verified via pydcs: airport 166 now loads `is_blue()`.
   (The `.miz` was repackaged with `zipfile`, preserving every other member byte-for-byte —
   `zip` isn't available in the shell here.)

6. **Economy buildings + advanced-IADS laydown added** (2026-06-23). Red Tide originally had
   **no working factory** (the lone `Workshop A` "Kastrup Factory" was placed in the **CJTF Red**
   country block, but the loader's factory scan is **blue-only** — `MizCampaignLoader.factories`
   iterates `self.blue.static_group` — so it was never detected; after turn 0 *nobody* could
   recruit ground units). Reference campaigns confirmed the pattern: **Northern Guardian** = 2
   `Workshop A`, **both in CJTF Blue** (ownership resolves by nearest CP); **The Falcon Went Over
   The Mountain** = the gold-standard advanced IADS via `advanced_iads: true` + a by-name
   `iads_config`. Changes (text-edited the `mission` member + re-zip with `zipfile`, since
   **pydcs `Mission.save` is broken for this miz — it emits a duplicate `theatre` member**):
   - **3 factories, all in the CJTF Blue block** (required for detection; ownership = nearest CP):
     **Ramstein (165)** → blue, **Sperenberg (101)** + **Schönefeld (26)** → red rear (feed red
     convoys/airlifts down Schönefeld→Sperenberg→Haina→Fulda front). Blue had *zero* statics
     before, so a `["static"]` block was created inside CJTF Blue country `[1]` (after `["id"]=80`).
   - **3 ammo depots** (`.Ammunition depot`, red): Sperenberg, Schönefeld (+ existing Kastrup);
     +12 deployable ground units each over the 15 baseline.
   - **Advanced IADS (range mode):** `advanced_iads: true` in the yaml (**no** `iads_config` — red
     SAMs are procedurally spawned with random names, so Falcon-style by-name wiring is impossible;
     range mode auto-wires SAMs to comms <15nm / power <35nm / command center). Each red SAM base
     (Sperenberg, Schönefeld, Hamburg, Haina, Templin, Wittstock, Peenemünde, Kastrup) got a
     co-located **Command Center + Comms tower M + GeneratorF** cell. The dead "Kastrup Factory"
     was **repurposed in place** into "Kastrup Command Center" (same spot, no renumber needed).
     - **FOLLOW-UP (2026-06-24):** these placed C2 statics land on some airfield aprons and
       block aircraft spawns (seen at Haina). Plan to replace them with **real map buildings**
       (destroyable IADS scenery targets) and remove the statics is fully scoped in
       [`414th-red-tide-c2-real-buildings-HANDOFF.md`](414th-red-tide-c2-real-buildings-HANDOFF.md)
       — incl. per-field coords, the scanner-dump feasibility (only Haina + Templin are scanned;
       the other 3 fields need a re-scan), and the emitter/pipeline details.
   - **IDs:** new groups start at `groupId 300` / `unitId 700` (max existing was 281/631). Appended
     to the red `["static"]["group"]` table with fresh keys `[13]+` to dodge a **pre-existing**
     key-collision (the hand-added Kastrup `[1]/[2]` clobbered Invisible-FARP `[1]/[2]` — 10 of 12
     FARPs survive; left as-is, out of scope).
   - **Verified (pydcs load-only):** miz parses; 3 blue `Workshop A`; red = 3 ammo + 8 CC + 8 comms
     + 8 power; every structure's nearest CP is its intended base (1.7–5.4 km) at the right
     coalition; warehouses member byte-identical (Kastrup red / Fulda blue intact); 3 naval groups
     intact. **In-game pass still needed:** confirm red builds ground at Sperenberg/Schönefeld and
     convoys/airlifts roll toward the front, blue builds at Ramstein, and the IADS shows networked
     (Skynet) behavior with destroyable C2/power per base.
   - **C2 nodes → real map buildings, Haina + Templin (2026-06-24).** The hand-placed C2
     statics landed on airfield aprons (blocking spawns, ugly — seen at Haina). Replaced via the
     scenery-import pipeline (`SceneryGroup` trigger zones, not statics): for each node a blue
     `type=0` def zone (`PROPERTY_1=commandcenter|comms|power`, r=100) over a real building + a
     white `type=2` kill quad. **Haina:** `KDP_USSR` (cc, 261 m), `RSP-10MA` radar (comms, 658 m),
     transformer (power, 728 m) — completes Haina's trio (it had no power node). **Templin:**
     `BARRACK_SMALL` (cc, 2.6 km), `NDB_RADIO` (comms, 2.6 km), transformer (power, 1.3 km) — gives
     Templin the full trio (it had only a comms static). **Removed** the `Haina Command Center`,
     `Haina Comms`, `Templin Comms` statics (deleted `red.static_group` keys `[20]/[21]/[22]`;
     pydcs iterates the table as a dict so the index gap is harmless). Edit was the hand-Lua +
     `zipfile` path (pydcs save still broken). **Verified (pydcs):** miz loads; all 6 groups parse
     to the right `GroupTask` with one white zone each; the 3 statics are gone, others intact; every
     building's nearest airfield is its own base (Haina 0.4–0.9 km, Templin 1.5–2.8 km; next field
     8–11 km), so TGOs anchor correctly. **In-game pass still needed:** apron clear at Haina/Templin,
     kill quads sit on the real objects, and Skynet still wires the base SAMs to the new C2 (Templin's
     2.6 km cc/comms are the marginal case). Kastrup/Hamburg/Peenemünde still use placed statics
     (no scanner dump coverage — needs a re-scan; Phase 2).
   - **C2 + ammo → real buildings, Phase 2: Hamburg/Kastrup/Peenemünde + Sperenberg/Schönefeld ammo
     (2026-06-24).** After the user re-flew the CWG scanner over the three previously-uncovered bases
     (dump 216k→410k rows, bbox now reaches Kastrup), the remaining **placed** C2/ammo statics were
     replaced with real-building scenery nodes (same `SceneryGroup` blue-def + white-quad pattern).
     **Deleted 12 statics** (Hamburg/Kastrup/Peenemünde Command Center+Comms+Power, Kastrup/Sperenberg/
     Schönefeld Ammo Depot) and dropped kill-quads on matched real buildings 0.1–1.5 mi from each
     field: e.g. Hamburg cc=`KDP`/comms=`VOR_DME`/power=`TRANSFORMER`; Kastrup comms=`TESLA_RP3F`
     (0.12 mi); Peenemünde cc=`BARRACK_SMALL` (0.12 mi); ammo on `INDUSTRIAL_*` buildings. The picker
     skips buildings already used by an existing zone (the scenery **strike** targets), re-checks
     nearest CP, and uses `ammo`→`GroupTask.AMMO`. **Why this fixes the garbage:** a real building is
     by definition cleared ground — unlike the earlier "open-ground" guesses, which were unreliable
     because the dump catalogs *buildings*, not forest/field/water. **Verified (pydcs):** miz loads;
     all 12 nodes parse to the right GroupTask with one white zone each; 12 statics gone; Haina/Templin
     IADS intact.
   - **SAMs → standalone sites in open farmland @ 1–2.3 mi (2026-06-24).** Design intent (user):
     unlike the C2/economy targets, **SAMs must NOT sit on/beside map buildings** — they're standalone
     SAM sites at a real standoff *from* the airfield. (An earlier pass had wrongly parked them ~55 m
     beside buildings.) All 10 SAMs (Haina, Templin, Wittstock, Sperenberg ×2, Schönefeld ×2, Kastrup
     LORAD, Hamburg, Peenemünde) relocated to **open spots 1.0–2.3 mi from their field**, in the field
     **~140 m beside an *isolated* farm building** (a building cluster of 1–8 within 200 m). The logic:
     a SAM in the open with no building within ~110 m but a farm within ~260 m is **farmland, not deep
     forest** (deep forest has no buildings for km) and not a lake — the best terrain proxy available
     since pydcs has no surface query and the CWG dump only catalogs buildings. **Verified (pydcs):**
     all 10 at 1.0–2.3 mi standoff, ≥110 m from any building, nearest CP = own base. **Residual
     in-game-pass risk:** the isolated-farm proxy is heuristic, not a true terrain test — spot-check
     in the ME / nudge any that still land in trees.
   - **Apron-blocking cleanup — SAMs + remaining statics off parking slots (2026-06-24).** The
     placement-fix (item below) snapped objects onto parking slots, which blocked aircraft spawns
     (user screenshot). Audited every red base: 13 objects sat at 0 m from a parking slot — 6 SAM
     markers (Templin/Haina/Wittstock/Hamburg MERAD, Sperenberg MERAD+LORAD), the Sperenberg ammo
     depot, and the Hamburg + Kastrup C2 trios. **All are pure coordinate moves** (group + unit +
     route-point x/y rewritten in-place, anchored on the unique `groupId`; no new groups). Two
     strategies, since pydcs has **no terrain-clear query** (the forest/water trap):
     **Distances are a real 0.5–2 mi standoff, not a perimeter nudge** — an early pass placed these
     only 150–650 m off the field (still hugging the runway, user screenshot of Sperenberg); they were
     re-pushed to ~0.7–0.9 mi.
     - **Dump-covered SAMs + Sperenberg ammo → open ground @ ~0.9 mi.** Sampled 0.5–2 mi rings off
       Templin/Haina/Wittstock/Sperenberg; kept points >250 m from any parking slot, with the nearest
       CWG-dump building bracketed 90–600 m (dry land nearby but not on a structure — doubles as the
       anti-water/void guard), and **re-checked nearest control point** so the larger offset still
       anchors each object to its own base (next field 8–11 mi away). Result: ~0.9 mi out, 605–1106 m
       slot clearance, nearest building 265–573 m.
     - **Hamburg SAM + Hamburg C2 trio → inland open ground @ 0.7–0.9 mi (no dump, BLIND).** Hamburg
       is outside the dump bbox (urban), so these can't be dump-validated. Offset into the inland arc
       (~122°, toward the A24/Hagenow supply corridor, away from the Elbe), spaced. **Highest residual
       risk — verify in-game; a CWG re-scan over Hamburg would let this be done safely / as real
       buildings.**
     - **Kastrup C2 trio → left on far dispersal hardstands (~1.1 mi).** No dump coverage; already
       well off the active ramp on guaranteed-clear pavement, so unchanged.
     **Verified (pydcs):** miz loads, brace-balanced; **nothing within 0.5 mi of any red base**; all
     at target coords; C2 scenery zones (6) + all statics intact; nearest CP re-confirmed as each
     object's own base. NB the Sperenberg `Comms Site` / `Fuel Depot` markers near the field are
     **real-building scenery *strike* targets** (0.6–0.7 mi, actual map buildings) — intentional, not
     relocatable, and not parking blockers.
     **In-game pass:** open-ground SAM/ammo spots not in forest/water; **Hamburg** the case to watch
     (blind inland placement, no dump validation).
7. **Medium-range SAM belt added** (2026-06-23). Red's air defense was long-range (S-300) +
   AAA + scattered short-range, with the main red bases carrying *no* medium SAM. Air-defense
   range is slot-driven: each control point's `medium_range_sams` preset locations come from
   **`.miz` vehicle markers** whose launcher type sets the bucket
   (`MizCampaignLoader.MEDIUM_RANGE_SAM_UNIT_TYPES`, scanned in **`self.red.vehicle_group`** only);
   `generate_aa_at` then fills each medium slot with a MERAD ForceGroup. The faction already had 7
   MERAD templates (SA-2 ×3, SA-3 ×2, SA-6, SA-11), so the gap was **slots, not templates**.
   Added one `S_75M_Volhov` medium marker (→ MERAD: random SA-2/3/6/11) to the **CJTF Red** vehicle
   group at each of the 8 red bases that lacked one: Haina, Sperenberg, Schönefeld, Templin,
   Wittstock, Peenemünde, **Hamburg** (Hamburg's stock marker is silently dropped by a pre-existing
   duplicate-key in the red vehicle table — same hand-edit quirk as the Kastrup statics; left as-is,
   out of scope). Placed at base center `(-2000, -1000)` — a distinct quadrant from each base's IADS
   cell but well inside the 15 nm comms range, so the new MERAD sites are **networked by the
   advanced IADS** added in item 6. Additive: existing markers untouched (verified — 5 stock red
   S-75 survive, +7 added = 12 loaded). Text-edit + re-zip; anchored on the existing red marker
   `groupId 116` (the early summary `["red"]` block is NOT the country-data coalition — anchoring
   there put markers in **blue** on the first attempt). IDs from `groupId 400`/`unitId 800`.
8. **LORAD depth at the rear hubs** (2026-06-23). Added one `S-300PS 5P85C ln` long-range marker
   (→ LORAD: SA-10/S-300PS or SA-5/S-200) to the **CJTF Red** vehicle group at **Sperenberg** and
   **Schönefeld**, giving the Berlin-cluster rear a long-range belt behind the front (red had only
   2 LORAD markers before, now 4). Both hubs are now layered LORAD + MERAD + (existing short/AAA),
   inside their IADS comms range so they network. Same text-edit/anchor method as item 7; IDs
   auto-allocated above the current max.
9. **Placement moved onto airfield aprons** (2026-06-23). Items 6–8 used blind base-center
   offsets, which dropped several structures into forest/built-up terrain (in-game screenshot).
   pydcs exposes no surface-type query and the GCW reference missions
   (`CG_Cold War Germany Framework`, `Foothold_GCW`) place objects only at *their* sites — too
   sparse near our bases (Hamburg's nearest reference is 42 km). The one guaranteed-clear, paved
   location at every base is the **parking apron**, so all **38 additions** (3 factories, 2 ammo,
   8 CC, 8 comms, 8 power, 7 MERAD, 2 LORAD) were relocated onto `airport.parking_slots` via
   farthest-point sampling (spread across the apron) biased toward heli/cargo slots to limit
   fixed-wing parking conflicts. Block-scoped x/y rewrite (`relocate_to_aprons.py`); Kastrup's CC
   uses a value-based fallback (its repurposed block has the original hand-edited shallow indent).
   Verified via pydcs: all 38 on their base apron (≤3.9 km from the airfield ref, correct nearest
   CP), members byte-identical. **Trade-off / in-game watch:** buildings + SAM sites now sit on the
   apron (clear, but visually on-field); if a static lands on a slot Retribution wants for a based
   aircraft there can be a spawn overlap — watch the red bases that host squadrons.
10. **Duplicate-key cleanup — clobbered groups recovered** (2026-06-23). The Kastrup/Copenhagen
    hand-edits (items 4–8) appended new red groups while **reusing the integer table keys `[1]`/`[2]`**
    that stock groups (and each other) already held. In Lua a later `[k] = …` silently overwrites the
    earlier one, so on load the red country was **dropping 6 groups**: two `["vehicle"]` markers
    (`Ground-2-1`, `Ground-3-1` — stock `S_75M_Volhov` SAM sites) plus the Kastrup **SHORAD** and
    **AAA** vehicles (only the last `[1]`/`[2]` — Kastrup LORAD/MRAD — survived), and two
    `["static"]` groups (**both Invisible FARPs**, clobbered by the Kastrup Command Center + Ammo
    Depot). Earlier notes flagged this as out-of-scope ("Hamburg's stock marker silently dropped",
    "10 of 12 FARPs survive"); the Hamburg **MERAD** marker (`[52]`, gid 406) was actually fine — the
    real loss was these 6 `[1]`/`[2]` collisions. **Fix** (`tools/fix_red_tide_dup_keys.py`): renumber
    only the six hand-added Kastrup blocks to free keys — vehicle `[55]`–`[58]`, static `[38]`/`[39]`
    — leaving stock `[1]`/`[2]` intact. groupIds/unitIds were already unique and are untouched; only
    table keys change. Text-edit + re-zip (pydcs `Mission.save` is broken for this miz). **Verified
    (structural):** red vehicle table 54→58 unique groups, static 37→39, **no remaining duplicate
    keys**, valid brace nesting, and every other `.miz` member byte-identical. (pydcs/DCS aren't
    runnable here, so an in-game pass should still confirm the recovered SAM/FARP/Kastrup-SHORAD/AAA
    groups spawn.)
11. **Human-led offensive retune — fewer blue AI flights** (2026-06-23). Goal: make the human's
    414th sorties the spearhead instead of letting the blue auto-planner fill the whole ATO. Two
    coordinated, **campaign-yaml-only** levers (both in `red_tide.yaml`, no `.miz` change):
    - **AI-only squadron trims** (player-flyable 414th airframes left large): A-6E 12→6, B-1B 6→4,
      Mirage-F1EE 8→6, AV-8B 8→6, F-15C 8→6, Tornado IDS 10→8. **Untouched** (human-flown): F-16CM 12,
      F/A-18C 12, F-15E 12, F-14B 8, A-10C 8, every F-4E 8, B-52H 4. Fewer AI airframes ⇒ fewer
      simultaneous AI flights per turn (the planner gates each flight on untasked inventory).
    - **`settings:` block** (merged into the existing `squadron_start_full` block — there can only be
      **one** top-level `settings:` key; YAML keeps the last, so a second block silently wins):
      `ownfor_autoplanner_aggressiveness: 10` (default 20 — blue AI ignores less of red's threat
      radius, so it won't auto-throw strike/SEAD packages into the IADS belt; the human flies those)
      and `oca_target_autoplanner_min_aircraft_count: 40` (default 20 — airfield OCA becomes a
      human-chosen objective). OPFOR aggressiveness untouched. These seed **recommended new-game
      defaults** (`QNewGameSettings._load_campaign_settings` → `settings.__dict__.update`), so the
      wizard can still override them. **Verified:** yaml parses; the merged `settings` block is
      `{squadron_start_full, ownfor_autoplanner_aggressiveness: 10, oca_target_autoplanner_min_aircraft_count: 40}`
      (plain ints — no enum/timedelta conversion). **In-game watch:** confirm the AI doesn't stall
      the offensive — if blue under-flies, raise aggressiveness back toward 15–20 or bump
      `recommended_player_income_multiplier`; if blue *still* out-flies the human, trim those further.

### Fulda forward heli base + supply re-route

- **Why.** A blue forward FARP in the Fulda Gap, on the Frankfurt→Haina axis (Fulda sits ~2.5
  km off the old front route). Fulda hosts three forward US Army heli squadrons (AH-64D 1-1
  ARB, OH-58D 1-6 Cav, UH-1H 159th Avn Det Fwd) with their own defs/liveries.
- **Supply re-route.** The single `Frankfurt (163) → Haina (161)` front route was split into
  `Frankfurt → Fulda` (blue rear) + `Fulda → Haina` (the new front line), both anchored on
  Fulda's exact coordinate `(-401102, -768302)`.
- **Red-end anchor fix.** `add_yaml_supply_routes` resolves each route end with
  `theater.closest_control_point`, which considers **all** CPs (including neutral FARPs). The
  old Haina-end waypoint `(-359860, -710938)` was 2.9 km from the neutral FARP **`H Med GDR
  12` (180)** but 8.9 km from Haina, so the original "front" actually anchored on 180, ~9 km
  short of Haina (a plausible cause of FLOT units appearing south-west of Haina). Route B now
  ends on **Haina's exact CP position `(-359857, -702040)`** so the front is cleanly
  Fulda↔Haina. Verified: that endpoint resolves to `[161] Haina` at 0.0 km.

### Faction edits (shared)
- `resources/factions/russia_1980.json` — added `SA-11` (Buk) and `SA-10/S-300PS` preset
  groups. Both are vanilla DCS and match the names already used by `russia_1990`. This is a
  **shared-faction** change, so the original Crossing the Rubicon also gets the tougher IADS.
- `resources/factions/blufor_late_coldwar.json` — added `KC-135 Stratotanker MPRS` to
  `tankers` so the Frankfurt MPRS (drogue) squadron's def actually loads (the loader drops any
  def whose airframe isn't in the faction). Also shared, but additive — it only makes the
  airframe available.

### Aircraft / squadron specifics
- **German Phantom:** the `GAF JG 74` "Moelders" entry is a *squadron name* in the
  `aircraft:` list, not an aircraft type. `DefaultSquadronAssigner.find_squadron_by_name`
  matches the predefined squadron def (`resources/squadrons/F-4E-45MC/GAF JG-74.yaml`,
  country Germany, livery `37+36_N72_JG74`) so it spawns with the real Luftwaffe livery.
  Works because Blufor's country is `Combined Joint Task Forces Blue` (`any_country`), so
  German-country squadron defs load as long as the airframe is in the faction.
- **Tomcat buff:** F-14A (Block 135-GR Late) → **F-14B Tomcat**.
- **Coverage adds:** F-15E Strike Eagle (Hahn BAI) and the OH-58D Kiowa (Frankfurt) — the
  Kiowa had been lost when Hamburg flipped red.
- **F-111C removed** entirely (squadron + the `f111c` mod setting + the mod note); the
  UH-60A is intentionally left out. The campaign now only notes the Heatblur F-4E module.

### Squadron naming & liveries (every squadron is now a named, liveried unit)

**Problem.** A campaign squadron entry that lists a bare **aircraft type** gets its def from
`DefaultSquadronAssigner.find_squadron_for_airframe`, which collects *every* predefined
squadron def for that airframe and does `random.choice` with **no country filter**. So a
NATO `F-4E-45MC Phantom II` could spawn in Egyptian/Greek/Korean colors and a GSFG `Mi-24P`
in South-African camo. That randomness was the "many mismatches" seen in-game.

**Fix / mechanism.** A livery can only be pinned by a **predefined squadron def**
(`resources/squadrons/<type>/<unit>.yaml`, fields `name`/`nickname`/`country`/`role`/
`aircraft`/`livery`) **referenced by name** in the campaign's `aircraft:` list — exactly how
`GAF JG 74` and `185th GvIAP Fighter Regiment` already worked. The campaign squadron config
(`SquadronConfig`) has **no livery field**, so inline liveries are impossible. Every Red Tide
squadron now references such a def, with `aircraft_type:` kept as a fallback airframe:

```yaml
    - primary: BARCAP
      secondary: any
      aircraft:
        - 85th Guards Fighter Aviation Regiment   # predefined def -> name + livery
      aircraft_type: MiG-29A Fulcrum-A             # fallback airframe if the def is missing
      size: 6
```

**Two constraints that shaped the defs (both verified in code):**
- **Country gate.** `SquadronDefLoader.load` loads a def only if the faction is
  `any_country` *or* `def.country == faction.country`. Red's faction country is `Russia`, so
  **all red defs use `country: Russia`**; Blufor is `Combined Joint Task Forces Blue`
  (`any_country`), so blue defs can carry their real nation (`USA`/`Germany`/`Spain`).
- **Capability gate.** `SquadronDef.capable_of` is **airframe-based**, not from the def's
  `mission_types:` list (that field is decorative — `from_yaml` recomputes from the airframe).
  `find_squadron_by_name` rejects a def whose airframe can't do the squadron's `primary`, so
  the Sperenberg Backfire regiment's primary was changed `OCA/Aircraft → OCA/Runway` (the
  Tu-22M3 can do Strike / Anti-ship / OCA/Runway, not OCA/Aircraft).

**Naming scheme (the user's "real red, 414th blue" call):**
- **Red** keeps the real GSFG/VVS regiments already named inline (85 GvIAP, 831 GvIAP, …),
  now each with `country: Russia` + a period Soviet livery (e.g. Mi-24P `AF USSR` /
  `262nd_SHQ_USSR`, MiG-29-Fulcrum `Soviet AF 968th FAR`, Su-27 `Air Force Standard Early`).
- **Blue** wears 414th Joint Fighter Group identities where the squadron has its own livery
  pack — **VMF-29** (F-14B), **Voodoo** (F-16CM), **414th TFS** (F-15E), **JFG Hornets**
  (F/A-18C), **414th Aviation Det / Huey** (UH-1H), **910th AW** (C-130J) — and real USAFE/
  USN/USMC/Luftwaffe units wearing period liveries elsewhere (81st TFS A-10 in the Spangdahlem
  scheme, 493rd FS Eagles, JBG 31 *Boelcke* Tornados, NATO E-3A, 12th CAB Apaches, …).

**Livery IDs are folder/zip basenames** under the DCS install (`Bazar/Liveries`, `CoreMods`,
`Mods`) — each was checked against a real folder, *not guessed*. The 414th custom liveries
live in `Saved Games\DCS\Liveries` (per-user, squadron-distributed); a non-414th player who
lacks the pack falls back to the airframe default for those names (cosmetic only).

**480th SEAD-Sweep gap (fixed 2026-06-27).** A liveries-folder audit of the live build found
the SEAD-Sweep F-4E slot referenced `480th Tactical Fighter Squadron`, for which **no
squadron def existed**. With no name match, `find_squadron_by_name` returned `None` and
`find_preferred_squadron` fell through to `find_squadron_for_airframe`, which does
`random.choice` over **every loaded F-4E def with no country filter** — and because Blufor is
`any_country`, that pool includes the Egyptian/Greek/**Israeli**/Iranian/Japanese/RAF/ROKAF/
Turkish F-4E defs. So the NATO SEAD package was spawning Israeli *Kurnass* (and other foreign)
Phantoms at random. Fixed by adding `resources/squadrons/F-4E-45MC/414th 480th TFS.yaml`
(name `480th Tactical Fighter Squadron`, `country: USA`, livery `RS68-517_SEA_526TFS` — an
installed, previously-unused USAFE Ramstein paint), mirroring the 512th/526th defs. A
resolver pass (`find_squadron_by_name` + airframe `capable_of`) over all 51 campaign squadron
references now reports **0 unbound slots**; the 480th is the last random-livery leak in the
roster.

## Known caveats — verify on first in-game load

The Lua plugins/terrain can't be exercised here; pydcs/DCS aren't runnable in CI. Confirm:

1. **Kastrup loads as red.** If it shows neutral, the `[41]` warehouse entry didn't take.
2. **All three naval groups spawn red.** Coalition is resolved by nearest base; up north
   that is red (Kastrup/Peenemünde), but it is computed at load, not asserted here.
3. **`Red Navy Copenhagen` position** (x≈80000, y≈-430000) is an *estimated* open-water
   point off Copenhagen — eyeball that it isn't clipping land/an island. One-line nudge if so.
4. **Liveries render correctly.** All 47 squadron defs load and resolve in a campaign-config
   check (`name`/`country`/airframe/`capable_of(primary)` all pass), but the **livery string
   itself is only exercised in-game** — generate a mission and confirm each unit wears the
   intended paint, especially the 414th custom skins (need the Saved Games livery pack
   installed).
5. **A-10 is A-10C Suite 3** (`A-10C Thunderbolt II (Suite 3)`, dcs `A-10C`) — converted from
   the AI-only A-10A so the CAS squadron is player-flyable. **Not** the modern Suite 7 /
   A-10C II (`A-10C_2`). The 81st TFS (Panthers) keeps the stock USAFE *Spangdahlem* livery
   (`81st FS Spangdahlem AB, Germany (SP) 1`), which exists in the `A-10C` livery set too. The
   414th "Bulldog" skin is Suite-7-only and intentionally **not** used here.

## Files
- `resources/campaigns/red_tide.yaml` / `red_tide.miz` — the campaign.
- `resources/campaigns/crossing_the_rubicon.*` — original, preserved (An-26B fix only).
- `resources/factions/russia_1980.json` — SA-10/SA-11 preset groups.
- `resources/squadrons/<type>/*.yaml` — the 48 named squadron defs (23 red GSFG/VVS regiments,
  22 blue 414th/USAFE/USN units, + 3 Fulda forward-FARP heli units: 1-1 ARB, 1-6 Cav, 159th
  Avn Det Fwd) that pin each squadron's name + livery; referenced by name from `red_tide.yaml`.
  The two pre-existing refs (`GAF JG 74`, `185th GvIAP Fighter Regiment`) and the existing
  `340th EARS` MPRS def are reused, not duplicated.
- `resources/factions/blufor_late_coldwar.json` — `KC-135 Stratotanker MPRS` added to tankers.
