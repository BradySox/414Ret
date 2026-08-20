"""§93 region priorities — the factor gates, the ordering effect, the drops.

Fakes are duck-typed per the local convention; narrow ignores where the real
signatures expect engine types.
"""

from __future__ import annotations

from types import SimpleNamespace

from game.commander.objectivefinder import ObjectiveFinder
from game.commander.tasks.compound.attackbattlepositions import AttackBattlePositions
from game.commander.tasks.compound.attackships import AttackShips
from game.commander.tasks.compound.degradeiads import DegradeIads
from game.data.groups import GroupTask
from game.fourteenth.region_priorities import (
    RegionPriority,
    auto_planning_skips,
    planning_factor,
    priority_of,
)
from game.theater import Airfield, Player


def _fake_cp(priority: RegionPriority | None = None) -> Airfield:
    cp = object.__new__(Airfield)
    if priority is not None:
        cp.blue_region_priority = priority
    return cp


def _target(owner: Airfield | None, distance: float = 10_000.0) -> SimpleNamespace:
    return SimpleNamespace(control_point=owner, distance_to=lambda _cp, d=distance: d)


def _settings(on: bool) -> SimpleNamespace:
    # The unpredictability pair keeps shuffled_by_priority a no-op, so the task
    # tests assert on order deterministically.
    return SimpleNamespace(
        region_priorities=on,
        ownfor_planner_unpredictability=0,
        opfor_planner_unpredictability=0,
        c2_decapitation_effects=False,
    )


def test_pre_93_save_reads_normal() -> None:
    # getattr-guarded: a CP pickled before the field existed defaults NORMAL.
    assert priority_of(_fake_cp()) is RegionPriority.NORMAL


def test_property_round_trip() -> None:
    cp = _fake_cp()
    cp.blue_region_priority = RegionPriority.EMPHASIZED
    assert cp.blue_region_priority is RegionPriority.EMPHASIZED
    assert priority_of(cp) is RegionPriority.EMPHASIZED


def test_factor_identity_when_off_red_or_cpless() -> None:
    tgt = _target(_fake_cp(RegionPriority.EMPHASIZED))
    assert planning_factor(tgt, _settings(False), True) == 1.0  # type: ignore[arg-type]
    assert planning_factor(tgt, _settings(True), False) == 1.0  # type: ignore[arg-type]
    orphan = SimpleNamespace(control_point=None)
    assert planning_factor(orphan, _settings(True), True) == 1.0  # type: ignore[arg-type]


def test_factor_levels_and_ignored_drop() -> None:
    s = _settings(True)
    assert planning_factor(_target(_fake_cp(RegionPriority.EMPHASIZED)), s, True) == 0.5  # type: ignore[arg-type]
    assert planning_factor(_target(_fake_cp()), s, True) == 1.0  # type: ignore[arg-type]
    assert (
        planning_factor(_target(_fake_cp(RegionPriority.DEPRIORITIZED)), s, True) == 2.0  # type: ignore[arg-type]
    )
    assert planning_factor(_target(_fake_cp(RegionPriority.IGNORED)), s, True) is None  # type: ignore[arg-type]


def test_cp_target_weighted_as_itself() -> None:
    cp = _fake_cp(RegionPriority.IGNORED)
    assert planning_factor(cp, _settings(True), True) is None  # type: ignore[arg-type]


def _finder(on: bool, player: Player = Player.BLUE) -> ObjectiveFinder:
    game = SimpleNamespace(settings=_settings(on))
    finder = ObjectiveFinder(game, player)  # type: ignore[arg-type]
    home = SimpleNamespace(position=None)
    finder.friendly_control_points = (  # type: ignore[method-assign]
        lambda: iter([home])  # type: ignore[list-item]
    )
    return finder


def test_targets_by_range_weighted_reorders_and_drops() -> None:
    finder = _finder(on=True)
    near_deprio = _target(_fake_cp(RegionPriority.DEPRIORITIZED), distance=100.0)
    far_emph = _target(_fake_cp(RegionPriority.EMPHASIZED), distance=150.0)
    ignored = _target(_fake_cp(RegionPriority.IGNORED), distance=1.0)
    out = list(
        finder._targets_by_range(  # type: ignore[type-var]
            [near_deprio, far_emph, ignored], weighted=True
        )
    )
    # 150*0.5 = 75 beats 100*2.0 = 200; the IGNORED target is gone entirely.
    assert out == [far_emph, near_deprio]


def test_targets_by_range_unweighted_is_untouched() -> None:
    # The rescue/ground-war path: same inputs, plain range order, nothing drops.
    finder = _finder(on=True)
    near_deprio = _target(_fake_cp(RegionPriority.DEPRIORITIZED), distance=100.0)
    far_emph = _target(_fake_cp(RegionPriority.EMPHASIZED), distance=150.0)
    ignored = _target(_fake_cp(RegionPriority.IGNORED), distance=1.0)
    out = list(
        finder._targets_by_range([near_deprio, far_emph, ignored])  # type: ignore[type-var]
    )
    assert out == [ignored, near_deprio, far_emph]


def test_weighted_mode_identity_when_setting_off() -> None:
    finder = _finder(on=False)
    near_deprio = _target(_fake_cp(RegionPriority.DEPRIORITIZED), distance=100.0)
    far_emph = _target(_fake_cp(RegionPriority.EMPHASIZED), distance=150.0)
    out = list(
        finder._targets_by_range([near_deprio, far_emph], weighted=True)  # type: ignore[type-var]
    )
    assert out == [near_deprio, far_emph]


def test_red_planner_never_weighted() -> None:
    finder = _finder(on=True, player=Player.RED)
    near_ignored = _target(_fake_cp(RegionPriority.IGNORED), distance=100.0)
    far = _target(_fake_cp(), distance=150.0)
    out = list(
        finder._targets_by_range([near_ignored, far], weighted=True)  # type: ignore[type-var]
    )
    assert out == [near_ignored, far]


def _targets_of(methods: object) -> list[object]:
    """The target of each single-task method a compound task yielded."""
    return [m[0].target for m in methods]  # type: ignore[attr-defined]


def _state(on: bool, player: Player = Player.BLUE, **lists: object) -> SimpleNamespace:
    context = SimpleNamespace(
        settings=_settings(on),
        coalition=SimpleNamespace(player=player),
        theater=SimpleNamespace(),
    )
    return SimpleNamespace(context=context, **lists)


def test_an_ignored_ship_is_not_tasked_but_stays_a_threat() -> None:
    """`state.enemy_ships` feeds the threat zones as well as AttackShips.

    Flown 2026-08-20 (test.retribution turn 2): an IGNORED red carrier still drew an
    anti-ship package plus escort, because the task read the list and nothing gated
    it. Filtering the list itself instead would route blue over the carrier.
    """
    ignored = _fake_cp(RegionPriority.IGNORED)
    normal = _fake_cp(RegionPriority.NORMAL)
    carrier, freighter = _target(ignored), _target(normal)
    state = _state(True, enemy_ships=[carrier, freighter])

    assert auto_planning_skips(carrier, state)
    assert not auto_planning_skips(freighter, state)
    tasked = _targets_of(AttackShips().each_valid_method(state))  # type: ignore[arg-type]
    assert tasked == [freighter]
    assert state.enemy_ships == [carrier, freighter]


def test_ignored_ships_still_tasked_when_the_feature_is_off() -> None:
    ignored = _fake_cp(RegionPriority.IGNORED)
    carrier = _target(ignored)
    state = _state(False, enemy_ships=[carrier])
    methods = AttackShips().each_valid_method(state)  # type: ignore[arg-type]
    assert _targets_of(methods) == [carrier]


def test_red_never_reads_blues_ignore_list_for_ships() -> None:
    carrier = _target(_fake_cp(RegionPriority.IGNORED))
    state = _state(True, player=Player.RED, enemy_ships=[carrier])
    methods = AttackShips().each_valid_method(state)  # type: ignore[arg-type]
    assert _targets_of(methods) == [carrier]


def test_an_ignored_cp_gets_neither_bai_nor_armed_recon() -> None:
    ignored = _fake_cp(RegionPriority.IGNORED)
    normal = _fake_cp(RegionPriority.NORMAL)
    hidden, live = _target(ignored), _target(normal)
    state = _state(
        True,
        enemy_battle_positions={
            ignored: SimpleNamespace(in_priority_order=[hidden]),
            normal: SimpleNamespace(in_priority_order=[live]),
        },
        control_point_priority_queue=[ignored, normal],
    )
    methods = AttackBattlePositions().each_valid_method(state)  # type: ignore[arg-type]
    targets = _targets_of(methods)
    assert hidden not in targets
    assert live in targets
    assert ignored not in targets
    assert normal in targets


def test_an_ignored_regions_sam_is_not_hunted_but_still_answers_a_threat() -> None:
    """DegradeIads has two tiers and only one of them chooses a region.

    Flown 2026-08-20 on test.retribution: with Sukhumi-Babushara IGNORED, its MERAD
    (CASTOR) was still offered as a DEAD target by the opportunistic tier. The
    reactive tier stays ungated on purpose -- a SAM shooting at a package flying
    somewhere else is a threat response, not a choice of where to work.
    """
    ignored, normal = _fake_cp(RegionPriority.IGNORED), _fake_cp(RegionPriority.NORMAL)
    hidden, live = _target(ignored), _target(normal)
    for sam in (hidden, live):
        sam.task = GroupTask.MERAD
        sam.max_threat_range = lambda: SimpleNamespace(meters=40_000.0)

    state = _state(
        True,
        enemy_air_defenses=[hidden, live],
        threatening_air_defenses=[],
        detecting_air_defenses=[],
        priority_cp=None,
    )
    assert _targets_of(DegradeIads().each_valid_method(state)) == [live]  # type: ignore[arg-type]

    # ... but the same SAM, once it threatens a planned package, is serviced.
    state.threatening_air_defenses = [hidden]
    assert hidden in _targets_of(DegradeIads().each_valid_method(state))  # type: ignore[arg-type]
