from types import SimpleNamespace

from game.ato.flighttype import FlightType
from game.commander.tasks.primitive.dead import PlanDead


def _target(has_live_radar_sam: bool, tankers: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        alive_unit_count=lambda: 5,
        has_live_radar_sam=has_live_radar_sam,
        control_point=SimpleNamespace(
            coalition=SimpleNamespace(
                game=SimpleNamespace(
                    settings=SimpleNamespace(autoplan_tankers_for_dead=tankers)
                )
            )
        ),
    )


def test_dead_with_live_radar_sam_uses_dedicated_sead_not_sweep() -> None:
    task = PlanDead(_target(has_live_radar_sam=True))  # type: ignore[arg-type]
    task.propose_flights()

    assert [flight.task for flight in task.flights] == [
        FlightType.DEAD,
        FlightType.ESCORT,
        FlightType.SEAD,
    ]


def test_dead_without_live_radar_sam_uses_sead_escort_not_sweep() -> None:
    task = PlanDead(_target(has_live_radar_sam=False))  # type: ignore[arg-type]
    task.propose_flights()

    assert [flight.task for flight in task.flights] == [
        FlightType.DEAD,
        FlightType.ESCORT,
        FlightType.SEAD_ESCORT,
    ]
