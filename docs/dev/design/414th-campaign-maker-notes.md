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
- **Increment B — server + map paint UI (in progress):**
  - **Paint = server-side ✅ (built, headless-verified):** `PUT /control-points/{id}/coalition`
    (`blue`/`red`/`neutral`) calls `ControlPoint.assign_setup_coalition(game, player)`
    (re-binds `starting_coalition` + live `_coalition`) and pushes an SSE
    `update_control_point` — the exact drop-spawn §20 mutation pattern.
    `ControlPointJs` gained a `neutral: bool` so the map can render gray. Verified:
    a CP cycles gray→blue→red→gray and the JS model reflects it each step.
  - **Finalize = Qt-side ✅ (built):** game *lifecycle* (new/load) is Qt-driven
    (`onGameGenerated` → `GameUpdateSignal.game_loaded`); the FastAPI server has **no**
    precedent for swapping the whole game, so finalize is a Qt "Finalize Campaign"
    toolbar action (visible only when `game.blank_canvas_setup`). It calls
    `finalize_blank_canvas(setup_game)`, which **reconstructs** the generation inputs
    from the setup game itself (factions / settings / budgets / date — no param stash) →
    `generate_blank_theater(ownership=…)` → `GameGenerator.generate()`, then runs the
    air-wing dialog → `begin_turn_0` → `onGameGenerated`. The wizard "Build your own"
    now generates **all-neutral** + sets the flag + skips the air-wing dialog (bases
    aren't owned until finalize). Headless-verified end to end (paint 6 blue/4 red →
    finalize prunes 15 gray → turn 0, budget carried).
  - **React ✅ (built, type-checked):** neutral CPs already render **yellow** via the
    `UNKNOWN` SIDC — no rendering change. In setup mode (`blank_canvas_setup` from
    `GameJs`, stored in `mapSlice` as `blankCanvasSetup`) a left-click cycles a base
    neutral→blue→red→neutral via `PUT /control-points/{id}/coalition` (raw `backend`
    axios, SSE recolors it); right-click cycles backward. `ControlPoint.neutral` +
    `Game.blank_canvas_setup` were added to the **committed** generated client
    (`_liberationApi.ts`) because CI's `npm run build` type-checks but does not run the
    API codegen. `tsc --noEmit` clean; the CP-layer jest test passes.
  - **Status:** the whole loop — wizard → paint on the live map → Finalize → staff
    airwings → play — is built and verified short of an actual flight. Remaining: the
    live in-game pass (checklist BC-rows).
- **Increment C — support buildings ✅ (minimal pass landed):**
  `_synthesize_support_buildings(game)` runs at the tail of `finalize_blank_canvas`.
  For every **owned** control point it places a small economy — a **factory**
  (income) plus an **ammo** and **fuel** dump — built from the coalition's building
  force groups via `ForceGroup.generate` (the same templates drop-spawn §20 and the
  campaign generator use), positioned on land near the base by `_nearby_land_point`
  (fans out by index across 4/6/8 km rings, skips sea). Neutral/soon-pruned bases
  are skipped. Without this a blank canvas finalized to **+0 income** (pure
  airfields; `Airfield.income_per_turn == 0`, income comes only from `REWARDS`
  building categories). Verified headless (Afghanistan 4 blue/3 red): 21 buildings,
  0 on neutral, blue 208/turn + red 156/turn. **PR #155.**
- **Increment C.2 — default air-defence / armor seeding + richer economy ✅
  (built + headless-verified, 2026-06-27):** the "plays like a real campaign out of
  the gate" pass. `_seed_air_defenses_and_armor(theater)` runs in
  `finalize_blank_canvas` **before** `GameGenerator.generate()`, populating each
  owned base's **`preset_locations`** (a SHORAD + EWR ringing the field, a forward
  MERAD + a BASE_DEFENSE armor group pushed toward the nearest enemy base — counts
  are tunable module constants; geometry land-validated against the theater). This
  routes the SAMs/EWR/armor through the **engine's own ground-object generator**
  (`generate_aa`/`generate_ewrs`/`generate_armor_groups`) — exactly the path a real
  campaign's `.miz` presets feed — so the SAMs/EWR **wire into the IADS** at
  `begin_turn_0` (`initialize_network`) and the armor becomes BAI targets, with no
  bespoke placement code. A faction lacking a template for a task degrades
  gracefully (the generator logs + falls back / skips). The economy mix also gained
  **OIL** (`_BLANK_CANVAS_BUILDINGS`). Empty `tgo_config` is safe —
  `get_unit_group_for_task` falls back to `armed_forces.random_group_for_task`.
  **Headless-verified (Caucasus):** 4-base canvas with `[CH] Russia 2020` → 32
  ground objects (BASE_DEFENSE/SHORAD/MERAD/EWR/FACTORY/AMMO/FUEL/OIL ×4) and **11
  IADS nodes after `begin_turn_0`**; a sparse blue (PMC-USA) correctly degrades
  MERAD→SHORAD and drops EWR. **Still deferred:** building-on-runway/overlap
  avoidance beyond the land check, per-base variety/scaling, seeding the front-line
  ground-unit *inventory* (`base.armor`) for a real FLOT push (only BASE_DEFENSE
  armor TGOs are seeded today). Needs an in-game pass (fly a finalized blank canvas).
- **Increment D — save a hand-built theater as a reusable campaign (DESIGN SPIKE
  2026-06-27; keystone proven headless, not yet built).** See the dedicated design
  section **"Increment D — save-as-campaign"** below.

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

---

## Increment D — save-as-campaign (BUILT 2026-06-27; needs an in-app click-test)

**Goal.** Bottle a hand-built theater (a finalized blank canvas + drop-spawned
units + the §C.2 default laydown) as a **reusable campaign** that shows up in the
New Game list like any shipped campaign — so a built map can be replayed fresh
(different date / factions / settings), not just resumed as a one-off `.retribution`
save. This is the "major release" payoff.

**Status: D.1 + D.2 + D.3 all BUILT.** Core (`game/campaignloader/blankcampaign.py` +
the `Campaign.load_theater` branch + `tests/test_blankcampaign.py`) is headless-verified;
the **Qt "Save as Campaign" toolbar action** (`QLiberationWindow.saveCampaign`, gated by
the new `Game.from_blank_canvas` flag set at finalize) writes the YAML into
`Retribution/Campaigns`. Headless-confirmed end to end: finalize sets the flag →
`save_blank_campaign` writes `my-test-war.yaml` → `Campaign.from_file` loads it as
**compatible (shows in New Game)** → `load_theater` rebuilds the laydown. The only
unexercised step is the literal button-click + name dialog (checklist BC-H).

### The seam

A `Campaign` = a YAML descriptor + a `.miz`. `Campaign.load_theater`
(`campaign.py`) loads the terrain, then `MizCampaignLoader.populate_theater()`
parses the `.miz` into control points, supply routes and preset SAM/armor/building
locations. The whole New-Game wizard keys off `Campaign.load_each()`, which scans
`<saved games>/Retribution/Campaigns` **and** `resources/campaigns`.

### Three approaches considered

1. **Write a real `.miz`** (reverse `MizCampaignLoader`). "Proper" — the saved
   campaign is indistinguishable from a shipped one — but requires authoring a
   pydcs `Mission` with placeholder groups that exactly match every
   `MizCampaignLoader` parsing convention (CP airfields, supply-route vehicle
   groups, preset SAM/armor/building/IADS naming). High effort, fragile, and most
   of it is redundant for a blank canvas. **Rejected.**
2. **Just pickle the `Game`.** Already possible (a finalized game saves like any
   other). But it's a *resume*, not a *reusable* campaign — no New-Game entry, no
   re-roll of date/factions/budget. Doesn't meet the ask. **Insufficient alone.**
3. **`.miz`-less blank-canvas campaign (RECOMMENDED).** A blank-canvas theater is
   already built **without a `.miz`** (`generate_blank_theater` +
   `_seed_air_defenses_and_armor` + drop-spawn). So don't write a `.miz` — serialize
   the *inputs* that produced the theater (terrain + ownership + the ground-object
   graph) into the campaign YAML itself, and teach `Campaign.load_theater` to
   **rebuild** from that descriptor instead of parsing a `.miz`.

### Keystone — PROVEN headless (2026-06-27)

The rebuild primitive already exists and is faithful: serialize a built theater's
ownership → `generate_blank_theater(terrain, ownership=…)` reproduces an **identical**
theater. Verified on Caucasus (4 painted bases): same control points, same sides,
same 12 derived front-edges, `ROUND-TRIP MATCH: True`. So the terrain + ownership +
fronts spine round-trips for free; the only net-new work is **(a)** serializing the
ground objects, **(b)** the `load_theater` branch, and **(c)** the save UI.

### Descriptor schema (lives in the campaign YAML)

```yaml
name: "My Hand-Built War"
theater: Caucasus
version: <current CAMPAIGN_FORMAT_VERSION>   # honor the version gate (see notes)
recommended_player_faction / recommended_enemy_faction / dates / money: …  # normal
blank_canvas:                 # presence of THIS key routes load_theater to the rebuild
  ownership: { Anapa-Vityazevo: blue, Krymsk: red, … }   # airfield name -> side
  ground_objects:             # the hand-placed + seeded TGOs, serialized as raw units
    - side: blue
      category: <TGO.category>          # e.g. "aa", "armor", "factory", "ewr"
      task: <GroupTask.name or null>    # SHORAD / MERAD / BASE_DEFENSE / FACTORY / …
      anchor_airfield: Anapa-Vityazevo  # nearest owned CP it attaches to
      groups:
        - units: [ { type: <dcs_unit_type_id>, x: …, y: …, heading: … }, … ]
```

Serializing **raw units** (not a layout name) sidesteps the fact that a placed
`TheaterGroundObject` doesn't remember which `TgoLayout` built it — and round-trips
exactly what's on the map (the §C.2 seed, drop-spawn §20, and scenery alike).

### Build plan (phased; each phase its own PR + headless gate)

- **D.1 + D.2 — serializer + `.miz`-less load path + laydown ✅ BUILT + HEADLESS-VERIFIED
  (2026-06-27).** `game/campaignloader/blankcampaign.py`: `serialize_blank_campaign(game)`
  captures ownership + a `sites` list (anchor CP + side + **`GroupTask` + position** per
  ground object), `blank_campaign_document(game, name=…)` wraps it in a full campaign YAML
  (stamped `version = CAMPAIGN_FORMAT_VERSION` so the New-Game gate doesn't hide it), and
  `build_blank_theater_from_descriptor(terrain, descriptor, advanced_iads)` rebuilds.
  `Campaign.load_theater` branches on the `blank_canvas` key → the builder, **else** the
  existing `MizCampaignLoader` path (shipped campaigns untouched).
  **The key design improvement over the original D.2 plan:** rather than serialize raw units
  and reconstruct ~17 TGO subclasses via a `category`→class factory, the rebuild stores the
  **laydown intent** — re-populating each CP's `preset_locations` keyed by the site's
  `GroupTask` (`_TASK_TO_PRESET`), so the **normal** `GameGenerator.generate()` places every
  site through its own battle-tested path (`generate_aa`/`generate_ewrs`/`generate_armor_groups`/
  `generate_factories`/…). That **eliminates the TGO-factory entirely**, wires the IADS for
  free (`begin_turn_0` → `initialize_network`), and is **cross-faction-safe** (re-rolling with a
  different faction generates appropriate units; no unit-availability landmine). Storing intent
  not exact units means a placed S-300 re-rolls as "some LORAD" — acceptable v1; exact-layout
  fidelity is deferred. Tasks with no preset generator (FUEL/OIL flavour buildings) and
  dynamic/naval objects are **not** round-tripped.
  **Verified:** pure logic unit-tested (`tests/test_blankcampaign.py`: map validity, serialize,
  site→preset routing, version stamping). Full headless round-trip through the **real**
  `Campaign.from_file` → `load_theater` → `GameGenerator.generate()` (Caucasus, 4 bases,
  `[CH] Russia 2020`): ownership matches and every preset-native task count matches exactly
  (BASE_DEFENSE/SHORAD/MERAD/EWR/FACTORY/AMMO 4↔4); FUEL/OIL drop as designed.
- **D.3 — Qt "Save as Campaign" action ✅ BUILT (2026-06-27).** A toolbar action
  (`QLiberationWindow.saveCampaign`) visible only on a finalized blank-canvas game
  (gated by the new persisted `Game.from_blank_canvas` flag, set in
  `finalize_blank_canvas`; `__init__`/`__setstate__` default False). It prompts for a
  name (`QInputDialog`), calls `save_blank_campaign(game, …/Retribution/Campaigns, name)`
  (slug filename, `_slugify`), and confirms. New-Game lists it via the existing
  `load_each()` scan — no wizard change. The **version gate** is handled in
  `blank_campaign_document` (stamps the live `CAMPAIGN_FORMAT_VERSION`, so the campaign
  is not hidden — `[[campaign-version-gate-gotcha]]`). No thumbnail is generated: the
  terrain's own menu thumbnail is reused by `Campaign.from_file`. The write helper is
  unit-tested; only the literal click + dialog need an in-app pass (BC-H).
- **D.4 — polish.** Squadron/air-wing presets in the descriptor (so a saved campaign
  can pre-staff bases), supply-route overrides, FOB/FARP capture, round-trip of
  drop-spawn respawn flags.

### Risks / open questions

- ~~**Faithful TGO rebuild (D.2)**~~ — **RESOLVED by the intent-based rebuild:** the
  preset-locations approach routes every site through the normal generator, so the IADS
  wires for free and no TGO-subclass factory exists to get wrong (headless-confirmed:
  11 IADS nodes on the §C.2 verification; exact preset-native counts on the round-trip).
- ~~**Unit-type availability across factions**~~ — **RESOLVED:** storing the laydown *intent*
  (task) not exact units means rebuild draws from whatever faction is re-rolled, so there is
  no cross-faction unit-availability landmine. The cost is exact-layout fidelity (deferred).
- **Version gate.** Handled — `blank_campaign_document` stamps the live
  `CAMPAIGN_FORMAT_VERSION` so New-Game does not hide the saved campaign
  ([[campaign-version-gate-gotcha]]).
- **Deferred (D.4 polish):** exact-layout preservation (store the chosen group, not just
  the task) + FUEL/OIL/flavour buildings (a post-generation pass like
  `_synthesize_support_buildings`, which needs a generated game — not available in
  `load_theater`) + squadron/air-wing presets in the descriptor (pre-staff bases) +
  drop-spawn respawn flags. The only outstanding *verification* is the BC-H in-app
  click-test (the button/dialog itself).
