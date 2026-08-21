"""Every time on a Zulu airframe's card reads Zulu, not just the BLUF's TOT.

Reported from the cockpit 2026-08-20 (Persian Gulf, UTC+4): the F-16 DED read
10:38:37 while the Mission Info flight plan printed a 14:50:24 takeoff and the
BLUF above it printed the same event as 11:12:14Z. ``utc_kneeboard`` reached the
BLUF and the friendly-packages page; the flight-plan table, the package TOT and
the AWACS/tanker station times were still on the mission clock.
"""

from __future__ import annotations

import datetime
from types import SimpleNamespace
from typing import Any, Optional
from unittest.mock import MagicMock

from dcs import Point
from dcs.terrain import Caucasus

from game.ato.flightwaypoint import FlightWaypoint
from game.ato.flightwaypointtype import FlightWaypointType
from game.missiongenerator.kneeboard import (
    FlightPlanBuilder,
    KneeboardGenerator,
    SupportPage,
    _format_clock,
)
from game.utils import NauticalUnits, feet

TIME_COLUMN = 5
DEPARTURE_COLUMN = 6

#: The reported case: Persian Gulf, whose info.yaml pins timezone +4.
GULF = datetime.timezone(datetime.timedelta(hours=4))


def _waypoint(tot: datetime.datetime, departure: datetime.datetime) -> FlightWaypoint:
    wp = FlightWaypoint(
        "TAKEOFF",
        FlightWaypointType.TAKEOFF,
        Point(0, 0, Caucasus()),
        feet(191),
        "BARO",
    )
    wp.tot = tot
    wp.departure_time = departure
    return wp


def _row(zulu_tz: Optional[datetime.tzinfo]) -> list[str]:
    builder = FlightPlanBuilder(
        datetime.datetime(2026, 8, 20, 14, 50, 24),
        NauticalUnits(),
        zulu_tz=zulu_tz,
    )
    builder.add_waypoint(
        0,
        _waypoint(
            datetime.datetime(2026, 8, 20, 14, 50, 24),
            datetime.datetime(2026, 8, 20, 14, 59, 16),
        ),
    )
    return builder.rows[0]


def test_flight_plan_stays_on_the_mission_clock_without_a_zulu_airframe() -> None:
    row = _row(None)
    assert row[TIME_COLUMN] == "14:50:24"
    assert row[DEPARTURE_COLUMN] == "14:59:16"


def test_flight_plan_converts_for_a_zulu_airframe() -> None:
    row = _row(GULF)
    assert row[TIME_COLUMN] == "10:50:24Z"
    assert row[DEPARTURE_COLUMN] == "10:59:16Z"


def _support_page(zulu_tz: Optional[datetime.tzinfo]) -> SupportPage:
    flight = MagicMock()
    flight.custom_name = None
    flight.callsign = "Enfield 1-1"
    flight.intra_flight_channel = None
    flight.channels_for.return_value = []
    return SupportPage(
        flight,
        package_flights=[],
        comms=[],
        awacs=[],
        tankers=[],
        jtacs=[],
        start_time=MagicMock(),
        dark_kneeboard=False,
        zulu_tz=zulu_tz,
    )


def test_support_page_station_times_follow_the_same_clock() -> None:
    # The package TOT line and the AWACS/tanker TOT cells all render through
    # this one formatter, so pinning it pins the whole Support Info page.
    tot = datetime.datetime(2026, 8, 20, 15, 12, 14)
    assert _support_page(None)._format_time(tot) == "15:12:14"
    assert _support_page(GULF)._format_time(tot) == "11:12:14Z"


def _generator(utc: bool) -> KneeboardGenerator:
    game: Any = SimpleNamespace(
        settings=SimpleNamespace(generate_dark_kneeboard=False),
        theater=SimpleNamespace(timezone=GULF),
    )
    mission = SimpleNamespace(start_time=SimpleNamespace(hour=12))
    return KneeboardGenerator(mission, game)  # type: ignore[arg-type]


def test_the_bluf_tot_and_the_flight_plan_agree_on_one_instant() -> None:
    # The defect was visible as a 4-hour disagreement between two blocks of the
    # same page: BLUF "TOT 11:12:14Z" over a flight plan row reading 15:12:14.
    tot = datetime.datetime(2026, 8, 20, 15, 12, 14)
    bluf = _format_clock(_generator(utc=True)._to_kneeboard_time(tot, utc=True))
    builder = FlightPlanBuilder(tot, NauticalUnits(), zulu_tz=GULF)
    builder.add_waypoint(0, _waypoint(tot, tot))
    assert bluf == builder.rows[0][TIME_COLUMN] == "11:12:14Z"
