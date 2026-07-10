"""§55 Red Intent -- posture classifier, the four planner seams, and the §53 join.

Covers the pure decision logic (classifier, asymmetric hysteresis, key round-trip,
economy-coupled supply term) and the end-to-end resolve/latch/surface path through a
minimal duck-typed fake game (P0), plus the four planner seams (P1 offensive emphasis,
P2 unpredictability + aggressiveness, P3 ground husbanding), and the P4 war-economy join
exercised against a stubbed war_economy module (the real §53 producer lands separately).
"""

import sys
from types import ModuleType, SimpleNamespace
from typing import Optional

import pytest

from game.commander.tasks.compound.nextaction import PlanNextAction
from game.commander.tasks.primitive.aggressiveattack import AggressiveAttack
from game.commander.tasks.primitive.defensivestance import DefensiveStance
from game.commander.tasks.targetorder import _unpredictability_for
from game.fourteenth.red_intent import (
    CONSOLIDATE_GROUND_RATIO,
    DEFAULT_INTENSITY,
    IADS_COLLAPSE_TREND,
    INTENT_MIN_DWELL_TURNS,
    MEMORY_LENGTH,
    RESOLVE_COLLAPSE_TREND,
    RedIntentMetrics,
    RedIntentSample,
    RedPosture,
    SURGE_GROUND_RATIO,
    SURGE_OPPORTUNITY_GROUND_RATIO,
    SURGE_STRONG_RATIO,
    _POSTURE_EMPHASIS,
    _intensity,
    _next_posture,
    _posture_from_key,
    _record_sample,
    _red_supply_health,
    _trend_lookback,
    active_red_intensity,
    active_red_intent,
    classify_red_intent,
    collect_metrics,
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
    iads_trend: float = 0.0,
    resolve_trend: float = 0.0,
    base_trend: int = 0,
    front_trend: float = 0.0,
    blue_air_collapsing: bool = False,
) -> RedIntentMetrics:
    return RedIntentMetrics(
        ground_ratio=ground_ratio,
        air_ratio=air_ratio,
        resolve=resolve,
        front_advance=front_advance,
        lost_base=lost_base,
        supply_health=supply_health,
        iads_trend=iads_trend,
        resolve_trend=resolve_trend,
        base_trend=base_trend,
        front_trend=front_trend,
        blue_air_collapsing=blue_air_collapsing,
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
    def __init__(
        self,
        fronts: tuple[object, ...],
        ground_objects: tuple[object, ...] = (),
        controlpoints: tuple[object, ...] = (),
    ) -> None:
        self._fronts = fronts
        self.ground_objects = list(ground_objects)
        self.controlpoints = list(controlpoints)

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
        self.red_intent_history: list[RedIntentSample] = []
        self.red_intent_intensity: Optional[float] = None

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


# --- P4: the §53 war-economy join (stubbed, to prove it wires end-to-end) ------------


def _stub_war_economy(monkeypatch: pytest.MonkeyPatch, health: float) -> None:
    """Inject a fake `game.fourteenth.war_economy` exposing coalition_supply_health so
    the dynamic-import join in `_red_supply_health` resolves without the real §53."""
    fake = ModuleType("game.fourteenth.war_economy")
    setattr(fake, "coalition_supply_health", lambda game, coalition: health)
    monkeypatch.setitem(sys.modules, "game.fourteenth.war_economy", fake)


def test_supply_health_reads_a_stubbed_war_economy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_war_economy(monkeypatch, 0.42)
    game = _FakeGame(red_intent=True)
    game.settings = SimpleNamespace(red_intent=True, war_economy=True)
    assert _red_supply_health(game) == 0.42  # type: ignore[arg-type]


def test_starved_economy_forces_a_winning_red_to_consolidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Ground-dominant red (4:1) would SURGE on its own; a starved war economy overrides
    # that to CONSOLIDATE -- the §53->§55 join lit up: bomb the supply, red digs in.
    _stub_war_economy(monkeypatch, 0.1)
    game = _FakeGame(red_intent=True, fronts=(_FakeFront(red_units=20, blue_units=5),))
    game.settings = SimpleNamespace(red_intent=True, war_economy=True)
    update_red_intent(game)  # type: ignore[arg-type]
    assert game.red_intent_key == RedPosture.CONSOLIDATE.value


def test_supplied_economy_lets_a_winning_red_surge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The same winning red, but well supplied -> the economy doesn't hold it back.
    _stub_war_economy(monkeypatch, 0.9)
    game = _FakeGame(red_intent=True, fronts=(_FakeFront(red_units=20, blue_units=5),))
    game.settings = SimpleNamespace(red_intent=True, war_economy=True)
    update_red_intent(game)  # type: ignore[arg-type]
    assert game.red_intent_key == RedPosture.SURGE.value


# =====================================================================================
# Smarter red (2026-07-10): rolling trend memory (A) + battle-reading (C) + intensity (B)
# =====================================================================================


def _sample(
    turn: int,
    resolve: float = 100.0,
    front_advance: float = 0.0,
    sam_alive: int = 8,
    red_fighters: int = 10,
    blue_fighters: int = 10,
    red_bases: int = 5,
    supply_health: Optional[float] = None,
) -> RedIntentSample:
    return RedIntentSample(
        turn=turn,
        resolve=resolve,
        front_advance=front_advance,
        sam_alive=sam_alive,
        red_fighters=red_fighters,
        blue_fighters=blue_fighters,
        red_bases=red_bases,
        supply_health=supply_health,
    )


def _fake_sam() -> SimpleNamespace:
    """A minimal live RED long-range SAM TGO for the theater ground-object accessor."""
    from game.data.groups import GroupTask

    return SimpleNamespace(
        task=GroupTask.LORAD,
        is_friendly=lambda player: False,  # not friendly to blue => red-owned
        groups=[SimpleNamespace(units=[SimpleNamespace(alive=True)])],
    )


# --- C: trend signals bias a ground-dominant red toward CONSOLIDATE ------------------


def test_iads_being_dismantled_forces_consolidate() -> None:
    # Red outnumbers on the ground (would SURGE) but its SAM belt is falling -> dig in.
    m = _metrics(ground_ratio=2.0, iads_trend=IADS_COLLAPSE_TREND + 0.1)
    assert classify_red_intent(m) is RedPosture.CONSOLIDATE


def test_collapsing_resolve_trend_forces_consolidate() -> None:
    # Resolve is still above the absolute floor, but falling fast -> the derivative bites.
    m = _metrics(
        ground_ratio=2.0, resolve=80.0, resolve_trend=RESOLVE_COLLAPSE_TREND - 1
    )
    assert classify_red_intent(m) is RedPosture.CONSOLIDATE


def test_bleeding_bases_over_the_window_forces_consolidate() -> None:
    m = _metrics(ground_ratio=2.0, base_trend=-1)
    assert classify_red_intent(m) is RedPosture.CONSOLIDATE


def test_front_eroding_again_forces_consolidate() -> None:
    # The cumulative front_advance is still shallow, but it moved against red over the
    # window -> the trend catches renewed erosion after a plateau.
    m = _metrics(ground_ratio=2.0, front_advance=0.0, front_trend=0.1)
    assert classify_red_intent(m) is RedPosture.CONSOLIDATE


# --- C: the blue-air-collapse opportunity window ------------------------------------


def test_blue_air_collapse_opens_a_surge_at_a_lower_ground_bar() -> None:
    # Rough ground parity (below the normal SURGE bar) but blue's air just cratered ->
    # red pounces through the transient gap.
    m = _metrics(ground_ratio=SURGE_OPPORTUNITY_GROUND_RATIO, blue_air_collapsing=True)
    assert m.ground_ratio < SURGE_GROUND_RATIO  # would be ATTRITION without the window
    assert classify_red_intent(m) is RedPosture.SURGE


def test_opportunity_window_still_needs_a_modest_edge() -> None:
    # Blue air collapsed but red has no ground edge at all -> no reckless surge.
    m = _metrics(ground_ratio=1.0, blue_air_collapsing=True)
    assert classify_red_intent(m) is RedPosture.ATTRITION


def test_opportunity_window_does_not_override_pressure() -> None:
    # A collapsing blue air force does not make red surge while red itself is bleeding.
    m = _metrics(
        ground_ratio=SURGE_OPPORTUNITY_GROUND_RATIO,
        blue_air_collapsing=True,
        lost_base=True,
    )
    assert classify_red_intent(m) is RedPosture.CONSOLIDATE


# --- trend derivation in collect_metrics --------------------------------------------


def test_collect_metrics_derives_trends_from_the_lookback_sample() -> None:
    game = _FakeGame(red_intent=True)  # no fronts -> ground_ratio 1.0, last_sitrep None
    prior = _sample(turn=1, resolve=90.0, sam_alive=8, red_bases=5, blue_fighters=20)
    now = _sample(turn=3, resolve=78.0, sam_alive=4, red_bases=4, blue_fighters=10)
    m = collect_metrics(game, now, prior)  # type: ignore[arg-type]
    assert m.iads_trend == 0.5  # (8-4)/8
    assert m.resolve_trend == -12.0  # 78 - 90
    assert m.base_trend == -1  # 4 - 5
    assert m.blue_air_collapsing  # blue fighters halved, red air not suppressed


def test_collect_metrics_has_neutral_trends_without_history() -> None:
    game = _FakeGame(red_intent=True)
    m = collect_metrics(game, _sample(turn=1), None)  # type: ignore[arg-type]
    assert m.iads_trend == 0.0
    assert m.resolve_trend == 0.0
    assert m.base_trend == 0
    assert not m.blue_air_collapsing


def test_blue_air_collapse_ignored_when_reds_own_air_is_suppressed() -> None:
    game = _FakeGame(red_intent=True)
    # Blue lost most of its fighters, but red has far fewer -> red can't exploit it.
    prior = _sample(turn=1, blue_fighters=20, red_fighters=2)
    now = _sample(turn=3, blue_fighters=8, red_fighters=2)
    m = collect_metrics(game, now, prior)  # type: ignore[arg-type]
    assert not m.blue_air_collapsing


# --- the lookback selector -----------------------------------------------------------


def test_trend_lookback_is_none_without_prior_history() -> None:
    assert _trend_lookback([], 1) is None
    assert _trend_lookback([_sample(turn=5)], 5) is None  # current turn excluded


def test_trend_lookback_prefers_about_two_turns_back() -> None:
    history = [_sample(turn=t) for t in (1, 2, 3, 4)]
    # From turn 5, target is turn 3; the newest sample at/before it is turn 3.
    got = _trend_lookback(history, 5)
    assert got is not None and got.turn == 3


def test_trend_lookback_falls_back_to_the_oldest_when_young() -> None:
    history = [_sample(turn=4)]
    # From turn 5, target is turn 3 -- none that old, so the oldest earlier stands in.
    got = _trend_lookback(history, 5)
    assert got is not None and got.turn == 4


# --- rolling history recording -------------------------------------------------------


def test_record_sample_replaces_a_same_turn_entry() -> None:
    game = _FakeGame(red_intent=True)
    _record_sample(game, _sample(turn=2, sam_alive=8))  # type: ignore[arg-type]
    _record_sample(game, _sample(turn=2, sam_alive=3))  # type: ignore[arg-type]
    assert len(game.red_intent_history) == 1
    assert game.red_intent_history[0].sam_alive == 3


def test_record_sample_trims_to_memory_length() -> None:
    game = _FakeGame(red_intent=True)
    for t in range(1, MEMORY_LENGTH + 4):
        _record_sample(game, _sample(turn=t))  # type: ignore[arg-type]
    assert len(game.red_intent_history) == MEMORY_LENGTH
    # The oldest turns are dropped; the most recent are kept.
    assert game.red_intent_history[-1].turn == MEMORY_LENGTH + 3


def test_update_banks_a_sample_each_turn() -> None:
    game = _FakeGame(red_intent=True, fronts=(_FakeFront(red_units=20, blue_units=5),))
    update_red_intent(game)  # type: ignore[arg-type]
    assert len(game.red_intent_history) == 1
    assert game.red_intent_history[0].turn == 1


def test_rolling_memory_consolidates_when_iads_is_dismantled() -> None:
    # End-to-end: a ground-dominant red surges turn 1, then digs in once its SAM belt is
    # visibly dismantled over the following turns -- the memory the design always wanted.
    game = _FakeGame(red_intent=True, fronts=(_FakeFront(red_units=20, blue_units=5),))
    game.turn = 1
    game.theater.ground_objects = [_fake_sam() for _ in range(8)]
    update_red_intent(game)  # type: ignore[arg-type]
    assert game.red_intent_key == RedPosture.SURGE.value
    game.turn = 3
    game.theater.ground_objects = [_fake_sam() for _ in range(4)]  # half the belt gone
    update_red_intent(game)  # type: ignore[arg-type]
    assert game.red_intent_key == RedPosture.CONSOLIDATE.value
    assert "IADS falling" in (game.red_intent_status_line or "")


# --- B: intensity -------------------------------------------------------------------


def test_surge_intensity_ramps_with_the_margin() -> None:
    floor = _intensity(_metrics(ground_ratio=SURGE_GROUND_RATIO), RedPosture.SURGE)
    runaway = _intensity(_metrics(ground_ratio=SURGE_STRONG_RATIO), RedPosture.SURGE)
    assert runaway == 1.0
    assert 0.0 < floor < runaway


def test_consolidate_intensity_deepens_with_pressure() -> None:
    mild = _intensity(
        _metrics(ground_ratio=CONSOLIDATE_GROUND_RATIO - 0.05), RedPosture.CONSOLIDATE
    )
    # A fully collapsed regime (resolve 0) maxes the resolve severity axis.
    deep = _intensity(
        _metrics(ground_ratio=0.0, resolve=0.0, lost_base=True), RedPosture.CONSOLIDATE
    )
    assert deep == 1.0
    assert mild < deep


def test_attrition_intensity_is_the_neutral_midpoint() -> None:
    assert _intensity(_metrics(), RedPosture.ATTRITION) == DEFAULT_INTENSITY


# --- B: the graduated seams read intensity ------------------------------------------


def _intensity_game(posture: str, intensity: float, aggr: int = 50) -> "_FakeGame":
    game = _FakeGame(red_intent=True)
    game.settings = SimpleNamespace(
        red_intent=True, opfor_autoplanner_aggressiveness=aggr, campaign_phases=False
    )
    game.red_intent_key = posture
    game.red_intent_intensity = intensity
    return game


def test_active_red_intensity_defaults_and_reads() -> None:
    off = _FakeGame(red_intent=False)
    off.red_intent_intensity = 0.9
    assert active_red_intensity(off) == DEFAULT_INTENSITY  # type: ignore[arg-type]
    unset = _FakeGame(red_intent=True)
    assert active_red_intensity(unset) == DEFAULT_INTENSITY  # type: ignore[arg-type]
    set_game = _FakeGame(red_intent=True)
    set_game.red_intent_intensity = 0.8
    assert active_red_intensity(set_game) == 0.8  # type: ignore[arg-type]


def test_aggressiveness_scales_with_surge_intensity() -> None:
    weak = _intensity_game(RedPosture.SURGE.value, 0.0)
    strong = _intensity_game(RedPosture.SURGE.value, 1.0)
    mid = _intensity_game(RedPosture.SURGE.value, DEFAULT_INTENSITY)
    assert effective_aggressiveness(mid) == 80  # type: ignore[arg-type]  # v1 anchor
    assert effective_aggressiveness(weak) == 65  # type: ignore[arg-type]  # 50 + 15
    assert effective_aggressiveness(strong) == 95  # type: ignore[arg-type]  # 50 + 45


def test_commit_factor_scales_with_intensity() -> None:
    surge_strong = _intensity_game(RedPosture.SURGE.value, 1.0)
    surge_weak = _intensity_game(RedPosture.SURGE.value, 0.0)
    consolidate_deep = _intensity_game(RedPosture.CONSOLIDATE.value, 1.0)
    assert stance_commit_factor(surge_strong) == 1.55  # type: ignore[arg-type]
    assert stance_commit_factor(surge_weak) == 1.15  # type: ignore[arg-type]
    assert stance_commit_factor(consolidate_deep) == 0.5  # type: ignore[arg-type]


def test_status_line_carries_the_intensity_word() -> None:
    # A runaway surge reads "Surging (all-in)"; the enriched detail still flows.
    game = _FakeGame(red_intent=True, fronts=(_FakeFront(red_units=40, blue_units=5),))
    update_red_intent(game)  # type: ignore[arg-type]
    assert game.red_intent_key == RedPosture.SURGE.value
    assert "Surging (all-in)" in (game.red_intent_status_line or "")


def test_sitrep_posture_detail_surfaces_the_status_line() -> None:
    game = _FakeGame(red_intent=True)
    game.red_intent_key = RedPosture.SURGE.value
    game.red_intent_status_line = "Surging (all-in) — ground 4.0x · IADS falling"
    from game.fourteenth.red_intent import sitrep_posture_detail

    assert sitrep_posture_detail(game) == (  # type: ignore[arg-type]
        "Surging (all-in) — ground 4.0x · IADS falling"
    )
    off = _FakeGame(red_intent=False)
    off.red_intent_status_line = "stale"
    assert sitrep_posture_detail(off) is None  # type: ignore[arg-type]


def test_intensity_word_helper() -> None:
    from game.fourteenth.red_intent import intensity_word

    surge = _FakeGame(red_intent=True)
    surge.red_intent_key = RedPosture.SURGE.value
    surge.red_intent_intensity = 1.0
    assert intensity_word(surge) == "all-in"  # type: ignore[arg-type]
    consolidate = _FakeGame(red_intent=True)
    consolidate.red_intent_key = RedPosture.CONSOLIDATE.value
    consolidate.red_intent_intensity = 1.0
    assert intensity_word(consolidate) == "dug in"  # type: ignore[arg-type]
    # ATTRITION (neutral middle) and feature-off carry no descriptor.
    attrition = _FakeGame(red_intent=True)
    attrition.red_intent_key = RedPosture.ATTRITION.value
    assert intensity_word(attrition) is None  # type: ignore[arg-type]
    off = _FakeGame(red_intent=False)
    off.red_intent_key = RedPosture.SURGE.value
    assert intensity_word(off) is None  # type: ignore[arg-type]
