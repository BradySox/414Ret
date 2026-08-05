"""The §85 GPS-jamming Lua bridge (dcsRetribution.gpsJamming).

Pins the emit contract the plugin reads: the node exists only when the feature is
on and a live site exists, and each record carries the owner, position, reach,
miss radius and the group names the runtime re-checks for liveness. The weapon
pattern list is emitted (not hardcoded in the Lua) so it has exactly one home.
"""

from __future__ import annotations

from typing import Any, Optional

from game.dcs.groundunittype import GpsJammingProperties
from game.fourteenth.gps_jamming import GPS_GUIDED_WEAPON_PATTERNS
from game.missiongenerator.gpsjammingluadata import populate_gps_jamming_lua
from game.missiongenerator.luagenerator import LuaData


class _Point:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y


class _UnitType:
    def __init__(self, jams: Optional[GpsJammingProperties]) -> None:
        self.gps_jamming = jams


class _Unit:
    def __init__(
        self, jams: Optional[GpsJammingProperties], alive: bool = True
    ) -> None:
        self.unit_type = _UnitType(jams)
        self.alive = alive


class _Group:
    def __init__(self, group_name: str, units: list[_Unit]) -> None:
        self.group_name = group_name
        self.units = units


class _Tgo:
    def __init__(self, name: str, groups: list[_Group], position: _Point) -> None:
        self.name = name
        self.groups = groups
        self.position = position

    def known_for(self, viewer: Any) -> bool:
        return True


class _Player:
    def __init__(self, is_blue: bool) -> None:
        self.is_blue = is_blue


class _ControlPoint:
    def __init__(self, captured: _Player, ground_objects: list[_Tgo]) -> None:
        self.captured = captured
        self.ground_objects = ground_objects


class _Theater:
    def __init__(self, controlpoints: list[_ControlPoint]) -> None:
        self.controlpoints = controlpoints


class _Settings:
    gps_jamming = True
    gps_jamming_default_reach_nm = 30.0
    gps_jamming_miss_radius_m = 200.0


class _Game:
    def __init__(self, theater: _Theater, settings: Any) -> None:
        self.theater = theater
        self.settings = settings


def _game(jams: bool = True, enabled: bool = True) -> _Game:
    props = GpsJammingProperties(radius_nm=45.0, miss_radius_m=350.0)
    tgo = _Tgo(
        "Haina jammer",
        [_Group("Haina jammer grp", [_Unit(props if jams else None)])],
        _Point(1000.0, -2000.0),
    )
    settings = _Settings()
    if not enabled:
        settings.gps_jamming = False
    return _Game(_Theater([_ControlPoint(_Player(False), [tgo])]), settings)


def _emit(game: _Game) -> str:
    root = LuaData("dcsRetribution")
    populate_gps_jamming_lua(root, game, None)  # type: ignore[arg-type]
    return root.serialize()


def test_a_live_site_is_emitted_with_everything_the_runtime_needs() -> None:
    lua = _emit(_game())
    assert "gpsJamming" in lua
    assert '"Haina jammer"' in lua
    assert 'coalition = "red"' in lua
    assert 'x = "1000.0"' in lua
    assert 'y = "-2000.0"' in lua
    # 45 nm / 350 m, from the unit definition rather than the campaign defaults.
    assert "83340" in lua  # 45 nm in metres
    assert 'missRadiusM = "350.0"' in lua
    assert '"Haina jammer grp"' in lua


def test_the_weapon_patterns_come_from_python() -> None:
    """One home for the curated list -- the Lua must never carry its own copy."""
    lua = _emit(_game())
    for pattern in GPS_GUIDED_WEAPON_PATTERNS:
        assert f'"{pattern}"' in lua


def test_the_feature_off_emits_no_node() -> None:
    assert "gpsJamming" not in _emit(_game(enabled=False))


def test_a_theater_with_no_jammer_emits_no_node() -> None:
    assert "gpsJamming" not in _emit(_game(jams=False))
