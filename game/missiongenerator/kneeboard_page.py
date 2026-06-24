"""Base class for kneeboard pages.

Kept in its own module to avoid circular imports between kneeboard.py and
kneeboard_recon/pages.py, which both need KneeboardPage.
"""

from __future__ import annotations

from pathlib import Path
from typing import List


class KneeboardPage:
    """Base class for all kneeboard pages."""

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
