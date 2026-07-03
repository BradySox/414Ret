"""Tests for the route-aware fuel-tank top-up (feature §46).

The safety contract is the important part: the top-up may only ADD tanks to
empty, tank-capable stations, and must NEVER remove or replace an existing store
(a TGP, ECM pod, or ordnance). These tests pin that against the real F/A-18C
pylon tables, plus the trigger/no-op guards.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Optional

import pytest

from game import persistency
from game.ato.loadouts import Loadout
from game.data.weapons import Pylon, Weapon
from game.dcs.aircrafttype import AircraftType
from game.fourteenth.range_fuel import (
    add_range_fuel_tanks,
    is_fuel_tank,
    route_length_nm,
    tank_capacity_lbs,
    top_up_for_route,
)

HORNET_NAME = "F/A-18C Hornet (Lot 20)"
FAR_ROUTE_NM = 1500.0  # well beyond any Hornet internal+tank endurance -> triggers
SHORT_ROUTE_NM = 40.0  # covered on internal fuel alone -> never triggers


@pytest.fixture(autouse=True)
def _persistency(tmp_path: Path) -> None:
    # AircraftType.named() / Pylon.for_aircraft load the unit data + weapon DB.
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16885)


def _hornet() -> AircraftType:
    return AircraftType.named(HORNET_NAME)


def _tank_count(loadout: Loadout) -> int:
    return sum(
        1 for w in loadout.pylons.values() if w is not None and is_fuel_tank(w.clsid)
    )


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
    """A (station, weapon) for a real non-tank store, to prove it is never touched."""
    for number in sorted(aircraft.dcs_unit_type.pylons):
        pylon = Pylon.for_aircraft(aircraft, number)
        for weapon in pylon.allowed:
            if not is_fuel_tank(weapon.clsid) and weapon.clsid != "<CLEAN>":
                return number, weapon
    raise AssertionError("no non-tank store found for the airframe")


def _occupy_all_tank_stations_but_one(
    hornet: AircraftType,
) -> tuple[dict[int, Optional[Weapon]], int]:
    """Loadout pylons with every tank station filled except the highest one."""
    tank_stations = _tank_capable_stations(hornet)
    assert len(tank_stations) >= 2, "test needs the Hornet to have >=2 tank stations"
    empty_station = sorted(tank_stations)[-1]
    pylons: dict[int, Optional[Weapon]] = {
        n: tank for n, tank in tank_stations.items() if n != empty_station
    }
    return pylons, empty_station


def test_far_route_fills_an_empty_tank_station() -> None:
    hornet = _hornet()
    pylons, empty_station = _occupy_all_tank_stations_but_one(hornet)
    # A non-tank store on a non-tank-capable station, to prove it is untouched.
    store_station, store = _non_tank_store(hornet)
    pylons.setdefault(store_station, store)

    loadout = Loadout("Retribution Strike", pylons, date=None)
    result = top_up_for_route(hornet, FAR_ROUTE_NM, loadout)

    # The empty tank station is now a tank, and the tank count strictly rose.
    filled = result.pylons.get(empty_station)
    assert filled is not None and is_fuel_tank(filled.clsid)
    assert _tank_count(result) > _tank_count(loadout)


def test_never_removes_or_replaces_an_existing_store() -> None:
    hornet = _hornet()
    pylons, _ = _occupy_all_tank_stations_but_one(hornet)
    store_station, store = _non_tank_store(hornet)
    pylons[store_station] = store

    loadout = Loadout("Retribution Strike", pylons, date=None)
    result = top_up_for_route(hornet, FAR_ROUTE_NM, loadout)

    # Every originally-occupied station keeps the exact same store.
    for number, weapon in loadout.pylons.items():
        assert weapon is not None
        kept = result.pylons.get(number)
        assert kept is not None and kept.clsid == weapon.clsid


def test_short_route_is_a_noop() -> None:
    hornet = _hornet()
    pylons, _ = _occupy_all_tank_stations_but_one(hornet)
    loadout = Loadout("Retribution Strike", pylons, date=None)

    result = top_up_for_route(hornet, SHORT_ROUTE_NM, loadout)

    assert result.pylons.keys() == loadout.pylons.keys()


def test_empty_loadout_is_untouched() -> None:
    hornet = _hornet()
    result = top_up_for_route(hornet, FAR_ROUTE_NM, Loadout.empty_loadout())
    assert not result.pylons


def test_hook_respects_the_setting_and_custom_loadouts() -> None:
    hornet = _hornet()
    pylons, _ = _occupy_all_tank_stations_but_one(hornet)

    flight = SimpleNamespace(
        unit_type=hornet, flight_plan=SimpleNamespace(waypoints=[])
    )

    # Setting OFF -> untouched even on a far route.
    off = SimpleNamespace(auto_range_fuel_tanks=False)
    base = Loadout("Retribution Strike", dict(pylons), date=None)
    result_off = add_range_fuel_tanks(flight, base, off)  # type: ignore[arg-type]
    assert result_off.pylons.keys() == base.pylons.keys()

    # Custom loadout -> untouched even with the setting ON.
    on = SimpleNamespace(auto_range_fuel_tanks=True)
    custom = Loadout("Custom", dict(pylons), date=None, is_custom=True)
    result_custom = add_range_fuel_tanks(flight, custom, on)  # type: ignore[arg-type]
    assert result_custom.pylons.keys() == custom.pylons.keys()


def test_tank_detection_and_capacity() -> None:
    hornet = _hornet()
    # A real Hornet tank round-trips through the detector...
    tank = next(iter(_tank_capable_stations(hornet).values()))
    assert is_fuel_tank(tank.clsid)
    assert tank_capacity_lbs(tank.clsid) > 500  # a real tank, not the tiny default
    # ...and a non-tank store does not.
    _, store = _non_tank_store(hornet)
    assert not is_fuel_tank(store.clsid)


def test_route_length_sums_legs() -> None:
    # Three waypoints, each leg 18520 m = 10 NM, so two legs -> 20 NM total.
    class Pos:
        def distance_to_point(self, other: object) -> float:
            return 18520.0

    waypoints = [SimpleNamespace(position=Pos()) for _ in range(3)]
    assert route_length_nm(waypoints) == pytest.approx(20.0, abs=0.1)  # type: ignore[arg-type]
