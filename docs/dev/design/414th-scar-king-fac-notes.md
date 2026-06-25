# SCAR rework — loiter-and-task under the C-130 "King" on-scene commander (design)

**Status:** design / draft (no code yet) · **Date:** 2026-06-25
**Related:** [`414th-scar-task-spec.md`](414th-scar-task-spec.md) (current SCAR),
[`414th-combat-sar-spec.md`](414th-combat-sar-spec.md) (the King + orbit pattern this reuses),
[`414th-moose-ops-opportunity-map.md`](414th-moose-ops-opportunity-map.md) (why we stay off
`Ops.Chief`), CLAUDE.md §15 (SCAR) + §21 (Combat SAR).

## Vision (user's words, locked)

> The SCAR task should be planned like a CSAR package where it orbits and "holds" in an area and
> then is tasked onto an armor group that is **static** (Retribution generates them so losses
> track). Lean on MOOSE much more instead of a Retribution-UI-planned `.miz` vs a canned target
> that is running. **Player task first.** Use the **C-130 King as the on-scene commander.** And
> **eliminate as much of the F10 menu as possible — it's cumbersome.**

## The reframe

| | Current SCAR (spec §5, "spawn" variant) | This rework |
|---|---|---|
| Target | Plugin-**spawned** canned convoy (HVT signature + decoys + clutter) that **flees** to a city | **Real, static** Retribution-generated armor TGO(s) |
| Loss tracking | Spawned units aren't campaign TGOs → deaths don't flow to debrief (hence `scar_results`/`commit_scar_results` is a logged-only skeleton: "scoring is a later increment") | Real TGOs → kills go through the **normal ground-loss/debrief path for free** |
| Flight plan | A strike-shaped sortie at a baked-in moving target | A **loiter/orbit "hold"** package (the Combat SAR / AEWC support-orbit builder) |
| Runtime brain | Retribution pre-scripts the whole picture into the `.miz` | **MOOSE** drives it: the King detects → designates → the player prosecutes |
| Player flow | Arrive, ID the runner among decoys, chase it down | **Check in on-station → King hands off a target → service it** |

The two headline wins fall straight out of "static real TGOs":
1. **Scoring is solved by deletion.** No bespoke `scar_results` campaign-effect bridge — a destroyed
   armor TGO already attrits the enemy in `commit_*_losses` like any other. This retires the hardest
   open piece of SCAR.
2. **The intelligence moves into MOOSE**, the same "Python plans the orbit, MOOSE runs the dynamic
   part" split that made Combat SAR clean — instead of a brittle, fully-scripted runner.

## The C-130 King as on-scene commander (the unifying idea)

The Combat SAR **King** (a C-130J-30 flying an overhead orbit, §21) already exists as an
*on-scene-command* platform with a callsign, a TACAN, and a designation/relay role. **Make it the
SCAR on-scene commander too** — one King platform, two jobs:

- **Combat SAR:** holds overhead a downed pilot, runs LARS, vectors the rescue helo.
- **SCAR:** holds over the kill box, finds the eligible armor, **designates it for the striker**, and
  calls the hand-off.

This is realistic (the HC-130/AFAC "King" mission) and it lets the two features share one Python
emission shape and one Lua bridge style. A player can even fly the King as the C2 element while
another player (or AI) services the targets.

## Minimal-F10 designation model (the "cumbersome" fix)

The hand-off is **designation-first, not menu-first.** When the striker is on-station, the King
(MOOSE) marks the target so the player just *looks and shoots* — no nested F10 tree:

- **Smoke / flare** on the target group (`COORDINATE:Smoke`, `IlluminationBomb` at night).
- **F10 map mark** dropped on the target (`MarkToCoalition`) — one persistent cue, not a submenu.
- **Laser/IR `SPOT`** on the lead vehicle for LGB/auto-lase and an IR pointer for goggles.
- **A single text/SRS call** ("MAGIC, target armor, my smoke, cleared hot") instead of options.

F10 is trimmed to **at most one** entry — a "check in with MAGIC" / "say again target" fallback — and
ideally even that is replaced by **proximity auto-check-in** (the King designates once the striker
enters the kill box, mirroring how Combat SAR spawns the CASEVAC on arrival). Goal: the radio menu is
a backstop, not the interface.

## The four forks — recommended answers (red-line these)

1. **Discrimination puzzle — keep it, but the King runs the talk-on.** Still spawn/bind several
   static groups (the real HVT armor + decoy/clutter groups) so ID still matters, but the King does
   a **talk-on** ("armor in the treeline, *not* the trucks on the road") and only smokes/lases the
   real one once the player calls visual or after a beat. Mis-ID (hitting a decoy) still costs budget
   via the existing R7 penalty. This preserves SCAR's soul while leaning on the King instead of F10.
   *(Alternative if we want it simpler: the King just designates the real target outright — drops the
   puzzle. Recommend keeping the light talk-on.)*
2. **Static, not fleeing.** Drop the flee-to-a-city mechanic for this mode; the target armor is a
   real static TGO so losses track and the "hold + service" loop is the gameplay. The moving-HVT
   "armor"/"missile" race variants can stay as a *separate* legacy SCAR mode, or be retired later.
3. **Hand-off — proximity auto-check-in + King designation.** On-station → King calls and
   smokes/marks/lases. One F10 "say again" backstop only.
4. **MOOSE mechanism — a thin custom bridge, not a full FAC/`Ops.Chief`.** Reuse the CSAR/MANTIS
   config-bridge pattern: Python emits the kill box + the eligible armor TGO group names + the King
   group; a small `scar`-side Lua controller (or an extension of the existing King code) detects the
   striker on-station and drives the smoke/mark/laser/message. Explicitly **avoid `Ops.Chief`** (the
   ops map flags it as a ground-up strategic build) and avoid a heavy MOOSE `Ops.FAC` dependency for v1.

## What changes / what's reused

- **Reuse:** the Combat SAR orbit flight-plan builder (the "hold"); the King emission
  (`dcsRetribution.CombatSAR.kings` → generalize to carry SCAR target data); the config-bridge
  plugin style; the SCAR plugin's existing **real-group bind** path (`scar_414_init.lua` already
  binds real armor/missile groups — we keep the bind, drop the chase).
- **New:** Python plans `FlightType.SCAR` as a loiter package over a kill box containing real static
  armor TGOs (instead of emitting a spawned runner); the King-as-SCAR-controller Lua; the
  designation logic.
- **Retire/repurpose:** the spawned canned convoy + the flee-to-city routing (spec §5) for this mode;
  the `scar_results` scoring skeleton (no longer needed once losses are native). Mis-ID/R7 stays.

## Relationship to the SOF commander-capture loop (§15)

The SOF-insert → commander-capture → stranded-SOF-CSAR-recovery loop is **orthogonal** and stays as
is — it hangs off the *command-vehicle* in the picture, not the armor target. If the static picture
still includes a command vehicle, the capture path can ride along unchanged. Worth confirming when we
spec the picture composition.

## Phasing (each its own branch + in-game pass; never merge unflown)

| Phase | Scope | Validates |
|---|---|---|
| 1 | Plan `SCAR` as a loiter/hold package over a kill box of **real static armor TGOs**; no King yet, no designation — just confirm the orbit + that killing the TGOs attrits natively at debrief | Losses track with zero scoring code |
| 2 | King-as-SCAR-controller bridge: on-station detect → **smoke + F10 map mark + message** on the target | Player flies the hold, gets a designated target, services it; F10 ≤ 1 entry |
| 3 | Laser/IR `SPOT` designation + the talk-on discrimination (multi-group ID, mis-ID R7 penalty on a wrong kill) | The puzzle survives without F10 |
| 4 | Polish: night illum, SRS call, AI-flown fallback, kneeboard | nice-to-haves |

## Future — auto-planned commander (grand-scheme)

Beyond the player-first v1: when a coalition **owns a C-130J-30**, the HTN planner can
**auto-plan it as a standing on-scene commander** — exactly the pattern the auto-AWACS / auto-tanker
support and `auto_combat_sar` already use (`PlanCombatSarSupport` / `PlanAewcSupport`). A coalition
with a Hercules then *automatically* fields a King overhead that services both the Combat SAR rescue
loop and the SCAR hunt, rather than the player hand-fragging it. This is the "grand-scheme planning
rewrite" target: one auto-planned commander platform feeding multiple dynamic, MOOSE-driven tasks.
Gate it behind a setting (default OFF until flown), airframe-scarcity self-limits (no C-130J-30 → not
planned), and keep v1 player-planned so the auto path is a later, separable increment.

## Open questions / risks

- **Picture composition:** how many decoy/clutter armor groups, and do they need to be real TGOs too
  (more attrition bookkeeping) or can clutter stay spawned-and-untracked?
- **King availability:** SCAR shouldn't *require* a King squadron. Fallback when no King is up —
  degrade to a single F10 "check in" self-designation, or a JTAC ground unit?
- **AI strikers:** v1 is player-first; an AI SCAR striker servicing King-designated targets is later.
- **Kill-box geometry:** how the loiter anchor + target TGO selection are chosen (nearest eligible
  enemy armor to the front? a designated area?).
- **Does the moving-HVT mode survive** as a separate legacy option, or fully replaced?

## Definition of done (v1, player-first)

A player plans a **SCAR** flight; it launches and **holds** over a kill box. A **C-130 King**
overhead (player or AI) **detects and designates** a real, static enemy armor group — smoke + map
mark + a single call, **no F10 digging**. The player services it; the kills **attrit the enemy at
debrief through the normal ground-loss path** with no SCAR-specific scoring code. Hitting a decoy
still costs budget (R7). `dcs.log` clean.
