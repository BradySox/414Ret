"""Recon pages are written as JPEG, at their own declared suffix.

The unit-level format rules live in
``game/missiongenerator/tests/test_kneeboard_image_format.py``. These drive a
*real* recon page render (the same stubs the smoke tests use) through the
generator's actual naming path, so the size win is measured on real rendered
imagery rather than synthetic noise.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from PIL import Image

from game.missiongenerator.kneeboard_recon.pages import AirfieldDeparturePage


def _page(
    flight: MagicMock, game: MagicMock, weather: MagicMock
) -> AirfieldDeparturePage:
    return AirfieldDeparturePage(flight=flight, game=game, weather=weather)


def test_real_recon_page_writes_a_jpeg_at_its_declared_suffix(
    tmp_path: Path,
    stub_flight: MagicMock,
    stub_game: MagicMock,
    stub_weather: MagicMock,
) -> None:
    page = _page(stub_flight, stub_game, stub_weather)

    # Exactly how KneeboardGenerator names the file: the page picks its own suffix.
    out = tmp_path / f"page05{page.image_suffix}"
    page.write(out)

    assert out.name == "page05.jpg"
    assert Image.open(out).format == "JPEG"
    assert Image.open(out).size == (768, 1024)


def test_real_recon_page_is_far_smaller_as_jpeg(
    tmp_path: Path,
    stub_flight: MagicMock,
    stub_game: MagicMock,
    stub_weather: MagicMock,
) -> None:
    """The regression guard on the change's whole reason for existing."""
    _page(stub_flight, stub_game, stub_weather).write(tmp_path / "page.jpg")
    _page(stub_flight, stub_game, stub_weather).write(tmp_path / "page.png")

    jpg = (tmp_path / "page.jpg").stat().st_size
    png = (tmp_path / "page.png").stat().st_size
    assert jpg < png, f"jpeg {jpg} vs png {png}"
