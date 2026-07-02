"""Tests for the one-page Brief Sheet (compact deck P1) and its auto-fill helpers."""

from __future__ import annotations

import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, List

from game.ato.flighttype import FlightType
from game.ato.flightwaypointtype import FlightWaypointType
from game.missiongenerator.kneeboard import (
    BriefSheetData,
    BriefSheetPage,
    KneeboardGenerator,
    ThreatCard,
    _brief_game_plan,
    _brief_loadout,
    _brief_mission,
    _brief_route,
    _brief_sam_threats,
)


def _wp(
    wptype: FlightWaypointType,
    name: str,
    tot: datetime.datetime | None = None,
    departure_time: datetime.datetime | None = None,
) -> Any:
    return SimpleNamespace(
        waypoint_type=wptype,
        name=name,
        pretty_name=name,
        tot=tot,
        departure_time=departure_time,
    )


def test_brief_route_lists_every_point_and_collapses_target_runs() -> None:
    t = datetime.datetime(2020, 1, 1, 19, 5, 0)
    waypoints = [
        _wp(FlightWaypointType.TAKEOFF, "Hahn", tot=t),
        _wp(FlightWaypointType.LOITER, "Scabbard", departure_time=t),
        _wp(FlightWaypointType.REFUEL, "Texaco"),
        _wp(FlightWaypointType.JOIN, "Lancer"),
        _wp(FlightWaypointType.INGRESS_SEAD, "INGRESS on Bongo"),
        _wp(FlightWaypointType.TARGET_POINT, "Bongo"),
        _wp(FlightWaypointType.TARGET_POINT, "Bongo"),
        _wp(FlightWaypointType.TARGET_POINT, "Bongo"),
        _wp(FlightWaypointType.SPLIT, "Picket"),
        _wp(FlightWaypointType.LANDING_POINT, "Hahn"),
        _wp(FlightWaypointType.BULLSEYE, "bulls"),  # own field -> skipped
    ]

    def fmt(waypoint: Any) -> str:
        return "19:05" if (waypoint.tot or waypoint.departure_time) else ""

    route = _brief_route(waypoints, fmt)
    # Every steerpoint is listed with its number (the waypoint index) and time;
    # the run of TARGET_POINTs (5-7) collapses to one TGT entry with a range.
    assert route == [
        ("T/O", "0", "19:05"),
        ("HOLD", "1", "19:05"),  # hold carries its push (departure) time
        ("TKR", "2", ""),
        ("JOIN", "3", ""),
        ("IP", "4", ""),
        ("TGT", "5-7", ""),
        ("EGRESS", "8", ""),
        ("LAND", "9", ""),
    ]


def test_brief_mission_builds_a_sentence() -> None:
    assert (
        _brief_mission(FlightType.SEAD, "BONGO", "SEAD")
        == "Suppress the air defenses at BONGO."
    )
    assert _brief_mission(FlightType.STRIKE, "Depot 4", "Strike") == "Strike Depot 4."
    # No target (a patrol) falls back to a fragged line, never an empty string.
    assert _brief_mission(FlightType.BARCAP, "", "BARCAP") == "BARCAP as fragged."
    # The doctrine display label (Vietnam rename) is used in the no-verb fallback.
    assert _brief_mission(FlightType.BARCAP, "", "MiGCAP") == "MiGCAP as fragged."


def _card(system: str, mez: str, defeat: str = "", live: int = 1) -> ThreatCard:
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
        defeat=defeat,
        sort_range_m=0.0,
    )


def test_brief_sam_threats_condenses_top_systems() -> None:
    cards = [
        _card('SAM SA-5 S-200 "Square Pair" TR', "138"),
        _card('SAM SA-10 S-300 "Grumble" Flap Lid TR', "65"),
        _card("Unidentified MERAD", "—", live=0),  # not live -> excluded
    ]
    line = _brief_sam_threats(cards)
    assert "SA-5 S-200 138nm" in line
    assert "SA-10 S-300 65nm" in line
    assert "Unidentified" not in line


def test_brief_game_plan_trims_to_a_line() -> None:
    short = _card("SA-6", "20", defeat="Stay low and HARM the Straight Flush.")
    assert _brief_game_plan([short]) == "Stay low and HARM the Straight Flush."
    long = _card("SA-5", "138", defeat="word " * 60)
    plan = _brief_game_plan([long])
    assert plan.endswith("…") and len(plan) <= 160


def test_brief_loadout_summarises_pylons() -> None:
    from game.data.weapons import Weapon, WeaponGroup

    WeaponGroup.load_all()
    # Two stations of the same clsid -> a "2x <name>" count; an empty station is ignored.
    clsid = next(iter(Weapon._by_clsid))
    unit = SimpleNamespace(pylons={1: {"CLSID": clsid}, 2: {"CLSID": clsid}, 3: {}})
    summary = _brief_loadout([unit])
    assert summary.startswith("2×")  # the doubled station is counted


def test_brief_freq_includes_preset_channel() -> None:
    from game.missiongenerator.kneeboard import _brief_freq

    freq = SimpleNamespace(mhz=264.0)
    bare = SimpleNamespace()  # no channel_for -> bare freq
    assert _brief_freq(bare, freq) == "264.0"
    assert _brief_freq(bare, None) == ""
    preset = SimpleNamespace(
        channel_for=lambda f: SimpleNamespace(radio_id=1, channel=4),
        aircraft_type=SimpleNamespace(channel_name=lambda r, c: f"COMM{r} Ch{c}"),
    )
    assert _brief_freq(preset, freq) == "COMM1 Ch4 264.0"


def test_brief_sheet_page_renders_and_colour_codes(tmp_path: Path) -> None:
    data = BriefSheetData(
        op_turn="RED TIDE · TURN 2",
        mc=None,
        ident="ROMAN 7 · 2-ship SEAD · F/A-18C",
        tot="19:30Z",
        mission="Suppress the SA-2/3 belt vic BONGO.",
        route=[("HOLD", "1", "19:05"), ("IP", "3", "19:21"), ("TGT", "5", "19:30")],
        bingo="5100",
        joker="6100",
        divert="Frankfurt",
        hard_deck="—",
        threats_air="MiG-29 CAP near the front.",
        threats_sam="SA-5 138nm",
        game_plan="HARM from standoff.",
        comms=[("PKG ", "264.0")],
        guard="243.0",
        push_word="Cobalt",
        success_word="Crimson",
        abort_word="Teal",
        threat_word=None,
        bullseye="N50 E10",
        fields="Dep Hahn 21",
        weather="QNH 29.92 inHg / 1013 hPa · Wind 240°/12kt",
        loadout="2× AGM-88",
        laser="1688",
        sar=[("King", "Toxic")],
        if_down="beacon on, squawk 7700",
    )
    page = BriefSheetPage(
        SimpleNamespace(callsign="Roman 7"), data, dark_kneeboard=True  # type: ignore[arg-type]
    )
    out = tmp_path / "brief.png"
    page.write(out)
    assert out.exists()
    text = out.with_suffix(".txt").read_text("utf8")
    for token in ("ROMAN 7", "HOLD", "BINGO", "Cobalt", "If down", "QNH"):
        assert token in text


def _generator() -> KneeboardGenerator:
    gen = KneeboardGenerator.__new__(KneeboardGenerator)
    gen.awacs = [SimpleNamespace(callsign="Magic", freq=SimpleNamespace(mhz=251.0))]  # type: ignore[list-item]
    gen.tankers = [SimpleNamespace(callsign="Arco", freq=SimpleNamespace(mhz=322.0))]  # type: ignore[list-item]
    gen.flights = []
    coalition = SimpleNamespace(
        bullseye=SimpleNamespace(
            position=SimpleNamespace(
                latlng=lambda: SimpleNamespace(format_dms=lambda: "N50 E10")
            )
        ),
        code_words=SimpleNamespace(
            push_for=lambda ft: "Cobalt", success="Crimson", abort="Teal"
        ),
        opponent=SimpleNamespace(faction=SimpleNamespace(aircraft=[])),
    )
    gen.game = SimpleNamespace(  # type: ignore[assignment]
        campaign_name="Red Tide",
        turn=2,
        settings=SimpleNamespace(enable_package_code_words=True),
        coalition_for=lambda player: coalition,
    )
    return gen


def _flight() -> Any:
    units = SimpleNamespace(mass=lambda m: m.pounds, mass_uom="lb")
    return SimpleNamespace(
        callsign="Roman 7",
        custom_name=None,
        friendly=object(),
        size=2,
        flight_type=FlightType.SEAD,
        task_display_name=FlightType.SEAD.value,
        aircraft_type=SimpleNamespace(
            kneeboard_units=units, utc_kneeboard=False, variant_id="F/A-18C"
        ),
        package=SimpleNamespace(
            target=SimpleNamespace(name="BONGO"),
            time_over_target=None,
            frequency=SimpleNamespace(mhz=264.0),
        ),
        waypoints=[
            _wp(FlightWaypointType.JOIN, "Lancer"),
            _wp(FlightWaypointType.INGRESS_SEAD, "Bongo"),
            _wp(FlightWaypointType.TARGET_POINT, "Bongo"),
        ],
        bingo_fuel=5100,
        joker_fuel=6100,
        divert=SimpleNamespace(airfield_name="Frankfurt"),
        departure=SimpleNamespace(airfield_name="Hahn", runway_name="21"),
        arrival=SimpleNamespace(airfield_name="Hahn", runway_name="21"),
        units=[SimpleNamespace(pylons={})],
        laser_codes=[1688, None],
        combat_sar_king=None,
    )


def test_brief_weather_reports_qnh_and_surface_wind() -> None:
    gen = _generator()
    gen.game.conditions = SimpleNamespace(  # type: ignore[assignment]
        weather=SimpleNamespace(
            atmospheric=SimpleNamespace(
                qnh=SimpleNamespace(inches_hg=29.92), temperature_celsius=15.0
            ),
            wind=SimpleNamespace(at_0m=SimpleNamespace(direction=240.0, speed=6.0)),
        )
    )
    gen.game.theater = None  # type: ignore[assignment]
    line = gen._brief_weather(_flight())
    assert line.startswith("QNH 29.92 inHg / 1013 hPa")
    assert "Wind" in line and line.endswith("kt")
    # No theater -> no field elevation -> raw sea-level QNH and no QFE.
    assert "QFE" not in line


def test_brief_weather_is_best_effort() -> None:
    # The fake generator carries no weather at all: the WX field falls back to
    # the fill-in blank rather than crashing sheet generation.
    assert _generator()._brief_weather(_flight()) == ""


def test_build_brief_sheet_data_populates_from_the_mission() -> None:
    gen = _generator()
    flight = _flight()
    cards = [_card('SAM SA-5 S-200 "Square Pair" TR', "138", defeat="Stand off.")]
    data = gen._build_brief_sheet_data(flight, cards)

    assert data.op_turn == "RED TIDE · TURN 2"
    assert data.ident == "Roman 7 · 2-ship SEAD · F/A-18C"
    assert data.mission == "Suppress the air defenses at BONGO."
    # First waypoint is the join, steerpoint 0; the fake carries no times.
    assert data.route[0] == ("JOIN", "0", "")
    assert data.bingo == "5100" and data.divert == "Frankfurt"
    assert data.push_word == "Cobalt" and data.abort_word == "Teal"
    assert "SA-5 S-200 138nm" in data.threats_sam
    assert data.game_plan == "Stand off."
    assert data.comms[0] == ("PKG ", "264.0")  # no preset channel on the fake flight
    assert data.laser == "1688"  # the None member code is dropped
    assert data.bullseye == "N50 E10"
    # Empty enemy faction -> the loose fallback air-threat line, never a crash.
    assert "CAP" in data.threats_air
