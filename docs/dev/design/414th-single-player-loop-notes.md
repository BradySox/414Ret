# 414th Single-Player Campaign Loop — "SP Pilot Mode"

> **STATUS: DESIGN ONLY (2026-08-03). Nothing is landed.** No code, no settings field, no
> plugin. This note scopes the problem, the seams, and the open squadron calls. Do not
> treat any name below as an existing API.

---

## The problem, stated honestly

The fork's single-player loop dies at a specific, reproducible place:

> Create a new campaign → play turn 1 → **accept results** → never play turn 2.

Note *where* it stops. Not at flying, not at the debrief — the player gets all the way
through `process_debriefing`. It stops at the moment the map comes back and the game
implicitly says **"now plan turn 2."**

Meanwhile the 414th's multiplayer campaigns run to completion, on the same engine, with
the same features, on the same builds.

## Why MP completes and SP doesn't

**In MP you play a pilot. In SP you play the DM *and* the pilot — and the DM job has no
fun in it.**

That is the whole asymmetry. In an MP event the host builds the campaign, processes the
turn, plans the ATO, and generates the miz; the squadron shows up, slots in, flies, and
goes to bed. The commander cost is paid once by one person and amortised across eight
sorties. In SP the same cost is paid by one person for **one** sortie, and it is paid
*before* any reward.

Three fork-specific factors compound it:

1. **Turn 1 is the best mission by construction.** Full wing, full ramp, undamaged
   fields, fresh targets, no attrition, no missing pilots. Every later turn is a
   strictly degraded copy of it. Nothing in the campaign gets *better* as it goes.
2. **Starting a new campaign is cheaper and more rewarding than continuing one.** The
   fork ships 70+ campaigns across a dozen maps and eras, and adds toys weekly. Novelty
   is thirty seconds and one wizard away; turn 2 is ten minutes of commander work away.
   The player is making a rational choice.
3. **Nothing the player personally did carries forward visibly.** They flew 1 of ~25
   packages; the sim resolved the rest. The §29 SITREP that explains why turn 2 matters
   is rendered on the **turn 2 kneeboard** — i.e. it is only readable *after* the player
   has already committed to the thing it was supposed to motivate.

## What already exists (do not rebuild these)

The seams are in better shape than expected. An SP express lane is mostly assembly:

| Piece | Where | Note |
|---|---|---|
| Player pilots are already named per squadron | `SquadronDef` `players:`, `AirWingConfigurationDialog` | `Pilot(name, player=True)` |
| Auto-seating of player pilots already exists | `Settings.auto_ato_behavior` (`AutoAtoBehavior`) | `Prefer` / `Default` / `Never` / `Disabled`, honoured in `Squadron.claim_available_pilot` |
| Player sorties can already be pulled early | `Settings.auto_ato_player_missions_asap` | |
| Turn advance is already one call | `Game.pass_turn` → `finish_turn` + `initialize_turn` | `initialize_turn` re-plans the blue ATO |
| Per-airframe player preferences persist | §43 `flight_defaults.json` | fuel + properties, applied on fresh BLUE flights |
| Per-task loadout defaults persist | §73 `loadout_defaults.py` | |
| The debrief already chains into the next turn | `QWaitingForMissionResultWindow.process_debriefing` | calls `process_results` then `game.pass_turn()` |
| Generation + launch is already one call | `QTopPanel.launch_mission` | fixed `retribution_nextturn.miz`, §66 archives each copy |

The gap is **not** capability. It is that these are a global preference plus five
separate manual UI steps, with no path that says *"you are a pilot; here is your next
sortie."*

## The design — SP Pilot Mode

One setting, four staged pieces. Each stage is independently useful and independently
shippable; **S1 alone already removes the observed stop point.**

### S1 — "Accept results & fly next"

A second button beside `Accept results` in `QWaitingForMissionResultWindow`. It runs the
existing chain — `process_results` → `pass_turn` → generate → launch — with no map
interaction in between. The player goes debrief → next briefing without ever seeing the
ATO.

Everything it calls already exists. The only new logic is **seating the player**, which
S2 supplies; with S2 deferred, S1 can fall back to `auto_ato_behavior = Prefer` and take
whatever the commander seated.

### S2 — the sortie board

After `pass_turn`, present **three** offered sorties from the freshly-planned blue ATO —
task, target, TOT, airframe, threat summary, field — and let the player take one seat.
Everything else on the ATO stays AI-crewed and is resolved by the sim exactly as today.

Mechanically: plan the turn with player pilots **not** auto-seated, then re-seat the one
chosen flight through `FlightMembers.set_pilot` (which already claims/returns pilots
correctly) so `Flight.client_count` becomes 1. §43/§73 defaults apply on the normal path.

This is the piece that reproduces the MP experience: *you choose your sortie from what
the DM fragged, you do not build the ATO.*

### S3 — the pre-turn hook card

The motivation half. Before the player commits to the turn, show the reasons this
specific turn matters — sourced from state the fork **already tracks** but only surfaces
after commitment:

- **§21 downed pilots.** An MIA evader's capture probability climbs with depth toward 90%
  and re-rolls every turn. "Capt. Reyes is evading 22 NM inside — every turn you skip is
  a roll for the POW cage" is a reason to fly turn 2 that has nothing to do with the FLOT.
- **§75 victory progress.** Which conditions are met, which are one objective away.
- **COIN clocks** (IED 3-turn fuse, HVT 4-turn window, dispersed-cell 3-turn maturation) —
  already turn-counted, already expiring, currently invisible until you are airborne.
- **§29 SITREP** — pulled *forward* of the commitment instead of onto the next kneeboard.

None of this needs new game state. It is a read-only view of things `finish_turn` already
computed.

### S4 — guardrails

Non-negotiable, and the reason this is additive rather than a rewrite:

1. **The normal path is untouched.** SP Pilot Mode is an express lane. The map, the ATO,
   the package dialogs, hand-planning, and MP hosting all behave exactly as today.
2. **No AI or red behaviour change.** No planner coupling, no doctrine change, no force
   model change. This is UI flow plus one pilot assignment.
3. **Gated, default OFF** until flown (fork convention), and OFF must be byte-identical.
4. **Never auto-launch DCS without a confirm.** Generation is cheap and reversible;
   launching is not.
5. **No new persisted state** if S3 can be built as a pure view — and it can.

## Honest risk

**Speed is not motivation.** S1 and S2 remove the reason to *stop*; they do not by
themselves supply a reason to *continue*. If the underlying feeling is "I flew 1 of 25
packages and the war moved for reasons I didn't cause," then a faster path to the next
sortie just delivers that feeling more efficiently.

S3 is the piece that answers it, and S3 is the cheapest of the four. **If only one stage
ships, the diagnosis argues for S1 + S3, not S1 + S2.**

The deeper fix — making the player's sortie *consequential* out of 25 — is a separate
question and probably means smaller ATOs in SP, not better UI.

## Open squadron calls

1. **Does the board offer only what the commander planned, or may it frag for you?** If
   the AI planned no CAS and you want CAS, is that a "no" or does the board build a
   package? (Recommend: offer-only in v1 — building packages re-imports the commander job.)
2. **Seat scope** — lead of an existing flight, or the whole flight as your wingmen?
   (Recommend: one seat, existing flight; wingmen stay AI as in MP.)
3. **Is the sortie choice binding?** After taking a seat, can you still open the map and
   edit the flight, or does the board go straight to generate? (Recommend: editable —
   never trap the player.)
4. **"None of these"** — is there a skip/re-roll that passes the turn without flying?
5. **Where does S1 stop?** At "mission generated, go load DCS," or does it launch?
6. **Does SP Pilot Mode force `auto_ato_behavior`?** S2 needs player pilots *not*
   pre-seated; that conflicts with a saved `Prefer`. Override for the mode, or require
   the setting?

## Deferred / non-goals

- **Turnless play** — different problem, different note (`turnless.md`).
- **Campaign victory arcs** — authoring §75 `victory:` blocks on shipped campaigns is
  real and wanted, but it is content work, not this.
- **Pilot career page** (your kills, your squadronmates, medals across turns) — the data
  is tracked; the surface is a separate feature.
- **Smaller SP ATOs** — the "make your sortie matter" lever. Touches the planner, so it
  is deliberately out of scope here.

## Test plan (when it builds)

- Headless: after `pass_turn`, the offer function returns N flights, all blue, all from
  player-capable squadrons, none already client-crewed.
- Headless: seating one flight sets exactly that flight's `client_count` to 1, returns
  the displaced pilot to the squadron, and leaves every other flight AI-crewed.
- Headless: mode OFF is byte-identical — no ATO difference, no seating difference.
- Offscreen Qt: the board renders and the button chain fires (`qt_ui` is not CI
  type-checked, so an in-app eyeball is owed regardless).
- Checklist row: in-app pass for the debrief → board → generate flow.
