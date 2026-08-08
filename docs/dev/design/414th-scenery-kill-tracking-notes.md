# Scenery strike-target kill tracking — how it works, why it fails, and the proxy unit

**Status:** investigation note + the feature it produced (§88), 2026-08-08. Written to answer the
Discord question "why do some strike targets register as killed and some do not", and to scope the
follow-on ask: reuse the IADS infantry stand-in as a general kill tracker for every strike target.

**What shipped:** `scenery_kill_proxies`, default OFF — one `Fortification.Electric_power_box`
static per live `SceneryUnit`, registered in the unit map, union with the existing trigger. §5 is
the design; **§5.4 is the field evidence, including the reading of it that was wrong** (`Landmine`
is a decal, not a kill tracker); §7 is what the in-game pass has to answer (checklist **B53**).

**The unit is a judgement call, not a measurement.** Nothing in this note establishes that any
static dies when the map building under it dies. B53 is the gate, and its first question is whether
the marker dies at all.

Read this before touching `add_trigger_zone_for_scenery`, `generate_scenery_kill_proxy`,
`generate_iads_command_unit`, or the MANTIS C2 watcher.

---

## 1. The short version

There are **two** kill-tracking mechanisms for strike targets, and only one of them is reliable.

| Target kind | Authored as | Tracked by | Reliable |
|---|---|---|---|
| **Spawned statics** | a `Tech_combine` marker in the campaign `.miz` → Retribution spawns a building layout | DCS `S_EVENT_DEAD` matched on the static's DCS unit name | Yes |
| **Map scenery** | blue category zone + white per-object zones drawn in the ME over real map buildings | a `MapObjectIsDead` trigger rule per white zone, writing the **zone name** into `dead_events` | No — four failure modes, §4 |

Both kinds coexist in most campaigns. That alone produces "some track, some don't".

**§88 adds a third row**, off by default: a registered small static per scenery unit, tracked
by the reliable mechanism in row 1. It is a *union* with row 2, not a replacement — both signals
converge on the same `kill()` and `clean_unit_list` dedups.

The M4 infantryman is **not** part of any of these paths. It is the MANTIS/Skynet in-mission
liveness probe for C2 nodes, and §88 deliberately left it alone. Details in §3.

---

## 2. The two paths, end to end

### 2.1 Spawned statics — the path that works

1. `mizcampaignloader.py:129` — a `Fortification.Tech_combine` static in the campaign miz marks a
   strike location.
2. `start_generator.py:730` `generate_strike_targets` → `generate_building_at(GroupTask.STRIKE_TARGET, …)`
   picks a layout from `resources/layouts/buildings/*.yaml` and builds a `BuildingGroundObject`.
3. `tgogenerator.py:656` `create_static_group` spawns each static via `mission.static_group(name=unit.unit_name)`.
   **pydcs names the group `X` and its unit `"X object"`.**
4. `tgogenerator.py:665` `_register_theater_unit` → `unitmap.py:162` `add_theater_unit_mapping`,
   keyed on the **DCS unit name** (`"0123 | ware1 0-0 object"`).
5. In mission, the static dies → `S_EVENT_DEAD` → `dcs_retribution.lua:247` appends the DCS unit
   name to `dead_events`.
6. `debriefing.py:626` looks the name up via `unit_map.theater_units(name)` → hit →
   `missionresultsprocessor.py:471` `commit_ground_losses` calls `theater_unit.kill(events)`.

Every hop is name-matched on a string Retribution itself minted. Nothing about the DCS terrain can
break it.

### 2.2 Map scenery — the fragile path

1. `scenery_group.py:41` `SceneryGroup.from_trigger_zones` pairs each **blue** zone (carries the
   category in `properties[1]`) with the **white** zones inside it.
2. `start_generator.py:669` `generate_tgo_for_scenery` makes one `SceneryUnit` per white zone,
   `id = zone.id`, `name = zone.name`, and hangs the zone off the unit.
3. `tgogenerator.py:737` `add_trigger_zone_for_scenery` re-creates the zone in the generated
   mission and attaches a rule:
   - alive → `generate_on_dead_trigger_rule` (`tgogenerator.py:785`): a `TriggerOnce` with a
     `MapObjectIsDead(zone.id)` condition whose `DoScript` runs
     `dead_events[#dead_events + 1] = "<zone name>"`.
   - already dead → `generate_destruction_trigger_rule`: a `SceneryDestructionZone` so the rubble
     renders.
4. `unitmap.py:238` `add_scenery` keys the mapping on the **trigger-zone name** — *not* the
   `TheaterUnit.unit_name`.
5. `debriefing.py:675` `unit_map.scenery_object(name)` → `commit_ground_losses` →
   `ground_unit.kill(events)`.

The whole chain hangs on DCS's `MapObjectIsDead` (`c_dead_zone`) condition firing. That condition is
evaluated by the sim against the terrain, not against anything Retribution controls.

---

## 3. What the M4 infantryman actually is

`tgogenerator.py:796` `generate_iads_command_unit`:

```python
self.m.static_group(
    country=self.country,
    name=unit.unit_name,                     # "0123 | <zone name>"
    _type=dcs.vehicles.Infantry.Soldier_M4,
    position=unit.position,
    heading=unit.position.heading.degrees,
    dead=not unit.alive,
)
```

Gated at `tgogenerator.py:422` on all three of:

- the unit is a `SceneryUnit`,
- the `mantisiads` plugin option is on (upstream: `skynetiads`),
- the group is an `IadsGroundGroup` whose `iads_role.participate` is true.

`IadsRole.for_category` (`iadsrole.py:73`) only returns a participating role for **`comms`**,
**`power`** and **`commandcenter`**. Every other scenery category — `ammo`, `factory`, `fuel`,
`oil`, `ware`, `village`, `derrick`, `farp`, `fob`, `allycamp`, `ww2bunker` — gets no soldier.

### 3.1 Why it exists

Skynet and MANTIS need a DCS object handle for a node. A map building is not a `StaticObject` or a
`Group`, so `StaticObject.getByName` / `GROUP:FindByName` never find it. The soldier is a real,
findable object standing in for the building.

### 3.2 How MANTIS consumes it

- `iadsnetwork.py:47` `dcs_name_for_group` returns `unit.unit_name` for `COMMAND_CENTER`,
  `CONNECTION_NODE`, `POWER_SOURCE` and `EWR` roles.
- `luagenerator.py:285` emits it as `dcsGroupName` into the `dcsRetribution.IADS` table.
- `mantis-config.lua:301` `node_dead(node_name)` tests two things, in order:
  1. `StaticObject.getByName(node_name .. " object")` exists **and** `not :isExist()` → dead.
     The `" object"` suffix is exactly pydcs's `static_group` unit-naming convention, so **this
     resolves to the soldier**.
  2. Otherwise, scan the global `dead_events` table for the node name, verbatim or with the
     `"<id> | "` prefix stripped (`bare_name`, `mantis-config.lua:298`). This is the fallback for C2
     nodes that are pure scenery with no static.

The comment block at `mantis-config.lua:287` records why: the original test was `so == nil → dead`,
which read every scenery node as destroyed on the first poll and decapitated the whole network at
mission start.

### 3.3 Why it is not a campaign kill tracker

`generate_iads_command_unit` **never calls `_register_theater_unit` or any `unit_map.add_*`**. So:

- The soldier's DCS unit name is `"0123 | <zone name> object"`.
- The scenery mapping is keyed on `"<zone name>"` (`unitmap.py:239`).
- The theater-unit mapping does not contain the soldier at all.

When the soldier dies its name reaches `dead_events`, misses every lookup in
`debriefing.py:626-706`, and lands in the `untracked` list that gets one summary `logging.debug`
line. The building stays alive in the campaign.

**Net effect today:** killing the soldier takes a comms/power node offline **for the rest of that
mission** (MANTIS degrades the dependent SAMs) and changes **nothing** at debrief. Next turn the
node is back.

### 3.4 A live quirk worth knowing

`Soldier_M4` as a static has infantry hit points. Splash from a bomb tens of metres away, a stray
cannon burst, or cluster submunitions will kill it while the building it represents is untouched.
For comms/power/command-center scenery objectives that means MANTIS can declare a C2 node lost from
collateral damage. Not campaign-visible, but it is in-mission behaviour nobody chose deliberately.

---

## 4. The four ways scenery tracking fails

Ranked by how likely they are to explain the Discord reports.

1. **Map updates move the object off the zone.** Upstream bumped the campaign format to **7.0** "to
   account for DCS map changes that made scenery strike targets incompatible with existing
   campaigns". [dcs-liberation#1894](https://github.com/dcs-liberation/dcs_liberation/issues/1894)
   is the same story: tracking used to key on `event.initiator.id` (the map object ID) and ED
   changed those IDs across map updates, which is exactly why the project moved to the trigger-zone
   approach it uses now. Fully map-dependent — matches the "some maps aren't set up for it"
   instinct.
2. **Non-destructible map objects.** Some scenery has no destructible body. A zone assigned to one
   will never satisfy the condition, whatever the player does to it.
3. **Circular-zone shrink.** `add_trigger_zone_for_scenery` keeps quad-zone polygons verbatim but
   **rebuilds circular zones at a 16 ft (4.87 m) radius**, discarding the authored radius. Audit of
   all 73 shipped campaigns (§6): **3040 white zones, 2903 quad, 137 circular**, all with valid
   `OBJECT ID` properties. Syria's `power_plant_01` is authored at **69.3 m** and regenerates at
   4.87 m. Whether this matters depends on whether DCS's `c_dead_zone` resolves by geometry or by
   the zone's `OBJECT ID` property — **unresolved, see §7 for the test**.
4. **Culling deletes the tracking trigger — upstream only.** Upstream's `generate()` opens with
   `if self.culled: return` **before** the scenery block, so a culled objective gets no zone and no
   trigger, while the map building stays bombable. The fork fixed this (`tgogenerator.py:404-412`);
   upstream [PR #873](https://github.com/dcs-retribution/dcs-retribution/pull/873) is still an open
   draft. **Narrow in practice:** the un-cull list (`game.py:570-614`) includes every non-BARCAP
   package target at a 100 km radius, so a target you were fragged against is always un-culled.
   This only bites opportunity kills and deep-rear targets, and only with `perf_culling` on
   (default `False` on both sides).

Also relevant, and outside our control: ED broke `S_EVENT_DEAD` for scenery objects in
**2.9.7.58923** (map buildings assigned as zones stopped being detected when destroyed). Worth
keeping in mind before betting a design on that event.

---

## 5. The proxy unit — the ask, and what shipped

The idea is sound in principle — the statics path (§2.1) is 100% reliable precisely because it
tracks a unit Retribution spawned and named. Extending that to scenery targets means giving every
`SceneryUnit` a real, registered proxy.

**This is now built** (§88, `scenery_kill_proxies`, default OFF). §5.1–5.3 below are the design as
scoped; §5.4 is the field evidence that answered §5.2's open question and decided the unit.

### 5.1 What the change is

`generate_scenery_kill_proxy` in `tgogenerator.py`, called from `generate()` in the `SceneryUnit`
branch alongside `add_trigger_zone_for_scenery`, gated on `scenery_kill_proxies`:

```python
proxy = self.m.static_group(
    country=self.country,
    name=f"{unit.unit_name} proxy",
    _type=Fortification.Landmine,
    position=unit.position,
    heading=unit.position.heading.degrees,
    hidden=True,
)
self._register_theater_unit(unit, proxy.units[0])
```

`add_theater_unit_mapping` takes a `TheaterUnit`, and `SceneryUnit` **is** one, so
`commit_ground_losses` (`missionresultsprocessor.py:471`) calls `theater_unit.kill(events)` with no
further changes. The existing `MapObjectIsDead` trigger stays — the two signals are a union, and
`clean_unit_list` (`debriefing.py:191`) already dedups.

Four decisions worth recording, because each is a place a later edit could silently break it:

- **The `" proxy"` suffix is load-bearing.** `generate_iads_command_unit` already spawns a static
  named `unit.unit_name` for C2 scenery; pydcs names a static group's unit `"<group name> object"`,
  so without the suffix the `unitmap` duplicate guard raises on every IADS scenery node. Pinned by
  a test.
- **Dead scenery units get no proxy.** A proxy spawned dead can never fire an event, and the
  destruction trigger rule already renders the rubble.
- **`hidden=True`.** It is bookkeeping, and the objective already draws its own F10 zone.
- **The IADS soldier is left alone.** The tempting one-liner — register the existing soldier so C2
  nodes become campaign-trackable for free — is *not* taken: §3.4's infantry hit points make it a
  false-positive generator. Merging the two objects into one landmine would fix both, and is listed
  as deferred work rather than done here, because it changes a flown feature.

### 5.2 What unit to use — settled by §5.4

This was the whole design risk, and it was open when this note was first written:

| Choice | Problem |
|---|---|
| `Soldier_M4` (what IADS uses today) | Dies to splash, strafing, submunitions. Would credit kills on untouched buildings. Do not use. |
| A matching building static | Renders a second building inside the real one. Ugly, and DCS statics have their own HP unrelated to the map object's. |
| A small durable static | Best compromise, but "durable" is not tunable per map object — Retribution has no idea how tough the real building is. |

**§5.4 did not answer it. It ruled one candidate out.** The shipped-campaign evidence looked at
first like it settled the question — those campaigns place `Landmine` statics on target buildings —
but `Landmine` is the one static of pydcs's 230 `Fortification`s whose model is a flat **decal**, and
what those campaigns are doing with it is marking positions. Details in §5.4.

**What §88 ships: `Fortification.Electric_power_box`, and it is a judgement call.** Small enough not
to read as a second building, plausible beside any structure the game calls a scenery objective,
physical, and carrying no weapon, radar or crew. Nothing measured it. Say so when citing this.

The trade-off is unchanged and unresolved. No unit type matches an arbitrary map building's
durability, so **every proxy design trades a false negative (today) for a false positive** — the
campaign credits a strike that did not happen, and the building renders intact next mission while
the map shows it dead. That is why §88 ships default OFF with checklist row **B53**.

**The deeper tension, stated once so it is not rediscovered:** an object with no physical body
probably cannot be killed, and an object that can be killed renders as a visible thing standing on
the map building. There is no invisible-and-killable static. Any proxy design pays one of those two
costs. §8's position matcher pays neither, which is why it is still the better idea.

### 5.3 Volume

Proxies are per **white zone**, not per objective. From §6: `red_tide` 340, Canary Islands 169,
`red_flag_81_2` 139, `exercise_quasar` 129, `operation_peace_spring` 128. A few hundred extra
statics per generated mission on the big campaigns. Tolerable for DCS, but it fights the reason
culling exists. Proxies follow the fork's culling exemption (`tgogenerator.py:404-412`) — culling
them would reintroduce failure mode 4. They spawn `hidden=True`, so they add nothing to the F10 map;
the scenery objective already draws its own zone there.

The number matters more than it looks, because of §5.4's lattice finding: any multiplier applies to
these counts. 340 × 6 is ~2,000 extra statics on `red_tide` alone.

### 5.4 Field evidence — what the shipped campaigns are actually doing

**Read this before proposing `Landmine` for anything. It is a decal.**

Source: **campaign F**, a paid FA-18C Syria campaign in the DM's install, mission 11. Its target
points are `Landmine` statics, and a screenshot of one is what prompted this section. The first
reading of that evidence was "a shipped campaign uses `Landmine` as a kill-tracking proxy, so the
unit question is settled." **That reading was wrong**, and the correction is the useful part.

**What the miz contains.**

- The object is `["type"] = "Landmine"`, `["shape_name"] = "landmine"`, category `Fortifications`,
  spawned on the **red** (target-owning) side, one per aimpoint, named `TGT POINT 1/2/3`.
- The miz has **`["trig"] = {}`, `["trigrules"] = {}`, `["goals"] = {}`** — no ME triggers, no
  trigger zones, no goals at all. Mission logic lives in the encrypted campaign pak, which resolves
  these statics **by name**.
- Nothing else in the miz references them: not by `unitId`, not by `groupId`. Name is the entire
  contract.

**The model is a flat crater decal.** `Bazar/World/Shapes/landmine.lods` points at `voronka.edm`
(Russian *voronka* = crater): **1,547 bytes**, one render node, material `Voronka_10x10`, flagged
`DECAL` with blending and depth bias. No collision mesh, no damage LOD, no destroyed state. Of the
**230** `Fortification` statics pydcs exposes, checked model by model, **`Landmine` is the only
one carrying the `DECAL` flag.** It is a texture stamped on the ground.

**So the campaigns are marking positions, not tracking kills.** Everything fits that reading:

- Four statics named **"Smoke Tower"** appear in *every* mission of two campaigns. Unambiguously
  effect anchors — a named coordinate a script reads with `getByName(...):getPoint()`.
- The clusters below read as an impact-check or aimpoint grid over a footprint, which is a
  *position* use.
- The briefing tells each wingman to "acquire your assigned target point", and the crater art is
  a reasonable thing to have at an aimpoint.

The kill-tracking inference came from the names plus two dictionary strings (`TGT DEAD!!`,
`Target Golf was not destroyed.`). Suggestive; not proof. **`Landmine` is the community's standard
named position marker, and it is unsafe to assume it can be destroyed at all.**

**How widely.** Scanning all 23 installed campaigns for `Landmine` statics: **6 place them.**
Names seen: `TGT POINT 1-3`, `Golf 1 A-F`, `Golf 2 A-G`, `GOLF 3/4`, `Player Target`, `Target-1/2`,
`GAUNTLET TARGET 13A-E`, `Shaft 1/2`, `TGT 1`, `Bunker Landmine`, `LFF East 1/2`, `Smoke Tower`,
`GH Mine`.

**Placement — one per aimpoint, or a lattice.** Still worth recording, because it tells us how these
authors think about a target's extent:

| Pattern | Where it is used | Observed |
|---|---|---|
| One marker per aimpoint | the pilot is assigned that exact point | 3 singles on one building, 46–118 m apart, one per wingman |
| A lattice inside a small box | the impact point is not known in advance | 6 in 11 × 10 m; 7 in 16 × 16 m; and in another campaign 12 in ~15 m, twice; 5 in ~9 m |

The mission's own briefing confirms the split: each wingman is assigned a numbered target point on
the primary building ("the centre of the southeast tower") and gets a single marker, while the
secondary facilities — where the pilot picks their own aimpoint — get lattices.

**What survives for us.** Only the placement observation, and only weakly: Retribution is the second
case, so if a single centre-of-zone proxy turns out to under-detect, a small lattice is the shape to
try. That is a **B53 finding, not a design input** — it was never evidence about durability, because
these markers are not durability tests.

§88 ships **one** proxy per white zone. §5.3's volume is the reason not to guess a multiplier.

---

## 6. Campaign audit data

Script: `tools/check_scenery_targets.py` already validates authoring (blue/white pairing, category,
`OBJECT ID` presence) and is CI-guarded by `tests/fourteenth/test_scenery_targets.py`. The
quad-vs-circular breakdown below came from an ad-hoc pass over the same miz set using the pinned
pydcs (`requirements.txt`).

**Totals: 73 campaigns · 752 scenery objectives · 3040 white zones · 2903 quad · 137 circular · 0
missing `OBJECT ID`.**

Campaigns carrying circular white zones (the fragile subset under failure mode 3):

| Campaign | Circular zones |
|---|---:|
| `mozdok_to_maykop` | 33 |
| `caen_to_evreux` | 27 |
| `golan_heights_lite` | 16 |
| `exercise_quasar` | 14 |
| `operation_dynamo` | 13 |
| `grabthars_hammer` | 9 |
| `syria_full_map` | 7 |
| `syria_TheLongRoadToH3` | 6 |
| `Task Force Thunder` | 4 |
| `TheFalconWentOverTheMountain` | 3 |
| `WRL_Battle4SyriaNorth` | 3 |
| `IntotheHornetsNest`, `WRL_AssaultonDamascus` | 1 each |

Everything else is 100% quad-authored, including `red_tide` (340), `operation_peace_spring` (128),
`iraq_desert_storm` (36) and `red_flag_81_2` (139).

---

## 7. What the in-game pass has to answer

Four questions, one mission, `scenery_kill_proxies` ON. Checklist row **B53** carries the full
setup and fail signatures; this is why each one is on the list.

1. **Does the proxy track?** Frag one strike against a scenery objective and one against a
   spawned-building objective as a control. The scenery kill must survive the turn and still be
   dead next mission, and `state.json` must carry `"<id> | <zone> proxy object"` in `dead_events`.
2. **The false positive.** The one thing that can disqualify the feature. If a building you did not
   hit reads destroyed, note the miss distance — that number decides between shipping it, shipping
   it with a tougher unit, or dropping it for §8.
3. **One marker or a lattice (§5.4).** If you flatten the building and it still does not record,
   the marker survived the hit and the answer is the 5–12 pattern the source campaigns use, not a
   different unit type.
4. **Settle failure mode 3, since you are there.** Generate `syria_full_map` and bomb the
   `Powerplant` objective (circular, 69.3 m authored → 4.87 m regenerated) and the `Tank Factory`
   objective in the same sortie. Check `state.json` for both **zone** names in `dead_events` —
   these are the trigger's own records, separate from the proxy's.
   - Both present → `c_dead_zone` resolves by `OBJECT ID`, the shrink is harmless, close mode 3.
   - Only `Tank Factory` → the shrink is a real bug; fix is one line (keep the authored radius).

**Also check `destroyed_objects_positions`** in the same `state.json`, for entries at the bombed
buildings' coordinates. That is the one dependency of §8's position matcher, which is cheaper than
this feature and needs no units at all. If it is populated, build the matcher next.

---

## 8. The alternative worth considering first: position matching

The fork's Lua **already records the world position of every destroyed object**.
`dcs_retribution.lua:247-266` writes `{x, y, z, type, orientation}` into
`destroyed_objects_positions` for every `S_EVENT_DEAD` that is not a crash model.

That data reaches Python as `StateData.destroyed_statics` (`debriefing.py:381`) and is currently
used for **one** thing: persisting carcasses so wrecks re-render next mission
(`missionresultsprocessor.py:634` `record_carcasses`). It is never used for kill attribution.

A matcher that says *"a destroyed object within N metres of this `SceneryUnit`'s zone centre means
this target died"* would be:

- immune to map-object-ID churn (failure mode 1),
- immune to zone geometry and the 16 ft shrink (mode 3),
- immune to culling, since it needs no generated trigger (mode 4),
- zero new units, zero F10 clutter, no false-positive-from-splash problem,
- ~30 lines in `debriefing.py`, plus a distance threshold to tune.

Its one dependency is that `S_EVENT_DEAD` fires for scenery objects — which test 2 in §7 settles,
and which ED has broken before.

**Still worth building, and it is not either/or.** The proxy shipped first because §5.4 answered its
one open question with hard evidence, and because it works whether or not scenery `S_EVENT_DEAD`
fires. The matcher is cheaper and has no false-positive-from-splash problem, but it has a dependency
the proxy does not: §7's `destroyed_objects_positions` check.

All three signals — trigger, proxy, matcher — converge on the same `kill()` call and
`clean_unit_list` dedups, so shipping two is strictly better than shipping one. Order of work after
B53:

- §7 q2 shows false positives → the proxy is wrong as built; the matcher becomes the primary path.
- `destroyed_objects_positions` is populated → build the matcher regardless. ~30 lines.
- §7 q4 fails → the one-line radius fix, independent of both.

---

## 9. Reference — every file touched by this subsystem

| File | Lines | What |
|---|---|---|
| `game/scenery_group.py` | 41 | blue/white zone pairing, category validation |
| `game/theater/start_generator.py` | 669-706 | `SceneryUnit` creation from zones |
| `game/theater/theatergroup.py` | 202-224 | `SceneryUnit`; `unit_name` = `"<id> | <name>"` |
| `game/missiongenerator/tgogenerator.py` | 404-433 | `generate()`; fork's culling exemption; the §88 gate |
| " | 658-667 | `create_static_group` + unit-map registration |
| " | 739-796 | scenery zone + `MapObjectIsDead` / destruction rules |
| " | 798-851 | `generate_scenery_kill_proxy` — the §88 proxy + the unit rationale |
| " | 841-852 | `generate_iads_command_unit` — the M4 stand-in |
| `game/settings/settings.py` | — | `scenery_kill_proxies` (Features page → Strike accounting) |
| `tests/missiongenerator/test_scenery_kill_proxy.py` | — | the §88 pins (7) |
| `game/unitmap.py` | 162-173 | `add_theater_unit_mapping` (keyed on DCS unit name) |
| " | 238-245 | `add_scenery` (keyed on trigger-zone name) |
| `game/theater/iadsnetwork/iadsnetwork.py` | 46-66 | `dcs_name_for_group` |
| `game/theater/iadsnetwork/iadsrole.py` | 73-99 | `for_category`, `participate` |
| `game/missiongenerator/luagenerator.py` | 285 | emits `dcsGroupName` |
| `game/debriefing.py` | 191-206 | `clean_unit_list` (dedup, int→str for map objects) |
| " | 381 | `destroyed_statics` parse |
| " | 626-706 | loss attribution; `untracked` bucket |
| `game/sim/missionresultsprocessor.py` | 471-481 | `commit_ground_losses` |
| " | 634-636 | `record_carcasses` |
| `game/game.py` | 570-614 | un-cull zone list |
| " | 700-745 | `position_culled`, `iads_considerate_culling` |
| `resources/plugins/base/dcs_retribution.lua` | 247-266 | `S_EVENT_DEAD` → `dead_events` + positions |
| `resources/plugins/mantisiads/mantis-config.lua` | 252-365 | C2 watcher, `node_dead` |
| `tools/check_scenery_targets.py` | — | authoring validator |
