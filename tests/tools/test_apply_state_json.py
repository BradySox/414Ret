"""Unit tests for the tools/apply_state_json.py translation core.

The tool re-binds a flown mission's state.json to a regenerated campaign save
(the Red Tide "process turn 1 from the M1 session JSON" workflow). These tests
pin the pure name-parsing and the phased matching rules; the end-to-end path
(headless generation -> debrief -> pass_turn) is exercised by running the tool
itself.
"""

from __future__ import annotations

import math
from types import SimpleNamespace
from typing import Any

from tools.apply_state_json import (
    AircraftEntry,
    FrontLineEntry,
    StateTranslator,
    TargetPools,
    TgoEntry,
    front_line_side,
    parse_front_line_unit_name,
    parse_pilot_unit_name,
    parse_tic_clone_name,
)

SIDES = {0: "red", 80: "blue"}


class FakePoint:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def distance_to_point(self, other: "FakePoint") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)


def source_unit(name: str, x: float = 0.0, y: float = 0.0) -> Any:
    return SimpleNamespace(name=name, position=FakePoint(x, y))


def make_translator(
    source_units: dict[str, Any], pools: TargetPools
) -> StateTranslator:
    return StateTranslator(source_units, pools, SIDES)


def test_parse_pilot_unit_name() -> None:
    assert parse_pilot_unit_name("Haina BARCAP|0|45|MiG-29A Fulcrum-A| Pilot #2") == (
        "Haina BARCAP",
        "MiG-29A Fulcrum-A",
    )
    # Front-line, intercept-template, and TGO names are not aircraft.
    assert parse_pilot_unit_name("unit|0|8|PT-76| Unit #2") is None
    assert parse_pilot_unit_name("Intercept|Haina|abc123 Pilot #1") is None
    assert parse_pilot_unit_name("0373 | AAA Fire Can SON-9") is None


def test_parse_front_line_unit_name() -> None:
    assert parse_front_line_unit_name("unit|0|8|PT-76| Unit #2") == "PT-76"
    assert parse_front_line_unit_name("TIC:unit|80|5|M113| Unit #4") == "M113"
    # TIC infantry sub-groups keep the composite name; the killed unit's type
    # is the token right before the " Unit #N" tail.
    assert (
        parse_front_line_unit_name(
            "TIC:unit|80|4|M2A2 Bradley|#infantry|80|1|Infantry M4| Unit #1"
        )
        == "Infantry M4"
    )
    assert parse_front_line_unit_name("Haina BARCAP|0|45|MiG| Pilot #1") is None


def test_parse_tic_clone_name() -> None:
    # A respawned vehicle clone.
    assert parse_tic_clone_name("TIC:unit|80|5|M113|-10#001-01") == "M113"
    # A dismounted-infantry clone (the -N#NNN segment can repeat).
    assert (
        parse_tic_clone_name(
            "TIC:unit|0|9|BMP-1|#infantry|0|16|Mortar 2B11 120mm|-29#001-01"
        )
        == "Mortar 2B11 120mm"
    )
    # QRA clones share the -NN suffix shape but are not front-line groups.
    assert parse_tic_clone_name("Intercept|Haina|5c3c#001-01") is None


def test_front_line_side() -> None:
    assert front_line_side("unit|0|8|PT-76| Unit #2", SIDES) == "red"
    assert front_line_side("unit|80|5|M113| Unit #1", SIDES) == "blue"
    assert front_line_side("unit|99|5|M113| Unit #1", SIDES) is None


def test_tgo_matches_nearest_same_name_once() -> None:
    pools = TargetPools(
        tgos=[
            TgoEntry("0101 | SA-9 Strela", "SA-9 Strela", FakePoint(5000, 0)),
            TgoEntry("0102 | SA-9 Strela", "SA-9 Strela", FakePoint(100, 0)),
        ]
    )
    sources = {
        "0384 | SA-9 Strela": source_unit("SA-9 Strela"),
        "0385 | SA-9 Strela": source_unit("SA-9 Strela"),
    }
    translator = make_translator(sources, pools)
    out = translator.translate_events(
        {"dead_events": ["0384 | SA-9 Strela", "0385 | SA-9 Strela"]}
    )
    # Nearest first, and each target unit is consumed exactly once.
    assert out["dead_events"] == ["0102 | SA-9 Strela", "0101 | SA-9 Strela"]


def test_aircraft_exact_label_wins_over_earlier_type_match() -> None:
    pools = TargetPools(
        aircraft=[
            AircraftEntry(
                "TOAD BAI|0|1|Su-25 Frogfoot| Pilot #1",
                "TOAD BAI",
                "Su-25 Frogfoot",
                client=False,
            ),
            AircraftEntry(
                "SCARAB BAI|0|2|Su-25 Frogfoot| Pilot #1",
                "SCARAB BAI",
                "Su-25 Frogfoot",
                client=False,
            ),
        ]
    )
    translator = make_translator({}, pools)
    # The type-only kill comes FIRST in event order, but must not steal the
    # SCARAB entry that the second kill matches exactly.
    out = translator.translate_events(
        {
            "kill_events": [
                "WRASSE BAI|0|9|Su-25 Frogfoot| Pilot #1",
                "SCARAB BAI|0|9|Su-25 Frogfoot| Pilot #2",
            ]
        }
    )
    assert out["kill_events"] == [
        "TOAD BAI|0|1|Su-25 Frogfoot| Pilot #1",
        "SCARAB BAI|0|2|Su-25 Frogfoot| Pilot #1",
    ]


def test_front_line_exact_token_wins_over_earlier_side_fallback() -> None:
    pools = TargetPools(
        front_line=[
            FrontLineEntry("TIC:unit|0|13|APC BTR-70| Unit #1", "APC BTR-70", "red"),
            FrontLineEntry("TIC:unit|0|9|T-55A| Unit #1", "T-55A", "red"),
        ]
    )
    translator = make_translator({}, pools)
    # The infantry kill (no exact token in the pool) is listed first, but the
    # BTR-70 kill must still claim the exact BTR-70 entry; the infantry kill
    # side-falls back onto the remaining red unit.
    out = translator.translate_events(
        {
            "dead_events": [
                "TIC:unit|0|11|APC BTR-70|#infantry|0|21|Infantry AK-74 Rus|-4#001-01",
                "TIC:unit|0|11|APC BTR-70|-3#001-01",
            ]
        }
    )
    assert out["dead_events"] == [
        "TIC:unit|0|9|T-55A| Unit #1",
        "TIC:unit|0|13|APC BTR-70| Unit #1",
    ]
    assert translator.report.front_side_fallback
    assert translator.report.front_mapped


def test_front_line_overflow_drops() -> None:
    pools = TargetPools(
        front_line=[
            FrontLineEntry("unit|0|8|PT-76| Unit #1", "PT-76", "red"),
        ]
    )
    translator = make_translator({}, pools)
    out = translator.translate_events(
        {"dead_events": ["unit|0|8|PT-76| Unit #2", "unit|0|9|PT-76| Unit #1"]}
    )
    # One maps; the overflow kill keeps its (non-colliding) name and is
    # reported dropped -- you cannot kill more units than the front fields.
    assert out["dead_events"][0] == "unit|0|8|PT-76| Unit #1"
    assert len(translator.report.front_unmapped) == 1


def test_collision_guard_prefixes_unresolvable_known_name() -> None:
    pools = TargetPools(known_names={"unit|0|8|PT-76| Unit #2"})
    translator = make_translator({}, pools)
    out = translator.translate_events({"dead_events": ["unit|0|8|PT-76| Unit #2"]})
    # No pool entry to map onto, but the raw name exists in the target game --
    # passing it through would kill an unrelated unit by coincidence.
    assert out["dead_events"] == ["UNMAPPED|unit|0|8|PT-76| Unit #2"]
    assert translator.report.collision_guarded


def test_numeric_and_unknown_names_pass_through() -> None:
    translator = make_translator({}, TargetPools())
    out = translator.translate_events(
        {"dead_events": [367641190, "CIV_Yak-52_9 Pilot #1", "Haina"]}
    )
    assert out["dead_events"] == [367641190, "CIV_Yak-52_9 Pilot #1", "Haina"]
    assert translator.report.numeric_events == 1
