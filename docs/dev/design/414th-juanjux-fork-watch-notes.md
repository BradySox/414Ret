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
reverted 2026-06-30 with backup branches). No reason is recorded in the commits.
**Do not read this as a verdict on our §2/§77** — ask him before assuming.

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

### Already ours, no action

shapely `contains_xy` · escort-leash `mist.DBs.groupsById` · LGB fuze (#919) ·
Super Hornet JSOW station-2 clsid (#918) · convoy name collision (#928, ported as
414Ret#852) · weapon clsid groups (#922) · cloud preset packs (ours as #773).

### Open candidates, not taken

| Candidate | Note |
|---|---|
| PySide6 6.4.2 → 6.8.3 (his #52) | On 6.4.x QtWebEngine composites the map through native desktop-GL, whose context cleanup deadlocks when a fullscreen GPU application — DCS — takes the GPU. 6.8 composites via D3D11. This is the "Retribution goes Not Responding" freeze. A dependency bump needs a real app run, not a test pass. |
| Base capture zone radius (his #89) | Ours is `TRIGGER_RADIUS_CAPTURE = 3000`. He tested in-game that DCS ground AI engages T-72, BMP-2 and even an unarmed truck, but **never a ZU-23 emplacement** — so one surviving AD emplacement inside 3 km blocks a capture forever and dropped troops cannot clear it. He made it a setting, default 1000 m. |
| IADS rebuild economy (his #97) | Comms/power/command buildings generate no income, so they have no repair price and stay rubble for the rest of the campaign. He priced them flat: 15M power, 10M command centre, 5M comms tower. Turns striking the network into an attrition loop. Sits beside §52. |
| ATMOS-X live METAR weather (his #927) | We took the cloud-preset-pack half as #773. The METAR half replaces generated weather with a real observation, with a switch for whether it brings its date along. Fits §47. |
| Weapon `range:` drives the stand-off ingress point | A package carrying a weapon whose range exceeds the doctrine ingress distance starts its run at that range instead of being dragged in. We have no equivalent. |

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
