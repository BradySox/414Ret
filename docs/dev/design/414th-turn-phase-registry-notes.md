# 414th — turn-phase registry (scoping, not built)

Status: **scoping only.** Nothing here is implemented. Written 2026-08-19.

## The problem, measured

The fork hand-wires its per-turn work into four ordered sequences:

| Sequence | Fork steps | Guard test |
|---|---|---|
| `Game.finish_turn` | 11 | none |
| `Game.initialize_turn` | 6 | none |
| `Coalition.plan_missions` | 3 | none |
| `MissionResultsProcessor.commit` | 20 | **yes** — `COMMIT_STEPS` + `_record_steps` |

`finish_turn` is 150 lines, `initialize_turn` 117. Most of that is comment: each step
carries 3–8 lines explaining what it is and where it must sit. The ordering constraints
are real and load-bearing, and they exist only as prose:

- *"The coalition-specific turn finalization **must** happen before unit deliveries … If in
  the other order, units may be delivered to captured bases"*
- *"Runs BEFORE the commander so it claims its carrier air first (else the commander spends
  the Hornets on nearer SEAD/BAI and leaves none for the package)"*
- *"Score the front line before capturing bases: … a base's defenders would be miscounted
  as the new owner's casualties once a capture flips ownership, turning a win into a defeat"*

Nothing enforces any of them. Reorder two calls and the tests still pass.

Adding a step today means: write the function, add an inline `from game.fourteenth import`,
pick a spot by reading neighbours' comments, and — in exactly one of the four sequences —
remember to update a list in a test file. That last step is the only reason the debrief is
safe, and it is safe: it caught the §3 command-post reveal being added, 2026-08-18.

## What makes this cheap

**The fork's `finish_turn` hooks are contiguous.** Lines 49–116 of the method are one
unbroken block of fork calls, sandwiched between upstream's coalition `end_turn` loop and
upstream's `if not skipped:`. The same is true of `initialize_turn`.

That matters more than anything else here: the registry replaces **one contiguous block per
sequence with one call**, so the upstream merge surface *shrinks* rather than grows. A design
that interleaved registry steps with upstream's own would be a merge conflict generator and
should be rejected.

## The precedent to follow

`game/plugins/manager.py`'s `_PLUGIN_CLASSES` + the `LuaPlugin` late-init pass is the same
shape, already shipped: a registry of declarative entries, a uniform pass that runs them, and
a test (`game/plugins/tests/test_late_init.py`) that fails when an entry is wrong. CLAUDE.md
records what it replaced — the hand-injected `_inject_*_script()` "scramble pattern" — which
is precisely what the turn loop still is.

## Shape

```python
# game/fourteenth/turnphases.py
class TurnPhase(Enum):
    INITIALIZE = auto()   # Game.initialize_turn
    PLAN       = auto()   # Coalition.plan_missions
    DEBRIEF    = auto()   # MissionResultsProcessor.commit
    FINISH     = auto()   # Game.finish_turn

@dataclass(frozen=True)
class TurnStep:
    name: str
    phase: TurnPhase
    run: Callable[..., None]
    after: tuple[str, ...] = ()      # the prose constraints, as data
    gate: str | None = None          # the Settings field that makes it a no-op

TURN_STEPS: tuple[TurnStep, ...] = (...)
```

Each sequence becomes one loop:

```python
for step in steps_for(TurnPhase.FINISH):
    with logged_duration(step.name):
        step.run(self, events)
```

## What it buys

1. **Ordering becomes enforceable.** `after=("coalition_end_turn",)` topologically sorted,
   so the three constraints quoted above fail a test instead of a campaign.
2. **One guard for all four sequences.** Generalize `_record_steps`: stub every registered
   step, run the phase, assert the registry and the run set match. Today three of four
   sequences have no such guard.
3. **Uniform timing.** `logged_duration` wraps every step. Only the debrief has it now, and
   the turn loop is where the §59/ANTIFREEZE perf work actually lands.
4. **A testable no-op claim.** Nearly every fork hook's docstring says "no-op unless the
   setting is on." With `gate` declared, one parametrized test can assert it for all of them
   instead of trusting 20 docstrings.
5. **`game.py` stops growing.** 14 inline `from game.fourteenth import` statements move out.

## What NOT to do

- **Do not pull upstream's own steps into the registry.** Fork steps only. The value is the
  contiguous-block substitution; interleaving destroys it.
- **Do not convert all four sequences at once.** `finish_turn` alone proves the shape and is
  the biggest block. The debrief is last — it already has a guard, so it gains least.
- **Do not drop the prose.** The three ordering constraints above cost real campaigns to
  learn. They become `after=` tuples *and* stay as one-line comments on the entry.
- **Do not add a plugin-style `enabled` flag.** The gate is the `Settings` field the feature
  already has; a second gate is the §36 lesson.

## Size

Medium. `finish_turn` + `initialize_turn` is ~17 steps to declare, one runner, one guard test,
and a mechanical edit to `game.py`. No behaviour change — the acceptance criterion is that the
full suite passes with the steps running in the same order, then the topological sort proves it
still holds when the declaration order is shuffled.

## See also

- `game/plugins/manager.py`, `game/plugins/luaplugin.py` — the registry precedent
- `tests/test_missionresultsprocessor.py` — the guard test to generalize
- [414th-retribution-long-view.md](414th-retribution-long-view.md) — seam 5 (time between
  turns) is the same region of code; scope them together if seam 5 is ever started
