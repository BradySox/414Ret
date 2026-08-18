"""A deleted module still has to unpickle out of an existing save.

Pickle resolves a class in `find_class` BEFORE `__setstate__` runs. So an owner
that already drops the orphan key -- `AirWing.__setstate__` pops
`pending_arrivals` -- still cannot load the save without a tombstone here. The
§82 "Wing Grows" removal (2026-08-16) did the first half and missed the second,
which made every save written before that date fail to load with
`ModuleNotFoundError: game.fourteenth.wing_growth`.
"""

from __future__ import annotations

import importlib
import io

import pytest

from game.persistency import REMOVED_MODULES, DummyObject, MigrationUnpickler


def _unpickler() -> MigrationUnpickler:
    return MigrationUnpickler(io.BytesIO(b""))


@pytest.mark.parametrize("module", REMOVED_MODULES)
def test_a_tombstoned_module_resolves_to_a_placeholder(module: str) -> None:
    assert _unpickler().find_class(module, "AnyClassName") is DummyObject


def test_wing_growth_is_tombstoned() -> None:
    """The §82 regression: saves from before 2026-08-16 pickle this module."""
    assert "game.fourteenth.wing_growth" in REMOVED_MODULES
    assert (
        _unpickler().find_class("game.fourteenth.wing_growth", "PendingSquadron")
        is DummyObject
    )


@pytest.mark.parametrize("module", REMOVED_MODULES)
def test_a_tombstoned_module_is_actually_gone(module: str) -> None:
    """A tombstone for a live module would shadow the real class on load."""
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(module)


def test_an_untombstoned_missing_module_still_fails_loudly() -> None:
    """The list is an allowlist, not a blanket catch.

    A genuinely missing module -- a bad install, a typo in a refactor -- must
    still raise rather than silently degrade the save it appears in.
    """
    with pytest.raises(ModuleNotFoundError):
        _unpickler().find_class("game.fourteenth.not_a_real_module", "Whatever")


def test_the_placeholder_absorbs_whatever_state_the_save_carried() -> None:
    """DummyObject is reconstructed by pickle and handed the orphan's state."""
    placeholder = DummyObject()
    placeholder.__setstate__({"turn": 4, "note": "orphaned"})

    assert placeholder.__dict__["turn"] == 4
