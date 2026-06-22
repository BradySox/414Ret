# 414th Red Tide Campaign Notes

Design and build notes for **Germany - Red Tide** (`resources/campaigns/red_tide.yaml`
+ `red_tide.miz`), the 414th's reworked GermanyCW scenario. Read this before editing the
campaign or re-touching its `.miz`; it records *what* was changed, *where* in the binary,
and the gotchas that bit us.

Red Tide is a **fork of `crossing_the_rubicon`**, not a rewrite of it. The original
campaign is preserved untouched (it kept only an unrelated `An-26B` variant-id fix). Red
Tide is a separate, selectable campaign that carries the heavier 414th laydown.

## Premise

13 July 1988, a conventional Warsaw Pact invasion through the Fulda Gap — explicitly in the
spirit of Tom Clancy's *Red Storm Rising* (nodded to in the in-app description). Framing
puts the player inside the **414th Joint Fighter Group**, a multinational NATO wing that
simply *happened* to be forward-based when it kicked off. Setting stays 1988-07-13; player
faction `Blufor Late Cold War (80s)`, enemy `Russia 1980`. The premise is written so the
in-game laydown matches the fiction: Hamburg has fallen, the carrier never made station,
and a dense SAM belt (S-300/SA-11) reaches deep.

## Force laydown

GermanyCW coordinate convention: **larger x = further north**, **larger (less negative)
y = further east**. The blue/red split is intentionally clean — every blue base sits in the
south-west (the real Rhineland NATO cluster), every red base to the north/centre/east.

### Blue (NATO) — south-west cluster
| Base | id | Squadrons |
|---|---|---|
| Ramstein | 165 | B-1B (OCA/Runway), A-10A (CAS), Mirage-F1EE (Escort), AV-8B (SEAD Sweep), **A-6E (OCA/Aircraft)** |
| Spangdahlem | 162 | F-15C (TARCAP), **F-14B (Escort)**, **GAF JG 74 (TARCAP)**, F-4E-45MC (BAI), UH-1H, AH-1W |
| Hahn | 155 | B-52H (Strike), F-16CM (DEAD), Tornado IDS (SEAD Escort), F-4E-45MC (OCA/Runway), **F/A-18C (SEAD)**, **F-15E (BAI)** |
| Frankfurt | 163 | KC-135, C-130J, CH-47F, AH-64D, **E-3A (AEW&C)**, **OH-58D Kiowa (Escort)** |

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

### Faction edit (shared)
`resources/factions/russia_1980.json` — added `SA-11` (Buk) and `SA-10/S-300PS` preset
groups. Both are vanilla DCS and match the names already used by `russia_1990`. This is a
**shared-faction** change, so the original Crossing the Rubicon also gets the tougher IADS.

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

## Known caveats — verify on first in-game load

The Lua plugins/terrain can't be exercised here; pydcs/DCS aren't runnable in CI. Confirm:

1. **Kastrup loads as red.** If it shows neutral, the `[41]` warehouse entry didn't take.
2. **All three naval groups spawn red.** Coalition is resolved by nearest base; up north
   that is red (Kastrup/Peenemünde), but it is computed at load, not asserted here.
3. **`Red Navy Copenhagen` position** (x≈80000, y≈-430000) is an *estimated* open-water
   point off Copenhagen — eyeball that it isn't clipping land/an island. One-line nudge if so.

## Files
- `resources/campaigns/red_tide.yaml` / `red_tide.miz` — the campaign.
- `resources/campaigns/crossing_the_rubicon.*` — original, preserved (An-26B fix only).
- `resources/factions/russia_1980.json` — SA-10/SA-11 preset groups.
