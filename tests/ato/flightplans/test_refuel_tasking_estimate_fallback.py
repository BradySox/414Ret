"""``FormationAttackBuilder._refuel_tasking`` falls back to the synthesised estimate.

Airframes that ship no hand-measured ``fuel:`` block (many mod jets, e.g. the
F-4E-45MC) have ``fuel_consumption is None``. The kneeboard fuel ladder already
draws their RTB margin from ``estimated_fuel_consumption``, so it can warn "short of
home -- tank or divert". The tanker-tasking decision must use the *same* source, or
it silently refuses to frag a tanker the theater can crew on exactly the sortie the
ladder flagged. These tests pin that consistency (and that measured data still wins).
"""

from __future__ import annotations

from types import SimpleNamespace

from game.ato.flightplans.formationattack import (
    FormationAttackBuilder,
    FormationAttackFlightPlan,
    FormationAttackLayout,
)
from game.ato.flightwaypointtype import FlightWaypointType
from game.ato.refueltasking import RefuelTasking
from game.dcs.aircrafttype import FuelConsumption
from game.utils import KG_TO_LBS

_NM = 1852.0  # meters per nautical mile

# A thirsty jet: on a long sortie this burn far outruns internal fuel, so any flight
# that is allowed to consult it will want a tanker.
_THIRSTY = FuelConsumption(
    taxi=100, climb=20.0, cruise=10.0, combat=16.0, min_safe=1500
)
# Internal fuel that a full top-off restores to; 10000 lb after taxi.
_MAX_FUEL_KG = 10000.0 / KG_TO_LBS


class _Pos:
    """A point on a line; ``distance_to_point`` returns meters along it."""

    def __init__(self, nautical_miles: float) -> None:
        self.x = nautical_miles * _NM

    def distance_to_point(self, other: "_Pos") -> float:
        return abs(self.x - other.x)


class _WP:
    def __init__(self, at_nm: float, kind: FlightWaypointType) -> None:
        self.position = _Pos(at_nm)
        self.waypoint_type = kind


class _Builder(
    FormationAttackBuilder[FormationAttackFlightPlan, FormationAttackLayout]
):
    """Minimal concrete builder: bypass ``IBuilder.__init__`` (which reaches for
    ``game.settings``) so we can exercise ``_refuel_tasking`` in isolation."""

    def __init__(self, flight: object) -> None:
        self.flight = flight  # type: ignore[assignment]

    def build(self, dump_debug_info: bool = False) -> FormationAttackFlightPlan:
        raise NotImplementedError


def _flight(
    *,
    measured: FuelConsumption | None,
    estimated: FuelConsumption | None,
    can_plan_tanker: bool = True,
    is_helo: bool = False,
) -> SimpleNamespace:
    # No members -> the fuel-first tank pass sees no loadouts and no external fuel,
    # so these tests exercise the internal-fuel decision in isolation.
    return SimpleNamespace(
        is_helo=is_helo,
        unit_type=SimpleNamespace(
            fuel_consumption=measured,
            estimated_fuel_consumption=estimated,
            max_fuel=_MAX_FUEL_KG,
        ),
        iter_members=lambda: iter(()),
        coalition=SimpleNamespace(
            air_wing=SimpleNamespace(can_auto_plan=lambda task: can_plan_tanker),
            game=SimpleNamespace(
                settings=SimpleNamespace(
                    auto_range_fuel_tanks=True,
                    fuel_tanks_over_jammers=True,
                )
            ),
        ),
    )


def _long_sortie() -> tuple[list[_WP], set[_WP], _WP]:
    """A takeoff -> vul -> long trip home route that outruns internal fuel."""
    takeoff = _WP(0, FlightWaypointType.TAKEOFF)
    join = _WP(200, FlightWaypointType.JOIN)
    split = _WP(210, FlightWaypointType.SPLIT)
    landing = _WP(900, FlightWaypointType.LANDING_POINT)
    route = [takeoff, join, split, landing]
    return route, {join, split}, split


def _decide(flight: SimpleNamespace) -> RefuelTasking:
    route, combat_speed, split = _long_sortie()
    builder = _Builder(flight)
    return builder._refuel_tasking(route, combat_speed, split)  # type: ignore[arg-type]


def test_no_measured_fuel_still_tanks_from_the_estimate() -> None:
    # The F-4E case: no hand-measured block, but a thirsty estimate over a long
    # sortie -> the flight is tasked a tanker instead of being stranded.
    tasking = _decide(_flight(measured=None, estimated=_THIRSTY))
    assert tasking.needs_tanker


def test_no_fuel_data_at_all_plans_no_tanker() -> None:
    # Neither measured nor estimated (e.g. an airframe with no fuel capacity) -> the
    # decision can't reason about fuel, so it stays hands-off.
    assert _decide(_flight(measured=None, estimated=None)) is RefuelTasking.NONE


def test_measured_fuel_still_wins_over_the_estimate() -> None:
    # A roomy measured block covers the sortie; the thirsty estimate must not be
    # consulted, so no tanker is tasked.
    roomy = FuelConsumption(taxi=50, climb=2.0, cruise=1.0, combat=1.5, min_safe=500)
    assert _decide(_flight(measured=roomy, estimated=_THIRSTY)) is RefuelTasking.NONE


def test_no_tanker_squadron_means_no_tasking_even_when_short() -> None:
    # The theater can't crew a tanker -> the estimate fallback must not conjure one.
    tasking = _decide(_flight(measured=None, estimated=_THIRSTY, can_plan_tanker=False))
    assert tasking is RefuelTasking.NONE


def test_helo_never_tasked_from_the_estimate() -> None:
    tasking = _decide(_flight(measured=None, estimated=_THIRSTY, is_helo=True))
    assert tasking is RefuelTasking.NONE
