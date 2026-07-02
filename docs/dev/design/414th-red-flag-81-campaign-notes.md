# 414th — Red Flag 81-2 (Nevada) Campaign Notes

Design and build notes for **Nevada - Red Flag 81-2**
(`resources/campaigns/red_flag_81_2.yaml` + `red_flag_81_2.miz`) — a Retribution
campaign on the NTTR that recreates the **1981 Red Flag exercise war** with the full
**Vietnam mechanics stack** (political will, static front, ROE/phases arc, Vietnam Ops
runtime suite, Vietnam doctrines). The styling/laydown reference is the commercial
**Reflected Simulations "F-4E Red Flag 81-2"** DCS campaign the squadron flies (its
kneeboard idiom is already harvested in `414th-campaign-doc-ideas-harvest.md` §1).

> **Laydown refinement pending:** the squadron is supplying the actual 81-2 campaign
> `.miz` so the range-target laydown (mock airfield, SAM emulator rings, convoy routes,
> tank arrays) can be re-pointed at the real placements. The current `.miz` is a
> historically-plausible first cut built from the dreamlandresort/NTTR public record.
> When the reference arrives: compare target coordinates, adjust markers, keep this doc
> in sync.

---

## 1. The study — Red Flag and the F-4

### Why Red Flag exists (the Vietnam link that makes this campaign fit the fork)

Red Flag **is** the Vietnam feedback loop institutionalized. Gen. John D. Ryan's
dissatisfaction with Vietnam loss rates and bombing accuracy fed the **Red Baron**
studies, which found most aircrew losses happened in their **first ten combat
missions**. Col. Richard "Moody" Suter sold TAC commander Gen. Robert J. Dixon on
giving crews those ten missions *in peacetime*; Dixon approved in **May 1975**, the
first Red Flag flew **29 November 1975** (37 aircraft, 561 personnel, 552 sorties),
and the **4440th Tactical Fighter Training Group (Red Flag)** was chartered
**1 March 1976**. So a Retribution campaign that plays Red Flag *with the Vietnam
mechanics* is not a mash-up — it is literally the war the exercise was built to
rehearse: the aggressors flew NVA/Soviet GCI doctrine, the ranges were dressed with
SA-2/SA-3 emulators and AAA belts, and the scoring pressure ("political will") maps to
the exercise assessment.

### The F-4's Red Flags

- **Red Flag I (Nov–Dec 1975):** primary unit = **49th TFW F-4Ds** (Holloman), with
  OV-10s, F-105 Weasels and CH-53s in support. Before Red Flag, F-4 crews trained
  "F-4 versus F-4" — the whole point was to stop that.
- The F-4 was the backbone TAC fighter of Red Flag's first decade: **4th TFW /
  Seymour Johnson F-4Es** (the 81-2 player unit), **347th TFW F-4Es** (photographed at
  Nellis 1981), **388th TFW F-4Es** (until their 1980 F-16 conversion), **George AFB
  F-4G Advanced Wild Weasels**, **RF-4C** recon squadrons flying the reconnaissance
  block of nearly every flag, plus ANG/AFRES F-4C/D units.
- **Red Flag 81-2** (second flag of FY81): the Reflected campaign puts the player in
  the **336th TFS "Rocketeers" (4th TFW, Seymour Johnson AFB)** on a two-week
  detachment to Nellis — **13 missions**, force-on-force over the NTTR.

### The red force of 1981 (what the `.miz` models)

- **Aggressor air:** the **64th & 65th Aggressor Squadrons** at Nellis flew **F-5E
  Tiger IIs** simulating the MiG-21 with Soviet/NVA GCI tactics (born as the 64th FWS
  in fall 1972, first with T-38s).
- **Constant Peg:** the **4477th TES "Red Eagles"** flew *actual* **MiG-17s/21s** (and
  later MiG-23s) out of the **Tonopah Test Range airfield** from July 1979 — so red
  MiGs flying from TTR in this campaign is the literal 1981 order of battle, not a
  what-if.
- **Ground threat array:** SA-2/SA-3 **emulator sites** and GCI/EW emitters around the
  **Tolicha Peak Electronic Combat Range** (between Tonopah and Beatty) and the north
  ranges; **"Smoky SAM"** (GTR-18) visual launch simulators; ZSU-23-4/AAA gun sims —
  the Red Team historically sets up on the **west side** of the Nellis ranges.
- **Targets:** 50+ types across ranges 61–76 — a **mock airfield** dressed with
  mothballed airframes at Tolicha Peak, **convoys**, **trains**, tank arrays,
  industrial complexes, POL, bridges, radar/SAM/AAA sites.
- **The Box:** the Groom Lake restricted airspace sat (and sits) inside the range
  complex and is **never** released to exercise traffic — the perfect analog for the
  Vietnam arc's never-releasing sanctuary ring (the PRC-border ring in Yankee
  Station).

Sources: Wikipedia "Exercise Red Flag", Air & Space Forces Magazine "Red Flag",
dreamlandresort.com NTTR exercise/range pages, Nellis 414th CTS fact sheet (yes — the
real Red Flag is run by the **414th** Combat Training Squadron, which is too good a
coincidence not to note), Reflected Simulations product page.

---

## 2. Game framing — "the exercise as the war"

We play the war the exercise simulates, from inside the sim: BLUE is the deployed Blue
Force (the 336th's detachment + supporting players), RED is the integrated Red Force
(aggressors + threat array + a simulated enemy ground army holding the ranges).
The Vietnam mechanics stack maps 1:1:

| Mechanic | Red Flag reading |
|---|---|
| `vietnam_political_will` (BLUE will) | The TAC exercise assessment — blow the ROE, bleed jets, and the flag is scored a failure ("Washington orders withdrawal" reads as *the exercise is called off*) |
| Regime Resolve (RED) | Red Force's capacity to keep contesting; break it and Blue "graduates" (the negotiation WIN) |
| `vietnam_static_front` | The simulated FEBA on the ranges — it bends under pressure but the exercise never lets it sweep the map; Air Assault is the deliberate territorial lever |
| Authored `phases:` arc | The two-week exercise period structure (see §5) — restrictions release as the flag escalates, exactly like the Rolling Thunder → Linebacker II arc rides the same engine |
| `gci_ambush` (red doctrine) | Aggressor hit-and-run GCI — late scramble, one slash through the package, home. This IS the documented aggressor playbook |
| Vietnam Ops runtime (§32–§39) | The range environment: flak gauntlet = the AAA sims, FAC willie-pete = the OV-10s that flew Red Flag I, Arc Light = SAC B-52 cells (B-52s flew Red Flag from the start), convoy interdiction = the moving convoy targets, harassment = red "sapper play" against forward strips |

Vietnam-worded banners/verdict strings ("Hanoi agrees to terms") stay as-is — the
aggressors are *playing* Hanoi; that's the fiction of the exercise itself.

---

## 3. Laydown (first cut — refine from the reference `.miz`)

Base `.miz` derived from `exercise_vegas_nerve.miz` (same theater, rebuilt marker set,
ownership flipped to the classic Red Flag geometry: Blue in the SE corner, Red holding
the ranges to the NW). **The miz is generated, not hand-edited**:
`tools/build_red_flag_81_2_miz.py` (any recent release pydcs round-trips it; the
laydown tables at the top of the script are the single edit point). Re-run it to
regenerate `resources/campaigns/red_flag_81_2.miz` after a laydown change.

NTTR coordinate convention: **larger x = further north**, **larger (less negative)
y = further east**.

### Control points

| CP | id | Side | Role |
|---|---|---|---|
| Nellis AFB | 4 | **BLUE** | The deployment base — player F-4E wing, tankers, AWACS |
| Creech (Indian Springs AAF, its 1981 name) | 1 | **BLUE** | Forward helo/FAC field on the range boundary |
| Camp Mercury FOB | — (FOB marker) | **BLUE** | Blue's toe-hold inside the south range boundary (NTS gate analog); Super Gaggle destination when besieged |
| Tonopah Test Range | 18 | **RED** | Red air hub — the 4477th's real field (MiG-21/17, F-5E det) |
| Groom Lake AFB | 2 | **RED** | **The Box** — sanctuary inside a never-releasing restricted zone |
| Pahute Mesa Airstrip | 16 | **RED** | Forward red strip feeding the FEBA |
| Beatty | 5 | **RED** | Western red logistics node (Tolicha Peak corridor) |
| Tonopah (civil) | 17 | **RED** | Red rear depot |
| FOB Tolicha | — (FOB marker) | **RED** | Red forward ground node south of Pahute Mesa — the FEBA anchor |
| McCarran / Henderson / North LV / Boulder City / Jean / Echo Bay / Laughlin / Mesquite / Lincoln County / Mina | 3/8/15/6/9/7/10/13/11/14 | NEUTRAL | Civil fields — off-exercise |
| Strategic Air Command (off-map, NE spawn) | — | BLUE | SAC B-52/tanker cells (kept from Vegas Nerve's off-map spawn, renamed) |

### The front

Single front: **Camp Mercury (BLUE) ↔ FOB Tolicha (RED)** up the Nevada Test Site
corridor (Mercury Hwy → Pahute Mesa axis). YAML `supply_routes` (the fork mechanism,
as Yankee Station) — blue↔red connection creates the FrontLine; `vietnam_static_front`
pins it in the ±10 % band.

Red's rear web (red↔red, interdiction targets, never new fronts):
Tonopah (17) → TTR (18) → Pahute Mesa (16) → FOB Tolicha, plus Beatty (5) → FOB
Tolicha (the US-95/Tolicha corridor — the campaign's "trail" that
`vietnam_convoy_interdiction` keeps flowing). Blue rear: Nellis → Creech → Camp
Mercury (blue↔blue).

### Objective markers (per `MizCampaignLoader` conventions)

- **SA-2 rings** (`S_75M_Volhov` MERAD markers): Tolicha Peak complex ×2, TTR ring,
  Pahute Mesa, Groom box edge — the emulator sites.
- **SA-3 point defense** (`x_5p73_s_125_ln`): TTR field + the mock airfield complex.
- **AAA** (`ZSU_23_4_Shilka` markers): gun belts along the two ingress corridors
  (Student Gap analog N of Creech; the western Beatty corridor) + every red field +
  the FEBA/strip point defense — feeds the §33 flak gauntlet. **No SHORAD markers**:
  the 1981 Red Force faction has no SAM-SHORAD unit (guns were the point defense), so
  a SHORAD preset location could never be filled.
- **EWR** (`1L13` markers): Tonopah (P-37 Bar Lock from the faction) + an eastern
  site covering the Groom approach.
- **Armor arrays** (`M_1_Abrams` markers): Kawich Valley tank array (N ranges),
  Gold Flat array, FEBA armor at FOB Tolicha.
- **Strike targets**: mock airfield complex at Tolicha Peak (`Tech_combine` strike
  target + `Workshop_A` factory + ammo depot markers — **factories must sit in the
  BLUE country block**, the loader only scans blue statics for factories), industrial
  complex at TTR, POL/ammo at Tonopah civil and Beatty.
- **Command center** (`_Command_Center` static): Red Force C2 inside the Groom box
  (hidden until the §15 command-post fog is beaten).
- **Convoy spawn hints** (`M1043_HMMWV_Armament` pairs) near each CP, as Vegas Nerve.
- Kept from Vegas Nerve: the TTR Invisible-FARP helipad cluster (red helo ground
  spawns), both off-map spawn plane groups (renamed to SAC roles).

### What the reference `.miz` should refine

Exact coordinates of: the mock airfield target complex, the SA-2/SA-3 emulator sites,
the convoy route the campaign uses, tank-array placement, any range targets we
haven't modeled (trains, bridges) — plus anything about the 81-2 mission flow worth
folding into the phases arc.

---

## 4. Factions

Two new faction files (era-correct, doctrine-wired):

- **`usa_red_flag_1981.json`** — "USA Red Flag 1981", country USA, **doctrine
  `vietnam`** (MiGCAP/knife-fight ranges, strike-through-threat, no-SEAD whitelist —
  Iron Hand rides the strike packages, which is exactly how an F-4E wing without
  co-located Weasels fought). Air: F-4E-45MC (player), A-10A (new at Red Flag
  ~1979+), OV-10A (mod), RF-101B (VWV; RF-4C stand-in — no DCS RF-4C), B-52H, C-130,
  UH-1H/CH-47D helos, E-3A (IOC 1977) + KC-135s.
- **`red_force_aggressors_1981.json`** — "Red Force 1981 (Nellis Aggressors)",
  country **USAF Aggressors** (a real DCS country), **doctrine
  `vietnam_air_defense`** (red's air force IS its BARCAP + `gci_ambush`). Air: F-5E
  Tiger II (FC) with 64th/65th aggressor liveries, MiG-21bis + MiG-21MF (VWV) +
  MiG-17F (VWV) for the Constant Peg birds, Mi-8 helos, An-26 transport. Ground/AD:
  SA-2 + SA-3 presets, ZSU-23-4/ZSU-57/S-60/ZU-23 AAA, P-37 Bar Lock EWR,
  Vietnam-pattern light armor (PT-76/T-55) as the simulated enemy army.

Both factions stay **fork-side** (they encode 414th campaign identity; the
upstreaming carve rule from the community-contribution roadmap applies).

---

## 5. The phases arc (authored, P2 tier)

Three exercise periods + the standing Box, riding the same YAML schema as Yankee
Station (`min_turn` + `advance_when: blue_will_below` acceleration):

1. **`week_one` — "Week One: Familiarization"** (emphasis `interdiction`): deep
   classes locked (`factory, power, oil, fuel, ammo, comms, ware, airfield`),
   restricted zones = the Box (Groom 12 NM) + the Tonopah rear ring (8 NM — off-range
   restriction) + the Box's buffer. Fly the corridors, hit the FEBA and the convoys.
2. **`week_two` — "Week Two: Force on Force"** (`min_turn: 6`, emphasis `rollback`):
   Tonopah ring drops, deep classes release except `airfield`; red_tempo
   `ground_offensive: 2` — the aggressor ground push (the flag's scripted
   counterattack), still clamped by the static front.
3. **`final_exam` — "Surge Week: Final Exam"** (`min_turn: 11`, emphasis
   `offensive`): everything releases (airfields too — TTR/Pahute become OCA targets),
   maximum effort. Only the Box remains.
- **The Box never releases** (present in every phase, exactly like Yankee's PRC
  ring): Groom Lake 12 NM — enter it on the real range and you're grounded; here it
  soft-costs political will per the W4 zone-violation economy.

Turn pacing targets the 81-2 detachment: ~13 turns ≈ the 13 missions.

---

## 6. Settings preseed (era + theater fit)

Mirrors Yankee Station's block except:

- `vietnam_naval_gunfire: false` — **NTTR has no sea** (guarded no-op anyway, but
  don't advertise a dead mechanic).
- `vietnam_super_gaggle: true` — Camp Mercury is the besieged-FOB destination.
- `vietnam_arc_light: true` — SAC cells from the off-map spawn.
- Flak gauntlet / convoy interdiction / harassment / FAC / snake-and-nape: **on**
  (§2 table).
- `vietnam_political_will: true`, `vietnam_static_front: true` — the requested core.
- `restrict_weapons_by_date: true` + start date **1981-01-26** → AIM-7F/AIM-9J/L-era
  loadouts fall out of the date gate; JHMCS-era props gated off by §24.
- Mods: `vietnamwarvessels: true` (MiG-17F/MiG-21MF/RF-101B), `ov10a_bronco: true`,
  `high_digit_sams: true` (the two EWR sites fill with the period **P-37 Bar Lock** —
  flipped ON across all five Vietnam-era campaigns 2026-07-02, squadron call; HDS
  Ultimate is on the Required-Mods pages).
- Compressed-theater support-orbit buffers (`aewc/tanker_threat_buffer_min_distance:
  25/20`) — NTTR is small like the Caucasus recast.

---

## 7. Status / open items

- [x] Study + design note (this file)
- [x] Factions ×2
- [x] Campaign YAML (squadrons, routes, phases arc, preseed)
- [x] First-cut `.miz` (script-built from `exercise_vegas_nerve.miz`)
- [x] Wiki campaign pack (`docs/wiki/Red-Flag-81-2-*.md` ×5: briefing / intel / role cards /
  first-three-turns / required mods — carries the 🟡 unflown + first-cut-laydown flags)
- [ ] **Re-point laydown at the real 81-2 `.miz`** (user supplying tonight)
- [ ] Headless validation: campaign loads, front forms, phases parse (CI test run)
- [ ] Balance pass: red economy vs. the 13-turn arc; will-feed weights
- [ ] In-game pass (add checklist row; needs the flown flag: gauntlet over the
  corridors, aggressor GCI slash, Box violation will-drain, Mercury gaggle run)
