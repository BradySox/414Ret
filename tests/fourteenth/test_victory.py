"""Custom victory conditions (§75): parse, evaluation, verdict, surfacing.

Locks the contracts from docs/dev/design/414th-victory-conditions-notes.md:
AND-within-entry / OR-across-entries semantics (the deliberate divergence from
PhaseCondition's any-field trigger), the no-vacuous-win rules (empty baselines
and absent categories never fire), loss precedence, the knob synthesis, the
announce latch, and that an unconfigured game is a byte-identical no-op all the
way through the real ``Game.check_win_loss`` branch order.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Iterator, Optional, cast

import pytest

from game.fourteenth import victory as victory_mod
from game.fourteenth.victory import (
    VictoryCondition,
    VictoryProfile,
    active_victory_profile,
    condition_met,
    describe_condition,
    ensure_victory_baseline,
    parse_victory,
    victory_overview,
    victory_sitrep_lines,
    victory_verdict,
)
from game.theater.player import Player


@pytest.fixture(autouse=True)
def _clean_profile_cache() -> Iterator[None]:
    victory_mod._PROFILE_CACHE.clear()
    yield
    victory_mod._PROFILE_CACHE.clear()


def _cp(
    name: str,
    owner: Player,
    operational: bool = True,
    armor: int = 0,
) -> Any:
    return SimpleNamespace(
        name=name,
        captured=owner,
        runway_is_operational=lambda: operational,
        base=SimpleNamespace(total_armor=armor),
    )


def _tgo(name: str, category: str, cp: Any, *alive: bool) -> Any:
    return SimpleNamespace(
        name=name,
        category=category,
        control_point=cp,
        units=[SimpleNamespace(alive=a) for a in alive],
    )


def _wing(*owned: int) -> Any:
    squadrons = [SimpleNamespace(owned_aircraft=n) for n in owned]
    return SimpleNamespace(iter_squadrons=lambda: list(squadrons))


def _game(
    cps: Optional[list[Any]] = None,
    tgos: Optional[list[Any]] = None,
    red_air: tuple[int, ...] = (10,),
    blue_air: tuple[int, ...] = (10,),
    turn: int = 5,
    domination: int = 0,
    attrition: int = 0,
    campaign_name: Optional[str] = None,
    will: Optional[tuple[float, float]] = None,
    supply_on: bool = False,
) -> Any:
    wings = {Player.RED: _wing(*red_air), Player.BLUE: _wing(*blue_air)}
    messages: list[tuple[str, str]] = []
    game = SimpleNamespace(
        theater=SimpleNamespace(controlpoints=cps or [], ground_objects=tgos or []),
        air_wing_for=lambda player: wings[player],
        settings=SimpleNamespace(
            alternate_victory_domination=domination,
            alternate_victory_attrition=attrition,
            vietnam_political_will=will is not None,
            war_economy=supply_on,
        ),
        turn=turn,
        campaign_name=campaign_name,
        messages=messages,
        # (blue_will, red_will) when will tracking is on; the coalition stubs
        # always exist so the supply reader can hand them to a patched
        # coalition_supply_health.
        blue=SimpleNamespace(political_will=will[0] if will else None),
        red=SimpleNamespace(political_will=will[1] if will else None),
    )
    game.message = lambda title, text="": messages.append((title, text))
    return game


def _baseline(game: Any) -> Any:
    return ensure_victory_baseline(cast(Any, game))


# --- parsing --------------------------------------------------------------------------


def test_parse_full_block() -> None:
    profile = parse_victory(
        {
            "description": "Liberate Abkhazia",
            "win_when": [
                {"capture_cps": ["Sukhumi", "Gudauta"], "label": "Take the coast"},
                {"enemy_air_below": 0.1, "min_turn": 4},
            ],
            "lose_when": [{"lose_cps": ["Kutaisi"]}],
        }
    )
    assert profile is not None
    assert profile.description == "Liberate Abkhazia"
    assert profile.win_when[0].capture_cps == ("Sukhumi", "Gudauta")
    assert profile.win_when[0].label == "Take the coast"
    assert profile.win_when[1].enemy_air_below == 0.1
    assert profile.win_when[1].min_turn == 4
    assert profile.lose_when[0].lose_cps == ("Kutaisi",)


def test_parse_absent_block_is_none() -> None:
    assert parse_victory(None) is None
    assert parse_victory({}) is None


def test_parse_rejects_bad_shapes() -> None:
    with pytest.raises(ValueError):
        parse_victory("win")
    with pytest.raises(ValueError):
        parse_victory({"win_when": [{"capture_cps": ["A"]}], "extra": True})
    with pytest.raises(ValueError):
        parse_victory({"win_when": [{"capture_the_flag": ["A"]}]})
    with pytest.raises(ValueError):
        # label/min_turn alone do not end a war.
        parse_victory({"win_when": [{"label": "x", "min_turn": 3}]})
    with pytest.raises(ValueError):
        parse_victory({"description": "no conditions at all"})
    with pytest.raises(ValueError):
        parse_victory({"win_when": [{"capture_cps": []}]})
    with pytest.raises(ValueError):
        parse_victory({"win_when": [{"enemy_air_below": 0.0}]})
    with pytest.raises(ValueError):
        parse_victory({"win_when": [{"enemy_air_below": 1.0}]})
    with pytest.raises(ValueError):
        parse_victory({"win_when": [{"territory_below": 1.0}]})
    with pytest.raises(ValueError):
        parse_victory({"win_when": [{"enemy_air_denied": False}]})


def test_parse_territory_above_one_is_legal() -> None:
    profile = parse_victory({"win_when": [{"territory_above": 1.0}]})
    assert profile is not None
    assert profile.win_when[0].territory_above == 1.0


def test_parse_meter_fields() -> None:
    profile = parse_victory(
        {
            "win_when": [{"red_resolve_below": 30, "enemy_supply_below": 25}],
            "lose_when": [{"blue_will_below": 40}, {"friendly_supply_below": 20}],
        }
    )
    assert profile is not None
    assert profile.win_when[0].red_resolve_below == 30
    assert profile.win_when[0].enemy_supply_below == 25
    assert profile.lose_when[0].blue_will_below == 40
    assert profile.lose_when[1].friendly_supply_below == 20
    # Meter thresholds are the meters' own 0-100 scale, exclusive both ends.
    with pytest.raises(ValueError):
        parse_victory({"win_when": [{"red_resolve_below": 0}]})
    with pytest.raises(ValueError):
        parse_victory({"win_when": [{"red_resolve_below": 100}]})
    with pytest.raises(ValueError):
        parse_victory({"lose_when": [{"blue_will_below": 150}]})


# --- evaluation -----------------------------------------------------------------------


def test_capture_cps_requires_all_named_blue() -> None:
    game = _game(cps=[_cp("A", Player.BLUE), _cp("B", Player.RED)])
    baseline = _baseline(game)
    partial = VictoryCondition(capture_cps=("A", "B"))
    assert not condition_met(game, partial, baseline)
    game.theater.controlpoints[1].captured = Player.BLUE
    assert condition_met(game, VictoryCondition(capture_cps=("A", "B")), baseline)
    # A typo'd name can never be met -- visible in the UI, never a silent win.
    assert not condition_met(game, VictoryCondition(capture_cps=("Nope",)), baseline)


def test_lose_cps_fires_on_any_named_red() -> None:
    game = _game(cps=[_cp("A", Player.BLUE), _cp("B", Player.RED)])
    baseline = _baseline(game)
    assert condition_met(game, VictoryCondition(lose_cps=("A", "B")), baseline)
    assert not condition_met(game, VictoryCondition(lose_cps=("A",)), baseline)


def test_territory_thresholds() -> None:
    game = _game(
        cps=[
            _cp("A", Player.BLUE),
            _cp("B", Player.BLUE),
            _cp("C", Player.RED),
            _cp("N", Player.NEUTRAL),
        ]
    )
    baseline = _baseline(game)
    # 2/3 non-neutral bases are blue.
    assert condition_met(game, VictoryCondition(territory_above=0.6), baseline)
    assert not condition_met(game, VictoryCondition(territory_above=0.7), baseline)
    assert condition_met(game, VictoryCondition(territory_below=0.7), baseline)
    assert not condition_met(game, VictoryCondition(territory_below=0.5), baseline)


def test_destroy_targets_needs_every_named_tgo_dead() -> None:
    cp = _cp("A", Player.RED)
    game = _game(
        cps=[cp],
        tgos=[
            _tgo("HQ North", "commandcenter", cp, False, False),
            _tgo("HQ South", "commandcenter", cp, True),
        ],
    )
    baseline = _baseline(game)
    assert condition_met(
        game, VictoryCondition(destroy_targets=("hq north",)), baseline
    )
    both = VictoryCondition(destroy_targets=("HQ North", "HQ South"))
    assert not condition_met(game, both, baseline)
    # A name matching nothing can never be met.
    missing = VictoryCondition(destroy_targets=("HQ West",))
    assert not condition_met(game, missing, baseline)


def test_destroy_categories_baseline_guards_the_vacuous_win() -> None:
    cp = _cp("A", Player.RED)
    game = _game(cps=[cp], tgos=[_tgo("Comms", "comms", cp, True)])
    baseline = _baseline(game)
    cond = VictoryCondition(destroy_categories=("comms",))
    assert not condition_met(game, cond, baseline)
    game.theater.ground_objects[0].units[0].alive = False
    assert condition_met(game, cond, baseline)
    # A category the campaign never fielded can never produce a win.
    absent = VictoryCondition(destroy_categories=("power",))
    assert not condition_met(game, absent, baseline)


def test_destroy_categories_capturing_the_site_counts_as_denial() -> None:
    # The last comms site's base gets CAPTURED intact: red owns no alive comms
    # any more, which is the condition's meaning ("the enemy no longer operates
    # any"), and the baseline proves the class existed.
    cp = _cp("A", Player.RED)
    game = _game(cps=[cp], tgos=[_tgo("Comms", "comms", cp, True)])
    baseline = _baseline(game)
    cp.captured = Player.BLUE
    assert condition_met(
        game, VictoryCondition(destroy_categories=("comms",)), baseline
    )


def test_strength_ratios_measure_against_the_baseline() -> None:
    game = _game(red_air=(10, 10), blue_air=(8,))
    baseline = _baseline(game)
    assert baseline.red_air == 20
    cond = VictoryCondition(enemy_air_below=0.5)
    assert not condition_met(game, cond, baseline)
    # Red loses one whole squadron: 10/20 is not < 0.5 ...
    game.air_wing_for(Player.RED).iter_squadrons()[0].owned_aircraft = 0
    assert not condition_met(game, cond, baseline)
    # ... one more airframe down is.
    game.air_wing_for(Player.RED).iter_squadrons()[1].owned_aircraft = 9
    assert condition_met(game, cond, baseline)


def test_empty_baseline_never_fires_a_ratio_condition() -> None:
    game = _game(red_air=(0,))
    baseline = _baseline(game)
    assert not condition_met(game, VictoryCondition(enemy_air_below=0.9), baseline)
    assert not condition_met(game, VictoryCondition(enemy_ground_below=0.9), baseline)


def test_ground_and_friendly_ratios() -> None:
    game = _game(
        cps=[_cp("A", Player.RED, armor=10), _cp("B", Player.BLUE, armor=4)],
        blue_air=(10,),
    )
    baseline = _baseline(game)
    assert baseline.red_ground == 10
    game.theater.controlpoints[0].base.total_armor = 1
    assert condition_met(game, VictoryCondition(enemy_ground_below=0.2), baseline)
    game.air_wing_for(Player.BLUE).iter_squadrons()[0].owned_aircraft = 2
    assert condition_met(game, VictoryCondition(friendly_air_below=0.3), baseline)


def test_air_denial_counts_operational_red_bases() -> None:
    game = _game(
        cps=[
            _cp("Red field", Player.RED, operational=True),
            _cp("Blue field", Player.BLUE, operational=True),
        ]
    )
    baseline = _baseline(game)
    cond = VictoryCondition(enemy_air_denied=True)
    assert not condition_met(game, cond, baseline)
    # Cratered/captured: the red field stops operating; blue fields never count.
    game.theater.controlpoints[0].runway_is_operational = lambda: False
    assert condition_met(game, cond, baseline)


def test_and_semantics_within_one_entry() -> None:
    game = _game(cps=[_cp("A", Player.BLUE)], red_air=(10,), turn=5)
    baseline = _baseline(game)
    both = VictoryCondition(capture_cps=("A",), enemy_air_below=0.5)
    # The CP is held but the air condition is not met -> the entry is not met.
    assert not condition_met(game, both, baseline)
    game.air_wing_for(Player.RED).iter_squadrons()[0].owned_aircraft = 1
    assert condition_met(game, both, baseline)


def test_min_turn_guards_the_entry() -> None:
    game = _game(cps=[_cp("A", Player.BLUE)], turn=2)
    baseline = _baseline(game)
    cond = VictoryCondition(capture_cps=("A",), min_turn=4)
    assert not condition_met(game, cond, baseline)
    game.turn = 4
    assert condition_met(game, cond, baseline)


# --- the baseline latch ---------------------------------------------------------------


def test_baseline_latches_once() -> None:
    game = _game(red_air=(10,))
    first = _baseline(game)
    game.air_wing_for(Player.RED).iter_squadrons()[0].owned_aircraft = 2
    assert _baseline(game) is first
    assert _baseline(game).red_air == 10


# --- knobs + profile merge ------------------------------------------------------------


def test_no_configuration_means_no_profile() -> None:
    assert active_victory_profile(_game()) is None


def test_domination_knob_synthesizes_a_win_condition() -> None:
    game = _game(cps=[_cp("A", Player.BLUE), _cp("B", Player.RED)], domination=80)
    profile = active_victory_profile(game)
    assert profile is not None
    assert profile.win_when[0].territory_above == 0.8
    assert not profile.lose_when


def test_attrition_knob_synthesizes_a_win_condition() -> None:
    profile = active_victory_profile(_game(attrition=10))
    assert profile is not None
    assert profile.win_when[0].enemy_air_below == 0.1


def test_authored_profile_and_knobs_stack() -> None:
    authored = VictoryProfile(
        description="Test war",
        win_when=(VictoryCondition(capture_cps=("A",)),),
        lose_when=(VictoryCondition(lose_cps=("B",)),),
    )
    victory_mod._PROFILE_CACHE["Test Campaign"] = authored
    game = _game(campaign_name="Test Campaign", attrition=10)
    profile = active_victory_profile(game)
    assert profile is not None
    assert profile.description == "Test war"
    assert len(profile.win_when) == 2
    assert profile.win_when[0].capture_cps == ("A",)
    assert profile.win_when[1].enemy_air_below == 0.1
    assert len(profile.lose_when) == 1


# --- the verdict ----------------------------------------------------------------------


def test_verdict_none_without_configuration() -> None:
    assert victory_verdict(_game(cps=[_cp("A", Player.BLUE)])) is None


def test_verdict_win_announces_once() -> None:
    game = _game(cps=[_cp("A", Player.BLUE), _cp("B", Player.RED)], domination=50)
    assert victory_verdict(game) == "win"
    assert victory_verdict(game) == "win"
    banners = [m for m in game.messages if m[0] == "Victory condition met"]
    assert len(banners) == 1
    assert "50%" in banners[0][1]


def test_loss_takes_precedence_over_a_simultaneous_win() -> None:
    authored = VictoryProfile(
        win_when=(VictoryCondition(capture_cps=("A",)),),
        lose_when=(VictoryCondition(lose_cps=("B",)),),
    )
    victory_mod._PROFILE_CACHE["Test Campaign"] = authored
    game = _game(
        cps=[_cp("A", Player.BLUE), _cp("B", Player.RED)],
        campaign_name="Test Campaign",
    )
    assert victory_verdict(game) == "loss"
    assert game.messages[0][0] == "Defeat condition met"


def test_verdict_uses_the_label_in_the_banner() -> None:
    authored = VictoryProfile(
        win_when=(VictoryCondition(label="Take the coast", capture_cps=("A",)),),
    )
    victory_mod._PROFILE_CACHE["Test Campaign"] = authored
    game = _game(cps=[_cp("A", Player.BLUE)], campaign_name="Test Campaign")
    assert victory_verdict(game) == "win"
    assert game.messages[0] == ("Victory condition met", "Take the coast")


# --- the real check_win_loss branch order ---------------------------------------------


def test_check_win_loss_wiring() -> None:
    # Drive the REAL Game.check_win_loss with a duck-typed self: the negotiation
    # branch (off) is consulted first, the §75 branch wins on the domination
    # knob, and with nothing configured the stock territory checks still rule.
    from game.game import Game, TurnState

    cps = [_cp("A", Player.BLUE), _cp("B", Player.RED)]
    game = _game(cps=cps, domination=50)
    game.blank_canvas_setup = False
    game.settings.vietnam_political_will = False
    game.theater.player_points = lambda state_check=False: [cps[0]]
    game.theater.enemy_points = lambda state_check=False: [cps[1]]
    assert Game.check_win_loss(cast(Any, game)) is TurnState.WIN

    quiet = _game(cps=cps)
    quiet.blank_canvas_setup = False
    quiet.settings.vietnam_political_will = False
    quiet.theater.player_points = lambda state_check=False: [cps[0]]
    quiet.theater.enemy_points = lambda state_check=False: [cps[1]]
    assert Game.check_win_loss(cast(Any, quiet)) is TurnState.CONTINUE


# --- surfacing ------------------------------------------------------------------------


def test_overview_rows_and_live_prose() -> None:
    authored = VictoryProfile(
        description="Test war",
        win_when=(VictoryCondition(enemy_air_below=0.1),),
        lose_when=(VictoryCondition(lose_cps=("B",)),),
    )
    victory_mod._PROFILE_CACHE["Test Campaign"] = authored
    game = _game(
        cps=[_cp("B", Player.BLUE)], red_air=(10,), campaign_name="Test Campaign"
    )
    rows = victory_overview(game)
    assert len(rows) == 2
    assert rows[0]["defeat"] is False
    assert rows[0]["met"] is False
    assert "Enemy air force below 10% of start (now 100%)" in str(rows[0]["text"])
    assert rows[1]["defeat"] is True
    assert "B falls to the enemy (0/1 fallen)" in str(rows[1]["text"])


def test_overview_empty_without_configuration() -> None:
    assert victory_overview(_game()) == []
    assert victory_sitrep_lines(_game()) == []


def test_describe_without_live_values() -> None:
    game = _game(cps=[_cp("A", Player.BLUE)])
    baseline = _baseline(game)
    text = describe_condition(
        game, VictoryCondition(capture_cps=("A",)), baseline, live=False
    )
    assert text == "Capture A"


# --- the absorbed negotiation ending + the meter vocabulary ---------------------------


def test_negotiation_ending_flows_through_victory_verdict() -> None:
    # Will exhaustion IS a victory verdict now -- and carries no announce of its
    # own (update_political_will fires the era banner on the crossing edge).
    assert victory_verdict(_game(will=(0.0, 50.0))) == "loss"
    assert victory_verdict(_game(will=(50.0, 0.0))) == "win"
    # BLUE-loss precedence on a simultaneous collapse (the W2 rule).
    assert victory_verdict(_game(will=(0.0, 0.0))) == "loss"
    game = _game(will=(0.0, 50.0))
    assert victory_verdict(game) == "loss"
    assert game.messages == []
    # Meters healthy, nothing else configured: the war goes on.
    assert victory_verdict(_game(will=(60.0, 60.0))) is None


def test_negotiation_outranks_authored_and_knob_conditions() -> None:
    # An authored/knob win being met never beats a will collapse -- the same
    # precedence the ending had as its own check_win_loss branch.
    game = _game(
        cps=[_cp("A", Player.BLUE), _cp("B", Player.RED)],
        domination=50,
        will=(0.0, 50.0),
    )
    assert victory_verdict(game) == "loss"


def test_check_win_loss_negotiation_precedence() -> None:
    from game.game import Game, TurnState

    cps = [_cp("A", Player.BLUE), _cp("B", Player.RED)]
    game = _game(cps=cps, domination=50, will=(0.0, 50.0))
    game.blank_canvas_setup = False
    game.theater.player_points = lambda state_check=False: [cps[0]]
    game.theater.enemy_points = lambda state_check=False: [cps[1]]
    assert Game.check_win_loss(cast(Any, game)) is TurnState.LOSS


def test_will_ending_rows_lead_the_overview() -> None:
    # A will campaign's VICTORY checklist opens with its real endings, labeled
    # by the will profile (Vietnam defaults here), zero authoring required.
    rows = victory_overview(_game(will=(62.0, 87.0)))
    assert len(rows) == 2
    assert rows[0]["text"] == "Break Hanoi's resolve (now 87 of 100)"
    assert rows[0]["defeat"] is False
    assert rows[0]["met"] is False
    assert rows[1]["text"] == "Washington's patience runs out (now 62 of 100)"
    assert rows[1]["defeat"] is True
    # Will tracking off: no rows, the block stays hidden.
    assert victory_overview(_game()) == []


def test_authored_will_threshold_fields() -> None:
    game = _game(will=(60.0, 25.0))
    baseline = _baseline(game)
    assert condition_met(game, VictoryCondition(red_resolve_below=30), baseline)
    assert not condition_met(game, VictoryCondition(red_resolve_below=20), baseline)
    assert not condition_met(game, VictoryCondition(blue_will_below=50), baseline)
    # Will tracking off: the field can never fire, and the prose says why.
    off = _game()
    off_baseline = _baseline(off)
    assert not condition_met(off, VictoryCondition(red_resolve_below=99), off_baseline)
    text = describe_condition(
        off, VictoryCondition(red_resolve_below=30), off_baseline, live=True
    )
    assert text == "Hanoi's resolve falls below 30 (will tracking off)"


def test_supply_conditions_gated_on_the_war_economy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import game.fourteenth.war_economy as war_economy_mod

    monkeypatch.setattr(
        war_economy_mod, "coalition_supply_health", lambda game, coalition: 0.3
    )
    game = _game(supply_on=True)
    baseline = _baseline(game)
    assert condition_met(game, VictoryCondition(enemy_supply_below=40), baseline)
    assert not condition_met(game, VictoryCondition(enemy_supply_below=25), baseline)
    assert condition_met(game, VictoryCondition(friendly_supply_below=40), baseline)
    text = describe_condition(
        game, VictoryCondition(enemy_supply_below=40), baseline, live=True
    )
    assert text == "Enemy front supply falls below 40% (now 30%)"
    # Economy off: never fires, and the prose says why.
    off = _game()
    off_baseline = _baseline(off)
    assert not condition_met(off, VictoryCondition(enemy_supply_below=99), off_baseline)
    assert (
        describe_condition(
            off, VictoryCondition(enemy_supply_below=40), off_baseline, live=True
        )
        == "Enemy front supply falls below 40% (war economy off)"
    )


def test_sitrep_lines_are_prefixed_and_capped() -> None:
    authored = VictoryProfile(
        win_when=(
            VictoryCondition(capture_cps=("A",)),
            VictoryCondition(enemy_air_below=0.1),
            VictoryCondition(enemy_ground_below=0.1),
            VictoryCondition(enemy_air_denied=True),
        ),
        lose_when=(VictoryCondition(lose_cps=("B",)),),
    )
    victory_mod._PROFILE_CACHE["Test Campaign"] = authored
    game = _game(
        cps=[_cp("A", Player.BLUE), _cp("B", Player.RED)],
        campaign_name="Test Campaign",
    )
    lines = victory_sitrep_lines(game)
    assert len(lines) == 5
    assert lines[0].startswith("Victory: ")
    assert lines[-1] == "(+1 more conditions)"
