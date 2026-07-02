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
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

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
class RestrictedZone:
    """A circle where offensive tasking is forbidden (authored phases, W4).

    ``center_cp`` names a control point (resolved at runtime so the zone follows
    the campaign's real laydown); explicit ``x``/``y`` theater coordinates are the
    fallback for a zone anchored off-base. Radius is authored in NM.
    """

    radius_nm: float
    center_cp: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None
    name: str = ""


@dataclass(frozen=True)
class PhaseCondition:
    """An ``advance_when`` condition set: ANY satisfied field advances the arc.

    ``min_turn`` here is an acceleration pin *inside* the condition; the next
    phase's own ``min_turn`` is the scheduled escalation date. ``blue_will_below``
    couples escalation to the W1 political-will economy (Washington's patience for
    restraint runs out); ``enemy_iads_below`` releases escalation on rollback
    progress (ratio vs. the turn-0 baseline).
    """

    min_turn: Optional[int] = None
    blue_will_below: Optional[float] = None
    enemy_iads_below: Optional[float] = None


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
    #: Circles where offensive tasking is forbidden while this phase is active.
    restricted_zones: tuple[RestrictedZone, ...] = ()
    #: Strike-target classes still locked in this phase (TGO ``category`` strings,
    #: plus the special ``"airfield"`` for OCA against a control point).
    locked_target_classes: tuple[str, ...] = ()
    #: True for phases parsed from a campaign ``phases:`` block.
    authored: bool = False


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
        zones = []
        for zone in entry.get("restricted_zones") or []:
            if "radius_nm" not in zone or not (
                zone.get("center") or ("x" in zone and "y" in zone)
            ):
                raise ValueError(
                    f"restricted_zones: entry needs radius_nm and a center "
                    f"(CP name) or x/y: {zone!r}"
                )
            zones.append(
                RestrictedZone(
                    radius_nm=float(zone["radius_nm"]),
                    center_cp=zone.get("center"),
                    x=zone.get("x"),
                    y=zone.get("y"),
                    name=str(zone.get("name", "")),
                )
            )
        advance = entry.get("advance_when")
        condition = None
        if advance:
            condition = PhaseCondition(
                min_turn=advance.get("min_turn"),
                blue_will_below=advance.get("blue_will_below"),
                enemy_iads_below=advance.get("enemy_iads_below"),
            )
        phases.append(
            CampaignPhase(
                key=str(entry["key"]),
                name=str(entry.get("name", entry["key"])),
                narrative=str(entry.get("narrative", "")),
                emphasis=emphasis,
                min_turn=int(entry.get("min_turn", 0)),
                advance_when=condition,
                restricted_zones=tuple(zones),
                locked_target_classes=tuple(entry.get("locked_targets") or ()),
                authored=True,
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
        " · ROE restrictions active" if phase.restricted_zones else ""
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


def _resolved_zones(
    game: "Game", phase: CampaignPhase
) -> list[tuple[str, "object", float]]:
    """Resolve a phase's zones to (name, center Point, radius meters).

    A zone naming a control point absent from this theater resolves to nothing
    (logged once per resolution) rather than crashing -- authored data must never
    brick a campaign.
    """
    zones: list[tuple[str, object, float]] = []
    for zone in phase.restricted_zones:
        center = None
        if zone.center_cp is not None:
            for cp in game.theater.controlpoints:
                if cp.name == zone.center_cp:
                    center = cp.position
                    break
            if center is None:
                logging.warning(
                    "Restricted zone %r: no control point named %r in this theater",
                    zone.name or zone.center_cp,
                    zone.center_cp,
                )
        elif zone.x is not None and zone.y is not None:
            center = game.point_in_world(zone.x, zone.y)
        if center is not None:
            zones.append(
                (
                    zone.name or zone.center_cp or "Restricted zone",
                    center,
                    zone.radius_nm * 1852.0,
                )
            )
    return zones


def active_restricted_zones(game: "Game") -> list[tuple[str, "object", float]]:
    """The active phase's resolved zones -- the map layer / server payload feed."""
    phase = active_phase(game)
    if phase is None:
        return []
    return _resolved_zones(game, phase)


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
    for name, center, radius_m in _resolved_zones(game, phase):
        if center.distance_to_point(position) <= radius_m:  # type: ignore[attr-defined]
            return f"inside {name}"
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
    if not phase.restricted_zones and not phase.locked_target_classes:
        return []
    lines: list[tuple[str, str]] = []
    zone_bits = [
        f"{name} {radius_m / 1852.0:.0f} nm"
        for name, _center, radius_m in _resolved_zones(game, phase)
    ]
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


def arc_overview(game: "Game") -> list[dict[str, object]]:
    """The whole phase arc for the client expander (W3 item-1 UI).

    One dict per phase: key/name/narrative, the scheduled ``min_turn`` (0 = not
    turn-pinned -- Tier-0 arcs advance adaptively), the locked target classes,
    the zone names, and whether it is the current phase. Empty when phases are
    off or no phase has resolved yet.
    """
    if active_phase(game) is None:
        return []
    current = getattr(game, "current_phase_key", None)
    overview: list[dict[str, object]] = []
    for phase in _arc_for_display(game):
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
                "current": phase.key == current,
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
    """Enemy ground kills inside an active restricted zone this turn.

    The SOFT player enforcement: nothing stops the strike, but each kill inside a
    zone drains political will sharply (weighted in ``political_will.py``). Reads
    the debriefing's enemy ground-object losses (the strike-damage ledger; their
    theater units carry positions).
    """
    zones = active_restricted_zones(game)
    if not zones:
        return 0
    violations = 0
    ground_losses = getattr(debriefing, "ground_losses", None)
    if ground_losses is None:
        return 0
    for mapping in getattr(ground_losses, "enemy_ground_objects", []) or []:
        position = getattr(mapping.theater_unit, "position", None)
        if position is None:
            continue
        for _name, center, radius_m in zones:
            if center.distance_to_point(position) <= radius_m:  # type: ignore[attr-defined]
                violations += 1
                break
    return violations
