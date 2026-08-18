# 414th Living Battlespace — the turn as a slice of a continuous air war

**Status: ALL FIVE SLICES LANDED 2026-08-15** (feature §89, checklist rows B56–B60,
features doc §89). The note's build program is complete; what remains is the in-game pass
ladder (B56–B60) and the open calls below.
P1: player pinning + the phase curve + the auto pre-roll at launch. P2: recovery residue,
expended stores on egress-phase strikers, burned-down AI fuel. P3: the follow-on tail
(knob-free, symmetric with the pre-roll) and the "air war so far today" briefing block. P4:
the voice net — **open call 5 answered**: generation-time SAPI pre-render with native
playback (zero player footprint; spike-measured ~150 ms and ~35 KB per 8 kHz call), the
SRS/MSRS runtime ecosystem recorded as the dynamic alternative; calls transmit positionally
from real flights on the blue AWACS frequency via the `battlespacenet` plugin. P5: reactive
red — up to two REAL claimed alert flights parked past the mission (deliberately not the §61
untracked-freebie path), launched one-per-struck-objective by the `reactivered` plugin under
positive-list discipline, flying a defensive orbit over the struck point. Recorded
deviations: carrier ramp residue deferred (§64/§72 interplay); the stores strip is
**clean-wing-plus-pods** rather than "keep A2A and tanks" (open call 9); reactive red's
second event (CAP backfill surge) stays open call 6. This note records the problem, the
measured evidence, the scoping decisions, and the phased plan.

**Related:** [`414th-single-player-loop-notes.md`](414th-single-player-loop-notes.md)
(§83 SP Pilot Mode — the delivery surface this pairs with) ·
[`turnless.md`](turnless.md) (superseded upstream draft; §12 below on why this is not
that) · [`414th-moose-ops-opportunity-map.md`](414th-moose-ops-opportunity-map.md)
(the Tier-A adoption rule the voice net follows) ·
[`414th-comint-notes.md`](414th-comint-notes.md) (§70's red net; its deferred
"voice chatter" item now has a home) · features doc §1 (QRA), §6 (BARCAP waves),
§26 (off-mission resolution), §47 (continuous clock), §83 (SP Pilot Mode).

---

## 1. Decisions in force (DM, 2026-08-15)

| Call | Decision |
|---|---|
| Layers | Desynchronized ATO, voice net, reactive red. **Ambient logistics deferred** — not selected; revisit after P1–P3. |
| Background flights | **All real sorties.** Every background airframe is a real squadron/economy unit and its loss counts. No immortal/invisible furniture. |
| Hot-start depth | **Phase-aware.** The first flyable turn keeps its H-hour launch; later turns spawn progressively mid-cycle. |
| Audience | **SP first.** MP sizing deferred until the SP shape is flown (§8). |
| Voice audio | **Adopt, don't build.** TTS-over-radio transports already exist as community scripts/plugins; a spike validates the SP footprint before any build (§6). |
| Sequencing | Probe before design (done, §4); design note before code (this note). |

## 2. The problem

A Retribution turn generates a real 20+-package ATO and still feels canned, because the
whole air war is synchronized to the player's sortie:

1. **Everything launches with you.** At mission start the entire ATO is on the ramp;
   nothing is already outbound, on station past its first vul, or inbound to land.
2. **The sky dies behind you.** No package has a TOT after yours; after the last TOT the
   theater is empty and stays empty.
3. **The net is silent.** DCS AI generates almost no AI-to-AI radio traffic, so tuning
   another package's frequency yields nothing. The only organic traffic is the tower net.

Measured on `operation_baltic_fury`, turn 0 (headless, 2026-08-15): 23 packages,
35 flights.

| Series | 10-minute buckets from mission start |
|---|---|
| takeoffs | 0m:3 · 10m:15 · 20m:3 · 30m:4 · 40m:5 · 50m:2 · 60m:1 · 70m:1 · 80m:1 |
| TOTs | 0m:1 · 10m:13 · 20m:1 · 30m:2 · 40m:2 · 50m:6 · 60m:2 · 70m:2 · 90m:4 · 110m:2 |
| egress | 40m:1 · 60m:5 · 70m:12 · 80m:3 · 90m:2 · 110m:6 · 130m:4 · 150m:2 |

18 of 35 flights take off inside the first 20 minutes; all 35 inside 90; the war is over
by ~2.5 h. That distribution is the canned feel.

## 3. What a hand-built campaign does instead (campaign G)

Campaign G is an installed paid F-16C campaign, scanned across its 11 missions at
unit/route level. (Its trigger and voice logic is DRM-protected — an encrypted pak loaded
via `ext_loader`; the miz carries **zero** trigger rules and zero Lua. Choreography below
is read from the unit layout only.)

| Measure | Value |
|---|---|
| AI air groups per mission | 15–27 (avg ~19); **red 0–6** |
| Late-activated story reserves | 75 of 208 groups |
| Air-start first waypoints | 156 of 208 groups |
| Voice files per combat mission | 250–320 oggs (9–16 MB) |
| Ramp statics per mission | 30–91 |

The recipe, as far as the unit layout shows it:

- Support is always up at T=0: 3–4 tankers on standing named tracks, AWACS, a drone —
  set immortal + invisible, unlimited fuel. Combat AI also gets unlimited fuel so the
  choreography cannot run dry.
- A transport conveyor crosses the theater every mission (3–4 strategic airlifters plus
  smaller types), unrelated to the player's tasking.
- The player's squadron visibly cycles: an airborne flight lands mid-mission while a
  parked twin (same name + " Landed") dresses the ramp; parked singles start up around
  the player; the same callsign exists twice (parked copy, late-activated airborne copy)
  so a jet re-materializes in whatever state the next scene needs.
- The radio soundtrack is carried by dedicated invisible transmitter aircraft.

**What translates:** desynchronization (things end and begin around the player) and an
audible net matter far more than sortie count — the "war" is ~20 aircraft and a
soundtrack. **What is rejected:** the furniture flags (immortal/invisible/unlimited
fuel) and phantom re-materialization. The all-real decision (§1) and the fork's
no-phantom rule both forbid them; Retribution's advantage is that its background war is
real, so ours must be desynchronized honestly instead of staged.

## 4. The probe (2026-08-15)

Method — adapted from `tools/system_probe.py::_build_game`, run against
`operation_baltic_fury`:

```python
game = _build_game("resources/campaigns/operation_baltic_fury.yaml", tmp)
game.initialize_turn(GameUpdateEvents())   # begin_turn_0 alone leaves the ATO empty
game.settings.fast_forward_stop_condition = FastForwardStopCondition.MANUAL
sim = MissionSimulation(game)
sim.begin_simulation()
for _ in range(40 * 60):                   # +40 min of war, 1 s ticks
    ev = sim.tick(GameUpdateEvents(), CombatResolutionMethod.RESOLVE, force_continue=True)
    if ev.simulation_complete:
        break
sim.generate_miz(out_path)                 # a mid-cycle miz, 40 min into the war
```

Findings:

- **F1 — mid-cycle generation works today, end to end.** The T+40 miz contains 19 combat
  flights spawned airborne mid-route (CAPs mid-vul, escorts at their join, a tanker
  inbound to its track, helos at 500 ft on ingress), the next wave taxiing, and the
  flights that already finished or died correctly absent. Wall cost: seconds to march,
  normal generation time. This is the §26 fast-forward machinery
  (`FlightGroupSpawner.generate_mid_mission`, `game/sim/missionsimulation.py`) — it has
  simply never been pointed at "start the player mid-cycle."
- **F2 — the flight-state machine is rich enough.** Per-flight position, altitude, speed
  and fuel estimates (tanker top-ups included) exist for every in-flight state
  (`game/ato/flightstate/inflight.py`).
- **F3 — the pre-roll fights a real war.** `CombatResolutionMethod.RESOLVE` killed 5 of
  35 flights in 40 minutes (BARCAP-on-BARCAP, both sides). Losses merge into the debrief
  through the existing `merge_simulation_results` path — economically consistent, but
  the attrition rate makes pre-roll length a real tuning knob (§5, W4).
- **F4 — returned flights vanish.** `aircraftgenerator.py` skips flights in `Completed`
  (~line 163), so there is no recovered-jets ramp residue. Upstream left the seam
  marked: `Completed.spawn_type` returns `COLD` with a `TODO: may want to make these
  uncontrolled?`.
- **F5 — no stores-expenditure model exists.** A flight spawned past its target carries
  full ordnance (grep: "expend" appears only in weapon-release scripting and naval
  magazines).
- **F6 — ambience already in the tree:** 62 parked idle airframes
  (`create_idle_aircraft`), QRA alert templates, and 6–8 neutral civilian airliners
  airborne, every generation.
- **F7 — parking overflow during mid-cycle generation air-promotes the flight** with a
  warning (existing upstream fallback; acceptable, watch the rate).

## 5. Design — the pre-roll spine (the desynchronized ATO)

**Core idea: do not build new spawn machinery.** Seat the player later inside an ATO
cycle that is planned around them, then auto-run the existing fast-forward to the
player's startup before generating. The pre-roll length *is* the player's position in
the cycle.

The v1 flow, all on existing seams:

1. **Planner window spread (W1).** A gated change in `plan_missions`: package TOTs
   distribute across a wider cycle window instead of front-loading, and the player's
   package is pinned so its startup falls at the briefed mission start (the inverse of
   `auto_ato_player_missions_asap`). Flights earlier in the cycle will be outbound,
   on station, inbound, or already home when the player walks out.
2. **Auto pre-roll at launch (SP flow).** On Take Off, run `MissionSimulation` with
   `RESOLVE` and stop condition `PLAYER_STARTUP`, then `generate_miz`. No new sim code —
   UI wiring plus a progress surface that already exists for fast-forward.
3. **Results stay honest.** Pre-roll outcomes merge at debrief via
   `merge_simulation_results`, exactly as fast-forward outcomes do today.
4. **OFF is byte-identical.** No spread, no auto-pre-roll, today's behavior.

A clock-shift variant (move `conditions.start_time` back, plan, march to the original
time) was considered and dropped: seating the player later in the same cycle produces
the same world with no clock semantics risk (§47's marched clock stays untouched).

**Phase-aware curve (strawman, open call 1):** first flyable turn = 0 minutes (the
H-hour launch is a feature, not a bug — the war's first mission *should* start with
everyone on the ramp); turns 2–3 ≈ 15 min; turn 4+ ≈ 30–45 min, capped by a settings
knob and overridable per campaign. The campaign's rhythm becomes visible: early = massed
launches, mid-war = you join a war already in motion.

### Work items

| # | Item | Size | Notes |
|---|---|---|---|
| W1 | Planner TOT spread + player pinning | M | The only planner-touching piece. Additive and gated (§8); flights whose whole cycle predates startup arrive as `Completed`. |
| W1b | Follow-on waves | S/M | Plan CAP rotations + at least one offensive package with TOTs past the player's expected egress. The delay/late-activation machinery already generates delayed flights; verify long delays survive generation (open call 4). |
| W2 | Recovery residue | S | Stop skipping `Completed`: spawn parked, uncontrolled, at the arrival field (the upstream TODO). Flights still airborne on their return legs already spawn correctly under W1 — "jets on final as you taxi out" needs no extra work. |
| W3 | Stores expenditure on egress-phase spawns | S/M | In `generate_mid_mission`, if the flight is past its ingress/target waypoint and flies an air-to-ground task, strip A2G stores from the spawned payload (keep A2A and tanks). Generation-time only; no economy hook. Verify the estimated fuel is actually written to the spawned group, not just computed. |
| W4 | Pre-roll combat policy | — | v1: `RESOLVE` as-is; short pre-rolls keep the measured attrition (5/35 per 40 min) small. v2 option: freeze active combats and spawn them live at T=0 — turnless.md's frozen-engagement idea repurposed as an opener ("a merge is happening 60 NM north as you spawn"). A no-kill grace for the player's coalition is listed for completeness and disfavored: it is furniture by another name. |
| W5 | "The war so far today" briefing block | S | Pre-roll events (launches, kills, losses) surfaced in the §58 briefing popup / §29 SITREP style, so the mid-cycle start reads as narrative, not a bug. |

Perf note: a pre-rolled T=0 has *fewer* live units than today's (some flights are done or
dead); follow-on waves add parked units awaiting activation. Net near-neutral, with the
wave count as the cap knob.

## 6. The voice net (adopt, don't build) — BUILT, THEN REMOVED (2026-08-18)

> **⛔ The voice net is gone.** Built as P4 on 2026-08-15 and removed on 2026-08-18 on the
> DM's call — *"the AI already uses the radio"*. DCS's own AI already transmits on the
> briefed channel, so a synthesized net layered on top read as duplication rather than
> atmosphere, and it never earned its in-game pass. Everything below is the reasoning
> that led to building it, kept because open call 5 (the transport decision) is still
> the record of why generation-time pre-render beat the SRS-runtime ecosystem — reach
> for it if a future feature needs synthesized audio. Do NOT author against it as a
> live feature. §89's other phases are unaffected.

What "audible net" must mean, stated honestly: DCS AI does not talk to itself, so there
is no traffic to overhear by frequency-sharing. The only organic gain is the **tower
net** — under W1/W2 the player's field genuinely cycles flights, and their native ATC
calls are audible on the tower frequency for free.

Everything else is generated: at planning time the ATO already implies every call
(check-ins, pushes, picture calls, on-/off-station, RTB). The design follows the
Python-plans / Lua-executes split:

- **Python** emits a chatter schedule — `(time, frequency, source unit, text)` rows
  derived from the real ATO timeline, through a normal one-entry-point emitter.
- **Lua** walks the schedule and speaks each row through an **adopted** TTS transport
  (DM call 2026-08-15: these exist in the ecosystem as scripts/plugins). Positional
  `radioTransmission` from the real source unit is the delivery contract the §70 red
  net already proved.
- **Spike first (P4a):** validate the transport's SP footprint — what must run beside
  DCS, what the pilot must install — before any build. This is the layer's one hard
  unknown and it gates the rest.

Discipline: constrained brevity phraseology, rate-limited (cap calls/minute, silence
windows), own-package and nearest-net calls preferred. Every call describes a flight
that actually exists on the timeline it actually flies — chatter that matches the war is
the point, and the thing campaign G spends 300 hand-recorded files per mission faking.

## 7. Reactive red

Extend the §1 alert-dispatcher pattern from intercepts to a small set of event-driven
responses, inside red's settled defensive fighter posture:

- **v1 event:** post-strike reconnaissance. A struck red objective tasks a real
  alert-reserve recce sortie over its own target area within ~15 minutes. The player
  sees the war *react* to what they just did.
- **Candidate second event (open call 6):** CAP backfill surge after red fighter losses
  exceed a threshold, beyond normal QRA scramble logic.

Safety shape is the standard one: Python emits a positive list (which objectives may
react, which squadron/airframes may fly it); the Lua side cannot widen it; every spawn
is a real tracked reserve airframe.

## 8. Constraints

1. **No phantom units** — settled by the all-real decision; applies to every layer.
2. **Gated, default OFF, byte-identical OFF.** Campaigns that preseed the feature must
   preseed its plugin too (the §36 lesson) once a plugin exists.
3. **Planner discipline.** W1 is additive on upstream's planner; the 2026-08-09
   re-convergence decision stands. Upstream planning is a crowded PR zone and the PR
   freeze is in force — this bakes fork-side; carving waits.
4. **MP deferred, risks named now:** every client spawns mid-cycle, not just one player;
   carrier slot timing (§64) interacts with a cycling deck; generation-time pre-roll is
   host-side only (fine). Revisit after the SP shape is flown.
5. **Unflown-feature debt is real.** Each slice lands with its own checklist row and an
   in-game pass before the next slice starts.

## 9. Phased slices

Each slice is independently flyable and independently gated. Proposed pass criteria
become checklist rows when the slice lands, not before.

| Slice | Content | Size | Proposed pass criterion / fail signature |
|---|---|---|---|
| P1 | **LANDED 2026-08-15** (§89, row B56) — player pinning + auto pre-roll in the launch flow + phase curve knob; the W1 spread half deferred to P3 | M | Pass: at spawn, multiple flights are airborne mid-route and at least one recovers within ~20 min; player startup matches the briefed window. Fail: flights teleported to waypoint 1, briefed-vs-DCS clock mismatch, mass parking-overflow air-promotes (F7). |
| P2 | **LANDED 2026-08-15** (§89, row B57) — W2 residue at the arrival field (carriers deferred) + W3 stores strip (v1 clean-wing-plus-pods, open call 9) + AI mid-air fuel. **2026-08-16: residue un-starved by the removal-site ledger** — the sim removes every `Completed` flight from the ATO at the tick boundary, so generation's walk only ever saw final-tick completions (B57 desk check: zero at generation across 40–150-minute marches, ATO census 38→18; solo-flight packages, most CAPs, could never render). The removal site now records (flight, arrival-frozen-at-completion) into a transient ledger (fogofwar.py pattern: cleared at `begin_simulation`, never pickled), `generate_flights` parks ledger flights after the tasked walk, and the P3 briefing's `recovered` count reads it too. Recorded-means-removed keeps ledger and walk disjoint; the generation-time synthetic `Completed` flights (idle ramp, QRA/red-scramble templates) never pass the removal site, so they stay excluded by construction | S/M | Pass: a completed flight's jets sit parked at their field; an egress-phase striker spawns without A2G stores. Fail: "returners" with full racks; duplicate airframes. |
| P3 | **LANDED 2026-08-15** (§89, row B58) — W1b follow-on tail (spread window += pre-roll minutes, knob-free) + W5 briefing block | S/M | Pass: at least one package launches after the player's egress; the briefing narrates the pre-roll. Fail: waves never activate (silent-gate class) or eat all parking. |
| P4 | **LANDED 2026-08-15** (§89, row B59) — spike answered open call 5 (generation-time SAPI pre-render; SRS/MSRS recorded as the runtime alternative); schedule emitter + `battlespacenet` plugin, AWACS-frequency delivery | spike S, build M/L | Pass: calls audible on briefed frequencies matching real ATO events, rate-limited. Fail: silence (transport absent) or spam. |
| P5 | **LANDED 2026-08-15** (§89, row B60) — real claimed alert flights (not the §61 freebie path), one defensive orbit per struck listed objective, pool-capped | M | Pass: striking a listed objective produces the reaction sortie from real reserve stock. Fail: any spawn outside the positive list. |

## 10. Open calls

1. Phase curve numbers and the campaign override shape.
2. Pre-roll combat policy: `RESOLVE` v1 vs freeze-and-spawn-live v2 (W4).
3. Whether pre-roll attrition needs a soft cap independent of pre-roll length.
4. Follow-on wave budget (count/perf cap), and verification that long activation delays
   survive generation.
5. ~~Voice transport pick and its SP footprint~~ — **ANSWERED 2026-08-15 by the P4a spike:**
   generation-time Windows SAPI pre-render with native playback (zero installs, ~150 ms and
   ~35 KB per 8 kHz call, the band limit doubling as the radio effect). The SRS/MSRS runtime
   TTS ecosystem stays the recorded alternative if dynamic in-mission calls or better voices
   are ever wanted (its cost: SRS running beside DCS).
6. Reactive red's second event.
7. Briefed-time presentation: does the kneeboard lead with "the war began 40 minutes
   ago" (W5's framing)?
8. MP entry criteria, after SP verification.
9. The stores strip's weapon taxonomy: v1 strips returning strikers to a clean wing plus
   pods because `WeaponType` carries no A2A/TANK members. Enriching `resources/weapons`
   `type:` (an AAM/TANK tagging sweep, ~50–100 yamls) would restore the designed
   "keep A2A and tanks" — decide whether the sweep is worth it or clean-wing stands.

## 11. Test plan (when it builds)

- Headless: gate OFF is byte-identical to baseline generation.
- Headless: gate ON widens the takeoff histogram past a threshold and pins the player's
  startup to the briefed window.
- Headless: a `Completed` flight yields a parked uncontrolled group at its arrival
  field; an egress-phase A2G flight spawns without A2G stores and with estimated fuel.
- Headless: a package with a TOT past player egress generates late-activation plus a
  live activation path.
- Harness (`tests/lua/`): the voice-net plugin walks a schedule and stops cleanly; the
  red-reaction plugin refuses anything outside its positive list.
- In-game: one checklist row per slice (§9), written the turn the slice lands.

## 12. Non-goals

- **Not turnless.** Turns, economy, persistence, and the §47 clock are untouched; this
  renders the slice's edges instead of removing its boundaries. `turnless.md` stays
  superseded.
- **Not the ambient logistics layer** (transport conveyor, liaison helos) — deferred by
  the 2026-08-15 scoping call; the existing civilian traffic plus W1/W2's cycling carry
  the ambience until it is revisited.
- **Not a planner re-divergence.** One additive, gated distribution change; upstream
  defaults remain the OFF state.
- **Not MP-tuned yet**, and **not a hand-authored chatter library.**
