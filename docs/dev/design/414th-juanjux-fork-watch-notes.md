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

### How he actually uses it — an engine QA harness (CORRECTED 2026-08-24, twice)

**The design docs above describe a product. His use of it is a defect-finding instrument
pointed at Retribution itself, and that is what matters to us.** This took two
corrections to get right: the first read here treated `game/agent/` as a feature to
evaluate for adoption; the second, on the DM's steer, called it a testbed for red
doctrine. The doctrine half is real (below) but it is the smaller half.

**In his own words, relayed 2026-08-24:**

> They find problems and papercuts when using the API to play opfor, then I fix it and
> repeat. I have used it on six campaigns already but still they find more bugs or things
> to improve, so it'll be a while until I try to merge it upstream.

An agent that must actually plan and execute a whole red turn through the API is a
tireless, literal-minded user that exercises paths no human clicks. Six campaigns of that
has produced a continuous stream of engine fixes.

**It is stated outright in his commit messages.** On `e06b25c`, which added
`rebuild: {force_group, turns_remaining}` because a site under construction was
indistinguishable from a wrecked one:

> Reported from a live campaign by the LLM planning red: two of its own sites had
> vanished from every read while the human could see them being rebuilt.

**The defect class is the seam between game state and any consumer that is not a human
looking at the map.** A player never hits that one — they can *see* the works. Our own
verification is a person flying missions against a checklist, so it cannot reach this
layer either. We have no equivalent instrument.

**This loop already feeds us and we did not know it.** The faction-editor trio adopted
here on 2026-08-23 (his #953, checklist **B94** — the faction edit that never reached the
buy menus, the tick boxes that removed nothing, the lists sorted by internal id) came out
of exactly this. So did the convoy-counter and hold-release fixes. Expect the stream to
continue for as long as he runs campaigns, and read his `[FIX]` commits after each one.

**Checked here, and NOT applicable — do not re-check:** the `rebuild` defect itself
cannot occur in our tree, because we have no multi-turn construction. §68's SAM repair is
the instant pay-full-price flip-alive the player's own repair button does, and
`theatergroundobject.py` / `theatergroup.py` carry no construction countdown at all. If a
multi-turn rebuild is ever added here, this is the hole to design against: represent
"under construction" distinctly from "dead" *in the read model*, not only on the map.

### The doctrine half

The other output of the same loop. Findings that are not engine bugs get written into the
LLM's playbook instead, and his commit pattern shows both kinds landing together:

```
howtoplay: fold in the campaign-4 lessons
howtoplay: what turn 0 is free in is time, not money
howtoplay: stagger a BARCAP racetrack by reversing START/END
prev_turns: what died, what killed it, and which killed which
OPFOR-AI: each flight reports when it starts engines
OPFOR-AI: per-flight TOT offsets, readable and settable
```

That is one loop, run per campaign: **play → watch a strong general handle red → find
something it wanted to do that the engine could not express or the model could not see →
either expose the data/control, or write the lesson down.** The `OPFOR-AI:` commits widen
what red can observe and act on; the `howtoplay:` commits are the findings.

### `ai-docs/howtoplay.md` is the artifact, and it needs none of his code

218 lines, and most of it is **not API mechanics — it is an empirically derived doctrine
for red**, accumulated campaign by campaign. It carries a section called *"the ten things
that cost the most aircraft when forgotten."* A sample, all engine-agnostic and all true
of our tree:

- **Concentration of force.** "Pick 1–3 objectives and concentrate on them. **Do not** plan
  a little bit of everything everywhere." Our HTN plans a little bit of everything
  everywhere — that is his own diagnosis of it, quoted above.
- **A TOT has a floor, and the launch base decides the order.** Plans build backward from
  the TOT, so a SEAD lifting from 180 nm never precedes a strike from 40 nm whatever TOT
  you set; asking for an impossible-early time floors it and can drop a push trigger into
  the past so the flight never launches. Stagger from each package's *floor*, not from
  zero.
- **Time the strikes into the player's actual mission window.** Aim every TOT inside
  `desired_player_mission_duration` — a TOT after it is wasted, because the mission is over
  before it happens. Concentrate in time, not only in space. **Nothing in our tree does
  this for red**; §69 and §89 are the blue-side and pre-roll analogues.
- **DEAD before CAS, for the same reason as DEAD before strike** — the front-line
  sandwich: CAS descends to acquire and eats MANPADS, climbs to escape and enters the area
  SAM ring, with no safe altitude between.
- **Route helos over land, never open water** — nap-of-earth masks a helo in ground
  clutter; over sea it is engaged like any other contact.

### How the loop actually runs — and what it is NOT

**It is live, whole-campaign, and there is no A/B against the scripted planner.** Worth
stating because the obvious guess — generate a campaign, save turn 0, hand it to an agent,
compare the plan to stock — is wrong on every clause:

- **Live over HTTP, never a save.** A headless save-file mode was in early drafts and is
  explicitly **out**: the Qt app already runs FastAPI in-process against the live `Game`,
  and the agent talks to that.
- **The whole campaign, not one turn.** The human says "your turn" in chat, the agent
  plans red, and **Take Off is blocked until it finishes**. Six campaigns end to end.
- **Stock red never runs alongside it.** When the AI is on, the engine does not auto-plan
  red at all — the scripted `TheaterCommander` is a *fallback* for when the agent is
  absent, errors or times out. There is a dev-only "review-only" mode that generates a
  plan and applies nothing, and he calls it a test aid, not a product mode.

**So no measured delta between LLM-red and HTN-red exists anywhere.** An earlier revision
of this note said the delta "is the headroom" and that `howtoplay.md` is "the transcript
of that delta." That was wrong — nobody has run the comparison, him included.

### What `howtoplay.md` actually is: a requirements list

It is the set of things a strong general had to be **told** in order to play this engine
well. Each line is one of four things, and only the third is worth our time:

1. an engine rule the scripted planner already honours — no action;
2. an engine defect or missing read/control — his papercuts, which he fixes and we harvest;
3. **something a competent commander does that our planner cannot express** — a planner gap;
4. genuine judgement that should stay with a human.

That is not evidence of headroom and it does not lift the seam-7 tombstone. It is a much
cheaper source of **candidates** than another analytic sweep, because each candidate is
already stated as a concrete behaviour rather than an aggregate that comes back flat.

### The standing direction here (DM, 2026-08-24)

> "Long term I don't want the LLM planning red, I wanna use the LLM to teach the
> model/Retribution to plan better."

So the programme is **category 3, mined offline**: read the playbook, find what our planner
cannot express, and build those as ordinary Python in the scripted planner. No LLM at
runtime, no API, no adoption of `game/agent/`, no dependency on his fork beyond reading a
markdown file. The LLM is the instrument that found the requirement; it is not part of the
product.

**First confirmed gap, found this way, 2026-08-24.** His doctrine says the front-line
sandwich makes CAS need suppression exactly as a strike does — CAS descends to acquire and
eats MANPADS, climbs to escape and enters the area-SAM ring, with no safe altitude between.
Our §69 `COORDINATED_STRIKE_TYPES` is `{STRIKE, BAI, OCA_RUNWAY, OCA_AIRCRAFT}` — **`CAS` is
absent**, and nothing else in `game/commander/` times CAS behind a suppressor. The
docstring names Armed Recon and Air Assault as deliberate exclusions and does not mention
CAS, so this reads as an oversight rather than a decision. Not yet fixed; needs the
same check §69 got (does the CAS target sit inside a ring a SEAD/DEAD package is servicing)
and a flown pass before it counts.

**What this does NOT license.** It is not evidence that adopting `game/agent/` is right,
and it does not lift the seam-7 tombstone: reading a list of things a good commander does
is not the same as showing our HTN measurably loses for want of them. Any move here still
starts at [414th-red-brain-phase0-notes.md](414th-red-brain-phase0-notes.md) and the §55
removal record. What changed is that a fourth Phase 0 now has a **cheap, concrete
pre-registered card** available to it — take two or three of the doctrine points above,
check whether our planner can express them at all, and measure one.

**His own adoption timing, and it is firmer than it first looked.** The opening quote was
"better to wait a little until is more polished or even merged upstream"; the fuller
version is six campaigns in and the agents are *still* finding bugs, so "it'll be a while
until I try to merge it upstream." Treat that as the schedule. He is also benchmarking
Grok against Claude and means to try Codex, so the design is model-agnostic in practice
rather than tuned to one provider.

Read the docs and harvest the fixes; do not evaluate the code for adoption yet.

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

**Smart threat reaction** (his [#63](https://github.com/juanjux/dcs-retribution/pull/63)),
taken 2026-08-24 as §94. DCS' stock Evade Fire breaks every aircraft that *perceives* a
launch, so one naval or S-300 salvo scatters dozens of jets the missile was never aimed at.
The plugin parks every airplane at Passive Defense and flips only the group
`weapon:getTarget()` names. Design + adoption record:
[`414th-ai-threat-reaction-notes.md`](414th-ai-threat-reaction-notes.md); checklist **B97**.

**Two things about this one that generalise.** First, **the merged PR was the wrong file to
take**: he rewrote it a week later (2026-07-15) because the merged version ran a `setOption`
over every airplane every 5 s and *"was stalling the sim"* during an anti-ship salvo. Check
the file's commit history before porting from a diff — his `[FIX]` PRs land clean, but a
prototype he merged into his own fork may have been superseded in place. Second, this is the
first adoption that is **a doctrine change rather than a defect fix**, so it carries a
pre-registered falsifier instead of a verification: if AI attrition against SAM belts rises
enough to change how a campaign plays, narrow the baseline or turn the plugin off.

**Checked while porting, and worth not re-checking:** `redscramble` is the only plugin in our
tree that sets a reaction-on-threat option at runtime, so it is the only one needing the new
`dcsRetribution.aiReactionExempt` claim. MOOSE's `AI_A2A_DISPATCHER` does not set ROT; only
its `ESCORT` class does, and we do not use it.


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

The handoff written **for his agent** is
[`AGENT-HANDOFF.md`](../../upstreaming/juanjux/AGENT-HANDOFF.md) — the spec form, since he
works his fork through agents. The patches are the fast path inside it, not the deliverable.

These are for his fork and his testing; what he sends upstream is his call.

### Zero-port test asks

He already ships three of our features that we cannot close a row on. These cost no
porting at all — only his hardware:

| Row | Feature | What is owed |
|---|---|---|
| B39 ◐ | §81 naval magazines | Re-fly with release window back at 120/900 (ours ran with leftover 3600/3600 diagnostics, so no magazine was ever exercised). Pass = AShM launches spread across the mission, a `WINCHESTER` line, the debrief debit matching the track, turn 2 opening with reduced stock. |
| B45 ☐ | §86 GPS jamming | A JDAM strike inside 15 nm of a jammer, with a GBU-12 on the same pass as the control. Pass = the JDAM flies its normal profile and lands ~200 m off, the laser weapon hits, and killing the jammer restores the next JDAM in the same mission. |
| B32 ☐ | §78 coastal batteries | He has the coastal half only (`coastal_batteries_engage_ships`), not the convoy half. Pass = a land-based anti-ship site engages a hull passing in range on its own. |

**B45 is already part-answered, unasked** (2026-08-24, his own words): *"The GPS Jamming
works pretty well, now it's a lot harder to destroy those SA-22 or Patriots… I will give
you feedback once I have finished this campaign."* That is his port, not our build, and it
is a play impression rather than the instrumented pass B45 asks for — so the row does not
move on it. What it does establish is that the feature reads as intended in someone else's
campaign, and that fuller feedback is coming. Chase it when his campaign ends.

### His SLAM-ER exemption — a defect in OURS, found by using it (2026-08-24)

His commit `4b4d2a1` removes `AGM-84H` / `AGM-84K` / `SLAM` from the jammed weapon set.
Our §86 still jams all three. His reasoning has two halves and the second is the one we
missed:

1. **Physics.** The SLAM-ER's GPS/INS leg is only the midcourse. The imaging seeker can
   be brought up far outside a jammer's reach — bubbles are ~15 nm — so by the time the
   weapon is over denied ground it is already looking at the target and no longer
   navigating by satellite.
2. **The counter.** Jamming it "left no sane way to service a jammer with a stand-off
   weapon at all."

Our stated counters are laser/TV delivery and killing the jammer, both of which mean
flying into the bubble. **A feature should not remove its own counter**, and §86 does. His
play report is the evidence it matters: he unlocked SLAM/SLAM-ER specifically as the
answer to jamming bubbles, which is the shape the feature should have had.

**Candidate for us, not yet taken:** drop the three ids from `AFFECTED_WEAPONS` in
`game/fourteenth/gps_jamming.py`, update the setting text and the §86 note. Cheap. The
open question is whether GBU-54 (Laser JDAM, GPS/INS baseline) belongs in the same
exemption — it does not, on the same reasoning, because its GPS mode *is* the terminal
solution unless the crew lases.

### His OPFOR-AI status, in his words (2026-08-24)

*"the LLM control is awesome. (I am finding Grok works better than Claude as OPFOR
general, need to test Codex too next campaign)… better to wait a little until is more
polished or even merged upstream."*

What that quote is evidence *of* is worked through above under
[How he actually uses it](#how-he-actually-uses-it--a-testbed-not-just-an-opponent-corrected-2026-08-24)
— it is a testbed, and `ai-docs/howtoplay.md` is the artifact worth reading. Do not
evaluate `game/agent/` for adoption yet; do read its docs.

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
