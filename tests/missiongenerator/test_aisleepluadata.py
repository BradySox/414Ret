"""Ground-AI-sleep emitter (dcsRetribution.aiSleep) -- the sleepable positive list.

Locks the safety contract the ``aisleep`` plugin depends on: only ``armor``-category
garrison groups with alive vehicles are emitted; the air-defense network, missile
sites, ships and building TGOs are never eligible; and the concealed/map-hidden set
(exactly the COIN / convoy-ambush scripted movers, whose routes a sleeping
controller would kill) is skipped. Gated by ``perf_ground_ai_sleep``.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.missiongenerator.aisleepluadata import populate_ai_sleep_lua
from game.missiongenerator.luagenerator import LuaData


def _unit(alive: bool = True, vehicle: bool = True) -> Any:
    return SimpleNamespace(alive=alive, is_vehicle=vehicle, is_static=not vehicle)


def _tgo(
    category: str,
    group_name: str,
    units: list[Any] | None = None,
    *,
    concealed: bool = False,
    map_hidden: bool = False,
) -> Any:
    return SimpleNamespace(
        category=category,
        groups=[
            SimpleNamespace(group_name=group_name, units=units or [_unit()]),
        ],
        concealed=concealed,
        map_hidden=map_hidden,
    )


def _game(tgos: list[Any], *, on: bool = True) -> Any:
    cp = SimpleNamespace(ground_objects=tgos)
    return SimpleNamespace(
        settings=SimpleNamespace(perf_ground_ai_sleep=on),
        theater=SimpleNamespace(controlpoints=[cp]),
    )


def _groups(game: Any) -> list[str]:
    root = LuaData("dcsRetribution")
    populate_ai_sleep_lua(root, game)
    node = root.get_item("aiSleep")
    if node is None:
        return []
    values = node.value
    assert isinstance(values, list) and len(values) == 1
    assert values[0].key == "groups"
    return list(values[0].value)


def test_emits_each_live_garrison_group() -> None:
    a = _tgo("armor", "0100 | Garrison A")
    b = _tgo("armor", "0101 | Garrison B")
    assert _groups(_game([a, b])) == ["0100 | Garrison A", "0101 | Garrison B"]


def test_never_emits_air_defense_missiles_ships_or_buildings() -> None:
    sam = _tgo("aa", "0102 | SA-6")
    ewr = _tgo("ewr", "0103 | EWR")
    scud = _tgo("missile", "0104 | SCUD")
    coastal = _tgo("coastal", "0105 | Silkworm")
    ship = _tgo("ship", "0106 | Grisha")
    ammo = _tgo("ammo", "0107 | Cache", [_unit(vehicle=False)])
    motorpool = _tgo("motorpool", "0108 | Depot")
    assert _groups(_game([sam, ewr, scud, coastal, ship, ammo, motorpool])) == []


def test_skips_the_scripted_movers_concealed_and_map_hidden() -> None:
    cell = _tgo("armor", "0109 | COIN cell", concealed=True)
    ambush = _tgo("armor", "0110 | Ambush team", map_hidden=True)
    plain = _tgo("armor", "0111 | Garrison")
    assert _groups(_game([cell, ambush, plain])) == ["0111 | Garrison"]


def test_skips_dead_and_statics_only_groups() -> None:
    dead = _tgo("armor", "0112 | Dead garrison", [_unit(alive=False)])
    statics = _tgo("armor", "0113 | Revetments", [_unit(vehicle=False)])
    assert _groups(_game([dead, statics])) == []


def test_gated_off_by_the_setting() -> None:
    garrison = _tgo("armor", "0114 | Garrison")
    assert _groups(_game([garrison], on=False)) == []


def test_no_eligible_groups_emits_no_node() -> None:
    root = LuaData("dcsRetribution")
    populate_ai_sleep_lua(root, _game([]))
    assert root.get_item("aiSleep") is None
