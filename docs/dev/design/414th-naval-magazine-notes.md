# Cross-turn naval magazines (scope)

**Status:** SCOPED 2026-08-03, nothing built. Driven by the flown Marianas 2027 Tacview
(374 weapon launches, essentially all inside the first five minutes) and the DM's read:
*"in real life they would not dump the entire Chinese fleet's magazines in the opening
shots of the war — if this campaign goes 20 turns they can't keep dumping 20+ per turn."*

---

## The problem, precisely

Three separate facts combine into one bad outcome, and they need separating because they
have different fixes.

1. **Ships fire autonomously and instantly.** `TgoGenerator.set_ship_engagement` spawns
   every ship `OptROE.WeaponFree` with alarm RED, because that is the only way DCS makes
   a fleet fight (ship weapons are OPTION-driven; an `EngageTargets` task is air-only and
   crashed the naval AI when tried). So a ship shoots the moment anything enters weapon
   range.
2. **Modern anti-ship missiles out-range the theatre.** The YJ-18 reaches ~540 km against
   a 205 km Guam–Saipan gap. "In range" is permanently true from t=0, so the whole fleet
   salvos in the opening minute rather than fighting a developing battle.
3. **A DCS mission is a fresh spawn.** Loadouts reset every turn, so red re-dumps a full
   magazine every single turn. Sinking hulls is currently the *only* way volume ever goes
   down — there is no ammunition dimension to the naval war at all.

Hull culling (Marianas 2027, red 93 → 45 hulls) reduces the size of each salvo. It does
nothing about (1) or (3).

---

## What already exists to build on

**§63 cruise missile raids is the proven pattern for exactly this**, and the new work
should mirror it rather than invent anything:

| §63 piece | Where |
|---|---|
| Persisted per-group magazine, no rearm | `Game.cruise_missile_magazines: dict[str, int]` (`game/game.py`, `__setstate__`-defaulted) |
| Lua → Python report of what actually fired | `cruise_missiles_state: list[tuple[str, int]]` (`game/debriefing.py`) |
| Debrief reconciliation | `MissionResultsProcessor` → `game/fourteenth/cruise_raids.py` |
| Emitter | `game/missiongenerator/cruisemissileluadata.py` |
| Runtime | `resources/plugins/cruisemissiles/` |

Critically: **generation never debits**. Only the debrief report does, so re-generating a
turn is free. Any new magazine must keep that property.

The **`S_EVENT_SHOT` hook** needed to count autonomous fire is already used by §39
(snake-and-nape tracks weapon-to-impact) and §77, so the runtime shape is known-good.

The ROE lever is real: `OptROE.Values` exposes `WeaponHold`, **`ReturnFire`**,
`OpenFire`, `OpenFireWeaponFree`, `WeaponFree`.

---

## Proposed tiers

Each tier is independently shippable. **N1 alone fixes the symptom that was flown**, and
should go first.

### N1 — Staggered release (runtime only, no persisted state)

Ships spawn `WeaponHold`; a plugin releases each group to `WeaponFree` on a stagger
(§49's per-site stagger is the precedent — it exists because everything firing in the
same frame was itself a measured problem).

- Emitter: per-group release offsets, spread across a configurable window.
- Effect: the exchange develops over the mission instead of detonating at t=0. A player
  who pushes early meets a fleet that is still working up.
- Cost: one small plugin + an emitter. No campaign state, no debrief channel.
- Risk: low. Worst case a group is released late and contributes nothing that mission.

### N2 — The cross-turn magazine (the actual ask)

- **State:** `Game.naval_magazines: dict[str, int]`, keyed by TGO/group name, seeded from
  a per-hull capacity table (the §63 `LACM_SHIP_DCS_IDS` precedent — a curated dict, not
  a guess: e.g. Type 052D 32 VLS, Type 054A 8 AShM, Burke 8 Harpoon-equivalent).
- **Emitter:** each naval group's *remaining* count.
- **Runtime:** hook `S_EVENT_SHOT`; match the weapon against a curated anti-ship pattern
  list (`YJ-*`, `RGM-84`, `NSM`, `P_700`, …) exactly as §39 matches Snakeyes; increment a
  per-group counter; when the group reaches its remaining allowance, drop it to
  **`OptROE.ReturnFire`**.
- **Report:** mirror per-group fired counts into a `naval_magazine_state` channel; the
  debrief debits `Game.naval_magazines`. Never debit at generation.
- **Effect:** a fleet that empties its tubes in turn 1 is a spent force in turn 2. The
  naval war gains the attrition dimension it currently lacks.

### N3 — Replenishment (optional, later)

Magazines refill slowly, or only at a friendly port, so sustaining a fleet becomes a
logistics decision rather than a free reset. Only worth doing once N2 is flown.

### N4 — Surfacing

A SITREP line when a group goes winchester, and remaining VLS on the unit card. Without
this the player cannot *see* the mechanic and will read a quiet turn as a bug.

---

## The load-bearing unknown

**`ReturnFire` on a winchester ship may also mute its air defence.** DCS ROE is per
*group*, not per weapon type: there is no way to say "no more anti-ship missiles, but
keep shooting SAMs". `ReturnFire` is chosen over `WeaponHold` precisely because it should
leave the ship able to defend itself — but whether a DCS ship under `ReturnFire` will
engage an *inbound aircraft that has not yet fired at it* is unverified and cannot be
settled without flying it.

If it does not, a spent ship is also a defenceless one. That may be acceptable (it is out
of the fight either way) but it must be a deliberate call, not a surprise. **This is the
first thing to test, before building N2.**

Secondary unknowns:

- **Double-counting §63.** A §63 raid fires real missiles from a real ship; those shots
  will also be seen by the N2 `S_EVENT_SHOT` hook. The two magazines must either be
  unified or N2 must exclude LACM weapon types. Unifying is cleaner.
- **Group identity across turns.** Naval TGOs are regenerated each mission; the magazine
  key has to survive that. `TheaterGroundObject.original_name` (the miz marker name) is
  stable and is what `ground_forces` already keys on — use it, not the generated group
  name.
- **Blue symmetry.** Blue's Burkes should be bound by the same rule; the flown file had
  48 Tomahawks *and* 32 NSM from blue. Symmetric in code, as §63 is.

---

## Recommendation

Ship **N1** first — it is small, it directly fixes what was flown, and it needs no state.
Fly it, and use that same mission to answer the `ReturnFire` question. Only then build
N2, which is the part that makes a 20-turn campaign coherent.

Gate: `naval_magazines` (Mission Generation → Naval strike, default OFF until flown), and
a plugin preseeded ON in whichever campaign adopts it first (the §36 saved-defaults-off
lesson).
