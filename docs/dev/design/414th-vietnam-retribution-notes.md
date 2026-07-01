# 414th — "Vietnam Retribution" mode — design notes

**Status:** **P0 + P1 (doctrine model) + P1b (display read-path) + P1c (period planner numbers) landed**;
P2 (shell/preset) + P3 (behaviour taskings) outstanding.
**Decided direction:**
- Tasking redesign = **doctrine-gated + rename** (one `FlightType` enum, no new enum values).
- New-game entry = **dedicated shell over the shared engine** (a Vietnam card on the New Game
  screen that pre-seeds a profile + filters lists; reuses the existing metadata-driven wizard).
- This is **fork identity** (like the Iran pack / Red Tide) — **not upstreamable**.

> **Relationship to the Vietnam Ops suite** ([`414th-vietnam-ops-notes.md`](414th-vietnam-ops-notes.md)):
> the suite's runtime mechanics (§32 Arc Light, §33 AAA flak gauntlet, §34 naval gunfire) **are**
> this design's "Layer-3 flavor / P4" content, already built. This note is the *framing* layer
> (doctrine profile + content filter + shell) those mechanics live inside.

---

## Implementation progress

- **P0 — content tags — DONE.** The 3 Vietnam campaigns (`khe_sanh_niagara`, `1968_Yankee_Station`,
  `operation_velvet_thunder`) carry `era: vietnam`; `Campaign.era` reads it
  (`game/campaignloader/campaign.py`). Guard: `tests/test_vietnam_content.py::test_vietnam_campaigns_tagged_era_vietnam`.
- **P1 — doctrine model — DONE.** `VIETNAM_DOCTRINE` (`game/data/doctrine.py`) is a COLDWAR clone
  + a `task_display_names` rename map (MiGCAP / Iron Hand / Alpha Strike / Sandy / College Eye /
  Interdiction / Photo Recon / …) and an (open, `None`) `tasking_whitelist`. Two additive frozen-
  dataclass fields with defaults (so MODERN/COLDWAR/WWII are untouched) + `display_name_for()` /
  `allows()` helpers; `from_settings` carries them. Faction loader maps `"vietnam"`; the **10**
  Vietnam factions are repointed from `coldwar`. Tests: `tests/test_vietnam_doctrine.py`,
  `tests/test_vietnam_content.py::test_vietnam_factions_load_vietnam_doctrine`.
  - **P1c — period-authentic planner *numbers* (2026-07-01).** The doctrine is no longer a *pure*
    COLDWAR clone: on top of the display/whitelist/P3 layers it now overrides the planner values that
    make the era play differently, not just read differently — **A2A engagement ranges** shortened to
    the early-missile/gun era (`cap_engagement_range` 35→22 NM, `escort_engagement_range` 20→10 NM, so
    MiGCAP/escort fight close instead of BVR standoff), **`rtb_speed`** 450→400 kt (subsonic period
    cruise), and a **period ground OOB** (`VIETNAM_GROUND_PROCUREMENT`: infantry-dominant + artillery +
    mobile-AAA/SHORAD, light armour, and **no ATGM/IFV** — the ATGM-decisive war was Yom Kippur, not
    Vietnam). The rebadge-equality test now resets these four fields too (so it still proves nothing
    *else* drifted), plus dedicated tests lock the shorter ranges / subsonic RTB / infantry-heavy,
    ATGM-free ground ratio.
  - **Borderline repoints to confirm:** `usa_1965.json` / `usa_1970.json` are *generic* 1965/1970
    US factions (not Vietnam-War-named). They're Vietnam-*era*, so the renames fit, but they could
    be used in other Cold-War-SEA scenarios. Repointed per the design's faction list; flag if undesired.
- **P1b — display read-path — DONE.** The renames now **surface**. `Flight.task_display_name` +
  `FlightData.task_display_name` (→ `coalition.doctrine.display_name_for(flight_type)`) are the
  accessors; routed through the **kneeboard** (7 label sites + `_brief_mission` now takes the label;
  logic comparisons untouched) and the **qt_ui** flight/task surfaces: the **manual flight task picker**
  (`QFlightTypeComboBox`, doctrine passed from `QFlightCreator`; item *data* stays the `FlightType`),
  the **squadron primary-task picker** (`PrimaryTaskSelector`), the flight-creation summary, the
  flight list (`AirWingDialog`), flight task label (`QFlightTypeTaskInfo`), plan label
  (`QFlightWaypointTab`), the squadron auto-assign rows/checkboxes (`AirWingConfigurationDialog`,
  `SquadronDialog`), and the squadron-selector tooltip. Tests:
  `tests/test_vietnam_doctrine.py` (the two properties), `tests/missiongenerator/test_brief_sheet.py`
  (the `_brief_mission` label). **Deferred (graceful canonical fallback):** the "Add new Squadron" task
  picker only — a not-yet-attached new squadron has no coalition, so `PrimaryTaskSelector` is built with no
  doctrine and falls back to `FlightType.value` (`primarytaskselector.py`). (The old note also listed a
  `SeadTaskPage` header — no such class exists; dropped.)
- **P1b follow-up — package/flight planning labels — DONE.** The earlier-deferred *planning table* labels
  now rename too (the user saw the old labels in the ATO/package list under Vietnam). `Package` exposes no
  coalition, but every flight in a package shares one, so `Package.package_description` reads the doctrine
  off `self.flights[0].coalition` (renames the primary task; keeps the combined "OCA Strike" tag for
  un-renamed doctrines). `Flight.__str__` (the per-flight rows in the ATO/package lists, `[task] N x type`)
  now uses `task_display_name` with a `try/except` fallback so `__str__` can never raise on a partially
  restored flight. The **map** flight label is covered too: `game/server/flights/models.py` serializes
  `flight_type=flight.task_display_name` (the client uses it display-only — `FlightPlan.tsx`). All three are
  byte-identical to canonical under every non-Vietnam doctrine (`str(FlightType)==.value`). Headless: real
  Vietnam packages read **College Eye / MiGCAP / Interdiction / Alpha Strike**. Test:
  `test_vietnam_doctrine.py::test_package_description_uses_doctrine_rename`. The package *editor* dialog's
  "Primary task:" summary (`QPackageDialog`) was the last of these and now renames too via the same
  `flights[0].coalition.doctrine` read.
- **P2 (era pre-seed) — DONE.** The 3 Vietnam campaigns' `settings:` blocks turn the Vietnam Ops
  mechanics + `restrict_weapons_by_date` on (per-campaign: Khe Sanh/Velvet Thunder inland → no naval
  gunfire; Yankee Station coastal → naval gunfire on). Applied on campaign-select via the existing
  `QNewGameSettings._load_campaign_settings`. Test: `tests/test_vietnam_content.py::test_vietnam_campaign_era_preseed_applies`.
- **P2 (New-Game "Vietnam" card) — DONE.** A third radio in the Intro page's "Campaign type" group
  (`IntroPage`, alongside "included" + blank-canvas), registering a `vietnamMode` field. When set,
  `TheaterConfiguration.initializePage` filters the campaign list to `era: vietnam` via the new
  `Campaign.matches_era(era)` predicate threaded through `QCampaignList.setup_content(..., era=...)`
  (and the "show incompatible" toggle now re-applies the active `_era_filter`). `accept()` is **unchanged**
  — a Vietnam card game is a normal included-campaign game; the card *only* filters the list, and the
  settings/faction pre-seed already rides on per-campaign select (P2 era pre-seed above). Mirrors the proven
  blank-canvas field+initializePage pattern. The filter predicate is game-side + unit-tested
  (`test_vietnam_content.py::test_matches_era_drives_the_vietnam_card_filter`); the radio/field wiring is
  qt_ui (not in CI mypy) and needs an **in-app pass** (checklist L5): the visual render + the
  vietnamMode→filter path can't be exercised headless (the campaign-list item build needs the DCS install dir).
  The same pre-seed blocks also pin a tighter **AEW&C/tanker standoff** (`aewc_threat_buffer_min_distance: 25`
  / `tanker_threat_buffer_min_distance: 20`, vs the 80/70 NM defaults) so support orbits hug the compressed
  Vietnam fronts instead of sprawling to the map edge — diagnosed from a "support flies round the north edge"
  playtest (the cause was the support standoff, **not** threat routing; a SAM wall would worsen it). Per-campaign
  so large maps keep the wide defaults; PR #314, guard `tests/test_vietnam_content.py::test_vietnam_campaign_tightens_support_orbits`.
- **P3 (behaviour) — strike-deadlock fix DONE (the urgent one).** Root-caused 2026-06-28 from a live
  Khe Sanh save reporting "no BAI/Strike": **0/28 strike + 0/13 BAI targets were plannable** because
  retribution refuses to strike a target still covered by an air defense (`target_area_preconditions_met`),
  and Vietnam has no reliable SEAD to clear it (66 DEAD attempts, all scrubbed) → total deadlock of a
  15-squadron / 77-target offensive fleet. **Not** a fork regression: the gate, the escort logic, and the
  offensive task tree are all upstream-identical (the fork only *added* the beneficial CAS-decoupling), so
  upstream deadlocks here too — it's a retribution-vs-no-SEAD-era mismatch. Fix = two additive `Doctrine`
  flags (default False; VIETNAM True): `strike_through_air_defense_threat` (plan Strike/BAI into threatened
  areas; threats still recorded for DEAD targeting — `game/commander/tasks/packageplanningtask.py`) +
  `plan_strikes_without_full_escort` (a missing A2A/SEAD escort prunes instead of scrubbing the package —
  `game/commander/packagefulfiller.py`). Headless-verified on the reported save: BLUE **7 → 19 packages**,
  now planning CAS/BAI/Strike/Armed-Recon. **Existing saves don't benefit** (the old doctrine is pickled
  flags-off) — needs a NEW game.
- **P3 (behaviour) — tasking whitelist DONE.** The `tasking_whitelist`/`Doctrine.allows()` mechanism
  (built unused in P1) is now wired at the planner edge. `VIETNAM_DOCTRINE` drops
  **SEAD + SEAD_ESCORT + SEAD_SWEEP + DEAD + ANTISHIP** (`VIETNAM_DROPPED_TASKINGS`; the allowed set is
  the whole enum minus those, so new FlightTypes fail-open). The gate lives in
  `PackagePlanningTask.fulfill_mission`: the package primary is always proposed first, so a disallowed
  primary (DEAD/ANTISHIP) scrubs the whole mission, while a disallowed *escort* (the SEAD trio) is just
  dropped and the package flies on (pairs with `plan_strikes_without_full_escort`). Motivated by a playtest
  "A-1 on SEAD Sweep" — a squadron's auto-assignable tasks are `aircraft caps − secondary` (`squadrondef.py`),
  and the A-1H's DCS task list includes SEAD, so the planner's SEAD-escort proposals grabbed it. Headless on
  the live save: SEAD/DEAD/anti-ship **13 → 0**, and freeing those airframes *raised* offensive output
  (STRIKE 1→5, BAI 6→13, packages 19→31). Drops all SEAD per the "no reliable SEAD" premise (no current
  Vietnam campaign fields a Wild Weasel); revisit per-faction if one ever does. Tests:
  `test_vietnam_doctrine.py::test_vietnam_whitelist_drops_sead_dead_antiship` + the `fulfill_mission` scrub
  in `test_dead_planning.py::test_vietnam_doctrine_scrubs_the_whole_dead_package`.
- **P3 (behaviour) — Alpha Strike: single section + forced escort (UPDATED per playtest).**
  `Doctrine.strike_flight_count` (default 1) can fan N coordinated, shared-TOT STRIKE sections onto one
  target in `PlanStrike.propose_flights`. Vietnam first fanned **2** sections (concentration, not more
  aircraft — headless: same 10 strike a/c, 5 single→3 double targets). **Playtest feedback retired that:**
  the doubled bomber sections flew **unescorted**, so Vietnam now flies a **single section + a forced fighter
  escort** (`strike_flight_count=1` + the new `always_escort_strikes`). The flag forces the A2A escort
  "needed" in `PackageFulfiller.check_needed_escorts` for STRIKE-led packages even when no air threat is
  detected on the route (still pruned by `can_plan_escort` + `plan_strikes_without_full_escort` when no
  fighter is free). **Gotcha:** the strike target is *enemy*-owned, so `PlanStrike` reads the *planner's*
  doctrine via `self.target.coalition.opponent.doctrine`. Both flags are save-safe (`= 1` / `= False`)
  defaults. Tests: `test_strike_planning.py` (single section + `test_always_escort_strikes_forces_a2a_escort`)
  + `test_vietnam_doctrine.py::test_vietnam_strike_is_single_section_and_force_escorted`. **Known limit:**
  the forced flag only guarantees the escort is *planned when a fighter is free* — it does not reserve a
  fighter ahead of BARCAP (HTN step #2 vs strikes at #8), so a fighter-starved campaign can still fly the
  strike naked; reserving fighters for strike escorts is a deeper, deferred lever. **Still TODO in P3:**
  Iron Hand = Shrike-vs-live-emitter (**moot** now SEAD is dropped from Vietnam — revisit only if a
  weasel-fielding Vietnam campaign appears).
- **P4** — see §9.

---

## 1. The idea

Vietnam shouldn't be "pick a 1970 faction inside the modern flow and hope the planner behaves."
It should be its own front door — a **"only the stuff that matters to Vietnam" mode** — where the
campaign/faction/theater lists are pre-filtered to Vietnam content, the difficulty/era knobs are
pre-seeded, and the auto-planner produces **era-correct taskings with era-correct names** (MiGCAP,
Iron Hand, Alpha Strike, Sandy/Jolly Green) instead of modern doctrine (HARM DEAD, PGM precision
strike, anti-ship packages).

The key architectural insight: **one engine underneath.** The "mode" is three thin layers over
machinery that already exists.

## 2. What already exists (verified 2026-06-28)

- **Factions:** `USA 1970/1971 Vietnam War`, `USSR 1971 Vietnam War`, `usa_1965/1970`,
  `vietnam_1965/1970`, `nva_1970`, `vietcong_1965/1970` — all now `doctrine: vietnam` (P1).
- **Campaigns:** `1968_Yankee_Station`, `khe_sanh_niagara`, `operation_velvet_thunder` (now
  `era: vietnam`). All on Caucasus/Marianas overlays; **no native DCS Vietnam map**.
- **~18 era mod packs** in `pydcs_extensions/` (a4ec, a6a, a7e, f4, f100/104/105/106, f9f, f111c,
  mirage3, ea6b, su15, oh6*, ov10a, vietnamwarvessels, coldwarassets).
- **Era gating functional:** `start_date` any year; `Weapon.available_on` + `restrict_weapons_by_date`
  + `weapons_introduction_year_overrides`; date-gated aircraft properties (§24).
- **Doctrine** (`game/data/doctrine.py`): frozen `Doctrine` with capability flags + planning
  geometry; MODERN/COLDWAR/WWII/**VIETNAM** in `ALL_DOCTRINES`; faction load/serialize via the
  `"doctrine"` string.

## 3. Architecture — three layers over one engine

```
LAYER 1  Shell         "Vietnam" card on New Game; pre-seeds profile + filters lists   (qt_ui)
LAYER 2  Content filter Vietnam campaigns/factions/maps shown; rest hidden             (qt_ui + tag)
LAYER 3  Doctrine       which taskings the planner produces + display names + sizing    (game/data) ← substance
            ▼ everything below is the existing, unchanged engine ▼
     commander/tasks · flightplan · aircraftgenerator · Lua plugins (incl. the Vietnam Ops suite)
```

The whole "mode" is: **select a doctrine profile + an era preset, filter the pickers, brand the
front door.** No parallel wizard, no planner fork.

## 4. Layer 3 — doctrine-gated taskings (the substance)

`VIETNAM_DOCTRINE` in `game/data/doctrine.py`, registered in `ALL_DOCTRINES`, `"vietnam"` in the
faction loader; Vietnam factions repointed. The frozen `Doctrine` gained two additive fields
(defaults, so the other three instances are untouched):

1. **A tasking whitelist** (`tasking_whitelist`) — the `FlightType`s the auto-planner may produce.
   `None` = no restriction. Used to drop `DEAD`/`ANTISHIP` (P3).
2. **A display-name override map** (`task_display_names`) — `{BARCAP: "MiGCAP"}` etc. **Does NOT
   touch the persisted enum value**, so saves stay compatible; UI/kneeboard read the override, else
   fall back to `FlightType.value`.
3. **Composition tweaks** (P3) — Alpha Strike sizing, Iron Hand = Shrike-vs-live-emitter.

**Gating bites** at the planner task edge (`game/commander/tasks/`): a disallowed task simply never
gets proposed. (P1 keeps the whitelist `None`; the gate + drop is P3.)

### The tasking map (modern → Vietnam) — implemented renames marked ✓

| Modern `FlightType` | Vietnam display | Status |
|---|---|---|
| `BARCAP` | **MiGCAP** | ✓ rename |
| `INTERCEPTION` | **GCI Intercept** | ✓ rename |
| `SEAD` / `SEAD_ESCORT` / `SEAD_SWEEP` | **Iron Hand / Iron Hand Escort / Weasel Sweep** | ✓ rename (Shrike-vs-emitter = P3) |
| `STRIKE` | **Alpha Strike** | ✓ rename (bigger sizing = P3) |
| `BAI` | **Interdiction** | ✓ rename |
| `OCA_RUNWAY` / `OCA_AIRCRAFT` | **Airfield Strike** | ✓ rename |
| `TARPS` | **Photo Recon** | ✓ rename |
| `SCAR` | **Sandy** | ✓ rename (already RESCAP §15) |
| `JAMMING` | **Standoff Jamming** | ✓ rename (C-130 EW §2) |
| `AEWC` | **College Eye** | ✓ rename |
| `TRANSPORT` | **Airlift** | ✓ rename |
| `TARCAP`/`ESCORT`/`CAS`/`SWEEP`/`ARMED_RECON`/`COMBAT_SAR`/`CSAR`/`SOF`/`REFUELING`/`RECOVERY`/`AIR_ASSAULT` | (canonical) | allow, no rename |
| `DEAD` | — | **drop** (no HARM) — P3 |
| `ANTISHIP` | — | **drop** (no fleet) — P3 |
| — | **Arc Light** (B-52 cell) | ✅ built (Ops suite §32) |

Honest split: **~70% whitelist + display-name override** (cheap, no behaviour change); **~30% real
behaviour** — Alpha Strike sizing, Iron Hand semantics, FAC(A). Start with the cheap 70%.

## 5. Layer 2 — content filter

Tag Vietnam **campaigns** (`era: vietnam`, done) and **factions** (`doctrine == "vietnam"`, done).
The shell's pickers filter to the tagged set; outside the shell nothing changes. Maps: offer the
maps the Vietnam campaigns use (Caucasus/Marianas today); a future native Indochina map drops in as
just another allowed theater.

## 6. Layer 1 — the shell

A **"Vietnam" card** on the New Game screen launching the existing `QNewGameWizard` with: the content
filter active, a **Vietnam era preset** applied (mirror `difficultypreset.py`:
`restrict_weapons_by_date=True`, era labels/realism, mod toggles `vietnamwarvessels`/`coldwarassets`/
`ov10a` on, modern-only off), and the doctrine implied by the chosen faction. A new entry point + a
preset + list filtering — **not** a second wizard.

## 7. Save-compat & constraints

- **Never rename `FlightType` enum values** — renames are a doctrine **display layer**; a true retire
  goes through `_LEGACY_FLIGHT_TYPE_VALUES` (`game/ato/flighttype.py`).
- `Doctrine` is `@dataclass(frozen=True)` — new fields have **defaults** (done); `from_settings`
  carries them (done).
- A campaign-mode/era flag stored on the game needs a `__setstate__` default. (`Campaign.era` has a
  default and `Campaign` is constructed fresh per new game, so no save migration is needed for it.)
- Reuse the `coldwarassets` mod gate (`faction.py`) for the era preset.

## 8. Open questions

1. **Manual tasking under Vietnam doctrine** — filter the in-UI "create flight" list to the whitelist,
   or stay full? (Lean: filter, with a "show all" escape hatch — decide at P2.)
2. **`VIETNAM_DOCTRINE` vs extending `COLDWAR`** — **DECIDED: distinct instance** (done).
3. **Display-override home** — **DECIDED: on `Doctrine`** (done); promote to `EraProfile` only if a
   second mode needs it.
4. **Alpha Strike sizing** — concrete package size/escort ratios; needs an SME pass (P3).
5. **Iron Hand semantics** — exact "Shrike vs live emitter" rule; reuse the SEAD planner with a flag (P3).
6. **FAC(A)** — v2. (**Arc Light is already done** via the Ops suite.)

## 9. Phased plan

- **P0 — content tags + verification.** ✅ DONE.
- **P1 — doctrine model.** ✅ DONE (model + faction repoint + tests). **P1b — display read-path** ✅ DONE
  (kneeboard + manual task picker + flight/squadron UI labels route through `*.task_display_name` /
  the picker doctrine).
- **P2 — era preset + shell.** Mirror `difficultypreset.py`; New Game "Vietnam" card + list filtering.
- **P3 — behaviour taskings.** Alpha Strike sizing; Iron Hand = Shrike-vs-emitter; set the Vietnam
  whitelist (drop DEAD/ANTISHIP) + gate the planner edge + verify clean degradation (in-game-pass row).
- **P4 — flavor.** Arc Light ✅ (Ops §32), flak ✅ (§33), naval gunfire ✅ (§34); FAC(A) + branding TODO.

Each phase is independently shippable + CI-gated. Runtime tasking-behaviour changes (P3+) get an
in-game-pass checklist row.

## 10. Integration-point index (verified paths)

| Concern | Path |
|---|---|
| Doctrine dataclass + instances | `game/data/doctrine.py` (`Doctrine`, `*_DOCTRINE`, `ALL_DOCTRINES`, `VIETNAM_TASK_DISPLAY_NAMES`) |
| Faction doctrine load/save | `game/factions/faction.py` (~360 load map, ~431 serialize) |
| Campaign era tag | `game/campaignloader/campaign.py` (`Campaign.era`) |
| FlightType enum + legacy remap | `game/ato/flighttype.py` (`FlightType`, `_LEGACY_FLIGHT_TYPE_VALUES`) |
| Planner taskings (P3 gate) | `game/commander/tasks/` (`primitive/*`, `packageplanningtask.py`, `theatercommandertask.py`) |
| New-game wizard (P2) | `qt_ui/windows/newgame/QNewGameWizard.py` + `WizardPages/*` |
| Preset pattern to mirror (P2) | `game/settings/difficultypreset.py` |
| Display read-path (P1b) | `game/missiongenerator/kneeboard.py` + the 9 `qt_ui` flight-type sites |

## 11. Map reality

No native DCS Vietnam map exists. Baseline = Caucasus/Marianas overlay (current campaigns) optionally
paired with Starway's "Green Thunder" retexture. Razbam "Wings Over Vietnam" has no firm release —
do not plan around it. Architecture keeps the map swappable.
