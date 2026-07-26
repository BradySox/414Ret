# 414th — DCS 2.9.28 Iraq map content: what it unlocks — design notes

**Status:** design + authoring plan. **No code, no `.miz` edits yet.** Scoped 2026-07-26.
**Trigger:** DCS **2.9.28.26283** (22.07.2026) shipped a substantial Iraq-map content pass.
Upstream picked the engine bump up as `update dcs to 2.9.28.26283 (#904)` (Druss99, 25.07.2026),
which bumped the pydcs pin and refreshed `resources/terrain-beacons/` for **Caucasus, Iraq, Kola**.

Related: [`414th-desert-storm-campaign-notes.md`](414th-desert-storm-campaign-notes.md),
[`414th-inherent-resolve-campaign-notes.md`](414th-inherent-resolve-campaign-notes.md),
[`414th-scenery-import-notes.md`](414th-scenery-import-notes.md) (the automation this plan
deliberately does **not** wait for), [`414th-tanker-war-campaign-notes.md`](414th-tanker-war-campaign-notes.md).

---

## What 2.9.28 actually added to the Iraq map

Verbatim from the changelog, trimmed to the gameplay-relevant items:

- **Kharg Island** with an **airfield** and unique objects (terminal, ATC, **oil flares**, **pipelines**).
- **Nine named dams with unique 3D models**: Alwand, Dukan, Fallujah, Haditha, Hemrin, Kut,
  Ramadi, Samarra, Diyala.
- Unique scenes around **Erbil International Airport**.
- **Lights** added to **Bashur Airport** and **Al-Salam Airbase** (+ signs at Al-Salam).
- **Fixed aircraft traffic problems on Mosul and H-3 Northwest airfields.**
- Trains, more vehicle routes, road signs/curbs/stones; improved night textures + lights; clipmap work.

**Not in this update, despite the name coming up:** there is **no Bahrain** content in the 2.9.28
Iraq changelog, and no Bahrain airfield on the map — the pinned pydcs Iraq terrain exposes
**19 airports** and the southernmost is **Al-Kut** (Al-Asad, Al-Kut, Al-Sahra, Al-Salam, Al-Taji,
Al-Taquddum, Baghdad Intl, Balad, Bashur, Erbil Intl, H-2, H-3 Main, H-3 Northwest, H-3 Southwest,
K1, Kirkuk Intl, Mosul Intl, Qayyarah West, Sulaimaniyah Intl). Bahrain sits with the unfinished
**southern** extension; treat it as roadmap, not content.

---

## The load-bearing finding: we already consume this, for free

The fork does **not** need the scenery-import automation to use the new content. Desert Storm
already ships **57 hand-authored scenery strike targets** on the Iraq map (Saad 16 Nuclear
Research Complex, Baba Gurgur Oil Processing Plant, Qayyarah POL 1–5, Mukhabarat Directorate
Annex …) through the stock `SceneryGroup.from_trigger_zones` path
(`game/scenery_group.py`, called from `mizcampaignloader.py:341`).

So the dams are **Mission-Editor authoring, not engineering**.

### The authoring convention (verbatim from a working DS91 target)

Two zone kinds, paired by containment:

1. **Blue circle = the objective definition.** `color` blue (`0,0,1,0.149`), `type=0`, a radius,
   and **exactly one property whose value is the category**:

   ```lua
   ["name"]="Erbil Garrison Camp",
   ["properties"]={ [1]={ ["key"]="PROPERTY_1", ["value"]="allycamp" } },
   ["radius"]=365.76, ["type"]=0,
   ```

   `from_trigger_zones` reads `zone_def.properties[1]["value"].lower()` and requires it to be in
   `NAME_BY_CATEGORY`. Valid categories: `allycamp · ammo · commandcenter · comms · derrick ·
   factory · farp · fob · fuel · oil · power · village · ware · ww2bunker`.

2. **White quad zones = the individual destructible objects**, created by the ME's
   scenery-object-to-zone workflow, which stamps the real map object identity:

   ```lua
   ["name"]="Saddam's Northern Palace",
   ["properties"]={ [1]={key="ROLE",value=""}, [2]={key="VALUE",value=""},
                    [3]={key="OBJECT ID", value="73424912"},
                    [4]={key="NAME",      value="erbildowntown_arc"} },
   ["type"]=2, ["verticies"]={...}
   ```

**Every white zone inside a blue zone is claimed by it.** A blue zone with zero white zones inside
raises `SceneryGroupError` and **fails campaign load** — so an un-authored or mis-sized blue circle
is a hard error, not a silent no-op.

> **Why this can't be scripted from here:** each white zone carries an `OBJECT ID` harvested from
> the live terrain. Those IDs only exist on a machine with DCS 2.9.28 + the Iraq map installed
> (via the ME, or the `cwg_scenery_scanner.lua` dump). The map coordinates below take the DM
> straight to each dam; the object binding is an ME step.

---

## Dam target plan

Positions computed with `Point.from_latlng(LatLng(lat, lon), Iraq)` — the same call
`tools/supply_route_geo.py:62` uses — against the pinned pydcs Iraq terrain.
DCS map coordinates (**x = north/south, y = east/west**). Real-world dam coordinates are
approximate (±1–2 km); **the ME is authoritative** — use these to navigate, not to place.

| Dam | lat / lon | map x | map y | nearest field | Campaign | Category |
|---|---|---:|---:|---|---|---|
| **Fallujah Barrage** | 33.3486 / 43.7644 | 10 558 | −42 682 | Al-Taquddum **15 km** | **Inherent Resolve** | `power` |
| **Ramadi Barrage** | 33.4297 / 43.2589 | 20 223 | −89 573 | Al-Taquddum **33 km** | **Inherent Resolve** | `power` |
| **Dukan Dam** | 35.9536 / 44.9414 | 298 747 | 67 005 | Sulaimaniyah 55 km · Kirkuk 76 km | **Inherent Resolve** | `power` |
| **Haditha Dam** | 34.1975 / 42.3550 | 107 161 | −171 435 | Al-Asad **47 km** | **Desert Storm** | `power` |
| **Kut Barrage** | 32.4950 / 45.8180 | −84 457 | 149 138 | Al-Kut **6 km** | **Desert Storm** | `power` |
| **Samarra Barrage** | 34.2028 / 43.8264 | 105 208 | −35 834 | Balad 58 km · Al-Sahra 58 km | **both** | `power` |
| **Hemrin Dam** | 34.1236 / 44.9525 | 95 805 | 67 910 | Balad 58 km | **both** | `power` |
| **Diyala Weir** | 33.2172 / 44.5297 | −4 592 | 28 464 | Al-Salam **8 km** · Baghdad 29 km | **both** | `power` |
| Alwand (Khanaqin) | 34.3400 / 45.3900 | 119 867 | 108 162 | Balad 104 km | *neither* — park | — |

### Why these assignments

- **Fallujah + Ramadi are the flagship pair for Inherent Resolve.** Al-Taquddum (Habbaniyah) is
  IR's blue strike base and sits *between* them; the campaign's own supply route already runs
  `Baghdad International → Al-Taquddum` on Highway 10 **through Fallujah**. Historically exact:
  ISIS held both barrages and manipulated the Fallujah gates to flood ground in 2014, and Ramadi
  was only retaken in February 2016 — eight months before the campaign's 2016-10-16 start.
- **Haditha is the Desert Storm anchor.** It is 47 km from Al-Asad, which DS91 laydown v2 reverts
  to red as **Qadessiya**. The 1991 coalition struck the Iraqi electrical grid hard, hydro
  included, so a `power` objective in the western AO is period-correct and gives the H-3 → H-2 →
  Al-Asad capture ladder a deep-strike target beside it.
- **Kut Barrage rides Al-Kut** (6 km) — the field DS91 already knows as the pre-v2 Fulcrum reserve.
- **Samarra / Hemrin / Diyala are the shared central set.** All three sit inside the
  Balad–Baghdad–Al-Salam triangle that **both** campaigns hold, so one authoring pass serves both.
- **Alwand is parked.** 104 km from the nearest field of either campaign and off both AOs.
  Author it only if a future campaign reaches Khanaqin.

### Category call

All of them take **`power`**. The hydroelectric dams (Haditha, Dukan, Samarra, Hemrin) are literally
power stations. The pure barrages/weirs (Fallujah, Ramadi, Kut, Diyala) are flow-control structures
rather than generators, but `power` is the only category in `NAME_BY_CATEGORY` that reads as
strategic water/electrical infrastructure, and it keeps the map symbol + `GroupTask.POWER`
economics consistent across the set. Do **not** spread them across `factory`/`ware` for flavour —
that trades a coherent target class for noise.

### Naming

Match the existing DS91 register: real proper nouns, no editorialising —
`Haditha Dam Powerhouse`, `Fallujah Barrage`, `Samarra Barrage Control House`. The 57 shipped
targets set the tone (`Baba Gurgur Gas Separation Hall`, `Qayyarah Thermal Power Plant`).

---

## Kharg Island: correct call is to park it

**Verdict: no home in a current campaign. Wait for ED's southern Iraq extension.** (DM call
2026-07-26, and the geometry agrees.)

Converted to map coordinates Kharg lands at **x −431 455 / y 589 924** — **565 km from Al-Kut**,
the southernmost airfield on the map, and 712 km from Al-Salam. Desert Storm fights western Iraq
and Baghdad; Inherent Resolve fights Nineveh, 700+ km north. Neither can reach it, and neither
should: Kharg is an **Iranian** oil terminal, so it is wrong-belligerent for 1991 (Iran was
neutral) and irrelevant to the 2016 caliphate fight.

Where it *does* belong, when the south map lands:

- The **Tanker War (1988)** currently runs on **Persian Gulf** over substitute WRL Noisy Cricket
  Redux geography. Kharg was *the* Tanker War objective — Iran's primary oil export terminal,
  bombed by Iraq throughout 1984–88. A southern Iraq map would let that campaign move to the
  geography that actually contains both belligerents.
- Its unique objects (**terminal, oil flares, pipelines**) are a ready-made `oil` / `fuel` /
  `derrick` scenery target set — the same authoring recipe as the dams.
- It is the natural showcase for **§78 coastal batteries engage ships**, whose design note already
  asks for shipping lanes authored near an opposing shore.

Nothing to do now beyond noting that the **pydcs bump is the gate**: the pinned terrain has no
Kharg airport, so a control point cannot bind there until the fork picks up upstream's #904 pin.

---

## Free wins already in hand (no authoring)

1. **Mosul and H-3 Northwest AI traffic fixed by ED.** These are the two most load-bearing Iraq
   fields the fork ships — Mosul is Inherent Resolve's red anchor, H-3 Northwest is part of Desert
   Storm's seized blue complex and the first rung of its capture ladder. Verify, don't celebrate
   (checklist **T4**).
2. **Night operations open up.** Lights added at Bashur and Al-Salam plus map-wide night texture
   and lighting work. This matters specifically because **§47's continuous campaign clock** marches
   campaigns through darkness instead of re-rolling a daylight slot, so night sorties out of those
   fields are a routine occurrence rather than an edge case.
3. **Erbil International got unique scenes** — a red-held CP in Inherent Resolve, so the target
   area simply reads better.
4. **Trains + extra vehicle routes.** Ambient only. Rail *interdiction* would be genuinely new
   engine work (§35's convoy machinery is road-graph-only, keyed on `supply_routes`), so this is
   recorded as an idea, **not** queued.

---

## Open unknowns (resolve before authoring)

1. **Are the dam models destructible?** A scenery objective needs white zones over *destroyable*
   map objects; large ED unique structures are sometimes indestructible. **Check one dam first**
   (Fallujah — the highest-value and easiest to reach) before authoring the other seven. If the
   models are indestructible, the whole plan collapses to "nice scenery" and should be abandoned
   rather than worked around.
2. **DCS models no dam-break flooding.** A struck dam is a struck building. Do not write campaign
   copy that implies inundation.
3. **Parking/slot churn.** 2.9.28 touched Iraq airfield traffic; DS91 carries a standing
   parking-fit invariant (`tests/fourteenth/test_desert_storm.py`). Re-run it against the bumped
   pydcs — a shrunk slot silently breaks a based squadron.
4. **The pydcs pin is the gate for anything new-airfield.** Dams need no pin bump (they are scenery,
   bound by object ID); Kharg does.

---

## Suggested order of work

1. Verification pass (checklist **T4**) — destructibility probe, Mosul/H-3 taxi, parking-fit re-run.
2. If destructible: author the **Inherent Resolve** set first (Fallujah + Ramadi + Dukan, then the
   shared central three) — biggest historical payoff, and Al-Taquddum makes the pair trivially
   reachable in testing.
3. Desert Storm set (Haditha + Kut + the shared three).
4. Register in `414th-features.md` + `README.md` only once targets actually ship in a `.miz`.
