"""Vietnam campaign layer W1: the political-will economy (observe-only).

Locks the feed model: BLUE (Political Will) drains from weighted airframe losses
(heavy bombers cost more), POW captures + a per-turn held trickle, warships sunk,
and lost bases, softened by Combat SAR rescues and claimed enemy air kills; RED
(Regime Resolve) drains mostly from trail-convoy and ground attrition, barely from
airframes. Off switch, clamping, and the SITREP threading are the safety rails.

The generalization layer (will profiles): the Vietnam framing and weights are only
the *defaults* -- a campaign's ``will:`` YAML block re-labels and re-weights the
economy. The default-equivalence tests here are the guarantee that the 4 Vietnam
campaigns (no ``will:`` block) are byte-identical to the pre-profile behavior.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from game.fourteenth.political_will import (
    BLUE_AIRFRAME_LOSS,
    BLUE_BASE_LOST,
    BLUE_ENEMY_AIR_CLAIMED,
    BLUE_HEAVY_BOMBER_LOSS,
    BLUE_PASSIVE_REGEN,
    BLUE_PILOT_RESCUED_REFUND,
    BLUE_POW_HELD_PER_TURN,
    BLUE_POW_TAKEN,
    BLUE_ROE_VIOLATION,
    BLUE_SHIP_LOST,
    RED_AIRFRAME_LOSS,
    RED_BASE_LOST,
    RED_CONVOY_UNIT_LOST,
    RED_GROUND_UNIT_LOST,
    RED_PASSIVE_REGEN,
    RED_SHIP_LOST,
    WILL_MAX,
    DEFAULT_WILL_PROFILE,
    WillProfile,
    WillSideCopy,
    WillWeights,
    _PROFILE_CACHE,
    negotiation_verdict,
    parse_will_profile,
    update_political_will,
    will_profile_for,
)


def _counts(
    aircraft: int = 0,
    convoy: int = 0,
    bases_lost: int = 0,
    ground: int = 0,
    ground_objects: int = 0,
) -> Any:
    return SimpleNamespace(
        aircraft=aircraft,
        front_line=ground,
        convoy=convoy,
        cargo_ships=0,
        airlift_cargo=0,
        ground_objects=ground_objects,
        scenery=0,
        bases_lost=bases_lost,
    )


class _AircraftType:
    """Hashable fake -- it keys the by_type dict, and SimpleNamespace is unhashable."""

    def __init__(self, dcs_id: str) -> None:
        self.dcs_unit_type = SimpleNamespace(id=dcs_id)


def _aircraft_type(dcs_id: str) -> Any:
    return _AircraftType(dcs_id)


def _tgo_loss(is_ship: bool = False) -> Any:
    return SimpleNamespace(theater_unit=SimpleNamespace(is_ship=is_ship))


def _debrief(
    *,
    blue_air_by_type: dict[Any, int] | None = None,
    blue_counts: Any = None,
    red_counts: Any = None,
    captures: list[Any] | None = None,
    rescues: list[str] | None = None,
    blue_ships: int = 0,
    red_ships: int = 0,
) -> Any:
    from game.theater import Player

    blue = blue_counts or _counts()
    red = red_counts or _counts()

    def loss_counts(player: Any) -> Any:
        return blue if player is Player.BLUE else red

    debrief = SimpleNamespace(
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
    if blue_ships or red_ships:
        # Ship losses ride the ground-object loss lists (TheaterUnit.is_ship);
        # most tests omit ground_losses entirely, matching the getattr guard.
        debrief.ground_losses = SimpleNamespace(
            player_ground_objects=[_tgo_loss(is_ship=True)] * blue_ships,
            enemy_ground_objects=[_tgo_loss(is_ship=True)] * red_ships,
        )
    return debrief


def _game(
    *,
    on: bool = True,
    blue_will: float = 100.0,
    red_will: float = 100.0,
    pows_held: int = 0,
) -> Any:
    messages: list[str] = []
    game = SimpleNamespace(
        settings=SimpleNamespace(vietnam_political_will=on),
        blue=SimpleNamespace(
            political_will=blue_will,
            pending_pow_recoveries=[object()] * pows_held,
        ),
        red=SimpleNamespace(political_will=red_will),
        messages=messages,
    )
    game.message = lambda title, text="": messages.append(title)
    return game


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


# ---- W2: the negotiation ending ------------------------------------------------------


def test_verdict_none_when_setting_off() -> None:
    # Even at zero will, non-Vietnam campaigns never touch the negotiation branch.
    assert negotiation_verdict(_game(on=False, blue_will=0.0, red_will=0.0)) is None


def test_verdict_none_while_both_sides_hold() -> None:
    assert negotiation_verdict(_game(blue_will=1.0, red_will=1.0)) is None


def test_blue_exhaustion_is_a_loss() -> None:
    # Washington orders withdrawal -- even with the front intact.
    assert negotiation_verdict(_game(blue_will=0.0, red_will=55.0)) == "loss"


def test_red_exhaustion_is_a_win() -> None:
    # Hanoi agrees to terms -- no base capture required.
    assert negotiation_verdict(_game(blue_will=40.0, red_will=0.0)) == "win"


def test_simultaneous_collapse_is_a_loss() -> None:
    # BLUE-loss precedence: your patience broke first; never a cheap win.
    assert negotiation_verdict(_game(blue_will=0.0, red_will=0.0)) == "loss"


def test_exhaustion_banner_fires_on_the_crossing_edge_only() -> None:
    # Driving BLUE to zero raises the withdrawal banner once...
    game = _game(blue_will=1.0)
    update_political_will(game, _debrief(blue_air_by_type={_aircraft_type("B-52H"): 1}))
    assert game.blue.political_will == 0.0
    assert "Washington orders withdrawal" in game.messages
    # ...and a side already sitting at zero does not repeat it every turn.
    withdrawals = game.messages.count("Washington orders withdrawal")
    update_political_will(game, _debrief(blue_air_by_type={_aircraft_type("B-52H"): 1}))
    assert game.messages.count("Washington orders withdrawal") == withdrawals


def test_red_exhaustion_banner_is_era_framed() -> None:
    game = _game(red_will=1.0)
    update_political_will(game, _debrief(red_counts=_counts(convoy=4)))
    assert game.red.political_will == 0.0
    assert "Hanoi agrees to terms" in game.messages


# ---- the attribution ledger ----------------------------------------------------------


def test_ledger_records_labeled_moves_per_turn() -> None:
    from game.fourteenth.political_will import ledger_notes, update_political_will

    game = _game(pows_held=2)
    game.turn = 5
    update_political_will(
        game,
        _debrief(
            blue_air_by_type={_aircraft_type("B-52H"): 1, _aircraft_type("F-4E"): 2},
            red_counts=_counts(convoy=3),
        ),
    )
    entry = game.will_ledger[-1]
    assert entry.turn == 5
    blue = dict(entry.blue_moves)
    assert blue["heavy bombers x1 down"] == -BLUE_HEAVY_BOMBER_LOSS
    assert blue["airframes x2 lost"] == -2 * BLUE_AIRFRAME_LOSS
    assert blue["POWs held x2"] == -2 * BLUE_POW_HELD_PER_TURN
    assert blue["passive regen"] == BLUE_PASSIVE_REGEN
    red = dict(entry.red_moves)
    assert red["trail convoys x3"] == -3 * RED_CONVOY_UNIT_LOST
    # The deltas are the component sums, matching the meter movement exactly.
    assert entry.blue_delta == sum(blue.values())
    assert 100.0 - game.blue.political_will == -entry.blue_delta
    # And the rendered notes lead with the delta.
    blue_note, red_note = ledger_notes(game)
    assert blue_note is not None and blue_note.startswith(f"{entry.blue_delta:+.1f}:")
    assert red_note is not None and "trail convoys x3" in red_note


def test_ledger_caps_its_length() -> None:
    from game.fourteenth.political_will import WILL_LEDGER_CAP, update_political_will

    game = _game()
    for turn in range(WILL_LEDGER_CAP + 10):
        game.turn = turn
        update_political_will(game, _debrief())
    assert len(game.will_ledger) == WILL_LEDGER_CAP
    assert game.will_ledger[-1].turn == WILL_LEDGER_CAP + 9


def test_ledger_untouched_when_off() -> None:
    from game.fourteenth.political_will import latest_ledger_entry, ledger_notes

    game = _game(on=False)
    update_political_will(game, _debrief(blue_counts=_counts(aircraft=2)))
    assert latest_ledger_entry(game) is None
    assert ledger_notes(game) == (None, None)


def test_format_moves_ranks_by_magnitude() -> None:
    from game.fourteenth.political_will import format_moves

    line = format_moves(
        (
            ("passive regen", 0.5),
            ("heavy bombers x1 down", -6.0),
            ("POWs held x1", -0.5),
        ),
        limit=2,
    )
    assert line.startswith("heavy bombers x1 down -6.0")
    assert "POWs held" not in line  # ties broken by order, limit respected


def test_game_stats_records_will_per_turn() -> None:
    # The will trend rides the existing game_stats per-turn series (the Stats
    # window / client sparkline source), not a bespoke history list.
    from game.models.game_stats import GameStats

    game = _game(blue_will=90.0, red_will=95.0)
    game.turn = 0
    game.theater = SimpleNamespace(controlpoints=[])
    stats = GameStats()
    stats.update(game)
    assert len(stats.data_per_turn) == 1
    assert stats.data_per_turn[0].allied_units.political_will == 90.0
    assert stats.data_per_turn[0].enemy_units.political_will == 95.0


def test_game_stats_will_none_when_feature_off() -> None:
    from game.models.game_stats import GameStats

    game = _game(on=False)
    game.turn = 0
    game.theater = SimpleNamespace(controlpoints=[])
    stats = GameStats()
    stats.update(game)
    assert stats.data_per_turn[0].allied_units.political_will is None
    assert stats.data_per_turn[0].enemy_units.political_will is None


# ---- will profiles: labels + tunable weights + the ship feed ---------------------------


def test_default_profile_is_the_vietnam_framing() -> None:
    # The default-equivalence guarantee: no `will:` block means the exact
    # pre-profile constants and copy, so the 4 Vietnam campaigns are unchanged.
    profile = DEFAULT_WILL_PROFILE
    assert profile.blue.label == "Washington's patience"
    assert profile.blue.exhaustion_title == "Washington orders withdrawal"
    assert profile.red.label == "Hanoi's resolve"
    assert profile.red.exhaustion_title == "Hanoi agrees to terms"
    weights = profile.weights
    assert weights.blue_airframe_loss == BLUE_AIRFRAME_LOSS
    assert weights.blue_heavy_bomber_loss == BLUE_HEAVY_BOMBER_LOSS
    assert weights.blue_pow_taken == BLUE_POW_TAKEN
    assert weights.blue_pow_held_per_turn == BLUE_POW_HELD_PER_TURN
    assert weights.blue_pilot_rescued_refund == BLUE_PILOT_RESCUED_REFUND
    assert weights.blue_base_lost == BLUE_BASE_LOST
    assert weights.blue_enemy_air_claimed == BLUE_ENEMY_AIR_CLAIMED
    assert weights.blue_passive_regen == BLUE_PASSIVE_REGEN
    assert weights.blue_roe_violation == BLUE_ROE_VIOLATION
    assert weights.blue_ship_lost == BLUE_SHIP_LOST
    assert weights.red_convoy_unit_lost == RED_CONVOY_UNIT_LOST
    assert weights.red_ground_unit_lost == RED_GROUND_UNIT_LOST
    assert weights.red_airframe_loss == RED_AIRFRAME_LOSS
    assert weights.red_base_lost == RED_BASE_LOST
    assert weights.red_passive_regen == RED_PASSIVE_REGEN
    assert weights.red_ship_lost == RED_SHIP_LOST


def test_parse_none_and_empty_keep_the_defaults() -> None:
    assert parse_will_profile(None) is DEFAULT_WILL_PROFILE
    assert parse_will_profile({}) == DEFAULT_WILL_PROFILE


def test_parse_authored_labels_and_weights() -> None:
    profile = parse_will_profile(
        {
            "blue": {
                "label": "Downing Street's patience",
                "exhaustion_title": "London recalls the task force",
            },
            "red": {"label": "the Junta's resolve"},
            "weights": {"blue_ship_lost": 8, "red_ship_lost": 6.5},
        }
    )
    assert profile.blue.label == "Downing Street's patience"
    assert profile.blue.exhaustion_title == "London recalls the task force"
    # Anything not authored keeps its default -- copy and weights alike.
    assert profile.blue.exhaustion_body == DEFAULT_WILL_PROFILE.blue.exhaustion_body
    assert profile.red.label == "the Junta's resolve"
    assert profile.red.exhaustion_title == "Hanoi agrees to terms"
    assert profile.weights.blue_ship_lost == 8.0
    assert profile.weights.red_ship_lost == 6.5
    assert profile.weights.blue_airframe_loss == BLUE_AIRFRAME_LOSS


def test_parse_rejects_unknown_weight_keys() -> None:
    # A typo must be a loud parse error (degraded by will_profile_for), never a
    # silently no-op'd rebalance.
    with pytest.raises(ValueError, match="unknown keys"):
        parse_will_profile({"weights": {"blue_shp_lost": 8}})
    with pytest.raises(ValueError, match="must be a mapping"):
        parse_will_profile({"weights": [1, 2]})
    with pytest.raises(ValueError, match="must be a mapping"):
        parse_will_profile("nope")


def test_profile_lookup_reads_campaign_yaml(tmp_path: Any, monkeypatch: Any) -> None:
    from game.campaignloader.campaign import Campaign

    campaign = tmp_path / "falklands.yaml"
    campaign.write_text(
        "name: Test Falklands\n"
        "will:\n"
        "  blue:\n"
        "    label: London's patience\n"
        "  weights:\n"
        "    blue_ship_lost: 8\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        Campaign, "iter_campaign_defs", classmethod(lambda cls: iter([campaign]))
    )
    _PROFILE_CACHE.pop("Test Falklands", None)
    try:
        game = _game()
        game.campaign_name = "Test Falklands"
        profile = will_profile_for(game)
        assert profile.blue.label == "London's patience"
        assert profile.weights.blue_ship_lost == 8.0
    finally:
        _PROFILE_CACHE.pop("Test Falklands", None)


def test_profile_lookup_degrades_on_a_bad_block(
    tmp_path: Any, monkeypatch: Any
) -> None:
    from game.campaignloader.campaign import Campaign

    campaign = tmp_path / "broken.yaml"
    campaign.write_text(
        "name: Test Broken\nwill:\n  weights:\n    not_a_weight: 3\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        Campaign, "iter_campaign_defs", classmethod(lambda cls: iter([campaign]))
    )
    _PROFILE_CACHE.pop("Test Broken", None)
    try:
        game = _game()
        game.campaign_name = "Test Broken"
        assert will_profile_for(game) == DEFAULT_WILL_PROFILE
    finally:
        _PROFILE_CACHE.pop("Test Broken", None)


def test_no_campaign_name_means_the_defaults() -> None:
    assert will_profile_for(_game()) is DEFAULT_WILL_PROFILE


def test_blue_ship_loss_drains_will() -> None:
    game = _game()
    update_political_will(game, _debrief(blue_ships=2))
    expected = 100.0 + BLUE_PASSIVE_REGEN - 2 * BLUE_SHIP_LOST
    assert game.blue.political_will == expected
    assert dict(game.will_ledger[-1].blue_moves)["warships x2 sunk"] == (
        -2 * BLUE_SHIP_LOST
    )


def test_red_ships_leave_the_ground_attrition_pool() -> None:
    # 3 ground-object units died, 2 of them warships: attrition counts 1, the
    # ships drain at their own weight -- never double-counted.
    game = _game()
    update_political_will(
        game, _debrief(red_counts=_counts(ground_objects=3), red_ships=2)
    )
    red = dict(game.will_ledger[-1].red_moves)
    assert red["ground attrition x1"] == -RED_GROUND_UNIT_LOST
    assert red["warships x2 sunk"] == -2 * RED_SHIP_LOST


def test_authored_profile_drives_weights_and_banners() -> None:
    profile = WillProfile(
        blue=WillSideCopy(
            label="London's patience",
            exhaustion_title="London recalls the task force",
            exhaustion_body="The war cabinet has folded.",
        ),
        red=WillSideCopy(
            label="the Junta's resolve",
            exhaustion_title="The Junta capitulates",
            exhaustion_body="Buenos Aires sues for peace.",
        ),
        weights=WillWeights(blue_ship_lost=200.0),
    )
    _PROFILE_CACHE["Test Falklands Live"] = profile
    try:
        game = _game()
        game.campaign_name = "Test Falklands Live"
        update_political_will(game, _debrief(blue_ships=1))
        # The authored ship weight drove BLUE straight to the floor...
        assert game.blue.political_will == 0.0
        # ...and the banner + per-turn message carry the authored framing.
        assert "London recalls the task force" in game.messages
        assert "Washington orders withdrawal" not in game.messages
    finally:
        del _PROFILE_CACHE["Test Falklands Live"]
