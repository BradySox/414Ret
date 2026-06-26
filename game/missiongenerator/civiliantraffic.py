"""Civilian background air traffic, planned in Python and spawned via pydcs.

This replaces the old MOOSE ``RAT`` plugin (``resources/plugins/civilian_traffic``).
RAT is a heavyweight "living airfield" engine (ATC, respawn scheduler, runway-retry,
heliport-id resolution) and the civilian layer only ever wanted a handful of ambient
flights -- so it switched almost all of RAT off and still inherited RAT's crash
surface (the recurring ``woCharacterHuman`` / GermanyCW-FARP sim crashes came from
RAT resolving an unresolvable *heliport id* and spawning a malformed unit, which is
why the rotary layer had to be disabled entirely).

Here the campaign engine -- which already knows every airfield, its coalition and
position, and the front line -- plans the routes itself and air-starts plain pydcs
groups at a *coordinate*. There is no heliport-id resolution anywhere, so fixed-wing
**and rotary** civilians are equally safe, and the geometry (neutral pool, front
keep-out, reachable-neighbour pairing, density) is ordinary Python that CI can test
instead of "fly it and hope". Traffic is air-started invisible (AI cannot target it
-- it never affects combat) with weapon-hold ROE, and staggered across the mission via
per-group ``start_time`` so the map stays occupied without a respawn loop (the respawn
churn was the other crash path).
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Sequence, Type

from dcs.helicopters import Mi_8MT, SA342M, UH_1H
from dcs.mapping import Point
from dcs.planes import An_26B, An_30M, C_130, Yak_52
from dcs.task import OptROE, SetInvisibleCommand
from dcs.unittype import FlyingType

if TYPE_CHECKING:
    from dcs.country import Country
    from dcs.mission import Mission
    from game.game import Game

# ── Routing knobs ─────────────────────────────────────────────────────────────
KEEPOUT_M = 75_000  # ~40 NM bubble around each active front; civilians avoid it.
FW_MAXDIST_M = 280_000  # fixed-wing regional hop cap (~150 NM)
HELO_MAXDIST_M = 130_000  # rotary city-hop cap (~70 NM)
# A field inside the front bubble is usually dropped, but kept with this small
# probability so civilians occasionally stray near the fight.
STRAY_CHANCE = 0.08
# Staggered activation window: groups appear spread across the first ~45 min so the
# map stays alive through a typical sortie without any respawn loop.
STAGGER_WINDOW_S = 2_700

# Per-layer flight profiles. Altitudes are MSL, picked high enough to clear
# rear-area terrain (the keep-out keeps them away from mountains near the front).
FW_TYPES: tuple[Type[FlyingType], ...] = (C_130, An_26B, An_30M, Yak_52)
HELO_TYPES: tuple[Type[FlyingType], ...] = (Mi_8MT, UH_1H, SA342M)
FW_ALTITUDE_M = 6_000
FW_SPEED_MS = 150  # ~290 kt TAS
HELO_ALTITUDE_M = 1_000
HELO_SPEED_MS = 60  # ~115 kt


@dataclass(frozen=True)
class _Field:
    """A neutral airfield available as a civilian route endpoint."""

    name: str
    point: Point


@dataclass(frozen=True)
class CivilianRoute:
    """One planned civilian flight: an air-start point flying to a neutral field."""

    aircraft_type: Type[FlyingType]
    start: Point  # air-start position, partway along the leg
    destination: _Field
    altitude_m: int
    speed_ms: int
    start_time_s: int
    is_helo: bool


def _dist2(a: Point, b: Point) -> float:
    dx = a.x - b.x
    dy = a.y - b.y
    return dx * dx + dy * dy


def _in_combat_zone(point: Point, fronts: Sequence[Point]) -> bool:
    keepout2 = KEEPOUT_M * KEEPOUT_M
    return any(_dist2(point, f) <= keepout2 for f in fronts)


def admit_field(point: Point, fronts: Sequence[Point], rng: random.Random) -> bool:
    """Fields clear of the front always qualify; a field inside the keep-out
    bubble qualifies only on a rare stray roll, so the front stays mostly clear
    but is not perfectly sterile."""
    if not _in_combat_zone(point, fronts):
        return True
    return rng.random() < STRAY_CHANCE


def prune_to_reachable(fields: Sequence[_Field], cap_m: float) -> list[_Field]:
    """Drop any field with no *other* field within ``cap_m``, repeating until
    stable, so every survivor is guaranteed a valid destination within the cap
    (no isolated field that could never be paired)."""
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
    """Flights-per-type scaled to pool size, clamped to ``[lo, hi]`` -- keeps the
    layer light on small maps and from getting busy on large ones."""
    n = -(-pool_size * 15 // 100)  # ceil(pool_size * 0.15)
    return max(lo, min(hi, n))


def _reachable_partners(
    field: _Field, pool: Sequence[_Field], cap_m: float
) -> list[_Field]:
    cap2 = cap_m * cap_m
    return [b for b in pool if b is not field and _dist2(field.point, b.point) <= cap2]


def plan_layer(
    pool: Sequence[_Field],
    cap_m: float,
    types: Sequence[Type[FlyingType]],
    altitude_m: int,
    speed_ms: int,
    is_helo: bool,
    per_type: tuple[int, int],
    rng: random.Random,
) -> list[CivilianRoute]:
    """Plan one traffic layer: for each aircraft type, a density-scaled number of
    A->B routes between neutral fields within ``cap_m``, air-started partway along
    the leg with a staggered start time."""
    reachable = prune_to_reachable(pool, cap_m)
    if len(reachable) < 2:
        return []
    count = density(len(reachable), *per_type)
    routes: list[CivilianRoute] = []
    for aircraft_type in types:
        for _ in range(count):
            departure = rng.choice(reachable)
            partners = _reachable_partners(departure, reachable, cap_m)
            if not partners:
                continue
            destination = rng.choice(partners)
            # Air-start partway down the leg so traffic is already moving at t=0.
            frac = rng.uniform(0.25, 0.75)
            start = Point(
                departure.point.x + (destination.point.x - departure.point.x) * frac,
                departure.point.y + (destination.point.y - departure.point.y) * frac,
                departure.point._terrain,
            )
            routes.append(
                CivilianRoute(
                    aircraft_type=aircraft_type,
                    start=start,
                    destination=destination,
                    altitude_m=altitude_m,
                    speed_ms=speed_ms,
                    start_time_s=rng.randint(0, STAGGER_WINDOW_S),
                    is_helo=is_helo,
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
        """Every map airfield Retribution does not control, admitted past the
        front keep-out. The campaign owns the front line, so this is computed
        here rather than re-derived at runtime in Lua."""
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
            point = airport.position
            if admit_field(point, fronts, self.rng):
                fields.append(_Field(name=name, point=point))
        return fields

    def _neutral_country(self) -> "Optional[Country]":
        countries = list(self.mission.coalition["neutrals"].countries.values())
        return countries[0] if countries else None

    def generate(self) -> None:
        country = self._neutral_country()
        if country is None:
            logging.warning("No neutral country available — skipping civilian traffic")
            return

        pool = self.neutral_fields()
        routes = plan_layer(
            pool,
            FW_MAXDIST_M,
            FW_TYPES,
            FW_ALTITUDE_M,
            FW_SPEED_MS,
            is_helo=False,
            per_type=(1, 3),
            rng=self.rng,
        ) + plan_layer(
            pool,
            HELO_MAXDIST_M,
            HELO_TYPES,
            HELO_ALTITUDE_M,
            HELO_SPEED_MS,
            is_helo=True,
            per_type=(1, 2),
            rng=self.rng,
        )

        spawned = 0
        for idx, route in enumerate(routes):
            if self._spawn(country, idx, route):
                spawned += 1
        logging.info(
            "Civilian traffic: %d flights from a %d-field neutral pool",
            spawned,
            len(pool),
        )

    def _spawn(self, country: "Country", idx: int, route: CivilianRoute) -> bool:
        name = f"CIV_{route.aircraft_type.id}_{idx}"
        try:
            group = self.mission.flight_group_inflight(
                country=country,
                name=name,
                aircraft_type=route.aircraft_type,
                position=route.start,
                altitude=route.altitude_m,
                speed=route.speed_ms,
                group_size=1,
            )
            group.add_waypoint(
                route.destination.point, route.altitude_m, route.speed_ms
            )
            dest_airport = self.mission.terrain.airports.get(route.destination.name)
            if dest_airport is not None:
                group.land_at(dest_airport)
            group.start_time = route.start_time_s
            group.points[0].tasks.append(OptROE(OptROE.Values.WeaponHold))
            group.points[0].tasks.append(SetInvisibleCommand(True))
        except Exception:  # pragma: no cover - defensive; never block generation
            logging.exception("Failed to spawn civilian flight %s", name)
            return False
        return True
