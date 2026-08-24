# Smart threat reaction (§94) — design and adoption record

Adopted 2026-08-24 from [juanjux/dcs-retribution#63](https://github.com/juanjux/dcs-retribution/pull/63).
Feature doc: [`414th-features.md` §94](../414th-features.md). Watch ledger:
[`414th-juanjux-fork-watch-notes.md`](414th-juanjux-fork-watch-notes.md).

## The defect

`game/missiongenerator/aircraft/aircraftbehavior.py` sets
`OptReactOnThreat.Values.EvadeFire` on ~18 flight configurations — every AI flight the
planner builds, on both coalitions. That is upstream's default and DCS' own.

Evade Fire makes an aircraft break defensively when it *perceives* a launch, not when a
missile is guiding on it. One Type-055 or S-300 salvo therefore sends every jet in
perception range defensive at once, most of them from packages the missile was never aimed
at. juanjux measured ~45 aircraft reacting to a single naval salvo, ~43 of them with nothing
guiding on them.

## The fix

Baseline everything at Passive Defense; flip only the group `weapon:getTarget()` names, and
only for as long as that weapon exists.

`weapon:getTarget()` is the whole reason this works. Every earlier attempt at this problem in
the DCS scripting community guesses from geometry — cone tests, closure rate, distance
gates — and guessing is what produces both false breaks and missed ones. The engine already
knows.

Granularity is the honest limitation: `REACTION_ON_THREAT` is a per-**group** option, so the
targeted flight breaks, not the targeted jet. ~2–4 aircraft instead of ~45 is the win; 1
instead of 45 is not available.

## What we changed on the way in

| Change | Why |
|---|---|
| Took head (2026-07-15), not the merged PR | The PR version ran `setOption` over every airplane every 5 s and logged every shot. It stalled the sim in an anti-ship salvo — his words. Our §63/§81/carrier campaigns are exactly that load. |
| `DEBUG` default `true` → `false` | His ships with on-screen text for every tagged shot. Unusable in a mission with a salvo in it, and this plugin is default-on. |
| Added `dcsRetribution.aiReactionExempt` | §61's host red-scramble sets its bandits Evade Fire deliberately. The baseline sweep stomped them back within 10 s. |
| Header trimmed to the house 15-line shape | `CLAUDE.md` comment standard. Every constraint survived the trim. |

## The exemption protocol

Any plugin that sets `REACTION_ON_THREAT` itself must claim the exemption or the baseline
will undo it on the next sweep:

```lua
dcsRetribution.aiReactionExempt = dcsRetribution.aiReactionExempt or {}
dcsRetribution.aiReactionExempt[groupName] = true   -- and clear it when the group dies
```

`ai_reaction.lua` reads the table lazily inside the sweep, so load order does not matter.
`redscramble-config.lua` is the reference implementation (`claim_exempt` / `release_exempt`).

**Checked and clean as of 2026-08-24:** `redscramble` is the *only* plugin in the tree that
sets a reaction-on-threat option at runtime. MOOSE's `AI_A2A_DISPATCHER` (§1 QRA) does not —
only MOOSE's `ESCORT` class does, and the fork does not use it. Re-run
`grep -rn "OptionROT\|REACTION_ON_THREAT" resources/plugins` before assuming that still holds.

## The open question — this is a doctrine change

Passive Defense means no defensive maneuver at all. A flight facing a missile whose target
the engine will not resolve flies straight through it. The re-check runs once at 1 s and then
gives up, which covers a lock that resolves a beat after launch but not a weapon that never
reports a unit target.

Against the fork's SAM density (§41 belts, §60 two-radar sites, MANTIS netting) that could
raise AI attrition measurably. Nobody has measured it — on his fork or ours.

**Falsifier, pre-registered:** if AI loss rates against SAM belts rise enough to change how a
campaign plays, the answer is not to tune the sweep. It is to narrow the baseline — apply
Passive Defense only outside a threat ring, or only to flights not currently tasked against
a SAM — or to turn the plugin off. The plugin toggle is a complete revert with no other
moving part.

## Deferred

- **Per-unit granularity** is not available: the option is per-group in the DCS API. Nothing
  to build here unless ED changes it.
- **Helicopters** are untouched (the sweep is `Group.Category.AIRPLANE` only). They keep
  stock Evade Fire. If a rotary campaign ever shows the same scatter, extend the sweep rather
  than writing a second script.
- **Harness coverage.** `tests/lua/` models no weapon objects and no controller options, so
  this plugin cannot be exercised there today. Adding a `weapon:getTarget()` fake plus a
  recorded `setOption` channel would make the tag/release state machine testable; the
  sim-behaviour half would still need a flight.
