"""Tests for the capacity-derived fuel-consumption estimate.

The estimate exists so the kneeboard fuel ladder renders for the many airframes
(the C-130J "King", helicopters, warbirds, ...) that ship no hand-measured
``fuel:`` data block. It is deliberately *not* wired into ``fuel_consumption`` so
the planner and in-flight sim are unaffected.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from game import persistency
from game.dcs.aircrafttype import AircraftType


@pytest.fixture(autouse=True)
def _persistency(tmp_path: Path) -> None:
    # AircraftType.named() loads the unit data files, which reach for the saved-games
    # folder; point it at a throwaway dir so the registry can populate.
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16884)


def test_c130_king_has_an_estimate_and_is_treated_as_a_heavy() -> None:
    # The reported case: the C-130J King kneeboard said "No fuel estimate available".
    c130 = AircraftType.named("C-130J-30")
    assert c130.fuel_consumption is None  # ships no measured block
    assert c130._is_heavy_airframe

    est = c130.estimated_fuel_consumption
    assert est is not None
    # A C-130J cruises ~15-18 ppm; the heavy bucket should land in a sane band, not
    # the ~80 ppm a fighter-calibrated model would produce for its huge tanks.
    assert 10 < est.cruise < 25
    # Climb/combat are multiples of cruise, never cheaper than it.
    assert est.climb > est.cruise
    assert est.combat > est.cruise
    assert est.min_safe > 0
    assert est.taxi > 0


def test_helicopter_uses_the_low_endurance_helo_bucket() -> None:
    chinook = AircraftType.named("CH-47F Block I")
    assert chinook.helicopter
    est = chinook.estimated_fuel_consumption
    assert est is not None
    # Helos sip far less than a fast jet but still measurably; just sanity-bound it.
    assert 0 < est.cruise < 40


def test_fighter_estimate_is_in_a_reasonable_band() -> None:
    # No measured A-10C block, so it should fall back to the combat bucket.
    a10 = AircraftType.named("A-10C Thunderbolt II (Suite 7)")
    assert a10.fuel_consumption is None
    assert not a10._is_heavy_airframe
    est = a10.estimated_fuel_consumption
    assert est is not None
    # Calibrated against the measured references (Hornet ~22, Viper ~12 ppm).
    assert 10 < est.cruise < 35


def test_measured_block_is_unaffected_by_the_estimate() -> None:
    # The Hornet ships a measured block; the estimate is a separate, independent value
    # and must never be substituted for it.
    hornet = AircraftType.named("F/A-18C Hornet (Lot 20)")
    assert hornet.fuel_consumption is not None
    assert hornet.fuel_consumption.cruise == 22.1  # the hand-measured number stands
