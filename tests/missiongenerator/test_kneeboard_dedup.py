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
        min_fuel=5000.0,
        waypoint_type=FlightWaypointType.NAV,
    )


def _row_len(include_min_fuel: bool) -> int:
    builder = FlightPlanBuilder(
        datetime.datetime(2026, 1, 1), _units(), include_min_fuel=include_min_fuel
    )
    builder.add_waypoint(0, _waypoint())
    return len(builder.rows[0])


def test_flight_plan_keeps_min_fuel_column_by_default() -> None:
    # 9 columns: #, Action, Alt, Dist, Brg, GSPD, Time, Departure, Min fuel.
    assert _row_len(include_min_fuel=True) == 9


def test_flight_plan_drops_min_fuel_column_when_fuel_ladder_owns_it() -> None:
    # The Fuel Ladder page owns the fuel ladder, so Mission Info drops the column.
    assert _row_len(include_min_fuel=False) == 8
