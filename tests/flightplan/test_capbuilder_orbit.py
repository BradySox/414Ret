"""Geometry tests for CapBuilder.cap_racetrack_for_objective.

Regression for the "orbit behind the base" bug: when a defended CP sits close
to (or inside) the enemy threat zone, ``distance_to_no_fly`` goes negative.
Without a floor the racetrack end was placed at a negative offset along the
heading-to-enemy, i.e. on the friendly side, pointing away from the threat. The
fix floors the forward distance at ``cap_min_distance_from_cp`` so the orbit
always sits on the enemy-facing side.
"""

from __future__ import annotations

from typing import Iterator

import pytest
from dcs import Point
from shapely.geometry import Point as ShapelyPoint

from game.ato.flightplans import capbuilder
from game.ato.flightplans.capbuilder import CapBuilder
from game.utils import nautical_miles


class _Doctrine:
    cap_engagement_range = nautical_miles(50)
    cap_max_track_length = nautical_miles(40)
    cap_min_track_length = nautical_miles(15)
    cap_min_distance_from_cp = nautical_miles(10)
    cap_max_distance_from_cp = nautical_miles(40)


class _ThreatZones:
    def __init__(self, geom: ShapelyPoint) -> None:
        self.all = geom


class _Airfield:
    def __init__(self, position: Point, captured: object) -> None:
        self.position = position
        self.captured = captured

    def runway_is_operational(self) -> bool:
        return True


class _Target:
    def __init__(self, name: str, position: Point) -> None:
        self.name = name
        self.position = position


class _Package:
    def __init__(self, target: _Target) -> None:
        self.target = target


class _ClosestAirfields:
    def __init__(self, airfields: list[_Airfield]) -> None:
        self._airfields = airfields

    @property
    def operational_airfields(self) -> Iterator[_Airfield]:
        return iter(self._airfields)

    @property
    def closest_airfields(self) -> Iterator[_Airfield]:
        return iter(self._airfields)


class _TestCapBuilder(CapBuilder):  # type: ignore[type-arg]
    """A CapBuilder with its dependency properties stubbed out.

    We bypass IBuilder.__init__ (which needs a full Flight) and override the
    properties cap_racetrack_for_objective actually reads.
    """

    def __init__(
        self,
        package: _Package,
        is_player: object,
        doctrine: _Doctrine,
        threat_zones: _ThreatZones,
    ) -> None:
        self._package = package
        self._is_player = is_player
        self._doctrine = doctrine
        self._threat_zones = threat_zones

    @property
    def package(self) -> _Package:  # type: ignore[override]
        return self._package

    @property
    def is_player(self) -> object:  # type: ignore[override]
        return self._is_player

    @property
    def doctrine(self) -> _Doctrine:  # type: ignore[override]
        return self._doctrine

    @property
    def threat_zones(self) -> _ThreatZones:  # type: ignore[override]
        return self._threat_zones

    def build(self, dump_debug_info: bool = False) -> object:
        raise NotImplementedError


def _build_racetrack(
    monkeypatch: pytest.MonkeyPatch, threat_geom: ShapelyPoint
) -> tuple[Point, Point, Point, Point]:
    """Returns (cp_pos, enemy_pos, start, end) for a single racetrack build."""
    cp_pos = Point(0, 0, None)  # type: ignore[arg-type]
    # Enemy airfield due "north" (pydcs +x). Exact axis is irrelevant; we only
    # check that the orbit ends up on the same side as the enemy.
    enemy_pos = Point(nautical_miles(120).meters, 0, None)  # type: ignore[arg-type]

    target = _Target("friendly-cp", cp_pos)
    enemy = _Airfield(enemy_pos, captured="RED")

    monkeypatch.setattr(
        capbuilder.ObjectiveDistanceCache,
        "get_closest_airfields",
        staticmethod(lambda _location: _ClosestAirfields([enemy])),
    )

    builder = _TestCapBuilder(
        package=_Package(target),
        is_player="BLUE",
        doctrine=_Doctrine(),
        threat_zones=_ThreatZones(threat_geom),
    )
    start, end = builder.cap_racetrack_for_objective(target, barcap=True)  # type: ignore[arg-type]
    return cp_pos, enemy_pos, start, end


def _dot_toward_enemy(cp: Point, enemy: Point, probe: Point) -> float:
    return (probe.x - cp.x) * (enemy.x - cp.x) + (probe.y - cp.y) * (enemy.y - cp.y)


def test_orbit_is_enemy_facing_when_cp_inside_threat_zone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Threat zone sits right on top of the CP -> distance_to_no_fly is strongly
    # negative. Pre-fix this placed the orbit end behind the CP (dot < 0).
    cp, enemy, _start, end = _build_racetrack(monkeypatch, ShapelyPoint(0, 0))
    assert _dot_toward_enemy(cp, enemy, end) > 0


def test_orbit_is_enemy_facing_when_threat_zone_far(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Threat zone far away -> plenty of room; orbit end is forward toward enemy.
    far = ShapelyPoint(nautical_miles(120).meters, 0)
    cp, enemy, _start, end = _build_racetrack(monkeypatch, far)
    assert _dot_toward_enemy(cp, enemy, end) > 0
