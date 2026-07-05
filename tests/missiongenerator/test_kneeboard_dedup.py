from __future__ import annotations

import datetime
from types import SimpleNamespace
from typing import Any

from game.ato.flightwaypointtype import FlightWaypointType
from game.missiongenerator.kneeboard import FlightPlanBuilder


def _units() -> Any:
    return SimpleNamespace(
        distance_short=lambda d: 0.0,
        distance_long=lambda d: 0.0,
        speed=lambda s: 0.0,
        mass=lambda m: m.pounds,
        distance_short_uom="ft",
        distance_long_uom="nm",
        speed_uom="kt",
        mass_uom="lb",
    )


def _waypoint() -> Any:
    return SimpleNamespace(
        display_name="NAV",
        alt=SimpleNamespace(feet=20000),
        tot=None,
        departure_time=None,
        fuel_planned=7500.0,
        min_fuel=5000.0,
        waypoint_type=FlightWaypointType.NAV,
    )


def test_flight_plan_always_carries_the_fuel_column() -> None:
    # 8 columns: #, Action, Alt, Dist, GSPD, Time, Departure, Fuel. The standalone
    # Fuel Ladder page is retired; the ladder rides in the flight plan.
    builder = FlightPlanBuilder(datetime.datetime(2026, 1, 1), _units())
    builder.add_waypoint(0, _waypoint())
    assert len(builder.rows[0]) == 8
