"""Escort pre-join ROE: ReturnFire at spawn, OpenFire from the JOIN waypoint.

pydcs OptROE semantics: OpenFire(2) = "engage ONLY targets specified in its
taskings" -- it grants NO return-fire allowance. An escort's one
target-designating task (the Escort ControlledTask) attaches at the JOIN
waypoint, so an escort spawned at OpenFire had an EMPTY legal-target set for its
whole hold/transit window: mechanically unable to fire even under attack (the
flown Red Tide M1 TOAD Escort MiG-29s died merged at gun range, silent, with a
JOIN ETA one second before the first death). The fix: spawn escorts at
ReturnFire, escalate to OpenFire at JOIN where the escort duty begins.
"""

from types import SimpleNamespace
from typing import Any

from dcs.task import ControlledTask, OptROE

from game.ato import FlightType
from game.missiongenerator.aircraft.aircraftbehavior import AircraftBehavior
from game.missiongenerator.aircraft.waypoints.joinpoint import JoinPointBuilder


class _RecordingBehavior(AircraftBehavior):
    """Capture configure_behavior kwargs without needing a real group/flight."""

    def __init__(self) -> None:  # do not call super
        self.recorded: dict[str, Any] = {}

    def configure_task(  # type: ignore[override]
        self, flight: Any, group: Any, task: Any
    ) -> None:
        pass

    def configure_behavior(  # type: ignore[override]
        self, flight: Any, group: Any, **kwargs: Any
    ) -> None:
        self.recorded = kwargs


def test_escort_spawns_at_return_fire() -> None:
    behavior = _RecordingBehavior()
    behavior.configure_escort(SimpleNamespace(), SimpleNamespace())  # type: ignore[arg-type]
    assert behavior.recorded["roe"] == OptROE.Values.ReturnFire


def test_sead_escort_spawns_at_return_fire() -> None:
    behavior = _RecordingBehavior()
    behavior.configure_sead_escort(SimpleNamespace(), SimpleNamespace())  # type: ignore[arg-type]
    assert behavior.recorded["roe"] == OptROE.Values.ReturnFire


def _join_builder(flight_type: FlightType) -> Any:
    builder: Any = JoinPointBuilder.__new__(JoinPointBuilder)
    doctrine = SimpleNamespace(
        escort_engagement_range=SimpleNamespace(nautical_miles=20.0),
        escort_spacing=SimpleNamespace(feet=1000.0),
        sead_escort_engagement_range=SimpleNamespace(nautical_miles=30.0),
        sead_escort_spacing=SimpleNamespace(feet=1000.0),
    )
    builder.flight = SimpleNamespace(
        flight_type=flight_type,
        is_helo=False,
        coalition=SimpleNamespace(doctrine=doctrine),
        squadron=SimpleNamespace(
            coalition=SimpleNamespace(
                game=SimpleNamespace(settings=SimpleNamespace(ai_unlimited_fuel=False))
            )
        ),
        package=SimpleNamespace(
            target=SimpleNamespace(), primary_flight=SimpleNamespace(group_id=7)
        ),
    )
    builder.package = builder.flight.package
    return builder


def _waypoint() -> Any:
    return SimpleNamespace(tasks=[])


def test_join_escalates_escort_to_open_fire() -> None:
    wp = _waypoint()
    _join_builder(FlightType.ESCORT).add_tasks(wp)
    roes = [t for t in wp.tasks if isinstance(t, OptROE)]
    assert len(roes) == 1
    assert roes[0].dict()["params"]["action"]["params"]["value"] == int(
        OptROE.Values.OpenFire
    )
    # The escort task itself still attaches here (the designation OpenFire scopes to).
    assert any(isinstance(t, ControlledTask) for t in wp.tasks)


def test_join_escalates_sead_escort_to_open_fire() -> None:
    wp = _waypoint()
    _join_builder(FlightType.SEAD_ESCORT).add_tasks(wp)
    roes = [t for t in wp.tasks if isinstance(t, OptROE)]
    assert len(roes) == 1
    assert roes[0].dict()["params"]["action"]["params"]["value"] == int(
        OptROE.Values.OpenFire
    )


def test_non_escort_join_gets_no_roe_change() -> None:
    wp = _waypoint()
    _join_builder(FlightType.BAI).add_tasks(wp)
    assert not any(isinstance(t, OptROE) for t in wp.tasks)
