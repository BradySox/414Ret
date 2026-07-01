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
so an inferred phase always explains itself. Tier 1/2 YAML authoring lands with P2
(the Vietnam W4 arcs); nothing here reads a campaign ``phases:`` block yet.

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

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from game import Game

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
class CampaignPhase:
    """A doctrine-like profile active for part of a campaign (spec S2.1).

    Tier 0 uses only these fields; the authored-tier fields (``min_turn``,
    ``advance_when``, whitelist deltas, objectives) arrive with P2/W4.
    ``emphasis`` is the full ordering of ``PlanNextAction``'s *offensive* root
    methods by class name -- the soft reweight of S4. Kept as names so this module
    never imports the commander (no cycles); ``nextaction.py`` resolves them and a
    test locks the two in sync.
    """

    key: str
    name: str
    narrative: str
    emphasis: tuple[str, ...] = ()


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
    """The phase consumers read (planner emphasis, kneeboard, server payload)."""
    if not getattr(game.settings, "campaign_phases", False):
        return None
    key = getattr(game, "current_phase_key", None)
    if key is None:
        return None
    return PHASES.get(key)
