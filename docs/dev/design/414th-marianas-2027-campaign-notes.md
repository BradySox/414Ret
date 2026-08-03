# Marianas — Second Island Chain (2027)

**Status:** BUILT + headless-verified 2026-08-02. CI-locked in
`tests/fourteenth/test_marianas_2027.py` (23 tests). Needs an in-game pass —
checklist **T5**. NEW game required.

The 414th's modern-day China campaign, and the answer to "can DCS's current maps host a
high-scale fight against China?"

---

## Why Marianas, and why nothing else

DCS ships **no Chinese terrain** — no Taiwan, no South China Sea, no mainland. So a China
war can only be fought where China would have to come to *us*, and exactly one map is that
place with **zero fiction required**: the Marianas. Guam is the Second Island Chain,
Andersen AFB is the airfield the PLA Rocket Force was built to range, and Apra Harbor is
where the fleet ties up. The DF-26 is nicknamed the "Guam killer" for a reason.

The alternatives were weighed and rejected as campaign homes:

| Map | Verdict |
|---|---|
| **Marianas** | ✅ Real geography, real target set, real belligerents. |
| Persian Gulf | ◐ Best campaign real estate on the list, but needs a PLAN-expeditionary fiction. |
| South Atlantic | ◐ Right *shape* (island chain, carrier vs land-based anti-ship), wrong hemisphere. |
| Afghanistan | ◐ The only map that borders China; no credible at-scale PLA story. |
| Nevada | ◐ Red Flag with PLA aggressors — training, not a war. |
| Syria / Sinai / Iraq / Kola / GermanyCW / Caucasus | ✖ No story at all. |

**The hard limit to remember:** the mainland is unreachable, so this is by construction an
*expeditionary* war. That is a feature here — it makes the campaign a defense-of-Guam and
roll-back fight rather than an invasion nobody could stage.

---

## What this forks, and why it is a fork rather than an edit

Fuzzle's **Marianas - Pacific Repartee** (`pacific_repartee.yaml`, US Navy 2005 vs China
2010) is the only pre-existing China campaign. A headless audit on 2026-08-02 found it
loads clean and furnishes properly — 15 CPs, 106 TGOs, ~590 units, the `ea6b_prowler`
preseed resolving — but it is not a modern fight, and six defects block it from becoming
one:

1. **Red air does not modernize with the faction.** Airframes are hardcoded per squadron,
   so swapping the enemy to `China 2020` upgrades the ground and naval kit (HQ-22, HQ-17A,
   LD-3000, Type 052D/054B/056A/022) and leaves the air force flying **J-7B** — a 1960s
   MiG-21 copy — into a 2020s war.
2. **No red AEW&C exists.** Both China factions declare the KJ-2000; nothing fielded it.
3. **165 red airframes vs 62 blue.** Six carrier squadron blocks omitted `size:` and
   silently defaulted to 12 each — 72 J-15s across three carriers.
4. **No `missile`-category TGO anywhere**, so the pack's DF-21D / CJ-10 / YJ-12B are never
   placed and §49's shoot-and-scoot has nothing to hunt.
5. **Blue is 2005** — F-14B, Hornet Lot 20, A-6E tanker, S-3B, AH-1W.
6. **Zero fork-feature preseeds** — no `plugins:` block at all, and §49 / §63 / §78 / §59
   all off.

Forking rather than editing keeps Fuzzle's 2005 scenario intact (and keeps the fork's copy
convergent with upstream's), which is the campaign-ownership model the wiki's *Campaign
maintenance* page asks for.

The **laydown** is inherited wholesale — `marianas_2027.miz` is generated from
`pacific_repartee.miz` by `tools/build_marianas_2027_miz.py`, which is the source of truth
for the *edits* only. **Never hand-edit the miz; re-run the tool.** Every unit in the source
is vanilla, so pydcs round-trips it losslessly (the mod-unit caveat does not apply).

---

## The premise inversion

Repartee's story is a lone carrier group retaking a Guam that China already holds. That caps
the campaign at **three blue CPs and no runway**, which in turn caps its scale: every blue
airframe has to be carrier-capable, so there is no place for the aircraft that would actually
fight this war — B-1s, F-15Es, KC-135s, E-3s.

This campaign inverts it. **Guam is American soil and holds**; the PLA took Rota, Tinian and
Saipan and pushed up the northern chain, and the war is fought northward. That buys:

- **Andersen AFB (194 parking slots)** — the only ramp on the map that can base a heavy
  wing, and the historically correct hub.
- A real south→north axis of advance across ~200 km of water: Guam → Rota → Tinian/Saipan →
  the northern chain, ending at the isolated Marine detachment on Farallon de Pajaros
  (FOB Uracus), which Repartee already authored and which becomes the campaign's far objective.
- 18 CPs instead of 15, and an honest offensive ratio (**158 blue vs 98 red airframes**).

---

## The laydown had to be re-seated (DM finding, 2026-08-02)

The first cut inverted the premise but left the fleet where Fuzzle put it, and that was
wrong in a way that only shows on the map. Repartee's story is a lone CSG fighting
**south** to retake a Chinese Guam, so its carrier group starts at the **far north** of
the chain and FOB Uracus (781 km north) is blue's toehold. Flip Guam blue without moving
any of that and **blue holds both ends with red sandwiched between them** — which is
exactly what the DM reported.

Three edits fix the axis, and they are now encoded in the build tool rather than left as
hand edits:

| Group | From | To |
|---|---|---|
| Naval-1 (CVN-74) | (824, 199) km | **(−54, −111)** — SW of Guam |
| Naval-2 (LHA-1) | (840, 185) km | **(−102, −70)** — SW of Guam |
| FOB Uracus | BLUE block | **RED** — the northern chain is red depth, not a blue island |
| Naval-18, Naval-27 | scattered | pulled in as the CSG's screen |

A second problem was underneath it: **red's fleet was parked in its own deep rear** —
three carrier groups at 398/545/679 km and two LHAs at 511/523 km, i.e. 220–500 km
*behind* the islands the player has to retake. They could not contest anything, and
blue's B-1Bs would have flown 400–680 km to reach them. The PLAN groups are now in the
Guam–Saipan corridor: carriers at 200/230/290 km (≈300 km off Guam — inside J-15 and
H-6J reach, and reachable by blue), amphibious groups on the lodgements they landed
(off Rota at 95 km, off Tinian/Saipan at 150 km), and the 18-hull escort screen spread
across 60–330 km instead of trailing out to 854 km.

Result, south → north: blue occupies −102…+11 km (LHA · escorts · CVN · Guam's three
airfields); red occupies 60…781 km unbroken. `test_no_blue_base_sits_behind_the_red_chain`
locks it.

## Two dormant airfields, and the loader trap that hid them

The Marianas map has **8 airfields**; Repartee used 4. The other four were `NEUTRAL`, and a
NEUTRAL airfield is **not** a control point — it is dropped entirely:

```python
# MizCampaignLoader.control_points
if airport.is_blue() or airport.is_red() or airport.is_neutral():
```

pydcs's `Airport.is_neutral()` returns **False** for a NEUTRAL coalition, so the guard is
really "blue or red", and a NEUTRAL field silently ceases to exist. (Neutral control points
are real in this engine, but they are declared explicitly via `NEUTRAL_FOB_UNIT_TYPE` — never
inferred from an airport.)

So the build tool declares them:

- **Rota Intl → RED** (9 slots): 90 km off Guam — the red strike field pointed at Andersen.
- **Pagan Airstrip → RED** (3 slots): extends the chain north alongside the existing FOB Pagan.
- **Olf Orote → BLUE** (4 slots): the Guam OLF, one small Harrier det.
- **North West Field stays NEUTRAL** deliberately — pydcs reports it with **zero runways**,
  so it can host no fixed wing. A guard test pins this so a future edit does not "helpfully"
  activate it.

Because Rota was never owned, it carries **no authored garrison of any kind** — so the tool
also adds one medium-range SAM marker there, or the red field nearest Guam would be naked.

---

## The PLARF hunt (the campaign's signature)

Three `MissilesSS.Scud_B` markers in the red block — the loader's missile-site convention —
on **Rota, Tinian and Saipan**. The red faction's own roster fills them (China 2020 declares
DF-21D, CJ-10 and YJ-12B), §49 `mobile_missile_relocation` makes them shoot and scoot between
recon passes, and §3 `concealed_enemy_forces` means an un-scouted site draws a dashed
"suspected activity" circle rather than an exact marker. Together that is an actual hunt: the
launcher is never quite where the last photo froze it.

**Why nothing north of Saipan.** The Marianas landmap only covers **Guam, Rota, Tinian and
Saipan** — Anatahan, Pagan, Agrihan and Uracus are all `is_in_sea` as far as
`ConflictTheater.is_on_land` is concerned. This is a pre-existing property of the terrain
data inherited from Repartee (whose four FOBs all sit on those islands), not something this
campaign introduced, and it is worth knowing before authoring anything ground-related up
there. It also happens to be the right threat picture anyway: a launcher 500 km up the chain
ranges nothing that matters, while Rota/Tinian/Saipan range Guam and the carrier group.

Every authored marker position is validated against the real landmap by the build tool, which
**raises** rather than degrading if it cannot find land — the same fail-loudly posture as the
scenery-target checker.

---

## Order of battle

**BLUE — USA 2020** (164 airframes / 23 squadrons)

| Base | Squadrons |
|---|---|
| Andersen AFB (194 slots) | **F-22A ×8 BARCAP** · F-15C ×10 BARCAP · F-15E ×12 Strike · F-16CM ×12 SEAD · **B-1B ×6 Anti-ship** · E-3A ×3 · **KC-135 ×4 (boom) + KC-135 MPRS ×2 (drogue)** · **C-130J-30 ×4 Transport** |
| Antonio B. Won Pat Intl (23) | F/A-18C ×12 BARCAP · A-10C II ×8 CAS |
| Olf Orote (4) | AV-8B ×4 BAI |
| CVN (Naval-1) | F/A-18E ×12 BARCAP · **F/A-18C ×12 BARCAP** · F/A-18F ×10 Anti-ship · F/A-18E ×8 SEAD · **EA-18G ×5 (VAQ-136)** · **F/A-18E Tanker ×4** · E-2D ×4 · SH-60B ×4 |
| LHA (Naval-2) | AV-8B ×8 BAI · AH-64D ×6 CAS · UH-60A ×6 Transport |

### Guam must not start under a SAM umbrella

A DM screenshot of turn 1 showed Guam blanketed by overlapping red rings. Measured:
**13 of 31 red sites covered Andersen or the carrier group.** Two of this campaign's own
changes had compounded — an HQ-22 pinned on Rota, and 250 km hulls put in the corridor.

The governing number is that **Guam→Saipan is 205 km while the HHQ-9 reaches 250 km**, so
a modern PLAN group anywhere in the corridor covers Guam by construction. The fix is
placement and composition, not capability:

| | Before | After |
|---|---|---|
| Rota (**75 km** from Andersen) | HQ-22, 170 km ring | **HQ-7 point defence** (marker re-banded SHORT) |
| Tinian (175 km) | S-300PMU-2, 200 km | **HQ-22, 170 km** — stops 5 km short of Guam |
| Scattered ship markers | heavy preset, 250 km | **inshore preset only** (054A/054B + 052B) |

**No land SAM site covers Guam any more**, and total coverage is down to **3 of 30** —
all three being escorts of the two amphibious groups, which draw from `naval_units` and
so still carry HHQ-9 hulls. Those are mobile and killable rather than a fixed wall, and
an amphibious group having real air defence is correct; leaving them is deliberate.

Third `ground_forces` rule, learned here: **naval groups cannot be pinned at all.**
`generate_ships` calls `random_group_for_task(GroupTask.NAVY)` and never consults the
block, so ship composition is set purely by *which Navy presets the faction registers* —
and registering two makes every scattered group a coin flip. Exactly one is registered.

Fourth: **a preset must fill every layout slot it wants to control.** A frigates-only
escort preset leaves the Naval Group layout's Destroyer×2 slot empty,
`has_unit_for_layout_group` fills it from the roster, and the roster's destroyers are the
250 km hulls — so the "light" group came back out at 250 km. The Type 052B (30 km) is in
the preset for that reason.

### Ring *size* is its own constraint, separate from coverage

A second DM screenshot, after the coverage fix, still read as a wall of red. Measuring
the rings rather than just their coverage explained it: **13 of 30 red rings were
250 km**. Only two actually contained Andersen — but Guam→Saipan is 205 km, so a single
HHQ-9 group covers a third of the theatre, and thirteen overlapping ones are simply an
unreadable map. Eight of those were self-inflicted: scattered surface markers pinned to
the heavy preset.

Final shape: **every ship marker is pinned to the inshore escort preset**, and the
area-defence destroyers stay concentrated with the carrier and LHA groups (which draw
from `naval_units`, not from a marker). 250 km rings **13 → 4**; 18 of the 30 rings are
now 45 km. The heavy `Chinese Navy 2027` preset was deleted rather than left registered
and unused — an unreferenced Navy preset is a live hazard, because any future unpinned
marker would coin-flip onto it.

Still covering Andersen: the two amphibious groups' own escorts (101 and 175 km out).
Those come from `LhaGroundObjectGenerator` and cannot be pinned; clearing them means
either stripping the HHQ-9 hulls from the roster entirely or moving the LHAs off the
lodgements they landed on. Left deliberately.

Note the three markers next to Guam (`Naval-17/18/27`) are unpinned **on purpose**: a
ship marker prefers a blue control point, so those generate the US carrier group's own
screen from USA 2020.

### The PLAN fleet had to be rebuilt around the HHQ-9 shooters

A DM look at the red ships found carrier groups screened by **Type 022 missile boats
and Type 056A corvettes**. The cause is the stock preset: `Chinese-Navy.yaml` supplies
Type 052C / 052B / 054A, and those satisfy the Naval Group layout's **Frigate ×2 /
Destroyer ×2** slots outright — so `has_unit_for_layout_group` never fills from the
faction roster and the CurrentHill **Type 055 and Type 052D never appear at all**,
despite being the only Chinese hulls with a long-range area SAM.

Measured air-defence reach:

| Hull | Reach | | Hull | Reach |
|---|---|---|---|---|
| **Type 055** | **250 km** | | Type 054A | 45 km |
| **Type 052D** | **250 km** | | Type 052B | 30 km |
| Type 052C | 150 km | | Type 056A | **8 km** |
| | | | Type 022 | **4 km** |

So a task group could bottom out at 4 km of air defence. New preset
`resources/groups/Chinese-Navy-2027.yaml` is built on Type 055 + Type 052D (Destroyer
slot) and Type 054B + Type 054A (Frigate slot), and `China 2027` drops the littoral
Type 022 / Type 056A and the superseded Type 052B from `naval_units` so they cannot be
drafted as blue-water escorts at all. Every red hull now carries ≥45 km, with the
HHQ-9 shooters at 250 km — a PLAN group is an area-denial problem to be rolled back,
not flown around. `test_the_plan_fleet_is_built_on_long_range_sam_shooters` locks it.

**Squadrons start full** (`squadron_start_full: true`). Come-as-you-are: the war opened
with a missile salvo on Guam, and with no land front the player cannot trade time for
mass. Note the key is **singular** — the Theater wizard page reads
`s.get("squadron_start_full", ...)` even though its own field is `squadrons_start_full`,
so a plural typo silently does nothing. Pinned by a test.

### The Raptor det, and the data gap it exposed

Andersen is the real-world F-22 rotation base and the Raptor is the one blue airframe
that beats a J-11A or J-15 on merit rather than on numbers, so the wing carries an
**8-ship det** (`f22_raptor` preseeded). The **F-15C squadron stays alongside it**,
trimmed 12 → 10 rather than replaced: the F-22 is a mod, and without it blue would
otherwise have no air-superiority arm at all. Same safety pattern as the carrier's
legacy Hornet squadron, and guard-tested the same way.

Adding it surfaced a real data gap: **`F-22A.yaml` authored no `max_range`**, so the
airframe silently fell back to the 150 NM default — *less than half* the F-15C's
authored 400 NM. That is backwards for a fighter whose internal-fuel radius exceeds the
Eagle's, and in this campaign it would have range-gated the Raptor out of the deep half
of the map: it could not have reached the PLAN carrier groups (108–157 NM) or anything
north of Saipan, while the older Eagle could. Now `max_range: 450`, in step with the
fleet's deliberately conservative values (F-15C 400, F-16C 350), and pinned by
`test_the_raptor_has_an_authored_max_range`. The fallback logs a warning and nothing
else, which is exactly why it went unnoticed.

Left alone deliberately: the same yaml declares **`SCR-522`** — the P-51 Mustang's
1940s radio — for both intra- and inter-flight comms, with an in-tree comment already
admitting it is wrong. It feeds the radio allocator, so it is a real bug, but fixing it
touches every campaign that fields the F-22 and belongs in its own change.

### Tankers: boom and drogue are not interchangeable

**Caught after the first cut shipped (DM correction).** Andersen was given a KC-135
**MPRS** as its only tanker — on the assumption that "multi-point" meant it served both
methods. It does not: `KC135MPRS.yaml` declares `tanker_refuel_types: [probe]`, because the
MPRS kit *is* the wing drogue pods. Meanwhile **every jet at Andersen and Won Pat is a boom
receiver** — F-15C, F-15E, F-16CM, B-1B and A-10C all carry `air_refuel_type: boom` — so the
entire land-based wing had nothing it could tank from.

Andersen now bases **both**: a plain **KC-135 ×4 (boom)** for the USAF wing, and a **KC-135
MPRS ×2 (drogue)** det for the Harriers off Olf Orote and the LHA, and as backup for the
carrier air. `test_every_blue_receiver_has_a_compatible_blue_tanker` now walks every authored
blue airframe and asserts some blue tanker's `can_refuel_from` accepts it — the invariant that
would have caught this, and which no "does it have a tanker?" check ever would, since both
entries simply read as "a tanker".

### The carrier air wing is transitional on purpose

The first cut put an **EA-6B Prowler** on the deck, following Repartee's existing
`ea6b_prowler` mod precedent. That was wrong: the Navy retired the Prowler in **2015** and
the Marines in **2019**, so it is precisely the anachronism this campaign strips out of red
(the J-7B). The wing is now the CJS Super Hornet package — `fa_18efg` (E/F/G) and
`fa18ef_tanker` (ET/FT), both preseeded:

- **EA-18G replaces the EA-6B.** §77's runtime is airframe-agnostic (it drives whatever
  ESCORT_JAMMER group the emitter names), so the swap carries no runtime risk, and the
  Growler outranks every other airframe for the role — **Escort Jammer 800** vs the
  Prowler's 790. VAQ-136 "Gauntlets" is a real Growler squadron, so the authored name stays.
- **The F/A-18E Tanker is the organic recovery tanker**, and it is *not* interchangeable
  with Andersen's boom tanker. `FA-18ET` is `tanker_refuel_types: probe`; so is the
  **KC-135 MPRS**, whose multi-point kit is *drogue* pods — it is a drogue tanker, not a
  boom one. Its `Refueling` task priority is 0, which is fine —
  `AircraftType.capable_of` gates on *presence* in `task_priorities`, not on the value.
- **One legacy F/A-18C squadron is kept deliberately.** CJS is a mod; an all-Super-Hornet
  deck would make every carrier jet mod-gated and lock out any MP pilot who has not
  installed it. A guard test pins the legacy squadron's existence — remove it only if the
  `fa_18efg` preseed goes with it.

§74 shipped native DTC cartridges for `FA-18E` / `FA-18F` / `EA-18G` on 2026-08-02, so the
Super Hornets spawn with comms, route and the §65 recovery aids already loaded (no SA
section — CJS stripped `SA` out of its descriptor, so no FLOT, CAP racetracks or threat
rings on those three).

**RED — China 2027** (98 airframes / 15 squadrons)

The enemy is a **fork faction**, `resources/factions/china_2027.json`, and the reason is
worth recording. The DM asked whether High Digit SAMs should be on. Measured, it adds
**only the HQ-2** to `China 2020` and **nothing at all** to `USA 2020` — and the HQ-2 is
a 1960s S-75 derivative that would displace HQ-22 sites. `Redfor (China) 2020` *can*
field the S-300PMU family with HDS, but it is a CJTF-Red faction that also rolls
**SA-2/S-75 and SA-6**, loses the Chinese country identity (§23 voices, zh_CN pilot
names) and mixes Soviet legacy kit into the ground and naval OOB. Switching to it was
tried and measured: red spawned SA-2 and HQ-2 sites as **base defences**, which
`ground_forces` cannot reach.

So `China 2027` = `China 2020` with the **HQ-2 dropped** and **SA-20/S-300PMU-1 +
SA-20B/S-300PMU-2 added**. Modern, era-clean, natively Chinese, and it makes
`high_digit_sams` a hard campaign requirement rather than a flavour toggle.

### Two rules about `ground_forces` overrides, learned the hard way

1. **They reach authored markers only.** A base's own generated air defences roll from
   the faction roster and cannot be pinned — which is why the *faction* had to be fixed.
2. **The preset's task must match the marker's band, or the override is silently
   discarded.** `StartGenerator.get_unit_group_for_task` gates on `task in fg.tasks`.
   The HQ-22 declares `LORAD`, so pinning it onto a medium marker did nothing at all and
   the site rolled an SA-11 — no warning anywhere. Rota's marker is therefore authored
   **long-range**. `test_ground_forces_pins_match_their_marker_band` now catches this
   class of silent failure.

Belt as generated: **1× S-300PMU-2 (Tinian)** · **1× HQ-22 (Rota)** · 5× SA-11 ·
8× HQ-7 · HQ-17A / LD-3000 / PGZ-09 / PGZ-95 / PGL-625 point defence · Silkworm coastal ·
3× CJ-10 PLARF. Zero SA-2, zero SA-6, zero HQ-2.


| Base | Squadrons |
|---|---|
| Saipan Intl (19) | J-11A ×10 BARCAP · **KJ-2000 ×2 AEW&C** · **H-6J ×6 Anti-ship** |
| Rota Intl (9) | Su-30MKK ×6 Strike · IL-78M ×2 |
| Tinian Intl (4) | FC-1 ×4 BARCAP |
| Pagan Airstrip (3) | IL-76MD ×2 |
| 3 × PLAN carrier | J-15 ×10 BARCAP/TARCAP + ×8 Strike/Anti-ship each |
| 2 × PLAN LHA | Mi-24P ×6 CAS · Mi-8MTV2 ×6 Transport |

**No J-7B** — pinned by a test. The modern PLAAF that DCS can actually field is
J-11A + Su-30MKK + J-15 + FC-1 + H-6J + KJ-2000; there is no J-10/J-16/J-20 module or AI unit.

**Every block states an explicit `size:`** — also pinned by a test, because the omitted-size
default is exactly what produced Repartee's inverted 165:62 ratio.

**Parking fit is a standing invariant** (the DS91 pattern): a test asserts no base is
oversubscribed against its real `parking_slots` count. Rota (9), Tinian (4), Pagan Airstrip (3)
and Olf Orote (4) are tiny and will not absorb a casual squadron addition.

---

## How it plays

The islands are not connected, so **ground fronts never form** — captures are made with Air
Assault packages (helicopters off Olf Orote and the LHA, or **§76 C-130J paradrops**), and
everything between the islands is an anti-ship and long-range strike fight. That was Repartee's
identity and it is kept.

Preseeded feature set, and why each earns its place:

- **§49 `mobile_missile_relocation` + §3 `concealed_enemy_forces`** — the PLARF hunt above.
- **§63 `cruise_missile_strikes` + auto raids** — both fleets carry real, finite, no-rearm
  magazines. Sinking a shooter ends its raids. This is the feature the campaign was waiting for.
- **§78 `cargo_ship_convoys` + `coastal_batteries_engage_ships`** — island logistics sail as
  multi-hull convoys that attrit proportionally, past Silkworm batteries that actually engage.
- **§50 `ambient_supply_convoys` + `convoy_ambush`** on Guam's two blue road corridors.
- **§70 `comint_collection` + `red_comms_net`** — the PLA net is audible and homeable.
- **§59 `perf_ground_ai_sleep` + `perf_aaa_site_sleep`** — a three-carrier PLAN order of
  battle plus island garrisons is a heavy maritime laydown.
- **§77 escort jamming** rides along free: VAQ-136's Growlers are authored SEAD, and
  `SquadronConfig.auto_assignable` offers the Escort Jammer role to every capable squadron,
  so they fly in front of the strike packages without a per-campaign edit.

Mod packs are preseeded through the campaign `settings:` block, which re-seeds the New Game
**Mods** checkboxes (`QGeneratorSettings.update_settings`): `chinesemilitaryassetspack` (a
hard requirement — without it the PLA kit degrades to Soviet legacy hardware),
`usamilitaryassetspack`, and the CJS pair `fa_18efg` + `fa18ef_tanker`. Every runtime plugin
the settings depend on is preseeded too (the §36 saved-defaults-off lesson).

**Red fields no ambient convoys, by geography** — no two red bases share an island, so there
is no red→red road. This is the same deliberate no-op as the nine campaigns the §50 batch-2
pass could not serve.

---

## Open questions for the in-game pass (T5)

- Do the three PLARF sites actually scoot on their islands? Rota/Tinian are small — the §49
  4 km scoot radius may push a launcher into the sea, which the relocation code does not
  currently check against the landmap. **This is the row's highest-value observation.**
- Does the DF-21D/CJ-10 kit render and fire at all from a `missile` TGO on these islands?
- Do Andersen's heavy squadrons (B-1B, KC-135, E-3A) fit their stands dimensionally? The
  parking-fit test counts slots, not the slot_version-2 dimensions the DS91 audit needed.
- Does the AI actually fly Air Assault captures across water at these ranges?
- Frame rate with three PLAN carrier groups plus garrisons, with §59 sleep on.

## Deliberately not done

- **North West Field** (0 runways) and a fourth PLARF site north of Saipan (no landmap).
- **An all-Super-Hornet deck** — historically right for 2027, but it would mod-gate every
  carrier jet. The transitional wing above keeps one legacy Hornet squadron instead.
- **A red→red supply road** — geography forbids it.
- **Front lines** — the islands are not connected; Air Assault is the capture mechanic.
