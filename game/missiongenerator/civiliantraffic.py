"""Civilian background air traffic, planned in Python and spawned via pydcs.

This replaces the old MOOSE ``RAT`` plugin (``resources/plugins/civilian_traffic``).
RAT is a heavyweight "living airfield" engine (ATC, respawn scheduler, runway-retry,
heliport-id resolution) and the civilian layer only ever wanted a handful of ambient
flights -- so it switched almost all of RAT off and still inherited RAT's crash
surface (the recurring ``woCharacterHuman`` / GermanyCW-FARP sim crashes came from
RAT resolving an unresolvable *heliport id* and spawning a malformed unit, which is
why the rotary layer had to be disabled entirely).

**Revisited 2026-08-05 and RAT stays retired.** It was reopened as "I think RAT is
the real answer" and closed the other way in the same conversation, for two reasons
worth keeping written down: RAT was never cut on taste (it crashed the sim, above),
and it does not fix what is actually wrong. Pressed on the symptom, the DM named the
two real issues as **civil identity** and **airways vs milk runs** -- RAT addresses
neither (it would not make an An-26 read as an airliner), and its one genuine
differentiator, ATC / living airfield, was explicitly not among the complaints.

So the rebuild stayed here, and fixed those two things:

**1. Civil identity is a data table** -- see ``civilianfleet.py``. The roster used to
be applied globally, so Antonovs and Hips flew over Nevada and the Marianas; worse,
modern civil traffic flew over 1944 Normandy. Fleet, operator names and cruise levels
are now chosen per region.

**2. Airways, not milk runs.** Each civilian used to fly a chain of five short
rear-area legs and land -- a meander that existed ONLY to keep the aircraft airborne
long enough to cover a mission without a respawn loop. Real civil traffic flies
straight, high, and across. Routes are now single long transits at a realistic
flight level, which is cheaper, more realistic, terrain-safe by construction, and
almost certainly fixes the third complaint ("too little / it disappears") on its own:
low-level traffic pottering between rear fields is *invisible* to a player at
altitude, so the felt sparsity was substantially a visibility problem.

**Why the endpoint pool could safely widen.** The old code drew endpoints only from
airfields Retribution does not control, which collapses the pool on maps where the
engine owns everything. For an *overflight* the endpoints are only direction anchors
-- the aircraft air-starts en route at cruise and never touches either one -- so the
neutral pool is now a preference rather than a hard requirement, with any airfield
used as a fallback when too few neutral ones exist to draw a transit.

Traffic remains invisible to AI (never targeted, never affects combat) with
weapon-hold ROE, under the neutral coalition.

**Speeds go to pydcs in km/h** (2026-08-08). Every pydcs speed argument --
``flight_group_inflight``, ``FlyingGroup.add_waypoint``, ``ShipGroup.add_waypoint`` --
is km/h and divides by 3.6 internally to get the m/s DCS stores. This module planned
in m/s and passed the raw number, so a third of the intended speed was written: the
air-started fleet spawned at 65-110 kt at FL200-FL310 and fell out of the sky, the
same failure the QRA scramble hit when Moose air-spawned its jets at ~0 kt
(``resources/plugins/intercept/intercept-config.lua``, SCRAMBLE_SPEED_KT). The
``CRUISE_PROFILE`` table stays in m/s -- it is the honest unit for a cruise level --
and every pydcs call converts with ``mps(...).kph``, which is what the rest of the
generator already does (``knots(12).kph``, ``speed.kph``).

**A transit is anchored at its flight level** (2026-08-08, found while fixing the
above). "Airways, not milk runs" removed the intermediate legs, and nothing replaced
them: a two-field route's ``chain[1:-1]`` is empty, so a ground start was written as
takeoff -> ``land_at`` with no waypoint carrying the cruise altitude at all. DCS flew
the shallow V that implies and the aircraft never climbed to its assigned level --
which defeats the point of choosing per-region flight levels for the ~30% of
fixed-wing traffic that departs from a field. Two-field routes now get synthesised
top-of-climb / top-of-descent waypoints (``CRUISE_ENTRY_FRAC`` / ``CRUISE_EXIT_FRAC``);
air starts are already at cruise and take only the descent point. The rotary layer is
unchanged -- it routes through real fields and always had waypoints.
"""

from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Sequence, Type

from dcs.mapping import Point
from dcs.mission import StartType
from dcs.task import OptROE, SetInvisibleCommand
from dcs.unittype import FlyingType, ShipType

from pydcs_extensions.vietnamwarvessels.vietnamwarvessels import (
    vwv_junk,
    vwv_sampan_canopy,
    vwv_sampan_covered,
    vwv_sampan_covered_ak47,
    vwv_sampan_open,
    vwv_sampan_open_box,
)

from game.utils import mps

from .civilianfleet import CRUISE_PROFILE, CivilRegion, region_for

if TYPE_CHECKING:
    from dcs.country import Country
    from dcs.mission import Mission
    from game.factions.faction import Faction
    from game.game import Game

# ── Routing knobs ─────────────────────────────────────────────────────────────
KEEPOUT_M = 75_000  # ~40 NM bubble around each active front; civilians avoid it.
#: An airway has to actually cross something to read as a transit rather than a hop.
MIN_TRANSIT_M = 150_000  # ~80 NM
#: Rotary traffic is local by nature -- a helicopter does not fly an airway.
HELO_MAXDIST_M = 130_000  # ~70 NM
STRAY_CHANCE = 0.08  # chance a field inside the keep-out is kept anyway
#: Departures are spread across this window so the sky fills over the mission rather
#: than all at once.
STAGGER_WINDOW_S = 6_600  # 110 min
#: Most airway traffic air-starts at cruise: pop-in at FL200+ is unobtrusive and
#: terrain-safe, and it means transits exist from mission start instead of taking an
#: hour to climb into view. A few ground-start so departures are visible too.
AIR_START_FRACTION = 0.7
#: Only types cruising at/above this MSL altitude may air-start.
AIR_START_MIN_ALT_M = 3_000
#: Where along the transit an air start drops in, so a fleet is spread down the airway
#: instead of stacked over one field. Must stay below ``CRUISE_EXIT_FRAC``.
AIR_START_FRAC_RANGE = (0.15, 0.85)
#: Where a transit reaches and leaves its cruise level. A two-field airway carries no
#: intermediate field by design, so without these it has NO waypoint between the
#: takeoff and the landing: a ground-started civilian flew a shallow
#: takeoff-to-touchdown V and never reached its assigned flight level at all. These
#: anchor the level explicitly -- top of climb, then top of descent.
#:
#: The entry fraction sets where DCS *wants* the aircraft level, not the climb
#: gradient it can manage: an An-26 needs ~90 km to make FL200 and will simply keep
#: climbing toward the next waypoint, which is at the same altitude. Air starts are
#: already at cruise and take only the exit point.
CRUISE_ENTRY_FRAC = 0.25
CRUISE_EXIT_FRAC = 0.9

FLEET_DENSITY = (1, 3)  # per fixed-wing type, scaled by pool size
HELO_DENSITY = (1, 2)
HELO_LEGS = 2  # a short local hop, not a meander


@dataclass(frozen=True)
class _Field:
    """An airfield usable as a civilian route endpoint."""

    name: str
    point: Point


@dataclass(frozen=True)
class CivilianRoute:
    """One planned civilian flight."""

    aircraft_type: Type[FlyingType]
    chain: tuple[_Field, ...]  # >= 2 fields; [0] is departure, [-1] is landing
    air_start: bool
    air_start_point: Optional[Point]  # set iff air_start (partway along the route)
    altitude_m: int
    speed_ms: int
    radio_alt: bool
    start_time_s: int
    is_helo: bool
    callsign: str  # the operator + flight number the map shows


def _neutral_country(mission: "Mission") -> "Optional[Country]":
    countries = list(mission.coalition["neutrals"].countries.values())
    return countries[0] if countries else None


def _dist2(a: Point, b: Point) -> float:
    dx = a.x - b.x
    dy = a.y - b.y
    return dx * dx + dy * dy


def along(a: Point, b: Point, frac: float) -> Point:
    """The point ``frac`` of the way from ``a`` to ``b``."""
    return Point(a.x + (b.x - a.x) * frac, a.y + (b.y - a.y) * frac, a._terrain)


def cruise_fracs(air_start: bool) -> tuple[float, ...]:
    """Where along a two-field transit the cruise-level waypoints go.

    A ground start needs both: climb to level, hold it, then descend for the landing.
    An air start spawns at cruise already, so it only needs the top of descent --
    which is why ``AIR_START_FRAC_RANGE`` must stay below ``CRUISE_EXIT_FRAC``, or the
    aircraft would be told to fly backwards up its own airway.
    """
    if air_start:
        return (CRUISE_EXIT_FRAC,)
    return (CRUISE_ENTRY_FRAC, CRUISE_EXIT_FRAC)


def _in_combat_zone(point: Point, fronts: Sequence[Point]) -> bool:
    keepout2 = KEEPOUT_M * KEEPOUT_M
    return any(_dist2(point, f) <= keepout2 for f in fronts)


def admit_field(point: Point, fronts: Sequence[Point], rng: random.Random) -> bool:
    """Fields clear of the front always qualify; a field inside the keep-out bubble
    qualifies only on a rare stray roll, so the front stays mostly clear but is not
    perfectly sterile."""
    if not _in_combat_zone(point, fronts):
        return True
    return rng.random() < STRAY_CHANCE


def prune_to_reachable(fields: Sequence[_Field], cap_m: float) -> list[_Field]:
    """Drop any field with no *other* field within ``cap_m``, repeating until stable,
    so every survivor is guaranteed at least one valid leg within the cap."""
    cap2 = cap_m * cap_m
    kept = list(fields)
    changed = True
    while changed:
        changed = False
        next_kept = []
        for i, a in enumerate(kept):
            if any(
                i != j and _dist2(a.point, b.point) <= cap2 for j, b in enumerate(kept)
            ):
                next_kept.append(a)
            else:
                changed = True
        kept = next_kept
    return kept


def density(pool_size: int, lo: int, hi: int) -> int:
    """Flights-per-type scaled to pool size, clamped to ``[lo, hi]``."""
    n = -(-pool_size * 15 // 100)  # ceil(pool_size * 0.15)
    return max(lo, min(hi, n))


def airway_pairs(pool: Sequence[_Field], min_transit_m: float) -> list[tuple[int, int]]:
    """Index pairs far enough apart to be a transit rather than a local hop.

    This is the whole of "airways, not milk runs": instead of walking a chain of short
    reachable legs, pick two endpoints that are genuinely distant and fly the straight
    line between them.
    """
    min2 = min_transit_m * min_transit_m
    return [
        (i, j)
        for i in range(len(pool))
        for j in range(i + 1, len(pool))
        if _dist2(pool[i].point, pool[j].point) >= min2
    ]


def _flight_number(rng: random.Random) -> int:
    return rng.randint(100, 999)


def plan_airways(
    pool: Sequence[_Field],
    region: CivilRegion,
    per_type: tuple[int, int],
    rng: random.Random,
    min_transit_m: float = MIN_TRANSIT_M,
) -> list[CivilianRoute]:
    """Plan the fixed-wing overflight layer: straight, high, long transits.

    Falls back to the longest pairs available when no pair clears ``min_transit_m``
    (a small map, or a heavily pruned pool), so a cramped theatre still gets traffic
    rather than silently getting none.
    """
    if len(pool) < 2 or not region.fleet:
        return []

    pairs = airway_pairs(pool, min_transit_m)
    if not pairs:
        # No true transit available -- take the longest legs the map can offer.
        pairs = sorted(
            ((i, j) for i in range(len(pool)) for j in range(i + 1, len(pool))),
            key=lambda p: _dist2(pool[p[0]].point, pool[p[1]].point),
            reverse=True,
        )[:8]
    if not pairs:
        return []

    count = density(len(pool), *per_type)
    routes: list[CivilianRoute] = []
    for aircraft_type in region.fleet:
        profile = CRUISE_PROFILE.get(aircraft_type)
        if profile is None:
            continue
        altitude_m, speed_ms, radio_alt = profile
        air_eligible = altitude_m >= AIR_START_MIN_ALT_M and not radio_alt
        for _ in range(count):
            i, j = rng.choice(pairs)
            start, end = pool[i], pool[j]
            if rng.random() < 0.5:  # fly the airway in either direction
                start, end = end, start

            air = air_eligible and rng.random() < AIR_START_FRACTION
            air_point: Optional[Point] = None
            start_time = 0
            if air:
                # Somewhere along the transit, so a fleet is spread down the airway
                # instead of stacked over one field.
                air_point = along(
                    start.point, end.point, rng.uniform(*AIR_START_FRAC_RANGE)
                )
            else:
                start_time = rng.randint(0, STAGGER_WINDOW_S)

            operator = rng.choice(region.operators) if region.operators else "CIVIL"
            routes.append(
                CivilianRoute(
                    aircraft_type=aircraft_type,
                    chain=(start, end),
                    air_start=air,
                    air_start_point=air_point,
                    altitude_m=altitude_m,
                    speed_ms=speed_ms,
                    radio_alt=radio_alt,
                    start_time_s=start_time,
                    is_helo=False,
                    callsign=f"{operator} {_flight_number(rng)}",
                )
            )
    return routes


def plan_local_rotary(
    pool: Sequence[_Field],
    region: CivilRegion,
    per_type: tuple[int, int],
    rng: random.Random,
    cap_m: float = HELO_MAXDIST_M,
) -> list[CivilianRoute]:
    """Plan the rotary layer: short local hops, low and on AGL.

    Helicopters deliberately do NOT fly airways -- local work between nearby fields is
    what civil rotary traffic actually is, so the milk-run rewrite does not apply here.
    """
    reachable = prune_to_reachable(pool, cap_m)
    if len(reachable) < 2 or not region.helos:
        return []

    cap2 = cap_m * cap_m
    count = density(len(reachable), *per_type)
    routes: list[CivilianRoute] = []
    for aircraft_type in region.helos:
        profile = CRUISE_PROFILE.get(aircraft_type)
        if profile is None:
            continue
        altitude_m, speed_ms, radio_alt = profile
        for _ in range(count):
            start = rng.choice(reachable)
            options = [
                f
                for f in reachable
                if f is not start and _dist2(start.point, f.point) <= cap2
            ]
            if not options:
                continue
            chain = [start]
            current = start
            for _ in range(HELO_LEGS):
                nxt = [
                    f
                    for f in reachable
                    if f is not current and _dist2(current.point, f.point) <= cap2
                ]
                if not nxt:
                    break
                current = rng.choice(nxt)
                chain.append(current)
            if len(chain) < 2:
                continue

            operator = rng.choice(region.operators) if region.operators else "CIVIL"
            routes.append(
                CivilianRoute(
                    aircraft_type=aircraft_type,
                    chain=tuple(chain),
                    air_start=False,
                    air_start_point=None,
                    altitude_m=altitude_m,
                    speed_ms=speed_ms,
                    radio_alt=radio_alt,
                    start_time_s=rng.randint(0, STAGGER_WINDOW_S),
                    is_helo=True,
                    callsign=f"{operator} {_flight_number(rng)}",
                )
            )
    return routes


def loiter_chain(
    anchor: Point, radius_m: float, n_legs: int, rng: random.Random
) -> tuple[Point, ...]:
    """A small, irregular loop of points around ``anchor``, each leg within
    ``radius_m``, for slow ambient traffic that never strays far from its anchor."""
    base_angle = rng.uniform(0, 2 * math.pi)
    points = []
    for i in range(n_legs):
        angle = base_angle + i * (2 * math.pi / n_legs) + rng.uniform(-0.3, 0.3)
        r = radius_m * rng.uniform(0.4, 1.0)
        points.append(
            Point(
                anchor.x + r * math.cos(angle),
                anchor.y + r * math.sin(angle),
                anchor._terrain,
            )
        )
    return tuple(points)


class CivilianTrafficGenerator:
    """Plans and spawns the civilian background-traffic layer into the mission."""

    def __init__(
        self, mission: Mission, game: Game, rng: Optional[random.Random] = None
    ) -> None:
        self.mission = mission
        self.game = game
        self.rng = rng or random.Random()

    def region(self) -> CivilRegion:
        return region_for(getattr(self.mission.terrain, "name", ""))

    def route_fields(self) -> list[_Field]:
        """Airfields usable as route endpoints, admitted past the front keep-out.

        Prefers airfields Retribution does not control -- a civil flight plan should
        not read as using an active military base -- but falls back to every admitted
        airfield when too few neutral ones remain to draw a transit. That fallback is
        the fix for maps where the engine owns nearly every field and the neutral pool
        collapsed to nothing; for an overflight the endpoints are only direction
        anchors, since the aircraft air-starts en route and never touches either.
        """
        controlled = {
            cp.dcs_airport.name
            for cp in self.game.theater.controlpoints
            if cp.dcs_airport is not None
        }
        fronts = [
            Point(front.position.x, front.position.y, self.mission.terrain)
            for front in self.game.theater.conflicts()
        ]
        neutral: list[_Field] = []
        every: list[_Field] = []
        for name, airport in self.mission.terrain.airports.items():
            if not admit_field(airport.position, fronts, self.rng):
                continue
            field = _Field(name=name, point=airport.position)
            every.append(field)
            if name not in controlled:
                neutral.append(field)
        return neutral if len(neutral) >= 2 else every

    def _neutral_country(self) -> "Optional[Country]":
        return _neutral_country(self.mission)

    def generate(self) -> None:
        if not self.game.settings.civilian_air_traffic:
            logging.info("Civilian air traffic disabled by settings")
            return
        region = self.region()
        if not region.fleet and not region.helos:
            # A theatre with no plausible civil traffic (the WWII maps). Deliberate.
            logging.info(
                "Civilian air traffic: no civil fleet for this theatre — skipping"
            )
            return
        country = self._neutral_country()
        if country is None:
            logging.warning("No neutral country available — skipping civilian traffic")
            return

        pool = self.route_fields()
        routes = plan_airways(
            pool, region, FLEET_DENSITY, self.rng
        ) + plan_local_rotary(pool, region, HELO_DENSITY, self.rng)

        spawned = sum(
            1 for idx, route in enumerate(routes) if self._spawn(country, idx, route)
        )
        logging.info(
            "Civilian traffic: %d flights (%d airway, %d rotary) from a %d-field pool",
            spawned,
            sum(1 for r in routes if not r.is_helo),
            sum(1 for r in routes if r.is_helo),
            len(pool),
        )

    def cruise_points(self, route: CivilianRoute) -> list[Point]:
        """The waypoints that hold a route at its cruise level, between the start and
        the ``land_at``.

        The rotary layer routes through real intermediate fields, so those are the
        points. An airway has none by design -- two endpoints and the straight line
        between them -- which left a ground-started transit with no waypoint at all
        between takeoff and landing, so it flew a shallow V and never reached its
        flight level. Those get a synthesised top-of-climb / top-of-descent pair
        instead.
        """
        if len(route.chain) > 2:
            return [field.point for field in route.chain[1:-1]]

        start, end = route.chain[0].point, route.chain[-1].point
        return [along(start, end, frac) for frac in cruise_fracs(route.air_start)]

    def _spawn(self, country: "Country", idx: int, route: CivilianRoute) -> bool:
        # The callsign IS the identity a player sees on the F10 map; the index keeps
        # group names unique when two flights draw the same operator and number.
        name = f"{route.callsign} [{idx}]"
        try:
            if route.air_start:
                assert route.air_start_point is not None
                # km/h: pydcs writes speed/3.6 onto both the spawned unit records
                # (the actual air-start velocity) and the first waypoint. Passing
                # m/s here spawned the transit at a third of cruise -- a stall.
                group = self.mission.flight_group_inflight(
                    country=country,
                    name=name,
                    aircraft_type=route.aircraft_type,
                    position=route.air_start_point,
                    altitude=route.altitude_m,
                    speed=mps(route.speed_ms).kph,
                    group_size=1,
                )
            else:
                departure = self.mission.terrain.airports.get(route.chain[0].name)
                if departure is None:
                    return False
                group = self.mission.flight_group_from_airport(
                    country=country,
                    name=name,
                    aircraft_type=route.aircraft_type,
                    airport=departure,
                    start_type=StartType.Runway,
                    group_size=1,
                )

            # Everything between the start and land_at, at the route's cruise level.
            for point in self.cruise_points(route):
                waypoint = group.add_waypoint(
                    point, route.altitude_m, mps(route.speed_ms).kph
                )
                if route.radio_alt:
                    waypoint.alt_type = "RADIO"

            destination = self.mission.terrain.airports.get(route.chain[-1].name)
            if destination is not None:
                group.land_at(destination)

            group.start_time = route.start_time_s
            group.points[0].tasks.append(OptROE(OptROE.Values.WeaponHold))
            group.points[0].tasks.append(SetInvisibleCommand(True))
        except Exception:  # pragma: no cover - defensive; never block generation
            logging.exception("Failed to spawn civilian flight %s", name)
            return False
        return True


# ── Naval civilian traffic (Sampans/Junks) ──────────────────────────────────────
# Only spawned when the campaign's faction requirements call for Vietnam War Vessels
# (see _faction_requires_vwv) -- these hulls don't exist outside that mod. Real-world
# top speed for both hull families is ~1-2 m/s, so unlike the air transits these never
# leave the immediate vicinity of their anchor; a tight loiter near a known-water point
# (a carrier/LHA control point) is realistic and avoids needing real water pathfinding.
NAVAL_TYPES: tuple[Type[ShipType], ...] = (
    vwv_junk,
    vwv_sampan_open,
    vwv_sampan_canopy,
    vwv_sampan_covered,
    vwv_sampan_covered_ak47,
    vwv_sampan_open_box,
)
NAVAL_SPEED_MS = 1.5  # matches the mod's own ~1-2 m/s hull speeds
NAVAL_LOITER_RADIUS_M = 1_500  # tight loiter around the anchor
NAVAL_LOITER_LEGS = 3  # waypoints in the loiter chain, excluding the anchor itself
NAVAL_PER_ANCHOR = (1, 2)  # min/max boats spawned per coastal anchor


def _faction_requires_vwv(faction: "Faction") -> bool:
    return any("vietnam war vessels" in key.lower() for key in faction.requirements)


@dataclass(frozen=True)
class NavalRoute:
    """One planned ambient boat: a slow loiter loop around a coastal anchor."""

    ship_type: Type[ShipType]
    chain: tuple[Point, ...]


class NavalCivilianTrafficGenerator:
    """Plans and spawns ambient Sampans/Junks near coastal control points.

    Only runs when a faction's requirements call for Vietnam War Vessels -- these hulls
    are mod-only and otherwise unavailable. See ``CivilianTrafficGenerator`` for the air
    traffic layer this complements.
    """

    def __init__(
        self, mission: Mission, game: Game, rng: Optional[random.Random] = None
    ) -> None:
        self.mission = mission
        self.game = game
        self.rng = rng or random.Random()

    def _vwv_available(self) -> bool:
        return _faction_requires_vwv(self.game.blue.faction) or _faction_requires_vwv(
            self.game.red.faction
        )

    def coastal_anchors(self) -> list[Point]:
        """Carrier/LHA control points: the only theater positions guaranteed to be
        navigable water, so no separate water-pathfinding is needed."""
        return [
            cp.position
            for cp in self.game.theater.controlpoints
            if cp.is_carrier or cp.is_lha
        ]

    def generate(self) -> None:
        if not self._vwv_available():
            return

        country = _neutral_country(self.mission)
        if country is None:
            logging.warning(
                "No neutral country available — skipping naval civilian traffic"
            )
            return

        anchors = self.coastal_anchors()
        routes: list[NavalRoute] = []
        for anchor in anchors:
            count = self.rng.randint(*NAVAL_PER_ANCHOR)
            for _ in range(count):
                ship_type = self.rng.choice(NAVAL_TYPES)
                chain = loiter_chain(
                    anchor, NAVAL_LOITER_RADIUS_M, NAVAL_LOITER_LEGS, self.rng
                )
                routes.append(NavalRoute(ship_type=ship_type, chain=chain))

        spawned = sum(
            1 for idx, route in enumerate(routes) if self._spawn(country, idx, route)
        )
        logging.info(
            "Naval civilian traffic: %d boats near %d coastal anchor(s)",
            spawned,
            len(anchors),
        )

    def _spawn(self, country: "Country", idx: int, route: NavalRoute) -> bool:
        name = f"CIV_{route.ship_type.id}_{idx}"
        try:
            group = self.mission.ship_group(
                country=country,
                name=name,
                _type=route.ship_type,
                position=route.chain[0],
                group_size=1,
            )
            for point in route.chain[1:]:
                # km/h, as above -- the raw m/s value crawled the hulls at ~0.8 kt.
                group.add_waypoint(point, mps(NAVAL_SPEED_MS).kph)

            group.points[0].tasks.append(OptROE(OptROE.Values.WeaponHold))
            group.points[0].tasks.append(SetInvisibleCommand(True))
        except Exception:  # pragma: no cover - defensive; never block generation
            logging.exception("Failed to spawn naval civilian traffic %s", name)
            return False
        return True
