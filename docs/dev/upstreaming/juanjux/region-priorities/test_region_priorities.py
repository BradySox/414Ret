"""Region priorities — the factor gates, the ordering effect, the drops.

Fakes are duck-typed per the local convention; narrow ignores where the real
signatures expect engine types.

The 414Ret original carries five more tests covering the tasking-gate consumers
(AttackShips / DegradeIads / AttackBattlePositions). Those need the second patch,
which is not in this payload -- see README.md.
"""

from __future__ import annotations

from types import SimpleNamespace

from game.commander.objectivefinder import ObjectiveFinder
from game.data.groups import GroupTask
from game.regionpriorities import (
    TARGET_FAMILIES,
    family_of,
    family_priority,
    priority_for_target,
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


def test_every_family_category_is_a_real_one() -> None:
    """A typo here is silent: the family just never matches a target."""
    from game.theater.theatergroundobject import NAME_BY_CATEGORY

    for family, categories in TARGET_FAMILIES.items():
        for category in categories:
            assert category in NAME_BY_CATEGORY, f"{family}: {category}"


def test_no_category_belongs_to_two_families() -> None:
    seen: set[str] = set()
    for categories in TARGET_FAMILIES.values():
        for category in categories:
            assert category not in seen, category
            seen.add(category)


def test_the_two_axes_multiply() -> None:
    """An emphasized place and a deprioritized kind cancel out, and read that way."""
    cp = _fake_cp(RegionPriority.EMPHASIZED)
    factory = _kinded(cp, "factory")
    settings = _settings_with(True, Infrastructure="deprioritized")
    assert planning_factor(factory, settings, True) == 1.0  # type: ignore[arg-type]


def test_a_target_override_beats_its_base_in_both_directions() -> None:
    """The point of a per-target setting: carve one target out of an ignored base."""
    cp = _fake_cp(RegionPriority.IGNORED)
    spared = _kinded(cp, "factory")
    spared._blue_region_priority = RegionPriority.NORMAL
    inheriting = _kinded(cp, "factory")

    assert priority_for_target(spared) is RegionPriority.NORMAL
    assert priority_for_target(inheriting) is RegionPriority.IGNORED
    settings = _settings(True)
    assert planning_factor(spared, settings, True) == 1.0  # type: ignore[arg-type]
    assert planning_factor(inheriting, settings, True) is None  # type: ignore[arg-type]


def test_an_ignored_family_is_absolute() -> None:
    """Kind is theater-wide policy; no per-target override reopens it."""
    cp = _fake_cp(RegionPriority.EMPHASIZED)
    target = _kinded(cp, "factory")
    target._blue_region_priority = RegionPriority.EMPHASIZED
    settings = _settings_with(True, Infrastructure="ignored")
    assert planning_factor(target, settings, True) is None  # type: ignore[arg-type]


def test_families_do_nothing_while_the_feature_is_off() -> None:
    cp = _fake_cp(RegionPriority.NORMAL)
    target = _kinded(cp, "factory")
    settings = _settings_with(False, Infrastructure="ignored")
    assert planning_factor(target, settings, True) == 1.0  # type: ignore[arg-type]


def test_a_target_with_no_family_is_weighted_by_place_alone() -> None:
    cp = _fake_cp(RegionPriority.DEPRIORITIZED)
    target = _kinded(cp, "fob")  # the FOB structure: never a family member
    assert family_of(target) is None
    assert planning_factor(target, _settings_with(True), True) == 2.0  # type: ignore[arg-type]


def test_an_unknown_stored_value_reads_as_normal() -> None:
    """A hand-edited save must not crash the planner."""
    settings = _settings_with(True, Infrastructure="nonsense")
    assert family_priority("Infrastructure", settings) is RegionPriority.NORMAL  # type: ignore[arg-type]


def test_red_never_reads_the_family_list() -> None:
    cp = _fake_cp(RegionPriority.NORMAL)
    target = _kinded(cp, "factory")
    settings = _settings_with(True, Infrastructure="ignored")
    assert planning_factor(target, settings, False) == 1.0  # type: ignore[arg-type]
