"""Save-compat tombstones for the retired SOF capture economy (removed 2026-07-01).

The loop's dead code is gone; what remains is the unpickle tombstone
(``PendingSofRescue``), the theater sweep for stale "downed SOF team" objectives
a pre-retirement save still carries, and the no-tasking guarantee on the
tombstoned ground-object class.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from game.scar_rescue import PendingSofRescue, purge_legacy_sof_state
from game.theater import Player
from game.theater.theatergroundobject import DownedSofGroundObject


def test_pending_sof_rescue_tombstone_constructs() -> None:
    # Old saves unpickle PendingSofRescue instances before Coalition.__setstate__
    # drops the list, so the class must keep its persisted field shape.
    rescue = PendingSofRescue(x=1.0, y=2.0)
    assert rescue.turns_remaining == 3
    assert rescue.anchor_cp_id is None


def _downed_sof(tgo_id: str) -> Any:
    tgo = DownedSofGroundObject.__new__(DownedSofGroundObject)
    tgo.id = tgo_id  # type: ignore[assignment]
    return tgo


def test_purge_removes_stale_downed_sof_objectives() -> None:
    stale = _downed_sof("sof-1")
    keeper = SimpleNamespace(id="live-1")
    cp = SimpleNamespace(connected_objectives=[stale, keeper])
    removed: list[str] = []
    game = SimpleNamespace(
        theater=SimpleNamespace(controlpoints=[cp]),
        db=SimpleNamespace(
            tgos=SimpleNamespace(
                objects={"sof-1": stale}, remove=lambda tgo_id: removed.append(tgo_id)
            )
        ),
    )

    purge_legacy_sof_state(cast(Any, game))

    assert cp.connected_objectives == [keeper]
    assert removed == ["sof-1"]


def test_purge_is_a_noop_on_a_clean_theater() -> None:
    keeper = SimpleNamespace(id="live-1")
    cp = SimpleNamespace(connected_objectives=[keeper])
    game = SimpleNamespace(
        theater=SimpleNamespace(controlpoints=[cp]),
        db=SimpleNamespace(tgos=SimpleNamespace(objects={}, remove=lambda _: None)),
    )

    purge_legacy_sof_state(cast(Any, game))

    assert cp.connected_objectives == [keeper]


def test_tombstoned_objective_offers_no_tasking() -> None:
    # A stale instance from an old save must never surface a plannable mission
    # (it is purged at the next turn initialization anyway).
    tgo = _downed_sof("sof-1")
    assert list(tgo.mission_types(Player.BLUE)) == []
    assert list(tgo.mission_types(Player.RED)) == []
