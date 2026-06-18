"""Unknown FlightWaypointType tolerance.

A save written by a build whose FlightWaypointType enum had a value this fork
lacks (e.g. an upstream/experimental or renumbered SCAR waypoint type) must not
abort the whole load. The unpickler substitutes NAV for any unknown value so the
campaign still loads; live values pass through unchanged.
"""

from __future__ import annotations

import io

import pytest

from game.ato.flightwaypointtype import FlightWaypointType
from game.persistency import MigrationUnpickler

# A value guaranteed not to be in the enum (computed so adding new waypoint types
# can never make it collide with a real member, as happened with a hard-coded 36).
UNKNOWN_VALUE = max(member.value for member in FlightWaypointType) + 100


def test_unknown_value_is_not_in_the_enum() -> None:
    with pytest.raises(ValueError):
        FlightWaypointType(UNKNOWN_VALUE)


def test_unpickler_substitutes_nav_for_unknown_value() -> None:
    unpickler = MigrationUnpickler(io.BytesIO(b""))
    migrate = unpickler._handle_flight_waypoint_type(
        "game.ato.flightwaypointtype", "FlightWaypointType"
    )
    assert migrate is not None
    # Unknown value -> NAV (passthrough nav point), not a crash.
    assert migrate(UNKNOWN_VALUE) is FlightWaypointType.NAV
    # Live values are unaffected.
    assert migrate(5) is FlightWaypointType.INGRESS_STRIKE
    assert migrate(35) is FlightWaypointType.RECOVERY_TANKER


def test_unpickler_ignores_non_flight_waypoint_type() -> None:
    unpickler = MigrationUnpickler(io.BytesIO(b""))
    assert (
        unpickler._handle_flight_waypoint_type(
            "game.ato.flightwaypointtype", "Squadron"
        )
        is None
    )
    assert (
        unpickler._handle_flight_waypoint_type(
            "some.other.module", "FlightWaypointType"
        )
        is None
    )
