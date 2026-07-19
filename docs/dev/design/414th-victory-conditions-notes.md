# Custom Victory Conditions (§75)

**Status: LANDED (V1 authored block + V2 generic knobs + ribbon/SITREP surfacing).**
In-app pass = checklist B29.

## Where this came from

A 2026-07-19 Discord thread (Ramius007 + Starfire, with the DM). The stock win
condition is literally "the enemy owns zero control points"
(`Game.check_win_loss`: `not theater.enemy_points()`), which forces every
campaign — including a limited war like "liberate Abkhazia" or a maritime
pressure campaign — into a total ground conquest ("the 1-Huey conquest of
entire Georgia"). The asks, verbatim in spirit:

- **Ramius:** victory control points ("hold these to win") and a domination
  threshold ("own a large % of enemy CPs"); maybe a losses threshold where the
  *enemy* wins (he immediately doubted that one himself).
- **Starfire** (has an upstream FR for this): (1) destroy all designated
  high-value targets → win; (2) enemy strength below a selectable % (air, or
  air + ground) → win; (3) enemy can no longer field air because every enemy
  airfield is captured or disabled → win. "The intent really is to get away
  from the capture-every-control-point gameplay."

The DM had been prototyping a much deeper version and was about to scrap it —
the depth (will meters, authored arcs) already shipped as the Vietnam layer
(W1–W6) and is NOT what the community asked for. This feature is the **shallow
layer**: simple, legible, checkable end-of-war conditions, built from
primitives the fork already owns.

## Shape

One new module, `game/fourteenth/victory.py`, on the exact patterns of its
siblings:

- **Authored tier (V1):** a campaign YAML `victory:` block (sibling of
  `will:` / `phases:`), parsed by `parse_victory` and re-derived from the
  campaign YAML by name at load — the phases-S5 **rederive-never-pickle** rule,
  module cache `_PROFILE_CACHE`, any failure degrades to "no profile" with a
  log, never a crash.
- **Generic tier (V2):** two opt-in Settings knobs usable on ANY campaign with
  zero authoring — `alternate_victory_domination` (own ≥ N% of the non-neutral
  bases → win) and `alternate_victory_attrition` (enemy air below N% of its
  turn-0 strength → win). Both default 0 = off. They synthesize the same
  condition objects the authored tier uses and stack with an authored block
  (any win path ends the war).
- **Evaluation site:** `victory_verdict(game)` called from
  `Game.check_win_loss` **between** the W2 negotiation branch and the stock
  territory checks. Loss precedence within the module (the W2 rule: a
  simultaneous collapse is never a cheap win); the negotiation ending still
  outranks both; the capture-everything default is untouched and remains the
  fallback for every campaign with nothing configured.

### The YAML block

```yaml
victory:
  description: Liberate Abkhazia          # optional, shown in the UI header
  win_when:
    - label: Liberate the coast           # optional display override
      capture_cps: [Sukhumi-Babushara, Gudauta]
    - enemy_air_below: 0.10
      min_turn: 4                         # compound: AND within one entry
  lose_when:
    - lose_cps: [Kutaisi]
```

**Semantics — deliberately different from `PhaseCondition`:** a
`PhaseCondition` is an escalation trigger, so ANY satisfied field advances the
arc. A victory entry is a *requirement*, so **every field set on one entry
must hold** (AND within the entry) and the `win_when` / `lose_when` **lists
are OR** (any fully-met entry ends the war). This is what makes `min_turn`
usable as a guard ("not before turn 4") instead of nonsense ("win at turn 4
regardless"). The divergence is documented on both dataclasses.

### Condition vocabulary (all evaluated at ground truth, `viewer=None`)

| Field | Meaning | Machinery |
| --- | --- | --- |
| `capture_cps: [names]` | ALL named CPs blue-owned | CP `captured` (the `PhaseCondition.capture_cp` check, pluralized) |
| `lose_cps: [names]` | ANY named CP red-owned | same, inverted — the `lose_when` staple |
| `territory_above: 0.8` | blue owns ≥ this fraction of non-neutral CPs | the phases `_base_counts` math |
| `territory_below: 0.2` | blue owns ≤ this fraction | same — the `lose_when` mirror |
| `destroy_targets: [names]` | ALL named TGOs fully dead | TGO name match (case-insensitive), `not any(unit.alive)` — statics/buildings are `TheaterUnit`s so building targets work |
| `destroy_categories: [comms, commandcenter]` | ALL red TGOs of these categories dead | `tgo.category` — the class-based decapitation win, zero naming needed |
| `enemy_air_below: 0.10` | red owned airframes < this fraction of turn-0 | `VictoryBaseline` (the `PhaseBaseline` lazy-snapshot pattern), counting `squadron.owned_aircraft` across the red air wing — ALL squadrons, not just fighters (Starfire asked for force strength, not the phases classifier's air-superiority slice) |
| `enemy_ground_below: 0.15` | red front-line ground < this fraction of turn-0 | `Base.total_armor` summed over red CPs (the force `plan_groundwar` fields) |
| `friendly_air_below: 0.3` | blue air < this fraction of turn-0 | the `lose_when` mirror of the above (Ramius's losses threshold, expressed as strength — not a raw kill counter) |
| `enemy_air_denied: true` | NO red CP can currently field aircraft | `runway_is_operational()` over red CPs: airfields (cratered = denied until repaired), carriers (sunk = denied), FOBs (helipads count — red helos are still air power) |
| `min_turn: N` | guard: no earlier than turn N | plain turn check (ANDed like everything else in the entry) |

**Honesty rules baked in:**

- **Off-map spawns always count as "can field air"** — a red `OffMapSpawn` can
  never be captured, so `enemy_air_denied` is unreachable on those campaigns
  by construction. That is correct (red genuinely can still fly); the author
  just shouldn't use that condition there. Documented, not special-cased.
- **The baseline is snapshotted lazily on first evaluation** and persisted on
  the game (`game.victory_baseline`, getattr-guarded). For a NEW game that is
  turn 0. For a pre-feature save it is "now", the same accepted migration the
  phases baseline documents. Because the baseline snapshots unconditionally
  (whenever any victory config is active OR could become active — i.e. every
  `check_win_loss`), flipping a knob on at turn 20 still measures against the
  earliest state this build ever saw, not turn 20.
- **Ratio conditions with an empty baseline never fire** (no red air at turn 0
  ⇒ `enemy_air_below` is meaningless ⇒ False), the `enemy_iads_below` rule.
- **Evaluation is turn-boundary only** — `check_win_loss` call sites are all
  post-`pass_turn`/debrief-close. A cratered runway that gets repaired next
  turn only produces a win if the check ran while it was down; that is the
  same transient-win semantics runway state already gives the territory check
  (a sunk-carrier side loses even though wrecks don't respawn), accepted.
- **No planner coupling.** The AI does not know the victory conditions exist
  (the §3 `viewer=None` discipline applies to fog, and the §17 boundary to
  planning: an authored campaign that wants the AI to *pursue* the objectives
  authors a `phases:` emphasis alongside — the two blocks compose). Difficulty
  stays a budget/income knob, per Ramius.

### Knob → condition synthesis

- `alternate_victory_domination = 80` ⇒ `VictoryCondition(territory_above=0.8)`
  appended to the win list, labeled "Domination: hold 80% of the bases".
  Footgun documented in the setting detail: pick a threshold above your
  starting share or the campaign ends on the first check (the live ribbon
  readout shows the current share, so a bad pick is visible immediately).
- `alternate_victory_attrition = 10` ⇒ `VictoryCondition(enemy_air_below=0.10)`,
  labeled "Attrition: enemy air below 10% of start".

Both live in Campaign Management → a new "Victory conditions" section, default
0 (off), so every existing save and campaign is byte-identical until opted in.

### Endings

A met win entry ⇒ `TurnState.WIN`; a met lose entry ⇒ `TurnState.LOSS` (loss
checked first). The met condition's label is announced via `game.message`
("Victory condition met: …" / "Defeat condition met: …") on the crossing turn
— the W2 exhaustion-banner pattern — so the generic Victory!/Defeat! dialog
always has a visible "why" beside it in the events feed. No custom dialog
copy in v1 (the will profile owns era-framed endings; an author who wants
bespoke ending prose uses a `will:` profile — the two systems deliberately
don't overlap).

## Surfacing (the "having effect" half)

Conditions nobody can see are conditions that don't exist:

- **Ribbon chip + expander block:** `CampaignStatusJs` gains
  `victory: list[VictoryConditionJs {text, met, defeat}]` (+
  `victory_description`), built by `victory_overview(game)` — one line per
  entry, prose with live values in the `_describe_condition` style ("Hold
  Sukhumi-Babushara and Gudauta (1/2 held)", "Enemy air force below 10% of
  start (now 62%)"). The bar shows a `VICTORY` chip whenever conditions exist
  (its own toggle, so it works even with `campaign_phases` off); the expander
  panel renders "Victory — any one of these ends the war:" + "Defeat if:"
  with the phase-objectives tick styling.
- **SITREP:** `Sitrep.victory_lines` (getattr-guarded like every later-added
  field) carries the same prose, capped at 4 lines, rendered by
  `kneeboard_lines()` — so the kneeboard band, the web LAST TURN panel, and
  the Qt debrief box all pick it up for free (§29 parity).

## Deliberately NOT in v1

- **Raw loss-count defeat** ("blue loses 50 airframes → loss"): covered
  properly by a minimal `will:` profile (losses priced into a meter with an
  authored ending); a raw counter is noisier and gameable. `friendly_air_below`
  covers the strength-based version.
- **Sustained-for-N-turns qualifiers** on transient conditions (air denial):
  add if a flown campaign shows cheap transient wins.
- **Per-campaign ending prose/cinematics:** the will profile owns that.
- **Planner pursuit of victory objectives:** compose with `phases:` emphasis.
- **Preseeds:** none. No shipped campaign changes behavior; the PG
  limited-war campaigns (Starfire's) are the natural first authors once this
  is upstream or he adopts the fork's build.

## Upstream carve

Prime candidate (a named community member has an FR for it; zero fork
couplings in the core): the carve is `victory.py` minus the SITREP/ribbon
integration + the `check_win_loss` branch + the two settings. The fork-side
`phases`/`will` interplay stays here. Carve after the in-app pass, the
§63/§65 pattern (fork PR first, upstream draft second).

## Files

- `game/fourteenth/victory.py` — the whole engine (conditions, parse, cache,
  baseline, verdict, overview).
- `game/game.py` — the `check_win_loss` branch.
- `game/settings/settings.py` — the two knobs + the "Victory conditions"
  section.
- `game/sitrep.py` + `game/sim/missionresultsprocessor.py` — the SITREP lines.
- `game/server/game/models.py` + `client/src/components/campaignstatus/` —
  the ribbon chip + expander block.
- `tests/fourteenth/test_victory.py` — parse/evaluation/verdict/overview.
