"""Expanded F-4E Weapons Pack restoration (feature §71).

The pack's ``inject_F4E``/``eject_F4E`` mutate the pydcs F-4E pylon tables
(process-global state, re-applied by ``Faction.apply_mod_settings`` at
generation and on save load). The loadout layer keys off that live state:
payload names ending in ``Loadout.EXPANDED_WEAPONS_SUFFIX`` are tried first
for their task but only picked while every store fits the current tables --
so the mod fits fly exactly when the mod is on, and the stock Shrike fits
are the automatic fallback when it is off (a store the unmodded pylon tables
can't mount would be silently stripped by DCS at spawn, i.e. a naked Weasel).

Of the pack's ARMs the **AGM-78B Standard is the preferred one** (user call
2026-07-18): the auto-selected (XW) fits carry it, while the 4x AGM-88C load
stays supported as the editor-only "Retribution SEAD HARM (XW)" fit (same mod
gate, never in the task name chain).
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
# The pack's LAU-77 Standard ARM (mod clsid, resolved via the AGM-78B yaml).
STANDARD_B = "{LAU_77_AGM_78B}"
# The stock pydcs AGM-88C entry the pack injects alongside it -- note the
# ...C93 clsid, not the Hornet-rack ...C9C sibling.
HARM = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}"
SHRIKE_A = "{LAU_34_AGM_45A}"

RED_TIDE_DATE = date(1988, 7, 13)

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
    # in the no-mod baseline so ordering can never leak mod stations around.
    eject_F4E()
    yield
    eject_F4E()


def _phantom() -> AircraftType:
    return AircraftType.named(PHANTOM)


def _stations_with(loadout: Loadout, clsid: str) -> set[int]:
    return {n for n, w in loadout.pylons.items() if w is not None and w.clsid == clsid}


def _editor_loadout(name: str) -> Loadout:
    by_name = {l.name: l for l in Loadout.iter_for_aircraft(_phantom())}
    assert name in by_name, sorted(by_name)
    return by_name[name]


@pytest.mark.parametrize("task,expected_stations", SEAD_TASKS, ids=lambda p: str(p))
def test_injected_pack_prefers_the_standard_arm_fit(
    task: FlightType, expected_stations: set[int]
) -> None:
    inject_F4E()
    loadout = Loadout.default_for_task_and_aircraft(task, _phantom().dcs_unit_type)
    assert loadout.name.endswith(Loadout.EXPANDED_WEAPONS_SUFFIX), loadout.name
    # Selection only returns an (XW) fit whose stores the injected tables accept,
    # so this doubles as the pylon-legality pin for the payload file. The AGM-78B
    # is the preferred ARM; the HARM fit is editor-only.
    assert _stations_with(loadout, STANDARD_B) == expected_stations
    assert not _stations_with(loadout, HARM)
    assert not _stations_with(loadout, SHRIKE_A)


def test_ejected_pack_falls_back_to_the_stock_shrike_fit() -> None:
    loadout = Loadout.default_for_task_and_aircraft(
        FlightType.SEAD, _phantom().dcs_unit_type
    )
    assert loadout.name == "Retribution SEAD"
    assert not _stations_with(loadout, STANDARD_B)
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
    # The supported-but-not-preferred HARM load: offered in the editor under the
    # same mod gate, but absent from every task's name chain.
    assert "Retribution SEAD HARM (XW)" in names


def test_harm_fit_is_editor_only_and_carries_the_harms() -> None:
    inject_F4E()
    loadout = _editor_loadout("Retribution SEAD HARM (XW)")
    assert _stations_with(loadout, HARM) == {1, 3, 11, 13}
    assert not _stations_with(loadout, STANDARD_B)


def test_other_airframes_never_see_the_xw_chain() -> None:
    # The (XW) name is tried first for every task on every airframe; only the
    # F-4E ships such payloads, so everything else must resolve exactly as
    # before the suffix existed.
    loadout = Loadout.default_for_task_and_aircraft(FlightType.SEAD, F_16C_50)
    assert not loadout.name.endswith(Loadout.EXPANDED_WEAPONS_SUFFIX)
    assert loadout.pylons


def test_arm_fits_survive_the_1988_era_gate() -> None:
    # A personal Red Tide (July 1988) runs restrict_weapons_by_date; both ARMs
    # must clear it. The AGM-78B is dated at its 1969 service entry; the DCS
    # AGM-88C is deliberately dated at the family's 1984 IOC -- a future re-date
    # to the C-model's real 1993 would silently disarm the 1988 Weasel's HARM
    # fit, so both are tripwired here.
    inject_F4E()
    auto = Loadout.default_for_task_and_aircraft(
        FlightType.SEAD, _phantom().dcs_unit_type
    )
    degraded = auto.degrade_for_date(
        _phantom(), RED_TIDE_DATE, SimpleNamespace()  # type: ignore[arg-type]
    )
    assert _stations_with(degraded, STANDARD_B) == {1, 3, 11, 13}

    harm_fit = _editor_loadout("Retribution SEAD HARM (XW)")
    degraded = harm_fit.degrade_for_date(
        _phantom(), RED_TIDE_DATE, SimpleNamespace()  # type: ignore[arg-type]
    )
    assert _stations_with(degraded, HARM) == {1, 3, 11, 13}
