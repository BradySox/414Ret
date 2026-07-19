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

Refinement (2026-07-10, "make red smarter"): the design note always called for *rolling*
trend memory ("blue has hit my IADS two turns running -> stay defensive"), but v1 only
snapshotted turn 0. This build adds:

* **Rolling memory (A)** -- a bounded per-turn ``red_intent_history`` of turn-stable levels
  on the ``Game``; the classifier reads *trends* against a lookback sample (~2 turns back),
  so red reacts to the ARC of the war, not just this turn's snapshot.
* **Richer battle-reading (C)** -- new trend signals: the IADS being dismantled over turns,
  resolve collapsing, bases bleeding, the front steadily eroding all bias toward
  CONSOLIDATE even at a paper ground edge; a collapsing BLUE air force opens an *opportunity
  window* letting red SURGE at a lower ground bar.
* **Graduated intensity (B)** -- the classifier also yields an ``intensity`` in [0, 1] (how
  strongly the posture is held), latched on the ``Game`` and read by the aggressiveness +
  ground-commit seams so a runaway red presses harder and a red on the ropes turtles harder,
  instead of flat per-posture constants. The graduated formulas are anchored so intensity
  ``DEFAULT_INTENSITY`` reproduces the v1 constants exactly (no behaviour change until the
  classifier produces a real margin).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
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

# --- rolling-memory trend thresholds (A + C, the "two turns running" signals) ---------

#: How many turns of per-turn samples the memory keeps on the ``Game``.
MEMORY_LENGTH = 6
#: How far back the classifier measures trends against (the lookback sample). The most
#: recent sample strictly older than this many turns is preferred; earlier in the game
#: the oldest available sample stands in, and turn 1 has no trend at all.
TREND_LOOKBACK_TURNS = 2
#: Fraction of red's long+medium SAM sites lost over the lookback window that reads as
#: "the IADS is being dismantled" -> bias to CONSOLIDATE (dig in, defend what's left).
IADS_COLLAPSE_TREND = 0.25
#: Drop in red resolve over the window that reads as "the regime is cracking" -> the
#: derivative signal the instantaneous ``CONSOLIDATE_RESOLVE`` level misses.
RESOLVE_COLLAPSE_TREND = -8.0
#: Rise in blue front progress over the window (distinct from the turn-0 cumulative) that
#: reads as the front actively eroding again after a plateau.
FRONT_EROSION_TREND = 0.05
#: Fraction of blue's air-superiority force lost over the window that opens an
#: *opportunity window*: red may SURGE at the reduced ground bar below, exploiting a
#: transient gap even without its own clear ground advantage.
BLUE_AIR_COLLAPSE_FRAC = 0.35
#: The reduced ground ratio red will SURGE at when a blue-air-collapse opportunity is live.
SURGE_OPPORTUNITY_GROUND_RATIO = 1.2

# --- intensity (B) -------------------------------------------------------------------

#: Neutral intensity: what the seams assume when intensity is unresolved (feature just
#: latched a key with no intensity, a pre-feature save, a bare test). The graduated seam
#: formulas are anchored here so this value reproduces the v1 flat constants exactly.
DEFAULT_INTENSITY = 0.5
#: Intensity floors: even a marginal surge/consolidate carries some conviction.
SURGE_INTENSITY_FLOOR = 0.35
CONSOLIDATE_INTENSITY_FLOOR = 0.35
#: Ground ratio at which a SURGE is "runaway" (intensity 1.0); the floor is at the SURGE
#: threshold and it ramps to 1.0 here.
SURGE_STRONG_RATIO = 3.0
#: Resolve drop over the window that maps to full CONSOLIDATE severity from the resolve
#: axis (a steeper collapse than the trigger threshold).
RESOLVE_COLLAPSE_SPAN = 20.0
#: A lost base (last turn or over the window) is inherently serious -- a fixed severity
#: floor feeding CONSOLIDATE intensity even when the other axes look mild.
BASE_LOSS_SEVERITY = 0.6

# --- seam graduation (B): deltas scale about the v1 midpoint by intensity -------------

#: Aggressiveness (seam 3): the SURGE/CONSOLIDATE delta is ``AGGRESSION_MID`` at
#: ``DEFAULT_INTENSITY`` (the v1 +/-30) and spans +/-``AGGRESSION_SPAN`` across the
#: intensity range -- a marginal surge nudges, a runaway one commits hard.
AGGRESSION_MID = 30
AGGRESSION_SPAN = 30
#: Ground-commit factor (seam 4): SURGE inflates the perceived balance about
#: ``SURGE_COMMIT_MID`` (v1 1.35), CONSOLIDATE deflates about ``CONSOLIDATE_COMMIT_MID``
#: (v1 0.7), each spanning +/-``COMMIT_SPAN`` by intensity.
SURGE_COMMIT_MID = 1.35
CONSOLIDATE_COMMIT_MID = 0.7
COMMIT_SPAN = 0.4

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
        "AttackMotorpools",
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
        "AttackMotorpools",
    ),
}

#: RED posture -> additive planner unpredictability (seam 2). ATTRITION carries a modest
#: floor (the folded-in 'feint' -- red is never perfectly deterministic); SURGE is 0
#: (focused on the priority target); CONSOLIDATE stays low (mostly defense-supporting
#: targets). Flat per posture (unlike the graduated aggressiveness/commit seams) -- it
#: already stacks with the §52 C2-decap bonus.
_POSTURE_UNPREDICTABILITY: dict[RedPosture, int] = {
    RedPosture.CONSOLIDATE: 5,
    RedPosture.ATTRITION: 15,
    RedPosture.SURGE: 0,
}


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


# --- tuning (settings-driven temperament) --------------------------------------------


@dataclass(frozen=True)
class RedIntentTuning:
    """The settings-derived knobs the classifier + seams read (the 'temperament').

    All default to the module constants, so ``DEFAULT_TUNING`` reproduces the base
    behaviour exactly -- a game with no red-intent tuning settings (or a bare test that
    calls ``classify_red_intent(m)`` positionally) classifies byte-identically to before.
    ``tuning_for(game)`` derives real values from the ``red_intent_boldness`` /
    ``red_intent_dwell_turns`` / ``red_intent_trend_window`` settings.
    """

    surge_ground_ratio: float = SURGE_GROUND_RATIO
    consolidate_ground_ratio: float = CONSOLIDATE_GROUND_RATIO
    surge_opportunity_ground_ratio: float = SURGE_OPPORTUNITY_GROUND_RATIO
    dwell_turns: int = INTENT_MIN_DWELL_TURNS
    trend_lookback_turns: int = TREND_LOOKBACK_TURNS
    #: Scales the aggressiveness delta + the commit-factor deviation from neutral, so a
    #: bold red presses harder once committed. 1.0 = the base swing.
    seam_scale: float = 1.0


DEFAULT_TUNING = RedIntentTuning()

#: How far the boldness dial swings the surge/consolidate/opportunity ground bars
#: (fraction of the base threshold at the extremes) and the seam magnitude.
_BOLDNESS_THRESHOLD_SWING = 0.30
_BOLDNESS_SEAM_SWING = 0.40


def tuning_for(game: "Game") -> RedIntentTuning:
    """Derive this game's red-intent tuning from its settings (default = the base values).

    ``red_intent_boldness`` (0-100, 50 = neutral) is the master dial: higher lowers the
    surge/opportunity bars and the consolidate bar (bolder -- surges at a smaller edge,
    turtles only when badly outnumbered) and raises the seam magnitude (presses harder).
    ``red_intent_dwell_turns`` / ``red_intent_trend_window`` tune the hysteresis dwell and
    the trend-lookback window. All getattr-defaulted so a pre-feature save/settings blob
    yields ``DEFAULT_TUNING``.
    """
    boldness = float(getattr(game.settings, "red_intent_boldness", 50))
    b = (boldness - 50.0) / 50.0  # [-1, 1], 0 at the neutral default
    scale = 1.0 - _BOLDNESS_THRESHOLD_SWING * b
    return RedIntentTuning(
        surge_ground_ratio=SURGE_GROUND_RATIO * scale,
        consolidate_ground_ratio=CONSOLIDATE_GROUND_RATIO * scale,
        surge_opportunity_ground_ratio=SURGE_OPPORTUNITY_GROUND_RATIO * scale,
        dwell_turns=int(
            getattr(game.settings, "red_intent_dwell_turns", INTENT_MIN_DWELL_TURNS)
        ),
        trend_lookback_turns=int(
            getattr(game.settings, "red_intent_trend_window", TREND_LOOKBACK_TURNS)
        ),
        seam_scale=1.0 + _BOLDNESS_SEAM_SWING * b,
    )


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
class RedIntentSample:
    """One turn's turn-stable *levels*, banked in the rolling ``red_intent_history``.

    Trends are derived by differencing the current sample against a lookback sample
    (~``TREND_LOOKBACK_TURNS`` back), so red reads the ARC of the war. Levels (not
    per-turn deltas) are stored because they are turn-stable -> recording is idempotent
    under the multiple-init-per-turn cases (re-recording the same turn is a no-op).
    """

    turn: int
    resolve: float
    front_advance: float  # cumulative mean blue progress vs the turn-0 baseline
    sam_alive: int  # red long+medium SAM sites still alive
    red_fighters: int  # red air-superiority owned airframes
    blue_fighters: int  # blue air-superiority owned airframes
    red_bases: int  # red-held control points
    supply_health: Optional[float]  # §53 coupling; None when the economy is off/absent


@dataclass(frozen=True)
class FrontPosture:
    """A per-front RED posture (D): resolved from that front's own ground balance +
    the shared theater air/resolve/supply/trend read, so red commits its reserves on
    the front it is winning and husbands on the one it is losing. Latched per front on
    ``game.red_intent_fronts`` (keyed by the front's cp-id pair), recompute-not-pickle
    like the theater pointer; carries its own dwell entry-turn for per-front hysteresis.
    """

    name: str  # display name for the front (the ribbon expander)
    posture: str  # RedPosture value
    entered_on_turn: int
    intensity: float


@dataclass(frozen=True)
class RedIntentMetrics:
    """One turn's classifier inputs -- current state + memory + resolve.

    The trend fields (``iads_trend`` .. ``blue_air_collapsing``) all default to a
    *neutral* value, so a metrics with no rolling history classifies exactly as v1 did
    (and the direct-construction classifier tests are unchanged). They only bite once
    there is prior history to difference against.
    """

    ground_ratio: float  # red deployable / blue deployable, active fronts
    air_ratio: float  # red air-sup airframes / blue's (current)
    resolve: float  # red political_will, 0-100 (100 when untracked)
    front_advance: float  # mean rise in blue progress vs turn-0 (>0 = red pushed back)
    lost_base: bool  # red lost >=1 base last turn (from last_sitrep)
    supply_health: Optional[float]  # §53 coupling (P4); None in P0 / economy off
    #: Fraction of red SAM sites lost over the lookback window (>0 = IADS dismantled).
    iads_trend: float = 0.0
    #: Change in red resolve over the window (<0 = the regime is cracking).
    resolve_trend: float = 0.0
    #: Change in red-held base count over the window (<0 = bleeding bases).
    base_trend: int = 0
    #: Change in cumulative front advance over the window (>0 = front eroding again).
    front_trend: float = 0.0
    #: True when blue's air-superiority force collapsed over the window (opportunity).
    blue_air_collapsing: bool = False


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


def _front_advance(game: "Game", baseline: RedIntentBaseline) -> float:
    """Mean signed blue front movement vs the turn-0 anchor, over fronts in both snaps."""
    deltas = []
    for key, fraction in _front_fractions(game).items():
        anchor = baseline.front_fractions.get(key)
        if anchor is not None:
            deltas.append(fraction - anchor)
    return sum(deltas) / len(deltas) if deltas else 0.0


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


def _front_key(front: object) -> Optional[str]:
    """A front's stable key (cp-id pair), or None if the object lacks cp ids.

    Defensive on the cp attrs so a duck-typed test front (which drives the stance task
    via ``control_point_friendly_to`` only, with no ``blue_cp``/``red_cp``) resolves to
    None and the seam falls back to the theater-wide posture rather than raising.
    """
    blue = getattr(getattr(front, "blue_cp", None), "id", None)
    red = getattr(getattr(front, "red_cp", None), "id", None)
    if blue is None or red is None:
        return None
    return f"{blue}:{red}"


def _front_ground_ratio(front: object) -> float:
    """Red deployable / blue deployable for a SINGLE front (the per-front D signal)."""
    red = getattr(getattr(front, "red_cp", None), "deployable_front_line_units", 0)
    blue = getattr(getattr(front, "blue_cp", None), "deployable_front_line_units", 0)
    if blue <= 0:
        return 3.0 if red > 0 else 1.0
    return red / blue


def _front_name(front: object) -> str:
    """A short display name for a front (the ribbon expander)."""
    name = getattr(front, "name", None)
    if name:
        return str(name)
    blue = getattr(getattr(front, "blue_cp", None), "name", None)
    red = getattr(getattr(front, "red_cp", None), "name", None)
    if blue and red:
        return f"{blue}–{red}"
    return "front"


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


def _fighter_ratio(red: int, blue: int) -> float:
    """Red air-superiority airframes / blue's. 2.0 if blue fields none, 1.0 if neither."""
    if blue <= 0:
        return 2.0 if red > 0 else 1.0
    return red / blue


def _air_ratio(game: "Game") -> float:
    """Red air-superiority airframes / blue's (current, live)."""
    from game.theater.player import Player

    return _fighter_ratio(_fighters(game, Player.RED), _fighters(game, Player.BLUE))


def _red_sam_sites(game: "Game") -> int:
    """Alive red long+medium SAM sites: TGOs tasked LORAD / MERAD (the DEAD target set).

    Bands by the TGO's ``GroupTask`` exactly like ``phases._enemy_sam_sites`` (the #379
    correction: ``IadsRole`` cannot band this). getattr-guarded on ``ground_objects`` so
    a minimal duck-typed test theater with no TGOs reads 0 rather than raising.
    """
    from game.data.groups import GroupTask
    from game.theater.player import Player

    count = 0
    for tgo in getattr(game.theater, "ground_objects", []):
        if getattr(tgo, "task", None) not in (GroupTask.LORAD, GroupTask.MERAD):
            continue
        if tgo.is_friendly(Player.BLUE):
            continue
        if any(unit.alive for group in tgo.groups for unit in group.units):
            count += 1
    return count


def _red_base_count(game: "Game") -> int:
    """Red-held control points. getattr-guarded for minimal test theaters."""
    from game.theater.player import Player

    return sum(
        1
        for cp in getattr(game.theater, "controlpoints", [])
        if getattr(cp, "captured", None) is Player.RED
    )


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


def _current_sample(game: "Game", baseline: RedIntentBaseline) -> RedIntentSample:
    """This turn's turn-stable levels (banked in history + differenced for trends)."""
    from game.theater.player import Player

    return RedIntentSample(
        turn=game.turn,
        resolve=_red_resolve(game),
        front_advance=_front_advance(game, baseline),
        sam_alive=_red_sam_sites(game),
        red_fighters=_fighters(game, Player.RED),
        blue_fighters=_fighters(game, Player.BLUE),
        red_bases=_red_base_count(game),
        supply_health=_red_supply_health(game),
    )


def _trend_lookback(
    history: list[RedIntentSample],
    turn: int,
    lookback: int = TREND_LOOKBACK_TURNS,
) -> Optional[RedIntentSample]:
    """The sample this turn's trends are measured against, or None until history exists.

    Prefers the most recent sample at or before ``turn - lookback``; earlier in the
    campaign the oldest strictly-earlier sample stands in. Samples for ``turn`` itself
    are excluded so a same-turn re-init (which may already have banked this turn) never
    differences against itself -- trends stay idempotent. ``lookback`` defaults to the
    base ``TREND_LOOKBACK_TURNS`` (the ``red_intent_trend_window`` setting overrides it).
    """
    earlier = [s for s in history if s.turn < turn]
    if not earlier:
        return None
    target = turn - lookback
    at_or_before = [s for s in earlier if s.turn <= target]
    if at_or_before:
        return max(at_or_before, key=lambda s: s.turn)
    return min(earlier, key=lambda s: s.turn)


def _record_sample(game: "Game", sample: RedIntentSample) -> None:
    """Bank ``sample`` in the rolling history, replacing any same-turn entry (idempotent)
    and trimming to ``MEMORY_LENGTH``."""
    history = [
        s
        for s in (getattr(game, "red_intent_history", None) or [])
        if s.turn != sample.turn
    ]
    history.append(sample)
    history.sort(key=lambda s: s.turn)
    game.red_intent_history = history[-MEMORY_LENGTH:]


def collect_metrics(
    game: "Game", sample: RedIntentSample, prior: Optional[RedIntentSample]
) -> RedIntentMetrics:
    """Build this turn's classifier inputs from the current sample + the lookback sample.

    Trends are neutral (0 / False) whenever ``prior`` is None (turn 1 / no history yet),
    so the classifier degrades to the instantaneous v1 read with no rolling memory.
    """
    air_ratio = _fighter_ratio(sample.red_fighters, sample.blue_fighters)

    iads_trend = 0.0
    resolve_trend = 0.0
    base_trend = 0
    front_trend = 0.0
    blue_air_collapsing = False
    if prior is not None:
        if prior.sam_alive > 0:
            iads_trend = (prior.sam_alive - sample.sam_alive) / prior.sam_alive
        resolve_trend = sample.resolve - prior.resolve
        base_trend = sample.red_bases - prior.red_bases
        front_trend = sample.front_advance - prior.front_advance
        if prior.blue_fighters > 0:
            blue_lost = (
                prior.blue_fighters - sample.blue_fighters
            ) / prior.blue_fighters
            # An opportunity only if red's own air can exploit it (not itself suppressed).
            blue_air_collapsing = (
                blue_lost >= BLUE_AIR_COLLAPSE_FRAC and air_ratio >= SURGE_MIN_AIR_RATIO
            )

    # last_sitrep.captured = CPs BLUE took last turn = RED's base losses (a committed,
    # turn-stable fact, so this stays idempotent under re-init).
    sitrep = getattr(game, "last_sitrep", None)
    lost_base = bool(sitrep and getattr(sitrep, "captured", None))

    return RedIntentMetrics(
        ground_ratio=_ground_ratio(game),
        air_ratio=air_ratio,
        resolve=sample.resolve,
        front_advance=sample.front_advance,
        lost_base=lost_base,
        supply_health=sample.supply_health,
        iads_trend=iads_trend,
        resolve_trend=resolve_trend,
        base_trend=base_trend,
        front_trend=front_trend,
        blue_air_collapsing=blue_air_collapsing,
    )


# --- the decision ----------------------------------------------------------------------


def classify_red_intent(
    m: RedIntentMetrics, tuning: RedIntentTuning = DEFAULT_TUNING
) -> RedPosture:
    """Pick RED's posture (caller applies hysteresis + derives intensity).

    CONSOLIDATE when red is under pressure -- outnumbered on the ground, low resolve, a
    base lost, ground given up since the start, (P4) starved of supply, OR -- the rolling
    memory (A/C) -- its IADS being dismantled, resolve collapsing, bases bleeding, or the
    front eroding again over the lookback window. SURGE when red holds a clear ground
    advantage (or a blue-air-collapse *opportunity* at a lower bar) AND its air isn't
    suppressed AND (P4) it can sustain the push. ATTRITION otherwise -- the default, which
    also absorbs the dropped 'Feint' as a moderate-unpredictability middle.

    ``tuning`` shifts the ground bars by the boldness dial (``DEFAULT_TUNING`` = the base
    thresholds, so a positional ``classify_red_intent(m)`` is byte-identical to before).
    """
    starved = m.supply_health is not None and m.supply_health < STARVED_SUPPLY
    under_pressure = (
        m.ground_ratio <= tuning.consolidate_ground_ratio
        or m.resolve < CONSOLIDATE_RESOLVE
        or m.lost_base
        or m.front_advance >= FRONT_LOSS_EPSILON
        # --- rolling-memory pressure (A + C): sustained damage over the window ---
        or m.iads_trend >= IADS_COLLAPSE_TREND
        or m.resolve_trend <= RESOLVE_COLLAPSE_TREND
        or m.base_trend < 0
        or m.front_trend >= FRONT_EROSION_TREND
    )
    if starved or under_pressure:
        return RedPosture.CONSOLIDATE

    supplied = m.supply_health is None or m.supply_health >= SURGE_MIN_SUPPLY
    air_ok = m.air_ratio >= SURGE_MIN_AIR_RATIO
    if not (air_ok and supplied):
        return RedPosture.ATTRITION
    # Own clear advantage, or a transient blue-air-collapse opportunity at a lower bar.
    if m.ground_ratio >= tuning.surge_ground_ratio:
        return RedPosture.SURGE
    if (
        m.blue_air_collapsing
        and m.ground_ratio >= tuning.surge_opportunity_ground_ratio
    ):
        return RedPosture.SURGE

    return RedPosture.ATTRITION


def _intensity(
    m: RedIntentMetrics, posture: RedPosture, tuning: RedIntentTuning = DEFAULT_TUNING
) -> float:
    """How strongly ``posture`` is held, in [0, 1] (seam graduation, B).

    SURGE ramps from the floor at the surge threshold to 1.0 at a runaway advantage.
    CONSOLIDATE takes the worst of its pressure axes (how outnumbered / how low or
    fast-collapsing resolve / how much IADS lost / how starved / a lost base). ATTRITION
    is the neutral midpoint (its graduated seams are no-ops anyway). Anchored so a
    *typical* posture sits near ``DEFAULT_INTENSITY``. ``tuning`` moves the surge/
    consolidate ground anchors with the boldness dial (``DEFAULT_TUNING`` = the base).
    """
    if posture is RedPosture.SURGE:
        span = SURGE_STRONG_RATIO - tuning.surge_ground_ratio
        ramp = (
            _clamp01((m.ground_ratio - tuning.surge_ground_ratio) / span)
            if span > 0
            else 0.0
        )
        return _clamp01(SURGE_INTENSITY_FLOOR + (1.0 - SURGE_INTENSITY_FLOOR) * ramp)
    if posture is RedPosture.CONSOLIDATE:
        ground_floor = tuning.consolidate_ground_ratio or CONSOLIDATE_GROUND_RATIO
        severities = [
            _clamp01((ground_floor - m.ground_ratio) / ground_floor),
            _clamp01((CONSOLIDATE_RESOLVE - m.resolve) / CONSOLIDATE_RESOLVE),
            _clamp01(m.iads_trend),
            _clamp01(-m.resolve_trend / RESOLVE_COLLAPSE_SPAN),
        ]
        if m.supply_health is not None:
            severities.append(
                _clamp01((STARVED_SUPPLY - m.supply_health) / STARVED_SUPPLY)
            )
        if m.lost_base or m.base_trend < 0:
            severities.append(BASE_LOSS_SEVERITY)
        worst = max(severities) if severities else 0.0
        return _clamp01(
            CONSOLIDATE_INTENSITY_FLOOR + (1.0 - CONSOLIDATE_INTENSITY_FLOOR) * worst
        )
    return DEFAULT_INTENSITY


def _next_posture(
    current: Optional[RedPosture],
    entered_on_turn: Optional[int],
    turn: int,
    target: RedPosture,
    dwell: int = INTENT_MIN_DWELL_TURNS,
) -> RedPosture:
    """Asymmetric dwell: escalating needs the target to hold ``dwell`` turns;
    de-escalating (toward the lower-ranked, more defensive posture) applies at once.
    ``dwell`` defaults to the base ``INTENT_MIN_DWELL_TURNS`` (the ``red_intent_dwell_turns``
    setting overrides it via ``tuning_for``)."""
    if current is None or target is current:
        return target
    if _POSTURE_RANK[target] < _POSTURE_RANK[current]:
        return target  # de-escalation is immediate
    if turn - (entered_on_turn or 0) < dwell:
        return current  # escalation waits out the dwell
    return target


def _legibility(m: RedIntentMetrics) -> str:
    """The 'why' string -- the posture explains itself (the §40 legibility rule).

    Leads with the instantaneous read (ground/air/front) and then names whichever rolling
    trend drove the decision, so a memory-based consolidate reads its reason ("IADS
    falling", "losing bases") rather than looking like it fired on a healthy snapshot.
    """
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
    if m.iads_trend >= IADS_COLLAPSE_TREND:
        parts.append("IADS falling")
    if m.resolve_trend <= RESOLVE_COLLAPSE_TREND:
        parts.append("resolve collapsing")
    if m.base_trend < 0:
        parts.append("losing bases")
    if m.blue_air_collapsing:
        parts.append("enemy air spent")
    if m.supply_health is not None:
        parts.append(f"supply {round(m.supply_health * 100)}%")
    return " · ".join(parts)


def _intensity_word(posture: RedPosture, intensity: float) -> str:
    """A short 'how committed' word for the status detail (B legibility), or "".

    Surfaces the graduated intensity the aggressiveness/commit seams act on so the
    ribbon detail reads not just *what* red is doing but *how hard* -- a probing surge
    vs an all-in one, a cautious hold vs a dug-in one. ATTRITION carries no descriptor
    (its seams are neutral).
    """
    if posture is RedPosture.SURGE:
        if intensity >= 0.8:
            return "all-in"
        return "pressing" if intensity >= 0.55 else "probing"
    if posture is RedPosture.CONSOLIDATE:
        if intensity >= 0.8:
            return "dug in"
        return "defensive" if intensity >= 0.55 else "cautious"
    return ""


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
    once and never overwritten; the history bank replaces any same-turn sample).

    Latches ``game.red_intent_key`` + ``game.red_intent_intensity`` + a status line,
    announces transitions, and banks this turn's sample; the four planner seams read the
    result through ``active_red_intent`` / ``active_red_intensity``. Setting off => state
    cleared, so consumers see 'no posture' and behave stock.
    """
    if not getattr(game.settings, "red_intent", False):
        game.red_intent_key = None
        game.red_intent_entered_on_turn = None
        game.red_intent_status_line = None
        game.red_intent_intensity = None
        game.red_intent_fronts = {}
        return

    baseline = getattr(game, "red_intent_baseline", None)
    if baseline is None:
        baseline = snapshot_baseline(game)
        game.red_intent_baseline = baseline

    tuning = tuning_for(game)
    history = list(getattr(game, "red_intent_history", None) or [])
    prior = _trend_lookback(history, game.turn, tuning.trend_lookback_turns)
    sample = _current_sample(game, baseline)
    metrics = collect_metrics(game, sample, prior)
    target = classify_red_intent(metrics, tuning)
    current = _posture_from_key(getattr(game, "red_intent_key", None))
    new = _next_posture(
        current,
        getattr(game, "red_intent_entered_on_turn", None),
        game.turn,
        target,
        tuning.dwell_turns,
    )
    intensity = _intensity(metrics, new, tuning)

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
    game.red_intent_intensity = intensity
    word = _intensity_word(new, intensity)
    label = f"{new.display} ({word})" if word else new.display
    game.red_intent_status_line = f"{label} — {_legibility(metrics)}"
    _update_front_postures(game, metrics, tuning)
    _record_sample(game, sample)


def _update_front_postures(
    game: "Game", metrics: RedIntentMetrics, tuning: RedIntentTuning
) -> None:
    """Per-front posture resolution (D): classify each active front from its own ground
    balance + the shared theater signals, with per-front hysteresis. Latches
    ``game.red_intent_fronts`` (front key -> :class:`FrontPosture`); cleared to ``{}``
    when ``red_intent_per_front`` is off so the seam falls back to the theater posture.
    Idempotent under re-init (turn-stable inputs; a same-turn re-run keeps entry turns).
    """
    if not getattr(game.settings, "red_intent_per_front", True):
        game.red_intent_fronts = {}
        return
    prior = getattr(game, "red_intent_fronts", None) or {}
    updated: dict[str, FrontPosture] = {}
    for front in game.theater.conflicts():
        key = _front_key(front)
        if key is None:
            continue
        front_metrics = replace(metrics, ground_ratio=_front_ground_ratio(front))
        front_target = classify_red_intent(front_metrics, tuning)
        state = prior.get(key)
        front_current = _posture_from_key(state.posture) if state else None
        front_new = _next_posture(
            front_current,
            state.entered_on_turn if state else None,
            game.turn,
            front_target,
            tuning.dwell_turns,
        )
        entered = (
            state.entered_on_turn
            if (state is not None and front_new is front_current)
            else game.turn
        )
        updated[key] = FrontPosture(
            name=_front_name(front),
            posture=front_new.value,
            entered_on_turn=entered,
            intensity=_intensity(front_metrics, front_new, tuning),
        )
    game.red_intent_fronts = updated


def active_red_intent(game: "Game") -> Optional[RedPosture]:
    """The posture consumers read (the four planner seams + the SITREP/status surfaces)."""
    if not getattr(game.settings, "red_intent", False):
        return None
    return _posture_from_key(getattr(game, "red_intent_key", None))


def active_red_intensity(game: "Game") -> float:
    """The latched intensity the graduated seams read, or ``DEFAULT_INTENSITY``.

    Falls back to the neutral midpoint whenever the feature is off or intensity hasn't
    been latched (a pre-feature save, a bare test that set only a key) -- and the seam
    formulas are anchored so that midpoint reproduces the v1 flat constants.
    """
    if not getattr(game.settings, "red_intent", False):
        return DEFAULT_INTENSITY
    value = getattr(game, "red_intent_intensity", None)
    return DEFAULT_INTENSITY if value is None else float(value)


def sitrep_posture_line(game: "Game") -> Optional[str]:
    """The short RED-posture label for the SITREP band, or None when off/unresolved."""
    posture = active_red_intent(game)
    return posture.display if posture else None


def intensity_word(game: "Game") -> Optional[str]:
    """The "how committed" word ("all-in" / "pressing" / "dug in" ...) for the ribbon
    chip, or None when off/unresolved/ATTRITION. Surfaces the graduated intensity the
    seams act on so the map ribbon reads *how hard* red is pushing, not just *what*."""
    posture = active_red_intent(game)
    if posture is None:
        return None
    word = _intensity_word(posture, active_red_intensity(game))
    return word or None


def sitrep_posture_detail(game: "Game") -> Optional[str]:
    """The RED-posture detail line (intensity word + trend drivers) for the SITREP band,
    or None when off/unresolved. Surfaces the *why* behind the posture word -- the
    "Surging (all-in) — ground 4.0x · air holding · IADS falling" legibility string --
    so the smart trend/intensity read is visible on the kneeboard, not just hover text.
    """
    if active_red_intent(game) is None:
        return None
    return getattr(game, "red_intent_status_line", None)


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


# --- P2 (seams 2 + 3) + B graduation: unpredictability + aggressiveness ----------------


def unpredictability_modifier(game: "Game") -> int:
    """RED's posture contribution to its planner unpredictability (seam 2).

    Added to ``opfor_planner_unpredictability`` + the C2-decap bonus in
    ``targetorder._unpredictability_for`` (RED only), then clamped there. 0 when
    red_intent is off/unresolved, so the base setting is preserved byte-identically.
    Flat per posture (not intensity-graduated) -- it already stacks with C2 decap.
    """
    posture = active_red_intent(game)
    if posture is None:
        return 0
    return _POSTURE_UNPREDICTABILITY.get(posture, 0)


def effective_aggressiveness(game: "Game") -> int:
    """``opfor_autoplanner_aggressiveness`` biased by RED's posture + intensity (seam 3).

    Returns the raw setting when red_intent is off/unresolved or the posture is
    ATTRITION (neutral) -- byte-identical to v1. SURGE raises it (red commits more bases
    to offense), CONSOLIDATE lowers it (red defends everything); the magnitude scales
    with intensity about the v1 midpoint (``AGGRESSION_MID`` at ``DEFAULT_INTENSITY``), so
    a runaway red strips more and a marginal one only nudges.
    """
    base = int(getattr(game.settings, "opfor_autoplanner_aggressiveness", 0))
    posture = active_red_intent(game)
    if posture is None or posture is RedPosture.ATTRITION:
        return base
    magnitude = round(
        (
            AGGRESSION_MID
            + AGGRESSION_SPAN * (active_red_intensity(game) - DEFAULT_INTENSITY)
        )
        * tuning_for(game).seam_scale
    )
    delta = magnitude if posture is RedPosture.SURGE else -magnitude
    return max(0, min(100, base + delta))


def _front_posture_and_intensity(
    game: "Game", front: object
) -> tuple[Optional[RedPosture], float]:
    """The (posture, intensity) the ground-commit seam uses for ``front``.

    Prefers the per-front posture (D) when ``red_intent_per_front`` is on and the front
    resolves to a latched state; otherwise falls back to the theater-wide posture (a
    single-posture red, the setting off, or a duck-typed front with no cp ids)."""
    posture = active_red_intent(game)
    if posture is None:
        return None, DEFAULT_INTENSITY
    if front is not None and getattr(game.settings, "red_intent_per_front", True):
        key = _front_key(front)
        if key is not None:
            state = (getattr(game, "red_intent_fronts", None) or {}).get(key)
            if state is not None:
                front_posture = _posture_from_key(state.posture)
                if front_posture is not None:
                    return front_posture, state.intensity
    return posture, active_red_intensity(game)


def stance_commit_factor(game: "Game", front: object = None) -> float:
    """RED's ground-commitment bias for the ATTACK-stance thresholds (seam 4).

    >1 commits reserves sooner (SURGE reaches aggressive/elimination/breakthrough at a
    lower real advantage); <1 husbands them (CONSOLIDATE needs more advantage to attack,
    while still defending normally). Uses the **per-front** posture/intensity (D) for
    ``front`` when available -- so on a multi-front war red commits on the front it is
    winning and husbands on the one it is losing -- else the theater-wide read. The factor
    scales with intensity about the v1 midpoints (SURGE 1.35 / CONSOLIDATE 0.7 at
    ``DEFAULT_INTENSITY``) and with the boldness dial (``seam_scale``). 1.0 for a
    stock/observing red -- and, per the [DECIDED] 'authored windows win' rule, 1.0 while
    an authored ``red_tempo`` ground-offensive pulse owns red's stances, so the two never
    double-drive the front.
    """
    from game.fourteenth.red_tempo import ground_offensive_active

    if ground_offensive_active(game):
        return 1.0
    posture, intensity = _front_posture_and_intensity(game, front)
    if posture is None or posture is RedPosture.ATTRITION:
        return 1.0
    scale = tuning_for(game).seam_scale
    if posture is RedPosture.SURGE:
        deviation = (SURGE_COMMIT_MID - 1.0) + COMMIT_SPAN * (
            intensity - DEFAULT_INTENSITY
        )
    else:
        deviation = (CONSOLIDATE_COMMIT_MID - 1.0) - COMMIT_SPAN * (
            intensity - DEFAULT_INTENSITY
        )
    return round(1.0 + deviation * scale, 3)


def front_postures(game: "Game") -> list[dict[str, Optional[str]]]:
    """Per-front postures for the ribbon expander (D legibility), or [] to hide the block.

    Empty when red_intent is off, per-front is off, or there is only one active front
    (redundant with the theater posture). Each entry carries the front's display name,
    posture word, and intensity word -- so a divergent multi-front war reads at a glance.
    """
    if active_red_intent(game) is None or not getattr(
        game.settings, "red_intent_per_front", True
    ):
        return []
    fronts = getattr(game, "red_intent_fronts", None) or {}
    if len(fronts) < 2:
        return []
    result: list[dict[str, Optional[str]]] = []
    for state in fronts.values():
        posture = _posture_from_key(state.posture)
        if posture is None:
            continue
        result.append(
            {
                "name": state.name,
                "posture": posture.display,
                "intensity": _intensity_word(posture, state.intensity) or None,
            }
        )
    return result
