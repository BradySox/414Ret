# 414th Air-War Planner Consolidation — design notes

**Status:** proposal / design-only (no code change yet) · **Date:** 2026-06-25
**Related:** [`414th-air-defense-planning-notes.md`](414th-air-defense-planning-notes.md),
[`414th-moose-ops-opportunity-map.md`](414th-moose-ops-opportunity-map.md),
[`414th-moose-longview.md`](414th-moose-longview.md), CLAUDE.md §6 (air-defense rework),
§17 (auto-planner unpredictability). Wiki face:
[`docs/wiki/Air-Defense-and-the-Air-War.md`](../../wiki/Air-Defense-and-the-Air-War.md).

## The question

The air-war page now lists ~12 interlocking systems (QRA, reworked BARCAP volume/placement,
forward CAP line, red forward-middle layer, front-anchored support orbits, theater-tanker-on-
demand, DEAD reachability gate, mobile-SAM MFD hide, reactive SEAD, unpredictability knob, IADS
engine). It reads as a lot of moving parts. **Can we simplify the machinery while keeping the
behavior?** — asked specifically in the context of "now that we're fully MOOSE."

## The premise correction (this is the load-bearing point)

"Fully MOOSE" simplifies the **runtime/execution** layer (Lua inside the generated `.miz`).
Almost everything on the air-war page is **Python planner** logic that runs *before* the mission
is generated:

| Layer | Systems | Can MOOSE absorb it? |
|---|---|---|
| **Python planner (decide)** | BARCAP volume/placement, forward CAP line, red forward-middle layer, support-orbit anchoring, tanker-on-demand, DEAD reachability gate, MFD-hide, unpredictability | **No** — these are planning *decisions*. MOOSE absorbing them = `Ops.Chief`/`Commander` (Tier C), a runtime theater commander that competes with Retribution's Python brain. The fork has declined this **twice** (§17; `turnless.md`). It would replace the effect, not preserve it. |
| **MOOSE runtime (execute)** | IADS engine (MANTIS), QRA dispatcher (`AI_A2A_DISPATCHER`) | Already the consolidated pieces. |

So the honest answer is **two separate tracks**, below: a Python refactor that is the real
"simplify the process" win, and an opportunistic MOOSE Tier-A track that reduces *plugin* sprawl
(not planner sprawl). They do not substitute for each other.

---

## Track 1 — Python: consolidate the threat-field + standoff geometry (the real win)

### Key finding: the shared service already half-exists

Most of the planner systems are expressions of **two underlying quantities**:

1. a **threat field** — where/how strong the air + SAM threat is, and
2. **standoff geometry relative to the FLOT** — how far behind the line is survivable, and on
   what axis.

These primitives are *already partly factored* — but scattered, so each consumer re-wires them
differently. Ground truth (verified in-tree, 2026-06-25):

| Primitive | Lives in | Consumed by |
|---|---|---|
| Threat field (rings, boundaries, "is X threatened", path/route threat, radar-SAM rings, `barcap_threat_range`) | `game/threatzones.py` `ThreatZones` (`for_faction`/`for_threats`, `closest_boundary`, `distance_to_threat`, `threatened_by_{aircraft,air_defense,radar_sam}`, `path_threatened`, `waypoints_threatened_by_radar_sam`, `radar_sam_rings`) | everywhere |
| Standoff anchor (center on FLOT, push back past threat by a buffer; player forward / AI deep) | `game/ato/flightplans/supportorbit.py` `support_orbit_anchor` | `aewc.py`, `theaterrefueling.py` |
| Forward-middle anchor (halfway rear-CP→FLOT, parallel to front) | `supportorbit.py` `forward_cap_front_anchor` | `theaterstate.py` (forward-middle BARCAP), `theater/missiontarget.py` |
| Threat→BARCAP volume | `game/commander/theaterstate.py` `threat_weighted_barcap_rounds` | BARCAP scheduling |
| DEAD reachability (route vs turn-start radar-SAM ring snapshot) | `theaterstate.py` `unreachable_air_defenses` | strike/DEAD gating |
| Receiver-demand centroid (count-weighted, boom/probe-aware) | `game/commander/tankerdemand.py` | `theaterrefueling.py` (overrides anchor) |

The sprawl is not conceptual — it's that these live in four different modules
(`threatzones.py`, `supportorbit.py`, `theaterstate.py`, `tankerdemand.py`) with no single
named "airspace geometry" service, so each new feature re-imports and re-wires the pieces (e.g.
`aewc`/`theaterrefueling` call `support_orbit_anchor`; `theaterstate` calls
`forward_cap_front_anchor`; `forwardbarcap` is separate again).

### Proposal: one `AirspaceGeometry` service the consumers call

Promote the scattered helpers into a single cohesive module (sketch:
`game/commander/airspacegeometry.py`) constructed once per coalition per turn over the two real
inputs it already needs — `ThreatZones` and the `FrontLine` set — and exposing the handful of
primitives every consumer wants:

```python
class AirspaceGeometry:
    """Threat-field + FLOT-standoff geometry for one coalition, one turn.

    Wraps ThreatZones + the active fronts so BARCAP, support orbits, the theater
    tanker, and the DEAD gate all derive placement/volume/reachability from ONE
    model instead of each re-importing the primitives. Behavior-preserving:
    every method returns exactly what its current scattered caller computes today.
    """
    def __init__(self, threats: ThreatZones, fronts: Sequence[FrontLine],
                 doctrine: Doctrine, for_player: bool): ...

    # --- standoff geometry (today: supportorbit.support_orbit_anchor) ---
    def standoff_anchor(self, target, buffer: Distance) -> tuple[Point, Heading]: ...
    # --- forward-middle screen (today: supportorbit.forward_cap_front_anchor) ---
    def forward_middle_anchor(self, rear_cp, front) -> Point | None: ...
    # --- threat -> volume (today: theaterstate.threat_weighted_barcap_rounds) ---
    def barcap_rounds(self, cp, base_rounds: int) -> int: ...
    # --- reachability (today: theaterstate.unreachable_air_defenses) ---
    def dead_reachable(self, dead_route, target) -> bool: ...
    # --- receiver-demand centroid (today: tankerdemand) ---
    def refuel_demand_centroid(self, ato, method) -> Point | None: ...
```

Each existing consumer becomes a thin caller:

- `aewc.py` / `theaterrefueling.py` → `geom.standoff_anchor(...)` (already do, via the helper —
  just re-homed).
- `theaterstate.threat_weighted_barcap_rounds` / forward-middle block → `geom.barcap_rounds` /
  `geom.forward_middle_anchor`.
- the DEAD gate → `geom.dead_reachable`.
- `theaterrefueling`'s tanker override → `geom.refuel_demand_centroid`.

No behavior change is intended — this is a **move + unify**, not a redesign. The win is that the
"12 systems" collapse, on inspection, to **one threat-field + standoff model with ~6 thin
consumers**, which is far easier to reason about, test in isolation, and extend (the next
air-placement feature calls the service instead of re-deriving geometry, which is exactly how the
sprawl accumulated).

### Why this preserves the effect

The observable behavior is defined by the consumers' outputs (where orbits sit, how many BARCAP
waves, which DEAD is reachable). Re-homing the *computation* behind one service changes none of
those outputs — it changes only how many places the geometry is spelled out. The deterministic,
economy-aware, save-persistent planning the fork wants stays in Python and stays intact.

---

## Track 2 — MOOSE Tier-A: reduce *plugin* sprawl (opportunistic, separate)

Per the MOOSE opportunity map / longview, the runtime layer is where "more MOOSE" genuinely
removes code — but mostly for features off the air-war page. The two with an air-defense home:

- **`SHORAD`** — reactive short-range SAM wake-up on nearby air threats; pairs with the §7
  MFD-hide logic (the one air-war item with a natural MOOSE runtime home).
- **`DETECTION_*` substrate** — unify how `bigeye` EWR, C-130 ISR, and TARS sense, instead of
  three bespoke detection paths feeding the Python fog/BDA layer.

These are independent, opt-in, in-game-validated plugins (same shape as MANTIS/CTLD), not a
planner change. Track them on the consolidation roadmap, not here.

## Explicitly out of scope

**`Ops.Chief` / `Ops.Commander` / `Legion…` (Tier C).** A runtime MOOSE theater commander that
*decides* force tasking is the only way "more MOOSE" could absorb Track 1's planner systems — and
it would replace the Python brain (campaign state, economy, HTN, save format). Declined twice
already (§17 chose the in-Python unpredictability knob precisely as the cheaper alternative;
`turnless.md` keeps the HTN in Python). Revisit only inside a funded turnless/real-time
re-architecture, never as an increment.

## Suggested first move + risks

1. Land `AirspaceGeometry` as a pure **move-and-wrap** of the existing helpers, with the current
   call sites delegating to it — zero intended behavior change.
2. **Test strategy:** characterization tests first — snapshot today's outputs (orbit anchors for
   a few fronts, BARCAP round counts per CP, the `unreachable_air_defenses` set, the tanker
   centroid) and assert byte-for-byte equality after the move. The existing air-defense tests
   plus these guard the refactor.
3. **Risk:** the helpers have subtly different inputs (player-forward vs AI-deep buffer multiples
   in `supportorbit.py`; the turn-start ring *snapshot* the DEAD gate judges against in
   `theaterstate.py`). The service must preserve those exactly, not "rationalize" them — they
   encode real tuning. Keep each method's semantics identical to its source; unify the *wiring*,
   not the *numbers*.

## Bottom line

The air war feels busy because it's a dozen Python planner heuristics that each re-derive threat
and standoff geometry — not because the MOOSE layer is sprawling. The behavior-preserving
simplification is a **Python consolidation** onto one `AirspaceGeometry` service the helpers are
already 60% of the way toward. "More MOOSE" only simplifies this by handing planning to
`Ops.Chief`, which trades away the exact effect we want — so keep the brain in Python, unify its
geometry, and lean into MOOSE only on the runtime-service tier.
