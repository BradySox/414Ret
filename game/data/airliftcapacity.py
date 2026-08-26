"""How much room a ground unit takes on an aircraft, and how much room it has.

Airlift capacity used to be one constant for the whole game --
``1 if helicopter else 2`` ground units per aircraft, in
``AirliftPlanner.create_airlift_flight``. That said a Gazelle and a C-17 differ
by one unit, and that a main battle tank and an infantry squad are the same
cargo.

Both halves are now graded in one unit, the **lift slot**, anchored at roughly
**seven tonnes** -- one army truck. The anchor is what makes these tables
re-derivable instead of taste: a class costs its representative vehicle's combat
weight over seven, and an aircraft carries its published maximum payload over
seven, floored at one. Neither is measured inside DCS. This is a proportionality
model, and the anchor is what keeps the two halves proportional to each other.

``cabin_size`` is NOT this, and must not be used for it. That field counts CTLD
infantry seats; it is deliberately clamped below the real figure for gameplay
(``CH-47D.yaml``: "It should have 33 but we do not want so much for CTLD to be
possible") and it is flat across lift classes -- the C-17A and the An-26B are
both 24, though one carries an Abrams and the other carries light freight.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from game.data.units import UnitClass

if TYPE_CHECKING:
    from game.dcs.aircrafttype import AircraftType
    from game.dcs.groundunittype import GroundUnitType

#: Tonnes of cargo one lift slot represents. Only used to derive the tables
#: below; nothing reads it at runtime. Kept here so the next person editing a
#: number knows what the number means.
TONNES_PER_SLOT = 7.0

#: Cost for a class with no entry below, and for ``UnitClass.UNKNOWN``. Sized as
#: a light armoured vehicle: heavy enough that unclassified cargo is not free,
#: light enough that it does not strand a transfer.
DEFAULT_LIFT_COST = 3

#: Lift slots consumed by one vehicle of each class, from the representative
#: vehicle's combat weight. Ship and aircraft classes are absent on purpose --
#: they never appear in a ground transfer, and fall to ``DEFAULT_LIFT_COST``.
LIFT_COST: dict[UnitClass, int] = {
    # A squad walks aboard.
    UnitClass.INFANTRY: 1,
    UnitClass.MANPAD: 1,
    # Light wheeled: BRDM-2 at 7 t, Ural-375 at 9 t, a ZU-23 on a truck bed.
    UnitClass.RECON: 1,
    UnitClass.LOGISTICS: 1,
    UnitClass.AAA: 1,
    UnitClass.ATGM: 1,
    UnitClass.SEARCH_LIGHT: 1,
    UnitClass.OPTICAL_TRACKER: 1,
    UnitClass.FORTIFICATION: 1,
    # BTR-80 at 13.6 t and the truck-mounted command and power vehicles.
    UnitClass.APC: 2,
    UnitClass.COMMAND_POST: 2,
    UnitClass.POWER: 2,
    UnitClass.ELECTRONIC_WARFARE: 2,
    UnitClass.AAA_RADAR: 2,
    # BMP-3 at 18.7 t; the radar vehicles sit on comparable chassis.
    UnitClass.IFV: 3,
    UnitClass.SHORAD: 3,
    UnitClass.SEARCH_RADAR: 3,
    UnitClass.TRACK_RADAR: 3,
    UnitClass.SEARCH_TRACK_RADAR: 3,
    UnitClass.SPECIALIZED_RADAR: 3,
    # 2S3 at 27.5 t, an S-75 launcher with its missile, the 55G6 mast.
    UnitClass.ARTILLERY: 4,
    UnitClass.LAUNCHER: 4,
    UnitClass.EARLY_WARNING_RADAR: 4,
    # Buk TELAR at 32 t, a Scud on its MAZ-543.
    UnitClass.TELAR: 5,
    UnitClass.MISSILE: 5,
    UnitClass.ANTISHIP_MISSILE: 5,
    # T-90 at 46 t, M1A2 at 62 t. The reason a Huey cannot move armour.
    UnitClass.TANK: 8,
}


def lift_cost(unit_type: GroundUnitType) -> int:
    """Lift slots one of this vehicle occupies."""
    return LIFT_COST.get(unit_type.unit_class, DEFAULT_LIFT_COST)


def airlift_capacity(aircraft: AircraftType) -> int:
    """Lift slots this airframe can carry, from its data file or the fallback.

    The fallback is the pre-2026-08-26 constant read as slots, so an airframe
    with no authored ``airlift_capacity`` moves exactly what it moved before for
    cargo of the default cost, and less only for cargo heavier than that.
    """
    if aircraft.airlift_capacity is not None:
        return aircraft.airlift_capacity
    return 1 if aircraft.dcs_unit_type.helicopter else 2


def units_fitting_in(units: dict[GroundUnitType, int], slots: int) -> int:
    """How many vehicles of ``units`` fit in ``slots``, counted in split order.

    Deliberately greedy in the dict's own iteration order, because
    ``PendingTransfers.split_transfer`` consumes the transfer in exactly that
    order -- a count derived any other way would not describe the units the
    split actually hands to the flight.

    A consequence worth knowing: a transfer led by tanks cannot be part-lifted
    by a helicopter that could have carried the infantry behind them. It returns
    0, the planner moves on to a squadron with a bigger aircraft, and if none
    exists the transfer waits for a road or a ship. That is the intended answer
    -- the alternative is reordering somebody's transfer to suit the airframe.
    """
    taken = 0
    for unit_type, count in units.items():
        cost = lift_cost(unit_type)
        for _ in range(count):
            if cost > slots:
                return taken
            slots -= cost
            taken += 1
    return taken
