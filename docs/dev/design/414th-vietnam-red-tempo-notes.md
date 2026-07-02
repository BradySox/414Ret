# Vietnam campaign layer W6 — phase-coupled red tempo

**Status: LANDED 2026-07-01** (same session as the approval; the red air-defense
doctrine split shipped just before it). Built exactly as designed below —
`game/fourteenth/red_tempo.py` (the three levers), `CampaignPhase.trail_surge/`
`ground_offensive_turns/resolve_regen` + the `red_tempo:` parse in
`game/fourteenth/phases.py`, the surge read in `vietnam_convoy.py`, the
`apply_red_tempo` hook in `Game.initialize_turn` (after the coalitions plan, before
GroundPlanner reads `cp.stances`), and the authored blocks in all 4 Vietnam arcs
(Bombing Halt: `trail_surge 2.0` + `resolve_regen 1.5`; Linebacker:
`ground_offensive 3` — the Easter Offensive pulse, all four arcs rather than two:
the offensive triggered Linebacker everywhere the arc exists). One deviation from
the sketch: the ground-offensive "reinforcement pulse" is folded into the trail
surge (`GROUND_OFFENSIVE_MIN_SURGE = 2.0` — an offensive implies the logistics
event) instead of separate machinery. Tests: `tests/fourteenth/test_red_tempo.py`
(parse / window math / raise-only stances / once-per-turn regen guard / the
end-to-end convoy surge / the 4 arcs' blocks). In-game pass = checklist M6.

## The gap

The campaign-phases arc (§40 / W3–W4) drives only BLUE: the phase emphasis reorders
BLUE's offensive HTN middle, the ROE zones gate BLUE's planner, and the escalation
copy narrates Washington's war. RED never *answers* the arc — it runs the same
reactive defense + default offensive ordering every turn of the campaign, whatever
phase the war is in.

Historically Hanoi exploited the arc hard:

- **Bombing halts were logistics windows.** Every pause (1965 ceasefires, the 1968
  halt) produced a measured surge down the trail — trucks that moved at night under
  Rolling Thunder moved in daylight during the Halt.
- **Ground offensives were timed to political moments.** Tet '68 landed during a
  lull; the Easter Offensive (March 1972) was a full conventional invasion launched
  *because* the air war had wound down — and it is what triggered Linebacker.
- **Resolve recovered when the bombs stopped.** The Halt years let Hanoi rebuild,
  repair, and re-man; a long pause cost Washington leverage.

## Design — a thin red block on the SAME authored `phases:` YAML

No new engine. The authored-phase model (`parse_phases` / `CampaignPhase`,
`game/fourteenth/phases.py`) grows one optional per-phase block:

```yaml
phases:
  - key: bombing_halt
    name: The Bombing Halt
    min_turn: 8
    red_tempo:
      trail_surge: 2.0        # convoy cadence/volume multiplier
      resolve_regen: 1.5      # Regime Resolve regained per turn while this phase holds
  - key: linebacker
    min_turn: 11
    red_tempo:
      ground_offensive: 3     # front-aggression pulse, N turns from phase entry
```

Three levers, all riding existing mechanisms:

1. **`trail_surge` (float)** — during the phase, `ensure_enemy_trail_convoy`
   (§35, `game/fourteenth/vietnam_convoy.py`, already runs once per `finish_turn`)
   surges: allow a second concurrent convoy and/or scale the units moved per convoy.
   Interdiction stays the counter — a surged trail is *more* Armed-Recon targets, and
   every kill still denies real reinforcements. No-op when `vietnam_convoy_interdiction`
   is off.
2. **`ground_offensive` (int, turns)** — a Tet/Easter pulse: for N turns from phase
   entry, RED's front-line stances flip to the aggressive stance (the TIC stance layer
   / `front_line_stances` the theater state already plans with) and the opfor gets a
   one-time ground-reinforcement pulse toward the active front. The **static front
   clamp (W2b) still bounds movement** — the ±10 % band means the offensive bends the
   line and bleeds BLUE (will drain via frontline losses) but never sweep-captures a
   base; Air Assault remains the only territorial lever. The pulse is pressure on the
   will economy, exactly like the real Easter Offensive was pressure on Paris.
3. **`resolve_regen` (float)** — while the phase holds, RED Regime Resolve regains
   this much per turn (`game/fourteenth/political_will.py`, next to the POW drain).
   Makes a long Bombing Halt *strategically costly* for BLUE: the will economy
   couples both ways, and "just wait out the halt" stops being free.

## Boundaries

- **Authored-only.** Tier-0 (inferred) phases never carry `red_tempo` — generic
  campaigns are untouched. Default-off unless a campaign author writes the block.
- **No save-schema change.** The authored arc is re-derived at load (never pickled),
  same as the W4 zones; the only per-turn state is the ground-offensive countdown,
  which can live on the existing phase state (`phase_entered_on_turn` already
  persists — the countdown is derivable).
- **The §17 boundary holds.** Red's *reactive* defense stays deterministic; these
  levers touch logistics volume, front stance, and the will economy — not target
  selection.
- **Red doctrine split is orthogonal and already shipped**: red Vietnam factions fly
  `VIETNAM_AIR_DEFENSE_DOCTRINE` (no Alpha Strike fan / no escort reserve / no forced
  strike escorts; every MiG back on the W5 ambush war).

## Authoring plan (the 4 Vietnam arcs)

- **Bombing Halt** (all 4): `trail_surge: 2.0`, `resolve_regen: 1.5`.
- **Linebacker** (the two 1972-shaped arcs): `ground_offensive: 3` — the Easter
  Offensive pulse that historically *caused* Linebacker, landing exactly when the
  player's ROE finally opens up.
- Rolling Thunder / Linebacker II: no block (baseline tempo / the ground war is
  spent by December '72).

## Delivery

One PR (W6): parse + the three lever applications + arc YAML edits + tests
(parse/no-op-when-unauthored/clamp-respected/regen math) + a checklist row (needs an
in-game pass for the stance flip; the convoy/regen halves are headless-verifiable).
