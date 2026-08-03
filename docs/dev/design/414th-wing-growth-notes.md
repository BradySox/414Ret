# The Wing Grows — scheduled squadron arrivals

> **STATUS: DESIGN ONLY (2026-08-03). Nothing is landed.** No code, no settings field, no
> campaign edits. Split out of `414th-single-player-loop-notes.md` §S3 reason **5b** at the
> DM's request, because unlike the rest of that note's motivation layer this is a real
> feature rather than a read-out.

---

## What it is

New squadrons — and, more to the point, **new airframe types** — arrive mid-campaign on a
schedule the player can see coming:

> *F-14 det arrives turn 4. Prowlers turn 6.*

## Why this one, specifically

Two of the three factors in the single-player diagnosis are hit by exactly this feature,
which is why it ranks above everything else in that note that isn't free:

1. **It converts the player's own motivator into the campaign's forward hook.** The DM's
   stated reason for flying is variety — *"I like to fly a lot of different aircraft."*
   Scheduling variety's arrival means you play to turn 6 **because that is when you get to
   fly the Prowler**. The pull comes from the thing the player already wants, rather than
   from a mechanic we hope they will care about.
2. **It inverts "turn 1 is the best mission by construction."** Today the wing is at its
   maximum on turn 1 and decays; every later turn is a degraded copy. With scheduled
   arrivals the turn-1 wing is no longer the whole wing you will ever have, so the
   campaign has an *upward* slope for the first time.

It also composes with the SP Pilot Mode board with zero extra work: a scheduled arrival is
a new entry in that board's **step 1** (pick the jet), and a not-yet-arrived type is the
natural "greyed with a reason" case that note already recommends — *"F-14A — arrives turn
4."* The jet you cannot fly yet is itself the advert.

## What exists, and what does not (verified 2026-08-03)

The DM's framing was *"reinforcement machinery already exists; nothing announces it."*
Half true, and the missing half is the half that matters:

| Thing | State |
|---|---|
| Aircraft replenishment into an **existing** squadron | **Exists** — `Squadron.pending_deliveries`, procurement. But it is a **one-turn buffer** (`Squadron.end_turn` → `deliver_orders`), so multi-turn ETAs are not representable, and it only ever delivers *more of what you already fly*. Serves attrition, not variety. |
| A **new squadron / new airframe type** arriving mid-campaign | **Does not exist.** The campaign's `squadrons:` block is consumed once by `DefaultSquadronAssigner.assign()` during `Coalition.configure_default_air_wing`, and the air wing is fixed from there. `Squadron` carries no activation turn (its `arrival` property is an unrelated `ControlPoint`). |

So this is **new machinery, not a missing announcement** — but it is small and additive.

## The design

### Campaign schema

One optional key on an existing squadron block. Unset = today's behaviour exactly.

```yaml
squadrons:
  Al Dhafra:
    - primary: BARCAP
      aircraft: [F-14A-135-GR]
      size: 12
      available_from_turn: 4        # NEW — the det shows up on turn 4
      arrival_note: "VF-154 det, CONUS"   # NEW, optional — announcement flavour
```

`available_from_turn: 0` (or unset) means present from the start. The value is compared
against the raw `game.turn` — the same number §58's briefing card and the kneeboard use —
so "turn 4" in the yaml is the "turn 4" the player reads in the cockpit.

### Activation

The squadron is **built at turn 0 exactly as today** and simply held back:

1. `DefaultSquadronAssigner.assign()` constructs the `Squadron` as it does now
   (`Squadron.create_from`, QRA reserve seeding, auto-assignable task set) but, when
   `available_from_turn > 0`, appends it to a **pending** list instead of calling
   `air_wing.add_squadron(squadron)`.
2. A per-turn hook (in `Coalition.initialize_turn`, before planning) promotes every
   pending squadron whose turn has come: `air_wing.add_squadron(squadron)`, then populate
   it, then record the arrival for announcement.

**Why building at turn 0 is the right call:** it reuses the whole existing construction
path — preset selection, the §23 country pin, callsign/nickname overrides, def claiming —
with no second code path to keep in sync, and it makes the arrival *deterministic* (the
schedule cannot fail later because a preset became unavailable).

### The part that turns out to be free

`ControlPoint.squadrons` is a **derived property** — it iterates
`coalition.air_wing.iter_squadrons()` and filters on `squadron.location == self`
(`game/theater/controlpoint.py:617`). There is **no separate base→squadron list to
maintain**, so the moment a squadron joins the air wing it appears at its base, is visible
to `AirWing.best_squadrons_for` (which walks `control_point.squadrons`), and becomes
plannable. The planner needs no change at all: the commander simply gains a squadron it
did not have last turn.

Likewise, everything that walks the wing per turn — `AirWing.reset()`,
`populate_for_turn_0()`, `end_turn()` — iterates `iter_squadrons()`, so a pending squadron
is untouched by all of it for free. It is not "hidden"; it is genuinely not in the wing.

### Populating an arrival

`Squadron.populate_for_turn_0(squadrons_start_full)` (`game/squadrons/squadron.py:301`) is
already generic despite its name — it recruits pilots to the limit and, when
`squadrons_start_full`, fills aircraft up to `min(max_size, location.unclaimed_parking(...))`.
An arrival calls the same thing. Worth renaming (`populate`) with the turn-0 caller kept,
rather than duplicating.

Note the parking clamp it applies: **a det arriving at a base that filled up since turn 0
gets fewer jets, silently.** See edge cases.

### Announcement — the whole point

An arrival nobody saw coming is a pleasant surprise; an arrival you *knew about* is a
reason to keep playing. Both halves are needed:

1. **Ahead of time — the schedule.** The upcoming-arrivals list is shown before it lands:
   on the SP Pilot Mode step-1 board (greyed, "arrives turn 4"), and in the S3 pre-turn
   card's anticipation band. This is the motivational half; without it the feature is
   invisible until the moment it fires.
2. **On the turn — the event.** A `Sitrep` line (§29), which already renders in three
   places at once (kneeboard band, web LAST TURN panel, Qt debrief) — so a new
   `arrivals: list[str]` field on `Sitrep` buys all three surfaces. Optionally the §58
   mission-start briefing card.

## Guardrails

1. **Additive and default-off in effect.** No `available_from_turn` anywhere ⇒ byte-identical
   behaviour. No shipped campaign changes unless it authors the key.
2. **No planner change.** The commander is never told about a pending squadron; it simply
   has more squadrons on a later turn.
3. **Symmetric in code, blue-authored in practice.** Nothing stops a red schedule, and red
   arrivals are interesting as escalation — but they must **not** be announced to the
   player as fact. If red arrivals ship, they surface (if at all) as a §70 COMINT-style
   estimate, never a certainty.
4. **The schedule is campaign data, not a setting.** Like §75 victory blocks: authored per
   campaign, because "when does the F-14 det arrive" is a scenario statement.

## Edge cases that need answers before building

- **Parking.** The arrival base may have filled since turn 0. Options: clamp silently
  (today's `populate_for_turn_0` behaviour), clamp *and* announce honestly ("det arrives
  understrength — 6 of 12, no parking"), or divert to the nearest friendly base with room.
  The fork already has a standing parking-fit invariant on two campaigns, so silent
  under-strength arrivals would be a regression in spirit.
- **The base is enemy-held (or gone) when the turn comes.** Cancel the arrival, hold it
  until the base is retaken, or divert. Holding is probably right — and is itself a
  motivator ("retake Balad and the Prowlers can finally base").
- **Def claiming.** A pending squadron claims its `SquadronDef` at turn 0, so its identity
  is reserved and cannot be handed to another squadron in the meantime. This is desirable
  but should be deliberate.
- **Save compatibility.** Pending squadrons are new persisted state on the coalition or
  air wing. Old saves have none: `__setstate__` defaults to an empty list, and a
  mid-campaign upgrade simply never has arrivals. A campaign edit needs a NEW game to take
  effect (the schedule is consumed at turn 0), which must be documented.
- **Air Wing Configuration dialog.** The New Game dialog lets the player edit squadrons. A
  scheduled squadron should be visible there with its arrival turn, and editing it must
  not silently make it immediate.
- **Interaction with `squadrons_start_full`.** Does a turn-4 det arrive full, or at the
  same fill rule the rest of the wing used? Probably the latter, for consistency.

## Open calls

1. **Player-visible schedule, or surprise?** (Recommend: **visible** — the whole
   motivational argument is anticipation. A "surprise" mode could be a per-campaign flag
   later.)
2. **Under-strength arrivals** — clamp silently, clamp and announce, or divert? (Recommend:
   clamp **and announce**; silence is how the parking problem became invisible elsewhere.)
3. **Lost/enemy-held arrival base** — cancel, hold, or divert? (Recommend: **hold**, and
   say so; it turns a retake into a reward.)
4. **Red schedules in v1?** (Recommend: **code symmetric, no shipped red schedules**, and
   never announced as fact.)
5. **Departures too?** A det that arrives on turn 4 and *leaves* on turn 12 is a strong
   use-it-or-lose-it hook, and is the same machinery inverted. Probably v2, but the schema
   should not preclude it (`available_until_turn`).
6. **Which campaigns author one first?** This is content work and the real test of whether
   the feature lands.

## Test plan

- Headless: a squadron with `available_from_turn: 4` is **absent** from
  `air_wing.iter_squadrons()` and from `control_point.squadrons` on turns 0–3, and present
  from turn 4 — with `can_auto_plan` for its tasks flipping accordingly.
- Headless: the arrival is populated on activation (pilots recruited; aircraft per the
  `squadrons_start_full` rule) and is plannable by the commander that same turn.
- Headless: unset `available_from_turn` is byte-identical to today — same squadrons, same
  order, same defs claimed.
- Headless: the pending squadron is untouched by `AirWing.reset()` / `end_turn()` while
  pending (no pilot recruitment, no deliveries, no drift).
- Headless: a `Sitrep` on the arrival turn carries the arrival line; quiet turns carry none.
- Save round-trip: a game pickled with pending arrivals restores them; a pre-feature save
  loads with an empty pending list.
- Campaign-data guard, once a campaign authors one: the scheduled squadron's base has
  parking for it (the standing parking-fit invariant, evaluated at the arrival turn).
