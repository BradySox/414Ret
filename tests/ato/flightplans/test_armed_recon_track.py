"""Tests for the armed-recon road sweep.

Convoy hunting used to plan a single target point at the package target -- for
a convoy or a supply-route interdiction that is effectively the origin base, so
the flight had nothing to actually search. The plan now sweeps the hunted
route: SEARCH START/MID/END points along the road polyline, ordered away from
the package ingress, each anchoring an engage zone at runtime.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Optional

import pytest

from dcs import Point
from dcs.terrain import Caucasus

from game.ato.flightplans.armedrecon import Builder, _path_length, _point_along
from game.theater import Player
from game.theater.controlpoint import Airfield
from game.transfers import Convoy

TERRAIN = Caucasus()
NM = 1852.0


def _pt(x: float, y: float) -> Point:
    return Point(x, y, TERRAIN)


def _road(*points: tuple[float, float]) -> tuple[Point, ...]:
    return tuple(_pt(x, y) for x, y in points)


def _airfield(
    captured: Player, convoy_routes: Optional[dict[Any, tuple[Point, ...]]] = None
) -> Airfield:
    field = Airfield.__new__(Airfield)
    # ControlPoint.captured reads coalition.player (via the _coalition backing).
    field._coalition = SimpleNamespace(player=captured)  # type: ignore[assignment]
    field.convoy_routes = convoy_routes or {}
    return field


def _builder(target: Any, ingress: Point) -> Builder:
    builder = Builder.__new__(Builder)
    builder.flight = SimpleNamespace(  # type: ignore[assignment]
        package=SimpleNamespace(
            target=target, waypoints=SimpleNamespace(ingress=ingress)
        )
    )
    return builder


def test_point_along_walks_the_polyline_by_distance() -> None:
    # An L-shaped road: 2 nm east then 2 nm north. Halfway is the corner.
    road = _road((0, 0), (2 * NM, 0), (2 * NM, 2 * NM))
    assert _path_length(road) == pytest.approx(4 * NM)
    mid = _point_along(road, 0.5)
    assert (mid.x, mid.y) == (pytest.approx(2 * NM), pytest.approx(0, abs=1e-6))
    assert _point_along(road, 1.0).y == pytest.approx(2 * NM)


def test_convoy_target_sweeps_its_own_road() -> None:
    destination = object()
    road = _road((0, 0), (4 * NM, 0))
    convoy = Convoy.__new__(Convoy)
    convoy.origin = SimpleNamespace(convoy_routes={destination: road})  # type: ignore[assignment]
    convoy.destination = destination  # type: ignore[assignment]

    track = _builder(convoy, ingress=_pt(-2 * NM, 0))._search_track()
    assert [name for name, _ in track] == ["SEARCH START", "SEARCH MID", "SEARCH END"]
    assert track[0][1].x == pytest.approx(0)
    assert track[1][1].x == pytest.approx(2 * NM)
    assert track[2][1].x == pytest.approx(4 * NM)


def test_sweep_flows_away_from_the_ingress() -> None:
    destination = object()
    road = _road((0, 0), (4 * NM, 0))
    convoy = Convoy.__new__(Convoy)
    convoy.origin = SimpleNamespace(convoy_routes={destination: road})  # type: ignore[assignment]
    convoy.destination = destination  # type: ignore[assignment]

    # Ingress beyond the far end: the road is flown in reverse, no backtrack.
    track = _builder(convoy, ingress=_pt(6 * NM, 0))._search_track()
    assert track[0][1].x == pytest.approx(4 * NM)
    assert track[2][1].x == pytest.approx(0)


def test_control_point_target_prefers_its_own_supply_corridor() -> None:
    # The right-click supply-route interdiction frags armed recon on the enemy
    # end CP. Enemy trucks drive the rear-to-front trail (a same-owner road),
    # not the contested front road -- prefer it, longest first.
    trail = _road((0, 0), (0, 10 * NM))
    short_trail = _road((0, 0), (3 * NM, 0))
    front_road = _road((0, 0), (-20 * NM, 0))
    target = _airfield(
        Player.RED,
        {
            _airfield(Player.RED): trail,
            _airfield(Player.RED): short_trail,
            _airfield(Player.BLUE): front_road,
        },
    )
    route = Builder._interdiction_route_for(target)
    assert route is trail


def test_control_point_falls_back_to_a_contested_road() -> None:
    front_road = _road((0, 0), (-20 * NM, 0))
    target = _airfield(Player.RED, {_airfield(Player.BLUE): front_road})
    assert Builder._interdiction_route_for(target) is front_road


def test_no_road_network_keeps_the_single_point_plan() -> None:
    target = _airfield(Player.RED)
    assert Builder._interdiction_route_for(target) is None
    assert _builder(target, ingress=_pt(0, 0))._search_track() == []


def test_other_targets_keep_the_single_point_plan() -> None:
    tgo_like = SimpleNamespace(position=_pt(0, 0))
    assert _builder(tgo_like, ingress=_pt(0, 0))._search_track() == []
