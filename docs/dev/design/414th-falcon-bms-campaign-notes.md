# Falcon BMS's dynamic campaign — study note

Status: **study note, nothing built.** Written 2026-08-20 on the DM's ask. What the BMS
engine actually does, mechanism by mechanism; the crosswalk to what this fork already has;
the four candidates worth considering; and the tombstones this material must not resurrect.

**Sources and limits.** BMS is closed-source freeware. Latest version verifiable from this
container: **4.38.1.1** (Build 3315, Dec 2025), via 4.38.0 (2025-07-01) and 4.38.1 Update 1
(Nov 2025). The egress proxy blocks falcon-bms.com, its forum and wiki, so a newer 2026
release may exist that search does not surface — check
https://www.falcon-bms.com/changelogs/ from a normal connection before citing "current". The original Falcon 4.0 source circulating online is **leaked
proprietary code — not read, and not to be read**, the same licence gate as
`414th-mist-author-repos-notes.md`. Everything here comes from public documentation,
developer interviews and community guides, reached through search summaries because the
egress proxy blocks the BMS wiki and forums directly. Mechanisms are triangulated across
several sources; **specific numbers (the 250 km falloff, the supply-point values) are
community-reported, not primary-verified — re-verify before building on any of them.**
Links in §6.

## 1. What BMS is

Falcon 4.0 (1998) shipped a real-time theater war — the dynamic campaign engine was written
essentially single-handedly by lead engineer Kevin Klemmick — and Benchmark Sims has
maintained and extended it for two decades. One continuous simulation runs the whole war at
all times: every battalion, squadron and flight exists and moves on the 2D map whether or
not the player is flying. The player's mission is a *window* into that war, not a generated
scenario. Retribution generates a scenario per turn and reconciles afterward. Almost every
difference below follows from that one split.

## 2. The engine, in five mechanisms

### 2.1 One war, always ticking — and the bubble

The campaign simulates continuously; time compression runs it faster between sorties. The
famous trick that made a theater war run on 1998 hardware is **aggregation**: units far from
any player are a few bytes (a battalion is a bitfield of alive vehicles, a formation and a
position) resolved by abstract force-on-force math, and **deaggregate** into individual
vehicles only inside a bubble around the player (and around player sensor footprints —
radar/TGP cursors deaggregate what they look at).

### 2.2 The ATO pipeline

Mission generation is request-driven. Campaign systems raise **mission requests** against
targets (a factory worth bombing, a front unit needing CAS, an airbase worth closing). Each
request's initial priority sums **mission-type priority + target-type priority + PAK
(region) priority** — equal weights, all three player-adjustable by slider — **plus a
distance-to-FLOT bonus** (community-documented as decaying to zero at ~250 km) **plus a
small random component**. The engine then finds a squadron, sizes the flight, adds SEAD
and/or escort when the computed threat at the target and along ingress/egress exceeds the
mission type's altitude-banded threshold, routes waypoints around threats, and **cancels the
package outright when the threat exceeds what the mission type will accept**. The player
steers all of it with sliders and can hand-edit or add packages; human-flown results shift
the war like AI ones.

### 2.3 The ground war

Ground battalions move objective-to-objective on the 2D map and fight abstractly; the FLOT
emerges from where units actually stand; **initiative** points shift sides on ground
victories, captured objectives and successful human sorties. Notably, **only 4.38 (2025)
gave 2D ground movement real path-aware routing between objectives** — for 27 years the
premier dynamic campaign moved its ground war on abstractions of the road net.

### 2.4 Initiative and posture — the strategic layer

(Added from the BMS wiki's campaign section, 2026-08-20.) **Initiative points** sit above the
ground war: they shift on ground victories, captured objectives and successful human-flown
sorties, and they set each team's **posture** — Offensive, Minor-Offensive, Defensive, or
Consolidate. A big enough lead puts one team Offensive and forces the other Defensive; a
narrow lead yields only a Minor-Offensive. Crucially, **trigger files can shift initiative
directly**, independent of the military situation — the documented pattern for scripted
political events: an ally enters the war (shift toward that team → offensive), a capital
falls (shift toward the loser → a reconquest offensive).

### 2.5 Logistics — one closed loop

The part everything else hangs off. Factories produce supply, refineries fuel; airlift and
convoys physically move it (a transport landing is community-documented at ~20 supply /
2 fuel / 2 replacement points; scheduled distribution roughly twice an hour); units consume
it, and **supply, morale and fatigue scale a unit's combat effectiveness**. Squadron weapon
stores and airframe replacement ride the same flow — squadrons genuinely run short of jets
and LGBs, and SAM sites shoot dry and rearm off the same net. Cratering a runway **closes
the airbase** (its sortie generation stops until repaired); community consensus is that
runway closure is the *only* airbase strike effect that matters. Interdicting the flow
degrades everything downstream of it.

### 2.6 Victory

Trigger files: capture or hold named objectives, by day where scripted, inside a campaign
time limit. Four endings — Victory, Stalemate, Timeout, Defeat.

## 3. Crosswalk — BMS mechanism vs this fork

| BMS mechanism | Fork state |
|---|---|
| Continuous war, mission = window | Turn-based by design. §89 fakes the window's *feel* (mid-cycle starts, pre-rolled packages, follow-on waves); §47 marches one clock. **Seam 5's audit stands: the fork's gap is reporting, not simulation** — 39 between-turn operations already run; the player just isn't told. `turnless.md` (the inherited make-it-BMS plan) is superseded — do not re-litigate |
| Aggregation bubble | **Impossible and not wanted** — DCS owns the 3D world and cannot aggregate. The fork's culling + §59 ground-AI sleep + §26 abstract resolution is the DCS-shaped equivalent: instantiate near the player, resolve abstractly far away. Same idea, different boundary |
| Request → priority → frag pipeline | Upstream's HTN commander plans from theater state; not request-driven but same job. The **small random component** BMS bakes in is exactly §17 (opt-in reordering) — independent convergence |
| Escort/SEAD sizing by threat | Upstream sizes escorts; §69 retimes strikes behind their SEAD; B75/B78 track the remaining escort-spend defects |
| Cancel-if-too-hot | Partially present (threat-aware routing upstream; §67 weather demotions; B51 wants the rescue version). BMS's per-mission-type acceptable-threat ceiling is the concrete missing shape |
| PAK / region priorities | **No fork analog.** Doctrine emphasis exists globally, nothing regional |
| Ground war from unit positions | §90 rungs A–D are the turn-cadence version: supply-following reinforcement, attack-costs-more, line-counts-forces-present, terrain-slows. BMS 4.38's new path-aware 2D routing arrives at the fork's own **driveable-corridor standard** (2026-07-03) — they got there after us |
| Supply scales combat effectiveness | **Not modeled.** §90 rung A gates *reinforcement* by supply; the units already at the front fight at full strength however cut off they are. The one BMS idea with a cheap fork-shaped hole to land in |
| Production→transport→consumption economy | **Tombstones §48/§53/§54** (political will, war economy, munitions), all removed 2026-07-21. BMS explains *why* they failed here: its economy works because it is one closed loop simulated continuously — production feeds transport feeds consumption feeds combat, each observable. The fork built the bookkeeping without the loop. Do not re-propose them piecemeal; they only exist as the whole loop, and the whole loop is a different game |
| Finite squadron airframes/pilots | Upstream squadrons already persist both; §82 (scheduled arrivals) was removed as not-worth-it. Covered |
| SAM sites shoot dry, rearm off the net | **The parked SAM-magazines note** (`414th-sam-magazines-notes.md`) is exactly this mechanism at turn cadence. BMS corroborates the design, including rearm-from-supply |
| Runway closure stops sorties | **Present.** `ControlPoint.can_operate` refuses a damaged runway (`runway_status.damaged`), squadrons relocate around it, repair runs over turns |
| Campaign-map fog / recon intel | BMS's own community calls its strategic fog weak; recon flights update unit intel on the map. The fork's §3 engage-to-reveal is a *deliberately different* answer, and seam 2's audit capped intel-layer work at a tidy-up. Nothing to take |
| Initiative → posture (Offensive/Minor-Offensive/Defensive/Consolidate) | Split verdict. The *systemic* version is §55 Red Intent — tried, removed, seam 7 dropped. The *authored* version (trigger-file initiative shifts for political events) is exactly what the fork kept: red tempo's turn-windowed surges (M6/W6) and §75's authored victory blocks. BMS validates the path chosen. Note also the fork already has posture at a finer grain: the commander assigns per-front ground stances, where BMS postures the whole team |
| Initiative as a scored currency | Tombstone §48 (political will). Do not restore |
| Victory triggers, four endings | §75 (authored win/lose blocks + domination/attrition endings). Covered |
| Player as theater commander (sliders) | Fork exposes doctrine through settings + the auto-planner; BMS's per-slider live steering is finer-grained but the turn cadence makes settings equivalent in practice |
| Time-compress until interesting, then commit | §83 SP Pilot Mode (accept-and-fly-next, reasons-to-continue brief) is the turn-shaped version; seam 5's reporting reframe covers the rest |

## 4. The four candidates

Smallest first. None started; each carries its own gate.

1. **Supply as a combat-effectiveness multiplier** (§90 extension). A front-line group at a
   supply-cut CP fights at reduced strength — one multiplier riding rung A's existing
   connectivity, applied where §26/§90 already compute combat power. Cheap, legible,
   makes interdiction bite the way BMS's does. Gate: §90's owner pass (B65–B68 are still
   untested — extending an untested model buries the test).
2. **Per-mission-type acceptable-threat ceiling** (the cancel-if-too-hot shape). B51/B75
   already point here. Gate: read `414th-autoplanner-upstream-divergence-audit.md` first —
   planner behavior is re-converged with upstream, and the crowded-zones list names four
   active upstream planning PRs; this may be theirs to build.
3. **FLOT-distance weighting in target priority.** Small planner term, historically the
   thing that keeps a campaign's air war coupled to its ground war. Same gate as 2.
4. **PAK-style region priorities.** A per-region emphasis the player sets on the map,
   weighted into target selection. Real UI + planner work; the only candidate that adds a
   player-facing control surface. Gate: DM appetite — it is a feature, not a fix.
   **Upstream is already in this territory** (DM spot, 2026-08-20): red-one1's
   [#686](https://github.com/dcs-retribution/dcs-retribution/pull/686) (WIP draft, v1.6
   milestone, no reviews) lets the player click navmesh polygons as an Area of Operations and
   then **hard-limits all A2G missions to them**, in the same code sites this candidate names
   (`objectivefinder.py`, `theaterstate.py`). The distinction is load-bearing: #686 is a
   *constraint* (a fence missions may not cross), PAK is a *weight* (0–100 emphasis entering
   the priority sum, where 0 approximates the fence and everything between exists). The fork
   has a verdict on the constraint shape — §40's removed ROE-zones layer was exactly that,
   dropped 2026-07-21 — so if this candidate is ever built it is the weighting version, and it
   coordinates with (or waits out) #686 rather than colliding with it.

Not a candidate but recorded: BMS corroborates the parked SAM-magazines note (§3 table row);
if that feature is ever built, its design needs no change on BMS's evidence.

## 5. What not to take

- **Turnless.** Proposed in-tree once (`turnless.md`, superseded), audited once (seam 5:
  the gap is reporting), rejected twice. BMS is the existence proof it *can* work — as a
  game built around it from day one, which Retribution is not.
- **The aggregation bubble.** DCS owns the 3D world. The fork's instantiate-near/
  resolve-far boundary is the correct translation, already built.
- **The economy loop, piecemeal.** §48/§53/§54 died here once. BMS shows the loop only
  works whole and continuous. Candidate 1 deliberately takes the *smallest consuming end*
  of the loop (effectiveness) without the production side — that is the line, hold it.
- **Anything about red.** BMS's red runs the same planner mirrored, topped by the
  initiative→posture layer (§2.4) — and that layer is the system §55 already tried here and
  removed. Retribution mirrors the planner today; the posture layer's authored half survives
  as red tempo and triggers. Seam 7 stays dropped; the red-brain Phase 0 note governs.

## 6. Sources

- **BMS wiki campaign section** (reached via domain-scoped search — the proxy blocks direct
  fetch): [campaign index](https://wiki.falcon-bms.com/en/bms-campaign) ·
  [Campaign Initiative](https://wiki.falcon-bms.com/bms-campaign/initiative) (the §2.4
  posture mechanics) · [changelog index](https://wiki.falcon-bms.com/en/changelogs) (newest
  indexed entry 4.38.1.1; 4.38.1 also reworked the TvT campaign and integrated the F-35A)
- [BMS 4.38 release](https://www.falcon-bms.com/blog/the-wait-is-over-falcon-4-38-is-here) ·
  [4.38 changelog](https://wiki.falcon-bms.com/changelogs/4-38/release) (campaign entries:
  HAVCAP/BARCAP/TARCAP/RESCORT/AMBUSHCAP evaluation refactors; path-aware 2D ground routes) ·
  [Update 1](https://www.falcon-bms.com/news/falcon-bms-4-38-update-1-is-out/)
- Engine internals (community documentation): the BMS forum guide "How to rationalize the
  Dynamic Campaign engine" (mission-request pipeline, priority weights, threat ceilings) ·
  BMS forum threads on campaign priorities, squadron logistics, supply chain, airfield
  strikes · [Mudspike campaign tips](https://forums.mudspike.com/t/falcon-bms-dynamic-campaign-tips-and-tricks/15619)
- History: [Falcon 4.0](https://en.wikipedia.org/wiki/Falcon_4.0) · combatsim.com's period
  review "Campaign AI, Player Bubble, Force on Force" · the 2024 Klemmick interview
  (CombatACE) and the Falcon 4 history site's earlier one.

## 7. Owed

Candidates 1–4 are offers with named gates, not commitments. If one is picked up, it gets
its own note; this one stays a study. One standing watch line: the 4.38 changelog marks its
HAVCAP/BARCAP/TARCAP/RESCORT/AMBUSHCAP mission-evaluation refactors as "to prepare for new
code" — when the next BMS release lands (check the changelog index; the DM may see the
announcement before search does), read its campaign section for what those refactors were
preparing. That is the one place their engine is visibly mid-change.
