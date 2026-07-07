"""Unit tests for the drop-spawn placement decision logic (§20).

These cover the Lua-free Python gate in :func:`place_unit_group` — terrain
validation, the non-cheat 200 km range limit (and the two bypasses), and the
"Deploy Next Turn" queueing path — without the heavy ``_materialise`` step,
which builds real DCS groups and is covered by the in-game pass instead.

The pattern (stub ``Point.from_latlng`` with ``terrain=None`` and fake the
game/theater/coalition graph with ``SimpleNamespace``) mirrors
``tests/server/test_tgo_movement_routes.py``.
"""

from types import SimpleNamespace
from typing import Any

import pytest
from dcs.mapping import Point

from game.data.groups import GroupTask
from game.theater.controlpoint import Player
from game.theater.unitplacement import (
    PendingUnitPlacement,
    _is_sea_layout,
    place_unit_group,
    process_pending_placements,
)


def _layout(*, sea: bool) -> Any:
    tasks = {GroupTask.NAVY} if sea else {GroupTask.AAA}
    return SimpleNamespace(tasks=tasks)


def _game(
    *,
    on_land: bool = True,
    in_sea: bool = True,
    has_cp: bool = True,
    free_cheat: bool = False,
) -> Any:
    cp = SimpleNamespace(position=Point(0, 0, None), is_fleet=False)  # type: ignore[arg-type]
    theater = SimpleNamespace(
        terrain=None,
        is_on_land=lambda p: on_land,
        is_in_sea=lambda p: in_sea,
        control_points_for=lambda player: ([cp] if has_cp else []),
    )
    return SimpleNamespace(
        theater=theater,
        settings=SimpleNamespace(enable_free_unit_placement=free_cheat),
        pending_unit_placements=[],
    )


def _coalition() -> Any:
    return SimpleNamespace(player=Player.BLUE)


def _force_group() -> Any:
    # Only read at _materialise (tasks[0]); never reached on these gate paths.
    return SimpleNamespace(tasks=[GroupTask.AAA])


@pytest.fixture(autouse=True)
def _patch_latlng(monkeypatch: pytest.MonkeyPatch) -> None:
    # from_latlng needs a real terrain projection; with terrain=None return a
    # point whose x/y are the raw lat/lng (so they read as meters for the
    # distance check), matching the route-test stub.
    monkeypatch.setattr(
        "game.theater.unitplacement.Point.from_latlng",
        staticmethod(lambda latlng, terrain: Point(latlng.lat, latlng.lng, None)),  # type: ignore[arg-type]
    )


def _place(game: Any, layout: Any, **kw: Any) -> Any:
    return place_unit_group(
        game,
        _coalition(),
        kw.pop("lat", 0.0),
        kw.pop("lng", 0.0),
        _force_group(),
        layout,
        [],  # selections
        **kw,
    )


def test_is_sea_layout() -> None:
    assert _is_sea_layout(SimpleNamespace(tasks={GroupTask.NAVY})) is True  # type: ignore[arg-type]
    assert _is_sea_layout(SimpleNamespace(tasks={GroupTask.AIRCRAFT_CARRIER})) is True  # type: ignore[arg-type]
    assert _is_sea_layout(SimpleNamespace(tasks={GroupTask.AAA})) is False  # type: ignore[arg-type]
    assert _is_sea_layout(SimpleNamespace(tasks=set())) is False  # type: ignore[arg-type]


def test_land_layout_in_sea_rejected() -> None:
    with pytest.raises(ValueError, match="on land"):
        _place(_game(on_land=False), _layout(sea=False))


def test_sea_layout_on_land_rejected() -> None:
    with pytest.raises(ValueError, match="in sea"):
        _place(_game(in_sea=False), _layout(sea=True))


def test_no_friendly_cp_rejected() -> None:
    with pytest.raises(ValueError, match="no control points"):
        _place(_game(has_cp=False), _layout(sea=False))


def test_out_of_range_rejected() -> None:
    # 300 km from the only CP (at origin), no free bypass -> rejected.
    with pytest.raises(ValueError, match="km from nearest"):
        _place(_game(), _layout(sea=False), lat=300_000.0)


def test_free_flag_bypasses_range_and_queues() -> None:
    game = _game()
    result = _place(
        game, _layout(sea=False), lat=300_000.0, free=True, deploy_next_turn=True
    )
    assert isinstance(result, PendingUnitPlacement)
    assert result.free is True
    assert result.coalition_player_is_blue is True
    assert game.pending_unit_placements == [result]


def test_free_cheat_setting_bypasses_range() -> None:
    game = _game(free_cheat=True)
    result = _place(game, _layout(sea=False), lat=300_000.0, deploy_next_turn=True)
    assert isinstance(result, PendingUnitPlacement)
    assert game.pending_unit_placements == [result]


def test_deploy_next_turn_queues_in_range() -> None:
    game = _game()
    result = _place(game, _layout(sea=False), deploy_next_turn=True, respawn=True)
    assert isinstance(result, PendingUnitPlacement)
    assert result.respawn is True
    assert game.pending_unit_placements == [result]


def test_discarded_pending_placement_refunds_its_cost() -> None:
    """A deploy-next-turn placement charged at queue time must refund if it can
    no longer be satisfied (here: the CP is gone by materialisation time)."""
    game = _game(has_cp=True)
    coalition = SimpleNamespace(player=Player.BLUE, budget=100.0)
    pending = PendingUnitPlacement(
        lat=0.0,
        lng=0.0,
        coalition_player_is_blue=True,
        force_group=_force_group(),
        layout=_layout(sea=False),
        cost=25.0,
    )
    game.pending_unit_placements = [pending]
    # The CP is lost before the placement materialises.
    game.theater.control_points_for = lambda player: []
    process_pending_placements(game, coalition)  # type: ignore[arg-type]
    assert game.pending_unit_placements == []  # discarded
    assert coalition.budget == 125.0  # refunded


def test_free_pending_placement_is_not_refunded() -> None:
    game = _game(has_cp=True)
    coalition = SimpleNamespace(player=Player.BLUE, budget=100.0)
    pending = PendingUnitPlacement(
        coalition_player_is_blue=True,
        force_group=_force_group(),
        layout=_layout(sea=False),
        free=True,
        cost=0.0,
    )
    game.pending_unit_placements = [pending]
    game.theater.control_points_for = lambda player: []
    process_pending_placements(game, coalition)  # type: ignore[arg-type]
    assert coalition.budget == 100.0  # nothing charged, nothing refunded
