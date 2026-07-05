from __future__ import annotations

import datetime
from types import SimpleNamespace
from typing import Any

from game.ato.codewords import MissionCodeWords
from game.ato.flighttype import FlightType
from game.missiongenerator.kneeboard import (
    KneeboardGenerator,
    KneeboardPageWriter,
    ThreatCard,
)


def _generator(*, code_words_on: bool) -> KneeboardGenerator:
    mission = SimpleNamespace(start_time=SimpleNamespace(hour=12))
    coalition = SimpleNamespace(code_words=MissionCodeWords.generate())
    game = SimpleNamespace(
        settings=SimpleNamespace(
            generate_dark_kneeboard=False,
            enable_package_code_words=code_words_on,
        ),
        coalition_for=lambda friendly: coalition,
    )
    return KneeboardGenerator(mission, game)  # type: ignore[arg-type]


def _flight(flight_type: FlightType = FlightType.STRIKE) -> Any:
    return SimpleNamespace(
        flight_type=flight_type,
        task_display_name=flight_type.value,
        friendly=object(),
        aircraft_type=SimpleNamespace(utc_kneeboard=False),
        package=SimpleNamespace(
            target=SimpleNamespace(name="Bunker complex"),
            time_over_target=datetime.datetime(2026, 6, 26, 12, 34),
        ),
    )


def _live_card() -> ThreatCard:
    return ThreatCard(
        system="SA-6 Kub",
        band="MERAD",
        identified=True,
        guidance="Semi-active radar",
        ceiling="40,000 ft",
        mez_nm="20",
        detect_nm="28",
        harm="108",
        live=1,
        dead=0,
        cues=["061/28"],
        defeat="Stay low and pop",
        sort_range_m=38000.0,
    )


def _unknown_card() -> ThreatCard:
    return ThreatCard(
        system="Unidentified MERAD",
        band="MERAD",
        identified=False,
        guidance="—",
        ceiling="—",
        mez_nm="—",
        detect_nm="—",
        harm="—",
        live=1,
        dead=0,
        cues=["070/35"],
        defeat="",
        sort_range_m=0.0,
    )


def test_bluf_lines_carry_task_push_and_top_threat() -> None:
    gen = _generator(code_words_on=True)
    task, push, threat = gen._bluf_lines(_flight(), [_live_card()])

    assert task is not None and task.startswith("TASK")
    assert "Bunker complex" in task
    assert "TOT" in task

    assert push is not None
    assert "PUSH " in push
    assert "SUCCESS " in push and "ABORT " in push

    assert threat is not None
    assert "TOP THREAT" in threat
    assert "SA-6 Kub" in threat
    assert "MEZ 20 nm" in threat


def test_bluf_push_line_omitted_without_code_words() -> None:
    gen = _generator(code_words_on=False)
    _task, push, _threat = gen._bluf_lines(_flight(), [_live_card()])
    assert push is None


def test_bluf_top_threat_is_always_on_independent_of_brief_setting() -> None:
    # The top-threat line comes straight off the cards, so it is present whenever a
    # live, identified system exists -- even with the dedicated brief page disabled.
    gen = _generator(code_words_on=False)
    _task, _push, threat = gen._bluf_lines(_flight(), [_live_card()])
    assert threat is not None


def test_bluf_threat_line_none_when_only_unidentified() -> None:
    gen = _generator(code_words_on=False)
    _task, _push, threat = gen._bluf_lines(_flight(), [_unknown_card()])
    assert threat is None


def test_table_wraps_wide_columns_to_fit_the_page_width() -> None:
    # A package on three radio channels makes a very wide FREQ cell; the table must
    # wrap it rather than run off the right edge (losing the frequency).
    writer = KneeboardPageWriter()
    rows = [
        [
            "Raygun 6",
            "Refueling",
            "A-6E Tanker",
            "1",
            "COMM1 Ch 2 / COMM1 Ch 3 / COMM1 Ch 4\n232.000 MHz AM",
        ],
    ]
    writer.table(rows, headers=["Callsign", "Task", "Type", "#A/C", "FREQ"])
    content_px = writer.image_size[0] - writer.page_margin - writer.x
    lines = writer.get_text_string().splitlines()
    assert lines  # the table drew something
    for line in lines:
        assert writer.table_font.getlength(line) <= content_px + 1


def test_table_leaves_a_fitting_table_untouched() -> None:
    # A narrow table already fits, so the fitter returns None and output is unchanged.
    writer = KneeboardPageWriter()
    narrow = [["Colt 1", "CAP", "2"]]
    assert (
        writer._fit_col_widths(narrow, ["Callsign", "Task", "#A/C"], writer.table_font)
        is None
    )
