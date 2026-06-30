"""PlanStrike fans `doctrine.strike_flight_count` coordinated sections onto a target.

Locks the section count at the proposal layer so a regression that drops the doctrine
read fails CI. Every doctrine now plans a single section -- playtest feedback retired the
2-section Vietnam "Alpha Strike" fan in favour of one section + a forced fighter escort
(always_escort_strikes; see test_always_escort_strikes_forces_a2a_escort). See
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


def _strike_sections(doctrine: Doctrine) -> list[int]:
    task = PlanStrike(_target(doctrine))  # type: ignore[arg-type]
    task.propose_flights()
    return [f.num_aircraft for f in task.flights if f.task is FlightType.STRIKE]


def test_stock_doctrines_plan_a_single_strike_section() -> None:
    for doctrine in (MODERN_DOCTRINE, COLDWAR_DOCTRINE):
        assert len(_strike_sections(doctrine)) == 1


def test_vietnam_plans_a_single_strike_section() -> None:
    # Playtest feedback retired the 2-section Alpha Strike fan: a Vietnam STRIKE flies one
    # section + a forced fighter escort (always_escort_strikes) instead of two unescorted
    # bomber sections.
    assert len(_strike_sections(VIETNAM_DOCTRINE)) == 1


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
