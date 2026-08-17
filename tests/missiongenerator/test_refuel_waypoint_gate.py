"""A refuel waypoint is only worth flying to if a tanker is actually up.

The planner emits one whenever the coalition owns a tanker-capable squadron
ANYWHERE in theater -- deliberately, because gating it on fuel need is what the
reverted §46 did. Flown 2026-08-16: 10 of 40 flights carried one, including a
14 nm carrier escort whose refuel point sat 3.7 nm from the boat, and a flight
whose refuel waypoint was 4.1 nm from home, after SPLIT, just before landing.

This gate runs at GENERATION, so the plan and §46's decision are untouched.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.missiongenerator.aircraft.waypoints.waypointgenerator import (
    WaypointGenerator,
)
from game.theater.player import Player


def generator(tankers: Any, flight_is_blue: bool = True) -> WaypointGenerator:
    gen = WaypointGenerator.__new__(WaypointGenerator)
    gen.mission_data = SimpleNamespace(tankers=tankers)  # type: ignore[assignment]
    gen.flight = SimpleNamespace(  # type: ignore[assignment]
        blue=Player.BLUE if flight_is_blue else Player.RED
    )
    return gen


def tanker(blue: bool) -> Any:
    return SimpleNamespace(blue=Player.BLUE if blue else Player.RED)


def test_a_friendly_tanker_in_the_mission_keeps_the_waypoint() -> None:
    assert generator([tanker(blue=True)])._friendly_tanker_is_flying()


def test_no_tanker_at_all_drops_it() -> None:
    assert not generator([])._friendly_tanker_is_flying()


def test_only_an_enemy_tanker_drops_it() -> None:
    """`blue` is a Player enum and therefore always truthy; a bare truthiness
    test here would match the enemy tanker and make the gate a no-op."""
    assert not generator([tanker(blue=False)])._friendly_tanker_is_flying()
    assert not generator(
        [tanker(blue=True)], flight_is_blue=False
    )._friendly_tanker_is_flying()


def test_red_flight_matches_a_red_tanker() -> None:
    assert generator(
        [tanker(blue=False)], flight_is_blue=False
    )._friendly_tanker_is_flying()


def test_absent_tanker_data_never_drops_anything() -> None:
    """Lightweight test doubles carry no tanker list; never drop on a guess."""
    assert generator(None)._friendly_tanker_is_flying()
