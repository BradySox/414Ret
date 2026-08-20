# The campaign architecture — one substrate

Status: **direction note — nothing built, no standing policy changed.** Written 2026-08-20 on
the DM's call: *"disregard what was built and killed in the past — how do we do this overall
objective the right way."* That call authorizes this note to think past the tombstones; it
does not lift any of them. Every rung in §6 lands on its own DM call, and §5 records what
stays dead even from first principles. Successor frame to
[`414th-retribution-long-view.md`](414th-retribution-long-view.md) — none of its audits are
overturned; its seams become consequences of one diagnosis.

## 1. The objective, stated once

A campaign where the war exists independently of the player and the player can read it:
the theater runs whether you fly or not; your sortie is a sample of it and writes back into
it; the enemy reads the same world and its behavior can be narrated from what the game
shows; and between sorties you command by shaping priorities, not by micromanaging packages.
That is what BMS actually delivers, and it is the standing objective behind §89, §90, §91,
§29, §83 and §93.

## 2. The diagnosis the graveyard agrees on

Read the removals as one dataset instead of five verdicts
(`414th-falcon-bms-campaign-notes.md` §3 has the full crosswalk):

| Removed | What it kept | What it lacked |
|---|---|---|
| §53 war economy | its own money | anything else that read the money |
| §54 munitions availability | its own stock ledger | a flow that fed it or a system that read it |
| §48 political will | its own meter | a consequence the meter drove |
| §55 red intent | its own posture dial | an observable surface for the posture |
| §40 phases / ROE zones | its own scripted arc | a war state the arc could emerge from |

**Every one of them kept a private number and none of them had a substrate to stand on.**
Numbers-without-consequences read as arbitrary, and arbitrary gets cut — correctly. Meanwhile
the systems that *lived* are exactly the ones that accidentally started building the
substrate: `SupplyStatus` scaling recovery (`game/theater/supply.py`), §90's rungs on the
transit network, §81/§63's persisted magazines, §56's reserve pool rendered as a bombable
depot. BMS's individual mechanisms are not clever; they are all readers and writers of one
ground-truth theater model, so every number has consequences and every consequence has a
number. That is the whole difference.

## 3. The architecture — five pillars

### 3.1 One substrate: the theater as a flow network

Promote what exists piecemeal into one explicit model, owned in one place:

- **Nodes** — control points holding **stocks**: ground units (`Base.armor` and friends),
  munitions classes, repair capacity. Already half-true: §56's reserve, §81's naval
  magazines, §63's cruise stocks, the parked SAM-magazines scoping
  (`414th-sam-magazines-notes.md`) are all stocks today, each with private bookkeeping.
- **Edges** — the transit network (`game/theater/transitnetwork.py`,
  `TransitNetworkBuilder`) with **capacity**, carrying **flow**: reinforcement, resupply,
  repair. Already half-true: supply tiers, rung A reinforcement, convoys and cargo ships are
  all flow today, each computed separately.
- **Every campaign system reads and writes this model** instead of keeping a ledger:
  `ProcurementAi.spend_budget` buys into stocks, interdiction drains edges, the front line
  (§90) consumes stocks at rates, `Game.finish_turn`/`initialize_turn`'s 39 operations
  become passes over one state instead of 39 private ones.

The two warnings already carved into `supply.py`'s docstring are load-bearing here and carry
over verbatim: tiers are about the *kind* of route (the builder links every airfield pair as
a last resort, so "is there a path" is almost always true), and a coalition with no rear
area reads SUPPLIED — small campaigns must have nothing to model.

### 3.2 The mission is a transaction against the substrate

§91 built the read-back (sortie records); §89 built the front half (the war visibly mid-cycle
when you walk out). The remaining piece: **the abstract war ticks during the mission** at low
fidelity, Lua-side — convoys already move in-mission, the front's firefights already run
(§9); what is missing is the substrate's own quantities (front micro-moves, flow deliveries)
advancing across a 3-hour sortie so the debrief lands in a theater that aged 3 hours. Two
invariants: everything the campaign asserts is visible in the miz, and everything observable
in the miz writes back. No hidden resolution in either direction.

### 3.3 Time: the turn is a variable-length sample, not a fixed jump

Turnless stays dead — DCS cannot spawn mid-maneuver or hand SA to AI (`turnless.md`'s own
hard-problems list; §5 below). But the fixed block is not physics. **Event-driven turn
advance**: run the substrate forward to the next *decision point* — a package worth flying, a
red push starting, a rescue window closing, a stock running out — and offer that as the turn.
`Conditions.advance` (§47) already marches clock and weather by elapsed time; §83's sortie
board and pre-turn "reasons to continue" brief are the seed of the surface. Seam 5's audit
stands: the simulation is already there and silent — this pillar is the reporting gap plus a
variable dt, not a new simulator.

### 3.4 Red is legible, not smarter

Seam 7 is DROPPED and stays dropped: three framings, three Phase 0s, no decision-quality
headroom — red runs the same planner blue does. **This pillar proposes zero changes to red's
decisions.** The BMS lesson is orthogonal: BMS red is not smart, it is *legible* — pushes
have names, posture changes are announced, and the player can narrate the enemy's war.
Fork-side that means two things, both substrate reads:

- **Posture as an output, not a dial.** Red's stance emerges from its own substrate state
  (stocks, flows, front position) by fixed, documented rules — §55 subsumed, not restored:
  no hidden dial, no adaptation, nothing to tune. The authored `red_tempo:` windows
  (`game/fourteenth/red_tempo.py`) stay as the campaign designer's override on top.
- **Surfaced where the fork already has ears.** The SITREP band (§29), the COMINT leak
  (§70), the audible red net (§70), §51's jamming consequences — the surfaces exist; they
  start reporting the substrate's red-side story ("the Fulda push is culminating; its
  supply edge is cut") instead of disconnected events.

The pre-registered seam-7 fly card in the long view §8 is untouched and still the only path
to reopening red's *decisions*.

### 3.5 The player commands by weight, never by fence

§93 region priorities is the first brick and the template: every command lever is a priority
or posture the planner *weighs* — per-region emphasis (built), task-mix emphasis, per-mission
risk tolerance (the BMS threat-ceiling candidate) — never a constraint that fights the sim
(§40's lesson, kept). Paired with plan legibility: the planner can say *why* it fragged what
it fragged, continuing §4's transparency line. The player's hand is never fenced; red never
reads any of it.

## 4. The admission rules

Four rules, applied to every quantity and every lever this architecture admits:

1. **Two readers minimum.** A quantity exists only if at least two systems read it. One
   reader is a private ledger; zero is §53.
2. **Cockpit-reachable.** A quantity exists only if a player action in the miz can change
   it. If nothing flown moves the number, the number is spreadsheet.
3. **Weight, never fence** for every player lever; the auto-planner may be shaped, the
   player's own hand may not be blocked.
4. **Real assets only** (standing constraint): every consequence is carried by a real,
   tracked unit or a visible surface — nothing hidden resolves the war off-screen both ways
   (3.2's invariants).

## 5. What stays dead even from first principles

- **Turnless** — DCS physics: no mid-maneuver spawns, no AI SA handoff, SAM zones freeze
  everything. `turnless.md` remains superseded; pillar 3.3 is the part of its intent that
  survives contact.
- **Authored phase arcs** (§40's classifier) — the arc must emerge from the substrate;
  scripting it against the sim is what made it arbitrary. Campaign designers keep
  `red_tempo:` windows and §75 victory blocks as the authored layer.
- **ROE zones / target-release fences** (§40) — rule 3.
- **Decoy zones** (§79) — rule 4; fake things lie.
- **A smarter red** — seam 7's three Phase-0 verdicts stand; only the pre-registered card
  reopens it.
- **Political will as a meter** (§48) — still has no second reader in this architecture;
  what a campaign needs from it, §75's authored victory conditions already express.

## 6. The rungs — build order, gates, falsifiers

Each rung independently shippable, each landing only when a cockpit can feel it, each on its
own DM call. Later rungs read earlier ones; none requires a later one.

| Rung | What | Absorbs | Gate | Falsifier (kills the rung) |
|---|---|---|---|---|
| **R0** | Inventory: map every campaign quantity to (readers, writers, cockpit path); the substrate spec falls out | — | none (a doc) | **DONE 2026-08-20 — and the falsifier partially fired**: the core is already coherent (`414th-substrate-inventory-notes.md`); R1 shrinks to magazine consolidation + five named couplings |
| **R1** | ~~Big consolidation~~ **reshaped by R0**: one persistence home for magazine stocks (§81 + §63, ready for SAM) + answer the inventory's open questions (delivery-vs-ISOLATED **answered 2026-08-20, inventory §5.1 — no delivery-gating fix needed**; income route-coupling still open) | §81/§63 magazines only | DM call | a third magazine channel ships anyway; or the couplings land as new private numbers |
| **R2** | Supply scales combat effectiveness (BMS candidate 1, already scoped) | §90 rung C counting | **B65–B68 flown first** | cutting a real supply line produces no felt change in one turn |
| **R3** | Munitions as substrate stocks: un-park SAM magazines onto R1; ground-munitions class if R2 held | `414th-sam-magazines-notes.md`, §81 pattern | DM call | scarcity never reaches a cockpit (rule 2 breach) |
| **R4** | In-mission substrate ticking: front micro-moves + flow deliveries age the theater across a sortie | §9 TIC, §89, convoy movers | in-game pass owed by design | mission-length aging is imperceptible or double-counts the between-turn pass |
| **R5** | Event-driven turn advance + the event feed on the SITREP | §47 `Conditions.advance`, §83, seam 5 | DM call | players ignore the offered decision points and just fly fixed cadence anyway |
| **R6** | Red posture derived from red's substrate + surfaced on SITREP/COMINT | §55 subsumed, `red_tempo` kept, §70/§29 surfaces | DM call; seam-7 card untouched | posture changes are noise: the player cannot use them to decide anything |
| **R7** | Remaining command levers: task-mix weights, per-mission threat ceilings (BMS candidate 2) | §93 template, §67 veto precedent | autoplanner-audit discipline; crowded upstream zones | levers get set once and never touched — command without decisions |

R2 and R7 already have scoping in the BMS note's candidates 1 and 2; R3 has the SAM note.
R0 is one session and produces the evidence for whether R1 is worth its risk — start there.

## 7. Relation to the long view

The long view found seams by walking the engine; this note claims the seams share a cause.
Seam 1 (reporting up) and seam 4 (front line) are built substrate edges. Seam 5's audit
("simulated but not told") is pillar 3.3's foundation. Seam 2's accepted tidy-up is
untouched — the intel layer is not part of the substrate and stays three-rules-small. Seam 7
stays dropped; pillar 3.4 is about red's *surface*, not red's *brain*. Where this note and
the long view disagree about emphasis, the long view's *audits* win and this note's
*architecture* organizes them.

## 8. Owed

R0 is done — `414th-substrate-inventory-notes.md` (2026-08-20), verdict in its §4. When any rung lands, this note gains that
rung's result and the features doc gains the section; until then this is direction, and the
tombstone list in CLAUDE.md remains exactly as it stands.
