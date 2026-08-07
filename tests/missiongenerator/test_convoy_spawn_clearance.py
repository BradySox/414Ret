"""Convoys must not spawn on the runway.

An ``Airfield`` control point's ``position`` is the DCS airfield reference
point -- the same point pydcs uses for a ``StartType.Runway`` spawn -- so a
supply route authored with its first waypoint at the control point parks the
whole convoy on the runway. ``ConvoyGenerator.spawn_position`` walks such a
spawn back out along the authored route.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

from dcs.mapping import Point

from game.missiongenerator.convoygenerator import (
    AIRFIELD_SPAWN_CLEARANCE_M,
    MAX_SPAWN_WALK_M,
    ConvoyGenerator,
)


def point(x: float, y: float) -> Point:
    return Point(x, y, None)  # type: ignore[arg-type]


@dataclass
class FakeAirport:
    position: Point


@dataclass
class FakeControlPoint:
    name: str
    dcs_airport: Optional[FakeAirport]
    route: Sequence[Point]
    convoy_spawns: dict[object, tuple[Point, ...]] = field(default_factory=dict)

    def convoy_route_to(self, destination: object) -> Sequence[Point]:
        return self.route


@dataclass
class FakeConvoy:
    origin: FakeControlPoint
    name: str = "Convoy 001"
    destination: object = None

    @property
    def route_start(self) -> Point:
        return self.origin.route[0]


@dataclass
class FakeTheater:
    water: Sequence[Point] = field(default_factory=tuple)

    def is_on_land(self, p: Point) -> bool:
        return all(p.distance_to_point(w) > 250 for w in self.water)


@dataclass
class FakeGame:
    theater: FakeTheater


def generator(theater: Optional[FakeTheater] = None) -> ConvoyGenerator:
    gen = ConvoyGenerator.__new__(ConvoyGenerator)
    gen.game = FakeGame(theater or FakeTheater())  # type: ignore[assignment]
    return gen


AIRFIELD = point(0, 0)


def straight_route(start: Point, *, length: float = 30_000.0) -> list[Point]:
    """A route running due east from ``start``."""
    return [start, point(start.x + length, start.y)]


def test_spawn_on_the_airfield_reference_is_walked_clear() -> None:
    origin = FakeControlPoint("Bremen", FakeAirport(AIRFIELD), straight_route(AIRFIELD))
    spawned = generator().spawn_position(FakeConvoy(origin))  # type: ignore[arg-type]

    assert spawned.distance_to_point(AIRFIELD) >= AIRFIELD_SPAWN_CLEARANCE_M
    # It stays on the authored corridor rather than wandering off it.
    assert spawned.y == AIRFIELD.y
    # And it does not march the convoy any further than it has to.
    assert spawned.distance_to_point(AIRFIELD) < AIRFIELD_SPAWN_CLEARANCE_M + 200


def test_route_already_clear_of_the_field_is_untouched() -> None:
    start = point(5_000, 0)
    origin = FakeControlPoint("Fulda", FakeAirport(AIRFIELD), straight_route(start))
    spawned = generator().spawn_position(FakeConvoy(origin))  # type: ignore[arg-type]

    assert spawned == start


def test_control_point_without_a_runway_is_untouched() -> None:
    origin = FakeControlPoint("FOB Alpha", None, straight_route(AIRFIELD))
    spawned = generator().spawn_position(FakeConvoy(origin))  # type: ignore[arg-type]

    assert spawned == AIRFIELD


def test_water_along_the_route_is_skipped() -> None:
    origin = FakeControlPoint(
        "Nordholz", FakeAirport(AIRFIELD), straight_route(AIRFIELD)
    )
    theater = FakeTheater(water=[point(AIRFIELD.x + AIRFIELD_SPAWN_CLEARANCE_M, 0)])
    spawned = generator(theater).spawn_position(FakeConvoy(origin))  # type: ignore[arg-type]

    assert theater.is_on_land(spawned)
    assert spawned.distance_to_point(AIRFIELD) >= AIRFIELD_SPAWN_CLEARANCE_M


def test_a_fully_fouled_approach_falls_back_to_the_authored_start() -> None:
    # Every sample within the walk budget is "water", so no clear spot exists.
    water = [point(x, 0) for x in range(0, int(MAX_SPAWN_WALK_M) + 500, 200)]
    origin = FakeControlPoint(
        "Nordholz", FakeAirport(AIRFIELD), straight_route(AIRFIELD)
    )
    spawned = generator(FakeTheater(water)).spawn_position(FakeConvoy(origin))  # type: ignore[arg-type]

    assert spawned == AIRFIELD


def test_the_walk_is_bounded() -> None:
    # A short first leg that never leaves the keep-out circle, then a long one:
    # the convoy is never marched past the budget hunting for clear ground.
    water = [point(x, 0) for x in range(0, 60_000, 200)]
    route = [AIRFIELD, point(200, 0), point(60_000, 0)]
    origin = FakeControlPoint("Bremen", FakeAirport(AIRFIELD), route)
    spawned = generator(FakeTheater(water)).spawn_position(FakeConvoy(origin))  # type: ignore[arg-type]

    assert spawned == AIRFIELD


# --- The authored spawn chain must not defeat the clearance guard -------------
#
# The chain is interpolated *from the route's endpoint*, so a route authored on
# the airfield reference point produces a chain whose lead vehicle stands on the
# runway. Observed on Caucasus - Slava Ukraini: eight T-80UDs strung across
# Anapa's runway 22 while eight AI flights taxied for takeoff.


@dataclass
class FakeConvoyWithSpawns(FakeConvoy):
    spawns: Sequence[Point] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        self.origin.convoy_spawns = {self.destination: tuple(self.spawns)}


def chain_from(start: Point, count: int = 8) -> list[Point]:
    """An authored chain marching east from ``start`` at 100 ft separation."""
    return [point(start.x + i * 30.48, start.y) for i in range(count)]


def test_a_chain_beginning_on_the_runway_is_discarded() -> None:
    origin = FakeControlPoint("Anapa", FakeAirport(AIRFIELD), straight_route(AIRFIELD))
    convoy = FakeConvoyWithSpawns(origin, spawns=chain_from(AIRFIELD))

    plan = generator().spawn_plan(convoy)  # type: ignore[arg-type]

    assert plan.spawns is None
    assert plan.cleared
    assert plan.position.distance_to_point(AIRFIELD) >= AIRFIELD_SPAWN_CLEARANCE_M


def test_a_chain_clear_of_the_runway_is_honored_wholesale() -> None:
    start = point(5_000, 0)
    origin = FakeControlPoint("Fulda", FakeAirport(AIRFIELD), straight_route(start))
    chain = chain_from(start)
    convoy = FakeConvoyWithSpawns(origin, spawns=chain)

    plan = generator().spawn_plan(convoy)  # type: ignore[arg-type]

    assert plan.spawns == tuple(chain)
    assert not plan.cleared
    assert plan.position == start


def test_a_fouled_approach_keeps_the_chain_rather_than_losing_both() -> None:
    # No clear ground exists, so the spawn cannot be walked out. Discarding the
    # author's chain as well would leave the convoy on the runway *and* stacked.
    water = [point(x, 0) for x in range(0, int(MAX_SPAWN_WALK_M) + 500, 200)]
    origin = FakeControlPoint(
        "Nordholz", FakeAirport(AIRFIELD), straight_route(AIRFIELD)
    )
    chain = chain_from(AIRFIELD)
    convoy = FakeConvoyWithSpawns(origin, spawns=chain)

    plan = generator(FakeTheater(water)).spawn_plan(convoy)  # type: ignore[arg-type]

    assert plan.spawns == tuple(chain)
    assert not plan.cleared


def test_no_chain_reports_whether_the_spawn_was_cleared() -> None:
    origin = FakeControlPoint("Anapa", FakeAirport(AIRFIELD), straight_route(AIRFIELD))
    plan = generator().spawn_plan(FakeConvoy(origin))  # type: ignore[arg-type]

    assert plan.spawns is None
    assert plan.cleared
