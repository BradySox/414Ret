# 414th — Campaign Maker (blank-start foundation) — design notes

**Status:** in progress. Increment 1 (pure policy core) landed (PR #120).
Increments 2–3 (terrain glue + wizard "Blank canvas" entry) built and
**headless-verified**; the live in-game pass (fly a blank campaign) is still
pending. Scoped 2026-06-23.

> **Runnability gate: PASSED headless (2026-06-23).** A blank Caucasus theater
> (21 airfields, 11 blue / 10 red, nearest-neighbor fronts) was run through the
> real `GameGenerator.generate()` → `begin_turn_0()` pipeline outside the UI and
> reached turn 0 cleanly. The feared "no ground fronts → crash" was **not** the
> blocker (the default front graph runs fine). The only real fix was the air-wing
> config: an empty campaign passes a plain `{}` to `CampaignAirWingConfig`, but
> `DefaultSquadronAssigner` does `by_location[cp]`, which `KeyError`s unless the
> dict is a `defaultdict`. Fixed via `CampaignAirWingConfig.empty()`. A blank
> canvas therefore starts with **0 squadrons** — the player staffs bases via the
> `AirWingConfigurationDialog` the wizard already shows next; that dialog's
> add-from-scratch UX is the remaining thing to confirm in-game.

**Vision:** start from an empty theater and build a campaign by hand — assign
airfield ownership, drop in SAMs / armor / strike targets, author airwings, save &
play. The "major release" the squadron flagged. This note covers the **foundation**:
the *blank canvas* — every airfield on a chosen map, assignable ownership, **no**
preset SAMs/armor/objectives/fronts — loaded into the normal UI so the existing
placement tools (drop-spawn §20, scenery targets, squadron model) can fill it in.

---

## REDESIGN — the neutral-paint flow (current direction, 2026-06-23)

Playtest feedback: the first cut auto-assigned sides and auto-drew connectivity —
"I would hardly call that blank." The real flow the user wants:

1. **Setup** — generate *every* airfield on the terrain as **neutral (gray)**, no
   fronts, no units.
2. **Paint** — the player clicks bases on the **live map** to cycle gray → blue →
   red (chosen interaction model; the alternative wizard base-list was declined).
3. **Finalize** — **drop every still-gray base**, derive the front from where blue
   meets red, build support buildings, then the player staffs airwings, then start.

**Why gray bases must be pruned, not just hidden (the "sneak-in" gotcha):** each
side's planner only sees its own bases (`player_points`=blue, `enemy_points`=red),
but `ObjectiveFinder` pulls `control_points_for(NEUTRAL)` as **capture/expansion
targets** (`game/commander/objectivefinder.py:392`). So an unpainted gray base is
something the AI tries to seize. Dropping unpainted bases at finalize removes that
path and keeps them off the map entirely.

### Feasibility — both gates PASSED headless (2026-06-23)

- An **all-neutral** Afghanistan (25 gray CPs) runs through `GameGenerator.generate()`
  → `begin_turn_0()` to turn 0. So the engine can hold an empty paintable game.
- Full backbone: setup 25 gray → paint 7 blue / 5 red → `ownership_from_theater` →
  `generate_blank_theater(ownership=…)` **pruned the 13 gray bases**, kept 12 with
  correct sides + 23 derived front pairs → generate + turn 0, **0 neutral remaining**.

### Architecture / increments

- **Increment A — backend backbone ✅ (built + headless-verified):**
  `game/campaignloader/blanktheatergen.py` now has three modes:
  `all_neutral=True` (setup, all gray, no fronts), `ownership={name: Player}`
  (finalize — only painted bases kept, sides assigned, fronts derived), and the
  legacy auto-split fallback. Plus `ownership_from_theater()` to read painted
  ownership off the setup theater. Front derivation reuses the policy core's
  `nearest_neighbor_links` over the *kept* bases.
- **Increment B — server + map paint UI (NEXT, can't verify in CI):** wizard
  "Build your own" generates the all-neutral game and enters a **setup mode**; a
  FastAPI endpoint flips a CP's coalition on click (SSE refresh, like drop-spawn
  §20); a "Finalize" endpoint reads ownership → rebuilds via `generate_blank_theater`
  → `GameGenerator` → `begin_turn_0` → returns the real game; React renders neutral
  CPs gray and cycles them on click. **Until this lands, the wizard keeps the legacy
  auto-split** so there is no unusable all-gray intermediate.
- **Increment C — support buildings:** finalize should procedurally place economy
  structures (factories/depots/etc.) for owned bases. Retribution normally gets
  these from the `.miz`; blank canvas must synthesize them. Biggest remaining
  unknown; deferred.
- **Increment D+ — save a hand-built theater as a reusable campaign.**

### Airfield count caveat

`terrain.airport_list()` returns pydcs's named-airbase set (e.g. 25 for
Afghanistan). DCS ME may show more (FARP pads / helipads pydcs doesn't expose as
airbases) — that's a pydcs terrain-data limit, not something the generator can add.

Sibling pieces already built: drop-spawn (§20, right-click unit placement),
scenery strike-target data (`scenerycatalog`, PR #115/#117), fog reveal (§18).
This note is the spine they hang off.

---

## How a campaign is instantiated today (the seam)

`qt_ui/windows/newgame/QNewGameWizard.py` `accept()`:

1. Pick a **`Campaign`** (`Campaign.load_each()` — pre-authored YAML + `.miz` pairs
   in `resources/campaigns/` and the user's saved-games dir).
2. `theater = campaign.load_theater(advanced_iads)` →
   `TheaterLoader(name).load()` builds the empty `ConflictTheater`, then
   `MizCampaignLoader(miz, theater, data).populate_theater()` parses the `.miz` into
   control points, supply routes, preset SAM/objective/scenery locations.
3. `GameGenerator(blue, red, theater, air_wing_config, settings, …).generate()` →
   `Game`.
4. `AirWingConfigurationDialog(...)`, then `game.begin_turn_0(...)`.

**Everything keys off a `Campaign` (YAML + `.miz`).** The blank canvas has to slot
in at step 1–2: produce a `ConflictTheater` *without* a hand-authored `.miz`.

## Where the control points come from

`MizCampaignLoader.control_point_from_airport()`
(`game/campaignloader/mizcampaignloader.py:134`) is the whole recipe for an airfield
CP:

```python
cp = Airfield(airport, theater, starting_coalition, ctld_zones=[])
```

`starting_coalition` is just `Player.BLUE` / `Player.RED` / `Player.NEUTRAL`. The
airfields themselves come from `mission.terrain.airport_list()`. So a blank theater
is, in essence:

```
for airport in terrain.airport_list():
    theater.add_controlpoint(Airfield(airport, theater, coalition_for(airport), ctld_zones=[]))
```

— no `.miz` required. Connectivity (where ground fronts can form) is added with
`ControlPoint.create_convoy_route(to, waypoints, spawns)`
(`controlpoint.py:729`), called once per direction per link.

---

## The pure-core / glue split

Same pattern that worked for `scenerycatalog`: keep the **map-agnostic decisions**
free of pydcs so they're unit-testable without loading a (heavy) DCS terrain, and
isolate the terrain-binding glue for the in-game pass.

### Increment 1 — pure policy core ✅ (this PR)

`game/campaignloader/blanktheater.py` (+ `tests/test_blanktheater.py`, 9 tests):

- `AirfieldSite(name, x, y)` — a candidate CP as a plain point.
- `assign_coalitions(sites, inverted=False) -> {name: is_blue}` — deterministic
  geographic split along the axis of greatest spread, median cut, with a guard that
  guarantees both coalitions are present. So a fresh map isn't all one colour.
- `nearest_neighbor_links(sites, k=3) -> set[frozenset[name,name]]` — proposes a
  ground-connectivity graph for when the player wants fronts rather than a pure air
  war. De-duplicated, undirected.

No Retribution imports; pure stdlib. These are the decisions worth pinning down and
testing; everything below is glue.

### Increment 2 — terrain glue (`BlankTheaterGenerator`) — NEXT, needs in-game pass

A `game/`-layer builder, no Qt:

```
def generate_blank_theater(terrain_name, *, inverted=False, with_fronts=False) -> ConflictTheater
```

1. `theater = TheaterLoader(terrain_name.lower()).load()`.
2. Build `AirfieldSite`s from `terrain.airport_list()` (`airport.name`,
   `airport.position.x/.y`).
3. `owners = assign_coalitions(sites, inverted)` → create one
   `Airfield(airport, theater, Player.BLUE/RED, ctld_zones=[])` each;
   `theater.add_controlpoint(cp)`.
4. If `with_fronts`: `nearest_neighbor_links(sites)` → for each pair, both-direction
   `create_convoy_route` with straight-line waypoints between CP positions.
5. `theater.iads_network = IadsNetwork(advanced_iads, [])` (empty), mirroring
   `Campaign.load_theater`'s tail.

**Open runnability question (the gate):** does the rest of the engine tolerate a
theater with **no** ground connectivity (`with_fronts=False`)? Navmesh build,
threat-zone math, conflict detection, and the AI commander may assume at least one
front. First in-game pass must answer this. If it doesn't run clean, default the
blank canvas to `with_fronts=True` (auto k-NN graph) until the pure-air path is
hardened. **Fail signature to watch:** crash/empty-plan during `GameGenerator.generate`
or `begin_turn_0` on a theater with zero `connected_points`.

### Increment 3 — wizard entry (`Qt`, not CI-type-checked)

A top-level **"Campaign type"** choice on the **Introduction page**: a radio pair
"Play an included campaign" (default) vs "Build your own (blank canvas)", registered
as the `blankCanvas` wizard field. (First cut buried this as a checkbox in the
theater page's Map Settings group; user feedback moved it up front where the
include-vs-build fork belongs.) When blank canvas is on, `accept()` calls
`generate_blank_theater(campaign.data["theater"], …)` + `CampaignAirWingConfig.empty()`
instead of `campaign.load_theater()`; the campaign still selected on the theater page
only chooses the terrain. Everything downstream — `GameGenerator` /
`AirWingConfigurationDialog` / `begin_turn_0` — runs unchanged. Headless-verified the
page builds and the field toggles (offscreen `QApplication`); the live add-from-scratch
air-wing UX is the remaining in-game check.

> **Note — the #121 stacked-merge hazard (2026-06-23):** Increments 2–3 first
> merged as PR #121 whose *base* was the (undeleted) `claude/campaign-maker-blank-start`
> branch, so it merged into that side branch, not `main` — the glue silently never
> reached `main`. Recovered by cherry-picking the glue commits onto a fresh branch
> off `main`. Lesson: don't stack a PR on a branch that's about to merge-and-not-delete;
> target `main` directly or confirm the base is deleted so GitHub retargets.

### Increment 4+ — the editor proper (the long arc)

Re-own airfields after generation, save/load a hand-built theater as a reusable
campaign, author fronts by drawing, richer ownership presets. These build on the
blank canvas + drop-spawn; out of scope for the foundation.

---

## Risks / unknowns

- **Runnability with no fronts** — the Increment-2 gate above. Biggest unknown;
  can't be settled in CI (no game runtime here), needs a manual run.
- **Squadron assignment** — `GameGenerator` + `DefaultSquadronAssigner` may expect
  campaign-provided squadrons; an empty air-wing config needs verifying.
- **Persistence** — saving an edited blank theater as a campaign is a later
  increment; the generated `Game` itself pickles like any other.
- **Airfields are fixed to the terrain** — blank start *assigns ownership of* the
  map's real airfields; it can't place new airbases (FOBs/FARPs/carriers are the
  only freely-placeable bases, via drop-spawn later).

## Testing

Increment 1 is fully unit-tested (split correctness on both axes, inversion,
both-coalitions guarantee, degenerate all-same-point, single/empty, link de-dup +
`k`). Increments 2–3 are gated on the in-game pass — add a row to
`docs/dev/414th-ingame-pass-checklist.md` when the glue lands, with the no-fronts
runnability criterion + the fail signature above.
