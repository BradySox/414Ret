"""PlanStrike fans `doctrine.strike_flight_count` coordinated sections onto a target.

Locks the section count at the proposal layer so a regression that drops the doctrine
read fails CI. Stock doctrines plan a single section; Vietnam masses up to FOUR
coordinated shared-TOT sections on one target -- the real Alpha Strike deck-load --
plus the forced fighter escort (always_escort_strikes; see
test_always_escort_strikes_forces_a2a_escort). Only the first section is required: the
rest are surge sections (ProposedFlight.optional) that plan when a squadron has the
jets and drop silently when not, so the top-priority target absorbs the strike fleet
and later strike targets shrink instead of scrubbing. The fan was briefly reverted to
1 when the sections flew naked; restored once the fighter economy held
(escort_support_aircraft off + strike_escort_reserve + its fence). See
docs/dev/design/414th-vietnam-retribution-notes.md (P3).
"""

from __future__ import annotations

from types import SimpleNamespace

from game.ato.flighttype import FlightType
from game.commander.tasks.primitive.strike import PlanStrike
from game.data.doctrine import (
    COLDWAR_DOCTRINE,
    Doctrine,
    MODERN_DOCTRINE,
    VIETNAM_DOCTRINE,
)


def _target(doctrine: Doctrine, units: int = 6) -> SimpleNamespace:
    # The strike target is enemy-owned, so the planning coalition is the target
    # owner's *opponent* -- that is where PlanStrike reads the doctrine from.
    planner = SimpleNamespace(doctrine=doctrine)
    return SimpleNamespace(
        alive_unit_count=lambda: units,
        coalition=SimpleNamespace(
            opponent=planner,
            game=SimpleNamespace(
                settings=SimpleNamespace(autoplan_tankers_for_strike=False)
            ),
        ),
    )


def _strike_sections(doctrine: Doctrine) -> list[bool]:
    """The proposed STRIKE sections, as their `optional` (surge) flags in order."""
    task = PlanStrike(_target(doctrine))  # type: ignore[arg-type]
    task.propose_flights()
    return [f.optional for f in task.flights if f.task is FlightType.STRIKE]


def test_stock_doctrines_plan_a_single_strike_section() -> None:
    for doctrine in (MODERN_DOCTRINE, COLDWAR_DOCTRINE):
        assert _strike_sections(doctrine) == [False]


def test_vietnam_masses_a_deck_load_of_surge_sections() -> None:
    # The real Alpha Strike: Vietnam fans up to FOUR coordinated shared-TOT sections
    # onto ONE target. Only the first is required; the surge sections are optional so
    # the fan masses as deep as inventory allows instead of scrubbing the package.
    assert _strike_sections(VIETNAM_DOCTRINE) == [False, True, True, True]


def test_always_escort_strikes_forces_a2a_escort() -> None:
    # Under a doctrine with always_escort_strikes (Vietnam), a STRIKE-led package marks the
    # A2A escort "needed" even with no detected air threat on the route -- otherwise
    # check_needed_escorts prunes it and the bombers fly naked.
    from typing import Any, cast

    from game.commander.missionproposals import EscortType
    from game.commander.packagefulfiller import PackageFulfiller

    no_threat = SimpleNamespace(
        waypoints_threatened_by_aircraft_engagement=lambda wps: False,
        waypoints_threatened_by_radar_sam=lambda wps: False,
    )
    strike = SimpleNamespace(
        flight_type=FlightType.STRIKE,
        flight_plan=SimpleNamespace(escorted_waypoints=lambda: []),
    )
    builder = SimpleNamespace(
        package=SimpleNamespace(flights=[strike], primary_flight=strike)
    )

    def needed(doctrine: Doctrine) -> dict[EscortType, bool]:
        ff = PackageFulfiller.__new__(PackageFulfiller)
        ff.coalition = cast(
            Any,
            SimpleNamespace(
                doctrine=doctrine, opponent=SimpleNamespace(threat_zone=no_threat)
            ),
        )
        return ff.check_needed_escorts(cast(Any, builder))

    assert needed(VIETNAM_DOCTRINE)[EscortType.AirToAir] is True
    # Stock doctrine without the flag: no detected threat -> no forced escort.
    assert needed(COLDWAR_DOCTRINE)[EscortType.AirToAir] is False
