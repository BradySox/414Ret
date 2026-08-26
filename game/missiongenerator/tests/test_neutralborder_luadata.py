"""Emitter contract for dcsRetribution.neutralBorder (§96)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.missiongenerator.luagenerator import LuaData
from game.missiongenerator.neutralborderluadata import (
    NeutralBorderLuaZone,
    populate_neutral_border_lua,
)


def _zone(sam: bool = True) -> NeutralBorderLuaZone:
    return NeutralBorderLuaZone(
        country="Lebanon",
        airfield="Rayak",
        floor_blue_ft=None,
        floor_red_ft=None,
        fighter_template="NeutralBorder|Lebanon|MiG-29A",
        sam_template="NeutralBorder|Lebanon|SAM" if sam else None,
        red_country_id=34,
        blue_country_id=2,
        border=[(0.0, 0.0), (20000.0, 0.0), (20000.0, 20000.0), (0.0, 20000.0)],
    )


def _emit(enabled: bool, zones: list[Any]) -> str:
    root = LuaData("dcsRetribution")
    game = SimpleNamespace(settings=SimpleNamespace(neutral_border_defense=enabled))
    mission_data = SimpleNamespace(neutral_border_zones=zones)
    populate_neutral_border_lua(root, game, mission_data)  # type: ignore[arg-type]
    return root.create_operations_lua()


def test_emits_the_zone_with_templates_ids_and_border() -> None:
    lua = _emit(True, [_zone()])
    assert "neutralBorder" in lua
    assert "Lebanon" in lua
    assert "Rayak" in lua
    assert "NeutralBorder|Lebanon|MiG-29A" in lua
    assert "NeutralBorder|Lebanon|SAM" in lua
    # No floor emitted at all: this zone grants no safe altitude, and a
    # number in the payload would imply one exists.
    assert "floorBlueFt" not in lua
    assert "floorRedFt" not in lua
    assert "34" in lua and "2" in lua
    assert "20000.0" in lua  # border vertex, one decimal


def test_sam_key_is_absent_when_no_sam_template() -> None:
    lua = _emit(True, [_zone(sam=False)])
    assert "samTemplate" not in lua
    assert "fighterTemplate" in lua


def test_setting_off_emits_nothing() -> None:
    lua = _emit(False, [_zone()])
    assert "neutralBorder" not in lua


def test_no_zones_emits_nothing() -> None:
    lua = _emit(True, [])
    assert "neutralBorder" not in lua
