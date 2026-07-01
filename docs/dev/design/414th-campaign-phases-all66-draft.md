# 414th — Campaign Phases: all-66 Tier-0 draft arcs

**Status:** draft (2026-07-01). Companion to
[`414th-campaign-phases-notes.md`](414th-campaign-phases-notes.md) (spec) and
[`414th-campaign-phases-pilot.md`](414th-campaign-phases-pilot.md) (6-campaign pilot). Generated,
not hand-authored.

## What this is

A drafted Tier-0 phase arc for **every** base-Retribution campaign, produced by
`tools/campaign_phase_classify.py` — the offline reference implementation of the §3.2 classifier
run over each campaign's turn-0 `--lite` laydown (ownership + IADS tiers + air OOB, all parsed
from the `.miz` + YAML with no fork pydcs). A turn-0 snapshot classifies the **opening** phase
and projects the intended arc; it does not simulate turn-by-turn advancement — that is what a
"draft" is.

This table also **validates the §3.2 thresholds against all 66 theaters at once** (the "validation
corpus" the spec calls for). Distribution: 55 open in Rollback, 6 in Air Superiority (SAM below
the floor but real enemy fighters), 4 in Interdiction (permissive air — COIN/siege).

## Read the caveats before trusting a row

These are `--lite` fidelity limits; **`--engine` mode closes all three** (real `IadsRole`,
assigned squadrons, loaded factions):

1. **Mod SAMs are undercounted.** The tier table is vanilla-DCS only, so HighDigitSAMs /
   CurrentHill (`[CH] …`) launchers don't count. E.g. *Northern Guardian* (vs `[CH] Russia 2020`)
   reads 2 L+M SAM and mis-opens in Interdiction; its real IADS is dense. Any `[CH]`/mod-pack
   enemy faction is suspect in this table.
2. **Air OOB is blank for auto-assigned squadrons.** Campaigns with no explicit `squadrons:`
   block (e.g. *Khe Sanh*) read `0` enemy fighters; the classifier then leans on the SAM count +
   an "air unknown" assumption.
3. **Era depends on the date/faction fields.** A campaign with no `recommended_start_date` (e.g.
   *Operation Dynamo*, 1940) falls back to "modern". Era only affects cosmetic phase labels, not
   the phase logic.

The opening phase and arc are driven by SAM + air counts, which are correct wherever (1)/(2)
don't bite — i.e. vanilla-unit campaigns with explicit squadrons, which is most of them.

## The draft table

| Campaign | Theater | Date | Era | Enemy SAM | Enemy Ftr | Opening | Projected arc | Why |
|---|---|---|---|--:|--:|---|---|---|
| Caucasus - The Tblisi Gap | Caucasus | 1980-09-21 | cold_war | 21 | 4 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=21; enemy fighters=4; SAM belt present -> DEAD/SEAD rollback; 17 neutral fields -> long war |
| Germany - Crossing the Rubicon | GermanyCW | 1988-07-13 | cold_war | 15 | 28 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=15; enemy fighters=28; SAM belt present -> DEAD/SEAD rollback; 191 neutral fields -> long war; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Germany - Red Tide | GermanyCW | 1988-07-13 | cold_war | 18 | 40 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=18; enemy fighters=40; SAM belt present -> DEAD/SEAD rollback; 213 neutral fields -> long war; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Kola Peninsula - Able Archer 83 | Kola | 1983-11-09 | cold_war | 31 | 38 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=31; enemy fighters=38; SAM belt present -> DEAD/SEAD rollback; 21 neutral fields -> long war |
| Sinai - Operation Gazelle (Yom Kippur War) | Sinai | 1973-10-15 | cold_war | 34 | 32 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=34; enemy fighters=32; SAM belt present -> DEAD/SEAD rollback; 47 neutral fields -> long war; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Afghanistan - Clash of the Titans | Afghanistan | 2006-01-27 | modern | 12 | 36 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=12; enemy fighters=36; SAM belt present -> DEAD/SEAD rollback; 16 neutral fields -> long war; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Afghanistan - Graveyard of Empires | Afghanistan | 2002-01-27 | modern | 17 | 26 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=17; enemy fighters=26; SAM belt present -> DEAD/SEAD rollback; 17 neutral fields -> long war; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Afghanistan - Operation Shattered Dagger | Afghanistan | 2006-04-24 | modern | 0 | 0 | Interdiction | Interdiction -> Offensive -> Consolidation | enemy L+M SAM=0; enemy fighters=0; SAM < floor + weak enemy air -> skip air-superiority phase; 19 neutral fields -> long war |
| Caucasus - Black Sea | Caucasus | 2004-01-07 | modern | 13 | 16 | Rollback (IADS) | Rollback -> Interdiction -> Offensive | enemy L+M SAM=13; enemy fighters=16; SAM belt present -> DEAD/SEAD rollback; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Caucasus - Full | Caucasus | 2008-08-01 | modern | 30 | 40 | Rollback (IADS) | Rollback -> Interdiction -> Offensive | enemy L+M SAM=30; enemy fighters=40; SAM belt present -> DEAD/SEAD rollback |
| Caucasus - Mozdok to Maykop | Caucasus | ? | modern | 12 | 12 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=12; enemy fighters=12; SAM belt present -> DEAD/SEAD rollback; 18 neutral fields -> long war |
| Caucasus - Multi-Part Russia | Caucasus | 2008-08-01 | modern | 24 | 28 | Rollback (IADS) | Rollback -> Interdiction -> Offensive | enemy L+M SAM=24; enemy fighters=28; SAM belt present -> DEAD/SEAD rollback |
| Caucasus - Muti-Part Georgia | Caucasus | 1995-06-13 | modern | 15 | 20 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=15; enemy fighters=20; SAM belt present -> DEAD/SEAD rollback; 14 neutral fields -> long war; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Caucasus - Northern Russia | Caucasus | 1995-06-13 | modern | 21 | 60 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=21; enemy fighters=60; SAM belt present -> DEAD/SEAD rollback; 15 neutral fields -> long war |
| Caucasus - Operation Vectron's Claw | Caucasus | 2008-08-08 | modern | 21 | 32 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=21; enemy fighters=32; SAM belt present -> DEAD/SEAD rollback; 14 neutral fields -> long war; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Caucasus - Slava Ukraini | Caucasus | 2026-02-24 | modern | 7 | 24 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=7; enemy fighters=24; SAM belt present -> DEAD/SEAD rollback; 16 neutral fields -> long war; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Caucasus - WRL - Battle for Georgia (v1.2) #1.0 - Original Release / #1.1 - Player F15e added / #1.2 - Complete overhaul campaign map and enemy units | Caucasus | 2015-02-02 | modern | 24 | 24 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=24; enemy fighters=24; SAM belt present -> DEAD/SEAD rollback; 15 neutral fields -> long war |
| Caucasus - WRL - Kutaisi to Vaziani (v1.1) #1.0 - Original Release / #1.1 - Player F15e added | Caucasus | 2019-12-25 | modern | 15 | 44 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=15; enemy fighters=44; SAM belt present -> DEAD/SEAD rollback; 15 neutral fields -> long war |
| Falklands - Battle for No Man's Land | Falklands | 2001-11-10 | modern | 8 | 0 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=8; enemy fighters=0; SAM belt present -> DEAD/SEAD rollback; 22 neutral fields -> long war |
| Falklands - Gran Polvorin | Falklands | 2006-05-12 | modern | 1 | 14 | Air Superiority (fighter) | Air Superiority -> Interdiction -> Offensive | enemy L+M SAM=1; enemy fighters=14; no SAM belt but real enemy air -> CAP/OCA/sweep, not SEAD |
| Falklands - Operation Grabthar's Hammer | Falklands | 1999-12-25 | modern | 25 | 20 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=25; enemy fighters=20; SAM belt present -> DEAD/SEAD rollback; 19 neutral fields -> long war; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Falklands - Retake the Falklands | Falklands | 2002-12-21 | modern | 5 | 24 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=5; enemy fighters=24; SAM belt present -> DEAD/SEAD rollback; 19 neutral fields -> long war |
| Germany - Northern Guardian | GermanyCW | 2027-07-17 | modern | 2 | 4 | Interdiction | Interdiction -> Offensive -> Consolidation | enemy L+M SAM=2; enemy fighters=4; SAM < floor + weak enemy air -> skip air-superiority phase; 192 neutral fields -> long war |
| Iraq - Operation Desert Aladeen | Iraq | 2012-05-16 | modern | 20 | 28 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=20; enemy fighters=28; SAM belt present -> DEAD/SEAD rollback; 13 neutral fields -> long war; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Kola Peninsula - Operation Frostbite (Test Build) | Kola | 2016-06-06 | modern | 32 | 20 | Rollback (IADS) | Rollback -> Interdiction -> Offensive | enemy L+M SAM=32; enemy fighters=20; SAM belt present -> DEAD/SEAD rollback |
| Kola Peninsula - The Anvil of War | Kola | 2007-05-13 | modern | 21 | 40 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=21; enemy fighters=40; SAM belt present -> DEAD/SEAD rollback; 17 neutral fields -> long war; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Marianas - Guam - Landing at Agat | MarianaIslands | ? | modern | 6 | 24 | Rollback (IADS) | Rollback -> Interdiction -> Offensive | enemy L+M SAM=6; enemy fighters=24; SAM belt present -> DEAD/SEAD rollback |
| Marianas - Guam - Mount Barrigada | MarianaIslands | ? | modern | 6 | 16 | Rollback (IADS) | Rollback -> Interdiction -> Offensive | enemy L+M SAM=6; enemy fighters=16; SAM belt present -> DEAD/SEAD rollback; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Marianas - Pacific Repartee | MarianaIslands | 2006-02-17 | modern | 12 | 47 | Rollback (IADS) | Rollback -> Interdiction -> Offensive | enemy L+M SAM=12; enemy fighters=47; SAM belt present -> DEAD/SEAD rollback |
| Nevada - Exercise Vegas Nerve | Nevada | 2011-02-24 | modern | 32 | 20 | Rollback (IADS) | Rollback -> Interdiction -> Offensive | enemy L+M SAM=32; enemy fighters=20; SAM belt present -> DEAD/SEAD rollback; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Nevada - WRL - Battle for Area 51 (v1.1) #1.0 - Original Release / #1.1 - Player F15e added | Nevada | 2022-06-04 | modern | 24 | 32 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=24; enemy fighters=32; SAM belt present -> DEAD/SEAD rollback; 14 neutral fields -> long war; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Persian Gulf - Battle of Abu Dhabi | Persian Gulf | ? | modern | 37 | 16 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=37; enemy fighters=16; SAM belt present -> DEAD/SEAD rollback; 24 neutral fields -> long war; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Persian Gulf - Operation Noisy Cricket | Persian Gulf | 2019-07-13 | modern | 25 | 58 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=25; enemy fighters=58; SAM belt present -> DEAD/SEAD rollback; 21 neutral fields -> long war |
| Persian Gulf - Scenic Route | Persian Gulf | 2005-04-26 | modern | 1 | 30 | Air Superiority (fighter) | Air Superiority -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=1; enemy fighters=30; no SAM belt but real enemy air -> CAP/OCA/sweep, not SEAD; 25 neutral fields -> long war |
| Persian Gulf - Scenic Route 2 - Dust To Dust | Persian Gulf | 2005-06-29 | modern | 1 | 23 | Air Superiority (fighter) | Air Superiority -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=1; enemy fighters=23; no SAM belt but real enemy air -> CAP/OCA/sweep, not SEAD; 24 neutral fields -> long war |
| Persian Gulf - Scenic Route Merged | Persian Gulf | 2005-06-29 | modern | 4 | 88 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=4; enemy fighters=88; SAM belt present -> DEAD/SEAD rollback; 19 neutral fields -> long war |
| Persian Gulf - Valley of Rotary | Persian Gulf | 2022-06-13 | modern | 0 | 0 | Interdiction | Interdiction -> Offensive -> Consolidation | enemy L+M SAM=0; enemy fighters=0; SAM < floor + weak enemy air -> skip air-superiority phase; 27 neutral fields -> long war |
| Persian Gulf - WRL - Operation Noisy Cricket (Redux) | Persian Gulf | 2019-07-13 | modern | 38 | 54 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=38; enemy fighters=54; SAM belt present -> DEAD/SEAD rollback; 20 neutral fields -> long war |
| Persian Gulf - WRL - Wargames (v1.1) #1.0 - Original Release / #1.1 - Player F15e added | Persian Gulf | 2022-05-15 | modern | 27 | 64 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=27; enemy fighters=64; SAM belt present -> DEAD/SEAD rollback; 24 neutral fields -> long war; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Sinai - Exercise Bright Star | Sinai | 2025-09-01 | modern | 27 | 32 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=27; enemy fighters=32; SAM belt present -> DEAD/SEAD rollback; 49 neutral fields -> long war; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Sinai - Exercise Quasar (v1) | Sinai | 2025-09-01 | modern | 38 | 52 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=38; enemy fighters=52; SAM belt present -> DEAD/SEAD rollback; 43 neutral fields -> long war |
| Sinai - Operation Desert Sabre (v1) | Sinai | 2011-01-30 | modern | 59 | 92 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=59; enemy fighters=92; SAM belt present -> DEAD/SEAD rollback; 20 neutral fields -> long war |
| Sinai - Red Sea Rising | Sinai | 2005-01-11 | modern | 16 | 36 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=16; enemy fighters=36; SAM belt present -> DEAD/SEAD rollback; 45 neutral fields -> long war; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Syria - Battle for Golan Heights | Syria | ? | modern | 11 | 36 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=11; enemy fighters=36; SAM belt present -> DEAD/SEAD rollback; 56 neutral fields -> long war |
| Syria - Full Map | Syria | 2012-06-05 | modern | 7 | 72 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=7; enemy fighters=72; SAM belt present -> DEAD/SEAD rollback; 37 neutral fields -> long war |
| Syria - Into the Hornet's Nest | Syria | 2022-06-04 | modern | 56 | 36 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=56; enemy fighters=36; SAM belt present -> DEAD/SEAD rollback; 202 neutral fields -> long war |
| Syria - Invasion of the Canary Islands | Syria | 2000-06-01 | modern | 63 | 87 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=63; enemy fighters=87; SAM belt present -> DEAD/SEAD rollback; 42 neutral fields -> long war; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Syria - Operation Aegean Aegis | Syria | 2013-04-20 | modern | 13 | 8 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=13; enemy fighters=8; SAM belt present -> DEAD/SEAD rollback; 207 neutral fields -> long war |
| Syria - Operation Allied Sword | Syria | 2004-07-17 | modern | 3 | 44 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=3; enemy fighters=44; SAM belt present -> DEAD/SEAD rollback; 55 neutral fields -> long war |
| Syria - Operation Blackball | Syria | 2006-05-17 | modern | 7 | 12 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=7; enemy fighters=12; SAM belt present -> DEAD/SEAD rollback; 56 neutral fields -> long war |
| Syria - Operation Peace Spring | Syria | 2019-12-23 | modern | 27 | 52 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=27; enemy fighters=52; SAM belt present -> DEAD/SEAD rollback; 214 neutral fields -> long war |
| Syria - Operation Syrian Shield | Syria | 2024-06-01 | modern | 14 | 32 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=14; enemy fighters=32; SAM belt present -> DEAD/SEAD rollback; 205 neutral fields -> long war |
| Syria - Task Force Thunder | Syria | 2009-06-19 | modern | 16 | 20 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=16; enemy fighters=20; SAM belt present -> DEAD/SEAD rollback; 53 neutral fields -> long war |
| Syria - The Falcon went over the mountain | Syria | 2012-06-01 | modern | 32 | 12 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=32; enemy fighters=12; SAM belt present -> DEAD/SEAD rollback; 51 neutral fields -> long war; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Syria - The Long Road to H3 | Syria | 2005-06-05 | modern | 7 | 84 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=7; enemy fighters=84; SAM belt present -> DEAD/SEAD rollback; 53 neutral fields -> long war |
| Syria - Tripoint Hostility | Syria | 2006-08-03 | modern | 1 | 20 | Air Superiority (fighter) | Air Superiority -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=1; enemy fighters=20; no SAM belt but real enemy air -> CAP/OCA/sweep, not SEAD; 50 neutral fields -> long war |
| Syria - WRL - Aleppo Insurgency (v1.1) #1.0 - Original Release / #1.1 - Player F15e added | Syria | 2022-09-07 | modern | 33 | 0 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=33; enemy fighters=0; SAM belt present -> DEAD/SEAD rollback; 50 neutral fields -> long war |
| Syria - WRL - Assault on Damascus (v1.2) #1.0 - Original Release / #1.1 - Player F15e added / #1.2 - IADS ADDED & Massive Overhaul, Added C130 spawn support at main airbase | Syria | 2022-06-04 | modern | 38 | 12 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=38; enemy fighters=12; SAM belt present -> DEAD/SEAD rollback; 50 neutral fields -> long war |
| Syria - WRL - Battle For Syria North (v1.2) #1.2 Complete Mission Overhaul - Frontlines Removed - CTLD or C130s are expected for base capture / Consider victory by destroying all airbases. | Syria | 2019-06-04 | modern | 33 | 60 | Rollback (IADS) | Rollback -> Interdiction -> Offensive -> Consolidation | enemy L+M SAM=33; enemy fighters=60; SAM belt present -> DEAD/SEAD rollback; 50 neutral fields -> long war |
| The Channel - Operation Dynamo | The Channel | ? | modern | 0 | 8 | Air Superiority (fighter) | Air Superiority -> Interdiction -> Offensive | enemy L+M SAM=0; enemy fighters=8; no SAM belt but real enemy air -> CAP/OCA/sweep, not SEAD |
| Caucasus - 1968 Yankee Station | Caucasus | 1968-06-13 | vietnam | 21 | 68 | Rollback (IADS) | Iron Hand -> Steel Tiger -> Offensive | enemy L+M SAM=21; enemy fighters=68; SAM belt present -> DEAD/SEAD rollback |
| Caucasus - Khe Sanh: Operation Niagara | Caucasus | 1968-07-15 | vietnam | 0 | 0 | Interdiction | Steel Tiger -> Offensive -> Consolidation | enemy L+M SAM=0; enemy fighters=0; SAM < floor + weak enemy air -> skip air-superiority phase; 15 neutral fields -> long war |
| Caucasus - Steel Tiger: Trail Interdiction | Caucasus | 1968-04-03 | vietnam | 21 | 68 | Rollback (IADS) | Iron Hand -> Steel Tiger -> Offensive | enemy L+M SAM=21; enemy fighters=68; SAM belt present -> DEAD/SEAD rollback |
| Marianas - Operation Velvet Thunder | MarianaIslands | 1970-11-29 | vietnam | 12 | 16 | Rollback (IADS) | Iron Hand -> Steel Tiger -> Offensive | enemy L+M SAM=12; enemy fighters=16; SAM belt present -> DEAD/SEAD rollback; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Normandy - From Caen to Evreux | Normandy | 1944-07-04 | wwii | 0 | 16 | Air Superiority (fighter) | Air Superiority -> Interdiction -> Breakout -> Consolidation | enemy L+M SAM=0; enemy fighters=16; no SAM belt but real enemy air -> CAP/OCA/sweep, not SEAD; 34 neutral fields -> long war; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |
| Normandy - The Final Countdown II | Normandy | 1944-06-06 | wwii | 65 | 56 | Rollback (IADS) | Rollback -> Interdiction -> Breakout -> Consolidation | enemy L+M SAM=65; enemy fighters=56; SAM belt present -> DEAD/SEAD rollback; 81 neutral fields -> long war; peer air (symmetric fighters) -> 'air won' gates on air+IADS both |

## Next

- Re-run `python tools/campaign_phase_classify.py --json` after `campaign_phase_laydown.py
  --engine` to regenerate this table from authoritative numbers (fixes caveats 1-2).
- Promote the campaigns worth hand-tuning to Tier 1/2 authored arcs (spec §2).
