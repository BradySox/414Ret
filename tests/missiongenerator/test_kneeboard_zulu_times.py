"""A Zulu airframe's card carries both clocks, on every page.

Reported from the cockpit 2026-08-20 (Persian Gulf, UTC+4): the F-16 DED read
10:38:37 while the Mission Info flight plan printed a 14:50:24 takeoff and the
BLUF above it printed the same event as 11:12:14Z. ``utc_kneeboard`` reached the
BLUF and the friendly-packages page; the flight-plan table, the package TOT and
the AWACS/tanker station times were still local-only.

Both times, never one: the jet needs Zulu and a package flying mixed types
coordinates off the local figure (upstream #949 review).
"""

from __future__ import annotations

import datetime
from typing import Optional
from unittest.mock import MagicMock

from dcs import Point
from dcs.terrain import Caucasus

from game.ato.flightwaypoint import FlightWaypoint
from game.ato.flightwaypointtype import FlightWaypointType
from game.missiongenerator.kneeboard import (
    FlightPlanBuilder,
    SupportPage,
    _labelled_time,
    format_kneeboard_time,
    format_kneeboard_time_inline,
)
from game.utils import NauticalUnits, feet

TIME_COLUMN = 5
DEPARTURE_COLUMN = 6

#: The reported case: Persian Gulf, whose info.yaml pins timezone +4.
GULF = datetime.timezone(datetime.timedelta(hours=4))
TAKEOFF = datetime.datetime(2026, 8, 20, 14, 50, 24)
TOT = datetime.datetime(2026, 8, 20, 15, 12, 14)


def _takeoff_row(zulu_tz: Optional[datetime.tzinfo]) -> list[str]:
    """One flight-plan row, built the way BriefingPage builds the table."""
    builder = FlightPlanBuilder(NauticalUnits(), zulu_tz=zulu_tz)
    waypoint = FlightWaypoint(
        "TAKEOFF",
        FlightWaypointType.TAKEOFF,
        Point(0, 0, Caucasus()),
        feet(191),
        "BARO",
    )
    waypoint.tot = TAKEOFF
    waypoint.departure_time = TAKEOFF + datetime.timedelta(minutes=8, seconds=52)
    builder.add_waypoint(0, waypoint)
    return builder.rows[0]


def test_flight_plan_is_local_only_for_an_airframe_that_does_not_ask() -> None:
    row = _takeoff_row(None)
    assert row[TIME_COLUMN] == "14:50:24"
    assert row[DEPARTURE_COLUMN] == "14:59:16"


def test_flight_plan_stacks_zulu_under_local() -> None:
    # Underneath rather than beside: the table is eight columns wide already.
    row = _takeoff_row(GULF)
    assert row[TIME_COLUMN].splitlines() == ["14:50:24", "10:50:24Z"]
    assert row[DEPARTURE_COLUMN].splitlines() == ["14:59:16", "10:59:16Z"]


def _support_page(zulu_tz: Optional[datetime.tzinfo]) -> SupportPage:
    flight = MagicMock()
    flight.custom_name = None
    flight.callsign = "Lobo 5"
    flight.intra_flight_channel = None
    flight.channels_for.return_value = []
    return SupportPage(
        flight,
        package_flights=[],
        comms=[],
        awacs=[],
        tankers=[],
        jtacs=[],
        dark_kneeboard=False,
        zulu_tz=zulu_tz,
    )


def test_the_support_package_line_parenthesises_its_tot() -> None:
    # Prose, not a cell: "FREQ: ...    TOT: 15:12:14 (11:12:14Z)".
    assert _support_page(None)._format_time(TOT) == "15:12:14"
    assert _support_page(GULF)._format_time(TOT) == "15:12:14 (11:12:14Z)"


def test_a_tot_cell_indents_zulu_under_the_time() -> None:
    # The narrowest column on the deck. Parenthesised, the tanker cell wrapped
    # to "TOT: 14:12:09 / (10:12:09Z) TOS: / 1:00:00" and lost the pairing.
    cell = _labelled_time("TOT:", format_kneeboard_time(TOT, GULF))
    assert cell.splitlines() == ["TOT: 15:12:14", "     11:12:14Z"]
    assert _labelled_time("TOT:", "-") == "TOT: -"


def test_every_block_of_the_page_reports_one_instant() -> None:
    # The defect was visible as a 4-hour disagreement between two blocks of the
    # same page: BLUF "TOT 11:12:14Z" over a flight-plan row reading 15:12:14.
    bluf = format_kneeboard_time_inline(TOT, GULF)
    packages = format_kneeboard_time(TOT, GULF)
    support = _support_page(GULF)._format_time(TOT)
    assert bluf == support == "15:12:14 (11:12:14Z)"
    assert packages.splitlines() == ["15:12:14", "11:12:14Z"]
