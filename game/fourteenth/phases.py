"""Campaign phases (W3): Tier-0 inference + the soft planner emphasis.

Spec: docs/dev/design/414th-campaign-phases-notes.md. Every campaign -- including the
63 base-Retribution campaigns that ship with nothing but a YAML header -- knows what
*phase* of the war it is in, the UI shows it, and the auto-planner biases its
offensive intent to match. A phase is a doctrine-like profile, time-sliced instead of
campaign-wide, resolved fresh each turn from live campaign state (the
``VIETNAM_DOCTRINE`` display-and-gate precedent -- never a commander rewrite, never a
persisted-enum mutation).

This module is the whole Tier-0 engine: the :class:`CampaignPhase` object (spec
S2.1), the three generic phases, the inference classifier (S3.2 -- reads state that
already exists via the accessors the phase-pilot confirmed), the mandatory hysteresis
(S3.3: min-dwell + monotonic-forward; asymmetric regression thresholds are
implemented but regression stays opt-in/authored, i.e. off in v1), and the S3.4
legibility string ("Interdiction -- enemy IADS 22% / air threat low / front static")
so an inferred phase always explains itself.

W4 adds the **P2 authored tier + the ROE escalation layer** (spec:
414th-vietnam-political-will-roe-notes.md S3): a campaign YAML may carry a
``phases:`` block of authored :class:`CampaignPhase`\\ s that **override** Tier-0
inference -- advanced sequentially by turn pins (``min_turn``) or accelerated by
``advance_when`` conditions (bleeding political will speeds escalation --
historically backwards-sounding, historically true). Authored phases may carry
**restricted zones** (circles where offensive tasking is forbidden -- the planner
gate scrubs packages targeting inside; sanctuary airfields fall out) and
**locked target classes** (``target_release``: e.g. no power/factory strikes until
the phase releases them). Player enforcement is SOFT: the debrief charges a sharp
will penalty for kills inside an active zone (:func:`count_roe_violations`) -- the
LBJ-era pilot could always break the rules and answer for it. Definitions are
re-derived from the campaign YAML at load (module cache) and never pickled, so
editing a campaign's phases can't corrupt a save.

Boundaries (the S17 invariant): reactive defense stays deterministic. The emphasis
only reorders the *offensive* HTN root methods -- ``TheaterSupport`` /
``ProtectAirSpace`` / ``DefendBases`` keep their fixed lead positions in
``PlanNextAction`` regardless of phase, and the phase can never forbid a task in
Tier 0 (hard whitelist deltas are authored-only, P2).

Everything is gated by ``Settings.campaign_phases`` (default ON -- [DECIDED] Tier-0
inference is the default for every campaign); off means no classifier run, no
baseline, no emphasis, no status line.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from shapely.geometry import LineString, Polygon
from shapely.geometry import Point as ShapelyPoint
from shapely.geometry.base import BaseGeometry

if TYPE_CHECKING:
    from game import Game
    from game.debriefing import Debriefing

# --- S3.2 thresholds (v1; refined by the 6-campaign pilot) --------------------------

#: Below this many enemy long+medium SAM sites at turn 0 there is no meaningful
#: Rollback phase -- the campaign opens in Interdiction (or Air Superiority when real
#: enemy air exists). Engine-corrected examples (#379 all-66 re-run): the genuine
#: below-floor cases are Shattered Dagger / No Man's Land / Valley of Rotary /
#: Northern Guardian; Velvet Thunder sits exactly at the floor (3 SA-2 sites) and
#: keeps Rollback. (Khe Sanh was the pilot's original example but is NOT below the
#: floor in real gameplay -- the generator fills 4 SA-2/SA-3 batteries there.)
ROLLBACK_SAM_FLOOR = 3

#: Enemy fighter airframes that still justify holding an air-superiority fight.
AIR_THREAT_FLOOR = 8

#: Fraction of the enemy fighter baseline still flying for the air threat to count as
#: "present" (together with the absolute floor above).
AIR_THREAT_RATIO = 0.5

#: Stay in Rollback while the enemy IADS is at or above this fraction of its turn-0
#: strength.
IADS_ROLLBACK_HOLD = 0.5

#: Asymmetric regression threshold (S3.3): falling *back* from Interdiction to
#: Rollback requires the IADS to climb past this margin, not merely re-cross the hold
#: line -- a real rebuild, not sensor noise. Unused while regression is off (v1).
IADS_ROLLBACK_REENTER = 0.6

#: The Offensive phase needs the IADS below this fraction of baseline.
IADS_OFFENSIVE_CEILING = 0.3

#: Mean blue front-line progress (fraction of route length) gained since turn 0 that
#: counts as "the front is advancing".
FRONT_ADVANCE_EPSILON = 0.05

#: Min turns a phase holds before any transition is considered (S3.3 hysteresis).
PHASE_MIN_DWELL_TURNS = 2


@dataclass(frozen=True)
class ZoneAnchor:
    """A point a zone hangs off: a control point by name, or theater ``x``/``y``.

    A CP name resolves at runtime so the zone follows the campaign's real laydown;
    explicit coordinates are the fallback for a point anchored off-base. Used for a
    circle/box center and for each vertex of a corridor's ``path``.
    """

    cp: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None


@dataclass(frozen=True)
class RestrictedZone:
    """A shape where offensive tasking is forbidden (authored phases, W4).

    ``kind`` selects the geometry (all authored in NM, resolved to theater metres):

    * ``circle`` -- ``center_cp`` (or ``x``/``y``) + ``radius_nm``. The original
      shape; a zone block with only ``radius_nm`` + a center parses to this, so the
      4 Vietnam campaigns are byte-identical.
    * ``box`` -- a rotatable rectangle: ``center`` + ``width_nm`` x ``height_nm``,
      optional ``heading`` degrees (0 = axis-aligned). The Nevada range / a Route
      Package rectangle.
    * ``corridor`` -- a lane: a ``path`` of >=2 anchors + ``corridor_width_nm`` (a
      buffered polyline). An ingress route / the Ho Chi Minh trail.
    * ``drawing`` -- geometry read from a shape *drawn in the campaign .miz's Mission
      Editor* (Path B): ``from_drawing`` names the drawing, resolved against
      ``theater.zone_drawings``. A drawn Circle -> circle, a FreeFormPolygon -> a
      polygon area -- so an author traces the zone instead of typing coordinates.

    Box and corridor require a ``name`` (there is no CP to borrow one from).
    """

    kind: str = "circle"
    name: str = ""
    #: circle / box center anchor
    radius_nm: float = 0.0
    center_cp: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None
    #: box extents (NM) + rotation (degrees clockwise from north; 0 = axis-aligned)
    width_nm: float = 0.0
    height_nm: float = 0.0
    heading: float = 0.0
    #: corridor centerline vertices + full lane width (NM)
    path: tuple[ZoneAnchor, ...] = ()
    corridor_width_nm: float = 0.0
    #: name of the Mission-Editor drawing to read geometry from (kind == "drawing")
    drawing: Optional[str] = None


@dataclass(frozen=True)
class PhaseCondition:
    """An ``advance_when`` condition set: ANY satisfied field advances the arc.

    ``min_turn`` here is an acceleration pin *inside* the condition; the next
    phase's own ``min_turn`` is the scheduled escalation date. ``blue_will_below``
    couples escalation to the W1 political-will economy (Washington's patience for
    restraint runs out); ``enemy_iads_below`` releases escalation on rollback
    progress (ratio vs. the turn-0 baseline). ``red_resolve_below`` reads Hanoi's
    Regime Resolve and ``capture_cp`` a named control point falling to BLUE --
    both usable as ``advance_when`` triggers and as objective ``done_when`` ticks.
    """

    min_turn: Optional[int] = None
    blue_will_below: Optional[float] = None
    enemy_iads_below: Optional[float] = None
    red_resolve_below: Optional[float] = None
    capture_cp: Optional[str] = None


@dataclass(frozen=True)
class PhaseObjective:
    """One line of a phase's objectives checklist (P2 'objectives', display).

    ``done_when`` is an optional :class:`PhaseCondition` evaluated live for the
    expander tick; None means a display-only bullet (guidance the engine can't
    measure, e.g. "respect the sanctuaries").
    """

    text: str
    done_when: Optional[PhaseCondition] = None


@dataclass(frozen=True)
class CampaignPhase:
    """A doctrine-like profile active for part of a campaign (spec S2.1).

    Tier 0 fills only key/name/narrative/emphasis; the authored tier (P2/W4) adds
    the transition fields (``min_turn``, ``advance_when``) and the ROE payload
    (``restricted_zones``, ``locked_target_classes``).
    ``emphasis`` is the full ordering of ``PlanNextAction``'s *offensive* root
    methods by class name -- the soft reweight of S4. Kept as names so this module
    never imports the commander (no cycles); ``nextaction.py`` resolves them and a
    test locks the two in sync.
    """

    key: str
    name: str
    narrative: str
    emphasis: tuple[str, ...] = ()
    #: Earliest campaign turn this phase may begin (authored arcs; 0 = no pin).
    min_turn: int = 0
    #: Optional acceleration conditions to LEAVE this phase (authored arcs).
    advance_when: Optional[PhaseCondition] = None
    #: Shapes (circle/box/corridor) where offensive tasking is forbidden while this
    #: phase is active.
    restricted_zones: tuple[RestrictedZone, ...] = ()
    #: Strike-target classes still locked in this phase (TGO ``category`` strings,
    #: plus the special ``"airfield"`` for OCA against a control point).
    locked_target_classes: tuple[str, ...] = ()
    #: Free-fire zones -- inverted ROE (COIN). When non-empty, the polarity flips:
    #: fixed strike targets are off-limits EVERYWHERE except inside one of these
    #: cleared pockets (the whole map goes weapons-hold with a few hot pockets).
    #: Shape-typed like ``restricted_zones``; a ``restricted_zone`` still carves a
    #: no-strike hole *inside* a pocket, and the front-line fight stays legal.
    free_fire_zones: tuple[RestrictedZone, ...] = ()
    #: The phase's objectives checklist (P2 'objectives'): what this phase is FOR,
    #: shown with live done-ticks in the arc expander. Display guidance, never a
    #: gate -- transitions stay owned by min_turn/advance_when (or Tier-0
    #: inference).
    objectives: tuple[PhaseObjective, ...] = ()
    #: True for phases parsed from a campaign ``phases:`` block.
    authored: bool = False
    #: W6 red-tempo levers (authored-only; Tier-0 phases never set them -- see
    #: docs/dev/design/414th-vietnam-red-tempo-notes.md). ``trail_surge``
    #: multiplies the trail-convoy budget while the phase holds (bombing halts
    #: were logistics windows); ``ground_offensive_turns`` flips RED's front
    #: stances aggressive for N turns from phase entry (the Tet/Easter pulse --
    #: the W2b static-front clamp still bounds the movement); ``resolve_regen``
    #: is Regime Resolve regained per turn while the phase holds (Hanoi recovers
    #: when unbombed, so a long halt costs Washington leverage).
    trail_surge: float = 1.0
    ground_offensive_turns: int = 0
    resolve_regen: float = 0.0


#: PlanNextAction's offensive tail in its stock order. The fixed reactive prefix
#: (TheaterSupport / ProtectAirSpace / DefendBases) and the RecoverySupport tail are
#: NOT listed -- phases may never touch them (the S17 boundary).
OFFENSIVE_METHODS = (
    "InterdictReinforcements",
    "AttackBattlePositions",
    "CaptureBases",
    "PlanFrontLineCas",
    "AttackAirInfrastructure",
    "AttackBuildings",
    "AttackShips",
    "DegradeIads",
)

ROLLBACK = CampaignPhase(
    key="rollback",
    name="Air Superiority",
    narrative="Win the air: degrade the SAM belt and blunt the enemy fighter force.",
    objectives=(
        PhaseObjective(
            f"Roll the SAM belt back below {IADS_ROLLBACK_HOLD:.0%} strength",
            done_when=PhaseCondition(enemy_iads_below=IADS_ROLLBACK_HOLD),
        ),
        PhaseObjective("Blunt the enemy fighter force (sweeps, OCA, intercepts)"),
    ),
    emphasis=(
        "DegradeIads",
        "AttackAirInfrastructure",
        "InterdictReinforcements",
        "AttackBattlePositions",
        "CaptureBases",
        "PlanFrontLineCas",
        "AttackShips",
        "AttackBuildings",
    ),
)

INTERDICTION = CampaignPhase(
    key="interdiction",
    name="Interdiction",
    narrative="The air is largely won: choke enemy reinforcement and logistics.",
    objectives=(
        PhaseObjective(
            f"Grind the enemy IADS below {IADS_OFFENSIVE_CEILING:.0%} strength",
            done_when=PhaseCondition(enemy_iads_below=IADS_OFFENSIVE_CEILING),
        ),
        PhaseObjective("Choke reinforcement: kill convoys and rear-area depots"),
    ),
    emphasis=(
        "InterdictReinforcements",
        "AttackAirInfrastructure",
        "AttackBattlePositions",
        "AttackShips",
        "CaptureBases",
        "PlanFrontLineCas",
        "AttackBuildings",
        "DegradeIads",
    ),
)

OFFENSIVE = CampaignPhase(
    key="offensive",
    name="Offensive",
    narrative="Air won and the ground fight is live: take ground.",
    objectives=(
        PhaseObjective("Take enemy bases and push the front to the victory line"),
        PhaseObjective("Keep the won air: CAS flows only while the SAMs stay down"),
    ),
    # CaptureBases stays ahead of PlanFrontLineCas (losing fronts keep first claim
    # on the CAS jets -- the stock-order comment in nextaction.py).
    emphasis=(
        "CaptureBases",
        "PlanFrontLineCas",
        "AttackBattlePositions",
        "InterdictReinforcements",
        "AttackAirInfrastructure",
        "AttackShips",
        "DegradeIads",
        "AttackBuildings",
    ),
)

PHASES: dict[str, CampaignPhase] = {
    p.key: p for p in (ROLLBACK, INTERDICTION, OFFENSIVE)
}

#: Monotonic-forward ordering (S3.3): most narratives don't un-happen. Regression is
#: opt-in per campaign (authored, P2) and off in v1.
_PHASE_ORDER = {"rollback": 0, "interdiction": 1, "offensive": 2}


@dataclass
class PhaseBaseline:
    """Turn-0 snapshots the ratio math runs against (spec S3.1 'Baselines').

    Nothing in the engine persists an initial front line or IADS count, so the
    classifier snapshots them the first time it runs (turn 0 for a new game; first
    load for a pre-feature save, which the spec documents as acceptable).
    """

    sam_sites: int
    enemy_fighters: int
    #: Blue route-progress fraction per front, keyed "blue_cp_id:red_cp_id".
    front_fractions: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class PhaseMetrics:
    """One turn's classifier inputs, all derived from pre-existing accessors."""

    sam_baseline: int
    sam_alive: int
    iads_ratio: float
    fighters_baseline: int
    fighters_alive: int
    air_threat_present: bool
    front_delta: float
    recent_capture: bool
    base_ratio: float


def classify(m: PhaseMetrics) -> str:
    """The S3.2 phase boundaries: first match wins (hysteresis applied by caller).

    The absolute-SAM-floor gate is checked inside the Rollback condition: a theater
    whose turn-0 belt never met the floor cannot be in Rollback on IADS grounds, but
    real enemy air still holds the air-superiority fight (the pilot's 'Air
    Superiority (fighter)' opening). The peer-fight guard falls out of the same
    shape: Rollback only releases when the IADS is down AND the air threat is gone.
    """
    rollback_reachable = m.sam_baseline >= ROLLBACK_SAM_FLOOR
    if (rollback_reachable and m.iads_ratio >= IADS_ROLLBACK_HOLD) or (
        m.air_threat_present
    ):
        return "rollback"
    if m.iads_ratio < IADS_OFFENSIVE_CEILING and (
        m.front_delta >= FRONT_ADVANCE_EPSILON or m.recent_capture
    ):
        return "offensive"
    return "interdiction"


def _next_phase_key(
    current: Optional[str],
    entered_on_turn: Optional[int],
    turn: int,
    m: PhaseMetrics,
    allow_regression: bool = False,
) -> str:
    """Apply the S3.3 hysteresis around :func:`classify`.

    ``allow_regression`` is the authored-tier flag (P2); v1 callers never set it.
    When it is set, falling back to Rollback additionally requires the IADS to have
    climbed past the asymmetric :data:`IADS_ROLLBACK_REENTER` margin.
    """
    target = classify(m)
    if current is None or current not in _PHASE_ORDER:
        return target
    if turn - (entered_on_turn or 0) < PHASE_MIN_DWELL_TURNS:
        return current
    if _PHASE_ORDER[target] < _PHASE_ORDER[current]:
        if not allow_regression:
            return current
        if target == "rollback" and m.iads_ratio < IADS_ROLLBACK_REENTER:
            return current
    return target


# --- live-state collection (S3.1 signals; accessors confirmed by the pilot) ---------


def _enemy_sam_sites(game: "Game") -> int:
    """Alive enemy long+medium SAM sites: TGOs tasked LORAD / MERAD.

    Bands by the TGO's ``GroupTask`` — the exact target set ``degradeiads.py`` rolls
    back — per the spec §3.1 correction from the all-66 engine re-run (#379):
    ``IadsRole`` CANNOT band this (its ``SAM`` role swallows SHORAD and its ``EWR``
    role swallows AAA/navy). EWR stays deliberately excluded (author-noise);
    SHORAD/point defense likewise, by construction of the LORAD/MERAD set.
    """
    from game.data.groups import GroupTask
    from game.theater.player import Player

    count = 0
    for tgo in game.theater.ground_objects:
        if tgo.task not in (GroupTask.LORAD, GroupTask.MERAD):
            continue
        if tgo.is_friendly(Player.BLUE):
            continue
        if any(unit.alive for group in tgo.groups for unit in group.units):
            count += 1
    return count


def _enemy_fighters(game: "Game") -> int:
    """Enemy owned airframes in air-superiority squadrons (S3.1 'enemy_fighters')."""
    from game.ato.flighttype import FlightType
    from game.theater.player import Player

    air_superiority = {
        FlightType.BARCAP,
        FlightType.TARCAP,
        FlightType.SWEEP,
        FlightType.ESCORT,
        FlightType.INTERCEPTION,
    }
    return sum(
        squadron.owned_aircraft
        for squadron in game.air_wing_for(Player.RED).iter_squadrons()
        if squadron.primary_task in air_superiority
    )


def _front_fractions(game: "Game") -> dict[str, float]:
    """Blue progress fraction per active front, keyed stably across turns."""
    fractions: dict[str, float] = {}
    for front in game.theater.conflicts():
        key = f"{front.blue_cp.id}:{front.red_cp.id}"
        length = front.route_length
        if length > 0:
            fractions[key] = front._blue_route_progress / length
    return fractions


def _base_counts(game: "Game") -> tuple[int, int]:
    """(blue, total non-neutral) control points."""
    from game.theater.player import Player

    blue = 0
    total = 0
    for cp in game.theater.controlpoints:
        if cp.captured is Player.NEUTRAL:
            continue
        total += 1
        if cp.captured is Player.BLUE:
            blue += 1
    return blue, total


def snapshot_baseline(game: "Game") -> PhaseBaseline:
    return PhaseBaseline(
        sam_sites=_enemy_sam_sites(game),
        enemy_fighters=_enemy_fighters(game),
        front_fractions=_front_fractions(game),
    )


def collect_metrics(game: "Game", baseline: PhaseBaseline) -> PhaseMetrics:
    sam_alive = _enemy_sam_sites(game)
    iads_ratio = sam_alive / baseline.sam_sites if baseline.sam_sites else 0.0

    fighters_alive = _enemy_fighters(game)
    fighter_ratio = (
        fighters_alive / baseline.enemy_fighters if baseline.enemy_fighters else 0.0
    )
    air_threat_present = (
        fighters_alive >= AIR_THREAT_FLOOR and fighter_ratio >= AIR_THREAT_RATIO
    )

    # Mean signed front movement vs. the turn-0 anchor, over fronts present in both
    # snapshots. A front that appeared later (post-capture) simply doesn't vote.
    deltas = []
    for key, fraction in _front_fractions(game).items():
        anchor = baseline.front_fractions.get(key)
        if anchor is not None:
            deltas.append(fraction - anchor)
    front_delta = sum(deltas) / len(deltas) if deltas else 0.0

    sitrep = getattr(game, "last_sitrep", None)
    recent_capture = bool(sitrep and getattr(sitrep, "captured", None))

    blue, total = _base_counts(game)
    base_ratio = blue / total if total else 0.0

    return PhaseMetrics(
        sam_baseline=baseline.sam_sites,
        sam_alive=sam_alive,
        iads_ratio=iads_ratio,
        fighters_baseline=baseline.enemy_fighters,
        fighters_alive=fighters_alive,
        air_threat_present=air_threat_present,
        front_delta=front_delta,
        recent_capture=recent_capture,
        base_ratio=base_ratio,
    )


def legibility(phase: CampaignPhase, m: PhaseMetrics) -> str:
    """The S3.4 'why' string -- an inferred phase must explain itself."""
    if m.sam_baseline:
        iads = f"enemy IADS {round(m.iads_ratio * 100)}%"
    else:
        iads = "no enemy SAM belt"
    air = "air threat up" if m.air_threat_present else "air threat low"
    if m.front_delta >= FRONT_ADVANCE_EPSILON:
        front = "front advancing"
    elif m.front_delta <= -FRONT_ADVANCE_EPSILON:
        front = "front giving ground"
    else:
        front = "front static"
    return f"{phase.name} — {iads} · {air} · {front}"


# --- the per-turn entry point --------------------------------------------------------


def update_campaign_phase(game: "Game") -> None:
    """Resolve this turn's phase. Called from ``Game.initialize_turn`` (idempotent).

    Setting off => all phase state cleared, so consumers (planner emphasis,
    kneeboard, status band) see 'no phase' and behave stock. The baseline is
    snapshotted lazily on the first gated run: turn 0 for a new campaign (the IADS
    network exists by then -- ``begin_turn_0`` builds it before ``initialize_turn``),
    first load for a pre-feature save (spec S5: re-snapshot is the accepted
    migration).
    """
    if not getattr(game.settings, "campaign_phases", False):
        game.current_phase_key = None
        game.phase_entered_on_turn = None
        game.phase_status_line = None
        return

    baseline = getattr(game, "phase_baseline", None)
    if baseline is None:
        baseline = snapshot_baseline(game)
        game.phase_baseline = baseline

    # An authored arc (a campaign `phases:` block, P2/W4) overrides Tier-0
    # inference entirely -- the author owns the transitions.
    arc = authored_arc_for(game)
    if arc:
        _update_authored_phase(game, arc, baseline)
        return

    metrics = collect_metrics(game, baseline)
    current = getattr(game, "current_phase_key", None)
    new_key = _next_phase_key(
        current, getattr(game, "phase_entered_on_turn", None), game.turn, metrics
    )
    if new_key != current:
        game.current_phase_key = new_key
        game.phase_entered_on_turn = game.turn
        # Announce transitions, not the campaign-start assignment (turn 0 already
        # tells the player the opening phase via the status surfaces). initialize_turn
        # re-runs never repeat this: same turn re-inits resolve to the same phase.
        if current is not None:
            phase = PHASES[new_key]
            game.message(
                f"Campaign enters {phase.name}",
                f"{phase.narrative} ({legibility(phase, metrics)})",
            )
    game.phase_status_line = legibility(PHASES[new_key], metrics)


def active_phase(game: "Game") -> Optional[CampaignPhase]:
    """The phase consumers read (planner emphasis, kneeboard, server payload).

    Authored keys resolve against the campaign's arc first; a stale authored key
    (the campaign's ``phases:`` block was edited or removed under a save) resolves
    to None here and Tier 0 reassigns on the next ``initialize_turn`` -- the spec
    S5 "definitions re-derived at load" behaviour.
    """
    if not getattr(game.settings, "campaign_phases", False):
        return None
    key = getattr(game, "current_phase_key", None)
    if key is None:
        return None
    for phase in authored_arc_for(game):
        if phase.key == key:
            return phase
    return PHASES.get(key)


# --- the authored tier (P2) + the ROE escalation layer (W4) --------------------------

#: Authored-arc cache keyed by campaign name. Definitions live in the campaign
#: YAML and are re-derived per process (never pickled); tests may inject here.
_ARC_CACHE: dict[str, tuple[CampaignPhase, ...]] = {}


def _parse_anchor(node: object) -> ZoneAnchor:
    """A corridor ``path`` node: a CP name string, or an ``{x, y}`` mapping."""
    if isinstance(node, str):
        return ZoneAnchor(cp=node)
    if isinstance(node, dict) and "x" in node and "y" in node:
        return ZoneAnchor(x=float(node["x"]), y=float(node["y"]))
    raise ValueError(f"corridor path anchor must be a CP name or {{x, y}}: {node!r}")


def _parse_restricted_zone(zone: object) -> RestrictedZone:
    """Parse one ``restricted_zones`` entry into a shape-typed ``RestrictedZone``.

    ``shape`` defaults to ``circle`` so a legacy ``{center, radius_nm}`` block is
    unchanged. Raises on structurally invalid data so a bad campaign fails loudly
    in tests rather than silently losing a zone.
    """
    if not isinstance(zone, dict):
        raise ValueError(f"restricted_zones: entry must be a mapping: {zone!r}")
    if zone.get("from_drawing"):
        ref = str(zone["from_drawing"])
        # The drawing name doubles as the display label unless one is given.
        return RestrictedZone(
            kind="drawing", name=str(zone.get("name", ref)), drawing=ref
        )
    kind = str(zone.get("shape", "circle")).lower()
    name = str(zone.get("name", ""))
    has_center = bool(zone.get("center")) or ("x" in zone and "y" in zone)
    if kind == "circle":
        if "radius_nm" not in zone or not has_center:
            raise ValueError(
                f"restricted_zones circle needs radius_nm and a center "
                f"(CP name) or x/y: {zone!r}"
            )
        return RestrictedZone(
            kind="circle",
            name=name,
            radius_nm=float(zone["radius_nm"]),
            center_cp=zone.get("center"),
            x=zone.get("x"),
            y=zone.get("y"),
        )
    if kind == "box":
        if not name:
            raise ValueError(f"restricted_zones box needs a name: {zone!r}")
        if "width_nm" not in zone or "height_nm" not in zone or not has_center:
            raise ValueError(
                f"restricted_zones box needs width_nm, height_nm and a center "
                f"(CP name) or x/y: {zone!r}"
            )
        return RestrictedZone(
            kind="box",
            name=name,
            center_cp=zone.get("center"),
            x=zone.get("x"),
            y=zone.get("y"),
            width_nm=float(zone["width_nm"]),
            height_nm=float(zone["height_nm"]),
            heading=float(zone.get("heading", 0.0)),
        )
    if kind == "corridor":
        if not name:
            raise ValueError(f"restricted_zones corridor needs a name: {zone!r}")
        path_raw = zone.get("path")
        if (
            not isinstance(path_raw, list)
            or len(path_raw) < 2
            or "width_nm" not in zone
        ):
            raise ValueError(
                f"restricted_zones corridor needs width_nm and a path of >=2 "
                f"anchors (CP name or {{x, y}}): {zone!r}"
            )
        return RestrictedZone(
            kind="corridor",
            name=name,
            path=tuple(_parse_anchor(node) for node in path_raw),
            corridor_width_nm=float(zone["width_nm"]),
        )
    raise ValueError(
        f"restricted_zones: unknown shape {kind!r} (want circle, box, or corridor)"
    )


def _parse_condition(raw: object) -> Optional[PhaseCondition]:
    """Parse an ``advance_when`` / objective ``done_when`` mapping, or None."""
    if not raw:
        return None
    if not isinstance(raw, dict):
        raise ValueError(f"condition must be a mapping: {raw!r}")
    return PhaseCondition(
        min_turn=raw.get("min_turn"),
        blue_will_below=raw.get("blue_will_below"),
        enemy_iads_below=raw.get("enemy_iads_below"),
        red_resolve_below=raw.get("red_resolve_below"),
        capture_cp=raw.get("capture_cp"),
    )


def parse_phases(raw: object) -> tuple[CampaignPhase, ...]:
    """Parse a campaign YAML ``phases:`` block into authored phases.

    ``emphasis`` names a Tier-0 phase key to borrow that planner ordering
    (``rollback`` / ``interdiction`` / ``offensive``); omitted means no planner
    bias for that phase. Raises on structurally invalid entries so a bad campaign
    fails loudly in tests rather than silently losing its arc.
    """
    if not raw:
        return ()
    if not isinstance(raw, list):
        raise ValueError(f"phases: must be a list, got {type(raw).__name__}")
    phases = []
    for entry in raw:
        if not isinstance(entry, dict) or "key" not in entry:
            raise ValueError(f"phases: entry needs a 'key': {entry!r}")
        emphasis_key = entry.get("emphasis")
        if emphasis_key is not None and emphasis_key not in PHASES:
            raise ValueError(
                f"phases: unknown emphasis {emphasis_key!r} (want one of "
                f"{sorted(PHASES)})"
            )
        emphasis = PHASES[emphasis_key].emphasis if emphasis_key else ()
        zones = [
            _parse_restricted_zone(zone) for zone in entry.get("restricted_zones") or []
        ]
        free_fire = [
            _parse_restricted_zone(zone) for zone in entry.get("free_fire_zones") or []
        ]
        condition = _parse_condition(entry.get("advance_when"))
        objectives = []
        for objective in entry.get("objectives") or []:
            if isinstance(objective, str):
                objectives.append(PhaseObjective(text=objective))
            elif isinstance(objective, dict) and "text" in objective:
                objectives.append(
                    PhaseObjective(
                        text=str(objective["text"]),
                        done_when=_parse_condition(objective.get("done_when")),
                    )
                )
            else:
                raise ValueError(
                    f"objectives: entry must be a string or a mapping with "
                    f"'text': {objective!r}"
                )
        tempo = entry.get("red_tempo") or {}
        if not isinstance(tempo, dict):
            raise ValueError(f"red_tempo: must be a mapping: {tempo!r}")
        phases.append(
            CampaignPhase(
                key=str(entry["key"]),
                name=str(entry.get("name", entry["key"])),
                narrative=str(entry.get("narrative", "")),
                emphasis=emphasis,
                min_turn=int(entry.get("min_turn", 0)),
                advance_when=condition,
                restricted_zones=tuple(zones),
                free_fire_zones=tuple(free_fire),
                locked_target_classes=tuple(entry.get("locked_targets") or ()),
                objectives=tuple(objectives),
                authored=True,
                trail_surge=float(tempo.get("trail_surge", 1.0)),
                ground_offensive_turns=int(tempo.get("ground_offensive", 0)),
                resolve_regen=float(tempo.get("resolve_regen", 0.0)),
            )
        )
    return tuple(phases)


def authored_arc_for(game: "Game") -> tuple[CampaignPhase, ...]:
    """The campaign's authored arc, or () for Tier-0 campaigns.

    Re-derived from the campaign YAML by name (spec S5: definitions are never
    pickled) and cached per process. Any lookup/parse failure degrades to Tier 0
    with a log, never a crash -- an old save whose campaign was removed still
    plays.
    """
    name = getattr(game, "campaign_name", None)
    if not name:
        return ()
    if name in _ARC_CACHE:
        return _ARC_CACHE[name]
    arc: tuple[CampaignPhase, ...] = ()
    try:
        import yaml

        from game.campaignloader.campaign import Campaign

        for path in Campaign.iter_campaign_defs():
            try:
                with path.open(encoding="utf-8") as campaign_file:
                    data = yaml.safe_load(campaign_file)
            except Exception:  # noqa: BLE001 -- one bad yaml must not kill the scan
                continue
            if isinstance(data, dict) and data.get("name") == name:
                arc = parse_phases(data.get("phases"))
                break
    except Exception:  # noqa: BLE001
        logging.exception("Campaign phases: authored-arc lookup failed for %r", name)
        arc = ()
    _ARC_CACHE[name] = arc
    return arc


def _condition_satisfied(
    game: "Game", condition: Optional[PhaseCondition], baseline: PhaseBaseline
) -> bool:
    """ANY specified field of an ``advance_when`` set advances the arc."""
    if condition is None:
        return False
    if condition.min_turn is not None and game.turn >= condition.min_turn:
        return True
    if condition.blue_will_below is not None:
        will = getattr(game.blue, "political_will", None)
        if will is not None and will < condition.blue_will_below:
            return True
    if condition.enemy_iads_below is not None and baseline.sam_sites:
        ratio = _enemy_sam_sites(game) / baseline.sam_sites
        if ratio < condition.enemy_iads_below:
            return True
    if condition.red_resolve_below is not None:
        resolve = getattr(getattr(game, "red", None), "political_will", None)
        if resolve is not None and resolve < condition.red_resolve_below:
            return True
    if condition.capture_cp is not None:
        for cp in game.theater.controlpoints:
            if cp.name != condition.capture_cp:
                continue
            captured = getattr(cp, "captured", None)
            if captured is not None and captured.is_blue:
                return True
    return False


def _update_authored_phase(
    game: "Game", arc: tuple[CampaignPhase, ...], baseline: PhaseBaseline
) -> None:
    """Advance an authored arc: sequential, forward-only, author-owned.

    Move from phase i to i+1 when the *next* phase's ``min_turn`` is reached
    (the scheduled escalation date; 0 = no schedule) OR the *current* phase's
    ``advance_when`` is satisfied (the acceleration coupling). A save that adopts
    an arc mid-campaign (or whose stored key vanished from an edited arc) enters
    at the latest turn-eligible phase.
    """
    keys = [phase.key for phase in arc]
    current = getattr(game, "current_phase_key", None)
    if current in keys:
        index = keys.index(current)
    else:
        index = 0
        for i, phase in enumerate(arc):
            if phase.min_turn and game.turn >= phase.min_turn:
                index = i
    while index + 1 < len(arc):
        next_phase = arc[index + 1]
        scheduled = next_phase.min_turn > 0 and game.turn >= next_phase.min_turn
        accelerated = _condition_satisfied(game, arc[index].advance_when, baseline)
        if not (scheduled or accelerated):
            break
        index += 1
    phase = arc[index]
    if phase.key != current:
        game.current_phase_key = phase.key
        game.phase_entered_on_turn = game.turn
        if current is not None:
            game.message(f"Campaign enters {phase.name}", phase.narrative)
    game.phase_status_line = f"{phase.name} — phase {index + 1} of {len(arc)}" + (
        " · ROE restrictions active"
        if phase.restricted_zones or phase.free_fire_zones
        else ""
    )


def _target_class(target: object) -> Optional[str]:
    """The ``target_release`` class of a mission target.

    Control points (OCA) are the special ``"airfield"`` class; ground objects use
    their ``category`` string (power, factory, fuel, ammo, ware, comms, aa, ...).
    Other targets (front lines, convoys) have no class and are never class-gated.
    """
    from game.theater import ControlPoint
    from game.theater.theatergroundobject import TheaterGroundObject

    if isinstance(target, ControlPoint):
        return "airfield"
    if isinstance(target, TheaterGroundObject):
        return target.category
    return None


@dataclass(frozen=True)
class ResolvedZone:
    """A phase zone resolved to concrete theater geometry (metres, x/y floats).

    Shape-agnostic for its consumers: :meth:`contains` gates the AI planner and
    the player will-penalty; ``center_xy``/``radius_m``/``outline_xy`` feed the two
    painters (the ME F10-map drawing and the web map layer), which build DCS
    ``Point``/``LatLng`` from these raw coordinates. ``outline_xy`` is the polygon
    ring for box/corridor and empty for a circle (drawn natively both places).
    """

    name: str
    kind: str
    center_xy: tuple[float, float]
    radius_m: float = 0.0
    outline_xy: tuple[tuple[float, float], ...] = ()
    #: shapely polygon for box/corridor containment; None for a circle (distance).
    geometry: Optional[BaseGeometry] = field(default=None, repr=False, compare=False)

    def contains(self, position: object) -> bool:
        px = float(getattr(position, "x"))
        py = float(getattr(position, "y"))
        if self.kind == "circle":
            cx, cy = self.center_xy
            return math.hypot(px - cx, py - cy) <= self.radius_m
        if self.geometry is None:
            return False
        return bool(self.geometry.contains(ShapelyPoint(px, py)))


def _anchor_xy(game: "Game", anchor: ZoneAnchor) -> Optional[tuple[float, float]]:
    """Resolve a :class:`ZoneAnchor` to theater ``(x, y)`` metres, or None.

    A CP name absent from this theater resolves to nothing (logged) rather than
    crashing -- authored data must never brick a campaign.
    """
    if anchor.cp is not None:
        for cp in game.theater.controlpoints:
            if cp.name == anchor.cp:
                return (cp.position.x, cp.position.y)
        logging.warning(
            "Restricted zone anchor: no control point named %r in this theater",
            anchor.cp,
        )
        return None
    if anchor.x is not None and anchor.y is not None:
        return (float(anchor.x), float(anchor.y))
    return None


def _box_corners(
    cx: float, cy: float, width_m: float, height_m: float, heading_deg: float
) -> list[tuple[float, float]]:
    """The four rotated corners of a box (DCS x=north, y=east; heading clockwise)."""
    rad = math.radians(heading_deg)
    cos_h, sin_h = math.cos(rad), math.sin(rad)
    hw, hh = width_m / 2.0, height_m / 2.0
    corners = []
    for along, perp in ((hw, hh), (hw, -hh), (-hw, -hh), (-hw, hh)):
        corners.append(
            (cx + along * cos_h - perp * sin_h, cy + along * sin_h + perp * cos_h)
        )
    return corners


def _resolve_drawing_zone(game: "Game", zone: RestrictedZone) -> Optional[ResolvedZone]:
    """Resolve a ``from_drawing`` zone against ``theater.zone_drawings`` (Path B).

    A drawn Circle becomes a circle ResolvedZone; a FreeFormPolygon becomes a polygon
    area (shapely-gated, painted as an outline). A reference to a name that isn't in
    the campaign's drawings resolves to nothing (logged) -- never a crash.
    """
    theater = getattr(game, "theater", None)
    drawings = getattr(theater, "zone_drawings", None) or {}
    drawn = drawings.get(zone.drawing)
    if drawn is None:
        logging.warning(
            "Restricted zone %r references ME drawing %r not found in this campaign",
            zone.name,
            zone.drawing,
        )
        return None
    if drawn.kind == "circle":
        return ResolvedZone(
            name=zone.name or drawn.name,
            kind="circle",
            center_xy=drawn.center_xy,
            radius_m=drawn.radius_m,
        )
    if len(drawn.outline_xy) < 3:
        return None
    return ResolvedZone(
        name=zone.name or drawn.name,
        kind="polygon",
        center_xy=drawn.center_xy,
        outline_xy=drawn.outline_xy,
        geometry=Polygon(drawn.outline_xy),
    )


def _resolve_zone(game: "Game", zone: RestrictedZone) -> Optional[ResolvedZone]:
    """Resolve one authored zone to a :class:`ResolvedZone`, or None if unanchored."""
    if zone.kind == "drawing":
        return _resolve_drawing_zone(game, zone)
    if zone.kind == "box":
        center = _anchor_xy(game, ZoneAnchor(cp=zone.center_cp, x=zone.x, y=zone.y))
        if center is None:
            return None
        corners = _box_corners(
            center[0],
            center[1],
            zone.width_nm * 1852.0,
            zone.height_nm * 1852.0,
            zone.heading,
        )
        return ResolvedZone(
            name=zone.name or "Restricted zone",
            kind="box",
            center_xy=center,
            outline_xy=tuple(corners),
            geometry=Polygon(corners),
        )
    if zone.kind == "corridor":
        points = [
            xy for xy in (_anchor_xy(game, a) for a in zone.path) if xy is not None
        ]
        if len(points) < 2:
            logging.warning(
                "Restricted corridor %r: fewer than 2 anchors resolved", zone.name
            )
            return None
        poly = LineString(points).buffer(zone.corridor_width_nm * 1852.0 / 2.0)
        ring = list(poly.exterior.coords)
        if len(ring) > 1 and ring[0] == ring[-1]:
            ring = ring[:-1]
        cx = sum(p[0] for p in points) / len(points)
        cy = sum(p[1] for p in points) / len(points)
        return ResolvedZone(
            name=zone.name or "Restricted zone",
            kind="corridor",
            center_xy=(cx, cy),
            outline_xy=tuple((float(x), float(y)) for x, y in ring),
            geometry=poly,
        )
    # Default / "circle".
    center = _anchor_xy(game, ZoneAnchor(cp=zone.center_cp, x=zone.x, y=zone.y))
    if center is None:
        return None
    return ResolvedZone(
        name=zone.name or zone.center_cp or "Restricted zone",
        kind="circle",
        center_xy=center,
        radius_m=zone.radius_nm * 1852.0,
    )


def _resolve_zone_list(
    game: "Game", zones: tuple[RestrictedZone, ...]
) -> list[ResolvedZone]:
    """Resolve a tuple of authored zones, dropping any that won't anchor."""
    resolved = []
    for zone in zones:
        result = _resolve_zone(game, zone)
        if result is not None:
            resolved.append(result)
    return resolved


def _resolved_zones(game: "Game", phase: CampaignPhase) -> list[ResolvedZone]:
    """Resolve a phase's restricted zones to concrete geometry."""
    return _resolve_zone_list(game, phase.restricted_zones)


def active_restricted_zones(game: "Game") -> list[ResolvedZone]:
    """The active phase's restricted (no-strike) zones -- map layer / server feed."""
    phase = active_phase(game)
    if phase is None:
        return []
    return _resolve_zone_list(game, phase.restricted_zones)


def active_free_fire_zones(game: "Game") -> list[ResolvedZone]:
    """The active phase's free-fire (weapons-free) zones -- inverted ROE (COIN).

    Non-empty means the whole map is weapons-hold except these cleared pockets;
    fed to the green map layer + the F10/ME painter alongside the red restricted
    zones. Empty for every phase that doesn't author ``free_fire_zones``.
    """
    phase = active_phase(game)
    if phase is None:
        return []
    return _resolve_zone_list(game, phase.free_fire_zones)


def roe_blocks_target(game: "Game", target: object) -> bool:
    """True when the active phase's ROE forbids offensive tasking at ``target``.

    The AI planner gate (read in ``PackagePlanningTask.fulfill_mission`` next to
    the Vietnam ``tasking_whitelist``): a locked target class is blocked anywhere;
    any target inside an active restricted zone is blocked regardless of class
    (sanctuary airfields fall out of this). BLUE-only by the caller (the ROE is
    Washington's, not Hanoi's). The *player* is never hard-blocked -- their
    enforcement is the will penalty (:func:`count_roe_violations`).
    """
    return roe_restriction_reason(game, target) is not None


def roe_restriction_reason(game: "Game", target: object) -> Optional[str]:
    """Why the ROE forbids ``target`` this phase, or None when it doesn't.

    The player-facing half of :func:`roe_blocks_target` (same logic, same order):
    a class lock reads "factory targets are locked this phase", a zone hit reads
    "inside Hanoi sanctuary" -- so the map badge explains itself instead of a
    bare RESTRICTED (playtest: a locked factory with no circle nearby read as a
    render bug). AAA/armor and other unlocked classes outside the zones return
    None and carry no badge: flak is always fair game.
    """
    phase = active_phase(game)
    if phase is None:
        return None
    target_class = _target_class(target)
    if target_class is not None and target_class in phase.locked_target_classes:
        return f"{target_class} targets are locked this phase"
    position = getattr(target, "position", None)
    if position is None:
        return None
    for zone in _resolved_zones(game, phase):
        if zone.contains(position):
            return f"inside {zone.name}"
    # Inverted ROE (COIN free-fire): with free-fire zones set, a fixed strike
    # target is off-limits UNLESS it sits inside a cleared pocket. Front-line
    # forces / convoys (target_class is None) stay legal -- the ground fight is
    # never weapons-hold. Fail-open if none of the pockets resolved.
    if phase.free_fire_zones and target_class is not None:
        free_fire = _resolve_zone_list(game, phase.free_fire_zones)
        if free_fire and not any(zone.contains(position) for zone in free_fire):
            return "outside the weapons-free area"
    return None


#: Human names for the target_release classes (TGO ``category`` strings plus the
#: special ``"airfield"``); an unlisted class falls back to its raw name.
_CLASS_DISPLAY = {
    "ware": "warehouses",
    "factory": "factories",
    "power": "power plants",
    "oil": "oil facilities",
    "fuel": "fuel depots",
    "ammo": "ammo depots",
    "comms": "comms",
    "commandcenter": "command centers",
    "airfield": "airfields (OCA)",
    "aa": "air defenses",
    "ship": "ships",
    "derrick": "derricks",
}


def _class_display(target_class: str) -> str:
    return _CLASS_DISPLAY.get(target_class, target_class)


def _cleared_classes(game: "Game", phase: CampaignPhase) -> list[str]:
    """Enemy target classes actually present in this theater and NOT locked.

    Derived from the live laydown so the CLEARED list never advertises a class
    the campaign doesn't field. Villages are never advertised as targets.
    """
    present: set[str] = set()
    for cp in game.theater.controlpoints:
        if cp.captured.is_blue or cp.captured.is_neutral:
            continue
        if getattr(cp, "dcs_airport", None) is not None:
            present.add("airfield")
        for tgo in cp.connected_objectives:
            present.add(tgo.category)
    present.discard("village")
    return [
        _class_display(target_class)
        for target_class in sorted(present)
        if target_class not in phase.locked_target_classes
    ]


def _zone_label(zone: ResolvedZone) -> str:
    """A zone's OFF-LIMITS bit: a circle's radius, else the shape name."""
    if zone.kind == "circle":
        return f"{zone.name} {zone.radius_m / 1852.0:.0f} nm"
    return f"{zone.name} ({zone.kind})"


def roe_summary_lines(game: "Game") -> list[tuple[str, str]]:
    """The active phase's ROE, spelled out: what is off limits and what is good.

    Returns ``(label, text)`` rows for the kneeboard cover's CAMPAIGN PHASE band
    -- OFF LIMITS (sanctuary zones with radii), LOCKED (target classes still
    withheld), CLEARED (classes actually present in-theater and released, plus
    the never-gated front-line fight). Empty when no phase is active or the
    phase carries no ROE payload, so non-ROE campaigns see no change.
    """
    phase = active_phase(game)
    if phase is None:
        return []
    if (
        not phase.restricted_zones
        and not phase.locked_target_classes
        and not phase.free_fire_zones
    ):
        return []
    lines: list[tuple[str, str]] = []
    # Inverted ROE (COIN) leads with the dominant rule: weapons-hold everywhere but
    # the cleared pockets.
    free_fire_bits = [_zone_label(zone) for zone in active_free_fire_zones(game)]
    if free_fire_bits:
        lines.append(
            ("WEAPONS FREE", " · ".join(free_fire_bits) + " (all else off-limits)")
        )
    zone_bits = [_zone_label(zone) for zone in _resolved_zones(game, phase)]
    if zone_bits:
        lines.append(("OFF LIMITS", " · ".join(zone_bits)))
    if phase.locked_target_classes:
        lines.append(
            (
                "LOCKED",
                ", ".join(_class_display(c) for c in phase.locked_target_classes),
            )
        )
    cleared = _cleared_classes(game, phase)
    # Front-line forces and convoys are never class-gated (flak is always fair
    # game) -- say so, or a fully locked phase reads as "nothing to fly".
    cleared.append("front-line forces & convoys")
    lines.append(("CLEARED", ", ".join(cleared)))
    return lines


def _arc_for_display(game: "Game") -> tuple[CampaignPhase, ...]:
    """The campaign's arc for UI purposes: authored, else the Tier-0 sequence."""
    return authored_arc_for(game) or (ROLLBACK, INTERDICTION, OFFENSIVE)


#: How each Tier-0 phase advances (the classifier's own thresholds, spelled out
#: for the expander -- an inferred arc should explain its transitions the same
#: way an authored one does). The Offensive phase is terminal.
_TIER0_ADVANCE = {
    "rollback": (
        f"Advances once the enemy IADS falls below {IADS_ROLLBACK_HOLD:.0%} "
        "and the enemy air threat fades"
    ),
    "interdiction": (
        f"Advances once the enemy IADS falls below {IADS_OFFENSIVE_CEILING:.0%} "
        "and the front starts moving (or a base falls)"
    ),
    "offensive": "",
}


def _describe_condition(
    game: "Game",
    condition: PhaseCondition,
    baseline: Optional[PhaseBaseline],
    live: bool,
) -> str:
    """An ``advance_when`` set as prose; live values only on the active phase."""
    bits = []
    if condition.blue_will_below is not None:
        now = ""
        will = getattr(getattr(game, "blue", None), "political_will", None)
        if live and will is not None:
            now = f" (now {will:.0f})"
        bits.append(f"will falls below {condition.blue_will_below:g}{now}")
    if condition.enemy_iads_below is not None:
        now = ""
        if live and baseline is not None and baseline.sam_sites:
            ratio = _enemy_sam_sites(game) / baseline.sam_sites
            now = f" (now {ratio:.0%})"
        bits.append(f"enemy IADS falls below {condition.enemy_iads_below:.0%}{now}")
    if condition.red_resolve_below is not None:
        now = ""
        resolve = getattr(getattr(game, "red", None), "political_will", None)
        if live and resolve is not None:
            now = f" (now {resolve:.0f})"
        bits.append(f"enemy resolve falls below {condition.red_resolve_below:g}{now}")
    if condition.capture_cp is not None:
        bits.append(f"{condition.capture_cp} is captured")
    if condition.min_turn is not None:
        bits.append(f"turn {condition.min_turn} arrives")
    return " or ".join(bits)


def _advance_display(
    game: "Game", arc: tuple[CampaignPhase, ...], index: int, live: bool
) -> str:
    """How the arc LEAVES phase ``index``, for its expander row.

    Authored phases spell out the ``advance_when`` acceleration (the schedule --
    the next phase's ``min_turn`` -- already shows on the next row's header);
    Tier-0 phases spell out the classifier thresholds they advance on. Empty for
    a terminal phase or one with no early-out.
    """
    phase = arc[index]
    if not phase.authored:
        return _TIER0_ADVANCE.get(phase.key, "")
    if index + 1 >= len(arc) or phase.advance_when is None:
        return ""
    baseline = getattr(game, "phase_baseline", None)
    described = _describe_condition(game, phase.advance_when, baseline, live)
    if not described:
        return ""
    return f"Escalates early if {described}"


def _objective_states(game: "Game", phase: CampaignPhase) -> list[dict[str, object]]:
    """The phase's objectives with live done-ticks (None = display-only)."""
    baseline = getattr(game, "phase_baseline", None) or PhaseBaseline(
        sam_sites=0, enemy_fighters=0
    )
    return [
        {
            "text": objective.text,
            "done": (
                None
                if objective.done_when is None
                else _condition_satisfied(game, objective.done_when, baseline)
            ),
        }
        for objective in phase.objectives
    ]


def arc_overview(game: "Game") -> list[dict[str, object]]:
    """The whole phase arc for the client expander (W3 item-1 UI).

    One dict per phase: key/name/narrative, the scheduled ``min_turn`` (0 = not
    turn-pinned -- Tier-0 arcs advance adaptively), the locked target classes,
    the zone names, whether it is the current phase, how the arc leaves it
    (``advance`` -- the transition-transparency string, live values on the
    current phase), and the objectives checklist with live done-ticks. Empty
    when phases are off or no phase has resolved yet.
    """
    if active_phase(game) is None:
        return []
    current = getattr(game, "current_phase_key", None)
    arc = _arc_for_display(game)
    overview: list[dict[str, object]] = []
    for index, phase in enumerate(arc):
        is_current = phase.key == current
        overview.append(
            {
                "key": phase.key,
                "name": phase.name,
                "narrative": phase.narrative,
                "min_turn": phase.min_turn,
                "locked": list(phase.locked_target_classes),
                "zones": [
                    zone.name or zone.center_cp or "Restricted zone"
                    for zone in phase.restricted_zones
                ],
                "current": is_current,
                "advance": _advance_display(game, arc, index, live=is_current),
                "objectives": _objective_states(game, phase),
            }
        )
    return overview


def zone_detail(game: "Game") -> str:
    """One line for the zone tooltip: what the ROE locks now, and when it eases.

    Playtest-driven (item-4 UI): the circle alone didn't explain that buildings
    are locked everywhere while AAA stays fair game, or that the restriction is
    temporary. Empty when no authored phase is active.
    """
    phase = active_phase(game)
    if phase is None or not phase.authored:
        return ""
    locked = (
        ", ".join(phase.locked_target_classes)
        if phase.locked_target_classes
        else "none"
    )
    detail = f"No offensive tasking inside. Locked classes everywhere: {locked}."
    arc = authored_arc_for(game)
    keys = [p.key for p in arc]
    if phase.key in keys:
        index = keys.index(phase.key)
        if index + 1 < len(arc):
            nxt = arc[index + 1]
            when = f" (~turn {nxt.min_turn})" if nxt.min_turn else ""
            detail += f" Eases at {nxt.name}{when}."
    return detail


def count_roe_violations(game: "Game", debriefing: "Debriefing") -> int:
    """Enemy ground kills that broke the active phase's ROE this turn.

    The SOFT player enforcement: nothing stops the strike, but each violating kill
    drains political will sharply (weighted in ``political_will.py``). A kill
    violates when it lands **inside a restricted (no-strike) zone**, or -- under
    inverted ROE (COIN free-fire) -- **outside every free-fire pocket**. Reads the
    debriefing's enemy ground-object losses (their theater units carry positions).
    """
    restricted = active_restricted_zones(game)
    free_fire = active_free_fire_zones(game)
    if not restricted and not free_fire:
        return 0
    violations = 0
    ground_losses = getattr(debriefing, "ground_losses", None)
    if ground_losses is None:
        return 0
    for mapping in getattr(ground_losses, "enemy_ground_objects", []) or []:
        position = getattr(mapping.theater_unit, "position", None)
        if position is None:
            continue
        if any(zone.contains(position) for zone in restricted):
            violations += 1  # inside a no-strike zone (or a pocket's carve-out)
        elif free_fire and not any(zone.contains(position) for zone in free_fire):
            violations += 1  # weapons-hold everywhere but the pockets
    return violations
