# Naval station-keeping racetracks

414Ret §87. One file, one new method group, one call site.

## The defect

A ship group with no campaign destination this turn generates with a **zero-waypoint
route**. DCS parks it on its campaign marker for the whole mission, so every hull is a
stationary target and a fleet reads as scenery.

His tree has the same hole: `GroundObjectGenerator.generate` calls
`sail_to_destination` when `target_position` is set and does nothing otherwise. The
patch adds the `else`.

## What it does

An anchor-centred racetrack, sailed by DCS itself.

- **The anchor is the oval's centre, not a point on it.** That is what makes it station
  *keeping*: mean position stays the campaign position, and displacement is capped at
  half the diagonal, so the map, the drawn threat rings and the turn-boundary model stay
  honest however long the mission runs.
- 3 × 1 NM at 10 kt — a ~48 minute lap. Sized by the smallest thing it must not
  invalidate: a short-legged hull's own threat ring. An 8 × 2 NM oval was rejected for
  putting a Molniya wholly outside its own drawn ring.
- **No runtime.** The waypoints are ordinary route points and the loop is the Mission
  Editor's own `SwitchWaypoint`. No plugin, no Lua, no scheduled task. It also survives a
  pushed task — a cruise-missile `FireAtPoint` pops back to this route when the salvo is
  done, where a scripted `mist.goRoute` would have wiped it.
- **Water-validated.** DCS naval AI does no land avoidance at all, so every leg is
  sampled every half mile and a track is rejected unless the whole line is sea. Candidate
  bearings are tried in a deterministic per-group order (crc32 of the group name, so
  regenerating a turn re-derives the same station instead of reshuffling the fleet).
- **Degrades to today's behaviour**, never worse: no landmap, or no clear orientation
  (a harbour berth, a tight anchorage) leaves the group stationary.

## Applying

```
git apply station-keeping.patch
cp test_naval_station_keeping.py tests/missiongenerator/
```

Verified to apply at `ca780fd2`. The test drives real pydcs `ShipGroup`s against a faked
theater — only `landmap` and `is_in_sea` are consulted — so it needs nothing from our
tree. 11 tests; the load-bearing one is
`test_the_anchor_is_the_centre_of_the_track`.

`pairwise` and `SwitchWaypoint` are already in his tree; `Point.lerp` is pydcs.

## Verification status here

**◐ PARTIAL** (our row B48). What is established, across three campaigns and four
Tacviews:

- Pre-§87 every authored naval group sat at 0.1 km; post-§87 the same groups sail
  12–24 km over a 48-minute mission.
- Formation spacing is unchanged — widest gap between any two hulls of a group is
  constant to two decimal places across a whole mission.
- Net drift stays small: a Perry sailed 22.9 km for 2.8 km of drift, a Burke 9.9 km
  for 2.5 km, over 95 minutes.

**What is still owed, and what his testing would settle:** those numbers are *distance
sailed* and *drift over the sampled window*. §87's actual contract is displacement from
the campaign anchor over a **long** mission. A ≥90 minute mission measuring
position-vs-anchor closes the row. Carriers are excluded by design — they steam for wind.
