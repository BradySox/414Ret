"""Airbase-harassment emitter gates: the Vietnam siege vs the generic artillery mode.

The §36 runtime is shared; what differs is the gate and the reach. The Vietnam toggle
(``vietnam_airbase_harassment``) emits every occupied field within ~200 km of a front
(the theater-wide siege); the generic ``artillery_base_harassment`` reuses the same
emitter with real gun range (~35 km), so only a field genuinely on the FLOT -- a forward
FARP -- sits under fire. Player-spawn fields are excluded in both modes.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.missiongenerator.luagenerator import LuaData
from game.missiongenerator.vietnamopsluadata import populate_vietnam_ops_lua
from game.theater import ControlPointType


class _Point:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def distance_to_point(self, other: "_Point") -> float:
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5


class _CP:
    """Hashable fake (the exclusion walk collects CPs into a set)."""

    def __init__(self, name: str, pos: _Point, blue: bool = True) -> None:
        self.full_name = name
        self.position = pos
        self.cptype = ControlPointType.FARP
        self.captured = SimpleNamespace(is_blue=blue, is_red=not blue, is_neutral=False)


def _settings(*, vietnam: bool = False, artillery: bool = False) -> Any:
    return SimpleNamespace(
        vietnam_arc_light=False,
        vietnam_flak_gauntlet=False,
        vietnam_naval_gunfire=False,
        vietnam_airbase_harassment=vietnam,
        vietnam_super_gaggle=False,
        vietnam_fac_marking=False,
        vietnam_snake_and_nape=False,
        artillery_base_harassment=artillery,
    )


def _game(settings: Any, cps: list[_CP]) -> Any:
    front = SimpleNamespace(position=_Point(0.0, 0.0))
    return SimpleNamespace(
        settings=settings,
        theater=SimpleNamespace(controlpoints=cps, conflicts=lambda: [front]),
        coalitions=[],
    )


def _harassed_names(game: Any) -> list[str]:
    root = LuaData("dcsRetribution")
    populate_vietnam_ops_lua(root, game, mission_data=None)  # type: ignore[arg-type]
    vietnam = root.get_item("VietnamOps")
    if vietnam is None:
        return []
    harass = vietnam.get_item("airbaseHarassment")
    if harass is None:
        return []
    fields = harass.get_item("fields")
    assert isinstance(fields, LuaData)
    names: list[str] = []
    for obj in fields.objects:
        vals = obj.value
        assert isinstance(vals, list)
        name = next(v.value for v in vals if v.key == "name")
        assert isinstance(name, str)
        names.append(name)
    return names


_FARP_ON_THE_FLOT = _CP("Fulda", _Point(20_000.0, 0.0))
_REAR_FIELD = _CP("Ramstein", _Point(120_000.0, 0.0))


def test_artillery_mode_reaches_only_real_gun_range() -> None:
    game = _game(_settings(artillery=True), [_FARP_ON_THE_FLOT, _REAR_FIELD])
    # The FARP on the FLOT is shelled; the field 120 km back is out of gun range.
    assert _harassed_names(game) == ["Fulda"]


def test_vietnam_mode_keeps_the_theater_wide_siege_reach() -> None:
    game = _game(_settings(vietnam=True), [_FARP_ON_THE_FLOT, _REAR_FIELD])
    assert _harassed_names(game) == ["Fulda", "Ramstein"]


def test_both_modes_off_emits_nothing() -> None:
    game = _game(_settings(), [_FARP_ON_THE_FLOT])
    assert _harassed_names(game) == []
