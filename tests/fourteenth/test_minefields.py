"""Cross-turn minefield reconcile (§57 Phase 2).

Locks how the plugin's end-of-mission field report folds into ``game.minefields``: a known
persisted field takes the plugin's charge count (and is removed once exhausted), a newly-laid
field (id 0) that survived is promoted to a persisted record with a fresh id, a persisted field
the plugin did not report is left untouched, and the whole step is a no-op when the feature is
off or nothing was reported.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from dcs.mapping import Point
from dcs.terrain import Caucasus

from game.fourteenth.minefields import (
    Minefield,
    active_minefields,
    reconcile_minefields,
)

TERR = Caucasus()


def _mf(fid: int, x: float, z: float, charges: int) -> Minefield:
    return Minefield(
        id=fid, position=Point(x, z, TERR), radius_m=200.0, charges=charges
    )


def _game(
    fields: list[Minefield] | None = None, *, on: bool = True, turn: int = 3
) -> Any:
    return SimpleNamespace(
        settings=SimpleNamespace(air_droppable_minefields=on),
        minefields=list(fields or []),
        theater=SimpleNamespace(terrain=TERR),
        turn=turn,
    )


def _debrief(reports: list[tuple[int, float, float, float, int]]) -> Any:
    return SimpleNamespace(state_data=SimpleNamespace(minefields_state=reports))


def test_new_field_is_created_with_a_fresh_id_and_laid_turn() -> None:
    game = _game(turn=7)
    reconcile_minefields(game, _debrief([(0, 1000.0, 2000.0, 250.0, 4)]))
    assert len(game.minefields) == 1
    m = game.minefields[0]
    assert m.id >= 1
    assert m.charges == 4
    assert m.position.x == 1000.0 and m.position.y == 2000.0
    assert m.radius_m == 250.0
    assert m.laid_turn == 7


def test_existing_field_takes_reported_charges_and_exhausted_is_removed() -> None:
    game = _game([_mf(1, 0.0, 0.0, 6), _mf(2, 100.0, 100.0, 6)])
    reconcile_minefields(
        game, _debrief([(1, 0.0, 0.0, 200.0, 3), (2, 100.0, 100.0, 200.0, 0)])
    )
    surviving = {m.id: m for m in game.minefields}
    assert set(surviving) == {1}  # field 2 exhausted -> removed
    assert surviving[1].charges == 3


def test_unreported_persisted_field_is_left_untouched() -> None:
    # Field 1 exists but the plugin only reports an unrelated (unknown) field 9.
    game = _game([_mf(1, 0.0, 0.0, 6)])
    reconcile_minefields(game, _debrief([(9, 5.0, 5.0, 200.0, 2)]))
    assert [m.id for m in game.minefields] == [1]
    assert game.minefields[0].charges == 6  # a field nobody drove over does not decay


def test_empty_report_is_a_noop() -> None:
    game = _game([_mf(1, 0.0, 0.0, 6)])
    reconcile_minefields(game, _debrief([]))
    assert len(game.minefields) == 1 and game.minefields[0].charges == 6


def test_off_is_a_noop_even_with_a_report() -> None:
    game = _game([_mf(1, 0.0, 0.0, 6)], on=False)
    reconcile_minefields(
        game, _debrief([(1, 0.0, 0.0, 200.0, 0)])
    )  # would remove if on
    assert len(game.minefields) == 1 and game.minefields[0].charges == 6


def test_multiple_new_fields_get_distinct_ids() -> None:
    game = _game([_mf(5, 0.0, 0.0, 6)])  # existing id 5
    reconcile_minefields(
        game, _debrief([(0, 10.0, 10.0, 200.0, 3), (0, 20.0, 20.0, 200.0, 2)])
    )
    ids = sorted(m.id for m in game.minefields)
    assert len(set(ids)) == len(ids) == 3  # unique, no collision with the existing 5
    assert 5 in ids
    assert len(active_minefields(game)) == 3


def test_new_field_that_exhausted_same_mission_is_not_created() -> None:
    game = _game()
    reconcile_minefields(game, _debrief([(0, 10.0, 10.0, 200.0, 0)]))  # id 0, 0 charges
    assert game.minefields == []
