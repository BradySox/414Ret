# 414th — "Vietnam Retribution" mode — design notes

**Status:** **P0 + P1 (doctrine model) landed**; P1b (display read-path) + P2 (shell/preset) +
P3 (behaviour taskings) outstanding.
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
  Vietnam factions are repointed from `coldwar`. Behaviour is identical to COLDWAR (verified by a
  rebadge-equality test). Tests: `tests/test_vietnam_doctrine.py`,
  `tests/test_vietnam_content.py::test_vietnam_factions_load_vietnam_doctrine`.
  - **Borderline repoints to confirm:** `usa_1965.json` / `usa_1970.json` are *generic* 1965/1970
    US factions (not Vietnam-War-named). They're Vietnam-*era*, so the renames fit, but they could
    be used in other Cold-War-SEA scenarios. Repointed per the design's faction list; flag if undesired.
- **P1b — display read-path — TODO.** The renames are in the model but **not yet surfaced**: the
  kneeboard (~10 sites) + ~9 `qt_ui` sites still render `FlightType.value`. Route them through
  `doctrine.display_name_for(...)` (the player faction's doctrine). Several `kneeboard.py` helpers
  take a bare `FlightType` and need the doctrine threaded in. Do it comprehensively (avoid
  "Alpha Strike here, Strike there").
- **P2 / P3 / P4** — see §9.

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
- **P1 — doctrine model.** ✅ DONE (model + faction repoint + tests). **P1b — display read-path** TODO.
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
