# The red brain — seam 7, framing 3 · Phase 0 · 2026-08-19

Seam 7 ("the enemy") was **DROPPED 2026-08-17** in
[414th-retribution-long-view.md](414th-retribution-long-view.md) §8, after two framings died on
two Phase 0 measurements and one shared cause. That note fixes the terms for anything that comes
after:

> **What would reopen this.** Not another dimension picked off the planner. A flown observation of
> something red actually does that reads wrong in the air.

And, on the remaining dimensions:

> None of those is scoped here, and none should be started without its own Phase 0.

A third framing has since arrived from outside the fork. This note is its Phase 0.

## Framing 3, and why it is not framing 1 or 2 again

juanjux's fork ships `game/agent/` — an LLM in the commander's seat for red, reached over REST,
MCP or a copy-paste blob, with the HTN kept as fallback. Design principle: *replace the brain,
reuse the hands.* Full writeup in
[414th-juanjux-fork-watch-notes.md](414th-juanjux-fork-watch-notes.md).

It is genuinely a different proposition:

| | What it changes |
|---|---|
| Framing 1 — red commits to an axis | one dimension of the HTN's output |
| Framing 2 — red defends where the player flies | one dimension of the HTN's output |
| **Framing 3 — an LLM plans red's turn** | **the decision-maker itself** |

So the §8 verdict does not automatically carry. Framings 1 and 2 died because *those two
dimensions* were empty; framing 3 claims the whole plan is worse than it could be.

## Two constraints it has to clear before any measurement matters

Both are already written down, and neither is fatal, but both must be answered rather than
stepped around.

**1. The third-party dependency rule.** The long-view note, §10: *"Not an argument for any
third-party dependency. Nothing here needs software outside DCS. Our rule against mod
dependencies for core behaviour applies the same way to analysis tools."* An external LLM is
squarely that. The answer available is that it would be opt-in and the HTN stays the default —
which is exactly how juanjux built it — so core behaviour never depends on it. That is a real
answer, but it caps the feature's reach: it can never be what red *is*, only what red can be
for a host who wires one up.

**2. Red and blue share a planner, and that is a fairness property.** §8's catch: *"A change
that only red gets needs to be a change blue does not need (continuity of intent), not a change
blue is denied (better tactics)."* Framing 3 is squarely better tactics for red.

The counter-argument is decent and should be stated rather than assumed: blue does not *need*
a brain because blue has one — the player. The HTN exists to stand in for a human on the side
that has none, and it is a poor stand-in. On that reading, an LLM commander closes a gap rather
than opening one. This is the strongest thing framing 3 has going for it, and it is an argument
about fairness, not about quality — it still has to show the quality gap is real.

## Phase 0 — is there headroom?

The precondition, stated so it can fail:

> A better brain is only worth building if the current one is leaving value on the table. If
> red's plan is forced by structure, every brain converges on the same plan.

That is the §8 shared cause aimed at framing 3: red's choices and the player's choices are both
functions of the same static map structure, so red *looks* responsive with no memory at all. If
the structure also dictates *what* red does and not just *where*, the seam is empty for any brain.

Three measurements, none of which needs an LLM, a feature, or a flight. Instrument:
`tools/measure_red_planner_headroom.py`.

1. **Choice volume** — candidate targets `TheaterState` offered red, versus distinct targets red
   actually fragged.
2. **Task mix** — red's offensive effort by primary task. §8 flagged "what it goes after" as an
   open dimension, having observed red open against vehicle groups rather than the SAM belt.
3. **Blind push** — red offensive packages whose target sits inside blue's radar-SAM threat, set
   against how much suppression red planned. Pushing strike into a live SAM belt you never tried
   to suppress is a decision that reads wrong in the air.

### What was run

**Caucasus — Vectron's Claw** (`authors: Starfire`, so it meets the standard §8 sets: fork-authored
campaigns are tuned to fork features and are not representative). Two saves — turn 1 and turn 4 —
four headless red-only re-plans each, `initialize_turn(for_red=True, for_blue=False)`.

Blue 6 control points, red 8, one active front line.

### Results

| | turn-1 save | turn-4 save |
|---|---|---|
| Red offensive packages, 4 re-plans | 22 | 26 |
| Distinct targets | 18 | 22 |
| Candidate targets offered per turn | 15 | 15 |
| Suppression packages planned (SEAD/DEAD) | 1 | 3 |
| **Offensive packages targeting anything inside blue's radar-SAM threat** | **0 / 22** | **0 / 26** |

A representative red turn, printed in full from the turn-1 save:

```
AEW&C x2, Refueling x1, BARCAP x8
CAS          -> Front line UNOMIG Sector HQ/Sukhumi-Babushara  [2x Su-25T]
Armed Recon  -> UNOMIG Sector HQ                               [2x Su-25T, 2x MiG-29A]
Air Assault  -> UNOMIG Sector HQ                               [1x IL-76MD, 2x MiG-29A]
Air Assault  -> Psezuapse River FARP                           [2x Mi-8MTV2, 2x Mi-24P]
```

### Verdict — no headroom found. Seam 7 stays dropped.

**1. The blind-push candidate is dead.** Zero of 48 red offensive packages across two saves and
eight re-plans target anything inside blue's radar-SAM threat. Red is not flying into SAM belts
it failed to suppress. It plans about one DEAD when it can afford one, and its targets are not
under SAM cover, so it does not need more. That is internally consistent, not a defect.

**2. The task mix is defensible.** CAS on the front, armed recon behind it, two capture assaults
at contested points, anti-ship against the carrier group, a strike and a DEAD when budget allows.
Asked what is wrong with that turn, this analysis has no answer. The initial read that 8 of 22
offensive packages were Air Assault looked alarming and was wrong on inspection: both assaults
are capture operations at contested points, which is a sensible thing for red to be doing.

**3. The choice-volume metric does not show what it looked like it showed, and this is the
honest limitation of this Phase 0.** Red used 30–37% of the offered targets. That reads like
discarded options; it is not. Red flies 5–8 offensive packages against 15 candidates because
that is what its budget buys, not because it evaluated 15 and rejected 9. **This metric cannot
separate "chose not to" from "could not afford to", and it should not be quoted as if it can.**
A successor would have to bound red's affordable sortie count first and measure choice within
that.

**4. Red's plan is invariant turn to turn.** Turns 1, 2 and 4 of the turn-4 run produced the
identical task mix on the identical target count; turn 3 was a strict subset, having lost the
DEAD and the Strike to budget. The turn loop uses `pass_turn(no_action=True)`, so **nothing
changed between turns and determinism is the expected result** — the same caveat §8 records for
its Baltic Fury numbers. This shows red is deterministic, not that it is stuck.

### What this evidence is, and is not

This is **weaker than the two prior kills, and the difference matters.** Framings 1 and 2 died
because their *premises* were measured false — there is one axis; red already defends where blue
attacks. This run instead **fails to find** a defect it went looking for. Absence of evidence
across two saves of one campaign is not proof there is no headroom.

It was also **exploratory, not pre-registered.** No threshold was fixed in advance, so it cannot
carry the weight a pre-registered test carries. The card below fixes that for anyone who wants to
push framing 3 further.

What it does establish is that **the case for framing 3 does not exist yet.** Three specific
candidates for "the HTN plans badly" were checked and none held up. Building an LLM commander on
the strength of "the HTN walks a fixed priority list" — which is true, and is juanjux's stated
reason — would be building on a structural observation that has now twice failed to produce an
observable defect.

## AMENDMENT 2026-08-19 — the Phase 0 above tested the wrong thing

Written the same day, after reading his actual evidence rather than his design docs. The
measurement stands; the framing around it was too narrow, and this section says how.

### What his evidence turned out to be

Not a design experiment. `game/agent/` has **100 commits over six weeks** (2026-07-02 →
08-12), real campaigns played against it ("first campaign", "Red Sea Rising" round 2), and
five models tried. The LLM is called **GeneraLLM** and is credited in the commit log.

**Its demonstrated output is engine defects, not a better red.** Five of his `[FIX]` PRs
were authored inside the agent work — the commits touch `game/agent/` alongside the engine
change. One of them is the hold-release clamp we ported today (his #100, commit `bb83b720`,
which touches `planner.py`, `schemas.py`, the playbook, `tests/agent/test_tot_floor.py` **and**
`holdpoint.py` in one change). The others: a FOB reported as a cratered runway, the planner
seeing a squadron count instead of the base's contents, `/start` documenting twelve endpoints
that do not exist, and the planner not being able to see what an aircraft costs.

An agent that must command through the player's own API and reports back when the data is
wrong is a **defect-finding instrument**. That is a different product from "a smarter red",
and it is the one with evidence behind it.

### What he does not claim

The claim in the README is "refined across real campaigns played against it" — usage, not
superiority — and there is no changelog entry for it.

> **CORRECTION, 2026-08-22.** This note originally read the README's "not intended for
> upstream" as a confidence signal: *"for someone with 28 merged upstream PRs who carves
> nearly everything, that restraint is a data point."* **That inference was wrong, and he
> said so when asked.** His actual position:
>
> > The plan is to upstream everything, but I go little by little, only extremely tested
> > things and important bug fixes go upstream for now because the guys can feel overwhelmed
> > fast. […] this will probably take a while yet to upstream.
>
> It is a **pacing decision about maintainer bandwidth**, not a judgement on the feature. The
> line is kept here rather than quietly deleted because the failure is instructive: an absence
> — no changelog entry, no PR — was read as evidence, and absences are the easiest thing in
> the world to over-read. Nothing else in this note rests on it.

He also confirmed the usage figure is larger than inferred: **four campaigns played with
Claude, now being tested with Grok** — "and he is finding new issues". Which is the same
defect-finding output, from a second model, still with no claim that red plays better.

He did take the fairness constraint seriously unprompted: commit `a9d5c5be` closed a hole
where the LLM could read blue's entire ATO, on the principle that *"every other asymmetry in
this game is one the human can see and reason about; this one is not."*

### Why the Phase 0 above missed it

It measured **which targets red picks and with what tasks**. His findings are about **how the
package is built and routed** — ingress placement, escort and SEAD waypoint placement, package
composition, formation behaviour under fire. That is downstream of target selection, it is
**shared with blue**, and the instrument never looked at waypoint geometry at all.

So the verdict "no headroom in red's plan" is true as measured and does not answer the
question his work raises. The reframe:

> The gap is not red's brain. It is the planner's output, which a human player silently
> compensates for by dragging waypoints and an HTN cannot.

**That is a better target than seam 7 ever was**, because it is fixable in the engine, it
helps both sides, and it needs no LLM. The first instance is already fixed — the stand-off
ingress bound (features doc §8, checklist B87), verified live in our tree before the fix.

### The inference worth keeping

His playbook grew **42.6 KB → 62.9 KB** in five weeks of play, and it is almost entirely
corrections: don't let the formation abort, move the ingress out, move SEAD SEARCH out, move
ESCORT SEARCH out, don't mix short-legged flights into a bomber package, separate by altitude
or they mid-air. **An LLM handed only `turn_context` plans badly.** The work is being done by
accumulated engine lore, not by the model — which means the transferable asset is the lore,
and the lore is a bug list.

### What this does and does not change

- The pre-registered card below **still stands** for anyone who wants to test framing 3 on
  its own terms. Do not edit it.
- Seam 7 **stays dropped**. Nothing here shows red's decisions are bad.
- What is now open is a different question with its own evidence: **how many more of these
  planner-geometry defects are there, and what is the cheapest way to find them?** His answer
  was to point an agent at the API and let it complain. That is worth considering on its
  merits, and it is not seam 7.

## The card, pre-registered 2026-08-19

**Written before the feature exists, and not to be edited once it has run.** If it is the wrong
test, replace it with a dated successor and say why.

### The claim being tested

An LLM planning red's turn produces a materially different plan from the HTN's, on the same save,
with the same budget and the same candidate targets — and the difference is one the player meets
in the air.

### The way this test lies

**Novelty reads as quality.** An LLM will produce a *different* plan; different is not better,
and a human comparing two ATOs will find a story in the difference. This is the same
pattern-matching failure §8's card guards against, and it is handled the same way: fix the
observable in advance and measure convergence, not appeal.

### The discriminating measurement

> Same save, same turn, same budget. Plan red twice — once with the HTN, once with the LLM
> through the player-legal action set. Compare the two ATOs.

- **Target overlap O** — the Jaccard overlap of the two plans' distinct target sets.
- **Task-mix distance D** — total variation distance between the two task histograms.

### Fixed now

- Run on **at least two Starfire campaigns**, one of them with a contested front and one without.
- Three independent LLM runs per save, to separate model variance from a real difference.
- Budget parity is mandatory: the LLM plan is invalid if it spends more than the HTN's plan.

### The threshold

| Outcome | Verdict |
|---|---|
| **O ≥ 0.8 and D ≤ 0.15** | The two brains converge. Framing 3 is dead and seam 7 stays dropped. |
| O < 0.8 or D > 0.15, **and** the difference survives a blind read | Reopen seam 7 on framing 3, and only then discuss building anything. |
| Plans differ but the LLM's is invalid or over-budget | Instrument failure, not a result. Fix and re-run. |

**Predicted in advance: O ≥ 0.8.** The §8 shared cause says the map structure dictates the answer,
and this Phase 0 found nothing wrong with the answer the HTN gives.

### The blind read

The comparison must be blind. Print both ATOs unlabelled, in the format above, and have the DM say
which one they would rather fly against. If they cannot tell, the metric result stands regardless
of what the numbers say.

### Cost

One evening. No feature is needed for the HTN half; the LLM half needs only the ability to read a
save and emit a package list, which does not require juanjux's service layer to test.

## What is kept

`tools/measure_red_planner_headroom.py` — the instrument, alongside
`tools/measure_red_axis_persistence.py` from the first framing. Any successor question needs the
same candidate-target and task-mix mapping, and it should not be improvised per run.

## The correction this note also carries

`CLAUDE.md` described seams "2, 5 and 7" as *accepted, not started*. Seam 7 has been **dropped**
since 2026-08-17 and the long-view note's own summary table says so. Fixed in the same change as
this note.
