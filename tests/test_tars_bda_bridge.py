"""TARS recon -> BDA fog-of-war bridge (Python side).

The Lua plugin appends photographed enemy unit names into the state file global
``tars_recon_captures``; ``StateData`` parses them and
``MissionResultsProcessor.tars_reconned_tgos`` resolves them to the TGOs whose
confirmed status should be snapped to truth. These cover both halves without a
running DCS mission.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from game.debriefing import StateData
from game.sim.missionresultsprocessor import MissionResultsProcessor


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


def test_tars_reconned_tgos_resolves_captures_to_tgos() -> None:
    tgo_a = object()
    tgo_b = object()

    def theater_units(name: str) -> Any:
        mapping = {
            "unit_a": SimpleNamespace(
                theater_unit=SimpleNamespace(ground_object=tgo_a)
            ),
            "unit_b": SimpleNamespace(
                theater_unit=SimpleNamespace(ground_object=tgo_b)
            ),
        }
        return mapping.get(name)

    debriefing = cast(
        Any,
        SimpleNamespace(
            state_data=SimpleNamespace(
                tars_recon_captures=["unit_a", "unit_b", "never_mapped"]
            ),
            unit_map=SimpleNamespace(theater_units=theater_units),
        ),
    )

    reconned = MissionResultsProcessor.tars_reconned_tgos(debriefing)
    # Both mapped captures resolve to their TGO; the unmapped name is ignored.
    assert reconned == {tgo_a, tgo_b}
