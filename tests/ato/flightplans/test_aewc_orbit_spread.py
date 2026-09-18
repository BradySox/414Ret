"""AEW&C on one station step back from the threat instead of stacking.

The layout is deterministic in the target, so two AWACS tasked on one target flew
the identical racetrack. The §6 revert (2026-08-09) removed the sideways spread and
left AEW&C with nothing while the tanker got TANKER_ORBIT_SPACING. The spread is not
restored as it was: reviewed 2026-09-17, it half-overlapped in its only live case (a
hand-fragged second AWACS, because the first was never laid out again) and could
cross into a curved threat zone. Each further AWACS steps back from the threat, the
tanker's pattern, and the tanker's own threatened branch now steps the right way.

The slot is picked by where the others actually orbit, not by counting them. A
count collided whenever an AWACS was added to an earlier package, or one was deleted
and another fragged: the ones already laid out keep their orbit (review, 2026-09-17).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from game.ato.flightplans.aewc import Builder
from game.ato.flightplans.patrolling import step_back_from_threat
from game.ato.flighttype import FlightType
from dcs.mapping import Point
from dcs.terrain import Caucasus

from game.ato.flightplans.aewc import AEWC_ORBIT_SPACING
from game.utils import nautical_miles

# ---- step_back_from_threat ----------------------------------------------------


def test_a_clear_anchor_steps_back_toward_itself() -> None:
    # The centre sits short of the threat edge, so back is a smaller distance.
    moved = step_back_from_threat(
        nautical_miles(50), threatened=False, step=nautical_miles(20)
    )
    assert moved.nautical_miles == pytest.approx(30)


def test_a_threatened_anchor_steps_further_past_the_edge() -> None:
    # The centre sits past the edge; subtracting walked it back toward the zone,
    # which is what the tanker did before this.
    moved = step_back_from_threat(
        nautical_miles(90), threatened=True, step=nautical_miles(20)
    )
    assert moved.nautical_miles == pytest.approx(110)


def test_slot_zero_does_not_move() -> None:
    for threatened in (False, True):
        moved = step_back_from_threat(
            nautical_miles(50), threatened=threatened, step=nautical_miles(0)
        )
        assert moved.nautical_miles == pytest.approx(50)


# ---- Builder._orbit_slot ------------------------------------------------------
#
# Slots lie on a line, one AEWC_ORBIT_SPACING apart; a peer blocks the slot whose
# centre its own orbit sits on.

TERRAIN = Caucasus()
SPACING = AEWC_ORBIT_SPACING.meters


def _centre(slot: int) -> Point:
    return Point(slot * SPACING, 0.0, TERRAIN)


def _coalition() -> Any:
    return SimpleNamespace(ato=SimpleNamespace(packages=[]))


def _package(target: Any, coalition: Any, *, in_ato: bool = True) -> Any:
    package = SimpleNamespace(target=target, flights=[])
    if in_ato:
        coalition.ato.packages.append(package)
    return package


def _flight(
    package: Any, coalition: Any, *, at: int | None = None, kind: Any = None
) -> Any:
    """A flight in `package`, already orbiting slot `at` (None = not laid out)."""
    plan = None
    if at is not None:
        centre = _centre(at)
        plan = SimpleNamespace(
            layout=SimpleNamespace(
                patrol_start=SimpleNamespace(position=centre),
                patrol_end=SimpleNamespace(position=centre),
            )
        )
    flight = SimpleNamespace(
        flight_type=kind or FlightType.AEWC,
        package=package,
        coalition=coalition,
        laid_out_flight_plan=plan,
    )
    package.flights.append(flight)
    return flight


def _slot(flight: Any) -> int:
    builder = Builder.__new__(Builder)
    builder.flight = flight
    return builder._orbit_slot(_centre)


def test_a_lone_awacs_takes_slot_zero() -> None:
    coalition = _coalition()
    assert _slot(_flight(_package(object(), coalition), coalition)) == 0


def test_a_second_awacs_steps_back_one_slot() -> None:
    station = object()
    coalition = _coalition()
    _flight(_package(station, coalition), coalition, at=0)
    assert _slot(_flight(_package(station, coalition, in_ato=False), coalition)) == 1


def test_an_awacs_added_to_an_earlier_package_does_not_take_the_first_ones_slot() -> (
    None
):
    # Review finding, 3/3: counting AWACS ahead in ATO order gave the new flight in
    # the EARLIER package slot 0 -- the slot the existing AWACS already flew.
    station = object()
    coalition = _coalition()
    early = _package(station, coalition)
    _flight(_package(station, coalition), coalition, at=0)
    assert _slot(_flight(early, coalition)) == 1


def test_deleting_one_and_fragging_another_reuses_the_freed_slot() -> None:
    # Review finding: with A at 0 and B at 1, delete A and frag C. Counting gave C
    # slot 1, on top of B. The freed slot is 0.
    station = object()
    coalition = _coalition()
    first = _package(station, coalition)
    _flight(first, coalition, at=0)
    _flight(_package(station, coalition), coalition, at=1)
    coalition.ato.packages.remove(first)
    assert _slot(_flight(_package(station, coalition), coalition)) == 0


def test_replanning_a_later_one_after_a_delete_avoids_the_survivors() -> None:
    # Review finding: A0/A1/A2 at 0/1/2, delete A0, replan only A2. Counting gave A2
    # slot 1, still held by A1.
    station = object()
    coalition = _coalition()
    first = _package(station, coalition)
    _flight(first, coalition, at=0)
    _flight(_package(station, coalition), coalition, at=1)
    third = _flight(_package(station, coalition), coalition, at=2)
    coalition.ato.packages.remove(first)
    assert _slot(third) == 0


def test_replanning_keeps_an_awacs_clear_of_the_one_it_was_beside() -> None:
    station = object()
    coalition = _coalition()
    first = _flight(_package(station, coalition), coalition, at=0)
    _flight(_package(station, coalition), coalition, at=1)
    assert _slot(first) == 0


def test_two_awacs_in_one_unsaved_package_do_not_stack() -> None:
    coalition = _coalition()
    package = _package(object(), coalition, in_ato=False)
    _flight(package, coalition, at=0)
    assert _slot(_flight(package, coalition)) == 1


def test_a_peer_not_yet_laid_out_blocks_nothing() -> None:
    station = object()
    coalition = _coalition()
    _flight(_package(station, coalition), coalition)
    assert _slot(_flight(_package(station, coalition), coalition)) == 0


def test_a_jammer_is_never_part_of_the_spread() -> None:
    # JAMMING shares this builder. It keeps its own orbit, and an AWACS on the same
    # target neither counts it nor is pushed by it.
    station = object()
    coalition = _coalition()
    jammer = _flight(
        _package(station, coalition), coalition, at=0, kind=FlightType.JAMMING
    )
    assert _slot(jammer) == 0
    assert _slot(_flight(_package(station, coalition), coalition)) == 0


def test_different_targets_never_push_each_other() -> None:
    coalition = _coalition()
    _flight(_package(object(), coalition), coalition, at=0)
    assert _slot(_flight(_package(object(), coalition), coalition)) == 0


def test_other_flight_types_on_the_target_do_not_count() -> None:
    coalition = _coalition()
    package = _package(object(), coalition)
    _flight(package, coalition, at=0, kind=FlightType.BARCAP)
    assert _slot(_flight(package, coalition)) == 0
