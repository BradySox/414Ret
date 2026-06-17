"""Tests for the SCAR (Strike Coordination and Reconnaissance) flight type.

This is the Phase-1 planner foundation: SCAR is a selectable air-to-ground task
whose flight plan reuses the Armed Recon area/ingress machinery. The scenario
itself (HVT/decoy/clutter spawn, movement, fail-on-arrival, scoring) lives in
the SCAR Lua plugin and is validated in-game, not here. These tests lock in the
cheap-to-verify Python contract: the FlightType classification and the
builder-dispatch wiring.
"""

from unittest.mock import MagicMock

from game.ato.flighttype import FlightType
from game.ato.flightplans.flightplanbuildertypes import FlightPlanBuilderTypes
from game.ato.flightplans.scar import ScarFlightPlan


def test_scar_is_primary_air_to_ground_task() -> None:
    # SCAR is a lead/standalone ground-attack task, not an A2A or support role.
    assert FlightType.SCAR.is_air_to_ground
    assert not FlightType.SCAR.is_air_to_air
    assert FlightType.SCAR.is_primary_package_task
    assert FlightType.SCAR.entity_type.name == "ATTACK_STRIKE"


def test_scar_value_roundtrips() -> None:
    assert FlightType.from_name("SCAR") is FlightType.SCAR
    assert str(FlightType.SCAR) == "SCAR"


def test_scar_dispatches_to_scar_builder() -> None:
    flight = MagicMock()
    flight.flight_type = FlightType.SCAR
    assert FlightPlanBuilderTypes.for_flight(flight) is ScarFlightPlan.builder_type()
