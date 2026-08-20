"""§93 region priorities — the factor gates, the ordering effect, the drops.

Fakes are duck-typed per the local convention; narrow ignores where the real
signatures expect engine types.
"""

from __future__ import annotations

from types import SimpleNamespace

from game.commander.objectivefinder import ObjectiveFinder
from game.fourteenth.region_priorities import (
    RegionPriority,
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
    return SimpleNamespace(region_priorities=on)


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
