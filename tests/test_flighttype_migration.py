"""Legacy FlightType migration.

The 414th's retired SCRAMBLE QRA flight type (and the older ISR type) must map
onto their live equivalents so campaigns saved on older builds still load. Both
the runtime ``_missing_`` path and the unpickler path are covered.
"""

from __future__ import annotations

import io

from game.ato.flighttype import FlightType, _LEGACY_FLIGHT_TYPE_VALUES
from game.persistency import MigrationUnpickler


def test_scramble_is_gone_from_the_enum() -> None:
    assert not any(member.value == "Scramble" for member in FlightType)


def test_missing_maps_legacy_values() -> None:
    # Enum value lookup (the path pickle uses to rehydrate an enum member).
    assert FlightType("Scramble") is FlightType.BARCAP
    assert FlightType("ISR") is FlightType.JAMMING
    assert FlightType("Cargo Transport") is FlightType.TRANSPORT
    # Live values are unaffected.
    assert FlightType("BARCAP") is FlightType.BARCAP


def test_unpickler_flight_type_migration() -> None:
    unpickler = MigrationUnpickler(io.BytesIO(b""))
    migrate = unpickler._handle_flight_type("game.ato.flighttype", "FlightType")
    assert migrate is not None
    # The unpickler keeps no remap table of its own: these resolve through
    # FlightType._missing_ via FlightType(value).
    assert migrate("Scramble") is FlightType.BARCAP
    assert migrate("ISR") is FlightType.JAMMING
    assert migrate("Cargo Transport") is FlightType.TRANSPORT
    assert migrate("TARCAP") is FlightType.TARCAP


def test_legacy_table_is_single_source_for_both_paths() -> None:
    # Every legacy remap must resolve identically through the runtime path
    # (FlightType(value)) and the unpickler path -- proving the table is the
    # one source of truth and the unpickler no longer duplicates it.
    unpickler = MigrationUnpickler(io.BytesIO(b""))
    migrate = unpickler._handle_flight_type("game.ato.flighttype", "FlightType")
    assert migrate is not None
    assert _LEGACY_FLIGHT_TYPE_VALUES  # guard against an empty table
    for legacy_value, expected in _LEGACY_FLIGHT_TYPE_VALUES.items():
        assert FlightType(legacy_value) is expected
        assert migrate(legacy_value) is expected


def test_unpickler_substitutes_barcap_for_unknown_value() -> None:
    # A save with a flight type this build lacks (e.g. SCAR loaded by a build
    # without it) must degrade, not crash the whole load.
    unknown = "NotARealFlightType-xxxxxxxx"
    assert unknown not in {member.value for member in FlightType}
    unpickler = MigrationUnpickler(io.BytesIO(b""))
    migrate = unpickler._handle_flight_type("game.ato.flighttype", "FlightType")
    assert migrate is not None
    assert migrate(unknown) is FlightType.BARCAP


def test_unpickler_ignores_non_flight_type() -> None:
    unpickler = MigrationUnpickler(io.BytesIO(b""))
    assert unpickler._handle_flight_type("game.ato.flighttype", "Squadron") is None
    assert unpickler._handle_flight_type("some.other.module", "FlightType") is None
