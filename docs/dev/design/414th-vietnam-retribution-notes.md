# 414th — "Vietnam Retribution" mode — design notes

**Status:** DRAFT / not-yet-landed (design only). No code written yet.
**Author:** 414th JFG
**Decided direction (this note's scope):**
- Tasking redesign = **doctrine-gated + rename** (one `FlightType` enum, no new enum values).
- New-game entry = **dedicated shell over the shared engine** (a Vietnam card on the New
  Game screen that pre-seeds a profile + filters lists; reuses the existing
  metadata-driven wizard underneath).
- This is **fork identity** (like the Iran pack / Red Tide) — **not upstreamable**, so we can
  be opinionated and don't need to keep it carve-friendly.

---

## 1. The idea

Vietnam shouldn't be "pick a 1970 faction inside the modern flow and hope the planner
behaves." It should be its own front door — a **"only the stuff that matters to Vietnam"
mode** — where the campaign/faction/theater lists are pre-filtered to Vietnam content, the
difficulty/era knobs are pre-seeded, and the auto-planner produces **era-correct taskings
with era-correct names** (MiGCAP, Iron Hand, Alpha Strike, Sandy/Jolly Green) instead of
modern doctrine (HARM DEAD, PGM precision strike, anti-ship packages).

The key architectural insight: **one engine underneath.** The "mode" is three thin layers
stacked on machinery that already exists.

---

## 2. What already exists (verified inventory, 2026-06-28)

This is a content + curation effort, not a rebuild. Confirmed present:

### Factions (`resources/factions/`)
- `USA 1970 Vietnam War.json`, `USA 1971 Vietnam War.json`, `USSR 1971 Vietnam War.json`
- `usa_1965.json`, `usa_1970.json` (blue), `vietnam_1965.json`, `vietnam_1970.json` (NVAF)
- `nva_1970.json` (NVA ground+air), `vietcong_1965.json`, `vietcong_1970.json`
- All Vietnam factions already declare `"doctrine": "coldwar"`.
- `USA 1970 Vietnam War.json` already uses `"excluded_generic_layouts": ["fob1"]` +
  `"extra_layouts": ["vietnam_fob"]`.
- `nva_1970.json` already uses `weapons_introduction_year_overrides` to gate radar AAMs
  (e.g. R-3R/R-60) past their real fielding date.

### Campaigns (`resources/campaigns/`)
- `1968_Yankee_Station.yaml` (+`.miz`) — carrier air war.
- `khe_sanh_niagara.yaml` (+`.miz`) — 1968 siege.
- `operation_velvet_thunder.yaml` (+`.miz`) — third Vietnam scenario.
- All run on existing maps (Caucasus) with renamed/repositioned control points; **there is
  no native DCS Vietnam map.**

### Era mod packs (`pydcs_extensions/`)
`a4ec`, `a6a`, `a7e`, `f4`, `f4e_expanded_weapons`, `f100`, `f104`, `f105`, `f106`, `f9f`,
`f111c`, `mirage3`, `ea6b`, `su15`, `oh6`, `oh6_vietnamassetpack`, `ov10a`,
`vietnamwarvessels` (TeTeT — ships + AI A-1/A-37/MiG-17/RF-101/F-8/O-1 etc.), `coldwarassets`.
Mod-integration pattern proven: `@planemod`/`@shipmod`/… decorators + `inject_weapons()` +
register in `pydcs_extensions/__init__.py` + reference unit ids in faction JSON.

### Era gating (already functional)
- Campaign `start_date` accepts any year (1960s fine).
- `Weapon.available_on(date, faction)` enforces weapon introduction years; gated by the
  `restrict_weapons_by_date` setting; faction-level overrides via
  `weapons_introduction_year_overrides`.
- Date-gated aircraft properties (§24): JHMCS@2003 etc. — harmless to 1970s jets, but the
  mechanism is the template for any era-defining property gate we want.

### Doctrine (the anchor — `game/data/doctrine.py`)
- Frozen `Doctrine` dataclass already carries **capability flags**:
  `cas, cap, sead, strike, antiship` (bool) **plus** all planning geometry (hold/push/ingress
  distances, CAP track lengths, altitudes, escort spacing, durations…).
- Three instances: `MODERN_DOCTRINE`, `COLDWAR_DOCTRINE`, `WWII_DOCTRINE`; registered in
  `ALL_DOCTRINES`.
- `Faction.doctrine` (`game/factions/faction.py`): loaded from the JSON `"doctrine"` string
  via a simple `if doctrine == "modern"/"coldwar"/"ww2"` map (line ~358), default MODERN;
  serialized back as `self.doctrine.name`.

### Planner taskings (`game/commander/tasks/`)
- `primitive/` holds one task module per tasking: `barcap.py`, `forwardbarcap.py`, `cas.py`,
  `bai.py`, `strike.py`, `oca.py`, `sead.py`/`dead.py`, `antiship.py`/`antishipping.py`,
  `armedrecon.py`, `aewc.py`, `refueling.py`, `recovery.py`, `combatsar.py`, the ground
  stance tasks, etc. Plus `compound/`, `packageplanningtask.py`, `theatercommandertask.py`,
  `targetorder.py`.
- `FlightType` (`game/ato/flighttype.py`): the enum **value is the UI display string** and is
  **persisted into the save** (part of the ATO). Renaming a value breaks saves unless added to
  `_LEGACY_FLIGHT_TYPE_VALUES`. **This is why "rename" must be a display layer, not an enum
  edit.**

### The presets/wizard machinery we'll reuse
- New-game wizard: `qt_ui/windows/newgame/QNewGameWizard.py` +
  `WizardPages/{QFactionSelection,QTheaterConfiguration,QGeneratorSettings,QNewGameSettings}.py`.
- Difficulty presets: `game/settings/difficultypreset.py` (`DifficultyPreset` +
  `PRESET_VALUES` + `apply_preset`/`detect_preset`) — the exact pattern to mirror for an
  era/Vietnam preset.
- Settings are 100% metadata-driven (§28 `FIELD_LAYOUT`), so the wizard pages can be
  pre-seeded/filtered without per-field surgery.

---

## 3. Architecture — three layers over one engine

```
┌──────────────────────────────────────────────────────────┐
│  LAYER 1  Shell        "Vietnam" card on New Game screen   │  qt_ui
│           pre-seeds the profile + filters lists            │
├──────────────────────────────────────────────────────────┤
│  LAYER 2  Content filter   Vietnam campaigns/factions/maps │  qt_ui + a tag
│           shown; everything else hidden                    │
├──────────────────────────────────────────────────────────┤
│  LAYER 3  Doctrine profile  which taskings the planner     │  game/data
│           produces + their display names + composition     │  (the substance)
└──────────────────────────────────────────────────────────┘
        ▼ everything below is the existing, unchanged engine ▼
   commander/tasks · flightplan · aircraftgenerator · Lua plugins
```

The whole "mode" is: **select a doctrine profile + an era preset, filter the pickers, and
brand the front door.** No parallel wizard, no fork of the planner.

---

## 4. Layer 3 — doctrine-gated taskings (the substance)

### 4.1 Where it lives

Add a fourth doctrine instance: **`VIETNAM_DOCTRINE`** in `game/data/doctrine.py`, registered
in `ALL_DOCTRINES`, and a `"vietnam"` case in the faction loader
(`game/factions/faction.py` ~line 358). Repoint the Vietnam factions from
`"doctrine": "coldwar"` to `"doctrine": "vietnam"`.

Extend the (frozen) `Doctrine` dataclass with **additive fields (with defaults so the three
existing instances are untouched):**

1. **A tasking whitelist** — the set of `FlightType`s the auto-planner may produce under this
   doctrine. The existing `cas/cap/sead/strike/antiship` bools are the seed of this; we
   generalize to an explicit allow-set so we can also drop `DEAD`, `ANTISHIP`, etc.
2. **A display-name override map** — `{FlightType: "MiGCAP"}` etc. **Crucially this does NOT
   touch the enum value** (which is persisted), so saves stay compatible. The UI and kneeboard
   read the override when a doctrine supplies one, else fall back to `FlightType.value`.
3. **Composition tweaks** — e.g. Alpha Strike package sizing, Iron Hand = Shrike-pair tied to
   an active emitter. Most of these are small numeric/flag knobs, not new planners.

### 4.2 How gating actually bites

The planner already asks "may I plan task X here?" in `game/commander/tasks/` (each primitive
+ `packageplanningtask`/`theatercommandertask`). We gate at that edge against the doctrine's
whitelist — the same place `Doctrine.sead`/`.antiship` are already consulted. **No planner
rewrite**: a disallowed task simply never gets proposed. Manual tasking in the UI can still
offer the full list (or be filtered too — open question §8).

### 4.3 The tasking map (modern → Vietnam)

| Modern `FlightType` | Vietnam display | Doctrine action |
|---|---|---|
| `BARCAP` / `TARCAP` | **MiGCAP / TARCAP** | allow; rename |
| `ESCORT` / `SEAD_ESCORT` | **Escort / Iron Hand Escort** | allow; rename |
| `INTERCEPTION` (+ QRA reserve §1) | **GCI Intercept** | allow (reserve already fits) |
| `SWEEP` / `SEAD_SWEEP` | **Fighter Sweep** | allow |
| `CAS` | **CAS** (FAC-directed) | allow; FAC(A) marking is a future add |
| `BAI` | **Interdiction** (the Trail / Steel Tiger) | allow; rename |
| `STRIKE` | **Alpha Strike** (Rolling Thunder/Linebacker) | allow; **bigger package sizing** |
| `OCA_RUNWAY` / `OCA_AIRCRAFT` | **Airfield Strike** | allow (ROE-limited historically) |
| `SEAD` | **Iron Hand / Wild Weasel** (AGM-45 Shrike) | allow; **Shrike-only, vs live Fan Song** |
| `DEAD` | — | **drop** (no HARM / precision SAM kill) |
| `ANTISHIP` | — | **drop** (NV had ~no fleet) |
| `TARPS` (+ TARS §3/§12) | **Photo Recon** (RF-101/RA-5C) | allow — recon-fog shines here |
| `ARMED_RECON` | **Armed Recon** | allow |
| `SCAR` (→ RESCAP §15) | **Sandy** | allow — iconic, already built |
| `COMBAT_SAR` (§21) / `CSAR`/`SOF` | **King / Jolly Green / Sandy** | allow — iconic, built |
| `JAMMING` (§2 C-130 EW) | **EB-66 / EA-6B standoff jam** | allow; reframe |
| `AEWC` | **College Eye (EC-121)** | allow |
| `REFUELING` / `RECOVERY` | **Tanker track** | allow |
| `TRANSPORT` / `AIR_ASSAULT` | **Airlift / Air Assault** (Khe Sanh resupply) | allow |
| — | **Arc Light** (B-52 cell) | optional future behavior, not v1 |

Honest split: **~70% is whitelist + display-name override** (cheap, no behavior change);
**~30% is real behavior** — Alpha Strike sizing, Iron Hand = Shrike-vs-live-emitter, and
later FAC(A) and Arc Light. Start with the cheap 70%; the behavior items are independently
schedulable.

---

## 5. Layer 2 — content filter

- Tag Vietnam **campaigns** (a field in the campaign YAML, e.g. `tags: [vietnam]` or
  `era: vietnam`) and **factions** (the doctrine == `vietnam`, or an explicit tag).
- The shell's faction/theater/campaign pickers filter to the tagged set. Outside the shell,
  nothing changes — the modern flow still shows everything.
- Maps: the filter offers the maps the Vietnam campaigns actually use (Caucasus today;
  optionally surface the Green Thunder texture-mod tip in the description). A future native
  Indochina map drops in as just another allowed theater.

---

## 6. Layer 1 — the shell

- A **"Vietnam" card/button** on the New Game screen (alongside the normal "New Campaign"
  entry). Selecting it launches the existing `QNewGameWizard` with:
  - the content filter active (Layer 2),
  - a **Vietnam era preset** applied (mirror `difficultypreset.py`: a `PRESET_VALUES`-style
    bundle that sets `restrict_weapons_by_date=True`, era-appropriate labels/realism, mod
    toggles like `vietnamwarvessels`/`coldwarassets`/`ov10a` on, modern-only toggles off),
  - the doctrine profile implied by the chosen faction (Layer 3).
- Bounded UI cost: it's a new entry point + a preset + list filtering, **not** a second
  wizard. The metadata-driven settings (§28) mean we don't hand-edit pages.

---

## 7. Save-compat & constraints

- **Never rename `FlightType` enum values** for the renames — values are persisted in the ATO.
  Renames are a doctrine **display-override layer**; if we ever truly retire a value, it goes
  through `_LEGACY_FLIGHT_TYPE_VALUES` (`game/ato/flighttype.py`).
- `Doctrine` is `@dataclass(frozen=True)` — new fields must have **defaults** so
  MODERN/COLDWAR/WWII instances and any unpickled state stay valid.
- A campaign-mode/era flag stored on the game needs a `__setstate__` default (None/modern) so
  old saves load.
- `coldwarassets` mod gate already referenced in `faction.py` (~line 730) — reuse, don't
  reinvent, the mod-on plumbing for the era preset.

---

## 8. Open questions (decide before/within implementation)

1. **Manual tasking under Vietnam doctrine** — should the in-UI "create flight" task list be
   filtered to the whitelist too, or stay full (planner-gated only)? (Lean: filter it, with a
   "show all" escape hatch.)
2. **`VIETNAM_DOCTRINE` vs. extending `COLDWAR_DOCTRINE`** — a distinct instance is cleaner and
   lets Korea/other cold-war scenarios keep COLDWAR untouched. (Lean: distinct instance.)
3. **Display-override home** — on `Doctrine`, or a separate `EraProfile` that *wraps* a
   doctrine? (Lean: start on `Doctrine`; promote to `EraProfile` only if a second mode needs
   it.)
4. **Alpha Strike sizing** — concrete package size/escort ratios; needs an SME pass.
5. **Iron Hand semantics** — exact "Shrike vs. live emitter" rule and whether it reuses the
   existing SEAD planner with a doctrine flag.
6. **FAC(A) / Arc Light** — confirmed v2, not v1.

---

## 9. Phased plan

- **P0 — content tags + verification.** Add the Vietnam tag to the 3 campaigns + Vietnam
  factions; confirm the existing `tests/` Vietnam content gate still passes.
- **P1 — doctrine profile.** Add `VIETNAM_DOCTRINE` (whitelist + display overrides, behavior =
  COLDWAR for now), wire faction loader `"vietnam"`, repoint Vietnam factions. Wire the
  display-override read path in UI + kneeboard. (Cheap 70%.)
- **P2 — era preset + shell.** Mirror `difficultypreset.py` for a Vietnam era bundle; add the
  New Game "Vietnam" card + list filtering.
- **P3 — behavior taskings.** Alpha Strike sizing; Iron Hand = Shrike-vs-emitter; drop
  DEAD/ANTISHIP from the whitelist and verify the planner degrades cleanly.
- **P4 — flavor (optional).** FAC(A), Arc Light, kneeboard/branding polish.

Each phase is independently shippable and CI-gated (Black/mypy/pytest; Lua gate if any plugin
touched). Add an in-game-pass checklist row for any runtime tasking-behavior change (P3+).

---

## 10. Integration-point index (verified paths)

| Concern | Path |
|---|---|
| Doctrine dataclass + instances | `game/data/doctrine.py` (`Doctrine`, `MODERN/COLDWAR/WWII_DOCTRINE`, `ALL_DOCTRINES`) |
| Faction doctrine load/save | `game/factions/faction.py` (~358 load map, ~431 serialize) |
| FlightType enum + legacy remap | `game/ato/flighttype.py` (`FlightType`, `_LEGACY_FLIGHT_TYPE_VALUES`) |
| Planner taskings | `game/commander/tasks/` (`primitive/*`, `packageplanningtask.py`, `theatercommandertask.py`) |
| New-game wizard | `qt_ui/windows/newgame/QNewGameWizard.py` + `WizardPages/*` |
| Preset pattern to mirror | `game/settings/difficultypreset.py` |
| Settings layout (metadata-driven) | `game/settings/settings.py` (`FIELD_LAYOUT`) |
| Weapon date gating | `game/data/weapons.py` (`Weapon.available_on`), `restrict_weapons_by_date` |
| Vietnam factions | `resources/factions/{USA 1970/1971 Vietnam War, USSR 1971 Vietnam War, usa_1965/1970, vietnam_1965/1970, nva_1970, vietcong_1965/1970}.json` |
| Vietnam campaigns | `resources/campaigns/{1968_Yankee_Station, khe_sanh_niagara, operation_velvet_thunder}.yaml` |
| Era mod packs | `pydcs_extensions/{a4ec,a6a,a7e,f4,f100,f104,f105,f106,f9f,f111c,mirage3,ea6b,su15,oh6*,ov10a,vietnamwarvessels,coldwarassets}` |

---

## 11. Map reality (the one real gap)

No native DCS Vietnam map exists. Baseline = Caucasus overlay (current campaigns already do
this) optionally paired with Starway's "Green Thunder" Caucasus retexture for a SE-Asia look.
Razbam "Wings Over Vietnam" is listed but has no firm release — **do not plan around it.**
Architecture keeps the map swappable (just another allowed theater) if a native one ships.
