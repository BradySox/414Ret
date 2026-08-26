"""Lift-slot accounting for ground-unit airlift (game/data/airliftcapacity.py).

The point of the module is that a C-17 and a Gazelle stopped differing by one
unit, and that a tank stopped costing what an infantry squad costs. These pin
that, plus the two things that would silently break a transfer: the fallback
for an unauthored airframe, and the greedy count agreeing with the order
``PendingTransfers.split_transfer`` consumes the transfer in.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING, cast

import pytest

from game.data.airliftcapacity import (
    DEFAULT_LIFT_COST,
    LIFT_COST,
    airlift_capacity,
    lift_cost,
    units_fitting_in,
)
from game.data.units import UnitClass

if TYPE_CHECKING:
    from game.dcs.groundunittype import GroundUnitType


@dataclass(frozen=True)
class FakeGroundUnit:
    unit_class: UnitClass


@dataclass(frozen=True)
class FakeDcsType:
    helicopter: bool


@dataclass(frozen=True)
class FakeAircraft:
    dcs_unit_type: FakeDcsType
    airlift_capacity: Optional[int] = None


TANK = FakeGroundUnit(UnitClass.TANK)
INFANTRY = FakeGroundUnit(UnitClass.INFANTRY)
APC = FakeGroundUnit(UnitClass.APC)
MYSTERY = FakeGroundUnit(UnitClass.UNKNOWN)


def manifest(*entries: tuple[FakeGroundUnit, int]) -> dict[GroundUnitType, int]:
    """A transfer's unit dict, built from fakes and typed as the real thing.

    One cast site instead of a ``dict-item`` ignore on every call. Insertion
    order is preserved deliberately: it is the order ``split_transfer``
    consumes, and half of what these tests check is that the count agrees
    with it.
    """
    return cast("dict[GroundUnitType, int]", dict(entries))


def test_a_tank_costs_more_than_a_squad() -> None:
    """The defect this replaced: every vehicle cost the same."""
    assert lift_cost(TANK) > lift_cost(APC) > lift_cost(INFANTRY)  # type: ignore[arg-type]


def test_unclassified_cargo_falls_back() -> None:
    assert lift_cost(MYSTERY) == DEFAULT_LIFT_COST  # type: ignore[arg-type]


def test_every_cost_is_at_least_one_slot() -> None:
    """A free vehicle would let one aircraft lift an army."""
    assert all(cost >= 1 for cost in LIFT_COST.values())


def test_authored_capacity_wins() -> None:
    strategic = FakeAircraft(FakeDcsType(helicopter=False), airlift_capacity=11)
    assert airlift_capacity(strategic) == 11  # type: ignore[arg-type]


@pytest.mark.parametrize("helicopter,expected", [(True, 1), (False, 2)])
def test_unauthored_capacity_is_the_old_constant(
    helicopter: bool, expected: int
) -> None:
    """An airframe nobody authored must behave exactly as it did before."""
    aircraft = FakeAircraft(FakeDcsType(helicopter=helicopter))
    assert airlift_capacity(aircraft) == expected  # type: ignore[arg-type]


def test_counts_units_not_slots() -> None:
    """Four squads at one slot each fit in four slots."""
    assert units_fitting_in(manifest((INFANTRY, 4)), 4) == 4


def test_partial_load_is_counted() -> None:
    tank = lift_cost(TANK)  # type: ignore[arg-type]
    assert units_fitting_in(manifest((TANK, 3)), tank * 2) == 2


def test_an_aircraft_too_small_for_the_next_vehicle_carries_nothing() -> None:
    """Returning 0 is what stops the planner looping on a hopeless squadron."""
    assert units_fitting_in(manifest((TANK, 1)), 1) == 0


def test_the_count_stops_at_the_head_of_the_queue() -> None:
    """Must match split_transfer, which consumes the dict in its own order.

    A helo that cannot lift the leading tank takes nothing, even though the
    infantry behind it would have fitted. Counting them would describe a load
    the split would never actually hand over.
    """
    assert units_fitting_in(manifest((TANK, 1), (INFANTRY, 5)), 2) == 0


def test_a_strategic_lifter_moves_armour_and_a_helo_does_not() -> None:
    """The whole point, stated as one comparison."""
    c17 = FakeAircraft(FakeDcsType(helicopter=False), airlift_capacity=11)
    huey = FakeAircraft(FakeDcsType(helicopter=True))
    assert units_fitting_in(manifest((TANK, 1)), airlift_capacity(c17)) == 1  # type: ignore[arg-type]
    assert units_fitting_in(manifest((TANK, 1)), airlift_capacity(huey)) == 0  # type: ignore[arg-type]
