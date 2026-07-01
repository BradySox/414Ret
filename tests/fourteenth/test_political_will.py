"""Vietnam campaign layer W1: the political-will economy (observe-only).

Locks the feed model: BLUE (Political Will) drains from weighted airframe losses
(heavy bombers cost more), POW captures + a per-turn held trickle, and lost bases,
softened by Combat SAR rescues and claimed enemy air kills; RED (Regime Resolve)
drains mostly from trail-convoy and ground attrition, barely from airframes. Off
switch, clamping, and the SITREP threading are the safety rails.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.fourteenth.political_will import (
    BLUE_AIRFRAME_LOSS,
    BLUE_BASE_LOST,
    BLUE_ENEMY_AIR_CLAIMED,
    BLUE_HEAVY_BOMBER_LOSS,
    BLUE_PASSIVE_REGEN,
    BLUE_PILOT_RESCUED_REFUND,
    BLUE_POW_HELD_PER_TURN,
    BLUE_POW_TAKEN,
    RED_CONVOY_UNIT_LOST,
    RED_PASSIVE_REGEN,
    WILL_MAX,
    update_political_will,
)


def _counts(
    aircraft: int = 0, convoy: int = 0, bases_lost: int = 0, ground: int = 0
) -> Any:
    return SimpleNamespace(
        aircraft=aircraft,
        front_line=ground,
        convoy=convoy,
        cargo_ships=0,
        airlift_cargo=0,
        ground_objects=0,
        scenery=0,
        bases_lost=bases_lost,
    )


class _AircraftType:
    """Hashable fake -- it keys the by_type dict, and SimpleNamespace is unhashable."""

    def __init__(self, dcs_id: str) -> None:
        self.dcs_unit_type = SimpleNamespace(id=dcs_id)


def _aircraft_type(dcs_id: str) -> Any:
    return _AircraftType(dcs_id)


def _debrief(
    *,
    blue_air_by_type: dict[Any, int] | None = None,
    blue_counts: Any = None,
    red_counts: Any = None,
    captures: list[Any] | None = None,
    rescues: list[str] | None = None,
) -> Any:
    from game.theater import Player

    blue = blue_counts or _counts()
    red = red_counts or _counts()

    def loss_counts(player: Any) -> Any:
        return blue if player is Player.BLUE else red

    return SimpleNamespace(
        air_losses=SimpleNamespace(
            by_type=lambda player: (
                dict(blue_air_by_type or {}) if player is Player.BLUE else {}
            )
        ),
        loss_counts=loss_counts,
        state_data=SimpleNamespace(
            combat_sar_captures=captures or [], combat_sar_rescues=rescues or []
        ),
    )


def _game(
    *,
    on: bool = True,
    blue_will: float = 100.0,
    red_will: float = 100.0,
    pows_held: int = 0,
) -> Any:
    return SimpleNamespace(
        settings=SimpleNamespace(vietnam_political_will=on),
        blue=SimpleNamespace(
            political_will=blue_will,
            pending_pow_recoveries=[object()] * pows_held,
        ),
        red=SimpleNamespace(political_will=red_will),
        message=lambda title, text="": None,
    )


def test_off_switch_touches_nothing() -> None:
    game = _game(on=False, blue_will=80.0, red_will=70.0)
    update_political_will(game, _debrief(blue_counts=_counts(aircraft=5)))
    assert game.blue.political_will == 80.0
    assert game.red.political_will == 70.0


def test_quiet_turn_regenerates_both_sides() -> None:
    game = _game(blue_will=50.0, red_will=50.0)
    update_political_will(game, _debrief())
    assert game.blue.political_will == 50.0 + BLUE_PASSIVE_REGEN
    assert game.red.political_will == 50.0 + RED_PASSIVE_REGEN


def test_will_never_exceeds_the_ceiling() -> None:
    game = _game(blue_will=WILL_MAX, red_will=WILL_MAX)
    update_political_will(game, _debrief())
    assert game.blue.political_will == WILL_MAX
    assert game.red.political_will == WILL_MAX


def test_heavy_bomber_costs_more_than_a_tactical_jet() -> None:
    jet_game = _game()
    update_political_will(
        jet_game, _debrief(blue_air_by_type={_aircraft_type("F-4E"): 1})
    )
    buff_game = _game()
    update_political_will(
        buff_game, _debrief(blue_air_by_type={_aircraft_type("B-52H"): 1})
    )
    jet_cost = 100.0 - jet_game.blue.political_will
    buff_cost = 100.0 - buff_game.blue.political_will
    assert buff_cost > jet_cost
    # Exact weights (regen cancels in the subtraction).
    assert jet_cost == BLUE_AIRFRAME_LOSS - BLUE_PASSIVE_REGEN
    assert buff_cost == BLUE_HEAVY_BOMBER_LOSS - BLUE_PASSIVE_REGEN


def test_pows_hit_on_capture_and_drain_while_held() -> None:
    game = _game(pows_held=2)
    update_political_will(game, _debrief(captures=[("unit", 1.0, 2.0, "field")]))
    expected = 100.0 + BLUE_PASSIVE_REGEN - BLUE_POW_TAKEN - 2 * BLUE_POW_HELD_PER_TURN
    assert game.blue.political_will == expected


def test_rescue_refunds_and_claimed_kills_restore() -> None:
    game = _game(blue_will=50.0)
    update_political_will(
        game, _debrief(rescues=["pilot1"], red_counts=_counts(aircraft=4))
    )
    expected = (
        50.0
        + BLUE_PASSIVE_REGEN
        + BLUE_PILOT_RESCUED_REFUND
        + 4 * BLUE_ENEMY_AIR_CLAIMED
    )
    assert game.blue.political_will == expected


def test_lost_base_drains_blue() -> None:
    game = _game()
    update_political_will(game, _debrief(blue_counts=_counts(bases_lost=1)))
    assert game.blue.political_will == 100.0 + BLUE_PASSIVE_REGEN - BLUE_BASE_LOST


def test_red_resolve_bleeds_from_the_trail() -> None:
    # 4 convoy trucks killed (the §35 real convoy) bites Hanoi harder than losing
    # 4 airframes -- resolve is logistics-driven, not casualty-driven.
    convoy_game = _game()
    update_political_will(convoy_game, _debrief(red_counts=_counts(convoy=4)))
    air_game = _game()
    update_political_will(air_game, _debrief(red_counts=_counts(aircraft=4)))
    convoy_cost = 100.0 - convoy_game.red.political_will
    air_cost = 100.0 - air_game.red.political_will
    assert convoy_cost > air_cost
    assert convoy_cost == 4 * RED_CONVOY_UNIT_LOST - RED_PASSIVE_REGEN


def test_will_floors_at_zero() -> None:
    game = _game(blue_will=2.0)
    update_political_will(game, _debrief(blue_air_by_type={_aircraft_type("B-52H"): 3}))
    assert game.blue.political_will == 0.0
