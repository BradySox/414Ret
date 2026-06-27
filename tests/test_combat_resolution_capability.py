"""Unit tests for capability-weighted abstract combat resolution.

Covers the pure scoring helpers behind the P2/P3 fidelity rework (replacing the old
numbers-only coin flips in AirCombat / DefendingSam). Uses lightweight duck-typed fakes
so the math is exercised without standing up a full Game/Flight.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict

from game.ato.flighttype import FlightType
from game.sim.combat.capability import (
    air_combat_survivor_loss_chance,
    air_combat_win_probability,
    air_to_air_capability,
    air_to_air_strength,
    sam_death_chance,
)


class _FakeAircraft:
    def __init__(self, priorities: Dict[FlightType, int]) -> None:
        self._priorities = priorities

    def capable_of(self, task: FlightType) -> bool:
        return task in self._priorities

    def task_priority(self, task: FlightType) -> int:
        return self._priorities[task]


# Real-ish A2A task priorities (from the unit YAMLs): a top fighter, a legacy one, and a
# bomber with no air-to-air rating at all.
_F15 = {FlightType.BARCAP: 655, FlightType.TARCAP: 640, FlightType.SWEEP: 625}
_MIG21 = {FlightType.BARCAP: 480, FlightType.TARCAP: 480}
_BOMBER: Dict[FlightType, int] = {}


def _flight(
    priorities: Dict[FlightType, int],
    count: int = 2,
    flight_type: FlightType = FlightType.BARCAP,
) -> Any:
    return SimpleNamespace(
        unit_type=_FakeAircraft(priorities),
        count=count,
        flight_type=flight_type,
    )


def test_a2a_capability_uses_best_task_and_floor() -> None:
    assert air_to_air_capability(_flight(_F15)) == 655
    assert air_to_air_capability(_flight(_MIG21)) == 480
    # A bomber with no A2A task falls to the floor, not zero.
    assert air_to_air_capability(_flight(_BOMBER)) == 100.0


def test_a2a_strength_scales_with_count_and_floors_count() -> None:
    assert air_to_air_strength(_flight(_F15, count=2)) == 655 * 2
    # A degenerate 0-count flight is weighted as 1, never weightless.
    assert air_to_air_strength(_flight(_F15, count=0)) == 655


def test_win_probability_favours_capability_but_numbers_still_tell() -> None:
    # Better jet, equal numbers -> better than even (it was a coin flip before).
    assert air_combat_win_probability(655, 480) > 0.5
    # Two cheap jets can still overcome one good one -- numbers matter.
    assert air_combat_win_probability(655, 480 * 2) < 0.5
    # Both sides scoreless -> even odds (guard against divide-by-zero).
    assert air_combat_win_probability(0, 0) == 0.5


def test_survivor_loss_rewards_dominance_never_worse_than_legacy_half() -> None:
    # An even fight costs ~half, matching the legacy flat rate.
    assert air_combat_survivor_loss_chance(500, 500) == 0.5
    # A lopsided win bleeds few survivors.
    assert air_combat_survivor_loss_chance(1500, 300) < 0.2
    # Clamped: never above the legacy 0.5, never an impossible 0.
    assert air_combat_survivor_loss_chance(1, 1000) == 0.5
    assert air_combat_survivor_loss_chance(1000, 0) == 0.05


def test_sam_death_chance_baseline_sead_and_stacking() -> None:
    strike = _flight(_BOMBER, flight_type=FlightType.STRIKE)
    # A generic flight vs a single site is the legacy 0.5 (anchor preserved).
    assert sam_death_chance(strike, 1) == 0.5
    # A SEAD-role flight is equipped to survive -> halved.
    assert sam_death_chance(_flight(_BOMBER, flight_type=FlightType.SEAD), 1) == 0.25
    # Additional engaging sites stack the threat.
    assert sam_death_chance(strike, 3) == 0.75
    # Clamped to <= 0.95 so it is never a guaranteed loss.
    assert sam_death_chance(strike, 10) == 0.95


def test_sam_death_chance_sead_capable_airframe_also_counts() -> None:
    # Even on a non-SEAD tasking, a SEAD-capable airframe gets the survival bonus.
    sead_capable = _flight({FlightType.SEAD: 475}, flight_type=FlightType.STRIKE)
    assert sam_death_chance(sead_capable, 1) == 0.25
