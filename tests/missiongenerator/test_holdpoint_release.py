"""A hold must always be told to release at a time DCS will actually reach.

Flight plans are built backwards from the TOT, so a TOT the flight cannot make
puts the push before the mission starts. DCS never fires a trigger scheduled for
a negative time, so an unclamped value held the flight for the whole mission.
Found in juanjux/dcs-retribution#100 (a shipped .miz carried
``stopCondition.time = -865`` on four aircraft).
"""

from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

from game.ato.flightplans.loiter import LoiterFlightPlan
from game.missiongenerator.aircraft.waypoints.holdpoint import HoldPointBuilder
from game.utils import knots


def _stop_time_for(push_offset: timedelta) -> int:
    now = datetime(2026, 8, 19, 12, 0, 0)
    flight_plan = MagicMock(spec=LoiterFlightPlan)
    flight_plan.push_time = now + push_offset

    builder = object.__new__(HoldPointBuilder)
    builder.now = now
    builder.waypoint = SimpleNamespace(departure_time=None)  # type: ignore[assignment]
    builder.flight = SimpleNamespace(  # type: ignore[assignment]
        flight_plan=flight_plan,
        is_helo=False,
        squadron=SimpleNamespace(
            aircraft=SimpleNamespace(preferred_patrol_speed=lambda alt: knots(250))
        ),
    )

    captured: list[int] = []
    builder.add_stopping_orbit = (  # type: ignore[method-assign]
        lambda waypoint, *, speed_kph, pattern, stop_time: captured.append(stop_time)
    )
    waypoint: Any = SimpleNamespace(alt=6000, add_task=lambda task: None)
    builder.add_tasks(waypoint)
    return captured[0]


def test_an_unreachable_tot_does_not_produce_a_negative_release() -> None:
    # push 10 minutes before mission start => -660s before the clamp.
    assert _stop_time_for(timedelta(minutes=-10)) == 0


def test_a_reachable_tot_keeps_its_release_time() -> None:
    # 60s of lead time is subtracted so the flight is moving at the push.
    assert _stop_time_for(timedelta(minutes=10)) == 540
