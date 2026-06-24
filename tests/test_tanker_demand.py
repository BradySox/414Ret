"""Tests for theater-tanker placement from receiver demand (the scoring core)."""

from __future__ import annotations

import math

from types import SimpleNamespace

from game.ato.flighttype import FlightType
from game.ato.flightwaypointtype import FlightWaypointType
from game.commander.tankerdemand import (
    RefuelDemand,
    best_tanker_service_point,
    theater_refuel_demand,
)
from game.dcs.aircrafttype import AirRefuelType
from game.utils import nautical_miles

BOOM = AirRefuelType.BOOM
PROBE = AirRefuelType.PROBE


class FakePoint:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def distance_to_point(self, other: "FakePoint") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def new_in_same_map(self, x: float, y: float) -> "FakePoint":
        return FakePoint(x, y)


def _d(method, count, x, y):  # type: ignore[no-untyped-def]
    return RefuelDemand(method=method, count=count, position=FakePoint(x, y))  # type: ignore[arg-type]


def test_no_demand_returns_none() -> None:
    assert best_tanker_service_point([], frozenset({BOOM})) is None


def test_picks_strongest_cluster() -> None:
    # Two clusters far apart (200 km): a light one near the origin and a heavy one out
    # east. The service point should land in the heavy (east) cluster.
    demands = [
        _d(BOOM, 2, 0, 0),
        _d(BOOM, 2, 5_000, 0),
        _d(BOOM, 4, 200_000, 0),
        _d(BOOM, 4, 205_000, 0),
    ]
    point = best_tanker_service_point(demands, frozenset({BOOM}))
    assert point is not None
    assert 190_000 < point.x < 215_000  # in the heavy eastern cluster
    assert abs(point.y) < 1


def test_weighted_centroid_within_cluster() -> None:
    # One cluster, weighted toward the larger flight.
    demands = [_d(BOOM, 1, 0, 0), _d(BOOM, 3, 40_000, 0)]
    point = best_tanker_service_point(demands, frozenset({BOOM}))
    assert point is not None
    # (1*0 + 3*40000) / 4 == 30000
    assert point.x == 30_000


def test_boom_only_tanker_ignores_probe_receivers() -> None:
    # A boom-only tanker scored against a big probe cluster + a small boom flight must
    # serve the boom flight, never the (incompatible) probe cluster.
    demands = [
        _d(PROBE, 4, 200_000, 0),
        _d(PROBE, 4, 205_000, 0),
        _d(BOOM, 2, 0, 0),
    ]
    point = best_tanker_service_point(demands, frozenset({BOOM}))
    assert point is not None
    assert point.x == 0  # the lone boom flight, not the heavier probe cluster


def test_boom_only_tanker_with_only_probe_demand_returns_none() -> None:
    demands = [_d(PROBE, 4, 0, 0), _d(PROBE, 2, 10_000, 0)]
    assert best_tanker_service_point(demands, frozenset({BOOM})) is None


def test_untagged_is_permissive_both_ways() -> None:
    # Untagged receiver is served by any tanker; untagged tanker serves anyone.
    assert best_tanker_service_point([_d(None, 2, 0, 0)], frozenset({BOOM})) is not None
    assert best_tanker_service_point([_d(PROBE, 2, 0, 0)], frozenset()) is not None


def test_cluster_radius_separates_demand() -> None:
    # With a tiny cluster radius, every receiver is its own cluster; the single largest
    # flight wins.
    demands = [_d(BOOM, 2, 0, 0), _d(BOOM, 5, 100_000, 0), _d(BOOM, 2, 200_000, 0)]
    point = best_tanker_service_point(
        demands, frozenset({BOOM}), cluster_radius=nautical_miles(1)
    )
    assert point is not None
    assert point.x == 100_000


# --- theater_refuel_demand (ATO extraction rules) ---------------------------------


def _wp(is_refuel, x=0.0, y=0.0):  # type: ignore[no-untyped-def]
    return SimpleNamespace(
        waypoint_type=(
            FlightWaypointType.REFUEL if is_refuel else FlightWaypointType.NAV
        ),
        position=FakePoint(x, y),
    )


def _flight(flight_type, method, count, waypoints):  # type: ignore[no-untyped-def]
    return SimpleNamespace(
        flight_type=flight_type,
        count=count,
        unit_type=SimpleNamespace(air_refuel_type=method),
        flight_plan=SimpleNamespace(waypoints=waypoints),
    )


def _coalition(packages):  # type: ignore[no-untyped-def]
    return SimpleNamespace(ato=SimpleNamespace(packages=packages))


def test_extraction_collects_receiver_refuel_waypoints() -> None:
    receiver = _flight(FlightType.DEAD, BOOM, 4, [_wp(False), _wp(True, 1000, 0)])
    no_gas = _flight(FlightType.BARCAP, BOOM, 2, [_wp(False)])
    pkg = SimpleNamespace(flights=[receiver, no_gas])
    demands = theater_refuel_demand(_coalition([pkg]))
    assert len(demands) == 1
    assert demands[0].count == 4 and demands[0].position.x == 1000


def test_extraction_ignores_tanker_flights_and_buddy_tanker_packages() -> None:
    # A dedicated tanker package: the tanker itself is not demand.
    tanker_pkg = SimpleNamespace(
        flights=[_flight(FlightType.REFUELING, None, 1, [_wp(False)])]
    )
    # An offensive package that carries its OWN buddy tanker -> its receivers refuel
    # in-package and must be excluded from theater demand.
    buddy_pkg = SimpleNamespace(
        flights=[
            _flight(FlightType.STRIKE, PROBE, 4, [_wp(True, 5000, 0)]),
            _flight(FlightType.REFUELING, None, 1, [_wp(False)]),
        ]
    )
    demands = theater_refuel_demand(_coalition([tanker_pkg, buddy_pkg]))
    assert demands == []
