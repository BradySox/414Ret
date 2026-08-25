"""Neutral-faction border defense zones (§96).

A campaign yaml may declare neutral countries that defend their own airspace:
a border polygon (real-data traced, see ``tools/neutral_border_geo.py``), an
altitude floor under which a crossing counts, and where the alert flight comes
from. Parsed at campaign load by ``MizCampaignLoader`` and persisted on
``ConflictTheater.neutral_border_zones``; consumed each turn by
``NeutralBorderGenerator`` + ``neutralborderluadata``. The planner never reads
these -- the border is a runtime (Lua) rule only, by design.

**The alert flight comes from a field OR a point.** Most maps put the neutral's
own airbase on the map (Syria has Rayak), and a cold field is the natural
source. Some do not: the DCS Afghanistan map carries 26 airfields and **every
one is inside Afghanistan**, so Pakistan, Iran, Turkmenistan, Uzbekistan and
Tajikistan have no field to launch from at all. Those zones declare a ``spawn``
point instead and the flight air-spawns over its own side of the line -- a CAP
already up, which is what a nervous neighbour actually keeps airborne.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

#: Air-spawn altitude for a point-spawned alert flight when the campaign does
#: not say. A standing CAP, not a scramble -- high enough to be a credible
#: intercept and clear of Afghanistan's terrain.
DEFAULT_SPAWN_ALT_FT = 20000


@dataclass(frozen=True)
class NeutralBorderZone:
    """One neutral country's airspace and its alert posture."""

    #: DCS country name the alert units fly under, e.g. "Lebanon". Must exist in
    #: pydcs -- the generator skips the zone (with a warning) when it does not.
    country: str
    #: pydcs plane id for the alert fighters (vanilla only), e.g. "MiG-29A".
    aircraft: str
    #: Crossings above this are legal transit; below it the border trips.
    floor_ft: int
    #: Author an SA-6 point-defense battery, cloned on player escalation only.
    sam: bool
    #: Map airfield the alert flight air-spawns overhead. Any airfield on the
    #: terrain works -- it does not need to be a campaign control point. None
    #: when the zone uses ``spawn`` instead.
    airfield: str | None = None
    #: Terrain XY the alert flight air-spawns at, for a neutral with no airfield
    #: on the map. Mutually exclusive with ``airfield``.
    spawn: tuple[float, float] | None = None
    #: Air-spawn altitude for ``spawn`` (ignored for an airfield zone).
    spawn_alt_ft: int = DEFAULT_SPAWN_ALT_FT
    #: Border polygon as terrain XY pairs (pydcs Point.x/.y = DCS x/z), closed
    #: implicitly (last vertex connects to first).
    border: list[tuple[float, float]] = field(default_factory=list)

    @property
    def origin_label(self) -> str:
        """What the map tooltip and kneeboard call the alert flight's source."""
        if self.airfield is not None:
            return self.airfield
        return f"{self.country} border CAP"

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

            airfield = data.get("airfield")
            spawn_raw = data.get("spawn")
            if (airfield is None) == (spawn_raw is None):
                logging.warning(
                    "neutral_border_defense entry for %s: needs exactly one of "
                    "'airfield' or 'spawn' — skipped",
                    data.get("country", "?"),
                )
                return None
            spawn = None
            if spawn_raw is not None:
                spawn = (float(spawn_raw[0]), float(spawn_raw[1]))

            return cls(
                country=str(data["country"]),
                aircraft=str(data["aircraft"]),
                floor_ft=int(data.get("floor_ft", 10000)),
                sam=bool(data.get("sam", False)),
                airfield=str(airfield) if airfield is not None else None,
                spawn=spawn,
                spawn_alt_ft=int(data.get("spawn_alt_ft", DEFAULT_SPAWN_ALT_FT)),
                border=border,
            )
        except (KeyError, TypeError, ValueError, IndexError):
            logging.warning(
                "neutral_border_defense entry malformed — skipped", exc_info=True
            )
            return None
