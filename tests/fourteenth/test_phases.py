"""Campaign phases (W3): the Tier-0 classifier, hysteresis, and planner emphasis.

Locks the §3.2 phase boundaries (incl. the pilot's absolute-SAM-floor gate and the
peer-fight guard), the §3.3 hysteresis (min-dwell, monotonic-forward default, the
asymmetric regression margin behind the authored-only flag), the §3.4 legibility
string, the per-turn update entry point's gating/idempotence, and the §4 soft
emphasis contract between game/fourteenth/phases.py and PlanNextAction.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Optional

from game.commander.tasks.compound.nextaction import PlanNextAction
from game.fourteenth.phases import (
    AIR_THREAT_FLOOR,
    FRONT_ADVANCE_EPSILON,
    IADS_OFFENSIVE_CEILING,
    IADS_ROLLBACK_HOLD,
    OFFENSIVE_METHODS,
    PHASE_MIN_DWELL_TURNS,
    PHASES,
    PhaseBaseline,
    PhaseMetrics,
    ROLLBACK_SAM_FLOOR,
    _next_phase_key,
    active_phase,
    classify,
    collect_metrics,
    legibility,
    update_campaign_phase,
)


def _metrics(
    *,
    sam_baseline: int = 12,
    iads_ratio: float = 1.0,
    air_threat_present: bool = False,
    front_delta: float = 0.0,
    recent_capture: bool = False,
    base_ratio: float = 0.5,
) -> PhaseMetrics:
    return PhaseMetrics(
        sam_baseline=sam_baseline,
        sam_alive=round(sam_baseline * iads_ratio),
        iads_ratio=iads_ratio,
        fighters_baseline=20,
        fighters_alive=20 if air_threat_present else 0,
        air_threat_present=air_threat_present,
        front_delta=front_delta,
        recent_capture=recent_capture,
        base_ratio=base_ratio,
    )


# --- §3.2 phase boundaries -----------------------------------------------------------


def test_dense_iads_opens_in_rollback() -> None:
    # Turn 0: every ratio is 1.0; the SAM belt keeps the opening in Rollback.
    assert classify(_metrics(sam_baseline=12, iads_ratio=1.0)) == "rollback"


def test_sam_floor_unmet_with_real_air_holds_air_superiority() -> None:
    # The pilot's "Air Superiority (fighter)" opening: no SAM belt, real MiGs.
    m = _metrics(sam_baseline=0, iads_ratio=0.0, air_threat_present=True)
    assert classify(m) == "rollback"


def test_sam_floor_unmet_and_weak_air_opens_in_interdiction() -> None:
    # The Khe Sanh finding: 0 SAM + no real air => no Rollback phase at all.
    m = _metrics(sam_baseline=0, iads_ratio=0.0, air_threat_present=False)
    assert classify(m) == "interdiction"


def test_sam_floor_boundary() -> None:
    below = _metrics(sam_baseline=ROLLBACK_SAM_FLOOR - 1, iads_ratio=1.0)
    at = _metrics(sam_baseline=ROLLBACK_SAM_FLOOR, iads_ratio=1.0)
    assert classify(below) == "interdiction"
    assert classify(at) == "rollback"


def test_degraded_iads_and_quiet_air_is_interdiction() -> None:
    m = _metrics(iads_ratio=IADS_ROLLBACK_HOLD - 0.1)
    assert classify(m) == "interdiction"


def test_peer_guard_air_threat_keeps_rollback_despite_dead_iads() -> None:
    # Slava Ukraini shape: IADS collapsed but red air is still a real threat --
    # Rollback only releases when BOTH are down.
    m = _metrics(iads_ratio=0.1, air_threat_present=True)
    assert classify(m) == "rollback"


def test_offensive_needs_low_iads_and_ground_movement() -> None:
    moving = _metrics(iads_ratio=0.2, front_delta=FRONT_ADVANCE_EPSILON)
    static = _metrics(iads_ratio=0.2, front_delta=0.0)
    captured = _metrics(iads_ratio=0.2, recent_capture=True)
    too_much_iads = _metrics(iads_ratio=IADS_OFFENSIVE_CEILING + 0.05, front_delta=0.2)
    assert classify(moving) == "offensive"
    assert classify(static) == "interdiction"
    assert classify(captured) == "offensive"
    assert classify(too_much_iads) == "interdiction"


# --- §3.3 hysteresis -----------------------------------------------------------------


def test_min_dwell_holds_the_phase() -> None:
    m = _metrics(iads_ratio=0.2)  # target: interdiction
    held = _next_phase_key("rollback", 5, 5 + PHASE_MIN_DWELL_TURNS - 1, m)
    released = _next_phase_key("rollback", 5, 5 + PHASE_MIN_DWELL_TURNS, m)
    assert held == "rollback"
    assert released == "interdiction"


def test_monotonic_forward_by_default() -> None:
    # The IADS "rebuilds" but v1 never regresses (most narratives don't un-happen).
    m = _metrics(iads_ratio=0.9)
    assert _next_phase_key("offensive", 1, 10, m) == "offensive"
    assert _next_phase_key("interdiction", 1, 10, m) == "interdiction"


def test_regression_needs_the_asymmetric_margin() -> None:
    # The authored-tier flag (P2): a rebuild must clear the 0.6 re-enter margin,
    # not merely re-cross the 0.5 hold line.
    noise = _metrics(iads_ratio=0.55)
    rebuild = _metrics(iads_ratio=0.65)
    assert (
        _next_phase_key("interdiction", 1, 10, noise, allow_regression=True)
        == "interdiction"
    )
    assert (
        _next_phase_key("interdiction", 1, 10, rebuild, allow_regression=True)
        == "rollback"
    )


def test_first_assignment_ignores_dwell() -> None:
    m = _metrics(sam_baseline=0, air_threat_present=False)
    assert _next_phase_key(None, None, 0, m) == "interdiction"


# --- §3.4 legibility -----------------------------------------------------------------


def test_legibility_explains_itself() -> None:
    m = _metrics(iads_ratio=0.22, air_threat_present=False, front_delta=0.0)
    line = legibility(PHASES["interdiction"], m)
    assert "Interdiction" in line
    assert "22%" in line
    assert "air threat low" in line
    assert "front static" in line


def test_legibility_without_a_sam_belt() -> None:
    m = _metrics(sam_baseline=0, iads_ratio=0.0)
    line = legibility(PHASES["interdiction"], m)
    assert "no enemy SAM belt" in line


# --- the per-turn entry point --------------------------------------------------------


def _duck_game(
    *,
    on: bool = True,
    turn: int = 0,
    current: Optional[str] = None,
    entered: Optional[int] = None,
    baseline: Optional[PhaseBaseline] = None,
) -> Any:
    messages: list[tuple[str, str]] = []
    game = SimpleNamespace(
        settings=SimpleNamespace(campaign_phases=on),
        theater=SimpleNamespace(
            iads_network=SimpleNamespace(nodes=[]),
            conflicts=lambda: [],
            controlpoints=[],
        ),
        air_wing_for=lambda player: SimpleNamespace(iter_squadrons=lambda: []),
        turn=turn,
        last_sitrep=None,
        current_phase_key=current,
        phase_entered_on_turn=entered,
        phase_status_line=None,
        phase_baseline=baseline,
        messages=messages,
    )
    game.message = lambda title, text="": messages.append((title, text))
    return game


def test_update_disarmed_clears_state() -> None:
    game = _duck_game(on=False, current="rollback", entered=1)
    update_campaign_phase(game)
    assert game.current_phase_key is None
    assert game.phase_entered_on_turn is None
    assert game.phase_status_line is None
    assert active_phase(game) is None


def test_update_snapshots_baseline_and_assigns_opening_phase() -> None:
    game = _duck_game(on=True, turn=0)
    update_campaign_phase(game)
    # An empty theater has no SAM belt and no air: the Khe Sanh opening.
    assert game.phase_baseline is not None
    assert game.current_phase_key == "interdiction"
    assert game.phase_entered_on_turn == 0
    assert game.phase_status_line is not None
    assert active_phase(game) is PHASES["interdiction"]
    # The campaign-start assignment is not announced...
    assert game.messages == []
    # ...and a same-turn re-init (initialize_turn runs multiple times) is stable.
    update_campaign_phase(game)
    assert game.current_phase_key == "interdiction"
    assert game.messages == []


def test_update_announces_a_transition_once() -> None:
    # Start in rollback (as if the belt existed), with the live theater empty the
    # classifier targets interdiction once the dwell releases.
    baseline = PhaseBaseline(sam_groups=12, enemy_fighters=0)
    game = _duck_game(
        on=True,
        turn=PHASE_MIN_DWELL_TURNS,
        current="rollback",
        entered=0,
        baseline=baseline,
    )
    update_campaign_phase(game)
    assert game.current_phase_key == "interdiction"
    assert len(game.messages) == 1
    assert "Interdiction" in game.messages[0][0]
    # Re-init the same turn: no phase change, no repeat announcement.
    update_campaign_phase(game)
    assert len(game.messages) == 1


def test_collect_metrics_reads_the_duck_theater() -> None:
    baseline = PhaseBaseline(
        sam_groups=4, enemy_fighters=10, front_fractions={"a:b": 0.5}
    )
    game = _duck_game(on=True)
    m = collect_metrics(game, baseline)
    assert m.sam_baseline == 4
    assert m.sam_alive == 0
    assert m.iads_ratio == 0.0
    assert m.fighters_alive == 0
    assert not m.air_threat_present
    # No live front matches the baseline key: no vote, front reads static.
    assert m.front_delta == 0.0


# --- §4 planner emphasis -------------------------------------------------------------


def test_factories_and_phase_orderings_stay_in_sync() -> None:
    factories = list(PlanNextAction._OFFENSIVE_FACTORIES)
    assert factories == list(OFFENSIVE_METHODS)
    for phase in PHASES.values():
        assert sorted(phase.emphasis) == sorted(OFFENSIVE_METHODS), phase.key


def _planner_state(coalition: Any) -> Any:
    return SimpleNamespace(context=SimpleNamespace(coalition=coalition))


def _coalition(game: Any, blue: bool) -> Any:
    return SimpleNamespace(
        player=SimpleNamespace(is_blue=blue),
        game=game,
    )


def test_offensive_order_stock_without_a_phase() -> None:
    task = PlanNextAction(aircraft_cold_start=False)
    game = _duck_game(on=False)
    order = task._offensive_order(_planner_state(_coalition(game, blue=True)))
    assert order == list(OFFENSIVE_METHODS)


def test_offensive_order_follows_the_blue_phase() -> None:
    task = PlanNextAction(aircraft_cold_start=False)
    game = _duck_game(on=True, current="rollback", entered=0)
    order = task._offensive_order(_planner_state(_coalition(game, blue=True)))
    assert order == list(PHASES["rollback"].emphasis)
    assert order[0] == "DegradeIads"


def test_red_planner_keeps_stock_order() -> None:
    task = PlanNextAction(aircraft_cold_start=False)
    game = _duck_game(on=True, current="offensive", entered=0)
    order = task._offensive_order(_planner_state(_coalition(game, blue=False)))
    assert order == list(OFFENSIVE_METHODS)


def test_each_valid_method_keeps_the_reactive_prefix_and_tail() -> None:
    task = PlanNextAction(aircraft_cold_start=False)
    game = _duck_game(on=True, current="offensive", entered=0)
    state = _planner_state(_coalition(game, blue=True))
    names = [type(method[0]).__name__ for method in task.each_valid_method(state)]
    # The §17 boundary: support/defense lead in fixed order; recovery closes.
    assert names[:3] == ["TheaterSupport", "ProtectAirSpace", "DefendBases"]
    assert names[-1] == "RecoverySupport"
    assert names[3:-1] == list(PHASES["offensive"].emphasis)
    assert names[3] == "CaptureBases"
