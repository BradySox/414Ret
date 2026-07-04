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

> **Scope revised 2026-07-04 (post-merge playtest):** the first cut gave red only Mosul + a
> tight FOB cluster — "a tiny red area." Per the user's call, the caliphate now holds the
> **whole northern belt** (the 2014-era extent), and blue reconquers it from the south. Every
> red stronghold was also enriched from one lone marker to a real garrison. The single-front /
> Mosul-only laydown below is superseded by the belt version.

- 🔴 **RED airfields (7):** **Mosul (3)** the anchor, **Erbil (4)**, **Kirkuk (10) / K1 (11)**,
  **Bashur (5)**, **Sulaimaniyah (7)**, **Al-Sahra (12, Tikrit)** — the northern belt.
- 🔴 **RED town strongholds (5 FOBs; XY from real lat/lon):** Hammam al-Alil `(322805, -81581)`,
  Bartella `(343841, -73022)`, Bashiqa `(355988, -73419)`, Hamdaniya `(334903, -73325)`,
  **Tal Afar** `(348018, -156505)` — the western gateway toward Syria / the far end of the ratline.
- 🔵 **BLUE forward:** **Qayyarah West (6)** — the **sole** forward airhead (player fields + the
  air-assault helos), now the belt is red.
- 🔵 **BLUE rear:** **Balad (8, the heavies + the Tikrit-front base)** · Al-Taji (9) ·
  **Baghdad (2, support/CSAR)** · Al-Salam (14) · Al-Taquddum (13).
- ⚪ **Excluded** (left unset → not drawn as CPs): Al-Asad (1), Al-Kut (19), the H-2 / H-3
  desert fields (15–18).

So RED holds **12 CPs** (7 airfields + 5 FOBs), BLUE **6**. **Al-Salam** sits ~25 km from
Baghdad (deep rear), not a Mosul strip.

### Fronts & connectivity — **two fronts**
- **Mosul axis:** Qayyarah West (blue) ↔ Hammam al-Alil (red) — the historical Federal Police
  motorway thrust (`FRONT Qayyarah-Mosul`).
- **Tikrit axis:** Balad (blue) ↔ Al-Sahra (red) — Highway 1 north out of Baghdad
  (`FRONT Balad-Tikrit`).
  Both are M-113 front-line groups, each starting partway up its axis via `control_point_strengths`.
- **Red-red belt + ring/ratline** (yaml `supply_routes`, 11 routes): Mosul → each of the five
  towns (incl. the westward Mosul → Tal Afar ratline), plus the belt chaining
  Mosul/Erbil/Kirkuk/K1/Bashur/Sulaimaniyah/Al-Sahra so the deep-belt fields are
  reachable/capturable behind the two fronts. The deep-eastern fields (Sulaimaniyah, Bashur)
  have no blue neighbour and fall to air assault as the noose tightens.

### Ground enrichment (per red stronghold)
Every one of the 12 red strongholds is furnished by the generator with **two garrison groups**
(armor markers → filled from the ISIS frontline roster: technicals, gun trucks, the VBIED),
an **AAA** site (ZU-23), a **SHORAD** site (SA-8/9/13), and a **strongpoint** (`Tech_combine`
strike target) — so each objective reads as an occupied position, not a lone icon — plus its
ammo caches. **Mosul and Kirkuk** additionally anchor the **SA-6** (medium/SEAD) radar sites,
one per front.

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

---

## The generator

`tools/build_iraq_inherent_resolve_miz.py` builds `iraq_inherent_resolve.miz` **from scratch**
(there was no pre-authored Mosul miz to decorate, unlike ER decorating Shattered Dagger). It
creates a fresh Iraq mission, adds the CJTF blue/red countries, sets airfield ownership
(`Airport.set_red()/set_blue()`), and places the typed marker groups the `MizCampaignLoader`
reads: FOB (`SKP-11`) strongholds, garrison cells (`M-1 Abrams` armor marker → fills from the
red frontline roster), AAA (`ZSU-23`), SHORAD (`Strela-1`) and — at Mosul only — a MEDIUM
(`S-75` marker → the faction's SA-6 preset) site, the ammo-cache statics
(`Warehouse._Ammunition_depot`), the southern front (`M-113`), and two blue economy factories
(`Workshop_A`). Everything is deterministic (fixed offsets, no randomness).

**Headless verification** (the pipeline was proven end-to-end before landing): the generated
miz loads through the real `TheaterLoader("iraq") → MizCampaignLoader.populate_theater()` to
**18 control points** (13 airfields incl. red Mosul + 5 town FOBs), with caches bound to the
right CP (Mosul 3, each town 2), the garrison + AAA + SHORAD (+ SA-6 medium at Mosul) as
preset locations, and the Q-West ↔ Hammam al-Alil front + the full red ring/ratline as convoy
routes. `Campaign.from_file` + `parse_will_profile` + `parse_phases` all parse the authored
blocks. CI-locked in `tests/fourteenth/test_inherent_resolve.py`.

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
