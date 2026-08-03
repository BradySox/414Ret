# 414th Single-Player Campaign Loop — "SP Pilot Mode"

> **STATUS: LANDED 2026-08-03 as feature §83** (S1 + S2 + S3; S4's guardrails are
> honoured throughout). Engineering detail lives in `414th-features.md` §83; this note
> keeps the diagnosis, the reasons-to-continue taxonomy and the open calls.
> **App-side pass owed: checklist B41.**
>
> What landed: the `sp_pilot_mode` gate (default OFF), the "Accept results && fly next"
> button, `game/fourteenth/sp_pilot_mode.py` (the aircraft-first board, ladder rungs 1-2)
> and `game/fourteenth/pre_turn_briefing.py` (the five-section pre-turn card, including
> the capture odds that were computed every turn and never shown).
>
> What deliberately did **not** land: rung 3 (a standalone frag), rung 2's *mutation*
> (the board offers joins; building the flight is the ATO's own add-flight path), and
> smaller SP ATOs — the structural fix, which is planner work and its own change.
>
> Original status line: **DESIGN ONLY (2026-08-03). Nothing is landed.** No code, no settings field, no
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

##### Verified against the code, 2026-08-03 — one earlier claim corrected

An earlier draft of this note asserted that rung 2 was "already supported" by
`PackageFulfiller.check_needed_escorts` plus `ProposedFlight.preferred_type`. The DM
pushed back — *"these feel like they might need a major rework?"* — so both were read
end to end. **Half of that was wrong, and the correction makes rung 2 cheaper, not more
expensive.**

**`ProposedFlight.preferred_type` — the claim holds.** `PackageBuilder.plan_flight`
passes it straight into `AirWing.best_squadron_for(..., preferred_type=plan.preferred_type,
...)`, and §44 (`game/fourteenth/carrier_ops.py`) builds `ProposedFlight`s with it and
calls `fulfiller.plan_mission(...)`. Pinning a chosen airframe into a **newly built**
package is a shipped, exercised path. This is **rung 3's** mechanism.

**`check_needed_escorts` — the claim was overstated, twice.**

1. *Ownership.* It takes a `PackageBuilder`, and `PackageBuilder.__init__` **always
   constructs a fresh `Package`** (`self.package = Package(location, flight_db, ...)`).
   There is no way to hand it an existing, already-planned package, so "ask the package
   what it needs" does not work as written. Its body reads only `builder.package.flights`
   and `builder.package.primary_flight`, so a signature change to take a `Package` is
   small — 1 real call site (`packagefulfiller.py:388`) plus 3 test sites, one of which
   already calls it unbound against a stub — but it *is* a change, not something that
   already exists.
2. *Semantics.* It answers "what is this route **threatened by**", evaluated while the
   package is being built, **before** escorts are added. Called on a finished package it
   does not mean "what is still missing" — you would have to subtract the escorts already
   present.

**But the rework the DM suspected is not needed, because rung 2 should not go through the
commander at all.** Adding a flight to an existing package is already a shipped operation
— it is what the ATO UI does every time a human clicks *Add Flight* on a package
(`QFlightCreator.create_flight` → `PackageModel.add_flight`), and it reduces to:

```python
flight = Flight(package, squadron, size, task, start_type, divert, roster=roster)
package.add_flight(flight)   # then update the package TOT
```

`Flight.__init__` takes the target package directly and `Package.add_flight` appends to
it. No `PackageBuilder`, no `PackageFulfiller`, no new engine seam.

##### Corrected cost of each rung

| Rung | Mechanism | Engine change |
|---|---|---|
| 1 — seat an existing flight | `FlightMembers.set_pilot` | **none** |
| 2 — join an existing package | `Flight(package, …)` + `Package.add_flight` + TOT update (the UI's own path) | **none** |
| 3 — frag a standalone sortie | `PackageFulfiller.plan_mission` with `preferred_type` (§44's pattern) | **none** |
| *role suggestion* | either re-point `check_needed_escorts` at `Package`, **or** infer absent roles from the package's own flights | small, or none |

The role suggestion is the only place any engine edit appears, and it is optional: the
package's existing flights already say which roles are present, which is enough to offer
"this package has no SEAD escort." Reach for `check_needed_escorts` only if the
threat-derived *should it have one* judgement is wanted too.

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

### S3 — the reasons to continue

DM steer 2026-08-03, after reading the S1/S2 spec: *"I'm looking more for reasons to
continue, but this is a great start."* S1 and S2 are the delivery mechanism. **This
section is the actual answer to the question the note was opened for**, and it is
where the remaining design effort belongs.

#### The finding that shapes everything below

The fork already computes almost every reason-to-continue it needs. `Sitrep`
(`game/sitrep.py`) today carries `pilots_mia`, `pows_held`, `red_c2_status` and
`victory_lines` — named people on clocks, proof that your bombing changed enemy
behaviour, and live victory progress. All of it is real, all of it is per-turn, and
**all of it renders only after the player has committed to the next turn** (kneeboard
band, web LAST TURN panel, Qt debrief box).

**The reasons already exist and are pointed the wrong way in time.** That reframes S3
from "invent motivation" to "move an existing surface earlier and sharpen its framing" —
which is why it stays the cheapest stage in the note.

#### The taxonomy — seven reasons, ranked by strength × cheapness

**1. A named person on a clock you caused.** *(strongest, nearly free)*
§21's MIA evader is the best hook the fork owns: a **named** aviator, down because of
*your* mission, with a depth-weighted capture roll re-run **every turn you don't go**
(10% near the front → 90% at 40 NM+). §21's recovery surge then opens the next turn
with the rescue package **already airborne**. That is a complete, working,
emotionally-loaded loop that the player currently cannot see until they have already
decided to play. Needed: promote it to the headline of the pre-turn card, framed as
pressure ("Capt. Reyes — 22 NM inside, 4 turns down; every turn you skip is a roll for
the cage"), not as a status line. POWs are the same hook one stage later.

**2. Proof that your sortie changed the war.** *(strongest structural fix, cheap)*
The honest SP complaint is "I flew 1 of 25 packages and the war moved for reasons I
didn't cause." §52 already **disproves** that when the player kills C2 — enemy planning
degrades measurably (unpredictability up, offensive package cap down) and
`red_c2_status` already says so. Generalise it: attribute outcomes to the player's own
flight wherever the debrief can. "Your strike on the Haina command post cut red to 2 of
3 command posts — they fragged four fewer offensive packages this turn." That single
sentence is worth more than any amount of UI speed.

**3. Open loops you personally opened.** *(cheap, high curiosity value)*
Recon and hunting create unfinished business by construction and the fork already
tracks it: TARPS/AI-recon captures (§3/§12), §3 concealed contacts you circled but never
identified, §49 missile batteries that scooted after you found them, §79 decoys you have
not burned. "You photographed 3 SAM sites; 2 are still alive. The SCUD battery you found
has moved." Curiosity is a renewable resource and this is a read-out over existing state.

**4. A visible finish line.** *(no engine work, pure content)*
§75 shipped the mechanism and **no shipped campaign authors a `victory:` block**, so
every SP campaign is still an open-ended capture-everything grind with no progress bar.
MP campaigns get their finish line socially (the event calendar ends). SP has nothing.
Authoring 6–10-turn objective ladders on the shipped campaigns is the single largest
motivational return available for zero engine risk — and `victory_lines` already renders
the progress once a block exists.

**5. Anticipation — something is arriving.** *(cheap read-out)*
Runway repair timers, pilot replenishment and pending deliveries are turn-counted and
unsurfaced before commitment. **Accuracy caveat, checked 2026-08-03:**
`Squadron.pending_deliveries` is a **one-turn buffer** — `deliver_all` zeroes it at the
next turn boundary — so "four Vipers arrive on turn 12" is *not* representable today.
Aircraft replenishment can only ever announce "next turn," which is weak anticipation.
Runway repair is the one existing multi-turn clock.

**5b. THE WING GROWS — new airframes and squadrons on an announced schedule.**
*(DM proposal 2026-08-03, endorsed: "is awesome")*
The sharpest form of anticipation, and the one aimed directly at this DM's stated
motivator: *"F-14 det arrives turn 4," "Prowlers turn 6."* If variety is what pulls the
player forward, then **scheduling variety's arrival converts the player's own motivator
into the campaign's forward hook** — you play to turn 6 because that is when you get to
fly the Prowler. It also inverts factor (1) in the diagnosis above: turn 1 stops being
the best mission by construction, because the wing on turn 1 is no longer the whole wing
you will ever have.

**Premise check — this one is only half-true today, and the half that matters is the
missing half.** The DM's framing was "reinforcement machinery already exists; nothing
announces it." Verified:

- **Aircraft replenishment into existing squadrons: exists** (`pending_deliveries`,
  procurement) — but one-turn only, per above, and it delivers *more of what you already
  fly*. It does not serve variety at all.
- **New squadrons / new airframe types arriving mid-campaign: does not exist.** A
  campaign's `squadrons:` block is applied at turn 0 and the air wing is fixed from
  there; `Squadron` carries no arrival turn or activation concept (the only `arrival` on
  it is a `ControlPoint` property, unrelated). So the announced F-14 det is **new
  machinery**, not a missing announcement.

**Good news: it is small, and it is the additive kind.** A campaign-authored
`available_from_turn:` on a squadron config, the squadron held out of the air wing until
that turn, then activated and announced. No planner change (the commander simply gains
squadrons it did not have), no save-format risk beyond one field, and unset behaves
exactly as today. The campaign layer already authors squadrons per base with full
control, so the authoring surface exists.

This deserves its own scoped section — probably its own note — because unlike the rest of
S3 it is a real feature rather than a read-out. Recorded here as the highest-value item
that is **not** free, so the note does not misrepresent it as one.

**6. Dread — the enemy is building toward something.** *(cheap, campaigns already author it)*
§W6 red tempo already schedules trail surges and offensive windows per campaign, and §70
COMINT Tier 2 already leaks red's most threatening package of the coming mission. Surface
these as *intel estimates* rather than certainties ("collection suggests an increase in
enemy offensive tempo") and the player has a reason to be there when it lands — plus a
reason to fly the collector that produced the estimate.

**7. A record that is yours.** *(smallest engine gap in the list)*
Sunk cost made visible: your kills, your sorties, your squadron's losses under your
command, who you have rescued. **Gap:** `PilotRecord` (`game/squadrons/pilot.py`) tracks
only `missions_flown` — no kills, no rescues. Everything else is present in the squadron
and downed-pilot records. This is the one reason on the list needing new persisted state,
so it is last.

#### Composition

1, 2 and 3 are per-turn and personal — they answer *"why fly tonight."* 4, 5 and 6 are
arc-level — they answer *"why finish this campaign."* 7 is cumulative — it answers *"why
this campaign rather than a new one,"* which is precisely the choice the player is
currently making wrong. A card carrying one line from each band is a complete answer.

**Everything except 7 is a read-only view of state `finish_turn` already computed.**

#### The sortie board is itself a reason, if the choice has consequences

S2 currently offers a *flavour* choice — which jet, which role. It can cheaply become a
**campaign** choice by showing what each offered sortie would actually change:

- "Cache at Shirqat — slows insurgent regeneration" (§C1 throttle)
- "HVT window closes in 2 turns — kill him or he's gone" (COIN HVT)
- "Command post at Haina — degrades red planning" (§52)
- "Evader pickup — Capt. Reyes, 4 turns down"

Each line is one lookup against machinery that already exists. It converts "pick tonight's
jet" into "decide what the war does next," and a decision you *made* is a far stronger
reason to come back and see the result than a mission you were merely assigned. This is
the cheapest available answer to "I flew 1 of 25 packages and nothing I did mattered."

#### What this does NOT fix

The structural version of that complaint — that the auto-planner services 25 packages
whether or not the player flies — is untouched by any read-out. The real lever is
**smaller SP ATOs**: fewer, larger, more consequential packages so one sortie is a
meaningful fraction of the turn. That touches the planner, needs its own note, and
should not be smuggled into this one. Recorded here so it is not mistaken for solved.

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

**Revised again, same day, by the DM's steer** *("I'm looking more for reasons to
continue, but this is a great start")*. The note has now swung twice, so state the
settled position plainly:

- **S1 + S2 are the vehicle.** They remove the reason to stop and they make the airframe
  variety real. They are a great start — and on their own they deliver the existing
  feeling faster, which is not the goal.
- **S3 is the payload.** The reasons to continue are the actual ask, and the S3 taxonomy
  above is where the remaining design effort goes.

Neither half works alone: reasons the player never sees before committing are the
current bug, and a fast path to a turn with no stakes is a faster treadmill. **Build S3's
content; deliver it through S1/S2's surfaces.**

The deeper fix — making the player's sortie *consequential* out of 25 — is a separate
question and probably means smaller ATOs in SP, not better UI. See "What this does NOT
fix" under S3.

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
