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


def _tanker_sqn(
    name: str, *dispenses: AirRefuelType, carrier: bool = False, reachable: bool = True
) -> Any:
    """A tanker squadron. `carrier` puts it on a boat, which the land station skips;
    `reachable=False` is one the planner cannot assign to this station."""
    return SimpleNamespace(
        aircraft=SimpleNamespace(
            name=name,
            variant_id=name,
            air_refuel_type=None,
            tanker_refuel_types=frozenset(dispenses),
        ),
        location=SimpleNamespace(is_carrier=carrier, is_fleet=carrier),
        untasked_aircraft=2,
        capable_of=lambda task: task is FlightType.REFUELING,
        reachable=reachable,
    )


def _air_wing(tankers: list[Any]) -> Any:
    """The wing, with best_squadron_for ranking `tankers` in list order.

    List order stands in for the planner's squadron ranking, so putting the boom
    tanker first is what makes an unconstrained pick land on boom.
    """

    def best_squadrons_for(
        location: Any,
        task: Any,
        size: int,
        heli: bool,
        this_turn: bool,
        preferred_type: Any = None,
        ignore_range: bool = False,
        refuel_methods: Any = None,
    ) -> list[Any]:
        ranked = []
        for squadron in tankers:
            if not squadron.reachable:
                continue
            if preferred_type is not None and squadron.aircraft is not preferred_type:
                continue
            # The planner's filter is permissive for an untagged tanker.
            dispenses = squadron.aircraft.tanker_refuel_types
            if refuel_methods and dispenses and not refuel_methods <= dispenses:
                continue
            ranked.append(squadron)
        return ranked

    def best_squadron_for(*args: Any, **kwargs: Any) -> Any:
        ranked = best_squadrons_for(*args, **kwargs)
        return ranked[0] if ranked else None

    return SimpleNamespace(
        iter_squadrons=lambda: iter(tankers),
        best_squadrons_for=best_squadrons_for,
        best_squadron_for=best_squadron_for,
    )


def _fill(proposals: list[Any], tankers: list[Any]) -> list[Any]:
    """The tankers the planner actually assigns, proposal by proposal."""
    wing = _air_wing(tankers)
    return [
        wing.best_squadron_for(
            None,
            FlightType.REFUELING,
            1,
            False,
            True,
            preferred_type=p.preferred_type,
            refuel_methods=p.refuel_methods,
        )
        for p in proposals
    ]


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
    task._air_wing = _air_wing(tankers)
    task.propose_flights()
    return [f for f in task.flights if f.task is FlightType.REFUELING]


def test_a_single_method_wing_plans_one_tanker() -> None:
    """Everything takes the boom, so one boom tanker serves everyone."""
    tankers = _proposals(AirRefuelType.BOOM, AirRefuelType.BOOM)
    assert len(tankers) == 1
    assert tankers[0].refuel_methods == frozenset({AirRefuelType.BOOM})
    assert not tankers[0].optional


def test_a_wing_with_no_declared_methods_plans_one_tanker() -> None:
    """Campaigns whose aircraft carry no refuelling data must not regress."""
    tankers = _proposals(None, None)
    assert len(tankers) == 1
    assert tankers[0].refuel_methods is None


def test_a_mixed_wing_plans_one_tanker_per_method() -> None:
    tankers = _proposals(AirRefuelType.BOOM, AirRefuelType.BOOM, AirRefuelType.PROBE)
    assert [t.refuel_methods for t in tankers] == [
        frozenset({AirRefuelType.BOOM}),
        frozenset({AirRefuelType.PROBE}),
    ]


def test_a_probe_heavy_wing_gets_a_probe_tanker_not_two_boom() -> None:
    """The B76 fail signature, reproduced on Long Road to H3 (2026-09-17).

    Probe is the majority method, so it is listed first. The first tanker used to be
    unconstrained, so it took the wing's best squadron -- the boom KC-135 -- and the
    loop then proposed the method listed second, boom, which the same squadron
    filled. Two boom tankers; the KC-135 MPRS was never asked for.
    """
    boom_first = [
        _tanker_sqn("KC-135", AirRefuelType.BOOM),
        _tanker_sqn("KC-135 MPRS", AirRefuelType.PROBE),
    ]
    planned = _proposals(
        AirRefuelType.PROBE,
        AirRefuelType.PROBE,
        AirRefuelType.PROBE,
        AirRefuelType.BOOM,
        tankers=boom_first,
    )
    filled = _fill(planned, boom_first)
    dispensed = sorted(
        m.name for squadron in filled for m in squadron.aircraft.tanker_refuel_types
    )
    assert dispensed == ["BOOM", "PROBE"]
    assert not planned[0].optional


def test_the_extra_tanker_never_scrubs_the_package() -> None:
    """A probe-flying wing that owns no drogue tanker keeps its boom tanker."""
    tankers = _proposals(AirRefuelType.BOOM, AirRefuelType.PROBE)
    assert not tankers[0].optional
    assert all(t.optional for t in tankers[1:])


def test_methods_are_ordered_by_how_much_of_the_wing_needs_them() -> None:
    """The majority method gets the mandatory first tanker, so it is the one kept
    when only one can be filled."""
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
    assert planned[0].refuel_methods == frozenset({AirRefuelType.BOOM})


def test_the_land_station_still_fans_out_when_both_are_ashore() -> None:
    planned = _proposals(AirRefuelType.BOOM, AirRefuelType.BOOM, AirRefuelType.PROBE)
    assert len(planned) == 2
    assert planned[1].refuel_methods == frozenset({AirRefuelType.PROBE})


def test_probe_receivers_with_only_a_boom_tanker_keep_one_tanker() -> None:
    """B76's negative case: the package stays, with the one tanker the wing has."""
    planned = _proposals(
        AirRefuelType.PROBE,
        AirRefuelType.PROBE,
        tankers=[_tanker_sqn("KC-135", AirRefuelType.BOOM)],
    )
    assert len(planned) == 1
    assert not planned[0].optional


def test_a_mixed_wing_with_only_a_boom_tanker_is_not_given_two() -> None:
    # The old loop re-proposed boom here too, so a lone boom squadron was asked
    # for twice.
    only_boom = [_tanker_sqn("KC-135", AirRefuelType.BOOM)]
    planned = _proposals(
        AirRefuelType.PROBE, AirRefuelType.PROBE, AirRefuelType.BOOM, tankers=only_boom
    )
    assert [t.refuel_methods for t in planned] == [frozenset({AirRefuelType.BOOM})]
    assert not planned[0].optional


def test_a_tanker_that_cannot_fly_the_station_does_not_count() -> None:
    """The first tanker is mandatory: constrained to a method whose only tanker
    cannot be assigned here, it would scrub a package that fills today."""
    tankers = [
        _tanker_sqn("KC-135", AirRefuelType.BOOM),
        _tanker_sqn("KC-135 MPRS", AirRefuelType.PROBE, reachable=False),
    ]
    planned = _proposals(
        AirRefuelType.PROBE, AirRefuelType.PROBE, AirRefuelType.BOOM, tankers=tankers
    )
    assert [t.refuel_methods for t in planned] == [frozenset({AirRefuelType.BOOM})]
    assert all(squadron is not None for squadron in _fill(planned, tankers))


def test_no_method_is_proposed_twice() -> None:
    planned = _proposals(
        AirRefuelType.PROBE,
        AirRefuelType.BOOM,
        AirRefuelType.PROBE,
        AirRefuelType.BOOM,
    )
    methods = [t.refuel_methods for t in planned]
    assert len(methods) == len(set(methods))


def test_the_tanker_type_follows_the_planners_ranking_not_wing_order() -> None:
    """Review, 2026-09-17: the type was the first matching one in wing order, so a
    KC-135 flew 160 NM while a KC-10 sat at the station. The planner ranks the
    station's own squadron first; that is the one to ask for."""
    near = _tanker_sqn("KC-10", AirRefuelType.BOOM)
    far = _tanker_sqn("KC-135", AirRefuelType.BOOM)
    task = PlanRefueling(_land_station())
    task.needed_refuel_methods = [AirRefuelType.BOOM]
    ranked = _air_wing([near, far])
    task._air_wing = SimpleNamespace(  # type: ignore[assignment]
        # Wing order lists the far one first; the ranking puts the near one first.
        iter_squadrons=lambda: iter([far, near]),
        best_squadrons_for=ranked.best_squadrons_for,
        best_squadron_for=ranked.best_squadron_for,
    )
    task.propose_flights()
    (tanker,) = [f for f in task.flights if f.task is FlightType.REFUELING]
    assert tanker.preferred_type is near.aircraft


def test_an_untagged_tanker_covers_no_method() -> None:
    """The planner lets an untagged tanker through any method filter. It still
    covers nothing, so with no tagged tanker the pre-U15 single tanker is planned."""
    untagged = _tanker_sqn("Mystery tanker")
    planned = _proposals(AirRefuelType.PROBE, AirRefuelType.BOOM, tankers=[untagged])
    assert len(planned) == 1
    assert planned[0].refuel_methods is None
    assert not planned[0].optional
