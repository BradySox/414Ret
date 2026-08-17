from typing import Any, cast

from game.sim.missionresultsprocessor import (
    ASSAULT_COST_FRACTION,
    DEFEAT_INFLUENCE,
    OFFENSIVE_STANCES,
    MissionResultsProcessor,
)
from game.ground_forces.combat_stance import CombatStance
from game.theater.base import Base


class FakeControlPoint:
    def __init__(self, name: str) -> None:
        self.name = name
        self.base = Base()

    def __repr__(self) -> str:
        return self.name


class FakeSettings:
    def __init__(self, enabled: bool) -> None:
        self.assault_costs_the_attacker = enabled


class FakeGame:
    def __init__(self, enabled: bool) -> None:
        self.settings = FakeSettings(enabled)


def _processor(enabled: bool = True) -> MissionResultsProcessor:
    return MissionResultsProcessor(cast(Any, FakeGame(enabled)))


def _pair() -> tuple[Any, Any]:
    return cast(Any, FakeControlPoint("winner")), cast(Any, FakeControlPoint("loser"))


def test_attacking_winner_banks_less_than_the_loser_gives_up() -> None:
    winner, loser = _pair()
    winner.base.strength = 0.5
    loser.base.strength = 0.5

    _processor().apply_battle_result(
        winner=winner, loser=loser, delta=DEFEAT_INFLUENCE, winner_attacked=True
    )

    expected_gain = DEFEAT_INFLUENCE * (1.0 - ASSAULT_COST_FRACTION)
    assert winner.base.strength == 0.5 + expected_gain
    assert loser.base.strength == 0.5 - DEFEAT_INFLUENCE
    # The assault is paid for: less ground banked than the enemy surrendered.
    assert expected_gain < DEFEAT_INFLUENCE


def test_defending_winner_banks_the_full_delta() -> None:
    """Holding is cheaper than taking -- the whole point of rung B."""
    winner, loser = _pair()
    winner.base.strength = 0.5
    loser.base.strength = 0.5

    _processor().apply_battle_result(
        winner=winner, loser=loser, delta=DEFEAT_INFLUENCE, winner_attacked=False
    )

    assert winner.base.strength == 0.5 + DEFEAT_INFLUENCE
    assert loser.base.strength == 0.5 - DEFEAT_INFLUENCE


def test_holding_beats_taking_for_the_same_win() -> None:
    attacker, its_loser = _pair()
    defender, other_loser = _pair()
    for cp in (attacker, its_loser, defender, other_loser):
        cp.base.strength = 0.5

    processor = _processor()
    processor.apply_battle_result(
        winner=attacker, loser=its_loser, delta=DEFEAT_INFLUENCE, winner_attacked=True
    )
    processor.apply_battle_result(
        winner=defender,
        loser=other_loser,
        delta=DEFEAT_INFLUENCE,
        winner_attacked=False,
    )

    assert defender.base.strength > attacker.base.strength
    # The loser pays the same either way.
    assert its_loser.base.strength == other_loser.base.strength


def test_setting_off_restores_the_straight_swap() -> None:
    winner, loser = _pair()
    winner.base.strength = 0.5
    loser.base.strength = 0.5

    _processor(enabled=False).apply_battle_result(
        winner=winner, loser=loser, delta=DEFEAT_INFLUENCE, winner_attacked=True
    )

    assert winner.base.strength == 0.5 + DEFEAT_INFLUENCE
    assert loser.base.strength == 0.5 - DEFEAT_INFLUENCE


def test_strength_stays_inside_its_bounds() -> None:
    """affect_strength clamps; a discounted gain must not escape that."""
    winner, loser = _pair()
    winner.base.strength = 1.0
    loser.base.strength = 0.05

    _processor().apply_battle_result(
        winner=winner, loser=loser, delta=DEFEAT_INFLUENCE, winner_attacked=True
    )

    assert winner.base.strength == 1.0
    assert loser.base.strength == 0.0


def test_offensive_stances_are_the_pushing_ones() -> None:
    assert CombatStance.AGGRESSIVE in OFFENSIVE_STANCES
    assert CombatStance.ELIMINATION in OFFENSIVE_STANCES
    assert CombatStance.BREAKTHROUGH in OFFENSIVE_STANCES
    # A dug-in or withdrawing side is never charged the assault cost.
    assert CombatStance.DEFENSIVE not in OFFENSIVE_STANCES
    assert CombatStance.AMBUSH not in OFFENSIVE_STANCES
    assert CombatStance.RETREAT not in OFFENSIVE_STANCES


def test_assault_cost_only_ever_reduces_the_winners_gain() -> None:
    assert 0.0 < ASSAULT_COST_FRACTION < 1.0
