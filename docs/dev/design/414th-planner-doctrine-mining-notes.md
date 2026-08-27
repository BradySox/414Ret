# Planner doctrine mining — turning a strong commander's playbook into planner code

**A working procedure for a local agent, run against a real install.** Started 2026-08-24.

## The direction, and the thing it is not

> "Long term I don't want the LLM planning red, I wanna use the LLM to teach the
> model/Retribution to plan better." — DM, 2026-08-24

**No LLM runs in this fork, ever, under this programme.** Not in the planner, not behind a
setting, not opt-in. The LLM already did its job on someone else's machine: it played six
campaigns as red and produced a written account of what a competent commander has to do to
play this engine well. That account is the input. Everything after it is ordinary Python
in our own scripted planner, verified our own way.

Nothing here depends on juanjux's fork beyond **reading one markdown file**. No API, no
`game/agent/`, no service layer, no network call at runtime.

## The input

`ai-docs/howtoplay.md` in `juanjux/dcs-retribution` — 218 lines, accumulated campaign by
campaign, including a section called *"the ten things that cost the most aircraft when
forgotten."* Fetch it read-only:

```
curl -sSO https://raw.githubusercontent.com/juanjux/dcs-retribution/master/ai-docs/howtoplay.md
```

Background on where it came from and why it exists:
[414th-juanjux-fork-watch-notes.md](414th-juanjux-fork-watch-notes.md).

**Licence.** Read it, reason from it, reimplement against our own tree. Do not vendor the
file, and do not copy its prose into our docs beyond short quotation. Our own rule applies:
his name and handle stay out of this repo's code, commits and PR metadata.

## The loop

Per doctrine line, in order. Most lines die at step 2, and that is the point — the cost of
this method is reading, not building.

### 1. Classify

Every line is exactly one of four things:

| | Kind | What to do |
|---|---|---|
| **A** | A rule our planner already honours | Nothing. Record it as checked so nobody re-checks. |
| **B** | An engine defect, or state a consumer cannot read | A bug fix in its own right; usually small. |
| **C** | **Something a competent commander does that our planner cannot express** | The prize. Continue to step 2. |
| **D** | Genuine judgement | Leave it with the human. Never a setting default. |

### 2. Establish expressibility, in the code, before believing anything

**This is the step that does the work, and it is where the naive reading is usually
wrong in both directions.** Do not accept "our planner doesn't do that" from a grep, and
do not accept "we already handle it" from finding the setting referenced somewhere. Read
the call path end to end and write down the composition.

Worked example, and the reason this step exists — *"aim every TOT inside the mission
window"*:

- First read: "nothing in our tree does this for red." **Wrong** — `MissionScheduler` is
  constructed with `desired_player_mission_duration` (`game/coalition.py`).
- Second read: "so it is already handled." **Also wrong** — `start_time_generator` bounds
  the random *spread offset* by that duration, and then
  `package.time_over_target = next(start_time) + tot`, where `tot` is
  `TotEstimator(package).earliest_tot(now)`.
- Actual state: **the window bounds the offset, not the TOT.** A long-transit package can
  be placed past the end of the mission, and nothing clamps it.

That third reading is a measurable claim. The first two were not.

### 3. Measure it against a real save, headless

A category-C candidate is not a defect until it is counted. No DCS process is needed —
only the install's `Saved Games` folder and a campaign save.

The instrument to copy is `tools/measure_red_planner_headroom.py`. Its harness is four
lines and every new measurement reuses it:

```python
persistency.setup(saved_games, True, 16880)      # ~/Saved Games/DCS
game = persistency.load_game(save)
game.initialize_turn(GameUpdateEvents(), for_red=True, for_blue=False)
state = TheaterState.from_game(game, Player.RED, now, tracer)   # candidate targets
```

`initialize_turn(for_red=True, for_blue=False)` re-plans red only, so the same save can be
re-planned several times to see whether red's choice is stable or noisy.

```
python tools/measure_red_planner_headroom.py <save.retribution> [--turns 4]
```

Write a sibling tool per candidate rather than growing that one. Name the count in the
docstring so the number is reproducible, and **pre-register the threshold that would make
it a defect before running it** — the three prior Phase 0s are the reason this rule exists.

`tools/measure_tot_past_mission_window.py` (row 2) is the second one, and the shape to copy
for a scheduling candidate: it takes several saves and pools them into one verdict, prints a
per-save subtotal so an outlier is visible rather than averaged away, and carries its
thresholds in its own docstring. It also **splits the population by whether a fix could
reach it** — 60 packages were late, but only the ones whose transit alone would have fitted
are the defect; the rest are a different question. Deciding that split before running is
most of the work.

**Separate the two coalitions in the output even when the doctrine line is about red.** Row
2's defect turned out to hit blue harder than red, which is what established it as a
shared-path correction rather than something red was being handed.

**Name the bias that would push the reading toward a defect, and check whether the
verdict survives it.** `tools/measure_offensive_concentration.py` (row 3) over-counts the
candidate pool, because some tasks pick from a narrower slice than `TheaterState` holds.
That inflates "it spreads". The row died anyway, so the bias could not have manufactured
the result — which is the only reason the number was quotable. A DEFECT verdict under a
known bias in the same direction is not a finding.

**⚠️ MEASURE A FRESH CAMPAIGN, NOT A SAVE. This is the mistake that voided every number this procedure produced.** The step-3 recipe above loads a `.retribution` save out of Saved Games. **Those saves are hand-edited.** `initialize_turn` re-plans the ATO, so the packages ARE machine-generated — which is exactly why the mistake survived so long — but every input to that planning is curated: air-wing composition, squadron basing, aircraft counts, control-point ownership, front lines, settings, the SAM laydown. Any claim whose answer depends on how much of what is where was measuring the DM, not the planner. Three rows were reported with confident percentages and all three moved or reversed when re-run on fresh campaigns; the numbers have been withdrawn rather than restated. Use `tools/_campaign_game.py`, and prefer campaigns the fork did not author (the campaign list carries `authors:`). A save is worth measuring when the question is *about that save* — a flown result, a reported defect. It is never evidence for how the planner behaves.

**Migrate the save before measuring it**, on the rare occasion a save is the right subject. `persistency.load_game` runs no migration; only the app's load path constructs `Migrator`. Without it you are measuring a state no player ever loads.

**Before calling a dead code path a defect, find out whether its JOB is already being done under another name.** This is step 2's second half and skipping it is what killed [#978](https://github.com/BradySox/414Ret/pull/978). RECOVERY really was unreachable — correctly diagnosed — but the carrier already had a tanker on station through the ordinary REFUELING tasking, so there was no gap to close. **"The planner does not do X" and "the planner does not achieve X" are different claims**, and only the second is a defect. A dead path is where the "we already handle it" check is easiest to skip, because there is nothing named X to grep for. Search for the outcome.

**Inspect the individual case before believing any share.** Every over-water helo route row 4 flagged turned out, on inspection, to be a package forming over the sea because its assault element launched off a carrier — correct behaviour. One opened case falsified a whole aggregate. Open one before quoting a percentage, and open one before quoting a zero.

**A gate can be unsatisfiable rather than merely strict.** Row 3's inclusion gate was
first written as "candidate objectives >= 2 x packages" and could never fire: objective
count is bounded by the map, package count is not. Every turn scored as "no room" and it
had to be rewritten after the data was visible, which costs the pre-registration most of
its value. Sanity-check a gate against the ranges the quantities actually take before
running.

Pick saves that are **not** fork-authored campaigns where possible. Our own campaigns are
tuned to fork features and are not representative; the phase-0 note uses a Starfire
campaign for exactly this reason.

**Turn-passing can die in code unrelated to the measurement.** `game.pass_turn(no_action=True)`
raised `IndexError` in the ambient-convoy layer on one of the five saves. Catch per turn and
take the turns the save did give rather than losing the whole sample — and file the crash,
because a save that cannot pass a turn headless cannot pass one in the app either.

### 4. Build it as ordinary planner code

Smallest change that expresses the doctrine. Gate it only if it changes existing
behaviour for everyone; a correctness fix takes no setting.

**Red and blue share a planner, and that is a fairness property.** From the long-view
note: a change only red gets has to be a change blue does not *need*, not a change blue is
*denied*. Most of these are shared-path fixes and are fine. If a candidate would make red
better at blue's expense, stop and raise it.

### 5. Verify our way, not by looking at it

- Tests that **fail on the unpatched tree** and pass on the patched one. A test that
  passes either way proves nothing — write it if it pins an exclusion, but never count it
  as the evidence.
- Black, mypy, and the suite. Note the suite is **Windows-only by construction**
  (`game/weather/atmosxliveweather.py` imports `winreg` unguarded; CI runs
  `windows-latest`), which is free on this install and awkward anywhere else.
- A checklist row if it has runtime behaviour CI cannot exercise, per
  [414th-ingame-pass-checklist.md](../414th-ingame-pass-checklist.md). Planner timing
  changes do — "the packages arrived in a sensible order" is a flying observation.
- One PR per candidate.

## Guardrails — read before proposing anything

**Seam 7 is DROPPED and this does not lift it.** Three framings, three Phase 0s, no
observable defect found. Read
[414th-red-brain-phase0-notes.md](414th-red-brain-phase0-notes.md) first. A list of things
a good commander does is **not** evidence our planner measurably loses for want of them.
What this method changes is the cost of getting a candidate, not the standard of proof.

**§55 tried the obvious shape and it was removed.** Adaptive red posture, 2026-07-21. Do
not re-derive it.

**Do not trust "reads wrong in the air" without the measurement.** Framing 3's Phase 0
went looking for red pushing into unsuppressed SAM belts and found **0 of 48 packages**
doing it. The thing that looked obviously broken was fine.

**One known-bad metric.** Candidate targets offered vs. targets fragged cannot separate
"chose not to" from "could not afford to". It is in the existing tool; do not quote it as
if it measures choice.

## Worked example — what a finished one looks like

**CAS pushes behind its SEAD window** — [414Ret#973](https://github.com/BradySox/414Ret/pull/973).
**Superseded 2026-08-27: §69 was removed**, so this worked example describes a feature that
no longer exists. It is kept because the *method* it demonstrates is still the method.

1. **Classify:** the front-line sandwich — CAS descends into MANPADS, climbs into the area
   SAM ring, no safe altitude. Category C.
2. **Expressibility:** §69's `COORDINATED_STRIKE_TYPES` was
   `{STRIKE, BAI, OCA_RUNWAY, OCA_AIRCRAFT}`; nothing else in `game/commander/` times CAS
   behind a suppressor. Two checks before believing it: CAS is **not** `auto_asap` (only
   the first AEWC package is), so the pass reaches it and the change is not inert; and
   `FrontLine` carries a plain `.position`, so the ring test needs no change.
3. **Measure:** skipped — this one is a set-membership omission whose docstring names its
   deliberate exclusions and does not name CAS. When the code says what it meant to
   exclude, that *is* the evidence.
4. **Build:** one enum member.
5. **Verify:** four tests, the two behavioural ones red/green confirmed. Flown pass owed.

Total: one line of behaviour change, and the reading around it is 90% of the work. That
ratio is normal here and is not a sign the method is failing.

## The queue

Verification state is what matters; do not re-do a row that is already resolved.

| # | Doctrine point | State |
|---|---|---|
| 1 | **CAS behind its SEAD window** | ⚪ Built then REMOVED with §69, 2026-08-27 — #973. A set-membership omission: `COORDINATED_STRIKE_TYPES` named its deliberate exclusions in its own docstring and CAS was not among them. No measurement was needed or taken. Flown pass owed. |
| 2 | **A TOT past the end of the mission window** | ✅ Built — [#975](https://github.com/BradySox/414Ret/pull/975), **on a justification that did not hold up.** The code defect is real and readable: the spread bounded the random offset by the cycle and then added transit on top, so nothing bounded the arrival. The share of packages it actually affected was first measured on hand-edited saves and was badly overstated; on fresh campaigns it is small. The fix stays because it is structurally right and is an identity for a zero-transit package, not because of a number. |
| 3 | **Concentration of force on 1–3 objectives** | ⚪ **Looked at, not pursued.** No evidence the planner spreads its effort thinly. The measurements taken were against hand-edited saves and are withdrawn rather than restated. What is worth keeping is the code reading below: concentration is expressed in three narrow places and the Alpha Strike fan sits at 1 outside Vietnam. |
| 4 | **Route helos over land, never open water** | ⚪ **Looked at, not pursued.** Nothing routes by terrain — `navmesh.py` and `packagewaypoints.py` both contain zero references to land, sea or water, and `ThreatZones` is range circles with no terrain or line of sight, so the masking the doctrine line buys is invisible to the planner. Every over-water helo route inspected turned out to be correct behaviour (a package forming over the sea because its assault element launches off a carrier). No count is quoted; the ones taken were unsound. |
| 5 | **Stagger from each package's floor, not from zero** | ✅ **Category A — we already do this. Do not re-check.** Read directly off `schedule_missions`: eight of its nine TOT assignments floor on the package's own `earliest_tot`. Only the RECOVERY branch does not — row 6. |
| 6 | **Recovery tankers are the one branch with no floor** | ⚪ **Looked at, not pursued.** Two readable facts: no campaign yaml lists `Recovery` as a squadron task, so the RECOVERY tasking is never offered and its whole path is unreachable; and the RECOVERY branch assigns a carrier ETA with no `max(earliest_tot, ...)`. Neither is worth acting on. The carrier already gets a tanker on station through the ordinary REFUELING tasking, so there is no capability gap, and [#978](https://github.com/BradySox/414Ret/pull/978) — which tried to enable it — was closed for committing the whole tanker squadron to a station further from the boat than the one already there. |
| 7 | **Why the recovery station lands 40 NM out** | ⚪ Recorded, unbuilt. `RecoveryTankerFlightPlan`'s builder sets `time_to_landing` to the whole `desired_tanker_on_station_time` and projects the carrier along the reciprocal wind at 20 kt, so the station is placed where the boat will be when the tanker goes **home**, not where it is during recoveries. Arithmetic, not a measurement. Anyone reopening recovery tanking fixes this first. |

Add a row per doctrine line assessed, including the ones that die. **A category-A finding
is worth recording precisely because it stops the next pass re-checking it.**

## What this is not allowed to become

- A reason to adopt `game/agent/`. His own timing is "it'll be a while."
- A reason to reopen seam 7 without a measurement that meets the phase-0 bar.
- A settings page. These are planner corrections, not knobs.
- A justification for shipping doctrine we have not tested because a good commander said
  it. He is playing his fork, not ours; several of these will not survive step 2.

## Row 3's composition — where concentration lives in our planner

Row 3 is dead, but the reading behind it is the expensive part and is recorded so the
next pass does not repeat it. Path read end to end 2026-08-24: `theatercommander.py` →
`PlanNextAction.each_valid_method` → each compound task → `PackagePlanningTask` →
`objectivefinder`.

**Concentration is expressed in three places, all narrow:**

| Mechanism | What it does | How far it reaches |
|---|---|---|
| `Doctrine.strike_flight_count` — the Alpha Strike fan | `PlanStrike.propose_flights` puts N coordinated STRIKE sections on one target sharing a TOT. The first is required, the rest optional, so they mass as deep as the squadron allows and drop silently when it runs dry. | **1 on every doctrine except `VIETNAM_DOCTRINE`, which is 4.** Real concentration of force, built, and set to 1 almost everywhere. |
| `AttackBattlePositions` | Iterates `state.control_point_priority_queue[:2]` — the top two capturable control points and nothing else. | That task only. |
| `DegradeIads`, opportunistic tier | Sorts by `priority_cp.distance_to(x) - x.max_threat_range()`. | That tier only. `priority_cp` is read in **exactly one place in the whole tree**. |

**It is not expressed anywhere else:**

- `AttackBuildings`, `AttackMotorpools`, `AttackAirInfrastructure`, `AttackShips` and
  `InterdictReinforcements` each consume a globally range-sorted candidate list.
- That sort key is `min(distance to ANY friendly control point)` — `_targets_by_range`
  and the `strike_targets` iterator. Global proximity with no notion of grouping: two
  targets 200 km apart sort adjacent when each is 50 km from a different friendly base,
  so the near-list is a band along the whole front rather than a cluster.
- A tasked TGO leaves the planning state (`PlanStrike.apply_effects` →
  `strike_targets.remove`; `PlanDead` → `eliminate_air_defense`), so several packages on
  one TGO is impossible by construction. Massing on one *objective* means planning
  several of its TGOs, and nothing steers toward that.
- `each_valid_method` walks a fixed method order. Only §67 weather demotion reorders it
  and only the §52 C2 throttle trims it; neither weights by place.

**The naive reading is wrong in both directions**, which is the whole point of step 2.
"No operational shape" is false — two tasks already concentrate and the Alpha Strike fan
is real massing sitting at 1. "We already handle it" is also false — the five remaining
offensive tasks pick globally by proximity with nothing weighting them by place.

**Where a weight would attach, if this is ever re-opened on new evidence.** `priority_cp`
is already computed every turn and almost unused, and §93's `planning_factor` is exactly
the right shape — a multiplicative factor on the range sort, with call sites already cut
into both sort sites. A derived, both-sides analogue goes there, not into a new
subsystem. No measurement is offered here for or against: the ones
taken were unsound and have been withdrawn.

**What row 3 did NOT ask.** It asked *how many* objectives the effort lands on, not
*which*. If the real complaint is that the objectives chosen are the wrong ones, that is
a different row with a different measurement, and this verdict says nothing about it.

---

## Suppression-first ordering — MEASURED AND REJECTED (2026-08-27)

**The ask.** Make the auto-planner work in the order SEAD → DEAD → SEAD Sweep → BAI →
Armed Recon → OCA → Strike → Air Assault, i.e. plan suppression first instead of last.

**Two facts kill the literal form.** SEAD and SEAD Sweep are not objectives — there is no
`PlanSead` primitive. `DegradeIads` plans `PlanDead`; SEAD and SEAD Sweep are proposed as
`EscortType.Sead` inside other packages (`dead.py`, `antiship.py`, `cas.py`,
`propose_common_escorts`). You cannot plan SEAD before DEAD; the SEAD flight exists only
because a DEAD package asked for it.

**`DegradeIads` is last on purpose, and it is load-bearing.**
`TheaterState.threatening_air_defenses` is built empty and is populated by
`target_area_preconditions_met`, which every offensive task calls as it evaluates a target.
Planning suppression last means its reactive tier services the SAMs the other tasks just
declared. Hoist it and that list is empty, so only the opportunistic tiers run.

**Measured** — three real saves, BLUE re-planned via `initialize_turn`, same RNG seed.
"Offensive" counts Strike/BAI/OCA/Armed Recon/Air Assault packages.

| Save | Order | DEAD | Offensive |
|---|---|---|---|
| Syrian Shield t12 | stock | 5 | **7** |
| | suppression first | 9 | **2** |
| Vietnam 3 | stock | 4 | **4** |
| | suppression first | 6 | **2** |
| Persian Gulf t6 | stock | 0 | **5** |
| | suppression first | 2 | **2** |

Suppression roughly doubles and the strike package collapses. It is zero-sum: the HTN plans
until airframes run out, so order **is** priority for a fixed pool. Two side results — the
full 8-step sequence is indistinguishable from moving `DegradeIads` alone (every other
position is inert), and the hoisted DEAD targets are a strict *superset* of stock's, so the
cost is over-spending rather than mis-aiming.

**A reserved floor was built and reverted the same day.** Holding airframes back from
non-suppression tasking (`sead_aircraft_reserve`, gated in `can_auto_assign_mission`) does
not redirect them — it strands them. Syrian Shield went to DEAD 4 / offensive 5 at
`floor=2`, worse than stock on **both** axes, with total packages falling 22 → 19 → 15.
Narrowing the reserve to fixed-wing DEAD-capable squadrons made Persian Gulf worse again
(DEAD 0, offensive 4). Denying a strike an airframe does not make that airframe fly DEAD,
because fulfilment also fails on range, base and package composition.

**The real constraint is capacity, not priority.** Instrumented on the Persian Gulf save
under stock order: `DegradeIads` offered **62** DEAD taskings against **22** correctly
declared threats, and **all 61** fulfilment attempts failed for lack of aircraft — the
Weasel squadron (77th FS F-16CM) is at zero available by the time suppression runs. You
cannot re-slice a pie that is already fully eaten.

**Do not re-run either experiment.** If suppression coverage is the goal, the levers are
procurement (more DEAD-capable airframes) or fewer offensive objectives per turn — not
ordering and not reservation. A future attempt needs a *new* mechanism, not a new order.
