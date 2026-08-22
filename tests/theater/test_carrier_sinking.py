"""Sinking a carrier takes its air wing down with it.

``TheaterUnit.kill`` removes the squadrons based on a sunk carrier. Two defects
lived in that branch:

1. It matched only ``UnitClass.AIRCRAFT_CARRIER``, so sinking any hull classed
   ``HELICOPTER_CARRIER`` left its squadrons flying. That is not only the LHAs --
   the WWII ``Essex`` is classed ``HELICOPTER_CARRIER`` on purpose, because that
   class is what ``transform_to_essex_if_needed`` tests before swapping the
   control point for ``EssexCarrier``. So the Essex, an aircraft carrier by any
   other measure at ``plane_num=90``, was exempt from its own sinking.
2. ``ControlPoint.squadrons`` is a generator over
   ``itertools.chain.from_iterable(air_wing.squadrons.values())`` -- the live
   lists. Removing from those lists while iterating skipped elements, so with two
   squadrons of one aircraft type on a hull the second survived. That one hit
   correctly-classed supercarriers too.

The fakes here deliberately reuse the real ``AirWing.iter_squadrons`` and the real
``ControlPoint.squadrons`` property, because the iteration *is* the second defect.
Ship types are the real DCS ones, so the class assertions are data, not fiction.
"""

from __future__ import annotations

from collections import defaultdict
from types import SimpleNamespace
from typing import Any, cast

import pytest
from dcs.ships import USS_Arleigh_Burke_IIa, Essex, LHA_Tarawa, Stennis
from dcs.unittype import ShipType

from game.data.units import UnitClass
from game.dcs.shipunittype import ShipUnitType
from game.squadrons.airwing import AirWing
from game.theater.controlpoint import ControlPoint
from game.theater.theatergroup import TheaterUnit


class FakeCarrierControlPoint:
    """Reuses the real ``ControlPoint.squadrons`` property so the lazy iteration
    under test is the shipped one, not a re-implementation of it."""

    squadrons = ControlPoint.squadrons

    def __init__(self, air_wing: AirWing) -> None:
        self.coalition = SimpleNamespace(air_wing=air_wing)


def make_air_wing() -> AirWing:
    # __init__ wants a Game and a Faction to build squadron defs; none of that is
    # reachable from kill(). Bypassing it keeps iter_squadrons real.
    wing = object.__new__(AirWing)
    wing.squadrons = defaultdict(list)
    return wing


def add_squadron(wing: AirWing, cp: Any, aircraft: str) -> Any:
    squadron = SimpleNamespace(aircraft=aircraft, location=cp, name=f"{aircraft} sqn")
    wing.squadrons[cast(Any, aircraft)].append(cast(Any, squadron))
    return squadron


def make_unit(ship: type[ShipType], ground_object: Any) -> TheaterUnit:
    return TheaterUnit(
        id=0,
        name=ship.id,
        type=ship,
        # kill() never reads the position.
        position=cast(Any, None),
        ground_object=ground_object,
    )


def sink(ship: type[ShipType], wing: AirWing, cp: Any, escorts: int = 0) -> None:
    """Build a naval TGO around ``ship``, then sink the ship itself."""
    ground_object = SimpleNamespace(
        is_iads=False,
        is_naval_control_point=True,
        control_point=cp,
        invalidate_threat_poly=lambda: None,
        units=[],
    )
    carrier = make_unit(ship, ground_object)
    ground_object.units = [carrier] + [
        make_unit(USS_Arleigh_Burke_IIa, ground_object) for _ in range(escorts)
    ]
    carrier.kill(cast(Any, SimpleNamespace(update_tgo=lambda tgo: None)))


# The fake squadrons carry a str where a real one carries an AircraftType.
def remaining(wing: AirWing) -> list[Any]:
    return [s.aircraft for s in wing.iter_squadrons()]


@pytest.mark.parametrize(
    "ship,expected_class",
    [
        (Stennis, UnitClass.AIRCRAFT_CARRIER),
        (Essex, UnitClass.HELICOPTER_CARRIER),
        (LHA_Tarawa, UnitClass.HELICOPTER_CARRIER),
    ],
)
def test_sinking_a_carrier_removes_its_squadrons(
    ship: type[ShipType], expected_class: UnitClass
) -> None:
    # Pin the classification the fix depends on. If DCS or the yaml reclassifies a
    # hull, this says so instead of the behaviour quietly changing.
    assert next(ShipUnitType.for_dcs_type(ship)).unit_class is expected_class

    wing = make_air_wing()
    cp = FakeCarrierControlPoint(wing)
    add_squadron(wing, cp, "F/A-18C")
    sink(ship, wing, cp)
    assert remaining(wing) == []


def test_every_squadron_of_one_aircraft_is_removed() -> None:
    """Two squadrons of one type share a list; removing while iterating skipped
    the second."""
    wing = make_air_wing()
    cp = FakeCarrierControlPoint(wing)
    add_squadron(wing, cp, "F/A-18C")
    add_squadron(wing, cp, "F/A-18C")
    add_squadron(wing, cp, "F-14B")
    sink(Stennis, wing, cp)
    assert remaining(wing) == []


def test_squadrons_survive_while_the_carrier_floats() -> None:
    """An escort going down is not the carrier going down."""
    wing = make_air_wing()
    cp = FakeCarrierControlPoint(wing)
    add_squadron(wing, cp, "F/A-18C")

    ground_object = SimpleNamespace(
        is_iads=False,
        is_naval_control_point=True,
        control_point=cp,
        invalidate_threat_poly=lambda: None,
        units=[],
    )
    carrier = make_unit(Stennis, ground_object)
    escort = make_unit(USS_Arleigh_Burke_IIa, ground_object)
    ground_object.units = [carrier, escort]

    escort.kill(cast(Any, SimpleNamespace(update_tgo=lambda tgo: None)))
    # The carrier unit is still alive, so nothing is grounded.
    assert remaining(wing) == ["F/A-18C"]


def test_squadrons_at_other_bases_are_untouched() -> None:
    wing = make_air_wing()
    boat = FakeCarrierControlPoint(wing)
    ashore = FakeCarrierControlPoint(wing)
    add_squadron(wing, boat, "F/A-18C")
    add_squadron(wing, ashore, "F-16C")
    sink(Essex, wing, boat)
    assert remaining(wing) == ["F-16C"]
