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
            # The Warthog is a CAS/BAI attacker, not a heavy striker: it carries
            # no 2000 lb / penetrator class weapon, so it is intentionally kept
            # off the STRIKE lane (see resources/units/aircraft/A-10C*.yaml).
            "A-10C Thunderbolt II (Suite 7)",
            [FlightType.CAS, FlightType.BAI],
            [
                FlightType.STRIKE,
                FlightType.BARCAP,
                FlightType.TARCAP,
                FlightType.SEAD,
                FlightType.TARPS,
            ],
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


def test_transport_aircraft_can_fly_sof_insert(tmp_path: Path) -> None:
    # The SOF insert is the C-130 "drop" leg: a fixed-wing transport airdrop that
    # reuses the air-assault CTLD delivery, so transports inherit the SOF lane
    # (see AircraftType.__post_init__).
    aircraft = _aircraft(tmp_path, "C-130")
    assert aircraft.capable_of(FlightType.TRANSPORT)
    assert aircraft.capable_of(FlightType.SOF)


@pytest.mark.parametrize(
    ("variant_id", "capable"),
    [("CH-47D", True), ("C-130", True), ("F-15C Eagle", False)],
)
def test_combat_sar_eligibility(variant_id: str, capable: bool, tmp_path: Path) -> None:
    # Combat SAR (the standing pilot-rescue orbit) is flown by the CH-47 (pickup)
    # and the C-130 (HC-130 "King" orbit); fighters never get the lane.
    aircraft = _aircraft(tmp_path, variant_id)
    assert aircraft.capable_of(FlightType.COMBAT_SAR) is capable


@pytest.mark.parametrize("variant_id", ["UH-1H Iroquois", "F-15C Eagle"])
def test_sof_insert_excludes_helos_and_non_transports(
    variant_id: str, tmp_path: Path
) -> None:
    # Helicopters fly the CSAR recovery leg, not the insert, so the SOF lane must
    # not leak onto them; and aircraft without a transport lane (fighters) never
    # get it either.
    aircraft = _aircraft(tmp_path, variant_id)
    assert not aircraft.capable_of(FlightType.SOF)


def test_air_assault_helo_can_fly_csar_recovery(tmp_path: Path) -> None:
    # CSAR is the helo recovery leg of the SOF loop; helicopters that can already
    # air-assault inherit the lane (see AircraftType.__post_init__).
    aircraft = _aircraft(tmp_path, "UH-1H Iroquois")
    assert aircraft.capable_of(FlightType.AIR_ASSAULT)
    assert aircraft.capable_of(FlightType.CSAR)


@pytest.mark.parametrize("variant_id", ["C-130", "F-15C Eagle"])
def test_csar_excludes_fixed_wing(variant_id: str, tmp_path: Path) -> None:
    # The recovery leg is rotary-wing: fixed-wing transports (the SOF insert leg)
    # and fighters never get the CSAR lane.
    aircraft = _aircraft(tmp_path, variant_id)
    assert not aircraft.capable_of(FlightType.CSAR)
