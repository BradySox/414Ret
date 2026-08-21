# Terrain elevation for ground-marked steerpoints

**Built 2026-08-20.** Owning feature: §8 (robustness/crash fixes), checklist rows B79 and
a new row for the target steerpoint. Producer `scripts/derive_terrain_elevations.py`,
data `resources/terrain_elevation/<terrain>.json`, lookup
`game/theater/terrainelevation.py`.

## The defect

Reported from the cockpit: a DEAD steerpoint does not sit at 0 AGL, it sits at **0 MSL**.

Every consumer wrote `alt = 0` for a client's ground-marked waypoint, with an AGL flag
beside it — `alt_type = "RADIO"` in the `.miz`, `altitudeType = 2` in the DTC cartridge.
Whatever that flag is supposed to mean, the number reaches the jet as sea level. On high
terrain the steerpoint ends up under the map, and there is nothing at it to slave a pod to
— which is the exact thing upstream's comment says the 0 exists to enable.

This is upstream behaviour, not a fork regression:
`PydcsWaypointBuilder.build`'s "Set Altitute to 0 AGL for player flights so that they can
slave target pods or weapons to the waypoint" is upstream's line, and every airframe
inherits it.

## Why it took a new data source

Nothing in the tree knows terrain height at an arbitrary point. Checked, all three:

| Source | What it has |
|---|---|
| `resources/airport_imagery/<terrain>.json` | airfields only — this is what Takeoff and Land use |
| pydcs | no heightmap |
| campaign `.miz` ground objects | route points stored as `0` / `-0` |

## What was built

`scripts/derive_terrain_elevations.py` walks every campaign `.miz`, collects the authored
ground/static/ship positions, rounds them to a 100 m grid, and asks Open-Elevation (SRTM,
~5 m) for each cell's height. One JSON per terrain, mirroring `airport_imagery`'s layout
and naming.

`game/theater/terrainelevation.elevation_at(terrain, position)` returns the sampled
elevation, searching outward to `SEARCH_RADIUS_M` (1 km) when the exact cell was not
sampled — a campaign marker is a point, but the layout spreads its units a few hundred
metres around it, so the waypoint rarely lands in the sampled cell itself. Past that
radius it returns None rather than guess: a mountain's height applied to a valley is worse
than the status quo.

`ground_mark_altitude(waypoint, theater)` in `game/ato/flightwaypoint.py` is the single
rule, and its three consumers now agree by construction:

- `PydcsWaypointBuilder.build` — the generated `.miz`
- `dtc.common.client_altitude` — the Hornet and Viper cartridges
- `FlightPlanBuilder` — the kneeboard's Alt column

Sampled → elevation AMSL as BARO. Unsampled → `0` / RADIO, exactly as before.

## Coverage, and what it deliberately misses

Only positions authored into a campaign `.miz` are sampled. **Front-line CAS boundaries,
convoys and relocated mobile SAMs (§49) resolve to None and keep the old 0.** That was the
accepted trade when this was scoped: it covers the reported case (a SAM site) and every
strike/BAI/DEAD target, at ~1,300 points and 34 KB for the Persian Gulf, versus a full
per-terrain heightmap costing megabytes per map.

Twelve terrains shipped, 8,783 cells, 268 KB. Spot checks that say the projection and the
scale are right: Caucasus tops out at 5,590 m (Elbrus is 5,642 m), Sinai bottoms at −404 m
(the Dead Sea is −430 m), Persian Gulf runs −16 m of sabkha to 4,185 m of Zagros rim.

**Kola is the thirteenth and ships nothing.** SRTM covers 60°N to 56°S; Kola sits at ~68°N,
and Open-Elevation answers `0` rather than erroring outside coverage, so all 484 of its
cells came back sea level. Writing that would be worse than writing nothing — the consumer
would take the 0 as a real elevation instead of falling back to 0 AGL — so the script now
discards any terrain whose every point reads 0 and says so. Kola's targets keep the old
behaviour. A `land.getHeight` dump would fix Kola too, since DCS has the mesh regardless of
latitude.

## The upgrade path, if the misses start to matter

A DCS-side `land.getHeight` grid dump — the same shape as the CWG scenery scanner — would
be **exact rather than ~5 m, offline, and complete**, because it reads the mesh the jet
itself flies over. It costs the DM one run per map and a few MB per terrain in the repo.
Take that route before widening the SRTM sampling; do not build a second approximate
source.

## Regenerating

```
python scripts/derive_terrain_elevations.py                  # every terrain
python scripts/derive_terrain_elevations.py --terrain PersianGulf
python scripts/derive_terrain_elevations.py --dry-run        # count cells only
```

Runs merge into the existing JSON, so a new campaign only costs its own new cells. The
script needs network access and is build-time only — nothing at runtime ever calls
Open-Elevation.

## What still needs a cockpit

The premise came from the cockpit and the fix has not been back there yet. What to look
for: a DEAD or Strike target on high ground, steerpoint elevation in the DED/HSI matching
the terrain rather than reading 0, and a pod slaving to the mark instead of short of it.
If the steerpoint is still wrong with a non-zero elevation written, the problem is not the
number and the next suspect is the `altitudeType` handling itself.
