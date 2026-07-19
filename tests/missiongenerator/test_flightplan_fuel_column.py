"""The fuel ladder folded into the flight-plan table (the Mission Info page).

The standalone Fuel Ladder page was retired 2026-07-05 ("why can you not build
the fuel table into the flight plan?"): the flight plan carries a Fuel column
(planned remaining at each RTB steerpoint) and the page prints the constant RTB
margin once as a one-line call-out. These pin the ladder's old eligibility and
margin semantics on the new home.
"""

from __future__ import annotations

import datetime
from types import SimpleNamespace
from typing import Any, Optional

from game.ato.flightwaypoint import GROUND_MARKED_WAYPOINTS
from game.ato.flightwaypointtype import FlightWaypointType
from game.missiongenerator.kneeboard import FlightPlanBuilder


def _units() -> Any:
    # mass() returns the raw pound value so the rendered figures equal the inputs.
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


def _wp(
    name: str,
    plan: Optional[float],
    min_fuel: Optional[float],
    wtype: FlightWaypointType = FlightWaypointType.NAV,
) -> Any:
    return SimpleNamespace(
        display_name=name,
        alt=SimpleNamespace(feet=20000),
        position=SimpleNamespace(distance_to_point=lambda other: 1000.0),
        tot=None,
        departure_time=None,
        fuel_planned=plan,
        min_fuel=min_fuel,
        waypoint_type=wtype,
        marks_ground_for_player=wtype in GROUND_MARKED_WAYPOINTS,
    )


def _build(waypoints: list[Any]) -> FlightPlanBuilder:
    builder = FlightPlanBuilder(datetime.datetime(2026, 1, 1), _units())
    for num, waypoint in enumerate(waypoints):
        builder.add_waypoint(num, waypoint)
    builder.build()
    return builder


# Mirrors the old ladder fixture: plan/min walked from opposite ends, margin 1507.
_LADDER = [
    _wp("Takeoff", 10633, 9126),
    _wp("Hold", 9969, 8462),
    _wp("Target area", 7026, 5519),
    _wp("Land", 3507, 2000),
    _wp("Bullseye", 425, None),  # post-landing reference: no min-to-RTB
]


def test_flight_plan_has_a_fuel_column() -> None:
    builder = _build(_LADDER)
    # 8 columns: #, Action, Alt, Dist, GSPD, Time, Departure, Fuel.
    assert all(len(row) == 8 for row in builder.rows)
    assert builder.rows[0][-1] == "10633"
    assert builder.rows[2][-1] == "7026"


def test_fuel_blank_for_post_landing_reference_points() -> None:
    # The bullseye (no min-to-RTB) is not a real arrival state: no fuel figure,
    # and it must not feed the margin.
    builder = _build(_LADDER)
    assert builder.rows[4][-1] == ""
    assert len(builder.fuel_margins) == 4


def test_margin_call_out_reports_the_constant_surplus_once() -> None:
    line = _build(_LADDER).fuel_margin_line()
    assert line == (
        "RTB margin +1507 lb — spare over the minimum to get home with reserves."
    )


def test_negative_margin_warns_to_tank_or_divert() -> None:
    short = [_wp("Takeoff", 5000, 6000), _wp("Land", 2000, 3000)]
    line = _build(short).fuel_margin_line()
    assert line is not None
    assert "RTB margin -1000 lb" in line
    assert "tank or divert" in line


def test_no_fuel_data_yields_no_margin_line() -> None:
    # An airframe with no fuel estimate at all: dashes/blanks, no call-out.
    no_data = [_wp("Takeoff", None, None), _wp("Land", None, None)]
    builder = _build(no_data)
    assert builder.fuel_margin_line() is None
    assert builder.rows[0][-1] == ""


def test_planned_missing_but_min_present_shows_dash() -> None:
    builder = _build([_wp("Takeoff", None, 5000.0)])
    assert builder.rows[0][-1] == "-"
    assert builder.fuel_margin_line() is None


def test_post_landing_reference_rows_carry_no_time_or_speed() -> None:
    # The divert and bullseye ride the jet's route as steerpoints, but the
    # chained ETA past the landing point ("when you would get there if you kept
    # flying after landing") is noise: their Time/Departure/GSPD cells stay
    # blank, matching the Fuel column's reference-row treatment.
    land = _wp("Land", 3507, 2000, FlightWaypointType.LANDING_POINT)
    land.tot = datetime.datetime(2026, 1, 1, 0, 55, 24)
    divert = _wp("Divert", None, None, FlightWaypointType.DIVERT)
    divert.tot = datetime.datetime(2026, 1, 1, 1, 9, 34)
    bullseye = _wp("Bullseye", None, None, FlightWaypointType.BULLSEYE)
    bullseye.tot = datetime.datetime(2026, 1, 1, 1, 15, 12)

    builder = _build([land, divert, bullseye])

    # The landing row keeps its planned recovery time.
    assert builder.rows[0][5] == "00:55:24"
    # GSPD / Time / Departure blank on the reference rows.
    assert builder.rows[1][4:7] == ["", "", ""]
    assert builder.rows[2][4:7] == ["", "", ""]
