"""Bordering-nation airspace (§96).

A campaign yaml lists the countries that border the war, each with a border
polygon (real-data traced, see ``tools/neutral_border_geo.py``). **Every
bordering nation should be represented** (DM call, 2026-08-24): drawing only the
dangerous ones tells the player where not to go but never where they *may* go,
which reads as "the rest of the map is unmodelled" rather than "this one is
fine".

**Alignment is derived, not authored** (DM call, 2026-08-24): *a nation hosting
a RED or BLUE airfield is aligned with that team; a nation hosting neither is
the neutral.* The campaign already knows who owns what, so asking the yaml to
repeat it only creates something that can go stale -- and deriving it means a
country flips the turn its field changes hands. ``posture:`` overrides the
derivation for the case base-ownership gets wrong.

The three postures and what each means to a pilot:

* ``neutral`` -- genuinely out of the war. Whether it lets you *through* is a
  second, authored fact (``overflight``), because alignment does not decide it:
  in 2006 Turkmenistan permitted coalition transit and Iran did not, and both
  were neutral. A neutral that refuses transit defends its airspace -- cross
  below the floor and a §96 alert flight shadows, warns, and engages a player
  who presses. One that permits it is drawn and nothing more.
* ``blue`` -- hosts your side's fields. Overflight is allowed; the border is
  drawn and nothing enforces it.
* ``red`` -- hosts the enemy's fields. Not a third party, so it gets no §96
  flight of its own; instead its polygon is handed to **§1's QRA dispatcher as
  a RED accept zone**, so the enemy's existing alert fighters defend it. One
  interception system over that ground, not two.

Only ``neutral`` zones need an ``aircraft`` and an origin, because only they
spawn anything. That is also what lets a nation DCS does not model be drawn at
all: DCS has no Turkmenistan, Uzbekistan or Tajikistan, and a zone that spawns
nothing needs no pydcs country.

Parsed at campaign load by ``MizCampaignLoader`` and persisted on
``ConflictTheater.neutral_border_zones``; consumed each turn by
``NeutralBorderGenerator`` + ``neutralborderluadata``. The planner never reads
these -- the border is a runtime (Lua) rule only, by design.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

#: Air-spawn altitude for a point-spawned alert flight when the campaign does
#: not say. A standing CAP, not a scramble -- high enough to be a credible
#: intercept and clear of Afghanistan's terrain.
DEFAULT_SPAWN_ALT_FT = 20000

#: No coalition airfield inside it: out of the war, and it defends itself.
NEUTRAL = "neutral"
#: Hosts BLUE airfields -- a blue host, not a third party.
BLUE_ALIGNED = "blue"
#: Hosts RED airfields.
RED_ALIGNED = "red"
POSTURES = (NEUTRAL, BLUE_ALIGNED, RED_ALIGNED)


@dataclass(frozen=True)
class NeutralBorderZone:
    """One bordering country's airspace and what happens if you enter it."""

    #: Display name. A ``neutral`` zone spawns units, so its name must also be a
    #: pydcs country; an aligned zone spawns nothing and any name works.
    country: str
    #: pydcs plane id for the alert fighters (vanilla only). Neutral only.
    aircraft: str | None = None
    #: Crossings above this are legal transit; below it a neutral border trips.
    floor_ft: int = 10000
    #: Author an SA-6 point-defense battery, cloned on player escalation only.
    sam: bool = False
    #: Map airfield the alert flight air-spawns overhead. Any airfield on the
    #: terrain works -- it does not need to be a campaign control point.
    airfield: str | None = None
    #: Terrain XY the alert flight air-spawns at, for a neutral with no airfield
    #: on the map. Mutually exclusive with ``airfield``.
    spawn: tuple[float, float] | None = None
    #: Air-spawn altitude for ``spawn`` (ignored for an airfield zone).
    spawn_alt_ft: int = DEFAULT_SPAWN_ALT_FT
    #: Author override for the derived alignment, or None to derive it.
    posture_override: str | None = None
    #: Does this neutral permit transit? Alignment says whose side a country is
    #: on; this says whether an uninvolved one lets you through, which is a
    #: separate diplomatic fact the campaign has to state. In 2006 Turkmenistan
    #: permitted coalition overflight and Iran did not, and both were neutral.
    #: A permitting neutral spawns nothing, so it needs no aircraft or origin.
    #: Meaningless on an aligned zone (blue lets you through, red is the enemy).
    overflight: bool = False
    #: Border polygon as terrain XY pairs (pydcs Point.x/.y = DCS x/z), closed
    #: implicitly (last vertex connects to first).
    border: list[tuple[float, float]] = field(default_factory=list)

    def posture_in(self, theater: Any) -> str:
        """This country's alignment: who owns the airfields inside its border.

        A country hosting both sides' fields is contested, not neutral; it
        resolves to whoever holds more, because the one thing it certainly is
        not is an uninvolved third party.
        """
        if self.posture_override is not None:
            return self.posture_override
        blue, red = self.control_points_in(theater)
        if blue == 0 and red == 0:
            return NEUTRAL
        return BLUE_ALIGNED if blue >= red else RED_ALIGNED

    def control_points_in(self, theater: Any) -> tuple[int, int]:
        """(blue, red) control-point counts inside this border."""
        from shapely.geometry import Point as ShapelyPoint, Polygon

        if len(self.border) < 3:
            return (0, 0)
        polygon = Polygon(self.border)
        blue = red = 0
        for cp in getattr(theater, "controlpoints", []):
            # An off-map spawn is not territory; it sits at a map edge and would
            # falsely align whichever country the edge happens to run through.
            if type(cp).__name__ == "OffMapSpawn":
                continue
            position = getattr(cp, "position", None)
            if position is None:
                continue
            if not polygon.contains(ShapelyPoint(position.x, position.y)):
                continue
            captured = getattr(cp, "captured", None)
            if captured is None:
                continue
            if getattr(captured, "is_blue", False):
                blue += 1
            elif getattr(captured, "is_red", False):
                red += 1
        return (blue, red)

    def enforces_in(self, theater: Any) -> bool:
        """True when this border will actually intercept an intruder.

        Only an uninvolved country that refuses transit does: an aligned one is
        handled by its own side's QRA, and a permitting neutral is a line on the
        map by definition.
        """
        return self.posture_in(theater) == NEUTRAL and not self.overflight

    def origin_label(self, posture: str) -> str:
        """What the map tooltip calls this border's meaning."""
        if posture == BLUE_ALIGNED:
            return "friendly — overflight permitted"
        if posture == RED_ALIGNED:
            return "enemy-aligned"
        if self.overflight:
            return "neutral — overflight permitted"
        if self.airfield is not None:
            return self.airfield
        return f"{self.country} border CAP"

    @classmethod
    def from_yaml(cls, data: dict[str, Any]) -> "NeutralBorderZone | None":
        """Build a zone from one ``neutral_border_defense:`` yaml entry.

        Returns None (with a log line) on a malformed entry rather than raising:
        a bad campaign block must cost the feature, never the campaign.

        ``aircraft`` and an origin are validated whenever they are present or
        the zone could derive to ``neutral`` -- which is any zone without an
        override pinning it to a coalition. A blue/red-pinned zone may omit
        them, since it will never spawn.
        """
        try:
            country = str(data["country"])
            border_raw = data.get("border", [])
            border = [(float(x), float(y)) for x, y in border_raw]
            if len(border) < 3:
                logging.warning(
                    "neutral_border_defense entry for %s: border needs 3+ "
                    "vertices — skipped",
                    country,
                )
                return None

            override = data.get("posture")
            if override is not None:
                override = str(override).lower()
                if override not in POSTURES:
                    logging.warning(
                        "neutral_border_defense entry for %s: posture must be one "
                        "of %s — skipped",
                        country,
                        "/".join(POSTURES),
                    )
                    return None

            airfield = data.get("airfield")
            spawn_raw = data.get("spawn")
            aircraft = data.get("aircraft")
            overflight = bool(data.get("overflight", False))
            # Only a zone that could end up intercepting needs the means to.
            can_be_neutral = override in (None, NEUTRAL) and not overflight

            if can_be_neutral:
                # It may end up defending, so it needs something to defend with.
                if (airfield is None) == (spawn_raw is None):
                    logging.warning(
                        "neutral_border_defense entry for %s: a zone that can "
                        "derive to neutral needs exactly one of 'airfield' or "
                        "'spawn' — skipped",
                        country,
                    )
                    return None
                if aircraft is None:
                    logging.warning(
                        "neutral_border_defense entry for %s: a zone that can "
                        "derive to neutral needs 'aircraft' — skipped",
                        country,
                    )
                    return None

            spawn = None
            if spawn_raw is not None:
                spawn = (float(spawn_raw[0]), float(spawn_raw[1]))

            return cls(
                country=country,
                aircraft=str(aircraft) if aircraft is not None else None,
                floor_ft=int(data.get("floor_ft", 10000)),
                sam=bool(data.get("sam", False)),
                airfield=str(airfield) if airfield is not None else None,
                spawn=spawn,
                spawn_alt_ft=int(data.get("spawn_alt_ft", DEFAULT_SPAWN_ALT_FT)),
                posture_override=override,
                overflight=overflight,
                border=border,
            )
        except (KeyError, TypeError, ValueError, IndexError):
            logging.warning(
                "neutral_border_defense entry malformed — skipped", exc_info=True
            )
            return None
