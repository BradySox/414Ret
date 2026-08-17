"""A refuel waypoint has to point at a tanker that can actually service it.

The planner emits one whenever the coalition owns a tanker-capable squadron
ANYWHERE in theater -- deliberately, because gating it on fuel need is what the
reverted §46 did -- and places it 75 % of the way from home to the join point,
a rule with no term in common with where any tanker orbits. Flown 2026-08-16:
10 of 40 flights carried one, including a 14 nm carrier escort whose refuel
point sat 3.7 nm from the boat, and a flight whose refuel waypoint was 4.1 nm
from home, after SPLIT, just before landing.

This resolution runs at GENERATION, so the plan and §46's decision are untouched.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Optional

from dcs.mapping import Point
from dcs.terrain.caucasus import Caucasus

from game.missiongenerator.refuelrendezvous import (
    nearest_point_on_leg,
    refuel_rendezvous,
)
from game.theater.player import Player

TERRAIN = Caucasus()


def at(x: float, y: float) -> Point:
    return Point(x, y, TERRAIN)


class FakeType:
    """A receiver that will take fuel from anything unless told otherwise."""

    def __init__(self, refuses: Optional[object] = None) -> None:
        self.refuses = refuses

    def can_refuel_from(self, tanker: object) -> bool:
        return tanker is not self.refuses


def tanker(
    blue: bool = True,
    start: Optional[Point] = None,
    end: Optional[Point] = None,
    recovery: bool = False,
    aircraft_type: Any = None,
) -> Any:
    return SimpleNamespace(
        blue=Player.BLUE if blue else Player.RED,
        orbit_start=start,
        orbit_end=end,
        recovery=recovery,
        aircraft_type=aircraft_type,
    )


def resolve(
    tankers: list[Any], planned: Point, receiver: Any = None
) -> Optional[Point]:
    return refuel_rendezvous(
        receiver or FakeType(), True, planned, tankers  # type: ignore[arg-type]
    )


# --------------------------------------------------------------- no rendezvous


def test_no_tanker_at_all_drops_it() -> None:
    assert resolve([], at(0, 0)) is None


def test_only_an_enemy_tanker_drops_it() -> None:
    """`blue` is a Player enum and therefore always truthy; a bare truthiness
    test here would match the enemy tanker and make the gate a no-op."""
    assert resolve([tanker(blue=False, start=at(0, 0))], at(0, 0)) is None


def test_a_recovery_tanker_is_not_a_rendezvous() -> None:
    """It orbits astern of the boat to catch aircraft coming aboard. Sending a
    passing striker there is a detour to the carrier, not a refuel."""
    assert resolve([tanker(start=at(0, 0), recovery=True)], at(50_000, 0)) is None


def test_an_incompatible_tanker_drops_it() -> None:
    """A probe-only receiver and nothing but a boom tanker up: the waypoint has
    no rendezvous behind it even though a tanker is flying."""
    boom = object()
    only_boom = [tanker(start=at(0, 0), aircraft_type=boom)]
    assert resolve(only_boom, at(0, 0), receiver=FakeType(refuses=boom)) is None


# ------------------------------------------------------------ real rendezvous


def test_the_waypoint_moves_onto_the_tanker_orbit() -> None:
    planned = at(0, 0)
    moved = resolve(
        [tanker(start=at(100_000, -20_000), end=at(100_000, 20_000))], planned
    )
    assert moved is not None
    # Nearest point on that north-south leg is abeam the planned point.
    assert moved.x == 100_000
    assert moved.y == 0


def test_the_nearest_suitable_tanker_wins() -> None:
    near = tanker(start=at(10_000, 0), end=at(10_000, 0))
    far = tanker(start=at(300_000, 0), end=at(300_000, 0))
    moved = resolve([far, near], at(0, 0))
    assert moved is not None and moved.x == 10_000


def test_an_incompatible_near_tanker_yields_to_a_compatible_far_one() -> None:
    boom = object()
    moved = resolve(
        [
            tanker(start=at(10_000, 0), end=at(10_000, 0), aircraft_type=boom),
            tanker(start=at(300_000, 0), end=at(300_000, 0), aircraft_type=object()),
        ],
        at(0, 0),
        receiver=FakeType(refuses=boom),
    )
    assert moved is not None and moved.x == 300_000


def test_a_tanker_with_no_orbit_data_leaves_the_plan_alone() -> None:
    """Still a real tanker: it must not read as "none flying" and drop the
    waypoint, and there is nothing better to snap to."""
    planned = at(1234, 5678)
    assert resolve([tanker(start=None)], planned) is planned


def test_a_package_tanker_already_on_the_point_does_not_move_it() -> None:
    """A package tanker's racetrack is centred on the package refuel point, so
    resolution has to be a no-op there -- and idempotent across regeneration."""
    planned = at(0, 0)
    orbit = [tanker(start=at(0, -37_000), end=at(0, 37_000))]
    once = resolve(orbit, planned)
    assert once is not None and once.x == 0 and once.y == 0
    twice = resolve(orbit, once)
    assert twice is not None and twice.x == 0 and twice.y == 0


# ------------------------------------------------------------------- geometry


def test_nearest_point_is_clamped_to_the_orbit_leg() -> None:
    """The racetrack ends are where the tanker turns, not waypoints it flies
    past, so a point beyond an end resolves to the end itself."""
    start, end = at(0, 0), at(0, 10_000)
    assert nearest_point_on_leg(at(500, 99_000), start, end).y == 10_000
    assert nearest_point_on_leg(at(500, -99_000), start, end).y == 0


def test_a_degenerate_orbit_resolves_to_its_point() -> None:
    spot = at(7, 9)
    assert nearest_point_on_leg(at(1000, 1000), spot, spot) is spot
