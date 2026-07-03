from __future__ import annotations

import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, List

from PIL import Image

from game.ato.codewords import MissionCodeWords
from game.ato.flighttype import FlightType
from game.ato.flightwaypointtype import FlightWaypointType
from game.missiongenerator.kneeboard import (
    CombatIntelPage,
    FuelLadderCard,
    KneeboardGenerator,
    KneeboardPageWriter,
    StrikeTaskPage,
    ThreatCard,
    ThreatIntelBriefPage,
)
from game.settings.settings import TargetIntelPrecision
from game.utils import NauticalUnits


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


def _strike_flight() -> Any:
    def wp(
        name: str,
        wtype: FlightWaypointType,
        min_fuel: float | None = None,
        fuel_planned: float | None = None,
    ) -> Any:
        latlng = SimpleNamespace(
            format_dms=lambda include_decimal_seconds=False: "N 35 12 30 E 36 48 10"
        )
        return SimpleNamespace(
            display_name=name,
            waypoint_type=wtype,
            position=SimpleNamespace(latlng=lambda: latlng),
            min_fuel=min_fuel,
            fuel_planned=fuel_planned,
        )

    return SimpleNamespace(
        callsign="Hammer 1",
        custom_name=None,
        flight_type=FlightType.STRIKE,
        task_display_name=FlightType.STRIKE.value,
        bingo_fuel=3500,
        joker_fuel=5000,
        aircraft_type=SimpleNamespace(
            utc_kneeboard=False, kneeboard_units=NauticalUnits()
        ),
        units=[SimpleNamespace(unit_type=object())],
        waypoints=[
            wp("INGRESS", FlightWaypointType.NAV, 3000, 9000),
            wp("Bunker", FlightWaypointType.TARGET_POINT, 3000, 7000),
        ],
        squadron=SimpleNamespace(
            coalition=SimpleNamespace(
                game=SimpleNamespace(
                    settings=SimpleNamespace(
                        target_intel_precision=TargetIntelPrecision.EXACT
                    )
                )
            )
        ),
    )


def test_combat_intel_page_fills_blank_space_with_fuel_ladder() -> None:
    # When the recon photo takes the flex slot, the dropped Fuel Ladder is handed to
    # the Threats & Targets page; with the threats all unidentified the page is roomy,
    # so the ladder draws to fill the otherwise-blank lower half.
    flight = _strike_flight()
    threat_page = ThreatIntelBriefPage(flight, [_unknown_card()], 1, False)
    page = CombatIntelPage(
        flight,
        threat_page,
        StrikeTaskPage(flight, False),
        False,
        fuel_card=FuelLadderCard(flight, False),
    )
    writer = KneeboardPageWriter()
    page.render_body(writer)
    assert "Fuel Ladder" in writer.get_text_string()


def test_combat_intel_page_drops_fuel_ladder_when_the_page_is_full() -> None:
    # With enough identified threat cards to fill the page, the low-priority fuel
    # section is dropped rather than spilled onto a continuation page.
    flight = _strike_flight()
    cards: List[ThreatCard] = [_live_card() for _ in range(10)]
    threat_page = ThreatIntelBriefPage(flight, cards, 0, False)
    page = CombatIntelPage(
        flight,
        threat_page,
        StrikeTaskPage(flight, False),
        False,
        fuel_card=FuelLadderCard(flight, False),
    )
    writer = KneeboardPageWriter()
    page.render_body(writer)
    assert "Fuel Ladder" not in writer.get_text_string()


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


def test_combat_intel_page_renders_target_over_threats_single_page(
    tmp_path: Path,
) -> None:
    # The compact deck's page 2 composes the target table with the threat cards on a
    # single 960x1080 image (no continuation page).
    flight = _strike_flight()
    cards: List[ThreatCard] = [_live_card(), _unknown_card()]
    threat_page = ThreatIntelBriefPage(flight, cards, 1, False)
    target_page = StrikeTaskPage(flight, False)
    page = CombatIntelPage(flight, threat_page, target_page, False)

    out = tmp_path / "p2.png"
    page.write(out)

    assert out.exists()
    with Image.open(out) as img:
        assert img.size == (960, 1080)
