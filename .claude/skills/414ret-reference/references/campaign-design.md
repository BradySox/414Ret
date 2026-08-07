# Campaign Design (distilled from wiki: Custom campaigns, Motorpools, Campaign maintenance)

A campaign = a **YAML file** (metadata) + a **.miz file** (theater layout with placeholder units). Both live in `resources/campaigns/` in the install, OR better in `<DCS Saved Games>/Retribution/Campaigns/` (searched first, keeps custom work separate from the install). Restart Retribution after changes; changes only affect NEW games. If a campaign doesn't appear in the New Game wizard, the YAML is broken — check console/log.

**Version rule that bites people:** the `version` field is the CAMPAIGN FORMAT version, not the Retribution version. Always check `CAMPAIGN_FORMAT_VERSION` in `game/version.py` (dev branch) — breaking format changes are documented there, not on the wiki.

## Campaign YAML fields

| Field | Required | Notes |
|---|---|---|
| `name`, `authors`, `description` | Yes | Shown in New Game wizard |
| `theater` | Yes | One of: Caucasus, Persian Gulf, Nevada, Normandy, Syria, The Channel, Falklands, Sinai, Kola, Afghanistan, Iraq, MarianaIslands, GermanyCW |
| `version` | Yes | Campaign format version from version.py. Missing or "0" = flagged incompatible |
| `miz` | Yes | Filename of the .miz in the same directory |
| `performance` | Yes | 0 (light) to 3 (heavy) |
| `squadrons` | Yes | Starting squadrons per base — see below |
| `recommended_player_faction` / `recommended_enemy_faction` | No | Can be a name or a full in-line faction definition |
| `recommended_start_date` | No | YYYY-MM-DD, optionally with time; no time = random midday hour |
| `recommended_player_money` / `recommended_enemy_money` | No | Default 2000 |
| `recommended_*_income_multiplier` | No | Default 1.0 |
| `advanced_iads` | No | true enables Comms/Power/C2 IADS features |
| `iads_config` | No | Explicit IADS network wiring — see below |
| `ground_forces` | No | Override SAM type per group name (e.g. `SAM-LR-Palmyra: SA-5/S-200`) — type must exist in the faction |
| `carriers` | No | Override carrier name+type per .miz group name; both `preferred_name` and `preferred_type` required per entry |
| `settings` | No | Suggest any game setting as default (names/values from `game/settings/settings.py`) |

## Squadron config in the YAML

```yaml
squadrons:
  BASE_NAME_OR_ID:            # group name (FOB/LHA/CV) or pydcs airfield ID number
    - primary: BARCAP          # a FlightType name exactly as shown in the UI
      secondary: any           # any | air-to-air | air-to-ground | list of types (optional)
      aircraft:                # tried in order; first valid for the coalition wins
        - F-14B Tomcat
```

Common YAML errors and causes (all case-sensitive):
- **"air-to-ground is not a valid FlightType"** — air-to-air/air-to-ground are secondary-only, never primary
- **"'primary'"** — stray dash before `secondary:` or `aircraft:` (each squadron is ONE list item)
- **Carrier class error** — no `squadrons` block at all
- **"NoneType is not iterable"** — an `aircraft:` block with nothing under it
- **"Cannot find ControlPoint named X"** — squadron key doesn't match the group name in the .miz exactly

Optional per-squadron-entry fields: `size` (default 12), `aircraft_type` (real DCS type key when `aircraft` names are display names), plus `name`/`nickname`/`female_pilot_percentage` overrides.

Design guidance from upstream: not every base needs squadrons; cover the major task types (BARCAP, CAS, SEAD, Transport, AEW&C, Refueling); set up one rear-area transit hub per side (big airfield, factory, cargo squadron, ideally a port — good home for AEW&C/tankers plus a BARCAP to guard them).

## Mission editor placeholder units (Unit Type Quick Reference)

Coalitions: assign to **Combined Joint Task Forces Blue/Red**. Easiest start: copy an existing campaign in the same theater.

| Objective | Coalition | Placeholder unit | Clearance |
|---|---|---|---|
| EWR | Red | EWR 1L13 | 50ft |
| Long range SAM | Red | Patriot LN M901 / SA-10 TEL C or D | 1000ft |
| Medium range SAM | Red | Hawk LN M192 / NASAMS LN (B or C) / SA-2 LN SM-90 / SA-3 LN 5P73 | 800ft |
| Short range SAM | Red | Avenger / Rapier LN / SA-19 Tunguska / SA-9 Strela 1 | 800ft |
| AAA | Either | Flak 18 / Vulcan M163 / ZSU-23-4 | 700ft |
| Factory | Blue | Workshop A | fit building |
| Ammo depot | Either | Ammunition depot warehouse | 350ft |
| Strike target | Either | Tech Combine | 350ft |
| Offshore strike target | Red | Oil Platform | 1000ft |
| Missile site | Red | SSM SS-1C Scud-B | 800ft |
| Coastal defense | Red | AShM SS-N-2 Silkworm | 800ft |
| Ship | Red | Arleigh Burke IIa | 5000ft |
| Armor group | Either | MBT M1A2 Abrams | 500ft |
| FOB | Either | Truck SKP-11 Mobile ATC | 100ft |
| FOB (no statics) | Either | Truck M939 Heavy | none |
| Neutral FOB | Red | KrAZ6322 | 100ft |
| Comms | Either | Comms tower M | fit building |
| Power | Either | GeneratorF | 350ft |
| Command Center | Either | Command Center | fit building |
| Carrier | Either | CVN-74 | — |
| LHA | Either | LHA-1 | — |
| Off-map spawn | Either | F-15C | — |
| Ground spawn slot | Either | A-10A / AJS37 / C-130 (large slot) | wingspan of an A-10A |
| Supply route | Blue | M113 with offroad waypoints | — |
| Convoy spawn position | — | Scout HMMWV ~200m behind route ends, onroad waypoints ~2NM | — |
| Shipping lane | Blue | Bulker Handy Wind | navigable route — DCS ships will NOT avoid islands |

Other .miz rules:
- Airbase ownership: assign the airbase itself to blue/red; check `dynamic spawns` for a capturable neutral base
- Control-point influence zones: RED trigger zone, property value = CP name
- Heading of a placed objective unit is kept if non-zero; 0 = auto-orient toward conflict center (Anti Air, Missile, Coastal, Vehicle groups only)
- Campaign inversion: mark player-owned-when-inverted via "unlimited aircraft" warehouse property (airbases) or "late activation" (FOB/carrier/LHA/off-map)
- Air Assault LZs: trigger zone named `<CP name> CTLD`, white, sized for a safe random landing point anywhere inside; multiple LZs auto-suffix -1, -2; closest to ingress is used
- Ground spawns: first waypoint of the placed aircraft = center of a SCENERY REMOVE OBJECTS ZONE (may not work in MP)

## Supply routes — the classic mistakes

1. Verify a real onroad route first with a temporary ground unit set to onroad waypoints; then place the M113 waypoints so they intersect that road route; delete the temp unit.
2. Don't trace every bend — over-waypointing convolutes the UI route and can flip frontline orientation 180°.
3. Don't place waypoints off-road for aesthetics — every M113 waypoint must sit on the road.
4. Add convoy spawn positions (Scout HMMWV) or convoys spawn offroad and waste time forming up.

## Strike-target income (source of truth: `REWARDS` in `game/config.py`)

| Type (key) | Income/turn |
|---|---|
| Oil platform (`oil`) | 10 |
| Oil derrick (`derrick`) | 8 |
| Factory (`factory`) | 2.5 + produces ground units + $10M note: factory income listed separately in config |
| Warehouse (`ware`), Fuel depot (`fuel`) | 2 |
| FARP (`farp`) | 1 |
| Army camp (`allycamp`) | 0.5 |
| Village (`village`) | 0.25 |
| `power`, `comms`, `commandcenter`, `fob` | 0 (structural/IADS roles) |

Income is per **structure**, not per group. Map scenery objects can be targets: white auto trigger zone per building ("assign as..."), blue zone (0,0,255) enclosing the white zone centers = the named objective group; first property of the blue zone = category. Blue zones can't overlap; unique names required.

**Factories**: ground units only originate from CPs with factories; front-line factory = no convoys (removes a mission type); prefer rear hubs; losing all factories ends ground procurement (turn 0 exempt). **Ammo depots**: each CP gets 15 free deployable ground units; each depot building +12 (default template = 36). **Rebel zones**: trigger zone named `Rebels*`; color picks side (blue=OWNFOR, red=OPFOR); properties = unit id → count or range (e.g. `1-4`).

## IADS and Skynet

Modes: **Basic** (auto-association, no comms/power) is default. **Advanced** requires `advanced_iads: true`; network defined either **by config** (`iads_config` list — primary nodes = SAM/EWR/C2/naval by exact .miz group name, each with a list of its connected secondary nodes) or **by range** (auto: comms ≤15nm, power ≤35nm). AWACS auto-added. Connection nodes can't link to each other. Map-object IADS pieces get a dummy static soldier for Skynet tracking.

**Upstream's own warning, keep it in mind for squadron use:** Skynet is a deliberately unrealistic coordination challenge for large MP groups — it breaks AI SEAD (radars stay dark, AI SEAD RTBs without kills). Enabled by default; disable for solo/small-group play. Skynet per-SAM overrides go in the Search Radar's unit.yaml under `skynet_properties`.

> **414th delta — the engine is different, the authoring is not.** Skynet is **removed**;
> **MANTIS is the sole IADS engine** and there is no `iads_engine` selector. Everything above
> about *authoring* still applies — the `advanced_iads` flag, `iads_config` by-name networks,
> the by-range mode, connection-node rules and the dummy-static trick are unchanged, and the
> `IadsNetwork` / `IadsRole` / `IadsProperties` data model (with `Skynet*` back-compat aliases,
> including `skynet_properties` in unit yamls) is what MANTIS consumes. The AI-SEAD warning is
> a Skynet behaviour and does **not** transfer.
>
> Two fork conventions when laying out a new campaign's air defences:
> - **Legacy/mobile systems** (SA-2/3/6, Hawk, generic launcher sites) — a lone site is fine;
>   §60 already gives every SAM layout **two** guidance radars so one HARM isn't a site kill.
> - **Strategic belts** (S-300/S-400/Patriot) — prefer **several single-radar fire units plus a
>   shared EWR** and let MANTIS net them, rather than one doubled fat site.
> - **Never run both models on the same system** — that double-counts radars.

## Motorpools

Strikeable vehicle park showing a CP's UNDEPLOYED reserve armor. Opt-in: place a `Fortification.Garage_A` static (coalition = owner); nearest CP claims it. Vehicles spawn in rows starting ~150ft behind the garage, 12m spacing, rotating with garage heading — reserve that space. **414th: reworked 2026-07-26 (upstream #899/#895) — the authored `Garage_A` marker IS the depot anchor now (the depot renders exactly on it) and the vehicle grid moves clear at 45.72 m in the building's local +x/+y corner, still heading-rotated. The planner also bails on an empty reserve pool. Pretense is removed fork-side, so that caveat doesn't apply.** Keep the whole site outside the 3,000m (~2nm) capture zone; the UI warning only checks the Garage anchor, not the vehicle grid. Mechanics: 1:1 with reserve armor (kill = CP loses that unit), no income, no frontline effect, passive weapon-hold units, default cap 10/CP/turn (0–25), multiple motorpools share one pool, the garage building itself is inert and respawns. AI targets them with escorted BAI (STRIKE fallback). Not supported in Pretense mode.

## Campaign maintenance (upstream policy)

Unowned campaigns get REMOVED when they break. Volunteering: announce in Discord #campaign-maintenance, add yourself on the wiki page. Updates via PR, or via the Campaign Update issue template with files attached if PRs aren't your thing. Upstream prefers maintainers own 1–2 campaigns done well.
