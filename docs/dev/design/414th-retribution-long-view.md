# Retribution — the long view

**Written 2026-08-17.** A plain read of how the engine actually works, and the seven weak spots
that follow from it.

| Seam | Short version | Status |
|---|---|---|
| **1 — what the mission tells the campaign** | When you land, the campaign only learns who died | **BUILT 2026-08-17** — features doc §91, pass row B70 |
| **2 — how the game tracks what you know** | Three rules, not five; 18 methods thread `viewer` to reach them | **ACCEPTED** — scope cut to a tidy-up by the 08-17 audit |
| 3 — the map graph | Roads route traffic but can't be cut | Analysis only — but see seam 4 rung A |
| **4 — the front line** | One number divided by another | **BUILT 2026-08-17** — all five rungs; features doc §90, pass rows B65–B69 |
| **5 — time between turns** | 39 things happen between turns; the SITREP reports 7 | **ACCEPTED** — reframed as a *reporting* gap by the 08-17 audit |
| 6 — the squadron layer | Already scoped in its own note, not built | See that note |
| 7 — the enemy | Red is amnesiac, and nothing it decides is visible | **DROPPED 2026-08-17** — two framings, two Phase 0 kills, one shared cause; see §8 |

**Seam 7 was missed in the first pass, and that was the note's biggest failure.** §1 measured
13 lines of mission builder per line of campaign brain, and observed that red is blue's planner
instantiated twice — then never turned either fact into a seam. Numbering stays stable, so it is
seam 7 despite arguably being the most important. See §8.

**What the build changed about this note.** Two claims below were wrong and are corrected in
place: `Base.strength` is a float in `[0.0, 1.0]`, not a unit count (§5), and the §26
capability weighting in `game/sim/combat/capability.py` is **air-to-air only** — it weights
flights, not ground units, so rung C could not reuse it and uses `total_armor_value` instead.

Seam 4 rung A also turned out to be seam 3's edit at one-tenth the size, as predicted: the
supply gate is the first thing in the codebase that makes cutting a route cost something.
Seam 3 proper — per-link capacity and damage state — is still unbuilt.

**Re-measure before quoting any number here.** Everything below was measured on 2026-08-17 and
will drift. The `file:line` references are how you check.

**Three seams have now been audited against the code rather than read, and all three premises were
overstated.** Seam 7 died outright (two framings, §8). Seam 2 is three rules, not five (§3). Seam 5
had the gap backwards — the between-turn time is simulated, just not reported (§6). The pattern is
worth knowing before trusting seam 3's description at face value: this note's structural claims were
written by reading the code, and measuring keeps deflating them.

---

## 1. What Retribution is

**A mission generator with a save file attached.** The campaign part is thin, and always has been.

| Thing | Size |
|---|---|
| All of `game/` | 96,038 lines |
| The mission builder, `game/missiongenerator/` | 32,739 lines — a third of the engine |
| The entire campaign AI, `game/commander/` | 2,453 lines |

That is **13 lines of mission builder for every 1 line of campaign brain.** One file that
resolves off-screen combat (`game/sim/missionresultsprocessor.py`, 773 lines) is a third the
size of the whole commander.

Three more facts of the same kind:

- **The mission barely reports back.** What comes home is a list of dead unit names, a list of
  captured bases, and seven one-off extras bolted on over time (`game/debriefing.py:129`).
- **The front line is one fraction divided by another** (`game/theater/frontline.py:191`), and
  those fractions are health bars in the range 0.0–1.0, not counts of anything
  (`game/theater/base.py:4`).
- **Red is not an opponent.** It is blue's planner run a second time with different inputs —
  the same `TheaterCommander` class, built twice (`game/coalition.py:313`).

**None of that is a bug.** The mission builder is the product and it's good. It just means more
work on the builder pays less than it looks, and work on everything else pays more.

---

## 2. Seam 1 — what the mission tells the campaign · **BUILT**

### The problem in one line

You fly a two-hour sortie, and the campaign learns one thing: which units died.

### Why it's like that

Every time a feature needed to know something else, it punched its own hole through the wall.
There are seven holes now (`game/debriefing.py:147-183`):

recon photos · minefields · cruise-missile magazines · naval magazines · QRA survivors ·
ejections · rescues

Six of the seven are ours. Each one carries its own Lua writer, its own reconcile function, its
own "this is empty on old saves" clause, and its own guard against double-counting. That bill
gets paid again by the next feature that needs anything.

**Seven holes in one wall is a missing part, not seven features.**

### What we build instead

One record per flight, written by the base plugin, into the file that already comes home:

- where the flight actually went
- how long it stayed on station
- fuel at the end
- what it shot, and at what
- who shot at it, from where, and when

Nothing new has to be invented. `state.json` already crosses this boundary seven times a
mission. It needs an agreed format, not a new pipe.

### What that gets us that we simply cannot do today

- Debriefs that describe the flight instead of listing corpses.
- Losses that follow from what happened, not from whether a name showed up in a kill list.
- The planner learning that a route which got someone killed is a route that gets people killed.
- Any question of the form "where was this flight at 14:20" — right now, unanswerable.

### Tacview is not the answer

[Tacview](https://www.tacview.net) is a paid third-party program outside DCS. It only writes an
`.acmi` on machines where somebody installed it and its DCS exporter.

**It cannot be a dependency.** A campaign feature that silently does nothing for players without
an add-on is not a feature.

That makes the case for doing this properly *stronger*, not weaker — there's no free shortcut,
so the plugin has to write it, into the path that works for everyone.

Tacview stays useful for two things: checking that what the plugin reports is true, and the hand
measurement it already does here (`game/data/carrier_deck_decor.py:42`, `:102` are numbers a
human read off recordings). Both fine. Both stay.

### The catch

An agreed format is a promise. Every save and every plugin version has to cope with it being
missing or older. The seven existing holes each solved that badly and separately; this has to
solve it once and properly.

---

## 3. Seam 2 — how the game tracks what you know · **ACCEPTED**

### The problem in one line

We have built "the player doesn't know this yet" five separate times, five separate ways.

### AUDITED 2026-08-17 — it is three, not five

The "five costumes" claim above was written by reading and is wrong. Measured:

| Claimed a costume | Actually |
|---|---|
| recon fog (§3) | A rule — `known_for` |
| BDA damage lag | A rule — `alive_for` |
| SCAR command posts (§15) | A rule — `hidden_on_player_map` |
| COMINT (§70) | **Not a rule.** It *writes* `discovered_by_player` (`comint.py:249`) — a producer feeding `known_for` |
| recon capture (§12) | **Not a rule.** Same one-line write (`missionresultsprocessor.py:467`) |
| decoy zones (§79) | **Not in this layer.** Separate fake objects (`decoy_zones.py`) |
| C-130 ISR (§2) | **Not in this layer.** In-mission Lua |

Counted across `theatergroundobject.py`, `theatergroup.py`, `controlpoint.py` and `fogofwar.py`:
**21 methods take `viewer`. Exactly 3 decide anything. The other 18 forward it and nothing else.**

**The evidence cuts against the seam's own argument.** COMINT is the newest intel feature and it
cost *one line* against the existing model; recon capture is the same. So "every new one pays full
price" is not supported — the producers already share a path through `discovered_by_player`.

### What is actually there

Two things, both smaller than the section above claims:

1. The 3 rules duplicate an identical three-clause guard — `viewer is None` / `fog_revealed()` /
   friendly → truth — with divergent tails.
2. 18 methods hand-thread `viewer` purely to reach those 3 rules. That is the layer's real
   carrying cost, and it is boilerplate rather than divergent logic.

With the standing rule capping the payoff at "fewer switches than we started with", the ceiling is
removing two switches and de-duplicating one guard. **A tidy-up, not an enabling abstraction.**
Accepted on that basis, with no larger claim attached.

### The catch

This is surgery on a load-bearing layer that lives in save files. And there's a standing rule
against re-splitting it into paired methods (see CLAUDE.md).

**Rule for this work: it has to end with fewer switches than it started with.** More switches
means it went backwards.

---

## 4. Seam 3 — the map graph · analysis only

### The problem in one line

Blowing up a truck costs the enemy a truck. Cutting the road costs them nothing.

### Why

The road network (`game/theater/transitnetwork.py`) has **no memory at all** — nothing for
blocked, nothing for damaged, nothing for capacity. `cost(a, b)` at `:82` is a fixed number
based only on the link type: road, ship, or air. The network gets rebuilt from the map, routed,
and thrown away.

A destroyed bridge does not exist in it. A struck depot does not exist in it.

### What that explains

Every feature that circles logistics — convoy interdiction, ambient convoys, motorpool depots,
sea supply — lands as **content** rather than **consequence**. They put trucks on roads. They
don't make the road matter.

### Smallest real version

Give each link some state and a capacity. Let strikes wear it down. Then feed the front-line
strength that already drives `frontline.py:191` through it.

That turns the front line's fraction into the *output of a supply model* instead of a number
that drifts on its own.

### Why it's analysis only for now

This is the one change that moves campaign balance everywhere at once, and our balance is tuned
by flying, not by tests. It would need its own run of fly-cards on top of the backlog in §8.

**But note:** seam 4's first step (below) is the same edit, at one-tenth the size.

---

## 5. Seam 4 — the front line · **BUILT**

### The problem in one line

The most-looked-at thing in the campaign is computed from the least information in the engine.

### The whole model, in four lines of code

| What | Where |
|---|---|
| Position = `blue.strength ÷ (blue + red) × route_length`, clamped off both ends | `frontline.py:191-206` |
| `strength` is a health bar, 0.0 to 1.0, starting at 1.0 | `base.py:4-11` |
| It moves in exactly three places: a flat per-turn top-up, the ground battle result, and a reset to zero on capture | `game.py:573` · `missionresultsprocessor.py:673-683` · `controlpoint.py:1086` |
| Position is recalculated from scratch each turn — it isn't stored | `frontline.py:96` |

### Five things it can't express

1. **It doesn't know how many tanks are there.** 1.0 vs 1.0 puts the line dead centre whether
   each side has five vehicles or five hundred. It's a morale number wearing a position's hat.
2. **Attacking costs the same as defending.** The battle result is a straight swap — winner up,
   loser down by the same amount. Nothing is dug in. Nothing is held. Retaking ground refunds
   exactly what losing it cost.
3. **Losses heal on a timer.** The per-turn top-up applies no matter what — whether or not
   anything reached that base, whether or not the road is open. Ground taken drains back for free.
4. **You can't predict it.** Position comes from *both* sides' strength, and hiding red's
   strength is the entire point of the fog layer. The most visible feedback in the campaign is
   calculated from a number the player is deliberately not allowed to see.
5. **The whole front is one point.** It slides along one line. No breakthroughs, no salients, and
   a mountain pass advances exactly as fast as open ground.

### The ladder — cheapest first

**A. Make the per-turn top-up depend on supply.** Right now it's a fixed constant. Make it a
function of whether supply actually reached that control point. **One constant becomes one call.**
This is also seam 3's edit at one-tenth the size — two seams, one change. Best value in this
whole document.

**B. Stop making attack and defence cost the same.** Make taking ground cost more than holding
it. Fronts then sit still until pushed, and give when they break — which is what a front line is
supposed to do. Contained to one function.

**C. Make strength know about scale.** Weight it by the ground force actually present instead of
a 0-to-1 fraction.

> **Corrected during the build.** This originally claimed §26's auto-resolution already works
> out combat power in the same file. It does not — `game/sim/combat/capability.py` weights
> *flights* for air-to-air resolution and knows nothing about ground units. The ground
> analogue that does exist is `Base.total_armor_value` (price × count), which is what shipped
> as `Base.front_line_weight`.

**D. Weight the route by terrain.** A per-segment multiplier. The geometry already exists — our
supply-line standard has us drawing routes along real driveable corridors, so the segments
already mean something. Only the weight is missing.

**E. Sample the front at several points.** Local balance at each, so you get salients and
breakthroughs. Biggest job here by far — FLOT generation and CAS/BAI targeting all assume one
point today.

### Don't lose what works

The current model has one genuinely good property: a fraction can't run off the end of the road,
and it stores nothing so it never needs save migration.

A and B both keep that — the clamp already exists (`_adjust_for_min_dist`) and `strength` is
already saved. Anything further up the ladder has to prove it keeps both.

---

## 6. Seam 5 — time between turns · **ACCEPTED**

**The problem in one line, as first written:** a turn is a jump, not a sample of an ongoing war.

### AUDITED 2026-08-17 — that is wrong, and the real gap is the opposite

A great deal already happens at a turn boundary. Counted from `Game.finish_turn` and
`Game.initialize_turn`: **39 distinct operations.** Trail and ambient convoys spawn and move,
ambushes seed, insurgent cells regenerate and re-infiltrate, IEDs and HVTs and dispersed cells
advance, decoy zones shift, ships relocate and re-parent, supply status is recomputed, strength
recovers, weather evolves, front lines move, COMINT reveals land, red tempo applies, and the
ground war is re-planned.

The engine is not skipping the time between turns. It is simulating it and **not telling anyone**:

| | |
|---|---|
| Between-turn operations | **39** |
| Lines the SITREP can emit | **7** |
| Sampled systems with zero player-facing hooks | **5 of 8** — trail convoys, ambient convoys, ambushes, ship movement, and more |

**So seam 5 is a reporting gap, not a simulation gap** — the same class as seam 1, pointed the
other way. Seam 1 asked what the mission tells the campaign; this asks what the campaign tells the
player.

That reframing is *additive*: it surfaces behaviour that already exists, on the §29 SITREP surface
that already exists, with no refactor of load-bearing state. §89 proved the in-cockpit version of
"the war ran without you" reads well, and seam 1 extended the SITREP successfully.

### Phase 0, owed before building

Not everything invisible deserves a line, and a report nobody reads is worse than silence. The
disconfirming question: **which of the silent systems actually change state the player would act
on?** If ambient convoys and ship drift are inconsequential, reporting them is noise and the seam
shrinks to whatever survives.

---

## 7. Seam 6 — the squadron layer · already scoped elsewhere

Not news. `414th-coop-persistent-campaign-notes.md` scoped this on 2026-07-08 and it hasn't been
built: no human owns a pilot, no persistent frag board, no record that follows a person across
turns.

Listed here only so the set is complete. That note's decisions stand; nothing here revisits them.

---

## 8. Seam 7 — the enemy · **DROPPED** (both framings killed by Phase 0)

### The problem in one line

Red is not a bad opponent. Red is an **amnesiac** one, and nothing it decides is ever visible.

### What red actually is

- **The same planner as blue.** `TheaterCommander(self.game, self.player)` (`game/coalition.py:313`)
  — one class, instantiated twice, differing only in inputs. That is worth *keeping*: it guarantees
  red plays by the rules you play by. The seam is not "give red its own planner."
- **It can see you.** `TheaterState` carries `enemy_air_defenses`, `enemy_convoys`, `enemy_shipping`,
  `enemy_ships`, `enemy_battle_positions`, `enemy_barcaps` (`theaterstate.py:131-141`). Red has a
  decent current-frame picture. It is not blind.
- **It cannot remember.** `TheaterState.from_game(...)` (`theaterstate.py:229`) rebuilds the whole
  state from the current game every turn, and `TheaterCommander` stores nothing but `game` and
  `player`. So red cannot commit to an axis, cannot notice you have hit the same target three turns
  running, cannot follow through on anything it started.
- **It weighs 2,453 lines** against the mission builder's 32,739. That ratio is not damning by
  itself — the builder *should* be big — but it says where the investment went.

### Why this was left out of the first pass, and why that was wrong

Two defensible reasons and one bad one. Defensible: §55 Red Intent was removed on 2026-07-21 and
the features doc says "do not restore", so re-opening it needs a reason. Defensible: "smarter AI"
is the classic unbounded project. The bad one: the observation was made in §1 and simply never
carried into a seam. That is how a measurement becomes decoration.

### What §55 actually teaches, which is not what it looks like

§55 was removed as "the symmetric teardown of the §40 removal" — part of one deliberate purge of
abstract campaign-layer machinery, alongside campaign phases, the war economy, munitions
availability and the commitment ceiling. It is worth being precise about what §55 had:

- It **had** memory: a rolling trend and graduated per-front postures.
- It **had** legibility: ribbon and SITREP posture surfaces.
- It was removed anyway.

So the lesson is not "memory bad" or "surface it and it will land". It is that **§55's output was a
word on a ribbon rather than something you met in the air.** `CONSOLIDATE`/`ATTRITION`/`SURGE` told
you a label had changed; it did not put anything different in front of your aircraft.

**The test any proposal here has to pass:** the player must be able to infer red's intent from what
they fly against, without reading a label. If the only way to know red changed its mind is a
caption, it is §55 again.

### Where the thin end is

Red already reacts within a turn (§89 reactive red: a struck objective gets a defensive patrol) and
that is the shape that works — a decision you meet in the air. The unbuilt thing is **continuity**:
red committing to something across turns and the player discovering it by flying into it. Concretely,
the smallest version is a persisted red intent that survives `from_game` and biases target selection,
with **no** new surface at all — you learn red is pushing the northern axis because that is where its
packages keep coming from.

### SEAM 7 IS DROPPED, 2026-08-17

Two framings, two Phase 0 measurements, two disconfirmations, **one shared cause**. Dropped rather
than re-scoped a third time — chasing a feature past its own evidence is the failure the
pre-registration discipline exists to prevent.

**Framing 1 — red commits to an axis.** Killed: there is effectively one axis. Detail below.

**Framing 2 — red defends where the player keeps flying.** Killed the same day, before anything was
written, by measuring its premise on the same save (Syria, Desert Trident, turn 4):

| | |
|---|---|
| Blue attacks | King Abdullah II 7, Muwaffaq Salti 5, H3 Southwest 1 |
| Red CAPs | King Abdullah II 2, Muwaffaq Salti 2 |
| Capped but **not** attacked | **none** |
| Attacked but not capped | H3 Southwest — 1 of 13 blue packages |

Red already defends exactly where blue attacks, wasting no CAP at all. The feature would have
produced the behaviour that already exists.

**The shared cause, which is the finding worth keeping.** Red's choices and the player's choices are
both functions of the same static map structure: blue attacks the forward objectives because that is
where the targets are, and red defends them because that is where the threat is. Red therefore
*looks* responsive with no memory whatsoever, and memory has nothing to add. The original diagnosis —
"red is amnesiac, therefore bad" — does not follow, because amnesia costs nothing wherever the
structural answer and the responsive answer coincide.

The one measured gap is thin and not worth a feature: red's CAP weighting is flat (2/2) where blue's
effort is 58/42. With four CAP packages in the theatre there is no resolution for that to be
perceptible.

**What would reopen this.** Not another dimension picked off the planner. A flown observation of
something red actually does that reads wrong in the air. That is evidence this analysis cannot
produce, and every attempt to derive it from the planner has now failed twice.

---

### Phase 0 RESULT, 2026-08-17 — the axis framing is dead

**Phase 0 ran and stopped the feature.** That is the outcome it existed to produce, and the card
below is kept unedited as the record of what was predicted.

Measured on the DM's own save — **Syria, Desert Trident, turn 4**, one of Starfire's campaigns
(the standard for judging engine behaviour; fork-authored campaigns are tuned to fork features and
are not representative):

| | |
|---|---|
| Contested fronts | **0** |
| Red offensive packages | 10 |
| Axes targeted | **2** — Ben Gurion 9, Tel Nof 1 |
| Target mix | 7 vehicle groups, 2 buildings, 1 SAM |

Baltic Fury, for contrast: 1 contested front, 3 axes, and a distribution frozen across turns.

**The precondition cannot be met on representative campaigns, and that is not a sampling problem.**
The standard campaigns do not give red several axes to choose between. Ninety per cent of red's
offensive effort sits on one base because that is where the targets are, not because red decided
anything.

So the question the card asks is wrong. Red is not failing to commit to an axis; **there is
effectively one axis.** "Continuity of intent across axes" is a feature with no room to exist, and
no threshold tuning rescues it.

**What this does NOT establish.** It does not say red is fine. It says the *axis* dimension is
empty. If red should vary at all, the candidate dimensions left are what it goes after (it opened
against vehicle groups, not the SAM belt), how hard it presses, and whether it reacts to being
hurt. None of those is scoped here, and none should be started without its own Phase 0.

**Two caveats on the numbers.** The Baltic Fury turn loop used `pass_turn(no_action=True)`, so
nothing changed between turns — those figures show red is *deterministic*, not that it persists.
And the Desert Trident figure is one turn's planned ATO, not a time series. Neither weakens the
verdict, because the verdict rests on the precondition, not on the latency.

The instrument is `tools/measure_red_axis_persistence.py`; it is kept, since any successor question
needs the same axis mapping.

---

### The fly card, pre-registered 2026-08-17

**Written before the feature exists, and not to be edited once Phase 0 has run.** The value of a
pre-registered test is entirely in being fixed in advance; a threshold revised after seeing the
result is not a test. If it turns out to be the wrong test, replace it with a dated successor and
say why — do not quietly retune it.

#### The claim being tested

Red commits to an axis across turns, and the player can tell which one by flying, without reading
a label.

#### The two ways this test can lie

1. **Pattern-matching.** Fly three missions after any change and you will find a story in it. A
   human reading intent into noise is the default outcome, not the exception.
2. **The baseline already concentrates.** `ObjectiveFinder.prioritized_points()` produces a
   similar ordering turn to turn when the map has not changed, so red may *already* hit the same
   axis repeatedly with no memory at all. "Red concentrated on one axis" therefore proves nothing
   on its own.

Both are handled by measuring the baseline first and by testing **persistence under pressure**
rather than concentration.

#### The discriminating manoeuvre

Concentration cannot separate commitment from stable priorities. Persistence after the player
changes the situation can:

> Reinforce the axis red is pushing until it is no longer the locally attractive target, then
> count how many turns red keeps coming anyway.

Current red rebuilds `TheaterState` from scratch every turn, so it should re-evaluate and switch at
the next re-plan. A red that commits should keep pushing for a while, then reconsider.

#### Definitions, fixed now

- **Red offensive package** — a package in `game.red.ato.packages` whose primary task is
  air-to-ground (`FlightType.is_air_to_ground`). Defensive tasks are excluded.
- **Axis** — the *blue* control point a package's target belongs to. Front-line targets map through
  the pair's blue CP; ground objects through their own control point. (There is no single
  `MissionTarget.control_point`; the mapping is per target type and must be written once, in the
  measurement script, not improvised per run.)
- **Primary axis of turn T** — the axis receiving the most red offensive packages that turn. A tie
  is recorded as a tie, never broken arbitrarily.
- **Switch latency L** — turns elapsed between the intervention and the first turn whose primary
  axis differs from the pre-intervention primary axis.

#### Phase 0 — baseline, before any code is written

Headless. No flying.

1. Pick a campaign with **at least three contested axes**. Record which.
2. Load a save. For 6 turns: `initialize_turn(events, for_red=True, for_blue=False)`, then record
   every red offensive package and its axis.
3. Compute the primary axis per turn, and the concentration on it.
4. At turn 3, apply the intervention: reinforce the current primary axis until it is clearly the
   least attractive target. Continue to turn 6. Record **L_baseline**.

**Predicted in advance: `L_baseline <= 1`.** Red re-plans from scratch, so it should switch almost
immediately.

**If `L_baseline >= 2`, this whole test is invalid** — it would mean current red already persists,
and the feature would have nothing to demonstrate. Stop and redesign the test rather than
proceeding.

**If concentration is already ~1.0 at baseline**, the campaign has effectively one axis and is
unsuitable. Pick another.

#### Phase 1 — after the feature

Same campaign, same save, same 6 turns, same intervention at turn 3, same script.

| Outcome | Verdict |
|---|---|
| `L <= 1` | **FAIL — does nothing.** Indistinguishable from baseline. |
| `2 <= L <= 4` | **PASS.** Red commits, then reconsiders. |
| `L >= 6`, or never switches | **FAIL — stubborn, and worse than baseline.** A red that cannot be pulled off an axis can be farmed: park your defence and fly everywhere else unopposed. |

The upper bound is not optional. A feature that only ever increases persistence has not been tested
until someone has checked it can still let go.

#### The legibility half — the only part that needs flying

This is the test §55 failed, and no amount of headless data substitutes for it.

After each of 6 flown missions, **before looking at any data or the F10 map**, write down which
axis you think red is pushing. Then compare against the computed primary axis.

- **Pass:** correct on 4 of 6 or better.
- **Fail:** 3 or fewer. Red may well be committing — but if it cannot be read from the cockpit it is
  a caption, which is exactly what was removed.

Guesses must be written before checking. A guess recalled afterwards is not evidence.

#### Fail signatures to watch for beyond the metric

1. **Red commits to an axis it cannot supply** — it keeps attacking through a corridor whose supply
   the player cut (§90 rung A). Commitment must not survive the ground truth that makes it pointless.
2. **Red stops defending elsewhere** to sustain the axis, leaving objectives entirely unopposed.
   Continuity of *offensive* intent must not drain the defensive posture.
3. **Blue's planner drifts too.** Red and blue share `TheaterCommander`; any change must be gated so
   blue's behaviour is byte-identical. Diff a blue ATO before and after on the same save.
4. **The save grows a field that cannot be loaded by an older build** — persisted intent is new
   state, and every other persisted addition in this engine went through `__setstate__` tolerance.

#### Cost

Phase 0 and Phase 1 are minutes each: 12 headless re-plans and a script. The legibility half is 6
flown missions and is the real expense — it should ride on a campaign already being played rather
than being run as a dedicated exercise.

**Run Phase 0 now, not later.** It needs no feature and it is the only part that can still
invalidate the design: if current red already persists, the premise is wrong and nothing should be
built.

#### Where this card lives when the feature lands

Here, until then. On landing it becomes a row in `docs/dev/414th-ingame-pass-checklist.md` with the
Phase 1 thresholds as its pass criterion and the list above as its fail signatures, and the
measurement script goes in `tools/`. It does **not** belong on the opportunistic WATCH card — it
needs a campaign arranged on purpose.

### The catch

- **This is the seam most likely to reproduce a removed feature.** Anything proposed here must be
  checked against `414th-red-intent-notes.md` and state plainly how it differs.
- Red and blue sharing a planner is a fairness property. A change that only red gets needs to be a
  change blue does not *need* (continuity of intent), not a change blue is denied (better tactics).
- Verification is the hard part. "Red felt like it had a plan" is not a fail signature. Any fly card
  here needs an observable: which axis its packages came from, over how many turns.

---

## 9. The thing that binds before any of this

91 features. The pass checklist was already carrying roughly 75 outstanding rows against 86
closed when this note was written, and seams 1 and 4 added six more (B65-B70). Re-read
`docs/dev/414th-ingame-pass-checklist.md` for the live count rather than trusting this line.

**Being worked in the background** by a separate agent as of 2026-08-17.

The constraint moved from "can we build it" to "can we prove it works" a while ago. Three
consequences for the seams still open:

1. **Seam 2 pays twice** — it retires existing one-offs, so it cuts code *and* cuts rows that
   would otherwise each need their own pass. Seam 1 had the same property and did not collect on
   it: the seven bespoke channels are still there, and folding them onto the new schema is where
   that saving actually lands.
2. **Seam 5 costs verification and almost nothing else.** It is low code risk and can only be
   judged by flying, which is exactly the budget already under strain.
3. **Seam 7 is the hardest thing here to verify**, because "red felt like it had a plan" is not a
   fail signature. Any card needs an observable: which axis its packages came from, over how many
   turns. Write that card before writing the feature.

---

## 10. What this note is not saying

- **Not "stop building features."** The mission builder is good. The content features work.
- **Not "rewrite the engine."** Every seam is reachable step by step from where we already are.
  Three of them are just generalisations of code that already exists.
- **Not a priority order.** Seams 1 and 2 are cheapest and clear existing debt. Seam 4 rung A is
  the smallest edit with a visible effect. Seam 3 is the biggest change to how the campaign feels
  and the most expensive to prove. Those are costs, not a sequence.
- **Not a complaint about the front line.** It's thin, it's honest about being thin, and it has
  never broken. §5 lists what it can't express — not bugs.
- **Not an argument for any third-party dependency.** Nothing here needs software outside DCS.
  Our rule against mod dependencies for core behaviour applies the same way to analysis tools.
- **Not a case for restoring §55.** Seam 7 argues red needs *continuity*, and that whatever it
  decides has to be met in the air rather than read off a caption. §55's posture classifier and
  its ribbon are exactly the shape that was already tried and dropped.
- **Not a claim that 2,453 lines is too few.** A small campaign brain is not automatically a bad
  one. The ratio says where the investment went; it does not say the number should be bigger.
