# Retribution — the long view

**Written 2026-08-17.** A plain read of how the engine actually works, and the six weak spots
that follow from it.

| Seam | Short version | Status |
|---|---|---|
| **1 — what the mission tells the campaign** | When you land, the campaign only learns who died | **BUILT 2026-08-17** — features doc §91, pass row B70 |
| **2 — how the game tracks what you know** | Built five separate times, five separate ways | **ACCEPTED — not started** |
| 3 — the map graph | Roads route traffic but can't be cut | Analysis only — but see seam 4 rung A |
| **4 — the front line** | One number divided by another | **BUILT 2026-08-17** — all five rungs; features doc §90, pass rows B65–B69 |
| 5 — time between turns | A turn is a jump, not a sample | Analysis only |
| 6 — the squadron layer | Already scoped in its own note, not built | See that note |

**What the build changed about this note.** Two claims below were wrong and are corrected in
place: `Base.strength` is a float in `[0.0, 1.0]`, not a unit count (§5), and the §26
capability weighting in `game/sim/combat/capability.py` is **air-to-air only** — it weights
flights, not ground units, so rung C could not reuse it and uses `total_armor_value` instead.

Seam 4 rung A also turned out to be seam 3's edit at one-tenth the size, as predicted: the
supply gate is the first thing in the codebase that makes cutting a route cost something.
Seam 3 proper — per-link capacity and damage state — is still unbuilt.

**Re-measure before quoting any number here.** Everything below was measured on 2026-08-17 and
will drift. The `file:line` references are how you check.

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

## 2. Seam 1 — what the mission tells the campaign · **ACCEPTED**

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

### The five

recon fog (§3) · recon capture (§12) · COMINT (§70) · C-130 ISR (§2) · decoy zones (§79) —
plus BDA damage lag.

All of them are the same idea underneath: **everything the player sees came from somewhere, at
some time, and might be wrong.** Source, age, confidence.

### The evidence

There are three separate yes/no switches — `alive_for`, `known_for`, `hidden_on_player_map` —
each with its own rule about who's looking. The overview toggle has to reach in and override all
three by hand (`game/theater/fogofwar.py`). Every new intel feature adds a fourth, a fifth.

No design note in `docs/dev/design/` describes the shared idea. Nobody has claimed this.

### Why it's worth the effort

The viewer-aware layer is the most original thing this fork has built compared to upstream. It's
also the only original thing that's unfinished — the shared part that would make the *next*
intel feature cheap doesn't exist, so every one of them pays full price.

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

## 5. Seam 4 — the front line · **ACCEPTED**

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

## 6. Seam 5 — time between turns · analysis only

**The problem in one line:** a turn is a jump, not a sample of an ongoing war.

The continuous clock (§47) and the living-battlespace pre-roll (§89) are steps one and two.
§89 already proved the idea reads well in the cockpit — earlier packages already airborne,
follow-on waves launching behind you.

What's left is the same idea at campaign scale: red doing things between turns that you can
*see* evidence of, and your sortie being one of several that turn rather than being the turn.

**Low code risk, high testing cost** — this can only be judged by flying, and §89's own five
slices already owe five passes.

---

## 7. Seam 6 — the squadron layer · already scoped elsewhere

Not news. `414th-coop-persistent-campaign-notes.md` scoped this on 2026-07-08 and it hasn't been
built: no human owns a pilot, no persistent frag board, no record that follows a person across
turns.

Listed here only so the set is complete. That note's decisions stand; nothing here revisits them.

---

## 8. The thing that binds before any of this

89 features. **86 verified · 49 untested · 23 partial · 3 regressed** — 75 rows outstanding
against 86 closed (`docs/dev/414th-ingame-pass-checklist.md`).

**Being worked in the background** by a separate agent as of 2026-08-17.

The constraint moved from "can we build it" to "can we prove it works" a while ago. Two
consequences for the accepted seams:

1. **Seams 1 and 2 pay twice** — they retire existing one-offs, so they cut code *and* cut rows
   that would otherwise each need their own pass.
2. **Seam 4's rungs A and B change balance everywhere**, so each needs a fly-card written
   *before* the change, not after.

The exception is **seam 4 rung A**: one line, and it can be judged on a single turn's front-line
movement instead of a series.

---

## 9. What this note is not saying

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
