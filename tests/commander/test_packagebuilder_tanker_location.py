"""Where PackageBuilder ranks squadrons from, in a tanker-led package.

Upstream ranks every flight after the first from the primary flight's departure
field, so a tanker's escort launches near the tanker it guards. U15 adds further
TANKERS to that package, and those serve the station, not the first tanker. Ranked
from the first tanker's field, a boom KC-135 flew 223 NM on Vietnam tes while one
sat at the station (review, 2026-09-17).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.ato.flighttype import FlightType
from game.commander.missionproposals import EscortType, ProposedFlight
from game.commander.packagebuilder import PackageBuilder

STATION = SimpleNamespace(name="station")
FIRST_TANKER_FIELD = SimpleNamespace(name="first tanker's field")


def _ranked_from(plan: ProposedFlight) -> Any:
    """The location PackageBuilder asks the air wing to rank squadrons from."""
    asked: list[Any] = []

    def best_squadron_for(location: Any, *args: Any, **kwargs: Any) -> None:
        asked.append(location)
        return None  # plan_flight returns early; only the location matters here

    primary = SimpleNamespace(
        flight_type=FlightType.REFUELING,
        departure=FIRST_TANKER_FIELD,
        is_helo=False,
        unit_type=SimpleNamespace(air_refuel_type=None),
    )
    builder = PackageBuilder.__new__(PackageBuilder)
    builder.package = SimpleNamespace(  # type: ignore[assignment]
        target=STATION, primary_flight=primary, flights=[primary]
    )
    builder.air_wing = SimpleNamespace(  # type: ignore[assignment]
        best_squadron_for=best_squadron_for
    )
    assert builder.plan_flight(plan, ignore_range=False) is False
    (location,) = asked
    return location


def test_a_further_tanker_is_ranked_from_the_station() -> None:
    assert _ranked_from(ProposedFlight(FlightType.REFUELING, 1)) is STATION


def test_the_tankers_escort_still_launches_near_the_tanker() -> None:
    escort = ProposedFlight(FlightType.ESCORT, 2, EscortType.AirToAir)
    assert _ranked_from(escort) is FIRST_TANKER_FIELD
