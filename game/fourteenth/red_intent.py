"""Red Intent -- a thinking red opponent (the deferred red arc, §55).

The mirror of ``game/fourteenth/phases.py`` for RED, and unlike the blue phase arc it
carries *memory* across turns. Each turn resolves a RED **posture**
(``CONSOLIDATE`` / ``ATTRITION`` / ``SURGE``) from live state + territorial memory +
resolve, latches it on the ``Game``, and exposes it to consumers.

The posture is classified, latched, surfaced (SITREP line + a per-turn message), and
consumed by four planner seams: offensive emphasis (``offensive_emphasis``), target-shuffle
unpredictability (``unpredictability_modifier``), offensive-commit aggressiveness
(``effective_aggressiveness``), and ground husbanding (``stance_commit_factor``). The §53
war-economy supply coupling feeds the classifier via ``_red_supply_health``. Every helper
returns a neutral value when the feature is off, the side is blue, or the posture is
ATTRITION, so the planner stays byte-identical to stock until red actively consolidates or
surges. See ``docs/dev/design/414th-red-intent-notes.md``.

Design decisions (2026-07-08): three postures (Feint folded into Attrition); full memory
from v1 (state + last-turn setback + resolve); authored ``red_tempo`` windows win (a P3
concern -- P0 touches no stances). Structure mirrors ``phases.py`` so the two read the
same way: a lazily-snapshotted turn-0 baseline the memory measures against, a pure
``classify_red_intent``, asymmetric hysteresis, and an ``update`` entry point called from
``Game.initialize_turn`` that is idempotent under the multiple-init-per-turn cases.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique
from importlib import import_module
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from game.game import Game
    from game.theater.player import Player


@unique
class RedPosture(Enum):
    """RED's turn-to-turn intent. Persisted by ``value`` on the ``Game``."""

    CONSOLIDATE = "consolidate"
    ATTRITION = "attrition"
    SURGE = "surge"

    @property
    def display(self) -> str:
        return {
            RedPosture.CONSOLIDATE: "Consolidating",
            RedPosture.ATTRITION: "Attrition",
            RedPosture.SURGE: "Surging",
        }[self]

    @property
    def narrative(self) -> str:
        return {
            RedPosture.CONSOLIDATE: "defending and husbanding reserves under pressure",
            RedPosture.ATTRITION: "grinding and trading evenly",
            RedPosture.SURGE: "pressing an offensive while it holds the advantage",
        }[self]


# --- classifier thresholds -----------------------------------------------------------

#: Ground-force ratio (red deployable / blue deployable, summed over active fronts)
#: at/above which red may SURGE, and at/below which it CONSOLIDATEs.
SURGE_GROUND_RATIO = 1.5
CONSOLIDATE_GROUND_RATIO = 0.7
#: Red air-superiority strength relative to blue's (alive fighters, current) below
#: which red is treated as air-suppressed and cannot SURGE.
SURGE_MIN_AIR_RATIO = 0.5
#: Red resolve (political_will, 0-100) below which red CONSOLIDATEs regardless of the
#: ground ratio. Inert on non-will campaigns (resolve stays ~100 -- see ``_red_resolve``).
CONSOLIDATE_RESOLVE = 35.0
#: §53 (P4) supply-health bounds: below STARVED forces CONSOLIDATE; SURGE additionally
#: needs supply at/above SURGE_MIN_SUPPLY. Both inert while supply is None (economy off).
STARVED_SUPPLY = 0.35
SURGE_MIN_SUPPLY = 0.5
#: Mean rise in blue front progress since campaign start treated as "red giving ground"
#: -- a territorial-memory signal biasing toward CONSOLIDATE.
FRONT_LOSS_EPSILON = 0.05
#: Turns a posture must hold before ESCALATING (CONSOLIDATE->ATTRITION, ->SURGE).
#: De-escalation (toward CONSOLIDATE) is immediate -- a command reacts to a setback at
#: once. Asymmetric hysteresis; mirrors the phase dwell but one-way.
INTENT_MIN_DWELL_TURNS = 2

_POSTURE_RANK = {
    RedPosture.CONSOLIDATE: 0,
    RedPosture.ATTRITION: 1,
    RedPosture.SURGE: 2,
}

#: P1 (seam 1): each posture's ordering of ``PlanNextAction``'s offensive root methods
#: (class-name strings, like the campaign-phase ``emphasis`` -- kept as names so this
#: module never imports the commander). ATTRITION is deliberately absent -> the stock
#: order stands (the neutral default). CONSOLIDATE leans defensive (blunt the enemy
#: buildup, keep the SAM belt up; push captures/CAS to the back -- don't lunge); SURGE
#: leans offensive (take ground first). A test locks each tuple to the real factory set.
_POSTURE_EMPHASIS: dict[RedPosture, tuple[str, ...]] = {
    RedPosture.CONSOLIDATE: (
        "InterdictReinforcements",
        "AttackBattlePositions",
        "DegradeIads",
        "AttackAirInfrastructure",
        "AttackBuildings",
        "AttackShips",
        "CaptureBases",
        "PlanFrontLineCas",
    ),
    RedPosture.SURGE: (
        "CaptureBases",
        "PlanFrontLineCas",
        "AttackBattlePositions",
        "InterdictReinforcements",
        "AttackAirInfrastructure",
        "AttackShips",
        "DegradeIads",
        "AttackBuildings",
    ),
}


# --- state -----------------------------------------------------------------------------


@dataclass
class RedIntentBaseline:
    """Turn-0 anchor the territorial memory measures against (like ``PhaseBaseline``).

    Snapshotted lazily on the first gated run and never overwritten, so the metrics
    stay stable under the multiple-init-per-turn cases (a cheat capture re-inits the
    turn; the posture must not flicker).
    """

    front_fractions: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class RedIntentMetrics:
    """One turn's classifier inputs -- current state + memory + resolve."""

    ground_ratio: float  # red deployable / blue deployable, active fronts
    air_ratio: float  # red air-sup airframes / blue's (current)
    resolve: float  # red political_will, 0-100 (100 when untracked)
    front_advance: float  # mean rise in blue progress vs turn-0 (>0 = red pushed back)
    lost_base: bool  # red lost >=1 base last turn (from last_sitrep)
    supply_health: Optional[float]  # §53 coupling (P4); None in P0 / economy off


# --- live-state collection (all stable within a turn -> idempotent) --------------------


def _front_fractions(game: "Game") -> dict[str, float]:
    """Blue progress fraction per active front, keyed stably across turns."""
    fractions: dict[str, float] = {}
    for front in game.theater.conflicts():
        length = front.route_length
        if length > 0:
            fractions[f"{front.blue_cp.id}:{front.red_cp.id}"] = (
                front._blue_route_progress / length
            )
    return fractions


def _ground_ratio(game: "Game") -> float:
    """Red deployable front-line units / blue's, summed over active fronts.

    3.0 when red faces no deployable blue ground (red unopposed); 1.0 when there is no
    active front at all (nothing to press).
    """
    red = 0
    blue = 0
    for front in game.theater.conflicts():
        red += front.red_cp.deployable_front_line_units
        blue += front.blue_cp.deployable_front_line_units
    if blue <= 0:
        return 3.0 if red > 0 else 1.0
    return red / blue


def _fighters(game: "Game", player: "Player") -> int:
    from game.ato.flighttype import FlightType

    air_superiority = {
        FlightType.BARCAP,
        FlightType.TARCAP,
        FlightType.SWEEP,
        FlightType.ESCORT,
        FlightType.INTERCEPTION,
    }
    return sum(
        squadron.owned_aircraft
        for squadron in game.air_wing_for(player).iter_squadrons()
        if squadron.primary_task in air_superiority
    )


def _air_ratio(game: "Game") -> float:
    """Red air-superiority airframes / blue's (current). 2.0 if blue fields none."""
    from game.theater.player import Player

    red = _fighters(game, Player.RED)
    blue = _fighters(game, Player.BLUE)
    if blue <= 0:
        return 2.0 if red > 0 else 1.0
    return red / blue


def _red_resolve(game: "Game") -> float:
    """Red Regime Resolve (0-100), or 100 when the will economy isn't tracking it.

    getattr-defaulted so a non-will campaign never trips the low-resolve CONSOLIDATE
    trigger (its resolve reads a full 100).
    """
    return float(getattr(game.red, "political_will", 100.0))


def _red_supply_health(game: "Game") -> Optional[float]:
    """Red materiel readiness in [0, 1], or None when §53 (war_economy) is absent/off.

    Reads the locked interface ``war_economy.coalition_supply_health(game, coalition)``
    lazily, and degrades to None on any absence -- setting off, module missing, or a raise
    -- so red intent never depends on the economy being present. None makes the
    classifier's supply terms drop out entirely.
    """
    if not getattr(game.settings, "war_economy", False):
        return None
    # Dynamic import: §53's war_economy module may be absent on this branch, and mypy
    # must not hard-resolve it (it would error where §53 is absent and flag an unused
    # ignore where it is present). importlib keeps the optional coupling honest.
    try:
        module = import_module("game.fourteenth.war_economy")
    except ImportError:
        return None
    supply_health = getattr(module, "coalition_supply_health", None)
    if supply_health is None:
        return None
    try:
        return supply_health(game, game.red)
    except Exception:
        # Best-effort optional coupling: a broken/partial economy never breaks intent.
        return None


def snapshot_baseline(game: "Game") -> RedIntentBaseline:
    return RedIntentBaseline(front_fractions=_front_fractions(game))


def collect_metrics(game: "Game", baseline: RedIntentBaseline) -> RedIntentMetrics:
    deltas = []
    for key, fraction in _front_fractions(game).items():
        anchor = baseline.front_fractions.get(key)
        if anchor is not None:
            deltas.append(fraction - anchor)
    front_advance = sum(deltas) / len(deltas) if deltas else 0.0

    # last_sitrep.captured = CPs BLUE took last turn = RED's base losses (a committed,
    # turn-stable fact, so this stays idempotent under re-init).
    sitrep = getattr(game, "last_sitrep", None)
    lost_base = bool(sitrep and getattr(sitrep, "captured", None))

    return RedIntentMetrics(
        ground_ratio=_ground_ratio(game),
        air_ratio=_air_ratio(game),
        resolve=_red_resolve(game),
        front_advance=front_advance,
        lost_base=lost_base,
        supply_health=_red_supply_health(game),
    )


# --- the decision ----------------------------------------------------------------------


def classify_red_intent(m: RedIntentMetrics) -> RedPosture:
    """Pick RED's posture (caller applies hysteresis).

    CONSOLIDATE when red is under pressure -- outnumbered on the ground, low resolve,
    a base lost last turn, ground given up since the start, or (P4) starved of supply.
    SURGE when red holds a clear ground advantage AND its air isn't suppressed AND (P4)
    it can sustain the push. ATTRITION otherwise -- the default, which also absorbs the
    dropped 'Feint' as a moderate-unpredictability middle once P2 wires seam 2.
    """
    starved = m.supply_health is not None and m.supply_health < STARVED_SUPPLY
    under_pressure = (
        m.ground_ratio <= CONSOLIDATE_GROUND_RATIO
        or m.resolve < CONSOLIDATE_RESOLVE
        or m.lost_base
        or m.front_advance >= FRONT_LOSS_EPSILON
    )
    if starved or under_pressure:
        return RedPosture.CONSOLIDATE

    supplied = m.supply_health is None or m.supply_health >= SURGE_MIN_SUPPLY
    if (
        m.ground_ratio >= SURGE_GROUND_RATIO
        and m.air_ratio >= SURGE_MIN_AIR_RATIO
        and supplied
    ):
        return RedPosture.SURGE

    return RedPosture.ATTRITION


def _next_posture(
    current: Optional[RedPosture],
    entered_on_turn: Optional[int],
    turn: int,
    target: RedPosture,
) -> RedPosture:
    """Asymmetric dwell: escalating needs the target to hold ``INTENT_MIN_DWELL_TURNS``;
    de-escalating (toward the lower-ranked, more defensive posture) applies at once."""
    if current is None or target is current:
        return target
    if _POSTURE_RANK[target] < _POSTURE_RANK[current]:
        return target  # de-escalation is immediate
    if turn - (entered_on_turn or 0) < INTENT_MIN_DWELL_TURNS:
        return current  # escalation waits out the dwell
    return target


def _legibility(m: RedIntentMetrics) -> str:
    """The 'why' string -- the posture explains itself (the §40 legibility rule)."""
    air = "air holding" if m.air_ratio >= SURGE_MIN_AIR_RATIO else "air suppressed"
    if m.front_advance >= FRONT_LOSS_EPSILON:
        front = "giving ground"
    elif m.front_advance <= -FRONT_LOSS_EPSILON:
        front = "gaining ground"
    else:
        front = "front static"
    parts = [f"ground {m.ground_ratio:.1f}x", air, front]
    if m.resolve < CONSOLIDATE_RESOLVE:
        parts.append("resolve low")
    if m.supply_health is not None:
        parts.append(f"supply {round(m.supply_health * 100)}%")
    return " · ".join(parts)


def _posture_from_key(key: Optional[str]) -> Optional[RedPosture]:
    if key is None:
        return None
    try:
        return RedPosture(key)
    except ValueError:
        return None  # stale/unknown persisted value -> reclassify from scratch


# --- the per-turn entry point ----------------------------------------------------------


def update_red_intent(game: "Game") -> None:
    """Resolve this turn's RED posture. Called from ``Game.initialize_turn`` after
    ``update_campaign_phase`` and before the coalitions plan. Idempotent under the
    multiple-init-per-turn cases (all inputs are turn-stable; the baseline is snapshotted
    once and never overwritten).

    Latches ``game.red_intent_key`` + a status line and announces transitions; the four
    planner seams read the result through ``active_red_intent``. Setting off => state
    cleared, so consumers see 'no posture' and behave stock.
    """
    if not getattr(game.settings, "red_intent", False):
        game.red_intent_key = None
        game.red_intent_entered_on_turn = None
        game.red_intent_status_line = None
        return

    baseline = getattr(game, "red_intent_baseline", None)
    if baseline is None:
        baseline = snapshot_baseline(game)
        game.red_intent_baseline = baseline

    metrics = collect_metrics(game, baseline)
    target = classify_red_intent(metrics)
    current = _posture_from_key(getattr(game, "red_intent_key", None))
    new = _next_posture(
        current, getattr(game, "red_intent_entered_on_turn", None), game.turn, target
    )

    if new is not current:
        game.red_intent_key = new.value
        game.red_intent_entered_on_turn = game.turn
        # Announce transitions, not the campaign-start assignment (the status surfaces
        # already carry the opening posture). Same-turn re-inits resolve identically,
        # so this never double-fires.
        if current is not None:
            game.message(
                f"Enemy posture: {new.display}",
                f"Red is {new.narrative} ({_legibility(metrics)}).",
            )
    game.red_intent_status_line = f"{new.display} — {_legibility(metrics)}"


def active_red_intent(game: "Game") -> Optional[RedPosture]:
    """The posture consumers read (the four planner seams + the SITREP/status surfaces)."""
    if not getattr(game.settings, "red_intent", False):
        return None
    return _posture_from_key(getattr(game, "red_intent_key", None))


def sitrep_posture_line(game: "Game") -> Optional[str]:
    """The short RED-posture label for the SITREP band, or None when off/unresolved."""
    posture = active_red_intent(game)
    return posture.display if posture else None


def offensive_emphasis(game: "Game") -> Optional[tuple[str, ...]]:
    """RED's posture-driven offensive-method ordering, or None to use the stock order.

    P1 seam 1: the RED branch of ``PlanNextAction._offensive_order`` consumes this the
    way the BLUE branch consumes the campaign phase's ``emphasis``. None when red_intent
    is off, unresolved, or the posture is ATTRITION (the neutral default) -- so the
    planner is byte-identical to stock unless red is actively consolidating or surging.
    """
    posture = active_red_intent(game)
    if posture is None:
        return None
    return _POSTURE_EMPHASIS.get(posture)


# --- P2 (seams 2 + 3): unpredictability + aggressiveness ------------------------------

#: RED posture -> additive planner unpredictability. ATTRITION carries a modest floor
#: (the folded-in 'feint' -- red is never perfectly deterministic); SURGE is 0 (focused
#: on the priority target); CONSOLIDATE stays low (mostly defense-supporting targets).
_POSTURE_UNPREDICTABILITY: dict[RedPosture, int] = {
    RedPosture.CONSOLIDATE: 5,
    RedPosture.ATTRITION: 15,
    RedPosture.SURGE: 0,
}

#: RED posture -> delta on ``opfor_autoplanner_aggressiveness`` (0-100; higher = red
#: abandons more bases to commit fighters offensively). SURGE commits, CONSOLIDATE
#: defends, ATTRITION leaves the setting alone.
_POSTURE_AGGRESSION_DELTA: dict[RedPosture, int] = {
    RedPosture.CONSOLIDATE: -30,
    RedPosture.ATTRITION: 0,
    RedPosture.SURGE: 30,
}

#: RED posture -> multiplier on the *perceived* ground-force balance the ATTACK stance
#: thresholds test (seam 4). SURGE inflates it (commit reserves sooner -- reach an
#: attacking stance at a lower real advantage); CONSOLIDATE deflates it (husband --
#: harder to escalate to attacking, while defending is left untouched, so consolidate
#: never forces a retreat). ATTRITION is neutral.
_POSTURE_COMMIT_FACTOR: dict[RedPosture, float] = {
    RedPosture.CONSOLIDATE: 0.7,
    RedPosture.ATTRITION: 1.0,
    RedPosture.SURGE: 1.35,
}


def unpredictability_modifier(game: "Game") -> int:
    """RED's posture contribution to its planner unpredictability (seam 2).

    Added to ``opfor_planner_unpredictability`` + the C2-decap bonus in
    ``targetorder._unpredictability_for`` (RED only), then clamped there. 0 when
    red_intent is off/unresolved, so the base setting is preserved byte-identically.
    """
    posture = active_red_intent(game)
    if posture is None:
        return 0
    return _POSTURE_UNPREDICTABILITY.get(posture, 0)


def effective_aggressiveness(game: "Game") -> int:
    """``opfor_autoplanner_aggressiveness`` biased by RED's posture, clamped 0-100 (seam 3).

    Returns the raw setting when red_intent is off/unresolved or the posture is
    ATTRITION (neutral) -- byte-identical to today. SURGE raises it (red commits more
    bases to offense), CONSOLIDATE lowers it (red defends everything).
    """
    base = int(getattr(game.settings, "opfor_autoplanner_aggressiveness", 0))
    posture = active_red_intent(game)
    if posture is None:
        return base
    return max(0, min(100, base + _POSTURE_AGGRESSION_DELTA.get(posture, 0)))


def stance_commit_factor(game: "Game") -> float:
    """RED's ground-commitment bias for the ATTACK-stance thresholds (seam 4).

    >1 commits reserves sooner (SURGE reaches aggressive/elimination/breakthrough at a
    lower real advantage); <1 husbands them (CONSOLIDATE needs more advantage to attack,
    while still defending normally). 1.0 for a stock/observing red -- and, per the
    [DECIDED] 'authored windows win' rule, 1.0 while an authored ``red_tempo``
    ground-offensive pulse owns red's stances, so the two never double-drive the front.
    """
    from game.fourteenth.red_tempo import ground_offensive_active

    if ground_offensive_active(game):
        return 1.0
    posture = active_red_intent(game)
    if posture is None:
        return 1.0
    return _POSTURE_COMMIT_FACTOR.get(posture, 1.0)
