"""Regression tests for representative aircraft tasking lanes.

These checks are intentionally broad rather than exhaustive. They protect the
planner against role drift in a few high-signal aircraft families:

* pure fighters should stay out of strike / SEAD lanes,
* multirole strike fighters should keep their SEAD lanes,
* SEAD specialists should remain focused on SEAD,
* attackers should stay out of CAP / SEAD lanes,
* Tomcats should keep TARPS without drifting back into SEAD sweep.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pytest

from game import persistency
from game.ato.flighttype import FlightType
from game.dcs.aircrafttype import AircraftType


def _aircraft(tmp_path: Path, variant_id: str) -> AircraftType:
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16880)
    return AircraftType.named(variant_id)


@pytest.mark.parametrize(
    ("variant_id", "expected_tasks", "forbidden_tasks"),
    [
        (
            "F-15C Eagle",
            [FlightType.BARCAP, FlightType.TARCAP, FlightType.SWEEP],
            [
                FlightType.SEAD,
                FlightType.SEAD_SWEEP,
                FlightType.STRIKE,
                FlightType.TARPS,
            ],
        ),
        (
            "F-14B Tomcat",
            [FlightType.TARCAP, FlightType.STRIKE, FlightType.TARPS],
            [FlightType.SEAD, FlightType.SEAD_SWEEP],
        ),
        (
            "F/A-18C Hornet (Lot 20)",
            [
                FlightType.SEAD,
                FlightType.SEAD_ESCORT,
                FlightType.SEAD_SWEEP,
                FlightType.STRIKE,
                FlightType.TARCAP,
            ],
            [FlightType.TARPS],
        ),
        (
            "F-16CM Fighting Falcon (Block 50)",
            [
                FlightType.SEAD,
                FlightType.SEAD_ESCORT,
                FlightType.SEAD_SWEEP,
                FlightType.STRIKE,
                FlightType.TARCAP,
            ],
            [FlightType.TARPS],
        ),
        (
            "EA-18G Growler",
            [FlightType.SEAD, FlightType.SEAD_ESCORT, FlightType.SEAD_SWEEP],
            [FlightType.BARCAP, FlightType.TARCAP, FlightType.STRIKE, FlightType.TARPS],
        ),
        (
            "A-10C Thunderbolt II (Suite 7)",
            [FlightType.CAS, FlightType.BAI, FlightType.STRIKE],
            [FlightType.BARCAP, FlightType.TARCAP, FlightType.SEAD, FlightType.TARPS],
        ),
    ],
)
def test_representative_aircraft_tasking_lanes(
    variant_id: str,
    expected_tasks: Iterable[FlightType],
    forbidden_tasks: Iterable[FlightType],
    tmp_path: Path,
) -> None:
    aircraft = _aircraft(tmp_path, variant_id)

    for task in expected_tasks:
        assert aircraft.capable_of(
            task
        ), f"{variant_id} should be capable of {task.name}"

    for task in forbidden_tasks:
        assert not aircraft.capable_of(
            task
        ), f"{variant_id} should not be capable of {task.name}"
