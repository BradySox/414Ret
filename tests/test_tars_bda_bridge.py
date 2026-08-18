"""TARS recon capture parsing (Python side).

The Lua plugin appends photographed enemy unit names into the state file global
``tars_recon_captures`` and ``StateData`` parses them. The captures no longer
drive the recon fog -- engaging a site is the only reveal (2026-08-18) -- so
this covers the parse contract only.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from game.debriefing import StateData


def _no_flight_unit_map() -> Any:
    # StateData.from_json only touches unit_map.flight() while classifying killed
    # units; recon-capture parsing does not need it.
    return cast(Any, SimpleNamespace(flight=lambda _: None))


def test_parse_capture_dicts_extracts_unit_names() -> None:
    state = StateData.from_json(
        {
            "tars_recon_captures": [
                {"unit": "SA-6 Battery 1 Unit #2", "life": 0, "type": "Kub 2P25 ln"},
                {"unit": "Comms Tower", "life": 80, "type": "tower"},
            ]
        },
        _no_flight_unit_map(),
    )
    assert state.tars_recon_captures == ["SA-6 Battery 1 Unit #2", "Comms Tower"]


def test_parse_accepts_empty_list_and_bare_strings() -> None:
    # Lua serializes an empty table as [], and we tolerate bare-string entries.
    assert StateData.from_json({}, _no_flight_unit_map()).tars_recon_captures == []
    assert (
        StateData.from_json(
            {"tars_recon_captures": []}, _no_flight_unit_map()
        ).tars_recon_captures
        == []
    )
    state = StateData.from_json(
        {"tars_recon_captures": ["Tank A", {"life": 50}, {"unit": ""}, 7]},
        _no_flight_unit_map(),
    )
    # "Tank A" kept; the dict without a usable "unit", the empty name, and the
    # stray int are all dropped.
    assert state.tars_recon_captures == ["Tank A"]
