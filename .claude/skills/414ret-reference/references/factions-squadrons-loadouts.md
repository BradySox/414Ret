# Factions, Squadrons, Pilots, Loadouts (distilled from wiki)

## Custom factions

YAML (preferred) or JSON. Locations: `resources/factions/` (bundled) or `<DCS Saved Games>/Retribution/Factions/` (custom — appears at bottom of list, not alphabetized). Errors = faction silently missing; check console output and validate syntax first.

| Field | Notes |
|---|---|
| `country` | Must be a valid DCS country or mission generation fails |
| `name` | Faction name in Retribution UI |
| `aircrafts`, `awacs`, `tankers` | Air units |
| `frontline_units`, `artillery_units`, `infantry_units`, `logistics_units`, `air_defense_units`, `missiles`, `naval_units` | Ground/naval |
| `preset_groups` | Reference by NAME only (strings) — the group definitions live in `resources/groups/`, never inline in the faction file |
| `requirements` | Dict of mod name → download URL; `{}` if none |
| `carrier_names`, `helicopter_carrier_names` | Random pick if multiple |
| `has_jtac`, `jtac_unit` | JTAC config |
| `doctrine` | `modern` / `coldwar` / `ww2` — drives flight altitudes and planner AI |
| `building_set` | `default` / `ww2ally` / `ww2germany` / `ww2free` |
| `locales` | For random pilot-name generation (default en_US) |
| `liveries_overrides` / `liveries_overrides_ground_forces` | Aircraft or vehicle → list of liveries, random pick; livery must exist for the country |
| `weapons_introduction_year_overrides` | Weapon group → year; e.g. block a client state from AIM-120s |
| `cargo_ship` | Default Bulker Handy Wind; WW2 factions pick something period-correct |
| `unrestricted_satnav` | true = non-US aircraft get GPS |

**Unit naming — the rule that trips everyone:** faction files use Retribution *variant names*, not DCS names. Variants live under `variants:` in `resources/units/aircraft/*.yaml` (and `ground_units/`, `ships/`). Variants are name-only skins over the real DCS module (an "EF-18A+" is still the F/A-18C module). The unit YAML files are the authoritative list — don't trust hand-maintained lists.

Give every faction at least one of each ground unit class (tank, IFV, APC, ...) or auto-purchase misbehaves. Core-module liveries must be in the module's livery folder, not Saved Games.

## Squadron YAML

Bundled: `resources/squadrons/**/*.yaml`. User: `<DCS Saved Games>/Retribution/Squadrons/**/*.yaml`. Subdirectory names are just organization.

| Field | Notes |
|---|---|
| `name`, `nickname`, `country`, `role` | Country spelled exactly as in faction files; CJTF factions match all squadrons with the right aircraft |
| `aircraft` | Retribution variant name |
| `mission_types` | Spelled exactly as in the UI; incompatible ones are dropped with a log error |
| `livery` | One livery — for custom downloads, use the livery FOLDER name |
| `livery_set` | Multiple liveries, random round-robin (each used once before repeats) |
| `bases` | Override shore/carrier/lha. Defaults: helicopters all three; LHA-capable shore+lha; carrier-capable carrier only; everything else shore only. This is how you make carrier-and-shore Marine Hornet squadrons |
| `pilots` / `players` | Named AI / player pilots used before random generation |
| `radio_presets` | e.g. `intra_flight:` list of frequencies — keeps MP squadron freqs consistent |
| `female_pilot_percentage` | Optional |

Pilot mechanics: one pilot per airframe (no multi-crew modeling); pilots die with their aircraft (players exempt by default — the airframe is still lost); AI pilots gain a skill level every 4 missions; recruitment auto-refills understaffed squadrons at up to 4 pilots/turn toward a 16-pilot cap (both configurable under Campaign Management → Pilots and Squadrons); leave prevents auto-assignment next turn. Adding a squadron mid-campaign: Air Wing → Faction OWNFOR → add the aircraft type, then enable the "Enable Air Wing adjustments" cheat and add the squadron in the Air Wing Config dialog.

Player planning preference (settings): Disabled / Never assign players / No preference / Prefer players — controls whether the auto-planner puts player pilots on generated missions.

## Custom loadouts

Create the loadout in the DCS mission editor, name it exactly `Retribution <mission type>` (e.g. `Retribution OCA/Aircraft`). Mission-type names = Retribution flight types as shown in the UI. DCS saves them under `Saved Games\DCS\MissionEditor\UnitPayloads\`.

**Fallback chain — you don't need one per type.** Defining the base types covers most others:

| Missing type | Falls back to |
|---|---|
| SEAD Escort | SEAD |
| Escort, Fighter sweep | TARCAP |
| Intercept | BARCAP |
| OCA/Aircraft | BAI → CAS |
| DEAD | BAI → CAS |
| OCA/Runway | Strike |

`Liberation <type>` names also work (migration support); "Prefer custom Liberation payloads" in Preferences controls which prefix wins (off = Retribution first).
