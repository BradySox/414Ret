# 414th War Economy & Munitions Availability — design notes

**Status:** **§53 P0 LANDED 2026-07-08** (code + tests, Black/mypy/pytest clean); P1–P4,
§54, and §55 (red intent) to follow. Core decisions locked (below).
Two coupled features: **§53 War Economy** (the ground-supply loop) + **§54 Munitions
Availability** (the air axis riding the same ledger). This note is the source of truth
for the build; register the §N entries in `game/fourteenth/features.py` (and the
features-doc / README / CLAUDE / checklist) only as each phase *lands* — the registry
test fails CI on a dangling `settings_fields` reference, so the settings must exist first.

---

## Decisions locked (2026-07-08)

**§53 ground supply:**
1. **Accumulating stockpile** per base (not a per-turn flow) — reserves build up; a
   sustained blockade *starves over several turns*.
2. **Full bite from the outset** — supply gates the free strength recovery **and** the
   deployable-unit cap **and** the combat `delta`. Not a soft recovery-only start.
3. **Symmetric** — both coalitions; red interdicting *your* supply is half the point.

**§54 munitions:**
- **Curated-scarce taxonomy** — track stock only for the munitions worth running out of
  (PGM/GPS, standoff, ARM, long-range A2A): tag ~40–60 weapons into a few scarce families;
  everything else (dumb bombs, rockets, guns, short-range A2A, fuel tanks) stays infinite.
- **Consumable counts**, **debited at loadout** (took 4 JDAMs → base is 4 lighter; no
  dependence on flaky DCS expenditure data), **produced/transported/stored on the §53
  ledger**, **auto-swap to a stocked fallback + grey-out in the UI** on empty (guide the
  player, don't hard-block mid-plan).

---

## The problem (why this exists)

Stock Retribution's economy is **one scalar** (`Coalition.budget`, [game/coalition.py:43](../../../game/coalition.py))
fed by a **flat cash trickle**: each alive `REWARDS` building pays a fixed sum
([game/config.py:6](../../../game/config.py) — factory 2.5, fuel/ammo 2, oil 10…) plus
`cp.income_per_turn`. Nothing you bomb *traceably* changes what the enemy can field —
interdiction is a mission type, not a strategy, and "why am I striking this factory" has no
legible answer beyond "slightly less enemy cash next turn."

Worse, **the front is decoupled from materiel.** The FLOT position is a pure `strength`
ratio ([FrontLine._blue_route_progress](../../../game/theater/frontline.py:198)), and
`strength` moves *only* via casualty-driven `affect_strength(±delta)` in combat
([missionresultsprocessor.py:647-656](../../../game/sim/missionresultsprocessor.py); delta ∈
{0.1 MINOR, 0.3 DEFEAT, 0.5 STRONG}) plus a flat **`+0.2` recovery every turn**
([game.py:515](../../../game/game.py), `PLAYER_BASE_STRENGTH_RECOVERY` at
[game.py:83](../../../game/game.py)). Armor *counts* never touch position directly. **This is
the trap:** throttling production alone does nothing visible — a supply loop must bite on the
`strength` path, not just on unit counts.

**Goal:** a legible produce → transport → store → consume loop where striking the enemy's
production/transport/storage traceably degrades what they field and how hard they fight, and
the debrief says so: *"your bridge strike cut 40% of 2nd Corps' resupply."*

---

## Why it's tractable — the plumbing already exists

- **One income chokepoint to tap:** [`Income`](../../../game/income.py:25) converts TGO/CP
  state → a resource; `.total` ([income.py:52](../../../game/income.py)) is banked in
  [`Coalition.end_turn`](../../../game/coalition.py:234) as
  `self.budget += apply_commitment_ceiling(self.game, self.player, income)`. That
  `apply_commitment_ceiling` wrapper is the **exact precedent** for coupling a resource to a
  multiplier — mirror it.
- **Dead plumbing waiting for a consumer:** [`active_fuel_depots_count`](../../../game/theater/controlpoint.py:1258)
  / `total_fuel_depots_count` are defined and have **zero consumers** — a pre-built hook for
  the fuel/readiness axis (P3).
- **A cap formula that already models "storage → deployable strength":**
  [`front_line_capacity_with`](../../../game/theater/controlpoint.py:1209) =
  `min(perf_max, FREE(15) + ammo_depots × 12)` (constants at
  [controlpoint.py:107-108](../../../game/theater/controlpoint.py)). That's the shape a
  consumed stockpile factor slots into.
- **Transport rails:** the `TransitNetwork` + [`transfers.py`](../../../game/transfers.py)
  convoy machinery the fork already extended (§35 interdiction, §50 ambient convoys).
- **The `finish_turn` hook pattern:** [game.py:439-500](../../../game/game.py) is where
  `war_economy.py` attaches, exactly like `vietnam_convoy` / `ambient_convoys` / `coin`.
- **The whole shape has a precedent:** `political_will.py` + `commitment_ceiling.py` —
  observe-only first, recompute-don't-pickle, getattr-guarded state, gated default-OFF /
  campaign-preseeded-ON.

---

## §53 — the ground supply loop

### Model: accumulating per-base stockpile
`Base.supply: float` (a stock, 0..cap) on each control point's `Base`
([base.py:8](../../../game/theater/base.py), the object at
[controlpoint.py:416](../../../game/theater/controlpoint.py)). Each turn:
**produce → transport → store (accumulate/decay) → consume (bite).**

### The three stages + seams
1. **Produce** — factories (+ oil/derrick as raw feed) emit a *supply rate* banked at the
   producing CP. Today the factory is a boolean recruit-gate
   ([`has_factory`](../../../game/theater/controlpoint.py:627)) + a flat 2.5 cash whose own
   TODO ([config.py:12](../../../game/config.py)) says it shouldn't pay cash once it generates
   units — we resolve that here. Kill the factory → the rate stops.
2. **Transport** — supply flows producer→front each turn along the `TransitNetwork`; a cut /
   interdicted link (bridge down, convoy killed, contested route) throttles the delivered
   fraction. This is where §35/§50 get their point.
3. **Consume / bite** — a front-line CP's effectiveness is gated by its accumulated supply
   (below).

### The bite (solving the decoupling trap) — full, per decision #2
Supply must touch the `strength` path. Three hooks, all in v1:
- **(a) Scale the free recovery** — `+0.2 × supply_factor` at
  [game.py:515](../../../game/game.py). A starved front *stops healing between fights.*
  One-line, legible, symmetric.
- **(b) Scale the deployable cap** — fold a supply factor into
  [`front_line_capacity_with`](../../../game/theater/controlpoint.py:1209) so a dry front
  fields fewer units.
- **(c) Scale the combat `delta`** — a starved attacker wins less ground per victory
  ([missionresultsprocessor.py:647-656](../../../game/sim/missionresultsprocessor.py)). Most
  aggressive; keep the multiplier gentle and clamp so a starved side never *gains* ground
  from a lost fight.

`supply_factor` = a clamped ramp of `Base.supply / demand` (define `demand` from the CP's
deployed frontline unit count so a bigger front needs more supply to stay "full").

### Data model + save-safety
- `Base.supply: float` — the **one** pickled addition (Base is pickled with its CP). Add a
  `Base.__setstate__` default `0.0`/full so old saves load (the pattern
  `Loadout.__setstate__` / `Weapon.__setstate__` use).
- **`game/fourteenth/war_economy.py`** — a `SupplyLedger`, **recomputed each turn** from live
  state (production rate per producer, delivered fraction per link, per-base stock delta);
  nothing pickled beyond the `Base.supply` scalar, mirroring how `phases.py` re-derives from a
  couple of latched fields. Hooked from `finish_turn` after the convoy passes.

### Phasing (each independently shippable)
- **P0 — Ledger + production + observe-only. ✅ LANDED 2026-07-08.** Shipped:
  `Base.supply` (+ `__setstate__` default), `game/fourteenth/war_economy.py` (the ledger:
  `frontline_demand`/`stockpile_capacity`/`production_rate`, a one-time `_seed_supply` to
  capacity, and `advance_war_economy` hooked in `finish_turn` — seed + accrue production
  capped, no bite), the `war_economy` setting (Campaign Management → *War economy*, default
  OFF), Red Tide preseed, `game.war_economy_seeded` latch, and `tests/fourteenth/test_war_economy.py`
  (9 tests). **Observe-only surface = a per-turn `game.message`** ("BLUE logistics: producing
  +X supply/turn; front supply Y%") — the SITREP-band integration is deferred to when the bite
  makes it real news (P2). Both public accessors below ship in P0. **No combat bite yet** —
  instrument first, fly it, read the meter (the will-economy W1 precedent).
- **P1 — Transport + consumption. ✅ LANDED 2026-07-08.** Supply now *flows*: producers
  accrue output (capped), then each active-front CP consumes a turn's `frontline_demand` from
  its own stock and refills toward capacity from its **connected producers**
  (`_external_supply_sources` via `ControlPoint.transitive_connected_friendly_destinations`),
  neediest front first, drawing those sources' stockpiles down. A front cut off from
  production (route severed / rear base lost) can't refill and drains — the interdiction loop,
  using existing connectivity accessors (no transit-network coupling). `stockpile_capacity`
  now also scales with `production_rate` so a rear factory can hold what it makes. **Still no
  FLOT effect** — supply levels moving is material only; the combat bite is P2. The per-turn
  message now reports produced / moved-forward / consumed / % supplied / fronts-short. Tests
  extended (transport refills a connected front and drains its producer; an isolated front
  drains). *Deferred refinements:* hop-distance decay on delivery, and coupling the throttle to
  actual §35/§50 convoy kills on the route (P1 uses territorial connectivity as the throttle).
- **P2 — The bite** (a)+(b)+(c). The FLOT responds to logistics. Symmetric.
- **P3 — Fuel/readiness axis (optional).** Wire the dead `active_fuel_depots_count` to sortie
  generation — bomb fuel → enemy flies fewer packages.
- **P4 — Full legibility.** Client map supply-flow overlay, base-card stock readout, the full
  "why" chain in the debrief.

### Gating + testbed
- Setting `war_economy` (Campaign Management), **default OFF**, kill-switch pattern.
- **Testbed = Red Tide** — it already ships the economy build (3 factories + 3 ammo depots +
  advanced IADS + a destroyable red C2/logistics net). Preseed `war_economy: true`.
- **Composes with the will economy:** supply (*can I fight?*) and will (*do I want to?*) are
  orthogonal, stacking axes — a starved *and* demoralized army is doubly weak.
  `commitment_ceiling` couples will→budget; this couples supply→effectiveness; same wrapper
  pattern.

---

## §54 — munitions availability (the air axis)

The most **legible** axis: it hits the player directly in the loadout screen. Grey-out the
JDAM and the pilot understands the depot they let get bombed is why they're carrying dumb
bombs today. Same produce→transport→store→consume loop as §53 — the "consume" is the player
loading bombs, the "bite" is the greyed-out dropdown.

### It rides the date gate (near-identical plumbing to `restrict_weapons_by_date`)
- **UI (cosmetic):** [`QPylonEditor.__init__`](../../../qt_ui/windows/mission/flight/payload/QPylonEditor.py:34)
  builds the per-pylon dropdown from `pylon.available_on(date, faction)`; intersect that with
  the base's stock → grey-out/remove unstocked weapons. It already holds `self.flight` +
  `self.game`, so `flight.departure.base` is reachable.
- **Generator (authoritative):** [`setup_payload`](../../../game/missiongenerator/aircraft/flightgroupconfigurator.py:415)
  runs `Loadout.degrade_for_date` at `.miz` build. Add a sibling `Loadout.degrade_for_stock(base)`
  that reuses the **already-built** `_fallback_for` + `Weapon.fallbacks` chain
  ([loadouts.py:103](../../../game/ato/loadouts.py)) to swap an unstocked store down to a
  stocked fallback (JDAM → dumb bomb), else drop the pylon. Enforcement **must** be
  generator-side — the dropdown is bypassable via custom/saved payloads.

### The curated-scarce taxonomy (decision: option 1)
`WeaponType` has only 7 members and **~248 of 301 weapon groups are `UNKNOWN`**
([game/data/weapons.py:215](../../../game/data/weapons.py)) — the §46 gap. Rather than
backfill all 301 YAMLs, add a `scarce_family` tag to only the **~40–60 weapons worth running
out of** (PGM/GPS bombs, standoff, ARM, long-range A2A). Everything untagged is infinite.
- Store the tag in `resources/weapons/*.yaml` (a new optional field, read in
  `WeaponGroup._each_weapon_group`), exposed as `WeaponGroup.scarce_family`.
- Stock is keyed by family, not by CLSID (one weapon = many CLSIDs) and not by `WeaponGroup`
  (301 SKUs is too granular).
- **Expandable:** more tags later; if we ever want full coverage it becomes the §46 fix too.

### Consumable, debit-at-loadout, auto-swap
- `Base.munitions: dict[str, int]` (family → count) on [base.py](../../../game/theater/base.py),
  `__setstate__` default `{}`; produced/transported/stored on the §53 ledger.
- **Debit at loadout**, at generation, in/near `setup_payload` — count each scarce store the
  flight carries and decrement the base. Robust (no DCS expenditure data needed).
- **On empty:** generator auto-swaps to a stocked fallback via `degrade_for_stock`; UI greys
  out the item. Guide, don't block.

### Phasing
- **M0** — the taxonomy: tag the ~40–60 scarce weapons; expose `WeaponGroup.scarce_family`.
- **M1** — `Base.munitions` stock, fed by the §53 ledger, debited at loadout.
- **M2** — the gate: UI grey-out ([QPylonEditor.py:34](../../../qt_ui/windows/mission/flight/payload/QPylonEditor.py))
  + generator `degrade_for_stock` ([setup_payload](../../../game/missiongenerator/aircraft/flightgroupconfigurator.py:415)).
- **M3** — legibility: base-card stock readout, *"Kandahar is Winchester on PGMs"* on the
  kneeboard/SITREP.
- Setting `restrict_weapons_by_stock` (mirrors `restrict_weapons_by_date`), default OFF.

### Gotchas (from the investigation)
- **Fuel tanks are `UNKNOWN` and added *after* the gate** ([`add_range_fuel_tanks`](../../../game/fourteenth/range_fuel.py)
  runs post-degrade at [setup_payload:433](../../../game/missiongenerator/aircraft/flightgroupconfigurator.py)) —
  exempt them from stock (matches §46's conservative contract).
- **Custom/saved loadouts:** `degrade_for_date`'s substitution loop already applies to
  `is_custom` ([loadouts.py:163-185](../../../game/ato/loadouts.py); only the LGB step is
  `not is_custom`-gated). A stock gate on the same path will silently swap a player's
  hand-picked, now-unstocked store — *desired for enforcement, surprising for players*; call
  it out in the UI. Saved `.lua` payloads reintroduce arbitrary CLSIDs and must be gated at
  generation too.
- **§43 per-airframe defaults** persist fuel + properties **only, not weapons**
  ([flight_defaults.py](../../../game/fourteenth/flight_defaults.py)) — no direct clash; but a
  default *preset* can select unstocked munitions, and since presets aren't `is_custom` the
  generator degrade catches them.
- **AI vs player:** `setup_payload` runs per member, so a generator-side gate covers both
  naturally.

---

## Shared architecture (the ledger)

**The §55 interface is live as of P0 (coordination resolved).** `war_economy.py` exposes two
pure read accessors, module-level, no side effects: **`supply_factor(cp)`** (per-CP readiness
`clamp(Base.supply / frontline_demand, 0, 1)`, the input to the §53 P2 bite) and
**`coalition_supply_health(game, coalition)`** (the mean over active-front CPs that §55
red-intent P4 consumes). No shim is needed — §55 imports `coalition_supply_health` lazily and
degrades to `None` when `war_economy` is off, exactly as its design note specifies.

One module, `game/fourteenth/war_economy.py`, owns both axes:
- Runs from `finish_turn` ([game.py:439-500](../../../game/game.py)) after the convoy passes,
  before front-position update.
- Recompute-don't-pickle: the only pickled state is `Base.supply` (float) + `Base.munitions`
  (dict), both `__setstate__`-defaulted.
- Getattr-guarded reads everywhere for save tolerance.
- Both settings (`war_economy`, `restrict_weapons_by_stock`) default OFF; Red Tide preseeds
  both ON.

---

## Registration / doc-sync plan (as each phase lands)

Registry + docs are CI-coupled to real settings, so they land *with the code*, not now:
1. `game/fourteenth/features.py` — add `Feature("war_economy", …, 53, settings_fields=("war_economy",))`
   and `Feature("munitions_availability", …, 54, settings_fields=("restrict_weapons_by_stock",))`
   once the settings exist; regenerate the catalog (`python -m game.fourteenth.features`).
2. `docs/dev/414th-features.md` §53/§54 engineering deep-dive.
3. `README.md` (player-facing) when the bite is live.
4. CLAUDE.md / AGENTS.md "Features at a Glance" §53/§54 + this note in the design-notes list
   (resync AGENTS.md byte-identically).
5. `docs/dev/414th-ingame-pass-checklist.md` rows: §53 = "does bombing enemy production/
   transport visibly thin their front over a multi-turn campaign"; §54 = "is the greyed-out/
   fallback munition correct in the payload editor and enforced in the generated `.miz`."

## Tests
- `tests/fourteenth/test_war_economy.py` — production rate, transport throttle on a cut link,
  the recovery/cap/delta scaling, off / no-factory / no-front no-ops, save-migration default.
- `tests/fourteenth/test_munitions_availability.py` — family tagging resolves, debit-at-loadout
  math, `degrade_for_stock` swaps to a stocked fallback (against real F/A-18C pylon tables, per
  the §46 test style), fuel-tank exemption, custom-loadout behavior.

## Deferred / open
- P3 fuel/readiness axis and P4 client overlay are optional follow-ons.
- Full weapon-family backfill (the §46 `UNKNOWN` fix) is a superset of M0's curated tags —
  revisit if we want it for its own sake.
- Whether ammo depots should become a *stockpile* (consumed) rather than the current *cap*
  formula — the cap stays in v1; converting it is a P2+ refinement once the ledger is proven.
