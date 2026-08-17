"""Whether a tanker this flight could actually plug into is in the ATO.

The planner's refuel waypoint used to be gated on "does this coalition OWN a
tanker-capable squadron anywhere in theater", which is a question about the air
wing rather than about this turn. A flight got the waypoint whether or not a
tanker was flying, and the in-app fuel readout then credited a top-off from it.

This asks the narrower question the generated mission already asks (see
``game/missiongenerator/refuelrendezvous.py``, which resolves the same waypoint
against the tankers that exist in the .miz). Asking it at plan time as well
keeps the planning UI and the mission in agreement.

Deliberately NOT a fuel-need test. Whether the sortie needs the gas is what the
reverted §46 decided, and re-opening it would re-open the planner divergence the
2026-08-09 re-convergence closed.

Safe to call while a flight plan is being built: ``TheaterSupport`` is the first
method ``PlanNextAction`` yields, so tankers are in the ATO before any offensive
package is planned, and this reads ``flight_type``/``unit_type`` only -- never
another flight's ``flight_plan``, which would risk recursion.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from game.ato.flighttype import FlightType

if TYPE_CHECKING:
    from game.ato.flight import Flight


def serviceable_tanker_planned(flight: "Flight") -> bool:
    """Whether this coalition has a tanker planned that ``flight`` can use.

    ``FlightType.RECOVERY`` is excluded by construction rather than by a check:
    a recovery tanker is its own flight type, and it works the boat's pattern
    rather than servicing passing traffic.
    """
    ato = getattr(getattr(flight, "coalition", None), "ato", None)
    if ato is None:
        # Lightweight test doubles carry no ATO. Read as "yes" so nothing is
        # dropped on a guess -- the generation-time pass is the backstop.
        return True
    for package in ato.packages:
        for tanker in package.flights:
            if tanker.flight_type is not FlightType.REFUELING:
                continue
            if flight.unit_type.can_refuel_from(tanker.unit_type):
                return True
    return False
