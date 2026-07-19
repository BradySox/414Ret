# Iraq — Umm al-Ma'arik (Desert Storm 1991): campaign notes

**Status: BUILT + headless-verified 2026-07-19; laydown v2 (the western desert war)
same day; in-game pass = checklist T3. NEW game required (it's a new campaign).**

## Laydown v2 — the western desert war (2026-07-19, the DM's call)

The v1 laydown shipped blue holding Al-Asad — always its biggest fiction (in January
1991 the coalition held **zero** Iraqi airfields, and Al-Asad was *Qadessiya AB*, home
of the real MiG-25PD wing). The DM's parking question ("confirm big parking spots")
exposed the deeper problem and drove the rework:

**The Iraq map has NO oversized parking west of Baghdad.** The map is `slot_version 2`
(pydcs resolves parking by real slot *dimensions*, not the legacy `large` flag — the
flag is zero map-wide), and the 60×60 heavy stands live only at Baghdad (15), Erbil
(17), Balad (6), Sulaymaniyah (6), Al-Salam (5), Taquddum (3), Qayyarah (2), Al-Asad
(2). The v1 E-3/KC-135 wing at H-3 Main had **zero** fitting stands; the original DS91
also mis-based the 24-Fulcrum reserve at Al-Kut (58 helipads + six plane stands) and
v1 briefly re-based the A-10s at H-3 SW (two Hog-wide stands). All caught and now
guarded by `test_desert_storm_every_squadron_fits_its_parking`, which asserts every
based squadron has **at least as many dimensionally-fitting slots as airframes**.

The v2 shape:

- **BLUE = the H-3 complex + the off-map Saudi rear.** The fiction inverts to a much
  smaller lie: the coalition seized the three border strips in the opening hours
  (real planners drafted exactly this; SOF owned that desert). H-3 Main = the
  fighter/strike wing (F-15C ×12 BARCAP · F-4E ×12 · F-14B ×8; trimmed 16→12s to fit
  36 fighter stands), H-3 Northwest = the SEAD/precision/attack strip (F-16CM ·
  F/A-18C · F-15E · **A-10C** ×8 each — the Hog lives here, not SW), H-3 Southwest =
  the army-aviation strip (CH-47F + AH-64A + OH-58D, 8 Chinook-fit pads). The
  **E-3 + KC-135 + MPRS fly from "Coalition Rear (Saudi Arabia)"**, an `OffMapSpawn`
  marker group — no parking dependency, no OCA exposure, historically exactly where
  they were.
- **The capture ladder is the campaign**: H-3 → **H-2** (red forward picket,
  MiG-21bis ×8; P2 objective) → **Al-Asad/Qadessiya** (the Foxbat wing home from
  Baghdad + the Frogfoot/F-6 wing forward from Taquddum; P3 objective) → Taquddum
  (emptied to a SOC-West depth fortress) → Baghdad. Authored as three M-113 path
  groups in the miz ("Front H-3 to H-2", "Corridor H-2 to Al-Asad", + the original
  Asad↔Taquddum group): the front line advances rung by rung as ownership flips, and
  each leg doubles as the convoy road once captured.
- **Red gains its historical anchors**: **Balad (al-Bakr AB)** — the Al-Salam
  MiG-23ML + Su-24M wings move to their real home, plus the Backfire wing resized
  ×8→×6 to its six heavy stands; **Mosul (Firnas AB)** — the MiG-21bis wing up from
  Erbil (which keeps the 12-Backfire wing on the map's largest heavy ramp); the
  **Fulcrum reserve moves Al-Kut → Al-Sahra (Tikrit)**, the regime's hometown, 51
  fitting stands. Al-Kut keeps SOC East + defenses as a depth field.
- **KARI extended**: comms/power relays at Qadessiya/H-2/Balad/Mosul (13 comms + 13
  power total), a fifth EWR forward at Qadessiya facing the H-3 front, and **two
  western-basket Scud batteries** (9 missile TGOs total — the Israel-shot geography
  now sits on the front's doorstep, which is the whole Scud-hunt phase).
- Blue AA/armor markers for the strips (Hawk + Vulcan + M-1 garrisons, authored in
  the red block per the coalition-agnostic marker convention); Qadessiya/H-2/Balad/
  Mosul get era AA rings. The old blue Hawk markers at Al-Asad now correctly
  re-resolve as red MERAD from Iraq's roster — the marker convention working as
  designed.
- Supply yaml re-cut to **12 red interior routes** (Highway 1 now splits at the
  Balad junction and extends Qayyarah→Mosul; Mosul→Erbil added). 17 total pairs
  bind with the miz-native corridors.

Headless-verified end-to-end (17 CPs — 3 blue + off-map + 13 red; front exactly
H-3 Main ↔ H-2; 40 squadrons resolve exactly; every squadron fits its parking; KARI
at 104 IADS nodes).

## Historical squadron identities (2026-07-19, the DM's call)

Every squadron is named for the real unit that flew (or best matches) its airframe
and role in January 1991 — Gulf War Air Power Survey for the coalition, the
ACIG/Osprey IrAF orders of battle for Iraq:

| Wing | Unit | The story |
|---|---|---|
| F-14B Strike | **VF-103 "Sluggers"** | The actual F-14A+/B DS unit (Saratoga, CVW-17) |
| F-15C BARCAP | **58th TFS "Gorillas"** | 16 kills — the most of any squadron in the war |
| F-4E SEAD Sweep | **561st TFS "Black Knights"** | The Wild Weasels (F-4E stands in for the F-4G) |
| F/A-18C SEAD | **VFA-81 "Sunliners"** | Killed two MiG-21s mid-strike, bombs still aboard |
| F-16CM DEAD | **23rd TFS "Fighting Hawks"** | The 52nd TFW Weasel hunter-killer Vipers |
| F-15E OCA | **336th TFS "Rocketeers"** | The 4th TFW Scud hunters |
| A-10C CAS | **355th TFS "Falcons"** | Myrtle Beach Hogs out of King Fahd |
| CH-47F | **7-101st Aviation "Eagle Lift"** | The G-Day air assault into FOB Cobra |
| AH-64A | **1-101st Aviation "Expect No Mercy"** | Task Force Normandy — the war's first shots, against the EWR chain this campaign models |
| OH-58D | **2-17th Cavalry "Out Front"** | The Screaming Eagles' scouts |
| E-3/KC-135s | **963rd AWACS / 1701st + 1702nd AREFW(P)** | The Saudi-rear support wings |
| Red fixed-wing | **Nos. 84 (MiG-25, the night-one kill), 6 + 39 (MiG-29), 63 + 93 (MiG-23), 11 + 47 (MiG-21), 79 (Mirage F1), 8 (all the Fencers, split into flights), 69 + 44 + 109 + 114 (Fitters/Frogfoots), 7 (Tu-22), 10 (bombers), 33 (Il-76), Adnan-1 AEW Flight** | Published IrAF numbers where documented |
| Red helos | Nos. 2/4/30/55/66 Sqn, IqAAC | **Representative** — IqAAC helo numbers are poorly documented |

Era discipline: `female_pilot_percentage: 0` everywhere (US combat squadrons were
closed until 1993). Iraqi squadrons author an **explicit empty nickname** — which
now *clears* the field (a one-line `override_squadron_defaults` change:
`config.nickname or None`), suppressing the def generator's random "Apoplectic
Porcupine"-style roll that otherwise lands on every generated def. **Liveries are
deliberately NOT authored** — preset livery strings must match the installed DCS
livery set (the squadron-livery-audit lesson); identity first, paint later if the
DM wants a livery pass against the real install.

The DM's homemade "DS91" campaign (`DS91.yaml` + `DS91.miz`, authored ~Jan 2026 against
the same 10.8 campaign format the fork still speaks), audited, fixed, modernized onto the
current 414th feature stack, and promoted into the repo as
`resources/campaigns/iraq_desert_storm.{yaml,miz}`. The Desktop originals are untouched.

## The premise

"It was said Baghdad was the most well defended city in the world before Desert Storm."
The campaign is the air war against that claim: the French-built **KARI** IADS (ADOC in
Baghdad + sector operations centers + an EWR chain feeding the SA-2/SA-3/Kub rings),
the GCI-alert Iraqi Air Force behind it, the Scud hunt, and the six-week arc from the
night-one decapitation strikes to the ground offensive. Blue flies east out of Al-Asad
and H-3 (the real western-desert geography); red holds the other nine airfields.

## What was inherited, what was fixed

The original was built on top of Starfire's `operation_desert_aladeen.miz` and carried
its *Dictator*-universe fiction (19+ Wadiyan/Aladeen/Nadal/Tamir-Mafraad scenery-target
zones). It also had five silent squadron bugs and a pre-war start date:

- **MiG-25PD squadron didn't exist** — a missing `- ` list marker made the yaml parse
  the string as characters (`M`, `i`, `G`…); the whole 16-ship Baghdad Foxbat squadron
  silently substituted to Mirage F1. Fixed (one character).
- `u-22M3 Backfire-C` typo → `Tu-22M3`; `Su-34 Fullback` (2014 airframe, not in the
  faction) → `Su-22M4`; `E-3A` authored at RED Baghdad → `A-50` (the real Iraqi
  "Adnan-1" was literally an Il-76 AWACS conversion); `Mi-26` (not in faction) →
  `IL-76MD`.
- `CH-47F Block I` + `A-10C Thunderbolt II (Suite 7)` were authored (the DM wants the
  flyable modules) but absent from the `NATO Desert Storm` faction, silently falling
  back to UH-1H/A-10A. **The faction gained both** (zero blast radius — no other
  campaign uses it) and the campaign preseeds `restrict_weapons_by_date` +
  `restrict_props_by_date`, so the 1991 date era-clamps their stores and cueing visors
  (the elegant half: a Suite 7 Hog flying with era weapons).
- Start date `1990-05-16` (pre-invasion) → **`1991-01-17T03:00`** — the datetime form
  seeds the clock, so a new campaign opens on the night-one strikes.
- All 33 Dictator-universe trigger zones renamed to the real 1991 CENTAF target set,
  geography- and category-matched: **Saad 16** research complex at Erbil (the real
  northern weapons-R&D site), **Baba Gurgur** oil infrastructure at Kirkuk, the
  **Daura refinery** + **Rasheed** military-industrial set at Al-Salam, the
  **Qayyarah** refinery/POL farm, Ba'ath/Mukhabarat leadership targets. The blue
  definition zones were renamed too — `start_generator` passes `zone_def.name`
  straight into the TGO, so "New Trigger Zone-4" was the *in-game objective name*.
  The DM's own era-neutral gags (Kirkuk "Pointy/Round Weapons", the Erbil "Ammo
  Drive-Thru", the Daura sub-buildings) survive.

## Balance: the escort-starvation fix + red's posture

Blue had 13 squadrons and exactly one A2A unit — 8 F-15Cs tasked *Escort*, no BARCAP
squadron at all — against ~56 red fighters (the classic no-offensive-air signature).
The F-15Cs are now **`primary: BARCAP, secondary: air-to-air, size 16`** (the 33rd
TFW wall): blue stands defensive orbits AND every strike package can draw its escort
from the air-to-air secondary.

Red follows the Red Tide red-posture lesson (fighters defensively roled, attackers
offensive): MiG-25PD / MiG-23ML ×2 / Kirkuk's MiG-29A all fly `BARCAP + air-to-air`
primaries, and the campaign seeds `opfor_default_qra_reserve: 4` — the GCI-vectored
hot-alert force KARI actually ran (guard-tested). The Su-22/Su-24/Su-25/Tu-22/H-6
attack wings keep the DM's offensive taskings. The MiG-19P stays on close escort for
the Taquddum Frogfoots (Iraq's Chinese F-6s), and the Kiowa squadron moved from the
odd `OCA/Aircraft` to `Armed Recon` (its actual role).

## The KARI build (the Red Tide advanced-IADS pattern)

`advanced_iads: true` + red-block statics in the miz; MANTIS range-mode auto-wires
(comms <15 nm, power <35 nm — no `iads_config` needed):

- **C2 trios** (Command Center + Comms tower M + GeneratorF): the **ADOC at Baghdad**
  + SOCs at **Al-Taquddum (West) / Kirkuk (North) / Al-Kut (East)**.
- **Comms + power relays** (no CC) at the other five red bases (Rasheed/Al-Salam,
  Tikrit/Al-Sahra, Qayyarah, Erbil, Sulaymaniyah) so the whole net is C2-coupled —
  killing comms matters everywhere, and §70 COMINT gets nine nets to hunt.
- **EWR chain** (`1L13 EWR` markers; the faction fields P-37 Bar Lock + 1L13) facing
  the blue axis: Habbaniyah, Baghdad, Tikrit, Qayyarah.

Headless-verified: 4 commandcenter + 9 comms + 9 power + 4 ewr TGOs bind, and the
IADS network builds 86 nodes with 255 connections. The existing 78 authored AA sites
(the user's Baghdad super-MEZ: 14 at Baghdad Intl + 28 at Al-Salam) resolve through
the Iraq 1991 roster to the era-correct KARI kit — SA-2/SA-3/Kub/Osa/KS-19+SON-9/
ZSU-57-2/Shilka. The NASAMS/Patriot/S-300PS units in the miz are **band markers by
design** (the loader's vocabulary for "medium/long SAM here"), not anachronisms — do
not "fix" them.

Note the SAM-belt standard tension deliberately left alone: Iraq 1991 fields no
strategic SAM (its best is the SA-6), so the regiment-by-authoring pattern doesn't
apply — the legacy sites ride the §60 doubling like every other campaign.

## The feature stack (preseeds)

All preseeded ON in `settings:` (with their plugins, per the §36 saved-default-off
lesson): `campaign_phases` (authored arc below), `vietnam_political_will` (the will
economy — which also makes POWs an **indefinite running sore**, the real POW-parade
story, repatriated on the negotiated win), `c2_decapitation_effects` (§52 — KARI's 4
command centers degrade red's planning), `auto_repair_air_defenses` (§68 — KARI
historically repaired between strikes), `comint_collection` + `red_comms_net` (§70
C0+C1 — bomb-it-or-tap-it on the same nine nets), `convoy_ambush` (§50),
`host_red_scramble` + `redscramble.hostPlayers: Flash` (§61), plugins
`mobilemissiles` (§49 — the seven authored Scud batteries shoot-and-scoot; **the
Great Scud Hunt needs this**) + `convoyambush` + `rednet` + `redscramble`.
`restrict_weapons_by_date` + `restrict_props_by_date` enforce the era (both halves,
per the settings-split-orphans lesson). Budgets: P2000 / E1000 ×0.5 income — the
sanctioned, blockaded state.

Deliberately NOT enabled: `enemy_comms_jamming` (§51 — Iraq jamming blue isn't the
story), cruise missiles (§63 — no navy in the laydown, the map has no blue water
here), `artillery_base_harassment` (the front CPs sit 119 km apart, out of reach).

## The will profile + phase arc

**Will:** BLUE "Coalition cohesion" (exhaustion: "The coalition fractures") vs RED
"the regime's resolve" (exhaustion: "Baghdad capitulates" — the negotiated win at
Safwan). Weights stay at the Vietnam-derived defaults except
`blue_roe_violation: 3.0` — one Al-Firdos is survivable, a habit is not. Balance
tuning deferred to the first flown session (the M1 pattern; don't blind-tune 20
weights).

**Phases** (authored, OR-semantics `advance_when`):

1. **Instant Thunder** (`rollback`) — decapitate KARI, roll back the rings. Advances
   on `enemy_iads_below: 0.55` (the real coupling: you leave phase 1 by killing the
   IADS, not by waiting).
2. **The Great Scud Hunt** (`interdiction`, `min_turn: 4`, `trail_surge: 1.5`) — the
   launchers relocate between recon passes (§49 + §3 concealment), and red surges
   its highway convoys. Advances on `enemy_iads_below: 0.35`.
3. **Umm al-Ma'arik — the ground offensive** (`offensive`, `min_turn: 9`) —
   capture-Al-Taquddum + break-the-resolve objectives.

**The Baghdad no-strike circle rides every phase** (4 nm at [9000, 16000], the
populated river-bend core — computed to clear both airbase MEZs: 9.9 nm to Baghdad
Intl, 6.2 nm to Al-Salam). CDE is priced, never hard-blocked.

## The highway graph

Ten routes traced from the real 1991 road network via `tools/supply_route_geo.py`
(mode **`iraq_desert_storm`** — regenerate there, never hand-edit the yaml numbers):
Highway 1 (Baghdad→Taji→Samarra→Tikrit→Bayji→Qayyarah), Highway 10 west
(Abu Ghraib→Fallujah→Habbaniyah), Highway 6 southeast (Salman Pak→Kut), the Jabal
Hamrin crossing (Tikrit→Kirkuk), the Kurdish arcs (Altun Kupri, Chamchamal,
Makhmur), and BLUE's one MSR — **the IPC pipeline-station road H-3 → H-2 → H-1 →
Al-Baghdadi that the H airfields are literally named for** (and the §50 ambush
alley). Nine red interior corridors = the §35/§50/§57 interdiction target set. Three
more red corridors ride in the miz from the original build (Al-Salam↔Kirkuk 53-wp
road trace, Al-Salam↔Taquddum, plus the Al-Asad↔Taquddum front route).

## Verification

- `tests/fourteenth/test_desert_storm.py` — CI-locks the campaign definition, the
  faction adds, the red defensive posture, the will/phase parses, the supply-graph
  endpoints, and the miz KARI/rename content (7 tests).
- Headless end-to-end: full `GameGenerator` → `begin_turn_0` run — **all 39
  squadrons resolve to their authored airframes exactly** (the original had 6
  silent substitutions), 13 route pairs bind, the arc + will parse live on the
  game object.
- In-game pass owed: **checklist T3**.

## Deferred / open

- **Balance pass after the first fly** — the will weights, red fighter counts
  (24-ship Fulcrum wing at Kut), and the enemy budget are first-fly tuning levers.
- **A Scud→will feed** (a launch draining Coalition cohesion — the Israel story) has
  no engine mechanism; would need a §49-adjacent will hook. Not worth building
  until the campaign proves out flown.
- **Carriers/navy**: none in the laydown (the DCS Iraq map's water is marginal for a
  CVN anyway). If a Red Sea/Gulf slice ever matters, §63 cruise raids become
  available.
- The three miz-native red supply routes are kept as-found (driveable, user-traced);
  if a re-trace is ever wanted, add them to the geo tool's mode.
