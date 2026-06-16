"""FlightControl airbase-list emission (Python side).

``_flightcontrol_airbase_entries`` selects blue-held land airdromes and attaches
their ATC frequency when runway data is available. Tested directly with fakes so
no pydcs Mission or plugin-manager state is required.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from dcs.task import Modulation

from game.missiongenerator.luagenerator import LuaGenerator


def _cp(name: str, *, airport: bool, blue: bool) -> Any:
    return SimpleNamespace(
        name=name,
        dcs_airport=object() if airport else None,
        captured=SimpleNamespace(is_blue=blue),
    )


def _runway(name: str, mhz: float, modulation: Modulation) -> Any:
    return SimpleNamespace(
        airfield_name=name,
        atc=SimpleNamespace(mhz=mhz, modulation=modulation),
    )


def _generator(controlpoints: list[Any], runways: list[Any]) -> LuaGenerator:
    game = cast(
        Any, SimpleNamespace(theater=SimpleNamespace(controlpoints=controlpoints))
    )
    mission_data = cast(Any, SimpleNamespace(runways=runways))
    return LuaGenerator(game, cast(Any, None), mission_data)


def test_entries_include_only_blue_airdromes() -> None:
    cps = [
        _cp("Incirlik", airport=True, blue=True),
        _cp("Damascus", airport=True, blue=False),  # enemy-held: excluded
        _cp("Carrier Strike Group", airport=False, blue=True),  # not an airdrome
    ]
    entries = _generator(cps, [])._flightcontrol_airbase_entries()
    assert len(entries) == 1
    assert 'name = "Incirlik"' in entries[0]
    # No runway data supplied, so no frequency is attached.
    assert "freq" not in entries[0]


def test_entry_attaches_atc_frequency_and_modulation() -> None:
    cps = [_cp("Incirlik", airport=True, blue=True)]
    runways = [_runway("Incirlik", 251.0, Modulation.AM)]
    entries = _generator(cps, runways)._flightcontrol_airbase_entries()
    assert len(entries) == 1
    assert 'name = "Incirlik"' in entries[0]
    assert "freq = 251.0" in entries[0]
    assert f"modulation = {Modulation.AM.value}" in entries[0]
