"""§55 Red Intent P0 -- observe-only resolver.

Covers the pure decision logic (classifier, asymmetric hysteresis, key round-trip,
economy-independent supply term) and the end-to-end resolve/latch/surface path through
a minimal duck-typed fake game. No planner seam is wired in P0, so nothing here touches
the commander -- that lands with P1's tests.
"""

from types import SimpleNamespace
from typing import Optional

import pytest

from game.commander.tasks.compound.nextaction import PlanNextAction
from game.commander.tasks.primitive.aggressiveattack import AggressiveAttack
from game.commander.tasks.primitive.defensivestance import DefensiveStance
from game.commander.tasks.targetorder import _unpredictability_for
from game.fourteenth.red_intent import (
    CONSOLIDATE_GROUND_RATIO,
    INTENT_MIN_DWELL_TURNS,
    RedIntentMetrics,
    RedPosture,
    SURGE_GROUND_RATIO,
    _POSTURE_EMPHASIS,
    _next_posture,
    _posture_from_key,
    _red_supply_health,
    active_red_intent,
    classify_red_intent,
    effective_aggressiveness,
    offensive_emphasis,
    sitrep_posture_line,
    stance_commit_factor,
    unpredictability_modifier,
    update_red_intent,
)


def _metrics(
    ground_ratio: float = 1.0,
    air_ratio: float = 1.0,
    resolve: float = 100.0,
    front_advance: float = 0.0,
    lost_base: bool = False,
    supply_health: Optional[float] = None,
) -> RedIntentMetrics:
    return RedIntentMetrics(
        ground_ratio=ground_ratio,
        air_ratio=air_ratio,
        resolve=resolve,
        front_advance=front_advance,
        lost_base=lost_base,
        supply_health=supply_health,
    )


# --- classifier ----------------------------------------------------------------------


def test_surge_on_clear_advantage() -> None:
    assert classify_red_intent(_metrics(ground_ratio=2.0)) is RedPosture.SURGE


def test_attrition_is_the_default() -> None:
    assert classify_red_intent(_metrics(ground_ratio=1.0)) is RedPosture.ATTRITION


def test_consolidate_when_outnumbered() -> None:
    m = _metrics(ground_ratio=CONSOLIDATE_GROUND_RATIO - 0.1)
    assert classify_red_intent(m) is RedPosture.CONSOLIDATE


def test_low_resolve_overrides_a_ground_advantage() -> None:
    # A collapsing regime turtles even when it outnumbers on the ground.
    m = _metrics(ground_ratio=2.0, resolve=20.0)
    assert classify_red_intent(m) is RedPosture.CONSOLIDATE


def test_a_lost_base_forces_consolidate() -> None:
    m = _metrics(ground_ratio=2.0, lost_base=True)
    assert classify_red_intent(m) is RedPosture.CONSOLIDATE


def test_giving_ground_forces_consolidate() -> None:
    m = _metrics(ground_ratio=2.0, front_advance=0.2)
    assert classify_red_intent(m) is RedPosture.CONSOLIDATE


def test_air_suppression_blocks_surge_but_not_to_consolidate() -> None:
    m = _metrics(ground_ratio=2.0, air_ratio=0.2)
    assert classify_red_intent(m) is RedPosture.ATTRITION


# --- §53 supply coupling (P4 wiring, exercised via the metric) -----------------------


def test_starved_supply_forces_consolidate() -> None:
    m = _metrics(ground_ratio=2.0, supply_health=0.1)
    assert classify_red_intent(m) is RedPosture.CONSOLIDATE


def test_healthy_supply_allows_surge() -> None:
    m = _metrics(ground_ratio=2.0, supply_health=0.8)
    assert classify_red_intent(m) is RedPosture.SURGE


def test_low_supply_blocks_surge_without_starving() -> None:
    # Between STARVED (0.35) and SURGE_MIN (0.5): not starved, but can't sustain a push.
    m = _metrics(ground_ratio=2.0, supply_health=0.4)
    assert classify_red_intent(m) is RedPosture.ATTRITION


def test_supply_none_is_ignored() -> None:
    # P0 / economy off: the supply terms drop out; the ground read decides.
    assert classify_red_intent(_metrics(ground_ratio=2.0, supply_health=None)) is (
        RedPosture.SURGE
    )


# --- asymmetric hysteresis -----------------------------------------------------------


def test_first_resolution_takes_the_target_immediately() -> None:
    assert _next_posture(None, None, 3, RedPosture.SURGE) is RedPosture.SURGE


def test_escalation_waits_out_the_dwell() -> None:
    # Entered ATTRITION on turn 5; one turn later (< dwell) a SURGE target is held off.
    got = _next_posture(RedPosture.ATTRITION, 5, 5 + 1, RedPosture.SURGE)
    assert got is RedPosture.ATTRITION


def test_escalation_applies_after_the_dwell() -> None:
    got = _next_posture(
        RedPosture.ATTRITION, 5, 5 + INTENT_MIN_DWELL_TURNS, RedPosture.SURGE
    )
    assert got is RedPosture.SURGE


def test_de_escalation_to_consolidate_is_immediate() -> None:
    got = _next_posture(RedPosture.SURGE, 5, 5 + 1, RedPosture.CONSOLIDATE)
    assert got is RedPosture.CONSOLIDATE


def test_surge_to_attrition_is_immediate() -> None:
    got = _next_posture(RedPosture.SURGE, 5, 5 + 1, RedPosture.ATTRITION)
    assert got is RedPosture.ATTRITION


# --- key round-trip ------------------------------------------------------------------


def test_posture_key_round_trip() -> None:
    for posture in RedPosture:
        assert _posture_from_key(posture.value) is posture


def test_unknown_or_missing_key_is_none() -> None:
    assert _posture_from_key(None) is None
    assert _posture_from_key("not-a-posture") is None


# --- economy independence ------------------------------------------------------------


def test_supply_health_is_none_when_war_economy_absent() -> None:
    game = SimpleNamespace(settings=SimpleNamespace(), red=SimpleNamespace())
    assert _red_supply_health(game) is None  # type: ignore[arg-type]


# --- the resolve/latch/surface path (minimal fake game) ------------------------------


class _FakeAirWing:
    def iter_squadrons(self) -> list[object]:
        return []


class _FakeFront:
    def __init__(self, red_units: int, blue_units: int) -> None:
        self.blue_cp = SimpleNamespace(id=1, deployable_front_line_units=blue_units)
        self.red_cp = SimpleNamespace(id=2, deployable_front_line_units=red_units)
        self.route_length = 100.0
        self._blue_route_progress = 50.0


class _FakeTheater:
    def __init__(self, fronts: tuple[object, ...]) -> None:
        self._fronts = fronts

    def conflicts(self) -> list[object]:
        return list(self._fronts)


class _FakeGame:
    def __init__(
        self, red_intent: bool = True, fronts: tuple[object, ...] = (), turn: int = 1
    ):
        self.settings = SimpleNamespace(red_intent=red_intent)
        self.theater = _FakeTheater(fronts)
        self.red = SimpleNamespace(political_will=100.0)
        self.last_sitrep = None
        self.turn = turn
        self.messages: list[tuple[str, str]] = []
        self.red_intent_key: Optional[str] = None
        self.red_intent_entered_on_turn: Optional[int] = None
        self.red_intent_status_line: Optional[str] = None
        self.red_intent_baseline: object = None

    def air_wing_for(self, player: object) -> _FakeAirWing:
        return _FakeAirWing()

    def message(self, title: str, body: str) -> None:
        self.messages.append((title, body))


def test_setting_off_clears_state() -> None:
    game = _FakeGame(red_intent=False)
    stale: Optional[str] = "surge"
    game.red_intent_key = stale
    game.red_intent_status_line = stale
    update_red_intent(game)  # type: ignore[arg-type]
    assert game.red_intent_key is None
    assert game.red_intent_status_line is None
    assert active_red_intent(game) is None  # type: ignore[arg-type]


def test_default_posture_latches_and_surfaces() -> None:
    # No fronts, no squadrons, full resolve -> the ATTRITION default.
    game = _FakeGame(red_intent=True)
    update_red_intent(game)  # type: ignore[arg-type]
    assert game.red_intent_key == RedPosture.ATTRITION.value
    assert game.red_intent_entered_on_turn == 1
    assert active_red_intent(game) is RedPosture.ATTRITION  # type: ignore[arg-type]
    assert sitrep_posture_line(game) == "Attrition"  # type: ignore[arg-type]
    # First resolution announces nothing (no prior posture to transition from).
    assert game.messages == []


def test_ground_dominant_red_surges() -> None:
    game = _FakeGame(red_intent=True, fronts=(_FakeFront(red_units=20, blue_units=5),))
    update_red_intent(game)  # type: ignore[arg-type]
    assert game.red_intent_key == RedPosture.SURGE.value
    assert game.red_intent_baseline is not None  # snapshotted once


def test_resolve_is_idempotent_within_a_turn() -> None:
    game = _FakeGame(red_intent=True, fronts=(_FakeFront(red_units=20, blue_units=5),))
    update_red_intent(game)  # type: ignore[arg-type]
    entered = game.red_intent_entered_on_turn
    update_red_intent(game)  # type: ignore[arg-type]  # re-init same turn
    assert game.red_intent_key == RedPosture.SURGE.value
    assert game.red_intent_entered_on_turn == entered
    assert game.messages == []  # no spurious transition message


# --- P1: offensive-emphasis seam -----------------------------------------------------


def test_attrition_uses_the_stock_order() -> None:
    # ATTRITION is the neutral default -> no reorder (None -> stock in the planner).
    game = _FakeGame(red_intent=True)
    game.red_intent_key = RedPosture.ATTRITION.value
    assert offensive_emphasis(game) is None  # type: ignore[arg-type]


def test_offensive_emphasis_is_none_when_off() -> None:
    game = _FakeGame(red_intent=False)
    game.red_intent_key = RedPosture.SURGE.value
    assert offensive_emphasis(game) is None  # type: ignore[arg-type]


def test_surge_and_consolidate_have_distinct_orderings() -> None:
    surge = _POSTURE_EMPHASIS[RedPosture.SURGE]
    consolidate = _POSTURE_EMPHASIS[RedPosture.CONSOLIDATE]
    assert surge[0] == "CaptureBases"  # surge takes ground first
    assert consolidate[0] == "InterdictReinforcements"  # consolidate blunts the buildup
    assert surge != consolidate


def test_emphasis_tuples_match_the_offensive_factory_set() -> None:
    # Sync lock: every posture ordering must be a permutation of the planner's real
    # offensive methods, so a rename/typo can never silently drop or duplicate one.
    factories = set(PlanNextAction._OFFENSIVE_FACTORIES)
    for posture, emphasis in _POSTURE_EMPHASIS.items():
        assert set(emphasis) == factories, posture
        assert len(emphasis) == len(factories), posture  # no duplicates


def _order_for(game: object) -> list[str]:
    task = PlanNextAction(aircraft_cold_start=False)
    state = SimpleNamespace(
        context=SimpleNamespace(
            coalition=SimpleNamespace(player=SimpleNamespace(is_blue=False), game=game)
        )
    )
    return task._offensive_order(state)  # type: ignore[arg-type]


def test_offensive_order_follows_red_posture() -> None:
    game = _FakeGame(red_intent=True)
    game.red_intent_key = RedPosture.SURGE.value
    assert _order_for(game) == list(_POSTURE_EMPHASIS[RedPosture.SURGE])


def test_offensive_order_is_stock_when_red_intent_off() -> None:
    game = _FakeGame(red_intent=False)
    game.red_intent_key = RedPosture.SURGE.value  # latched but feature off -> ignored
    assert _order_for(game) == list(PlanNextAction._OFFENSIVE_FACTORIES)


# --- P2: unpredictability + aggressiveness seams -------------------------------------


def test_unpredictability_modifier_by_posture() -> None:
    game = _FakeGame(red_intent=True)
    game.red_intent_key = RedPosture.ATTRITION.value
    assert unpredictability_modifier(game) == 15  # type: ignore[arg-type]
    game.red_intent_key = RedPosture.SURGE.value
    assert unpredictability_modifier(game) == 0  # type: ignore[arg-type]
    game.red_intent_key = RedPosture.CONSOLIDATE.value
    assert unpredictability_modifier(game) == 5  # type: ignore[arg-type]


def test_unpredictability_modifier_zero_when_off() -> None:
    game = _FakeGame(red_intent=False)
    game.red_intent_key = RedPosture.ATTRITION.value
    assert unpredictability_modifier(game) == 0  # type: ignore[arg-type]


def _aggr_game(
    posture: Optional[str], aggr: int = 50, red_intent: bool = True
) -> "_FakeGame":
    game = _FakeGame(red_intent=red_intent)
    game.settings = SimpleNamespace(
        red_intent=red_intent, opfor_autoplanner_aggressiveness=aggr
    )
    game.red_intent_key = posture
    return game


def test_effective_aggressiveness_by_posture() -> None:
    surge = _aggr_game(RedPosture.SURGE.value, 50)
    consolidate = _aggr_game(RedPosture.CONSOLIDATE.value, 50)
    attrition = _aggr_game(RedPosture.ATTRITION.value, 50)
    assert effective_aggressiveness(surge) == 80  # type: ignore[arg-type]
    assert effective_aggressiveness(consolidate) == 20  # type: ignore[arg-type]
    assert effective_aggressiveness(attrition) == 50  # type: ignore[arg-type]


def test_effective_aggressiveness_clamps() -> None:
    hot = _aggr_game(RedPosture.SURGE.value, 90)
    cold = _aggr_game(RedPosture.CONSOLIDATE.value, 10)
    assert effective_aggressiveness(hot) == 100  # type: ignore[arg-type]
    assert effective_aggressiveness(cold) == 0  # type: ignore[arg-type]


def test_effective_aggressiveness_off_is_raw_setting() -> None:
    # red_intent off -> posture unresolved -> the raw setting, unbiased.
    game = _aggr_game(RedPosture.SURGE.value, 50, red_intent=False)
    assert effective_aggressiveness(game) == 50  # type: ignore[arg-type]


def _unpred_state(
    game: "_FakeGame", is_blue: bool, opfor: int = 10, ownfor: int = 0
) -> SimpleNamespace:
    settings = SimpleNamespace(
        red_intent=getattr(game.settings, "red_intent", False),
        opfor_planner_unpredictability=opfor,
        ownfor_planner_unpredictability=ownfor,
        c2_decapitation_effects=False,
    )
    game.settings = settings
    return SimpleNamespace(
        context=SimpleNamespace(
            coalition=SimpleNamespace(
                player=SimpleNamespace(is_blue=is_blue), game=game
            ),
            settings=settings,
            theater=SimpleNamespace(),
        )
    )


def test_red_unpredictability_includes_posture_modifier() -> None:
    game = _FakeGame(red_intent=True)
    game.red_intent_key = RedPosture.ATTRITION.value
    state = _unpred_state(game, is_blue=False, opfor=10)
    result = _unpredictability_for(state)  # type: ignore[arg-type]
    assert result == 25  # 10 base + 15 attrition


def test_blue_unpredictability_ignores_red_posture() -> None:
    game = _FakeGame(red_intent=True)
    game.red_intent_key = RedPosture.ATTRITION.value
    state = _unpred_state(game, is_blue=True, ownfor=8)
    # Blue base only; the red-posture modifier is never applied to blue.
    assert _unpredictability_for(state) == 8  # type: ignore[arg-type]


# --- P3: ground-husbanding seam ------------------------------------------------------


def _commit_game(posture: Optional[str], red_intent: bool = True) -> "_FakeGame":
    game = _FakeGame(red_intent=red_intent)
    game.settings = SimpleNamespace(red_intent=red_intent, campaign_phases=False)
    game.red_intent_key = posture
    return game


def test_stance_commit_factor_by_posture() -> None:
    surge = _commit_game(RedPosture.SURGE.value)
    consolidate = _commit_game(RedPosture.CONSOLIDATE.value)
    attrition = _commit_game(RedPosture.ATTRITION.value)
    assert stance_commit_factor(surge) == 1.35  # type: ignore[arg-type]
    assert stance_commit_factor(consolidate) == 0.7  # type: ignore[arg-type]
    assert stance_commit_factor(attrition) == 1.0  # type: ignore[arg-type]


def test_stance_commit_factor_off_is_neutral() -> None:
    game = _commit_game(RedPosture.SURGE.value, red_intent=False)
    assert stance_commit_factor(game) == 1.0  # type: ignore[arg-type]


def test_stance_commit_factor_yields_to_red_tempo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    game = _commit_game(RedPosture.SURGE.value)
    monkeypatch.setattr(
        "game.fourteenth.red_tempo.ground_offensive_active", lambda g: True
    )
    # An authored pulse owns red's stances -> P3 defers even in SURGE.
    assert stance_commit_factor(game) == 1.0  # type: ignore[arg-type]


def _stance_balance(
    task_cls: type,
    f_units: int,
    e_units: int,
    game: object,
    is_blue: bool = False,
) -> float:
    coalition = SimpleNamespace(player=SimpleNamespace(is_blue=is_blue), game=game)
    friendly = SimpleNamespace(deployable_front_line_units=f_units, coalition=coalition)
    enemy = SimpleNamespace(deployable_front_line_units=e_units, coalition=coalition)
    front = SimpleNamespace(
        control_point_friendly_to=lambda p: friendly,
        control_point_hostile_to=lambda p: enemy,
    )
    task = task_cls(front, SimpleNamespace(is_blue=is_blue))
    return task.ground_force_balance


def test_surge_inflates_attack_stance_balance() -> None:
    game = _commit_game(RedPosture.SURGE.value)
    # AGGRESSIVE is an attack stance -> raw balance 1.0 inflated by 1.35.
    assert _stance_balance(AggressiveAttack, 10, 10, game) == 1.35


def test_consolidate_deflates_attack_but_not_defensive() -> None:
    game = _commit_game(RedPosture.CONSOLIDATE.value)
    # AGGRESSIVE (attack) is deflated; DEFENSIVE (non-attack) keeps the raw balance,
    # so consolidate tempers the attack without forcing a retreat.
    assert _stance_balance(AggressiveAttack, 10, 10, game) == 0.7
    assert _stance_balance(DefensiveStance, 10, 10, game) == 1.0


def test_blue_attack_stance_balance_is_unscaled() -> None:
    game = _commit_game(RedPosture.SURGE.value)
    # A blue stance task must never pick up red's posture.
    assert _stance_balance(AggressiveAttack, 10, 10, game, is_blue=True) == 1.0
