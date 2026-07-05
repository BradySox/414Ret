# Operation Inherent Resolve — the Iraq / Mosul COIN campaign

**Status: LANDED 2026-07-04 (headless-verified; needs an in-game pass).** The 414th's
**second COIN campaign**, a sibling of *Operation Enduring Resolve* (Afghanistan) built on
the same `coin.py` machinery, retuned for the **Battle of Mosul, October 2016 → July 2017**
on the **DCS: Iraq** map.

This note is the source of truth for the laydown. It was researched from the historical
record (see Sources) and grounded in the real terrain: every stronghold XY was derived from
the town's real lat/lon through the Iraq terrain projection.

---

## Why Mosul / OIR fits the COIN engine

ISIS had **no air force**, so a stock two-air-force campaign doesn't apply — which is exactly
the shape *Enduring Resolve* already solved: RED runs with zeroed air, a trickle economy, and
**cache-throttled ground regeneration**; BLUE is all the airpower; the war is the ISF grind
into the city plus the insurgent replenishment fighting back. The real battle ran in **three
phases** that map 1:1 onto the `phases:` authoring tier (Isolation → East Mosul → West Mosul /
Old City), and every COIN mechanic the fork shipped has a real-world referent here:

| OIR reality | Engine feature |
|---|---|
| ISIS VBIEDs ("15 truck bombs in a day toward Bartella") | `coin_ied` mobile-VBIED variant |
| Roadside IEDs on the ratline | `coin_ied` static devices |
| ISIS emirs / named leaders | `coin_hvt` rotating HVT |
| Ammo/HME caches | `coin_insurgency` cache throttle |
| Infiltration back through cleared ground | `coin_reinfiltration` + `coin_dispersed_cells` |
| Standoff fire on forward fields | `vietnam_airbase_harassment` (Q-West) |
| The ratline west to Tal Afar / Syria | `vietnam_convoy_interdiction` |
| Strategic patience vs. CIVCAS backlash | the inverted `vietnam_political_will` economy |

---

## Theater laydown (DCS Iraq, real terrain CP ids)

Coordinates: **+x = north, +y = east, Baghdad at origin.** Mosul (id 3) is the northwest
apex; Q-West (6) is ~60 km due south; Erbil (4) ~72 km east.

> **Scope revised three times (post-merge playtest, 2026-07-04 → 07-05):** the first cut gave
> red only Mosul + a tight FOB cluster ("a tiny red area"); it briefly swung to the **whole
> northern belt** (7 red + 6 blue airfields — "this is a ton"); then settled on **6 airfields
> total** (3 red, 3 blue — Q-West dropped), red presence carried by **FOBs**. Finally, the user
> **hand-positioned the whole laydown in the ME** to fit the terrain (that miz is now the
> committed **base**, `iraq_inherent_resolve_base.miz`) and asked for **more strongholds in the
> gaps** — so the generator now *decorates* the base with **5 in-between FOBs** (see "The
> generator" below). Current shipped laydown:

- 🔴 **RED airfields (3):** **Mosul (3)** the anchor + SA-6, **Erbil (4)** NE, **Kirkuk (10)**
  central + SA-6.
- 🔴 **RED FOB strongholds (10):** the **authored** towns (ME-positioned in the base) — the
  Highway-1 steps **Tikrit** + **Shirqat**, and the Nineveh ring **Hammam al-Alil**, **Bartella**,
  **Tal Afar** (Syria ratline gateway) — plus the **in-between** gap-fillers (generator-added):
  **Bayji** (Tikrit↔Shirqat), **Qayyarah** (Shirqat↔Hammam), **Hawija** and **Makhmur** and
  **Gwer** (the eastern belt, tying Kirkuk/Erbil to Mosul and the corridor).
- 🔵 **BLUE airfields (3):** **Balad (8)** — the forward field + the player's fast air/helos —
  **Al-Taquddum (13)** — the strike / coalition-CAS field — **Baghdad (2)** — support
  (tankers / AWACS / CSAR).
- ⚪ **Dropped / unset** (not drawn as CPs): **Qayyarah West airfield (6)**, Al-Taji (9),
  Al-Salam (14), Bashur (5), Sulaimaniyah (7), K1 (11), Al-Sahra (12), Al-Asad (1), Al-Kut (19),
  H-2/H-3 (15–18). (Qayyarah returns as a red *town* FOB, not an airfield.)

So RED holds **13 CPs** (3 airfields + 10 FOBs), BLUE **3** — **6 airfields total**.
Dropping Q-West means blue's forward-most field is **Balad** (~270 km from Mosul, ~110 km from
the Tikrit front): a Highway-1 grind, with captured red airfields (Kirkuk, then Mosul) becoming
the forward bases for the final push.

### Front & connectivity — **one front, up Highway 1**
- **The front:** Balad (blue) ↔ Tikrit (red FOB) — the historical Baghdad → Mosul advance
  (`FRONT Balad-Tikrit`), starting partway up the axis via `control_point_strengths`.
- **Red-red supply graph** (yaml `supply_routes`, 14 routes) now runs *through* the in-between
  towns so there are no 100 km empty gaps: the corridor Tikrit → **Bayji** → Shirqat →
  **Qayyarah** → Hammam al-Alil → Mosul the ISF grinds up; the Nineveh ring off Mosul (Bartella +
  the Tal Afar ratline); the NE belt Mosul → **Gwer** → Erbil → Kirkuk; and the bridges
  (**Makhmur** ties Mosul↔Kirkuk, **Hawija** ties the corridor↔Kirkuk). Erbil and Kirkuk have no
  blue neighbour and fall to air assault as the line
  comes up.

### Ground enrichment (per red stronghold)
Every one of the 8 red strongholds is furnished by the generator with **two garrison groups**
(armor markers → filled from the ISIS frontline roster: technicals, gun trucks, the VBIED),
an **AAA** site (ZU-23), a **SHORAD** site (SA-8/9/13), and a **strongpoint** (`Tech_combine`
strike target) — so each objective reads as an occupied position, not a lone icon — plus its
ammo caches. **Mosul and Kirkuk** additionally anchor the **SA-6** (medium/SEAD) radar sites.

---

## Factions

- **BLUE `CJTF-OIR 2016`** (`resources/factions/cjtf_oir_2016.json`, `doctrine: coin`) — a
  multi-nation coalition faction (CJTF Blue country) adapted from `oef_coalition_2006`: USAF
  Vipers/Strike Eagles/A-10s, Navy & Marine Hornets/Harriers, the B-1 and KC-135 bridge, E-3
  and MQ-9, plus the **French Mirage 2000C** and the **Iraqi Su-25** for coalition/ISF flavor.
- **RED `Islamic State 2016`** (`resources/factions/isis_2016.json`) — cloned from Starfire's
  *Toyota Al Gaib* (the most fleshed-out insurgent roster) with an ISIS identity: the suicide
  VBIED (`DIM' KAMIKAZE`), Toyota technicals, DShK/KORD gun trucks, ZU-23 flak, BM-21s, and
  the **captured-SAM crust trimmed to exactly SA-6 / SA-8 / SA-9 / SA-13** (SA-2/3/15 dropped
  from the parent). Zero aircraft.

The crust is the one deliberate divergence from a purist ISIS laydown (which had only
MANPADS/AAA): a thin radar layer that keeps SEAD/DEAD a real job, per the user's call. SA-6 is
the medium (SEAD-relevant) site at Mosul; SA-8/9/13 are the SHORAD across the ring.

### The drone wing (2026-07-05, from the installed-inventory audit)

The user spotted the MQ-9/MQ-1 and asked to use them — they are the OIR signature, and they
close the ISR loop the concealment layer opened. Three coordinated changes:

- **Unit data** (shared, all campaigns): `MQ-9 Reaper.yaml` + `RQ-1A Predator.yaml` gain
  `TARPS: 700` (drones become plannable recon; the `airecon` plugin banks an AI drone's
  overflight as confirmed BDA, so **the drones are what localize the concealed IED/HVT/cell
  circles**) and honest `max_range` (800 / 400 NM — the 150 NM default would have gated them
  out of Balad→Mosul). The Reaper keeps its background combat tasks (armed ISR); the
  Predator's Hellfire tasks stay at zero priority (pure ISR bird).
- **Faction**: `MQ-9 Reaper` + `RQ-1A Predator` added to `cjtf_oir_2016` `aircrafts` (the
  MQ-9 was previously only the faction's JTAC unit).
- **Campaign**: Baghdad (the rear support field — the endurance covers the whole map from
  there) hosts **RQ-1A ×4 `primary: TARPS`** and **MQ-9 ×4 `primary: BAI`**. NEW game
  required; in-game pass = the P7 drone bullet.

---

## The generator — now decorates a hand-authored base (the ER pattern)

The first three cuts were built **from scratch** by the generator (fresh Iraq mission, CJTF
countries, `Airport.set_red()/set_blue()` ownership, and the typed marker groups the
`MizCampaignLoader` reads — FOB `SKP-11`, garrison `M-1 Abrams`, AAA `ZSU-23`, SHORAD
`Strela-1`, MEDIUM `S-75`→SA-6, cache `Warehouse._Ammunition_depot`, front `M-113`, factory
`Workshop_A`). Once the user **hand-positioned everything in the ME** to fit the terrain, that
became the committed base **`iraq_inherent_resolve_base.miz`** — the source of truth for the 6
airfields' ownership, **all 10 authored FOBs** (the 5 originals + the 5 gap-fillers, once
hand-tuned), and every unit's map-fitted placement. **Edit the base in the ME, not the
generator.**

`tools/build_iraq_inherent_resolve_miz.py` now **decorates** the base (exactly like ER decorates
Shattered Dagger): it loads the base and adds only the **`NEW_FOBS`** in-between strongholds
(each an `SKP-11` FOB + 2 garrisons + AAA + SHORAD + a `Tech_combine` strongpoint + one cache)
→ `iraq_inherent_resolve.miz`. When the user hand-tunes a machine-added FOB in the ME, it
graduates into the base (re-export) and comes off `NEW_FOBS`. **`NEW_FOBS` is currently empty:**
the first batch (Bayji, Qayyarah, Hawija, Makhmur, Gwer) was hand-tuned and has graduated into
the base, so the decorator is presently a pass-through (output == base) until the next batch.

**Headless verification:** the decorated miz loads through the real `TheaterLoader("iraq") →
MizCampaignLoader.populate_theater()` to **16 control points** (RED 13 = 3 airfields + 10 FOBs;
BLUE 3), every stronghold furnished (garrison + AAA + SHORAD + strongpoint + caches; SA-6 at
Mosul & Kirkuk), and the Balad↔Tikrit front + the 14-route red supply graph (corridor + ring +
belt + bridges) all forming as convoy routes. `Campaign.from_file` + `parse_will_profile` +
`parse_phases` parse the authored blocks. CI-locked in `tests/fourteenth/test_inherent_resolve.py`.

---

## The will economy & phase arc

The **inverted COIN will profile** (mirrors ER, OIR labels): BLUE *"The Coalition's mandate"*
bleeds from airframes, lost bases, **civilian casualties in the city** (`blue_roe_violation`
1.0 — CDE pressure, not taboo), IED detonations, and plain time (no passive regen). RED *"the
caliphate's resolve"* bleeds from caches (4.0), emir kills (`red_hvt_killed` 4.0), lost bases,
and ground attrition — but its **dead fighters buy almost nothing** (`red_ground_unit_lost`
0.05). Break the resolve before the mandate runs out.

The three-phase arc (`phases:`), will-coupled:

| Phase | Advance when | Emphasis | ROE |
|---|---|---|---|
| **Isolate Mosul** | capture Hammam al-Alil | interdiction | Mosul positive-control box |
| **East Mosul** | red resolve < 45 | offensive | Mosul box (+ a `trail_surge` 2.0) |
| **West Mosul & the Old City** | (final) | offensive | Mosul box **+ the tight Old City box** |

The Mosul positive-control box is permanent (the city is always populated); the West Mosul
phase adds the tight Old City no-strike box on top — the densest CDE ground of the battle. No
free-fire inversion (following the shipped COIN ROE direction): the desert and plains are
simply unrestricted. **No target class is ever locked** — the caches must always be legal
targets.

---

## Deferred / follow-ups

- **In-game pass owed** — the runtime feel (does it play, does the front grind, do the VBIEDs
  and the CDE dilemma read) needs a flown campaign. The COIN mechanics themselves are the same
  ones already tracked in the checklist P-series.
- **Supply-route tracing** — the red-red ring/ratline waypoints are straight-ish first cuts;
  re-trace the intermediates on the real road network via `tools/supply_route_geo.py` (the
  414th supply-line standard), as flagged in the yaml.
- **Stronghold XY** are projection-accurate town centers; nudge against the actual map imagery
  in an in-app pass if any FOB lands awkwardly.
- **Coalition-nation pinning** — the French/Iraqi flavor is auto-cast from the CJTF pool; pin
  per-squadron country (§23) with named presets for exact voices later.

---

## Sources

- [Battle of Mosul (2016–2017)](https://en.wikipedia.org/wiki/Battle_of_Mosul_(2016%E2%80%932017))
- [MWI — Urban Warfare Case Study: Mosul](https://mwi.westpoint.edu/urban-warfare-project-case-study-2-battle-of-mosul/)
- [CTC West Point — Defeat by Annihilation (ISIS defense, VBIEDs)](https://ctc.westpoint.edu/defeat-by-annihilation-mobility-and-attrition-in-the-islamic-states-defense-of-mosul/)
- [Jamestown — Fall of a Jihadist Bastion](https://jamestown.org/fall-jihadist-bastion-history-battle-mosul-october-2016-july-2017/)
- [CJTF-OIR Qayyarah West fact sheet](https://www.inherentresolve.mil/Portals/14/Documents/Mission/Qayyarah%20Airfield%20West%20Fact%20Sheet.pdf)
