"""§54 M2 -- the loadout stock gate (Loadout.degrade_for_stock).

The authoritative half of "the airfield can't stock it". Pinned against the real
F/A-18C pylon tables: an out-of-stock scarce store is swapped to a non-scarce
fallback (or dropped), an in-stock one is untouched, a non-scarce store is never
touched, and an unseeded (empty) munitions map is a no-op.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from game import persistency
from game.ato.loadouts import Loadout
from game.data.weapons import Pylon, Weapon
from game.dcs.aircrafttype import AircraftType
from game.factions.faction import Faction
from game.factions.factionloader import FactionLoader

HORNET_NAME = "F/A-18C Hornet (Lot 20)"
FUTURE = date(2030, 1, 1)  # everything is date-available, so date never confounds


@pytest.fixture(autouse=True)
def _persistency(tmp_path: Path) -> None:
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16886)


def _hornet() -> AircraftType:
    return AircraftType.named(HORNET_NAME)


def _faction() -> Faction:
    return FactionLoader()["USA 2005"]


def _scarce_store(aircraft: AircraftType) -> tuple[int, Weapon]:
    for number in sorted(aircraft.dcs_unit_type.pylons):
        pylon = Pylon.for_aircraft(aircraft, number)
        for weapon in pylon.allowed:
            if weapon.weapon_group.scarce_family is not None:
                return number, weapon
    raise AssertionError("no scarce store on the airframe")


def _non_scarce_store(aircraft: AircraftType) -> tuple[int, Weapon]:
    for number in sorted(aircraft.dcs_unit_type.pylons):
        pylon = Pylon.for_aircraft(aircraft, number)
        for weapon in pylon.allowed:
            if weapon.clsid != "<CLEAN>" and weapon.weapon_group.scarce_family is None:
                return number, weapon
    raise AssertionError("no non-scarce store on the airframe")


def _loadout(station: int, weapon: Weapon) -> Loadout:
    return Loadout("test", {station: weapon}, FUTURE, False, pylon_settings={})


def test_empty_munitions_is_a_noop() -> None:
    # Unseeded (empty map) -> returns self, so pre-seed turns aren't falsely starved.
    hornet = _hornet()
    station, scarce = _scarce_store(hornet)
    loadout = _loadout(station, scarce)
    assert loadout.degrade_for_stock({}, hornet, FUTURE, _faction()) is loadout


def test_in_stock_scarce_store_is_kept() -> None:
    hornet = _hornet()
    station, scarce = _scarce_store(hornet)
    family = scarce.weapon_group.scarce_family
    assert family is not None
    result = _loadout(station, scarce).degrade_for_stock(
        {family: 5}, hornet, FUTURE, _faction()
    )
    assert result.pylons[station] == scarce


def test_out_of_stock_scarce_store_is_swapped_or_dropped() -> None:
    hornet = _hornet()
    station, scarce = _scarce_store(hornet)
    family = scarce.weapon_group.scarce_family
    assert family is not None
    result = _loadout(station, scarce).degrade_for_stock(
        {family: 0}, hornet, FUTURE, _faction()
    )
    replacement = result.pylons.get(station)
    assert replacement != scarce  # the depleted store is gone
    # ...and any fallback chosen is itself non-scarce (nothing is stocked here).
    assert replacement is None or replacement.weapon_group.scarce_family is None


def test_non_scarce_store_is_never_touched() -> None:
    hornet = _hornet()
    station, plain = _non_scarce_store(hornet)
    # Even with the whole economy "out of stock", a non-scarce store stays.
    result = _loadout(station, plain).degrade_for_stock(
        {"pgm_bomb": 0, "arm": 0}, hornet, FUTURE, _faction()
    )
    assert result.pylons[station] == plain
