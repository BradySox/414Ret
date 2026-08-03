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

**Two steps, aircraft first.** DM specification 2026-08-03: *"I like to fly a lot of
different aircraft, so there still has to be a first option of what kind of aircraft do
you want to fly, and then you should be presented with package options to pick from."*

That ordering is load-bearing, not cosmetic. **The airframe is the primary axis and the
sortie is chosen underneath it** — not a flat list of sorties that happen to have jets
attached. Getting this backwards produces exactly the failure the mode exists to fix: a
board that keeps offering the same three Hornet sorties because that is what the
commander happened to frag.

**Step 1 — pick the jet.** Every airframe the blue air wing can actually put up this
turn: type, squadron, home field, airframes ready, pilots available. Not filtered by
what the commander planned (see the ladder below) — filtered only by what genuinely
exists and is flyable.

**Step 2 — pick the package.** The sorties available to *that* airframe: task, target,
TOT, threat summary, field, and whether you are joining an existing package or flying
alone. Take one seat; everything else on the ATO stays AI-crewed and sim-resolves
exactly as today.

#### The sortie ladder (and why it settles open call #1)

Aircraft-first forces the answer to "offer-only, or may the board frag for you?" — it
must be **both**, in a strict preference order, or picking a jet the commander ignored
this turn dead-ends:

1. **Take a seat in an existing planned flight** of that airframe. Zero planner
   involvement — pure `FlightMembers.set_pilot`. Always preferred.
2. **Add a flight to an existing package.** Your jet joins a package that is already
   going — an extra section, an escort, a second striker. The package already owns the
   target, the TOT and the coordination, so this stays inside the commander's plan
   rather than inventing a private war. *This rung is the interesting one and is easy to
   overlook.*
3. **Frag a new package** for that squadron against a valid target. Last resort, and the
   only rung that touches the planner.

Rung 1 is free, rung 2 is cheap, rung 3 is the one that needs care. A v1 that ships
rungs 1–2 only is defensible — it would just mean some airframes show "no sortie
available this turn," which is honest and still leaves the jet visible in step 1.

#### Mechanically

Plan the turn with player pilots **not** auto-seated, then re-seat the one chosen flight
through `FlightMembers.set_pilot` (which already claims/returns pilots correctly) so
`Flight.client_count` becomes 1. §43/§73 defaults apply on the normal path.

#### Variety is the point, so measure it

Since the stated motivator is *flying different aircraft*, the board should show what
has already been flown this campaign (per airframe, per squadron) so varying is a
deliberate act rather than a memory exercise. The data is already tracked in the pilot
and squadron records; this is a read-out, not new state. A "not flown yet this campaign"
marker in step 1 is probably the single cheapest engagement win in this note.

This is the piece that reproduces the MP experience: *you choose your jet and your
sortie from what the DM fragged, you do not build the ATO.*

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

**Speed is not motivation.** S1 removes the reason to *stop*; it does not by itself
supply a reason to *continue*. If the underlying feeling is "I flew 1 of 25 packages and
the war moved for reasons I didn't cause," then a faster path to the next sortie just
delivers that feeling more efficiently.

**Revised 2026-08-03 by the aircraft-first spec.** The first cut of this note treated S2
as a pure speed feature and recommended shipping S1 + S3. That was wrong for this DM:
the stated motivator is *flying a lot of different aircraft*, which makes the step-1
airframe picker a **motivation** surface, not a convenience one — "which jet do I get to
fly tonight" is itself the pull into turn 2. S2 is therefore not deferrable, and the
variety read-out inside it is the cheapest engagement win on offer.

Current reading: **S1 + S2 are the ship, S3 is the amplifier.** S3 stays cheap and stays
recommended, but it is no longer the load-bearing motivational piece it was pitched as.

The deeper fix — making the player's sortie *consequential* out of 25 — is a separate
question and probably means smaller ATOs in SP, not better UI.

## Open squadron calls

1. ~~**Does the board offer only what the commander planned, or may it frag for you?**~~
   **SETTLED 2026-08-03 by the aircraft-first spec: both, laddered** (seat an existing
   flight → join an existing package → frag a new one). Picking the jet first makes
   offer-only a dead end whenever the commander ignored that airframe this turn. Rungs
   1–2 are a defensible v1; rung 3 is the only one that touches the planner.
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
7. **How complete is the step-1 airframe list?** Only types with airframes *and* pilots
   ready right now, or the whole wing with the unavailable ones greyed and reasoned
   ("no airframes — 3 turns to delivery")? (Recommend: whole wing, greyed — seeing the
   jet you can't fly yet is itself a reason to play the turn that unlocks it.)
8. **Rung-3 target selection.** When the board frags a new package, does it take the
   commander's next-best unserviced target, or the nearest valid one for that airframe?
   And does spending those airframes degrade the AI's own plan for the turn? (This is
   the only rung with planner side effects — worth deciding before it is built.)

## Deferred / non-goals

- **Turnless play** — different problem, different note (`turnless.md`).
- **Campaign victory arcs** — authoring §75 `victory:` blocks on shipped campaigns is
  real and wanted, but it is content work, not this.
- **Pilot career page** (your kills, your squadronmates, medals across turns) — the data
  is tracked; the surface is a separate feature.
- **Smaller SP ATOs** — the "make your sortie matter" lever. Touches the planner, so it
  is deliberately out of scope here.

## Test plan (when it builds)

- Headless: after `pass_turn`, the step-1 airframe list covers every blue airframe the
  wing can put up, is not filtered by what the commander happened to plan, and reports
  ready-airframe / available-pilot counts honestly.
- Headless: for a chosen airframe, the sortie ladder resolves in order — an existing
  flight of that type is offered before a package-join, and a package-join before a
  fresh frag; an airframe with no possibility at any rung returns empty rather than
  raising.
- Headless: after `pass_turn`, the offer function returns N flights, all blue, all from
  player-capable squadrons, none already client-crewed.
- Headless: seating one flight sets exactly that flight's `client_count` to 1, returns
  the displaced pilot to the squadron, and leaves every other flight AI-crewed.
- Headless: mode OFF is byte-identical — no ATO difference, no seating difference.
- Offscreen Qt: the board renders and the button chain fires (`qt_ui` is not CI
  type-checked, so an in-app eyeball is owed regardless).
- Checklist row: in-app pass for the debrief → board → generate flow.
