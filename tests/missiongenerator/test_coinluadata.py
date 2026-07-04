"""COIN in-mission movement emitter (dcsRetribution.coin).

Locks the shape the ``coin`` plugin consumes: a live HVT convoy emits its DCS group
name(s) + centre; each **mobile** VBIED emits its group(s) + position + the nearest
friendly base as a drive target; **static** roadside IEDs are never emitted (they don't
move); and the whole node is gated on ``coin_insurgency`` plus the per-object toggles, so
a non-COIN mission carries no ``coin`` node at all.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.missiongenerator.coinluadata import populate_coin_lua
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

    def distance_to_point(self, other: "_Point") -> float:
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5


def _tgo(tgo_id: str, group_name: str, pos: _Point) -> Any:
    return SimpleNamespace(
        id=tgo_id,
        groups=[SimpleNamespace(group_name=group_name)],
        position=pos,
    )


def _cp(kind: str, pos: _Point, tgos: list[Any]) -> Any:
    return SimpleNamespace(
        captured=SimpleNamespace(is_blue=(kind == "blue")),
        position=pos,
        ground_objects=tgos,
    )


def _game(*, insurgency: bool = True, hvt: bool = True, ied: bool = True) -> Any:
    hvt_tgo = _tgo("hvt1", "0042 | HVT Qari", _Point(100.0, 200.0))
    vbied_tgo = _tgo("vbied1", "0051 | VBIED", _Point(300.0, 400.0))
    static_tgo = _tgo("ied1", "0052 | IED", _Point(500.0, 600.0))
    red = _cp("red", _Point(300.0, 0.0), [hvt_tgo, vbied_tgo, static_tgo])
    blue = _cp("blue", _Point(0.0, 0.0), [])
    return SimpleNamespace(
        settings=SimpleNamespace(
            coin_insurgency=insurgency, coin_hvt=hvt, coin_ied=ied
        ),
        coin_state={
            "hvt": {"active": {"tgo_id": "hvt1", "name": "Qari"}},
            "ieds": [
                {"tgo_id": "ied1", "kind": "ied"},  # static -> never emitted
                {"tgo_id": "vbied1", "kind": "vbied", "target": "Base"},
            ],
        },
        theater=SimpleNamespace(controlpoints=[red, blue]),
    )


def _populate(game: Any) -> LuaData:
    root = LuaData("dcsRetribution")
    populate_coin_lua(root, game, mission_data=None)  # type: ignore[arg-type]
    return root


def test_emits_hvt_convoy_and_mobile_vbied() -> None:
    coin = _populate(_game()).get_item("coin")
    assert coin is not None

    hvt = coin.get_item("hvt")
    assert hvt is not None
    hvt_kv = _kv(hvt)
    assert hvt_kv["groups"] == ["0042 | HVT Qari"]
    assert hvt_kv["x"] == "100.0" and hvt_kv["y"] == "200.0"

    vbieds = coin.get_item("vbieds")
    assert vbieds is not None
    # Exactly one mobile VBIED -- the static IED is not a mover, so it isn't emitted.
    assert len(vbieds.objects) == 1
    v = _kv(vbieds.objects[0])
    assert v["groups"] == ["0051 | VBIED"]
    assert v["x"] == "300.0" and v["y"] == "400.0"
    # Drive target is the nearest friendly base (the blue CP at the origin).
    assert v["targetX"] == "0.0" and v["targetY"] == "0.0"


def test_gated_off_when_coin_insurgency_off() -> None:
    assert _populate(_game(insurgency=False)).get_item("coin") is None


def test_hvt_toggle_off_drops_only_the_hvt() -> None:
    coin = _populate(_game(hvt=False)).get_item("coin")
    assert coin is not None
    assert coin.get_item("hvt") is None
    assert coin.get_item("vbieds") is not None


def test_ied_toggle_off_drops_only_the_vbieds() -> None:
    coin = _populate(_game(ied=False)).get_item("coin")
    assert coin is not None
    assert coin.get_item("hvt") is not None
    assert coin.get_item("vbieds") is None


def test_no_movers_emits_no_node() -> None:
    game = _game()
    game.coin_state = {
        "hvt": {"active": None},
        "ieds": [{"tgo_id": "x", "kind": "ied"}],
    }
    assert _populate(game).get_item("coin") is None
