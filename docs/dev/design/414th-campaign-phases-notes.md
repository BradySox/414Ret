# 414th — Campaign Phases (inferred + authored) — design notes

> **SUPERSEDED / REMOVED 2026-07-21** — the campaign-phases feature (§40) was removed from the fork (ROE mechanic drop). This note is kept as a historical record.

**Status:** **P0 + P1 LANDED** (2026-07-01, Vietnam campaign layer W3 / feature §40 —
`game/fourteenth/phases.py`, the §2.1 object + §3 Tier-0 classifier + §3.3 hysteresis +
§4 soft emphasis in `PlanNextAction` + §5 persistence + the kneeboard cover band and the
client campaign-status ribbon, gated by `campaign_phases` default ON; in-game pass =
checklist M3). **P2 + first P3 arcs LANDED** (Vietnam W4): the `phases:` YAML load,
`advance_when` conditions, the ROE `restricted_zones`/`locked_targets` payload + planner gate,
and the Rolling Thunder → Linebacker II arcs in the 4 Vietnam campaigns (checklist M4). Open:
objectives checklist, per-phase whitelist deltas, `front_line_stance`, the 3 wiki-campaign
arcs. This note is the
**spec of record** for the phase model, the inference classifier, and the planner/UI
hooks; implementation is staged (see *Rollout* at the end). Design decisions locked with
the user this session are marked **[DECIDED]**.

> **One-line vision:** every campaign — including the 63 base-Retribution campaigns that
> ship with nothing but a thin YAML header — knows what *phase* of the war it is in, the
> UI shows it, and the auto-planner biases its offensive intent to match. Our three
> hand-built campaigns get bespoke authored arcs on top of the same machinery.

---

## 1. The idea, and why it isn't a rewrite

The squadron's campaign wiki docs have always been divided into **phases**, broken down by
turn ("Phase 1, turns 1–4: roll back the IADS; Phase 2: interdiction; Phase 3: the push").
Today that structure is a *human narrative* laid over the wiki — the engine has no idea it
exists, so the auto-planner runs the same generic HTN every turn regardless of the intended
arc, and the player never sees "what phase am I in" anywhere in the UI.

This makes phases first-class: a thin **layer** that (a) is reflected in the UI and (b)
biases the planner. It is explicitly **not** a rewrite of the commander — the fork already
has the exact precedent in `VIETNAM_DOCTRINE` (`game/data/doctrine.py`): a profile that
reshapes both planning (`tasking_whitelist`, `strike_through_air_defense_threat`, Alpha
Strike sizing) *and* display (`task_display_names`: BARCAP→MiGCAP) as a display-and-gate
overlay that never mutates a persisted enum. A phase is the same shape, **time-sliced
instead of campaign-wide**.

**Mental model:**

> A **phase** is a doctrine-like profile plus a narrative, active for part of a campaign,
> resolved fresh each turn from live campaign state, that biases the planner's *offensive
> intent* while leaving reactive defense deterministic.

That last clause is the same boundary §17 (planner unpredictability) already draws: if a
raid is inbound you still defend, phase or not. Phases only shift what the campaign chooses
to *go do* with spare capacity.

---

## 2. Three authoring tiers, one object

The core model is a single `CampaignPhase`. What changes across tiers is **who supplies its
values** — the inference engine, the campaign YAML, or a hand-authored block — never the
code path.

| Tier | Who fills it in | Coverage | Effort |
|---|---|---|---|
| **0 — Inferred** | classifier reads live state each turn | **all 66 campaigns** | zero authoring |
| **1 — YAML-tuned** | campaign YAML tweaks names/thresholds/turn-pins | opt-in | a few lines |
| **2 — Authored arc** | hand-written phases + objectives + narrative | our 3 campaigns | full |

**[DECIDED] Tier 0 inference is the default for every campaign.** A campaign with no
`phases:` block still gets a real, responsive arc. Authoring only *overrides* the inference.

Inferred phases can only ever be *generic* (rollback → interdict → push is the universal
air-campaign shape); they cannot know "capture Hanoi to win" — that is Tier 2. But
generic-and-responsive beats nothing for 63 of 66 campaigns, and it degrades gracefully into
the authored version wherever we invest.

### 2.1 The `CampaignPhase` object

```
CampaignPhase:
  key                  # "rollback" | "interdiction" | "offensive" | authored key
  name                 # display: "Air Superiority", or authored "Alpha Strike"
  narrative            # 1–2 lines for the kneeboard cover (§30) + status band
  # --- transition (authored tiers only; Tier 0 uses the classifier) ---
  min_turn             # earliest this phase may begin (turn-anchored convenience)
  advance_when         # optional condition set; shared mechanism with the classifier
  # --- planner effect (all OPTIONAL, all layer OVER faction doctrine) ---
  emphasis             # {HTN root-method or task: weight delta}, soft reweight
  tasking_whitelist    # optional HARD gate delta (reuses the Vietnam field)
  front_line_stance    # optional posture nudge (defensive → aggressive)
  # --- display only ---
  objectives           # checklist strings for the status band; never gates planning
```

Phase *definitions* live on the frozen `Campaign` dataclass
(`game/campaignloader/campaign.py`), loaded from an optional YAML `phases:` block and
**re-derived at load** — so editing a campaign's phases never corrupts an existing save.
Only the *pointer* persists (see §5).

---

## 3. The inference classifier (Tier 0) — metrics & thresholds

This is the heart of the "works for undocumented campaigns" answer. Every base campaign's
`.miz` builds a full theater at load; the classifier reads state that **already exists** (no
new measurement plumbing — accessors confirmed 2026-07-01) and picks the phase each turn.

### 3.1 Signals (all pre-existing accessors)

| Signal | Accessor | Derived metric |
|---|---|---|
| **Enemy IADS strength** | enemy TGOs with `tgo.task in {GroupTask.LORAD, GroupTask.MERAD}` (the same set `degradeiads.py` targets), alive via `TheaterUnit.alive` | `iads_ratio` = alive enemy long+medium SAM **sites** ÷ **turn-0 baseline**. (Corrected by the engine re-run: banding by `IadsRole` can't work — `IadsRole.SAM` also swallows SHORAD and `IadsRole.EWR` swallows AAA/navy — so band by the TGO's `GroupTask` instead.) |
| **Enemy air threat** | `ThreatZones.for_faction(game, enemy)` (`.air_engagement`, `.airbases`) | `air_threat` = enemy fighter/CAP reach coverage (coarse: present / degraded / absent) |
| **Enemy air inventory** | `air_wing.iter_squadrons()` → `owned_aircraft` × `primary_task==CAP` | `enemy_fighters` count vs. turn-0 baseline |
| **Front momentum** | `FrontLine.position` (snapshot at turn 0 — **not persisted natively**) | `front_progress` = signed displacement of FLOT vs. turn-0 baseline |
| **Territory** | `control_points_for(Player.BLUE/RED)`; `Debriefing.base_captures` | `base_ratio` = blue CPs ÷ total; recent-capture flag |
| **Momentum** | `Debriefing.loss_counts()` / `game.last_sitrep` (last turn only) | `exchange` = friendly vs. enemy losses last turn (tie-break only) |

**Baselines.** There is no persisted initial front-line or IADS count, so the classifier
**snapshots them at turn 0** (`begin_turn_0()`, after `iads_network.initialize_network()`)
and stores them on `Game` (`game.phase_baseline`) for the ratio math. Baselines migrate for
old saves (default: re-snapshot at first load, or treat ratios as 1.0 until a baseline
exists).

### 3.2 Phase boundaries (v1 thresholds — refined by the pilot, see the pilot note)

**Absolute-SAM-floor gate (checked first — the pilot's key finding).** `iads_ratio` alone
can't open the campaign correctly: at turn 0 *every* campaign's ratio is `1.0`, yet a
zero-SAM Vietnam theater and a dense S-300 theater must not both open in Rollback. So before
the ratio checks: **if the turn-0 baseline of long+medium SAM sites is below
`ROLLBACK_SAM_FLOOR` (≈ 3), there is no meaningful Rollback phase — open the campaign in
Interdiction.** (Engine-corrected examples — the pilot's original "Khe Sanh 0 SAM" case was a
`--lite` artifact; the generator actually fills 4 SA-2/SA-3 batteries there, see the pilot-note
addendum. The genuine below-floor cases across all 66 are Shattered Dagger, Battle for No Man's
Land, Valley of Rotary, and Northern Guardian ⇒ they skip Rollback; Velvet Thunder sits exactly
at the floor with 3 SA-2 sites ⇒ keeps it — same permissive-air era, opposite arc, decided by
laydown.)

Then, evaluated in order; first match wins (with hysteresis, §3.3):

1. **Rollback / Air Superiority** — the default early phase *(only reachable if the SAM floor
   is met)*.
   *Enter/stay when* `iads_ratio ≥ 0.5` **or** `air_threat == present`.
   Intent: win the air, degrade the SAM belt.
2. **Interdiction** — air largely won, ground not yet moving.
   *Enter when* `iads_ratio < 0.5` **and** `air_threat != present` **and**
   `front_progress` ≈ static.
   Intent: choke reinforcement/logistics.
3. **Offensive / Push** — air won *and* the ground fight is live.
   *Enter when* `iads_ratio < 0.3` **and** (`front_progress` advancing **or** a recent
   friendly base capture).
   Intent: take ground.
4. **Consolidation** *(optional)* — enemy near collapse.
   *Enter when* `base_ratio ≥ 0.8`.

**IADS strength = long+medium SAM launcher count, not EWR.** The pilot found EWR counts are
wildly author-dependent (Black Sea placed 50; the other five placed 0, letting SAM radars do
EWR duty). So `iads_ratio` is computed over **long+medium launchers**; EWR is flavor only.

**Peer-fight guard.** When the sides are air-symmetric (pilot: Slava Ukraini, Ukraine vs
Russia), the Rollback→Interdiction transition gates on `air_threat_absent AND iads_down`, not
IADS alone — otherwise it advances while red air is still a real threat.

`exchange` (loss ratio) is a **tie-breaker only** — it nudges dwell/advance timing, it never
selects a phase on its own (too noisy turn-to-turn).

These thresholds were sanity-checked against six real laydowns (4 modern + 2 Vietnam, dense-
IADS↔no-IADS) — see [`414th-campaign-phases-pilot.md`](414th-campaign-phases-pilot.md). The
absolute-floor gate is now a **P1 requirement**, not optional.

### 3.3 Hysteresis (mandatory)

A live-metric classifier flaps. Two guards, both required:

- **Min-dwell:** once entered, a phase holds for ≥ `PHASE_MIN_DWELL_TURNS` (default 2)
  before any transition is considered. Rollback's dwell should **scale with L+M SAM density**
  (pilot: Anvil 21 / Noisy 25 SAM ⇒ long Rollback; Slava 7 ⇒ short), and overall pacing tracks
  the capturable (neutral) airfield pool.
- **Asymmetric thresholds:** advancing forward uses the thresholds above; *regressing* to an
  earlier phase requires the reverse condition to be met by a margin (e.g. IADS must climb
  back above `0.6`, not merely `0.5`, to fall from Interdiction back to Rollback — models a
  real IADS rebuild, not sensor noise).

Phases are **monotonic-forward by default**; regression is opt-in per campaign (an authored
flag), because most campaign narratives don't un-happen.

### 3.4 Legibility

Because base campaigns have no docs, the classifier's output must explain itself. The status
band and kneeboard show *why*: **"Interdiction — enemy IADS 22% · air threat low · front
static."** This doubles as a sanity check and makes the planner's shift feel earned. Nice
side effect: **this auto-generates the campaign documentation those 66 campaigns never had**
— previewable in the New Game wizard as the campaign's expected shape.

---

## 4. How the planner consumes a phase

Two levers, softest first. Both **compose with** faction doctrine — they never replace it.

1. **Soft emphasis (default).** Reweight the HTN root-method ordering
   (`game/commander/tasks/compound/nextaction.py`) and the objective/target priorities. This
   is the same layer §17 already reorders offensive-target selection through — a proven,
   contained insertion point, **not** new HTN methods. A phase's `emphasis` map dials the
   weight of methods that already exist:

   | Phase | Emphasize | De-emphasize |
   |---|---|---|
   | Rollback | `ProtectAirSpace`, `DegradeIads`, OCA, BARCAP/Sweep | deep strike, CAS |
   | Interdiction | `InterdictReinforcements`, `AttackAirInfrastructure`, BAI, SCAR/Armed Recon | — |
   | Offensive | `PlanFrontLineCas`, `CaptureBases`, aggressive front stance | deep strike |

2. **Hard whitelist delta (optional, authored).** Reuse the Vietnam `tasking_whitelist`
   mechanism to actually forbid a task class in a phase ("no strategic strike until
   Phase 2"). Read exactly where Vietnam reads it — `PackagePlanningTask.fulfill_mission`.

**Invariant:** reactive defense stays deterministic (the §17 boundary). Phases bias
*opportunistic/offensive* selection only.

**Ceiling (honest):** the HTN is fundamentally reactive. Phases add strategic *intent* on
top, but can't override a genuine threat response and can't make the planner do anything the
task library can't already do. They are a bias and a narrative, not a new commander.

---

## 5. Persistence & migration

- **Definitions** ride on the frozen `Campaign` (re-derived at load) — never pickled.
- **State** persisted on `Game`: `current_phase_key: Optional[str]`,
  `phase_entered_on_turn: Optional[int]`, and `phase_baseline` (turn-0 snapshots).
- **Migration:** `Game.__setstate__` `setdefault`s all three to `None`. Old saves compute a
  phase on next `initialize_turn()`; ratios treat a missing baseline as 1.0 (or re-snapshot)
  until one exists. No enum values change, so no `_missing_` entry is needed — following the
  §16/save-migration discipline in CLAUDE.md.

---

## 6. UI surfaces

Cheapest → richest; ship in that order.

1. **Kneeboard (highest fit, near-zero new surface).** The cover page (§30), SITREP band
   (§29), and Brief Sheet (§31) already exist. Add one `CAMPAIGN PHASE: Interdiction — choke
   the trail` line to the cover and a phase note in the SITREP. Ship first.
2. **Web client status band.** **Catch:** `GameJs` (`game/server/game/models.py`) does not
   currently send turn, date, *or* campaign name to the client at all. So step one is a small
   campaign-status payload; phase rides in on it. Then a slim ribbon above the Leaflet map:
   *"Phase 2 of 4 · Interdiction · Turn 6 · advances turn 10"* + progress bar + objectives
   checklist + the §3.4 "why" string.
3. **New Game wizard (PyQt).** On campaign select, show the (inferred or authored) phase arc
   so the player sees the intended shape before starting — the auto-generated documentation.

---

## 7. Batch draft of all 66 campaigns (feasibility)

The user asked how hard it would be to draft phase plans for *every* existing campaign. The
key: **the engine already loads all 66 `.miz` files into full theaters** (that's the
product), so "analyze all campaigns" = "drive the existing loader headless and dump the
laydown," not "hand-parse locked mission files." Three costs:

1. **Extraction — cheap, write-once.** A headless script over `Campaign` +
   `mizcampaignloader` dumps per-campaign laydown (theater, era/date, blue/red base counts,
   front geometry, IADS composition by role, squadron inventory) — reusing the §3.1
   accessors.
2. **Analysis + authoring — the real cost, but parallelizes.** 66 independent reasoning jobs
   (laydown + schema → drafted `phases:` block + narrative) — the textbook fan-out
   **workflow** shape.
3. **Verification — impossible without flying them.** So the output is **drafts**: plausible
   arcs from laydown + doctrine, strong Tier-1 seeds, refined only where it matters.

**Bonus:** drafting all 66 is also the **validation corpus for the §3.2 thresholds** — it
checks "IADS < 30% ⇒ Interdiction" against 66 real theaters at once.

**Approach [planned]:** pilot ~6 representative campaigns (spread across eras/theaters),
prove the extraction pipeline + judge draft quality, *then* green-light the full fan-out.

---

## 8. Rollout (staged)

- **P0 — plumbing (no behavior change):** ✅ LANDED (W3) — `CampaignPhase` model +
  `Game` phase state/baseline + `__setstate__` migration + expose turn/date/campaign/phase in
  `GameJs`. Kneeboard cover + status band light up. (The Campaign YAML `phases:` load moved
  to P2 with the rest of the authoring tiers — Tier 0 needs no YAML.)
- **P1 — inference + emphasis:** ✅ LANDED (W3) — the §3 classifier drives the §4 soft reweight
  for **all** campaigns. Generic arc, hysteresis, legibility string.
- **P2 — conditions, objectives, whitelists:** ✅ MOSTLY LANDED (Vietnam W4) — the campaign
  `phases:` YAML load, `advance_when` conditions (min_turn / blue_will_below / enemy_iads_below),
  and the ROE payload (`restricted_zones` + `locked_targets` target-release gates, read in
  `PackagePlanningTask.fulfill_mission`) are in via `game/fourteenth/phases.py` (`parse_phases`,
  `authored_arc_for`). Still open from P2: the objectives checklist (display), per-phase
  `tasking_whitelist` deltas, and `front_line_stance` nudges.
- **P3 — authored arcs:** ✅ FIRST FOUR LANDED (Vietnam W4) — Rolling Thunder → Bombing Halt →
  Linebacker → Linebacker II `phases:` blocks in the 4 Vietnam campaigns. Converting the
  squadron's three wiki campaign breakdowns (Red Tide et al.) is still open.
- **ROE zone shapes (Path A):** ✅ LANDED — `restricted_zones` are shape-typed, not circle-only:
  `shape: circle | box | corridor` (a rotatable rectangle for the "Nevada box"/Route-Package
  rectangles; a buffered-polyline lane for ingress routes/the Ho Chi Minh trail). One shapely
  `ResolvedZone.contains` gates both the AI planner and the will-penalty; the zones are painted
  into the generated `.miz`'s F10/ME map (`DrawingsGenerator.generate_restricted_zones`), so the
  cockpit map and the web map show identical geometry. A legacy `{center, radius_nm}` block still
  parses to a circle byte-identically. In-game pass: checklist **M7**.
- **ROE zone shapes (Path B — draw in the ME):** ✅ LANDED — a `restricted_zones` entry can be
  `{from_drawing: "<name>"}`, hanging the zone off a shape the author *drew* in the campaign
  `.miz`'s Mission Editor instead of typed coordinates. `game/fourteenth/zone_drawings.py`
  reads the loaded mission's drawings into named `DrawnZone`s (v1: Circle → circle, FreeFormPolygon
  → polygon; Rectangle/Oval/TextBox/unnamed skipped), `MizCampaignLoader.populate_theater` stashes
  them on `theater.zone_drawings`, and `_resolve_drawing_zone` builds the same `ResolvedZone`. DCS
  drawings round-trip cleanly (confirmed against `1968_Yankee_Station.miz` + a real write/reload
  probe). Rectangle/Oval reading is deferred pending an in-game convention check (the polygon tool
  covers box/corridor). In-game pass folded into checklist **M7**.
- **Free-fire zones (inverted ROE — the COIN kill boxes):** ✅ LANDED — a phase authoring
  `free_fire_zones` (same shape system as `restricted_zones`) flips the polarity: the whole map is
  weapons-hold for fixed strikes, cleared only inside the pockets (the OIR Blue-Kill-Box model —
  the Rampagers reference library is the doctrine source). Front-line forces/convoys are never
  gated; a restricted zone still carves a no-strike hole inside a pocket; violations = kills
  outside every pocket; the summary leads with a WEAPONS FREE row; pockets paint dashed **green**
  (F10/ME + web). Content: `coin_enduring_resolve.yaml` kill boxes grow 4→8→10 across the arc,
  every capture objective inside a box (KB FRONTENAC/HADRIAN/TARIN KOWT — an objective outside
  the boxes would make the campaign punish its own assault), Lashkar Gah never boxed. In-game
  pass: checklist **M8**. Future (from the Rampagers harvest): Hot/Cold box cycling, CGRS cell
  overlay, a CAS-stack/ROZ marker.
- **(parallel) Batch draft:** §7 pilot → full 66 fan-out.

---

## 9. Open decisions (carried)

None blocking P0. Tunables deferred to the pilot: the §3.2 thresholds, `PHASE_MIN_DWELL_TURNS`,
whether Consolidation ships in v1, and default monotonic-forward vs. regression per campaign.

## 10. Key files (when P0 starts)

- `game/campaignloader/campaign.py` — `phases:` field + loader
- `game/game.py` — phase state, `phase_baseline`, `begin_turn_0` snapshot, `initialize_turn`
  compute, `__setstate__` migration
- `game/data/doctrine.py` — reference for the profile/override pattern (do not fold phases
  *into* Doctrine; compose)
- `game/commander/tasks/compound/nextaction.py` + the §17 target-order path — emphasis hook
- `game/server/game/models.py` + `routes.py` — campaign-status payload
- `game/missiongenerator/kneeboard.py` — cover/SITREP phase line
- `client/src/components/` — status band
- `qt_ui/windows/newgame/` — wizard phase preview
- `tests/` — classifier threshold + phase-migration tests (`test_vietnam_doctrine.py` is the
  precedent for profile tests)
