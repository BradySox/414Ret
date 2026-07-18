"""Expanded F-4E Weapons Pack restoration (feature §71).

The pack's ``inject_F4E``/``eject_F4E`` mutate the pydcs F-4E pylon tables
(process-global state, re-applied by ``Faction.apply_mod_settings`` at
generation and on save load). The loadout layer keys off that live state:
payload names ending in ``Loadout.EXPANDED_WEAPONS_SUFFIX`` are tried first
for their task but only picked while every store fits the current tables --
so the AGM-88 fits fly exactly when the mod is on, and the stock Shrike fits
are the automatic fallback when it is off (a store the unmodded pylon tables
can't mount would be silently stripped by DCS at spawn, i.e. a naked Weasel).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Iterator

import pytest
from dcs.payloads import PayloadDirectories
from dcs.planes import F_16C_50
from dcs.unittype import FlyingType

from game import persistency
from game.ato.flighttype import FlightType
from game.ato.loadouts import Loadout
from game.dcs.aircrafttype import AircraftType
from pydcs_extensions.f4e_expanded_weapons.f4e_expanded_weapons import (
    eject_F4E,
    inject_F4E,
)

PAYLOADS_DIR = Path(__file__).parent.parent.parent / "resources" / "customized_payloads"

PHANTOM = "F-4E-45MC Phantom II"
# The stock pydcs AGM-88C entry the pack injects onto stations 1/3/11/13 --
# note the ...C93 clsid, not the Hornet-rack ...C9C sibling.
HARM = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}"
SHRIKE_A = "{LAU_34_AGM_45A}"

SEAD_TASKS = [
    (FlightType.SEAD, {1, 3, 11, 13}),
    (FlightType.SEAD_ESCORT, {3, 11}),
    (FlightType.SEAD_SWEEP, {1, 3, 11, 13}),
]


@pytest.fixture(autouse=True)
def _persistency(tmp_path: Path) -> None:
    # AircraftType.named() / Pylon.for_aircraft load the unit data + weapon DB.
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16886)


@pytest.fixture(autouse=True)
def _payload_dirs() -> None:
    # Force a rescan against the repo's payload dir regardless of what earlier
    # tests (or a developer's Saved Games) left in the class-level cache.
    PayloadDirectories.set_fallback(PAYLOADS_DIR)
    FlyingType._payload_cache = None  # type: ignore[assignment]


@pytest.fixture(autouse=True)
def _pack_ejected() -> Iterator[None]:
    # The injection is process-global pydcs state; start and leave every test
    # in the no-mod baseline so ordering can never leak HARM stations around.
    eject_F4E()
    yield
    eject_F4E()


def _phantom() -> AircraftType:
    return AircraftType.named(PHANTOM)


def _stations_with(loadout: Loadout, clsid: str) -> set[int]:
    return {n for n, w in loadout.pylons.items() if w is not None and w.clsid == clsid}


@pytest.mark.parametrize("task,expected_stations", SEAD_TASKS, ids=lambda p: str(p))
def test_injected_pack_selects_the_harm_fit(
    task: FlightType, expected_stations: set[int]
) -> None:
    inject_F4E()
    loadout = Loadout.default_for_task_and_aircraft(task, _phantom().dcs_unit_type)
    assert loadout.name.endswith(Loadout.EXPANDED_WEAPONS_SUFFIX), loadout.name
    # Selection only returns an (XW) fit whose stores the injected tables accept,
    # so this doubles as the pylon-legality pin for the payload file.
    assert _stations_with(loadout, HARM) == expected_stations
    assert not _stations_with(loadout, SHRIKE_A)


def test_ejected_pack_falls_back_to_the_stock_shrike_fit() -> None:
    loadout = Loadout.default_for_task_and_aircraft(
        FlightType.SEAD, _phantom().dcs_unit_type
    )
    assert loadout.name == "Retribution SEAD"
    assert not _stations_with(loadout, HARM)
    assert _stations_with(loadout, SHRIKE_A) == {1, 13}


def test_editor_list_tracks_the_mod_state() -> None:
    aircraft = _phantom()
    names = {loadout.name for loadout in Loadout.iter_for_aircraft(aircraft)}
    assert not any(n.endswith(Loadout.EXPANDED_WEAPONS_SUFFIX) for n in names)
    assert "Retribution SEAD" in names  # the stock fits are always offered

    inject_F4E()
    names = {loadout.name for loadout in Loadout.iter_for_aircraft(aircraft)}
    assert "Retribution SEAD (XW)" in names
    assert "Retribution SEAD Escort (XW)" in names
    assert "Retribution SEAD Sweep (XW)" in names


def test_other_airframes_never_see_the_xw_chain() -> None:
    # The (XW) name is tried first for every task on every airframe; only the
    # F-4E ships such payloads, so everything else must resolve exactly as
    # before the suffix existed.
    loadout = Loadout.default_for_task_and_aircraft(FlightType.SEAD, F_16C_50)
    assert not loadout.name.endswith(Loadout.EXPANDED_WEAPONS_SUFFIX)
    assert loadout.pylons


def test_harm_fit_survives_the_1988_era_gate() -> None:
    # Red Tide (July 1988) preseeds restrict_weapons_by_date; the fork dates the
    # DCS AGM-88C at the family's 1984 IOC precisely so the era gate keeps it.
    # A future re-date to the C-model's real 1993 would silently strip every
    # HARM from the campaign this feature exists for -- this is the tripwire.
    inject_F4E()
    loadout = Loadout.default_for_task_and_aircraft(
        FlightType.SEAD, _phantom().dcs_unit_type
    )
    degraded = loadout.degrade_for_date(
        _phantom(), date(1988, 7, 13), SimpleNamespace()  # type: ignore[arg-type]
    )
    assert _stations_with(degraded, HARM) == {1, 3, 11, 13}
