# Khe Sanh — Operation Niagara (1968) — campaign design notes

Status: **built + headless-validated** (2026-06-28). `khe_sanh_niagara.yaml` +
`khe_sanh_niagara.miz` are in `resources/campaigns/` — the `.miz` was scripted by forking
`1968_Yankee_Station.miz` (pydcs load → re-color airfields → rebuild front edges → save;
pydcs `save()` works here, the old "broken" note was stale). Retribution's `MizCampaignLoader`
loads it with **Kutaisi blue + encircled by red Senaki/Sukhumi/Kobuleti** and Batumi/carriers
as the relief pocket. Leftover Yankee-Station FOBs were stripped (1 blue + 8 red). Base
defenses are **faction-generated from the inherited preset-location markers** (the correct
Retribution mechanism — not hand-placed groups): verified the red ring carries heavy AAA +
armor (incl. the Lang Vei armor group at Kobuleti, filled by NVA PT-76/`[CH] T-54`) + SAM
sites + IADS C2. **Pending (authenticity tuning, non-blocking):** Khe Sanh/Kutaisi inherits
Hanoi's 12 factories + 8 SAM sites — thin those for a firebase feel; relocate SA-2 to depth;
then the **in-game flight verify**. The fork builder is `scratchpad/khe_build.py`. Standalone
Vietnam campaign for Caucasus, distinct from `1968_Yankee_Station` (the broad North/South air
war); this one is a **siege**.

## Historical frame (21 Jan – 8 Apr 1968)

~6,000 US Marines (26th Marines) + ARVN Rangers held **Khe Sanh Combat Base** in NW Quang
Tri, encircled by 2–3 NVA divisions (304th, 325C, elements 320th/324th, ~20,000+). The
defense rested on **Operation Niagara** — a continuous air umbrella: B-52 *Arc Light* box
strikes (sometimes within ~1 km of the wire), Marine/Navy/USAF tac air (A-4, F-4, A-1, A-6),
and **aerial resupply** (C-130 LAPES/GPES/parachute, C-123). The defining terrain was the
ring of **hills — 881S, 881N, 861, 861A, 558, 950** (the "Hill Fights") and the **Lang Vei
Special Forces camp**, overrun 7 Feb by NVA **PT-76 amphibious tanks** (first NVA armor in
the South). Relief came overland-by-air via **Operation Pegasus** (1st Cav, up Route 9) in
April. The threat to aircraft was **massive AAA** (12.7/23/37/57 mm) + small arms — *not*
MiGs; SA-2s were a deeper-North problem. **No MANPADS** (SA-7 appeared in 1972).

## Why it's a good Retribution campaign

Asymmetric by design: **blue owns the air, red owns the ground and the initiative.** The
player (blue) keeps an encircled base alive with airpower while red grinds the perimeter,
then mounts the Pegasus relief. Showcases Combat SAR (downed pilots over hostile hills),
TIC perimeter firefights, dynamic fronts, and meaty BAI/CAS targets (artillery on the hills,
PT-76/T-54 armor at Lang Vei — now in `NVA 1970` after the 2026-06-28 faction pass).

## Map: Caucasus — geography mapping

Built as its **own `.miz`** (do not reuse Yankee Station's front layout — the siege ring is
a different topology). NW-Vietnam highlands mapped onto the foot of the Caucasus range:

| Vietnam | Caucasus CP | Side | Role |
|---|---|---|---|
| **Khe Sanh Combat Base** | **Kutaisi-Kopitnari** | BLUE | the besieged base — forward, encircled, air-only resupply; C-130-capable strip |
| Hills 881/861/558 + NVA arty massif | **Sukhumi** + foothill FARPs/TGOs | RED | the siege ring NW of the base — artillery + AAA on the high ground |
| Route 9 east / Pegasus axis | **Senaki-Kolkhi** | RED | NW approach the relief must reopen |
| Lang Vei SF camp (fell to PT-76) | **Kobuleti** + a red forward TGO | RED | SW — the armor threat (PT-76/T-54), Route 9 |
| Da Nang (relief + tac-air rear) | **Batumi** | BLUE | main blue tac-air + the Pegasus ground-relief staging |
| Yankee Station | **1–2 CV in the Black Sea off Batumi/Poti** | BLUE | offshore strike + BARCAP (A-4/A-6/F-8/F-4/E-2) |
| NVA divisional rear / Laos / DMZ | **Tbilisi-Vaziani** area | RED | deep rear — SA-2 belt, supply depots, token MiG-21 |

**Topology:** Kutaisi (blue) is **encircled** — its adjacent CPs (Senaki, Sukhumi, Kobuleti)
are all red, so the front line rings it and its only lifeline is air. Blue's *other* holding
(Batumi + carriers) is a **separate pocket**, not land-adjacent to Kutaisi. The blue win
arc = push from Batumi through Kobuleti/Senaki to **link up with Kutaisi** = break the siege
= Operation Pegasus.

## Factions

- **Blue:** `USA 1970 Vietnam War` (A-4, F-4, A-1, F-8, A-6, OV-10 FAC, UH-1/CH-53, C-130,
  B-52, the VWV carriers/New Jersey gun line from the faction pass).
- **Red:** `NVA 1970` — ground-heavy (T-55A, **[CH] T-54**, **PT-76**, BM-21, AAA belts),
  air-light (token MiG-17/19/21, Mi-8). Historically right: almost no red air over Khe Sanh.

## Economy — the siege lever

Player = blue (defender + relief force). No "aggressor" flag — skew the economy:

```yaml
recommended_player_money: 3000          # the Niagara air armada
recommended_enemy_money: 1500
recommended_player_income_multiplier: 1.5
recommended_enemy_income_multiplier: 1.2   # red keeps feeding the siege ground
```

Keep red's **air** budget effectively unspent (give red few/no fighter squadrons), so its
money flows to ground (front reinforcements). `automate_front_line_reinforcements: true` so
the ring keeps pressing. The besieged Kutaisi garrison starts ground-thin — held by air.

## Settings (mirror Yankee Station's mod block, plus the siege specifics)

```yaml
theater: Caucasus
recommended_start_date: 1968-01-21        # siege D-day
advanced_iads: true                       # deep SA-2 C2 in the NVA rear; AAA-only at the base
performance: 2
settings:
  vietnamwarvessels: true                 # carriers / New Jersey / riverine
  russianmilitaryassetspack: true         # [CH] T-54 / ASU-85 for the NVA armor
  ov10a_bronco: true                      # FAC / JTAC
  manpads: false                          # NO SA-7 in 1968 — historically critical
  night_day_missions: NightMissions.OnlyDay   # DayAndNight is authentic (Niagara ran 24/7) but harder
  automate_front_line_reinforcements: true
  max_frontline_width: 20                 # tight siege perimeter
  invulnerable_player_pilots: true
  player_skill: "Excellent"
  enemy_skill: "Average"
```

## Draft squadron laydown

(CP keys finalise to the `.miz` warehouse names/ids once built — names below are the
Caucasus airfields.)

```yaml
squadrons:
  # --- Khe Sanh Combat Base (besieged garrison air) ---
  Kutaisi:
    - { primary: CAS, secondary: air-to-ground, aircraft: [AH-1W SuperCobra], size: 4 }
    - { primary: CAS, secondary: air-to-ground, aircraft: [A-1H Skyraider], size: 4 }   # forward Sandy
    - { primary: Air Assault, secondary: any, aircraft: [UH-1H Iroquois], size: 4 }      # medevac/resupply
  # --- Da Nang (tac-air rear + Pegasus relief) ---
  Batumi:
    - { primary: CAS, secondary: air-to-ground, aircraft: [A-4E Skyhawk], size: 12 }
    - { primary: Strike, secondary: air-to-ground, aircraft: [F-4E Phantom II], size: 12 }
    - { primary: CAS, secondary: air-to-ground, aircraft: [A-1H Skyraider], size: 8 }
    - { primary: CAS, secondary: air-to-ground, aircraft: [OV-10A Bronco], size: 4 }     # FAC/JTAC
    - { primary: BARCAP, secondary: air-to-air, aircraft: [F-8E Crusader], size: 8 }
    - { primary: Strike, secondary: air-to-ground, aircraft: [B-52H Stratofortress], size: 4 }  # Arc Light
    - { primary: Refueling, aircraft: [KC-135 Stratotanker], size: 2 }
    - { primary: Transport, secondary: any, aircraft: [C-130J-30], size: 4 }              # Khe Sanh airlift
    - { primary: Air Assault, secondary: any, aircraft: [CH-53E], size: 2 }
    - { primary: Air Assault, secondary: any, aircraft: [UH-1H Iroquois], size: 4 }
  # --- Carrier (Yankee Station, offshore) ---
  Carrier:
    - { primary: AEW&C, aircraft: [E-2C Hawkeye], size: 2 }
    - { primary: BARCAP, secondary: air-to-air, aircraft: [F-4B Phantom II], size: 12 }
    - { primary: Strike, secondary: air-to-ground, aircraft: [A-6A Intruder], size: 12 }
    - { primary: Strike, secondary: air-to-ground, aircraft: [A-4E Skyhawk], size: 12 }
  # --- NVA siege ring + rear (mostly GROUND in the .miz; minimal air) ---
  Sukhumi:    # the hills
    - { primary: CAS, secondary: air-to-ground, aircraft: [Mi-8MTV2 Hip], size: 4 }
  Tbilisi:    # NVA divisional rear
    - { primary: BARCAP, aircraft: [MiG-21bis Fishbed-N], size: 8 }   # token MiG presence
    - { primary: Transport, aircraft: [An-26B], size: 4 }
```

## `.miz` build blueprint (DCS Mission Editor)

The `.miz` carries the theater (CPs, fronts, objective groups). Two paths:

**Fast path — fork Yankee Station's `.miz`** (same terrain): open `1968_Yankee_Station.miz`,
then (a) flip control-point ownership to the siege topology above, (b) delete the broad
North/South front and draw the **encirclement ring** around Kutaisi + a second front
Batumi↔Kobuleti, (c) re-place objective groups (below). Saves laying the carrier/airfield
warehouses from scratch.

**Objective groups to place:**
- **Siege ring (red):** artillery groups (BM-21, towed) on the foothill "hills" around
  Kutaisi; dense **AAA belt** (ZU-23, S-60 57 mm, ZSU-57-2) — the real Khe Sanh threat —
  but **no SAM** at the base (SA-2 only in the Tbilisi rear). Per-base C2 cells (Command
  Center + Comms + power statics) for `advanced_iads` range mode.
- **Lang Vei (red, Kobuleti approach):** a **PT-76 / [CH] T-54** armor group — the campaign's
  signature armor threat / BAI target.
- **NVA rear (Tbilisi):** SA-2 sites + supply depots (the deep-interdiction targets).
- **Blue:** carrier group(s) in the Black Sea off Batumi; Batumi as the tac-air warehouse;
  Kutaisi as the besieged warehouse (ground-thin garrison).
- **Front markers:** the ring around Kutaisi + the Batumi↔Kobuleti front (Pegasus axis).

**Authenticity guardrails:**
- `manpads: false` and **no SA-7** anywhere (1968).
- AAA, not SAM, around the base; SA-2 only in depth.
- Red air token-only (no large MiG presence near the base).
- PT-76/T-54 belong at the Lang Vei (Kobuleti) approach, not the deep rear.

## 414th features it showcases / could verify

- **Combat SAR** (G8–G12): downed pilots over the hostile hill ring — the whole COIN mood.
- **TIC** perimeter firefights; **dynamic fronts** (Pegasus relief movement).
- **Meaty BAI** (the "BAI targets too thin" itch): hill artillery + PT-76/T-54 armor.
- **Advanced IADS / MANTIS**: SA-2 C2 in the Tbilisi rear (watch the blind-network rule —
  the NVA rear needs an EWR-class unit + 1L13 markers, per the MANTIS blind-net note).

## Open decisions before build

1. Besieged base = **Kutaisi** (recommended, inland/highland feel) vs a coastal Senaki.
2. B-52 Arc Light from **Batumi** vs a dedicated off-map field.
3. Night ops: `OnlyDay` (default) vs `DayAndNight` (authentic Niagara, harder).
