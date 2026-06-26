"""Tests for per-method theater-tanker seeding (seed_refueling_targets).

A mixed boom+probe receiver fleet should get one theater tanker per method it needs
*and* can crew, instead of a single method-blind tanker that strands the other half.
"""

from __future__ import annotations

from types import SimpleNamespace

from game.ato.flighttype import FlightType
from game.commander.theaterstate import RefuelingTarget, seed_refueling_targets
from game.dcs.aircrafttype import AirRefuelType

BOOM = AirRefuelType.BOOM
PROBE = AirRefuelType.PROBE
LOCATION = object()  # opaque MissionTarget stand-in; only identity is used


def _sq(tanker_methods=frozenset(), receiver_method=None, refueling_capable=False):  # type: ignore[no-untyped-def]
    aircraft = SimpleNamespace(
        tanker_refuel_types=frozenset(tanker_methods),
        air_refuel_type=receiver_method,
    )
    return SimpleNamespace(
        aircraft=aircraft,
        capable_of=lambda task: refueling_capable and task is FlightType.REFUELING,
    )


def _coalition(*squadrons):  # type: ignore[no-untyped-def]
    return SimpleNamespace(
        air_wing=SimpleNamespace(iter_squadrons=lambda: list(squadrons))
    )


def _methods(targets):  # type: ignore[no-untyped-def]
    return [t.method for t in targets]


def test_mixed_fleet_with_both_tankers_gets_one_tanker_per_method() -> None:
    coalition = _coalition(
        _sq(tanker_methods={BOOM}),  # KC-135
        _sq(tanker_methods={PROBE}),  # KC-135 MPRS
        _sq(receiver_method=BOOM),  # F-16
        _sq(receiver_method=PROBE),  # F/A-18C
    )
    targets = seed_refueling_targets(coalition, LOCATION)  # type: ignore[arg-type]
    assert _methods(targets) == [BOOM, PROBE]  # sorted, deterministic
    assert all(t.location is LOCATION for t in targets)


def test_boom_only_receivers_seed_only_a_boom_tanker() -> None:
    coalition = _coalition(
        _sq(tanker_methods={BOOM}),
        _sq(tanker_methods={PROBE}),
        _sq(receiver_method=BOOM),
    )
    targets = seed_refueling_targets(coalition, LOCATION)  # type: ignore[arg-type]
    assert _methods(targets) == [BOOM]


def test_method_without_a_matching_tanker_is_skipped() -> None:
    # Boom + probe receivers but only a boom tanker: serve the boom receivers and skip
    # the unservable probe method (still one tanker -- never fewer than legacy).
    coalition = _coalition(
        _sq(tanker_methods={BOOM}),
        _sq(receiver_method=PROBE),
        _sq(receiver_method=BOOM),
    )
    targets = seed_refueling_targets(coalition, LOCATION)  # type: ignore[arg-type]
    assert _methods(targets) == [BOOM]


def test_no_servable_method_falls_back_to_one_unconstrained() -> None:
    # Legacy behavior preserved: every needed method lacks a tanker, so frag exactly one
    # unconstrained tanker (priority-first) rather than nothing.
    coalition = _coalition(
        _sq(tanker_methods={BOOM}),
        _sq(receiver_method=PROBE),
    )
    targets = seed_refueling_targets(coalition, LOCATION)  # type: ignore[arg-type]
    assert _methods(targets) == [None]


def test_untagged_receiver_fleet_gets_one_unconstrained_tanker() -> None:
    coalition = _coalition(
        _sq(tanker_methods={BOOM}),
        _sq(receiver_method=None),
        _sq(receiver_method=None),
    )
    targets = seed_refueling_targets(coalition, LOCATION)  # type: ignore[arg-type]
    assert targets == [RefuelingTarget(LOCATION, None)]  # type: ignore[arg-type]


def test_permissive_tanker_serves_everyone_with_one_target() -> None:
    # A refueling-capable tanker that advertises no method services any receiver, so a
    # single unconstrained tanker suffices even for a mixed fleet.
    coalition = _coalition(
        _sq(refueling_capable=True),  # untagged but tanker-capable
        _sq(receiver_method=BOOM),
        _sq(receiver_method=PROBE),
    )
    targets = seed_refueling_targets(coalition, LOCATION)  # type: ignore[arg-type]
    assert _methods(targets) == [None]
