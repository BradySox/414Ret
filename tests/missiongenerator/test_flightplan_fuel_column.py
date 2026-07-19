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
from game.utils import Speed, knots


def _units() -> Any:
    # mass()/speed() return the raw pound/knot values so the rendered figures
    # equal the inputs.
    return SimpleNamespace(
        distance_short=lambda d: 0.0,
        distance_long=lambda d: 0.0,
        speed=lambda s: s.knots,
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


def _build(
    waypoints: list[Any], patrol_speed: Optional[Speed] = None
) -> FlightPlanBuilder:
    builder = FlightPlanBuilder(
        datetime.datetime(2026, 1, 1), _units(), patrol_speed=patrol_speed
    )
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


def _racetrack(dwell_min: int, burn: float, push_margin: float) -> tuple[Any, Any]:
    # A racetrack pair: arrive on station at 10:17:26 with 12461 lb, push at
    # arrival + dwell having burned `burn` on station, `push_margin` above the
    # minimum to get home at push time.
    start = _wp("Race-track start", 12461.0, None, FlightWaypointType.PATROL_TRACK)
    start.tot = datetime.datetime(2026, 1, 1, 10, 17, 26)
    end = _wp(
        "Race-track end",
        12461.0 - burn,
        12461.0 - burn - push_margin,
        FlightWaypointType.PATROL,
    )
    end.tot = start.tot + datetime.timedelta(minutes=dwell_min)
    end.departure_time = end.tot
    return start, end


def test_racetrack_end_gspd_is_the_patrol_speed_not_track_over_dwell() -> None:
    # The racetrack-end row's schedule time is the on-station dwell (arrive
    # 10:17, push 11:02), so distance / time printed nonsense (a 13.9 nm track
    # over 45 minutes = 19 kt). The cell shows the planned patrol speed instead.
    start, end = _racetrack(dwell_min=45, burn=4500.0, push_margin=500.0)
    builder = _build([start, end], patrol_speed=knots(482))
    assert builder.rows[1][4] == "482"


def test_racetrack_end_gspd_dashes_without_a_patrol_speed() -> None:
    # A PATROL row with no patrol speed available (custom plan) never falls back
    # to the meaningless distance-over-dwell figure.
    start, end = _racetrack(dwell_min=45, burn=4500.0, push_margin=500.0)
    builder = _build([start, end])
    assert builder.rows[1][4] == "-"


def test_patrol_endurance_line_reports_station_time_the_fuel_supports() -> None:
    # 45 min planned at 100 lb/min on station, +500 lb over bingo at push: the
    # gas supports ~50 minutes before the RTB minimum.
    start, end = _racetrack(dwell_min=45, burn=4500.0, push_margin=500.0)
    builder = _build([start, end], patrol_speed=knots(482))
    assert builder.patrol_endurance_line() == (
        "On station 45 min planned; fuel supports ~50 min before bingo "
        "(RTB minimum)."
    )
    assert not builder.patrol_endurance_is_short


def test_patrol_endurance_line_warns_when_fuel_cuts_the_station_short() -> None:
    # Negative margin at push: the gas runs out before the planned departure.
    start, end = _racetrack(dwell_min=45, burn=4500.0, push_margin=-400.0)
    builder = _build([start, end], patrol_speed=knots(482))
    assert builder.patrol_endurance_line() == (
        "On station 45 min planned; fuel supports ~41 min before bingo "
        "(RTB minimum)."
    )
    assert builder.patrol_endurance_is_short


def test_no_racetrack_means_no_endurance_line() -> None:
    assert _build(_LADDER).patrol_endurance_line() is None
