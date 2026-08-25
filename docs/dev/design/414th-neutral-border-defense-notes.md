# Neutral-Faction Border Defense — Design Note

**Status: BUILT 2026-08-24 (§96).** Scope locked in a DM Q&A session the same day; every
decision below is a DM call from that session. Read this before editing or re-litigating
any of it. Features doc §96 carries the file list; in-game passes B100/B101 owed.

## Build outcome (what changed between the sketch and the code)

- **The SAM belt is an escalation-time clone, not standing units.** A cold late-activation
  SA-6 template (1S91 + 2×2P25) sits at the field and is SPAWN-cloned under the opposing
  coalition only when a player escalates. No standing red units at a neutral field — which
  also avoids DCS auto-capturing the airbase at mission start. Composition is fixed v1;
  the yaml carries only `sam: true`.
- **The engage task is §61's exact shape**: raw `getController():setTask({id="AttackGroup",
  params={groupId=...}})`, re-set only when the target id changes — not the MOOSE task
  builder. The vector loop uses MOOSE `RouteToVec3` for the benign shadow phase.
- **One fighter template per zone, cloned to either side** via `SPAWN:InitCountry` +
  `InitCoalition` at trip time (template itself lives under the neutral country in the
  neutrals coalition, so it collides with nobody's campaign forces).
- **Reference campaign locked: Into the Hornet's Nest + Lebanon** (DM call). Rayak field,
  MiG-29A (the type Russia offered Lebanon in 2008), 10,000 ft floor, SA-6 on. Desert
  Storm + Iran was investigated and rejected on the evidence: the DS corridor is
  H-3→Baghdad (west) and the map's only Iranian field is Kharg, far south — the border
  would never trip.
- **Border source**: `tools/neutral_border_geo.py` (GeoJSON → shapely simplify →
  `Point.from_latlng` → yaml). The Lebanon trace used the public-domain
  `georgique/world-geojson` country file, 44 vertices. The harness cannot exercise DCS
  behavior — B100/B101 carry the flown verdicts.

## The feature

On a map where most nations are bystanders, a neutral country keeps an alert force at an
airfield near its border. If red or blue violate that border, the neutral scrambles:
shadow first, shoot only if the intruder presses. A third party defending itself — as
theatre, and as a real hazard to a player who cuts the corner.

## Engine verdict (investigated 2026-08-24 — do not re-investigate)

- **A true-neutral unit cannot be made to fire.** Weapons release is gated on coalition
  hostility, not tasking. `AttackUnit` / weapons-free on a `coalition.side.NEUTRAL` unit
  does nothing, a neutral SAM never engages, and the scripting engine has no API to move a
  country between coalitions at runtime.
- **The loophole is spawn-time coalition choice.** `SPAWN:InitCountry` / `InitCoalition`
  override the template's country before `coalition.addGroup`
  (`resources/plugins/base/Moose.lua:20316`); the fork already uses this live
  (`airboss.lua`). The violator's coalition is known at trip time, so alert units spawn
  under the coalition that opposes the intruder.
- **Respawn-in-place under a new coalition exists** as a fallback mechanism:
  `coalition.addGroup` with an existing group name silently swaps the units, firing only
  S_EVENT_BIRTH (`land_relocate.lua` documents it; `mist.dynAdd` implements it). Flown
  only for ships at mission start — an airborne swap is unproven. **Not used in v1** (see
  the accepted risk), but recorded here so the fallback never needs re-research.
- **Generated missions already carry a neutrals coalition with countries**
  (`missiongenerator.py:226`) and neutral-coalition spawns are proven (civilian traffic).
- **Structural template: §61 redscramble** (`redscramble-config.lua`) — late-activation
  templates, `SPAWN:NewWithAlias`, air-spawn overhead the field, forced vectoring onto a
  target group. The engage half of this feature is that plugin's proven mechanism.

## Decisions (DM calls, 2026-08-24)

| Question | Call |
|---|---|
| Combat shape | **Single-flight escalation ladder.** One alert flight spawns red-flagged (visible as red) at the neutral field, shadows the intruder without firing, and on escalation the *same* flight is tasked to engage the group it is shadowing. No two-flight handoff, no coalition swap. |
| Shadow-phase ROE | **Return-fire**, not weapons-hold — a shadower that is shot at defends itself but never initiates. (Refinement inside the "spawn red, do not attack before escalation" call.) |
| Border trigger | **Authored border polygon + altitude floor.** Inside the polygon below the floor for N seconds trips it. A high transit over neutral territory is legal. |
| Who trips it | **Everyone.** Players get the full ladder. **AI intruders are shadowed only — never escalated on.** The planner stays blind (no navmesh hazard; do not reopen the §6 revert). |
| Consequences | **In-mission only for v1.** Nothing persists past the debrief. Escalating posture / joining the war are explicitly future work. |
| Unit tracking | Spawned alert units are **free, untracked event content** — the §61 precedent, called out explicitly against the no-phantom-units constraint. Valid while v1 is in-mission-only. |
| Ground layer | **SAM belt at the neutral field**, red-flagged, ROE weapons-hold, flipped weapons-free by the plugin on player escalation only. ROE-only suppression/release — the §51/§63/§77 mechanism. Never `enableEmission` (hard constraint). |

## Accepted risk (DM call, reaffirmed after the caveat was raised)

A red-flagged shadower is a legal target for every blue AI in sensor range from the moment
it spawns — the intruder's wingmen or a nearby CAP may engage it during the shadow phase,
uninvited. The DM accepted this in exchange for the simpler single-flight build ("it's
fine if they spawn red and show up as red, as long as they do not attack and shadow before
escalation"). Return-fire ROE means the shadower fights back rather than dying passively.
If flown tests show shadowers routinely dying before escalation, the recorded fallback is
the respawn-in-place coalition swap above — do not re-derive it.

Mirror case: a *red* intruder gets a blue-flagged shadower, symmetric behavior.

## Escalation triggers (player intruders only)

1. Dwell — remaining inside the polygon below the floor past a second, longer timer.
2. Weapon release inside the polygon (S_EVENT_SHOT by the intruder group).
3. Firing on the shadower or any unit of the neutral country (also covered by return-fire).

On escalation: shadower goes weapons-free + `TaskAttackGroup` on the shadowed group, and
the field's SAM belt flips weapons-free against that coalition.

## Architecture as built

Planner/Lua split as usual — Python sets up, Lua executes:

- **Python** (mission generation, not campaign state): a `neutralborder` plugin +
  generator that, for each participating neutral CP, spawns the SAM belt and
  late-activation fighter templates as **miz-only units bound to no campaign TGO** (the
  civiliantraffic pattern — regenerated every mission, never in campaign state, so the
  planner and fog never see them). Emits config: border polygon, altitude floor, timers,
  template names, field name, per-side template coalitions.
- **Border authoring (DECIDED 2026-08-24): real border data, converted once by a tool.
  Real-world-georeferenced maps only — fictional-overlay campaigns are out of scope for
  this feature (DM call).** Pipeline: Natural Earth admin-0 boundaries (public domain,
  1:50m GeoJSON) → shapely simplify to a ~48–64 vertex budget → `Point.from_latlng` →
  terrain XY (the calibrated `tools/supply_route_geo.py` machinery) → emitted as a plain
  vertex list in the campaign yaml. New sibling tool `tools/neutral_border_geo.py`; the
  GeoJSON is a dev-time input the tool reads, never vendored, never touched at runtime.
  The author may clip to the war-facing slice of the border (tool flag). Not ME drawings
  (the loader does not read them); not quad trigger zones (4 vertices is not a border).
- **The border is drawn, not invisible** (the §86 lesson): the plugin renders the
  simplified polyline as F10 markup, default on, plus one kneeboard line naming the
  neutral country and the altitude floor. On maps whose baked F10 art draws real national
  borders, the real-data polygon aligns with lines the player already sees.
- **The neutral field needs no control point**: the alert flight air-spawns overhead a map
  airbase found by name (`AIRBASE:FindByName`), so the campaign yaml names any airfield on
  the map — including fields outside the campaign's CP set.
- **Lua** (`resources/plugins/neutralborder/`): timer scan of red+blue airborne units
  against the polygon + floor (point-in-polygon; `bigeye_ewr.lua` has prior art), dwell
  bookkeeping per group, spawn via `SPAWN:NewWithAlias` on the intruder-opposing template,
  follow/shadow tasking, escalation state machine, SAM ROE flip, radio warnings to the
  intruder. pcall-guarded throughout; definition order per Lua 5.1.
- **Two gates as always**: settings toggle + plugin toggle; campaigns must preseed both
  (§36 lesson).

## Settled during the build

- **Shadow spawn is air-start overhead the field** (§61/QRA default). A ground spawn can
  stall or fail on a congested ramp, and a ~0 kt air clone spawns stalled — hence
  `InitSpeedKnots(300)` at field elevation + 760 m.
- **One template set per zone**, cloned per incident with `InitCountry`/`InitCoalition` —
  not two authored sets.
- **Warnings are `outTextForGroup` to the intruder**, not a broadcast sound file. Only
  players see them (an AI stray is shadowed silently).
- **Liveries are left to the template's country default.** A per-campaign livery pin is
  possible later; nothing about the mechanism depends on it.

## Deferred (not built, not promised)

- Cross-mission consequences: escalating posture, airspace closure, the neutral joining
  the war. All were explicitly scoped out of v1 by DM call.
- Per-zone SAM composition in the yaml (fixed SA-6 today).
- Naval or ground border crossings — the watch is airborne groups only.

## In-game passes owed

**B100** (the player ladder end to end) and **B101** (AI shadowed only, plus the
accepted-risk watch: how often the intruder's own side kills the shadower before
escalation). Full setup, pass criteria and fail signatures are on those checklist rows.
