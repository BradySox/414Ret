# Sortie records — his `prev_turns` aggregates vs our §91

Not a carve. Both trees answer "what did the mission actually do" and answer it
differently, on purpose. This is the comparison, so the difference is a choice rather
than an accident.

## The same starting complaint

His commit `53d7792` (2026-08-23):

> "Thirty aircraft lost" does not say whether a side lost its gunships or its CAS, and
> those mean different things for the next turn.

Our §91 design note, seam 1:

> The campaign historically learned only which units died. Everything else about a
> two-hour sortie was discarded, and each feature that needed more cut its own channel
> through `state.json` — there are seven.

Same hole. Different fill.

## His shape — type aggregates

Three dicts, derived from attribution his tree already parses for the UI feed:

| Aggregate | Keyed by |
|---|---|
| `air_lost_by_type` | airframe that died |
| `air_kills_by_weapon` | the weapon alone, never the shooter |
| `air_kills_by_victim` | `{victim: {killer: n}}` — the matchup table |

`air_killers` is kept for compatibility and marked redundant.

**His stated reason for stopping there** is a token-budget argument, and it is explicit:

> All keyed by TYPE rather than by event, so they cost a few hundred tokens whatever
> happened in the mission — the per-event record stays out, being a whole event log per
> turn that changes no plan these do not.

That is a correct argument **for his consumer**. `prev_turns` feeds the LLM commander in
`game/agent/`, and an event log per turn would blow the context budget for no planning
gain.

## Our shape — one record per flight

`game/sortierecord.py`, written by `resources/plugins/base/sortie_recorder.lua`.

Per flight: `unit`, `group`, `unit_type`, `coalition`, `first_seen`, `last_seen`,
`track` (a tuple of `TrackSample`: time, x, y, altitude, fuel), `shots`, `hits`,
`ejected`, `player`.

Design constraints worth lifting whatever he does with it:

- **Vanilla DCS only, explicitly not Tacview.** Tacview is a paid third-party program,
  so a feature depending on it silently does nothing for most players.
- **Forward compatible by construction.** Unknown keys ignored, a newer `version` still
  parses, the schema only ever gains fields. Anything malformed degrades to "no data" —
  a mission's results must never be lost to a telemetry bug.
- **`MIN_SORTIE_DISTANCE_M = 1000`.** This one cost a test to find. Our
  `_spawn_unused_for` parks a squadron's untasked airframes as 1-ship Completed BARCAP
  groups; the recorder's sweep sees airborne-category groups and cannot tell them from
  flights. Test 12 had **82 of 158 records sitting on ramps**, and the SITREP would have
  read "145 sorties, 96.7 hours airborne" for a mission 46 aircraft flew. If he builds
  anything that sweeps groups rather than reading the ATO, this trap is waiting.

## Where they actually diverge

His aggregates and our records are not competing implementations — they are different
resolutions, and his are **derivable from ours** while the reverse is not.

| | his | ours |
|---|---|---|
| Cost per turn | flat (a few hundred tokens) | scales with sorties |
| Answers "what died, to what" | yes | yes |
| Answers "did that CAP ever reach station" | no | yes (track + fuel) |
| Answers "was the loadout used" | partly (kills by weapon) | yes (shots vs hits) |
| Consumer | an LLM commander | debrief, SITREP, and the six other channels it collapses |

**The honest read:** if his only consumer is the LLM planner, his call is right and our
records would cost him context for nothing. It becomes wrong the moment a second consumer
wants mission facts — which is exactly how we ended up with seven private channels
through `state.json` before §91 collapsed them. That is the thing worth telling him,
not "take our schema."

## Status here

**◐ PARTIAL** (our row B70). The records reach the campaign; the numbers being
*believable* is on the standing watch list, and the ramp-furniture filter above is why.
