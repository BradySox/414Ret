"""Auto-fielding the JTAC drone squadron (game.fourteenth.jtac_drone).

Locks the qualification gate (blue + setting + has_jtac + a TARPS-capable drone +
no existing drone squadron) and the rear-most-airfield pick, monkeypatching the heavy
``Squadron.create_from`` so no real game fixture is needed.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Optional, cast

import game.fourteenth.jtac_drone as jd
from game.ato.flighttype import FlightType
from game.theater import Player

REAPER = "MQ-9 Reaper"


class _AC:
    def __init__(self, uid: str, tarps: bool = True) -> None:
        self.dcs_unit_type = SimpleNamespace(id=uid)
        self.variant_id = uid
        self._tarps = tarps

    def capable_of(self, task: FlightType) -> bool:
        return task is FlightType.TARPS and self._tarps


class _Pos:
    def __init__(self, x: float) -> None:
        self.x = x

    def distance_to_point(self, other: "_Pos") -> float:
        return abs(self.x - other.x)


class _CP:
    def __init__(
        self,
        name: str,
        captured: Player,
        x: float,
        *,
        fleet: bool = False,
        op: bool = True,
    ) -> None:
        self.name = name
        self._captured = captured
        self.position = _Pos(x)
        self.is_fleet = fleet
        self._op = op

    @property
    def captured(self) -> Player:
        return self._captured

    def can_operate(self, aircraft: Any) -> bool:
        return self._op


def _coalition(
    *,
    blue: bool = True,
    setting: bool = True,
    has_jtac: bool = True,
    jtac_unit: Optional[_AC] = None,
    existing_drone: bool = False,
    cps: Optional[list[_CP]] = None,
) -> Any:
    if jtac_unit is None:
        jtac_unit = _AC(REAPER)
    if cps is None:
        cps = [
            _CP("Front", Player.BLUE, 10.0),
            _CP("Rear", Player.BLUE, 100.0),
            _CP("Enemy", Player.RED, 0.0),
        ]
    existing = [SimpleNamespace(aircraft=_AC(REAPER))] if existing_drone else []
    return SimpleNamespace(
        player=Player.BLUE if blue else Player.RED,
        opponent=SimpleNamespace(player=Player.RED if blue else Player.BLUE),
        game=SimpleNamespace(
            settings=SimpleNamespace(auto_jtac_drone=setting),
            theater=SimpleNamespace(controlpoints=cps),
        ),
        faction=SimpleNamespace(
            has_jtac=has_jtac, jtac_unit=jtac_unit, name="Testland"
        ),
        air_wing=SimpleNamespace(
            iter_squadrons=lambda: iter(existing),
            squadron_def_generator=SimpleNamespace(
                generate_for_aircraft=lambda ac: SimpleNamespace(aircraft=ac)
            ),
            add_squadron=lambda s: added.append(s),
        ),
    )


added: list[Any] = []
created: list[tuple[Any, ...]] = []


def _patch(monkeypatch: Any) -> None:
    added.clear()
    created.clear()

    def _create_from(
        squadron_def: Any, task: Any, size: int, base: Any, coal: Any, game: Any
    ) -> Any:
        created.append((squadron_def, task, size, base))
        return SimpleNamespace(aircraft=squadron_def.aircraft, base=base, primary=task)

    monkeypatch.setattr(jd.Squadron, "create_from", _create_from)


def test_auto_fields_at_the_rear_airfield(monkeypatch: Any) -> None:
    _patch(monkeypatch)
    jd.ensure_jtac_drone_squadron(cast(Any, _coalition()))
    assert len(added) == 1
    squadron_def, task, size, base = created[0]
    assert task is FlightType.TARPS
    assert size == jd.JTAC_DRONE_SQUADRON_SIZE
    assert base.name == "Rear"  # farthest from the enemy base, not "Front"


def test_skips_when_the_setting_is_off(monkeypatch: Any) -> None:
    _patch(monkeypatch)
    jd.ensure_jtac_drone_squadron(cast(Any, _coalition(setting=False)))
    assert added == []


def test_skips_the_red_side(monkeypatch: Any) -> None:
    _patch(monkeypatch)
    jd.ensure_jtac_drone_squadron(cast(Any, _coalition(blue=False)))
    assert added == []


def test_skips_a_crewed_fac_jtac(monkeypatch: Any) -> None:
    # OV-10/Yak-52/etc. are not in UAV_DCS_IDS -- not auto-fielded here.
    _patch(monkeypatch)
    jd.ensure_jtac_drone_squadron(cast(Any, _coalition(jtac_unit=_AC("OV-10A"))))
    assert added == []


def test_skips_a_non_tarps_drone(monkeypatch: Any) -> None:
    _patch(monkeypatch)
    jd.ensure_jtac_drone_squadron(
        cast(Any, _coalition(jtac_unit=_AC(REAPER, tarps=False)))
    )
    assert added == []


def test_skips_when_a_drone_squadron_already_exists(monkeypatch: Any) -> None:
    # A campaign that hand-places its drones (e.g. Inherent Resolve) is left untouched.
    _patch(monkeypatch)
    jd.ensure_jtac_drone_squadron(cast(Any, _coalition(existing_drone=True)))
    assert added == []


def test_skips_when_no_blue_airfield_can_operate_the_drone(monkeypatch: Any) -> None:
    _patch(monkeypatch)
    cps = [_CP("Front", Player.BLUE, 10.0, op=False), _CP("Enemy", Player.RED, 0.0)]
    jd.ensure_jtac_drone_squadron(cast(Any, _coalition(cps=cps)))
    assert added == []


def test_skips_when_faction_has_no_jtac(monkeypatch: Any) -> None:
    _patch(monkeypatch)
    jd.ensure_jtac_drone_squadron(cast(Any, _coalition(has_jtac=False)))
    assert added == []
