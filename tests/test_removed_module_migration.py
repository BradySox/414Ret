"""Save-load compat for the 2026-07-21 ROE / §40 / §55 and will / war-economy removals.

The modules ``game.fourteenth.{phases, red_intent, zone_drawings}`` were deleted in the ROE
drop, and ``game.fourteenth.{political_will, commitment_ceiling, static_front, war_economy}``
in the will / §53 / §54 economy drop. A pre-removal save pickled ``game.phase_baseline``
(``campaign_phases`` was default ON, so nearly every in-progress save carries a
``PhaseBaseline``), ``red_intent_*`` state (``RedIntentBaseline`` / ``RedIntentSample`` /
the ``RedPosture`` / ``FrontPosture`` enums), ``theater.zone_drawings`` (``DrawnZone``), and
``game.will_ledger`` (a list of ``WillLedgerEntry``) when those were enabled. Unpickling
those instances would raise ``ModuleNotFoundError``. The ``MigrationUnpickler`` degrades
them to an inert ``DummyObject`` placeholder so the save still loads; the game/theater
``__setstate__`` no longer restores those attributes (will_ledger is popped), so the
placeholders are never read.
"""

from __future__ import annotations

import io
import pickle
from dataclasses import dataclass

from game.persistency import DummyObject, MigrationUnpickler

_REMOVED_MODULES = (
    "game.fourteenth.phases",
    "game.fourteenth.red_intent",
    "game.fourteenth.zone_drawings",
    "game.fourteenth.political_will",
    "game.fourteenth.commitment_ceiling",
    "game.fourteenth.static_front",
    "game.fourteenth.war_economy",
)


@dataclass
class _FakeRemovedDataclass:
    """Stands in for PhaseBaseline etc. (module-level so pickle can reference it)."""

    turn: int


def test_find_class_degrades_removed_modules_to_placeholder() -> None:
    unpickler = MigrationUnpickler(io.BytesIO(b""))
    for module in _REMOVED_MODULES:
        # Any class name from a deleted module resolves to the inert placeholder,
        # instead of raising ModuleNotFoundError from super().find_class.
        assert unpickler.find_class(module, "PhaseBaseline") is DummyObject
        assert unpickler.find_class(module, "AnythingAtAll") is DummyObject


def test_find_class_leaves_live_modules_alone() -> None:
    from game.fourteenth.red_tempo import RedTempoWindow

    unpickler = MigrationUnpickler(io.BytesIO(b""))
    # A surviving fourteenth module still resolves to its real class.
    resolved = unpickler.find_class("game.fourteenth.red_tempo", "RedTempoWindow")
    assert resolved is RedTempoWindow


def test_placeholder_absorbs_dataclass_and_enum_reconstruction() -> None:
    # Removed *dataclass* path: pickle reconstructs via __new__ + __setstate__.
    obj = DummyObject.__new__(DummyObject)
    obj.__setstate__({"turn": 7})
    assert obj.__dict__ == {"turn": 7}
    # Removed *enum* path: pickle reconstructs an enum member via cls(value), which
    # must not crash (the old default __init__ took no args).
    assert isinstance(DummyObject("surge"), DummyObject)
    assert isinstance(DummyObject(3), DummyObject)


def test_pre_removal_save_object_unpickles_without_crashing() -> None:
    # Simulate a save that pickled a game.fourteenth.phases.PhaseBaseline: pickle a real
    # dataclass at protocol 0 (ASCII GLOBAL opcodes), rewrite the class reference to the
    # deleted module path, and prove MigrationUnpickler loads it to a placeholder that
    # still carries the pickled state (vs. the crash super().find_class would raise).
    raw = pickle.dumps(_FakeRemovedDataclass(turn=9), protocol=0)
    rewritten = raw.replace(
        f"c{_FakeRemovedDataclass.__module__}\n_FakeRemovedDataclass\n".encode(),
        b"cgame.fourteenth.phases\nPhaseBaseline\n",
    )
    assert rewritten != raw, "protocol-0 class reference was not where expected"
    loaded = MigrationUnpickler(io.BytesIO(rewritten)).load()
    assert isinstance(loaded, DummyObject)
    assert loaded.__dict__.get("turn") == 9
