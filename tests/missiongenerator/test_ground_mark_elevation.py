"""A client's ground-marked steerpoint carries the terrain's elevation.

Reported from the cockpit 2026-08-20: the DEAD steerpoint does not sit at 0 AGL,
it sits at 0 MSL. Every consumer wrote `alt 0` with a RADIO/altitudeType-2 flag
beside it, and the number still reached the jet as sea level -- so a target on
high ground had a steerpoint under the terrain and nothing to slave a pod to.

The three consumers -- the generated .miz, the DTC cartridge and the kneeboard's
Alt column -- now share one rule, so the card, the jet and the AI agree. Where the
campaign sampled no elevation (front line, convoys, relocated mobile SAMs) the old
0 AGL stands.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Iterator

import pytest
from dcs import Point
from dcs.terrain import Caucasus

from game.ato.flightwaypoint import FlightWaypoint, ground_mark_altitude
from game.ato.flightwaypointtype import FlightWaypointType
from game.missiongenerator.dtc.common import client_altitude
from game.missiongenerator.kneeboard import FlightPlanBuilder
from game.theater import terrainelevation
from game.theater.terrainelevation import TerrainElevations
from game.utils import NauticalUnits, feet

ALT_COLUMN = 2
TERRAIN = "FakeTerrain"


@pytest.fixture
def theater() -> Iterator[Any]:
    """A theater whose table puts 600 m of ground under the origin."""
    terrainelevation._cache[TERRAIN] = TerrainElevations(100, {(0, 0): 600.0})
    yield SimpleNamespace(terrain=SimpleNamespace(name=TERRAIN))
    terrainelevation._cache.clear()


@pytest.fixture
def bare_theater() -> Iterator[Any]:
    """A theater with no sampled points at all."""
    terrainelevation._cache[TERRAIN] = TerrainElevations(100, {})
    yield SimpleNamespace(terrain=SimpleNamespace(name=TERRAIN))
    terrainelevation._cache.clear()


def _target() -> FlightWaypoint:
    wp = FlightWaypoint(
        "TARGET",
        FlightWaypointType.TARGET_GROUP_LOC,
        Point(0, 0, Caucasus()),
        feet(22000),  # the AI's track altitude; the client must not see it
        "RADIO",
    )
    wp.pretty_name = "DEAD on DUCK"
    return wp


def test_a_sampled_target_is_written_at_the_terrain_elevation(theater: Any) -> None:
    altitude, reference = ground_mark_altitude(_target(), theater)
    assert round(altitude.meters) == 600
    assert reference == "BARO"


def test_an_unsampled_target_keeps_the_old_zero_agl(bare_theater: Any) -> None:
    altitude, reference = ground_mark_altitude(_target(), bare_theater)
    assert altitude.meters == 0
    assert reference == "RADIO"


def test_the_cartridge_writes_the_same_number(theater: Any) -> None:
    # altitudeType 1 = BARO, 2 = RADIO. The cartridge must agree with the .miz or
    # AutoLoad floats the steerpoint back to the AI's track altitude.
    assert client_altitude(_target(), theater) == (600.0, 1)


def test_the_cartridge_keeps_zero_agl_where_nothing_was_sampled(
    bare_theater: Any,
) -> None:
    assert client_altitude(_target(), bare_theater) == (0.0, 2)


def test_the_kneeboard_alt_column_reads_the_same_ground(theater: Any) -> None:
    builder = FlightPlanBuilder(NauticalUnits(), theater=theater)
    builder.add_waypoint(1, _target())
    assert builder.rows[0][ALT_COLUMN] == "1969"  # 600 m


def test_the_kneeboard_alt_column_still_reads_zero_without_a_theater() -> None:
    # Every existing caller that builds a table without one is unchanged.
    builder = FlightPlanBuilder(NauticalUnits())
    builder.add_waypoint(1, _target())
    assert builder.rows[0][ALT_COLUMN] == "0"
