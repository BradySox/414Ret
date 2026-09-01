"""The join->ingress leg is paced by the package, and cruise mach is per airframe.

Both halves answer the same measured defect: a package's light escorts ran ahead of
the strikers they were escorting because that leg was the one transit segment every
flight priced on its own. See docs/dev/design/414th-cruise-mach-notes.md.
"""

from __future__ import annotations

from typing import cast

import pytest
from dcs import Point
from dcs.terrain import Caucasus, Terrain

from game.ato.flight import Flight
from game.ato.flightplans.formationattack import (
    FormationAttackFlightPlan,
    FormationAttackLayout,
)
from game.ato.flightwaypoint import FlightWaypoint
from game.ato.flightwaypointtype import FlightWaypointType
from game.ato.traveltime import DEFAULT_CRUISE_MACH, GroundSpeed
from game.utils import SPEED_OF_SOUND_AT_SEA_LEVEL, Speed, feet, kph, mach


class _StubUnitType:
    def __init__(self, max_speed: Speed, cruise_mach: float | None) -> None:
        self.max_speed = max_speed
        self.cruise_mach = cruise_mach


class _StubFlight:
    def __init__(self, unit_type: _StubUnitType, is_helo: bool = False) -> None:
        self.unit_type = unit_type
        self.is_helo = is_helo


def _flight(
    max_speed: Speed, cruise_mach: float | None, is_helo: bool = False
) -> Flight:
    return cast(Flight, _StubFlight(_StubUnitType(max_speed, cruise_mach), is_helo))


SUPERSONIC = kph(1950.12)  # F/A-18C
SUBSONIC = kph(720.0)  # A-10C


def test_unauthored_supersonic_jet_keeps_the_default_cruise_mach() -> None:
    speed = GroundSpeed.for_flight(_flight(SUPERSONIC, None), feet(21000))
    assert speed == mach(DEFAULT_CRUISE_MACH, feet(21000))


def test_authored_cruise_mach_wins_for_a_supersonic_jet() -> None:
    altitude = feet(21000)
    speed = GroundSpeed.for_flight(_flight(SUPERSONIC, 0.78), altitude)
    assert speed == mach(0.78, altitude)
    # The whole point: it is slower than the flat default it replaces.
    assert speed < mach(DEFAULT_CRUISE_MACH, altitude)


def test_authored_cruise_mach_wins_for_a_subsonic_aircraft() -> None:
    altitude = feet(16000)
    assert SUBSONIC < SPEED_OF_SOUND_AT_SEA_LEVEL
    speed = GroundSpeed.for_flight(_flight(SUBSONIC, 0.55), altitude)
    assert speed == mach(0.55, altitude)


def test_unauthored_subsonic_aircraft_still_derives_from_max_speed() -> None:
    altitude = feet(16000)
    speed = GroundSpeed.for_flight(_flight(SUBSONIC, None), altitude)
    assert speed == mach(SUBSONIC.mach() * 0.85, altitude)


def test_unauthored_helo_keeps_its_own_factor() -> None:
    altitude = feet(2000)
    speed = GroundSpeed.for_flight(_flight(SUBSONIC, None, is_helo=True), altitude)
    assert speed == mach(SUBSONIC.mach() * 0.7, altitude)


def _waypoint(name: str, waypoint_type: FlightWaypointType) -> FlightWaypoint:
    terrain: Terrain = Caucasus()
    return FlightWaypoint(name, waypoint_type, Point(0, 0, terrain))


@pytest.fixture(name="layout")
def layout_fixture() -> FormationAttackLayout:
    return FormationAttackLayout(
        departure=_waypoint("TAKEOFF", FlightWaypointType.TAKEOFF),
        hold=None,
        nav_to=[],
        join=_waypoint("JOIN", FlightWaypointType.JOIN),
        ingress=_waypoint("INGRESS", FlightWaypointType.INGRESS_STRIKE),
        targets=[_waypoint("TARGET", FlightWaypointType.TARGET_POINT)],
        split=_waypoint("SPLIT", FlightWaypointType.SPLIT),
        refuel=None,
        nav_from=[],
        arrival=_waypoint("LANDING", FlightWaypointType.LANDING_POINT),
        divert=None,
        bullseye=_waypoint("BULLSEYE", FlightWaypointType.BULLSEYE),
        custom_waypoints=[],
    )


class _PlanUnderTest(FormationAttackFlightPlan):
    def __init__(self, layout: FormationAttackLayout) -> None:
        self.layout = layout


def test_ingress_is_paced_by_the_package(layout: FormationAttackLayout) -> None:
    plan = _PlanUnderTest(layout)
    assert layout.ingress in plan.package_speed_waypoints
    assert layout.join in plan.package_speed_waypoints
    assert layout.split in plan.package_speed_waypoints
    assert layout.targets[0] in plan.package_speed_waypoints


def test_ingress_is_not_charged_combat_fuel(layout: FormationAttackLayout) -> None:
    # Fuel burn is priced off combat_speed_waypoints. Pacing the ingress leg with
    # the package must not silently re-price every strike package's fuel.
    plan = _PlanUnderTest(layout)
    assert layout.ingress not in plan.combat_speed_waypoints
    assert plan.combat_speed_waypoints == {
        layout.join,
        layout.split,
        layout.targets[0],
    }
