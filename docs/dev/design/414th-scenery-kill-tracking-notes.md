# Scenery strike-target kill tracking — how it works, why it fails, and the proxy unit

**Status:** investigation note, 2026-08-08. **No code changed.** Written to answer the Discord
question "why do some strike targets register as killed and some do not", and to scope the
follow-on ask: reuse the IADS infantry stand-in as a general kill tracker for every strike target.

**The conclusion, up front: the reported failure was never reproduced.** In the only flown sample
that contains scenery kills, the stock `MapObjectIsDead` trigger caught **11 of 11** (§8.1). A proxy
feature was designed, built and **reverted** on that basis — §5 keeps the design and the reasons. The
position matcher was measured and **has no input today** — §8.

What this note is worth keeping for: the mechanism end to end (§2), what the M4 infantryman actually
is (§3), the four failure modes (§4), the 73-campaign audit (§6), and two measurements taken from
archived flown saves that cost nothing to have made (§8.1).

Read this before touching `add_trigger_zone_for_scenery`, `generate_iads_command_unit`, the MANTIS
C2 watcher, or before proposing a proxy unit — §5.2 and §5.4 will save you the round trip.

---

## 0. RESOLVED 2026-08-16 — it was never the scenery path

**Read this before anything below.** The long-standing complaint that a destroyed strike target
does not register was reproduced, traced and fixed on 2026-08-16 (session `c86c58dd`). **The cause
is not in this subsystem.** Nothing in §§1–9 was wrong; the kills never reached any of it.

**That was one bug, not the only one. A second, independent cause was fixed 2026-08-30 — see
§8.6.** It is in this subsystem: an objective sharing its zone with indestructible scenery could
never be credited at all. The two are unrelated and both were real.

What actually happened, from the flown files:

1. The player launched the turn-2 mission, then **aborted it after ~100 seconds** and returned to
   the menu. DCS wrote `state.json` with `mission_ended: true`.
2. `PollDebriefingFileThread` read that file, logged **"Mission end detected; stopping poll"** at
   14:05:24, and **broke out of its loop permanently**. Its only staleness guard is an mtime newer
   than the current `.miz` — which an aborted run of that same `.miz` satisfies.
3. The player relaunched and flew the real 49-minute sortie, destroying three of the four Tuapse
   dock buildings (`TARANTULA`, a `ware` BuildingGroundObject at Maykop-Khanskaya). DCS recorded
   all three by zone name in `state.json`, along with their `_CRUSH` destroyed-shape models.
4. At 14:58:41 the player accepted the results. `_process_turn` committed `self.debriefing` — the
   **two-minute snapshot from the aborted run**. The 53 minutes in between, including the strike,
   were never read.

Proof it is not the scenery path: rebuilding a `Debriefing` from that same final `state.json`
against a generated unit map credits all three buildings, and committing it flips them dead.
Measured, not argued — the reproduction is `tests/test_final_debriefing.py` plus the scripted
end-to-end run recorded in that session.

**The fix** is `game/finaldebriefing.py`: the results commit re-reads `state.json` from disk and
uses it whenever it carries more recorded events than the polled snapshot, keeping the polled one
if the fresh read is shorter (a partial write, or a file already replaced by the next mission).
Map-independent by construction — nothing in it touches terrain, campaign or target type.

Two smaller things found in passing and fixed:

- `clean_unit_list` now drops empty names. The flown `state.json` carried **4** of them; they can
  never match anything and only inflated the untracked-deaths count that a reader uses to judge
  whether something real went unrecorded.
- `1835 | Airport Military Terminal object` in `dead_events` is **not** a scenery building. It is
  the MANTIS command stand-in — the M4 infantryman of §3 — spawned by `generate_iads_command_unit`
  and never registered in the unit map, so its death is always untracked. Left as-is deliberately:
  it is a liveness probe, not an objective, and crediting its death to the building would mark a
  standing building destroyed. Recorded here so the next reader does not re-chase it.

What is still **not** established: which DCS map-object ids the four numeric untracked deaths in
the *aborted* run's `state.json` belonged to. That file was overwritten and the ids cannot be
resolved. It does not block anything — those deaths belong to a run that was thrown away.

---

## 1. The short version

There are **two** kill-tracking mechanisms for strike targets, and only one of them is reliable.

| Target kind | Authored as | Tracked by | Reliable |
|---|---|---|---|
| **Spawned statics** | a `Tech_combine` marker in the campaign `.miz` → Retribution spawns a building layout | DCS `S_EVENT_DEAD` matched on the static's DCS unit name | Yes |
| **Map scenery** | blue category zone + white per-object zones drawn in the ME over real map buildings | the base script matches each scenery death to the nearest objective by position and writes the **zone name** into `dead_events` (§8.6) | Yes, since 2026-08-30 |

Both kinds coexist in most campaigns. That alone produces "some track, some don't".

A third row — a registered static per scenery unit, tracked by the reliable mechanism in row 1 —
was built and reverted. It works in principle and the design is preserved in §5, but no observed
failure justified it: see §8.1.

The M4 infantryman is **not** part of either path. It is the MANTIS/Skynet in-mission liveness probe
for C2 nodes. Details in §3.

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
2. **Non-destructible map objects — FIXED 2026-08-30, see §8.6.** Some scenery has no destructible
   body. Because `MapObjectIsDead` was true only once **every** object in the zone was dead, one
   indestructible neighbour (a `WOODPILE_01` reports a life of `1e38`) held the whole objective
   alive forever. This was the mode that actually bit, and it is now gone: the trigger is no longer
   generated and deaths are matched by position instead.
3. **Circular-zone shrink.** `add_trigger_zone_for_scenery` keeps quad-zone polygons verbatim but
   **rebuilds circular zones at a 16 ft (4.87 m) radius**, discarding the authored radius. Audit of
   all 73 shipped campaigns (§6): **3040 white zones, 2903 quad, 137 circular**, all with valid
   `OBJECT ID` properties. Syria's `power_plant_01` is authored at **69.3 m** and regenerates at
   4.87 m. Whether this matters depends on whether DCS's `c_dead_zone` resolves by geometry or by
   the zone's `OBJECT ID` property — **unresolved, see §7 for the test**.
4. **Culling deletes the tracking trigger — upstream only, and NOT a defect. Settled 2026-08-08:
   upstream is right and this row is listed here only so it is not re-raised.** Upstream's
   `generate()` opens with `if self.culled: return` **before** the scenery block, so a culled
   objective gets no zone and no trigger while the map building stays bombable, and the kill is
   never recorded. The fork exempts the scenery apparatus from culling
   (`tgogenerator.py:404-421`); the carve of that exemption,
   [PR #873](https://github.com/dcs-retribution/dcs-retribution/pull/873), was **self-closed
   2026-07-21**.

   Two maintainer objections, and both hold:

   - **Starfire13, in review on the PR itself:** "any map object strike target in a culled region
     that is the mission objective of a package is not actually culled." Confirmed from the code.
     `compute_unculled_zones` (`game.py:875-955`) adds **every non-BARCAP package target** as a
     culling zone, and `position_culled` (`game.py:1048-1059`) spares anything within
     `perf_culling_distance` — **100 km** by default. A target you were fragged against, and every
     air defence within 100 km of it, is always generated.
   - **The primary dev, 2026-08-08:** *"if you cull the map you shouldn't be able to strike a
     strike target in a culled area. That culled area probably had air defenses to protect the
     strike target and you technically cheated by culling and then striking the culled area."*

   The second follows from the first. Since a fragged target is never culled, the **only** scenery
   this code path can reach is more than 100 km from every package target, every front line and
   every carrier — a deep-rear opportunity kill against a building whose defences were deleted for
   frame rate. Recording that kill pays out on the exploit. Dropping it does not. Upstream's
   behaviour is correct, however it was arrived at.

   **The fork keeps its exemption** (call 2026-08-08) — `perf_culling` is default `False` on both
   sides, so it almost never fires, and consistency between what the player sees collapse and what
   the campaign records is worth more to a squadron campaign than closing an exploit nobody is
   running. Do not re-carve it.

   **One separable half, not an exploit and still unfixed upstream:** the same early return also
   skips `generate_destruction_trigger_rule`, so scenery destroyed in an *earlier* turn renders
   **intact** in any culled region. The player sees a building they legitimately flattened standing
   again, and bombing it now does nothing at all. That is a straight defect and independent of the
   kill-credit argument. Not raised while the upstream PR freeze is on.

Also relevant, and outside our control: ED broke `S_EVENT_DEAD` for scenery objects in
**2.9.7.58923** (map buildings assigned as zones stopped being detected when destroyed). Worth
keeping in mind before betting a design on that event.

---

## 5. The proxy unit — designed, built, reverted

The idea is sound in principle — the statics path (§2.1) is 100% reliable precisely because it
tracks a unit Retribution spawned and named. Extending that to scenery targets means giving every
`SceneryUnit` a real, registered proxy.

**It was built as §88 (`scenery_kill_proxies`, default OFF) and reverted the same day.** Not because
the design is wrong. Because no observed failure justified it: the reported symptom was never
reproduced, and in the only flown sample containing scenery kills the stock trigger caught 11 of 11
(§8.1). Shipping unvalidated machinery — a settings field, a registry entry, a checklist row, and a
marker unit chosen by judgement — for a failure that cannot be demonstrated was the wrong trade.

§5.1–5.3 are the design as scoped, kept so a future attempt starts from here. §5.4 is the field
evidence, including the reading of it that was wrong.

**The entry condition for picking this up again is a reproduction**: a save, a log, or a mission
where a scenery strike target demonstrably failed to register.

### 5.1 What the change was

A `generate_scenery_kill_proxy` on `GroundObjectGenerator`, called from `generate()` in the
`SceneryUnit` branch alongside `add_trigger_zone_for_scenery`, behind a setting:

```python
proxy = self.m.static_group(
    country=self.country,
    name=f"{unit.unit_name} proxy",
    _type=<see 5.2>,
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

**The build settled on `Fortification.Electric_power_box`, and it was a judgement call.** Small
enough not to read as a second building, plausible beside any structure the game calls a scenery
objective, physical, and carrying no weapon, radar or crew. **Nothing measured it.** That is a
reason to distrust it, not a recommendation — if you rebuild this, treat the unit as unresolved.

The trade-off is unresolved in both directions. No unit type matches an arbitrary map building's
durability, so **every proxy design trades a false negative (today) for a false positive** — the
campaign credits a strike that did not happen, and the building renders intact next mission while
the map shows it dead. Too tough or unkillable and the whole thing is a silent no-op instead.

**The deeper tension, stated once so it is not rediscovered:** an object with no physical body
probably cannot be killed, and an object that can be killed renders as a visible thing standing on
the map building. There is no invisible-and-killable static. Any proxy design pays one of those two
costs. §8's position matcher would pay neither — but §8 also shows it has no input today, so it is
not the ready-made alternative it looks like.

### 5.3 Volume

Proxies are per **white zone**, not per objective. From §6: `red_tide` 340, Canary Islands 169,
`red_flag_81_2` 139, `exercise_quasar` 129, `operation_peace_spring` 128. A few hundred extra
statics per generated mission on the big campaigns. Tolerable for DCS, but it fights the reason
culling exists. **Proxies would have to be culled, not exempted** — §4 mode 4 settled that a kill in
a culled region should not be credited at all, and a proxy standing in a region whose air defences
were deleted for frame rate is the exploit in object form. They would spawn `hidden=True`, so they
add nothing to the F10 map; the scenery objective already draws its own zone there.

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
case, so if a single centre-of-zone proxy ever turns out to under-detect, a small lattice is the
shape to try. It was never evidence about durability — these markers are not durability tests.
§5.3's volume is the reason not to guess a multiplier: 340 white zones on `red_tide` times six is
~2,000 extra statics per generated mission.

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

## 7. What is actually still open

Nothing is pending an in-game pass — there is no feature built to fly. Two questions remain, neither
urgent.

1. **A reproduction of the reported failure.** This is the gate on doing any of the work in §5 or
   §8.5. What is needed is one save, log or mission where a scenery strike target demonstrably did
   not register. Without it every fix here is speculative. Red Tide will not produce one — its stock
   path works (§8.1).
2. **Failure mode 3, the circular-zone shrink.** Cheap, and independent of everything else. Generate
   `syria_full_map` and bomb the `Powerplant` objective (circular, 69.3 m authored → 4.87 m
   regenerated) and the `Tank Factory` objective in the same sortie. Check `state.json` for both
   zone names in `dead_events`.
   - Both present → `c_dead_zone` resolves by `OBJECT ID`, the shrink is harmless, close mode 3.
   - Only `Tank Factory` → the shrink is a real bug; fix is one line (keep the authored radius).

**Do not re-run the `destroyed_objects_positions` check.** §8 settled it from two archived flown
saves: scenery `S_EVENT_DEAD` fires, and the position record still never happens for buildings. No
sortie changes that.

---

## 8. Position matching — the Python-side table cannot feed it; the Lua side can

**Read §8.6 first. §§8.1–8.5 are correct about the path they measured — the Python-side
`destroyed_objects_positions` table — and that path is still unusable. They do not describe the
path that was built: matching at event time in Lua, where the position is available and
ungated. The section title said "does not work today" and was read as "cannot work".**

**§§8.1–8.4 were rewritten 2026-08-08 after the claims in them were checked against flown saves.
The original version was wrong in a way that would have wasted the work. It is reconstructed at
§8.4 so the mistake is not repeated.**

### 8.1 What the data says

Two archived flown Red Tide saves, in `Saved Games\DCS\Retribution\Saves\Claude needs these\`:

| | M2 (2026-08-01) | M1 (2026-07-11) |
|---|---:|---:|
| `dead_events` entries | 4,809 | 3,419 |
| of those, numeric map-object ids | 4,743 | 3,346 |
| `destroyed_objects_positions` entries | 83 | 93 |
| **buildings among those positions** | **0** | **0** |

`red_tide.miz` authors an `OBJECT ID` property on all **341** white zones. Cross-matching those
against M2's `dead_events` gives **11 exact hits** — `Haina IADS CmdCenter Bldg`, `Power Hub 20-23`,
`Rail Platform 29-34`. So:

- **Scenery `S_EVENT_DEAD` fires.** The handler runs, `getName()` returns the map-object id, and
  `dcs_retribution.lua:248` records it. This needs no flight to establish; it is in the saves.
- **The position record never happens for those objects.** All 83 M2 position entries are vehicles
  and statics.
- **The existing trigger caught all 11 as well** — every one of those zone *names* is also in
  `dead_events`, written by `generate_on_dead_trigger_rule`'s `DoScript`. Both signals fired for
  every scenery target killed in the only flown sample that contains any.

### 8.2 Why the position record is missing

`dcs_retribution.lua:245-264`. The name is appended at **:248**, *before* the position block. Then
four gates stand between the event and the append at :261:

1. `event.initiator.getName` must exist (:245),
2. the name must not be a player despawn (:247),
3. `destruction.type ~= nil` (:257),
4. the two crash-model string tests (:258-259).

Gate 3 is the one that bites: `getTypeName()` returns nil for map buildings. The evidence is that
**map objects with a type name do pass** — `CONCERTINA_WIRE_CRUSH` produced 28 position records in
M2 and 20 in M1, and one entry typed `Haina` came through in M1. So `getPosition`, `getTypeName` and
`mist.getHeading` all work on map objects generally; the buildings are filtered, not crashing.

Not fully conclusive. The three calls at :249-255 are unguarded, and `mist.getHeading`
(`mist_moose_shim.lua:163-175`) returns nil on a falsy position with no pcall
(`mist_moose_shim.lua:755-763`), so a raise would also produce this signature — and would skip
`dirty_state` at :262 as well.

### 8.3 What that means for the matcher

**The matcher has no input.** It cannot be built today at any line count, because the table it reads
contains no buildings.

Three further problems the original section did not raise, all still live if the input is ever fixed:

- **Coordinate frame.** pydcs `Point` is 2-D `(x, y)`. DCS `getPosition().p` is 3-D with `y` as
  altitude MSL. The mapping is Lua `x` → `Point.x`, Lua `z` → `Point.y`, Lua `y` discarded. Three
  shipped sites already do this (`game.py`, `debriefing.py`, `missiongenerator.py`). Writing
  `Point(entry["x"], entry["y"])` type-checks, compares northing against altitude, silently never
  matches, and looks exactly like "the event doesn't fire".
- **Credit-all-within-N over-credits.** An objective's scenery zones sit metres apart by
  construction, so a radius rule marks neighbours dead too and `is_dead` trips early. Nearest-wins,
  or point-in-polygon using the predicate already in `game/scenery_group.py`, avoids it.
- **`LiveUnitIndex.occupied()` (`game/spatialindex.py`) returns a bool**, not a nearest neighbour.
  Reusable only if you iterate zones and query, not the other way round.

Two of the four advantages originally claimed do not hold either. **Culling immunity is not an
advantage at all** — §4 mode 4 settled that a kill in a culled region should not be credited, so a
matcher that works through culling is crediting the exploit, and it would need a `position_culled`
guard of its own. "No false-positive-from-splash problem" is not supported — a distance threshold
*is* the splash problem in different coordinates.

### 8.4 The claim that was wrong, kept on the record

> "`destroyed_objects_positions` already records the world position of every destroyed object […]
> Its one dependency is that scenery `S_EVENT_DEAD` still fires, which B53's flight settles in the
> same sortie."

Both halves fail. "Every destroyed object" is false — four gates, and empirically zero buildings
across two flown missions. The stated dependency was already answered before the sentence was
written, and it was never the actual dependency: the event firing is necessary, not sufficient.

The decision rule that followed it — *"`destroyed_objects_positions` is populated → build the
matcher regardless"* — was the dangerous part. That table **is** populated. With vehicles. A
superficial check of the file passes the test and gives the wrong answer.

Only one thing is consumed only by `record_carcasses`, and that part was right:
`StateData.destroyed_statics` (`debriefing.py:142`, parsed at `:314`) reaches exactly one consumer,
`missionresultsprocessor.py:556`.

### 8.5 If a second signal is still wanted, this is the order

1. **Harden the Lua block.** pcall :249-255, record the destruction when `getTypeName()` is nil, and
   stamp `destruction.id = name`. Small, testable in the existing `tests/lua/` harness, and worth
   doing on its own merits because it also protects `dirty_state` at :262. It is the prerequisite
   for anything downstream, and it produces the data that would settle this properly.
2. **Then prefer an id-keyed match over a position match.** The 11 M2 hits prove the key is already
   authored on every white zone (`OBJECT ID`) and already arrives in `dead_events`. Matching ids is
   exact and needs no distance threshold at all — a few lines in `unitmap.py`. It inherits failure
   mode 1 (ED churns object ids across map updates), so it is *not* the map-update-immune story
   position matching was sold as. It is simply correct when the ids agree.
3. **Weigh it honestly against doing nothing.** In the only flown sample that contains scenery
   kills, the existing trigger caught 11 of 11. A third path would have added zero.

### 8.6 BUILT 2026-08-30 — matched in Lua, adopted from upstream #957

Adopted from [dcs-retribution#957](https://github.com/dcs-retribution/dcs-retribution/pull/957)
(juanjux), which is open upstream, not merged. It fixes §4 mode 2.

**What §§8.1–8.5 got right, and the one thing they did not ask.** The measurement was of
`destroyed_objects_positions`, the table the Python side reads. That table really does contain no
buildings, for the reason §8.2 gives, and a matcher fed from it really cannot be built. What was
never measured is the same match done **in Lua at event time**, inside the `S_EVENT_DEAD` handler,
where `getPoint()` works on the initiator and none of the four gates has run yet. That is where it
is now done, so §8.2's gate analysis does not apply to it.

**§8.5's third bullet was measured on too narrow a sample.** It read: *"in the only flown sample
that contains scenery kills, the existing trigger caught 11 of 11. A third path would have added
zero."* True of those two Red Tide saves. Not true generally — upstream measured one Kola mission
at **978 scenery deaths, 15 of them direct hits on named objectives**, with **three objectives
recording nothing across three turns while being levelled each time**. Red Tide's zones happened
not to contain indestructible scenery; Kola's do.

**The mechanism.**

- `LuaGenerator._seed_scenery_objectives` emits `RETRIBUTION_SCENERY_ZONES` — every `SceneryUnit`
  with its name, position and alive/dead state — as one `TriggerStart` `DoScript`.
- `dcs_retribution.lua` matches a numeric-named `S_EVENT_DEAD` initiator to the nearest zone and
  appends that **zone name** to `dead_events`, which is the key `unit_map.add_scenery` already uses.
- `generate_on_dead_trigger_rule` is deleted. The `MapObjectIsDead` triggers go with it — 342 in one
  mission.
- Unmatched scenery is dropped instead of appending its id, which also takes several hundred dead
  entries out of `state.json`.

**Constraints, and how each §8.3 objection is answered.**

- **`SCENERY_MATCH_RADIUS = 30` is measured, not chosen.** The tightest successful match observed was
  **29 m**; collateral died from **31 m** out. Do not lower it below 30.
- **Coordinate frame** — `point.x → zone.x`, `point.z → zone.y`, Lua `y` (altitude) discarded. This is
  the trap §8.3 named; the shipped code does it correctly, so do not "fix" it.
- **Over-crediting** — nearest-wins plus a one-shot latch per zone (`scenery_zone_reported`), not
  credit-all-within-N. This is the answer to §8.3's second bullet.
- **Already-dead objectives are still seeded**, marked dead and pre-counted. They are in the list to
  *own* the deaths around them: the destruction zone replays their rubble at mission start, and those
  deaths would otherwise be credited to whichever live objective was nearest.
- **The fork's culling exemption is untouched.** It lives in `GroundObjectGenerator.generate`, not in
  `add_trigger_zone_for_scenery`, so §4 mode 4's settled position stands unchanged.

**Not settled, and flagged by the author.** A `_CRASH` rubble model dying also credits the objective.
At 0–1 m it is the same spot and the latch stops a double count, but it has had no explicit decision.

**Still open, unchanged by this.** Failure mode 1 (ED churns object ids across map updates) is
untouched — position matching does not depend on ids, but the authored zones still have to sit on the
buildings. Mode 3 (circular-zone shrink to 4.87 m) is unaffected either way: the match is to the
zone's *position*, not its radius, so a shrunk zone now matters less than it did.

**In-game pass: B63.** The LOCAL fly card row for it is unchanged and is now the falsifier for this.

---

---

## 9. Reference — every file touched by this subsystem

| File | Lines | What |
|---|---|---|
| `game/scenery_group.py` | 41 | blue/white zone pairing, category validation |
| `game/theater/start_generator.py` | 669-706 | `SceneryUnit` creation from zones |
| `game/theater/theatergroup.py` | 202-224 | `SceneryUnit`; `unit_name` = `"<id> | <name>"` |
| `game/missiongenerator/tgogenerator.py` | 404-431 | `generate()`; fork's culling exemption |
| " | 656-665 | `create_static_group` + unit-map registration |
| " | 737-794 | scenery zone + `MapObjectIsDead` / destruction rules |
| " | 796-807 | `generate_iads_command_unit` — the M4 stand-in |
| `game/unitmap.py` | 162-173 | `add_theater_unit_mapping` (keyed on DCS unit name) |
| " | 238-245 | `add_scenery` (keyed on trigger-zone name) |
| `game/theater/iadsnetwork/iadsnetwork.py` | 46-66 | `dcs_name_for_group` |
| `game/theater/iadsnetwork/iadsrole.py` | 73-99 | `for_category`, `participate` |
| `game/missiongenerator/luagenerator.py` | 285 | emits `dcsGroupName` |
| `game/debriefing.py` | 191-206 | `clean_unit_list` (dedup, int→str for map objects) |
| " | 142, 314 | `destroyed_statics` field + parse |
| " | 626-706 | loss attribution; `untracked` bucket |
| `game/sim/missionresultsprocessor.py` | 471-481 | `commit_ground_losses` |
| " | 555-556 | `record_carcasses` — the only consumer |
| `game/game.py` | 570-614 | un-cull zone list |
| " | 700-745 | `position_culled`, `iads_considerate_culling` |
| `resources/plugins/base/dcs_retribution.lua` | 245-264 | `S_EVENT_DEAD` → `dead_events` + positions (§8: buildings are filtered out at :257) |
| `resources/plugins/mantisiads/mantis-config.lua` | 252-365 | C2 watcher, `node_dead` |
| `tools/check_scenery_targets.py` | — | authoring validator |
