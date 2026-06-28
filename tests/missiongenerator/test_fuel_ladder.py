from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.ato.flightwaypointtype import FlightWaypointType
from game.missiongenerator.aircraft.waypoints.waypointgenerator import WaypointGenerator
from game.utils import KG_TO_LBS


def _wp(wptype: FlightWaypointType = FlightWaypointType.NAV) -> Any:
    return SimpleNamespace(waypoint_type=wptype, fuel_planned=None, min_fuel=None)


def _generator(*, taxi: float, fuel_kg: float, per_leg: float | None) -> Any:
    flight = SimpleNamespace(
        unit_type=SimpleNamespace(
            fuel_consumption=SimpleNamespace(taxi=taxi),
            estimated_fuel_consumption=None,
        ),
        fuel=fuel_kg,
        flight_plan=SimpleNamespace(
            fuel_consumption_between_points=lambda a, b, consumption=None: per_leg
        ),
    )
    gen = WaypointGenerator.__new__(WaypointGenerator)
    gen.flight = flight  # type: ignore[assignment]
    return gen


def test_planned_fuel_descends_by_leg_burn_after_taxi() -> None:
    gen = _generator(taxi=200, fuel_kg=10000.0, per_leg=1000.0)
    wps = [_wp(), _wp(), _wp()]

    gen._estimate_planned_fuel_for(wps)

    start = 10000.0 * KG_TO_LBS
    assert wps[0].fuel_planned == start - 200  # start minus taxi
    assert wps[1].fuel_planned == start - 200 - 1000  # one leg burned
    assert wps[2].fuel_planned == start - 200 - 2000  # two legs burned


def test_planned_fuel_tops_off_at_a_tanker() -> None:
    gen = _generator(taxi=0, fuel_kg=5000.0, per_leg=1000.0)
    wps = [_wp(), _wp(FlightWaypointType.REFUEL), _wp()]

    gen._estimate_planned_fuel_for(wps)

    full = 5000.0 * KG_TO_LBS
    assert wps[0].fuel_planned == full
    assert wps[1].fuel_planned == full  # refuel waypoint tops back up
    assert wps[2].fuel_planned == full - 1000  # then burns again


def test_planned_fuel_never_goes_negative() -> None:
    gen = _generator(taxi=0, fuel_kg=1.0, per_leg=100000.0)
    wps = [_wp(), _wp()]

    gen._estimate_planned_fuel_for(wps)

    assert wps[1].fuel_planned == 0.0  # clamped, not negative


def test_no_fuel_consumption_data_is_a_noop() -> None:
    flight = SimpleNamespace(
        unit_type=SimpleNamespace(
            fuel_consumption=None, estimated_fuel_consumption=None
        ),
        fuel=5000.0,
    )
    gen = WaypointGenerator.__new__(WaypointGenerator)
    gen.flight = flight  # type: ignore[assignment]
    wps = [_wp()]

    gen._estimate_planned_fuel_for(wps)

    assert wps[0].fuel_planned is None
