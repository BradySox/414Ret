from __future__ import annotations

import datetime
from types import SimpleNamespace
from typing import Any

from game.ato.codewords import MissionCodeWords, PushCategory
from game.ato.flighttype import FlightType
from game.missiongenerator.commsjamluadata import JAM_BACKUP_COMM_NAME
from game.missiongenerator.kneeboard import (
    KneeboardGenerator,
    KneeboardPageWriter,
    ThreatCard,
    _brief_loadout,
    _brief_sam_threats,
)
from game.radio.radios import RadioFrequency


def _generator(*, code_words_on: bool) -> KneeboardGenerator:
    mission = SimpleNamespace(start_time=SimpleNamespace(hour=12))
    coalition = SimpleNamespace(
        code_words=MissionCodeWords.generate(),
        ato=SimpleNamespace(packages=[]),
    )
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
        units=[],
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


def test_bluf_lines_carry_task_threats_and_sar() -> None:
    gen = _generator(code_words_on=True)
    lines = gen._bluf_lines(_flight(), [_live_card()])

    task = lines[0]
    assert task.startswith("TASK")
    assert "Bunker complex" in task
    assert "TOT" in task

    push = next(line for line in lines if "PUSH " in line)
    assert "SUCCESS " in push and "ABORT " in push

    # The compact threat picture: an air-threat line (the fake coalition has no
    # opponent, so the loose fallback) + the condensed live SAM systems.
    air = next(line for line in lines if line.startswith("THREATS  AIR"))
    assert "CAP" in air
    sam = next(line for line in lines if "SAM " in line)
    assert "SA-6 Kub 20nm" in sam

    # The SAR if-down drill always closes the BLUF (no SAR assets on this fake).
    assert lines[-1].startswith("SAR")
    assert "squawk 7700" in lines[-1]


def test_bluf_has_no_top_threat_line() -> None:
    # The verbose TOP THREAT prose was dropped in the back-to-upstream rework;
    # the SAM picture is the condensed "system MEZnm" line instead.
    gen = _generator(code_words_on=False)
    lines = gen._bluf_lines(_flight(), [_live_card()])
    assert not any("TOP THREAT" in line for line in lines)


def test_bluf_push_line_omitted_without_code_words() -> None:
    gen = _generator(code_words_on=False)
    lines = gen._bluf_lines(_flight(), [_live_card()])
    assert not any("PUSH " in line for line in lines)


def test_bluf_sam_line_omitted_when_only_unidentified() -> None:
    gen = _generator(code_words_on=False)
    lines = gen._bluf_lines(_flight(), [_unknown_card()])
    assert not any("SAM " in line for line in lines)


def test_bluf_loadout_line_omitted_without_pylons() -> None:
    gen = _generator(code_words_on=False)
    lines = gen._bluf_lines(_flight(), [])
    assert not any(line.startswith("LOADOUT") for line in lines)


def test_bluf_jam_backup_line_none_without_a_registered_backup() -> None:
    # No enemy comms jamming this mission -> no JAM BACKUP comm registered -> the
    # BLUF carries no jam-backup line (§51).
    gen = _generator(code_words_on=False)
    lines = gen._bluf_lines(_flight(), [_live_card()])
    assert not any(JAM_BACKUP_COMM_NAME in line for line in lines)


def test_bluf_jam_backup_line_present_when_backup_registered() -> None:
    # §51: when the comms-jam planner allocated a fallback channel it is registered
    # on the generator's comm ladder; the BLUF surfaces it next to the code words
    # (moved off the Support Info package table, where it read as a phantom flight).
    gen = _generator(code_words_on=True)
    gen.add_comm(JAM_BACKUP_COMM_NAME, RadioFrequency(hertz=280_000_000))
    jam = next(
        line
        for line in gen._bluf_lines(_flight(), [_live_card()])
        if JAM_BACKUP_COMM_NAME in line
    )
    assert jam.startswith(JAM_BACKUP_COMM_NAME)
    assert "280.000 MHz AM" in jam


def test_code_words_block_none_when_feature_off() -> None:
    gen = _generator(code_words_on=False)
    assert gen._code_words_block(_flight()) is None


def test_code_words_block_marks_own_task_and_carries_event_words() -> None:
    gen = _generator(code_words_on=True)
    block = gen._code_words_block(_flight(FlightType.STRIKE))
    assert block is not None
    # The flight's own category is present and marked even with an empty ATO.
    own_rows = [row for row in block.pushes if row[2]]
    assert len(own_rows) == 1
    assert own_rows[0][0] == PushCategory.STRIKE.value
    assert block.success and block.abort
    # No EW package in the ATO -> no STOP JAM word.
    assert block.stop_jam is None


def test_brief_sam_threats_condenses_top_systems() -> None:
    def card(system: str, mez: str, live: int = 1) -> ThreatCard:
        return ThreatCard(
            system=system,
            band="LORAD",
            identified=True,
            guidance="—",
            ceiling="—",
            mez_nm=mez,
            detect_nm="—",
            harm="—",
            live=live,
            dead=0,
            cues=[],
            defeat="",
            sort_range_m=0.0,
        )

    cards = [
        card('SAM SA-5 S-200 "Square Pair" TR', "138"),
        card('SAM SA-10 S-300 "Grumble" Flap Lid TR', "65"),
        card("Unidentified MERAD", "—", live=0),  # not live -> excluded
    ]
    line = _brief_sam_threats(cards)
    assert "SA-5 S-200 138nm" in line
    assert "SA-10 S-300 65nm" in line
    assert "Unidentified" not in line


def test_brief_loadout_summarises_pylons() -> None:
    from game.data.weapons import Weapon, WeaponGroup

    WeaponGroup.load_all()
    # Two stations of the same clsid -> a "2x <name>" count; an empty station is ignored.
    clsid = next(iter(Weapon._by_clsid))
    unit = SimpleNamespace(pylons={1: {"CLSID": clsid}, 2: {"CLSID": clsid}, 3: {}})
    summary = _brief_loadout([unit])
    assert summary.startswith("2×")  # the doubled station is counted


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
