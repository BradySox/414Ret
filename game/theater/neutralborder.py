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
from typing import Any, Optional

#: Air-spawn altitude for a point-spawned alert flight when the campaign does
#: not say. A standing CAP, not a scramble -- high enough to be a credible
#: intercept and clear of Afghanistan's terrain.
DEFAULT_SPAWN_ALT_FT = 20000

#: Floor for a `contested` country when the campaign does not state one. Only
#: that bucket gets a floor at all -- see NeutralBorderZone.floor_for.
DEFAULT_CONTESTED_FLOOR_FT = 10000

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
    #: Author override for the altitude below which a crossing trips, or None
    #: to derive it. **A floor is not a universal rule** (DM call, 2026-08-25):
    #: it means "high transit is tolerated", which is true of a country that
    #: merely dislikes you and false of one that is closed. Derived, only a
    #: `contested` posture gets one; `closed` and `hostile` intercept at any
    #: altitude, because inventing a safe height there is inventing a sanctuary.
    floor_ft: Optional[int] = None
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
    #: Author override for transit consent, or None to resolve it from the
    #: dated posture table. Alignment says whose side a country is on; this says
    #: whether an uninvolved one lets you through, which alignment cannot decide
    #: -- in 2006 Turkmenistan permitted coalition transit and Iran did not, and
    #: both were neutral. Resolved per side, so a country may be open to one
    #: bloc and closed to the other. Meaningless on an aligned zone.
    overflight_override: Optional[bool] = None
    #: Border polygon as terrain XY pairs (pydcs Point.x/.y = DCS x/z), closed
    #: implicitly (last vertex connects to first).
    border: list[tuple[float, float]] = field(default_factory=list)
    #: Came from resources/borders/<terrain>.yaml rather than the campaign.
    #: Set after construction, never parsed -- a terrain list is a cache of a
    #: shipped file, so a save carrying one is refreshed on load instead of
    #: freezing whatever shipped the day it was made. A campaign's own zones are
    #: campaign state and are never touched.
    from_terrain: bool = False

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

    def permits(self, bloc: str, on: Any) -> bool:
        """Does this country let ``bloc``'s aircraft transit on ``on``?

        The campaign's override wins outright; otherwise the dated table
        decides, defaulting to refusal for anything it does not cover.
        """
        if self.overflight_override is not None:
            return self.overflight_override
        from game.theater.nationalpostures import permits_overflight

        return permits_overflight(self.country, on, bloc)

    def floor_for(self, bloc: str, on: Any) -> Optional[int]:
        """Altitude below which a crossing trips, or None for any altitude.

        The campaign's value wins. Otherwise only a `contested` posture gets a
        floor -- a country that is closed or hostile offers no safe height.
        """
        if self.floor_ft is not None:
            return self.floor_ft
        from game.theater.nationalpostures import CONTESTED, posture_for

        if posture_for(self.country, on, bloc) == CONTESTED:
            return DEFAULT_CONTESTED_FLOOR_FT
        return None

    def enforces_against(self, theater: Any, bloc: str, on: Any) -> bool:
        """True when this border intercepts ``bloc``'s aircraft.

        Only an uninvolved country that refuses that side transit does: an
        aligned one is handled by its own side's QRA, and a permitting neutral
        is a line on the map by definition.
        """
        return self.posture_in(theater) == NEUTRAL and not self.permits(bloc, on)

    def origin_label(self, posture: str, enforced: bool = True) -> str:
        """What the map tooltip calls this border's meaning."""
        if posture == BLUE_ALIGNED:
            return "friendly — overflight permitted"
        if posture == RED_ALIGNED:
            return "enemy-aligned"
        if not enforced:
            return "neutral — overflight permitted"
        if self.airfield is not None:
            return self.airfield
        return f"{self.country} border CAP"

    @classmethod
    def from_yaml(
        cls, data: dict[str, Any], from_terrain: bool = False
    ) -> "NeutralBorderZone | None":
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
            overflight = data.get("overflight")
            if overflight is not None:
                overflight = bool(overflight)

            # Naming BOTH origins is a real authoring error and still refused.
            # Naming NEITHER is not: whether this zone ever needs one depends on
            # its alignment and the posture table, neither of which exists at
            # parse time -- and requiring them here would defeat the point of a
            # campaign being able to list a country and its border, nothing
            # else. A zone that turns out to need an origin it lacks is skipped
            # by the generator, with a log line naming the country.
            if airfield is not None and spawn_raw is not None:
                logging.warning(
                    "neutral_border_defense entry for %s: name 'airfield' or "
                    "'spawn', not both — skipped",
                    country,
                )
                return None

            spawn = None
            if spawn_raw is not None:
                spawn = (float(spawn_raw[0]), float(spawn_raw[1]))

            return cls(
                country=country,
                aircraft=str(aircraft) if aircraft is not None else None,
                floor_ft=(
                    int(data["floor_ft"]) if data.get("floor_ft") is not None else None
                ),
                sam=bool(data.get("sam", False)),
                airfield=str(airfield) if airfield is not None else None,
                spawn=spawn,
                spawn_alt_ft=int(data.get("spawn_alt_ft", DEFAULT_SPAWN_ALT_FT)),
                posture_override=override,
                overflight_override=overflight,
                border=border,
                from_terrain=from_terrain,
            )
        except (KeyError, TypeError, ValueError, IndexError):
            logging.warning(
                "neutral_border_defense entry malformed — skipped", exc_info=True
            )
            return None
