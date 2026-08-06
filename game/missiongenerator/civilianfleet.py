"""Region-appropriate civil fleets, operators and cruise levels.

The civilian layer's identity problem, in the DM's words: "civil identity is a data
table -- liveries + airline callsigns + cruise levels do nearly all the perceptual
work", and the shipped roster "leans Soviet-military -- An-26 / IL-76 / Mi-8 read
*wrong* over Germany or the Gulf. **Region-appropriate selection matters more than
adding types.**"

That is the whole of this module: which airframes are plausible civil traffic where,
who is flying them, and how high. It is deliberately data, not logic -- adding a map
or re-crewing a region is an edit here and nothing else.

Two findings from building it, both worse than "the roster leans Soviet":

* The previous roster was applied **globally**, so Antonovs and Hips flew over Nevada
  and the Marianas as readily as over the Caucasus. The Soviet set is not wrong --
  it is *right* for the Caucasus, Kola, Afghanistan, Syria and Iraq, where Antonov
  and Ilyushin freighters genuinely are the civil traffic. It was wrong everywhere
  else, which is a selection bug, not a roster bug.

* **The WWII maps had modern civil traffic on them.** Normandy and The Channel are
  1944; a Yak-40 or an IL-76 crossing the beachhead is not a small immersion
  problem. Those regions field nothing at all (`CIVIL_TRAFFIC_NONE`) -- a 1944 combat
  theatre had no civil overflights worth modelling, so the honest answer is an empty
  fleet rather than a period-costume one.

DCS ships no airliner, so nothing here will ever read as a scheduled 737. The goal is
narrower and achievable: the aircraft crossing your map should be one that plausibly
flies in that part of the world, under a plausible operator's name, at a plausible
flight level.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Type

from dcs.helicopters import Mi_8MT, Mi_26, SA342M, UH_1H
from dcs.planes import An_26B, An_30M, C_130, IL_76MD, Yak_40, Yak_52
from dcs.unittype import FlyingType

#: Cruise profile per type: (altitude m MSL, speed m/s, fly_on_agl).
#:
#: Levels are the realistic band for the airframe rather than the old flat 5,000 m --
#: a freighter transiting at FL260 reads as overflight traffic, the same jet pottering
#: at 16,000 ft reads as something military and interesting. Light props and helos stay
#: low and fly AGL so they clear terrain.
CRUISE_PROFILE: dict[Type[FlyingType], tuple[int, int, bool]] = {
    Yak_40: (7_900, 150, False),  # ~FL260, regional trijet
    IL_76MD: (9_400, 200, False),  # ~FL310, heavy freighter
    An_26B: (6_100, 120, False),  # ~FL200, turboprop freighter
    An_30M: (6_100, 120, False),  # ~FL200, survey turboprop
    C_130: (7_000, 140, False),  # ~FL230
    Yak_52: (900, 50, True),  # light prop, local
    Mi_8MT: (300, 50, True),
    UH_1H: (300, 50, True),
    SA342M: (350, 55, True),
    Mi_26: (400, 55, True),
}


@dataclass(frozen=True)
class CivilRegion:
    """The civil air picture for one part of the world."""

    #: Fixed-wing types that fly the region's airways.
    fleet: tuple[Type[FlyingType], ...]
    #: Rotary types working locally. Helicopters do not fly airways -- short local
    #: hops are what rotary civil traffic actually does.
    helos: tuple[Type[FlyingType], ...]
    #: Operator names used to label the traffic. These are what a player sees on the
    #: F10 map, and they are the cheapest half of "civil identity" by a distance:
    #: `AEROFLOT 412` reads as an airliner where `CIV_An-26B_3` reads as a bug.
    operators: tuple[str, ...]


#: A theatre with no plausible civil overflight traffic at all.
CIVIL_TRAFFIC_NONE = CivilRegion(fleet=(), helos=(), operators=())

_SOVIET_SPHERE = CivilRegion(
    fleet=(Yak_40, An_26B, An_30M, IL_76MD),
    helos=(Mi_8MT, Mi_26),
    operators=("AEROFLOT", "VOLGA AIR", "POLET", "URAL CARGO", "ARKTIKA"),
)

_CENTRAL_ASIA = CivilRegion(
    fleet=(An_26B, IL_76MD, Yak_40),
    helos=(Mi_8MT, Mi_26),
    operators=("ARIANA", "KAM AIR", "SILK ROUTE", "PAMIR CARGO"),
)

_LEVANT = CivilRegion(
    fleet=(An_26B, IL_76MD, Yak_40, C_130),
    helos=(Mi_8MT, SA342M),
    operators=("CHAM WINGS", "LEVANT CARGO", "CEDAR AIR", "PALMYRA"),
)

_GULF = CivilRegion(
    fleet=(IL_76MD, An_26B, C_130, Yak_40),
    helos=(Mi_8MT, SA342M),
    operators=("GULF FREIGHT", "KISH AIR", "DUBAI CARGO", "HORMUZ AIR"),
)

_WESTERN = CivilRegion(
    fleet=(C_130, Yak_52),
    helos=(UH_1H, SA342M),
    operators=("SKYWEST", "GRAND CANYON AIR", "PACIFIC FREIGHT", "DESERT AIR"),
)

_COLD_WAR_EUROPE = CivilRegion(
    # A divided Germany is genuinely mixed: Interflug flew Antonovs and Tupolevs in
    # the east while western civil traffic was Boeing/Airbus, which DCS does not ship
    # -- so the eastern half of the picture is what can honestly be rendered, plus
    # military transport traffic that belongs on either side of the line.
    fleet=(An_26B, IL_76MD, Yak_40, C_130),
    helos=(Mi_8MT, UH_1H),
    operators=("INTERFLUG", "LOT CARGO", "BALKAN AIR", "MALEV"),
)

#: Keyed by ``dcs.terrain.Terrain.name``. An unknown map falls back to the Soviet
#: sphere, which is the shipped behaviour and the safest default -- those airframes
#: exist on every DCS install, so a new terrain never generates nothing by surprise.
REGIONS: dict[str, CivilRegion] = {
    "Caucasus": _SOVIET_SPHERE,
    "Kola": _SOVIET_SPHERE,
    "Afghanistan": _CENTRAL_ASIA,
    "Syria": _LEVANT,
    "Iraq": _LEVANT,
    "SinaiMap": _GULF,
    "PersianGulf": _GULF,
    "Nevada": _WESTERN,
    "MarianaIslands": _WESTERN,
    "Falklands": _WESTERN,
    "GermanyCW": _COLD_WAR_EUROPE,
    # 1944. Modern civil traffic over the beachhead is an anachronism, not flavour.
    "Normandy": CIVIL_TRAFFIC_NONE,
    "TheChannel": CIVIL_TRAFFIC_NONE,
}

DEFAULT_REGION = _SOVIET_SPHERE


def region_for(terrain_name: str) -> CivilRegion:
    """The civil air picture for a terrain, by ``Terrain.name``."""
    return REGIONS.get(terrain_name, DEFAULT_REGION)
