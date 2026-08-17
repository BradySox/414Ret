"""A refuel waypoint is only planned when a tanker is planned.

Reported 2026-08-17 off the Payload tab: a Hornet burning 8,111 lb of the 15,225
it carried was shown "1 tanker pass · RTB margin +11,680 lb". Nothing had tasked
a tanker for it -- ``PlanRefueling`` walks theater refueling stations and never
looks at a strike flight's fuel -- but the planner put a REFUEL waypoint on the
route because the coalition OWNED a tanker squadron, and the readout then
credited a full top-off from it.

This gate asks the narrower question the generated mission already asks: is a
tanker this flight could actually use in the ATO. It is deliberately NOT a
fuel-need test; that is the reverted §46 and re-opening it would re-open the
planner divergence the 2026-08-09 re-convergence closed.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.ato.flighttype import FlightType
from game.ato.tankeravailability import serviceable_tanker_planned


class Airframe:
    """A receiver that takes fuel from anything unless told otherwise."""

    def __init__(self, refuses: Any = None) -> None:
        self.refuses = refuses

    def can_refuel_from(self, tanker: Any) -> bool:
        return tanker is not self.refuses


def flight(flight_type: FlightType, unit_type: Any = None) -> Any:
    return SimpleNamespace(flight_type=flight_type, unit_type=unit_type or Airframe())


def receiver(packages: list[list[Any]], unit_type: Any = None) -> Any:
    ato = SimpleNamespace(packages=[SimpleNamespace(flights=p) for p in packages])
    return SimpleNamespace(
        coalition=SimpleNamespace(ato=ato), unit_type=unit_type or Airframe()
    )


def test_a_planned_tanker_earns_the_waypoint() -> None:
    assert serviceable_tanker_planned(receiver([[flight(FlightType.REFUELING)]]))


def test_no_tanker_in_the_ato_means_no_waypoint() -> None:
    assert not serviceable_tanker_planned(
        receiver([[flight(FlightType.BARCAP), flight(FlightType.STRIKE)]])
    )


def test_an_empty_ato_means_no_waypoint() -> None:
    assert not serviceable_tanker_planned(receiver([]))


def test_a_recovery_tanker_is_not_one() -> None:
    """It is its own flight type and works the boat's pattern, not passing
    traffic -- so it never earns a passing striker a refuel waypoint."""
    assert not serviceable_tanker_planned(receiver([[flight(FlightType.RECOVERY)]]))


def test_a_tanker_this_jet_cannot_use_does_not_count() -> None:
    """A probe-only receiver with nothing but a boom tanker up is in the same
    position as one with no tanker at all."""
    boom = object()
    assert not serviceable_tanker_planned(
        receiver(
            [[flight(FlightType.REFUELING, boom)]], unit_type=Airframe(refuses=boom)
        )
    )


def test_one_usable_tanker_among_several_is_enough() -> None:
    boom = object()
    assert serviceable_tanker_planned(
        receiver(
            [
                [flight(FlightType.RECOVERY)],
                [flight(FlightType.REFUELING, boom)],
                [flight(FlightType.REFUELING, object())],
            ],
            unit_type=Airframe(refuses=boom),
        )
    )


def test_absent_ato_never_drops_anything() -> None:
    """Lightweight test doubles carry no ATO; the generation-time pass is the
    backstop, so never drop on a guess."""
    assert serviceable_tanker_planned(SimpleNamespace(coalition=None))  # type: ignore[arg-type]
    assert serviceable_tanker_planned(SimpleNamespace())  # type: ignore[arg-type]
