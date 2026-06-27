"""Coverage for Loadout.uses_laser_code (gates the kneeboard Laser Code page).

An escort carrying air-to-air missiles has no use for a laser code; a DEAD/strike
flight with LGBs or a targeting pod does. The kneeboard prints the code only when
this returns True (see flightgroupconfigurator.configure_flight_member).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Optional

from game.ato.loadouts import Loadout
from game.data.weapons import WeaponType


def _weapon(weapon_type: WeaponType, accepts_code: bool) -> Any:
    return SimpleNamespace(
        weapon_group=SimpleNamespace(type=weapon_type),
        accepts_laser_code=lambda: accepts_code,
    )


def _loadout(*weapons: Optional[Any]) -> Loadout:
    loadout = Loadout.__new__(Loadout)
    loadout.pylons = {i: w for i, w in enumerate(weapons)}
    return loadout


def test_air_to_air_escort_has_no_use_for_a_laser_code() -> None:
    aam = _weapon(WeaponType.UNKNOWN, accepts_code=False)
    assert _loadout(aam, aam).uses_laser_code() is False


def test_harm_and_gps_jdam_loadouts_do_not_use_a_laser_code() -> None:
    arm = _weapon(WeaponType.ARM, accepts_code=False)
    jdam = _weapon(WeaponType.UNKNOWN, accepts_code=False)  # GPS-guided, no laser
    assert _loadout(arm).uses_laser_code() is False
    assert _loadout(jdam).uses_laser_code() is False


def test_laser_guided_bomb_uses_a_laser_code() -> None:
    # LGBs are matched by type: a few LGB stores (e.g. the AUF2 GBU-12 rack) carry no
    # `laser_code` setting yet are still laser-guided.
    lgb_no_setting = _weapon(WeaponType.LGB, accepts_code=False)
    assert _loadout(lgb_no_setting, None).uses_laser_code() is True


def test_laser_coded_store_without_lgb_type_uses_a_laser_code() -> None:
    # LJDAM / laser Maverick / APKWS rockets read as UNKNOWN type but expose a laser code.
    apkws = _weapon(WeaponType.UNKNOWN, accepts_code=True)
    assert _loadout(apkws).uses_laser_code() is True


def test_targeting_pod_alone_uses_a_laser_code() -> None:
    # A pod has no `laser_code` setting itself, but a flight carrying one designates
    # (own or buddy lase), so the code is worth printing.
    tgp = _weapon(WeaponType.TGP, accepts_code=False)
    assert _loadout(tgp).uses_laser_code() is True
    # Even alongside AAMs (a sweep/escort that can still buddy-lase).
    aam = _weapon(WeaponType.UNKNOWN, accepts_code=False)
    assert _loadout(tgp, aam).uses_laser_code() is True


def test_empty_loadout_has_no_use_for_a_laser_code() -> None:
    assert Loadout.empty_loadout().uses_laser_code() is False
