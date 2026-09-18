# FinCenturion's campaign dist — study note (2026-09-17)

Status: **study note. Nothing adopted, no policy changed, no tombstone lifted.** A third
party built four campaign-layer systems on top of Retribution and published a write-up of
them. This note records what they are, measures each against what this tree already
decided, and names the candidates and the tombstones.

- Source: his posts in the Retribution Discord, 2026-08-28, plus a later follow-up adding
  bridges and connecting zones between tiles.
- Companion document: *Campaign Systems Overview: Tile-Based Ground War, Intel, PBEM, and
  the Campaign Editor*, 4 pages. **Not vendored here** — see §7.
- He states his own position plainly: the code is probably not usable as is, merging it to
  current Retribution would be very hard, and the value on offer is conceptual.

## 1. What it is

A self-contained distribution, not a PR series and not a fork aimed at upstream. Four
connected systems:

1. **Tile-based ground war.** The theater is carved into a Voronoi partition of irregular
   tiles, generated once per theater/seed. Ground forces become `ManeuverUnit` battalions of
   companies and platoons, each platoon a few elements with individual skill. A unit is
   Attacking, Defending, Reserve, Moving or Resting. Morale, fatigue and supplies drive
   retreat, deployment pacing and the right to renew an attack. Combat resolves three ways —
   captured, contested, repelled — on majority presence.
2. **Intel.** Every ground object carries a per-side intel tier, computed independently for
   blue and red. Low intel means a generic icon and a blurred position (snapped to one of the
   object's own route waypoints). Gained passively per turn, by three recon flight types
   (Recon, Photo Recon with an aircraft and altitude gate, Tile Recon scoring every maneuver
   unit in a tile), and by in-mission proximity.
3. **PBEM.** A Game Master role plus password-protected Blue and Red roles. The active role
   decides what the web map shows; the opposing side is redacted through the intel tiers, and
   role-inappropriate actions are locked out. Turn handoff merges a submitted save into shared
   state with campaign-identity and turn validation.
4. **Campaign editor.** A second mode of the same web client. Reads a starting `.miz`, then
   authors ownership, squadrons, the tile grid, maneuver units, preset locations and victory
   conditions on the map. Every field is written as a **full snapshot, not a diff**, so a
   deletion stays deleted. Personal campaign library, save-as, export bundle, and a
   start-from-blank-theater option that needs no `.miz` at all.

## 2. The four systems, measured against this tree

| His system | Our position | Verdict |
|---|---|---|
| Tile ground war | Same seam as **§90** (front-line model), opposite answer. His is a wargame layer commanded at platoon level; ours is a model of one continuous line the player never touches. | **Rival, not complementary.** And unjudgeable today — see §5 candidate 2. |
| Intel tiers | **§3 was settled by DM call 2026-08-18**: *"hidden until scouted is wrong, it should be hidden until struck, then you should be omniscient."* Graded intel was deleted (`alive_at_last_recon`, `sync_confirmed_status`, the BDA lag). Seam 2 is ACCEPTED only as a tidy-up with a ceiling of two fewer switches. Red is never fogged here. | **Contradicts a live decision.** Tombstone, §6. |
| PBEM | Nothing in this tree. No seam, no tombstone, no prior attempt. | **Genuinely new territory.** |
| Campaign editor | Built here as the blank-canvas campaign maker across eight PRs, then **removed 2026-08-02** — `5349cfa21` (#750), 58 files, −2,971 lines, "Full rip-out of two features (DM call)". The commit records **no defect**; it was a scope call, and it took §20 drop-spawn with it. | **We stopped; he carried it further.** Only the DM reopens it. |

## 3. What it corroborates

His morale/fatigue/supplies economy **has readers**. Combat resolution, automatic retreat,
the right to renew an attack, and deployment pacing all consume it. Admission rule 1 in
[retlab-campaign-architecture-notes.md](retlab-campaign-architecture-notes.md) §4 says a
quantity exists only if two systems read it; §48/§53/§54 died precisely because nothing read
theirs.

**He built the ledger and its consumers in the same pass, and the result is legible.** That is
independent corroboration of this fork's own graveyard diagnosis, from someone who never read
it. It does not make the economy adoptable — it is welded to his tile layer — but it settles
that the diagnosis was about coupling, not about the numbers being a bad idea.

## 4. Where it diverges on purpose

Two divergences, both deliberate on both sides, and neither is a defect in his work.

- **Command by fence, at platoon resolution.** His battle-plan dialog assigns platoons to
  defensive positions and orders their deployment rank. Pillar 3.5 of the architecture note is
  *weight, never fence*, established by §40's removal. His player micromanages; ours sets
  emphasis (§93) and lets the planner weigh it.
- **A wargame with a DCS front-end, versus a mission generator you sample.** He confirms this
  himself — Starfire's "turn this into wargaming" comment is, in his words, close to what he
  wants it to be. The long view's §1 measurement stands against it: Retribution is 13 lines of
  mission builder for every 1 line of campaign brain, and the mission builder is the product.

## 5. The candidates

Smallest first. None started; each carries its own gate.

1. **Bounded deployment stagger.** He caps a worn battalion's platoon trickle at a flat 3×
   baseline (it used to stretch with mission length) and caps cross-battalion pile-up delay at
   2× the interval. Gate: find an instance here first — §9 TIC retry spreading (B108) and §64
   deck stagger are the candidates. **No instance in our build = no fix.**
2. **Retreat along the axis the attack actually came from**, not a fixed fallback direction.
   A §90 detail, cheap and legible. Gate: **B65–B68 flown first.** B65 is PARTIAL and B66
   UNTESTED; the BMS note's candidate-1 gate applies verbatim — extending an untested model
   buries the test, and so does replacing one.
3. **PBEM.** The only genuinely new territory on offer. Gate: DM appetite, and a hard
   dependency — asymmetric two-player turns need per-viewer intel to mean anything, and §3
   deliberately refuses that for blue while red is never fogged at all. **PBEM without the
   intel model is a password on a save file.** Scope it against that, not against his version.
4. **The campaign editor, second attempt.** Gate: the 2026-08-02 removal was a DM call with no
   recorded defect, so only the DM reopens it. If it ever is reopened, the one design idea
   worth taking from him is **snapshot-not-diff authoring** — our own removal recorded nothing
   about that failure mode, and he hit it and fixed it.

## 6. What not to take

- **Graded per-viewer intel percentages.** Settled 2026-08-18 and recorded in CLAUDE.md and
  features doc §3. Re-proposing "intel improves gradually" is reopening a DM decision, not
  fixing a bug.
- **An Intel Difficulty setting and per-side passive gain rates.** The same tombstone with
  knobs on. Rule 2: if nothing flown moves the number, the number is spreadsheet.
- **OPFOR AI aggressiveness sliders.** In fairness his OPFOR AI exists because his
  architecture needs a commander per side — it is a consequence of the tile layer, not a bid to
  make red smarter, and it is **not** seam 7. The sliders are the §55 Red Intent posture dial,
  removed 2026-07-21. Pillar 3.4 stands: posture is an output, never a dial.
- **The tile grid as a replacement for §90.** Not before B65–B68 are flown. Possibly not then:
  §90 answers seam 4 with a model, his answers it with a game.
- **Platoon-level battle plans.** Admission rule 3.

## 7. The licence gate

**His dist's licence is unknown and this tree is LGPL-3.** The MIST-author precedent governs
([retlab-mist-author-repos-notes.md](retlab-mist-author-repos-notes.md)): read it, verify our
own numbers against it, reimplement a mechanism from the Retribution and DCS APIs if we want
it — **never vendor a file, never commit his data.** His write-up is not copied into this repo
for the same reason.

**Ask him the licence before any of this goes near a branch.** He is offering concepts openly
and would almost certainly answer; nobody has asked.

## 8. One thing to check in our own tree

He fixed a class of bug worth a look here: legacy ground objects parsed from the `.miz` were
binding to the geographically nearest control point rather than the one that owns the
territory, so an object could sit deep in one side's land and generate for the other.

We bind the same way — `ConflictTheater.closest_control_point`
(`game/theater/conflicttheater.py:252`), used throughout `mizcampaignloader.py`, with the
influence-zone rules on top (a marker outside every zone binds the nearest *unzoned* CP).

**This is the same seam with a different tie-breaker, not a confirmed defect.** His fix needs a
territory-ownership concept, which tiles give him and we do not have. Worth one check against a
real campaign before anyone calls it a bug.

## 9. Sources

- His Discord posts, 2026-08-28, with seven UI screenshots: the maneuver-unit dialog
  (Fatigue 6/6, Supplies 100%, Morale 100%, Intel 52%), the tile dialog with an "Order package"
  action, both battle-plan dialogs, the intel tooltip (`~40 elements -- Intel: 46%`), and the
  map-layers panel carrying new *Ground maneuver tiles*, *Maneuver units*, *Surface fires
  units*, *Capture zones*, *Attack routes*, *Defensive lines* and *Bridges* rows.
- The 4-page overview PDF, read 2026-09-17.
- His own open ideas list: airborne resupply, naval combat, indirect fires.

## 10. Owed

- Ask the licence (§7). Nothing else is actionable until that answer exists.
- Re-read when he ships the naval, indirect-fires or airborne-resupply work — indirect fires
  is the one that would touch a seam we have open (§9 TIC).
- If candidate 2 or 3 is ever picked up, it gets its own design note; this one stays a study.
