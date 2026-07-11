"""Minefield emitter (dcsRetribution.minefields) -- re-arms persisted fields (§57 Phase 2).

Locks the shape the ``minefields`` plugin re-arms from: each live field on ``game.minefields``
emits its id + centre (x = north, z = east) + radius + charges; exhausted fields are skipped;
and the whole node is gated on ``air_droppable_minefields``.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.missiongenerator.luagenerator import LuaData, LuaValue
from game.missiongenerator.minefieldluadata import populate_minefields_lua


def _kv(item: Any) -> dict[str, Any]:
    vals = item.value
    if isinstance(vals, LuaValue):
        vals = [vals]
    return {v.key: v.value for v in vals}


class _Point:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y


def _mf(fid: int, x: float, z: float, radius: float, charges: int) -> Any:
    return SimpleNamespace(
        id=fid, position=_Point(x, z), radius_m=radius, charges=charges
    )


def _game(fields: list[Any], *, on: bool = True) -> Any:
    return SimpleNamespace(
        settings=SimpleNamespace(air_droppable_minefields=on),
        minefields=list(fields),
    )


def _fields(game: Any) -> list[dict[str, Any]]:
    root = LuaData("dcsRetribution")
    populate_minefields_lua(root, game, mission_data=None)  # type: ignore[arg-type]
    node = root.get_item("minefields")
    if node is None:
        return []
    field_list = node.get_item("fields")
    assert isinstance(field_list, LuaData)
    return [_kv(rec) for rec in field_list.objects]


def test_emits_each_live_field() -> None:
    game = _game([_mf(3, 1000.0, 2000.0, 250.0, 4)])
    fields = _fields(game)
    assert len(fields) == 1
    assert fields[0] == {
        "id": "3",
        "x": "1000.0",
        "z": "2000.0",
        "radius": "250.0",
        "charges": "4",
    }


def test_skips_exhausted_fields() -> None:
    game = _game([_mf(1, 0.0, 0.0, 200.0, 0), _mf(2, 10.0, 10.0, 200.0, 3)])
    assert [f["id"] for f in _fields(game)] == ["2"]


def test_no_live_field_emits_no_node() -> None:
    assert _fields(_game([])) == []
    assert _fields(_game([_mf(1, 0.0, 0.0, 200.0, 0)])) == []


def test_gated_off_by_the_setting() -> None:
    game = _game([_mf(1, 0.0, 0.0, 200.0, 4)], on=False)
    assert _fields(game) == []
