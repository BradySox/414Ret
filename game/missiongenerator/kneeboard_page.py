"""Base class for kneeboard pages.

Kept in its own module to avoid circular imports between kneeboard.py and
kneeboard_recon/pages.py, which both need KneeboardPage.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, List

if TYPE_CHECKING:
    from PIL.Image import Image

#: Encoder quality for JPEG pages. 85 is the measured knee for the recon
#: basemaps: a 768x1024 Esri satellite page is 1212 KB as PNG and 206 KB at q85
#: (mean pixel difference ~1.4%, no visible ringing even on the black title bar's
#: white text). q92 costs ~40% more bytes for no visible gain at kneeboard size.
JPEG_QUALITY = 85

_JPEG_SUFFIXES = {".jpg", ".jpeg"}


def save_kneeboard_image(image: Image, path: Path) -> None:
    """Write a kneeboard page image, encoding by ``path``'s suffix.

    The single save site for every page, so the format rules live in one place:
    JPEG needs RGB (it has no alpha channel) and an explicit quality, while PNG
    is saved exactly as it always was. Pillow infers the format from the suffix,
    and pydcs writes the file into the miz under its own name, so a page's
    ``image_suffix`` is the whole of the decision.
    """
    if path.suffix.lower() in _JPEG_SUFFIXES:
        image.convert("RGB").save(path, quality=JPEG_QUALITY, optimize=True)
    else:
        image.save(path)


class KneeboardPage:
    """Base class for all kneeboard pages."""

    #: File extension this page is written with, which picks the encoder (see
    #: :func:`save_kneeboard_image`). PNG is the right default: kneeboard pages
    #: are line art -- text, tables, rules -- which PNG stores losslessly and
    #: cheaply (20-100 KB/page) and which JPEG would both bloat and ring. Pages
    #: rendering *photographic* content override this to ".jpg"; see
    #: ``kneeboard_recon.pages._RecordingPage``.
    image_suffix: ClassVar[str] = ".png"

    def write(self, path: Path) -> None:
        """Writes the kneeboard page to the given path."""
        raise NotImplementedError

    def paginate(self) -> List["KneeboardPage"]:
        """Expand this page into the concrete pages that should be written.

        Most pages occupy a single image and return ``[self]``. Pages whose
        content can overflow a single image (e.g. long folded tables) return
        themselves plus continuation pages so nothing runs off the bottom edge.
        """
        return [self]
