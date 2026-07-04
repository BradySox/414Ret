"""Civilian background air traffic, planned in Python and spawned via pydcs.

This replaces the old MOOSE ``RAT`` plugin (``resources/plugins/civilian_traffic``).
RAT is a heavyweight "living airfield" engine (ATC, respawn scheduler, runway-retry,
heliport-id resolution) and the civilian layer only ever wanted a handful of ambient
flights -- so it switched almost all of RAT off and still inherited RAT's crash
surface (the recurring ``woCharacterHuman`` / GermanyCW-FARP sim crashes came from
RAT resolving an unresolvable *heliport id* and spawning a malformed unit, which is
why the rotary layer had to be disabled entirely).

Here the campaign engine -- which already knows every airfield, its coalition and
position, and the front line -- plans the routes itself. The geometry (neutral pool,
front keep-out, reachable-neighbour pairing, multi-leg chaining, density) is ordinary
Python that CI can test instead of "fly it and hope".

Design (see PR discussion):
- **Multi-leg milk runs.** Each civilian flies a chain of short rear-area legs and
  lands at the end, so it stays airborne ~1-1.5 h and a *staggered* fleet keeps the
  map occupied across a long (2 h) mission **without any respawn loop** -- the respawn
  churn was the other RAT crash path.
- **Hybrid spawn.** A few high-cruising heavies **air-start** at t=0 for instant
  presence (at altitude, where pop-in is unobtrusive and terrain-safe); everything
  else -- all helos and light props -- **ground/runway-starts** at a neutral airdrome
  and climbs out for real (no pop-in). Crucially this is *not* RAT: a plain pydcs
  ground-start at a real airdrome is what the old template code did safely; the crash
  was RAT cloning onto *heliports*, which never happens here.
- Low flyers (helos, light props) route on **RADIO (AGL) altitude** so they stay low
  without clipping terrain. Traffic is invisible to AI (never targeted, never affects
  combat) with weapon-hold ROE, under the neutral coalition.
"""

from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Sequence, Type

from dcs.helicopters import Mi_8MT, SA342M, UH_1H
from dcs.mapping import Point
from dcs.mission import StartType
from dcs.planes import An_26B, C_130, Yak_40, Yak_52
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

if TYPE_CHECKING:
    from dcs.country import Country
    from dcs.mission import Mission
    from game.factions.faction import Faction
    from game.game import Game

# ── Routing knobs ─────────────────────────────────────────────────────────────
KEEPOUT_M = 75_000  # ~40 NM bubble around each active front; civilians avoid it.
FW_MAXDIST_M = 280_000  # fixed-wing per-leg cap (~150 NM)
HELO_MAXDIST_M = 130_000  # rotary per-leg cap (~70 NM)
STRAY_CHANCE = 0.08  # chance a field inside the keep-out is kept anyway
# Ground departures are spread across this window so a multi-leg fleet keeps the map
# occupied through a long mission (each flight is airborne ~1-1.5 h).
STAGGER_WINDOW_S = 6_600  # 110 min
FW_LEGS = 5  # legs per fixed-wing milk run
HELO_LEGS = 4  # legs per rotary milk run
AIR_START_PER_TYPE = 1  # heavies air-started at t=0 for instant presence
# Only types cruising at/above this MSL altitude are eligible to air-start (so the
# pop-in is high and terrain-safe); everything lower ground-starts and climbs.
AIR_START_MIN_ALT_M = 3_000

# Per aircraft type: (altitude, speed m/s, radio_alt). ``radio_alt`` flies the route
# on AGL altitude (low flyers stay low without clipping terrain); heavies cruise on
# barometric/MSL altitude where the value is high enough to clear rear-area terrain.
_PROFILE: dict[Type[FlyingType], tuple[int, int, bool]] = {
    C_130: (5_000, 140, False),
    An_26B: (5_000, 120, False),
    Yak_40: (6_000, 150, False),  # civilian regional trijet; air-start-eligible cruiser
    Yak_52: (400, 50, True),
    Mi_8MT: (200, 50, True),
    UH_1H: (200, 50, True),
    SA342M: (250, 55, True),
}
FW_TYPES: tuple[Type[FlyingType], ...] = (C_130, An_26B, Yak_40, Yak_52)
HELO_TYPES: tuple[Type[FlyingType], ...] = (Mi_8MT, UH_1H, SA342M)

# ── Naval civilian traffic (Sampans/Junks) ──────────────────────────────────────
# Only spawned when the campaign's faction requirements call for Vietnam War Vessels
# (see _faction_requires_vwv) -- these hulls don't exist outside that mod. Real-world
# top speed for both hull families is ~1-2 m/s, so unlike the air milk runs these never
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


@dataclass(frozen=True)
class _Field:
    """A neutral airfield available as a civilian route endpoint."""

    name: str
    point: Point


@dataclass(frozen=True)
class CivilianRoute:
    """One planned civilian flight: a chain of neutral fields it flies and lands at."""

    aircraft_type: Type[FlyingType]
    chain: tuple[_Field, ...]  # >= 2 fields; [0] is departure, [-1] is landing
    air_start: bool
    air_start_point: Optional[Point]  # set iff air_start (partway into the first leg)
    altitude_m: int
    speed_ms: int
    radio_alt: bool
    start_time_s: int
    is_helo: bool


def _neutral_country(mission: "Mission") -> "Optional[Country]":
    countries = list(mission.coalition["neutrals"].countries.values())
    return countries[0] if countries else None


def _dist2(a: Point, b: Point) -> float:
    dx = a.x - b.x
    dy = a.y - b.y
    return dx * dx + dy * dy


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


def _neighbours(field: _Field, pool: Sequence[_Field], cap2: float) -> list[_Field]:
    return [b for b in pool if b is not field and _dist2(field.point, b.point) <= cap2]


def build_chain(
    start: _Field,
    pool: Sequence[_Field],
    cap_m: float,
    n_legs: int,
    rng: random.Random,
) -> tuple[_Field, ...]:
    """Walk a path of up to ``n_legs`` legs through the reachable graph, never
    immediately doubling back, so the route is a meandering regional milk run whose
    every leg is within the cap (and therefore stays in the rear)."""
    cap2 = cap_m * cap_m
    chain: list[_Field] = [start]
    previous: Optional[_Field] = None
    current = start
    for _ in range(n_legs):
        options = [n for n in _neighbours(current, pool, cap2) if n is not previous]
        if not options:
            break
        nxt = rng.choice(options)
        chain.append(nxt)
        previous, current = current, nxt
    return tuple(chain)


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


def plan_routes(
    pool: Sequence[_Field],
    cap_m: float,
    types: Sequence[Type[FlyingType]],
    per_type: tuple[int, int],
    n_legs: int,
    air_start_per_type: int,
    rng: random.Random,
) -> list[CivilianRoute]:
    """Plan one traffic layer: for each aircraft type, a density-scaled number of
    multi-leg milk runs. The first ``air_start_per_type`` of an air-start-eligible
    type (high cruiser) air-start at t=0; the rest ground-start, staggered."""
    reachable = prune_to_reachable(pool, cap_m)
    if len(reachable) < 2:
        return []
    count = density(len(reachable), *per_type)
    routes: list[CivilianRoute] = []
    for aircraft_type in types:
        altitude_m, speed_ms, radio_alt = _PROFILE[aircraft_type]
        air_eligible = altitude_m >= AIR_START_MIN_ALT_M and not radio_alt
        for i in range(count):
            chain = build_chain(rng.choice(reachable), reachable, cap_m, n_legs, rng)
            if len(chain) < 2:
                continue
            air = air_eligible and i < air_start_per_type
            air_point: Optional[Point] = None
            start_time = 0
            if air:
                frac = rng.uniform(0.25, 0.75)
                a, b = chain[0].point, chain[1].point
                air_point = Point(
                    a.x + (b.x - a.x) * frac,
                    a.y + (b.y - a.y) * frac,
                    a._terrain,
                )
            else:
                start_time = rng.randint(0, STAGGER_WINDOW_S)
            routes.append(
                CivilianRoute(
                    aircraft_type=aircraft_type,
                    chain=chain,
                    air_start=air,
                    air_start_point=air_point,
                    altitude_m=altitude_m,
                    speed_ms=speed_ms,
                    radio_alt=radio_alt,
                    start_time_s=start_time,
                    is_helo=bool(aircraft_type.helicopter),
                )
            )
    return routes


class CivilianTrafficGenerator:
    """Plans and spawns the civilian background-traffic layer into the mission."""

    def __init__(
        self, mission: Mission, game: Game, rng: Optional[random.Random] = None
    ) -> None:
        self.mission = mission
        self.game = game
        self.rng = rng or random.Random()

    def neutral_fields(self) -> list[_Field]:
        """Every map airfield Retribution does not control, admitted past the front
        keep-out. The campaign owns the front line, so this is computed here rather
        than re-derived at runtime in Lua."""
        controlled = {
            cp.dcs_airport.name
            for cp in self.game.theater.controlpoints
            if cp.dcs_airport is not None
        }
        fronts = [
            Point(front.position.x, front.position.y, self.mission.terrain)
            for front in self.game.theater.conflicts()
        ]
        fields: list[_Field] = []
        for name, airport in self.mission.terrain.airports.items():
            if name in controlled:
                continue
            if admit_field(airport.position, fronts, self.rng):
                fields.append(_Field(name=name, point=airport.position))
        return fields

    def _neutral_country(self) -> "Optional[Country]":
        return _neutral_country(self.mission)

    def generate(self) -> None:
        country = self._neutral_country()
        if country is None:
            logging.warning("No neutral country available — skipping civilian traffic")
            return

        pool = self.neutral_fields()
        routes = plan_routes(
            pool, FW_MAXDIST_M, FW_TYPES, (1, 3), FW_LEGS, AIR_START_PER_TYPE, self.rng
        ) + plan_routes(
            pool, HELO_MAXDIST_M, HELO_TYPES, (1, 2), HELO_LEGS, 0, self.rng
        )

        spawned = sum(
            1 for idx, route in enumerate(routes) if self._spawn(country, idx, route)
        )
        logging.info(
            "Civilian traffic: %d flights from a %d-field neutral pool",
            spawned,
            len(pool),
        )

    def _spawn(self, country: "Country", idx: int, route: CivilianRoute) -> bool:
        name = f"CIV_{route.aircraft_type.id}_{idx}"
        try:
            if route.air_start:
                assert route.air_start_point is not None
                group = self.mission.flight_group_inflight(
                    country=country,
                    name=name,
                    aircraft_type=route.aircraft_type,
                    position=route.air_start_point,
                    altitude=route.altitude_m,
                    speed=route.speed_ms,
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

            # Intermediate legs (the final field is handled by land_at).
            for field in route.chain[1:-1]:
                waypoint = group.add_waypoint(
                    field.point, route.altitude_m, route.speed_ms
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
                group.add_waypoint(point, NAVAL_SPEED_MS)

            group.points[0].tasks.append(OptROE(OptROE.Values.WeaponHold))
            group.points[0].tasks.append(SetInvisibleCommand(True))
        except Exception:  # pragma: no cover - defensive; never block generation
            logging.exception("Failed to spawn naval civilian traffic %s", name)
            return False
        return True
