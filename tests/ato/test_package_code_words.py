from __future__ import annotations

from game.ato.codewords import _CODE_WORD_POOL, PackageCodeWords
from game.ato.package import Package


def test_random_code_words_are_distinct_and_from_the_pool() -> None:
    cw = PackageCodeWords.random()
    assert len({cw.push, cw.success, cw.abort}) == 3
    for word in (cw.push, cw.success, cw.abort):
        assert word in _CODE_WORD_POOL


def test_code_words_assigned_once_and_stay_stable() -> None:
    # Stability across accesses is what protects a planner's briefing when the
    # mission is regenerated within a turn. __new__ exercises the property without
    # constructing a full Package (target/db).
    package = Package.__new__(Package)
    package._code_words = None

    first = package.code_words
    assert package.code_words is first  # cached, never re-rolled
    assert package._code_words is first  # stored on the package (pickled with the save)


def test_code_words_migrate_packages_pickled_before_the_field() -> None:
    # A package pickled before the field existed has no ``_code_words`` attribute at
    # all; the property's ``getattr`` default assigns one lazily.
    legacy = Package.__new__(Package)
    assert not hasattr(legacy, "_code_words")

    assigned = legacy.code_words
    assert legacy.code_words is assigned  # stable after the lazy assignment
