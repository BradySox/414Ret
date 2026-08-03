# 414th Baltic Fury Campaign Notes

> ## ✅ BUILT + VALIDATED (2026-07-20)
>
> Both files exist and the campaign loads **end-to-end**: `Campaign.from_file` →
> `load_theater(advanced_iads=True)` builds **16 control points** (4 blue: Nordholz/Bremen/
> Hamburg + the carrier · 12 red incl. 3 inert spare helipad fields), `load_air_wing_config`
> binds **34 squadrons across 11 bases** (the carrier wing keys off `CVN-75 Harry S. Truman`),
> and every IADS/coastal/naval/economy marker reads into `preset_locations`: **11 long-range
> SAM** (9 S-400 battalions + 2 S-300 nodes), **4 MERAD**, **9 SHORAD**, **5 coastal anti-ship**,
> **5 EWR**, **1 missile (Iskander)**, **3-ship Baltic Fleet SAG**, **4× C2 cells** (command
> center + comms + power), **3 factories + 3 ammo**. `iads_network` builds. The `phases:`/
> `victory:` blocks pass the real parsers; all 34 `aircraft_type` strings resolve.
>
> **The `.miz` is HAND-AUTHORED — [`tools/build_baltic_fury_miz.py`](../../../tools/build_baltic_fury_miz.py)
> was a one-time bootstrap** (it reshaped the all-vanilla `red_tide.miz` into the initial
> laydown). The DM built the laydown out in the Mission Editor on 2026-07-20, so **the `.miz`
> is now the source of truth, not the script's tables** — and the script enforces that: `main()`
> **refuses to run** when the miz exists unless you pass `--force`. Corrected 2026-08-02; this
> banner previously said the opposite ("edit the tables and re-run, never hand-edit the miz"),
> which contradicted the guard and mislead a reader into thinking flown ME work was one
> `python tools/…` away from being destroyed.
>
> ⚠️ **`--force` no longer reproduces the bootstrap.** It rebuilds from `red_tide.miz`, which has
> moved on since (road-snapped supply routes + a Haina ammo depot, 2026-08-02), so forcing would
> both discard every ME edit *and* build from a drifted base. If the laydown ever needs
> regenerating, convert to the Enduring/Inherent Resolve **decorate-a-base** pattern first
> (commit the hand-authored miz as `operation_baltic_fury_base.miz`, reduce the tool to an
> additive pass over it). Scoped, not yet built.
>
> **Remaining:** CI lock `tests/fourteenth/test_baltic_fury.py` → sync README/feature docs → the
> DM's in-app New Game eyeball (needs the mods enabled — faction/TGO resolution happens at New
> Game, which headless load can't fully exercise).

## Concept

Modern day (2027). A Russian offensive overran Schleswig-Holstein, seized the Baltic coast,
forced the Danish straits and took **Copenhagen** — then culminated. NATO answers **from the
sea**: a US carrier strike group (CVN-75 Truman) in the German Bight + the 414th's USAF F-22 +
F-15E wing at Nordholz. Break the coastal anti-ship / SAM belt, win the air battle over the
Baltic approaches, roll the enemy up the coast (Lübeck → Rostock → Peenemünde), force the
straits, and **liberate Copenhagen**.

The maritime northern flank Red Tide never fights: Red Tide is the Fulda Gap (S→N); this is the
sea, **west→northeast**. Same *Red Storm Rising* DNA, opposite axis.

- **Map:** GermanyCW · **Date:** 2027-07-17 · **Posture:** blue counter-offensive (enemy
  culminated; NATO out-produces — money 800/400, income ×1.3/×0.7).
- **Blue faction:** `NATO Baltic 2027` (`resources/factions/nato_baltic_2027.json`) — the
  purpose-built coalition, added 2026-08-02. `USA 2020`'s wing and OOB (carrier Rhinos +
  USAF F-22/F-15E; CH USA pack) **plus the two allies the Baltic actually belongs to**:
  - **Sweden** — a NATO member since March 2024, fighting in its home water, and the
    richest CH pack after USA/Russia (42 units). It closes gaps blue genuinely had:
    the **LvS-103** battery (`LvS-103 Rb103A/B` ± Mobile) gives blue its own long-range
    area SAM, and **RBS-15** gives blue a *coastal anti-ship* battery — the mirror of
    red's Bastion/Bal wall, which turns the campaign's signature fight into a
    coastal-vs-coastal duel rather than a one-sided belt-breaking problem. Plus
    RBS-70/90/98 SHORAD, the UndE 23 search radar, **Visby corvettes + CB90 (Strb 90)**
    for archipelago littoral, and Strv 122/123 / Strf 9040 / Archer ashore.
  - **United Kingdom** — the Joint Expeditionary Force, the Northern-Europe framework.
    **Type 45** (area air defence) and **Type 26** (ASW) for the CSG screen, **Sky Sabre**
    (C2 + Giraffe + iLauncher) and Stormer HVM over recaptured fields, Challenger 3 /
    Warrior / Ajax / AS-90 ashore.

  Country is `Combined Joint Task Forces Blue`, and `locales` carries `en_US` + `sv_SE` +
  `en_GB` so §23 gives Swedish and British squadrons their own comms identity and
  nation-appropriate pilot names instead of one shared US voice.

  **The Gripen is the one allied *airframe*** (the rest of the allied contribution is
  ground/naval/AD). `[CH] JAS 39C Gripen` ships **inside the CurrentHill Sweden pack** and is
  gated by `swedishmilitaryassetspack` — **not** by the separate `jas39_gripen` ModSetting,
  which gates the community mod's unrelated `JAS39Gripen` airframe. Preseeding the wrong one
  strips the squadron silently, so the pairing is pinned in the tests.

  **The Finnish Hornet detachment (2026-08-02).** Finland joined NATO in **April 2023** —
  before Sweden — and its F/A-18Cs were bought as interceptors, so BARCAP is the
  historically honest role. **HävLLv 31** (Fighter Squadron 31, Karjalan Lennosto at
  Rissala — the Russia-facing Finnish fighter squadron) sits at **Hamburg**, `primary:
  BARCAP`, `country: Finland`, 8 airframes. Two reasons for that placement:
  - **It closes a real hole.** Blue flew **zero** BARCAP squadrons against red's **six** —
    nothing stood a barrier patrol over blue's own fields. (Anti-ship looked like the other
    candidate gap, but the fork rates the F/A-18C **`Anti-ship: 150`**, so the Harpoon idea
    is not supported by the unit data; its strengths are OCA/Aircraft 730 and BARCAP 555.)
  - **Hamburg is blue's most exposed base** — ~53 km from the nearest red field, vs 137 km
    (Nordholz), 152 km (Bremen), 289 km (the carrier) — and it had **no fast air at all**,
    only A-10s, Apaches and lift.

  Unlike the CH Gripen (an AI-only mod airframe), the **F/A-18C is a full-fidelity module**,
  so this is a *flyable* seat — the reason it went to Finland rather than onto the boat: the
  USN retired legacy Hornets from carrier decks in 2019, so a CVN Hornet squadron in 2027
  would be an anachronism the Finnish one avoids.

  The Gripen is authored as a squadron too, not just a faction entry: **F 17 Blekinge Wing** (the real
  Baltic-facing Gripen wing, Ronneby/Kallinge) forward-deployed to **Nordholz**, `primary:
  DEAD`, `country: Sweden`, 8 airframes. That is a capability fix as much as flavour — blue's
  only other dedicated SEAD/DEAD unit is the carrier's Growler squadron, which is thin against
  an 11-site S-400/S-300 belt, and the CH Gripen's unit yaml carries **`DEAD: 790`**, the
  highest task priority in its own file. Its **RBS-15 Mk4** (160 NM) also gives blue a second
  anti-ship shooter against the Baltic Fleet SAG, and **Taurus KEPD-350** (270 NM) reaches the
  coastal belt from standoff.

  **Mod-gated:** the campaign preseeds `swedishmilitaryassetspack` + `ukmilitaryassetspack`
  alongside the USA pack. A missing pack **strips** those units from the faction (it does
  not fail), so the preseeds are load-bearing — pinned in
  `tests/fourteenth/test_baltic_fury.py`, along with a silent-drop guard that asserts every
  authored unit string resolves (the CH 1.5.0 rename wave is exactly how a contingent would
  quietly empty) and a mods-off guard that the faction degrades to its vanilla core rather
  than crashing.

- **Enemy faction:** `Redfor (Russia) 2020` — unchanged except for one addition. A full
  pack audit on 2026-08-02 (resolving preset-group members and aircraft, not just loose
  unit strings) found it fields **37 of the CH Russia pack's 55** units. The 18 it does not:
  - **13 legacy Soviet armour/artillery** (T-54, T-62M, T-72A/B, BMP-1/1P, BMD-2, BTR-50PK,
    MT-LB, PT-76B, ASU-85, 2S1, 2S3, ZSU-23-4, 9K35) — correctly era-excluded from a *2020*
    faction. Worth revisiting **for this campaign only**: Baltic Fury's premise is that the
    Russian offensive **culminated**, and an army feeding reserve stocks into the line is
    that story told in units. It would need a Baltic-specific red faction — `Redfor (Russia)
    2020` is shared by 4 campaigns (Baltic Fury, Slava Ukraini, Clash of the Titans,
    Graveyard of Empires). **Deliberately not done**; recorded here as the open option.
  - **`[CH] Iskander-K GLCM`** — a genuine gap, now **closed**: red fielded the ballistic
    Iskander-**M** but not the **cruise** variant. Added to the shared faction's `missiles`
    (purely additive, all 4 campaigns headless-verified to still load).
  - 2 non-combat objects (`BMD4_cargo`, `TM62_AT_Mine`) — no unit data, skipped.

  ⚠️ **Counting gotcha for future audits:** `[CH] Iskander-M SRBM` and `SRBM 9K720 Iskander
  HE [CH]` are two display names for the **same** unit (`CHAP_9K720_HE`, from the CH →
  ED-integrated CHAP wave), and faction collections dedupe by unit type — so the missiles
  list reads "4 authored, 3 resolved" and that is correct, not a silent drop. Any
  drop-detector needs `>=` against *distinct units*, not authored-string count.

  On the blue side the equivalent audit found **59 of 60** CH USA units fielded; the sole
  gap is `CH_B-21`, which has no unit yaml and is already tracked as an open faction call
  in the CH-wave adoption backlog. Left open deliberately.
- **Enemy faction:** `Redfor (Russia) 2020` — maritime Russia: coastal anti-ship + Baltic Fleet
  + S-400/BUK-M3; CH Russia pack.
- **Sweden:** neutral (southern Swedish fields left out).

### Verified geography
- Carrier box **`[127353, -868754]`** = 55.0N 6.8E (nearest land field Nordholz @ 100 nm).
- Carrier→Copenhagen 205 nm · carrier→Nordholz 100 nm.
- The only blue↔red supply route is **Hamburg (17) → Lübeck (81)**, so the turn-1 front sits at
  the Lübeck neck and marches up the coastal spine as blue captures each field.

## Order of battle (see the yaml for exact sizes/callsigns)

**Blue** — Carrier CVN-75 (F/A-18E TARCAP/SEAD ×12, F/A-18F Strike/Anti-ship ×10, EA-18G ×6,
E-2D ×2, F/A-18E tanker ×3, SH-60B ×2) · **Nordholz (47)** F-22A ×12 + F-15E ×12 · **Bremen (5)**
E-3A / KC-135 ×2 / KC-135 MPRS ×2 / B-1B ×4 · **Hamburg (17)** A-10C Suite 7 ×8 / AH-64D ×4 /
CH-47F ×2 / C-130J ×2. ~56 combat aircraft.

**Red** — Copenhagen/Kastrup (41) Tu-22M3 anti-ship ×8 + Su-30 ×8 + IL-76 · Rostock/Laage (20)
MiG-31 ×8 + Su-27 ×8 · Peenemünde (25) Su-30 ×8 + Su-24M SEAD ×8 · Parchim (84) MiG-29S ×12 +
Su-25 ×8 · Wismar (108) [CH] Ka-52 ×4 + Mi-24P ×4 + Mi-8 ×4 · Szczecin (50) Tu-95MS ×4 + [CH]
Tu-160M2 ×4 + A-50 + IL-78 ×2 + Su-30 ×8 · Bornholm (33) MiG-29S ×8. ~60 aircraft, defensive
by design (offensive agency = Backfire anti-ship raids + §55 red-intent surges).

> **Airframe note (2026-07-20):** the Flankers are **vanilla `Su-30 Flanker-C`** and the
> interceptors **vanilla `MiG-31 Foxhound`** — NOT the mod `Su-30SM Flanker-H` /
> `MiG-31BM Foxhound`, whose mods (`su30_flanker_h`, `mig31bm_foxhound`) aren't on the curated
> wizard Mods page and would silently drop the squadron if absent (`remove_aircraft`, not
> substitute). Swap them back + preseed those two mods only if the DM confirms both are installed.

## IADS / SAM / coastal / naval belt (the signature)

Networked advanced IADS (`advanced_iads: true`, MANTIS range mode + per-base C2 statics). Built
to the SAM-belt STANDARD:
- **Strategic S-400 → regiment-by-authoring** (multi-battalion single-radar + shared EWR; §60
  doubling OFF for these): hubs at Copenhagen `[127222, -500129]`, Rostock `[-46917, -547933]`,
  Szczecin `[-104437, -377931]`; `SA-20/PMU-1` mid nodes.
- **Coastal anti-ship wall** (`Bastion-P` + `BAL` LBASM, sea-facing — the CSG's gate): Rostock
  `[-21425, -544701]`, Kap Arkona/Rügen `[23897, -452187]`, Usedom `[-49529, -425779]`, Darß
  `[1512, -502398]`, Copenhagen `[131614, -490031]`.
- **Baltic Fleet SAG** (`Russian Navy`) at `[19397, -441610]` — CSG threat + hunt target.
- **Forward MERAD screen** (§60 doubling ON): `SA-11`/`SA-17`/`BUK M3` + `SA-6` across the neck.
- **Point defense** every red base: `SA-15 Tor M2`/`Pantsir-S2`/`SA-19`. **EWR**: `55G6U`/`1L119`/`1L13`.
- **Blue base AD:** `Patriot` + `NASAMS 3` at Nordholz/Bremen; the CSG carries Aegis.
- **§49 SCUD hunt:** one coastal `SS-26 Iskander` at `[-70726, -537596]` (shoot-and-scoot).

## Phases & victory

- **§40 authored arc:** Rollback (*Break the Coastal Wall*) → Interdiction (*Clear the Baltic
  Coast*) → Offensive (*Force the Straits — Liberate Copenhagen*). A **Copenhagen positive-control
  no-strike circle** (`[133729, -489625]`, 22 nm) in phases 1–2, lifted in the offensive phase.
  `advance_when` accelerates on the enemy IADS falling past the min_turn floor.
- **§75 victory:** win = capture Copenhagen (`capture_cps: [Kastrup]`, min_turn 6); lose = lose
  the Nordholz bridgehead (`lose_cps: [Nordholz]`). Stock territory endings remain in addition.
- **Political will:** deliberately OFF (territory + §75 carries the ending).

## Preseeds & mods

`squadron_start_full`, `restrict_weapons_by_date` + `restrict_props_by_date` (2027 gate),
`restrict_weapons_by_stock`, cautious blue auto-planner (`ownfor_autoplanner_aggressiveness: 10`,
`oca_..._min_aircraft_count: 40`), `war_economy` + `fuel_air_readiness`, `red_intent`,
`c2_decapitation_effects`, `campaign_phases`, `mobile_missile_relocation`, `convoy_ambush`,
`artillery_base_harassment` (reach 42 km), `enemy_comms_jamming`, `host_red_scramble` (gated to
"Flash"). Plugins pinned: `mantisiads`, `mobilemissiles`, `convoyambush`, `commsjam`,
`redscramble`, `vietnamops`, `combatsar`. **Mods:** `f22_raptor`, `fa_18efg`, `fa18ef_tanker`,
`usamilitaryassetspack`, `high_digit_sams`, `russianmilitaryassetspack`.

### The Modern Missiles mod — EVALUATED AND REJECTED (2026-08-03)

The DM proposed adopting Nightstorm's **Modern Missiles v1.30** (DCS User Files 3328022) for this
campaign. **Do not adopt it, and do not preseed it.** The readme settles all three questions:

1. **It is an in-place core-file swap, not an asset pack.** It overwrites `Bazar` / `CoreMods` /
   `MissionEditor` in the DCS install root via `.cmd` scripts, keeping the stock clsids — "the
   avionics for the aircraft will still show the old versions", "the mission editor labels them as
   AIM-120B's". So there is **nothing to register**: no `pydcs_extensions` module, no `ModSettings`
   toggle, no wizard checkbox, no faction edit. Retribution cannot see it, and therefore cannot
   gate it per campaign.
2. **It shifts the whole Sidewinder ladder one rung, globally** — "AIM-9L becomes AIM-9X", plus
   "performance improvements to the AIM-9M". `AIM-9L.yaml` is year 1976 and `AIM-9M.yaml` is 1982,
   so it silently defeats §24 date gating exactly where the fork can least afford it: **Red Tide**
   (1988-07-13) and **Desert Storm** (1991-01-17) both resolve 9L/9M as their top Sidewinder, and
   Red Tide is a shipped, flown, balanced build. Un-scoping it means every pilot runs
   `AAM_AIM_9L.cmd` between campaigns. It also breaks IC and needs MP version lockstep.
3. **The payoff here is near zero, because the capability is already in the two packs this
   campaign already requires.** The F-22A pack ships its own `{AIM-120D-3}` (self-contained, no
   annotation) and `F-22A.lua` already frags it in 12 fits; the CJS Super Hornet pack ships
   AIM-120D and AIM-9X2 stores.

**Do NOT "fix" this by re-pointing the Super Hornet fits at the pack's D/9X-2 stores.** Those come
in two flavours and neither is usable here: the `*_AI` ones are labelled **"(AI Only)"**, and the
player-usable ones are labelled **"(Modern Missiles Mod Required)"** — i.e. the CJS pack declares
this very mod as a dependency. Re-pointing would either break the flyable Rhino seats or make the
campaign require the mod, reintroducing everything in (2). The Super Hornet fits stay on
AIM-120C + AIM-9X deliberately.

#### Verified against the installed mod + the live DCS (2026-08-03, DM's machine)

The three points above were reasoned from the readme. They were then checked against the real
files at `E:\DCS World\OVGME MODS\Modern Missiles` — **all three hold verbatim** (the `.cmd`
swap scripts, the in-place overwrite of `Bazar/World/Shapes` + `CoreMods/aircraft/
AircraftWeaponPack/{aim9,aim120}_family.lua` + `MissionEditor/data/images`, the
"mission editor labels them as AIM-120B's" line, and "AIM-9L becomes AIM-9X"). No new clsids
anywhere: it edits ED's *existing* weapon families in place, which is exactly why Retribution
cannot see it.

**A fourth reason emerged, and it is the strongest — the mod is a year stale and enabling it
would DELETE live DCS content.** It ships `VERSION.txt = 2.9.0`; the install is
**2.9.28.26385** (built 2026-07-28), and ED touched both files it replaces within the last two
weeks. The mod's copies are not a superset:

| File | Mod copy | Live | Delta |
| --- | --- | --- | --- |
| `aim9_family.lua` | 1501 lines | **1631** | mod is **130 lines short**, 459 lines differ |
| `aim120_family.lua` | 620 lines | 602 | 500 lines differ |
| `DLZ_Refference.lua` | ships a `Backup/` copy | **does not exist** | ED removed/renamed it |

Diffing the declarations, the live `aim9_family.lua` defines **AIM-9D, AIM-9G and AIM-9H** and
the mod's year-old copy **does not**. Those are the Vietnam-era Sidewinders, and this fork
depends on them directly: `resources/weapons/a2a-missiles/AIM-9{D,G,H}.yaml` register them
(1965 / 1970 / 1972) and `vwv_crusader.lua` + `vwv_crusader_np.lua` frag them on the F-8. So
enabling the mod would remove the definitions out from under the Crusader fits, and DCS
silently strips a store it cannot resolve — the **F-8 flies naked**, the same failure mode §71
documents for `(XW)` fits without their pylon injection.

Bottom line: this is not "a mod we chose not to adopt", it is a mod that **cannot safely be
enabled on this install at all** until its author rebuilds it against current DCS. Re-check the
line counts above before reconsidering it after any mod update.

What *did* come out of the evaluation is a real data fix, applied fork-wide (see
`resources/weapons/a2a-missiles/AIM-120D.yaml`): the packs' AIM-120D / AIM-260A / AIM9X-BLKII /
Mako clsids were **unregistered**, so `register_unknown_weapons` gave them
`introduction_year=None` and `Weapon.available_on` treated them as always-available with no
fallback. Not academic — `F-22A.lua` frags `{AIM-120D-3}` in 12 fits and `{MAKO_A2A_C}` in **all
six** of the Raptor's `Retribution ...` fits, so every F-22A A2A sortie in the eleven campaigns
preseeding the pack carried an ungated AIM-120D and two ungated hypersonic AAMs — including
Clash of the Titans, set in **2006**. Now dated and laddered (C 2018 → D 2019 → 260A 2026 →
Mako 2027).

**AIM-260A is blue's top-end A2A missile — the Mako is cut (DM call 2026-08-03).** The pack's
own payloads put 2× Mako in all six of the Raptor's `Retribution ...` fits; those two stations
now carry **AIM-260A** instead (pylon-legal on stations 5 and 7 per the pack's own `Pylon5` /
`Pylon7` classes), so nothing Retribution plans frags a hypersonic in any campaign.

Mako stays **registered** rather than deleted, because deleting it is not neutral — the store is
still selectable in the payload editor, and an unregistered clsid is ungated in *every* era, so
dropping the file would put an ungated hypersonic back in a 2006 campaign the moment anyone
hand-loaded it. It keeps its 2027 date (after AIM-260A, the less mature of the two) and is simply
never auto-fragged. If the fork ever wants AIM-260A to be a ceiling even a hand-load can't beat,
park Mako's year past every shipped campaign — do not delete the file.

Verified end-to-end through the real `degrade_for_date` path on the Raptor's BARCAP fit:

| Campaign | Date | Raptor carries |
|---|---|---|
| Clash of the Titans | 2006 | 2× AIM-9M + 6× AIM-120B |
| Vegas Nerve | 2011 | 2× AIM-9M + 6× AIM-120B |
| Noisy Cricket | 2019 | 2× AIM-9X + 6× AIM-120D |
| **Baltic Fury / Marianas 2027** | 2027 | **2× AIM-9X + 4× AIM-120D + 2× AIM-260A** |

Guarded by `tests/test_modern_amraam_weapons.py`, which pins that no shipped fit frags Mako, that
the 2027 fit survives the date gate, and that Mako stays registered-and-gated.

---

## Miz generation (`tools/build_baltic_fury_miz.py`)

⚠️ **The miz is the source of truth — the script was a one-time bootstrap.** The DM built the
laydown out in the Mission Editor on 2026-07-20, so `resources/campaigns/operation_baltic_fury.miz`
is authoritative and `main()` **refuses to run** unless you pass `--force` (which would wipe those
edits, and no longer reproduces the bootstrap anyway — it rebuilds from a `red_tide.miz` that has
since moved on). Edit the miz in the ME. The tool's laydown tables are kept in sync with the miz
only so a hypothetical `--force` doesn't reintroduce known-bad placements. (This section used to
claim the opposite; corrected 2026-08-02.)

The bootstrap below is retained as the record of how the laydown was originally derived.

How it works (all conventions read straight from `game/campaignloader/mizcampaignloader.py`):

1. **CP ownership** — `ap.set_blue()` for Nordholz/Bremen/Hamburg, `ap.set_red()` for the 9 red
   fields (Kastrup/Laage/Peenemünde/Parchim/Wismar/Szczecin/Bornholm + the coastal-spine
   objectives Lübeck & Barth), `ap.set_neutral()` for the rest. GermanyCW has 227 airfields but
   only *touched* ones become CPs, so 3 red_tide-touched helipads (Bienenfarm, H FRG 09, H FRG 12)
   survive as **inert red-rear spares** (no squadrons; delete them in the ME if undesired). The
   only blue↔red route is Hamburg→Lübeck, so the FLOT starts at the neck.
2. **Vanilla band markers** — the faction supplies the real mod (CH/HDS) units at generation, so
   the miz stays 100 % vanilla and round-trips through pydcs losslessly. Marker → band:
   `S_300PS_5P85C_ln`→LORAD (S-400), `S_75M_Volhov`→MERAD, `Strela_1_9P31`→SHORAD,
   `x_1L13_EWR`→EWR, `Vulcan`→blue AAA, `MissilesSS.hy_launcher`→coastal anti-ship,
   `MissilesSS.Scud_B`→§49 missile.
3. **Carrier** — a blue `Stennis` ship group named `CVN-75 Harry S. Truman` (the yaml keys the
   wing by that string; drives the §65 comms card). **Fleet SAG** — 3 red `USS_Arleigh_Burke_IIa`
   marker hulls (the loader's naval-target type; faction navy fills in).
4. **Advanced-IADS C2** — `_Command_Center` + `Comms_tower_M` + `GeneratorF` statics co-located at
   each of 4 red hubs (Copenhagen/Rostock/Szczecin/Peenemünde) — the cells §51/§52 key on.
5. **Economy** — `Workshop_A` (factory) + `_Ammunition_depot` (ammo), blue at Bremen/Hamburg, red
   at Rostock/Peenemünde/Copenhagen/Szczecin.
6. **Trigger zones cleared** — Red Tide's scenery/influence zones (named after its CPs, e.g.
   `Haina`) are dropped so the loader's preset-location pass doesn't look up dead control points.

**Finish:** load a New Game (mods enabled) → eyeball top-down (FLOT at the neck, carrier offshore,
belt where intended) → CI test + doc sync. The mods must be enabled for faction/TGO resolution;
headless `load_theater` validates structure but not the mod-backed generation.

## Never author at a control point's raw coordinate (fixed 2026-08-02)

An `Airfield` control point's `position` **is** the DCS airfield reference point — the same point
pydcs uses for a `StartType.Runway` spawn — so anything authored at the raw CP coordinate is put
**on the runway**. The bootstrap's economy/defense tables did exactly that. The DM's ME pass had
already moved the factories and AAA (0.9–3.4 km off their fields), but the **three ammunition
depots were missed** and sat at 0 m from the Hamburg, Peenemünde and Szczecin references. They are
now 1.5 km off each field, on land, on a bearing ≥30° away from every supply road leaving that base
(so they never collide with a convoy forming up). `tools/build_baltic_fury_miz.py`'s tables were
synced to the miz's real positions and carry a warning; the invariant is CI-locked by
`test_no_preset_marker_sits_on_a_runway` in `tests/fourteenth/test_baltic_fury.py` (no preset
marker within 500 m of an airfield reference).

The **supply routes** have the same anchoring — all 10 `supply_routes:` endpoints in the yaml sit
on their airfield reference to under 1 m, which parked every departing convoy on the runway. That
half is fixed **engine-side** rather than in the yaml (see features doc §8, `ConvoyGenerator`):
the generator walks a convoy's spawn back out along the authored corridor until it is 1.5 km clear
of the field, which fixes existing saves on the next regeneration and covers every campaign — Red
Tide has 3 endpoints with the same defect.

### Open: the Peenemünde routes cross open water

Found while fixing the above, **not fixed**. Both supply routes touching Peenemünde run as straight
lines across the Peenestrom/Achterwasser rather than following roads — the first 5 km of the
Peenemünde→Neubrandenburg leg and 6 of the first 8 km of Peenemünde→Szczecin are water. A red
convoy on either would try to drive across a strait. The spawn guard degrades safely here (no land
inside its walk budget ⇒ it leaves the spawn where authored, i.e. no worse than today), but the
routes themselves need a real road re-trace per the "supply lines follow the driveable corridor"
standard (`tools/supply_route_geo.py`).

## References
- Campaign: [`resources/campaigns/operation_baltic_fury.yaml`](../../../resources/campaigns/operation_baltic_fury.yaml)
- Quality bar / patterns: [`414th-red-tide-campaign-notes.md`](414th-red-tide-campaign-notes.md),
  [`414th-sam-site-realism-notes.md`](414th-sam-site-realism-notes.md)
