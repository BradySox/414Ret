"""A theater tanker is only useful to aircraft whose receptacle it fits.

Boom and probe are physically incompatible, so a wing flying both needs one tanker
of each. Retribution planned exactly one, ever: ``refueling_targets`` is a
single-element list and ``PlanRefueling`` proposed a single ``REFUELING`` flight, so
half of a mixed wing had nothing to tank from. That is upstream issue #243, open
since 2024 — the recovery-tanker half was fixed in 2025, the theater half was not.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock

from game.ato.flighttype import FlightType
from game.commander.tasks.primitive.refueling import PlanRefueling
from game.dcs.aircrafttype import AirRefuelType


def _state(*receiver_methods: AirRefuelType | None) -> Any:
    """A theater state whose wing flies one squadron per method given."""
    squadrons = [
        SimpleNamespace(aircraft=SimpleNamespace(air_refuel_type=method))
        for method in receiver_methods
    ]
    coalition = SimpleNamespace(
        player=SimpleNamespace(is_blue=False),
        air_wing=SimpleNamespace(iter_squadrons=lambda: iter(squadrons)),
    )
    return cast(
        Any,
        SimpleNamespace(
            context=SimpleNamespace(
                coalition=coalition,
                settings=SimpleNamespace(auto_ato_behavior_tankers=True),
            )
        ),
    )


def _tanker_sqn(name: str, *dispenses: AirRefuelType, carrier: bool = False) -> Any:
    """A tanker squadron. `carrier` puts it on a boat, which the land station skips."""
    return SimpleNamespace(
        aircraft=SimpleNamespace(
            name=name, air_refuel_type=None, tanker_refuel_types=frozenset(dispenses)
        ),
        location=SimpleNamespace(is_carrier=carrier, is_fleet=carrier),
        untasked_aircraft=2,
        capable_of=lambda task: task is FlightType.REFUELING,
    )


def _land_station() -> Any:
    """A land tanker station. MagicMock would read as a carrier on every getattr."""
    return SimpleNamespace(is_carrier=False, is_fleet=False)


def _proposals(
    *receiver_methods: AirRefuelType | None, tankers: list[Any] | None = None
) -> list[Any]:
    task = PlanRefueling(_land_station())
    task.needed_refuel_methods = PlanRefueling._methods_the_wing_needs(
        _state(*receiver_methods)
    )
    # A land station only fans out over methods a LAND tanker can serve, so the
    # wing has to carry one of each unless a test says otherwise.
    if tankers is None:
        tankers = [
            _tanker_sqn("KC-135", AirRefuelType.BOOM),
            _tanker_sqn("KC-130", AirRefuelType.PROBE),
        ]
    task._air_wing = SimpleNamespace(  # type: ignore[assignment]
        iter_squadrons=lambda: iter(tankers)
    )
    task.propose_flights()
    return [f for f in task.flights if f.task is FlightType.REFUELING]


def test_a_single_method_wing_plans_one_tanker() -> None:
    """The no-change case. Everything takes the boom, one tanker serves everyone."""
    tankers = _proposals(AirRefuelType.BOOM, AirRefuelType.BOOM)
    assert len(tankers) == 1
    assert tankers[0].refuel_methods is None
    assert not tankers[0].optional


def test_a_wing_with_no_declared_methods_plans_one_tanker() -> None:
    """Campaigns whose aircraft carry no refuelling data must not regress."""
    tankers = _proposals(None, None)
    assert len(tankers) == 1
    assert tankers[0].refuel_methods is None


def test_a_mixed_wing_plans_one_tanker_per_method() -> None:
    tankers = _proposals(AirRefuelType.BOOM, AirRefuelType.BOOM, AirRefuelType.PROBE)
    assert len(tankers) == 2
    # The first is unconstrained, so the wing's best tanker is still free to win it.
    assert tankers[0].refuel_methods is None
    assert tankers[1].refuel_methods == frozenset({AirRefuelType.PROBE})


def test_the_extra_tanker_never_scrubs_the_package() -> None:
    """A probe-flying wing that owns no drogue tanker keeps its boom tanker."""
    tankers = _proposals(AirRefuelType.BOOM, AirRefuelType.PROBE)
    assert not tankers[0].optional
    assert all(t.optional for t in tankers[1:])


def test_methods_are_ordered_by_how_much_of_the_wing_needs_them() -> None:
    """The unconstrained first tanker gets the better squadron, so the majority
    method should be the one it is most likely to end up serving."""
    probe_heavy = PlanRefueling._methods_the_wing_needs(
        _state(
            AirRefuelType.PROBE,
            AirRefuelType.PROBE,
            AirRefuelType.PROBE,
            AirRefuelType.BOOM,
        )
    )
    assert probe_heavy == [AirRefuelType.PROBE, AirRefuelType.BOOM]


def test_the_escort_is_still_proposed() -> None:
    task = PlanRefueling(MagicMock())
    task.needed_refuel_methods = [AirRefuelType.BOOM, AirRefuelType.PROBE]
    task.propose_flights()
    assert [f.task for f in task.flights].count(FlightType.ESCORT) == 1


def _builder_with_package(flights: list[Any], flight: Any) -> Any:
    from game.ato.flightplans.theaterrefueling import Builder

    builder = Builder.__new__(Builder)
    # Builder.package is a read-only property reading through to the flight.
    flight.package = SimpleNamespace(flights=flights)
    builder.flight = flight
    return builder


def _tanker_flight() -> Any:
    return SimpleNamespace(flight_type=FlightType.REFUELING, package=None)


def test_each_tanker_in_a_package_gets_its_own_orbit_slot() -> None:
    """Two tankers handed the same racetrack would orbit in the same airspace."""
    first, second = _tanker_flight(), _tanker_flight()
    escort = SimpleNamespace(flight_type=FlightType.ESCORT, package=None)
    flights = [first, escort, second]
    assert _builder_with_package(flights, first)._orbit_index() == 0
    assert _builder_with_package(flights, second)._orbit_index() == 1


def test_a_flight_missing_from_its_package_falls_back_to_the_first_slot() -> None:
    """Never raise out of layout(); an unplaceable tanker just takes slot zero."""
    stray = _tanker_flight()
    assert _builder_with_package([_tanker_flight()], stray)._orbit_index() == 0


def test_the_spacing_moves_extra_tankers_away_from_the_threat() -> None:
    """Backwards, so an extra tanker cannot be pushed into the threat zone the
    buffer just cleared."""
    from game.ato.flightplans.theaterrefueling import TANKER_ORBIT_SPACING
    from game.utils import nautical_miles

    assert TANKER_ORBIT_SPACING > nautical_miles(0)
    # The layout subtracts spacing * index from the orbit distance, and orbit
    # distance is measured from the control point toward the threat.
    assert (TANKER_ORBIT_SPACING * 2).meters > TANKER_ORBIT_SPACING.meters


def test_an_explicit_tanker_constraint_beats_the_receivers_derived_one() -> None:
    """A theater tanker has no receivers in its package to infer a method from."""
    from game.commander.packagebuilder import PackageBuilder
    from game.commander.missionproposals import ProposedFlight

    builder = PackageBuilder.__new__(PackageBuilder)
    receiver = SimpleNamespace(
        flight_type=FlightType.BARCAP,
        unit_type=SimpleNamespace(air_refuel_type=AirRefuelType.BOOM),
    )
    builder.package = cast(Any, SimpleNamespace(flights=[receiver]))

    derived = ProposedFlight(FlightType.REFUELING, 1)
    assert builder._required_refuel_methods(derived) == frozenset({AirRefuelType.BOOM})

    stated = ProposedFlight(
        FlightType.REFUELING, 1, refuel_methods=frozenset({AirRefuelType.PROBE})
    )
    assert builder._required_refuel_methods(stated) == frozenset({AirRefuelType.PROBE})


# ---- per-carrier stations (2026-08-19) ----------------------------------------
#
# The station list was a single element: the CP nearest the enemy, chosen with no
# regard for basing. On a flown Caucasus turn that put both tankers on a sector HQ
# with the KC-135 151 NM away and the carrier's A-6E 173 NM off its boat. Each
# carrier now gets its own station, and the land station goes to a field that
# hosts a tanker.


def test_a_carrier_station_plans_one_tanker_from_that_boat() -> None:
    boat = SimpleNamespace(is_carrier=True, is_fleet=True)
    own = _tanker_sqn("A-6E", AirRefuelType.PROBE, carrier=True)
    own.location = boat  # the squadron IS on this station's boat
    ashore = _tanker_sqn("KC-135", AirRefuelType.BOOM)
    task = PlanRefueling(boat)  # type: ignore[arg-type]
    task.needed_refuel_methods = [AirRefuelType.BOOM, AirRefuelType.PROBE]
    task._air_wing = SimpleNamespace(  # type: ignore[assignment]
        iter_squadrons=lambda: iter([own, ashore])
    )
    task.propose_flights()

    tankers = [f for f in task.flights if f.task is FlightType.REFUELING]
    assert len(tankers) == 1, "a boat covers its own station, no per-method fan-out"
    assert tankers[0].preferred_type is own.aircraft


def test_the_land_station_skips_a_method_only_a_boat_can_serve() -> None:
    # The regression this guards: the land station's probe slot reached for the
    # carrier's A-6E and dragged it 314 NM off its boat, which is worse than the
    # defect being fixed -- and pointless, because the boat's own station covers
    # those receivers.
    tankers = [
        _tanker_sqn("KC-135", AirRefuelType.BOOM),
        _tanker_sqn("A-6E", AirRefuelType.PROBE, carrier=True),
    ]
    planned = _proposals(
        AirRefuelType.BOOM, AirRefuelType.BOOM, AirRefuelType.PROBE, tankers=tankers
    )
    assert len(planned) == 1
    assert planned[0].refuel_methods is None


def test_the_land_station_still_fans_out_when_both_are_ashore() -> None:
    planned = _proposals(AirRefuelType.BOOM, AirRefuelType.BOOM, AirRefuelType.PROBE)
    assert len(planned) == 2
    assert planned[1].refuel_methods == frozenset({AirRefuelType.PROBE})
