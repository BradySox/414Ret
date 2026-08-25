"""Neutral-faction border defense zones (§96).

A campaign yaml may declare neutral countries that defend their own airspace:
a border polygon (real-data traced, see ``tools/neutral_border_geo.py``), an
altitude floor under which a crossing counts, and the airfield the alert flight
launches from. Parsed at campaign load by ``MizCampaignLoader`` and persisted on
``ConflictTheater.neutral_border_zones``; consumed each turn by
``NeutralBorderGenerator`` + ``neutralborderluadata``. The planner never reads
these -- the border is a runtime (Lua) rule only, by design.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class NeutralBorderZone:
    """One neutral country's airspace and its alert posture."""

    #: DCS country name the alert units fly under, e.g. "Lebanon". Must exist in
    #: pydcs -- the generator skips the zone (with a warning) when it does not.
    country: str
    #: Map airfield the alert flight air-spawns overhead. Any airfield on the
    #: terrain works -- it does not need to be a campaign control point.
    airfield: str
    #: pydcs plane id for the alert fighters (vanilla only), e.g. "MiG-29A".
    aircraft: str
    #: Crossings above this are legal transit; below it the border trips.
    floor_ft: int
    #: Author an SA-6 point-defense battery template at the field, cloned on
    #: player escalation only.
    sam: bool
    #: Border polygon as terrain XY pairs (pydcs Point.x/.y = DCS x/z), closed
    #: implicitly (last vertex connects to first).
    border: list[tuple[float, float]] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, data: dict[str, Any]) -> "NeutralBorderZone | None":
        """Build a zone from one ``neutral_border_defense:`` yaml entry.

        Returns None (with a log line) on a malformed entry rather than raising:
        a bad campaign block must cost the feature, never the campaign.
        """
        try:
            border_raw = data.get("border", [])
            border = [(float(x), float(y)) for x, y in border_raw]
            if len(border) < 3:
                logging.warning(
                    "neutral_border_defense entry for %s: border needs 3+ "
                    "vertices — skipped",
                    data.get("country", "?"),
                )
                return None
            return cls(
                country=str(data["country"]),
                airfield=str(data["airfield"]),
                aircraft=str(data["aircraft"]),
                floor_ft=int(data.get("floor_ft", 10000)),
                sam=bool(data.get("sam", False)),
                border=border,
            )
        except (KeyError, TypeError, ValueError):
            logging.warning(
                "neutral_border_defense entry malformed — skipped", exc_info=True
            )
            return None
