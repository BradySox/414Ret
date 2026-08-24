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

Pick saves that are **not** fork-authored campaigns where possible. Our own campaigns are
tuned to fork features and are not representative; the phase-0 note uses a Starfire
campaign for exactly this reason.

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
| 1 | **CAS behind its SEAD window** | ✅ Built — #973. Flown pass owed. |
| 2 | **A TOT past the end of the mission window** | 🔵 **Next.** Expressibility established (step 2 above): the window bounds the spread offset, not the TOT. **Not yet measured** — count red packages whose final TOT exceeds `desired_player_mission_duration`, across several saves and several re-plans. Pre-register the threshold first. If it is near zero the row dies and that is a good outcome. |
| 3 | **Concentration of force on 1–3 objectives** | ⚪ Unstarted, and the biggest. His diagnosis is that `PlanNextAction.each_valid_method` walks a fixed priority list with no operational shape. Ours is the same walker. Note §93 region priorities is the *blue-side, human-set* analogue already built — read it before designing anything, because a red-side version that is a weight rather than a fence is the same shape. |
| 4 | **Route helos over land, never open water** | ⚪ Unstarted. Nap-of-earth masks a helo in ground clutter; over sea it is engaged like any other contact. Flight-plan/navmesh territory. Check what §90's terrain weighting and the navmesh already do first. |
| 5 | **Stagger from each package's floor, not from zero** | ⚪ Unstarted, and possibly category A. §69 already uses `TotEstimator(package).earliest_tot(now)` as its clamp, so we may honour this on the coordinated path and not elsewhere. Read before measuring. |

Add a row per doctrine line assessed, including the ones that die. **A category-A finding
is worth recording precisely because it stops the next pass re-checking it.**

## What this is not allowed to become

- A reason to adopt `game/agent/`. His own timing is "it'll be a while."
- A reason to reopen seam 7 without a measurement that meets the phase-0 bar.
- A settings page. These are planner corrections, not knobs.
- A justification for shipping doctrine we have not tested because a good commander said
  it. He is playing his fork, not ours; several of these will not survive step 2.
