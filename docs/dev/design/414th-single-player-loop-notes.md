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

**Step 2 — pick the package.** The sorties available to *that* airframe: **role**,
package, target, TOT, threat summary, field, and who else is going. Take one seat;
everything else on the ATO stays AI-crewed and sim-resolves exactly as today.

#### Two axes of variety: you pick the jet, the planner picks the job

DM specification 2026-08-03: *"I would like to be put into existing packages, should
still be escort, strike, jamming, whatever the planner decides."*

So the board is **not** a mission-type menu. The player chooses the **airframe**; the
**role comes from what the air war actually needs that turn** — escort one night, strike
the next, ESCORT_JAMMER (§77) the night after, because that is what the packages
require. Two independent variety axes, only one of which the player drives.

This matters for step 2's presentation: **lead with the role and the package**, not with
the target. "Escort — WOLVERINE strike on Haina, TOT 0742, 2× SA-6 on route" is the
useful line. And step 2 must never be filtered to one task family: a multi-role jet
should surface strike, SEAD escort and BARCAP options side by side if the packages want
them.

#### The sortie ladder (and why it settles open call #1)

Aircraft-first forces the answer to "offer-only, or may the board frag for you?" — it
must be **both**, in a strict preference order, or picking a jet the commander ignored
this turn dead-ends. The DM's "put me into existing packages" makes rungs 1–2 **the
model**, not merely the preferred path:

1. **Take a seat in an existing planned flight** of that airframe. Zero planner
   involvement — pure `FlightMembers.set_pilot`. Always preferred.
2. **Add a flight to an existing package.** Your jet joins a package that is already
   going, in **the role that package still needs** — an escort it lacks, a jammer, a
   second striker. The package already owns the target, the TOT and the coordination, so
   this stays inside the commander's plan rather than inventing a private war. *This is
   the headline rung.*
3. **Frag a standalone sortie.** Only when no package can use that airframe at all, and
   **surfaced explicitly** ("no package needs a Tomcat this turn — fly a standalone
   sortie?") rather than silently generated. A private war built to order is precisely
   what the spec above rules out, so this rung must never be reached by default.

A v1 shipping rungs 1–2 only is defensible — some airframes would show "no sortie this
turn," which is honest and still leaves the jet visible in step 1.

#### Mechanically

Rung 1 is the simple case: plan the turn with player pilots **not** auto-seated, then
re-seat the chosen flight through `FlightMembers.set_pilot` (which already claims and
returns pilots correctly) so `Flight.client_count` becomes 1. §43/§73 defaults apply on
the normal path.

**Rung 2 is better supported than expected — both halves already exist:**

- *"What does this package still need?"* → `PackageFulfiller.check_needed_escorts`
  (`game/commander/packagefulfiller.py`) already returns the `EscortType` set a package
  warrants — `AirToAir`, `Sead`, and `Jammer` (§77) — computed from real threat-zone
  intersections against the package's own escorted waypoints.
- *"Put THIS airframe in that slot."* → `ProposedFlight.preferred_type`
  (`game/commander/missionproposals.py`) already pins a specific `AircraftType` into a
  proposed flight, and §44 long-range carrier ops already uses exactly this to force
  chosen airframes through `PackageFulfiller`.

So rung 2 is roughly: ask the package what it needs → build a `ProposedFlight` with that
task and `preferred_type` = the player's jet → fulfil it → seat the player. The escort
prune rules, ROE, join/split geometry and TOT all come along for free, which is the
entire reason to join a package rather than frag beside one.

Open question this raises, for the call list: when a package needs *nothing*, may the
player still be added as a surplus section (a second striker), or is "nothing needed"
a no-offer?

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
2. ~~**Seat scope** — lead of an existing flight, or the whole flight as your wingmen?~~
   **SETTLED 2026-08-03: one seat, AI wingmen — exactly as in MP.** The player takes a
   single seat in a flight; the rest of the flight, the rest of the package and the rest
   of the ATO stay AI-crewed. This keeps `Flight.client_count` at 1 and means no
   multi-slot bookkeeping, no missing-pilot dialogs, and the same generation path an MP
   event already exercises.
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
8. **Rung-3 target selection.** When the board frags a standalone sortie, does it take
   the commander's next-best unserviced target, or the nearest valid one for that
   airframe? And does spending those airframes degrade the AI's own plan for the turn?
   (Only rung with planner side effects, and the spec already demotes it to an explicit
   opt-in — worth deciding before it is built.)
9. **Surplus sections on rung 2.** When `check_needed_escorts` says a package needs
   nothing, may the player still join as a surplus section (a second striker riding the
   package's target and TOT), or is "nothing needed" a no-offer for that package?
   (Recommend: allow it, capped at one surplus flight per package — it widens the
   step-2 list a lot on quiet turns and costs the plan nothing, since the package was
   already going.)

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
  standalone frag; an airframe with no possibility at any rung returns empty rather than
  raising.
- Headless: rung 2 offers the role the package actually needs — a package whose
  `check_needed_escorts` reports `Sead`/`Jammer` offers those roles, and the resulting
  flight is fulfilled with `preferred_type` equal to the chosen airframe.
- Headless: seating never exceeds one player slot — the chosen flight ends at
  `client_count == 1` and every other flight in the package stays AI-crewed.
- Headless: after `pass_turn`, the offer function returns N flights, all blue, all from
  player-capable squadrons, none already client-crewed.
- Headless: seating one flight sets exactly that flight's `client_count` to 1, returns
  the displaced pilot to the squadron, and leaves every other flight AI-crewed.
- Headless: mode OFF is byte-identical — no ATO difference, no seating difference.
- Offscreen Qt: the board renders and the button chain fires (`qt_ui` is not CI
  type-checked, so an in-app eyeball is owed regardless).
- Checklist row: in-app pass for the debrief → board → generate flow.
