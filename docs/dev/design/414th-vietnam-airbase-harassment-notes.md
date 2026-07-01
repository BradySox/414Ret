# 414th Vietnam Ops — Airbase harassment (sapper / mortar / rocket) — design note

**Status:** **LANDED (2026-07-01) — CLAUDE.md §36.** Built as designed: the `vietnam_airbase_harassment`
toggle, the `_populate_airbase_harassment` emitter (+ `_client_spawn_control_points` exclude walk), the
`vietnamops` plugin runtime, the plugin options, the registry (§36), and emitter tests are all in. The
player-spawn exclusion + startup grace were treated as hard requirements (see "critical design tension").
**Still owed: an in-game pass** (checklist L8) — the runtime Lua can't be exercised headless.
**Date:** 2026-06-28 (designed) · 2026-07-01 (landed)
**Related:** [`414th-vietnam-ops-notes.md`](414th-vietnam-ops-notes.md) (the suite this belongs
to — read its "Architecture posture" + "settings page" sections first; this feature is **§F** of
that suite), [`414th-tic-dynamic-fronts-notes.md`](414th-tic-dynamic-fronts-notes.md) (the
`TaskFireAtPoint` / `trigger.action.explosion` runtime patterns reused here),
[`414th-moose-ops-opportunity-map.md`](414th-moose-ops-opportunity-map.md) (why this stays
Tier-A runtime, never `Ops.Chief`). CLAUDE.md §33 (flak gauntlet — the closest existing
pattern), §28 (settings IA).

---

## Why this exists

The Vietnam air war was fought as much **on the ground at the airbase** as in the air. Bien Hoa,
Tan Son Nhut, Da Nang, Chu Lai, and the Khe Sanh strip were under near-constant **standoff
attack** — 122 mm rockets, 82 mm mortars, and sapper infiltration — for years. Tet 1968 opened
with simultaneous ground attacks on a dozen airfields. None of this exists in the Retribution
engine: an occupied airbase is a perfectly safe rear area until the FLOT reaches it.

The flak gauntlet (§33) made the *air over the target* dangerous. This makes the *home plate and
forward strips* feel contested the way they historically were — the missing other half of the
"the rear isn't safe" picture, and a natural thematic partner to the ground-start work
(revetments, period equipment) that surrounds it.

## Architecture posture (inherited, locked)

Same shape as the rest of the suite: **Python emits a small on-marker + target list; the Lua
`vietnamops` plugin runs the runtime behavior inside the one generated `.miz`.** No campaign-brain
changes, no save-format changes, no new `FlightType`. Removing the toggle removes the behavior.
This is the §33 flak pattern almost exactly — flak discovers AAA guns at runtime and throws
airbursts; harassment discovers *occupied airbases* and throws ground impacts near them.

`Ops.Chief`/`Commander` stays out. This is not a planned ground offensive — it is ambient
harassment fire, modelled the same way TIC models firefights (`trigger.action.explosion` /
`TaskFireAtPoint`), not a logistics/AI-tasking system.

## The mechanic

For each **opposing-occupied airbase / FARP / roadbase** in range of the campaign's notion of
enemy reach, the runtime periodically lands a small cluster of standoff impacts (rockets/mortars)
on or near the parking/runway area:

- **Cadence:** a randomized interval (plugin option, default ~minutes apart), not a steady metronome
  — historical harassment was sporadic. Optionally a short "barrage" of 3–6 impacts per event.
- **Aimpoint:** the field's parking/runway centroid (already known to the generator) with a
  generous dispersion radius (plugin option) — most rounds miss, a few are close. This is
  *harassment*, not precision counter-air; the point is to make the ramp tense, not to reliably
  destroy parked jets.
- **Effect:** `trigger.action.explosion` at a modest per-blast power (small, like flak — mostly
  noise/smoke with an occasional bite), plus optional smoke for visibility. A direct hit on a
  parked static or a slow-taxiing aircraft is a bonus, not the design goal.
- **Symmetry:** applies to whichever side's fields are *forward / contested*. v1 may ship
  red-fields-only (the common player-flies-blue case) with a symmetry phase to follow, mirroring
  how Combat SAR phased blue → symmetric.

## The critical design tension — do NOT grief the cold-starting player

A player sitting cold-and-dark on the ramp at mission start is the worst possible victim of this
feature. The whole thing is worthless if it blows up players during a 6-minute alignment. Gating
rules (all mandatory):

1. **Never target the player coalition's active spawn field(s).** The simplest safe v1: harass
   only **AI-occupied** fields, never any field a client flight is spawning from this mission.
   Python knows which control points host client flights (the `cull_farp_statics` logic in
   `tgogenerator.py` already walks `ato.packages → flights → squadron.location` for exactly this
   reason — reuse that determination to build the *exclude* set).
2. **Startup grace period.** Even on eligible fields, suppress all harassment for the first N
   minutes of the mission (plugin option) so nothing fires while players are still aligning
   anywhere.
3. **Tunable to zero bite.** Per-blast power and hit dispersion default low enough that the
   feature reads as atmosphere; campaign authors can dial lethality up for a deliberately brutal
   siege scenario (Khe Sanh).
4. **Coastal/forward only by construction, like NGFS.** If no field qualifies as contested, the
   feature emits nothing and the plugin no-ops.

Open question for build time: do we *also* allow a low-rate harassment of the player's own
**forward** strips (not the main base) once airborne ops are underway, accepting the griefing risk
for immersion? Default answer: **no** in v1 — exclude every player-spawn field unconditionally;
revisit only with explicit campaign opt-in.

## Settings + plugin wiring (proposed)

- **Toggle:** `vietnam_airbase_harassment` on the Vietnam Ops page, "Battlefield & interdiction"
  section, default **OFF**, campaign-flipped ON (Khe Sanh / Yankee Station). Add to
  `_LAYOUT_SPEC` + `features.py` registry at build time.
- **Python emitter:** extend `populate_vietnam_ops_lua` (`game/missiongenerator/vietnamopsluadata.py`)
  with a `_populate_airbase_harassment(vietnam, game)` that emits, per eligible field, the field
  name + parking centroid (x, y) + coalition, plus the player-spawn **exclude** set. Add the
  toggle to the top-level `if not (...)` guard. Emitter is unit-testable exactly like the NGFS
  ship list (`tests/missiongenerator/` — assert excluded fields never appear, absent toggle emits
  nothing).
- **Plugin options** (`resources/plugins/vietnamops/plugin.json`, mirroring the flak/NGFS knobs):
  seconds between events, rounds per event, dispersion radius (m), per-blast power, startup grace
  (s), and a max-reach (m) if we want a range gate rather than a Python-side contested check.
- **Lua runtime** (`vietnamops-config.lua`): a scheduled loop per eligible field, honoring the
  grace period and exclude set, placing the impact cluster. Same Lua-5.1 / definition-order
  discipline as the rest of the plugin; needs an in-game pass (it cannot be validated here).

## Risks / watch-items for the in-game pass

- **Player griefing** (above) — the #1 fail signature: any impact on or near a client spawn field.
- **Performance** — many fields × frequent `explosion` calls. Keep cadence modest; cap concurrent
  events. The flak gauntlet already proved per-frame explosion spam is viable at small scale, but
  harassment is field-anchored and should be far lower volume.
- **Static damage persistence** — destroyed parking statics shouldn't leak into the campaign model
  (this is runtime cosmetic, like §33). Confirm no BDA feedback loop.
- **Marker collision** — coexist with the §33 flak and §34 NGFS markers; reuse the same
  `dcsRetribution.VietnamOps` subtree, one `airbaseHarassment` node.

## Verdict

Buildable, low-risk *if and only if* the player-spawn exclusion + startup grace are treated as
hard requirements, not options. It is the strongest genuinely-MOOSE/runtime idea adjacent to the
ground-start settings (the settings themselves should stay Python — see the modernization pass).
Sequence it after the convoy / Super Gaggle phases; one branch, emitter tests + an in-game pass,
then register as Vietnam Ops §F / CLAUDE.md §35.
