"""Mobile-missile emitter (dcsRetribution.mobileMissiles) -- the SCUD hunt's config.

Locks the shape the ``mobilemissiles`` plugin consumes: each moved TGO with at least one
alive *vehicle* emits its drivable group names + campaign centre. ``missile`` sites move
under ``mobile_missile_relocation``; ``coastal`` sites move only when
``coastal_missile_relocation`` is also on (default off, a naval-campaign opt-in). Anti-air
and building TGOs are never emitted (the SAM network must never move); statics-only and
fully-dead sites are skipped.
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


def _game(tgos: list[Any], *, on: bool = True, coastal: bool = False) -> Any:
    cp = SimpleNamespace(ground_objects=tgos)
    return SimpleNamespace(
        settings=SimpleNamespace(
            mobile_missile_relocation=on,
            coastal_missile_relocation=coastal,
        ),
        theater=SimpleNamespace(controlpoints=[cp]),
    )


def _sites(game: Any, mission_data: Any = None) -> list[dict[str, Any]]:
    root = LuaData("dcsRetribution")
    populate_mobile_missiles_lua(root, game, mission_data=mission_data)
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


def test_emits_coastal_sites_only_when_opted_in() -> None:
    silkworm = _tgo("coastal", "0080 | Silkworm", [_unit()], _Point(5.0, 6.0))
    # Default: coastal_missile_relocation off -> a coastal site never moves.
    assert _sites(_game([silkworm])) == []
    # Opted in -> the coastal battery joins the shoot-and-scoot set.
    sites = _sites(_game([silkworm], coastal=True))
    assert len(sites) == 1
    assert sites[0]["groups"] == ["0080 | Silkworm"]


def test_forwards_fire_mission_holds_for_the_sites_own_groups() -> None:
    # §49 fire-then-scoot: a group MissileSiteGenerator armed with a
    # Hold -> FireAtPoint (recorded on mission_data.missile_fire_missions) is
    # forwarded with its hold deadline so the plugin lets it fire before it
    # scoots. Groups without a fire mission carry no hold; another site's
    # entries never bleed in.
    scud = _tgo("missile", "0070 | SCUD", [_unit()], _Point(1.0, 2.0))
    shahed = _tgo("missile", "0071 | SHAHED", [_unit()], _Point(3.0, 4.0))
    mission_data = SimpleNamespace(
        missile_fire_missions={"0071 | SHAHED": 240, "0099 | ELSEWHERE": 60}
    )
    sites = _sites(_game([scud, shahed]), mission_data=mission_data)
    by_group = {s["groups"][0]: s for s in sites}
    assert "fireHoldGroups" not in by_group["0070 | SCUD"]
    assert by_group["0071 | SHAHED"]["fireHoldGroups"] == ["0071 | SHAHED"]
    assert by_group["0071 | SHAHED"]["fireHoldS"] == ["240"]


def test_no_mission_data_emits_no_fire_holds() -> None:
    scud = _tgo("missile", "0072 | SCUD", [_unit()], _Point(0.0, 0.0))
    sites = _sites(_game([scud]), mission_data=None)
    assert len(sites) == 1
    assert "fireHoldGroups" not in sites[0]


def test_coastal_opt_in_composes_with_the_missile_setting() -> None:
    scud = _tgo("missile", "0081 | SCUD", [_unit()], _Point(1.0, 2.0))
    silkworm = _tgo("coastal", "0082 | Silkworm", [_unit()], _Point(3.0, 4.0))
    # Both on -> both categories move.
    both = _sites(_game([scud, silkworm], on=True, coastal=True))
    assert {s["groups"][0] for s in both} == {"0081 | SCUD", "0082 | Silkworm"}
    # Only coastal on -> only the silkworm (the SCUD stays put).
    coastal_only = _sites(_game([scud, silkworm], on=False, coastal=True))
    assert [s["groups"][0] for s in coastal_only] == ["0082 | Silkworm"]


def test_fire_window_stays_inside_the_plugin_scoot_margin() -> None:
    """The generator's fire-task stop window must end before the plugin routes.

    The 2026-07-17 Scenic Route fly showed a dry, never-ending FireAtPoint pins
    its launchers in the deployed state (resetTask recovered only 2 of 9 fired
    batteries), so the generator now ends the task with a stop condition at
    hold + MISSILE_FIRE_WINDOW_S. The plugin's fireMarginS (Lua default and
    plugin.json default) must stay ABOVE that window, or the first route push
    lands while the fire task is still alive and the battery never scoots.
    """
    import json
    import re
    from pathlib import Path

    from game.missiongenerator.tgogenerator import MISSILE_FIRE_WINDOW_S

    plugin_dir = (
        Path(__file__).parent.parent.parent / "resources" / "plugins" / "mobilemissiles"
    )
    lua = (plugin_dir / "mobilemissiles-config.lua").read_text()
    match = re.search(r"^local FIRE_MARGIN = (\d+)", lua, re.M)
    assert match is not None, "plugin lost its FIRE_MARGIN default"
    assert MISSILE_FIRE_WINDOW_S < int(match.group(1))

    plugin_json = json.loads((plugin_dir / "plugin.json").read_text())
    margins = [
        o["defaultValue"]
        for o in plugin_json.get("specificOptions", [])
        if o.get("mnemonic") == "fireMarginS"
    ]
    assert margins, "plugin.json lost the fireMarginS option"
    assert MISSILE_FIRE_WINDOW_S < margins[0]
