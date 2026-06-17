"""Tests for the SCAR (Strike Coordination and Reconnaissance) flight type.

Phase-1 planner work: SCAR is a selectable, opt-in air-to-ground task whose
flight plan reuses the Armed Recon area/ingress machinery. The scenario itself
(HVT/decoy/clutter spawn, movement, fail-on-arrival, scoring) lives in the SCAR
Lua plugin and is validated in-game, not here. These tests lock in the
cheap-to-verify Python contract: the FlightType classification, builder dispatch,
fixed-wing capability gating, and target exposure.
"""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from dcs.mapping import Point

from game import persistency
from game.ato.flighttype import FlightType
from game.ato.flightplans.flightplanbuildertypes import FlightPlanBuilderTypes
from game.ato.flightplans.scar import ScarFlightPlan
from game.dcs.aircrafttype import AircraftType
from game.theater.controlpoint import OffMapSpawn, Player
from game.theater.presetlocation import PresetLocation
from game.theater.theatergroundobject import SamGroundObject, TheaterGroundObject
from game.utils import Heading

# Fixed-wing CAS airframe -> SCAR-capable; CAS-capable helo -> NOT SCAR-capable.
A10_VARIANT_ID = "A-10C Thunderbolt II (Suite 3)"
APACHE_VARIANT_ID = "AH-64D Apache Longbow (AI)"


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


def test_fixed_wing_cas_airframe_is_scar_capable(tmp_path: Path) -> None:
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16880)
    a10 = AircraftType.named(A10_VARIANT_ID)
    assert a10.capable_of(FlightType.CAS)
    assert a10.capable_of(FlightType.SCAR)


def test_helicopter_cas_airframe_is_not_scar_capable(tmp_path: Path) -> None:
    # SCAR is a fixed-wing convoy-hunt task; a CAS-capable helo must be excluded
    # even though it has CAS, so the enrichment gate stays fixed-wing only.
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16880)
    apache = AircraftType.named(APACHE_VARIANT_ID)
    assert apache.capable_of(FlightType.CAS)
    assert not apache.capable_of(FlightType.SCAR)


def test_scar_is_offered_against_enemy_targets(monkeypatch: pytest.MonkeyPatch) -> None:
    # SCAR rides the base offensive mission_types set, so any enemy ground object
    # exposes it (here a SAM site, matching the TARPS-test fixture pattern).
    monkeypatch.setattr(TheaterGroundObject, "is_friendly", lambda self, player: False)
    location = PresetLocation(
        name="loc", position=Point(0, 0, None), heading=Heading(0)  # type: ignore
    )
    control_point = OffMapSpawn(
        name="cp",
        position=Point(0, 0, None),  # type: ignore
        theater=None,  # type: ignore
        starts_blue=Player.BLUE,
    )
    sam = SamGroundObject(
        name="sam", location=location, control_point=control_point, task=None
    )
    assert FlightType.SCAR in list(sam.mission_types(for_player=Player.RED))


def test_scar_not_offered_against_friendly_targets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(TheaterGroundObject, "is_friendly", lambda self, player: True)
    location = PresetLocation(
        name="loc", position=Point(0, 0, None), heading=Heading(0)  # type: ignore
    )
    control_point = OffMapSpawn(
        name="cp",
        position=Point(0, 0, None),  # type: ignore
        theater=None,  # type: ignore
        starts_blue=Player.BLUE,
    )
    sam = SamGroundObject(
        name="sam", location=location, control_point=control_point, task=None
    )
    assert FlightType.SCAR not in list(sam.mission_types(for_player=Player.BLUE))
