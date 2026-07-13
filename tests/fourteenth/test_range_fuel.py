"""Tests for the route-aware fuel-tank planning (feature §46).

Two contracts, one per half:

* The generation-time top-up (``top_up_for_route``) may only ADD tanks to empty,
  tank-capable stations, and must NEVER remove or replace an existing store (a
  TGP, ECM pod, or ordnance). Pinned against the real F/A-18C pylon tables.
* The plan-time fuel-first pass (``plan_sortie_fuel``) may additionally trade a
  JAMMER-typed pod for a tank, but ONLY when the extra bag strictly reduces the
  tanker-pass count (or no tanker exists and the sortie is short) -- and never
  anything else (ordnance/TGP/UNKNOWN stay untouchable; custom loadouts are
  skipped). Pinned against the real F-16C pylon tables -- the motivating Viper:
  two wing bags + a centerline ALQ-184 planned through two refuel passes.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Optional

import pytest

from game import persistency
from game.ato.loadouts import Loadout
from game.data.weapons import Pylon, Weapon
from game.dcs.aircrafttype import AircraftType, FuelConsumption
from game.fourteenth.range_fuel import (
    _plan_loadout_fuel,
    add_range_fuel_tanks,
    external_fuel_lbs,
    is_fuel_tank,
    plan_sortie_fuel,
    route_length_nm,
    tank_capacity_lbs,
    top_up_for_route,
)

HORNET_NAME = "F/A-18C Hornet (Lot 20)"
VIPER_NAME = "F-16CM Fighting Falcon (Block 50)"
FAR_ROUTE_NM = 1500.0  # well beyond any Hornet internal+tank endurance -> triggers
SHORT_ROUTE_NM = 40.0  # covered on internal fuel alone -> never triggers

# The real F-16C stations of the motivating case: 370 gal bags on the wet wing
# stations, the ALQ-184 on the (tank-capable) centerline, HARMs outboard.
VIPER_TANK_370 = "{F376DBEE-4CAE-41BA-ADD9-B2910AC95DEC}"
VIPER_ALQ_184 = "ALQ_184"
VIPER_HARM = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}"


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


# --- The plan-time fuel-first pass (tier 2: the jammer-pod trade) -------------------


def _viper() -> AircraftType:
    return AircraftType.named(VIPER_NAME)


def _weapon(clsid: str) -> Weapon:
    weapon = Weapon.with_clsid(clsid)
    assert weapon is not None, f"weapon DB is missing {clsid}"
    return weapon


def _viper_sead_loadout() -> Loadout:
    """The motivating loadout: 370 gal bags on 4/6, ALQ-184 on 5, HARMs on 3/7."""
    return Loadout(
        "Retribution SEAD",
        {
            3: _weapon(VIPER_HARM),
            4: _weapon(VIPER_TANK_370),
            5: _weapon(VIPER_ALQ_184),
            6: _weapon(VIPER_TANK_370),
            7: _weapon(VIPER_HARM),
        },
        date=None,
    )


def _plan(
    loadout: Loadout,
    *,
    fuel_to_end_of_vul: float,
    fuel_vul_to_home: float,
    tanker_available: bool = True,
    allow_displacement: bool = True,
) -> bool:
    viper = _viper()
    from game.utils import KG_TO_LBS

    return _plan_loadout_fuel(
        viper,
        loadout,
        internal=viper.max_fuel * KG_TO_LBS,
        taxi=0.0,
        reserve=0.0,
        fuel_to_end_of_vul=fuel_to_end_of_vul,
        fuel_vul_to_home=fuel_vul_to_home,
        tanker_available=tanker_available,
        allow_displacement=allow_displacement,
    )


def _viper_internal_lbs() -> float:
    from game.utils import KG_TO_LBS

    return _viper().max_fuel * KG_TO_LBS


def test_jammer_traded_for_a_tank_when_it_saves_a_pass() -> None:
    # Two bags: cannot reach the end of the vul AND a full top-off cannot cover
    # the sortie -> two passes. The third (centerline) bag lets the jet reach the
    # vul end and come home on one post-vul pass -> the ALQ-184 gives up its seat.
    internal = _viper_internal_lbs()
    loadout = _viper_sead_loadout()

    changed = _plan(
        loadout, fuel_to_end_of_vul=internal + 6000.0, fuel_vul_to_home=500.0
    )

    assert changed
    centerline = loadout.pylons[5]
    assert centerline is not None and is_fuel_tank(centerline.clsid)
    # The ordnance is untouchable: the HARMs are exactly where they were.
    assert loadout.pylons[3] is not None and loadout.pylons[3].clsid == VIPER_HARM
    assert loadout.pylons[7] is not None and loadout.pylons[7].clsid == VIPER_HARM


def test_jammer_kept_when_the_extra_bag_saves_no_pass() -> None:
    # A sortie so long that even every pod traded for a bag still needs two
    # passes: the trade buys nothing, so the pod stays.
    internal = _viper_internal_lbs()
    loadout = _viper_sead_loadout()

    _plan(loadout, fuel_to_end_of_vul=internal + 20000.0, fuel_vul_to_home=20000.0)

    centerline = loadout.pylons[5]
    assert centerline is not None and centerline.clsid == VIPER_ALQ_184


def test_jammer_kept_when_fuel_already_covers_the_sortie() -> None:
    loadout = _viper_sead_loadout()

    changed = _plan(loadout, fuel_to_end_of_vul=1000.0, fuel_vul_to_home=500.0)

    assert not changed
    centerline = loadout.pylons[5]
    assert centerline is not None and centerline.clsid == VIPER_ALQ_184


def test_jammer_kept_when_displacement_is_disabled() -> None:
    internal = _viper_internal_lbs()
    loadout = _viper_sead_loadout()

    _plan(
        loadout,
        fuel_to_end_of_vul=internal + 6000.0,
        fuel_vul_to_home=500.0,
        allow_displacement=False,
    )

    centerline = loadout.pylons[5]
    assert centerline is not None and centerline.clsid == VIPER_ALQ_184


def test_no_tanker_trades_the_jammer_whenever_short() -> None:
    # With no tanker in theater the bags are the only gas there is, so the trade
    # happens on a plain shortfall (no pass-count gate to consult).
    internal = _viper_internal_lbs()
    loadout = _viper_sead_loadout()

    _plan(
        loadout,
        fuel_to_end_of_vul=internal + 6000.0,
        fuel_vul_to_home=500.0,
        tanker_available=False,
    )

    centerline = loadout.pylons[5]
    assert centerline is not None and is_fuel_tank(centerline.clsid)


def test_plan_is_idempotent_across_rebuilds() -> None:
    internal = _viper_internal_lbs()
    loadout = _viper_sead_loadout()

    _plan(loadout, fuel_to_end_of_vul=internal + 6000.0, fuel_vul_to_home=500.0)
    first = dict(loadout.pylons)
    changed = _plan(
        loadout, fuel_to_end_of_vul=internal + 6000.0, fuel_vul_to_home=500.0
    )

    assert not changed
    assert loadout.pylons == first


def test_plan_sortie_fuel_mutates_shared_loadouts_once_and_skips_custom() -> None:
    internal = _viper_internal_lbs()
    shared = _viper_sead_loadout()
    custom = _viper_sead_loadout().derive_custom("Custom")
    members = [
        SimpleNamespace(loadout=shared),
        SimpleNamespace(loadout=shared),
        SimpleNamespace(loadout=custom),
    ]
    flight = SimpleNamespace(unit_type=_viper(), iter_members=lambda: iter(members))
    settings = SimpleNamespace(auto_range_fuel_tanks=True, fuel_tanks_over_jammers=True)
    fuel = FuelConsumption(taxi=0, climb=20.0, cruise=10.0, combat=16.0, min_safe=0)

    plan_sortie_fuel(
        flight,  # type: ignore[arg-type]
        fuel,
        internal + 6000.0,
        500.0,
        True,
        settings,  # type: ignore[arg-type]
    )

    # The shared loadout got the trade (and stayed the same, still-shared object).
    assert members[0].loadout is shared and members[1].loadout is shared
    centerline = shared.pylons[5]
    assert centerline is not None and is_fuel_tank(centerline.clsid)
    # The custom loadout is never touched.
    custom_centerline = custom.pylons[5]
    assert custom_centerline is not None and custom_centerline.clsid == VIPER_ALQ_184


def test_plan_sortie_fuel_respects_the_master_setting() -> None:
    internal = _viper_internal_lbs()
    loadout = _viper_sead_loadout()
    flight = SimpleNamespace(
        unit_type=_viper(),
        iter_members=lambda: iter([SimpleNamespace(loadout=loadout)]),
    )
    settings = SimpleNamespace(
        auto_range_fuel_tanks=False, fuel_tanks_over_jammers=True
    )
    fuel = FuelConsumption(taxi=0, climb=20.0, cruise=10.0, combat=16.0, min_safe=0)

    plan_sortie_fuel(
        flight,  # type: ignore[arg-type]
        fuel,
        internal + 6000.0,
        500.0,
        True,
        settings,  # type: ignore[arg-type]
    )

    centerline = loadout.pylons[5]
    assert centerline is not None and centerline.clsid == VIPER_ALQ_184


def test_external_fuel_counts_the_bags() -> None:
    loadout = _viper_sead_loadout()
    # Two 370 gal bags at ~6.7 lb/gal.
    assert external_fuel_lbs(loadout) == pytest.approx(2 * 370 * 6.7, rel=0.01)
