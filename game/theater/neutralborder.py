"""Bordering-nation airspace (§96).

A campaign yaml lists the countries that border the war, each with a border
polygon, though in practice every shipped border comes from the terrain files
that ``tools/build_terrain_borders.py`` generates. **Every
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

The four postures and what each means to a pilot:

* ``neutral`` -- genuinely out of the war: no coalition holds an airfield
  inside it. It defends its airspace -- it flies a standing patrol inside its
  own border from mission start, hails you on entry, and turns hostile in place
  on a player who presses. A neutral that can field no
  interceptor (DCS models no Turkmenistan; Cyprus and Armenia have no entry in
  the dated table) is drawn and toothless, on the map as well as in the
  mission.
* ``blue`` -- hosts your side's fields. Overflight is allowed; the border is
  drawn and nothing enforces it.
* ``red`` -- hosts the enemy's fields. Not a third party, so it gets no §96
  flight of its own; instead its polygon is handed to **§1's QRA dispatcher as
  a RED accept zone**, so the enemy's existing alert fighters defend it. One
  interception system over that ground, not two.
* ``contested`` -- both sides hold airfields inside it. Neither side's claim is
  the truth about it, so §96 never enforces it and neither side's QRA claims
  it.

**Whether a country lets you through is derived from the same airfields** (DM
call, 2026-08-26): a country you fly from has plainly let you in, one both
sides fly from lets both through, and one you have no presence in has not. The
dated posture table used to answer this and no longer does -- it made consent a
fact about the calendar rather than about the campaign in front of you. It
survives as the source of each country's era-correct airframe, which nothing
else can supply. ``overflight:`` still overrides outright.

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
import math
from dataclasses import dataclass, field
from typing import Any, Optional

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
#: Both sides hold airfields inside this country: it is the battlefield, and
#: neither side is the truth about it. Measured on Able Archer 83, where Norway
#: -- the NATO host -- drew as enemy-red because the Soviets held two of its
#: three fields, and Finland the same. §96 never enforces a contested country;
#: nor does either side's QRA claim it, because the claim would be a lie.
CONTESTED_ALIGNED = "contested"
POSTURES = (NEUTRAL, BLUE_ALIGNED, RED_ALIGNED, CONTESTED_ALIGNED)


@dataclass(frozen=True)
class NeutralBorderZone:
    """One bordering country's airspace and what happens if you enter it."""

    #: Display name. A ``neutral`` zone spawns units, so its name must also be a
    #: pydcs country; an aligned zone spawns nothing and any name works.
    country: str
    #: pydcs plane id for the alert fighters (vanilla only). Neutral only.
    aircraft: str | None = None
    #: Altitude below which a crossing trips, or None for any altitude.
    #: **A floor is not a universal rule** (DM call, 2026-08-25): it means "high
    #: transit is tolerated", which is a judgement no fact on the map supports,
    #: so it is authored only -- it used to come from the posture table's
    #: `contested` bucket and went with it. None is the normal case, and it
    #: means no sanctuary at any height.
    floor_ft: Optional[int] = None
    #: An SA-6 point-defense battery, cloned on player escalation only.
    #: **Defaults on.** It was authored-only until 2026-08-28, and the terrain
    #: files that are now the only source of borders never set it -- so no
    #: shipped campaign could produce a SAM at all, while the setting text and
    #: the plugin description both promised one. Flown that day: escalation
    #: fired correctly and nothing woke, because the template was never built.
    #: A campaign may still turn it off per zone.
    sam: bool = True
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
    #: Author override for transit consent, or None to derive it from the
    #: airfields inside the border (see ``permits``). Resolved per side, so a
    #: country may be open to one bloc and closed to the other.
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

    def label_point(self) -> Optional[tuple[float, float]]:
        """Where the F10 map should write this country's name.

        The polygon's representative point, not its centroid: a country is
        usually concave (Norway spectacularly so) and a centroid lands in the
        sea or in the neighbour. shapely guarantees this one is inside.
        """
        from shapely.geometry import Polygon

        if len(self.border) < 3:
            return None
        try:
            point = Polygon(self.border).buffer(0).representative_point()
        except Exception:
            return None
        return (float(point.x), float(point.y))

    def posture_in(self, theater: Any) -> str:
        """This country's alignment: who owns the airfields inside its border.

        Counted over every zone of the same country, not this polygon alone: a
        country clipped into pieces is still one country. Russia is two zones on
        the Kola map, and per-piece counting drew Karelia -- 116,420 km2, the
        largest zone on the map -- as an uninvolved neutral that intercepts you,
        in a campaign where Russia is the enemy.

        Both sides holding airfields makes it contested, not one side's. It is
        the battlefield, and calling it red because red holds one more field
        than blue reports the front line as though it were allegiance.
        """
        if self.posture_override is not None:
            return self.posture_override
        blue, red = self.country_control_points(theater)
        if blue and red:
            return CONTESTED_ALIGNED
        if blue == 0 and red == 0:
            return NEUTRAL
        return BLUE_ALIGNED if blue else RED_ALIGNED

    def country_control_points(self, theater: Any) -> tuple[int, int]:
        """(blue, red) counts over every zone this country has on the map."""
        siblings = [
            zone
            for zone in getattr(theater, "neutral_border_zones", [])
            if zone.country == self.country
        ]
        if self not in siblings:
            siblings.append(self)
        blue = red = 0
        for zone in siblings:
            zone_blue, zone_red = zone.control_points_in(theater)
            blue += zone_blue
            red += zone_red
        return (blue, red)

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

    def permits(self, theater: Any, is_blue: bool, posture: str | None = None) -> bool:
        """Does this country let that side's aircraft transit?

        **Derived from the airbases inside its border** (DM call, 2026-08-26),
        the same fact that decides alignment: a country you fly from is a
        country that has let you in, and one you have no presence in has not.
        A country both sides operate from lets both through, because it plainly
        already does.

        The dated posture table used to answer this. It was dropped as the
        source because it made consent a fact about the calendar rather than
        about the campaign in front of you -- it read Sweden and Finland
        `closed` in 1983 while both sides flew combat sorties off their
        runways, and it cannot see a base changing hands. The research is kept
        (`resources/borders/national_postures.yaml`) and still picks each
        country's era-correct airframe, which nothing else can supply.

        A campaign's ``overflight:`` still wins outright.

        ``posture`` lets a caller that has already derived it hand it in.
        Deriving it means walking every zone on the map and testing every
        control point against a polygon, and the two natural callers both ask
        for the posture and the consent together -- so without this the map
        pays for it twice per zone and the generator three times. It is a
        parameter and deliberately NOT a cached field: the whole value of
        deriving posture is that a country flips the turn its airfield changes
        hands, and a stored one would go stale exactly then.
        """
        if self.overflight_override is not None:
            return self.overflight_override
        if posture is None:
            posture = self.posture_in(theater)
        if posture == CONTESTED_ALIGNED:
            return True
        if posture == NEUTRAL:
            return False
        return posture == (BLUE_ALIGNED if is_blue else RED_ALIGNED)

    def floor_for(self, theater: Any, is_blue: bool) -> Optional[int]:
        """Altitude below which a crossing trips, or None for any altitude.

        Authored only. A floor means "high transit is tolerated", which is a
        judgement no fact on the map supports -- it used to come from the
        posture table's `contested` bucket, and went with it.
        """
        return self.floor_ft

    def enforces_against(self, theater: Any, is_blue: bool) -> bool:
        """True when this border intercepts that side's aircraft.

        Only an uninvolved country does: one that hosts a side is handled by
        that side's QRA, one both sides use has already let them both in, and a
        country with nothing inside its border is nobody's business but its own.
        """
        posture = self.posture_in(theater)
        return posture == NEUTRAL and not self.permits(theater, is_blue, posture)

    def can_field_an_interceptor(self, day: Any) -> bool:
        """Could this country actually put a fighter up, on this date?

        A border that enforces needs somewhere to launch from and an airframe
        the era allows. 14 of the shipped zones have neither -- DCS models no
        Turkmenistan, and Cyprus, Armenia and Azerbaijan have no entry in the
        dated table -- so they are drawn and toothless.

        Asked here rather than in each consumer because the generator and the
        planning map both need it and used to answer it separately: the map
        drew Cyprus as "closed to you at any altitude" while the mission it
        generated let you fly straight through. Promising an interception the
        mission cannot deliver is worse than drawing no line at all.
        """
        if self.airfield is None and self.spawn is None:
            return False
        if self.aircraft is not None:
            return True
        from game.theater.nationalpostures import aircraft_for

        return aircraft_for(self.country, day) is not None

    def patrol_leg_end(
        self, anchor: tuple[float, float], length_m: float
    ) -> tuple[float, float] | None:
        """The far end of a racetrack leg from ``anchor`` that stays inside.

        A DCS Race-Track orbit flies between its waypoint and the *next* one.
        Flown 2026-08-29: with a one-waypoint route there is no leg, and all
        three patrol leaders flew into the ground inside 43 s (the wingmen
        followed them down to 1,000-3,800 m and pulled out once the lead was
        gone). Returns None for a country too thin to hold even a short leg;
        the caller orbits in a circle instead, which needs no second point.
        """
        from shapely.geometry import LineString, Polygon

        if len(self.border) < 3:
            return None
        polygon = Polygon(self.border)
        if not polygon.is_valid:
            polygon = polygon.buffer(0)
        best: tuple[float, tuple[float, float]] | None = None
        for degrees in range(0, 360, 30):
            radians = math.radians(degrees)
            for scale in (1.0, 0.6, 0.35):
                end = (
                    anchor[0] + length_m * scale * math.cos(radians),
                    anchor[1] + length_m * scale * math.sin(radians),
                )
                if not polygon.contains(LineString([anchor, end])):
                    continue
                if best is None or scale > best[0]:
                    best = (scale, end)
                break
        return None if best is None else best[1]

    def origin_label(self, posture: str, enforced: bool = True) -> str:
        """What the map tooltip calls this border's meaning."""
        if posture == BLUE_ALIGNED:
            return "friendly — overflight permitted"
        if posture == RED_ALIGNED:
            return "enemy-aligned"
        if posture == CONTESTED_ALIGNED:
            return "contested — both sides hold ground here"
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
                sam=bool(data.get("sam", True)),
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
