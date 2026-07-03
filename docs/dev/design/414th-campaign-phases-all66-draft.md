# 414th — Campaign Phases: all-66 Tier-0 draft arcs

**Status:** engine-authoritative (2026-07-01, supersedes the same-day `--lite` draft). Companion
to [`414th-campaign-phases-notes.md`](414th-campaign-phases-notes.md) (spec) and
[`414th-campaign-phases-pilot.md`](414th-campaign-phases-pilot.md) (6-campaign pilot). Generated,
not hand-authored.

> **Note (2026-07-03):** this is a dated snapshot of the generator output. Since it was produced,
> the two standalone Caucasus Vietnam campaigns **Khe Sanh: Operation Niagara** and **Steel Tiger:
> Trail Interdiction** were consolidated into **1968 Yankee Station** and their `.yaml`/`.miz`
> removed, so their rows below no longer correspond to shipped campaigns. The table is left as the
> historical snapshot; re-run the generator (below) to regenerate the current 64-campaign set.

## What this is

A drafted Tier-0 phase arc for **every** base-Retribution campaign, produced by
`tools/campaign_phase_classify.py` (the offline reference implementation of the §3.2 classifier)
run over each campaign's turn-0 **`--engine`** laydown — the real
`GameGenerator → begin_turn_0` pipeline, so ownership, SAM bands, and the air OOB are what a
player's New Game actually generates. A turn-0 snapshot classifies the **opening** phase and
projects the intended arc; it does not simulate turn-by-turn advancement — that is what a
"draft" is.

Reproduce with:

```powershell
python tools\campaign_phase_laydown.py --engine --all > laydown.json
python tools\campaign_phase_classify.py --laydown laydown.json
```

Distribution: **57 open in Rollback, 5 in Air Superiority, 4 in Interdiction**
(`--lite` drafted 55/6/4 — see the flips below).

## How to read the numbers

- **Enemy SAM** is `N sites (Mu)`: N = red TGOs whose `GroupTask` is LORAD/MERAD — exactly the
  set the DEAD planner targets (`degradeiads.py`) — and M = the alive units inside them
  (launchers + radars + support). The floor gate (`ROLLBACK_SAM_FLOOR = 3`) runs on **sites**.
  Note the spec §3.1 originally suggested banding by `IadsRole`; that can't work —
  `IadsRole.SAM` also swallows SHORAD and `IadsRole.EWR` swallows AAA/navy — so the extractor
  bands by TGO `task` instead.
- **Enemy Ftr** counts airframes in squadrons whose primary task is
  BARCAP/TARCAP/Intercept/Escort/Sweep, at full squadron strength (`squadrons_start_full`),
  including faction auto-assigned squadrons.
- The **Consolidation / long-war** heuristic still reads the raw `.miz` neutral-airfield pool
  (`neutral_pool`), because the engine assigns every control point to a side.

## What `--engine` fixed over `--lite`

The lite draft carried three blind spots; all are closed here:

1. **Mod SAMs counted.** The engine reads generated TGOs, not a vanilla-only keyword table —
   e.g. *Northern Guardian* (vs `[CH] Russia 2020`) is now measured for real (verdict: it
   genuinely has only 2 L+M sites and 4 fighters — its Interdiction opening was right after all).
2. **Auto-assigned air visible.** Campaigns with no explicit `squadrons:` block now show their
   real air wing (*Khe Sanh* red reads 8 fighters, not 0; *Caucasus Full* red reads 142).
3. **Generator-filled AA slots counted (new — the pilot never saw this one).** `--lite` only
   reads units authored in the `.miz`, but Retribution *generates* SAM sites into the
   campaign's air-defense TGO slots from the faction. This is why several openings flip below.

Notable reclassifications vs the lite draft:

| Campaign | Lite | Engine | Why |
|---|---|---|---|
| **Khe Sanh: Operation Niagara** | Interdiction | **Rollback** | The generator fills 4 real SA-75/S-125 batteries for the NVA (blind spot 3). The pilot's "Khe Sanh 0 SAM" headline was a lite artifact — see the pilot-note addendum. |
| Gran Polvorin | Air Superiority | **Rollback** | 7 generated L+M sites (lite saw 1 authored unit) |
| Scenic Route / Scenic Route 2 | Air Superiority | **Rollback** | 8 / 12 generated L+M sites |
| Tripoint Hostility | Air Superiority | **Rollback** | 7 generated L+M sites |
| Battle for No Man's Land | Rollback | **Interdiction** | lite's "8 L+M" was keyword pollution (Rapier); engine generates 0 L+M sites and 0 red fighters |
| The Final Countdown II (WWII) | Rollback | **Air Superiority** | lite's "65 L+M" was KS-19 flak matching the keyword table; a 1944 theater has no SAM belt |
| Guam - Mount Barrigada | Rollback | **Air Superiority** | 2 sites < floor; 48 red fighters |
| Operation Aegean Aegis | Rollback | **Air Superiority** | 2 sites < floor; 8 red fighters |

The **floor gate keeps four genuine cases** (Shattered Dagger, No Man's Land, Valley of Rotary,
Northern Guardian — all 0–2 sites), and **Velvet Thunder sits exactly at the floor** (3 SA-2
sites) and keeps Rollback, preserving the pilot's "same era, opposite arc" demonstration —
now vs the permissive-air campaigns instead of vs Khe Sanh.

## Remaining caveats

- A turn-0 snapshot: opening phase + projected arc only, no turn-by-turn simulation.
- Era labels still derive from the YAML date/faction text (*Operation Dynamo*, dateless 1940,
  reads "modern"; label-cosmetic only).
- Generation is seeded randomly per run; site/unit counts can wobble slightly between runs
  (squadron fill and TGO fill draw from pools). Phase verdicts are threshold-based and stable.

## The draft table
| Campaign | Theater | Date | Era | Enemy SAM | Enemy Ftr | Opening | Projected arc | Why |
|---|---|---|---|--:|--:|---|---|---|
| Caucasus - The Tblisi Gap | Caucasus | 1980-09-21 | cold_war | 6 (83u) | 12 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=6; enemy fighters=12; SAM belt present -> DEAD/SEAD rollback; 17 neutral fields -> long war |
| Germany - Crossing the Rubicon | GermanyCW | 1988-07-13 | cold_war | 7 (84u) | 28 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=7; enemy fighters=28; SAM belt present -> DEAD/SEAD rollback; 191 neutral fields -> long war; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Germany - Red Tide | GermanyCW | 1988-07-13 | cold_war | 19 (229u) | 40 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=19; enemy fighters=40; SAM belt present -> DEAD/SEAD rollback; 213 neutral fields -> long war; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Kola Peninsula - Able Archer 83 | Kola | 1983-11-09 | cold_war | 6 (71u) | 38 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=6; enemy fighters=38; SAM belt present -> DEAD/SEAD rollback; 21 neutral fields -> long war |
| Sinai - Operation Gazelle (Yom Kippur War) | Sinai | 1973-10-15 | cold_war | 8 (87u) | 32 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=8; enemy fighters=32; SAM belt present -> DEAD/SEAD rollback; 47 neutral fields -> long war; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Afghanistan - Clash of the Titans | Afghanistan | 2006-01-27 | modern | 5 (60u) | 40 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=5; enemy fighters=40; SAM belt present -> DEAD/SEAD rollback; 16 neutral fields -> long war; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Afghanistan - Graveyard of Empires | Afghanistan | 2002-01-27 | modern | 8 (81u) | 26 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=8; enemy fighters=26; SAM belt present -> DEAD/SEAD rollback; 17 neutral fields -> long war; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Afghanistan - Operation Shattered Dagger | Afghanistan | 2006-04-24 | modern | 0 (0u) | 0 | Interdiction | Interdiction -> Offensive -> Consolidation | enemy L+M SAM=0; enemy fighters=0; SAM < floor + weak enemy air -> skip air-superiority phase; 19 neutral fields -> long war |
| Caucasus - Black Sea | Caucasus | 2004-01-07 | modern | 27 (289u) | 48 | Rollback (IADS) | Rollback -> Interdiction -> Offensive | enemy L+M SAM=27; enemy fighters=48; SAM belt present -> DEAD/SEAD rollback; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Caucasus - Full | Caucasus | 2008-08-01 | modern | 27 (294u) | 142 | Rollback (IADS) | Rollback -> Interdiction -> Offensive | enemy L+M SAM=27; enemy fighters=142; SAM belt present -> DEAD/SEAD rollback |
| Caucasus - Mozdok to Maykop | Caucasus | ? | modern | 6 (71u) | 36 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=6; enemy fighters=36; SAM belt present -> DEAD/SEAD rollback; 18 neutral fields -> long war |
| Caucasus - Multi-Part Russia | Caucasus | 2008-08-01 | modern | 17 (178u) | 108 | Rollback (IADS) | Rollback -> Interdiction -> Offensive | enemy L+M SAM=17; enemy fighters=108; SAM belt present -> DEAD/SEAD rollback |
| Caucasus - Muti-Part Georgia | Caucasus | 1995-06-13 | modern | 13 (132u) | 60 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=13; enemy fighters=60; SAM belt present -> DEAD/SEAD rollback; 14 neutral fields -> long war |
| Caucasus - Northern Russia | Caucasus | 1995-06-13 | modern | 20 (226u) | 106 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=20; enemy fighters=106; SAM belt present -> DEAD/SEAD rollback; 15 neutral fields -> long war |
| Caucasus - Operation Vectron's Claw | Caucasus | 2008-08-08 | modern | 9 (97u) | 36 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=9; enemy fighters=36; SAM belt present -> DEAD/SEAD rollback; 14 neutral fields -> long war; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Caucasus - Slava Ukraini | Caucasus | 2026-02-24 | modern | 6 (79u) | 24 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=6; enemy fighters=24; SAM belt present -> DEAD/SEAD rollback; 16 neutral fields -> long war; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Caucasus - WRL - Battle for Georgia (v1.2) #1.0 - Original Release / #1.1 - Player F15e added / #1.2 - Complete overhaul campaign map and enemy units | Caucasus | 2015-02-02 | modern | 11 (95u) | 24 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=11; enemy fighters=24; SAM belt present -> DEAD/SEAD rollback; 15 neutral fields -> long war |
| Caucasus - WRL - Kutaisi to Vaziani (v1.1) #1.0 - Original Release / #1.1 - Player F15e added | Caucasus | 2019-12-25 | modern | 7 (67u) | 44 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=7; enemy fighters=44; SAM belt present -> DEAD/SEAD rollback; 15 neutral fields -> long war |
| Falklands - Battle for No Man's Land | Falklands | 2001-11-10 | modern | 0 (0u) | 0 | Interdiction | Interdiction -> Offensive -> Consolidation | enemy L+M SAM=0; enemy fighters=0; SAM < floor + weak enemy air -> skip air-superiority phase; 22 neutral fields -> long war |
| Falklands - Gran Polvorin | Falklands | 2006-05-12 | modern | 7 (76u) | 42 | Rollback (IADS) | Rollback -> Interdiction -> Offensive | enemy L+M SAM=7; enemy fighters=42; SAM belt present -> DEAD/SEAD rollback |
| Falklands - Operation Grabthar's Hammer | Falklands | 1999-12-25 | modern | 9 (94u) | 20 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=9; enemy fighters=20; SAM belt present -> DEAD/SEAD rollback; 19 neutral fields -> long war; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Falklands - Retake the Falklands | Falklands | 2002-12-21 | modern | 14 (162u) | 60 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=14; enemy fighters=60; SAM belt present -> DEAD/SEAD rollback; 19 neutral fields -> long war |
| Germany - Northern Guardian | GermanyCW | 2027-07-17 | modern | 2 (25u) | 4 | Interdiction | Interdiction -> Offensive -> Consolidation | enemy L+M SAM=2; enemy fighters=4; SAM < floor + weak enemy air -> skip air-superiority phase; 192 neutral fields -> long war |
| Iraq - Operation Desert Aladeen | Iraq | 2012-05-16 | modern | 6 (66u) | 28 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=6; enemy fighters=28; SAM belt present -> DEAD/SEAD rollback; 13 neutral fields -> long war; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Kola Peninsula - Operation Frostbite (Test Build) | Kola | 2016-06-06 | modern | 12 (138u) | 148 | Rollback (IADS) | Rollback -> Interdiction -> Offensive | enemy L+M SAM=12; enemy fighters=148; SAM belt present -> DEAD/SEAD rollback |
| Kola Peninsula - The Anvil of War | Kola | 2007-05-13 | modern | 8 (98u) | 40 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=8; enemy fighters=40; SAM belt present -> DEAD/SEAD rollback; 17 neutral fields -> long war; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Marianas - Guam - Landing at Agat | MarianaIslands | ? | modern | 6 (70u) | 71 | Rollback (IADS) | Rollback -> Interdiction -> Offensive | enemy L+M SAM=6; enemy fighters=71; SAM belt present -> DEAD/SEAD rollback |
| Marianas - Guam - Mount Barrigada | MarianaIslands | ? | modern | 2 (20u) | 48 | Air Superiority (fighter) | Air Superiority -> Interdiction -> Offensive | enemy L+M SAM=2; enemy fighters=48; no SAM belt but real enemy air -> CAP/OCA/sweep, not SEAD; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Marianas - Pacific Repartee | MarianaIslands | 2006-02-17 | modern | 7 (78u) | 111 | Rollback (IADS) | Rollback -> Interdiction -> Offensive | enemy L+M SAM=7; enemy fighters=111; SAM belt present -> DEAD/SEAD rollback |
| Nevada - Exercise Vegas Nerve | Nevada | 2011-02-24 | modern | 11 (124u) | 20 | Rollback (IADS) | Rollback -> Interdiction -> Offensive | enemy L+M SAM=11; enemy fighters=20; SAM belt present -> DEAD/SEAD rollback; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Nevada - WRL - Battle for Area 51 (v1.1) #1.0 - Original Release / #1.1 - Player F15e added | Nevada | 2022-06-04 | modern | 6 (61u) | 32 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=6; enemy fighters=32; SAM belt present -> DEAD/SEAD rollback; 14 neutral fields -> long war |
| Persian Gulf - Battle of Abu Dhabi | Persian Gulf | ? | modern | 15 (172u) | 48 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=15; enemy fighters=48; SAM belt present -> DEAD/SEAD rollback; 24 neutral fields -> long war |
| Persian Gulf - Operation Noisy Cricket | Persian Gulf | 2019-07-13 | modern | 8 (97u) | 58 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=8; enemy fighters=58; SAM belt present -> DEAD/SEAD rollback; 21 neutral fields -> long war |
| Persian Gulf - Scenic Route | Persian Gulf | 2005-04-26 | modern | 8 (91u) | 70 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=8; enemy fighters=70; SAM belt present -> DEAD/SEAD rollback; 25 neutral fields -> long war |
| Persian Gulf - Scenic Route 2 - Dust To Dust | Persian Gulf | 2005-06-29 | modern | 12 (142u) | 47 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=12; enemy fighters=47; SAM belt present -> DEAD/SEAD rollback; 24 neutral fields -> long war; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Persian Gulf - Scenic Route Merged | Persian Gulf | 2005-06-29 | modern | 18 (210u) | 88 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=18; enemy fighters=88; SAM belt present -> DEAD/SEAD rollback; 19 neutral fields -> long war |
| Persian Gulf - Valley of Rotary | Persian Gulf | 2022-06-13 | modern | 0 (0u) | 0 | Interdiction | Interdiction -> Offensive -> Consolidation | enemy L+M SAM=0; enemy fighters=0; SAM < floor + weak enemy air -> skip air-superiority phase; 27 neutral fields -> long war |
| Persian Gulf - WRL - Operation Noisy Cricket (Redux) | Persian Gulf | 2019-07-13 | modern | 14 (144u) | 54 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=14; enemy fighters=54; SAM belt present -> DEAD/SEAD rollback; 20 neutral fields -> long war |
| Persian Gulf - WRL - Wargames (v1.1) #1.0 - Original Release / #1.1 - Player F15e added | Persian Gulf | 2022-05-15 | modern | 15 (133u) | 64 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=15; enemy fighters=64; SAM belt present -> DEAD/SEAD rollback; 24 neutral fields -> long war; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Sinai - Exercise Bright Star | Sinai | 2025-09-01 | modern | 6 (83u) | 36 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=6; enemy fighters=36; SAM belt present -> DEAD/SEAD rollback; 49 neutral fields -> long war; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Sinai - Exercise Quasar (v1) | Sinai | 2025-09-01 | modern | 17 (233u) | 52 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=17; enemy fighters=52; SAM belt present -> DEAD/SEAD rollback; 43 neutral fields -> long war; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Sinai - Operation Desert Sabre (v1) | Sinai | 2011-01-30 | modern | 45 (601u) | 276 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=45; enemy fighters=276; SAM belt present -> DEAD/SEAD rollback; 20 neutral fields -> long war |
| Sinai - Red Sea Rising | Sinai | 2005-01-11 | modern | 8 (85u) | 36 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=8; enemy fighters=36; SAM belt present -> DEAD/SEAD rollback; 45 neutral fields -> long war; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Syria - Battle for Golan Heights | Syria | ? | modern | 3 (31u) | 36 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=3; enemy fighters=36; SAM belt present -> DEAD/SEAD rollback; 56 neutral fields -> long war |
| Syria - Full Map | Syria | 2012-06-05 | modern | 28 (331u) | 192 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=28; enemy fighters=192; SAM belt present -> DEAD/SEAD rollback; 37 neutral fields -> long war |
| Syria - Into the Hornet's Nest | Syria | 2022-06-04 | modern | 7 (78u) | 36 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=7; enemy fighters=36; SAM belt present -> DEAD/SEAD rollback; 202 neutral fields -> long war |
| Syria - Invasion of the Canary Islands | Syria | 2000-06-01 | modern | 41 (535u) | 87 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=41; enemy fighters=87; SAM belt present -> DEAD/SEAD rollback; 42 neutral fields -> long war |
| Syria - Operation Aegean Aegis | Syria | 2013-04-20 | modern | 2 (23u) | 8 | Air Superiority (fighter) | Air Superiority -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=2; enemy fighters=8; no SAM belt but real enemy air -> CAP/OCA/sweep, not SEAD; 207 neutral fields -> long war |
| Syria - Operation Allied Sword | Syria | 2004-07-17 | modern | 17 (185u) | 92 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=17; enemy fighters=92; SAM belt present -> DEAD/SEAD rollback; 55 neutral fields -> long war |
| Syria - Operation Blackball | Syria | 2006-05-17 | modern | 7 (67u) | 60 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=7; enemy fighters=60; SAM belt present -> DEAD/SEAD rollback; 56 neutral fields -> long war |
| Syria - Operation Peace Spring | Syria | 2019-12-23 | modern | 11 (128u) | 52 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=11; enemy fighters=52; SAM belt present -> DEAD/SEAD rollback; 214 neutral fields -> long war |
| Syria - Operation Syrian Shield | Syria | 2024-06-01 | modern | 11 (138u) | 26 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=11; enemy fighters=26; SAM belt present -> DEAD/SEAD rollback; 205 neutral fields -> long war |
| Syria - Task Force Thunder | Syria | 2009-06-19 | modern | 15 (176u) | 58 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=15; enemy fighters=58; SAM belt present -> DEAD/SEAD rollback; 53 neutral fields -> long war |
| Syria - The Falcon went over the mountain | Syria | 2012-06-01 | modern | 25 (288u) | 34 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=25; enemy fighters=34; SAM belt present -> DEAD/SEAD rollback; 51 neutral fields -> long war; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Syria - The Long Road to H3 | Syria | 2005-06-05 | modern | 21 (253u) | 93 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=21; enemy fighters=93; SAM belt present -> DEAD/SEAD rollback; 53 neutral fields -> long war |
| Syria - Tripoint Hostility | Syria | 2006-08-03 | modern | 7 (79u) | 60 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=7; enemy fighters=60; SAM belt present -> DEAD/SEAD rollback; 50 neutral fields -> long war |
| Syria - WRL - Aleppo Insurgency (v1.1) #1.0 - Original Release / #1.1 - Player F15e added | Syria | 2022-09-07 | modern | 5 (42u) | 0 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=5; enemy fighters=0; SAM belt present -> DEAD/SEAD rollback; 50 neutral fields -> long war |
| Syria - WRL - Assault on Damascus (v1.2) #1.0 - Original Release / #1.1 - Player F15e added / #1.2 - IADS ADDED & Massive Overhaul, Added C130 spawn support at main airbase | Syria | 2022-06-04 | modern | 12 (109u) | 12 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=12; enemy fighters=12; SAM belt present -> DEAD/SEAD rollback; 50 neutral fields -> long war |
| Syria - WRL - Battle For Syria North (v1.2) #1.2 Complete Mission Overhaul - Frontlines Removed - CTLD or C130s are expected for base capture / Consider victory by destroying all airbases. | Syria | 2019-06-04 | modern | 24 (218u) | 60 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=24; enemy fighters=60; SAM belt present -> DEAD/SEAD rollback; 50 neutral fields -> long war |
| The Channel - Operation Dynamo | The Channel | ? | modern | 0 (0u) | 24 | Air Superiority (fighter) | Air Superiority -> Interdiction -> Offensive | enemy L+M SAM=0; enemy fighters=24; no SAM belt but real enemy air -> CAP/OCA/sweep, not SEAD |
| Caucasus - 1968 Yankee Station | Caucasus | 1968-06-13 | vietnam | 21 (228u) | 56 | Rollback (IADS) | Iron Hand -> Steel Tiger -> Offensive | enemy L+M SAM=21; enemy fighters=56; SAM belt present -> DEAD/SEAD rollback; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Caucasus - Khe Sanh: Operation Niagara | Caucasus | 1968-07-15 | vietnam | 4 (42u) | 8 | Rollback (IADS) | Iron Hand -> Steel Tiger -> Offensive -> Consolidation | enemy L+M SAM=4; enemy fighters=8; SAM belt present -> DEAD/SEAD rollback; 15 neutral fields -> long war |
| Caucasus - Steel Tiger: Trail Interdiction | Caucasus | 1968-04-03 | vietnam | 21 (224u) | 56 | Rollback (IADS) | Iron Hand -> Steel Tiger -> Offensive | enemy L+M SAM=21; enemy fighters=56; SAM belt present -> DEAD/SEAD rollback |
| Marianas - Operation Velvet Thunder | MarianaIslands | 1970-11-29 | vietnam | 3 (31u) | 16 | Rollback (IADS) | Iron Hand -> Steel Tiger -> Offensive | enemy L+M SAM=3; enemy fighters=16; SAM belt present -> DEAD/SEAD rollback; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Normandy - From Caen to Evreux | Normandy | 1944-07-04 | wwii | 0 (0u) | 16 | Air Superiority (fighter) | Air Superiority -> Interdiction -> Breakout -> Consolidation | enemy L+M SAM=0; enemy fighters=16; no SAM belt but real enemy air -> CAP/OCA/sweep, not SEAD; 34 neutral fields -> long war; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Normandy - The Final Countdown II | Normandy | 1944-06-06 | wwii | 0 (0u) | 56 | Air Superiority (fighter) | Air Superiority -> Interdiction -> Breakout -> Consolidation | enemy L+M SAM=0; enemy fighters=56; no SAM belt but real enemy air -> CAP/OCA/sweep, not SEAD; 81 neutral fields -> long war; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |

## Next

- Promote the campaigns worth hand-tuning to Tier 1/2 authored arcs (spec §2).
- P0 plumbing (`CampaignPhase` model + `Game` phase state + UI surface) per the spec rollout.
