"""Mobile-missile emitter (dcsRetribution.mobileMissiles) -- the SCUD hunt's config.

Locks the shape the ``mobilemissiles`` plugin consumes: each ``category == "missile"``
TGO with at least one alive *vehicle* emits its drivable group names + campaign centre;
anti-air / coastal / building TGOs are never emitted (the SAM network must never move);
statics-only and fully-dead sites are skipped; and the whole node is gated on the
``mobile_missile_relocation`` setting.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.missiongenerator.luagenerator import LuaData, LuaValue
from game.missiongenerator.mobilemissileluadata import populate_mobile_missiles_lua


def _kv(item: Any) -> dict[str, Any]:
    vals = item.value
    if isinstance(vals, LuaValue):
        vals = [vals]
    return {v.key: v.value for v in vals}


class _Point:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y


def _unit(alive: bool = True, vehicle: bool = True) -> Any:
    return SimpleNamespace(alive=alive, is_vehicle=vehicle, is_static=not vehicle)


def _tgo(category: str, group_name: str, units: list[Any], pos: _Point) -> Any:
    return SimpleNamespace(
        category=category,
        groups=[SimpleNamespace(group_name=group_name, units=units)],
        position=pos,
    )


def _game(tgos: list[Any], *, on: bool = True) -> Any:
    cp = SimpleNamespace(ground_objects=tgos)
    return SimpleNamespace(
        settings=SimpleNamespace(mobile_missile_relocation=on),
        theater=SimpleNamespace(controlpoints=[cp]),
    )


def _sites(game: Any) -> list[dict[str, Any]]:
    root = LuaData("dcsRetribution")
    populate_mobile_missiles_lua(root, game, mission_data=None)  # type: ignore[arg-type]
    node = root.get_item("mobileMissiles")
    if node is None:
        return []
    sites = node.get_item("sites")
    assert isinstance(sites, LuaData)
    return [_kv(site) for site in sites.objects]


def test_emits_each_live_missile_site_with_its_drivable_groups() -> None:
    scud = _tgo("missile", "0070 | SCUD", [_unit()], _Point(1000.0, 2000.0))
    sites = _sites(_game([scud]))
    assert len(sites) == 1
    assert sites[0]["groups"] == ["0070 | SCUD"]
    assert sites[0]["x"] == "1000.0" and sites[0]["y"] == "2000.0"


def test_never_emits_the_air_defense_network_or_other_categories() -> None:
    sam = _tgo("aa", "0071 | SA-6", [_unit()], _Point(0.0, 0.0))
    coastal = _tgo("coastal", "0072 | Silkworm", [_unit()], _Point(0.0, 0.0))
    building = _tgo("ammo", "0073 | Cache", [_unit(vehicle=False)], _Point(0.0, 0.0))
    assert _sites(_game([sam, coastal, building])) == []


def test_skips_dead_and_statics_only_sites() -> None:
    dead = _tgo("missile", "0074 | Dead SCUD", [_unit(alive=False)], _Point(0.0, 0.0))
    static_site = _tgo(
        "missile", "0075 | Fixed site", [_unit(vehicle=False)], _Point(0.0, 0.0)
    )
    assert _sites(_game([dead, static_site])) == []


def test_gated_off_by_the_setting() -> None:
    scud = _tgo("missile", "0076 | SCUD", [_unit()], _Point(0.0, 0.0))
    assert _sites(_game([scud], on=False)) == []
