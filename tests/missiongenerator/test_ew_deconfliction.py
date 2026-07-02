"""Tests for the C-130J EW de-confliction (per-group deny-list).

The c130j EW/ISR plugin claims every C-130J-30 by airframe. A Combat SAR "King"
C-130J-30 must fly clean, but the previous fix skipped the whole plugin for the
mission -- which also stripped EW from a co-present JAMMING C-130J-30. Now the generator
emits a per-group deny-list (``dcsRetribution.EwExcludedGroups``) that the plugin honors,
so only the non-EW aircraft are skipped and the EW jet keeps its systems.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

from game import persistency
from game.ato.flighttype import FlightType
from game.dcs.aircrafttype import AircraftType
from game.missiongenerator.luagenerator import LuaGenerator


def _fd(group_name: str, flight_type: FlightType, aircraft_type: Any) -> Any:
    return SimpleNamespace(
        group_name=group_name, flight_type=flight_type, aircraft_type=aircraft_type
    )


def test_ew_excluded_groups_lists_only_non_ew_c130j_flights(tmp_path: Path) -> None:
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16883)
    c130j = AircraftType.named("C-130J-30")
    other = SimpleNamespace()  # any non-C-130J airframe (never == the C-130J type)
    flights = [
        _fd("KING-1", FlightType.COMBAT_SAR, c130j),  # excluded (King)
        _fd("JAM-1", FlightType.JAMMING, c130j),  # NOT excluded -- the EW jet itself
        _fd("KING-HELO", FlightType.COMBAT_SAR, other),  # NOT excluded -- not a C-130J
        _fd("STRIKE-1", FlightType.STRIKE, other),  # NOT excluded
    ]
    gen = LuaGenerator.__new__(LuaGenerator)
    gen.mission_data = SimpleNamespace(flights=flights)  # type: ignore[assignment]
    assert gen._ew_excluded_c130j_groups() == ["KING-1"]


def test_ew_excluded_groups_empty_when_no_non_ew_c130j(tmp_path: Path) -> None:
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16884)
    c130j = AircraftType.named("C-130J-30")
    gen = LuaGenerator.__new__(LuaGenerator)
    gen.mission_data = SimpleNamespace(  # type: ignore[assignment]
        flights=[_fd("JAM-1", FlightType.JAMMING, c130j)]
    )
    assert gen._ew_excluded_c130j_groups() == []


def test_c130j_plugin_honors_the_deny_list() -> None:
    script = Path("resources/plugins/c130j/c130j_mission_systems.lua").read_text(
        encoding="utf-8"
    )
    # Reads the generator-emitted deny-list into a lookup table.
    assert "dcsRetribution.EwExcludedGroups" in script
    assert "ewExcludedGroups" in script
    # isEligible rejects an excluded group (so the plugin no longer claims it).
    iseligible = script.split("local function isEligible(unit)", maxsplit=1)[1].split(
        "local function registerUnit", maxsplit=1
    )[0]
    assert "ewExcludedGroups[gname]" in iseligible
    assert "return false" in iseligible
