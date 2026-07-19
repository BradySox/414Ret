"""Tests for the EWR enroute task + forced RED alarm on EWR ground objects.

Reverting the `isinstance(self.ground_object, EwrGroundObject)` guard in either
`GroundObjectGenerator.enable_ewr` or `GroundObjectGenerator.set_alarm_state`
makes the corresponding assertion below fail: these tests pin the EWR-only
behaviour and prove non-EWR groups are left alone.

Fork divergence from upstream #879: the fork removed the perf_red_alert_state
toggle (#231 — networked SAM alarm state is owned by the MANTIS IADS engine at
runtime), so a non-EWR, non-ship group gets NO alarm option at all (DCS AUTO)
rather than upstream's GREEN. Only ships (force_red) and dedicated EWR sites are
forced RED at generation.
"""

from types import SimpleNamespace
from typing import Any

from dcs.task import EWR, OptAlarmState

from game.missiongenerator.tgogenerator import GroundObjectGenerator
from game.theater.theatergroundobject import EwrGroundObject, VehicleGroupGroundObject


def _generator(ground_object: Any) -> Any:
    game = SimpleNamespace(settings=SimpleNamespace())
    return GroundObjectGenerator(
        ground_object, None, game, None, None  # type: ignore[arg-type]
    )


def _group() -> Any:
    return SimpleNamespace(points=[SimpleNamespace(tasks=[])])


# EwrGroundObject / VehicleGroupGroundObject are built without their heavy __init__
# (which needs a full ControlPoint graph): enable_ewr/set_alarm_state only branch on
# the runtime type, so a bare instance keeps the test focused on the behaviour.
def _ewr_tgo() -> EwrGroundObject:
    return object.__new__(EwrGroundObject)


def _armor_tgo() -> VehicleGroupGroundObject:
    return object.__new__(VehicleGroupGroundObject)


def test_enable_ewr_adds_task_for_ewr_ground_object() -> None:
    group = _group()
    _generator(_ewr_tgo()).enable_ewr(group)

    assert [type(t) for t in group.points[0].tasks] == [EWR]


def test_enable_ewr_skips_non_ewr_ground_object() -> None:
    group = _group()
    _generator(_armor_tgo()).enable_ewr(group)

    assert group.points[0].tasks == []


def test_ewr_forces_red_alarm() -> None:
    group = _group()
    _generator(_ewr_tgo()).set_alarm_state(group)

    alarm = group.points[0].tasks[0]
    assert isinstance(alarm, OptAlarmState)
    assert alarm.value == 2  # RED


def test_non_ewr_gets_no_alarm_option() -> None:
    # Fork contract (#231): alarm state for everything but EWRs/ships is owned by
    # the IADS engine at runtime — generation writes nothing, leaving DCS AUTO.
    group = _group()
    _generator(_armor_tgo()).set_alarm_state(group)

    assert group.points[0].tasks == []


def test_force_red_still_honored_for_non_ewr() -> None:
    group = _group()
    _generator(_armor_tgo()).set_alarm_state(group, force_red=True)

    assert group.points[0].tasks[0].value == 2  # RED
