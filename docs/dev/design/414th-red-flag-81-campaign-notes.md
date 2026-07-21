# 414th — Red Flag 81-2 (Nevada) Campaign Notes

Design and build notes for **Nevada - Red Flag 81-2**
(`resources/campaigns/red_flag_81_2.yaml` + `red_flag_81_2.miz`) — a Retribution
campaign on the NTTR that recreates the **1981 Red Flag exercise war** with the full
**Vietnam mechanics stack** (political will, static front, ROE/phases arc, Vietnam Ops
runtime suite, Vietnam doctrines). The styling/laydown reference is the commercial
**Reflected Simulations "F-4E Red Flag 81-2"** DCS campaign the squadron flies (its
kneeboard idiom is already harvested in `414th-campaign-doc-ideas-harvest.md` §1).

> **Laydown refined against the reference (2026-07-02):** the squadron supplied the
> Reflected 81-2 campaign's 15 mission `.miz` files and the laydown tables were
> re-pointed at the real placements (see §3a for the extraction method and what the
> reference actually showed). The dreamlandresort first cut is superseded; a NEW game
> is required to see the refined laydown.

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

## 3. Laydown (re-pointed at the Reflected reference, 2026-07-02)

Base `.miz` derived from `exercise_vegas_nerve.miz` (same theater, rebuilt marker set,
ownership flipped to the classic Red Flag geometry: Blue in the SE corner, Red holding
the ranges to the NW). **The miz is generated, not hand-edited**:
`tools/build_red_flag_81_2_miz.py` (any recent release pydcs round-trips it; the
laydown tables at the top of the script are the single edit point). Re-run it to
regenerate `resources/campaigns/red_flag_81_2.miz` after a laydown change.

### 3a. What the reference `.miz` set actually showed

Method: pydcs' full object loader rejects the commercial missions (unknown trigger
ids), so all 15 mission files were raw-Lua parsed (`dcs.lua.loads` on the `mission`
table, the `campaign_phase_laydown.py --lite` pattern), every red vehicle/static
group dumped, and positions greedy-clustered (3–4 km) across missions. Findings that
re-shaped the first cut:

- **The array sits ~45 km further north than the first cut guessed.** All red range
  activity concentrates in x ∈ [-297k, -219k], y ∈ [-190k, -115k] (the first cut's
  "Tolicha Peak" complexes at x ≈ -318k were Sarcobatus Flat, too far south).
- **The threat is flak-first, exactly like the campaign's Vietnam framing wants:**
  104 KS-19 100 mm guns in belts with 18 SON-9 Fire Can directors, plus 46 ZSU-23-4
  and 7 ZSU-57-2 — versus exactly **one** full SA-2 site (-270.6k, -182.3k) and one
  SA-3 (-248.5k, -189.0k). The missile array beyond that is **SA-6** (4 Kub sites,
  one a full 11-unit site at -219.5k, -164.1k) and **2 lone SA-8s** — the aggressor
  MUTES emulator set.
- **A dense "Smokey" belt** (100 SA-18 units named Smokey1–10, ~22 positions) covers
  the eastern corridor box x ∈ [-273k, -228k], y ∈ [-129k, -115k] — the GTR-18 Smoky
  SAM field.
- **Four F-86F-dressed mock airfields** (the ranges' famous target dressing): the
  24-Sabre main complex (-267.8k, -162.5k), Tolicha south (-275.0k, -178.7k), the NW
  airfield/EWR complex (-249.5k, -185.8k), and an east complex (-269.4k, -125.9k).
- **The Tolicha Peak complex is the showpiece target area**: SA-2 + three KS-19
  belts + T-55 static array + a train marshalling yard (18 freight vans/locomotives)
  + a 67-truck GAZ-66 park + a 32-tank POL farm (-270.77k, -185.28k).
- 3 × 1L13 EWR positions: deep SW (-296.7k, -169.9k), central GCI heart
  (-263.4k, -151.1k), NW complex (-249.1k, -187.5k).
- T-55/armor target arrays at five spots incl. the 24-unit "RocketTarget" array in
  the Smoky belt (-247.7k, -121.6k).
- No routed red convoys — every reference "convoy" is parked static dressing (the
  campaign's live trail convoys come from §35 `vietnam_convoy_interdiction` instead).

Decisions taken while re-pointing (the loader's marker vocabulary and squadron calls
constrain a 1:1 copy):

- **SA-6 joins the faction** (`SA-6` preset group; markers are Hawk-type in the ME —
  MERAD is MERAD to the loader, the faction presets decide the fill). **SON-9 Fire
  Can + SA-8 Osa join `air_defense_units`** (all vanilla units, all in the
  reference).
- **The Smoky belt reads as SHORAD, not manpads:** the squadron's no-manpads call
  (the Vietnam-faction SA-7 drop) stands, so the belt is represented by SHORAD
  markers (SA-8 fill) at its two densest clusters plus the two real SA-8 positions.
- **Trains/POL/truck parks map to ammo-depot markers** (the loader has no
  train/fuel marker types); the mock airfields map to strike-target markers with
  the factory (blue-block quirk) at the main complex.
- **Blue point defense is AAA-only by loader rule:** `MizCampaignLoader` reads
  MERAD/SHORAD markers from the RED country block only, so the first cut's "Hawk at
  Creech" never actually loaded (pre-existing, found during this pass). Creech gets
  a Vulcan marker; the player faction carries the Hawk preset for purchase.
  **FIXED 2026-07-12:** the loader now walks the BLUE country block for every marker
  class (ships/offshore/missile/coastal/LORAD/MERAD/SHORAD/EWR), and a blue-block
  marker binds to the nearest BLUE control point when one exists (red-block markers
  keep the coalition-agnostic nearest-any convention, which is how blue defenses are
  conventionally authored). A "Hawk at Creech" in the blue block would load today;
  this campaign keeps its Vulcan-marker layout as tuned.
  **COMPLETED 2026-07-20** (Starfire13's upstream #891 review ask — "consistency in
  the use of CJTF Blue and Red"): the loader's last single-block classes now chain
  both blocks too — `factories` was BLUE-only (the "blue-block quirk" above; a sweep
  found 3 shipped red-block factories silently dropped — TblisiGap,
  RetakeTheFalklands, operation_allied_sword — now resurrected), and front-line
  paths / shipping lanes / cp-convoy spawns (blue-only) + the neutral-FOB
  declaration (red-only) chained with zero shipped cross-block instances. The rule
  is total: the block never decides whether an authored object exists; it means
  ownership only for the CP classes and the bounded blue-marker preference.
  Contract-locked in `tests/test_miz_marker_binding.py`.
- **Campaign fabric kept as-is:** CPs, the Mercury↔Tolicha front, FOB positions,
  convoy spawn hints, the SAC off-map spawn, and point-defense AAA at red fields are
  Retribution mechanics the reference (a scripted linear campaign) has no analog
  for.
- Not modeled (dressing the loader can't express): the parked-Sabre statics
  themselves, watchtower/container camps, the 2 live locomotives. Nice-to-have if a
  scenery/dressing mechanism ever lands.

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

All positions below are reference cluster centers (§3a) unless tagged
*campaign fabric*:

- **SA-2** (`S_75M_Volhov` MERAD marker): the one full reference S-75 site at the
  Tolicha Peak complex.
- **SA-3** (`x_5p73_s_125_ln`): the NW airfield/EWR complex SW of TTR.
- **SA-6** (`Hawk ln` MERAD markers ×3 — the loader treats every medium-SAM marker
  type the same; the Hawk type just keeps them distinct in the ME): main mock
  airfield south, Tolicha south, and the TTR SE-approach full site. The faction's
  new `SA-6` preset provides the fill.
- **SHORAD** (`Strela-1 9P31` markers ×4 → faction SA-8 Osa): the two real
  reference SA-8 positions + two stand-ins for the Smoky belt (§3a decision).
- **AAA** (`ZSU_23_4_Shilka` markers ×18 red): eleven reference gun-belt positions
  (Tolicha ×2, mock airfields, NW complex + satellite, central band, Fire Can site,
  refueler camp, the two "FuelAAA" camps) + seven *campaign fabric* point-defense
  sites (red fields, FOB Tolicha, the FEBA corridor) — feeds the §33 flak gauntlet.
  Faction fills mix KS-19/SON-9/S-60/ZU-23/ZSUs.
- **EWR** (`1L13` markers ×3): deep SW, central GCI heart, NW complex (P-37 Bar
  Lock fills when HDS is on).
- **Armor arrays** (`M_1_Abrams` markers ×5): Tolicha T-55 array, NW complex array,
  east mock-airfield armor, and the two Smoky-belt target arrays.
- **Strike targets**: the four mock airfields (`Tech_combine`; `Workshop_A` factory
  at the main complex — **factories must sit in the BLUE country block**, the
  loader only scans blue statics for factories) + TTR industrial (*campaign
  fabric*). **Ammo depots**: Tolicha marshalling yard, Tolicha POL farm, NW truck
  park + Tonopah/Beatty depots (*campaign fabric*).
- **Command center** (`_Command_Center` static): Red Force C2 inside the Groom box
  (hidden until the §15 command-post fog is beaten). *Campaign fabric.*
- **Convoy spawn hints** (`M1043_HMMWV_Armament` pairs) near each CP, as Vegas Nerve.
- Kept from Vegas Nerve: the TTR Invisible-FARP helipad cluster (red helo ground
  spawns), both off-map spawn plane groups (renamed to SAC roles).

### What the reference `.miz` refined (done — see §3a)

The mock airfields (×4, not 1), the SAM emulator sites (SA-2 ×1 / SA-3 ×1 / SA-6 ×3
/ SA-8s — not five SA-2 rings), the flak belts (KS-19/Fire Can-first), tank arrays,
the train marshalling yard + POL farm, and the Smoky belt. The reference has no
moving convoys (all its columns are parked dressing) and no bridges-as-targets, so
nothing to fold there; the mission flow already matches the three-week phases arc.

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
  SA-2 + SA-3 + **SA-6** presets (SA-6 added on reference evidence, §3a),
  KS-19 + **SON-9 Fire Can** + ZSU-23-4/ZSU-57/S-60/ZU-23 AAA, **SA-8 Osa** SHORAD,
  P-37 Bar Lock EWR, Vietnam-pattern light armor (PT-76/T-55) as the simulated
  enemy army.

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
- [x] **Re-point laydown at the real 81-2 `.miz`** (done 2026-07-02 — §3a; faction
  gains SA-6/SON-9/SA-8; needs a NEW game)
- [x] Headless validation: campaign loads, factions resolve (no silent roster
  drops), preset census = tables (5 MERAD / 4 SHORAD / 20 AAA / 3 EWR / 5 armor /
  5 strike / 5 ammo / factory / C2), Mercury↔Tolicha front forms, 3-phase arc
  parses (2026-07-02, worktree venv smoke)
- [ ] Balance pass: red economy vs. the 13-turn arc; will-feed weights
- [ ] In-game pass (add checklist row; needs the flown flag: gauntlet over the
  corridors, aggressor GCI slash, Box violation will-drain, Mercury gaggle run)
