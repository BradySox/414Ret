"""Tests for tanker selection by refueling method (AirWing._tanker_serves_methods).

This is the planner-side gate: when a tanker is being planned for a package, only
squadrons whose aircraft provide the receivers' boom/probe method(s) are eligible.
"""

from types import SimpleNamespace
from typing import Optional

from game.dcs.aircrafttype import AirRefuelType
from game.squadrons.airwing import AirWing

BOOM = AirRefuelType.BOOM
PROBE = AirRefuelType.PROBE


def _serves(
    provides: frozenset[AirRefuelType], required: Optional[frozenset[AirRefuelType]]
) -> bool:
    aircraft = SimpleNamespace(tanker_refuel_types=provides)
    return AirWing._tanker_serves_methods(aircraft, required)  # type: ignore[arg-type]


def test_no_required_methods_allows_any_tanker() -> None:
    # Non-refueling planning (or an untagged-receiver package) passes None.
    assert _serves(frozenset({BOOM}), None)


def test_untagged_tanker_is_permissive() -> None:
    assert _serves(frozenset(), frozenset({BOOM}))


def test_tanker_must_provide_the_required_method() -> None:
    assert _serves(frozenset({PROBE}), frozenset({PROBE}))
    assert not _serves(frozenset({BOOM}), frozenset({PROBE}))
    assert _serves(frozenset({BOOM, PROBE}), frozenset({PROBE}))


def test_mixed_receiver_package_needs_a_multi_method_tanker() -> None:
    mixed = frozenset({BOOM, PROBE})
    assert not _serves(frozenset({BOOM}), mixed)
    assert _serves(frozenset({BOOM, PROBE}), mixed)
