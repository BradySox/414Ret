"""PlanStrike fans `doctrine.strike_flight_count` coordinated sections onto a target.

Locks the Alpha Strike behaviour (Vietnam = 2 sections, every other doctrine = 1) at the
proposal layer, so a regression that drops the doctrine read fails CI. See
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


def test_vietnam_plans_two_coordinated_strike_sections() -> None:
    sections = _strike_sections(VIETNAM_DOCTRINE)
    assert len(sections) == 2
    # Both sections request the same size -- two coordinated runs on one aimpoint.
    assert len(set(sections)) == 1
