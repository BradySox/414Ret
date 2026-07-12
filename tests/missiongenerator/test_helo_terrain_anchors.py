"""Terrain re-anchoring waypoints for AI helicopter routes.

A RADIO (AGL) waypoint anchors the commanded altitude to the terrain at the
waypoint only; DCS interpolates straight between waypoints, so a 40-110 km low
transit leg across rising terrain is commanded into the ridge line (the flown
Red Tide M1 Harz/Sauerland Mi-8/Mi-24 CFITs). ``_insert_helo_terrain_anchors``
subdivides long RADIO legs with speed-locked Turning Points so the commanded
profile re-anchors at most MAX_HELO_ANCHOR_SPACING apart.

The lock flags are DCS-validated at mission start: both-unlocked is rejected
unless bracketed by ETA-locked waypoints ("has both unlocked speed and time and
not surrounded by waypoints with locked time" -- the first generated Red Tide
M2 tripped this on every subdivided helo RTB leg), and a locked speed BETWEEN
ETA-locked waypoints is rejected too. Anchors therefore insert speed-locked and
rely on ``_resolve_locked_speed_time_conflicts`` (which runs right after in
``build()``) to unlock the bracketed ones.
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
        # Speed locked, ETA unlocked: the only combination DCS accepts on a
        # leg that is not bracketed by TOT-locked waypoints (an RTB leg).
        assert anchor.ETA_locked is False
        assert anchor.speed_locked is True
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


def _route_is_dcs_legal(points: list[MovingPoint]) -> bool:
    """The two mission-start route validations DCS applies to lock flags."""
    n = len(points)
    eta_before = [False] * n
    seen = False
    for i in range(n):
        eta_before[i] = seen
        seen = seen or points[i].ETA_locked
    eta_after = [False] * n
    seen = False
    for i in range(n - 1, -1, -1):
        eta_after[i] = seen
        seen = seen or points[i].ETA_locked
    for i in range(n):
        bracketed = eta_before[i] and eta_after[i]
        if points[i].speed_locked and bracketed:
            return False  # "locked speed ... surrounded by ... locked time"
        if not points[i].speed_locked and not points[i].ETA_locked and not bracketed:
            return False  # "both unlocked speed and time and not surrounded ..."
    return True


def test_anchors_on_an_unbracketed_leg_are_dcs_legal() -> None:
    # The Red Tide M2 failure: subdivided RTB legs after the flight's last
    # TOT-locked waypoint. Both-unlocked anchors there are rejected by DCS at
    # mission start; speed-locked anchors are accepted.
    leg = nautical_miles(30).meters
    start = _point(0, 0, 30.5)
    start.ETA_locked = True  # departure point carries the locked start time
    points = [start, _point(leg, 0, 30.5)]
    gen = _gen(points)
    gen._insert_helo_terrain_anchors()
    gen._resolve_locked_speed_time_conflicts()
    assert [p.name for p in points].count("TERRAIN") == 5
    assert _route_is_dcs_legal(points)


def test_anchors_between_tot_locked_waypoints_get_speed_unlocked() -> None:
    # The inverse DCS rejection: a locked speed between ETA-locked waypoints.
    # The conflict resolver (which build() runs right after the insertion)
    # must unlock the bracketed anchors' speed.
    leg = nautical_miles(30).meters
    a = _point(0, 0, 30.5)
    a.ETA_locked = True
    b = _point(leg, 0, 30.5)
    b.ETA_locked = True
    points = [a, b, _point(leg + nautical_miles(1).meters, 0, 30.5)]
    gen = _gen(points)
    gen.flight = SimpleNamespace(is_helo=True, client_count=0)
    gen._insert_helo_terrain_anchors()
    gen._resolve_locked_speed_time_conflicts()
    anchors = [p for p in points if p.name == "TERRAIN"]
    assert anchors
    assert all(not p.speed_locked for p in anchors)
    assert _route_is_dcs_legal(points)
