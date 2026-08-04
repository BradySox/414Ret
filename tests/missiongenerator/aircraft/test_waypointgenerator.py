from typing import Any
from unittest.mock import MagicMock

from game.missiongenerator.aircraft.waypoints.waypointgenerator import (
    WaypointGenerator,
)


def _wp(eta_locked: bool, speed_locked: bool, name: str = "") -> Any:
    wp = MagicMock()
    wp.ETA_locked = eta_locked
    wp.speed_locked = speed_locked
    wp.name = name
    return wp


def _generator(points: list[Any]) -> WaypointGenerator:
    # Bypass __init__ (it needs a full flight/mission); only group.points and
    # flight are consulted by the method under test.
    gen: Any = object.__new__(WaypointGenerator)
    gen.group = MagicMock()
    gen.group.points = points
    gen.flight = MagicMock()
    return gen


def test_unlocks_speed_locked_waypoint_trapped_between_tots() -> None:
    """A carrier escort's JOIN waypoint gets a locked speed (its TOT clamps to
    the mission start, ETA == 0) while trapped between TOT-locked waypoints,
    which DCS rejects. The speed lock must be dropped while the times stay."""
    # spawn, JOIN (trapped), ESCORT HOLD, SPLIT, REFUEL, LANDING
    points = [
        _wp(eta_locked=True, speed_locked=True, name="spawn"),
        _wp(eta_locked=True, speed_locked=True, name="JOIN"),
        _wp(eta_locked=True, speed_locked=False, name="ESCORT HOLD"),
        _wp(eta_locked=False, speed_locked=True, name="SPLIT"),
        _wp(eta_locked=False, speed_locked=True, name="REFUEL"),
        _wp(eta_locked=False, speed_locked=True, name="LANDING"),
    ]

    _generator(points)._resolve_locked_speed_time_conflicts()

    # Only JOIN is unlocked; the spawn (nothing before it) and the SPLIT/RTB legs
    # (no TOT-locked waypoint after them) keep their locked speed.
    assert [p.speed_locked for p in points] == [True, False, False, True, True, True]
    # Times are untouched.
    assert all(p.ETA_locked for p in points[:3])


def test_leaves_untrapped_speed_locks_alone() -> None:
    """A normal escort (JOIN has a real TOT, so no speed lock there) is unchanged:
    the split/RTB legs are not trapped (no TOT-locked waypoint follows them)."""
    points = [
        _wp(eta_locked=True, speed_locked=True, name="spawn"),
        _wp(eta_locked=True, speed_locked=False, name="JOIN"),
        _wp(eta_locked=True, speed_locked=False, name="ESCORT HOLD"),
        _wp(eta_locked=False, speed_locked=True, name="SPLIT"),
        _wp(eta_locked=False, speed_locked=True, name="REFUEL"),
        _wp(eta_locked=False, speed_locked=True, name="LANDING"),
    ]

    _generator(points)._resolve_locked_speed_time_conflicts()

    assert [p.speed_locked for p in points] == [True, False, False, True, True, True]


def test_unlocks_second_of_two_adjacent_tot_locked_waypoints() -> None:
    """DCS's span is INCLUSIVE of the closing TOT waypoint, so two adjacent
    TOT-locked waypoints are rejected when the second one is also speed-locked.

    This is the route of the turn-2 Marianas "Kunlun Shan BARCAP|27|68|J-15
    Flanker X-2|" that DCS refused to load with "All waypoints (2-2) have locked
    speed and surrounded by waypoints 1 and 2 with locked time!": an air-started
    BARCAP whose racetrack TOT had already elapsed, so its ETA clamped to 0 and
    set_waypoint_tot speed-locked it right behind the ETA-0 spawn point.
    """
    points = [
        _wp(eta_locked=True, speed_locked=True, name=""),  # in-flight spawn
        _wp(eta_locked=True, speed_locked=True, name="RACETRACK START"),
        _wp(eta_locked=False, speed_locked=True, name="RACETRACK END"),
        _wp(eta_locked=False, speed_locked=True, name="NAV"),
        _wp(eta_locked=False, speed_locked=True, name="LANDING"),
    ]

    _generator(points)._resolve_locked_speed_time_conflicts()

    # Only the racetrack start is freed: the spawn point opens the route and the
    # RTB legs have no TOT after them, so both keep their locked speed.
    assert [p.speed_locked for p in points] == [True, False, True, True, True]
    # The spawn point keeps its locked time -- late activation requires it.
    assert [p.ETA_locked for p in points] == [True, True, False, False, False]


def test_unlocks_a_run_of_trapped_speed_locked_waypoints() -> None:
    """Every locked-speed waypoint in a run bounded by TOT-locked waypoints on
    both sides is unlocked."""
    points = [
        _wp(eta_locked=True, speed_locked=False, name="A"),
        _wp(eta_locked=False, speed_locked=True, name="B"),
        _wp(eta_locked=False, speed_locked=True, name="C"),
        _wp(eta_locked=True, speed_locked=False, name="D"),
    ]

    _generator(points)._resolve_locked_speed_time_conflicts()

    assert [p.speed_locked for p in points] == [False, False, False, False]
