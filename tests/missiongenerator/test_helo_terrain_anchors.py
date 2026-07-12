"""Terrain re-anchoring waypoints for AI helicopter routes.

A RADIO (AGL) waypoint anchors the commanded altitude to the terrain at the
waypoint only; DCS interpolates straight between waypoints, so a 40-110 km low
transit leg across rising terrain is commanded into the ridge line (the flown
Red Tide M1 Harz/Sauerland Mi-8/Mi-24 CFITs). ``_insert_helo_terrain_anchors``
subdivides long RADIO legs with plain unlocked Turning Points so the commanded
profile re-anchors at most MAX_HELO_ANCHOR_SPACING apart.
"""

from types import SimpleNamespace
from typing import Any

from dcs.mapping import Point
from dcs.point import MovingPoint
from dcs.terrain import Caucasus

from game.missiongenerator.aircraft.waypoints.waypointgenerator import (
    MAX_HELO_ANCHOR_SPACING,
    WaypointGenerator,
)
from game.utils import feet, nautical_miles

TERRAIN = Caucasus()
CRUISE_AGL_FT = 500


def _gen(points: list[MovingPoint]) -> Any:
    gen: Any = WaypointGenerator.__new__(WaypointGenerator)
    gen.flight = SimpleNamespace(is_helo=True, client_count=0)
    gen.settings = SimpleNamespace(heli_cruise_alt_agl=CRUISE_AGL_FT)
    gen.group = SimpleNamespace(points=points)
    return gen


def _point(
    x: float, y: float, alt: float, alt_type: str = "RADIO", name: str = ""
) -> MovingPoint:
    mp = MovingPoint(Point(x, y, TERRAIN))
    mp.alt = int(round(alt))
    mp.alt_type = alt_type
    mp.name = name
    mp.speed = 55.0
    return mp


def test_long_radio_leg_is_subdivided() -> None:
    leg = nautical_miles(50).meters
    points = [_point(0, 0, 30.5), _point(leg, 0, 30.5)]
    gen = _gen(points)
    gen._insert_helo_terrain_anchors()

    assert len(points) > 2
    spacing = MAX_HELO_ANCHOR_SPACING.meters
    for a, b in zip(points, points[1:]):
        assert a.position.distance_to_point(b.position) <= spacing + 1.0
    for anchor in points[1:-1]:
        assert anchor.name == "TERRAIN"
        assert anchor.alt_type == "RADIO"
        # Floored at the cruise AGL so a treetop-anchored return leg is not
        # pinned at combat height for 100 km.
        assert anchor.alt == int(round(feet(CRUISE_AGL_FT).meters))
        assert anchor.ETA_locked is False
        assert anchor.speed_locked is False
        assert anchor.speed == 55.0


def test_anchor_altitude_keeps_the_higher_leg_end() -> None:
    leg = nautical_miles(20).meters
    high = int(round(feet(1000).meters))
    points = [_point(0, 0, high), _point(leg, 0, 30.5)]
    gen = _gen(points)
    gen._insert_helo_terrain_anchors()
    assert all(p.alt == high for p in points[1:-1])


def test_short_leg_untouched() -> None:
    leg = nautical_miles(4).meters
    points = [_point(0, 0, 30.5), _point(leg, 0, 30.5)]
    _gen(points)._insert_helo_terrain_anchors()
    assert len(points) == 2


def test_baro_leg_untouched() -> None:
    leg = nautical_miles(50).meters
    points = [
        _point(0, 0, 500, alt_type="BARO"),
        _point(leg, 0, 500, alt_type="BARO"),
    ]
    _gen(points)._insert_helo_terrain_anchors()
    assert len(points) == 2


def test_racetrack_orbit_leg_never_subdivided() -> None:
    # The RACETRACK START -> next point adjacency IS the orbit definition;
    # inserting a point inside it would corrupt the racetrack.
    leg = nautical_miles(50).meters
    points = [
        _point(0, 0, 30.5, name="RACETRACK START"),
        _point(leg, 0, 30.5, name="RACETRACK END"),
    ]
    _gen(points)._insert_helo_terrain_anchors()
    assert len(points) == 2


def test_mixed_route_subdivides_only_the_long_radio_legs() -> None:
    long_leg = nautical_miles(30).meters
    points = [
        _point(0, 0, 30.5),
        _point(long_leg, 0, 30.5),  # long RADIO leg before this: subdivided
        _point(long_leg + nautical_miles(3).meters, 0, 30.5),  # short: untouched
    ]
    gen = _gen(points)
    gen._insert_helo_terrain_anchors()
    names = [p.name for p in points]
    # 5 anchors on the 30 NM leg (ceil(30/5) - 1), none on the 3 NM leg.
    assert names.count("TERRAIN") == 5
    assert names[-2:] == ["", ""]
