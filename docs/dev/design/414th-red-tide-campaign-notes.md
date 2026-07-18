# 414th Red Tide Campaign Notes

> ## 🔒 FEATURE LOCK — Red Tide (effective FRIDAY NIGHT 2026-07-17; user correction 2026-07-12)
>
> **The lock takes effect Friday night 2026-07-17**, when the user regenerates the campaign
> with every feature landed by then and processes a turn 1 for the squadron from the
> 2026-07-11 M1 session JSON. **Until that regeneration, new features and Red Tide preseeds
> MAY land** — anything merged before Friday ships in the fresh build (no save-compat risk).
>
> **From the Friday-night regeneration onward, Red Tide is FEATURE-LOCKED. Do NOT add new
> features, mechanics, content, or laydown scope to this campaign.** It is a shipped,
> balanced build and the goal then is to keep it stable, not to keep bolting things on. If a
> future session (or a future you) is tempted to "force" one more system into Red Tide — a
> new plugin toggle, another laydown object, a balance re-skew, a new economy knob — **stop
> and don't.** That is exactly the "force bullshit in later and break it" the lock exists to
> prevent.
>
> **Still allowed under the lock** (a lock is not a freeze on correctness):
> - **Bug / crash fixes** to already-shipped Red Tide behavior (e.g. the custom-callsign
>   spawn crash, the SCUD/COIN 2-WP mover fix, the artillery-reach tune — these are repairs,
>   not features).
> - **In-game-pass verification** of features already built into Red Tide and closing out its
>   checklist rows.
> - **Tuning an already-shipped Red Tide mechanic** to its intended behavior when an in-game
>   pass shows it misfiring (e.g. the 42 km artillery reach, the ambush light-kit re-scope).
>
> **NOT allowed without an explicit new user go-ahead that overrides this lock:** adding a
> brand-new feature/plugin/setting to Red Tide, expanding the laydown, or re-opening the
> balance pass. If in doubt, ask the user before touching it.
>
> **Lock-override record:**
> - **2026-07-18 (explicit user go-ahead, post-lock):** §71 Expanded F-4E Weapons Pack
>   restored as an optional mod and preseeded ON (`f4e_expanded_weapons: true` in the
>   campaign settings block) — the Heatblur F-4E gains its AGM-88 stations and SEAD-tasked
>   Phantoms auto-load the "(XW)" HARM fits (stock Shrike fit is the automatic fallback when
>   the box is unchecked or the mod is ejected). Settings-namespace preseed only, no
>   laydown/balance change; applies to NEW games only, so it ships with whatever
>   regeneration follows it.
>
> **The "process turn 1 from the M1 session JSON" step is tooled** —
> `tools/apply_state_json.py` (built + validated 2026-07-12) re-binds the flown 2026-07-11
> `state.json` to ANY regenerated Red Tide save: it translates every kill event from the
> flown save's namespace (TGO unit ids, ATO flight names, front-line units, QRA squadron
> UUIDs) into the fresh game's, then runs the real debrief → commit → `pass_turn` pipeline
> headlessly and writes a processed turn-2 save. **The canonical M1 event bundle is
> archived in `C:\Users\brady\Saved Games\DCS\Retribution\Saves\Claude needs these\`**
> (the flown source save, the `state.json`, the actual flown
> `Red Tide M1 with Mags happy.miz`, the old-campaign TURN 2 SAVE, and the event-night
> `dcs.log`); bundle cross-verified 2026-07-12 — 116/121 state.json kill names bind to the
> flown miz, the 5 misses being runtime spawns (a dynamic-slot jet + QRA clones) that never
> appear in a miz. Friday-night usage:
>
> ⚠️ **The target must be a TURN-1 save, not a literally fresh new game.** The source
> `state.json` carries 29 front-line kills, and the front-line pool is matched against the
> *target's* live ground forces. A brand-new game is **turn 0 with zero armor at every CP**
> (`Haina armor=0, Fulda armor=0` — verified headlessly through the real `GameGenerator` →
> `begin_turn_0` pipeline), so every front kill drops on the floor and
> `missionresultsprocessor` tests `ally_units_alive == 0` FIRST — handing blue a **fabricated
> strong defeat** and then `pass_turn`-ing it into the season save. The invariant is simply
> **the target's turn must match the source's turn** (the source is turn 1). So: New Game →
> **pass one turn** → save → target THAT. No manual purchasing needed; automatic procurement
> reaches ≈11/11 armor on its own. Same JSON, same build, measured both ways:
>
> | target | FRONT translation | verdict |
> |---|---|---|
> | genuine fresh turn 0 (0/0 armor) | `0 mapped, 0 side-fallback, 29 DROPPED` | ❌ "Allied ground forces suffer a strong defeat" |
> | turn 1 (11/11 armor) | `10 mapped, 5 side-fallback, 14 dropped` | ✅ "Allied ground forces win a strong victory" |
>
> The drop is **not** loudly flagged: `report.print()` runs *after* the commit and words it
> as the benign "dropped (front thinner than kill count)". Read the FRONT line yourself.
>
> ```powershell
> .venv\Scripts\python.exe tools/apply_state_json.py `
>   --source-save "C:\Users\brady\Saved Games\DCS\Retribution\Saves\Claude needs these\414th red tide v5 6pm lock.retribution" `
>   --state "C:\Users\brady\Saved Games\DCS\Retribution\Saves\Claude needs these\state.json" `
>   --target-save "<the Friday-night save AFTER passing one turn — turn 1>" `
>   --out-save "<new save name for turn 2>"
> ```
>
> The printed translation report lists every mapping/fallback/drop, and its header prints
> `Target: <name> (turn N)` — **confirm it reads `(turn 1)` before trusting the run.**
> Validated 2026-07-12 against `Saves\turn 0.retribution`, and **that filename is a trap**:
> it does NOT contain a turn-0 game. It loads as **turn = 1** with Haina 11 / Fulda 11 armor
> (re-verified headlessly 2026-07-16), which is exactly why the validation passed — RED −35
> airframes matched the real turn-2 processing, and the Haina IADS layer, comms building,
> runway hit, and front-line result all carried. Rename it if you get the chance; as it
> stands the name teaches the wrong lesson to whoever runs this next.
>
> Do not fly the throwaway miz it generates. `pass_turn` rewrites `autosave.retribution`,
> same as the app. A bad run is fully re-runnable — `--out-save` writes a new file and
> nothing is consumed until M2. Keep the archive folder intact through the Friday
> regeneration (and after — it is the season's historical record of M1).

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
**`Russia 1980 (Red Tide)`** — the *fork*, not the shared base `Russia 1980`
(`resources/factions/russia_1980_red_tide.json`; `recommended_enemy_faction` at
`red_tide.yaml:6`). The distinction matters at New Game: the base faction silently loses both
the single-radar S-300 regiments and the SA-15 Tor / SA-19 Tunguska point defense.
The red-heavy laydown (red still holds the north, centre, and east) is *why*
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
>    > ⚠️ **The red-trim line above never matched the yaml and is kept only as the record of
>    > what was *planned* on 2026-06-23.** Engine-dumped 2026-07-16, the live sizes are
>    > **Peenemünde 8 · Hamburg 12 · Sperenberg 12** — plus Haina's 24 (MiG-29A ×12 + MiG-23MLD
>    > ×12), which this plan never mentioned. Red fields **56 fixed-wing fighters**, not the 16
>    > implied here. Trust the generated Force-laydown tables below, not this line.
> 3. **Red posture / AI — no knob needed.** Red's QRA reserve (`opfor_default_qra_reserve`) and
>    planner unpredictability are already at the defaults that favor a blue offensive (reserve 0,
>    deterministic). *Raising* red's QRA would make red defend better (backfire); it can't go
>    lower than 0. The intended "red stays reactive" effect instead falls out of (1)+(2) — cutting
>    red's economy and fighter mass naturally shrinks red's offensive air. Left at defaults.
>    > ⚠️ **Superseded.** The campaign now deliberately preseeds `opfor_default_qra_reserve: 4`
>    > (see the settings block) — the reasoning inverted once red went defensive-only: a hot-alert
>    > reserve is what makes red fly a dense defensive screen, and the M1 Tacview showed the QRA
>    > path is red's *only proven-firing* planned fighter path. Do not "restore" this to 0.
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

> **These tables are generated from the yaml, not hand-maintained.** They drifted badly once
> (documenting 16 red fighters against an actual 32) and the fighter count is the number that
> drives the whole air balance — so re-dump rather than hand-patch. Last regenerated
> **2026-07-16** by binding `squadrons:` through the engine's own resolver
> (`CampaignAirWingConfig.from_campaign_data` + `find_control_point_by_airport_id`), i.e. what
> the game actually loads. **Totals: BLUE 116 airframes / 40 fighter-role · RED 171 / 64
> fighter-role** (red's 64 includes 8 Mi-24P Escort helos ⇒ **56 fixed-wing fighters**).

### Blue (NATO) — south-west cluster · 116 airframes
| Base | id | Squadrons (type × size, primary) |
|---|---|---|
| Ramstein | 165 | B-52H ×4 Strike · E-3A ×2 AEW&C · KC-135 ×2 Refueling · KC-135MPRS ×2 Refueling (drogue) |
| Frankfurt | 163 | **F-16CM Block 50 ×12 DEAD** (414th Voodoo) · **F/A-18C Lot 20 ×12 SEAD** (414th JFG Hornets) · F-15C ×6 TARCAP · F-14B ×8 Escort · GAF JG 74 ×8 TARCAP (AI, faction default) · A-10C Suite 3 ×8 CAS · F-15E Suite 4+ ×12 BAI · Mirage-F1EE ×6 Escort · C-130J-30 ×2 Transport |
| **Fulda** | **166** | **Forward FARP (flipped neutral→BLUE).** AH-64D ×4 CAS · OH-58D ×4 Armed Recon · UH-1H ×4 Air Assault · CH-47F ×4 Air Assault · AH-64D ×4 Escort · OH-58D ×4 Escort · UH-1H ×4 Air Assault · AH-1W ×4 Escort |
| Spangdahlem | 162 | *(no squadron block — quiet rear field)* |
| Hahn | 155 | *(no squadron block — quiet rear field)* |

*(Blue basing re-laid 2026-07-05 from the user's in-app air-wing pass — the `414th red tide.retribution`
save is the source: Frankfurt is the main fighter base (414th Vipers/Hornets + the fighter cover +
the support wing) AND now hosts the F-15Es, the A-10s, the Mirage and the C-130; Ramstein is the rear
heavy-iron/AEW&C/tanker field; ALL rotary sits forward at Fulda. Spangdahlem and Hahn kept their
`id`s but no longer carry a squadron block at all.)*

### Red (Soviet/WP) — north, centre, east · 171 airframes, 56 fixed-wing fighters
| Base | id | Squadrons (type × size, primary) |
|---|---|---|
| Hamburg | 17 | **Captured** (flipped BLUE→RED). Forward airhead: **MiG-29A ×12 BARCAP** · Su-25 ×8 Armed Recon · Su-24M ×8 SEAD · Mi-24P ×4 Escort · Mi-8MTV2 ×4 Air Assault |
| Kastrup / Copenhagen | 41 | **Soviet-seized far-north enclave.** Maritime strike: Tu-22M3 ×8 Anti-ship · Su-24M ×8 SEAD · An-26B ×4 Transport |
| **Haina** | **161** | **Western Soviet spearhead — the theatre's fighter concentration: MiG-29A ×12 BARCAP + MiG-23MLD ×12 TARCAP (24 fighters)** · Su-25 ×8 Armed Recon · MiG-27K ×8 SEAD Escort |
| H FRG 20 | 143 | **Flipped NEUTRAL→RED** (see the `.miz` edits ledger). Mi-24P ×4 Escort · Mi-8MTV2 ×4 Air Assault |
| Sperenberg | 101 | Tu-95MS ×8 Strike · Tu-22M3 ×8 OCA/Runway · **Su-27 ×12 BARCAP** |
| Schönefeld | 26 | A-50 ×1 AEW&C · IL-78M ×2 Refueling · An-26B ×4 Transport |
| Templin | 15 | Su-24M ×8 SEAD · 185th GvIAP ×8 BAI (faction default) |
| Wittstock | 1 | Su-17M4 ×8 DEAD |
| Peenemünde | 25 | **MiG-29 ×8 BARCAP** (Baltic coast) |

*(The rotary that older revisions of this note placed at Haina now lives at **H FRG 20**; Kastrup's
MiG-29 moved to Haina. Red's fighter force is **56 fixed-wing across 5 regiments** — Hamburg 12,
Haina 24, Sperenberg 12, Peenemünde 8 — all BARCAP/TARCAP-primary per the settled defensive posture.)*

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

5b. **H FRG 20 flipped RED (forward helo FOB).** *(Ledger entry added 2026-07-16 — the edit
   itself landed with the forward-basing pass; it was made but never recorded here.)* Airport
   `[143]` (H FRG 20) was NEUTRAL with `["dynamicSpawn"] = true`. **Exactly the same two-field
   edit as Fulda 166 above**, for the same loader reason (`control_point_from_airport` forces a
   `dynamic_spawn` airport NEUTRAL *before* checking coalition): `dynamicSpawn true → false`
   **and** `coalition "NEUTRAL" → "RED"`. This is what gives Haina's displaced Mi-24P/Mi-8
   detachments a red field to base from — without it they are stranded at a neutral field.
   **Guarded** by `tests/fourteenth/test_red_tide_forward_basing.py::test_h_frg_20_loads_red`,
   whose assertion message carries the recovery instruction, so a silent revert fails CI rather
   than the event. Recorded here anyway: this ledger is what survives a re-save of a `.miz` that
   gets hand-edited as often as this one.

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
   - **Advanced IADS (range mode):** `advanced_iads: true` in the yaml (**no** `iads_config`;
     range mode auto-wires SAMs to comms <15nm / power <35nm / command center). **Correction
     (2026-07-12): the earlier claim that Falcon-style by-name `iads_config` is "impossible" here
     because the SAMs spawn with random names is WRONG.** A marker-spawned site's *display* name is
     random (`start_generator.generate_ground_object_from_group` → `random_objective_name()`), but
     its **`original_name` is the marker group's name** (`theatergroundobject.py` sets
     `original_name = location.original_name`; `PresetLocation.from_group` copies `group.name`), and
     `iads_config` matches on exactly that (`iadsnetwork.py` `self.ground_objects[tgo.original_name]`).
     So by-name wiring *is* feasible — give the markers unique stable names and wire them like The
     Falcon. Range mode simply stays because it needs no per-site bookkeeping and scales with the
     laydown; the choice is convenience, not a constraint. Each red SAM base
     (Sperenberg, Schönefeld, Hamburg, Haina, Templin, Wittstock, Peenemünde, Kastrup) got a
     co-located **Command Center + Comms tower M + GeneratorF** cell. The dead "Kastrup Factory"
     was **repurposed in place** into "Kastrup Command Center" (same spot, no renumber needed).
     - **FOLLOW-UP (2026-06-24) — ✅ RESOLVED, the statics are gone.** These placed C2 statics
       landed on some airfield aprons and blocked aircraft spawns (seen at Haina); the plan to
       replace them with **real map buildings** was scoped in
       [`414th-red-tide-c2-real-buildings-HANDOFF.md`](414th-red-tide-c2-real-buildings-HANDOFF.md)
       — **and then landed.** Re-verified 2026-07-16: the campaign now loads **11 `commandcenter`
       + 9 `comms` + 11 `power`** scenery zones (real destroyable buildings), and `ComCenter` /
       `Comms tower M` / `GeneratorF` each return **0 hits** in `red_tide.miz`. That HANDOFF is
       bannered SUPERSEDED and is an investigation record only — do not re-open it as work.
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

   **Rear S-300 hubs → 3-battalion regiments (2026-07-12, user feature-lock OVERRIDE).** The
   single-site LORAD hubs died to one HARM / one turn (a played turn-1 debrief showed the whole
   forward IADS — SA-6 STR, SA-2 Fan Song, SA-3 Low Blow, a P-14 EWR — gone in the opening sortie).
   Per the CLAUDE.md "SAM belts: strategic → regiment-by-authoring" STANDARD, the three **rear**
   S-300 hubs (**Sperenberg, Kastrup, Schönefeld**) are clustered into **3-battalion regiments +
   a shared EWR**: two extra `S-300PS 5P85C ln` LORAD markers per hub (cloned from the existing
   validated marker via pydcs, positioned on the segment between the hub's existing LORAD and MERAD
   spots so they stay on the already-cleared open ground; 0.9–2.7 km apart — dispersed enough to
   survive one strike, well inside the 15 nm comms range so range mode nets them), plus a `1L13 EWR`
   marker at Kastrup + Schönefeld (Sperenberg already had one). The front stays a mobile MERAD/
   SHORAD screen by design (the hard kill is the S-300 belt in depth). Faction-agnostic (markers,
   not hand-placed groups); added by `build_regiments.py` (pydcs clone-and-reposition — the miz
   round-trips losslessly, all 504 failures / economy statics / IADS cells preserved). Headless-
   verified through `Campaign.load_theater`: each hub CP resolves **3 `long_range_sams` + an EWR**.
   CI-locked in `tests/fourteenth/test_red_tide_sam_regiments.py`.

   **Single-radar battalions via a Red-Tide faction fork (§60 guardrail).** Redundancy comes from
   *three* fire units, not doubled radars, so §60's second track radar is reverted **for Red Tide's
   S-300/SA-5 only** — scoped so every other campaign's lone S-300 keeps its §60 redundancy. Because
   the enemy is the shared, player-selected `Russia 1980`, the scoping boundary is a **faction fork**
   `Russia 1980 (Red Tide)` (`resources/factions/russia_1980_red_tide.json`, set as
   `recommended_enemy_faction`) whose LORAD presets — SA-10/S-300PS, SA-5/S-200
   — point at **single-radar layout variants** (`S-300 Site (Single Radar)` / `SA-5 Legacy Site
   (Single Radar Circle|Semicircle)`: the same `.miz` templates, guidance slot `unit_count: 1`).
   **Battalions are lean fire units (2026-07-12 second pass, user catch from the generated save —
   "all long range sams still generated full sites"):** v1 only trimmed the *guidance* radar and left
   each battalion its whole acquisition suite (2 SRs + C2 on the S-300; Tin Shield + P-19 + its own
   P-14 + 8 LN on the SA-5), so a hub read as three stacked full sites. The single-radar variants now
   field what the realism note prescribes — acquisition serves the *regiment*, not each fire unit:
   the S-300 battalion is **1 search radar (Clam Shell/Tin Shield/Big Bird roll) + C2 + 1 TR + 4
   TELs** (DCS needs SR+CP+TR in-group or the site won't engage, so it can't go leaner), the SA-5
   battalion is **Tin Shield + Square Pair + 6 launchers** with the battalion-level P-19/P-14 slots
   deleted (the hub's shared EWR *is* the early warning; the full-suite base layouts are untouched
   for every other campaign). PD escorts (the #586 Tor slot) stay. Known behavior, not a bug: the
   loader fills each LORAD marker with a **random** faction LORAD preset (`random_group_for_task`),
   so a hub can mix S-300 and SA-5 battalions — a layered rather than pure-S-300 regiment. The
   fork carries **no aircraft/OOB change** and only takes effect if the player keeps the
   recommended faction (the New-Game default). (It is *not* byte-identical otherwise — the same
   fork also adds the **SA-15 Tor + SA-19 Tunguska** point defense and drops the HDS
   `SA-10A/S-300PT` leak; see the era-audit section below.) The **front + legacy screen
   keeps §60 doubling** (a lone SA-6/SA-2 MERAD site *should* have its anti-single-HARM second radar)
   — so the campaign now cleanly expresses both halves of the STANDARD: legacy→§60-doubled,
   strategic→single-radar regiment. Headless-verified: the fork's SA-10 (Single Radar) preset spawns
   an S-300 site with exactly one track radar, and the shared `S-300 Site` layout is unchanged
   (`[2]`). **In-game pass:** confirm the new battalion spots are open ground (not forest/water —
   pydcs can't surface-check GCW), that MANTIS nets the three single-radar battalions + EWR into one
   regiment that degrades gracefully instead of dying in one pass, and that the recommended fork
   faction is selected. NEW game required.

   **Mod-unit leak fixed (2026-07-12, user catch from the buy menu).** The fork originally shipped a
   *third* single-radar preset, `SA-10A/S-300PT (Single Radar)` — every unit in it a **High Digit
   SAMs** mod unit (S-300PT 5P85-1 LNs, 76N6E/64H6E-truck SRs, mast 30N6 TR). Red Tide is a
   vanilla-only campaign, and worse, the preset survived a no-mod game: `Faction.apply_mod_settings`
   strips mod presets by an **exact-name list**, and nobody added the new name, so the group showed
   in the buy menu (and sat in red's AI procurement pool — a purchase would have baked mod units
   into the generated `.miz`, which then fails to load for clients without the mod). Fixed
   three ways: the preset is removed from the fork faction (and its yaml deleted — S-300PS +
   SA-5 remain the regiment presets), `apply_mod_settings` gained a **provenance backstop** that
   strips any preset group carrying units from a disabled `pydcs_extensions` package regardless of
   name (also fixed three modern-Russia factions leaking the `[CH] Russian Navy` preset), and
   `Game.on_load` sweeps the pickled `ArmedForces` so **existing saves self-heal on load**.
   CI-locked in `tests/fourteenth/test_faction_mod_presets.py` (every shipped faction, all mods
   off ⇒ zero mod preset groups; the fork faction ⇒ pure-vanilla accessible roster).

   **Lock-override #2, same day — SA-15 Tor + SA-19 Tunguska added to the fork (user call).**
   The user's roster question ("Red Tide has no 15s or 19s — can SA-9/13/8 engage ARMs the same
   way?") exposed that the MANTIS SHORAD link (checklist G30) was a red no-op here: the fork's
   SHORAD roster was SA-8/SA-9/SA-13 only, and DCS tasks none of them against missiles (the IR
   seekers can't, and the Osa isn't given the capability) — so the "PD ambushes the HARM" mechanic
   had no red shooter. Both systems are era-correct for a first-line July-1988 force (Tor IOC 1986,
   Tunguska 1982 — the same army fielding S-300PS), so they were added to the fork's
   `air_defense_units` (base `Russia 1980` untouched). Gen-probed: the S-300 regiment battalions
   now draw Tor point defense (18 Tors on the generated map, 11 in PD groups); the S-300 Site
   layout's explicit `Tor 9A331` SHORAD2 slot finally fills. The full roster was audited against
   the campaign date in the same pass — **no other era violations** (newest units: BTR-80 '86,
   IL-78M '87). Guards: `tests/fourteenth/test_red_tide_faction_era.py` (era ceiling + the Tor
   presence). NEW game required.
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
12. **Red dedicated EWR coverage** (2026-06-28). Added **4 red `1L13 EWR` marker groups** to the
    red `["vehicle"]` block (`groupId`/`unitId` 409–412, past the mission max), each placed ~3 km
    NE of a long/medium red SAM site so they fall in red territory along the strategic belt.
    `MizCampaignLoader.ewrs` (marker type `AirDefence.x_1L13_EWR`) turns each into a dedicated
    `EwrGroundObject` at the nearest red CP. **Why:** under MANTIS the red SAM net was previously
    detection-blind until the ground-start A-50 climbed (no dedicated red EWRs at all — the whole
    campaign rode on one AWACS; see the in-game-pass G18 / G15 5th-pass notes). Paired with the
    `EWR 1L13` faction add above so the markers actually fill. **Edit method:** done via pydcs
    (`Mission.vehicle_group` + `save`) — a load→save round-trip was first verified to preserve all
    58 red vehicles, 12 red statics (incl. the advanced-IADS command-center/comms/power cells), and
    the blue side byte-for-count, so the usual hand-edit-Lua caution didn't apply here. Headless
    validated: loader now sees 4 red EWR markers; the IADS-detection scan flips Red Tide AMBER→OK.
    **EWR 1 relocation (2026-07-12, log-review catch):** `414th Red EWR 1` actually sat **28 km from
    blue Frankfurt** (200 km from the nearest red field — the "~3 km NE of a red SAM site" placement
    missed for this one). The campaign loader binds a marker to the nearest CP **coalition-blind**,
    so Frankfurt swallowed it, and since Blufor fields no EWR ForceGroup it errored
    (`Blufor Late Cold War (80s) has no ForceGroup for EWR` on every generation) and silently never
    spawned — the net ran 3-of-4 from day one. Relocated to the **Wittstock heath** (~3.5 km from the
    CP, ~1 km off the validated SCUD/SA-2 cluster), which also fills the northern-sector coverage
    hole (Hamburg/Wittstock/Templin/Peenemünde had no EWR). CI-locked: every `414th Red EWR *` marker
    must sit ≤25 km from a red anchor field (`test_red_ewr_net_markers_sit_in_red_territory`). The
    coalition-blind nearest-CP binding remains a generic loader foot-gun (sibling of the Red-Flag-81
    "blue SAM marker silently drops" note) — upstream-carve candidate. Unrelated but diagnosed from
    the same log: the `need United Nations Peacekeepers` squadron-matching spam is the **neutral
    civilian-traffic coalition** loading its (empty) squadron list — harmless DEBUG noise.

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
- `resources/factions/russia_1980.json` — added **`EWR 1L13`** to `air_defense_units` so the
  faction can field a **dedicated early-warning radar** (`EarlyWarningRadar` ForceGroup went
  `0 → 1`). Required because under MANTIS every SAM is held dark until cued, so the red net's
  detection rides on dedicated EWRs + the A-50; with `EWR-FG = 0` the red `.miz` EWR markers
  below could never have been filled (`generate_ewrs` would log "no ForceGroup for EWR"). 1L13
  "Box Spring" is era-appropriate for 1988 (`russia_1990` already uses it). Shared/additive —
  only enables the airframe; no other campaign places red EWR markers, so nothing else changes.
- `resources/factions/blufor_late_coldwar.json` — added `KC-135 Stratotanker MPRS` to
  `tankers` so the Frankfurt MPRS (drogue) squadron's def actually loads (the loader drops any
  def whose airframe isn't in the faction). Also shared, but additive — it only makes the
  airframe available.

### P-14 "Tall King" additions (2026-07-04)

Two coordinated changes so red fields the recently-added DCS **P-14 "Tall King"** radar
(`AirDefence.P14_SR`, unit class `EarlyWarningRadar`, `resources/units/ground_units/P14_SR.yaml`):

1. **Every S-200 / SA-5 site now carries a Tall King alongside its ST-68U "Tin Shield"**
   (real-world pairing: the P-14 fed the S-200 long-range EW while the ST-68U acquired). This is
   **game-wide, shared core content — NOT Red-Tide-local** (every faction/campaign with an S-200
   gets it) and is a clean **upstream candidate**. Mechanism, three files:
   - `resources/units/ground_units/P14_SR.yaml` — added a clean standalone `EWR P-14 Tall King`
     variant (the pre-existing `SAM SA-5 S-200 P-14 'Tall king' SR` variant was unreferenced).
   - `resources/groups/SA-5.yaml` — added `EWR P-14 Tall King` to the preset group's `units:`
     pool, so any faction fielding the `SA-5/S-200` preset gains `has_access_to_dcs_type(P14_SR)`.
   - `resources/layouts/anti_air/SA-5 Legacy Site (Circle).yaml` + `(Semicircle).yaml` — added an
     **`optional` `EW Radar` slot** (`unit_types: [P14_SR]`, `unit_count: [1]`). Optional so a
     faction lacking P-14 access degrades gracefully (the site stays valid — `usable_by_faction`
     only gates non-optional groups); with the pool addition above, all S-200 factions fill it.
   - Positions come from the two **shared template missions**
     `8_Launcher_Circle.miz` (8 layouts reference it) + `6_Launcher_Semicircle.miz`: each got a
     new `EW Radar` vehicle group (1× `P14_SR`) at the site periphery. Only the SA-5 layouts map
     the `EW Radar` group name, so the other layouts sharing the template **ignore** it
     (`group_for_name` → `KeyError` → skipped). **Editing gotcha:** pydcs `Mission.save` re-emitted
     the known **duplicate `theatre` zip member** — stripped afterward by rewriting each `.miz`
     keeping one copy of every member (both `theatre` entries were byte-identical `Caucasus`).
     Verify with `zipfile.namelist()` having no dupes.
2. **russia_1980 fields the P-14 as a standalone EWR.** Added `EWR P-14 Tall King` to
   `air_defense_units` (the *same* variant the SA-5 pool uses, so `accessible_units`' `set()`
   dedupes it). Shared with Crossing the Rubicon; era-correct for 1988.

### EWR net de-modded — P-37 Bar Lock removed (2026-07-04)

The HDS Ultimate Compilation PR (#382) had added `EWR P-37 Bar Lock` to `russia_1980` to close
the period red EWR gap — but the **P-37 Bar Lock is a High Digit SAMs *mod* unit** (its class
lives in `pydcs_extensions/highdigitsams/`), so it silently made the flown Red Tide campaign
depend on the HDS mod being installed by every client. Per the squadron (they fly with HDS
**disabled**), the Bar Lock was removed from `air_defense_units`, leaving a **fully vanilla EWR
net: 1L13 "Box Spring" + P-14 "Tall King"** (headless-verified: EWR-class accessible units =
`1L13 EWR`, `P14_SR`; **zero** HDS-typed units remain in the faction). The generic `Early-Warning
Radar` draw pool is now a balanced `1L13 / P-14` (~½ each). Shared change — Crossing the Rubicon
also loses the Bar Lock. The corresponding wiki/handbook + intel-assessment threat pages were
updated to the 1L13 + P-14 net and the S-200-hosts-a-Tall-King detail.

**Headless-verified (real new-game pipeline, `red_tide.yaml`):** both S-200 sites spawn a Tin
Shield **and** a Tall King; standalone red EWR sites roll a P-14; the faction carries no HDS
units; black + mypy + full pytest green.

### Blue roster slimmed — F-4E wing + heavy/orphan AI squadrons cut (2026-07-05)

Per the user ("too much AI, not enough 414th" + the airframe mix), **six blue squadrons were
removed** from `red_tide.yaml` (yaml-only; no `.miz` change, no squadron-def deletions):

- **480th TFS** (F-4E, SEAD Sweep, Ramstein ×6), **512th TFS** (F-4E, OCA/Runway, Hahn ×8),
  **526th TFS** (F-4E, BAI, Spangdahlem ×8) — the whole USAFE Phantom wing. **GAF JG 74
  stays as the single German AI squadron** (TARCAP, Spangdahlem ×8).
- **VA-34** (A-6E, OCA/Aircraft, Ramstein ×6) — the last carrier orphan.
- **JBG 31 Boelcke** (Tornado IDS, SEAD Escort, Hahn ×8).
- **37th BS** (B-1B, OCA/Runway, Ramstein ×4) — SIOP-only in 1988; the B-52H (20th BS)
  stays as the lone heavy.

Kept AI: Mirage F1EE (Ala 14 ×6, Escort), F-15C (493rd ×6, TARCAP), B-52H ×4, GAF JG 74 ×8,
tankers/E-3A/lift. The player core (F-16CM/F-A-18C/F-15E ×12, F-14B ×8, A-10C ×8 + helos) is
untouched. Offensive fixed-wing tasking now concentrates on the human's 414th jets; the
remaining AI fast jets are all in supporting roles (TARCAP/Escort) except the B-52H.
Side effects: the description's Heatblur-F-4E note + "Phantoms" line reworded; the
`settings:` comment airframe list updated; wiki briefing/role-cards/first-three-turns +
`docs/campaigns/` mirrors re-synced (F-4E role card deleted, OCA recipes re-pointed at
F-15E/B-52H, tanker pairing lists trimmed). The squadron defs (`414th 480th TFS.yaml` etc.)
are kept on disk — they're generic resources, just no longer referenced by this campaign.
The upstream carve payload (`docs/dev/upstreaming/red-tide/`) is stale until
`build_payload.py` is re-run. NEW game required to see the slimmed roster.

### Frontline artillery harassment preseeded (2026-07-05)

`red_tide.yaml` now preseeds **`artillery_base_harassment: true`** — the generic mode of the
§36 airbase-harassment runtime (features doc §36, "generic artillery mode"): fields within
tube/rocket reach (`ARTILLERY_FRONT_REACH_M` ≈ 35 km) of a front draw sporadic in-mission
standoff harassment fire. On this laydown that is the **Fulda forward FARP** (~2.5 km off the
Fulda↔Haina front) and red's **Haina** spearhead — the Gap is not a safe ramp — while the
Rhineland cluster (100+ km back) stays silent. Player-spawn fields are never targeted
(emitter-filtered + Lua double-guard) and a 5-min startup grace protects a cold start. A
*recommended new-game default* like the other `settings:` entries; NEW game (or flipping the
setting in an existing save) required. In-game pass: checklist L8's artillery bullet.

**Plugin dependency (user-caught 2026-07-05, same day):** the runtime lives in the
**vietnamops plugin** — a player whose saved defaults had unticked "Vietnam Ops (period
mechanics)" (reasonable on this squadron) would silently lose the feature: the emitter emits,
nothing consumes. `red_tide.yaml` therefore also preseeds **`plugins: {vietnamops: true}`**
(campaign plugin choices layer over the player's saved defaults in the New Game wizard —
still uncheckable there). The plugin is renamed "Vietnam Ops **& standoff harassment**" and
both toggle descriptions state the coupling. Guard:
`tests/fourteenth/test_campaign_plugin_preseed.py`. An **existing** Red Tide save needs both
the setting AND the plugin flipped on by hand.

**Reach bumped 35 → 42 km (2026-07-10, flown-test finding).** The 2026-07-10 turn-1 fly
(session `gallant-panini-5485e7`) found the miz emitted **`VietnamOps = {}`** — nothing shelled
— because the ~2.5 km "off the front" figure above is the *route-anchor* distance, not the
distance to the **FLOT**: at turn 0 the front sits at the route midpoint, so Fulda is **~39.3 km**
and Haina **~39.6 km** from the line, both ~4 km past the old 35 km reach. The reach is now a
campaign-tunable setting **`artillery_harassment_reach_km`** (default 35; `enabled_when=
artillery_base_harassment`), and `red_tide.yaml` preseeds **42 km** so both fields fall inside
from turn 1 (WP BM-27 Uragan MRLs reach ~35 km, so ~42 km is period-honest). Guard:
`test_artillery_reach_is_campaign_tunable`; in-game re-fly = checklist L8's artillery bullet.

### Fewer red bomber *missions* — the `secondary: any` confinement (2026-07-10)

Flown-test tuning (same session): the user wanted red to keep flying *some* offensive but was
hand-deleting a couple of strategic-bomber flights before each mission — and, when asked,
specifically **did not want the bomber fleet trimmed off the ramp** (the big parked Soviet bomber
force is immersion), only **fewer bomber missions flown**. So this is a *tasking* change, not a
`size` change: every bomber `size` stays 8 (24 heavy bombers still parked).

The driver was **`secondary: any`** on the three heavy-bomber squadrons (Sperenberg Tu-95MS `Strike`,
Sperenberg Tu-22M3 `OCA/Runway`, Kastrup Tu-22M3 `Anti-ship`). `SquadronConfig.auto_assignable` is
`{primary} | set(secondary) | {TARPS}`, so `secondary: any` made each bomber auto-assignable for
**all 26 capable mission types** — including **STRIKE-as-secondary and BARCAP** (that is why the
flown OOB showed 16 Tu-22M3s parked as "Kastrup/Sperenberg BARCAP" filler and extra Backfire strikes
the player was skimming). Dropping the `secondary: any` line confines each bomber to **just its own
primary + TARPS** (2 types): the Tu-22M3s are no longer STRIKE- or BARCAP-eligible and fall back to
their own **target-gated** primaries — OCA/Runway (gated by `oca_target_autoplanner_min_aircraft_count:
40`) and Anti-ship (few reachable blue ships) — so they rarely auto-frag. The **Tu-95MS keeps
`primary: Strike`**, so red still flies the occasional prestige Bear raid (the GRYPHON strike the
user said "didn't feel bad"); it just stops being BARCAP filler too. Net: same airframes on the
ramp, markedly fewer AI bomber sorties, tactical **Su-25 BAI / Su-24 SEAD / CAS** offensive
untouched. Verified headless (auto-assignable set 26 → 2 types, STRIKE/BARCAP dropped for the
Tu-22M3s). Reversible; NEW game required; a fly should confirm the bomber-package count actually
drops (and that red still flies its one Bear strike + its tactical offensive).

### Feature-audit adds — C2 decapitation + the SCUD hunt (2026-07-07)

A feature audit against the full §1–§52 catalog found Red Tide covered on the default-ON
battlefield-life set (§3 concealment, §15 hidden CPs, §21 Combat SAR, §40 phases, §46 fuel,
§47 clock, §50 convoys/ambush) and the three preseeded standoff features (§36/§50/§51), but
missing two things the laydown was practically built for. Both were added (yaml + one `.miz`
edit); guard `tests/fourteenth/test_campaign_plugin_preseed.py`.

1. **§52 command-center decapitation — `c2_decapitation_effects: true` (default OFF).** Red
   Tide is one of the very few campaigns with a real, per-base, **destroyable command-center
   network** — the advanced-IADS build stood up **9 red Command Center cells** (the scenery
   real-building nodes at Wittstock/Templin/Hamburg/Peenemünde/Schönefeld/Kastrup/Sperenberg/
   Haina, headless-confirmed via `preset_locations.scenery` category `commandcenter`; Fulda
   carries the blue pair). §52 keys off exactly those `category == "commandcenter"` TGOs and
   scales red's §17 planner unpredictability up in proportion to the dead fraction, so bombing
   Hanoi's — er, the GSFG's — HQs makes red *plan* worse, not just lose SAM autonomy. Pure
   turn-model, no plugin, no `.miz` change; the campaign premise ("break him before he can
   consolidate") made mechanical. Reactive defense is untouched (the §17 boundary). A SITREP
   band line reports "N/M command posts operational (claimed)".

2. **§49 mobile-missile relocation — two SS-1C Scud-B batteries added to the `.miz`.**
   `mobile_missile_relocation` is default ON but had **nothing to relocate** — the laydown
   placed no missile-category TGO, so the SCUD hunt was inert. Added **two red `Scud_B`
   vehicle markers** to the CJTF Red country block (a forward battery off **Haina**, a
   rear/mid one near **Wittstock**), so `MizCampaignLoader.missile_sites` builds two
   `MissileSiteGroundObject`s (`category == "missile"`). With §49 on they shoot-and-scoot
   within the 4 km scoot radius each ~8 min, and with `concealed_enemy_forces` (default ON)
   they surface only as a dashed "suspected activity" circle until a recon bird finds them —
   the launcher is never quite where the last photo froze it. `mobile_missile_relocation:
   true` and the **`mobilemissiles` plugin** are both preseeded (same saved-default-off
   reasoning as the vietnamops/convoyambush/commsjam plugins).

   **`.miz` edit method / verification.** pydcs `m.vehicle_group(red, …, MissilesSS.Scud_B,
   …)` for both markers (auto-assigned `groupId` 413/414, `unitId` 813/814, past the mission
   max 412/812), then `Mission.save`, then a **theatre-member dedup** on the resulting zip
   (this `.miz` already ships a duplicate `theatre` member and pydcs save adds a third — keep
   one). Headless-verified through the **real loader**: the only preset-location delta is
   `missile_sites 0 → 2` (anchored to Haina + Wittstock, both red), every other preset total
   (armor 27, medium SAM 16, scenery 71 incl. the 9 command centers, ships 3, EWR 4, factory
   2) **byte-for-count identical**, the **`warehouses` member byte-identical** (Kastrup red /
   Fulda blue / Hamburg red base ownership intact), and the blue side untouched (27 veh / 2
   static). Placements co-locate near the design-validated red SAM markers (open farmland,
   real standoff), so terrain confidence is inherited; the SCUD spots are still an in-game-pass
   watch item (checklist S2 / B6) like every blind GermanyCW placement. NEW game required.

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
  UH-60A is intentionally left out. The Heatblur F-4E module note was dropped from the
  description with the 2026-07-05 roster slim (the only F-4Es left are the AI JG 74).

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

## Strikeable motorpool depot (§56, 2026-07-08)

Red Tide is the first fork campaign to author a **motorpool depot** (feature §56, adopted from
upstream PR dcs-retribution#859). A single `Fortification.Garage_A` static sits ~4 km NE of **Haina**
(the forward Soviet base at the Fulda Gap) in the RED country's `static_group`. The §56 loader
(`MizCampaignLoader.motorpools` → `PresetLocations.motorpools` → `start_generator.generate_motorpools`)
turns it into a `MotorpoolGroundObject` bound to Haina, projecting Haina's not-yet-deployed armor
**reserve** (`base.armor` − front deployment) as strikeable parked vehicles — "bomb the motor pool
before its armor reaches the front."

- **Added via pydcs** (`m.static_group(country=red, _type=Fortification.Garage_A, position=Haina+3km)`),
  not a text-edit: red_tide.miz is all-vanilla units, so pydcs round-trips it losslessly (108→108
  groups, verified) — the "pydcs save breaks the miz" caveat only bit the earlier mod-unit era.
- **Empty at turn 0:** `base.armor` is the coalition's *purchase* stock (zero at game start), so the
  depot renders immediately but its parked tanks only appear once red has procured armor a couple of
  turns in. This is the feature's designed "empty depot resting state" (`sidc_status` pinned PRESENT),
  not a bug.
- **Headless-verified** through the real `GameGenerator` pipeline: the static binds to Haina (RED) and
  materialises exactly one `MotorpoolGroundObject`; CP count unchanged (17). CI-locked in
  `tests/fourteenth/test_red_tide_motorpool.py`. In-game pass = checklist B8.
- **NEW game required** (the depot is read from the miz at theater load / injected by the migrator on
  old saves).

## M1 flown-session tuning batch (2026-07-12 — tuning-to-intended, inside the lock)

The 2026-07-11 squadron M1 ("Red Tide M1 with Mags happy", ~125 min MP) Tacview deep-dive
produced three tuning findings, preseeded into the campaign yaml (NEW game required; on the
live save set the same values by hand in Settings):

- **`civilian_air_traffic` — preseed REVERSED same-day (squadron call 2026-07-12): Red Tide
  KEEPS its civilians.** #580 briefly preseeded the new generic gate OFF (a neutral IL-76 at
  FL230 transited the deep BVR corridor and died to a player's double Phoenix — the civ
  layer's ~40 NM front keep-out is no protection on a campaign whose air war runs 100+ NM
  behind the lines), but the user kept civ air ON for the live TURN 2 save and then for the
  campaign: the ambient life is worth the occasional Aeroflot incident, and BVR target
  discrimination past the FLOT is on the shooter. The campaign now carries NO
  `civilian_air_traffic` preseed (generic default ON applies); guard
  `test_red_tide_keeps_civilian_air_traffic`. The gate itself remains available for any
  campaign that wants a sterile picture.
- **`aewc/tanker_threat_buffer_min_distance: 30/25`** (defaults 80/70): the AI support-orbit
  depth push (2.5× the buffer) parked the red A-50/IL-78 200/175 NM back over Berlin all
  mission — too far to cue low targets at Fulda, which made the P-14 line red's entire
  detection net and its death so decisive. 30 NM puts the A-50 ~75 NM behind the FLOT
  (Halle/Leipzig), covering the whole Fulda corridor, still threat-zone-floored.
- **`desired_barcap_mission_duration: 45`** (default 60 min): a Schonefeld BARCAP MiG-29
  flamed out dry at ~75 min airborne with no combat — the on-station racetrack is the one
  real-fuel-burn window under AI unlimited fuel, and 60 min at the AI's patrol speed is a
  whole Fulcrum+centerline-tank load. Wave count unchanged at the default mission length.

Guards: `test_red_tide_preseeds_the_m1_tuning_batch` +
`test_barcap_duration_preseed_deserializes_to_a_timedelta` in
`tests/fourteenth/test_campaign_plugin_preseed.py`. The full M1 debrief lives in the local
`missions/red-tide/` folder (m1-debrief-2026-07-11.md).
