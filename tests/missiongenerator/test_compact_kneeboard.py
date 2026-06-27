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
    KneeboardGenerator,
    StrikeTaskPage,
    ThreatCard,
    ThreatIntelBriefPage,
)
from game.settings.settings import TargetIntelPrecision


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
    def wp(name: str, wtype: FlightWaypointType) -> Any:
        latlng = SimpleNamespace(
            format_dms=lambda include_decimal_seconds=False: "N 35 12 30 E 36 48 10"
        )
        return SimpleNamespace(
            display_name=name,
            waypoint_type=wtype,
            position=SimpleNamespace(latlng=lambda: latlng),
        )

    return SimpleNamespace(
        callsign="Hammer 1",
        custom_name=None,
        flight_type=FlightType.STRIKE,
        units=[SimpleNamespace(unit_type=object())],
        waypoints=[
            wp("INGRESS", FlightWaypointType.NAV),
            wp("Bunker", FlightWaypointType.TARGET_POINT),
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
