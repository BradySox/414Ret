# 414th — Player-Manned QRA (design notes)

> Status: **LANDED (Phase 2, 2026-06-29) — needs an in-game pass (checklist A3).**
> Lets a human pilot "man" part of a Quick-Reaction-Alert reserve instead of QRA
> being purely AI. Read `414th-air-defense-planning-notes.md` (QRA intent) and
> features doc §1 first; the engineering write-up is features §1 "Player-manned QRA".
>
> **Implemented design** (the two decisions that shaped it):
> - **Reserve-derived** (§4 Approach B): a per-squadron `qra_player_manned` count
>   carves N of the reserve into an auto-fragged alert flight and debits the AI
>   dispatcher — not a hand-built flight.
> - **Full ATO flight** (the user's call over the simpler bare-client-spawn): the
>   alert jet is a real `Package`+`Flight` in the ATO, so it gets a flight plan,
>   task loadout, kneeboard, briefing, and normal loss accounting.
> - **Reuse `FlightType.BARCAP`** (no new enum, no save migration); the dedicated
>   `FlightType.QRA` alternative stays documented in §6 but unbuilt.
>
> Phase 3 (2026-06-29): the **"raid inbound — scramble" cue** is now built — a
> per-base scan in `intercept-config.lua` (fed by `PLAYER_ALERT` records) calls the
> player to scramble when a hostile closes inside the AI GCI radius + a lead margin.
> Still deferred: an AI-wingman option for a manned 2-ship.

---

## 1. The problem, precisely

Today a player **cannot** man a QRA package, and that's a structural fact, not a
missing checkbox.

A flight becomes player-flyable only when a real `Flight` exists in the ATO whose
`FlightMember.pilot.player` is `True`; at generation `FlightGroupConfigurator.set_skill()`
sees that flag and calls `unit.set_client()` / `set_player()` to hand DCS a controllable
slot (`game/missiongenerator/aircraft/flightgroupconfigurator.py`).

QRA deliberately has **no ATO flight**:

- The reserve is just an integer, `Squadron.intercept_reserve`, carved out of
  `untasked_aircraft` (`owned_aircraft − intercept_reserve`, `game/squadrons/squadron.py`)
  so the auto-planner never frags it.
- At mission gen, `AircraftGenerator.spawn_intercept_templates()`
  (`game/missiongenerator/aircraft/aircraftgenerator.py:237`) builds a **throwaway**
  `Flight(… FlightType.BARCAP, StartType.COLD …)` whose `state = Completed()` (so it is
  never spawned the normal way), drops a **late-activated, uncontrolled** parking template
  via `create_intercept_template()`, appends an `InterceptEntry`, then `roster.clear()`s.
- At runtime, MOOSE `AI_A2A_DISPATCHER` (`resources/plugins/intercept/intercept-config.lua`)
  owns those templates and **air-spawns** 1–2 AI ships when a raid crosses the GCI radius.

So QRA is "reactive AI defense, spawned by a script." MOOSE air-spawns *AI groups*; it
cannot hand a human a cockpit, and DCS can't hold a human "cold on alert and scramble them
by timer." The only faithful human experience is **sit alert**: spawn cold on the alert
pad, monitor GCI, launch when the raid is called. That is exactly how human alert missions
are flown in DCS, so the design leans into it rather than fighting it.

---

## 2. Design principle

> A player QRA jet is a **real ATO flight** (so it gets a flight plan, loadout,
> kneeboard, briefing, and normal loss accounting). The QRA *reserve* integration
> is one thing only: **decrement the AI dispatcher's count** by the airframes the
> player takes, so a manned jet isn't also air-spawned by MOOSE.

This keeps the two systems cleanly separated:

| | AI QRA (today) | Player QRA (new) |
|---|---|---|
| Lives in ATO? | No (throwaway template) | **Yes** (real `Flight` + `Package`) |
| Spawn | MOOSE air-spawn, on demand | Cold on the alert pad, present at mission start |
| Controlled by | `AI_A2A_DISPATCHER` | The human |
| Flight plan / kneeboard / loadout | None | Full, normal pipeline |
| Counted in `resource_count`? | Yes | **No** — subtracted out |

The player flight and the AI dispatcher **coexist** at the same base: e.g. a squadron with
reserve 3 and 1 player-manned puts the human on the pad and leaves 2 for the dispatcher.

---

## 3. End-to-end change map

### 3.1 Model — designate the manned count

Add a per-squadron `qra_player_manned: int = 0` to `Squadron`
(`game/squadrons/squadron.py`), clamped to `0 ≤ manned ≤ fielded reserve`.

- Default 0 → no behaviour change for every existing campaign/squadron.
- `__setstate__` defaults it to 0 for old saves (no migration table needed — it's a new
  field, not a renamed enum value).
- It does **not** further reduce `untasked_aircraft` — those airframes were already removed
  from the planner pool by `intercept_reserve`. `qra_player_manned` only *re-labels* part of
  the existing reserve as human-flown.

A small helper next to the existing ones in `game/squadrons/intercept_reserve.py`:

```python
def qra_player_manned_count(player_manned, fielded_resource_count) -> int:
    """Manned QRA airframes, never more than the squadron actually fields."""
    return max(0, min(player_manned, fielded_resource_count))
```

### 3.2 Generation — split the reserve, build a real client flight

In `spawn_intercept_templates()` (`aircraftgenerator.py:237`):

1. Compute `fielded = qra_resource_count(...)` as today.
2. `manned = qra_player_manned_count(squadron.qra_player_manned, fielded)`.
3. **Dispatcher count becomes `fielded − manned`.** If that is `0`, skip the `InterceptEntry`
   entirely (the human is the whole alert response for that base) but still build the player
   flight. If `manned == 0`, behaviour is byte-for-byte unchanged.
4. Build the **player** flight as a *real* flight, not the throwaway:
   - `FlightType.BARCAP`, `StartType.COLD` (decision §5.1). The jet is a **normal
     cold-start flight present from mission start** — *not* late-activated/triggered. It
     simply sits on the alert pad and **the player decides when to scramble** (start, taxi,
     launch). No activation trigger is built; the incoming-raid message (§3.3) only *informs*
     that decision, it never launches the flight.
   - A **base-defense orbit** flight plan anchored on the home field (reuse the existing
     BARCAP/patrolling flight-plan builder with the patrol anchor at the airbase, matching
     the fork's base-defense QRA posture — no forward CAP line).
   - One member with `pilot.player = True`; remaining members (if `manned > 1` or a 2-ship)
     AI wingmen.
   - The flight must flow through the **normal** generation path (so it gets loadout,
     kneeboard, debrief) — i.e. it is added to a real `Package`/ATO, not left `Completed()`.

The cleanest seam: rather than special-casing this inside the template loop, create the
player QRA flight in the **same place the planner builds flights** so it inherits the full
pipeline, and have `spawn_intercept_templates()` only do the *count subtraction*. (See §4 for
how the flight gets created — auto from the count, vs. player-built in the UI.) The precedent
that a generated flight can carry a client slot already exists in `_spawn_unused_for()`
(`aircraftgenerator.py:360`): the opfor-client path sets `state = WaitingForStart`,
`group.uncontrolled = False`, `units[0].skill = Skill.Client`.

### 3.3 The scramble message (Lua) — in scope (decision §5.4)

The player explicitly wants a **"raid inbound — scramble" message** when a raid is detected,
so they can *decide* to launch (the message never launches them — see §3.2). This is a core
Phase-2 piece, not deferred.

- In `intercept-config.lua`, when the dispatcher detects a raid approaching a base that has a
  *player alert flight*, fire an **F10 text + radio** call — e.g. "SCRAMBLE — bandits
  bullseye XYZ, vector NNN, NN nm." Needs the player flight's group name (and base) passed
  through the Lua bridge: a new optional field on `InterceptEntry`, or a small sibling list
  `dcsRetribution.Intercept.PLAYER`. Keep it optional so absent → today's behaviour.
- **Lead-distance margin (decision §5.4):** the player message must fire at a **larger
  radius than the AI scramble** (e.g. `gci_max_radius_nm + player_scramble_lead_nm`) so a
  cold-starting human has spool-up + taxi + climb time before the merge. Expose
  `player_scramble_lead_nm` as a setting (or plugin option).
- A bare fallback already exists for free: the coalition GCI messages emitted when
  `qra_comms_enabled` is on (`intercept-config.lua:318,358`) — usable before the dedicated
  player call lands.
- **Deferred:** scramble timer / scoring ("airborne within N minutes").

### 3.4 UI — set the manned count

In `SquadronDialog.py` (the QRA reserve spinbox lives at lines 343–359), add a second,
dependent spinbox **"…of which player-manned"** directly under "QRA reserve":

- `min = 0`, `max = squadron.intercept_reserve` (kept in sync when the reserve spinbox
  changes), disabled when the squadron can't fly BARCAP or reserve is 0.
- `valueChanged → squadron.qra_player_manned = value` (mirror `on_qra_reserve_changed`).
- Tooltip: "How many alert jets you'll fly yourself. These spawn cold on the alert pad and
  are removed from the AI scramble pool."

(Alternative/added later: a "QRA / Alert" role button in flight creation that sets cold start
+ home-field orbit in one click — see §4 Approach A.)

### 3.5 Debrief / loss accounting — avoid double-count

Player QRA flights are normal ATO flights, so their losses are committed by the **normal**
loss path — nothing to add there. The only correctness requirement is that the AI
reconciliation (`game/missiongenerator/interceptattrition.py` →
`fielded_qra_by_squadron` / `reconcile_intercept_losses`, committed in
`missionresultsprocessor.py`) uses the **same** `fielded − manned` baseline the generator
seeded the dispatcher with, so it never attributes a player loss to the AI reserve or vice
versa. Centralise the `manned` subtraction in one helper used by both generation and
`fielded_qra_by_squadron` (the file already documents "single source of truth so report and
debit compute the same baseline").

### 3.6 Tests

- `tests/squadrons/` — `qra_player_manned_count` clamping; manned never exceeds fielded;
  reserve→manned interplay.
- `tests/missiongenerator/test_interceptluadata.py` / a generation test — dispatcher
  `resource_count` is reduced by `manned`; entry skipped when `fielded − manned == 0`;
  unchanged when `manned == 0`.
- `tests/missiongenerator/test_interceptattrition.py` — reconciliation baseline matches the
  reduced count (no phantom AI losses for a manned jet).
- `tests/squadrons/test_squadron_setstate.py` — old saves default `qra_player_manned = 0`.

---

## 4. Two ways the player flight gets created

Both reuse §3.2's flight shape; they differ in *who* creates it.

- **Approach A — player-built (lowest effort, most flexible).** No `qra_player_manned`
  field. The player just creates a BARCAP flight, cold start, at an alert base; an optional
  "Alert" flight-plan profile sets the home-field orbit in one click. Reserve reconciliation
  is best-effort or skipped. Ships fastest; "QRA" is really "a base-defense CAP you chose to
  ground-start."
- **Approach B — reserve-derived (recommended, truest to the question).** The
  `qra_player_manned` count carves the human jet out of the *same reserve pool* the
  dispatcher draws from, auto-creating the alert flight at generation and subtracting it from
  the AI count. This is literally "man one of those QRA jets," with unified bookkeeping.

Recommendation: **build B**, but its flight-creation core is A, so A is the natural **MVP /
Phase 1** and B is Phase 2 (add the count + subtraction + UI on top).

---

## 5. Design decisions (RESOLVED)

1. **Start posture — `COLD`, present from mission start, player-decided scramble.** The jet
   sits cold on the alert pad from t=0; the player chooses when to start/taxi/launch. It is a
   normal cold-start flight, **not** a triggered/late-activated one. (See §3.2.)
2. **Single vs multi-ship — up to a 2-ship, default single.** Default is one manned ship
   (matching the 75% single-ship AI posture); the player may opt into a 2-ship (human lead +
   AI wingman). (Author's call, per the user.)
3. **Flight plan — pure home-field defensive orbit.** A tight CAP anchored on the alert base;
   the player vectors off it on the cue. No forward CAP line. (See §3.2.)
4. **Scramble message — YES, when a raid is incoming.** Fire an F10/radio "raid inbound —
   scramble" call so the player can *decide* to launch (it never launches them). The message
   triggers at a **larger radius than the AI scramble** (lead-distance margin) so a cold start
   has time. (See §3.3.)
5. **BLUE only.** Player QRA is the human side; red-side players remain served by the existing
   `untasked_opfor_client_slots`. No red-specific work.

---

## 6. Rejected / deferred alternative: a dedicated `FlightType.QRA`

A first-class `FlightType.QRA` (or `ALERT`) would give cleaner semantics, an alert-specific
flight-plan builder, and bespoke kneeboard treatment. **Not recommended for v1** because it
costs:

- a save migration entry in `_LEGACY_FLIGHT_TYPE_VALUES` (`game/ato/flighttype.py`) and the
  full enum-plumbing (role description, loadouts, codewords, flight-plan builder registration);
- divergence from the AI QRA path, which deliberately reuses `BARCAP`.

Reusing `BARCAP` with a cold start + home-field orbit gets ~95% of the experience for a
fraction of the surface area. Revisit `FlightType.QRA` only if the alert flight needs
behaviour BARCAP genuinely can't express.

---

## 7. Risk / gotcha register

- **Double-spawn** — the #1 correctness trap. If the dispatcher count isn't reduced, the same
  airframe is both on the pad (player) and air-spawned (AI). The `fielded − manned` baseline
  must be the single source of truth shared by generation *and* debrief reconciliation.
- **Parking pressure** — a real cold-start flight consumes a parking slot that the throwaway
  template also wanted; watch `NoParkingSlotError` (already handled for templates at
  `aircraftgenerator.py:291`).
- **No true "alert hold"** — DCS can't keep a human uncommitted until scrambled; the player
  simply starts cold and waits. Set expectations in the tooltip/briefing.
- **Lua bridge churn (Phase 2)** — passing the player group name through `InterceptEntry`
  touches `interceptluadata.py` + the Lua reader; keep it optional so absent → today's
  behaviour.

---

## 8. Suggested phasing

- **Phase 1 (MVP):** Approach A — "Alert" BARCAP flight-plan profile (cold start + home-field
  orbit), no model/Lua change. A player can fly a QRA-style alert today.
- **Phase 2:** Approach B — `qra_player_manned` field + UI spinbox + dispatcher-count
  subtraction + shared reconciliation baseline + tests, **plus** the §3.3 "raid inbound —
  scramble" F10/radio message with its lead-distance margin (the user wants the cue as part of
  the feature). This is the real "man one of the QRA reserve" feature.
- **Phase 3 (deferred):** scramble scoring/timer ("airborne within N minutes").

Docs to update when it lands (per CLAUDE.md hygiene): this note → features doc §1 (extend) →
README (player-facing) → register in `game/fourteenth/features.py` → in-game-pass checklist
row (the cold-start alert + scramble cue need a flight test).
