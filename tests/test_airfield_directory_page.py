from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from PIL import Image, ImageFont

from game.missiongenerator.kneeboard import (
    SupportPage,
    build_airfield_directory_rows,
)
from game.radio.radios import MHz
from game.theater.controlpoint import Airfield


def _airfield(name: str, friendly: bool) -> MagicMock:
    cp = MagicMock(spec=Airfield)
    cp.full_name = name
    cp.is_friendly.return_value = friendly
    runway = MagicMock()
    runway.atc = None
    runway.tacan = None
    runway.ils = None
    runway.icls = None
    runway.runway_name = "13"
    cp.active_runway.return_value = runway
    return cp


def _game(*cps: MagicMock) -> MagicMock:
    game = MagicMock()
    game.theater.controlpoints = list(cps)
    return game


def test_rows_only_blue_airfields_with_atis() -> None:
    blue = _airfield("Batumi", friendly=True)
    red = _airfield("Mozdok", friendly=False)
    flight = MagicMock()
    flight.channel_for.return_value = None
    rows = build_airfield_directory_rows(_game(blue, red), flight, {"Batumi": MHz(131)})
    assert len(rows) == 1
    field, atc, atis, *_ = rows[0]
    assert field == "Batumi"
    assert "131" in atis


def _support_flight() -> MagicMock:
    flight = MagicMock()
    flight.custom_name = None
    flight.callsign = "Enfield 1-1"
    flight.intra_flight_channel = MHz(251)
    flight.channels_for.return_value = []
    package = MagicMock()
    package.custom_name = None
    package.package_description = "Strike"
    package.frequency = MHz(251)
    package.time_over_target = None
    flight.package = package
    return flight


def test_support_page_renders_airfield_directory_section(tmp_path: Path) -> None:
    rows = [["Batumi", "", "VHF 131.000", "", "", "13"]]
    page = SupportPage(
        _support_flight(),
        package_flights=[],
        comms=[],
        awacs=[],
        tankers=[],
        jtacs=[],
        start_time=MagicMock(),
        dark_kneeboard=False,
        airfield_rows=rows,
    )
    out = tmp_path / "support.png"
    stub_font = ImageFont.load_default()
    with patch(
        "game.missiongenerator.kneeboard.ImageFont.truetype", return_value=stub_font
    ):
        page.write(out)
    assert out.exists()
    img = Image.open(out)
    assert img.size == (960, 1080)
