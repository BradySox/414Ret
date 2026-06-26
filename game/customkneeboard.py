"""Player-authored custom kneeboard pages stored in the campaign save.

A `CustomKneeboard` is an image (PNG/JPG bytes) the campaign owner imports through
the UI to be injected into every client flight's kneeboard at mission generation —
optionally scoped to a single airframe. Storing the bytes in the save (rather than a
loose file path) keeps the kneeboard self-contained: it travels with the `.retribution`
file and is per-campaign, never leaking into other campaigns the way the global
``Saved Games/DCS/Retribution/Kneeboards`` folder does.

The injection happens in ``KneeboardGenerator.generate`` (see ``missiongenerator/
kneeboard.py``); DCS can only scope kneeboards per airframe, so ``airframe_id`` (a DCS
unit-type id) is the finest grain available — ``None`` means "all client flights".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class CustomKneeboard:
    """One imported kneeboard image and the airframe it applies to."""

    #: Short label shown in the management UI (e.g. the source filename).
    name: str
    #: Raw image bytes (PNG/JPG) as imported; written to a temp PNG at generation.
    image: bytes
    #: DCS unit-type id to scope this page to, or ``None`` for every client flight.
    airframe_id: Optional[str] = None

    @property
    def scope_label(self) -> str:
        """Human-readable scope for the management UI."""
        return self.airframe_id if self.airframe_id else "All flights"
