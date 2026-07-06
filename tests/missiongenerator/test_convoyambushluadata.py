"""Convoy-ambush emitter (dcsRetribution.convoyAmbush) -- the plugin's runtime config.

Locks the shape the ``convoyambush`` plugin consumes: each live ambush pairing on
``game.convoy_ambush_state`` emits the ambush team's alive group names + centre and the
escorted convoy's group name; a record whose TGO is gone or fully dead is dropped; and the
whole node is gated on the ``convoy_ambush`` setting.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.missiongenerator.convoyambushluadata import populate_convoy_ambush_lua
from game.missiongenerator.luagenerator import LuaData, LuaValue


def _kv(item: Any) -> dict[str, Any]:
    vals = item.value
    if isinstance(vals, LuaValue):
        vals = [vals]
    return {v.key: v.value for v in vals}


class _Point:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y


def _unit(alive: bool = True) -> Any:
    return SimpleNamespace(alive=alive)


def _tgo(tgo_id: str, group_name: str, units: list[Any], pos: _Point) -> Any:
    return SimpleNamespace(
        id=tgo_id,
        groups=[SimpleNamespace(group_name=group_name, units=units)],
        position=pos,
    )


def _game(tgos: list[Any], ambushes: list[dict[str, Any]], *, on: bool = True) -> Any:
    cp = SimpleNamespace(ground_objects=tgos)
    return SimpleNamespace(
        settings=SimpleNamespace(convoy_ambush=on),
        convoy_ambush_state={"ambushes": ambushes},
        theater=SimpleNamespace(controlpoints=[cp]),
    )


def _ambushes(game: Any) -> list[dict[str, Any]]:
    root = LuaData("dcsRetribution")
    populate_convoy_ambush_lua(root, game, mission_data=None)  # type: ignore[arg-type]
    node = root.get_item("convoyAmbush")
    if node is None:
        return []
    ambushes = node.get_item("ambushes")
    assert isinstance(ambushes, LuaData)
    return [_kv(rec) for rec in ambushes.objects]


def test_emits_each_pairing_with_team_and_convoy_groups() -> None:
    tgo = _tgo("t1", "Ambush | t1", [_unit()], _Point(1000.0, 2000.0))
    game = _game([tgo], [{"tgo_id": "t1", "convoy": "Convoy-1"}])
    ambushes = _ambushes(game)
    assert len(ambushes) == 1
    assert ambushes[0]["groups"] == ["Ambush | t1"]
    assert ambushes[0]["x"] == "1000.0" and ambushes[0]["y"] == "2000.0"
    assert ambushes[0]["convoyGroups"] == ["Convoy-1"]


def test_emits_without_convoy_groups_when_the_pairing_lost_its_convoy_name() -> None:
    tgo = _tgo("t1", "Ambush | t1", [_unit()], _Point(0.0, 0.0))
    game = _game([tgo], [{"tgo_id": "t1"}])  # no "convoy" key
    ambushes = _ambushes(game)
    assert len(ambushes) == 1
    assert "convoyGroups" not in ambushes[0]


def test_drops_a_record_whose_tgo_is_gone_or_dead() -> None:
    dead = _tgo("t1", "Ambush | t1", [_unit(alive=False)], _Point(0.0, 0.0))
    game = _game(
        [dead],
        [
            {"tgo_id": "t1", "convoy": "Convoy-1"},  # fully dead -> no alive group
            {"tgo_id": "missing", "convoy": "Convoy-2"},  # no such TGO
        ],
    )
    assert _ambushes(game) == []


def test_gated_off_by_the_setting() -> None:
    tgo = _tgo("t1", "Ambush | t1", [_unit()], _Point(0.0, 0.0))
    game = _game([tgo], [{"tgo_id": "t1", "convoy": "Convoy-1"}], on=False)
    assert _ambushes(game) == []
