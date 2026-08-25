# Three features from the 414Ret fork — implementation brief

**For an agent working in `juanjux/dcs-retribution`.** Written 2026-08-24 against
`master @ ca780fd2`.

Three self-contained features, in ascending order of size. Each is independent — do one,
all three, or none, in any order.

Everything here was built and flown in the 414Ret fork. Where a feature has open
verification debt, this brief says so rather than claiming it is finished.

---

## Ground rules

**Verify before you implement.** Every claim below about *your* tree was checked at
`ca780fd2`, but check again — line numbers move. If an anchor named here is not where
this says, find it by the surrounding code and adapt. Do not force a match.

**The fast path.** Each feature has a patch verified to apply cleanly at `ca780fd2`:

```
curl -O https://raw.githubusercontent.com/BradySox/414Ret/main/docs/dev/upstreaming/juanjux/naval-station-keeping/station-keeping.patch
curl -O https://raw.githubusercontent.com/BradySox/414Ret/main/docs/dev/upstreaming/juanjux/sead-coordination/sead-coordination.patch
curl -O https://raw.githubusercontent.com/BradySox/414Ret/main/docs/dev/upstreaming/juanjux/region-priorities/region-priorities-core.patch
git apply station-keeping.patch sead-coordination.patch region-priorities-core.patch
```

All three apply together, in any order, and the seven touched files compile as a set.
The tests live beside each patch in the same directories.

If `git apply` fails because your tree has moved, implement from the spec instead. The
spec is authoritative; the patch is a convenience.

**Two traps, both already hit:**

1. **`settings.py` anchor collision.** Features 2 and 3 both add a `boolean_option` to
   the Campaign Doctrine page. They must not use the same insertion anchor. As written,
   feature 2 anchors on `desired_barcap_mission_duration` and feature 3 on
   `desired_awacs_mission_duration`. Keep them apart.
2. **Do not take patches generated against the old 414Ret fork point** (`dce851ea`).
   That commit predates both trees' upstream syncs and nothing built against it applies
   to you. Your `tgogenerator.py` is 1,760 lines; that base's is 1,636; 414Ret's is
   2,213.

**House style in your tree, which this follows:** comments say *why*, never *what*;
a constraint learned from a flown test is worth a comment, the next line is not.

---

## Feature 1 — Naval station-keeping racetracks

**Size:** one file, +115 lines. **Tests:** 11, self-contained. **Status in 414Ret:**
partially verified in-game (see below).

### The defect, which is in your tree

`GroundObjectGenerator.generate` (`game/missiongenerator/tgogenerator.py`, ~line 329)
calls `sail_to_destination` when `self.ground_object.target_position` is set — and does
nothing otherwise. A ship group with no campaign destination this turn therefore
generates with a **zero-waypoint route**, so DCS parks it on its campaign marker for the
entire mission. Every hull is a stationary target and a fleet reads as scenery.

The fix is the missing `else`.

### What to build

An anchor-centred racetrack that DCS sails by itself.

**The load-bearing property: the anchor is the oval's CENTRE, not a point on it.** That
is what makes this station *keeping* — the group's mean position stays its campaign
position, and displacement is capped at half the diagonal, so the map, the drawn threat
rings and the turn-boundary model stay honest however long the mission runs. If you
change one thing about this design, do not change that.

**Constants** (module level, before `class GroundObjectGenerator`):

| Constant | Value | Why |
|---|---|---|
| `STATION_LEG` | `nautical_miles(3)` | Sized by the smallest thing it must not invalidate: a short-legged hull's own threat ring. An 8 × 2 NM oval was rejected for putting a Molniya wholly outside its own drawn ring. Do not enlarge on feel. |
| `STATION_WIDTH` | `nautical_miles(1)` | as above |
| `STATION_SPEED` | `knots(10)` | ~48 min lap. Economical loiter, not a transit — visibly under way all mission without standing on the helm. |
| `STATION_WATER_SAMPLE` | `nautical_miles(0.5)` | DCS naval AI does **no land avoidance whatsoever**, so a leg is usable only if the whole line is sea. Two clear endpoints with an island between them sail the group onto the beach. |
| `STATION_BEARING_STEP` | `30` | Candidate long-axis bearings, tried in order until one is clear. |

**Methods** on `GroundObjectGenerator`, placed next to `sail_to_destination`:

- `hold_station(group: ShipGroup) -> None` — set `points[0].speed`, add the four corners
  as waypoints, then append a `SwitchWaypoint(from_waypoint=len(group.points),
  to_waypoint=2)` to the last point.

  **`to_waypoint=2`, never 1.** Waypoint 1 is the spawn at the *centre* of the oval — it
  is the one-time run-out onto station and must not become a leg of the repeating
  circuit.

  **No runtime component.** These are ordinary route points and the Mission Editor's own
  `SwitchWaypoint` action. No plugin, no Lua, no scheduled task. That also means the
  route survives a pushed task: a cruise-missile `FireAtPoint` is pushed onto the queue
  and pops back to this route when the salvo is done. A scripted `mist.goRoute` — a
  `setTask` — would have wiped it instead.

- `_station_racetrack(anchor, name) -> Optional[List[Point]]` — try each bearing in a
  **deterministic per-group order** and return the first whose whole circuit is clear.

  Use `crc32(name.encode("utf-8")) % count` for the starting offset, **not** `hash()`:
  `str` hashing is salted per process (`PYTHONHASHSEED`), so `hash()` would reshuffle the
  whole fleet's patrol pattern every time a turn is regenerated.

  Return `None` when `self.game.theater.landmap` is falsy — without a landmap
  `is_in_sea()` answers False everywhere, so nothing can be validated and the group
  should stay put rather than sail blind into a coastline.

- `_racetrack_corners(anchor, bearing) -> List[Point]` (static) — a flattened oval
  centred on `anchor`. Order the four corners so the circuit is two long legs joined by
  two short ones, i.e. four 90° turns rather than a 180° reversal at each end.

- `_track_is_clear(path) -> bool` — sample every leg at `STATION_WATER_SAMPLE` spacing
  and return False on the first point that is not `theater.is_in_sea`. Validate
  `[anchor, *corners, corners[0]]` — the run-out leg counts.

**Call site** — the `else` on the existing branch:

```python
else:
    # No campaign destination this turn, so the group would otherwise generate
    # with a zero-waypoint route and sit on its marker all mission. Put it on
    # station instead.
    self.hold_station(ship_group)
```

**Degrade, never break.** No landmap, or no orientation clear of land (a harbour berth, a
tight anchorage), leaves the group exactly as it is today. This feature can only add
motion, never take it away.

### Imports

`crc32` from `zlib` is new. `SwitchWaypoint` goes into the existing `from dcs.task import`
block. `nautical_miles` and `pairwise` join `from game.utils import Heading, feet, knots,
mps` — both already exist in your tree (`pairwise` at `game/utils.py:472`). `Point.lerp`
is pydcs and is already used in five places in upstream's own code.

### Acceptance

- `tests/missiongenerator/test_naval_station_keeping.py` passes (11 tests). It drives
  real pydcs `ShipGroup`s against a faked theater — only `landmap` and `is_in_sea` are
  consulted — so it needs nothing from the 414Ret tree.
- The one that matters is `test_the_anchor_is_the_centre_of_the_track`. If you refactor,
  keep it passing.
- A generated mission's naval groups have a 5-waypoint route ending in a `SwitchWaypoint`
  back to waypoint 2.

### Honest status

**Partially verified in-game** (414Ret row B48). Established across three campaigns and
four Tacviews: groups that previously sat at 0.1 km now sail 12–24 km per mission;
formation spacing is unchanged (widest gap between two hulls of a group constant to two
decimal places across a whole mission); net drift stays small — a Perry sailed 22.9 km
for 2.8 km of drift, a Burke 9.9 km for 2.5 km, over 95 minutes.

**Not yet established:** those are distance-sailed and drift-over-sample. The actual
contract is displacement from the campaign anchor over a *long* mission. A ≥90 minute
mission measuring position-vs-anchor is what would close it.

Carriers are excluded by design — they steam for wind.

---

## Feature 2 — Strikes push behind their SEAD window

**Size:** two files, +143 lines. **Tests:** 15, self-contained. **Status in 414Ret:**
verified in-game, no caveats.

Your README's 2026-08 review already queued this: *"packages are scheduled independently
today, so nothing stops a strike entering a ring before the SEAD servicing it."* This is
that.

### The defect

`MissionScheduler.schedule_missions` times packages independently — a random spread
across the mission window. Nothing connects a strike to the SEAD tasked against the SAM
covering its target, so a strike can arrive at a defended objective half an hour *before*
its suppression.

### What to build

One pass, `_coordinate_sead_windows(now)`, plus a free function holding the window math.

**Split the math out.** `coordinated_strike_tot(strike_tot, earliest_tot, provider_tots,
lead, duration) -> Optional[datetime]` takes no `self` and touches no engine types, which
is what makes the interesting half testable without building a `Coalition`.

Its rules, in order:

1. No providers → `None` (keep the TOT).
2. Window opens at `max(provider_tots) + lead`, closes `duration` later.
   **`max`, not `min`** — every suppressor on station before the strike pushes.
3. Strike already inside the window → `None`.
4. Otherwise `desired = max(window_start, earliest_tot)` — never earlier than the
   package can physically fly.
5. If `desired > window_end` **and** `strike_tot >= window_start`, return `None`. It
   cannot make the window, but at least it is not ahead of its SEAD, so leave the spread
   schedule alone.
6. `desired == strike_tot` → `None`. Otherwise return `desired`.

**Class constants:** `SEAD_WINDOW_LEAD = timedelta(minutes=2)`,
`SEAD_WINDOW_DURATION = timedelta(minutes=8)`, and

```python
COORDINATED_STRIKE_TYPES = frozenset({
    FlightType.STRIKE, FlightType.BAI,
    FlightType.OCA_RUNWAY, FlightType.OCA_AIRCRAFT,
})
```

Armed Recon and Air Assault stay on the spread schedule.

> **Correction, 2026-08-25.** The patch comment justifies those two exclusions with
> "a loitering sweep, not a push" and "tied to the ground war's timing". **Both are
> false**; fix the comment when you apply the patch. `ArmedReconFlightPlan` extends
> `FormationAttackFlightPlan` and does not loiter — `CasFlightPlan` is the
> `PatrollingFlightPlan`. Nothing times an Air Assault by the ground war either:
> `auto_asap` is set only for the first AEWC package and for player packages. Both
> exclusions are unexamined scope, not mechanism; include them if you want them.

**The pass:**

- Providers: packages whose `primary_task` is `SEAD` or `DEAD`. Read
  `max_threat_range` off the target with `getattr(..., None)` and skip on `None` or a
  ring `<= 0` — duck-typed so a non-TGO tasking degrades to "no window" rather than
  crashing.
- Consumers: packages in `COORDINATED_STRIKE_TYPES` that are **not** `auto_asap` and
  **not** `has_players`.
- Match on `p.target.position.distance_to_point(package.target.position) <= ring`.
- Several strikes behind one SEAD mass into the same window. That is the point — it reads
  as a push.

**Players are immune, providers are read-only.** A package with a player flight is never
rescheduled. A player-flown SEAD still *opens* a window the AI pushes behind, because
providers are only read.

**Where the call goes.** After the main scheduling loop (so it sees final TOTs) and
before the recovery-tanker ETA filtering (so those are collected against the coordinated
TOTs). In your tree that is immediately above the `# division by 2 is meant to provide
some leeway...` comment.

> Your scheduler has no carrier-recovery stagger. 414Ret's runs this pass *before* its
> stagger; the stagger only ever delays, so it can nudge a strike deeper into its window
> but never back ahead of its SEAD. If you add a stagger later, keep that order.

**Setting:** `sead_strike_coordination: bool`, Campaign Doctrine → General, **default
`False`**. `Iterator, TYPE_CHECKING` in the typing import needs `Optional` added.

### Acceptance

- `tests/test_sead_strike_coordination.py` passes (15 tests) — pydcs plus
  `SimpleNamespace` fakes, nothing from the 414Ret tree.
- With the setting off, the pass returns immediately and no TOT changes.

---

## Feature 3 — Region priorities

**Size:** six files, one new, +230 lines. **Tests:** 18. **Status in 414Ret:** verified
in-game, through a Qt surface not included here.

This landed 2026-08-20 — after your last 414Ret review window closed, so it is in none of
your ledgers.

### What it is

Per-control-point planning emphasis for the **blue** auto-planner. An emphasized region's
targets rank as if at half their distance, a deprioritized region's as if at double, an
ignored region is left to manual packages.

It is the *weighting* answer to the territory red-one1's upstream #686 hard-limits with
navmesh polygons, and to BMS's PAK weights.

**A weight, never a fence.** IGNORED mutes the auto-planner only — a manual package is
never blocked, ROE is untouched, rescue tasking is untouched. 414Ret built the fence
version once (ROE zones) and removed it. This is deliberately not that.

**Two axes, multiplied:**

- **Place** — per control point, with a per-target override that beats it in *both*
  directions, so one target inside an ignored base can still be marked normal and
  planned. Without both directions the override could only ever subtract, which is not
  what a per-target setting is for.
- **Kind** — seven target families. An IGNORED family is **absolute**: no target of that
  kind anywhere, and no per-target override reopens it.

Blue only, by design. Anchored on control points because navmesh polygon ids are rebuilt
from threat zones every turn.

### What to build

**New module `game/regionpriorities.py`** — a `RegionPriority` enum
(`EMPHASIZED`/`NORMAL`/`DEPRIORITIZED`/`IGNORED`), a `SORT_FACTOR` map
(0.5 / 1.0 / 2.0; IGNORED deliberately absent — it drops rather than scales), the
`TARGET_FAMILIES` table, and five functions: `family_of`, `family_priority`,
`priority_of`, `priority_for_target`, `owning_control_point`, `planning_factor`.

Keep it **duck-typed throughout** (`getattr` everywhere) and import `ControlPoint` only
*inside* functions and under `TYPE_CHECKING`. That is what keeps it free of an import
cycle when `controlpoint.py` imports `RegionPriority` from it at module level.

`planning_factor(target, settings, is_blue) -> Optional[float]` is the single gate:
`1.0` when the feature is off, the planner is red, or nothing governs the target; `None`
means drop. Putting the gate here is what keeps every caller a one-liner. `settings` may
be `None` — duck-typed test fakes hold partial games — and absent means off.

`owning_control_point` returns `None` for front lines, convoys and downed pilots. Those
are **never weighted**: a rescue must not rank lower for being in a quiet region.

**`objectivefinder.py`** — two sort sites:

- `_targets_by_range` gains a keyword-only `weighted: bool = False`. When set, compute
  the factor, `continue` on `None`, and multiply into the sort key:
  `target_ranges.append((target, min(ranges) * factor))`. Pass `weighted=True` from
  `threatening_ships`.
- `strike_targets` carries its own sort for the multi-TGO dedup, so it needs the same
  three lines inline.

**`controlpoint.py`** — a `blue_region_priority` property backed by
`_blue_region_priority`, read through `getattr(self, "_blue_region_priority",
RegionPriority.NORMAL)` so pre-feature saves read NORMAL with no migration.

**`theatergroundobject.py`** — `self._blue_region_priority: Optional[RegionPriority] =
None` in `__init__`. `None` means inherit.

**`settings.py`** — `region_priorities: bool` (Campaign Doctrine → General, default
`False`) and `blue_target_family_priorities: Dict[str, str] = field(default_factory=dict)`.
The dict carries **no option metadata on purpose**: the auto settings dialog renders
declared options, and this one is owned by its own window. An absent family reads NORMAL,
so old saves need no migration.

### What this brief deliberately leaves out

- **The tasking gate.** `auto_planning_skips` exists in the module but nothing calls it.
  In 414Ret it gates `AttackShips`, `DegradeIads` and `AttackBattlePositions`. It is
  needed because **`enemy_ships` is threat data as well as a target list** — filtering
  the list itself would route blue over a carrier it had been told to ignore. Gate the
  tasking, never the threat picture. Without those call sites, an ignored region's ships
  and SAMs are still tasked at those tiers.
- **All UI.** No Qt CP-dialog control, no per-target combo, no target-families window, no
  React tooltip. The fields are ordinary attributes; the engine works without them, but
  nothing sets them from the app.

Both are real gaps, not oversights. Decide whether you want them before shipping this to
players.

### Acceptance

- `tests/test_region_priorities.py` passes (18 tests) — factor gates, both axes, the
  override in both directions, the ordering effect, the drops.
- Five further tests exist in 414Ret and are omitted here because they exercise the
  tasking-gate consumers above.
- With the setting off, `planning_factor` returns `1.0` for everything and target order
  is byte-identical to today.

---

## Not in this brief, but worth knowing

**Your SLAM-ER call looks right, and 414Ret has the bug.** Your commit `4b4d2a1` removed
`AGM-84H`/`AGM-84K`/`SLAM` from the jammed set: the GPS/INS leg is only the midcourse,
the imaging seeker comes up well outside a ~15 nm bubble, and degrading it left no sane
way to service a jammer with a stand-off weapon at all. 414Ret still jams all three. The
second half of that reasoning — that a feature should not remove its own counter — is the
part 414Ret missed, and it is being taken back the other way.

**Two features where the two trees answer the same question differently**, written up
rather than offered as patches:

- **Sortie records.** Your `prev_turns` type-aggregates versus 414Ret's per-flight
  records. Your token-cost argument is right for an LLM consumer and stops being right at
  the second consumer — which is how 414Ret ended up with seven private `state.json`
  channels before collapsing them.
  [COMPARISON.md](sortie-records/COMPARISON.md)
- **DTC cartridges.** Your inventory declines them because ED's auto-load is broken. It
  is not — the cause is a per-unit `AutoLoad` block that upstream does not write, and
  414Ret's row went verified with no DTC-page interaction. The flip condition you
  recorded has no fix to wait for. Two caveats 414Ret still carries are in the brief.
  [COMPARISON.md](dtc-cartridges/COMPARISON.md)
