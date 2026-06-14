from typing import Any, Callable
from unittest.mock import MagicMock

from dcs.task import AttackGroup, Expend, WeaponType

from game.missiongenerator.aircraft.waypoints.seadingress import SeadIngressBuilder
from game.theater import TheaterGroundObject


def _model_group(name: str) -> MagicMock:
    group = MagicMock()
    group.group_name = name
    return group


def _build_builder(target: Any, find_group: Callable[[str], Any]) -> tuple[Any, Any]:
    builder: Any = object.__new__(SeadIngressBuilder)
    builder.register_special_strike_points = MagicMock()
    builder.register_special_ingress_points = MagicMock()
    builder.package = MagicMock()
    builder.package.target = target
    builder.flight = MagicMock()
    builder.mission = MagicMock()
    builder.mission.find_group.side_effect = find_group
    builder.waypoint = MagicMock()
    builder.waypoint.targets = []
    waypoint = MagicMock()
    waypoint.alt = 20000
    waypoint.position = MagicMock()
    waypoint.tasks = []
    return builder, waypoint


def test_sead_ingress_staggers_decoys_and_kinetic_shots() -> None:
    target = MagicMock(spec=TheaterGroundObject)
    target.groups = [_model_group("sam-group")]
    target.position = MagicMock()
    target.position.heading_between_point.return_value = 45

    miz_group = MagicMock()
    miz_group.id = 42

    builder, waypoint = _build_builder(
        target, lambda name: miz_group if name == "sam-group" else None
    )
    builder.add_tasks(waypoint)

    attacks = [task for task in waypoint.tasks if isinstance(task, AttackGroup)]
    assert [task.params["weaponType"] for task in attacks[:4]] == [
        WeaponType.Decoy.value,
        WeaponType.ARM.value,
        WeaponType.ASM.value,
        WeaponType.GuidedBombs.value,
    ]

    for task in attacks[:4]:
        assert task.params["attackQtyLimit"] is True
        assert task.params["attackQty"] == 1
        assert task.params["expend"] == Expend.One.value
        assert task.params["groupAttack"] is False
