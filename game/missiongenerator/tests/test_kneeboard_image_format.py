"""Kneeboard page image formats.

The recon pages render photographic Esri satellite basemaps, which PNG stores
losslessly at ~1.2 MB/page — ~90% of a generated miz. They go out as JPEG; every
line-art page stays PNG, where JPEG would ring on text and save nothing. These
tests pin the format split, the encoder rules, and the size win that motivates it.
"""

from __future__ import annotations

import random
from pathlib import Path

from PIL import Image

from game.missiongenerator.kneeboard_page import (
    JPEG_QUALITY,
    KneeboardPage,
    save_kneeboard_image,
)
from game.missiongenerator.kneeboard_recon.pages import (
    AirbaseReconPage,
    AirfieldDeparturePage,
    DetailReconPage,
    FrontLineDetailPage,
    OverviewReconPage,
    _RecordingPage,
)


def _photographic(size: tuple[int, int] = (768, 1024)) -> Image.Image:
    """Deterministic noise — an incompressible stand-in for satellite imagery.

    A flat fill or synthetic gradient would let PNG win, making the size
    assertion below pass for the wrong reason.
    """
    rng = random.Random(1234)
    return Image.frombytes("RGB", size, rng.randbytes(size[0] * size[1] * 3))


def test_recon_pages_are_written_as_jpeg() -> None:
    for page in (
        OverviewReconPage,
        DetailReconPage,
        AirbaseReconPage,
        AirfieldDeparturePage,
        FrontLineDetailPage,
    ):
        assert page.image_suffix == ".jpg", page.__name__
    assert _RecordingPage.image_suffix == ".jpg"


def test_line_art_pages_stay_png() -> None:
    """PNG is the default, so a page must opt in to JPEG deliberately."""
    assert KneeboardPage.image_suffix == ".png"


def test_save_writes_the_format_named_by_the_suffix(tmp_path: Path) -> None:
    img = _photographic((64, 64))

    save_kneeboard_image(img, tmp_path / "page.png")
    save_kneeboard_image(img, tmp_path / "page.jpg")

    assert Image.open(tmp_path / "page.png").format == "PNG"
    assert Image.open(tmp_path / "page.jpg").format == "JPEG"


def test_jpeg_save_handles_alpha(tmp_path: Path) -> None:
    """JPEG has no alpha channel; an RGBA page must not blow up the generator."""
    rgba = Image.new("RGBA", (32, 32), (10, 20, 30, 255))

    save_kneeboard_image(rgba, tmp_path / "page.jpg")

    assert Image.open(tmp_path / "page.jpg").mode == "RGB"


def test_jpeg_is_much_smaller_for_photographic_pages(tmp_path: Path) -> None:
    """The whole point: a satellite page is several times smaller as JPEG."""
    img = _photographic()

    save_kneeboard_image(img, tmp_path / "page.png")
    save_kneeboard_image(img, tmp_path / "page.jpg")

    png = (tmp_path / "page.png").stat().st_size
    jpg = (tmp_path / "page.jpg").stat().st_size
    assert jpg * 2 < png, f"jpeg {jpg} vs png {png} — expected a large saving"


def test_quality_is_the_measured_knee() -> None:
    """Pinned: 85 was chosen against a real recon page, not guessed."""
    assert JPEG_QUALITY == 85
