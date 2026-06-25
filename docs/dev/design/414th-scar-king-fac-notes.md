# SCAR rework — loiter-and-task under the C-130 "King" on-scene commander (design)

**Status:** **Phase 1 MERGED** (PR #187) — loiter + static + inverted SOF capture on `main` (pending
in-game pass F7/F8). **Phase 2 (King designation) + Phase 3 talk-on gate BUILT** on PR #189 (pending
in-game pass F9): the script-as-MAGIC controller cues the box on-station (GREEN smoke + mark + call),
then escalates to a precise RED-smoke designation on the real target after the talk-on window — the
decoy ID puzzle survives, voice-first/additive. **Deferred:** the **laser/IR `SPOT`** (Phase 3b —
needs a spawned designator emitter) and a "say again" F10; **Phase 4** polish; and the
**dead-chase-code retirement** (until after the F7/F8 flight). · **Date:** 2026-06-25
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

> ⚠️ **The King is a PLAYER who can TALK — SRS is the *voice platform*, not just a pop-up channel.**
> A human King checks the strikers in and runs the talk-on **over live voice**, exactly like a real
> AFAC. So every scripted aid above (smoke / mark / laser / IR / a text or SRS-TTS line) is a
> **complement to player voice, not a replacement for it.** Build the designation layer so it is
> **additive and skippable**: it exists so the cue still works with an **AI King** or silent comms,
> and so a human King has something concrete to point at while talking — never as a
> scripted-SRS-popup-*only* flow. The same applies to the **talk-on ID puzzle**: assume two humans
> can be ID'ing the target on SRS, and keep the scripted talk-on as the fallback for the AI/solo case.

## The four forks — DECIDED (2026-06-25)

1. **Discrimination puzzle — KEEP IT COMPLEX (talk-on + decoys).** Spawn/bind several static groups
   (the real HVT armor + decoy/clutter groups) so ID matters. The King runs a **talk-on** ("armor in
   the treeline, *not* the trucks on the road") and only smokes/lases the real one once the player
   calls visual or after a beat. Mis-ID (hitting a decoy) still costs budget via the existing R7
   penalty. This keeps SCAR's soul while moving the cueing off F10 and onto the King.
2. **Static, not fleeing — DROP THE OLD, BUILD THE NEW.** The fleeing-to-a-city moving-HVT mode
   (current spec §5 "armor"/"missile"/"spawn" runners) is **retired**, not kept as a legacy option.
   The target armor is a real, static TGO; the "hold + service" loop is the gameplay.
3. **Hand-off — proximity auto-check-in + King designation; AGREED.** On-station → King calls and
   smokes/marks/lases. One F10 "say again" backstop. **No-King fallback:** degrade to a single F10
   self-check-in (the striker self-designates the area); no ground JTAC needed for v1.
4. **MOOSE mechanism — a thin custom bridge, not a full FAC/`Ops.Chief`.** Reuse the CSAR/MANTIS
   config-bridge pattern: Python emits the kill box + the eligible armor TGO group names + the King
   group; a small `scar`-side Lua controller (or an extension of the existing King code) detects the
   striker on-station and drives the smoke/mark/laser/message. Explicitly **avoid `Ops.Chief`** (the
   ops map flags it as a ground-up strategic build) and avoid a heavy MOOSE `Ops.FAC` dependency for v1.
   **Decoy/clutter:** only the **real HVT armor must be a campaign TGO** (for native loss tracking);
   pure decoy/clutter groups may stay **spawned-and-untracked** (no extra attrition bookkeeping).

## What changes / what's reused

- **Reuse:** the Combat SAR orbit flight-plan builder (the "hold"); the King emission
  (`dcsRetribution.CombatSAR.kings` → generalize to carry SCAR target data); the config-bridge
  plugin style; the SCAR plugin's existing **real-group bind** path (`scar_414_init.lua` already
  binds real armor/missile groups — we keep the bind, drop the chase).
- **New:** Python plans `FlightType.SCAR` as a loiter package over a kill box containing real static
  armor TGOs (instead of emitting a spawned runner); the King-as-SCAR-controller Lua; the
  designation logic.
- **Retire entirely (decided):** the moving-HVT mode — the spawned canned runner + the flee-to-city /
  SCUD-race routing (current spec §5 "spawn"/"armor"/"missile") is **replaced, not kept** as a legacy
  option; and the `scar_results` scoring skeleton (no longer needed once losses are native). Mis-ID/R7
  stays. Pure decoy/clutter groups may still be spawned-and-untracked — only the **real HVT armor** is
  a campaign TGO.

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

## Phase 2 — implementation design (the King-as-controller bridge) · design-first, not built

Phase 1 is on `main` (loiter hold, static target, native attrition, inverted SOF capture). Phase 2
adds the **on-scene-commander designation** so the player is *vectored and cued* onto the held target
instead of cold-searching. Build-ready spec:

**Who is the King (v1 decision): the SCAR script plays the controller ("MAGIC").** Designation is
driven by the existing `scar` plugin on striker-on-station — it does **not** require a King C-130
flight to exist. This keeps Phase 2 minimal and *always available* (a lone striker still gets cued),
and it's the clean substrate for the **voice-first** rule: when a human King *is* flying, they run the
check-in/talk-on **over SRS voice** and the script cues are the additive backstop. Binding designation
to an actual King flight's *presence/position* (so only a real overhead King cues) is a later
refinement (Phase 4 / the auto-planned-commander grand-scheme below), not v1.

**Trigger — reuse what exists.** `package_near(area)` already fires when a human striker crosses the
50 NM ring (`scar_414_init.lua`). Hang designation off the same on-station event — no new detection,
no F10 to check in. (`activate_movement` is now the static "open the fail clock" step; add a
`designate(area)` call beside it.)

**Designation actions (additive, skippable, voice-first):**
- **Smoke** the target's lead unit (`trigger.action.smoke` at the live position from
  `command_vehicle_pos` / the bound group's unit) — the "my smoke" cue.
- **One** persistent `MarkToCoalition` on the target/area (reuse `next_mark_id` + the `brief_*`
  marking already in the file) — not a submenu.
- **One** controller message ("MAGIC: armor in the box, my smoke, cleared to engage"), framed as the
  on-scene controller. Text now; an SRS-TTS line is Phase 4 — but **never** as the *only* channel: a
  human King talks over it.
- **F10 ≤ 1**: a single "say again / re-smoke (MAGIC)" backstop, nothing nested.

**Reuse:** `package_near`, `scar_side`, `command_vehicle_pos`, the `brief_*` mark/message helpers,
`next_mark_id`. **New:** a `designate(area)` function + its one-shot guard (`area.designated`), and the
single F10 command. No new Python emission required for v1 (the area already carries `groups`,
`centerX/Y`, `commandType`).

**Phase 2 ↔ Phase 3 boundary (puzzle tension).** Phase 2 is the *mechanism*: cueing the player onto
the box/target works. Smoking the real lead vehicle outright would trivialise the discrimination
puzzle, so the **talk-on gate** — describe first ("armor in the treeline, *not* the trucks"), smoke/
lase the real one only after a visual call or a beat, mis-ID (decoy kill) still costs R7 — is
**Phase 3**. v1 of Phase 2 may smoke the **target area** (centre) + a descriptive call so the player
still IDs among the decoys; precise on-vehicle smoke/laser arrives with the Phase 3 talk-on.

**In-game pass (new row when built):** striker crosses the ring → exactly one smoke + one map mark +
one MAGIC call, no F10 digging; the cue points at the real target/area; `dcs.log` clean; a human King
talking on SRS is unaffected (cues don't spam over voice).

## Future — auto-planned commander (grand-scheme)

Beyond the player-first v1: when a coalition **owns a C-130J-30**, the HTN planner can
**auto-plan it as a standing on-scene commander** — exactly the pattern the auto-AWACS / auto-tanker
support and `auto_combat_sar` already use (`PlanCombatSarSupport` / `PlanAewcSupport`). A coalition
with a Hercules then *automatically* fields a King overhead that services both the Combat SAR rescue
loop and the SCAR hunt, rather than the player hand-fragging it. This is the "grand-scheme planning
rewrite" target: one auto-planned commander platform feeding multiple dynamic, MOOSE-driven tasks.
Gate it behind a setting (default OFF until flown), airframe-scarcity self-limits (no C-130J-30 → not
planned), and keep v1 player-planned so the auto path is a later, separable increment.

## Open questions / risks (post-decisions)

- **Picture composition tuning:** how *many* decoy/clutter groups, and how the talk-on stays solvable
  but non-trivial (the four forks settled clutter = spawned-untracked, only the real HVT armor a TGO).
- **AI strikers:** v1 is player-first; an AI SCAR striker servicing King-designated targets is later.
- **Kill-box geometry:** how the loiter anchor + target-TGO selection are chosen (nearest eligible
  enemy armor to the front? a designated area? player-picked target on the map?).
- **Talk-on fidelity:** how rich the King's cueing message can be without SRS (text talk-on quality;
  smoke colour conventions; when to escalate from talk-on → smoke → laser).
- **SOF capture loop:** confirm the §15 command-vehicle capture path still rides the static picture
  (it should, since it hangs off the command vehicle, not the armor).

## Definition of done (v1, player-first)

A player plans a **SCAR** flight; it launches and **holds** over a kill box. A **C-130 King**
overhead (player or AI) **detects and designates** a real, static enemy armor group — smoke + map
mark + a single call, **no F10 digging**. The player services it; the kills **attrit the enemy at
debrief through the normal ground-loss path** with no SCAR-specific scoring code. Hitting a decoy
still costs budget (R7). `dcs.log` clean.
