"""Tests for external-fuel-tank accounting.

The route-aware tank *planning* these helpers used to serve (feature §46) was
reverted 2026-08-09 with the auto-planner re-convergence to upstream. What
survives only reports the tanks a loadout already carries, for the kneeboard fuel
ladder and the Payload-tab readout, so the contract is narrow: recognise a real
drop tank, never mistake another store for one, and total the bags correctly.

Pinned against the real F/A-18C and F-16C pylon tables rather than fixtures --
the detector matches DCS display names, so it is only meaningful against them.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pytest

from game import persistency
from game.ato.loadouts import Loadout
from game.data.weapons import Pylon, Weapon
from game.dcs.aircrafttype import AircraftType
from game.fourteenth.range_fuel import (
    external_fuel_lbs,
    is_fuel_tank,
    tank_capacity_lbs,
)

HORNET_NAME = "F/A-18C Hornet (Lot 20)"
VIPER_NAME = "F-16CM Fighting Falcon (Block 50)"

# Real F-16C stores: 370 gal bags on the wet wing stations, ALQ-184 on the
# centerline, HARMs outboard.
VIPER_TANK_370 = "{F376DBEE-4CAE-41BA-ADD9-B2910AC95DEC}"
VIPER_ALQ_184 = "ALQ_184"
VIPER_HARM = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}"


@pytest.fixture(autouse=True)
def _persistency(tmp_path: Path) -> None:
    # AircraftType.named() / Pylon.for_aircraft load the unit data + weapon DB.
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16885)


def _hornet() -> AircraftType:
    return AircraftType.named(HORNET_NAME)


def _tank_capable_stations(aircraft: AircraftType) -> dict[int, Weapon]:
    """Real tank-capable stations on the airframe -> a compatible tank weapon."""
    stations: dict[int, Weapon] = {}
    for number in aircraft.dcs_unit_type.pylons:
        pylon = Pylon.for_aircraft(aircraft, number)
        tanks = [w for w in pylon.allowed if is_fuel_tank(w.clsid)]
        if tanks:
            stations[number] = tanks[0]
    return stations


def _non_tank_store(aircraft: AircraftType) -> tuple[int, Weapon]:
    """A (station, weapon) for a real non-tank store, to prove it is not counted."""
    for number in sorted(aircraft.dcs_unit_type.pylons):
        pylon = Pylon.for_aircraft(aircraft, number)
        for weapon in pylon.allowed:
            if not is_fuel_tank(weapon.clsid) and weapon.clsid != "<CLEAN>":
                return number, weapon
    raise AssertionError("no non-tank store found for the airframe")


def _viper_sead_loadout() -> Loadout:
    """Two 370 gal wing bags, a centerline ALQ-184, HARMs outboard."""
    viper = AircraftType.named(VIPER_NAME)
    clsids = {4: VIPER_TANK_370, 6: VIPER_TANK_370, 5: VIPER_ALQ_184, 3: VIPER_HARM}
    pylons: dict[int, Optional[Weapon]] = {}
    for station, clsid in clsids.items():
        weapon = Weapon.with_clsid(clsid)
        assert weapon is not None, f"{clsid} missing from the weapon DB"
        assert Pylon.for_aircraft(viper, station).can_equip(
            weapon
        ), f"station {station} cannot carry {clsid}"
        pylons[station] = weapon
    return Loadout("SEAD", pylons, date=None)


def test_tank_detection_and_capacity() -> None:
    hornet = _hornet()
    # A real Hornet tank round-trips through the detector...
    tank = next(iter(_tank_capable_stations(hornet).values()))
    assert is_fuel_tank(tank.clsid)
    assert tank_capacity_lbs(tank.clsid) > 500  # a real tank, not the tiny default
    # ...and a non-tank store does not.
    _, store = _non_tank_store(hornet)
    assert not is_fuel_tank(store.clsid)


def test_external_fuel_counts_the_bags() -> None:
    loadout = _viper_sead_loadout()
    # Two 370 gal bags at ~6.7 lb/gal. The ALQ-184 and the HARM contribute nothing.
    assert external_fuel_lbs(loadout) == pytest.approx(2 * 370 * 6.7, rel=0.01)


def test_external_fuel_is_zero_without_tanks() -> None:
    viper = AircraftType.named(VIPER_NAME)
    harm = Weapon.with_clsid(VIPER_HARM)
    assert harm is not None
    assert Pylon.for_aircraft(viper, 3).can_equip(harm)
    assert external_fuel_lbs(Loadout("SEAD", {3: harm}, date=None)) == 0.0
