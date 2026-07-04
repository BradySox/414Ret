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

- 🔴 **RED airfield:** **Mosul International (3)** — the one red airfield, the objective
  (zeroed air).
- 🔴 **RED town strongholds** (authored as **FOB** control points; XY from real lat/lon):
  Hammam al-Alil `(322805, -81581)`, Bartella `(343841, -73022)`, Bashiqa `(355988, -73419)`,
  Hamdaniya `(334903, -73325)`, **Tal Afar** `(348018, -156505)` — the western gateway toward
  Syria and the far end of the ratline (a late-arc objective).
- 🔵 **BLUE forward:** Qayyarah West (6, the player fields) · Erbil (4) · Bashur (5) ·
  Kirkuk (10) / K1 (11).
- 🔵 **BLUE rear:** Sulaimaniyah (7) · Al-Sahra (12) · **Balad (8, the heavies)** · Al-Taji (9) ·
  **Baghdad (2, support/CSAR)** · Al-Salam (14) · Al-Taquddum (13).
- ⚪ **Excluded** (left unset → not drawn as CPs, to keep the theater on Mosul):
  Al-Asad (1), Al-Kut (19), the H-2 / H-3 desert fields (15–18).

**Al-Salam** was confirmed to sit ~25 km from Baghdad International (a deep-rear staging field),
**not** a Mosul-area strip — so Mosul stands as the sole red airfield near the front.

### Front & connectivity
- **One southern front:** Qayyarah West (blue) ↔ Hammam al-Alil (red) — the historical
  Federal Police motorway thrust — authored as an **M-113 front-line group** in the miz
  (`FRONT Qayyarah-Mosul`), starting partway up the axis via `control_point_strengths`.
- **Red-red ring/ratline** (yaml `supply_routes`): Mosul → each of the five town strongholds,
  the western Mosul → Tal Afar leg being the convoy-interdiction ratline. Hammam al-Alil
  therefore carries **both** the front (to Q-West) and a red route (to Mosul), so the grind
  advances organically as it's captured.

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
