# Red Tide — Supply Routes & Kastrup Preset Patch

**Branch:** `feature/red-tide-kastrup-supply-routes`
**Status:** Implemented, tested (658 tests pass, Black + mypy clean). Ready for Brady review.

---

## What was done

Two independent workstreams in this branch:

1. **YAML-driven supply routes** — a new system letting campaign YAMLs define land convoy
   routes and sea shipping lanes without touching the binary `.miz` file.
2. **Kastrup/Copenhagen preset patch** — the Red Tide `.miz` was patched to add the full
   Soviet defense/infrastructure suite at Copenhagen/Kastrup (CP 41).

---

## 1. YAML Supply Routes

### Problem

`MizCampaignLoader` previously read supply routes exclusively from sentinel vehicle/ship
groups baked into the `.miz` binary (M-113 vehicles → convoy routes, HandyWind ships →
shipping lanes). Changing routes required ME binary edits or external patch scripts — not
suitable for a text-based campaign configuration.

### Solution

Extended `MizCampaignLoader` to also read `supply_routes` and `shipping_lanes` sections
from the campaign YAML. Both systems are **additive** — YAML routes are added after `.miz`
routes, so nothing existing breaks.

**Modified files:**

- **`game/campaignloader/mizcampaignloader.py`**
  - `__init__` now accepts `campaign_data: Optional[dict[str, Any]] = None`
  - Added `add_yaml_supply_routes()` — reads `supply_routes` list, creates bidirectional
    convoy routes via `create_convoy_route()`
  - Added `add_yaml_shipping_lanes()` — reads `shipping_lanes` list, creates bidirectional
    sea lanes via `create_shipping_lane()`
  - Both use `dcs.mapping.Point(x, y, terrain)` for coordinate objects
  - Origin/destination CPs are inferred via `closest_control_point()` from the
    first/last waypoint — no manual CP IDs needed
  - `populate_theater()` calls both new methods after the `.miz`-based routes

- **`game/campaignloader/campaign.py`**
  - Passes `self.data` (the parsed YAML dict) to `MizCampaignLoader`

**YAML schema** (added to `resources/campaigns/red_tide.yaml`):

```yaml
supply_routes:
  - waypoints:
      - [x1, y1]   # DCS terrain coords; first WP → origin CP
      - [x2, y2]
      - [xN, yN]   # last WP → destination CP

shipping_lanes:
  - waypoints:
      - [x1, y1]
      - [xN, yN]
```

Waypoints are `[x, y]` DCS map coordinates (meters, same system as pydcs). Use
`Point.from_latlng(LatLng(lat, lon), terrain)` to convert real-world lat/lon to DCS
coords — see `tools/verify_kastrup_full.py` for usage pattern.

### Red Tide routes added

**Land: Hamburg → Wittstock** (follows the A24/B195 road corridor, not a straight line)

```yaml
supply_routes:
  - waypoints:
      - [-63016, -691931]    # Hamburg
      - [-98000, -636000]    # Hagenow / A24 junction
      - [-118000, -591000]   # Parchim area
      - [-135396, -529213]   # Wittstock
```

**Sea: Kastrup → Peenemünde** (Baltic maritime channel via Øresund)

Route traces the real-world deep-water channel: Kastrup airport → Drogden channel
(port/harbor east of airport) → south through the Øresund → Køge Bay → Baltic south of
Falsterbo/Sweden → Arkona Basin (north of Kap Arkona/Rügen) → east of Rügen → northeast
of Usedom → Peenemünde.

All waypoints verified with pydcs `Point.from_latlng` against `GermanyColdWar` terrain.
First and last waypoints are the exact CP airport coordinates so the line anchors at the
airbase rather than terminating in open water.

```yaml
shipping_lanes:
  - waypoints:
      - [133705, -489651]    # Kastrup airport (55.62N 12.65E)
      - [127676, -481587]    # Drogden channel / port (55.57N 12.79E)
      - [107576, -486537]    # South Øresund (55.39N 12.75E)
      - [86888,  -492218]    # Køge Bay (55.20N 12.70E)
      - [73561,  -474471]    # Baltic exit (55.10N 13.00E)
      - [64121,  -440082]    # Arkona Basin (55.05N 13.55E)
      - [38305,  -407238]    # Baltic E of Rügen (54.85N 14.10E)
      - [-28616, -410553]    # Pomeranian Bay NE of Peenemünde (54.25N 14.15E)
      - [-37265, -436134]    # Peenemünde airport (54.15N 13.77E)
```

### How to add routes to another campaign

1. Open the campaign's `.yaml` file.
2. Add `supply_routes:` and/or `shipping_lanes:` sections (see schema above).
3. Use pydcs to get accurate coordinates:

```python
from dcs.terrain.germanycoldwar import GermanyColdWar
from dcs.mapping import Point, LatLng

t = GermanyColdWar()
p = Point.from_latlng(LatLng(55.62, 12.65), t)
print(p.x, p.y)
```

4. For convoy routes, ensure waypoints follow roads/terrain — Retribution doesn't
   pathfind, it draws straight segments between waypoints. Add enough intermediate
   waypoints to avoid obstacles.
5. For shipping lanes, ensure **all straight-line segments between consecutive waypoints
   stay in water**. Use intermediate waypoints to navigate around peninsulas/islands.
   The first and last waypoints should be the CP airport coordinates for visual anchoring.

---

## 2. Kastrup Preset Patch

### Problem

Copenhagen/Kastrup (CP 41) had no ground presets — no factories, ammo depots, or air
defense. Also, the existing AAA group (from an earlier patch) was placed in water
northeast of the airport.

### Solution

Patched `resources/campaigns/red_tide.miz` directly using
`tools/patch_kastrup_full.py`. The script reads the `.miz` as a zip archive, surgically
inserts new groups into the red coalition section, and rewrites the archive.

**Groups added/fixed (all in red coalition, all on land west/southwest of airport):**

| Group | Type | DCS Coords | Description |
|-------|------|-----------|-------------|
| Ground-Kastrup-SHORAD | 2S6 Tunguska | x=130500, y=-492500 | Was already correct |
| Ground-Kastrup-AAA | ZSU-23-4 Shilka | x=131000, y=-494500 | **Fixed** — was in water at x=136000, y=-486800 |
| Ground-Kastrup-LORAD | S-300PS 5P85C ln | x=128500, y=-494000 | **New** — long-range SAM preset |
| Ground-Kastrup-MRAD | S_75M_Volhov | x=131200, y=-491500 | **New** — medium-range SAM preset |
| Kastrup Factory | Workshop A | x=130000, y=-493500 | **New** — factory static group |
| Kastrup Ammo Depot | .Ammunition depot | x=129500, y=-491000 | **New** — ammo depot static group |

Sentinel unit types drive Retribution's preset system:
- `2S6 Tunguska` → SHORAD slot
- `ZSU-23-4 Shilka` → AAA slot
- `S-300PS 5P85C ln` → LORAD slot
- `S_75M_Volhov` → MRAD slot
- `Workshop A` (static, shape `tec_a`) → factory
- `.Ammunition depot` (static, shape `SkladC`, category `Warehouses`) → ammo depot

Vehicle groups go into the red coalition `["vehicle"]["group"]` array. Static groups go
into `["static"]["group"]`. Both require distinct `groupId` and `unitId` values above the
existing max.

**Tools** (in `tools/`):
- `patch_kastrup_full.py` — the comprehensive patch script (already applied; keep as
  reference if re-patching is needed after a `.miz` change)
- `verify_kastrup_full.py` — verifies all 6 groups are present, in red coalition, with
  correct coordinates
- `extract_supply_routes.py` — extracts M-113 waypoints from a `.miz` for reference
- `check_preset_ids.py` — lists all sentinel unit type IDs in a `.miz`
- `find_static_group.py` — finds static group structure by type string

### Coordinate system notes

- DCS GermanyCW: x increases going **north**, y increases going **east**
- Kastrup airport center: x=133729, y=-489625 (verified against pydcs)
- Land is west/southwest of the airport; water (Øresund) is to the east/northeast
- 1 DCS unit = 1 meter (approximately; map uses curved projection, small error at scale)

---

## Testing

```powershell
.venv\Scripts\python.exe -m black --check .    # 0 files to reformat
.venv\Scripts\python.exe -m mypy game tests    # 0 new errors
.venv\Scripts\python.exe -m pytest tests -q    # 658 passed, 2 skipped
```

Generate a Red Tide campaign in Retribution and verify:
- Supply route Hamburg → Wittstock visible on the Retribution map (red convoy line)
- Shipping lane Kastrup → Peenemünde visible on the Retribution map (ship line)
- Kastrup CP shows SHORAD, AAA, LORAD, MRAD, factory, and ammo depot preset slots
  when opening base management

---

## Full migration to YAML routing (follow-up)

Red Tide is now routed **entirely from YAML** — the `.miz` no longer contains any M-113
front-line path groups or HandyWind shipping groups. What changed:

1. **Migrated the 5 original `.miz` M-113 routes to `supply_routes:` verbatim** (every road-snapped
   waypoint preserved, since `frontline.py` builds the front geometry from
   `convoy_route_to()` — each route becomes a front line as blue captures and pushes, so the
   paths must stay faithful):
   - Ramstein → Frankfurt, Spangdahlem → Frankfurt (blue rear)
   - **Frankfurt → Haina** (the opening front)
   - Haina → Wittstock, Wittstock → Peenemünde (red rear/advance)
2. **Deleted those 5 M-113 groups from `red_tide.miz`** (brace-balanced; all other groups —
   carrier-removed state, red Hamburg/Kastrup, the 3 Baltic Fleet markers, and the Kastrup
   defense preset — left intact).
3. **Wired in the 4 previously-orphaned bases** so the front can advance across the whole
   theater (they had no supply link in the original `.miz`):
   - Hahn → Frankfurt (blue rear)
   - Haina → Sperenberg → Schönefeld → Templin → Wittstock (the red Berlin cluster)

   These 5 new links are **straight-line paths** (2–3 waypoints) — functional connectivity, but
   they should be refined with road-following waypoints (pydcs `from_latlng` / mission editor)
   for nicer front geometry when they activate, the same way the Hamburg → Wittstock and the
   Baltic lane were built.

**Net:** 11 `supply_routes` + 1 `shipping_lanes`, all endpoints verified to snap to the intended
control points. The whole network is connected, so blue can capture every red base by ground.
Still needs an in-game load to confirm the lines render and the front advances correctly.
