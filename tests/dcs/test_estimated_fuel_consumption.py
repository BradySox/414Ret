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
    # No measured Fulcrum block, so it should fall back to the combat bucket. (The
    # A-10C used to stand here; it gained a measured block when the DCS Liberation
    # fuel data was adopted, which is exactly the case this test must *not* use.)
    fulcrum = AircraftType.named("MiG-29A Fulcrum-A")
    assert fulcrum.fuel_consumption is None
    assert not fulcrum._is_heavy_airframe
    est = fulcrum.estimated_fuel_consumption
    assert est is not None
    # Calibrated against the measured references (Hornet ~22, Viper ~12 ppm).
    assert 10 < est.cruise < 35


def test_measured_block_is_unaffected_by_the_estimate() -> None:
    # The Hornet ships a measured block; the estimate is a separate, independent value
    # and must never be substituted for it.
    hornet = AircraftType.named("F/A-18C Hornet (Lot 20)")
    assert hornet.fuel_consumption is not None
    assert hornet.fuel_consumption.cruise == 22.1  # the hand-measured number stands


#: Cruise ppm for the airframes whose measured ``fuel:`` blocks were adopted from DCS
#: Liberation. Before adoption these fell back to the capacity-derived estimate, which
#: overshot the measured burn by +35% (A-4E) to +140% (F-14) and so drew a needlessly
#: pessimistic kneeboard bingo ladder.
#: Every variant is listed, so the block reaching the variants (F-15J, the Phantom
#: export marks, ...) is pinned too and not just the base airframe.
ADOPTED_CRUISE_PPM = {
    "A-10A Thunderbolt II": 12,
    "A-10C Thunderbolt II (Suite 3)": 12,
    "A-10C Thunderbolt II (Suite 7)": 12,
    "A-4E Skyhawk": 7.7,
    "AV-8B Harrier II Night Attack": 11,
    "F-100D": 9,
    "F-100D Super Sabre": 9,
    "F-14A Tomcat (Block 95-GR Export)": 13,
    "F-14A Tomcat (Block 135-GR Early)": 13,
    "F-14A Tomcat (Block 135-GR Late)": 13,
    "F-14B Tomcat": 13,
    "F-15C Eagle": 11,
    "F-15J Eagle": 11,
    "F-4E-45MC Phantom II": 17,
    "F-4EJ Phantom II": 17,
    "Phantom FGR.2": 17,
}


@pytest.mark.parametrize(("name", "cruise"), sorted(ADOPTED_CRUISE_PPM.items()))
def test_adopted_fuel_data_is_present_and_measured(name: str, cruise: float) -> None:
    aircraft = AircraftType.named(name)
    measured = aircraft.fuel_consumption
    # A real ``fuel:`` block must win over the estimate -- losing it here would silently
    # drop these airframes back onto the capacity-derived approximation.
    assert measured is not None, f"{name} lost its measured fuel: block"
    assert measured.cruise == cruise
    assert measured.climb > measured.cruise
    assert measured.combat > measured.cruise
    assert measured.taxi > 0
    assert measured.min_safe > 0
