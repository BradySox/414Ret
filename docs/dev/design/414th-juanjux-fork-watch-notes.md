# juanjux's fork — a second high-signal source (WATCH, established 2026-08-19)

`juanjux/dcs-retribution` is the personal fork of upstream's most prolific
non-maintainer contributor. It is not a competitor and not an upstream: it is a
second fork of the same base, run to the same standards, finding the same class of
defect we do — and finding some of them first.

- Fork: https://github.com/juanjux/dcs-retribution (default branch `master`)
- His working integration branch is `juanjux-dev`; `master` carries the built fork.
- He is the reviewer whose objection closed our #851 (HDS Ultimate Compilation).

## Why he is worth watching

Measured 2026-08-19:

| | juanjux | us |
|---|---|---|
| PRs to upstream | 64 (28 merged, 3 open, 33 closed) | 50-odd (9 merged) |
| Own-fork PRs | 100 | comparable |
| Ahead of upstream `dev` | 954 commits / 300 files | comparable |

Overlap with our feature set is high but not total, and the parts that overlap are
mostly *bug* territory rather than feature territory — which is what makes the watch
cheap and productive.

## What his process does that ours does not

**He reproduces offline before fixing.** The strongest example is his #80: rather
than reporting a ~100 s in-mission freeze, he traced it to `json:encode` in
`write_state`, worked out that `getName()` returns a *number* for scenery objects,
proved the cost with a standalone repro on the shipped `json.lua` (numeric key
71610370 → 4.8 s under LuaJIT), and only then wrote a three-line guard.

Our equivalent standard is "flown once, looked right." His is stronger and costs
little. Adopt the habit, not just the fixes.

Two smaller habits worth copying:

- **PR bodies lead with the measurement**, not the rationale. "27 units requested by
  the mission, 0 in `debrief.log`'s `world_state`" settles a question a paragraph
  cannot.
- **Numbered design docs written before the feature** (`ai-docs/00`…`07`), so scope,
  non-goals and risks are on paper before any code exists.

## The traffic is two-way

He ports *from* us, with credit in his changelog ("adapted from the 414Ret fork"):
the unified map-layers panel, DEAD reachability gating, the despawn-loss guard, the
weapons-coverage refresh (without our date gating), AWACS/tanker support orbits, and
§63 ship-launched cruise missiles.

**He also reverted one of ours, and he was right.** His PR #40 backed out the
support-orbit port: in naval scenarios the FLOT anchoring sent AWACS and tankers to
orbit over enemy ship groups, inside the SAM ring. We reverted the same geometry
independently on 2026-08-09 (planner re-convergence work order D). Two forks reached
the same verdict from different evidence — treat that as the strongest confirmation
the re-convergence call was correct, and do not re-litigate it.

One thing he built and then deleted: an EW jamming flight task (his #28/#44/#45,
reverted 2026-06-30 with backup branches). **The reason is now recorded — found
2026-08-24 in his README's "Halted for Now" section, not in the commits**, which is
why the earlier "ask him before assuming" stood for as long as it did:

> after a lot of in-game soak-testing, a *reliable and good* EWAR turned out to be
> basically impossible without proper support from the DCS engine itself. The available
> levers (scripted ROE, missile deletion, engine ECM) don't scale consistently — e.g. a
> few jammers saturate a fleet's radar into total silence, which is neither realistic
> nor fun.

His scope was wider than ours (a dedicated EWAR flight task across EA-18G, EA-6B, Su-34,
Mi-8 and emulated Compass Call / Su-24MP / Tornado ECR, built on upstream's `ewrj`), and
he kept every branch — `juanjux/ew_jamming_parked` is the complete pre-removal state.

**Read this before the B31 and B52 escort-jamming passes.** It is soak-test evidence
against the *saturation* failure mode specifically, which is the one our §77 guards with
non-stacking bubbles and a per-side jammer cap. It is not a verdict on §77 — his levers
and ours differ — but it is the closest thing to a second opinion that exists, and it
came from more in-game hours than we have spent on §77.

## The OPFOR-AI feature — the part we do not have

`game/agent/` (~160 KB of Python: `planner.py`, `views.py`, `service.py`,
`schemas.py`, `session.py`, `mapimage.py`) plus `game/mcp/` and REST routers under
`/retribution-ai/*`. Designed in `ai-docs/00`–`07`. It puts an LLM in the commander's
seat for red.

His statement of the problem is the one our long view records as seam 7:

> `PlanNextAction.each_valid_method` walks the same fixed task-priority list every
> turn, driven by local preconditions, with no model of the player, no memory, no
> concentration of force, no operational shape. It is trivial to read after a few
> turns.

His design principle: **replace the brain, reuse the hands.** The LLM decides what
to do; `PackageFulfiller`, the flight-plan builders, `MissionScheduler` and
`PurchaseAdapter` decide how, and guarantee the result is valid. The LLM is never
asked for waypoints or raw unit data.

Shape worth studying regardless of whether we ever build it:

- **One service layer, three transports.** All logic in `game/agent/service.py`; the
  REST handler and the MCP tool are three-line shims over the same function. A third
  copy-paste transport (compressed blob in a Qt dialog) exists so accounts with no
  API access can still play it.
- **It rides infrastructure that already exists.** The Qt app already runs FastAPI
  in-process against the live `Game` via `GameContext`. Nothing new is spawned.
- **The AI plays by the player's rules.** The exposed action set is exactly what a
  human can do. Cheats — setting budgets, capturing bases, teleporting units, the
  free aircraft +/- — are excluded by design. For anything outside that set the AI
  advises the human in chat and the human decides.
- **The scripted commander stays as fallback**, so red's turn is never empty.
- **The engine change is one branch**: when OPFOR-AI is on, skip the scripted
  planning of red and let the API author the ATO.

Relevant because §55 (Red Intent adaptive posture) was removed 2026-07-21 as the
obvious shape that did not work. This is a different shape: §55 tried to make the HTN
smarter, this replaces the HTN. Read
[414th-retribution-long-view.md](414th-retribution-long-view.md) seam 7 before
proposing anything here.

Nothing about this is adopted. It is recorded so seam 7 has a worked precedent to
argue with.

## Adoption ledger

### Fixed here 2026-08-19 (found by him, verified live in our tree first)

| His PR | Our file | What it was |
|---|---|---|
| #100 | `aircraft/waypoints/holdpoint.py` | An unreachable TOT produced a negative hold-release time. DCS never fires a trigger at a negative time, so the flight orbited the whole mission. Clamped at 0, logged. |
| #79 (1) | `flotgenerator.py` `_set_reform_waypoint` | `timedelta.seconds` on a negative delta gave 86340 s — a front-line group immobilised for 23h59m. Now `total_seconds()`, clamped. |
| #79 (2) | `flotgenerator.py`, three call sites | `DEFENSIVE` groups held until the *enemy's* CAS TOT before moving or returning fire. Only `AGGRESSIVE` waits now. |
| #97 (same hole, our engine) | `iadsnetwork.py`, `luagenerator.py`, `mantis-config.lua` | A destroyed C2 node was dropped from the exported IADS graph, so from the next turn MANTIS had no dependency to watch: the SAMs behind a bombed power station came back fully operational, and killing every command centre restored perfect command instead of removing it. Dead C2 nodes and edges now stay in the graph, and a `DeadC2` list names what the runtime cannot see for itself. |

The IADS one is the consequential one: it silently nullified the whole MANTIS C2
phase-5 layer from turn 2 onward, and §52's decapitation only ever covered the
planner side of the same idea.

### Checked and NOT applicable

| His PR | Why not |
|---|---|
| #79 (3) — `perf_red_alert_state` disarms the ground war | We removed that toggle (#231). Non-IADS groups fall to DCS **AUTO**, never GREEN, and only ships and dedicated EWRs force RED. Forcing the FLOT to RED remains an open *behaviour* question, not a bug. |
| #80 — scenery deaths poison the state encoder | `death_time`/`took_off` are his own tables. Our event records are arrays (`t[#t+1] = name`), so a numeric name is a value, never a key, and no 71M-hole array is built. |
| #94 — SA-10B/S-300PS never spawn | Specific to Auranis HDS 2.1.0, which dropped the S-300PS family. We are on Ultimate Compilation. |

### Adopted here

**PySide6/Qt 6.4.2 → 6.8.3** (his #52), taken 2026-08-19 as 414Ret#905. Four pins, no application
code. On 6.4.x QtWebEngine composites the map through the native desktop-OpenGL driver, whose
context cleanup deadlocks while a fullscreen GPU application — DCS — holds the card; 6.8
composites via D3D11 so that context is never created. Still needs an app pass on non-NVIDIA
hardware (checklist **B86**), because the deadlock is driver-specific and he verified NVIDIA only.

**Two things the bump taught that are worth keeping.** All 132 dotted Qt call paths the app makes
resolve identically on 6.4.2 and 6.8.3 — the code already uses fully-scoped Qt6 enum names, which
is why nothing moved. But **a local mypy run cannot check a dependency bump**: the local venv still
had 6.4.2 installed, so mypy read the old stubs and CI found two type errors a clean install
reproduces immediately. `QWidget.layout()` is now typed `QLayout | None` (more accurate), and
`QObject.findChildren` is now `Iterable[PlaceHolderType]` — an unbindable type variable, so a
**worse** stub than 6.4's, needing the element type at the call site.

**Stand-off ingress by weapon range** (his changelog; the failure is documented at length in
his OPFOR playbook), taken 2026-08-19. The defect was verified live here first:
`Doctrine.max_ingress_distance` is 45 nm on modern doctrine and `ipsolver.py` constrains the
IP to `at_most()` it with **no weapon-range term**, so a stand-off shooter was dragged from
its launch range into the defenses before its attack task existed. A weapon yaml may now
declare `range:` in nautical miles; the package's ingress widens to its **shortest** shooter's
reach, capped at 60% of the departure-to-target leg so the route cannot invert past the join.
Features doc §8, checklist **B87**.

Two things his write-up gets right that are worth repeating: the number is a **planning
bound, not a promise** (DCS releases at its own doctrine distance — he measured ~140 nm for a
YJ-12 and ~130 nm for a Kh-22 that reaches 270+), and **a short-legged flight in a stand-off
package drags the whole package to its attack distance**, which is why the minimum sets the
number rather than the maximum.

**Faction-editor papercuts** (his upstream **#953**), taken 2026-08-23. Three defects in the
Air Wing dialog's faction tabs. All three were verified live in our tree *before* porting, and
his patch then applied to our files with **zero conflicts** — so this is his code, not a
reimplementation of it.

1. **A faction edit never reached the buy menus.** `ArmedForces` is built from the faction once,
   in `Coalition.__init__`, and each `ForceGroup` freezes the units it could reach then. The
   rebuild hung off `preset_groups_changed`, which only `_on_add_preset_group` emitted — so
   adding a *unit* changed nothing you could buy. The signal is now `faction_changed` and every
   mutation emits it.
2. **The tick boxes never removed anything outside the wizard.** `_filter_selected_units` is
   reached only from `QFactionSelection`'s two properties, so unticking a unit from the
   in-campaign Air Wing button did nothing at all. Entries there get a remove button instead,
   gated on an `in_use` callback that refuses while squadrons fly the type or the map has it
   deployed. The checkbox is still built and registered — the wizard's save path reads every
   entry and an unshown one reads as kept.
3. **Both lists sorted by the internal DCS id** while displaying `display_name`/`variant_id`,
   which are unrelated, so the combo boxes looked shuffled. Now case-insensitive by the name
   the player actually reads.

**Drift watch: #953 was OPEN when we took it**, with no reviews. This is a pre-merge adoption of
the kind the adoption-drift rule warns about — re-check our copy against his when it merges, and
expect the `in_use` refusal wording and the remove-button glyph to be the parts a reviewer moves.
Upstream's own test came with it (`tests/test_faction_edit_rebuilds_forces.py`, 5 cases).
Checklist **B94**.
### Checked, and it went the other way

- **His formation-abort cascade does NOT explain our M1 zero-missile finding.** He observed a
  14-flight anti-ship strike fire nothing after a single frigate's SM-6 — the DCS AI going
  defensive and aborting as a formation. That is a genuine third mechanism we had not
  documented, but our M1 case already has its own verified cause: escorts spawned
  `OptROE=OpenFire` ("engage only designated targets") with the designating task attaching at
  JOIN, so the pre-join legal-target set was **empty** and the MiG-29s were mechanically
  unable to return fire. Fixed in 414Ret#581; checklist row A6. Our §81 naval finding is a
  third, separate ROE mechanism (a DCS ship on `ReturnFire` mounts no missile defense at
  all). Three different ways to die without shooting; do not merge them.
- **"SEAD SEARCH and ESCORT SEARCH sit right on the target" does not describe our tree.** Our
  ingress is bounded to 10–45 nm (`min_ingress_distance` / `max_ingress_distance`), not placed
  on the target. His complaint and the stand-off one are the same defect seen from two ends —
  the band is weapon-agnostic — and widening it by weapon range addresses both. His base may
  differ; ours re-converged to upstream's planner on 2026-08-09.

### Already ours, no action

shapely `contains_xy` · escort-leash `mist.DBs.groupsById` · LGB fuze (#919) ·
Super Hornet JSOW station-2 clsid (#918) · convoy name collision (#928, ported as
414Ret#852) · weapon clsid groups (#922) · cloud preset packs (ours as #773) · **ATMOS-X live
METAR weather** (his #927; ours as 414Ret#902, landed 2026-08-19 — the cloud-preset half was
already #773, this is the observation half).

### Open candidates, not taken

| Candidate | Note |
|---|---|
| Base capture zone radius (his #89) | Ours is `TRIGGER_RADIUS_CAPTURE = 3000`. He tested in-game that DCS ground AI engages T-72, BMP-2 and even an unarmed truck, but **never a ZU-23 emplacement** — so one surviving AD emplacement inside 3 km blocks a capture forever and dropped troops cannot clear it. He made it a setting, default 1000 m. |
| IADS rebuild economy (his #97) | Comms/power/command buildings generate no income, so they have no repair price and stay rubble for the rest of the campaign. He priced them flat: 15M power, 10M command centre, 5M comms tower. Turns striking the network into an attrition loop. Sits beside §52. |

## He keeps his own ledger on us — read it first (found 2026-08-24)

Two files in his repo say exactly what he has taken from us and what he has declined,
with reasons. Neither was known to this note before 2026-08-24, and both are cheaper to
read than any diff.

- **`inventario_fork_414ret.txt`** (repo root, Spanish, 374 lines). His decision ledger
  on our fork: 30 numbered features, 13 SÍ / 17 NO, each with an implementation sketch,
  a `PROBADO` flag, an overlap verdict, and — the useful part — a **`Flip a SÍ si:`**
  line naming what would change his mind. It also carries a "YA ES NUESTRO" section
  listing our commits that are really back-ports of *his* PRs, which is the fastest way
  to avoid offering him his own work.
- **`README.md` → "From the 414Ret fork"** — what actually landed, each row crediting the
  original author, plus a **"Queued from the 2026-08 review"** section of what he has
  decided to take but not started. His stated bar: *"every feature carried here is one
  more thing to reconcile on each upstream sync, so the bar is 'clearly worth the
  maintenance', not 'interesting'."*

His last review covered our commits **2026-06-23 → 2026-08-22**. Anything of ours after
that date he has not assessed.

**His standing NO reasons, so we stop re-offering things he has already ruled on:** MOOSE
dependency (hard no — heavy, untestable in Python, third-party code in the repo); the
BARCAP planning family (#9/#10/#11, "no interesa"); anything requiring the fog refactor
(#5 — it breaks the accessors his own map PRs read); and features that are immature or
gated off in our tree.

### Two structural facts that constrain any carve

- **He runs Skynet, not MANTIS.** His `resources/plugins/` has `skynetiads`; he has no
  `mantisiads`. Anything of ours riding MANTIS does not port to him at all — that covers
  §51, §70's red net, the C2 consequences layer and G41.
- **A patch built against our fork point does not apply to him.** `dce851ea` predates
  both trees' upstream syncs; his `tgogenerator.py` is 1,760 lines to that base's 1,636
  and ours' 2,213. Generate against *his* HEAD and verify with `git apply --check`.

### Carve payloads prepared 2026-08-24

[`docs/dev/upstreaming/juanjux/`](../../upstreaming/juanjux/) — three patches verified to
apply at `ca780fd2` (§87 naval station-keeping, §69 SEAD coordination, §93 region
priorities core) and two comparison briefs (§91 sortie records vs his `prev_turns`
aggregates; §74 DTC, whose declined premise our B28 evidence falsifies).

**Nothing has been sent.** The upstream PR freeze binds us, and routing a carve through
him to get around it would be using him as a proxy for a policy we have been told applies
to us. These are for his fork and his testing; what he sends upstream is his call.

### Zero-port test asks

He already ships three of our features that we cannot close a row on. These cost no
porting at all — only his hardware:

| Row | Feature | What is owed |
|---|---|---|
| B39 ◐ | §81 naval magazines | Re-fly with release window back at 120/900 (ours ran with leftover 3600/3600 diagnostics, so no magazine was ever exercised). Pass = AShM launches spread across the mission, a `WINCHESTER` line, the debrief debit matching the track, turn 2 opening with reduced stock. |
| B45 ☐ | §86 GPS jamming | A JDAM strike inside 15 nm of a jammer, with a GBU-12 on the same pass as the control. Pass = the JDAM flies its normal profile and lands ~200 m off, the laser weapon hits, and killing the jammer restores the next JDAM in the same mission. |
| B32 ☐ | §78 coastal batteries | He has the coastal half only (`coastal_batteries_engage_ships`), not the convoy half. Pass = a land-based anti-ship site engages a hull passing in range on its own. |

## Running the watch

Cheap pass, a few minutes:

```
gh pr list --repo juanjux/dcs-retribution --state all --limit 40 --json number,title,state,createdAt
```

Read the `[FIX]` ones first — those are the ones that land in our tree unchanged.
Feature PRs usually collide with something we already solved differently.

Then check what upstream merged of his, since anything merged arrives in our next
sync anyway:

```
gh pr list --repo dcs-retribution/dcs-retribution --author juanjux --state merged --limit 20
```

**Verify every claim against our own files before acting.** Of the five defects
reviewed on 2026-08-19, four were live here and one was not — and the one that was
not (`perf_red_alert_state`) reads identical at a glance.
