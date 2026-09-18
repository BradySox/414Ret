"""The refuel waypoint has to earn its place in the route.

Test 36 (2026-09-17): a B-1B that had burned 11% of its fuel flew 66 km PAST
Incirlik to a tanker, arriving at 0.894 with unlimited fuel already switched on
at the split, and was still out there when the mission ended. The waypoint was
planned because the coalition owns tankers, never because the jet needed gas.
Generation now drops it when the sortie's DRY margin -- the walk with no
top-off applied -- clears the airframe's landing reserve with room.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from game.missiongenerator.aircraft.waypoints.waypointgenerator import WaypointGenerator
from game.retlab.fuel_brief import FuelBrief


def _generator(has_refuel_point: bool = True) -> WaypointGenerator:
    from game.ato.flightwaypointtype import FlightWaypointType

    points = (
        [SimpleNamespace(waypoint_type=FlightWaypointType.REFUEL)]
        if has_refuel_point
        else [SimpleNamespace(waypoint_type=FlightWaypointType.NAV)]
    )
    generator = WaypointGenerator.__new__(WaypointGenerator)
    generator.flight = SimpleNamespace(points=points)  # type: ignore[assignment]
    return generator


def _brief(
    *, dry_margin_lbs: float, estimated: bool, refuel_passes: int = 1
) -> FuelBrief:
    return FuelBrief(
        internal_lbs=10000.0,
        external_lbs=0.0,
        tank_count=0,
        burn_lbs=4000.0,
        reserve_lbs=1500.0,
        refuel_passes=refuel_passes,
        margin_lbs=dry_margin_lbs,
        dry_margin_lbs=dry_margin_lbs,
        estimated=estimated,
    )


def _with_brief(monkeypatch: pytest.MonkeyPatch, brief: Any) -> None:
    monkeypatch.setattr("game.retlab.fuel_brief.fuel_brief_for", lambda _flight: brief)


@pytest.mark.parametrize(
    "dry_margin_lbs, estimated, dropped",
    [
        # Measured data: two reserves of spare is enough.
        (3000.0, False, True),
        (2999.0, False, False),
        # A synthesised model is a guess, so it has to clear three.
        (4500.0, True, True),
        (3000.0, True, False),
        # Short of the reserve entirely -- the flight needs the gas.
        (-500.0, False, False),
        (-500.0, True, False),
    ],
)
def test_the_drop_scales_with_how_good_the_fuel_data_is(
    monkeypatch: pytest.MonkeyPatch,
    dry_margin_lbs: float,
    estimated: bool,
    dropped: bool,
) -> None:
    _with_brief(monkeypatch, _brief(dry_margin_lbs=dry_margin_lbs, estimated=estimated))
    assert _generator().gets_home_without_the_tanker() is dropped


def test_an_airframe_with_no_fuel_model_keeps_its_tanker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """217 airframes carry no measured fuel block. Absent any model at all the
    planner's decision stands -- a guess is not grounds to remove a tanker."""
    _with_brief(monkeypatch, None)
    assert _generator().gets_home_without_the_tanker() is False


def test_a_route_with_no_refuel_waypoint_drops_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _with_brief(
        monkeypatch, _brief(dry_margin_lbs=90000.0, estimated=False, refuel_passes=0)
    )
    assert _generator().gets_home_without_the_tanker() is False
    # And the route is checked first, so the fuel walk is skipped entirely for
    # the flights that make up most of an ATO.
    _with_brief(monkeypatch, _brief(dry_margin_lbs=90000.0, estimated=False))
    assert _generator(has_refuel_point=False).gets_home_without_the_tanker() is False
