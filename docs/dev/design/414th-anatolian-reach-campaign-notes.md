# Syria — Anatolian Reach (campaign notes)

**Status: BUILT 2026-08-26, flown once (turn 2), not balance-tested.**
Owning test: `tests/fourteenth/test_anatolian_reach.py`.
Files: `resources/campaigns/anatolian_reach.yaml` + `.miz`.

Israel and a US carrier/tanker hub against a Turkey–Russia bloc, 1 June 2004.
The subject of the campaign is **range**: every target that matters is 250–400 nm
from the Negev, and getting there is the problem the whole laydown is arranged
around.

---

## Why this exists rather than one of the seventeen shipped Syria campaigns

The brief was Israel + US against Iran, Iraq or Turkey in 2004. Two of the three
were closed by evidence before any authoring started:

- **Iran is not on the map.** The Syria terrain's easternmost airfield is
  Diyarbakir at 40.2°E; Iran's western border is ~45.5°E. There is no Iranian
  ground to fight over.
- **Iraq in 2004 had no air force**, and the US was occupying it. Separately,
  `operation_desert_trident` already ships USA-Israel 2000 vs Iraq 2000 on this
  exact map.

Turkey is the one foe fully on-map (12 airfields including Incirlik and Konya),
with a faction that already matches the date, and no shipped campaign pairing it
against Israel — `operation_aegean_aegis` is a Cyprus-only helicopter raid with
grounded enemy aircraft and no Israeli involvement.

## Scale, and how it was chosen

The first laydown proposed 41 airfields. An audit of **all 68 campaigns upstream
ships** (`tools`-free, read with the loader's own rules) put that 4× over:

| Airfields per campaign | All 68 | Syria's 17 |
|---|---|---|
| median | 8 | 9 |
| max | 29 (Pretense, a different mode) | 17 |

`Syria - Full Map` — the campaign literally named Full Map — uses **13**. Blue is
always small: Syria median 2 blue airfields, max 6.

Final: **14 airfields, 17 control points** (4 blue / 13 red), 120 objective
groups. Comparable to Desert Trident (13) and Full Map (13); under the Syria
ceiling of 17.

## The three decisions that are load-bearing

### 1. Akrotiri is support-only

Akrotiri is the **closest blue base to seven of the nine Turkish fields**
(Incirlik 188 nm, against Ramat David's 260). Base a strike or fighter squadron
there and the auto-planner frags from Cyprus every time; the Israeli squadrons
sit on the ramp and the long-range campaign silently does not happen.

It therefore carries **tankers, AEW&C and lift only**. That is not a stylistic
choice — it is the mechanism that makes the transit a designed piece of
infrastructure instead of an obstacle. Locked by
`test_akrotiri_flies_no_combat_aircraft`.

Confirmed in the first flown turn: Akrotiri put up one E-3A and two KC-135s, and
Hatzerim and Ramat David flew the `Incirlik Escort` / `Incirlik SEAD Escort` /
`Incirlik Armed Recon` packages.

### 2. The enemy faction is inline

Retribution allows **one faction per coalition**, so an alliance has to be written
into the yaml. The shape follows Fuzzle's shipped `operation_allied_sword`, whose
`Syria-Lebanon 2005 … with several imported Russian assets` faction does exactly
this on this map.

It matters twice over. `Turkey 2005` rosters **no long-range SAM at all** —
Hawk, SA-3, Rapier — so a campaign about penetrating defended airspace had
nothing defending it. Starfire hit the other half of the same problem and said so
in Peace Spring's own description: he set that campaign in Turkey's 2019
incursion and still chose Iraq 1991 as the enemy, because Turkey 2005 fields only
two jet types.

Per-squadron `country:` pins put Turkish liveries and voices on the Turkish
fields and Russian on the deep east and the Syrian gates.

### 3. The SAM belt is period-gated by hand

`restrict_weapons_by_date` gates **weapons but never preset groups**. Nothing in
the engine stops an S-400 in a 2004 campaign. Excluded deliberately: SA-21/S-400
(2007), SA-17/Buk-M2 (2008), Su-34 (2014), T-72B3 (2011). Locked by
`test_sam_presets_are_period_correct_for_2004`.

## Traps paid for while building this

- **The carrier must be a Stennis hull in the editor.** `MizCampaignLoader`
  recognises `Stennis.id` and nothing else as a carrier. The authored boat was a
  `CVN_71`, and it registered as no control point at all — no error, just an
  absent base. The `carriers:` block paints it back to a Roosevelt in game. It
  must also sit under **CJTF Blue**; carriers are read per-country.
- **A FOB's CJTF block decides its side**, unlike SAMs and factories which the
  fork reads from both blocks. Two FOBs authored into the blue block came out as
  blue control points inside red Turkey.
- **145 of the map's 224 "airports" are zero-runway helipads.** Assign one by
  accident and it becomes a control point.
- **`inclusion_zone_only` is not a land test.** It subtracts the 117 exclusion
  zones — one of which spans 304 × 545 km over deep Turkey — and the sea polygon
  overlaps the Akrotiri peninsula, so both make good ground read as water. Use
  `landmap.inclusion_zones`: open sea reads False, every airfield reads True.
- **Blue and red cannot be land-connected here.** Akrotiri is on an island;
  Ramat David to Bassel Al-Assad is 168 nm through neutral Lebanon. The campaign
  therefore has no ground front, which is the same conclusion HolyOrangeJuice
  reached on this map — WRL Battle for Syria North is subtitled *"Frontlines
  Removed"*.

## What the first flown turn established

Turn 2, 36.9 minutes, 2004-06-01 at 22:36 local (night — see below).

Worked: MANTIS built the red IADS (8 SAM, 13 EWR groups); both halves of the
alliance flew; Akrotiri stayed support-only; blue SEAD **killed an S-300PS track
radar 10 nm from Incirlik**; the carrier killed two offshore platforms; QRA
scrambled from Bassel Al-Assad and Chukurova, scored 4 hits and was wiped out;
§91 recorded all 176 sorties. Blue 51 sorties / 11 lost / 66 shots / 44 hits
against red 123 / 23 / 38 / 19.

**Fuel was never the constraint** — zero of 34 crashes had under 5% remaining,
against a predicted starvation failure that did not occur.

## Deferred / unverified

- **The long-range design is only half-tested.** A Hatzerim–Incirlik round trip
  is ~700 nm; the session ran 37 minutes. The kills that landed came from §89
  pre-rolled flights already airborne. Needs a long session.
- **Balance is unmeasured.** USA-Israel 2000 is 1999–2000 kit against S-300PS and
  MiG-31s. Untested beyond one short night.
- **Supply routes are one road** (Incirlik–Kahramanmaras, 41 waypoints against
  the 3–5 guidance). Konya/Gazipasa and the Syrian gates are unconnected.
- **Night is not a bug.** §47 marches the clock 3–7 hours per turn and
  `Conditions.advance` never consults `night_day_missions` — that setting governs
  turn 1 only. A full day cycles every 4–8 turns, so expect roughly a third of
  missions in darkness. Left unpinned on the DM's call.
- **`CLAUDE.md:893` disagrees with this campaign.** The standard prefers
  regiment-by-authoring for strategic belts; the S-300s here are single sites, on
  an explicit DM call this session. Undocumented deviation until that line is
  amended.
- Red engages civilian airliners (two lost in the first turn). Cosmetic.
