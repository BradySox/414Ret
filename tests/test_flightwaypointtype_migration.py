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


def test_unknown_value_is_not_in_the_enum() -> None:
    # 36 is the value seen in the wild (one past RECOVERY_TANKER = 35).
    with pytest.raises(ValueError):
        FlightWaypointType(36)


def test_unpickler_substitutes_nav_for_unknown_value() -> None:
    unpickler = MigrationUnpickler(io.BytesIO(b""))
    migrate = unpickler._handle_flight_waypoint_type(
        "game.ato.flightwaypointtype", "FlightWaypointType"
    )
    assert migrate is not None
    # Unknown value -> NAV (passthrough nav point), not a crash.
    assert migrate(36) is FlightWaypointType.NAV
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
